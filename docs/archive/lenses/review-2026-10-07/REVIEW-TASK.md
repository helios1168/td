# Design review: will issues #103, #129 and #130 reach the goal?

You are a design reviewer from outside the team that wrote these issues. The work has **not
started**: no code is written and the lanes are on hold until this review. Your job is to say,
before we spend about a day of agent time, whether building exactly what these three issues
describe will produce **maps in which every district passes M1, with as few state splits as
possible, and that are eligible**. Where it will not, say what to change.

Read-only: read files, never edit anything in the repository. The one file you write is your report (see Report format). The owner may talk to you directly in this session; answer them. The repository is the td checkout in your working directory.
Sales data, rep names and firm names are confidential and must not appear in your report; descaled
opportunity (m_rel) and $ per district are fine.

## Read, in this order
1. `/tmp/iss/acb/review/BRIEF.md`: the goal, the evidence so far, the pipeline in one page.
2. `WATCHDOG.md`: the goal, the mandates (M1 exactly), the ranking and the open owner decisions.
   This is the yardstick.
3. The three issue bodies as filed:
   - `/tmp/iss/acb/review/issue-103.md` (A). The 2026-10-07 amendment is appended at the end, after
     the original B2 body.
   - `/tmp/iss/acb/review/issue-129.md` (B, the carver).
   - `/tmp/iss/acb/review/issue-130.md` (P, the pipeline).

   The shared contract is inside each body.
4. Background, as needed:
   - `docs/problem/SPLITS.md` §3 and §5: the master and the F2 formulation.
   - `docs/MODEL.md` §3 (the master), §4.7–4.9 (Proposition D, drawable alone, the support-ban
     proofs) and §9 (the audit).
   - `td/audit.py`: `district_pieces`, `district_necks` (the M1 gate) and `border_cm`.
   - `tools/exp/contig/plancheck.py`: `drawable`, `wide_rows`, `grow`. This is #124's
     single-district MILP, which B generalises.
   - `tools/exp/contig/wholeplan.py`: `loop`, #127's check-and-ban, which P extends.
   - `docs/RESULTS.md`: the history behind the brief.

## Part 1: your own review (do this before reading Part 2)
Answer each question with evidence (file:line, or a short argument). Say plainly when you do not
know.

1. **Goal fit.** If all three issues are delivered as written, does the result produce M1-clean,
   eligible maps with minimal or near-minimal splits for FI K 20, IFA K 46–49, and a complete main
   map (national, WH, FI and WIFI)? What is the most likely way it ends without a usable map?
2. **Correctness of the exact pieces.**
   - Is F2 with rule C a correct count of split states, in the scorer's sense, given n_S integer
     copies, η and the aggregate mass rows?
   - Is the carver's model, with the attach set contracted to one root, wide-passage rows and lazy
     NeckCut rows, a **relaxation** of "piece ∪ attach states passes M1 in its mass window"? It
     must be, for "infeasible" to justify a ban.
   - Is P's no-good cut, written Σ_{S∈Q} n_S ≤ |Q| − 1, valid and exact for what the carve proved?
3. **Tractability.** #124's single-district MILP proved nothing infeasible and timed out on the
   hard Northeast cases. Is a k-piece MILP over a whole state (NY about 1,800 ZCTAs in 4 pieces,
   CA about 1,700) likely to return ok within 900 s? What would you do instead or in addition? Is
   exactness needed for ok results, or only for bans?
4. **The contract.** Can P actually re-plan with A's split-minimising master and its cuts, using
   only what the contract defines? Is anything missing: a re-plan API, per-copy shares when
   n_S > 1, which δ the carve uses, the IDs of near-tied plans?
5. **The ranking.**
   - Splits, then cuts, then defects, then shape, then balance. Does the pipeline optimise these in
     that order?
   - A's pass 2 minimises diameter; the ranking puts cuts second.
   - B minimises cut border length.
   - Is anything that matters to the owner, such as looks or balance, left to chance?
6. **Scope and parallelism.**
   - Is each issue executable by one worker within a 2 h stage, without needing to ask?
   - Do the three lanes really parallelise, or does P need A's and B's code to do anything
     meaningful?
   - Should #103's original B2 acceptance (sweep runs, drawn maps, the top 3 eligible maps per
     target, the F6 cross-check) still apply now that P draws the maps?
7. **Mandates and open decisions.**
   - Does any issue weaken M1, measure something easier than the goal, or call a result
     "minimal", "eligible" or "done" before it is?
   - Does any issue settle an open owner decision by default? In particular #102 (how M1 is
     achieved), #112 (what gives way: here the re-plan may add splits, s* + g), OD1 (the bands)
     and OD4 (county pieces).
8. **Anything else** that would make you stop the wave.

## Part 2: the orchestrator's own concerns
Rate each one **confirmed / refuted / partly**, with a reason, and say whether it blocks the wave.

- **C1. Contract gap.** P has no defined way to call A's split-count master with rule C and its
  no-good cuts. Without one, P falls back to `td.master`'s diameter objective and loses the
  minimal-split property.
- **C2. The cut is wrong as written.**
  - n_S is an integer count of copies. When a support is used twice, Σ_{S∈Q} n_S ≤ |Q| − 1 bans
    too much.
  - The cut also bans plans that keep every support in Q but add another district holding the
    same state, which is a different carve problem that was never proved infeasible.
  - It must exclude exactly the configuration of σ's holders that was proved infeasible.
- **C3. Exact-only carving will stall** the way #124 did. B should first find a feasible carve
  fast: a constructive heuristic or ReCom, checked by the exact M1 gate, which is the source of
  truth. The exact MILP would run only to prove infeasibility, or as a fallback.
- **C4. Pass 2 should minimise cuts before diameter,** to follow the ranking.
- **C5.** The per-district `share` in `plan.json` is undefined when n_S > 1 copies of {σ} split
  t_{σ,S} among them, because the mass rows are aggregated over the copies.
- **C6.** #103 carries its original B2 acceptance (drawn maps through sweep.py, the top 3 eligible
  per target) on top of the amendment. That is too much for one Sonnet lane, and it overlaps P.
- **C7.** P's run order omits WIFI, so the main map is incomplete.
- **C8.** Because the pipeline answers a proved-infeasible carve by re-planning, possibly with
  more splits, it settles #112 by default. The owner should confirm that rule.
- **C9.** Two mechanical problems: `## Files` and `## Read first` are not written as bullets with
  backticked paths. The wave tooling therefore reads an empty file list, and its gate would block
  every change.

## Report format
1. **Verdict, one line:** `GO`, `GO WITH CHANGES` or `STOP`.
2. **Will it reach the goal?** One paragraph naming the most likely failure.
3. **Findings, most serious first.** Each finding gives: the issue (#103, #129, #130 or the
   contract); what is wrong; evidence; the exact change to the issue text, with the replacement
   wording where you can; and whether it blocks.
4. **The Part 2 ratings,** one line each.
5. **Proposed changes to the plan,** if you would restructure: lanes, order, a fallback.
6. End with `LEARNED: ...` lines, or `LEARNED: none`.

Write the report to `/tmp/iss/acb/review/report-<your model>.md` (`fable` or `astra`) and also show it in the chat. Rewrite that file if the owner's questions change your findings.
