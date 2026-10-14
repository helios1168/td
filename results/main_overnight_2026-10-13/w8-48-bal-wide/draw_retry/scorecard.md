# Scorecard: w8-48-bal-wide (contig arm1, instance_descaled_usd.json.gz)

**Verdict: fail**

| check | status | summary |
|---|---|---|
| one owner per cell | pass | 166500 cells, 0 with other than one owner, 0 not placed with no opportunity |
| district count per channel | pass | 4 channels, 0 off K |
| dropped for zero opportunity | pass | no cells dropped |
| final bands on drawn mass | fail | 48 districts, 2 outside the final tolerance |
| phantom shares | pass | 156 reported shares compared with the ledger, 0 not backed |
| planned against drawn owners | listed | 4 listed |
| mode compliance | pass | 0 violations, 0 metro exceptions, 0 units with zero-opportunity ZCTAs owned across them |
| ZIP contiguity | listed | 2 districts in pieces, 2 pieces, 0 ZIPs not in the graph |
| M1 polygon contiguity | fail | 2 districts in pieces, 2 detached pieces (largest 0.441 τ), 6 necks, 0 channel ZCTAs with no owner, 0 (ZCTA, fine channel) cells with no row, 0 owned twice, 15 mass necks listed beside M1 |
| geography manifest is 2025 | pass | 18 sources, all 2025 |
| solver status, bound and gap | listed | 4 channels |
| certificate tier | pass | weakest tier: exact |
| one name per district | pass | 48 districts |
| rep labels | pass | blank, as OD3 (#58) decides |

## final bands on drawn mass

- FI/FI_05: drawn 699.226 outside [765.076, 1019.57]; undrawn share of CA
- FI/FI_13: drawn 693.064 outside [765.076, 1019.57]; undrawn share of IN, OH

## planned against drawn owners

- FI/AR/FI_01: planned share 0.430389 drawn as no ZIPs (C8)
- WH/NY/WH_05: planned share 0.0928015 drawn as no ZIPs (C8)
- national/IL/national_12: planned share 0.0976766 drawn as no ZIPs (C8)
- national/OH/national_08: planned share 0.365831 drawn as no ZIPs (C8)

## ZIP contiguity

- FI/FI_06: piece of 288 ZIPs, 0.43 of the district's mass, cause corridor
- WH/WH_05: piece of 288 ZIPs, 0.275 of the district's mass, cause corridor

## M1 polygon contiguity

- FI/FI_06: detached piece of 288 ZIPs (06001...), 0.441 τ, cause corridor
- WH/WH_05: detached piece of 288 ZIPs (06001...), 0.283 τ, cause corridor
- FI/FI_06: neck 0.40 km wide cuts off 365 ZIPs (07001...), 37.2% of its land area and 57.0% of its mass; cut 07846-07860 0.40 km
- WH/WH_05: neck 1.11 km wide cuts off 287 ZIPs (06001...), 39.8% of its land area and 27.5% of its mass; cut 06371-06376 1.11 km
- national/national_03: neck 5.48 km wide cuts off 203 ZIPs (82930...), 13.4% of its land area and 15.0% of its mass; cut 84621-84652 4.19 km, 84621-84654 1.29 km
- national/national_04: neck 8.81 km wide cuts off 5 ZIPs (93527...), 5.9% of its land area and 0.0% of its mass; cut 93527-93554 8.81 km
- national/national_05: neck 9.08 km wide cuts off 2 ZIPs (91759...), 6.1% of its land area and 1.6% of its mass; cut 91750-91759 9.08 km
- national/national_09: neck 5.67 km wide cuts off 597 ZIPs (07001...), 38.7% of its land area and 78.6% of its mass; cut 08023-08069 3.34 km, 08023-08070 2.33 km
- FI/FI_05: mass neck (diagnostic, not M1) 5.96 km wide cuts off 68 ZIPs (94002...), 0.4% of its land area and 16.0% of its mass; cut 94115-94129 0.26 km, 94118-94129 2.82 km, 94121-94129 1.12 km, 94123-94129 1.77 km
- FI/FI_06: mass neck (diagnostic, not M1) 1.11 km wide cuts off 287 ZIPs (06001...), 62.8% of its land area and 43.0% of its mass; cut 06371-06376 1.11 km
- FI/FI_06: mass neck (diagnostic, not M1) 2.64 km wide cuts off 61 ZIPs (07701...), 7.9% of its land area and 9.5% of its mass; cut 08832-08879 0.82 km, 08861-08879 1.82 km
- FI/FI_17: mass neck (diagnostic, not M1) 3.94 km wide cuts off 11 ZIPs (10017...), 0.0% of its land area and 9.9% of its mass; cut 10016-10017 1.60 km, 10017-10018 0.16 km, 10017-10020 0.08 km, 10017-10022 1.45 km, 10017-10036 0.32 km, 10017-10110 0.09 km, ...
- WH/WH_02: mass neck (diagnostic, not M1) 0.40 km wide cuts off 1 ZIPs (70163...), 0.0% of its land area and 5.2% of its mass; cut 70112-70163 0.07 km, 70113-70163 0.33 km
- WH/WH_04: mass neck (diagnostic, not M1) 5.55 km wide cuts off 2 ZIPs (90067...), 0.0% of its land area and 7.0% of its mass; cut 90024-90067 0.78 km, 90024-90212 0.36 km, 90025-90067 1.39 km, 90210-90212 3.02 km
- WH/WH_05: mass neck (diagnostic, not M1) 1.11 km wide cuts off 287 ZIPs (06001...), 39.8% of its land area and 27.5% of its mass; cut 06371-06376 1.11 km
- WH/WH_06: mass neck (diagnostic, not M1) 5.73 km wide cuts off 4 ZIPs (20006...), 0.0% of its land area and 20.3% of its mass; cut 20005-20006 0.60 km, 20006-20024 0.34 km, 20006-20036 1.28 km, 20006-20037 0.68 km, 20006-20052 0.80 km, 20006-20220 0.37 km, ...
- WH/WH_08: mass neck (diagnostic, not M1) 5.10 km wide cuts off 1 ZIPs (60606...), 0.0% of its land area and 13.4% of its mass; cut 60601-60606 0.28 km, 60602-60606 0.28 km, 60603-60606 0.29 km, 60604-60606 0.28 km, 60606-60607 1.29 km, 60606-60654 1.00 km, ...
- WH/WH_10: mass neck (diagnostic, not M1) 5.27 km wide cuts off 13 ZIPs (10017...), 0.0% of its land area and 5.4% of its mass; cut 10016-10017 1.60 km, 10017-10018 0.16 km, 10017-10022 1.45 km, 10017-10036 0.32 km, 10017-10110 0.09 km, 10019-10020 0.71 km, ...
- WH/WH_11: mass neck (diagnostic, not M1) 7.17 km wide cuts off 1 ZIPs (19103...), 0.0% of its land area and 7.3% of its mass; cut 19102-19103 2.23 km, 19103-19104 1.26 km, 19103-19130 1.54 km, 19103-19146 2.14 km
- national/national_03: mass neck (diagnostic, not M1) 5.48 km wide cuts off 203 ZIPs (82930...), 13.4% of its land area and 15.0% of its mass; cut 84621-84652 4.19 km, 84621-84654 1.29 km
- national/national_07: mass neck (diagnostic, not M1) 7.75 km wide cuts off 18 ZIPs (11203...), 0.1% of its land area and 15.9% of its mass; cut 11207-11212 2.26 km, 11207-11233 2.13 km, 11207-11236 1.27 km, 11236-11239 2.09 km
- national/national_09: mass neck (diagnostic, not M1) 5.67 km wide cuts off 546 ZIPs (08023...), 61.3% of its land area and 21.4% of its mass; cut 08023-08069 3.34 km, 08023-08070 2.33 km
- national/national_13: mass neck (diagnostic, not M1) 3.94 km wide cuts off 11 ZIPs (10017...), 0.0% of its land area and 16.3% of its mass; cut 10016-10017 1.60 km, 10017-10018 0.16 km, 10017-10020 0.08 km, 10017-10022 1.45 km, 10017-10036 0.32 km, 10017-10110 0.09 km, ...

## solver status, bound and gap

- FI: status optimal, objective 7071.320871784333, bound 7071.320871784333, gap 0, tier exact
- WH: status optimal, objective 6437.71876600095, bound 6437.71876600095, gap 0, tier exact
- WIFI: status optimal, objective 1549.9296713965784, bound 1549.9296713965784, gap 0, tier exact
- national: status optimal, objective 6771.969056768514, bound 6771.969056768514, gap 0, tier exact

## certificate tier

- FI: exact
- WH: exact
- WIFI: exact
- national: exact
