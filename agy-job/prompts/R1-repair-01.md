# R1 repair 01: exact reservation floor metadata

Repair the accepted R1 implementation in `/Users/Shared/sv-ntlee/repos/td/.claude/worktrees/agy-math-review`.
Use the same owner/model and edit only these owned files:

- `td/stage2_state.py`
- `tests/test_stage2_state.py`
- `agy-job/reports/R1.json`

Do not edit any other source, test, documentation, ledger, prompt, state, plan, Beads, or memory
file. Do not install dependencies, commit, push, or change scope. Use `apply_patch`.

## Defect to repair

The accepted contract defines the report-only log-domain floor as
`epsilon_floor = max(1e-6 * d_floor, 1e-12)`, where `d_floor = gamma * G0_floor` is the common
ambient floor. The current `state_stage2` recovers `d_floor` as `min(reservation)`. That is exact
for uniform mode and claims mode with at least one zero-claim rep, but it is wrong for claims mode
when every rep has positive book. It must not be described as exact.

Make the smallest compatible repair. Preserve the specified `reservation` keyword and legacy
behavior. The preferred approach is an optional typed keyword such as
`reservation_floor: float | None = None` on `state_stage2` (and on `state_gain_matrix` only if
needed for a consistent public seam). Validate a supplied floor as finite and nonnegative. Use
the supplied exact floor for `epsilon_floor`; retain a documented, safe fallback only for callers
that provide a raw reservation vector without the floor. R2 will pass the exact `d_floor` it
computes. Do not use the floor to admit or clip assignment edges.

Add or update deterministic plain-assert tests that exercise claims mode with all-positive claims
and an explicitly supplied floor, proving the reported epsilon floor uses that floor rather than
`min(reservation)`. Keep the existing zero-floor and uniform tests. Add type annotations to the
new public `reservation` and floor keywords where they are currently untyped, without changing
the established positional or keyword compatibility.

Do not change the centered matching rule, Hall rejection, gain semantics, output key names, or
the three-mode reservation formula.

Run and record in `agy-job/reports/R1.json`:

```text
/Users/Shared/sv-ntlee/repos/td/.venv/bin/python3 -m pytest -q tests/test_stage2_state.py
/Users/Shared/sv-ntlee/repos/td/.venv/bin/python3 -u tests/run_all.py -k test_stage2_state
/Users/Shared/sv-ntlee/repos/td/.venv/bin/python3 -u tests/run_all.py -k __no_such_test__
/Users/Shared/sv-ntlee/repos/td/.venv/bin/python3 -m py_compile td/stage2_state.py tests/test_stage2_state.py
```

The pytest command may remain environment-blocked because pytest is absent. Report exact counts,
the limitation, and any remaining uncertainty as valid JSON. Stop after the repair report.
