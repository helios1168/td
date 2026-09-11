# Track: simplified

## Goal

Make the live pipeline runnable end to end on the work RHEL server from one command line.
The server has a shell like the development machine; the four input tables arrive as files
(csv or parquet), as the exporter already expects. The live pipeline is the one `docs/HEADLINE.md` §8 reproduces:
export the descaled instance, draw k districts (stage 1), split states at a band δ (level 1
and level 2), render the zip table, match reps (stage 2). Everything else in the repo is
research record and stays runnable where it is runnable today, but off the install path.

Status 2026-09-08: design only. Nothing implemented. The Snowflake route (notebooks, container
jobs, connector) was assessed the same day and set aside; the record is in this file's git
history (`6faf2fb`), and nothing in the layout below depends on it.

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

## RHEL server: what has to hold

- x86_64 Linux. Every live-path dependency ships a manylinux wheel at the hub's pins (numpy
  2.5.2, scipy 1.18.1, networkx 3.6.1, matplotlib 3.11.1, shapely 2.1.2, pyproj 3.7.2,
  geopandas 1.1.4, pyogrio 0.13.0, pandas 3.0.5), so no compiler and no system GEOS or PROJ
  is needed. The macOS cbcbox codesign note does not apply and leaves with cbcbox.
- Python. The hub `.venv` is 3.13. RHEL 9 appstreams stop at 3.12 and RHEL 8 at 3.12 as
  well, so the match is `uv python install 3.13` into the user's home, no root and no dnf.
  Falling back to a dnf `python3.12` is fine for the code (`requires-python >= 3.11`), but
  it is a second interpreter version to reason about when a number differs, so 3.13 via uv
  is the plan. Decision 4 asks which is allowed.
- No display. `us_maps.py` already sets `matplotlib.use("Agg")` inside `_canvas`; nothing
  else touches a GUI.
- Process pools use `fork` on Linux, `spawn` on macOS. `run_draw.py` keeps its pool target
  module-level and its `main` under `__name__ == "__main__"`, so both work. The hub's
  numbers were produced under `spawn`; the regression gate in step 4 is what proves the
  start method does not move a number (it should not: each job seeds its own RNG).
- Internet. `td/geo.py` fetches two census.gov files on a cache miss (gazetteer, state
  outline, under 2 MB together). If the server has no outbound HTTP, copy `data/geo/` from
  the hub once and pass `--geo-cache`. Decision 5.
- Inputs. The exporter reads sales, opportunity, edges and states from csv, and parquet or
  feather for the edge table with pyarrow present. Whatever produces those files on the
  server is outside this track; the exporter's guards run unchanged.

The pipeline runs on the descaled instance, which has the same optima, gaps and certificates
as the real one at every ρ (`tools/instance_export/README.md`). So even on the server the
export step stays: it is the validated entry format, and it is cheap.

## Design

### Layout after the move

```
td/                     the package, the only thing installed
  __init__.py
  cli.py                argparse front end: td export | draw | splits | maps | run
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
td export  --sales S --opportunity O --graph E --states T --out WORK/  (-> WORK/instance.json.gz)
td draw    WORK/instance.json.gz --k 18 --seeds 0-9 --out WORK/draw/
td splits  WORK/instance.json.gz --draw WORK/draw/k18/draw.csv --delta 0.05 \
           --anchor-homes --time-limit 600 --out WORK/splits/
td maps    --table WORK/splits/d0.05/draw.csv --out WORK/figures/
td run     --work WORK --k 18 --seeds 0-9 --delta 0.05 [--from draw] [--workers 1]
```

`td run` is a thin loop over the same argparse mains, one function call per step, no new
logic. `--from STEP` restarts at a step whose inputs exist; `--from draw` is the usual entry
once `WORK/instance.json.gz` exists, since the export asks for confirmation and is run once. Every step keeps its current flags
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
basemap   = ["geopandas"]          # only geo.states_outline; see Decision 3
parquet   = ["pyarrow"]            # exporter edge table in parquet or feather
research  = ["pyscipopt", "highspy", "mip", "sympy", "mpmath", "geopandas", "pandas"]
```

`requirements.txt` keeps the frozen pins for the hub `.venv` (the zip50 anchor depends on
them) and gains a `requirements-work.txt` with the live-path pins only: numpy 2.5.2, scipy
1.18.1, networkx 3.6.1, matplotlib 3.11.1, shapely 2.1.2, pyproj 3.7.2, and geopandas 1.1.4
with pyogrio 0.13.0 and pandas 3.0.5 while Decision 3 is open. Python 3.13.

### Server install

```
curl -LsSf https://astral.sh/uv/install.sh | sh          # or copy the uv binary in
git clone git@github.com:helios1168/td.git && cd td      # or unpack a tarball of the branch
uv python install 3.13
uv venv --python 3.13 .venv && uv pip install --python .venv/bin/python3 -e ".[basemap,parquet]" -c requirements-work.txt
.venv/bin/td export validate --sales S --opportunity O --graph E --states T    # writes nothing
.venv/bin/td export export   --sales S --opportunity O --graph E --states T --out ~/td-work
.venv/bin/td run --work ~/td-work --from draw --k 18 --seeds 0-9 --delta 0.05 --workers 8
```

If uv is not allowed, `python3.12 -m venv` from the dnf appstream and `pip install` with the
same constraints file; the code path is identical. A server without outbound HTTP needs the
wheels and `data/geo/` carried in by hand once (`pip download -r requirements-work.txt` on
the hub, then `pip install --no-index --find-links`).

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
5. `pyproject.toml` extras, `requirements-work.txt`, `app/engines.py` argv update,
   `docs/CODE_MAP.md` `## Files` and `## Recipes` rewritten, `docs/HEADLINE.md` §8 paths.
   Verify: `tests/test_docs_owners.py` and the CODE_MAP recipes run as written.
6. Linux dry run here before the server: the install recipe and `td run --from draw` on the
   synthetic instance inside a `python:3.13` container on the Mac, so the first server
   session is not the first Linux run. Verify: same `draw.csv` as step 3 produced on macOS.

Steps 1 to 6 run here. The server run is the user's, with `td export validate` first.

## Next step

Decisions below, then step 1 delegated to a subagent with the file list above.

## Done

- 2026-09-08: worktree created and locked; live-path inventory; Snowflake runtime and
  package facts checked, route set aside the same day; this plan, retargeted at a RHEL server.

## Decisions needed

1. Where the off-path research code goes: `research/` at the repo root (plan above), or left
   in place under `td/solvers/` and `tools/` behind a `research` extra. `research/` is
   cleaner to install and to read; leaving it saves the import edits in six test files and
   keeps `docs/units/*.md` citations valid without a path note. The verify scripts are
   unrunnable either way (deleted worktree paths). Recommendation: `research/`.
2. How the four exporter inputs reach the server, and in which format. The exporter takes
   csv for all four and parquet or feather for the edge table. The rook edge table was a
   local pyarrow file on 2026-08-31; if it is unavailable on the server,
   `research/instance_export/build_adjacency.py` rebuilds it from the TIGER shapefiles
   (needs geopandas and the two zip files). Nothing to build here until this is known.
3. Whether to keep geopandas at all. It serves one function, `geo.states_outline`, the state
   basemap under every figure. shapely 2 plus pyogrio, or a cached GeoJSON in the geo cache,
   would drop geopandas and pandas from the live install. Small change, but it touches the
   figures, so it is a separate decision.
4. Python on the server: uv-managed 3.13 in the home directory (matches the hub, no root),
   or the dnf `python3.12` appstream. Also RHEL major version and whether uv or any binary
   download is permitted.
5. Outbound HTTP from the server: to PyPI for the install and to census.gov for the two
   gazetteer files. If neither, the wheels and `data/geo/` travel with the code.
6. `td/solvers/__init__.py` probes `scip_tree` (pyscipopt) for the registry. On the live
   path nothing uses the registry except `tests/test_engines.py`. Drop the probe and let the
   test import the research module directly, or keep it guarded.

## Files owned / forbidden

Owned: `PLAN.md`; after the decisions, `td/`, `tools/`, `research/`, `tests/`, `app/engines.py`,
`app/app.sh`, `pyproject.toml`, `requirements-work.txt`, `docs/CODE_MAP.md` `## Files` and
`## Recipes`, `docs/HEADLINE.md` §8 only.

Forbidden: `docs/PROBLEM.md`, `docs/MODEL.md`, `docs/APP.md`, `docs/units/`, `docs/foundations/`,
`requirements.txt` pins, `figures/`, `STATE.md`, any number in any result.
