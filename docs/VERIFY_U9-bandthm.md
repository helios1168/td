# Verify — unit U9-bandthm — adversarial check of the five claims `EG^bal_S(δ)` rests on

**Date:** 2026-09-04 · **Track:** A1, branch `wt/A1` · **Unit:** `docs/units/U9-bandthm.md` ·
**Under test:** `docs/MODEL_U9-bandthm.md` and `docs/artifacts/U9-bandthm/bandthm.py` ·
**Owns:** this file, `docs/artifacts/U9-bandthm/verify/**` ·
**Did not touch:** `docs/MODEL_U9-bandthm.md`, `docs/MODEL_U8-band.md`, `td/`, `tests/`, `tools/`,
`docs/FRAME.md`, `docs/BRIEF.md`, `docs/APPROACHES.md`, `docs/LENS_*`, `docs/DOMAIN_*`, `docs/LIT_*`.

**Headline.** All five brief-mandated propositions pass, and every expansion of them passes, with
**four corrections to report and one new hazard the model did not name**:

1. **P3-split's `≤ k−1+t` is real but is a *numerically fragile* count.** It is attained (min slack
   0 on 64 of 440 adversarial vertices), so the regime where it binds is exactly the regime where a
   support threshold set below the LP solver's dirt (1e-7…1e-9) manufactures phantom splits. With a
   1e-9 threshold I produced 108 apparent violations of the *sharp* bound out of 517 vertices; every
   one of them dissolved on cleaning. **U8 must clean-and-recertify the returned vertex before
   counting splits.** The mathematics is unharmed — the `−1` dependency `D` is exactly zero in
   rationals under every hypothesis I could strip.
2. **`s_min` is more fragile than §2 says, in a direction that breaks P4.6.** The model says the
   aggregate `Σ(μ⁺+μ⁻)` must be minimised. True, and I confirm it — but I also find that at `δ = 0`
   **`Σ_i|ν_i|` is *itself* gauge-dependent** (an arbitrary optimal dual gave `5.102` where the
   gauge-reduced value is `0.3115`, a factor 16.4), and that **an `ε`-relaxed minimisation over the
   dual-optimal set biases `s_min` downward and produces an *invalid* supergradient**: at
   `ε ∈ {1e-3, 1e-4, 1e-5}` the tangent bound `φ(δ') ≤ φ(0) + s_min·δ'` is violated by up to
   `9.9e-4` nats. §6's "one extra small LP" is not safe as stated.
3. **P2.5's refutation of `DOMAIN_optimization` §2.12 is correct, and admits a far smaller
   counterexample than the model's** — `n = 1` zip, `k = 2` agents, `M = [1]`, `u = [[2],[1]]`,
   `ν ≡ 0`, integer data, exact arithmetic. The published rule is false in one line.
4. **A citation slip in P1b-band.** A1's `docs/LENS_GROMOV.md` M8 (line 58) **already**
   writes the sandwich at `δ₀`, not at `0.0078`; the model describes M8 as if it still wrote
   `EG^bal_{S₁₃}(0.0078)`. The `0.0078` misplacement is real but lives in M8's U13/M12 grid
   (lines 118, 121, 155, 271) and in `DOMAIN_economic-theory` §2.8 line 440 and N7 line 739. The
   recommendation ("grid from `0.0039`") stands unchanged.

The model's own §4 reproduces: `bandthm.py` reruns to `FAILURES: none` in ~110 s, and every table in
§4.0–§4.8 matches. One number does not reproduce independently — see §8.

---

## 0. Method, and why it is independent

The model solved `EG^bal_S(δ)` with a scipy/HiGHS outer-approximation loop and read its multipliers
from a KKT LP built on that same primal. Re-running it would only reproduce its own bugs. So:

| | model | this verification |
|---|---|---|
| primal | scipy `linprog` (HiGHS) OA loop + SLSQP polish | **SCIP 10 / pyscipopt 6.2.1**, native `log` in the expression graph |
| dual | KKT LP on the model's own primal support | a **separately derived** closed-form Lagrangian dual, solved as its **own** convex program in SCIP; no primal support used |
| value | the solver's number | a **rigorous bracket** `L ≤ EG^bal_S(δ) ≤ U`: both endpoints come from points repaired to **exact rational feasibility** (`fractions.Fraction`) and evaluated in 60-digit `mpmath` |
| identities | float residuals at 1e-13 | **sympy**, `simplify(...) == 0` in exact rationals |

The dual, re-derived from scratch (`docs/artifacts/U9-bandthm/verify/oracle.py` docstring):

```
D(p, μ⁺, μ⁻) = Σ_i [ log( max_z u_i(z)/q_{zi} ) − 1 ] + Σ_z p_z
               + (T/k)[ (1+δ) Σ_i μ⁺_i − (1−δ) Σ_i μ⁻_i ],     q = p + ν M > 0
```

and, with `s_i := 1/max_z(u_i(z)/q_{zi})`, `s_i u_i(z) ≤ q_{zi}` is **linear**, so the dual is itself
a concave program. `D` at *any* feasible `(p, μ)` is a valid upper bound by weak duality; `Σ log g_i`
at any feasible `X` is a valid lower bound. Both endpoints are re-checked in exact rationals before
being quoted, so the bracket is a certificate, not a solver claim. Observed widths: `6.3e-10` to
`3.2e-7` on the fixtures used.

**Fixtures.** All built **unmasked** (`td/channel.py::gain_matrix` convention), rebuilt from the raw
numbers rather than imported: the `MODEL_U7-meas` §4 fixture (pinned — `g` matrix reproduces to
`0.00e+00`, `V = 6.178804`); a heavy-zip toy (`k=2, n=6`) that makes the band bind; **my own**
`k=3, n=8` instance at seed `424242` (a different shape and seed from the model's toy2); and
118–240 random adversarial instances (`n ∈ [4,10]`, `k ∈ [2,5]`, uniform / log-normal / one-huge-zip
`M`, `δ ∈ {0, 1e-4, 0.01, 0.05, 0.15, 0.5}`).

**Artifacts** (all under `/Users/ntlee/projects/td/.claude/worktrees/A1/docs/artifacts/U9-bandthm/verify/`):

| file | what it runs | result |
|---|---|---|
| `sym.py` | the symbolic leg: tangent inequality, `P0b`, `P2.3`, `P2.5`, `P3`'s dependency `D`, `P4.2`, `P4.3/P4.4`, `P5.4` + its converse, `P0` at `δ = 0` in exact rationals | `SYMBOLIC FAILURES: none` |
| `oracle.py` | the independent SCIP primal, the independent SCIP dual, and the exact-rational bracket | library |
| `num.py` | the numeric leg: `P0, P0b, P1, P1a, P1c, P2.1–2.6, P2b, P3, P4.1–4.7, P5.1–5.6, P6` | `NUMERIC FAILURES: none` |
| `p3_probe.py` | dissects every apparent `P3` violation (optimality, vertex-ness, `t` at four thresholds, rank) | diagnostic |
| `p3_attack.py` | `P3` on **cleaned, re-certified** vertices + the dependency test on 118 instances | `P3 FAILURES: none` |
| `smin.py` | `s_min` recomputed independently; the gauge reduction; the `ε`-conditioning sweep | see §7 |

Re-run (from the worktree root, `cd docs/artifacts/U9-bandthm/verify` first for the numeric ones):

```
/Users/ntlee/projects/td/.venv/bin/python3 docs/artifacts/U9-bandthm/verify/sym.py
cd docs/artifacts/U9-bandthm/verify && /Users/ntlee/projects/td/.venv/bin/python3 -W ignore num.py
cd docs/artifacts/U9-bandthm/verify && /Users/ntlee/projects/td/.venv/bin/python3 -W ignore p3_attack.py
cd docs/artifacts/U9-bandthm/verify && /Users/ntlee/projects/td/.venv/bin/python3 -W ignore smin.py
```

Environment: CPython 3.13.15, numpy 2.5.2, scipy 1.18.1, sympy 1.14.0, mpmath 1.3.0 (`dps = 60`),
pyscipopt 6.2.1 (SCIP), HiGHS via scipy. Seeds, all explicit: my toy `424242`, `P3` vertices `2024`,
`P3` ensemble `5150`, `P5` cut sets `31337`, `P0b` `11`, `P1` `ρ`-leg `7`.

---

## 1. Verdict table

| # | proposition | verdict | basis |
|---|---|---|---|
| P0 | Slater / strong duality at **every** `δ ≥ 0`, incl. `δ = 0` | **VERIFIED** | exact zero gap in rationals at `δ=0`; brackets close to `≤1.1e-8` at `δ ∈ {0, .005, .05, .4}` on 3 instances |
| P0b | `g*` unique, split set not | **VERIFIED** | strict concavity symbolic; `max|Δg*| = 7.1e-15…1.2e-8` over 40 vertices, 4–5 distinct split sets |
| **P1-band** | `V ≤ EG^bal_S(δ)` for every band-feasible integral coverage, every `ρ ≥ 0` under H3 | **VERIFIED** | exhaustive `k^n` (16 + 64 + 6561) × 5 `δ`, against a **certified** `U ≥ φ`; max `(V − U) = −3.5e-10` |
| P1a-band | the band hypothesis is load-bearing | **VERIFIED** | independent witness, `+2.578e-02` nats above `U` at `δ = 0` |
| P1b-band | monotone chain; left endpoint at `δ₀` | **VERIFIED** (citation slip, §8) | monotonicity verified; `δ₀ = 0.0039` is FRAME §0/§6's own number |
| P1c-band | the bound can be true and empty | **VERIFIED** | exact: min over all 64 coverages of max deviation `= 1/9` exactly |
| P2.1 | stationarity, equality on `supp` | **VERIFIED** | symbolic + `≤1.05e-9` on my duals |
| P2.2 | `q > 0` always; `p > 0` needs `δ > 0` | **VERIFIED**, hypothesis shown **necessary** | at `δ=0` my independent dual has `min p = −1.2056` |
| P2.3 | budget identities | **VERIFIED** | symbolic residual **exactly 0** on a symbolic `n=4, k=3` instance |
| P2.4 | agent-side MBB | **VERIFIED** | `max_z u/q = g*` to `1.7e-7` |
| **P2.5** | corrected good-side rule; §2.12 **REFUTED** | **VERIFIED — refutation confirmed and sharpened** | exact `n=1, k=2` counterexample at `ν ≡ 0` |
| P2.6 | not a CE at the stated budgets | **VERIFIED** | **independent demand LP**: `ν>0` agent's demand `31.55 > g* = 27.91`; `ν<0` agent spends `1.138 > 1` |
| P2.7 | fairness reading | **VERIFIED as a citation check**, one over-reach (§6) | annotations at `LIT_economic-theory` 821–835, 889–900 |
| P2b | the multiplier gauge | **VERIFIED** | `δ=0`: `D` invariant over `c ∈ [−5,5]`; `δ>0` + slack agent: every `c ≠ 0` strictly worse |
| **P3-split** | `#splits ≤ k−1+t ≤ 2k−1`, `−1` unconditional | **VERIFIED** (with a counting warning, §5) | `D ≡ 0` in exact rationals under 4 stripped hypotheses; 440 certified-clean vertices, min slack 0 |
| P3a-split | inherited from `MODEL_U1-cert` P3c | not re-derived | cited, consistent |
| **P4.1–P4.3** | monotone, concave, supergradient | **VERIFIED** | conservative chord/tangent tests against certified brackets |
| **P4.4** | aggregate non-unique and unbounded at `δ=0` | **VERIFIED and strengthened** | `D` unchanged to `1e-10` while the aggregate reaches `1.8e8`; **and `Σ|ν|` is itself gauge-dependent at `δ=0`** |
| P4.5 | one-sided derivatives, kinks | **VERIFIED**; refutes the *brief's* equality form | two kinks exhibited with certified `D⁺ < D⁻` |
| P4.6 | one-solve softness certificate | **VERIFIED**, with a new precondition (§7) | valid at every grid pair; **invalid if `s_min` is computed with a loose tolerance** |
| P4.7 | two-sided envelope from a grid | **VERIFIED** | chord lower envelope, max violation `−2.4e-8` |
| P4.8 | bisection licensed by monotonicity alone | **VERIFIED** | follows from P4.1 |
| **P5.1** | every master optimum `≥ EG^bal_S(δ)` | **VERIFIED** | symbolic tangent + **SCIP** LP master, 120 cut sets incl. `ĝ = 1e-4·g*` and `1e4·g*`, min `(MP − U) = −4.5e-10` |
| P5.2 | monotone in the cut set | **VERIFIED** | nested cut sets, non-increasing |
| P5.3 | `ĝ > 0` with explicit constant | **VERIFIED** | symbolic from the model formula |
| P5.4 | one well-placed cut is exact | **VERIFIED**, and its **converse proved** (new) | `MP` lands inside the certified bracket; converse closes P5.5's gap |
| **P5.5** | finite convergence **REFUTED**, restated | **VERIFIED — the refutation stands, and is not an evasion** | citation reading correct; converse of P5.4 supplied; 250-iteration independent Kelley run, 0 exact hits |
| P5.6 | what breaks validity | **VERIFIED** | a cut set missing one agent leaves the master unbounded |
| P6-cells | `O(nk)` separating-cell certificate under the band | **VERIFIED** (direct half) | `supp ⊆ argmax_i f_i`, `max_i f_i = p_z` to `1.0e-9`, `f = W·lift` exactly |
| P6-cells | the `borgwardt2019` half `[conjectured]` | **PLAUSIBLE** | matches `LIT_optimization` §8's annotation verbatim; paper not read; the model's downgrade to "corroborating" is endorsed |

---

## 2. P5.1 — the safety property (priority target 1)

**Attack.** (a) Symbolic: is `log ĝ + (g−ĝ)/ĝ − log g ≥ 0` for all `g, ĝ > 0`? Encoded in sympy;
derivative `1/ĝ − 1/g`, unique stationary point at `g = ĝ`, second derivative `1/g² > 0`, value `0`
there, `→ +∞` at both ends — so a strict global minimum of `0`. Cross-probed on a 108×98 grid of
rationals: `min = 0.000e+00`. `ĝ > 0` is necessary (`log ĝ` is not real otherwise).
(b) Numeric, with a solver the model never used: the master `MP(𝒞)` as a **pure LP in SCIP**,
against the **certified upper** bound `U ≥ φ` (so a violation would be `MP < φ ≤ U`, and I measure
`MP − U`). 60 cut sets per fixture, deliberately including the numerically nastiest placements:
`ĝ = 1e-4·g*` (huge tangent gradient `1/ĝ`) and `ĝ = 1e4·g*` (near-flat), 1–3 cut points, and one
set containing the exact `g*` plus noise.

**Result.** `min (MP − U) = −4.520e-10` (heavy-zip toy, bracket width `2.87e-07`) and `−9.412e-09`
(my `k=3` toy, bracket width `9.63e-09`). No cut set ever produced a master value below the certified
bound. The hypothesis **"at least one cut per agent" is load-bearing**: drop one agent's cut and the
master is unbounded, not a bound — so P5.6's discipline has teeth.

**VERDICT: VERIFIED.** U8's number is a certificate, not a heuristic, *provided* the master is solved
to optimality (P5.6) — a `time_limit` stop, a nonzero `mip_rel_gap`, or a truncated incumbent is not.

---

## 3. P1-band (priority target 2)

**Attack.** (a) The wrong-convention trap was pinned first: the `MODEL_U7-meas` §4 `g` matrix
reproduces to `max|Δg| = 0.00e+00` and `V(D1→A, D2→C) = 6.178804`, so every `u` used here is the
unmasked `gain_matrix` object. (b) All `k^n` coverages enumerated on three fixtures — 16, 64 and
**6561** — at five `δ` each, band feasibility tested at `1e-12`. (c) Compared against a **certified**
upper bound on `φ`, not a solver primal, so a `V > U` would refute outright. (d) Coverages
band-feasible *only* to within `1e-12` searched for separately (none exist on these fixtures — the
integral masses are far from the band edges; reported rather than hidden). (e) The `ρ > 0` leg: the
one step the band adds is `m_i(X_π) = M(A_{σ⁻¹(i)})`, checked as an **exact rational identity** over
2000 random coverages — 0 mismatches. The `ρ` term itself is `MODEL_U1-cert` P1's H3, already
VERIFIED in `VERIFY_U1-cert` §2, and the band does not touch it.

**Result.** `max (V − U) = −3.5201e-10` (heavy-zip), `−6.33e-10` (U7 toy), `−1.479e-02` (my toy).
On the U7 and heavy-zip fixtures the best band-feasible integral coverage *attains* `φ` — the bound
is tight, which is the hardest place for it to survive, and it does.

Note for the reader of my logs: at those attaining points `V` exceeds my *lower* endpoint `L` by
`3.4e-12`. That is not a violation — `L` comes from a rationally-repaired feasible point, and `X_π`
is itself in `F(δ)`, so `φ ≥ V` by definition. The rigorous test is `V ≤ U`, and it passes.

**VERDICT: VERIFIED**, at every `ρ ≥ 0` under H3, needing neither concavity nor `g_i > 0`.

---

## 4. P3-split (priority target 3) — and the counting warning

**Attack on the algebra.** The dependency `D = Σ_z p_z·(supply) + Σ_{i∈B} ν_i·(band) − Σ_i (budget)`
was rebuilt in sympy on a symbolic `n=5, k=3` instance in exact rationals, and then the hypotheses
were stripped one at a time:

| hypothesis stripped | `D` still the zero row? | RHS still `0`? |
|---|---|---|
| baseline (`B = {0,2}`) | yes, every coefficient `simplify == 0` | yes, `= Σp + Σ_B ν m − k`, `= 0` by P2.3 |
| **every `ν_i = 0`** | yes | yes (`Σp − k = 0`) |
| **`B = ∅`** (no nonzero band multiplier) | yes | yes |
| **`B = S`** (every agent band-tight with `ν ≠ 0`) | yes | yes |
| **`δ = 0`** | the two band rows share one gradient ⇒ one row per agent ⇒ `t = k`, count `n+2k−1` | — |

Nontriviality never depends on the band: the `k` budget rows enter with coefficient `−1`. So the
`−1` is **unconditional**, exactly as claimed, and the stop rule's escape clause is not needed.
Numerically, on 118 random instances the residual of `D` on the support equals **exactly** the KKT
stationarity residual of the dual used (difference `0.00e+00`), i.e. the dependency is exact and any
float residue is the dual's accuracy, not a defect.

**Attack on the count.** 440 optimal-face vertices over 118 adversarial instances (`k` up to 5,
heavy-tailed and one-huge-zip `M`, `δ ∈ {0, 1e-4, 0.01, 0.05, 0.15, 0.5}`, `δ = 0` all-tight regime
exercised on 66 vertices):

```
#splits <= k-1+t        min slack 0   (attained 64 times)   max splits 5, max t 5
#splits <= 2k-1         min slack 2
|supp|  <= n+k+t-1      min slack 0
```

So the sharp bound is **attained**, the coarse `2k−1` was never attained, and the rank statement it
rests on holds with no slack to spare. At `t = 0` it reduces to `≤ k−1`, consistent with
`VERIFY_U1-cert` §5 — no contradiction with the settled result.

**The warning — and it is the one thing in this unit most likely to bite U8.** My first pass used a
`1e-9` support threshold, reasoning that a *strict* threshold is the adversarial choice. It is not:
**it is below the LP solver's own dirt.** With `x > 1e-9` I recorded 108 apparent violations of the
sharp bound out of 517 vertices. `p3_probe.py` dissected them; every one was a column like
`(1.0, −4.7e-9, +4.7e-9)` or `(0.999999858, 1.42e-7)` — solver residue counted as a split. After
cleaning (zero entries below `1e-6`, renormalise the column, then **re-certify**: `g` unchanged to
`1e-6`, masses still in the band, and `rank(tight rows | supp) == |supp|` so it is still a vertex),
zero violations remain and the bound is attained. Because the bound is *attained*, this is exactly
the regime where the threshold flips the verdict. **U8 must clean-and-recertify before counting.**

**VERDICT: VERIFIED**, `#splits ≤ k−1+t ≤ 2k−1`, the `−1` unconditional, `25` split units at `k=13`.

---

## 5. P2.5 (priority target 4) — `DOMAIN_optimization` §2.12 is false as written

`docs/DOMAIN_optimization.md:420` states `supp(X) ⊆ argmax_i u_i(z)/(p_z + ν_i M_z)`.

**The smallest counterexample. `n = 1` zip, `k = 2` agents, `M = [1]`, `u = [[2],[1]]`, integer data,
exact arithmetic, `ν ≡ 0`.** `T/k = 1/2`. Feasible `x = (a, 1−a)`, masses `(a, 1−a)`.

* `max log(2a) + log(1−a)` has `a* = 1/2` (`1/a = 1/(1−a)`), so `g* = (1, 1/2)` and
  `m = (1/2, 1/2) = T/k` — the band is **slack for every `δ > 0`**, hence `ν ≡ 0` by complementary
  slackness. The band plays no role whatever.
* Stationarity: `u_1/g_1 = 2/1 = 2` and `u_2/g_2 = 1/(1/2) = 2`, so `p = 2` and `Σ_z p_z = 2 = k`.
* §2.12's rule reads `argmax_i u_i(z)/(p + 0) = argmax_i u_i(z) = {agent 1}`. But
  `x_{2} = 1/2 > 0`, so agent 2 is in `supp(X)`. **The containment fails.**
* The corrected rule reads `argmax_i (u_i(z)/g*_i − ν_i M_z) = argmax_i (2, 2) = {1, 2} ⊇ supp`,
  and its maximum is `2 = p_z`. Correct.

A non-degenerate strict version: `n = 2, k = 2, M = [1,1], u = [[10,10],[3,1]]`. The EG optimum gives
zip 0 **entirely** to agent 2 (`g* = (10,3)`, `p = (1,1)`, value `log 30 = 3.4011973817`, confirmed by
the certified bracket at `δ ∈ {0, 0.05, 0.5}` to `1e-10`), while §2.12's rule assigns it to agent 1
on `u = 10 > 3`. Margin `10/3`.

So the error is not induced by the band, is not a degeneracy of the model's toys, and is present in
the unbanded reading. On my fixtures the published form is violated on **5 of 6** and **4 of 8** zips.

**VERDICT: P2.5 VERIFIED; `DOMAIN_optimization` §2.12's selection rule REFUTED.**
**Corrected statement (verbatim, for §2.12):**

> At the optimum, `supp(X) ⊆ argmax_{i∈S} ( u_i(z)/g*_i − ν_i M_z )`, and that maximum equals `p_z`.
> Rank zips by `margin_z := max_i(u_i(z)/g*_i − ν_i M_z) − 2nd-max_i(u_i(z)/g*_i − ν_i M_z)`.
> (Equivalently, and scale-free: `argmax_i u_i(z)/(g*_i q_{zi})`, whose maximum is `1`.)

U14's first-mover list computed from the ratio form would be the wrong list.

---

## 6. P4.4 (priority target 5) — and a hazard the model did not name

**The model's claim, verified.** At `δ = 0` I built the adversarial dual explicitly: take my
independent optimal `(p, ν)`, set `μ⁺ = max(ν,0) + c`, `μ⁻ = max(−ν,0) + c`. The certified dual value
`D` is **unchanged to `1e-10`** for `c ∈ {0, 1, 100, 1e4, 1e6}` while `(T/k)Σ(μ⁺+μ⁻)` runs
`5.10 → 185 → 1.80e4 → 1.80e6 → 1.80e8`. Every one is still a *valid* supergradient at `δ = 0` (the
domain has no `δ' < 0`, so an arbitrarily large slope is admissible) and every one is vacuous.
Symbolically: at `δ = 0` the Lagrangian band terms collapse to `−ν_i(m_i − T/k)` and the dual
objective term to `(T/k)Σν_i`, both independent of `c`; at `δ > 0` the same shift raises the dual
objective by `2cδT/k > 0`, so it leaves the dual-optimal set and the aggregate is pinned to `Σ|ν|`.
Independent corroboration I did not plant: my SCIP dual solve at `δ = 0` **drifted to
`μ⁺ ≈ μ⁻ ≈ 5001`** — its box bound — of its own accord. The degeneracy is not a thought experiment.

**What the model missed.** `Σ_i|ν_i|` is **also** gauge-dependent at `δ = 0`. My arbitrary optimal
dual gives `ν = (0.053228, 0.060151)` and `(T/k)Σ|ν| = 5.102078`; the gauge-reduced value is
`(T/k)·min_c Σ_i|ν_i + c| = (T/k)|ν_1 − ν_0| = 45 × 0.006923196 = 0.311544` — **a factor 16.4**.
(That gauge-reduced number reproduces the model's §4.3 `s_min = 0.311544` to `2e-7`, from a
completely independent dual: strong cross-confirmation of the model's arithmetic, and proof that the
minimisation is not optional.) §2's P4.4 defines `s_min` *as* the minimised value, so the model is
formally correct — but §6 item 2's operational instruction ("report `(T/k)Σ_i|ν_i|`") is only safe if
the minimisation is actually performed.

**The new hazard: a loose minimisation gives an INVALID supergradient.** `s_min` is the minimum over
the *exact* dual-optimal set. Relaxing dual optimality to `D ≤ φ + ε` biases it **downward**, and a
too-small slope breaks P4.6's tangent bound. Measured on the heavy-zip toy at `δ = 0`
(`smin.py`, true `s_min = 0.311544`):

| `ε` in the dual-optimality constraint | `s_min` returned | max violation of `φ(δ') ≤ φ(0) + s·δ'` |
|---|---|---|
| `1e-3` | `0.25754122` | **`+9.942e-04` — INVALID** |
| `1e-4` | `0.29440346` | **`+9.763e-05` — INVALID** |
| `1e-5` | `0.30611476` | **`+8.426e-06` — INVALID** |
| `1e-6` | `0.30981918` | `−1.010e-05` (valid) |
| `1e-10` | `0.31137792` | `−1.789e-05` (valid) |
| exact (gauge-reduced) | `0.311544` | `−1.872e-05` (valid) |

The model's own `solve_duals` relaxes stationarity by `resid·1.000001 + 1e-13` before minimising
`Σ|ν|`; on its toys `resid = 0.00e+00`, so nothing broke there — but the mechanism is live on a real
instance where `resid > 0`. **VERDICT: P4.4 VERIFIED, and P4.6 VERIFIED subject to a precondition
U8 must implement (§9 item 2).**

---

## 7. P5.5 (priority target 6) — is the refutation of the brief an evasion?

**No.** Three things had to be true and all three check out.

1. **The citation reading is correct.** DuranGrossmann1986 and FletcherLeyffer1994 prove finite
   termination for convex **MINLPs**, and the finiteness comes from one place: the integer
   assignment set is finite and no assignment is generated twice, so the algorithm stops after at
   most that many major iterations. `EG^bal_S(δ)` at `ρ = 0` has **no integer variables**, so the
   argument has nothing to count. `DOMAIN_optimization` §2.11 line 323 cites them for "validity and
   finite convergence of outer approximation for convex problems"; validity transfers, finiteness
   does not. The unit brief's line 58 ("finite convergence under `ĝ > 0`") inherits the slip, and
   `LIT_optimization` §5 row G already records the absence of any result for a *pure-continuous*
   `Σ log` OA.
2. **The missing "only if" — which §3 asserts but does not prove — I closed.** Let
   `h_i(y) := min` over agent-`i` cuts of the tangent at `y`; then `h_i ≥ log` with equality exactly
   at cut points, and `MP(𝒞) = max_{g∈G} Σ_i h_i(g_i) ≥ φ`. Suppose `MP = φ` and `ĝ` attains the
   master max. Then `Σ_i log ĝ_i ≤ φ = MP = Σ_i h_i(ĝ_i)` with `h_i ≥ log` termwise, so both squeeze:
   `h_i(ĝ_i) = log ĝ_i` for every `i`, **and** `ĝ` maximises `Σ log` over `G(δ)`, so `ĝ = g*` by P0b.
   Hence exact termination **requires** a cut placed exactly at `g*` — which is P5.4 read backwards
   and is what makes non-finiteness a theorem rather than an observation. This belongs in §3.
3. **The behaviour is as described.** An independent Kelley loop (SCIP LP master, 250 iterations, my
   `k=3` toy at `δ = 0.03`): `MP − U` runs `4.96e-02 → 9.81e-05 → 1.765e-07` and then **stalls** at
   `1.765e-07`; `MP` is monotone non-increasing; the bracket contains `φ` at every iteration; **0**
   iterates ever landed on `g*`.

**One caveat against the model.** §3's item (iv) — "`MP` decreases and converges to `φ(δ)`, standard
Kelley convergence" — is marked `[sketch]` and my run does not corroborate it: it stalls at `1.8e-7`
rather than continuing to descend. That is consistent with textbook Kelley instability on a near-flat
objective (`Lemarechal1995`, which §2.11 already cites), and it does not touch anything U8 needs,
because validity (P5.1) and the bracket hold at every iteration. But **U8 must not write "the loop
converged"**, and must not treat the bracket closing as convergence — the model says this and it is
right.

**VERDICT: P5.5 VERIFIED — the brief's "finite convergence under `ĝ > 0`" is REFUTED for the
continuous master; `ε`-termination is all that holds.**
**Corrected statement for the unit brief's acceptance item P5-OA:**

> Every optimum of the tangent master is an upper bound on `EG^bal_S(δ)`; the bound is monotone
> non-increasing in the cut set; the loop holds a certified bracket at every iteration and therefore
> `ε`-terminates for any `ε > 0`. **Finite termination at exact optimality does not hold** — it
> requires a cut placed exactly at `g*` (P5.4 and its converse) — and the
> DuranGrossmann1986 / FletcherLeyffer1994 theorems do not supply it, being statements about the
> finitely many integer assignments of a MINLP.

---

## 8. Where the model's own §4 does not reproduce

Re-running `docs/artifacts/U9-bandthm/bandthm.py` gives `FAILURES: none` in ~110 s and **every**
table in §4.0–§4.8 matches its published values, including the 400-iteration `P5` trace, the
`18,150`-coverage `P1` row, the `360`-vertex ensemble, and all of §4.8's arithmetic (recomputed in
30-digit mpmath: `T/k = 211.200860538`, `EG − V = 0.7599458155`, `screen − V = 0.8650302`, the four
slope thresholds `47.2016 / 16.4847 / 7.9079 / 2.3304`, `2k−1 = 25`).

Independently, my own dual reproduces §4.5's toy3 `s_min` column at 7 of 8 grid points to `≤5e-7`.
**One number does not reproduce:**

| `δ` | `MODEL` §4.5 | this verification | difference |
|---|---|---|---|
| `0.09` | `0.183500` | **`0.183537`** | `3.71e-05` |

Both are valid supergradients (each passes the global tangent test to bracket precision), the gap is
`7e-6` in `ν` and two orders inside tier 2, and its **sign matches the downward bias** documented in
§6 — the model's `solve_duals` relaxes stationarity before minimising `Σ|ν|`. I record it as a
non-reproduction rather than an error, and note that the bias direction is the unsafe one.

Two further presentation points, not errors:

* §4.2 reports `ν = [0.000000, 0.006274]` at the heavy-zip toy, `δ = 0.02`; my independent dual gives
  `[−0.003137, +0.003137]`. These are the **same point of the gauge orbit** (`c = −0.003137`), and
  both give `s_min = 0.282324`. This is P2b working exactly as advertised — and it is a reminder
  that a per-rep `ν_i` is not quotable without the tight set beside it.
* §4.3's "toy3 `δ = 0` gauge interval `= ℝ`" is confirmed structurally: my exact `δ = 0` toy in
  `sym.py` has multiplier family `p = (3/2 − 2c, 1/2 − c)`, `ν = (c, c)` with `c` free over all of
  `ℝ` and zero duality gap for every `c`.

---

## 9. Corrections and instructions

### To `docs/MODEL_U9-bandthm.md` (report only — I did not edit it)

1. **§2 P1b-band / §3.** "`LENS_GROMOV` M8's `V ≤ EG^bal_{S₁₃}(0.0078)`" is out of date. A1's
   `docs/LENS_GROMOV.md:58` already writes the sandwich with `δ₀`, and lines 62–64 already
   carry the max-deviation-vs-spread distinction. The live `0.0078` sites are M8's U13 grid
   (lines 118, 121, 155, 271) and `docs/DOMAIN_economic-theory.md` lines 440–441, 520, 739.
   The recommendation is unaffected.
2. **§2 P4.4 / §6 item 2.** Add that at `δ = 0` **`Σ_i|ν_i|` is itself gauge-dependent** (factor 16.4
   measured), so "report `(T/k)Σ|ν_i|`" must read "report the value **minimised over the
   dual-optimal set**, and gauge-reduce". Add the `ε`-conditioning warning of §6 above.
3. **§3 P5.5.** Insert the converse of P5.4 (§7 item 2 here). It is what turns "does not terminate
   finitely in general" from an assertion into a proof, and it costs four lines.
4. **§2 P2.7.** `kawase2026balanced`'s *positive* result (EF1+fPO balanced allocations exist,
   poly-time) is stated for **cardinality** balancedness — bundle sizes differing by at most one —
   and for the two-valuation-type and personalised-bivalued classes. Our band is a **weighted**
   `M`-mass band with general valuations, so the existence half does **not** transfer as written.
   `LIT_economic-theory` line 899 hedges it correctly as "nearby special cases"; the model drops the
   hedge. The *negative* half (maximising NSW over balanced allocations need not be EF1) and the
   `echenique2021constrained` fairness clause transfer exactly as the model states, and the
   correction to `DOMAIN_economic-theory` §2.8's EF1 row stands.
5. **§4** is otherwise clean; §8 above lists the single non-reproducing number.

### To `docs/DOMAIN_optimization.md` (for whoever owns it)

* **§2.12 line 420 is REFUTED.** Replace with the corrected rule in §5 above.
* §2.10's "Slater ... in the relative interior of the band for `δ > 0`" is **weaker than the truth**;
  all constraints are affine, so the refined condition gives multipliers at `δ = 0` too (P0).
* §2.11's "Its supergradient at `δ` is `(T/k)Σ(μ⁺+μ⁻)`" should read "**a** supergradient, for any
  optimal dual; the quotable one is the minimised `(T/k)Σ|ν_i|`, and at `δ = 0` the unminimised form
  is unbounded".
* §2.10's coarse `≤ 2k` is superseded by the unconditional `≤ 2k−1` (P3-split).
* §8's verdict line calls `borgwardt2019` "the load-bearing entry" for the `O(nk)` cell certificate.
  It is not: their cost is a common squared distance on a geometric point set, ours is `Σ log` with
  agent-specific `u`. P6 proves the certificate directly; the citation is for the constraint class.

---

## 10. Answers to the three questions the task asks for

**Which of the five brief-mandated propositions passed.** All five.
**P1-band VERIFIED** · **P2-price VERIFIED** (with §2.12's published selection rule REFUTED, and the
"not a competitive equilibrium at the stated budgets" sentence confirmed by an independent demand LP)
· **P3-split VERIFIED** (`≤ k−1+t ≤ 2k−1`, the `−1` unconditional, and the `2k` fallback not needed)
· **P4-slope VERIFIED** (with the brief's own equality form `d EG^bal/dδ = (T/k)Σ(μ⁺+μ⁻)` REFUTED at
kinks and at `δ = 0`) · **P5-OA VERIFIED for validity and monotonicity; the brief's "finite
convergence under `ĝ > 0`" REFUTED**, `ε`-termination is what holds.
`P6-cells` VERIFIED for the direct half, PLAUSIBLE for the explicitly `[conjectured]`
`borgwardt2019` half.

**What U8-band must change.**

1. **Grid from `δ₀ = 0.0039`**, not `0.0078`, and mark the delivered point there (the model's item 1;
   confirmed — `0.0078` is the spread, `δ₀` the max deviation, and FRAME §0 line 23 already says so).
2. **Compute `s_min` as a minimisation over the *exact* dual-optimal set, gauge-reduce it, and check
   it.** Two things beyond the model's instruction: (a) at `δ = 0`, `Σ|ν|` from an arbitrary optimal
   dual overstated the slope by 16.4× on a toy; (b) an `ε`-relaxed minimisation *understates* it and
   yields an **invalid** supergradient (`ε = 1e-5` already broke the tangent bound by `8.4e-6` nats).
   Cheap guard: after computing `s_min(δ₀)`, verify `φ(δ₁) ≤ φ(δ₀) + s_min·(δ₁ − δ₀)` at one further
   grid point before quoting P4.6's certificate.
3. **Rank first movers by the additive margin** `max_i(u_i(z)/g*_i − ν_i M_z) − 2nd-max`, never the
   ratio form (the model's item 3; confirmed with a one-zip counterexample).
4. **Clean and re-certify the returned vertex before counting splits.** A support threshold below the
   solver's dirt floor manufactures splits and makes the (attained) `k−1+t` bound appear to fail;
   I reproduced 108 phantom violations this way. Zero entries below `1e-6`, renormalise the column,
   then confirm `g` unchanged, masses still in band, and `rank(tight rows | supp) == |supp|`.
5. **Report `t`, the tight set, and the gauge width beside `p`, `ν` and the split count.** `g*` and
   `φ` are invariants; `p`, the individual `ν_i`, and the split *set* are not (4–6 distinct split
   sets at the same `g*` on my fixtures).
6. **Never report "OA converged."** Quote the master optimum and the incumbent as a bracket
   (P5.1/P5.6); `mip_rel_gap = 0.0`; a `time_limit` stop is not a bound. My independent loop stalled
   at `1.8e-7` for 225 consecutive iterations without closing.
7. **Run the P1c check first.** If `cert_integer_balance_floor`'s `t*` exceeds `δ·T/k`, the bound at
   that `δ` is true and empty and no frontier point should be plotted without saying so.

**What contradicts a previously settled result.** Nothing.

* `VERIFY_U1-cert` P1 (VERIFIED at every `ρ ≥ 0` under H3) is extended, not contradicted: the band
  adds exactly one feasibility check, which is an exact rational identity.
* `VERIFY_U1-cert` §5's `≤ k−1` splits via the MBB face is the `t = 0` specialisation of `k−1+t`;
  my 440-vertex ensemble is consistent with it and I did not re-derive it.
* `VERIFY_U1-cert` §5's quotation hazard survives the band in the exact form P0b predicts.
* Three *documents* are contradicted, all deliberately and all flagged above:
  `DOMAIN_optimization` §2.12's selection rule (REFUTED), §2.10's `δ > 0` restriction on multiplier
  existence (too weak), and the unit brief's own P5-OA "finite convergence" and P4 derivative-equality
  clauses (REFUTED). `DOMAIN_economic-theory` §2.8's EF1 row is corrected by `kawase2026balanced`
  exactly as `LIT_economic-theory` line 896 already records.

**Tolerance tiers used.** Exact (`0`) for every sympy identity and for the `n=1`/`n=2` counterexamples
and P1c's `1/9`. Rigorous-bracket tier for every `EG^bal` value: widths `6.3e-10`–`3.2e-7`, both
endpoints re-verified in exact rationals, so all `EG^bal` comparisons clear tier 1 (`1e-8`) except
the two heavy-zip points at `δ ∈ {0.02, 0.06}` where the bracket is `2.9e-7` and the margins tested
(`1e-2`) are four orders larger. `5e-6` for KKT residuals read off a `feastol = 1e-9` SCIP solve.
Split counts are integers, and the counting threshold is the load-bearing choice (§4).

**What this did NOT cover.** The real instance (this unit computed none, by design, and I ran none —
`instance_descaled.json.gz` was not read, so nothing here depends on a gitignored input). `ρ > 0`
beyond P1-band: P2–P6 are `ρ = 0` statements and I verified them only there. The `borgwardt2019`
paper itself (annotation-level check only). `budish2013`'s bihierarchy class membership (the model's
open item 6) — I did not re-derive it; the reasoning in `LIT_optimization` §0 (a *weighted* per-agent
row is outside a class defined by counting set memberships) is sound on its face but is a citation
claim, not a checked one. `P4.5`'s open half — that `∂φ(δ)` **equals** the closure of the multiplier
aggregates rather than merely containing it — is still open; I used only the direction the model
proves, and nothing downstream needs the other.
