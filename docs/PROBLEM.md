# The national channel: the problem

**Opened:** 2026-08-31; renamed and reorganised 2026-09-07 (see `git log --follow` for the
history, and the commit "Step 2: …" for what was folded in from where). This file owns
the settled facts about the *business problem*. `docs/MODEL.md` owns the settled facts about the
model, `STATE.md` `## Facts` owns every measured number, and `docs/CODE_MAP.md` says how to run
anything. Nothing here is a resume point; `STATE.md` `## Now` is.

The business is standing up a **new "national" channel**, carving the two largest firms out of
the financial-institutions and wirehouse channels, with territories targeted at roughly equal
opportunity — about **$1B each**.

That is not the two-player merger problem, and it is not quite the N-way problem either. It is
**greenfield balanced districting**. Decided: **two-stage**, with the $1B as an emergent target
rather than a constraint.

The original problem was bilateral: two sales forces merge, a national *census* intersects the
two legacy representative maps and decomposes the country into contested components, each with
one A-rep and one B-rep. A greenfield channel has no such overlap, so what was many independent
30–500 zip subproblems becomes **one k-way partition of the whole footprint**, and what is to be
balanced is *opportunity*, a quantity attached to the territory and not to any representative.

## 1. Nash welfare on a common measure *is* equal-size districting

Every zip lands in exactly one district, so `Σ_j M_j` is the same for every partition.
Maximising `Σ_j log M_j` subject to a fixed sum equalises the terms (`∂/∂M_j → 1/M_j = μ`).
So the Nash objective already *is* the balance objective — the same optimum, not an
approximation of it. Set `k = total_opportunity / $1B` and balance falls out.

This is why the target does not need to be a hard band. It also sidesteps **trap 2**:
explicitly minimising a spread can leave everyone worse off, whereas Nash reaches the same
balance as the maximiser of a concave objective and stays Pareto efficient. The battery's
own equalisation finding (an unconstrained equaliser reaching KS gap 5.2e-8 but
Pareto-dominated by Nash) is the same phenomenon from the other side.

`test_channel.py::test_nash_welfare_is_equal_size_districting` brute-forces every contiguous
3-way cut of P₁₂ and confirms the argmax is the balanced one.

The formal statement, its proof, and the published names for it (Schur-concavity, Pigou–Dalton,
proportional fairness) are in `docs/MODEL.md` §7.

## 2. The welfare decomposition

```
Σ_i g_i = Σ_z [ λ·M_z + c2·T_z + c_free·S_free ]     ← partition-invariant
        + Σ_z (c1 − c2)·S_owner(z)(z)                ← maximised by keeping zips with their incumbent
```

The objective splits into **balance the territories** and **where there is slack, leave
business with the rep who already has it**.

**Correction, 2026-09-01 (Gromov review R1), re-measured on v2.** `ceiling.py` had hard-coded
`SATURATION = 0.05`, and the reading "a balanced map with a modest continuity tilt" was written
on that assumption. It is wrong. Aggregate saturation is **29.588 %** on the live v2 instance
(41.9 % as first measured on v1), so the books move the map a lot.

**The consequence, and it is the load-bearing one.** The claim that the two-stage scheme is
*derived* rather than assumed fails on the real instance. The incumbency premium window is
**0.890 nats exact** on the delivered k=18 draw against `D(g) = 0.148` nats, so the ordering
inverts by a factor of 6: incumbency, not balance, is the larger term. The premium itself is
**0.72–0.78 nats and not soft** (146–155× the 5e-3 tier-2 floor, with no `δ*` at which it
vanishes). The two-stage scheme therefore survives as a **business constraint** — *territories
shall be opportunity-balanced* — and not as a consequence derived from the objective. Balance
still dominates asymptotically (log blows up as a territory starves), but not on the region the
programme operates in.

Every number in this section is sourced from `STATE.md` `## Facts`; the algebra is
`docs/MODEL.md` §7.

## 3. Two stages

| stage | problem | status |
|---|---|---|
| **1 — draw** | k balanced compact districts on opportunity alone | **the hard part**; heuristic, certified |
| **2 — match** | assign retained reps to districts | **built** — `td/channel.py`, exact |

Stage 2 is a max-weight matching on **log** weights: `g_ij = Σ_{z∈A_j} u_i(z)`, maximise
`Σ_i log g_{i,σ(i)}` by the Hungarian algorithm. Same objective as stage 1, O(n³), exact.
Nash rather than utilitarian matching matters — a utilitarian match will hand one rep a
district holding almost none of their book if the total looks good.

**Rectangular matching selects the retained set.** With more reps than districts the unmatched
reps are the ones not retained, and the choice is well-posed precisely because k is fixed.
On the live instance 114 representatives face 18 districts, so 96 go unmatched and the matching
*is* the retention decision.

**The 6.3:1 ratio is a business reading, not a mathematical one.** 114 representatives against
18 territories only makes sense if the channel is a *specialist carve-out* staffed by a handful
of senior wholesalers while the remaining representatives keep covering the other manufacturers
in the existing FI/wirehouse channel — that is, stage 2's "unmatched" reps are *not selected for
this channel*, not released. If that reading is wrong, stage 2's framing needs revisiting.

**Known cost of the split.** Stage 1 cannot see relationships, so a good matching may not be
available at stage 2 — the same objection `CLAUDE.md` raises to "decouple fairness from
compactness": it relocates the difficulty rather than removing it. Mitigation, cheap because
stage 2 is milliseconds: generate a *portfolio* of stage-1 draws and keep the one that staffs
best (`channel.score_draws`). Not the joint optimum, and it must not be reported as one; it is
a cheap lower bound on it, and the spread across the portfolio diagnoses what the split costs.

## 4. What this does to the data requirement

**Stage 1 needs almost none of the confidential data** — only `(zip, M)` and public
coordinates. Opportunity is plausibly third-party market sizing.

**Stage 2 can run entirely on the work machine**, since it needs only the returned district
map plus internal books.

The descaled-export route stays correct and is still the right channel for anything that does
need to travel (`docs/DATA.md`), but the national-channel problem needs a fraction of it.

## 5. Adjacency contiguity is not available on this footprint

Stage 1 destroys the census decomposition. The bilateral pair structure came from *overlap
between two legacy rep maps*; a greenfield channel has no such structure, so stage 1 is one
k-way partition over the whole footprint.

**And the sold-zip graph is shattered.** On v2 the Rook adjacency graph restricted to sold zips
has **862 components over 3,748 zips, 516 of them singletons**; the largest holds 13.5 % of
opportunity and 47.6 % of opportunity sits in components under 1 % each. (v1: 547 components
over 1,229 zips.) A contiguous k-partition of that graph does not exist for any k below several
hundred, so at k = 18 the constraint is not binding-but-hard, it is **infeasible**. Contracting
to states does not rescue it either: the instance graph gives only 10 edges over 42 components,
which is why a state model must import the TIGER state rook graph (49 nodes, 107 edges) that
`td/geo.py::state_rook` builds.

**Decision, 2026-09-01: drop adjacency and keep the geometric requirement contiguity was
standing in for — compactness.** Stage 1 becomes center-based balanced assignment on
equal-area planar coordinates. Restoring contiguity would mean re-exporting the unsold "glue"
zips, most of the country, and districting an object the channel does not sell in.

**Symmetry is the hazard the reformulation removes.** k anonymous districts are interchangeable
labels, which costs branch-and-bound its pruning. The centre-based (Hess) formulation — assign
each zip to one of k *centres* — breaks the symmetry by construction, and is what the districting
literature uses.

**Correction, 2026-09-01 (literature reconnaissance, A2).** This file and `CLAUDE.md` used to
say that ~1,500 units is the published state of the art for certified districting, citing
Validi, Buchanan & Lykhovyd. That is stale by roughly two orders of magnitude: the same group
now reports provably optimal plans for **all** US congressional and legislative instances
(whole-counties objective, combinatorial Benders; Shahmizad & Buchanan, MPC in revision) and
runs experiments at **175,000 vertices** with inexact contiguity (Jolly & Buchanan 2026). Our
3,748 zips are not near any frontier. The binding difficulty is the log objective and the
shattered graph, not the unit count.

## 6. The instance

**Every number describing the instance lives in `STATE.md` `## Facts`**, which carries the v1
and v2 columns side by side. The live instance is v2, `instance_descaled_v2.json.gz`: 3,748
zips, 114 reps, k = 18 at $1B. The v1 sizing that this file used to carry (2,232 then 1,229
zips, 72 reps, ≈$6.2B, k ≈ 6, "four islands") is superseded on every line and is kept only in
`## Facts` as a regression column.

Two structural readings survive the re-sizing and are worth stating separately from the numbers.

**The footprint is national, not four islands.** The 2026-08-31 reading of west coast / east
coast / Texas / Florida with an uncovered midwest was corrected by the user on 2026-09-01: about
18 % of opportunity is spread across the "uncovered" midwest and rest. There is no regional
decomposition to solve along.

**Granularity is benign.** The largest single zip is about 1 % of total opportunity, and the
transportation relaxation splits at most `k − 1` zips (17 at k = 18, and the bound binds
exactly). Those 17 carry 17.03 % of one mean district at equal-split targets. So the whole
indivisibility problem is under a fifth of one district wide, and near-perfect balance is
geometrically reachable. `docs/MODEL.md` §8 turns that into a certificate rather than leaving
it as an intuition.

## 7. Balance has a geometric ceiling — compute it first

`channel.allocate_districts(component_M, k)` maximises `Σ_c k_c·log(M_c/k_c)` over integer
allocations with `k_c ≥ 1`. Within a component the best conceivable outcome is `k_c` equal
districts, so this is an **upper bound on any real partition** — a free dual bound for
stage 1, available before a solver runs (`test_ceiling_is_an_upper_bound_on_any_real_partition`).

At k = 18 on a single national component the ceiling reduces to `k·log(M/k)`, and the delivered
draw sits 0.000082 nats under it. The certificate, and the warning that two ceilings on
different bases are in circulation, are in `docs/MODEL.md` §10.

Three things follow, and they are the reason the ceiling is computed before any solver runs.

1. **A hard ±10 % band around $1B may not be reachable**, because a region small enough to get
   exactly one district cannot be subdivided. On the v1 four-island reading the friendliest
   split topped out near 20 % spread; on the v2 national footprint the ceiling is far tighter,
   but the argument is the same and the ceiling is what settles it.
2. **The best `k` depends entirely on the regional composition.** `k` is a balance decision,
   not just a headcount.
3. **It is a few numbers of work**, with no solver and no confidential per-zip data.

The illustrative $6.2B ceiling table this section used to carry was v1 and is superseded; see
`docs/foundations/FRAME.md`, whose header supersedes it explicitly, and `STATE.md` `## Facts`.

A caveat that still applies: `allocate_districts` returns `ceiling_spread_rel` at the
dual-bound budget and `min_spread_rel` at the spread floor, with `spread_optima_agree` saying
whether they coincide. The objective-optimal budget is not always the *most even* budget, so the
two numbers answer different questions and must not be quoted interchangeably.

## 8. The zero-mismatch requirement

**Set by the stakeholder on 2026-09-06.** The territory map the business is shown draws each
district as a region and each zip as a dot. A dot coloured for one district sitting on another
district's ground is not defensible in front of the sponsor, so **that count must be zero**: the
shipped labelling must *be* a power diagram, not merely be near one.

This is a requirement on the deliverable, not on the mathematics. Region contiguity in the plane
is already free — the cells of a balanced least-squares assignment are convex polygons by
construction — and zip-set contiguity on the adjacency graph is infeasible (§5). The live
question is the gap between the two: how far the shipped labelling drifts off the diagram it
implies.

**"Zero" always needs the diagram it is zero against.** A labelling is a power diagram with
respect to one set of centres and weights; rebuild the diagram from that labelling and a handful
of zips fall outside again (15 or 16 of 3,704, measured 2026-09-06). Since 2026-09-06 one figure
displays the guarantee honestly: `tools/us_maps.py --regions-fixed` holds the centres and
weights instead of recentroiding. Every other rendering recentroids, so a zero read off one of
those is not this zero.

The routes to zero, their costs and their verdicts are `docs/MODEL.md` §11; the measurements are
`STATE.md` `## Facts`.

## 9. State borders

**Decided 2026-09-06:** districts snap to state lines where they can, under a mass-deviation cap
of 10 %, because visual contiguity on state boundaries is what the sponsor reads as a coherent
territory. The build, the results and the recommended cell are in `docs/BORDERS_PLAN.md` and
`docs/BORDERS_RESULTS.md`.
