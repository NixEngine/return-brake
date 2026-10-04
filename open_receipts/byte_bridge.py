"""Source -> transformation -> output commitments, from the PowerBI antecedent.

R9 is a new adapter, not a reimplementation of the complete PowerBI pipeline.
No network, dynamic code execution, or source embedding without explicit opt-in.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

from .verifier import _check_json_value, _finite_float, _reject_constant, _unique_object

SCHEMA = "open_receipts.byte_bridge/1"
MAX_BYTES = 16 * 1024 * 1024
MODES = ("identity-v1", "utf8-lf-v1", "json-object-sorted-v1", "declared-only-v1")
FIELDS = {
    "schema", "SHA256Fonte", "SHA256Saida", "TamanhoFonteBytes", "TamanhoSaidaBytes",
    "ModoSaida", "OriginalReversivelIncluido",
}


def _limit(max_bytes: int) -> None:
    if type(max_bytes) is not int or max_bytes < 1:
        raise ValueError("max_bytes must be a positive integer")


def _bytes(value: bytes, max_bytes: int) -> None:
    _limit(max_bytes)
    if type(value) is not bytes or len(value) > max_bytes:
        raise ValueError("expected bytes within the configured size limit")


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def read_bounded(path: Path, max_bytes: int = MAX_BYTES) -> bytes:
    """Read at most limit+1 bytes. Paths are supplied by the caller, not records."""
    _limit(max_bytes)
    with path.open("rb") as stream:
        data = stream.read(max_bytes + 1)
    _bytes(data, max_bytes)
    return data


def load_record(data: bytes, max_bytes: int = MAX_BYTES) -> dict[str, Any]:
    """Parse strict JSON. Size includes the possible base64-encoded original."""
    _bytes(data, max_bytes * 2 + 65536)
    obj = json.loads(data.decode("utf-8"), object_pairs_hook=_unique_object,
                     parse_constant=_reject_constant, parse_float=_finite_float)
    _validate(obj, max_bytes)
    return obj


def transform(source: bytes, mode: str, max_bytes: int = MAX_BYTES) -> bytes:
    """Replay a fixed local operation; never interpret a supplied command."""
    _bytes(source, max_bytes)
    if mode == "identity-v1":
        output = source
    elif mode == "utf8-lf-v1":
        output = source.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
    elif mode == "json-object-sorted-v1":
        obj = json.loads(source.decode("utf-8"), object_pairs_hook=_unique_object,
                         parse_constant=_reject_constant, parse_float=_finite_float)
        if type(obj) is not dict:
            raise ValueError("normalization requires a JSON object")
        _check_json_value(obj)
        # Unlike receipt canonicalization, preserve ALL keys, including sha256.
        output = json.dumps(obj, ensure_ascii=False, sort_keys=True,
                            allow_nan=False, separators=(",", ":")).encode("utf-8")
    else:
        raise ValueError("mode has no implemented replay")
    _bytes(output, max_bytes)
    return output


def _validate(record: Any, max_bytes: int) -> None:
    _limit(max_bytes)
    if type(record) is not dict:
        raise ValueError("record must be an object")
    if record.get("schema") != SCHEMA:
        raise ValueError("unsupported schema")
    if type(record.get("OriginalReversivelIncluido")) is not bool:
        raise ValueError("OriginalReversivelIncluido must be boolean")
    expected = FIELDS | ({"OriginalBase64"} if record["OriginalReversivelIncluido"] else set())
    if set(record) != expected:
        raise ValueError("missing or unsupported record fields")
    if record["ModoSaida"] not in MODES:
        raise ValueError("unsupported ModoSaida")
    for key in ("SHA256Fonte", "SHA256Saida"):
        if type(record[key]) is not str or re.fullmatch(r"[0-9a-f]{64}", record[key]) is None:
            raise ValueError("digest must be 64 lowercase hexadecimal characters")
    for key in ("TamanhoFonteBytes", "TamanhoSaidaBytes"):
        if type(record[key]) is not int or not 0 <= record[key] <= max_bytes:
            raise ValueError("size must be a nonnegative integer within limit, not bool")
    if record["OriginalReversivelIncluido"]:
        encoded = record["OriginalBase64"]
        if type(encoded) is not str or len(encoded) != 4 * ((record["TamanhoFonteBytes"] + 2) // 3):
            raise ValueError("base64 length inconsistent with original size")


def capture(source: bytes, output: bytes, mode: str, *, include_original: bool = False,
            max_bytes: int = MAX_BYTES) -> dict[str, Any]:
    """Commit both byte streams. Default contains hashes/sizes, not file content."""
    _bytes(source, max_bytes)
    _bytes(output, max_bytes)
    if type(include_original) is not bool or mode not in MODES:
        raise ValueError("invalid capture configuration")
    if mode != "declared-only-v1" and transform(source, mode, max_bytes) != output:
        raise ValueError("supplied output does not match replay")
    record: dict[str, Any] = {
        "schema": SCHEMA, "SHA256Fonte": _sha(source), "SHA256Saida": _sha(output),
        "TamanhoFonteBytes": len(source), "TamanhoSaidaBytes": len(output),
        "ModoSaida": mode, "OriginalReversivelIncluido": include_original,
    }
    if include_original:
        record["OriginalBase64"] = base64.b64encode(source).decode("ascii")
    return record


def restore_original(record: dict[str, Any], max_bytes: int = MAX_BYTES) -> bytes:
    """Restore retained bytes, not an inverse of a lossy transformation."""
    _validate(record, max_bytes)
    if not record["OriginalReversivelIncluido"]:
        raise ValueError("original not included; a digest cannot reconstruct it")
    encoded = record["OriginalBase64"]
    raw = base64.b64decode(encoded, validate=True)
    if base64.b64encode(raw).decode("ascii") != encoded:
        raise ValueError("noncanonical base64")
    if len(raw) != record["TamanhoFonteBytes"] or _sha(raw) != record["SHA256Fonte"]:
        raise ValueError("restored original does not match commitment")
    return raw


def verify(record: dict[str, Any], *, source: bytes | None = None,
           output: bytes | None = None, max_bytes: int = MAX_BYTES) -> dict[str, str]:
    """Separate missing evidence from mismatch. No event/authorship attestation."""
    _validate(record, max_bytes)
    result = {"source_bytes": "NOT_CHECKED", "output_bytes": "NOT_CHECKED",
              "restoration": "NOT_INCLUDED", "replay": "NOT_CHECKED"}
    if source is not None:
        _bytes(source, max_bytes)
    if output is not None:
        _bytes(output, max_bytes)
    if record["OriginalReversivelIncluido"]:
        try:
            restored = restore_original(record, max_bytes)
            result["restoration"] = "MATCH"
            if source is None:
                source = restored
            elif source != restored:
                result["restoration"] = "MISMATCH"
        except (ValueError, UnicodeError):
            result["restoration"] = "MISMATCH"
    for label, data, size_key, hash_key in (
        ("source_bytes", source, "TamanhoFonteBytes", "SHA256Fonte"),
        ("output_bytes", output, "TamanhoSaidaBytes", "SHA256Saida"),
    ):
        if data is not None:
            result[label] = "MATCH" if len(data) == record[size_key] and _sha(data) == record[hash_key] else "MISMATCH"
    if source is not None and output is not None and record["ModoSaida"] != "declared-only-v1":
        try:
            result["replay"] = "MATCH" if transform(source, record["ModoSaida"], max_bytes) == output else "MISMATCH"
        except (ValueError, UnicodeError, RecursionError):
            result["replay"] = "MISMATCH"
    checked = ("source_bytes", "output_bytes", "replay")
    result["status"] = ("INVALID" if "MISMATCH" in result.values() else
                        "VERIFIED_BYTES_AND_REPLAY" if all(result[k] == "MATCH" for k in checked)
                        else "NOT_DECIDABLE")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check source/output bytes and local replay, not historical truth.")
    parser.add_argument("record", type=Path)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--max-bytes", type=int, default=MAX_BYTES)
    args = parser.parse_args(argv)
    try:
        _limit(args.max_bytes)
        record = load_record(read_bounded(args.record, args.max_bytes * 2 + 65536), args.max_bytes)
        result = verify(record,
                        source=read_bounded(args.source, args.max_bytes) if args.source else None,
                        output=read_bounded(args.output, args.max_bytes) if args.output else None,
                        max_bytes=args.max_bytes)
    except (OSError, ValueError, TypeError, UnicodeError, RecursionError):
        print('{"status":"INPUT_ERROR"}', file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return {"VERIFIED_BYTES_AND_REPLAY": 0, "INVALID": 1, "NOT_DECIDABLE": 2}[result["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
