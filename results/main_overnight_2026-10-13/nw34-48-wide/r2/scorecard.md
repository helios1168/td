# Scorecard: nw34-48-wide (contig arm1+repair + window repair, nw34-48-wide, repair pass 2)

**Verdict: fail**

| check | status | summary |
|---|---|---|
| one owner per cell | pass | 166500 cells, 0 with other than one owner, 0 not placed with no opportunity |
| district count per channel | pass | 2 channels, 0 off K |
| dropped for zero opportunity | pass | no cells dropped |
| final bands on drawn mass | pass | 48 districts, 0 outside the final tolerance |
| phantom shares | pass | 110 reported shares compared with the ledger, 0 not backed |
| planned against drawn owners | listed | 3 listed |
| mode compliance | pass | 0 violations, 0 metro exceptions, 0 units with zero-opportunity ZCTAs owned across them |
| ZIP contiguity | listed | 1 districts in pieces, 1 pieces, 0 ZIPs not in the graph |
| M1 polygon contiguity | fail | 1 districts in pieces, 1 detached pieces (largest 0.32 τ), 6 necks, 0 channel ZCTAs with no owner, 0 (ZCTA, fine channel) cells with no row, 0 owned twice, 16 mass necks listed beside M1 |
| geography manifest is 2025 | pass | 18 sources, all 2025 |
| solver status, bound and gap | listed | 2 channels |
| certificate tier | pass | weakest tier: exact |
| one name per district | pass | 48 districts |
| rep labels | pass | blank, as OD3 (#58) decides |

## planned against drawn owners

- WIFI/CT/WIFI_08: planned share 0.389285 drawn as no ZIPs (C8)
- WIFI/IL/WIFI_15: planned share 0.154308 drawn as no ZIPs (C8)
- WIFI/IN/WIFI_19: planned share 0.253778 drawn as no ZIPs (C8)

## ZIP contiguity

- WIFI/WIFI_10: piece of 57 ZIPs, 0.339 of the district's mass, cause corridor

## M1 polygon contiguity

- WIFI/WIFI_10: detached piece of 57 ZIPs (20001...), 0.32 τ, cause corridor
- WIFI/WIFI_05: neck 5.96 km wide cuts off 236 ZIPs (93635...), 16.6% of its land area and 82.6% of its mass; cut 94115-94129 0.26 km, 94118-94129 2.82 km, 94121-94129 1.12 km, 94123-94129 1.77 km
- WIFI/WIFI_06: neck 9.39 km wide cuts off 29 ZIPs (93901...), 5.6% of its land area and 2.0% of its mass; cut 93452-93920 9.39 km
- WIFI/WIFI_10: neck 5.67 km wide cuts off 150 ZIPs (08001...), 33.5% of its land area and 33.7% of its mass; cut 08023-08069 3.34 km, 08023-08070 2.33 km
- WIFI/WIFI_11: neck 3.01 km wide cuts off 4 ZIPs (33430...), 19.8% of its land area and 0.0% of its mass; cut 33430-33470 3.01 km
- WIFI/WIFI_19: neck 7.08 km wide cuts off 176 ZIPs (45001...), 8.7% of its land area and 44.4% of its mass; cut 41011-45202 0.00 km, 41017-45204 4.63 km, 41071-45202 0.00 km, 41074-45202 0.10 km, 41074-45226 2.36 km
- national/national_08: neck 4.06 km wide cuts off 456 ZIPs (12719...), 45.5% of its land area and 6.9% of its mass; cut 07461-12771 4.06 km
- WIFI/WIFI_01: mass neck (diagnostic, not M1) 5.86 km wide cuts off 1 ZIPs (30326...), 0.0% of its land area and 8.4% of its mass; cut 30305-30326 3.40 km, 30326-30342 2.46 km
- WIFI/WIFI_02: mass neck (diagnostic, not M1) 0.40 km wide cuts off 1 ZIPs (70163...), 0.0% of its land area and 5.9% of its mass; cut 70112-70163 0.07 km, 70113-70163 0.33 km
- WIFI/WIFI_05: mass neck (diagnostic, not M1) 5.96 km wide cuts off 357 ZIPs (94129...), 83.4% of its land area and 17.4% of its mass; cut 94115-94129 0.26 km, 94118-94129 2.82 km, 94121-94129 1.12 km, 94123-94129 1.77 km
- WIFI/WIFI_06: mass neck (diagnostic, not M1) 8.56 km wide cuts off 1 ZIPs (90212...), 0.0% of its land area and 5.3% of its mass; cut 90024-90212 0.36 km, 90035-90212 2.30 km, 90067-90212 1.63 km, 90210-90212 3.02 km, 90211-90212 1.25 km
- WIFI/WIFI_10: mass neck (diagnostic, not M1) 5.51 km wide cuts off 32 ZIPs (20715...), 4.3% of its land area and 9.3% of its mass; cut 21619-21638 5.51 km
- WIFI/WIFI_10: mass neck (diagnostic, not M1) 0.49 km wide cuts off 56 ZIPs (20001...), 0.7% of its land area and 33.9% of its mass; cut 20024-20204 0.49 km
- WIFI/WIFI_11: mass neck (diagnostic, not M1) 3.27 km wide cuts off 2 ZIPs (34103...), 0.2% of its land area and 9.5% of its mass; cut 34102-34103 3.27 km
- WIFI/WIFI_17: mass neck (diagnostic, not M1) 5.10 km wide cuts off 1 ZIPs (60606...), 0.0% of its land area and 12.1% of its mass; cut 60601-60606 0.28 km, 60602-60606 0.28 km, 60603-60606 0.29 km, 60604-60606 0.28 km, 60606-60607 1.29 km, 60606-60654 1.00 km, ...
- WIFI/WIFI_19: mass neck (diagnostic, not M1) 7.08 km wide cuts off 176 ZIPs (45001...), 8.7% of its land area and 44.4% of its mass; cut 41011-45202 0.00 km, 41017-45204 4.63 km, 41071-45202 0.00 km, 41074-45202 0.10 km, 41074-45226 2.36 km
- WIFI/WIFI_21: mass neck (diagnostic, not M1) 4.87 km wide cuts off 1 ZIPs (02110...), 0.0% of its land area and 6.1% of its mass; cut 02108-02110 0.21 km, 02109-02110 2.38 km, 02110-02111 0.92 km, 02110-02210 1.36 km
- WIFI/WIFI_28: mass neck (diagnostic, not M1) 1.60 km wide cuts off 11 ZIPs (10017...), 0.0% of its land area and 11.3% of its mass; cut 10016-10017 1.60 km
- WIFI/WIFI_29: mass neck (diagnostic, not M1) 0.00 km wide cuts off 115 ZIPs (10001...), 0.7% of its land area and 31.4% of its mass; cut 12508-12550 0.00 km
- WIFI/WIFI_32: mass neck (diagnostic, not M1) 7.17 km wide cuts off 1 ZIPs (19103...), 0.0% of its land area and 8.0% of its mass; cut 19102-19103 2.23 km, 19103-19104 1.26 km, 19103-19130 1.54 km, 19103-19146 2.14 km
- national/national_06: mass neck (diagnostic, not M1) 6.84 km wide cuts off 6 ZIPs (91101...), 0.9% of its land area and 7.0% of its mass; cut 91030-91105 2.31 km, 91030-91106 0.93 km, 91030-91108 1.78 km, 91108-91801 1.82 km
- national/national_08: mass neck (diagnostic, not M1) 0.16 km wide cuts off 12 ZIPs (10017...), 0.0% of its land area and 16.6% of its mass; cut 10017-10018 0.16 km
- national/national_13: mass neck (diagnostic, not M1) 7.74 km wide cuts off 7 ZIPs (10001...), 0.0% of its land area and 5.3% of its mass; cut 10001-10010 0.58 km, 10001-10016 0.64 km, 10002-10012 0.51 km, 10002-10013 0.70 km, 10003-10011 1.37 km, 10003-10012 1.35 km, ...

## solver status, bound and gap

- WIFI: status optimal, objective 7863.099200281956, bound 7863.099200281956, gap 0, tier exact
- national: status optimal, objective 6467.236846821314, bound 6467.236846821314, gap 0, tier exact

## certificate tier

- WIFI: exact
- national: exact

**Overnight grid label (main_overnight_2026-10-13):** fails M1 (M1 across coverage gaps: fail, 1 districts in pieces, 1 detached pieces (largest 0.32 τ), 3 necks, 0 channel ZCTAs with no owner, 0 (ZCTA, fine channel) cells with no row, 0 owned twice, 14 mass necks listed beside M1)
