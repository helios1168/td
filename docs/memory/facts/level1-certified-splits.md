# Level-1 certified minimum splits by k (2026-09-09)

Engine after 2026-09-09 (`docs/CODE_MAP.md` "Runtime after round 2"): HiGHS with flow roots
fixed to the anchor states, `portfolio` strategy, certificate by cutoff. See
`mem:solver/highs-and-scipy`.

Certified minimum splits at δ = 10%, CONUS instance, anchored; one grid of six concurrent chains
on two threads each, 2020-gazetteer coordinates:

| k | 10 | 12 | 14 | 16 | 18 | 20 |
|---|---|---|---|---|---|---|
| splits | 4 | 4 | 5 | 7 | 7 | 10 |
| solve | 18 s | 14 s | 1.4 s | 84 s | 49 s | 150 s |

Grid wall 163 s.

Re-run on the 2025 gazetteer vintage 2026-09-09 (`battery/results/app/gaz2025_*`): identical at
k = 10/12/14/16/18, **k = 20 goes from 10 to 11**, and k = 16's cut moves MD to VA. k = 16 is
time-limited on both vintages (gap 1.785%). Alone on the machine k = 20 closes in 70 s and k = 16
certifies in 83 s. Under scipy's HiGHS the same k = 20 cell stopped at the 600 s cap with a
one-split gap. Never compare a number across vintages (`mem:geo/zcta-geometry`).

Open, low priority (matters only if δ = 10% is chosen): the free bound at δ = 10% says 6 splits
might be possible (NJ alone plus PA+MD+DE+WV); HiGHS neither found nor refuted it in 600 s.

Source: `main:STATE.md` `## Facts` (a3924e8).
