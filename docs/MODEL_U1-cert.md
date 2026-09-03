# Model — unit U1-cert — does the Eisenberg–Gale dual subsume the four existing certificates?

**Date:** 2026-09-03 · **Framework:** 0.1-dev · **Track:** A1 (`docs/APPROACHES.md` §A1), run on
`wt/A1` · **Unit:** `docs/units/U1-cert.md` ·
**Reads:** `docs/DOMAIN_optimization.md` §2.2, §3, §5, §8 Q4; `docs/DOMAIN_economic-theory.md`
§2.1, §2.2; `docs/LENS_GROTHENDIECK.md` §2, §4, "The general case, stated", descent 1–3;
`docs/LENS_GROMOV.md` Move 3; `docs/MODEL.md`; `docs/FRAME.md` §5, §6, §9, §10 Q3;
`docs/REVIEW_GROMOV.md` R3; `docs/LIT_economic-theory.md` §0.5, §1, §2; read-only
`td/solvers/cert_draw.py`, `td/solvers/centers.py::power_weights`, `td/channel.py`,
`td/model.py`, `td/instance.py`; `instance_descaled.json.gz`;
`battery/results/draw_k13_20260901/` ·
**Owns:** this file, `docs/artifacts/U1-cert/**` ·
**Not read (does not exist):** `docs/LIT_optimization.md` — U0-lit has not run, so the split-unit
count is proved here and marked *pending citation*.

**Headline.** Three of the four certificates collapse; the fourth does not, and its resistance is
informative rather than a defect. Measured on the real instance, the fibre bound at the delivered
roster is `EG_{S₁₃} = 60.697416` against a delivered `V = 59.937470` — a **0.7599-nat** optimality
gap on the objective the business signs, where the analytic balance ceiling gives only **9.6491**
nats. The EG bound is decision-relevant against FRAME §6's ~3.7-nat premium; the ceiling is not.

---

## 1. Setup (symbol table)

Every symbol is defined once here and used with no other meaning.

| symbol | meaning | units / reference value |
|---|---|---|
| `Z` | the footprint: zips carrying sales | `n = |Z| = 1,229` (FRAME §6) |
| `R` | wholesalers | `m = |R| = 111` |
| `k` | territories | `13` |
| `M_z` | opportunity at `z` | descaled `m_rel`; `T := M(Z) = 2745.611187` |
| `S_i(z)` | rep `i`'s booked production at `z` | descaled; `T_z := Σ_j S_j(z)` |
| `S_free(z)` | vacancy ("filler") book at `z` | descaled |
| `λ` | opportunity weight | `0.30` (`td/model.py`) |
| `θ` | capture rate against a departing book | `0.40` |
| `c1, c2, c_free` | `1−λ`, `θ(1−λ)`, filler rate | `0.70`, `0.28`, `c2` under `filler_capture="theta"` |
| `u_i(z)` | rep `i`'s value of `z` | `c1 S_i + c2(T_z−S_i) + c_free S_free + λ M_z` |
| `w` | premium coefficient `c1 − c2 = (1−λ)(1−θ)` | `0.42` |
| `ν_i` | peak intensity `max_z u_i(z)/M_z` | `≤ 1` iff headroom holds |
| `π = (A_1,…,A_k)` | ordered `k`-partition of `Z` | |
| `σ : [k] ↪ R` | injection of territories into reps | |
| `(π,σ)` | a **coverage** (Groth §3) | |
| `S = im σ` | the **staff set**, `|S| = k` | delivered `S₁₃` = the 13 reps in `draw_k13_20260901` |
| `C(π)` | geometric penalty on the partition (perimeter, `td/model.py::perimeter`) | integer count |
| `ρ` | penalty weight | `0` in the delivered pipeline (stage 2 has no `ρ`) |
| `V(π,σ)` | composite value `Σ_j log u_{σ(j)}(A_j) − ρ C(π)` | nats; delivered `59.937470` |
| `W(π)` | stage-1 surrogate `Σ_j log M(A_j)` | nats; delivered `69.586488` |
| `X ∈ [0,1]^{Z×S}` | fractional assignment, `Σ_{i∈S} x_{zi} = 1` | |
| `g_i(X)` | `Σ_z u_i(z) x_{zi}` | descaled gain units |
| `Ĉ(X)` | a convex extension of `C` to fractional `X` | `C_TV(X) = ½ Σ_{(u,v)∈E} Σ_i |x_{ui}−x_{vi}|` |
| `EG_S` | `max_X Σ_{i∈S} log g_i(X) − ρ Ĉ(X)` — the **fibre** | nats |
| `p_z` | dual price on zip `z` (multiplier of `Σ_i x_{zi} = 1`) | |
| `D(p)` | `Σ_z p_z − k + Σ_{i∈S} log max_z (u_i(z)/p_z)` | the Lagrangian dual, `ρ=0` |
| `m_j` | district mass `M(A_j)` (or `Σ_z M_z x_{zj}` fractionally) | target `T/k = 211.2009` |
| `β_j, ω_j` | mass-row duals / power-diagram weights | squared-distance units |
| `F` | the set of **split units** at a vertex optimum | `|F| = 10` measured |
| `t*` | `min_π max_j |m_j − T/k|` — certificate 2's object | absolute, in `M` units |

**Two conventions that must not be mixed.** `td/model.py::utilities` zeroes `u_i(z)` for
non-candidates; `td/channel.py::gain_matrix` does not (staffing is unconstrained by legacy
candidacy — that is the point of drawing first). Everything in this unit uses the **unmasked**
convention, because the integral coverages P1 bounds are exactly the ones `channel.stage2` scores.
Under the masked convention `g_i` can be `0` and the fibre program is a different object.

**Estimand / decision.** Not a decision: this unit produces a *certificate*. The estimand is the
optimality gap `V̄ − V(delivered)` in nats, with `V̄` the tightest available upper bound, plus a
statement of which existing certificates are redundant.

---

## 2. Propositions

> **P1 (fibrewise relaxation bound).** Fix a staff set `S ⊆ R`, `|S| = k`. Let `Ĉ` be any
> extension of `C` to fractional assignments with `Ĉ(X_π) ≤ C(π)` at every integral `X_π`
> **(H3)**. Then for every integral coverage `(π,σ)` with `im σ = S`,
> `V(π,σ) ≤ EG_S`, with the convention `log 0 = −∞`. This holds at **every** `ρ ≥ 0`.
> The bound needs neither concavity nor strict positivity of any `g_i`; concavity is needed only
> to *compute* `EG_S` and to read its duals. `[proved]`

> **P1a (H3 is not decoration).** There exist instances and extensions `Ĉ` with
> `Ĉ(X_π) > C(π)` for which `max V > EG_S` by an arbitrary margin; so P1 at `ρ > 0` is a
> statement about a *named* extension, not about "adding compactness". `C_TV` satisfies H3 with
> equality. `[proved; counterexample in docs/artifacts/U1-cert/check_p1_p3.py]`

> **P1b (finiteness).** If `min_z M_z > 0` and `λ > 0` then `u_i(z) ≥ λ M_z > 0` for every `i,z`
> and `EG_S ∈ ℝ` for every `S`. On the instance `min_z M_z = 1.80577e-3 > 0`, so no starvation
> guard is needed and `DOMAIN_optimization.md` §2.2's ill-conditioning failure mode does not
> arise at `ρ = 0`. `[proved; hypothesis verified on the instance]`

> **P1c (the closed-form outer bound).** If the headroom condition holds in the strong form
> `u_i(z) ≤ M_z` for all `i,z`, then for **every** staff set `S`,
> `EG_S ≤ k log(M(Z)/k)` — the analytic balance ceiling — and the same bound holds for the
> cardinality-relaxed perspective relaxation `EG_R`. Hence
> `V(delivered) ≤ max_S EG_S ≤ EG_R ≤ k log(T/k)`, and **the outer term of
> `DOMAIN_optimization.md` §3's sandwich is available in closed form with no barrier solve.**
> `[proved]`

> **P2 (the collapse — three of four).** Of the four certificates in `td/solvers/cert_draw.py`:
>
> - **P2.1 `cert_balance_ceiling` is a degeneration of `EG_S`'s dual.** At `u_i ≡ λM`, `ρ = 0`,
>   the fibre is staff-independent, `EG_S = k log(λT/k)`, and the dual `D(p)` attains it at the
>   explicit price vector `p_z = (k/T)·M_z`. At `λ = 1` this is exactly the number
>   `cert_balance_ceiling` returns as `ceiling_nash`. The certificate is therefore
>   *EG's dual evaluated at prices proportional to opportunity*, checkable in `O(n)`. `[proved]`
> - **P2.2 `cert_integer_balance_floor` is NOT a degeneration or restriction of the dual.**
>   Its LP relaxation has optimum `t = 0` (split every unit fractionally), so it carries no dual
>   bound at all; its entire content is primal-constructive. What it measures is the **slack in
>   P1** at `u_i ≡ λM` — the achievability half of the same sandwich — and the conversion to
>   nats is `k log(T/k) − max_π Σ_j log m_j ≤ k ε²/(2(1−ε)²)` with `ε = t*/(T/k)`.
>   `[proved]` — **this is a partial refutation of `DOMAIN_optimization.md` §3's load-bearing
>   claim, stated in full in §6 below.**
> - **P2.3 `cert_assignment_at_centers` is a restriction, by a named triple specialisation.**
>   `u_i ≡ λM` (`τ = 0`); `ρ > 0` with the linear compactness penalty `Σ_z M_z d²(z,c_j)x_{zj}`;
>   centers pinned; the log-balance term traded for an ε-constraint band `|m_j − T/k| ≤ δ`; and
>   integrality reimposed. It bounds the *compactness component* of the fibre, not its value.
>   `[proved]`
> - **P2.4 `cert_power_diagram` is the KKT system of the same `τ = 0`, `ρ > 0` fibre.**
>   Every optimum `X*` of that fibre is supported on the power (Laguerre) diagram of the pinned
>   centers with weights `ω_j = 1/(ρ m*_j)`, and `ω` is a **dual-optimal** weight vector of the
>   transportation LP `centers.power_weights` solves at targets `m*`. The duals HiGHS returns
>   satisfy the EG stationarity identity `ρ β_j − 1/m*_j = const` **iff that LP is
>   nondegenerate** (support size `= n + k − 1`); at a degenerate optimum HiGHS returns a
>   different, equally valid, dual optimum which is *not* the EG multiplier. `[proved; the
>   nondegeneracy caveat is new and is a caveat on an existing certificate]`

> **P3a (the split-unit count, and where `k−1` comes from).** The set of `EG_S` optima at `ρ = 0`
> is exactly `{X feasible : g(X) = g*}` with `g*` unique. Its constraint matrix has rank
> `n + k` in general and `n + k − 1` **exactly when the `u_i` are mutually proportional**. Hence a
> vertex optimum splits at most `k` units in general and at most `k − 1` in the common-measure
> (`τ = 0`) case. **The lens's `[standard]` `≤ |S| − 1` is a `τ = 0` privilege**; the honest
> heterogeneous statement is `≤ k`. `[proved here — pending citation, U0-lit has not run]`

> **P3b (the gap in value, not count).** Let `X*` be a vertex optimum with split set `F` and
> `L_i = Σ_{z∈F} u_i(z) x*_{zi}`. Rounding each split unit to one of its buyers gives an integral
> coverage with `g_i ≥ g*_i − L_i`, hence
> `0 ≤ EG_S − max_integral V ≤ −Σ_{i∈S} log(1 − L_i/g*_i) ≤ −log(1 − M(F)/min_i g*_i)`,
> the last step using `Σ_i L_i ≤ Σ_{z∈F} max_i u_i(z) ≤ M(F)` under headroom and the convexity
> of `−log(1−·)`. `[proved]`

> **P3c (the a-priori form of P3b is vacuous on this instance).** Bounding `M(F)` a priori by the
> `k−1 = 12` largest zips gives `M(F) ≤ 249.392` (9.083% of `T`) against `min_i g*_i = 103.617`,
> so `M(F)/g_min = 2.407 > 1` and the bound is `+∞`. **The `≤ k−1` count is therefore not
> quotable without the split masses.** With the *measured* `F` (10 units, `M(F) = 66.168`,
> 2.410% of `T`) the bound is `1.018` nats; with the per-agent losses it is `0.245` nats; the
> gap actually realised is `5.131e-4` nats. `[measured]`

> **P4 (what the fibre bound says about the instance).** At the delivered roster `S₁₃`,
> `EG_{S₁₃} = 60.697416` (certified bracket width `1.3e-13` nats), so no coverage staffed by
> those 13 reps is worth more than `0.7599` nats above the delivered draw — and rounding the EG
> vertex realises `0.7594` of it constructively. But the rounded coverage has an `M`-spread of
> **54.21%** against the delivered `0.781%`, so essentially the whole gap is bought by abandoning
> the balance FRAME §9 records as settled. `[measured]`

---

## 3. Proofs and sketches

### P1 — the relaxation bound

Let `(π,σ)` be integral with `im σ = S`. Define `X_π ∈ {0,1}^{Z×S}` by `x_{z,σ(j)} = 1` for
`z ∈ A_j`. Since `π` partitions `Z` and `σ` is injective, `Σ_{i∈S} x_{zi} = 1` for every `z`, so
`X_π` is feasible for the fibre program. Its gains are `g_i(X_π) = Σ_{z ∈ σ^{-1}(i)} u_i(z) =
u_{σ^{-1}(i)}(A_{σ^{-1}(i)})`, so

```
Σ_{i∈S} log g_i(X_π)  =  Σ_j log u_{σ(j)}(A_j).
```

Under H3, `−ρ Ĉ(X_π) ≥ −ρ C(π)`. Hence the fibre objective at `X_π` is `≥ V(π,σ)`, and since
`EG_S` is the supremum of that objective over a set containing `X_π`, `V(π,σ) ≤ EG_S`. ∎

Three remarks the acceptance criterion asks for explicitly.

1. **`ρ > 0` does not break the bound**, unlike the fairness reading. `DOMAIN_economic-theory.md`
   §2.1 failure mode (i) is correct that at `ρ > 0` the objective is no longer Nash welfare and
   the Caragiannis EF1/PO characterisation lapses. That is a statement about *axioms*, which are
   properties of the maximiser. P1 is a statement about *feasibility*, which is indifferent to
   what the objective means. The only thing `ρ > 0` costs is H3.
2. **H3 is the whole content at `ρ > 0`.** `C_TV` is convex and *exactly* reproduces
   `td/model.py::perimeter` on integral `X` (an edge with a shared owner contributes `0`, an edge
   with different owners contributes `½·2 = 1`), so it satisfies H3 with equality. The linear
   compactness cost `Σ_z M_z d²(z,c_j) x_{zj}` used by `centers.assign` likewise. An extension
   that over-estimates on integral points breaks the bound; P1a exhibits this by arithmetic:
   with `Ĉ = C_TV + c`, `EG_ρ(Ĉ) ≤ EG_0 − ρc` because `C_TV ≥ 0`, and `EG_0` is bracketed above by
   the certified dual, so choosing `c = (D(p) − max_π V_ρ + 1)/ρ` forces a violation of at least
   one nat with no solver in the trusted path.
3. **`ρ = 0` is the operative case here.** `td/channel.py::gain_matrix` carries no `ρ` term
   (confirmed at `td/channel.py:281-284`), so the delivered `V` is the `ρ = 0` object and every
   number in §4 is at `ρ = 0`.

**Stop-rule check.** P1 does *not* require strict positivity of every `g_i` and does *not*
require `ρ = 0`. It requires H3, which is a property of a modelling choice this unit controls, not
of the instance. P1b verifies the one instance-dependent hypothesis (`min_z M_z > 0`) directly.
No hypothesis is assumed of the instance without checking it.

### P1c — the ceiling as the closed-form outer term

Headroom in the form used by `td/model.py::headroom_violations` with `filler_capture="theta"`
gives `u_i(z) = (1−λ)[S_i + θ(T_z + S_free − S_i)] + λM_z ≤ (1−λ)M_z + λM_z = M_z`. Therefore for
any feasible `X`, `g_i(X) ≤ Σ_z M_z x_{zi} =: m_i(X)`, with `Σ_i m_i(X) = T`. By Jensen,
`Σ_{i∈S} log g_i ≤ Σ_i log m_i ≤ k log(T/k)`.

For the cardinality-relaxed base (`DOMAIN_optimization.md` §2.1's perspective form), the objective
is `Σ_i y_i log(g_i/y_i)` with `Σ_i y_i = k`, `y ∈ [0,1]^R`. Writing `g_i = y_i c_i` and applying
Jensen with weights `y_i/k`: `Σ_i y_i log c_i ≤ k log(Σ_i y_i c_i / k) = k log(Σ_i g_i/k) ≤
k log(T/k)`. ∎

**Consequence.** The ceiling is not merely a bound on the surrogate `W`; under headroom it bounds
the composite `V` too. It is therefore *already* the outer term of the sandwich, and §5 #7's
barrier solve of `EG_R` can only tighten a bound that is available for free.

**Where this breaks.** `filler_capture` is an open FRAME §9 decision. At `"full"` (`c_free = c1`,
`docs/MODEL.md` §6.7's *recommended* option) the measured `max_{i,z} u_i(z)/M_z = 1.294899 > 1`
and headroom in the strong form fails; the corrected bound is
`EG_S ≤ k log(T/k) + Σ_{i∈S} log ν_i`, and the correction is up to `+3.360` nats — the same order
as the premium term the certificate exists to bound. **P1c is conditional on a business decision
that is open.**

### P2.1 — the ceiling is EG's dual at prices proportional to opportunity

The Lagrangian dual of the `ρ = 0` fibre on the supply rows is derived once, in
`docs/artifacts/U1-cert/eg.py`'s module docstring:
`D(p) = Σ_z p_z − k + Σ_{i∈S} log max_z(u_i(z)/p_z)`, valid as an upper bound for every `p > 0`
(weak duality; each agent's inner maximisation is `max_{s≥0} log(r_i s) − s = log r_i − 1`).

At `u_i ≡ λM` take `p_z = (k/T)M_z`. Then `Σ_z p_z = k` and `max_z u_i(z)/p_z = λT/k` for every
`i`, so `D(p) = k − k + k log(λT/k) = k log(λT/k)`. It is attained: any `X` with
`Σ_z M_z x_{zi} = T/k` for all `i` gives `g_i = λT/k`, so the primal reaches the same value. At
`λ = 1` this is `cert_balance_ceiling`'s `ceiling_nash`. ∎

Two things this buys that the Jensen argument does not. First, the ceiling acquires a
*certificate object* — a price vector — which is what `DOMAIN_optimization.md` §2.4 needs and what
`LENS_GROTHENDIECK` descent 7 asks for. Second, the same dual at the same prices, evaluated on the
real `u`, gives `EG_S ≤ k log(T/k) + Σ_i log ν_i` — the heterogeneous generalisation of the
ceiling, which is P1c's corrected form.

### P2.2 — the integer balance floor does not collapse, and why that is the useful answer

`cert_integer_balance_floor` solves `min t s.t. |Σ_z M_z x_{zj} − T/k| ≤ t, Σ_j x_{zj} = 1,
x ∈ {0,1}`. Its LP relaxation has optimum `t = 0` — set `x_{zj} = 1/k` for all `z,j` — so **no
dual of that model bounds anything**; the certificate's docstring says as much
(`td/solvers/cert_draw.py:340-357`: "the root bound is vacuous", "the primal side therefore does
not go through the MILP", measured `0` nodes and no incumbent in 300 s at `n=1,223, k=13`).
A certificate whose LP dual is identically zero cannot be a degeneration of a dual that is not.

What it *is*: the achievability half of P1's sandwich at `τ = 0`. P1 says `EG_S` bounds every
integral coverage from above; at `u_i ≡ λM`, `EG_S` equals the ceiling and is generally not
attained integrally, and `t*` is exactly the residual imbalance that indivisibility forces. The
conversion into nats is one line: with `δ_j = (m_j − T/k)/(T/k)` and `Σ_j δ_j = 0`,
`−log(1+δ) ≤ −δ + δ²/(2(1−ε)²)` for `|δ| ≤ ε`, so summing over the partition attaining `t*`,

```
k log(T/k) − max_π Σ_j log m_j  ≤  Σ_j δ_j² / (2(1−ε)²)  ≤  k ε² / (2(1−ε)²),   ε = t*/(T/k).
```

So the four certificates sit on **two sides of one duality gap**, not on one: 1, 3 and 4 are dual
(they bound value or cost from the outside); 2 is primal (it says how much of the gap was ever
reachable). That is a *better* organising statement than "five collapse into one", and it is not
the statement `DOMAIN_optimization.md` §3 asked to be verified.

### P2.3 — assignment at pinned centers is a restriction

Take the `τ = 0` fibre with the linear compactness penalty at pinned centers `c_j`. It is a
biobjective problem in `(Σ_j log m_j, cost)`. `cert_assignment_at_centers` is its ε-constraint
form (**Boland2015**, `DOMAIN_optimization.md` §2.5): minimise `cost` subject to
`|m_j − T/k| ≤ δ`, with `δ` defaulting to the draw's own max deviation so the draw is feasible for
its own test. Integrality is then reimposed. Two specialisations at once — `τ = 0`, and the log
term traded for a band — plus one restriction, integrality. Verified against brute-force
enumeration of all `3^8` integral assignments in the same band on the toy. ∎

Note the certificate's own honest caveat survives unchanged: the band is a *strictly larger*
feasible set than mass equality, so its optimum and `cert_power_diagram`'s bound are not
comparable in either direction, and neither certifies the centers.

### P2.4 — the power weights are the EG multipliers, up to degeneracy

Write the `τ = 0`, `ρ > 0`, pinned-centers fibre as `max_X Σ_j log m_j − ρ Σ_{z,j} M_z d²_{zj}
x_{zj}` over `Σ_j x_{zj} = 1`, `x ≥ 0`, with `m_j = Σ_z M_z x_{zj}`. Stationarity in `x_{zj}`
with multiplier `α_z` on the supply row:

```
M_z/m_j − ρ M_z d²(z,c_j) ≤ α_z,   with equality on the support.
```

Dividing by `M_z > 0`: `z`'s support lies in `argmax_j (1/m_j − ρ d²(z,c_j)) =
argmin_j (d²(z,c_j) − ω_j)` with `ω_j = 1/(ρ m*_j)`. That is a **power diagram of the centers with
weights `ω`** — precisely `centers.power_labels(xy, C, ω)`.

Setting `α_z := M_z min_j(d²(z,c_j) − ω_j)` gives a dual-feasible pair for the transportation LP
(`α_z + M_z ω_j ≤ M_z d²(z,c_j)` for all `z,j`) satisfying complementary slackness on `supp X*`,
so `ω` is dual-**optimal** at targets `m*` and its dual objective equals `cost(X*)`. Measured on
the toy: violation `3.1e-15`, dual objective equal to primal cost to `1e-9`.

The value-function reading: `F(m) := min{cost : masses = m}` is convex piecewise-linear, the fibre
is `max_{Σ m_j = T} Σ_j log m_j − ρF(m)`, and the first-order condition is
`1/m_j − ρ β_j = μ` for some `β ∈ ∂F(m*)`, i.e. `β = ω − μ/ρ` — the same power diagram, shifted.
**But `∂F(m*)` is a set when the transportation LP is degenerate**, and HiGHS returns one of its
extreme points, which need not be `ω` shifted. Both cases are exhibited:

| `ρ` on the toy | support size vs `n+k−1 = 10` | `max_j |ρβ_j − 1/m_j − mean|` |
|---|---|---|
| `0.005` | `10` (nondegenerate) | `5.0e-16` |
| `0.02` | `9` (degenerate) | `8.9e-3` |

Both dual vectors attain the identical `lp_bound`, so **`cert_power_diagram` is sound in both
cases**; what fails at degeneracy is only the identification of its weights with the EG
multipliers. Recorded because the programme's reading of the weights as "the EG prices" is exact
only off the degenerate locus, and a balance-tight transportation LP is degenerate by construction
(`DOMAIN_optimization.md` §2.6 failure mode makes the same observation about ranging).

### P3a — the split-unit count

`Σ log` is strictly concave and `G := {g(X) : X feasible}` is convex and compact, so the optimal
gain vector `g*` is unique and the optimal face is `P := {X ≥ 0 : Σ_i x_{zi} = 1 ∀z,
Σ_z u_i(z) x_{zi} = g*_i ∀i}`. A vertex of `P` has at most `rank(A)` nonzeros, where `A` has rows
`P_z` (coefficient `1` on `(z,i)` for all `i`) and `G_i` (coefficient `u_i(z)` on `(z,i)` for all
`z`).

*Rank.* A left-null vector `(a, b)` satisfies `a_z + b_i u_i(z) = 0` for every `(z,i)`. If some
`b_i ≠ 0` then `u_i(z) = −a_z/b_i` for all `z`, i.e. `u_i ∝ a`; if some other `b_{i'} = 0` then
`a ≡ 0` and hence `b_i u_i ≡ 0`, a contradiction unless `u_i ≡ 0`. So a nontrivial dependency
exists **iff all the `u_i` are mutually proportional**, in which case there is exactly one.
Therefore `rank(A) = n + k` in general and `n + k − 1` under proportionality.

Each unit has at least one positive entry, so the number of units with two or more is at most
`rank(A) − n`: **`≤ k` in general, `≤ k − 1` at `τ = 0`.** ∎

Verified numerically on the toy (`heterogeneous 11, u_i = M 10, u_i = c_i M 10; n+k = 11`) and
consistent with the instance (`|F| = 10 ≤ 13`). **Label: proved here, pending citation.**
`DOMAIN_optimization.md` §6 Q5 asks `lit-search` for the balanced-fractional-clustering version;
`LENS_GROTHENDIECK.md` §2 attributes `≤ k−1` to `brieden2017 Lem. 4`, which is a common-measure
statement and is therefore the `τ = 0` half of the above, correctly cited. The heterogeneous `≤ k`
appears to be new to this programme; if U0-lit returns a citation the proof here should be
replaced by it, not kept alongside it.

### P3b — the gap in value

Round each `z ∈ F` entirely to one buyer `i(z)` with `x*_{z,i(z)} > 0`. Agent `i` loses at most
what it held fractionally on `F`: `g_i(rounded) ≥ g*_i − Σ_{z∈F} u_i(z) x*_{zi} = g*_i − L_i > 0`
(strict, because `L_i ≤ Σ_{z∈F} u_i(z) < g*_i` whenever `F ≠ Z`; on the instance
`max_i L_i/g*_i = 0.040296`). The rounded assignment is a coverage `(π,σ)` with `im σ = S`, so

```
max_integral V  ≥  Σ_i log(g*_i − L_i)  =  EG_S + Σ_i log(1 − L_i/g*_i),
```

and combining with P1, `0 ≤ EG_S − max_integral V ≤ −Σ_i log(1 − L_i/g*_i)`.

For the coarser form: `Σ_i L_i = Σ_{z∈F} Σ_i u_i(z) x*_{zi} ≤ Σ_{z∈F} max_i u_i(z) ≤ M(F)` under
headroom. `−log(1−ℓ)` is convex and increasing, so `−Σ_i log(1 − ℓ_i)` subject to `Σ_i ℓ_i ≤ s`
and `ℓ_i ≥ 0` is maximised by concentrating on one coordinate; with `ℓ_i = L_i/g*_i ≤ L_i/g_min`
and `Σ_i L_i ≤ M(F)`, the bound is `−log(1 − M(F)/g_min)`, finite iff `M(F) < g_min`. ∎

---

## 4. Numbers computed

Interpreter `/Users/ntlee/projects/td/.venv/bin/python3` (CPython 3.13.15), numpy 2.5.2,
scipy 1.18.1, networkx 3.6.1, HiGHS via `scipy.optimize`. All commands run from the worktree root
`/Users/ntlee/projects/td/.claude/worktrees/A1`. **No seed is used on the real instance**
(proportional response starts from the uniform allocation); the toy is deterministic and its
`seed=` argument is unused. Every number below is printed by the named script.

Command A: `docs/artifacts/U1-cert/instance_numbers.py` (≈4 s) ·
Command B: `docs/artifacts/U1-cert/check_p1_p3.py` (≈7 s) ·
Command C: `docs/artifacts/U1-cert/check_p2.py` (≈5 s).

### 4.1 The certificate itself

| quantity | value | script |
|---|---|---|
| `T = M(Z)` | `2745.611187` | A |
| analytic balance ceiling `k log(T/k)` | `69.5865251441` | A |
| `V(delivered)`, recomputed via `channel.stage2` | `59.9374697984` | A |
| — agrees with `metrics.json` `winner.stage2_value` | `59.9374697984` | A |
| **`EG_{S₁₃}` primal (feasible `X`)** | **`60.6974156139`** | A |
| **`EG_{S₁₃}` dual (weak duality, any `p>0`)** | **`60.6974156139`** | A |
| certified bracket width | `1.279e-13` nats | A |
| **`EG_{S₁₃} − V(delivered)`** | **`0.7599458154`** nats | A |
| `k log(T/k) − EG_{S₁₃}` | `8.8891095303` nats | A |
| `k log(T/k) − V(delivered)` | `9.6490553457` nats | A |
| **tightness factor** `(ceiling − V) / (EG − V)` | **`12.6970`** | A |
| `(EG − V)` as a share of FRAME §6's `3.7`-nat premium | `20.54 %` | A |
| `EG` at `τ=0` (primal = dual = closed form) | `69.5865251441` | A |

### 4.2 What the certificate is a statement about (§5 #2, `LENS_GROMOV` M3 consequence 1)

| quantity | value | script |
|---|---|---|
| spread of `M_j` on the delivered draw | `0.7813 %` | A |
| **spread of realised gains `g_i` on the delivered draw** | **`60.65 %`** | A |
| ratio `g`-spread / `M`-spread | `77.63` | A |
| spread of `g_i` at the `EG_{S₁₃}` optimum | `31.06 %` | A |
| `min_i g_i` delivered / at the EG optimum | `81.869` / `103.617` | A |

### 4.3 Integrality (P3)

| quantity | value | script |
|---|---|---|
| split units at a vertex of the optimal face | `10` (`≤ k = 13`) | A |
| the split zips | `07059 07901 11230 21401 27408 45236 55391 84111 92020 92614` | A |
| `M(F)` | `66.1681` = `2.410 %` of `T` | A |
| a-priori worst case: `12` largest zips | `249.392` = `9.083 %` of `T` | A |
| `M(F)_worst / g_min` | `2.4069` → **bound `= +∞`, vacuous** | A |
| P3b with the realised `M(F)` | `1.0177` nats | A |
| P3b with per-agent `L_i` | `0.2448` nats | A |
| **integrality gap actually realised** | **`5.131e-4`** nats | A |
| `max_i L_i/g*_i` (used in P3b's strictness step) | `0.040296` | A |
| `V` of the rounded EG vertex | `60.6969024656` | A |
| — its improvement over the delivered draw | `+0.7594` nats | A |
| — its `M`-spread / max deviation | `54.21 %` / `33.00 %` | A |

### 4.4 Hypothesis checks and flipping thresholds

| quantity | value | reading | script |
|---|---|---|---|
| `min_z M_z` | `1.80577e-3 > 0` | P1b holds; no starvation guard needed | A |
| `max_{i,z} u_i(z)/M_z`, `filler="theta"` | `1.00000042` | headroom holds to export rounding | A |
| ceiling correction for that slack | `5.46e-6` nats | `≫` tier 1 (`1e-8`), `≪` tier 2 (`5e-3`) | A |
| `max_{i,z} u_i(z)/M_z`, `filler="full"` | `1.2948988` | **headroom fails**; P1c needs `+3.360` nats | A |
| **threshold — `EG_R` useful** | `EG_R ≤ 63.637` | else the outer term cannot see FRAME §6's `3.7`-nat premium | A |
| **threshold — `M(F)` swamps the premium** | `M(F) ≥ 101.055` (`3.68 %` of `T`) | measured `2.410 %`, so P3b bites at `1.018` nats but is not decorative | A |
| toy: rank of the optimal face | `11` heterogeneous, `10` proportional (`n+k = 11`) | P3a's `k` vs `k−1` | B |
| toy: `P1` over all `4 × 3^8` coverages | `max(V − EG_upper) = −4.02e-3` | P1 at `ρ=0` | B |
| toy: `P1` at `ρ = 0.05` with `C_TV` | `max(V_ρ − EG_ρ) ≤ −5.5e-2` | P1 at `ρ>0` | B |
| toy: `P1` proof identity over all `3^8` | `max |V − objective(X_π)| = 0` | the proof, checked | B |
| toy: H3 violated by `c = 26.02` | bound violated by `≥ 1` nat | P1a | B |
| toy: `D(p*)` at `p_z = (k/T)M_z` | `= k log(λT/k)` to `1e-12` | P2.1 | C |
| toy: integer-floor LP relaxation | `t = 0` exactly | P2.2, no dual exists | C |
| toy: `ceiling − max_π Σ log m_j` vs bound | `1.041e-3 ≤ 1.667e-3` | P2.2's nat conversion | C |
| toy: `cert_assignment_at_centers` vs brute force | `41.005296320` both | P2.3 | C |
| toy: `ω = 1/(ρm*)` dual objective vs cost(`X*`) | equal, violation `≤ 3.1e-15` | P2.4b | C |
| toy: EG stationarity of HiGHS `β` | `5.0e-16` (`ρ=0.005`) / `8.9e-3` (`ρ=0.02`) | P2.4c and its caveat | C |

---

## 5. Failure modes

1. **`filler_capture` is open and it decides P1c.** At `"full"` — `docs/MODEL.md` §6.7's own
   recommendation — headroom in the strong form fails (`1.2949`) and the ceiling stops bounding
   `V` without a `+3.360`-nat correction, larger than the premium term. Degrades gracefully: the
   corrected bound `k log(T/k) + Σ_i log ν_i` is still `O(nk)`-computable. **FRAME §9 open item.**
2. **Export rounding (FRAME §5, 6 significant figures)** makes `u_i(z)` exceed `M_z` by up to
   `4.2e-7` relative on 69 zips. The ceiling then holds only to `5.46e-6` nats — three orders
   below the tier-2 floor, two orders above tier 1. Any tier-1 (`1e-8`) claim about the ceiling as
   a bound on `V` is unsupported by the data as exported.
3. **`EG_S` ignores balance, which is the business's settled constraint.** The rounded EG optimum
   has a `54.21 %` `M`-spread. So `0.7599` nats is a bound over a feasible set the sponsor would
   reject, and the balance-constrained fibre value `EG^bal_{S₁₃} ∈ [59.9375, 60.6974]` is the
   number a decision actually needs. This is the same warning `MODEL_U7-meas.md` §2 attaches to
   the premium ladder, and it is why P4 is stated with the spread beside it.
4. **`ρ > 0` needs a named extension.** P1a shows the bound is not automatic. The programme
   currently has no fractional `ρ` term at all (`gain_matrix` has none), so nothing is broken
   today, but any future `ρ`-aware relaxation must declare `Ĉ` and check H3.
5. **Degenerate transportation LPs mis-identify the power weights.** A balance-tight transportation
   LP is degenerate by construction, so on the real instance the `β` `cert_power_diagram` returns
   should not be read as "the EG prices" without checking `support = n + k − 1`. The bound is
   unaffected; the interpretation is.
6. **A4 (is `M` a trustworthy common measure?) is invisible to the EG dual too.** The prices `p_z`
   are a functional of `M` and `S`; a regional bias in `M` biases the prices in the same direction
   and the gap does not move. The EG collapse does *not* answer `LENS_GROMOV` Move 3's **U5**;
   `DOMAIN_optimization.md` §2.8 remains blocked on A4.
7. **A8 (saturation excluding headroom-repaired zips).** The 69 zips at `u/M > 1` are exactly where
   the repair path bit. If the repairs are material, `ν_i` moves and so does P1c's slack.
8. **The masked/unmasked convention.** Under `td/model.py::utilities` a rep with no candidacy
   anywhere in a district has `g_i = 0` and `EG_S = −∞`. P1 is stated and measured in the
   unmasked convention only.

### What the bound does not cover

The gap `EG_S − V` prices only the *drawing and the assignment*, holding the reported inputs fixed.
It says nothing about **misreporting**: `u_i(z)` is built from self-reported book `S_i(z)`, and a
rep who inflates their book raises their own `g_i` and therefore their own claim on zips, with the
fibre program and its dual both computing faithfully on the inflated input (FRAME A7, §10 Q5;
`LENS_GROTHENDIECK` §5b's `G`-invariance is the answer, and it is not this unit's). It says nothing
about **error in `M`**: every quantity here — the ceiling, the prices, the split masses, the gap —
is a functional of `M`, so a regional bias in the sizing shifts the certificate and its bound
together and is undetectable from inside (FRAME A4, `DOMAIN_optimization.md` §3.4 item 4). Neither
exposure is reduced by the collapse; the collapse reduces the *number of things to check*, not the
*set of things unchecked*.

---

## 6. What this says about the problem in FRAME's terms

**FRAME §10 Q3 (why is there no premium bound?) is answered, and the number is small.** One
concave solve, certified by its own dual to `1.3e-13` nats, gives `EG_{S₁₃} = 60.697416` against
a delivered `59.937470`. **At the delivered roster, no map is worth more than `0.760` nats above
the one that was drawn** — against FRAME §6's `~3.7`-nat premium swing. `LENS_GROTHENDIECK`'s yoga
("the premium is won by relabelling the roster, not by redrawing the map") is *supported*: at most
`20.5 %` of the premium exposure is reachable by redrawing at this roster, and the remainder, if
it exists, must come from selection — i.e. from `MODEL_U7-meas.md`'s ladder, not from here.

**The refutation, in the words `docs/units/U1-cert.md` asks for.** The four certificates do **not**
all collapse. Three of four are degenerations or restrictions of `EG_S`'s dual;
`cert_integer_balance_floor` is not, because its LP relaxation has value `0` and it therefore
carries no dual at all. To that extent `LENS_GROTHENDIECK.md`'s central reframing is weaker than it
reads (`DOMAIN_optimization.md` §8 Q4). But the note should *not* keep its five-certificate
structure: the correct replacement is **one duality gap with two sides** — an EG dual (certificates
1, 3, 4, and R3's "certificate 5", all one object) and a constructive primal (certificate 2), which
is a shorter and more honest organisation than either "five certificates" or "one".

**FRAME §10 Q1/Q2 (is two-stage the right decomposition?).** The measured spread of realised gains
is `60.65 %` against a published `M`-spread of `0.781 %` — a factor of `77.63`. Stage 1 equalises the
wrong vector, exactly as `LENS_GROMOV` Move 3 consequence 1 says. But the *cost* of that is
`0.760` nats at the delivered roster, and buying it back costs the balance the sponsor asked for
(`54.21 %` spread at the EG optimum). The two-stage split is not costless and it is not the main
term; both readings are now numbers rather than positions.

**`REVIEW_GROMOV` R3 is settled.** The EG bound is not a fifth certificate. It is *the* dual, and
it is **`12.70×`** tighter than the ceiling on this instance (`0.760` vs `9.649` nats).

**FRAME §10 Q7 (units).** Unchanged by this unit and not helped by it: the gap is still in nats.
The prices `p_z` this unit computes are the input `DOMAIN_optimization.md` §2.4 needs to convert
it, but the modulus `objective-gap ≥ φ(mass moved)` is not established here and remains
`DOMAIN_optimization.md` §8 Q3, the plan's highest-leverage unknown.

---

## 7. Handoff to `math-verify`

Ordered by how much the unit's headline depends on the proposition.

| # | proposition | expected mode | independent oracle |
|---|---|---|---|
| 1 | **P1** — `V(π,σ) ≤ EG_S` for every integral coverage with `im σ = S`, at every `ρ ≥ 0` under H3 | SYMBOLIC | Re-derive: `X_π` feasible, objective identity, sup. Then NUMERIC confirmation by exhausting all `C(4,3)·3^8` toy coverages against the certified dual (`check_p1_p3.py`, `P1(proof)` and `P1a`). |
| 2 | **P4 / the headline numbers** — `EG_{S₁₃} = 60.697416` with a `1.3e-13` bracket, `EG − V = 0.7599` | NUMERIC | Independent of proportional response: check `eg_dual(U, p) ≥ eg_primal(U, X)` by direct `O(nk)` arithmetic on the returned `p, X`; separately verify `V(delivered)` against `metrics.json` `winner.stage2_value` and `td/channel.py::stage2`. A second EG solver (any convex solver, or `cvxpy` if available) should land inside the bracket. |
| 3 | **P2.1** — `cert_balance_ceiling` = `D(p)` at `p_z = (k/T)M_z` | SYMBOLIC | Evaluate `D(p)` by hand at `u_i ≡ λM`; compare against `cert_draw.cert_balance_ceiling(...)["ceiling_nash"]` on the toy and on the instance's realised labels. |
| 4 | **P2.2** — the integer floor is *not* a degeneration | SYMBOLIC + NUMERIC | Symbolic: exhibit `x_{zj} = 1/k` as an LP-feasible point with `t = 0`, so the LP optimum is `0` and its dual is `0`. Numeric: `check_p2.py` `P2.2a`. Then check the nat conversion `k ε²/(2(1−ε)²)` by exhaustion (`P2.2b`). |
| 5 | **P1c** — `EG_S ≤ k log(T/k)` under `u_i(z) ≤ M_z`, and the same for `EG_R` | SYMBOLIC | Two Jensen applications; check the perspective step `Σ y_i log c_i ≤ k log(Σ y_i c_i /k)` separately. NUMERIC side: verify `max_{i,z} u_i(z)/M_z ≤ 1 + 4.2e-7` on the instance and that `EG_{S₁₃} < k log(T/k)`. |
| 6 | **P3a** — split units `≤ k`, and `≤ k−1` iff the `u_i` are proportional | SYMBOLIC | Redo the left-null-space argument `a_z + b_i u_i(z) = 0`. NUMERIC oracle: `numpy.linalg.matrix_rank` on the toy's constraint matrix in the three configurations (`check_p1_p3.py` `P3a'`), plus `|F| = 10 ≤ 13` on the instance. **Flag if a citation for the heterogeneous case surfaces.** |
| 7 | **P3b / P3c** — the value bound, and its vacuity a priori | SYMBOLIC + NUMERIC | Symbolic: `g_i ≥ g*_i − L_i`; `Σ_i L_i ≤ M(F)`; convexity of `−log(1−·)` for the concentration step. Numeric: confirm `2.4069 > 1` so the a-priori bound is `+∞`, and that the realised chain `5.131e-4 ≤ 0.2448 ≤ 1.0177` holds. |
| 8 | **P2.4** — power weights are the EG multipliers, with the nondegeneracy caveat | SYMBOLIC + NUMERIC | Symbolic: KKT of the penalised fibre; dual feasibility of `(α, ω)`; complementary slackness. Numeric: `check_p2.py` `P2.4a–d` at both `ρ`, and confirm the *caveat* reproduces (identity fails at `ρ=0.02` while `lp_bound` is unchanged). |
| 9 | **P2.3** — assignment at pinned centers is the ε-constraint integral restriction | NUMERIC | Brute-force enumeration in the same band on the toy vs `cert_draw.cert_assignment_at_centers` (`check_p2.py` `P2.3`). Check `mip_rel_gap = 0.0` was used (trap 12). |
| 10 | **P1a / P1b** — H3's necessity, and finiteness | NUMERIC | `check_p1_p3.py` `P1c`; and `min_z M_z > 0` from `instance_numbers.py`. |

**Artifacts.** `docs/artifacts/U1-cert/eg.py` (the fibre program, its dual, the toy),
`check_p1_p3.py`, `check_p2.py`, `instance_numbers.py`. `check_*` print `FAILURES: none` and exit
`0` on success; both currently do.

---

## 8. Open (what this unit could not settle)

1. **`max_S EG_S` and `EG_R`.** Only `EG_{S₁₃}` was solved. `max_S EG_S ≥ 60.697416` and
   `≤ k log(T/k) = 69.586525` (P1c). Whether the selection margin is worth anything is
   `MODEL_U7-meas.md`'s ladder, not this unit's. Threshold recorded: `EG_R` is decision-relevant
   only below `63.637`.
2. **The balance-constrained fibre `EG^bal_S`.** The obvious next object: the same concave program
   with an ε-constraint band `|m_j − T/k| ≤ δ`. Still concave, still bounds every *balanced*
   integral coverage by the same argument as P1 (a smaller feasible set), and it is the number a
   sponsor's gap should be quoted in. Bracketed here only as `[59.9375, 60.6974]`. Proportional
   response does not accept side constraints, so this needs a real convex solver — one barrier
   solve, `DOMAIN_optimization.md` §2.2's Stage 3.
3. **`ρ`-aware fibres.** Nothing here computes an `EG_S` with `ρ > 0` on the real instance; the
   toy establishes only that the bound survives under H3. `LENS_GROTHENDIECK` open question 2
   ("is the solver-free `O(nk)` certificate available at `τ > 0`?") is untouched: P2.4's power
   structure is a `τ = 0` result, and whether the heterogeneous fibre's cells are generalized
   power diagrams remains `DOMAIN_optimization.md` §6 Q5.
4. **The `≤ k` heterogeneous split-unit bound's provenance.** Proved here; U0-lit has not run and
   `docs/LIT_optimization.md` does not exist. If §6 Q5 returns a citation, replace the proof.
5. **The displacement modulus.** The prices `p_z` are computed and returned but not converted into
   a lower bound on displacement-to-any-better-coverage (`DOMAIN_optimization.md` §2.4, §8 Q3).
   This unit supplies the input and settles nothing about the output.
6. **`filler_capture` (FRAME §9).** P1c's applicability is conditional on it; the correction is
   `3.360` nats at `"full"`. One business answer removes the conditional.
