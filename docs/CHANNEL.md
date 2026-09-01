# The national channel — the problem as it now stands

**Opened:** 2026-08-31 · **Split out of `NWAY.md` on 2026-08-31.** Companion files: `CHANNEL.md` (the problem), `MODEL.md` (the model), `DATA.md` (the export route).

Read this first. `MODEL.md` has the N-way maths this rests on; `DATA.md` has the export route.

---

## 0. Resume — read this first in a fresh session

**State on 2026-09-01 (latest): FINDINGS §9-A1 is done — the territory map is a power
diagram, and its duals are certificate 4.** 151 tests pass, 0 fail (was 131).

*What landed.* `centers.power_weights` / `power_labels` — the transportation LP re-solved for
its **duals**, which are the power-diagram weights; `cert_draw.cert_power_diagram` —
certificate 4, a lower bound on the compactness of every assignment to these centers, valid
without a solver in the trusted path (`O(nk)` arithmetic on `alpha`, `beta`);
`us_maps.power_cells` / `figure_power_regions` — `figures/district_regions.png` redrawn as 13
convex cells with exact straight borders, the old zip-catchment rendering kept behind
`--regions-voronoi`.

*What it says about the draw.* At the draw's own district masses the duals are exact (max
violation `3.5e-18` relative, 12 split zips = `k − 1`), and the draw sits **8.22% above the
bound** with **132 of 1,223 zips outside their own power cell**. So the committed draw is not
a power diagram of its centers, and the 8.22% independently reproduces the pinned-centers
MILP's 8.53% — the cross-check A1 predicted. The figure shows both: fill = the cells, dots =
the committed draw, and a dot whose colour differs from the ground under it is one of the 132.
The legend now carries share of M beside share of *area* (all 7.7% of M; 0.06% to 28.3% of the
map), which is the power diagram's whole content — equal opportunity is not equal ground.

*Two traps found in the doing, both recorded in FINDINGS §9-A1.* The bound must be taken at
the draw's **own masses**, not the equal split, or a near-balanced draw is infeasible for its
own test and the gap comes out negative. And the LP must use bounds `[0, inf)`, not `[0, 1]`:
same feasible set, but an explicit upper bound lets HiGHS park a reduced cost on it and the
duals come back infeasible by `-0.80` instead of `-5e-17`.

*What is next.* Unchanged, minus A1: A2/A3, then C1–C4. **The lexicographic decision is now
exactly the 132 dots** — adopt the cells, or keep the draw where it is.

**Earlier — 2026-09-01 (late night): literature reconnaissance complete — the niche is
unoccupied, and stage 1 turns out to be a published method.** Head `98f3c0e` (docs-only
since `b289f3a`; 131 tests as recorded at `f45bf89`, no code touched).

*What landed.* `acb34f9` — the research brief (`docs/RESEARCH_GUIDE.md`). `98f3c0e` — the
results of the overnight run (seven parallel verification-required sweeps, every citation
checked against a fetched source): `docs/RESEARCH_FINDINGS.md` (~130 entries organised by
guide §§1–7; headline findings §0; absence-claim ledger with search provenance §8;
prioritized reframings/roadmap §9) and `docs/RESEARCH_ADDITIONS.bib` (tiered BibTeX
candidates for `channel_note/references.bib`; three inferred DOIs flagged for
re-resolution).

*What it means (FINDINGS §0, in order of consequence).* (1) Stage 1 is a published named
method — Aurenhammer–Hoffmann–Aronov constrained least-squares assignment / semi-discrete
OT / weight-balanced k-means / capacitated Lloyd for centroidal power diagrams / the Hess
model — with an inheritable convergence theorem (Bourne–Roper 2015) and a redistricting
precedent (Cohen-Addad–Klein–Young 2018). (2) **`figures/district_regions.png` should be a
power diagram, not Voronoi** — the transportation-LP mass-balance duals *are* the cell
weights, giving a free exact assignment certificate at fixed centers that supersedes the
pinned-centers MILP (flagged independently by three sweeps). (3) The MNW-equals-balance
proposition is Schur-concavity (Marshall–Olkin); its integer form is NP-hard balanced
partitioning; the ≤ k−1 split lemma is Brieden–Gritzmann–Klemm 2017 Lemma 4 — cite, don't
prove. (4) The "~1,500 units is the SOTA" claim was stale (all-US instances now certified;
175k vertices with inexact contiguity). (5) caragiannis2019 already defines lexicographic
MNW — adopting it verbatim closes the empty-bundle decision in `MODEL.md` §6. (6) Verified
absences ours to claim: no price-of-connectivity for Nash welfare anywhere; no Nash-welfare
districting formulation; no sales-territory power diagrams; no joint alignment +
retention-selection. The five-paper shortlist says the niche is unoccupied (FINDINGS §7).

*What is next, and the decision it needs.* FINDINGS §9 is the menu, prioritized: **A1**
(power-diagram redraw + dual-weight certificate — a correctness fix to a primary artifact,
do first), then the cheap experiments **C1** (quadratic objective vs log — may delete the
OA machinery), **C2** (utilitarian-vs-Nash matching — envy-freeability), **C3** (EG
fractional dual bound), **C4** (compactness-measure robustness of the 8.53%). The
**lexicographic decision (open question 1) should now wait** on C4 + the frontier sweep
(§9-D) and the in-press ezazipour2025 Pareto paper. Then the citation pass over
`channel_note` (§9-B). The decision to make: adopt A1+B before presenting the draw, or
present as-is.

**Earlier — 2026-09-01 (night): stage 1 built, drawn, certified, mapped, and formalized.**
Head `b289f3a`, **131 tests pass**.

*What landed (all Opus-subagent builds from written plans).* `td/solvers/centers.py` —
center-based draw (k-means++ seeding, transportation-LP balanced assignment, Lloyd,
Nash polish, portfolio). `tools/run_draw.py` + `channel.place_by_state` — reproducible
runs into `battery/results/` (gitignored). `td/solvers/cert_draw.py` — three certificates.
`td/geo.py` + `tools/us_maps.py` — five map figures incl. the Voronoi territory map.
`docs/channel_note/` rewritten (21 pp, builds clean): §7 center-based formulation +
transportation lemma, §8 certificates + real run, old ceiling/contiguity demoted intact.
Atlas artifact (5 maps): https://claude.ai/code/artifact/1f2cddd9-b98b-4213-83ea-784566147c6a

*The draw (battery/results/draw_k13_20260901).* Winner seed 3 of 5 by stage-2 value
59.9375 (not the stage-1-best — the portfolio earning its keep); spread 0.642% drawn /
0.781% after placing the 6 coordinate-less zips; all 13 districts staffed (13 of 111 reps
selected). Certified: 4.51e-5 nats under the analytic ceiling; max-dev ~1,975× the
constructive indivisibility floor (imbalance = price of geometry); pinned-centers MILP
*proved* an 8.53% more compact assignment exists in the same balance band (152 relabels,
−4.66e-5 nats) — **not adopted; lexicographic priority is open question 1**.

*What is next.* The lexicographic decision (adopt the compacter assignment or keep
Nash-first); exact center choice (k-means-hard — column generation or center-MILP if
wanted); the θ/filler open decisions in `MODEL.md` §6; and presenting the draw.

**Earlier — 2026-09-01 (evening): the export landed and rewrote the problem.** Head
`98d042d`, 69 tests.

*What landed.* The real descaled instance (`instance_descaled.json.gz`, worktree root,
gitignored, `check_descaled` clean): **1,229 zips, 111 reps, 675 contested / 477
uncontested / 2 vacant / 75 untapped**. Exporter grew work-machine ergonomics on the way
(`0d3b556` adjacency builder from TIGER; `0a23b9b` `--join-floor`; `5f3b4c2` combined-file
input + `--impute-missing-m`; `91e203c` `--repair-headroom`; `98d042d` rounding margin +
loader tolerance).

*What the data said — three corrections from the user, all their SQL/double-count errors:*
total opportunity is **~$13B, not $6.2B** ⇒ **k ≈ 13** at $1B; reps are **111, not 72**;
and the footprint is **national, not four islands** — shares: west 33.2%, east 31.0%,
TX 11.5%, FL 6.7%, **~18% spread across the "uncovered" midwest+rest**. And the sold-zip
graph is shattered: **547 components**, largest 5.1% of M, 68% of M in sub-1% crumbs —
adjacency contiguity over sold zips is meaningless.

*Decisions (user, 2026-09-01).* **Stage 1 is center-based (Hess) compact assignment on
distances — option (a)** — no adjacency contiguity, no glue re-export. Granularity is
benign: the largest zip (10017) is 1.07% of total M ≈ 14% of one k=13 district, so
near-perfect balance is geometrically reachable and the old ceiling machinery is moot
under (a).

*What is next.* Build stage 1: ZCTA coordinates from the public Census Gazetteer
(~1MB, `pyproj` in the venv), then a balanced center-based heuristic (portfolio of draws)
feeding the existing exact stage 2 (`channel.score_draws`). The exact MILP comes after the
heuristic maps exist.

**Earlier — 2026-09-01.** Branch **`national-channel`** (`1272c72`), 37 tracked files,
**65 tests pass, 0 fail, 0 skipped**.

*What landed.* `1272c72`: the exporter's `validate` run now prints the **footprint
components as shares of total opportunity and the balance ceiling table** (k = n..n+5) —
an inlined stdlib `alloc_ceiling`, cross-checked against `channel.allocate_districts` by
`test_instance.py::test_footprint_report_components_and_ceiling`. Components below 1% of
total M are surfaced as crumbs, not sized, since each would have to host a whole district.

*What it means.* The four numbers stage 1 is blocked on no longer need a manual pull:
`validate` writes nothing and the new section is all shares and counts, so **one read-only
run on the work machine settles k** and whether ~$1B is reachable.

*What is next.* Run `export_instance.py validate` on the work machine (runbook:
`tools/instance_export/README.md`) and bring back the share column and the ceiling table —
or the full export, which supersedes them. Then the stage-1 MILP per §8 of the note,
centre-based (Hess), largest region first. The open modelling decisions below are unchanged.

**Earlier — 2026-08-31 (evening).** The problem changed shape three times that day and the
repo matches the final shape (then `6cfdd67`, 64 tests).

*What landed.* (i) **N-way primitives** — `b8ae73d`: `td/model.py`, a zip can be claimed by
3+ reps; the two-rep reduction is asserted against the old contract so the existing corpus
stays interpretable. (ii) **Descaled real-instance route** — `85492ef`: replaces the synthetic
twin, since the dollar scale is not information the model uses; `tools/instance_export/` +
`td/instance.py`. (iii) **National-channel reframing and stage 2** — `549e377`: greenfield
balanced districting, two-stage, staffing solved exactly by Hungarian matching on log weights.
(iv) **Instance sized and the balance ceiling** — `82d7b6a`: 2,232 zips, 72 reps, ~$6.2B,
k ≈ 6, disconnected footprint. (v) **Prune and restructure** — `acfdbfe`, `ecbbf84`: 199
tracked files → 33, `td/` package, `docs/` split, explicit registry, plus the 16-page
`docs/channel_note/`. (vi) **Adjacency cache dropped** — `6cfdd67`, recipe kept in
`data/README.md`.

*What it means.* Two results carry the work. **Nash welfare on a common measure IS
equal-size districting** (§1) — same optimum, not an approximation — so the $1B target needs
no constraint and trap 2's equalisation pathology is avoided. And **the footprint is
disconnected**, which both decomposes the problem by region (~500 zips each, near where
`scip_tree` already works) and puts a **geometric ceiling on balance**: `allocate_districts`
computes it as a free dual bound, and on illustrative splits $1B ± 10% is already out of reach
before any solver runs. A correction landed in `ecbbf84`: the earlier claim that ρ > 0 breaks
scale invariance was **wrong** — the objective is scale-invariant at every ρ ≥ 0, which
strengthens the descaled export rather than qualifying it.

*What is next, and the decision it needs.* **Stage 1 is the open work** — draw k balanced
contiguous districts. Before writing any solver, the cheapest and most informative step is the
balance ceiling, and it is blocked on **four numbers from the user: opportunity by region
(west coast / east coast / Texas / Florida).** Those give `k`, say whether ~$1B is reachable
at all, and need no solver and no per-zip data. *(Resolved 2026-09-01 — see the entry
above.)* After that: the stage-1 MILP per §8 of the note, centre-based (Hess) to break the
k-district symmetry, on the largest region first.

*Also open, and mine to ask rather than assume* (`MODEL.md` §6): empty bundles /
lexicographic MNW · θ directionality (`θ_{i←j}`) · the brute-force tier re-cut by
`Π|cand(z)|` · who owns untapped and vacant zips · the filler-capture mode (`theta` is the
default only because it is the no-change case; `full` is the better argument) · and whether
71 reps against ~6 territories means a specialist carve-out staffed thinly, which is the
reading stage 2's "unmatched" output assumes.

Earlier — the two-player merger programme (harness, method wave, S0/S1/S2, W6b/W6c/W6d,
`scip_tree` certifying every pair ≤ 135 zips with 124/135 proved exact global optima) is on
branch `contiguity-harness`; its resume point was `research/contiguity/PLAN.md` §0 and its
record is `docs/RESULTS.md`.

---


The business is standing up a **new "national" channel**, carving the two largest firms out
of the financial-institutions and wirehouse channels, with territories targeted at roughly
equal opportunity — about **$1B each**.

That is not the two-player merger problem, and it is not quite the N-way problem either. It
is **greenfield balanced districting**. Decided: **two-stage**, with the $1B as an emergent
target rather than a constraint.

### 1 Nash welfare on a common measure *is* equal-size districting

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

### 2 The welfare decomposition

```
Σ_i g_i = Σ_z [ λ·M_z + c2·T_z + c_free·S_free ]     ← partition-invariant
        + Σ_z (c1 − c2)·S_owner(z)(z)                ← maximised by keeping zips with their incumbent
```

The objective splits into **balance the territories** and **where there is slack, leave
business with the rep who already has it**. At ~5% saturation with λ=0.3 the opportunity term
is roughly 90% of `u_i` and the book differentiation roughly 10% — so a balanced map with a
modest continuity tilt. *Check the ratio against real saturation*: it decides how much the
legacy books move the map at all.

### 3 Two stages

| stage | problem | status |
|---|---|---|
| **1 — draw** | k balanced contiguous districts on opportunity alone | **the hard part**; balanced contiguous districting |
| **2 — match** | assign retained reps to districts | **built** — `td/channel.py`, exact |

Stage 2 is a max-weight matching on **log** weights: `g_ij = Σ_{z∈A_j} u_i(z)`, maximise
`Σ_i log g_{i,σ(i)}` by the Hungarian algorithm. Same objective as stage 1, O(n³), exact.
Nash rather than utilitarian matching matters — a utilitarian match will hand one rep a
district holding almost none of their book if the total looks good.

**Rectangular matching selects the retained set.** With more reps than districts the unmatched
reps are the ones not retained, and the choice is well-posed precisely because k is fixed
(§6.3's objection does not bite).

**Known cost of the split.** Stage 1 cannot see relationships, so a good matching may not be
available at stage 2 — the same objection CLAUDE.md raises to "decouple fairness from
compactness": it relocates the difficulty rather than removing it. Mitigation, cheap because
stage 2 is milliseconds: generate a *portfolio* of stage-1 draws and keep the one that staffs
best (`channel.score_draws`). Not the joint optimum, but close to free.

### 4 What this does to the data requirement

**Stage 1 needs almost none of the confidential data** — only `(zip, M)` and the adjacency
graph. No books, no rep ids, no shares. Opportunity is plausibly third-party market sizing.

**Stage 2 can run entirely on the work machine**, since it needs only the returned district
map plus internal books.

The descaled-export route (§5b) stays correct and is still the right channel for anything
that does need to travel, but the national-channel problem needs a fraction of it.

### 5 What is now the open risk

Stage 1 destroys the census decomposition. The bilateral pair structure came from *overlap
between two legacy rep maps*; a greenfield channel has no such structure, so stage 1 is one
k-way partition over the whole footprint.

- `scip_tree` certifies to **135 zips**. Validi, Buchanan & Lykhovyd certify ~**1,500 units**
  for political districting, which is the published state of the art for exactly this problem.
- If the footprint is larger than that, the options are pre-aggregation (cluster ZCTAs, or
  work at county/CBSA level), ε-certified acceptance (tier 2, already in the harness), or a
  heuristic with a reported bound.
- **Symmetry** is the new hazard: k anonymous districts are interchangeable labels, which
  costs branch-and-bound its pruning. The standard remedy is the centre-based (Hess)
  formulation — assign each zip to one of k *centres* — which breaks the symmetry by
  construction and is what the districting literature uses.

### 6 The instance, sized (2026-08-31; zip count corrected 2026-09-01)

| | |
|---|---|
| zips carrying sales | **~1,229** — the 2026-08-31 figure of 2,232 was a double-count in the source pull (user's correction, 2026-09-01) |
| distinct reps | **72**, including the "open" (vacancy) key → 71 real |
| total opportunity | **≈ $6.2B** — from the same 2026-08-31 sizing; **re-read it off the corrected extract** before trusting `k` |
| footprint | west coast, east coast, Texas, Florida — **midwest uncovered** |
| ⇒ `k` | **≈ 6** at $1B *if* the $6.2B stands; the validate report settles it |

Two consequences, and the second is the important one.

**Scale is at the frontier but not past it.** ~1,229 units × 6 districts ≈ 7,400 binaries —
half the pre-correction estimate. Validi, Buchanan & Lykhovyd certify ~1,500 units for
political districting, so this is the same order of magnitude as the published state of the
art — attemptable, not routine.

**The footprint is disconnected, and that is a gift.** No contiguous district spans
California and Florida, so the adjacency graph has ≥ 4 major components and **the problem
separates**: allocate an integer district count to each component, then solve each
independently. Failure mechanism (a) — pre-existing graph disconnection, the thing that
broke the legacy cut loop — arrives here as the structure that makes the problem tractable.
At roughly 200–500 zips per region the subproblems are far closer to where `scip_tree`
already works than the ~1,229-zip whole would be.

### 7 Balance has a geometric ceiling — compute it first

`channel.allocate_districts(component_M, k)` maximises `Σ_c k_c·log(M_c/k_c)` over integer
allocations with `k_c ≥ 1`. Within a component the best conceivable outcome is `k_c` equal
districts, so this is an **upper bound on any real partition** — a free dual bound for
stage 1, available before a solver runs (`test_ceiling_is_an_upper_bound_on_any_real_partition`).

It is also the answer to whether the target is reachable at all. Illustrative splits of
$6.2B (real regional totals still needed):

| split | k=6 | k=7 | k=8 |
|---|---|---|---|
| even-ish (2.0 / 2.2 / 1.1 / 0.9) | **19.4%** | 41.4% | 55.9% |
| east-heavy (1.6 / 3.0 / 0.9 / 0.7) | 87.1% | 33.9% | **25.8%** |
| coast-heavy (2.6 / 2.6 / 0.6 / 0.4) | 87.1% | 101.6% | **60.2%** |

(spread = (max−min)/mean across districts, at the **objective-optimal** budget)

**Caveat, added 2026-08-31.** Those are the spreads at the budget maximising
`Σ_c k_c·log(M_c/k_c)`, which is not always the *most even* budget. East-heavy at k=6 is the
worked case: the objective optimum allocates W/E/TX/FL = 1/3/1/1 for 87.1% spread, while
2/2/1/1 reaches 77.4%. `allocate_districts` now returns both — `ceiling_spread_rel` at the
dual-bound budget and `min_spread_rel` at the spread floor, with `spread_optima_agree` saying
whether they coincide. The conclusion is unchanged (77.4% is still nowhere near ±10%), but the
two numbers answer different questions and should not be quoted interchangeably.

Three things follow:

1. **$1B ± 10% is probably not reachable.** Even the friendliest split tops out near 20%
   spread, because a ~$0.9B region gets exactly one district and cannot be subdivided.
2. **The best `k` depends entirely on the regional composition** — the table moves in
   opposite directions across scenarios. `k` is a balance decision, not just headcount.
3. **This is four numbers of work.** Regional opportunity totals answer it immediately, with
   no solver and no confidential per-zip data.

**Next input needed: opportunity by region (west / east / TX / FL).** Everything above is
illustrative until those land.

**Also to confirm:** 71 real reps against ~6 territories is a 12:1 ratio. The reading that
makes sense is that the national channel is a *specialist* carve-out staffed by a handful of
senior wholesalers, while the other reps keep covering the remaining firms in the existing
FI/wirehouse channel — i.e. stage 2's "unmatched" reps are *not selected for this channel*,
not released. If that is wrong the framing of stage 2 needs revisiting.
