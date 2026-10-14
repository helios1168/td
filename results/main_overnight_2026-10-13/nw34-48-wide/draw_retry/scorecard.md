# Scorecard: nw34-48-wide (contig arm1, instance_descaled_usd.json.gz)

**Verdict: fail**

| check | status | summary |
|---|---|---|
| one owner per cell | pass | 166500 cells, 0 with other than one owner, 0 not placed with no opportunity |
| district count per channel | pass | 2 channels, 0 off K |
| dropped for zero opportunity | pass | no cells dropped |
| final bands on drawn mass | fail | 48 districts, 7 outside the final tolerance |
| phantom shares | pass | 110 reported shares compared with the ledger, 0 not backed |
| planned against drawn owners | listed | 4 listed |
| mode compliance | pass | 0 violations, 0 metro exceptions, 0 units with zero-opportunity ZCTAs owned across them |
| ZIP contiguity | listed | 3 districts in pieces, 5 pieces, 0 ZIPs not in the graph |
| M1 polygon contiguity | fail | 3 districts in pieces, 5 detached pieces (largest 0.38 τ), 11 necks, 0 channel ZCTAs with no owner, 0 (ZCTA, fine channel) cells with no row, 0 owned twice, 16 mass necks listed beside M1 |
| geography manifest is 2025 | pass | 18 sources, all 2025 |
| solver status, bound and gap | listed | 2 channels |
| certificate tier | pass | weakest tier: exact |
| one name per district | pass | 48 districts |
| rep labels | pass | blank, as OD3 (#58) decides |

## final bands on drawn mass

- WIFI/WIFI_17: drawn 1199.88 outside [727.543, 1155.58]
- WIFI/WIFI_25: drawn 1169.14 outside [727.543, 1155.58]
- WIFI/WIFI_30: drawn 1195.9 outside [727.543, 1155.58]
- national/national_02: drawn 880.016 outside [1000.11, 1413.57]; undrawn share of TX
- national/national_08: drawn 1529.75 outside [1000.11, 1413.57]; undrawn share of NY
- national/national_12: drawn 992.707 outside [1000.11, 1413.57]; undrawn share of NJ
- national/national_13: drawn 1534.26 outside [1000.11, 1413.57]

## planned against drawn owners

- WIFI/IL/WIFI_15: planned share 0.154308 drawn as no ZIPs (C8)
- WIFI/IN/WIFI_19: planned share 0.253778 drawn as no ZIPs (C8)
- WIFI/NC/WIFI_26: planned share 0.100681 drawn as no ZIPs (C8)
- national/FL/national_01: planned share 0.116372 drawn as no ZIPs (C8)

## ZIP contiguity

- WIFI/WIFI_09: piece of 120 ZIPs, 0.382 of the district's mass, cause shape
- WIFI/WIFI_10: piece of 57 ZIPs, 0.339 of the district's mass, cause corridor
- WIFI/WIFI_29: piece of 7 ZIPs, 0.00709 of the district's mass, cause shape
- WIFI/WIFI_29: piece of 7 ZIPs, 0.00176 of the district's mass, cause shape
- WIFI/WIFI_29: piece of 8 ZIPs, 0.000105 of the district's mass, cause shape

## M1 polygon contiguity

- WIFI/WIFI_09: detached piece of 120 ZIPs (06390...), 0.38 τ, cause shape
- WIFI/WIFI_10: detached piece of 57 ZIPs (20001...), 0.32 τ, cause corridor
- WIFI/WIFI_29: detached piece of 7 ZIPs (10471...), 0.00709 τ, cause shape
- WIFI/WIFI_29: detached piece of 7 ZIPs (10510...), 0.00176 τ, cause shape
- WIFI/WIFI_29: detached piece of 8 ZIPs (10501...), 0.000105 τ, cause shape
- WIFI/WIFI_05: neck 5.96 km wide cuts off 236 ZIPs (93635...), 16.6% of its land area and 82.6% of its mass; cut 94115-94129 0.26 km, 94118-94129 2.82 km, 94121-94129 1.12 km, 94123-94129 1.77 km
- WIFI/WIFI_06: neck 9.39 km wide cuts off 29 ZIPs (93901...), 5.6% of its land area and 2.0% of its mass; cut 93452-93920 9.39 km
- WIFI/WIFI_09: neck 2.80 km wide cuts off 15 ZIPs (06405...), 8.0% of its land area and 9.7% of its mass; cut 06460-06516 2.80 km
- WIFI/WIFI_09: neck 1.27 km wide cuts off 119 ZIPs (06390...), 28.6% of its land area and 38.2% of its mass; cut 11901-11947 0.92 km, 11947-11970 0.35 km
- WIFI/WIFI_10: neck 5.67 km wide cuts off 150 ZIPs (08001...), 33.5% of its land area and 33.7% of its mass; cut 08023-08069 3.34 km, 08023-08070 2.33 km
- WIFI/WIFI_11: neck 3.01 km wide cuts off 4 ZIPs (33430...), 19.8% of its land area and 0.0% of its mass; cut 33430-33470 3.01 km
- WIFI/WIFI_19: neck 7.08 km wide cuts off 171 ZIPs (45001...), 8.7% of its land area and 40.5% of its mass; cut 41011-45202 0.00 km, 41017-45204 4.63 km, 41071-45202 0.00 km, 41074-45202 0.10 km, 41074-45226 2.36 km
- national/national_04: neck 8.81 km wide cuts off 5 ZIPs (93527...), 5.7% of its land area and 0.0% of its mass; cut 93527-93554 8.81 km
- national/national_05: neck 8.12 km wide cuts off 4 ZIPs (92328...), 9.2% of its land area and 0.0% of its mass; cut 92384-92389 8.12 km
- national/national_08: neck 4.06 km wide cuts off 1158 ZIPs (07001...), 29.3% of its land area and 90.8% of its mass; cut 07461-12771 4.06 km
- national/national_13: neck 0.00 km wide cuts off 68 ZIPs (10901...), 19.7% of its land area and 4.2% of its mass; cut 12508-12550 0.00 km
- WIFI/WIFI_01: mass neck (diagnostic, not M1) 5.86 km wide cuts off 1 ZIPs (30326...), 0.0% of its land area and 8.4% of its mass; cut 30305-30326 3.40 km, 30326-30342 2.46 km
- WIFI/WIFI_02: mass neck (diagnostic, not M1) 0.40 km wide cuts off 1 ZIPs (70163...), 0.0% of its land area and 5.9% of its mass; cut 70112-70163 0.07 km, 70113-70163 0.33 km
- WIFI/WIFI_05: mass neck (diagnostic, not M1) 5.96 km wide cuts off 357 ZIPs (94129...), 83.4% of its land area and 17.4% of its mass; cut 94115-94129 0.26 km, 94118-94129 2.82 km, 94121-94129 1.12 km, 94123-94129 1.77 km
- WIFI/WIFI_06: mass neck (diagnostic, not M1) 8.56 km wide cuts off 1 ZIPs (90212...), 0.0% of its land area and 5.3% of its mass; cut 90024-90212 0.36 km, 90035-90212 2.30 km, 90067-90212 1.63 km, 90210-90212 3.02 km, 90211-90212 1.25 km
- WIFI/WIFI_09: mass neck (diagnostic, not M1) 2.80 km wide cuts off 15 ZIPs (06405...), 8.0% of its land area and 9.7% of its mass; cut 06460-06516 2.80 km
- WIFI/WIFI_09: mass neck (diagnostic, not M1) 1.27 km wide cuts off 119 ZIPs (06390...), 28.6% of its land area and 38.2% of its mass; cut 11901-11947 0.92 km, 11947-11970 0.35 km
- WIFI/WIFI_10: mass neck (diagnostic, not M1) 5.51 km wide cuts off 32 ZIPs (20715...), 4.3% of its land area and 9.3% of its mass; cut 21619-21638 5.51 km
- WIFI/WIFI_10: mass neck (diagnostic, not M1) 0.49 km wide cuts off 56 ZIPs (20001...), 0.7% of its land area and 33.9% of its mass; cut 20024-20204 0.49 km
- WIFI/WIFI_11: mass neck (diagnostic, not M1) 3.27 km wide cuts off 2 ZIPs (34103...), 0.2% of its land area and 9.5% of its mass; cut 34102-34103 3.27 km
- WIFI/WIFI_17: mass neck (diagnostic, not M1) 5.10 km wide cuts off 1 ZIPs (60606...), 0.0% of its land area and 11.4% of its mass; cut 60601-60606 0.28 km, 60602-60606 0.28 km, 60603-60606 0.29 km, 60604-60606 0.28 km, 60606-60607 1.29 km, 60606-60654 1.00 km, ...
- WIFI/WIFI_19: mass neck (diagnostic, not M1) 7.08 km wide cuts off 171 ZIPs (45001...), 8.7% of its land area and 40.5% of its mass; cut 41011-45202 0.00 km, 41017-45204 4.63 km, 41071-45202 0.00 km, 41074-45202 0.10 km, 41074-45226 2.36 km
- WIFI/WIFI_28: mass neck (diagnostic, not M1) 3.94 km wide cuts off 11 ZIPs (10017...), 0.1% of its land area and 11.7% of its mass; cut 10016-10017 1.60 km, 10017-10018 0.16 km, 10017-10020 0.08 km, 10017-10022 1.45 km, 10017-10036 0.32 km, 10017-10110 0.09 km, ...
- WIFI/WIFI_32: mass neck (diagnostic, not M1) 7.17 km wide cuts off 1 ZIPs (19103...), 0.0% of its land area and 8.0% of its mass; cut 19102-19103 2.23 km, 19103-19104 1.26 km, 19103-19130 1.54 km, 19103-19146 2.14 km
- national/national_06: mass neck (diagnostic, not M1) 6.84 km wide cuts off 6 ZIPs (91101...), 0.9% of its land area and 7.0% of its mass; cut 91030-91105 2.31 km, 91030-91106 0.93 km, 91030-91108 1.78 km, 91108-91801 1.82 km
- national/national_08: mass neck (diagnostic, not M1) 4.06 km wide cuts off 1229 ZIPs (10985...), 70.7% of its land area and 9.2% of its mass; cut 07461-12771 4.06 km
- national/national_13: mass neck (diagnostic, not M1) 3.94 km wide cuts off 11 ZIPs (10017...), 0.0% of its land area and 12.6% of its mass; cut 10016-10017 1.60 km, 10017-10018 0.16 km, 10017-10020 0.08 km, 10017-10022 1.45 km, 10017-10036 0.32 km, 10017-10110 0.09 km, ...

## solver status, bound and gap

- WIFI: status optimal, objective 7863.099200281956, bound 7863.099200281956, gap 0, tier exact
- national: status optimal, objective 6467.236846821314, bound 6467.236846821314, gap 0, tier exact

## certificate tier

- WIFI: exact
- national: exact
