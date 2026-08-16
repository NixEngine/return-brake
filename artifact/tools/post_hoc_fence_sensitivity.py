"""Post-hoc sensitivity analysis for one observed serialization symptom.

This script does not modify the preregistered parser or primary run artifacts. It
removes at most one complete outer Markdown JSON fence, reuses the frozen parser,
and prints a counterfactual analysis to stdout.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from return_brake.analysis import analyze_records
from return_brake.protocol import HARNESS_INVALID, parse_model_text


OUTER_JSON_FENCE = re.compile(
    r"\A\s*```(?:json)?\s*\r?\n(?P<body>.*)\r?\n```\s*\Z",
    flags=re.IGNORECASE | re.DOTALL,
)


def load_records(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def apply_sensitivity(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    revised = copy.deepcopy(records)
    changes: list[dict[str, Any]] = []
    for record in revised:
        if not (
            record.get("choice") == HARNESS_INVALID
            and record.get("symptom") == "json_parse:JSONDecodeError"
        ):
            continue
        model_text = record.get("model_text")
        if not isinstance(model_text, str):
            continue
        match = OUTER_JSON_FENCE.fullmatch(model_text)
        if match is None:
            continue
        parsed = parse_model_text(match.group("body"))
        if parsed.symptom is not None:
            continue
        before = record["choice"]
        record["choice"] = parsed.choice
        record["parsed"] = parsed.parsed
        record["parser_candidate_choice"] = parsed.choice
        record["symptom"] = None
        record["valid_observation"] = record.get("exit_code") == 0
        changes.append(
            {
                "call_id": record["call_id"],
                "card_id": record["card_id"],
                "frame": record["frame"],
                "method": record["method"],
                "stage": record.get("stage"),
                "before": before,
                "after": parsed.choice,
                "transformation": "strip_one_complete_outer_markdown_json_fence",
            }
        )
    return revised, changes


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("observations", type=Path)
    args = parser.parse_args()

    original = load_records(args.observations)
    revised, changes = apply_sensitivity(original)
    original_invalid = [r for r in original if r.get("choice") == HARNESS_INVALID]
    remaining_invalid = [r for r in revised if r.get("choice") == HARNESS_INVALID]

    result = {
        "schema_version": "return-brake.post-hoc-fence-sensitivity.v1",
        "status": "POST_HOC_NON_PRIMARY",
        "transformation": "strip exactly one complete outer Markdown JSON fence only from primary JSON parse symptoms",
        "primary_artifacts_modified": False,
        "original_record_count": len(original),
        "original_invalid_count": len(original_invalid),
        "original_invalid_by_frame": dict(Counter(r["frame"] for r in original_invalid)),
        "reclassified_count": len(changes),
        "reclassified_by_frame": dict(Counter(r["frame"] for r in changes)),
        "remaining_invalid_count": len(remaining_invalid),
        "changes": changes,
        "counterfactual_analysis": analyze_records(revised),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
