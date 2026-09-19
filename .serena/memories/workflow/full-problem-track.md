# Where the full-problem track's work lives

Track `full-problem`: worktree `.claude/worktrees/full-problem`, branch `worktree-full-problem`,
locked, unmerged by decision, pushed by the user. Its checkpoint is its own `PLAN.md`
(`## Next step`, `## Done`); `STATE.md` is the hub's. Suite at `9b74c3f`: 823 pass.

Results under the worktree's `battery/results/full_problem/` (gitignored):
- `grid_20260910/` (the first twelve cells) with `REVIEW.md`, one row per cell with a verdict
  and the ranking; `grid_20260910_of/` (`--other-first MT,WA,WY --other-floor 0.5`);
  `grid_20260911_splits*/` (split caps); `grid_20260911_lowk/` (national at 10 and 12);
  `grid_20260911_wifi/` (all channels merged, 50 and 53, no sweep);
  `grid_20260911_wifi_sweep/` (merged with the sweep; MT joins the adjacent WIFI district at 467
  against U 500); `grid_20260911_full/` (rank 1's and rank 2's counts with every rule of the
  day, unheld mass 0 on every channel, two or three western districts at 1.3 to 1.5 books: the
  candidates to replace rank 1).
- Each cell dir: `plan.json`, `assignment.csv`, `districts.csv`, `wholesalers.csv`,
  `maps/summary.png`.
- `hot/`: every live figure as a symlink named in plain English, with a README mapping names to
  run dirs; the user reviews from there.
- `best/`: the frozen rank 1 figure for the first stakeholder share (2026-09-11), inputs under
  `run/`, `PROVENANCE.md` (instance sha256, code tag `stakeholder-best-1` = `26142e0`) and
  `reproduce.sh`.

App scenarios live in the hub store `battery/results/app/`
(`x-n16w11f20-d10-cap900-allstates` first); the worktree's app runs on port 8503, the hub's on
8502.

Sibling worktree `.claude/worktrees/contig-cut` (branch `worktree-contig-cut`, off the track at
`d322951`, locked, work uncommitted): the contiguous split-state cut (ported to the track) and
the land-clipped graph variants (not adopted), results under its own
`battery/results/full_problem/contig_20260911/`.

v4 landed and re-ran on 2026-09-11. The sandvault clone (hub `/Users/Shared/sv-ntlee/repos/td`,
same track worktree path under it) has no `hot/`, `best/` or reference grids; its results are
the FI 21 run, `battery/results/full_problem/grid_20260911_fi21_{U2,C,S,S_retry1,S_retry2}` and
a `_newcut` twin of each (border-aware cut and DC-VA edge), cell files as `cells_input.json`,
numbers in `mem:facts/fi21-cover-grid`. In the sandbox set `TD_ZCTA_SHP` to the hub's
`data/tiger/2025/tl_2025_us_zcta520.shp`, and run grids from a `git archive` snapshot.

The national-only study (done 2026-09-11): grid `grid_20260911_fi21_P5` (pool = group + DE DC
SC CA; solved at `cca6be9`, sweep replayed with `8bf4a43`, old plan kept per cell as
`plan_presweepfix.json`), `_P_nocover`, `_P2`, `_P3`, `_P4` (superseded, kept as evidence);
figures and the answer tables in `battery/results/full_problem/fi21_national_only_summaries/`
(names: group, N allowed and used, wholesalers). Code snapshot `/Users/Shared/sv-ntlee/tmp/snap_ns`
(`cca6be9` with `tools/plan_realise.py` from `4fd87fc`). Scripts in `/Users/Shared/sv-ntlee/tmp/`:
`resweep.py RUN_DIR` (replay the level-0 sweep with the worktree's `_sweep`, rewrite plan,
projections, staffing), `p_fix.sh TAG` (resweep, rerealise, summary `--groups`, copy under the
review name), `probe_fi.py` (does a variant pass the FI stage), `probe_one.py`,
`national_only_report.py GRID` (per state: wholly / partly / not in N), `district_values.py`
($MM per district by channel).

Scenario datasets (2026-09-11): `tools/scenario_export.py --out CSV --scenario NAME RUN_DIR ...
[--rep-map PATH]` joins realised runs onto the source table's (zip_code, current_channel) rows
in the user's spellings (National (Chase), Wells WH, Wells FI, WH, FI); identifiers only, no
masses. `scenarios.csv` for G2 k 10 and G1 k 14 sits next to the figures. Raw rep ids need the
export run again on the work machine with `--rep-map rep_map.csv` (export_instance.py); the
map is confidential and stays off the clone. Commit `dbd7fbc`, bead `td-9ek.20.9`.

Dollar-target study (2026-09-11): worktree `.claude/worktrees/full-problem-usd`, branch
`worktree-full-problem-usd` from `worktree-full-problem` at `dbd7fbc`, locked; `6d72c6b` adds
`--band-target BUNDLE=MASS` (band = band_lo, band_hi times the target; count free). Grid
`grid_20260911_usd` (U1_usd G1 pool, U2_usd G2 pool), figures and README in
`battery/results/full_problem/usd_summaries/` of that worktree; snapshot
`/Users/Shared/sv-ntlee/tmp/snap_usd`, cells `/Users/Shared/sv-ntlee/tmp/cells_usd.json`, watcher
`p_usd.sh`. Kept apart from `worktree-full-problem` by the user's decision.

Next work on the track: the user's pick, WH_03's CT end (`td-9ek.20.6`) and the border-aware seed defect (`td-9ek.20.7`).

Decisions: `mem:decisions/full-problem-2026-09-11`.

Source: host memory td-full-problem-overnight-2026-09-10; `worktree-full-problem:PLAN.md`
`## Next step` (2026-09-11 night).
