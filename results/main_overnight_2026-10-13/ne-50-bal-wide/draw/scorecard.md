# Scorecard: ne-50-bal-wide (contig arm1, instance_descaled_usd.json.gz)

**Verdict: fail**

| check | status | summary |
|---|---|---|
| one owner per cell | pass | 166500 cells, 0 with other than one owner, 0 not placed with no opportunity |
| district count per channel | pass | 4 channels, 0 off K |
| dropped for zero opportunity | pass | no cells dropped |
| final bands on drawn mass | pass | 50 districts, 0 outside the final tolerance |
| phantom shares | pass | 134 reported shares compared with the ledger, 0 not backed |
| planned against drawn owners | listed | 1 listed |
| mode compliance | pass | 0 violations, 0 metro exceptions, 0 units with zero-opportunity ZCTAs owned across them |
| ZIP contiguity | listed | 3 districts in pieces, 4 pieces, 0 ZIPs not in the graph |
| M1 polygon contiguity | fail | 3 districts in pieces, 4 detached pieces (largest 0.113 τ), 5 necks, 0 channel ZCTAs with no owner, 0 (ZCTA, fine channel) cells with no row, 0 owned twice, 11 mass necks listed beside M1 |
| geography manifest is 2025 | pass | 18 sources, all 2025 |
| solver status, bound and gap | listed | 4 channels |
| certificate tier | pass | weakest tier: exact |
| one name per district | pass | 50 districts |
| rep labels | pass | blank, as OD3 (#58) decides |

## planned against drawn owners

- FI/NY/FI_07: extra owner from repair in a free unit

## ZIP contiguity

- FI/FI_04: piece of 1 ZIPs, 0.0144 of the district's mass, cause shape
- national/national_08: piece of 8 ZIPs, 0.0211 of the district's mass, cause shape
- national/national_09: piece of 4 ZIPs, 0.104 of the district's mass, cause tiny share
- national/national_09: piece of 3 ZIPs, 0.00469 of the district's mass, cause tiny share

## M1 polygon contiguity

- FI/FI_04: detached piece of 1 ZIPs (95113...), 0.0164 τ, cause shape
- national/national_08: detached piece of 8 ZIPs (10302...), 0.0228 τ, cause shape
- national/national_09: detached piece of 4 ZIPs (11214...), 0.113 τ, cause tiny share
- national/national_09: detached piece of 3 ZIPs (11701...), 0.00509 τ, cause tiny share
- FI/FI_07: neck 5.67 km wide cuts off 69 ZIPs (08023...), 21.0% of its land area and 12.2% of its mass; cut 08023-08069 3.34 km, 08023-08070 2.33 km
- national/national_04: neck 8.81 km wide cuts off 5 ZIPs (93527...), 6.2% of its land area and 0.0% of its mass; cut 93527-93554 8.81 km
- national/national_05: neck 8.12 km wide cuts off 4 ZIPs (92328...), 9.1% of its land area and 0.0% of its mass; cut 92384-92389 8.12 km
- national/national_09: neck 5.67 km wide cuts off 69 ZIPs (08023...), 21.0% of its land area and 2.3% of its mass; cut 08023-08069 3.34 km, 08023-08070 2.33 km
- national/national_15: neck 6.14 km wide cuts off 44 ZIPs (79734...), 6.7% of its land area and 3.3% of its mass; cut 79718-79734 6.14 km
- FI/FI_07: mass neck (diagnostic, not M1) 5.67 km wide cuts off 69 ZIPs (08023...), 21.0% of its land area and 12.2% of its mass; cut 08023-08069 3.34 km, 08023-08070 2.33 km
- FI/FI_16: mass neck (diagnostic, not M1) 3.94 km wide cuts off 11 ZIPs (10017...), 0.0% of its land area and 9.7% of its mass; cut 10016-10017 1.60 km, 10017-10018 0.16 km, 10017-10020 0.08 km, 10017-10022 1.45 km, 10017-10036 0.32 km, 10017-10110 0.09 km, ...
- WH/WH_02: mass neck (diagnostic, not M1) 9.96 km wide cuts off 2 ZIPs (70112...), 0.0% of its land area and 5.0% of its mass; cut 70112-70113 3.44 km, 70112-70116 2.48 km, 70112-70119 2.36 km, 70112-70130 1.35 km, 70113-70163 0.33 km
- WH/WH_04: mass neck (diagnostic, not M1) 6.12 km wide cuts off 2 ZIPs (90067...), 0.0% of its land area and 6.1% of its mass; cut 90024-90067 0.78 km, 90024-90212 0.36 km, 90025-90067 1.39 km, 90035-90067 0.53 km, 90035-90212 2.30 km, 90064-90067 0.76 km
- WH/WH_05: mass neck (diagnostic, not M1) 5.73 km wide cuts off 4 ZIPs (20006...), 0.0% of its land area and 22.6% of its mass; cut 20005-20006 0.60 km, 20006-20024 0.34 km, 20006-20036 1.28 km, 20006-20037 0.68 km, 20006-20052 0.80 km, 20006-20220 0.37 km, ...
- WH/WH_07: mass neck (diagnostic, not M1) 8.47 km wide cuts off 1 ZIPs (30326...), 0.0% of its land area and 6.1% of its mass; cut 30305-30326 3.40 km, 30319-30326 1.50 km, 30324-30326 1.11 km, 30326-30342 2.46 km
- WH/WH_08: mass neck (diagnostic, not M1) 5.10 km wide cuts off 1 ZIPs (60606...), 0.0% of its land area and 14.0% of its mass; cut 60601-60606 0.28 km, 60602-60606 0.28 km, 60603-60606 0.29 km, 60604-60606 0.28 km, 60606-60607 1.29 km, 60606-60654 1.00 km, ...
- WH/WH_10: mass neck (diagnostic, not M1) 5.27 km wide cuts off 13 ZIPs (10017...), 0.0% of its land area and 5.2% of its mass; cut 10016-10017 1.60 km, 10017-10018 0.16 km, 10017-10022 1.45 km, 10017-10036 0.32 km, 10017-10110 0.09 km, 10019-10020 0.71 km, ...
- national/national_04: mass neck (diagnostic, not M1) 8.36 km wide cuts off 6 ZIPs (94104...), 0.0% of its land area and 6.1% of its mass; cut 94102-94108 0.90 km, 94103-94105 0.89 km, 94103-94108 0.16 km, 94105-94107 2.28 km, 94105-94109 0.62 km, 94108-94109 0.96 km, ...
- national/national_09: mass neck (diagnostic, not M1) 1.12 km wide cuts off 3 ZIPs (11224...), 0.1% of its land area and 8.2% of its mass; cut 11214-11224 1.12 km
- national/national_14: mass neck (diagnostic, not M1) 3.94 km wide cuts off 11 ZIPs (10017...), 0.0% of its land area and 15.9% of its mass; cut 10016-10017 1.60 km, 10017-10018 0.16 km, 10017-10020 0.08 km, 10017-10022 1.45 km, 10017-10036 0.32 km, 10017-10110 0.09 km, ...

## solver status, bound and gap

- FI: status optimal, objective 6958.485883536435, bound 6958.485883536435, gap 0, tier exact
- WH: status optimal, objective 7149.178452772243, bound 7149.178452772243, gap 0, tier exact
- WIFI: status optimal, objective 2217.567709579973, bound 2217.567709579973, gap 0, tier exact
- national: status optimal, objective 7060.550678331434, bound 7060.550678331434, gap 0, tier exact

## certificate tier

- FI: exact
- WH: exact
- WIFI: exact
- national: exact
