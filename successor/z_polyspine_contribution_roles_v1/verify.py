#!/usr/bin/env python3
"""Typed post-P3 successor for contribution-role separation finding p2-f03."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any


PARENT_P3_COMMIT = "183c3507ed6af268140573e6483b1bacb30de373"
PARENT_P3_RECORD = "successor/z_polyspine/phases/P3/record.json"
PARENT_P3_RECORD_SHA256 = (
    "7eab2cfc6ed35186fa750273c10dea6ae56b731899e1bf1b70e5d8987c5444fe"
)
P2_RECORD = "successor/z_polyspine/phases/P2/record.json"
PARENT_VERIFIER = "successor/z_polyspine/verify.py"
CONTRACT_PATH = "successor/z_polyspine_contribution_roles_v1/CONTRACT.json"
BASIS_FINDING_ID = "p2-f03"
SURFACE = "contribution_role_separation"
ERROR_CODE = "MATERIAL_ROLES_COLLAPSED"
MATERIAL_ROLE_FAMILY = (
    "CONCEPTION",
    "AUTHENTICATION",
    "COMMAND_DISPATCH",
    "PROCESS_EXECUTION",
    "PUBLICATION_INITIATION",
)
MINIMUM_DISTINCT_PRINCIPALS = 2


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def add_error(errors: list[dict[str, str]], code: str, message: str) -> None:
    errors.append({"code": code, "message": message})


def expected_contract() -> dict[str, Any]:
    return {
        "schema": "z-polyspine-contribution-role-successor-v1",
        "parent": {
            "commit": PARENT_P3_COMMIT,
            "phase_id": "P3",
            "record_path": PARENT_P3_RECORD,
            "record_sha256": PARENT_P3_RECORD_SHA256,
        },
        "basis": {
            "phase_id": "P2",
            "finding_id": BASIS_FINDING_ID,
            "surface": SURFACE,
            "disposition": "ADD_SUCCESSOR",
        },
        "boundary": {
            "error_code": ERROR_CODE,
            "complete_role_family": list(MATERIAL_ROLE_FAMILY),
            "minimum_distinct_principals": MINIMUM_DISTINCT_PRINCIPALS,
            "other_roles_count_toward_threshold": False,
        },
    }


def load_parent_verifier(root: Path) -> ModuleType:
    module_path = root / PARENT_VERIFIER
    spec = importlib.util.spec_from_file_location("zpoly_frozen_parent_verify", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load frozen parent verifier: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_basis(
    root: Path,
    parent: ModuleType,
    contract: Any,
    errors: list[dict[str, str]],
) -> None:
    if contract != expected_contract():
        add_error(errors, "SUCCESSOR_CONTRACT_MISMATCH", CONTRACT_PATH)

    p3_path = root / PARENT_P3_RECORD
    if sha256_file(p3_path) != PARENT_P3_RECORD_SHA256:
        add_error(errors, "PARENT_P3_RECORD_MISMATCH", PARENT_P3_RECORD)
        return
    p3 = parent.load_json(p3_path)
    dispositions = [
        item
        for item in p3.get("finding_dispositions", [])
        if isinstance(item, dict) and item.get("finding_id") == BASIS_FINDING_ID
    ]
    if (
        p3.get("phase_id") != "P3"
        or p3.get("basis_phase_id") != "P2"
        or len(dispositions) != 1
        or dispositions[0].get("disposition") != "ADD_SUCCESSOR"
    ):
        add_error(errors, "PARENT_P3_BASIS_MISMATCH", BASIS_FINDING_ID)

    p2_path = root / P2_RECORD
    if sha256_file(p2_path) != p3.get("previous_phase_record_sha256"):
        add_error(errors, "P2_TO_P3_CHAIN_MISMATCH", P2_RECORD)
        return
    p2 = parent.load_json(p2_path)
    findings = [
        item
        for item in p2.get("audit", {}).get("findings", [])
        if isinstance(item, dict) and item.get("id") == BASIS_FINDING_ID
    ]
    if (
        len(findings) != 1
        or findings[0].get("surface") != SURFACE
        or findings[0].get("result") != "FAIL"
        or ERROR_CODE not in findings[0].get("verifier_codes", [])
    ):
        add_error(errors, "P2_FINDING_BASIS_MISMATCH", BASIS_FINDING_ID)


def verify_material_role_separation(
    record: Any,
    valid_principals: set[str],
    errors: list[dict[str, str]],
) -> None:
    """Reject one-principal ownership of the complete material role family.

    Roles outside ``MATERIAL_ROLE_FAMILY`` are intentionally excluded from the
    principal threshold, so a verification-only entry cannot mask collapse.
    Structural ledger errors remain the responsibility of the frozen verifier.
    """

    if not isinstance(record, dict):
        return
    entries = record.get("contributions")
    if not isinstance(entries, list):
        return
    owners: dict[str, set[str]] = {role: set() for role in MATERIAL_ROLE_FAMILY}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        role = entry.get("role")
        principal = entry.get("principal")
        if role in owners and principal in valid_principals:
            owners[role].add(principal)
    if not all(owners.values()):
        return
    material_principals = set().union(*(owners[role] for role in MATERIAL_ROLE_FAMILY))
    if len(material_principals) < MINIMUM_DISTINCT_PRINCIPALS:
        phase_id = record.get("phase_id", "?")
        add_error(
            errors,
            ERROR_CODE,
            f"{phase_id}: complete material role family has "
            f"{len(material_principals)} distinct principal; other roles do not count",
        )


def verify_repository(root: Path) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    details: dict[str, Any] = {
        "parent_commit": PARENT_P3_COMMIT,
        "basis_finding_id": BASIS_FINDING_ID,
        "surface": SURFACE,
        "material_role_family": list(MATERIAL_ROLE_FAMILY),
    }
    try:
        parent = load_parent_verifier(root)
        parent_result = parent.verify_repository(root, git_history=False)
        details["frozen_parent_ok"] = parent_result.get("ok", False)
        parent_errors = parent_result.get("errors", [])
        if isinstance(parent_errors, list):
            errors.extend(parent_errors)

        contract = parent.load_json(root / CONTRACT_PATH)
        verify_basis(root, parent, contract, errors)
        protocol = parent.load_json(
            root / "successor/z_polyspine/CONTRIBUTION_PROTOCOL.json"
        )
        valid_principals = {
            item.get("id")
            for item in protocol.get("principals", [])
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        }
        checked: list[str] = []
        phase_root = root / "successor/z_polyspine/phases"
        phase_paths = sorted(
            phase_root.glob("P*/record.json"),
            key=lambda path: int(path.parent.name.removeprefix("P")),
        )
        for path in phase_paths:
            record = parent.load_json(path)
            verify_material_role_separation(record, valid_principals, errors)
            checked.append(record.get("phase_id", path.parent.name))
        details["phase_records_checked"] = checked
    except (OSError, ValueError, RuntimeError) as exc:
        add_error(errors, "SUCCESSOR_VERIFIER_EXCEPTION", f"{type(exc).__name__}: {exc}")
    return {"ok": not errors, "errors": errors, "details": details}


def default_root() -> Path:
    return Path(__file__).resolve().parents[2]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    local = sub.add_parser("verify-local")
    local.add_argument("--repo-root", type=Path, default=default_root())
    args = parser.parse_args(argv)
    result = verify_repository(args.repo_root.resolve())
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
