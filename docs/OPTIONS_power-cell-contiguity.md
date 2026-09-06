# Contiguity for the power-cell stage-1 route — option register

**Opened:** 2026-09-06. **Branch:** `worktree-power-cell-contiguity` (unmerged).
**Companions:** `docs/CODE_MAP.md` "Two stages" (which file owns what), `docs/CHANNEL.md` §3
(the two stages) and §5 (the open risk), `research/contiguity/OPTIONS.md` on
`origin/worktree-contiguity-research` (the 2026-08-28 two-agent option brief this one
supersedes for the center-based route).

This file is the durable register of routes for one question. It is not a resume point:
`STATE.md` names which option is live, and this file holds all of them with their evidence.
Each session appends its measurements to the option it touched rather than rewriting the list.

---

## 0. The question, and why it has two answers

For the power-cell route, "is the territory contiguous" resolves into two different questions
that give opposite answers.

**Region contiguity in the plane is already a theorem.** `centers.power_weights` solves the
balanced-assignment transportation LP for its mass-balance duals. Complementary slackness says
an optimal assignment sends zip `z` to the district minimising `d²(z, c_j) − β_j`, which is
exactly a power (Laguerre) diagram with weights `w_j = β_j` — the Aurenhammer–Hoffmann–Aronov
constrained least-squares assignment. Every bisector is a straight line, so every cell is an
intersection of half-planes, and therefore a convex polygon. The territory map the business is
shown (`us_maps.py --regions`) is `k` convex regions with exact straight borders. There is
nothing to enforce here.

**Zip-set contiguity on the adjacency graph is not guaranteed, and on v2 it is barely
well-posed.** The v2 zip graph has 862 components over 3,748 zips, which is why the
center-based route dropped the constraint in the first place (`docs/CODE_MAP.md`).

So the live question is neither of those. It is the gap between the two: **how far the shipped
labelling drifts off the diagram it implies.** A zip that drifts appears on the territory map
as a dot coloured for one district sitting on another district's ground.

**Stakeholder requirement, set 2026-09-06: that count must be zero.** A dot in another
district's territory is not defensible in front of the sponsor, so the shipped labelling must
*be* a power diagram, not merely be near one. Options 2 and 3 below are the routes that deliver
this; options 4 and 5 answer the different, harder graph question; options 0 and 1 are the
measurements that rank them.

**Three sources of drift.** `improve()` moves zips after the LP to repair the balance that
integral rounding cost. The LP's basic solution splits at most `k − 1` zips, each rounded to one
side. And `power_weights` returns both `labels` (the true power cells) and `lp_labels`, which
need not agree.

---

## 1. The measurement record

All numbers below are on the live power-cell draw
`battery/results/draw_k18_v2_20260904/k18/draw.csv`, instance `instance_descaled_v2.json.gz`,
k = 18, measured 2026-09-06. That run has `scenario = {'fix': {}, 'anchor': {}}` and
`hand_drawn = []`, so no zip was pinned and every discrepancy comes from the polish and the
rounding. The map drops 44 of 3,748 zips (41 absent from the 2020 gazetteer, 3 non-CONUS),
leaving 3,704 with total M 8,468.3.

| labelling | zips outside their own cell | spread | Σ log M | gap to ceiling |
|---|---|---|---|---|
| committed draw | 258 (6.97% of zips, **1.66% of M**) | 1.2902% | 110.766686 | **0.000082** |
| snapped, targets = draw's own masses | 0 by construction | 7.6346% | 110.764808 | 0.001959 |
| snapped, targets = exactly-equal split | 0 by construction | **4.0041%** | 110.766044 | **0.000724** |

Ceiling is `k·log(M_total/k) = 110.766768` on the 3,704 plotted zips. Diagram health at the
committed draw: 17 split zips (exactly the `k − 1` bound, so it is at the maximum) and max dual
violation 1.9e-18 relative, so the cells themselves are numerically sound and the 7.0% is a real
property of the draw rather than solver noise.

**Price of the zero-mismatch requirement, best route measured:** gap 0.000082 → 0.000724 nats,
spread 1.2902% → 4.0041%.

Three readings that a later session should not have to re-derive:

1. **Equal-split targets dominate own-masses targets** for *producing* a zero-mismatch draw —
   about half the spread and a third of the gap. Own-masses remains the right choice for
   *auditing* an existing draw, because it holds balance fixed district by district and so
   isolates compactness, which is the argument in `power_diagram_of_draw`'s docstring. The two
   targets answer different questions and should not be quoted interchangeably.
2. **The drift is cheap because it moves small zips.** 6.97% of zips carry only 1.66% of M,
   which is why the welfare cost lands in the fourth decimal place. Worst per-district mass
   change under the own-masses snap: D12 +4.25% of mean, D05 −3.33%.
3. **4.0041% is an upper bound, not the achievable spread.** The snap is single-shot, and
   snapping moves the M-weighted centroids, so the result is not a fixed point of
   snap → recentroid → snap. It also reuses one draw (seed 2, the winner of a 10-seed portfolio
   selected under the old objective). Both slacks are unexplored.

**Cross-route comparison, stated with its caveat.** The state-atom route sits at gap 0.093715
nats and 30.484% spread. A zero-mismatch power-cell draw at 0.000724 nats and 4.0041% spread is
better on both axes by a wide margin, and it is the only one of the two whose territory is
convex and whose dots agree with its fill. But the two gaps are **not measured on the same
base**: the atom figure is against a component-wise `allocate_districts` ceiling of 110.883247
over the whole instance, while the power-cell figure is against `k·log(M/k) = 110.766768` over
the 3,704 plotted zips. The ranking is very unlikely to turn on that, given two orders of
magnitude, but it is not certified. Recompute both on one base before quoting the comparison to
a sponsor.

Reproduce with `~/.claude/jobs/0974a42b/tmp/snap_cost.py` (job-temp, not durable — fold it into
`tools/` if this route is adopted).

---

## 2. Option 0 — Measure the drift · **DONE 2026-09-06**

**Idea.** Count the zips whose committed district is not the district whose power cell they sit
in.

**Cost.** None. This already exists as `power_diagram_of_draw`'s `outside`
(`tools/us_maps.py:1043`), and the count is printed in the figure subtitle and on the
`--report` line. No code needed.

**Status.** Measured: 258 of 3,704 zips (6.97% of zips, 1.66% of M), 17 split zips, max dual
violation 1.9e-18 relative. See §1.

**Verdict.** Closed. The number this route needed is now on the record.

---

## 3. Option 1 — Largest-contiguous-piece fractions · **OPEN, cheap, do next**

**Idea.** Run `tools/us_maps.py --regions-voronoi` on the power-cell draw, dissolving each
zip's Voronoi catchment by its committed district, and report each district's largest
contiguous piece as a share of its territory.

**Guarantee.** None — it is a measurement, not a method.

**Cost.** One command. The flag is already on `main`.

**Status.** Not run for the power-cell draw. The same measurement on the CA5 state-atom draw
gave D02 48%, D11 53%, D17 55%, D06 73%, with the other fourteen districts at 98–100%.

**Verdict.** Run it. This is the apples-to-apples number against the atom route, and it is the
one a sponsor will ask for.

---

## 4. Option 2 — Snap to the diagram · **the cheapest route to zero mismatches**

**Idea.** Ship `power_labels(xy, centers, weights)` as the draw instead of the polished labels.
Zero mismatches by construction, because the labelling *is* the diagram.

**Guarantee.** Exact zero mismatch, and convex territory. No guarantee on balance beyond what
the measurement shows.

**Two variants, and they differ.**

- **Route A — snap post-hoc.** Take the committed draw's centers, get weights from the
  transportation duals, relabel. Measured in §1. The single-shot snap is not self-consistent:
  relabelling moves the M-weighted centroids, so the object actually wanted is a **fixed point
  of snap → recentroid → snap**. Not yet iterated.
- **Route B — make the diagram the search space.** Delete the `improve()` polish from
  `centers.draw` and close the residual balance error by moving *weights* rather than
  individual zips. Weights are the diagram-preserving lever, since a larger `w_j` enlarges
  cell `j` at its neighbours' expense. Closer to the existing code than it sounds: the Lloyd
  loop's inner step already solves the LP whose duals are the weights, and `power_weights`
  already returns them. Only the polish breaks the diagram. Not yet built.

**Cost.** Route A is a relabelling plus an iteration loop, roughly half a day. Route B is a
change to `centers.draw`'s final step, one to two days, and it needs the existing draws to be
reproducible under a flag so the old numbers stay auditable.

**Status.** Route A measured single-shot at equal-split targets: spread 4.0041%, gap 0.000724
nats. Route A iterated and Route B both unmeasured.

**Shared hard limit, applying to both variants.** With indivisible zips, no power diagram hits
exact equal masses in general. The LP hits them only fractionally, on at most `k − 1` = 17 split
zips, and rounding those is irreducible. That residual, not the 258, sets the achievable spread
floor — and under a heavy-tailed M a single split zip can be a large metro, so the floor is not
guaranteed small. Measure the split zips' masses before promising a spread number.

**Verdict.** Primary route. Iterate Route A to a fixed point first, because it is cheap and it
bounds what Route B can win.

---

## 5. Option 3 — Constrain the polish · **fallback if Route B is too invasive**

**Idea.** Keep `improve()` but restrict its swaps to moves that leave each district a power
cell, which reduces to a sign check on `d²(z, c_j) − w_j`.

**Guarantee.** Exact zero mismatch, as option 2. Recovers less balance than the unconstrained
polish by construction.

**Cost.** About half a day, and it is a smaller diff than Route B.

**Status.** Not built, not measured.

**Verdict.** Hold. It is strictly dominated by Route B if Route B works, since Route B removes
the polish rather than constraining it. Keep it as the fallback if removing the polish costs
more balance than the measurements above suggest.

---

## 6. Option 4 — Hard graph contiguity, single tree · **expensive, and answers a different question**

**Idea.** Lazy minimal-separator cuts inside one SCIP branch-and-cut tree (PySCIPOpt), on the
center-based Hess formulation that `docs/CHANNEL.md` §5 already recommends for symmetry
breaking. This is Option A of `research/contiguity/OPTIONS.md`.

**Guarantee.** The only route with a certificate on the zip adjacency graph. Gap reported
natively by SCIP.

**Cost.** New dependency (`pyscipopt`), and days rather than hours. Two traps carry over from
`CLAUDE.md`: separator cuts must be **component-wise** — one root per district per component,
or the dual bound is unsound — and SCIP needs `misc/allow{strong,weak}dualreds` off for any
lazily separated model, `ga ≤ Σu·x` rather than `==`, and a gain lower bound from the incumbent.

**Status.** Not built.

**Verdict.** Do not start this to satisfy the zero-mismatch requirement — it does not address
it, and options 2 and 3 do. On v2's 862 components it also needs pre-aggregation to be
non-vacuous, at which point it has rebuilt the state-atom route. Revisit only if graph
contiguity itself becomes a stated requirement.

---

## 7. Option 5 — Make contiguity emergent via a travel term · **a modelling change, not a solver fix**

**Idea.** Replace the utility with `u_i(z) = c₁A_z + c₂B_z + λM_z − κ·d(z, p_i)`, where `d` is
the graph shortest-path distance to rep `i`'s base `p_i`. With κ dominating the data-term
variation, the free Nash solution is an additively weighted graph-Voronoi partition, whose cells
are connected by construction: any vertex on a shortest path from `z` to its centre inherits
`z`'s assignment. Contiguity becomes emergent, and κ replaces ρ with a behavioural reading.

**Guarantee.** Connectivity by construction at large κ. At moderate κ the constraint is still
needed.

**Cost.** High and mostly non-technical. It needs rep base locations, changes the settled
utility model, redistributes welfare, and needs distribution sign-off.

**Status.** Assessed 2026-08-28 and recorded in `research/contiguity/OPEN_QUESTIONS.md` §C as
the paper's N>2 / capacity route. Not pursued.

**Verdict.** Out of scope for this track. Listed so a later session does not rediscover it as
new.

---

## 8. Assessed and rejected

| Candidate | Reason |
|---|---|
| Shirabe one-shot flow formulation | Loses to cut-based branch-and-cut above a few hundred units; v2 has 3,748 zips. Still useful as a small-instance cross-check oracle, since it shares no cut-generation code. |
| OR-Tools CP-SAT | No lazy constraints at all, and no continuous log. |
| Zhang–Validi–Buchanan–Hicks linear-size planar formulation | Integral for pure connected partitioning, but the authors report it underperforms Hess once value and balance constraints are added, which is exactly our coupling. |
| METIS / multilevel coarsening | Heuristic, does not preserve connectivity on refinement, and smooths the heavy tail the map exists to show. |

---

## 9. Recommended order

1. **Option 1** — `--regions-voronoi` on the power-cell draw. One command, and it gives the
   number that ranks this route against the atoms.
2. **Option 2 Route A, iterated** — snap → recentroid to a fixed point, and report spread and
   Σ log M at the fixed point. Bounds what Route B can win.
3. **Measure the 17 split zips' masses.** This sets the achievable spread floor for every
   zero-mismatch route, and it is arithmetic.
4. **Option 2 Route B** — remove the polish from `centers.draw`, close balance with weights, and
   re-run the portfolio scoring zero-mismatch draws.
5. Recompute the atom and power-cell gaps on one common base before any sponsor comparison.

---

## 10. Open questions this file does not settle

1. Whether a fixed point of snap → recentroid exists and is unique. Nothing here proves it
   terminates.
2. The mass of the 17 split zips, hence whether the irreducible spread floor is small.
3. Whether the 44 dropped zips (41 gazetteer-absent, placed by state; 3 non-CONUS) should be in
   the objective at all. They are 0.65% of M and currently sit outside every measurement above.
4. Whether zero mismatch should be enforced at every seed in the portfolio, or only at the
   winner. Enforcing it at every seed changes what the portfolio is selecting over.
