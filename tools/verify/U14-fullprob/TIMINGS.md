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
