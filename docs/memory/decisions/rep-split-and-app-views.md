# Rep splits, rep maps and the app's views (decided 2026-09-09)

**A within-district rep split is contiguous on the Voronoi cell graph.** Enforced in the greedy
engine only (contiguous seed, articulation-point move guard); both engines report
`pieces` / `contiguous` in `split.json`. Zip rook adjacency stays unused (shattered). Cells and
their rook edges live in `geom.json` as `proximity_edges` / `proximity_zips`
(`mem:geo/zip-adjacency`).

**Rep maps** fill zip cells by rep colour and carry no zip markers (user choice; hover sits on
cell vertices, `hoverdistance` 40 px, unconfirmed on screen). A scoped staffing never gives an
in-scope district to a rep the table already places outside the scope. Unavailable reps are
excluded from candidacy, never released (CLAUDE.md trap 20).

**App views** (four user calls via AskUserQuestion, not inferred):
- Per-round instances collapse to one sidebar "Instance" picker under "Scenario" (member = k +
  delta), driving Map and Reps in place of each tab's own run picker. Overrides narrows to it;
  Compare stays exempt on purpose (it diffs two arbitrary runs).
- Naming a Staff or Split result (`view.json`, beside `step.json`, at most one default per
  instance) makes it a `View` dropdown entry, with an opt-in "make default". An unnamed result
  only previews in the pane, with a name and save prompt, and drops on navigating away; the run
  directory is never deleted either way.
- The Reps tab is one named-view pane, replacing both old before/after map pairs; their two
  before/after tables collapse to one after/change table.
Branch `worktree-cell-split` (commits `c748b08`, `bcb3f00`, `2ef0a19` on `f176171`) carried
this; check `git branch --merged main` before assuming it is on `main`.

Related: `mem:decisions/app-2026-09-08`, `mem:geo/zcta-geometry`.

Source: host memory td-contiguity-programme (2026-09-09 entries).
