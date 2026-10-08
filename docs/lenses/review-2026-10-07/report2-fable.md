# Round 2 cross-review of the v2 drafts (#103 A, #129 B, #130 P, contract v2)

Reviewer: Claude Fable 5.1, 2026-10-07. Read-only. Sources: `CONSOLIDATED.md`, the v2 drafts in `/tmp/iss/acb/v2/`, `report-astra.md`, and the td checkout. Masses are m_rel or dollars; no sales or names.

## 1. My round-1 findings against v2

| # | Finding | Status | Where v2 closes it, or the wording still needed |
|---|---|---|---|
| F1 | Rule C infeasible for IFA at K ≤ 49 (CT and RI) | **partly closed, and changed by D3** | A plan 2 posts the grid first and B plan 3.1 measures CT with RI: both right. But under D3 the band is target·[0.85, 1.15] in dollars at every K, so D1's "K ≥ 50" no longer touches CT. With rate 62.14e9 / 48,989 m_rel, L = 837.6 m_rel; CT's pieces need 2L − RI ≤ CT, i.e. 1,328.3 ≤ 1,333.6, so the CT piece that joins RI has a window about 5 m_rel wide ($7M, 0.5% of target) at every K from 46 to 55. Feasible on paper, a knife edge in ZCTAs. Wording needed: see change C3 (CT settled by B's exact carve, D1 (b) kept open in the contract). |
| F2 | No-good over-bans | closed | Contract `holder_nogood` ("every support containing the state, zero for absent ones… excludes exactly that vector"); A plan 5 and 6; A acceptance toy "a changed multiplicity and an added holder stay feasible". |
| F3 | Exact-only stall, no fallback | closed as decided | B plan 1.1 heuristic-first, gate decides; D4 "no policy bans": unknown ends as "no map found" after the pool. Residual risk stands and is the owner's. Note the dependency: P can write no cut until §4.10 is tagged [proved] (contract: `proof.verified`), so round 2 feedback waits on B's Sol verification. |
| F4 | No re-plan entry point | closed | Contract "replan CLI", stub first commit, `cuts.json`; P plan 1.1 "never fall back to td.master". |
| F5 | Rule C as a filter | closed | A plan 1: Σ_{v∈S} s_v + \|S\|·n_S ≤ \|S\| + 1, "do not filter the family by free lists"; toy in A acceptance. |
| F6 | "ok" must be the gate; bodies per component; proof direction | closed | Contract carve result ("ok means … passes district_pieces and district_necks"); B plan 1.3 ("one body per connected component… must reach every other body"), B plan 2 (one direction only; `milp_infeasible_claimed`). |
| F7 | Files and Read first format | closed | All three drafts use `- \`path\`` bullets; acceptance runs `python3 tests/run_all.py`. |
| F8 | #103's old acceptance | closed | A amendment: "supersedes the original B2 Goal, Files and Acceptance". |
| F9 | Planning band silent | closed | D2 ±15%; contract `band`; P "planned and judged the same way". |
| F10 | Balance recarve can undo a clean carve | closed | P plan 4 "keeping the last carve the gate passed; accept a recarve only if the drawn rank improves". |
| F11 | "Minimal" vs A3 | closed | A plan 4 "Never write 'minimal' or 'must split'"; P plan 5 last paragraph. |
| F12 | No run-folder writer | closed | P plan 1.4 writes `run.py`'s format in `pipeline.py`. |
| F13 | η floor, "clipped" | closed | Contract "Window" paragraph. |
| F14 | Pin the count, not the set | closed | A plan 3.2 "(the count, not the set)". |
| F15 | Small pieces | closed | P plan 3 "Report small pieces per map; add no piece floor". |
| F16 | WIFI, doc sections, scope | partly closed | WIFI in P plan 5.2.3; "its own section only" in every Files list. Scope is still large per lane; the checkpoint rule covers it, and nothing in v2 says so. Add one line to each Lane paragraph: "Told to checkpoint, commit what passes and report; a fresh child continues." |

## 2. The other reviewer's findings

**A2, no support ban from a carved district that fails the gate: agree.** Proposition B's ban needs D_c(S, δ) = ∅, every ZIP set X with footprint S (`docs/MODEL.md:365-400`); #127's ban is valid only because every unit is whole, which `wholeplan.loop` enforces by raising otherwise (`tools/exp/contig/wholeplan.py:97-99`). A failed carve of one assignment proves nothing about the support. v2 closes it (contract `support_ban` "valid only (i)… (ii)…"; P plan 2 "integration error. Stop and add no ban"). One gap remains: P plan 1.3 routes every fine-channel cell, and a unit dropped for zero opportunity is owned by a territory pass. If such a unit's ZCTAs are added to a district after B's gate ran on piece ∪ attach, P's gate sees a different union and a failure there is not an integration error. Change C8 fixes it.

**A12, the gate rejects `$`: agree.** `agent/wave/wave.mjs:57-58` `safeCheck` returns false on any of `;&|<>\`$(){}\\`, so `"$TD_PY" tests/run_all.py` is never auto-selected. v2 acceptance uses `python3 tests/run_all.py`: closed.

## 3. New problems from v2 and the owner's answers

### N1. Dollars are a cross-cutting unit change with no owner in the drafts. **Blocks round 2.**

The contract says cells are weighted by `score.py dollar_rates`, A plan 0 says "add a spec switch: masses are dollars", and B's and P's drafts say nothing about how they get dollar masses. The instance sums m_rel per cell into `ch.m` and `ch.M` at `td/spec.py:594`; `td/spec.py` is in no lane's Files, so A cannot add a spec switch. If A, B and P each weight independently, a piece inside B's window can sit outside A's band or P's audit. For IFA, FI and WH each channel has one fine channel (`runs/exp/contig/_specs/ifa49.toml`, `wh_dollar/s13_WH11.toml`), so dollars are m_rel times one rate and windows can be stated exactly in m_rel. National mixes `national_chase`, `wells_wh` and `wells_fi` at rates that differ by about 5% (`docs/memory/facts/scenario-sweeps-2026-10.md`, "$1.24–1.25M… $1.18M for wells_fi"; a real map moved 9.2% → 9.9% between units), so national needs per-cell weighting, and so does every derived mass row: corridor floors (`supports.corridor_floors` reads `ch.m`), the band row, the η share floors. Change C1.

### N2. The target band is centred on the target, not on total/K, so main-map feasibility moves. **Blocks the main map's K choice.**

The band [0.85, 1.15]·target is symmetric around the target and one-sided around a channel's average. From #125's $ per district (`docs/RESULTS.md:941-947`):

| channel, K | $ per district | band relative to the average | smallest symmetric δ (#125) |
|---|---|---|---|
| national 15 | 1,126M (−9.9%) | [−5.6%, +27.7%] | 0.0888 |
| national 14 | ≈1,206M (−3.5%) | [−11.9%, +19.2%] | 0.1201 |
| WH 11 | 922M (−7.8%) | [−7.8%, +24.7%] | 0.0879 |
| FI 20 | 925M (+2.8%) | [−17.3%, +11.9%] | 0.0494 |
| IFA 46 | 1,351M | [−21.4%, +6.4%] | 0.02 at ifa49's free list |
| IFA 50 | 1,243M | [−14.5%, +15.7%] | — |

National 15 may place no district more than 5.6% below its average and WH 11 none more than 7.8% below; their symmetric smallest δ exceed those edges. Asymmetric plans may still exist, but nothing in the drafts says so, and the main map's only K set (15/11/20/3) could come back infeasible with no fallback inside K 48–54. For IFA the comfortable K are 49–52, which happens to agree with D1. Change C2.

### N3. `plancheck.drawable` cannot be reused as B plans it. **Blocks B plan 1.2.**

`drawable` takes δ and builds the band as τ_c(1 ± δ) (`tools/exp/contig/plancheck.py:124`), reads m_rel masses, and decides which units are held from `ch.mode` (`:127-128`). Under A's master every state is a candidate, so every mode is free, and `drawable` would treat NV in a CA+NV piece as free, not held: a weaker test whose "infeasible" is still valid but whose purpose (a strong per-piece ban) is lost. B's Files do not include `plancheck.py`. Change C4.

### N4. The scorecard's band row and the scorer disagree on every D3 map. Not blocking; cosmetic but visible to the watchdog.

`td/audit.py::check_bands` (`:254-281`) judges drawn mass against τ_c(1 ± final_delta) and is a watched path that no lane changes. `score.py::eligibility` already excludes that row from eligibility (`:333`, `name != BAND_CHECK`), so a D3-eligible map is still ELIGIBLE, but its scorecard reads "final bands on drawn mass: fail" whenever a district is inside the $ band and outside the τ band (FI 20: −17% is legal in dollars, illegal at ±15% of the average). Change C5.

### N5. The proofs survive D3; the document does not say so. Not blocking; one paragraph.

Claim 1 and Proposition D are stated for a fixed interval [L_c, U_c] and never use its centre (`docs/MODEL.md:464-498, 298-336`); Proposition B likewise. Only §1 defines the band as τ_c[1 − δ_c, 1 + δ_c] (`docs/MODEL.md:53`), and Claim 2's smallest-δ machinery (`exact_delta`, `bisect_delta`) assumes it; the contract already forbids A from using them ("never changes δ"). What the proofs do need is one additive per-ZIP mass used in every row, which is N1. Change C6.

### N6. Small contract gaps. Not blocking.

- `units` must allow `m_rel` for WIFI, which keeps τ_c·[0.85, 1.15].
- The targets are nowhere in v2; they are in code: national 1.25e9, WH 1.0e9, FI 0.9e9, IFA 1.25e9 (`tools/looks/score.py:92`). State them, so IFA's band is not read as total/K.
- `"eta": 0.02` in the example is not any spec's value (IFA 0.05, FI 0.15); say it comes from the spec.
- The carve job has a single `state`, which closes D1 (b) off even though the consolidated review says the owner may revisit D1. Making it a list costs nothing now.

## 4. Verdict

**GO WITH CHANGES.** Round 1 (stubs and toys) can start once C1 is placed and C4 is in B's Files; C2 and C3 must be settled before round 2 draws anything.

**C1 (contract, A plan 0, B, P): one dollar-weighting function, owned by A.** Replace A plan 0's "Add a spec switch" with: "Add `tools/expb2/usd.py` with `usd_masses(inst, channel) -> ({zip: $}, {unit: $})`, weighting each (ZIP, fine channel) cell by `tools/looks/score.py::dollar_rates` and summing over the channel's fine channels; `td/spec.py` is not changed. A builds every mass row (band, η share floors, corridor floors, μ ≡ 0) from these masses." Add to the contract: "For a channel with one fine channel (IFA, FI, WH) this equals m_rel × one rate, and windows may be written in m_rel by dividing by that rate; national and WIFI need the per-cell weighting. B converts its ZIP masses with the same function and never re-derives rates; P writes `m_rel` and `usd` per district in `districts.csv`." Add `tools/expb2/usd.py` to A's Files and to B's and P's Read first.

**C2 (A plan 2, P plan 5.2.3): the grid covers neighbouring K and names feasible main-map combinations.** Append to A plan 2: "Also national 13–16, WH 10–12 and FI 19–21, each at the target band, because the band is centred on the $ target and a channel whose average sits below target has a tight lower edge (national 15: no district below −5.6% of its average; WH 11: none below −7.8%). The grid lists every (national, WH, FI, WIFI 3) combination with total K 48–54 whose channels are all feasible." Replace P plan 5.2.3 with: "the assembled main map at national 15 + WH 11 + FI 20 + WIFI 3 = 49 if A's grid shows all four feasible; otherwise P stops before drawing and reports the feasible combinations with their $ per district, and the owner picks. A K change on the main map is the owner's."

**C3 (P plan 5.2.2, B plan 3.1, contract): CT is settled by a proof, and D1 (b) stays open.** Append to B plan 3.1: "CT with RI is the decisive case: under the target band the piece that joins RI has a window about 5 m_rel wide at every K. CT has about 280 ZCTAs, so after the heuristic run the joint MILP to a verdict, not a time limit, and post ok or proved infeasible with the window." Append to P plan 5.2.2: "Before any IFA re-plan, read B's CT result. If CT with RI is proved infeasible, no K helps under rule C; stop IFA and put D1 (b), a declared CT district with an MA or NY piece carved jointly, or (c) to the owner." In the contract's carve job: "`state` is a string or a list of states; with a list the job is a declared joint carve and each piece names its `split` state. P writes a list only on an owner decision."

**C4 (B Files): `drawable` gets an interval and a held set.** Add `- \`tools/exp/contig/plancheck.py\` (the `drawable` signature only)` to B's Files, with the plan text: "`drawable` takes `held` (the attach ZCTAs), a `window` [lo, hi] and a `mass` dict in place of δ and the channel's modes, and its verdict cache is keyed by the window; every existing caller passes what it passed before." Reason, for the worker: with every state a candidate the modes are all free, so the current `drawable` would treat attach states as free (`plancheck.py:124-128`).

**C5 (P plan 1.4): declare a covering τ-band so the scorecard does not false-fail.** Append: "Set each channel's `final_delta` in the run's spec copy to the smallest symmetric band around τ_c that contains the $ band (for FI 20, 0.173), so the scorecard's 'final bands on drawn mass' row passes every D3-eligible district; eligibility is the scorer's per-district $ band, and `td/audit.py` is unchanged."

**C6 (A plan 6): one paragraph in §4.12.** Append: "State that Claim 1, Proposition D and Proposition B hold for any fixed interval [L_c, U_c], given directly in the band's units, because no proof uses the interval's centre; that Claim 2's smallest-δ results are not used; and that every mass row, corridor floors included, is taken in the same unit as the band."

**C7 (contract): units, targets, η.** Add: "`units` is `usd` or `m_rel` (WIFI). Targets are `tools/looks/score.py` `TARGET`: national 1.25e9, WH 1.0e9, FI 0.9e9, IFA 1.25e9; WIFI has none. `eta` is the spec's value for the channel."

**C8 (P plan 1.3): dropped units are attached before the gate.** Append: "A unit dropped for zero opportunity in a channel is given whole to one district as part of that district's `attach` in the carve job, or to a whole-state district before its gate check; nothing is added to a district after its gate ran, so the gate's union is exactly the ledger's."

**C9 (all three Lane paragraphs): the checkpoint rule.** Append: "Told to checkpoint, commit only work that passes its checks, report what is done and what remains, and stop; a fresh child continues."

## LEARNED lines

LEARNED: Under a band centred on the $ target (owner D3, 2026-10-07) the CT bound is K-independent: with the IFA rate 62.14e9 / 48,989 m_rel, L = 837.6 m_rel and CT's RI-attached piece has a window of about 5 m_rel ($7M) at every K 46–55, so "K ≥ 50" does not help CT; B's CT+RI carve decides it.
LEARNED: A target-centred band is one-sided around a channel's average: national 15 ($1,126M, −9.9%) allows no district below −5.6% of its average and WH 11 ($922M) none below −7.8%, both tighter than their symmetric smallest δ (0.0888, 0.0879), so main-map feasibility under D3 must be re-established by A's grid.
LEARNED: `tools/looks/score.py::eligibility` already excludes the scorecard's "final bands on drawn mass" row (BAND_CHECK), so a per-district $ band in the scorer does not conflict with `td/audit.py::check_bands` for eligibility, only for the scorecard's verdict text.
LEARNED: `plancheck.drawable` decides held units from `ch.mode` and builds its band from δ around τ_c; with every state a candidate (all modes free) it treats attach states as free, so a rule-C per-piece check needs an explicit held set and window.
DECIDED: none
