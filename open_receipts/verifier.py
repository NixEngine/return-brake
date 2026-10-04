#!/usr/bin/env python3
"""Check JSONL receipt-chain consistency, optionally against a trusted checkpoint.

R7 hardening of the clean R6 component. Standard library only.
This is not a signature, an append-only storage system, or proof of real events.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any, Iterable

CANONICAL_SEPARATORS = (",", ":")
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")


def _check_json_value(value: Any) -> None:
    """Require JSON-native types, string keys and finite numbers."""
    if value is None or type(value) in (str, bool, int):
        return
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError("non-finite number")
        return
    if type(value) is list:
        for item in value:
            _check_json_value(item)
        return
    if type(value) is dict:
        for key, item in value.items():
            if type(key) is not str:
                raise ValueError("JSON object keys must be strings")
            _check_json_value(item)
        return
    raise ValueError("value is not a JSON-native type")


def canonical_bytes(receipt: dict[str, Any]) -> bytes:
    """UTF-8 compact sorted-key Python JSON, excluding only top-level sha256.

    This profile is NOT RFC 8785/JCS; do not assume cross-language numeric
    equivalence or preservation of the original JSONL whitespace/key order.
    """
    if type(receipt) is not dict:
        raise ValueError("receipt must be a JSON object")
    material = dict(receipt)
    material.pop("sha256", None)
    _check_json_value(material)
    return json.dumps(
        material, ensure_ascii=False, sort_keys=True, allow_nan=False,
        separators=CANONICAL_SEPARATORS,
    ).encode("utf-8")


def receipt_digest(receipt: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_bytes(receipt)).hexdigest()


def finalize_receipt(receipt: dict[str, Any]) -> dict[str, Any]:
    """Return a hashed copy; schema validity is checked by verify_receipts."""
    digest = receipt_digest(receipt)
    return {**receipt, "sha256": digest}


def _is_digest(value: Any) -> bool:
    return type(value) is str and _DIGEST.fullmatch(value) is not None


def verify_receipts(
    receipts: Iterable[dict[str, Any]], *,
    expected_head: str | None = None, expected_count: int | None = None,
) -> list[str]:
    """Return errors; [] means consistency, not authenticity or completeness.

    Optional checkpoints must be obtained independently of the input file.
    Record indexes count nonblank JSONL records, not physical file lines.
    """
    if expected_head is not None and not _is_digest(expected_head):
        raise ValueError("expected_head must be 64 lowercase hexadecimal characters")
    if expected_count is not None and (
        type(expected_count) is not int or expected_count < 1
    ):
        raise ValueError("expected_count must be a positive integer")

    errors: list[str] = []
    previous_digest: str | None = None
    count = 0
    for index, receipt in enumerate(receipts, start=1):
        count = index
        prefix = f"record {index}: "
        if type(receipt) is not dict:
            errors.append(prefix + "receipt must be a JSON object")
            previous_digest = None
            continue
        for field in ("seq", "prev_sha256", "sha256"):
            if field not in receipt:
                errors.append(prefix + f"missing required field {field}")
        seq = receipt.get("seq")
        if type(seq) is not int or seq != index - 1:
            errors.append(prefix + f"seq={seq!r}; expected {index - 1} (integer, not bool)")
        declared = receipt.get("sha256")
        if not _is_digest(declared):
            errors.append(prefix + "sha256 must be 64 lowercase hexadecimal characters")
        try:
            computed = receipt_digest(receipt)
        except (ValueError, TypeError, UnicodeError, RecursionError) as exc:
            errors.append(prefix + f"payload cannot be canonicalized ({type(exc).__name__})")
            computed = None
        if declared != computed or computed is None:
            errors.append(prefix + "sha256 mismatch")
        prev = receipt.get("prev_sha256")
        if index == 1:
            if prev is not None and prev != "":
                errors.append(prefix + "first prev_sha256 must be null or empty")
        elif not _is_digest(prev) or prev != previous_digest:
            errors.append(prefix + "prev_sha256 does not match preceding digest")
        previous_digest = computed

    if count == 0:
        errors.append("empty receipt chain")
    if expected_count is not None and count != expected_count:
        errors.append(f"receipt count {count}; expected {expected_count}")
    if expected_head is not None and previous_digest != expected_head:
        errors.append("final digest does not match trusted expected_head")
    return errors


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    obj: dict[str, Any] = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError("duplicate JSON object key")
        obj[key] = value
    return obj


def _reject_constant(value: str) -> None:
    raise ValueError("non-finite JSON constant")


def _finite_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError("JSON number exceeds finite float range")
    return parsed


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    """Load strict JSON objects; blank physical lines are ignored."""
    receipts: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for lineno, raw in enumerate(handle, start=1):
            if not raw.strip():
                continue
            try:
                obj = json.loads(
                    raw, object_pairs_hook=_unique_object,
                    parse_constant=_reject_constant, parse_float=_finite_float,
                )
            except (ValueError, RecursionError) as exc:
                raise ValueError(f"line {lineno}: invalid JSON: {exc}") from exc
            if type(obj) is not dict:
                raise ValueError(f"line {lineno}: expected a JSON object")
            receipts.append(obj)
    return receipts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check JSONL receipt-chain consistency.")
    parser.add_argument("jsonl", type=Path, help="path to receipt JSONL")
    parser.add_argument("--expected-head", help="independently trusted final SHA-256")
    parser.add_argument("--expected-count", type=int, help="independently trusted record count")
    args = parser.parse_args(argv)
    try:
        receipts = load_jsonl(args.jsonl)
        errors = verify_receipts(
            receipts, expected_head=args.expected_head, expected_count=args.expected_count,
        )
    except (OSError, ValueError, UnicodeError, RecursionError) as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 2
    if errors:
        print("INVALID")
        for err in errors:
            print(f"- {err}")
        return 1
    print(f"VALID receipts={len(receipts)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
