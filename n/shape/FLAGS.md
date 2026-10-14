# Shape flags (for eye review only)

**Provisional review rule:** flag a district when `cut_edges >= 126 AND bite >= 0.18`.
*Fitted on the owner's 74 calibration verdicts; does not generalise; for eye review only, not a gate.* A flag says "look at this district first", nothing more; an unflagged district is not certified.

Measures are from `tools/looks/study.py` (branch `m5-studio/study-v2`, land-hull definitions of 2026-10-14): `bite` = share of the land hull taken by other districts' land reachable without crossing water; `hull_fill` = district land over land hull (1 = fills its hull); `cut_edges` = polygon-graph edges shared with other districts of the same channel inside a shared state. Per-district values: [districts.csv](districts.csv) (`usd_m` is district dollars in $M; IFA maps converted at the IFA rate 1.25197 from `m_rel`).

## Per-map summary

| map | districts | flagged | max bite | min hull_fill | max cut_edges |
|---|---|---|---|---|---|
| IFA_K48 | 48 | 4 | 0.379 (IFA IFA_32) | 0.614 (IFA IFA_32) | 198 (IFA IFA_28) |
| IFA_K49 | 49 | 3 | 0.379 (IFA IFA_33) | 0.614 (IFA IFA_33) | 198 (IFA IFA_29) |
| IFA_K50 | 50 | 3 | 0.379 (IFA IFA_34) | 0.614 (IFA IFA_34) | 198 (IFA IFA_30) |
| IFA_K51 | 51 | 3 | 0.379 (IFA IFA_34) | 0.537 (IFA IFA_49) | 198 (IFA IFA_30) |
| IFA_K52 | 52 | 2 | 0.294 (IFA IFA_26) | 0.537 (IFA IFA_50) | 198 (IFA IFA_30) |
| IFA_K53 | 53 | 2 | 0.294 (IFA IFA_27) | 0.537 (IFA IFA_51) | 198 (IFA IFA_31) |
| IFA_K54 | 54 | 3 | 0.294 (IFA IFA_27) | 0.394 (IFA IFA_53) | 289 (IFA IFA_53) |
| MAIN_ne-48-bal | 48 | 2 | 0.456 (national national_11) | 0.522 (national national_11) | 283 (FI FI_19) |

## Flagged districts

### IFA_K48

| channel | district | states | $M | cut_edges | bite | hull_fill | water_wrap | arm_share | roughness |
|---|---|---|---|---|---|---|---|---|---|
| IFA | IFA_32 | IN;MI | 1,349 | 176 | 0.379 | 0.614 | 0.055 | 0.020 | 2.35 |
| IFA | IFA_28 | TX | 1,172 | 198 | 0.202 | 0.650 | 0.055 | 0.067 | 12.65 |
| IFA | IFA_10 | PA | 1,373 | 164 | 0.194 | 0.825 | 0.000 | 0.040 | 3.05 |
| IFA | IFA_14 | NY | 1,035 | 126 | 0.187 | 0.796 | 0.133 | 0.021 | 2.77 |

### IFA_K49

| channel | district | states | $M | cut_edges | bite | hull_fill | water_wrap | arm_share | roughness |
|---|---|---|---|---|---|---|---|---|---|
| IFA | IFA_33 | IN;MI | 1,349 | 176 | 0.379 | 0.614 | 0.055 | 0.020 | 2.35 |
| IFA | IFA_29 | TX | 1,172 | 198 | 0.202 | 0.650 | 0.055 | 0.067 | 12.65 |
| IFA | IFA_11 | NY | 1,035 | 126 | 0.187 | 0.796 | 0.133 | 0.021 | 2.77 |

### IFA_K50

| channel | district | states | $M | cut_edges | bite | hull_fill | water_wrap | arm_share | roughness |
|---|---|---|---|---|---|---|---|---|---|
| IFA | IFA_34 | IN;MI | 1,349 | 176 | 0.379 | 0.614 | 0.055 | 0.020 | 2.35 |
| IFA | IFA_30 | TX | 1,172 | 198 | 0.202 | 0.650 | 0.055 | 0.067 | 12.65 |
| IFA | IFA_11 | NY | 1,035 | 126 | 0.187 | 0.796 | 0.133 | 0.021 | 2.77 |

### IFA_K51

| channel | district | states | $M | cut_edges | bite | hull_fill | water_wrap | arm_share | roughness |
|---|---|---|---|---|---|---|---|---|---|
| IFA | IFA_34 | IN;MI | 1,349 | 176 | 0.379 | 0.614 | 0.055 | 0.020 | 2.35 |
| IFA | IFA_30 | TX | 1,172 | 198 | 0.202 | 0.650 | 0.055 | 0.067 | 12.65 |
| IFA | IFA_11 | NY | 1,035 | 126 | 0.187 | 0.796 | 0.133 | 0.021 | 2.77 |

### IFA_K52

| channel | district | states | $M | cut_edges | bite | hull_fill | water_wrap | arm_share | roughness |
|---|---|---|---|---|---|---|---|---|---|
| IFA | IFA_30 | TX | 1,172 | 198 | 0.202 | 0.650 | 0.055 | 0.067 | 12.65 |
| IFA | IFA_11 | NY | 1,035 | 126 | 0.187 | 0.796 | 0.133 | 0.021 | 2.77 |

### IFA_K53

| channel | district | states | $M | cut_edges | bite | hull_fill | water_wrap | arm_share | roughness |
|---|---|---|---|---|---|---|---|---|---|
| IFA | IFA_31 | TX | 1,172 | 198 | 0.202 | 0.650 | 0.055 | 0.067 | 12.65 |
| IFA | IFA_11 | NY | 1,035 | 126 | 0.187 | 0.796 | 0.133 | 0.021 | 2.77 |

### IFA_K54

| channel | district | states | $M | cut_edges | bite | hull_fill | water_wrap | arm_share | roughness |
|---|---|---|---|---|---|---|---|---|---|
| IFA | IFA_31 | TX | 1,172 | 198 | 0.202 | 0.650 | 0.055 | 0.067 | 12.65 |
| IFA | IFA_53 | CA;NV;OR | 1,060 | 289 | 0.202 | 0.394 | 0.001 | 0.108 | 20.50 |
| IFA | IFA_11 | NY | 1,035 | 126 | 0.187 | 0.796 | 0.133 | 0.021 | 2.77 |

### MAIN_ne-48-bal

| channel | district | states | $M | cut_edges | bite | hull_fill | water_wrap | arm_share | roughness |
|---|---|---|---|---|---|---|---|---|---|
| FI | FI_06 | DC;DE;MD;PA | 825 | 142 | 0.324 | 0.647 | 0.090 | 0.058 | 2.77 |
| FI | FI_18 | OH;PA;WV | 781 | 225 | 0.211 | 0.787 | 0.001 | 0.011 | 2.38 |
