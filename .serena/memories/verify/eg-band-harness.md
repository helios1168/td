# Traps when building a harness for the band-constrained EG program

Found building U9-bandthm's harness (2026-09-04).

- **The U7-meas shared fixture has symmetric `M`** (`docs/units/U7-meas.md` `## Model` §4), so
  its EG optimum is already exactly balanced: the band never binds, `ν = 0`, the frontier is
  flat. It is useless for the price and frontier claims. Build a skewed-`M` toy (one heavy zip)
  as well, and keep the fixture only for the convention pin.
- **Writing the dual over `(μ⁺, μ⁻)` makes the LP unbounded at δ = 0.** Parametrise by `ν`
  (free, ≥ 0, ≤ 0 or = 0 by complementary slackness) with an auxiliary `a_i ≥ |ν_i|`.
- **Kelley / OA stalls at about 1e-9** on this flat objective (400 iterations, bracket 7e-9).
  Polish with SLSQP, then re-solve the single-cut master to recover a clean vertex support
  before building the dual LP; otherwise the KKT equality rows are inconsistent (about 1e-7) and
  the dual LP is infeasible. Run a phase 1 (minimise the residual) and report it rather than
  hiding it.
- **The optimal face is `{x feasible : g(x) = g*}`** (`g*` unique by strict concavity).
  Maximise random linear objectives over it to enumerate vertices; min slack 0 over 360 random
  vertices is how the sharp `k-1+t` split bound was shown attained.

Reusable: `tools/verify/U9-bandthm/bandthm.py` (108 s, `FAILURES: none`): OA master, the
independent KKT dual LP, gauge intervals, optimal-face vertex enumeration, exhaustive integral
checks.

Related: `mem:model/u9-bandthm`, `mem:verify/oracles-eg`, `mem:solver/lp-degeneracy`.

Source: `.claude/agent-memory/modeler/project_u9-bandthm.md` (2026-09-04).
