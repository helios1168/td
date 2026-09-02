# optimization plan — the national channel territory problem

**Date:** 2026-09-02 · **Framework:** 0.1-dev · **Reads:** `docs/FRAME.md`,
`docs/LENS_GROMOV.md`, `docs/LENS_GROTHENDIECK.md`, `~/resources/optimization/FOUNDATIONS.md`
(113 entries, seeded 2026-09-02) · **Supersedes:** none

**Citation rule.** Every citation below is a bold key from `~/resources/optimization/FOUNDATIONS.md`.
Anything the lenses cite that is *not* in that file (`brieden2017`, `aha1998`, `alpers2015`,
`fotakis2014`, `marshall2011`, Eisenberg–Gale, Nemhauser–Wolsey–Fisher) is deliberately left
uncited here and appears in the §6 search brief instead.

**One-sentence position.** The lenses agree that the programme optimised the small term; in this
domain that is not a philosophical problem but a *formulation* problem, and the fix is a single
rep-indexed concave-objective MINLP whose staffing indicators carry a perspective reformulation
— everything built so far (transportation LP, power weights, Hungarian match, four certificates)
reappears inside it as a relaxation or a fixed-variable restriction rather than being discarded.

---

## 1. What the lenses handed over, in this domain's terms

| lens construct | becomes | or "no counterpart, because" |
|---|---|---|
| **Coverage / composite value `V(π,σ)`** (Groth §3) | the objective of a mixed-integer **nonlinear** program: `max Σ_i y_i log g_i`, `g_i = Σ_z u_i(z) x_{zi}` linear, `x,y` binary. Concave objective over a MILP-representable set — the tractable MINLP class (**Kronqvist2018**, **DuranGrossmann1986**) | — |
| **Fiber/base split `Σ log g = n log ḡ − D(g)`** (Gromov M3) | an objective decomposition into a **linear** part (the premium `P`, linear in `x`) and a **Schur-convex penalty** `D(g)` on the gain vector. Optimisation reading: linear objective + inequality penalty ⇒ a natural biobjective MIP (**Boland2015**) and a natural Benders master/sub split (**Benders1962**, **Geoffrion1972**) | — |
| **Eisenberg–Gale / Fisher-market fiber** (Groth §2 step 2) | the **continuous concave relaxation** of the above at fixed roster: a smooth convex program solved by barrier (**Mehrotra1992**, **Wright1997**, **NesterovNemirovskii1994**, **BoydVandenberghe2004**), whose KKT multipliers are per-zip prices (**KuhnTucker1951**, **Rockafellar1970**). Its value is the fiberwise upper bound | the *market* interpretation itself has no counterpart in FOUNDATIONS — §6 search item |
| **Relativisation over the roster `{EG_S}`** (Groth §4) | a **cardinality-constrained program with indicator variables**: `Σ_i y_i = k`, `x_{zi} ≤ y_i`. Exactly the setting of **FrangioniGentile2006** / **GunlukLinderoth2010** — an indicator switching on a nonlinear term. The relaxation `EG_R` over all 111 is the base relaxation | — |
| **Roster bound `P₁₃ = max_{|R|=13} Σ_z max_{i∈R} S_i(z)`** (Gromov M4) | a **max-`k`-coverage MILP**: 111 binaries, 1,229 continuous, LP-relaxation-tight enough to solve exactly in seconds (**LandDoig1960**, **NemhauserWolsey1988**). Submodularity (**Schrijver2003**) supplies the greedy fallback but is *not needed* at this size | — |
| **`P₀`, `P*(A)`** (Gromov M4 ladder) | `P₀` is evaluation; `P*(A)` is a **linear assignment problem** on premium weights — **Kuhn1955**, exact in milliseconds, and the same routine already in `td/channel.py:288` with different weights | — |
| **Displacement metric** (Groth §5a) | a **transportation / min-cost-flow problem** between two partitions (**Hitchcock1941**, **Ahuja1993**, **Orlin1993**); integral automatically by total unimodularity (**Schrijver1986**). Displacement *bounds* come from LP duals and RHS ranging (**GaleKuhnTucker1951**, **Chvatal1983**) | — |
| **τ-deformation, modulus in τ** (Groth OQ1) | **parametric programming / sensitivity analysis**: objective-coefficient ranging along the ray `u_i(τ)` (**Chvatal1983**), with warm-started dual simplex reoptimisation (**Dantzig1963**, **Bixby2002**). Barrier does *not* warm-start (**Mehrotra1992**) — use simplex for the homotopy | — |
| **Power diagram / the 132 dots** (`937460e`, Groth §2) | the fixed-centers assignment is a **transportation problem**, hence TU-integral (**Schrijver1986**, **Hitchcock1941**); the duals are the power weights. The gap between the drawn map and its cells is a displacement, not a nat | the *equivalence theorem* (constrained least-squares ≡ power diagram) is not in FOUNDATIONS — §6 |
| **Balance↔continuity exchange rate `U12`** (Gromov ledger) | the **Pareto frontier** of a biobjective MIP in `(P, balance)` — **Boland2015** enumerates it exactly by ε-constraint MILPs | the *elicitation* is a business act, not an optimisation |
| **Tier-2 tolerance `5e-3` nats, `U6`** (Gromov M2, Groth §5a) | in this domain, two distinct objects that the programme conflates: the **solver gap** (`mip_rel_gap`, must be `0.0` — trap 12; **LandDoig1960**, **AchterbergWunderling2013**) and the **acceptance tolerance** (a statistical object). Only the first is ours | the noise floor's calibration is not an optimisation question |
| **Inflation group `G` and its invariants** (Groth §5b) | **no counterpart.** Restricting the drawing to read only `G`-invariant statistics is a *change of input data*, not of formulation — every method in §2 is indifferent to which `S` it is handed | mechanism design — §7 |
| **`U5`: regional bias in the sizing estimate `M`** | **uncertainty in the objective/constraint coefficients** ⇒ robust counterpart with a budget of uncertainty (**BertsimasSim2004**), which stays inside MILP; or ellipsoidal/conic (**BenTalNemirovski1998**, **Lobo1998**) if a covariance is credible | — |
| **547 components / "the glue is worthless"** (Groth §5, FRAME §10.6) | with contiguity dropped, **no counterpart** — no connectivity constraint is imposed, so no cut family is separated. Section 8 of FOUNDATIONS (**ValidiBuchanan2022**, **Buchanan2018**, **Rehfeldt2019**, **Shirabe2005**) is dormant, not deleted | reopened only by the full-ZCTA experiment |
| **The hand-drawn baseline `U10`** (Gromov M4) | a **warm start / MIP start**, and the seed for **local branching** (**FischettiLodi2003**) and **RINS** (**Danna2005**) — a premium-greedy incumbent is exactly what an LNS wants to improve | — |
| **"Five certificates is a symptom"** (Groth yoga) | correct in this domain's terms: certificates 1–4 are **restrictions and degenerations of one LP/convex dual**. The unification is a duality statement (**GaleKuhnTucker1951**, **Rockafellar1970**), not a new construction | — |

---

## 2. Candidate methods

### 2.1 Rep-indexed formulation with a perspective reformulation of the staffing indicator — **the centrepiece**

- **Rests on:** **GunlukLinderoth2010** and **FrangioniGentile2006** (perspective reformulation of
  a nonlinear term switched by an indicator; convex hull for separable constraints, conic-
  representable), **Vielma2015** (formulation strength, ideal formulations), **DuranGrossmann1986**
  / **FletcherLeyffer1994** (finite convergence of outer approximation for convex MINLPs linear in
  the binaries), **QuesadaGrossmann1992** / **Bonami2008** (single-tree LP/NLP branch-and-bound,
  the fix for repeated master re-solves), **LandDoig1960**, **Kronqvist2018** (solver choice).
- **The formulation.** Index territories by *reps*, not by anonymous labels. `x_{zi} ∈ {0,1}` =
  zip `z` is covered by rep `i`; `y_i ∈ {0,1}` = rep `i` staffs the channel.

  ```
  max   Σ_i  y_i · log(g_i / y_i)                    (perspective of log)
  s.t.  Σ_i x_{zi} = 1                    ∀z         (partition)
        x_{zi} ≤ y_i                      ∀z,i       (only staffed reps cover)
        Σ_i y_i = k = 13                              (roster size)
        g_i = Σ_z u_i(z)·x_{zi}                       (gains, linear)
        [ optional: ρ·C(x) compactness penalty, convex ]
  ```

  On binaries `y_i log(g_i/y_i) = y_i log g_i` exactly, so this is the same objective; its
  continuous relaxation is the tightest concave envelope of the on/off log term
  (**GunlukLinderoth2010**), and the term is exponential-cone / SOCP-representable
  (**Lobo1998**, **NesterovNemirovskii1994**).
- **Two structural payoffs, both new.**
  1. **The `S_k` label symmetry disappears.** Territories are named by their rep, and reps are
     distinguishable precisely because `u_i ≠ u_j` — i.e. *because* saturation is 41.9%. The
     symmetry hazard `CLAUDE.md` names as "the new hazard" is a `τ=0` pathology; at `τ≈0.42`
     the formulation is asymmetric by construction. (Residual symmetry survives only among reps
     with identical books, which the export makes rare.)
  2. **The two stages become fixed-variable restrictions.** Fixing `y` recovers stage 2; fixing
     `y` *and* linearising `log` at a target gain recovers the transportation LP in
     `td/solvers/centers.py`. Nothing built is thrown away; it becomes warm-start and
     restriction.
- **Assumptions, against FRAME §5/§6.** (i) `u_i(z)` linear in the assignment — met, `MODEL.md`;
  (ii) `g_i > 0` at every feasible point — met while every territory holds `λ·M > 0` mass, and
  guarded by a lower bound on `g_i` from the incumbent (trap 14); (iii) size: 1,229 × 111 =
  136,419 binaries if the roster is free. **Not met as stated** — see failure mode.
- **Produces.** A single optimum of the objective the business actually signs, with a
  branch-and-bound gap that is a bound on *everything* (balance, premium, compactness jointly).
  **Cannot say:** anything about misreporting, and nothing about `M`'s own validity (§7, U5).
- **Failure mode.** 136k binaries with a near-flat objective is the classic cut-loop thrash
  (**Lemarechal1995** diagnoses exactly "nearly flat near the optimum"; **BenAmeurNeto2007** and
  **FischettiSalvagnin2010** give the cheap in-out stabilisation). Mitigations, in order:
  restrict the roster to a candidate set from §2.3's `P₁₃` solve (111 → ~25–30, i.e. ~35k
  binaries); restrict `x_{zi}` by geographic locality to the reps whose current cells are near
  `z`; single-tree architecture (**QuesadaGrossmann1992**) rather than multi-tree; and
  `mip_rel_gap = 0.0` only on the final certification run (trap 12).

### 2.2 The fixed-roster concave relaxation as the fiberwise upper bound (the "certificate 5" collapse)

- **Rests on:** **BoydVandenberghe2004** (recognising and dualising the concave program),
  **KuhnTucker1951** / **Rockafellar1970** (multipliers as per-zip prices, Fenchel duality where
  LP duality does not reach), **Mehrotra1992** / **Wright1997** (the barrier solve),
  **NesterovNemirovskii1994** (polynomial-time guarantee for the conic form),
  **Khachiyan1980** (separation ≡ optimisation, licensing an `O(nk)`-checkable dual certificate).
- **Assumptions.** Concavity of `Σ log g_i` in the fractional assignment — holds, `log` of a
  linear map. Fractional feasibility relaxes integrality; the descent back to an integral
  partition costs at most `k−1` split zips per the lens's `[standard]` claim, **which is not in
  FOUNDATIONS and must be sourced (§6) or proved (`math-verify`)**.
- **Produces.** One duality gap that dominates certificates 1–4: at `u_i ≡ λM` it degenerates to
  the analytic balance ceiling, and with `ρ·C` to the power-diagram bound. The gap is
  `O(nk)`-checkable from the duals, i.e. solver-free, exactly as `cert_power_diagram` already is.
  **Cannot say:** whether a *different* roster does better — that is §2.3 and §2.1.
- **Failure mode.** Barrier does not warm-start (**Mehrotra1992**), so this is a per-roster cost,
  not something to embed in branch-and-bound; if `g_i → 0` for a starved rep the log barrier and
  the objective fight each other and the solve becomes ill-conditioned. Guard with a strictly
  positive lower bound on `g_i`, not with a tolerance.

### 2.3 The roster ladder `P₀ ≤ P*(A) ≤ P₁₃ ≤ P_free` — three small exact solves

- **Rests on:** **Kuhn1955** (`P*(A)`: Hungarian on premium weights — same code, different
  weights), **LandDoig1960** + **NemhauserWolsey1988** (`P₁₃` as a max-`k`-coverage MILP),
  **Karp1972** (it is NP-hard in general, which is why we solve *this* instance rather than
  claim a polynomial method), **Schrijver2003** (submodularity, for the greedy fallback only).
- **Simplification against the lens.** `LENS_GROMOV` proposes greedy + a monotone-submodular
  marginal certificate (~1.8M marginal evaluations). At 111 binaries and 1,229 coverage
  continuous variables the **exact** MILP is smaller than the certificate machinery and gives a
  true optimum instead of a `(1−1/e)` guarantee. Recommend the MILP; keep greedy as a warm start.
- **Assumptions.** None beyond nonnegative `S_i(z)` — met.
- **Produces.** The missing upper bound on the premium (FRAME §10.3), unconditional over all
  `C(111,13) ≈ 10¹⁶` rosters, plus a **candidate roster set** that prunes §2.1 from 111 reps to
  the reps appearing in near-optimal `P₁₃` solutions (enumerate via solution pool / no-good cuts,
  **CodatoFischetti2006**).
- **Failure mode.** The bound ignores balance and geometry entirely, so if `S_i` and `M` are
  strongly correlated (**U8**) it is loose in a way that is not small — the lens's own escape
  clause. Measure `corr(S_i, M)` first (§5).

### 2.4 Displacement as the acceptance unit, derived from duals

- **Rests on:** **Hitchcock1941** (the transportation problem *is* the distance between two
  assignments), **Kuhn1955**, **Ahuja1993** / **Orlin1993** (min-cost flow when the move carries a
  cost as well as a mass), **Schrijver1986** (TU ⇒ integral, so "mass moved" is a count of zips
  and their `M`, not a fraction), **Chvatal1983** (RHS/objective ranging: how far a parameter
  moves before the optimal plan changes), **GaleKuhnTucker1951** (shadow prices as the
  translation layer).
- **Assumptions.** That a *lower* bound on displacement-to-any-better-coverage can be read from
  the §2.2 duals. **This is the one genuinely unproved step in this plan** — it needs either a
  literature result (§6, "stability radius / inverse optimization") or a `math-verify` unit
  establishing a modulus `objective-gap ≥ φ(mass moved)`. Without it, displacement is a
  *descriptive* metric only.
- **Produces.** FRAME §3.5 in the units a sponsor signs: "no achievable map beats this one by
  more than `$Y` of misplaced book / `X`% of a territory's opportunity". Also FRAME §3.4 free:
  per-rep continuity is the `i`-th term of `V` at `λ=0` (Groth descent 8).
- **Failure mode.** Descriptive displacement between two given maps is trivial and always
  available; the *bound* may simply not exist in usable form, in which case acceptance stays in
  nats and §3.5 is answered by §2.1's branch-and-bound gap translated through the near-equality
  rung instead.

### 2.5 The `(premium, balance)` Pareto frontier — the exchange rate the business never stated

- **Rests on:** **Boland2015** (triangle splitting: exact criterion-space enumeration of a
  biobjective MIP's frontier via a sequence of ε-constraint MILPs), **Vielma2015** (encoding the
  band), **FischettiLodi2003** (warm-starting each ε-solve from the previous).
- **Assumptions.** Both objectives MILP-representable: premium `P` is *linear*; balance is
  representable as a band (max/min gain constraint) — met. The Nash objective itself need not be
  linearised, because each ε-solve maximises the linear `P` subject to a balance band.
- **Produces.** A curve the sponsor can point at, which is the only honest way to settle **U12**;
  the committed draw and the hand-drawn baseline both plot as points on the same axes, which is
  also the cleanest form of **U10**.
- **Failure mode and the trap it sits next to.** `CLAUDE.md` trap 2 forbids replacing the
  objective with explicit balance minimisation. An ε-constraint band is not that — the objective
  stays `P`, and the MNW point remains a *distinguished point on the frontier*. But if the
  frontier is ever reported without that point marked, trap 2 has been walked into by the back
  door. Mark it. Secondary risk: frontier cardinality — cap the ε-grid rather than enumerating
  exhaustively.

### 2.6 Homotopy in `τ` — the cheapest decisive experiment in either lens

- **Rests on:** **Chvatal1983** (objective-coefficient ranging: the optimal basis is constant on
  an interval), **Dantzig1963** / **Bixby2002** (dual simplex reoptimisation makes each step of
  the homotopy nearly free), **Danna2005** (RINS-style reuse of the previous incumbent).
- **Assumptions.** That `u_i(τ)` is affine in `τ` — true by construction (`u_i = M_z[λ + τ(...)]`).
  Ranging theory is exact for LP; for the MINLP the "piecewise constant in `τ`" claim is
  empirical, not a theorem.
- **Produces.** Groth OQ1's answer: whether `π*(τ)` is piecewise constant and whether `τ=0.42`
  lies in the cell containing `τ=0`. If yes, the two-stage scheme survives and needs only a local
  polish under `V` — and §2.1's full MINLP becomes optional rather than necessary.
- **Failure mode.** Sensitivity ranging on a *degenerate* LP (and a balance-tight transportation
  LP is degenerate) gives an interval of zero width and says nothing. Detect degeneracy before
  trusting the ranging; fall back to a coarse grid of τ with independent solves.

### 2.7 Matheuristic polish: local branching and LNS on the composite objective

- **Rests on:** **FischettiLodi2003** (local branching: a Hamming ball around the incumbent,
  explored exactly by the solver, no problem-specific neighbourhood needed), **Danna2005** (RINS),
  **Shaw1998** / **RopkePisinger2006** / **PisingerRopke2010** (destroy-and-repair with a MIP
  repair step), **LinKernighan1973** (variable-depth chains of zip swaps — the natural move for
  territory improvement), **Kirkpatrick1983** / **Glover1986** / **GloverLaguna1997** and the
  domain analogues **RiosMercadoFernandez2009**, **Bozkaya2003** (the districting heuristics of
  record, as baselines).
- **Assumptions.** A feasible incumbent exists — trivially, three do (the committed draw, the
  cells map, the hand-drawn baseline). **FischettiGloverLodi2005**'s feasibility pump is
  therefore *not* needed; note that explicitly so nobody builds it.
- **Produces.** Fast improvement of `V` from a premium-greedy start; the practical answer if
  §2.1 stalls. **Cannot say:** any bound. Pair it with §2.2/§2.3 or it produces an unfalsifiable
  number.
- **Failure mode.** The Groth yoga guesses the premium is won by *relabelling the roster*, not by
  redrawing the map. If that holds, zip-swap neighbourhoods are the wrong operator entirely and
  the right neighbourhood is a permutation move on `σ` — which §2.3's Hungarian already solves
  exactly. Run §5's `P₀` vs `P*(A)` before writing any neighbourhood.

### 2.8 Robustness of the balance claim to regional bias in `M` (U5 / A4)

- **Rests on:** **BertsimasSim2004** (budget-of-uncertainty `Γ`: the robust counterpart of a
  linear constraint stays linear and survives integrality — the only robust model that fits a
  MIP without conic machinery), **BenTalNemirovski1998** / **Lobo1998** / **BenTal2009** if an
  ellipsoidal set is ever credible, **CharnesCooper1959** if the sponsor prefers a probabilistic
  statement.
- **Assumptions.** A bound on the per-region deviation of `M`. **FRAME §5 supplies none** — A4 is
  unaudited and U5 is graded `[B]`. So the input does not exist yet.
- **Produces.** "The balance claim holds even if any `Γ` regions are mis-sized by up to `δ`" —
  the direct answer to the lens's observation that a regional bias in `M` is invisible to all
  five certificates.
- **Failure mode.** Without an elicited `δ`, `Γ` is a knob with no meaning and the robust model
  is decoration. **Do not build this before A4 is answered.**

### 2.9 Benders / logic-based Benders on the fiber–base split — named, and deferred

- **Rests on:** **Benders1962**, **Geoffrion1972** (convex subproblems), **HookerOttosson2003** and
  **CodatoFischetti2006** (combinatorial cuts from a 0-1 master, finite convergence by exhaustion).
- **Why it is deferred.** The split is real (master = roster + coarse allocation; subproblem =
  the concave fiber, whose duals are ready-made optimality cuts, which is precisely FINDINGS
  §9-F6). But at 1,229 units and `k=13` the monolithic §2.1 model is small enough that Benders is
  engineering ahead of evidence. Revisit only if §2.1 stalls after the §2.1 mitigations.
- **Failure mode if built early.** Two cut families in one loop do not share a convergence proof
  (**HookerOttosson2003** vs **DuranGrossmann1986**) — the exact error `RESEARCH_FINDINGS` already
  records the two-player harness making.

---

## 3. Solution concept and how it is verified

**An answer is:** a coverage `(π, σ)` — a partition of the 1,229 zips into 13 territories and an
injection of territories into the 111 wholesalers — together with

1. an **upper bound** `V̄ ≥ max V` over all coverages, from the sandwich
   `V(delivered) ≤ max_S EG_S ≤ EG_R` (§2.2 outer term) intersected with §2.1's branch-and-bound
   bound and §2.3's premium ladder;
2. the **gap** `V̄ − V(delivered)`, reported in two units: nats (internal) and displacement
   (§2.4 — mass of opportunity and share of book that would have to move), with the second
   flagged as *descriptive* until the modulus in §2.4 is established;
3. the **`i`-th terms** of `V` for each of the 13 selected wholesalers — i.e. FRAME §3.4's
   per-person continuity report, which is not a separate artifact;
4. a statement of **which relaxations were used** and therefore what the bound does and does not
   cover (it does not cover misreporting, and it does not cover error in `M`).

**Verification handed to `math-verify`:**
- the perspective identity `y log(g/y) = y log g` on `y ∈ {0,1}` and joint concavity of the
  perspective on `y > 0` (§2.1);
- that the fractional relaxation's value upper-bounds every integral coverage with the same
  roster (§2.2) — the lens marks this `[claim, immediate but unverified]`;
- that `P₀ ≤ P*(A) ≤ P₁₃ ≤ P_free` (§2.3), each inequality separately;
- that the four existing certificates are degenerations of §2.2's dual at `u_i ≡ λM` (Groth §3
  descent) — this is the "five collapse into one" claim and it is the load-bearing one;
- the `≤ k−1` split-zip descent, if §6 does not return a citation.

**Verification handed to `code-verify`:**
- `mip_rel_gap = 0.0` on every certification run (trap 12); a `time_limit` abort must not be
  reported as a bound (trap 15);
- the dual certificate is checkable in `O(nk)` without a solver, matching `cert_power_diagram`'s
  existing contract;
- rep-indexed and territory-indexed formulations agree on the committed draw's objective value;
- the scale-invariance test still passes (`Σ log g` shifts by `n log κ` and nothing else), and
  `tests/test_model.py::test_two_rep_reduction` still pins the two-player reduction.

---

## 4. Recommended path, with the decision points

**Stage 0 — measure before formulating (no solver, hours).** Run §5 in full. Both lenses converge
on this and it is the only step with no dependency on any open decision. Two of its outputs can
*cancel the rest of this plan*: if `P₀ ≈ P*(A)` and the contested-among-the-13 count is small,
the premium is not reachable by redrawing and the two-stage scheme was right all along.

**Stage 1 — the ladder and the candidate roster (§2.3).** Three exact solves, none over a minute.
Delivers FRAME §10.3's missing upper bound and prunes §2.1 from 111 reps to ~25–30.

**Stage 2 — the homotopy (§2.6).** The cheapest decisive experiment in either lens. Answer:
does the optimal coverage move between `τ=0` and `τ=0.42`?
> **D1 — the fork.** If `π*(τ)` is piecewise constant and `0.42` sits in the `τ=0` cell, stop at a
> local polish (§2.7 restricted to roster moves) and skip §2.1 entirely. If not, build §2.1.
> *This is a measurement, not a judgement call — it decides itself.*

**Stage 3 — the fixed-roster concave relaxation (§2.2).** One barrier solve per roster. Delivers
the certificate that subsumes the existing four, and the prices §2.4 needs.
> **D2 — blocking, and only here.** Both §2.1 and §2.2 read `u_i`, hence books, inside the
> drawing. FRAME §9 records this as *the* blocking user decision. **The optimisation methods are
> indifferent to which book they are handed** — reported, audited, or `G`-invariant normalised
> profiles (Groth §5b). So the decision does not block *formulation*, only *deployment*: build
> against reported book, deploy against whatever the user rules admissible. Recommend proceeding
> and recording the assumption, per the unattended rule.

**Stage 4 — the joint MINLP (§2.1)** with §2.3's candidate roster, single-tree architecture, and
in-out stabilisation held in reserve.
> **D3 — stop rule.** If the gap has not closed below the premium's own scale after the stated
> mitigations, fall back to §2.7 + §2.2 (heuristic incumbent, certified bound) and report the
> sandwich. Do **not** escalate to §2.9 (Benders) without evidence that the monolith is the
> bottleneck.

**Stage 5 — the frontier and the units (§2.5, §2.4).** The frontier gives the sponsor the
exchange rate; displacement gives the acceptance test in signable units. Mark the MNW point on the
frontier (trap 2).
> **D4 — acceptance unit.** Nats or displacement. Recommend displacement for anything a sponsor
> reads and nats internally, per both lenses — but note this is only *valid* if §2.4's modulus
> lands; otherwise displacement is descriptive and the certified statement stays in nats.

**Not on the path:** §2.8 (blocked on A4), §2.9 (deferred), all of FOUNDATIONS §8's contiguity
machinery (dormant while contiguity is dropped).

---

## 5. Numbers to compute first (cheap, decisive)

All from the existing export; none needs a new solver. Ordered by decisiveness per minute.

| # | number | method | why it is decisive |
|---|---|---|---|
| 1 | `P₀`, `P*(A)`, `P₁₃`, `P_free` | evaluation; **Kuhn1955** Hungarian; 111-binary MILP; evaluation | if `P₀ ≈ P*(A)` the matching is already right and the whole premium gap is in the *drawing*; if `P*(A) ≫ P₀` it is in the *matching* and is fixed in milliseconds |
| 2 | spread of realized gains `g_i` on the committed draw (U1) | one line next to `td/channel.py:322` | the headline 0.781% is a spread of `M`; the objective wants `g` equalised. If these differ, the published number measures the wrong thing |
| 3 | zips contested **among the selected 13**, and their share of `M` (U4) | count on `cand(z) ∩ S` | if small, D2 (the blocking book decision) is worth almost nothing and is settled by data instead of principle |
| 4 | `corr(S_i, M_z)` (U8) | correlation | decides whether §2.3's ladder bites or is loose; the lens's own escape clause |
| 5 | the hand-drawn state-grouped baseline's `(P, D(g), V)` (U10) | construct + evaluate | the headline claim "better than what we'd have done anyway" is currently unevidenced and, per Gromov M4, *plausibly false* |
| 6 | `V` of the cells map vs the dots map | stage-2 rescore, already ordered by `REVIEW_GROMOV` R2 | settles the 132-dots decision on the only criterion that is not second-order flat |
| 7 | `EG_R` — the concave relaxation over all 111 reps | one barrier solve (**Mehrotra1992**) | the outer term of the sandwich; if it is not absurdly loose, §2.2 is worth building |
| 8 | displacement (zips and `M`-mass) between dots and cells | transportation solve (**Hitchcock1941**) | converts a 4.66e-5-nat non-decision into a first-order quantity |
| 9 | saturation excluding headroom-repaired zips (U9 / A8) | recount | 41.9% is load-bearing for every argument above it |

---

## 6. Search brief for `lit-search`

**What FOUNDATIONS does not cover that this problem needs.** FOUNDATIONS is strong on
MILP/MINLP machinery, flows, and districting-with-contiguity, and *silent* on: market-equilibrium
convex programs, Nash welfare as an optimisation object, submodular approximation guarantees,
power diagrams and semi-discrete transport, joint districting-plus-selection, and stability
metrics on solutions. Those six gaps are the brief.

**Questions, stated precisely.**

1. **Eisenberg–Gale / Fisher markets as a convex program.** What is the canonical statement of
   `max Σ_i log u_i(X_i)` over a fractional allocation with equal budgets, its dual (prices), and
   its algorithms (interior point, proportional response, combinatorial)? Bears on **§2.2** and on
   whether "certificate 5" is a citation or a construction.
2. **Nash social welfare, integral case.** Complexity and approximation of *integral* MNW with
   additive valuations; MILP/MINLP formulations; lexicographic MNW and the empty-bundle
   convention (FRAME §9 records this as "answerable from the literature"). Bears on **§2.1** and
   on the tie-breaking open item.
3. **Cardinality-constrained EG / selection.** Is `max_{|S|=k} EG_S` a studied object — market
   design with agent selection, or facility location with a convex utility? Is there a Lagrangian
   or a bound better than "relax the base"? Bears on **§2.1**'s indicator layer and **§2.3**.
4. **Max-`k`-coverage certificates.** The `(1−1/e)` greedy guarantee and its LP/greedy duality
   certificate, plus the exact-MILP tightness of the natural coverage formulation. Bears on
   **§2.3** — specifically on whether my simplification (exact MILP over greedy+submodular
   certificate) is right at `n=1,229, |R|=111`.
5. **Power diagrams, constrained least-squares assignment, and balanced clustering.** The
   equivalence "capacity-constrained assignment ⇔ power diagram with the transport duals as
   weights"; the `≤ k−1` split-unit bound for balanced fractional clustering; anisotropic /
   generalized power diagrams. Bears on **§2.2** (does the `O(nk)` solver-free certificate survive
   at `τ > 0`, or is it a `τ=0` privilege?) and on the §3 verification list.
6. **Sales territory alignment and joint districting + salesforce selection.** The commercial
   (not political) districting literature: multiple balancing attributes, workload/potential
   balance, and any formulation that *chooses the reps* as well as the districts. Bears on
   **§2.1** — is the rep-indexed formulation already published?
7. **Stability, displacement and inverse optimization.** Is there a result of the form
   "objective gap ≥ φ(mass that must move)" for assignment or partitioning problems — stability
   radius, inverse optimization, or sensitivity of the optimal partition? Bears on **§2.4**, the
   one unproved step in this plan, and on FRAME §3.5's acceptance test.
8. **Symmetry in districting MIPs.** Orbital branching / symmetry breaking for anonymous
   districts, and whether center- or rep-indexing is the accepted remedy. Bears on **§2.1**'s
   claim that rep-indexing dissolves the `S_k` symmetry.
9. **Hierarchical decomposition fidelity.** When is a first-stage surrogate objective a valid
   relaxation of a two-stage problem's true objective, and what moduli exist? Bears on
   **§2.6** and on FRAME §10.1 — Groth §3 says nobody has checked this step.

**Literatures to sweep.** *Venues:* Mathematical Programming, Math. Programming Computation,
Operations Research, INFORMS J. on Computing, EJOR, SIAM J. Optimization, Discrete Optimization,
Management Science, Geographical Analysis, ACM EC / SAGT / Games and Economic Behavior (for 1–4),
Discrete & Computational Geometry and SIAM J. Imaging Sciences (for 5).
*Keywords:* Eisenberg–Gale; Fisher market; competitive equilibrium from equal incomes;
Nash social welfare approximation; proportional fairness allocation; max-k-coverage; monotone
submodular maximization; capacity-constrained power diagram; semi-discrete optimal transport;
balanced clustering with cardinality constraints; sales territory alignment; commercial
districting; salesforce sizing and deployment; stability radius combinatorial optimization;
inverse optimization; orbital branching; two-stage vs monolithic formulation fidelity.
*Canonical anchors already in FOUNDATIONS to walk citations from:* **GunlukLinderoth2010**,
**FrangioniGentile2006**, **Boland2015**, **RiosMercadoFernandez2009**, **Bozkaya2003**,
**ValidiBuchanan2022**, **Hitchcock1941**, **Kuhn1955**, **NemhauserWolsey1988**,
**BoydVandenberghe2004**, **NesterovNemirovskii1994**, **BertsimasSim2004**.

**Deliverable.** Entries as `citation · venue/year · DOI · 2–4 sentence annotation naming which
§2 method or §4 decision point it bears on · tag ∈ {foundation, frontier,
contradicts-or-sharpens, tool-we-lack}`. Plus a **five-paper shortlist** — the five that would
change what gets built. Every absence claim must state where it looked (venue, keyword, years),
because the programme's own recon (`RESEARCH_FINDINGS` §0.5) already went stale once. Write
`docs/LIT_optimization.md` and append to `docs/RESEARCH_ADDITIONS.bib`.

---

## 7. Out of this domain — hand to

| item | to | why |
|---|---|---|
| The audited-vs-reported book split; whether a drawing rule reading only `G`-invariants is strategyproof; what `fotakis2014`'s impossibility forbids once the input is not a report (Groth §5b, Gromov M13.1, FRAME §10.5) | **mechanism design / economic-theory** | Every §2 method is indifferent to which `S` it is handed. The choice of admissible statistic is not an optimisation question. **This is the paper-shaped question in the file.** |
| The fiberwise reading of the equal-split theorem; MNW with heterogeneous-but-proportional valuations; lexicographic MNW, EF1, empty bundles (Gromov OQ2, FRAME §9) | **economic-theory / fair division** | Axiomatics, not algorithms — though §6 Q2 overlaps and `lit-search` should not duplicate. |
| **U6** — the data-noise floor at `n=1,229, k=13`, and whether the tier-2 tolerance is measuring the right noise (FRAME §10.4) | **econometrics / data-science** | A bootstrap under a contestability noise model. Optimisation supplies only the observation that the two tolerances (`mip_rel_gap`, acceptance floor) are different objects and only the first is ours. |
| **U5 / A4** — regional bias in the sizing estimate `M` | **data-science**, then back here | §2.8 needs a `δ` before it is anything but decoration. |
| **U12** — eliciting the balance↔continuity exchange rate | **the sponsor** (via the user) | §2.5 draws the frontier; only leadership picks the point. |
| Contiguity on the full ZCTA graph; "the glue is the worthless part" (FRAME §10.6, §9-H) | **applied-math / geometry**, currently out of scope (FRAME §7) | If reopened, FOUNDATIONS §8 (**ValidiBuchanan2022**, **Buchanan2018**, **Rehfeldt2019**, **Miyazawa2021**) is already seeded for it. |

---

## 8. Open questions (inputs to `/research-plan`)

1. **Does the homotopy answer the whole thing?** If §2.6 shows `π*(τ)` constant from `0` to
   `0.42`, methods §2.1, §2.5 and §2.9 are unnecessary and the programme's remaining work is a
   rename pass plus a roster polish. This should be the first unit cut, and it should be allowed
   to cancel the others.
2. **Is the rep-indexed perspective formulation new, or published?** §6 Q6 decides whether §2.1 is
   a citation-plus-implementation or a contribution. It changes the shape of the note, not the
   code.
3. **Does §2.4's modulus exist?** Everything about acceptance in business units (FRAME §3.5,
   §10.7, both lenses' units complaint) rests on a bound of the form
   `objective-gap ≥ φ(mass moved)`. Either §6 Q7 returns it, or a `math-verify` unit must attempt
   it, or acceptance stays in nats. **This is the single highest-leverage unknown in the plan.**
4. **Do the four existing certificates actually collapse into §2.2's dual?** Stated in §3 as the
   load-bearing verification claim. If they do, the note shortens by pages; if they do not, the
   Groth lens's central reframing is weaker than it reads.
5. **Is `EG_R` (all 111 reps) loose or useful?** One barrier solve settles it (§5 #7). If it is
   useless, the sandwich has no outer term and §2.3's ladder carries the whole bound.
6. **Roster moves or zip moves?** Groth's yoga guesses the premium is won by relabelling, not
   redrawing. §5 #1 answers it, and the answer determines whether §2.7 is written at all — and,
   more sharply, whether stage 1 ever needed to see books.
7. **Does D2 actually block anything?** My reading is no: the methods are indifferent to which
   `S` they read, so the decision blocks deployment rather than formulation. If `/research-plan`
   disagrees, every unit downstream of §2.1 stalls on a user answer — worth resolving explicitly
   rather than by default.
8. **Scope check on §2.8.** Robustness to `M`-bias is the only method here with no input. Should
   it be cut from the plan entirely rather than carried as blocked?
