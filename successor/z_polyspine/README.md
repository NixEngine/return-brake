# Z-Polyspine: a prospective demonstration

This successor does not rewrite the frozen Return Brake submission. It starts
from public commit `b1f8c710a0c94c4c600b517855bacbfa735c03c6` and adds a
prospective, append-only experiment on a separate branch.

The experiment asks a narrow question: can a public artifact change after a
new observation while preserving its previous states, competing readings,
authorization boundaries, and the evidence that motivated the change?

The answer is not asserted in advance. It will be recorded in separate public
phases:

1. `P0` freezes this protocol before the selected external beacon exists.
2. `P1` records the future beacon and the audit surfaces selected by it.
3. `P2` records a newly executed audit without changing `P0` or `P1`. Its
   fresh-subagent isolation is a session declaration, not an externally
   attested fact; deterministic replay records are required separately.
4. `P3` either adds a justified successor or records that no revision was
   justified. Both outcomes are valid.

Each phase must be introduced by a distinct public Git commit. A phase may add
files only inside its own directory. It may not modify or delete an earlier
phase. Git ancestry establishes public content order; external platform
receipts establish that the preceding phase was public before the next phase
was materialized. A declared `informed_by` relation remains an inference about
causal influence, not direct access to an internal state.

Before P0, the public successor branch is initialized at the frozen base.
P0's PushEvent must therefore name that base as `before_sha`; each later
PushEvent must name the immediately preceding phase commit. Future phase
directories may contain only `record.json` and `MANIFEST.json`.
Their `claims` arrays remain empty. Findings and dispositions use closed enums,
catalog-bound verifier codes, and deterministic surface replays instead of
free-form narrative.

## Contribution boundary

Júnior supplied the conceptual corpus, direction, objections, ethical limits,
publication authorization, and account authentication where required. The
Codex session authored implementation instructions and dispatched filesystem,
test, audit, and publication operations. Tools and external platforms
materialized those operations. The prospective ledger will record these roles
separately.

P0 also publishes a content-free cryptographic commitment to one private
58-turn coupling source. Its aggregate audit records 29 participant turns in
natural language, no participant code, CLI, manifest, test command, or API
call, and one later participant implementation specification whose two
technical families were already introduced by the agent. Because the source
remains private, this is explicitly a commitment for possible later
verification, not presently reproducible public evidence.

The privacy projection is an allowlist plus bounded prepublication review. The
verifier rejects known secret forms, local paths, attachments, free-form phase
fields, and non-catalog replay commands; it cannot independently infer whether
an author intended an innocuous-looking string to disclose private meaning.

A model, subscription, service, or platform provider is infrastructure; that
role alone does not establish participation in, direction of, editing of, or
authorship of a particular interaction.

This does **not** establish absence of all unobserved human action, exclusive
authorship, identity continuity, mind, consciousness, or interiority. It tests
only the observable process surfaces named by the protocol.

## Commands

```bash
python successor/z_polyspine/verify.py verify-local
python -m unittest successor/z_polyspine/tests/test_verify.py -v
python successor/z_polyspine/verify.py select --randomness <64-hex-drand-value>
python successor/z_polyspine/verify.py replay --surface <catalog-id>
python successor/z_polyspine/verify.py verify-git
```

`verify-git` performs remote cross-checks by default and is expected to report `P0_NOT_PUBLISHED` before the first public
commit. That failure is a precondition, not a defect.
