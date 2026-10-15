# Shape review flags (eye review only, not a gate)

Measured with `tools/looks/study.py` of branch `m5-studio/study-v2` (commit 168d51f: land-only `hull_fill` and `bite`, `arm_share`, `roughness`) on each map's merged ledger; per-district rows in `districts.csv`. The input is the ledger, so a ZCTA the realizer heuristic placed counts like any other, and **areas placed by the heuristic may look rougher** (more cut edges, deeper bites) than an exactly drawn area. Nothing here fails a map: a flag means *look at this district on the page*.

Flag rule: `cut_edges >= 126 AND bite >= 0.18`. `bite` = share of the district's land-hull taken by other districts' land of the same channel; `hull_fill` = district land / land inside its convex hull (1 = convex); `cut_edges` = polygon-graph edges between this district and another district of its channel inside a shared state.

## Per map

| map | districts | max bite | min hull_fill | max cut_edges | max arm_share | max roughness | flagged |
|---|---|---|---|---|---|---|---|
| ne-48-bal | 48 | 0.409 (FI FI_14) | 0.437 (national national_13) | 247 (FI FI_20) | 0.265 (FI FI_17) | 20.45 (WH WH_04) | 2 |
| ne-50-filight | 50 | 0.335 (national national_15) | 0.542 (national national_04) | 243 (national national_09) | 0.265 (FI FI_15) | 20.45 (WH WH_04) | 4 |
| ne-cmp-tierP | 49 | 0.305 (FI FI_12) | 0.542 (national national_04) | 197 (national national_04) | 0.265 (FI FI_15) | 20.45 (WH WH_04) | 2 |
| ne-48-bal (last night, unsealed) | 48 | 0.456 (national national_11) | 0.522 (national national_11) | 283 (FI FI_19) | 0.263 (national national_12) | 20.47 (WH WH_04) | 2 |

## Flagged districts (`cut_edges >= 126 AND bite >= 0.18`)

### ne-48-bal

| channel | district | states | $M | cut_edges | bite | bite states | hull_fill | arm_share | roughness |
|---|---|---|---|---|---|---|---|---|---|
| FI | FI_07 | DE MD PA | 836 | 131 | 0.338 | PA:0.119 VA:0.110 WV:0.077 | 0.654 | 0.052 | 2.64 |
| FI | FI_06 | DC PA VA WV | 835 | 128 | 0.241 | PA:0.090 MD:0.059 OH:0.057 | 0.752 | 0.012 | 2.27 |

### ne-50-filight

| channel | district | states | $M | cut_edges | bite | bite states | hull_fill | arm_share | roughness |
|---|---|---|---|---|---|---|---|---|---|
| national | national_09 | DE NY PA | 1,011 | 243 | 0.214 | PA:0.094 NJ:0.075 NY:0.023 | 0.655 | 0.015 | 2.81 |
| national | national_04 | CA | 1,123 | 197 | 0.276 | CA:0.276 | 0.542 | 0.124 | 8.46 |
| FI | FI_18 | OH PA WV | 874 | 167 | 0.244 | PA:0.117 OH:0.061 VA:0.042 | 0.755 | 0.009 | 2.25 |
| national | national_08 | DC MD OH PA WV | 1,003 | 146 | 0.215 | VA:0.109 PA:0.059 KY:0.019 | 0.774 | 0.008 | 1.83 |

### ne-cmp-tierP

| channel | district | states | $M | cut_edges | bite | bite states | hull_fill | arm_share | roughness |
|---|---|---|---|---|---|---|---|---|---|
| national | national_04 | CA | 1,123 | 197 | 0.276 | CA:0.276 | 0.542 | 0.124 | 8.46 |
| FI | FI_18 | OH PA WV | 874 | 167 | 0.244 | PA:0.117 OH:0.061 VA:0.042 | 0.755 | 0.009 | 2.25 |

### ne-48-bal (last night, unsealed)

| channel | district | states | $M | cut_edges | bite | bite states | hull_fill | arm_share | roughness |
|---|---|---|---|---|---|---|---|---|---|
| FI | FI_18 | OH PA WV | 781 | 225 | 0.211 | PA:0.131 VA:0.040 MD:0.019 | 0.787 | 0.011 | 2.38 |
| FI | FI_06 | DC DE MD PA | 825 | 142 | 0.324 | VA:0.117 PA:0.093 WV:0.082 | 0.647 | 0.058 | 2.77 |

