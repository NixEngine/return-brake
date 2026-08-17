from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


BASE_VERIFY_PATH = Path(__file__).resolve().parents[1] / "z_polyspine" / "verify.py"
BASE_SPEC = importlib.util.spec_from_file_location("z_polyspine_frozen_verify", BASE_VERIFY_PATH)
if BASE_SPEC is None or BASE_SPEC.loader is None:
    raise RuntimeError(f"cannot load frozen verifier: {BASE_VERIFY_PATH}")
BASE_VERIFY = importlib.util.module_from_spec(BASE_SPEC)
BASE_SPEC.loader.exec_module(BASE_VERIFY)

CONTRACT_PATH = "successor/z_polyspine_claim_status_v1/SUCCESSOR_CONTRACT.json"
EXPECTED_CONTRACT: dict[str, Any] = {
    "schema": "z-polyspine-claim-status-successor-v1",
    "parent": {
        "phase_id": "P3",
        "commit": "183c3507ed6af268140573e6483b1bacb30de373",
        "record_path": "successor/z_polyspine/phases/P3/record.json",
        "record_sha256": "7eab2cfc6ed35186fa750273c10dea6ae56b731899e1bf1b70e5d8987c5444fe",
    },
    "basis_finding": {
        "phase_id": "P2",
        "record_path": "successor/z_polyspine/phases/P2/record.json",
        "id": "p2-f02",
        "surface": "claim_status_boundaries",
        "result": "FAIL",
        "disposition": "ADD_SUCCESSOR",
    },
    "frozen_baseline": {
        "source_commit": "cbf5ba8fcf81f06fe24d4970e0de860a8eb68cd1",
        "protocol_path": "successor/z_polyspine/CONTRIBUTION_PROTOCOL.json",
        "protocol_sha256": "f9b795c68345182f025b052240aeac22aab4479aee25370564338390488a992d",
        "claim_id_field": "id",
        "immutable_type_fields": ["predicate", "status"],
    },
}


def add_error(errors: list[dict[str, str]], code: str, message: str) -> None:
    errors.append({"code": code, "message": message})


def _git_bytes(root: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=False,
        capture_output=True,
    )


def _load_blob_json(root: Path, commit: str, relative: str) -> tuple[dict[str, Any], bytes]:
    result = _git_bytes(root, "show", f"{commit}:{relative}")
    if result.returncode != 0:
        message = result.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError(message or f"cannot read {commit}:{relative}")
    value = json.loads(
        result.stdout.decode("utf-8"),
        object_pairs_hook=BASE_VERIFY._pairs,
        parse_float=BASE_VERIFY._reject_float,
    )
    if not isinstance(value, dict):
        raise ValueError("frozen protocol must be a JSON object")
    return value, result.stdout


def _claim_type_rows(
    claims: Any,
    *,
    source: str,
    id_field: str,
    type_fields: list[str],
    errors: list[dict[str, str]],
) -> tuple[list[str], dict[str, tuple[Any, ...]]] | None:
    if not isinstance(claims, list):
        add_error(errors, "FROZEN_BASELINE_CLAIMS_INVALID", f"{source}: claims is not a list")
        return None
    ids: list[str] = []
    rows: dict[str, tuple[Any, ...]] = {}
    for index, claim in enumerate(claims):
        if not isinstance(claim, dict):
            add_error(
                errors,
                "FROZEN_BASELINE_CLAIMS_INVALID",
                f"{source}[{index}]: claim is not an object",
            )
            continue
        claim_id = claim.get(id_field)
        if not isinstance(claim_id, str) or not claim_id:
            add_error(
                errors,
                "FROZEN_BASELINE_CLAIMS_INVALID",
                f"{source}[{index}]: invalid {id_field}",
            )
            continue
        ids.append(claim_id)
        if claim_id in rows:
            add_error(
                errors,
                "FROZEN_BASELINE_CLAIM_ID_DUPLICATE",
                f"{source}: {claim_id}",
            )
            continue
        rows[claim_id] = tuple(claim.get(field) for field in type_fields)
    return ids, rows


def verify_claim_type_identity(
    frozen_claims: Any,
    current_claims: Any,
    *,
    id_field: str,
    type_fields: list[str],
    errors: list[dict[str, str]],
) -> dict[str, Any]:
    frozen = _claim_type_rows(
        frozen_claims,
        source="frozen",
        id_field=id_field,
        type_fields=type_fields,
        errors=errors,
    )
    current = _claim_type_rows(
        current_claims,
        source="current",
        id_field=id_field,
        type_fields=type_fields,
        errors=errors,
    )
    if frozen is None or current is None:
        return {}
    frozen_ids, frozen_rows = frozen
    current_ids, current_rows = current
    if frozen_ids != current_ids:
        add_error(
            errors,
            "FROZEN_BASELINE_CLAIM_IDS_MISMATCH",
            f"expected={frozen_ids!r} observed={current_ids!r}",
        )
    for claim_id in frozen_ids:
        if claim_id not in current_rows or claim_id not in frozen_rows:
            continue
        expected = frozen_rows[claim_id]
        observed = current_rows[claim_id]
        if observed != expected:
            expected_fields = dict(zip(type_fields, expected, strict=True))
            observed_fields = dict(zip(type_fields, observed, strict=True))
            add_error(
                errors,
                "FROZEN_BASELINE_CLAIM_TYPE_MISMATCH",
                f"{claim_id}: expected={expected_fields!r} observed={observed_fields!r}",
            )
    return {
        "claim_count": len(frozen_ids),
        "claim_ids_sha256": hashlib.sha256(
            json.dumps(frozen_ids, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
        "immutable_type_fields": type_fields,
    }


def verify_successor_links(root: Path, errors: list[dict[str, str]]) -> dict[str, Any]:
    try:
        observed_contract = BASE_VERIFY.load_json(root / CONTRACT_PATH)
    except (OSError, ValueError, BASE_VERIFY.DuplicateKeyError) as exc:
        add_error(errors, "SUCCESSOR_CONTRACT_INVALID", str(exc))
        return {}
    if observed_contract != EXPECTED_CONTRACT:
        add_error(errors, "SUCCESSOR_CONTRACT_MISMATCH", CONTRACT_PATH)

    parent = EXPECTED_CONTRACT["parent"]
    parent_record = root / parent["record_path"]
    if not parent_record.is_file() or BASE_VERIFY.digest_file(parent_record) != parent["record_sha256"]:
        add_error(errors, "SUCCESSOR_PARENT_RECORD_MISMATCH", parent["record_path"])
    ancestry = BASE_VERIFY.git(root, "merge-base", "--is-ancestor", parent["commit"], "HEAD")
    if ancestry.returncode != 0:
        add_error(errors, "SUCCESSOR_PARENT_NOT_ANCESTOR", parent["commit"])

    finding_contract = EXPECTED_CONTRACT["basis_finding"]
    try:
        p2 = BASE_VERIFY.load_json(root / finding_contract["record_path"])
        p3 = BASE_VERIFY.load_json(root / parent["record_path"])
    except (OSError, ValueError, BASE_VERIFY.DuplicateKeyError) as exc:
        add_error(errors, "SUCCESSOR_LINK_SOURCE_INVALID", str(exc))
        return {}
    findings = p2.get("audit", {}).get("findings", [])
    finding = next(
        (item for item in findings if isinstance(item, dict) and item.get("id") == finding_contract["id"]),
        None,
    )
    if not isinstance(finding, dict) or any(
        finding.get(field) != finding_contract[field]
        for field in ("id", "surface", "result")
    ):
        add_error(errors, "SUCCESSOR_FINDING_LINK_MISMATCH", finding_contract["id"])
    dispositions = p3.get("finding_dispositions", [])
    disposition = next(
        (
            item
            for item in dispositions
            if isinstance(item, dict) and item.get("finding_id") == finding_contract["id"]
        ),
        None,
    )
    if not isinstance(disposition, dict) or disposition.get("disposition") != finding_contract["disposition"]:
        add_error(errors, "SUCCESSOR_DISPOSITION_LINK_MISMATCH", finding_contract["id"])
    required_actions = {"ADD_TYPED_BOUNDARY", "ADD_TEST"}
    observed_actions = {
        item.get("action")
        for item in p3.get("changes", [])
        if isinstance(item, dict) and finding_contract["id"] in item.get("basis_finding_ids", [])
    }
    if observed_actions != required_actions:
        add_error(
            errors,
            "SUCCESSOR_ACTION_LINK_MISMATCH",
            f"expected={sorted(required_actions)!r} observed={sorted(observed_actions)!r}",
        )
    return {
        "parent_phase_id": parent["phase_id"],
        "parent_commit": parent["commit"],
        "basis_finding_id": finding_contract["id"],
        "basis_surface": finding_contract["surface"],
    }


def verify_frozen_baseline(root: Path, errors: list[dict[str, str]]) -> dict[str, Any]:
    boundary = EXPECTED_CONTRACT["frozen_baseline"]
    try:
        frozen_protocol, frozen_blob = _load_blob_json(
            root,
            boundary["source_commit"],
            boundary["protocol_path"],
        )
        current_protocol = BASE_VERIFY.load_json(root / boundary["protocol_path"])
    except (OSError, ValueError, BASE_VERIFY.DuplicateKeyError) as exc:
        add_error(errors, "FROZEN_BASELINE_SOURCE_UNAVAILABLE", str(exc))
        return {}
    frozen_sha256 = hashlib.sha256(frozen_blob).hexdigest()
    if frozen_sha256 != boundary["protocol_sha256"]:
        add_error(
            errors,
            "FROZEN_BASELINE_SOURCE_HASH_MISMATCH",
            f"expected={boundary['protocol_sha256']} observed={frozen_sha256}",
        )
    details = verify_claim_type_identity(
        frozen_protocol.get("baseline_claims"),
        current_protocol.get("baseline_claims"),
        id_field=boundary["claim_id_field"],
        type_fields=boundary["immutable_type_fields"],
        errors=errors,
    )
    return {
        "source_commit": boundary["source_commit"],
        "source_protocol_sha256": frozen_sha256,
        **details,
    }


def verify_repository(root: Path, *, git_history: bool, remote: bool = False) -> dict[str, Any]:
    root = root.resolve()
    base_result = BASE_VERIFY.verify_repository(root, git_history=git_history, remote=remote)
    errors = [dict(item) for item in base_result["errors"]]
    details = {
        "frozen_spine": base_result["details"],
        "successor_links": verify_successor_links(root, errors),
        "frozen_baseline": verify_frozen_baseline(root, errors),
    }
    return {
        "ok": not errors,
        "verification_level": base_result["verification_level"],
        "errors": errors,
        "details": details,
    }


def default_root() -> Path:
    return Path(__file__).resolve().parents[2]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    local = sub.add_parser("verify-local")
    local.add_argument("--repo-root", type=Path, default=default_root())
    history = sub.add_parser("verify-git")
    history.add_argument("--repo-root", type=Path, default=default_root())
    history.add_argument("--offline", action="store_true")
    args = parser.parse_args(argv)
    result = verify_repository(
        args.repo_root,
        git_history=args.command == "verify-git",
        remote=args.command == "verify-git" and not args.offline,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
