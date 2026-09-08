## Goal

Re-run the state-border Track 2 anchored pipeline on the CONUS ground set (lower 48 plus DC,
3,713 zips, k = 18) at balance band delta = 0.07, using the already-committed stage-1 draw
(seed 3, spread 1.585%). Produce the per-delta cell, the per-zip and per-district tables, the
two figures, and commit them on this worktree branch.

## Next step

None. The delta = 0.07 cell is complete and committed. If a further band is requested, run the
same command with a different --delta and a fresh --out path; do not overwrite this cell.

## Done

Command:

    .venv/bin/python3 -u tools/state_splits.py instance_descaled_v2_conus.json.gz \
      --draw battery/results/draw_k18_v2conus_20260907/k18/draw.csv --geo-cache data/geo \
      --delta 0.07 --anchor-homes --time-limit 600 --rounds 5 --eta 0.01 \
      --out battery/results/borders_k18_v2conus_20260907/track2_anchored/d0.07 --maps

Run directory: battery/results/borders_k18_v2conus_20260907/track2_anchored/d0.07/d0.07/
Wall time: 2026-09-08T01:26:06Z to 2026-09-08T01:28:52Z, about 2 min 46 s (166 s; the run's own
timers report 162.2 s solve, 165.4 s cell total).

Level 1 (state-level minimum-splits MILP): status 0 (optimal), mip_gap 0.0 (closed, not
time-limited). 8 splits across 4 states: CA, FL, NY, TX. All four already span multiple
districts in the committed baseline, so the border-metric n_states_split (which counts only
newly-created splits) reads 0 with no new states named; this is not a discrepancy, it is the
metric's definition (docs: a split in an already-multi-owner state is not a border artifact).

Balance pass (fixes z, tightens y): spread_rel 0.12233, max_dev_rel 0.06967 (within the 7% band
on the continuous state-share solution).

Level 2 realization (rounds_used 3, n_fractional 8) then completion to the full 3,713-zip
instance moves the final zip-level numbers slightly past the balance pass: spread 0.128703
(12.87%), max deviation 0.070751 (7.0751%, district D09). D09 sits 0.0751 percentage points
outside the nominal 7% band after rounding zips to integer labels; every other district is
inside the band. This is a realization/rounding effect, not a level-1 or balance-pass failure.

Nash: sum of log g = 110.773301, ceiling 18*log(tau) = 110.795534, gap = 0.022232 nats.
Stage 2 value: 95.6469, unmatched reps: 95 (of 113).

zips_changed vs the committed map: 798. outside_owner_share: 0.0675.

Legend check: district_regions_voronoi.png's "share of M" column matches
district_summary.csv's share_of_M_pct for all 18 districts to two decimals. No mismatch.

Note: D11's plurality state (IN, 22.0%) and its committed home state (MO, 17.6%) both hold
under a quarter of the district's own mass; the rest is spread over LA, KY, AL, TN, AR, MS.
This is a genuinely multi-state rural district at k = 18, not an error, but it is the one
district in this cell with no state holding a clear plurality above 25%.

Per-district table (district, zips, opportunity, share of M %, g/tau, deviation %):

| district | zips | opportunity | share_% | g/tau | dev_% |
|---|---|---|---|---|---|
| D01 | 254 | 439.4439 | 5.18 | 0.933 | -6.74 |
| D02 | 205 | 439.4924 | 5.18 | 0.933 | -6.73 |
| D03 | 200 | 493.9030 | 5.82 | 1.048 | 4.82 |
| D04 | 270 | 495.2348 | 5.84 | 1.051 | 5.10 |
| D05 | 242 | 498.2498 | 5.87 | 1.057 | 5.74 |
| D06 | 305 | 471.2380 | 5.56 | 1.000 | 0.01 |
| D07 | 182 | 490.8311 | 5.79 | 1.042 | 4.16 |
| D08 | 226 | 443.9038 | 5.23 | 0.942 | -5.80 |
| D09 | 109 | 437.8730 | 5.16 | 0.929 | -7.08 |
| D10 | 130 | 489.6147 | 5.77 | 1.039 | 3.91 |
| D11 | 249 | 455.9586 | 5.38 | 0.968 | -3.24 |
| D12 | 209 | 498.5195 | 5.88 | 1.058 | 5.80 |
| D13 | 127 | 489.0727 | 5.77 | 1.038 | 3.79 |
| D14 | 87 | 448.8700 | 5.29 | 0.953 | -4.74 |
| D15 | 276 | 495.3390 | 5.84 | 1.051 | 5.12 |
| D16 | 164 | 441.4784 | 5.21 | 0.937 | -6.31 |
| D17 | 226 | 472.3782 | 5.57 | 1.002 | 0.25 |
| D18 | 252 | 480.4093 | 5.66 | 1.020 | 1.95 |

Total M 8,481.81, tau 471.211685.

Sources: battery/results/borders_k18_v2conus_20260907/track2_anchored/d0.07/{grid.csv,grid.md,
params.json,d0.07/splits.json,d0.07/zip_districts.csv,d0.07/district_summary.csv}.

## Decisions needed

None raised by this run. D09's small band overshoot after rounding and D11's diffuse state
composition are recorded above for whoever reviews this cell next; neither blocked the run.

## Files owned / forbidden

Owned: figures/borders_conus_track2_anchored_d07_districts.png,
figures/borders_conus_track2_anchored_d07_voronoi.png, this PLAN.md.
Forbidden: anything under docs/, any source file under td/ or tools/. This track did not touch
either.
