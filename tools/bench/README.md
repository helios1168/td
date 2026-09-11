# MILP engine bench

Compares the level-1 minimum-splits MILP (`td.solvers.state_splits.SplitProblem`) across
solvers, on the real instance, to find the fastest route to a proven-optimal split count at
`k = 18` and `k = 20` (docs/CODE_MAP.md; the runtime table there shows HiGHS through
`scipy.optimize.milp` capped at 600 s and stuck one split short of proof at `k = 20`).

## Build `.venv-opt`

The `cpsat` engine runs out of process in a third virtualenv, so `ortools` never touches the
`.venv` pins the app and the zip50 anchor are frozen against.  Build it from the hub root:

```
uv venv --python 3.13 "$(git rev-parse --show-toplevel)/.venv-opt"
uv pip install --python "$(git rev-parse --show-toplevel)/.venv-opt/bin/python3" \
    -r tools/bench/requirements-opt.txt
```

Resolved 2026-09-08: `ortools==9.15.6755`, `numpy==2.5.3` (plus their own dependencies --
`absl-py`, `immutabledict`, `protobuf`, `pandas`, `python-dateutil`, `six`,
`typing-extensions` -- pulled in by `ortools`/`pandas`, not pinned directly).
`requirements-opt.txt` pins the two direct dependencies to these versions.

`scipy`, `highs` (`highspy`) and `scip` (`pyscipopt`) run in the ordinary `.venv`; both packages
are already installed there.

## Usage

```
.venv/bin/python3 -u tools/bench/milp_bench.py instance_descaled_v2_conus.json.gz \
    --draw battery/results/app/draw_grid-k20_20260908_144239/k20/draw.csv \
    --ks 18,20 --cap 180
```

- `--ks` a comma-separated list; each `k` must match the `k` the given `--draw` was drawn at
  (one `--draw` per bench run, same as `tools/state_splits.py`).
- `--cap` seconds, the time limit passed to every solver-backed variant (the heuristic ignores
  it -- it runs in milliseconds).
- `--variants a,b` runs only that subset, still in the table's order below; a `*-cutoff` or
  `*-warm` variant needs an earlier variant in the same run to have produced an incumbent, or
  the bench exits with a usage error naming which.
- `--out DIR` overrides the output directory (default `battery/results/bench` under the hub
  root, `app.config.RESULTS / "bench"`).

Writes `battery/results/bench/milp_<stamp>.json`:
`{instance, draw, cap, ks, variants, rows: [{k, variant, status, objective, dual_bound, gap,
splits, seconds, nodes, trajectory: [[t, primal, dual], ...]}, ...]}` and prints one line per
`(k, variant)` as it runs.

## Variants (run in this order)

| variant | engine | exact? |
|---|---|---|
| `scipy` | today's `state_splits.solve`, the baseline | yes |
| `highs` | `highspy` direct, 12 threads, `mip_rel_gap=0` | yes |
| `highs-root` | `highs` plus the flow root fixed at each district's home state | yes |
| `scip` | `pyscipopt`, default emphasis | yes |
| `scip-root` | `scip` plus the flow root fixed | yes |
| `lp-heur` | reweighted-L1 relaxation, milliseconds | no (primal, upper bound only) |
| `cpsat` | OR-Tools CP-SAT, 12 workers, `y`/flow discretised, out of process in `.venv-opt` | no (primal, upper bound only) |
| `highs-root-cutoff` / `scip-root-cutoff` | roots fixed, `with_cutoff(best incumbent so far)` asked for feasibility -- infeasible certifies the incumbent optimal | yes |
| `highs-root-warm` / `scip-root-warm` | roots fixed, MIP-started from the best primal solution so far | yes |

No Gurobi (no licence). `status` is `0` at proven optimality, `"time_limit"` for a time-limited
incumbent, `"heuristic"` for `lp-heur` (no certificate by construction), or the `SolveFailure`
reason (`"infeasible"`, `"no_incumbent"`) when a variant found nothing usable -- that row still
gets written, with every other field `None`, so a killed run keeps what already finished.

Acceptance for adopting a winning engine (`docs/CODE_MAP.md`, W3b): `k = 20` proven optimal in
under 120 s. If nothing gets there, the lazy-cut connectivity formulation (W4) is conditional
on this bench's own numbers.
