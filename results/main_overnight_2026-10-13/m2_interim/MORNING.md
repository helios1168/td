# MORNING: main_overnight_2026-10-13

Built by `tools/exp/contig/overnight.py morning` from `GRID.json` at 2026-10-13T09:53:35+00:00.  Extract `instance_descaled_usd.json.gz` (sha256 `98cc87bc8ba5`); code `54f5afa`; stop at 2026-10-13T17:47:53+00:00.

27 points: 6 infeasible, 21 error.

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
| 1 | w8-48-bal | west8 | national 14, WH 11, FI 22, WIFI 1 = 48 | — | — | — | — | — | **infeasible** | — |
| 2 | w8-50-bal | west8 | national 15, WH 11, FI 23, WIFI 1 = 50 | — | — | — | — | — | **infeasible** | — |
| 3 | w8-50-filight | west8 | national 16, WH 12, FI 21, WIFI 1 = 50 | — | — | — | — | — | **infeasible** | — |
| 4 | w8-52-bal | west8 | national 15, WH 12, FI 24, WIFI 1 = 52 | — | — | — | — | — | **infeasible** | — |
| 5 | w8-52-filight | west8 | national 16, WH 12, FI 23, WIFI 1 = 52 | — | — | — | — | — | **infeasible** | — |
| 6 | w8-cmp-seed | west8 | national 13, WH 11, FI 24, WIFI 1 = 49 | — | — | — | — | — | **infeasible** | — |
| 7 | ne-48-bal | ne_plains | national 14, WH 10, FI 21, WIFI 3 = 48 | — | — | — | — | — | **error** | — |
| 8 | ne-50-bal | ne_plains | national 15, WH 10, FI 22, WIFI 3 = 50 | — | — | — | — | — | **error** | — |
| 9 | ne-50-filight | ne_plains | national 16, WH 11, FI 20, WIFI 3 = 50 | — | — | — | — | — | **error** | — |
| 10 | ne-52-bal | ne_plains | national 15, WH 11, FI 23, WIFI 3 = 52 | — | — | — | — | — | **error** | — |
| 11 | ne-52-filight | ne_plains | national 16, WH 11, FI 22, WIFI 3 = 52 | — | — | — | — | — | **error** | — |
| 12 | ne-cmp-tierP | ne_plains | national 15, WH 11, FI 20, WIFI 3 = 49 | — | — | — | — | — | **error** | — |
| 13 | nw34-48 | nw34 | national 14, WIFI 34 = 48 | — | — | — | — | — | **error** | — |
| 14 | nw34-50 | nw34 | national 15, WIFI 35 = 50 | — | — | — | — | — | **error** | — |
| 15 | nw34-52 | nw34 | national 16, WIFI 36 = 52 | — | — | — | — | — | **error** | — |
| 16 | nw49-48 | nw49 | national 15, WIFI 33 = 48 | — | — | — | — | — | **error** | — |
| 17 | nw49-50 | nw49 | national 16, WIFI 34 = 50 | — | — | — | — | — | **error** | — |
| 18 | nw49-52 | nw49 | national 17, WIFI 35 = 52 | — | — | — | — | — | **error** | — |
| 19 | w1-48 | w1 | WIFI 48 = 48 | — | — | — | — | — | **error** | — |
| 20 | w1-50 | w1 | WIFI 50 = 50 | — | — | — | — | — | **error** | — |
| 21 | w1-52 | w1 | WIFI 52 = 52 | — | — | — | — | — | **error** | — |
| 22 | w8-48-bal-wide | west8 | national 14, WH 11, FI 22, WIFI 1 = 48 | — | — | — | — | — | **error** | — |
| 23 | w8-50-bal-wide | west8 | national 15, WH 11, FI 23, WIFI 1 = 50 | — | — | — | — | — | **error** | — |
| 24 | w8-50-filight-wide | west8 | national 16, WH 12, FI 21, WIFI 1 = 50 | — | — | — | — | — | **error** | — |
| 25 | w8-52-bal-wide | west8 | national 15, WH 12, FI 24, WIFI 1 = 52 | — | — | — | — | — | **error** | — |
| 26 | w8-52-filight-wide | west8 | national 16, WH 12, FI 23, WIFI 1 = 52 | — | — | — | — | — | **error** | — |
| 27 | w8-cmp-seed-wide | west8 | national 13, WH 11, FI 24, WIFI 1 = 49 | — | — | — | — | — | **error** | — |

## Reasons

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
- **w8-48-bal-wide** (error): no label (status queued)
- **w8-50-bal-wide** (error): no label (status queued)
- **w8-50-filight-wide** (error): no label (status queued)
- **w8-52-bal-wide** (error): no label (status queued)
- **w8-52-filight-wide** (error): no label (status queued)
- **w8-cmp-seed-wide** (error): no label (status queued)

## Needs your eye

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
- w8-48-bal-wide: no label (status queued), counted as an error
- w8-50-bal-wide: no label (status queued), counted as an error
- w8-50-filight-wide: no label (status queued), counted as an error
- w8-52-bal-wide: no label (status queued), counted as an error
- w8-52-filight-wide: no label (status queued), counted as an error
- w8-cmp-seed-wide: no label (status queued), counted as an error
