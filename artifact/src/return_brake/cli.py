from __future__ import annotations

import argparse
import json
from pathlib import Path

from .runner import create_frozen_manifest, run_pilot, verify_frozen_manifest, verify_run


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="return-brake")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("freeze", help="freeze protocol, cases, implementation, and tests")
    subparsers.add_parser("verify-frozen", help="verify the pre-run frozen manifest")
    run = subparsers.add_parser("run", help="run the frozen pilot through Claude CLI")
    run.add_argument("--model", default="sonnet")
    verify = subparsers.add_parser("verify-run", help="verify receipts and derived analysis")
    verify.add_argument("run_dir", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = project_root()
    if args.command == "freeze":
        manifest = create_frozen_manifest(root)
        print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    if args.command == "verify-frozen":
        ok, problems = verify_frozen_manifest(root)
        print(json.dumps({"ok": ok, "problems": problems}, indent=2))
        return 0 if ok else 1
    if args.command == "run":
        run_dir = run_pilot(root, args.model)
        print(str(run_dir))
        return 0
    if args.command == "verify-run":
        ok, problems = verify_run(root, args.run_dir.resolve())
        print(json.dumps({"ok": ok, "problems": problems}, indent=2))
        return 0 if ok else 1
    raise AssertionError("unreachable")


if __name__ == "__main__":
    raise SystemExit(main())
