from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from return_brake.canonical import sha256_file, verify_hash_chain  # noqa: E402


PUBLIC_FIELDS = (
    "sequence",
    "call_id",
    "card_id",
    "frame",
    "method",
    "stage",
    "choice",
    "parser_candidate_choice",
    "valid_observation",
    "symptom",
    "prompt_sha256",
    "raw_private_sha256",
    "previous_hash",
    "record_hash",
)
FORBIDDEN_FIELDS = {
    "model_text",
    "prompt",
    "parsed",
    "basis",
    "return_condition",
}


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build(source: Path, output: Path, manifest: Path) -> None:
    records = read_jsonl(source)
    ok, problem = verify_hash_chain(records)
    if not ok:
        raise SystemExit(problem or "source receipt chain is invalid")

    commitments = [{key: record.get(key) for key in PUBLIC_FIELDS} for record in records]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "".join(json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for record in commitments),
        encoding="utf-8",
    )
    write_json(
        manifest,
        {
            "schema": "return-brake-public-original-commitments-v1",
            "source_observations_sha256": sha256_file(source),
            "source_record_count": len(records),
            "source_receipt_chain_head": records[-1]["record_hash"] if records else None,
            "public_fields": list(PUBLIC_FIELDS),
            "withheld_fields_include": sorted(FORBIDDEN_FIELDS),
            "commitments_file": output.name,
            "commitments_sha256": sha256_file(output),
        },
    )


def verify(commitments_path: Path, manifest_path: Path) -> tuple[bool, list[str]]:
    problems: list[str] = []
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    records = read_jsonl(commitments_path)
    if manifest.get("schema") != "return-brake-public-original-commitments-v1":
        problems.append("unexpected manifest schema")
    if manifest.get("commitments_sha256") != sha256_file(commitments_path):
        problems.append("commitments file hash mismatch")
    if manifest.get("source_record_count") != len(records):
        problems.append("record count mismatch")
    expected_keys = set(PUBLIC_FIELDS)
    for index, record in enumerate(records):
        if set(record) != expected_keys:
            problems.append(f"field set mismatch at record {index}")
        if set(record) & FORBIDDEN_FIELDS:
            problems.append(f"withheld field exposed at record {index}")
        if index == 0 and record.get("previous_hash") is not None:
            problems.append("first previous_hash must be null")
        if index and record.get("previous_hash") != records[index - 1].get("record_hash"):
            problems.append(f"receipt link mismatch at record {index}")
    head = records[-1].get("record_hash") if records else None
    if manifest.get("source_receipt_chain_head") != head:
        problems.append("receipt-chain head mismatch")
    return not problems, problems


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    build_parser = sub.add_parser("build")
    build_parser.add_argument("source", type=Path)
    build_parser.add_argument("output", type=Path)
    build_parser.add_argument("manifest", type=Path)
    verify_parser = sub.add_parser("verify")
    verify_parser.add_argument("commitments", type=Path)
    verify_parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    if args.command == "build":
        build(args.source, args.output, args.manifest)
        ok, problems = verify(args.output, args.manifest)
    else:
        ok, problems = verify(args.commitments, args.manifest)
    print(json.dumps({"ok": ok, "problems": problems}, ensure_ascii=False, indent=2))
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
