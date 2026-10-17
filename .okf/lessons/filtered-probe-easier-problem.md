---
type: Lesson
title: 'A channel-filtered probe solves an easier problem: slicing the data can drop states silently, and feasibility conclusions do not transfer'
description: A feasibility probe filtered to the national channel silently dropped ND/SD, solved an easier instance, and reported 1,200 km district caps sufficient; the full data needs 1,500 km. Feasibility probes over a channel slice must be re-run unfiltered before committing compute.
tags:
- lesson
- probes
- validation
- feasibility
status: stable
generated:
  by: session-reviewer/glm-5.3
  at: 2026-10-17T10:46:11Z
verified:
- {by: 'human:owner', at: '2026-10-17T22:05:20Z'}
state: ACCEPTED
kind: lesson
evidence:
- pi-session:01a13930-cf7a-75cb-9a2d-ab837963b1be#0b7fd8f3
uses: []
supersedes: null
history:
- {at: '2026-10-17T10:46:11Z', from: null, to: STAGED, by: session-reviewer/glm-5.3, gate: intake}
- {at: '2026-10-17T22:05:20Z', from: STAGED, to: ACCEPTED, by: 'human:owner', gate: owner, result: pass, review_id: 242985e3-860c-4f9f-9559-16b8e9f39f37}
---

The nw49 feasibility probe that chose the 1,200 km district distance cap had cut its input to the national channel alone. The filter silently dropped ND and SD from the data, so it solved an easier instance and reported 1,200 km sufficient - and the launched runs still had no plan at 1,200 km. Re-run on the full data, national plans at 1,500 km and fails at 1,200; nw49-48 and nw49-50 were relaunched at 1,500 km and planned.

Generalizing: feasibility is not preserved under slicing. A probe over one channel, corridor or region answers only the slice's question, and the slice can quietly lose territory (here two whole states vanished from a national-footprint question). Any upstream conclusion a filtered probe feeds - distance caps, split lists, K values, partitions, carve-first sizing - must be re-run on the unfiltered data before solver time is committed to it. The same session's channel-by-channel arithmetic was only trusted because its blockers (New England's $355M, the WIFI Plains) were checked against whole-channel footprints.

This trap bites hardest exactly where it hid: the probe's conclusion looked like the cheapest kind of evidence (a small, fast run), which is why its refinement on the full extract was cheap and worth it.
