---
type: Lesson
title: Map labels must come from the gate's whole-map verdict on unrounded full-extract dollars; every derived scorer drifts
description: A CONUS-only merged extract read FI about 2% high; IFA is stored in relative units (x1.252) and `score.py` had no per-district IFA numbers; the gate compared rounded; the IFA index matched names, not verdicts. The fixes landed and an independent re-gate confirmed all 12 labelled maps.
tags:
- lesson
- scoring
- labels
- gate
- verification
status: draft
generated:
  by: session-reviewer/glm-5.3
  at: 2026-10-17T10:45:49Z
state: STAGED
kind: lesson
evidence:
- pi-session:01a13930-cf7a-75cb-9a2d-ab837963b1be#f3b953c3
- pi-session:01a13930-cf7a-75cb-9a2d-ab837963b1be#8d3b7eb5
- pi-session:01a13930-cf7a-75cb-9a2d-ab837963b1be#07768472
- pi-session:01a13930-cf7a-75cb-9a2d-ab837963b1be#65768338
uses: []
supersedes: null
history:
- {at: '2026-10-17T10:45:49Z', from: null, to: STAGED, by: session-reviewer/glm-5.3, gate: intake}
---

Between 2026-10-14 and 2026-10-16 independent review found four ways a map could be labelled without earning it:
- the sealed driver scored from the merged map's own data file, which holds only CONUS cells, so FI districts read about 2% high (FI_04 showed $1,054M and was really $1,031M); the warm-start 'FI over the cap' verdicts were this artifact;
- IFA runs store relative units and need the 1.252 $M-per-unit conversion (`merge.py`), while `tools/looks/score.py:509` produced only an IFA average, so a first re-gate pass read IFA districts about 20% low with 17-44 of them apparently under the window;
- the dollar gate compared after rounding (then `score.py:346`);
- the IFA index decided pass from per-district run records plus a district-name match, ignoring the gate's whole-map verdict including coverage, and the sealed driver ignored a failed gate's exit code.

The fixes on main (merged with the #143 landing, 2026-10-16): a pass requires the gate's full item list, dollars compared unrounded from the full extract, a real per-district IFA gate, Manhattan identified by county (36061) not name, and a failed gate blocks the label. An independent verifier then re-ran the exact gate over the stored ledgers on copies of every labelled-passing map (`runs/exp/national_2026-10-14/REGATE_2026-10-15.md`): all 12 - the four main maps, the re-run ne-48-bal, and IFA K48-54 - held.

The durable rule: every derived scorer, index or caption drifts from the gate; only the gate's own whole-ledger verdict on unrounded full-extract dollars decides eligibility, and periodic independent re-gates on untouched copies keep labels honest.
