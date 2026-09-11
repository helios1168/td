# Verification oracles for the Eisenberg-Gale programs

Established verifying U8-band (2026-09-04) and U1-cert (2026-09-03).

- **Proportional response dynamics** (Fisher market, budgets 1: `b_zi <- u_i(z)x_zi/g_i`,
  `x = b/Σ_i b`, dual `p_z = Σ_i b_zi`, upper bound `Σp - k + Σ_i log max_z u/p`) reproduces the
  unconstrained EG value on the real 1229 x 13 instance to 1e-10 in about 32k iterations, with no
  solver at all. The single best oracle for any `EG_S` number. It cannot take side constraints,
  so it does not compute the band-constrained program.
- **Certificate checking beats re-solving.** Treat the solver as untrusted: audit its `X`
  (x ≥ 0, row sums 1, band) yourself for a lower bound, and evaluate the Lagrangian dual
  `D = Σp + Σ_i(log max_z u_i/q_zi - 1) + (T/k)[(1+δ)Σμ⁺ - (1-δ)Σμ⁻]`, `q = p + νM`, yourself
  for an upper one. It needs only `μ ≥ 0` and `q > 0` and gives a bracket independent of HiGHS.
- **Secant squeeze for shadow prices.** For a concave value function, solving at `a < δ₀ < b`
  brackets the whole superdifferential between the two secants, which settles "is this slope a
  valid supergradient, and how far from minimal" without a minimisation LP.
- `scipy.optimize.minimize(method="SLSQP")` multi-start is a fine oracle for concave programs on
  toys (n·k ≤ 20 variables); agrees to 1e-9.
- **KKT residuals from an OA loop are O(√bracket)**, not O(bracket): a 3e-9 objective bracket
  buys prices good to about 1e-5. Verify by sweeping the tolerance; do not read 1e-5 as a leak.

Reusable artifacts: `tools/verify/U1-cert/eg.py` (proportional response plus the dual
`D(p) = Σ p_z - k + Σ_i log max_z(u_iz/p_z)`, a bound for any `p > 0`; 60k iterations close
1229 x 13 to 1e-13 in about 1 s) and `tools/verify/U9-bandthm/bandthm.py`
(`mem:verify/eg-band-harness`).

Theory behind the band program: `mem:model/u9-bandthm`.

Source: `.claude/agent-memory/code-verify/project_td-verification-oracles.md`;
`.claude/agent-memory/modeler/project_u1-cert-eg-dual.md`.
