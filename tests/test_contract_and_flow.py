from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from english_explain.flow import run_lesson
from english_explain.schema import LessonValidationError, load_bundle, validate_bundle


ROOT = Path(__file__).parents[1]
FIXTURES = ROOT / "fixtures"


@pytest.mark.parametrize("name", ["sentence-structure.json", "dialogue-repair.json"])
def test_fixtures_validate_offline(name: str) -> None:
    bundle = load_bundle(FIXTURES / name)
    validate_bundle(bundle)


def test_text_and_audio_segments_keep_stable_ids() -> None:
    bundle = load_bundle(FIXTURES / "dialogue-repair.json")
    segments = bundle["items"][0]["input"]["segments"]
    assert [segment["id"] for segment in segments] == ["turn-a", "turn-b"]
    assert all(segment.get("audio") for segment in segments)
    assert all(segment["text"] for segment in segments)


def test_flow_exposes_feedback_revision_and_transfer_without_a_score() -> None:
    bundle = load_bundle(FIXTURES / "dialogue-repair.json")
    result = run_lesson(
        bundle,
        item_id="clarification-1",
        response="Sorry, could you repeat that?",
        revised_response="Sorry, could you say that again?",
        transfer_response="Sorry, could you say the platform number again?",
    )

    assert [step["step"] for step in result["steps"]] == [
        "input",
        "produce",
        "feedback",
        "revise",
        "transfer",
    ]
    feedback = result["steps"][2]["dimensions"]
    assert [dimension["status"] for dimension in feedback] == ["met", "needs_revision"]
    revised_feedback = result["steps"][3]["feedback"]
    assert all(dimension["status"] == "met" for dimension in revised_feedback)
    assert "score" not in json.dumps(result).casefold()
    assert "proficiency" not in json.dumps(result).casefold()


def test_flow_output_is_deterministic() -> None:
    bundle = load_bundle(FIXTURES / "sentence-structure.json")
    kwargs = {
        "item_id": "counterfactual-1",
        "response": "If I had known, I would have called.",
        "revised_response": "If I had known earlier, I would have called you.",
        "transfer_response": "If I had seen the warning, I would have stopped.",
    }
    assert run_lesson(bundle, **kwargs) == run_lesson(copy.deepcopy(bundle), **kwargs)


def test_unsupported_proficiency_claim_is_rejected() -> None:
    bundle = load_bundle(FIXTURES / "sentence-structure.json")
    invalid = copy.deepcopy(bundle)
    invalid["items"][0]["proficiency_score"] = 1
    with pytest.raises(LessonValidationError, match="unsupported proficiency"):
        validate_bundle(invalid)
