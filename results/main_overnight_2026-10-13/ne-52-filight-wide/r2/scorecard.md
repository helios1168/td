# Scorecard: ne-52-filight-wide (contig arm1+repair + window repair, ne-52-filight-wide, repair pass 2)

**Verdict: fail**

| check | status | summary |
|---|---|---|
| one owner per cell | pass | 166500 cells, 0 with other than one owner, 0 not placed with no opportunity |
| district count per channel | pass | 4 channels, 0 off K |
| dropped for zero opportunity | pass | no cells dropped |
| final bands on drawn mass | pass | 52 districts, 0 outside the final tolerance |
| phantom shares | pass | 134 reported shares compared with the ledger, 0 not backed |
| planned against drawn owners | listed | 1 listed |
| mode compliance | pass | 0 violations, 0 metro exceptions, 0 units with zero-opportunity ZCTAs owned across them |
| ZIP contiguity | pass | 0 districts in pieces, 0 pieces, 0 ZIPs not in the graph |
| M1 polygon contiguity | fail | 0 districts in pieces, 0 detached pieces (largest 0 τ), 2 necks, 0 channel ZCTAs with no owner, 0 (ZCTA, fine channel) cells with no row, 0 owned twice, 11 mass necks listed beside M1 |
| geography manifest is 2025 | pass | 18 sources, all 2025 |
| solver status, bound and gap | listed | 4 channels |
| certificate tier | pass | weakest tier: exact |
| one name per district | pass | 52 districts |
| rep labels | pass | blank, as OD3 (#58) decides |

## planned against drawn owners

- FI/NY/FI_07: extra owner from repair in a free unit

## M1 polygon contiguity

- FI/FI_07: neck 5.67 km wide cuts off 69 ZIPs (08023...), 21.0% of its land area and 12.2% of its mass; cut 08023-08069 3.34 km, 08023-08070 2.33 km
- national/national_16: neck 6.14 km wide cuts off 44 ZIPs (79734...), 5.8% of its land area and 3.7% of its mass; cut 79718-79734 6.14 km
- FI/FI_07: mass neck (diagnostic, not M1) 5.67 km wide cuts off 69 ZIPs (08023...), 21.0% of its land area and 12.2% of its mass; cut 08023-08069 3.34 km, 08023-08070 2.33 km
- FI/FI_16: mass neck (diagnostic, not M1) 3.94 km wide cuts off 11 ZIPs (10017...), 0.0% of its land area and 9.7% of its mass; cut 10016-10017 1.60 km, 10017-10018 0.16 km, 10017-10020 0.08 km, 10017-10022 1.45 km, 10017-10036 0.32 km, 10017-10110 0.09 km, ...
- WH/WH_01: mass neck (diagnostic, not M1) 8.47 km wide cuts off 1 ZIPs (30326...), 0.0% of its land area and 6.7% of its mass; cut 30305-30326 3.40 km, 30319-30326 1.50 km, 30324-30326 1.11 km, 30326-30342 2.46 km
- WH/WH_02: mass neck (diagnostic, not M1) 0.40 km wide cuts off 1 ZIPs (70163...), 0.0% of its land area and 5.4% of its mass; cut 70112-70163 0.07 km, 70113-70163 0.33 km
- WH/WH_04: mass neck (diagnostic, not M1) 9.82 km wide cuts off 2 ZIPs (94104...), 0.0% of its land area and 5.1% of its mass; cut 94104-94105 0.52 km, 94104-94108 0.66 km, 94105-94111 6.60 km, 94108-94111 0.36 km, 94111-94133 1.67 km
- WH/WH_05: mass neck (diagnostic, not M1) 5.73 km wide cuts off 4 ZIPs (20006...), 0.0% of its land area and 21.4% of its mass; cut 20005-20006 0.60 km, 20006-20024 0.34 km, 20006-20036 1.28 km, 20006-20037 0.68 km, 20006-20052 0.80 km, 20006-20220 0.37 km, ...
- WH/WH_06: mass neck (diagnostic, not M1) 7.17 km wide cuts off 1 ZIPs (19103...), 0.0% of its land area and 6.0% of its mass; cut 19102-19103 2.23 km, 19103-19104 1.26 km, 19103-19130 1.54 km, 19103-19146 2.14 km
- WH/WH_08: mass neck (diagnostic, not M1) 5.10 km wide cuts off 1 ZIPs (60606...), 0.0% of its land area and 14.8% of its mass; cut 60601-60606 0.28 km, 60602-60606 0.28 km, 60603-60606 0.29 km, 60604-60606 0.28 km, 60606-60607 1.29 km, 60606-60654 1.00 km, ...
- WH/WH_10: mass neck (diagnostic, not M1) 5.27 km wide cuts off 13 ZIPs (10017...), 0.0% of its land area and 5.9% of its mass; cut 10016-10017 1.60 km, 10017-10018 0.16 km, 10017-10022 1.45 km, 10017-10036 0.32 km, 10017-10110 0.09 km, 10019-10020 0.71 km, ...
- national/national_09: mass neck (diagnostic, not M1) 4.01 km wide cuts off 7 ZIPs (10019...), 0.0% of its land area and 5.0% of its mass; cut 10019-10022 0.57 km, 10019-10023 2.61 km, 10019-10065 0.52 km, 10019-10153 0.08 km, 10022-10103 0.08 km, 10022-10111 0.08 km, ...
- national/national_14: mass neck (diagnostic, not M1) 1.77 km wide cuts off 9 ZIPs (10017...), 0.0% of its land area and 15.3% of its mass; cut 10016-10017 1.60 km, 10017-10018 0.16 km

## solver status, bound and gap

- FI: status optimal, objective 6958.485883536435, bound 6958.485883536435, gap 0, tier exact
- WH: status optimal, objective 7068.125682387932, bound 7068.125682387932, gap 0, tier exact
- WIFI: status optimal, objective 2217.567709579973, bound 2217.567709579973, gap 0, tier exact
- national: status optimal, objective 6288.596596507043, bound 6288.596596507043, gap 0, tier exact

## certificate tier

- FI: exact
- WH: exact
- WIFI: exact
- national: exact

**Overnight grid label (main_overnight_2026-10-13):** fails M1 (M1 across coverage gaps: fail, 0 districts in pieces, 0 detached pieces (largest 0 τ), 1 necks, 0 channel ZCTAs with no owner, 0 (ZCTA, fine channel) cells with no row, 0 owned twice, 9 mass necks listed beside M1)
