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

Wave 1: eight subagents in parallel on disjoint files (store/steps/runner, geom export, staff,
override Mode A, `run_draw --lock-zips`, `state_splits --edits`, district split engine, Map and
Scenarios tabs). Then wave 2 (override Mode B, remaining tabs, docs), then the end-to-end grid.

## Done

- 2026-09-08 wave 0: `ziptable` optional `rep` column; `geo.assert_conus`; `state_splits.py`
  asserts CONUS and drops the AK/HI placement path; plotly 7.0.0 in `.venv-app`; old app
  modules removed, `runner.py` pruned to `_alive`, `cancel`, `log_tail`. Suite green.

## Decisions needed

- Removing the abandoned `app-review` and `motion` worktrees needs `git worktree remove --force`
  (untracked files inside); left for the user.

## Files owned / forbidden

Owned: `app/`, `tools/geom_export.py`, `tools/staff.py`, `tools/override.py`,
`tools/split_district.py`, `td/solvers/district_split.py`, `td/ziptable.py`,
`td/geo.py` (`assert_conus` only), `td/model.py` (`release_reps` only),
`tools/run_draw.py` (`--lock-zips` only), `tools/state_splits.py` (`--edits`, CONUS assert),
`td/solvers/state_splits.py` (`bound_z` only), `docs/APP.md`, `docs/CODE_MAP.md` (recipes),
new tests under `tests/`.
Forbidden: `docs/foundations/`, `figures/`, `STATE.md`, every other `docs/*.md`, solver pins.
