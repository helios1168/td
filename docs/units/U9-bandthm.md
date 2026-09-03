# Unit U9-bandthm — the four claims `EG^bal_S(δ)` rests on

The theory U8-band consumes. Each is a `[claim]` in `DOMAIN_optimization` §2.10–§2.11 or
`DOMAIN_economic-theory` §2.8–§2.9; two are now citations per `LIT_optimization` §0.

## Spec (verbatim from `docs/DOMAIN_optimization.md` §2.10, §2.11 and `docs/DOMAIN_economic-theory.md` §2.9)

> **`EG^bal_S(δ)` upper-bounds every integral coverage with roster `S` whose districts respect
> the band at `δ`.** `[claim — P1's proof with one extra feasibility check; math-verify]`
>
> Stationarity at an optimum reads `u_i(z)/g_i ≤ p_z + ν_i·M_z`, with equality on `supp(X)`.
> … the modified budget identity `Σ_z p_z x_{zi} = 1 − ν_i m_i`, and summing over `i`,
> `Σ_z p_z = k − Σ_i ν_i m_i`. `[claim; math-verify]`
>
> *Sharp (the MBB-restricted face).* … one dependency survives and the count is **`≤ 2k−1`**.
> `[claim]`
>
> `d EG^bal_{S₁₃}(δ) / dδ = (T/k)·Σ_{i∈S} (μ_i^+ + μ_i^-)   [claim]`
>
> Each tangent is a **global overestimator** of `log` (concavity), so **every master optimum is
> a valid upper bound on `EG^bal(δ)`** … That property … must be tested.

## Files owned

`docs/MODEL_U9-bandthm.md` (by `modeler`) · `docs/VERIFY_U9-bandthm.md` (by `math-verify`) ·
`docs/artifacts/U9-bandthm/**`.

## Files forbidden

Every other unit's owned files (`docs/MODEL_U8-band.md`, `td/solvers/eg_band.py`, …) ·
`docs/FRAME.md` · `docs/BRIEF.md` · `docs/APPROACHES.md` · `docs/LENS_*.md` · `docs/DOMAIN_*.md` ·
`docs/LIT_*` · `docs/channel_note/**` · `CLAUDE.md` · all of `td/`, `tests/`, `tools/` (read-only;
toy scripts live under the artifacts directory).

## Agent → verifier

`modeler` → `math-verify`.

## Acceptance

VERIFIED or REFUTED (not INCONCLUSIVE) on each of:

- **P1-band.** For fixed `S` and `δ ≥ 0`, `V(π,σ) ≤ EG^bal_S(δ)` for every integral coverage with
  `im σ = S` whose districts satisfy the band; at every `ρ ≥ 0` under `MODEL_U1-cert`'s H3.
- **P2-price.** The KKT system of `EG^bal_S(δ)`; the personalised-price form
  `π_i(z) = p_z + ν_i M_z`; the budget identities. State explicitly, with `jalota2023`
  (`LIT_optimization` §1) and `echenique2021constrained` (`LIT_economic-theory` 2026-09-03 §0),
  that this is a multiplier statement and that the optimum is **not** a competitive equilibrium
  at the stated budgets — the sentence U12-menu is allowed to quote.
- **P3-split.** Split units `≤ k − 1 + #tight band rows ≤ 2k − 1` at a vertex of the optimal
  face. Cite `lenstra1990` / `shmoystardos1993` / `lauravisingh2011` for the pattern
  (`LIT_optimization` §0); prove only the budget-identity dependency that makes it `2k − 1`
  rather than `2k`. State whether the `− 1` survives when some `ν_i = 0`.
- **P4-slope.** The envelope identity for the value function, its concavity and monotonicity in
  `δ`, the one-sided derivatives at a kink, and the one-solve softness certificate as a
  corollary.
- **P5-OA.** Every optimum of the tangent master is an upper bound on `EG^bal_S(δ)`; the bound
  is monotone non-increasing in the cut set; finite convergence under `ĝ > 0`.

At PLAUSIBLE-or-better: whether `borgwardt2019`'s bounded-shape partition-polytope result
(`LIT_optimization` §0) gives a separating power diagram for the `EG^bal` vertex at `δ > 0`, so
that `cert_power_diagram`'s `O(nk)` check survives the band.

Toy instances (3–5 reps, 6–12 zips) under the artifacts directory check every specialisation
numerically; the `MODEL_U7-meas` §4 toy is the shared fixture with U8.

## Numbers to compute first

None that need the real instance; the unit may read it (★6 lifted) to check P3-split's count
against U8's returned vertex once U8 exists, but must not wait for U8.

## Inputs to read (paths and sections only)

`docs/DOMAIN_optimization.md` §2.10–§2.13 · `docs/DOMAIN_economic-theory.md` §2.8–§2.9 ·
`docs/MODEL_U1-cert.md` §1–§3 (P1's proof, P3a's MBB-face argument as corrected) ·
`docs/VERIFY_U1-cert.md` §2, §5 · `docs/LIT_optimization.md` §0, §1, §2, §4 · the 2026-09-03
section of `docs/LIT_economic-theory.md` (`echenique2021constrained`, `kawase2026balanced`) ·
`docs/LENS_GROTHENDIECK.md` "The general case, stated".

## Open questions for ★0

None. ★8 (the `fotakis2014` correction) is U3-inv's, not this unit's.

## Branch

`wt/A1` (or `wt/U9-bandthm` from `wt/A1`)

## Stop rule

If P3-split's `− 1` needs a hypothesis the instance may fail (all bands tight, or `ν_i ≠ 0` for
every `i`), state the hypothesis and give the `2k` bound as the unconditional one. If P5-OA's
finite convergence needs a compactness argument the polytope does not supply, say so; the
upper-bound property is what U8 needs and it does not depend on convergence.

**stop and report rather than improvise**
