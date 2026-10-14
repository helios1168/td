# Scorecard: w8-50-filight-wide (contig arm1, instance_descaled_usd.json.gz)

**Verdict: fail**

| check | status | summary |
|---|---|---|
| one owner per cell | pass | 166500 cells, 0 with other than one owner, 0 not placed with no opportunity |
| district count per channel | pass | 4 channels, 0 off K |
| dropped for zero opportunity | pass | no cells dropped |
| final bands on drawn mass | pass | 50 districts, 0 outside the final tolerance |
| phantom shares | pass | 153 reported shares compared with the ledger, 0 not backed |
| planned against drawn owners | listed | 3 listed |
| mode compliance | pass | 0 violations, 0 metro exceptions, 0 units with zero-opportunity ZCTAs owned across them |
| ZIP contiguity | listed | 2 districts in pieces, 2 pieces, 0 ZIPs not in the graph |
| M1 polygon contiguity | fail | 2 districts in pieces, 2 detached pieces (largest 0.421 τ), 8 necks, 0 channel ZCTAs with no owner, 0 (ZCTA, fine channel) cells with no row, 0 owned twice, 16 mass necks listed beside M1 |
| geography manifest is 2025 | pass | 18 sources, all 2025 |
| solver status, bound and gap | listed | 4 channels |
| certificate tier | pass | weakest tier: exact |
| one name per district | pass | 50 districts |
| rep labels | pass | blank, as OD3 (#58) decides |

## planned against drawn owners

- FI/IL/FI_02: planned share 0.161172 drawn as no ZIPs (C8)
- WH/VA/WH_05: planned share 0.230111 drawn as no ZIPs (C8)
- national/IL/national_12: planned share 0.18042 drawn as no ZIPs (C8)

## ZIP contiguity

- FI/FI_06: piece of 288 ZIPs, 0.397 of the district's mass, cause corridor
- FI/FI_14: piece of 963 ZIPs, 0.403 of the district's mass, cause corridor

## M1 polygon contiguity

- FI/FI_06: detached piece of 288 ZIPs (06001...), 0.421 τ, cause corridor
- FI/FI_14: detached piece of 963 ZIPs (15001...), 0.395 τ, cause corridor
- FI/FI_05: neck 5.96 km wide cuts off 245 ZIPs (93067...), 6.7% of its land area and 35.3% of its mass; cut 94115-94129 0.26 km, 94118-94129 2.82 km, 94121-94129 1.12 km, 94123-94129 1.77 km
- FI/FI_06: neck 1.12 km wide cuts off 428 ZIPs (07001...), 45.8% of its land area and 60.3% of its mass; cut 11214-11224 1.12 km
- FI/FI_14: neck 0.43 km wide cuts off 962 ZIPs (15001...), 35.1% of its land area and 40.3% of its mass; cut 15315-15349 0.43 km
- WH/WH_05: neck 5.50 km wide cuts off 266 ZIPs (07003...), 15.6% of its land area and 30.1% of its mass; cut 08505-08610 4.74 km, 08505-08611 0.76 km
- national/national_03: neck 5.48 km wide cuts off 203 ZIPs (82930...), 15.7% of its land area and 26.2% of its mass; cut 84621-84652 4.19 km, 84621-84654 1.29 km
- national/national_04: neck 8.81 km wide cuts off 5 ZIPs (93527...), 6.3% of its land area and 0.0% of its mass; cut 93527-93554 8.81 km
- national/national_05: neck 8.12 km wide cuts off 4 ZIPs (92328...), 9.1% of its land area and 0.0% of its mass; cut 92384-92389 8.12 km
- national/national_15: neck 0.00 km wide cuts off 162 ZIPs (10001...), 8.6% of its land area and 91.0% of its mass; cut 12508-12550 0.00 km
- FI/FI_05: mass neck (diagnostic, not M1) 5.96 km wide cuts off 245 ZIPs (93067...), 6.7% of its land area and 35.3% of its mass; cut 94115-94129 0.26 km, 94118-94129 2.82 km, 94121-94129 1.12 km, 94123-94129 1.77 km
- FI/FI_06: mass neck (diagnostic, not M1) 1.11 km wide cuts off 287 ZIPs (06001...), 54.2% of its land area and 39.7% of its mass; cut 06371-06376 1.11 km
- FI/FI_14: mass neck (diagnostic, not M1) 0.43 km wide cuts off 962 ZIPs (15001...), 35.1% of its land area and 40.3% of its mass; cut 15315-15349 0.43 km
- FI/FI_15: mass neck (diagnostic, not M1) 7.80 km wide cuts off 9 ZIPs (28202...), 0.0% of its land area and 6.5% of its mass; cut 28202-28206 3.41 km, 28204-28205 3.52 km, 28204-28206 0.56 km, 28205-28207 0.31 km
- FI/FI_16: mass neck (diagnostic, not M1) 3.94 km wide cuts off 11 ZIPs (10017...), 0.0% of its land area and 9.9% of its mass; cut 10016-10017 1.60 km, 10017-10018 0.16 km, 10017-10020 0.08 km, 10017-10022 1.45 km, 10017-10036 0.32 km, 10017-10110 0.09 km, ...
- WH/WH_01: mass neck (diagnostic, not M1) 0.40 km wide cuts off 1 ZIPs (70163...), 0.0% of its land area and 6.7% of its mass; cut 70112-70163 0.07 km, 70113-70163 0.33 km
- WH/WH_03: mass neck (diagnostic, not M1) 9.82 km wide cuts off 2 ZIPs (94104...), 0.0% of its land area and 6.3% of its mass; cut 94104-94105 0.52 km, 94104-94108 0.66 km, 94105-94111 6.60 km, 94108-94111 0.36 km, 94111-94133 1.67 km
- WH/WH_04: mass neck (diagnostic, not M1) 6.82 km wide cuts off 16 ZIPs (10001...), 0.0% of its land area and 6.5% of its mass; cut 10001-10010 0.58 km, 10001-10011 1.99 km, 10001-10016 0.64 km, 10016-10017 1.60 km, 10016-10018 0.39 km, 10017-10022 1.45 km, ...
- WH/WH_05: mass neck (diagnostic, not M1) 5.50 km wide cuts off 266 ZIPs (07003...), 15.6% of its land area and 30.1% of its mass; cut 08505-08610 4.74 km, 08505-08611 0.76 km
- WH/WH_07: mass neck (diagnostic, not M1) 5.10 km wide cuts off 1 ZIPs (60606...), 0.0% of its land area and 14.0% of its mass; cut 60601-60606 0.28 km, 60602-60606 0.28 km, 60603-60606 0.29 km, 60604-60606 0.28 km, 60606-60607 1.29 km, 60606-60654 1.00 km, ...
- WH/WH_11: mass neck (diagnostic, not M1) 1.81 km wide cuts off 22 ZIPs (10019...), 0.0% of its land area and 19.8% of its mass; cut 10452-10453 1.81 km
- WH/WH_12: mass neck (diagnostic, not M1) 7.17 km wide cuts off 1 ZIPs (19103...), 0.0% of its land area and 7.3% of its mass; cut 19102-19103 2.23 km, 19103-19104 1.26 km, 19103-19130 1.54 km, 19103-19146 2.14 km
- national/national_03: mass neck (diagnostic, not M1) 5.48 km wide cuts off 203 ZIPs (82930...), 15.7% of its land area and 26.2% of its mass; cut 84621-84652 4.19 km, 84621-84654 1.29 km
- national/national_04: mass neck (diagnostic, not M1) 0.16 km wide cuts off 4 ZIPs (94104...), 0.0% of its land area and 6.0% of its mass; cut 94103-94108 0.16 km
- national/national_08: mass neck (diagnostic, not M1) 9.49 km wide cuts off 3032 ZIPs (01001...), 98.7% of its land area and 41.2% of its mass; cut 10464-10475 0.27 km, 10475-10803 0.39 km, 11939-11957 7.95 km, 11957-11965 0.88 km
- national/national_15: mass neck (diagnostic, not M1) 0.00 km wide cuts off 210 ZIPs (10901...), 91.4% of its land area and 9.0% of its mass; cut 12508-12550 0.00 km

## solver status, bound and gap

- FI: status optimal, objective 7100.788409392868, bound 7100.788409392868, gap 0, tier exact
- WH: status optimal, objective 6883.50682369453, bound 6883.50682369453, gap 0, tier exact
- WIFI: status optimal, objective 1549.9296713965784, bound 1549.9296713965784, gap 0, tier exact
- national: status optimal, objective 6029.253647600414, bound 6029.253647600414, gap 0, tier exact

## certificate tier

- FI: exact
- WH: exact
- WIFI: exact
- national: exact
