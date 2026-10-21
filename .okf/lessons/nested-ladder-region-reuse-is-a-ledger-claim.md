---
type: Lesson
title: 'A region marked ''reused'' in a merged nested-ladder map is a ZIP-ledger claim, not a manifest-source claim: verify assignments across Ks, and expect a redrawn region to move every line and its splits, not just the one new district'
description: 'Each IFA K is a merge of six regional runs; the manifest''s params.sources names source folders, but only the per-K ZIP ledgers prove what a region carried over — the reuse claim was verified from ledger assignments, not names. Verified: each step K→K+1 changes exactly one region (+1 district; Mid-Atlantic 12, South Atlantic 9/10, West 7/8 each when redrawn) and the rest are identical down to the ZIP (New England ×4 and South Central ×6 never change across all seven Ks); a redrawn region comes from a different run so every line in it can move, and the split-state list follows the redraws — 21, 21, 21, 19, 18, 18, 21 split states for K48..54 (AZ/NV drop at the K51 West redraw, return with OR at K54).'
tags:
- lesson
- ifa
- k-grid
- merge
- ledger
- verification
- reuse
- splits
status: draft
generated:
  by: session-reviewer/glm-5.3
  at: 2026-10-21T08:18:32Z
state: STAGED
kind: lesson
evidence:
- pi-session:01a1502d-5d27-7021-af2f-34b768910beb#85469cf9
- pi-session:01a1502d-5d27-7021-af2f-34b768910beb#80d75b11
uses: []
supersedes: null
history:
- {at: '2026-10-21T08:18:32Z', from: null, to: STAGED, by: session-reviewer/glm-5.3, gate: intake}
---

Every IFA K-map is a merge of six regional runs (`merge.py`; `manifest.json` params.sources names the six source folders). Two durable lessons from the 2026-10-18 read:

1. "This region was reused" is a ledger claim, not a manifest claim. The manifest records only source-run names — the merge step could in principle have moved ZIPs — so the reuse conclusion was drawn by comparing each region's ZIP→district assignments between consecutive Ks: identical assignments means true reuse. Result: each step K→K+1 changes exactly one region and adds exactly one district. The change order: Mid-Atlantic 11→12 (K49), South Atlantic 8→9 (K50), West 6→7 (K51), Midwest 13→14 (K52), South Atlantic 9→10 (K53), West 7→8 (K54). New England (4 districts) and South Central (6) are unchanged, ZIP for ZIP, across all seven maps (re-checked at review: the New England ZIP→district sets of K48 and K54 are identical).

2. A changed region is a full redraw, not one carved split. It comes from a different regional run, so every district line inside it can move: the South Atlantic's τ went $1,378M → $1,225M → $1,103M across its redraws, and nothing inside a redrawn region is comparable across the redraw. A region-local count therefore tracks its region's redraws, not K: the split-state list on the sealed maps is 21, 21, 21, 19, 18, 18, 21 for K48..54 — the West 6→7 redraw at K51 drops AZ and NV (−2), the Midwest 13→14 redraw at K52 drops IN (−1), the South Atlantic redraw at K53 leaves the count unchanged, and the K54 West 7→8 redraw brings AZ, NV and OR back (+3). A mid-ladder dip in a state list is a redraw signature, not a combinatorial optimum.

The maps use the project's six IFA regions from `scenarios/regions/ifa/`, not Census divisions.
