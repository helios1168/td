# MORNING: main_overnight_2026-10-13

Built by `tools/exp/contig/overnight.py morning` from `GRID.json` at 2026-10-13T15:28:29+00:00.  Extract `instance_descaled_usd.json.gz` (sha256 `98cc87bc8ba5`); code `54f5afa`; stop at 2026-10-13T17:47:53+00:00.

27 points: 4 fails M1, 6 infeasible, 17 error.

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
| 1 | w8-cmp-seed-wide | west8 | national 13, WH 11, FI 24, WIFI 1 = 49 | 13 | 8.7594 | WH_04 -29.8% (686.7M) | fail / fail, 1 flips | 55.6 (2 > R) | **fails M1** | [folder](w8-cmp-seed-wide/r2/) · [map](w8-cmp-seed-wide/r2/summary.png) · [score](w8-cmp-seed-wide/r2/score.txt) |
| 2 | w8-50-bal-wide | west8 | national 15, WH 11, FI 23, WIFI 1 = 50 | 13 | 9.4477 | WH_04 -29.8% (686.7M) | fail / fail | 55.2 (4 > R) | **fails M1** | [folder](w8-50-bal-wide/r2/) · [map](w8-50-bal-wide/r2/summary.png) · [score](w8-50-bal-wide/r2/score.txt) |
| 3 | w8-52-bal-wide | west8 | national 15, WH 12, FI 24, WIFI 1 = 52 | 15 | 4 | national_14 -24.4% (855.3M) | fail / fail | 55.5 (4 > R) | **fails M1** | [folder](w8-52-bal-wide/r2/) · [map](w8-52-bal-wide/r2/summary.png) · [score](w8-52-bal-wide/r2/score.txt) |
| 4 | w8-52-filight-wide | west8 | national 16, WH 12, FI 23, WIFI 1 = 52 | 16 | 8.6796 | national_15 -31.5% (727.1M) | fail / fail, 1 flips | 54.2 (3 > R) | **fails M1** | [folder](w8-52-filight-wide/r2/) · [map](w8-52-filight-wide/r2/summary.png) · [score](w8-52-filight-wide/r2/score.txt) |
| 5 | w8-48-bal | west8 | national 14, WH 11, FI 22, WIFI 1 = 48 | — | — | — | — | — | **infeasible** | — |
| 6 | w8-50-bal | west8 | national 15, WH 11, FI 23, WIFI 1 = 50 | — | — | — | — | — | **infeasible** | — |
| 7 | w8-50-filight | west8 | national 16, WH 12, FI 21, WIFI 1 = 50 | — | — | — | — | — | **infeasible** | — |
| 8 | w8-52-bal | west8 | national 15, WH 12, FI 24, WIFI 1 = 52 | — | — | — | — | — | **infeasible** | — |
| 9 | w8-52-filight | west8 | national 16, WH 12, FI 23, WIFI 1 = 52 | — | — | — | — | — | **infeasible** | — |
| 10 | w8-cmp-seed | west8 | national 13, WH 11, FI 24, WIFI 1 = 49 | — | — | — | — | — | **infeasible** | — |
| 11 | ne-48-bal | ne_plains | national 14, WH 10, FI 21, WIFI 3 = 48 | — | — | — | — | — | **error** | — |
| 12 | ne-50-bal | ne_plains | national 15, WH 10, FI 22, WIFI 3 = 50 | — | — | — | — | — | **error** | — |
| 13 | ne-50-filight | ne_plains | national 16, WH 11, FI 20, WIFI 3 = 50 | — | — | — | — | — | **error** | — |
| 14 | ne-52-bal | ne_plains | national 15, WH 11, FI 23, WIFI 3 = 52 | — | — | — | — | — | **error** | — |
| 15 | ne-52-filight | ne_plains | national 16, WH 11, FI 22, WIFI 3 = 52 | — | — | — | — | — | **error** | — |
| 16 | ne-cmp-tierP | ne_plains | national 15, WH 11, FI 20, WIFI 3 = 49 | — | — | — | — | — | **error** | — |
| 17 | nw34-48 | nw34 | national 14, WIFI 34 = 48 | — | — | — | — | — | **error** | — |
| 18 | nw34-50 | nw34 | national 15, WIFI 35 = 50 | — | — | — | — | — | **error** | — |
| 19 | nw34-52 | nw34 | national 16, WIFI 36 = 52 | — | — | — | — | — | **error** | — |
| 20 | nw49-48 | nw49 | national 15, WIFI 33 = 48 | — | — | — | — | — | **error** | — |
| 21 | nw49-50 | nw49 | national 16, WIFI 34 = 50 | — | — | — | — | — | **error** | — |
| 22 | nw49-52 | nw49 | national 17, WIFI 35 = 52 | — | — | — | — | — | **error** | — |
| 23 | w1-48 | w1 | WIFI 48 = 48 | — | — | — | — | — | **error** | — |
| 24 | w1-50 | w1 | WIFI 50 = 50 | — | — | — | — | — | **error** | — |
| 25 | w1-52 | w1 | WIFI 52 = 52 | — | — | — | — | — | **error** | — |
| 26 | w8-48-bal-wide | west8 | national 14, WH 11, FI 22, WIFI 1 = 48 | — | — | — | — | — | **error** | — |
| 27 | w8-50-filight-wide | west8 | national 16, WH 12, FI 21, WIFI 1 = 50 | — | — | — | — | — | **error** | — |

## Reasons

- **w8-cmp-seed-wide** (fails M1): M1 across coverage gaps: fail, 2 districts in pieces, 2 detached pieces (largest 0.477 τ), 4 necks, 0 channel ZCTAs with no owner, 0 (ZCTA, fine channel) cells with no row, 0 owned twice, 12 mass necks listed beside M1
- **w8-50-bal-wide** (fails M1): M1 across coverage gaps: fail, 2 districts in pieces, 2 detached pieces (largest 0.283 τ), 2 necks, 0 channel ZCTAs with no owner, 0 (ZCTA, fine channel) cells with no row, 0 owned twice, 11 mass necks listed beside M1
- **w8-52-bal-wide** (fails M1): M1 across coverage gaps: fail, 0 districts in pieces, 0 detached pieces (largest 0 τ), 2 necks, 0 channel ZCTAs with no owner, 0 (ZCTA, fine channel) cells with no row, 0 owned twice, 10 mass necks listed beside M1
- **w8-52-filight-wide** (fails M1): M1 across coverage gaps: fail, 2 districts in pieces, 2 detached pieces (largest 0.514 τ), 3 necks, 0 channel ZCTAs with no owner, 0 (ZCTA, fine channel) cells with no row, 0 owned twice, 13 mass necks listed beside M1
- **w8-48-bal** (infeasible): national: no plan up to final_delta 0.1755 (converged)
- **w8-50-bal** (infeasible): national: no plan up to final_delta 0.1166 (converged)
- **w8-50-filight** (infeasible): national: no plan up to final_delta 0.0577 (converged)
- **w8-52-bal** (infeasible): national: no plan up to final_delta 0.1166 (converged)
- **w8-52-filight** (infeasible): national: no plan up to final_delta 0.0577 (converged)
- **w8-cmp-seed** (infeasible): national: no plan up to final_delta 0.1004 (converged)
- **ne-48-bal** (error): no label (status elsewhere)
- **ne-50-bal** (error): no label (status elsewhere)
- **ne-50-filight** (error): no label (status elsewhere)
- **ne-52-bal** (error): no label (status elsewhere)
- **ne-52-filight** (error): no label (status elsewhere)
- **ne-cmp-tierP** (error): no label (status elsewhere)
- **nw34-48** (error): no label (status elsewhere)
- **nw34-50** (error): no label (status elsewhere)
- **nw34-52** (error): no label (status elsewhere)
- **nw49-48** (error): no label (status elsewhere)
- **nw49-50** (error): no label (status elsewhere)
- **nw49-52** (error): no label (status elsewhere)
- **w1-48** (error): no label (status elsewhere)
- **w1-50** (error): no label (status elsewhere)
- **w1-52** (error): no label (status elsewhere)
- **w8-48-bal-wide** (error): no label (status running)
- **w8-50-filight-wide** (error): no label (status running)

## Needs your eye

- render failed (exit 1): w8-50-bal-wide/draw/render.log
- render failed (exit 1): w8-50-bal-wide/r1/render.log
- render failed (exit 1): w8-50-bal-wide/r2/render.log
- render failed (exit 1): w8-52-filight-wide/draw/render.log
- render failed (exit 1): w8-52-filight-wide/r1/render.log
- render failed (exit 1): w8-52-filight-wide/r2/render.log
- w8-cmp-seed-wide: M1 flip national/national_03, a neck strict only: national/national_03: neck 5.48 km wide cuts off 203 ZIPs (82930...), 13.6% of its land area and 15.0% of its mass; cut 84621-84652 4.19 km, 84621-84654 1.29 km
- w8-cmp-seed-wide: WIFI_01 1,542.7M on the whole-state allowance (up to 1,600.0M)
- w8-cmp-seed-wide: FI NY in-state land ratio 55.65 beyond R = 10 (FI_20 115596.0 km², FI_06 2077.1 km²)
- w8-cmp-seed-wide: national CA in-state land ratio 31.63 beyond R = 10 (national_06 168567.8 km², national_05 5329.1 km²)
- w8-50-bal-wide: WIFI_01 1,542.7M on the whole-state allowance (up to 1,600.0M)
- w8-50-bal-wide: FI NY in-state land ratio 55.25 beyond R = 10 (FI_19 115574.6 km², FI_06 2091.9 km²)
- w8-50-bal-wide: FI PA in-state land ratio 48.24 beyond R = 10 (FI_21 94505.0 km², FI_08 1959.0 km²)
- w8-50-bal-wide: national CA in-state land ratio 28.47 beyond R = 10 (national_07 123685.5 km², national_06 4345.0 km²)
- w8-50-bal-wide: national NY in-state land ratio 26.23 beyond R = 10 (national_14 116864.6 km², national_08 4454.8 km²)
- w8-52-bal-wide: WIFI_01 1,542.7M on the whole-state allowance (up to 1,600.0M)
- w8-52-bal-wide: FI NY in-state land ratio 55.50 beyond R = 10 (FI_20 115596.0 km², FI_06 2082.9 km²)
- w8-52-bal-wide: WH NY in-state land ratio 30.36 beyond R = 10 (WH_11 117450.2 km², WH_04 3869.2 km²)
- w8-52-bal-wide: national CA in-state land ratio 28.47 beyond R = 10 (national_07 123685.5 km², national_06 4345.0 km²)
- w8-52-bal-wide: national NY in-state land ratio 26.23 beyond R = 10 (national_14 116864.6 km², national_08 4454.8 km²)
- w8-52-filight-wide: M1 flip national/national_03, a neck strict only: national/national_03: neck 5.48 km wide cuts off 203 ZIPs (82930...), 15.7% of its land area and 26.2% of its mass; cut 84621-84652 4.19 km, 84621-84654 1.29 km
- w8-52-filight-wide: WIFI_01 1,542.7M on the whole-state allowance (up to 1,600.0M)
- w8-52-filight-wide: FI NY in-state land ratio 54.22 beyond R = 10 (FI_19 115655.7 km², FI_06 2133.0 km²)
- w8-52-filight-wide: WH NY in-state land ratio 30.36 beyond R = 10 (WH_11 117450.2 km², WH_04 3869.2 km²)
- w8-52-filight-wide: national CA in-state land ratio 27.12 beyond R = 10 (national_07 168143.1 km², national_06 6200.3 km²)
- ne-48-bal: no label (status elsewhere), counted as an error
- ne-50-bal: no label (status elsewhere), counted as an error
- ne-50-filight: no label (status elsewhere), counted as an error
- ne-52-bal: no label (status elsewhere), counted as an error
- ne-52-filight: no label (status elsewhere), counted as an error
- ne-cmp-tierP: no label (status elsewhere), counted as an error
- nw34-48: no label (status elsewhere), counted as an error
- nw34-50: no label (status elsewhere), counted as an error
- nw34-52: no label (status elsewhere), counted as an error
- nw49-48: no label (status elsewhere), counted as an error
- nw49-50: no label (status elsewhere), counted as an error
- nw49-52: no label (status elsewhere), counted as an error
- w1-48: no label (status elsewhere), counted as an error
- w1-50: no label (status elsewhere), counted as an error
- w1-52: no label (status elsewhere), counted as an error
- w8-48-bal-wide: no label (status running), counted as an error
- w8-50-filight-wide: no label (status running), counted as an error
