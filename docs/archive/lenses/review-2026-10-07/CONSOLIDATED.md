# Consolidated design review of #103, #129 and #130 (2026-10-07)

**Sources:** `report-fable.md` (Fable 5.1, verdict GO WITH CHANGES) and `report-astra.md` (GPT-6
Astra, verdict STOP). Merged by the orchestrator.

The v2 issue drafts are in `/tmp/iss/acb/v2/`. Owner decisions D1–D6 are open and appear in the
drafts as `[OWNER Dn]`.

**Key:** F = Fable finding, A = Astra finding. The orchestrator column says ✓ when a claim was
re-derived here.

## Blocking findings: both reviewers agree

| # | Finding | F | A | Orchestrator | Fix in v2 |
|---|---|---|---|---|---|
| 1 | The no-good Σ_{S∈Q} n_S ≤ \|Q\|−1 over-bans: it bans sub-configurations when a copy repeats, and it bans supersets of Q that add a holder of σ. | F2 | A1 | agree | The contract's `holder_nogood` excludes exactly the multiplicity vector over every support containing σ, zeros included. A implements it as exact indicator rows, with a test. Scope: channel, K, δ, rule, graph. |
| 2 | P has no way to call A's master with cuts, so it would fall back to the diameter master. | F4 | A5 | agree | A owns the `tools/expb2/plan.py` re-plan CLI. Its first commit is a stub. P builds against the stub. |
| 3 | Exact-only carving will stall, as #124 did. "ok" needs the gate, not an exact optimum. | F3 | A7 | agree | B is heuristic-first and the gate decides "ok". Per-piece `drawable` can prove a piece undrawable alone. The joint MILP is for proofs only. |
| 4 | Contracting the attach set to one root invents paths and hides necks, so the §4.10 equivalence claim is false. Only the relaxation direction holds. | F6 | A3 | agree | One body per connected attach component, conditional wide rows as `wide_rows` has them, and "ok" decided by the gate. §4.10 proves the relaxation direction only. A carve is reported "infeasible" only once §4.10 is tagged [proved]. |
| 5 | Rule C as a family filter removes every multi-state support, because every state is a candidate. It must be a row on states that actually split. | F5 | A4 | agree | The row is Σ_{v∈S} s_v + \|S\|·n_S ≤ \|S\|+1 for \|S\| ≥ 2, with a toy test. |
| 6 | #103 still carries its old B2 acceptance (sweeps, drawn maps, top 3), which is too much for one lane and overlaps P. | F8, F16 | A11 | agree | Struck from #103 and moved to P. A keeps the certificate, labels, root gap and an optional F6 cross-check. |
| 7 | The wave tooling parses an empty `## Files` and `## Read first`, and its gate rejects `"$TD_PY"`. | F7 | A12 | ✓ (wave.mjs:37, :57) | Bullets with backticked paths; acceptance runs `python3 tests/run_all.py`. |
| 8 | Pinning the split *set* after pass 1 stops cuts from being minimised over other sets of the same size. | F14 | A8 | agree | Pin Σ s_v = s* instead; pin cuts after pass 2. |
| 9 | WIFI is missing from P's run order, so no complete main map can be assembled. | F16 | A9 | agree | P assembles national 15 + WH 11 + FI 20 + WIFI 3 = 49 with the full audit. |
| 10 | "Minimal" wording conflicts with A3, and an unknown lower bound shown with `gap: 0.0` misleads. | F11 | A6 | agree | Report incumbent, lower bound, proof status and domain separately. Never use "minimal" unless #119's all-M1 bound covers the map. |

## Found by one reviewer

| # | Finding | By | Orchestrator | Fix or route |
|---|---|---|---|---|
| 11 | **Rule C makes IFA infeasible at K ≤ 49 at ±15%** (K ≤ 52 at ±10%, K ≤ 46 at ±20%). CT has to split, and RI is its only whole neighbour. | F1 | ✓ recomputed from `whole127/ifa46-whole/districts.csv`: the edges are K 50 at ±15%, K 53 at ±10%, K 47 at ±20% | **[OWNER D1]**. A posts its rule-C grid within the first hour. |
| 12 | A district holding a carved piece that fails the gate does not justify a support ban: a support with part of σ fixes no single ZIP set. When B said ok and P's identical check fails, that is an integration error. | A2 | agree | Support bans only for whole-unit districts, or for a piece `drawable` proves undrawable alone (Prop B). Otherwise stop with an integration error. |
| 13 | IFA K 47 and 48 are missing. | A9 | agree, but moot under D1 | IFA's K is set by A's grid and D1. |
| 14 | The scorer's rank key leaves out cuts (`score.py:419`), but WATCHDOG ranks cuts second. | A8 | ✓ (`score.py:419-421` rank key has no cuts) | P adds the cuts key and its test (`tools/looks/score.py` is a watched path; this aligns it with the settled ranking). |
| 15 | The planning band is a silent choice. Drawn mass equals carved mass here, so the planning δ *is* the drawn band. | F9 | agree | **[OWNER D2]** |
| 16 | The $ rule as coded is the channel average. WATCHDOG and the brief can be read as per district. | A9 | agree; already raised with the owner | **[OWNER D3]** |
| 17 | P's balance recarve can undo a clean carve or repeat it. | F10, A8 | agree | Keep the last carve the gate passed. Accept a recarve only if the drawn rank improves. A balance-target failure is never a ban. |
| 18 | Piece windows need the η floor, and "clipped" is undefined. | F13, A5 | agree | mass_lo = max(η·M_σ, τ(1−δ) − M(whole)), mass_hi = min(M_σ, τ(1+δ) − M(whole)). The partition conserves mass. |
| 19 | P has no run-folder writer, since `wholeplan.loop` rejects non-whole units. | F12 | agree | P writes the run folder in `run.py`'s format (`pipeline.py`) for the gate, scorer, renderer and T1. |
| 20 | `share` with n_S > 1: the decoder already gives each copy t/n, so the share is a target and the window is the constraint. | F (C5), A5 | agree | The contract names it `target_share`. Unequal masses across copies are allowed. |
| 21 | Three lanes add to MODEL, RESULTS and CODE_MAP at once. | F16, A11 | agree | Each lane writes only its own section. Landing order is A, then B, then P. |
| 22 | Small pieces are left to chance; a piece floor is not adopted. | F15 | agree | P reports small pieces per map and adds no floor. |
| 23 | WATCHDOG lists #110 as open, while PROBLEM.md records an answer. | A6 | ✓ (WATCHDOG.md:76 vs PROBLEM.md:60) | Fix the wording before any "certified" claim; this is not a lane task. |

## Where they disagree

| Topic | Fable | Astra | Orchestrator |
|---|---|---|---|
| Verdict | GO WITH CHANGES | STOP | Both are STOP for the issues as filed and GO once the v2 fixes land. |
| A carve still "unknown" after the pool is used up | Labelled policy no-good, kept out of the certificate, then continue | No permanent cut from a timeout; report unknown | **[OWNER D4]**. Until the owner rules: try the rest of the pool, then report unknown. |
| C8, the re-plan rule | Covered by the owner's approval on 2026-10-07 | Ask before an automatic extra split | Ask: **[OWNER D5]**. |

## Owner decisions

- **D1, IFA under rule C:**
  - (a) plan IFA at K ≥ 50 (inside 46–55) at ±15%;
  - (b) allow a declared list of districts holding two split states (for example CT with an MA or
    NY piece), carved jointly;
  - (c) IFA without rule C, as a separate track.
- **D2, the planning band:** δ_plan = 0.15, the eligibility band, which favours fewer splits; or
  0.10.
- **D3, the $ rule:** channel average within ±10% of target (as coded), or every district within
  the band of its target.
- **D4, a carve still unknown after the pool:** report "no map found", or add a labelled policy
  ban that stays out of the certificate.
- **D5, re-plan:** may a re-plan add splits above s* at fixed K and band, reported as s* + g?
- **D6, the ranking:** confirm cuts second, as committed WATCHDOG has it (owner 2026-10-05).

## Owner answers (2026-10-07)
- **D1:** "IFA at K ≥ 50 under rule C".
- **D2:** "±15% (the eligibility band)".
- **D3:** "Every district vs target", tolerance "±15% of target"; shortlist rescoring "Later, with
  #130". This replaces both of today's checks (average within ±10% of target, and each district
  within ±15% of the average). The band no longer depends on K, so masses are planned in dollars.
  Consequence: the CT bound in finding 11 becomes K-independent and marginal (about 1,328 needed
  of CT's 1,334 m_rel), so A's grid reports IFA K 46–49 as well.
- **D4/D5:** "Add splits; no policy bans".
- **D6:** already settled as owner decision 2, 2026-10-05 (`docs/lenses/COUNCIL_2026-10-05.md:42`),
  "Cuts break ties"; the scorer gets the cuts key in #130.

# Round 2 (2026-10-07): report2-fable.md GO WITH CHANGES, report2-astra.md STOP

Both agree that v2 closes most round-1 findings: F2 and F4–F15 are closed; A1–A10 are closed or
partly closed.

## Checked here
- **CT under D3 and rule C, decided by the dollar rate.** CT = 1,333.63 m_rel, RI = 342.56
  (`whole127` districts.csv). For IFA, `score.dollar_rates` divides the whole-extract $62.14B by
  the whole extract's m_rel: $1.25197M per m_rel. The CONUS ledger holds 48,989 m_rel, so about
  $0.8B lies outside the drawn map.
  - At the extract rate: L = 848.66 m_rel, and 2L − RI = 1,354.77 > 1,333.63. **Short by
    $26.5M at every K, so IFA has no plan under rule C at the ±15% target band.**
  - If $62.14B were spread over CONUS only: 2L − RI = 1,332.72, slack $1.2M (0.07% of CT), a
    knife edge.
  - At −20% (extract rate), the slack is +78.7 m_rel, so the plan is feasible.
  - Fable's 5 m_rel came from rounding RI to 347; Astra's arithmetic is the correct one.
- **wave.mjs takes the first matching section** (`wave.mjs:128`), so appended amendments are
  ignored and #103's body must be **replaced**.
- **`--tracking` is not on the gate's flag list** (`wave.mjs:26`), so the tracking check runs at
  integration and review.

## Agreed changes for v3 (no owner input needed)

| # | Change | From |
|---|---|---|
| R1 | One dollar adapter, owned by A: `tools/expb2/usd.py`, `usd_masses()` from `score.dollar_rates`, with the rate snapshot frozen in the contract. Every mass row (band, η floors, corridor floors) is in that unit. B and P use the same function. `td/spec.py` is unchanged. Tests cover mixed fine rates (national, WIFI). | F N1, A C1 |
| R2 | MODEL §4.12 states that Claim 1, Prop D and Prop B hold for any fixed [L, U] in one additive unit (none uses the centre), and that the Claim 2 smallest-δ machinery is unused. B's §4.10 is proved on the same domain. | F N5/C6, A C1 |
| R3 | `plancheck.drawable` takes an explicit `held` set, `window` and `mass` (B's Files gain the signature). An old τ-band infeasibility is never reused as a ban. | F N3/C4, A C1 |
| R4 | `support_ban` (n_S = 0) is valid only if every unit of S is forced whole across all re-plans. For S that is merely unsplit now, add a conditional exclusion: n_S > 0 ∧ all s_v = 0 is excluded, written as n_S ≤ Σ s_v for multi-state supports and n_{v} ≤ U_v·s_v for singletons. Test with an S that becomes drawable once one member splits. Drawable-alone bans quantify over all allowed modes and the full band. | A C2 |
| R5 | Content identity: hashes of the input files, rates, targets, η, modes, caps, support universe, polygon and connector data, and the proof-model version. `job_id` hashes the full job. | A C2 |
| R6 | "Add splits" mechanics (D5): after a pool comes back unknown, A serves **search layers**. First come unexplored plans at the same split count with higher cut counts, then the next split count, within a run budget (see E4). Layers select experiments only: they are never cuts and never raise s_lower. | A C3 |
| R7 | A exports the conditional balance LP that P calls. B keeps the best gate-passed candidate by the drawn ranking, not by border length alone. Reported as s_drawn = s_lower + g, or "not covered". | A C4 |
| R8 | Units in audit and render: `ledger.csv` keeps `m_rel`, and dollars are stored separately with their rate provenance. Each run's spec copy sets `final_delta` to the smallest τ band containing the $ band, so the scorecard's band row does not false-fail. The scorer, summaries and `render.py --fac` all use one snapshot. | A C5, F N4/C5 |
| R9 | Empty-attach pieces: the MILP picks one root per piece, and the heuristic uses distinct seeds. The deadline covers validation too. A timeout with a gate-passed incumbent counts as `ok`; without one it is `unknown`. | A C6 |
| R10 | The grid covers national 13–16, WH 10–12, FI 19–21 and IFA 46–55 at the target band, and lists every main-map combination totalling 48–54 whose channels are all feasible. If national 15 / WH 11 / FI 20 / WIFI 3 is infeasible, P stops before drawing and the owner picks. | F N2/C2 |
| R11 | Staging: stage 0 freezes rates and bands and posts the arithmetic screen (capacity `ceil(M/U) ≤ K ≤ floor(M/L)`, CT's condition). FI 20 comes first. The full grid and the rule-C-off bounds are later stages. Partial progress is posted at one hour; cells not yet run are "pending". B's benchmark is split into milestones. P reports up to three eligible candidates per channel or map. | A C7 |
| R12 | Replace #103's canonical sections instead of appending. The stub becomes a canned toy response, not a family filter. Tracking runs at integration. | A C8 |
| R13 | Zero-opportunity units are attached before the gate, so the gate's union equals the ledger's. A carve job's `state` may be a list (a declared joint carve). Contract fields `units` ∈ {usd, m_rel}, the targets, and η taken from the spec. Each lane gets the checkpoint line. | F C7–C9, N6 |

## Owner decisions
- **E1:** the IFA dollar rate: the extract rate (as coded, $1.252M per m_rel) or $62.14B spread
  over CONUS only.
- **E2:** IFA under rule C, given E1 (D1 revisited): a declared joint CT district, no rule C for
  IFA, or a −20% lower edge for IFA.
- **E3:** WIFI's band: ±15% of its average in m_rel (as before) or in dollars.
- **E4:** the search budget for added splits: how many layers above s*, and how much time per
  channel.

## Owner answers, round 2 (2026-10-07)
- **E1:** "Extract rate, as coded". IFA is $1.25197M per m_rel ($62.14B over the whole extract,
  as `score.dollar_rates` computes it). The alternative, $62.14B over CONUS ($1.2685M), is
  recorded and rejected. Off-map $ is not credited to CONUS districts.
- **E2:** "IFA lower edge −20%". IFA districts must be within −20% / +15% of the $1.25B target.
  This is an owner band change for IFA (OD1). CT check at the extract rate: L = 798.7 and
  U = 1,148.2 m_rel. CT in 2 pieces (one with RI) has slack +78.7 m_rel; in 1 piece it is over U,
  and in 3 pieces it is short 720. MA alone (1,535) is over U, so it must split. L and U do not
  depend on K. D1's "K ≥ 50" no longer has a reason; IFA's K is set by the grid within 46–55.
- **E3:** "Dollar-weighted average". WIFI districts must be within ±15% of WIFI's dollar
  average.
- **E4:** not answered. The owner asked for the search method to be investigated for a better
  and faster solution, rather than setting a budget for search layers.

# Round 3 (2026-10-07): carve-first; both reviewers ADOPT WITH CHANGES
- **Agreed:**
  - A lazy, seeded library of gate-passed columns, not exhaustive pre-carving.
  - Selection MILP as sequential lexicographic passes on the scorer's rank key, with K as a
    range (IFA 46–55; main map 48 ≤ ΣK ≤ 54 in one joint MILP).
  - A's master is the pricer of record, with `--exclude` keeping the exact holder_nogood
    encoding as an enumeration device. Dual pricing is optional and second.
  - Certificate: s_lower = s_drawn certifies only over A's named domain, and only if every
    column is in the support family with η-floored pieces.
  - Dropped: R3, R4, cuts.json and support_ban, B's MILP and §4.10 from the critical path. R6 is
    replaced by request enumeration. The rest is kept.
  - Astra: pricing must include the K dual; a τ-envelope never stands in for the $ band.
- **Verified here, Fable:** under rule C at E2, **MD has no plan**. MD is 1,203.64 m_rel, over
  U = 1,148.19. Two MD pieces need 393.84 of attach mass, but DC + DE + WV = 346.78 and VA
  (1,120.63) can take at most 27.56. So IFA under rule C is infeasible at E2, and also at D3
  ±15%.
- **Fable:** `set125/fi20_fi_nonc-r1` already satisfies rule C and the D3 band, so FI 20 starts
  at s_drawn ≤ 6 against a forced floor of 5. Under D3, the national 15 and WH 11 lead-map
  districts fall below the target band, so main-map K must be re-chosen.
- **Open for the owner:** IFA's MD (joint MD+PA pattern, MD county pieces, rule C off for IFA,
  or another band); the library budget (E4); confirming main-map K from the MILP.
