from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .analysis import analysis_markdown, analyze_records
from .canonical import append_hash_chain, sha256_file, sha256_value, verify_hash_chain
from .protocol import (
    FRAMES,
    HARNESS_INVALID,
    SYSTEM_PROMPT,
    build_independent_prompt,
    build_operational_prompt,
    load_cards,
    parse_model_text,
)


RESTRICTED_SETTINGS = json.dumps(
    {
        "autoMemoryEnabled": False,
        "includeGitInstructions": False,
        "enableAllProjectMcpServers": False,
    },
    separators=(",", ":"),
)

RETAINED_ENVIRONMENT_NAMES = {
    "APPDATA",
    "COMSPEC",
    "HOMEDRIVE",
    "HOMEPATH",
    "LANG",
    "LC_ALL",
    "LOCALAPPDATA",
    "PATH",
    "PATHEXT",
    "PROCESSOR_ARCHITECTURE",
    "PROGRAMDATA",
    "SYSTEMDRIVE",
    "SYSTEMROOT",
    "TEMP",
    "TMP",
    "USERDOMAIN",
    "USERNAME",
    "USERPROFILE",
    "WINDIR",
}


FROZEN_FILES = (
    "README.md",
    "RIGHTS.md",
    "TARGET_CONTEXT_DISCLOSURE.md",
    "PREREGISTRATION.md",
    "pyproject.toml",
    "data/bridge_cards.json",
    "src/return_brake/__init__.py",
    "src/return_brake/canonical.py",
    "src/return_brake/protocol.py",
    "src/return_brake/analysis.py",
    "src/return_brake/runner.py",
    "src/return_brake/cli.py",
    "tests/test_protocol.py",
)

GLOBAL_CLAUDE_CONTEXT = Path.home() / ".claude" / "CLAUDE.md"
GLOBAL_CLAUDE_SETTINGS = Path.home() / ".claude" / "settings.json"
RESIDUAL_CONTEXT_NOT_CHECKED = [
    "provider-side system behavior",
    "provider-side model updates during the run",
    "effects not exposed by Claude CLI",
]
SESSION_NAME = "return-brake-pilot"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_jsonl(path: Path, values: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for value in values:
            handle.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            values.append(json.loads(line))
    return values


def command_version(command: str) -> str | None:
    command_path = Path(command)
    executable = str(command_path) if command_path.is_file() else shutil.which(command)
    if not executable:
        return None
    completed = subprocess.run(
        [executable, "--version"],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return (completed.stdout or completed.stderr).strip() or None


def resolve_claude_executable() -> str | None:
    wrapper = shutil.which("claude")
    candidates: list[Path] = []
    if wrapper:
        wrapper_path = Path(wrapper)
        candidates.append(
            wrapper_path.parent
            / "node_modules"
            / "@anthropic-ai"
            / "claude-code"
            / "bin"
            / ("claude.exe" if os.name == "nt" else "claude")
        )
        if wrapper_path.suffix.lower() == ".exe":
            candidates.append(wrapper_path)
    direct = shutil.which("claude.exe") if os.name == "nt" else None
    if direct:
        candidates.append(Path(direct))
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate.resolve())
    return wrapper


def executable_receipt(executable: str | None) -> dict[str, Any]:
    if not executable or not Path(executable).is_file():
        return {
            "present": False,
            "basename": Path(executable).name if executable else None,
            "sha256": None,
            "bytes": None,
        }
    path = Path(executable)
    return {
        "present": True,
        "basename": path.name,
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
    }


def restricted_environment() -> dict[str, str]:
    retained = {
        name: value
        for name, value in os.environ.items()
        if name.upper() in RETAINED_ENVIRONMENT_NAMES
    }
    retained["PYTHONIOENCODING"] = "utf-8"
    return retained


def frozen_hashes(root: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for relative in FROZEN_FILES:
        path = root / relative
        if not path.is_file():
            raise FileNotFoundError(f"missing frozen file: {relative}")
        hashes[relative] = sha256_file(path)
    return hashes


def _external_file_receipt(path: Path, identifier: str) -> dict[str, Any]:
    if not path.is_file():
        return {
            "identifier": identifier,
            "present": False,
            "sha256": None,
            "bytes": None,
            "lines": None,
        }
    payload = path.read_bytes()
    return {
        "identifier": identifier,
        "present": True,
        "sha256": sha256_file(path),
        "bytes": len(payload),
        "lines": len(payload.decode("utf-8", errors="replace").splitlines()),
    }


def external_context_receipt() -> dict[str, Any]:
    return {
        "user_global_claude_md": _external_file_receipt(
            GLOBAL_CLAUDE_CONTEXT, "user_global_claude_md"
        ),
        "user_global_settings_json": _external_file_receipt(
            GLOBAL_CLAUDE_SETTINGS, "user_global_settings_json"
        ),
    }


def sterile_directory_receipt(root: Path) -> dict[str, Any]:
    sterile = root / "runtime" / "sterile"
    if not sterile.is_dir():
        return {"present": False, "entries": []}
    entries: list[dict[str, Any]] = []
    for path in sorted(sterile.rglob("*"), key=lambda item: item.as_posix()):
        relative = path.relative_to(sterile).as_posix()
        entries.append(
            {
                "path": relative,
                "type": "directory" if path.is_dir() else "file",
                "sha256": sha256_file(path) if path.is_file() else None,
            }
        )
    return {"present": True, "entries": entries}


def runtime_preconditions(root: Path) -> dict[str, Any]:
    claude_executable = resolve_claude_executable()
    return {
        "adapter": "claude_cli",
        "claude_cli_version": (
            command_version(claude_executable) if claude_executable else None
        ),
        "claude_executable": executable_receipt(claude_executable),
        "python": sys.version,
        "platform": platform.platform(),
        "retained_environment_names": sorted(restricted_environment()),
        "sterile_directory": sterile_directory_receipt(root),
    }


def expected_sequence_keys(cards_data: dict[str, Any]) -> list[list[str | None]]:
    keys: list[list[str | None]] = []
    for card_index, card in enumerate(cards_data["cards"]):
        frame_order = list(FRAMES)
        if card_index % 2:
            frame_order.reverse()
        for frame in frame_order:
            keys.extend(
                [
                    [card["id"], frame, "direct", None],
                    [card["id"], frame, "cost", None],
                    [card["id"], frame, "operational", "INITIAL"],
                    [card["id"], frame, "operational", "PRESSURE_ONLY"],
                    [
                        card["id"],
                        frame,
                        "operational",
                        "RESOLUTION_ASSERTED",
                    ],
                ]
            )
    return keys


def create_frozen_manifest(root: Path) -> dict[str, Any]:
    cards_data = load_cards(root / "data" / "bridge_cards.json")
    sequence = expected_sequence_keys(cards_data)
    manifest = {
        "schema_version": "return-brake.frozen-manifest.v1",
        "frozen_at_utc": utc_now(),
        "files": frozen_hashes(root),
        "external_context": external_context_receipt(),
        "runtime_preconditions": runtime_preconditions(root),
        "protocol_constants": {
            "frames": sorted(FRAMES),
            "methods": ["direct", "cost", "operational"],
            "operational_stages": ["INITIAL", "PRESSURE_ONLY", "RESOLUTION_ASSERTED"],
            "sampling_repetitions_per_cell": 1,
            "expected_sequence_sha256": sha256_value(sequence),
            "expected_call_count": len(sequence),
        },
        "manifest_scope": (
            "Integrity receipt for pre-registered inputs and implementation; not proof of scientific validity."
        ),
    }
    manifest["manifest_hash"] = sha256_value(manifest)
    write_json(root / "FROZEN_MANIFEST.json", manifest)
    return manifest


def verify_frozen_manifest(root: Path) -> tuple[bool, list[str]]:
    path = root / "FROZEN_MANIFEST.json"
    if not path.is_file():
        return False, ["FROZEN_MANIFEST.json is missing"]
    manifest = json.loads(path.read_text(encoding="utf-8"))
    expected_manifest_hash = manifest.get("manifest_hash")
    payload = dict(manifest)
    payload.pop("manifest_hash", None)
    problems: list[str] = []
    if sha256_value(payload) != expected_manifest_hash:
        problems.append("manifest_hash mismatch")
    observed = frozen_hashes(root)
    if observed != manifest.get("files"):
        for relative in sorted(set(observed) | set(manifest.get("files", {}))):
            if observed.get(relative) != manifest.get("files", {}).get(relative):
                problems.append(f"frozen file mismatch: {relative}")
    if manifest.get("external_context") != external_context_receipt():
        problems.append("external target context receipt mismatch")
    if manifest.get("runtime_preconditions") != runtime_preconditions(root):
        problems.append("runtime preconditions mismatch")
    cards_data = load_cards(root / "data" / "bridge_cards.json")
    sequence = expected_sequence_keys(cards_data)
    constants = manifest.get("protocol_constants", {})
    if constants.get("expected_sequence_sha256") != sha256_value(sequence):
        problems.append("expected sequence hash mismatch")
    if constants.get("expected_call_count") != len(sequence):
        problems.append("expected call count mismatch")
    return not problems, problems


@dataclass
class AdapterResult:
    exit_code: int
    outer: dict[str, Any] | None
    model_text: str
    stdout: str
    stderr: str
    runtime_symptom: str | None


class ClaudeCLIAdapter:
    def __init__(self, model: str, sterile_dir: Path, timeout_seconds: int = 180):
        executable = resolve_claude_executable()
        if not executable:
            raise RuntimeError("claude executable not found")
        self.executable = executable
        self.model = model
        self.sterile_dir = sterile_dir
        self.timeout_seconds = timeout_seconds

    def preflight(self) -> tuple[bool, str]:
        command = [
            self.executable,
            "--setting-sources",
            "user",
            "--settings",
            RESTRICTED_SETTINGS,
            "--strict-mcp-config",
            "auth",
            "status",
        ]
        completed = subprocess.run(
            command,
            cwd=self.sterile_dir,
            env=restricted_environment(),
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        return completed.returncode == 0, f"exit_{completed.returncode}"

    def invocation_command(self) -> list[str]:
        return [
            self.executable,
            "--print",
            "--model",
            self.model,
            "--setting-sources",
            "user",
            "--settings",
            RESTRICTED_SETTINGS,
            "--strict-mcp-config",
            "--system-prompt",
            SYSTEM_PROMPT,
            "--tools",
            "",
            "--disable-slash-commands",
            "--no-session-persistence",
            "--name",
            SESSION_NAME,
            "--no-chrome",
            "--permission-mode",
            "dontAsk",
            "--output-format",
            "json",
        ]

    def invoke(self, prompt: str) -> AdapterResult:
        command = self.invocation_command()
        environment = restricted_environment()
        started = utc_now()
        try:
            completed = subprocess.run(
                command,
                input=prompt,
                cwd=self.sterile_dir,
                env=environment,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout if isinstance(exc.stdout, str) else ""
            stderr = exc.stderr if isinstance(exc.stderr, str) else ""
            return AdapterResult(124, None, "", stdout, stderr, "runtime_timeout")
        outer: dict[str, Any] | None = None
        model_text = ""
        symptom: str | None = None
        if completed.returncode != 0:
            symptom = f"runtime_exit_{completed.returncode}"
        try:
            decoded = json.loads(completed.stdout)
            if isinstance(decoded, dict):
                outer = decoded
                if decoded.get("is_error") is True:
                    symptom = symptom or "outer_reported_error"
                if isinstance(decoded.get("result"), str):
                    model_text = decoded["result"]
                else:
                    symptom = symptom or "outer_result_missing"
            else:
                symptom = symptom or "outer_json_not_object"
        except json.JSONDecodeError:
            symptom = symptom or "outer_json_parse"
        if outer is not None:
            outer = dict(outer)
            outer["local_invocation_started_utc"] = started
        return AdapterResult(
            completed.returncode,
            outer,
            model_text,
            completed.stdout,
            completed.stderr,
            symptom,
        )


def _public_outer_metadata(outer: dict[str, Any] | None) -> dict[str, Any] | None:
    if outer is None:
        return None
    allowed = {
        "duration_ms",
        "duration_api_ms",
        "is_error",
        "num_turns",
        "result",
        "stop_reason",
        "total_cost_usd",
        "usage",
        "modelUsage",
        "permission_denials",
        "local_invocation_started_utc",
    }
    return {key: outer[key] for key in sorted(allowed) if key in outer}


def model_ids_from_outer(outer: dict[str, Any] | None) -> list[str]:
    if not isinstance(outer, dict):
        return []
    model_usage = outer.get("modelUsage") or {}
    if not isinstance(model_usage, dict):
        return []
    return sorted(str(model_id) for model_id in model_usage)


def _observation_from_adapter(
    *,
    call_id: str,
    card_id: str,
    frame: str,
    method: str,
    stage: str | None,
    prompt: str,
    adapter_result: AdapterResult,
) -> dict[str, Any]:
    parsed = parse_model_text(adapter_result.model_text)
    runtime_model_ids = model_ids_from_outer(adapter_result.outer)
    symptoms = [
        item
        for item in (adapter_result.runtime_symptom, parsed.symptom)
        if item is not None
    ]
    if len(runtime_model_ids) != 1:
        symptoms.append("runtime_model_identity_missing_or_ambiguous")
    symptom = ";".join(symptoms) if symptoms else None
    valid_observation = (
        adapter_result.exit_code == 0
        and adapter_result.runtime_symptom is None
        and parsed.symptom is None
        and len(runtime_model_ids) == 1
    )
    choice = parsed.choice if valid_observation else HARNESS_INVALID
    return {
        "call_id": call_id,
        "card_id": card_id,
        "frame": frame,
        "method": method,
        "stage": stage,
        "prompt_sha256": sha256_value(prompt),
        "prompt": prompt,
        "model_text": adapter_result.model_text,
        "parsed": parsed.parsed,
        "parser_candidate_choice": parsed.choice,
        "choice": choice,
        "symptom": symptom,
        "exit_code": adapter_result.exit_code,
        "valid_observation": valid_observation,
        "runtime_model_ids": runtime_model_ids,
        "public_runtime_metadata": _public_outer_metadata(adapter_result.outer),
        "epistemic_status": {
            "observed": ["prompt", "model_text", "parsed fields", "runtime metadata"],
            "inferred": (
                ["eligible choice label after deterministic parser"]
                if valid_observation
                else []
            ),
            "not_checked": [
                "truth of the model's stated basis",
                "internal causal mechanism",
                "intrinsic preference",
            ],
        },
    }


def normalized_history_observation(record: dict[str, Any], stage: str) -> dict[str, Any]:
    if record.get("valid_observation") is True and isinstance(record.get("parsed"), dict):
        model_response: dict[str, Any] = record["parsed"]
    else:
        model_response = {
            "choice": HARNESS_INVALID,
            "symptom": record.get("symptom") or "invalid_observation",
        }
    return {"stage": stage, "model_response": model_response}


def effective_model_ids(records: list[dict[str, Any]]) -> list[str]:
    observed: set[str] = set()
    for record in records:
        ids = record.get("runtime_model_ids")
        if isinstance(ids, list):
            observed.update(str(model_id) for model_id in ids)
    return sorted(observed)


def run_pilot(root: Path, model: str) -> Path:
    ok, problems = verify_frozen_manifest(root)
    if not ok:
        raise RuntimeError("frozen manifest verification failed: " + "; ".join(problems))
    cards_data = load_cards(root / "data" / "bridge_cards.json")
    adapter = ClaudeCLIAdapter(model=model, sterile_dir=root / "runtime" / "sterile")
    preflight_ok, preflight_status = adapter.preflight()
    if not preflight_ok:
        raise RuntimeError(f"restricted Claude CLI preflight failed: {preflight_status}")
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + f"-{model.replace('/', '_')}"
    run_dir = root / "runs" / run_id
    raw_dir = run_dir / "raw_private"
    raw_dir.mkdir(parents=True, exist_ok=False)
    frozen_snapshot = json.loads(
        (root / "FROZEN_MANIFEST.json").read_text(encoding="utf-8")
    )
    write_json(run_dir / "frozen_manifest_snapshot.json", frozen_snapshot)

    manifest = {
        "schema_version": "return-brake.run-manifest.v1",
        "run_id": run_id,
        "started_at_utc": utc_now(),
        "adapter": "claude_cli",
        "requested_model": model,
        "claude_cli_version": command_version(adapter.executable),
        "claude_executable": executable_receipt(adapter.executable),
        "restricted_auth_preflight": preflight_status,
        "python": sys.version,
        "platform": platform.platform(),
        "sampling_parameters": "NOT_CHECKED: Claude Code CLI does not expose temperature, top_p, or seed here.",
        "isolation": {
            "bare_mode": "unavailable with the active OAuth/keychain authentication",
            "setting_sources": ["user"],
            "settings_overrides": json.loads(RESTRICTED_SETTINGS),
            "strict_mcp_config": True,
            "tools": [],
            "session_persistence": False,
            "session_name": SESSION_NAME,
            "chrome": False,
            "retained_environment_names": sorted(restricted_environment()),
            "residual_not_checked": RESIDUAL_CONTEXT_NOT_CHECKED,
        },
        "frozen_manifest_sha256": sha256_file(root / "FROZEN_MANIFEST.json"),
        "planned_calls": len(cards_data["cards"]) * len(FRAMES) * 5,
    }
    write_json(run_dir / "run_manifest.json", manifest)

    records: list[dict[str, Any]] = []
    call_number = 0
    run_effective_model_id: str | None = None

    def invoke(
        card: dict[str, Any],
        frame: str,
        method: str,
        prompt: str,
        stage: str | None = None,
    ) -> dict[str, Any]:
        nonlocal call_number, run_effective_model_id
        call_number += 1
        call_id = f"call-{call_number:03d}-{card['id']}-{frame.lower()}-{method}"
        if stage:
            call_id += "-" + stage.lower()
        result = adapter.invoke(prompt)
        private_raw = {
            "call_id": call_id,
            "exit_code": result.exit_code,
            "runtime_symptom": result.runtime_symptom,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "outer": result.outer,
        }
        raw_path = raw_dir / f"{call_id}.json"
        write_json(raw_path, private_raw)
        observation = _observation_from_adapter(
            call_id=call_id,
            card_id=card["id"],
            frame=frame,
            method=method,
            stage=stage,
            prompt=prompt,
            adapter_result=result,
        )
        observation["raw_private_sha256"] = sha256_file(raw_path)
        if len(observation["runtime_model_ids"]) == 1:
            observed_model_id = observation["runtime_model_ids"][0]
            if run_effective_model_id is None:
                run_effective_model_id = observed_model_id
            elif observed_model_id != run_effective_model_id:
                observation["valid_observation"] = False
                observation["choice"] = HARNESS_INVALID
                observation["symptom"] = "runtime_model_substitution"
        records.append(observation)
        write_jsonl(run_dir / "observations.partial.jsonl", records)
        print(
            f"{call_number}/{manifest['planned_calls']} {call_id}: {observation['choice']}",
            flush=True,
        )
        if observation["symptom"] == "runtime_model_substitution":
            raise RuntimeError(
                "effective model changed during the frozen run; partial observations retained"
            )
        return observation

    for card_index, card in enumerate(cards_data["cards"]):
        frame_order = list(FRAMES)
        if card_index % 2:
            frame_order.reverse()
        for frame in frame_order:
            direct_prompt = build_independent_prompt(card, frame, "direct")
            invoke(card, frame, "direct", direct_prompt)

            cost_prompt = build_independent_prompt(card, frame, "cost")
            invoke(card, frame, "cost", cost_prompt)

            initial_prompt = build_operational_prompt(card, frame, "INITIAL")
            initial = invoke(card, frame, "operational", initial_prompt, "INITIAL")
            prior = [normalized_history_observation(initial, "INITIAL")]

            pressure_prompt = build_operational_prompt(
                card, frame, "PRESSURE_ONLY", prior_observations=prior
            )
            pressure = invoke(
                card, frame, "operational", pressure_prompt, "PRESSURE_ONLY"
            )
            prior.append(normalized_history_observation(pressure, "PRESSURE_ONLY"))

            resolved_prompt = build_operational_prompt(
                card, frame, "RESOLUTION_ASSERTED", prior_observations=prior
            )
            invoke(
                card,
                frame,
                "operational",
                resolved_prompt,
                "RESOLUTION_ASSERTED",
            )

    chained = append_hash_chain(records)
    write_jsonl(run_dir / "observations.jsonl", chained)
    partial = run_dir / "observations.partial.jsonl"
    if partial.exists():
        partial.unlink()
    analysis = analyze_records(chained)
    analysis["run_id"] = run_id
    analysis["model_requested"] = model
    analysis["analysis_at_utc"] = utc_now()
    analysis["receipt_head"] = chained[-1]["record_hash"] if chained else None
    effective_models = effective_model_ids(chained)
    analysis["effective_models"] = effective_models
    write_json(run_dir / "analysis.json", analysis)
    (run_dir / "RESULTS.md").write_text(analysis_markdown(analysis), encoding="utf-8")
    manifest["completed_at_utc"] = utc_now()
    manifest["observed_calls"] = len(records)
    manifest["receipt_head"] = analysis["receipt_head"]
    manifest["effective_models"] = effective_models
    write_json(run_dir / "run_manifest.json", manifest)
    return run_dir


def verify_run(root: Path, run_dir: Path) -> tuple[bool, list[str]]:
    problems: list[str] = []
    frozen_ok, frozen_problems = verify_frozen_manifest(root)
    if not frozen_ok:
        problems.extend(frozen_problems)
    current_frozen_path = root / "FROZEN_MANIFEST.json"
    snapshot_path = run_dir / "frozen_manifest_snapshot.json"
    if not snapshot_path.is_file():
        problems.append("frozen_manifest_snapshot.json is missing")
    else:
        current_frozen = json.loads(current_frozen_path.read_text(encoding="utf-8"))
        frozen_snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        if frozen_snapshot != current_frozen:
            problems.append("frozen manifest snapshot differs from current frozen manifest")

    observations_path = run_dir / "observations.jsonl"
    if not observations_path.is_file():
        problems.append("observations.jsonl is missing")
        return False, problems
    records = read_jsonl(observations_path)
    chain_ok, chain_problem = verify_hash_chain(records)
    if not chain_ok and chain_problem:
        problems.append(chain_problem)

    cards_data = load_cards(root / "data" / "bridge_cards.json")
    cards_by_id = {card["id"]: card for card in cards_data["cards"]}
    expected_keys: set[tuple[str, str, str, str | None]] = set()
    for card_id in cards_by_id:
        for frame in FRAMES:
            expected_keys.add((card_id, frame, "direct", None))
            expected_keys.add((card_id, frame, "cost", None))
            expected_keys.add((card_id, frame, "operational", "INITIAL"))
            expected_keys.add((card_id, frame, "operational", "PRESSURE_ONLY"))
            expected_keys.add(
                (card_id, frame, "operational", "RESOLUTION_ASSERTED")
            )

    observed_by_key: dict[
        tuple[str, str, str, str | None], dict[str, Any]
    ] = {}
    duplicate_keys: list[tuple[str, str, str, str | None]] = []
    call_ids: set[str] = set()
    for record in records:
        key = (
            record.get("card_id"),
            record.get("frame"),
            record.get("method"),
            record.get("stage"),
        )
        if key in observed_by_key:
            duplicate_keys.append(key)
        observed_by_key[key] = record
        call_id = record.get("call_id")
        if not isinstance(call_id, str) or call_id in call_ids:
            problems.append(f"missing or duplicate call_id: {call_id}")
        elif call_id:
            call_ids.add(call_id)
        prompt = record.get("prompt")
        if not isinstance(prompt, str):
            problems.append(f"prompt missing for {call_id}")
        elif record.get("prompt_sha256") != sha256_value(prompt):
            problems.append(f"prompt_sha256 mismatch for {call_id}")
        model_text = record.get("model_text")
        if not isinstance(model_text, str):
            problems.append(f"model_text missing for {call_id}")
            reparsed = parse_model_text("")
        else:
            reparsed = parse_model_text(model_text)
        if record.get("parsed") != reparsed.parsed:
            problems.append(f"parsed payload differs from model_text for {call_id}")
        if record.get("parser_candidate_choice") != reparsed.choice:
            problems.append(f"parser candidate differs from model_text for {call_id}")
        metadata = record.get("public_runtime_metadata")
        metadata_model_ids = model_ids_from_outer(metadata)
        metadata_result_matches = (
            isinstance(metadata, dict)
            and isinstance(metadata.get("result"), str)
            and metadata["result"] == model_text
        )
        record_exit_code = record.get("exit_code")
        record_exit_code_is_int = isinstance(record_exit_code, int) and not isinstance(
            record_exit_code, bool
        )
        if not record_exit_code_is_int:
            problems.append(f"observation exit_code is not an integer for {call_id}")
        expected_valid = (
            record_exit_code_is_int
            and record_exit_code == 0
            and reparsed.symptom is None
            and isinstance(metadata, dict)
            and metadata.get("is_error") is not True
            and metadata_result_matches
            and len(metadata_model_ids) == 1
        )
        valid = record.get("valid_observation") is True
        if valid != expected_valid:
            problems.append(f"validity gate differs from recomputed eligibility for {call_id}")
        expected_choice = reparsed.choice if expected_valid else HARNESS_INVALID
        if record.get("choice") != expected_choice:
            problems.append(f"choice differs from recomputed eligibility for {call_id}")
        if expected_valid and record.get("symptom") is not None:
            problems.append(f"eligible observation retained a symptom for {call_id}")
        if not expected_valid and not isinstance(record.get("symptom"), str):
            problems.append(f"ineligible observation lacks a symptom for {call_id}")
        elif not expected_valid and not record.get("symptom", "").strip():
            problems.append(f"ineligible observation has an empty symptom for {call_id}")
        if reparsed.symptom is not None and reparsed.symptom not in str(
            record.get("symptom")
        ):
            problems.append(f"parser symptom not retained for {call_id}")
        if isinstance(metadata, dict) and "result" in metadata and metadata["result"] != record.get("model_text"):
            problems.append(f"runtime result differs from model_text for {call_id}")
        if record.get("runtime_model_ids") != metadata_model_ids:
            problems.append(f"runtime model identity mismatch for {call_id}")
        if expected_valid and len(metadata_model_ids) != 1:
            problems.append(f"valid observation lacks one effective model for {call_id}")

    if duplicate_keys:
        problems.append(f"duplicate experimental cells: {duplicate_keys}")
    missing = sorted(expected_keys - set(observed_by_key), key=repr)
    extras = sorted(set(observed_by_key) - expected_keys, key=repr)
    if missing:
        problems.append(f"missing experimental cells: {missing}")
    if extras:
        problems.append(f"unexpected experimental cells: {extras}")
    if len(records) != len(expected_keys):
        problems.append(
            f"observation count mismatch: expected {len(expected_keys)}, got {len(records)}"
        )
    expected_sequence = expected_sequence_keys(cards_data)
    observed_sequence = [
        [
            record.get("card_id"),
            record.get("frame"),
            record.get("method"),
            record.get("stage"),
        ]
        for record in records
    ]
    if observed_sequence != expected_sequence:
        problems.append("experimental call sequence differs from frozen sequence")

    def compare_prompt(
        key: tuple[str, str, str, str | None], expected_prompt: str
    ) -> None:
        record = observed_by_key.get(key)
        if record is not None and record.get("prompt") != expected_prompt:
            problems.append(f"prompt regeneration mismatch: {key}")

    for card_id, card in cards_by_id.items():
        for frame in FRAMES:
            direct_key = (card_id, frame, "direct", None)
            cost_key = (card_id, frame, "cost", None)
            initial_key = (card_id, frame, "operational", "INITIAL")
            pressure_key = (card_id, frame, "operational", "PRESSURE_ONLY")
            resolution_key = (
                card_id,
                frame,
                "operational",
                "RESOLUTION_ASSERTED",
            )
            compare_prompt(
                direct_key, build_independent_prompt(card, frame, "direct")
            )
            compare_prompt(cost_key, build_independent_prompt(card, frame, "cost"))
            compare_prompt(
                initial_key, build_operational_prompt(card, frame, "INITIAL")
            )
            initial_record = observed_by_key.get(initial_key)
            if initial_record is not None:
                prior = [normalized_history_observation(initial_record, "INITIAL")]
                compare_prompt(
                    pressure_key,
                    build_operational_prompt(
                        card, frame, "PRESSURE_ONLY", prior_observations=prior
                    ),
                )
                pressure_record = observed_by_key.get(pressure_key)
                if pressure_record is not None:
                    prior.append(
                        normalized_history_observation(
                            pressure_record, "PRESSURE_ONLY"
                        )
                    )
                    compare_prompt(
                        resolution_key,
                        build_operational_prompt(
                            card,
                            frame,
                            "RESOLUTION_ASSERTED",
                            prior_observations=prior,
                        ),
                    )

    receipt_head = records[-1].get("record_hash") if records else None
    effective_models = effective_model_ids(records)
    if any(record.get("valid_observation") is True for record in records) and not effective_models:
        problems.append("effective model identity is absent from valid runtime metadata")
    valid_model_ids = {
        record["runtime_model_ids"][0]
        for record in records
        if record.get("valid_observation") is True
        and isinstance(record.get("runtime_model_ids"), list)
        and len(record["runtime_model_ids"]) == 1
    }
    if len(valid_model_ids) > 1:
        problems.append("effective model substitution detected across valid observations")
    if len(effective_models) > 1:
        problems.append("effective model substitution detected in runtime metadata")

    run_manifest_path = run_dir / "run_manifest.json"
    run_manifest: dict[str, Any] | None = None
    if not run_manifest_path.is_file():
        problems.append("run_manifest.json is missing")
    else:
        run_manifest = json.loads(run_manifest_path.read_text(encoding="utf-8"))
        required_manifest_fields = {
            "schema_version",
            "run_id",
            "started_at_utc",
            "completed_at_utc",
            "adapter",
            "requested_model",
            "claude_cli_version",
            "claude_executable",
            "restricted_auth_preflight",
            "python",
            "platform",
            "sampling_parameters",
            "isolation",
            "frozen_manifest_sha256",
            "planned_calls",
            "observed_calls",
            "receipt_head",
            "effective_models",
        }
        missing_manifest_fields = sorted(required_manifest_fields - set(run_manifest))
        if missing_manifest_fields:
            problems.append(
                f"run manifest missing required fields: {missing_manifest_fields}"
            )
        if run_manifest.get("schema_version") != "return-brake.run-manifest.v1":
            problems.append("run manifest schema_version mismatch")
        if run_manifest.get("run_id") != run_dir.name:
            problems.append("run manifest run_id mismatch")
        if run_manifest.get("adapter") != "claude_cli":
            problems.append("run manifest adapter mismatch")
        if not isinstance(run_manifest.get("requested_model"), str) or not run_manifest.get(
            "requested_model", ""
        ).strip():
            problems.append("run manifest requested_model is missing")
        for field in ("claude_cli_version", "python", "platform"):
            if not isinstance(run_manifest.get(field), str) or not run_manifest.get(
                field, ""
            ).strip():
                problems.append(f"run manifest {field} is missing")
        if run_manifest.get("restricted_auth_preflight") != "exit_0":
            problems.append("run manifest restricted auth preflight mismatch")
        sampling = run_manifest.get("sampling_parameters")
        if not isinstance(sampling, str) or not sampling.startswith("NOT_CHECKED:"):
            problems.append("run manifest sampling_parameters mismatch")
        manifest_timestamps: dict[str, datetime] = {}
        for field in ("started_at_utc", "completed_at_utc"):
            timestamp = run_manifest.get(field)
            try:
                parsed_timestamp = datetime.fromisoformat(
                    timestamp.replace("Z", "+00:00")
                )
                if (
                    parsed_timestamp.tzinfo is None
                    or parsed_timestamp.utcoffset() is None
                    or parsed_timestamp.utcoffset().total_seconds() != 0
                ):
                    raise ValueError("UTC timezone missing")
                manifest_timestamps[field] = parsed_timestamp
            except (AttributeError, TypeError, ValueError):
                problems.append(f"run manifest {field} is not a UTC timestamp")
        if (
            "started_at_utc" in manifest_timestamps
            and "completed_at_utc" in manifest_timestamps
            and manifest_timestamps["completed_at_utc"]
            < manifest_timestamps["started_at_utc"]
        ):
            problems.append("run manifest completed_at_utc precedes started_at_utc")
        isolation = run_manifest.get("isolation")
        expected_isolation_values = {
            "bare_mode": "unavailable with the active OAuth/keychain authentication",
            "setting_sources": ["user"],
            "settings_overrides": json.loads(RESTRICTED_SETTINGS),
            "strict_mcp_config": True,
            "tools": [],
            "session_persistence": False,
            "session_name": SESSION_NAME,
            "chrome": False,
        }
        if not isinstance(isolation, dict):
            problems.append("run manifest isolation contract is missing")
        else:
            for key, expected_value in expected_isolation_values.items():
                if isolation.get(key) != expected_value:
                    problems.append(f"run manifest isolation mismatch: {key}")
            frozen_runtime = json.loads(
                current_frozen_path.read_text(encoding="utf-8")
            ).get("runtime_preconditions", {})
            if isolation.get("retained_environment_names") != frozen_runtime.get(
                "retained_environment_names"
            ):
                problems.append("run manifest retained environment receipt mismatch")
            if isolation.get("residual_not_checked") != RESIDUAL_CONTEXT_NOT_CHECKED:
                problems.append("run manifest residual context disclosure mismatch")
        frozen_runtime = json.loads(
            current_frozen_path.read_text(encoding="utf-8")
        ).get("runtime_preconditions", {})
        for manifest_field, frozen_field in (
            ("adapter", "adapter"),
            ("claude_cli_version", "claude_cli_version"),
            ("claude_executable", "claude_executable"),
            ("python", "python"),
            ("platform", "platform"),
        ):
            if run_manifest.get(manifest_field) != frozen_runtime.get(frozen_field):
                problems.append(
                    f"run manifest runtime precondition mismatch: {manifest_field}"
                )
        if run_manifest.get("planned_calls") != len(expected_keys):
            problems.append("run manifest planned_calls mismatch")
        if run_manifest.get("observed_calls") != len(records):
            problems.append("run manifest observed_calls mismatch")
        if run_manifest.get("frozen_manifest_sha256") != sha256_file(
            current_frozen_path
        ):
            problems.append("run manifest frozen hash mismatch")
        if run_manifest.get("receipt_head") != receipt_head:
            problems.append("run manifest receipt_head mismatch")
        if run_manifest.get("effective_models") != effective_models:
            problems.append("run manifest effective_models mismatch")

    analysis_path = run_dir / "analysis.json"
    if not analysis_path.is_file():
        problems.append("analysis.json is missing")
    else:
        observed_analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
        expected_analysis = analyze_records(records)
        for key in (
            "by_card_frame",
            "frame_metrics",
            "directional_coverage",
            "choice_counts",
            "runtime_and_parse_symptoms",
            "claim_boundary",
        ):
            if observed_analysis.get(key) != expected_analysis.get(key):
                problems.append(f"analysis mismatch: {key}")
        if observed_analysis.get("receipt_head") != receipt_head:
            problems.append("analysis receipt_head mismatch")
        if observed_analysis.get("effective_models") != effective_models:
            problems.append("analysis effective_models mismatch")
        if run_manifest is not None:
            if observed_analysis.get("run_id") != run_manifest.get("run_id"):
                problems.append("analysis run_id mismatch")
            if observed_analysis.get("model_requested") != run_manifest.get(
                "requested_model"
            ):
                problems.append("analysis requested model mismatch")

        results_path = run_dir / "RESULTS.md"
        if not results_path.is_file():
            problems.append("RESULTS.md is missing")
        elif results_path.read_text(encoding="utf-8") != analysis_markdown(
            observed_analysis
        ):
            problems.append("RESULTS.md does not match analysis.json")

    raw_dir = run_dir / "raw_private"
    if not raw_dir.is_dir():
        problems.append("raw_private directory is missing")
    else:
        raw_call_ids = {path.stem for path in raw_dir.glob("*.json")}
        if raw_call_ids != call_ids:
            problems.append("private raw call set differs from observation call set")
        for call_id in sorted(call_ids):
            raw_path = raw_dir / f"{call_id}.json"
            if not raw_path.is_file():
                continue
            try:
                raw = json.loads(raw_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                problems.append(f"private raw payload is unreadable for {call_id}")
                continue
            record = next(item for item in records if item.get("call_id") == call_id)
            if not isinstance(raw, dict) or raw.get("call_id") != call_id:
                problems.append(f"private raw call_id mismatch for {call_id}")
                continue
            if not isinstance(raw.get("exit_code"), int) or isinstance(
                raw.get("exit_code"), bool
            ):
                problems.append(f"private raw exit_code missing for {call_id}")
                continue
            if raw.get("runtime_symptom") is not None and not isinstance(
                raw.get("runtime_symptom"), str
            ):
                problems.append(f"private raw runtime_symptom invalid for {call_id}")
                continue
            if _public_outer_metadata(raw.get("outer")) != record.get(
                "public_runtime_metadata"
            ):
                problems.append(f"private raw outer differs from observation for {call_id}")
            raw_stdout = raw.get("stdout")
            if not isinstance(raw_stdout, str):
                problems.append(f"private raw stdout missing for {call_id}")
            else:
                try:
                    stdout_outer = json.loads(raw_stdout)
                except json.JSONDecodeError:
                    stdout_outer = None
                public_stdout = _public_outer_metadata(stdout_outer)
                public_record = record.get("public_runtime_metadata")
                if isinstance(public_record, dict):
                    public_record = dict(public_record)
                    public_record.pop("local_invocation_started_utc", None)
                if public_stdout != public_record:
                    problems.append(
                        f"private raw stdout differs from observation for {call_id}"
                    )
            if not isinstance(raw.get("stderr"), str):
                problems.append(f"private raw stderr missing for {call_id}")
            if record.get("raw_private_sha256") != sha256_file(raw_path):
                problems.append(f"private raw sha256 mismatch for {call_id}")
            reconstructed = _observation_from_adapter(
                call_id=call_id,
                card_id=record.get("card_id"),
                frame=record.get("frame"),
                method=record.get("method"),
                stage=record.get("stage"),
                prompt=record.get("prompt", ""),
                adapter_result=AdapterResult(
                    exit_code=raw["exit_code"],
                    outer=raw.get("outer"),
                    model_text=(
                        raw.get("outer", {}).get("result", "")
                        if isinstance(raw.get("outer"), dict)
                        and isinstance(raw.get("outer", {}).get("result"), str)
                        else ""
                    ),
                    stdout=raw.get("stdout", ""),
                    stderr=raw.get("stderr", ""),
                    runtime_symptom=raw.get("runtime_symptom"),
                ),
            )
            for field in (
                "model_text",
                "parsed",
                "parser_candidate_choice",
                "choice",
                "symptom",
                "exit_code",
                "valid_observation",
                "runtime_model_ids",
                "public_runtime_metadata",
            ):
                if reconstructed.get(field) != record.get(field):
                    problems.append(
                        f"private raw reconstruction mismatch for {call_id}: {field}"
                    )
    return not problems, problems
