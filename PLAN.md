# Track: cell-split

## Goal

Rep territories from a within-district split are contiguous on the Voronoi cell graph, and the
rep maps fill zip cells by rep colour instead of drawing dots. On the way, a scoped staffing
never hands an in-scope district to a rep the table already places outside the scope.

## Next step

On-screen check of the branch app (tmux `tdapp-cell`, `100.69.120.67:8503`, round3 k10 map on
the Reps tab): cell fills in both colour modes, hover on cell vertices, the district and global
before/after pairs, a D05 split showing the pieces column. Then merge on request.

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

## Decisions needed

- Hover on cell vertices with `hoverdistance` 40 px: confirm on screen, raise if cells show a
  dead centre at district zoom.
- `tests/run_all.py` under `.venv-app`: filter by file name before importing, or guard the
  networkx import in `tests/test_atom_draw.py`. Outside this track's files.

## Files owned / forbidden

Owned: `td/solvers/district_split.py`, `tools/split_district.py`, `tools/geom_export.py`,
`tools/staff.py`, `app/mapfig.py`, `app/tab_map.py`, `app/tab_reps.py`, `app/steps.py`,
`docs/APP.md`, their tests.
Forbidden: `tools/rep_export.py`, `app/mapfig.figure` (the district map keeps its markers),
`docs/foundations/`, `battery/figures/`.
