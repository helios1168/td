---
type: Lesson
title: 'A solver segfault is a crash, not evidence: contain SCIP''s time-limit faults and retry once with heuristics off'
description: SCIP faults at its own time limit (six P3 crashes on one nw49-48 window). The landed fix records the crash, retries once with heuristics off (the same window solved to optimal in 261 s), files unknown rather than infeasible or connected, and never grows a window from a crash.
tags:
- lesson
- solvers
- scip
- robness
- signals
status: stable
generated:
  by: session-reviewer/glm-5.3
  at: 2026-10-17T10:46:11Z
verified:
- {by: 'human:owner', at: '2026-10-17T22:05:20Z'}
state: ACCEPTED
kind: lesson
evidence:
- pi-session:01a13930-cf7a-75cb-9a2d-ab837963b1be#504934d0
- pi-session:01a13930-cf7a-75cb-9a2d-ab837963b1be#34e05f1e
uses: []
supersedes: null
history:
- {at: '2026-10-17T10:46:11Z', from: null, to: STAGED, by: session-reviewer/glm-5.3, gate: intake}
- {at: '2026-10-17T22:05:20Z', from: STAGED, to: ACCEPTED, by: 'human:owner', gate: owner, result: pass, review_id: 242985e3-860c-4f9f-9559-16b8e9f39f37}
---

SCIP 6.2.1 (PySCIPOpt) segfaulted six times in the P3 campaign on one nw49-48 repair window - always at its own time limit - while the same window solves in about five minutes with SCIP's heuristics off. The root cause of the fault is unknown; what landed (2026-10-16, `tools/exp/bnc/scip_engine.py`, commits 986a6ca, 4766b62 and cca6fa9 through the #143 landing) contains it:
- SCIP runs in an isolated child process, so a crash is recorded as a result and cannot take down the driver;
- the window is retried once with heuristics off, and the retry gets the full time limit again - on the real nw49-48 window the retry solved to optimal in 261 s and the district went from one detached piece to none;
- a crash never counts as infeasible, so it never triggers window growth: growth follows only a proof;
- a crash late in a solve cannot be masked by an earlier connected drawing: the window files as unknown, not connected;
- a cancelled window stops its SCIP child, SIGTERM/SIGINT are held across the child's creation, and the blocked signal mask is restored on every exit from `solve_isolated`.

The design principle: a crash is missing evidence, and missing evidence must read as unknown - treating it as infeasibility would silently grow repair windows on noise, and treating it as success would present an unverified drawing. A crashed solve can now cost up to twice its limit (the retry is a fresh one), which is the accepted price. The outstanding follow-up is the fault's actual cause at the time limit.
