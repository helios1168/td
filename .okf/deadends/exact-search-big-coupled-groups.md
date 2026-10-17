---
type: Deadend
title: Exact search finds no drawing of the big coupled groups in 2 hours (the warm-start chain stays the practical path)
description: On the four exported hard groups (500-1,800 free ZCTAs), draw.py complete, a HiGHS cut loop and SCIP lazy cuts all returned no drawing inside 2 hours single-threaded; lower bounds were close, so feasibility-finding is the bottleneck. HiGHS's lazy callback is unusable.
tags:
- deadend
- drawing
- branch-and-cut
- scip
- highs
status: stable
generated:
  by: session-reviewer/glm-5.3
  at: 2026-10-17T10:45:49Z
verified:
- {by: 'human:owner', at: '2026-10-17T22:05:20Z'}
state: ACCEPTED
kind: deadend
evidence:
- pi-session:01a13930-cf7a-75cb-9a2d-ab837963b1be#8885ad4b
- pi-session:01a13930-cf7a-75cb-9a2d-ab837963b1be#f87f315d
- pi-session:01a13930-cf7a-75cb-9a2d-ab837963b1be#14f3770b
uses: []
supersedes: null
history:
- {at: '2026-10-17T10:45:49Z', from: null, to: STAGED, by: session-reviewer/glm-5.3, gate: intake}
- {at: '2026-10-17T22:05:20Z', from: STAGED, to: ACCEPTED, by: 'human:owner', gate: owner, result: pass, review_id: 242985e3-860c-4f9f-9559-16b8e9f39f37}
---

Four hard groups exported from `tools/exp/contig/draw.py`'s own model - FI PA 1,833 free ZCTAs / 4 districts / 12,115 columns; FI FL 1,013 / 3 / 5,619; FI NY 223 / 5 / 1,167; WIFI MD 477 / 3 / 2,567, each matching the original run's recorded row and column counts - were given to three exact methods under 2-hour, one-thread limits: draw.py's complete model, a HiGHS separate-and-re-solve loop, and SCIP lazy a,b-separator cuts. None returned a connected in-window drawing for FI PA, FI FL or WIFI MD (FI NY was proved infeasible and is claimed separately). FI PA only re-reported the start it was handed (5.3% gap) and the search found nothing new; the rest were no-answers. The root bounds sat close (FI PA: 3,999 against the start's 4,219), so finding a feasible drawing is the bottleneck, not proving optimality; single-threaded lazy cuts are no breakthrough at 500-1,800 free ZCTAs. HiGHS's undocumented lazy-constraint callback (highspy `kCallbackMipDefineLazyConstraints`, arm d) never fired - unusable.

The 2026-10-14 'exact drawing' runs that timed out on these groups never reached this complete model: the restricted DAG-first stage (`draw.py:409`, `for dag in (True, False)`) consumed the whole budget, so those runs never proved anything about exact solvability. With that corrected, the practical chain stayed: build a first drawing (heuristic fill allowed), then exact local window repair - which produced all the passing maps - and use targeted SCIP windows for infeasibility questions.
