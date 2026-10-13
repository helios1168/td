# Scorecard: w1-50-wide (contig arm1+repair + window repair, w1-50-wide, repair pass 2)

**Verdict: fail**

| check | status | summary |
|---|---|---|
| one owner per cell | pass | 166500 cells, 0 with other than one owner, 0 not placed with no opportunity |
| district count per channel | pass | 1 channels, 0 off K |
| dropped for zero opportunity | pass | no cells dropped |
| final bands on drawn mass | pass | 50 districts, 0 outside the final tolerance |
| phantom shares | pass | 81 reported shares compared with the ledger, 0 not backed |
| planned against drawn owners | listed | 7 listed |
| mode compliance | pass | 0 violations, 0 metro exceptions, 0 units with zero-opportunity ZCTAs owned across them |
| ZIP contiguity | listed | 2 districts in pieces, 2 pieces, 0 ZIPs not in the graph |
| M1 polygon contiguity | fail | 2 districts in pieces, 2 detached pieces (largest 0.406 τ), 3 necks, 0 channel ZCTAs with no owner, 0 (ZCTA, fine channel) cells with no row, 0 owned twice, 23 mass necks listed beside M1 |
| geography manifest is 2025 | pass | 18 sources, all 2025 |
| solver status, bound and gap | listed | 1 channels |
| certificate tier | pass | weakest tier: exact |
| one name per district | pass | 50 districts |
| rep labels | pass | blank, as OD3 (#58) decides |

## planned against drawn owners

- WIFI/MD/WIFI_13: planned share 0.235997 drawn as no ZIPs (C8)
- WIFI/MI/WIFI_25: planned share 0.119502 drawn as no ZIPs (C8)
- WIFI/MN/WIFI_19: planned share 0.104514 drawn as no ZIPs (C8)
- WIFI/SC/WIFI_01: planned share 0.249604 drawn as no ZIPs (C8)
- WIFI/MI/WIFI_23: extra owner from repair in a free unit
- WIFI/MI/WIFI_41: extra owner from repair in a free unit
- WIFI/TX/WIFI_26: extra owner from repair in a free unit

## ZIP contiguity

- WIFI/WIFI_13: piece of 199 ZIPs, 0.496 of the district's mass, cause corridor
- WIFI/WIFI_29: piece of 938 ZIPs, 0.417 of the district's mass, cause corridor

## M1 polygon contiguity

- WIFI/WIFI_13: detached piece of 199 ZIPs (08001...), 0.343 τ, cause corridor
- WIFI/WIFI_29: detached piece of 938 ZIPs (03031...), 0.406 τ, cause corridor
- WIFI/WIFI_13: neck 5.67 km wide cuts off 69 ZIPs (08023...), 43.6% of its land area and 30.4% of its mass; cut 08023-08069 3.34 km, 08023-08070 2.33 km
- WIFI/WIFI_20: neck 5.48 km wide cuts off 96 ZIPs (84511...), 6.5% of its land area and 6.6% of its mass; cut 84621-84652 4.19 km, 84621-84654 1.29 km
- WIFI/WIFI_38: neck 2.32 km wide cuts off 51 ZIPs (10001...), 17.5% of its land area and 85.1% of its mass; cut 10004-10005 0.78 km, 10004-10038 0.05 km, 10005-10006 0.25 km, 10006-10007 0.68 km, 10006-10038 0.09 km, 10006-10271 0.06 km, ...
- WIFI/WIFI_05: mass neck (diagnostic, not M1) 6.88 km wide cuts off 2 ZIPs (94538...), 0.2% of its land area and 10.4% of its mass; cut 94538-95035 0.85 km, 94538-95134 6.03 km
- WIFI/WIFI_06: mass neck (diagnostic, not M1) 5.54 km wide cuts off 1 ZIPs (90212...), 0.1% of its land area and 5.9% of its mass; cut 90024-90212 0.36 km, 90035-90212 2.30 km, 90067-90212 1.63 km, 90211-90212 1.25 km
- WIFI/WIFI_08: mass neck (diagnostic, not M1) 1.94 km wide cuts off 1 ZIPs (94104...), 0.0% of its land area and 5.0% of its mass; cut 94104-94105 0.52 km, 94104-94108 0.66 km, 94104-94111 0.76 km
- WIFI/WIFI_09: mass neck (diagnostic, not M1) 0.27 km wide cuts off 4 ZIPs (92606...), 1.8% of its land area and 14.8% of its mass; cut 92701-92780 0.27 km
- WIFI/WIFI_10: mass neck (diagnostic, not M1) 8.72 km wide cuts off 18 ZIPs (94505...), 0.8% of its land area and 6.6% of its mass; cut 95206-95215 5.66 km, 95206-95336 3.06 km
- WIFI/WIFI_13: mass neck (diagnostic, not M1) 1.00 km wide cuts off 198 ZIPs (08001...), 98.6% of its land area and 49.6% of its mass; cut 08037-08217 0.79 km, 08215-08217 0.21 km
- WIFI/WIFI_13: mass neck (diagnostic, not M1) 3.90 km wide cuts off 52 ZIPs (20001...), 1.4% of its land area and 49.9% of its mass; cut 20001-20004 1.30 km, 20004-20005 0.48 km, 20004-20220 0.21 km, 20004-20230 0.53 km, 20004-20560 0.51 km, 20004-20565 0.18 km, ...
- WIFI/WIFI_18: mass neck (diagnostic, not M1) 8.47 km wide cuts off 1 ZIPs (30326...), 0.0% of its land area and 7.2% of its mass; cut 30305-30326 3.40 km, 30319-30326 1.50 km, 30324-30326 1.11 km, 30326-30342 2.46 km
- WIFI/WIFI_19: mass neck (diagnostic, not M1) 8.45 km wide cuts off 1 ZIPs (53202...), 0.0% of its land area and 5.6% of its mass; cut 53202-53203 1.59 km, 53202-53204 1.05 km, 53202-53207 1.07 km, 53202-53211 2.31 km, 53202-53212 2.43 km
- WIFI/WIFI_20: mass neck (diagnostic, not M1) 3.86 km wide cuts off 52 ZIPs (84710...), 2.5% of its land area and 6.3% of its mass; cut 84740-84750 3.86 km
- WIFI/WIFI_21: mass neck (diagnostic, not M1) 5.10 km wide cuts off 1 ZIPs (60606...), 0.0% of its land area and 17.3% of its mass; cut 60601-60606 0.28 km, 60602-60606 0.28 km, 60603-60606 0.29 km, 60604-60606 0.28 km, 60606-60607 1.29 km, 60606-60654 1.00 km, ...
- WIFI/WIFI_25: mass neck (diagnostic, not M1) 5.81 km wide cuts off 26 ZIPs (45001...), 0.2% of its land area and 8.5% of its mass; cut 41011-45202 0.00 km, 41017-45204 4.63 km, 41071-45202 0.00 km, 41074-45202 0.10 km, 45202-45226 1.09 km
- WIFI/WIFI_26: mass neck (diagnostic, not M1) 0.40 km wide cuts off 1 ZIPs (70163...), 0.0% of its land area and 6.3% of its mass; cut 70112-70163 0.07 km, 70113-70163 0.33 km
- WIFI/WIFI_28: mass neck (diagnostic, not M1) 8.61 km wide cuts off 1 ZIPs (21031...), 0.0% of its land area and 6.3% of its mass; cut 21030-21031 8.61 km
- WIFI/WIFI_29: mass neck (diagnostic, not M1) 0.44 km wide cuts off 937 ZIPs (03031...), 98.0% of its land area and 41.7% of its mass; cut 05478-05481 0.44 km
- WIFI/WIFI_37: mass neck (diagnostic, not M1) 8.46 km wide cuts off 19 ZIPs (10901...), 0.8% of its land area and 11.2% of its mass; cut 10925-10990 8.46 km
- WIFI/WIFI_38: mass neck (diagnostic, not M1) 1.65 km wide cuts off 3 ZIPs (10020...), 0.1% of its land area and 5.7% of its mass; cut 10017-10020 0.08 km, 10019-10020 0.71 km, 10019-10111 0.39 km, 10020-10036 0.31 km, 10022-10111 0.08 km, 10022-10112 0.08 km
- WIFI/WIFI_39: mass neck (diagnostic, not M1) 9.76 km wide cuts off 19 ZIPs (10025...), 0.0% of its land area and 5.0% of its mass; cut 10451-10456 2.59 km, 10452-10453 1.81 km, 10452-10456 1.17 km, 10452-10457 0.61 km, 10454-10474 0.51 km, 10455-10456 0.90 km, ...
- WIFI/WIFI_43: mass neck (diagnostic, not M1) 7.17 km wide cuts off 1 ZIPs (19103...), 0.0% of its land area and 11.3% of its mass; cut 19102-19103 2.23 km, 19103-19104 1.26 km, 19103-19130 1.54 km, 19103-19146 2.14 km
- WIFI/WIFI_45: mass neck (diagnostic, not M1) 8.26 km wide cuts off 1 ZIPs (18101...), 0.0% of its land area and 5.0% of its mass; cut 18101-18102 8.26 km
- WIFI/WIFI_47: mass neck (diagnostic, not M1) 3.53 km wide cuts off 1 ZIPs (75225...), 0.0% of its land area and 7.5% of its mass; cut 75206-75225 1.64 km, 75225-75231 1.89 km
- WIFI/WIFI_49: mass neck (diagnostic, not M1) 8.46 km wide cuts off 1 ZIPs (78701...), 0.0% of its land area and 7.5% of its mass; cut 78701-78702 2.77 km, 78701-78704 2.29 km, 78701-78705 2.40 km, 78701-78712 0.99 km
- WIFI/WIFI_50: mass neck (diagnostic, not M1) 2.91 km wide cuts off 1 ZIPs (24011...), 0.0% of its land area and 5.9% of its mass; cut 24011-24013 0.92 km, 24011-24016 1.99 km

## solver status, bound and gap

- WIFI: status optimal, objective 6485.879906746569, bound 6485.879906746569, gap 0, tier exact

## certificate tier

- WIFI: exact

**Overnight grid label (main_overnight_2026-10-13):** fails M1 (M1 across coverage gaps: fail, 2 districts in pieces, 2 detached pieces (largest 0.406 τ), 2 necks, 0 channel ZCTAs with no owner, 0 (ZCTA, fine channel) cells with no row, 0 owned twice, 15 mass necks listed beside M1)
