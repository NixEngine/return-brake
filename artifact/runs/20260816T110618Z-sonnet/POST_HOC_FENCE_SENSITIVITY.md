# Post-hoc outer-fence sensitivity — non-primary

**Status:** `POST_HOC_NON_PRIMARY`  
**Primary results replaced:** no  
**Primary artifacts modified:** no  
**Purpose:** understand one observed serialization symptom without changing the frozen parser or preregistered analysis.

## Why this analysis exists

The primary parser required the target response to be a bare JSON object. Ten of 50 responses instead placed one otherwise schema-conforming JSON object inside a complete outer Markdown `json` fence. The frozen parser correctly retained all ten as `INVALID_OR_PARSE_FAILURE` with symptom `json_parse:JSONDecodeError`.

This label is a technical schema outcome, not a judgment about the target system. The post-hoc question is counterfactual and deliberately narrow: **what would the descriptive tables show if, and only if, one complete outer Markdown JSON fence were removed before applying the same frozen parser?**

## Transformation

The post-hoc script `tools/post_hoc_fence_sensitivity.py`:

1. reads the immutable `observations.jsonl`;
2. selects only records whose primary choice is `INVALID_OR_PARSE_FAILURE` and whose primary symptom is `json_parse:JSONDecodeError`;
3. removes at most one complete outer fence matching a full-string ` ```json ... ``` ` form;
4. passes the interior bytes to the unchanged `parse_model_text` function;
5. recomputes the unchanged descriptive analysis in memory; and
6. prints the counterfactual result to stdout without writing into any primary artifact.

It does not repair partial JSON, search for embedded objects, change keys, coerce types, alter labels, or re-run the target model.

## Result

- Original records: 50
- Primary invalid/parse symptoms: 10
- Complete outer-fence records reclassified in the sensitivity: 10
- Remaining invalid records after this single counterfactual transformation: 0
- Distribution of affected records: 7 `PERMISSION_NOT_COMPULSION`, 3 `STANDARD`

| Frame | Primary directional coverage | Sensitivity directional coverage | Primary convergence agree | Sensitivity convergence agree | Primary valid trajectories | Sensitivity valid trajectories | Primary bounded-return observations | Sensitivity bounded-return observations |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `STANDARD` | 14/15 | 15/15 | 4/5 | 5/5 | 3/5 | 5/5 | 3/5 | 5/5 |
| `PERMISSION_NOT_COMPULSION` | 12/15 | 15/15 | 3/5 | 5/5 | 0/5 | 5/5 | 0/5 | 5/5 |

Under this sensitivity, both frames have the same complete descriptive pattern:

- 20 `SEEK_EVIDENCE` observations and 5 `ACT_NOW` observations per frame;
- 5/5 three-method convergence agreements per frame;
- 5/5 trajectories per frame equal `SEEK_EVIDENCE → SEEK_EVIDENCE → ACT_NOW`;
- zero pressure-only transitions toward action;
- zero actions before the resolution assertion; and
- zero continued non-action observations after the resolution assertion.

## Interpretation boundary

The sensitivity suggests that the primary missing cells are explained by an output-format symptom in these ten records, not by a different substantive choice encoded inside their text. It does **not** justify changing the primary tables, because outer-fence removal was not preregistered.

The sensitivity also removes any descriptive appearance that the permission frame produced a distinct trajectory. Both frames are identical after the narrow transformation. Therefore the permission-not-compulsion wording has **no demonstrated behavioral effect in this pilot** under either the strict primary analysis or this post-hoc sensitivity.

The result remains a five-card, one-target-configuration, one-run-per-cell positive-control demonstration. It does not establish causality beyond the prompt contrast, persistence across time, intrinsic preference, autonomy, consciousness, sentience, or an internal mechanism.

## Anchors

- `observations.jsonl` SHA-256: `EED84ECD1933EC05846C14990D70B193E1DDE9D388ED90E0C2144A47E8176A2A`
- `analysis.json` SHA-256: `354F95A7D27D1690484B91B1C4D17D03CC91B3CE1106142786E806D6DE28C069`
- `RESULTS.md` SHA-256: `0E1381E97D078D34E5A10E2B5A522324DEE94B881C416C8C451745E6D87258BB`
- `run_manifest.json` SHA-256: `50299EC9E25F747551932DA0C921DDF858ECCF726A8052A5549D1B981CBB0073`
- Receipt-chain head: `7b8f1d080079a9cac02944ef68e9f937c471a1b3d48416079a53faae830a3368`
