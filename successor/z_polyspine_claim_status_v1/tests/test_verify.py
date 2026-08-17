from __future__ import annotations

import copy
import importlib.util
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "verify.py"
SPEC = importlib.util.spec_from_file_location("zpoly_claim_status_verify", MODULE_PATH)
assert SPEC and SPEC.loader
VERIFY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFY)


class ClaimStatusSuccessorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parents[3]

    def test_valid_frozen_baseline_verifies(self) -> None:
        result = VERIFY.verify_repository(self.root, git_history=False)
        self.assertTrue(result["ok"], result["errors"])
        self.assertEqual(
            "p2-f02",
            result["details"]["successor_links"]["basis_finding_id"],
        )
        self.assertEqual(
            ["predicate", "status"],
            result["details"]["frozen_baseline"]["immutable_type_fields"],
        )

    def test_exact_predicate_and_status_laundering_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            clone = Path(directory) / "repo"
            subprocess.run(
                [
                    "git",
                    "clone",
                    "--quiet",
                    "--no-local",
                    "--branch",
                    "successor/z-polyspine-claim-status-v1",
                    str(self.root),
                    str(clone),
                ],
                check=True,
                capture_output=True,
            )
            contract_source = self.root / VERIFY.CONTRACT_PATH
            contract_target = clone / VERIFY.CONTRACT_PATH
            contract_target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(contract_source, contract_target)

            protocol_path = clone / "successor/z_polyspine/CONTRIBUTION_PROTOCOL.json"
            protocol = VERIFY.BASE_VERIFY.load_json(protocol_path)
            target = next(
                claim
                for claim in protocol["baseline_claims"]
                if claim["id"] == "participant-no-formal-technical-education"
            )
            self.assertEqual(
                ("BOUNDED_PARTICIPANT_INFERENCE", "INFERRED"),
                (target["predicate"], target["status"]),
            )
            original_statement = target["statement"]
            original_evidence = copy.deepcopy(target["evidence_refs"])
            target["predicate"] = "VERIFIER_BEHAVIOR"
            target["status"] = "OBSERVED"
            self.assertEqual(original_statement, target["statement"])
            self.assertEqual(original_evidence, target["evidence_refs"])
            protocol_path.write_text(
                json.dumps(protocol, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            snapshot_path = clone / "successor/z_polyspine/P0_SNAPSHOT.json"
            snapshot = VERIFY.BASE_VERIFY.load_json(snapshot_path)
            entry = snapshot["files"]["successor/z_polyspine/CONTRIBUTION_PROTOCOL.json"]
            entry["bytes"] = protocol_path.stat().st_size
            entry["sha256"] = VERIFY.BASE_VERIFY.digest_file(protocol_path)
            snapshot_path.write_text(
                json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            frozen_result = VERIFY.BASE_VERIFY.verify_repository(clone, git_history=False)
            self.assertTrue(frozen_result["ok"], frozen_result["errors"])
            successor_result = VERIFY.verify_repository(clone, git_history=False)
            self.assertFalse(successor_result["ok"])
            errors = [
                item
                for item in successor_result["errors"]
                if item["code"] == "FROZEN_BASELINE_CLAIM_TYPE_MISMATCH"
            ]
            self.assertEqual(1, len(errors), successor_result["errors"])
            self.assertIn("BOUNDED_PARTICIPANT_INFERENCE", errors[0]["message"])
            self.assertIn("VERIFIER_BEHAVIOR", errors[0]["message"])
            self.assertIn("INFERRED", errors[0]["message"])
            self.assertIn("OBSERVED", errors[0]["message"])

    def test_valid_observed_verifier_behavior_pair_remains_allowed(self) -> None:
        errors: list[dict[str, str]] = []
        VERIFY.BASE_VERIFY.verify_claims(
            [
                {
                    "id": "verifier-exit-observation",
                    "predicate": "VERIFIER_BEHAVIOR",
                    "status": "OBSERVED",
                    "statement": "The verifier returned exit code zero for this bounded execution.",
                    "evidence_refs": ["successor/z_polyspine/README.md"],
                }
            ],
            "fixture",
            errors,
        )
        self.assertEqual([], errors)


if __name__ == "__main__":
    unittest.main()
