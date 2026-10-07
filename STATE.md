# State — support-master territory design

**Updated:** 2026-10-07 · **Branch:** `main`

## Now

The owner is away overnight (2026-10-07) and has granted autonomy: "a good clean set of maps".

- **#123 landed** (ee800d8): `repair.py --jobs N` and `run.py --jobs N`.
- **Running:**
  - **#124:** the plan check. Measurement A, A+B, A+B+C is running on branch `m5-studio/124`. So far A and B remove nothing; Sol must verify B's proof before landing.
  - **#125:** the main-map set in the ne_plains layout at every $-eligible K, ±10% band, no widening.
  - **#126:** an IFA map that passes M1 and the $ rule.
- **Shortlist:** maps that pass every tier-1 check go to a new tier P, "pending owner review". The owner places them.
- **Eligible today:** only ne_plains_wh11 (border/ne_plains_wh11-r2-all).

## Next

- Renderer caption: the summary page says "±10%" even for channels widened to ±15%. Small fix.
- Fewer splits: #103, #115; #119 only if "minimal" is wanted. #118 any time.

## Blocked

- Owner: place tier-P maps; #124's defaults; WH 10 or any band widening (OD1).
- #112 general rule; #111, #83; swap rule B (#85); #3, #59, #75, #76.
