import json
import tempfile
import unittest
from pathlib import Path

from open_receipts.verifier import finalize_receipt, receipt_digest, verify_receipts, load_jsonl


class ReceiptVerifierTests(unittest.TestCase):
    def make_chain(self):
        first = finalize_receipt({
            "seq": 0,
            "prev_sha256": None,
            "event": "model_loaded",
            "model": "example/model",
            "runtime": "local",
        })
        second = finalize_receipt({
            "seq": 1,
            "prev_sha256": first["sha256"],
            "event": "evaluation_completed",
            "status": "observed",
        })
        return [first, second]

    def test_valid_chain(self):
        self.assertEqual(verify_receipts(self.make_chain()), [])

    def test_payload_tamper_is_detected(self):
        chain = self.make_chain()
        chain[1]["status"] = "rewritten"
        errors = verify_receipts(chain)
        self.assertTrue(any("sha256 mismatch" in e for e in errors))

    def test_broken_link_is_detected(self):
        chain = self.make_chain()
        chain[1]["prev_sha256"] = "0" * 64
        chain[1]["sha256"] = receipt_digest(chain[1])
        errors = verify_receipts(chain)
        self.assertTrue(any("prev_sha256" in e for e in errors))

    def test_sequence_gap_is_detected(self):
        chain = self.make_chain()
        chain[1]["seq"] = 3
        chain[1]["sha256"] = receipt_digest(chain[1])
        errors = verify_receipts(chain)
        self.assertTrue(any("expected 1" in e for e in errors))

    def test_jsonl_loader(self):
        chain = self.make_chain()
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "receipts.jsonl"
            path.write_text("\n".join(json.dumps(x) for x in chain) + "\n", encoding="utf-8")
            loaded = load_jsonl(path)
            self.assertEqual(loaded, chain)


if __name__ == "__main__":
    unittest.main()
