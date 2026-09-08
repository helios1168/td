# Track: the zip table as the pipeline's core unit

## Goal

Make one row per instance zip the thing every stage passes on, instead of a `{zip: district}`
dict in memory and a two-column `draw.csv` at the end. `draw.csv` becomes that table
(`zip,state,x,y,opportunity,district`), so a map needs no instance and no gazetteer join, and
every intermediate step of a solver can be written out and drawn exactly like a final draw.

Acceptance: 321 existing tests plus the new ones green; the stage-1 and level-2 CONUS runs
reproduce the shipped labellings zip for zip; the level-2 map is clipped per state.

## Next step

None. The work is finished and committed; the branch is ready for the orchestrator to review.

## Done

- `td/ziptable.py`: `build`, `read`, `write`, `labels`, `masses`, `balance`, `render`. The
  module loads `tools/us_maps.py` by path (tools/ is not a package) and calls the existing
  builders with per-state clipping and heavy state lines always on.
- `td/solvers/centers.py`: `draw` returns `iterates`, the `(name, labels)` trajectory
  (`lloyd_00`.., `rounded`, `polished`). Nothing in the loop reads it.
- `td/solvers/state_splits.py`: `realise` returns `trajectory`, `(state, round, labels of every
  zip at that moment)`, which is what a driver needs to write a whole-instance step table.
- `tools/run_draw.py`: writes `k<kk>/steps/NN_<name>.csv` for the winning draw, `draw.csv` in
  the new schema, `steps` in `metrics.json`, and gained `--maps` (default off) / `--maps-steps`.
- `tools/state_splits.py`: per cell writes `state_shares.csv` (level 1's whole decision) and
  `steps/NN_realise_<ST>_r<r>.csv` plus `NN_completed.csv`; gained `--maps-steps`; loads the
  basemap once per run rather than once per cell.
- `tools/borders_report.py`: `draw.csv` is a zip table; `write_cell` gained `steps=`;
  `render_cell_maps` renders in-process from the table instead of shelling out to us_maps.
- `tools/us_maps.py`: `--table PATH` renders a zip table with no instance and no gazetteer.
- `tools/measure/{frontier,premium}.py`: `read_draw` checks for the two columns by name instead
  of pinning the whole header.
- `app/headline.py`: the draw diff selects `zip,district` before merging.
- `tests/test_ziptable.py` (new, 9 tests); `tests/test_borders_report.py` updated for the new
  schema and given a test for `write_cell(steps=)`.

## Decisions needed

Taken here, where the brief left the choice open. None of these needs an answer to proceed.

1. **Two per-round mechanisms in `write_cell`, one writer underneath.** `iterates=` stays
   exactly as it was (Track 1, `tools/state_borders.py`, and `tools/motion_page/steps_data.py`
   reads `d0.05_lam100/iterates/*.csv` by that name); `steps=` is the new named form. Both write
   through `ziptable.write`, so the file format is one thing. Converting Track 1 to `steps/`
   would have moved files the motion page reads, which is outside this refactor.
2. **`render_cell_maps` always draws the final table**, so `--no-maps --maps-steps` on
   `tools/state_splits.py` still writes `figures/`. `tools/run_draw.py`, whose `--maps` defaults
   off, does honour the two flags separately.
3. **No CONUS-box filter in `build`.** `render` draws every row that has an `x,y`, whatever the
   caller's `xy` dict carried; `tools/us_maps.py`'s own CLI path still drops points outside the
   lower 48. The live instance is CONUS-only, so the two agree today. A non-CONUS instance drawn
   from a table would stretch the frame to Alaska.
4. **`balance(rows, k)` uses `total / k` as the target**, not the mean of the districts present,
   so a table missing a district reads as unbalanced rather than balanced over fewer.
5. **`render_cell_maps` no longer writes the four instance figures** (`opportunity.png`,
   `firm_a.png`, `firm_b.png`, `contestability.png`) into a cell's `figures/`. They were a side
   effect of shelling out to the whole `us_maps` CLI and say nothing about the cell.
6. **`borders_report.SOLVER_PYTHON` removed** -- the subprocess it existed for is gone.
7. **`ctx.d` is now required by `write_cell`**, which reads the instance for state and mass.
   `tests/test_borders_report.py` builds a three-node `Descaled` instead of passing `d=None`.

## Files owned / forbidden

Owned: `td/ziptable.py`, `td/solvers/centers.py` (`draw` only), `td/solvers/state_splits.py`
(`realise` only), `tools/run_draw.py`, `tools/state_splits.py`, `tools/borders_report.py`,
`tools/state_borders.py` (one call site), `tools/us_maps.py` (the `--table` path only),
`tools/measure/{frontier,premium}.py` (`read_draw` only), `app/headline.py` (`diff` only),
`tests/test_ziptable.py`, `tests/test_borders_report.py`, one row of `docs/CODE_MAP.md`.

Forbidden: every other file under `docs/`, the hub checkout outside `battery/results/`,
`battery/figures/`, `figures/`.
