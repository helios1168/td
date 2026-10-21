---
type: Lesson
title: 'The IFA K48–K54 ladder order was a 2026-10-13 judgement, not a formula: one region per step inside each region''s τ-window district caps, Mid-Atlantic deferred to last, K49–K51 balance the price'
description: 'How the nested IFA ladder decided which region takes each extra district: K52 = `ifa_conus_v2` anchor; one region redrawn per step (the per-K most-balanced alternative was declined: ~2x the region draws, no nesting); the $1,000–1,437.5M window caps each region''s district count (NE 4 only; Mid-Atlantic 10–13; South Atlantic 8–11; South Central 5–7; Midwest 12–16; West 6–8); the owner accepted the order that added South Atlantic first ($1,225M, highest τ), deferring the Mid-Atlantic (slowest redraw at NY''s Manhattan neck), at a measured cost: K49–K54 regional τ spread 301 vs the most-even 124.'
tags:
- lesson
- ifa
- k-grid
- ladder
- allocation
- balance
- region-totals
- decision-provenance
status: draft
generated:
  by: session-reviewer/glm-5.3
  at: 2026-10-21T08:18:32Z
state: STAGED
kind: lesson
evidence:
- pi-session:01a1502d-5d27-7021-af2f-34b768910beb#b090a91b
- pi-session:01a1502d-5d27-7021-af2f-34b768910beb#e684bbee
- pi-session:01a1502d-5d27-7021-af2f-34b768910beb#5eca654a
uses: []
supersedes: null
history:
- {at: '2026-10-21T08:18:32Z', from: null, to: STAGED, by: session-reviewer/glm-5.3, gate: intake}
---

Provenance: no formula chose the steps of the nested IFA K48–K54 ladder. On 2026-10-13 the supervisor session proposed the order by judgement (15:04 message) and the owner approved it unchanged ("go with your recommendations for all 3", 15:18); `~/.pi/briefs/ifa-kgrid.md` records the order as owner-approved but not the reasoning. When the owner asked on 2026-10-18 how the allocation had been determined, the reasoning had to be dug out of the 2026-10-13 session — it exists nowhere else. `docs/RESULTS.md:1330` documents the ladder's structure, not why each step went where.

The decision, as made:
- K52 is the anchor (the existing map, `ifa_conus_v2`); every other K builds outward from it — six new region draws in total: SA10, SA8, W8, W6, MW13, MA11.
- One region changes per step and the other five reuse their v2 region folders unchanged. The alternative offered and declined: the most balanced split chosen separately for each K, which would need about twice as many region draws and the Ks would not nest.
- The per-district window [$1,000M, $1,437.5M] (E2) caps each region's allowed district count. From the v2 region totals (New England $4,835M; Mid-Atlantic $13,142M; South Atlantic $11,027M; South Central $7,143M; Midwest+CO $16,811M; West $8,375M), the caps are: New England 4 only (5 districts → $967M, under the floor); Mid-Atlantic 10–13; South Atlantic 8–11; South Central 5–7; Midwest 12–16; West 6–8. These caps need no solver; they bound every allocation.
- Adding (K52→K54): South Atlantic first ($1,225M, the highest region τ), then West; the Midwest ($1,201M) and New England ($1,209M, which cannot gain) were passed over. Removing (K52→K48): Midwest, then West, then South Atlantic, then Mid-Atlantic. Within a region, the district goes to the state group whose τ moves least out of balance.
- The Mid-Atlantic was deferred to last because it is the slowest to redraw (NY, the Manhattan neck); the supervisor noted at the time that letting it lose a district first was "also defensible" (at $1,095M it has the lowest τ).

The balance that decision bought (ladder vs most-even split, computed in the 2026-10-18 session from the brief's region totals): K49 and K50 carry a region-τ spread of $301M where the most-even split sits at $124M/$103M (the Mid-Atlantic held at 12 districts → $1,095M while the West sits at $1,396M); K51 sits at $198M vs $35M; K48, K53 and K54 are close to their most-even alternatives. Every individual district stays inside the window at every K — this is balance between regions, not a pass/fail problem. Buying better balance on K49–K51 means redrawing the Mid-Atlantic, exactly the cost the ladder was designed to avoid, and that was weighed at the time.

Durable rule: a nested reuse ladder is a compute-budget decision, not an optimisation output. Record which allocation was declined and why, or the next session rediscovers the trade-off by archaeology; and while a region is reused unchanged, its τ — and its imbalance — is frozen across every K that reuses it.
