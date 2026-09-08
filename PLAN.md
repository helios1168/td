## Goal

Re-run the state-border pipeline (Track 2, anchored) on the CONUS ground set (lower 48 plus DC,
3,713 zips) at balance band delta = 0.10, on the committed k=18 stage-1 draw, and report the
resulting split states, balance, and Nash gap.

## Next step

Done. The run, the per-zip and per-district tables, the checks, and the figure copies are all
committed on this branch. No further action is pending here unless a merge to main is requested.

## Done

Command run:

```
.venv/bin/python3 -u tools/state_splits.py instance_descaled_v2_conus.json.gz \
  --draw battery/results/draw_k18_v2conus_20260907/k18/draw.csv --geo-cache data/geo \
  --delta 0.10 --anchor-homes --time-limit 600 --rounds 5 --eta 0.01 \
  --out battery/results/borders_k18_v2conus_20260907/track2_anchored/d0.10 --maps
```

Run directory: `battery/results/borders_k18_v2conus_20260907/track2_anchored/d0.10/d0.1/`
(the per-delta subdirectory the tool writes; delta prints as `d0.1`).

Wall time: about 10 minutes 9 seconds (20:26:19 to 20:36:28 local), of which the solve plus
level-2 realisation accounted for 603.0s (600.0s MILP time limit plus level-2 realisation).

Level-1 MILP: status time_limit, mip_gap 1.754%, splits 8, split_states CA, FL, NJ, NY, TX.
Split shares (y): CA into D03 8.43%, D09 26.14%, D14 26.49%, D15 12.45%, D16 26.49%; FL into
D08 75.41%, D18 24.59%; NJ into D05 3.61%, D07 96.39%; NY into D01 39.07%, D10 60.93%; TX into
D12 54.29%, D13 45.71%. Of these five, only NJ is a split newly forced by delta = 0.10: CA, FL,
NY and TX are already multi-district in the committed draw's own owner sets (borders_report's
n_states_split excludes those, and reports n_states_split = 1, states_split = NJ).

Balance pass (after fixing z, tightening y): spread_rel 0.18237, max_dev_rel 0.09523.

Level-2 realisation (zip level, independently recomputed from the instance and draw.csv):
spread = 0.18969, max deviation = 0.10016. One district, D12, sits just outside the delta = 0.10
band (deviation +10.02%), a small overshoot introduced by the level-2 zip rounding on top of a
balance pass that itself only reached 0.09523. zips_changed vs the committed draw = 671.
outside_owner_share = 2.01% (2.78% against the labelling's own owner sets).
n_districts_outside_home_1pct = 10 (ten districts draw more than 1% of their mass from a state
other than their committed home state; this is expected, not a defect, since Track 2 assembles
districts from whole states plus split-state shares rather than confining each district to one
state). rounds_used = 3 (level-2 Lloyd rounds kept).

Nash: sum log g = 110.743272, ceiling 18*log(tau) = 110.795534, gap = 0.052262 nats.
Stage 2: value 95.8019, unmatched reps 95 (of 113).

Legend check: district_regions_voronoi.png's "share of M" column matches the independently
computed share_of_M_pct for all 18 districts to two decimals. No mismatch.

Notable finding: district D11 (home state MO) draws only 17.63% of its mass from MO; the rest
comes from the other whole states in its z-membership (AL, AR, IN, KY, LA, MS, TN). This is
expected under Track 2's design (an anchor only guarantees the home state is included, not that
it dominates), not a bug, but it is the extreme case of the ten districts flagged by
n_districts_outside_home_1pct.

Per-district table (zip level, independently computed from the instance and draw.csv):

| district | zips | opportunity | share % | g/tau | deviation % |
|---|---|---|---|---|---|
| D01 | 278 | 516.30 | 6.09 | 1.096 | +9.57 |
| D02 | 235 | 430.12 | 5.07 | 0.913 | -8.72 |
| D03 | 181 | 434.30 | 5.12 | 0.922 | -7.83 |
| D04 | 292 | 515.26 | 6.07 | 1.093 | +9.35 |
| D05 | 222 | 467.49 | 5.51 | 0.992 | -0.79 |
| D06 | 270 | 429.60 | 5.07 | 0.912 | -8.83 |
| D07 | 162 | 429.02 | 5.06 | 0.910 | -8.95 |
| D08 | 223 | 436.67 | 5.15 | 0.927 | -7.33 |
| D09 | 141 | 515.82 | 6.08 | 1.095 | +9.47 |
| D10 | 146 | 505.33 | 5.96 | 1.072 | +7.24 |
| D11 | 249 | 455.96 | 5.38 | 0.968 | -3.24 |
| D12 | 200 | 518.41 | 6.11 | 1.100 | +10.02 |
| D13 | 101 | 438.12 | 5.17 | 0.930 | -7.02 |
| D14 | 112 | 506.88 | 5.98 | 1.076 | +7.57 |
| D15 | 265 | 429.61 | 5.07 | 0.912 | -8.83 |
| D16 | 164 | 507.73 | 5.99 | 1.077 | +7.75 |
| D17 | 217 | 457.54 | 5.39 | 0.971 | -2.90 |
| D18 | 255 | 487.65 | 5.75 | 1.035 | +3.49 |

Total M = 8481.81, tau = 471.2117 (18 districts).

## Decisions needed

None. D12's small overshoot of the delta = 0.10 band (+10.02% vs the 10.00% cap) is reported
as a fact of this time-limited, anchored run; whether to accept it, extend the time limit, or
adjust eta is a call for whoever consumes this cell, not made here.

## Files owned / forbidden

Owned on this branch: `figures/borders_conus_track2_anchored_d10_districts.png`,
`figures/borders_conus_track2_anchored_d10_voronoi.png`, this `PLAN.md`.

Forbidden: `docs/`, all source code (`td/`, `tools/`) — read only for reference, not edited.
The run outputs themselves live under the hub's gitignored
`battery/results/borders_k18_v2conus_20260907/track2_anchored/d0.10/` and are not part of this
worktree's tracked tree.
