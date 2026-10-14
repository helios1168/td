# Scorecard: w8-52-filight-wide (contig arm1, instance_descaled_usd.json.gz)

**Verdict: fail**

| check | status | summary |
|---|---|---|
| one owner per cell | pass | 166500 cells, 0 with other than one owner, 0 not placed with no opportunity |
| district count per channel | pass | 4 channels, 0 off K |
| dropped for zero opportunity | pass | no cells dropped |
| final bands on drawn mass | pass | 52 districts, 0 outside the final tolerance |
| phantom shares | pass | 154 reported shares compared with the ledger, 0 not backed |
| planned against drawn owners | listed | 2 listed |
| mode compliance | pass | 0 violations, 0 metro exceptions, 0 units with zero-opportunity ZCTAs owned across them |
| ZIP contiguity | listed | 2 districts in pieces, 2 pieces, 0 ZIPs not in the graph |
| M1 polygon contiguity | fail | 2 districts in pieces, 2 detached pieces (largest 0.462 τ), 10 necks, 0 channel ZCTAs with no owner, 0 (ZCTA, fine channel) cells with no row, 0 owned twice, 16 mass necks listed beside M1 |
| geography manifest is 2025 | pass | 18 sources, all 2025 |
| solver status, bound and gap | listed | 4 channels |
| certificate tier | pass | weakest tier: exact |
| one name per district | pass | 52 districts |
| rep labels | pass | blank, as OD3 (#58) decides |

## planned against drawn owners

- WH/VA/WH_05: planned share 0.230111 drawn as no ZIPs (C8)
- national/IL/national_12: planned share 0.18042 drawn as no ZIPs (C8)

## ZIP contiguity

- FI/FI_06: piece of 288 ZIPs, 0.473 of the district's mass, cause corridor
- FI/FI_12: piece of 1103 ZIPs, 0.166 of the district's mass, cause corridor

## M1 polygon contiguity

- FI/FI_06: detached piece of 288 ZIPs (06001...), 0.462 τ, cause corridor
- FI/FI_12: detached piece of 1103 ZIPs (50001...), 0.165 τ, cause corridor
- FI/FI_06: neck 0.03 km wide cuts off 263 ZIPs (07001...), 25.5% of its land area and 52.2% of its mass; cut 07001-08830 0.03 km
- FI/FI_08: neck 5.67 km wide cuts off 75 ZIPs (08023...), 18.0% of its land area and 12.2% of its mass; cut 08023-08069 3.34 km, 08023-08070 2.33 km
- FI/FI_12: neck 0.64 km wide cuts off 1102 ZIPs (50001...), 49.2% of its land area and 16.6% of its mass; cut 52218-52344 0.64 km
- FI/FI_18: neck 6.97 km wide cuts off 16 ZIPs (10501...), 13.9% of its land area and 0.4% of its mass; cut 10504-10506 6.97 km
- WH/WH_04: neck 4.94 km wide cuts off 250 ZIPs (07701...), 39.7% of its land area and 34.5% of its mass; cut 08832-08861 2.29 km, 08861-08863 0.84 km, 08861-08879 1.82 km
- WH/WH_05: neck 3.03 km wide cuts off 330 ZIPs (07001...), 20.3% of its land area and 34.7% of its mass; cut 08030-08093 3.03 km
- national/national_03: neck 5.48 km wide cuts off 203 ZIPs (82930...), 15.7% of its land area and 26.2% of its mass; cut 84621-84652 4.19 km, 84621-84654 1.29 km
- national/national_04: neck 8.81 km wide cuts off 5 ZIPs (93527...), 6.3% of its land area and 0.0% of its mass; cut 93527-93554 8.81 km
- national/national_05: neck 8.12 km wide cuts off 4 ZIPs (92328...), 9.1% of its land area and 0.0% of its mass; cut 92384-92389 8.12 km
- national/national_16: neck 6.14 km wide cuts off 44 ZIPs (79734...), 6.2% of its land area and 3.7% of its mass; cut 79718-79734 6.14 km
- FI/FI_06: mass neck (diagnostic, not M1) 1.11 km wide cuts off 287 ZIPs (06001...), 74.5% of its land area and 47.3% of its mass; cut 06371-06376 1.11 km
- FI/FI_06: mass neck (diagnostic, not M1) 4.91 km wide cuts off 253 ZIPs (07002...), 25.0% of its land area and 50.0% of its mass; cut 07036-07202 3.76 km, 10005-10271 0.28 km, 10006-10271 0.06 km, 10012-10014 0.80 km
- FI/FI_08: mass neck (diagnostic, not M1) 5.67 km wide cuts off 75 ZIPs (08023...), 18.0% of its land area and 12.2% of its mass; cut 08023-08069 3.34 km, 08023-08070 2.33 km
- FI/FI_12: mass neck (diagnostic, not M1) 0.64 km wide cuts off 1102 ZIPs (50001...), 49.2% of its land area and 16.6% of its mass; cut 52218-52344 0.64 km
- FI/FI_14: mass neck (diagnostic, not M1) 7.08 km wide cuts off 53 ZIPs (45001...), 0.4% of its land area and 11.4% of its mass; cut 41011-45202 0.00 km, 41017-45204 4.63 km, 41071-45202 0.00 km, 41074-45202 0.10 km, 41074-45226 2.36 km
- FI/FI_18: mass neck (diagnostic, not M1) 3.94 km wide cuts off 11 ZIPs (10017...), 0.0% of its land area and 10.6% of its mass; cut 10016-10017 1.60 km, 10017-10018 0.16 km, 10017-10020 0.08 km, 10017-10022 1.45 km, 10017-10036 0.32 km, 10017-10110 0.09 km, ...
- WH/WH_01: mass neck (diagnostic, not M1) 0.40 km wide cuts off 1 ZIPs (70163...), 0.0% of its land area and 6.7% of its mass; cut 70112-70163 0.07 km, 70113-70163 0.33 km
- WH/WH_03: mass neck (diagnostic, not M1) 9.82 km wide cuts off 2 ZIPs (94104...), 0.0% of its land area and 6.3% of its mass; cut 94104-94105 0.52 km, 94104-94108 0.66 km, 94105-94111 6.60 km, 94108-94111 0.36 km, 94111-94133 1.67 km
- WH/WH_04: mass neck (diagnostic, not M1) 4.94 km wide cuts off 250 ZIPs (07701...), 39.7% of its land area and 34.5% of its mass; cut 08832-08861 2.29 km, 08861-08863 0.84 km, 08861-08879 1.82 km
- WH/WH_05: mass neck (diagnostic, not M1) 3.03 km wide cuts off 330 ZIPs (07001...), 20.3% of its land area and 34.7% of its mass; cut 08030-08093 3.03 km
- WH/WH_07: mass neck (diagnostic, not M1) 5.10 km wide cuts off 1 ZIPs (60606...), 0.0% of its land area and 14.0% of its mass; cut 60601-60606 0.28 km, 60602-60606 0.28 km, 60603-60606 0.29 km, 60604-60606 0.28 km, 60606-60607 1.29 km, 60606-60654 1.00 km, ...
- WH/WH_11: mass neck (diagnostic, not M1) 1.81 km wide cuts off 22 ZIPs (10019...), 0.0% of its land area and 19.8% of its mass; cut 10452-10453 1.81 km
- WH/WH_12: mass neck (diagnostic, not M1) 7.17 km wide cuts off 1 ZIPs (19103...), 0.0% of its land area and 7.3% of its mass; cut 19102-19103 2.23 km, 19103-19104 1.26 km, 19103-19130 1.54 km, 19103-19146 2.14 km
- national/national_03: mass neck (diagnostic, not M1) 5.48 km wide cuts off 203 ZIPs (82930...), 15.7% of its land area and 26.2% of its mass; cut 84621-84652 4.19 km, 84621-84654 1.29 km
- national/national_04: mass neck (diagnostic, not M1) 0.16 km wide cuts off 4 ZIPs (94104...), 0.0% of its land area and 6.0% of its mass; cut 94103-94108 0.16 km
- national/national_15: mass neck (diagnostic, not M1) 0.00 km wide cuts off 1246 ZIPs (10901...), 99.4% of its land area and 28.3% of its mass; cut 12508-12550 0.00 km

## solver status, bound and gap

- FI: status optimal, objective 7305.2120367688885, bound 7305.2120367688885, gap 0, tier exact
- WH: status optimal, objective 6883.50682369453, bound 6883.50682369453, gap 0, tier exact
- WIFI: status optimal, objective 1549.9296713965784, bound 1549.9296713965784, gap 0, tier exact
- national: status optimal, objective 6029.253647600414, bound 6029.253647600414, gap 0, tier exact

## certificate tier

- FI: exact
- WH: exact
- WIFI: exact
- national: exact
