# Stage-1 route and map decisions (2026-09-06 to 2026-09-07)

- **The state-atom route was adopted on 2026-09-06 (morning) and abandoned the same evening.**
  Its 30.5% spread at k = 18 against the power-cell route's 1.3% was the reason. The engine stays
  in the package, retired (`mem:facts/state-atoms-retired`).
- **2026-09-06 evening: the power-cell route is the deliverable, and the committed k = 18 map's
  borders move onto state lines**, sacrificing balance up to a 10% spread cap, because borders
  on state lines buy sponsor confidence. Visual map contiguity is sufficient; exact graph
  contiguity is not required. Warm start from seed 2 only; a district's home state is the
  plurality of its mass. Build plan: `docs/units/state_borders.md` (penalised, banded
  transportation LP; owner sets per state). Results: `mem:facts/state-border-snapping`.
- **2026-09-07: the modeled ground set is the lower 48 plus DC.** The 32 blank-state, 2 AK and
  1 HI zips never get placed at completion again: the shipped whole-instance map had sent them to
  the lightest districts, and without them it re-measures at 6.26% max deviation, not 5.25%
  (`docs/PROBLEM.md` §6, `docs/HEADLINE.md` §0).
- **2026-09-07 evening: the pipeline's core unit is the zip table**, one row per zip
  (`zip,state,x,y,opportunity,district[,rep]`), written by every step that changes a label; every
  figure is rendered from a table with per-state clipping always on (`td/ziptable.py`). Cause:
  the driver's `--maps` rendered unclipped Voronoi catchments, and the CONUS re-runs were
  published looking unsnapped although their labels were snapped. Lessons: look at every figure
  before publishing it; draw a figure from the dataset the claim is about, never re-join three
  sources at render time (`mem:model/corrections`).
- Level 1 is a minimum-splits MILP over 49 states (`td/solvers/state_splits.py`), level 2
  realises whole zips (`realise`), stage 2 is one Hungarian (`channel.match`).

Source: host memory td-contiguity-programme (2026-09-10).
