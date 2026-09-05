# Model — unit U9-bandthm — the four claims `EG^bal_S(δ)` rests on

**Date:** 2026-09-04 · **Framework:** 0.1-dev · **Track:** A1 (`docs/APPROACHES.md` §A1), run on
`wt/A1` · **Unit:** `docs/units/U9-bandthm.md` ·
**Reads:** `docs/DOMAIN_optimization.md` §2.10–§2.13, §3 · `docs/DOMAIN_economic-theory.md`
§2.8–§2.9 · `docs/MODEL_U1-cert.md` §1–§3 · `docs/VERIFY_U1-cert.md` §2, §4–§7 ·
`docs/MODEL_U7-meas.md` §4 · `docs/LIT_optimization.md` §0, §1, §2, §8 ·
`docs/LIT_economic-theory.md` 2026-09-03 §0, A1-Q1 · `docs/LENS_GROTHENDIECK.md` "The general
case, stated" · `docs/LENS_GROMOV.md` M8, M11, M12 · read-only `td/channel.py`,
`td/model.py` ·
**Owns:** this file, `docs/artifacts/U9-bandthm/**` · **Does not own / did not touch:**
`docs/MODEL_U8-band.md`, `td/`, `tests/`, `tools/`, `docs/FRAME.md`, `docs/BRIEF.md`,
`docs/LENS_*`, `docs/DOMAIN_*`, `docs/LIT_*`.

> **Path note.** The brief's `docs/DOMAIN_*.md` and `docs/LENS_GROMOV.md` are stale: the hub
> copies are the neutral versions and carry none of §2.8–§2.15 or Move 8. A1's copies are under
> `docs/`. Everything else the brief names is at the hub path.

**Headline.** All five claims survive, four of them as theorems and one — P5's *finite*
convergence — only after being restated. Three corrections fall out of the proofs and one of
them is load-bearing for U8 and U12:

1. **`DOMAIN_optimization` §2.12's good-side selection rule is false as written.**
   `supp(X) ⊆ argmax_i u_i(z)/q_{zi}` omits the `1/g_i` normalisation. The correct
   `O(nk)`-checkable rule is `z ↦ argmax_{i∈S} ( u_i(z)/g_i − ν_i M_z )`, whose value is exactly
   `p_z`. **6 of 9 zips on toy2 and 5 of 6 on toy3 violate the published form.** The first-mover
   ranking U14 rests on this and must be recomputed in the corrected margin.
2. **`(T/k)·Σ_i(μ_i^+ + μ_i^-)` is unbounded above at `δ = 0`** and is non-unique whenever every
   agent is band-tight. The supergradient statement is true for *every* optimal dual, so U8 must
   report the **minimised** aggregate `(T/k)·Σ_i|ν_i|` — one extra small LP — or the one-solve
   softness certificate is arbitrarily loose and, at `δ = 0`, vacuous.
3. **The `−1` in `≤ 2k−1` needs no hypothesis** — not `ν_i ≠ 0`, not "some band slack". The
   stop rule's escape clause is not needed and the unconditional bound is `2k−1`, not `2k`.
   `k − 1 + t` with `t` = number of band-tight agents is the sharp form and it is **attained**
   (360 random vertices, minimum slack 0).

Everything is proved for the fibre program; nothing here is a statement about the real instance,
which this unit deliberately did not solve (the brief's "numbers to compute first: none").

---

## 1. Setup (symbol table)

Symbols inherited from `MODEL_U1-cert` §1 keep their meaning exactly; only the new ones are
re-defined. Every symbol appears once.

| symbol | meaning | units / reference value |
|---|---|---|
| `Z`, `n` | footprint of zips carrying sales | `n = 1,229` (FRAME §6) |
| `R`, `m` | wholesalers | `m = 111` |
| `S ⊆ R`, `k` | roster (staff set), `|S| = k` | `k = 13`; delivered `S₁₃` |
| `M_z > 0` | opportunity at `z` (descaled) | `T := Σ_z M_z = 2745.611187` |
| `T/k` | balance target | `211.200861` |
| `λ`, `θ`, `w` | opportunity weight, capture, premium `(1−λ)(1−θ)` | `0.30`, `0.40`, `0.42` |
| `u_i(z) > 0` | rep `i`'s value of `z`, **unmasked** (`td/channel.py::gain_matrix`) | `≥ λ M_z` (P1b) |
| `X ∈ [0,1]^{Z×S}` | fractional assignment | |
| `g_i(X)` | `Σ_z u_i(z) x_{zi}` — gain | descaled gain units |
| `m_i(X)` | `Σ_z M_z x_{zi}` — district mass | `M` units |
| `δ ≥ 0` | band half-width, a **max relative deviation** from `T/k` | grid `{0.0039, …, 0.33}` |
| `F(δ)` | `{X ≥ 0 : Σ_{i∈S} x_{zi} = 1 ∀z, (1−δ)T/k ≤ m_i(X) ≤ (1+δ)T/k ∀i}` | a polytope |
| `G(δ)` | `{g(X) : X ∈ F(δ)} ⊆ ℝ^k_{>0}` — the **gain body** | convex, compact |
| `φ(δ) = EG^bal_S(δ)` | `max_{X ∈ F(δ)} Σ_{i∈S} log g_i(X) − ρ Ĉ(X)` | nats |
| `EG_S` | `φ(∞)`, the unconstrained fibre of `MODEL_U1-cert` P1 | `EG_{S₁₃} = 60.6974156139` |
| `V(π,σ)` | `Σ_j log u_{σ(j)}(A_j) − ρ C(π)` | delivered `59.9374697984` |
| `δ₀` | `max_j |M(A_j) − T/k| / (T/k)` on the committed draw | `0.0039` seed 3, `0.0062` seed 9 |
| `δ_c` | `min{ δ : φ(δ) = EG_S }` — where the band stops binding | instance-dependent |
| `p_z` | multiplier of the supply row `Σ_i x_{zi} = 1` (free sign) | nats per unit of `x` |
| `μ_i^+, μ_i^- ≥ 0` | multipliers of the upper / lower band rows | nats per unit of `M` |
| `ν_i` | `μ_i^+ − μ_i^-`, the **net band multiplier** | nats per unit of `M` |
| `q_{zi}` | `p_z + ν_i M_z`, the **personalised price** | |
| `Σ` | `{(z,i) : u_i(z)/g_i = q_{zi}}` — the MBB set at a KKT point | |
| `t` | `#{i ∈ S : a band row of `i` is tight at the point in question}` | `0 ≤ t ≤ k` |
| `s(δ)` | `(T/k)·Σ_{i∈S}(μ_i^+ + μ_i^-)`, an element of `∂φ(δ)` | nats per unit `δ` |
| `s_min(δ)` | `(T/k)·Σ_{i∈S}|ν_i|` minimised over the dual-optimal set | the **quotable** slope |
| `C(π)`, `Ĉ`, `ρ` | perimeter, its convex extension, penalty weight | `ρ = 0` in the delivered pipeline |
| **H3** | `Ĉ(X_π) ≤ C(π)` at every integral `X_π` (`MODEL_U1-cert` P1) | a modelling choice |
| tier 1 / tier 2 | `1e-8` / `5e-3` nats | FRAME §6 |

**The convention that must not be mixed** (carried verbatim from `MODEL_U1-cert` §1 and
`VERIFY_U1-cert` §7.5): everything below is **unmasked** — `td/channel.py::gain_matrix`, every
rep valued on every zip. Under `td/model.py::utilities` a rep with no candidacy in a district has
`g_i = 0`, `P1b` fails, and every proposition here that uses `u_i(z) > 0` (P2a, P2b, P5's `ĝ > 0`)
is false. The toys in §4 are built unmasked and pinned against `MODEL_U7-meas` §4's published `g`.

**Estimand / decision.** Not a decision. This unit produces the *theorems* U8-band consumes: the
validity of the bound, the price reading and what may be said about it, the split-unit count, the
shape of the frontier, and the safety property of the OA loop.

---

## 2. Propositions

> **P0 (well-posedness).** For every `δ ≥ 0`, `F(δ) ≠ ∅` (`x ≡ 1/k` is feasible, with
> `m_i = T/k` exactly), `F(δ)` is a nonempty compact polytope, `G(δ)` is a nonempty compact
> convex subset of `ℝ^k_{>0}`, and `φ(δ) ∈ ℝ`. Because every constraint is affine and the
> objective's domain `{g > 0}` is open, **Slater's refined condition holds at every `δ ≥ 0`,
> including `δ = 0`** — strong duality and existence of a multiplier pair `(p, μ^+, μ^-)`
> therefore hold on the whole grid, not only for `δ > 0`. `[proved]`
> *(This strengthens `DOMAIN_optimization` §2.10, which asserts multiplier existence only for
> `δ > 0` "in the relative interior of the band".)*

> **P0b (the optimal gain vector is unique).** `Σ_i log g_i` is strictly concave on `ℝ^k_{>0}`
> and `G(δ)` is convex, so the maximiser `g*(δ) ∈ G(δ)` is **unique**, even though the optimal
> `X` is not. Consequently `φ(δ)`, `g*`, the per-agent gains, and every quantity that is a
> function of `g*` alone are vertex-independent; the split *set* is not. `[proved]`
> *(This is the band analogue of `VERIFY_U1-cert` §5's quotation hazard, and it says exactly which
> half of it survives: quote `g*`, never `F`.)*

> **P1-band (the relaxation bound).** Fix `S`, `δ ≥ 0`, and `Ĉ` satisfying **H3**. Then for every
> integral coverage `(π,σ)` with `im σ = S` **whose districts satisfy the band at `δ`**, i.e.
> `(1−δ)T/k ≤ M(A_j) ≤ (1+δ)T/k` for every `j`,
> `V(π,σ) ≤ EG^bal_S(δ)`, with `log 0 = −∞`. This holds at **every `ρ ≥ 0`** under H3, and needs
> neither concavity nor `g_i > 0`. `[proved]`

> **P1a-band (the band hypothesis is load-bearing, not decoration).** Dropping the band from the
> hypothesis makes the statement false: there are instances and `δ` at which a band-**in**feasible
> integral coverage has `V > EG^bal_S(δ)`. `[proved; witness in §4]`

> **P1b-band (monotone chain, and the left endpoint).** `δ ↦ F(δ)` is nested increasing, so
> `V(delivered) ≤ EG^bal_S(δ) ≤ EG_S` for every `δ ≥ δ₀`, and the chain is **false for `δ < δ₀`**
> — not because the inequality fails but because the hypothesis of P1-band does. `LENS_GROMOV`
> M8's `V ≤ EG^bal_{S₁₃}(0.0078)` is therefore **true** (since `δ₀ = 0.0039 ≤ 0.0078`, FRAME §6
> seed 3), but `0.0078` is the *spread*, not `δ₀`, and the sandwich's left endpoint is at
> `0.0039`. `DOMAIN_optimization` §2.10's arithmetic caveat resolves in favour of the published
> inequality and against the published label. `[proved; the numeric premise `δ₀ = 0.0039` is
> FRAME §6's, not recomputed here]`

> **P1c-band (the bound can be vacuous, and that is certificate 2's job).** If no integral
> band-feasible coverage with roster `S` exists at `δ`, P1-band is true and empty. This happens:
> on toy3 the set is empty for every `δ < 0.1111`. The obstruction is exactly
> `cert_integer_balance_floor`'s `t*` — the one certificate that did **not** collapse into the EG
> dual (`VERIFY_U1-cert` row 4) — and `t*/(T/k) > δ` is a Farkas-style infeasibility report
> (**Farkas1902**) that the sponsor must see before any frontier is plotted. `[proved; witness in
> §4]`

> **P2-price (KKT, personalised prices, budget identities).** Let `X*` be optimal at `δ` with
> gains `g*` and let `(p, μ^+, μ^-)` be any multiplier pair (P0). Write `ν_i = μ_i^+ − μ_i^-`,
> `q_{zi} = p_z + ν_i M_z`. Then, at `ρ = 0`:
>
> - **P2.1 (stationarity).** `u_i(z)/g*_i ≤ q_{zi}` for all `(z,i)`, with **equality on
>   `supp(X*)`**. `[proved]`
> - **P2.2 (positivity).** If `u_i(z) > 0` for all `(z,i)` (P1b), then `q_{zi} > 0` everywhere.
>   If in addition `δ > 0`, then `p_z > 0` for every `z`. `[proved]`
>   *(The `δ > 0` hypothesis is real: at `δ = 0` the sign of `p` is not determined — see P2.5.)*
> - **P2.3 (the budget identities).** `Σ_z p_z x*_{zi} = 1 − ν_i m_i(X*)` for every `i ∈ S`, and
>   summing, `Σ_z p_z = k − Σ_{i∈S} ν_i m_i(X*)`. Equivalently, at the *personalised* prices
>   every agent spends exactly its unit budget: `Σ_z q_{zi} x*_{zi} = 1`. `[proved]`
> - **P2.4 (the agent-side MBB).** `max_z u_i(z)/q_{zi} = g*_i`, and `supp(X*_i) ⊆ argmax_z
>   u_i(z)/q_{zi}`: agent `i` buys only zips of maximal bang-per-buck at its own prices, and that
>   maximal ratio *is* its gain. `[proved]`
> - **P2.5 (the good-side rule — the correction).** `supp(X*) ⊆ argmax_{i∈S} ( u_i(z)/g*_i −
>   ν_i M_z )`, and the maximum equals `p_z`. `DOMAIN_optimization` §2.12's
>   `supp(X) ⊆ argmax_i u_i(z)/(p_z + ν_i M_z)` is **REFUTED as written** — it omits `1/g*_i` and
>   is already false in the unbanded case `ν ≡ 0`. The corrected **first-mover margin** is
>   `margin_z := max_i(u_i(z)/g*_i − ν_i M_z) − 2nd-max_i(u_i(z)/g*_i − ν_i M_z)`,
>   `O(nk)`-computable from one solve. `[proved; counterexample in §4]`
> - **P2.6 (it is not a competitive equilibrium at the stated budgets).** If `ν_i ≠ 0` for some
>   `i`, then by P2.3 that agent's expenditure at the **anonymous** prices `p` is
>   `1 − ν_i m_i ≠ 1`. Since `u_i > 0` and `p > 0` (P2.2, `δ > 0`), a rep with `ν_i > 0` leaves
>   budget unspent and would strictly gain by buying more; a rep with `ν_i < 0` is over budget.
>   So `X*` is **not** a Walrasian demand at equal unit budgets and prices `p`.
>   `[proved; the statement matches `jalota2023` (`LIT_optimization` §1), whose repair is a
>   fixed-point perturbation of the budgets, and `echenique2021constrained`
>   (`LIT_economic-theory` A1-Q1), whose constraint-pricing rule is exactly `q_{zi}`]`
> - **P2.7 (what may be claimed about fairness).** Pareto optimality *within `F(δ)`* survives
>   (**Eisenberg & Gale 1959** via the EG-market class, `jainvazirani2010`). Envy-freeness is lost
>   **by theorem, not by conjecture**: `echenique2021constrained` guarantees fairness only when the
>   constraints "do not single out individual agents", and a per-agent band does. EF1 is **not**
>   lost as an achievable property: `kawase2026balanced` shows balanced EF1+fPO allocations exist
>   while *maximising Nash welfare over balanced allocations need not be EF1* — so the correct
>   statement is that the band costs **MNW's EF1 guarantee**, not EF1.
>   `[cited: echenique2021constrained, kawase2026balanced, jainvazirani2010, jalota2023;
>   this corrects `DOMAIN_economic-theory` §2.8's table, which was written 2026-09-03 before
>   `kawase2026balanced` landed]`

> **P2b (the multiplier gauge).** The map `(p, ν) ↦ (p − c·M, ν + c·𝟙)` leaves every `q_{zi}`,
> every budget identity and the whole KKT system unchanged. It preserves the sign/complementarity
> conditions iff `c` lies in an interval `[c⁻, c⁺] ∋ 0` determined by the tight set:
> - if **some** agent has both band rows slack, then `c⁻ = c⁺ = 0` — the decomposition is pinned;
> - if **every** agent is band-tight, the interval is generally nondegenerate; at `δ = 0` (where
>   both rows of every agent are tight) it is **all of `ℝ`**, so `p_z` and the individual `ν_i`
>   are not determined at all and only `q` is.
>
> Consequence: `p` and `ν` are quotable only after the tight set is reported beside them.
> `[proved; both regimes exhibited in §4]`

> **P3-split (the split-unit count).** Let `X` be a vertex of the optimal face of `EG^bal_S(δ)`
> at `ρ = 0`, let `t` be the number of agents with a tight band row at `X`, and let `#splits` be
> the number of zips `z` with `|{i : x_{zi} > 0}| ≥ 2`. Then
>
> ```
> |supp(X)| ≤ n + k + t − 1        and       #splits ≤ k − 1 + t ≤ 2k − 1.
> ```
>
> The `−1` comes from one linear dependency among the tight rows of the *MBB-restricted* face,
> and **it holds unconditionally**: it needs neither `ν_i ≠ 0` for any `i`, nor a slack agent, nor
> `δ > 0`. At `k = 13` the bound is **25 split units of 1,229**. `[proved; the pattern
> "`k−1` + one row per agent" is `lenstra1990`'s extreme-point lemma as extended by
> `shmoystardos1993`, accounted by `lauravisingh2011` Ch. 2's rank lemma and `bansal2012`; only
> the dependency that turns `2k` into `2k−1` is proved here]`

> **P3a-split (the count is worthless without the masses — inherited).** `MODEL_U1-cert` P3c's
> a-priori form is already `+∞` at 12 splits (`M(F)/g_min = 2.407 > 1`); at 25 it is more so.
> `[cited: MODEL_U1-cert P3c, VERIFY_U1-cert §5]`

> **P4-slope (the frontier).** Let `φ(δ) = EG^bal_S(δ)` at `ρ = 0`.
>
> - **P4.1 (monotone).** `φ` is nondecreasing, and constant on `[δ_c, ∞)` with `φ = EG_S` there.
>   `[proved]`
> - **P4.2 (concave).** `φ` is concave on `[0, ∞)`. `[proved]`
> - **P4.3 (envelope / supergradient).** For **any** multiplier pair at `δ`,
>   `s = (T/k)·Σ_{i∈S}(μ_i^+ + μ_i^-) ∈ ∂φ(δ)`, hence
>   `φ(δ') ≤ φ(δ) + s·(δ' − δ)` for every `δ' ≥ 0`. `[proved]`
> - **P4.4 (the aggregate is not unique, and at `δ = 0` it is unbounded — the correction).**
>   `Σ_i(μ_i^+ + μ_i^-)` is **not** a function of the optimum: adding `c ≥ 0` to both `μ_i^+` and
>   `μ_i^-` of a two-sided-tight agent changes nothing else, so at `δ = 0` (every agent
>   two-sided-tight) the expression ranges over `[s_min, +∞)`. The value at the canonical
>   decomposition is `s_min(δ) = (T/k)·Σ_i|ν_i|`, obtained by one small LP over the dual-optimal
>   set, and it is the only form that should be reported or plotted. `[proved]`
> - **P4.5 (one-sided derivatives and kinks).** `φ` concave ⇒ `φ'_+(δ) ≤ φ'_-(δ)` exist and
>   `∂φ(δ) = [φ'_+(δ), φ'_-(δ)]`; hence `φ'_+(δ) ≤ s_min(δ) ≤ φ'_-(δ)`, and `φ` is differentiable
>   at `δ` iff every multiplier pair gives the same aggregate. A kink exists at `δ_c`, where
>   `φ'_+ = 0 < φ'_-`. At a kink, quote the interval `[φ'_+, φ'_-]`, not a number.
>   `[proved; the identification of `∂φ` with the closure of the dual-optimal aggregates is the
>   standard perturbation-function result — **Rockafellar1970**, **BoydVandenberghe2004** §5.6 —
>   and the inclusion direction used here is proved]`
> - **P4.6 (the one-solve softness certificate — corollary).** From one solve at `δ₀` with its
>   duals, for every `δ ≥ δ₀`:
>   `EG^bal_S(δ) − V(delivered) ≤ φ(δ₀) + s_min(δ₀)·(δ − δ₀) − V(delivered)`.
>   If that number is `≤ 5e-3` nats the premium is **certified soft** on `[δ₀, δ]` with no second
>   solve. `[proved]`
> - **P4.7 (two-sided envelope from a finite grid — corollary).** On a grid
>   `δ_1 < … < δ_r`, concavity gives an upper envelope from the tangents and a **lower** envelope
>   from the chords: `φ` lies between the piecewise-linear interpolant of `(δ_j, φ(δ_j))` and
>   `min_j [φ(δ_j) + s_min(δ_j)(δ − δ_j)]` on `[δ_1, δ_r]`. So the frontier U8 plots comes with a
>   certified error bar at every `δ`, not only at grid points. `[proved]`
> - **P4.8 (bisection for `δ*` is licensed by P4.1 alone).** `δ ↦ φ(δ) − V(delivered)` is
>   nondecreasing, so `δ* = min{δ : φ(δ) − V > 5e-3}` is a monotone root and bisection converges;
>   concavity is not needed for this and is what makes M12's "not soft" *prediction*, not the
>   method. `[proved]`

> **P5-OA (the tangent master).** Fix `δ`. For a finite cut set `𝒞 = {(i, ĝ) : ĝ > 0}` with at
> least one cut per agent, let
> `MP(𝒞) := max { Σ_i t_i : X ∈ F(δ), t_i ≤ log ĝ + (g_i(X) − ĝ)/ĝ ∀(i,ĝ) ∈ 𝒞 }`.
>
> - **P5.1 (validity — the safety property).** `MP(𝒞) ≥ EG^bal_S(δ)` for **every** such `𝒞`, at
>   every iteration, not only at convergence. Hence any optimum of the master, and any valid dual
>   bound for it, is an upper bound on `EG^bal_S(δ)` and therefore on `V` for every band-feasible
>   integral coverage (P1-band). `[proved]`
> - **P5.2 (monotone in the cut set).** `𝒞 ⊆ 𝒞'` ⇒ `MP(𝒞') ≤ MP(𝒞)`. `[proved]`
> - **P5.3 (`ĝ > 0` is guaranteed, with an explicit constant).** On `F(δ)`,
>   `g_i(X) ≥ λ·m_i(X) ≥ λ(1−δ)T/k > 0` for `δ < 1`. At `k = 13`, `λ = 0.30` this is
>   `63.113` at `δ = 0.0039` and `42.451` at `δ = 0.33`. `[proved]`
> - **P5.4 (a single well-placed cut is exact).** If `𝒞` contains the cut `(i, g*_i(δ))` for every
>   `i`, then `MP(𝒞) = EG^bal_S(δ)` **exactly**. The master is not an approximation scheme that
>   needs many cuts; it needs one *correctly placed* cut per agent. Corollary: the master LP's
>   duals at that cut set are exactly the original program's multipliers `(p, μ^±)` — so U8 can
>   read P2's prices off its last LP with no NLP solver. `[proved]`
> - **P5.5 (finite convergence — REFUTED as stated, restated correctly).** The
>   **DuranGrossmann1986** / **FletcherLeyffer1994** finite-convergence theorems are about convex
>   *MINLPs*, where finiteness comes from the finitely many integer assignments. `EG^bal_S(δ)` is
>   a purely continuous convex program and the loop is Kelley's cutting-plane method
>   (**Lemarechal1995**); it does **not** terminate finitely at exact optimality in general,
>   because the optimum is not a vertex of any finite cut set unless P5.4's cut is hit exactly.
>   What holds instead: (i) the loop is equivalent to Kelley's method on `Φ(g) = Σ_i log g_i` over
>   the compact convex `G(δ) ⊆ ℝ^k` — so its behaviour is governed by `k = 13`, not by
>   `nk ≈ 16,000`; (ii) `MP` decreases monotonically to `φ(δ)`; (iii) at every iteration the loop
>   holds a certified bracket `[Σ_i log g_i(X^r), MP(𝒞^r)]`, so it can be stopped anywhere and
>   still yield a certificate; (iv) `ε`-termination therefore occurs in finitely many iterations
>   for any `ε > 0`. `[proved for (i)–(iv); the "finite convergence under `ĝ > 0`" of the brief
>   is REFUTED for the continuous master and holds only in the `ε` sense]`
> - **P5.6 (what breaks validity).** P5.1 is a statement about the master's **optimum**. A
>   `time_limit` or solver abort is *not* a bound (trap 15); a nonzero `mip_rel_gap` on any MILP
>   in the loop is not a bound (trap 12); an LP dual-feasible point *is* a bound. `[proved]`

> **P6-cells (the `O(nk)` separating-cell certificate survives the band).** Define the sites
> `f_i(z) := u_i(z)/g*_i − ν_i M_z`. By P2.5 the optimal support is contained in
> `{(z,i) : f_i(z) = max_j f_j(z)}` and `max_j f_j(z) = p_z`. Reading `z ↦ (u_1(z), …, u_k(z), M_z)`
> as a point in `ℝ^{k+1}`, each `f_i` is a **linear** functional there, so the optimal assignment
> is separated by a **generalised power diagram** — one cell per agent, additive weight `−ν_i` on
> the `M`-coordinate — and the whole certificate is checkable in `O(nk)` with no solver, exactly
> the contract `cert_power_diagram` already has. `[proved]`
> `borgwardt2019` (`LIT_optimization` §8) is **corroborating but not the source**: our band is
> verbatim a *bounded-shape* constraint and its theorem says vertices of the bounded-shape
> partition polytope admit a separating power diagram — the same shape of conclusion — but it is
> stated for a geometric point set with a common squared-distance cost, whereas ours is in
> utility space and needs no geometry. `[cited: borgwardt2019, for the analogy only]`
> **What does *not* transfer:** the power diagram of the *geographic centers* that
> `cert_power_diagram` uses at `ρ > 0`, `τ = 0`. At `ρ = 0` with heterogeneous `u` there is no
> geometry in the objective and the cells live in utility space. `[stated]`

---

## 3. Proofs and sketches

Throughout, `ρ = 0` unless stated; P1-band is the only proposition that mentions `ρ` and it
inherits `MODEL_U1-cert` P1's treatment verbatim.

### P0 — feasibility, compactness, Slater at every `δ ≥ 0`

`x ≡ 1/k` has `Σ_i x_{zi} = 1` and `m_i = (1/k)Σ_z M_z = T/k`, which lies in `[(1−δ)T/k,
(1+δ)T/k]` for every `δ ≥ 0` — with equality at `δ = 0`. `F(δ)` is the intersection of the unit
box with finitely many affine sets, hence compact; it is nonempty; `g` is linear so `G(δ)` is a
compact convex subset of `ℝ^k`, and `g_i ≥ λ(1−δ)T/k > 0` on it by P5.3, so `G(δ) ⊆ ℝ^k_{>0}` and
`Σ log` is continuous there: `φ(δ)` is attained and finite.

For strong duality: **every** constraint of the program is affine, and the objective's effective
domain `{X : g_i(X) > 0 ∀i}` is open. The refined Slater condition (**BoydVandenberghe2004**
§5.2.3) then requires only a feasible point in the relative interior of the domain, and does *not*
require strict feasibility of the affine constraints. `x ≡ 1/k` supplies it. Hence strong duality
holds and a multiplier pair exists **at every `δ ≥ 0`**. ∎

This is strictly stronger than `DOMAIN_optimization` §2.10, which claims relative-interior
feasibility only for `δ > 0` and would leave `δ = 0` — the point M8's sandwich starts near —
without a dual.

### P0b — `g*` is unique

`Σ_i log g_i` is strictly concave on `ℝ^k_{>0}` (Hessian `−diag(1/g_i²) ≺ 0`). If `g¹ ≠ g²` were
both maximisers over the convex `G(δ)`, their midpoint would be feasible with strictly larger
value. ∎ The optimal `X`-face is `{X ∈ F(δ) : g(X) = g*}` — this identification is what §4's
vertex enumeration uses, and it is why `g*` is an instance invariant while `F` (the split set)
is not.

### P1-band — the relaxation bound

Let `(π,σ)` be integral with `im σ = S` and `M(A_j) ∈ [(1−δ)T/k, (1+δ)T/k]` for every `j`.
Define `X_π` by `x_{z,σ(j)} = 1` for `z ∈ A_j`.

*Step 1 (inherited).* `MODEL_U1-cert` §3 shows `X_π` satisfies the supply rows and
`Σ_{i∈S} log g_i(X_π) = Σ_j log u_{σ(j)}(A_j)`, and that `−ρĈ(X_π) ≥ −ρC(π)` under H3.

*Step 2 (the one extra check).* `m_i(X_π) = Σ_z M_z x_{z i} = Σ_{z ∈ A_{σ^{-1}(i)}} M_z =
M(A_{σ^{-1}(i)})`, which lies in the band **by hypothesis**. So `X_π ∈ F(δ)`.

Hence the fibre objective at `X_π` is `≥ V(π,σ)` and `EG^bal_S(δ)` is a supremum over a set
containing `X_π`. ∎

**Stop-rule check.** Exactly one hypothesis is instance-dependent — that the coverage is
band-feasible — and it is a hypothesis of the statement, not an assumption about the data. H3 is
a modelling choice this unit controls (`C_TV` satisfies it with equality; `VERIFY_U1-cert` §2
verified this exactly over `3⁷` labellings). Nothing else is assumed. `ρ > 0` costs H3 and
nothing more, and P1a of `MODEL_U1-cert` (VERIFIED, and strengthened by `VERIFY_U1-cert` §2 to a
non-constant convex violator) shows H3 is not decoration.

### P1a-band — the band hypothesis is load-bearing

Immediate from P1b-band's monotonicity read backwards: `EG^bal_S(δ)` is a max over a *smaller*
set than `EG_S`, so it does not bound coverages outside the band. §4 exhibits it: on toy3 at
`δ = 0` there is an integral coverage with `V` exceeding `EG^bal_S(0)` by `2.578e-2` nats.
The gap between "P1" and "P1-band" is therefore not a formality — quoting `EG^bal` against a draw
whose `δ₀` exceeds the plotted `δ` is a wrong claim, and it is exactly what M8's left endpoint
was at risk of. ∎

### P1b-band — the chain and the left endpoint

`δ ≤ δ'` ⇒ `F(δ) ⊆ F(δ')` ⇒ `φ(δ) ≤ φ(δ')`; and `F(δ) ⊆ F(∞)` gives `φ(δ) ≤ EG_S`. The delivered
draw is band-feasible iff `δ ≥ δ₀` by the definition of `δ₀` as a max deviation. Since FRAME §6
reports `δ₀ = 0.0039` (seed 3), `0.0062` (seed 9), and `0.0039 < 0.0078`, M8's inequality holds
as written; its label does not. ∎

*The factor-of-two discrepancy, stated once.* `DOMAIN_economic-theory` N7's grid starts at
`0.0078` = the *spread* `(max−min)/mean`; the band's `δ` is a *max deviation from `T/k`*, and the
two differ by up to a factor 2. Using `0.0078` as the left endpoint does not invalidate anything
(monotonicity), but it misplaces the delivered point on the plot by a factor of two in `δ` and
therefore misplaces `δ*` if `δ*` is near `δ₀` — which is precisely M12's prediction. **U8 should
grid from `δ₀ = 0.0039` and mark the delivered point there.**

### P1c-band — vacuity, and whose job it is

If `{integral band-feasible coverages at roster `S`} = ∅` the proposition quantifies over the
empty set. The existence question is `cert_integer_balance_floor`'s `t*`: an integral coverage
with `max_j |m_j − T/k| ≤ δ·T/k` exists iff `t* ≤ δ·T/k`. `VERIFY_U1-cert` §4 confirms this
certificate's LP root bound is `0` and its content is primal/constructive — which is why it is the
right instrument here and the EG dual is not. ∎

### P2 — the KKT system

Lagrangian (`ρ = 0`), with `s_{zi} ≥ 0` on `x ≥ 0`:

```
L = Σ_i log g_i − Σ_z p_z(Σ_i x_{zi} − 1)
    − Σ_i μ_i^+ (m_i − (1+δ)T/k) − Σ_i μ_i^- ((1−δ)T/k − m_i) + Σ_{z,i} s_{zi} x_{zi}.
```

`∂L/∂x_{zi} = u_i(z)/g_i − p_z − μ_i^+ M_z + μ_i^- M_z + s_{zi} = 0`, i.e.

```
u_i(z)/g_i = p_z + ν_i M_z − s_{zi} ≤ q_{zi},    with equality iff s_{zi} = 0,
```

and complementary slackness `s_{zi} x_{zi} = 0` gives equality on `supp(X*)`. **P2.1 ∎**

**P2.2.** For any `(z,i)`, `q_{zi} ≥ u_i(z)/g*_i > 0` by P1b. For `p`: since `Σ_i m_i(X*) = T` and
the band is centred at `T/k`, there is `i₀` with `m_{i₀} ≤ T/k`; for `δ > 0` that is strictly
below `(1+δ)T/k`, so `μ_{i₀}^+ = 0` by complementary slackness and `ν_{i₀} = −μ_{i₀}^- ≤ 0`. Then
`p_z = q_{z i₀} − ν_{i₀} M_z ≥ q_{z i₀} > 0`. ∎
*(At `δ = 0` this argument fails and, by P2b, must fail: `p` is then determined only up to
`p − cM`.)*

**P2.3.** Multiply the equality form by `x*_{zi}` and sum over `z` (the equality holds wherever
`x*_{zi} > 0`, and both sides are multiplied by `0` elsewhere):
`Σ_z x*_{zi} u_i(z)/g*_i = g*_i/g*_i = 1` on the left, `Σ_z p_z x*_{zi} + ν_i m_i` on the right.
Summing over `i ∈ S` and using `Σ_i x*_{zi} = 1` gives `Σ_z p_z = k − Σ_i ν_i m_i`. The
personalised form `Σ_z q_{zi} x*_{zi} = 1` is the same identity rearranged. ∎

**P2.4.** From P2.1, `u_i(z)/q_{zi} ≤ g*_i` with equality on `supp(X*_i)`, and `supp(X*_i) ≠ ∅`
because `g*_i > 0`. ∎ (This is the standard linear-Fisher MBB with `q` in place of `p`, exactly as
`DOMAIN_optimization` §2.10 says; **KuhnTucker1951**, and the class-level statement is
`jainvazirani2010`'s.)

**P2.5 — the correction.** Rearrange P2.1 as `u_i(z)/g*_i − ν_i M_z ≤ p_z`, with equality iff
`x*_{zi} > 0`. Since `Σ_i x*_{zi} = 1`, some `i` attains equality, so
`max_i (u_i(z)/g*_i − ν_i M_z) = p_z` and the support is contained in the argmax. ∎

Why the published ratio form fails: dividing P2.1 by `q_{zi}` gives `u_i(z)/q_{zi} ≤ g*_i` —
an inequality against an **agent-dependent** right-hand side. `argmax_i u_i(z)/q_{zi}` compares
those ratios across agents *without* dividing by `g*_i`, so it is the argmax of the wrong
quantity, and the error is already present at `ν ≡ 0` (where the published rule reduces to
`argmax_i u_i(z)`, plainly wrong for the unconstrained EG optimum). The scale-free correct form is
`argmax_i u_i(z)/(g*_i q_{zi})`, whose maximum is `1`; the additive form above is the same thing
and is the one to compute, being an `O(nk)` max of affine functions. §4 exhibits a violation with
a 1.6 % margin.

**P2.6.** By P2.3, agent `i` spends `1 − ν_i m_i` at prices `p`. If `ν_i > 0` this is `< 1`; since
`u_i > 0` everywhere and `p_z < ∞`, adding `ε` of any zip strictly raises `g_i` and remains
affordable, so `X*_i` does not solve `max{g_i(x) : p·x ≤ 1, x ≥ 0}`. If `ν_i < 0` the bundle is
*not affordable* at budget 1. Either way `(X*, p)` is not a competitive equilibrium at equal unit
budgets. ∎

**The sentence U12-menu may quote, verbatim:**

> The band multipliers `ν_i` are Lagrange multipliers, not competitive prices. At the equal unit
> budgets the programme actually uses, the `EG^bal_S(δ)` optimum is **not** a competitive
> equilibrium: rep `i` spends `1 − ν_i m_i`, not `1`, at the anonymous prices `p` (proved,
> `MODEL_U9-bandthm` P2.3/P2.6). Equilibrium is recovered only after a fixed-point perturbation of
> the budgets (`jalota2023`), or by re-reading `q_{zi} = p_z + ν_i M_z` as a *constraint price* in
> the sense of `echenique2021constrained` — which is legitimate, and which also settles the
> fairness question negatively: that paper's outcome is fair only when the constraints do not
> single out individual agents, and a per-agent band does. What the band costs is **MNW's** EF1
> guarantee, not EF1 itself; balanced EF1+fPO allocations exist (`kawase2026balanced`).

### P2b — the gauge

Under `(p, ν) → (p − cM, ν + c𝟙)`, `q_{zi} = p_z + ν_i M_z ↦ p_z − cM_z + (ν_i + c)M_z = q_{zi}`.
Stationarity depends only on `q`, so it is preserved. The budget identity's two sides both shift
by `−c m_i`; the summed identity's both sides by `−cT`. What is *not* automatic is
complementarity: writing `ν_i + c = μ_i^+ − μ_i^-` with `μ^± ≥ 0` and `μ_i^+ > 0 ⇒ upper tight`,
`μ_i^- > 0 ⇒ lower tight`, requires

- `c = 0` if agent `i` has both rows slack (then `ν_i = 0` and `ν_i + c` must be `0`);
- `c ≥ −ν_i` if only the upper row is tight; `c ≤ −ν_i` if only the lower row is tight;
- no condition if both rows are tight (only possible when `δ = 0`, since the two rows have
  parallel gradients and coincide only at `δ = 0`).

So `c` ranges over an interval containing `0`, degenerate iff some agent is band-slack, and equal
to `ℝ` when every agent is two-sided-tight. ∎

### P3-split — the dependency that gives the `−1`

Let `X` be a vertex of the optimal face at `δ`, with multipliers `(p, μ^±)` (P0) and
`Σ = {(z,i) : u_i(z)/g*_i = q_{zi}}`. Let `B := {i : μ_i^+ > 0 or μ_i^- > 0}` and let
`𝒯 := {i : a band row of i is tight at X}`; complementary slackness gives `B ⊆ 𝒯`, and
`t := |𝒯|`.

**Step 1 — a smaller polytope containing `X`, all of whose points are optimal.** Put

```
P' := { Y ≥ 0 : y_{zi} = 0 off Σ;  Σ_i y_{zi} = 1 ∀z;  Σ_z q_{zi} y_{zi} = 1 ∀i;
        m_i(Y) = m_i(X) ∀i ∈ B;   (1−δ)T/k ≤ m_i(Y) ≤ (1+δ)T/k ∀i }.
```

For `Y ∈ P'`: on `Σ`, `q_{zi} = u_i(z)/g*_i`, so `Σ_z q_{zi} y_{zi} = 1` reads `g_i(Y) = g*_i`.
Hence `Y` satisfies stationarity with the *same* `(p, μ^±)` (P2.1 with `g(Y) = g*`), satisfies
complementary slackness on the band rows (rows with nonzero multiplier are pinned to their value
at `X`, which is their bound), and is primal feasible. By KKT sufficiency for a concave program,
`Y` is optimal. So `P' ⊆ {optimal face}`, `X ∈ P'`, and since `X` is an extreme point of the
optimal face it is an extreme point of `P'`.

**Step 2 — the rank lemma.** By `lauravisingh2011` Ch. 2, `|supp(X)| ≤ rank(A_tight)` where
`A_tight` is the system of constraints of `P'` tight at `X`, restricted to the columns in
`supp(X)`. Those rows are: `n` supply rows; `k` budget rows `Σ_z q_{zi} y_{zi} = 1`; and, for each
`i ∈ 𝒯`, one band row (for `i ∈ B` the pinned equality, for `i ∈ 𝒯∖B` the tight inequality — and
at `δ = 0` the upper and lower rows are the same affine functional, so they contribute one row,
not two). Total `n + k + t`.

**Step 3 — the dependency.** Consider

```
D := Σ_z p_z·(supply row z)  +  Σ_{i∈B} ν_i·(band row i)  −  Σ_{i∈S} (budget row i).
```

Coefficient of `y_{zi}` for `(z,i) ∈ Σ`: `p_z + ν_i M_z·[i ∈ B] − q_{zi}`. If `i ∈ B` this is
`p_z + ν_i M_z − q_{zi} = 0`. If `i ∉ B` then `ν_i = 0` by complementary slackness, so it is
`p_z − q_{zi} = −ν_i M_z = 0`. Every coefficient vanishes.
Right-hand side: `Σ_z p_z·1 + Σ_{i∈B} ν_i m_i(X) − Σ_i 1 = Σ_z p_z + Σ_{i∈S} ν_i m_i − k = 0` by
P2.3's summed identity (again using `ν_i = 0` off `B`).
`D` is therefore the zero row with zero right-hand side, and it is a **nontrivial** combination
because the budget rows enter with coefficient `−1 ≠ 0`. Hence `rank(A_tight) ≤ n + k + t − 1`.

**Step 4 — the count.** `|supp(X)| ≤ n + k + t − 1`. Every zip has at least one positive entry,
so `#splits ≤ Σ_z (|{i : x_{zi}>0}| − 1) = |supp(X)| − n ≤ k + t − 1`. Since at most one band row
per agent can be tight with a distinct gradient, `t ≤ k`, giving `≤ 2k − 1`. ∎

**Answer to the brief's stop-rule question, explicitly.** *Does the `−1` survive when some
`ν_i = 0`?* **Yes, unconditionally.** Nothing in Steps 3–4 uses `ν_i ≠ 0`: the vanishing
coefficient argument treats `ν_i = 0` as the easy case, the nontriviality comes from the budget
rows (which exist for every agent regardless of the band), and the right-hand side identity is
P2.3, which holds at any KKT point. Nor is a band-slack agent needed. Nor is `δ > 0`. §4 exhibits
the awkward case the stop rule feared — every agent band-tight *and* one of them with `ν_i = 0`
(toy3 at `δ = 0.02`: `t = 2 = k`, `ν = (0, 0.006274)`) — and the bound holds there with slack.
**The `2k` bound is therefore not needed as an unconditional fallback**; it is the coarse version
of `DOMAIN_optimization` §2.10, valid and superseded.

**What is cited and what is proved.** `lenstra1990`'s extreme-point lemma is the `≤ k − 1`
baseline (`VERIFY_U1-cert` §5 re-proved it once; it should not be re-proved again).
`shmoystardos1993` is the same argument with one **weighted** resource row per agent — the exact
shape of our band — and gives `≤ k − 1 + #side rows` as a published pattern; `lauravisingh2011`
Ch. 2's rank lemma is the accounting step and `bansal2012` shows the "+ #side rows" degradation is
essentially unavoidable in general. Only Step 3 is ours, and it is the only thing `math-verify`
needs to attack.

**Sharpness.** The bound `k − 1 + t` is *attained*: over 360 random optimal-face vertices the
minimum slack is 0 (§4). The coarse `2k − 1` was not attained in the ensemble.

### P4 — the frontier

**P4.1.** `F(δ) ⊆ F(δ')` for `δ ≤ δ'` (the band interval widens), so the max is nondecreasing;
and `F(δ) = F(∞)∩{band}` equals `F(∞)`'s optimal face's ambient set once `δ ≥ δ_c`. More
carefully: `δ_c := min{δ : g*(δ) = g*(∞)}` exists because `φ` is nondecreasing and bounded above
by `EG_S`, and by P0b `φ(δ) = EG_S` iff some unconstrained optimum lies in `F(δ)`. ∎

**P4.2.** Let `δ = θδ_1 + (1−θ)δ_2`, `X_j` optimal at `δ_j`, `X = θX_1 + (1−θ)X_2`. Supply rows
are affine so `X` satisfies them; `m_i(X) = θm_i(X_1) + (1−θ)m_i(X_2)` lies in
`[θ(1−δ_1)T/k + (1−θ)(1−δ_2)T/k, …] = [(1−δ)T/k, (1+δ)T/k]` because the band endpoints are affine
in `δ`. So `X ∈ F(δ)`, and by concavity of the objective
`φ(δ) ≥ Σ_i log g_i(X) ≥ θφ(δ_1) + (1−θ)φ(δ_2)`. ∎

**P4.3.** Write the band rows as `m_i ≤ (1+δ_0)T/k + v_i^+` and `−m_i ≤ −(1−δ_0)T/k + v_i^-`, and
let `h(v)` be the optimal value as a function of the perturbation `v ∈ ℝ^{2k}`. `h` is concave and,
under strong duality (P0), `−(μ^+, μ^-) ∈ ∂(−h)(0)`, i.e. `h(v) ≤ h(0) + ⟨μ, v⟩`
(**Rockafellar1970**; **BoydVandenberghe2004** §5.6). Moving `δ_0 → δ` corresponds to
`v_i^+ = v_i^- = (δ − δ_0)T/k` for every `i`, so
`φ(δ) = h(v(δ)) ≤ φ(δ_0) + (δ − δ_0)(T/k)Σ_i(μ_i^+ + μ_i^-)`. ∎
Note both perturbations have the *same* sign: widening the band relaxes the upper row upward and
the lower row downward, which is why the aggregate carries `μ^+ + μ^-` and not `μ^+ − μ^-`.

**P4.4.** At `δ = 0` both band rows of every agent are tight and their multipliers enter the
Lagrangian only through `ν_i = μ_i^+ − μ_i^-` (the two terms combine to `−ν_i(m_i − T/k)`). So
`(μ^+ + c𝟙, μ^- + c𝟙)` is dual optimal for every `c ≥ 0` and `Σ_i(μ_i^+ + μ_i^-)` ranges over
`[Σ_i|ν_i|, +∞)`. The minimum is attained at the canonical decomposition
`μ_i^+ = max(ν_i, 0)`, `μ_i^- = max(−ν_i, 0)`, which is dual feasible (its complementarity
conditions are implied by the sign conditions on `ν`). For `δ > 0` at most one row per agent is
tight, so `Σ_i(μ_i^+ + μ_i^-) = Σ_i|ν_i|` automatically; the residual non-uniqueness is then the
gauge of P2b. Hence `s_min(δ) = (T/k)Σ_i|ν_i|` computed over the dual-optimal set is the tightest
supergradient available from multipliers, and it is a small LP. ∎

**P4.5.** Standard for a finite concave function on an interval: one-sided derivatives exist,
`φ'_+ ≤ φ'_-`, `∂φ(δ) = [φ'_+(δ), φ'_-(δ)]`, and by P4.3 every multiplier aggregate lies in that
interval. `[proved]` The reverse identification — that *every* element of `∂φ(δ)` arises from some
optimal dual — is the standard perturbation-duality correspondence; used here only in the
direction proved. `[sketch: the step not closed is that the optimal dual set is exactly the
`δ`-section of `∂h(0)`; nothing downstream needs it.]`
At `δ_c`, `φ'_+ = 0` (P4.1: `φ` is constant to the right) and `φ'_- > 0` whenever `φ` is not
already constant to the left — a kink, exhibited twice in §4 (magnitudes `0.1546` and
`6.95e-5`, so the *existence* of a kink says nothing about its size).

**P4.6.** Substitute `δ_0 := δ₀` into P4.3 with `s = s_min` and subtract `V(delivered)`. Validity
does not require `V(delivered)` to be optimal for anything; it is a number. ∎

**P4.7.** Upper: P4.3 at each grid point. Lower: concavity implies `φ` lies above every chord, in
particular above the piecewise-linear interpolant of the computed points. ∎

**P4.8.** `φ − V` is nondecreasing (P4.1), so `{δ : φ(δ) − V > 5e-3}` is an up-set and its
infimum is found by bisection. ∎

### P5 — the outer-approximation master

**P5.1.** Fix `X ∈ F(δ)` and `(i, ĝ) ∈ 𝒞`. Concavity of `log` gives
`log g_i(X) ≤ log ĝ + (g_i(X) − ĝ)/ĝ` — a tangent is a global overestimator. Hence
`t_i := log g_i(X)` satisfies every cut row for agent `i`, so `(X, t)` is master-feasible with
objective `Σ_i log g_i(X)`. Taking the supremum over `X ∈ F(δ)`, `MP(𝒞) ≥ φ(δ)`. Boundedness of
`MP(𝒞)` with `≥ 1` cut per agent: `t_i ≤ log ĝ_i + (g_i(X) − ĝ_i)/ĝ_i` and `g_i ≤ Σ_z u_i(z) < ∞`
on `F(δ)`. ∎

**P5.2.** More cut rows shrink the master's feasible set. ∎

**P5.3.** `u_i(z) ≥ λ M_z` (`MODEL_U1-cert` P1b, verified symbolically in `VERIFY_U1-cert` §2), so
`g_i(X) = Σ_z u_i(z)x_{zi} ≥ λ Σ_z M_z x_{zi} = λ m_i(X) ≥ λ(1−δ)T/k`. ∎ This is the explicit
form of what `DOMAIN_optimization` §2.11 calls "guaranteed by the lower band", and it is what
makes the tangent constant `1/ĝ` bounded, hence the master numerically safe.

**P5.4.** With one cut per agent at `ĝ = g*`,
`MP = Σ_i log g*_i + max_{g ∈ G(δ)} Σ_i (g_i − g*_i)/g*_i`. Since `g*` maximises the concave
`Φ(g) = Σ_i log g_i` over the convex `G(δ)`, first-order optimality gives
`∇Φ(g*)·(g − g*) ≤ 0` for all `g ∈ G(δ)`, and `∇Φ(g*)_i = 1/g*_i`. So the max is `0`, attained at
`g = g*`, and `MP = Φ(g*) = φ(δ)`. ∎

*Corollary (the duals come free).* In that master, stationarity in `t_i` forces the multiplier on
agent `i`'s cut row to be exactly `1`; stationarity in `x_{zi}` is then
`−u_i(z)/g*_i + p_z + ν_i M_z ≥ 0` with the LP's own supply and band multipliers `(p, μ^±)`. That
is P2.1. So the LP master at a converged cut set returns the original program's multipliers —
U8 needs no NLP solver to get the prices, only a well-placed cut. `[proved]` §4 checks the
converse numerically by recovering `(p, ν)` from an *independent* dual-feasibility LP and finding
the same KKT system.

**P5.5.** The loop is Kelley's method: define `G(δ) ⊆ ℝ^k` and note that the master is
`max_{g ∈ G(δ)} min_{(i,ĝ) ∈ 𝒞} [tangent]`, a function of `g` alone; the `nk` variables enter only
through `g`. Duran–Grossmann/Fletcher–Leyffer finiteness is a statement about the finitely many
*integer* assignments of a MINLP, of which this problem has none; Kelley's method on a smooth
strictly concave objective over a polytope has no finite termination in general, because by P5.4
exact termination requires hitting `g*` exactly and `g*` is not a vertex of `G(δ)` in general.
`[proved that the cited theorems do not apply and that exactness requires P5.4's cut]`
What does hold, and is all U8 needs: (i) validity at every iteration (P5.1); (ii) monotonicity
(P5.2); (iii) the bracket `[Σ_i log g_i(X^r), MP(𝒞^r)]` contains `φ(δ)` at every `r`; (iv) `MP`
decreases and converges to `φ(δ)` — standard Kelley convergence on a compact convex set with a
Lipschitz-gradient objective, the Lipschitz constants coming from P5.3's `g_i ∈ [λ(1−δ)T/k,
Σ_z u_i(z)]`. `[sketch for (iv): the step not closed is an explicit iteration bound; the
dimension-`k` reduction says any such bound depends on `k = 13`, not on `nk ≈ 16,000`, but the
classical Kelley bounds are exponential in the dimension and are not worth quoting.]`

**The stop rule's escape clause, used.** The brief anticipated that finite convergence might need
a compactness argument the polytope does not supply. It is worse and simpler than that: the
polytope supplies compactness (P0) and the lower band supplies `ĝ > 0` (P5.3); what is missing is
that the *theorem being cited is about a different class of problem*. **U8 must not report "OA
converges finitely" and must not use "the loop converged" as the certificate — the certificate is
the master optimum at whatever cut set it stopped with (P5.1) together with the incumbent.**

**P5.6.** P5.1 bounds `φ` by the master's **optimal value**. Any procedure that returns a number
larger than the master optimum still bounds `φ` (a dual-feasible point of the master LP is such a
number); any procedure that may return a number *smaller* than it — a truncated branch-and-bound
incumbent, a `time_limit` stop, a nonzero `mip_rel_gap` — does not. ∎

### P6-cells — the `O(nk)` check under the band

Proved in the statement: P2.5 says `max_i f_i(z) = p_z` with `f_i(z) = u_i(z)/g*_i − ν_i M_z`, and
`supp(X*) ⊆ argmax_i f_i(z)`. Each `f_i` is affine in the `(k+1)`-vector
`(u_1(z),…,u_k(z), M_z)`, so the assignment cells are the maximisation cells of `k` affine
functions — a generalised power diagram with sites indexed by agents. Checking the certificate is
`k` evaluations per zip: `O(nk)`, no solver, matching `cert_power_diagram`'s existing contract and
`Khachiyan1980`'s separation-equals-optimisation licence quoted by `DOMAIN_optimization` §2.10. ∎

**On `borgwardt2019` (the PLAUSIBLE-or-better item), verdict.** *Corroborating; not needed; and
it does not deliver the geometric power diagram the acceptance criterion literally asks for.*
Our band `(1−δ)T/k ≤ m_i ≤ (1+δ)T/k` is verbatim a **bounded-shape** constraint, and Borgwardt &
Happach's theorem — vertices of the bounded-shape partition polytope correspond to clusterings
admitting a separating power diagram, one cell per cluster — is the same *shape* of conclusion, so
the claim that "the cell certificate survives the band" is supported by published work as well as
by P6. But (i) their result is stated for a clustering of a geometric point set with a common
cost, and our cells live in utility space with agent-specific `u_i`; (ii) our `EG^bal` vertex is
a vertex of the **optimal face of the EG program**, not of the bounded-shape partition polytope,
and is fractional on up to `2k−1` zips; (iii) at `ρ = 0` there is no geometry in the objective at
all, so a power diagram of the *geographic centers* is not what separates. **The honest report is
that `cert_power_diagram`'s `O(nk)` contract survives the band by P6, proved directly, and that
`borgwardt2019` is the citation for the class of constraint, not for our certificate.** The
second half of that entry — the normal-cone *volume* as a stability radius for the map — is a real
and unexplored lead for U4-disp and is not this unit's. `[conjectured, for the geometric version:
a counterexample would live in an instance where two agents' `u` differ on zips that are
geographically interleaved, so no separating power diagram of centers exists while P6's utility-
space cells are unaffected.]`

---

## 4. Numbers computed

**Environment.** `/Users/ntlee/projects/td/.venv/bin/python3` (CPython 3.13.15), numpy 2.5.2,
scipy 1.18.1, HiGHS via `scipy.optimize.linprog` / SLSQP via `scipy.optimize.minimize`. All
commands from `/Users/ntlee/projects/td/.claude/worktrees/A1`. Runtime `108 s`, exit `0`,
`FAILURES: none`.

```
/Users/ntlee/projects/td/.venv/bin/python3 -W ignore docs/artifacts/U9-bandthm/bandthm.py
```

**Seeds** (all explicit, printed by the script): toy2 instance `20260904`; optimal-face vertex
directions `7` (toys) and `1234` (ensemble); random cut sets `99`; `g*`-uniqueness vertices `5`.
No random number is used on any real-instance quantity — this unit computes none.

**Fixtures.** *toy1* = `MODEL_U7-meas` §4's shared fixture (3 reps, 4 zips, `k = 2`, θ = 0.40,
λ = 0.30, `M = [20,15,15,20]`), roster `{A, C}`. *toy3* = 6 zips, 3 reps, `k = 2`,
`M = [40,10,10,10,10,10]`, one heavy zip — **built so the band binds**, which toy1 does not.
*toy2* = 5 reps, 9 zips, `k = 3`, seeded. *ensemble* = 60 random instances, `n ∈ [6,10]`,
`k ∈ [2,4]`, `δ ∈ {0, 0.02, 0.08, 0.25}`.

### 4.0 Convention pin (the trap in `MODEL_U1-cert` §5.8)

| quantity | value | script · command |
|---|---|---|
| toy1 `g` matrix vs `MODEL_U7-meas` §4's published `[[22.82,16.10],[17.78,19.46],[16.10,21.14]]` | `max|Δ| = 0.00e+00` | `bandthm.py` §P0 |
| toy1 `V(D1→A, D2→C)` vs published `6.1788` | `6.178804` | same |
| `g − 0.42·b` rep-independent (FRAME `w = 0.42`) | spread `0.00e+00` | same |

### 4.1 P1-band

| quantity | value | script |
|---|---|---|
| toy1: `max(V − EG^bal)` over band-feasible integral coverages, `δ ∈ {0, 0.02, 0.0714, 0.15, 0.33}` | `0.000e+00` | `bandthm.py` §P1 |
| toy3: same, `δ ∈ {0, 0.02, 0.06, 0.1111, 0.33}` (62 coverages) | `0.000e+00` | same |
| toy2: same, `δ ∈ {0, 0.03, 0.12, 0.35}` (18,150 coverages) | `−1.748e-02` | same |
| **P1a-band witness**: toy3 at `δ = 0`, best band-**in**feasible coverage minus `EG^bal(0)` | **`+2.5781e-02` nats** | same |
| **P1c-band witness**: toy3 band-feasible integral coverages at `δ ∈ {0, 0.02, 0.06}` | **`0`** (the bound is true and empty) | same |
| toy1 frontier is flat: `EG^bal(δ) = EG_S` for every `δ ≥ 0` | `6.1788043249` | same |
| toy3 `EG^bal` at `δ = 0 / 0.02 / 0.06 / 0.1111` | `6.6680676256 / 6.6740054555 / 6.6841517659 / 6.6938489330` | same |

### 4.2 P2-price (toy3 at `δ = 0.02`; the duals come from an LP independent of the primal solver)

| quantity | value | script |
|---|---|---|
| masses `m` vs band `[44.10, 45.90]` | `[44.10, 45.90]` — both agents tight, `t = k = 2` | `bandthm.py` §P2 |
| `ν` | `[0.000000, 0.006274]` — **one tight row with `ν_i = 0`** | same |
| stationarity `max_{z,i}(u_i/g_i − q_{zi})` | `1.0e-13` (`≤ 0` required) | same |
| stationarity residual on `supp(X)` | `1.0e-13` | same |
| `min_{z,i} q_{zi}` (P2.2) | `0.1551 > 0` | same |
| `min_z p_z` (P2.2) | `0.155126 > 0` | same |
| budget identity `max_i |Σ_z p_z x_{zi} − (1 − ν_i m_i)|` | `3.4e-13` | same |
| summed identity `|Σ_z p_z − (k − Σ_i ν_i m_i)|` | `2.8e-13` | same |
| personalised spend `max_i |Σ_z q_{zi}x_{zi} − 1|` | `3.4e-13` | same |
| **P2.6 witness**: rep 1's spend at the anonymous prices `p` | **`0.712029`** (budget 1; `ν = +0.006274`) | same |
| toy2 `δ = 0.03`, the other sign: rep 1's spend | **`1.072318`** (`ν = −0.001196`, force-fed) | same |
| good-side rule `max_i(u_i/g_i − ν_i M_z)` vs `p_z` | `max|Δ| = 1.0e-13` | same |
| **P2.5 refutation**: zips where `supp(X) ⊄ argmax_i u_i(z)/q_{zi}` | **5 of 6** (toy3), **6 of 9** (toy2) | same |
| — the witness: toy3 zip 1, owner's `u/q` vs rival's | `27.907200` vs `28.364000` (rival larger by **1.64 %**), yet the rival holds `x = 0.410` | same |

### 4.3 P2b (the gauge) and P4.4 (the unbounded aggregate)

| quantity | value | script |
|---|---|---|
| toy3 `δ = 0`, gauge interval for `c` | all of `ℝ` (LP boxed at `±50`, width `≥ 100`) | `bandthm.py` §P2d |
| toy3 `δ = 0.02` and `0.06` (both agents tight) | `c ∈ [−0.0050, 0]`, width `5.0e-3` | same |
| toy3 `δ = 0.33` (an agent slack) | `c ∈ [0, 0]`, width `0` — **pinned** | same |
| toy2 `δ = 0.03, 0.12, 0.35` (an agent slack) | width `0` | same |
| `max_{z,i}|Δq|` along the gauge orbit | `≤ 3.5e-13` (invariant, as proved) | same |
| toy3 `δ = 0`: agents with **both** rows tight | `2/2` ⇒ `Σ(μ⁺+μ⁻)` unbounded above | `bandthm.py` §P4-caveat |
| toy3 `δ = 0`: minimised slope `s_min = (T/k)Σ|ν_i|` | `0.311544` (finite) | same |

### 4.4 P3-split

| quantity | value | script |
|---|---|---|
| toy3, 16 optimal-face vertices over 4 `δ` | `#splits ≤ k−1+t` with min slack `1`; `t ∈ {0, 2}` | `bandthm.py` §P3 |
| toy2, 30 optimal-face vertices over 4 `δ` | min slack **`0`** (the sharp bound is attained); `t ∈ {0,1,2,3}` | same |
| ensemble, **360** optimal-face vertices, 60 instances | sharp bound `k−1+t`: min slack **`0`**; coarse `2k−1`: min slack `1` | `bandthm.py` §P3-random |
| — max splits observed / max `t` observed | `4` / `4` | same |
| toy3 `δ = 0.02` — the case the stop rule feared: `t = k = 2` (all tight) **and** `ν_0 = 0` | bound holds, slack `1` | §P2, §P3 |
| **at `k = 13`**: `k−1 = 12`, `2k−1 = 25`, `2k = 26` | `25` split units of 1,229 | §specialisations |

### 4.5 P4-slope

| quantity | value | script |
|---|---|---|
| toy3 grid `δ ∈ {0, .01, .02, .04, .06, .09, .15, .33}`, monotone | min increment `0.000e+00` | `bandthm.py` §P4 |
| toy3 concavity (all chord triples) | min `(value − chord)` = `7.305e-05 ≥ 0` | same |
| toy3 supergradient `φ(δ') ≤ φ(δ) + s_min(δ)(δ'−δ)`, all grid pairs | max violation `0.000e+00` | same |
| toy3 chord lower bound (P4.7) | max violation `0.000e+00` | same |
| toy3 `s_min` at `δ = 0 / .01 / .02 / .04 / .06 / .09 / ≥.15` | `0.311544 / 0.296870 / 0.282324 / 0.253587 / 0.225276 / 0.183500 / 0` | same |
| toy3 one-sided bracket `D⁺ ≤ s_min ≤ D⁻` (`h = 1e-5`) | holds at every interior grid point | same |
| toy2 concavity / supergradient / chord | `0.000e+00` / `1.776e-15` / `1.776e-15` | same |
| toy2 `s_min` at `δ = 0 / .01 / .03 / .06 / ≥.12` | `0.119445 / 0.101362 / 0.074555 / 0.034299 / 0` | same |
| width of a single `ν_i` over the dual-optimal set, `δ > 0` | `≤ 6.6e-03` (toy3), `≤ 3.3e-14` (toy2) | same |
| **kink** toy3 at `δ_c = 0.111111`: `D⁺ / s_min / D⁻` | `0 / 0 / 0.154586` | `bandthm.py` §P4-kink |
| **kink** toy2 at `δ_c = 0.084952`: `D⁺ / s_min / D⁻` | `0 / 0 / 6.954e-05` | same |
| P4.6 softness certificate, toy2: `φ(0.03) = 10.0043860916`, `s_min = 0.074555` | one-solve bound at `δ = 0.12`: `10.0110960492`; true `10.0064509834`; **slack `4.645e-03`** | `bandthm.py` §P4-softness |

### 4.6 P5-OA (toy2 at `δ = 0.03`; the hardest case, the loop does not converge in 400 iterations)

| quantity | value | script |
|---|---|---|
| master optima over **400** iterations, min | `10.004386098825` `≥ φ = 10.004386091643` | `bandthm.py` §P5 |
| master optima monotone non-increasing | max increment `0.000e+00` | same |
| bracket at iteration 400 | `7.265e-09` nats (inside tier 1) | same |
| first six master upper bounds | `10.019378, 10.006189, 10.004591, 10.004444, 10.004396, 10.004390` | same |
| **P5.4**: master with a single tangent per agent at `g*` | `10.004386091643`, `|Δ| = 0.00e+00` | same |
| 25 random cut sets: `min(MP − φ)` | `+2.553e-02 ≥ 0` | same |
| toy3 `δ = 0.02`: same battery | valid, monotone, single-cut exact to `0.00e+00` | same |
| `g_min` vs `λ(1−δ)T/k` (P5.3) | `25.7422` vs `18.1388` | same |

### 4.7 P0b and the vertex-dependence discipline

| quantity | value | script |
|---|---|---|
| toy3 `δ = 0.02`, 25 optimal-face vertices: `max|Δg*|` | `2.13e-14` — `g*` is an invariant | `bandthm.py` §P0b |
| — distinct split **sets** over those vertices | `5` | same |
| toy2 `δ = 0.03`: `max|Δg*|` / distinct split sets | `1.10e-13` / `6` | same |

### 4.8 Specialisations at the real instance's shape (arithmetic on FRAME §6 constants only)

| quantity | value | script |
|---|---|---|
| `T/k` | `211.200861` | `bandthm.py` §specialisations |
| band at `δ₀ = 0.0039` (seed 3) | `[210.3772, 212.0245]`, width `1.6474` | same |
| band at `δ₀ = 0.0062` (seed 9) | `[209.8914, 212.5103]`, width `2.6189` | same |
| band at `δ = 0.0078` (the *spread*, N7's left endpoint) | `[209.5535, 212.8482]`, width `3.2947` | same |
| band at `δ = 0.33` | `[141.5046, 280.8971]` | same |
| P5.3 floor `λ(1−δ)T/k` at `δ = 0.0039 / 0.05 / 0.33` | `63.1132 / 60.1922 / 42.4514` | same |
| `EG_{S₁₃} − V(delivered)` (from `MODEL_U1-cert` §4.1, recomputed as a difference) | `0.7599458155` nats | same |
| roster-free screen `60.8025` minus `V` (`LENS_GROMOV` M8) | `0.8650` nats | same |
| slope that would exhaust the certified gap from `δ₀ = 0.0039` to `δ = 0.02 / 0.05 / 0.10 / 0.33` | `47.20 / 16.48 / 7.91 / 2.33` nats per unit `δ` | same |

> **Reading of the last row, for U8.** If the measured `s_min(δ₀)` on the real instance is below
> `2.33` nats per unit `δ`, then the *one-solve* certificate at `δ₀` already proves that no
> band-feasible coverage anywhere on the grid beats the delivered draw by more than the
> unconstrained `0.760` nats — i.e. P4.6 immediately recovers `MODEL_U1-cert`'s headline over the
> whole frontier. If it is above `47.2`, the tangent is useless past `δ = 0.02` and the grid must
> be solved. The toys give `s_min` of order `0.1–0.3` on `T/k`-normalised instances, which is not
> evidence about the real one.

---

## 5. Failure modes

Which FRAME §5 gaps and §6 bounds break these results, and how each degrades.

1. **The masked/unmasked convention (`MODEL_U1-cert` §5.8, `VERIFY_U1-cert` §7.5).** Under
   `td/model.py::utilities` a rep with no candidacy in a district has `g_i = 0`; then P1b fails,
   `q_{zi} > 0` (P2.2) fails, `log g_i = −∞`, P5.3's `ĝ > 0` fails and the whole tangent master is
   undefined. **Every proposition here is stated in the unmasked convention only.** A
   wrong-convention run on the real instance would put the bound ≈34 nats *below* `V` and look
   like a refutation of P1-band. Degrades: catastrophically and silently. **Mitigation:** the toy
   fixture pins the convention against `MODEL_U7-meas` §4's published `g` (§4.0), and U8 should
   run that pin first.

2. **No integral band-feasible coverage exists (P1c-band).** At small `δ` the bound is true and
   empty, and the whole frontier below `t*/(T/k)` describes a fractional world with no integral
   inhabitant. On toy3 this is *every* `δ < 0.1111`. FRAME's grid starts at `δ₀`, which is by
   construction feasible for the delivered draw, so the real instance is protected at the left
   endpoint — but §2.13's rounding problem is not, and `cert_integer_balance_floor`'s `t*` is the
   only instrument that detects it. Degrades gracefully **if reported**; silently if not.

3. **`δ₀` is a max deviation and N7's grid is a spread.** The factor-of-2 does not break any
   inequality (P1b-band) but misplaces the delivered point and, since M12 predicts `δ*` is near
   `δ₀`, misplaces the one number the softness test is about. Degrades: a wrong `δ*` by up to a
   factor of 2. **Mitigation:** grid from `0.0039`.

4. **`ρ > 0` needs a named `Ĉ` (H3).** Inherited from `MODEL_U1-cert` P1a, VERIFIED and
   strengthened by `VERIFY_U1-cert` §2. The delivered pipeline has `ρ = 0` and
   `channel.gain_matrix` carries no `ρ` term, so nothing is broken today. P2–P6 are stated at
   `ρ = 0` only: with a `ρ Ĉ(X)` term the KKT system acquires a subgradient of `Ĉ` in every
   stationarity row and **P2.5, P3, P6 all change**. Degrades: those four propositions become
   claims about a different program. **Do not carry them into a `ρ`-aware fibre without redoing
   §3.**

5. **Dual degeneracy is structural, not incidental (P2b, P4.4).** A balance-tight polytope is
   degenerate by construction. `p` and the individual `ν_i` are gauge-dependent whenever every
   agent is band-tight, which is *the* case of interest at small `δ`; `Σ(μ⁺+μ⁻)` is unbounded at
   `δ = 0`. Degrades: the *bound* is untouched (weak duality holds at any dual-feasible point);
   the *exchange rate* U14 sells to the sponsor is not a number until the tight set and the
   minimisation are reported beside it. **Report `s_min`, the tight set, and the gauge width.**

6. **The split count is worthless without the split masses.** `MODEL_U1-cert` P3c: at 12 splits
   the a-priori value bound is already `+∞`; at 25 it is more so. And the split *set* is
   vertex-dependent under the band exactly as it was without it (§4.7: 5–6 distinct split sets at
   the same `g*`). Degrades: a bare "`≤ 25` splits" is a true sentence that supports no claim.
   **Quote `|F| ≤ k−1+t`, `M(F) < g_min`, and the direction of the chain** (`VERIFY_U1-cert` §5).

7. **A `time_limit` or a nonzero `mip_rel_gap` is not a bound (P5.6, traps 12 and 15).** The
   whole architecture rests on P5.1, which is about the master's *optimum*. Degrades: a reported
   "certificate" that is not one. This is the single most likely way U8 ships a wrong number.

8. **Finite convergence of the OA loop does not hold (P5.5).** toy2 at `δ = 0.03` did not close in
   400 iterations (bracket `7.3e-09`, inside tier 1 but not zero). Degrades gracefully — the
   bracket is a certificate at every iteration — provided nobody writes "converged".

9. **A4 (is `M` a trustworthy common measure?) is invisible here too.** Every object in this
   unit — `p`, `ν`, `q`, `s_min`, `δ₀`, the cells of P6 — is a functional of `M`. A regional bias
   in the sizing moves the band, the multipliers and the exchange rate together and is undetectable
   from inside, exactly as `VERIFY_U1-cert` §6 records for the unbanded case. Not reduced by
   anything proved here.

10. **Misreporting (FRAME A7).** `u_i(z)` is affine and strictly increasing in the self-reported
    book with coefficient `w = 0.42`; an inflated book raises `g_i`, raises `u_i(z)/g_i − ν_i M_z`
    on the inflated zips, and moves P6's cells toward them, with every identity in §3 remaining
    internally consistent on the inflated input. Not reduced by anything proved here.

11. **`echenique2021constrained` and `kawase2026balanced` were read through
    `docs/LIT_economic-theory.md`'s annotations, not the papers.** P2.7 is a `[cited]` claim whose
    strength is the annotation's. `math-verify` should treat P2.7 as citation-checkable, not
    proof-checkable.

---

## 6. What this says about the problem in FRAME's terms

**The certificate the charter should have named is sound, and it is now a theorem rather than
five claims.** P1-band is `MODEL_U1-cert` P1 plus one line, exactly as `LENS_GROMOV` Move 8
predicted; P2's identities hold as written; P3's `2k−1` holds *without* the hypothesis the stop
rule was prepared to concede; P4's envelope holds and its corollary is the cheapest decisive
computation in the plan. So A1's retreat from "MINLP" to "a few convex programs plus rounding"
is licensed by the mathematics, not merely by the arithmetic.

**Three things U8 must do differently from what the plan says.**

1. **Grid from `δ₀ = 0.0039`, not `0.0078`.** Monotonicity means nothing published becomes false,
   but M12's prediction is about the *left* of the curve and the left endpoint is off by a factor
   of two.
2. **Report `s_min(δ) = (T/k)Σ_i|ν_i|` minimised over the dual-optimal set** — one extra small LP
   per grid point. The plan's `(T/k)Σ_i(μ_i^+ + μ_i^-)` is a valid supergradient for *some* dual
   and unbounded for others; at `δ = 0` it is `+∞`, which would make the one-solve softness
   certificate vacuous exactly where FRAME §3's tolerance question lives.
3. **Rank first movers by `max_i(u_i(z)/g_i − ν_i M_z) − 2nd-max_i(·)`, not by the ratio form.**
   §2.12's rule is false; U14's list computed from it would be the wrong list, and the error is
   present even at `ν ≡ 0`, i.e. it is inherited from the unbanded reading, not introduced by the
   band.

**On FRAME §3's "never elicited" tolerance.** P4.3 + P4.4 give the exchange rate as a *computed*
number with an honest error bar (`[φ'_+, φ'_-]` at a kink; the gauge width beside it). But
`DOMAIN_economic-theory` §2.9's distinction stands and is now sharper: `s_min` is a marginal rate
of *transformation*, a fact about `F(δ)`; the sponsor's rate is a marginal rate of substitution.
They coincide only at the sponsor's own optimum. What P2.6 adds is that the object producing the
rate is **not a market price**, so the temptation to present `ν_i` as "what a territory-dollar
costs rep `i`" is not available: it is a multiplier on a constraint the sponsor imposed
(`echenique2021constrained`'s constraint price), and `jalota2023` says the market reading needs
budgets that were never perturbed.

**On the `0.760`-nat headline.** P1-band says that number is an upper bound over a feasible set
the sponsor would reject (`M`-spread `≥ 50 %`, `MODEL_U1-cert` §5.3). `EG^bal_{S₁₃}(δ₀)` is the
number a decision needs, and P4.6 says one solve at `δ₀` may settle the whole grid. §4.8 gives the
threshold: the certificate covers the full grid to `δ = 0.33` if `s_min(δ₀) ≤ 2.33` nats per unit
`δ`, and covers only to `δ = 0.02` if it is `47.2`. **That comparison is the first thing to print
after U8's first solve.**

**On what none of this touches.** Other rosters (`max_S EG^bal_S` is bounded only by the screen
`60.8025`, i.e. `0.865` nats over `V`); misreporting; error in `M`; and business units. The
exposure ledger of `VERIFY_U1-cert` §6 is unchanged by the band.

---

## 7. Handoff to `math-verify`

Ordered by how much the deliverable depends on the proposition.

| # | proposition | expected mode | independent oracle |
|---|---|---|---|
| 1 | **P5.1** — every master optimum is `≥ EG^bal_S(δ)`, at every cut set | NUMERIC | Brute force: on a toy with `n ≤ 8`, `k ≤ 3`, enumerate random cut sets and compare `MP(𝒞)` against `φ(δ)` computed by a *different* solver (SLSQP / trust-constr / a fine grid over `G(δ)`). Symbolically, the tangent inequality `log g ≤ log ĝ + (g−ĝ)/ĝ` in sympy. **The safety property the whole architecture rests on — break this and U8 ships wrong bounds.** |
| 2 | **P1-band** — `V(π,σ) ≤ EG^bal_S(δ)` for every band-feasible integral coverage, every `ρ ≥ 0` under H3 | NUMERIC + SYMBOLIC | Exhaustion over all `k^n` coverages on an independent toy, compared against a *certified dual* value of `EG^bal` (not a solver's claimed primal). The `ρ > 0` leg: reuse `VERIFY_U1-cert` §2's `C_TV` exactness check with the band added. Attack the band step: search for a coverage that is band-feasible to within `1e-12` and exceeds the bound. |
| 3 | **P3-split** — `#splits ≤ k−1+t ≤ 2k−1`, and the `−1` unconditionally | SYMBOLIC | The dependency `D` in exact rationals: build `Σ`, `p`, `ν` symbolically on a small instance and check `D` is the zero row with zero RHS (sympy, `simplify == 0`, not `.equals()`). Then attack the *hypotheses*: construct an optimum with every agent band-tight and every `ν_i = 0`, and one with `δ = 0`, and check the count. Cross-check `|supp| ≤ n+k+t−1` by rank computation over `ℚ` on random instances. **The claim most likely to have a hidden hypothesis, because Step 1's `P'` is a polytope I chose.** |
| 4 | **P4.3 + P4.4** — the supergradient, and that only the minimised aggregate is quotable | SYMBOLIC + NUMERIC | Finite differences at `h = 10^{-4}…10^{-7}` against `s_min` on several instances; and an *adversarial* dual: exhibit an optimal dual whose `Σ(μ⁺+μ⁻)` exceeds `s_min` by an arbitrary amount at `δ = 0` and confirm the tangent bound is then vacuous. Concavity by chord test over a fine grid and by the convex-combination argument in sympy. |
| 5 | **P2.5** — the good-side rule, and the refutation of `DOMAIN_optimization` §2.12's ratio form | SYMBOLIC + NUMERIC | Derive `max_i(u_i/g_i − ν_i M_z) = p_z` from KKT in sympy; then search for the *smallest* counterexample to the ratio form, ideally at `ν ≡ 0` (unbanded), to confirm the error predates the band. **This one changes what U14 computes, so a wrong refutation is expensive.** |
| 6 | **P2.3 + P2.6** — the budget identities and the non-equilibrium | SYMBOLIC | The identities in sympy on a symbolic `n×k` instance (multiply-and-sum). For P2.6, an independent demand computation: solve `max{g_i(x) : p·x ≤ 1, x ≥ 0}` by LP and check its value strictly exceeds `g*_i` whenever `ν_i > 0`. |
| 7 | **P0** — Slater at every `δ ≥ 0`, including `δ = 0`, and strong duality there | SYMBOLIC | Check that a dual optimum exists at `δ = 0` by exhibiting `(p, ν)` with zero duality gap in exact arithmetic on a toy; confirm the *ordinary* Slater condition genuinely fails at `δ = 0` (so the refined affine version is doing work). |
| 8 | **P5.4** — a single tangent at `g*` makes the master exact, and its LP duals are the program's multipliers | SYMBOLIC + NUMERIC | First-order optimality `∇Φ(g*)·(g−g*) ≤ 0` symbolically; then compare HiGHS' master marginals against the independently-computed `(p, ν)` from the dual-feasibility LP. |
| 9 | **P0b** — `g*` unique; the split set not | SYMBOLIC | Strict concavity in sympy; numerically, many random objective directions over the optimal face. |
| 10 | **P4.1, P4.2, P4.5, P4.7, P4.8** — monotone, concave, kinks, envelopes, bisection | NUMERIC | Fine grids on several toys; explicit construction of a kink (`δ_c` = max deviation of the unconstrained optimum) and a two-sided derivative bracket. |
| 11 | **P5.5** — finite convergence REFUTED for the continuous master | SYMBOLIC (a non-theorem) | Confirm that **DuranGrossmann1986** / **FletcherLeyffer1994** as stated require a finite integer-assignment set; then exhibit an instance where the Kelley iterates approach `g*` without reaching it in `N` steps for arbitrary `N`. A refutation of *my* refutation would be a finite-termination proof, which would be a genuine result. |
| 12 | **P6-cells** — the `O(nk)` separating-cell certificate under the band | NUMERIC | Direct: evaluate `argmax_i(u_i(z)/g_i − ν_i M_z)` on every zip of a toy and compare against `supp(X*)`; confirm `O(nk)` by construction. The `borgwardt2019` half is `[conjectured]` and needs no verification beyond confirming the entry says what §3 says it says. |
| 13 | **P2.7** — the fairness reading | citation check, not proof | `LIT_economic-theory.md` A1-Q1's annotations for `echenique2021constrained` and `kawase2026balanced`. Confirm in particular that `kawase2026balanced`'s negative result is about *MNW over balanced allocations*, not about EF1's existence — this contradicts `DOMAIN_economic-theory` §2.8's table as written and the contradiction is the point. |

**Tolerance tiers used.** Tier 1 (`1e-8` nats) for every `EG^bal` value and bracket in §4; **exact**
(`0`) for the identities checked at `1e-13`–`1e-16` (float round-off only, no tolerance argument);
`1e-5` for the one-sided-derivative brackets, where the quantity being classified (kink / no kink)
is discrete. The toy2 kink at `6.95e-5` is *inside* tier 2 and would be invisible to a tier-2
test — deliberately kept, because it shows a kink's existence and its size are different
questions.

---

## 8. Open — what this unit could not settle

1. **Whether `s_min(δ₀)` on the real instance is below `2.33` or above `47.2` nats per unit `δ`.**
   That single number decides whether P4.6's one-solve certificate covers the whole grid or only
   the first grid point. It needs U8's first solve, which this unit was forbidden to wait for.
2. **An explicit iteration bound for P5.5(iv).** The reduction to Kelley's method in `k = 13`
   dimensions is proved; the classical bounds in that dimension are exponential and not worth
   quoting. If U8's loop needs a stopping guarantee rather than a bracket, this is the gap.
3. **`∂φ(δ)` equals the closure of the multiplier aggregates**, not merely contains it (P4.5's
   sketch). Nothing downstream needs it; a `math-verify` closure would let U8 report `[φ'_+, φ'_-]`
   from duals alone instead of from finite differences.
4. **Everything at `ρ > 0` beyond P1-band.** P2–P6 are `ρ = 0` statements and the KKT system
   changes with a `ρ Ĉ` term. The programme has no fractional `ρ` term today, so this is a
   boundary marker, not a defect.
5. **`borgwardt2019`'s normal-cone volume as a stability radius.** The entry's second half — the
   volume of the normal cone at a bounded-shape vertex as "how far can the data move before the
   partition changes" — is a structurally different route to `DOMAIN_optimization` §2.4's modulus
   and to U4-disp's displacement metric. Flagged, not pursued; it is not this unit's.
6. **`budish2013`'s bihierarchy test.** `LIT_optimization` §0 records that our band is a
   *weighted* per-agent constraint and therefore outside the bihierarchy class, so §2.13's
   325-binary rounding MIP is not avoidable by a decomposition theorem. I did not re-derive that;
   it is a citation and it bears directly on whether P3-split's `≤ 25` splits can be rounded for
   free. `math-verify` may wish to confirm the class membership claim.
7. **The real instance's `t`** — how many of the 13 agents are band-tight at the optimum — decides
   whether the split bound is nearer `12` or `25`, and whether the gauge of P2b is degenerate.
   One line off U8's first solve; deliberately not computed here.
