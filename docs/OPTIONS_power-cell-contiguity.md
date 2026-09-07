# Contiguity for the power-cell stage-1 route — option register

**Opened:** 2026-09-06. **Last measured:** 2026-09-06 (options 1, 2 Route A, and 3).
**Branch:** `worktree-power-cell-contiguity` (unmerged).
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

**"Zero" always needs the diagram it is zero against** (§4). A labelling is a power diagram with
respect to one set of centres and weights. Rebuild the diagram from that labelling and a handful
of zips fall outside again — 16 of 3,704, measured 2026-09-06. So the requirement is met, but no
figure currently drawn can show it: they all recentroid first.

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
| snapped, equal split, best of 20 snap → recentroid iterates | 0 by construction | **2.1051%** | 110.766485 | **0.000283** |

Ceiling is `k·log(M_total/k) = 110.766768` on the 3,704 plotted zips. Diagram health at the
committed draw: 17 split zips (exactly the `k − 1` bound, so it is at the maximum) and max dual
violation 1.9e-18 relative, so the cells themselves are numerically sound and the 7.0% is a real
property of the draw rather than solver noise.

**Price of the zero-mismatch requirement, best route measured:** gap 0.000082 → 0.000283 nats,
spread 1.2902% → 2.1051%, at iteration 15 of Route A (§4). The single-shot snap's
0.000724 / 4.0041% is what one step costs, not what the route costs.

Five readings that a later session should not have to re-derive:

1. **Equal-split targets dominate own-masses targets** for *producing* a zero-mismatch draw —
   about half the spread and a third of the gap. Own-masses remains the right choice for
   *auditing* an existing draw, because it holds balance fixed district by district and so
   isolates compactness, which is the argument in `power_diagram_of_draw`'s docstring. The two
   targets answer different questions and should not be quoted interchangeably.
2. **The drift is cheap because it moves small zips.** 6.97% of zips carry only 1.66% of M,
   which is why the welfare cost lands in the fourth decimal place. Worst per-district mass
   change under the own-masses snap: D12 +4.25% of mean, D05 −3.33%.
3. **4.0041% is an upper bound, and iterating recovers about half of it.** The snap is
   single-shot, and snapping moves the M-weighted centroids. Iterating snap → recentroid reaches
   2.1051% at gap 0.000283 (§4), and finds no fixed point along the way. The other slack is
   untouched: this reuses one draw (seed 2, the winner of a 10-seed portfolio selected under the
   old objective).
4. **The split-zip floor is real.** The LP splits exactly `k − 1` = 17 zips, carrying 17.03% of a
   mean district at equal-split targets, largest single zip 3.699% of one. Rounding them is
   forced, so no zero-mismatch route should be expected near the committed draw's 1.2902%.
5. **On map contiguity the snapped labelling is dramatically better than the committed one**, and
   better than the atom route: one district at 55% and the other seventeen at 96–100% (§3).
6. **The largest-contiguous-piece fraction has an area denominator, and that denominator
   misreports dense metro districts.** D01's 55% is one rural ZIP's catchment, not a split
   territory (§3a, measured 2026-09-06). Measured on opportunity instead of area the snapped
   labelling's worst district is D17 at 92.72% and D01 sits at 99.86%, which reverses the
   ranking the area column gives. Quote both denominators, or the table says the opposite of
   what it means.

**Cross-route comparison, stated with its caveat.** The state-atom route sits at gap 0.093715
nats and 30.484% spread. A zero-mismatch power-cell draw at 0.000283 nats and 2.1051% spread is
better on both axes by a wide margin, and it is the only one of the two whose territory is
convex and whose dots agree with its fill. It is also ahead on the shared zip-catchment
contiguity measure once snapped (§3), which the committed draw was not. But the two gaps are
**not measured on the same
base**: the atom figure is against a component-wise `allocate_districts` ceiling of 110.883247
over the whole instance, while the power-cell figure is against `k·log(M/k) = 110.766768` over
the 3,704 plotted zips. The ranking is very unlikely to turn on that, given two orders of
magnitude, but it is not certified. Recompute both on one base before quoting the comparison to
a sponsor.

Reproduce with `~/.claude/jobs/0974a42b/tmp/snap_cost.py` (the first three rows) and
`~/.claude/jobs/4ce805a0/tmp/snap_fixpoint.py` / `snap_once.py` (the iteration, the split-zip
masses, and the snapped `draw.csv` the §3 map measurement consumes). All are job-temp and not
durable — fold them into `tools/` if this route is adopted. The split-zip masses need
`centers.power_weights`' `fractional` return, added 2026-09-06 on this branch and surfaced as
`power_diagram_of_draw`'s `split_zips`.

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

## 3. Option 1 — Largest-contiguous-piece fractions · **DONE 2026-09-06**

**Idea.** Run `tools/us_maps.py --regions-voronoi` on the power-cell draw, dissolving each
zip's Voronoi catchment by its committed district, and report each district's largest
contiguous piece as a share of its territory.

**Guarantee.** None — it is a measurement, not a method.

**Cost.** One command. The flag is already on `main`.

**Status.** Run on the committed power-cell draw, 2026-09-06. Largest contiguous piece, as a
share of the district's territory:

| | | | | | |
|---|---|---|---|---|---|
| D14 51% | D12 52% | D01 64% | D16 67% | D07 71% | D09 73% |
| D17 74% | D18 77% | D03 78% | D15 88% | D05 89% | D06 95% |
| D08 96% | D10 98% | D13 98% | D02 99% | D11 99% | D04 100% |

The same measurement on the CA5 state-atom draw gave D02 48%, D11 53%, D17 55%, D06 73%, with
the other fourteen districts at 98–100%.

**On the committed draw the result inverts the ranking §1 gives on gap and spread.** Nine of its
districts fall below 80% against the atom draw's four, and only seven reach 95% against the atom
draw's fourteen. A route that wins by two orders of magnitude on the Nash gap loses, on the
committed labelling, on the fragmentation a sponsor can see.

**The snapped labelling reverses that, and it is the one this route would ship.** Repeating the
measurement on the zero-mismatch labelling of §4 (single-shot snap, equal-split targets):

| | | | | | |
|---|---|---|---|---|---|
| D01 55% | D09 96% | D14 97% | D10 98% | D07 99% | D08 99% |
| D02 100% | D03 100% | D04 100% | D05 100% | D06 100% | D11 100% |
| D12 100% | D13 100% | D15 100% | D16 100% | D17 100% | D18 100% |

Twelve districts are a single piece, seventeen of eighteen are at 96% or better, and D01 at 55%
is the lone outlier. Shared border segments fall from 1,591 to 636, which is the same fact seen
from the other side: the snapped labelling is a far simpler object on the ground.

**So the zero-mismatch requirement pays for itself twice.** It was adopted to remove the stray
dots, and it removes most of the fragmentation as well. Ranked by worst-case fragmentation the
order is: snapped power-cell (one district at 55%, the rest 96–100%), then the CA5 atom draw
(four below 80%), then the committed power-cell draw (nine below 80%). That ordering agrees with
the gap and spread ordering rather than contradicting it, which the committed-draw numbers alone
would have suggested.

**D01 is explained in §3a**, and the explanation is that the 55% is an artefact of the area
denominator rather than a fragmented district.

**Read all of this with the rendering in mind, because the two routes ship different maps.** The
zip-catchment rendering is the only one that applies to both, which is what makes it
apples-to-apples, but it is not what this route ships. The power-cell route's own map is
`--regions`, the power diagram, and §0's theorem says each of those cells is a convex polygon:
the shipped territory has no fragments at all. The fractions above measure the *labelling*
scattered across catchments, not the territory the business is shown. For the atom route the
catchment rendering is the map, so its fractions are the delivered object.

That difference is the whole reason the comparison is hard, and this file does not resolve it.
What the numbers do settle: **which labelling is measured decides the answer.** On the committed
labelling the power-cell route is behind the atoms on the shared zip-catchment measure; on the
snapped labelling it is ahead of them, and ahead by more than it is behind. Since the
zero-mismatch requirement means the snapped labelling is what ships, the honest summary is that
the power-cell route leads on every axis measured so far — welfare, balance, convex territory,
and catchment fragmentation — with D01 the one blemish.

**Verdict.** Closed, on both the committed and the snapped labelling, and D01 is now closed too
(§3a).

---

## 3a. Why D01 reads 55% · **DONE 2026-09-06**

**The answer: D01 is not fragmented. Its second "part" is a single rural ZIP.** Under the
snapped labelling D01 dissolves into exactly **two** parts, and they divide as follows.

| part | share of D01's area | ZIPs | M | share of D01's M |
|---|---|---|---|---|
| 0 — the NY/NJ core | **55.44%** | 148 (107 NY, 41 NJ) | 471.88 | **99.86%** |
| 1 — ZIP `18337` | **44.56%** | 1 (PA) | 0.68 | **0.14%** |

`18337` is Milford, Pike County, Pennsylvania, in the Poconos, about 85 km north-west of the
core's centroid. It is rural, so its Voronoi catchment is enormous: **1,555,699,398 map units,
which is 0.0199% of the whole clip polygon, the 80.5th percentile of all 3,704 catchments, and
204× the median catchment of D01's other 148 ZIPs (7,636,382).** D01's entire dissolved
territory is 3,491,143,536 units, so that one catchment is 44.56% of it by arithmetic alone. The
"largest piece is 55%" is the ratio of a 148-ZIP metropolitan core to one empty rural cell, and
nothing about it says the territory is in pieces.

**Measured on opportunity rather than area the picture inverts.** Charging each ZIP to the part
its own catchment overlaps most, the largest part's share of each district's M under the snap is:

| | | | | |
|---|---|---|---|---|
| D17 92.72% | D10 95.45% | D14 99.74% | **D01 99.86%** | D08 99.90% |
| the other thirteen districts 100.00% | | | | |

D01 is fourth from the top on this denominator, and the two genuinely split districts are D17 and
D10 — which the area column records at 100% and 98%. The two measures do not merely differ in
degree; they disagree about which districts are the problem. On zip count the same reading holds:
D01 99.3%, worst D10 97.5%.

**The mechanism, in one sentence.** D01's power cell is a thin convex wedge that runs from the
New York City core out into rural north-west New Jersey and Pike County; the snap puts the one
ZIP at the far end of the wedge into D01 while its geographic neighbours go elsewhere
(`18428` at 22.1 km to D05, `07860` at 30.7 km and `07871` at 37.3 km to D12, `10990` at 42.4 km
to D04), so the dissolve leaves it an island. Every district with a small dense core is exposed
to this; D01 is the one where it happened.

**Ruled out, each by measurement.**

- **The 44 excluded ZIPs are not involved.** Two of them (`33394`, `60670`) do sit in D01 on the
  committed labelling, but they are dropped before the Voronoi diagram is built, so they
  contribute no ground and cannot produce a part. D01 has 149 plotted ZIPs under the snap.
- **Sliver size is not the cause, and the refutation is stronger than §3 knew.** D01's dissolved
  territory (3,491,143,536) is *larger* than D14's (2,894,136,494), and D14 reads 97%. Small area
  is a necessary condition for the artefact, not a sufficient one; what matters is the ratio of
  the outlying catchment to the district total.
- **The three-centre hypothesis is real geometry but the wrong cause.** D01's core is indeed
  carved by two neighbours — 22 adjacent D04 catchments and 17 D12 — and the `18337` island is
  ringed by D04 (3), D12 (2) and D05 (1). But D12 is a single piece at 100% and 148 of D01's 149
  ZIPs are a single piece, so the three-way carve of the NY/NJ agglomeration explains why D01's
  cell is thin, not why the measure reports 55%.
- **Rendering, not labelling.** D01's power cell is **one connected convex polygon** carrying
  0.0579% of the power diagram's area. The territory the business would be shown (`--regions`)
  has no fragment at all. The 55% is a property of the zip-catchment dissolve only.
- **No iterate needed.** The mechanism is one ZIP at the far end of one cell, visible in the
  single-shot snap, so iteration 15's labelling did not have to be regenerated to answer this.
  Register item 6 stands on its own merits, not on D01's.

**The committed labelling makes the denominator problem worse, and corrects §3's table.** On the
committed draw D01 has 12 parts and §3 records "64%". That 64% is *also* a single rural ZIP —
one part, one ZIP, **0.00%** of D01's M — while D01's actual 137-ZIP core carrying 99.35% of its
opportunity is only **16.90%** of the area. So the committed figure quoted in §3 is not measuring
the core at all. On mass the committed D01 is 99.35%, and the committed draw's worst district on
that denominator is D09 at 90.03%, not D14 (98.20%) or D12 (95.34%) as the area column suggests.

**What would fix the 55%, and what it costs.** Moving `18337` alone out of D01 does it, and the
measured cost is close to nothing: to **D05** or to **D12**, D01 becomes **1 part at 100%** and
the recipient stays 1 part at 100%. The mass spread is unchanged at 4.0041% to four decimals, and
`Σ log M` moves 110.766044 → 110.766035, so the gap to the 110.766768 ceiling widens
0.000724 → 0.000733, by **9e-6 nats**. The real price is the one that matters to the stakeholder
requirement: it puts **one ZIP of 3,704 outside its own power cell**, which is a departure from
zero. Given that the shipped `--regions` map draws D01 as a single convex polygon either way,
paying a mismatched dot to improve a number that is measuring the wrong thing is a bad trade. The
recommendation is to **report the mass denominator beside the area one and leave the draw alone**.

**Reproduce.** `tools/measure/district_pieces.py <draw.csv> <instance> --detail D01` gives the
three-denominator table and D01's parts for any labelling; `tests/test_district_pieces.py` covers
the statistic. The snapped labelling reproduces §1's spread 4.0041% and `Σ log M` 110.766044
exactly, which is the cross-check that this measurement and §1's are on the same object.

---

## 4. Option 2 — Snap to the diagram · **the cheapest route to zero mismatches**

**Idea.** Ship `power_labels(xy, centers, weights)` as the draw instead of the polished labels.
Zero mismatches by construction, because the labelling *is* the diagram.

**Guarantee.** Exact zero mismatch, and convex territory. No guarantee on balance beyond what
the measurement shows.

**Read the guarantee precisely — it is relative to one diagram.** The snapped labelling has zero
zips outside their own cell *with respect to the diagram that produced it*, the one built at the
committed draw's centroids. It is not zero against a diagram rebuilt from the snapped labels.
Measured 2026-09-06 with `us_maps.py --regions` on the snapped `draw.csv`, which recomputes
centroids from whatever draw it is handed and so takes a recentroid step before drawing:
**16 of 3,704 zips (0.4%) lie outside their own cell, against 258 (7.0%) on the committed
draw**, and the split-zip count falls from 17 to 10. The 16 are the same non-self-consistency
that leaves the iteration below without a fixed point.

The practical consequence is a reporting one. Every power-diagram figure recomputes the diagram
from its input, so **no existing figure can display the zero**; it always reports the next
iterate's mismatch. A figure that shows the guarantee has to hold centres and weights fixed and
colour the dots by the labelling those weights produced. That figure does not exist yet, and
until it does, "zero mismatched dots" must be quoted with the diagram it is zero against.

**Two variants, and they differ.**

- **Route A — snap post-hoc.** Take the committed draw's centers, get weights from the
  transportation duals, relabel. Measured in §1. The single-shot snap is not self-consistent:
  relabelling moves the M-weighted centroids, so this file expected the object wanted to be a
  **fixed point of snap → recentroid → snap**. Iterated 2026-09-06, and there is no such fixed
  point — see the iteration measurement below.
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
nats. Route A iterated 2026-09-06, 20 iterations, reported below. Route B unmeasured.

**Route A iterated — snap → recentroid at equal-split targets, 20 iterations.** Selected values:

| iter | zips moved | spread | Σ log M | gap |
|---|---|---|---|---|
| 1 (single-shot) | 266 | 4.0041% | 110.766044 | 0.000724 |
| 2 | 15 | 2.6652% | 110.766297 | 0.000471 |
| 3 | 8 | 2.5904% | 110.766237 | 0.000531 |
| 5 | 8 | 5.6051% | 110.765497 | 0.001271 |
| 8 | 9 | 2.5460% | 110.766392 | 0.000376 |
| **15** | 12 | **2.1051%** | **110.766485** | **0.000283** |
| 20 | 12 | 5.6051% | 110.765553 | 0.001215 |

**There is no fixed point, and the iteration is not a descent.** After the first step, which
moves 266 zips, every later step moves 5 to 15 and the objective goes both ways: iterations 4,
5, 11, 13, 18 and 20 are all *worse* than their predecessor. Twenty iterations produced no exact
repeat, so it is not a short cycle either — it wanders a band of roughly spread 2.1–5.6% and gap
0.00028–0.00128. Open question 1 in §10 asked whether the fixed point exists and is unique; on
this instance the iteration does not reach one, so the question as posed does not decide
anything.

**Read it as a search, not as a convergence.** Every iterate is a power diagram, so every one of
them has zero mismatched zips and convex cells by construction. Feasibility is therefore not at
stake in choosing among them, and taking the best iterate is legitimate rather than
cherry-picking. Best of 20 is **iteration 15 at spread 2.1051% and gap 0.000283**, which beats
the single-shot on both axes — spread nearly halved and gap cut to 39% of it. That is the number
Route A can claim.

**What this costs Route B.** Route B was justified as removing the polish so balance is closed
with weights. Route A's best iterate already reaches 2.1051%, against the split-zip floor
argument below, so the room Route B has left to win is small. Measure Route B against
iteration 15, not against the 4.0041% single-shot, or it will look better than it is.

**Shared hard limit, applying to both variants.** With indivisible zips, no power diagram hits
exact equal masses in general. The LP hits them only fractionally, on at most `k − 1` = 17 split
zips, and rounding those is irreducible. That residual, not the 258, sets the achievable spread
floor.

**Measured 2026-09-06, at the equal-split targets.** The LP splits exactly 17 zips, so it sits
at the `k − 1` bound. Their masses total **80.13 = 0.9463% of M, which is 17.03% of a mean
district**. The largest is `20814` at **3.699% of a mean district**, then `60462` 2.067%,
`85254` 1.620%, `94104` 1.494%, `91786` 1.351%. At the own-masses targets the count is again
exactly 17, and the mass is larger: 103.9 = 1.2266% of M = 22.08% of a mean district, largest
`19067` at 4.108%. Both target choices sit at the bound, so the count is structural rather than
a property of either question.

That answers the question the previous paragraph asked, and the answer is not the reassuring
one. A single split zip carries up to 3.7% of a district, and the seventeen together carry 17%
of one, so rounding them can move max-minus-min by several percent on its own. The single-shot
snapped spread of 4.0041% is therefore the same order as this residual, and the iteration
measured above reaches 2.1051% without ever going far under it. The floor is a real constraint
on every zero-mismatch route, and no route here should be expected to return to the committed
draw's 1.2902%.

**Verdict.** Primary route, and Route A is now measured: spread 2.1051% at gap 0.000283, with
zero mismatches and near-solid territory (§3). That is the standing offer for the zero-mismatch
requirement. Route B is worth building only if it beats it, and the split-zip floor says the
room left is small.

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

Items 1 to 3 were done on 2026-09-06 and are struck through. What remains, in order:

1. ~~Option 1 — `--regions-voronoi` on the power-cell draw.~~ Done, §3, on the committed draw
   and on the snapped one.
2. ~~Option 2 Route A, iterated.~~ Done, §4. There is no fixed point; best of 20 iterates is
   spread 2.1051%, gap 0.000283.
3. ~~Measure the 17 split zips' masses.~~ Done, §4. 17.03% of a mean district at equal-split
   targets.
4. **Build the fixed-diagram figure.** Hold centres and weights fixed and colour the dots by the
   labelling those weights produced, so the zero-mismatch guarantee can actually be shown. Today
   every rendering recentroids and reports 16 instead. This is the figure a sponsor review needs.
5. ~~Explain D01.~~ Done, §3a. It is not fragmented: 148 of its 149 ZIPs and 99.86% of its M are
   one piece, and the second "part" is the single rural ZIP `18337`, whose catchment is 44.56% of
   D01's area and 0.14% of its opportunity. The 55% is an area-denominator artefact. What this
   opens instead: **the §3 table should carry the mass denominator beside the area one**, since
   on mass the snapped worst case is D17 at 92.72%, not D01.
6. **Iterate Route A properly and keep the best iterate as an artifact.** The 2026-09-06 run
   wrote no per-iteration draw, so iteration 15's labelling was not saved and its map contiguity
   is unmeasured. Re-run writing a `draw.csv` per iterate, then run `--regions-voronoi` on the
   best one. Each iteration is one transportation LP, a few minutes.
7. **Option 2 Route B** — remove the polish from `centers.draw`, close balance with weights, and
   re-run the portfolio scoring zero-mismatch draws. Judge it against iteration 15's
   2.1051% / 0.000283, not against the single-shot.
8. Recompute the atom and power-cell gaps on one common base before any sponsor comparison.

---

## 10. Open questions this file does not settle

1. ~~Whether a fixed point of snap → recentroid exists and is unique.~~ Settled negatively on
   this instance, 2026-09-06: 20 iterations reach no fixed point and no exact repeat, and the
   objective is non-monotone. What replaces it: whether the band the iteration wanders has a
   floor, and whether a longer run beats iteration 15's 2.1051%.
2. ~~The mass of the 17 split zips.~~ Measured, §4: 17.03% of a mean district at equal-split
   targets, largest single zip 3.699%. The floor is not small.
3. ~~Why D01 stays fragmented at 55% under the snap.~~ Settled 2026-09-06, §3a: it does not stay
   fragmented. The question was mis-posed because the statistic it rests on has an area
   denominator, and D01 is a dense metro core plus one rural ZIP whose empty catchment is 44.56%
   of the district's area and 0.14% of its opportunity. What replaces it: **whether
   `--regions-voronoi` should report the mass-weighted largest piece instead of, or beside, the
   area one.** The two disagree about which districts are fragmented on both labellings — snapped,
   area says D01 55% while mass says D17 92.72%; committed, area's "D01 64%" is a part carrying
   0.00% of D01's M. `tools/measure/district_pieces.py` computes all three denominators; wiring
   it into `us_maps.py`'s `report` line is a small change nobody has made.
4. Whether the 44 dropped zips (41 gazetteer-absent, placed by state; 3 non-CONUS) should be in
   the objective at all. They are 0.65% of M and currently sit outside every measurement above.
5. Whether zero mismatch should be enforced at every seed in the portfolio, or only at the
   winner. Enforcing it at every seed changes what the portfolio is selecting over.
