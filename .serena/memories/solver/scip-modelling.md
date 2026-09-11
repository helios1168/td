# SCIP on td's programs: what works and what to distrust

- **Epigraph form with an auxiliary gain variable** (`g_i ≤ Σu·x`, `t_i ≤ log g_i`, `g_i`
  lower-bounded from the OA incumbent) solves k = 13 / n = 1,229 at δ = 0.33 in about 5 s.
  Taking `log` of the 1,229-term expression directly takes 380 to 430 s. The recipe in trap 14
  (AGENTS.md) is load-bearing: `ga ≤ Σu·x`, not `==`, and dual reductions
  (`misc/allow{strong,weak}dualreds`) off for any lazily separated model.
- **`getDualbound()` is not rigorous at 1e-9.** At δ = 0.05 it returned `optimal` with a bound
  5.9e-9 below a certified-feasible primal. Use it as a cross-check only; never let it replace
  an LP or weak-duality bound at tier 1 (`CERT_TOL = 1e-8`).
- For MILP verification set `limits/gap` and `limits/absgap` to 0.
- SCIP exact closes real districts in the app's zip-level split engine
  (`td/solvers/district_split.py`, greedy warm start then SCIP) in under 10 s.
- The engine seam is `_scip_solve` in `td/solvers/milp_engines.py`, next to the HiGHS path
  (`mem:solver/highs-and-scipy`).

Source: `.claude/agent-memory/code-verify/project_td-verification-oracles.md`; host memory
td-app-rebuild-2026-09-08; `worktree-full-problem:PLAN.md`.
