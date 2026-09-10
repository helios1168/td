# Track: cell-split

## Goal

Rep territories from a within-district split are contiguous on the Voronoi cell graph, and the
rep maps fill zip cells by rep colour instead of drawing dots. On the way, a scoped staffing
never hands an in-scope district to a rep the table already places outside the scope. Second,
later piece on the same branch: one sidebar instance (member) picker drives Map and Reps
instead of each tab's own flat run picker, and the Reps tab collapses to one named-view pane
instead of three map panes and two before/after tables. Third piece, added 2026-09-09: the Map
board encodes opportunity at the zip rather than the dot, the Reps tab has one staffing form
instead of separate staffing and split areas, and the zip shapes on every map are real census
ZCTA polygons instead of a Voronoi tessellation of zip centroids.

## Next step

On-screen check of the branch app, now serving real ZCTA geometry (`4428ef1`; the 15 runs
under `battery/results/app/` that carry polygons were rebuilt in place, 0.14/0.91 MB to
3.68 MB each, `cells_source` = `tl_2025_us_zcta520.shp simplify=250m`). Check the zip shapes
against a real US ZIP map, that district gaps read as gaps rather than as missing data, and
whether the 3.68 MB payload drags the browser. Then merge on request.

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
  carry an `"error"` string when that district's split raised; a roster is capped at the
  district's own zip count, one more reason `resolved_n` can read below `requested_n`; a
  `--multi` run whose geom has no `"cells"` is a hard `failure.json`, not a silent unguarded
  solve. Committed as `7fd78e0`. 522 passed, 0 failed under `.venv`; the AppTest smoke and the
  19 mapfig tests verified under `.venv-app`, with streamlit and plotly 7.0.0 genuinely loaded.
  Implemented by Sonnet subagents, each reviewed by an Opus agent reading the real files; the
  reviews found 13 behaviour defects, all fixed before the commit. Three worth carrying: a
  stale `st.data_editor` re-applies its `edited_rows` by ROW POSITION to whatever frame is
  passed next, with no identity or bounds check, so a scope change replayed an edited rep count
  onto a district the user never touched (the widget key now folds in a hash of the resolved
  scope); a pre-cells `geom.json` reached `district_split.split(adjacency=None)` and silently
  produced a non-contiguous split (now a hard failure); and the split phase originally ran
  after the Hungarian match, so a raised split stranded its district unstaffed with its reps
  still excluded from that match. The split phase now runs BEFORE assign: a district whose
  split raises falls through and is staffed as an ordinary single-rep district, its roster reps
  free for anyone else, with the error recorded in `requested_multi`.
  `tests/test_app_smoke.py`'s sidebar assertion was a live regression from `bcb3f00` (the
  Instance picker makes two selectboxes, the test allowed at most one) and is fixed here.
- 2026-09-09, committed as `4428ef1` (`td/geo.py`, `tools/geom_export.py`, `app/mapfig.py`,
  `tests/test_geom_export.py`, `tests/test_mapfig.py`, `docs/APP.md`), 534 passed, 0 failed,
  app smoke green under `.venv-app`: the zip shapes on the maps were never real ZIP
  boundaries. `geom.json["cells"]` was a Voronoi tessellation of ZCTA centroid points from the
  2020 Gazetteer (`tools/us_maps.py:858`), clipped to the state outline, so every "zip" was a
  synthetic catchment tiling the whole state; real ZCTA polygons were never loaded for drawing.
  Replaced with `data/tiger/2025/tl_2025_us_zcta520.shp` at 250 m simplify: 100% coverage of
  the 3,704 placed zips, `geom.json` 0.91 MB to 3.59 MB, export 0.3 s to 13.9 s, and a new
  `cells_source` key so a stale geom is identifiable. `cell_edges` stays the Voronoi rook
  adjacency, byte-identical at 10,483 edges, so `td/solvers/district_split.py`'s contiguity
  guard and every existing split result are unchanged. Vintage caveat: ZCTAs are re-delineated
  only each decennial, so the 2025 TIGER release carries the same 33,791 ZCTA5 codes as the
  2020 one, but 865 of 2,000 sampled polygons have refined geometry. Opus review found 9
  defects, all fixed before the commit; the load-bearing one is that
  `tools/split_district.py:73` builds its contiguity graph as
  `{z for z in zips if z in geom["cells"]}`, an inference that held only while `cells` meant
  "has a Voronoi cell" — a zip whose Voronoi cell clips away to nothing on the coastline would
  now enter the graph as an isolated vertex and make the guard infeasible (latent: 0 such zips
  on this instance). That vertex set now ships explicitly as `cell_graph_zips`. A district's
  interior gaps ride in a separate `"holes"` key, strokes-only, because `staffed_figure` fills
  `rings` in two places and a hole folded into `rings` would render as a solid blob; all 10
  districts on the live run have holes, 605 in total. District colouring reads its adjacency
  off the Voronoi dissolve, which tiles, not the ZCTA dissolve, which does not (15 adjacent
  pairs against 7), so "neighbours never share a hue" still holds. `geo.ZCTA_SHP` resolves
  repo-relative, then `TD_ZCTA_SHP`, then the hub, so no machine path is baked into the source.

## Decisions needed

- Hover on cell vertices with `hoverdistance` 40 px: confirm on screen, raise if cells show a
  dead centre at district zoom. Now applies to the main Map board too, not just the rep maps,
  and real ZCTA cells share boundary vertices with their neighbours, so a click near a border
  can resolve to the neighbouring zip.
- Zip `x`/`y` vintage. The table's coordinates are the 2020 Gazetteer internal points exactly
  (max deviation 0.0 m, measured). A 2025 Gazetteer exists and agrees with the 2025 TIGER
  polygons to 0.1 m, while the 2020 Gazetteer disagrees with TIGER's own internal points for
  the same ~468 zips in both releases. Switching moves the live instance's zips by median 33 m,
  p95 2.4 km, max 72.6 km, 12.6% over 1 km; a nearest-centre proxy flips 1 zip of 3,704
  (0.03%), so the districting is very unlikely to move materially, but only a stage-1 re-run
  proves it. It buys coordinate/polygon consistency and fixes the 36 zips (1%) whose current
  point falls OUTSIDE its own 2025 ZCTA polygon (median 554 m out, worst 93001 Ventura at
  53 km, a coastal point sitting in the water). Cost: re-derives the instance and invalidates
  existing run artifacts. User asked for the numbers on 2026-09-09; not yet decided. Deliberately
  kept out of the map change.
- `geom.json` payload is now 3.59 MB per run and reloads on every rerun. Chosen deliberately
  (250 m from a measured 250 m/500 m/1 km menu); revisit if the browser drags.
- `tests/run_all.py` under `.venv-app`: filter by file name before importing, or guard the
  networkx import in `tests/test_atom_draw.py`. Outside this track's files.

## Files owned / forbidden

Owned: `td/solvers/district_split.py`, `td/geo.py`, `tools/split_district.py`,
`tools/geom_export.py`, `tools/staff.py`, `tools/staff_and_split.py`, `app/mapfig.py`,
`app/tab_map.py`,
`app/tab_reps.py`, `app/steps.py`, `app/store.py`, `app/common.py`, `app/main.py`,
`app/tab_overrides.py`, `docs/APP.md`, their tests.
Forbidden: `tools/rep_export.py`, `docs/foundations/`, `battery/figures/`.
