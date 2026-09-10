# Code map and run recipes

What is built, where, and how to run it. State lives in `STATE.md`; the problem and the model
are `docs/PROBLEM.md` and `docs/MODEL.md`. Keep this file to facts about the tree.

## Two stages

| stage | problem | where |
|---|---|---|
| **1 — draw**, power cells | k balanced **compact** districts on opportunity alone (contiguity abandoned: on v2 the zip graph has 862 components over 3,748 zips); the territory is a power diagram | `td/solvers/centers.py`, certificates in `td/solvers/cert_draw.py` |
| **1 — draw**, state atoms | k balanced **contiguous** districts, on whole states with only the oversized ones cut into pieces — pre-aggregation, so contiguity becomes achievable rather than vacuous | `td/atoms.py` + `td/solvers/atom_draw.py`, run by `tools/run_atoms.py` |
| **2 — match** | assign reps to districts — max-weight matching on **log** gains (`g_ij = Σ_{z∈A_j} u_i(z)`, maximise `Σ_i log g_{i,σ(i)}`), Hungarian, exact; rectangular matching selects which reps staff the channel | `td/channel.py` |

Stage 1 cannot see relationships, so `channel.score_draws` ranks a portfolio of stage-1 draws
by how well each staffs. Node classes from `cand(z) = {i : S_i(z) > 0}`: contested (≥2),
uncontested (1), vacant (0, filler book), untapped (0, no book) — vacant and untapped zips stay
in the graph (`docs/MODEL.md` §6 on who may own them).

## Data route

The descaled real instance, not a synthetic twin, is the source of record: real ZCTAs, real
adjacency, real share patterns, with PII and firm masked and the dollar scale removed
(`tools/instance_export/export_instance.py`, the work-machine exporter; `td/instance.py`, the
repo-side loader — both in `## Files` below). The route is licensed algebraically: `u_i(z)`
factors `M_z` out, and `Σ_i log g_i` shifts by a constant under any global rescale, including at
ρ > 0 (corrected 2026-08-31: perimeter is combinatorial, so every objective difference and the
argmax are untouched at every ρ ≥ 0). Descaling changes only conditioning — solver feasibility
tolerances are absolute in gain units; certificate tolerances are in nats and scale-free either
way.

## Files

| file | role |
|---|---|
| `td/model.py` | N-way primitives: schema shim, per-rep utilities, gains, objective, perimeter, per-rep pieces, n-agent EF1 |
| `td/channel.py` | stage 2 (Hungarian on logs), balance report, `place_by_state`, `allocate_districts` (the ceiling / dual bound) |
| `td/instance.py` | loads the descaled real instance into the N-way schema |
| `td/ziptable.py` | the zip table, one row per instance zip (`zip,state,x,y,opportunity,district`) and the schema `draw.csv` now carries: `build`/`read`/`write`, `labels`/`masses`/`balance`, and `render`, which draws a table with no instance and no gazetteer, clipped per state with heavy state lines always on |
| `td/solvers/centers.py` | stage 1: k-means++ seeding, transportation-LP balanced assignment, Lloyd, Nash polish, portfolio; `power_weights` / `power_labels` (the LP duals and the power diagram) — `power_weights` also returns `fractional` (the split zips' row indices), surfaced as `power_diagram_of_draw`'s `split_zips`. `assign()`'s LP is pinned to `method="highs-ds"` with an explicit `options` dict — scipy 1.18.1's HiGHS wrapper hangs on v2 without one |
| `td/atoms.py` | state atoms for stage 1: whole states, with the oversized groups cut by `centers.draw` (CA 5 / TX 2 / NY+NJ 3 / FL 2, decided 2026-09-06), and their rook adjacency. Owns the AK→WA / HI→CA1 merge and the stateless (`??`) rule, both documented placeholders |
| `td/solvers/atom_draw.py` | stage 1 on an atom graph: multi-restart seeded growth plus connectivity-checked border moves, contiguity verified on the result. `free_search` is the contiguity-dropped **reference, not a bound** — the bound is `cert_draw.cert_balance_ceiling`. Requires `PYTHONHASHSEED=0` |
| `td/solvers/eg_band.py` | U8-band: the band-constrained Eisenberg–Gale program `EG^bal_S(δ)` — `O(nk)` dual bound (no solver in the trusted path), HiGHS outer approximation, SCIP cross-check |
| `td/solvers/cert_draw.py` | four post-hoc certificates: analytic balance ceiling, integer balance floor, assignment optimality at pinned centers (MILP), `cert_power_diagram` (duals as a solver-free `O(nk)`-checkable bound) |
| `td/solvers/scip_tree.py` | the two-player MILP engine — **not** what stage 1 was built on |
| `td/solvers/cert_exact.py` | exact post-hoc certificate (W6c); its AM–GM OA generalises to n terms |
| `td/solvers/{base,brute}.py` | harness contract; brute-force oracle |
| `td/geo.py` + `tools/us_maps.py` | ZCTA points, `zcta_polygons` (the real ZCTA boundaries the app's maps draw, subset by zip before reprojecting and cached; `ZCTA_SHP` resolves repo-relative, then `TD_ZCTA_SHP`, then the hub, and the 822 MB shapefile is local-only, never cache-fetched like the gazetteer), LAEA projection, state basemap, `state_rook` (the TIGER state rook graph, 49 nodes / 107 edges — the instance cannot supply it, contracted to states its zip graph has 10 edges over 42 components); six figures incl. `figure_power_regions` (the territory map) and `figure_district_regions` (superseded catchment fill, `--regions-voronoi`), plus the close-ups `figures_district_detail` (`--district-figures`) and `figures_state_detail` (`--state-figures`); every label goes through `_place_labels`, which pushes a label off its anchor and draws a leader line when the box would hide the district |
| `tools/run_draw.py` | the reproducible pipeline: instance → (k, seed) draws on a process pool → stage 2 → `battery/results/<run-id>/k<kk>/` + `sweep.csv`; `--fix`/`--anchor NAME=ST,ST` or `--scenario file.json` for hand-drawn districts; `--k 14-22` is the v2 sweep, `--k 8-16` the v1 regression (pinned to `sweep_20260902_s10`) |
| `tools/run_atoms.py` | the state-atom stage-1 driver: instance → atoms → contiguous draw → `k<kk>/draw.csv` + `metrics.json`, the same shapes `run_draw.py` writes. A separate script rather than a `run_draw.py` flag because the atom route has no coordinate-less gap — a zip with no gazetteer point still has a state, so it still has an atom, and routing it through `place_by_state` would change the draw's value |
| `td/solvers/state_splits.py` + `tools/state_splits.py` | Track 2: the state-level minimum-splits MILP (`build_milp`) and its level-2 realisation (`realise`), driven per `δ`. `--anchor-homes` names each district's committed home state so HiGHS can close the model; `--cap ST=N` holds a state to N districts and `--unanchor ST` releases only the anchors a cap forces; `--dump-state-shares PATH` writes each state's `M_s/τ` and anchored count and exits before solving, which is what the app's Headline tab reads. `--strategy` (`direct`, `descent`, `portfolio`, the default) picks how `solve` reaches its answer; `splits.json`'s `certified_splits` says the split count is proven even when `status` is `time_limit` on the compactness tie-break (`docs/APP.md` §4). A cell whose MILP returns no map writes `failure.json` and re-raises, so `infeasible` (a proof) and `no_incumbent` (the time limit) stay apart. `docs/HEADLINE.md` is the write-up |
| `tools/measure/premium.py` | the premium ladder, U1/U4/U8, verdict conversions |
| `tools/measure/district_pieces.py` | each district's largest contiguous piece by area, by mass and by ZIP count |
| `tools/measure/frontier.py` | the D1′ driver: utility-convention gate (`EG_S ≥ V`), the `δ` frontier, `δ*`, first movers, N8/N9, the plot. Background it with `python3 -u` |
| `tools/measure/instance_diff.py` | v1↔v2 comparison: recovers the descaling divisor from the unchanged zips; run on any new export before trusting a sizing figure |
| `tools/instance_export/export_instance.py` | work-machine exporter — stdlib only, single file, **read it before running it** (`tools/instance_export/README.md`); accepts the three national sub-channels in place of `national` |
| `tools/verify/runs/` | the catalogue driver (`run_all.sh`), maps (`make_maps.sh`), generator (`build_artifact.py`), 14 scenario specs |
| `tools/verify/U*/` | runnable artifacts behind each unit's Model / Verify / Code verify sections in `docs/units/<id>.md` |
| `docs/channel_note/`, `docs/math_note/` | the LaTeX notes (channel model; the original two-player formulation). `math_note/toy_*.py` import the deleted `code/gfx` and are broken |
| `tests/run_all.py` | 534 fast tests (solver venv, 2026-09-09); `-k <name>` filters. `TD_SLOW=1` currently adds nothing — no module sets `SLOW = True`. `tests/test_app_smoke.py` and `tests/test_mapfig.py` need the app venv instead (`docs/APP.md` §7) |
| `app/` + `tools/app.sh` | the Streamlit scenario app: launch a scenario grid, see the map and the incumbent reps' territories, staff and split, override, compare, watch the timings. Runs in its own venv `.venv-app` and never imports `td`, it drives the drivers by subprocess, which is both the version boundary and the solver-swap seam. `app/main.py` wires six tabs (Scenarios, Map, Reps, Overrides, Compare, Timings), each its own `tab_*.py` module; `app/common.py` holds what they share (cached reads, run pickers, `launch_child`); `app/store.py`/`app/steps.py` are the run ledger and argv builders; `app/mapfig.py` builds every plotly figure (the zip map, the rep and staffed maps); `app/repdata.py` loads or builds `reps.json`; `app/staffdiff.py` is the before/after arithmetic. `docs/APP.md` is the whole story |
| `tools/rep_export.py` | writes `reps.json`: per-zip rep shares and weights, dominant-rep territories, footprints, the contested union, all ratios and polygons, no mass. `docs/APP.md` §4 |
| `td/telemetry.py` | `Timings`: nested phases, accumulated ticks, wall/CPU/RSS, written as `timings.json` next to a driver's other outputs; `TD_PROFILE=1` also dumps a `cProfile` run. Stdlib only, so library code (`td/solvers/centers.py`'s `assign`) can call the module-level `telemetry.tick`/`telemetry.phase` hooks and stay import-clean. `docs/APP.md` §4 |
| `td/solvers/milp_engines.py` + `td/solvers/milp_worker.py` | alternative solvers for the level-1 minimum-splits MILP behind one seam, `solve_problem`: `scipy` (the baseline), `highs` and `scip` in process, `cpsat` out of process in `.venv-opt` through `milp_worker.py`. `fix_roots`, `with_cutoff` and `lp_heuristic` build variant problems. `docs/APP.md` §1, §4 |
| `tools/bench/` | `milp_bench.py` compares the engines above on the real instance at a given k, writing `battery/results/bench/milp_<stamp>.json`; `requirements-opt.txt` pins `.venv-opt`; `README.md` has the build steps, the variant table and the acceptance rule |
| `tools/verify/milp_root_fix/` | the root-fix claim (fixing an anchored district's flow root loses no optimum) VERIFIED by `math-verify`, `check_root_fix.py` the runnable artifact, `REPORT.md` the write-up |
| `tools/geom_export.py` | a zip table's polygons as `geom.json`, no solver needed downstream: `cells` are the real 2025 TIGER/Line ZCTA polygons (`geo.zcta_polygons`, 250 m simplify) and `districts` their dissolve, so unpopulated land and water show as real gaps (`holes` carries each district's interior gaps, a separate key because `rings` has fill call sites). Voronoi survives internally only for `cell_edges` (the split's contiguity graph, unchanged), its vertex set `cell_graph_zips`, and the colouring adjacency — only the Voronoi dissolve tiles, so only there does "intersects" mean "shares a border". `cells_source` records shapefile and tolerance. `docs/APP.md` §4 |
| `tools/staff.py` | stage 2 plus released reps and restricted candidacy: `model.release_reps` folds a departing rep's book into `S_free`; a rep may be assigned only a district it already holds book in; writes `staffing.json` and a `draw.csv` with `rep` filled per staffed district. `docs/APP.md` §6 |
| `tools/staff_and_split.py` | one pass over a scope where a district takes one rep or several: the N=1 districts go through `staff.py`'s Hungarian match, the N≥2 ones through `district_split.split`'s contiguous Nash bargaining, sharing a single `channel.gain_matrix` call. A rep claimed by a multi-rep district is held out of candidacy, never released — releasing folds their book into `S_free` at `c1` and distorts every neighbouring match, which is why this is one script and not two CLI calls chained. Splits run before the match, so a split that fails leaves its district to the ordinary match with its reps still free. `staffing.json` gains `split_districts` and `requested_multi`; the run kind stays `staff`. `docs/APP.md` §6 |
| `tools/override.py` | the map-override driver: mode A relabels a zip table by hand, no rerun; mode B translates the same edits into its parent's own flags and reruns that driver. Both report balance, contiguity and a diff. `docs/APP.md` §4, §6 |
| `tools/split_district.py` + `td/solvers/district_split.py` | divides one district's zips among the reps who staff it by the same Nash objective one level down: a greedy pass by default, a `pyscipopt` MINLP warm-started from it under `--exact`. Contiguity is on the Voronoi **cell** graph, not the sold-zip graph (that one is shattered), and is enforced in the greedy engine only — contiguous seed plus an articulation-point move guard — with `pieces`/`contiguous` reported from both engines. `build_adjacency` turns a `geom.json` into the graph; a geom with no cells is a hard failure, never a silent unguarded solve. `docs/APP.md` §6 |
| `docs/PROBLEM.md` | owner of the settled business-problem facts |
| `docs/MODEL.md` | owner of the settled model facts |
| `docs/CODE_MAP.md` | this file: what is built, where, how to run it |
| `docs/APP.md` | owner of the Streamlit app's story |
| `docs/HEADLINE.md` | owner of the shipped headline map end to end: the committed draw, the level-1 split MILP, level-2 realisation, what is certified, and how to reproduce it |
| `docs/FULL_PROBLEM.md` | owner of the multi-channel formulation (track `full-problem`): cells by (zip, channel), bundles, the joint problem F, the decomposition by bundle, level 0 at state × channel grain, routes S/J and merge drivers R/G |
| `docs/MODEL_FULL.md` | the full model line by line (track `full-problem`): level 0 rows and passes as built, the level-2 transportation LP and repair, the stage-2 assignment, and what was left out |
| `docs/units/<id>.md` | one unit's brief plus `## Model`, `## Verify`, `## Code verify` and a `Status: open\|done\|dropped` line |
| `docs/foundations/` | frozen FRAME, APPROACHES, LENS_*, DOMAIN_*, LIT_*, BRIEF and the former `archive/`; read-only, never edited |
| `<worktree>/PLAN.md` | one track's running log (`## Goal`, `## Next step`, `## Done`, `## Decisions needed`, `## Files owned / forbidden`); committed on the branch, deleted at merge |
| `tools/verify/<id>/` | runnable verifier artifacts for unit `<id>`, cited from that unit's `## Verify` / `## Code verify`; not test-discovered |
| `literature/territory_bibliography.{md,csv,bib}`, `literature/RESEARCH_ADDITIONS.bib` | citations (bibliography skill) |
| `.claude/doc-owners.txt` | the docs ownership allowlist, read by the `td-doc-owners.sh` PreToolUse hook and `tests/test_docs_owners.py` |
| `.claude/settings.json` | wires the four `~/.claude/hooks/td-*.sh` hooks: SessionStart, PreCompact, PreToolUse, Stop |

## Recipes (v2 forms — the live ones)

```
tools/run_draw.py instance_descaled_v2.json.gz --k 18 --seeds 0-9 --workers 8 --out battery/results/draw_k18_v2_20260904
PYTHONHASHSEED=0 tools/run_atoms.py instance_descaled_v2.json.gz --k 18 --reference --out battery/results/atoms_k18_v2_20260906
tools/measure/premium.py instance_descaled_v2.json.gz battery/results/draw_k18_v2_20260904 --out battery/results/meas_v2_20260904
python3 -u tools/measure/frontier.py instance_descaled_v2.json.gz battery/results/draw_k18_v2_20260904 --out battery/results/u8_band_v2_20260904 --figure figures/u8_band_v2/frontier.png
tools/measure/instance_diff.py <old> <new> [--json out.json]
tools/us_maps.py <instance> --out figures/<dir>/ --districts <draw.csv> --regions <draw.csv>
.venv/bin/python3 tools/run_draw.py instance_descaled_v2.json.gz --k 14-22 --seeds 0-9 --workers 8 --out battery/results/runs_<date>/baseline
bash tools/verify/runs/run_all.sh   # 15 runs, ~14 min; then make_maps.sh and build_artifact.py --date <date>
tools/app.sh                          # the scenario app on 127.0.0.1:8501 (docs/APP.md)
tools/geom_export.py --table <run>/draw.csv --out <run>
tools/staff.py instance_descaled_v2_conus.json.gz --table <run>/draw.csv --release R12,R31 --out battery/results/app/staff_<name>
tools/override.py instance_descaled_v2_conus.json.gz --table <run>/draw.csv --edits edits.json --mode A --out battery/results/app/override_<name>
tools/split_district.py instance_descaled_v2_conus.json.gz --table <run>/draw.csv --district D05 --reps R1,R2 --exact --time-limit 60 --out battery/results/app/split_<name>
.venv/bin/python3 tests/run_all.py    # 312 fast tests; -k <name> filters
~/.claude/hooks/test-td-hooks.sh      # SessionStart / PreCompact / PreToolUse / Stop hook tests
```

### Runtime baseline (2026-09-08)

The app grid of 2026-09-08 14:42 (k = 10 to 20, delta 0.10, 5 seeds, 2 workers per draw), before
the MILP engine bench picked a winner (`docs/APP.md` §1, §4):

| step | k=10 | k=12 | k=14 | k=16 | k=18 | k=20 |
|---|---|---|---|---|---|---|
| draw (stage 1 + stage 2, per chain) | 9 s | 9 s | 11 s | 12 s | 11 s | 10 s |
| clip: level-1 MILP (`state_splits.solve`) | 16.5 s | ~150 s | ~3 s | 600 s cap | 600 s cap | 600 s cap |
| clip: balance pass + level-2 realise + stage 2 + tables | < 1 s | < 1 s | < 1 s | < 1 s | < 1 s | < 1 s |
| geom export | ~2 s | ~2 s | ~2 s | ~2 s | ~2 s | ~2 s |
| chain end to end | 27 s | 2.5 min | 14 s | 10.2 min | 10.2 min | 10.2 min |

The six chains run in parallel, so the grid's wall clock is the slowest MILP plus about 15 s:
10 min 14 s, set by the 600 s time limit at k = 16 to 20. The MILP bench's own numbers
(`tools/bench/README.md`) will be recorded beside this table once it has run.

### Runtime after round 2 (2026-09-09)

The same k = 10 to 20 grid, delta 0.10, run again once the portfolio strategy (HiGHS and SCIP
racing as separate processes, `docs/APP.md` §4) replaced the plain HiGHS solve as the clip
default, each chain's clip sized by `steps.grid`'s per-chain `--threads 2` (Apple M2 Max, 12
cores):

| step | k=10 | k=12 | k=14 | k=16 | k=18 | k=20 |
|---|---|---|---|---|---|---|
| clip: level-1 MILP | 18 s, certified | 14 s, certified | 1.4 s, certified | 84 s, certified | 49 s, certified | 150 s, certified |
| draw | 8 to 12 s | 8 to 12 s | 8 to 12 s | 8 to 12 s | 8 to 12 s | 8 to 12 s |
| geom export | < 1 s | < 1 s | < 1 s | < 1 s | < 1 s | < 1 s |

Wall clock: 163.5 s, down from 614 s before the portfolio strategy; k=20 alone is the long pole
at 150 s.

Two standalone cells, run with no other chain competing for the machine: k=20 closes fully in
70 s (SCIP finds 10 splits at 47 s, the proof takes 0.2 s, the tie-break 11 s); k=16 certifies
7 splits in 82.7 s (the certificate "no 6-split map" is not LP-infeasible outright, so SCIP
proves it in 24 s during a cutoff round against HiGHS's 74 s), tie-break left open at the 30 s
cap.

MILP engine bench (`tools/bench/milp_bench.py`, `tools/bench/README.md`), real instance, delta
0.10, cap 180 s, same machine (`battery/results/bench/milp_20260909_015338.json` k=20,
`milp_20260909_020619.json` k=18):

| variant | k=20 | k=18 |
|---|---|---|
| scipy (the old engine) | 12 splits, gap 5.2 %, cap | 7 splits, gap 1e-5, cap |
| highs, 12 threads | 10 splits at 142 s, gap 1.7 %, cap | 8 splits, gap 1.8 %, cap |
| highs, roots fixed | 11 at 6.5 s, 10 at 130 s, gap 0.85 %, cap | 7 proven, 27.8 s |
| scip, roots fixed | 10 at 44 s, gap 1.6 %, cap | 7 proven, 47.5 s |
| lp-heur | 93 splits (useless) | 65 splits (useless) |
| cpsat (`.venv-opt`) | 10 at 79 s, own proof 170 s | 7 proven 124 s |
| highs-root + cutoff Σz ≤ S + s* − 1 | infeasible in 0.1 s: 10 is optimal | infeasible 0.1 s |
| highs-root, warm from a 10-split map | proven 19.1 s | proven 5.9 s |

The root fix lifts the k=20 LP relaxation bound from 58.005 to 58.50, so the 9-split cutoff is
LP-infeasible. HiGHS `mip_heuristic_effort=0.5` finds 10 splits at 78 s plain (130 s default)
and 96 s under the cutoff (255 s). A zero-objective feasibility solve finds nothing in 120 s
(CLAUDE.md trap 19).

The next lever is a k-weighted thread split across the grid's six chains, so k=20 gets more
threads than k=10; not done.

## Scenario exploration goes through the app, not a new artifact

When the question is "what does this scenario do" — pin a region, change k, try a different
engine — define it in the Streamlit app and run it there. The app writes the same
`k<kk>/draw.csv` + `metrics.json` that the drivers do, into
`battery/results/app/<scenario>_<timestamp>/`, and renders the maps with `tools/us_maps.py`, so
nothing about the numbers or the figures changes; what changes is that the sponsor can turn the
knobs without a session, and every scenario is saved to `battery/scenarios/<slug>.json` in the
format `run_draw.py --scenario` already accepts.

Build a Claude artifact (`tools/verify/runs/build_artifact.py`) only for a **fixed deliverable**
— a catalogue that is finished, reviewed, and meant to be cited, like the pin-cost catalogue. An
artifact is a snapshot with no engine behind it, so it cannot answer the next question; the app
can. New exploratory work should not add one.

`run_atoms.py` **requires** `PYTHONHASHSEED=0` and refuses to start without it: its search
tie-breaks on set iteration over atom names, so the answer moves by about 0.015 nats under a
different hash seed. `us_maps.py --districts` reads its `draw.csv`; `--regions` does not apply,
since atom districts are not a power diagram.

The v1 runs reproduce by swapping the instance and draw back and adding
`--gate-reference 60.6974156139` to `frontier.py`. The two catalogue shell scripts date their
output directory by `date +%Y%m%d`, so a re-run lands in `runs_<today>`. `us_maps.py` also emits
the four base figures into `--out`; ~3 s per k with the gazetteer cached.

## Gitignored inputs (repo root; hand-copy into a `.claude/worktrees/<name>` worktree)

`.venv-app` is per-worktree and is rebuilt, not copied:
`uv venv --python 3.13 .venv-app && uv pip install --python .venv-app/bin/python3 -r app/requirements.txt`.
The app reads its data from the hub checkout (`TD_REPO`), so the gitignored inputs below do not
need copying for it.


`instance_descaled_v2_conus.json.gz` (**live since 2026-09-07**, v2 minus the 32 blank-state,
2 AK and 1 HI zips; `docs/PROBLEM.md` §6) · `battery/results/draw_k18_v2conus_20260907` (its
k = 18 draw) · `instance_descaled_v2.json.gz` (v2, whole instance) · `instance_descaled_v2.raw.json.gz`
(uncleaned, provenance) · `instance_descaled.json.gz` (v1, regression only) · `data/geo/` (the
gazetteer cache) · `data/tiger/2025/tl_2025_us_zcta520.*` (the real ZCTA boundaries
`tools/geom_export.py` hard-depends on, 822 MB, local only, never fetched; a worktree that does
not copy it points `TD_ZCTA_SHP` at the hub's copy, which is also the built-in fallback) ·
`battery/results/`: **v2** `draw_k18_v2_20260904`, `u8_band_v2_20260904`,
`meas_v2_20260904`, `runs_20260904/` (the 15 catalogue runs); **v1** `draw_k13_20260901`,
`sweep_20260902_s10`, `meas_20260903`, `u8_band_20260904`.
