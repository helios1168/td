---
type: Formulation
title: F2.W whole-unit window planning
description: 'Fixed-window master of F2 with whole-unit ownership: pointers to its statement, spec, code and conformance test.'
tags:
- formulation
- f2
status: draft
generated:
  by: process:migration
  at: 2026-10-17T09:29:57Z
state: STAGED
kind: formulation
evidence:
- docs/MODEL.md#3.6.6b
uses: []
supersedes: null
history:
- {at: '2026-10-17T09:29:57Z', from: null, to: STAGED, by: 'process:migration', gate: intake}
form_id: F2.W
statement: docs/MODEL.md#3.6.6b
spec:
  runtime: pyomo
  entry: td/formulation/f2w.py:build_model
  max_instance:
    zips: 300
code: tools/exp/contig/wholeplan.py:loop
relation:
  to_reference: heuristic
  parent: F2
  to_parent: unstated
tests:
- tests/test_formulation_wholeplan.py
certifies: reduced fixed-window master agrees with F2 on a 30-ZCTA instance
---

**Relation to F0: heuristic overall.** This is F2 with fixed routing, K, family and whole-unit ownership, followed by raw-gate support checks; it does not optimize F0 or implement its Manhattan exception. Its fixed-window master has the following reduced specification.
