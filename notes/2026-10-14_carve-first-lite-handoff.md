2026-10-14 · main · afe055e · Agent: supervisor (claude-opus-5-5)

# Handoff: carve-first lite, a parallel track to tonight's sealing runs

For an interactive session the owner runs in parallel. Start with `/skill:plan` on #130 (with #129 as its carver). This session keeps going on regional sealing; the two tracks share only the M1 gate.

## Tasks
- Carve-first lite design (below): drafted in chat 2026-10-14, **not planned or started**.
- M1 water/empty-land rule in `td/audit.py`: **in progress** in this session (worker run eeec4958); the library must use it.
- Shape-metrics explainer PDF: **in progress** (worker run 1a41476d); its metrics are the shape filter.

## Critical references
- `docs/archive/lenses/review-2026-10-07/METHOD-carve-first.md`: the full method (library, selection MILP, certificate, pricing). Reviewers voted "adopt with changes" in round 3 on 2026-10-07; it was never built.
- `notes/2026-10-13_ifa-split-state-constraints.md` and `notes/2026-10-13_hypergraph-framing-and-alternatives.md`: why sealing worked for IFA and what it cannot fix.
- Issues: #129 (carver), #130 (pipeline), #141 (rule C), #134 and its children (looks-first policy).

## Changes this session
- `afe055e`: IFA region specs are tracked only in `scenarios/regions/ifa/`, and `tools/exp/contig/coarse.py:255` defaults there.
- DECIDED comments 2026-10-14: #140 (Manhattan stays an exception; every approved connector has unlimited width; passage width counts no-ZCTA land and zero-opportunity ZCTAs), #112 (the ±15% band is hard; K moves, the band does not), #134 (order: contiguity, shape, balance, splits), #105 (done means the full grid passes; the grid's extent is not yet fixed).

## Design as drafted ("carve-first lite")
1. **Library, built in parallel per state and per region, on m5 and m2.**
   - Whole-state columns: every connected set of whole states in the band, gated once. Use `tools/exp/contig/wholeplan.py`'s `m1_verdict` (the gate's own functions).
   - Split-state patterns: for a state that must split, k pieces, each with a disjoint attach set of whole neighbouring states, each piece plus its attach set in the band. Generate them at the state-senate (sldu) grain by generalising `tools/exp/contig/coarse.py`'s flow MILP (it groups sldu units into K connected groups at least border). Contract the attach states to a root, randomise seeds and attach choices, and gate every district on its real ZCTA union. `pieces.py` (county cuts) and `plancheck.drawable` are the alternatives.
   - Store every column with its M1 verdict and its shape metrics (`tools/looks/study.py`). Keep only passing columns.
2. **Selection MILP:** cover each state exactly once with K columns. Shape limits and the band act as filters at selection time, so they are parameters and the library is not rebuilt when they change. Objective: splits, then cuts, then shape, then balance.
3. **Assembly:** write the ledger from the chosen columns and gate the whole map; a gate failure here is a bug, not a ban.
4. **The library does not depend on K:** one library per channel answers every K in the grid. WIFI needs a band per K (E3).
5. **Sealing combination, option A (recommended):** generation runs in parallel per state and region, and one national selection runs with no region lines. Option B, the fallback: a library and selection per region, joined with `merge.py`, for a region where the national selection is slow or infeasible.
6. **Pilot on IFA first** (one channel, close to passing), then the main-map channels.

## Learnings
- Rule C (at most one split state per district) is what makes carves independent and parallel. IFA's maps follow it. It is still undecided (#141).
- County grain fails where one county exceeds τ (LA). Use the sldu grain, as `coarse.py` does.
- Balance is fixed when a column is generated: a map can only be balanced better by adding columns.
- The gate in `td/audit.py` is changing tonight. Build against `check_m1`/`district_necks` as called by `wholeplan.m1_verdict`, then rebase onto the M1-rule commit once it lands on main.

## Next steps
1. `/skill:plan` on #130: settle the four open decisions below, then write Goal · Files · Acceptance · Phases into #130's body.
2. Draft the column-record contract (fields, file format, gate call) so the library, carver and selection can be built by three workers at once.
3. Keep to new files (for example `tools/exp/carve/`) and leave `td/audit.py`, `tools/exp/contig/overnight.py`, `merge.py` and `scenarios/regions/` to the sealing session, to avoid merge conflicts.
4. IFA pilot at one K, then the IFA K grid, then the main-map channels.

## Open owner decisions
- Rule C for carve-first (#141): accept it (recommended) or allow two split states per district.
- Option A or B for combining with sealing (A recommended).
- Shape filter values: the provisional ones are bite ≤ 0.30, hull fill ≥ 0.45, at most 4 states per district, no hard doughnut; retune them after the PDF (#135, #138).
- Compute: m5 and m2 shared with tonight's sealing runs; agree slot counts with that session.

## Refinement (same session, later): phased plan
- **Phase 0, sizing (arithmetic, no solve).** `tools/exp/region_arith.py` (worker run 1cab5266, in progress; land it before starting). Per channel and K it gives: feasible K, forced splits (a floor for the certificate), the whole-state library size at caps 4/6/none, the carving job list (σ, k) with candidate attach-set counts, and rule C orphans. Go/no-go per channel: no orphans, small states coverable under the shape cap, attach-set counts that will not blow up. This decides #141 with data.
- **Phase 1, contract.**
  - Column record: id, channel, whole states, split state σ or none, ZCTA list (side file), $M, M1 verdict and details under the 2026-10-14 rule, shape metrics from `study.py`, border km, gate commit.
  - Pattern record: σ, k, its k column ids, and a check that the pieces partition σ's ZCTAs.
  - A library is per channel and window, and independent of K (WIFI: per K).
- **Phase 2, three workers in parallel.**
  - (a) Whole-state columns from the Phase 0 enumeration, gated and scored in parallel.
  - (b) Carver per (σ, k): choose k disjoint attach sets from the Phase 0 candidates (one may be empty), then run a flow MILP at the sldu grain generalised from `coarse.py`. It contracts each attach set to a root, puts a window on each piece plus its attach set, and minimises border plus a compactness term. Randomised variants; keep a pattern only when all k districts pass the gate and the shape metrics are computed.
  - (c) Selection MILP and assembly. Coverage rows carry an elastic slack per state at a large penalty, so an infeasible library names the states it cannot cover. Shape and band are filters; the objective is splits, then cuts, then shape, then balance. Output is the ledger, the full gate and a `zip_pages` render.
- **Phase 3, IFA pilot at one K** (K52, compared against `results/ifa_kgrid_2026-10-13/K52`).
- **Phase 4, growth loop.** Each state the slack names becomes a targeted carver job; repeat. Pricing by duals is later.
- **Phase 5, grids.** IFA K48–54. Then the main-map channels: each channel's footprint is separate, so the libraries are independent and build in parallel.
- **Sealing tie-in.** Region partitions are used only to shard Phase 2 work across m5/m2 (Phase 0 gives the per-region load). Option B (selection per region) is the fallback for a slow or infeasible national selection.
