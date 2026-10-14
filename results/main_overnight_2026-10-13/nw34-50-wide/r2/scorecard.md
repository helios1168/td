# Scorecard: nw34-50-wide (contig arm1+repair + window repair, nw34-50-wide, repair pass 2)

**Verdict: fail**

| check | status | summary |
|---|---|---|
| one owner per cell | pass | 166500 cells, 0 with other than one owner, 0 not placed with no opportunity |
| district count per channel | pass | 2 channels, 0 off K |
| dropped for zero opportunity | pass | no cells dropped |
| final bands on drawn mass | fail | 50 districts, 8 outside the final tolerance |
| phantom shares | pass | 110 reported shares compared with the ledger, 0 not backed |
| planned against drawn owners | listed | 5 listed |
| mode compliance | pass | 0 violations, 0 metro exceptions, 0 units with zero-opportunity ZCTAs owned across them |
| ZIP contiguity | pass | 0 districts in pieces, 0 pieces, 0 ZIPs not in the graph |
| M1 polygon contiguity | fail | 0 districts in pieces, 0 detached pieces (largest 0 τ), 3 necks, 0 channel ZCTAs with no owner, 0 (ZCTA, fine channel) cells with no row, 0 owned twice, 13 mass necks listed beside M1 |
| geography manifest is 2025 | pass | 18 sources, all 2025 |
| solver status, bound and gap | listed | 2 channels |
| certificate tier | pass | weakest tier: exact |
| one name per district | pass | 50 districts |
| rep labels | pass | blank, as OD3 (#58) decides |

## final bands on drawn mass

- WIFI/WIFI_02: drawn 1162.86 outside [700.627, 1128.69]
- WIFI/WIFI_25: drawn 674.441 outside [700.627, 1128.69]; undrawn share of NC
- national/national_01: drawn 1418.75 outside [1000, 1252.76]
- national/national_09: drawn 1293.14 outside [1000, 1252.76]
- national/national_10: drawn 809.401 outside [1000, 1252.76]; undrawn share of FL
- national/national_11: drawn 824.12 outside [1000, 1252.76]; undrawn share of IL
- national/national_12: drawn 1404.51 outside [1000, 1252.76]
- national/national_13: drawn 1276.18 outside [1000, 1252.76]; undrawn share of NJ

## planned against drawn owners

- WIFI/AL/WIFI_01: planned share 0.476248 drawn as no ZIPs (C8)
- WIFI/IL/WIFI_16: planned share 0.0694965 drawn as no ZIPs (C8)
- WIFI/TN/WIFI_19: planned share 0.05 drawn as no ZIPs (C8)
- national/IL/national_11: planned share 0.521778 drawn as no ZIPs (C8)
- national/NJ/national_13: planned share 0.0967811 drawn as no ZIPs (C8)

## M1 polygon contiguity

- WIFI/WIFI_12: neck 5.67 km wide cuts off 150 ZIPs (08001...), 26.7% of its land area and 38.2% of its mass; cut 08023-08069 3.34 km, 08023-08070 2.33 km
- national/national_09: neck 5.67 km wide cuts off 597 ZIPs (07001...), 38.7% of its land area and 78.6% of its mass; cut 08023-08069 3.34 km, 08023-08070 2.33 km
- national/national_14: neck 0.00 km wide cuts off 50 ZIPs (10901...), 45.8% of its land area and 6.1% of its mass; cut 12508-12550 0.00 km
- WIFI/WIFI_01: mass neck (diagnostic, not M1) 8.47 km wide cuts off 1 ZIPs (30326...), 0.0% of its land area and 8.9% of its mass; cut 30305-30326 3.40 km, 30319-30326 1.50 km, 30324-30326 1.11 km, 30326-30342 2.46 km
- WIFI/WIFI_02: mass neck (diagnostic, not M1) 9.96 km wide cuts off 2 ZIPs (70112...), 0.0% of its land area and 5.0% of its mass; cut 70112-70113 3.44 km, 70112-70116 2.48 km, 70112-70119 2.36 km, 70112-70130 1.35 km, 70113-70163 0.33 km
- WIFI/WIFI_06: mass neck (diagnostic, not M1) 9.82 km wide cuts off 2 ZIPs (94104...), 0.0% of its land area and 6.0% of its mass; cut 94104-94105 0.52 km, 94104-94108 0.66 km, 94105-94111 6.60 km, 94108-94111 0.36 km, 94111-94133 1.67 km
- WIFI/WIFI_10: mass neck (diagnostic, not M1) 3.94 km wide cuts off 11 ZIPs (10017...), 0.0% of its land area and 16.5% of its mass; cut 10016-10017 1.60 km, 10017-10018 0.16 km, 10017-10020 0.08 km, 10017-10022 1.45 km, 10017-10036 0.32 km, 10017-10110 0.09 km, ...
- WIFI/WIFI_11: mass neck (diagnostic, not M1) 5.73 km wide cuts off 4 ZIPs (20006...), 0.0% of its land area and 20.8% of its mass; cut 20005-20006 0.60 km, 20006-20024 0.34 km, 20006-20036 1.28 km, 20006-20037 0.68 km, 20006-20052 0.80 km, 20006-20220 0.37 km, ...
- WIFI/WIFI_12: mass neck (diagnostic, not M1) 5.67 km wide cuts off 150 ZIPs (08001...), 26.7% of its land area and 38.2% of its mass; cut 08023-08069 3.34 km, 08023-08070 2.33 km
- WIFI/WIFI_18: mass neck (diagnostic, not M1) 5.10 km wide cuts off 1 ZIPs (60606...), 0.0% of its land area and 13.5% of its mass; cut 60601-60606 0.28 km, 60602-60606 0.28 km, 60603-60606 0.29 km, 60604-60606 0.28 km, 60606-60607 1.29 km, 60606-60654 1.00 km, ...
- WIFI/WIFI_20: mass neck (diagnostic, not M1) 8.46 km wide cuts off 6 ZIPs (43002...), 0.3% of its land area and 13.3% of its mass; cut 43026-43119 5.29 km, 43026-43162 3.16 km
- WIFI/WIFI_33: mass neck (diagnostic, not M1) 7.17 km wide cuts off 1 ZIPs (19103...), 0.0% of its land area and 8.5% of its mass; cut 19102-19103 2.23 km, 19103-19104 1.26 km, 19103-19130 1.54 km, 19103-19146 2.14 km
- national/national_06: mass neck (diagnostic, not M1) 6.84 km wide cuts off 6 ZIPs (91101...), 0.9% of its land area and 7.0% of its mass; cut 91030-91105 2.31 km, 91030-91106 0.93 km, 91030-91108 1.78 km, 91108-91801 1.82 km
- national/national_09: mass neck (diagnostic, not M1) 5.67 km wide cuts off 546 ZIPs (08023...), 61.3% of its land area and 21.4% of its mass; cut 08023-08069 3.34 km, 08023-08070 2.33 km
- national/national_13: mass neck (diagnostic, not M1) 0.66 km wide cuts off 207 ZIPs (06390...), 1.4% of its land area and 41.2% of its mass; cut 10464-10475 0.27 km, 10475-10803 0.39 km
- national/national_14: mass neck (diagnostic, not M1) 0.00 km wide cuts off 50 ZIPs (10901...), 45.8% of its land area and 6.1% of its mass; cut 12508-12550 0.00 km

## solver status, bound and gap

- WIFI: status optimal, objective 7978.090701413706, bound 7978.090701413706, gap 0, tier exact
- national: status optimal, objective 7318.471382921802, bound 7318.471382921801, gap 1.24274e-16, tier exact

## certificate tier

- WIFI: exact
- national: exact

**Overnight grid label (main_overnight_2026-10-13):** fails M1 (M1 across coverage gaps: fail, 0 districts in pieces, 0 detached pieces (largest 0 τ), 2 necks, 0 channel ZCTAs with no owner, 0 (ZCTA, fine channel) cells with no row, 0 owned twice, 11 mass necks listed beside M1)
