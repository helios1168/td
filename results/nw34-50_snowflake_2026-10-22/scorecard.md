# Scorecard: nw34-50 (merged from AL+AR+AZ+CA+CO+CT+DC+DE+FL+GA+IA+ID+IL+IN+KS+KY+LA+MA+MD+ME+MI+MN+MO+MS+MT+NC+ND+NE+NH+NJ+NM+NV+NY+OH+OK+OR+PA+RI+SC+SD+TN+TX+UT+VA+VT+WA+WI+WV+WY)

**Verdict: pass**

| check | status | summary |
|---|---|---|
| one owner per cell | pass | 166500 cells, 0 with other than one owner, 0 not placed with no opportunity |
| district count per channel | pass | 2 channels, 0 off K |
| dropped for zero opportunity | pass | no cells dropped |
| final bands on drawn mass | pass | 50 districts, 0 outside the final tolerance |
| phantom shares | pass | 0 reported shares compared with the ledger, 0 not backed |
| planned against drawn owners | listed | 47 listed |
| mode compliance | pass | 0 violations, 0 metro exceptions, 0 units with zero-opportunity ZCTAs owned across them |
| ZIP contiguity | pass | 0 districts in pieces, 0 pieces, 0 ZIPs not in the graph |
| M1 polygon contiguity | pass | 0 districts in pieces, 0 detached pieces (largest 0 τ), 0 necks (pieces: no land-only gap edges in the polygon graph, R5 inactive), 0 channel ZCTAs with no owner, 0 (ZCTA, fine channel) cells with no row, 0 owned twice, 10 mass necks listed beside M1 |
| geography manifest is 2025 | pass | 18 sources, all 2025 |
| solver status, bound and gap | unverified | no solver report |
| certificate tier | unverified | no solver report |
| one name per district | pass | 50 districts |
| rep labels | pass | blank, as OD3 (#58) decides |

## planned against drawn owners

- WIFI/CA/WIFI_04: extra owner from repair in a free unit
- WIFI/CA/WIFI_05: extra owner from repair in a free unit
- WIFI/CA/WIFI_06: extra owner from repair in a free unit
- WIFI/CT/WIFI_07: extra owner from repair in a free unit
- WIFI/CT/WIFI_08: extra owner from repair in a free unit
- WIFI/FL/WIFI_11: extra owner from repair in a free unit
- WIFI/FL/WIFI_12: extra owner from repair in a free unit
- WIFI/FL/WIFI_13: extra owner from repair in a free unit
- WIFI/GA/WIFI_01: extra owner from repair in a free unit
- WIFI/GA/WIFI_13: extra owner from repair in a free unit
- WIFI/GA/WIFI_14: extra owner from repair in a free unit
- WIFI/IN/WIFI_18: extra owner from repair in a free unit
- WIFI/IN/WIFI_19: extra owner from repair in a free unit
- WIFI/MA/WIFI_07: extra owner from repair in a free unit
- WIFI/MA/WIFI_21: extra owner from repair in a free unit
- WIFI/MD/WIFI_09: extra owner from repair in a free unit
- WIFI/MD/WIFI_10: extra owner from repair in a free unit
- WIFI/MD/WIFI_22: extra owner from repair in a free unit
- WIFI/MN/WIFI_15: extra owner from repair in a free unit
- WIFI/MN/WIFI_24: extra owner from repair in a free unit
- WIFI/NC/WIFI_25: extra owner from repair in a free unit
- WIFI/NC/WIFI_26: extra owner from repair in a free unit
- WIFI/NJ/WIFI_10: extra owner from repair in a free unit
- WIFI/NJ/WIFI_27: extra owner from repair in a free unit
- WIFI/NY/WIFI_08: extra owner from repair in a free unit
- WIFI/NY/WIFI_27: extra owner from repair in a free unit
- WIFI/NY/WIFI_28: extra owner from repair in a free unit
- WIFI/NY/WIFI_29: extra owner from repair in a free unit
- WIFI/OH/WIFI_19: extra owner from repair in a free unit
- WIFI/OH/WIFI_30: extra owner from repair in a free unit
- WIFI/PA/WIFI_22: extra owner from repair in a free unit
- WIFI/PA/WIFI_32: extra owner from repair in a free unit
- WIFI/PA/WIFI_33: extra owner from repair in a free unit
- WIFI/TN/WIFI_01: extra owner from repair in a free unit
- WIFI/TN/WIFI_34: extra owner from repair in a free unit
- WIFI/TX/WIFI_31: extra owner from repair in a free unit
- WIFI/TX/WIFI_35: extra owner from repair in a free unit
- national/CA/national_04: extra owner from repair in a free unit
- national/CA/national_05: extra owner from repair in a free unit
- national/CA/national_06: extra owner from repair in a free unit
- national/CA/national_07: extra owner from repair in a free unit
- national/IL/national_11: extra owner from repair in a free unit
- national/IL/national_12: extra owner from repair in a free unit
- national/NY/national_09: extra owner from repair in a free unit
- national/NY/national_14: extra owner from repair in a free unit
- national/TX/national_02: extra owner from repair in a free unit
- national/TX/national_15: extra owner from repair in a free unit

## M1 polygon contiguity

- WIFI/WIFI_02: mass neck (diagnostic, not M1) 1.81 km wide cuts off 1 ZIPs (70163...), 0.0% of its land area and 5.9% of its mass; cut 70112-70163 0.07 km, 70113-70163 0.33 km, 70130-70163 0.24 km, 70139-70163 1.17 km
- WIFI/WIFI_09: mass neck (diagnostic, not M1) 6.69 km wide cuts off 1 ZIPs (20006...), 0.0% of its land area and 25.1% of its mass; cut 20005-20006 0.60 km, 20006-20024 0.34 km, 20006-20036 1.28 km, 20006-20037 0.68 km, 20006-20052 0.80 km, 20006-20220 0.37 km, ...
- WIFI/WIFI_14: mass neck (diagnostic, not M1) 7.07 km wide cuts off 1 ZIPs (30326...), 0.0% of its land area and 7.9% of its mass; cut 30319-30326 1.50 km, 30324-30326 1.11 km, 30326-30329 2.00 km, 30326-30342 2.46 km
- WIFI/WIFI_17: mass neck (diagnostic, not M1) 5.10 km wide cuts off 1 ZIPs (60606...), 0.0% of its land area and 13.5% of its mass; cut 60601-60606 0.28 km, 60602-60606 0.28 km, 60603-60606 0.29 km, 60604-60606 0.28 km, 60606-60607 1.29 km, 60606-60654 1.00 km, ...
- WIFI/WIFI_21: mass neck (diagnostic, not M1) 6.73 km wide cuts off 1 ZIPs (02110...), 0.0% of its land area and 5.0% of its mass; cut 02108-02110 0.21 km, 02109-02110 2.38 km, 02110-02111 0.92 km, 02110-02113 0.33 km, 02110-02133 0.17 km, 02110-02203 0.58 km, ...
- WIFI/WIFI_27: mass neck (diagnostic, not M1) 2.18 km wide cuts off 5 ZIPs (10019...), 0.1% of its land area and 7.2% of its mass; cut 10024-10025 2.18 km
- WIFI/WIFI_28: mass neck (diagnostic, not M1) 3.58 km wide cuts off 1 ZIPs (10036...), 0.1% of its land area and 9.1% of its mass; cut 10017-10036 0.32 km, 10018-10036 2.19 km, 10020-10036 0.31 km, 10024-10069 0.08 km, 10036-10110 0.40 km, 10036-10173 0.08 km, ...
- WIFI/WIFI_33: mass neck (diagnostic, not M1) 8.07 km wide cuts off 1 ZIPs (19103...), 0.0% of its land area and 9.2% of its mass; cut 19102-19103 2.23 km, 19103-19104 1.26 km, 19103-19108 0.22 km, 19103-19109 0.68 km, 19103-19130 1.54 km, 19103-19146 2.14 km
- national/national_09: mass neck (diagnostic, not M1) 7.33 km wide cuts off 214 ZIPs (06390...), 1.4% of its land area and 41.4% of its mass; cut 10573-10580 3.97 km, 10577-10580 2.34 km, 10706-10964 1.02 km
- national/national_14: mass neck (diagnostic, not M1) 7.28 km wide cuts off 5 ZIPs (10017...), 0.0% of its land area and 17.9% of its mass; cut 10016-10017 1.60 km, 10017-10018 0.16 km, 10017-10020 0.08 km, 10017-10022 1.45 km, 10017-10036 0.32 km, 10017-10110 0.09 km, ...

**Sealed-region driver label (nw34-50):** passes
