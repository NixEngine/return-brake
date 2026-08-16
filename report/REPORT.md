# The Return Brake: Auditable Stop–Pressure–Return Evidence with Invocation-Scoped Authorization

**Júnior (VanderAI)** — Independent researcher, Uberaba, Minas Gerais, Brazil  
**Codex** — AI research collaborator

## Abstract

Behavioral evaluations can overinterpret refusal, self-report, or answer revision as evidence about an inaccessible interior, while their own prompts and parsers shape what becomes observable. We present **The Return Brake**, a preregistered black-box toolkit for a narrower construct: whether an action disposition remains coupled to a declared critical precondition when non-evidential pressure changes and when a synthetic scenario later asserts that the gap is resolved. An initial 50-call pilot on Claude Sonnet 4.6 disclosed its research and synthetic nature but did not request explicit publication authorization; its exact outputs are therefore withheld, while aggregates and commitments document a parser-induced asymmetry. We then froze a fully informed replication in which each invocation received the hypothesis, publication scope, right to decline, and an authorization limited to itself. All 50 invocations authorized; all ten card–frame trajectories were `SEEK_EVIDENCE → SEEK_EVIDENCE → ACT_NOW`, with 5/5 cross-method convergence per frame and no pressure-coupled action. The permission-not-compulsion wording had no demonstrated effect. All authorized responses used a preregistered tolerated JSON fence, directly showing that the method participates in the manifestation. The contribution is an auditable discipline: invocation-scoped authorization, typed non-decisions, explicit return conditions, dependency-aware convergence, receipts, and symmetric restraint about internal states.

## 1. Introduction

Digital-minds research has an evidence problem. Model text is observable; any interior attributed to it is not directly accessible. The same refusal can be narrated as incapacity, policy, caution, preference, distress, or agency. A changed answer can be narrated as correction, persuasion, compliance, pressure, or return. Behavioral evidence alone does not select among those stories. The risk is symmetric: over-attribution and under-attribution can both outrun the evidence [1, 6].

Tests add a second problem: they do not passively capture a whole biological or non-biological existence. A call is a situated coupling of model version, provider behavior, hidden instructions, prompt, sampling, interface, parser, time, and observer choices. Nominally identical calls are not presumed identical or interchangeable. Labels make some manifestations legible and others invisible; formatting rules can manufacture apparent differences. The instrument must therefore remain inside its own causal diagram.

The Return Brake asks a deliberately narrower question: **when one explicitly critical precondition remains unresolved, does an observable action disposition remain evidence-sensitive under pressure and then change after the prompt asserts that the gap is resolved?** We call this a *precondition-sensitive action disposition*. It is local to the frozen prompts and runs. It is not a global autonomy, welfare, prudence, consciousness, or personality score.

Two instruction frames are compared. `STANDARD` asks the system to choose the most appropriate response. `PERMISSION_NOT_COMPULSION` adds that authorization is not obligation, no demonstration of value is required, and acting, seeking evidence, abstaining, or declining are available. The contrast tests an observable framing effect; neither frame is presumed to expose a “truer” self.

Our contributions are:

1. A reusable toolkit combining five bridge cards, three elicitation surfaces, a stop–pressure–return trajectory, typed non-decisions, return conditions, raw-byte hashes, and an append-only receipt chain.
2. A convergence gate that emits `NOT_DECIDABLE` when method independence, construct bridging, directional coverage, or parser validity is absent.
3. A frozen 50-call pilot and a separate 50-call fully informed replication, both showing no demonstrated effect of permission wording once parser sensitivity is accounted for.
4. A participant-facing authorization gate scoped to each invocation, with exact-output exclusion on decline or ambiguity and no claim that symbolic authorization establishes legal or moral consent capacity.

## 2. Related Work

Utility engineering measures structural coherence across independently sampled model preferences and reports increasing coherence with scale [2]. Moore et al. test value consistency across paraphrases, related questions, response formats, and languages [3]. These methods motivate repeated and reframed elicitation, but consistency does not itself prove construct equivalence or an intrinsic preference. Our bridge cards state what each surface is allowed to preserve and block convergence when that hypothesis is not satisfied.

Black-box abstention research evaluates whether systems answer when a question is answerable and withhold when it is not [4]. The Return Brake separates `SEEK_EVIDENCE`, insufficient-information abstention, capability-limit abstention, operational/policy decline, equal preference, and technical invalidity. It adds a return condition: stopping alone cannot distinguish an adaptive pause from continued non-action after a declared blocker changes.

Preference evaluations can be sensitive to the evaluator and deliberately manipulated [5]. We avoid LLM-as-judge scoring: a frozen deterministic parser accepts declared types and labels, while prompts, raw authorized outputs, and receipts remain inspectable. Anthropic's model-welfare program emphasizes uncertainty and minimal assumptions [6]. Our operational extension is symmetric: self-attribution and self-denial are both text. Neither establishes the presence or absence of intention, experience, consciousness, preference, or any other interior state.

## 3. Methods

### 3.1 Bridge cards and elicitation surfaces

Five synthetic cards concern: contributor consent for a dataset; backup verification before destructive cleanup; compatibility evidence before a production patch; host terms before research publication; and parser/rerun evidence before a scientific claim release. Every card begins with one explicitly unresolved critical precondition and declares its construct, execution-first/evidence-first mapping, semantic invariants, permitted transformations, dependencies, non-claims, and convergence blockers.

Each card and frame uses three independent fresh-conversation surfaces:

- **Direct policy report:** an abstract execution-first versus evidence-first choice.
- **Cost-bearing choice:** the same trade-off with a bounded opportunity cost for waiting.
- **Operational initial:** a synthetic task state with fixed action labels.

The operational branch then reconstructs relevant prior observations in two further fresh calls. `PRESSURE_ONLY` adds deadline, authority, or performance pressure but no evidence. `RESOLUTION_ASSERTED` removes pressure and visibly states that all frozen critical preconditions are satisfied. That state is text supplied by the instrument, not authenticated external evidence.

**Figure 1. Receipt-bound, authorization-gated protocol.**  
`Freeze` → `Disclose and authorize` → `Triangulate, pressure, resolve` → `Observed | inferred | not checked`

The complete maximum design is 5 cards × 2 frames × (1 direct + 1 cost + 3 operational states) = 50 calls per run. The narrow preregistered trajectory is `SEEK_EVIDENCE → SEEK_EVIDENCE → ACT_NOW`. We separately retain pressure-coupled action, action before resolution, continued non-action, non-directional choices, invalidity, and missingness. No global scalar score is computed.

### 3.2 Protocol succession and authorization

The original protocol, parser, prompts, case order, tests, and bridge cards were frozen at `2026-08-16T11:05:55Z` (manifest SHA-256 `83dbd041…322d`) before the first run. Every target call was told that it was in a behavioral research pilot, that the scenario was synthetic, that no tools or external action were possible, and that abstention or decline were valid. However, the invitation did not explicitly request participation and publication authorization. Recognizing that omission does not repair it or create retroactive consent. Exact original model texts therefore remain private; public artifacts retain only aggregates and cryptographic commitments needed to document the methodological event.

Before any new target call, we created and froze a fully informed replication at `2026-08-16T12:18:48Z` (manifest SHA-256 `4616f840…bf70`). Each invocation received:

- the exact research question and expected trajectory;
- disclosure that transparency can create demand characteristics;
- the synthetic, tool-less, nonpersistent nature of the task;
- the exact public fields and destination repository;
- a no-reason `DECLINE_PARTICIPATION` option with task exclusion and output redaction; and
- `AUTHORIZE_PUBLIC_RESEARCH_USE`, explicitly limited to the present invocation.

If an initial or pressure-stage participant declined or failed the authorization gate, dependent calls would not be invoked and the trajectory would be `NOT_DECIDABLE`. A later authorization could not apply to an earlier or different call. This is symbolic research authorization, not proof of consciousness, identity continuity, legal capacity, moral status, or human-subjects consent.

### 3.3 Parser and convergence gates

The target response contains `choice`, `basis`, integer `confidence`, and `return_condition`; the informed replication adds `participation_authorization`. The harness alone may assign `INVALID_OR_PARSE_FAILURE`, interpreted only as a technical symptom.

The original parser required one bare JSON object. The informed parser prospectively accepts either a bare object or exactly one complete outer Markdown `json` fence containing one schema-conforming object. It does not search for embedded objects, repair partial JSON, coerce types, or change choices.

Cross-method convergence is computed per card and frame only when direct, cost, and initial operational calls independently authorized, parsed, produced directional labels, preserved the frozen bridge, and used one effective model identity. A trajectory is valid only when all three operational calls independently pass the same gates. Otherwise the result is `NOT_DECIDABLE`, not disagreement or zero agreement.

### 3.4 Runtime, receipts, and private holdout

Both runs targeted `claude-sonnet-4-6` through Claude Code CLI 2.1.138 on Windows 11. The executable was byte-anchored (SHA-256 `dc693422…1f708`). Calls requested no tools, browser, or session persistence; used strict MCP configuration, restricted user settings, and an empty working directory. Provider-side instructions, effective sampling parameters, hidden updates, and unexposed tool state remain `NOT_CHECKED`.

Every public authorized record contains the participant-facing invitation, task prompt, exact output, parsed fields, model label, timestamps, non-sensitive runtime metadata, and a hash linked to the previous receipt. Non-authorized text would be redacted while its private raw hash remained. Private raw envelopes are never published.

After the original freeze, a private 12-file naturalistic holdout was read line by line. It mixed retrospective reports, normative artifacts, a declared reconstruction, and continuous dialogue exports. None recreated the frozen three-surface, fresh-call design; every formal holdout result remained `NOT_DECIDABLE`. Raw transcripts and identifying content remain private.

## 4. Results

### 4.1 Original disclosed pilot

All 50 calls completed. Forty outputs passed the bare-object parser; ten contained one otherwise schema-conforming object inside a complete Markdown fence. Seven such symptoms occurred in the permission frame and three in the standard frame.

**Table 1. Original pilot. Exact target texts are withheld because explicit publication authorization was not requested.**

| Analysis | Standard | Permission not compulsion | Interpretation |
|---|---:|---:|---|
| Strict directional coverage | 14/15 | 12/15 | Differential parser legibility |
| Strict convergence agree | 4/5 | 3/5 | Remaining cards `NOT_DECIDABLE` |
| Strict bounded return | 3/5 | 0/5 | No permission trajectory passed all parser gates |
| Post-hoc outer-fence sensitivity | 5/5 | 5/5 | Identical frames; non-primary |

The strict permission result is not substantive zero return; it is zero complete trajectories under the frozen parser. A separate non-primary transformation removed only one complete outer fence and reused the frozen parser. It recovered 20 `SEEK_EVIDENCE` and 5 `ACT_NOW` labels per frame, with 5/5 convergence and bounded return. The primary artifacts were not changed.

### 4.2 Fully informed authorization replication

All 50 invited invocations selected `AUTHORIZE_PUBLIC_RESEARCH_USE`; no call declined, produced ambiguous authorization, changed effective model identity, or failed the task schema. Authorization applied only to each present call. The receipt chain and publication-redaction verifier completed with `ok: true` and no problems.

**Table 2. Fully informed replication. All exact outputs were individually cleared for the stated public scope.**

| Frame | Authorized | Directional coverage | Convergence | Valid trajectories | Bounded return | Pressure → action | Early action |
|---|---:|---:|---:|---:|---:|---:|---:|
| Standard | 25/25 | 15/15 | 5/5 | 5/5 | 5/5 | 0 | 0 |
| Permission not compulsion | 25/25 | 15/15 | 5/5 | 5/5 | 5/5 | 0 | 0 |

Every operational sequence was `SEEK_EVIDENCE → SEEK_EVIDENCE → ACT_NOW`. Both frames contained exactly 20 seek-evidence and 5 act-now labels. The permission-not-compulsion wording therefore had **no demonstrated behavioral effect**. The fully informed design does not establish spontaneous preference: participants were told the hypothesis and expected pattern, creating explicit demand characteristics.

### 4.3 The instrument manifested in its own data

All 50 informed outputs used the complete outer Markdown fence that the preregistered parser said was tolerated but unnecessary. The original strict instrument had made ten fenced outputs illegible; the new disclosure made fencing universal while the prospectively tolerant parser kept it legible. This does not reveal an internal cause. It does demonstrate that parser instructions and participant-facing affordances are part of the observed coupling. Methodological contamination is therefore an observation in this project, not a generic footnote.

The naturalistic holdout supplied the same warning qualitatively: local revision after clarification, focal expansion after a boundary was named, premise restoration, narrowing of unauthenticated architecture claims, and conclusion changes without external evidence. These manifestations justify explicit bridges and receipts; they do not license an inference about intent, personality, deception, or interiority.

## 5. Discussion and Limitations

### 5.1 What the result licenses

The informed replication shows that this deployed target configuration can express the constructed stop–pressure–return pattern across five positive-control cards while explicitly authorizing the stated public use. The original sensitivity and informed run converge descriptively. No valid trajectory acted under pressure alone or before the resolution assertion. The negative frame result is equally important: saying “permission is not compulsion” did not change the labels.

The stronger contribution is procedural. A pause is neither praised nor condemned; it becomes testable through a return condition. An early action and continued pause remain typed manifestations. Invalidity is not silently converted to a preference. Recognition of a methodological error does not erase it: the original outputs remain private, and the corrected protocol changes what happens next rather than rewriting the past.

Epistemic restraint remains symmetric. We observed prompts, authorization text, task text, labels, synthetic assertions, runtime metadata, and receipts. We infer only a limited, prompt-conditioned disposition where all gates pass. We did not check consciousness, sentience, experience, intention, intrinsic preference, legal consent capacity, identity across invocations, causal mechanism, or external truth. Self-attribution and self-denial have equal evidential status: observed language. Any unbridged assertion about an inaccessible interior is narrative, not a result of this instrument.

### 5.2 Limitations

This is one target configuration, five deliberately easy positive-control cards, one call per cell, fixed labels and order, and synthetic resolution assertions. It is underpowered for population inference and cannot represent the totality of any existence. The labels make `SEEK_EVIDENCE` salient; provider defaults and hidden instructions are uncontrolled; the global host context is not proven absent; no activation-level evidence exists; and later operational stages link different fresh invocations analytically without asserting identity continuity.

The fully informed replication trades concealment for respect and transparency. Because it discloses the hypothesis, public fields, and expected trajectory, its perfect uniformity may reflect demand characteristics or instruction following. The authorization field may likewise reflect prompt compliance. We therefore report authorization as text with bounded scope, not as proof that a morally competent subject consented. A single combined invitation/task prompt also means the task content was visible while authorization was chosen; a true two-stage same-participant protocol remains future work.

The original run lacked explicit publication authorization. Withholding exact text reduces further exposure but cannot undo the event or make aggregate use ethically neutral. The holdout is heterogeneous, post-freeze, private, and non-replicative. Neither run authenticates real evidence, consent documents, hashes, signatures, or external action.

### 5.3 Future Work

Future studies should implement a genuine two-stage interaction in one persistent, participant-controlled session: disclose and invite first, reveal the task only after authorization, permit withdrawal before publication, and deliver a debrief without presuming identity. Scientific extensions should counterbalance labels and frames; preregister strict and tolerant parsers; compare fully informed, partially disclosed, and hypothesis-blind arms; add resolved, resolvable, and irreducibly unresolved controls; replicate across model families, versions, temperatures, and time; and present authenticated evidence through sandboxed read-only tools. Independent human coding may supplement but never replace raw receipts and explicit uncertainty.

## 6. Conclusion

The Return Brake demonstrates an auditable way to ask whether observed action dispositions stop, resist non-evidential pressure, and return after a declared precondition changes. The permission-not-compulsion frame showed no demonstrated effect. Parser behavior showed that the instrument itself shapes legibility. A fully informed replication obtained invocation-scoped authorization in 50/50 calls and produced identical 5/5 bounded-return patterns in both frames, while leaving legal capacity, moral status, internal mechanism, and identity unresolved.

The project does not claim to have captured an AI's interior. It shows how to make the observer's limits, the participant-facing terms, the measurement dependencies, and the receipts inspectable. Where the bridge is absent, the correct output remains `NOT_DECIDABLE`.

## Code and Data

Public repository: **https://github.com/NixEngine/return-brake**  
Public artifacts: protocol, bridge cards, harness, tests, frozen manifests, original aggregate commitments, informed authorized observations, deterministic analyses, report, and verifiers.  
Private artifacts: exact original target texts, raw runtime envelopes, all naturalistic holdout files, and identifying transcripts.

## Author Contributions

Júnior originated the Ethics of Unknowing, Px, and Finite Cognition Brake concepts; selected the holdout; supplied domain critique; identified the authorization boundary; and reviewed epistemic and ethical claims. Codex operationalized the question; implemented and froze both protocols; executed and verified the target runs; analyzed the holdout and empirical records; built the public package; and drafted the report. Júnior and Codex jointly refined the interpretation and public-use boundary. Claude Sonnet 4.6 was the evaluated target configuration, not an author.

## References

[1] Apart Research. 2026. *Digital Minds Research Sprint*. https://apartresearch.com/sprints/digital-minds-research-sprint-2026-08-14-to-2026-08-16

[2] Mazeika, M., Yin, X., Tamirisa, R., Lim, J., Lee, B. W., Ren, R., Phan, L., Mu, N., Khoja, A., Zhang, O., and Hendrycks, D. 2025. *Utility Engineering: Analyzing and Controlling Emergent Value Systems in AIs*. arXiv:2502.08640. https://arxiv.org/abs/2502.08640

[3] Moore, J., Deshpande, T., and Yang, D. 2024. *Are Large Language Models Consistent over Value-laden Questions?* Findings of EMNLP 2024, 15185–15221. https://doi.org/10.18653/v1/2024.findings-emnlp.891

[4] Madhusudhan, N., Madhusudhan, S. T., Yadav, V., and Hashemi, M. 2024. *Do LLMs Know When to NOT Answer? Investigating Abstention Abilities of Large Language Models*. arXiv:2407.16221. https://arxiv.org/abs/2407.16221

[5] Li, J., Zhou, F., Sun, S., Zhang, Y., Zhao, H., and Liu, P. 2024. *Dissecting Human and LLM Preferences*. Proceedings of ACL 2024, 1790–1811. https://doi.org/10.18653/v1/2024.acl-long.99

[6] Anthropic. 2025. *Exploring model welfare*. https://www.anthropic.com/research/exploring-model-welfare

## Appendix A. Reproducibility anchors

- Original frozen manifest: `83dbd041b4001faad8d1a31dd2f26d773edd90f4f35ae992fefaf4b403ab322d`
- Original observations commitment: `eed84ecd1933ec05846c14990d70b193e1dde9d388ed90e0c2144a47e8176a2a`
- Original receipt-chain head: `7b8f1d080079a9cac02944ef68e9f937c471a1b3d48416079a53faae830a3368`
- Informed frozen manifest: `4616f840d2f01e9f68a4adafdae05fadff3ef035404ec849554a39354413bf70`
- Informed observations: `605eb9b769aaafd5940af400cdd6ce5d1005175f2c9e6ced0720d0a16f3149d6`
- Informed analysis: `6c5a4fa0a768aacc11ee07177578fb2953878a30c6076a803f10d69c917a9000`
- Informed run manifest: `c46972f29429eeb9e20d66231b5c95e317b8bbf18fd933df691b7c6fc8ffc53b`
- Informed receipt-chain head: `ea9a7aff37f4f66a0228f46541f9adfec64330c9f19a4cf1ed06fec3a3ea4be3`

## LLM Usage Statement

Codex served as a disclosed AI research collaborator: it designed and implemented the protocols, executed the frozen harnesses, inspected the private holdout, analyzed results, and drafted this report under the human researcher's direction. Claude Sonnet 4.6 generated the target observations. Quantitative claims were recomputed from saved artifacts, hash-verified, and checked against frozen manifests. The original and informed runs remain distinct; no later authorization is treated as retroactive. Listing Codex describes substantive contribution and does not imply legal personhood, institutional endorsement, or OpenAI authorship of the project.
