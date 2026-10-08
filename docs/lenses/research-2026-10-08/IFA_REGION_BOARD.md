# IFA region board, 2026-10-08 (written 05:20 by td-research; latest commits)

M1 column is the verdict of the DEFAULT gate (check_m1 measures shared border only until #131
lands). South Central FAILS M1 under that gate; the G1 prototype verdict is reported beside it and
does not make it a pass. Whether the El Paso coverage-gap neck is settled by G1 for tonight's map is
an open owner question (asked 05:22); until answered the CONUS verdict is 'fails M1 on El Paso'.

Band verdict per district against the E2 window [798.74, 1148.19] m_rel (owner, southatl tab);
every merge audited at the spec default final_delta 0.15 with the τ line informational.

| region | branch, commit | folder | K | M1 (regional, full graph) | window |
|---|---|---|---|---|---|
| New England | m5-studio/ifa-newengland 01ffe5e | runs/exp/contig/ifa/newengland/merged | 4 | pass, 0 pieces 0 necks | 4 of 4 |
| South Central | m5-studio/ifa-southcentral 5b5da26 | runs/exp/contig/ifa/southcentral/merged_b (balanced successor) | 6 | FAIL (default gate): El Paso 6.14 km coverage-gap neck in TX IFA_05, cuts off 44 ZIPs, 6.9% land and mass; neck-free under the G1 prototype only | 6 of 6 |
| South Atlantic | m5-studio/ifa-southatl 20cfe36 | runs/exp/contig/ifa/southatl/merged | 9 | pass | 8 of 9, MD+DE+WV $1,924M under the widened F1 waiver |
| Midwest (ENC+WNC+CO) | m5-studio/ifa-midwest 8eeb8bf | runs/exp/contig/ifa/midwest/ifa_mw_merge | 14 | pass | 14 of 14 |
| West (Mountain less CO, Pacific) | m5-studio/ifa-west a2d2602 | runs/exp/contig/ifa/west/merged | 7 | pass | 7 of 7 |
| Middle Atlantic | m5-studio/ifa-midatl, open | NJ 3 (ifa_nj_k3-neck) + PA 4 (ifa_pa_k4t-neck) + NY 5 pending | 12 | NY open | NJ, PA in |

Regions with nothing left to run: five (South Central's M1 is a reported failure). Total so far 40 districts plus Middle Atlantic 12 = 52, inside the IFA grid 46-55 (F2).
Split states: CT MA (NE); TX TN (SC); NC FL (SA); MI OH IL WI MN KS (MW); CA (W); NJ PA NY (MA).

Region DECIDED lines, filed here for the record:
- newengland: free = MA only in the MA+VT+NH+ME draw (rule C by construction).
- southcentral: reused ifa_tx_k3 rather than redrawing TX; owner chose the in-region TN split (option a).
- southatl: SC with an NC piece, not GA (SC+GA is 14.07 m_rel under two floors); DC rides with VA.
- midwest: whole attached states marked whole in every spec; MI by congressional-district grouping
  after the 1,800 s ZIP draw kept necks; Twin Cities shape is forced by the dollars (metro >= $1,032M)
  and the district reaches Wisconsin along the St. Croix, so no redraw. T1 breach noted: one map was
  shown before registration; no further images until the lander registers.
- west: Pacific built from the gated CA K 4 drawing by moving 18 northern CA counties (47 m_rel) to
  OR+WA and re-gating with repair.py, instead of waiting on the tangled 1,800 s CA+OR+WA draw.
- td-research: CO to western Kansas (owner pick B); band rule relayed to all tabs at 05:16.
