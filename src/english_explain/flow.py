"""Deterministic learner-facing flow for a validated lesson bundle."""

from __future__ import annotations

from collections.abc import Mapping
import re
from typing import Any

from .schema import LessonValidationError, validate_bundle


def run_lesson(
    bundle: Mapping[str, Any],
    *,
    item_id: str,
    response: str,
    revised_response: str | None = None,
    transfer_response: str | None = None,
) -> dict[str, Any]:
    """Run one inspectable input → produce → feedback → revise → transfer flow.

    Feedback checks are explicit phrase checks declared in the lesson bundle. The
    result contains per-dimension rationale and never collapses the learner path
    into a proficiency claim or an overall score.
    """

    validate_bundle(bundle)
    item = next((candidate for candidate in bundle["items"] if candidate["id"] == item_id), None)
    if item is None:
        raise LessonValidationError((f"unknown item id: {item_id}",))
    if not isinstance(response, str) or not response.strip():
        raise ValueError("response must be a non-empty string")

    initial_feedback = _feedback(item, response)
    steps: list[dict[str, Any]] = [
        {
            "step": "input",
            "context": bundle["context"],
            "segments": item["input"]["segments"],
        },
        {
            "step": "produce",
            "prompt": item["task"]["prompt"],
            "response": response,
        },
        {"step": "feedback", "dimensions": initial_feedback},
    ]

    revision: dict[str, Any] = {
        "step": "revise",
        "prompt": item["task"]["revision_prompt"],
        "status": "pending" if revised_response is None else "submitted",
    }
    if revised_response is not None:
        if not revised_response.strip():
            raise ValueError("revised_response must be non-empty when provided")
        revision["response"] = revised_response
        revision["feedback"] = _feedback(item, revised_response)
    steps.append(revision)

    transfer: dict[str, Any] = {
        "step": "transfer",
        "prompt": item["task"]["transfer_prompt"],
        "status": "pending" if transfer_response is None else "recorded",
    }
    if transfer_response is not None:
        if not transfer_response.strip():
            raise ValueError("transfer_response must be non-empty when provided")
        transfer["response"] = transfer_response
    steps.append(transfer)

    return {
        "lesson_id": bundle["id"],
        "item_id": item_id,
        "steps": steps,
    }


def _feedback(item: Mapping[str, Any], response: str) -> list[dict[str, Any]]:
    normalized = _normalize(response)
    results: list[dict[str, Any]] = []
    for dimension in item["feedback"]["dimensions"]:
        missing = [
            term
            for term in dimension["required_terms"]
            if _normalize(term) not in normalized
        ]
        results.append(
            {
                "id": dimension["id"],
                "label": dimension["label"],
                "status": "met" if not missing else "needs_revision",
                "missing_terms": missing,
                "rationale": dimension["rationale"],
                "guidance": None if not missing else dimension["missing_guidance"],
            }
        )
    return results


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s']", " ", text.casefold())).strip()
