# Grothendieck lens — the national channel territory problem

**Date:** 2026-09-02 · **Framework:** 0.1-dev · **Reads:** `docs/FRAME.md` (§3, §6, §10),
`docs/MODEL.md`, `docs/REVIEW_GROMOV.md`, `docs/RESEARCH_FINDINGS.md` (§1C–E, §6C, §9-G/H),
`td/solvers/base.py:72,81` · **Provenance:** uncited draft of the method; see
`~/.claude/commands/grothendieck.md`. **Nothing here is a quotation of Grothendieck and
nothing is attributed to him.**

Claims below are tagged `[measured]` (a number computed against the export, sourced),
`[standard]` (a textbook/literature result, cited by name in FINDINGS, not re-derived here),
or `[claim]` (this lens's assertion, unverified — for `/math-verify` or a unit brief).

---

## Moves that fired

### 3. Name the nut

Everything open in `FRAME.md` §10 keeps returning to one kernel. Stripped of the problem:

> **The map is chosen by a functional of the map alone; its value is a functional of the pair
> (map, roster). No relation between the two has ever been asserted.**

Write it. A *coverage* is a pair `(π, σ)`: `π = (A_1,…,A_k)` an ordered partition of the
footprint `Z`, `σ` an injection from territories into wholesalers `R`. The value the business
signs is

```
V(π, σ) = Σ_j log u_{σ(j)}(A_j),        u_i(A) = Σ_{z∈A} u_i(z)
```

Stage 1 maximises `W(π) = Σ_j log M(A_j)`, a function of `π` only. Stage 2 maximises
`V(π, ·)` at that fixed `π`. `W` is **not** an upper bound on `max_σ V(π,σ)`, not a lower
bound, and not a projection with a known modulus — it is a different function on a different
space. At 5% saturation the difference is a rounding error; at the measured 41.9% it is
~3.7 nats against a 4.5e-5-nat balance residual `[measured, REVIEW_GROMOV R1]`.

**What it is an instance of.** A two-stage scheme in which the first stage optimises a
*degeneration* of the true objective and the second stage optimises inside a fibre. Such a
scheme is sound exactly when the degeneration is a relaxation (bound) or a limit with a
modulus. Neither has been checked here, and FRAME §10.1–§10.3 are three faces of the same
unchecked step. So: **the sea rises around the pair `(π,σ)`, not around the partition.**

The nut also explains why FRAME §3.4 (the per-wholesaler continuity report, "never produced")
reads as a reporting gap. It is not. Continuity *is* the `i`-th term of `V`. The report and
the objective are the same object seen twice, and the report is missing because the objective
was never written down in the form that has an `i`-th term.

### 2. Let the sea rise — from partition to market

Widen in three steps and watch what dissolves.

| step | setting | what dissolves | what it costs |
|---|---|---|---|
| 0 | integral partition, common measure `M` | (the current programme) | — |
| 1 | fractional assignment `X ∈ [0,1]^{Z×R}`, `Σ_i x_{zi} = 1`, common measure | integrality; the objective becomes concave and the analytic ceiling becomes an LP fact rather than an AM–GM identity | nothing — `Σ log` of a linear map is concave `[standard]`; the descent back is ≤ k−1 split zips `[standard, brieden2017 Lem. 4]` |
| 2 | fractional, **per-agent measures** `u_i` | *the difficulty of the nut vanishes*: `V` is concave in `X` with no `M`-vs-`u_i` split at all. There is one objective, one optimum, one duality gap | the drawing now reads books — FRAME §9's blocking decision |
| 3 | + convex geometric penalty `ρ·C(X)` | compactness re-enters without leaving concavity | one parameter, already in the model |

Step 2 is the dissolution, and the object it lands on is not new. With agents `R`, goods `Z`
endowed with mass `M`, equal budgets, and additive valuations `u_i`, `max_X Σ_i log u_i(X_i)`
is the **Eisenberg–Gale program** of a Fisher market — i.e. competitive equilibrium from equal
incomes `[standard, FINDINGS §1B/§5A]`. In that reading:

- **Balance is not a theorem, it is the equal-budget condition.** "~$1B each" stops being a
  consequence of a common measure (which the instance does not have) and becomes the market's
  own defining constraint. This is the exact replacement FRAME §10.2 asks for: not a weighted
  version of equal-size districting, but a different characterisation that reduces to it.
- **The incumbency premium is priced.** The dual gives per-zip prices `p_z` and per-agent
  bang-per-buck; the premium is not a residual term needing its own bound, it is a component of
  one gap. FRAME §10.3 asks why no upper bound on the premium ever appeared: **because balance
  was proved by AM–GM, an inequality that exists only on a common measure.** No sharpening of
  that argument reaches the heterogeneous case; only changing the object does. `REVIEW_GROMOV`
  R3 (= FINDINGS C3) proposes exactly this solve as "certificate 5" — the lens's contribution
  is that it is not a fifth certificate, it is *the* certificate, of which the existing four are
  degenerations.
- **The current answer is the `τ = 0` fibre.** Write `u_i(z) = M_z·[λ + (c1−c2)s_{i,z} + c2 t_z]`
  and let `τ` scale the book terms. At `τ = 0` all `u_i` collapse to `λM`, every equal-mass
  partition is optimal, the optimum is `k·log(M(Z)/k)` — the analytic balance ceiling — and
  adding `ρ·C` selects the power diagram of the centers with the transport duals as weights
  `[standard, aha1998/brieden2017; built at 937460e]`. The real instance sits at `τ ≈ 0.42`.

**Cap check.** A fourth widening (drop the partition constraint to a measure-valued
assignment / semi-discrete OT `[FINDINGS §6C]`) buys solver machinery, not dissolution. Stop
at step 3.

### 4. Relativise — work over the roster

The parameter being re-derived per value is the roster. Stage 2 is run once per draw; the
portfolio (`score_draws`) re-runs it per seed; `REVIEW_GROMOV` R2 requires yet another rescore
for the cells map. Replace the object with a family.

Base `B` = staff sets `S ⊂ R`, `|S| = k`. Fibre `EG_S` = the step-2 program restricted to `S`.
Then `V*(S) = max EG_S` is a function on the base, and:

- **Fibrewise bound.** `EG_S ≥ max{V(π,σ) : im σ = S}` for every integral `(π,σ)` — a
  relaxation, so a genuine upper bound `[claim, immediate but unverified]`. This is the bound
  R3 computes, conditioned on the winner's 13.
- **Stable under base change.** Equal budgets holds in *every* fibre: balance is a
  base-independent property. So is scale-invariance (already proved), and so is the ≤ k−1
  fractional-split count. **The content lives in what is not stable:** the geometry (the
  optimal centers move with `S`), and hence compactness, and hence the cells-vs-dots question.
  Stage 1 fixes geometry before the base point is chosen — that is precisely the "known cost of
  the split" in `CLAUDE.md`, now with a name.
- **Relaxing the base gives a computable global bound.** `max_{S} EG_S ≤ EG_R` with a
  cardinality constraint on positive-utility agents; the unconstrained `EG_R` over all 111
  reps is a valid but weak outer bound `[claim]`. `C(111,13)` fibres are not enumerable, so the
  useful statement is the sandwich: `V(delivered) ≤ max_S EG_S ≤ EG_R`. Whether the outer term
  is loose enough to be useless is one concave solve away.

### 5. Ask for the morphisms first

Two "sameness" questions are open, and both are asked on the wrong object.

**(a) When are two maps the same?** The programme's answer is "within tier-2, 5e-3 nats"
(`base.py:81`). Apply it: the cells-vs-dots gap is 4.66e-5 nats `[measured]`, so the answer is
"indistinguishable", and the main open decision is undecidable by the programme's own rule
(FRAME §10.4). The lens's reading: the tolerance is not mis-measured, it is **applied to a
functional that is second-order flat at its optimum**. `Δ ≈ ½Σδ_j²` `[REVIEW_GROMOV R2]`:
4.51e-5 nats ⇔ 0.26% RMS deviation of territory mass. A quadratically flat functional turns any
tolerance into a first-order-wide indifference ball, *by construction*, no matter how the
noise floor is measured. The morphism-first fix is to define sameness on a first-order object:
**displacement** — the mass of opportunity (or of book) that must move to carry one map to the
other, i.e. a transport distance between partitions. Tolerances in that metric are in dollars
and are not self-defeating. This is also the answer to FRAME §10.7: the invariant unit is
displaced mass; nats are a chart on the objective, not a metric on the decision.

**(b) When are two instances the same?** Known invariances: global rescale of `M` (proved),
relabelling of territories (`S_k`; a solver hazard — and note stage 1's objective is
`S_k`-invariant while `V` is not, which is exactly why the split loses value). The unnoticed
one is the action that matters for governance. Let `G = (ℝ_{>0})^R` act by rep-uniform
inflation of reported books, `S_{i,·} ↦ γ_i·S_{i,·}` — the natural model of the incentive the
98 unselected reps have. Its invariants include `M_z`, the candidate sets `cand(z)`, and each
rep's **normalised geographic profile** `S_{i,z}/S_i(Z)`. Hence:

> **A drawing rule that reads reported books only through normalised per-rep profiles is
> invariant under uniform inflation, by construction.** `[claim]`

That is a direct, checkable answer to FRAME §10.5 that needs no mechanism-design theorem: it
does not choose between "books in stage 1" and "books nowhere", it identifies the *invariant
subalgebra* the drawing may read. It does not cover selective (per-zip) inflation, and it
discards book magnitude — which stage 2 legitimately needs, and which audited system-of-record
revenue supplies from outside the action `[FINDINGS §9-G]`. Stating the group is the
deliverable; the escape was already half-guessed, and this says which half is forced.

## Moves that did not fire, and why

- **1 (state structurally).** Already done, before this lens. `MODEL.md` states the problem
  N-way with no instance particulars, and the objective is scale-invariant, so `k=13`,
  1,229 zips and $13B are calibration, not statement. What is missing is not vocabulary about
  structure but the *composite* objective — Move 3's job, not Move 1's.
- **7 (refuse the trick).** No live trick. The one candidate — the transportation duals as a
  "free" certificate — is already the concept, not a coincidence: constrained least-squares
  assignment ≡ power-diagram partition is a published equivalence `[aha1998]`. The trick was
  refused at `937460e`. (`place_by_state` for the 6 coordinate-less zips is plumbing at 0.14%
  scale, not a difficulty.)
- **8 (build the tool before the theorem).** The machinery exists and is cited: EG/Fisher
  solvers, semi-discrete OT with proved convergence, damped Newton `[FINDINGS §6C]`. Building
  it here would be re-deriving. The action is a citation pass plus one solve, not a tool.
- **6 (find the functor)** fires but has no independent content: the repeated construction is
  "solve the convex relaxation, read the duals" (power weights, EG prices, transport
  potentials), and identifying them as one construction at three values of `τ` is Move 2's
  output already.
- **9 (write the yoga)** runs throughout; its output is the last section.

## Concepts introduced (the deliverable)

| concept | one-line definition | what it makes trivial | what it costs |
|---|---|---|---|
| **Coverage / composite value `V(π,σ)`** | the value of a (map, roster) pair, `Σ_j log u_{σ(j)}(A_j)` | "is two-stage right?" becomes "is `W` a relaxation of `V`?"; the per-rep continuity report becomes the `i`-th term of the objective | nothing — it is what the business signs |
| **The `τ`-deformation** | one-parameter family of instances from common measure (`τ=0`) to measured saturation (`τ≈0.42`) | sorting results into `τ=0`-exact (equal-size districting, the analytic ceiling, the power diagram) vs. continuous-in-`τ` | the modulus in `τ` is not known and must be computed |
| **Equal-budget market (EG) formulation** | the fibre relaxation is a Fisher-market equilibrium: goods = zips endowed with `M`, agents = staff, equal budgets, valuations `u_i` | balance without a common measure; the premium bound; the unification of four certificates into one duality gap | the draw reads books (the blocking decision); integrality becomes ≤ k−1 split zips |
| **Relativisation over the roster** | the family `{EG_S}` over staff sets, with stage 2 as maximisation over the base | why stage 1 cannot see what stage 2 needs (fibres are not isomorphic in geometry); a computable outer bound by relaxing the base | `C(111,13)` fibres; only the relaxed bound is computable |
| **Displacement metric** | distance between maps = mass that must move (transport distance), not objective difference | acceptance §3.5 in dollars; and the diagnosis that a nat-tolerance on a second-order-flat functional is self-defeating | a new certificate shape; existing gaps must be converted |
| **The inflation group `G = (ℝ_{>0})^R` and its invariants** | rep-uniform book scaling; invariants = `M_z`, `cand(z)`, normalised per-rep profiles | inflation-proofing the draw by construction rather than by theorem | covers uniform, not selective, inflation; discards book magnitude |
| **The two supports** | `M` lives on all ZCTAs; `S` lives on the 1,229 sold zips; the objective is on `M` | the "547 components" count is a count on the support the objective does *not* live on | reopening the full-ZCTA experiment, currently out of scope (FRAME §7) |

## The general case, stated

Let `Z` be finite, `M` a measure on `Z`, `R` a finite agent set, `k ≤ |R|`, and `(u_i)_{i∈R}`
a family of measures on `Z` absolutely continuous w.r.t. `M` with densities bounded by the
headroom condition. A **coverage** is a pair `(π,σ)` with `π` an ordered `k`-partition of `Z`
and `σ : [k] ↪ R`. Fix a convex geometric penalty `C` and `ρ ≥ 0`.

**Problem.** `max_{(π,σ)} Σ_j log u_{σ(j)}(A_j) − ρ·C(π)`.

**Fibre.** For a staff set `S`, the relaxation over fractional assignments `X` supported on `S`
is concave; it is the Eisenberg–Gale program of the Fisher market `(S, Z, M, budgets ≡ 1, u)`
penalised by `ρ·C`. Its value upper-bounds every integral coverage with `im σ = S` `[claim]`;
its duals are prices on `Z`; at a basic optimum at most `|S| − 1` units are split `[standard]`.

**Degeneration.** At `u_i ≡ λM` for all `i` the fibres become isomorphic and staff-independent;
the optimum is `k·log(λM(Z)/k)` — the analytic balance ceiling — every equal-mass partition
attains it, and the `ρ`-term selects a power diagram of the centers with the duals as weights.
**The programme as built is this degeneration.** Two-stage design is the assertion that the
degeneration is a good approximation; the measured saturation says it is off by ~4 orders of
magnitude in the term it drops.

*Dissolution check:* step 2 made the `W`-vs-`V` mismatch vanish rather than move — there is one
objective afterwards. *Descent check:* every statement above has an instance reading, below.

## Descent: what this says about the instance in `docs/FRAME.md`

1. **§10.1 (is two-stage the right decomposition?)** It is the right decomposition of the
   `τ=0` degeneration. Keep it as the business constraint FRAME §9 already records it as, but
   grade every candidate map by `V`, never by `W`. Concretely: the cells-vs-dots decision is
   settled by the stage-2 rescore R2 already ordered, and nothing else.
2. **§10.2 (what survives of equal-size districting?)** It survives *exactly* as the `τ=0`
   term and *exactly* as a statement about `M`-mass — which is what leadership asked for, so
   the delivered balance claim stands unchanged. Its heterogeneous replacement is not a
   weighted equal-size theorem; it is the equal-budget equilibrium.
3. **§10.3 (why is there no premium bound?)** Because AM–GM/Schur-concavity `[marshall2011]`
   needs a common measure. The bound exists in the other object: one concave solve. Promote
   R3 from "certificate 5" to "the certificate", with the existing four as its degenerations.
4. **§10.4 (is the tolerance calibrated?)** The floor is not measuring the wrong noise — it is
   attached to a second-order-flat functional, so *any* nat-tolerance makes near-optimal maps
   indistinguishable. Restate acceptance in displacement (mass moved), where it is first-order.
5. **§10.5 (a non-gameable formulation?)** Yes, in the stated sense: read reported books only
   through `G`-invariants (normalised profiles), take magnitudes from audited revenue. This is
   a design rule that can be written into `MODEL.md` today, and it converts the blocking
   decision from "books: yes or no" into "which invariants".
6. **§10.6 (is "the glue is worthless" structural?)** Malformed as posed. 547 is a component
   count on the support of `S`; the objective is a functional of `M`, whose support is all
   ZCTAs. The glue is worthless *for the book measure* and load-bearing *for the opportunity
   measure*. Not a recommendation to reopen contiguity (FRAME §7 rules it out) — a
   recommendation to stop quoting 547 as a property of the problem.
7. **§10.7 (units)** Displacement. §3.5's "no achievable map beats this by more than $Y of
   misplaced book" is literally a displacement statement; the concept says derive it from the
   dual prices rather than by translating nats.
8. **§3.4 (per-wholesaler continuity)** Not a separate report. Emit the `i`-th terms of `V`
   for the delivered coverage; the "share of book inside the assigned territory" is that term
   with `λ = 0`.
9. **Baseline (§3)** The hand-drawn state-grouped alignment is a coverage; score it with `V`
   and quote the difference in displacement. Cheap, and it makes the headline claim evidenced.

## Open questions this lens raises (inputs to `/domain` and `/research-plan`)

1. **Modulus of the `τ`-deformation.** How does the optimal coverage move as `τ: 0 → 0.42`?
   Is `τ ↦ π*(τ)` piecewise constant (equilibrium homotopy), and is the real instance inside
   the cell containing `τ=0`? *If yes, the two-stage scheme is nearly right and needs only a
   local polish under `V` — the single cheapest experiment on this list.*
2. **Does EG + convex geometric penalty retain a diagram structure?** Are its cells generalized
   /anisotropic power diagrams `[alpers2015]`, i.e. is the solver-free `O(nk)` certificate
   available at `τ > 0` too, or is it a `τ=0` privilege?
3. **Selection is not convex.** EG with a cardinality constraint on positive-utility agents
   (13 of 111) — Lagrangian, greedy, or bound? Touches the open incentive-ratio-2 statement for
   the rectangular-with-selection rule `[FINDINGS §9-G]`.
4. **Invariant theory of the inflation action.** Full invariant subalgebra of `G`; and what
   fraction of the premium a `G`-invariant drawing rule can retain. A lower bound here is the
   difference between "safe and worthless" and "safe and worth doing".
5. **Displacement as a certificate.** Can a lower bound on displacement-to-any-better-coverage
   be read from the EG duals, giving §3.5 in dollars without passing through the log?
6. **Are the fibres far apart?** Measure `spread_S EG_S` on a handful of staff sets. If small,
   relativisation is bookkeeping; if large, stage 1's geometry-before-roster ordering is the
   dominant loss and the roadmap changes.
7. **The two supports.** One rebuild of the TIGER ZCTA adjacency (`data/README.md`) answers
   whether the `M`-support is connected per region — settling §10.6 as fact rather than framing.

## Yoga (heuristic, unproved)

- **Everything hard here is a difference between two measures on the same set.** `M` vs `u_i`;
  the sold support vs the full support; nats vs mass. When a statement is confusing, ask which
  measure it lives on. Most of the open list is one of these three, wearing a different hat.
- **Five certificates is a symptom.** A programme that needs five separate optimality
  certificates has not written its objective down once. Expect them to collapse into one
  duality gap, and expect the collapse to be more valuable than any of them individually.
- **Whenever a bound is wanted, solve the convex relaxation and read the duals.** This has now
  worked three times (balance ceiling, power weights, EG). Expect it to be the answer before
  looking for a combinatorial argument.
- **The business's units are the invariant ones.** Dollars of opportunity, share of book
  retained, zips moved — these survive every reformulation. Nats do not; they are a chart.
  Prefer a clumsy statement in invariant units to an elegant one in nats.
- **Never ask one number to serve both balance and continuity.** The `τ=0` theory is exactly
  right for the first and structurally silent on the second. A tolerance, a certificate or a
  spread that claims to cover both is measuring only the first.
- **Guess, testable and cheap:** at `τ ≈ 0.42` the `V`-optimal coverage differs from the
  `W`-optimal one in *few zips but much premium* — the premium is won by relabelling the
  roster, not by redrawing the map. If that holds, the whole 3.7-nat exposure is recovered by
  a local polish and the two-stage scheme survives intact. If it fails, stage 1 must be rebuilt
  as the market. Open question 1 is exactly this test, and it should run first.
