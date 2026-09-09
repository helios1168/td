# Track: cell-split

## Goal

Rep territories from a within-district split are contiguous on the Voronoi cell graph, and the
rep maps fill zip cells by rep colour instead of drawing dots. On the way, a scoped staffing
never hands an in-scope district to a rep the table already places outside the scope. Second,
later piece on the same branch: one sidebar instance (member) picker drives Map and Reps
instead of each tab's own flat run picker, and the Reps tab collapses to one named-view pane
instead of three map panes and two before/after tables.

## Next step

On-screen check of the branch app (tmux `tdapp-cell`, `100.69.120.67:8503`), the live checks
`~/.claude/plans/lets-simplify-certain-aspect-cached-origami.md` §5.3 calls for:

- A district set to 1 rep in the new staffing form: identical result to the old plain Staff.
- A district set to 3+ reps: roster resolved, Nash split runs, "contiguous: true" on that
  district's Contest detail.
- Two districts whose candidate pools overlap: confirm the second-processed district's roster
  actually skips the rep the first one claimed.
- A district requesting more reps than it has positive-gain candidates: confirm the shortfall
  caption on Contest detail, not a block on Staff.
- Map tab: a run with `geom.json` shows opportunity-hue filled cells with a visible light
  border and a legend of up to 8 opportunity ranges; a run without `geom.json` (or an old one
  with no cells) falls back cleanly to the unchanged dot board.

Then merge on request.

## Done

- 2026-09-09: plan approved (`~/.claude/plans/ok-lets-pick-up-spicy-starfish.md`), worktree
  created and locked, `docs/APP.md` updated for cells, split.json fields, the new trace lists
  and the scope rule.
- 2026-09-09: all seven parts implemented. Suite 489 passed, 0 failed under `.venv`; the 8
  mapfig tests and the AppTest smoke pass under `.venv-app` (run directly: the runner imports
  `tests/test_atom_draw.py`, which needs networkx, before filtering, so the documented `-k`
  invocation fails under the app venv; pre-existing).
- 2026-09-09: real instance, round3 k10 staff run: geom.json rebuilt with 3,704 cells in 1.2 s
  (885 KB); D05 split over R0015 and R0002 in 0.2 s, one piece each, objective 10.171006
  against 10.174261 unguarded, where the unguarded greedy left R0015 in 5 pieces and R0002 in
  11. Both round3 k10 geom.json files (clip and staff) rebuilt in place in the hub.
- 2026-09-09: instance picker + one-pane Reps tab (plan
  `~/.claude/plans/lets-simplify-certain-aspect-cached-origami.md`), commits `c748b08`
  (`store.py` view.json sidecar, `staffing_run`, `members`/`member_label`), `bcb3f00`
  (`common.py` instance picker/`resolve_instance`; `main.py`, `tab_map.py`, `tab_reps.py`,
  `tab_overrides.py` wired to it; Reps collapsed to one View dropdown, one pane, one
  after/change table, Staff/Split now preview immediately with a name+default Save form),
  `2ef0a19` (`docs/APP.md`: `view.json` in the frozen-contracts list, the stale
  map_runs/pick_map sentence, §6's Reps recipe rewritten). One bug caught in review and fixed
  before commit: `render_contest` was threading `staffing_run` into `render_split` instead of
  `view_run`, which would have pinned every split to the original staff table instead of
  whichever view was open. 489 passed, 0 failed under `.venv`; a headless `AppTest` run against
  the real round3/k10 data hit no exception (sidebar, Map's Advanced expander, Reps' View
  dropdown all render). `app/staffdiff.py`'s `summary`/`district_view` are now unreferenced by
  the app (only caller was the deleted before/after panes) but still carry dedicated tests and
  were outside this change's file list, so left in place rather than pruned.
- 2026-09-09: `tdapp-cell` found crashing on every real page load on a stale `app.common`
  module (no `watchdog` installed, the poller-based file watcher missed the reload even though
  the file on disk was already correct). Restarting it took the whole tmux session down too,
  since that pane ran the streamlit command directly with no persistent shell under it, so
  Ctrl-C killed the pane. Recreated `tdapp-cell` with a real shell this time and relaunched;
  clean startup, `HTTP 200`, no traceback.
- 2026-09-09: cell-fill opportunity maps plus one merged staffing/split interface (plan
  `~/.claude/plans/lets-simplify-certain-aspect-cached-origami.md`), wave 1 (backend, this
  session's own uncommitted work: `app/mapfig.py`'s `figure()` rewritten onto opportunity-hue
  cell fills with a district-outline-only underlay and a legend of up to 8 bins, dot fallback
  unchanged; `tools/staff_and_split.py` new, one `channel.gain_matrix` call over N=1 and N>1
  districts alike, `resolve_rosters()` claiming a multi-rep roster's reps before the Hungarian
  match runs, `tools/split_district.py::build_adjacency` extracted for both call sites) plus
  wave 2 (frontend, this pass): `app/tab_reps.py`'s `render_keep_release`+`render_scope` merged
  into `render_staffing_form` (released reps, theta/lam/filler plus new global `staff-exact`/
  `staff-limit`, scope radio, one `st.data_editor` of district/today/reps replacing the old
  district-picker-then-Split flow), `render_contest` renamed `render_contest_detail` and its
  split action deleted (now read-only: contest table, a multi-rep district's `split_districts`
  detail, a `requested_multi` shortfall caption with any recorded error), `render_split` and
  its five session keys deleted, `render_assignment`'s "Districts staffed" metric and table
  extended to cover split districts. `docs/APP.md` and this file's Owned/Forbidden and `## Done`
  updated to match. Real `staffing.json` deltas from the plan's own spec text, read off
  `tools/staff_and_split.py`/`tests/test_staff_and_split.py` directly: `requested_multi[d]` can
  carry an `"error"` string when that district's split raised (it then falls through to
  `unstaffed_districts`, its would-be roster freed); a roster is capped at the district's own
  zip count, one more reason `resolved_n` can read below `requested_n`; a `--multi` run whose
  geom has no `"cells"` is a hard `failure.json`, not a silent unguarded solve. 522 passed, 0
  failed under `.venv`.

## Decisions needed

- Hover on cell vertices with `hoverdistance` 40 px: confirm on screen, raise if cells show a
  dead centre at district zoom.
- `tests/run_all.py` under `.venv-app`: filter by file name before importing, or guard the
  networkx import in `tests/test_atom_draw.py`. Outside this track's files.

## Files owned / forbidden

Owned: `td/solvers/district_split.py`, `tools/split_district.py`, `tools/geom_export.py`,
`tools/staff.py`, `tools/staff_and_split.py`, `app/mapfig.py`, `app/tab_map.py`,
`app/tab_reps.py`, `app/steps.py`, `app/store.py`, `app/common.py`, `app/main.py`,
`app/tab_overrides.py`, `docs/APP.md`, their tests.
Forbidden: `tools/rep_export.py`, `docs/foundations/`, `battery/figures/`.
