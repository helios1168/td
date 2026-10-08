# Division-level plan: contiguity by construction, coarse split borders, parallel trials

Research tab, 2026-10-08, draft v1 for co-development with an Astra oracle and owner review.

## 0. What the two Middle Atlantic runs taught

| Run | Method | Time | M1 | Look |
|---|---|---|---|---|
| `ifa_div2_midatl_k11` | whole-unit planner, county pieces | 70 s | pass on 9/11 real ZIP sets | atrocious (Hudson strip, no shape term) |
| `ifa_div2_midatl_zip_k12` | existing ZIP realizer, δ 0.15 | 11 min | **fail**: 2 districts in pieces, 4 necks | fallback scatter in Manhattan |

The realizer failure is instructive. `run.py` builds the draw on `geo.polygon_graph()`, which
ships the whole CONUS vertex set (trap 21), so the "division" draw had 33,300 free ZCTAs and
1,058,862 rows, hit its 600 s limit with no incumbent, and the constructive fallback drew the
map. The necks it left are the known ones (the Delaware Memorial Bridge connector 08023, the
Nassau–Suffolk line at 11786–11792, Brooklyn) plus a NJ+PA district the plan allowed because
`run.py` has no rule C. None of this is division-specific; it is the plan-then-draw-then-repair
pattern failing at any scale.

## 1. The contiguity guarantee (the non-negotiable)

M1 is judged on a district's ZIP set alone (`td.audit.district_pieces` and `district_necks`
read the polygon graph, land area and connectors; mass only orders components). So:

1. **A district is admitted only after the exact gate passes on its final ZIP set.** Never a
   coarse check in its place; a coarse neck implies a fine neck but not the reverse (Utah 84621
   is invisible at county grain). Never repair: a failed candidate is discarded or re-cut.
2. **Districts are built from whole planning units plus at most one carved piece**, so the
   candidate set is small and each candidate's gate call is seconds.
3. **Sealed divisions make the guarantee compose.** A district's ZIP set lies in one division,
   so its verdict cannot change when nine division ledgers are merged. The merged ledger is
   re-gated once anyway, for coverage (every CONUS ZCTA owned exactly once, zero-opportunity
   ones included) and as the only verdict that counts.
4. **A run that cannot reach all-pass stops and reports fail.** No map is a scenario map until
   the merged ledger passes the gate (M1, mandate, no tolerance).

Unsealed divisions lose property 3 only at the seams: a district crossing a division line is
gated on its full ZIP set like any other, but the two divisions must then be planned together.

## 2. Coarser within-state split borders

Candidate unit levels for a split, all present in `reference/2025/zcta_reference.csv.gz` or
derivable from it: county (`county`), CBSA (`cbsa`), CSA (`csa`), metropolitan division
(`metdiv`), and the state remainder outside any of these. Unit adjacency is induced from the
polygon graph (two units touch when some ZCTA of one shares a polygon edge or approved connector
with some ZCTA of the other), so unit-level connectivity is sound for rejection and the ZCTA gate
decides acceptance.

| Level | Units in NY/NJ/PA | What a split looks like | Where it fails |
|---|---|---|---|
| state | 3 | no split | NY, PA, NJ all over U |
| CSA + remainder | ~12 | metro as a block, rest of state as a block | NYC CSA alone is $5.5B of NY's $5.47B: it must itself split |
| CBSA + remainder | ~40 | MSA blocks | NYC MSA still over U |
| metdiv + remainder | ~45 | NYC MSA's 4 divisions (Nassau–Suffolk, NYC, Newark, New Brunswick) | within reach: each is roughly one district |
| county | ~130 | county blocks | shapes grown without a shape term look bad; Queens, Brooklyn are single counties over U |

Prediction to test: **metdiv + remainder** is the right grain for the dense corridors (its
divisions are drawn by OMB to be commuting-coherent and roughly district-sized), **CSA +
remainder** for everything else, **county** only as fallback, and the ZIP carve only inside a
unit still over U after that. A split at a metdiv border is a border stakeholders will read as
deliberate.

## 3. Channel-agnostic core

One module takes: a universe of (ZIP, fine channel) cells; a dollar mass per cell; a band [L, U]
(target-centred for national/WH/FI/IFA, mean-relative for WIFI, resolved before the call); a K
range; a unit hierarchy (division ⊃ state ⊃ {csa|cbsa|metdiv|county} ⊃ ZCTA); the sealed flag;
and the gate. It returns admitted districts (ZIP sets with verdicts) and the plan statistics
(splits, cuts, band, wall time). Nothing in it names a channel, a state, or a K.

Existing code it wraps: `td.spec` (instance), `td.master` (support master), `td.audit`
(gate), `tools/exp/contig/wholeplan.py` (check-and-ban loop, today county-only and IFA-only),
`tools/exp/contig/pieces.py` (unit grouping, to be generalised to any unit column), `draw.py`
(the ZIP realizer, run on the induced subgraph), `tools/maps/render.py` (render). New code is
the unit builder, the induced-subgraph wrapper, the division merge, and the trial runner.

## 4. The trial matrix, built to run in parallel

Each job is one (division, channel, unit level, K, sealed) cell. A job is small (minutes) and
writes one tracked folder with manifest, districts, verdicts and timings. The runner dispatches
jobs with a process cap and notifies on completion; results land in one table.

| Axis | Values |
|---|---|
| division | 9 Census divisions; for the main map also the 4 regions and the current 2-group layout |
| channel | IFA; national, WH, FI; WIFI (combined set given) |
| unit level | state, csa, metdiv, cbsa, county |
| K | the division's arithmetic range |
| sealed | yes; no (seams planned jointly, later) |

Order of execution:

1. **S0, build (about 2 h):** unit builder; induced-subgraph draw; generalised `wholeplan`
   over any unit level and channel; division merge plus full gate; the runner. All tested on
   the Middle Atlantic IFA instance, which has every failure mode.
2. **S1, screen (minutes):** arithmetic per cell: forced splits, K range, forced company.
   Prunes the matrix.
3. **S2, whole-unit plans with check-and-ban (minutes each, all cells in parallel):** M1-clean
   by construction; gives splits, cuts, band, and a look per unit level.
4. **S3, carve the remaining over-U units** (NYC and the like) with the ZIP realizer on the
   unit's own subgraph, gated; or the k-piece carver if the realizer's shapes disappoint.
5. **S4, merge, gate, render, shortlist.** Judge by splits, cuts, look, band.

Compute: the brief caps this Studio at 4 solver processes. S2 cells take about a minute, so 9
divisions × 5 unit levels × 1 channel is about 15 minutes at the cap; the main map's three pure
channels and WIFI triple that. Raising the cap is the owner's call.

## 5. Owner choices this plan needs

- Sealed divisions as a constraint for IFA (and, via regions or the current layout, the main map).
- Whether metdiv/CSA borders are acceptable split lines (they are not state or county lines).
- Process cap above 4 for the trial matrix.

## 6. Open questions for the oracle

- Is the contiguity guarantee in section 1 complete? What can break at merge besides coverage?
- Is "whole units plus at most one carved piece" too restrictive for balance anywhere?
- Which unit level should be tried first, and is the metdiv prediction sound?
- What in the matrix is wasted, and what is missing?

## 7. Oracle co-development (GPT-6 Astra medium, `research-2026-10-08/ORACLE-PLAN.md`), accepted

- **Two graphs.** Planning and drawing use the induced subgraph on the division's shipped
  vertices (from `graph_vertex`, never from extract rows); the audit always uses the full
  polygon graph, connectors, borders and land areas, because a connector's width depends on land
  alternatives across the district's states (`td/audit.py:532-559`).
- **The invariant** every job keeps: each admitted district owns a fixed, nonempty ZCTA set
  inside an explicit footprint; every (ZCTA, fine channel) cell has exactly one owner, zero-dollar
  cells included; each district passed the authoritative gate on exactly that set; merge never
  adds, removes or re-routes a cell. Merge hazards beyond coverage: colliding district ids, fine
  channels of one ZIP routed to different districts, geometry version drift, seam filling. So ids
  are namespaced, gates are cached by hash of the ZIP set plus gate inputs, and the merged ledger
  is re-gated with full `check_m1` regardless. An unresolved neck search is `unknown`, never a pass.
- **"At most one carved piece" was a shape heuristic, not a contiguity rule**; dropped from
  section 1. Rule C counts original split states, not units.
- **Corrections to section 0:** the K 12 draw timed out on the global graph, so it measured
  nothing about a scoped draw; NY's $5.47B admits at most five $1,000M-floor IFA districts, not
  six, and the $1,913M city group cannot become two in-band districts without mass from outside.
- **Coarse units, from the reference and polygon edges:** CSA and CBSA remainders are not
  connected (NY's CSA remainder has 4 components, PA's 6), 19 of the Middle Atlantic's 150 county
  groups disconnect on the polygon graph, and CSAs cross state lines so they must be intersected
  by state. The "roughly district-sized metdiv" claim was unsupported. Two controlled proposals
  replace the five-level matrix: (1) adaptive hierarchy, state-intersected CSA → CBSA → metdiv
  where present → ZCTA refinement, every unit split into connected components, oversized units
  expanded; (2) connected spatial aggregation inside original states with no administrative
  labels. Same solver, same gate; only the proposal partition differs.
- **Contract needs more than [L, U]:** explicit footprint, original-state map, full-precision
  fine-channel dollars with rates frozen from the full extract, the cell-routing policy (not
  proven binary: `td/spec.py:411-414` allows national-absent fallback), rule C with the F1
  exception, global K and WIFI (M, K) resolved before any regional solve.
- **Timing, honest:** S0 is 4–8 engineering hours including tests; the two-method pilot another
  2–4 hours plus measured runs. No evidence yet supports minute-long gates or ten-minute
  nationwide completion (a neck search alone may take 60 s per component). Four single-process
  jobs including gate solvers; no nested pools.
- **S0 task list** (files and runnable acceptance per task) is in the oracle report, section 5.
