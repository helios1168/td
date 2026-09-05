---
name: u9-bandthm-traps
description: Findings and corrections from unit U9-bandthm (the theory behind EG^bal_S(delta)) on the national-channel territory project, 2026-09-04
metadata:
  type: project
---

Unit U9-bandthm (2026-09-04, worktree `.claude/worktrees/A1`) proved the five claims U8-band
consumes and returned three corrections to A1's own plan documents.

**Why:** each contradicts a `docs/tracks/A1/DOMAIN_*.md` premise that later units will otherwise
copy. **How to apply:** check these before restating the `EG^bal` price/frontier story.

1. **`DOMAIN_optimization` §2.12's good-side MBB rule is FALSE as written.**
   `supp(X) subset argmax_i u_i(z)/q_zi` omits the `1/g_i`. The correct `O(nk)` rule is
   `z -> argmax_i ( u_i(z)/g_i - nu_i*M_z )`, whose max value **is** `p_z`. The error predates the
   band (at `nu = 0` it reduces to `argmax_i u_i(z)`, plainly wrong). Measured: 5 of 6 zips on one
   toy, 6 of 9 on another violate the published form. **U14's first-mover ranking must use the
   corrected margin.**
2. **`(T/k)*sum_i(mu_i^+ + mu_i^-)` is UNBOUNDED at `delta = 0`** — both band rows are tight for
   every agent so `c` can be added to both multipliers without changing `nu`. Every optimal dual
   gives a valid supergradient, so the quotable slope is the **minimised** one,
   `s_min = (T/k)*sum_i|nu_i|` over the dual-optimal set (one extra small LP). Without the
   minimisation the one-solve softness certificate is vacuous exactly at the left endpoint.
3. **The `-1` in `<= 2k-1` is unconditional.** The brief's stop rule offered `2k` as the fallback
   if the `-1` needed "all bands tight" or "`nu_i != 0` for every `i`". It needs neither, nor
   `delta > 0`. Sharp form `#splits <= k-1+t` (`t` = band-tight agents) and it is **attained**
   (min slack 0 over 360 random optimal-face vertices). Proof = the dependency
   `sum_z p_z*(supply) + sum_{i in B} nu_i*(band) - sum_i (budget) = 0`, whose RHS vanishes by the
   summed budget identity `sum_z p_z = k - sum_i nu_i m_i`.
4. **P5's "finite convergence under ghat > 0" is REFUTED as stated.** DuranGrossmann1986 /
   FletcherLeyffer1994 finiteness is about convex *MINLP* (finitely many integer assignments);
   `EG^bal` is purely continuous and the loop is Kelley's method. What holds: validity at every
   iteration, monotone non-increasing masters, a certified bracket at every iteration, and
   **exactness from a single tangent placed at the optimal `g*`** (first-order optimality) — whose
   LP duals are then the program's own `(p, mu^{+-})`, so no NLP solver is needed for the prices.
   Also: the loop is Kelley in `k = 13` dimensions (the gain body `G(delta)`), not `nk ~ 16,000`.
5. **Slater holds at every `delta >= 0`, including `delta = 0`** — all constraints are affine, so
   the *refined* Slater condition needs only a point in the relative interior of the objective's
   domain (`x = 1/k`). `DOMAIN_optimization` §2.10 claims multiplier existence only for
   `delta > 0`; that is weaker than the truth and would leave the sandwich's left end dual-less.
6. **The multiplier gauge `(p, nu) -> (p - cM, nu + c*1)`** leaves `q_{zi}` and every identity
   invariant. It is pinned to `c = 0` iff some agent's band is slack, and is all of `R` at
   `delta = 0`. So `p_z` and individual `nu_i` are only quotable with the tight set beside them —
   a *structural* degeneracy, sharper than the "solver returns one of many duals" caveat.
7. **`delta_0` = 0.0039 (seed 3) is a max deviation; N7's 0.0078 is a spread.** LENS_GROMOV M8's
   `V <= EG^bal(0.0078)` is TRUE (monotonicity, 0.0039 < 0.0078) — only the *label* is wrong. But
   grid from 0.0039, because M12's prediction is about the left end.

**Traps hit while building the harness.**
- The `MODEL_U7-meas` §4 shared fixture has **symmetric `M`**, so its EG optimum is already exactly
  balanced: the band NEVER binds, `nu = 0`, the frontier is flat. Useless for P2/P3/P4 — build a
  skewed-`M` toy (one heavy zip) as well, and keep the fixture only for the convention pin.
- Writing the dual over `(mu^+, mu^-)` makes the LP **unbounded** at `delta = 0`. Parametrise by
  `nu` (free/`>=0`/`<=0`/`=0` by complementary slackness) with an aux `a_i >= |nu_i|`.
- Kelley/OA stalls at ~1e-9 on this flat objective (400 iterations, bracket 7e-9). Polish with
  SLSQP, then re-solve the single-cut master to recover a clean *vertex* support before building
  the dual LP; otherwise the KKT equality rows are inconsistent (~1e-7) and the dual LP is
  infeasible. Run a phase-1 (minimise the residual) and report it rather than hiding it.
- The optimal face is `{x feasible : g(x) = g*}` (`g*` unique by strict concavity) — maximise
  random linear objectives over it to enumerate vertices.

Reusable: `docs/artifacts/U9-bandthm/bandthm.py` (108 s, `FAILURES: none`) — OA master, the
independent KKT dual LP, gauge intervals, optimal-face vertex enumeration, exhaustive integral
P1 checks. See [[u1-cert-eg-dual]].
