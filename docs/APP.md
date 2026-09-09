# The scenario app: parameter grids, staffing, overrides

A Streamlit application for business users: launch a grid of state-clipped maps over k, staff a
chosen map against the reps' own sales footprints (matching, plus a within-district split), and
override a map by hand. Rebuilt from scratch 2026-09-08; work happens on branch `worktree-app`
in `.claude/worktrees/app`. Three invariants govern every driver: the ground set is CONUS plus
DC, the zip table is the unit every step reads and writes, and the delivered map is the clipped
one, never the draw (section 3 below).

## 1. Three virtualenvs, on purpose

| venv | who owns it | what is in it |
|---|---|---|
| `.venv` (repo root) | the solvers | the frozen pins in `requirements.txt`: numpy 2.5.2, scipy 1.18.1, geopandas, shapely, pyproj, SCIP/HiGHS |
| `.venv-app` (per worktree) | the app | streamlit 1.63.0, pandas 3.0.5, plotly 7.0.0 (`app/requirements.txt`) |
| `.venv-opt` (repo root) | the MILP bench | `ortools` 9.15.6755, `numpy` 2.5.3, pinned in `tools/bench/requirements-opt.txt` |

The solver pins are frozen because the zip50 anchor depends on those exact versions, so
Streamlit's dependency tree must never be allowed to resolve them upward. The app therefore
never imports `td`; it drives every solver step by subprocess. That process boundary is also
the version boundary.

`.venv-opt` exists for the same reason, one level down. The MILP engine bench
(`tools/bench/milp_bench.py`, §4 and §7) compares solvers on the level-1 split problem, and one
of them, OR-Tools CP-SAT, would otherwise pull its own `numpy` into `.venv` and risk moving the
frozen pins. `td/solvers/milp_engines.py`'s `cpsat` engine therefore runs out of process, under
`.venv-opt`, through `td/solvers/milp_worker.py`; the `scipy`, `highs` (`highspy`) and `scip`
(`pyscipopt`) engines run in process, in the ordinary `.venv`, where both packages already
live. Build it once from the hub root: `uv venv --python 3.13 .venv-opt && uv pip install
--python .venv-opt/bin/python3 -r tools/bench/requirements-opt.txt` (`tools/bench/README.md`).

Rebuild the app venv from scratch, in every new worktree (it is not copied):

```
uv venv --python 3.13 .venv-app
uv pip install --python .venv-app/bin/python3 -r app/requirements.txt
```

`app/config.py` keeps two roots apart. `REPO` (default `/Users/ntlee/projects/td`, override
`TD_REPO`) is the hub checkout, because the gitignored inputs (the CONUS instances, `data/geo/`,
`battery/results/`) are never copied into a worktree. `CODE` is this checkout, because the
drivers a run launches sit beside `app/config.py`, which on a track branch are not the hub's.
`SOLVER_PYTHON` (default `REPO/.venv/bin/python3`, override `TD_SOLVER_PYTHON`) is separate from
both, since a worktree has no `.venv` of its own.

## 2. Running it and reaching it

```
tools/app.sh                                  # loopback 127.0.0.1:8501
tools/app.sh --server.address=100.69.120.67   # bind the tailnet address
```

`.streamlit/config.toml` sets `headless = true` and binds loopback by default. Run it inside
tmux so it survives the SSH session dropping.

`tools/app.sh` resolves its own worktree root and exports `PYTHONPATH` before calling Streamlit:
`streamlit run app/main.py` directly would put `app/` on `sys.path` instead of the worktree
root, so `from app import ...` would fail at the first line of the script.

Smoke test, no browser needed:

```
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8501/healthz    # 200
```

**Reaching it from the iPad.** The Mac Studio is `ntlees-mac-studio-1.tail133394.ts.net` /
`100.69.120.67` on the tailnet. Two routes, and the choice is about how much Rootshell can do,
not about security; both stay off the public internet.

Route A, bind the tailnet address (recommended, no tunnel): start with
`tools/app.sh --server.address=100.69.120.67` and open `http://100.69.120.67:8501` in Safari on
the iPad. Tailscale's ACLs are the access boundary. Browse by the same address the server
bound; if the websocket fails to connect under a MagicDNS name instead, that is a Host header
mismatch, fixed by using the IP or by adding `server.enableXsrfProtection = false` (acceptable
only on a private tailnet).

Route B, SSH local port forward: `ssh -N -L 8501:127.0.0.1:8501 ntlee@100.69.120.67`, then open
`http://localhost:8501`. This needs Rootshell to expose the forwarded port on the iPadOS
loopback interface; if Safari cannot reach it, fall back to route A. Mosh does not forward ports
at all, so this route needs a plain `ssh`, and the forward must be `-L`, not `-R`.

## 3. Three invariants

**CONUS plus DC.** `td.geo.assert_conus(d)` raises a `ValueError` unless every zip of the loaded
instance carries a lower-48-or-DC state; `NON_CONUS = {AK, HI, PR, VI, GU, MP, AS}`, plus a
blank state. Every driver (`run_draw.py`, `state_splits.py`, `staff.py`, `override.py`,
`split_district.py`) calls it immediately after loading the instance, so a non-CONUS instance
fails the whole run rather than placing those zips somewhere quiet. `tools/state_splits.py` no
longer carries any AK/HI placement path; the app's instance picker
(`config.INSTANCES = sorted(REPO.glob("instance_descaled_*_conus.json.gz"))`) only ever lists
CONUS files, defaulting to `instance_descaled_v2_conus.json.gz`.

The zip table is the unit. Every step reads a zip table and writes one:
`zip,state,x,y,opportunity,district` plus an optional seventh `rep` column (`td/ziptable.py`).
`read` returns `rep` as `""` when the column is absent; `write` emits it only when some row
carries one, so a plain map stays six columns. `staff.py` fills `rep` on every row of a staffed
district; `split_district.py` fills it per zip inside one district, leaving `district`
unchanged. The instance file is opened only for books and candidacy (`S`, `cand`, `S_free`
through `td.model`), never for labels or masses; balance, contiguity and every diff come from
the table alone.

The delivered map is the clipped one. The grid's terminal map per k is the clip step's own
table (`tools/state_splits.py`'s output), not the draw that fed it. The Map tab's run picker
defaults to the clip, staff, override, split and import kinds; a "show intermediates" toggle
adds `draw` back in. A clip cell that fails writes `failure.json` and no table; `store.status`
reads that as `failed`, and the Map tab shows the failure reason in place of a map, never the
draw standing in for it.

## 4. Architecture

**Run directory:** `battery/results/app/<member>_<kind>_<YYYYmmdd_HHMMSS>[-n]/step.json`, the
`-n` suffix added on a same-second name collision (`store.new_run_dir`). `member` is a
scenario member's name (`store.member_name`): the scenario slug plus its district count and
delta, unpadded (`custom_k10_d5`, `custom_k10_d7.5`); a run outside any scenario falls back to
a bare `k<kk>`. Every picker shows `store.label`, built from the ledger (`custom_k10_d5 ·
clip · 2026-09-08 14:42:39`), so a run made under the older `<kind>_k<kk>_<stamp>` naming still
reads, as `k18 · clip · 2026-09-08 14:42:39`. `step.json`:

```
{kind, parent: "<run name>"|null, params, argv, pid, started,
 outputs: {table: "k18/draw.csv", metrics: "..." , geom: "geom.json"},
 scenario: "custom"|null, member: "custom_k10_d5"|null}
```

**Scenarios.** `scenario` is the slug a grid launch's typed name reduces to
(`store.slugify`: lowercased, everything outside `[a-z0-9-]` collapsed to one hyphen, empty
input falling back to `grid-<YYYYmmdd>-<HHMM>`); `member` is that slug plus the chain's own k
and delta. `steps.grid(name=...)` writes both into the draw and clip steps of every chain it
launches; with no `threads` given it also splits the machine's cores evenly across those chains
(`max(2, cpu_count // len(ks))` per clip), so a six-k grid's chains do not each size a
`highs`/`scip` portfolio for the whole machine. A child (`staff`, `override`, `split`) never sets
them itself, and
`store.scenario_of`/`store.member_of` walk a run's lineage to find them the way `store.k_of`
already does, so the child still reads its parent chain's scenario. `store.scenarios(root)`
groups every discovered run by scenario, newest scenario first by its own newest run, with runs
carrying neither anywhere in their lineage (made before this ledger, or hand-imported) grouped
last under the slug `None`. The sidebar's scenario picker (`app.common.current_scenario`, the
`None` group shown as "older runs") drives every child tab's picker
(`app.common.map_runs`/`pick_map`), which filters to whichever scenario is selected; the
Scenarios tab's own runs table adds `scenario` and `instance` (the member name; "Instance" is
the UI label there, since the user's "instance" collides with the code's own word for the data
file, labelled "Instance file") columns, defaults to the current scenario, and carries a "show
every scenario" toggle.

paths under `outputs` are relative to the run directory, so a run can be moved or copied whole.
`store.discover(root)` returns every directory carrying a `step.json`, newest first by the
timestamp in its name. `store.status(run)`: a table already on disk reads `done` outright
(a driver that finished writing is done regardless of its pid); short of that a live pid
(`runner._alive`, which reaps a finished child with `waitpid(WNOHANG)` before falling back to
`os.kill`, so a zombie does not read as still running) is `running`; a `failure.json` or a dead
pid is `failed`; otherwise `queued`. A chain member launched by `runner.launch_chain` shares its
predecessor's pid, so it reads `running` for as long as the chain is still working its way to
that member's own step. `store.lineage(run, root)` walks `parent` back to the root ancestor;
`store.children` is the one-level reverse.

The kinds a wired code path creates are `draw` and `clip` (`steps.grid()`, from the Scenarios
tab) and `staff`, `override` and `split` (each from its own tab, through `main.launch_child`).
`launch_child` writes the child's `step.json` (kind, parent, params, argv) with `geom` already
named in `outputs` before anything runs, then launches the driver and `geom_export.py` as one
two-member chain (`runner.launch_chain`, `PYTHONHASHSEED=0` on every launch), so a map arrives
with polygons already built rather than as bare points. `geom` is still not a run kind of its
own: it is always an addition to an existing run's own directory and its own `step.json.outputs`
(the same thing the Map tab's manual "Build polygons" button does for a run `launch_child` did
not chain it onto). `import` is the one kind nothing yet produces: `app.main.MAP_KINDS` and
`store` both anticipate it, for wrapping an externally-supplied table as a root with no engine to
rerun, but no driver or tab writes one.

Drivers:

| driver | CLI | reads | writes |
|---|---|---|---|
| draw | `run_draw.py <instance> --k K --seeds S --workers W --theta T --lam L --filler-capture F --geo-cache DIR --out RUN [--scenario FILE] [--lock-zips FILE]` | instance; optional `scenario.json` (fix/anchor pins); optional `locks.json` | `k<kk>/draw.csv`, `k<kk>/metrics.json` |
| clip | `state_splits.py <instance> --draw TABLE --k K --delta D --time-limit T --theta T --lam L --filler-capture F --rounds 5 --eta 0.01 --anchor-homes --engine {highs,scip,scipy} --strategy {portfolio,descent,direct} --primal-seconds S --threads N --no-fix-roots --no-maps --geo-cache DIR --out RUN [--bounds FILE]` | instance; a draw table; optional `bounds.json` | `d<delta>/draw.csv`, `d<delta>/splits.json`, `state_shares.csv`, `steps/` |
| geom_export | `geom_export.py --table TABLE --out RUN [--geo-cache DIR] [--simplify M] [--no-basemap]` | a zip table | `geom.json`, in the run directory `--out` names |
| staff | `staff.py <instance> --table TABLE [--keep R,.. \| --release R,..] --theta T --lam L --filler-capture F [--districts D01,D05,...] --out RUN` | instance; a zip table | `staffing.json`, `draw.csv` (rep filled per staffed district) |
| rep_export | `rep_export.py <instance> --out DIR [--geo-cache DIR] [--simplify M] [--no-basemap]` | instance | `reps.json` |
| override, mode A | `override.py <instance> --table TABLE --edits FILE --mode A [--eta E] --out RUN` | instance (CONUS assert only); a zip table; `edits.json` | `draw.csv` (relabelled), `metrics.json` |
| override, mode B | `override.py <instance> --table TABLE --edits FILE --mode B --parent PARENT_RUN --out RUN` | `edits.json`; `PARENT_RUN`'s lineage, walked up to its nearest `draw`/`clip` ancestor for that step's own recorded `argv` | `locks.json` or `bounds.json`, `engine/` (the rerun engine's own output tree), `draw.csv`, `metrics.json` |
| split_district | `split_district.py <instance> --table TABLE --district D --reps R,R --theta T --lam L --filler-capture F [--exact] [--time-limit T] [--n-near N] [--geom GEOM] --out RUN` | instance; a zip table; optionally the run's `geom.json`, whose `cell_edges` make the greedy split contiguous on the cell graph | `draw.csv` (rep filled inside the district, `district` unchanged), `split.json` |

theta, lambda and the filler-capture rule weight the stage-2 rep utility and nothing else: no
geometry moves when they change. Every step of a chain is given the same three, so the values a
chain reports are comparable within it. The draw and the split take them from the tab that
launched the run, the clip takes them from the draw it clips, and a split takes them from the
staffing run it descends from. `d<delta>/splits.json` records `stage2_value` next to
`stage2_theta`, `stage2_lam` and `stage2_filler`, and the Map tab shows the value with those
weights beneath it, since a stage-2 value read without its weights means nothing. The drivers'
own defaults are unchanged and still `theta`, so a run made without the flags stays comparable to
the committed map.

Frozen JSON contracts.

`timings.json`, written by every driver next to its other outputs
(`step.json.outputs["timings"]`, set by `steps.grid` for draw and clip, by
`app.common.launch_child` for every tab-launched child, and by `app.repdata.ensure` for the rep
export) from `td/telemetry.py`'s `Timings`:
```
{"driver": "clip", "argv": [...], "started": iso, "finished": iso, "wall": s,
 "cpu": s (this process plus its reaped children), "rss_peak_mb": float,
 "phases": [{"name": "solve", "depth": 0, "start": s-from-driver-start, "wall": s,
             "cpu": s, "note": {...}}, ...],
 "ticks":  {"lp.assign": {"n": 42, "wall": s}}}
```
A run directory that already holds another driver's `timings.json` (a clip run's own directory,
then a chained `geom_export`) keeps it and gives the second driver `timings.<driver>.json`
instead (`Timings.write`), so only a same-driver rerun overwrites its own file.

A phase nests (`depth` counts how many phases are already open when it starts) and can carry a
`note` (arbitrary key/values, `ph.note(...)`); a tick accumulates many small calls under one
name (`Timings.tick`) rather than opening a phase for each. `TD_PROFILE=1` in the environment
also dumps a `cProfile` run of the whole driver to `<out_dir>/profile.prof`
(`telemetry.maybe_profile`, wrapping every driver's own `main`); §7 has the recipe.

Phase names are fixed across drivers so the Timings tab can line chains up, but two of them are
an approximation rather than a full breakdown. The draw's `stage1` phase covers the whole
per-`(k, seed)` sweep and folds in each pool job's own `lp.assign` ticks (one per
`centers.assign` call); `centers.improve`, the polish step that runs after the Lloyd loop,
records no tick of its own, so its cost sits inside `stage1`'s wall time rather than named
apart from it. `split_district.py` bills its one call into `td.solvers.district_split.split`
to whichever engine actually ran, a phase named `"greedy"` or `"scip"` rather than two, since
`--exact` escalates from one to the other inside a single call this workstream does not own.

| driver | phases (depth 0) |
|---|---|
| draw | `load`, `coordinates`, `stage1` (note `jobs`, `workers`; ticks `lp.assign`), `stage2`, `write` |
| clip | `load`, `build_milp`, `solve` (note `status`, `nodes`, `gap`, `dual_bound`, `objective`, `time_limit`, `engine`), `balance_pass`, `realise`, `stage2`, `write` |
| geom_export | `load`, `voronoi`, `dissolve`, `colour`, `cells`, `write` |
| staff | `load`, `books`, `gain_matrix`, `assign`, `write` |
| split_district | `load`, `greedy` or `scip`, `write` |
| rep_export | `load`, `shares`, `voronoi`, `dissolve`, `footprints`, `write` |

`geom.json`:
```
{"crs": "laea",
 "districts": {"D01": {"rings": [[[x,y],...],...], "color": "#rrggbb"}, ...},
 "states": {"TX": {"rings": [[[x,y],...],...], "label": [x,y]}, ...},
 "cells": {"75201": {"rings": [[[x,y],...],...]}, ...},   # one Voronoi cell per placed zip
 "cell_edges": [["75201", "75202"], ...]}                  # rook adjacency of the cells
```
Coordinates are the table's own LAEA metres, rounded to a decimetre; rings are exterior only
(holes dropped), simplified at 2000 m by default. Colours come from a generated 50-entry
palette (25 hues at two lightness levels, laid out on a stride coprime with 25 so consecutive
entries sit about 130 degrees apart), assigned over the adjacency read off the polygons
themselves, so two districts sharing a border never share a hue. `cells` are the same Voronoi
cells the districts dissolve from, so the rep maps can fill zips one by one; `cell_edges` is
read off the unsimplified cells (a shared boundary of positive length, corner touches excluded)
and stored rather than derived from the rings, because simplification treats each polygon
alone and neighbours' simplified rings no longer coincide. Cells depend only on the zips'
coordinates and states, never on the district labels, so every run of one instance carries
the same cells. On the CONUS k=10 run the two keys take the file from about 120 KB to about
880 KB and cost 0.3 s.

`reps.json` (written by `tools/rep_export.py`, read by `app/repdata.py` and `app/mapfig.py`):
```
{"crs": "laea", "instance": "instance_descaled_v2_conus.json.gz",
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
Ratios and identifiers only: `weight` and `book_share` are shares of one unknown total that
never itself appears in the file (invariant 4, §7). Coordinates
are the table's own LAEA metres, exterior rings only, simplified 2000 m, exactly
`geom_export._rings`. Colours come from `geom_export.palette()` assigned over the territories'
own adjacency, so two touching territories never share a hue, the same promise `geom.json`
makes. Voronoi cells are built over every zip with coordinates, untapped zips included, so no
territory swallows ground nobody claims; an untapped cell dissolves into nothing and stays
unfilled. Location: `config.REP_CACHE / <instance stem> / reps.json`
(`REP_CACHE = RESULTS / "app_reps"`), outside `APP_RESULTS` so `store.discover` never lists it;
the directory carries a minimal `step.json` (`kind: "reps"`, `parent: None`, `outputs:
{"reps": "reps.json", "timings": "timings.json"}`) so `runner.launch`, `store.status` and the
log tail work unchanged. `app/repdata.py`'s `ensure(instance)` builds it on demand, behind a
"Build rep territories" button, keyed by the instance's own name rather than by when it ran, so
one export per instance is reused rather than rebuilt.

`staffing.json`:
```
{"kept": [...], "released": [...], "k": int, "districts": [...],
 "assignment": {district: rep}, "gains": {district: g}, "value": float,
 "unmatched_reps": [...], "unstaffed_districts": [...],
 "balance": {...ziptable.balance...},
 "contest": {district: {"candidates": [...], "share": {rep: frac},
                        "free_share": float, "g": {rep: g_ij}}}}
```
`districts` is the scope `--districts` restricted this run to, or every district of the table
when the flag was absent; a row outside the scope is left exactly as the input table had it, so
`kept`, `released`, `k` and `balance` stay whole-table regardless of scope.

`edits.json` (`override.py`'s own input, both modes):
```
{"moves": [{"unit": "state"|"zip", "id": "TX", "to": "D05"}],
 "hold": {"states": [...], "zips": [...]}}
```
Mode A applies `moves` in order and ignores `hold`, since a relabel reruns nothing.

`bounds.json` (`state_splits.py`'s own `--bounds` document, consumed at the MILP and at the
realise pass):
```
{"force":  [["TX", "D05"], ...],
 "forbid": [["TX", "D03"], ...],
 "fix":    {"VT": ["D02"]},
 "freeze": {"05401": "D02"},
 "pull":   {"75201": "D05"}}
```
`force`/`forbid` bound `z_sj` at 1/0; `fix` sets `z_sj = 1` for the listed districts and 0 for
every other one a state could touch; `freeze` overwrites a zip's realised label unconditionally
after `realise` runs; `pull` is a tiebreak bonus fed into `realise`, a preference rather than a
bound. `parse_bounds` resolves every state, district and zip name against the draw's own state
list, k and zips, and refuses (`sys.exit`) an unknown name, an internal contradiction (a pair
both forced and forbidden, or a `fix` also named in a `force`/`forbid`), or an out-of-range bound
before any solve starts. An entry that contradicts an `--anchor-homes` anchor drops that anchor
rather than fighting it (`_release_bound_anchors`), the way `--unanchor` drops one by hand.
`splits.json` carries `bounds` (the document as given) and `bounds_honoured` (whether each entry
held after the solve and the realise pass), since a `pull` is only a preference and a forced `z`
can still be refused by the band. `override.py`'s own mode B translation (below) never emits a
`forbid` entry; that key exists for a `--bounds` file written by hand.

`locks.json` (`run_draw.py --lock-zips`):
```
{"75201": "D05", ...}
```
Zip keys are normalised to five characters whether or not they arrive zero-padded; values are
district names, treated exactly like an anchor district's own zips. A locked district colliding
with a `--fix` district name is refused (fixed districts never reach the solver at all); a lock
naming a district that is not otherwise an anchor becomes a new anchor for that run, and every
lock is recorded on `k<kk>/metrics.json` under `locks` plus a `mode: "lock"` row in `hand_drawn`.

`split.json`:
```
{"district": "D05", "reps": [...], "objective": float, "gains": {rep: g},
 "shares": {rep: frac}, "method": "greedy"|"scip", "gap": float|null, "status": str,
 "n_zips": int, "dropped_reps": [...], "seconds": float,
 "pieces": {rep: int}|null, "contiguous": bool|null}
```
`pieces` counts each rep's connected pieces on the district's Voronoi cell graph, one per
component of that graph at most when `contiguous` is true; both are `null` when the run had no
`--geom`. The greedy engine keeps every rep in one piece by construction (a contiguous seed,
then moves only of a zip that is not an articulation point of its rep, only to a rep owning a
neighbouring cell); the exact engine is unconstrained and only reports its pieces, so an
`--exact` answer can read `contiguous: false`.

`metrics.json` of an override, both modes computing the same five fields through a shared
`report()` helper:
```
{"mode": "A", "k": int, "moves": [...],
 "balance": {...}, "balance_before": {...},
 "contiguity": {district: bool},
 "diff": {"zips_relabelled": int, "districts": {district: {"share_before", "share_after"}}},
 "states_split": [...],
 "edits_honoured": true}
```
`edits_honoured` is the literal `true` in mode A, since a relabel is exact. In mode B it is a
per-edit report instead, `{"moves": [{"unit", "id", "to", "honoured": bool}, ...],
"hold": {"states": {state: bool}, "zips": {zip: bool}}}`, read off the reran table rather than
assumed. Mode B's own `metrics.json` also carries `"mode": "B"`, `"engine": "draw"|"clip"`,
`"engine_run"` (the ancestor run's name) and `"engine_out": "engine"` (its own output tree,
under the override's run directory), the translated document under `"locks"` or `"bounds"`
depending on `engine`, and, when `engine` is `"clip"`, a passthrough `"bounds_honoured"` copied
from that engine's own `splits.json`.

**The MILP engine seam.** `td/solvers/milp_engines.py`'s `solve_problem(problem, engine, ...)`
runs the level-1 minimum-splits MILP (`td.solvers.state_splits.SplitProblem`) through one of
four engines behind one return shape: `scipy` (today's `state_splits.solve`, the baseline),
`highs` and `scip` in process (`highspy`, `pyscipopt`, already in `.venv`), and `cpsat` out of
process under `.venv-opt` through `td/solvers/milp_worker.py`. Three pure functions build
variant problems rather than solving anything: `fix_roots` roots an anchored district's flow
at its home state (no optimum is lost, since a connected set can be rooted anywhere;
`tools/verify/milp_root_fix/REPORT.md` is the verified claim); `with_cutoff` asks "does a
smaller map exist", so an infeasible answer certifies the current count optimal without
closing a gap; `lp_heuristic` is a reweighted-L1 relaxation that reaches a feasible split count
in milliseconds with no certificate. `tools/bench/milp_bench.py` drives every variant on the
real instance and records which route reaches proven optimality fastest; `tools/bench/README.md`
has the usage, the variant table and the acceptance rule.

**Strategies.** `tools/state_splits.py --strategy` picks how `state_splits.solve` reaches its
answer: `direct` (one solve to `--time-limit`, the old path; the `scipy` engine reproduces the
committed map bit for bit), `descent` (a quick primal incumbent within `--primal-seconds`,
default 30 s, then repeated cutoff solves proving no smaller split count exists, then a
warm-started tie-break close; on the real k=20 cell this took 293 s, 255 s of it the 10-split
search under the cutoff), and `portfolio` (the default: HiGHS on cores-3 threads at heuristic
effort 0.5 and SCIP on one thread, spawned as members streaming incumbents to the parent; the
parent quick-certifies each new split count with a 5 s cutoff solve on 2 threads, skips
incumbents above 2k splits, restarts the members on the cutoff problem after 5 s of quiet when
the quick certificate cannot close it, takes a member's own infeasible verdict as the
certificate, then closes the compactness tie-break for up to 30 s, warm-started). `splits.json`'s
`certified_splits` is true whenever the split count itself is proven, even when `status` reads
`time_limit` because only the tie-break ran out of time. Real standalone cells: k=20 closes
fully in 70 s (SCIP finds 10 splits at 47 s, the proof takes 0.2 s, the tie-break 11 s); k=16
certifies 7 splits in 82.7 s (the certificate "no 6-split map" is not LP-infeasible outright, so
SCIP proves it in 24 s during a cutoff round against HiGHS's 74 s), tie-break left open at the
30 s cap.

## 5. The map

`app/mapfig.py` builds one plotly figure from a zip table plus `geom.json`. Coordinates are the
table's own LAEA metres, drawn on cartesian axes with `scaleanchor="x"`, `scaleratio=1`; there
are no map tiles, since a tiled basemap needs geographic coordinates and this repo has no
inverse projection. Equal aspect on an equal-area projection is what makes the shapes read as a
map.

Trace order is a contract with `app/main.py`, which reads a selection event back by matching
`curve_number` against the trace names: state outlines (one line trace, rings joined by `None`,
hover skipped); district polygons (one filled trace per district, opacity 0.35, hover skipped);
zips (one `go.Scattergl`, marker size proportional to `sqrt(opportunity)`, hover shows zip,
state, district, rep and opportunity, plus the top three reps by book share when a
`staffing.json` is loaded); state label handles (one text trace, hover shows the state code).
Optional overlays: a set of highlighted zips (open circle markers), and a dashed `outline` ring
copied from another map's own `geom.json`, so a child map can be read against its parent's
district boundary; no tab passes one yet, though `render_footprint` (Reps) uses the highlight
overlay to show a district or one rep's own zips within it. Outlines and polygons skip hover so
a click always lands on a zip or a state handle, never the fill under them.

Selection: `st.plotly_chart(fig, on_select="rerun", selection_mode=("points",))`. `render_board`
reads back `event["selection"]["points"]`, resolves each point's trace by `curve_number`, and on
a zip stores `selected_zip`/`selected_state` in `st.session_state`; on a state handle it stores
`selected_state` alone. The Reps tab defaults its district picker to the selected zip's own
district; the Overrides tab prefills a move's id box from the selected zip or state, depending on
which unit is chosen.

Caching: `_rows`/`_geom` in `main.py` are `st.cache_data`, keyed on `(path, mtime)`, so a driver
rewriting a file under the same name busts the cache; `mapfig.py` itself imports neither
streamlit nor pandas and stays importable from plain Python. `in_flight()` is an
`st.fragment(run_every=5)` block, so the five-second poll of in-progress runs reruns only that
fragment.

`app.mapfig.rep_figure` draws the incumbent layout, in trace order: state outlines; one filled
trace per rep over the cells of the zips whose `top` is that rep (`REP_FILLS`, opacity 0.45,
rings joined by `None`); the hatched `CONTESTED` union (cells where two or more reps hold
book); the focused rep's territory or footprint on top (`FOCUS`); `DISTRICT_LINES` from the
run's `geom.json`, when asked to overlay them; state label handles. `colour_by="n"` swaps the
rep fills for four fills off `mapfig.N_RAMP`, the sequential ramp for 0/1/2/3+ reps holding
book at a zip, one per step in `N_LABELS` order with the legend on the fills themselves.
`app.mapfig.staffed_figure` draws the "after" map the same way: state outlines; one fill per
rep over the cells whose table `rep` is that rep (`STAFFED_FILLS`, opacity 0.55), so a
within-district split shows as cells changing colour inside the district; the hatched
`UNSTAFFED` union; state handles. Neither figure draws zip markers any more; hover sits on the
cell vertices (`hoveron="points"`, the cell's text repeated on every vertex, `hoverdistance`
40 px), since plotly shows only the trace name when hovering a fill. A `geom.json` written
before cells were exported has no `cells` key, and both figures then fall back to the
dissolved fills (territories from `reps.json`, districts from `geom.json`) with no hover; rerun
`geom_export.py` on that run to get the cells. `app.mapfig.rep_colours(reps)` builds the one
`{rep: hex}` map both figures draw from, so a rep keeps its hue on both sides of a before/after
pair: a rep with a territory keeps `reps.json`'s own colour, assigned so neighbouring
territories never share a hue; a rep with none takes the next palette entry not already spoken
for. Both figures take the same `bbox` keyword `figure` does, for zooming to one district, with
`uirevision` set to the bbox so pan and zoom persist across reruns and reset when the bbox
changes.

The Timings tab (`app/tab_timings.py`) draws a Gantt of one bar per run in the current
scenario, coloured by step kind (draw, clip, geom, staff, everything else bucketed as "other")
off a fixed palette, so hue always means the same kind across scenarios; a run still running
draws hollow, and one with no `timings.json` yet draws a zero-width "no timings" marker rather
than being skipped.

## 6. The three uses, as recipes through the tabs

The k grid at delta 10%. In Scenarios, the defaults are k = 10, 12, 14, 16, 18, 20
(`config.KS`), delta 0.10, seeds "0-4", workers 2 per draw, theta 0.40, lambda 0.30,
filler-capture "full", clip time limit 600 s. "Launch grid" builds six chains (`steps.grid`),
one per k: a `run_draw.py` process for that k alone, then
`state_splits.py --draw ... --k kk --delta 0.10 --anchor-homes --rounds 5 --eta 0.01 --no-maps
--time-limit 600`, then `geom_export.py` on the clip's own winning table, written into that same
clip run directory. Each chain runs as one detached shell (`runner.launch_chain`, `a && b && c`),
so its clip step reads `running` for as long as its draw step is still working, and the same pid
covers both directories. Every launch sets `PYTHONHASHSEED=0`. The Map tab's default kinds are
the clip and its descendants; a clip cell with no table shows `store.status` and, when present,
`failure.json`'s reason: `infeasible` means HiGHS proved no such map exists at that band,
`no_incumbent` means the time limit arrived before any feasible point, and the two are different
claims.

Staffing and contestability with released reps. From the Reps tab, naming reps who leave (typed
by hand if the map carries no `rep` column and no prior staffing, since the app cannot open the
instance to list reps itself) runs `staff.py --release R12,R31`, which folds each one's book into
`S_free` (`td.model.release_reps`) and drops them from `cand`, so the reps who stay value that book at
`c_free` rather than at `c2`. The default `--filler-capture full` sets `c_free = c1`, the same
rate a rep values its own book at, on the reasoning that with the departing rep gone nobody is
left to pull that business away; `theta` and `opportunity` are the other two choices (`c2` and
`lam`) and value it lower. Candidacy for staffing is narrower than `channel.gain_matrix`'s own
default: a rep may only be assigned a district it already holds book in (`S_i(z) > 0` on some
zip of it, read after the release fold), so a district no kept rep sells in is left unstaffed
rather than handed to the top scorer. The assignment is the Hungarian algorithm on `-log g`
(`scipy.optimize.linear_sum_assignment`), with every non-candidate cell priced above anything a
swap of allowed cells could recover, so the optimum never uses one it can avoid and any pair left
over drops out and reads `unstaffed`. Picking a district and its candidate reps and running the
split (`split_district.py --district D05 --reps R1,R2 [--exact --time-limit 60]`) divides that
district's zips among them by the same Nash objective one level down: greedy single-zip moves
first (`td.solvers.district_split.greedy`, deterministic, milliseconds), then, only with
`--exact`, a `pyscipopt` MINLP warm-started from the greedy labelling. The result is reported
`method: "scip"` only when SCIP's answer is at least as good as greedy's; `status` and `gap` say
whether the gap actually closed rather than the incumbent merely improving. The tab passes the
staffing run's `geom.json` as `--geom`, so the greedy answer is contiguous on the cell graph;
the result table shows each rep's `pieces`, and a warning names any rep in more than one piece
(only an `--exact` answer can be). A staffing scoped with `--districts` never hands an in-scope
district to a rep the table already places outside the scope, so no rep holds two districts.

Overrides. The Overrides tab builds one `edits.json` from clicks on the Map tab or typed ids
("Add move" appends `{"unit", "id", "to"}` to a list held in `st.session_state`) and a choice of
three modes: "A: relabel only", "B (i): rerun, moved units locked" and "B (ii): rerun, moved
units locked plus the hold set", the last two both `--mode B` with the hold set left empty for
(i). Mode A relabels the parent table by hand with no rerun: a `"state"` move relabels every row
of that state, a `"zip"` move relabels one row, and a moved row's `rep` clears to `""`. Both
modes report the same five numbers through a `report()` helper they share: balance beside the
old, per-district contiguity (a district's owner-state set, every state holding at least `eta`
(default 0.01) of its own opportunity in that district, checked against `td.geo.state_rook`; a
district owning no state reads as disconnected), and the diff (`zips_relabelled`, each district's
opportunity share before and after); a breach is reported, never refused.

Mode B (`override.py --mode B --parent PARENT_RUN`) walks `PARENT_RUN`'s `step.json.parent`
chain up to its nearest `draw` or `clip` ancestor, takes that step's own recorded `argv`, repoints
its `--out` into a nested directory (`args.out/engine/`), adds the one new flag below, and reruns
it with `subprocess.run`, not `os.execv`: the override driver's own process stays alive afterward
to build its report. Against a `draw` ancestor, the moved units become a `locks.json`
(`draw_locks`): a moved state or zip locked to its target, plus, under (ii), every held state's
or zip's own parent label, so a rerun with an empty hold set (i) leaves every other district free
to be re-seeded and renamed, and only the moved and held names persist. Against a `clip`
ancestor, the moves and holds become a `bounds.json` (`clip_bounds`): a moved state is a `fix` to
its target alone; a moved zip is weaker, since level 1 knows nothing about zips, so its state is
`force`d to touch the target and the zip itself is only `pull`ed there at level 2; a held state
keeps the district set it owns in the parent table (a `fix` again), and when that set already
spans more than one district, its zips are also `freeze`d at their parent labels to reproduce the
same split; a held zip is `freeze`d outright. `edits_honoured` is the literal `true` in mode A;
in mode B it is a per-edit report, `{moves: [{unit, id, to, honoured}], hold: {states, zips}}`,
read off the reran table, and a clip-parent rerun also copies `bounds_honoured` off the engine's
own `splits.json`. When the engine rerun fails, the override run copies the engine's own
`failure.json` if it wrote one, else writes a generic `reason: "engine_failed"`.

Reading the incumbent layout, staffing one district, and reading the before and after. The Map
tab's "Rep territories, as sold today" section (`repdata.ensure`, building `reps.json` on first
use) shows whose book covers which zips today, coloured by rep or by how many reps hold book
there, with the contested cells hatched. The Reps tab opens on that same layout with the picked
run's own districts drawn over it (`district_lines=True`), then lets a scope be chosen: "the
whole map", or one or more districts (`st.multiselect`, defaulting to the district of the zip
last clicked on the Map tab) behind `st.radio("Staff", ...)`. Naming which reps are released
and clicking "Staff" runs `staff.py --districts D01,D05 ...` scoped to that selection; a row
outside the scope keeps the `rep` it arrived with, and `staffing.json["districts"]` records the
scope. Picking the district in Contestability shows, side by side and zoomed to it, the rep
layout as sold today (`mapfig.rep_figure(..., bbox=...)`) and the staffed result
(`mapfig.staffed_figure(..., bbox=...)`, or the newest split's own table when one exists for
that district), with a small table underneath (`app.staffdiff.district_view`) giving each rep's,
plus "contested"'s and "untapped"'s, share of the district's book before and after. The same
pair, unzoomed and over the whole map, sits under Assignment ("Before and after the staffing"),
together with `app.staffdiff.summary`'s whole-map counts (reps with territory, contested book,
free versus unstaffed book) and `app.staffdiff.per_rep`'s sortable table of every rep's book
share before, after and the change.

## 7. Assumptions and what is not tested

1. `tests/test_app_smoke.py` drives every tab of the Streamlit UI headlessly, through
   `streamlit.testing.v1.AppTest`, which only the app venv has installed: run it by hand as
   `PYTHONPATH=$PWD .venv-app/bin/python3 tests/run_all.py -k app_smoke`. Under the solver
   venv (`tests/run_all.py`'s own run) the import fails and the test returns at once, an early
   return rather than a skip the runner counts. `tests/test_mapfig.py` is the same shape for
   the same reason, gated on `plotly` rather than `streamlit`: it too is exercised for real
   only under the app venv, `PYTHONPATH=$PWD .venv-app/bin/python3 tests/run_all.py -k mapfig`.
2. Every driver has a solver-venv test that runs it end to end on a synthetic instance, no
   network and no real instance file: `tests/test_run_draw.py` and `test_run_draw_locks.py`
   (`run_draw.py`, including `--lock-zips`); `tests/test_state_splits.py`,
   `test_state_splits_cli.py` and `test_state_splits_bounds.py` (`state_splits.py`, including
   `--bounds` at the MILP level, `bound_z`, and at the CLI's own translation and realise-time
   freeze/pull); `tests/test_geom_export.py`; `tests/test_staff.py`, including `--districts`;
   `tests/test_rep_export.py` (`tools/rep_export.py`, on the toy instance, `--no-basemap`);
   `tests/test_override_a.py` and `tests/test_override_b.py` (mode B's translation, engine
   rerun and `edits_honoured`); `tests/test_district_split.py` (an 8-zip/3-rep brute-force
   oracle bounding the greedy answer and, when `pyscipopt` is importable, matching the exact
   one); `tests/test_ziptable.py` (the optional `rep` column); `tests/test_geo.py`
   (`assert_conus`). `app/staffdiff.py` (`tests/test_staffdiff.py`, an inline fixture, pure
   Python) and `td/telemetry.py` (`tests/test_telemetry.py`: nesting depth, tick accumulation,
   the write round trip, `maybe_profile` under `TD_PROFILE=1`, the module-level hook as a
   no-op with nothing active) are covered the same way, needing neither streamlit nor plotly.
   `td/solvers/milp_engines.py` is `tests/test_milp_engines.py`, also solver-venv: every exact
   engine returns the same split count as `scipy` on the toy problems, `fix_roots` changes
   nothing, `with_cutoff` behaves as a certificate should, and the `cpsat` cases return early
   when `.venv-opt` is absent.
3. `app/store.py` and `app/steps.py` import neither `streamlit` nor `pandas`, so
   `tests/test_app_store.py` runs from the solver venv on fake run directories (discover,
   lineage, status, the grid's chain expansion, the scenario ledger); `runner._alive`'s zombie
   reap is `tests/test_app_runner.py`.
4. `geom.json`, `reps.json`, `staffing.json` and `split.json` hold ratios, geography and
   identifiers only, never a raw mass or a dollar figure: `reps.json`'s `weight` (a zip's share
   of the whole channel's book) and `book_share` (a rep's share of it) are shares of one
   unknown total that never itself appears in the file. Per-zip opportunity travels only inside
   `draw.csv`, under the gitignored `battery/results/`.
5. Profiling a driver: `TD_PROFILE=1` in the environment (any driver, e.g. `TD_PROFILE=1
   .venv/bin/python3 tools/geom_export.py --table TABLE --out RUN`) dumps a `cProfile` run to
   `<out_dir>/profile.prof`, which the Timings tab's per-run detail shows as a `pstats` top-25
   by cumulative time. Sampling a running solve instead: `uv tool install py-spy` (never into
   `.venv`), then `py-spy record -o out.svg --pid <pid>` against the driver's own process.
6. The MILP engine bench (`tools/bench/milp_bench.py`, §4, `tools/bench/README.md`) writes
   `battery/results/bench/milp_<stamp>.json`, one row per `(k, variant)`; it is not
   test-covered beyond `test_milp_engines.py`'s unit-level checks on the engines it calls. Its
   own numbers are recorded once, in `docs/CODE_MAP.md`'s runtime tables, not repeated here.
7. The k = 10 to 20 grid, six chains at once through the app, each clip's portfolio sized by
   `steps.grid`'s per-chain `--threads 2`: wall clock 163.5 s, down from 614 s before the
   portfolio strategy, every clip cell certified, k=20 alone the long pole at 150 s. A
   k-weighted thread split, giving the k=20 chain more threads than k=10, is the next lever and
   is not done.
