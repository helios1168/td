# Scenario app, round 2: scenarios as the unit, rep territories, scoped staffing

Track `worktree-app2`, worktree `.claude/worktrees/app2`, created 2026-09-08. This file is the
track's running log (CLAUDE.md, Docs discipline) and carries the approved plan in full below.
A durable copy of the plan lives at `~/.claude/plans/lets-plan-updates-to-reflective-bachman.md`.

## Goal

The six asks in `## Context` below, delivered on this branch, tests at 0 fail, then offered
for a fast-forward merge into `main`.

## Next step

Wave 3: W3 docs agent running; the MILP bench (k=20 then k=18, cap 180 s) running in the
background; W3b adoption starts when the bench JSON is read. Then the scenario-launch check
(verification item 4) once the bench has released the CPU.

## Done

- 2026-09-08 wave 2 (`dc5e583`): sidebar scenario picker and filtering, rep territories on
  the Map tab, Reps tab map-first with scoped staffing and both before/after views, Timings
  tab, staff and rep_export instrumented, AppTest smoke test, root-fix claim VERIFIED
  (`tools/verify/milp_root_fix/`, guard: root only anchors that survive release). Bench
  interim at k=20, 180 s: scipy 12 splits gap 5.2 %; highs (12 threads) 10 splits gap 1.7 %;
  highs-root 10 splits gap 0.85 %.
- 2026-09-08 wave 1 (`a042e11`): main.py split, scenario ledger, rep_export.py, staff
  --districts, rep/staffed figures, repdata, staffdiff, telemetry, milp_engines and bench,
  `.venv-opt` (ortools 9.15.6755). Real rep export: 107 territories, 0.82 MB, under a minute.
- 2026-09-08: plan approved; worktree created and locked; palettes validated with the
  `dataviz` script. Five-kind Gantt palette `#2563eb #d97706 #059669 #7c3aed #dc2626` passes
  (CVD warn 7.9 on green/orange, covered by the bars' direct kind labels). The four-step
  `n` ramp `#f1f5f9 #a5b4fc #6366f1 #312e81` is sequential, lightness monotone, kept; class 0
  markers take a `#94a3b8` 1 px outline so they stay visible on the surface.

## Decisions needed

- Merge into `main` when the track is done (user's call, memory: ask before merging to hub).
- W4 go/no-go is settled in advance by the bench acceptance (k=20 proven in under 120 s).

## Files owned / forbidden

Owned: everything each workstream lists under "Owns" below, plus this file. Forbidden:
`docs/foundations/`, `battery/figures/`, `STATE.md` (stamped by `/state` from the hub only),
any `docs/*.md` not listed in a workstream.

## Context

The app (`app/`, merged 2026-09-08 as `cdc2583`) treats every run directory as a peer: the
Map, Reps, Overrides and Compare tabs each open a flat picker over all 30-odd runs under
`battery/results/app/`, named `<kind>_k<kk>_<stamp>`. A grid launch creates six draw/clip/geom
chains with nothing tying them together. Three asks:

1. **Scenarios as the unit.** A grid launch gets a user-typed name; its members are named
   `<name>_k<k>_d<delta%>` (`custom_k10_d5`); every other tab defaults to the newest scenario
   and its pickers list that scenario's runs only.
2. **Rep territories on the Map tab.** A new section drawing how the 113 incumbent reps'
   sales are laid out over the 3,713 CONUS zips. 42 % of zips have no rep, 39 % one, 19 % two
   or more (max 5). The app never opens the instance, so a solver-venv driver must export the
   layout as ratios and polygons first (APP.md invariant 4: no masses leave `draw.csv`).
3. **Reps tab opens on that map with the proposed districts drawn over it**, and staffing
   (`tools/staff.py`, Hungarian on `-log g`) can be run on one district or a chosen subset.
4. **Before and after the Nash staffing**, at two levels: the whole map (incumbent layout
   beside the staffed map, one table per rep) and one district (its zips as sold today
   beside its staffed state, zoomed). Added by the user after the first plan draft.
5. **Telemetry.** Measure and profile every step of a chain, the optimisation steps above
   all, and show the numbers in the app.
6. **End-to-end runtime.** Cut the time from "Launch grid" to six finished maps, using the
   machine (Apple M2 Max, 12 CPU cores, 30 GPU cores, 32 GB) and any language or library
   that helps.

### Runtime today (grid of 2026-09-08 14:42, k = 10 to 20, delta 0.10, 5 seeds, 2 workers)

| step | k=10 | k=12 | k=14 | k=16 | k=18 | k=20 |
|---|---|---|---|---|---|---|
| draw (stage 1 + stage 2, per chain) | 9 s | 9 s | 11 s | 12 s | 11 s | 10 s |
| clip: level-1 MILP (`state_splits.solve`) | 16.5 s | ~150 s | ~3 s | 600 s cap | 600 s cap | 600 s cap |
| clip: balance pass + level-2 realise + stage 2 + tables | < 1 s | < 1 s | < 1 s | < 1 s | < 1 s | < 1 s |
| geom export | ~2 s | ~2 s | ~2 s | ~2 s | ~2 s | ~2 s |
| chain end to end | 27 s | 2.5 min | 14 s | 10.2 min | 10.2 min | 10.2 min |

The six chains already run in parallel, so the grid's wall clock is the slowest MILP plus
about 15 s: 10 min 14 s, set by the time limit. At k=20 HiGHS (through `scipy.optimize.milp`,
single-threaded, no warm start, no callbacks) stops at objective 59.005 with dual bound 58.0:
the incumbent has 10 splits and the solver cannot rule out 9. The gap is one whole split,
not the epsilon tie-break, so the fix is a stronger bound (formulation or solver), not an
early-exit rule. The MILP is small (S=49 states, k=20: 980 `z` + 980 `r` binaries, 980 `y`
and 4,280 flow continuous; the connectivity is a single-commodity flow with big-M `N-1 = 48`,
which is why the LP relaxation is weak).

**GPU.** Nothing here is GPU-shaped: the two solvers are branch-and-bound and simplex (no
Metal or MPS implementation exists; NVIDIA cuOpt is CUDA-only), Voronoi and dissolve are
already C++ (GEOS through shapely), and the largest dense array is 3,704 × 20 distances.
The machine's resource for this work is its 12 CPU cores, which the plan uses through
parallel chains and solver threads. Python packages `torch`, `mlx`, `ortools` are absent
from `.venv`; `pyscipopt` (SCIP) and `highspy` (HiGHS direct) are present.

**Continuous or smooth proxies for the MILP** (user question, 2026-09-08). The objective is
a cardinality (states split) plus per-district connectivity on the state rook graph. A
continuous surrogate (reweighted L1 on relaxed `z`, concave or log-sum penalties as a
sequence of LPs, a smooth NLP solve) reaches a good integer-ish point in milliseconds but
certifies nothing about the count, and connectivity has no natural smooth proxy. The
measured gap is dual-sided (incumbent 10, bound 9 at k=20), so the exact levers are bound
strength and search; the continuous methods enter as the primal side (warm starts,
incumbents). Decisions with the user: bench the cheap exact levers plus the heuristics
first; the lazy-cut formulation is a follow-on only if k=20 stays above 120 s; new solver
packages go into a third venv `.venv-opt` behind an out-of-process engine seam; no Gurobi
licence, so open-source engines only.

Decisions taken with the user (2026-09-08): split `app/main.py` into per-tab modules first;
rep map = dominant-rep fill with a hatch over contested cells; scoped staffing keeps the
whole-map candidacy rule (every kept rep with book in the district), no exclusion of reps
staffed elsewhere.

Assumptions recorded, not asked: the user's "instance" (a member of a scenario) collides
with the code's `instance` (the `.json.gz` data file). UI labels: the Scenarios tab data-file
picker becomes "Instance file"; the member picker on the other tabs is labelled "Instance".
Code keeps `instance` for the file and uses `member` for the scenario member. One delta per
scenario, as today. The subset for scoped staffing is a district multiselect, defaulting to
the district of the zip last clicked on the Map tab.

## Parallelisation strategy

Sonnet subagents from this session, in waves, inside one plain-git worktree. Not separate
sessions: the work is disjoint by file, needs no cross-session messaging, and one commit
stream after each wave is simpler than merging branches. Agents do not commit; the main
session reviews each wave's diff, runs the tests, commits. Separate sessions would pay off
only for work outliving one context window or needing its own worktree; nothing here does.

Worktree: `git worktree add .claude/worktrees/app2 -b worktree-app2` then lock, enter by
path (CLAUDE.md §9). Hand-copy nothing: the app reads gitignored inputs from the hub via
`config.REPO`, and `.venv`/`.venv-app` are the hub's.

## Contracts (fixed here so parallel agents agree)

### Run naming and the scenario ledger (`app/store.py`)

- Scenario slug: user text lowercased, `[^a-z0-9-]` → `-`, collapsed, stripped; empty →
  `grid-<YYYYmmdd>-<HHMM>`. Underscores become hyphens so `_k(\d+)_` and `_stamp` keep
  parsing directory names.
- Member name: `f"{slug}_k{k}_d{dpct:g}"` with `dpct = round(delta * 100, 4)`; k unpadded
  (`custom_k8_d5`, `custom_k10_d5`, `custom_k10_d7.5`).
- Run directory: `f"{member}_{kind}_{stamp}[-n]"`, e.g. `custom_k10_d5_clip_20260908_181500`.
  `store.new_run_dir(root, kind, member)` replaces the `k` argument; `_stamp` (last two `_`
  parts) and `discover` are unchanged. `k_of`'s regex fallback becomes `_k(\d+)_`, already so.
- `step.json` gains two fields: `"scenario": slug`, `"member": member`. Children written by
  `launch_child` copy both from the parent's step (`store.scenario_of`, `store.member_of`
  walk the lineage like `k_of`; a run with neither anywhere in its lineage returns `None`).
- `store.label(run, root)` → `f"{member} · {kind} · {when}"`; legacy runs (no member) fall
  back to today's `k18 · clip · when`.
- `store.scenarios(root) -> list[tuple[str | None, list[Path]]]`: slugs newest-first by the
  newest run each holds, legacy runs grouped under `None` last. Scenario definition is not
  stored separately: it is the union of the member draws' `params` (`k`, `delta`, `theta`,
  ...), already recorded by `steps.grid`.
- `steps.grid(..., name: str)` writes `scenario` and `member` into both the draw and clip
  steps; `params` of the draw and clip additionally carry `scenario_name` (the raw text).

### `reps.json` (written by the new `tools/rep_export.py`, read by `app/repdata.py` and `app/mapfig.py`)

Location: `config.REP_CACHE / <instance stem> / reps.json` with `REP_CACHE = RESULTS /
"app_reps"`, outside `APP_RESULTS` so `store.discover` never lists it. The directory carries a
minimal `step.json` (`kind: "reps"`, `parent: None`, `params: {instance}`, `outputs:
{"reps": "reps.json"}`) so `runner.launch`, `store.status` and `runner.log_tail` work
unchanged.

```
{"crs": "laea",
 "instance": "instance_descaled_v2_conus.json.gz",
 "reps": ["R0022", ...],                                   # model.reps order
 "book_share": {"R0022": 0.0123, ...},                     # rep's share of the whole channel
                                                            # book, sums to 1 - free_share
 "free_share": 0.004,
 "zips": {"01001": {"top": "R0022" | "", "shares": {"R0022": 0.61, "R0068": 0.39},
                    "free": 0.0, "n": 2, "weight": 0.00031}, ...},
                                                            # shares: of the zip's own book,
                                                            # sum(shares)+free == 1 (or all 0)
                                                            # weight: the zip's share of the
                                                            # whole channel book, sums to 1
 "territories": {"R0022": {"rings": [[[x,y],...],...], "color": "#rrggbb"}, ...},
                                                            # cells dissolved by `top`
 "footprints":  {"R0022": {"rings": [...]}, ...},          # cells of every zip with book>0
 "contested":   {"rings": [...]},                          # union of cells with n >= 2
 "states": {... same shape as geom.json ...}}
```

Ratios and identifiers only (`weight` and `book_share` are shares of one unknown total, the
same kind of number `staffing.json`'s `share` already is). Coordinates in the table's LAEA metres, exterior rings only,
simplified 2000 m, exactly `geom_export._rings`. Colours: `geom_export.palette()` assigned
by `us_maps.color_districts` over `geom_export._adjacency(territories)`, so two touching
territories never share a hue (113 reps over 50 entries: repeats sit far apart, same
promise `geom.json` makes). Voronoi cells are built over every zip (untapped zips included,
so no territory swallows empty ground) with the per-state clip `geom_export.export` already
uses; untapped cells are dissolved into nothing and stay unfilled.

### Telemetry (`td/telemetry.py`, no third-party imports)

```python
T = telemetry.Timings("clip")                 # driver name
with T.phase("load"): ...                     # nestable; a phase inside a phase gets depth 1
with T.phase("solve") as ph:
    ...
    ph.note(nodes=res.mip_node_count, dual_bound=..., gap=res.mip_gap, status=...)
T.tick("lp.assign", seconds)                  # accumulate many small calls under one name
T.write(out_dir)                              # <out_dir>/timings.json
```

`timings.json`:
```
{"driver": "clip", "argv": [...], "started": iso, "finished": iso, "wall": s,
 "cpu": s (process + reaped children), "rss_peak_mb": float,
 "phases": [{"name": "solve", "depth": 0, "start": s-from-driver-start, "wall": s,
             "cpu": s, "note": {...}}, ...],
 "ticks":  {"lp.assign": {"n": 42, "wall": s}}}
```

Every driver writes one next to its outputs and `step.json.outputs["timings"] =
"timings.json"` (set by `steps.grid` for draw and clip, by `launch_child` for children, by
`repdata.ensure` for the rep export). `TD_PROFILE=1` in the environment makes
`Timings.write` also dump `cProfile` stats to `<out_dir>/profile.prof` (profiling wraps
the driver's `main`, enabled in every driver through one `telemetry.maybe_profile(main)`
call). Sampling profiles of a running solve use `py-spy` (a Rust binary, wheel on PyPI,
installed with `uv tool install py-spy`, never into `.venv`): `py-spy record -o out.svg
--pid <pid>`; recipe in APP.md §7.

Phase names, fixed so the Timings tab can line chains up:
- draw: `load`, `coordinates`, `stage1` (with per-job ticks `lp.assign`, `improve`,
  and a note `jobs`, `workers`), `stage2`, `write`.
- clip: `load`, `build_milp`, `solve` (note `status`, `nodes`, `gap`, `dual_bound`,
  `objective`, `time_limit`, `engine`), `balance_pass`, `realise` (ticks `lp.assign`
  per state round), `stage2`, `write`.
- geom: `load`, `voronoi`, `dissolve`, `colour`, `write`.
- staff: `load`, `books`, `gain_matrix`, `assign`, `write`. split: `load`, `greedy`, `scip`,
  `write`. reps: `load`, `shares`, `voronoi`, `dissolve`, `footprints`, `write`.

### MILP engine bench (`tools/bench/milp_bench.py`)

Builds the real level-1 problem (`state_splits.build_milp` on the instance and a chosen
draw table, exactly as `tools/state_splits.py main` does, `--anchor-homes` on) for k in
`--ks`, then runs each variant under `--cap` seconds and records
`battery/results/bench/milp_<stamp>.json`: `{k, variant, status, objective, dual_bound,
gap, splits, seconds, nodes, trajectory: [[t, primal, dual], ...]}`. Variants:

| variant | what | exact? |
|---|---|---|
| `scipy` | today's `state_splits.solve`, the baseline | yes |
| `highs` | `highspy` direct, `threads=12`, `mip_rel_gap=0`, logging callback for the trajectory | yes |
| `highs-root` | `highs` plus roots fixed: with `--anchor-homes` every district has a home state, so `r_{home(j), j} = 1` and the other `r_sj = 0` (a connected set can be rooted at any member, so no optimum is lost; math-verify confirms before adoption) | yes |
| `scip` / `scip-root` | `pyscipopt`, default emphasis, same matrix, `misc/allow{strong,weak}dualreds` left on (no lazy separation here) | yes |
| `lp-heur` | successive LPs: relax `z`, minimise `Σ w_sj z_sj` with reweighted-L1 weights `w = 1/(z_prev + ε)` for up to 10 rounds, round `z`, solve the `y` LP (`balance_pass`) for feasibility, repair by re-opening the cheapest `z` when infeasible. Milliseconds. Reports its split count as an upper bound only | no (primal) |
| `cpsat` | OR-Tools CP-SAT, 12 workers, `y` and the flow discretised to 1e-4 units with integer-scaled band coefficients. Its optimum is an upper bound on the true count (discretising `y` restricts the feasible set) and its proof covers the discretised problem only; reported as primal engine | no (primal) |
| `*-cutoff` | for `highs-root` and `scip-root`: take the best incumbent `s*` from any variant, add `Σ z ≤ S + s* − 1` and ask for feasibility. A proof that no `s* − 1` map exists is the certificate; usually far faster than closing a gap | yes |
| `*-warm` | for `highs-root` and `scip-root`: MIP start from `lp-heur` or `cpsat`, to measure how much of the time is bound and how much search | yes |

No Gurobi (no licence). A lazily separated cut formulation (component-wise separator cuts,
trap 13, dual reductions off, trap 14) is W4, conditional: built only if the bench leaves
k=20 above 120 s to proven optimality.

### Engine seam and the solver venv

`td/solvers/milp_engines.py`: `solve_problem(problem: SplitProblem, engine: str, *,
time_limit, cutoff=None, warm=None, threads=None) -> dict` with the same return shape as
`state_splits.solve` plus `nodes`, `dual_bound`, `trajectory`, `engine`. In-process
engines: `scipy`, `highs` (`highspy` is in `.venv`), `scip` (`pyscipopt` is in `.venv`).
Out-of-process engines (`cpsat`, and anything else installed later): the problem's arrays
go to a `.npz` in a temp dir, `.venv-opt/bin/python3 -m td.solvers.milp_worker <npz>
<json-out>` solves it and writes the solution JSON, the seam reads it back. `.venv-opt` is
built from `tools/bench/requirements-opt.txt` (`ortools` pinned to the current release,
`numpy`); it never imports `td` beyond `milp_worker`'s own array handling, so the frozen
`.venv` pins and the zip50 anchor are untouched. `config.OPT_PYTHON = REPO / ".venv-opt" /
"bin" / "python3"`, overridable by `TD_OPT_PYTHON`.

### `tools/staff.py --districts D01,D05`

Optional. Restricts `to_district` to those districts before `district_books` and
`gain_matrix`; unknown name → `sys.exit`. Output `draw.csv`: rows in scope take the
assignment, rows out of scope keep the `rep` they arrived with. `staffing.json` gains
`"districts": [...]` (the scope, or every district when the flag is absent); `k`, `balance`
stay whole-table. `steps.staff_argv(..., districts=None)` appends the flag when given.

### Figure trace names (`app/mapfig.py`)

Existing constants stay. New: `REP_FILLS` (one trace per territory, `name=rep`),
`CONTESTED` (one hatched trace, `fillpattern=dict(shape="/")`, `hoverinfo="skip"`),
`FOCUS` (one filled trace, the focused rep's footprint), `DISTRICT_LINES` (one line trace,
every district ring joined by `None`), `REP_ZIPS` (one `Scattergl`, small uniform markers,
hover only). Hover on `REP_ZIPS`: `zip · state / district Dxx / R0022 61 %, R0068 39 % / free
0 %`. No legend for 113 reps; identity comes from hover and the focus selector, and the
"colour by reps with book" mode carries a 4-step legend (0, 1, 2, 3+; one hue, light to
dark, `#f1f5f9 #a5b4fc #6366f1 #312e81` or any validated one-hue ramp).

Staffed ("after") figure, `mapfig.staffed_figure(rows, geom, rep_colours, *, staffing,
bbox=None)`: state outlines; `STAFFED_FILLS` (one trace per district, filled in the assigned
rep's colour from `rep_colours`, opacity 0.55, `name=district`); `UNSTAFFED` (districts with
no assignment, light grey with the same `/` hatch, one trace); `SPLIT_ZIPS` (a `Scattergl` of
the zips whose `rep` differs from their district's assignment, coloured per rep, size 6, only
present after a split); `REP_ZIPS`-style hover markers carrying `zip · state · district ·
rep`; `HANDLES`. `rep_colours` is `{rep: hex}` taken from `reps.json["territories"]` so a rep
keeps one hue across the before and the after (dataviz: colour follows the entity); a rep
with no territory takes the next unused palette entry. `bbox=(x0, y0, x1, y1)` sets the axis
ranges for the district-level pair; `rep_figure` takes the same keyword. Both figures set
`uirevision` to the bbox so pan and zoom persist across reruns.

Before/after arithmetic, `app/staffdiff.py` (no streamlit, no pandas, no plotly):
`per_rep(reps, rows, staffing) -> list[dict]` with keys `rep`, `before` (`book_share`),
`after` (sum of `weight` over the zips of the rep's assigned districts, or of the zips the
split table labels with the rep), `districts` (list), `change` (`after - before`);
`summary(reps, rows, staffing) -> dict` with `reps_with_territory_before`,
`reps_with_territory_after`, `contested_weight_before` (weight of zips with `n >= 2`),
`contested_weight_after` (weight of zips inside a district whose zips carry two or more
reps, so 0 without a split), `free_weight_before`, `unstaffed_weight_after`;
`district_view(reps, rows, staffing, district) -> dict` with `before` (`{rep: weight of the
zips where rep is top}` inside the district, plus `contested` and `untapped` weights) and
`after` (`{rep: weight}` from the table's `rep` column inside the district), all normalised
to the district's own weight so both sides sum to 1.

## Workstreams (each owns exactly the files listed; touch nothing else)

### W0. Split `app/main.py` into modules (mechanical)

Owns: `app/main.py`, new `app/common.py`, `app/tab_scenarios.py`, `app/tab_map.py`,
`app/tab_reps.py`, `app/tab_overrides.py`, `app/tab_compare.py`.

- `common.py`: the module docstring's shared part, `MAP_KINDS`, `FILLERS`, `FAILURE_TEXT`,
  `OTHER_FAILURE`, `MODES`, `parse_ks`, `pins_from_table`, `_rows`, `_geom`, `_stamp`,
  `runs_frame`, `show_failure`, `_json`, `_figure`, `map_runs`, `label_run`, `k_for`,
  `pick_map`, `open_on_map`, `instance_of`, `newest_child`, `launch_child`.
- One `render_*` family per tab file; `main.py` keeps `set_page_config`, `title`, `st.tabs`
  and the five `with` blocks (about 30 lines).
- No behaviour change. `git diff --stat` should read as moves. Verify by launching the app
  (`tools/app.sh --server.port 8503`) and clicking every tab once.

### W1a. Scenario ledger

Owns: `app/store.py`, `app/steps.py`, `tests/test_app_store.py`.

- Implement the naming and ledger contract above: `slugify`, `member_name`, `new_run_dir`
  signature, `scenario_of`, `member_of`, `scenarios`, `label`, `grid(name=...)`.
- Tests: slug rules (spaces, underscores, empty), member names for `0.05`, `0.10`, `0.075`,
  directory name shape, `label` for new and legacy runs, `scenarios()` ordering with a legacy
  group, `grid` writing `scenario`/`member` into both steps. Update the existing grid and
  label tests to the new names.

### W1b. `tools/rep_export.py` and its test

Owns: new `tools/rep_export.py`, new `tests/test_rep_export.py`.

- CLI: `rep_export.py <instance> --out DIR [--geo-cache DIR] [--simplify M] [--no-basemap]`.
  Loads through `td.instance.load_descaled`, asserts CONUS (`td.geo.assert_conus`), reads
  `model.books`, `model.free_book`, `model.reps`. Coordinates: build a zip table in memory
  with `td.ziptable.build` (the same route `run_draw.py` takes to get `x, y`), or read them
  the way `geom_export` does; a zip with no coordinates is skipped from polygons but kept in
  `zips`.
- Reuse, do not copy: `geom_export._us_maps`, `_rings`, `_adjacency`, `_parts`, `palette`,
  `write`; `us_maps.clip_region`, `voronoi_cells`, `dissolve`, `color_districts`.
- Test on the toy instance from `tests/test_staff.py` (`_write_instance`, `TOY`) with
  `--no-basemap`: shares sum to one, `top` is the argmax, `n` counts, `weight` sums to one
  over zips, `book_share` plus `free_share` sums to one, `contested` is non-empty only when
  some zip has two reps, `footprints` keys equal `reps`, no raw mass anywhere in the file
  (assert no key named `M`, `S`, `opportunity`).

### W1c. Scoped staffing

Owns: `tools/staff.py`, `tests/test_staff.py`.

- `--districts` per the contract. Test: on `TOY`, scope to one district; assert the
  assignment names only that district, out-of-scope rows keep the input `rep`, unknown
  district refused, `staffing.json["districts"]` equals the scope.

### W1d. Rep figure, staffed figure, rep data loader, before/after arithmetic

Owns: `app/mapfig.py`, new `app/repdata.py`, new `app/staffdiff.py`, `app/config.py`, new
`tests/test_mapfig.py`, new `tests/test_staffdiff.py`.

- `mapfig.staffed_figure` and the `bbox` keyword per the contract. `mapfig.rep_colours(reps)
  -> dict[str, str]` builds the shared `{rep: hex}` map (territory colour, else next unused
  palette entry) so both tabs call one function.
- `app/staffdiff.py` per the contract, pure Python. `tests/test_staffdiff.py` (solver venv,
  no plotly): a 6-zip, 3-rep, 2-district fixture built inline; asserts `per_rep` sums,
  `summary` counts, `district_view` sides each sum to 1, a split table moves weight between
  reps inside one district and leaves the other district's `after` untouched.

- `mapfig.rep_figure(reps: dict, rows: list[dict] | None, geom: dict | None, *,
  colour_by="rep" | "n", focus_rep="", show_contested=True, district_lines=True) -> go.Figure`.
  Layers in order: state outlines; `REP_FILLS` (opacity 0.45, thin border in the fill
  colour); `CONTESTED` hatch (opacity 0.5, grey `#444`); `FOCUS` (opacity 0.7, `#111`
  border 1.5); `DISTRICT_LINES` from `geom["districts"]` (colour `#111`, width 1.8) when
  `geom` given; `REP_ZIPS` markers (size 4, colour `#333`, opacity 0.6) carrying the hover;
  `HANDLES` as today. `colour_by="n"`: `n` is a per-zip count and `reps.json` carries no
  per-zip cells, so this mode draws `REP_FILLS` as light grey outlines only and colours the
  `REP_ZIPS` markers (size 6) from the 4-step ramp, with a legend of the four classes. Same
  layout block as `figure` (`scaleanchor`, no axes, `uirevision="rep-map"`).
- `repdata.py` (imports streamlit): `reps_dir(instance) -> Path`, `reps_path(instance) ->
  Path | None`, `load(path, mtime)` under `st.cache_data`, `ensure(instance) -> dict | None`
  that returns the loaded file or, when absent, renders a "Build rep territories" button
  which writes the minimal `step.json` and calls `runner.launch` with
  `steps`-style argv (`[SOLVER_PYTHON, CODE/tools/rep_export.py, instance, "--out", dir,
  "--geo-cache", GEO_CACHE]`); while `store.status` reads `running`, shows the log tail.
- `config.py`: add `REP_CACHE = RESULTS / "app_reps"`.
- `tests/test_mapfig.py`: gated `try: import plotly except ImportError: plotly = None` and
  every test returns early when `plotly is None` (the solver venv has no plotly; run it by
  hand with `.venv-app/bin/python3 tests/run_all.py -k mapfig`). Asserts trace names and
  order for `rep_figure` with and without `geom`, `focus_rep`, `colour_by="n"`; for
  `staffed_figure` with an unstaffed district, with a split table (`SPLIT_ZIPS` present) and
  with a `bbox` (axis ranges set); and that `rep_colours` gives one rep the same hex in both
  figures.

### W1e. Telemetry core and driver instrumentation

Owns: new `td/telemetry.py`, new `tests/test_telemetry.py`, `tools/run_draw.py`,
`tools/state_splits.py`, `td/solvers/state_splits.py` (only `solve`: add the `note`
fields to its return, `nodes` from `res.mip_node_count`, `dual_bound` from
`res.mip_dual_bound`), `td/solvers/centers.py` (only a `telemetry.tick("lp.assign", dt)`
around the `linprog` call in `assign`, through a module-level hook that is a no-op when no
`Timings` is active, so library code stays import-clean), `tools/geom_export.py`,
`tools/split_district.py`.

- `telemetry.py` per the contract: `Timings`, `phase`, `tick`, `note`, `write`,
  `maybe_profile`, `current()` (the active `Timings` for the hook), all stdlib.
- Tests: nesting depth, tick accumulation, `write` round trip, `maybe_profile` writes
  `profile.prof` only under `TD_PROFILE=1`, the hook is a no-op with no active `Timings`.
- Existing driver tests must still pass; every instrumented driver writes `timings.json`
  (assert its presence in one existing end-to-end test per driver, one line each).

### W1f. MILP engines, bench and the solver venv

Owns: new `td/solvers/milp_engines.py`, new `td/solvers/milp_worker.py`, new
`tools/bench/milp_bench.py`, new `tools/bench/requirements-opt.txt`, new
`tools/bench/README.md`, new `tests/test_milp_engines.py`, `app/config.py` (only the
`OPT_PYTHON` line; W1d owns the rest of that file and adds `REP_CACHE`; the two lines do
not touch).

- Engine seam per the contract. `highs` through `highspy.Highs().passModel` from `A`, `c`,
  bounds, integrality; `scip` through `pyscipopt` from the same arrays; `cpsat` in
  `milp_worker` from the `.npz`. `fix_roots(problem, anchors)` tightens `var_lb`/`var_ub` on
  the `r` block; `with_cutoff(problem, s_star)` appends one row `Σ z ≤ S + s* − 1`;
  `lp_heuristic(problem)` per the contract; all three are pure functions on `SplitProblem`.
  Trajectory via `highspy` callbacks, SCIP's event handler on `BESTSOLFOUND` plus a
  one-second poll of the dual bound, CP-SAT's solution callback.
- The bench drives the variants in the order of the table, one process at a time, and
  writes the JSON per the contract; `--variants` selects a subset.
- `.venv-opt`: `uv venv --python 3.13 .venv-opt && uv pip install --python
  .venv-opt/bin/python3 -r tools/bench/requirements-opt.txt`; the agent builds it and
  records the resolved versions in the README. `.venv-opt/` is not gitignored today
  (`.venv-app` is): W1f adds the line to `.gitignore`.
- Tests (solver venv; `cpsat` cases return early when `config.OPT_PYTHON` is absent): on the
  4-state toys in `tests/test_state_splits.py`, every exact variant returns `scipy`'s count;
  `fix_roots` leaves it unchanged; `with_cutoff(s* − 1)` on an optimal `s*` is infeasible
  and on `s*` feasible; `lp_heuristic` returns a feasible `z` with count `≥ s*`; the worker
  round-trips a problem through the `.npz` and JSON.
- The real run is the main session's (long pole below), not the agent's.

### W2a. Sidebar scenario picker, Scenarios tab naming, Overrides and Compare filtering

Owns: `app/common.py`, `app/tab_scenarios.py`, `app/tab_overrides.py`, `app/tab_compare.py`.

- `common.current_scenario() -> str | None`: renders `st.sidebar.selectbox("Scenario", ...)`
  over `store.scenarios(config.APP_RESULTS)` (legacy group shown as "older runs"), default
  index 0 (newest), key `"scenario"`. Honours `st.session_state.pop("scenario-pending")` by
  writing the key before the widget is built (same reason `open_on_map` is a callback).
  Called once in `main.py` before the tabs (W2a also owns that one line in `main.py`; W0 is
  finished before W2 starts).
- `common.map_runs(scenario)` and `pick_map(label, key)` filter by the current scenario;
  `pick_map`'s label becomes "Instance" and its `format_func` `label_run`.
- Scenarios tab: `st.text_input("Scenario name", placeholder="custom")` above the k field;
  data-file picker relabelled "Instance file"; launch passes `name=` to `steps.grid`, then
  sets `scenario-pending` to the slug and `st.rerun()`. The runs table gains `scenario` and
  `instance` (member) columns and is filtered to the current scenario with a "show every
  scenario" toggle.
- Overrides: `pick_map` already; nothing else. Compare: A and B lists are the scenario's
  runs; defaults unchanged (index 1 and 0).
- `launch_child` adds `"timings": "timings.json"` to `outputs`. `main.py` gains the sixth
  tab, "Timings", calling `tab_timings.render_timings()` (W2d writes the module).
- The runs table gains a `wall (s)` column read from `timings.json` when present.

### W2d. Timings tab

Owns: new `app/tab_timings.py`.

- Scenario Gantt: one row per member, one bar per chain step (draw, clip, geom, and every
  child), x from `step.started` to `started + timings.wall`, colour by step kind (five
  kinds, fixed order, a categorical palette validated with the `dataviz` script), hover
  shows the phases. Read `timings.json` through a `st.cache_data` loader keyed on
  `(path, mtime)`; a run without one shows a hollow bar labelled "no timings".
- Per-run detail: pick a run (default the scenario's slowest), show a horizontal bar per
  phase (depth 0 and 1), the `solve` note as metrics (status, gap, nodes, dual bound), the
  `ticks` table, and, when `profile.prof` exists, a `pstats` top-25 by cumulative time in an
  expander (`pstats` is stdlib; the app venv has it).
- Scenario summary line: total wall of the slowest chain, the step that set it, and the sum
  of CPU seconds across the scenario against wall clock as a parallelism ratio.

### W2e. Instrument the wave-1 drivers that were owned elsewhere

Owns: `tools/staff.py`, `tools/rep_export.py`, `app/repdata.py` (only to add
`outputs["timings"]` to the rep export's `step.json`).

- Phase names per the contract; `timings.json` asserted in one test each
  (`tests/test_staff.py`, `tests/test_rep_export.py` are W1c's and W1b's files: W2e may add
  one assertion line to each, nothing else).

### W3b. Adopt the winning MILP engine

Owns: `td/solvers/state_splits.py`, `tools/state_splits.py`, `tests/test_state_splits.py`,
`tests/test_state_splits_cli.py`, `app/steps.py`, `app/tab_scenarios.py`. Runs only after
the bench numbers are in; scope is set by them:

- `state_splits.solve(problem, *, engine="scipy", strategy="direct" | "primal-then-cutoff",
  time_limit, strict)` delegates to `milp_engines.solve_problem`. `primal-then-cutoff` runs
  the winning primal engine (`lp-heur` or `cpsat`) for its incumbent `s*`, then the winning
  exact engine on `with_cutoff(s* − 1)`: infeasible proves `s*` optimal and the incumbent's
  `y` goes to the balance pass; feasible means a better map exists and the exact engine
  continues from that point with the plain objective. `status` stays `0`, `time_limit` or
  a `SolveFailure` reason, so the app's failure texts still apply.
- `build_milp(..., fix_roots=True)` once math-verify has confirmed the root fix; `--engine`,
  `--strategy`, `--no-fix-roots` flags on `tools/state_splits.py`; `steps.clip_argv` passes
  them; a Scenarios tab selectbox defaults to the bench winner; `config.TIME_LIMIT` lowered
  to what the winner needs at k=20 plus margin.
- Certificate rules unchanged: `mip_rel_gap=0` on the exact engine (trap 12); a primal
  engine's count is never reported as optimal without the cutoff proof; a `time_limit` stop
  still reads `status="time_limit"` and the app still shows the gap.
- Tests: the toy problems return the same counts under every engine and both strategies;
  `fix_roots=True` returns the same count as `False` on every toy; the CLI flags reach
  `solve`.

### W4. Lazy-cut connectivity formulation (conditional)

Built only if the bench leaves k=20 above 120 s to proven optimality. Owns: new
`td/solvers/state_splits_cuts.py`, new `tests/test_state_splits_cuts.py`, a `cuts` engine
in `milp_engines.py`. SCIP constraint handler separating component-wise a-b separator cuts
(trap 13: one root per district per component), `misc/allowstrongdualreds` and
`allowweakdualreds` off (trap 14), `ga ≤ Σu·x` form where a gain bound appears. Same
`SplitProblem` interface minus the flow block. A unit brief under `docs/units/` if it goes
ahead, since it changes the certified model.

### W3c. Remaining runtime levers, deferred with numbers

Recorded so nobody re-derives them: stage 1 is 6 to 9 s per chain (5 seeds on 2 workers;
`workers` could default to `min(5, cores // chains)` for a 2× cut of a 9 s step); the
transportation LP in `centers.assign` is sub-second per call and would drop to
milliseconds under a network-simplex solver (OR-Tools `SimpleMinCostFlow`, C++) for a
saving of a few seconds per chain; geom export is about 2 s; instance load is under a
second. None of these moves the grid clock while the MILP is above 60 s. Revisit after
W3b, from the Timings tab.

### W2b. Map tab: scenario-filtered picker plus the rep-territory section

Owns: `app/tab_map.py`.

- Run picker lists `shown` filtered by `common.current_scenario()`; label "Instance".
- New section under the board, `st.subheader("Rep territories, as sold today")`:
  `reps = repdata.ensure(common.instance_of(run))`; controls in one row: colour by (`rep` /
  `reps with book`), focus rep (`""` + `reps["reps"]`), toggles "hatch contested" (on) and
  "overlay this instance's districts" (off). `st.plotly_chart(mapfig.rep_figure(...))` with
  a cache wrapper like `common._figure` keyed on `(reps path, mtime, geom stamp, options)`.
  Caption under it: counts of zips by `n` (0 / 1 / 2 / 3+) read off `reps["zips"]`, as a
  one-line table, and the sentence that hatch marks a cell where two or more reps hold book.

### W2c. Reps tab: map first, scoped staffing

Owns: `app/tab_reps.py`.

- `render_reps` order: picker (`pick_map`), then the rep figure with `district_lines=True`
  and `geom` of the picked run (focus rep selector kept, contested hatch on), then "Kept and
  released", then "Scope", then contest and assignment.
- Scope: `st.radio("Staff", ["the whole map", "these districts"], horizontal=True)`; when
  the second, `st.multiselect("Districts", districts, default=[home])` where `home` is the
  district of `st.session_state["selected_zip"]` if any. The Staff button passes
  `districts=` to `steps.staff_argv`, records `districts` in the child's `params`.
- Staffing to display: replace `newest_child(run, "staff")` with a selectbox over the run's
  staff children (label: `member · staff · time · scope`, scope = "whole map" or the
  district list), default newest. Contest and assignment sections read that staffing; the
  assignment table adds a `scope` caption.
- `render_footprint`: when `reps.json` is loaded, the per-rep option highlights the rep's
  true footprint inside the district (zips where `shares[rep] > 0`) and the caption says so;
  the old "table labelling only" text stays as the fallback.
- **District before/after**, inside the Contestability section under the candidate table,
  for the picked district: two columns, left `rep_figure(reps, rows, geom, bbox=district
  bbox, district_lines=True)` captioned "as sold today", right `staffed_figure(rows_after,
  geom, colours, staffing=staffing, bbox=same)` captioned "after staffing" (or "after
  split" when the newest split child of this staffing for this district has a table, in
  which case `rows_after` is that table). Under the pair one small table from
  `staffdiff.district_view`: rows = reps present on either side plus "contested" and
  "untapped", columns `before`, `after`, `change`, shares of the district's book, formatted
  `%.1%`. The district bbox is the min/max of its zips' `x, y` padded 5 %.
- **Global before/after**, a new section after Assignment, `st.subheader("Before and after
  the staffing")`: the same two-column pair unzoomed (left `rep_figure` with hatch, right
  `staffed_figure` with unstaffed districts hatched grey), then three metric rows from
  `staffdiff.summary` (reps with territory before/after, contested book before/after, free
  book before against unstaffed book after), then the per-rep table from `staffdiff.per_rep`
  sorted by `change`, columns `rep`, `before`, `after`, `change`, `districts`, with a "show
  only reps whose territory changed by more than 1 pt" toggle on by default. The table stays
  in ink colours; rep hue lives on the maps only. Cache both figures through a
  `common._figure`-style wrapper keyed on the reps path, table stamp, staffing stamp and bbox.

### W3. Docs and code map

Owns: `docs/APP.md`, `docs/CODE_MAP.md` (`## Files` rows for `app/`, `tools/rep_export.py`,
`td/telemetry.py`, `tools/bench/`).

- APP.md §4 also: `timings.json` contract and phase names; §5: the Timings tab; §7: the
  `py-spy` and `TD_PROFILE=1` recipes, and the bench's result location. CODE_MAP: the
  runtime table above moves here as the measured baseline, with the bench's numbers beside
  it once W3b has run.

- APP.md §4: run directory naming, `scenario`/`member` fields, `reps.json` contract,
  `staff.py --districts`; §5: the rep and staffed figures' trace order and the shared rep
  colours; §6: a recipe "read the incumbent layout, staff one district, read the before and
  after"; §7: `tests/test_mapfig.py` runs only under `.venv-app`, `app/staffdiff.py` is
  covered from the solver venv.
- CODE_MAP `## Files`: `app/` row lists the tab modules; add `tools/rep_export.py`.

## Verification

1. `.venv/bin/python3 tests/run_all.py` → 0 failed (expect about 440 tests; the mapfig file
   contributes only early-returning passes under the solver venv).
2. `.venv-app/bin/python3 tests/run_all.py -k mapfig` → passes (plotly present, numpy absent
   is fine since mapfig imports neither numpy nor td; if `run_all` itself needs a module the
   app venv lacks, run the file directly with `python3 -c "import tests.test_mapfig as t; ..."`).
3. Real-instance rep export, started as soon as W1b lands:
   `.venv/bin/python3 -u tools/rep_export.py instance_descaled_v2_conus.json.gz --out
   battery/results/app_reps/instance_descaled_v2_conus --geo-cache data/geo`; check the file
   is under 3 MB and `len(territories) <= 113`, `len(zips) == 3713`.
4. Manual, in the worktree on a spare port (`tools/app.sh --server.port 8503`, hub app on
   8502 untouched): launch a scenario named `custom` with `8,10,12` at delta 0.05; the sidebar
   selects it; the Map tab lists `custom_k8_d5 · clip …` only; the rep section renders with
   hatch and focus; the Reps tab opens on the rep map with district lines; staff `D01` alone
   and confirm the child is `custom_k8_d5_staff_<stamp>` with `staffing.json["districts"] ==
   ["D01"]`; Compare offers only the scenario's runs; legacy runs appear under "older runs".
   Then staff everyone: the global before/after pair renders with one hue per rep on both
   sides, the per-rep table's `after` column sums to about 1 minus unstaffed book, and the
   district pair for `D01` zooms to that district with both tables summing to 1. Run a split
   on `D01` and confirm the right-hand district map shows `SPLIT_ZIPS` and the table's
   `after` column moves weight between the two reps.
5. Check the rep figure against `dataviz` anti-patterns before calling W1d done: no legend
   pretending 113 hues are identities, text in ink colours not series colours, one hue for
   the `n` ramp, hover on every zip.
6. Telemetry: after the manual grid in item 4, every run directory holds `timings.json`;
   the Timings tab's Gantt shows three members with draw, clip, geom bars; the clip detail
   shows `solve` with status, gap and nodes; `TD_PROFILE=1 .venv/bin/python3
   tools/geom_export.py --table ... --out /tmp/x` writes `profile.prof` and the tab lists it.
7. Bench: `.venv/bin/python3 -u tools/bench/milp_bench.py instance_descaled_v2_conus.json.gz
   --draw battery/results/app/draw_grid-k20_20260908_144239/k20/draw.csv --ks 18,20 --cap 180`
   writes a JSON with one row per (k, variant); the report names the fastest exact route to
   proven optimality at k=20 (direct, or primal engine plus cutoff proof), or the smallest
   gap at the cap. Acceptance for W3b: k=20 proven optimal in under 120 s; otherwise W4 goes
   ahead.
8. After W3b: relaunch the k = 10 to 20 grid; the Timings tab reports the grid's wall clock;
   target under 2 min end to end (from 10 min 14 s).

## Execution

**Model per step.** Every workstream goes to a Sonnet subagent, prompted with this plan's
contract section plus its own workstream section and the `file:line` anchors below. W1d's
and W2d's agents load the `dataviz` skill before writing a figure. The root-fix claim goes
to the `math-verify` agent (its own model) in parallel with the bench. Design, wave review
(`git diff` per wave, test run, commit), the two real-instance runs (rep export, MILP bench),
reading the bench numbers and the manual app pass stay in the main session (Fable).

**Waves** (file sets disjoint inside each wave; agents do not commit):

| wave | agents (files owned) | gate to next wave |
|---|---|---|
| 1 | W0 (`app/main.py`, `app/common.py`, `app/tab_*.py`) · W1a (`app/store.py`, `app/steps.py`, `tests/test_app_store.py`) · W1b (`tools/rep_export.py`, `tests/test_rep_export.py`) · W1c (`tools/staff.py`, `tests/test_staff.py`) · W1d (`app/mapfig.py`, `app/repdata.py`, `app/staffdiff.py`, `app/config.py` `REP_CACHE` line, `tests/test_mapfig.py`, `tests/test_staffdiff.py`) · W1e (`td/telemetry.py`, `tests/test_telemetry.py`, `tools/run_draw.py`, `tools/state_splits.py`, `td/solvers/state_splits.py`, `td/solvers/centers.py`, `tools/geom_export.py`, `tools/split_district.py`) · W1f (`td/solvers/milp_engines.py`, `td/solvers/milp_worker.py`, `tools/bench/*`, `tests/test_milp_engines.py`, `app/config.py` `OPT_PYTHON` line, `.venv-opt` build) | `run_all.py` 0 fail; app boots after W0; commit; start the rep export and the bench |
| 2 | W2a (`app/common.py`, `app/tab_scenarios.py`, `app/tab_overrides.py`, `app/tab_compare.py`, `app/main.py`) · W2b (`app/tab_map.py`) · W2c (`app/tab_reps.py`) · W2d (`app/tab_timings.py`) · W2e (`tools/staff.py`, `tools/rep_export.py`, `app/repdata.py`, one line each in `tests/test_staff.py`, `tests/test_rep_export.py`) · math-verify (writes only `docs/units/` or a scratch report, per its own rules) | manual pass items 4 to 6; commit |
| 3 | W3 (`docs/APP.md`, `docs/CODE_MAP.md`) · W3b (`td/solvers/state_splits.py`, `td/solvers/milp_engines.py`, `tools/state_splits.py`, `tests/test_state_splits*.py`, `app/steps.py`, `app/tab_scenarios.py`), W3b only once the bench JSON is read | `run_all.py` 0 fail; item 8's grid; `test_docs_owners` passes; commit; report, ask before merge |
| 4 (conditional) | W4 (`td/solvers/state_splits_cuts.py`, `tests/test_state_splits_cuts.py`, the `cuts` engine in `milp_engines.py`, a `docs/units/` brief) | only if item 7 fails its 120 s acceptance; re-bench, then W3b's adoption step repeats for the `cuts` engine |

Serial chains stay inside one agent: `new_run_dir` signature and its callers in `steps.grid`
(W1a); `staff_argv(districts=)` is W1a's file but W1c's flag, so W1a adds the keyword from
the contract and W1c implements the driver side, both against the contract text, no
hand-off. W2b and W2c both import `repdata` and `mapfig.rep_figure` from wave 1, never edit
them. W1e touches `tools/geom_export.py` (instrumentation only) while W1b imports from it:
W1b must not edit that file. W3b waits for the bench, so wave 3's docs agent starts while
the bench is still running and W3b joins when the numbers land.

**Long poles**, both started the moment wave 1 is committed, in the background with
`python3 -u`:

1. The MILP bench at k = 18 and 20, cap 180 s, about ten variant rows per k (the exact
   ones, the two primal ones, and the cutoff and warm combinations), one at a time so the
   timings are clean: worst case about 60 min, likely well under since the primal engines
   and any variant that proves optimality stop early. It is the gate for W3b and nothing
   else waits on it; waves 2 and 3's docs run alongside. It reuses the existing draw tables
   under `battery/results/app/draw_grid-k*_20260908_144239/` and the cached `data/geo`;
   nothing is redrawn.
2. The real-instance `rep_export.py` run (Voronoi over 3,704 points, 113 dissolves, 113
   footprint unions; under a minute expected). It must exist before W2b and W2c are clicked
   through.

**Not delegated.** Choosing the ramp hex values (the `dataviz` validator run, main
session, before wave 1 launches, so W1d and W2d receive validated colours), launching and
reading the two long poles, the go/no-go on W4 from the bench numbers (settled in advance:
go if k=20 is not proven inside 120 s), the wave gates, and the merge question (memory: ask
before merging to hub).

## Anchors for the agents

- Naming today: `app/store.py:26-39` (`new_run_dir`), `:79-82` (`_stamp`), `:96-106`
  (`label`); `app/steps.py:84-131` (`grid`).
- Pickers to filter: `app/main.py:144-148` (`map_runs`), `:166-174` (`pick_map`),
  `:302-318` (Map tab picker), `:765-772` (Compare A/B).
- Launch sites that must record scenario/member: `app/main.py:203-212` (`launch_child`),
  `:429-467` (staff button), `:524-573` (split), `:610-671` (override).
- Reps tab today: `app/main.py:410-426` (`render_reps`), `:470-521` (contest, footprint).
- Figure to extend: `app/mapfig.py:113-201` (`figure`), trace-name constants at the top.
- Driver to extend: `tools/staff.py:128-200` (`main`), `:51-66` (argparser).
- Polygon machinery to reuse: `tools/geom_export.py:93-110` (`_adjacency`), `:122-137`
  (`_rings`), `:140-179` (`export`), `:182-187` (`write`); `tools/us_maps.py` `clip_region`,
  `voronoi_cells` (:803), `dissolve` (:873), `color_districts` (:417).
- Instance access for the driver: `td/instance.py` `load_descaled`; `td/model.py:72-92`
  (`books`, `reps`), `:67-69` (`free_book`); toy instance writer `tests/test_staff.py:56-68`.
- Test conventions: `tests/run_all.py` discovers `tests/test_*.py`, runs every `test_*`
  callable, no pytest fixtures; `tests/test_app_store.py:161-204` is the grid test to update.
- MILP: `td/solvers/state_splits.py:89-125` (`SplitProblem`, variable blocks `z`, `y`, `r`,
  `f`), `:155-290` (`build_milp`; the `root` and `rz` rows at the `r` block are what the root
  fix tightens through `var_lb`/`var_ub`), `:293-334` (`solve`, `scipy.optimize.milp`,
  `mip_rel_gap=0`); `tools/state_splits.py:573-657` (`main/run_cell`, the phases to time:
  `build_milp`, `solve`, `balance_pass`, `realise`, `cell_row`, `write_cell`).
- Stage 1: `td/solvers/centers.py:148-241` (`assign`, the `linprog` call to tick), `:580-666`
  (`draw`, Lloyd loop then `improve`); `tools/run_draw.py:304-323` (`run_sweep`, the process
  pool), `main` for the phase boundaries.
- Existing timing lines to keep: `tools/state_splits.py` prints `solve_s` and `total_s`
  (`run_cell`); `run_draw.py` prints "stage 1: ... in 6.3s". `timings.json` supersedes them
  as the machine-readable record; the prints stay.
