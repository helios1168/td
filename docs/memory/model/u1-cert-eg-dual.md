# U1-cert: the Eisenberg-Gale dual and the four certificates

Unit U1-cert (2026-09-03, v1 instance, k = 13). Headline numbers live in `docs/units/U1-cert.md`
`## Model` / `## Verify`; read them there.

1. **Three of the four certificates collapse, not all four.** `cert_integer_balance_floor`'s
   LP relaxation has optimum `t = 0` (split every zip fractionally), so it carries no dual; it
   is the primal (achievability) half of the same sandwich. The honest organisation is one
   duality gap with two sides.
2. **Retracted: the `≤ k-1` split bound holds heterogeneously** (not only at tau = 0). A vertex
   of the optimal face is a Fisher equilibrium, so it lies in the MBB-restricted face whose
   supply and budget rows are linearly dependent (`Σ_z p_z·supply_z - Σ_i budget_i = 0`),
   giving rank `≤ n+k-1`. `brieden2017 Lem. 4` needs no replacement. General trap: before
   quoting "rank implies split count", ask whether an equilibrium or KKT restriction cuts the
   face further; the obvious description is not minimal.
3. **The `≤ k-1` count is worthless without the split masses.** Top-12 zip mass 249.39 against
   EG `g_min = 103.62` (ratio 2.41) makes the a-priori value bound infinite. Realised `M(F)` with
   10 splits gives 1.018 nats; per-agent 0.245; actual gap 5.1e-4.
4. **Headroom `u_i(z) ≤ M_z` holds only under `filler_capture="theta"`** (max ratio 1.00000042,
   the export rounding). Under `"full"` it is 1.2949. The ceiling correction is
   `Σ_{i in S} log ν_i` = +0.2584 nats at S13, not `k·log(ν_max)` = 3.360, which is 13 times
   loose and once turned a footnote into a false claim.

Traps:
- `centers.power_weights`' `beta` equals the EG multiplier only when the transportation LP is
  nondegenerate; balance-tight LPs are degenerate by construction (`mem:solver/lp-degeneracy`).
  `ω_j = 1/(ρ m*_j)` is always a dual optimum.
- Split sets are vertex-dependent: quote `|F| ≤ k-1`, `M(F) < g_min` and the direction of the
  bound chain, never a bare `M(F)`.
- Two `u` conventions: `model.utilities` masks non-candidates to 0, `channel.gain_matrix` does
  not. Compare against `stage2` with the unmasked one.
- Never name a scratch script `numbers.py`: it shadows stdlib `numbers` and numpy dies.

Reusable: `tools/verify/U1-cert/eg.py`, proportional response plus the Lagrangian dual
`D(p) = Σ p_z - k + Σ_i log max_z(u_iz/p_z)`, a bound for any `p > 0` (`mem:verify/oracles-eg`).

Source: `.claude/agent-memory/modeler/project_u1-cert-eg-dual.md` (2026-09-03).
