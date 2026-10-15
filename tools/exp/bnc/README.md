# tools/exp/bnc: exact ZIP drawing by lazy connectivity cuts (#142 phase 0)

Question: can an unrestricted exact ZIP model with lazy connectivity cuts draw the national coupled
groups that the restricted-first pipeline never finished? Four hard groups, four solvers of the same
model and objective, then the gate.

| file | what |
|---|---|
| `capture.py` | runs `draw._solve_group` (draw.py is not changed) up to its first MILP solve and keeps the model; the stand-ins that give an exported call back to draw.py |
| `export.py` | replays the run that drew a group and writes `instances/<id>.json.gz`; the faithfulness and round-trip checks |
| `inst_io.py`, `sepcuts.py` | instance I/O and the HiGHS model; minimal a,b-separator rows (integer and fractional) |
| `arms.py` | arms a, b, c, d |
| `run.py`, `report.py` | one (instance, arm) per process, the gate, `REPORT.md` |
| `synth.py` | the grids of `tests/test_bnc.py` |

## The instances

`export.py` replays each run with `draw._solve_group` wrapped (earlier groups of a sequential run take
their drawing from the run's ledger), captures the target call and builds the instance's MILP with
`dag` False, no flow, no repair rows and no neck cuts: draw.py's complete group model, objective
included (split weight 1000, border, moment tie-break, land term). Checks written into each
instance's `meta`: `faithful` (the same call with the run's own flags has the columns and rows its
`contig.json` recorded) and `roundtrip` (the MILP rebuilt from the instance alone by draw.py's code
equals the exported one, column by column and row by row). Both are fatal on a mismatch.

`widths` (a top-level section, apart from the objective's border coefficients in `draw.border`): for
the group's ZCTAs, its bodies' ZCTAs and their neighbours, the gate's width data from the 2025 polygon
graph (`capture.width_data`): `border` (polygon edges, metres), `connectors` (approved passages),
`gaps` (land-only gap widths), `aland`, `state`, and `relays` (zero-opportunity ZCTAs of the set).

| id | run | group |
|---|---|---|
| `FI_PA` | `main/ne-48-bal/rest-FI-WH-national/draw`, FI group 4 | 4 districts, 1,833 free ZCTAs, 12,115 columns |
| `FI_FL` | `main/ne-50-bal/rest-FI-WH-national/draw`, FI group 2 | 3 districts, 1,013 ZCTAs, 5,619 columns |
| `FI_NY` | `warm/ne-50-bal/r2` + `r3`, FI repair window, corridor slack 1 around FI_19 (NY+PA+WV#1, 4 pieces) | 5 districts, 223 ZCTAs, 4,466 columns with the repair's flow and cap rows; 1,167 in the instance |
| `WIFI_MD` | m2 `main_nw49/nw49-50/rest/draw`, WIFI group 0 | 3 districts, 477 ZCTAs, 2,567 columns |

The m2 inputs were copied to `/tmp/bnc_in/m2` (`draw/{contig.json,ledger.csv,districts.csv,manifest.json,run.json}`,
`spec.toml`, `plans/<pkl>`, `merged/` = `warm_m2/nw49-50/pass2_merged`); the extract has the same
sha256 on both machines.

```
export TD_REPO=/Users/Shared/sv-ntlee/td; TD_PY=$TD_REPO/.venv/bin/python3
"$TD_PY" -u tools/exp/bnc/export.py --out "$TD_REPO/runs/exp/bnc_2026-10-15/instances" [--only FI_PA ...] [--m2-dir /tmp/bnc_in/m2]
```

## The arms (`arms.py`)

All at `mip_rel_gap` 0 (trap 12), absolute gap 1e-6, one process each, `--threads` for HiGHS (one value
per process, trap 18; SCIP runs one thread, so the comparison runs use `--threads 1`), `--time-limit` wall seconds.

- **a** draw.py's own solve path on the instance's call: `dag` False, single-commodity flow rows and
  per-layer separators (`--no-flow` drops the flow), then its solve-check-cut loop. It also starts from
  `construct`'s drawing when it finds one (none of the four instances had one at export, except FI_PA).
- **b** HiGHS: solve, find each district's detached components in the integer optimum, add minimal
  a,b-separator rows (Validi-Buchanan-Lykhovyd; minimal as in Fischetti et al.), solve again. No flow.
- **c** PySCIPOpt 6.2.1 / SCIP 10: a constraint handler (`conscheck`, `consenfolp`, `consenfops`,
  `conslock`) adding the same rows as lazy cuts at the node; `--frac-root` also separates fractional rows
  at the root (max flow with vertex capacities x).
- **d** HiGHS `kCallbackMipDefineLazyConstraints`: a 20-node probe (`arms.probe_highs_lazy`). highspy
  1.15.1 never invokes the callback and its input has no field to define a row, so the arm's status is
  `not usable` with what the probe saw. `tests/test_bnc.py` fails if a later highspy changes that.

Status: `optimal` (connected optimum proved), `feasible` (connected drawing, not proved), `infeasible`
(proved that no connected drawing exists in the group under the model's rules), `unknown`, `not usable`.

Comparability notes, all reported by the runs: arm a is the only one given a constructed start and the
flow rows; arm a's HiGHS stops its first phase at an absolute gap of 0.05 until a connected drawing
exists (draw.py's `PHASE1_GAP`), as implemented; the instances from sequential runs (`FI_PA`, `FI_FL`,
`WIFI_MD`) count districts' undrawn parts at their *planned* masses (`extra`), so a drawing that solves
the model can still leave a district out of its dollar window once the rest of the district is what the
map has; the gate reports that as a failure.

## Running

One arm on one instance (log, `result.json`, `ledger.csv`, `merged/` under
`$TD_REPO/runs/exp/bnc_2026-10-15/<instance>/<arm>/`):

```
"$TD_PY" -u tools/exp/bnc/run.py one FI_PA b --time-limit 7200 --threads 1
```

The long runs (4 instances × 4 arms, 2 h each, 4 at a time with 1 thread each, the thread count SCIP runs
with, so the arms compare like for like (A1); the REPORT is written at the end, or rerun `report.py`):

```
cd <worktree>; export TD_REPO=/Users/Shared/sv-ntlee/td; TD_PY=$TD_REPO/.venv/bin/python3
nohup "$TD_PY" -u tools/exp/bnc/run.py all --time-limit 7200 --threads 1 --jobs 4 \
    > "$TD_REPO/runs/exp/bnc_2026-10-15/all.log" 2>&1 &
```

After a drawing is returned the gate always runs on it (there is no bypass): the group's ZCTAs replaced in the source map's full
ledger (`warm/ne-48-bal/merged`, `warm/ne-50-bal/merged`, m2 `pass2_merged`), `tools/mandates/check.py`'s
`m1` on the full graph (relays, necks as the gate has them) and `tools/looks/score.py`'s `dollar_gate`.
`gate.m1` is the gate's verdict on the whole merged map (`pass`, `fail` or `ungated`), less only the
detached-piece and neck items of districts outside the group that the gate also reports, with the same text, on the
unmodified source map (`gate.m1_excluded` lists them); coverage, ownership, routing and unverified results are never
left out. `gate.map_m1` is the merged map's raw status. The arm folder and `merged/` each
get a `manifest.json` (mandate T1, `run.write_manifest`), `failed` when the run raised.

`"$TD_PY" tests/run_all.py -k bnc`: three grids on which every arm returns the same optimum and a
connected drawing; the separator rows are valid and minimal; the round trip detects a change; the probe.
