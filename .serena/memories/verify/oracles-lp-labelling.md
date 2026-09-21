# Verifying LP and labelling code (Track 1 state-border snapping, 2026-09-06)

- **Intercept `linprog` to make the solver call observable.** `centers.linprog = spy` (module
  attribute, restored in `finally`) records `(c, A_eq, b_eq, A_ub, b_ub, bounds, method,
  options)` and `res.x`. That turns "does `assign` build the model's LP" into two array
  comparisons, and it is the only way to check a "bit-for-bit / same matrices" claim: the
  repo's own git-head test only compares returned labels, which can agree by luck.
- **Two-directional LP comparison.** Rebuild the LP from scratch in raw units with hand-built
  dense matrices, then check (a) the implementation's `x` is feasible for your constraints and
  attains your optimum, and (b) your `x*` is feasible for the implementation's matrices. (a)
  alone misses over-constraining; (b) alone misses under-constraining. Cheap at n = 40, k = 3.
- **Score the rival hypothesis, not just the claim.** For "the penalty enters before the
  `/c.mean()` descale", compute both orderings and print both residuals (0.0 against 1.99). A
  single residual of 0 does not show the alternative was distinguishable.
- **Ask a metric which reference it used by computing it both ways over every recorded cell.**
  `_owner_metrics` could score against the committed owner sets or the cell's own; recomputing
  both from the written `draw.csv` plus the instance gave 0.0 against committed for all 9 cells
  and up to 2.1e-02 against own. The reading is then pinned, and the divergence is itself a
  finding.
- **Degenerate-input sweep is where the bugs are.** `refine` raises `ValueError: attempt to get
  argmax of an empty sequence` when every `state_idx` is -1 (`n_states = 0`); `pure_snap`
  guards the same case. Unreachable on the real instance, but the sweep is five lines.

Related: `mem:verify/oracles-core`, `mem:verify/oracles-milp`.

Source: `.claude/agent-memory/code-verify/project_td-verification-oracles.md`.
