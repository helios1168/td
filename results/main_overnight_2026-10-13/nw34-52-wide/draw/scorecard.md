# Scorecard: nw34-52-wide (contig arm1, instance_descaled_usd.json.gz)

**Verdict: fail**

| check | status | summary |
|---|---|---|
| one owner per cell | pass | 166500 cells, 0 with other than one owner, 0 not placed with no opportunity |
| district count per channel | pass | 2 channels, 0 off K |
| dropped for zero opportunity | pass | no cells dropped |
| final bands on drawn mass | fail | 52 districts, 3 outside the final tolerance |
| phantom shares | pass | 112 reported shares compared with the ledger, 0 not backed |
| planned against drawn owners | listed | 4 listed |
| mode compliance | pass | 0 violations, 0 metro exceptions, 0 units with zero-opportunity ZCTAs owned across them |
| ZIP contiguity | listed | 3 districts in pieces, 4 pieces, 0 ZIPs not in the graph |
| M1 polygon contiguity | fail | 3 districts in pieces, 4 detached pieces (largest 0.269 τ), 4 necks, 0 channel ZCTAs with no owner, 0 (ZCTA, fine channel) cells with no row, 0 owned twice, 18 mass necks listed beside M1 |
| geography manifest is 2025 | pass | 18 sources, all 2025 |
| solver status, bound and gap | listed | 2 channels |
| certificate tier | pass | weakest tier: exact |
| one name per district | pass | 52 districts |
| rep labels | pass | blank, as OD3 (#58) decides |

## final bands on drawn mass

- WIFI/WIFI_31: drawn 1131.04 outside [675.208, 1103.29]
- national/national_04: drawn 1116.07 outside [996.319, 1115.65]
- national/national_05: drawn 1116.02 outside [996.319, 1115.65]

## planned against drawn owners

- WIFI/CT/WIFI_08: planned share 0.096204 drawn as no ZIPs (C8)
- WIFI/IL/WIFI_16: planned share 0.05 drawn as no ZIPs (C8)
- WIFI/KY/WIFI_01: planned share 0.412171 drawn as no ZIPs (C8)
- WIFI/KY/WIFI_36: extra owner from repair in a free unit

## ZIP contiguity

- WIFI/WIFI_22: piece of 74 ZIPs, 0.104 of the district's mass, cause shape
- WIFI/WIFI_29: piece of 51 ZIPs, 0.253 of the district's mass, cause shape
- WIFI/WIFI_29: piece of 8 ZIPs, 0.0823 of the district's mass, cause shape
- national/national_03: piece of 136 ZIPs, 0.12 of the district's mass, cause attachment

## M1 polygon contiguity

- WIFI/WIFI_22: detached piece of 74 ZIPs (06390...), 0.11 τ, cause shape
- WIFI/WIFI_29: detached piece of 51 ZIPs (10001...), 0.269 τ, cause shape
- WIFI/WIFI_29: detached piece of 8 ZIPs (10302...), 0.0876 τ, cause shape
- national/national_03: detached piece of 136 ZIPs (85118...), 0.126 τ, cause attachment
- WIFI/WIFI_11: neck 5.67 km wide cuts off 266 ZIPs (07701...), 42.7% of its land area and 66.6% of its mass; cut 08023-08069 3.34 km, 08023-08070 2.33 km
- WIFI/WIFI_12: neck 3.01 km wide cuts off 4 ZIPs (33430...), 19.8% of its land area and 0.0% of its mass; cut 33430-33470 3.01 km
- national/national_03: neck 1.27 km wide cuts off 364 ZIPs (91701...), 48.4% of its land area and 88.0% of its mass; cut 92101-92132 1.27 km
- national/national_14: neck 9.49 km wide cuts off 233 ZIPs (07002...), 6.3% of its land area and 88.3% of its mass; cut 12723-12741 9.49 km
- WIFI/WIFI_05: mass neck (diagnostic, not M1) 9.82 km wide cuts off 2 ZIPs (94104...), 0.0% of its land area and 6.0% of its mass; cut 94104-94105 0.52 km, 94104-94108 0.66 km, 94105-94111 6.60 km, 94108-94111 0.36 km, 94111-94133 1.67 km
- WIFI/WIFI_08: mass neck (diagnostic, not M1) 4.87 km wide cuts off 1 ZIPs (02110...), 0.0% of its land area and 5.3% of its mass; cut 02108-02110 0.21 km, 02109-02110 2.38 km, 02110-02111 0.92 km, 02110-02210 1.36 km
- WIFI/WIFI_10: mass neck (diagnostic, not M1) 5.73 km wide cuts off 4 ZIPs (20006...), 0.0% of its land area and 21.6% of its mass; cut 20005-20006 0.60 km, 20006-20024 0.34 km, 20006-20036 1.28 km, 20006-20037 0.68 km, 20006-20052 0.80 km, 20006-20220 0.37 km, ...
- WIFI/WIFI_11: mass neck (diagnostic, not M1) 5.67 km wide cuts off 221 ZIPs (08023...), 57.3% of its land area and 33.4% of its mass; cut 08023-08069 3.34 km, 08023-08070 2.33 km
- WIFI/WIFI_12: mass neck (diagnostic, not M1) 3.27 km wide cuts off 2 ZIPs (34103...), 0.2% of its land area and 9.5% of its mass; cut 34102-34103 3.27 km
- WIFI/WIFI_15: mass neck (diagnostic, not M1) 8.47 km wide cuts off 1 ZIPs (30326...), 0.0% of its land area and 8.9% of its mass; cut 30305-30326 3.40 km, 30319-30326 1.50 km, 30324-30326 1.11 km, 30326-30342 2.46 km
- WIFI/WIFI_18: mass neck (diagnostic, not M1) 5.10 km wide cuts off 1 ZIPs (60606...), 0.0% of its land area and 13.5% of its mass; cut 60601-60606 0.28 km, 60602-60606 0.28 km, 60603-60606 0.29 km, 60604-60606 0.28 km, 60606-60607 1.29 km, 60606-60654 1.00 km, ...
- WIFI/WIFI_21: mass neck (diagnostic, not M1) 0.40 km wide cuts off 1 ZIPs (70163...), 0.0% of its land area and 8.2% of its mass; cut 70112-70163 0.07 km, 70113-70163 0.33 km
- WIFI/WIFI_22: mass neck (diagnostic, not M1) 7.65 km wide cuts off 70 ZIPs (10501...), 0.9% of its land area and 14.6% of its mass; cut 12563-12564 7.65 km
- WIFI/WIFI_22: mass neck (diagnostic, not M1) 1.27 km wide cuts off 73 ZIPs (06390...), 1.3% of its land area and 10.4% of its mass; cut 11901-11947 0.92 km, 11947-11970 0.35 km
- WIFI/WIFI_28: mass neck (diagnostic, not M1) 3.21 km wide cuts off 12 ZIPs (10017...), 0.0% of its land area and 12.3% of its mass; cut 10016-10017 1.60 km, 10017-10022 1.45 km, 10022-10171 0.16 km
- WIFI/WIFI_29: mass neck (diagnostic, not M1) 0.08 km wide cuts off 50 ZIPs (10001...), 0.1% of its land area and 25.3% of its mass; cut 10019-10153 0.08 km
- WIFI/WIFI_29: mass neck (diagnostic, not M1) 1.46 km wide cuts off 7 ZIPs (10302...), 0.1% of its land area and 8.1% of its mass; cut 10311-10314 1.46 km
- WIFI/WIFI_32: mass neck (diagnostic, not M1) 5.59 km wide cuts off 7 ZIPs (15101...), 0.2% of its land area and 13.0% of its mass; cut 15219-15222 5.59 km
- WIFI/WIFI_33: mass neck (diagnostic, not M1) 7.17 km wide cuts off 1 ZIPs (19103...), 0.0% of its land area and 8.0% of its mass; cut 19102-19103 2.23 km, 19103-19104 1.26 km, 19103-19130 1.54 km, 19103-19146 2.14 km
- national/national_03: mass neck (diagnostic, not M1) 0.07 km wide cuts off 135 ZIPs (85118...), 51.6% of its land area and 12.0% of its mass; cut 85236-85295 0.07 km
- national/national_14: mass neck (diagnostic, not M1) 2.33 km wide cuts off 7 ZIPs (10017...), 0.0% of its land area and 18.1% of its mass; cut 10016-10017 1.60 km, 10017-10018 0.16 km, 10017-10020 0.08 km, 10017-10036 0.32 km, 10017-10110 0.09 km, 10036-10173 0.08 km
- national/national_15: mass neck (diagnostic, not M1) 8.08 km wide cuts off 11 ZIPs (10019...), 0.0% of its land area and 5.9% of its mass; cut 10019-10022 0.57 km, 10019-10065 0.52 km, 10019-10153 0.08 km, 10021-10065 1.83 km, 10022-10103 0.08 km, 10022-10111 0.08 km, ...

## solver status, bound and gap

- WIFI: status optimal, objective 7821.600868799401, bound 7821.600868799401, gap 0, tier exact
- national: status optimal, objective 7271.069511068012, bound 7271.069511068012, gap 0, tier exact

## certificate tier

- WIFI: exact
- national: exact
