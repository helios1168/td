# Code map and run recipes

What is built, where, and how to run it. State lives in `STATE.md`; the problem and the model
are `docs/CHANNEL.md` and `docs/MODEL.md`. Keep this file to facts about the tree.

## Two stages

| stage | problem | where |
|---|---|---|
| **1 — draw** | k balanced **compact** districts on opportunity alone (contiguity abandoned: the sold-zip graph has 547 components); the territory is a power diagram | `td/solvers/centers.py`, certificates in `td/solvers/cert_draw.py` |
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
| `td/solvers/eg_band.py` | U8-band: the band-constrained Eisenberg–Gale program `EG^bal_S(δ)` — `O(nk)` dual bound (no solver in the trusted path), HiGHS outer approximation, SCIP cross-check |
| `td/solvers/cert_draw.py` | four post-hoc certificates: analytic balance ceiling, integer balance floor, assignment optimality at pinned centers (MILP), `cert_power_diagram` (duals as a solver-free `O(nk)`-checkable bound) |
| `td/solvers/scip_tree.py` | the two-player MILP engine — **not** what stage 1 was built on |
| `td/solvers/cert_exact.py` | exact post-hoc certificate (W6c); its AM–GM OA generalises to n terms |
| `td/solvers/{base,brute}.py` | harness contract; brute-force oracle |
| `td/geo.py` + `tools/us_maps.py` | ZCTA points, LAEA projection, state basemap; six figures incl. `figure_power_regions` (the territory map) and `figure_district_regions` (superseded catchment fill, `--regions-voronoi`) |
| `tools/run_draw.py` | the reproducible pipeline: instance → (k, seed) draws on a process pool → stage 2 → `battery/results/<run-id>/k<kk>/` + `sweep.csv`; `--fix`/`--anchor NAME=ST,ST` or `--scenario file.json` for hand-drawn districts; `--k 14-22` is the v2 sweep, `--k 8-16` the v1 regression (pinned to `sweep_20260902_s10`) |
| `tools/measure/premium.py` | the premium ladder, U1/U4/U8, verdict conversions |
| `tools/measure/frontier.py` | the D1′ driver: utility-convention gate (`EG_S ≥ V`), the `δ` frontier, `δ*`, first movers, N8/N9, the plot. Background it with `python3 -u` |
| `tools/measure/instance_diff.py` | v1↔v2 comparison: recovers the descaling divisor from the unchanged zips; run on any new export before trusting a sizing figure |
| `tools/instance_export/export_instance.py` | work-machine exporter — stdlib only, single file, **read it before running it** (`tools/instance_export/README.md`) |
| `docs/artifacts/runs/` | the catalogue driver (`run_all.sh`), maps (`make_maps.sh`), generator (`build_artifact.py`), 14 scenario specs |
| `docs/artifacts/U*/` | runnable artifacts behind each MODEL/VERIFY document |
| `docs/channel_note/`, `docs/math_note/` | the LaTeX notes (channel model; the original two-player formulation). `math_note/toy_*.py` import the deleted `code/gfx` and are broken |
| `tests/run_all.py` | 222 fast tests; `TD_SLOW=1` adds the slow anchor tier; `-k <name>` filters |

## Recipes (v2 forms — the live ones)

```
tools/run_draw.py instance_descaled_v2.json.gz --k 18 --seeds 0-9 --workers 8 --out battery/results/draw_k18_v2_20260904
tools/measure/premium.py instance_descaled_v2.json.gz battery/results/draw_k18_v2_20260904 --out battery/results/meas_v2_20260904
python3 -u tools/measure/frontier.py instance_descaled_v2.json.gz battery/results/draw_k18_v2_20260904 --out battery/results/u8_band_v2_20260904 --figure figures/u8_band_v2/frontier.png
tools/measure/instance_diff.py <old> <new> [--json out.json]
tools/us_maps.py <instance> --out figures/<dir>/ --districts <draw.csv> --regions <draw.csv>
bash docs/artifacts/runs/run_all.sh   # 15 runs, ~14 min; then make_maps.sh and build_artifact.py --date <date>
```

The v1 runs reproduce by swapping the instance and draw back and adding
`--gate-reference 60.6974156139` to `frontier.py`. The two catalogue shell scripts date their
output directory by `date +%Y%m%d`, so a re-run lands in `runs_<today>`. `us_maps.py` also emits
the four base figures into `--out`; ~3 s per k with the gazetteer cached.

## Gitignored inputs (repo root; hand-copy into a `wt/*` worktree)

`instance_descaled_v2.json.gz` (**live**, cleaned) · `instance_descaled_v2.raw.json.gz`
(uncleaned, provenance) · `instance_descaled.json.gz` (v1, regression only) · `data/geo/` (the
gazetteer cache) · `battery/results/`: **v2** `draw_k18_v2_20260904`, `u8_band_v2_20260904`,
`meas_v2_20260904`, `runs_20260904/` (the 15 catalogue runs); **v1** `draw_k13_20260901`,
`sweep_20260902_s10`, `meas_20260903`, `u8_band_20260904`.
