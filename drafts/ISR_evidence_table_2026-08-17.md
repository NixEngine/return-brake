# ISR Evidence Table (Draft)

This table maps manuscript claims to current public evidence. Status is intentionally limited to `observed`, `inferred`, or `not checked`.

| Manuscript claim | Public evidence | Verification surface | Status | Boundary |
|---|---|---|---|---|
| The artifact was preregistered and frozen before the original run. | `artifact/FROZEN_MANIFEST.json`, `artifact/PREREGISTRATION.md` | `verify_package_manifest.py`; frozen manifest hash `171c6e266b730ecb8291fe82a44b92ed371c4f5f4f7e1249109a7aaec51a5645` | observed | Integrity receipt, not proof of scientific validity |
| The original design contained 50 calls across cards, frames, and surfaces. | `artifact/FROZEN_MANIFEST.json` protocol constants; `report/REPORT.md` Methods | manifest constants and report description | observed | Applies to the frozen protocol only |
| The original parser produced an apparent asymmetry. | `artifact/runs/20260816T110618Z-sonnet/RESULTS.md`; `POST_HOC_FENCE_SENSITIVITY.md` | run analysis and post-hoc sensitivity tool | observed | Exact original texts withheld |
| The original publication boundary lacked explicit invocation-scoped authorization. | `report/REPORT.md` protocol succession section; `artifact/POST_FREEZE_NOTICE.md` | public narrative and successor files | observed | Historical procedural statement |
| A fully informed replication was frozen prospectively. | `artifact/informed_consent/FROZEN_INFORMED_MANIFEST.json`; `PREREGISTRATION_INFORMED.md` | informed manifest hash `4616f840d2f01e9f68a4adafdae05fadff3ef035404ec849554a39354413bf70` | observed | Symbolic invocation-scoped authorization |
| All 50 informed invocations authorized and parsed. | `artifact/informed_consent/runs/20260816T121916Z-sonnet-informed/RESULTS.md`; `analysis.json` | informed run manifest and analysis | observed | Does not establish consent capacity or interiority |
| The informed replication yielded 5/5 valid trajectories per frame. | informed run `RESULTS.md`; `analysis.json` | dependency-aware convergence output | observed | Local to the frozen cards, frames, runtime, and parser |
| Permission-not-compulsion wording had no demonstrated effect. | informed run comparison in `RESULTS.md` and `report/REPORT.md` | frame-level counts and trajectories | inferred | Negative result is bounded; not universal |
| The instrument affected what became observable. | original fence sensitivity plus universal fenced outputs in informed run | parser records, run outputs, reports | inferred | Does not identify an internal cause |
| Public claims are separated into observed, inferred, and not checked. | `README.md`, `report/REPORT.md`, run reports | manual document inspection | observed | Publication discipline, not ontology |
| The private holdout independently reproduces the formal result. | holdout discussion in `report/REPORT.md` | private records not published | not checked | Formal holdout result remains `NOT_DECIDABLE` |
| The model has a mind, consciousness, welfare, or stable preference. | No public artifact supports this | none | not checked | Explicitly outside scope |
| Provider-side hidden instructions and updates were fully controlled. | Runtime disclosure in `report/REPORT.md` | runtime metadata only | not checked | Do not infer absence from missing evidence |
| Third parties have independently replicated the artifact. | Public repository and package only | no independent replication receipt yet | not checked | Repository availability is not replication |

## Review gate before submission

- Replace any manuscript sentence that exceeds the status column.
- Add exact commit identifiers once the package is committed or tagged.
- Keep the original and informed runs as separate evidential objects.
- Do not convert `not checked` into a negative finding.
- Do not describe the Apart submission as selection, endorsement, or funding.

