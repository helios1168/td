# Scorecard: w1-48-wide (contig arm1 + window repair, w1-48-wide #124 C round 1)

**Verdict: fail**

| check | status | summary |
|---|---|---|
| one owner per cell | pass | 166500 cells, 0 with other than one owner, 0 not placed with no opportunity |
| district count per channel | pass | 1 channels, 0 off K |
| dropped for zero opportunity | pass | no cells dropped |
| final bands on drawn mass | pass | 48 districts, 0 outside the final tolerance |
| phantom shares | pass | 76 reported shares compared with the ledger, 0 not backed |
| planned against drawn owners | listed | 4 listed |
| mode compliance | pass | 0 violations, 0 metro exceptions, 0 units with zero-opportunity ZCTAs owned across them |
| ZIP contiguity | listed | 1 districts in pieces, 1 pieces, 0 ZIPs not in the graph |
| M1 polygon contiguity | fail | 1 districts in pieces, 1 detached pieces (largest 0.578 τ), 4 necks, 0 channel ZCTAs with no owner, 0 (ZCTA, fine channel) cells with no row, 0 owned twice, 20 mass necks listed beside M1 |
| geography manifest is 2025 | pass | 18 sources, all 2025 |
| solver status, bound and gap | listed | 1 channels |
| certificate tier | pass | weakest tier: exact |
| one name per district | pass | 48 districts |
| rep labels | pass | blank, as OD3 (#58) decides |

## planned against drawn owners

- WIFI/MA/WIFI_11: planned share 0.1064 drawn as no ZIPs (C8)
- WIFI/MI/WIFI_24: planned share 0.0823698 drawn as no ZIPs (C8)
- WIFI/MO/WIFI_19: planned share 0.306266 drawn as no ZIPs (C8)
- WIFI/MI/WIFI_23: extra owner from repair in a free unit

## ZIP contiguity

- WIFI/WIFI_35: piece of 580 ZIPs, 0.438 of the district's mass, cause shape

## M1 polygon contiguity

- WIFI/WIFI_35: detached piece of 580 ZIPs (13020...), 0.578 τ, cause shape
- WIFI/WIFI_13: neck 0.76 km wide cuts off 103 ZIPs (07004...), 12.0% of its land area and 39.7% of its mass; cut 08505-08611 0.76 km
- WIFI/WIFI_31: neck 1.30 km wide cuts off 27 ZIPs (07717...), 27.3% of its land area and 8.8% of its mass; cut 07717-07720 1.30 km
- WIFI/WIFI_32: neck 1.97 km wide cuts off 40 ZIPs (07438...), 31.5% of its land area and 2.3% of its mass; cut 08628-08638 1.97 km
- WIFI/WIFI_46: neck 6.14 km wide cuts off 44 ZIPs (79734...), 6.0% of its land area and 6.7% of its mass; cut 79718-79734 6.14 km
- WIFI/WIFI_01: mass neck (diagnostic, not M1) 5.86 km wide cuts off 1 ZIPs (30326...), 0.0% of its land area and 6.5% of its mass; cut 30305-30326 3.40 km, 30326-30342 2.46 km
- WIFI/WIFI_05: mass neck (diagnostic, not M1) 7.81 km wide cuts off 4 ZIPs (94104...), 0.1% of its land area and 8.6% of its mass; cut 94103-94105 0.89 km, 94104-94108 0.66 km, 94105-94107 2.28 km, 94105-94109 0.62 km, 94105-94133 1.32 km, 94108-94111 0.36 km, ...
- WIFI/WIFI_06: mass neck (diagnostic, not M1) 8.56 km wide cuts off 1 ZIPs (90212...), 0.1% of its land area and 5.4% of its mass; cut 90024-90212 0.36 km, 90035-90212 2.30 km, 90067-90212 1.63 km, 90210-90212 3.02 km, 90211-90212 1.25 km
- WIFI/WIFI_07: mass neck (diagnostic, not M1) 3.49 km wide cuts off 1 ZIPs (91101...), 0.0% of its land area and 12.0% of its mass; cut 91101-91103 1.91 km, 91101-91104 1.59 km
- WIFI/WIFI_09: mass neck (diagnostic, not M1) 6.67 km wide cuts off 1 ZIPs (92614...), 0.4% of its land area and 8.1% of its mass; cut 92606-92614 5.00 km, 92614-92705 1.67 km
- WIFI/WIFI_12: mass neck (diagnostic, not M1) 5.73 km wide cuts off 4 ZIPs (20006...), 0.0% of its land area and 21.9% of its mass; cut 20005-20006 0.60 km, 20006-20024 0.34 km, 20006-20036 1.28 km, 20006-20037 0.68 km, 20006-20052 0.80 km, 20006-20220 0.37 km, ...
- WIFI/WIFI_13: mass neck (diagnostic, not M1) 0.76 km wide cuts off 103 ZIPs (07004...), 12.0% of its land area and 39.7% of its mass; cut 08505-08611 0.76 km
- WIFI/WIFI_21: mass neck (diagnostic, not M1) 5.10 km wide cuts off 1 ZIPs (60606...), 0.0% of its land area and 17.3% of its mass; cut 60601-60606 0.28 km, 60602-60606 0.28 km, 60603-60606 0.29 km, 60604-60606 0.28 km, 60606-60607 1.29 km, 60606-60654 1.00 km, ...
- WIFI/WIFI_24: mass neck (diagnostic, not M1) 4.40 km wide cuts off 16 ZIPs (47613...), 1.2% of its land area and 7.7% of its mass; cut 42420-47713 2.05 km, 42420-47715 2.36 km
- WIFI/WIFI_25: mass neck (diagnostic, not M1) 0.40 km wide cuts off 1 ZIPs (70163...), 0.0% of its land area and 6.3% of its mass; cut 70112-70163 0.07 km, 70113-70163 0.33 km
- WIFI/WIFI_31: mass neck (diagnostic, not M1) 1.30 km wide cuts off 27 ZIPs (07717...), 27.3% of its land area and 8.8% of its mass; cut 07717-07720 1.30 km
- WIFI/WIFI_32: mass neck (diagnostic, not M1) 3.09 km wide cuts off 20 ZIPs (07009...), 1.7% of its land area and 6.8% of its mass; cut 07009-07042 0.21 km, 07042-07043 2.88 km
- WIFI/WIFI_35: mass neck (diagnostic, not M1) 2.25 km wide cuts off 9 ZIPs (10017...), 0.0% of its land area and 21.2% of its mass; cut 10016-10017 1.60 km, 10017-10018 0.16 km, 10017-10036 0.32 km, 10017-10110 0.09 km, 10036-10173 0.08 km
- WIFI/WIFI_35: mass neck (diagnostic, not M1) 0.78 km wide cuts off 579 ZIPs (13020...), 99.6% of its land area and 43.8% of its mass; cut 14301-14302 0.78 km
- WIFI/WIFI_36: mass neck (diagnostic, not M1) 4.01 km wide cuts off 5 ZIPs (10019...), 0.3% of its land area and 11.0% of its mass; cut 10019-10022 0.57 km, 10019-10023 2.61 km, 10019-10065 0.52 km, 10019-10153 0.08 km, 10022-10103 0.08 km, 10022-10111 0.08 km, ...
- WIFI/WIFI_40: mass neck (diagnostic, not M1) 7.17 km wide cuts off 1 ZIPs (19103...), 0.0% of its land area and 10.5% of its mass; cut 19102-19103 2.23 km, 19103-19104 1.26 km, 19103-19130 1.54 km, 19103-19146 2.14 km
- WIFI/WIFI_42: mass neck (diagnostic, not M1) 8.26 km wide cuts off 1 ZIPs (18101...), 0.0% of its land area and 5.3% of its mass; cut 18101-18102 8.26 km
- WIFI/WIFI_46: mass neck (diagnostic, not M1) 3.33 km wide cuts off 32 ZIPs (79821...), 1.2% of its land area and 6.7% of its mass; cut 79839-79853 3.33 km
- WIFI/WIFI_47: mass neck (diagnostic, not M1) 2.91 km wide cuts off 1 ZIPs (24011...), 0.0% of its land area and 5.9% of its mass; cut 24011-24013 0.92 km, 24011-24016 1.99 km
- WIFI/WIFI_48: mass neck (diagnostic, not M1) 8.45 km wide cuts off 1 ZIPs (53202...), 0.0% of its land area and 7.2% of its mass; cut 53202-53203 1.59 km, 53202-53204 1.05 km, 53202-53207 1.07 km, 53202-53211 2.31 km, 53202-53212 2.43 km

## solver status, bound and gap

- WIFI: status optimal, objective 6325.12148078099, bound 6325.12148078099, gap 0, tier exact

## certificate tier

- WIFI: exact
