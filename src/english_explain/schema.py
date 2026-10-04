"""Validation for the public, text-first lesson bundle contract.

The repository intentionally uses a small standard-library validator rather than
an opaque model or a runtime service. The JSON Schema is published beside this
module for tooling that wants a machine-readable contract; this validator adds
cross-field invariants such as aligned segment IDs and explicit provenance.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import json
import re
from pathlib import Path
from typing import Any


class LessonValidationError(ValueError):
    """Raised when a lesson bundle is missing required, inspectable structure."""

    def __init__(self, errors: Sequence[str]) -> None:
        self.errors = tuple(errors)
        super().__init__("; ".join(self.errors))


_ID = re.compile(r"^[a-z0-9][a-z0-9-]{1,63}$")
_UNSUPPORTED_TERMS = re.compile(
    r"\b(?:proficien(?:cy|t)|master(?:y|ed)|cefr\s*(?:score|level)|overall\s+score)\b",
    re.IGNORECASE,
)
_UNSUPPORTED_FIELDS = re.compile(r"(?:proficiency|mastery|cefr|score)", re.IGNORECASE)


def load_bundle(path: str | Path) -> dict[str, Any]:
    """Load and validate a UTF-8 JSON lesson bundle from ``path``."""

    source = Path(path)
    try:
        value = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LessonValidationError((f"cannot read JSON bundle {source}: {exc}",)) from exc
    validate_bundle(value)
    return value


def validate_bundle(bundle: Any) -> None:
    """Validate a lesson bundle, raising :class:`LessonValidationError` on failure.

    The contract supports intended learner levels (for example ``intermediate``),
    but rejects claims about a learner's achieved proficiency or a single score.
    """

    errors: list[str] = []
    if not isinstance(bundle, Mapping):
        raise LessonValidationError(("bundle must be a JSON object",))

    required = {
        "schema_version",
        "id",
        "title",
        "language",
        "audience",
        "objectives",
        "context",
        "items",
        "provenance",
    }
    missing = sorted(required - set(bundle))
    errors.extend(f"missing required field: {name}" for name in missing)

    if bundle.get("schema_version") != "0.1":
        errors.append("schema_version must be '0.1'")
    _require_id(bundle.get("id"), "id", errors)
    _require_string(bundle.get("title"), "title", errors)
    if bundle.get("language") != "en":
        errors.append("language must be 'en' for this contract")

    audience = bundle.get("audience")
    if not isinstance(audience, Mapping):
        errors.append("audience must be an object")
    else:
        _require_string(audience.get("level"), "audience.level", errors)
        _require_string(audience.get("description"), "audience.description", errors)

    _require_string_list(bundle.get("objectives"), "objectives", errors, nonempty=True)
    _require_string(bundle.get("context"), "context", errors)

    provenance = bundle.get("provenance")
    if not isinstance(provenance, Mapping):
        errors.append("provenance must be an object")
    else:
        for field in ("text", "audio", "license"):
            _require_string(provenance.get(field), f"provenance.{field}", errors)

    items = bundle.get("items")
    if not isinstance(items, list) or not items:
        errors.append("items must be a non-empty array")
    else:
        item_ids: set[str] = set()
        for index, item in enumerate(items):
            _validate_item(item, index, item_ids, errors)

    _reject_unsupported_claims(bundle, errors)
    if errors:
        raise LessonValidationError(errors)


def _validate_item(
    item: Any,
    index: int,
    item_ids: set[str],
    errors: list[str],
) -> None:
    prefix = f"items[{index}]"
    if not isinstance(item, Mapping):
        errors.append(f"{prefix} must be an object")
        return
    for field in ("id", "title", "input", "task", "feedback", "provenance"):
        if field not in item:
            errors.append(f"{prefix} missing required field: {field}")
    item_id = item.get("id")
    _require_id(item_id, f"{prefix}.id", errors)
    if isinstance(item_id, str):
        if item_id in item_ids:
            errors.append(f"duplicate item id: {item_id}")
        item_ids.add(item_id)
    _require_string(item.get("title"), f"{prefix}.title", errors)

    input_data = item.get("input")
    segment_ids: set[str] = set()
    if not isinstance(input_data, Mapping):
        errors.append(f"{prefix}.input must be an object")
    else:
        segments = input_data.get("segments")
        if not isinstance(segments, list) or not segments:
            errors.append(f"{prefix}.input.segments must be a non-empty array")
        else:
            for segment_index, segment in enumerate(segments):
                segment_prefix = f"{prefix}.input.segments[{segment_index}]"
                if not isinstance(segment, Mapping):
                    errors.append(f"{segment_prefix} must be an object")
                    continue
                segment_id = segment.get("id")
                _require_id(segment_id, f"{segment_prefix}.id", errors)
                if isinstance(segment_id, str):
                    if segment_id in segment_ids:
                        errors.append(f"duplicate segment id in {prefix}: {segment_id}")
                    segment_ids.add(segment_id)
                _require_string(segment.get("text"), f"{segment_prefix}.text", errors)
                audio = segment.get("audio")
                if audio is not None:
                    _require_relative_path(audio, f"{segment_prefix}.audio", errors)

    task = item.get("task")
    if not isinstance(task, Mapping):
        errors.append(f"{prefix}.task must be an object")
    else:
        for field in ("prompt", "revision_prompt", "transfer_prompt"):
            _require_string(task.get(field), f"{prefix}.task.{field}", errors)
        dimensions = task.get("response_dimensions")
        _require_string_list(dimensions, f"{prefix}.task.response_dimensions", errors, nonempty=True)

    feedback = item.get("feedback")
    dimension_ids: set[str] = set()
    if not isinstance(feedback, Mapping):
        errors.append(f"{prefix}.feedback must be an object")
    else:
        dimensions = feedback.get("dimensions")
        if not isinstance(dimensions, list) or not dimensions:
            errors.append(f"{prefix}.feedback.dimensions must be a non-empty array")
        else:
            for dimension_index, dimension in enumerate(dimensions):
                dimension_prefix = f"{prefix}.feedback.dimensions[{dimension_index}]"
                if not isinstance(dimension, Mapping):
                    errors.append(f"{dimension_prefix} must be an object")
                    continue
                dimension_id = dimension.get("id")
                _require_id(dimension_id, f"{dimension_prefix}.id", errors)
                if isinstance(dimension_id, str):
                    if dimension_id in dimension_ids:
                        errors.append(f"duplicate feedback dimension id in {prefix}: {dimension_id}")
                    dimension_ids.add(dimension_id)
                for field in ("label", "rationale", "missing_guidance"):
                    _require_string(dimension.get(field), f"{dimension_prefix}.{field}", errors)
                _require_string_list(
                    dimension.get("required_terms"),
                    f"{dimension_prefix}.required_terms",
                    errors,
                    nonempty=True,
                )
        response_dimensions = task.get("response_dimensions") if isinstance(task, Mapping) else None
        if isinstance(response_dimensions, list) and dimension_ids:
            unknown = sorted(set(response_dimensions) - dimension_ids)
            errors.extend(
                f"{prefix}.task.response_dimensions references unknown dimension: {name}"
                for name in unknown
            )

    item_provenance = item.get("provenance")
    if not isinstance(item_provenance, Mapping):
        errors.append(f"{prefix}.provenance must be an object")
    else:
        for field in ("source", "license"):
            _require_string(item_provenance.get(field), f"{prefix}.provenance.{field}", errors)


def _reject_unsupported_claims(value: Any, errors: list[str], path: str = "bundle") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_path = f"{path}.{key}"
            if _UNSUPPORTED_FIELDS.search(str(key)):
                errors.append(f"unsupported proficiency or score field: {key_path}")
            _reject_unsupported_claims(child, errors, key_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_unsupported_claims(child, errors, f"{path}[{index}]")
    elif isinstance(value, str) and _UNSUPPORTED_TERMS.search(value):
        errors.append(f"unsupported proficiency claim in {path}")


def _require_id(value: Any, path: str, errors: list[str]) -> None:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        errors.append(f"{path} must match ^[a-z0-9][a-z0-9-]{{1,63}}$")


def _require_string(value: Any, path: str, errors: list[str]) -> None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{path} must be a non-empty string")


def _require_string_list(value: Any, path: str, errors: list[str], *, nonempty: bool) -> None:
    if not isinstance(value, list) or (nonempty and not value) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        errors.append(f"{path} must be a {'non-empty ' if nonempty else ''}array of strings")


def _require_relative_path(value: Any, path: str, errors: list[str]) -> None:
    if not isinstance(value, str) or not value.strip() or value.startswith("/") or ".." in value.split("/"):
        errors.append(f"{path} must be a non-empty relative path")
