# Territory Division (td) — Claude Code Setup

**Last updated:** 2026-08-31
**Project:** Territory design for a new "national" annuity wholesaling channel
**Status: THE PROBLEM CHANGED SHAPE ON 2026-08-31. Read
`research/contiguity/NWAY.md` before anything else in this file** — much of what follows
describes the superseded two-player problem and is kept for provenance, not as instruction.

**What it is now.** The business is standing up a **new "national" channel**, carving the two
largest firms out of the financial-institutions and wirehouse channels. Territories are
targeted at roughly equal opportunity, ~$1B each. Sized 2026-08-31: **2,232 ZCTAs carrying
sales, 72 reps** (including an "open"/vacancy key), **~$6.2B opportunity**, footprint = west
coast / east coast / Texas / Florida with the **midwest uncovered**, so **k ≈ 6**.

**What that changed, in one line each.**
- Not two players. A zip can be claimed by 3+ reps → `battery/code/contig_methods/nway.py`.
- Not a merger. Greenfield balanced districting, solved in **two stages**: draw k balanced
  contiguous districts, then match reps to them → `contig_methods/channel.py` (stage 2 built,
  exact; stage 1 open).
- **Nash welfare on a common measure *is* equal-size districting** — same optimum, not an
  approximation — so the $1B target needs no constraint. This is why the existing Nash
  machinery still applies. NWAY.md §7.1.
- Not a synthetic twin. The **real instance leaves descaled** (shares + M/median(M), no
  currency amount), because at ρ=0 the objective is invariant to the dollar scale →
  `tools/instance_export/` + `battery/code/descaled.py`. NWAY.md §5b.
- The footprint is **disconnected**, which decomposes the problem by region *and* puts a
  **geometric ceiling on balance** — `channel.allocate_districts` computes it, and it is a
  free dual bound. $1B ± 10% may be unreachable. NWAY.md §7.7.

**Still true and still load-bearing:** the d=(0,0) rationale, every trap in the trap list
(12–15 are about tolerances and solver behaviour, none of it two-player), the two-tier
acceptance criterion, and `scip_tree`'s architecture. `scip_tree` certifies to 135 zips;
the new subproblems are ~500 zips per region.

**Legacy state (superseded, kept for provenance).** On `contiguity-harness`: harness, unit and
method waves merged; S0/S1/S2, W6b/W6c/W6d in `research/contiguity/RESULTS.md`. `scip_tree`
was the two-player finalist — every pair ≤ 135 zips certified, 124/135 proved exact global
optima by W6c, large pairs ε-certified at 5e-3.

---

## Quick Start

**Entry points, in order:**

1. **`nash_territory_division.tex`** — the paper. Nash formulation, prefix property,
   contiguity MILP, contestability, parameter breakpoints, the worked 50-zip instance.
   Alternative criteria are in its appendices.
2. **This file** — settled decisions, the model on one page, the trap list, code
   inventory, open gates.
3. **`battery/FINDINGS.md`** — synthetic case studies (C1–C9): what broke, why, and the
   three contiguity failure mechanisms. `battery/RESEARCH_PLAN.md` is the test plan.
4. **`SYNTH.md`** — the synthetic generator (S1–S7) and census `min_share` sensitivity.
   Read before running the census on real data.
5. **`research/contiguity/PLAN.md`** — **the approved development programme (2026-08-28) and
   the resume point for a fresh session.** §0 = kick-off sequence and environment facts;
   "Decisions taken" = what not to re-ask; Parts A–G = parallel-work protocol, workstreams
   and open questions, harness contract, twin export, graphics library, model assignment,
   generator v2 and regional instances.
6. **`research/contiguity/`** (the rest) — the 2026-08-28 literature study behind the plan:
   `OPTIONS.md` (eight option briefs, ranked), `TEST_PLAN.md` (harness spec, tiers, gap
   metrics, acceptance — still authoritative where PLAN.md does not override it),
   `OPEN_QUESTIONS.md` (40 items; §A partly superseded by PLAN.md). Read before touching
   `districting.py` or the paper's §5.

**Environment.** Use `.venv/bin/python3` for everything — the system `python3` has no
numpy/scipy/networkx. Dependencies are pinned in `requirements.txt`. Scripts assume the
**repo root** as the working directory.

MacTeX provides `pdflatex`/`latexmk` at `/Library/TeX/texbin`. That path is on `PATH` in
interactive login shells but **not** in non-interactive ones — prefix
`export PATH=/Library/TeX/texbin:$PATH` when building from a script or an agent shell.

**Minimal working example:**
```python
import networkx as nx
import territory as T
import districting as D

# Assume a networkx ZCTA graph G with per-node attributes:
# "rep_a", "rep_b", "A" (firm-A sales), "B" (firm-B sales), "M" (opportunity)
# "state" (optional)

T.validate(G)
ra, rb, _ = T.largest_pair(G)
zips = T.zips_for_pair(G, ra, rb)
exact_nash = T.solve(G, zips, "nash")  # outer approximation, 6–7 iterations
contiguous = D.solve_contiguous_nash(G, zips, rho=2e-3)  # + separator cuts
```

---

## What's Settled (Do Not Relitigate)

| Factor | Decision | Why |
|--------|----------|-----|
| **Utility model** | Linear / additive in A_z, B_z, M_z | Cobb-Douglas collapsed to one variable; had fatal zero-pathology |
| **Disagreement point** | d=(0,0) (gains are bundle utilities) | See below |
| **Solution concept** | Maximum Nash welfare (max g_a·g_b) | Exactly solvable via outer approximation; Pareto efficient by construction; finite algorithm with optimality certificates |
| **Fairness applies to** | All criteria (Nash, KS, egalitarian, equal-gain) | All use d=(0,0) |
| **Domain** | Discrete zips, not continuum | Exact, not approximate; matches data; Rook adjacency from networkx |
| **Compactness weight ρ** (decided 2026-08-28) | **ρ = 0 is the model**; contiguity is a hard constraint | ρ>0 was an engineering crutch for the multi-tree cut loop (traps 4, 7), not part of the model. Headline results at ρ=0; ρ=2e-3 only as a secondary column for the legacy solver. Tie-break by lexicographic perimeter post-pass, never a penalty. Travel-cost κ is explored separately (PLAN.md W11). |
| **Real data route** (decided 2026-08-28, **revised 2026-08-31**) | **Real instance, descaled.** PII/firm masked upstream; shares `S_i/M_z` and `M/median(M)` leave, no currency amount. `tools/instance_export/` + `battery/code/descaled.py`. | The dollar scale is not information the model uses: `u_i(z) = M_z·[c1·s_i + c2·(t_z−s_i) + λ]`, and `Σ log g_i` shifts by `n·log κ` under a rescale, so at ρ=0 the descaled and real instances have identical optima, gaps and certificates. Strictly better than a twin. `tools/twin_export/` is kept but superseded — see `research/contiguity/NWAY.md` §5b. |
| **Development mode** (decided 2026-08-28) | Subagents in git worktrees; main session reviews at ★ checkpoints | PLAN.md Part A; agent teams / Agent View not used for building. |

### Why d=(0,0) — the full rationale

Earlier drafts set the disagreement point at the pre-merger books, `d=(S_a, S_b)`, so a
gain was the *increase* over a rep's legacy production. An adversarial review reversed
this. Three arguments, in descending force:

1. **The threat point is not available.** After the merger neither rep can revert to
   their legacy book — there is no firm left to revert to. A disagreement point must be
   what each side gets if bargaining fails, and that is zero, not the status quo ante.
2. **EF1 requires a zero baseline.** Caragiannis et al. (2019) prove maximum Nash
   welfare over indivisible goods is Pareto efficient and envy-free up to one good.
   The theorem is stated for a zero baseline; subtracting a constant from each utility
   voids the guarantee. At `d=0` EF1 is a theorem, not an aspiration.
3. **It restores the optimal-transport correspondence.** Warren (2025) characterises
   continuum Nash bargaining; at a zero disagreement point the solution is an
   optimal-transport map, and the allocation boundary is a Laguerre-cell tessellation —
   contiguous by construction. This is also the natural route to N>2 wholesalers.

The migration removed a whole failure mode: under the old baseline the bargaining set
could be *empty* below a headroom threshold `lambda*` (trap 10). At `d=0` gains are
bundle utilities, positive by construction, so `lambda*` does not exist.

An explicit seniority tilt, if distribution insists on one, goes through **asymmetric
Nash** with a signed-off `omega` — never through the baseline. The reference
implementation was `review/code/omega.py::asym_nash`, deleted in the 2026-08-27 cleanup;
recover with `git show 99289ea:review/code/omega.py` if needed.

**Code status:** `territory.py` and `districting.py::solve_contiguous_nash` are at
d=(0,0) (migrated 2026-08-27). Two known holdouts — see *Baseline inconsistencies* below.

---

## The Model in One Page

For each postal code `z`: `A_z` (firm-A sales), `B_z` (firm-B sales), `M_z` (total market
opportunity). Totals `S_a`, `S_b`, `M`.

```
c1 = 1 - lam
c2 = theta * (1 - lam)                    # NET headroom convention throughout

u_a(z) = c1*A_z + c2*B_z + lam*M_z        # value of z to wholesaler a
u_b(z) = c2*A_z + c1*B_z + lam*M_z

g_a(S) = sum_{z in S}      u_a(z)         # gain at d=(0,0): the bundle utility
g_b(S) = sum_{z not in S}  u_b(z)

G_a^max = sum_z u_a(z)                    # attainable maxima
G_b^max = sum_z u_b(z)
```

Requires non-negative headroom pointwise:
`M_z >= max(A_z + theta*B_z, B_z + theta*A_z)`.

### Parameters

- **theta** (transfer capture): fraction of the other rep's book the inheriting rep
  retains. Estimable from historical reassignments by staggered DiD / synthetic control
  — *the one parameter resting on real identification work, and it has not been done*.
  Reference: 0.40.
- **lam** (headroom credit): how much a dollar of untapped opportunity counts against a
  dollar of booked production. Not estimable; a compensation-philosophy choice.
  Reference: 0.30.
- **rho** (compactness weight): fairness-versus-perimeter trade-off. Knee at 2e-3 on the
  battery (C8). `rho = 0` is exact Nash; anything positive solves Nash-minus-a-penalty.
  **Decision 2026-08-28: ρ=0 is the model** — the battery's ρ=2e-3 numbers are the legacy
  solver's, kept only for continuity (see *What's Settled*).

### Two algorithms — use the exact one

**Exact (default).** `log(g_a*g_b)` is *concave* in the linear expressions `g_a, g_b`, so
this is a convex MINLP and outer approximation is a finite global method. Add supporting
hyperplanes `z_a <= log(ghat) + (g_a - ghat)/ghat`, maximise `z_a + z_b`, add a tangent at
the incumbent, repeat. The tangent set is a relaxation, so its optimum is an upper bound;
when the incumbent meets it, that is an optimality **certificate**.

Validated against exhaustive enumeration, 120 instances per size: 100% exact match, bound
gap identically zero. 6–7 iterations regardless of n — 0.10s at n=50, 0.84s at n=400.
`territory.solve(G, zips, "nash")` uses this by default.

**Fast heuristic (preview / sanity check).**

```
r_z = u_a(z) / u_b(z)                     # exchange rate
sort zips by r_z descending
cumulative-sum u_a and u_b -> g_a[k], g_b[k] for k = 0..n
return argmax_k g_a[k]*g_b[k]
```

`O(n log n)`, no solver. **An approximation, not a theorem** — see trap 1.

---

## Traps — every one of these was hit during development

1. **The prefix rule is a heuristic, not a theorem — including for Nash.** The usual
   threshold argument is *marginal*, treating `g_a, g_b` as fixed while a zip moves;
   discretely they jump by a finite amount. Against exhaustive enumeration it is optimal
   only ~45% of the time at any size, though the shortfall shrinks with n:

   ```
   n=6    optimal 40%   mean shortfall 3.91%     worst 53.9%
   n=14   optimal 45%   mean shortfall 0.57%     worst 10.7%
   n=50                 mean shortfall 0.02%     (vs 1-swap local optimum)
   n=400                mean shortfall 0.0009%
   ```

   It is exact for the *utilitarian* criterion only (`{z : u_a(z) > u_b(z)}`). It fails
   outright for equal-gain, KS and egalitarian, which minimise a *distance*: over 400k
   random subsets max-min reached 14.096 vs the best prefix's 13.382. **Use `nash_exact`
   unless you specifically want a solver-free preview.**

2. **Equalisation can destroy value.** Minimising `|g_a - g_b|` can make *both*
   wholesalers worse off — an unconstrained equalising MILP hit a gap of 0.000161 at 82%
   of attainable welfare. Nash cannot do this. If you ever use an equalising criterion,
   add a welfare floor `g_a + g_b >= kappa * max(g_a + g_b)`; the right-hand side is
   closed-form because the utilitarian optimum is the prefix `{z : u_a(z) > u_b(z)}`.
   *(Re-verified at d=0 on 2026-08-30: the unconstrained equaliser reaches KS gap 5.2e-8
   at 98.1% of welfare but is Pareto-dominated by Nash — gains (7.3226, 7.0699) vs
   (7.3715, 7.2318). The 0.000161/82% figures are the old baseline's; the paper labels
   them as such.)*

3. **The mixture-quantile shortcut is off by one zip on discrete data.** Exact in a
   continuum only. Do not use it — enumerate the `n+1` prefixes instead.

4. **In the contiguity MILP, the compactness term is not optional.** Fairness alone is
   degenerate; many allocations tie, so contiguity cuts never bite and cut generation
   thrashes. An implementation without it ran 17 rounds without converging.

5. **`log(g_a·g_b)` does not linearise the objective — it concavifies it.** That is what
   makes outer approximation exact. A weighted-sum scalarisation `w*g_a + (1-w)*g_b`
   **collapses to corner solutions** when the frontier is near linear, which it is. An
   epsilon-constraint sweep works but needs one MILP per frontier point.

6. **Greedy island repair is catastrophic** — three orders of magnitude worse than the
   exact MILP. Use it to *detect* fragmentation, never to fix it.

7. **`rho` competes directly with the objective.** Sweep it; report product and perimeter
   together. At `rho = 1e-5` the boundary cut 25% of adjacency edges to gain 0.26% of
   product.

8. **Data uncertainty dominates parameter uncertainty.** Perturbing `lam` and `theta`
   across their defensible ranges moved 5 of 50 zips; 10% noise on sales moved 34.
   Getting `A_z` and `B_z` right matters more than settling `lam`.

9. **Nash's axioms assume a convex bargaining set.** Indivisible zips give a point cloud,
   so `max g_a·g_b` is the discrete analogue rather than the axiomatic solution. Measured
   cost of not randomising: 0.0034%. Ignore in practice, know it exists.

10. **VOID under d=(0,0) — kept for history.** Under the old pre-merger baseline Nash
    needed `g_a, g_b > 0`, and below a threshold `lambda*` the bargaining set was empty
    (`lambda*_net = lambda*_gross / (1 + lambda*_gross)`, ~0.069 on test instances). With
    the zero baseline, gains are positive by construction, so `lambda*` does not exist and
    the egalitarian fallback is unnecessary. Demonstrated on the tight-headroom battery
    case (C6): the instance that was infeasible under the old baseline solves routinely.

11. **Contiguity non-convergence has (at least) three independent causes.** See the next
    section — this is the live blocker, not a historical trap.

12. **`solve_contiguous_nash`'s "optimal" is certified only to `mip_rel_gap = 1e-4`.** Found
    2026-08-29 through the harness validator: `scipy.optimize.milp` defaults HiGHS to a 1e-4
    relative MIP gap, so the loop's master value (and hence its bound) can sit ~1e-4·|obj|
    above the incumbent when the cut loop stops (C8 pair, ρ=0: 6.3e-4 nats). `nash_exact`
    sets `mip_rel_gap=0.0`; the legacy loop did not. Pass `milp_options=dict(mip_rel_gap=0.0)`
    for a real certificate — on the C8 pair this also *moves the incumbent* (log-product
    6.47177 → 6.47234, 9 iterations instead of 14); the harness reports the loose case as
    status `gap_limit`.

13. **The legacy separator cuts are *invalid* on a disconnected pair graph.** Found
    2026-08-29 by U2's brute-force cross-check (S1_aligned n=50 seed=2, pair A1/B1: components
    {8,11} and {14,15,16,39,44,46}). `solve_contiguous_nash` fixes one root per side; a cut
    generated for a component `S` of a's side whose outside neighbours lie *inside a stray
    component* (e.g. `x_8 ≤ x_11`) forces growth toward a root that is unreachable, so it
    excludes allocations that are feasible under component-wise contiguity (PLAN.md C.0 #1).
    The master problem is then no longer a relaxation: its "optimal" value (6.283) sat *below*
    a feasible iterate the loop had already seen (6.436). Three consequences: (i) the loop's
    dual bound is unsound, not merely loose, whenever `pair_components > 1` (three of the six
    named failures); (ii) `contig_methods/current.py` detects `LB > UB` after recomputation
    and downgrades to `heuristic` with `UB=None`; (iii) every root-based formulation in the
    method wave (flow, SCIP/CBC trees, loop_v2) needs **one root per pair component** (or
    selectable roots) — this is the mechanism-(a) fix, and it is a formulation fix, not a
    solver fix.

14. **HiGHS 1.15 returns "Status 4: Solve error" under `*_feasibility_tolerance=1e-9`.** Found
    2026-08-29 (U5's compat test): `nash_exact` failed on C4_contested A0/B0 (27 zips) after two
    OA rounds, and `territory.solve` *silently* fell back to the prefix heuristic (8.96110 vs
    the exact 8.96316). The 1e-9 tolerances exist to stop the 1e-6-default stall (trap in
    `nash_exact`'s comment); 1e-8 solves the same instance exactly. `nash_exact` now retries
    down a ladder (1e-9 → 1e-8 → HiGHS defaults) on "Solve error", and `solve` warns when it
    falls back. Any new method forwarding tolerance options to HiGHS must guard the same way
    (W4's `flow` does). **SCIP (W6):** any lazily separated model needs
    `misc/allowstrongdualreds` and `misc/allowweakdualreds` **off** — with them on, presolve fixed
    a tangent-bounded variable to its bound before the lazy rows existed and "certified" a
    suboptimal warm start; `numerics/feastol=1e-9` is needed because the residual gap is primal
    slack ≈ 2·feastol; gains must be `ga ≤ Σu·x` (not `==`) or presolve multi-aggregates them and
    `trySol` dies; and the gain lower bound must come from the incumbent (`exp(LB0)/Σu_other`),
    not 1e-9, or the log's 1e9 gradient destabilises the LP. **Consequence for the anchor:** the contestability bootstrap in
    `mkfig_zip50.py` had been hitting this silently, so the 2026-08-28 anchor carried heuristic
    draws; the anchor was deliberately refreshed on 2026-08-29 (zip 22 doubt 0.5367 → 0.5400,
    zip 28 0.5700 → 0.5667, `nash_contestability.png` regenerated). The paper's Contestability
    numbers must be checked against the new `mkfig_zip50.py` output (see *Paper edits pending*).

15. **A solver abort reported as `time_limit` silently disables a retry ladder.** Found
    2026-08-30 (W6b): `scip_tree` maps SCIP's LP abort (`error in LP solver`, status `unknown`) to
    `time_limit` so the harness counts crashes, not capped runs, under `errors` — and its own
    `solve()` then continued the 1e-7/1e-6/OA ladder only on status `error`. Every S2 pair above
    ~125 zips stopped after 1–58 s of a 1200 s budget and the ladder never ran once; the "scale
    wall at ~125 zips regardless of budget" in `RESULTS.md` §S2 was this bug for `scip_tree`.
    Rules that follow: a retry decision must key on the *engine's* stop reason (`extra["retryable"]`),
    never on the harness-facing status; SCIP's `limits/time` runs on its own clock and under
    load can fire at ~half the wall budget (`_short_stop` retries such a stop); and a certificate from a
    rung at feastol f is a floating-point certificate, rigorous only to O(f·‖duals‖) — usually far
    tighter in practice (simplex vertices are exact unless a tolerance binds: C1-seed2 A3/B3
    certified to 2e-9 from a 1e-6 rung). **Resolved 2026-08-31 by W6c**
    (`contig_methods/cert_exact.py`, RESULTS.md §W6c): an exact post-hoc branch-and-bound
    (HiGHS as oracle, all pruning re-derived in exact integer arithmetic, product/AM-GM OA —
    no logs ever evaluated) proved the 124/135-zip incumbents are the exact global optima —
    those residuals were tolerance, not search. Run it as a post-pass on any
    tolerance-floor row; the 160+ dual-wall residuals (169/197) are real search and stay
    tier 2 (ε=5e-3).

### Contiguity MILP: three independent failure mechanisms (trap 11)

The outer-approximation + separator-cut loop in `solve_contiguous_nash` fails to converge
on certain instances. Root-cause analysis across C1–C9 identified **three independent
failure modes**, not one:

1. **Pre-existing graph disconnection** (C1-seed2 A0/B0, C5-respect_state A2/B2): the free-
   Nash partition already splits a pair into separate components before contiguity is
   imposed. Both the solver and human re-assignment prefer the split. Candidate fix:
   component-quotient preprocessing — detect undisputed stray components, fix them in
   place, then run the MINLP on the reduced graph.

2. **Pure scale** (C7 at n=400): HiGHS hits time/iteration limits at 125+ zips regardless
   of topology. Candidate fix: lazy-callback solver (Gurobi, or CBC via PuLP) or a
   flow-based contiguity formulation.

3. **Value concentration** (C9, heavy-tailed A_z/B_z): switching from lognormal to double
   Pareto-lognormal noise, same geometry and adjacency, **moves which pairs fail**.
   C9-seed2's previously-trivial 31-zip single-component pair (2 iterations under C1) now
   hits the iteration limit, while C1-seed2's previously-failing disconnected pair
   converges cleanly in 16. Cost % doubles-to-quintuples even on pairs that still
   converge. Fixer: unknown.

**Impact:** a fix aimed at one mechanism is not guaranteed to help the others. Any
candidate must be validated against all three. "Decouple fairness from compactness"
(free Nash → welfare floor → separate perimeter-minimising MILP, mirroring
`solve_contiguous`'s KS-gap pattern) was examined structurally and addresses *neither* the
disconnection nor the scale mechanism — it relocates where the difficulty shows up, from
one joint MILP to two sequential ones.

**Research verdict (2026-08-28, `research/contiguity/OPTIONS.md`).** The architecture is
right and the engine is wrong: lazily separated connectivity cuts in branch-and-cut are the
state of the art (Validi, Buchanan & Lykhovyd 2022 certify ~1,500 units), but HiGHS has **no
cut-injection callback**, so the restart-per-round loop is structural. The two cut families
have different convergence theories (OA: Duran–Grossmann; connectivity: combinatorial
Benders) and their iteration bounds *multiply*. The ρ=0 thrash is textbook Kelley
instability, fixable by in-out stabilisation. Corrections to the candidate fixes above:
Gurobi is excluded (open-source only — PySCIPOpt is the primary candidate, python-mip/CBC
the cross-check); component-quotient preprocessing has **no published precedent and is not
optimality-preserving** — keep it only as a fallback that reports its gap; a fourth regime,
**(d) sparse active zips with zero-value glue**, is what real data adds and is addressed
only by the reduction layer (Option E). Real pairs will be 400–800 ZCTAs (180 wholesalers
across both firms).

### Baseline inconsistencies (found 2026-08-27, re-verified; flagged not fixed)

- **`districting.py:161` is still on the old baseline.** `solve_contiguous` sets
  `Sa, Sb = A.sum(), B.sum()`, so the two districting entry points run on *different*
  disagreement points: `solve_contiguous_nash` is at d=(0,0), `solve_contiguous` is not.
  Its `Amax`/`Bmax` and welfare-floor constraint inherit the old baseline too.
- **`verify_algebra.py` certifies the superseded model.** All 35 SymPy checks pass, but
  they carry the `- Sa`/`- Sb` subtractions (lines 46-47, 110-114) and the old
  mixture-quantile `q` (line 48). It cannot certify d=(0,0) and did not catch the
  migration. The numeric anchor is `code/mkfig_zip50.py` (see below).

### Parameter estimation

- **theta** is the single most-important lever. Everything rests on it. Needs DiD or
  synthetic control on prior territory reassignments (split by *why* the prior rep left:
  internal move, industry exit, or departure to a competitor — the third has the loss).
  **Not done.**

### Real data blocking

- Real data (opportunity, sales, rep maps) exists on the user's confidential work machine
  and **cannot be brought here**. Route decided 2026-08-28: the synthetic twin
  (`PLAN.md` Part C.2, unit U3) plus public TIGER geometry (U4) and public-data regional
  instances (U8: NY+, CA+, TX). The twin gates only the T3/T4 tiers; S0/S1 run without it.

### Algorithmic gaps

- **Three+ wholesalers:** no threshold rule. Leximin over dense components is the natural
  extension; unimplemented. Warren (2025)'s semi-discrete transport → Laguerre cells is
  the other route worth exploring — but note (assessed 2026-08-28, `OPEN_QUESTIONS.md`
  28/28b): the continuum contiguity comes from distance-structured utilities, not from
  transport; on data-driven per-zip utilities the OT/threshold solution *is* the free Nash
  solution. It becomes structural only under a modelling change (an explicit travel-cost
  term `−κ·d(z, p_i)`, which makes the free solution a connected graph-Voronoi partition
  for large κ). Not a solver fix.
- **Dense components (C2 at alpha=0):** two-player fairness does not compose. Every pair
  within a dense blob gets its own bilateral solve, which looks perfect while no
  component-level fairness is defined. Unimplemented. **Recommended design (PLAN.md G.4,
  W12):** every zip has exactly two candidate owners (its legacy A-rep, its legacy B-rep),
  so component-level maximum Nash welfare `Σ_i log g_i` stays one binary per zip, convex,
  OA-exact, with per-rep contiguity — MNW over leximin. User decides at ★.
- **State borders:** life and annuity product availability is state-scoped. If
  `respect_state=True`, the state constraint becomes the binding one (C5: shatters 18.6%
  of edges, can fragment multi-state pairs into 5+ pieces). **Must be settled with
  distribution before tuning anything downstream.**
- **Capacity constraints:** travel time and producing-advisor count per rep, not bundled
  into M_z. Unbuilt.

### Paper edits pending

Done in the 2026-08-27 pass (do not redo): Setup and "The bargaining problem" rewritten
around d=(0,0) with the classical Nash axioms; the stale `lambda*` paragraph removed from
"Why Nash"; the prefix heuristic moved from the main body into Appendix B; Appendix A's
comparison tables (KS, egalitarian, equal-gain) and the §5/§6/Contestability/breakpoints/
opportunity-balance numbers all recomputed at d=0 via `code/mkfig_zip50.py`.

**Done in the 2026-08-30 pass (do not redo):** all ten steps of the *Integrating the
contiguity research* list below (framing sentence in §2 Layer 4; scoped EF1 with
`bilo2022`/`igarashipeters2019`; encoding citations + one-shot comparison in §2; root-free
cut warnbox + single-tree paragraph in §5 `sec:cuts`; three-trap warnbox with the
convergence-theory multiplication and in-out/PWL remedies; new §5 subsection "Failure
mechanisms at scale" (`sec:mechanisms`) carrying the three mechanisms, the sparse-glue
regime, the 2026 harness results, and the two-tier ε=5e-3 certificate; price-of-connectivity
paragraph (`bei2022`, `deligkas2021`); continuum-paragraph caution + travel-cost κ;
open-source stack in §Implementation; Related-work paragraph in §Setup; prefix-as-OT-bound
sentence in Appendix B; `kalai1975` cited). **Contestability doubts updated** from the
refreshed anchor (zip 22 0.537→0.540, zip 28 0.570→0.567; other rows re-verified
unchanged, figures byte-identical). **Equalisation numbers re-verified at d=0** and both
sites rewritten: the unconstrained equalising MILP over all subsets reaches KS gap 5.2e-8
at 98.1% of attainable welfare (vs 99.5% for the Nash prefix), gains (7.3226, 7.0699) —
Pareto-dominated by Nash's (7.3715, 7.2318), so "both parties worse off" survives at d=0
in a cleaner form; the old 0.000161/82.1% figures are kept only as the labelled pre-merger
baseline comparison. Builds clean, `.blg` and `.log` free of undefined citations/references.

**Still open in `nash_territory_division.tex`:**

- **Appendix C (mixture-quantile shortcut)** still derives its closed form under the
  discarded d=(S_a,S_b) baseline. Flagged in-paper as an open item, not re-derived.
- `mariotti1998` / `xu2005` (non-convex bargaining, relevant to trap 9) remain uncited —
  a candidate one-sentence addition to the §2 non-convexity warnbox.
- The S3/real-data results are not yet in the paper (blocked on the twin); when they land,
  extend `sec:mechanisms` with the production-size table.

### Integrating the contiguity research into `nash_territory_division.tex`

**Completed 2026-08-30 (see "Done in the 2026-08-30 pass" above); kept for provenance.**

Source of truth: `research/contiguity/OPTIONS.md` (§0 for the four-sentence verdict, §12 for
the theory results and framing, §11 for the portfolio) and `OPEN_QUESTIONS.md` §C for what
to state as open. All 45 new references are already in
`literature/territory_bibliography.bib` (keys below are the `.bib` keys — `grep "^@"` to
confirm before citing). Rules: cite only keys that exist; brace-protect proper nouns in any
new `.bib` entry; **do not add numbers the harness has not produced** — the existing ρ-sweep
table on the 50-zip instance stays as is until `TEST_PLAN.md` Stage 1 results exist; build
with `make` (needs `export PATH=/Library/TeX/texbin:$PATH`) and check the `.blg` for
undefined citations.

1. **§2 "The bargaining problem" (`sec:statement`), Layer 3 or 4.** Name the concept once:
   "maximum Nash welfare — the Nash bargaining solution at `d=0`" — so both literatures can
   be cited. Keep the bargaining exposition; it supplies the axioms and the "constraints
   shrink `F`" argument (Layer 5). Cite `caragiannis2019` (already) and, for the graph
   setting, `bouveret2017`.
2. **§2 Layer 2 / §4 "Why Nash" — scope the EF1 claim.** "EF1 is a theorem at `d=0`" holds
   for the unconstrained solve. Add: a connected EF1 allocation for two agents exists on any
   graph whose block-tree is a path (`bilo2022`, Thm 3.10; every biconnected census
   component qualifies), computable in O(m) by discrete cut-and-choose; whether the
   *contiguous Nash maximiser* is EF1 for two agents is **open** (known counterexamples use
   ≥3 agents — `igarashipeters2019`). The harness reports it empirically (`TEST_PLAN.md` §1 audit
   fields).
3. **§2 "Two representations of connectivity" + §5 `sec:cuts`.** Cite the encodings:
   flow (`shirabe2005`, `shirabe2009`), separator cuts and the CUT/MCF/LCUT comparison
   (`validi2021`, `validibuchanan2022`), the three-way one-shot comparison (`duque2011`), the
   linear-size planar formulation and why it is not used here (`zhang2024`). State that the
   separator-cut loop as implemented is a *multi-tree* scheme and that the production route
   is a single branch-and-cut tree with lazy cuts (`quesada1992`, `bonami2008`,
   `validi2021`); note the aggregated one-cut-per-component separation.
4. **§5 "Formulation" warnbox — add the convergence-theory trap.** The tangent cuts and the
   connectivity cuts have different finite-convergence arguments (`duran1986`,
   `fletcher1994` vs. `hooker2003`, `codato2006`); the combined worst-case bound is their
   product. The ρ=0 thrash is Kelley instability (`lemarechal1995`); the remedy is in-out
   stabilisation (`benameur2007`, `fischettisalvagnin2010`). Mention the ε-certified
   piecewise-linear alternative that removes the OA loop (`caragiannis2019` §6,
   `vielma2011`).
5. **§5 "Result" → new subsection "Failure mechanisms at scale".** Fold in
   `battery/FINDINGS.md`: the three mechanisms with their named instances (C1-seed2 A0/B0,
   C5 A2/B2, C7 125/205, C9-seed2 A2/B2), the 2–5× cost inflation under heavy tails
   (`pisinger2005` as the hardness analogy), and the fourth regime real data adds (sparse
   active zips). Cite the reduction literature for that regime (`rehfeldt2019`,
   `buchanan2018`, `fischetti2017`). Keep it qualitative until Stage 1 numbers exist; then
   add the option-comparison table from `RESULTS.md`.
6. **§5 — price of connectivity.** Report the battery's 0.03–5% cost of contiguity against
   the theoretical price of connectivity: exactly 4/3 for MMS on biconnected graphs, 1/k at
   a k-way cut vertex (`bei2022`); no published bound for Nash welfare — state as open.
   Connected fair division is NP-hard even for two agents with identical valuations
   (`deligkas2021`) — cite where the MILP is justified.
7. **§4 "The continuum limit agrees" paragraph.** Keep `warren2025`; add that the continuum
   contiguity comes from distance-structured utilities (power diagrams —
   Aurenhammer, Hoffmann & Aronov 1998 is **not** in the `.bib`; add it via the
   `LITERATURE_WORKFLOW.md` DOI check first, else cite `warren2025` only) and has no discrete analogue,
   which is why the hard constraint is needed; the discrete-OT relaxation is the convex-hull
   bound already discussed in §4. Mention the travel-cost κ route as future work here or in
   §"Implementation and scope" alongside the N>2 remark (line ~584).
8. **§"Implementation and scope"** — replace "Gurobi or CBC" style remarks with the
   open-source stack decision (PySCIPOpt primary, python-mip/CBC cross-check; HiGHS has no
   lazy-cut callback) and point to `research/contiguity/TEST_PLAN.md` for the harness.
9. **Related work / §1.** The districting lineage (`hess1971`, `zoltners*`,
   `salazaraguilar2011`, `rosmercado2012` — note the pre-existing key's spelling) and the fair-division-on-graphs lineage
   (`bouveret2017`, `bilo2022`, `suksompong2019`, `bei2022`) are both now in the `.bib`;
   this is the editorial pass the "related-work grounding is thin" item asks for.
10. **Appendix B (prefix heuristic).** One sentence: the prefix/ratio-threshold rule is the
    fractional (discrete-OT) relaxation of two-agent MNW, hence an upper bound on the free
    value; contiguity restricts the feasible set further (`OPEN_QUESTIONS.md` 28c/28d for
    why neither maximin nor an approximate-fairness criterion is more tractable).

After the edit: `make`, confirm no `Citation ... undefined` in `nash_territory_division.blg`,
and update the "Still open" list above.

---

## Code Structure

### Main modules (`code/`)

| Module | Role | Key functions |
|--------|------|---|
| **territory.py** | Core solver against a networkx ZCTA graph. At d=(0,0). | `validate`, `census` (components), `nash_exact` (outer approximation), `solve` (exact or heuristic), `compare_criteria` (KS, egalitarian, etc.), `contiguity_report`, `contestability` (bootstrap robustness), `write_back` (commit assignment) |
| **districting.py** | Contiguity MILP with separator cuts | `solve_contiguous_nash` (Nash + hard contiguity, **at d=0**), `solve_contiguous` (KS-gap variant: free Nash + welfare floor + perimeter min — **still on the old baseline**, line 161) |
| **synth.py** | Synthetic instance generator | Multi-rep battery: alignment, correlation, slivers, state borders, headroom, value concentration (heavy-tail dial via double Pareto-lognormal); 12 scenarios (S1–S7); see `TAIL_DISTRIBUTION_NOTE.md` |
| **zip50.py** | The paper's §5 worked instance | Deterministic (seed 17); writes `/tmp/z50.pkl`, which `mkfig_zip50.py` reads |
| **mkfig_zip50.py** | **The project's numeric anchor.** Regenerates §5's numbers and three of the four zip50 figures at d=(0,0) | Verified 2026-08-27: runs clean in ~2 min from the repo root and reproduces `figures/*.png` **byte-identically**. Prints everything §5, §6, Contestability, breakpoints, opportunity balance, and Appendix A/B need. `zip50_distributions.png` is deliberately not regenerated — every panel is a function of the raw instance only, so d=0 never touched it. Adjacency is a Delaunay triangulation on the centroids, reproducing the paper's 50 zips / 132 edges exactly |
| **verify_algebra.py** | 35 SymPy symbolic checks | 35/35 pass, but against the **superseded** d=(S_a,S_b) model. Standalone; does NOT exercise `territory.py` |
| **verify_2d.py** | Verification for the 2-D continuum note | Reproduces that note's numbers on a 600×600 grid. Now the only trace in-repo of its one portable result: **bimodal books do not disconnect a territory in the plane**, unlike on a line — so part of the apparent 1-D contiguity cost is a projection artefact |
| **census_stress.py** | Census `min_share` sweep, corr dial, state binding | Writes `figures/census_stress.png` |
| **mkfig_census.py** | Standalone plot script for the census stress test | **Not** a shared style module — nothing imports it; the battery carries its own `MAP_RC` in `battery/code/mapviz.py` |
| **territory_demo.py** | End-to-end smoke test | Synthetic lattice with misaligned territories and state bands |

### Expected graph schema

```python
G.nodes[z] = {
    "rep_a": <id>,  "rep_b": <id>,          # firm-A and -B rep IDs
    "A": <float>,   "B": <float>,   "M": <float>,  # sales, sales, opportunity
    "state": "NE",                           # optional; triggers respect_state=True path
}
# Edges = Rook adjacency (4-neighbor grid) between ZCTAs
```

---

## Workflows

Run everything from the **repo root** with `.venv/bin/python3`.

### Generate a synthetic case

```bash
.venv/bin/python3 code/synth.py --scenario S1_aligned --seed 1
# Outputs: (n_zips, S_a, S_b, M, A_z[], B_z[], M_z[], state[], rep_a[], rep_b[], adj_matrix)
```

Pick from S1–S7 in `SCENARIOS`. `S7_heavytail` is the dPlN tail dial for A_z, B_z — see
`code/TAIL_DISTRIBUTION_NOTE.md`.

### Regenerate the paper's worked instance (the numeric anchor)

```bash
.venv/bin/python3 code/mkfig_zip50.py
# ~2 min. Prints every number §5/§6/Contestability/breakpoints/Appendix A+B need,
# rewrites figures/{nash_solution,zip50_nash_milp,nash_contestability}.png
```

Run this after any change to `territory.py` or `districting.py`: the printed numbers are
the regression test, and the PNGs should come back byte-identical if nothing moved.

### Verify the algebra

```bash
.venv/bin/python3 code/verify_algebra.py    # 35 SymPy checks; exits nonzero on failure
```

Symbolic only, and against the superseded baseline — it cannot certify d=(0,0).

### Run the full battery (C1–C9)

```bash
.venv/bin/python3 battery/code/run_battery.py
# Writes battery/figures/C*.png + C*.json + battery_run_log.json
```

**Treat `battery/figures/*.png` as primary artifacts, not derived outputs.** A full run is
a ~17-case MINLP sweep taking ~6.5 minutes, and C7/C9 do not reliably converge — so don't
re-run casually; it overwrites them. Each case produces a three-panel figure (pre-merger
territories → exact Nash → contiguous MINLP, all zip-level Voronoi choropleths) and a
metrics JSON (bound gaps, fragmentation, perimeter, product cost of contiguity).

### Stress-test the census

```bash
.venv/bin/python3 code/census_stress.py     # writes figures/census_stress.png
```

### Build the paper PDF

```bash
export PATH=/Library/TeX/texbin:$PATH      # needed in non-interactive shells
make            # latexmk -pdf nash_territory_division.tex
make clean      # remove latexmk-generated aux/log/etc.
```

The `.tex`, the `Makefile`, and the PDF all live at the repo root;
`\graphicspath{{figures/}}` resolves the four figures from there. The PDF target depends
on the `.tex`, `literature/territory_bibliography.bib`, and `figures/*.png`, so a
bibliography or figure change triggers a rebuild; `latexmk` runs BibTeX automatically.

Proper nouns in `.bib` titles are brace-protected (`{Nash}`, `{MINLP}`, `{COSTA}`) —
`plainnat` lowercases titles otherwise. Protect them in any new entry.

---

## Next Steps (Priority Order)

### 0. The active programme: `research/contiguity/PLAN.md` (approved 2026-08-28)

Everything under items 2–3 below is now scheduled inside PLAN.md. Kick-off order (PLAN.md §0):
U0a anchors → U0b `districting.py` hygiene → U0c deps → U1a harness contract (freeze) →
parallel wave (U1b tiers/bench, U2 current/brute/bounds, U3 twin export, U4 TIGER loader,
U5 synth v2, U7 gfx) → S0 smoke → method wave W4–W9a → S1 screening → finalists → S2/S3.
Plus W11 (travel-cost κ), U8 (regional instances), W12 (component MNW). Every leg has a ★
review checkpoint; model per unit in Part E; own-plan-step units in Part F.

### 1. Paper edits (publish & communicate)

Work the **Still open** list under *Paper edits pending* above: fold the C1–C9 battery
findings and the three contiguity mechanisms into §5/§6, re-derive or retire Appendix C,
re-verify the Appendix A equalisation numbers at d=0, and apply the ten-step
*Integrating the contiguity research* list (framing sentence in §2, scoped EF1 claim,
encodings and convergence-theory citations in §5, price-of-connectivity paragraph,
related-work pass).

Outcome: paper ready for circulation.

### 2. Fix contiguity convergence (unblock real data at scale) — scheduled in PLAN.md

Follow `research/contiguity/PLAN.md` (which sequences the below); the option briefs are in
`OPTIONS.md` §2–§9, the harness spec in `TEST_PLAN.md`. Note PLAN.md's overrides: **ρ=0
headline** (ρ=2e-3 secondary for `current` only; the ρ sweep below is dropped), C10 is the
synthetic twin, G1 in-out is required, G3/H dropped:

- **Stage 0 (½ day):** Option D (Shirabe flow one-shot on scipy/HiGHS — the constraints are
  already in the paper) as the oracle; F1 spanning-tree warm start; G2/G4 cut and tangent
  hygiene (minimal-separator cuts; data-scaled tangent seeds — the current `g0 ∈ {1..11}`
  and `z ∈ [−50, 50]` are absolute and wrong on dollar-scaled data).
- **Stage 1 (2–3 days):** Option A PySCIPOpt single-tree branch-and-cut (primary), B
  python-mip/CBC (cross-check), C ε-certified PWL log, E1 safe reductions, E3 quotient as a
  gap-reporting fallback. Screening at 60 s caps ≈ 20 min wall on 11 workers.
- **Stage 2 (overnight):** finalists at 20-min caps, ρ ∈ {2e-3, 2e-4, 1e-5}, plus C10
  real-opportunity instances (400–800 zips) — the machinery is specified in `TEST_PLAN.md`
  §6 and needs the opportunity file (`OPEN_QUESTIONS.md` §A, items 1–2 are gated).
- **First thing when the opportunity file lands:** run the *current* solver on C10 overnight
  for the baseline gap-vs-time profile.

**Validation must cover all three failure mechanisms plus the sparse-glue regime** before
declaring sufficiency. Acceptance (`TEST_PLAN.md` §3, §7): brute-force match on n ≤ 20; all
C1–C9 pairs certified with gap ≤ 1e-8 (ε-methods: ≤ ε); the six named failures certified
within cap; `pieces = 1/1`; product ≤ free product; the deviation-from-optimality metrics
(certified gap, cross-method gap, gap-vs-time) reported for every option. Open-source
solvers only. State borders off, but `--respect-state` must remain a one-flag rerun.

### 3. Leximin over dense components (future architecture)

Where the census reveals dense (3A-vs-5B) overlap: either decompose the bilevel
subproblem — compute a maximin welfare floor over dense pairs, then maximise total
welfare subject to it — or adopt a lexicographic rule. Test on C2 at alpha=0.

---

## Prerequisites (parallel / blocking)

### Real ZCTA data ingestion (GATE → resolved by the twin route, PLAN.md C.2/C.3)

- Geometry: Census TIGER ZCTA5 2020 (public) downloaded here; Rook adjacency cached to
  `data/zcta_adjacency.npz` (U4). State membership from the Census ZCTA→state relationship
  file; population/income from public Census tables (U8).
- Values: `tools/twin_export/` run by the user on the work machine → `twin_stats.json`
  (aggregates) + `twin_instance.json.gz` (synthetic twin), user-audited before export (U3).
- Loader: `battery/code/twin.py::load_twin` → repo graph schema; validate headroom, census
  at `min_share` sweep, active-zip fraction per pair.

### Estimate theta (parameter identification)

- DiD or synthetic control on historical territory reassignments, split by reason
  (internal move / industry exit / departure to a competitor — the third has the loss).
- Outcome: point estimate + confidence interval for the merger scenario.

### Settle the state-scope question (decision gate)

- Consult distribution on whether territories must respect state lines.
- If yes: `respect_state=True` downstream, and flag that the state constraint is the
  binding one (C5: 18.6% of edges cross state, multi-state pairs shatter into 5+ pieces).
- If no: proceed without it, but document the assumption.

---

## Key Files & Documents

### Paper & method

- **`nash_territory_division.{pdf,tex}`** — the paper. Root of the repo; builds with `make`.
- **`Makefile`** — `latexmk` wrapper for the above.
- **`figures/`** — the paper's four PNGs plus `census_stress.png`. Three of the four
  regenerate via `code/mkfig_zip50.py`; `zip50_distributions.png` is d-independent.

### Synthetic battery & findings

- **`battery/RESEARCH_PLAN.md`** — the C1–C9 test plan and acceptance criteria.
- **`battery/FINDINGS.md`** — results, verified numbers, root causes, structural insights.
- **`battery/code/case_pipeline.py`** — per-case runner (instance → census → exact Nash →
  contiguous MINLP → 3-row figure + JSON).
- **`battery/code/run_battery.py`** — batch runner. Paths resolve relative to the repo root.
- **`battery/figures/C*.{png,json}`** — 15 outputs; `battery_run_log.json` has wall times
  and iteration counts.
- **`SYNTH.md`** — the S1–S7 scenarios: what each kills, and census `min_share`
  sensitivity.
- **`code/TAIL_DISTRIBUTION_NOTE.md`** — the heavy-tail dial (dPlN), citations,
  backward-compatibility verification.

### Contiguity research (2026-08-28)

- **`research/contiguity/PLAN.md`** — **the approved development programme; resume point.**
  §0 kick-off, decisions table, Parts A–G (parallel protocol, workstreams + open questions,
  harness contract, twin export, graphics, models, generator v2 / regional / component MNW).
- **`research/contiguity/OPTIONS.md`** — the problem in three sentences; eight option briefs
  (A SCIP single tree, B CBC lazy constraints, C ε-certified PWL log, D Shirabe flow,
  E reductions/fixing, F warm starts incl. OT-threshold, G loop engineering, H frontier
  audit) scored against mechanisms (a)–(d); not-recommended table; portfolio; §12 theory
  results and the solution-concept framing; OT assessment.
- **`research/contiguity/TEST_PLAN.md`** — harness layout (`battery/code/contig_methods/`,
  results under `battery/results/contiguity/`, never `battery/figures/`), instance tiers
  T0–T4, optimality-gap metrics, stage/cap/wall-time table, `--respect-state` switch, C10
  real-opportunity machinery, per-option acceptance, dependencies to add.
- **`research/contiguity/OPEN_QUESTIONS.md`** — 40 items in six groups plus resume notes
  and the table of decisions already taken. **Start here in a new session.**
- **`research/contiguity/raw/*.md`** — the five literature legs (encodings, algorithms,
  solvers, preprocessing, fair division on graphs); verbose; grep them for a source.

### Literature

- **`literature/territory_bibliography.{md,csv,bib}`** — the full annotated citation set,
  three synchronised formats (78 entries; 45 added 2026-08-28 under "Contiguity: encodings,
  algorithms, preprocessing" and "Fair division on graphs"). Every entry carries a
  resolving DOI; the `.bib` parses under `plainnat` with `\nocite{*}`.
- **`literature/LITERATURE_WORKFLOW.md`** — how that bibliography was built and how to
  extend it (DOI resolution against fabrication; citation-graph traversal against silent
  incompleteness). Generic and reusable; not territory-specific.

### Deleted 2026-08-27 — recoverable from git

The `handoff/` flatten and cleanup removed `HANDOFF.md`, `SIMPLIFICATION_PROPOSAL.md`,
`papers/`, all of `review/` (the adversarial review, its 18 analysis scripts, its
figures), and `reference/` (the 2-D continuum and earlier all-criteria drafts). Their
load-bearing content has been absorbed into this file and the paper. Recover anything
else with `git show 99289ea:<path>`. The three most likely to be wanted:
`review/code/omega.py` (asymmetric Nash), `review/HANDOFF_REVIEW.md` (the full objection
1–4 record), and `method.md` — a `problem-framing` Claude skill file, removed 2026-08-27,
which is the provenance for the d=(0,0) reversal: the adversarial review's §2 and §5 are
its Grothendieck and Gromov passes.

---

## Code Conventions

### Naming

- **g_a, g_b**: gains at the disagreement point (d=0); bundle utilities
- **u_a(z), u_b(z)**: per-zip utility to each rep
- **rep_a, rep_b**: wholesaler IDs (nodes in the census overlap graph)
- **z**: a ZCTA node; **S** or **assignment**: the subset of zips allocated to rep A
- **theta**: transfer capture (0–1); **lam**: headroom credit (0–1); **rho**: compactness
  weight (nonnegative; 0 means fairness only, 2e-3 is the knee)

### Solver

- **outer approximation** (in `nash_exact`): log-concave objective → convex MINLP →
  supporting hyperplanes → optimality certificate
- **separator cuts** (in `solve_contiguous_nash`): hard contiguity via lazily generated
  separator inequalities
- **Both live inside one MINLP loop** but are *not* the same convergence theory — worth
  knowing before assuming one argument covers both

---

## Quick Reference: What Each Module Produces

| Module | Input | Output | Use case |
|--------|-------|--------|----------|
| `synth.py` | scenario name, seed, n_reps, n_zips | networkx graph G with attributes | Stress test, battery cases, example instances |
| `territory.py::nash_exact` | graph G, zip list | assignment S, gains g_a/g_b, bound gap | Exact fair division (6–7 iterations regardless of n) |
| `territory.py::solve` | graph G, zip list, criterion="nash" | assignment S, gains, metrics | Plug-and-play solver; exact by default |
| `districting.py::solve_contiguous_nash` | graph G, zip list, rho | assignment S, gains, perimeter, contiguity cost % | Fairness + geographic compactness |
| `territory.py::census` | graph G | list of components + per-pair metadata | Decompose the national problem into bilaterals |
| `territory.py::contestability` | graph G, assignment, bootstrap n | per-zip objection probability | Robustness under measurement error |

---

## Attribution

**Theory:** Nash bargaining (Rubinstein & Wolinsky 1985; Binmore, Rubinstein & Wolinsky
1986), discrete fair division (Caragiannis et al. 2019 on EF1), and optimal transport
(Warren 2025, `10.1007/s00030-025-01118-7`).

**Code:** Python 3.13 in `.venv`; see `requirements.txt`. HiGHS ships with `scipy>=1.11`
and is the default MILP backend.

---

## For Claude Code CLI

When starting a task on this project:

1. **Read the paper and this file.** `HANDOFF.md` no longer exists — everything it carried
   is here.
2. **Use `.venv/bin/python3` from the repo root.** System `python3` has no dependencies.
3. **The numeric anchor is `code/mkfig_zip50.py`.** Run it after any solver change: the
   printed numbers and the byte-identical PNGs are the regression test.
   `verify_algebra.py` is symbolic, standalone, and certifies the *superseded* model — it
   will not catch a baseline regression.
4. **Run relevant battery cases** (C9 for heavy tails, C5 for state borders) to validate
   structural changes — but never re-run the full battery casually; it overwrites primary
   artifacts.
5. **Test on the smallest instance that exhibits the failure mode** before running the
   full battery.
6. **Update this file** after discovering a new trap or resolving an open item.

**Kicking off the contiguity programme (fresh session, 2026-08-28 onward):**

7. Open `research/contiguity/PLAN.md` §0 and follow the kick-off sequence literally — U0a
   (anchors) comes *before* any solver edit. `contiguity-harness` exists (U0a–U1a committed
   2026-08-29); one worktree branch `wt/<unit>` per unit; main session merges. Fast tests:
   `.venv/bin/python3 battery/code/tests/run_all.py`; add `TD_SLOW=1` for the zip50 anchor
   whenever `districting/territory/synth` change. `tests/test_env.py` guards the solver stack
   (see the macOS `cbcbox` code-signing note in `requirements.txt`).
8. Every unit gets a brief = its PLAN.md section verbatim + files owned + files forbidden +
   acceptance command + "stop and report rather than improvise". Use plan mode /
   `AskUserQuestion` at each ★ (brief, plan, diff, stage gate). Models: PLAN.md Part E.
   Units with their own plan step: Part F. Serial-only files (main session, never a
   subagent): `requirements.txt`, `.gitignore`, `code/districting.py`, `code/territory.py`,
   `CLAUDE.md`, `research/contiguity/*.md`, and the `params` edit to `code/synth.py`.
9. Harness output goes to `battery/results/contiguity/<run_id>/`, never `battery/figures/`.
   New figures come from `code/gfx/` (PLAN.md Part D); old figure scripts stay frozen.
10. Decisions in PLAN.md's "Decisions taken" table are final; the remaining user calls are
    listed there and land at stage gates.

The codebase is mature and tested; most changes will be algorithmic (contiguity fixes) or
operational (real data loading) rather than model changes.
