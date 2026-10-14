# Scorecard: w8-52-bal-wide (contig arm1 + window repair, w8-52-bal-wide, repair pass 1)

**Verdict: fail**

| check | status | summary |
|---|---|---|
| one owner per cell | pass | 166500 cells, 0 with other than one owner, 0 not placed with no opportunity |
| district count per channel | pass | 4 channels, 0 off K |
| dropped for zero opportunity | pass | no cells dropped |
| final bands on drawn mass | pass | 52 districts, 0 outside the final tolerance |
| phantom shares | pass | 152 reported shares compared with the ledger, 0 not backed |
| planned against drawn owners | listed | 2 listed |
| mode compliance | pass | 0 violations, 0 metro exceptions, 0 units with zero-opportunity ZCTAs owned across them |
| ZIP contiguity | pass | 0 districts in pieces, 0 pieces, 0 ZIPs not in the graph |
| M1 polygon contiguity | fail | 0 districts in pieces, 0 detached pieces (largest 0 τ), 2 necks, 0 channel ZCTAs with no owner, 0 (ZCTA, fine channel) cells with no row, 0 owned twice, 13 mass necks listed beside M1 |
| geography manifest is 2025 | pass | 18 sources, all 2025 |
| solver status, bound and gap | listed | 4 channels |
| certificate tier | pass | weakest tier: exact |
| one name per district | pass | 52 districts |
| rep labels | pass | blank, as OD3 (#58) decides |

## planned against drawn owners

- FI/CA/FI_05: planned share 0.0984861 drawn as no ZIPs (C8)
- WH/VA/WH_05: planned share 0.230111 drawn as no ZIPs (C8)

## M1 polygon contiguity

- FI/FI_08: neck 5.67 km wide cuts off 69 ZIPs (08023...), 21.1% of its land area and 13.4% of its mass; cut 08023-08069 3.34 km, 08023-08070 2.33 km
- WH/WH_05: neck 5.50 km wide cuts off 266 ZIPs (07003...), 15.6% of its land area and 30.1% of its mass; cut 08505-08610 4.74 km, 08505-08611 0.76 km
- FI/FI_06: mass neck (diagnostic, not M1) 6.29 km wide cuts off 15 ZIPs (10465...), 0.4% of its land area and 7.2% of its mass; cut 10461-10465 5.01 km, 10462-10465 0.09 km, 10465-10469 0.31 km, 10465-10473 0.08 km, 10465-10475 0.80 km
- FI/FI_08: mass neck (diagnostic, not M1) 5.67 km wide cuts off 69 ZIPs (08023...), 21.1% of its land area and 13.4% of its mass; cut 08023-08069 3.34 km, 08023-08070 2.33 km
- FI/FI_09: mass neck (diagnostic, not M1) 2.38 km wide cuts off 44 ZIPs (33701...), 1.2% of its land area and 6.7% of its mass; cut 33635-34677 2.38 km
- FI/FI_19: mass neck (diagnostic, not M1) 3.94 km wide cuts off 11 ZIPs (10017...), 0.0% of its land area and 9.8% of its mass; cut 10016-10017 1.60 km, 10017-10018 0.16 km, 10017-10020 0.08 km, 10017-10022 1.45 km, 10017-10036 0.32 km, 10017-10110 0.09 km, ...
- WH/WH_01: mass neck (diagnostic, not M1) 0.40 km wide cuts off 1 ZIPs (70163...), 0.0% of its land area and 6.7% of its mass; cut 70112-70163 0.07 km, 70113-70163 0.33 km
- WH/WH_03: mass neck (diagnostic, not M1) 9.82 km wide cuts off 2 ZIPs (94104...), 0.0% of its land area and 6.3% of its mass; cut 94104-94105 0.52 km, 94104-94108 0.66 km, 94105-94111 6.60 km, 94108-94111 0.36 km, 94111-94133 1.67 km
- WH/WH_04: mass neck (diagnostic, not M1) 6.82 km wide cuts off 16 ZIPs (10001...), 0.0% of its land area and 6.5% of its mass; cut 10001-10010 0.58 km, 10001-10011 1.99 km, 10001-10016 0.64 km, 10016-10017 1.60 km, 10016-10018 0.39 km, 10017-10022 1.45 km, ...
- WH/WH_05: mass neck (diagnostic, not M1) 5.50 km wide cuts off 266 ZIPs (07003...), 15.6% of its land area and 30.1% of its mass; cut 08505-08610 4.74 km, 08505-08611 0.76 km
- WH/WH_07: mass neck (diagnostic, not M1) 5.10 km wide cuts off 1 ZIPs (60606...), 0.0% of its land area and 14.0% of its mass; cut 60601-60606 0.28 km, 60602-60606 0.28 km, 60603-60606 0.29 km, 60604-60606 0.28 km, 60606-60607 1.29 km, 60606-60654 1.00 km, ...
- WH/WH_11: mass neck (diagnostic, not M1) 1.81 km wide cuts off 22 ZIPs (10019...), 0.0% of its land area and 19.8% of its mass; cut 10452-10453 1.81 km
- WH/WH_12: mass neck (diagnostic, not M1) 7.17 km wide cuts off 1 ZIPs (19103...), 0.0% of its land area and 7.3% of its mass; cut 19102-19103 2.23 km, 19103-19104 1.26 km, 19103-19130 1.54 km, 19103-19146 2.14 km
- national/national_08: mass neck (diagnostic, not M1) 5.62 km wide cuts off 12 ZIPs (11203...), 0.1% of its land area and 12.9% of its mass; cut 11207-11212 2.26 km, 11207-11236 1.27 km, 11236-11239 2.09 km
- national/national_14: mass neck (diagnostic, not M1) 1.81 km wide cuts off 1408 ZIPs (10453...), 99.8% of its land area and 33.2% of its mass; cut 10452-10453 1.81 km

## solver status, bound and gap

- FI: status optimal, objective 7412.75351033627, bound 7412.75351033627, gap 0, tier exact
- WH: status optimal, objective 6883.50682369453, bound 6883.50682369453, gap 0, tier exact
- WIFI: status optimal, objective 1549.9296713965784, bound 1549.9296713965784, gap 0, tier exact
- national: status optimal, objective 6178.531289733178, bound 6178.531289733178, gap 0, tier exact

## certificate tier

- FI: exact
- WH: exact
- WIFI: exact
- national: exact
