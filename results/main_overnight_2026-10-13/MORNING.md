# MORNING: main_overnight_2026-10-13

Built by `tools/exp/contig/overnight.py morning` from `GRID.json` at 2026-10-13T15:00:14+00:00.  Extract `instance_descaled_usd.json.gz` (sha256 `98cc87bc8ba5`); code `54f5afa`; stop at 2026-10-13T17:47:53+00:00.

32 points: 6 fails M1, 14 infeasible, 12 error.

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
| 1 | w1-50-wide | w1 | WIFI 50 = 50 | 11 | 10.7492 | WIFI_01 -31.4% (670.9M) | fail / fail, 1 flips | 395.7 (4 > R) | **fails M1** | [folder](w1-50-wide/r2/) · [map](w1-50-wide/r2/summary.png) · [score](w1-50-wide/r2/score.txt) |
| 2 | w1-48-wide | w1 | WIFI 48 = 48 | 12 | 9.7483 | WIFI_31 +30.3% (1,327.9M) | fail / fail, 1 flips | 123.4 (4 > R) | **fails M1** | [folder](w1-48-wide/r2/) · [map](w1-48-wide/r2/summary.png) · [score](w1-48-wide/r2/score.txt) |
| 3 | w1-52-wide | w1 | WIFI 52 = 52 | 13 | 8.7538 | WIFI_20 -28.8% (669.6M) | fail / fail | 405.7 (5 > R) | **fails M1** | [folder](w1-52-wide/r2/) · [map](w1-52-wide/r2/summary.png) · [score](w1-52-wide/r2/score.txt) |
| 4 | nw34-50-wide | nw34 | national 15, WIFI 35 = 50 | 16 | 0 | national_10 -28.1% (809.4M) | fail / fail, 1 flips | 91.6 (4 > R) | **fails M1** | [folder](nw34-50-wide/r2/) · [map](nw34-50-wide/r2/summary.png) · [score](nw34-50-wide/r2/score.txt) |
| 5 | nw34-48-wide | nw34 | national 14, WIFI 34 = 48 | 17 | 6.3197 | WIFI_21 -22.7% (727.6M) | fail / fail, 3 flips | 34.2 (2 > R) | **fails M1** | [folder](nw34-48-wide/r2/) · [map](nw34-48-wide/r2/summary.png) · [score](nw34-48-wide/r2/score.txt) |
| 6 | nw34-52-wide | nw34 | national 16, WIFI 36 = 52 | 19 | 8.2367 | WIFI_31 +27.2% (1,131.0M) | fail / fail | 52.2 (2 > R) | **fails M1** | [folder](nw34-52-wide/r2/) · [map](nw34-52-wide/r2/summary.png) · [score](nw34-52-wide/r2/score.txt) |
| 7 | ne-50-bal | ne_plains | national 15, WH 10, FI 22, WIFI 3 = 50 | — | — | — | — | — | **infeasible** | — |
| 8 | ne-50-filight | ne_plains | national 16, WH 11, FI 20, WIFI 3 = 50 | — | — | — | — | — | **infeasible** | — |
| 9 | ne-52-bal | ne_plains | national 15, WH 11, FI 23, WIFI 3 = 52 | — | — | — | — | — | **infeasible** | — |
| 10 | ne-52-filight | ne_plains | national 16, WH 11, FI 22, WIFI 3 = 52 | — | — | — | — | — | **infeasible** | — |
| 11 | ne-cmp-tierP | ne_plains | national 15, WH 11, FI 20, WIFI 3 = 49 | — | — | — | — | — | **infeasible** | — |
| 12 | nw34-48 | nw34 | national 14, WIFI 34 = 48 | — | — | — | — | — | **infeasible** | — |
| 13 | nw34-50 | nw34 | national 15, WIFI 35 = 50 | — | — | — | — | — | **infeasible** | — |
| 14 | nw34-52 | nw34 | national 16, WIFI 36 = 52 | — | — | — | — | — | **infeasible** | — |
| 15 | nw49-48 | nw49 | national 15, WIFI 33 = 48 | — | — | — | — | — | **infeasible** | — |
| 16 | nw49-50 | nw49 | national 16, WIFI 34 = 50 | — | — | — | — | — | **infeasible** | — |
| 17 | nw49-52 | nw49 | national 17, WIFI 35 = 52 | — | — | — | — | — | **infeasible** | — |
| 18 | w1-48 | w1 | WIFI 48 = 48 | — | — | — | — | — | **infeasible** | — |
| 19 | w1-50 | w1 | WIFI 50 = 50 | — | — | — | — | — | **infeasible** | — |
| 20 | w1-52 | w1 | WIFI 52 = 52 | — | — | — | — | — | **infeasible** | — |
| 21 | ne-48-bal | ne_plains | national 14, WH 10, FI 21, WIFI 3 = 48 | — | — | — | — | — | **error** | — |
| 22 | ne-50-bal-wide | ne_plains | national 15, WH 10, FI 22, WIFI 3 = 50 | — | — | — | — | — | **error** | — |
| 23 | ne-50-filight-wide | ne_plains | national 16, WH 11, FI 20, WIFI 3 = 50 | — | — | — | — | — | **error** | — |
| 24 | ne-52-bal-wide | ne_plains | national 15, WH 11, FI 23, WIFI 3 = 52 | — | — | — | — | — | **error** | — |
| 25 | ne-52-filight-wide | ne_plains | national 16, WH 11, FI 22, WIFI 3 = 52 | — | — | — | — | — | **error** | — |
| 26 | ne-cmp-tierP-wide | ne_plains | national 15, WH 11, FI 20, WIFI 3 = 49 | — | — | — | — | — | **error** | — |
| 27 | w8-48-bal | west8 | national 14, WH 11, FI 22, WIFI 1 = 48 | — | — | — | — | — | **error** | — |
| 28 | w8-50-bal | west8 | national 15, WH 11, FI 23, WIFI 1 = 50 | — | — | — | — | — | **error** | — |
| 29 | w8-50-filight | west8 | national 16, WH 12, FI 21, WIFI 1 = 50 | — | — | — | — | — | **error** | — |
| 30 | w8-52-bal | west8 | national 15, WH 12, FI 24, WIFI 1 = 52 | — | — | — | — | — | **error** | — |
| 31 | w8-52-filight | west8 | national 16, WH 12, FI 23, WIFI 1 = 52 | — | — | — | — | — | **error** | — |
| 32 | w8-cmp-seed | west8 | national 13, WH 11, FI 24, WIFI 1 = 49 | — | — | — | — | — | **error** | — |

## Reasons

- **w1-50-wide** (fails M1): M1 across coverage gaps: fail, 2 districts in pieces, 2 detached pieces (largest 0.406 τ), 2 necks, 0 channel ZCTAs with no owner, 0 (ZCTA, fine channel) cells with no row, 0 owned twice, 15 mass necks listed beside M1
- **w1-48-wide** (fails M1): M1 across coverage gaps: fail, 2 districts in pieces, 2 detached pieces (largest 0.414 τ), 2 necks, 0 channel ZCTAs with no owner, 0 (ZCTA, fine channel) cells with no row, 0 owned twice, 14 mass necks listed beside M1
- **w1-52-wide** (fails M1): M1 across coverage gaps: fail, 2 districts in pieces, 2 detached pieces (largest 0.423 τ), 4 necks, 0 channel ZCTAs with no owner, 0 (ZCTA, fine channel) cells with no row, 0 owned twice, 16 mass necks listed beside M1
- **nw34-50-wide** (fails M1): M1 across coverage gaps: fail, 0 districts in pieces, 0 detached pieces (largest 0 τ), 2 necks, 0 channel ZCTAs with no owner, 0 (ZCTA, fine channel) cells with no row, 0 owned twice, 11 mass necks listed beside M1
- **nw34-48-wide** (fails M1): M1 across coverage gaps: fail, 1 districts in pieces, 1 detached pieces (largest 0.32 τ), 3 necks, 0 channel ZCTAs with no owner, 0 (ZCTA, fine channel) cells with no row, 0 owned twice, 14 mass necks listed beside M1
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
- **ne-48-bal** (error): no label (status queued)
- **ne-50-bal-wide** (error): no label (status running)
- **ne-50-filight-wide** (error): no label (status queued)
- **ne-52-bal-wide** (error): no label (status running)
- **ne-52-filight-wide** (error): no label (status running)
- **ne-cmp-tierP-wide** (error): no label (status queued)
- **w8-48-bal** (error): no label (status elsewhere)
- **w8-50-bal** (error): no label (status elsewhere)
- **w8-50-filight** (error): no label (status elsewhere)
- **w8-52-bal** (error): no label (status elsewhere)
- **w8-52-filight** (error): no label (status elsewhere)
- **w8-cmp-seed** (error): no label (status elsewhere)

## Needs your eye

- w1-50-wide: M1 flip WIFI/WIFI_20, a neck strict only: WIFI/WIFI_20: neck 5.48 km wide cuts off 96 ZIPs (84511...), 6.5% of its land area and 6.6% of its mass; cut 84621-84652 4.19 km, 84621-84654 1.29 km
- w1-50-wide: WIFI_31 1,275.4M on the whole-state allowance (up to 1,600.0M)
- w1-50-wide: WIFI CA in-state land ratio 54.82 beyond R = 10 (WIFI_10 106875.0 km², WIFI_06 1949.5 km²)
- w1-50-wide: WIFI IL in-state land ratio 24.48 beyond R = 10 (WIFI_22 138077.4 km², WIFI_21 5641.4 km²)
- w1-50-wide: WIFI NY in-state land ratio 395.70 beyond R = 10 (WIFI_39 69930.5 km², WIFI_38 176.7 km²)
- w1-50-wide: WIFI PA in-state land ratio 19.63 beyond R = 10 (WIFI_44 76026.7 km², WIFI_43 3872.6 km²)
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
- nw34-50-wide: M1 flip national/national_14, a neck strict only: national/national_14: neck 0.00 km wide cuts off 50 ZIPs (10901...), 45.8% of its land area and 6.1% of its mass; cut 12508-12550 0.00 km
- nw34-50-wide: WIFI_02 1,162.9M on the whole-state allowance (up to 1,600.0M)
- nw34-50-wide: WIFI CT in-state land ratio 13.55 beyond R = 10 (WIFI_09 11679.8 km², WIFI_10 862.3 km²)
- nw34-50-wide: WIFI NY in-state land ratio 91.59 beyond R = 10 (WIFI_30 116391.8 km², WIFI_10 1270.7 km²)
- nw34-50-wide: national CA in-state land ratio 34.21 beyond R = 10 (national_07 164082.4 km², national_06 4795.9 km²)
- nw34-50-wide: national NY in-state land ratio 40.05 beyond R = 10 (national_13 118364.3 km², national_14 2955.1 km²)
- nw34-48-wide: M1 flip WIFI/WIFI_05, a neck strict only: WIFI/WIFI_05: neck 5.96 km wide cuts off 236 ZIPs (93635...), 16.6% of its land area and 82.6% of its mass; cut 94115-94129 0.26 km, 94118-94129 2.82 km, 94121-94129 1.12 km, 94123-94129 1.77 km
- nw34-48-wide: M1 flip WIFI/WIFI_06, a neck strict only: WIFI/WIFI_06: neck 9.39 km wide cuts off 29 ZIPs (93901...), 5.6% of its land area and 2.0% of its mass; cut 93452-93920 9.39 km
- nw34-48-wide: M1 flip WIFI/WIFI_11, a neck strict only: WIFI/WIFI_11: neck 3.01 km wide cuts off 4 ZIPs (33430...), 19.8% of its land area and 0.0% of its mass; cut 33430-33470 3.01 km
- nw34-48-wide: WIFI NY in-state land ratio 31.37 beyond R = 10 (WIFI_29 114000.9 km², WIFI_09 3634.2 km²)
- nw34-48-wide: national CA in-state land ratio 34.21 beyond R = 10 (national_07 164082.4 km², national_06 4795.9 km²)
- nw34-52-wide: WIFI NY in-state land ratio 52.23 beyond R = 10 (WIFI_29 100997.3 km², WIFI_28 1933.8 km²)
- nw34-52-wide: national CA in-state land ratio 42.70 beyond R = 10 (national_07 117407.9 km², national_06 2749.4 km²)
- ne-48-bal: no label (status queued), counted as an error
- ne-50-bal-wide: no label (status running), counted as an error
- ne-50-filight-wide: no label (status queued), counted as an error
- ne-52-bal-wide: no label (status running), counted as an error
- ne-52-filight-wide: no label (status running), counted as an error
- ne-cmp-tierP-wide: no label (status queued), counted as an error
- w8-48-bal: no label (status elsewhere), counted as an error
- w8-50-bal: no label (status elsewhere), counted as an error
- w8-50-filight: no label (status elsewhere), counted as an error
- w8-52-bal: no label (status elsewhere), counted as an error
- w8-52-filight: no label (status elsewhere), counted as an error
- w8-cmp-seed: no label (status elsewhere), counted as an error
