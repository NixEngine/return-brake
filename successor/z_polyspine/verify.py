#!/usr/bin/env python3
"""Standard-library verifier for the prospective Z-Polyspine demonstration."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import unicodedata
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any


BASE_COMMIT = "b1f8c710a0c94c4c600b517855bacbfa735c03c6"
BASE_TREE = "d7f59203eac4fbc809ae2668bc6da083df71a155"
EXPECTED_ORIGIN = "https://github.com/NixEngine/return-brake"
EXPECTED_BRANCH = "successor/z-polyspine-demonstration-v1"
EXPECTED_REPOSITORY = "NixEngine/return-brake"
EXPECTED_CHAIN_HASH = "8990e7a9aaed2ffed73dbd7092123d6f289930540d7651336225dc172e51b2ce"
EXPECTED_DRAND_GENESIS = 1595431050
EXPECTED_DRAND_PERIOD = 30
EXPECTED_BEACON_ROUND = 6383646
EXPECTED_RELAYS = [
    "https://api.drand.sh",
    "https://api2.drand.sh",
    "https://api3.drand.sh",
    "https://drand.cloudflare.com",
]
PREFIX = "successor/z_polyspine/"
P0_SNAPSHOT = "successor/z_polyspine/P0_SNAPSHOT.json"
PREREG = "successor/z_polyspine/PREREGISTRATION.json"
PHASE_RECORD = re.compile(r"^successor/z_polyspine/phases/P([0-9]+)/record\.json$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
GIT_SHA = re.compile(r"^[0-9a-f]{40}$")
STATUSES = {
    "OBSERVED",
    "INFERRED",
    "EXTERNALLY_UNVERIFIED",
    "NOT_DECIDABLE",
    "USER_DECLARED",
    "OBSERVED_IN_SESSION",
    "EXTERNALLY_VERIFIED",
}
FORBIDDEN_KEYS = {
    "api_key",
    "credential",
    "local_path",
    "password",
    "private_payload",
    "raw_private",
    "secret",
    "token",
    "transcript_payload",
    "canonical_truth",
}
PHASE_KINDS = {
    0: {"PREREGISTRATION"},
    1: {"BEACON_SELECTION"},
    2: {"AUDIT_OBSERVATION"},
    3: {"REVISION", "NO_REVISION"},
}
PHASE_SCHEMA = "z-polyspine-phase-record-v1"
COMMON_PHASE_REQUIRED = {
    "schema",
    "phase_id",
    "sequence",
    "kind",
    "spines",
    "retains_phase_ids",
    "contributions",
    "claims",
    "privacy_projection",
}
CLAIM_PREDICATES = {
    "AUDIT_RESULT",
    "BEACON_OBSERVATION",
    "BOUNDED_PARTICIPANT_INFERENCE",
    "BOUNDED_SEARCH_OBSERVATION",
    "CAUSAL_ORDER_BOUNDARY",
    "CONTRIBUTION_ROLE_OBSERVATION",
    "FUTURE_BEACON_AVAILABILITY",
    "NO_REVISION_RESULT",
    "PARTICIPANT_DECLARATION",
    "PRIVATE_SOURCE_COMMITMENT",
    "PUBLIC_BYTE_INTEGRITY",
    "PUBLIC_PREDECESSOR_INSPECTABILITY",
    "PUBLIC_RECEIPT_OBSERVATION",
    "PUBLIC_REGISTRY_OBSERVATION",
    "REVISION_RELATION",
    "SELECTION_RESULT",
    "SERVICE_ROLE_BOUNDARY",
    "VERIFIER_BEHAVIOR",
}
PREDICATE_STATUSES = {
    "AUDIT_RESULT": {"OBSERVED", "INFERRED", "NOT_DECIDABLE"},
    "BEACON_OBSERVATION": {"OBSERVED"},
    "BOUNDED_PARTICIPANT_INFERENCE": {"INFERRED"},
    "BOUNDED_SEARCH_OBSERVATION": {"OBSERVED_IN_SESSION"},
    "CAUSAL_ORDER_BOUNDARY": {"EXTERNALLY_UNVERIFIED"},
    "CONTRIBUTION_ROLE_OBSERVATION": {"OBSERVED_IN_SESSION"},
    "FUTURE_BEACON_AVAILABILITY": {"EXTERNALLY_UNVERIFIED"},
    "NO_REVISION_RESULT": {"OBSERVED"},
    "PARTICIPANT_DECLARATION": {"USER_DECLARED"},
    "PRIVATE_SOURCE_COMMITMENT": {"OBSERVED_IN_SESSION"},
    "PUBLIC_BYTE_INTEGRITY": {"OBSERVED"},
    "PUBLIC_PREDECESSOR_INSPECTABILITY": {"INFERRED"},
    "PUBLIC_RECEIPT_OBSERVATION": {"EXTERNALLY_VERIFIED"},
    "PUBLIC_REGISTRY_OBSERVATION": {"EXTERNALLY_VERIFIED"},
    "REVISION_RELATION": {"INFERRED"},
    "SELECTION_RESULT": {"OBSERVED"},
    "SERVICE_ROLE_BOUNDARY": {"OBSERVED_IN_SESSION"},
    "VERIFIER_BEHAVIOR": {"OBSERVED", "INFERRED"},
}
PHASE_ALLOWED_KEYS = {
    0: COMMON_PHASE_REQUIRED
    | {"public_introduction_commit", "clock_observation", "informed_by"},
    1: COMMON_PHASE_REQUIRED
    | {
        "prior_public_commit",
        "prior_public_receipt",
        "previous_phase_record_sha256",
        "authorization_ref",
        "beacon",
        "selection",
    },
    2: COMMON_PHASE_REQUIRED
    | {
        "prior_public_commit",
        "prior_public_receipt",
        "previous_phase_record_sha256",
        "authorization_ref",
        "audit",
    },
    3: COMMON_PHASE_REQUIRED
    | {
        "prior_public_commit",
        "prior_public_receipt",
        "previous_phase_record_sha256",
        "authorization_ref",
        "basis_phase_id",
        "finding_dispositions",
        "active_heads",
        "changes",
        "reason_code",
    },
}
OVERCLAIM_PATTERN = re.compile(
    r"(?:\bmind\b|conscio(?:us|usness)|sentien\w*|interiority|inner state|"
    r"subjective awareness|self-aware|\bsoul\b|personhood|identity continuity|"
    r"no human intervention|without any human|nobody else acted|no one else acted|"
    r"sole originator|exclusive (?:causal )?authorship)",
    re.IGNORECASE,
)
LOCAL_PATH_PATTERN = re.compile(
    r"(?:[A-Za-z]:\\|/Users/|\\Users\\|AppData\\|/home/|/root/)", re.IGNORECASE
)
SECRET_VALUE_PATTERN = re.compile(
    r"(?:ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|"
    r"sk-[A-Za-z0-9_-]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|"
    r"Bearer\s+[A-Za-z0-9._-]{20,}|password\s*[:=])",
    re.IGNORECASE,
)


class DuplicateKeyError(ValueError):
    pass


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        value = json.load(handle, object_pairs_hook=_pairs, parse_float=_reject_float)
    if not isinstance(value, dict):
        raise ValueError("top-level JSON value must be an object")
    return value


def _reject_float(value: str) -> Any:
    raise ValueError(f"floating point JSON value is forbidden: {value}")


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def digest_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_relative(value: str) -> bool:
    if not value or "\\" in value or ":" in value:
        return False
    raw_parts = value.split("/")
    if any(part in {"", ".", ".."} for part in raw_parts):
        return False
    path = PurePosixPath(value)
    return not path.is_absolute()


def _walk(value: Any, where: str, errors: list[dict[str, str]]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if unicodedata.normalize("NFC", key) != key:
                add_error(errors, "JSON_NON_NFC", f"{where}: non-NFC key")
            if key.casefold() in FORBIDDEN_KEYS:
                add_error(errors, "PRIVATE_KEY_FORBIDDEN", f"{where}: forbidden key {key}")
            _walk(child, f"{where}.{key}", errors)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _walk(child, f"{where}[{index}]", errors)
    elif isinstance(value, str):
        if unicodedata.normalize("NFC", value) != value:
            add_error(errors, "JSON_NON_NFC", f"{where}: non-NFC string")
        if len(value) > 4000:
            add_error(errors, "JSON_STRING_TOO_LONG", where)
        if LOCAL_PATH_PATTERN.search(value):
            add_error(errors, "LOCAL_PATH_DISCLOSURE", f"{where}: local absolute path")
        if SECRET_VALUE_PATTERN.search(value):
            add_error(errors, "SECRET_VALUE_FORBIDDEN", where)
    elif isinstance(value, float):
        add_error(errors, "JSON_FLOAT_FORBIDDEN", f"{where}: floating point value")


def add_error(errors: list[dict[str, str]], code: str, message: str) -> None:
    errors.append({"code": code, "message": message})


def git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def verify_claims(value: Any, where: str, errors: list[dict[str, str]]) -> None:
    if not isinstance(value, list):
        add_error(errors, "CLAIMS_NOT_LIST", f"{where}: claims must be a list")
        return
    if len(value) > 20:
        add_error(errors, "CLAIMS_TOO_MANY", where)
    for index, claim in enumerate(value):
        if not isinstance(claim, dict):
            add_error(errors, "CLAIM_NOT_OBJECT", f"{where}[{index}]")
            continue
        allowed = {"id", "predicate", "subject", "status", "statement", "evidence_refs"}
        extra = sorted(set(claim) - allowed)
        if extra:
            add_error(errors, "CLAIM_FIELD_FORBIDDEN", f"{where}[{index}]: {extra}")
        claim_id = claim.get("id")
        if not isinstance(claim_id, str) or not re.fullmatch(
            r"[a-z0-9][a-z0-9-]{0,79}", claim_id
        ):
            add_error(errors, "CLAIM_ID_INVALID", f"{where}[{index}]")
        if claim.get("predicate") not in CLAIM_PREDICATES:
            add_error(errors, "CLAIM_PREDICATE_INVALID", f"{where}[{index}]")
        elif claim.get("status") not in PREDICATE_STATUSES[claim["predicate"]]:
            add_error(errors, "CLAIM_PREDICATE_STATUS_INVALID", f"{where}[{index}]")
        subject = claim.get("subject")
        if subject is not None and (
            not isinstance(subject, str)
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", subject)
        ):
            add_error(errors, "CLAIM_SUBJECT_INVALID", f"{where}[{index}]")
        if claim.get("status") not in STATUSES:
            add_error(errors, "CLAIM_STATUS_INVALID", f"{where}[{index}]: invalid status")
        if (
            not isinstance(claim.get("statement"), str)
            or not claim["statement"].strip()
            or len(claim["statement"]) > 800
        ):
            add_error(errors, "CLAIM_STATEMENT_INVALID", f"{where}[{index}]")
            continue
        evidence_refs = claim.get("evidence_refs")
        if not isinstance(evidence_refs, list) or not evidence_refs or any(
            not isinstance(item, str) or not safe_relative(item) for item in evidence_refs
        ):
            add_error(errors, "CLAIM_EVIDENCE_MISSING", f"{where}[{index}]")
        if OVERCLAIM_PATTERN.search(claim["statement"]):
            add_error(errors, "CLAIM_OUTSIDE_OBSERVABLE_BOUNDARY", f"{where}[{index}]")


def verify_phase_common(
    record: Any,
    sequence: int,
    root: Path,
    errors: list[dict[str, str]],
) -> None:
    where = f"P{sequence}"
    if not isinstance(record, dict):
        add_error(errors, "PHASE_RECORD_NOT_OBJECT", where)
        return
    if record.get("schema") != PHASE_SCHEMA:
        add_error(errors, "PHASE_SCHEMA_INVALID", where)
    missing = sorted(COMMON_PHASE_REQUIRED - set(record))
    if missing:
        add_error(errors, "PHASE_FIELD_MISSING", f"{where}: {missing}")
    extra = sorted(set(record) - PHASE_ALLOWED_KEYS.get(sequence, set()))
    if extra:
        add_error(errors, "PHASE_FIELD_FORBIDDEN", f"{where}: {extra}")
    if record.get("phase_id") != where or record.get("sequence") != sequence:
        add_error(errors, "PHASE_RECORD_ID_MISMATCH", where)
    if record.get("kind") not in PHASE_KINDS.get(sequence, set()):
        add_error(errors, "PHASE_KIND_INVALID", f"{where}: {record.get('kind')!r}")
    spines = record.get("spines")
    if (
        not isinstance(spines, list)
        or len(spines) < 2
        or len(spines) > 12
        or any(
            not isinstance(item, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,79}", item)
            for item in spines
        )
        or len(set(spines)) != len(spines)
    ):
        add_error(errors, "SPINES_NOT_PRESERVED", where)
    retained = record.get("retains_phase_ids")
    if retained != [f"P{i}" for i in range(sequence)]:
        add_error(errors, "PHASE_PRESERVATION_FAILURE", where)
    privacy = record.get("privacy_projection")
    required_privacy = {
        "mode": "ALLOWLISTED_PUBLIC_FACTS_ONLY",
        "source_payload_included": False,
        "local_paths_included": False,
        "credentials_included": False,
    }
    if privacy != required_privacy:
        add_error(errors, "PRIVACY_PROJECTION_INVALID", where)
    verify_contributions(record, root, errors)
    verify_claims(record.get("claims"), f"{where}.claims", errors)
    if sequence > 0 and record.get("claims") != []:
        add_error(errors, "LATER_PHASE_CLAIMS_FORBIDDEN", where)
    verify_evidence_refs(record, root, errors)


def select_candidates(randomness: str, catalog: dict[str, Any], count: int) -> list[dict[str, str]]:
    if not SHA256.fullmatch(randomness):
        raise ValueError("randomness must be exactly 64 lowercase hexadecimal characters")
    candidates = catalog.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise ValueError("catalog candidates must be a non-empty list")
    ids: list[str] = []
    for item in candidates:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            raise ValueError("every candidate requires a string id")
        ids.append(item["id"])
    if len(ids) != len(set(ids)):
        raise ValueError("candidate ids must be unique")
    if not isinstance(count, int) or count < 1 or count > len(ids):
        raise ValueError("selection count is outside catalog bounds")
    seed = bytes.fromhex(randomness)
    ranked = [
        {
            "id": candidate_id,
            "rank_digest": digest_bytes(seed + b"\0" + candidate_id.encode("utf-8")),
        }
        for candidate_id in ids
    ]
    ranked.sort(key=lambda item: (item["rank_digest"], item["id"]))
    return ranked[:count]


def replay_surface(surface: str, catalog: dict[str, Any]) -> dict[str, Any]:
    candidates = catalog.get("candidates")
    if not isinstance(candidates, list):
        raise ValueError("catalog candidates must be a list")
    matches = [item for item in candidates if isinstance(item, dict) and item.get("id") == surface]
    if len(matches) != 1:
        raise ValueError("surface must identify exactly one catalog candidate")
    candidate = matches[0]
    if set(candidate) != {"id", "question", "verifier_checks"}:
        raise ValueError("candidate fields differ from the frozen replay schema")
    question = candidate.get("question")
    checks = candidate.get("verifier_checks")
    if not isinstance(question, str) or not question or len(question) > 300:
        raise ValueError("candidate question is invalid")
    if (
        not isinstance(checks, list)
        or not checks
        or len(checks) > 12
        or any(not isinstance(code, str) or not re.fullmatch(r"[A-Z][A-Z0-9_]{1,79}", code) for code in checks)
    ):
        raise ValueError("candidate verifier checks are invalid")
    return {
        "schema": "z-polyspine-surface-replay-v1",
        "surface": surface,
        "question": question,
        "verifier_checks": checks,
    }


def expected_replay_command(surface: str) -> list[str]:
    return [
        "python",
        "successor/z_polyspine/verify.py",
        "replay",
        "--surface",
        surface,
    ]


def parse_utc(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def fetch_json(url: str) -> Any:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json, application/json",
            "User-Agent": "return-brake-z-polyspine-verifier",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"), object_pairs_hook=_pairs)


def normalized_beacon_payload(beacon: dict[str, Any]) -> dict[str, Any]:
    return {
        "round": beacon.get("round"),
        "randomness": beacon.get("randomness"),
        "signature": beacon.get("signature"),
        "previous_signature": beacon.get("previous_signature"),
    }


def verify_receipt(
    receipt: Any,
    expected_head: str,
    expected_before: str,
    expected_ref: str,
    errors: list[dict[str, str]],
    *,
    remote: bool,
) -> datetime | None:
    where = "prior_public_receipt"
    if not isinstance(receipt, dict):
        add_error(errors, "PRIOR_PUBLIC_RECEIPT_MISSING", where)
        return None
    expected_static = {
        "provider": "github_repository_events",
        "collection_url": "https://api.github.com/repos/NixEngine/return-brake/events",
        "event_type": "PushEvent",
        "repository": EXPECTED_REPOSITORY,
        "ref": expected_ref,
        "head_sha": expected_head,
        "before_sha": expected_before,
    }
    for key, expected in expected_static.items():
        if receipt.get(key) != expected:
            add_error(errors, "PUBLIC_RECEIPT_FIELD_MISMATCH", f"{key}: {receipt.get(key)!r}")
    event_id = receipt.get("event_id")
    if not isinstance(event_id, str) or not event_id.isdecimal():
        add_error(errors, "PUBLIC_RECEIPT_EVENT_ID_INVALID", repr(event_id))
    created = parse_utc(receipt.get("created_at_utc"))
    if created is None:
        add_error(errors, "PUBLIC_RECEIPT_TIME_INVALID", repr(receipt.get("created_at_utc")))
    before = receipt.get("before_sha")
    if not isinstance(before, str) or not GIT_SHA.fullmatch(before):
        add_error(errors, "PUBLIC_RECEIPT_BEFORE_INVALID", repr(before))
    if remote and isinstance(event_id, str) and event_id.isdecimal():
        matched: dict[str, Any] | None = None
        collection = expected_static["collection_url"]
        for page in range(1, 4):
            separator = "&" if "?" in collection else "?"
            try:
                events = fetch_json(f"{collection}{separator}per_page=100&page={page}")
            except Exception as exc:  # network failure is a structured verification failure
                add_error(errors, "PUBLIC_RECEIPT_FETCH_FAILED", f"{type(exc).__name__}: {exc}")
                break
            if not isinstance(events, list):
                add_error(errors, "PUBLIC_RECEIPT_RESPONSE_INVALID", f"page {page}")
                break
            matched = next((item for item in events if str(item.get("id")) == event_id), None)
            if matched is not None or not events:
                break
        if matched is None:
            add_error(errors, "PUBLIC_RECEIPT_EVENT_NOT_FOUND", event_id)
        else:
            payload = matched.get("payload") if isinstance(matched.get("payload"), dict) else {}
            observed = {
                "event_type": matched.get("type"),
                "repository": (matched.get("repo") or {}).get("name"),
                "ref": payload.get("ref"),
                "head_sha": payload.get("head"),
                "before_sha": payload.get("before"),
                "created_at_utc": matched.get("created_at"),
            }
            declared = {
                key: receipt.get(key)
                for key in (
                    "event_type",
                    "repository",
                    "ref",
                    "head_sha",
                    "before_sha",
                    "created_at_utc",
                )
            }
            if observed != declared:
                add_error(
                    errors,
                    "PUBLIC_RECEIPT_REMOTE_MISMATCH",
                    f"observed={observed} declared={declared}",
                )
    return created


def verify_remote_branch_event_chain(
    phase_commits: list[str], errors: list[dict[str, str]]
) -> dict[str, Any]:
    collection = "https://api.github.com/repos/NixEngine/return-brake/events"
    events: list[dict[str, Any]] = []
    for page in range(1, 4):
        try:
            batch = fetch_json(f"{collection}?per_page=100&page={page}")
        except Exception as exc:
            add_error(errors, "BRANCH_EVENT_FETCH_FAILED", f"{type(exc).__name__}: {exc}")
            return {}
        if not isinstance(batch, list):
            add_error(errors, "BRANCH_EVENT_RESPONSE_INVALID", f"page {page}")
            return {}
        events.extend(item for item in batch if isinstance(item, dict))
        if not batch:
            break
    branch_name = EXPECTED_BRANCH
    full_ref = f"refs/heads/{branch_name}"
    creates = [
        item
        for item in events
        if item.get("type") == "CreateEvent"
        and isinstance(item.get("payload"), dict)
        and item["payload"].get("ref") == branch_name
        and item["payload"].get("ref_type") == "branch"
    ]
    deletes = [
        item
        for item in events
        if item.get("type") == "DeleteEvent"
        and isinstance(item.get("payload"), dict)
        and item["payload"].get("ref") == branch_name
        and item["payload"].get("ref_type") == "branch"
    ]
    pushes = [
        item
        for item in events
        if item.get("type") == "PushEvent"
        and isinstance(item.get("payload"), dict)
        and item["payload"].get("ref") == full_ref
    ]
    if len(creates) != 1:
        add_error(errors, "BRANCH_CREATE_EVENT_COUNT", str(len(creates)))
    if deletes:
        add_error(errors, "BRANCH_DELETE_EVENT_FOUND", repr([item.get("id") for item in deletes]))
    expected_edges = [
        (BASE_COMMIT if index == 0 else phase_commits[index - 1], commit)
        for index, commit in enumerate(phase_commits)
    ]
    allowed_edges = set(expected_edges) | {("0" * 40, BASE_COMMIT)}
    edge_events: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for item in pushes:
        payload = item["payload"]
        edge = (payload.get("before"), payload.get("head"))
        if edge not in allowed_edges:
            add_error(errors, "BRANCH_PUSH_EDGE_UNEXPECTED", repr(edge))
        edge_events.setdefault(edge, []).append(item)
        if payload.get("forced") is True:
            add_error(errors, "BRANCH_FORCE_PUSH_EVENT", str(item.get("id")))
    ordered_times: list[datetime] = []
    event_ids: list[str] = []
    for edge in expected_edges:
        matches = edge_events.get(edge, [])
        if len(matches) != 1:
            add_error(errors, "BRANCH_PUSH_EDGE_COUNT", f"{edge}: {len(matches)}")
            continue
        event = matches[0]
        event_time = parse_utc(event.get("created_at"))
        if event_time is None:
            add_error(errors, "BRANCH_PUSH_TIME_INVALID", str(event.get("id")))
            continue
        ordered_times.append(event_time)
        event_ids.append(str(event.get("id")))
    if any(right <= left for left, right in zip(ordered_times, ordered_times[1:])):
        add_error(errors, "BRANCH_PUSH_TIME_ORDER_FAILURE", repr(event_ids))
    if creates and ordered_times:
        created = parse_utc(creates[0].get("created_at"))
        if created is None or created >= ordered_times[0]:
            add_error(errors, "BRANCH_CREATE_NOT_BEFORE_P0", repr(creates[0].get("id")))
    return {
        "create_event_id": str(creates[0].get("id")) if len(creates) == 1 else None,
        "phase_push_event_ids": event_ids,
    }


def verify_beacon_and_selection(
    record: dict[str, Any],
    prereg: dict[str, Any],
    root: Path,
    errors: list[dict[str, str]],
    *,
    remote: bool,
) -> None:
    expected = prereg.get("future_beacon")
    beacon = record.get("beacon")
    if not isinstance(expected, dict) or not isinstance(beacon, dict):
        add_error(errors, "BEACON_MISSING", "P1 beacon")
        return
    allowed_beacon_fields = {
        "network",
        "chain_hash",
        "scheme",
        "round",
        "signature",
        "previous_signature",
        "randomness",
        "relay_observations",
    }
    if set(beacon) != allowed_beacon_fields:
        add_error(errors, "BEACON_FIELD_FORBIDDEN", repr(sorted(set(beacon))))
    for key in ("network", "chain_hash", "scheme", "round"):
        if beacon.get(key) != expected.get(key):
            add_error(errors, "BEACON_FIELD_MISMATCH", key)
    signature = beacon.get("signature")
    previous = beacon.get("previous_signature")
    randomness = beacon.get("randomness")
    if not isinstance(signature, str) or not re.fullmatch(r"[0-9a-f]{192}", signature):
        add_error(errors, "BEACON_SIGNATURE_INVALID", "signature")
    if not isinstance(previous, str) or not re.fullmatch(r"[0-9a-f]{192}", previous):
        add_error(errors, "BEACON_SIGNATURE_INVALID", "previous_signature")
    if not isinstance(randomness, str) or not SHA256.fullmatch(randomness):
        add_error(errors, "BEACON_RANDOMNESS_INVALID", repr(randomness))
    elif isinstance(signature, str) and re.fullmatch(r"[0-9a-f]{192}", signature):
        if digest_bytes(bytes.fromhex(signature)) != randomness:
            add_error(errors, "BEACON_RANDOMNESS_SIGNATURE_MISMATCH", "sha256(signature)")
    payload_hash = digest_bytes(canonical_bytes(normalized_beacon_payload(beacon)))
    observations = beacon.get("relay_observations")
    allowed_relays = set(expected.get("cross_check_relays", []))
    expected_beacon_time = parse_utc(expected.get("expected_utc_from_chain_parameters"))
    if not isinstance(observations, list) or len(observations) < 3:
        add_error(errors, "BEACON_RELAY_QUORUM", "at least three relays required")
        observations = []
    relays: set[str] = set()
    for index, observation in enumerate(observations):
        if not isinstance(observation, dict):
            add_error(errors, "BEACON_RELAY_INVALID", str(index))
            continue
        if set(observation) != {"relay", "http_date_utc", "normalized_response_sha256"}:
            add_error(errors, "BEACON_RELAY_FIELD_FORBIDDEN", str(index))
        relay = observation.get("relay")
        if relay not in allowed_relays or relay in relays:
            add_error(errors, "BEACON_RELAY_INVALID", repr(relay))
            continue
        relays.add(relay)
        if observation.get("normalized_response_sha256") != payload_hash:
            add_error(errors, "BEACON_RELAY_HASH_MISMATCH", relay)
        observed_http_time = parse_utc(observation.get("http_date_utc"))
        if observed_http_time is None:
            add_error(errors, "BEACON_RELAY_TIME_INVALID", relay)
        elif expected_beacon_time is None or observed_http_time < expected_beacon_time:
            add_error(errors, "BEACON_RELAY_TIME_PREMATURE", relay)
        if remote:
            endpoint = f"{relay}/public/{expected.get('round')}"
            try:
                live = fetch_json(endpoint)
            except Exception as exc:
                add_error(errors, "BEACON_RELAY_FETCH_FAILED", f"{relay}: {exc}")
                continue
            if normalized_beacon_payload(live) != normalized_beacon_payload(beacon):
                add_error(errors, "BEACON_RELAY_REMOTE_MISMATCH", relay)
    selection_config = prereg.get("selection", {})
    if not isinstance(randomness, str) or not SHA256.fullmatch(randomness):
        return
    try:
        catalog = load_json(root / selection_config["catalog_path"])
        expected_selection = select_candidates(
            randomness, catalog, selection_config["count"]
        )
    except (OSError, ValueError, KeyError, DuplicateKeyError) as exc:
        add_error(errors, "SELECTION_RECOMPUTE_FAILED", str(exc))
        return
    if record.get("selection") != expected_selection:
        add_error(errors, "SELECTION_MISMATCH", "P1 selection is not beacon-derived")


def verify_contributions(
    record: dict[str, Any], root: Path, errors: list[dict[str, str]]
) -> None:
    protocol = load_json(root / "successor/z_polyspine/CONTRIBUTION_PROTOCOL.json")
    principals = {item.get("id") for item in protocol.get("principals", []) if isinstance(item, dict)}
    roles = set(protocol.get("roles", []))
    entries = record.get("contributions")
    if not isinstance(entries, list) or len(entries) < 2 or len(entries) > 12:
        add_error(errors, "CONTRIBUTION_LEDGER_MISSING", record.get("phase_id", "?"))
        return
    distinct_principals: set[str] = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            add_error(errors, "CONTRIBUTION_ENTRY_INVALID", str(index))
            continue
        allowed = {"principal", "role", "status", "evidence_refs"}
        extra = sorted(set(entry) - allowed)
        if extra:
            add_error(errors, "CONTRIBUTION_FIELD_FORBIDDEN", f"{index}: {extra}")
        principal = entry.get("principal")
        role = entry.get("role")
        if principal not in principals:
            add_error(errors, "CONTRIBUTION_PRINCIPAL_INVALID", repr(principal))
        else:
            distinct_principals.add(principal)
        if role not in roles:
            add_error(errors, "CONTRIBUTION_ROLE_INVALID", repr(role))
        if entry.get("status") not in {"USER_DECLARED", "OBSERVED_IN_SESSION", "EXTERNALLY_VERIFIED", "INFERRED"}:
            add_error(errors, "CONTRIBUTION_STATUS_INVALID", str(index))
        refs = entry.get("evidence_refs")
        if not isinstance(refs, list) or not refs:
            add_error(errors, "CONTRIBUTION_EVIDENCE_MISSING", str(index))
    if len(distinct_principals) < 2:
        add_error(errors, "MATERIAL_ROLES_COLLAPSED", record.get("phase_id", "?"))


def verify_evidence_refs(
    record: dict[str, Any], root: Path, errors: list[dict[str, str]]
) -> None:
    containers: list[Any] = [record.get("claims", []), record.get("contributions", [])]
    for entries in containers:
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            for relative in entry.get("evidence_refs", []):
                if not isinstance(relative, str) or not safe_relative(relative):
                    add_error(errors, "EVIDENCE_PATH_INVALID", repr(relative))
                elif not (root / relative).is_file():
                    add_error(errors, "EVIDENCE_PATH_MISSING", relative)


def verify_contribution_protocol(root: Path, errors: list[dict[str, str]]) -> None:
    protocol = load_json(root / "successor/z_polyspine/CONTRIBUTION_PROTOCOL.json")
    if protocol.get("schema") != "z-polyspine-contribution-ledger-v1":
        add_error(errors, "CONTRIBUTION_PROTOCOL_SCHEMA", "unexpected schema")
    baseline = protocol.get("baseline_claims")
    verify_claims(baseline, "CONTRIBUTION_PROTOCOL.baseline_claims", errors)
    verify_evidence_refs({"claims": baseline}, root, errors)
    boundary = protocol.get("communication_service_boundary")
    if not isinstance(boundary, dict) or set(boundary) != {
        "status",
        "provider_function",
        "not_attributed_to_provider",
        "bounded_observation",
    }:
        add_error(errors, "SERVICE_BOUNDARY_INVALID", "communication_service_boundary")


def verify_phase_semantics(
    records: list[dict[str, Any]],
    root: Path,
    prereg: dict[str, Any],
    errors: list[dict[str, str]],
    *,
    remote: bool,
) -> None:
    for sequence, record in enumerate(records):
        verify_phase_common(record, sequence, root, errors)
    if len(records) >= 2:
        verify_beacon_and_selection(records[1], prereg, root, errors, remote=remote)
    if len(records) >= 3:
        p1_ids = [item.get("id") for item in records[1].get("selection", []) if isinstance(item, dict)]
        try:
            audit_catalog = load_json(root / prereg["selection"]["catalog_path"])
        except (OSError, ValueError, KeyError, DuplicateKeyError) as exc:
            add_error(errors, "AUDIT_CATALOG_INVALID", str(exc))
            audit_catalog = {"candidates": []}
        audit = records[2].get("audit")
        if not isinstance(audit, dict):
            add_error(errors, "AUDIT_MISSING", "P2")
        else:
            allowed_audit = {
                "execution_declaration",
                "selected_surfaces",
                "finding_count",
                "findings",
                "replay",
            }
            if set(audit) != allowed_audit:
                add_error(errors, "AUDIT_FIELD_FORBIDDEN", repr(sorted(set(audit) - allowed_audit)))
            expected_execution = {
                "executor": "FRESH_CODEX_SUBAGENT",
                "isolation": "FORK_TURNS_NONE",
                "attestation_status": "SESSION_DECLARED_NOT_EXTERNALLY_ATTESTED",
            }
            if audit.get("execution_declaration") != expected_execution:
                add_error(errors, "AUDIT_EXECUTION_DECLARATION_INVALID", "P2")
            if audit.get("selected_surfaces") != p1_ids:
                add_error(errors, "AUDIT_SELECTION_MISMATCH", "P2 selected surfaces")
            findings = audit.get("findings")
            if not isinstance(findings, list):
                add_error(errors, "AUDIT_FINDINGS_INVALID", "P2")
            else:
                finding_ids: set[str] = set()
                for index, finding in enumerate(findings):
                    if not isinstance(finding, dict):
                        add_error(errors, "AUDIT_FINDING_INVALID", str(index))
                        continue
                    finding_id = finding.get("id")
                    if not isinstance(finding_id, str) or finding_id in finding_ids:
                        add_error(errors, "AUDIT_FINDING_ID_INVALID", repr(finding_id))
                    finding_ids.add(str(finding_id))
                    if finding.get("surface") not in p1_ids:
                        add_error(errors, "AUDIT_FINDING_OUT_OF_SCOPE", repr(finding.get("surface")))
                    if finding.get("result") not in {"PASS", "FAIL", "NOT_DECIDABLE"}:
                        add_error(errors, "AUDIT_FINDING_RESULT_INVALID", repr(finding.get("result")))
                    if finding.get("status") not in {"OBSERVED", "INFERRED", "EXTERNALLY_UNVERIFIED", "NOT_DECIDABLE"}:
                        add_error(errors, "AUDIT_FINDING_STATUS_INVALID", repr(finding.get("status")))
                    allowed_finding = {
                        "id",
                        "surface",
                        "result",
                        "status",
                        "verifier_codes",
                        "reproduction",
                    }
                    if set(finding) != allowed_finding:
                        add_error(errors, "AUDIT_FINDING_FIELD_FORBIDDEN", repr(finding_id))
                    verifier_codes = finding.get("verifier_codes")
                    try:
                        allowed_codes = set(
                            replay_surface(str(finding.get("surface")), audit_catalog)["verifier_checks"]
                        )
                    except ValueError as exc:
                        add_error(errors, "AUDIT_FINDING_SURFACE_SCHEMA_INVALID", str(exc))
                        allowed_codes = set()
                    if (
                        not isinstance(verifier_codes, list)
                        or not verifier_codes
                        or len(verifier_codes) != len(set(verifier_codes))
                        or any(code not in allowed_codes for code in verifier_codes)
                    ):
                        add_error(errors, "AUDIT_FINDING_CODE_INVALID", repr(finding_id))
                    reproduction = finding.get("reproduction")
                    if reproduction != [finding.get("surface")]:
                        add_error(errors, "AUDIT_REPRODUCTION_MISSING", repr(finding_id))
                if audit.get("finding_count") != len(findings):
                    add_error(errors, "AUDIT_FINDING_COUNT_MISMATCH", "P2")
            replay = audit.get("replay")
            if not isinstance(replay, list) or len(replay) != len(p1_ids):
                add_error(errors, "AUDIT_REPLAY_COVERAGE", "P2")
            else:
                replay_surfaces: set[str] = set()
                for entry in replay:
                    if not isinstance(entry, dict) or set(entry) != {
                        "surface",
                        "command",
                        "expected_exit_code",
                        "normalized_stdout_sha256",
                    }:
                        add_error(errors, "AUDIT_REPLAY_INVALID", repr(entry))
                        continue
                    surface = entry.get("surface")
                    command = entry.get("command")
                    if surface not in p1_ids or surface in replay_surfaces:
                        add_error(errors, "AUDIT_REPLAY_SURFACE_INVALID", repr(surface))
                    replay_surfaces.add(str(surface))
                    if command != expected_replay_command(str(surface)):
                        add_error(errors, "AUDIT_REPLAY_COMMAND_INVALID", repr(surface))
                    if entry.get("expected_exit_code") != 0:
                        add_error(errors, "AUDIT_REPLAY_EXIT_INVALID", repr(surface))
                    try:
                        catalog = load_json(root / prereg["selection"]["catalog_path"])
                        replay_result = {"ok": True, **replay_surface(str(surface), catalog)}
                        normalized_hash = digest_bytes(canonical_bytes(replay_result))
                    except (OSError, ValueError, KeyError, DuplicateKeyError) as exc:
                        add_error(errors, "AUDIT_REPLAY_RECOMPUTE_FAILED", str(exc))
                        continue
                    stdout_hash = entry.get("normalized_stdout_sha256")
                    if stdout_hash != normalized_hash:
                        add_error(errors, "AUDIT_REPLAY_HASH_INVALID", repr(surface))
    if len(records) >= 4:
        p2_findings = records[2].get("audit", {}).get("findings", [])
        finding_ids = {item.get("id") for item in p2_findings if isinstance(item, dict)}
        p3 = records[3]
        if p3.get("basis_phase_id") != "P2":
            add_error(errors, "REVISION_BASIS_MISSING", "P3")
        dispositions = p3.get("finding_dispositions")
        if not isinstance(dispositions, list):
            add_error(errors, "REVISION_DISPOSITIONS_MISSING", "P3")
            dispositions = []
        disposition_ids = {item.get("finding_id") for item in dispositions if isinstance(item, dict)}
        if disposition_ids != finding_ids:
            add_error(errors, "REVISION_DISPOSITION_COVERAGE", "P3")
        for item in dispositions:
            if not isinstance(item, dict) or set(item) != {
                "finding_id",
                "disposition",
                "rationale_code",
            }:
                add_error(errors, "REVISION_DISPOSITION_FIELD_INVALID", repr(item))
                continue
            if item.get("disposition") not in {
                "ADD_SUCCESSOR",
                "RETAIN",
                "CONTEST",
                "NOT_DECIDABLE",
            }:
                add_error(errors, "REVISION_DISPOSITION_INVALID", repr(item))
            rationale_pairs = {
                "ADD_SUCCESSOR": "VERIFIER_EVIDENCE_SUPPORTS_SUCCESSOR",
                "RETAIN": "CURRENT_SPINE_RETAINED",
                "CONTEST": "COUNTEREVIDENCE_REQUIRES_CONTEST",
                "NOT_DECIDABLE": "EVIDENCE_NOT_DECIDABLE",
            }
            if item.get("rationale_code") != rationale_pairs.get(item.get("disposition")):
                add_error(errors, "REVISION_RATIONALE_CODE_INVALID", repr(item.get("finding_id")))
        if p3.get("kind") == "REVISION":
            if "reason_code" in p3:
                add_error(errors, "REVISION_REASON_FIELD_FORBIDDEN", "P3")
            if not isinstance(p3.get("changes"), list) or not p3["changes"]:
                add_error(errors, "REVISION_CHANGESET_EMPTY", "P3")
            else:
                for change in p3["changes"]:
                    if not isinstance(change, dict) or set(change) != {
                        "id",
                        "basis_finding_ids",
                        "action",
                    }:
                        add_error(errors, "REVISION_CHANGE_INVALID", repr(change))
                        continue
                    if change.get("action") not in {
                        "ADD_GUARD",
                        "ADD_TEST",
                        "ADD_TYPED_BOUNDARY",
                        "RETAIN_PARALLEL_SPINE",
                    }:
                        add_error(errors, "REVISION_CHANGE_ACTION_INVALID", repr(change.get("id")))
                    basis = change.get("basis_finding_ids")
                    if (
                        not isinstance(basis, list)
                        or not basis
                        or any(item not in finding_ids for item in basis)
                    ):
                        add_error(errors, "REVISION_CHANGE_BASIS_INVALID", repr(change.get("id")))
        elif p3.get("kind") == "NO_REVISION":
            if "changes" in p3:
                add_error(errors, "NO_REVISION_CHANGE_FIELD_FORBIDDEN", "P3")
            if p3.get("reason_code") not in {
                "NO_FAILED_FINDING",
                "NO_ACTIONABLE_COUNTEREVIDENCE",
                "EVIDENCE_NOT_DECIDABLE",
            }:
                add_error(errors, "NO_REVISION_REASON_CODE_INVALID", "P3")
        active_heads = p3.get("active_heads")
        if (
            not isinstance(active_heads, list)
            or len(active_heads) > 12
            or any(not isinstance(item, str) or not item for item in active_heads)
            or len(set(active_heads)) < 2
        ):
            add_error(errors, "SINGLE_CANONICAL_HEAD", "P3")


def _manifest_files(
    manifest: dict[str, Any], root: Path, where: str, errors: list[dict[str, str]]
) -> set[str]:
    entries = manifest.get("files")
    if not isinstance(entries, dict) or not entries:
        add_error(errors, "MANIFEST_EMPTY", f"{where}: files must be non-empty")
        return set()
    seen_casefold: set[str] = set()
    listed: set[str] = set()
    for relative, expected in entries.items():
        if not isinstance(relative, str) or not safe_relative(relative):
            add_error(errors, "MANIFEST_PATH_UNSAFE", f"{where}: {relative!r}")
            continue
        folded = unicodedata.normalize("NFC", relative).casefold()
        if folded in seen_casefold:
            add_error(errors, "PATH_COLLISION", f"{where}: {relative}")
        seen_casefold.add(folded)
        listed.add(relative)
        full = root.joinpath(*PurePosixPath(relative).parts)
        try:
            resolved = full.resolve(strict=True)
            resolved.relative_to(root.resolve(strict=True))
        except (OSError, ValueError):
            add_error(errors, "PATH_ESCAPE", f"{where}: {relative}")
            continue
        if full.is_symlink() or os.path.islink(full):
            add_error(errors, "SYMLINK_FORBIDDEN", f"{where}: {relative}")
            continue
        if not full.is_file():
            add_error(errors, "MANIFEST_FILE_MISSING", f"{where}: {relative}")
            continue
        if not isinstance(expected, dict):
            add_error(errors, "MANIFEST_ENTRY_INVALID", f"{where}: {relative}")
            continue
        if set(expected) != {"sha256", "bytes"}:
            add_error(errors, "MANIFEST_ENTRY_FIELD_FORBIDDEN", f"{where}: {relative}")
        actual_hash = digest_file(full)
        actual_bytes = full.stat().st_size
        if expected.get("sha256") != actual_hash:
            add_error(errors, "MANIFEST_HASH_MISMATCH", f"{where}: {relative}")
        if expected.get("bytes") != actual_bytes:
            add_error(errors, "MANIFEST_SIZE_MISMATCH", f"{where}: {relative}")
    return listed


def verify_p0(root: Path, errors: list[dict[str, str]]) -> dict[str, Any]:
    snapshot_path = root / P0_SNAPSHOT
    if not snapshot_path.is_file():
        add_error(errors, "P0_SNAPSHOT_MISSING", P0_SNAPSHOT)
        return {}
    snapshot = load_json(snapshot_path)
    if snapshot.get("schema") != "z-polyspine-p0-snapshot-v1":
        add_error(errors, "P0_SNAPSHOT_SCHEMA", "unexpected P0 snapshot schema")
    if set(snapshot) != {"schema", "files"}:
        add_error(errors, "P0_SNAPSHOT_FIELD_FORBIDDEN", repr(sorted(set(snapshot))))
    listed = _manifest_files(snapshot, root, "P0_SNAPSHOT", errors)
    if P0_SNAPSHOT in listed:
        add_error(errors, "P0_SELF_REFERENCE", "P0 snapshot must exclude itself")
    required = {
        "successor/z_polyspine/README.md",
        "successor/z_polyspine/.gitignore",
        "successor/z_polyspine/ROOT_ANCHOR.json",
        PREREG,
        "successor/z_polyspine/PHASE_CONTRACT.json",
        "successor/z_polyspine/CONTRIBUTION_PROTOCOL.json",
        "successor/z_polyspine/evidence/participant_registry_receipt.json",
        "successor/z_polyspine/evidence/natural_language_coupling_receipt.json",
        "successor/z_polyspine/vectors/catalog.json",
        "successor/z_polyspine/phases/P0/record.json",
        "successor/z_polyspine/verify.py",
        "successor/z_polyspine/tests/test_verify.py",
    }
    if listed != required:
        add_error(
            errors,
            "P0_COVERAGE_MISMATCH",
            f"missing={sorted(required-listed)} extra={sorted(listed-required)}",
        )
    verify_contribution_protocol(root, errors)
    anchor = load_json(root / "successor/z_polyspine/ROOT_ANCHOR.json")
    if anchor.get("repository", {}).get("frozen_main_commit") != BASE_COMMIT:
        add_error(errors, "BASE_COMMIT_MISMATCH", "ROOT_ANCHOR frozen commit")
    if anchor.get("repository", {}).get("frozen_main_tree") != BASE_TREE:
        add_error(errors, "BASE_TREE_MISMATCH", "ROOT_ANCHOR frozen tree")
    verify_claims(anchor.get("claims"), "ROOT_ANCHOR.claims", errors)
    phase = load_json(root / "successor/z_polyspine/phases/P0/record.json")
    verify_phase_common(phase, 0, root, errors)
    prereg = load_json(root / PREREG)
    future = prereg.get("future_beacon", {})
    expected_parameters = {
        "chain_hash": EXPECTED_CHAIN_HASH,
        "genesis_time_unix": EXPECTED_DRAND_GENESIS,
        "period_seconds": EXPECTED_DRAND_PERIOD,
        "round": EXPECTED_BEACON_ROUND,
    }
    for key, expected in expected_parameters.items():
        if future.get(key) != expected:
            add_error(errors, "BEACON_PARAMETER_DRIFT", f"{key}: {future.get(key)!r}")
    if future.get("cross_check_relays") != EXPECTED_RELAYS:
        add_error(errors, "BEACON_RELAY_CONFIG_DRIFT", repr(future.get("cross_check_relays")))
    computed_beacon_time = datetime.fromtimestamp(
        EXPECTED_DRAND_GENESIS
        + (EXPECTED_BEACON_ROUND - 1) * EXPECTED_DRAND_PERIOD,
        tz=timezone.utc,
    )
    if parse_utc(future.get("expected_utc_from_chain_parameters")) != computed_beacon_time:
        add_error(errors, "BEACON_TIME_FORMULA_MISMATCH", computed_beacon_time.isoformat())
    actual_files = {
        path.relative_to(root).as_posix()
        for path in (root / "successor/z_polyspine").rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }
    allowed_future = {
        path
        for path in actual_files
        if re.fullmatch(r"successor/z_polyspine/phases/P[1-3]/.+", path)
    }
    unexpected = actual_files - listed - {P0_SNAPSHOT} - allowed_future
    if unexpected:
        add_error(errors, "P0_UNCOVERED_FILE", repr(sorted(unexpected)))
    return {"snapshot_sha256": digest_file(snapshot_path), "covered_files": len(listed)}


def scan_public_tree(root: Path, errors: list[dict[str, str]]) -> dict[str, int]:
    successor = root / "successor/z_polyspine"
    files = [
        path
        for path in successor.rglob("*")
        if path.is_file()
        and "__pycache__" not in path.parts
        and path.suffix.lower() != ".pyc"
    ]
    folded: dict[str, str] = {}
    json_count = 0
    for path in files:
        relative = path.relative_to(root).as_posix()
        normalized = unicodedata.normalize("NFC", relative)
        key = normalized.casefold()
        if key in folded and folded[key] != relative:
            add_error(errors, "PATH_COLLISION", f"{folded[key]} vs {relative}")
        folded[key] = relative
        if path.is_symlink() or os.path.islink(path):
            add_error(errors, "SYMLINK_FORBIDDEN", relative)
        if path.suffix.lower() not in {".json", ".md", ".py", ".gitignore"} and path.name != ".gitignore":
            add_error(errors, "PUBLIC_FILE_TYPE_FORBIDDEN", relative)
        try:
            path.read_bytes().decode("utf-8")
        except UnicodeDecodeError:
            add_error(errors, "PUBLIC_FILE_NOT_UTF8", relative)
        if path.suffix.lower() == ".json":
            json_count += 1
            try:
                value = load_json(path)
                _walk(value, relative, errors)
            except (OSError, ValueError, DuplicateKeyError) as exc:
                add_error(errors, "JSON_INVALID", f"{relative}: {exc}")
    return {"file_count": len(files), "json_count": json_count}


def _intro_commit(root: Path, relative: str) -> str | None:
    result = git(root, "log", "--reverse", "--diff-filter=A", "--format=%H", "--", relative)
    commits = [line.strip() for line in result.stdout.splitlines() if GIT_SHA.fullmatch(line.strip())]
    return commits[0] if result.returncode == 0 and commits else None


def _blob_at(root: Path, commit: str, relative: str) -> bytes | None:
    result = subprocess.run(
        ["git", "-C", str(root), "show", f"{commit}:{relative}"],
        check=False,
        capture_output=True,
    )
    return result.stdout if result.returncode == 0 else None


def verify_git_history(
    root: Path, errors: list[dict[str, str]], require_remote: bool
) -> dict[str, Any]:
    inside = git(root, "rev-parse", "--is-inside-work-tree")
    if inside.returncode != 0 or inside.stdout.strip() != "true":
        add_error(errors, "NOT_GIT_REPOSITORY", str(root))
        return {}
    actual_tree = git(root, "rev-parse", f"{BASE_COMMIT}^{{tree}}")
    if actual_tree.returncode != 0 or actual_tree.stdout.strip() != BASE_TREE:
        add_error(errors, "BASE_TREE_UNRESOLVED", actual_tree.stdout.strip())
    origin = git(root, "remote", "get-url", "origin")
    normalized_origin = origin.stdout.strip().removesuffix(".git")
    if origin.returncode != 0 or normalized_origin != EXPECTED_ORIGIN:
        add_error(errors, "ORIGIN_MISMATCH", normalized_origin)
    p0_commit = _intro_commit(root, PREREG)
    if p0_commit is None:
        add_error(errors, "P0_NOT_PUBLISHED", "PREREGISTRATION has no introducing commit")
        return {"p0_commit": None}
    phase_paths = []
    for path in (root / "successor/z_polyspine/phases").glob("P*/record.json"):
        relative = path.relative_to(root).as_posix()
        match = PHASE_RECORD.fullmatch(relative)
        if match:
            phase_paths.append((int(match.group(1)), relative, path))
    phase_paths.sort()
    expected_sequences = list(range(len(phase_paths)))
    if [item[0] for item in phase_paths] != expected_sequences:
        add_error(errors, "PHASE_SEQUENCE_GAP", str([item[0] for item in phase_paths]))
    if len(phase_paths) > 4:
        add_error(errors, "PHASE_OUTSIDE_PREREGISTRATION", str(len(phase_paths)))
    records = [load_json(item[2]) for item in phase_paths]
    prereg = load_json(root / PREREG)
    verify_phase_semantics(records, root, prereg, errors, remote=require_remote)
    history = git(root, "rev-list", "--reverse", "--ancestry-path", f"{BASE_COMMIT}..HEAD")
    commits = [line.strip() for line in history.stdout.splitlines() if GIT_SHA.fullmatch(line.strip())]
    if history.returncode != 0:
        add_error(errors, "GIT_HISTORY_FAILED", history.stderr.strip())
    if len(commits) != len(phase_paths):
        add_error(
            errors,
            "ONE_COMMIT_PER_PHASE_FAILURE",
            f"commits={len(commits)} phases={len(phase_paths)}",
        )
    snapshot = load_json(root / P0_SNAPSHOT)
    p0_paths = set(snapshot.get("files", {})) | {P0_SNAPSHOT}
    intro_commits: list[str] = []
    receipt_times: list[datetime] = []
    previous_record_hash: str | None = None
    for sequence, relative, path in phase_paths:
        record = records[sequence]
        intro = _intro_commit(root, relative)
        if intro is None:
            add_error(errors, "PHASE_NOT_COMMITTED", relative)
            continue
        intro_commits.append(intro)
        if sequence >= len(commits) or intro != commits[sequence]:
            add_error(errors, "PHASE_INTRO_COMMIT_MISMATCH", f"P{sequence}: {intro}")
        expected_parent = BASE_COMMIT if sequence == 0 else intro_commits[sequence - 1]
        parent_line = git(root, "rev-list", "--parents", "-n", "1", intro)
        parent_fields = parent_line.stdout.split()
        if len(parent_fields) != 2 or parent_fields[1] != expected_parent:
            add_error(errors, "NON_LINEAR_PHASE_HISTORY", parent_line.stdout.strip())
        if sequence == 0 and intro != p0_commit:
            add_error(errors, "P0_MULTI_COMMIT", f"{intro} != {p0_commit}")
        change_result = git(root, "diff-tree", "--no-commit-id", "--name-status", "-r", expected_parent, intro)
        changed: set[str] = set()
        for line in change_result.stdout.splitlines():
            fields = line.split("\t")
            if len(fields) != 2 or fields[0] != "A":
                add_error(errors, "PHASE_NON_APPEND_CHANGE", line)
                continue
            changed.add(fields[1])
        phase_prefix = f"successor/z_polyspine/phases/P{sequence}/"
        if sequence == 0:
            expected_changed = p0_paths
        else:
            expected_changed = {
                item.relative_to(root).as_posix()
                for item in (root / phase_prefix).rglob("*")
                if item.is_file()
            }
            allowed_phase_files = {
                f"{phase_prefix}record.json",
                f"{phase_prefix}MANIFEST.json",
            }
            if expected_changed != allowed_phase_files:
                add_error(
                    errors,
                    "PHASE_FILE_ALLOWLIST_FAILURE",
                    f"P{sequence}: {sorted(expected_changed)}",
                )
        if changed != expected_changed:
            add_error(
                errors,
                "PHASE_COMMIT_COVERAGE_MISMATCH",
                f"P{sequence}: missing={sorted(expected_changed-changed)} extra={sorted(changed-expected_changed)}",
            )
        if sequence > 0:
            if record.get("prior_public_commit") != intro_commits[sequence - 1]:
                add_error(errors, "PRIOR_PUBLIC_COMMIT_MISMATCH", relative)
            if record.get("previous_phase_record_sha256") != previous_record_hash:
                add_error(errors, "PHASE_CHAIN_HASH_MISMATCH", relative)
            if record.get("authorization_ref") != f"{PREREG}#authorization":
                add_error(errors, "AUTHORIZATION_REFERENCE_MISMATCH", relative)
            receipt_time = verify_receipt(
                record.get("prior_public_receipt"),
                intro_commits[sequence - 1],
                BASE_COMMIT if sequence == 1 else intro_commits[sequence - 2],
                f"refs/heads/{EXPECTED_BRANCH}",
                errors,
                remote=require_remote,
            )
            if receipt_time is not None:
                if receipt_times and receipt_time <= receipt_times[-1]:
                    add_error(errors, "PUBLIC_RECEIPT_ORDER_FAILURE", relative)
                receipt_times.append(receipt_time)
                if sequence == 1:
                    beacon_time = parse_utc(
                        prereg.get("future_beacon", {}).get("expected_utc_from_chain_parameters")
                    )
                    if beacon_time is None or receipt_time >= beacon_time:
                        add_error(errors, "P0_NOT_PUBLIC_BEFORE_BEACON", receipt_time.isoformat())
                if sequence == 2:
                    beacon_time = parse_utc(
                        prereg.get("future_beacon", {}).get("expected_utc_from_chain_parameters")
                    )
                    if beacon_time is None or receipt_time < beacon_time:
                        add_error(errors, "P1_NOT_PUBLIC_AFTER_BEACON", receipt_time.isoformat())
            phase_manifest_path = root / phase_prefix / "MANIFEST.json"
            if not phase_manifest_path.is_file():
                add_error(errors, "PHASE_MANIFEST_MISSING", phase_prefix)
            else:
                phase_manifest = load_json(phase_manifest_path)
                if phase_manifest.get("schema") != "z-polyspine-phase-manifest-v1":
                    add_error(errors, "PHASE_MANIFEST_SCHEMA", phase_prefix)
                if set(phase_manifest) != {"schema", "phase_id", "files"}:
                    add_error(errors, "PHASE_MANIFEST_FIELD_FORBIDDEN", phase_prefix)
                if phase_manifest.get("phase_id") != f"P{sequence}":
                    add_error(errors, "PHASE_MANIFEST_ID", phase_prefix)
                listed = _manifest_files(
                    phase_manifest, root, f"P{sequence}_MANIFEST", errors
                )
                actual = {
                    item.relative_to(root).as_posix()
                    for item in (root / phase_prefix).rglob("*")
                    if item.is_file() and item.name != "MANIFEST.json"
                }
                if listed != actual:
                    add_error(
                        errors,
                        "PHASE_MANIFEST_COVERAGE",
                        f"P{sequence}: missing={sorted(actual-listed)} extra={sorted(listed-actual)}",
                    )
        tree = git(root, "ls-tree", "-r", "--name-only", intro, "--", phase_prefix)
        tree_paths = set(tree.stdout.splitlines())
        if tree_paths != expected_changed.intersection({p for p in expected_changed if p.startswith(phase_prefix)}):
            add_error(errors, "PHASE_TREE_COVERAGE_MISMATCH", f"P{sequence}")
        for introduced_path in tree_paths:
            historical = _blob_at(root, intro, introduced_path)
            current_path = root / introduced_path
            current = current_path.read_bytes() if current_path.is_file() else None
            if historical is None or current != historical:
                add_error(errors, "PHASE_IMMUTABILITY_FAILURE", introduced_path)
        previous_record_hash = digest_file(path)
    status = git(root, "status", "--porcelain=v1", "--untracked-files=all")
    if status.returncode != 0 or status.stdout.strip():
        add_error(errors, "WORKTREE_NOT_CLEAN", status.stdout.strip() or status.stderr.strip())
    branch = git(root, "branch", "--show-current").stdout.strip()
    if branch != EXPECTED_BRANCH:
        add_error(errors, "BRANCH_MISMATCH", branch)
    remote_head = None
    remote_event_chain: dict[str, Any] | None = None
    if require_remote:
        query = git(
            root,
            "ls-remote",
            "origin",
            "refs/heads/main",
            f"refs/heads/{EXPECTED_BRANCH}",
        )
        if query.returncode != 0:
            add_error(errors, "REMOTE_QUERY_FAILED", query.stderr.strip())
        else:
            refs = {
                fields[1]: fields[0]
                for line in query.stdout.splitlines()
                if len(fields := line.split()) == 2
            }
            remote_main = refs.get("refs/heads/main")
            remote_head = refs.get(f"refs/heads/{EXPECTED_BRANCH}")
            head = git(root, "rev-parse", "HEAD").stdout.strip()
            if remote_main != BASE_COMMIT:
                add_error(errors, "REMOTE_MAIN_DRIFT", f"{remote_main} != {BASE_COMMIT}")
            if remote_head != head:
                add_error(errors, "REMOTE_HEAD_MISMATCH", f"{remote_head} != {head}")
        remote_event_chain = verify_remote_branch_event_chain(intro_commits, errors)
    return {
        "p0_commit": p0_commit,
        "phase_introduction_commits": intro_commits,
        "branch": branch,
        "remote_head": remote_head,
        "remote_event_chain": remote_event_chain,
    }


def verify_repository(root: Path, *, git_history: bool, remote: bool = False) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    details: dict[str, Any] = {}
    try:
        details["tree"] = scan_public_tree(root, errors)
        details["p0"] = verify_p0(root, errors)
        if git_history:
            details["git"] = verify_git_history(root, errors, remote)
    except (OSError, ValueError, DuplicateKeyError) as exc:
        add_error(errors, "VERIFIER_EXCEPTION", f"{type(exc).__name__}: {exc}")
    return {
        "ok": not errors,
        "verification_level": "REMOTE_CROSS_CHECKED" if git_history and remote else "LOCAL_ONLY",
        "errors": errors,
        "details": details,
    }


def default_root() -> Path:
    return Path(__file__).resolve().parents[2]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("verify-local", "verify-git"):
        command = sub.add_parser(name)
        command.add_argument("--repo-root", type=Path, default=default_root())
        if name == "verify-git":
            command.add_argument("--offline", action="store_true")
    select = sub.add_parser("select")
    select.add_argument("--randomness", required=True)
    select.add_argument("--repo-root", type=Path, default=default_root())
    replay = sub.add_parser("replay")
    replay.add_argument("--surface", required=True)
    replay.add_argument("--repo-root", type=Path, default=default_root())
    args = parser.parse_args(argv)
    if args.command == "select":
        try:
            prereg = load_json(args.repo_root / PREREG)
            catalog = load_json(args.repo_root / prereg["selection"]["catalog_path"])
            result = {
                "ok": True,
                "randomness": args.randomness,
                "selected": select_candidates(
                    args.randomness, catalog, prereg["selection"]["count"]
                ),
            }
        except (OSError, ValueError, KeyError, DuplicateKeyError) as exc:
            result = {"ok": False, "errors": [{"code": "SELECTION_FAILURE", "message": str(exc)}]}
    elif args.command == "replay":
        try:
            prereg = load_json(args.repo_root / PREREG)
            catalog = load_json(args.repo_root / prereg["selection"]["catalog_path"])
            result = {"ok": True, **replay_surface(args.surface, catalog)}
        except (OSError, ValueError, KeyError, DuplicateKeyError) as exc:
            result = {"ok": False, "errors": [{"code": "REPLAY_FAILURE", "message": str(exc)}]}
    else:
        result = verify_repository(
            args.repo_root.resolve(),
            git_history=args.command == "verify-git",
            remote=args.command == "verify-git" and not getattr(args, "offline", False),
        )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
