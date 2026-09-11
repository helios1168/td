# Owner sets on the committed k = 18 draw (measured 2026-09-06, corrected 2026-09-07)

Draw `draw_k18_v2_20260904/k18`, seed 2; tau = 473.513; 52 state codes including `??` at
0.070 tau. A district's home state is the plurality of its mass (user decision, see
`mem:decisions/stage1-route`).

Home states: NY (D01, D04), CA (D02, D10, D14, D17, D18), TX (D03, D16), PA (D05), CO (D06),
FL (D07, D15), NC (D08), MI (D09), IL (D11), NJ (D12), MO (D13). 41 states have no home
district.

- Mass outside the owner sets: **9.15%** (90.85% inside). The 9.46% first quoted on 2026-09-06
  was a hand count, superseded by `tools/borders_report.py` on 2026-09-07.
- Blocks a 10% band cannot close: NY+NJ+CT+MA+NH+RI+VT+ME = 3.19 tau for three districts
  against PA+MD+DE = 0.82 tau; D06 without its AZ and TX slivers is 0.68 tau.
- Full composition table: `git show ae2b18d:docs/BORDERS_PLAN.md`.

Related: `mem:facts/state-border-snapping`.

Source: `main:STATE.md` `## Facts` (a3924e8).
