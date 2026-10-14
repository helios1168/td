# G1 prototype: neck width across ZCTA coverage gaps (2026-10-08)

Owner decision G1 (2026-10-08, "Measure width across coverage gaps"), prototyped behind
`audit.NeckGraph(polygon, gap_width=True)` (default off; `check_m1` reads `TD_NECK_GAP_WIDTH=1`).
With the flag on, every same-state pair of ZCTAs adjacent in the Voronoi ZIP graph but neither a
polygon edge nor an approved connector (`reference/2025/zcta_polygon_vs_voronoi.csv.gz`,
`change = dropped`) becomes a neck edge as wide as its shared Voronoi border (`border_m`).

**No land test.** `geo` removes perennial water per (ZCTA, county) piece at build time (TIGER
FACES with LWFLAG P, `td/geo.py` `_county_water`, lines 388-411) and proposes connectors along
roads whose stretch outside every ZCTA it calls "land in no ZCTA" (`road_crossings`, `TOUCH_M`,
line 662); neither ships a reusable land-versus-water test of a gap. The flag therefore uses
same-state Voronoi adjacency only, and a gap across water (Great Lakes shoreline, Long Island
Sound, bays) also counts. No verdict below changed except TX's, whose gap edges are all West
Texas desert, so no water crossing changed a verdict here.

Method: `audit.district_necks` on each district of the IFA channel of each run's `ledger.csv`,
mass `m_rel`, on `geo.polygon_graph()`, flag off and on. Run folders were not rewritten.

| run | districts | necks, flag off | necks, flag on | verdict |
|---|---|---|---|---|
| ifa_tx_k3 | 3 | 1 (IFA_02: 44 ZIPs from 79734, 6.86% land, 6.93% mass, cut 79718-79734 6.14 km) | 0 | fail -> pass (necks) |
| ifa_ctri_k2 | 2 | 0 | 0 | pass, stays pass |
| ifa_il_k2 | 2 | 0 | 0 | pass, stays pass |
| ifa_oh_k2 | 2 | 0 | 0 | pass, stays pass |
| ifa_fl_k4-neck | 4 | 0 | 0 | pass, stays pass |
| ifa_ca_k4-neck | 4 | 0 | 0 | pass, stays pass |
| ifa_ca_k5-neck | 5 | 0 | 0 | pass, stays pass |
| ifa_pa_k4t-neck | 4 | 0 | 0 | pass, stays pass |
| ifa_nj_k3-neck | 3 | 0 | 0 | pass, stays pass |

Verdict changes other than TX IFA_02: none. Every other district of these nine runs has no neck
with the flag off and none with it on. (G1 is issue #131; its full `--rescore` is the complete list.)

## TX K3, IFA_02 under the flag

`district_necks` proves no part holding 5% of the land reaches the rest through under 10 km. The
old neck's side (the 44 ZIPs of El Paso and the Trans-Pecos) now has a cut of 350.17 km: the
polygon edge 79718-79734 (6.14 km) plus eleven gap edges, all TX-TX:

| a | b | km |
|---|---|---|
| 79734 | 79785 | 17.379 |
| 79830 | 79842 | 64.383 |
| 79832 | 79718 | 14.785 |
| 79832 | 79735 | 34.987 |
| 79832 | 79780 | 9.908 |
| 79832 | 79842 | 13.765 |
| 79834 | 79842 | 40.597 |
| 79847 | 79770 | 43.799 |
| 79847 | 79785 | 18.296 |
| 79852 | 79842 | 31.747 |
| 79855 | 79785 | 54.390 |

Another 23 gap edges join ZCTAs inside that side. The narrowest cut of IFA_02 above 10 km was not
computed: `district_necks` decides only whether one under 10 km exists.
