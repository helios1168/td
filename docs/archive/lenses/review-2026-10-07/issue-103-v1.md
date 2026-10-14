## Context
Part of the owner's 2026-10-04 experiment plan to finalize the main map (national / WH / FI plus combined channels) and the IFA map with as few channel-state splits as possible, looks first. The plan is drafted on m5 in gitignored `runs/plan_2026-10-04/EXPERIMENTS.md`; this body carries what the issue needs.

- **Eligible map:** the ledger audit passes at a plain ±15% band; main-map total K is 48–54; each channel's average $ per district is within ±10% of target (national $1.25B, WH $1.0B, FI $900M, IFA $1.25B; the combined channel's target is open).
- **Ranking:** (1) channel-state splits, fewest first (a state split in WH and in FI counts 2); (2) visual defects: thin links, pieces under 20% τ, crowded states, ZIP-contiguity pieces. A map with one split more but fewer defects than every map at the best split count stays, flagged `REVIEW`. (3) Shape: largest extent, then states per district. (4) Worst, then mean deviation.
- **Baselines:** NE + plains combined (`runs/sweep/comb_2026-10-02/s13/`), 13 splits, 50/50 within ±10%, but its WH 12 ($845M) fails the $ rule; its WH 10 ($1,014M, plans at 12.6%, CA and PA split) and WH 11 ($922M, 4.6%) variants are the new baselines. IFA K 49: 49/49 within ±10% but 22 split states (NY 6 ways, CA and NJ 5).
- **Worktrees:** one issue, one branch, one worktree (`/wave` lane on m5). Run output goes to the hub's gitignored `runs/exp/<lane>/` by absolute path, this lane's folder only; the extract and `data/public/` are read from `$TD_REPO`.

**Lane rules:** every run goes through `tools/exp/sweep.py` (the run-tracking issue) with the margin set by the #84 switch, writes one flat run folder (manifest, spec, run.json, solver.json, scorecard, districts, ledger, `map_<channel>.png`), and nothing else. Lane code lives in `tools/exp<lane>/` and `scenarios/experiments/`; production `td/` and `docs/MODEL.md` stay untouched.

**Lane B2 (as settled by #91's triage, `docs/lenses/COUNCIL_2026-10-05.md`):** F2: a binary s_v per unit with r_v = Σ_{S∋v} n_S ≤ 1 + (U_v − 1)·s_v, U_v = min(K, ⌊1/η⌋, cap_v, |Z_v|), plus 1 + s_v ≤ r_v so flags are exact outside optimisation. Fix s_v = 1 when M_v > U_c; no s_v for units forced whole. Candidates: all states (owner 2026-10-05); bans explicit with their cost. Never the pair row s_v ≥ n_S + n_T − 1 (invalid, finding 2). Passes, each pinned before the next (finding 3): (1) min Σ s_v, pin the chosen split set; (2) min cuts Σ (r_v − 1) (owner 2026-10-05: cuts break ties); (3) min diameter; (4) balance as a **fixed-candidate LP**: freeze the chosen plan's support counts and optimise its shares, worst then mean deviation, reported as conditional on that plan, not best among tied plans (owner 2026-10-05, decision B). Also export a **pool** of the next few plans tied or near-tied on passes (1)–(3), for #109 to draw; the scorer picks on the drawn map. No ε blend; do not use HiGHS's MIP lexicographic mode. Hall border rows (finding 11) are optional and reported if used. Splits are counted on the drawn map: a district owning any ZCTA of a state has split it (owner 2026-10-05). Also plans at tighter internal bands (±10%, ±12%) and audits at ±15%. Do not port the archive's home-state anchors (owner 2026-10-05).

## Goal
Lane B2 (new objective, same master, main and IFA) finds its best eligible maps under the owner's ranking and reports them against the baselines and the split floor.

## Files
tools/expb2/, scenarios/experiments/, tests/test_expb2_*.py, docs/CODE_MAP.md

## Acceptance
- Every run of the lane has a `manifest.json` with status `done`, or `failed` with the engine's stop reason, and appears in `runs/exp/index.jsonl`.
- A comment on this issue gives `tools/exp/table.py` output for the lane and its top 3 eligible maps per target (main, IFA where in scope), each with run folder, split count against the split floor, defects and worst deviation, or states that none is eligible and why.
- Each reported s* is certified (finding 4): μ ≡ 0 via #84's switch, mip_rel_gap = mip_abs_gap = 0, a validated incumbent, and a fresh master with Σ s ≤ s* − 1 proved infeasible; a timeout is reported as unknown. The floor is labelled with its policy class per #110: today's η-free master keeps cap_v, the support-size limit and drops zero-mass units, so s* is labelled "over 𝒳_c(δ) only" and never backs "minimal" or "must split" (owner 2026-10-05, decision A3; the all-M1 bound is #119); each drawn map reports s* + g, "minimal" only at g = 0.
- Where the cutoff layer of supersets of the forced set Φ is small (C(m − f, s* − 1 − f) solves), an F6 cross-check confirms s* (finding 5; same solver, so a formulation check only).
- Root gap, node count and pass times are recorded per channel (U53).
- `"$TD_PY" tests/run_all.py` passes.

## Read first
- docs/memory/facts/scenario-sweeps-2026-10.md
- docs/memory/facts/highs-traps.md
- docs/problem/PROBLEM.md (rows 2026-10-05)
- docs/lenses/COUNCIL_2026-10-05.md
- U53 in docs/problem/UNKNOWNS.md

## Blocked by
- [x] #84
- [x] #92
- [x] #91
- [x] #110







## Amendment (owner, 2026-10-07): part A of the fewest-splits pipeline

#103 is now part A of the pipeline for strictly contiguous maps with the fewest state splits. It runs in parallel with the carver (B, #129) and the pipeline (P, #130), against the shared contract below. P reads this issue's `plan.json`.

**Added to the lane:**
1. **Rule C as a switch, `one_split_per_district`.** The support family keeps only supports holding at most one splittable state; everything else in them is whole states. So no district holds pieces of two split states. Report s* with the switch on and with it off, per channel, so the cost of the rule is measured.
2. **`plan.json` export** per the contract: the chosen plan and a pool of near-tied plans. Each plan carries every district's whole states, its split state, its share and its piece mass window.
3. **Speed order:** FI (K 20) first, then IFA (K 46 and 49), then national 15 and WH 11 on the ne_plains layout. Post the first FI `plan.json` on the issue as soon as it exists; P is waiting for it.
4. **Band frontier, information only (owner, 2026-10-07):** report s* at ±10%, ±15% and ±20%. A band other than the scenario's is never adopted here; that is OD1.

The certificate protocol is unchanged: μ ≡ 0, both gaps 0, and the s* − 1 cutoff proved infeasible; a timeout is unknown. With the switch on, the floor is labelled "over C-rule supports in 𝒳_c(δ)".

**Files, widened:** add `docs/MODEL.md` (new §4.12 only: the proof that s_v counts split states exactly under rule C) and `docs/RESULTS.md`. The lane rule that `docs/MODEL.md` stays untouched is lifted for §4.12 alone.

**Acceptance, added:** with the switch on and off, a certified s* (or unknown) per channel at each of the three bands. A toy test where rule C changes s*. A `plan.json` for FI that validates against the contract. §4.12 tagged [proved] by the Sol verifier, or [claimed].

## Lane (owner, 2026-10-07)
- Worker: `worker-advised` (sv-ntlee agent/pi/agents/worker-advised.md) on `claude-bridge/claude-sonnet-5-5:high`, one lane of a single `/wave` on m5, at most 6 solver processes.
- Advisor: Sol 6.1 xhigh through `ask_advisor`, on Anthropic's advisor timing (after orientation and before the first write, when stuck or changing approach, before declaring done once the result is committed). The orchestrator checks each call in the transcript and resumes the worker if it wrote code without one. The advisor is not review.
- Review: a Sol 6.1 reviewer on the diff, which also verifies the MODEL.md proof as the other vendor.

## Contract (shared with #129 and #130)
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


