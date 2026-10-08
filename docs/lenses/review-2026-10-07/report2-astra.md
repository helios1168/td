STOP

v2 repairs most original design faults. Hold dispatch: dollar normalization can flip IFA's rule-C feasibility; old τ-based proof code cannot certify the new target-band model; and a support held whole in one plan need not remain whole after re-planning. These need contract changes, not implementation guesses.

Read-only review. No solver runs or repository edits. `A`, `B`, `P`, and `Contract` below mean the four drafts in `/tmp/iss/acb/v2/`; A1–A12 identify my round-1 findings.

## 1. Round-1 findings: disposition

| Finding | Status | Evidence / remaining change |
|---|---|---|
| **A1: holder no-good over-bans** | **Partly closed** | Contract:61–65 excludes the complete multiplicity vector, zeros included; A:68–69 tests both objections. Combinatorics fixed. Dollar-band proof domain and input identity still need C1/C2 below. |
| **A2: failed carved district → support ban** | **Partly closed** | P:21–22 correctly stops on B/P disagreement. Contract:66–68 and P:19 still allow an unconditional ban when a district is merely **currently** whole. Later plans may split one of its states. C2 fixes this remaining over-ban. My round-1 shorthand about “no split state” needed this qualification too. |
| **A3: contracted-root equivalence** | **Partly closed** | B:24–34 restores separate attach components, conditional rows, one-way proof and full-union gate; B:55–62 adds useful fixtures. Empty-attach roots disappeared from the model specification; per-piece `drawable` still uses the old band. C1/C6. |
| **A4: splittable versus actually split; F2 count** | **Closed at design level** | A:16–23 uses actual split indicators. Its row is valid for integer solutions **with F2 linking rows retained**: `n=0` is unrestricted, `n=1` permits at most one split, and `n≥2` on a multi-state support is forbidden—as intended, since every member then has multiple holders. Restate both F2 links explicitly in the replacement body. |
| **A5: missing re-plan/data contract** | **Partly closed** | Contract:29–47 supplies copy IDs, target shares, explicit windows, rule-off bound-only output, pool and CLI. Missing: consistent currency/rate identity, balance-LP entry point, WIFI semantics, search beyond the first optimal pool. C1/C3–C5. |
| **A6: certificate/status scope** | **Partly closed** | A:37–42 separates incumbent/lower status and forbids “minimal”; P:23 says “no map found.” P:54 incorrectly says `s_incumbent + g`; dollar-proof inheritance remains unspecified. C1/C4. The #110 record conflict remains a pre-wave task in CONSOLIDATED:43. |
| **A7: exact-only tractability** | **Partly closed** | B:10–21 is heuristic-first; B:35–39 stages measurements. “Add splits” is not implemented after unknowns; empty-piece seeding and timeout-with-incumbent semantics need repair. C3/C6. No empirical 900 s guarantee exists. |
| **A8: ranking / balance recarve** | **Partly closed** | A:35–36 pins counts; P:28–40 adds cuts, pool scoring and incumbent retention. But A's fixed-candidate LP was removed while P:37 still calls it. B retains candidates by border length alone. C4. |
| **A9: complete-map scope / eligibility** | **Partly closed** | P:44–47 includes main49 and WIFI. D1 intentionally replaces old IFA46–49 delivery scope; those K remain information-only. Currency-consistent audit/rendering and WIFI planning need assignment. FI-only “eligible” needs channel-result wording. C1/C5. |
| **A10: owner decisions** | **Partly closed** | D1–D6 settle K≥50, target-band ±15%, extra splits/no policy bans, and cuts second. B:13–14 keeps counties as seeds. Remaining choices: dollar denominator/WIFI measure, extra-split search mechanics, recorded frame updates. C1/C3/C5. Do not reopen answered D1–D6. |
| **A11: oversized stages / scope overlap** | **Open** | A's map acceptance was removed and document sections separated, but A:24–29 demands 39 C-on grid cells in the first hour, before the dollar migration/proofs are specified. B still requires both measurement stages in one acceptance. Top-three reporting was said to move to P but is absent. C7. |
| **A12: packet formatting / `$` rejection** | **Partly closed** | Standalone lists and `python3 tests/run_all.py` are correct. Appending A's “superseding” sections does not replace the first sections read by the parser. `--tracking` is outside the gate's accepted flags. C8. |

## 2. Cross-check of Fable's F1: CT under rule C

**Agree with the necessary-condition argument and old K thresholds. Disagree with using rounded RI or the new “1,328” number as evidence of feasibility.**

Direct opportunity outputs give:

- CT = **1,333.625795626** (`runs/exp/contig/whole127/ifa46-whole/districts.csv:7`).
- CT+RI = **1,676.184132626** (`runs/exp/contig/whole127/ifa46-pieces/districts.csv:9`).
- Thus RI = **342.558337**, not approximately 347.
- Sum of the 46 whole-plan district masses ≈ **48,988.987835** (whole-plan CSV, rows 2–47).

Under F1's neighbour premise, NY, MA and CT must split; RI is CT's only whole attachment. At least two CT holders therefore require

`M_CT + M_RI ≥ 2L`.

Under the old mean band, this gives the same thresholds: K≥50 at ±15%, K≥53 at ±10%, K≥47 at ±20%. Passing is necessary, not proof of a balanced or M1-clean carve.

**D3 removes K from this local inequality.** With target $1.25B, `L=$1.0625B`: CT+RI must contain at least **$2.125B**, regardless of K.

Two conversions now matter:

1. **Allocate the entire $62.14B across the above CONUS total:** target ≈985.45598 m_rel. Required CT ≈**1,332.71683**, leaving only **0.90896 m_rel**, approximately **$1.15M**, of joint slack—not roughly 6 m_rel. Extremely tight before M1.
2. **Use the recent render's recorded factor:** `ifa = 1.251968155812553` million dollars per m_rel (`runs/sweep/grid_2026-10-01/tables.json:8`, referenced by `ifa46-whole/render.json:3–6`). CT+RI then contains only ≈**$2.09853B**. Necessary condition fails by ≈**$26.47M at every K**. Increasing K cannot rescue it.

I have not recomputed `dollar_rates` on the current extract. Historical render factor proves a normalization discrepancy, not today's rate. Existing scorer used `62.14B/K` for IFA independently of ledger sums (`tools/looks/score.py:380–384`); `dollar_rates` instead divides by full-input fine-channel mass (`:263–269,364–365`). Resolve the denominator before asserting CT feasibility. A target-band decision does not itself authorize redistributing excluded opportunity onto CONUS.

**Replace A:32's arithmetic claim:**

> Under a target band, CT's necessary condition is K-independent: `M_CT_usd + M_RI_usd ≥ 2·0.85·T_IFA`. Evaluate it from the approved rate snapshot before the grid. If it fails, report rule-C infeasibility for every K covered by the neighbour/forced-split argument. If it passes, report exact slack, not feasibility. K46–49 remain informational unless the owner revises D1.

My A2 and A12 also remain supported; their qualifications are C2 and C8 below.

## 3. Remaining/new problems and replacement wording

### C1. D3 needs one mass/band definition and a proof extension. **Blocks.**

**Evidence:** A:11–15,47–49; Contract:33–38; B:20–21. `td/master.py:139–165` hardcodes `1±δ` around `ch.tau`. `plancheck.drawable:125–150` also builds a τ band. `td/spec.py:661–669` initializes mean bands. Changing masses to dollars does not change those centres.

Old `drawable` can falsely reject a legal target-band support: with τ=0.95T, a whole district of 1.10T passes [0.85T,1.15T] but exceeds the old upper bound 1.0925T. That old-model infeasibility licenses no new-model ban.

**Proof answer:** D3 does **not** inherently invalidate Proposition D or Claim 1. For fixed nonnegative additive dollar weights, positive represented state masses, explicit L,U and unchanged family/policies:

- Claim 1 still divides `L n_S ≤ Σ M_v t_vS ≤ U n_S` by `n_S`.
- Proposition D still sums per-copy rows. Corridor/path masses must use those same weights. Geometry, counts and land-area M1 stay unchanged.
- Neither argument needs the interval centre to equal total/K. Their currently defined domain does; document the extension instead of inheriting an unchanged `[proved]` tag.

**Add to A/Contract:**

> Freeze rate values, denominator population/filter, dollar-total version and targets. Owner resolves IFA full-input versus covered-CONUS normalization before runs. A owns a shared adapter supplying `m_usd`, `M_usd` and explicit `[L,U]` to planning, carving, drawable-alone tests and audit. Keep τ=total/K; do not disguise T as τ. Recompute mass-dependent rows in the chosen measure. Preserve documented tolerance semantics under consistent scaling.

> Extend MODEL §4.12 to fixed additive weights and explicit bounds, with Claim 1/Proposition D read-back proofs. Extend B's proof and drawable-alone invocation to that exact domain. Old mean-band infeasibility is not reusable merely because δ matches.

Add mixed-fine-rate and unequal-τ/T tests. Assign any needed `td/spec.py`, `td/master.py` or `plancheck.py` edits explicitly, or use adapters within permitted experiment paths. A's current Files list grants no production edits.

### C2. “Whole now” bans remain unsafe; cache identities are incomplete. **Blocks.**

**Evidence:** A:16–22 makes split states decision-dependent; Contract:66–68 allows fixed-union bans; Contract:8–11 identifies the extract by name only.

A failed whole union on S does not prove every partial-state district with footprint S fails. Re-planning can retain S but split a member. #127's permanently-whole-unit premise then no longer holds.

**Replace `support_ban`:**

> Unconditional `n_S=0` requires failure for every district with footprint S in the cut's policy domain. Whole-union failure suffices only if all S's units are globally forced whole. If merely unsplit in the current solution, exclude `n_S>0 AND s_v=0 for all v∈S`, not S itself. Test an S that becomes drawable when one member splits.

For multi-state S under rule C, use `n_S ≤ Σ_{v∈S}s_v`. Singleton supports need the bounded-count form, e.g. `n_{ {v} } ≤ U_v s_v`, preserving multiple split copies.

> A drawable-alone support ban must quantify over global allowed modes and the full target band. Freezing current attach states or target shares gives only a conditional proof, never an unconditional support ban.

**Replace identity wording:**

> Fingerprint opportunity input contents, numerical rates/normalization, targets, η/modes/caps, support universe, polygon/connector data and proof-model version. Validate every cut against these. `job_id` hashes the full job, including windows and balance targets. A filename or “2025 graph” is not a content identity.

### C3. D4/D5 says “Add splits”; v2 stops at the first unknown pool. **Blocks goal-directed search.**

**Evidence:** CONSOLIDATED:77; Contract:41–42,70; P:23–25.

All five plans share the same split count **and** optimal cut count. Unknown carves stop the channel. Extra splits occur only if proof-backed cuts remove every cheaper plan—the same proof bottleneck the owner authorized escaping. No API requests another split layer or other cut counts at the same split count.

**Replace:**

> Separate the clean certified bound from candidate search. After an unknown pool, request further candidate layers at fixed K and band: unexplored plans/cut counts at the current split count, then the next split count, within an explicit run budget. Add a search-layer/enumeration CLI parameter. These restrictions select experiments; they are never proof-backed cuts and never raise the clean lower bound. No policy bans. Budget exhaustion reports “no map found,” unresolved layers and the best audited incumbent.

Set the run budget before dispatch. If the owner intended stopping after five unknown plans instead, record that clarification; “Add splits” does not say it.

### C4. Balance LP is orphaned; ranking and gap arithmetic remain incomplete. **Blocks those claims.**

**Evidence:** A:33–49 has only three passes; P:37 still calls A's fixed-candidate LP; B:18–19 retains by border length; P:54 writes `s_incumbent + g`.

**Add to A/Contract:**

> With support multiplicities fixed, provide P's conditional balance LP: minimise worst then mean deviation from the declared target/mean basis. Export per-copy masses as soft targets through a named entry point or normal plan output. Claim no global balance optimum. Failed targeted recarves retain the audited incumbent and create no full-band cuts.

**Replace B's retention rule:**

> Border length guides search, not owner ranking. Retain the best validated candidate by the agreed drawn comparison, or pass candidates to P for comparison; do not discard fewer-defect candidates solely for shorter border.

**Replace P:54:**

> `s_drawn` is the ledger split count. When covered, `g=s_drawn−s_lower`; report `s_drawn=s_lower+g`, alongside `s_incumbent`, proof status and domain. Otherwise report `not covered` or unknown bound. A master incumbent is not a lower bound.

Separate target-relative balance metrics from legacy m_rel/τ looks diagnostics. D1 permits K≥50; it does not prioritize smallest K over fewest splits. Recommended clarification: “Try smallest feasible K first; compare reached K50–55 candidates under owner ranking within the run budget.”

### C5. Dollar migration stops before audit, rendering and WIFI. **Blocks real maps.**

**Evidence:** P:14–16,29–32,46–57; `td/output.py:416–420` combines ledger `m_rel` cells with instance bounds; `tools/exp/contig/run.py:421–445` reuses that path. `tools/maps/zip_pages.py:270–283` separately converts m_rel using a factor file. `tools/maps/summary.py:197` prints a fixed ±10% caption.

Scorer-only changes do not suffice. Dollar bounds against m_rel cells reject good maps; silently replacing m_rel with dollars causes double conversion. Maps can display different dollars from those certified.

**Add to P:**

> Preserve `ledger.csv:m_rel` units. Store dollar totals/bands/rate provenance separately. Construct audit masses and bounds in matching units, including planned/drawn share diagnostics, preserving cell ownership/routing and land-area M1. Write `scorecard.md` and `solver.json` too. Scorer, target-relative summaries and rendered dollars use one frozen rate snapshot. Pass it through render.py's existing `--fac` interface in its documented million-dollar units. Assign caption changes to explicitly allowed files.

> Rescore and update shortlist eligibility/tier/rank/labels under versioned D3 policy without overwriting historical evidence. Rebuild the index. FI20 alone is channel validation; full-main eligibility belongs to assembled main49.

**WIFI needs a decision:** does “keeps ±15% of its average” retain its previous **m_rel** mean, or adopt a **dollar-weighted** mean? It mixes fine channels with different rates, so these are different tests. D3's target decision does not unambiguously settle this exception.

> Encode WIFI's approved measure, `target:null`, `band_basis:"channel_mean"`, actual mean and bounds. Include WIFI3 in A's planning/API tests, with nullable `split` and zero `target_share` for whole-only districts. “No carve” does not mean “no plan or M1 gate.”

### C6. Empty-attach pieces and timeout semantics regressed. **Blocks B's model specification.**

**Evidence:** B:11–12,24–25; Contract:97.

Repeated singleton supports have no attach body to root flow. The v1 root-choice binary vanished. “Each piece … its heaviest ZCTA” can seed all empty pieces at the same ZIP. Standalone σ-piece connectivity is also stronger than union connectivity.

**Add:**

> For empty attach sets, the MILP chooses one owned root per piece. Heuristics use distinct available seeds. Fixed seeds or standalone-piece connectivity, if used as heuristic restrictions, never enter infeasibility proofs. Required connectivity is piece∪attach. Add all-empty-attach multi-copy and disconnected-piece/connected-union fixtures.

> Deadline covers search and validation. Timeout with a validated incumbent returns `ok` plus the engine stop reason; without one, `unknown`. Retain/publish first validated success before optional improvement. Proof fields are required for `infeasible`, not fabricated for heuristic `ok`.

### C7. First-hour scope grew; delivery obligations disappeared. **Blocks stage packaging.**

**Evidence:** A:24–29 demands `(10 IFA K + 3 main channels) × 3 bands = 39` C-on cells, before C-off comparisons, cutoff proofs, later passes, currency migration and new proof. P omits top-three acceptance; B:64 still requires both benchmark stages.

**Replace:**

> Stage 0 freezes rates, bands, proof/API domain and packet scopes. First arithmetic report gives total-capacity `ceil(M/U) ≤ K ≤ floor(M/L)` and CT's necessary condition; neither is a master certificate. Once the adapter works, prioritize FI20 and approved IFA ±15% cases. Schedule the full information-band/C-off grid and certificates as explicit follow-on stages. Post partial progress at one hour; unrun cells are pending, not infeasible.

Under full-total IFA normalization, M=$62.14B gives necessary capacity **44≤K≤58** at ±15%; every requested K46–55 passes that aggregate screen. This does not settle CT or global feasibility. Increasing K no longer relaxes each district's target-band window.

> Separate B's first benchmark milestone from later measurements. P's final acceptance reports up to three eligible main and IFA candidates, or why fewer exist. A toy/stub milestone does not close real-map acceptance.

### C8. Replace the actual issue body, not another appended amendment. **Blocks packet correctness.**

**Evidence:** A:3 supersedes sections “above”; `agent/wave/wave.mjs:128` selects the **first** matching section. `issueSections` preserves order (`agent/batch/stages/prepare.mjs:123–135`).

**Replace amendment instructions:**

> Replace canonical Goal, Files, Acceptance and Read first in filed #103; do not append duplicate headings. Remove obsolete lane/pass wording while explicitly retaining F2's linking rows. Attach the same final contract to every packet. Inspect parsed allowlists and checks before dispatch.

The `$` rejection itself is fixed. But `--tracking` is absent from `wave.mjs:26`'s allowed flags, so P:87 is not automatically selected. Require a saved integration/reviewer tracking check or an accepted runnable wrapper; do not assume the gate ran it.

Replace Contract:54's “rule-C-filtered diameter plan” stub with a versioned canned toy response. Current wording revives the rejected family-filter idea. Stub tests check orchestration; repeat the no-good end-to-end test against A's real CLI at integration.

## 4. Verdict

**STOP for dispatch as drafted.** Revised decomposition remains worth pursuing. Resume after C1–C8 enter canonical issue bodies, starting with:

1. Freeze IFA denominator and WIFI measure; recompute CT's necessary condition. If approved rates make rule C infeasible at every K, return that result to the owner—do not spend a wave on larger K.
2. Extend explicit-band proofs; replace bans based only on currently-whole districts with conditional exclusions.
3. Implement approved extra-split search and assign missing dollar/audit/balance interfaces.
4. Fix stage/packet mechanics; test FI and the complete two-piece CT+RI job before the wide grid.

DECIDED: none; review only, no policy or implementation changes applied.
LEARNED: Whole-union M1 failure supports an unconditional support ban only when whole-mode restrictions persist across re-plans; decision-dependent unsplit states require conditional exclusion.
LEARNED: Stored #127 outputs give RI 342.558337 m_rel from CT+RI minus CT; target-band CT feasibility is rate-normalization-sensitive and K-independent under rule C.
LEARNED[global]: wave.mjs selects the first matching issue section; appended duplicate Files or Acceptance headings do not replace the earlier packet sections.
