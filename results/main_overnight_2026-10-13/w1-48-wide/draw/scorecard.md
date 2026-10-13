# Scorecard: w1-48-wide (contig arm1, instance_descaled_usd.json.gz)

**Verdict: fail**

| check | status | summary |
|---|---|---|
| one owner per cell | pass | 166500 cells, 0 with other than one owner, 0 not placed with no opportunity |
| district count per channel | pass | 1 channels, 0 off K |
| dropped for zero opportunity | pass | no cells dropped |
| final bands on drawn mass | pass | 48 districts, 0 outside the final tolerance |
| phantom shares | pass | 77 reported shares compared with the ledger, 0 not backed |
| planned against drawn owners | listed | 6 listed |
| mode compliance | pass | 0 violations, 0 metro exceptions, 0 units with zero-opportunity ZCTAs owned across them |
| ZIP contiguity | listed | 3 districts in pieces, 4 pieces, 0 ZIPs not in the graph |
| M1 polygon contiguity | fail | 3 districts in pieces, 4 detached pieces (largest 0.438 τ), 3 necks, 0 channel ZCTAs with no owner, 0 (ZCTA, fine channel) cells with no row, 0 owned twice, 19 mass necks listed beside M1 |
| geography manifest is 2025 | pass | 18 sources, all 2025 |
| solver status, bound and gap | listed | 1 channels |
| certificate tier | pass | weakest tier: exact |
| one name per district | pass | 48 districts |
| rep labels | pass | blank, as OD3 (#58) decides |

## planned against drawn owners

- WIFI/MA/WIFI_11: planned share 0.1064 drawn as no ZIPs (C8)
- WIFI/MD/WIFI_12: planned share 0.05 drawn as no ZIPs (C8)
- WIFI/MI/WIFI_23: planned share 0.208192 drawn as no ZIPs (C8)
- WIFI/MO/WIFI_18: planned share 0.306266 drawn as no ZIPs (C8)
- WIFI/MI/WIFI_22: extra owner from repair in a free unit
- WIFI/NY/WIFI_31: extra owner from repair in a free unit

## ZIP contiguity

- WIFI/WIFI_12: piece of 57 ZIPs, 0.39 of the district's mass, cause corridor
- WIFI/WIFI_34: piece of 4 ZIPs, 0.165 of the district's mass, cause shape
- WIFI/WIFI_34: piece of 1 ZIPs, 0.00891 of the district's mass, cause shape
- WIFI/WIFI_35: piece of 36 ZIPs, 0.431 of the district's mass, cause shape

## M1 polygon contiguity

- WIFI/WIFI_12: detached piece of 57 ZIPs (20001...), 0.334 τ, cause corridor
- WIFI/WIFI_34: detached piece of 4 ZIPs (11214...), 0.178 τ, cause shape
- WIFI/WIFI_34: detached piece of 1 ZIPs (11226...), 0.00961 τ, cause shape
- WIFI/WIFI_35: detached piece of 36 ZIPs (10001...), 0.438 τ, cause shape
- WIFI/WIFI_12: neck 3.34 km wide cuts off 59 ZIPs (08002...), 17.8% of its land area and 37.5% of its mass; cut 08023-08069 3.34 km
- WIFI/WIFI_36: neck 0.16 km wide cuts off 73 ZIPs (10002...), 33.1% of its land area and 79.3% of its mass; cut 11414-11420 0.16 km
- WIFI/WIFI_46: neck 6.14 km wide cuts off 44 ZIPs (79734...), 6.0% of its land area and 6.7% of its mass; cut 79718-79734 6.14 km
- WIFI/WIFI_01: mass neck (diagnostic, not M1) 5.86 km wide cuts off 1 ZIPs (30326...), 0.0% of its land area and 6.5% of its mass; cut 30305-30326 3.40 km, 30326-30342 2.46 km
- WIFI/WIFI_05: mass neck (diagnostic, not M1) 7.81 km wide cuts off 4 ZIPs (94104...), 0.1% of its land area and 8.6% of its mass; cut 94103-94105 0.89 km, 94104-94108 0.66 km, 94105-94107 2.28 km, 94105-94109 0.62 km, 94105-94133 1.32 km, 94108-94111 0.36 km, ...
- WIFI/WIFI_06: mass neck (diagnostic, not M1) 8.56 km wide cuts off 1 ZIPs (90212...), 0.1% of its land area and 5.4% of its mass; cut 90024-90212 0.36 km, 90035-90212 2.30 km, 90067-90212 1.63 km, 90210-90212 3.02 km, 90211-90212 1.25 km
- WIFI/WIFI_07: mass neck (diagnostic, not M1) 3.49 km wide cuts off 1 ZIPs (91101...), 0.0% of its land area and 12.0% of its mass; cut 91101-91103 1.91 km, 91101-91104 1.59 km
- WIFI/WIFI_09: mass neck (diagnostic, not M1) 6.67 km wide cuts off 1 ZIPs (92614...), 0.4% of its land area and 8.1% of its mass; cut 92606-92614 5.00 km, 92614-92705 1.67 km
- WIFI/WIFI_12: mass neck (diagnostic, not M1) 3.34 km wide cuts off 69 ZIPs (08023...), 79.7% of its land area and 23.5% of its mass; cut 08023-08069 3.34 km
- WIFI/WIFI_12: mass neck (diagnostic, not M1) 0.49 km wide cuts off 56 ZIPs (20001...), 2.5% of its land area and 39.0% of its mass; cut 20024-20204 0.49 km
- WIFI/WIFI_20: mass neck (diagnostic, not M1) 5.10 km wide cuts off 1 ZIPs (60606...), 0.0% of its land area and 17.3% of its mass; cut 60601-60606 0.28 km, 60602-60606 0.28 km, 60603-60606 0.29 km, 60604-60606 0.28 km, 60606-60607 1.29 km, 60606-60654 1.00 km, ...
- WIFI/WIFI_24: mass neck (diagnostic, not M1) 0.40 km wide cuts off 1 ZIPs (70163...), 0.0% of its land area and 6.3% of its mass; cut 70112-70163 0.07 km, 70113-70163 0.33 km
- WIFI/WIFI_26: mass neck (diagnostic, not M1) 8.61 km wide cuts off 1 ZIPs (21031...), 0.0% of its land area and 6.3% of its mass; cut 21030-21031 8.61 km
- WIFI/WIFI_34: mass neck (diagnostic, not M1) 1.12 km wide cuts off 3 ZIPs (11224...), 1.0% of its land area and 13.0% of its mass; cut 11214-11224 1.12 km
- WIFI/WIFI_35: mass neck (diagnostic, not M1) 0.35 km wide cuts off 35 ZIPs (10001...), 0.4% of its land area and 42.5% of its mass; cut 10005-10271 0.28 km, 10006-10271 0.06 km
- WIFI/WIFI_36: mass neck (diagnostic, not M1) 0.16 km wide cuts off 47 ZIPs (11004...), 66.9% of its land area and 20.7% of its mass; cut 11414-11420 0.16 km
- WIFI/WIFI_37: mass neck (diagnostic, not M1) 1.57 km wide cuts off 33 ZIPs (11103...), 0.2% of its land area and 14.4% of its mass; cut 11357-11358 1.57 km
- WIFI/WIFI_40: mass neck (diagnostic, not M1) 7.17 km wide cuts off 1 ZIPs (19103...), 0.0% of its land area and 10.5% of its mass; cut 19102-19103 2.23 km, 19103-19104 1.26 km, 19103-19130 1.54 km, 19103-19146 2.14 km
- WIFI/WIFI_42: mass neck (diagnostic, not M1) 8.26 km wide cuts off 1 ZIPs (18101...), 0.0% of its land area and 5.3% of its mass; cut 18101-18102 8.26 km
- WIFI/WIFI_46: mass neck (diagnostic, not M1) 3.33 km wide cuts off 32 ZIPs (79821...), 1.2% of its land area and 6.7% of its mass; cut 79839-79853 3.33 km
- WIFI/WIFI_47: mass neck (diagnostic, not M1) 2.91 km wide cuts off 1 ZIPs (24011...), 0.0% of its land area and 5.9% of its mass; cut 24011-24013 0.92 km, 24011-24016 1.99 km
- WIFI/WIFI_48: mass neck (diagnostic, not M1) 8.45 km wide cuts off 1 ZIPs (53202...), 0.0% of its land area and 7.2% of its mass; cut 53202-53203 1.59 km, 53202-53204 1.05 km, 53202-53207 1.07 km, 53202-53211 2.31 km, 53202-53212 2.43 km

## solver status, bound and gap

- WIFI: status optimal, objective 6306.820171209256, bound 6306.820171209256, gap 0, tier exact

## certificate tier

- WIFI: exact
