---
type: Lesson
title: 'Across the IFA K48–K54 ladder the district extremes never move: reused regions pin the range (Omaha $1,436.9M up, Waterbury–Shelton $1,007.8M down, ratio 1.43 at every K) and K moves the mean, never the range'
description: All 357 districts over the seven IFA maps sit inside $1,000M–$1,437.5M; measured against its own map's average the typical district deviates ±10.8% (1σ), 85% lie within ±15%, 97% within ±20%, the full spread is −21.1%/+26.5%, and the per-map mean falls $1,277.8M (K48) → $1,135.8M (K54) while the extremes stay put (Omaha $1,436.9M highest at every K; Waterbury-Shelton $1,007.8M lowest at K48–53, Salt Lake City-Murray $1,002.1M at K54; ratio 1.43); the slide-ready summary is "districts average $1.14–1.28B depending on K; typically within ±11%, all within −21%/+27%".
tags:
- lesson
- ifa
- k-grid
- balance
- dollars
- summary-metric
- stakeholders
status: draft
generated:
  by: session-reviewer/glm-5.3
  at: 2026-10-21T08:18:32Z
state: STAGED
kind: lesson
evidence:
- pi-session:01a1502d-5d27-7021-af2f-34b768910beb#9b1baa09
- pi-session:01a1502d-5d27-7021-af2f-34b768910beb#8ef49b82
- pi-session:01a1502d-5d27-7021-af2f-34b768910beb#5e2bdd7a
- pi-session:01a1502d-5d27-7021-af2f-34b768910beb#0c38e2e6
uses: []
supersedes: null
history:
- {at: '2026-10-21T08:18:32Z', from: null, to: STAGED, by: session-reviewer/glm-5.3, gate: intake}
---

The owner asked for each IFA map's balance and then a single number with an error band (2026-10-18). Measured on the sealed runs (`runs/exp/sealed_2026-10-14/ifa/K48..K54/districts.csv`, drawn mass × the manifest rate 1.2519681558; every figure re-verified in review against the same ledgers):

- Every district at every K is inside the window $1,000M–$1,437.5M. The per-map mean falls $1,277.8M (K48) → $1,251.7M → $1,226.7M → $1,202.6M → $1,179.5M → $1,157.2M → $1,135.8M (K54).
- The extremes never move with K: the largest district is IFA Omaha, NE-IA at $1,436.9M at every K (just under the ceiling); the smallest is IFA Waterbury-Shelton, CT at $1,007.8M from K48 through K53, until the K54 West redraw replaces it with IFA Salt Lake City-Murray, UT at $1,002.1M. Lowest-to-highest ratio: 1.43 at every K. Both extremes live in reused regions (Midwest, New England), so adding districts lowers the mean and leaves the range alone; narrowing the national range requires redrawing New England and Midwest, the two regions that span most of the window at every K.
- Per-map CV of drawn dollars: 10.3, 11.5, 11.8, 11.0, 10.9, 9.9, 10.1% — the middle Ks are the most even (K53/K54), K49/K50 the least, mirroring the ladder's regional imbalance (at K49–50 the West sits at $1,396M per district against the Mid-Atlantic's $1,095M).
- Deviations are lopsided in K: low K is skewed below the average (K48: +12.5% / −21.1%), high K above it (K54: +26.5% / −11.8%); closest to even at K50 (+17.1% / −17.8%).
- 8–11 districts per K sit within $25M of a window edge — passing, with little room.

The one number across all seven maps (357 districts, each measured against its own map's average): typical deviation ±10.8% (1σ); 85% of districts within ±15%; 97% within ±20%; full range −21.1% to +26.5%; average district size, averaged over the seven maps, $1,204.5M. Slide line: "Districts average $1.14–1.28B depending on K; typically within ±11%, all within −21%/+27%."

Reading rule: in a nested reuse ladder K moves the mean, not the range, and the range is pinned by the reused regions. A claim that a different K gives stakeholders "the same balance with a wider choice" must be checked against where the extremes sit, not against the mean.
