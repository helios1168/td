# Unit U9-bandthm — the four claims `EG^bal_S(δ)` rests on

Status: done

The theory U8-band consumes. Each is a `[claim]` in `DOMAIN_optimization` §2.10–§2.11 or
`DOMAIN_economic-theory` §2.8–§2.9; two are now citations per `LIT_optimization` §0.

## Spec (verbatim from `docs/foundations/DOMAIN_optimization.md` §2.10, §2.11 and `docs/foundations/DOMAIN_economic-theory.md` §2.9)

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
`tools/verify/U9-bandthm/**`.

## Files forbidden

Every other unit's owned files (`docs/MODEL_U8-band.md`, `td/solvers/eg_band.py`, …) ·
`docs/foundations/FRAME.md` · `docs/foundations/BRIEF.md` · `docs/foundations/APPROACHES.md` · `docs/foundations/LENS_*.md` · `docs/foundations/DOMAIN_*.md` ·
`docs/foundations/LIT_*` · `docs/channel_note/**` · `CLAUDE.md` · all of `td/`, `tests/`, `tools/` (read-only;
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

`docs/foundations/DOMAIN_optimization.md` §2.10–§2.13 · `docs/foundations/DOMAIN_economic-theory.md` §2.8–§2.9 ·
`docs/MODEL_U1-cert.md` §1–§3 (P1's proof, P3a's MBB-face argument as corrected) ·
`docs/VERIFY_U1-cert.md` §2, §5 · `docs/foundations/LIT_optimization.md` §0, §1, §2, §4 · the 2026-09-03
section of `docs/foundations/LIT_economic-theory.md` (`echenique2021constrained`, `kawase2026balanced`) ·
`docs/foundations/LENS_GROTHENDIECK.md` "The general case, stated".

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

## Model

From `docs/MODEL_U9-bandthm.md` (2026-09-04). Headline: all five claims survive, four of them as
theorems and one — P5's finite convergence — only after being restated. Three corrections fall
out of the proofs, one load-bearing for U8 and U12: (1) `DOMAIN_optimization` §2.12's good-side
selection rule is false as written (omits the `1/g_i` normalisation; 6 of 9 zips on toy2 violate
it). (2) `(T/k)Σ_i(μ_i^+ + μ_i^-)` is unbounded above at `δ = 0`; U8 must report the **minimised**
`(T/k)Σ_i|ν_i|`. (3) The `−1` in `≤ 2k−1` needs no hypothesis; `k − 1 + t` is the sharp form and
is attained.

**Propositions.**

- **P0 (well-posedness).** Slater's refined condition holds at every `δ ≥ 0`, including `δ = 0`.
  `[proved]` **P0b.** The optimal gain vector `g*` is unique; the optimal `X` and the split set are
  not. `[proved]`
- **P1-band.** `V(π,σ) ≤ EG^bal_S(δ)` for every integral coverage with roster `S` whose districts
  satisfy the band, at every `ρ ≥ 0` under H3. `[proved]` **P1a-band**: the band hypothesis is
  load-bearing, not decoration. `[proved; witness]` **P1b-band**: the monotone chain and the left
  endpoint at `δ₀`, not the spread `0.0078`. `[proved]` **P1c-band**: the bound can be true and
  empty; that is `cert_integer_balance_floor`'s job to detect. `[proved; witness]`
- **P2-price (KKT).** P2.1 stationarity; P2.2 positivity (`q > 0` always, `p > 0` needs `δ > 0`);
  P2.3 the budget identities; P2.4 the agent-side MBB — all `[proved]`. **P2.5 (the correction)**:
  the good-side rule is `argmax_{i∈S}(u_i(z)/g*_i − ν_i M_z)`, not the published ratio form, which
  is REFUTED. `[proved; counterexample]` **P2.6**: not a competitive equilibrium at the stated
  budgets. `[proved]` **P2.7**: Pareto optimality within `F(δ)` survives; envy-freeness is lost by
  theorem; EF1 is not lost as an achievable property. `[cited: echenique2021constrained,
  kawase2026balanced, jainvazirani2010, jalota2023]`
- **P2b (the multiplier gauge).** `p`, `ν` are quotable only after the tight set is reported beside
  them; at `δ = 0` with every agent two-sided tight, the gauge is all of `ℝ`. `[proved]`
- **P3-split.** `#splits ≤ k − 1 + t ≤ 2k − 1`, the `−1` unconditional (needs no `ν_i ≠ 0`, no
  slack agent, no `δ > 0`); at `k = 13` the bound is 25 split units of 1,229. `[proved; the
  pattern is `lenstra1990`/`shmoystardos1993`/`lauravisingh2011`/`bansal2012`, only the dependency
  making it `2k−1` rather than `2k` is proved here]` **P3a-split**: the count is worthless without
  the masses. `[cited: MODEL_U1-cert P3c]`
- **P4-slope.** P4.1 monotone, P4.2 concave, P4.3 envelope/supergradient — `[proved]`. **P4.4 (the
  correction)**: the raw aggregate is not unique and is unbounded at `δ = 0`; only `s_min`, the
  minimised gauge-reduced value, should be reported. `[proved]` P4.5 one-sided derivatives and
  kinks; P4.6 the one-solve softness certificate; P4.7 the two-sided envelope from a grid; P4.8
  bisection licensed by monotonicity alone — all `[proved]`.
- **P5-OA.** P5.1 validity (the safety property) — every master optimum is an upper bound, at
  every iteration; P5.2 monotone in the cut set; P5.3 `ĝ > 0` with an explicit constant; P5.4 a
  single well-placed cut is exact — all `[proved]`. **P5.5 (REFUTED as stated, restated
  correctly)**: the DuranGrossmann1986/FletcherLeyffer1994 finite-convergence theorems are about
  MINLPs and do not apply to this purely continuous master; only `ε`-termination holds. `[proved]`
  P5.6: what breaks validity (a `time_limit` or nonzero `mip_rel_gap` is not a bound). `[proved]`
- **P6-cells.** The `O(nk)` separating-cell certificate survives the band, proved directly; the
  `borgwardt2019` bounded-shape-partition result is corroborating, not the source, and does not
  transfer geometrically. `[proved directly; cited for the constraint class only]`

**Numbers computed** (§4; `tools/verify/U9-bandthm/bandthm.py`, 108 s, `FAILURES: none`, on toy
fixtures — this unit deliberately computes nothing on the real instance).

| quantity | value |
|---|---|
| toy3, 360 optimal-face vertices, sharp bound `k−1+t` | min slack **0** — the bound is attained |
| toy3, coarse bound `2k−1` | min slack 1 — never attained |
| toy2 P4.6 softness certificate, one-solve bound vs true value | slack `4.645e-03` |
| kink toy3 at `δ_c = 0.111111` | `D⁺/s_min/D⁻ = 0/0/0.154586` |
| at `k = 13`: `k−1 = 12`, `2k−1 = 25`, `2k = 26` | `25` split units of 1,229 |
| slope that would exhaust the certified `0.760`-nat gap from `δ₀` to `δ = 0.02/0.05/0.10/0.33` | `47.20/16.48/7.91/2.33` nats per unit `δ` |

**Open.** Whether the real instance's `s_min(δ₀)` is below `2.33` or above `47.2` nats per unit
`δ` (needed U8's first solve — since resolved: v2 measured `s_min(δ₀) = 0.5856`, well under
`2.33`, so the one-solve certificate covers the whole grid). An explicit iteration bound for
P5.5(iv). Whether `∂φ(δ)` equals the closure of the multiplier aggregates, not merely contains it
(nothing downstream needs it). Everything at `ρ > 0` beyond P1-band. `borgwardt2019`'s normal-cone
volume as a stability radius — flagged for U4-disp, not pursued here. `budish2013`'s bihierarchy
class membership — a citation, not re-derived.

Full report: `git show 8b14eee:docs/MODEL_U9-bandthm.md`.

## Verify

From `docs/VERIFY_U9-bandthm.md` (2026-09-04, `math-verify`, independent SCIP primal/dual and
exact-rational brackets — never reruns the model's own scipy/HiGHS solve). **All five
brief-mandated propositions passed**, with four corrections to report and one new hazard the model
did not name.

| # | proposition | verdict |
|---|---|---|
| P0, P0b | Slater at every `δ ≥ 0`; `g*` unique | VERIFIED |
| **P1-band** | `V ≤ EG^bal_S(δ)` for every band-feasible integral coverage | **VERIFIED** |
| P1a/P1b/P1c-band | load-bearing; monotone chain; can be true and empty | VERIFIED (P1b: citation slip noted, no change to the recommendation) |
| P2.1–P2.4, P2.6, P2b | stationarity, positivity, budget identities, MBB, non-equilibrium, gauge | VERIFIED |
| **P2.5** | corrected good-side rule; §2.12 REFUTED | **VERIFIED — refutation confirmed and sharpened** with a smaller (`n=1,k=2`) counterexample |
| P2.7 | fairness reading | VERIFIED as a citation check, one over-reach on `kawase2026balanced`'s scope |
| **P3-split** | `#splits ≤ k−1+t ≤ 2k−1`, `−1` unconditional | **VERIFIED (with a counting warning)** — a 1e-9 support threshold below solver dirt manufactures phantom splits; clean-and-recertify first |
| P4.1–P4.3, P4.5, P4.7, P4.8 | monotone, concave, supergradient, kinks, envelopes, bisection | VERIFIED |
| **P4.4** | aggregate non-unique and unbounded at `δ=0` | **VERIFIED and strengthened** — `Σ_i|ν_i|` is itself gauge-dependent at `δ=0` (factor 16.4 measured), and an `ε`-relaxed minimisation biases `s_min` downward into an **invalid** supergradient |
| P5.1–P5.4, P5.6 | validity, monotone in cut set, `ĝ>0`, single-cut exactness, what breaks validity | VERIFIED (P5.4's converse newly proved) |
| **P5.5** | finite convergence REFUTED, restated | **VERIFIED — the refutation stands, and is not an evasion** |
| P6-cells | direct half | VERIFIED; `borgwardt2019` half PLAUSIBLE (citation-level only) |

No proposition was REFUTED outright; P2.5 and P5.5 confirm refutations the model itself already
made (of `DOMAIN_optimization` §2.12 and of the brief's own "finite convergence" claim,
respectively) and sharpen them.

**Instructions to U8-band** (all since implemented and confirmed in `MODEL_U8-band.md`): grid from
`δ₀`, not `0.0078`; compute `s_min` as a minimisation over the exact dual-optimal set,
gauge-reduce it, and sanity-check it against a further grid point before quoting P4.6; rank first
movers by the additive margin, never the ratio form; clean and re-certify the returned vertex
before counting splits; report `t`, the tight set and the gauge width beside `p`, `ν` and the
split count; never report "OA converged"; run the P1c check first.

**Artifacts**, moved out of the deleted per-unit artifacts directory to `tools/verify/U9-bandthm/`:
`bandthm.py` (the model's own), and under `verify/`: `sym.py`, `oracle.py`, `num.py`,
`p3_probe.py`, `p3_attack.py`, `smin.py`.

Full report: `git show 8b14eee:docs/VERIFY_U9-bandthm.md`.

## Code verify

none yet
