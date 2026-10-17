---
type: Deadend
title: 'Hard shape gates from calibrated metrics failed: no 2026-10-14 metric rule reproduced the owner''s verdicts beyond its sample'
description: 'Fitting two blind sheets (74 distinct districts, 16 owner rejects): best rule (cut edges >= 126 AND bite >= 0.18) reached 8 errors and failed cross-sheet; arm share, roughness and water wrap were no better than the baseline. Shape stayed solver-level plus the owner''s eye, and a cut-sinuosity measure was deferred.'
tags:
- deadend
- looks
- shape-metrics
- calibration
- m1
status: draft
generated:
  by: session-reviewer/glm-5.3
  at: 2026-10-17T10:46:11Z
state: STAGED
kind: deadend
evidence:
- pi-session:01a13930-cf7a-75cb-9a2d-ab837963b1be#ac73b40c
- pi-session:01a13930-cf7a-75cb-9a2d-ab837963b1be#aefd13b0
uses: []
supersedes: null
history:
- {at: '2026-10-17T10:46:11Z', from: null, to: STAGED, by: session-reviewer/glm-5.3, gate: intake}
---

Calibrating hard shape limits from the owner's eye: two blind sheets of 40 districts each, 80 verdicts, 74 distinct districts, 16 rejected. Nothing separated clean:
- best single measure, cut edges >= 165: 11 errors of 74; bite >= 0.17: 11;
- best combination, cut edges >= 126 AND bite >= 0.18: 8 errors;
- the new tentacle measures (arm share at 5/10/20/40 km), roughness and water wrap: 15-16 errors - no better than rejecting nothing;
and each rule fitted on one sheet failed on the other (6-9 errors), so any threshold picked then would have been fitted to the sample. Two rejects are explained by no measure: the Lake Michigan wrap (whole states, no ragged cuts) and C29. The 5-40 km shrinking-and-regrowing tentacle measures miss the fine, ZIP-scale fractal edge the owner was reacting to; a cut-sinuosity measure (cut length against chord) was deferred as the better next try.

Why M1 cannot catch this: the gate fails a district only when a part holding at least 5% of its land hangs off a narrow passage, and small fringes off a larger body 'are never added together' (the 2026-10-06 rule), so a fractal district of many thin arms each under 5% passes by design - tentacles are a shape problem, not contiguity. Tightening M1 to flag small parts had failed before (#121): single dense downtown ZCTAs and coastal slivers became necks and no map could pass. The resolution: contiguity and the band stay the exact hard gates, shape stays in the drawing objective (perimeter cost) plus flag-and-rank with the owner's eye deciding, and the 2026-10-15 maps passed on the eye. Calibration data: `runs/exp/looks_calibration_2026-10-14/` (gitignored).
