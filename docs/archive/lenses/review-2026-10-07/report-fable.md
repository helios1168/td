# Design review of #103 (A), #129 (B), #130 (P): will the A+C+B pipeline reach the goal?

Reviewer: Claude Fable 5.1, outside the team, 2026-10-07. Read-only. Evidence is `path:line` on the td checkout, or a short argument. Masses are descaled opportunity (m_rel) and τ multiples; no sales or names appear here.

## 1. Verdict

**GO WITH CHANGES.** The design is sound in its core idea, but five things in the text as filed would end the wave without a usable map or with a wrong certificate. Each has a short fix in the issue text. Items marked **blocks** must be changed before the lanes start.

## 2. Will it reach the goal?

The idea is right: with rule C, a district is one piece of one split state plus whole states, so M1 separates exactly into one carve problem per split state plus a gate check on every whole-state district. That is precisely the condition council finding 10 asks for (joint over each exchange component, every share), and it is what made #127's whole-unit loop reliable. The main map (FI 20, national 15, WH 11, WIFI 3) can plausibly come out of this M1-clean and eligible, since #125 already produced M1-clean eligible FI 20 maps at 12–13 splits with a weaker method. The most likely way the wave ends without a usable map is twofold. First, **IFA at K 46 and K 49 has no plan under rule C inside ±15%**: Connecticut is 1.25–1.33 τ at those K, so it must split, and its only whole-state neighbour is Rhode Island at about 0.33 τ, because New York and Massachusetts must split too; two CT pieces, one alone and one with RI, need at least 2·τ(1−δ) − 347 of mass, which exceeds CT's 1,334 until K ≥ 50 at ±15% (K ≥ 53 at ±10%, K ≥ 47 at ±20%). A would report "infeasible" at every band in the frontier and P would have nothing to carve. Second, at any K, **B's exact k-piece MILP on NY, CA, PA and TX will mostly return unknown at 900 s**, as #124's smaller single-district MILP did, and P as written turns unknown into "retry once, then report", which is "no plan". Both are fixable before launch: run the rule-C master over K 46–55 first (seconds per solve) and move IFA's target K or let the owner allow a declared two-state exception; and make B heuristic-first with the gate as the judge, keeping the exact MILP only for proofs, with a labelled policy fallback in P so unknowns never stall the loop.

## 3. Findings, most serious first

### F1. Rule C makes IFA infeasible at the issue's K (contract, #103, #130). **Blocks the IFA goal.**

What is wrong: #130 runs IFA at K 46 and K 49; #103 certifies s* with the switch on at ±10/15/20. Under rule C a split state's piece attaches only to whole states. CT's neighbours are NY, MA, RI. NY (4,369) and MA (about 1,531) exceed 1.15 τ at every K in 46–55, so they split, and CT (1,333.6) exceeds 1.15 τ at every K ≥ 43, so it splits. CT's pieces then each sit alone or with RI (about 347). The best case is two pieces: 2·τ(1−δ) − 347 ≤ 1,333.6, so τ ≤ 840 at ±15%, which means K ≥ 50; at ±10% K ≥ 53; at ±20% K ≥ 47.

Evidence: `runs/exp/contig/whole127/ifa46-whole/districts.csv` (CT 1,333.6; MA+RI 1,878.0; NH 346.8; VT 166.7; ME 136.9; total 48,989, so τ(46) = 1,065, τ(49) = 1,000, τ(50) = 980); `ifa46-pieces2/districts.csv` (MA_p1+RI 1,134.8) with `docs/RESULTS.md:1283` (MA_p1 ≈ 0.74 τ) gives RI ≈ 347 ± 5; `docs/RESULTS.md:1272` ("CT is 1.2523 τ"). WIFI holds New England on the main map (`runs/exp/contig/wh_dollar/s13_WH11.toml` [channels.WIFI]), so FI, national and WH do not meet this; IFA does.

Change: in #103's amendment item 3 (speed order) add: "Before anything else, solve pass 1 with the switch on for IFA at every K in 46–55 and δ in {0.10, 0.15}, and for FI 20, national 15, WH 11 at δ in {0.10, 0.15}; post the (channel, K, δ) → s* or infeasible grid on #103 and #130 within the first hour." In #130 replace "Then IFA K 46 and K 49" with "Then IFA at the smallest K in 46–55 that A's grid shows feasible under rule C at the planning band, and at one more K the owner picks." Put to the owner now, as one question: (a) accept IFA at K ≥ 50 under rule C, or (b) allow a declared list of two-split-state districts (for example CT with MA, or CT with NY) that B carves jointly as one job over both states, with the carve job's `state` field becoming `states`. Neither may be chosen by the lanes.

### F2. The no-good cut is wrong as written (#130). **Blocks.**

What is wrong: Σ_{S∈Q} n_S ≤ |Q| − 1 over-bans in two ways. With a singleton {σ} used k₀ ≥ 2 times the sum exceeds |Q|, so the cut also bans every sub-configuration with the same supports and fewer copies, none of which was proved infeasible. And it bans every plan that keeps all of Q and adds another holder T ∋ σ, which is a different carve problem (an extra piece can absorb a neck). A cut that bans unproved configurations turns s* + g into a number that is neither a bound nor a search result, exactly finding 10's warning.

Evidence: `docs/lenses/COUNCIL_2026-10-05.md` finding 10; rule C makes n_S ≤ 1 for every multi-unit holder (the whole-mode row, `td/master.py:165-166`) and leaves n_{σ} free.

Change, replace the cut in #130 plan 2 with: "Let the plan's holders of σ be the multi-unit supports Q = {S₁..S_q}, each with n = 1, and k₀ copies of {σ}. B proved that no M1 drawing has exactly these holders. The cut excludes exactly that configuration: Σ_{i}(1 − n_{S_i}) + Σ_{T∋σ, T∉Q, |T|≥2} n_T + a + b ≥ 1, with binaries a, b and rows n_{σ} ≥ (k₀+1)·a and n_{σ} ≤ k₀ − 1 + K·(1 − b) (drop b when k₀ = 0, and then a = [n_{σ} ≥ 1] via n_{σ} ≤ K·a). When k₀ = 0 this is the single row Σ_{S∈Q} n_S − Σ_{T∋σ, T∉Q} n_T ≤ |Q| − 1. Before writing a configuration cut, run `plancheck.drawable` on each piece's own support {σ} ∪ attach: a piece proved undrawable alone gives the stronger and valid ban n_S = 0 (MODEL §4.9, Proposition B)."

### F3. Exact-only carving will stall, and unknown has no fallback (#129, #130). **Blocks.**

What is wrong: #124's single-district MILP, with one flow and one binary per free ZCTA, proved nothing infeasible and returned no incumbent in 600 s on FI CT+DE+NY+PA, and 7 unknowns at 120 s on ifa_49. B's model has k flows, k·|Z_σ| binaries and a cut-border objective over every intra-state edge, on NY (about 1,800 ZCTAs) in 4 or CA in 4. Expect unknown within 900 s on the big states. P then retries once and reports, so one unknown state means no map for the channel. Exactness is needed only for a ban; an ok result is judged by the gate on the ZCTA set regardless of how it was found.

Evidence: `docs/RESULTS.md:1000-1004` (#124 table: FI 14/0/1, "no incumbent in 600 s"; IFA 19/0/7 at 120 s); `tools/exp/contig/plancheck.py:118-323` (the model B generalises); `docs/RESULTS.md:904-978` (#125: draw plus one repair pass gives M1-clean FI 20 maps, so a heuristic carve of a state is routinely achievable).

Change to #129 plan 1: "Order of attempts per job: (i) a constructive carve: seed each piece at its attach bodies (or the heaviest ZCTA for an empty attach set), grow by border-length-greedy BFS to its window, then local moves that keep every piece connected and inside its window; 20 seeded attempts as `pieces.py` does; each candidate is judged by `td.audit.district_pieces` and `district_necks` on piece ∪ attach, and the first that passes is `ok`. (ii) Only when (i) fails: `plancheck.drawable` per piece, which can prove a piece undrawable alone. (iii) Only then the joint exact MILP, for a proof of infeasibility, with the time limit." Change to #130 plan 2, replace the unknown line with: "unknown → try the next pool plan from A for that channel; if the pool is exhausted, add a **policy** no-good for that configuration, recorded as 'carve unknown at T s (policy, not a proof)' with its cost, and continue; the map is then reported at s* + g where s* is the clean master's certified value, and the policy bans are listed in the report. A policy ban never enters the certificate."

### F4. P cannot call A's master; the contract has no re-plan entry point (contract). **Blocks round 1's toy test and round 2.**

What is wrong: `td.master.plan` accepts only `banned` supports (n_S = 0, `td/master.py:184-186, 391`), no other rows, and minimises diameter. A's F2 master lives in `tools/expb2/`, which P never sees in round 1. P's toy end-to-end test ("first carve proved infeasible → cut → re-plan → pass") needs a master that takes cuts. Nothing in the contract names it.

Change, add to the contract: "### replan (A provides it, P calls it). CLI `"$TD_PY" tools/expb2/plan.py <spec> --channel C --k K --delta D --rule one_split_per_district --cuts cuts.json --out <dir>` writes `plan_<C>_<rank>.json` for the chosen plan and its pool. `cuts.json` is a list of {"type": "support_ban", "support": ["CA","NV"]} and {"type": "nogood", "state": "CT", "holders": [["CT","RI"]], "singleton_copies": 1}. A's first commit is the stub CLI that returns td.master's diameter plan under the rule-C filter with the cuts ignored and a `stub: true` key, so P can build against it." P's round-1 fixtures then use the stub.

### F5. Rule C cannot be a family filter when all states are candidates (#103). **Blocks A's correctness.**

What is wrong: the amendment says "the support family keeps only supports holding at most one splittable state". With all states as candidates (owner decision 3, `docs/problem/PROBLEM.md` "ranges over all states"), every state is splittable in the master, so the filter removes every multi-unit support. The rule must be a row tied to the s_v decision.

Change: "Rule C is the row Σ_{v∈S} s_v + |S|·n_S ≤ |S| + 1 for every support with |S| ≥ 2 (a used multi-unit support holds at most one state with s_v = 1; n_S ≤ 1 there follows from coverage). A unit with s_v = 0 is held whole by its one holder automatically (coverage with r_v = 1). This is not finding 2's pair row s_v ≥ n_S + n_T − 1, which stays banned." The family filter form may be used only in passes 2–4 after the split set is pinned.

### F6. B's "ok" and its proof claim must be the gate, not the model (#129). **Blocks the §4.10 claim as stated.**

What is wrong: plan 3 claims "any assignment the model accepts gives pieces that are connected and neck-free". With the attach set contracted to one root and necks cut lazily, the model accepts assignments the gate rejects: a piece that reaches one component of a two-component attach set but not the other, or a neck no cut has been added for yet. `drawable` handles this by contracting each held component to a body, requiring every other body to be reached, adding wide-passage rows between bodies, and judging every incumbent with `district_necks` before saying drawable (`tools/exp/contig/plancheck.py:243-246, 254-257, 300-312`).

Change #129 plan 1 and 3: "Each component of a piece's attach ZCTAs is a body; the flow is rooted at the heaviest body and every other body must be reached; wide-passage rows run between bodies as `plancheck.wide_rows` does. `ok` means every piece ∪ attach passes `district_pieces` (one component) and `district_necks` (no proved or unresolved neck); the model's acceptance alone never does. §4.10 proves one direction only: every M1-feasible carve satisfies every row, so a HiGHS proof of infeasibility is a valid ban; the other direction is the gate." Also drop "The attach state's own internal necks are out of scope": with the gate as the judge they are in scope at no cost.

### F7. The wave gate would block every lane on the file-list format (all three). **Blocks mechanically.**

Evidence: `agent/wave/wave.mjs:36-46` `bulletPaths` collects backticked tokens on bullet lines only; `allowed()` at `:84` then matches changed paths against them. #103's `## Files` is one prose line, #129's and #130's are comma-separated lines; none has a bullet with a backticked path, so the allowlist is empty and every commit is "outside ## Files". `## Read first` is parsed the same way (`:98-106`): #103's bullets carry no backticks and #129's and #130's are prose, so nothing is inlined.

Change: rewrite each `## Files` and `## Read first` as bullets with backticked paths, one per line, for example "- `tools/exp/contig/carve.py`", "- `docs/MODEL.md` (§4.10 only)", "- `docs/memory/facts/highs-traps.md`".

### F8. #103's original B2 acceptance contradicts its new role (#103). **Blocks A's acceptance.**

What is wrong: the original acceptance requires sweep.py runs, drawn maps and "top 3 eligible maps per target"; A now plans only and P draws. A Sonnet lane cannot meet it and should not try.

Change: strike the acceptance bullets on sweep runs, index entries for drawn maps and the top-3 table; keep the certificate protocol, the "over C-rule supports in 𝒳_c(δ)" label, root gap and node counts (U53, cheap), the F6 cross-check as optional, and the amendment's items. Add: "A's plan runs write a `manifest.json` under `runs/exp/expb2/<run_id>/` so #92's index sees them (T1)."

### F9. The planning band is a policy choice the issues make silently (contract, #130). Not blocking the build; ask before the runs.

What is wrong: in this pipeline drawn mass equals carved mass; nothing drifts. So the planning δ is the drawn band. The contract's example uses δ 0.10 and P says "the band" without naming it; the eligibility band is ±15% (settled frame). Planning at ±10% buys balance at the cost of splits, which inverts the ranking (splits first, balance fifth); planning at ±15% minimises splits among eligible maps. Either is defensible; it is the owner's (OD1-adjacent, "Asking" trigger: it changes a number you report).

Change: ask the owner once: "P plans at δ = 0.15 (the eligibility band) and reports the ±10% result alongside; or P plans at ±10%." Record the answer in #130 and the contract.

### F10. P's balance recarve can undo an M1-clean map (#130 plan 3). Not blocking.

Change: "After the fixed-candidate LP, tighten each piece's window toward the LP's share and recarve; keep the new carve only if it is ok by the gate, else keep the last ok carve. Report balance as conditional on the plan."

### F11. "Minimal" wording conflicts with decision A3 (#130). Not blocking; wording.

`docs/problem/PROBLEM.md` (2026-10-05, A3): s* from an η > 0 master "never backs 'minimal' or 'must split'". #130 plan 4 says "called 'minimal' only at g = 0 under the stated rule". Replace with: "reported as s* + g over C-rule supports in 𝒳_c(δ); never 'minimal' unless #119's all-M1 bound covers the map."

### F12. P has no writer for a run folder from (plan, carves) (#130). Scope, not blocking.

`wholeplan.loop` raises on any non-whole unit (`tools/exp/contig/wholeplan.py:97-99`), `contig_run` draws from a plan (`tools/exp/contig/run.py:149`), and spec pieces are county lists only (`td/spec.py:10, :175`), so "treat the pieces as whole units" has no spec path. P must assemble the ledger itself and write `districts.csv`, `ledger.csv`, `run.json`, `manifest.json` in run.py's format for the gate, scorer, renderer and T1. Add `tools/exp/contig/run.py` to P's `## Files` or name a new writer in `pipeline.py`.

### F13. Windows need the η floor and a definition of "clipped" (contract). Not blocking.

Set mass_lo = max(η·M(σ), τ(1−δ) − M(attach)) and mass_hi = min(M(σ), τ(1+δ) − M(attach)); B enforces Σ pieces = M(σ) by assignment. With the η floor every piece is non-empty, so the drawn split set equals the planned one and the gate count matches s_v. Without it a piece can be drawn empty, the district's footprint leaves 𝒳_c(δ), and the drawn split count can sit below s* (finding 14), which the report would then have to label "not covered".

### F14. Pass 1 pins the split set, not the count (#103). Not blocking.

"Pin the chosen split set" before pass 2 makes cuts and diameter conditional on one s*-set. Pin Σ s_v = s* for passes 2–3; pin the set only when exporting the pool.

### F15. Small pieces are left to chance (ranking rank 3). Not blocking; report it.

A piece's window can be far below 0.2 τ, so a sliver of CA on NV+UT is legal and the scorer flags it. A piece floor (F4, #104) is a restriction the owner has not adopted. P should report small pieces per map and not add a floor.

### F16. Scope and lane conflicts. Not blocking; plan for it.

None of the three fits one stage: A is a new master builder plus four passes, certificates, rule C, pool, 30 frontier solves, a proof and a toy; B is a new MILP, heuristic, proof, four toys and five real carves that may take 900 s each; P is a loop, fixtures, a writer and shortlist wiring. Use the checkpoint rule (commit passing work, report, fresh child continues). All three edit `docs/MODEL.md`, `docs/RESULTS.md` and `docs/CODE_MAP.md`; land A, then B, then P, each rebasing. WIFI 3 is missing from P's run order (C7); add it as the whole-plan path with no carve.

## 4. Part 2 ratings

- **C1 Contract gap: confirmed, blocks.** No API for cuts exists (`td/master.py:391` takes `banned` only); see F4.
- **C2 Cut wrong: confirmed, blocks.** Over-bans sub-configurations when k₀ ≥ 2 and every superset of Q; exact form in F2.
- **C3 Exact-only stalls: confirmed, blocks.** #124's evidence at `docs/RESULTS.md:1000-1004`; heuristic-first with the gate as judge, exact only for proofs, policy fallback for unknown (F3).
- **C4 Pass 2 cuts before diameter: refuted, no block.** #103's body already orders passes (1) splits, (2) cuts, (3) diameter, (4) balance LP; only the set-pinning needs the F14 tweak.
- **C5 Share undefined when n_S > 1: partly, no block.** The decoder gives each copy t_{σ,S}/n_S (MODEL §3.1), and B uses windows, not shares; say so in the contract and let `share` be informational.
- **C6 #103 carries too much: confirmed, blocks A's acceptance.** F8.
- **C7 WIFI omitted: confirmed, no block.** Add it as the no-carve path.
- **C8 Settles #112 by default: partly, no block.** The owner approved the re-plan on 2026-10-07; the rule it implies is "move the share (same s*), then another split, never a wider band than the planning δ". Record those words on #130 and in the contract; what is still open is the planning δ itself (F9).
- **C9 File-list format: confirmed, blocks.** `agent/wave/wave.mjs:36-46` reads backticked tokens on bullet lines only.

## 5. Proposed changes to the plan

1. **Hour 0, before the lanes:** fix the issue texts (F2, F4, F5, F6, F7, F8, F11, F13), and put two questions to the owner in one message: IFA K or a declared two-state exception (F1), and the planning δ (F9).
2. **A, first deliverable:** the rule-C F2 pass-1 grid over (channel, K, δ) posted within the hour (F1), then FI's `plan.json`, then the rest. Sonnet can do pass 1 and the grid; expect the certificate, pool and proof to need a second stage.
3. **B, order of attempts:** heuristic carve judged by the gate, per-piece `drawable` for strong bans, joint exact MILP last (F3, F6). Measure the five real states with the heuristic first; that alone tells us whether the pipeline can draw.
4. **P, round 1:** build against A's stub CLI and canned carve results; toy end-to-end with the exact no-good; the run-folder writer (F12). **Round 2:** after A and B land, FI 20 end to end at the owner's δ, then IFA at the feasible K, with the pool-then-policy fallback so every channel ends with a map or a listed reason.
5. **Keep the certificate honest:** s* is the clean master's value; policy bans and configuration cuts are listed; the map is s* + g over C-rule supports in 𝒳_c(δ), never "minimal".

## 6. LEARNED lines

LEARNED: Under rule C (one split state per district) IFA has no plan inside ±15% for K ≤ 49 and none inside ±10% for K ≤ 52: CT (1,333.6 m_rel) must split, NY and MA must split too, and RI (≈347) is CT's only whole neighbour, so two CT pieces need 2·τ(1−δ) − 347 ≤ 1,333.6 (`runs/exp/contig/whole127/ifa46-whole/districts.csv`, `ifa46-pieces2/districts.csv`, 2026-10-07).
LEARNED: A configuration no-good for a proved-infeasible carve must exclude exactly the holder multiset; Σ_{S∈Q} n_S ≤ |Q| − 1 also bans every superset of Q and, with singleton copies, sub-configurations never proved.
LEARNED[global]: The wave gate (`agent/wave/wave.mjs` `bulletPaths`) reads `## Files` and `## Read first` only from bullet lines with backticked paths; a comma-separated or prose line gives an empty allowlist and blocks every commit.
DECIDED: none
