---
type: Lesson
title: 'An empty-geometry district made `colouring_far` give every later district the first palette colour: skip empty geometries in distance colouring, and its regression test still needs the owner''s words'
description: 'The #144 review''s only concern: in `tools/maps/zip_pages.py` `colouring_far`, a district with no polygon scored NaN on every colour, so all later districts silently took the first palette colour. Fixed one-line in a066bb4 (none of the seven committed maps was affected); the reviewer''s suggested regression test was not added — `tests/` is an owner-words path, so that gap is open for the owner.'
tags:
- lesson
- rendering
- colouring
- zip-pages
- silent-failure
- regression-test
status: draft
generated:
  by: session-reviewer/glm-5.3
  at: 2026-10-18T08:13:36Z
state: CONTESTED
kind: lesson
evidence:
- pi-session:01a14bde-5509-737b-9142-90d7a3cde8f2#03a00828
- pi-session:01a14bde-5509-737b-9142-90d7a3cde8f2#17ad539f
- pi-session:01a14bde-5509-737b-9142-90d7a3cde8f2#89bf29a7
uses: []
supersedes: null
history:
- {at: '2026-10-18T08:13:36Z', from: null, to: STAGED, by: session-reviewer/glm-5.3, gate: intake}
- {at: '2026-10-22T00:48:25Z', from: STAGED, to: CONTESTED, by: 'human:owner', gate: owner, result: fail, reason: '"

    > Test', review_id: e4838505-34af-48dc-a6d0-e01a47f012c3}
---

The 2026-10-17 review of the IFA owner-page restyle (#144) came back "Review, no blocker" with one finding: in `tools/maps/zip_pages.py`'s `colouring_far` — the distance-aware greedy behind `--palette clean` (then `zip_pages.py:236`) — a district with no polygon makes every colour score NaN, the comparison never fires, and every district placed after it takes the first palette colour. No error, no warning: the map just comes out monochrome from the point of failure on. None of the seven committed IFA maps had an empty-geometry district, so no re-render was needed; the one-line fix — skip empty geometries ("a district with no polygon clashes with none") — went in as a066bb4 and landed with #144, suite green (688 passed).

The durable rule: a geometry-based colouring or layout loop must skip empty geometries before scoring; one NaN in the score table poisons every assignment after it, and a render whose districts collapse to one hue is a missing-geometry symptom to check before touching the palette. The gap: the reviewer's suggested regression test was deliberately not added, because `tests/` is an owner-words path (AGENTS.md) — the fix is guarded only by itself, and a test needs the owner's say-so.
