# The scenario app — development environment and architecture

A Streamlit application for business users: define a scenario, run it, see the map, save it.
Work happens on branch `worktree-streamlit` in `.claude/worktrees/streamlit`.

## 1. Two virtualenvs, on purpose

| venv | who owns it | what is in it |
|---|---|---|
| `.venv` (repo root) | the solvers | the frozen pins in `requirements.txt` — numpy 2.5.2, scipy 1.18.1, geopandas, SCIP/HiGHS |
| `.venv-app` (this worktree) | the app | streamlit 1.63.0, pandas 3.0.5 (`app/requirements.txt`) |

The solver pins are frozen because the zip50 anchor depends on those exact versions, so
Streamlit's dependency tree must never be allowed to resolve them upward. The app therefore
never imports `td`; it drives the solvers by subprocess. That process boundary is also the
version boundary, and it is what makes a solver swappable (§4).

Rebuild the app venv from scratch:

```
uv venv --python 3.13 .venv-app
uv pip install --python .venv-app/bin/python3 -r app/requirements.txt
```

The app reads its inputs from the hub checkout `/Users/ntlee/projects/td`, because the
gitignored data (`instance_descaled_v2.json.gz`, `data/geo/`, `battery/results/`) is not copied
into a worktree. Override with `TD_REPO` if that ever changes (`app/config.py`).

## 2. Running it

```
tools/app.sh                                  # loopback 127.0.0.1:8501
tools/app.sh --server.address=100.69.120.67   # bind the tailnet address
```

`.streamlit/config.toml` sets `headless = true` and binds loopback by default. Run it inside
tmux so it survives the SSH session dropping.

Use `tools/app.sh` rather than calling Streamlit directly: `streamlit run app/main.py` puts
`app/` on `sys.path` and not the worktree root, so `from app import ...` raises
`ModuleNotFoundError: No module named 'app'` at the first line of the script. The launcher
exports `PYTHONPATH` to fix it.

Smoke test, no browser needed:

```
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8501/healthz    # 200
```

## 3. Reaching it from the iPad

The Mac Studio is `ntlees-mac-studio-1.tail133394.ts.net` / `100.69.120.67` on the tailnet.
Two routes, and the choice is about how much Rootshell can do, not about security — both stay
off the public internet.

**Route A — bind the tailnet address (recommended, no tunnel).** Start the app with
`tools/app.sh --server.address=100.69.120.67` and open `http://100.69.120.67:8501` in Safari on
the iPad. Tailscale's ACLs are the access boundary; the port is never exposed to the LAN or the
internet, and iPadOS needs nothing but the Tailscale app already installed. Browse by the same
address the server bound; if the websocket fails to connect when using a MagicDNS name instead,
that is a Host-header mismatch, and the fix is to use the IP or to add
`server.enableXsrfProtection = false` to `.streamlit/config.toml` (acceptable only on a private
tailnet).

**Route B — SSH local port forward.** From Rootshell:

```
ssh -N -L 8501:127.0.0.1:8501 ntlee@100.69.120.67
```

then open `http://localhost:8501` in Safari. This works only if Rootshell exposes its forwarded
port on the iPadOS loopback interface where Safari can see it; if Safari cannot reach it, the
app is fine and the terminal app is the limitation, so fall back to route A.

Two traps worth naming. Mosh does not forward ports at all, so the usual mosh session cannot
carry route B — it needs a plain `ssh`. And the forward must be `-L`, a local forward; `-R`
would push the iPad's port to the Mac, which is the wrong direction.

## 4. Architecture

The design goal is that a solver from another workstream can be dropped in without the app
changing. The seam that makes that work already exists in the tree: both stage-1 drivers write
the same two files per k.

```
<run>/k<kk>/draw.csv       zip,district
<run>/k<kk>/metrics.json   k, seeds, scenario, winner, summary[], draws[]
```

`tools/run_draw.py` (power cells) and `tools/run_atoms.py` (state atoms) already agree on it, by
deliberate design (`docs/CODE_MAP.md`). The app depends on that contract and on nothing else
about how a draw was produced.

Layers, app venv on the left, solver venv on the right:

| module | role |
|---|---|
| `app/config.py` | paths, and the `TD_REPO` override |
| `app/scenario.py` | the saved scenario record: load, save, validate |
| `app/engines.py` | one entry per solver: driver, argv builder, required env, which scenario fields it honours |
| `app/runner.py` | launch an engine detached, poll its status, cancel it, render its maps |
| `app/runs.py` | discover run directories, read `metrics.json` / `draw.csv` |
| `app/headline.py` | the Headline tab's own logic: the shipped cell's numbers, the cap floor, and the diff against the headline |
| `app/main.py` | the UI: a Define-and-run tab, a Results tab and a Headline tab |

**Scenario format.** Do not invent one. `run_draw.py` already accepts
`--scenario file.json` with exactly `{"fix": {NAME: [ST, ...]}, "anchor": {...}}` and rejects
unknown keys, and fourteen such files live in `tools/verify/runs/scenarios/`. The app's saved
record is that object plus the run parameters it needs (engine, k, seeds, instance) and the
business metadata (name, notes, author, saved-at), stored at
`battery/scenarios/<name>.json`. At launch time `app/runner.py` writes the stripped
`{fix, anchor}` object into the run directory and passes that path to the driver, so there is
one user-facing file and no second format to keep in sync.

**Engine registry.** One entry per solver, holding the driver path, a function from a scenario
to argv, the environment it needs, and the scenario fields it honours. Two entries today:

- `power-cells` — `tools/run_draw.py`, honours `fix` and `anchor`, k sweep, seeds.
- `state-atoms` — `tools/run_atoms.py`, requires `PYTHONHASHSEED=0` (it refuses to start
  without it), takes a cut plan rather than `fix`/`anchor`.

Those two already disagree about which scenario fields mean anything, which is why the registry
records that rather than assuming every engine takes the same knobs. The UI greys out the fields
the selected engine does not honour. Adding a third workstream's solver is one registry entry,
as long as it writes the two files above.

**Running is asynchronous.** A `run_draw.py` sweep takes about 56 s at k = 14–22 with 10 seeds
on 8 workers, so a run cannot block a Streamlit script rerun. `app/runner.py` launches the
driver detached, writes its stdout to a log inside the run directory, and the UI polls for the
output files. Runs land in `battery/results/app/<scenario>_<timestamp>/`, which is already
gitignored.

**Maps: static PNGs, decided 2026-09-06.** `app/runner.render_maps` calls `tools/us_maps.py`
through the same subprocess boundary and the UI displays the PNGs it writes (`districts.png`,
`district_regions.png`, `district_regions_voronoi.png`). One implementation of the map, and the
app inherits the fixes made for the CA5 measurement. The cost is no pan or zoom, and about 40 s
per render including the gazetteer load. `--regions`, the power diagram, is asked for only when
the engine produced a center-based draw; `--regions-voronoi` applies to any draw.

Renderings land in `battery/results/app/figures/<run>/k<kk>/`, not in `figures/`. The tracked
`figures/` directory holds committed, reviewed artifacts, and app output is neither.

**The Headline tab, added 2026-09-07.** One hard-wired case rather than a free scenario: the
`borders-headline` engine entry reruns the shipped Track 2 anchored cell with exactly the
committed run parameters (`--draw` the committed k = 18 draw, `--anchor-homes`, `--eta 0.01`,
`--rounds 5`, `--time-limit 600`), so only `δ` and the per-state caps vary and a diff against the
result is a diff against the headline rather than against a different experiment. The entry is
`listed: False`, so it does not appear in the Define-and-run engine picker.

A cap is refused before launch when it falls below the state's arithmetic floor
`⌈M_s / ((1+δ)τ)⌉`, read from `--dump-state-shares`. A cap at or above the floor but below the
state's anchored count releases that state's anchors, keeping the cap-many that hold the most of
its committed opportunity; the tab warns and lets it run, because the anchors are what hold a
state above its floor, not the floor itself. The floor is necessary and not sufficient:
California at 4 is legal at δ = 5% and HiGHS found no feasible point in an hour.
`docs/HEADLINE.md` §7 carries what that does and does not prove.

## 5. Assumptions on the record

1. Business users define scenarios and launch runs from the browser; the app is not a read-only
   viewer of runs someone else started.
2. One user at a time, over the tailnet. No authentication, no multi-tenant session state.
3. Both engines are wired, but only the power-cell one has been exercised end to end from the
   app. The state-atom entry builds `--cut` arguments and sets `PYTHONHASHSEED=0`; it has not
   been launched through `app/runner.py` yet.
4. The live instance is `instance_descaled_v2.json.gz` at k = 18, and it is confidential. It
   never leaves the Mac Studio; the app displays derived numbers only.
5. Nothing downstream of a real `runner.launch` is covered by a test. Streamlit cannot be driven
   headlessly, so the Headline tab's run, cancel and render flow has been exercised by hand and
   by nothing else. The cap floor and the anchor-release rule are unit-tested
   (`tests/test_state_splits_cli.py`); the UI around them is not.
