# Research brief — the A1 track: joint coverage optimisation, after measurement

**Date:** 2026-09-03 · **Framework:** 0.1 · **Branch:** `wt/A1` (worktree
`.claude/worktrees/A1`, from `national-channel` at `a4eb488`) · **Reads:** `docs/APPROACHES.md`
§A1, `docs/FRAME.md` (§0, §3, §6 with the 2026-09-03 rows, §8–§10), `docs/LENS_GROTHENDIECK.md`
(inherited unchanged), `docs/LENS_GROMOV.md` (2026-09-03 A1 re-run), `docs/DOMAIN_optimization.md`
(2026-09-03), `docs/DOMAIN_economic-theory.md` (2026-09-03), `docs/LIT_optimization.md` (new),
`docs/LIT_economic-theory.md` (2026-09-02 body + 2026-09-03 section), `docs/MODEL_U7-meas.md`,
`docs/CODEVERIFY_U7-meas.md`, `docs/MODEL_U1-cert.md`, `docs/VERIFY_U1-cert.md`,
`docs/MODEL_U2-stab.md`, `docs/VERIFY_U2-stab.md`, `docs/units/U0–U7`, `CLAUDE.md` ·
**Supersedes:** the hub's `docs/BRIEF.md` of 2026-09-02 **on this branch only** — cited below as
**[pred]**; its units U0–U7 keep their IDs and are marked landed / carried / retired in §4.

> **⚠ Instance change, 2026-09-04.** Every number in this brief is computed on
> `instance_descaled.json.gz` (v1) at **k = 13**. The live instance is now
> **`instance_descaled_v2.json.gz` at `k = 18`** (≈$18B, sponsor-confirmed; v2 is a strict
> superset of v1 whose growth is overwhelmingly *untapped* market — contested zips only went
> 675 → 718). The units below are still the right units and the solvers are instance-agnostic,
> but **`δ₀`, `V`, `EG_S`, the (★) screen, the premium ladder and the roster must all be
> re-measured on v2 before they are quoted.** Stage 1 has to draw v2 at k = 18 first. See
> `docs/FRAME.md` §0 (2026-09-04, end of day).

**What changed since [pred].** ★6 is lifted in full (user, 2026-09-03). Two of [pred]'s units
landed and their numbers are in FRAME §6: U7-meas (the premium ladder) and U1-cert (the
Eisenberg–Gale bound). Those numbers re-shaped the charter: the lens (`LENS_GROMOV` M8, M13)
and both domain plans (`DOMAIN_optimization` §0, `DOMAIN_economic-theory` §0) retire the
rep-indexed MINLP to a contingency and put in its place **one concave program per roster with
the balance band inside it**, `EG^bal_S(δ)`, plus rounding and a bounded roster enumeration.
This brief cuts the units for that programme.

## 1. The problem in five sentences (from FRAME §1–3 and the A1 charter)

The business is standing up a national channel of `k = 13` territories, each near `$1B` of
opportunity `M`, staffed by 13 of 111 wholesalers who hold existing books `S_i` at 41.9%
aggregate saturation (FRAME §6). A0 draws the map on `M` alone and staffs it afterwards;
A1's charter (`APPROACHES.md` §A1) is to choose map and roster against the value the business
signs, `V(π,σ) = Σ_j log u_{σ(j)}(A_j)`, with balance as a band, and to certify the result by
the fixed-roster Eisenberg–Gale relaxation. Measurement (2026-09-03) says the matching on the
committed map is already premium-optimal, the map holds ≈ 0.64 nats of premium, the roster
≈ 0.04, and no coverage by *any* 13 of the 111 beats the delivered draw by more than 0.865 nats
(FRAME §6). At the delivered roster the unconstrained EG bound is 0.760 nats, but the vertex
realising it has an opportunity spread above 50% against the delivered 0.39% max deviation —
the gain is bought with balance (U1-cert P4). The question A1 must now answer is **how much of
that survives a balance band the sponsor has never named**, and the acceptance criteria are
FRAME §3's six, with C5 (distance-to-best in business units) still unmet by anything built.

## 2. What the lenses found

- **`LENS_GROTHENDIECK` (inherited).** The right object is the coverage `(π,σ)`, not the
  partition; the fibre over a staff set `S` is an Eisenberg–Gale program whose value bounds
  every integral coverage with that roster (its `[claim]`, now **P1 VERIFIED** in
  `VERIFY_U1-cert` §2 at every `ρ ≥ 0` under a named extension hypothesis); the programme as
  built is the `u_i ≡ λM` degeneration. Its "five certificates collapse into one" is **three of
  four** (`VERIFY_U1-cert` §4): the integer balance floor is primal-only, and it turns out to be
  load-bearing exactly where the band may be infeasible (`DOMAIN_optimization` §2.13).
- **`LENS_GROMOV` (A1 re-run, 2026-09-03).** Move 8: the charter's certificate `EG_S` is a
  surrogate that dropped the sponsor's one constraint; the honest object is `EG^bal_S(δ)`, still
  one concave program, sandwiched today as `59.9375 ≤ EG^bal_{S₁₃}(δ) ≤ 60.6974` for
  `δ ∈ [δ₀ = 0.0039, 0.33]`. Move 11: trace `δ ↦ EG^bal(δ)` as the `(balance, V)` frontier; its
  band duals are the balance↔continuity exchange rate FRAME §3 calls binding and never elicited
  (ledger U12 → U14). Move 12: the premium is soft inside the band iff `EG^bal(δ) − V ≤ 5e-3`,
  and concavity predicts it is not. Move 13: "MINLP" and "jointly" are purged — after
  measurement the problem is a short enumeration of convex programs, and A1's real content is
  (a) the map drawn on `u_i` under a band and (b) the value certified against `V`. Ledger
  U13–U19 added; U19 (the roster-free bound) is already answered by the (★) screen at 60.8025.

## 3. What each domain proposes

**Optimization (`DOMAIN_optimization` §4, 2026-09-03).** Stage 0: three zero-cost numbers —
`B_tot`, the (★) screening bound, `δ₀` — **done the same day** (FRAME §6: (★) at `P₁₃` = 60.8025;
`δ₀` = 0.39% seed 3 / 0.62% seed 9). Stage 1: one solve of `EG^bal_{S₁₃}(δ₀)` with duals, and
**D1′**: the one-solve concavity bound `EG^bal(δ₀) + s(δ₀)(δ − δ₀) − V ≤ 5e-3` at the widest
plausible `δ` *proves* softness and ends A1 if it holds. Stage 2: the frontier on
`{δ₀, 0.02, 0.05, 0.10, 0.33}`, bisection for `δ*`, SCIP cross-checks, MNW point marked
(trap 2). Stage 3: band-aware rounding, `γ(δ) = EG^bal − V(rounded)`, and **D2′**: `γ ≤ 5e-3`
keeps §2.1's MINLP retired; a band tighter than the integer balance floor `t*` is an
infeasibility report to the sponsor. Stage 4: roster enumeration in decreasing `P_S` under the
(★) stop rule, Nash-tie margin, intervals over the near-optimal set. Stage 5: the hand-drawn
baseline as a point on the frontier; displacement (§2.4) still unproved. Solve route: LP outer
approximation with warm-started dual simplex on HiGHS, SCIP-native `log` as the independent
cross-check; no conic solver on the machine. **`LIT_optimization` §0 folds in:** `EG^bal_S` is a
named object (an Eisenberg–Gale market, `jainvazirani2010`) but its price reading is a KKT
statement only — the EG optimum is *not* an equilibrium at stated budgets under per-agent
constraints (`jalota2023`); `≤ k−1` splits is `lenstra1990`/`shmoystardos1993`, "+ tight side
rows" is the rank lemma (`lauravisingh2011`); rounding-by-theorem is closed (`budish2013`, our
band is weighted, not a bihierarchy); no submodularity result exists for `S ↦ EG_S`, so (★) is
original; `borgwardt2019` keeps the `O(nk)` power-diagram certificate alive at `δ > 0`.

**Economic theory (`DOMAIN_economic-theory` §4, 2026-09-03).** Step 1: three audits on the
delivered artifact with no sponsor input — EF1 / FEFx / proportionality on the 13 × 13 matrix
(N1, N9), the 169-pair blocking test with gains (N3), closed-form Shapley and least core (N5,
N6). Step 2: the sponsor-facing **menu** `(δ, V, book share, μ, fairness verdicts)` per row,
MNW point marked — **★4 becomes a menu choice, not an elicitation**, and there are two knobs
(`δ` on `M`, `ε` on `g`; they came apart by 77.6×). Step 3: **D3 re-issued** — does the
equilibrium reading survive the band well enough to quote? Prices become personalised
`π_i(z) = p_z + ν_i M_z`; envy-freeness is lost, EF1 is replaced by FEFx, proportionality is
the first casualty. Step 5: **D5 splits** — audited book is needed for *selection* only; the
draw at fixed roster is `G`-invariant (P-G1, pending the `c2·T_z` coupling check N10). Step 6:
**D6** — the `fotakis2014` impossibility is over-read in four files; the invariant rests on
Gibbard–Satterthwaite generically. Step 7: **D7** — `S₁₃` is not unique at the programme's own
floor (8.1e-3 nats on seed 9); disclose the tie-break and report the near-optimal set.
**`LIT_economic-theory` 2026-09-03 §0 folds in:** `echenique2021constrained` prices constraints
and gives exactly `π_i(z) = p_z + ν_i M_z`, and proves fairness fails whenever constraints
single out agents — our per-agent band does, so envy is lost *by theorem*; `kawase2026balanced`:
MNW over balanced allocations need not be EF1 while balanced EF1+fPO allocations exist;
`breugem2022vertical` bounds the utility lost to per-player outcome constraints from high-level
parameters, a priori; `haimes1979tradeoffs` is the MRT-vs-MRS procedure; `chua2023multiunit`
half-closes the costly-verification gap.

## 4. The plan — units and dependency table

**Scope constraints applied** (user, 2026-09-03): ★6 lifted in full — units may read
`instance_descaled.json.gz` and run code · solver stack SCIP 10 / HiGHS 1.15 / scipy 1.18, no
conic solver · the sponsor's `δ` is un-elicited (FRAME §3's ±10% is the only number; `δ₀` =
0.39%) · tier-2 floor 5e-3 nats · nothing merges into `national-channel` without the user ·
**this session launches nothing** — the briefs are the deliverable · all units run on `wt/A1`.

**[pred] units, disposition.**

| unit | status | note |
|---|---|---|
| U0-lit | **landed** in A1 form (`LIT_optimization.md`, 46 entries, 2026-09-03) | the predecessor's nine questions were re-cut by `DOMAIN_optimization` §6; the split-count citation it was waiting for is `lenstra1990` |
| U1-cert | **landed** (`MODEL_U1-cert`, `VERIFY_U1-cert`) | P1 VERIFIED, P2 three-of-four, P3a's `≤ k` retracted; `EG_{S₁₃} = 60.6974` |
| U2-stab | **landed** (hub, `VERIFY_U2-stab` 13/13) | its N3 blocking test is now 169 comparisons and moves into U6-sel |
| U3-inv | **RETIRED** (user, 2026-09-04) | the books `S_i(z)` are measured directly from the data warehouse, not self-reported, so the strategy-proofness / misreporting question has no referent. ★2 (audited book) shrinks to a data-quality question, not an incentive one. N10 (the `c2·T_z` coupling) carries into U11-roster if it is still wanted |
| U4-disp | **carried** | still the highest-leverage unknown (FRAME §3.5); its new input is U8's band duals and first-mover list; `LIT_optimization` names the modulus a Hölderian error bound (absence D) |
| U5-crit | **retired as a unit** — folded into U12-menu | the criterion is two knobs `(δ, ε)` on one menu (`DOMAIN_economic-theory` §2.3, D2) |
| U6-sel | **carried, re-scoped and cheapened** | closed-form Shapley + least core, plus N1/N3/N9 audits on the delivered artifact; now a `python-typed` unit |
| U7-meas | **landed** (`MODEL_U7-meas`, `tools/measure/`, `CODEVERIFY` 15/17) | the ladder; rows 5, 7, 8 of its list survive into U13-base, U11-roster, U4-disp |

**New units for the A1 charter.**

| unit | one-line spec | agent → verifier | depends on | size | model |
|---|---|---|---|---|---|
| **U8-band** | Solve `EG^bal_{S₁₃}(δ)` at `δ₀` with duals; apply D1′ (one-solve softness certificate); trace the frontier on `{δ₀, 0.02, 0.05, 0.10, 0.33}` with bisection for `δ*`, SCIP cross-check at two points, MNW point marked; emit the first-mover list, N8, N9 (`DOMAIN_optimization` §2.10–§2.12, §5 rows 1–2, 4). | `python-typed` → `code-verify` | — (Stage 0 done) | **L** | opus |
| **U9-bandthm** | Prove or refute the four `[claim]`s U8 rests on: P1 with the band; the KKT price reading and its `jalota2023` caveat; `≤ 2k−1` splits; the envelope slope `dEG^bal/dδ = (T/k)Σ(μ⁺+μ⁻)` and the validity of every OA master optimum as an upper bound. | `modeler` → `math-verify` | — | M | opus |
| **U10-round** | Band-aware rounding of the `EG^bal` vertex at the sponsor's `δ` (≤ 325 binaries, `mip_rel_gap = 0.0`); `γ(δ)` at both solvers' vertices; the integer-balance-floor feasibility check `t*/(T/k)`; decide D2′ (`DOMAIN_optimization` §2.13, §5 row 3). | `python-typed` → `code-verify` | **U8** | M | opus |
| **U11-roster** | Roster enumeration in decreasing `P_S` under the (★) stop rule; `EG^bal_S(δ)` at every survivor (the `P₁₃` roster first); the exact Nash-tie margin on both draws; the near-optimal roster set at 5e-3 and 1.5e-2 nats; every `S₁₃`-conditional number as an interval (`DOMAIN_optimization` §2.14–§2.15, §5 rows 0c, 5; `DOMAIN_economic-theory` N11). | `python-typed` → `code-verify` | **U8** (the solver) | M | opus |
| **U12-menu** | The sponsor menu: rows `(δ, V, book share, μ, N1/N8/N9 verdicts)`, `breugem2022`'s a-priori bound on N7 beside the computed curve, `haimes1979` MRT-vs-MRS framing, the `(δ, ε)` two-knob statement, MNW point marked; the tie-break disclosure text (`DOMAIN_economic-theory` §2.3, §2.8–§2.10, §4 steps 2–3, 7). | `modeler` → `math-verify` | **U8**, **U11**; U13 for the baseline point | M | opus |
| **U13-base** | Construct A3's hand-drawn state-grouped baseline by its stated greedy rule (whole states to ≈ `T/k`, largest remaining neighbour first, split rule written down) and its top-book roster; score `(δ, V, P, D(g))`; place it on U8's frontier (`APPROACHES` §A3; `LENS_GROMOV` M11.3, ledger U10; `DOMAIN_optimization` §5 row 6). | `python-typed` → `code-verify` | — for construction; **U8** for the plot | S–M | opus |
| U6-sel *(carried)* | The 13 × 13 audits on the delivered artifact: EF1 / FEFx / proportionality (N1, N9), 169 blocking pairs with gains (N3), closed-form Shapley of all 111 and the least core (N5, N6) (`DOMAIN_economic-theory` §2.1, §2.4–§2.6, §4 step 1). | `python-typed` → `code-verify` | ★5 for N5 only | S–M | sonnet |
| ~~U3-inv~~ *(**RETIRED** 2026-09-04)* | ~~`G`-invariance of the fixed-roster map and of the `EG^bal` duals (P-G1–P-G3), N10, against `green1986`'s NRC; what `fotakis2014` forbids once books enter one concave objective (`DOMAIN_economic-theory` §2.7, §8 Q10–Q11).~~ Retired by the user: books are measured, not reported, so there is nothing to misreport. | — | — | — | — |
| U4-disp *(carried)* | The modulus `objective-gap ≥ φ(mass moved)`, now with U8's duals and first-mover list as input and `LIT_optimization` absence D's Hölderian-error-bound framing (`DOMAIN_optimization` §2.4, §8 Q3). | `modeler` → `math-verify` | **U8** | M–L | opus |

**Order.**
- **Wave 1 (independent, run in parallel):** U8-band, U9-bandthm, U13-base (construction),
  U6-sel, ~~U3-inv~~. U8 is the band-constrained kill test and goes first if only one runs.
  **Run 2026-09-04: U8-band and U9-bandthm launched in parallel and both landed verified**
  (`954d9eb`, `f199e92`, `69997ac`, `ddd162d`); U13-base and U6-sel were held for the D1′
  verdict and are still unlaunched; U3-inv is retired.
- **Wave 2 (gated on U8):** U10-round, U11-roster, U4-disp. **Unblocked 2026-09-04.**
- **Wave 3:** U12-menu (U8 + U11 + U13).
- **D1′ can end the track at wave 1:** if U8's one-solve certificate proves softness across
  the plausible band, record A1 `collapsed-on-softness` in `APPROACHES.md` §0, hand the
  problem to A5, and do not launch wave 2. **Did not fire (2026-09-04): the premium is NOT
  soft.** The gap is 0.683 nats at `δ₀` and 0.737 at `δ = 0.10` — 137–147× the 5e-3 floor —
  and there is no `δ*` on `[δ₀, 0.33]`. The whole frontier rises only 0.077 nats across an
  84-fold widening of the band, so the band was never what was binding. A1 continues; wave 2
  launches; `APPROACHES.md` §0 is **not** to be edited for softness. See FRAME §0 (2026-09-04).

**Estimate.** Wave 1 ≈ 2 L + 2 M + 1 S of subagent time; waves 2–3 ≈ 3 M + 1 M–L. **If the
budget halves:** run U8 and U9 only, then U10 at the single `δ = 0.10`; fold U11 down to the
`P₁₃` roster plus the tie margin (one solve, `k` Hungarian re-solves); replace U12 by a table
in FRAME §6; defer U13, U6, U3, U4.

## 5. Decisions needed from the user (★)

| ★ | question | gates | who answers |
|---|---|---|---|
| **★6** | Lifted in full 2026-09-03. | — | done |
| **★8** *(new)* | **Accept D6** — the `fotakis2014` scope correction: the "books enter at stage 2 only" invariant rests on Gibbard–Satterthwaite generically, not on `fotakis2014`, whose hypotheses A1's one-concave-objective formulation does not satisfy. Accepting it edits four hub files (`RESEARCH_FINDINGS` §9-G, `REVIEW_GROMOV`, `CHANNEL.md` §0, `APPROACHES.md`) and changes a settled item's *stated reason*. | the wording of A1's cost paragraph; U3-inv's framing | user (programme) |
| **★9** *(new)* | **The sponsor's band `δ`** — put as a menu after U8/U12, not as an elicitation: "at `δ` = 2 / 5 / 10% the marginal territory-dollar of balance costs X nats of continuity; which row?" Plus the second knob `ε` on the same page. | U10's `δ_sponsor`; the deployable map | user → sponsor, **after U12** |
| **★10** *(new)* | **Tie-break policy (D7):** disclose a named tie-break and report the near-optimal roster set, or randomise. Recommendation: disclose. Must be decided before any roster is announced. | U11's report format; every `S₁₃`-conditional number | user, on U11's evidence |
| **★11** *(new)* | **Rewrite A1's charter step 3** in `APPROACHES.md` from "rep-indexed MINLP" to "roster enumeration over band-constrained EG programs" — after U8 reports, per `LENS_GROMOV` M13.1 and `DOMAIN_optimization` §8 Q12. A hub edit. | the charter text only | user |
| **★12** *(new)* | **Merge `wt/A1` into `national-channel`?** Twelve commits (see FRAME §0); nothing merges without this answer. | the hub's resume point | user |
| ★1 | A2 — are the 98 released? Decides `d = 0` and whether **Caragiannis et al. 2019** applies (unchanged from [pred]). | U6-sel's EF1 verdict's citation | user → sponsor |
| ★2 | U11 — audited book at zip × wholesaler grain? **Now needed for selection only** (D5a); the draw at fixed roster is `G`-invariant pending N10. | U3-inv's live branch; U11-roster's deployability | user |
| ★3 | Stability as a hard requirement? Now decidable in 169 comparisons and a function of `δ`, so it may be one decision with ★9. | a sixth acceptance criterion | user → sponsor, after U6-sel |
| ★4 | Which welfare criterion — **restated as ★9's second knob `ε`**. | U12-menu | user → sponsor |
| ★5 | Report the least core? (De-escalated: with near-disjoint books it should be small.) | U6-sel's N5 | user |
| ★7 | Run `/domain econometrics` for U5/A4 (regional bias in `M`) and U6 (the noise floor, which U11's 8.1e-3-nat margin now makes urgent)? | the two hand-offs with no domain file | user |

## 6. Challenges to settled items (listed, not acted on)

[pred]'s six stand. Three are sharpened by the measurements and one is new:

1. **"Territories are drawn on opportunity, then staffed" (FRAME §9, settled as a business
   constraint).** Not challenged as a constraint; its *cost* is now a number: 0.760 nats at
   the delivered roster, all of it above 33% max deviation (U1-cert P4). Whether any of it is
   worth having is ★9's question, not a reopening.
2. **"Staffing is exact and selects the roster."** Sharpened: exact, but not unique at the
   programme's own floor (8.1e-3 nats, `CODEVERIFY_U7-meas`). D7 / ★10.
3. **"Books enter at stage 2 only" and its stated reason (`fotakis2014`).** `DOMAIN_economic-
   theory` §2.7a argues the citation is over-read. D6 / ★8. Listed, not acted on.
4. **"A certified k=13 draw exists"** → *balance-certified*. Still the free rename pass, still
   not done.
5. *New.* **"$1B ± 10% is probably not geometrically reachable" (`CLAUDE.md`, from the
   illustrative splits).** The measured draw sits at 0.39% max deviation; the sentence
   describes the superseded $6.2B scenario and should be retired from `CLAUDE.md` in the next
   `/state` pass. Wording, not a reopening.

## 7. What is deliberately not being done

- **Launching any unit in this session.** The user asked for the overnight run to proceed
  through the charter's stages 2–4 and stop before new units; it stops here. FRAME §0 records
  the assumption.
- **Building the rep-indexed MINLP** (`DOMAIN_optimization` §2.1). Retired to a contingency;
  fires only if U10's `γ(δ_sponsor)` exceeds 5e-3 with an exact reduced solve (D2′).
- **The τ-homotopy** (§2.6). Retired; U8's frontier in `δ` supersedes it (`LENS_GROMOV` M8).
- **The ε-constraint MILP frontier** (§2.5's old method) and **Benders** (§2.9). Replaced and
  deferred respectively.
- **`EG_R`** (the relaxation over all 111). Probably moot: the (★) screen at `P₁₃` = 60.8025
  is already below the 63.637 usefulness threshold `MODEL_U1-cert` §4.4 set for it.
- **Regional bias in `M` (U5/A4) and the noise floor (U6)** — no `DOMAIN_econometrics.md` (★7).
  `VERIFY_U1-cert` §6 confirms the bias is invisible to every certificate, including the new
  ones.
- **Contiguity, compensation, transition packages, residual channels** (FRAME §7).
- **The hub-file edits** D6's correction implies (★8), the charter rewrite (★11), the
  `CLAUDE.md` wording (§6.5) and the rename pass — all main-session work gated on the user.
- **Merging `wt/A1`** (★12).
