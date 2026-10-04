"""Command-line entry point for offline validation and learner flows."""

from __future__ import annotations

import argparse
import json
from typing import Sequence

from .flow import run_lesson
from .schema import LessonValidationError, load_bundle


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="english-explain")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="validate a lesson bundle")
    validate_parser.add_argument("lesson")

    run_parser = subparsers.add_parser("run", help="run one offline learner flow")
    run_parser.add_argument("lesson")
    run_parser.add_argument("--item", required=True)
    run_parser.add_argument("--response", required=True)
    run_parser.add_argument("--revised-response")
    run_parser.add_argument("--transfer-response")

    args = parser.parse_args(argv)
    try:
        bundle = load_bundle(args.lesson)
        if args.command == "validate":
            print(json.dumps({"status": "valid", "lesson_id": bundle["id"]}, sort_keys=True))
        else:
            result = run_lesson(
                bundle,
                item_id=args.item,
                response=args.response,
                revised_response=args.revised_response,
                transfer_response=args.transfer_response,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
    except (LessonValidationError, ValueError) as exc:
        parser.error(str(exc))
    return 0
