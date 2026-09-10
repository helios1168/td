# U14-fullprob: level-0 timing table

One row per solve. All runs on the Mac Studio (Apple M2 Max, 12 cores, 32 GB), HiGHS 1.15.1,
one process per row, `mip_rel_gap = 0` where a pass is marked certified. "Splits" is contacts
minus 49 over the used slots. A cell is named by route, driver and instance; a driver named
`geo` with neither `--n-max` nor `--dist-max` imposes nothing and the run is a plain
lexicographic solve.

| date | instance | route | driver, caps | bundles | slots | vars / rows | strategy, threads | per-pass limit | passes (value, certified, s) | splits | wall | run dir |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-09-10 | synthetic v2 (national = v2 CONUS, WH and FI hashed multiples) | S, N stage only, band 1 ± 0.05, committed anchors and centres | geo, no caps | N | 19 (18 used) | 6.9k / 13k | portfolio, 2 | 600 s | cover_N 8481.81 certified 15 s; contacts 85 timed out 601 s; compactness 57.003 timed out 600 s | 8 (CA 5, NY 3, TX 2, FL 2), matches the committed map, uncertified | 20 min | `battery/results/full_problem/seq_regression` |
| 2026-09-10 | synthetic v2 | J | geo, n_max 6 | default six | 95 | 34,390 / 64,689 | portfolio, 2 | 600 s | hung in the contacts pass: parent in `poll`, no member alive, 0% CPU for 35 min, killed | none | none | `/Users/ntlee/.claude/jobs/610589f0/tmp/longpole/` (sample.txt) |
| 2026-09-10 | v3 CONUS (real, 6,459 zips) | J, no warm start, before `cover_merged` | geo, no caps | default six | 161 | about 54k / 101k | direct, 6 | 600 s | cover_N 8479.77 certified 575 s (17 slots); cover_WH 376.88 timed out (one slot at L); cover_FI 565.32 timed out (one slot at U); contacts 100 timed out, incumbent unchanged | 48 in N (97 contacts), 46 states national only, WH and FI residual in 47 states | 40 min | `battery/results/full_problem/v3_joint_geo` |
| 2026-09-10 | v3 CONUS | S, no warm start, before `cover_merged` | geo, no caps | N, then WH and WH⁺, then FI, FI⁺, WHFI | 23, 38, 73 per stage (46 used) | pending | direct, 4 | 600 s | seq_N: cover_N 5699.6 timed out (67% of national, 11 slots), contacts 14 certified 68 s; seq_WH: cover_WH 5802 timed out, contacts 85 timed out; seq_FI: cover_FI 10274 timed out, contacts 86 timed out | N 3, WH 10, WH⁺ 63, FI 6, FI⁺ 57; 33 states read WH⁺ + FI⁺ (national dropped) because the N stage's weak incumbent left their national mass to later stages | 50 min | `battery/results/full_problem/v3_seq_geo` |
| 2026-09-10 | v3 CONUS | S, warm greedy, anchors (18 homes + greedy seeds), k-fixed N 18 / WH 11 / FI 19, catch-all | geo, no caps | N; WH, WH⁺; FI, FI⁺, WHFI | 23, 38, 64 (51 used) | pending | direct, 2 | 300 s | seq_N: greedy 7537, cover_N 8479.77 certified 59 s, contacts 180 timed out, compactness 59.0 timed out; seq_WH: cover_WH 5324.63 certified 15 s, contacts 52 timed out; seq_FI: cover_FI 8936.68 certified 3 s, cover_merged 0, contacts 56 timed out; catch-all skipped (no residual) | N 10, WH 3, FI 7; 51 districts (N 20, WH 12, FI 19), every channel fully covered, all 49 states keep three channels, 51 staffed, 63 reps idle | 21 min | `battery/results/full_problem/v3_seq_warm` |
| 2026-09-10 | v3 CONUS | J, same warm, anchors and counts, catch-all | geo, no caps | default six | 161 (50 used) | about 54k / 101k | direct, 2 | 300 s | greedy N 7537 / WH 5005 / FI 8132; cover_N 8479.77 certified 17 s; cover_WH 5157 (97%) timed out; cover_FI 8635 (97%) timed out; cover_merged 0 timed out; contacts 2063 timed out, no improvement; compactness timed out | contacts 862 / 443 / 758 in N / WH / FI: the cover passes spread every state over many slots at tiny shares and the contacts pass could not undo it in 300 s; 50 districts, 43 states keep three channels, WH and FI residual in 5 states each | 25 min | `battery/results/full_problem/v3_joint_warm` |
| 2026-09-10 night | v3 CONUS | S, warm greedy, greedy anchors, seeds as centres, `--k-mode cap` N 16 / WH 11 / FI 20, per-bundle band 1 ± 0.10, `--other-first MT,WA,WY --other-floor 0.5`, catch-all all | geo, dist_max 900, n_max 6 | seven (N; WH, WH⁺; FI, FI⁺, WHFI, WHFI⁺) | 108 other-first (2 used), then per stage | pending | direct, 2 | 180 s | other_first: contacts 4, cover 541 certified 1 s; seq_N: cover_N 8040.22, contacts 48 certified; seq_WH: cover_WH 4868.57, contacts 36 certified; seq_FI: cover_FI 8487.81, cover_merged 391.96, contacts 53 certified 368 s at the 900 s rerun; compactness passes timed out | 48 districts (N 16, WH 10, FI 19, WHFI 1, WHFI⁺ 2), max extent 894 km, every state in a grouping, 48 staffed | 11 min (22 min at 900 s) | `battery/results/full_problem/grid_20260910_of/X_n16w11f20_d100_d900n6_of` and `grid_20260910_cert/` |
| 2026-09-10 night | v3 CONUS | as above with N 18 / WH 11 / FI 19 and the committed draw as centres | geo, dist_max 900, n_max 6 | seven | as above | pending | direct, 2 | 900 s | every pass certified: other_first 4 / 541; N 8159, 51 contacts; WH 4868.57, 36; FI 8205.78, merged 412.59, 47 | 49 districts (N 18, WH 10, FI 18, WHFI 1, WHFI⁺ 2), max extent 894 km | 2 min | `battery/results/full_problem/grid_20260910_cert/X_n18w11f19_d100_d900n6_of_cert` |

The overnight grid (`grid_20260910/`, 97 cells at 180 s per pass, 5 at once, threads 2): a
cross cell with seven bundles and a cap runs 7 to 12 minutes; a single-channel stage cell 30 s to
10 minutes; the 5% band without a cap is the one setting whose contacts pass does not converge
in 180 s (67 contacts left in N, 250 pieces after realisation). Under the cap, a fixed count
banded on its own mean is infeasible (HiGHS proves it in under a second), which is why the
counts are ceilings.

Route decision from these two rows: sequential. At the same budget it certifies full coverage of all
three channels in under two minutes and reaches 20 splits; the joint model leaves 3% of WH and
FI uncovered and a contacts count no pass can repair inside the limit. The joint model stays as
the reference for the lexicographic reading and for route R, whose moves need all bundles in one
model.

Reference: level 1 today on the v2 CONUS national instance at k = 18 certifies 8 splits in 49 s
under the portfolio (6,498 variables, 11,317 rows).

Observations so far:

- The level-0 form of the level-1 problem is slower: the same 8 splits appear inside the limit
  but are not proven. Suspects, in order: the cover pass pinned as a row instead of the cover
  rows being equalities; the unused nineteenth slot and the `u` ordering; the pin row itself
  in HiGHS presolve. A `--cover-force` that turns the cover rows into equalities for a
  national-only run would make the regression the level-1 model exactly.
- HiGHS branch and bound is serial: both v3 runs sit at 100% of one core with 6 and 4
  threads. The overnight grid should run 5 to 6 cells at once at `threads=2`, with the
  per-pass limit as a grid axis, and certify the chosen cell once afterwards.
- The portfolio strategy is not usable on a `Level0Problem` until the hang is fixed.
