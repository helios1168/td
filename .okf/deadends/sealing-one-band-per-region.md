---
type: Deadend
title: 'Sealing the Northeast corridor failed for the main map: one average-centred band per region cannot plan a disconnected rest'
description: 'With a corridor sealed, the rest region splits into disconnected dollar-blocks whose densities differ; one band centred on the region average fits neither. Ruled out one cause at a time: the state cap, the split lists and the drawable-only check were not it. Sealing costs feasibility, not splits.'
tags:
- deadend
- sealing
- planning
- band
- regions
status: draft
generated:
  by: session-reviewer/glm-5.3
  at: 2026-10-17T10:45:49Z
state: STAGED
kind: deadend
evidence:
- pi-session:01a13930-cf7a-75cb-9a2d-ab837963b1be#9ca7434a
- pi-session:01a13930-cf7a-75cb-9a2d-ab837963b1be#2de6ee84
- pi-session:01a13930-cf7a-75cb-9a2d-ab837963b1be#14f3770b
uses: []
supersedes: null
history:
- {at: '2026-10-17T10:45:49Z', from: null, to: STAGED, by: session-reviewer/glm-5.3, gate: intake}
---

The 2026-10-14 sealed overnight ran the main map with a Northeast corridor fenced off and the rest planned as one region per channel; 9 of 18 region runs failed planning on m5 and every 'rest' region failed on m2. Testing causes one at a time on ne-48-bal's rest region ruled out the drawable-only check, the 4-state district cap (even raised to 6) and narrow split lists (even widened to 9 WH split states). The confirmed cause: with the WIFI states removed, the rest falls into a western block (WA, OR, CA, NV, AZ, UT, CO) and an eastern block that do not touch each other, while the region keeps one symmetric band centred on its average district - the western block's districts average about $900M, just below the $918-1,150M band, even though $900M is inside the dollar window. Another rest region (21 states, national K6) was proved unplannable in its band; the corridor's own coupled NY-NJ-PA-MD-DC drawing also ran out of time. The night ended 1 of 15 points passing, and that point was the unsealed 2026-10-13 ne-48-bal, whose plan had used corridor states (NY, NJ, PA) as filler.

The obstacle is not mathematics: channels are independent given K and routing, and the blocker was the merge tool requiring the regions' ZIP sets to be disjoint (`merge.py:87`), not the four-channel structure. No single corridor variant passed every point (B1 fails the FI channel at ne-52-bal; the arithmetic's best variant differs per point), so the partition would have to move per point. Sealing remains the right frame for IFA, whose six predefined regions pass at every K48-54; the main map moved to the unsealed window band instead. Sealing's cost was feasibility (zero extra splits in dollar-window arithmetic), which is the opposite of what was feared.
