## Goal

Re-run the state-border pipeline (tools/state_splits.py, track 2, anchored homes) on the CONUS
ground set at balance band delta = 0.05, using the committed CONUS stage-1 draw, and record the
result.

## Next step

None. The run, the per-zip table, the legend check and the commit are done. Report delivered to
the orchestrator.

## Done

Run directory: battery/results/borders_k18_v2conus_20260907/track2_anchored/d0.05 (per-delta
output nested at .../d0.05/d0.05/).

Command:
.venv/bin/python3 -u tools/state_splits.py instance_descaled_v2_conus.json.gz --draw
battery/results/draw_k18_v2conus_20260907/k18/draw.csv --geo-cache data/geo --delta 0.05
--anchor-homes --time-limit 600 --rounds 5 --eta 0.01 --out
battery/results/borders_k18_v2conus_20260907/track2_anchored/d0.05 --maps

Wall time: 187 seconds (20:25:05 to 20:28:12 CDT). Internal solver + balance pass: 182.3s solve,
185.6s total before map rendering.

Level 1 MILP: status = 0 (optimal), mip_gap = 0.0, milp_spread_rel = 0.10000, objective =
57.00487390120471, splits = 8, split states = CA, FL, NY, TX. CA is split across D03, D09, D14,
D15, D16; FL across D08, D18; NY across D01, D05, D10; TX across D12, D13.

Balance pass (level 1, fractional, 4 of 5 rounds used): spread_rel = 0.09297, max_dev_rel =
0.04680, within the 5% band.

Level 2 zip realization (final, integer zips): spread = (max g - min g)/tau = 0.12020, max
deviation = 0.06258, so four districts fall outside the nominal 5% band after zip-level
rounding: D09 (-6.26%), D12 (+5.18%), D14 (-5.97%), D15 (+5.76%). n_states_split (additional
splits introduced beyond the level-1 plan) = 0. zips_changed = 779. outside_owner_share = 0.0679
(6.79% of M sits in a district outside its home state); n_districts_outside_home_1pct = 11.
stage2_value = 95.65375486407322, n_unmatched_reps = 95 (of 113).

Nash: sum log g = 110.781029, ceiling 18*log(tau) = 110.795534, gap = 0.014504.

Per-zip / per-district check (tools/verify script run inline, not committed): draw zip set
equals the instance zip set (3,713), no zip has a blank state or state AK/HI. Total M =
8481.810335, tau = 471.211685.

18-row per-district table (district, zips, opportunity, share of M %, g/tau, deviation %):

D01, 258, 449.9342, 5.30, 0.955, -4.52
D02, 207, 450.2504, 5.31, 0.956, -4.45
D03, 198, 485.4109, 5.72, 1.030, 3.01
D04, 261, 481.4519, 5.68, 1.022, 2.17
D05, 241, 490.4439, 5.78, 1.041, 4.08
D06, 305, 471.2380, 5.56, 1.000, 0.01
D07, 182, 490.8311, 5.79, 1.042, 4.16
D08, 229, 459.1116, 5.41, 0.974, -2.57
D09, 113, 441.7225, 5.21, 0.937, -6.26
D10, 127, 486.9303, 5.74, 1.033, 3.34
D11, 249, 455.9586, 5.38, 0.968, -3.24
D12, 204, 495.6089, 5.84, 1.052, 5.18
D13, 132, 491.9833, 5.80, 1.044, 4.41
D14, 84, 443.0968, 5.22, 0.940, -5.97
D15, 283, 498.3639, 5.88, 1.058, 5.76
D16, 165, 451.8943, 5.33, 0.959, -4.10
D17, 226, 472.3782, 5.57, 1.002, 0.25
D18, 249, 465.2014, 5.48, 0.987, -1.28

Legend check: district_regions_voronoi.png "share of M" column matches share_of_M_pct above to
two decimals for all 18 districts.

Home-state composition check (flagged, not requested by the recipe but worth recording): D11's
home state MO provides only 17.6% of D11's opportunity (top state is actually IN at 22.0%, then
LA at 20.4%, MO third at 17.6%). D02's home state CO provides 35.5% of D02's opportunity, with
AZ the plurality state at 57.1%. Every other district's home state is at or above 42.5% of its
own mass (D15 lowest among the rest, 42.5%).

Figures copied into the tracked figures/ directory:
figures/borders_conus_track2_anchored_d05_districts.png
figures/borders_conus_track2_anchored_d05_voronoi.png

## Decisions needed

None raised by this run. D11 and D02's home-state shares are a fact about the anchored solve at
delta = 0.05 on CONUS; whether that is acceptable is for the owner of the borders track to judge.

## Files owned / forbidden

Owned: figures/borders_conus_track2_anchored_d05_districts.png,
figures/borders_conus_track2_anchored_d05_voronoi.png, PLAN.md.
Forbidden: docs/, source code, anything outside this worktree and the hub's gitignored
battery/results directory. No merge, no push.
