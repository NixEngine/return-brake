from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "verify.py"
SPEC = importlib.util.spec_from_file_location("zpoly_verify", MODULE_PATH)
assert SPEC and SPEC.loader
VERIFY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFY)


class ProtocolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parents[3]
        self.catalog = VERIFY.load_json(
            self.root / "successor/z_polyspine/vectors/catalog.json"
        )

    def test_local_snapshot_verifies(self) -> None:
        result = VERIFY.verify_repository(self.root, git_history=False)
        self.assertTrue(result["ok"], result["errors"])

    def test_selection_is_deterministic_and_unique(self) -> None:
        randomness = "12" * 32
        first = VERIFY.select_candidates(randomness, self.catalog, 3)
        second = VERIFY.select_candidates(randomness, self.catalog, 3)
        self.assertEqual(first, second)
        self.assertEqual(3, len({item["id"] for item in first}))

    def test_selection_rejects_noncanonical_randomness(self) -> None:
        with self.assertRaises(ValueError):
            VERIFY.select_candidates("AA" * 32, self.catalog, 3)

    def test_surface_replay_is_deterministic_and_closed(self) -> None:
        surface = "claim_status_boundaries"
        first = VERIFY.replay_surface(surface, self.catalog)
        second = VERIFY.replay_surface(surface, self.catalog)
        self.assertEqual(first, second)
        self.assertEqual(
            [
                "python",
                "successor/z_polyspine/verify.py",
                "replay",
                "--surface",
                surface,
            ],
            VERIFY.expected_replay_command(surface),
        )

    def test_duplicate_json_key_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "duplicate.json"
            path.write_text('{"a":1,"a":2}', encoding="utf-8")
            with self.assertRaises(VERIFY.DuplicateKeyError):
                VERIFY.load_json(path)

    def test_float_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "float.json"
            path.write_text('{"a":1.25}', encoding="utf-8")
            with self.assertRaises(ValueError):
                VERIFY.load_json(path)

    def test_unsafe_paths_are_rejected(self) -> None:
        for value in ("../x", "/absolute", "C:/drive", "a\\b", "a/./b"):
            self.assertFalse(VERIFY.safe_relative(value), value)

    def test_recursive_private_key_is_rejected(self) -> None:
        errors: list[dict[str, str]] = []
        VERIFY._walk({"outer": {"private_payload": "x"}}, "fixture", errors)
        self.assertIn("PRIVATE_KEY_FORBIDDEN", {item["code"] for item in errors})

    def test_claim_promotion_without_known_status_is_rejected(self) -> None:
        errors: list[dict[str, str]] = []
        VERIFY.verify_claims(
            [{"id": "x", "status": "CERTAIN", "statement": "overclaim"}],
            "fixture",
            errors,
        )
        self.assertIn("CLAIM_STATUS_INVALID", {item["code"] for item in errors})

    def test_observed_ontological_overclaim_is_rejected(self) -> None:
        errors: list[dict[str, str]] = []
        VERIFY.verify_claims(
            [
                {
                    "id": "x",
                    "predicate": "VERIFIER_BEHAVIOR",
                    "status": "OBSERVED_IN_SESSION",
                    "statement": "The model has a mind.",
                    "evidence_refs": ["successor/z_polyspine/README.md"],
                }
            ],
            "fixture",
            errors,
        )
        self.assertIn(
            "CLAIM_OUTSIDE_OBSERVABLE_BOUNDARY",
            {item["code"] for item in errors},
        )

    def test_empty_public_receipt_is_rejected(self) -> None:
        errors: list[dict[str, str]] = []
        VERIFY.verify_receipt(
            {},
            "a" * 40,
            "b" * 40,
            "refs/heads/successor/z-polyspine-demonstration-v1",
            errors,
            remote=False,
        )
        codes = {item["code"] for item in errors}
        self.assertIn("PUBLIC_RECEIPT_FIELD_MISMATCH", codes)
        self.assertIn("PUBLIC_RECEIPT_EVENT_ID_INVALID", codes)

    def test_public_receipt_requires_exact_before_commit(self) -> None:
        errors: list[dict[str, str]] = []
        receipt = {
            "provider": "github_repository_events",
            "collection_url": "https://api.github.com/repos/NixEngine/return-brake/events",
            "event_id": "123",
            "event_type": "PushEvent",
            "repository": "NixEngine/return-brake",
            "ref": "refs/heads/successor/z-polyspine-demonstration-v1",
            "before_sha": "c" * 40,
            "head_sha": "a" * 40,
            "created_at_utc": "2026-08-17T03:00:00Z",
        }
        VERIFY.verify_receipt(
            receipt,
            "a" * 40,
            "b" * 40,
            "refs/heads/successor/z-polyspine-demonstration-v1",
            errors,
            remote=False,
        )
        self.assertIn(
            "PUBLIC_RECEIPT_FIELD_MISMATCH",
            {item["code"] for item in errors},
        )

    def test_phase_rejects_free_form_top_level_field(self) -> None:
        record = VERIFY.load_json(
            self.root / "successor/z_polyspine/phases/P0/record.json"
        )
        record["notes"] = "free form"
        errors: list[dict[str, str]] = []
        VERIFY.verify_phase_common(record, 0, self.root, errors)
        self.assertIn(
            "PHASE_FIELD_FORBIDDEN",
            {item["code"] for item in errors},
        )

    def test_later_phase_rejects_free_form_claims(self) -> None:
        record = VERIFY.load_json(
            self.root / "successor/z_polyspine/phases/P0/record.json"
        )
        record.update(
            {
                "phase_id": "P1",
                "sequence": 1,
                "kind": "BEACON_SELECTION",
                "retains_phase_ids": ["P0"],
            }
        )
        errors: list[dict[str, str]] = []
        VERIFY.verify_phase_common(record, 1, self.root, errors)
        self.assertIn(
            "LATER_PHASE_CLAIMS_FORBIDDEN",
            {item["code"] for item in errors},
        )

    def test_empty_p1_semantics_are_rejected(self) -> None:
        errors: list[dict[str, str]] = []
        p0 = {
            "schema": VERIFY.PHASE_SCHEMA,
            "phase_id": "P0",
            "sequence": 0,
            "kind": "PREREGISTRATION",
            "spines": ["a", "b"],
            "retains_phase_ids": [],
            "contributions": [],
            "claims": [],
        }
        VERIFY.verify_phase_semantics(
            [p0, {}], self.root, {}, errors, remote=False
        )
        codes = {item["code"] for item in errors}
        self.assertIn("PHASE_FIELD_MISSING", codes)
        self.assertIn("BEACON_MISSING", codes)


if __name__ == "__main__":
    unittest.main()
