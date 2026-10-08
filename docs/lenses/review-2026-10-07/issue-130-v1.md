
## Goal
Strictly contiguous maps with the fewest state splits.
1. Take A's plan (#103, rule C on).
2. Carve each split state with B (#129).
3. Treat the pieces as whole units.
4. Check every district with the exact M1 gate.
5. Feed failures back to the master as exact no-good cuts.
6. Re-plan until every district passes, or report "no plan" with every cut and its reason.

Built in parallel with A and B against the shared contract, then integrated. Owner, 2026-10-07.

## Plan
1. **The loop, in `tools/exp/contig/pipeline.py`,** extending `wholeplan.loop` (#127):
   1. read `plan.json`;
   2. write one carve job per split state and run them in parallel processes, at most 6;
   3. assemble the ledger: whole states by unit, split states by the carve;
   4. run the M1 gate on each district's exact ZCTA set.
2. **Feedback, with exact cuts only.**
   - A carve proved infeasible adds the no-good cut Σ_{S∈Q} n_S ≤ |Q| − 1, where Q is the set of
     supports in the plan that hold that split state. The rule: not all of these together. The
     cut is valid only because B's mass windows are the plan's whole band; the proof goes in
     MODEL.md §4.11 and is verified by the other vendor.
   - A district that fails the gate after an ok carve bans its exact support with M1's reason,
     as #127 does. This can only come from an attach state's own internal neck.
   - unknown → retry once with a longer time limit, then report. Never a ban.
   - No state-pair bans.
3. **Balance pass,** splits fixed: the fixed-candidate LP from #103 pass 4, then a recarve at the
   new shares.
4. **Run order:** FI K 20 first, end to end. Then IFA K 46 and K 49. Then national 15 and WH 11
   on the ne_plains layout.
   - Each map is rendered with `tools/maps/render.py` and scored.
   - Shortlist: tier P if every tier-1 check passes; otherwise tier E with its failed checks
     named, or tier 3 if M1 fails.
   - The split count is reported against A's certified s*, as s* + g, and called "minimal" only
     at g = 0 under the stated rule.

## Files
tools/exp/contig/pipeline.py, tools/exp/contig/wholeplan.py, tests/test_pipeline.py,
docs/MODEL.md (§4.11), docs/RESULTS.md, docs/CODE_MAP.md, tools/shortlist/shortlist.json

## Acceptance
- **Toy end to end:** a plan whose first carve is proved infeasible gets a no-good cut,
  re-plans, and ends with every district passing M1. A timeout is never a cut.
- **FI and IFA K 46 maps:** each either passes M1 on every district by the gate, or reports
  "no plan" with all cuts. The issue gets a table of splits (s*, g), the band, the $ rule,
  defects and run times.
- `tools/mandates/check.py --tracking` passes for the new folders, and
  `"$TD_PY" tests/run_all.py` passes.

## Read first
tools/exp/contig/wholeplan.py (#127 loop and bans); docs/MODEL.md §4.9; td/audit.py (M1 gate); docs/memory/facts/highs-traps.md; docs/memory/facts/geography-traps.md; tools/shortlist/shortlist.json tier rules.

## Lane (owner, 2026-10-07)
- Worker: `worker-advised` (sv-ntlee agent/pi/agents/worker-advised.md) on `claude-bridge/claude-sonnet-5-5:high`, one lane of a single `/wave` on m5, at most 6 solver processes.
- Advisor: Sol 6.1 xhigh through `ask_advisor`, on Anthropic's advisor timing (after orientation and before the first write, when stuck or changing approach, before declaring done once the result is committed). The orchestrator checks each call in the transcript and resumes the worker if it wrote code without one. The advisor is not review.
- Review: a Sol 6.1 reviewer on the diff, which also verifies the MODEL.md proof as the other vendor.

## Contract (shared with #103 and #129)
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
None for the build.
- **Round 1** (this lane): build the loop against fixtures the lane writes from the contract, and pass the toy tests. Report the FI and IFA runs as pending integration, not as failed.
- **Round 2** (started by the orchestrator once #103 and #129 have landed): merge main, then run FI and IFA K 46 end to end for the map acceptance.

