# MODEL U8-band — `EG^bal_{S₁₃}(δ)`: the band-constrained fibre, its duals, the softness certificate and the frontier

**Date:** 2026-09-04 · **Unit:** `docs/tracks/A1/units/U8-band.md` · **Track:** A1
(`docs/APPROACHES.md` §A1), run on `wt/A1` · **Reads:** `docs/tracks/A1/DOMAIN_optimization.md`
§2.10–§2.12, §3, §4, §5 rows 1/2/4; `docs/tracks/A1/DOMAIN_economic-theory.md` §2.8, §2.9, N7–N9;
`docs/tracks/A1/LENS_GROMOV.md` M8/M11/M12; `docs/MODEL_U1-cert.md` P1 and §4.1;
`docs/MODEL_U7-meas.md` §4 and §6; `td/channel.py`, `td/model.py`, `td/instance.py`,
`td/solvers/centers.py`, `docs/artifacts/U1-cert/{eg.py,instance_numbers.py}` ·
**Implements:** `td/solvers/eg_band.py` and `tools/measure/frontier.py` (written by
`python-typed`, checked by `code-verify` → `docs/CODEVERIFY_U8-band.md`)

This is A1's kill test. Stage 0 is discharged (FRAME §6): `B_tot = 1145.81`, the roster-free
screen (★) at `P₁₃` = 60.8025, and `δ₀ = 0.39 %` on seed 3 / `0.62 %` on seed 9. Everything below
is one concave program, its duals, and the curve they bound.

---

## 1. The program

Fix the roster `S = S₁₃` (13 wholesalers, the image of stage 2 at the committed draw), the
utilities `u_i(z) > 0`, the common measure `M_z > 0`, `T = Σ_z M_z`, `k = |S| = 13` and the
per-district target `T/k`. For `δ ≥ 0`,

```
EG^bal_S(δ) = max_X  Σ_{i∈S} log g_i(X),        g_i(X) = Σ_z u_i(z)·x_{zi}
     s.t.   Σ_{i∈S} x_{zi} = 1                  ∀z          [duals p_z, free]
            Σ_z M_z x_{zi} ≤ (1+δ)·T/k          ∀i∈S        [duals μ_i^+ ≥ 0]
            Σ_z M_z x_{zi} ≥ (1−δ)·T/k          ∀i∈S        [duals μ_i^- ≥ 0]
            x ≥ 0
```

Write `m_i(X) = Σ_z M_z x_{zi}`, `ν_i = μ_i^+ − μ_i^-` for the net band multiplier, and
`hi = (1+δ)T/k`, `lo = (1−δ)T/k`. Dropping the two band families gives the unconstrained
Eisenberg–Gale fibre `EG_S`, and `EG^bal_S(δ) ↑ EG_S` as `δ` grows.

**What it bounds (P1 under the band).** `EG^bal_S(δ)` upper-bounds `V(π,σ) = Σ_j log g_{σ(j),j}`
for **every integral** coverage with roster `S` whose districts respect the band at `δ`, because
the indicator matrix `X_π` of such a coverage is feasible for the program
(`docs/MODEL_U1-cert.md` P1's proof plus one feasibility check;
`DOMAIN_optimization` §2.10). This is the only property that makes any number in this unit a
certificate rather than an estimate.

**Utility convention — the single silent failure mode.** `u_i(z)` must be the **unmasked** form
that `td/channel.py::gain_matrix` scores `V` with: a rep's utility is evaluated on *every* zip,
not only where it holds book. `td/model.py::utilities` is the **masked** form (`0` where not a
candidate) and is wrong here — 96.75 % of the `13 × 1,229` entries differ and the total utility
mass differs by 13.4×. Measured (`CODEVERIFY_U8-band.md` row 2): the masked bound lands at
`EG = 55.9763` and the masked delivered map at `Σ log g = 51.9343`, i.e. *below* `V = 59.9375`,
which would mimic a refutation of P1-band. The gate misses by 4.72 nats on the masked matrix.
Note that EG *re-optimises* against the masked structure, so the loss is far smaller than the
13.4× mass ratio suggests — an earlier ≈ 27-nat estimate scaled the gains directly and was
wrong by ~29 nats; the conclusion it supported (masked lands below `V`) is unaffected.
`docs/artifacts/U1-cert/instance_numbers.py::utility_matrix` is
the reference implementation. **Hard gate:** the unconstrained `EG_{S₁₃}` must reproduce
`60.6974156139` to `1e-6` before any frontier point is computed.

## 2. Duality, the price reading, and the solver-free certificate

Slater holds at every `δ ≥ 0`: `x ≡ 1/k` is feasible with `m_i = T/k` strictly inside the band for
`δ > 0`, and all `g_i > 0` (P1b: `u_i ≥ λ M_z > 0`). So strong duality and multiplier existence
hold and the KKT conditions are necessary and sufficient (`BoydVandenberghe2004` §5.2.3).

**Stationarity.** With the agent-specific effective price

```
q_{zi} = p_z + ν_i·M_z ,
```

optimality reads `u_i(z)/g_i ≤ q_{zi}` for all `(z,i)`, with equality on `supp(X)`. The band turns
the common price `p_z` into a personalised one: an agent pressed against its upper band pays a
surcharge proportional to a zip's opportunity content, one pressed against its lower band gets a
subsidy. The MBB reading of the unconstrained program survives with `q` in place of `p`, and with
it Pareto efficiency *within the band-feasible set*; **price anonymity and Varian's
envy-freeness argument do not** (`DOMAIN_economic-theory` §2.8).

> **Correction (U9, `docs/MODEL_U9-bandthm.md` P2.5) — the good-side rule.** Rearranged, the same
> condition reads `u_i(z)/g_i − ν_i M_z ≤ p_z`, so the good-side selection is
> ```
> supp(X*) ⊆ argmax_{i∈S} ( u_i(z)/g*_i − ν_i·M_z ),   and that maximum equals p_z.
> ```
> `DOMAIN_optimization` §2.12 publishes this as `argmax_i u_i(z)/q_{zi}` — a **ratio**, which
> drops the `1/g_i` normalisation and is false already in the unbanded case: at `ν ≡ 0` the
> denominator `p_z` does not depend on `i`, so the ratio collapses to `argmax_i u_i(z)`. U9
> measured the published form failing on 6 of 9 zips (toy2) and 5 of 6 (toy3);
> `tests/test_eg_band.py::test_published_ratio_rule_is_refuted` pins the collapse. **The
> first-mover ranking of §7 uses the corrected additive margin**, and `check_dual`'s
> `reduced = q − u/g` was already the correct condition and is unchanged.

**Gauge freedom (U9 P2b).** The split of `q_{zi}` into `p_z` and `ν_i` is not determined in
general — at `δ = 0` it is undetermined over all of `ℝ`. `q` is gauge-invariant and `p`, `ν` are
quotable only alongside the tight set, which this unit therefore reports beside them.

**The dual function, closed form.** Eliminating `x ≥ 0` from the Lagrangian gives, for any
`μ^± ≥ 0` and any `p` with `q_{zi} > 0` everywhere,

```
D(p, μ^+, μ^-) = Σ_z p_z  +  Σ_i [ log r_i − 1 ]  +  (T/k)·Σ_i [ (1+δ)·μ_i^+ − (1−δ)·μ_i^- ]
                 with   r_i = max_z u_i(z) / q_{zi}
```

and **`EG^bal_S(δ) ≤ D` by weak duality, at every dual-feasible point, converged or not.** At
`μ ≡ 0` this is exactly `docs/artifacts/U1-cert/eg.py::eg_dual`, i.e. `Σ_z p_z − k + Σ_i log r_i`.
`D` is `O(nk)` arithmetic with no solver in the trusted path, which is the same contract
`cert_power_diagram` already meets (`td/solvers/cert_draw.py`), now with the `2k` band terms.

**The `O(nk)` check, in `centers.py`'s style** (`td/solvers/centers.py:372-377`). With
`reduced_{zi} = q_{zi} − u_i(z)/g_i`,

```
viol = min(reduced.min(), 0.0)          # dual-feasibility violation
cs   = |reduced[supp(X)]|.max()         # complementary-slackness residual
```

both reported **relative** (divided by `max|reduced|`, or by `mean q`), alongside
`min_{z,i} q_{zi} > 0`, `min μ^± ≥ 0`, and the band complementary-slackness residuals
`μ_i^+·(hi − m_i)` and `μ_i^-·(m_i − lo)`.

**The `(0, None)` bounds trap.** Every LP here uses variable bounds `[0, ∞)`, never `[0, 1]`. The
feasible sets are identical (`Σ_i x_{zi} = 1` with `x ≥ 0` already forces `x_{zi} ≤ 1`), but an
explicit upper bound lets HiGHS park a reduced cost on it and the returned duals then violate
dual feasibility by an arbitrary amount — measured at `-0.80` with `[0,1]` versus `-5e-17` with
`[0,∞)` on the real `k = 13` instance (`td/solvers/centers.py:316-322`).

**Modified budget identity.** Multiplying stationarity by `x_{zi}` and summing gives
`Σ_z p_z x_{zi} = 1 − ν_i m_i` and hence `Σ_z p_z = k − Σ_i ν_i m_i` `[claim; math-verify]`. It is
computed and reported as a residual, not assumed.

**Degeneracy, and cleaning the vertex before counting.** A balance-tight polytope is degenerate
by construction. Before `ν` is read as "the" exchange rate, the support size is compared with
`n + k − 1 + t`, `t` = the number of tight band rows (`DOMAIN_optimization` §2.12;
`MODEL_U1-cert` failure mode 5). If it differs, `ν` is reported as *one* dual optimum and no
first-mover list is named from it alone.

> **Correction (`VERIFY_U9-bandthm` §10.B) — clean before counting.** A support threshold below
> the solver's dirt floor **manufactures splits**: `math-verify` reproduced 108 apparent
> violations of the split bound across 517 vertices at `x > 1e-9`, all of which dissolved on
> cleaning. The vertex is therefore zeroed below `1e-6` and each zip's row renormalised *before*
> any count, and the cleaning is re-certified rather than assumed — `g` must not move, the masses
> must stay in band, and the rank of `(supply rows | tight band rows | gain rows)` restricted to
> the support must equal `|supp|` for the point to be a vertex of the optimal face. §10.F settles
> the cap as `splits ≤ k − 1 + t ≤ 2k − 1 = 25` with the `−1` **unconditional**, so the `2k`
> fallback of §2.10 is not needed and the bound binds exactly where solver dirt would flip it.

> **Correction (`VERIFY_U9-bandthm` §10.E) — what is quotable.** `g*` and the value `φ` are
> invariants; `p`, the individual `ν_i` and the split *set* are not (`math-verify` saw 4–6
> distinct split sets at the same `g*`). Every published `p` and `ν` therefore carries `t`, the
> tight set itself and the gauge width beside it, and the **gauge-invariant `q_{zi}`** is the
> primary price object. The gauge is *pinned* whenever some agent's band is strictly slack on
> both sides, since complementary slackness then forces `ν_i = 0` exactly and no shift
> `p_z → p_z + cM_z`, `ν_i → ν_i − c` survives.

## 3. Shape facts, free before any solve

`δ ↦ EG^bal(δ)` is **nondecreasing** (the feasible set grows) and **concave** (the value function
of a concave maximisation whose right-hand side is affine in `δ`; `Rockafellar1970`). Its
supergradient at `δ` is

```
s_min(δ) = (T/k)·Σ_{i∈S} |ν_i| ,        ν_i = μ_i^+ − μ_i^-
```

— the aggregate band dual, in nats per unit of relative band width. Three consequences:

1. **One solve bounds the whole curve.** `EG^bal(δ') ≤ EG^bal(δ) + s(δ)·(δ' − δ)` for every `δ'`.
2. **Bisection for `δ*` is licensed by monotonicity**, not concavity: `EG^bal(δ) − V` is
   nondecreasing, so `δ* = min{δ : EG^bal(δ) − V > 5e-3}` is bracketed in ~8 solves.
3. Concavity predicts `LENS_GROMOV` M12's shape (fastest rise near `δ₀`); the opposite reading
   (flat, then a jump at a large-zip threshold) is a falsifiable rigidity signal, not a hunch.

> **Correction (U9 P4.3) — which supergradient.** `DOMAIN_economic-theory` §2.9 writes the slope
> as `(T/k)·Σ_i(μ_i^+ + μ_i^-)`. That aggregate is **not unique, and at `δ = 0` it is unbounded
> above**: adding any `c ≥ 0` to both `μ_i^+` and `μ_i^-` of a two-sided-tight agent changes
> nothing else, so the raw sum ranges over `[s_min, +∞)`. Every optimal dual gives a valid
> supergradient, so the D1′ bound is sound whichever is used — but the raw sum is neither the
> tightest certificate nor a reproducible number, and reading it straight off HiGHS would make
> acceptance 5's byte-identical re-run solver-dependent. **This unit reports and plots `s_min`
> only.** At `δ > 0` complementary slackness forbids both multipliers of one agent being positive
> at an optimal dual, so the two agree; the raw value is carried beside `s_min` in the manifest to
> show that they do, and any discrepancy is a degeneracy finding.

`s(δ)` is set-valued at a kink. Where the reported `δ` sits at a kink, the left and right
derivatives are reported as an interval, never a single shadow price
(`DOMAIN_economic-theory` §2.9 failure mode).

## 4. D1′ — the softness certificate

```
soft(δ_sponsor)  ⇔  EG^bal(δ₀) + s(δ₀)·(δ_sponsor − δ₀) − V(delivered)  ≤  5e-3 nats
```

Evaluated at `δ ∈ {0.02, 0.05, 0.10}`, with `0.10` the widest band on record (FRAME §3's ±10 %).
If it holds, the premium is soft across the entire plausible band, A1 is recorded
`collapsed-on-softness` with the certificate, and the problem goes to A5. If not, the frontier is
traced. **It is one solve and it is a certificate.**

> **Correction (`VERIFY_U9-bandthm` §10.A) — the certificate can be broken by a sloppy slope.**
> D1′ *is* the tangent bound, so an `s_min` minimised only to `ε` biases the slope **downward**
> and yields an **invalid** supergradient: `math-verify` measured tangent violations of
> `8.4e-6 / 9.8e-5 / 9.9e-4` nats at `ε = 1e-5 / 1e-4 / 1e-3`. This unit does **not** run a
> tolerance-relaxed minimisation, and it does not assume its `s_min` is minimal. Instead it runs
> §10.A's mandatory guard, in the strongest form available here: **every sponsor `δ` is also a
> grid point**, so `EG^bal(δ)` is solved outright and the tangent bound is checked against it,
> `bound ≥ direct`. A failure raises rather than being tuned away. Two consequences worth
> stating plainly: the softness *verdict* does not depend on `s_min` at all — it is read off the
> direct solves — and the one-solve bound is reported as the certificate it is meant to be, with
> its validity witnessed rather than asserted. §10.A(b)'s `δ = 0` gauge pathology does not arise:
> the grid starts at `δ₀ = 0.0039 > 0`, where complementary slackness forbids both multipliers of
> one agent being positive.

**Feasibility before plotting (`VERIFY_U9-bandthm` §10.D).** A bound over an empty feasible set
is true and useless. No MILP is needed to rule that out on this grid: the **delivered draw is
itself an integral coverage**, and `δ₀` is *defined* as its own max deviation, so it witnesses a
band-feasible integral coverage at every `δ ≥ δ₀`. The witness is re-checked at each plotted
point and recorded as `integral_witness_in_band`. (The sharp question — the smallest achievable
`t*`, and whether some `δ < δ₀` is integrally infeasible — is `cert_integer_balance_floor`'s and
belongs to U18, not here. Nothing below `δ₀` is plotted.)

**Why the certificate does not need OA convergence.** Let `Φ_C(δ)` be the optimal value of the OA
master at cut set `C` (§5). Every tangent is a global overestimator of `log`, so
`Φ_C(δ') ≥ EG^bal(δ')` for **every** `δ'` and every `C`; and `Φ_C` is the value function of an LP
whose right-hand side is affine in `δ`, hence concave in `δ`. Therefore, with `σ_C(δ)` the
master's own aggregate band dual,

```
EG^bal(δ')  ≤  Φ_C(δ')  ≤  Φ_C(δ) + σ_C(δ)·(δ' − δ)          for every δ', every cut set C.
```

The one-solve bound is thus valid at **any** iteration of the cut loop, using the master's value
and the master's slope as a matched pair. The reported number uses the converged pair; the
weaker statement is what makes a stop-rule abort still a certificate rather than a data point.

## 5. How it is computed

### 5.1 Primary — LP outer approximation on HiGHS, cut pool carried across `δ`

Epigraph variables `t_i` and the assignment `x_{zi}`; master

```
max Σ_i t_i
s.t.  t_i − g_i/ĝ_i^{(r)}  ≤  log ĝ_i^{(r)} − 1          ∀i, ∀ cuts r        [tangent at ĝ^{(r)}]
      Σ_i x_{zi} = 1                                     ∀z
      Σ_z M_z x_{zi} ≤ (1+δ)T/k,  −Σ_z M_z x_{zi} ≤ −(1−δ)T/k               ∀i
      x ≥ 0,  t free
```

solved by `scipy.optimize.linprog(method="highs")`. Size: `nk + k ≈ 16,000` columns,
`n + 2k + k·|C|` rows.

* **Validity.** `log ĝ + (g − ĝ)/ĝ ≥ log g` for all `g, ĝ > 0`, so `Φ_C(δ) ≥ EG^bal(δ)` at every
  iteration. **This is the safety property the whole architecture rests on** and it is what
  `code-verify` tests (§7).
* **The matching lower bound.** The master's `x` is feasible for the true program, so
  `Σ_i log g_i(x)` is a valid *lower* bound. The pair `[primal, Φ_C]` is a bracket at every
  iteration; tier 1 is `Φ_C − primal ≤ 1e-8` nats.
* **The loop.** Seed one cut per agent at `ĝ = g(x ≡ 1/k) = u_i(Z)/k` — the Slater point of
  §2.10, so the seed is exact rather than heuristic. `ĝ > 0` at every iterate is guaranteed with
  an explicit constant by U9 **P5.3**, `g_i(X) ≥ λ(1−δ)T/k` — `63.113` at `δ = 0.0039` and
  `42.451` at `δ = 0.33`. The seed clears that floor by a factor of ~1.4 (`u_i(Z)/k ≈ 89–93`), so
  P5.3 enters as a runtime guard rather than as the seed itself. Then solve, add a cut at the
  incumbent `g`, repeat.
  **Scope (`CODEVERIFY_U8-band.md` row 1).** P5.3's floor is derived from the band's *lower* row,
  so the guarantee holds only where that row is present. `solve_band(delta=None)` drops it, and on
  that path an OA iterate can zero an agent — `code-verify` exhibited such an instance. The
  guarantee is therefore stated for `δ` finite; on the unconstrained path `ĝ > 0` is enforced by
  an explicit per-iterate check that raises. In this unit every `delta=None` solve is the gate on
  the real instance, where all 13 gains sit at ≈ 90 against a floor of `63.113`, so no published
  number depends on the distinction.
* **A final polish (U9 P5.4).** A single tangent per agent placed at `g*` makes the master
  **exact**, and that master's duals **are** the original program's `(p, μ^±)` — the accumulated
  pool's are only asymptotically so. One extra LP is therefore run after convergence on the cut
  set `{g_final}`, and adopted only if it does not loosen the bound, so the reported `(upper,
  s_min)` remain a matched pair drawn from one concave majorant.
* **Not finitely convergent (U9 P5.5).** The Duran–Grossmann / Fletcher–Leyffer finiteness
  theorems are about MINLPs, where finiteness comes from finitely many integer assignments; the
  continuous master here terminates only to `ε`. This costs the unit nothing: by P5.1 every
  master optimum is a valid upper bound at every iteration, so the 200-cut stop rule yields a
  certificate regardless, and the certified bracket `[Σ_i log g_i(X^r), MP(𝒞^r)]` is carried at
  every iteration.
* **Across `δ`.** The cut pool is valid at every `δ` — only the band right-hand side moves — so
  the pool is carried from one grid point to the next. That is the practical content of
  "warm-started" here: `scipy.optimize.linprog` exposes no basis, so the reuse is at the cut
  level, which is where the iterations are.
* **Duals.** `p` from `res.eqlin.marginals` on the supply rows; `μ^+`, `μ^-` from
  `res.ineqlin.marginals` on the two band families, sign-normalised to `≥ 0`. Bounds are
  `(0, None)` for `x` and `(None, None)` for `t`.
* **Stop rule, and never the word "converged" (`VERIFY_U9-bandthm` §10.C).** The pair
  `[Σ_i log g_i(X^r), MP(𝒞^r)]` is quoted as a **bracket at every iteration**, never as a
  convergence claim: by P5.1 both ends are valid whatever the loop did. If tier 1 is not reached
  in 200 cuts the bracket and the iterate are reported and the loop stops, with no tuning — and
  that outcome is expected rather than exceptional, since `math-verify`'s independent loop
  stalled at `1.8e-7` for 225 consecutive iterations. **This unit's loop does not stall there,
  and the reason is worth recording:** the stall floor is the LP's own primal feasibility
  tolerance — a cut violated by less than it is not seen as violated — so at the HiGHS default
  `1e-7` the bracket floors at `≈ 6.7e-8`, and the `1e-9` rung of the tolerance ladder clears
  tier 1 in 15–57 tangents.

### 5.2 Cross-check — SCIP with native `log`

The same program stated directly through `pyscipopt`'s expression graph
(`VigerskeGleixner2018`), at **two or three `δ` only**. Settings mirror
`td/solvers/scip_tree.py:1090-1125`: `limits/gap 0.0`, `limits/absgap 0.0`,
`misc/allowstrongdualreds False`, `misc/allowweakdualreds False`, `numerics/feastol`. Gains enter
as `g_i ≤ Σ_z u_i(z)x_{zi}` (`≤`, not `==` — trap 14 multi-aggregation) with a lower bound taken
from the OA incumbent rather than from `1e-9`, or the log's gradient destabilises the LP.
**Only `getDualbound()` is read**, never the primal incumbent. A `timelimit` or any non-optimal
stop is reported as **no bound** (trap 15), never as a bound. Agreement is required to `1e-6`; on
disagreement both are reported and the *smaller valid upper bound* stands.

### 5.3 What is not on the path

Anything conic (unavailable); proportional response (`eg.eg_solve` — it cannot take side
constraints, `MODEL_U1-cert` §8.2); ε-constraint MILP enumeration (the wrong coordinate); a
barrier point (does not warm-start, and the OA bracket already reaches tier 1).

## 6. The grid, and the N7 discrepancy

**Finding (recorded here, not resolved).** `DOMAIN_economic-theory` N7 and §2.9 write the grid as
`δ ∈ {0.0078, 0.02, 0.05, 0.10, 0.33}`, and `LENS_GROMOV` M8 writes the sandwich starting at
`EG^bal_{S₁₃}(0.0078)`. But `0.0078` is FRAME §6's **spread** `(max−min)/mean`, whereas `δ` in the
band is a **maximum deviation** `max_j |m_j − T/k|/(T/k)`; the two differ by up to a factor of 2.
`DOMAIN_optimization` §2.10 carries the arithmetic caveat explicitly, and FRAME §6 and this
unit's brief both give `δ₀ = 0.0039` on seed 3 (`0.0062` on seed 9). **The grid used here is**

```
δ ∈ {δ₀ = 0.0039, 0.02, 0.05, 0.10, 0.33}
```

with `δ₀` recomputed from the committed draw rather than taken on trust. A factor of two in `δ₀`
moves the D1′ verdict, so the discrepancy is reported and the max-deviation reading is used.
`EG^bal(δ)` bounds the delivered draw only for `δ ≥ δ₀`.

## 7. Deliverables, and the acceptance they answer

| # | number | flips |
|---|---|---|
| 1 | `EG^bal_{S₁₃}(δ₀)`, `p`, `μ^±`, `q`, support size vs `n + k − 1 + t` | D1′; whether `ν` may be read as "the" exchange rate |
| 2 | the one-solve concavity bound at `δ ∈ {0.02, 0.05, 0.10}` | **A1 lives or collapses-on-softness** |
| 3 | the grid `{δ₀, 0.02, 0.05, 0.10, 0.33}` and `δ*` | U13; concave-rising vs flat-then-jump |
| 4 | first-mover zips at `δ*` and their `M`-mass | U14; U4-disp's input |
| 5 | N8: reps with a binding band and the sign of `ν_i` at each `δ` | whether §2.8 collapses to CEEI (all `ν_i = 0`) |
| 6 | N9: `u_i(A_i) − u_i(Z)/k` per selected rep at each `δ` | whether balance and "do not starve anybody" conflict |

**First-movers (§2.12, corrected by U9 P2.5).** At the optimum
`supp(X*) ⊆ argmax_i ( u_i(z)/g*_i − ν_i M_z )`. Zips are ranked by

```
margin_z = max_i ( u_i(z)/g*_i − ν_i M_z ) − second-max_i ( u_i(z)/g*_i − ν_i M_z )
```

reported both absolutely (in the units of `p_z`) and relative to `p_z`; the near-ties are the
units whose owner flips first as `δ` moves, read off **one** solve in `O(nk)`, and their `M`-mass
is the displacement handed to U4-disp. The list is void as an interpretation if the degeneracy
check of §2 fails.

**The sandwich (§3 of the domain plan).**

```
59.9375 = V(delivered) ≤ EG^bal(δ₀) ≤ EG^bal(0.02) ≤ … ≤ EG^bal(0.33) ≐ EG_{S₁₃} = 60.6974
```

Monotonicity and concavity on the grid are **checked and reported as findings if violated**, not
repaired. Note `EG^bal(0.33) = EG_{S₁₃}` only if the band is slack at the unconstrained optimum;
the `M`-max-deviation at that optimum is measured and reported beside it.

**Marking the MNW point (trap 2).** Every rendering of the curve carries (a) the delivered MNW
draw at `(δ₀, 59.9375)` and (b) the unconstrained endpoint `(0.33, 60.6974)` with its `≥ 50 %`
`M`-spread annotated. The objective is `Σ log g` at every point; no point is produced by
minimising a spread. A rendering without (a) has walked into trap 2 by the back door.

**Provenance (acceptance 5).** Every output carries run id, instance abspath + sha256, draw dir +
sha256, `θ`, `λ`, `filler_capture`, and `scipy` / `numpy` / `highspy` / `pyscipopt` versions
(`highspy` has no `__version__`; `importlib.metadata.version("highspy")`). `json.dump(...,
indent=2, sort_keys=True)` makes re-runs byte-identical modulo the `written` timestamp. The σ₀
consistency assertion of `tools/measure/premium.py:411-417` is copied: the recomputed `V` must
equal `metrics.json`'s `winner.stage2_value` to `1e-9`, else raise.

**Tests (acceptance 6).** On the `MODEL_U7-meas` §4 toy (three reps A/B/C, four zips,
`M = [20,15,15,20]`) with `k = 2` and with `k = 3`: `EG^bal` at `δ = 0` and at `δ` large against a
brute-force grid over fractional splits and against the unconstrained EG; and the OA bound is
**never below** the true value at any iteration. No test reads a gitignored input.

## 8. What this unit cannot say

Anything about a different roster (that is §2.14 / U16); anything about misreporting; anything
about error in the common measure `M` — every `p_z` and every `ν_i` is a functional of `M`, so a
regional bias in the sizing biases the exchange rate in the same direction and is undetectable
from inside (`VERIFY_U1-cert` §6). And `ν` is a **marginal rate of transformation**, a fact about
the feasible set; the sponsor's **marginal rate of substitution** has never been elicited and the
two coincide only at the sponsor's own optimum (`DOMAIN_economic-theory` §2.9). A computed shadow
price is not a business decision.

The instance's `u_i(z)/M_z` rounding — 69 zips exceed `1` by `≤ 4.2e-7` at `filler="theta"` — is
recorded, not repaired; if it moves a bound, by how much is reported.

---

## 9. Results

Run 2026-09-04 on the committed seed-3 draw. Machine-readable form:
`battery/results/u8_band_20260904/draw_k13_20260901.json` (gitignored); curve:
`figures/u8_band/frontier.png` (tracked). `instance_sha256` `cf7d66c09b28be1e…`, `draw_sha256`
`6614e6651cfa758a…`, θ = 0.40, λ = 0.30, `filler_capture = "theta"`; scipy 1.18.1, numpy 2.5.2,
highspy 1.15.1, pyscipopt 6.2.1, matplotlib 3.11.1. **Two full re-runs are byte-identical apart
from `written` and `wall_seconds`** (acceptance 5).

### 9.0 The gate, and `δ₀`

`V(delivered) = 59.937469798433`, equal to `metrics.json`'s `winner.stage2_value` to the last
digit. The unconstrained fibre came back as `EG_{S₁₃} ∈ [60.697415611321, 60.697415620014]`,
bracket `8.69e-9` in 23 tangents — **`6.11e-9` from the published `60.6974156139`**, so the
unmasked utility convention is confirmed and the gate passes.

```
δ₀ = 0.0039460106   (max deviation)          spread = 0.0078126145
spread / δ₀ = 1.9799
```

The `M`-max-deviation at the *unconstrained* optimum is `0.3224` with a spread of `0.5391`, so
`0.33 > 0.3224`: the band is slack at `δ = 0.33` and `EG^bal(0.33) = EG_{S₁₃}` exactly, which is
what closes the sandwich. It also confirms the "≥ 50 % spread" the trap-2 annotation carries.

### 9.1 The frontier (numbers 1 and 3)

| `δ` | `EG^bal` bracket `[primal, upper]` | width | tangents | `s_min` | `−V` | `t` | splits (cap) |
|---|---|---|---|---|---|---|---|
| `0.0039460106` | `[60.6204408013, 60.6204408042]` | `2.81e-9` | 15 | `0.5609` | `0.682971` | 12 | 19 (24) |
| `0.02` | `[60.6288653530, 60.6288653560]` | `2.98e-9` | 23 | `0.4942` | `0.691396` | 11 | 20 (23) |
| `0.05` | `[60.6416012810, 60.6416012849]` | `3.84e-9` | 35 | `0.3710` | `0.704131` | 10 | 16 (22) |
| `0.10` | `[60.6577253430, 60.6577253509]` | `7.87e-9` | 44 | `0.2663` | `0.720256` | 8 | 16 (20) |
| `0.33` | `[60.6974156089, 60.6974156171]` | `8.19e-9` | 57 | `0.0000` | `0.759946` | 0 | 10 (12) |

Every bracket is **tier 1** (`≤ 1e-8`). `s_min = s_raw` to `1e-9` at every `δ`, as complementary
slackness requires away from `δ = 0`. **The sandwich holds**:

```
59.9374697984  ≤  60.6204408  ≤  60.6288654  ≤  60.6416013  ≤  60.6577253  ≤  60.6974156  ≤  60.8025
V(delivered)        δ₀             0.02           0.05           0.10          0.33 = EG_S₁₃    (★) at P₁₃
```

monotone and concave on the grid with **zero** violations. Every point is a genuine vertex of the
optimal face (`rank = |supp|` at all five), cleaning at `1e-6` moved `g` by at most `1.3e-11` and
no mass out of band, cleaned and raw split counts are **identical** (no phantom splits), and every
count sits under `k − 1 + t` and under `2k − 1 = 25`. The delivered draw witnesses a band-feasible
*integral* coverage at all five points, so no bound here is quantified over an empty set.

**SCIP cross-check**, `limits/gap = limits/absgap = 0.0`, dual reductions off, `getDualbound()`
only, both stops `optimal`:

| `δ` | SCIP dual bound | `\|OA − SCIP\|` | wall |
|---|---|---|---|
| `0.02` | `60.6288653576` | `1.58e-9` | 853 s |
| `0.33` | `60.6974156182` | `1.10e-9` | 4 s |

Both inside `1e-6`. SCIP's bound sits marginally *above* the OA's at both points; both are valid
upper bounds and the smaller — the OA's — is the one reported.

### 9.2 D1′ (number 2) — **NOT SOFT**

From the single solve at `δ₀` (`EG^bal(δ₀) = 60.6204408042`, `s_min = 0.560876`):

| `δ` | one-solve bound | `bound − V` | verdict | direct `EG^bal(δ)` | tangent slack |
|---|---|---|---|---|---|
| `0.02` | `60.62944510` | `0.69197530` | **not soft** | `60.62886535` | `+5.80e-4` |
| `0.05` | `60.64627138` | `0.70880158` | **not soft** | `60.64160128` | `+4.67e-3` |
| `0.10` | `60.67431517` | `0.73684537` | **not soft** | `60.65772534` | `+1.66e-2` |

The tangent slack is positive at all three, so `s_min` is a valid supergradient and §10.A's guard
passes. The floor is `5e-3` nats and the smallest gap exceeds it by **138×**.

**The verdict does not turn on the slope at all.** `EG^bal(δ₀) − V = 0.682971` nats already, so
the intercept alone refuses softness and no non-negative slope can rescue it. This is worth
stating because the calibration circulated with U9's follow-up — "a slope below
`47.20 / 16.48 / 7.91 / 2.33` certifies softness at `0.02 / 0.05 / 0.10 / 0.33`" — is computed
against an intercept of `V`, i.e. it is `(EG_{S₁₃} − V)/(δ − δ₀) = 0.7599/(δ − δ₀)`. D1′'s
intercept is `EG^bal(δ₀)`, not `V`. Read correctly, `s_min(δ₀) = 0.5609` being far *below* those
figures says only that the curve is flat — which is exactly why softness fails: the whole gap is
already present at `δ₀` and the band buys back only `0.077` nats of it across the entire range.

**A1 continues.** The premium survives the band; the track does not collapse on softness.

### 9.3 `δ*` (number 3, second half)

`δ* ≤ δ₀ = 0.0039`. `EG^bal(δ) − V` is `0.682971` nats at the left endpoint, already `137×` the
tier-2 floor, so `min{δ : EG^bal(δ) − V > 5e-3}` is attained at or below `δ₀` and the bisection
runs zero solves. Neither of the brief's two anticipated answers ("three digits" / "none in
`[δ₀, 0.33]`") applies; this is the third case and it is the strongest one.

### 9.4 N8 — the band duals (number 5)

`t` = tight band rows; `gauge pinned` at every `δ` (at least one agent strictly slack on both
sides forces its `ν_i = 0`, so no `p_z → p_z + cM_z` shift survives).

| `δ` | `t` | `ν_i > 0` (upper binds) | `ν_i < 0` (lower binds) | `ν_i = 0` | `q` range |
|---|---|---|---|---|---|
| `0.0039` | 12 | R0010, R0014, R0017, R0018, R0013, R0005 | R0001, R0000, R0003, R0006, R0007, R0002 | R0008 | `[1.63e-5, 0.2210]` |
| `0.02` | 11 | — | R0001, R0000, R0003, R0006, R0007, R0002 | 7 reps | `[1.62e-5, 0.2198]` |
| `0.05` | 10 | — | R0001, R0000, R0003, R0002 | 9 reps | `[1.60e-5, 0.2187]` |
| `0.10` | 8 | — | R0001, R0000, R0002 | 10 reps | `[1.60e-5, 0.2202]` |
| `0.33` | 0 | — | — | all 13 | `[1.74e-5, 0.2142]` |

**§2.8 does not collapse to CEEI at the delivered balance.** At `δ₀` twelve of thirteen bands are
tight and the two directions are split six-and-six: six reps would buy more opportunity and are
prevented, six are being force-fed opportunity they do not want. Prices are genuinely
personalised there and Varian's envy-freeness argument is genuinely lost. From `δ = 0.02` outward
**only lower bands bind** — the upper band stops mattering almost immediately, and what the band
is really doing at every plausible sponsor width is *forcing opportunity onto three to six reps
who do not want it*. At `δ = 0.33` every `ν_i = 0`, price anonymity is restored and the section
reduces to §2.2. That is the good case §2.8 asks to be detected rather than assumed, and it is
detected — but only at a band width four times wider than anything a sponsor has named.

### 9.5 N9 — proportionality (number 6), and a prediction that does not hold

Gaps `u_i(A_i) − u_i(Z)/k` in descaled utility units (`u_i(Z)/k ≈ 88.7–92.7`):

| | min gap | reps below proportionality |
|---|---|---|
| **delivered draw** | `−7.1351` | **4 of 13** — R0010 `−7.14`, R0013 `−4.70`, R0017 `−2.33`, R0018 `−1.73` |
| `EG^bal(δ₀)` | `+9.0899` | 0 |
| `EG^bal(0.02)` | `+9.2644` | 0 |
| `EG^bal(0.05)` | `+10.6380` | 0 |
| `EG^bal(0.10)` | `+11.6582` | 0 |
| `EG^bal(0.33)` | `+13.3569` | 0 |

`DOMAIN_economic-theory` §2.8 predicts proportionality is "**the first casualty**" of the band.
**On this instance it is not.** No rep falls below proportionality at any band width on the
frontier, including the tightest. What does starve four reps is the **delivered integral draw**,
which sits `7.1` utility units below proportional for R0010 — so FRAME §3's "do not starve
anybody" is violated by the map the programme has committed to, and *not* by the balance
requirement. The mechanism §2.8 names is nevertheless visible and pointed in the predicted
direction: the minimum gap falls monotonically as the band tightens, `+13.36 → +9.09` from
`δ = 0.33` to `δ₀`, so balance does erode proportionality margins by about 32 % — it just does not
exhaust them at `k = 13`. **The two business goals do not conflict at the fractional optimum;
they conflict at the delivered map.** That is a finding for U18/U10, not for the sponsor
conversation about `δ`.

### 9.6 First movers (number 4) — and why the corrected rule changes the answer

At `δ₀`, ranked by U9 P2.5's margin on `u_i(z)/g*_i − ν_i M_z`:

- **75 zips are exact MBB ties** (`margin = 0` to `1e-12`), carrying `79.65` of `M` = **2.90 % of
  `T`**. The top 25 by mass-free rank carry `22.85` = `0.83 %` of `T`. Every one of the ten
  smallest-margin zips is an `R0001 ↔ R0000` tie — the two reps whose lower bands bind hardest
  (`ν = −4.54e-4` and `−1.16e-3`).
- The support is `1248` against an expected `1253`, so **the dual is degenerate** and, per the
  stop rule, `ν` is reported as **one** dual optimum and no first-mover list is named from it
  alone. The tie *set* is the defensible object; the ordering within it is not.
- The corrected rule matters here, not just in principle: under §2.12's published ratio form the
  top of the list was a completely different set of zips (93901, 90631, 16365, …) with strictly
  positive margins and `3.47 %` of `T`. The ratio form's answer was an artifact.

### 9.7 Findings, in the order they would change something

1. **The N7 / M8 grid discrepancy is real and is a factor of `1.9799`.** `δ₀ = 0.0039460106` is
   the max deviation; `0.0078126145` is the spread. Independently confirmed by U9. The published
   inequality at `0.0078` is true but mislabelled. Grid on `δ₀`.
2. **`DOMAIN_optimization` §2.12's good-side rule is false as written** and its first-mover list
   is an artifact — see §2's correction box and §9.6. Corrected here; the source document still
   carries the wrong form.
3. **§2.8's "proportionality is the first casualty" does not hold at `k = 13`** (§9.5). The
   starvation is the delivered map's, not the band's.
4. **The OA stall floor is the LP feasibility tolerance, not the method.** At the HiGHS default
   `1e-7` the bracket floors at `≈ 6.7e-8` and 200 further tangents buy nothing; at the `1e-9`
   rung tier 1 is reached in 15–57. This is the mechanism behind `math-verify`'s 225-iteration
   stall at `1.8e-7`, and it is a tolerance fact rather than a Kelley-instability one.
5. **Degeneracy is present at every reported `δ`** (support `1240`–`1249` against expected
   `1241`–`1253`), so every `ν` in §9.4 is one dual optimum. The *gauge* is pinned at every `δ`,
   so `p` and `ν` are at least not free to slide; the residual non-uniqueness is combinatorial,
   not gauge.
6. **`s_min` was not minimised over the exact dual-optimal set.** §10.A's LP was not run — the
   proportionate substitute is the mandatory guard, which passes with slack `+5.8e-4` to
   `+1.7e-2` nats at all three sponsor widths, so the reported `s_min` **is** a valid
   supergradient there. Residual exposure: `s_min` could in principle be smaller than reported,
   which would only *tighten* D1′ and cannot change a "not soft" verdict. Recorded, not tuned.
7. **The `u_i(z)/M_z` rounding (69 zips over `1` by `≤ 4.2e-7`) does not affect any bound here.**
   No number in this unit uses the headroom hypothesis — that enters only the closed-form outer
   bound P1c, which this unit does not quote. The gate reproduced `EG_{S₁₃}` to `6.11e-9` with
   the rounding in place. Not repaired.
8. **SCIP prints `Cannot set feasibility tolerance to small value 1e-12 without GMP - using
   1e-10`** on every solve. `numerics/feastol` was set to `1e-9`; the message concerns an
   internally derived tolerance. Both cross-checks stopped `optimal` and agreed to `1.6e-9`, so
   it is recorded, not acted on.
