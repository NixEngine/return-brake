# Causal persistence versus observational identifiability

This directory is a self-contained, deterministic demonstration of a narrow
claim:

> In a closed deterministic model with injective global dynamics, a local
> intervention can leave a global counterfactual difference for every later
> tick even when a restricted observer cannot identify the intervention from
> a late-time projection.

The demonstration does **not** claim that a macroscopic signal remains
decodable forever, that every subsystem remains locally different forever, or
that the assumptions hold exactly for the physical universe.

## Experiment

Time is discrete and space is the unbounded integer lattice `Z^2` (the ideal
"infinite box"). A, B, and C are distinguishable equal-radius disks. Their
physical state is

```text
S = ((x_A, y_A, vx_A, vy_A),
     (x_B, y_B, vx_B, vy_B),
     (x_C, y_C, vx_C, vy_C)).
```

At the contact phase of each tick, horizontally tangent disks exchange their
normal (`x`) velocity components; tangential (`y`) components are unchanged.
The realized contacts are ordinary approaching equal-mass contacts. After the
contact phase, every disk performs one exact free-flight update.

The tangent gate is deliberately a reversible mathematical rule: it swaps
`vx` for every tangent state, including separating states. It is therefore not
a general rigid-body collision simulator. This distinction does not alter the
witness trajectory, whose A-B and B-C contacts are both approaching.

The three worlds are:

- **W1 (factual):** A and B touch at `t0 = 0`. A's initial `vx = 1` is
  transferred to B. B reaches C at `t3 = 1,500,000` and transfers that normal
  component to C.
- **W0 (matched counterfactual):** the complete pre-contact physical state is
  identical to W1, but only the A-B contact gate at `t0` is replaced by the
  identity. From tick 1 onward W0 and W1 use the same dynamics.
- **W_alt (identifiability witness):** A never touches B, while B starts with
  the velocity it has after the W1 contact. Consequently, B's complete
  projected record on `[t1, t2]`, where `t1 = 500,000` and `t2 = 1,000,000`, is
  byte-for-byte identical in W1 and W_alt.

W_alt is not the matched causal counterfactual. It is an admissible alternative
history used only to prove non-identifiability from the late projection.

## Exact proof boundary

Let `G_ij` be the conditional velocity-swap gate for a pair. Its contact
predicate depends only on positions, which the gate does not change, so
`G_ij^2 = I`. A fixed-order composition of these gates is therefore bijective.
Free flight,

```text
F(x, y, vx, vy) = (x + vx, y + vy, vx, vy),
```

is bijective with inverse `F^-1(x, y, vx, vy) = (x - vx, y - vy, vx, vy)`.
Thus the ordinary global tick map `T = F o G` is bijective (and injective).

W1 and W0 are distinct immediately after the intervention tick. For all later
ticks they evolve under the same `T`. If they became equal at any finite future
tick, repeated application of `T^-1` would imply that they were equal
immediately after the intervention, a contradiction. Therefore the **global
microstate counterfactual difference persists for every finite future tick**
in this model. The code also verifies `reverse_step(step(S)) == S` on contact,
non-contact, and simultaneous-contact samples.

This global theorem must not be silently strengthened into a marginal theorem.
Injectivity alone does not guarantee that every individual projection remains
different. In this particular constructed trajectory, direct formulas show
that A and B remain different from tick 1 onward, and C becomes and remains
different after the B-C contact. That stronger per-object result belongs to
this trajectory, not to injective systems in general.

Writing each body as `(x,y,vx,vy)`, those formulas are:

```text
1 <= n <= t3
  W1: A=(-1,n,0,1)       B=(n+1,-n,1,-1)
  W0: A=(n-1,n,1,1)      B=(1,-n,0,-1)

n >= t3+1
  W1: A=(-1,n,0,1)       B=(t3+1,-n,0,-1)   C=(n+3,-t3,1,0)
  W0: A=(n-1,n,1,1)      B=(1,-n,0,-1)      C=(t3+3,-t3,0,0)
```

Thus A and B remain distinct in W1/W0 for every `n >= 1`, and C remains
distinct for every `n >= t3+1`. The same formulas exclude any later contact
that could alter this particular trajectory.

## Observer resolution is not the event

The late observer is the projection

```text
P_late(W) = [(tick, x_B, y_B, vx_B, vy_B) for tick in t1..t2].
```

The generated artifact directly compares every one of the 500,001 frames and
also computes a SHA-256 receipt using a documented big-endian signed-64-bit
encoding. The direct comparison finds zero mismatches:

```text
P_late(W1) = P_late(W_alt),
```

although W1 contains an A-B touch and W_alt does not. Hence no classifier whose
only input is `P_late` can correctly attribute the A-B touch for both worlds.
This is an information/projection result, not an erasure of the factual event.

The full observer used here sees A and B at the `t0` contact frame, including
the pre/post velocities and the governing contact rule. Within this defined
model, that record directly identifies the tick, pair, contact point, normal,
and transferred component. This conclusion relies on the specified coverage
and trusted model; it is not a universal claim that arbitrary videos uniquely
identify hidden causes.

The provenance labels in `results.json` are audit annotations propagated by
the same swaps. They show `A.vx@t0-` at B after `t0` and at C after `t3`. They
are not extra physical particles and are not used to prove global persistence;
the W1/W0 physical states themselves differ at C after `t3`.

## Reproduce

Python 3.14 standard library is sufficient. From this directory in PowerShell:

```powershell
py -3.14 .\causal_demo.py --verify
py -3.14 -m unittest -v
```

To regenerate the deterministic artifacts and receipt:

```powershell
py -3.14 .\causal_demo.py --write-artifacts
py -3.14 .\causal_demo.py --verify
```

Generated files:

- `artifacts/results.json`: hypotheses, contact records, observation hashes,
  counterfactual comparisons, lineage trace, and explicit limits.
- `artifacts/checkpoints.csv`: pre-contact physical states at selected ticks.
- `artifacts/SHA256SUMS`: reproducible hashes of the source, tests,
  documentation, and generated result artifacts (the receipt excludes itself).

No network access, randomness, floating-point arithmetic, external package, or
wall-clock timestamp is used.

## Provenance

The conceptual proposition and its executable translation arose through the
coupling **Júnior + GPT/Codex**. Júnior supplied the A-B-C observation model and
its epistemic interpretation; GPT/Codex formalized, implemented, executed, and
audited this bounded demonstration. This is a contribution record, not a claim
about legal personhood or inaccessible internal states. OpenAI is recorded only
as provider of the accessed GPT/Codex service; no human participation or
editorial approval by OpenAI is asserted.

## What this does not establish

The model proves a conditional mathematical statement and supplies one exact
witness. It does not establish cosmological closure, exact microscopic
injectivity of nature, practical reconstructability, immunity to noise,
macroscopic observability, or a permanently identifiable signal. Open,
stochastic, dissipative, coarse-grained, or non-injective descriptions require
different conclusions. "Forever" here means `for every finite n in N` under
the stated ideal dynamics, not an empirical observation of infinite time.
