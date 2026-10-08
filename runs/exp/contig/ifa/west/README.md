# IFA West (Mountain + Pacific), 2026-10-08

Canonical: `merged/` (K 7). Owner decision 2026-10-08, confirmed in the td-ifa-west tab (their answer
"Yes, CO goes to the Midwest"): Colorado leaves the West and is drawn by the Midwest with western Kansas.
`merged_co/` (K 8, CO alone in the West) is kept as the superseded alternative.

| run | what | M1 (regional) |
|---|---|---|
| ifa_mtn_k2 | AZ+NM $1,223M; ID+MT+NV+UT+WY $1,103M; whole states | 0 pieces, 0 necks |
| ifa_mtn_k3 | as above plus CO alone $1,056M (superseded) | 0 pieces, 0 necks |
| ifa_pac_k5 | CA+OR+WA K 5 MILP draw, 480 s, tangled | fail: 4 necks (tier 3) |
| ifa_pac_k5_hand | ifa_ca_k4-neck's CA K 4 drawing with 18 northern CA counties (Del Norte to Sutter/Yuba/Nevada/Lake; 47 m_rel) moved to OR+WA, 3 stray ZIPs returned to IFA_04, re-gated by repair.py | 0 pieces, 0 necks |
| merged | Mountain K 2 + Pacific K 5 | 0 pieces, 0 necks; all 7 in [$1,000M, $1,437.5M] |
| merged_co | Mountain K 3 + Pacific K 5 | 0 pieces, 0 necks; all 8 in band |

Every audit's remaining line is the out-of-region (ZCTA, fine channel) cells with no row.
