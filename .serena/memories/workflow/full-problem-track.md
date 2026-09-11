# Where the full-problem track's work lives

Track `full-problem`: worktree `.claude/worktrees/full-problem`, branch `worktree-full-problem`,
locked, unmerged by decision, pushed by the user. Its checkpoint is its own `PLAN.md`
(`## Next step`, `## Done`); `STATE.md` is the hub's. Suite at `3e9d002`: 801 pass.

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

Next work on the track: the v4 file, then `tools/instance_conus.py`, then re-run the ranked
cells on the v4 CONUS file (runbook: `docs/FULL_PROBLEM.md` §2 "When v4 lands").

Decisions: `mem:decisions/full-problem-2026-09-11`.

Source: host memory td-full-problem-overnight-2026-09-10; `worktree-full-problem:PLAN.md`
`## Next step` (2026-09-11 night).
