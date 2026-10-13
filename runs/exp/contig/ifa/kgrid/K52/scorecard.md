# Scorecard: ifa_conus_merge (merged from CT,MA,ME,NH,RI,VT; NJ,NY,PA; DC,DE,FL,GA,MD,NC,SC,VA,WV; AL,AR,KY,LA,MS,OK,TN,TX; CO,IA,IL,IN,KS,MI,MN,MO,ND,NE,OH,SD,WI; AZ,CA,ID,MT,NM,NV,OR,UT,WA,WY)

**Verdict: fail**

| check | status | summary |
|---|---|---|
| one owner per cell | pass | 33300 cells, 0 with other than one owner, 0 not placed with no opportunity |
| district count per channel | pass | 1 channels, 0 off K |
| dropped for zero opportunity | pass | no cells dropped |
| final bands on drawn mass | fail | 52 districts, 5 outside the final tolerance |
| phantom shares | pass | 0 reported shares compared with the ledger, 0 not backed |
| planned against drawn owners | listed | 45 listed |
| mode compliance | pass | 0 violations, 0 metro exceptions, 0 units with zero-opportunity ZCTAs owned across them |
| ZIP contiguity | pass | 0 districts in pieces, 0 pieces, 0 ZIPs not in the graph |
| M1 polygon contiguity | fail | 0 districts in pieces, 0 detached pieces (largest 0 τ), 1 necks, 0 channel ZCTAs with no owner, 0 (ZCTA, fine channel) cells with no row, 0 owned twice, 11 mass necks listed beside M1 |
| geography manifest is 2025 | pass | 18 sources, all 2025 |
| solver status, bound and gap | unverified | no solver report |
| certificate tier | unverified | no solver report |
| one name per district | pass | 52 districts |
| rep labels | pass | blank, as OD3 (#58) decides |

## final bands on drawn mass

- IFA/IFA_04: drawn 1135.27 outside [800.782, 1083.41]
- IFA/IFA_22: drawn 1536.61 outside [800.782, 1083.41]
- IFA/IFA_25: drawn 1134.44 outside [800.782, 1083.41]
- IFA/IFA_41: drawn 1147.72 outside [800.782, 1083.41]
- IFA/IFA_43: drawn 1129.43 outside [800.782, 1083.41]

## planned against drawn owners

- IFA/CA/IFA_48: extra owner from repair in a free unit
- IFA/CA/IFA_49: extra owner from repair in a free unit
- IFA/CA/IFA_50: extra owner from repair in a free unit
- IFA/CA/IFA_51: extra owner from repair in a free unit
- IFA/CA/IFA_52: extra owner from repair in a free unit
- IFA/CT/IFA_01: extra owner from repair in a free unit
- IFA/CT/IFA_02: extra owner from repair in a free unit
- IFA/FL/IFA_17: extra owner from repair in a free unit
- IFA/FL/IFA_18: extra owner from repair in a free unit
- IFA/FL/IFA_19: extra owner from repair in a free unit
- IFA/FL/IFA_20: extra owner from repair in a free unit
- IFA/IL/IFA_32: extra owner from repair in a free unit
- IFA/IL/IFA_33: extra owner from repair in a free unit
- IFA/KS/IFA_35: extra owner from repair in a free unit
- IFA/KS/IFA_36: extra owner from repair in a free unit
- IFA/MA/IFA_03: extra owner from repair in a free unit
- IFA/MA/IFA_04: extra owner from repair in a free unit
- IFA/MI/IFA_37: extra owner from repair in a free unit
- IFA/MI/IFA_38: extra owner from repair in a free unit
- IFA/MI/IFA_39: extra owner from repair in a free unit
- IFA/MN/IFA_40: extra owner from repair in a free unit
- IFA/MN/IFA_41: extra owner from repair in a free unit
- IFA/NC/IFA_23: extra owner from repair in a free unit
- IFA/NC/IFA_24: extra owner from repair in a free unit
- IFA/NJ/IFA_05: extra owner from repair in a free unit
- IFA/NJ/IFA_06: extra owner from repair in a free unit
- IFA/NJ/IFA_07: extra owner from repair in a free unit
- IFA/NY/IFA_08: extra owner from repair in a free unit
- IFA/NY/IFA_09: extra owner from repair in a free unit
- IFA/NY/IFA_10: extra owner from repair in a free unit
- IFA/NY/IFA_11: extra owner from repair in a free unit
- IFA/NY/IFA_12: extra owner from repair in a free unit
- IFA/OH/IFA_42: extra owner from repair in a free unit
- IFA/OH/IFA_43: extra owner from repair in a free unit
- IFA/PA/IFA_13: extra owner from repair in a free unit
- IFA/PA/IFA_14: extra owner from repair in a free unit
- IFA/PA/IFA_15: extra owner from repair in a free unit
- IFA/PA/IFA_16: extra owner from repair in a free unit
- IFA/TN/IFA_27: extra owner from repair in a free unit
- IFA/TN/IFA_28: extra owner from repair in a free unit
- IFA/TX/IFA_29: extra owner from repair in a free unit
- IFA/TX/IFA_30: extra owner from repair in a free unit
- IFA/TX/IFA_31: extra owner from repair in a free unit
- IFA/WI/IFA_44: extra owner from repair in a free unit
- IFA/WI/IFA_45: extra owner from repair in a free unit

## M1 polygon contiguity

- IFA/IFA_09: neck 6.99 km wide cuts off 40 ZIPs (10001...), 5.4% of its land area and 47.4% of its mass; cut 10024-10025 2.18 km, 10025-10029 1.13 km, 10026-10029 1.41 km, 10029-10035 1.94 km, 10035-10128 0.33 km
- IFA/IFA_03: mass neck (diagnostic, not M1) 6.73 km wide cuts off 1 ZIPs (02110...), 0.0% of its land area and 6.2% of its mass; cut 02108-02110 0.21 km, 02109-02110 2.38 km, 02110-02111 0.92 km, 02110-02113 0.33 km, 02110-02133 0.17 km, 02110-02203 0.58 km, ...
- IFA/IFA_09: mass neck (diagnostic, not M1) 1.09 km wide cuts off 1 ZIPs (10170...), 0.0% of its land area and 8.3% of its mass; cut 10017-10170 0.51 km, 10165-10170 0.09 km, 10167-10170 0.12 km, 10168-10170 0.10 km, 10169-10170 0.18 km, 10170-10174 0.09 km
- IFA/IFA_13: mass neck (diagnostic, not M1) 8.07 km wide cuts off 1 ZIPs (19103...), 0.1% of its land area and 5.4% of its mass; cut 19102-19103 2.23 km, 19103-19104 1.26 km, 19103-19108 0.22 km, 19103-19109 0.68 km, 19103-19130 1.54 km, 19103-19146 2.14 km
- IFA/IFA_15: mass neck (diagnostic, not M1) 5.46 km wide cuts off 1 ZIPs (19406...), 0.1% of its land area and 8.3% of its mass; cut 19355-19406 0.71 km, 19406-19460 4.76 km
- IFA/IFA_19: mass neck (diagnostic, not M1) 9.12 km wide cuts off 1 ZIPs (33609...), 0.0% of its land area and 8.0% of its mass; cut 33606-33609 2.77 km, 33609-33616 0.47 km, 33609-33629 5.89 km
- IFA/IFA_29: mass neck (diagnostic, not M1) 7.25 km wide cuts off 1 ZIPs (77046...), 0.0% of its land area and 5.5% of its mass; cut 77005-77046 2.34 km, 77019-77046 1.01 km, 77027-77046 2.91 km, 77046-77098 0.73 km, 77046-77401 0.25 km
- IFA/IFA_31: mass neck (diagnostic, not M1) 7.29 km wide cuts off 2 ZIPs (76102...), 0.0% of its land area and 5.8% of its mass; cut 76102-76103 0.89 km, 76102-76111 3.95 km, 76111-76164 2.46 km
- IFA/IFA_32: mass neck (diagnostic, not M1) 5.10 km wide cuts off 1 ZIPs (60606...), 0.0% of its land area and 7.7% of its mass; cut 60601-60606 0.28 km, 60602-60606 0.28 km, 60603-60606 0.29 km, 60604-60606 0.28 km, 60606-60607 1.29 km, 60606-60654 1.00 km, ...
- IFA/IFA_39: mass neck (diagnostic, not M1) 9.51 km wide cuts off 88 ZIPs (48101...), 97.4% of its land area and 40.9% of its mass; cut 48033-48219 2.37 km, 48033-48240 2.37 km, 48075-48219 3.21 km, 48075-48235 1.56 km
- IFA/IFA_40: mass neck (diagnostic, not M1) 3.20 km wide cuts off 1 ZIPs (55402...), 0.0% of its land area and 5.6% of its mass; cut 55401-55402 1.03 km, 55402-55403 1.30 km, 55402-55404 0.37 km, 55402-55415 0.50 km
- IFA/IFA_50: mass neck (diagnostic, not M1) 7.23 km wide cuts off 1 ZIPs (91101...), 0.0% of its land area and 8.3% of its mass; cut 91101-91105 1.74 km, 91101-91106 5.49 km
