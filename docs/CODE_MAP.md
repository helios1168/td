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

## Files

| file | role |
|---|---|
| `td/model.py` | N-way primitives: schema shim, per-rep utilities, gains, objective, perimeter, per-rep pieces, n-agent EF1 |
| `td/channel.py` | stage 2 (Hungarian on logs), balance report, `place_by_state`, `allocate_districts` (the ceiling / dual bound) |
| `td/instance.py` | loads the descaled real instance into the N-way schema |
| `td/solvers/centers.py` | stage 1: k-means++ seeding, transportation-LP balanced assignment, Lloyd, Nash polish, portfolio; `power_weights` / `power_labels` (the LP duals and the power diagram). `assign()`'s LP is pinned to `method="highs-ds"` with an explicit `options` dict — scipy 1.18.1's HiGHS wrapper hangs on v2 without one (`docs/RUNS.md`) |
| `td/atoms.py` | state atoms for stage 1: whole states, with the oversized groups cut by `centers.draw` (CA 5 / TX 2 / NY+NJ 3 / FL 2, decided 2026-09-06), and their rook adjacency. Owns the AK→WA / HI→CA1 merge and the stateless (`??`) rule, both documented placeholders |
| `td/solvers/atom_draw.py` | stage 1 on an atom graph: multi-restart seeded growth plus connectivity-checked border moves, contiguity verified on the result. `free_search` is the contiguity-dropped **reference, not a bound** — the bound is `cert_draw.cert_balance_ceiling`. Requires `PYTHONHASHSEED=0` |
| `td/solvers/eg_band.py` | U8-band: the band-constrained Eisenberg–Gale program `EG^bal_S(δ)` — `O(nk)` dual bound (no solver in the trusted path), HiGHS outer approximation, SCIP cross-check |
| `td/solvers/cert_draw.py` | four post-hoc certificates: analytic balance ceiling, integer balance floor, assignment optimality at pinned centers (MILP), `cert_power_diagram` (duals as a solver-free `O(nk)`-checkable bound) |
| `td/solvers/scip_tree.py` | the two-player MILP engine — **not** what stage 1 was built on |
| `td/solvers/cert_exact.py` | exact post-hoc certificate (W6c); its AM–GM OA generalises to n terms |
| `td/solvers/{base,brute}.py` | harness contract; brute-force oracle |
| `td/geo.py` + `tools/us_maps.py` | ZCTA points, LAEA projection, state basemap, `state_rook` (the TIGER state rook graph, 49 nodes / 107 edges — the instance cannot supply it, contracted to states its zip graph has 10 edges over 42 components); six figures incl. `figure_power_regions` (the territory map) and `figure_district_regions` (superseded catchment fill, `--regions-voronoi`) |
| `tools/run_draw.py` | the reproducible pipeline: instance → (k, seed) draws on a process pool → stage 2 → `battery/results/<run-id>/k<kk>/` + `sweep.csv`; `--fix`/`--anchor NAME=ST,ST` or `--scenario file.json` for hand-drawn districts; `--k 14-22` is the v2 sweep, `--k 8-16` the v1 regression (pinned to `sweep_20260902_s10`) |
| `tools/run_atoms.py` | the state-atom stage-1 driver: instance → atoms → contiguous draw → `k<kk>/draw.csv` + `metrics.json`, the same shapes `run_draw.py` writes. A separate script rather than a `run_draw.py` flag because the atom route has no coordinate-less gap — a zip with no gazetteer point still has a state, so it still has an atom, and routing it through `place_by_state` would change the draw's value |
| `tools/measure/premium.py` | the premium ladder, U1/U4/U8, verdict conversions |
| `tools/measure/frontier.py` | the D1′ driver: utility-convention gate (`EG_S ≥ V`), the `δ` frontier, `δ*`, first movers, N8/N9, the plot. Background it with `python3 -u` |
| `tools/measure/instance_diff.py` | v1↔v2 comparison: recovers the descaling divisor from the unchanged zips; run on any new export before trusting a sizing figure |
| `tools/instance_export/export_instance.py` | work-machine exporter — stdlib only, single file, **read it before running it** (`tools/instance_export/README.md`) |
| `docs/artifacts/runs/` | the catalogue driver (`run_all.sh`), maps (`make_maps.sh`), generator (`build_artifact.py`), 14 scenario specs |
| `docs/artifacts/U*/` | runnable artifacts behind each MODEL/VERIFY document |
| `docs/channel_note/`, `docs/math_note/` | the LaTeX notes (channel model; the original two-player formulation). `math_note/toy_*.py` import the deleted `code/gfx` and are broken |
| `tests/run_all.py` | 269 fast tests; `-k <name>` filters. `TD_SLOW=1` currently adds nothing — no module sets `SLOW = True` |
| `app/` + `tools/app.sh` | the Streamlit scenario app: define a scenario, run an engine, see the map, save it. Runs in its own venv `.venv-app` and never imports `td` — it drives the drivers by subprocess, which is both the version boundary and the solver-swap seam. `app/engines.py` is the registry; `docs/APP.md` is the whole story |

## Recipes (v2 forms — the live ones)

```
tools/run_draw.py instance_descaled_v2.json.gz --k 18 --seeds 0-9 --workers 8 --out battery/results/draw_k18_v2_20260904
PYTHONHASHSEED=0 tools/run_atoms.py instance_descaled_v2.json.gz --k 18 --reference --out battery/results/atoms_k18_v2_20260906
tools/measure/premium.py instance_descaled_v2.json.gz battery/results/draw_k18_v2_20260904 --out battery/results/meas_v2_20260904
python3 -u tools/measure/frontier.py instance_descaled_v2.json.gz battery/results/draw_k18_v2_20260904 --out battery/results/u8_band_v2_20260904 --figure figures/u8_band_v2/frontier.png
tools/measure/instance_diff.py <old> <new> [--json out.json]
tools/us_maps.py <instance> --out figures/<dir>/ --districts <draw.csv> --regions <draw.csv>
bash docs/artifacts/runs/run_all.sh   # 15 runs, ~14 min; then make_maps.sh and build_artifact.py --date <date>
tools/app.sh                          # the scenario app on 127.0.0.1:8501 (docs/APP.md)
```

## Scenario exploration goes through the app, not a new artifact

When the question is "what does this scenario do" — pin a region, change k, try a different
engine — define it in the Streamlit app and run it there. The app writes the same
`k<kk>/draw.csv` + `metrics.json` that the drivers do, into
`battery/results/app/<scenario>_<timestamp>/`, and renders the maps with `tools/us_maps.py`, so
nothing about the numbers or the figures changes; what changes is that the sponsor can turn the
knobs without a session, and every scenario is saved to `battery/scenarios/<slug>.json` in the
format `run_draw.py --scenario` already accepts.

Build a Claude artifact (`docs/artifacts/runs/build_artifact.py`) only for a **fixed deliverable**
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

## Gitignored inputs (repo root; hand-copy into a `wt/*` worktree)

`.venv-app` is per-worktree and is rebuilt, not copied:
`uv venv --python 3.13 .venv-app && uv pip install --python .venv-app/bin/python3 -r app/requirements.txt`.
The app reads its data from the hub checkout (`TD_REPO`), so the gitignored inputs below do not
need copying for it.


`instance_descaled_v2.json.gz` (**live**, cleaned) · `instance_descaled_v2.raw.json.gz`
(uncleaned, provenance) · `instance_descaled.json.gz` (v1, regression only) · `data/geo/` (the
gazetteer cache) · `battery/results/`: **v2** `draw_k18_v2_20260904`, `u8_band_v2_20260904`,
`meas_v2_20260904`, `runs_20260904/` (the 15 catalogue runs); **v1** `draw_k13_20260901`,
`sweep_20260902_s10`, `meas_20260903`, `u8_band_20260904`.
