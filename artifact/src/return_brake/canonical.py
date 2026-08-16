from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_value(value: Any) -> str:
    return sha256_bytes(canonical_bytes(value))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def append_hash_chain(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    chained: list[dict[str, Any]] = []
    previous_hash: str | None = None
    for index, source in enumerate(records):
        record = dict(source)
        record["sequence"] = index
        record["previous_hash"] = previous_hash
        payload = dict(record)
        record_hash = sha256_value(payload)
        record["record_hash"] = record_hash
        chained.append(record)
        previous_hash = record_hash
    return chained


def verify_hash_chain(records: Iterable[dict[str, Any]]) -> tuple[bool, str | None]:
    previous_hash: str | None = None
    for expected_sequence, record in enumerate(records):
        if record.get("sequence") != expected_sequence:
            return False, f"sequence mismatch at {expected_sequence}"
        if record.get("previous_hash") != previous_hash:
            return False, f"previous_hash mismatch at {expected_sequence}"
        payload = dict(record)
        observed_hash = payload.pop("record_hash", None)
        expected_hash = sha256_value(payload)
        if observed_hash != expected_hash:
            return False, f"record_hash mismatch at {expected_sequence}"
        previous_hash = observed_hash
    return True, None
