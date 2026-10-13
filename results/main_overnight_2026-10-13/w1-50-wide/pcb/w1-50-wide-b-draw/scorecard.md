# Scorecard: w1-50-wide (contig arm1, instance_descaled_usd.json.gz)

**Verdict: fail**

| check | status | summary |
|---|---|---|
| one owner per cell | pass | 166500 cells, 0 with other than one owner, 0 not placed with no opportunity |
| district count per channel | pass | 1 channels, 0 off K |
| dropped for zero opportunity | pass | no cells dropped |
| final bands on drawn mass | pass | 50 districts, 0 outside the final tolerance |
| phantom shares | pass | 84 reported shares compared with the ledger, 0 not backed |
| planned against drawn owners | listed | 8 listed |
| mode compliance | pass | 0 violations, 0 metro exceptions, 0 units with zero-opportunity ZCTAs owned across them |
| ZIP contiguity | listed | 6 districts in pieces, 7 pieces, 0 ZIPs not in the graph |
| M1 polygon contiguity | fail | 6 districts in pieces, 7 detached pieces (largest 0.348 τ), 11 necks, 0 channel ZCTAs with no owner, 0 (ZCTA, fine channel) cells with no row, 0 owned twice, 29 mass necks listed beside M1 |
| geography manifest is 2025 | pass | 18 sources, all 2025 |
| solver status, bound and gap | listed | 1 channels |
| certificate tier | pass | weakest tier: exact |
| one name per district | pass | 50 districts |
| rep labels | pass | blank, as OD3 (#58) decides |

## planned against drawn owners

- WIFI/CT/WIFI_13: planned share 0.05 drawn as no ZIPs (C8)
- WIFI/MD/WIFI_14: planned share 0.05 drawn as no ZIPs (C8)
- WIFI/MI/WIFI_25: planned share 0.140328 drawn as no ZIPs (C8)
- WIFI/MI/WIFI_23: extra owner from repair in a free unit
- WIFI/MI/WIFI_41: extra owner from repair in a free unit
- WIFI/NY/WIFI_12: extra owner from repair in a free unit
- WIFI/SC/WIFI_18: extra owner from repair in a free unit
- WIFI/TX/WIFI_26: extra owner from repair in a free unit

## ZIP contiguity

- WIFI/WIFI_07: piece of 7 ZIPs, 0.0553 of the district's mass, cause shape
- WIFI/WIFI_08: piece of 32 ZIPs, 0.00329 of the district's mass, cause shape
- WIFI/WIFI_13: piece of 81 ZIPs, 0.348 of the district's mass, cause corridor
- WIFI/WIFI_13: piece of 1 ZIPs, 0.0352 of the district's mass, cause shape
- WIFI/WIFI_14: piece of 57 ZIPs, 0.278 of the district's mass, cause corridor
- WIFI/WIFI_37: piece of 32 ZIPs, 0.354 of the district's mass, cause shape
- WIFI/WIFI_48: piece of 34 ZIPs, 0.0197 of the district's mass, cause shape

## M1 polygon contiguity

- WIFI/WIFI_07: detached piece of 7 ZIPs (91711...), 0.0574 τ, cause shape
- WIFI/WIFI_08: detached piece of 32 ZIPs (95410...), 0.00345 τ, cause shape
- WIFI/WIFI_13: detached piece of 81 ZIPs (02802...), 0.23 τ, cause corridor
- WIFI/WIFI_13: detached piece of 1 ZIPs (11797...), 0.0233 τ, cause shape
- WIFI/WIFI_14: detached piece of 57 ZIPs (20001...), 0.348 τ, cause corridor
- WIFI/WIFI_37: detached piece of 32 ZIPs (10001...), 0.331 τ, cause shape
- WIFI/WIFI_48: detached piece of 34 ZIPs (78002...), 0.0205 τ, cause shape
- WIFI/WIFI_01: neck 5.38 km wide cuts off 288 ZIPs (29003...), 30.9% of its land area and 42.5% of its mass; cut 39819-39845 5.38 km
- WIFI/WIFI_06: neck 9.76 km wide cuts off 6 ZIPs (91702...), 32.1% of its land area and 0.1% of its mass; cut 91702-91706 5.19 km, 91702-91722 4.56 km
- WIFI/WIFI_08: neck 0.00 km wide cuts off 163 ZIPs (94005...), 33.8% of its land area and 97.8% of its mass; cut 94404-94545 0.00 km
- WIFI/WIFI_12: neck 8.82 km wide cuts off 97 ZIPs (11050...), 14.8% of its land area and 28.8% of its mass; cut 11939-11957 7.95 km, 11957-11965 0.88 km
- WIFI/WIFI_14: neck 1.64 km wide cuts off 170 ZIPs (17859...), 24.5% of its land area and 31.0% of its mass; cut 19112-19153 1.64 km
- WIFI/WIFI_20: neck 5.48 km wide cuts off 96 ZIPs (84511...), 6.5% of its land area and 6.6% of its mass; cut 84621-84652 4.19 km, 84621-84654 1.29 km
- WIFI/WIFI_34: neck 6.45 km wide cuts off 12 ZIPs (07823...), 5.8% of its land area and 0.1% of its mass; cut 08825-08848 6.45 km
- WIFI/WIFI_36: neck 6.08 km wide cuts off 32 ZIPs (11203...), 16.0% of its land area and 35.4% of its mass; cut 11414-11420 0.16 km, 11414-11430 2.00 km, 11416-11419 0.97 km, 11417-11419 0.98 km, 11417-11420 1.97 km
- WIFI/WIFI_38: neck 1.33 km wide cuts off 18 ZIPs (11020...), 42.5% of its land area and 11.0% of its mass; cut 11361-11365 0.13 km, 11364-11365 1.20 km
- WIFI/WIFI_43: neck 0.53 km wide cuts off 98 ZIPs (15012...), 8.9% of its land area and 22.5% of its mass; cut 15773-15775 0.38 km, 15775-16646 0.15 km
- WIFI/WIFI_44: neck 1.91 km wide cuts off 113 ZIPs (17003...), 10.7% of its land area and 44.6% of its mass; cut 16689-17229 1.91 km
- WIFI/WIFI_01: mass neck (diagnostic, not M1) 5.38 km wide cuts off 288 ZIPs (29003...), 30.9% of its land area and 42.5% of its mass; cut 39819-39845 5.38 km
- WIFI/WIFI_05: mass neck (diagnostic, not M1) 8.34 km wide cuts off 1 ZIPs (95113...), 0.0% of its land area and 7.9% of its mass; cut 95110-95113 4.21 km, 95112-95113 4.12 km
- WIFI/WIFI_06: mass neck (diagnostic, not M1) 5.18 km wide cuts off 1 ZIPs (90212...), 0.1% of its land area and 6.0% of its mass; cut 90035-90212 2.30 km, 90067-90212 1.63 km, 90211-90212 1.25 km
- WIFI/WIFI_07: mass neck (diagnostic, not M1) 6.09 km wide cuts off 7 ZIPs (91006...), 0.4% of its land area and 8.9% of its mass; cut 91006-91107 0.92 km, 91007-91107 2.33 km, 91024-91107 2.83 km
- WIFI/WIFI_08: mass neck (diagnostic, not M1) 1.94 km wide cuts off 1 ZIPs (94104...), 0.0% of its land area and 5.2% of its mass; cut 94104-94105 0.52 km, 94104-94108 0.66 km, 94104-94111 0.76 km
- WIFI/WIFI_09: mass neck (diagnostic, not M1) 0.27 km wide cuts off 4 ZIPs (92606...), 1.9% of its land area and 15.2% of its mass; cut 92701-92780 0.27 km
- WIFI/WIFI_12: mass neck (diagnostic, not M1) 8.82 km wide cuts off 97 ZIPs (11050...), 14.8% of its land area and 28.8% of its mass; cut 11939-11957 7.95 km, 11957-11965 0.88 km
- WIFI/WIFI_13: mass neck (diagnostic, not M1) 2.36 km wide cuts off 79 ZIPs (02802...), 2.2% of its land area and 34.8% of its mass; cut 02871-02878 2.36 km
- WIFI/WIFI_14: mass neck (diagnostic, not M1) 1.64 km wide cuts off 170 ZIPs (17859...), 24.5% of its land area and 31.0% of its mass; cut 19112-19153 1.64 km
- WIFI/WIFI_14: mass neck (diagnostic, not M1) 0.49 km wide cuts off 56 ZIPs (20001...), 0.6% of its land area and 27.8% of its mass; cut 20024-20204 0.49 km
- WIFI/WIFI_18: mass neck (diagnostic, not M1) 8.47 km wide cuts off 1 ZIPs (30326...), 0.0% of its land area and 7.1% of its mass; cut 30305-30326 3.40 km, 30319-30326 1.50 km, 30324-30326 1.11 km, 30326-30342 2.46 km
- WIFI/WIFI_20: mass neck (diagnostic, not M1) 3.86 km wide cuts off 52 ZIPs (84710...), 2.5% of its land area and 6.3% of its mass; cut 84740-84750 3.86 km
- WIFI/WIFI_21: mass neck (diagnostic, not M1) 5.10 km wide cuts off 1 ZIPs (60606...), 0.1% of its land area and 21.7% of its mass; cut 60601-60606 0.28 km, 60602-60606 0.28 km, 60603-60606 0.29 km, 60604-60606 0.28 km, 60606-60607 1.29 km, 60606-60654 1.00 km, ...
- WIFI/WIFI_25: mass neck (diagnostic, not M1) 5.81 km wide cuts off 26 ZIPs (45001...), 0.2% of its land area and 8.5% of its mass; cut 41011-45202 0.00 km, 41017-45204 4.63 km, 41071-45202 0.00 km, 41074-45202 0.10 km, 45202-45226 1.09 km
- WIFI/WIFI_26: mass neck (diagnostic, not M1) 0.40 km wide cuts off 1 ZIPs (70163...), 0.0% of its land area and 6.3% of its mass; cut 70112-70163 0.07 km, 70113-70163 0.33 km
- WIFI/WIFI_27: mass neck (diagnostic, not M1) 4.87 km wide cuts off 1 ZIPs (02110...), 0.0% of its land area and 5.3% of its mass; cut 02108-02110 0.21 km, 02109-02110 2.38 km, 02110-02111 0.92 km, 02110-02210 1.36 km
- WIFI/WIFI_28: mass neck (diagnostic, not M1) 8.61 km wide cuts off 1 ZIPs (21031...), 0.0% of its land area and 6.3% of its mass; cut 21030-21031 8.61 km
- WIFI/WIFI_30: mass neck (diagnostic, not M1) 3.20 km wide cuts off 1 ZIPs (55402...), 0.0% of its land area and 8.0% of its mass; cut 55401-55402 1.03 km, 55402-55403 1.30 km, 55402-55404 0.37 km, 55402-55415 0.50 km
- WIFI/WIFI_33: mass neck (diagnostic, not M1) 3.02 km wide cuts off 3 ZIPs (07302...), 0.3% of its land area and 6.7% of its mass; cut 07302-07305 3.02 km
- WIFI/WIFI_35: mass neck (diagnostic, not M1) 9.21 km wide cuts off 1 ZIPs (07078...), 0.5% of its land area and 7.5% of its mass; cut 07039-07078 5.57 km, 07052-07078 1.22 km, 07078-07932 2.43 km
- WIFI/WIFI_36: mass neck (diagnostic, not M1) 6.08 km wide cuts off 32 ZIPs (11203...), 16.0% of its land area and 35.4% of its mass; cut 11414-11420 0.16 km, 11414-11430 2.00 km, 11416-11419 0.97 km, 11417-11419 0.98 km, 11417-11420 1.97 km
- WIFI/WIFI_37: mass neck (diagnostic, not M1) 0.35 km wide cuts off 31 ZIPs (10001...), 0.3% of its land area and 34.8% of its mass; cut 10005-10271 0.28 km, 10006-10271 0.06 km
- WIFI/WIFI_38: mass neck (diagnostic, not M1) 1.33 km wide cuts off 18 ZIPs (11020...), 42.5% of its land area and 11.0% of its mass; cut 11361-11365 0.13 km, 11364-11365 1.20 km
- WIFI/WIFI_43: mass neck (diagnostic, not M1) 0.53 km wide cuts off 98 ZIPs (15012...), 8.9% of its land area and 22.5% of its mass; cut 15773-15775 0.38 km, 15775-16646 0.15 km
- WIFI/WIFI_44: mass neck (diagnostic, not M1) 0.23 km wide cuts off 45 ZIPs (17505...), 2.9% of its land area and 27.8% of its mass; cut 17505-17543 0.23 km
- WIFI/WIFI_46: mass neck (diagnostic, not M1) 3.68 km wide cuts off 4 ZIPs (75024...), 0.2% of its land area and 19.4% of its mass; cut 75069-75072 3.68 km
- WIFI/WIFI_48: mass neck (diagnostic, not M1) 3.77 km wide cuts off 1 ZIPs (78701...), 0.0% of its land area and 7.3% of its mass; cut 78701-78702 2.77 km, 78701-78712 0.99 km
- WIFI/WIFI_49: mass neck (diagnostic, not M1) 2.91 km wide cuts off 1 ZIPs (24011...), 0.0% of its land area and 5.9% of its mass; cut 24011-24013 0.92 km, 24011-24016 1.99 km
- WIFI/WIFI_50: mass neck (diagnostic, not M1) 8.45 km wide cuts off 1 ZIPs (53202...), 0.0% of its land area and 7.2% of its mass; cut 53202-53203 1.59 km, 53202-53204 1.05 km, 53202-53207 1.07 km, 53202-53211 2.31 km, 53202-53212 2.43 km

## solver status, bound and gap

- WIFI: status optimal, objective 6255.006403617547, bound 6255.006403617547, gap 0, tier exact

## certificate tier

- WIFI: exact
