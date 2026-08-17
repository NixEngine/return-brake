from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "verify.py"
SPEC = importlib.util.spec_from_file_location("zpoly_contribution_roles_verify", MODULE_PATH)
assert SPEC and SPEC.loader
VERIFY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFY)


class ContributionRoleSuccessorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parents[3]
        self.parent = VERIFY.load_parent_verifier(self.root)

    def test_valid_frozen_baseline_verifies(self) -> None:
        result = VERIFY.verify_repository(self.root)
        self.assertTrue(result["ok"], result["errors"])
        self.assertEqual(VERIFY.PARENT_P3_COMMIT, result["details"]["parent_commit"])
        self.assertEqual(["P0", "P1", "P2", "P3"], result["details"]["phase_records_checked"])

    def test_complete_family_with_separated_principals_is_valid(self) -> None:
        record = self._attack_record()
        record["contributions"][2]["principal"] = "codex-session"
        errors: list[dict[str, str]] = []
        VERIFY.verify_material_role_separation(
            record,
            {"junior", "codex-session", "local-tools", "public-platforms"},
            errors,
        )
        self.assertNotIn(VERIFY.ERROR_CODE, {item["code"] for item in errors})

    def test_p2_f03_dummy_verification_bypass_is_rejected_after_rehash(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary_root = Path(directory)
            shutil.copytree(
                self.root / "successor/z_polyspine",
                temporary_root / "successor/z_polyspine",
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
            )
            successor_root = temporary_root / "successor/z_polyspine_contribution_roles_v1"
            successor_root.mkdir(parents=True)
            shutil.copy2(
                self.root / VERIFY.CONTRACT_PATH,
                successor_root / "CONTRACT.json",
            )

            record_path = temporary_root / "successor/z_polyspine/phases/P0/record.json"
            record = self.parent.load_json(record_path)
            record["contributions"] = self._attack_record()["contributions"]
            record_path.write_text(
                json.dumps(record, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            snapshot_path = temporary_root / "successor/z_polyspine/P0_SNAPSHOT.json"
            snapshot = self.parent.load_json(snapshot_path)
            relative = "successor/z_polyspine/phases/P0/record.json"
            snapshot["files"][relative] = {
                "sha256": hashlib.sha256(record_path.read_bytes()).hexdigest(),
                "bytes": record_path.stat().st_size,
            }
            snapshot_path.write_text(
                json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            frozen_result = VERIFY.load_parent_verifier(temporary_root).verify_repository(
                temporary_root, git_history=False
            )
            self.assertTrue(frozen_result["ok"], frozen_result["errors"])

            successor_result = VERIFY.verify_repository(temporary_root)
            self.assertFalse(successor_result["ok"])
            errors = [
                item
                for item in successor_result["errors"]
                if item["code"] == VERIFY.ERROR_CODE
            ]
            self.assertEqual(1, len(errors), successor_result["errors"])
            self.assertIn("other roles do not count", errors[0]["message"])

    @staticmethod
    def _attack_record() -> dict[str, object]:
        evidence = ["successor/z_polyspine/CONTRIBUTION_PROTOCOL.json"]
        roles = [
            "CONCEPTION",
            "AUTHENTICATION",
            "COMMAND_DISPATCH",
            "PROCESS_EXECUTION",
            "PUBLICATION_INITIATION",
        ]
        contributions = [
            {
                "principal": "junior",
                "role": role,
                "status": "OBSERVED_IN_SESSION",
                "evidence_refs": evidence,
            }
            for role in roles
        ]
        contributions.append(
            {
                "principal": "local-tools",
                "role": "VERIFICATION",
                "status": "OBSERVED_IN_SESSION",
                "evidence_refs": evidence,
            }
        )
        return {
            "phase_id": "P0",
            "contributions": contributions,
        }


if __name__ == "__main__":
    unittest.main()
