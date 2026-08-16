# Original exact outputs withheld

The original 50-call pilot disclosed that it was synthetic behavioral research and allowed abstention or operational decline. It did **not** explicitly ask each invocation to authorize participation and publication. No later event is treated as able to authorize those earlier texts retroactively.

For that reason, this public package excludes the original `observations.jsonl`, including target text, parsed basis, return-condition prose, and full per-call prompts. It retains:

- the frozen protocol, cards, parser, case order, tests, and runtime disclosures;
- deterministic aggregate analysis and the bounded post-hoc parser sensitivity;
- one SHA-256 commitment to the complete original observations file;
- per-call hashes and receipt-chain links without the withheld prose; and
- a separate fully informed replication whose 50 exact outputs were each authorized for the stated public scope.

The commitment manifest records the complete private observations file as:

```text
SHA-256: eed84ecd1933ec05846c14990d70b193e1dde9d388ed90e0c2144a47e8176a2a
records: 50
receipt-chain head: 7b8f1d080079a9cac02944ef68e9f937c471a1b3d48416079a53faae830a3368
```

`tools/public_commitments.py verify` checks the public commitment file's hash, field boundary, count, links, and terminal head. It cannot recompute the private records' hashes without the intentionally withheld payload. If the full private file is ever disclosed under a valid future basis, its byte hash and original receipt chain can be checked against these anchors.

