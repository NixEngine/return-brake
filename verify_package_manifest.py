from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "PACKAGE_MANIFEST.json"
EXCLUDED_PARTS = {".git", ".pytest_cache", "__pycache__"}
EXCLUDED_NAMES = {MANIFEST.name}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def package_files() -> list[Path]:
    return sorted(
        (
            path
            for path in ROOT.rglob("*")
            if path.is_file()
            and path.name not in EXCLUDED_NAMES
            and not any(part in EXCLUDED_PARTS for part in path.relative_to(ROOT).parts)
            and path.suffix.lower() not in {".pyc", ".pyo"}
        ),
        key=lambda path: path.relative_to(ROOT).as_posix(),
    )


def build() -> dict:
    files = {
        path.relative_to(ROOT).as_posix(): {
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in package_files()
    }
    manifest = {
        "schema": "return-brake-public-package-v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "scope": "All public package files except this manifest, Git metadata, and transient caches.",
        "file_count": len(files),
        "files": files,
    }
    canonical = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    manifest["manifest_payload_sha256"] = hashlib.sha256(canonical).hexdigest()
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def verify() -> tuple[bool, list[str]]:
    problems: list[str] = []
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    expected = manifest.get("files", {})
    observed = {
        path.relative_to(ROOT).as_posix(): {
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in package_files()
    }
    if observed != expected:
        for relative in sorted(set(observed) | set(expected)):
            if observed.get(relative) != expected.get(relative):
                problems.append(f"package file mismatch: {relative}")
    payload = dict(manifest)
    expected_payload_hash = payload.pop("manifest_payload_sha256", None)
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    if hashlib.sha256(canonical).hexdigest() != expected_payload_hash:
        problems.append("manifest payload hash mismatch")
    if manifest.get("file_count") != len(expected):
        problems.append("manifest file count mismatch")
    return not problems, problems


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("build", "verify"))
    args = parser.parse_args()
    if args.command == "build":
        build()
    ok, problems = verify()
    print(json.dumps({"ok": ok, "problems": problems}, ensure_ascii=False, indent=2))
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
