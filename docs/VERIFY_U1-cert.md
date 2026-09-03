# Verify — unit U1-cert — adversarial verification of `docs/MODEL_U1-cert.md`

**Date:** 2026-09-03 · **Verifier:** `math-verify` · **Track:** A1, branch `wt/A1` ·
**Verifies:** `docs/MODEL_U1-cert.md` (all of §2, §3, §4, and the §7 handoff table) ·
**Owns:** this file, `docs/artifacts/U1-cert/verify_*.py` ·
**Environment:** `/Users/ntlee/projects/td/.venv/bin/python3` (CPython 3.13.15), numpy 2.5.2,
scipy 1.18.1, sympy 1.14.0, mpmath (bundled), HiGHS via `scipy.optimize`. All commands from
`/Users/ntlee/projects/td/.claude/worktrees/A1`. No `cvxpy` in the venv — the second EG solver
is L-BFGS-B on a softmax parametrisation instead.

**There is no formal theorem prover in scope.** "Proved" below means machine-checked algebra
(sympy / exact rationals) plus a written argument, or an independent numeric oracle — not a
kernel-checked term.

---

## 0. Verdict summary

| # | proposition | verdict | artifact |
|---|---|---|---|
| 1 | **P1** — `V(π,σ) ≤ EG_S` for every integral coverage with `im σ = S`, every `ρ ≥ 0` under H3 | **VERIFIED** | `verify_props.py` |
| 2 | **P4 / headline** — `EG_{S₁₃} = 60.697415613859555`, bracket `7.1e-15`, `EG − V = 0.75994582` | **VERIFIED** (bracket *tighter* than claimed) | `verify_instance.py` |
| 3 | **P2.1** — `cert_balance_ceiling` is `D(p)` at `p_z = (k/T)M_z` | **VERIFIED** | `verify_props.py` |
| 4 | **P2.2** — the integer floor is *not* a degeneration of the dual | **VERIFIED, with one over-statement corrected** | `verify_props.py` |
| 5 | **P1c** — `EG_S ≤ k log(T/k)` under `u_i ≤ M_z`; same for `EG_R` | **VERIFIED as an implication**; its instance-side numbers are **coarser than the proposition** | `verify_props.py`, `verify_instance.py` |
| 6 | **P3a** — rank `n+k`; splits `≤ k`; "`≤ k−1` is a `τ=0` privilege" | **split verdict: rank claim VERIFIED, `≤ k` VERIFIED (but never attained), the interpretive claim REFUTED** | `verify_split.py` |
| 7 | **P3b / P3c** — the value bound and its a-priori vacuity | **VERIFIED**; §4.3's split-set numbers are **vertex-dependent, not instance invariants** | `verify_split.py` |
| 8 | **P2.4** — power weights are the EG multipliers, with the nondegeneracy caveat | **VERIFIED** (strengthened: dual optimality holds for *every* `ω>0`, in exact rationals); the "iff" is sound only in the `⇒` direction as a theorem | `verify_p23_p24.py` |
| 9 | **P2.3** — assignment at pinned centers is the ε-constraint integral restriction | **VERIFIED numerically**; one step of the "named specialisation" is a *substitution* of the balance functional, not a restriction | `verify_p23_p24.py` |
| 10 | **P1a / P1b** — H3's necessity and finiteness | **VERIFIED** (P1a strengthened to a non-constant convex extension) | `verify_props.py`, `verify_instance.py` |

**Brief acceptance:** P1 **VERIFIED**, P2 **VERIFIED** (three-of-four collapse confirmed, the
fourth's resistance confirmed), P3 at better than PLAUSIBLE — **VERIFIED with one refutation
inside it** (P3a's `≤ k` reading). The "what the bound does not cover" paragraph is checked in
§6 below.

**Two things the model should change.** (a) P3a §3's headline — "the lens's `[standard]`
`≤ |S|−1` is a `τ = 0` privilege; the honest heterogeneous statement is `≤ k`" — is **false**;
`≤ k−1` holds heterogeneously, and the claimed-new heterogeneous `≤ k` should not be carried
forward as a result pending citation. (b) The `+3.360`-nat `filler="full"` correction quoted in
§3, §4.4 and §5.1 is `k·log ν_max`, **not** the `Σ_{i∈S} log ν_i` that P1c actually states; the
sharp figure at `S₁₃` is `+0.2584` nats, and `max_S Σ_{i∈S} log ν_i` over all 111 reps is also
`0.2584`. The failure-mode sentence "the same order as the premium term" does not survive.

---

## 1. How to re-run

```
cd /Users/ntlee/projects/td/.claude/worktrees/A1
/Users/ntlee/projects/td/.venv/bin/python3 docs/artifacts/U1-cert/verify_instance.py   #  ~9 s
/Users/ntlee/projects/td/.venv/bin/python3 docs/artifacts/U1-cert/verify_props.py      # ~105 s
/Users/ntlee/projects/td/.venv/bin/python3 docs/artifacts/U1-cert/verify_split.py      #  ~50 s
/Users/ntlee/projects/td/.venv/bin/python3 docs/artifacts/U1-cert/verify_p23_p24.py    #  ~50 s
```

All four print `FAILURES: none` and exit `0`. They are **independent of the model's own
artifacts**: `verify_instance.py` rebuilds `u_i(z)` from the raw JSON columns of
`instance_descaled.json.gz` rather than through `td/instance.py`, recomputes `V(delivered)` by
hand from `draw.csv` rather than through `channel.gain_matrix`, and evaluates the EG primal and
dual with `math.fsum` and again at 50 mpmath digits. `verify_props.py` uses its own toy
(5 reps, 7 zips, `k = 3`, different graph, different books) and shares no code with `eg.py`.
No seed on the real instance affects any reported bound; the proportional-response run is
seeded (`seed=0`, randomised init, deliberately *not* the model's uniform init) purely to
produce a `(X, p)` pair whose bracket is then checked by arithmetic.

---

## 2. P1 — the relaxation bound · **VERIFIED**

**Statement verified.** Fix `S ⊆ R`, `|S| = k`, and an extension `Ĉ` of `C` to fractional `X`
with `Ĉ(X_π) ≤ C(π)` at every integral `X_π` (**H3**). Then `V(π,σ) ≤ EG_S` for every integral
coverage with `im σ = S`, at every `ρ ≥ 0`, with `log 0 = −∞`.

**Attack.** (i) The proof was re-derived from scratch, not read: `X_π` feasibility and the
identity `g_i(X_π) = u_{σ⁻¹(i)}(A_{σ⁻¹(i)})` were closed in sympy over *all* `2⁴` labellings of
a symbolic 4×2 instance (`simplify(lhs − rhs) == 0`, not `.equals()`). (ii) Exhaustion:
`C(5,3)·3⁷ = 21,870` coverages on an independent toy, each compared against the **certified
dual** `D(p) = Σ_z p_z − k + Σ_i log max_z(u_i(z)/p_z)` — not against a solver's claimed
optimum. Worst margin `−1.61e-3` at `ρ = 0`, `−2.69e-1` at `ρ = 0.05`. (iii) The one
instance-dependent step at `ρ > 0`, `Ĉ(X_π) = C(π)` for `C_TV`, was checked **exactly** (integer
arithmetic, max discrepancy `0.0`) over all `3⁷` labellings. (iv) The bound was attacked on the
real instance: a multi-restart local search over integral coverages on `S₁₃` reached
`60.695269`, `0.758` nats above the delivered draw and still `2.15e-3` *below* `EG_{S₁₃}` —
a search with teeth that failed to break the bound.

**Stop-rule check (the brief asks explicitly).** P1 needs **no** hypothesis the instance might
fail. It does not need `ρ = 0`, does not need concavity, and does not need `g_i > 0`. It needs
H3, which is a property of a modelling choice, not of the data. `DOMAIN_economic-theory.md`
§2.1 failure mode (i) is about the *axioms* of the maximiser and is correctly quarantined by
the model: the bound is a feasibility statement and survives `ρ > 0`. Confirmed.

**P1a (H3 is not decoration) — VERIFIED and strengthened.** The model's counterexample is a
constant shift `Ĉ = C_TV + c`, which is airtight but arguably degenerate. I built a
**non-constant, genuinely convex** violator: `Ĉ(X) = C_TV(X) + c·Σ_{z,i} x_zi²`. On integral
`X` the extra term is exactly `c·n > 0`, so H3 fails; and `max_X(A − B) ≤ max A − min B` with
`min_X Σ_{z,i} x_zi² = n/k` gives `EG_ρ(Ĉ) ≤ D(p) − ρcn(1 − 1/k)` with **no solver in the
trusted path**. At `c = 5.4394`, `ρ = 0.05` the toy's best integral coverage exceeds that upper
bound by exactly `1.000000` nats. H3 is load-bearing.

**P1b (finiteness) — VERIFIED.** Symbolically, `u_i(z) − λM_z = (1−λ)[(1−θ)S_i + θ(T_z + S_free)]
≥ 0`. On the instance `min_z M_z = 1.80577e-3 > 0` and `min_{i,z} u_i(z) = 1.047e-3 ≥ λ·min M_z`;
`u > 0` everywhere over `S₁₃`, so `EG_{S₁₃} ∈ ℝ` and no starvation guard is needed.

---

## 3. P4 / the headline numbers · **VERIFIED**

The certificate is self-witnessing in the right way: what is reported is a pair `(X, p)` and
two `O(nk)` evaluations, so no trust in proportional response is required. I rebuilt both
evaluations and checked feasibility of `X` rather than assuming it.

| quantity | model | this verification | tier |
|---|---|---|---|
| `T = M(Z)` | `2745.611187` | `2745.61118735` | exact |
| `k log(T/k)` | `69.5865251441` | `69.58652514411666` | exact |
| `V(delivered)` | `59.9374697984` | `59.93746979843285` (hand-recomputed from `draw.csv`) | `Δ = 0.0` vs `metrics.json` |
| `EG_{S₁₃}` primal | `60.6974156139` | `60.697415613859555` | tier 1 |
| `EG_{S₁₃}` dual | `60.6974156139` | `60.69741561385956` | tier 1 |
| bracket width | `1.279e-13` | **`7.11e-15`** (fsum), `3.62e-15` (mpmath, 50 dps) | tier 1 |
| `EG − V` | `0.7599458154` | `0.7599458154267` | tier 1 |
| `k log(T/k) − EG` | `8.8891095303` | same | tier 1 |
| tightness factor | `12.6970` | `12.697031` | tier 1 |
| `M`-spread / `g`-spread delivered | `0.7813 %` / `60.65 %` | same (`ratio 77.63`) | tier 1 |
| `min_i g_i` delivered / at EG | `81.869` / `103.617` | `81.868680` / `103.617149` | tier 1 |

**Attack.** `X` was checked for nonnegativity and row sums (`max|rowsum−1| = 4.4e-16`), `p` for
strict positivity (`min p = 1.74e-5`); the dual formula was independently re-derived (Lagrangian
on the supply rows; each agent's inner problem is `max_{s≥0} log(r_i s) − s = log r_i − 1`).
Both sides were then recomputed at 50 decimal digits to rule out a float-summation artefact —
the bracket **narrows** to `3.6e-15`, so the claimed `1.3e-13` is conservative rather than
optimistic. A second, structurally different solver (L-BFGS-B on a softmax parametrisation,
15,977 variables) lands at `60.695740`, inside the bracket from below.

Derived thresholds re-checked: `EG_R` useful below `V + 3.7 = 63.6375`; `M(F)` swamps the
premium at `g_min(1 − e^{−3.7}) = 101.0554` (`3.681 %` of `T`); `(EG−V)/3.7 = 20.539 %`. All
agree.

---

## 4. P2 — the collapse · **VERIFIED (three of four; the fourth resists)**

### P2.1 · VERIFIED
Symbolic, on `n = 4` symbolic masses with symbolic `λ`: `Σ_z p_z = k` exactly at
`p_z = (k/T)M_z`; `u_i(z)/p_z ≡ λT/k` (a single value, so the max is that constant);
`D(p) = k log(λT/k)`; attained by `x_{zi} = 1/k`. Numerically at `λ = 1`, `D(p)` equals
`cert_draw.cert_balance_ceiling(...)["ceiling_nash"]` to `0.0`, and proportional response's own
optimum agrees to `1.8e-15`. The ceiling **is** the EG dual at prices proportional to
opportunity, checkable in `O(n)`.

### P2.2 · VERIFIED, with one over-statement corrected
I rebuilt the *implemented* model (`cert_draw.cert_integer_balance_floor`, lines 405–445) as a
pure LP — including **both** symmetry breaks, which was the obvious way it could fail: fixing
the heaviest zip into district 0 and forcing districts `1..k−1` non-increasing could in
principle push the relaxation off `t = 0`. It does not: the LP optimum is `t = 0.0` with every
district exactly on target (`max dev 3.6e-15`). So the LP dual value is `0` and the root bound
certifies nothing. A certificate whose LP dual is identically `0` is not a degeneration of a
dual that is not — **the model's headline claim stands.**

The nat conversion is proved, not asserted: `−log(1+δ) = −δ + δ²/(2(1+ξ)²)` (Lagrange
remainder, checked against the series in sympy), `(1+ξ)² ≥ (1−ε)²` for `ξ ≥ −ε`, and `Σδ_j = 0`,
giving `k log(T/k) − max_π Σ_j log m_j ≤ k ε²/(2(1−ε)²)`. No violation in 400k random `(δ, ε)`
draws (`max excess 3.4e-17`), and the summed form holds by exhaustion over all `3⁷` toy
partitions (`5.58e-4 ≤ 1.19e-3`).

**Correction.** §3 P2.2's sentence "so it carries **no dual bound at all**" is too strong. When
the MILP *closes*, branch-and-bound does return a valid lower bound on `t*`: on the toy,
`cert_integer_balance_floor` returns `proved=True` with `t_lower = 0.6667 > 0`. The accurate
statement is the one the rest of the paragraph makes — its **LP relaxation / root bound** is
vacuous, which is what rules out its being a degeneration of a linear dual. Note also that `t*`
*is* a valid lower bound on every partition's `max_dev`, i.e. it bounds from the outside in
balance space; the model's "primal / achievability" reading is the useful one but is a reading,
not the only one. Neither point disturbs the conclusion.

### P2.3 · VERIFIED numerically; one word in the specialisation chain is wrong
Own toy (9 zips, `k = 3`, own coordinates and centers), own brute force over all
`3⁹ = 19,683` integral assignments inside the same max-deviation band: the MILP's `opt_cost`
equals the brute-force optimum exactly (`Δ = 0.0`), `proved=True`, and trap 12 is honoured
(`mip_rel_gap == 0.0`, confirmed on the returned dict).

**Caveat.** The chain "`τ=0`; `ρ>0` linear penalty; centers pinned; **the log-balance term
traded for an ε-constraint band**; integrality reimposed" contains one step that is not a
restriction: a max-deviation band is not a sublevel set of `Σ_j log m_j`, so
`{|m_j − T/k| ≤ δ}` is neither contained in nor contains the log-balance level set. The model
says as much two paragraphs later ("the band is a *strictly larger* feasible set than mass
equality, so its optimum and `cert_power_diagram`'s bound are not comparable in either
direction"), so this is an internal wording tension, not an error — but "restriction, by a named
triple specialisation" over-sells one of the three steps.

### P2.4 · VERIFIED, and strengthened
The KKT derivation was redone symbolically: dividing stationarity by `M_z > 0` turns
`M_z/m_j − ρM_z d²(z,c_j) ≤ α_z` into `argmax_j (1/m_j − ρ d²) = argmin_j (d² − ω_j)` with
`ω_j = 1/(ρ m_j)` — a power diagram of the pinned centers.

I then **strengthened** the dual-optimality half. The model checks it at one toy optimum with a
`3.1e-15` residual; in fact it is an identity requiring no optimisation at all. For *any*
`ω > 0`, let `X(ω)` be the power-diagram assignment and `m(ω)` its masses, and set
`α_z := M_z min_j(d²(z,c_j) − ω_j)`. Then `(α, ω)` is dual feasible for the transportation LP at
targets `m(ω)`, complementary slackness holds on `supp X(ω)`, and the dual objective equals the
primal cost. Verified in **exact rational arithmetic** (`fractions.Fraction`) on 200 random
instances: min dual slack `0`, max CS residual `0`, max `|dual − cost|` `0` — all exactly zero,
no tolerance involved. `ω = 1/(ρm*)` is then one instance of this.

**The nondegeneracy caveat reproduces, and it is the right caveat.** Across 23 genuine fibre
optima (`m*` obtained by an outer nested-grid refinement over the mass vector with `F(m)` from
an exact transportation LP — independent of the model's mirror ascent): 13 nondegenerate
(support `= n+k−1`) with `max_j |ρβ_j − 1/m*_j − mean| ≤ 3.4e-9`, and 10 degenerate with spreads
from `2.3e-5` to `7.5e-2`. In every degenerate case `power_weights`' `lp_bound` still equalled
the LP cost (`≤ 5.2e-7`), so **the bound is sound in both cases and only the interpretation
fails** — exactly as the model says.

**One logical caveat on the "iff".** `nondegenerate ⇒ identity` is a theorem (the dual is
unique, so HiGHS' `β` must be *the* multiplier). The converse — `degenerate ⇒ HiGHS returns a
different dual` — is not: primal degeneracy permits dual multiplicity but does not force HiGHS
off the EG multiplier. I searched for a degenerate optimum where the identity nevertheless
holds and found none in 10 cases, so the "iff" is not refuted here; but it is asserted beyond
what is proved, and the operationally correct form is the one §5.5 already uses: *the
identification is guaranteed only when `support = n + k − 1`, so check the support before
reading `β` as prices.*

---

## 5. P1c and P3 · one implication over-quoted, one interpretation refuted

### P1c · VERIFIED as an implication; its quoted numbers are the coarse form
Both Jensen steps close. Step 1 (`g_i ≤ m_i`, `Σ_i m_i = T`, `Σ log g_i ≤ k log(T/k)`) is
verified symbolically for the mass identity and by 400k random draws for the concavity step
(max excess `−2.1e-9`, i.e. no violation). Step 2 — the perspective form
`Σ_i y_i log c_i ≤ k log(Σ_i y_i c_i / k)` at `Σ y_i = k`, `y ∈ [0,1]^R` — is Jensen with
weights `y_i/k`; sympy confirms equality and a maximum at `c_1 = c_2` for `k = 2`
(`∂²/∂c₁² = −y₁(k−y₁)/(k c₁²) < 0`), and 200k random `(y, c)` draws over `R` up to 40 find no
violation. On the toy, `EG_S ≤ k log(T/k)` for all 10 staff sets.

**The problem is the numbers, not the proposition.** P1c's corrected form is
`EG_S ≤ k log(T/k) + Σ_{i∈S} log ν_i`. §3, §4.4 and §5.1 attach `+3.360` nats to it at
`filler="full"`. That figure is `k·log ν_max = 13 × log 1.2948988`, the *uniform* coarsening —
the proposition's own `Σ_{i∈S} log ν_i` at `S₁₃` is **`+0.258438`** nats, and the maximum over
all `C(111,13)` staff sets (top-13 `log ν_i`) is also `0.258438`. So §5.1's "larger than the
premium term" and §3's "the same order as the premium term the certificate exists to bound" are
wrong by a factor of 13: the sharp correction is `0.26` nats against a `3.7`-nat premium. The
same coarsening applies to the `filler="theta"` row (`5.46e-6 = k log ν_max`; the sharp value is
negative, `−6.59e-2`, because most `ν_i < 1`). Both coarse figures are valid upper bounds — the
claim is sound, the *reading* of it in the failure-mode section is not. Independently confirmed:
strong headroom `u_i(z) ≤ M_z` **fails** on the instance at `filler="theta"` too, by
`4.200e-7` relative on 69 zips, exactly as §5.2 records.

### P3a · **REFUTED in its interpretive half**
Three separable claims:

1. *rank(A) = n+k in general, `n+k−1` exactly when the `u_i` are mutually proportional.*
   **VERIFIED** for the matrix `A` as written — 300 random positive heterogeneous instances all
   give `n+k`, 300 proportional ones all give `n+k−1`, and a 200k-trial search for a positive
   non-proportional instance with rank `n+k−1` found none. The left-null-space argument was
   redone. **One unstated hypothesis:** the "iff" needs `u_i ≢ 0` — `u_1 ≡ 0` with the other
   columns non-proportional also gives rank `n+k−1` (exhibited). On this instance P1b discharges
   it, so this is a statement-hygiene point, not a defect.

2. *"Hence a vertex optimum splits at most `k` units in general."* **VERIFIED as a valid bound**
   (support of a basic solution `≤ rank`, each unit has `≥ 1` entry). But it is **never
   attained**: 250 random heterogeneous instances (`n` up to 10, `k` up to 5) plus 400 more on
   the toy produced a maximum of exactly `k−1` splits for every `k`, and no counterexample.

3. *"The lens's `[standard]` `≤ |S| − 1` is a `τ = 0` privilege; the honest heterogeneous
   statement is `≤ k`."* **REFUTED.** `A` is not a minimal description of the optimal face.
   Take any vertex `X` of `P`; it is an EG optimum, so it has KKT prices `p` and satisfies
   `supp(X) ⊆ MBB(p)`, `Σ_i x_zi = 1`, `Σ_z p_z x_zi = 1`. Let `P'` be the polytope those three
   conditions define; every point of `P'` is an equilibrium allocation, hence an EG optimum,
   hence `P' ⊆ P`, and `X ∈ P'`, so `X` is a vertex of `P'` too. In `P'` the two constraint
   families are linearly dependent — `Σ_z p_z·(supply row z) − Σ_i (budget row i) = k − Σ_z p_z`
   contains no `x` and vanishes because every good is sold and every budget spent (checked in
   sympy) — so `rank ≤ n + k − 1` and `X` has at most `n + k − 1` nonzeros: **at most `k − 1`
   split units, heterogeneous or not.** This is the standard transportation/forest argument. On
   the real instance the vertex support is `1240 = n + k − 2` edges over `2` components, a
   forest, well inside `n+k−1 = 1241`.

   Consequence for the model: `brieden2017 Lem. 4`'s `≤ k−1` is **not** a common-measure
   privilege, the `≤ k` heterogeneous statement is not new and not needed, and §8 open item 4
   ("the `≤ k` heterogeneous split-unit bound's provenance") should be closed as *not a result*
   rather than left for U0-lit. Nothing else in the unit depends on it: §4.3 and P3c already use
   `k − 1 = 12`.

### P3b · VERIFIED
`g_i(rounded) ≥ g*_i − L_i` verified by construction on the toy (min slack `0.0`); `Σ_i L_i ≤
M(F)` verified on the instance (`33.456 ≤ 87.659` at my vertex); the concentration step
(`−log(1−·)` convex and increasing, so `−Σ log(1−ℓ_i)` at `Σℓ_i ≤ s` is maximised at `s·e_i`,
value `−log(1−s)`) closed symbolically for the derivatives and checked over 300k random draws
with no violation. The chain `realised ≤ per-agent ≤ M(F)-form` holds at both my vertex and the
model's.

### P3c · VERIFIED, with a reproducibility finding
`M(F)_worst = 249.3919` (12 largest zips, `9.083 %` of `T`) against `g_min = 103.617149` gives
ratio `2.4069 > 1`, so the a-priori bound is `+∞` — **the `≤ k−1` count is not quotable without
the split masses.** Confirmed exactly.

**But §4.3's split-set numbers are not instance invariants.** The optimal face has many
vertices, and which one a simplex lands on is solver-path dependent. My independent run (same
`g*` to `7e-14`, same `EG` to `1e-13`) returns a *different* split set of the same size:

| | model (`instance_numbers.py`) | this verification |
|---|---|---|
| `|F|` | `10` | `10` |
| split zips | `07059 07901 11230 21401 27408 45236 55391 84111 92020 92614` | `11230 21401 22102 33301 55110 63103 70005 84111 92130 92614` |
| `M(F)` | `66.168107` (`2.410 %`) | `87.658450` (`3.193 %`) |
| P3b per-agent | `0.244765` | `0.322685` |
| P3b `M(F)`-form | `1.017722` | `1.870699` |
| realised gap | `5.131e-4` | `1.919e-3` |
| `V(rounded)` | `60.6969024656` | `60.6954967680` |
| rounded `M`-spread | `54.21 %` | `58.97 %` |

The model's own script reproduces its numbers exactly (re-run and confirmed), so this is not an
arithmetic error — it is a **quotation hazard**: §4.3's `M(F) = 66.168`, `0.2448`, `5.131e-4`
and `54.21 %` are properties of one vertex, and any of them quoted as "the" value will not
survive a re-solve. The invariants are `|F| ≤ k−1`, `M(F) < g_min` (so the realised bound is
finite), the direction of the chain, `max dev 33.00 %`, and the qualitative claim that the
rounded EG optimum abandons balance (`≥ 50 %` `M`-spread on both runs). P4's headline sentence
"rounding the EG vertex realises `0.7594` of it constructively" should be quoted as `≈ 0.758`
or with the vertex named.

---

## 6. What the bound does not cover — checked

The model's paragraph is accurate and I have nothing to add to its content, only a confirmation
that the two exposures it names are structurally invisible to everything computed here.
`EG_S − V` prices the *drawing and the assignment at fixed reported inputs*, nothing else.
**Misreporting:** `u_i(z)` is affine and strictly increasing in the self-reported book `S_i(z)`
with coefficient `c1 − c2 = 0.42`, so an inflated book raises `g_i`, raises rep `i`'s
bang-per-buck `u_i(z)/p_z` on the inflated zips, and moves the fibre optimum toward them; the
primal, the dual and the bracket all remain internally consistent on the inflated input, so
nothing in this unit detects it (FRAME A7 / §10 Q5). **Error in `M`:** every object here — the
ceiling `k log(T/k)`, the prices `p_z`, the gains, the split masses, the gap — is a functional
of `M`; the scale-invariance the programme relies on means a *global* rescale is free, but a
*regional* bias in `M` shifts the certificate and the thing it certifies in the same direction
and is undetectable from inside (FRAME A4). Neither is reduced by the collapse. I add one
exposure the model does not list: the gap is quoted at the **delivered roster** `S₁₃` only, and
`max_S EG_S` is unbounded above by anything computed here except the ceiling — so "no map is
worth more than `0.760` nats above the one that was drawn" is conditional on the roster, which
§6 states but §0's headline does not.

---

## 7. Open / not covered by this verification

1. **`max_S EG_S` and `EG_R`** were not computed here either; the model's own §8.1 bracket
   `[60.697416, 69.586525]` is all that is available and I confirm both endpoints.
2. **`EG^bal_S`** (the balance-constrained fibre) is untouched; the bracket `[59.9375, 60.6974]`
   is a restatement of P1 plus the delivered value and needs no verification beyond §3.
3. **`ρ`-aware fibres on the real instance** — nothing computed, by the model's own admission.
   P1 at `ρ > 0` is verified as a theorem and on the toy only.
4. **The `≤ k−1` count's citation.** My §5 argument is the standard linear-Fisher-market /
   transportation forest argument and should be cited, not re-proved, when U0-lit runs; but the
   claim to be cited is `≤ k−1`, not `≤ k`.
5. **Convention.** Everything above is in the **unmasked** convention (`channel.gain_matrix`),
   as the model specifies. Under `model.utilities` a rep with no candidacy anywhere in a
   district has `g_i = 0` and `EG_S = −∞`; nothing here was checked in that convention.
6. **Tolerance tiers used.** Tier 1 (`1e-8` nats) for every headline number in §3 and for the
   nondegenerate `ρβ_j − 1/m*_j` identity; **exact** (integer or rational arithmetic, tolerance
   `0`) for H3 on integral points, for the P2.4b dual-feasibility/CS/objective triple, and for
   the sympy identities; `1e-6`–`1e-3` for the grid-solved fibre optima in P2.4c, where the
   quantity being classified (degenerate vs not) is discrete and the residual only has to
   separate `1e-9` from `1e-3`. The instance's `4.2e-7` headroom violation sits above tier 1 and
   below tier 2 (`5e-3`), so no tier-1 claim about the ceiling as a bound on `V` is supported by
   the data as exported — the model already says this and I confirm it.
