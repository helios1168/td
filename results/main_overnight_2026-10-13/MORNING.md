# MORNING: main_overnight_2026-10-13

Built by `tools/exp/contig/overnight.py morning` from `GRID.json` at 2026-10-13T10:00:39+00:00.  Extract `instance_descaled_usd.json.gz` (sha256 `98cc87bc8ba5`); code `54f5afa`; stop at 2026-10-13T17:47:53+00:00.

32 points: 14 infeasible, 18 error.

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
| 1 | ne-50-bal | ne_plains | national 15, WH 10, FI 22, WIFI 3 = 50 | — | — | — | — | — | **infeasible** | — |
| 2 | ne-50-filight | ne_plains | national 16, WH 11, FI 20, WIFI 3 = 50 | — | — | — | — | — | **infeasible** | — |
| 3 | ne-52-bal | ne_plains | national 15, WH 11, FI 23, WIFI 3 = 52 | — | — | — | — | — | **infeasible** | — |
| 4 | ne-52-filight | ne_plains | national 16, WH 11, FI 22, WIFI 3 = 52 | — | — | — | — | — | **infeasible** | — |
| 5 | ne-cmp-tierP | ne_plains | national 15, WH 11, FI 20, WIFI 3 = 49 | — | — | — | — | — | **infeasible** | — |
| 6 | nw34-48 | nw34 | national 14, WIFI 34 = 48 | — | — | — | — | — | **infeasible** | — |
| 7 | nw34-50 | nw34 | national 15, WIFI 35 = 50 | — | — | — | — | — | **infeasible** | — |
| 8 | nw34-52 | nw34 | national 16, WIFI 36 = 52 | — | — | — | — | — | **infeasible** | — |
| 9 | nw49-48 | nw49 | national 15, WIFI 33 = 48 | — | — | — | — | — | **infeasible** | — |
| 10 | nw49-50 | nw49 | national 16, WIFI 34 = 50 | — | — | — | — | — | **infeasible** | — |
| 11 | nw49-52 | nw49 | national 17, WIFI 35 = 52 | — | — | — | — | — | **infeasible** | — |
| 12 | w1-48 | w1 | WIFI 48 = 48 | — | — | — | — | — | **infeasible** | — |
| 13 | w1-50 | w1 | WIFI 50 = 50 | — | — | — | — | — | **infeasible** | — |
| 14 | w1-52 | w1 | WIFI 52 = 52 | — | — | — | — | — | **infeasible** | — |
| 15 | ne-48-bal | ne_plains | national 14, WH 10, FI 21, WIFI 3 = 48 | — | — | — | — | — | **error** | — |
| 16 | ne-50-bal-wide | ne_plains | national 15, WH 10, FI 22, WIFI 3 = 50 | — | — | — | — | — | **error** | — |
| 17 | ne-50-filight-wide | ne_plains | national 16, WH 11, FI 20, WIFI 3 = 50 | — | — | — | — | — | **error** | — |
| 18 | ne-52-bal-wide | ne_plains | national 15, WH 11, FI 23, WIFI 3 = 52 | — | — | — | — | — | **error** | — |
| 19 | ne-52-filight-wide | ne_plains | national 16, WH 11, FI 22, WIFI 3 = 52 | — | — | — | — | — | **error** | — |
| 20 | ne-cmp-tierP-wide | ne_plains | national 15, WH 11, FI 20, WIFI 3 = 49 | — | — | — | — | — | **error** | — |
| 21 | nw34-48-wide | nw34 | national 14, WIFI 34 = 48 | — | — | — | — | — | **error** | — |
| 22 | nw34-50-wide | nw34 | national 15, WIFI 35 = 50 | — | — | — | — | — | **error** | — |
| 23 | nw34-52-wide | nw34 | national 16, WIFI 36 = 52 | — | — | — | — | — | **error** | — |
| 24 | w1-48-wide | w1 | WIFI 48 = 48 | — | — | — | — | — | **error** | — |
| 25 | w1-50-wide | w1 | WIFI 50 = 50 | — | — | — | — | — | **error** | — |
| 26 | w1-52-wide | w1 | WIFI 52 = 52 | — | — | — | — | — | **error** | — |
| 27 | w8-48-bal | west8 | national 14, WH 11, FI 22, WIFI 1 = 48 | — | — | — | — | — | **error** | — |
| 28 | w8-50-bal | west8 | national 15, WH 11, FI 23, WIFI 1 = 50 | — | — | — | — | — | **error** | — |
| 29 | w8-50-filight | west8 | national 16, WH 12, FI 21, WIFI 1 = 50 | — | — | — | — | — | **error** | — |
| 30 | w8-52-bal | west8 | national 15, WH 12, FI 24, WIFI 1 = 52 | — | — | — | — | — | **error** | — |
| 31 | w8-52-filight | west8 | national 16, WH 12, FI 23, WIFI 1 = 52 | — | — | — | — | — | **error** | — |
| 32 | w8-cmp-seed | west8 | national 13, WH 11, FI 24, WIFI 1 = 49 | — | — | — | — | — | **error** | — |

## Reasons

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
- **ne-50-bal-wide** (error): no label (status queued)
- **ne-50-filight-wide** (error): no label (status queued)
- **ne-52-bal-wide** (error): no label (status queued)
- **ne-52-filight-wide** (error): no label (status queued)
- **ne-cmp-tierP-wide** (error): no label (status queued)
- **nw34-48-wide** (error): no label (status running)
- **nw34-50-wide** (error): no label (status running)
- **nw34-52-wide** (error): no label (status running)
- **w1-48-wide** (error): no label (status running)
- **w1-50-wide** (error): no label (status running)
- **w1-52-wide** (error): no label (status running)
- **w8-48-bal** (error): no label (status elsewhere)
- **w8-50-bal** (error): no label (status elsewhere)
- **w8-50-filight** (error): no label (status elsewhere)
- **w8-52-bal** (error): no label (status elsewhere)
- **w8-52-filight** (error): no label (status elsewhere)
- **w8-cmp-seed** (error): no label (status elsewhere)

## Needs your eye

- ne-48-bal: no label (status queued), counted as an error
- ne-50-bal-wide: no label (status queued), counted as an error
- ne-50-filight-wide: no label (status queued), counted as an error
- ne-52-bal-wide: no label (status queued), counted as an error
- ne-52-filight-wide: no label (status queued), counted as an error
- ne-cmp-tierP-wide: no label (status queued), counted as an error
- nw34-48-wide: no label (status running), counted as an error
- nw34-50-wide: no label (status running), counted as an error
- nw34-52-wide: no label (status running), counted as an error
- w1-48-wide: no label (status running), counted as an error
- w1-50-wide: no label (status running), counted as an error
- w1-52-wide: no label (status running), counted as an error
- w8-48-bal: no label (status elsewhere), counted as an error
- w8-50-bal: no label (status elsewhere), counted as an error
- w8-50-filight: no label (status elsewhere), counted as an error
- w8-52-bal: no label (status elsewhere), counted as an error
- w8-52-filight: no label (status elsewhere), counted as an error
- w8-cmp-seed: no label (status elsewhere), counted as an error
