# Scorecard: nw34-52-wide (contig arm1, instance_descaled_usd.json.gz)

**Verdict: fail**

| check | status | summary |
|---|---|---|
| one owner per cell | pass | 166500 cells, 0 with other than one owner, 0 not placed with no opportunity |
| district count per channel | pass | 2 channels, 0 off K |
| dropped for zero opportunity | pass | no cells dropped |
| final bands on drawn mass | pass | 52 districts, 0 outside the final tolerance |
| phantom shares | pass | 108 reported shares compared with the ledger, 0 not backed |
| planned against drawn owners | listed | 3 listed |
| mode compliance | pass | 0 violations, 0 metro exceptions, 0 units with zero-opportunity ZCTAs owned across them |
| ZIP contiguity | listed | 6 districts in pieces, 7 pieces, 0 ZIPs not in the graph |
| M1 polygon contiguity | fail | 6 districts in pieces, 7 detached pieces (largest 0.456 τ), 10 necks, 0 channel ZCTAs with no owner, 0 (ZCTA, fine channel) cells with no row, 0 owned twice, 20 mass necks listed beside M1 |
| geography manifest is 2025 | pass | 18 sources, all 2025 |
| solver status, bound and gap | listed | 2 channels |
| certificate tier | pass | weakest tier: exact |
| one name per district | pass | 52 districts |
| rep labels | pass | blank, as OD3 (#58) decides |

## planned against drawn owners

- WIFI/CO/WIFI_03: planned share 0.116548 drawn as no ZIPs (C8)
- WIFI/IL/WIFI_15: planned share 0.05 drawn as no ZIPs (C8)
- WIFI/MA/WIFI_08: planned share 0.0897375 drawn as no ZIPs (C8)

## ZIP contiguity

- WIFI/WIFI_01: piece of 698 ZIPs, 0.371 of the district's mass, cause attachment
- WIFI/WIFI_05: piece of 12 ZIPs, 0.0128 of the district's mass, cause shape
- WIFI/WIFI_10: piece of 10 ZIPs, 0.0699 of the district's mass, cause shape
- WIFI/WIFI_18: piece of 738 ZIPs, 0.17 of the district's mass, cause corridor
- WIFI/WIFI_22: piece of 1038 ZIPs, 0.409 of the district's mass, cause corridor
- WIFI/WIFI_22: piece of 79 ZIPs, 0.0121 of the district's mass, cause shape
- WIFI/WIFI_29: piece of 8 ZIPs, 0.0822 of the district's mass, cause shape

## M1 polygon contiguity

- WIFI/WIFI_01: detached piece of 698 ZIPs (40003...), 0.33 τ, cause attachment
- WIFI/WIFI_05: detached piece of 12 ZIPs (94510...), 0.0141 τ, cause shape
- WIFI/WIFI_10: detached piece of 10 ZIPs (18014...), 0.0653 τ, cause shape
- WIFI/WIFI_18: detached piece of 738 ZIPs (24701...), 0.184 τ, cause corridor
- WIFI/WIFI_22: detached piece of 1038 ZIPs (03031...), 0.456 τ, cause corridor
- WIFI/WIFI_22: detached piece of 79 ZIPs (12015...), 0.0135 τ, cause shape
- WIFI/WIFI_29: detached piece of 8 ZIPs (10302...), 0.0876 τ, cause shape
- WIFI/WIFI_01: neck 0.21 km wide cuts off 697 ZIPs (40003...), 40.0% of its land area and 37.1% of its mass; cut 42444-42455 0.21 km
- WIFI/WIFI_03: neck 5.48 km wide cuts off 203 ZIPs (82930...), 8.8% of its land area and 34.8% of its mass; cut 84621-84652 4.19 km, 84621-84654 1.29 km
- WIFI/WIFI_05: neck 5.96 km wide cuts off 175 ZIPs (94129...), 42.8% of its land area and 8.3% of its mass; cut 94115-94129 0.26 km, 94118-94129 2.82 km, 94121-94129 1.12 km, 94123-94129 1.77 km
- WIFI/WIFI_10: neck 5.67 km wide cuts off 69 ZIPs (08023...), 35.1% of its land area and 21.4% of its mass; cut 08023-08069 3.34 km, 08023-08070 2.33 km
- WIFI/WIFI_11: neck 3.01 km wide cuts off 4 ZIPs (33430...), 19.8% of its land area and 0.0% of its mass; cut 33430-33470 3.01 km
- WIFI/WIFI_18: neck 1.17 km wide cuts off 737 ZIPs (24701...), 38.2% of its land area and 17.0% of its mass; cut 25071-25156 1.17 km
- WIFI/WIFI_28: neck 4.13 km wide cuts off 57 ZIPs (10002...), 5.1% of its land area and 28.1% of its mass; cut 11414-11420 0.16 km, 11414-11430 2.00 km, 11417-11420 1.97 km
- WIFI/WIFI_36: neck 6.14 km wide cuts off 44 ZIPs (79734...), 6.6% of its land area and 5.4% of its mass; cut 79718-79734 6.14 km
- national/national_05: neck 8.12 km wide cuts off 4 ZIPs (92328...), 9.1% of its land area and 0.0% of its mass; cut 92384-92389 8.12 km
- national/national_15: neck 0.00 km wide cuts off 46 ZIPs (10901...), 42.3% of its land area and 5.8% of its mass; cut 12508-12550 0.00 km
- WIFI/WIFI_01: mass neck (diagnostic, not M1) 0.21 km wide cuts off 697 ZIPs (40003...), 40.0% of its land area and 37.1% of its mass; cut 42444-42455 0.21 km
- WIFI/WIFI_02: mass neck (diagnostic, not M1) 0.40 km wide cuts off 1 ZIPs (70163...), 0.0% of its land area and 5.9% of its mass; cut 70112-70163 0.07 km, 70113-70163 0.33 km
- WIFI/WIFI_03: mass neck (diagnostic, not M1) 5.48 km wide cuts off 203 ZIPs (82930...), 8.8% of its land area and 34.8% of its mass; cut 84621-84652 4.19 km, 84621-84654 1.29 km
- WIFI/WIFI_05: mass neck (diagnostic, not M1) 4.78 km wide cuts off 4 ZIPs (91303...), 0.1% of its land area and 5.8% of its mass; cut 91302-91367 4.78 km
- WIFI/WIFI_09: mass neck (diagnostic, not M1) 5.73 km wide cuts off 4 ZIPs (20006...), 0.0% of its land area and 20.8% of its mass; cut 20005-20006 0.60 km, 20006-20024 0.34 km, 20006-20036 1.28 km, 20006-20037 0.68 km, 20006-20052 0.80 km, 20006-20220 0.37 km, ...
- WIFI/WIFI_10: mass neck (diagnostic, not M1) 0.58 km wide cuts off 6 ZIPs (19103...), 0.1% of its land area and 9.9% of its mass; cut 08102-19123 0.58 km
- WIFI/WIFI_10: mass neck (diagnostic, not M1) 5.69 km wide cuts off 9 ZIPs (18014...), 3.2% of its land area and 7.0% of its mass; cut 18014-18058 5.69 km
- WIFI/WIFI_11: mass neck (diagnostic, not M1) 3.27 km wide cuts off 2 ZIPs (34103...), 0.2% of its land area and 9.5% of its mass; cut 34102-34103 3.27 km
- WIFI/WIFI_14: mass neck (diagnostic, not M1) 8.47 km wide cuts off 1 ZIPs (30326...), 0.0% of its land area and 8.9% of its mass; cut 30305-30326 3.40 km, 30319-30326 1.50 km, 30324-30326 1.11 km, 30326-30342 2.46 km
- WIFI/WIFI_17: mass neck (diagnostic, not M1) 5.10 km wide cuts off 1 ZIPs (60606...), 0.0% of its land area and 13.5% of its mass; cut 60601-60606 0.28 km, 60602-60606 0.28 km, 60603-60606 0.29 km, 60604-60606 0.28 km, 60606-60607 1.29 km, 60606-60654 1.00 km, ...
- WIFI/WIFI_18: mass neck (diagnostic, not M1) 1.17 km wide cuts off 737 ZIPs (24701...), 38.2% of its land area and 17.0% of its mass; cut 25071-25156 1.17 km
- WIFI/WIFI_18: mass neck (diagnostic, not M1) 4.42 km wide cuts off 57 ZIPs (40006...), 2.3% of its land area and 14.0% of its mass; cut 40202-40204 0.82 km, 40202-40206 1.81 km, 40203-40204 1.80 km
- WIFI/WIFI_22: mass neck (diagnostic, not M1) 0.44 km wide cuts off 1037 ZIPs (03031...), 95.7% of its land area and 40.9% of its mass; cut 05478-05481 0.44 km
- WIFI/WIFI_22: mass neck (diagnostic, not M1) 1.18 km wide cuts off 23 ZIPs (10013...), 0.1% of its land area and 6.6% of its mass; cut 10013-10014 1.18 km
- WIFI/WIFI_28: mass neck (diagnostic, not M1) 0.46 km wide cuts off 55 ZIPs (10002...), 4.9% of its land area and 27.8% of its mass; cut 11239-11414 0.46 km
- WIFI/WIFI_29: mass neck (diagnostic, not M1) 1.46 km wide cuts off 7 ZIPs (10302...), 0.1% of its land area and 8.1% of its mass; cut 10311-10314 1.46 km
- WIFI/WIFI_36: mass neck (diagnostic, not M1) 3.33 km wide cuts off 32 ZIPs (79821...), 1.3% of its land area and 5.4% of its mass; cut 79839-79853 3.33 km
- national/national_09: mass neck (diagnostic, not M1) 0.66 km wide cuts off 2059 ZIPs (10464...), 98.1% of its land area and 45.2% of its mass; cut 10464-10475 0.27 km, 10475-10803 0.39 km
- national/national_13: mass neck (diagnostic, not M1) 0.39 km wide cuts off 142 ZIPs (18940...), 0.8% of its land area and 19.6% of its mass; cut 19350-19374 0.39 km
- national/national_15: mass neck (diagnostic, not M1) 0.00 km wide cuts off 46 ZIPs (10901...), 42.3% of its land area and 5.8% of its mass; cut 12508-12550 0.00 km

## solver status, bound and gap

- WIFI: status optimal, objective 7401.898274252719, bound 7401.898274252719, gap 0, tier exact
- national: status optimal, objective 6195.180124318301, bound 6195.180124318301, gap 0, tier exact

## certificate tier

- WIFI: exact
- national: exact
