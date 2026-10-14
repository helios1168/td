# Scorecard: w1-52-wide (contig arm1 + window repair, w1-52-wide, repair pass 1)

**Verdict: fail**

| check | status | summary |
|---|---|---|
| one owner per cell | pass | 166500 cells, 0 with other than one owner, 0 not placed with no opportunity |
| district count per channel | pass | 1 channels, 0 off K |
| dropped for zero opportunity | pass | no cells dropped |
| final bands on drawn mass | pass | 52 districts, 0 outside the final tolerance |
| phantom shares | pass | 78 reported shares compared with the ledger, 0 not backed |
| planned against drawn owners | listed | 1 listed |
| mode compliance | pass | 0 violations, 0 metro exceptions, 0 units with zero-opportunity ZCTAs owned across them |
| ZIP contiguity | listed | 3 districts in pieces, 3 pieces, 0 ZIPs not in the graph |
| M1 polygon contiguity | fail | 3 districts in pieces, 3 detached pieces (largest 0.423 τ), 5 necks, 0 channel ZCTAs with no owner, 0 (ZCTA, fine channel) cells with no row, 0 owned twice, 22 mass necks listed beside M1 |
| geography manifest is 2025 | pass | 18 sources, all 2025 |
| solver status, bound and gap | listed | 1 channels |
| certificate tier | pass | weakest tier: exact |
| one name per district | pass | 52 districts |
| rep labels | pass | blank, as OD3 (#58) decides |

## planned against drawn owners

- WIFI/MI/WIFI_24: extra owner from repair in a free unit

## ZIP contiguity

- WIFI/WIFI_13: piece of 277 ZIPs, 0.35 of the district's mass, cause attachment
- WIFI/WIFI_29: piece of 938 ZIPs, 0.417 of the district's mass, cause corridor
- WIFI/WIFI_40: piece of 30 ZIPs, 0.346 of the district's mass, cause shape

## M1 polygon contiguity

- WIFI/WIFI_13: detached piece of 277 ZIPs (27006...), 0.379 τ, cause attachment
- WIFI/WIFI_29: detached piece of 938 ZIPs (03031...), 0.423 τ, cause corridor
- WIFI/WIFI_40: detached piece of 30 ZIPs (10001...), 0.331 τ, cause shape
- WIFI/WIFI_06: neck 4.68 km wide cuts off 1 ZIPs (93021...), 6.1% of its land area and 0.0% of its mass; cut 91360-93021 4.68 km
- WIFI/WIFI_13: neck 0.96 km wide cuts off 276 ZIPs (27006...), 37.5% of its land area and 35.0% of its mass; cut 27202-27244 0.96 km
- WIFI/WIFI_14: neck 0.76 km wide cuts off 136 ZIPs (07001...), 21.6% of its land area and 65.4% of its mass; cut 08505-08611 0.76 km
- WIFI/WIFI_39: neck 3.35 km wide cuts off 20 ZIPs (10305...), 11.0% of its land area and 34.7% of its mass; cut 11207-11236 1.27 km, 11236-11239 2.09 km
- WIFI/WIFI_41: neck 2.59 km wide cuts off 3 ZIPs (11364...), 6.2% of its land area and 1.7% of its mass; cut 11361-11364 2.59 km
- WIFI/WIFI_05: mass neck (diagnostic, not M1) 1.94 km wide cuts off 1 ZIPs (94104...), 0.0% of its land area and 5.5% of its mass; cut 94104-94105 0.52 km, 94104-94108 0.66 km, 94104-94111 0.76 km
- WIFI/WIFI_06: mass neck (diagnostic, not M1) 4.54 km wide cuts off 4 ZIPs (91101...), 1.0% of its land area and 14.3% of its mass; cut 91030-91106 0.93 km, 91101-91105 1.74 km, 91105-91106 1.88 km
- WIFI/WIFI_07: mass neck (diagnostic, not M1) 8.34 km wide cuts off 1 ZIPs (95113...), 0.0% of its land area and 8.3% of its mass; cut 95110-95113 4.21 km, 95112-95113 4.12 km
- WIFI/WIFI_10: mass neck (diagnostic, not M1) 8.47 km wide cuts off 2 ZIPs (92614...), 0.1% of its land area and 9.4% of its mass; cut 92612-92614 6.17 km, 92612-92707 1.38 km, 92614-92618 0.93 km
- WIFI/WIFI_13: mass neck (diagnostic, not M1) 0.61 km wide cuts off 756 ZIPs (20117...), 62.3% of its land area and 31.5% of its mass; cut 20016-22101 0.61 km
- WIFI/WIFI_13: mass neck (diagnostic, not M1) 0.96 km wide cuts off 276 ZIPs (27006...), 37.5% of its land area and 35.0% of its mass; cut 27202-27244 0.96 km
- WIFI/WIFI_14: mass neck (diagnostic, not M1) 0.76 km wide cuts off 107 ZIPs (08002...), 78.4% of its land area and 34.6% of its mass; cut 08505-08611 0.76 km
- WIFI/WIFI_19: mass neck (diagnostic, not M1) 8.47 km wide cuts off 1 ZIPs (30326...), 0.0% of its land area and 11.3% of its mass; cut 30305-30326 3.40 km, 30319-30326 1.50 km, 30324-30326 1.11 km, 30326-30342 2.46 km
- WIFI/WIFI_22: mass neck (diagnostic, not M1) 5.10 km wide cuts off 1 ZIPs (60606...), 0.0% of its land area and 17.3% of its mass; cut 60601-60606 0.28 km, 60602-60606 0.28 km, 60603-60606 0.29 km, 60604-60606 0.28 km, 60606-60607 1.29 km, 60606-60654 1.00 km, ...
- WIFI/WIFI_26: mass neck (diagnostic, not M1) 0.40 km wide cuts off 1 ZIPs (70163...), 0.0% of its land area and 6.3% of its mass; cut 70112-70163 0.07 km, 70113-70163 0.33 km
- WIFI/WIFI_28: mass neck (diagnostic, not M1) 8.61 km wide cuts off 1 ZIPs (21031...), 0.0% of its land area and 6.3% of its mass; cut 21030-21031 8.61 km
- WIFI/WIFI_29: mass neck (diagnostic, not M1) 0.44 km wide cuts off 937 ZIPs (03031...), 98.0% of its land area and 41.7% of its mass; cut 05478-05481 0.44 km
- WIFI/WIFI_33: mass neck (diagnostic, not M1) 8.69 km wide cuts off 4 ZIPs (28202...), 0.0% of its land area and 8.5% of its mass; cut 28202-28203 2.32 km, 28202-28204 2.21 km, 28202-28206 3.41 km, 28202-28216 0.75 km
- WIFI/WIFI_37: mass neck (diagnostic, not M1) 6.75 km wide cuts off 2 ZIPs (78701...), 0.0% of its land area and 8.0% of its mass; cut 78701-78703 2.31 km, 78701-78705 2.40 km, 78701-78712 0.99 km, 78702-78712 1.04 km
- WIFI/WIFI_39: mass neck (diagnostic, not M1) 3.35 km wide cuts off 20 ZIPs (10305...), 11.0% of its land area and 34.7% of its mass; cut 11207-11236 1.27 km, 11236-11239 2.09 km
- WIFI/WIFI_40: mass neck (diagnostic, not M1) 0.35 km wide cuts off 29 ZIPs (10001...), 0.3% of its land area and 33.9% of its mass; cut 10005-10271 0.28 km, 10006-10271 0.06 km
- WIFI/WIFI_41: mass neck (diagnostic, not M1) 1.49 km wide cuts off 2 ZIPs (10020...), 0.0% of its land area and 5.1% of its mass; cut 10017-10020 0.08 km, 10019-10020 0.71 km, 10020-10036 0.31 km, 10022-10112 0.08 km, 10111-10112 0.31 km
- WIFI/WIFI_44: mass neck (diagnostic, not M1) 7.17 km wide cuts off 1 ZIPs (19103...), 0.0% of its land area and 10.5% of its mass; cut 19102-19103 2.23 km, 19103-19104 1.26 km, 19103-19130 1.54 km, 19103-19146 2.14 km
- WIFI/WIFI_46: mass neck (diagnostic, not M1) 8.26 km wide cuts off 1 ZIPs (18101...), 0.0% of its land area and 5.3% of its mass; cut 18101-18102 8.26 km
- WIFI/WIFI_48: mass neck (diagnostic, not M1) 1.89 km wide cuts off 1 ZIPs (75225...), 0.0% of its land area and 7.9% of its mass; cut 75225-75231 1.89 km
- WIFI/WIFI_51: mass neck (diagnostic, not M1) 2.91 km wide cuts off 1 ZIPs (24011...), 0.0% of its land area and 6.7% of its mass; cut 24011-24013 0.92 km, 24011-24016 1.99 km
- WIFI/WIFI_52: mass neck (diagnostic, not M1) 8.45 km wide cuts off 1 ZIPs (53202...), 0.0% of its land area and 7.2% of its mass; cut 53202-53203 1.59 km, 53202-53204 1.05 km, 53202-53207 1.07 km, 53202-53211 2.31 km, 53202-53212 2.43 km

## solver status, bound and gap

- WIFI: status optimal, objective 6731.314120642743, bound 6731.314120642743, gap 0, tier exact

## certificate tier

- WIFI: exact
