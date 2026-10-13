# MORNING: main_overnight_2026-10-13

Built by `tools/exp/contig/overnight.py morning` from `GRID.json` at 2026-10-13T18:18:29+00:00.  Extract `instance_descaled_usd.json.gz` (sha256 `98cc87bc8ba5`); code `54f5afa`; stop at 2026-10-13T17:47:53+00:00.

38 points: 15 fails M1, 20 infeasible, 3 stopped.

## Assumptions (owner decisions open)

- #111, #112 (what gives way): open; no remedy arm beyond the stop/retry policy
- #119 (all-M1 bound): not used; no point is claimed minimal
- #133: R = 10 on in-state land, pieces of 20% of district mass or more, for this run only
- WIFI window $850-1,150M with the $1.6B whole-state allowance, national floor $1,000M: owner decisions (2026-10-12) still to be filed in PROBLEM.md
- M1 gated with necks across coverage gaps (scouts G1, TD_NECK_GAP_WIDTH=1); strict beside it
- -wide points (2026-10-13 05:00, the planner, owner asleep): a point whose master had no plan within the window-fitted final δ is drawn again as <id>-wide at the master's smallest feasible δ (rounded up to 1e-4); the per-district dollar gate and every window are unchanged, so it is eligible only when every district lands in its window. Not for nw49 (smallest δ 0.64 or more)

## Points

Eligible first by the scorer's rank key (splits, defects, extent, states per district, worst and mean deviation), then fails M1, ineligible ($), ineligible, infeasible, stopped and error; a balanced point beside its FI-light partner when both carry one label.  Worst $: the district farthest from its channel's mean $ per district.  M1: across coverage gaps (the gate) / strict.  Land: the largest in-state ratio, groups beyond R = 10.  `MORNING.pdf` has one page per point in this order.

| # | id | structure | K | splits | defects | worst $ | M1 gaps / strict | land | label | links |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | ne-50-bal-wide | ne_plains | national 15, WH 10, FI 22, WIFI 3 = 50 | 11 | 2 | FI_04 +13.5% (954.8M) | fail / fail | 32.1 (3 > R) | **fails M1** | [folder](ne-50-bal-wide/r2/) · [map](ne-50-bal-wide/r2/summary.png) · [score](ne-50-bal-wide/r2/score.txt) |
| 2 | w1-50-wide | w1 | WIFI 50 = 50 | 11 | 10.7492 | WIFI_01 -31.4% (670.9M) | fail / fail, 1 flips | 395.7 (4 > R) | **fails M1** | [folder](w1-50-wide/r2/) · [map](w1-50-wide/r2/summary.png) · [score](w1-50-wide/r2/score.txt) |
| 3 | ne-52-filight-wide | ne_plains | national 16, WH 11, FI 22, WIFI 3 = 52 | 12 | 1 | FI_04 +13.5% (954.8M) | fail / fail, 1 flips | 32.3 (3 > R) | **fails M1** | [folder](ne-52-filight-wide/r2/) · [map](ne-52-filight-wide/r2/summary.png) · [score](ne-52-filight-wide/r2/score.txt) |
| 4 | ne-48-bal | ne_plains | national 14, WH 10, FI 21, WIFI 3 = 48 | 12 | 2 | national_12 +16.8% (1,410.1M) | fail / fail | — | **fails M1** | [folder](ne-48-bal/r2/) · [map](ne-48-bal/r2/summary.png) · [score](ne-48-bal/r2/score.txt) |
| 5 | w1-48-wide | w1 | WIFI 48 = 48 | 12 | 9.7483 | WIFI_31 +30.3% (1,327.9M) | fail / fail, 1 flips | 123.4 (4 > R) | **fails M1** | [folder](w1-48-wide/r2/) · [map](w1-48-wide/r2/summary.png) · [score](w1-48-wide/r2/score.txt) |
| 6 | w1-52-wide | w1 | WIFI 52 = 52 | 13 | 8.7538 | WIFI_20 -28.8% (669.6M) | fail / fail | 405.7 (5 > R) | **fails M1** | [folder](w1-52-wide/r2/) · [map](w1-52-wide/r2/summary.png) · [score](w1-52-wide/r2/score.txt) |
| 7 | w8-cmp-seed-wide | west8 | national 13, WH 11, FI 24, WIFI 1 = 49 | 13 | 8.7594 | WH_04 -29.8% (686.7M) | fail / fail, 1 flips | 55.6 (2 > R) | **fails M1** | [folder](w8-cmp-seed-wide/r2/) · [map](w8-cmp-seed-wide/r2/summary.png) · [score](w8-cmp-seed-wide/r2/score.txt) |
| 8 | w8-50-bal-wide | west8 | national 15, WH 11, FI 23, WIFI 1 = 50 | 13 | 9.4477 | WH_04 -29.8% (686.7M) | fail / fail | 55.2 (4 > R) | **fails M1** | [folder](w8-50-bal-wide/r2/) · [map](w8-50-bal-wide/r2/summary.png) · [score](w8-50-bal-wide/r2/score.txt) |
| 9 | ne-52-bal-wide | ne_plains | national 15, WH 11, FI 23, WIFI 3 = 52 | 14 | 3 | FI_05 -12.0% (708.2M) | fail / fail | 33.4 (3 > R) | **fails M1** | [folder](ne-52-bal-wide/r2/) · [map](ne-52-bal-wide/r2/summary.png) · [score](ne-52-bal-wide/r2/score.txt) |
| 10 | w8-52-bal-wide | west8 | national 15, WH 12, FI 24, WIFI 1 = 52 | 15 | 4 | national_14 -24.4% (855.3M) | fail / fail | 55.5 (4 > R) | **fails M1** | [folder](w8-52-bal-wide/r2/) · [map](w8-52-bal-wide/r2/summary.png) · [score](w8-52-bal-wide/r2/score.txt) |
| 11 | nw34-50-wide | nw34 | national 15, WIFI 35 = 50 | 16 | 0 | national_10 -28.1% (809.4M) | fail / fail, 1 flips | 91.6 (4 > R) | **fails M1** | [folder](nw34-50-wide/r2/) · [map](nw34-50-wide/r2/summary.png) · [score](nw34-50-wide/r2/score.txt) |
| 12 | w8-52-filight-wide | west8 | national 16, WH 12, FI 23, WIFI 1 = 52 | 16 | 8.6796 | national_15 -31.5% (727.1M) | fail / fail, 1 flips | 54.2 (3 > R) | **fails M1** | [folder](w8-52-filight-wide/r2/) · [map](w8-52-filight-wide/r2/summary.png) · [score](w8-52-filight-wide/r2/score.txt) |
| 13 | nw34-48-wide | nw34 | national 14, WIFI 34 = 48 | 17 | 6.3197 | WIFI_21 -22.7% (727.6M) | fail / fail, 3 flips | 34.2 (2 > R) | **fails M1** | [folder](nw34-48-wide/r2/) · [map](nw34-48-wide/r2/summary.png) · [score](nw34-48-wide/r2/score.txt) |
| 14 | w8-48-bal-wide | west8 | national 14, WH 11, FI 22, WIFI 1 = 48 | 17 | 12.724 | WH_01 +22.4% (1,196.1M) | fail / fail, 2 flips | — | **fails M1** | [folder](w8-48-bal-wide/draw_retry/) · [map](w8-48-bal-wide/draw_retry/summary.png) · [score](w8-48-bal-wide/draw_retry/score.txt) |
| 15 | nw34-52-wide | nw34 | national 16, WIFI 36 = 52 | 19 | 8.2367 | WIFI_31 +27.2% (1,131.0M) | fail / fail | 52.2 (2 > R) | **fails M1** | [folder](nw34-52-wide/r2/) · [map](nw34-52-wide/r2/summary.png) · [score](nw34-52-wide/r2/score.txt) |
| 16 | ne-50-bal | ne_plains | national 15, WH 10, FI 22, WIFI 3 = 50 | — | — | — | — | — | **infeasible** | — |
| 17 | ne-50-filight | ne_plains | national 16, WH 11, FI 20, WIFI 3 = 50 | — | — | — | — | — | **infeasible** | — |
| 18 | ne-52-bal | ne_plains | national 15, WH 11, FI 23, WIFI 3 = 52 | — | — | — | — | — | **infeasible** | — |
| 19 | ne-52-filight | ne_plains | national 16, WH 11, FI 22, WIFI 3 = 52 | — | — | — | — | — | **infeasible** | — |
| 20 | ne-cmp-tierP | ne_plains | national 15, WH 11, FI 20, WIFI 3 = 49 | — | — | — | — | — | **infeasible** | — |
| 21 | nw34-48 | nw34 | national 14, WIFI 34 = 48 | — | — | — | — | — | **infeasible** | — |
| 22 | nw34-50 | nw34 | national 15, WIFI 35 = 50 | — | — | — | — | — | **infeasible** | — |
| 23 | nw34-52 | nw34 | national 16, WIFI 36 = 52 | — | — | — | — | — | **infeasible** | — |
| 24 | nw49-48 | nw49 | national 15, WIFI 33 = 48 | — | — | — | — | — | **infeasible** | — |
| 25 | nw49-50 | nw49 | national 16, WIFI 34 = 50 | — | — | — | — | — | **infeasible** | — |
| 26 | nw49-52 | nw49 | national 17, WIFI 35 = 52 | — | — | — | — | — | **infeasible** | — |
| 27 | w1-48 | w1 | WIFI 48 = 48 | — | — | — | — | — | **infeasible** | — |
| 28 | w1-50 | w1 | WIFI 50 = 50 | — | — | — | — | — | **infeasible** | — |
| 29 | w1-52 | w1 | WIFI 52 = 52 | — | — | — | — | — | **infeasible** | — |
| 30 | w8-48-bal | west8 | national 14, WH 11, FI 22, WIFI 1 = 48 | — | — | — | — | — | **infeasible** | — |
| 31 | w8-50-bal | west8 | national 15, WH 11, FI 23, WIFI 1 = 50 | — | — | — | — | — | **infeasible** | — |
| 32 | w8-50-filight | west8 | national 16, WH 12, FI 21, WIFI 1 = 50 | — | — | — | — | — | **infeasible** | — |
| 33 | w8-52-bal | west8 | national 15, WH 12, FI 24, WIFI 1 = 52 | — | — | — | — | — | **infeasible** | — |
| 34 | w8-52-filight | west8 | national 16, WH 12, FI 23, WIFI 1 = 52 | — | — | — | — | — | **infeasible** | — |
| 35 | w8-cmp-seed | west8 | national 13, WH 11, FI 24, WIFI 1 = 49 | — | — | — | — | — | **infeasible** | — |
| 36 | ne-50-filight-wide | ne_plains | national 16, WH 11, FI 20, WIFI 3 = 50 | — | — | — | — | — | **stopped** | — |
| 37 | ne-cmp-tierP-wide | ne_plains | national 15, WH 11, FI 20, WIFI 3 = 49 | — | — | — | — | — | **stopped** | — |
| 38 | w8-50-filight-wide | west8 | national 16, WH 12, FI 21, WIFI 1 = 50 | — | — | — | — | — | **stopped** | — |

## Reasons

- **ne-50-bal-wide** (fails M1): M1 across coverage gaps: fail, 0 districts in pieces, 0 detached pieces (largest 0 τ), 2 necks, 0 channel ZCTAs with no owner, 0 (ZCTA, fine channel) cells with no row, 0 owned twice, 8 mass necks listed beside M1
- **w1-50-wide** (fails M1): M1 across coverage gaps: fail, 2 districts in pieces, 2 detached pieces (largest 0.406 τ), 2 necks, 0 channel ZCTAs with no owner, 0 (ZCTA, fine channel) cells with no row, 0 owned twice, 15 mass necks listed beside M1
- **ne-52-filight-wide** (fails M1): M1 across coverage gaps: fail, 0 districts in pieces, 0 detached pieces (largest 0 τ), 1 necks, 0 channel ZCTAs with no owner, 0 (ZCTA, fine channel) cells with no row, 0 owned twice, 9 mass necks listed beside M1
- **ne-48-bal** (fails M1): M1 across coverage gaps: fail, 0 districts in pieces, 0 detached pieces (largest 0 τ), 1 necks, 0 channel ZCTAs with no owner, 0 (ZCTA, fine channel) cells with no row, 0 owned twice, 8 mass necks listed beside M1; relabelled from r2's completed score after the 8 h stop (was: stopped, the 8 h stop during score_r2)
- **w1-48-wide** (fails M1): M1 across coverage gaps: fail, 2 districts in pieces, 2 detached pieces (largest 0.414 τ), 2 necks, 0 channel ZCTAs with no owner, 0 (ZCTA, fine channel) cells with no row, 0 owned twice, 14 mass necks listed beside M1
- **w1-52-wide** (fails M1): M1 across coverage gaps: fail, 2 districts in pieces, 2 detached pieces (largest 0.423 τ), 4 necks, 0 channel ZCTAs with no owner, 0 (ZCTA, fine channel) cells with no row, 0 owned twice, 16 mass necks listed beside M1
- **w8-cmp-seed-wide** (fails M1): M1 across coverage gaps: fail, 2 districts in pieces, 2 detached pieces (largest 0.477 τ), 4 necks, 0 channel ZCTAs with no owner, 0 (ZCTA, fine channel) cells with no row, 0 owned twice, 12 mass necks listed beside M1
- **w8-50-bal-wide** (fails M1): M1 across coverage gaps: fail, 2 districts in pieces, 2 detached pieces (largest 0.283 τ), 2 necks, 0 channel ZCTAs with no owner, 0 (ZCTA, fine channel) cells with no row, 0 owned twice, 11 mass necks listed beside M1
- **ne-52-bal-wide** (fails M1): M1 across coverage gaps: fail, 0 districts in pieces, 0 detached pieces (largest 0 τ), 2 necks, 0 channel ZCTAs with no owner, 0 (ZCTA, fine channel) cells with no row, 0 owned twice, 11 mass necks listed beside M1
- **w8-52-bal-wide** (fails M1): M1 across coverage gaps: fail, 0 districts in pieces, 0 detached pieces (largest 0 τ), 2 necks, 0 channel ZCTAs with no owner, 0 (ZCTA, fine channel) cells with no row, 0 owned twice, 10 mass necks listed beside M1
- **nw34-50-wide** (fails M1): M1 across coverage gaps: fail, 0 districts in pieces, 0 detached pieces (largest 0 τ), 2 necks, 0 channel ZCTAs with no owner, 0 (ZCTA, fine channel) cells with no row, 0 owned twice, 11 mass necks listed beside M1
- **w8-52-filight-wide** (fails M1): M1 across coverage gaps: fail, 2 districts in pieces, 2 detached pieces (largest 0.514 τ), 3 necks, 0 channel ZCTAs with no owner, 0 (ZCTA, fine channel) cells with no row, 0 owned twice, 13 mass necks listed beside M1
- **nw34-48-wide** (fails M1): M1 across coverage gaps: fail, 1 districts in pieces, 1 detached pieces (largest 0.32 τ), 3 necks, 0 channel ZCTAs with no owner, 0 (ZCTA, fine channel) cells with no row, 0 owned twice, 14 mass necks listed beside M1
- **w8-48-bal-wide** (fails M1): M1 across coverage gaps: fail, 2 districts in pieces, 2 detached pieces (largest 0.441 τ), 4 necks, 0 channel ZCTAs with no owner, 0 (ZCTA, fine channel) cells with no row, 0 owned twice, 12 mass necks listed beside M1; relabelled from draw_retry's completed score after the 8 h stop (was: stopped, the 8 h stop during score_draw_retry)
- **nw34-52-wide** (fails M1): M1 across coverage gaps: fail, 2 districts in pieces, 2 detached pieces (largest 0.126 τ), 2 necks, 0 channel ZCTAs with no owner, 0 (ZCTA, fine channel) cells with no row, 0 owned twice, 12 mass necks listed beside M1
- **ne-50-bal** (infeasible): FI: no plan up to final_delta 0.0904 (converged)
- **ne-50-filight** (infeasible): national: no plan up to final_delta 0.053 (converged)
- **ne-52-bal** (infeasible): WH: no plan up to final_delta 0.0778 (converged)
- **ne-52-filight** (infeasible): national: no plan up to final_delta 0.053 (converged)
- **ne-cmp-tierP** (infeasible): WH: no plan up to final_delta 0.0778 (converged)
- **nw34-48** (infeasible): WIFI: no plan up to final_delta 0.0972 (converged)
- **nw34-50** (infeasible): WIFI: no plan up to final_delta 0.0706 (converged)
- **nw34-52** (infeasible): national: no plan up to final_delta 0.053 (converged)
- **nw49-48** (infeasible): national: no plan up to final_delta 0.1445 (converged)
- **nw49-50** (infeasible): national: no plan up to final_delta 0.0875 (converged)
- **nw49-52** (infeasible): national: no plan up to final_delta 0.0305 (converged)
- **w1-48** (infeasible): WIFI: no plan up to final_delta 0.1286 (converged)
- **w1-50** (infeasible): WIFI: no plan up to final_delta 0.131 (converged)
- **w1-52** (infeasible): WIFI: no plan up to final_delta 0.0962 (converged)
- **w8-48-bal** (infeasible): national: no plan up to final_delta 0.1755 (converged)
- **w8-50-bal** (infeasible): national: no plan up to final_delta 0.1166 (converged)
- **w8-50-filight** (infeasible): national: no plan up to final_delta 0.0577 (converged)
- **w8-52-bal** (infeasible): national: no plan up to final_delta 0.1166 (converged)
- **w8-52-filight** (infeasible): national: no plan up to final_delta 0.0577 (converged)
- **w8-cmp-seed** (infeasible): national: no plan up to final_delta 0.1004 (converged)
- **ne-50-filight-wide** (stopped): the 8 h stop during draw_retry
- **ne-cmp-tierP-wide** (stopped): the 8 h stop during draw_retry
- **w8-50-filight-wide** (stopped): the 8 h stop during r1

## Needs your eye

- ne-50-bal-wide: WIFI_03 1,230.7M on the whole-state allowance (up to 1,600.0M)
- ne-50-bal-wide: FI NY in-state land ratio 31.55 beyond R = 10 (FI_17 117494.7 km², FI_16 3724.6 km²)
- ne-50-bal-wide: national CA in-state land ratio 29.36 beyond R = 10 (national_07 168294.8 km², national_06 5732.8 km²)
- ne-50-bal-wide: national NY in-state land ratio 32.08 beyond R = 10 (national_08 117457.3 km², national_14 3661.1 km²)
- w1-50-wide: M1 flip WIFI/WIFI_20, a neck strict only: WIFI/WIFI_20: neck 5.48 km wide cuts off 96 ZIPs (84511...), 6.5% of its land area and 6.6% of its mass; cut 84621-84652 4.19 km, 84621-84654 1.29 km
- w1-50-wide: WIFI_31 1,275.4M on the whole-state allowance (up to 1,600.0M)
- w1-50-wide: WIFI CA in-state land ratio 54.82 beyond R = 10 (WIFI_10 106875.0 km², WIFI_06 1949.5 km²)
- w1-50-wide: WIFI IL in-state land ratio 24.48 beyond R = 10 (WIFI_22 138077.4 km², WIFI_21 5641.4 km²)
- w1-50-wide: WIFI NY in-state land ratio 395.70 beyond R = 10 (WIFI_39 69930.5 km², WIFI_38 176.7 km²)
- w1-50-wide: WIFI PA in-state land ratio 19.63 beyond R = 10 (WIFI_44 76026.7 km², WIFI_43 3872.6 km²)
- ne-52-filight-wide: WIFI_03 1,230.7M on the whole-state allowance (up to 1,600.0M)
- ne-52-filight-wide: FI NY in-state land ratio 31.55 beyond R = 10 (FI_17 117494.7 km², FI_16 3724.6 km²)
- ne-52-filight-wide: national CA in-state land ratio 29.67 beyond R = 10 (national_07 167368.5 km², national_06 5640.2 km²)
- ne-52-filight-wide: national NY in-state land ratio 32.28 beyond R = 10 (national_09 117674.1 km², national_14 3645.4 km²)
- ne-48-bal: WIFI_03 1,230.7M on the whole-state allowance (up to 1,600.0M)
- w1-48-wide: WIFI_25 1,230.7M on the whole-state allowance (up to 1,600.0M)
- w1-48-wide: WIFI CA in-state land ratio 45.40 beyond R = 10 (WIFI_07 121259.2 km², WIFI_06 2670.7 km²)
- w1-48-wide: WIFI IL in-state land ratio 24.48 beyond R = 10 (WIFI_21 138077.4 km², WIFI_20 5641.4 km²)
- w1-48-wide: WIFI NY in-state land ratio 123.40 beyond R = 10 (WIFI_37 68651.1 km², WIFI_36 556.4 km²)
- w1-48-wide: WIFI PA in-state land ratio 15.52 beyond R = 10 (WIFI_41 74135.7 km², WIFI_40 4777.5 km²)
- w1-52-wide: WIFI CA in-state land ratio 60.58 beyond R = 10 (WIFI_07 123333.0 km², WIFI_06 2035.8 km²)
- w1-52-wide: WIFI IL in-state land ratio 24.48 beyond R = 10 (WIFI_23 138077.4 km², WIFI_22 5641.4 km²)
- w1-52-wide: WIFI NY in-state land ratio 405.67 beyond R = 10 (WIFI_42 71010.5 km², WIFI_41 175.0 km²)
- w1-52-wide: WIFI PA in-state land ratio 15.52 beyond R = 10 (WIFI_45 74135.7 km², WIFI_44 4777.5 km²)
- w1-52-wide: WIFI VA in-state land ratio 20.25 beyond R = 10 (WIFI_51 97218.3 km², WIFI_13 4801.8 km²)
- w8-cmp-seed-wide: M1 flip national/national_03, a neck strict only: national/national_03: neck 5.48 km wide cuts off 203 ZIPs (82930...), 13.6% of its land area and 15.0% of its mass; cut 84621-84652 4.19 km, 84621-84654 1.29 km
- w8-cmp-seed-wide: WIFI_01 1,542.7M on the whole-state allowance (up to 1,600.0M)
- w8-cmp-seed-wide: FI NY in-state land ratio 55.65 beyond R = 10 (FI_20 115596.0 km², FI_06 2077.1 km²)
- w8-cmp-seed-wide: national CA in-state land ratio 31.63 beyond R = 10 (national_06 168567.8 km², national_05 5329.1 km²)
- w8-50-bal-wide: WIFI_01 1,542.7M on the whole-state allowance (up to 1,600.0M)
- w8-50-bal-wide: FI NY in-state land ratio 55.25 beyond R = 10 (FI_19 115574.6 km², FI_06 2091.9 km²)
- w8-50-bal-wide: FI PA in-state land ratio 48.24 beyond R = 10 (FI_21 94505.0 km², FI_08 1959.0 km²)
- w8-50-bal-wide: national CA in-state land ratio 28.47 beyond R = 10 (national_07 123685.5 km², national_06 4345.0 km²)
- w8-50-bal-wide: national NY in-state land ratio 26.23 beyond R = 10 (national_14 116864.6 km², national_08 4454.8 km²)
- ne-52-bal-wide: WIFI_03 1,230.7M on the whole-state allowance (up to 1,600.0M)
- ne-52-bal-wide: FI NY in-state land ratio 33.40 beyond R = 10 (FI_19 114242.1 km², FI_20 3420.0 km²)
- ne-52-bal-wide: national CA in-state land ratio 29.36 beyond R = 10 (national_07 168294.8 km², national_06 5732.8 km²)
- ne-52-bal-wide: national NY in-state land ratio 32.08 beyond R = 10 (national_08 117457.3 km², national_14 3661.1 km²)
- w8-52-bal-wide: WIFI_01 1,542.7M on the whole-state allowance (up to 1,600.0M)
- w8-52-bal-wide: FI NY in-state land ratio 55.50 beyond R = 10 (FI_20 115596.0 km², FI_06 2082.9 km²)
- w8-52-bal-wide: WH NY in-state land ratio 30.36 beyond R = 10 (WH_11 117450.2 km², WH_04 3869.2 km²)
- w8-52-bal-wide: national CA in-state land ratio 28.47 beyond R = 10 (national_07 123685.5 km², national_06 4345.0 km²)
- w8-52-bal-wide: national NY in-state land ratio 26.23 beyond R = 10 (national_14 116864.6 km², national_08 4454.8 km²)
- nw34-50-wide: M1 flip national/national_14, a neck strict only: national/national_14: neck 0.00 km wide cuts off 50 ZIPs (10901...), 45.8% of its land area and 6.1% of its mass; cut 12508-12550 0.00 km
- nw34-50-wide: WIFI_02 1,162.9M on the whole-state allowance (up to 1,600.0M)
- nw34-50-wide: WIFI CT in-state land ratio 13.55 beyond R = 10 (WIFI_09 11679.8 km², WIFI_10 862.3 km²)
- nw34-50-wide: WIFI NY in-state land ratio 91.59 beyond R = 10 (WIFI_30 116391.8 km², WIFI_10 1270.7 km²)
- nw34-50-wide: national CA in-state land ratio 34.21 beyond R = 10 (national_07 164082.4 km², national_06 4795.9 km²)
- nw34-50-wide: national NY in-state land ratio 40.05 beyond R = 10 (national_13 118364.3 km², national_14 2955.1 km²)
- w8-52-filight-wide: M1 flip national/national_03, a neck strict only: national/national_03: neck 5.48 km wide cuts off 203 ZIPs (82930...), 15.7% of its land area and 26.2% of its mass; cut 84621-84652 4.19 km, 84621-84654 1.29 km
- w8-52-filight-wide: WIFI_01 1,542.7M on the whole-state allowance (up to 1,600.0M)
- w8-52-filight-wide: FI NY in-state land ratio 54.22 beyond R = 10 (FI_19 115655.7 km², FI_06 2133.0 km²)
- w8-52-filight-wide: WH NY in-state land ratio 30.36 beyond R = 10 (WH_11 117450.2 km², WH_04 3869.2 km²)
- w8-52-filight-wide: national CA in-state land ratio 27.12 beyond R = 10 (national_07 168143.1 km², national_06 6200.3 km²)
- nw34-48-wide: M1 flip WIFI/WIFI_05, a neck strict only: WIFI/WIFI_05: neck 5.96 km wide cuts off 236 ZIPs (93635...), 16.6% of its land area and 82.6% of its mass; cut 94115-94129 0.26 km, 94118-94129 2.82 km, 94121-94129 1.12 km, 94123-94129 1.77 km
- nw34-48-wide: M1 flip WIFI/WIFI_06, a neck strict only: WIFI/WIFI_06: neck 9.39 km wide cuts off 29 ZIPs (93901...), 5.6% of its land area and 2.0% of its mass; cut 93452-93920 9.39 km
- nw34-48-wide: M1 flip WIFI/WIFI_11, a neck strict only: WIFI/WIFI_11: neck 3.01 km wide cuts off 4 ZIPs (33430...), 19.8% of its land area and 0.0% of its mass; cut 33430-33470 3.01 km
- nw34-48-wide: WIFI NY in-state land ratio 31.37 beyond R = 10 (WIFI_29 114000.9 km², WIFI_09 3634.2 km²)
- nw34-48-wide: national CA in-state land ratio 34.21 beyond R = 10 (national_07 164082.4 km², national_06 4795.9 km²)
- w8-48-bal-wide: M1 flip national/national_03, a neck strict only: national/national_03: neck 5.48 km wide cuts off 203 ZIPs (82930...), 13.4% of its land area and 15.0% of its mass; cut 84621-84652 4.19 km, 84621-84654 1.29 km
- w8-48-bal-wide: M1 flip national/national_04, a neck strict only: national/national_04: neck 8.81 km wide cuts off 5 ZIPs (93527...), 5.9% of its land area and 0.0% of its mass; cut 93527-93554 8.81 km
- w8-48-bal-wide: WIFI_01 1,542.7M on the whole-state allowance (up to 1,600.0M)
- nw34-52-wide: WIFI NY in-state land ratio 52.23 beyond R = 10 (WIFI_29 100997.3 km², WIFI_28 1933.8 km²)
- nw34-52-wide: national CA in-state land ratio 42.70 beyond R = 10 (national_07 117407.9 km², national_06 2749.4 km²)
