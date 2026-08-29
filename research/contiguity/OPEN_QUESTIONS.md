# Contiguity research — open questions and resume notes

**Date:** 2026-08-28. **Branch:** `worktree-contiguity-research` (worktree at
`.claude/worktrees/contiguity-research`, rebased onto `main` @ `5a1f115` the same day).
**Purpose of this file:** everything a fresh session needs to pick this work up without the
original conversation — what was decided, what was produced, what is still open, and who can
close each item. Items marked **[gate]** block something downstream.

---

## 0. How to resume

> **2026-08-28 (later): the development programme is approved — `research/contiguity/PLAN.md`**
> **is now the resume point.** Its §0 kick-off sequence and "Decisions taken" table supersede
> §A items 1, 2, 5, 6, 8, 9 below (opportunity file → synthetic twin; implementation in this
> repo; ρ=0 is the model; deps approved) and `TEST_PLAN.md` §6. Read PLAN.md first.

1. Read `CLAUDE.md` (repo root; carries traps 1–11), then `research/contiguity/OPTIONS.md`
   (the option briefs) and `research/contiguity/TEST_PLAN.md` (how to run them).
2. Sources: `research/contiguity/raw/{encodings,algorithms,solvers,preprocessing,fairdivision_graphs}.md`
   — five literature legs, every DOI Crossref-verified unless marked UNVERIFIED. The verified
   references are already appended to `literature/territory_bibliography.{bib,csv,md}` (33 → 78
   entries; new rows tagged `cont` / `minlp` / `fd`).
3. Environment: `.venv/bin/python3` from the **repo root** (system `python3` has no
   numpy/scipy/networkx). Pinned in `requirements.txt`: numpy 2.5.2, scipy 1.18.1, networkx 3.6.1.
   No solver packages beyond scipy's HiGHS are installed yet (`TEST_PLAN.md` §9 lists what to add).
   Machine: Apple M2 Max, 12 cores, 32 GB → plan assumes 11 parallel single-threaded jobs.
4. The numeric regression anchor for `districting.py` is `code/mkfig_zip50.py` (≈2 min; printed
   numbers must reproduce). `verify_algebra.py` passes but certifies the superseded
   d=(S_a,S_b) model. `battery/figures/*.png|json` are **primary artifacts** — do not rerun
   `run_battery.py` casually (~6.5 min, C7/C9 do not converge, it overwrites them).
5. **No code has been written for this study.** The user asked for a checkpoint before any
   implementation, and said implementation will be done "elsewhere" (see A.6).

## 0b. Decisions already taken (do not re-ask)

| decision | value | where recorded |
|---|---|---|
| Scope of options | formulations **and** architecture (solver, preprocessing, warm starts) | OPTIONS.md |
| Game-theory branch | included: fair division on graphs with connected bundles | OPTIONS.md §12, raw/fairdivision_graphs.md |
| Solvers | **open-source only** (no Gurobi/CPLEX) | OPTIONS.md, TEST_PLAN.md §9 |
| Scale target | 180 wholesalers across both firms ≈ 90/firm → ~375 ZCTAs per territory → **400–800 raw ZCTAs per pair**, active zips sparse; tiers must ≤300 / should ≤1000 / stretch 2000 | TEST_PLAN.md §2, §6 |
| Optimality | deviation from global optimality is a **headline metric**: certified gap, cross-method gap, brute-force ground truth (n ≤ 20), gap-vs-time profile | TEST_PLAN.md §3 |
| State borders | **off** for this study; must remain a one-flag rerun (`--respect-state`) | TEST_PLAN.md §5 |
| Real data | user will supply real **opportunity by zip**; battery/synth machinery must ingest it (C10); `A_z`/`B_z` synthesised conditional on real `M_z` | TEST_PLAN.md §6 |
| Runtime | overnight runs on this machine are acceptable; testing at scale sooner is wanted | TEST_PLAN.md §4 |
| Deliverable location | `research/contiguity/{OPTIONS,TEST_PLAN,OPEN_QUESTIONS}.md` + bib updates | this branch |
| Solution-concept framing | Nash bargaining solution at d=(0,0) ≡ maximum Nash welfare; keep the bargaining exposition, name the concept once in §2 so both literatures can be cited; connected-bundle results go in §5 | OPTIONS.md §12 |
| Research venue | run here (subagent fan-out with Crossref verification), not Claude.ai Research; Fable 5 for synthesis, Sonnet 5 for search legs | conversation 2026-08-28 |

## 0c. Recommended portfolio (from OPTIONS.md §11), stated so it can be falsified

```
Stage 0 (½ day)  D  flow one-shot on scipy/HiGHS      cheapest; oracle for everything else
                 F1 spanning-tree warm start           incumbent for every later run
                 G2/G4 cut + tangent hygiene           carried into A/B
Stage 1 (2–3 d)  A  PySCIPOpt single tree  ·  B python-mip/CBC single tree  ·  C PWL-log (on D and on A)
                 E1 safe reductions  ·  E3 component-quotient (fallback, reports gap)
Stage 2 (1–2 d)  E2 reduced-cost fixing on the winning engine; ρ sweep; real-opportunity C10 overnight
```
Prediction: A (or B) + C + E1/E2 + F1 certifies all C1–C9 pairs and the 400–800-zip
real-opportunity instances within the Stage-2 cap; D + C competitive to ~300 zips; G alone does
not clear C7. **First action when the opportunity file arrives:** run the *current* solver on the
real-opportunity instances overnight at a 20-min cap — the baseline every option is judged against.

---

## A. Decisions only the user can make

1. **[gate] Opportunity file** — columns, units, ZIP vs ZCTA, any state column; drop into
   `battery/data/` so the baseline overnight run can start. (`TEST_PLAN.md` §6, §10.1)
2. **[gate] Adjacency source** — Census TIGER ZCTA5 2020 shapefile (correct; ~500 MB; geopandas/
   shapely/pyogrio in the loader only, cached to parquet) vs. centroid Delaunay (same-day,
   caveated). Recommendation: shapefile. (§10.2)
3. **Rep territories** — synthesise ~90 seeds per firm on real geography (opportunity-weighted
   Voronoi + the existing `alpha` misalignment dial), or are real rep maps available? (§10.3)
4. **Stage-2 time cap** — 20 min per job overnight proposed; longer is possible. (§10.4)
5. **Screening scope** — all eight options, or drop H (audit) and most of G (loop engineering)?
   Recommendation: keep G2/G4 hygiene, drop the rest of G and H unless A/B are blocked. (§10.5)
6. **Where implementation happens** — the brief says "elsewhere"; `TEST_PLAN.md` §1 lays the
   harness out inside this repo (`battery/code/contig_methods/`, results under
   `battery/results/contiguity/`). Confirm, or point at the other location so paths are adjusted.
7. **Synthesised `A_z`/`B_z` on real `M_z`** — acceptable for the test plan; confirm it is also
   acceptable for the Stage-3 production dry run, or say when real sales data will exist.
8. **Dependencies** — approve adding `pyscipopt`, `mip`, `highspy` (and GIS libs for the loader
   only) to `requirements.txt`. All pip wheels on macOS arm64, permissive licences.
9. **ρ policy for the headline table** — screening at ρ=2e-3 (the C8 knee); finalists swept over
   {2e-3, 2e-4, 1e-5}. Confirm, and say whether exact Nash (ρ=0) should be attempted if in-out
   stabilisation (G1) removes the thrash.
10. **Commit / merge policy** — this branch holds research docs + bib only; say when to merge to
    `main` (the rebase was clean; `code/` and `battery/` untouched).

## B. Empirical — answered by the battery, not the literature

11. **Which engine wins at 400–800 zips** — SCIP single tree (A) vs. CBC (B) vs. one-shot
    flow+PWL on HiGHS (D+C). The literature puts the flow/cut crossover "at a few hundred units"
    (Validi et al. 2022; Duque et al. 2011 show flow failing to certify at n=25–49 without
    root-fixing), i.e. exactly our band. Must be measured.
12. **Whether component-quotient fixing (E3) ever loses optimality** — no published precedent;
    validate against brute force on T0 and against the unfixed bound on T1.
13. **Whether E1's zero-value-glue reductions are safe two-sided** — PCST/MWCS rules are
    one-sided; needs a short proof or a bit-identical `to_a` check on T0/T1 after expansion.
14. **How much the sparse real-data regime (d) costs on the current solver** — the baseline
    overnight run; decides whether this is a 2× or a 50× problem.
15. **Whether SCIP's native `log` handling (A′) certifies globally on this problem** vs. hand-added
    tangents (A); `raw/solvers.md` rates it medium confidence. Also `trySol` warm-start had
    historical bugs — smoke-test on the pinned PySCIPOpt.
16. **PWL grid size vs. B&B slowdown** (Option C) — SOS2 relaxations can be weak; measure ε=1e-4
    vs. 1e-6 with the Vielma–Nemhauser logarithmic encoding.
17. **Does in-out stabilisation (G1) remove the ρ=0 thrash** — if yes, exact Nash becomes
    runnable and the paper's claim upgrades from "exact for Nash-minus-a-penalty".
18. **Mechanism (c) under a real heavy tail** — C10-ht crosses (c) with (d); whether real
    opportunity is dPlN-shaped is itself unknown (`code/TAIL_DISTRIBUTION_NOTE.md`).
19. **Do minimal-separator (min vertex-cut) cuts beat the current `|S|·Σ_{N(S)} x ≥ Σ_S x`
    neighbourhood cut** in rounds and time (G2) — expected yes per Validi et al.; unmeasured here.
20. **Does an F1 incumbent materially shorten certification** (via pruning and E2 fixing)?
21. **Articulation points as a predictor of contiguity cost** — the MMS price-of-connectivity
    theory says cost jumps at cut vertices; test on the battery covariates (`TEST_PLAN.md` §3.6).
22. **Scaling** — the current solver seeds tangents at absolute `g0 ∈ {1,3,5,8,11}` and bounds
    `z ∈ [−50, 50]`; on dollar-scaled opportunity these are mis-placed. Plan rescales utilities so
    `Σ(u_a+u_b)=100` per pair; verify the free-Nash and contiguous solutions are invariant.

## C. Theory — open in the literature

23. **EF1 status of the contiguous Nash optimum for two agents** — a connected EF1 allocation
    exists on any graph whose block-tree is a path (Bilò et al. 2022, Thm 3.10), but whether the
    *Nash maximiser* under contiguity is EF1 is unresolved; known counterexamples use ≥3 agents
    (Igarashi & Peters 2019). The paper's "EF1 is a theorem at d=0" must be scoped to the
    unconstrained solve.
24. **Price of connectivity for Nash welfare** — none published (MMS only: exactly 4/3 on
    biconnected graphs, 1/k at a k-way cut vertex — Bei, Igarashi, Lu & Suksompong 2022).
    Candidate for original derivation; the battery bounds it empirically (0.03–5% so far).
25. **Complexity of contiguous MNW for exactly two agents on planar graphs** — connected
    EF/PROP/EF1 is NP-hard even for two identical agents (Deligkas et al. 2021, Prop. 3); nothing
    specific to the Nash objective; no pseudo-polynomial route known beyond paths/stars.
26. **Hardness under heavy-tailed values with a Nash/bilinear objective** — no literature;
    Pisinger 2005 (knapsack hardness from coefficient structure) is the nearest analogy.
27. **The k=2 connected-bipartition class** (complement also connected) is never treated on its
    own; tighter two-sided cuts may exist (Miyazawa et al. 2021 balanced-connected-partition
    inequalities are the closest published family).
28. **A discrete analogue of continuum contiguity** (Warren 2025 optimal transport / power
    diagrams) — none known; the ratio-threshold rule is empirically not contiguous (HANDOFF trap).
    Assessed 2026-08-28 (OPTIONS.md §12): OT does not help the solver because Warren's
    contiguity comes from distance-structured utilities, not from transport. What survives:
    (i) F3 OT-threshold warm start (TEST_PLAN §7); (ii) the two-sink Kantorovich LP is the
    fractional MNW relaxation = the convex-hull UB already in the paper, now recorded on every
    harness row as `UB_free`.
28b. **Modelling option — emergent contiguity via an explicit travel-cost term.** With
    `u_i(z) = c₁A_z + c₂B_z + λM_z − κ·d(z, p_i)` (`d` = graph shortest-path distance to rep
    `i`'s base `p_i`) and κ large relative to the data-term variation, the free Nash solution
    is an additively weighted graph-Voronoi partition, whose cells are connected (a vertex on
    a shortest path from `z` to its centre inherits `z`'s assignment). κ would replace ρ with a
    behavioural interpretation (rep travel) and is the natural N>2 route (Warren 2025).
    Open: (a) it changes the settled utility model and needs distribution sign-off; (b) needs
    rep base locations, which do not exist in the data; (c) redistributes welfare, so it is a
    different fairness question, not a reformulation; (d) for moderate κ the data term breaks
    cells and the hard constraint is still required — the threshold κ* at which contiguity
    becomes emergent on real data is unknown and measurable with the harness once `p_i` exist.
    Ties to CLAUDE.md's unbuilt "capacity constraints: travel time" item. Not pursued as a
    solver fix.
28c. **Would a different solution concept be more tractable? Assessed 2026-08-28: no.**
    The nonlinearity `log g_a + log g_b` is the easy part (concave in linear expressions;
    6–7 OA rounds free; Option C removes it at a certified ε). The hard part is contiguity,
    which is criterion-independent — connected fair division is NP-hard for two agents even
    with identical valuations (Deligkas et al. 2021), where every criterion coincides.
    Switching to utilitarian gives a pure MILP but corner solutions (paper: b left with 2.04);
    maximin / egalitarian / KS / equal-gain give a pure MILP (`t ≤ g_a, t ≤ g_b`) but lose
    Pareto efficiency (needs leximin), the EF1 theorem, and hit Trap 2 (equalising can make
    both worse — needs a welfare floor) — and their `min(·,·)` objective is *flat on a plateau*
    at the optimum, which is exactly the degeneracy that stops connectivity cuts biting
    (Trap 4). Nash's strict concavity is what the cut loop pushes against.
    What does buy tractability is on the feasible-set side: (a) restrict partitions to a
    structured family — for a 2-connected graph an st-numbering (Lempel–Even–Cederbaum) makes
    every prefix/suffix connected and the Győri–Lovász theorem guarantees connected
    2-partitions of any prescribed sizes, so any criterion is O(n) over prefixes (this is
    discrete cut-and-choose: fast, EF1-certified, heuristic w.r.t. the true contiguous
    optimum — Options F2/F3); (b) weaken the constraint (≤ k pieces; slivers below a share
    allowed); (c) coarsen the graph. All three change what is promised. Decision: keep Nash;
    spend effort on Option C and the feasible-set restrictions as warm starts.
    Still open: whether a leximin refinement of maximin over the *contiguous* set is ever
    wanted for the N>2 dense-component case (E.35), where Nash's two-player guarantees do not
    compose.

28d. **Relax exactness to an approximate-fairness guarantee (Suksompong 2019 style)?
    Assessed 2026-08-28: relax the certificate, not the criterion.** Two things are
    conflated under "exactness":
    (1) *Exact optimisation* — a zero-gap certificate. Relaxing this is cheap and already
    planned: Option C (ε-certified PWL log), time-capped B&C with the gap reported, EF1
    checked ex post (TEST_PLAN §3).
    (2) *Exact criterion* — replacing "maximise Nash welfare s.t. contiguity" by "construct
    any contiguous allocation with envy ≤ u_max / share ≥ proportional − u_max" (Suksompong
    2019 on paths; Bilò et al. 2022 lift EF1 to any graph whose block-tree is a path, O(m)
    cut-and-choose). Polynomial, but four losses, two landing on our hard instances:
    (a) efficiency — the construction optimises nothing; MNW is EF1 *and* Pareto-optimal,
    cut-and-choose is EF1 only, and the value left on the table is unbounded;
    (b) selection — many allocations satisfy the guarantee, so a secondary rule is needed,
    and the natural one (Nash-best prefix of an st-order) is Option F2, a heuristic with a
    measurable but unbounded gap; (c) the bound is additive in u_max — under heavy tails one
    mega-zip can be a large share of a book, so the guarantee is weakest in mechanism (c)'s
    regime; (d) topology — Bilò's characterisation is tight: a "trident" (cut vertex splitting
    the pair into ≥3 pieces) voids the 2-agent EF1 guarantee, i.e. the non-biconnected pairs
    of mechanism (a) are exactly where the approximate route gives up too.
    Middle grounds that keep the concept: use the constructions as fallbacks with a certified
    floor (F2/F3: "EF1 yes, envy ≤ u_max yes, gap to best UB x%"); report EF1 / envy-over-u_max
    / share − ½·total for the *Nash* solution on every harness row (answers item 23
    empirically); or restrict to intervals of a fixed ordering and solve exactly there
    (Suksompong's path results apply verbatim; loss vs. the true contiguous optimum measured
    by the harness — see 28c). Decision: keep MNW; relax the certificate; approximate fairness
    is the reported floor and the fallback, not the solution concept.
    Follow-up for TEST_PLAN: add `ef1`, `envy_over_umax`, `prop_shortfall` to the harness
    Result fields so every option's incumbent carries the approximate-fairness audit.

29. **Zhang, Validi, Buchanan & Hicks 2024 linear-size planar formulation** — rejected because
    integrality is lost under balance-type constraints; whether that carries over when the value
    coupling is in the *objective* (our case) rather than a hard constraint is untested.

## D. Unverified citations and unextracted numbers (re-check before citing)

30. UNVERIFIED DOIs: Williams 2002 (Networks, spanning-tree extended formulation); Cova & Church
    2000; Oh, Procaccia & Suksompong 2019 (O(log m) cut-and-choose); Margot symmetry survey;
    Han et al. 2017 / Jia et al. 2021 (generalised PCSF approximations); Yang et al. 2021
    (knapsack branching). None of these were added to the bibliography.
31. Numeric tables not extracted: Oehrlein & Haunert 2017 instance sizes; Carvajal et al. 2013
    formulation sizes; Validi et al. 2022 exact MCF/LCUT constraint counts; Kronqvist et al.
    2019 solver rankings; Mittelmann HiGHS/SCIP/CBC ordering on ~1k-binary MIPs.
32. Pisinger 2005 has two Crossref records (`10.1016/j.cor.2004.03.002` used; the
    `s0305-0548(04)00036-x` record is the in-press duplicate).

## E. Project gates outside this study (from CLAUDE.md, listed for completeness)

33. **theta** (transfer capture) — DiD / synthetic control on prior reassignments. Not done.
34. **State scope** — off here by decision; still an open business question with distribution.
35. **Three+ wholesalers / dense components** — leximin over components unimplemented (C2 α=0).
36. **`districting.py::solve_contiguous`** still on the old d=(S_a,S_b) baseline (`Sa, Sb =
    A.sum(), B.sum()`); `verify_algebra.py` certifies the superseded model. Flagged, not fixed;
    do not "fix" as a side effect.
37. **Paper (`nash_territory_division.tex`)** — still to do: Appendix C mixture-quantile
    shortcut derived at the old baseline; "equalisation destroys value" MILP numbers in
    Appendix A unverified at d=0; §5 battery findings and the three contiguity mechanisms not
    folded in; the OPTIONS §12 framing sentence and connected-bundle results not yet applied.
38. **Real ZCTA ingestion** beyond opportunity — sales `A_z`/`B_z`, rep maps, data source and
    procurement remain undecided.

## F. Housekeeping from this session

39. `.serena/project.yml` in this worktree now carries `main`'s tracked copy
    (`project_name: "td"`); the worktree-local version (`project_name: "contiguity-research"`)
    was set aside at `$CLAUDE_JOB_DIR/tmp/serena-project.yml.bak` and is disposable.
40. `raw/*.md` were written by search subagents and are verbose; OPTIONS.md is the curated view.
    If a claim in OPTIONS.md needs its source, grep the raw file named in the section.
