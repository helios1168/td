
## Goal
Given one split state and the pieces the master planned for it, assign every ZCTA of the
state to a piece so that, for each piece, the piece plus the whole states it attaches to passes
M1 (one connected piece on the 2025 ZCTA polygons, no neck), inside the piece's mass window.
The output is exact: ok, infeasible (proved) or unknown (timeout). Part B of the A+C+B pipeline
(owner, 2026-10-07). Runs in parallel with #103 (A) and #130 (P), against the shared contract.

## Plan
1. **Model:** `tools/exp/contig/carve.py`, a k-piece generalisation of `plancheck.drawable`
   (the single-district MILP, Proposition B, docs/MODEL.md §4.9).
   - Variables: x[z,i] for each ZCTA z of the state and each piece i, with Σ_i x[z,i] = 1.
   - Mass window per piece.
   - Connectivity by single-commodity flow per piece, rooted at the attach set contracted to one
     node. A piece with an empty attach set gets a root-choice binary.
   - Wide-passage rows (at least 10 km between held bodies) and lazy NeckCut rows, as in B.
   - Approved connectors are honoured exactly as M1 does.
   - Objective: minimise the total length of the cut border between pieces, so cuts are short
     and clean. Ties go to compactness.
2. **Warm start** from the state's split in the nearest existing drawn ledger, when one exists,
   or from #127's county pieces. A start that breaks M1 is still a valid MIP start for the
   assignment rows.
3. **Proof.** Extend Proposition B to k pieces with contracted attach sets, in docs/MODEL.md
   §4.10. The claim to prove: any assignment the model accepts gives pieces that are connected
   and neck-free once their attach states are added, and every such assignment is feasible in
   the model, so "infeasible" is a valid ban. The attach state's own internal necks are out of
   scope and are caught by P's exact gate.
4. **Measure on real states**, using shares from an existing plan: NY in 4, CA in 4, TX in 3,
   PA in 3 and FL in 3 (FI and IFA sizes). Record times, status and border km.

## Files
tools/exp/contig/carve.py, tests/test_carve.py, docs/MODEL.md (§4.10), docs/CODE_MAP.md,
docs/RESULTS.md

## Acceptance
- **Toy tests:** a state whose only feasible carve needs a non-obvious cut; a necked carve that
  is rejected; a proved-infeasible case (a piece's attach set touches the state only through a
  pinch under 10 km); a timeout reported as unknown.
- **Real carves:** every ok result, joined with its attach states, passes `td.audit` M1 by the
  gate (the exact check, not the model).
- **Proof:** §4.10 is checked by an other-vendor verifier and tagged [proved] or [claimed].
- **Measurements** for the five real states above are posted on the issue.
- `"$TD_PY" tests/run_all.py` passes.

## Read first
docs/MODEL.md §4.9; tools/exp/contig/plancheck.py (drawable, wide_rows, grow);
tools/exp/contig/pieces.py; td/audit.py (district_necks, border_cm);
docs/memory/facts/highs-traps.md; geography-traps.md; the contract.

## Lane (owner, 2026-10-07)
- Worker: `worker-advised` (sv-ntlee agent/pi/agents/worker-advised.md) on `claude-bridge/claude-opus-5-5:high`, one lane of a single `/wave` on m5, at most 6 solver processes.
- Advisor: Sol 6.1 xhigh through `ask_advisor`, on Anthropic's advisor timing (after orientation and before the first write, when stuck or changing approach, before declaring done once the result is committed). The orchestrator checks each call in the transcript and resumes the worker if it wrote code without one. The advisor is not review.
- Review: a Sol 6.1 reviewer on the diff, which also verifies the MODEL.md proof as the other vendor.

## Contract (shared with #103 and #130)
The three lanes are built at the same time against this contract. Each lane's first commit is
a stub that reads and writes these files, so the others can build against it.

### plan.json (A writes it, P reads it). One file per channel and plan.
```json
{
  "channel": "FI", "K": 20, "delta": 0.10, "tau": <float m_rel>,
  "rule": {"one_split_per_district": true},
  "split_states": ["CA", "NY", ...],                 # s_v = 1
  "certificate": {"s_star": 5, "lower_proof": "infeasible|unknown", "gap": 0.0},
  "districts": [
    {"id": "FI_01", "whole": ["NV", "UT"], "split": "CA" | null,
     "share": <mass of the split state's piece, m_rel>, "mass_lo": <float>, "mass_hi": <float>}
  ],
  "pool_rank": 0                                     # 0 = the chosen plan; 1.. = near-tied plans
}
```
The mass window is the piece's allowed mass: [τ(1-δ) - M(whole), τ(1+δ) - M(whole)],
clipped so the state's pieces sum to M(σ).

### carve job (P writes one per split state, B reads it)
```json
{"channel": "FI", "state": "CA", "delta": 0.10, "time_limit": 900,
 "pieces": [{"district": "FI_04", "mass_lo": ..., "mass_hi": ..., "attach": ["NV", "UT"]}, ...]}
```
`attach` is the whole states the piece must join to make its district; empty means the piece is
the whole district.

### carve result (B writes it, P reads it)
```json
{"state": "CA", "status": "ok|infeasible|unknown", "stop": "<engine stop reason>",
 "assign": {"<zcta>": "FI_04", ...},             # status ok only; every ZCTA of the state
 "border_km": <cut length between pieces>, "seconds": <float>}
```
"infeasible" only on a solver-proved infeasibility of the exact model. A timeout is "unknown"
and never becomes a ban.

## Blocked by
None. Builds against the contract.

