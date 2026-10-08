STOP

## Will it reach the goal?

Not as written. Most likely outcome: NY/Northeast carving returns `unknown`, retries consume budget, and P delivers plumbing or exploratory maps rather than eligible maps. Worse, its proposed bans can remove drawable plans while retaining a certificate label. FI K20 is a useful first integration target, not evidence that IFA K46–49 will work. K47–48 and WIFI are absent; complete main-map assembly is unspecified. Corrected decomposition is promising: with rule C applied to **actually split** states, different states can be carved independently, provided every complete district and the assembled ledger pass the unchanged audit. Neither 900 s success nor near-minimality follows from these issues. This is a static design review; no solver benchmarks or tests were run.

Issue-body citations below refer to `/tmp/iss/acb/review/issue-<n>.md`.

## Findings — most serious first

### 1. #130: proposed carve no-good is invalid. **BLOCKS.**

**Evidence:** `issue-130.md:20–23`; integer multiplicities in `docs/MODEL.md:124–138`.

`Σ_{S∈Q} n_S ≤ |Q|−1` does not exclude exactly the configuration tested. For example, when the tested holder counts on two supports are `(2,1)`, it also excludes `(1,1)`: one copy disappeared, yet the row still fails. Replacing counts with support-presence binaries fixes that example but not the second error: keeping those supports and adding another holder of σ changes the partition problem. An extra holder can absorb territory neither original holder can accept without a neck. Infeasibility is not monotone under that change.

**Replace feedback wording:**

> A proved-infeasible carve excludes only its complete holder configuration for σ: the multiplicity of every support containing σ, including zero multiplicities. Implement the disjunction `∨_{S∋σ}(n_S ≠ n̄_S)` with bounded-integer indicator rows or an equivalent exact encoding. Scope each exclusion to channel, K, τ, band, modes, rule C, graph/connector version, and the policy rows used in the proof. Different holders or multiplicities remain admissible. Broader exclusions require a separate proof.

The proof must cover **every allowed share allocation**, including unequal masses among copies, not merely A's exported target shares. Record a replayable carve job and proof provenance. Tests must preserve changed multiplicities, added holders, and feasible alternative allocations. No permanent cut from a heuristic, restricted repair, or timeout.

### 2. #130: failed carved district does not justify a support ban. **BLOCKS.**

**Evidence:** `issue-130.md:24–25`; `wholeplan.py:88–97,119–127`; `docs/MODEL.md:448–460`.

#127's ban is valid because **every unit is whole**: a support determines exactly one ZIP union. A support containing part of σ determines many unions. One failed carve proves only that assignment failed. Even an attach state's internal neck may disappear when a different σ piece supplies another route, widens the boundary, or changes the land-area denominator. “This can only come from an attach state's own internal neck” is also false: disconnected attach components and assembly/model errors are other possibilities.

**Replace:**

> If B returned `ok` but P's identical full-union M1 check fails, stop with a contract/integration error; add no support ban. For a district with no split state, an exact fixed-union M1 failure may ban that support. For a district with a split state, ban the support only after a separate drawable-alone proof covering all permitted pieces and masses. An unresolved gate produces `unknown`, never a ban.

### 3. #129: contraction can be a relaxation, but the claimed equivalence is false. **BLOCKS proof-driven feedback.**

**Evidence:** `issue-129.md:14–27,36–41`; `plancheck.py:162–182,337–397`; `docs/MODEL.md:411–440`; `td/audit.py:565–597`.

Contracting an arbitrary attach set to one root makes connectivity **easier**. Every truly connected union projects to a connected quotient, so this operation alone does not invalidate an infeasibility proof. But the converse fails when attach ZIPs have multiple components: the quotient invents paths between them. It also hides internal necks. B cannot both ignore those necks and prove that every accepted assignment passes M1.

Existing `plancheck.drawable` contracts **each connected held component separately**, requires flow to every component, and gates the expanded union. Its wide rows are conditional: both anchored bodies must hold at least 5% of the candidate district's land. An unconditional 10 km row excludes legal small fringes. Therefore the proposed pinch-under-10-km toy is not necessarily infeasible; land shares, alternate routes, and connector treatment matter.

**Replace model/proof wording:**

> Retain one node per connected attach component, not one artificial root for their union. Reuse the proved conditional wide-passage and NeckCut constructions on each full district, preserving land-area conditions, `border_cm` rounding, and `land_would_do` semantics. Do not require the σ piece alone to be connected when its attach states connect it. The MILP need only contain every admissible M1 carve. `ok` requires an independently checked full-union M1 pass for every piece, all mass/policy checks, and a complete state partition. Attach-state internal necks are included in that gate.

> `infeasible` is enabled only after the relaxation/row-validity proof is verified. A `[claimed]` proof may ship an experimental search, not certificate-producing bans.

Small exhaustive fixtures should check that no M1-valid assignment is excluded: disconnected attach sets, sub-5% fringes, internal attach necks, connectors, and unequal-copy masses. Solver tolerances remain documented, not silently tightened.

### 4. #103: distinguish “may split” from “does split”; F2 itself is conditionally correct. **BLOCKS.**

**Evidence:** `issue-103.md:11,51`; `docs/MODEL.md:126–162`; `tools/looks/score.py:213–225`.

All states are candidates, but the amendment retains supports with at most one **splittable** state. Literally applied to all free candidates, this removes multi-state supports even when their states would remain unsplit. It is not the intended rule.

**Replace:**

> All states remain candidates. For each active support, enforce `n_S > 0 ⇒ Σ_{v∈S}s_v ≤ 1`, where `s_v` means actually split, not merely allowed to split. States with `s_v=0` have one holder and contribute their entire territory to it. Do not filter supports by the initial free-state list. Test a support containing several candidate states with only one actually split.

**F2 answer:** for represented positive-mass state units, integer `n`, η>0, coverage, and valid caps give `1 ≤ r_v=Σ_{S∋v}n_S ≤ U_v`. The two rows imply `s_v=0 ⇔ r_v=1` and `s_v=1 ⇔ r_v≥2`. Aggregation does not break this: equal decoding `t_{v,S}/n_S` supplies positive mass on every copy and satisfies the aggregate band's per-copy counterpart. Rule C is not needed for this counting proof; it enables independent carving.

This equals the **scorer's** count only if the drawing retains those footprints. Every declared holder must own a ZCTA; zero-opportunity ZCTAs count; no later territory-fill pass may introduce unplanned state contacts. Zero-mass units omitted by the master remain a coverage/counting gap. An η-free bounding model must not inherit the η>0 decoding proof.

### 5. Contract: outputs exist, callable re-planning does not. **BLOCKS integration.**

**Evidence:** contract at `issue-103.md:67–103`; `wholeplan.py:107–117` calls `master.exact_delta` then `master.plan`; neither call implements A's F2 lexicographic re-plan contract.

P cannot independently implement “call A with these exclusions” from the three JSON examples. Reusing #127 unchanged also silently changes δ and optimises diameter rather than splits.

**Add one shared callable contract before dispatch:**

> A owns a re-plan API/CLI accepting the scenario/instance identity, channel, K, explicit planning δ, rule C, proof-backed holder exclusions, and requested pool enumeration. It returns a plan pool plus `feasible`, `infeasible`, or `unknown`, with objective-stage bounds and provenance. Every call reruns the same split/cut objectives. P never substitutes the production diameter or smallest-δ master.

Add these semantics, not another framework:

- Stable `plan_id`, parent/re-plan ID, canonical support IDs and copy ordinals, support multiplicities, pool index, and `(splits,cuts,diameter)` values. `pool_rank` is not an identity. Specify how P requests/tries another plan and what “near-tied” permits.
- Instance/scenario/graph references and channel footprint; fine-channel routing must be available to ledger assembly. Reject mismatched jobs/results.
- `delta_plan` versus final audit band, and the band's inclusion in certificate/cache keys. A's ±20% frontier is information, not permission to draw an eligible map at ±20%.
- Define `share` as a **target mass**, initially `M_σ t_{σ,S}/n_S`, not a mandatory exact ZIP mass. This is already the decoder's rule (`td/master.py:336–382`); multiplicity does not make decoding mathematically undefined. Carves may need unequal copy masses.
- Define complete piece intervals from the district band minus whole-state mass, intersected with physical bounds and explicitly applicable policy bounds. “Clipped so pieces sum” is not a clipping algorithm: the partition enforces conservation; interval tightening must preserve every feasible allocation. Require nonempty holders and check read-back membership before claiming a covered floor.
- Rule-off plans may contain several split states per district; the one-`split` schema cannot represent them. Either export rule-off **bound reports only**, explicitly, or give them a separate supported representation. P consumes C-on plans only.

### 6. #103/#130: certificates and terminal statuses need stricter scope. **BLOCKS certified/minimal claims.**

**Evidence:** `issue-103.md:22,56,77`; `issue-130.md:9,35–46`; `WATCHDOG.md:65–67`; `docs/problem/PROBLEM.md:58–61`.

A certified restricted master floor is not an all-M1 minimum. A floor at ±10% need not cover a carve at ±15%; an η-constrained proof cannot silently constrain the η-free certifier. Invalid bans make later cutoff proofs irrelevant to the intended domain. Unknown lower proof plus literal `gap: 0.0` is misleading.

The records also conflict: WATCHDOG lists #110 open, while PROBLEM records its answer; #103's old acceptance says its restricted floor never backs “minimal,” whereas P allows that word “under the stated rule.” Do not resolve this through implementation defaults.

**Replace:**

> Report incumbent split count, certified lower bound, proof status and domain separately. Use `g` only when a certified bound covers the final ledger's read-back; otherwise report `unknown` or `not covered`. Distinguish original floor from any re-plan bound and retain every cut's proof scope. No unqualified “minimal” or “must split”; reconcile the recorded #110/#119 wording before selecting final terminology.

> `no plan` means proved infeasible in the named search class at the fixed approved settings. Solver timeout, unresolved M1, retry exhaustion, or exhausted sampled pool means `unknown/no map found`, not infeasibility. A successful code milestone with no eligible map is not completion of the map goal.

### 7. #129/#130: exact-only search has no credible 900 s success commitment. **BLOCKS current delivery expectation.**

**Evidence:** `docs/RESULTS.md:989–1015` records zero B bans and FI's no-incumbent result at 600 s; `1222–1249` records M1-clean county plans but no eligible result. `plancheck.py:157–161,400–434` already tries constructive growth before MILP.

I do not know whether NY/CA k-piece instances will finish in 900 s. Removing cross-split-state coupling may help; simultaneous partitioning, free roots, label symmetry and repeated neck separation may hurt. These issues contain no measurements that settle it. An M1-invalid assignment start is not a feasible incumbent for the full model.

**Replace search order:**

> First try a bounded constructive carve, existing-ledger seeds and local boundary moves; validate every candidate with the exact full-union gate. Reuse existing growth/repair machinery where suitable. County partitions are seeds only, never fixed boundaries. Keep the best audited feasible candidate. Run MILP as improvement/fallback and as a separate proof attempt; do not wait for objective optimality before returning an audited `ok`. Record time to first valid carve separately from objective/proof time. Retain a guiding objective, not a zero-objective feasibility solve.

Try other tied plans while a difficult proof is pending. Search-only diversions must be labelled separately from mathematical bans and must not manufacture a lower bound. ReCom is optional, not a prerequisite or new dependency. Exact **M1 checking** is required for every `ok`; exact **optimisation** is not. Verified relaxation infeasibility is required for bans. Benchmark NY and one problematic attached-state case before funding the full frontier.

### 8. #103/#129/#130: ranking still diverges from owner's order. **BLOCKS ranking claims.**

**Evidence:** `WATCHDOG.md:58–64`; `issue-103.md:5,11`; `tools/looks/score.py:419–436`; `issue-129.md:18–19`; `issue-130.md:28–29`.

Important correction to the review prompt: **A already specifies cuts in pass 2 and diameter in pass 3.** Do not fix an absent error. Real defects:

- “Pin the chosen split set” after pass 1 prevents cuts being minimised across other equally small split sets. The council's intended row pins the **count** (`docs/lenses/COUNCIL_2026-10-05.md:93–95`).
- Existing scorer's actual rank key omits cuts entirely. #103's opening ranking is stale too.
- Cut **border length** is not number of cuts `Σ(r_v−1)`. For a fixed holder configuration the latter is already fixed. Border length/diameter are shape proxies, not a guarantee against small pieces, crowding, or poor drawn extent. B's within-state border objective also omits assignment-dependent boundaries against attach states.
- P does not require trying and ranking the pool. First feasible is not best-looking.
- P's balance recarve has no target-share field in its job. With unchanged full-band windows it can repeat the same carve; enforcing new exact LP shares can instead destroy feasible ZIP assignments. That restricted failure cannot justify a full-band ban.

**Replace/add:**

> Pin `Σs=s*`, not the first split-set identity; minimise and pin total cuts, then diameter. Enumerate and draw the agreed tied/near-tied pool. Score drawn maps by splits, cuts, defects, shape, worst deviation, mean deviation, retaining the settled REVIEW exception. Add cuts to scorer output/ranking and its test, explicitly widening the owning issue's Files list.

> The fixed-candidate LP freezes support counts and supplies soft balance targets. Retain the last audited carve; accept a recarve only when its actual ranking improves. Balance-target failures produce no full-band bans. Describe master objectives and border length as proxies; report achieved drawn keys, not a globally optimal looks claim.

### 9. #130: scope and eligibility acceptance can finish without the requested maps. **BLOCKS goal completion.**

**Evidence:** `issue-130.md:30–47,99–100`; `BRIEF.md` channel list; `docs/MODEL.md:805–857`; `tools/looks/score.py:328–350`.

WIFI K3 is omitted. National15+WH11+FI20 totals 46, not an eligible complete main-map K; adding WIFI gives 49. IFA K47 and K48 are omitted, and only FI plus IFA46 are in map acceptance. A FI-only gate pass is a channel result, not a main-map eligibility result. “Check every district” also does not check missing fine-channel cells, routing, duplicates, K, or bands.

**Replace map acceptance:**

> Integration covers FI20 first; IFA46,47,48,49; then one assembled ne_plains main map with national15/WH11/FI20/WIFI3. WIFI may reuse a matching audited ledger, with provenance and revalidation. Run the full scenario-aware ledger audit, M1, final bands, K and dollar checks on each complete map. Render only tracked runs and rebuild the shortlist index. Report eligible maps, or explicit failed/unknown requirements; do not call channel fragments or tier E maps goal completion.

Dollar semantics need explicit reconciliation: #103 and existing scorer check **channel-average** dollars per district (`score.py:271–278,339–345`), while WATCHDOG/brief can be read as a requirement on **each district**. The two tests differ. Do not silently strengthen or weaken this; name the metric and obtain owner clarification if literal per-district limits are intended.

Tier E currently covers M1-clean balance failures, not arbitrary failed checks (`tools/shortlist/shortlist.json:2–8`). Invalid ownership/routing must not be promoted to E. Keep M1-unresolved results ineligible.

### 10. All three: owner decisions remain required at policy boundaries. **BLOCKS automatic trade-offs, not experiments.**

**Evidence:** `WATCHDOG.md:72–84`; `issue-103.md:54`; `issue-130.md:20–29`; `docs/RESULTS.md:1227–1240`.

Pipeline approval supports trying this method; it does not clearly settle every future trade-off.

**Add an owner-decision checkpoint:**

> Confirm whether, at fixed K and approved band, re-planning may increase the split count above the initial floor, and what happens when no carve is found. Until confirmed, report the alternative and its cost; do not silently adopt it. No automatic widening of δ, movement to a different policy class, or declaration that #112 is resolved.

#102: record this as the approved experiment, not proof that the final M1 method is settled. OD1: keep the three-band frontier informational; do not inherit #127's automatic smallest-δ widening. OD4: county warm starts are harmless if freely recarved at ZCTA grain; fixed county restrictions would settle it by default. #111: preserve existing declared η for planning; no new smallest-piece threshold. Reconcile #110's conflicting records as noted above. M1 itself is not negotiable.

### 11. All three: oversized lanes and real dependency chain. **BLOCKS current 2 h packaging.**

**Evidence:** `issue-103.md:9,19–25,50–60`; `issue-129.md:23–43`; `issue-130.md:97–100`; wave skill's work-stage timeout is 7,200,000 ms.

No reasonable assurance that these tasks finish in one 2 h stage without questions. A retains original sweep/maps/top-three/F6 acceptance **plus** five named channel/K configurations × three bands × two C modes, certificates, pool export and proof. B combines an unproved formulation extension with five hard-state measurements. P can build meaningful fixture-based orchestration in parallel, but cannot establish real acceptance before A and B exist. P already acknowledges Round 2; that should not be overlooked.

**Replace packaging:**

> A owns the master, re-plan API, certificates and plan pool, not rendering. P owns integrated runs, full-map audits, ranking and top-three reporting. Keep A's cutoff validation and small applicable F6 cross-check; move the full frontier and repeated experiments to a scheduled follow-on stage with explicit completion criteria. B first delivers validated carving and first-feasible measurements; certificate-producing feedback waits for verified proof. P's fixture stage is not final map acceptance.

Avoid three concurrent appenders to `docs/MODEL.md`, `docs/RESULTS.md`, and `docs/CODE_MAP.md`: designate one integrator or explicitly reserved sections and ordered merges. Preserve original requirements by reassignment, not silent deletion.

### 12. All three: wave packet formatting and checks are mechanically broken. **BLOCKS launch.**

**Evidence:** all three `## Files` sections; `/Users/Shared/sv-ntlee/agent/wave/wave.mjs:35–47,99–113,127–154,219–244`.

`bulletPaths` accepts only backticked path tokens on bullet lines. Each Files list therefore parses empty, so every changed path is out of scope. #103's later “Files, widened” paragraph is not merged into its canonical Files section. #103's unquoted Read first bullets become unresolved references; #129/#130's non-bullet Read first text is not processed.

**Replace mechanically:** one `- \`path\`` per entry under canonical `## Files` and `## Read first`; place section restrictions outside the backticks. Include all amended paths, full geography-memory path, and whichever issue owns scorer/ranking changes.

A further gate gap: `safeCheck` rejects `$`, so `"$TD_PY" tests/run_all.py` is not auto-selected (`wave.mjs:57–66`). Put supported `python3 tests/run_all.py` in Acceptance; the gate prepends the hub virtualenv (`wave.mjs:227–229`). Ensure packet checks are nonempty and include the intended new tests; verify tracking separately where its invocation is not accepted by the command parser. Inspect the packet before dispatch, not after a worker commits.

## Part 2 ratings

- **C1 — confirmed; BLOCKS.** No F2 re-plan/cut API. Diameter fallback is a risk, not an unavoidable implementation.
- **C2 — confirmed, both objections; BLOCKS.** Need complete holder multiplicity exclusion, including absent supports, scoped to the proved domain.
- **C3 — partly; BLOCKS current success expectation.** Stalling is a strong evidenced risk, not a measured prediction for the new model. Heuristic-first audited feasibility is appropriate; ReCom specifically is optional. Existing `grow` already follows this pattern.
- **C4 — refuted; NOT a blocker as stated.** #103 already puts cuts second. Actual blockers are pinning a split-set identity and scorer's missing cuts key.
- **C5 — partly; BLOCKS contract until explicit.** Existing equal-copy decoding defines target shares. Contract must distinguish targets from admissible unequal realized masses and carry copy IDs.
- **C6 — confirmed; BLOCKS current packaging.** Amendment adds rather than supersedes B2 acceptance. Transfer map delivery to P; retain appropriately scoped formulation checks.
- **C7 — confirmed; BLOCKS complete main map.** WIFI is missing; add audited assembly. IFA47–48 are missing too.
- **C8 — partly; BLOCKS unapproved escalation.** Experiment has owner approval, but automatic extra-split policy and limits are not clearly recorded as resolution of #112. Ask before adoption.
- **C9 — confirmed; BLOCKS launch.** Empty parsed Files lists; Read first handling is also broken. `$TD_PY` acceptance command adds a third mechanical gap.

## Proposed plan changes

1. **Before wave:** reconcile policy questions and canonical issue bodies; freeze the small callable/data contract; repair packet scopes/checks. No repository edits were made by this review.
2. **Parallel build:** A implements F2, actual-split rule C and callable planning; B implements heuristic-first full-union-validated carving; P implements fixtures, ledger assembly, tracking and ranking. Proof obligations remain with their mathematical owners; one integrator owns shared documents.
3. **First integration:** run FI20 and difficult NY/attached-state carving before full sweeps. Require real audited incumbents and record first-feasible times. This is a feasibility milestone, not a claim of minimality.
4. **Proof stage:** verify relaxation and exact holder exclusions; then enable permanent feedback. Until then, failed candidates remain search observations, not bans. Preserve best audited incumbents and separate temporary pool exploration from proof-backed exclusions.
5. **Delivery:** IFA46–49 and complete main49, full audit and owner ranking; P reports top eligible candidates. Run frontier/certificate extensions in bounded follow-on stages.
6. **Fallback:** try alternate tied plans and permitted local recarves. If no eligible map emerges, retain M1-clean exploratory results under correct tiers and ask which explicit #112 trade-off to try. Never substitute a wider band, invalid cut, county restriction, or `unknown` labelled “no plan.”

DECIDED: none; review recommendations only, no implementation or policy changes applied.
LEARNED: In reviewed checkout, tools/looks/score.py:419–421 ranks splits then defects, omitting WATCHDOG's second-ranked cuts.
LEARNED: A support failure licenses #127's exact support ban because every unit is whole; a failed carve of a partial state does not establish support-wide infeasibility.
LEARNED[global]: agent/wave/wave.mjs parses Files only from backticked paths on bullet lines; appended prose scope amendments are not added to that allowlist.
