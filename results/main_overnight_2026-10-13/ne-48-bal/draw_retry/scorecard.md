# Scorecard: ne-48-bal (contig arm1, instance_descaled_usd.json.gz)

**Verdict: fail**

| check | status | summary |
|---|---|---|
| one owner per cell | pass | 166500 cells, 0 with other than one owner, 0 not placed with no opportunity |
| district count per channel | pass | 4 channels, 0 off K |
| dropped for zero opportunity | pass | no cells dropped |
| final bands on drawn mass | fail | 48 districts, 6 outside the final tolerance |
| phantom shares | pass | 136 reported shares compared with the ledger, 0 not backed |
| planned against drawn owners | listed | 1 listed |
| mode compliance | pass | 0 violations, 0 metro exceptions, 0 units with zero-opportunity ZCTAs owned across them |
| ZIP contiguity | listed | 5 districts in pieces, 7 pieces, 0 ZIPs not in the graph |
| M1 polygon contiguity | fail | 5 districts in pieces, 7 detached pieces (largest 0.211 τ), 3 necks, 0 channel ZCTAs with no owner, 0 (ZCTA, fine channel) cells with no row, 0 owned twice, 13 mass necks listed beside M1 |
| geography manifest is 2025 | pass | 18 sources, all 2025 |
| solver status, bound and gap | listed | 4 channels |
| certificate tier | pass | weakest tier: exact |
| one name per district | pass | 48 districts |
| rep labels | pass | blank, as OD3 (#58) decides |

## final bands on drawn mass

- FI/FI_10: drawn 726.837 outside [765.017, 997.289]; undrawn share of OH
- FI/FI_11: drawn 728.495 outside [765.017, 997.289]; undrawn share of OH
- FI/FI_13: drawn 731.986 outside [765.017, 997.289]; undrawn share of NC
- FI/FI_18: drawn 1011.91 outside [765.017, 997.289]; undrawn share of PA
- WH/WH_04: drawn 854.751 outside [877.817, 1149.94]; undrawn share of CA
- WH/WH_06: drawn 1191.46 outside [877.817, 1149.94]

## planned against drawn owners

- national/FL/national_01: planned share 0.123505 drawn as no ZIPs (C8)

## ZIP contiguity

- FI/FI_01: piece of 84 ZIPs, 0.217 of the district's mass, cause shape
- FI/FI_01: piece of 43 ZIPs, 0.0163 of the district's mass, cause shape
- FI/FI_01: piece of 15 ZIPs, 0.00604 of the district's mass, cause shape
- FI/FI_04: piece of 12 ZIPs, 0.0362 of the district's mass, cause shape
- FI/FI_17: piece of 2 ZIPs, 0.00829 of the district's mass, cause shape
- national/national_12: piece of 1 ZIPs, 0.00213 of the district's mass, cause shape
- national/national_13: piece of 24 ZIPs, 0.0514 of the district's mass, cause shape

## M1 polygon contiguity

- FI/FI_01: detached piece of 84 ZIPs (33523...), 0.211 τ, cause shape
- FI/FI_01: detached piece of 43 ZIPs (32008...), 0.0159 τ, cause shape
- FI/FI_01: detached piece of 15 ZIPs (34428...), 0.00588 τ, cause shape
- FI/FI_04: detached piece of 12 ZIPs (95008...), 0.0393 τ, cause shape
- FI/FI_17: detached piece of 2 ZIPs (10307...), 0.00855 τ, cause shape
- national/national_12: detached piece of 1 ZIPs (10119...), 0.0024 τ, cause shape
- national/national_13: detached piece of 24 ZIPs (10001...), 0.058 τ, cause shape
- national/national_04: neck 8.81 km wide cuts off 5 ZIPs (93527...), 5.6% of its land area and 0.0% of its mass; cut 93527-93554 8.81 km
- national/national_05: neck 8.12 km wide cuts off 4 ZIPs (92328...), 9.2% of its land area and 0.0% of its mass; cut 92384-92389 8.12 km
- national/national_08: neck 5.67 km wide cuts off 597 ZIPs (07001...), 38.5% of its land area and 76.3% of its mass; cut 08023-08069 3.34 km, 08023-08070 2.33 km
- FI/FI_01: mass neck (diagnostic, not M1) 4.26 km wide cuts off 83 ZIPs (33523...), 0.8% of its land area and 21.7% of its mass; cut 33523-33576 2.07 km, 33576-34639 2.19 km
- FI/FI_05: mass neck (diagnostic, not M1) 5.96 km wide cuts off 198 ZIPs (93635...), 2.3% of its land area and 35.3% of its mass; cut 94115-94129 0.26 km, 94118-94129 2.82 km, 94121-94129 1.12 km, 94123-94129 1.77 km
- FI/FI_16: mass neck (diagnostic, not M1) 3.94 km wide cuts off 11 ZIPs (10017...), 0.0% of its land area and 9.2% of its mass; cut 10016-10017 1.60 km, 10017-10018 0.16 km, 10017-10020 0.08 km, 10017-10022 1.45 km, 10017-10036 0.32 km, 10017-10110 0.09 km, ...
- WH/WH_02: mass neck (diagnostic, not M1) 9.96 km wide cuts off 2 ZIPs (70112...), 0.0% of its land area and 5.0% of its mass; cut 70112-70113 3.44 km, 70112-70116 2.48 km, 70112-70119 2.36 km, 70112-70130 1.35 km, 70113-70163 0.33 km
- WH/WH_04: mass neck (diagnostic, not M1) 9.82 km wide cuts off 2 ZIPs (94104...), 0.0% of its land area and 5.1% of its mass; cut 94104-94105 0.52 km, 94104-94108 0.66 km, 94105-94111 6.60 km, 94108-94111 0.36 km, 94111-94133 1.67 km
- WH/WH_05: mass neck (diagnostic, not M1) 5.73 km wide cuts off 4 ZIPs (20006...), 0.0% of its land area and 22.6% of its mass; cut 20005-20006 0.60 km, 20006-20024 0.34 km, 20006-20036 1.28 km, 20006-20037 0.68 km, 20006-20052 0.80 km, 20006-20220 0.37 km, ...
- WH/WH_07: mass neck (diagnostic, not M1) 8.47 km wide cuts off 1 ZIPs (30326...), 0.0% of its land area and 6.1% of its mass; cut 30305-30326 3.40 km, 30319-30326 1.50 km, 30324-30326 1.11 km, 30326-30342 2.46 km
- WH/WH_08: mass neck (diagnostic, not M1) 5.10 km wide cuts off 1 ZIPs (60606...), 0.0% of its land area and 14.0% of its mass; cut 60601-60606 0.28 km, 60602-60606 0.28 km, 60603-60606 0.29 km, 60604-60606 0.28 km, 60606-60607 1.29 km, 60606-60654 1.00 km, ...
- WH/WH_10: mass neck (diagnostic, not M1) 5.27 km wide cuts off 13 ZIPs (10017...), 0.0% of its land area and 5.5% of its mass; cut 10016-10017 1.60 km, 10017-10018 0.16 km, 10017-10022 1.45 km, 10017-10036 0.32 km, 10017-10110 0.09 km, 10019-10020 0.71 km, ...
- national/national_06: mass neck (diagnostic, not M1) 8.14 km wide cuts off 4 ZIPs (91101...), 0.4% of its land area and 5.8% of its mass; cut 91030-91106 0.93 km, 91030-91108 1.78 km, 91101-91105 1.74 km, 91105-91106 1.88 km, 91108-91801 1.82 km
- national/national_08: mass neck (diagnostic, not M1) 5.67 km wide cuts off 603 ZIPs (08023...), 61.5% of its land area and 23.7% of its mass; cut 08023-08069 3.34 km, 08023-08070 2.33 km
- national/national_12: mass neck (diagnostic, not M1) 3.29 km wide cuts off 12 ZIPs (10017...), 0.0% of its land area and 14.2% of its mass; cut 10016-10017 1.60 km, 10017-10020 0.08 km, 10017-10022 1.45 km, 10022-10171 0.16 km
- national/national_13: mass neck (diagnostic, not M1) 0.33 km wide cuts off 23 ZIPs (10001...), 0.0% of its land area and 5.1% of its mass; cut 10027-10115 0.33 km

## solver status, bound and gap

- FI: status optimal, objective 8855.152453286946, bound 8855.152453286946, gap 0, tier exact
- WH: status optimal, objective 7149.178452772243, bound 7149.178452772243, gap 0, tier exact
- WIFI: status optimal, objective 2217.567709579973, bound 2217.567709579973, gap 0, tier exact
- national: status optimal, objective 6263.821747107876, bound 6263.821747107876, gap 0, tier exact

## certificate tier

- FI: exact
- WH: exact
- WIFI: exact
- national: exact
