# Scorecard: nw34-48-wide (contig arm1, instance_descaled_usd.json.gz)

**Verdict: fail**

| check | status | summary |
|---|---|---|
| one owner per cell | pass | 166500 cells, 0 with other than one owner, 0 not placed with no opportunity |
| district count per channel | pass | 2 channels, 0 off K |
| dropped for zero opportunity | pass | no cells dropped |
| final bands on drawn mass | pass | 48 districts, 0 outside the final tolerance |
| phantom shares | pass | 105 reported shares compared with the ledger, 0 not backed |
| planned against drawn owners | listed | 2 listed |
| mode compliance | pass | 0 violations, 0 metro exceptions, 0 units with zero-opportunity ZCTAs owned across them |
| ZIP contiguity | listed | 3 districts in pieces, 6 pieces, 0 ZIPs not in the graph |
| M1 polygon contiguity | fail | 3 districts in pieces, 6 detached pieces (largest 0.375 τ), 6 necks, 0 channel ZCTAs with no owner, 0 (ZCTA, fine channel) cells with no row, 0 owned twice, 15 mass necks listed beside M1 |
| geography manifest is 2025 | pass | 18 sources, all 2025 |
| solver status, bound and gap | listed | 2 channels |
| certificate tier | pass | weakest tier: exact |
| one name per district | pass | 48 districts |
| rep labels | pass | blank, as OD3 (#58) decides |

## planned against drawn owners

- WIFI/AL/WIFI_01: planned share 0.548637 drawn as no ZIPs (C8)
- WIFI/MD/WIFI_22: planned share 0.05 drawn as no ZIPs (C8)

## ZIP contiguity

- WIFI/WIFI_10: piece of 119 ZIPs, 0.378 of the district's mass, cause shape
- WIFI/WIFI_10: piece of 2 ZIPs, 0.0127 of the district's mass, cause shape
- WIFI/WIFI_12: piece of 56 ZIPs, 0.0159 of the district's mass, cause shape
- WIFI/WIFI_29: piece of 7 ZIPs, 0.00709 of the district's mass, cause shape
- WIFI/WIFI_29: piece of 7 ZIPs, 0.00176 of the district's mass, cause shape
- WIFI/WIFI_29: piece of 8 ZIPs, 0.000105 of the district's mass, cause shape

## M1 polygon contiguity

- WIFI/WIFI_10: detached piece of 119 ZIPs (06390...), 0.375 τ, cause shape
- WIFI/WIFI_10: detached piece of 2 ZIPs (06479...), 0.0126 τ, cause shape
- WIFI/WIFI_12: detached piece of 56 ZIPs (18013...), 0.0144 τ, cause shape
- WIFI/WIFI_29: detached piece of 7 ZIPs (10471...), 0.00709 τ, cause shape
- WIFI/WIFI_29: detached piece of 7 ZIPs (10510...), 0.00176 τ, cause shape
- WIFI/WIFI_29: detached piece of 8 ZIPs (10501...), 0.000105 τ, cause shape
- WIFI/WIFI_10: neck 5.26 km wide cuts off 11 ZIPs (06405...), 5.3% of its land area and 9.7% of its mass; cut 06516-06519 5.26 km
- WIFI/WIFI_10: neck 1.27 km wide cuts off 118 ZIPs (06390...), 29.0% of its land area and 37.8% of its mass; cut 11901-11947 0.92 km, 11947-11970 0.35 km
- WIFI/WIFI_12: neck 5.67 km wide cuts off 69 ZIPs (08023...), 29.0% of its land area and 20.8% of its mass; cut 08023-08069 3.34 km, 08023-08070 2.33 km
- WIFI/WIFI_12: neck 0.05 km wide cuts off 55 ZIPs (18013...), 19.0% of its land area and 1.6% of its mass; cut 18405-18415 0.05 km
- WIFI/WIFI_13: neck 3.01 km wide cuts off 4 ZIPs (33430...), 19.8% of its land area and 0.0% of its mass; cut 33430-33470 3.01 km
- national/national_06: neck 0.80 km wide cuts off 167 ZIPs (90001...), 23.3% of its land area and 47.5% of its mass; cut 90040-90240 0.80 km
- WIFI/WIFI_01: mass neck (diagnostic, not M1) 8.47 km wide cuts off 1 ZIPs (30326...), 0.0% of its land area and 8.9% of its mass; cut 30305-30326 3.40 km, 30319-30326 1.50 km, 30324-30326 1.11 km, 30326-30342 2.46 km
- WIFI/WIFI_02: mass neck (diagnostic, not M1) 9.96 km wide cuts off 2 ZIPs (70112...), 0.0% of its land area and 5.0% of its mass; cut 70112-70113 3.44 km, 70112-70116 2.48 km, 70112-70119 2.36 km, 70112-70130 1.35 km, 70113-70163 0.33 km
- WIFI/WIFI_06: mass neck (diagnostic, not M1) 9.82 km wide cuts off 2 ZIPs (94104...), 0.0% of its land area and 6.0% of its mass; cut 94104-94105 0.52 km, 94104-94108 0.66 km, 94105-94111 6.60 km, 94108-94111 0.36 km, 94111-94133 1.67 km
- WIFI/WIFI_10: mass neck (diagnostic, not M1) 5.26 km wide cuts off 11 ZIPs (06405...), 5.3% of its land area and 9.7% of its mass; cut 06516-06519 5.26 km
- WIFI/WIFI_10: mass neck (diagnostic, not M1) 1.27 km wide cuts off 118 ZIPs (06390...), 29.0% of its land area and 37.8% of its mass; cut 11901-11947 0.92 km, 11947-11970 0.35 km
- WIFI/WIFI_11: mass neck (diagnostic, not M1) 5.73 km wide cuts off 4 ZIPs (20006...), 0.0% of its land area and 19.7% of its mass; cut 20005-20006 0.60 km, 20006-20024 0.34 km, 20006-20036 1.28 km, 20006-20037 0.68 km, 20006-20052 0.80 km, 20006-20220 0.37 km, ...
- WIFI/WIFI_12: mass neck (diagnostic, not M1) 5.67 km wide cuts off 69 ZIPs (08023...), 29.0% of its land area and 20.8% of its mass; cut 08023-08069 3.34 km, 08023-08070 2.33 km
- WIFI/WIFI_13: mass neck (diagnostic, not M1) 3.27 km wide cuts off 2 ZIPs (34103...), 0.2% of its land area and 9.5% of its mass; cut 34102-34103 3.27 km
- WIFI/WIFI_18: mass neck (diagnostic, not M1) 5.10 km wide cuts off 1 ZIPs (60606...), 0.0% of its land area and 13.5% of its mass; cut 60601-60606 0.28 km, 60602-60606 0.28 km, 60603-60606 0.29 km, 60604-60606 0.28 km, 60606-60607 1.29 km, 60606-60654 1.00 km, ...
- WIFI/WIFI_28: mass neck (diagnostic, not M1) 3.94 km wide cuts off 11 ZIPs (10017...), 0.1% of its land area and 11.7% of its mass; cut 10016-10017 1.60 km, 10017-10018 0.16 km, 10017-10020 0.08 km, 10017-10022 1.45 km, 10017-10036 0.32 km, 10017-10110 0.09 km, ...
- national/national_04: mass neck (diagnostic, not M1) 4.30 km wide cuts off 10 ZIPs (95608...), 1.1% of its land area and 5.8% of its mass; cut 95826-95828 4.30 km
- national/national_05: mass neck (diagnostic, not M1) 0.27 km wide cuts off 95 ZIPs (90003...), 3.8% of its land area and 36.0% of its mass; cut 92701-92780 0.27 km
- national/national_06: mass neck (diagnostic, not M1) 0.80 km wide cuts off 167 ZIPs (90001...), 23.3% of its land area and 47.5% of its mass; cut 90040-90240 0.80 km
- national/national_12: mass neck (diagnostic, not M1) 1.85 km wide cuts off 8 ZIPs (10017...), 0.0% of its land area and 13.1% of its mass; cut 10016-10017 1.60 km, 10017-10018 0.16 km, 10017-10110 0.09 km
- national/national_13: mass neck (diagnostic, not M1) 7.42 km wide cuts off 11 ZIPs (10019...), 0.0% of its land area and 5.3% of its mass; cut 10019-10022 0.57 km, 10019-10065 0.52 km, 10021-10023 0.58 km, 10022-10103 0.08 km, 10022-10111 0.08 km, 10022-10112 0.08 km, ...

## solver status, bound and gap

- WIFI: status optimal, objective 7559.738524677037, bound 7559.738524677037, gap 0, tier exact
- national: status optimal, objective 5647.077611908053, bound 5647.077611908053, gap 0, tier exact

## certificate tier

- WIFI: exact
- national: exact
