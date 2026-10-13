# Scorecard: w8-50-bal-wide (contig arm1+repair + window repair, w8-50-bal-wide, repair pass 2)

**Verdict: fail**

| check | status | summary |
|---|---|---|
| one owner per cell | pass | 166500 cells, 0 with other than one owner, 0 not placed with no opportunity |
| district count per channel | pass | 4 channels, 0 off K |
| dropped for zero opportunity | pass | no cells dropped |
| final bands on drawn mass | pass | 50 districts, 0 outside the final tolerance |
| phantom shares | pass | 152 reported shares compared with the ledger, 0 not backed |
| planned against drawn owners | listed | 3 listed |
| mode compliance | pass | 0 violations, 0 metro exceptions, 0 units with zero-opportunity ZCTAs owned across them |
| ZIP contiguity | listed | 2 districts in pieces, 2 pieces, 0 ZIPs not in the graph |
| M1 polygon contiguity | fail | 2 districts in pieces, 2 detached pieces (largest 0.283 τ), 2 necks, 0 channel ZCTAs with no owner, 0 (ZCTA, fine channel) cells with no row, 0 owned twice, 13 mass necks listed beside M1 |
| geography manifest is 2025 | pass | 18 sources, all 2025 |
| solver status, bound and gap | listed | 4 channels |
| certificate tier | pass | weakest tier: exact |
| one name per district | pass | 50 districts |
| rep labels | pass | blank, as OD3 (#58) decides |

## planned against drawn owners

- FI/NJ/FI_06: planned share 0.346703 drawn as no ZIPs (C8)
- WH/NC/WH_06: planned share 0.375651 drawn as no ZIPs (C8)
- WH/NY/WH_05: planned share 0.0928015 drawn as no ZIPs (C8)

## ZIP contiguity

- FI/FI_12: piece of 1103 ZIPs, 0.166 of the district's mass, cause corridor
- WH/WH_05: piece of 288 ZIPs, 0.275 of the district's mass, cause corridor

## M1 polygon contiguity

- FI/FI_12: detached piece of 1103 ZIPs (50001...), 0.165 τ, cause corridor
- WH/WH_05: detached piece of 288 ZIPs (06001...), 0.283 τ, cause corridor
- FI/FI_12: neck 0.64 km wide cuts off 1102 ZIPs (50001...), 49.2% of its land area and 16.6% of its mass; cut 52218-52344 0.64 km
- WH/WH_05: neck 1.11 km wide cuts off 287 ZIPs (06001...), 39.8% of its land area and 27.5% of its mass; cut 06371-06376 1.11 km
- FI/FI_06: mass neck (diagnostic, not M1) 3.94 km wide cuts off 11 ZIPs (10017...), 0.0% of its land area and 11.9% of its mass; cut 10016-10017 1.60 km, 10017-10018 0.16 km, 10017-10020 0.08 km, 10017-10022 1.45 km, 10017-10036 0.32 km, 10017-10110 0.09 km, ...
- FI/FI_12: mass neck (diagnostic, not M1) 0.64 km wide cuts off 1102 ZIPs (50001...), 49.2% of its land area and 16.6% of its mass; cut 52218-52344 0.64 km
- FI/FI_14: mass neck (diagnostic, not M1) 7.08 km wide cuts off 53 ZIPs (45001...), 0.4% of its land area and 11.4% of its mass; cut 41011-45202 0.00 km, 41017-45204 4.63 km, 41071-45202 0.00 km, 41074-45202 0.10 km, 41074-45226 2.36 km
- FI/FI_18: mass neck (diagnostic, not M1) 7.98 km wide cuts off 15 ZIPs (10301...), 4.2% of its land area and 12.3% of its mass; cut 11204-11228 0.53 km, 11209-11220 2.58 km, 11214-11228 2.34 km, 11219-11228 2.08 km, 11220-11228 0.45 km
- WH/WH_02: mass neck (diagnostic, not M1) 0.40 km wide cuts off 1 ZIPs (70163...), 0.0% of its land area and 5.2% of its mass; cut 70112-70163 0.07 km, 70113-70163 0.33 km
- WH/WH_04: mass neck (diagnostic, not M1) 9.82 km wide cuts off 2 ZIPs (94104...), 0.0% of its land area and 6.3% of its mass; cut 94104-94105 0.52 km, 94104-94108 0.66 km, 94105-94111 6.60 km, 94108-94111 0.36 km, 94111-94133 1.67 km
- WH/WH_05: mass neck (diagnostic, not M1) 1.11 km wide cuts off 287 ZIPs (06001...), 39.8% of its land area and 27.5% of its mass; cut 06371-06376 1.11 km
- WH/WH_06: mass neck (diagnostic, not M1) 5.73 km wide cuts off 4 ZIPs (20006...), 0.0% of its land area and 20.9% of its mass; cut 20005-20006 0.60 km, 20006-20024 0.34 km, 20006-20036 1.28 km, 20006-20037 0.68 km, 20006-20052 0.80 km, 20006-20220 0.37 km, ...
- WH/WH_08: mass neck (diagnostic, not M1) 5.10 km wide cuts off 1 ZIPs (60606...), 0.0% of its land area and 13.4% of its mass; cut 60601-60606 0.28 km, 60602-60606 0.28 km, 60603-60606 0.29 km, 60604-60606 0.28 km, 60606-60607 1.29 km, 60606-60654 1.00 km, ...
- WH/WH_10: mass neck (diagnostic, not M1) 5.27 km wide cuts off 13 ZIPs (10017...), 0.0% of its land area and 5.4% of its mass; cut 10016-10017 1.60 km, 10017-10018 0.16 km, 10017-10022 1.45 km, 10017-10036 0.32 km, 10017-10110 0.09 km, 10019-10020 0.71 km, ...
- WH/WH_11: mass neck (diagnostic, not M1) 7.17 km wide cuts off 1 ZIPs (19103...), 0.0% of its land area and 7.3% of its mass; cut 19102-19103 2.23 km, 19103-19104 1.26 km, 19103-19130 1.54 km, 19103-19146 2.14 km
- national/national_08: mass neck (diagnostic, not M1) 5.62 km wide cuts off 12 ZIPs (11203...), 0.1% of its land area and 12.9% of its mass; cut 11207-11212 2.26 km, 11207-11236 1.27 km, 11236-11239 2.09 km
- national/national_14: mass neck (diagnostic, not M1) 1.81 km wide cuts off 1408 ZIPs (10453...), 99.8% of its land area and 33.2% of its mass; cut 10452-10453 1.81 km

## solver status, bound and gap

- FI: status optimal, objective 7305.2120367688885, bound 7305.2120367688885, gap 0, tier exact
- WH: status optimal, objective 6437.71876600095, bound 6437.71876600095, gap 0, tier exact
- WIFI: status optimal, objective 1549.9296713965784, bound 1549.9296713965784, gap 0, tier exact
- national: status optimal, objective 6178.531289733178, bound 6178.531289733178, gap 0, tier exact

## certificate tier

- FI: exact
- WH: exact
- WIFI: exact
- national: exact

**Overnight grid label (main_overnight_2026-10-13):** fails M1 (M1 across coverage gaps: fail, 2 districts in pieces, 2 detached pieces (largest 0.283 τ), 2 necks, 0 channel ZCTAs with no owner, 0 (ZCTA, fine channel) cells with no row, 0 owned twice, 11 mass necks listed beside M1)
