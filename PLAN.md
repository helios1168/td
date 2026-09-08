# Track: simplified

## Goal

Make the live pipeline runnable end to end on the work machine from one command line, with
the data read from Snowflake. The live pipeline is the one `docs/HEADLINE.md` §8 reproduces:
export the descaled instance, draw k districts (stage 1), split states at a band δ (level 1
and level 2), render the zip table, match reps (stage 2). Everything else in the repo is
research record and stays runnable where it is runnable today, but off the install path.

Status 2026-09-08: design only. Nothing implemented.

## What the inventory found (2026-09-08)

Live path, reachable from `tools/run_draw.py`, `tools/state_splits.py`, `tools/us_maps.py`:

- `td/`: `instance`, `model`, `channel`, `geo`, `ziptable`, `solvers/{base, brute, centers,
  state_splits, state_borders}`; `solvers/scip_tree` only through the guarded registry import.
- `tools/`: `run_draw.py` (680 lines), `state_splits.py` (446), `borders_report.py` (388),
  `us_maps.py` (2136).
- Solvers on the live path are scipy's bundled HiGHS (`linprog`, `milp`). No pyscipopt,
  highspy, mip, cbcbox, sympy or mpmath is imported anywhere on it.
- Maps and `geo.state_rook` need matplotlib, shapely, pyproj; `geo.states_outline` needs
  geopandas. `pyproject.toml` declares only numpy, scipy, networkx.

Not reachable from the live path: `td/atoms.py`, `td/solvers/{atom_draw, cert_draw,
cert_exact, eg_band}.py`, `tools/run_atoms.py`, `tools/state_borders.py`, `tools/measure/`,
`tools/motion_page/`, `tools/state_atoms/`, all of `tools/verify/`, `app/`.

Layout assumptions that break on another machine:

- `td/ziptable.py` loads `tools/us_maps.py` by file path, so `td/` reaches back into `tools/`.
- `tools/` is not a package. Each script inserts its own directory and the repo root into
  `sys.path`, and `state_splits.py` imports `run_draw`, `us_maps`, `borders_report` as top-level
  modules.
- `td/geo.py` `DEFAULT_DEST = "data/geo"` is relative, so every driver assumes cwd is the
  repo root. Output defaults point at `battery/results/`.
- `tests/test_borders_report.py`, `app/config.py`, `tools/motion_page/`, `tools/state_atoms/`
  and every `tools/verify/` script carry `/Users/ntlee/...` paths; the verify scripts name
  three deleted worktrees and are unrunnable as written.
- `td/solvers/base.py` line 565 tries `from . import loop_v2`, a module that no longer exists;
  `cert_exact.py` and `scip_tree.py` import `instances` and `warm`, also gone.

Runtime facts: a k = 18, seeds 0 to 9 stage-1 run is under a minute even single-process
(the full 9 k × 10 seed sweep is 56 s on 8 workers); level 1 at δ = 5 % closes in about
3 minutes and δ = 10 % hits the 600 s limit; a map render is about 40 s. Only the atom route
needs `PYTHONHASHSEED=0`, and it is off the live path. Stage 2 is milliseconds.

The exporter (`tools/instance_export/export_instance.py`) is stdlib only and reads four
tables from files: sales `(zip_code, rep_id, firm, sales)`, opportunity `(zip_code, M)`,
edges `(u, v)`, states `(zip_code, state)`. Nothing in the repo talks to a database.

## Snowflake feasibility (checked against docs.snowflake.com, 2026-09-08)

Three ways to run it. Ranked.

1. Work machine, data pulled from Snowflake, pipeline run locally. `snowflake-connector-python`
   with `fetch_pandas_all`, or plain cursor rows into csv. Needs only a warehouse grant. Exact
   pins (scipy 1.18.1), process pools, matplotlib, all work as on the Mac. Results go back
   with `write_pandas` if wanted. This is the recommended route.
2. Notebooks in Workspaces (the current product; legacy notebooks are closed to accounts
   created after April 2026). One notebook cell, or a workspace `.py` file run whole, that
   calls the CLI entry point. Python 3.12 is selectable and the Snowflake Anaconda channel
   carries scipy 1.18.0, numpy 2.5.2, networkx 3.6.1, matplotlib 3.11.0, geopandas 1.1.3,
   shapely 2.1.2, pyproj 3.7.2; pip against the shared PyPI repository works with no
   external-access integration. Costs: a compute pool (usually an admin grant), no documented
   statement on `multiprocessing` (use `--workers 1`, cheap here), pip installs lost on the
   weekend service restart, headless `EXECUTE NOTEBOOK PROJECT` accepts `.ipynb` only, and
   outputs must be pushed to a stage to persist. Feasible, but every one of those is friction
   the local route does not have.
3. Snowpark Container Services job (`EXECUTE JOB SERVICE`, or `snowflake.ml.jobs.submit_file`
   from a laptop). Runs any `.py` with any image, stage volume for outputs. Needs a compute
   pool and, for a custom image, an image repository. Right answer only if the work machine
   cannot run a 10 minute job.

Ruled out: legacy warehouse-runtime notebooks (Python 3.9, no wheels, no process creation)
and Python stored procedures (no process creation, `/tmp` only, packages limited to the
channel or the shared PyPI repo; workable but worse than 2 for no gain).

The pipeline runs on the descaled instance, which has the same optima, gaps and certificates
as the real one at every ρ (`tools/instance_export/README.md`). So even on the work machine
the export step stays: it is the validated entry format, and it is cheap.

## Design

### Layout after the move

```
td/                     the package, the only thing installed
  __init__.py
  cli.py                argparse front end: td export | draw | splits | maps | run
  fetch.py              Snowflake -> the four csv tables (new, ~80 lines, connector only)
  export.py             tools/instance_export/export_instance.py, moved unchanged
  instance.py           as now
  model.py              as now
  channel.py            as now
  geo.py                as now; DEFAULT_DEST becomes an absolute cache dir (see Paths)
  ziptable.py           as now, minus the load-by-path of us_maps
  maps.py               tools/us_maps.py, moved; argparse main kept
  draw.py               tools/run_draw.py, moved; argparse main kept
  splits.py             tools/state_splits.py + tools/borders_report.py, moved
  solvers/
    __init__.py         registry without the scip_tree probe (see Decisions)
    base.py, brute.py, centers.py, state_splits.py, state_borders.py
research/               everything off the live path, moved as-is, not installed
  td_atoms.py, atom_draw.py, cert_draw.py, cert_exact.py, eg_band.py, scip_tree.py
  run_atoms.py, state_borders_tool.py, measure/, state_atoms/, motion_page/, verify/
  instance_export/build_adjacency.py (TIGER fallback, geopandas)
app/                    unchanged; engines.py argv updated to the new module paths
tests/                  unchanged in intent; imports updated for the moves
docs/, literature/      unchanged
```

`tools/` disappears. `tools/app.sh` moves to `app/app.sh`.

Whether `research/` is the right home, or the dead modules stay under `td/` behind an
extra, is Decision 1 below. The plan is written for the move.

### One command

`td run` chains the steps into one work directory:

```
td fetch   --account ... --database ... --out WORK/raw/          (Snowflake -> 4 csv)
td export  WORK/raw/ --out WORK/                                  (-> WORK/instance.json.gz)
td draw    WORK/instance.json.gz --k 18 --seeds 0-9 --out WORK/draw/
td splits  WORK/instance.json.gz --draw WORK/draw/k18/draw.csv --delta 0.05 \
           --anchor-homes --time-limit 600 --out WORK/splits/
td maps    --table WORK/splits/d0.05/draw.csv --out WORK/figures/
td run     --work WORK --k 18 --seeds 0-9 --delta 0.05 [--from draw] [--workers 1]
```

`td run` is a thin loop over the same argparse mains, one function call per step, no new
logic. `--from STEP` restarts at a step whose inputs exist. Every step keeps its current flags
so `docs/HEADLINE.md` §8 stays true after a path substitution.

Stage 2 already runs inside `draw` (its `metrics.json` carries the assignment), so no
separate `match` step is needed.

### Paths

- No relative defaults. `--geo-cache` defaults to `$TD_CACHE/geo`, falling back to
  `~/.cache/td/geo`. The gazetteer and the state outline download from census.gov on a cache
  miss as now; on a machine without internet, copy the two files in by hand or point
  `--geo-cache` at a shared folder. Two files, under 2 MB.
- Output defaults under `battery/results/` go away; `--out` is required, or `td run --work`
  supplies it.
- `td/ziptable.py` imports `td.maps` lazily by name instead of by file path.
- `tests/test_borders_report.py` reads its data paths from `TD_REPO` and skips when unset.

### Dependencies

`pyproject.toml`:

```
dependencies = ["numpy", "scipy", "networkx", "matplotlib", "shapely", "pyproj"]
[project.optional-dependencies]
snowflake = ["snowflake-connector-python[pandas]"]
basemap   = ["geopandas"]          # only geo.states_outline; see Decision 3
research  = ["pyscipopt", "highspy", "mip", "sympy", "mpmath", "geopandas", "pandas"]
```

`requirements.txt` keeps the frozen pins for the hub `.venv` (the zip50 anchor depends on
them) and gains a `requirements-work.txt` with the live-path pins only: numpy 2.5.2, scipy
1.18.1, networkx 3.6.1, matplotlib 3.11.1, shapely 2.1.2, pyproj 3.7.2, plus the connector.
Python 3.12 or 3.13. The macOS cbcbox codesign note leaves with cbcbox.

### Fetch step

`td fetch` runs four queries and writes the four csv files the exporter already reads. The
SQL lives in one file, `td/fetch.sql`, four named statements, edited by hand to the work
schema. Column names are matched by the exporter's existing synonym table, so the queries
only need to return the right columns. The edge table is the open question (Decision 2):
if the rook graph is only a local pyarrow file, `td fetch` copies it in, and
`research/instance_export/build_adjacency.py` stays the TIGER fallback.

Nothing confidential changes hands that did not before: the exporter's guards run unchanged,
and the work directory stays on the work machine.

### Work machine install

```
git clone git@github.com:helios1168/td.git && cd td
python3.12 -m venv .venv && .venv/bin/pip install -e ".[snowflake]" -c requirements-work.txt
.venv/bin/td run --work ~/td-work --k 18 --seeds 0-9 --delta 0.05
```

## Steps (implementation, not started)

1. Move the five live scripts and the exporter into `td/`, fix the imports, delete `tools/`
   after moving the rest to `research/`. Verify: `tests/run_all.py` 331 tests, 0 fail, with
   test imports updated and no other test edits.
2. Absolute cache and output paths; `ziptable` imports `td.maps` by name. Verify: run the
   three drivers from a cwd outside the repo on the hub's `instance_descaled_v2_conus.json.gz`.
3. `td/cli.py` with the five subcommands and `td run`; `[project.scripts] td = "td.cli:main"`.
   Verify: `td run --work /tmp/x --from draw` on a synthetic instance from
   `tests/test_instance.py`'s writer, workers 1 and 8.
4. Regression gate: `td draw` on `instance_descaled_v2conus` with seeds 0 to 9 reproduces
   `battery/results/draw_k18_v2conus_20260907/k18/draw.csv` byte for byte, and `td splits` at
   δ = 5 % with `--anchor-homes --time-limit 600` reproduces `borders_k18_v2conus_20260907`
   `state_shares.csv` and `splits.json` (status, splits, objective). A layout change must not
   move a number.
5. `td fetch` against Snowflake, written blind here with the four column contracts, run first
   on the work machine with `td export validate` (writes nothing) before any export.
6. `pyproject.toml` extras, `requirements-work.txt`, `app/engines.py` argv update,
   `docs/CODE_MAP.md` `## Files` and `## Recipes` rewritten, `docs/HEADLINE.md` §8 paths.
   Verify: `tests/test_docs_owners.py` and the CODE_MAP recipes run as written.

Steps 1 to 4 and 6 run here. Step 5 finishes on the work machine.

## Next step

Decisions below, then step 1 delegated to a subagent with the file list above.

## Done

- 2026-09-08: worktree created and locked; live-path inventory; Snowflake runtime and
  package facts checked; this plan.

## Decisions needed

1. Where the off-path research code goes: `research/` at the repo root (plan above), or left
   in place under `td/solvers/` and `tools/` behind a `research` extra. `research/` is
   cleaner to install and to read; leaving it saves the import edits in six test files and
   keeps `docs/units/*.md` citations valid without a path note. The verify scripts are
   unrunnable either way (deleted worktree paths). Recommendation: `research/`.
2. Which of the four exporter inputs live in Snowflake. Sales and opportunity presumably do.
   State membership can be derived from the gazetteer if absent. The rook edge table was
   described on 2026-08-31 as a local pyarrow cache; if it is not in Snowflake, is loading it
   into a table (33,791 zips, 90,429 edges, public TIGER data) acceptable, or does `td fetch`
   read it from a file?
3. Whether to keep geopandas at all. It serves one function, `geo.states_outline`, the state
   basemap under every figure. shapely 2 plus pyogrio, or a cached GeoJSON in the geo cache,
   would drop geopandas and pandas from the live install. Small change, but it touches the
   figures, so it is a separate decision.
4. Work machine OS and Python. Windows changes the multiprocessing start method and the
   venv paths in the install recipe; nothing in the code, `run_draw.py` already uses a
   module-level pool target.
5. Whether to run on Snowflake at all now, or only from the work machine. The plan makes the
   notebook route a one-cell wrapper around `td run --workers 1`, so it can follow later
   without a second layout.
6. `td/solvers/__init__.py` probes `scip_tree` (pyscipopt) for the registry. On the live
   path nothing uses the registry except `tests/test_engines.py`. Drop the probe and let the
   test import the research module directly, or keep it guarded.

## Files owned / forbidden

Owned: `PLAN.md`; after the decisions, `td/`, `tools/`, `research/`, `tests/`, `app/engines.py`,
`app/app.sh`, `pyproject.toml`, `requirements-work.txt`, `docs/CODE_MAP.md` `## Files` and
`## Recipes`, `docs/HEADLINE.md` §8 only.

Forbidden: `docs/PROBLEM.md`, `docs/MODEL.md`, `docs/APP.md`, `docs/units/`, `docs/foundations/`,
`requirements.txt` pins, `figures/`, `STATE.md`, any number in any result.
