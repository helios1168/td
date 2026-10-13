# Scorecard: nw34-50-wide (contig arm1, instance_descaled_usd.json.gz)

**Verdict: fail**

| check | status | summary |
|---|---|---|
| one owner per cell | pass | 166500 cells, 0 with other than one owner, 0 not placed with no opportunity |
| district count per channel | pass | 2 channels, 0 off K |
| dropped for zero opportunity | pass | no cells dropped |
| final bands on drawn mass | pass | 50 districts, 0 outside the final tolerance |
| phantom shares | pass | 110 reported shares compared with the ledger, 0 not backed |
| planned against drawn owners | listed | 2 listed |
| mode compliance | pass | 0 violations, 0 metro exceptions, 0 units with zero-opportunity ZCTAs owned across them |
| ZIP contiguity | listed | 3 districts in pieces, 6 pieces, 0 ZIPs not in the graph |
| M1 polygon contiguity | fail | 3 districts in pieces, 6 detached pieces (largest 0.498 τ), 9 necks, 0 channel ZCTAs with no owner, 0 (ZCTA, fine channel) cells with no row, 0 owned twice, 18 mass necks listed beside M1 |
| geography manifest is 2025 | pass | 18 sources, all 2025 |
| solver status, bound and gap | listed | 2 channels |
| certificate tier | pass | weakest tier: exact |
| one name per district | pass | 50 districts |
| rep labels | pass | blank, as OD3 (#58) decides |

## planned against drawn owners

- WIFI/IL/WIFI_16: planned share 0.0694965 drawn as no ZIPs (C8)
- WIFI/TN/WIFI_19: planned share 0.05 drawn as no ZIPs (C8)

## ZIP contiguity

- WIFI/WIFI_10: piece of 125 ZIPs, 0.402 of the district's mass, cause shape
- WIFI/WIFI_30: piece of 8 ZIPs, 0.0131 of the district's mass, cause shape
- WIFI/WIFI_30: piece of 9 ZIPs, 0.00812 of the district's mass, cause shape
- WIFI/WIFI_30: piece of 10 ZIPs, 0.00118 of the district's mass, cause shape
- WIFI/WIFI_30: piece of 2 ZIPs, 0.000591 of the district's mass, cause shape
- national/national_13: piece of 179 ZIPs, 0.47 of the district's mass, cause attachment

## M1 polygon contiguity

- WIFI/WIFI_10: detached piece of 125 ZIPs (06390...), 0.423 τ, cause shape
- WIFI/WIFI_30: detached piece of 8 ZIPs (10471...), 0.0137 τ, cause shape
- WIFI/WIFI_30: detached piece of 9 ZIPs (10510...), 0.00853 τ, cause shape
- WIFI/WIFI_30: detached piece of 10 ZIPs (10501...), 0.00124 τ, cause shape
- WIFI/WIFI_30: detached piece of 2 ZIPs (10535...), 0.000621 τ, cause shape
- national/national_13: detached piece of 179 ZIPs (10002...), 0.498 τ, cause attachment
- WIFI/WIFI_10: neck 2.80 km wide cuts off 11 ZIPs (06405...), 5.3% of its land area and 8.0% of its mass; cut 06460-06516 2.80 km
- WIFI/WIFI_10: neck 1.27 km wide cuts off 124 ZIPs (06390...), 34.7% of its land area and 40.2% of its mass; cut 11901-11947 0.92 km, 11947-11970 0.35 km
- WIFI/WIFI_12: neck 5.67 km wide cuts off 150 ZIPs (08001...), 26.7% of its land area and 38.2% of its mass; cut 08023-08069 3.34 km, 08023-08070 2.33 km
- WIFI/WIFI_13: neck 3.01 km wide cuts off 4 ZIPs (33430...), 19.8% of its land area and 0.0% of its mass; cut 33430-33470 3.01 km
- WIFI/WIFI_29: neck 0.46 km wide cuts off 144 ZIPs (10001...), 42.8% of its land area and 69.1% of its mass; cut 11239-11414 0.46 km
- national/national_04: neck 8.81 km wide cuts off 5 ZIPs (93527...), 5.7% of its land area and 0.0% of its mass; cut 93527-93554 8.81 km
- national/national_05: neck 8.12 km wide cuts off 4 ZIPs (92328...), 9.2% of its land area and 0.0% of its mass; cut 92384-92389 8.12 km
- national/national_09: neck 5.67 km wide cuts off 470 ZIPs (07001...), 31.1% of its land area and 76.9% of its mass; cut 08023-08069 3.34 km, 08023-08070 2.33 km
- national/national_15: neck 6.14 km wide cuts off 44 ZIPs (79734...), 6.7% of its land area and 3.3% of its mass; cut 79718-79734 6.14 km
- WIFI/WIFI_01: mass neck (diagnostic, not M1) 8.47 km wide cuts off 1 ZIPs (30326...), 0.0% of its land area and 6.4% of its mass; cut 30305-30326 3.40 km, 30319-30326 1.50 km, 30324-30326 1.11 km, 30326-30342 2.46 km
- WIFI/WIFI_02: mass neck (diagnostic, not M1) 0.40 km wide cuts off 1 ZIPs (70163...), 0.0% of its land area and 6.7% of its mass; cut 70112-70163 0.07 km, 70113-70163 0.33 km
- WIFI/WIFI_06: mass neck (diagnostic, not M1) 9.82 km wide cuts off 2 ZIPs (94104...), 0.0% of its land area and 6.0% of its mass; cut 94104-94105 0.52 km, 94104-94108 0.66 km, 94105-94111 6.60 km, 94108-94111 0.36 km, 94111-94133 1.67 km
- WIFI/WIFI_10: mass neck (diagnostic, not M1) 0.66 km wide cuts off 36 ZIPs (10461...), 2.1% of its land area and 6.9% of its mass; cut 10464-10475 0.27 km, 10475-10803 0.39 km
- WIFI/WIFI_10: mass neck (diagnostic, not M1) 1.27 km wide cuts off 124 ZIPs (06390...), 34.7% of its land area and 40.2% of its mass; cut 11901-11947 0.92 km, 11947-11970 0.35 km
- WIFI/WIFI_11: mass neck (diagnostic, not M1) 5.73 km wide cuts off 4 ZIPs (20006...), 0.0% of its land area and 20.8% of its mass; cut 20005-20006 0.60 km, 20006-20024 0.34 km, 20006-20036 1.28 km, 20006-20037 0.68 km, 20006-20052 0.80 km, 20006-20220 0.37 km, ...
- WIFI/WIFI_12: mass neck (diagnostic, not M1) 5.67 km wide cuts off 150 ZIPs (08001...), 26.7% of its land area and 38.2% of its mass; cut 08023-08069 3.34 km, 08023-08070 2.33 km
- WIFI/WIFI_13: mass neck (diagnostic, not M1) 3.27 km wide cuts off 2 ZIPs (34103...), 0.2% of its land area and 9.5% of its mass; cut 34102-34103 3.27 km
- WIFI/WIFI_18: mass neck (diagnostic, not M1) 5.10 km wide cuts off 1 ZIPs (60606...), 0.0% of its land area and 13.5% of its mass; cut 60601-60606 0.28 km, 60602-60606 0.28 km, 60603-60606 0.29 km, 60604-60606 0.28 km, 60606-60607 1.29 km, 60606-60654 1.00 km, ...
- WIFI/WIFI_20: mass neck (diagnostic, not M1) 8.46 km wide cuts off 6 ZIPs (43002...), 0.3% of its land area and 13.3% of its mass; cut 43026-43119 5.29 km, 43026-43162 3.16 km
- WIFI/WIFI_29: mass neck (diagnostic, not M1) 0.46 km wide cuts off 81 ZIPs (11001...), 57.2% of its land area and 30.9% of its mass; cut 11239-11414 0.46 km
- WIFI/WIFI_33: mass neck (diagnostic, not M1) 7.17 km wide cuts off 1 ZIPs (19103...), 0.0% of its land area and 8.5% of its mass; cut 19102-19103 2.23 km, 19103-19104 1.26 km, 19103-19130 1.54 km, 19103-19146 2.14 km
- national/national_06: mass neck (diagnostic, not M1) 6.84 km wide cuts off 6 ZIPs (91101...), 0.9% of its land area and 7.0% of its mass; cut 91030-91105 2.31 km, 91030-91106 0.93 km, 91030-91108 1.78 km, 91108-91801 1.82 km
- national/national_09: mass neck (diagnostic, not M1) 5.67 km wide cuts off 546 ZIPs (08023...), 68.9% of its land area and 23.1% of its mass; cut 08023-08069 3.34 km, 08023-08070 2.33 km
- national/national_10: mass neck (diagnostic, not M1) 3.21 km wide cuts off 165 ZIPs (33004...), 2.0% of its land area and 40.5% of its mass; cut 32963-34949 3.21 km
- national/national_12: mass neck (diagnostic, not M1) 5.46 km wide cuts off 7 ZIPs (60601...), 0.0% of its land area and 5.9% of its mass; cut 60601-60605 0.63 km, 60601-60606 0.28 km, 60602-60606 0.28 km, 60603-60605 0.59 km, 60603-60606 0.29 km, 60604-60605 0.86 km, ...
- national/national_13: mass neck (diagnostic, not M1) 0.35 km wide cuts off 178 ZIPs (10002...), 1.2% of its land area and 46.9% of its mass; cut 10005-10271 0.28 km, 10006-10271 0.06 km
- national/national_14: mass neck (diagnostic, not M1) 3.49 km wide cuts off 106 ZIPs (06390...), 1.8% of its land area and 22.6% of its mass; cut 11361-11362 0.90 km, 11361-11364 2.59 km

## solver status, bound and gap

- WIFI: status optimal, objective 7978.090701413706, bound 7978.090701413706, gap 0, tier exact
- national: status optimal, objective 7318.471382921802, bound 7318.471382921801, gap 1.24274e-16, tier exact

## certificate tier

- WIFI: exact
- national: exact
