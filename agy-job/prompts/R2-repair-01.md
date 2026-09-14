# R2 repair 01: validate reservation parameters in legacy mode

Repair the accepted R2 implementation in `/Users/Shared/sv-ntlee/repos/td/.claude/worktrees/agy-math-review`.
Use the same owner/model and edit only:

- `tools/full_plan.py`
- `tests/test_full_plan_cli.py`
- `agy-job/reports/R2.json`

Do not edit any other source, test, documentation, model, ledger, prompt, state, plan, Beads, or
memory file. Do not install dependencies, commit, push, or change scope. Use `apply_patch`.

## Defect to repair

`_compute_reservation_for_plan` returns immediately for `args.stage2_reservation == "none"`, so
`--stage2-reservation none --reservation-gamma -1` or a non-finite gamma/epsilon is silently
accepted. R2's contract says the CLI values are validated through R1's
`compute_reservation_vector`, and invalid gamma/epsilon must be rejected regardless of the chosen
mode. The legacy none path must remain numerically and geometrically unchanged for valid values.

Make the smallest repair. In none mode, invoke the R1 helper on a zero-length or zero-valued
synthetic book with zero region quantities and zero floor, solely to exercise its mode/range/input
validation, then return `(None, 0.0)` as before. Do not compute or apply a reservation in the
legacy path. Alternatively use an equivalent shared validation call that cannot change the output.

Add a focused plain-assert test showing invalid gamma and epsilon raise even when mode is `none`,
and retain the existing defaults/custom-mode tests and toy runs. Do not weaken claims or uniform
validation.

Run and record in `agy-job/reports/R2.json`:

```text
/Users/Shared/sv-ntlee/repos/td/.venv/bin/python3 -m pytest -q tests/test_full_plan_cli.py
/Users/Shared/sv-ntlee/repos/td/.venv/bin/python3 -u tests/run_all.py -k test_full_plan_cli
/Users/Shared/sv-ntlee/repos/td/.venv/bin/python3 -u tests/run_all.py -k __no_such_test__
/Users/Shared/sv-ntlee/repos/td/.venv/bin/python3 -m py_compile tools/full_plan.py tests/test_full_plan_cli.py
```

The pytest command may remain environment-blocked because pytest is absent. Report exact counts,
the limitation, and any remaining uncertainty as valid JSON. Stop after the repair report.
