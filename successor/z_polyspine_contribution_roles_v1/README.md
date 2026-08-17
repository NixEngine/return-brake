# Contribution-role separation successor v1

This post-P3 successor implements the typed boundary requested by P2 finding
`p2-f03` without changing the frozen `successor/z_polyspine` bytes.

When one ledger contains the complete role family `CONCEPTION`,
`AUTHENTICATION`, `COMMAND_DISPATCH`, `PROCESS_EXECUTION`, and
`PUBLICATION_INITIATION`, those bindings must resolve to at least two valid
protocol principals. Roles outside that family do not count toward the
threshold. A second principal recorded only for `VERIFICATION` therefore does
not mask concentration of all five material roles in one principal.

Run the successor and its regression suite with:

```bash
python successor/z_polyspine_contribution_roles_v1/verify.py verify-local
python -m unittest successor/z_polyspine_contribution_roles_v1/tests/test_verify.py -v
```

This boundary verifies ledger structure, not inaccessible causality or
interiority. It activates only when the complete five-role family is present;
it does not infer missing roles and does not decide authorship, merit, legal
identity, or whether an observation omitted unrecorded contributors.
