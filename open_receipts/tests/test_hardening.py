"""R7 regression tests and explicit demonstrations of the trust boundary."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from open_receipts.verifier import (
    canonical_bytes, finalize_receipt, load_jsonl, main, receipt_digest, verify_receipts,
)


class HardeningTests(unittest.TestCase):
    def chain(self):
        first = finalize_receipt({"seq": 0, "prev_sha256": None, "event": "synthetic_a"})
        second = finalize_receipt({"seq": 1, "prev_sha256": first["sha256"], "event": "synthetic_b"})
        return [first, second]

    def load_text(self, text):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "data.jsonl"
            path.write_text(text, encoding="utf-8")
            return load_jsonl(path)

    def cli(self, text, *args):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "data.jsonl"
            path.write_text(text, encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                return main([str(path), *args])

    def test_empty_chain_rejected(self):
        self.assertTrue(verify_receipts([]))

    def test_boolean_sequence_rejected(self):
        self.assertTrue(verify_receipts([finalize_receipt({"seq": False, "prev_sha256": None})]))

    def test_float_sequence_rejected(self):
        self.assertTrue(verify_receipts([finalize_receipt({"seq": 0.0, "prev_sha256": None})]))

    def test_negative_sequence_rejected(self):
        self.assertTrue(verify_receipts([finalize_receipt({"seq": -1, "prev_sha256": None})]))

    def test_missing_required_fields_rejected(self):
        for field in ("seq", "prev_sha256", "sha256"):
            with self.subTest(field=field):
                obj = self.chain()[0]
                del obj[field]
                if field != "sha256":
                    obj = finalize_receipt(obj)
                self.assertTrue(verify_receipts([obj]))

    def test_malformed_digest_rejected(self):
        for digest in (None, 42, "0" * 63, "A" * 64, "g" * 64):
            with self.subTest(digest=digest):
                obj = self.chain()[0]
                obj["sha256"] = digest
                self.assertTrue(verify_receipts([obj]))

    def test_nonfinite_payload_rejected(self):
        for value in (float("nan"), float("inf"), -float("inf")):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    canonical_bytes({"seq": 0, "prev_sha256": None, "nested": [value]})

    def test_non_json_types_and_nonstring_keys_rejected(self):
        for value in ({1: "key"}, {"value": (1, 2)}, {"value": {1, 2}}):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    canonical_bytes(value)

    def test_duplicate_top_level_keys_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.load_text('{"seq":9,"seq":0}\n')

    def test_duplicate_nested_keys_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.load_text('{"payload":{"value":1,"value":2}}\n')

    def test_nonfinite_json_constants_and_overflow_rejected(self):
        for token in ("NaN", "Infinity", "-Infinity", "1e999"):
            with self.subTest(token=token):
                with self.assertRaises(ValueError):
                    self.load_text('{"value":' + token + '}\n')

    def test_nonobject_jsonl_rejected(self):
        with self.assertRaises(ValueError):
            self.load_text('[]\n')

    def test_unicode_payload_valid(self):
        obj = finalize_receipt({"seq": 0, "prev_sha256": None, "text": "Júnior — humano–IAs"})
        self.assertEqual(verify_receipts([obj]), [])

    def test_whitespace_and_key_order_are_not_byte_integrity(self):
        chain = self.chain()
        text = "\n" + "\n\n".join(json.dumps(dict(reversed(list(x.items())))) for x in chain) + "\n"
        self.assertEqual(verify_receipts(self.load_text(text)), [])

    def test_matching_checkpoint_valid(self):
        chain = self.chain()
        self.assertEqual(verify_receipts(chain, expected_head=chain[-1]["sha256"], expected_count=2), [])

    def test_mismatching_checkpoint_rejected(self):
        self.assertTrue(verify_receipts(self.chain(), expected_head="0" * 64))

    def test_truncation_requires_independent_checkpoint(self):
        chain = self.chain()
        prefix = chain[:1]
        self.assertEqual(verify_receipts(prefix), [])
        self.assertTrue(verify_receipts(prefix, expected_head=chain[-1]["sha256"]))
        self.assertTrue(verify_receipts(prefix, expected_count=2))

    def test_complete_rewrite_requires_independent_checkpoint(self):
        chain = self.chain()
        old_head = chain[-1]["sha256"]
        chain[0] = finalize_receipt({**chain[0], "event": "rewritten"})
        chain[1] = finalize_receipt({**chain[1], "prev_sha256": chain[0]["sha256"]})
        self.assertEqual(verify_receipts(chain), [])
        self.assertTrue(verify_receipts(chain, expected_head=old_head))

    def test_expected_count_mismatch_rejected(self):
        self.assertTrue(verify_receipts(self.chain(), expected_count=3))

    def test_invalid_checkpoint_configuration_rejected(self):
        for params in ({"expected_head": "bad"}, {"expected_count": False}, {"expected_count": 0}):
            with self.subTest(params=params):
                with self.assertRaises(ValueError):
                    verify_receipts(self.chain(), **params)

    def test_cli_valid_checkpoint_exit_zero(self):
        chain = self.chain()
        text = "\n".join(json.dumps(x) for x in chain)
        self.assertEqual(self.cli(text, "--expected-head", chain[-1]["sha256"], "--expected-count", "2"), 0)

    def test_cli_empty_exit_one(self):
        self.assertEqual(self.cli("\n"), 1)

    def test_cli_malformed_exit_two(self):
        self.assertEqual(self.cli("not JSON\n"), 2)

    def test_cli_invalid_utf8_exit_two(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "invalid.jsonl"
            path.write_bytes(b"\xff\n")
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main([str(path)]), 2)

    def test_cli_missing_file_exit_two(self):
        with tempfile.TemporaryDirectory() as td, contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main([str(Path(td) / "missing.jsonl")]), 2)

    def test_surrogate_payload_rejected_without_crash(self):
        obj = {"seq": 0, "prev_sha256": None, "text": "\ud800", "sha256": "0" * 64}
        self.assertTrue(verify_receipts([obj]))

    def test_nonobject_receipt_rejected(self):
        self.assertTrue(verify_receipts([None]))

    def test_invalid_initial_link_rejected(self):
        obj = finalize_receipt({"seq": 0, "prev_sha256": "0" * 64})
        self.assertTrue(verify_receipts([obj]))


if __name__ == "__main__":
    unittest.main()
