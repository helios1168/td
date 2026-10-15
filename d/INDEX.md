# Unsealed national grid, 2026-10-14: final index

Written 2026-10-14 ~20:00 CDT. Folder: `runs/exp/national_2026-10-14/` on m5 (hub); m2 results read over ssh from the same path on m2. Read-only index: nothing else was changed.

Words used below
- **Window**: the dollar band every district must sit in (FI $765-1,035M, WH $850-1,150M, WIFI $850-1,150M, national $1,000-1,437.5M; WIFI_03 may use the whole-state allowance, up to $1,231M). "Worst $ position" is the district nearest a window edge, as a fraction of the window: 0 = at the lower edge, 1 = at the upper edge.
- **M1**: every district is one connected piece of territory on the drawn map. **gap-width** is the current rule (water and empty land judged by width); **strict** is the older, harsher rule.
- **Heuristic-placed ZCTAs**: ZIP areas whose exact drawing did not finish and that the realizer's fallback placed, then repaired and checked by the final exact gate. They are in the map and gate-verified, but were not drawn by the exact solver.

## 1. Summary

- 15 points were launched (6 on m5, 9 on m2). 3 produce a map that passes the final exact gate (M1 and every district in its window): ne-48-bal, ne-50-filight, ne-cmp-tierP. All three are on m5.
- The window band worked: every point found a plan inside the band (nw49-48 and nw49-50 only after the national reach was raised to 1,500 km, see `STATUS.md` 10:20 CDT).
- The exact drawing did not finish for large coupled groups (the Pennsylvania/Mid-Atlantic, Florida and Tennessee groups in FI; the Maryland group DC+MD+DE+NJ+PA+WV in WIFI). Every first attempt ended "no connected drawing", and the long retries (`main_r2`, `main_r2b`, `main_r2c`) hit the stop or were stopped by hand with those draws still unsolved.
- The warm start (repair the first drawing instead of redrawing, glue, merge, gate) produced the passing maps. 3,629 to 5,618 of their ZCTAs are heuristic-placed; the gate still passes M1 and all districts are in window. Pass or fail is decided by the gate, not by how the area was drawn.
- 3 more m5 points fail M1 after the warm start: ne-50-bal and ne-52-filight (FI_19 in NY, 4 detached pieces, largest 0.263 τ) and ne-52-bal (FI_18 NY and FI_07 NJ).
- m2 has no complete passing map yet. nw34-48 and nw34-50 pass M1 on the WIFI channel alone, but their national channel was never drawn. nw49-48 and nw49-52 fail M1 with one 9-ZIP NY piece in a WIFI district. nw49-50 fails M1 (7 detached pieces in 4 districts, largest 0.338 τ); nw34-52's WIFI was repaired (national never drawn); the nw49-48/52 third repair passes did not join their pieces (final 21:03 CDT); w1-48/50/52 never produced a drawing.
- Earlier passing maps for comparison: last night's ne-48-bal (fully exact draw) and IFA K48-K54 (7 maps).
- Shape (section 3): 2 to 4 districts per candidate are flagged for eye review (`cut_edges >= 126 AND bite >= 0.18`); this is a look-at-the-page list, not a gate.

## 2. Candidates (pass the final exact gate)

$ figures are scored with the full dollar extract. M1 detail is from each map's `merged/m1.json`.

| map | K per channel | M1 (gap-width / strict) | districts in window | split states (channel-state splits; distinct states) | worst $ position (0 = L, 1 = U) | heuristic-placed ZCTAs | maps |
|---|---|---|---|---|---|---|---|
| **ne-48-bal** | FI 21, WH 10, WIFI 3, national 14 = 48 | pass / pass. 0 districts in pieces, 0 necks | FI 21/21, WH 10/10, WIFI 3/3, national 14/14 | 11; 8 states: CA FL NJ NY OH PA TN TX (FI: CA FL NY OH PA TN; WH: CA NJ; national: CA NY TX; WIFI none) | FI 1.00, WH 0.02, WIFI 0.29, national 0.00 | FI 3,659 (PA group DC+PA+VA+WV, DE+MD+PA, NJ+PA, PA) | [summary](maps/MAIN_ne-48-bal_summary.png), [pages](maps/MAIN_ne-48-bal_pages.pdf), [FI](maps/MAIN_ne-48-bal_FI.png), [WH](maps/MAIN_ne-48-bal_WH.png), [WIFI](maps/MAIN_ne-48-bal_WIFI.png), [national](maps/MAIN_ne-48-bal_national.png) |
| **ne-50-filight** | FI 20, WH 11, WIFI 3, national 16 = 50 | pass / **fail** (strict: 2 necks, national_15 NY 5.99 km wide and national_16 79734 6.14 km wide; no pieces) | FI 20/20, WH 11/11, WIFI 3/3, national 16/16 | 15; 9 states: CA FL IL NJ NY OH PA TN TX (FI: CA FL NY OH PA TN; WH: CA NJ PA; national: CA FL IL NY PA TX; WIFI none) | FI 1.00, WH 0.02, WIFI 0.29, national 0.01 | FI 1,826 + national 1,803 = 3,629 (groups not recorded) | [summary](maps/MAIN_ne-50-filight_summary.png), [pages](maps/MAIN_ne-50-filight_pages.pdf), [FI](maps/MAIN_ne-50-filight_FI.png), [WH](maps/MAIN_ne-50-filight_WH.png), [WIFI](maps/MAIN_ne-50-filight_WIFI.png), [national](maps/MAIN_ne-50-filight_national.png) |
| **ne-cmp-tierP** | FI 20, WH 11, WIFI 3, national 15 = 49 | pass / pass. 0 districts in pieces, 0 necks | FI 20/20, WH 11/11, WIFI 3/3, national 15/15 | 13; 8 states: CA FL NJ NY OH PA TN TX (FI: CA FL NY OH PA TN; WH: CA NJ PA; national: CA FL NY TX; WIFI none) | FI 1.00, WH 0.02, WIFI 0.29, national 0.01 | FI 1,826 + national 3,792 = 5,618 (groups not recorded) | [summary](maps/MAIN_ne-cmp-tierP_summary.png), [pages](maps/MAIN_ne-cmp-tierP_pages.pdf), [FI](maps/MAIN_ne-cmp-tierP_FI.png), [WH](maps/MAIN_ne-cmp-tierP_WH.png), [WIFI](maps/MAIN_ne-cmp-tierP_WIFI.png), [national](maps/MAIN_ne-cmp-tierP_national.png) |

Notes on the three
- "FI 1.00" means the highest FI district sits at the top of its window ($1,034.6M of 1,035M). WIFI's three districts use the whole-state allowance (WIFI_03 $1,230.7M).
- m2 (`warm_m2/`): no complete map passes (final, 21:03 CDT); see section 4.
- Source folders: `warm/<point>/merged` (ledger and gate), `warm/<point>/warm.json`, `warm/INDEX.md` (heuristic groups and the older shape numbers).

### Earlier passing maps (for comparison)

Not part of today's unsealed grid. Same window; M1 under the water and empty-land rule.

| map | K | M1 | in window | split states | worst $ position | heuristic-placed | maps |
|---|---|---|---|---|---|---|---|
| last night's unsealed ne-48-bal (`../sealed_2026-10-14/main_unsealed/ne-48-bal-r2`) | FI 21, WH 10, WIFI 3, national 14 = 48 | pass / pass (gap-width and strict both 0 pieces, 0 necks) | 48/48 | 12 channel-state splits; 8 states: CA FL NC NJ NY OH PA TX (FI: CA FL NC NY OH PA; WH: CA NJ; national: CA FL NY TX) | FI 0.06, WH 0.93, WIFI 0.29, national 0.94 | 0 (every channel `tier: exact`, status optimal in its `run.json`) | [summary](../sealed_2026-10-14/main_unsealed/ne-48-bal-r2/zip_summary.png), [pages](../sealed_2026-10-14/main_unsealed/ne-48-bal-r2/zip_pages.pdf), [FI](../sealed_2026-10-14/main_unsealed/ne-48-bal-r2/zip_FI.png), [WH](../sealed_2026-10-14/main_unsealed/ne-48-bal-r2/zip_WH.png), [WIFI](../sealed_2026-10-14/main_unsealed/ne-48-bal-r2/zip_WIFI.png), [national](../sealed_2026-10-14/main_unsealed/ne-48-bal-r2/zip_national.png) |
| IFA K48 | IFA 48 | Manhattan only (IFA_12 neck, the one allowed exception) | 48/48 | 21: AZ CA CT FL IL IN KS MA MD MI MN NC NJ NV NY OH PA TN TX VA WI | $1,436.9M max in $1,000-1,437.5M = 1.00 | not recorded in IFA_INDEX | [summary](../sealed_2026-10-14/maps/IFA_K48_summary.png), [pages](../sealed_2026-10-14/maps/IFA_K48_pages.pdf), [IFA](../sealed_2026-10-14/maps/IFA_K48_IFA.png) |
| IFA K49 | IFA 49 | Manhattan only (IFA_09) | 49/49 | 21: same list as K48 | 1.00 (IFA_41 $1,436.9M) | not recorded | [summary](../sealed_2026-10-14/maps/IFA_K49_summary.png), [pages](../sealed_2026-10-14/maps/IFA_K49_pages.pdf), [IFA](../sealed_2026-10-14/maps/IFA_K49_IFA.png) |
| IFA K50 | IFA 50 | Manhattan only (IFA_09) | 50/50 | 21: same list as K48 | 1.00 (IFA_42 $1,436.9M) | not recorded | [summary](../sealed_2026-10-14/maps/IFA_K50_summary.png), [pages](../sealed_2026-10-14/maps/IFA_K50_pages.pdf), [IFA](../sealed_2026-10-14/maps/IFA_K50_IFA.png) |
| IFA K51 | IFA 51 | Manhattan only (IFA_09) | 51/51 | 19: CA CT FL IL IN KS MA MD MI MN NC NJ NY OH PA TN TX VA WI | 1.00 (IFA_42 $1,436.9M) | not recorded | [summary](../sealed_2026-10-14/maps/IFA_K51_summary.png), [pages](../sealed_2026-10-14/maps/IFA_K51_pages.pdf), [IFA](../sealed_2026-10-14/maps/IFA_K51_IFA.png) |
| IFA K52 | IFA 52 | Manhattan only (IFA_09) | 52/52 | 18: CA CT FL IL KS MA MD MI MN NC NJ NY OH PA TN TX VA WI | 1.00 (IFA_41 $1,436.9M) | not recorded | [summary](../sealed_2026-10-14/maps/IFA_K52_summary.png), [pages](../sealed_2026-10-14/maps/IFA_K52_pages.pdf), [IFA](../sealed_2026-10-14/maps/IFA_K52_IFA.png) |
| IFA K53 | IFA 53 | Manhattan only (IFA_09) | 53/53 | 18: same list as K52 | 1.00 (IFA_42 $1,436.9M) | not recorded | [summary](../sealed_2026-10-14/maps/IFA_K53_summary.png), [pages](../sealed_2026-10-14/maps/IFA_K53_pages.pdf), [IFA](../sealed_2026-10-14/maps/IFA_K53_IFA.png) |
| IFA K54 | IFA 54 | Manhattan only (IFA_09) | 54/54 | 21: AZ CA CT FL IL KS MA MD MI MN NC NJ NV NY OH OR PA TN TX VA WI | 1.00 (IFA_42 $1,436.9M) | not recorded | [summary](../sealed_2026-10-14/maps/IFA_K54_summary.png), [pages](../sealed_2026-10-14/maps/IFA_K54_pages.pdf), [IFA](../sealed_2026-10-14/maps/IFA_K54_IFA.png) |

The IFA maps are one channel with one dollar window; their position is the single worst district, from `IFA_INDEX.md`. The candidates above use the full-extract dollar scoring of `warm.py`; the IFA and last-night figures come from their own indexes.

## 3. Shape (eye review only, not a gate)

`tools/looks/study.py` from `m5-studio/study-v2` (168d51f: land-only `hull_fill` and `bite`, `arm_share`, `roughness`), run on each candidate's merged ledger plus last night's ne-48-bal. Files: [`shape/districts.csv`](shape/districts.csv) (every district, all measures) and [`shape/FLAGS.md`](shape/FLAGS.md).

| map | max bite | min hull_fill | max cut_edges | flagged (`cut_edges >= 126 AND bite >= 0.18`) |
|---|---|---|---|---|
| ne-48-bal | 0.409 (FI_14) | 0.437 (national_13) | 247 (FI_20) | 2: FI_07 (DE MD PA), FI_06 (DC PA VA WV) |
| ne-50-filight | 0.335 (national_15) | 0.542 (national_04) | 243 (national_09) | 4: national_09 (DE NY PA), national_04 (CA), FI_18 (OH PA WV), national_08 (DC MD OH PA WV) |
| ne-cmp-tierP | 0.305 (FI_12) | 0.542 (national_04) | 197 (national_04) | 2: national_04 (CA), FI_18 (OH PA WV) |
| last night's ne-48-bal | 0.456 (national_11) | 0.522 (national_11) | 283 (FI_19) | 2: FI_18 (OH PA WV), FI_06 (DC DE MD PA) |

Heuristic-placed areas may look rougher than exactly drawn ones. In ne-48-bal the two flagged FI districts (FI_06, FI_07) are two of the four districts of the heuristic-placed PA group (DC+PA+VA+WV, DE+MD+PA); for the other two candidates the heuristic groups were not recorded, so no such link is claimed. The flags only say where to look on the page; they fail nothing. FI_18 (OH PA WV) is also flagged on last night's fully exact map, so that pattern is not specific to the heuristic.

## 4. Failures (every other point)

First attempt (`main/`, m5 and m2) and the long retries (`main_r2`, `main_r2b`, `main_r2c`, `main_nw49`, m2 `main_r2`) are summarised in the reason column; the warm start (`warm/` on m5, `warm_m2/` on m2) is the last stage reached. `main_r2/SEALED.json` on m5 still reads "running": the driver was stopped by hand at 16:26 CDT with 5 draws stuck 4-5 h in exact solves.

| point | decisive reason | where |
|---|---|---|
| ne-50-bal | **Fails M1 after the warm start: FI_19 (NY) in 4 pieces** (104, 29, 3 and 1 ZIPs; largest 0.263 τ); 3 of 22 FI districts outside the window. Exact repair windows on NY ended "unknown" at their time limit (r1, r2, r3 at 1,500 s). First draw: the FL group (AL+FL, FL, FL+GA) did not finish. 7,708 FI + 3,792 national ZCTAs heuristic-placed. | `warm/ne-50-bal`, `main/SEALED.json` |
| ne-52-filight | **Fails M1: same FI_19 NY pieces** (the NY group is identical to ne-50-bal); 3 of 22 FI districts outside the window. 6,695 FI + 1,803 national ZCTAs heuristic-placed. | `warm/ne-52-filight` |
| ne-52-bal | **Fails M1: FI_18 (NY, 21 ZIPs, 0.061 τ) and FI_07 (NJ, 7 ZIPs, 0.0006 τ) detached**; FI 17/23 in window. Repair r1, r2 and an r3 with NY/NJ opened ended infeasible or unknown. First draw: the TN group (AR+MO+TN, KY+TN) did not finish. 13,901 FI + 3,792 national ZCTAs heuristic-placed. | `warm/ne-52-bal` |
| nw49-48 | **Fails M1: WIFI_27 (NY) has a detached 9-ZIP piece, 0.085 τ**; 1 WIFI district under the window (min $848.7M); 13,772 WIFI + 3,792 national ZCTAs heuristic-placed. The Mid-Atlantic group (DC+MD+DE+NJ+PA+WV, MD split) did not finish. A third repair pass with long windows was running at 19:50 CDT; result may change. | `warm_m2/nw49-48` |
| nw49-52 | **Fails M1: WIFI_29 (NY) has a detached 9-ZIP piece, 0.090 τ**; 1 WIFI and 2 national districts outside the window; 15,873 WIFI + 8,027 national ZCTAs heuristic-placed. Third repair pass running at 19:50 CDT. | `warm_m2/nw49-52` |
| nw49-50 | **Fails M1 (final, 21:03 CDT).** Repair ended with M1 failing: 4 districts in pieces, 7 detached pieces, largest 0.338 τ. First draw: the same Mid-Atlantic group did not finish (15,235 WIFI + 4,805 national ZCTAs heuristic-placed). | `warm_m2/nw49-50`, `main_nw49/SEALED.json` |
| nw34-48 | **No complete map: the national channel (K 14) was never drawn.** Its WIFI channel (K 34) passes M1 (0 pieces) but WIFI_30 ($834.1M) is under the $850M window; 14,890 WIFI ZCTAs heuristic-placed (Mid-Atlantic MD group, unknown at its time limit). National draw (`main/`): "run.py wrote no ledger: the constructed drawing breaks a row (band or targets)". | `warm_m2/nw34-48`, `main/SEALED.json` (m2) |
| nw34-50 | **No complete map: the national channel (K 15) was never drawn** (m2 `main/`: "run.py wrote no ledger: solve 1 (gap 0.05): Optimal, objective 2557.01, 3527.5s, 18455 rows"). Its WIFI channel (K 35) passes M1 and all 35 districts are in window; 15,528 WIFI ZCTAs heuristic-placed. | `warm_m2/nw34-50` |
| nw34-52 | **Running, no verdict.** The warm driver crashed twice (gate rc 1 on the first drawing: 5 WIFI districts in pieces, 7 detached pieces, largest 0.173 τ, WIFI_28 NJ+PA 126 ZIPs); repair pass 1 was restarted at 19:44 CDT. National channel: "no constructed drawing: no move helps DC+MD+OH+PA#1 (691.611 against [1000, 1437.5])". | `warm_m2/nw34-52`, `main/SEALED.json` (m2) |
| w1-48 | **Drawing did not finish by the stop.** m2 `main`: draw killed at its 100-minute cap; m5 `main_r2c`: the 5.6 h stop hit during `rest.draw`. No warm-start run exists. | `main/` (m2), `main_r2c/` |
| w1-50 | **No drawing.** m2 `main`: "the constructed drawing breaks a row (band or targets)"; m5 `main_r2c`: not started before the 5.6 h stop. No warm-start run. | `main/` (m2), `main_r2c/` |
| w1-52 | **No drawing.** m2 `main`: "no constructed drawing: no move helps DE+NJ#1 (605.948 against [850, 1150])"; m5 `main_r2c`: not started before the stop. No warm-start run. | `main/` (m2), `main_r2c/` |

Other history: ne-48-bal, ne-50-filight and ne-cmp-tierP also ended "no connected drawing" on their first attempt (the PA group for ne-48-bal; FI 1,826 + national 3,792 or 1,803 undrawn ZCTAs for the other two) and were rescued by the warm start. `main_r2b/ne-cmp-tierP` stopped at the 6.9 h stop during `rest-FI-WH-national.draw`. m2 `main_r2` (draw cap 36,000 s) ended all nine points `stopped` at the 7.2 h stop (the nw34 ones during `rest-WIFI.draw`, nw49-48/50 during `rest.draw`, nw49-52 and w1 not started).

## 5. Caveats

- Dollar scoring: `sealed.py`'s score stage reads rates from the merged extract (CONUS cells only), which overstates FI by about 2% when a merged folder is scored that way (FI_04 1,054.1M there vs 1,030.8M in the ledger). `warm.py` scores with the full extract; every number in this index comes from the full extract. Any figure taken from sealed.py's own score stage on a merged folder (for example the "outside band" line in `warm/ne-48-bal/point.log`) is the 2% high one.
- M1 rule R5 (missing-land glue) is inactive in these gates ("R5 inactive" in each gate line). Manhattan is the only allowed M1 exception (owner, 2026-10-14); none of the three candidates needs it, the IFA maps do.
- ne-50-filight passes the gap-width M1 gate but fails the strict rule (2 necks, no pieces). It is a candidate under the owner-approved rule that the final exact gate decides.
- Passing maps contain heuristic-placed ZCTAs (3,629 to 5,618): gate-verified, not drawn by the exact solver, so they may look rougher. The label for any of them is "passes (gate-verified; N ZCTAs placed by the realizer heuristic, not the exact draw)" (supervisor ruling 2026-10-14, `STATUS.md` 17:58 CDT).
- The shape flags are an eye-review list only. `shape/` uses the study-v2 (land-only) definitions; the `shape` lines in `warm/INDEX.md` come from the earlier study.py and differ slightly (ne-48-bal FI max bite 0.4083 there, 0.409 here).
- m2 work finished at 21:03 CDT; all m2 rows are final.
- Masking: district dollars are shown; no per-rep shares, sales or rep/firm names are used.
