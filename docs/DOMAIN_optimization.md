# optimization plan — the national channel territory problem, under the A1 charter

**Date:** 2026-09-03 (branch `wt/A1`) · **Framework:** 0.1 · **Track:** A1
(`docs/APPROACHES.md` §A1, taken verbatim as the problem) ·
**Reads:** `docs/APPROACHES.md` §A1, `docs/FRAME.md` (all, §6 as extended 2026-09-03),
`docs/LENS_GROMOV.md` (2026-09-03), `docs/LENS_GROTHENDIECK.md` (inherited unchanged),
`docs/MODEL_U7-meas.md` §1–§6, `docs/MODEL_U1-cert.md` §2–§6, §8,
`docs/VERIFY_U1-cert.md` §0, §5–§7, `docs/CODEVERIFY_U7-meas.md`,
`docs/DOMAIN_economic-theory.md` (for non-duplication),
`~/resources/optimization/FOUNDATIONS.md` (113 entries, seeded 2026-09-02) ·
**Supersedes:** `docs/DOMAIN_optimization.md` of **2026-09-02** (the hub's version, written
before U1-cert and U7-meas landed) — **on this branch only**. Its §2.1–§2.9 numbering is kept
so that `docs/units/*.md` and `docs/BRIEF.md` cross-references resolve; §2.10–§2.15 are new.

**Citation rule.** **Bold keys** are entries of `~/resources/optimization/FOUNDATIONS.md` and are
the only literature this plan asserts. `lowercase keys` are entries that already exist in
`docs/LIT_economic-theory.bib` or `docs/RESEARCH_ADDITIONS.bib` and are cited as pointers, not as
verified support. Anything else — a claim needing a source that neither file has — is left
uncited and appears in the §6 search brief. `docs/LIT_optimization.md` still does not exist
(U0-lit has not run), so **every §6 question from the predecessor is still unanswered**; §6 below
says which are retired and which carry.

**One-sentence position.** The predecessor proposed a 136k-binary rep-indexed MINLP as the
centrepiece; the measurements retire it to a contingency, and what replaces it is **one
band-constrained concave program `EG^bal_S(δ)`, its value function in `δ`, its duals, a
band-aware rounding of its vertex, and a short enumeration over rosters screened by a closed-form
premium bound** — five objects, all convex or tiny, none needing a conic solver, and together
they answer most of the charter.

---

## 0. What changed since 2026-09-02, method by method

The predecessor's §2 is a menu written against an unmeasured instance. FRAME §6's 2026-09-03 rows,
`MODEL_U7-meas` §6 and `MODEL_U1-cert` §4/§6 now decide most of it. **Status of every method:**

| § | method | status | why |
|---|---|---|---|
| 2.1 | rep-indexed perspective MINLP | **retired to a contingency** | `LENS_GROMOV` M13.1; the roster is the only genuine integrality and the ladder says the rosters worth trying are tens (U16); at fixed roster the object is concave over a polyhedron. Also **not executable as specified**: its stated form is exponential-cone/SOCP (**GunlukLinderoth2010**, **Lobo1998**) and there is no conic solver on this machine. Fires only under §2.13's criterion. |
| 2.2 | fixed-roster concave relaxation `EG_S` | **kept, and discharged** | Built and verified: `EG_{S₁₃} = 60.697416`, bracket `7.1e-15`, gap `0.760` nats (`VERIFY_U1-cert` row 2). **Changed in status, not in content:** it is a surrogate that drops the sponsor's own balance constraint (`MODEL_U1-cert` §5.3), so it is no longer *the* certificate — §2.10 is. Its starvation failure mode is discharged by P1b. |
| 2.3 | the roster ladder `P₀ ≤ P*(A) ≤ P₁₃ ≤ P_free` | **kept, executed, and extended** | Executed as `MODEL_U7-meas` with a new rung `P_S`. Its escape clause did **not** fire: `corr(T_z,M_z) = 0.650`, "bites moderately" (FRAME §6). Extended in §2.14 by a closed-form bound that turns the ladder into a *screening rule with a validity proof*. |
| 2.4 | displacement as the acceptance unit | **kept, unchanged, still unproved** | `MODEL_U1-cert` §8.5: the prices are computed, the modulus is not. §2.12 supplies a better input (band duals, in nats per unit of `M`) but does not prove the modulus. Still §8 Q3. |
| 2.5 | the `(premium, balance)` Pareto frontier | **changed: the object survives, the method is replaced** | The right axes are `(δ, V)`, not `(P, balance)`, and the tracing is parametric *convex* programming, not a sequence of ε-constraint MILPs (**Boland2015** no longer bears). See §2.11. Trap 2's marking requirement carries over verbatim and is strengthened. |
| 2.6 | homotopy in `τ` | **retired** | `LENS_GROMOV` M8: `EG^bal(δ)` supersedes it. The homotopy asks whether the *map* moves as books switch on and answers empirically; the frontier asks how much *value* the band leaves and answers convexly. D1 (the predecessor's fork) is withdrawn and replaced by D1′ in §4. |
| 2.7 | matheuristic polish (local branching, LNS) | **narrowed** | Its own failure-mode test has run: `P₀ = P*(A)` exactly on seed 3, so the matching is already premium-optimal and **zip-swap neighbourhoods are the wrong operator on this instance**. What survives is one specific use: **Danna2005** RINS as the band-aware rounding repair in §2.13. General LNS is out. |
| 2.8 | robustness of balance to regional bias in `M` | **still blocked on A4, and now visibly so** | `MODEL_U1-cert` §5.6 and `VERIFY_U1-cert` §6 confirm a regional bias in `M` moves the certificate and the thing it certifies together and is invisible from inside. Do not build. §8 Q8 asks whether to cut it. |
| 2.9 | Benders / logic-based Benders | **deferred, and further away** | The monolith it would decompose is itself retired (§2.1). Revisit only if §2.13's criterion fires *and* the resulting MINLP stalls. |

---

## 1. What the lenses handed over, in this domain's terms

The predecessor's table stands for the constructs the 2026-09-02 lenses named; only the rows the
new lens changed or added are restated here.

| lens construct (file §) | becomes | or "no counterpart, because" |
|---|---|---|
| **`EG^bal_S(δ)`** — band-constrained fibre (GROM M8, U13) | a **concave program over a polyhedron**: the same objective as `EG_S` with `2k` extra linear rows. Concavity untouched (**BoydVandenberghe2004**); Slater holds at every `δ ≥ 0` via `x ≡ 1/k` (**BoydVandenberghe2004** §5.2.3), so strong duality and multiplier existence hold (**KuhnTucker1951**, **Rockafellar1970**) | — |
| **the frontier `δ ↦ EG^bal_{S₁₃}(δ)`** (GROM M11.1, U13) | the **perturbation / optimal-value function** of a concave program with an affine right-hand side in `δ`: concave and nondecreasing in `δ`, with the band multipliers as its supergradient (**Rockafellar1970**, **BoydVandenberghe2004** §5.6, **KuhnTucker1951**). Traced by parametric programming with warm-started dual simplex (**Chvatal1983**, **Dantzig1963**, **Bixby2002**) | the *elicitation* of the sponsor's `δ` is a business act, not an optimisation |
| **band duals `μ_i^±`** as the balance↔continuity exchange rate (GROM M11.2, U12→U14) | **KKT multipliers on a resource row**, i.e. shadow prices in nats per unit of `M` (**KuhnTucker1951**, **GaleKuhnTucker1951**, **Chvatal1983** on ranging). Their aggregate *is* the frontier's slope, so the exchange rate and the frontier are one object seen twice | — |
| **"which zips move first as `δ` crosses `δ*`"** (GROM M12) | the **active set** of the modified bang-per-buck comparison `u_i(z)/(p_z + ν_i M_z)`, read off one solve by complementary slackness (**KuhnTucker1951**); the *mass* that moves is a transportation distance (**Hitchcock1941**, **Ahuja1993**) | — |
| **U15** — does the band change the `≤ k−1` split count? | a **rank/vertex-support question on the optimal face**. At most one band row per agent is tight, so the coarse count goes `≤ k` → `≤ 2k`; the surviving budget dependency gives `≤ 2k−1` `[claim, §2.10]`. Its consequence is a **value** bound, not a count (**Schrijver1986** for the TU intuition, which does *not* apply here — the gain rows are not TU) | — |
| **U16 / U19** — roster enumeration and `max_S EG^bal_S` | a **branch-and-bound over `k`-subsets with a closed-form bound** (§2.14): `EG_S ≤ k log((B_tot + w·P_S)/k)` by concavity of `log` (**BoydVandenberghe2004**), with `P_S` from the max-`k`-coverage MILP (**LandDoig1960**, **NemhauserWolsey1988**) and near-optimal rosters enumerated by no-good cuts (**CodatoFischetti2006**) | the *submodularity* question the lens asks about `S ↦ EG^bal_S` — **Schrijver2003** covers submodular *set functions*, not this composition; it is a §6 item |
| **U17** — Nash-tie fragility of `S₁₃` (8.1e-3 nats on seed 9) | the **stability radius of an optimal assignment**: how far the cost matrix moves before the optimal permutation changes — objective-coefficient ranging (**Chvatal1983**) on a linear assignment problem (**Kuhn1955**, **GaleKuhnTucker1951**). The margin is computed exactly by `k` re-solves, each forbidding one matched edge | the *reporting* convention (margin, or an interval over near-optimal rosters) is partly a statistics question — §7 |
| **U18** — the rounding gap at the sponsor's `δ` | a **tiny mixed-integer program on the split set only**: `≤ 2k−1` units × `k` buyers, concave separable objective, `2k` band rows — the tractable convex-MINLP class (**Kronqvist2018**, **GuptaRavindran1985**, **Bonami2012**), or equivalently one RINS neighbourhood (**Danna2005**) | — |
| **"MINLP" and "jointly" purged** (GROM M13) | in this domain: the selection binaries are the only integrality, and they are enumerated rather than branched. **Nothing here is a MINLP** unless §2.13's criterion fires | — |
| **no conic solver on the machine** (GROM OQ2) | a hard constraint on formulation, not a preference. Exponential-cone/SOCP forms (**Lobo1998**, **NesterovNemirovskii1994**, **GunlukLinderoth2010**) are **unavailable**; the executable routes are SCIP-native `log` (**VigerskeGleixner2018**) and LP outer approximation (**WesterlundPettersson1995**, **DuranGrossmann1986**, **Kronqvist2016**, `lubin2018`) | — |

---

## 2. Candidate methods

### 2.1 Rep-indexed formulation with a perspective reformulation of the staffing indicator — **retired to a contingency**

*(Predecessor text stands as written; only its status changes. Rests on **GunlukLinderoth2010**,
**FrangioniGentile2006**, **Vielma2015**, **DuranGrossmann1986** / **FletcherLeyffer1994**,
**QuesadaGrossmann1992** / **Bonami2008**, **LandDoig1960**, **Kronqvist2018**.)*

**Why it is retired.** Three measured reasons, in order of force.

1. **The nonlinearity is concave and the only integrality is selection.** At fixed `S` the problem
   is `EG^bal_S`, concave over a polyhedron; branch-and-bound has nothing to branch on but the
   `≤ 2k−1` split units, which §2.13 handles with a bound (`MODEL_U1-cert` P3b).
2. **Selection is a short enumeration, not a search.** `P₁₃ − P_S = 0.92 %` of book ≈ 0.043 nats
   (U7-meas §6), eight times the tier-2 floor but small; the `P₁₃` optimum is a two-rep swap from
   `S₁₃` (R0017, R0018 → R0009, R0012) and greedy attains the MILP optimum. §2.14 gives a valid
   screening bound that makes the enumeration provably sufficient.
3. **It is not executable as specified on this machine.** The perspective term's stated strength
   comes from its conic representation (**GunlukLinderoth2010**, **Lobo1998**); there is no conic
   solver. The executable substitutes are SCIP-native `log` (**VigerskeGleixner2018**) or an OA
   master (**WesterlundPettersson1995**, `lubin2018`), neither of which was costed.

**Assumptions, against FRAME §5/§6** — unchanged from the predecessor, plus: (iv) a solver able to
handle `y_i log(g_i/y_i)`; **not met** by the current stack except through SCIP's expression
graphs. (iii) size is **still not met** at 111 reps; §2.14's screening replaces §2.3's pruning.

**What would revive it.** §2.13's criterion only: if the band-aware rounding gap at the sponsor's
`δ` exceeds tier 2 *and* RINS on the split set cannot close it, *or* if §2.14's enumeration
returns hundreds of rosters inside the floor. **Failure mode if built early:** 37k binaries with a
near-flat objective is the classic cut-loop thrash (**Lemarechal1995**; **BenAmeurNeto2007** and
**FischettiSalvagnin2010** for the cheap in-out stabilisation) — and it would be built to answer a
question §2.10 answers in one solve.

### 2.2 The fixed-roster concave relaxation `EG_S` — **kept, discharged, demoted**

*(Rests on **BoydVandenberghe2004**, **KuhnTucker1951** / **Rockafellar1970**, **Mehrotra1992** /
**Wright1997**, **NesterovNemirovskii1994**, **Khachiyan1980**.)*

**What it produced.** `EG_{S₁₃} = 60.697416` against `V = 59.937470`; three of the four existing
certificates are its degenerations, the fourth (`cert_integer_balance_floor`) is not
(`VERIFY_U1-cert` row 4). The split-unit descent is `≤ k−1` unconditionally and needed no new
result (`brieden2017` Lem. 4 stands; `VERIFY_U1-cert` §5).

**What demotes it.** Its optimum has `M`-spread `≥ 50 %` on two independent solves, i.e. the
`0.760` nats is a gap over a feasible set the sponsor would reject. **It is the surrogate, not
the problem** (`LENS_GROMOV` M8). Keep it as (a) the `δ = δ_max` endpoint of §2.11's frontier and
(b) the cross-check that any `EG^bal` solver reproduces at a loose band.

**Failure mode retired.** The predecessor's ill-conditioning warning (`g_i → 0`) is discharged by
P1b (`min_z M_z = 1.8e-3 > 0`, so `u_i(z) ≥ λ M_z > 0`), and the band makes it structurally
impossible: `m_i ≥ (1−δ)T/k` forces `g_i ≥ λ(1−δ)T/k`. **The band improves conditioning.**

### 2.3 The roster ladder — **kept, executed, extended**

*(Rests on **Kuhn1955**, **LandDoig1960** + **NemhauserWolsey1988**, **Karp1972**,
**Schrijver2003**.)*

Executed as `tools/measure/premium.py` (`CODEVERIFY_U7-meas` 15/17 VERIFIED). The predecessor's
recommendation — exact MILP over greedy-plus-submodular-certificate — was **right**: the MILP
closed with `mip_rel_gap = 0.0` and greedy attained its optimum. The escape clause did not fire
(`corr(T_z,M_z) = 0.650`). `P_S` was added as a new rung and is the one the charter needed.

**What is extended.** The ladder is currently a set of numbers; §2.14 turns `P_S` into a **valid
upper bound on `EG_S` and `EG^bal_S`**, which is what makes roster enumeration a bounded search
rather than a hopeful sample.

### 2.4 Displacement as the acceptance unit — **kept, unchanged, still the unproved step**

*(Rests on **Hitchcock1941**, **Kuhn1955**, **Ahuja1993** / **Orlin1993**, **Schrijver1986**,
**Chvatal1983**, **GaleKuhnTucker1951**.)*

Unchanged in substance. What the new work adds is a **better input**: the band duals of §2.12 are
denominated in nats per unit of `M` and the set of first-moving zips (§2.12) is a displacement by
construction, so U4-disp has a concrete object to measure rather than a price vector to interpret.
The modulus `objective-gap ≥ φ(mass moved)` is still neither cited nor proved
(`MODEL_U1-cert` §8.5). **Failure mode unchanged:** without the modulus, displacement is
descriptive and acceptance stays in nats.

### 2.5 The `(premium, balance)` frontier — **changed: the object survives, the method is replaced**

*(Predecessor rested on **Boland2015**, **Vielma2015**, **FischettiLodi2003**.)*

**What is wrong with the predecessor's method.** It proposed ε-constraint MILPs maximising the
*linear* premium `P` subject to a balance band. But `P` is not what the business signs — `V` is,
and `V` is not linear in `P` (`MODEL_U7-meas` §1). Enumerating a `(P, balance)` frontier by MILPs
would spend integer programming to trace a curve in the wrong coordinate.

**What replaces it.** §2.11: the same trade-off in `(δ, V)` coordinates, where the curve is the
value function of a concave program and each point is one convex solve. **Boland2015** no longer
bears; **Vielma2015**'s band encoding is trivial here (two linear rows per agent).

**What carries over verbatim.** The trap-2 obligation. The objective is *never* replaced by a
balance minimisation; the band is a constraint and the objective stays `Σ log g_i` at every `δ`.
The MNW point must be marked on every rendering of the curve, and §2.11 states exactly which point
it is.

### 2.6 Homotopy in `τ` — **retired**

*(Rested on **Chvatal1983**, **Dantzig1963** / **Bixby2002**, **Danna2005**.)*

`LENS_GROMOV` M8: `EG^bal(δ)` supersedes it. Two further reasons from this domain. (i) The
homotopy's own failure mode fires: sensitivity ranging on a degenerate LP gives a zero-width
interval, and a balance-tight transportation LP is degenerate by construction — now *confirmed* on
this instance as `MODEL_U1-cert` failure mode 5. (ii) Its output (does `π*` move between `τ = 0`
and `τ = 0.42`?) is already known in the form that matters: it moves, and the move is worth
`≤ 0.760` nats bought with `≥ 50 %` `M`-spread. **The predecessor's D1 fork is withdrawn.**

### 2.7 Matheuristic polish — **narrowed to one use**

*(Rested on **FischettiLodi2003**, **Danna2005**, **Shaw1998** / **RopkePisinger2006** /
**PisingerRopke2010**, **LinKernighan1973**, **Kirkpatrick1983** / **Glover1986** /
**GloverLaguna1997**, **RiosMercadoFernandez2009**, **Bozkaya2003**.)*

The predecessor's own gate — "run `P₀` vs `P*(A)` before writing any neighbourhood" — has run and
**closed the general case**: `P₀ = P*(A)` exactly on seed 3, so roster relabelling buys nothing on
the committed map, and the map gap is not reachable by local swaps that respect the band. What
survives: **Danna2005**'s RINS *as the rounding repair* in §2.13 (fix the `≥ n − 2k + 1` units the
`EG^bal` vertex assigns integrally, solve the rest exactly), and **FischettiLodi2003** local
branching only if that reduced solve is itself too large — which at `≤ 25` free units it is not.
**FischettiGloverLodi2005**'s feasibility pump remains explicitly unnecessary: three feasible
incumbents exist.

### 2.8 Robustness of the balance claim to regional bias in `M` — **still blocked, do not build**

*(Rests on **BertsimasSim2004**, **BenTalNemirovski1998** / **Lobo1998** / **BenTal2009**,
**CharnesCooper1959**.)*

Unchanged and now with independent confirmation of *why* it matters: `VERIFY_U1-cert` §6 checks
that a regional bias in `M` shifts the certificate and the thing it certifies in the same
direction and is undetectable from inside. **FRAME §5 still supplies no `δ`** for the deviation, so
`Γ` remains a knob with no meaning. §8 Q8 asks whether to cut the method from the plan.

### 2.9 Benders / logic-based Benders — **deferred, and further away**

*(Rests on **Benders1962**, **Geoffrion1972**, **HookerOttosson2003**, **CodatoFischetti2006**.)*

The master/sub split is still real and its subproblem is now *named*: master = roster, subproblem =
`EG^bal_S`, whose band and price duals are ready-made optimality cuts (**Geoffrion1972**). But
§2.14 shows the master is a **short enumeration with a closed-form bound**, so there is nothing for
a cut loop to earn. One piece is borrowed rather than deferred: **CodatoFischetti2006**'s no-good
cuts are exactly how §2.14 enumerates near-optimal rosters from the `P₁₃` MILP.

---

### 2.10 `EG^bal_S(δ)` — the band-constrained fibre, and the certificate the charter should have named **[new; the centrepiece]**

- **Rests on:** **BoydVandenberghe2004** (recognising the concave program, Slater's condition,
  sensitivity), **Rockafellar1970** (conjugate/Fenchel duality where LP duality does not reach,
  and the perturbation function), **KuhnTucker1951** (multipliers, sufficiency under concavity,
  complementary slackness), **GaleKuhnTucker1951** (shadow prices as the translation layer),
  **NesterovNemirovskii1994** / **Mehrotra1992** / **Wright1997** (a barrier solve at a single
  `δ`), **Khachiyan1980** (separation ≡ optimisation, licensing an `O(nk)`-checkable dual
  certificate). Non-FOUNDATIONS pointers: `eisenberg1961` (the unconstrained program),
  `budish2011` (approximate CEEI with constraint sets — the nearest published relative, and a §6
  item, not support).

- **The program.**

  ```
  EG^bal_S(δ) = max_X  Σ_{i∈S} log g_i(X),        g_i(X) = Σ_z u_i(z) x_{zi}
       s.t.   Σ_{i∈S} x_{zi} = 1                  ∀z          [duals p_z, free]
              Σ_z M_z x_{zi} ≤ (1+δ)·T/k          ∀i∈S        [duals μ_i^+ ≥ 0]
              Σ_z M_z x_{zi} ≥ (1−δ)·T/k          ∀i∈S        [duals μ_i^- ≥ 0]
              x ≥ 0
  ```

  Write `ν_i := μ_i^+ − μ_i^-` for the net band multiplier.

- **Convexity.** `Σ log` of a linear map is concave; the feasible set is a polyhedron — the band
  adds `2k` linear rows and changes nothing about the class (**BoydVandenberghe2004**). P1's proof
  (`MODEL_U1-cert` §3) goes through verbatim with the band added to both sides, because it needs
  only that the integral `X_π` is feasible: **`EG^bal_S(δ)` upper-bounds every integral coverage
  with roster `S` whose districts respect the band at `δ`.** `[claim — P1's proof with one extra
  feasibility check; math-verify]`

- **Duality and the price reading.** Stationarity at an optimum reads

  ```
  u_i(z)/g_i  ≤  p_z + ν_i·M_z ,     with equality on supp(X).
  ```

  So the band turns the common price `p_z` into an **agent-specific effective price**
  `q_{zi} = p_z + ν_i M_z`: an agent pressed against its upper band pays a surcharge proportional
  to a zip's opportunity content, one pressed against its lower band receives a subsidy. The
  bang-per-buck / MBB reading of the unconstrained program survives intact with `q` in place of
  `p` (**KuhnTucker1951**). Multiplying by `x_{zi}` and summing gives the modified budget identity
  `Σ_z p_z x_{zi} = 1 − ν_i m_i`, and summing over `i`, `Σ_z p_z = k − Σ_i ν_i m_i`. `[claim;
  math-verify]` Strong duality and multiplier existence hold at every `δ ≥ 0` because `x ≡ 1/k` is
  feasible with all `g_i > 0` (P1b) and lies in the relative interior of the band for `δ > 0`
  (**BoydVandenberghe2004** §5.2.3). The dual value at *any* `(p, μ^±) ≥ 0` is a valid upper bound
  by weak duality, so the certificate is `O(nk)`-checkable without a solver, exactly as
  `cert_power_diagram` already is (**Khachiyan1980**).

- **Does `≤ k−1` survive (U15)?** Two statements, both to `math-verify`.
  - *Coarse (rank on the unrestricted face).* At most one of the two band rows per agent is tight
    at any point with `δ > 0`, so the optimal face is described by `n` supply rows, `k` gain rows
    and `≤ k` tight band rows; a vertex has `≤ n + 2k` nonzeros, every unit has `≥ 1`, hence
    **`≤ 2k` split units**. `[claim]`
  - *Sharp (the MBB-restricted face, P3a's argument).* On the face cut out by the modified MBB
    support, the supply rows and the modified budget rows, the identity
    `Σ_z p_z·(supply)_z − Σ_i (budget)_i = k − Σ_i ν_i m_i − Σ_z p_z = 0` still contains no `x`
    (the `m_i` are constants on that face: tight bands are pinned, slack bands have `ν_i = 0` by
    complementary slackness), so one dependency survives and the count is **`≤ 2k−1`**. `[claim;
    this is `LENS_GROMOV` U15's prediction, with the argument written out]`
  - *Consequence, and the trap.* At `k = 13` that is `≤ 25` split units of 1,229 — still tiny —
    but P3b's value bound scales with `M(F)`, and its a-priori form was already vacuous at 12
    splits (`M(F)/g_min = 2.41 > 1`, `MODEL_U1-cert` P3c). At 25 it is more vacuous. **Never quote
    the count without the measured split masses** (`MODEL_U1-cert` failure mode 9).

- **Assumptions, against FRAME §5/§6.**
  | assumption | met? |
  |---|---|
  | `u_i(z)` linear in the assignment | **met** (`docs/MODEL.md`; the `g = B_j + w·b` decomposition is verified, `CODEVERIFY_U7-meas` row 2) |
  | `g_i > 0` on the feasible set | **met and improved**: P1b gives `u_i ≥ λ M_z > 0`; the lower band forces `g_i ≥ λ(1−δ)T/k` |
  | Slater / relative-interior point | **met**: `x ≡ 1/k` |
  | headroom `u_i(z) ≤ M_z` (needed only for the closed-form outer bound P1c) | **met to `4.2e-7`** at `filler="theta"`; **fails** at `filler="full"`, where the sharp correction is `+0.258` nats — material against tier 2, immaterial against the premium. FRAME §9 open item |
  | the band is the sponsor's constraint | **not met — never elicited.** FRAME §3 Tolerance offers ±10% as "generous"; `LENS_GROMOV` U12. §2.11 is built precisely so that this is not needed in advance |
  | the delivered draw is band-feasible at the frontier's left endpoint | **must be checked, and is not the published number** — see the arithmetic caveat below |
  | the roster `S₁₃` is well defined | **fragile**: the Nash matching's margin is `8.1e-3` nats on seed 9 (§2.15) |

- **The arithmetic caveat on the left endpoint.** `LENS_GROMOV` M8 writes the sandwich starting at
  `EG^bal_{S₁₃}(0.0078)`, taking FRAME §6's **spread** `(max−min)/mean = 0.781 %` as `δ`. But `δ`
  in the band is a **maximum deviation from `T/k`**, and spread and max-deviation differ by up to
  a factor of 2. **Compute `δ_0 := max_j |m_j − T/k|/(T/k)` on the committed draw before choosing
  the grid**; if `δ_0 > 0.0078`, then `EG^bal(0.0078) ≥ V(delivered)` is *false as stated* and the
  sandwich's left end is at `δ_0`, not at the spread. `EG^bal(δ)` is defined and finite for every
  `δ ≥ 0` (fractional splitting makes `δ = 0` feasible), but it bounds the delivered draw only for
  `δ ≥ δ_0`. **Cheap, and it invalidates a published inequality if it is skipped.**

- **Produces.** The number a decision actually needs: an upper bound on every *band-feasible*
  coverage at roster `S`, in nats, with a solver-free dual check and prices that are the input to
  §2.12 and §2.4. **Cannot say:** anything about a different roster (§2.14), about misreporting, or
  about error in `M` (`VERIFY_U1-cert` §6).

- **Failure mode.** Three. (i) The concave solve is a *side-constrained* Fisher program, and
  **proportional response — the solver U1-cert used — does not accept side constraints**
  (`MODEL_U1-cert` §8.2); a new solve path is required and is §2.11's subject. (ii) Degeneracy: a
  balance-tight polytope is degenerate by construction, so the returned `μ` may be one of many
  dual optima and the "which zips move first" reading (§2.12) is interpretation-fragile — the same
  caveat P2.4 already carries. (iii) If `δ` is large the program relaxes to `EG_S` and the answer
  is already known (`60.697`); if `δ` is tiny the band nearly determines `m` and the answer tends
  to `V(delivered)`. **The whole content is in the middle, which is why §2.11 and not a single
  solve is the deliverable.**

### 2.11 Tracing the frontier `δ ↦ EG^bal_{S₁₃}(δ)` as a parametric concave program **[new]**

- **Rests on:** **Rockafellar1970** and **BoydVandenberghe2004** §5.6 (the perturbation function
  and multipliers as its supergradient), **KuhnTucker1951**, **Chvatal1983** (right-hand-side
  ranging: the optimal basis is constant on an interval, and the degeneracy caveat),
  **Dantzig1963** / **Bixby2002** (warm-started dual simplex makes each step nearly free),
  **WesterlundPettersson1995** (the extended cutting-plane method: MILP/LP masters only, no NLP
  subproblem — the right architecture when no nonlinear solver is trusted),
  **DuranGrossmann1986** / **FletcherLeyffer1994** (validity and finite convergence of outer
  approximation for convex problems), **Kronqvist2016** (supporting hyperplanes from line search:
  fewer cuts on a mildly curved surface), **VigerskeGleixner2018** (SCIP's expression-graph route,
  the independent cross-check), **Mehrotra1992** / **Wright1997** (barrier, for one high-accuracy
  point), **Lemarechal1995** / **BenAmeurNeto2007** / **FischettiSalvagnin2010** (stabilisation if
  the cut loop thrashes on a flat objective). Non-FOUNDATIONS pointer: `lubin2018`.

- **Shape facts, free before any solve.** `δ ↦ EG^bal(δ)` is **nondecreasing** (the feasible set
  grows) and **concave** (the value function of a concave maximisation with a right-hand side
  affine in `δ`; **Rockafellar1970**). Its supergradient at `δ` is
  `(T/k)·Σ_{i∈S} (μ_i^+ + μ_i^-)` — the aggregate band dual. Three consequences the plan uses:
  1. **One solve bounds the whole curve.** From any `δ` with slope `s(δ)`, concavity gives
     `EG^bal(δ') ≤ EG^bal(δ) + s(δ)·(δ' − δ)` for every `δ' > δ`. **So a single solve at `δ_0`
     plus its duals can *prove* softness at the sponsor's `δ`** if
     `EG^bal(δ_0) + s(δ_0)(δ_sponsor − δ_0) − V(delivered) ≤ 5e-3`. This is the cheapest decisive
     computation in the plan and it is a certificate, not an estimate.
  2. **Bisection for `δ*` is licensed by monotonicity**, not by concavity: `EG^bal(δ) − V` is
     nondecreasing, so `δ* = min{δ : EG^bal(δ) − V > 5e-3}` is found in ~8 solves to three digits.
  3. Concavity also predicts the shape `LENS_GROMOV` M12 expects — fastest rise near `δ_0`, hence
     "not soft" — and makes the opposite reading (flat, then a jump at a large-zip threshold) a
     *falsifiable rigidity signal* rather than a hunch.

- **How to trace it on this machine (SCIP 10 via pyscipopt 6.2.1, HiGHS 1.15, scipy 1.18
  `milp`/`linprog`; no conic solver, no cvxpy).**

  **Primary — LP outer approximation, warm-started across `δ` (`WesterlundPettersson1995`,
  `DuranGrossmann1986`).** Epigraph variables `t_i`, master

  ```
  max Σ_i t_i   s.t.  t_i ≤ log ĝ_i^{(r)} + (g_i − ĝ_i^{(r)})/ĝ_i^{(r)}   ∀i, ∀ cuts r
                      + the band and supply rows of §2.10
  ```

  Each tangent is a **global overestimator** of `log` (concavity), so **every master optimum is a
  valid upper bound on `EG^bal(δ)` and hence on `V`** — the loop can be stopped at any iteration
  and still yields a certificate. That property is what makes this the right architecture for a
  bound-producing unit, and it must be tested (§3). Size: `n·k ≈ 16k` continuous variables,
  `n + 2k + (cuts)` rows — routine for HiGHS (**Bixby2002**). Warm-start each `δ` from the previous
  `δ`'s basis by dual simplex (**Dantzig1963**); the band rows are the only changing right-hand
  side, so this is textbook RHS reoptimisation (**Chvatal1983**).
  *Use **Kronqvist2016**'s line-search supporting hyperplanes if the tangent count grows; use
  **Lemarechal1995**'s level step or **BenAmeurNeto2007**'s in-out point if the loop zigzags —
  the objective is known to be near-flat, which is exactly the diagnosis **Lemarechal1995** makes.*

  **Cross-check — SCIP with native `log` (**VigerskeGleixner2018**).** Same program stated
  directly; SCIP handles the concave objective through its expression graph. Set the gap to `0.0`
  (trap 12), and read the *dual* bound, never the primal incumbent, as the certificate. If any cut
  is separated lazily, `misc/allow{strong,weak}dualreds` must be off (trap 14). A `time_limit`
  stop is **not** a bound (trap 15). Run it at two or three `δ` only — it is the independent
  second solver that U1-cert's practice requires, not the tracing tool.

  **One high-accuracy point — barrier (**Mehrotra1992**, **Wright1997**, **NesterovNemirovskii1994**).**
  Useful once, at the sponsor's `δ`, for a tight primal–dual bracket. Barrier does not warm-start,
  so it is not the frontier tool.

  **Not on the path:** anything conic (**Lobo1998**, **GunlukLinderoth2010**) — unavailable;
  ε-constraint MILP enumeration (**Boland2015**) — the wrong coordinate (§2.5); proportional
  response — cannot take side constraints.

- **Marking the MNW point (trap 2).** The curve is `(δ, EG^bal(δ))`, an upper-bound curve. Two
  points must be plotted on the same axes and labelled every time it is rendered:
  (a) **the delivered MNW draw** at `(δ_0, V(delivered) = 59.9375)` — the Nash-maximising map on
  the common measure, the programme's own committed answer; and (b) the **unconstrained** endpoint
  `(δ_max = 0.3300, EG_{S₁₃} = 60.6974)` with its `≥ 50 %` `M`-spread annotated. The objective is
  `Σ log g` at every point of the curve; **no point on it is produced by minimising a spread**,
  which is the letter of trap 2. A rendering without (a) marked has walked into trap 2 by the back
  door, and the plan says so twice on purpose.

- **Assumptions vs FRAME §5/§6.** Inherits §2.10's. Adds: (i) the tangent cuts need `ĝ > 0` at
  every iterate — guaranteed by the lower band; (ii) RHS ranging between grid points is exact for
  the LP master but **degenerate here by construction** (`MODEL_U1-cert` failure mode 5), so a
  zero-width interval must be expected and the grid must not be replaced by ranging alone;
  (iii) the sponsor's `δ` is unknown, which the frontier is designed to survive.

- **Produces.** U13, U14 and U7 in one artifact: the curve, the softness verdict against the
  tier-2 floor, `δ*` if it exists, and the duals. **Cannot say:** whether a different roster does
  better (§2.14), and nothing in business units (§2.4).

- **Failure mode.** The OA loop thrashes on the flat objective (**Lemarechal1995**) — mitigated as
  above; or the two solvers disagree beyond tier 1, in which case the *smaller* of the two valid
  upper bounds is reported and the disagreement is a finding, not a defect.

### 2.12 The band duals as the balance↔continuity exchange rate, and the first zips to move **[new]**

- **Rests on:** **KuhnTucker1951** (multipliers, complementary slackness, the active set),
  **GaleKuhnTucker1951** (shadow prices as defensible marginal values), **Chvatal1983** (ranging:
  how far a right-hand side moves before the optimal basis changes), **Rockafellar1970**
  (multiplier = supergradient of the value function), **Hitchcock1941** / **Ahuja1993** (the moved
  mass as a transportation quantity).

- **The exchange rate.** `ν_i = μ_i^+ − μ_i^-` is in **nats of `Σ log g` per unit of `M`**, and
  `(T/k)Σ_i(μ_i^+ + μ_i^-)` is the frontier's slope at `δ`. This converts the sponsor question
  from "how much continuity would you trade for balance?" (unanswerable, never elicited, FRAME §3)
  into "at `δ = 5 %` the marginal territory-dollar of balance costs `X` nats of continuity — is
  that the right `δ`?" (answerable). **A computed shadow price is not a business decision**; the
  decision stays with leadership (§7).

- **Which zips move first.** At the optimum, `supp(X) ⊆ argmax_i u_i(z)/(p_z + ν_i M_z)`. Rank
  zips by the margin `max_i u_i(z)/q_{zi} − second-max_i u_i(z)/q_{zi}`: the near-ties are the
  units whose owner flips first as `δ` moves, and the ranking is read off **one** solve by
  complementary slackness, with no second solve (`LENS_GROMOV` M11.2). Their `M`-mass is a
  displacement and is the natural input to U4-disp (§2.4).

- **Assumptions vs FRAME §5/§6.** Multiplier uniqueness is **not met**: the polytope is degenerate
  at a tight band (`MODEL_U1-cert` failure mode 5, P2.4's nondegeneracy caveat), so `ν` is one of
  possibly many dual optima. The *bound* is unaffected (weak duality holds at any dual-feasible
  point); the *interpretation* is. **Check the support size (`= n + k − 1 + #tight bands`) before
  reading `ν` as "the" exchange rate**, exactly as P2.4 requires for the power weights. Second
  assumption: `M` is a trustworthy common measure (FRAME A4) — **unaudited**, and a regional bias
  biases `p` and `ν` together, invisibly.

- **Produces.** U14; the sponsor question in answerable form; the first-mover list. **Cannot say:**
  what `δ` should be.

- **Failure mode.** If the dual is degenerate and the first-mover list is not stable across the two
  solvers of §2.11, report the *intersection* of the two lists and flag the rest as
  solver-dependent — the same discipline `MODEL_U1-cert` failure mode 9 imposes on the split set.

### 2.13 Band-aware rounding of the `EG^bal` vertex, and the criterion for a genuine MINLP **[new]**

- **Rests on:** **Danna2005** (RINS: fix the variables the relaxation makes integral, solve the
  rest exactly as a reduced MIP — this *is* the rounding step, named), **GuptaRavindran1985**
  (NLP-based branch-and-bound for a small convex integer program), **Kronqvist2018** /
  **Bonami2012** (solver choice for a small convex MINLP), **WesterlundPettersson1995** /
  **DuranGrossmann1986** (the same OA master, so no new machinery), **LandDoig1960**,
  **FischettiLodi2003** (local branching only if the reduced solve is somehow large).

- **The problem P3b does not solve.** `MODEL_U1-cert` P3b rounds each split unit to any buyer and
  bounds the loss by `−Σ_i log(1 − L_i/g*_i)`. Under a band that is **not enough**: rounding moves
  `M`-mass between districts and can push the rounded map out of the band. So the rounding step is
  itself a constrained problem:

  ```
  max  Σ_{i∈S} log( g*_i − L_i + Σ_{z∈F} u_i(z) ξ_{zi} )     ξ_{zi} ∈ {0,1},  Σ_i ξ_{zi} = 1
  s.t. the band rows on the rounded district masses
  ```

  with `|F| ≤ 2k−1 ≤ 25` and `≤ k` buyers each: **≤ 325 binaries, `2k` rows, separable concave
  objective.** That is the tractable convex-MINLP class (**Kronqvist2018**), solvable by the OA
  master already written (**WesterlundPettersson1995**) or by NLP-based B&B
  (**GuptaRavindran1985**) in seconds, with `mip_rel_gap = 0.0` (trap 12). Equivalently it is one
  RINS neighbourhood around the fractional solution (**Danna2005**).

- **The criterion (U18, `LENS_GROMOV` M13.1).** Let `γ(δ) := EG^bal_S(δ) − V(rounded, δ)`.
  - `γ(δ_sponsor) ≤ 5e-3` nats (tier 2) ⇒ **no integer programming beyond this 325-binary repair
    is needed**; §2.1 stays retired, and A1's deliverable is "a few convex programs plus rounding"
    with a certified gap. This is the expected case: the unconstrained analogue realised
    `5.1e-4`–`1.9e-3` nats (`MODEL_U1-cert` §4.3), already inside tier 2.
  - `γ(δ_sponsor) > 5e-3` and the reduced solve is already exact ⇒ the gap is **structural**, not a
    rounding artefact, and §2.1 fires: only a full rep-indexed integer model can close it. Record
    which of the two solvers produced the vertex, since `F` is vertex-dependent.
  - Report `γ` at **both** §2.11 solvers' vertices, and never quote a single-vertex `M(F)`
    (`MODEL_U1-cert` failure mode 9).

- **Assumptions vs FRAME §5/§6.** `|F| ≤ 2k−1` — a `[claim]` from §2.10, and the method degrades
  gracefully if it is wrong: `F` is whatever the solve returns and is measured, not assumed.
  Feasibility of the rounding problem is **not guaranteed** at very small `δ` (a band tight enough
  may admit no integral map at all — the integer balance floor `t*` of `cert_integer_balance_floor`
  is exactly the obstruction, and it is the one certificate that did **not** collapse into the EG
  dual, `VERIFY_U1-cert` row 4). **That is what certificate 2 is for**, and this is the first
  place in the programme where its primal-constructive content is load-bearing: if
  `t*/(T/k) > δ_sponsor` no integral band-feasible map exists and the sponsor's band is
  infeasible, which is a Farkas-style report (**Farkas1902**) the sponsor must see.

- **Produces.** A **constructive integral band-feasible map** with a certified distance to the
  best band-feasible coverage at that roster, and the decision on whether §2.1 is ever built.
  **Cannot say:** anything about other rosters.

- **Failure mode.** Infeasibility at small `δ` (handled above); or a `time_limit` on the reduced
  MIP silently reported as a bound (trap 15) — the reduced MIP is small enough that a time limit
  is itself a bug signal.

### 2.14 Roster selection by enumeration inside the `P₁₃` slack, with a closed-form screening bound **[new]**

- **Rests on:** **BoydVandenberghe2004** / **Rockafellar1970** (concavity of `log`, i.e. the AM–GM
  step), **LandDoig1960** + **NemhauserWolsey1988** (the `P₁₃` max-`k`-coverage MILP, already
  solved), **CodatoFischetti2006** (no-good cuts to enumerate near-optimal 0-1 solutions from the
  same master), **Schrijver2003** (submodularity of `S ↦ Σ_z max_{i∈S} S_i(z)`, for the greedy
  seed only), **Karp1972** (why an enumeration and not a polynomial method), **Kuhn1955** (each
  roster's downstream matching).

- **The bound that makes enumeration a search with a stop rule.** From `MODEL_U7-meas` §1,
  `u_i(z) = common(z) + w·S_i(z)` with `w = 0.42`. Since every zip is assigned exactly once, for
  any roster `S` and any feasible `X` (integral or fractional),

  ```
  Σ_{i∈S} g_i(X) = B_tot + w·Σ_z Σ_i S_i(z) x_{zi}  ≤  B_tot + w·P_S ,
        B_tot := Σ_z [ c2·T_z + c_free·S_free(z) + λ·M_z ]   (partition-invariant, O(n))
  ```

  and by concavity of `log` at fixed sum,

  ```
  EG^bal_S(δ)  ≤  EG_S  ≤  k · log( (B_tot + w·P_S) / k ).                    (★)
  ```

  `P_S` is already computed for any `S` in `O(nk)` (`coverage_premium`), and `B_tot` is one pass.
  **Two payoffs.**
  1. **A roster-free bound (U19).** Putting `P₁₃` in (★) gives
     `max_S EG^bal_S(δ) ≤ max_S EG_S ≤ k log((B_tot + w·P₁₃)/k)` — an upper bound over **all**
     `C(111,13) ≈ 10¹⁶` rosters and all maps, from numbers already in `MODEL_U7-meas` §6, with no
     new solve. Back-of-envelope from FRAME §6's published quantities this lands near **60.8**
     nats against the analytic ceiling's 69.59 — i.e. it would replace a 9.65-nat unconditional
     gap by one under 0.9 nats. **Recompute it before quoting; the arithmetic here is illustrative
     and this plan ran no code.**
  2. **A stop rule for enumeration (U16).** Enumerate rosters in decreasing `P_S` (no-good cuts on
     the `P₁₃` master, **CodatoFischetti2006**), solving `EG^bal_S(δ)` only for those whose (★)
     exceeds the best value found so far. **This is branch-and-bound over rosters with a valid
     bound**, so "enumeration within the `P₁₃` slack" stops being a heuristic restriction (the
     charter's step 2, "a restriction for tractability") and becomes a proof.

- **Why this beats `Σ y_i = k`.** The charter's step 3 puts selection inside the program as
  binaries with `x ≤ y`. (★) does the same work outside it: the selection non-convexity
  (`LENS_GROTHENDIECK` OQ3) is **bypassed by enumeration with a bound**, not solved, and the
  bound's validity does not depend on the perspective reformulation, on a conic solver, or on
  branch-and-bound behaving.

- **Assumptions vs FRAME §5/§6.** (i) The `common + w·S_i` decomposition — **met and verified**
  (`CODEVERIFY_U7-meas` row 2, `w = 0.42` at the defaults). (ii) `P_S` computed at the *unmasked*
  convention, matching `MODEL_U1-cert` §1 — **met**, but the two conventions must not be mixed.
  (iii) (★) is loose exactly where the gains are unequal, i.e. where `D(g)` is large — and the
  realised `g`-spread is **60.65 %** (FRAME §6), so (★) may be loose at the *delivered* map even
  while being tight at the *EG optimum*, whose spread is 31.06 %. **This is the method's main
  risk and it is measurable in one line.** (iv) `filler_capture` enters `common(z)`, so `B_tot`
  and hence (★) inherit FRAME §9's open item.

- **Produces.** U16 and U19; a roster-unconditional certificate, which is what `VERIFY_U1-cert` §6
  names as the exposure `MODEL_U1-cert`'s headline does not carry. **Cannot say:** anything about
  balance beyond what `EG^bal` already says — (★) itself ignores the band.

- **Failure mode.** If (★) at `P₁₃` exceeds `V(delivered) + 3.7` nats it is decorative and the
  ladder carries the whole roster bound as before. If the near-optimal roster set is large (say
  > 100), the enumeration is still cheap per roster but the *reporting* becomes an interval —
  which is §2.15's problem anyway.

### 2.15 Nash-tie fragility of `S₁₃` — the stability radius of the matching **[new]**

- **Rests on:** **Kuhn1955** (the assignment problem and its duals), **Chvatal1983**
  (objective-coefficient ranging: how far a cost entry moves before the optimal solution changes —
  the exact tool for a margin), **GaleKuhnTucker1951**, **Dantzig1963** (degeneracy and ties),
  **CodatoFischetti2006** (no-good cuts, if the near-optimal set is enumerated rather than
  bracketed).

- **The problem.** `S₁₃` is the image of the Hungarian matching, and its margin to the second-best
  matching is `1.4e-2` nats on seed 3 and **`8.1e-3` on seed 9 — 1.6× the tier-2 floor**
  (`CODEVERIFY_U7-meas` finding 4). Every `S₁₃`-conditional number — `P_S`, U4 (83 contested
  zips), U8, and now `EG^bal_{S₁₃}(δ)` and the whole frontier — is one data refresh from changing,
  and **nothing in the pipeline detects a tie**.

- **What to compute.** (i) The margin itself, exactly: the second-best assignment value, obtained
  by `k` Hungarian re-solves each forbidding one matched edge and taking the best
  (**Kuhn1955**) — milliseconds. (ii) The *set* of rosters within the tier-2 floor of the optimum,
  which is the same enumeration §2.14 already runs, so the two units merge. (iii) A tie-aware
  report: each `S₁₃`-conditional number as an **interval over that set**, not a point.

- **Assumptions vs FRAME §5/§6.** Requires only the gain matrix — met. The choice between reporting
  the margin, the interval, or both is partly a statistical question about what a data refresh
  actually perturbs (FRAME §6's U6 noise floor is still unmeasured) — §7.

- **Produces.** U17 in a form that can be attached to every published number. **Cannot say:**
  whether the perturbation that would flip the tie is realistic — that needs the noise floor.

- **Failure mode.** If the near-optimal roster set is large, every headline becomes an interval and
  the presentation problem gets worse before it gets better. That is still the honest report; the
  alternative is a point estimate that is `1.6×` the acceptance floor away from being wrong.

---

## 3. Solution concept and how it is verified

**An answer is:** a coverage `(π, σ)` — a partition of the 1,229 zips into 13 territories and an
injection into the 111 wholesalers — that is **band-feasible at a stated `δ`**, together with

1. a **nested sandwich**, each term computable and each labelled with what it is conditional on:

   ```
   V(π,σ)  ≤  EG^bal_S(δ)  ≤  min{ EG_S ,  k·log((B_tot + w·P_S)/k) }        [at roster S]
                            ≤  k·log((B_tot + w·P₁₃)/k)                       [over all rosters]
                            ≤  k·log(T/k)                                     [the analytic ceiling]
   ```

   with `V(rounded)` from §2.13 supplying the matching **lower** bound, so the reported gap is
   `EG^bal_S(δ) − V(delivered)` and the *achievability* of the bound is demonstrated, not asserted;
2. the **frontier** `δ ↦ EG^bal_S(δ)` with the delivered MNW point and the unconstrained endpoint
   both marked (trap 2), and either a softness verdict (`≤ 5e-3`) or `δ*`;
3. the **band duals** `ν_i` as the balance↔continuity exchange rate, with the support-size
   nondegeneracy check beside them, and the first-mover zip list;
4. the **`i`-th terms** of `V` for each of the 13 — FRAME §3.4's per-person continuity report,
   which is the objective's own summands, not a separate artifact;
5. the **tie margin** of `S₁₃` beside every `S₁₃`-conditional number (§2.15);
6. a statement of **what the bound does not cover**: misreporting, error in `M`, and — unless
   §2.14 ran — other rosters (`VERIFY_U1-cert` §6's added exposure).

**Verification handed to `math-verify`** (new items only; the predecessor's list is discharged by
`VERIFY_U1-cert`):

- **P1 under the band** — `EG^bal_S(δ)` upper-bounds every integral coverage with roster `S` whose
  districts respect the band. (Expected: immediate from P1 plus one feasibility check.)
- **Concavity and monotonicity of `δ ↦ EG^bal(δ)`**, and that `(T/k)Σ_i(μ_i^+ + μ_i^-)` is a
  supergradient — this is what licenses both the one-solve bound on the whole curve and the
  bisection for `δ*`. **The single most load-bearing new claim.**
- **Slater at every `δ ≥ 0`** via `x ≡ 1/k`, hence strong duality and multiplier existence.
- **The modified budget identity** `Σ_z p_z x_{zi} = 1 − ν_i m_i` and the MBB reading under
  agent-specific prices `q_{zi} = p_z + ν_i M_z`.
- **The split-unit count under the band** — `≤ 2k` coarse, `≤ 2k−1` sharp (U15). Both, separately;
  the sharp one is a `[claim]` with the dependency argument written out in §2.10.
- **The screening bound (★)** `EG_S ≤ k log((B_tot + w·P_S)/k)`, including that `B_tot` is
  partition-invariant and that the inequality survives fractional `X`. Then the roster-free
  corollary at `P₁₃`.
- **`δ_0` is a max-deviation, not the published spread** — check whether
  `EG^bal(0.0078) ≥ V(delivered)` as `LENS_GROMOV` M8 writes it, or whether the left endpoint must
  move.

**Verification handed to `code-verify`:**

- **Every OA master optimum is a valid upper bound** on `EG^bal(δ)`, at every iteration, not only
  at convergence — test by comparing against a converged reference at a small `δ` and against a
  brute-forced toy. This is the safety property the whole architecture rests on.
- `mip_rel_gap = 0.0` on the `P₁₃` MILP and on §2.13's rounding MIP (trap 12); a `time_limit` or
  solver abort is reported as *no bound*, never as a bound (trap 15); SCIP's dual reductions are
  disabled if any cut is separated lazily (trap 14).
- **Two independent solvers at the same `δ`** (OA/HiGHS and SCIP-native `log`) agree to tier 1, in
  the same style U1-cert used; on disagreement the smaller valid upper bound is reported.
- The dual certificate is checkable in `O(nk)` with no solver, matching `cert_power_diagram`'s
  existing contract — now with the `2k` band terms.
- Support-size / nondegeneracy check is *run and reported* wherever `ν` is interpreted (§2.12).
- Vertex-dependence discipline: `F`, `M(F)` and `γ` reported for both solvers' vertices, never as
  a single instance number (`MODEL_U1-cert` failure mode 9).
- The scale-invariance test still passes and `tests/test_model.py::test_two_rep_reduction` still
  pins the two-player reduction; 184 tests stay green.

---

## 4. Recommended path, with the decision points

**Stage 0 — three numbers with no solve (minutes).** `B_tot`; the screening bound (★) at `P_S` and
at `P₁₃` (§2.14 — this alone may replace the 9.65-nat unconditional gap by one under a nat);
`δ_0 = max_j |m_j − T/k|/(T/k)` on the committed draw (§2.10's arithmetic caveat). Nothing
downstream is correctly parameterised until `δ_0` is known.

**Stage 1 — one solve of `EG^bal_{S₁₃}(δ_0)` and its duals (§2.10, §2.11, §2.12).** This is
`LENS_GROMOV` U13's first point and it delivers U14 for free.
> **D1′ — the fork, replacing the predecessor's τ-homotopy D1.** Evaluate the one-solve concavity
> bound `EG^bal(δ_0) + s(δ_0)·(δ − δ_0) − V(delivered)` at the widest `δ` any sponsor would name
> (FRAME §3's ±10% is the only number on record). **If it is ≤ 5e-3 nats, the premium is soft
> across the entire plausible band and A1 is done**: hand the problem to A5 (sample the band, pick
> by staffing value, report a percentile) and record A1 `collapsed-on-softness` with the
> certificate. If it is not, continue. *This is a certificate, not a judgement call, and it is one
> solve.*

**Stage 2 — trace the frontier and find `δ*` (§2.11).** Bisection on monotonicity, ~8 solves, plus
two SCIP cross-checks. Deliverable: the `(δ, V)` curve with the MNW point marked (trap 2), `δ*`,
and the first-mover zip list at `δ*` (§2.12).

**Stage 3 — round at the sponsor's `δ` (§2.13).**
> **D2′ — does anything integer get built?** If `γ(δ) ≤ 5e-3` at both vertices, **§2.1 stays
> retired** and the track's deliverable is a certified band-feasible map. If not, and the reduced
> MIP is exact, the gap is structural and §2.1 fires with §2.14's screened roster set.
>
> *Blocking sub-case:* if `t*/(T/k) > δ_sponsor` no integral band-feasible map exists at all
> (§2.13). Report it as an infeasibility with the offending districts named (**Farkas1902**) and
> take it back to the sponsor. This is the one place `cert_integer_balance_floor` — the
> certificate that did not collapse — is load-bearing.

**Stage 4 — the roster (§2.14, §2.15).** Enumerate rosters in decreasing `P_S` under (★)'s stop
rule; solve `EG^bal_S(δ)` for the survivors; compute the Nash-tie margin and re-report every
`S₁₃`-conditional number as an interval over the near-optimal set.

**Stage 5 — U10 on the frontier, and the units (§2.4).** Score the hand-drawn state-grouped
baseline (FRAME §3, never constructed) as a **point on the `(δ, V)` plane**, not as a `V`
comparison — `LENS_GROMOV` M11.3. Then displacement.
> **D3′ — acceptance unit, unchanged.** Nats internally, displacement for anything a sponsor
> reads — but valid only if §2.4's modulus lands. It has not. Until then the certified statement
> stays in nats and the displacement statement is labelled descriptive.

**D4′ — the book decision, restated more sharply than the predecessor could.** Both §2.10 and
§2.14 read `u_i`, hence books. `LENS_GROMOV` M13.2 localises the exposure exactly: **the only
place books enter the draw is the objective of one concave program.** The optimisation methods are
indifferent to which book they are handed — reported, audited, or `G`-invariant normalised
profiles. So the decision blocks *deployment*, not *formulation*: build against reported book,
deploy against whatever the user rules admissible, record the assumption (§8 Q7 keeps this open).

**Not on the path:** §2.1 (contingency, D2′), §2.5's MILP frontier (replaced), §2.6 (retired),
§2.7 beyond the RINS repair, §2.8 (blocked on A4), §2.9 (deferred), all of FOUNDATIONS §8's
contiguity machinery (dormant).

---

## 5. Numbers to compute first (cheap, decisive)

Re-cut to `LENS_GROMOV`'s recommended order — **U13 → U18 → U16 → U10-on-the-frontier** — with the
three zero-cost items ahead of them. The predecessor's rows 1–4, 6 and 9 are **done** (U7-meas,
U1-cert); rows 5, 7 and 8 survive and are placed below.

| # | number | method | why it is decisive |
|---|---|---|---|
| 0a | `B_tot` and the screening bound (★) at `P_S` and at `P₁₃` | one `O(n)` pass + arithmetic on `MODEL_U7-meas` §6's numbers; **no solve** (§2.14) | answers **U19** — the roster-free bound nothing but the 9.65-nat ceiling currently supplies. Free. |
| 0b | `δ_0 = max_j |m_j − T/k|/(T/k)` on the committed draw | one line | `LENS_GROMOV` M8's sandwich is written with the *spread* (0.0078) in a *max-deviation* slot; if `δ_0 > 0.0078` a published inequality is false and every grid below `δ_0` is meaningless |
| 0c | the Nash-tie margin of `S₁₃` on both draws | `k` Hungarian re-solves (**Kuhn1955**) | **U17**: `8.1e-3` nats is already known on seed 9; the margin must be attached to every `S₁₃`-conditional number before any of them is published |
| 1 | **`EG^bal_{S₁₃}(δ_0)` and its band duals** | §2.11 primary route, one OA solve (**WesterlundPettersson1995**) | **U13's first point + U14 + D1′.** With the concavity slope it can *prove* softness over the whole plausible band in one solve, killing or confirming A1 outright |
| 2 | the frontier on `{δ_0, 0.02, 0.05, 0.10, δ_max}` + bisection for `δ*` | ~8 warm-started solves (**Chvatal1983**, **Dantzig1963**, **Bixby2002**) + 2 SCIP cross-checks (**VigerskeGleixner2018**) | **U13** in full; the softness verdict against tier 2; the shape (concave-rising vs flat-then-jump) is itself a finding |
| 3 | **`γ(δ_sponsor)`** — the band-aware rounding gap, in nats and in moved `M` | §2.13, ≤ 325-binary MIP (**Danna2005**, **GuptaRavindran1985**) | **U18** and **D2′**: decides whether any integer programming is built at all |
| 4 | the first-mover zips at `δ*` and their `M`-mass | read off #1's duals (§2.12) | **U14**; the input to U4-disp and the sponsor conversation |
| 5 | `EG^bal_S(δ)` at the `P₁₃` roster and at every roster surviving (★) | §2.14, tens of solves | **U16**; bypasses `LENS_GROTHENDIECK` OQ3's non-convexity by a *bounded* enumeration |
| 6 | the hand-drawn state-grouped baseline as a point `(δ, V)` | construct + evaluate | **U10** in its corrected form (`LENS_GROMOV` M11.3). The headline claim "better than what we'd have done anyway" is still unevidenced |
| 7 | `EG_R` — the relaxation over all 111 reps | one solve, if (★) at `P₁₃` turns out loose | predecessor row 7; **(★) may make it unnecessary**, which is the cheaper outcome. Threshold recorded: useful only below `63.637` (`MODEL_U1-cert` §4.4) |
| 8 | displacement between dots and cells | transportation solve (**Hitchcock1941**) | predecessor row 8, unchanged; converts a `4.66e-5`-nat non-decision into a first-order quantity |

---

## 6. Search brief for `lit-search`

**Status of the predecessor's brief.** `docs/LIT_optimization.md` does not exist; U0-lit never ran.
Of its nine questions: **Q1 (EG/Fisher as a convex program)** and **Q5's split-unit half** are
answered internally by U1-cert (`eisenberg1961`, `brieden2017` Lem. 4 stand as cited);
**Q2, Q3, Q4, Q6, Q8, Q9** are **retired or demoted** — Q2 and Q3 because selection is now an
enumeration with a bound (§2.14), Q4 because the exact MILP closed, Q6 and Q8 because the
rep-indexed MINLP is retired, Q9 because the two-stage fidelity question was answered numerically
(`0.760` nats, bought with `≥ 50 %` spread). **Q5's power-diagram half and Q7 (the displacement
modulus) carry forward unchanged.** The new brief below is what A1 actually needs.

**What FOUNDATIONS does not cover that this problem needs.** FOUNDATIONS is strong on MILP/MINLP
machinery, LP/convex duality, flows and districting-with-contiguity, and **silent** on:
market-equilibrium convex programs *with side constraints*, the perturbation analysis of such
programs, integral rounding of constrained equilibria, and selection over markets. Those are the
brief.

**Questions, stated precisely enough to search.**

1. **Eisenberg–Gale / Fisher markets with per-agent quantity or capacity constraints.** Is
   `EG^bal_S` a named object? Candidate names: *constrained Fisher market*, *Fisher market with
   capacity constraints*, *EG with side constraints*, *pseudo-market / approximate CEEI with
   constraint sets* (`budish2011` is the nearest thing already in our bib), *market equilibrium
   with quotas*. Specifically: (a) does the equilibrium/price reading survive as the
   agent-specific effective price `q_{zi} = p_z + ν_i M_z`? (b) is there an equilibrium existence
   theorem, or only a convex-program optimum? (c) is there a combinatorial or proportional-response
   algorithm that accepts the side constraints, since the standard one does not? **Bears on §2.10
   — whether A1's certificate is a citation plus one solve or a construction.** *tag hint:
   foundation / tool-we-lack.*
2. **Support / split-unit bounds for constrained market equilibria.** The unconstrained bound is
   `≤ k−1` (the linear-Fisher forest argument, `brieden2017` Lem. 4). Is the generalisation
   "`≤ k−1 + #tight side rows`" published, for EG, for capacity-constrained transportation, or for
   constrained clustering? **Bears on §2.10's U15 claim and on §2.13's problem size.** Also fetch
   the canonical citation for the `≤ k−1` argument itself so `math-verify` cites rather than
   re-proves (`MODEL_U1-cert` §8.4).
3. **Perturbation / comparative statics of the constrained EG value function.** Is
   `δ ↦ EG^bal(δ)` — the value of a market equilibrium as its capacity band widens — studied as an
   object? Concavity and the multiplier-as-slope are textbook (**Rockafellar1970**,
   **BoydVandenberghe2004**); what is wanted is any result on its *shape* (piecewise-smooth
   structure, breakpoints, the identity of the first goods to move), which would turn §2.12's
   first-mover list from a computation into a characterisation. **Bears on §2.11, §2.12.**
4. **Rounding a fractional constrained-equilibrium allocation to an integral one, under the same
   constraints, with a value guarantee.** The unconstrained version is P3b; the constrained version
   is §2.13's MIP. Is there a rounding theorem — dependent rounding, iterative rounding, or a
   basis-based argument — that gives a bound better than "solve the small MIP"? **Bears on §2.13
   and on whether U18 needs a solver at all.**
5. **Selecting the agent set: `max_{|S|=k} EG_S`.** Is `S ↦ EG_S` (or `EG^bal_S`) known to be
   submodular, subadditive, or to admit any concave-envelope bound? Our (★) bound is elementary
   (AM–GM through the ladder's `P_S`); has it appeared, and is there a sharper one? **Bears on
   §2.14, U16, U19, and `LENS_GROTHENDIECK` OQ3.**
6. **Solving concave `Σ log` programs without a conic solver, at `n·k ≈ 16k` variables.** Practice
   for: SCIP's native `log` on a pure-continuous concave program (**VigerskeGleixner2018**); LP
   outer approximation / ECP for concave *maximisation* where every master is a valid bound
   (**WesterlundPettersson1995**, **Kronqvist2016**, `lubin2018`); stabilisation on near-flat
   objectives (**Lemarechal1995**, **BenAmeurNeto2007**). Wanted: reported cut counts, accuracy,
   and any warning about tangent-based bounds at near-degenerate optima. **Bears on §2.11 —
   the only engineering risk left in the plan.**
7. **Stability radius / second-best margins for the linear assignment problem** — how to report a
   `1.6×`-floor tie honestly, and whether "the set of optimal solutions within ε" has a standard
   name and enumeration method. **Bears on §2.15, U17.** *(A statistics half of this goes to §7.)*
8. **[carried]** Power diagrams, constrained least-squares assignment, and whether the solver-free
   `O(nk)` cell certificate survives at `τ > 0` and under a band — i.e. are the cells of
   `EG^bal_S` generalized/anisotropic power diagrams? (`aurenhammer1998`, `brieden2017`,
   `borgwardt2017` are the entries already in our bib.) **Bears on §2.10's `O(nk)` dual check and
   `LENS_GROTHENDIECK` OQ2.**
9. **[carried]** Stability, displacement and inverse optimization: any result of the form
   `objective-gap ≥ φ(mass that must move)` for assignment or partitioning. **Bears on §2.4, §8 Q3
   — still the plan's highest-leverage unknown for FRAME §3.5.**

**Literatures to sweep.** *Venues:* Mathematical Programming, Math. Programming Computation,
Operations Research, INFORMS J. on Computing, SIAM J. Optimization, EJOR, Discrete Optimization,
Management Science; ACM EC, SAGT, WINE, ITCS, Games and Economic Behavior, J. Political Economy
(for 1, 2, 4, 5); Discrete & Computational Geometry, SIAM J. Imaging Sciences (for 8);
Optimization Methods and Software, J. Global Optimization (for 6).
*Keywords:* constrained Fisher market; Eisenberg–Gale with side constraints; capacity-constrained
market equilibrium; pseudo-market with constraint sets; approximate CEEI; equilibrium computation
with quotas; support size of market equilibrium; transportation forest / basis structure; value
function of a parametric convex program; comparative statics of competitive equilibrium; iterative
rounding of fractional allocations; submodularity of market welfare in the agent set;
max-k-coverage screening bound; extended cutting plane; supporting hyperplane algorithm;
polyhedral approximation mixed-integer convex; stability radius assignment problem; k-best
assignments; capacity-constrained power diagram; semi-discrete optimal transport; inverse
optimization.
*Canonical anchors already in FOUNDATIONS to walk citations from:* **BoydVandenberghe2004**,
**Rockafellar1970**, **KuhnTucker1951**, **GaleKuhnTucker1951**, **Chvatal1983**,
**NesterovNemirovskii1994**, **WesterlundPettersson1995**, **DuranGrossmann1986**,
**Kronqvist2016**, **VigerskeGleixner2018**, **Kronqvist2018**, **Danna2005**,
**CodatoFischetti2006**, **NemhauserWolsey1988**, **Hitchcock1941**, **Kuhn1955**,
**Schrijver1986**, **Lemarechal1995**, **BenAmeurNeto2007**.
*Anchors already in our bib to deduplicate against and walk from:* `eisenberg1961`, `brieden2017`,
`budish2011`, `aurenhammer1998`, `borgwardt2017`, `lubin2018`, `peyre2019`.

**Deliverable.** Entries as `citation · venue/year · DOI · 2–4 sentence annotation naming which §2
method or §4 decision point it bears on · tag ∈ {foundation, frontier, contradicts-or-sharpens,
tool-we-lack}`. Plus a **five-paper shortlist** — the five that would change what gets built.
**Every absence claim must state where it looked** (venue, keyword, years), because the
programme's own recon (`RESEARCH_FINDINGS` §0.5) already went stale once, and because Q1's answer
being "no" is itself a publishable-shaped finding that must be defensible. Write
`docs/LIT_optimization.md` and append to `docs/RESEARCH_ADDITIONS.bib`; deduplicate against
`docs/LIT_economic-theory.bib`, `docs/RESEARCH_ADDITIONS.bib` and `docs/RESEARCH_FINDINGS.md`.

---

## 7. Out of this domain — hand to

| item | to | why |
|---|---|---|
| **The CEEI reading of the band multipliers** — in a competitive equilibrium with quantity constraints, is `ν_i` interpretable as a price the *sponsor* pays for balance, and is there a welfare-theoretic reading of "the first goods to move as a capacity band loosens"? (`LENS_GROMOV` OQ3, U12) | **economic-theory** | §2.12 computes the multiplier; what it *means* to an equal-entitlement market is not an optimisation question. `DOMAIN_economic-theory` §2.2 owns the EG/CEEI interpretation and does not yet have the constrained version. |
| **Is `S ↦ EG^bal_S` near-modular over near-optimal rosters?** (`LENS_GROMOV` OQ4, U16/U19) | **economic-theory / optimization jointly** | §2.14 supplies a *valid* bound (★) that makes enumeration sufficient regardless; the structural question — why book disjointness (83 contested among 13) makes selection nearly separable — is a welfare-structure question. `/research-plan` arbitrates. |
| **The audited-vs-reported book split; `G`-invariance of the *duals* rather than of the map; what `fotakis2014` forbids once books enter only one concave objective** (`LENS_GROMOV` OQ6, `LENS_GROTHENDIECK` §5b, FRAME §10 Q5) | **mechanism design / economic-theory** | Every method here is indifferent to which `S` it is handed. **Still the paper-shaped question in the file**, and now sharper: the exposure is one objective, not a MINLP. |
| **The tie-report convention** — margin, interval over near-optimal rosters, or both; and what a data refresh actually perturbs (`LENS_GROMOV` OQ5, U17, U6) | **statistics / econometrics** | §2.15 computes the margin exactly. Whether `8.1e-3` nats is *close* depends on a noise floor that has never been measured (FRAME §10 Q4). |
| **U5 / A4 — regional bias in `M`** | **data-science, then back here** | §2.8 needs a `δ` before it is anything but decoration, and `VERIFY_U1-cert` §6 confirms the bias is invisible to every certificate. |
| **U12 — choosing `δ`** | **the sponsor** (via the user) | §2.11 draws the frontier and §2.12 prices the axis; only leadership picks the point. FRAME A6's operational-rule question is the same ask in different clothes. |
| **Contiguity on the full ZCTA graph** (FRAME §10.6, §9-H) | **applied-math / geometry**, out of scope (FRAME §7) | FOUNDATIONS §8 is seeded for it and dormant. |

---

## 8. Open questions (inputs to `/research-plan`)

Numbering keeps the predecessor's Q3, Q4 and Q7 (referenced from `docs/units/*` and
`docs/APPROACHES.md`); Q1, Q2, Q5, Q6 are answered and restated as such; Q9–Q12 are new.

1. **~~Does the homotopy answer the whole thing?~~ — withdrawn.** §2.6 is retired; the question is
   replaced by **D1′** (§4): does the one-solve concavity bound prove softness across the plausible
   band? That is now the first fork and it is a certificate.
2. **~~Is the rep-indexed perspective formulation new or published?~~ — demoted.** §2.1 is a
   contingency; the question only matters if D2′ fires. §6 Q1 replaces it as the "is our object
   published?" question, now asked of `EG^bal_S` instead.
3. **Does §2.4's modulus exist?** *(unchanged, and still the plan's highest-leverage unknown for
   FRAME §3.5.)* Everything about acceptance in business units rests on
   `objective-gap ≥ φ(mass moved)`. §2.12 gives U4-disp a better input — duals in nats per unit of
   `M`, and a first-mover list that *is* a displacement — but proves nothing. Either §6 Q9 returns
   it, or a `math-verify` unit attempts it, or acceptance stays in nats.
4. **Do the four existing certificates collapse into one dual?** **Answered: three of four.**
   `cert_integer_balance_floor` does not (its LP root bound is vacuous; `VERIFY_U1-cert` row 4),
   and §2.13 now shows its resistance is *useful*: it is the feasibility obstruction for a
   band-tight sponsor request. The note's replacement structure is **one duality gap with two
   sides** (`MODEL_U1-cert` §6), and the remaining question for `/research-plan` is editorial —
   how many pages does the note shorten by.
5. **~~Is `EG_R` loose or useful?~~ — probably moot.** §2.14's (★) at `P₁₃` gives a roster-free
   bound with no solve; `EG_R` is worth one solve only if (★) lands above the `63.637` threshold
   (`MODEL_U1-cert` §4.4). Row 7 of §5 is conditional on that.
6. **~~Roster moves or zip moves?~~ — answered: neither, at this map.** `P₀ = P*(A)` exactly on
   seed 3, so relabelling buys nothing; the map holds 0.64 nats but it is bought with balance. The
   live version is **how much of the 0.64 survives the band**, which is U13.
7. **Does D2/D4′ actually block anything?** *(unchanged, and now easier to defend.)* My reading is
   still no — the methods are indifferent to which `S` they read, and `LENS_GROMOV` M13.2 pins the
   exposure to a single concave objective. If `/research-plan` disagrees, §2.10 and §2.14 both
   stall on a user answer. Worth resolving explicitly rather than by default.
8. **Scope check on §2.8.** Robustness to `M`-bias is the only method here with no input and now
   with confirmed invisibility to every certificate. **Cut it from the plan, or carry it as
   blocked?** My recommendation: carry it as blocked, one line, because `VERIFY_U1-cert` §6 makes
   it the largest *unpriced* exposure in the programme.
9. **Is the `≤ 2k−1` split bound worth a unit of its own, or a paragraph inside U13?** It is a
   `[claim]` with an argument (§2.10) and its only consequence is §2.13's problem size, which is
   trivial either way. My recommendation: a paragraph, verified alongside U13, not a unit.
10. **What is the sponsor's `δ`, and is the band even feasible integrally?** §2.13's blocking
    sub-case (`t*/(T/k) > δ_sponsor`) is the first time the programme could have to tell the
    sponsor their stated tolerance admits no map. It should be checked *before* the sponsor is
    asked for a number, so the ask can be phrased with the feasible range attached.
11. **Does the (★) screening bound already exist?** If §6 Q5 returns it, §2.14 is a citation and
    the roster question closes this week. If not, it is a small original result about *this*
    utility structure (`common + w·S_i`) and belongs in the note. Either way it should be computed
    before it is searched for — it costs one pass over the instance.
12. **Should A1's charter text be rewritten now?** `LENS_GROMOV` M13 says the charter's step 3
    ("MINLP", "jointly") no longer describes what the track will build, and its own recommendation
    is to rewrite step 3 **after** U13, not before. This plan assumes that ordering. If
    `/research-plan` wants `APPROACHES.md` §A1 amended earlier, it should say so, because the
    charter is what every downstream unit reads verbatim.
