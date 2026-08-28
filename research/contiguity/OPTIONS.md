# Contiguity enforcement — options brief

**Date:** 2026-08-28. **Status:** research synthesis, no code. Companion: `TEST_PLAN.md`
(how each option is run against the battery), `raw/*.md` (the five literature legs, every
DOI Crossref-verified unless marked UNVERIFIED), `literature/territory_bibliography.*`
(entries appended in the same pass).

**Question answered here:** given the paper's program — maximise `log g_a + log g_b` over
`x ∈ {0,1}^n` with both `G[S]` and `G[Z∖S]` connected, optional `ρ·perimeter` — what are the
credible ways to enforce connectivity at 400–800 ZCTAs per pair, sparse active zips, open-source
solvers only, keeping a measurable optimality guarantee?

---

## 0. What the literature says about the current method, in four sentences

1. **The architecture is right, the engine is wrong.** Lazily separated connectivity cuts inside
   branch-and-cut are the state of the art (Validi, Buchanan & Lykhovyd 2022: proven-optimal
   contiguous plans at ~1,500 units and 21 US states at tract level). What `districting.py` lacks is
   the *single tree*: every round re-solves `scipy.optimize.milp` from scratch, and HiGHS has **no
   cut-injection callback at all** (`raw/solvers.md`), so this cannot be fixed on the current stack.
2. **The two cut families have different convergence theories and their worst-case iteration
   bound multiplies.** OA tangents (Duran–Grossmann 1986) and connectivity cuts (logic-based /
   combinatorial Benders — Hooker & Ottosson 2003, Codato & Fischetti 2006) compose, but the
   combined bound is the product of each family's, which is why iteration limits appear.
3. **The ρ=0 thrash is textbook Kelley instability**, not a contiguity phenomenon: on a flat
   objective, plain cutting planes zigzag (Lemaréchal–Nemirovskii–Nesterov 1995). In-out
   stabilisation (Ben-Ameur & Neto 2007; Fischetti & Salvagnin 2010) is the standard cheap fix.
4. **Encoding choice alone will not clear the scale wall.** Duque, Church & Middleton 2011 show
   even Shirabe's one-shot flow model failing to certify at n=25–49 on CPLEX without root-fixing
   and warm starts. Solver architecture (single tree, warm start, variable fixing) matters at
   least as much as the constraint family.

Two theory results from the fair-division leg bear on the paper rather than the solver:
a connected **EF1 allocation for two agents exists on any graph whose block-tree is a path**
(Bilò et al. 2022, Thm 3.10 — every biconnected ZCTA blob qualifies) and is computable in O(m)
by discrete cut-and-choose; and connected fair division is **NP-hard even for two agents with
identical valuations** (Deligkas et al. 2021, Prop. 3), so no polynomial exact method is waiting
to be found. No price-of-connectivity bound exists for Nash welfare specifically (only MMS: 4/3 on
biconnected graphs, 1/k at a k-way cut vertex — Bei et al. 2022). See §9.

---

## 1. How the options are scored

Each option is rated on the three battery mechanisms from `CLAUDE.md` Trap 11 —
**(a)** pre-existing disconnection, **(b)** pure scale, **(c)** value concentration — plus the
regime real data adds, **(d)** sparse active zips with zero-value glue. Ratings: ● direct fix,
◐ indirect / partial, ○ no effect, ✗ likely worse.

**Optimality-gap measurement** (the user-requested key factor; defined precisely in
`TEST_PLAN.md` §3): every option reports `gap = (UB − LB)/|UB|` on the true objective
`log g_a + log g_b − ρ·perimeter`, where UB is the tightest valid relaxation bound the method can
produce and LB the incumbent's true value. Exact methods must reach `gap ≤ 1e-8`; ε-methods
report their a-priori ε and the realised gap; heuristics have no UB of their own and are scored
against the best UB any method produced on the same instance, plus brute-force ground truth on
small instances.

---

## 2. Option A — Single-tree branch-and-cut on SCIP (PySCIPOpt)

**Idea.** Keep the paper's formulation; move it into one branch-and-bound tree where both cut
families are lazy constraints. A `Conshdlr` subclass implements `conscheck`/`consenfolp`: when an
integer-feasible node is found, (i) test each side for connectivity, add one **aggregated
minimal-separator cut per violating component** (Validi et al.'s min-cut separation, stronger than
the current `N(S)` neighbourhood cut), and (ii) add the OA tangent at the incumbent's `(g_a, g_b)`
(Quesada & Grossmann 1992 LP/NLP-based B&B). Alternative A′: hand SCIP the `log` terms natively
(`exp`/`log` expression constraints) and let its convexity detection carry the certificate, leaving
connectivity as the only custom handler.

**Literature.** Quesada & Grossmann 1992; Bonami et al. 2008 (single-tree beats multi-tree OA
consistently as n grows); Validi, Buchanan & Lykhovyd 2022 (same subproblem at 1,500 units via
lazy min-cut separation in one tree); Kronqvist et al. 2019 review.

**Guarantee.** Global optimality certificate (finite by Duran–Grossmann for tangents,
Codato–Fischetti for combinatorial cuts). Gap reported natively by SCIP.

**Mechanisms.** (a) ◐ — a disconnected incumbent is cut once and the tree continues; no restart.
(b) ● — the direct remedy for re-solve-from-scratch. (c) ◐ — more budget per instance; no
structural fix. (d) ◐ — SCIP's presolve handles some glue; combine with Option E.

**Cost / risk.** New dependency: `pip install pyscipopt` (SCIP bundled in the wheel since 5.0,
macOS arm64 wheels exist, Apache-2.0 since SCIP 8.0.3). ~2 days to port `solve_contiguous_nash`
and validate against the existing solver on C1. Risks: SCIP's B&B is single-threaded (parallelism
comes from running pairs in parallel, which we do anyway); `trySol` warm-start had historical
bugs — smoke-test on the pinned version; the native-log path (A′) needs SCIP's nonlinear handler
verified to give a global certificate (`raw/solvers.md` flags this medium-confidence).

**Verdict.** Primary candidate. The only open-source stack with both single-tree lazy cuts and a
native convex-MINLP certificate.

---

## 3. Option B — Lazy constraints on CBC via python-mip

**Idea.** Same as A, on CBC: `model.lazy_constrs_generator = ConnectivityGen()` is called at
integer-feasible incumbents and may add both connectivity cuts and OA tangents (tangent cuts are
globally valid, so adding them lazily is sound); `model.start` gives a MIP start.

**Literature.** As A. python-mip docs (`raw/solvers.md`).

**Guarantee.** Same as A (certificate; gap from CBC's bound).

**Mechanisms.** (a) ◐ (b) ● (c) ◐ (d) ◐ — identical profile to A, weaker engine.

**Cost / risk.** `pip install mip` (CBC via `cbcbox`, native arm64 since 1.17, Python 3.13 OK).
The closest drop-in to the current code (~1 day). Risk: CBC is the weakest of the three MILP
engines on Mittelmann-style benchmarks; treat B as the *fast-to-test* variant of A, and as a
second engine to cross-check A's numbers.

**Verdict.** Run alongside A in the screening stage; keep whichever engine wins.

---

## 4. Option C — Certified piecewise-linear log: one MILP, no OA loop

**Idea.** Replace the OA tangent loop with an a-priori piecewise-linear under-estimator of
`log g_a` and `log g_b` over their known ranges `(0, Σu_a]`, `(0, Σu_b]` (SOS2 or the Vielma–
Nemhauser logarithmic encoding: `O(log k)` binaries for `k` segments). The welfare nonlinearity is
then inside one MILP with a certified error `ε` chosen up front (e.g. `ε = 1e-6` relative in log —
the tangent-at-breakpoints over-estimator gives the matching UB, so the a-priori gap is exactly
bounded). Connectivity becomes the **only** lazy family — the "two convergence theories in one
loop" hazard disappears. Combines with A/B (single tree) or with D (no lazy family at all).

**Literature.** Caragiannis et al. 2019 §6 (MNW via PWL log, exact at integer utilities — our
utilities are continuous, so the ε-grid version applies); Vielma & Nemhauser 2011.

**Guarantee.** ε-certified: `gap ≤ ε` by construction, plus the solver's MIP gap. Not exact, but
the bound is explicit and tunable — and with `ρ > 0` the solve is already "exact for
Nash-minus-a-penalty", so an explicit ε on the welfare term is a comparable modelling statement.

**Mechanisms.** (a) ○ (b) ◐ — fewer outer rounds, one larger MILP. (c) ● — the mechanism that
inflates OA iteration counts (heavy tails widen the `g` range and flatten the log) becomes a grid-
size choice, not an iteration count. (d) ○.

**Cost / risk.** Medium: PWL encoding is fiddly to get right by hand (Pyomo's `Piecewise` with
`LOG` representation exists, but we would prefer not to add Pyomo). Segment count: with the
range spanning 3–4 orders of magnitude under heavy tails, a log-spaced grid of ~60–100 breakpoints
gives relative ε ≈ 1e-5; the logarithmic encoding keeps that to ~7 extra binaries per side.
Risk: weak LP relaxation of SOS2 encodings can slow B&B — must be measured.

**Verdict.** Strong secondary; the natural partner of D and the direct answer to mechanism (c).

---

## 5. Option D — Compact flow formulation (Shirabe), one shot

**Idea.** Enforce connectivity with the single-commodity flow system already written in the paper
(§Layer 6(a)): fixed roots `r_a`, `r_b`; `O(|E|)` continuous flow variables per side; every
assigned zip absorbs one unit shipped from its root through in-district arcs. With fixed roots
and a planar Rook graph, this is ~`2·2·|E| ≈ 12n` continuous variables and `~4n` constraints. No
connectivity cut loop. Combined with Option C it is **a single MILP solve with no loop at all**,
runnable on today's `scipy`/HiGHS (which now has a parallel MIP) with zero new dependencies.

**Literature.** Shirabe 2005, 2009; Duque, Church & Middleton 2011 (FlowPRM best of three
one-shot models but fails to certify at n=25–49 without root-fixing); Validi et al. 2022 (CUT
dominates flow in LP strength; flow becomes the bottleneck "above a few hundred units").

**Guarantee.** Exact (with OA loop) or ε-certified (with C); gap from the MIP solver.

**Mechanisms.** (a) ● — there is no loop to diverge; a disconnected incumbent is infeasible by
construction. (b) ◐/✗ — the literature expects it to lose to cut-based B&C at the 800-unit end;
the crossover is exactly our target band, so it must be measured, not assumed. (c) ◐ — with C.
(d) ✗ — flow variables on zero-value glue zips are pure overhead; big-M coefficients `(n−1)` on
capacity links weaken the LP relaxation (tighten to per-side upper bounds).

**Cost / risk.** Lowest engineering cost (the constraints are already in the paper; ~½ day).
Risk is purely performance. Also the ideal **cross-check oracle** for A/B on small–medium
instances, because it shares no cut-generation code with them.

**Verdict.** Build first — cheapest, dependency-free, and doubles as the validation oracle.

---

## 6. Option E — Preprocessing and reduction layer (solver-agnostic)

**Idea.** Shrink the instance before any MILP sees it, in three tiers of decreasing certainty:

- **E1 Safe reductions (optimality-preserving).** From the PCST/MWCS literature: contract
  degree-2 chains of zero-value zips; a zero-value degree-1 zip takes its neighbour's side; more
  generally a zero-value zip whose removal does not disconnect either side's candidate region is
  free and can be assigned last by a connectivity-repair pass. Articulation points of the pair
  subgraph are computed up front and reported (they predict contiguity cost — §9).
- **E2 Reduced-cost / Lagrangian fixing (optimality-preserving given a bound).** Validi et al.'s
  device: after the root LP (or the free Nash solve, which is an upper bound on the contiguous
  optimum), fix any `x_z` whose reduced cost exceeds the current UB−LB gap. Requires an incumbent
  (Option F) to be effective.
- **E3 Component-quotient fixing (heuristic).** Fix stray components of the free-Nash partition in
  place and solve on the quotient graph. **No published precedent; not optimality-preserving in
  general** (`raw/preprocessing.md` §1.4). Keep it, but only as a fallback that reports its gap
  against the unfixed relaxation bound, and validate it against ground truth on small instances.

**Literature.** Rehfeldt, Koch & Maher 2019 (reductions trivialise >90% of PCST benchmarks);
Buchanan, Wang & Butenko 2018; Fischetti et al. 2017 (node-based model for uniform costs — our
perimeter cost is uniform); Validi et al. 2022 (Lagrangian fixing: 1.09M → 12k variables).

**Guarantee.** E1/E2 preserve the certificate; E3 does not.

**Mechanisms.** (a) ● via E3 (the mechanism it was designed for) and ◐ via E1 (articulation-point
detection). (b) ● — every option benefits from fewer binaries. (c) ◐ — E2 fixes the dominant-value
zips early, which is the knapsack-hardness remedy suggested by Pisinger 2005. (d) ● — this is the
only option that directly targets the sparse-glue regime.

**Cost / risk.** E1 ~1 day in networkx; E2 ~1 day on top of any solver that exposes reduced
costs (SCIP, CBC; scipy's `milp` does not); E3 ~½ day. No dependencies. Risk: E1's "free glue"
argument must be proven for the *two-sided* case (both sides connected) — the PCST literature is
one-sided; write the proof or restrict E1 to the two rules above that are obviously safe.

**Verdict.** Not an alternative to A–D but a multiplier on all of them; mandatory for real data.

---

## 7. Option F — Feasible-first heuristics as warm start and fallback

**Idea.** Produce a connected bipartition cheaply and hand it to the exact solver as a MIP start
(and report it as the answer if the exact solver times out). Two constructions:

- **F1 Spanning-tree bisection (ReCom-style).** Draw random spanning trees of the pair subgraph;
  cutting any tree edge yields two connected pieces; pick the cut maximising `g_a·g_b`; local-
  search with contiguity-preserving boundary swaps. Always feasible, `O(n)` per tree.
- **F2 Discrete cut-and-choose (Bilò et al. 2022).** On a bipolar (st-) numbering of the pair
  subgraph, every prefix and suffix is connected; scan the numbering for the Nash-best prefix.
  Certified EF1 and G-MMS when the block-tree is a path — a *provable* fairness floor for the
  fallback, which F1 lacks.

**Literature.** DeFord, Duchin & Solomon 2021 (ReCom; `gerrychain` on PyPI); Bilò et al. 2022
Thm 3.10 / Prop. 3.2; Ríos-Mercado & Fernández 2009 and Bozkaya et al. 2003 (feasible-only
metaheuristics, no bound — lower priority).

**Guarantee.** None on welfare; F2 carries EF1/G-MMS. Gap is measured against the best UB from
any exact option (cross-method gap).

**Mechanisms.** (a) ● — never constructs a disconnected solution. (b) ◐ — a good incumbent prunes
the tree and makes E2 fixing bite. (c) ◐. (d) ◐.

**Cost / risk.** F1 ~1 day hand-rolled (no need for `gerrychain`; a spanning-tree cut is ten
lines); F2 ~1 day (st-numbering via `networkx` biconnected components + an ear decomposition).
Risk: none to correctness; only the question of how close the incumbent is.

**Verdict.** Build F1 early (feeds A/B/E2 and gives the overnight real-data run a guaranteed
answer); F2 mainly for the paper.

---

## 8. Option G — Engineering the existing loop (no new solver)

**Idea.** If a solver migration is deferred, four upgrades to `districting.py` that keep the
certificate: (G1) **in-out stabilisation** of the tangent step — separate at a convex combination
of the stable centre and the master optimum rather than the raw optimum (Ben-Ameur & Neto 2007);
(G2) **minimal-separator cuts** — replace the `|S|·Σ_{N(S)} x ≥ Σ_S x` neighbourhood cut with a
min vertex-cut between the component and the root (fewer, tighter cuts; Validi et al.); (G3)
**warm start and parallel MIP via `highspy`** directly (`kCallbackMipUserSolution`, `threads`) —
scipy's wrapper exposes neither; (G4) **data-scaled initial tangents** — the current seeds
`g0 ∈ {1,3,5,8,11}` are absolute and will be badly placed on dollar-scaled real data; seed at
quantiles of the free-Nash `g` range instead.

**Guarantee.** Unchanged (exact).

**Mechanisms.** (a) ○ (b) ◐ — helps, but the re-solve-from-scratch cost remains. (c) ● for the
iteration-inflation symptom (G1, G4). (d) ○.

**Cost / risk.** G1/G2/G4 ~1 day total, G3 adds `highspy` (MIT wheel). Risk: none; ceiling is low.

**Verdict.** Do G2 and G4 regardless (they carry over to A/B); G1/G3 only if A/B are blocked.

---

## 9. Option H — Bi-objective frontier enumeration as an audit tool

**Idea.** Treat `(g_a, g_b)` as a bi-objective MILP with hard contiguity; enumerate the
nondominated frontier by ε-constraint / triangle-splitting (Boland, Charkhgard & Savelsbergh
2015); pick the Nash-best point. Each subproblem is a *linear* MILP with contiguity — no OA — so
the Nash optimum over the enumerated frontier is exact, not ε.

**Guarantee.** Exact, if the frontier is fully enumerated.

**Mechanisms.** (a)/(b) ○ — each frontier point is a full contiguity MILP; on real scale this is
many solves, not one. (c) ◐.

**Verdict.** Not a production method. Useful as a second independent oracle on 50–100-zip
instances where brute force is impossible; include in Stage 1 only.

---

## 10. Not recommended (and why)

| Candidate | Reason |
|---|---|
| Zhang, Validi, Buchanan & Hicks 2024 linear-size planar formulation | Integral for *pure* connected partitioning, but the authors report it underperforms Hess once value/balance constraints are added; our `g_a, g_b` couplings are exactly that. Could be revisited if A–D all stall at scale. |
| OR-Tools CP-SAT | No lazy constraints at all; no continuous log. |
| Pyomo + MindtPy single-tree | Gurobi/CPLEX-only (verbatim in docs). Multi-tree mode is what we already have. |
| Bonmin / Couenne / SHOT | No Python callback surface for custom connectivity cuts; conda/source installs. |
| GerryChain as a dependency | F1 is ten lines; the package's value is ensembles, not optimisation. |
| METIS / multilevel coarsening | Heuristic, does not preserve connectivity on refinement, smooths the heavy tail we need to see. |

---

## 11. Recommended portfolio and order

```
Stage 0 (½ day)  D  flow one-shot on scipy/HiGHS  ──┐  cheapest; oracle for everything else
                 F1 spanning-tree warm start        ──┤  gives every later run an incumbent
                 G2/G4 cut + tangent hygiene         ──┘  carried into A/B
Stage 1 (2–3 d)  A  PySCIPOpt single tree   B python-mip single tree   C PWL-log (on D and on A)
                 E1 safe reductions, E3 quotient (as fallback with gap)
Stage 2 (1–2 d)  E2 reduced-cost fixing on the winning engine; ρ sweep; real-opportunity C10
```

Expected outcome, stated so it can be falsified by the battery: **A (or B) + C + E1/E2 + F1**
certifies every C1–C9 pair and the 400–800-zip real-opportunity instances within the Stage-2
time cap; **D + C** is competitive up to ~300 zips and is the regression oracle; **G alone** does
not clear C7.

---

## 12. Theory results to carry into the paper (§5 / "Why Nash")

**Framing (agreed 2026-08-28).** The paper's solution concept is the Nash bargaining solution
on the discrete feasible set `F` at `d=(0,0)`. With gains equal to bundle utilities this is the
same optimiser as *maximum Nash welfare* in the fair-division-of-indivisible-goods literature —
one object, two lenses. The bargaining lens supplies the axioms and the "constraints shrink `F`,
they do not change the criterion" argument (paper §Layer 5); the fair-division lens supplies the
guarantees that are theorems only at `d=0` (Pareto efficiency, EF1 — Caragiannis et al. 2019)
and the *connected-bundle* results below, which the bargaining literature does not have. The
paper should name the concept once, in §2, as "maximum Nash welfare (the Nash bargaining
solution at `d=0`)" so both literatures can be cited; keep the bargaining exposition.

Results, stated for our concept under the contiguity constraint:

- **Existence of a fair connected allocation.** A connected EF1 allocation for two agents exists
  on any graph whose block-tree is a path — every biconnected ZCTA blob — computable in O(m) by
  discrete cut-and-choose, and it is simultaneously G-MMS (Bilò et al. 2022, Thm 3.10, Thm A.3).
  This allocation is *not* in general the contiguous Nash optimum. Check the block-tree of each
  census component; report articulation points.
- **EF1 status of the contiguous Nash optimum is open.** The paper's "EF1 is a theorem at
  `d=0`" holds for the unconstrained solve. Once contiguity shrinks `F`, whether the maximiser
  remains EF1 for two agents is unresolved — all known counterexamples use ≥3 agents (Igarashi
  & Peters 2019; Bilò et al. 2022 §8). State as: "a connected EF1 allocation exists; the EF1
  status of the contiguous Nash solution is open; the battery reports envy directly."
- **Hardness.** Connected fair division is NP-hard even for two agents with identical valuations
  (Deligkas et al. 2021, Prop. 3) — justifies the MILP; no polynomial exact route exists.
- **Price of connectivity.** Exactly 4/3 for MMS on biconnected graphs, `1/k` at a `k`-way cut
  vertex (Bei, Igarashi, Lu & Suksompong 2022). No published bound for Nash welfare; the
  battery's 0.03–5% cost of contiguity can be reported against the MMS bound, and a Nash-specific
  bound is a candidate for original derivation.
- **Continuum vs. discrete.** In the continuum the Nash solution at `d=0` is an optimal-transport
  map whose cells are contiguous by construction (Warren 2025; Aurenhammer–Hoffmann–Aronov 1998
  power diagrams). No discrete analogue exists — a hard constraint is genuinely necessary on the
  grid, which is the bargaining-lens statement "contiguity shrinks `F`" made precise.
- Warren 2025: DOI 10.1007/s00030-025-01118-7 (NoDEA 32:109), arXiv:1712.07202.

---

## 13. Open questions the research did not settle

1. Hardness under heavy-tailed values combined with a Nash/bilinear objective — no literature;
   Pisinger 2005 (knapsack hardness from coefficient structure) is the nearest analogy. Original
   analysis if needed; the battery's C9 remains the primary evidence.
2. The `k=2` "connected bipartition" (complement also connected) is never treated as its own
   problem class; tighter two-sided cuts may exist (Miyazawa et al. 2021's balanced-connected-
   partition inequalities are the closest published family).
3. Whether E1's free-glue reductions are safe in the two-sided setting — needs a short proof.
4. Whether SCIP's native `log` handling (A′) yields a global certificate on this problem, versus
   hand-added tangents (A) — verify on C1 before relying on it.
