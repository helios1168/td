# Scorecard: w8-cmp-seed-wide (contig arm1 + window repair, w8-cmp-seed-wide, repair pass 1)

**Verdict: fail**

| check | status | summary |
|---|---|---|
| one owner per cell | pass | 166500 cells, 0 with other than one owner, 0 not placed with no opportunity |
| district count per channel | pass | 4 channels, 0 off K |
| dropped for zero opportunity | pass | no cells dropped |
| final bands on drawn mass | pass | 49 districts, 0 outside the final tolerance |
| phantom shares | pass | 152 reported shares compared with the ledger, 0 not backed |
| planned against drawn owners | listed | 4 listed |
| mode compliance | pass | 0 violations, 0 metro exceptions, 0 units with zero-opportunity ZCTAs owned across them |
| ZIP contiguity | listed | 2 districts in pieces, 2 pieces, 0 ZIPs not in the graph |
| M1 polygon contiguity | fail | 2 districts in pieces, 2 detached pieces (largest 0.477 τ), 6 necks, 0 channel ZCTAs with no owner, 0 (ZCTA, fine channel) cells with no row, 0 owned twice, 18 mass necks listed beside M1 |
| geography manifest is 2025 | pass | 18 sources, all 2025 |
| solver status, bound and gap | listed | 4 channels |
| certificate tier | pass | weakest tier: exact |
| one name per district | pass | 49 districts |
| rep labels | pass | blank, as OD3 (#58) decides |

## planned against drawn owners

- FI/CA/FI_05: planned share 0.0984861 drawn as no ZIPs (C8)
- WH/NC/WH_06: planned share 0.375651 drawn as no ZIPs (C8)
- WH/NY/WH_05: planned share 0.0928015 drawn as no ZIPs (C8)
- national/MI/national_08: planned share 0.253765 drawn as no ZIPs (C8)

## ZIP contiguity

- FI/FI_01: piece of 656 ZIPs, 0.458 of the district's mass, cause corridor
- WH/WH_05: piece of 288 ZIPs, 0.275 of the district's mass, cause corridor

## M1 polygon contiguity

- FI/FI_01: detached piece of 656 ZIPs (35004...), 0.477 τ, cause corridor
- WH/WH_05: detached piece of 288 ZIPs (06001...), 0.283 τ, cause corridor
- FI/FI_01: neck 0.42 km wide cuts off 913 ZIPs (37601...), 48.1% of its land area and 54.1% of its mass; cut 37902-37929 0.42 km
- FI/FI_06: neck 8.82 km wide cuts off 102 ZIPs (11703...), 11.8% of its land area and 23.1% of its mass; cut 11939-11957 7.95 km, 11957-11965 0.88 km
- FI/FI_08: neck 5.67 km wide cuts off 69 ZIPs (08023...), 21.1% of its land area and 13.4% of its mass; cut 08023-08069 3.34 km, 08023-08070 2.33 km
- WH/WH_05: neck 1.11 km wide cuts off 287 ZIPs (06001...), 39.8% of its land area and 27.5% of its mass; cut 06371-06376 1.11 km
- national/national_03: neck 5.48 km wide cuts off 203 ZIPs (82930...), 13.6% of its land area and 15.0% of its mass; cut 84621-84652 4.19 km, 84621-84654 1.29 km
- national/national_09: neck 5.67 km wide cuts off 597 ZIPs (07001...), 38.7% of its land area and 78.6% of its mass; cut 08023-08069 3.34 km, 08023-08070 2.33 km
- FI/FI_01: mass neck (diagnostic, not M1) 0.49 km wide cuts off 655 ZIPs (35004...), 51.9% of its land area and 45.8% of its mass; cut 36101-36104 0.38 km, 36101-36107 0.11 km
- FI/FI_06: mass neck (diagnostic, not M1) 8.82 km wide cuts off 102 ZIPs (11703...), 11.8% of its land area and 23.1% of its mass; cut 11939-11957 7.95 km, 11957-11965 0.88 km
- FI/FI_08: mass neck (diagnostic, not M1) 5.67 km wide cuts off 69 ZIPs (08023...), 21.1% of its land area and 13.4% of its mass; cut 08023-08069 3.34 km, 08023-08070 2.33 km
- FI/FI_09: mass neck (diagnostic, not M1) 2.38 km wide cuts off 44 ZIPs (33701...), 1.2% of its land area and 6.7% of its mass; cut 33635-34677 2.38 km
- FI/FI_19: mass neck (diagnostic, not M1) 3.94 km wide cuts off 11 ZIPs (10017...), 0.1% of its land area and 10.9% of its mass; cut 10016-10017 1.60 km, 10017-10018 0.16 km, 10017-10020 0.08 km, 10017-10022 1.45 km, 10017-10036 0.32 km, 10017-10110 0.09 km, ...
- WH/WH_02: mass neck (diagnostic, not M1) 0.40 km wide cuts off 1 ZIPs (70163...), 0.0% of its land area and 5.2% of its mass; cut 70112-70163 0.07 km, 70113-70163 0.33 km
- WH/WH_04: mass neck (diagnostic, not M1) 9.82 km wide cuts off 2 ZIPs (94104...), 0.0% of its land area and 6.3% of its mass; cut 94104-94105 0.52 km, 94104-94108 0.66 km, 94105-94111 6.60 km, 94108-94111 0.36 km, 94111-94133 1.67 km
- WH/WH_05: mass neck (diagnostic, not M1) 1.11 km wide cuts off 287 ZIPs (06001...), 39.8% of its land area and 27.5% of its mass; cut 06371-06376 1.11 km
- WH/WH_06: mass neck (diagnostic, not M1) 5.73 km wide cuts off 4 ZIPs (20006...), 0.0% of its land area and 20.9% of its mass; cut 20005-20006 0.60 km, 20006-20024 0.34 km, 20006-20036 1.28 km, 20006-20037 0.68 km, 20006-20052 0.80 km, 20006-20220 0.37 km, ...
- WH/WH_08: mass neck (diagnostic, not M1) 5.10 km wide cuts off 1 ZIPs (60606...), 0.0% of its land area and 13.4% of its mass; cut 60601-60606 0.28 km, 60602-60606 0.28 km, 60603-60606 0.29 km, 60604-60606 0.28 km, 60606-60607 1.29 km, 60606-60654 1.00 km, ...
- WH/WH_10: mass neck (diagnostic, not M1) 5.27 km wide cuts off 13 ZIPs (10017...), 0.0% of its land area and 5.4% of its mass; cut 10016-10017 1.60 km, 10017-10018 0.16 km, 10017-10022 1.45 km, 10017-10036 0.32 km, 10017-10110 0.09 km, 10019-10020 0.71 km, ...
- WH/WH_11: mass neck (diagnostic, not M1) 7.17 km wide cuts off 1 ZIPs (19103...), 0.0% of its land area and 7.3% of its mass; cut 19102-19103 2.23 km, 19103-19104 1.26 km, 19103-19130 1.54 km, 19103-19146 2.14 km
- national/national_03: mass neck (diagnostic, not M1) 5.48 km wide cuts off 203 ZIPs (82930...), 13.6% of its land area and 15.0% of its mass; cut 84621-84652 4.19 km, 84621-84654 1.29 km
- national/national_04: mass neck (diagnostic, not M1) 8.36 km wide cuts off 21 ZIPs (94104...), 0.4% of its land area and 7.3% of its mass; cut 94102-94108 0.90 km, 94103-94105 0.89 km, 94103-94108 0.16 km, 94105-94107 2.28 km, 94105-94109 0.62 km, 94108-94109 0.96 km, ...
- national/national_06: mass neck (diagnostic, not M1) 6.12 km wide cuts off 6 ZIPs (94538...), 0.0% of its land area and 8.9% of its mass; cut 95132-95140 6.12 km
- national/national_07: mass neck (diagnostic, not M1) 7.91 km wide cuts off 10 ZIPs (10001...), 0.0% of its land area and 6.7% of its mass; cut 10001-10016 0.64 km, 10002-10003 0.36 km, 10002-10009 1.51 km, 10002-10012 0.51 km, 10002-10013 0.70 km, 10007-10013 1.06 km, ...
- national/national_09: mass neck (diagnostic, not M1) 5.67 km wide cuts off 546 ZIPs (08023...), 61.3% of its land area and 21.4% of its mass; cut 08023-08069 3.34 km, 08023-08070 2.33 km
- national/national_13: mass neck (diagnostic, not M1) 0.00 km wide cuts off 90 ZIPs (10017...), 0.3% of its land area and 34.1% of its mass; cut 12508-12550 0.00 km

## solver status, bound and gap

- FI: status optimal, objective 7412.75351033627, bound 7412.75351033627, gap 0, tier exact
- WH: status optimal, objective 6437.71876600095, bound 6437.71876600095, gap 0, tier exact
- WIFI: status optimal, objective 1549.9296713965784, bound 1549.9296713965784, gap 0, tier exact
- national: status optimal, objective 7206.143442299535, bound 7206.143442299535, gap 0, tier exact

## certificate tier

- FI: exact
- WH: exact
- WIFI: exact
- national: exact
