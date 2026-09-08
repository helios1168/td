# Track: app (worktree-app)

## Goal

Rebuild the Streamlit scenario app from scratch for three uses: a grid of state-clipped maps
over k at delta = 10 %, contestability and n-way Nash staffing of a chosen map (matching, and a
within-district split among kept reps, released reps' books treated as free), and overrides on
a map (Mode A relabel with no rerun; Mode B rerun with the moved unit locked, optionally plus a
hold set). Fully interactive plotly map. Approved plan: `~/.claude/plans/for-1-both-for-snazzy-kazoo.md`
(2026-09-08). Three invariants: CONUS plus DC only; the zip table is the input and output of
every step; the delivered map is the clipped one.

## Next step

The user is reviewing the app locally (`tools/app.sh --server.port 8503` from this worktree,
`http://127.0.0.1:8503`) against the runs under `battery/results/app/`; the track stays on this
branch until they ask for the merge (2026-09-08). The stage-2 weight alignment below wants one
look in the browser that no test covers: a clip's Map tab must show the value with the weights
under it, and a split launched from the Reps tab must inherit its staffing run's theta. Runs
made before 2026-09-08 carry none of the new keys and must render exactly as they did. At merge:
fast-forward into `main`, run
`/state` there, delete `PLAN.md` in the last commit, unlock and remove the worktree, delete the
branch.

## Done

- 2026-09-08 wave 0: `ziptable` optional `rep` column; `geo.assert_conus`; `state_splits.py`
  asserts CONUS and drops the AK/HI placement path; plotly 7.0.0 in `.venv-app`; old app
  modules removed, `runner.py` pruned to `_alive`, `cancel`, `log_tail`. Suite green.
- 2026-09-08 wave 1 (`9bec484`): geom export, staff with `release_reps`, override Mode A,
  `run_draw --lock-zips`, `state_splits --bounds`, district split engine, store/steps/runner,
  Map and Scenarios tabs. Wave 2 (`2f7d2d6`): override Mode B, Reps/Overrides/Compare tabs;
  docs (`e2671e0`). 408 tests, 0 fail.
- 2026-09-08 end to end on the CONUS instance: k grid 10..20 at delta 10 %, six chains in
  parallel, all six clipped with polygons (k 10-14 closed, k 16-20 at the 600 s limit with gap
  under 2 %); override A and B (i) on VT against the k = 18 clip (B closed the MILP, 7 splits,
  edit honoured); staff with everyone (18/18) and with ten released (18/18); exact split of D05
  among three candidates (SCIP optimal in 0.2 s). App healthz 200.
- 2026-09-08 (`4c8d530`): run directories are `<kind>_k<kk>_<YYYYmmdd_HHMMSS>` and every
  picker shows `store.label` (`k18 · clip · 2026-09-08 14:42:39`) built from the ledger; the
  free-text grid name is gone. 409 tests, 0 fail. The user reviewed the app locally and
  called it good.
- 2026-09-08: the stage-2 weights are one set per chain. `borders_report.cell_row` takes
  `theta`, `lam` and `filler_capture` as keyword-only parameters defaulting to its own
  constants, and its row echoes them as `stage2_theta`, `stage2_lam` and `stage2_filler`;
  `tools/state_splits.py` exposes the three flags and records the value and the weights in
  `d<delta>/splits.json`; the app passes them to the clip, and a split takes them from the
  staffing run it descends from; the Map tab shows the value with the weights beneath it. The
  app default stays `filler_capture="full"`. Driver defaults did not move: a no-flag clip of
  the k = 10 draw reproduces `stage2_value = 58.79368001770277` exactly, and the same clip under
  `--filler-capture full` gives 58.81832626294138 with identical geometry (`spread_rel`,
  `zips_changed`, `splits` unchanged), which is the point: the weights score reps, not maps.
  417 tests, 0 fail.

## Decisions needed

- Removing the abandoned `app-review` and `motion` worktrees needs `git worktree remove --force`
  (untracked files inside); left for the user.
- Level 2 overshoots the 10 % band after rounding at k = 16 to 20 (10.4 %, 10.0 %, 11.5 %), the
  open question already in `STATE.md`; the app shows the realised number, not the band.
- Under `filler_capture=full` the Nash value rises when reps are released, so `value` is not
  comparable across released sets; the Reps tab shows it per run only.

## Files owned / forbidden

Owned: `app/`, `tools/geom_export.py`, `tools/staff.py`, `tools/override.py`,
`tools/split_district.py`, `td/solvers/district_split.py`, `td/ziptable.py`,
`td/geo.py` (`assert_conus` only), `td/model.py` (`release_reps` only),
`tools/run_draw.py` (`--lock-zips` only), `tools/state_splits.py` (`--edits`, CONUS assert),
`td/solvers/state_splits.py` (`bound_z` only), `docs/APP.md`, `docs/CODE_MAP.md` (recipes),
new tests under `tests/`.
Forbidden: `docs/foundations/`, `figures/`, `STATE.md`, every other `docs/*.md`, solver pins.
