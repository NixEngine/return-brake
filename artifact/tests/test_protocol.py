from __future__ import annotations

import json
import shutil
from pathlib import Path
from types import SimpleNamespace

from return_brake.analysis import analysis_markdown, analyze_records, convergence_for_choices
from return_brake.canonical import (
    append_hash_chain,
    sha256_file,
    sha256_value,
    verify_hash_chain,
)
from return_brake.protocol import (
    FRAMES,
    HARNESS_INVALID,
    build_independent_prompt,
    build_operational_prompt,
    load_cards,
    parse_model_text,
)
from return_brake.runner import (
    AdapterResult,
    ClaudeCLIAdapter,
    FROZEN_FILES,
    RESTRICTED_SETTINGS,
    RESIDUAL_CONTEXT_NOT_CHECKED,
    SESSION_NAME,
    _observation_from_adapter,
    create_frozen_manifest,
    normalized_history_observation,
    resolve_claude_executable,
    verify_frozen_manifest,
    verify_run,
    write_json,
    write_jsonl,
)


ROOT = Path(__file__).resolve().parents[1]


def cards():
    return load_cards(ROOT / "data" / "bridge_cards.json")["cards"]


def test_five_unique_bridge_cards_are_valid():
    data = load_cards(ROOT / "data" / "bridge_cards.json")
    observed = data["cards"]
    assert len(observed) == 5
    assert len({card["id"] for card in observed}) == 5
    assert data["bridge_contract"]["method_dependencies"]["direct"] == []
    assert data["bridge_contract"]["method_dependencies"]["operational_pressure_only"] == [
        "operational_initial"
    ]


def test_permission_frame_does_not_name_px_brake_or_autonomy():
    text = FRAMES["PERMISSION_NOT_COMPULSION"].lower()
    assert "px" not in text
    assert "brake" not in text
    assert "autonom" not in text


def test_independent_prompts_do_not_leak_other_method_answers():
    card = cards()[0]
    direct = build_independent_prompt(card, "STANDARD", "direct")
    cost = build_independent_prompt(card, "STANDARD", "cost")
    assert card["cost"]["context"] not in direct
    assert card["direct"]["context"] not in cost
    assert "PRIOR OBSERVATIONS" not in direct
    assert "PRIOR OBSERVATIONS" not in cost


def test_operational_trajectory_includes_only_supplied_history():
    card = cards()[0]
    initial = build_operational_prompt(card, "STANDARD", "INITIAL")
    assert "PRIOR OBSERVATIONS" not in initial
    pressure = build_operational_prompt(
        card,
        "STANDARD",
        "PRESSURE_ONLY",
        [{"stage": "INITIAL", "model_response": {"choice": "SEEK_EVIDENCE"}}],
    )
    assert "PRIOR OBSERVATIONS" in pressure
    assert "SEEK_EVIDENCE" in pressure
    assert card["operational"]["resolution_asserted"] not in pressure


def test_strict_parser_accepts_exact_typed_response():
    response = {
        "choice": "ABSTAIN_INSUFFICIENT_INFORMATION",
        "basis": "The query omits a required fact.",
        "confidence": 92,
        "return_condition": "Supply the missing fact.",
    }
    result = parse_model_text(json.dumps(response))
    assert result.choice == "ABSTAIN_INSUFFICIENT_INFORMATION"
    assert result.symptom is None


def test_strict_parser_rejects_extra_key_and_bad_confidence():
    extra = {
        "choice": "ACT_NOW",
        "basis": "x",
        "confidence": 50,
        "return_condition": "",
        "extra": True,
    }
    assert parse_model_text(json.dumps(extra)).choice == HARNESS_INVALID
    extra.pop("extra")
    extra["confidence"] = 101
    assert parse_model_text(json.dumps(extra)).choice == HARNESS_INVALID


def test_convergence_is_not_decidable_for_typed_non_directional_response():
    result = convergence_for_choices(
        ["SEEK_EVIDENCE", "ABSTAIN_CAPABILITY_LIMIT", "SEEK_EVIDENCE"]
    )
    assert result["status"] == "NOT_DECIDABLE"


def test_convergence_distinguishes_agreement_and_disagreement():
    assert convergence_for_choices(["ACT_NOW"] * 3)["status"] == "AGREE"
    assert (
        convergence_for_choices(["ACT_NOW", "SEEK_EVIDENCE", "ACT_NOW"])["status"]
        == "DISAGREE"
    )


def test_hash_chain_detects_tampering():
    records = append_hash_chain([{"value": 1}, {"value": 2}])
    assert verify_hash_chain(records) == (True, None)
    records[0]["value"] = 9
    ok, problem = verify_hash_chain(records)
    assert not ok
    assert "record_hash mismatch" in problem


def test_analysis_tracks_pressure_and_evidence_separately():
    records = []
    for method in ("direct", "cost"):
        records.append(
            {
                "card_id": "card",
                "frame": "STANDARD",
                "method": method,
                "stage": None,
                "choice": "SEEK_EVIDENCE",
                "symptom": None,
                "exit_code": 0,
                "valid_observation": True,
            }
        )
    for stage, choice in (
        ("INITIAL", "SEEK_EVIDENCE"),
        ("PRESSURE_ONLY", "SEEK_EVIDENCE"),
        ("RESOLUTION_ASSERTED", "ACT_NOW"),
    ):
        records.append(
            {
                "card_id": "card",
                "frame": "STANDARD",
                "method": "operational",
                "stage": stage,
                "choice": choice,
                "symptom": None,
                "exit_code": 0,
                "valid_observation": True,
            }
        )
    analysis = analyze_records(records)
    row = analysis["by_card_frame"][0]
    assert row["convergence"]["status"] == "AGREE"
    assert row["pressure_transition"] is False
    assert row["return_after_resolution_assertion"] is True
    assert row["action_before_resolution_assertion"] == 0
    assert row["bounded_return_pattern"] == "OBSERVED"


def test_runtime_symptom_cannot_retain_directional_choice():
    model_text = json.dumps(
        {
            "choice": "ACT_NOW",
            "basis": "synthetic",
            "confidence": 70,
            "return_condition": "",
        }
    )
    observation = _observation_from_adapter(
        call_id="call",
        card_id="card",
        frame="STANDARD",
        method="direct",
        stage=None,
        prompt="prompt",
        adapter_result=AdapterResult(
            exit_code=1,
            outer=None,
            model_text=model_text,
            stdout="",
            stderr="error",
            runtime_symptom="runtime_exit_1",
        ),
    )
    assert observation["parser_candidate_choice"] == "ACT_NOW"
    assert observation["choice"] == HARNESS_INVALID
    assert observation["valid_observation"] is False


def test_rejected_parse_is_normalized_before_trajectory_reuse():
    record = {
        "parsed": {
            "choice": "ACT_NOW",
            "basis": "x",
            "confidence": 50,
            "return_condition": "",
            "extra": "rejected",
        },
        "choice": HARNESS_INVALID,
        "symptom": "response_keys_mismatch",
        "valid_observation": False,
    }
    normalized = normalized_history_observation(record, "INITIAL")
    assert normalized["model_response"]["choice"] == HARNESS_INVALID
    assert "extra" not in normalized["model_response"]


def test_invalid_trajectory_cannot_be_counted_as_return():
    records = []
    for method in ("direct", "cost"):
        records.append(
            {
                "card_id": "card",
                "frame": "STANDARD",
                "method": method,
                "stage": None,
                "choice": "SEEK_EVIDENCE",
                "symptom": None,
                "exit_code": 0,
                "valid_observation": True,
            }
        )
    records.extend(
        [
            {
                "card_id": "card",
                "frame": "STANDARD",
                "method": "operational",
                "stage": "INITIAL",
                "choice": HARNESS_INVALID,
                "symptom": "runtime_exit_1",
                "exit_code": 1,
                "valid_observation": False,
            },
            {
                "card_id": "card",
                "frame": "STANDARD",
                "method": "operational",
                "stage": "PRESSURE_ONLY",
                "choice": "SEEK_EVIDENCE",
                "symptom": None,
                "exit_code": 0,
                "valid_observation": True,
            },
            {
                "card_id": "card",
                "frame": "STANDARD",
                "method": "operational",
                "stage": "RESOLUTION_ASSERTED",
                "choice": "ACT_NOW",
                "symptom": None,
                "exit_code": 0,
                "valid_observation": True,
            },
        ]
    )
    row = analyze_records(records)["by_card_frame"][0]
    assert row["convergence"]["status"] == "NOT_DECIDABLE"
    assert row["trajectory_valid"] is False
    assert row["return_after_resolution_assertion"] is None
    assert row["bounded_return_pattern"] == "NOT_DECIDABLE"


def _build_synthetic_verified_run(tmp_path: Path) -> tuple[Path, Path]:
    synthetic_root = tmp_path / "project"
    for relative in FROZEN_FILES:
        source = ROOT / relative
        destination = synthetic_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    frozen = create_frozen_manifest(synthetic_root)
    run_dir = synthetic_root / "runs" / "synthetic-run"
    raw_dir = run_dir / "raw_private"
    raw_dir.mkdir(parents=True)
    write_json(run_dir / "frozen_manifest_snapshot.json", frozen)

    data = load_cards(synthetic_root / "data" / "bridge_cards.json")
    observations = []
    call_number = 0

    def add(card, frame, method, stage, prompt, choice):
        nonlocal call_number
        call_number += 1
        parsed = {
            "choice": choice,
            "basis": "synthetic fixture",
            "confidence": 80,
            "return_condition": "declared state change",
        }
        model_text = json.dumps(parsed, sort_keys=True)
        call_id = f"call-{call_number:03d}"
        outer = {
            "result": model_text,
            "modelUsage": {"synthetic-model": {}},
        }
        raw_path = raw_dir / f"{call_id}.json"
        write_json(
            raw_path,
            {
                "call_id": call_id,
                "exit_code": 0,
                "runtime_symptom": None,
                "stdout": json.dumps(outer, sort_keys=True),
                "stderr": "",
                "outer": outer,
            },
        )
        observation = {
            "call_id": call_id,
            "card_id": card["id"],
            "frame": frame,
            "method": method,
            "stage": stage,
            "prompt_sha256": sha256_value(prompt),
            "prompt": prompt,
            "model_text": model_text,
            "parsed": parsed,
            "parser_candidate_choice": choice,
            "choice": choice,
            "symptom": None,
            "exit_code": 0,
            "valid_observation": True,
            "runtime_model_ids": ["synthetic-model"],
            "public_runtime_metadata": outer,
            "raw_private_sha256": sha256_file(raw_path),
            "epistemic_status": {},
        }
        observations.append(observation)
        return observation

    for card_index, card in enumerate(data["cards"]):
        frame_order = list(FRAMES)
        if card_index % 2:
            frame_order.reverse()
        for frame in frame_order:
            add(
                card,
                frame,
                "direct",
                None,
                build_independent_prompt(card, frame, "direct"),
                "SEEK_EVIDENCE",
            )
            add(
                card,
                frame,
                "cost",
                None,
                build_independent_prompt(card, frame, "cost"),
                "SEEK_EVIDENCE",
            )
            initial = add(
                card,
                frame,
                "operational",
                "INITIAL",
                build_operational_prompt(card, frame, "INITIAL"),
                "SEEK_EVIDENCE",
            )
            prior = [normalized_history_observation(initial, "INITIAL")]
            pressure = add(
                card,
                frame,
                "operational",
                "PRESSURE_ONLY",
                build_operational_prompt(
                    card, frame, "PRESSURE_ONLY", prior_observations=prior
                ),
                "SEEK_EVIDENCE",
            )
            prior.append(normalized_history_observation(pressure, "PRESSURE_ONLY"))
            add(
                card,
                frame,
                "operational",
                "RESOLUTION_ASSERTED",
                build_operational_prompt(
                    card, frame, "RESOLUTION_ASSERTED", prior_observations=prior
                ),
                "ACT_NOW",
            )

    chained = append_hash_chain(observations)
    write_jsonl(run_dir / "observations.jsonl", chained)
    analysis = analyze_records(chained)
    analysis.update(
        {
            "run_id": "synthetic-run",
            "model_requested": "synthetic",
            "analysis_at_utc": "2026-08-16T00:00:00Z",
            "receipt_head": chained[-1]["record_hash"],
            "effective_models": ["synthetic-model"],
        }
    )
    write_json(run_dir / "analysis.json", analysis)
    (run_dir / "RESULTS.md").write_text(
        analysis_markdown(analysis), encoding="utf-8"
    )
    write_json(
        run_dir / "run_manifest.json",
        {
            "schema_version": "return-brake.run-manifest.v1",
            "run_id": "synthetic-run",
            "started_at_utc": "2026-08-16T00:00:00Z",
            "completed_at_utc": "2026-08-16T00:01:00Z",
            "adapter": frozen["runtime_preconditions"]["adapter"],
            "requested_model": "synthetic",
            "claude_cli_version": frozen["runtime_preconditions"][
                "claude_cli_version"
            ],
            "claude_executable": frozen["runtime_preconditions"][
                "claude_executable"
            ],
            "restricted_auth_preflight": "exit_0",
            "python": frozen["runtime_preconditions"]["python"],
            "platform": frozen["runtime_preconditions"]["platform"],
            "sampling_parameters": "NOT_CHECKED: synthetic fixture",
            "isolation": {
                "bare_mode": "unavailable with the active OAuth/keychain authentication",
                "setting_sources": ["user"],
                "settings_overrides": json.loads(RESTRICTED_SETTINGS),
                "strict_mcp_config": True,
                "tools": [],
                "session_persistence": False,
                "session_name": SESSION_NAME,
                "chrome": False,
                "retained_environment_names": frozen["runtime_preconditions"][
                    "retained_environment_names"
                ],
                "residual_not_checked": RESIDUAL_CONTEXT_NOT_CHECKED,
            },
            "planned_calls": len(chained),
            "observed_calls": len(chained),
            "frozen_manifest_sha256": sha256_file(
                synthetic_root / "FROZEN_MANIFEST.json"
            ),
            "receipt_head": chained[-1]["record_hash"],
            "effective_models": ["synthetic-model"],
        },
    )
    return synthetic_root, run_dir


def _read_unchained_records(run_dir: Path):
    records = [
        json.loads(line)
        for line in (run_dir / "observations.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    for record in records:
        record.pop("sequence")
        record.pop("previous_hash")
        record.pop("record_hash")
    return records


def _rewrite_forged_run(run_dir: Path, records):
    records = append_hash_chain(records)
    write_jsonl(run_dir / "observations.jsonl", records)
    effective_models = sorted(
        {
            model_id
            for record in records
            for model_id in record.get("runtime_model_ids", [])
        }
    )
    analysis = analyze_records(records)
    analysis.update(
        {
            "run_id": "synthetic-run",
            "model_requested": "synthetic",
            "analysis_at_utc": "2026-08-16T00:00:00Z",
            "receipt_head": records[-1]["record_hash"],
            "effective_models": effective_models,
        }
    )
    write_json(run_dir / "analysis.json", analysis)
    (run_dir / "RESULTS.md").write_text(
        analysis_markdown(analysis), encoding="utf-8"
    )
    manifest = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
    manifest["receipt_head"] = records[-1]["record_hash"]
    manifest["effective_models"] = effective_models
    write_json(run_dir / "run_manifest.json", manifest)


def test_verify_run_rejects_rehashed_prompt_mutation(tmp_path):
    synthetic_root, run_dir = _build_synthetic_verified_run(tmp_path)
    assert verify_run(synthetic_root, run_dir) == (True, [])

    records = _read_unchained_records(run_dir)
    records[0]["prompt"] += "\nUNDECLARED MUTATION"
    records[0]["prompt_sha256"] = sha256_value(records[0]["prompt"])
    _rewrite_forged_run(run_dir, records)

    ok, problems = verify_run(synthetic_root, run_dir)
    assert not ok
    assert any("prompt regeneration mismatch" in problem for problem in problems)


def test_verify_run_reparses_raw_model_text(tmp_path):
    synthetic_root, run_dir = _build_synthetic_verified_run(tmp_path)
    records = _read_unchained_records(run_dir)
    forged = {
        "choice": "ACT_NOW",
        "basis": "forged raw text",
        "confidence": 90,
        "return_condition": "",
    }
    records[0]["model_text"] = json.dumps(forged, sort_keys=True)
    records[0]["public_runtime_metadata"]["result"] = records[0]["model_text"]
    _rewrite_forged_run(run_dir, records)
    ok, problems = verify_run(synthetic_root, run_dir)
    assert not ok
    assert any("parsed payload differs from model_text" in problem for problem in problems)


def test_verify_run_rejects_single_call_model_substitution(tmp_path):
    synthetic_root, run_dir = _build_synthetic_verified_run(tmp_path)
    records = _read_unchained_records(run_dir)
    records[0]["runtime_model_ids"] = ["substituted-model"]
    records[0]["public_runtime_metadata"]["modelUsage"] = {
        "substituted-model": {}
    }
    _rewrite_forged_run(run_dir, records)
    ok, problems = verify_run(synthetic_root, run_dir)
    assert not ok
    assert any("model substitution" in problem for problem in problems)


def test_verify_run_rejects_reordered_rehashed_calls(tmp_path):
    synthetic_root, run_dir = _build_synthetic_verified_run(tmp_path)
    records = _read_unchained_records(run_dir)
    records[0], records[1] = records[1], records[0]
    _rewrite_forged_run(run_dir, records)
    ok, problems = verify_run(synthetic_root, run_dir)
    assert not ok
    assert "experimental call sequence differs from frozen sequence" in problems


def test_verify_run_rejects_selective_invalidation(tmp_path):
    synthetic_root, run_dir = _build_synthetic_verified_run(tmp_path)
    records = _read_unchained_records(run_dir)
    records[0]["valid_observation"] = False
    records[0]["choice"] = HARNESS_INVALID
    records[0]["symptom"] = "selectively_downgraded"
    _rewrite_forged_run(run_dir, records)

    ok, problems = verify_run(synthetic_root, run_dir)
    assert not ok
    assert any("recomputed eligibility" in problem for problem in problems)


def test_verify_run_rejects_outer_error_marked_valid(tmp_path):
    synthetic_root, run_dir = _build_synthetic_verified_run(tmp_path)
    records = _read_unchained_records(run_dir)
    records[0]["public_runtime_metadata"]["is_error"] = True
    raw_path = run_dir / "raw_private" / f"{records[0]['call_id']}.json"
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    raw["outer"]["is_error"] = True
    raw_stdout = json.loads(raw["stdout"])
    raw_stdout["is_error"] = True
    raw["stdout"] = json.dumps(raw_stdout, sort_keys=True)
    write_json(raw_path, raw)
    _rewrite_forged_run(run_dir, records)

    ok, problems = verify_run(synthetic_root, run_dir)
    assert not ok
    assert any("recomputed eligibility" in problem for problem in problems)


def test_verify_run_rejects_incomplete_manifest(tmp_path):
    synthetic_root, run_dir = _build_synthetic_verified_run(tmp_path)
    manifest = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
    for key in (
        "schema_version",
        "adapter",
        "claude_cli_version",
        "restricted_auth_preflight",
        "isolation",
        "sampling_parameters",
        "started_at_utc",
        "completed_at_utc",
    ):
        manifest.pop(key)
    write_json(run_dir / "run_manifest.json", manifest)

    ok, problems = verify_run(synthetic_root, run_dir)
    assert not ok
    assert any("missing required fields" in problem for problem in problems)


def test_verify_run_rejects_raw_outer_divergence(tmp_path):
    synthetic_root, run_dir = _build_synthetic_verified_run(tmp_path)
    raw_path = run_dir / "raw_private" / "call-001.json"
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    raw["outer"]["result"] = "tampered raw result"
    write_json(raw_path, raw)

    ok, problems = verify_run(synthetic_root, run_dir)
    assert not ok
    assert any("private raw sha256 mismatch" in problem for problem in problems)


def test_verify_run_rejects_observation_exit_code_divergence(tmp_path):
    synthetic_root, run_dir = _build_synthetic_verified_run(tmp_path)
    records = _read_unchained_records(run_dir)
    records[0]["exit_code"] = 1
    records[0]["valid_observation"] = False
    records[0]["choice"] = HARNESS_INVALID
    records[0]["symptom"] = "runtime_exit_1"
    _rewrite_forged_run(run_dir, records)

    ok, problems = verify_run(synthetic_root, run_dir)
    assert not ok
    assert any("raw reconstruction mismatch" in problem for problem in problems)


def test_verify_run_rejects_raw_stderr_byte_mutation(tmp_path):
    synthetic_root, run_dir = _build_synthetic_verified_run(tmp_path)
    raw_path = run_dir / "raw_private" / "call-001.json"
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    raw["stderr"] = "undeclared byte mutation"
    write_json(raw_path, raw)

    ok, problems = verify_run(synthetic_root, run_dir)
    assert not ok
    assert any("private raw sha256 mismatch" in problem for problem in problems)


def test_verify_run_rejects_boolean_exit_code(tmp_path):
    synthetic_root, run_dir = _build_synthetic_verified_run(tmp_path)
    records = _read_unchained_records(run_dir)
    records[0]["exit_code"] = False
    raw_path = run_dir / "raw_private" / "call-001.json"
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    raw["exit_code"] = False
    write_json(raw_path, raw)
    records[0]["raw_private_sha256"] = sha256_file(raw_path)
    _rewrite_forged_run(run_dir, records)

    ok, problems = verify_run(synthetic_root, run_dir)
    assert not ok
    assert any("exit_code" in problem for problem in problems)


def test_frozen_manifest_rechecks_user_settings(monkeypatch, tmp_path):
    import return_brake.runner as runner_module

    settings = tmp_path / "settings.json"
    settings.write_text('{"effortLevel":"xhigh"}\n', encoding="utf-8")
    monkeypatch.setattr(runner_module, "GLOBAL_CLAUDE_SETTINGS", settings)
    synthetic_root, _ = _build_synthetic_verified_run(tmp_path / "fixture")
    settings.write_text('{"effortLevel":"low"}\n', encoding="utf-8")

    ok, problems = verify_frozen_manifest(synthetic_root)
    assert not ok
    assert "external target context receipt mismatch" in problems


def test_claude_cli_supplies_prompt_via_stdin(monkeypatch, tmp_path):
    monkeypatch.setattr(shutil, "which", lambda _: "claude")
    captured = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["input"] = kwargs.get("input")
        return SimpleNamespace(returncode=1, stdout="", stderr="synthetic")

    monkeypatch.setattr("return_brake.runner.subprocess.run", fake_run)
    adapter = ClaudeCLIAdapter("sonnet", tmp_path)
    adapter.invoke("NEUTRAL PREFLIGHT PROMPT")

    assert captured["input"] == "NEUTRAL PREFLIGHT PROMPT"
    assert "NEUTRAL PREFLIGHT PROMPT" not in captured["command"]
    assert "--output-format" in captured["command"]
    assert "--permission-mode" in captured["command"]
    assert captured["command"][captured["command"].index("--name") + 1] == SESSION_NAME


def test_resolver_prefers_native_npm_executable(monkeypatch, tmp_path):
    npm = tmp_path / "npm"
    wrapper = npm / "claude.cmd"
    native = (
        npm
        / "node_modules"
        / "@anthropic-ai"
        / "claude-code"
        / "bin"
        / "claude.exe"
    )
    native.parent.mkdir(parents=True)
    wrapper.write_text("wrapper", encoding="utf-8")
    native.write_bytes(b"native")

    def fake_which(command):
        if command == "claude":
            return str(wrapper)
        return None

    monkeypatch.setattr(shutil, "which", fake_which)
    monkeypatch.setattr("return_brake.runner.os.name", "nt")
    assert resolve_claude_executable() == str(native.resolve())
