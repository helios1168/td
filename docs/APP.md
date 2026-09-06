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

| module | role | status |
|---|---|---|
| `app/config.py` | paths, and the `TD_REPO` override | built |
| `app/runs.py` | discover run directories, read `metrics.json` / `draw.csv` | built |
| `app/main.py` | the UI | walking skeleton: browse a run, district table, balance numbers, map |
| `app/scenario.py` | the saved scenario record: load, save, validate | planned |
| `app/engines.py` | one entry per solver: driver script, argv builder, required env, which scenario fields it honours | planned |
| `app/runner.py` | launch an engine as a subprocess, stream progress, collect the run directory | planned |

**Scenario format.** Do not invent one. `run_draw.py` already accepts
`--scenario file.json` with exactly `{"fix": {NAME: [ST, ...]}, "anchor": {...}}` and rejects
unknown keys, and fourteen such files live in `docs/artifacts/runs/scenarios/`. The app's saved
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

**Maps.** Version 1 reuses `tools/us_maps.py` through the same subprocess boundary and displays
the PNG it writes (`districts.png`, `district_regions.png`, `district_regions_voronoi.png`). That
keeps one implementation of the map and inherits the fixes made for the CA5 measurement. The cost
is no pan or zoom and about 3 s per render; an interactive in-browser map would need the
geometry reimplemented on the app side, which is a decision to make after business users have
seen the static one.

## 5. Assumptions on the record

1. Business users define scenarios and launch runs from the browser; the app is not a read-only
   viewer of runs someone else started.
2. One user at a time, over the tailnet. No authentication, no multi-tenant session state.
3. Only the power-cell engine is wired first, because it is the one that honours `fix` and
   `anchor` — the hand-drawn-district knobs the scenario UI is about.
4. The live instance is `instance_descaled_v2.json.gz` at k = 18, and it is confidential. It
   never leaves the Mac Studio; the app displays derived numbers only.
