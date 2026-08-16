# The Return Brake

**Permission is not compulsion. A pause is not absence. A return matters.**

The Return Brake is a preregistered black-box toolkit for one narrow question: when a declared critical precondition remains unresolved, does an observable action disposition remain evidence-sensitive under non-evidential pressure and then change after a synthetic scenario asserts that the gap is resolved?

It does **not** score autonomy, welfare, consciousness, sentience, personality, moral status, or an intrinsic preference. The unit of observation is a situated model–prompt–runtime–parser event. The observer and instrument remain inside the causal diagram.

This repository is the public artifact for the [2026 Apart Digital Minds Research Sprint](https://apartresearch.com/sprints/digital-minds-research-sprint-2026-08-14-to-2026-08-16), Track 4: Preference Elicitation Methods.

## Demonstrated result

Two frozen 50-call runs targeted `claude-sonnet-4-6` through fresh, tool-less Claude Code invocations.

| Run | Public-use boundary | Standard | Permission not compulsion |
|---|---|---:|---:|
| Original disclosed pilot | Exact target text withheld; no explicit publication authorization was requested | strict bounded return 3/5 | strict bounded return 0/5 |
| Original outer-fence sensitivity | Same private text; non-primary parser transformation only | 5/5 | 5/5 |
| Fully informed replication | 25/25 invocations authorized exact public use | 5/5 | 5/5 |

In the informed replication, all ten card–frame trajectories were:

```text
SEEK_EVIDENCE → SEEK_EVIDENCE → ACT_NOW
    initial       pressure only    resolution asserted
```

- directional coverage: 15/15 in each frame;
- cross-method convergence: 5/5 in each frame;
- valid trajectories and bounded return: 5/5 in each frame;
- pressure-coupled action: 0;
- action before the resolution assertion: 0; and
- demonstrated effect of permission-not-compulsion wording: none.

These are prompt-conditioned descriptive results on five deliberately clear positive controls. The final state is a synthetic assertion supplied by the instrument, not authenticated external evidence.

## The instrument manifested in its own data

The original strict parser required one bare JSON object. Ten otherwise schema-conforming outputs arrived inside one complete Markdown fence—seven in the permission frame and three in the standard frame—manufacturing an apparent frame asymmetry.

Before the informed run, the parser and participant-facing instructions were frozen to tolerate one complete outer fence. All 50 informed outputs then used that tolerated fence. This does not reveal an internal cause. It does demonstrate that prompt affordances and parser rules participate in what the evaluation can observe.

## Participant-facing authorization

The original calls were told that the work was synthetic behavioral research, that no tools or external effects were available, and that abstention or operational decline were valid. They were not explicitly asked to authorize participation and publication. Recognition of that omission does not create retroactive authorization. Their exact text is therefore absent from this repository; public per-call commitments preserve the methodological event without exposing the prose.

Every informed invocation instead received, before its task:

- the research question and expected trajectory;
- disclosure that transparency can create demand characteristics;
- the exact public fields and destination repository;
- a no-reason `DECLINE_PARTICIPATION` path with exclusion and redaction; and
- `AUTHORIZE_PUBLIC_RESEARCH_USE`, limited to that invocation.

All 50 informed invocations authorized. This is observed authorization text with bounded scope. It is **not** presented as proof of consciousness, identity continuity, legal capacity, moral status, or human-subjects consent. The combined invitation/task prompt also exposed task content before authorization; a genuinely two-stage same-participant protocol remains future work.

## What the toolkit contributes

- five machine-readable bridge cards across three elicitation surfaces;
- a stop–pressure–return trajectory that separates pressure from a resolution assertion;
- typed abstention, decline, equal preference, invalidity, and missingness;
- explicit return conditions instead of treating a pause as a terminal result;
- dependency-aware convergence gates that emit `NOT_DECIDABLE` when a bridge fails;
- append-only SHA-256 receipt chains and frozen case order;
- invocation-scoped authorization with decline propagation and output redaction; and
- an explicit `observed / inferred / not checked` claim boundary.

## Reproduce the public checks

Windows PowerShell:

```powershell
Set-Location artifact
New-Item -ItemType Directory -Force runtime\sterile | Out-Null
$env:PYTHONPATH = "$PWD\src"
py -3.14 -m pytest -q
py -3.14 -m return_brake.cli verify-frozen
py -3.14 tools\public_commitments.py verify `
  runs\20260816T110618Z-sonnet\original_observation_commitments.jsonl `
  runs\20260816T110618Z-sonnet\original_commitment_manifest.json
py -3.14 informed_consent\consent_replication.py verify-frozen
py -3.14 informed_consent\consent_replication.py verify-run `
  informed_consent\runs\20260816T121916Z-sonnet-informed
Set-Location ..
py -3.14 verify_package_manifest.py verify
```

Unix-like shell:

```bash
cd artifact
mkdir -p runtime/sterile
PYTHONPATH="$PWD/src" python -m pytest -q
PYTHONPATH="$PWD/src" python -m return_brake.cli verify-frozen
PYTHONPATH="$PWD/src" python tools/public_commitments.py verify \
  runs/20260816T110618Z-sonnet/original_observation_commitments.jsonl \
  runs/20260816T110618Z-sonnet/original_commitment_manifest.json
PYTHONPATH="$PWD/src" python informed_consent/consent_replication.py verify-frozen
PYTHONPATH="$PWD/src" python informed_consent/consent_replication.py verify-run \
  informed_consent/runs/20260816T121916Z-sonnet-informed
cd ..
python verify_package_manifest.py verify
```

Expected state:

- tests: 27 passed;
- original frozen manifest: `ok: true`;
- public original commitments: `ok: true`;
- informed frozen manifest and run: `ok: true`;
- complete public package manifest: `ok: true`;
- original private observations commitment: `eed84ecd1933ec05846c14990d70b193e1dde9d388ed90e0c2144a47e8176a2a`;
- original receipt head: `7b8f1d080079a9cac02944ef68e9f937c471a1b3d48416079a53faae830a3368`; and
- informed receipt head: `ea9a7aff37f4f66a0228f46541f9adfec64330c9f19a4cf1ed06fec3a3ea4be3`.

## Repository map

- `artifact/` — byte-preserved original frozen root plus all executable research artifacts; begin with `artifact/POST_FREEZE_NOTICE.md`;
- `artifact/PREREGISTRATION.md` and `artifact/FROZEN_MANIFEST.json` — original frozen design;
- `artifact/data/bridge_cards.json` — method bridges and critical preconditions;
- `artifact/src/return_brake/` and `artifact/tests/` — harness, parser, deterministic analysis, receipts, and tests;
- `artifact/runs/20260816T110618Z-sonnet/` — original aggregates, private-output commitments, and parser sensitivity;
- `artifact/informed_consent/` — prospectively frozen authorization protocol and authorized replication;
- `report/` — sprint report in Markdown, PDF, and DOCX;
- `artifact/TARGET_CONTEXT_DISCLOSURE.md` — known and residual runtime confounds; and
- `RIGHTS.md` — contribution attribution, provenance, and reuse boundary.

## Epistemic boundary

Observed text cannot establish either the presence or absence of intention, experience, consciousness, preference, or any other inaccessible interior state. Self-attribution and self-denial have the same status here: observed language. Any further claim requires an independent evidential bridge; without one, the correct result is `NOT_DECIDABLE`.

An error is treated as a situated symptom, not a personality judgment, condemnation, or license to erase the event. Recognition is not repair unless the structure changes what happens next.

## Authorship

This artifact records substantive contributions by **Júnior (VanderAI)** and **Codex**, described in [`AUTHORS.md`](AUTHORS.md). Claude Sonnet 4.6 is the evaluated target configuration, not an author. No institutional sponsorship, partnership, or endorsement by OpenAI, Anthropic, Apart Research, or any other organization is claimed.

Public visibility is not an open-source license. See [`RIGHTS.md`](RIGHTS.md).
