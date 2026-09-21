# Headline values on one nats scale (v2, k = 18, seed 2)

One instance (v2 whole), one draw (k = 18 seed 2), one scale. Reference values:
`δ₀ = 0.009970`, `V = 95.755192`, `EG_{S₁₈} = 96.532152`.

- **Balance is free.** Widening the band 33-fold buys 0.051 nats.
- **The incumbency premium is 0.72 to 0.78 nats and is not soft** (D1′: 146 to 155 times the
  5e-3 tier-2 floor, no `δ*`).
- The roster is worth **0.249 nats** (v1: 0.043).
- Match gap 0, map gap 0.663.
- Pinning a region costs 0.008 (CAROLINAS) to 2.04 (CALIFORNIA) nats; CALIFORNIA is about three
  times the whole premium. FLORIDA `fix` and CAROLINAS `anchor` out-staff the baseline at
  stage 2 (+0.029 / +0.012). Table: `mem:facts/region-pin-costs`.
- Premium ladder v2: `P₀` 41.53%, `P_S` 54.42%, `P₁₈` 59.27%, `P_free` 84.17% of book.

Acceptance tiers: tier 1 `CERT_TOL = 1e-8`; tier 2 `base.EPS_CERT = 5e-3` nats, grounded on a
measured data-noise floor.

Related: `mem:facts/phase0-measurements`, `mem:model/reference-parameters`.

Source: `main:STATE.md` `## Facts` (a3924e8); CLAUDE.md two-tier acceptance line.
