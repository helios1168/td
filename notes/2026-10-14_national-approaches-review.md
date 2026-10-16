Model: openai-codex/gpt-6-astra, thinking max (verified from the run's session log by the supervisor; the reviewer could not see its own model id)

# Mathematical review of the national-approaches note

**Question and decision:** Are the recorded formulations and explanations of past national-map attempts mathematically sound and supported by their implementations, so the owner can choose a new approach on correct premises?

## Recommendation

**Use the note as an experiment history, not yet as the mathematical specification for the next formulation.** Its central distinction—unit-level planning is not ZIP-level feasibility—is correct. Several load-bearing claims nevertheless need correction:

1. Current repair and drawable-alone checks omit parts of the current neck rule, beyond the connector discrepancy already identified.
2. Prominent “exact drawing” timeouts occurred entirely in the **geodesic-DAG restriction**, before the unrestricted connectivity model ran.
3. The supposedly “fully exact” older passing map has a **master-solver certificate**, not an exact-drawing certificate.
4. C20 confuses a district occupying **part of Florida** with Florida’s whole-state mass.
5. Multiple channels do not mathematically prevent regional decomposition; the ZIP-disjoint merge implementation imposes that limitation.

### Review basis

- I read all 529 lines of `notes/2026-10-14_national-approaches-formulations.md`, the relevant local implementations, `PROBLEM.md`, and `docs/MODEL.md`.
- I inspected the accessible hub run reports and dollar tables. **No solver, graph computation, or ledger aggregation was rerun.**
- **Verified** below means established by inspected source, a proof, or an explicitly identified saved report—not a fresh execution.
- **Inferred** identifies causal explanations that the evidence does not establish.
- Branch/tag-only implementations—including window-band modifications, `sealed.py`, `warm.py`, and `glue.py`—are **not verifiable by me**. Their quoted snippets in the note are not independent verification.
- `runs/...` citations refer to the hub clone’s gitignored artifacts.
- The owner rulings supplied in the task govern this review. Older contrary prose is not grounds to reopen them.

## 1. Per-section verdicts

| Section | Verdict | Key reason |
|---|---|---|
| §0 | **Sound with corrections** | Locality and channel-feasibility separation hold conditionally; routing certification, WIFI’s conditional cap, arithmetic sufficiency, and the objective need sharper statements. |
| §1 | **Not verifiable** | The legacy implementation and tagged review are unavailable here; the note itself did not inspect that implementation. |
| §2 | **Sound with corrections** | Aggregate master and ideal transport-rounding mathematics are sound within their stated domain; arbitrary bans and floating-point/tiny-ZIP handling qualify the guarantees. |
| §3 | **Sound with corrections** | Fixed-centre formulation is accurate; timeout or repeated-incumbent termination does not certify a local optimum. |
| §4 | **Unsound** | Its current-M1 repair infeasibility claims are too strong: neck cuts/checks omit relays and some width edges, besides using the old connector rule. The basic P-connectivity cuts are sound. |
| §5 | **Unsound** | Proposition B is sound, but the implemented test no longer establishes its premise under current M1; whole-unit checking has the same relay omission. |
| §6 | **Sound with corrections** | Accurate historical restricted pipeline; historical eligibility and smallest-δ results are not current-window or national-feasibility certificates. |
| §7 | **Sound with corrections** | Correct identification of restrictive symmetric bands and margins; K=1 and strict-interior handling need qualification, and widened bands permit—not force—dollar failures. |
| §8 | **Sound with corrections** | Sealing is a restriction under matched parameters; `--window` intersects the old band, and channel overlap is an implementation issue rather than a mathematical obstruction. |
| §9 | **Not verifiable** | Driver implementation is branch-only; accessible results do not isolate symmetric bands as the sole cause. |
| §10 | **Not verifiable** | Window substitution is mathematically sound, but its implementation is branch-only; saved failures do not establish failure of the unrestricted drawing model. |
| §11 | **Not verifiable** | Passing output reports are inspectable; warm/glue implementation guarantees are not independently verifiable here. |
| §12 | **Sound with corrections** | Pattern selection is sound for a consistently gated, restricted library; pricing, certificate scope, and obsolete objective/shape filters need correction. |
| §13 | **Sound with corrections** | Connected coarse units preserve P when expanded, not all M1; coarsening and `rulec_enum.py` restrict the search and do not establish ZIP feasibility. |
| §14 | **Sound with corrections** | Useful descriptive comparison, but multi-channel sealing and “absolute window in repair” are overstated; causal attribution remains unproved. |
| §15 | **Sound with corrections** | Runtime and attachment problems are evidenced; B6, the fully-exact premise in B7, and part of B3 require correction. |

“Unsound” in §§4–5 concerns the asserted **current-M1 certificate interpretation**, not the validity of every constituent model or the historical usefulness of those tools.

## 2. Every §16 claim

### C1 — **Verified**, as a mathematical locality statement

For fixed graph, channel masses, and zero-opportunity set, another district’s ownership does not enter P or N for \(X\). Relays depend on zero opportunity, not their owner.

**Code:** `td/audit.py:1016`:  
`zero = {z for z, m in chm[ch].items() if not m > 0}     # R3: no opportunity in ch`

**Proof:** P reads \(G[X]\). N reads \(X\), its land area, fixed widths, and the zero vertices reachable from it. Changing ownership outside \(X\), while preserving masses and routing, changes none of those inputs.

**Qualification:** An operational `unresolved` verdict also depends on computational limits. Locality does not mean a truncated ledger supplies the correct zero set.

### C2 — **Weakened**

With no land-gap adjacency edges, P-components are identical. Every **mathematical neck witness** under gap-width-on remains a neck under gap-width-off.

**Code:** `td/audit.py:563`:  
`self.border_cm[a][b] = self.border_cm[b][a] = border_cm(m)`

**Proof:** Adding nonnegative-width edges and reachable relay vertices cannot decrease the minimum cut width for a fixed own-connected side \(A\). Restrict any augmented cut to the old graph to obtain a cut no wider.

This does **not** guarantee identical reported necks: the routine selects witnesses rather than listing all of them, and a time-limited `unresolved` result need not be monotone.

### C3 — **Weakened**

The conditional theorem is correct: a connected union of internally connected states is ZIP-connected.

**Code:** `td/spec.py:488`:  
`unit_adj[ua].add(ub)`

A unit adjacency represents an actual ZIP edge; expanding a spanning tree of connected units proves the implication.

The empirical premise “all 49 states are connected” is supported by the committed regression assertion, but I did not recompute it:

`tests/test_spec.py:403`:  
`assert not inst.report["disconnected"] and not inst.report["disconnected_whole"]`

This proves only P, not the neck condition.

### C4 — **Verified** for the inspected implementation and saved IFA results

The inspected audit/scorer/gate paths contain no Manhattan exemption. The Manhattan references in `td/audit.py` are explanatory text.

**Code:** `td/audit.py:1055`:  
`status = "fail" if items else "pass" if ng is not None else "unverified"`

The saved IFA record identifies the exception externally: `runs/exp/sealed_2026-10-14/ifa/IFA_INDEX.md` lists the Manhattan neck for every K48–54. Its “passes” classification explicitly incorporates the owner exception; it is not an unmodified `check_m1` pass.

### C5 — **Weakened**

Proposition D extends to arbitrary fixed lower/upper bounds: summing per-district inequalities uses no symmetry. Corridor, border, count, coverage, η, mode, and contact arguments remain valid within the same domain.

**Code:** `td/supports.py:337`:  
`floor = max(floor, lightest_path(zs, inst.units.zip_adj, ch.m, side, rest))`

But “every row of §2(b)” includes arbitrary bans:

`td/master.py:189`:  
`rows.append(Row("ban", (s,), {model.n_col[s]: 1.0}, -math.inf, 0.0))`

**Counterexample to the literal wording:** Ban a support used by an otherwise qualifying connected drawing. Its read-back violates the ban. Either exclude policy bans from the proposition or include compliance with them in the domain.

The window-band branch implementation is **not verifiable by me**.

### C6 — **Verified**, for continuous explicit-copy plans

**Code:** `td/master.py:379`:  
`share = {v: t[v, s] / n[s] for v in sorted(s)}`

**Proof:** Copies of a common support have identical linear per-copy restrictions. Their average preserves η, corridor floors, and band inequalities; coverage totals and support-dependent objectives remain unchanged. Counts and caps depend on copy counts, not their differing shares.

This is not losslessness for **indivisible ZIP drawings** or for preserving each original copy’s geographic realization.

### C7 — **Weakened**

For \(K>1\), the unrounded maximal symmetric interval is contained in the window and equals it only at the midpoint. Rounding down can prevent equality even there.

**Code:** `tools/exp/contig/overnight.py:264`:  
`d = math.floor(min(tau - lo, hi - tau) / tau * 1e4 + 1e-9) / 1e4`

The implementation has a genuine exception:

`tools/exp/contig/overnight.py:263`:  
`return K1_FINAL_DELTA if lo <= tau <= hi else None`

For K=1, the returned symmetric interval need not be contained in the window. The sole district still has fixed mass \(\tau\), so its arithmetic eligibility can remain correct.

Also, small positive headroom can round to zero and be rejected despite \(\tau\) being strictly inside the window.

### C8 — **Verified as necessary arithmetic**, not sufficient feasibility

For common bounds,
\[
\left\lceil M_c/U_c\right\rceil\le K_c\le
\left\lfloor M_c/L_c\right\rfloor.
\]
The reported masses give national 12–16, WH 9–11, FI 18–24.

**Code:** `td/spec.py:660`:  
`tau = sum(M[u] for u in keep) / c.k`

These are **arithmetic-admissible** K values. ZIP indivisibility, disconnected footprints, necks, and restrictions can eliminate them. WIFI’s conditional allowance requires separate treatment.

### C9 — **Verified**

The objective contains support diameters, not balance deviations; share columns have zero objective cost.

**Code:** `td/master.py:149`:  
`model.t_col[v, s] = _add_col(model, 0.0, 0.0, 1.0, False)`

Saved edge-reaching plans appear in `runs/exp/national_2026-10-14/probes/split_rules.md`.

**Qualification:** This establishes indifference, not an objective explicitly maximizing imbalance. Nor does an edge-valued planned share necessarily constrain the later draw to that value.

### C10 — **Verified**, for the unrestricted modeled connectivity problem

**Code:** `tools/exp/contig/draw.py:1269`:  
`row(-inf, 1.0, [col[z, j], col[b, j]] + sidx, [1.0, 1.0] + [-1.0] * len(sidx))`

**Proof:** A path from a selected vertex in the detached component to the retained root—or to selected \(b\) in the rootless case—crosses each stated separator. For the second ring, take the path’s first entry into the old main component; its preceding vertex is both near-main and reachable without entering main.

At the generating assignment, separator vertices are unowned and the relevant endpoints are owned, so the row is violated. Exact separation therefore excludes at least one binary assignment per unsuccessful round.

This establishes finite, potentially exponential termination **without time limits**, not a polynomial runtime guarantee or validity of DAG restrictions as necessary conditions.

### C11 — **Verified**, with scope qualifications

**Code:** `tools/exp/contig/draw.py:982`:  
`row(0.0, 0.0, idx + [col[v, j]], val + [-1.0])`

**Proof:** Contract each genuinely connected fixed body. Route subtree sizes along a spanning tree rooted at the chosen body. Every selected free vertex and other body consumes one unit; the implemented capacities exceed total demand.

Only districts with bodies receive these particular flow variables; rootless districts still need the separator logic. Sequentially contracting a **disconnected union** into one body does not prove connectivity of the original district.

### C12 — **Verified**, for its stated fixed-body model

**Code:** `tools/exp/contig/draw.py:557`:  
`budget = hi - fixed_mass[j] + MASS_TOL * max(1.0, hi)`

**Proof:** If a feasible connected district owns \(z\), it contains a root–\(z\) path. With nonnegative masses and already-counted body masses set to zero on the contracted path, the cheapest path costs no more than the district’s total free mass, which is at most \(hi-F_j\).

Without a root, a connected selected set lies in one allowed component. If that entire component has insufficient mass, no subset can satisfy the lower bound.

This does not validate the fixed supports, omitted bodies, or sequential decomposition themselves.

### C13 — **Verified**

**Code:** `tools/exp/contig/draw.py:85`:  
`LAND_WEIGHT = SHAPE_SCALE   # the land term's (#133) most per group, below one split`

The relevant objective variation can reach \(900+900+9=1809\), exceeding the 1000 charge for an additional holder. Consequently the scalar objective does not encode strict holder-first lexicography.

The border term includes a constant-offset implementation through negative own-body credits; its **range**, rather than its raw signed value, is what matters to this argument.

### C14 — **Falsified under current M1**

**Code:** `tools/exp/contig/repair.py:211`:  
`_NECKS[key] = (m, ng, audit.district_necks(set(zips), m, ng))`

No `free=` relay set is supplied. Cut-edge enumeration also omits width-only neighbors:

`tools/exp/contig/repair.py:216`:  
`return set(ng.border.get(z, ())) | ng.connector.get(z, set())`

**Counterexample:** District \(X=\{a,b\}\) has equal land on its two vertices and a 1 km polygon edge. A zero-opportunity vertex \(r\), owned elsewhere, connects to both through 20 km borders. Current M1 admits \(r\) as a relay; separating \(a\) from \(b\) costs at least 21 km. The repair check without \(r\) finds a 1 km neck. Its retained-anchor row requires at least 10 km of owned boundary and rejects this current-M1-feasible district.

The old connected-anchor argument remains useful only with its width and connectivity assumptions. Fixing connector widths alone does not restore the claim.

### C15 — **Weakened: theorem verified; implementation does not establish its premise**

If \(D_c(S,\delta)\) is genuinely empty under the **same current M1 definition**, no qualifying map can contain a district with footprint \(S\): that district would itself belong to \(D_c(S,\delta)\).

However:

**Code:** `tools/exp/contig/plancheck.py:140`:  
`nks = audit.district_necks(set(X), m, ng)`

This omits relays. The wide-passage model likewise omits some width edges:

`tools/exp/contig/plancheck.py:360`:  
`for y in set(ng.border.get(z, ())) | ng.connector.get(z, set()):`

The C14 construction can therefore produce a false current-M1 infeasibility verdict even for an all-held support. Proposition B cannot justify that resulting ban.

### C16 — **Weakened**

Without opened units, the cap bounds the **aggregate** split-unit count and holder count over window units; the latter bounds aggregate cuts because the units remain covered.

**Code:** `tools/exp/contig/draw.py:1004`:  
`row(-inf, float(splits + extra), [scol[v] for v in vs], [1.0] * len(vs))`

But:

`tools/exp/contig/draw.py:1000`:  
`groups = [(list(scol), len(opened))]`

Opened units explicitly receive additional allowance. The pipeline can also retry without the cap. Thus this is not an unconditional guarantee of “a window repair,” nor a guarantee that each individual unit’s split count never increases.

### C17 — **Weakened**

The inclusion is valid when sealing adds only region restrictions while keeping **physical dollar bounds and all other parameters unchanged**, and each regional support belongs to the unsealed family.

**Code:** `td/supports.py:227`:  
`found = set() if cs.listed_only else set(connected_sets(ch.units, touch, cap, ok))`

**Proof:** Unite regional solutions; counts sum, each unit’s coverage remains one, and every unchanged per-support row holds.

“Same band” alone is insufficient: changed η, margins, modes, support caps, bans, or centroids can invalidate inclusion. Equal relative bands around different regional/global \(\tau\) are not equal physical bands.

### C18 — **Weakened**

The component-allocation condition is necessary on the **actual channel-footprint graph**, including its zero-opportunity territory:
\[
k_i\in\mathbb Z_{\ge1},\quad \sum_i k_i=K,\quad k_iL\le M_i\le k_iU.
\]

**Code:** `tools/exp/region_arith.py:215`:  
`ks = [j for j in range(1, k + 1) if lo - EPS <= m / j <= hi + EPS]`

A connected district cannot occupy two footprint components, proving necessity.

But the older arithmetic uses components of the supplied positive-mass unit dictionary:

`tools/exp/split_floor.py:163`:  
`comps = sorted(components(M, unit_adj), key=lambda c: -sum(M[u] for u in c))`

Dropping a zero-mass connecting unit can create artificial components. Also, that script’s legacy graph construction and symmetric-band calculation are not automatically current-M1/window bounds.

### C19 — **Verified at the reported precision**

The three inspected `merged/dollars.csv` files give FI_04 = 1030.828 and FI_05 = 1034.556, with CA/OR/WA appearing in no other FI district. Their reported total is 2065.384.

Thus, conditional on this closed two-district block,
\[
d_1,d_2\in[2065.384-1035,\;1035]
=[1030.384,\;1035].
\]
One district exceeds the upper bound; three require at least \(3(765)=2295\).

**Code:** `tools/looks/score.py:312`:  
`out[r["district"]] += float(r["m_rel"]) * rates[r["current_channel"]]`

The note’s 1030.4 lower endpoint is rounded. This is a **conditional block result**, not a reason national geography must retain that block.

### C20 — **Falsified**

NC’s FI mass is a whole-state quantity in these maps. Florida’s quoted national quantity is not.

**Code:** `tools/looks/score.py:327`:  
`states[r["model_channel"], r["district"]].add(r["state"])`

**Counterexample from the cited map:**

`runs/exp/national_2026-10-14/warm/ne-cmp-tierP/merged/dollars.csv:36`:  
`national,national_01,1013.994,1000.000,1437.500,,AL;FL;GA;SC,0,0,1`

The same file’s line 44 is:  
`national,national_09,1004.094,1000.000,1437.500,,FL,0,0,1`

Two national districts own Florida. The 1004.094 value is **part of Florida**, selected by the drawing. In ne-48-bal, the whole-state Florida national district is 1370.399. “FL alone” describes a district’s footprint, not ownership of all Florida.

### C21 — **Verified as saved-output facts**

I inspected all three dollar tables and `merged/m1.json` files. They record all districts in their applicable windows, gap-width passes, strict passes for ne-48-bal and ne-cmp-tierP, and two strict necks for ne-50-filight.

**Code:** `tools/looks/score.py:337`:  
`inside = lo is not None and round(lo) <= round(x) <= round(hi)`

**Scope:** These are verified saved reports, not fresh gates or independent checks against the original extract. The WIFI whole-state allowance is necessary for WIFI_03.

### C22 — **Verified from the saved state-incidence tables**

Reconstructing channel-specific state holder counts from the three dollar tables gives exactly the listed violations:

- ne-48-bal: none;
- ne-50-filight: national_09 NY/PA; WH_06 NJ/PA; FI_18 OH/PA;
- ne-cmp-tierP: WH_06 NJ/PA; FI_18 OH/PA.

**Code:** `tools/looks/score.py:326`:  
`owners[r["model_channel"], r["state"]].add(r["district"])`

The scorer’s state incidence includes zero-opportunity ownership. I checked these tables rather than independently aggregating their large ledgers.

### C23 — **Verified for the named run reports**

The ne-48-bal reports give FI 0.423 s, WH 0.015 s, national 0.020 s, WIFI 0.002 s.

**Code:** `td/master.py:212`:  
`"mip_rel_gap": self.mip_rel_gap, "time_s": round(self.time_s, 3)}`

These are engine solve times, not end-to-end planning times including geography loading and support construction. They do not establish the same bound for every grid point.

### C24 — **Not verifiable**

`m5-studio/window-band:tools/exp/contig/glue.py` and the corresponding branch-only implementation are **not verifiable by me**; no matching local file is present.

The guarantee would require inspecting the move predicate, donor comparison, handling of unresolved neck checks, and final positive-mass ownership assertion. A final passing gate does not independently prove the stronger “no donor failure ever grows” invariant.

### C25 — **Verified for joint-mode P/band feasibility; qualified for objectives**

**Code:** `tools/exp/contig/draw.py:349`:  
`parent[find(qi)] = find(first[j])`

The grouping joins free components whenever they share an allowed district. Therefore no free variable or participating district crosses final groups; fixed-body masses are constants. P and mass feasibility factor accordingly.

Optimality also factors for the objective actually assembled as a sum of group objectives. It does not establish equivalence to an independently specified map-wide objective: normalization and any cross-group unit/land terms must match. The claim does not cover sequential mode or an arbitrary new shape objective.

### C26 — **Verified**

**Code:** `tools/exp/contig/draw.py:1119`:  
`tol = 1e-7 * max(1.0, hi)`

At \(hi=1035\) in $M, this is \(0.0001035\) $M = **$103.50**. The start validator applies that tolerance to its stored rows, so it can accept a band-row excess of that size.

That numerical acceptance is not the whole-dollar gate’s acceptance and is not a new permissible balance tolerance.

### C27 — **Weakened**

The inspected w1 and nw49 2026-10-13 specs omit `margin`; the local bases and launcher support the analogous inference for west8 and nw34 WIFI.

**Code:** `td/spec.py:369`:  
`margin = c.get("margin", True)`

The ne_plains base explicitly disables it; inspected 2026-10-14 ne-48-bal copies do too.

However, `margin=true` does not imply \(\mu_S>0\) for **every support**—all-whole supports have zero margin. I did not inspect every generated 2026-10-14 spec, and the branch-only driver writing them is **not verifiable by me**.

## 3. Additional mathematical and evidentiary problems

### 3.1 The current neck-model mismatch has three separate causes

**Verified source facts:**

1. Old connector widths: `repair.py:230`:  
   `km += 0.0 if ng.land_would_do(u, v, states) else NECK_KM`
2. Missing zero-opportunity relays: `repair.py:211` and `plancheck.py:140`, quoted above.
3. Missing width-only adjacency in cut/flow construction: `repair.py:216` and `plancheck.py:360`, quoted above.

`wholeplan.py` shares the relay omission:

`tools/exp/contig/wholeplan.py:76`:  
`necks = audit.district_necks(set(zips), mass, ng, time_limit)`

**Mathematical consequence:** An infeasibility proof for these stricter models is not a proof for current M1. A fixed-support ban based on such a proof can remove a feasible district.

The old NeckCut lemma is defensible when both anchor sets remain connected, their areas force qualifying parts, and the cut’s counted capacities dominate the relevant gate capacities. The present implementation does not establish those hypotheses. The two distinct graphs—own-connectivity and augmented width—must not be conflated.

### 3.2 The highlighted first-attempt failures did not necessarily reach the complete model

**Verified:** The ne-48-bal FI/PA record has `dag=true`, zero separator cuts, and only one attempted solve:

`runs/exp/national_2026-10-14/main/ne-48-bal/rest-FI-WH-national/draw/contig.json:164`:  
`"dag": true,`

The same group records 4340.76 seconds and `unknown`. The ne-50-bal FI/FL record has the same restricted-only pattern.

The execution order is explicit:

`tools/exp/contig/draw.py:409`:  
`for dag in (True, False):`

In sequential mode a connected restricted result can bypass the complete solve:

`tools/exp/contig/draw.py:410`:  
`if not dag and not prove and out is not None and out.status == "connected":`

**Correction:** The evidenced bottleneck is the **implemented restricted-first drawing pipeline**. These records do not isolate the difficulty of the unrestricted separator formulation, much less prove the ZIP assignment infeasible.

### 3.3 “Fully exact passing map” confuses master optimality with drawing provenance

**Verified:** The run-folder tier comes from the master report:

`tools/exp/contig/run.py:475`:  
`"tier": audit.tier(reports[c]), "status": reports[c]["status"],`

The older supposedly fully exact map retains:

`runs/exp/sealed_2026-10-14/main_unsealed/ne-48-bal-r2/contig.json:355`:  
`"undrawn_zctas": 6475,`

and at line 1933:

`"undrawn_zctas": 5618,`

These are inherited **source** undrawn counts for FI and national; subsequent repair may have redrawn some of that territory. They nevertheless invalidate using `run.json`’s exact tier to assert zero heuristic provenance.

There are three different certificates:

- master optimality;
- group/window optimality with other ownership fixed;
- final-map feasibility under the gate.

None implies the others automatically. No national ZIP-map global optimum is established here.

### 3.4 The run-folder M1 gate does not itself verify routing

**Verified:** `score.m1_check` constructs an audit run without scenario routing:

`tools/looks/score.py:406`:  
`polygon=g.polygon, fine=None if fine is None else tuple(fine)),`

The actual construction is at lines 405–407. Its docstring explicitly delegates routing to the source run’s audit.

By contrast, the source audit supplies routing:

`td/output.py:430`:  
`route = {(u, f): c.name for c in s.channels.values() for u, fs in c.domain.items() for f in fs}`

**Consequence:** “The final gate proves P, N, coverage, and correct scenario routing” is too strong when “gate” means only `tools/mandates/check.py::m1`. The certification chain must include the matching source audit and immutable scenario/mass inputs.

### 3.5 IFA repair uses an intersection, not generally the entire dollar window

**Verified:**

`tools/exp/contig/repair.py:1133`:  
`ch.final_band = (max(ch.final_band[0], w_lo), min(ch.final_band[1], w_hi))`

Thus the local implementation enforces
\[
[\tau(1-\delta),\tau(1+\delta)]\cap[L,U],
\]
not automatically \([L,U]\).

For example, \(\tau=1200,\delta=.15\) gives \([1020,1380]\), strictly smaller than the national/IFA dollar window.

This intersection can still be substantially wider than the maximal symmetric interval fitted inside the window. That distinction is real; the note’s “absolute window in repair” inference is not exact. Any different IFA-branch implementation is **not verifiable by me**.

### 3.6 Per-channel feasibility separates; the present merge restriction does not generalize

**Verified mathematical deduction:** With domains and K fixed, distinct planning channels partition different fine-channel cells. Their district partitions may occupy the same physical ZCTA without conflicting. There is no shared resource constraint between them.

The merge tool instead requires ZIP-disjoint sources:

`tools/exp/contig/merge.py:87`:  
`if z in seen:`

It then raises an overlap error.

Consequently, equal-or-disjoint regional state sets are an implementation requirement of that assembly path, not a theorem about national feasibility. A channel-specific regional partition can lose feasibility through its own seals; merely overlapping another channel’s geography does not cause that loss.

**Objective qualification:** Independent channel feasibility does not automatically establish independent optimization of an arbitrary map-level shape preference. Additive or otherwise suitably separable objective structure must be specified.

### 3.7 Fixed supports remove geographic options; planned edge masses are not fixed drawing targets

The arm-1 model limits allowed holders and fixes singly held units. Those restrictions can exclude feasible national maps.

However, the note overstates the effect of edge-valued planned masses. The ordinary draw does not generally enforce those exact targets:

`tools/exp/contig/draw.py:1015`:  
`if fixed_targets:`

Planned totals also guide the construction heuristic:

`tools/exp/contig/draw.py:1118`:  
`target = {cp.name: cp.total for cp in plan.copies}`

**Verified:** Master balance indifference can select edge-valued plans; fixed supports can create a genuinely tight block such as FI CA/OR/WA.

**Inferred, not established:** The edge-valued shares themselves cause exact-draw infeasibility or runtime. The draw can redistribute within its allowed supports, and some tightness comes from the support’s closed mass block rather than target equality.

### 3.8 Several claimed “bounds” require tighter domain statements

- **Policy bans:** They restrict the feasible set; an infeasible restricted model is not a national infeasibility proof.
- **Positive η:** It excludes districts using arbitrarily small positive shares or zero-only territory in a touched state.
- **Dropped zero-mass units:** They can invalidate component-based geographic lower bounds if they connect otherwise separate positive-mass regions.
- **WIFI:** Applying 1150 to every district excludes legal whole-state districts. Applying 1600 to every district is a relaxation, not the exact conditional rule.
- **Diameter objective:** Its optimal value is not a lower bound on the number of split states. A split-count certificate requires an appropriate bound objective or separate valid arithmetic bound.

The note’s warning about restricted certificate domains is correct. Its statement that an η-free bound is mathematically necessary for **every** scoped equality certificate is too broad: equality with a valid lower bound can certify a minimum inside a precisely declared domain. The owner’s stronger requirement remains decisive for an unqualified “minimal” or “must split” claim about M1 maps.

### 3.9 Coarsening preserves P but can remove feasible ZIP partitions

**Verified:**

`tools/exp/contig/coarse.py:95`:  
`for i, comp in enumerate(sorted(components(zs, adj), key=len, reverse=True)):`

Each coarse unit is connected; adjacent coarse units share actual ZIP edges. Therefore a connected coarse district expands to a P-connected ZIP set.

But this is a restriction. Four unit-mass ZIPs on a path can form two mass-2 districts. If the first three ZIPs are contracted into one indivisible unit, the same K=2, exact-mass-2 problem becomes infeasible.

No coarse-unit contiguity theorem eliminates neck checking. The optional thin-land row is not equivalent to the owner’s connected-side neck definition.

Also, `coarse.py`’s current geographic loader is NY-specific:

`tools/exp/contig/coarse.py:31`:  
`FIPS = {"NY": "36"}`

The generic partition MILP and a national-ready geographic tool are different claims.

### 3.10 `rulec_enum.py` is not a complete divisible-mass relaxation of rule C

**Verified:**

`tools/exp/contig/rulec_enum.py:36`:  
`for n in range(2, 8):`

It also assigns entire connected components of the remaining states to districts and uses a positive \(10^{-6}\) floor.

**Counterexample:** Normalize \(L=1,U=1.4375\). Let split state \(\sigma\) have mass .8, and adjacent whole states A and B each have mass .7. Suppose \(\sigma\), A, B form a triangle in the state graph. A rule-C solution gives .4 of \(\sigma\) to A and .4 to B: two districts of mass 1.1.

The enumerator treats connected A+B as one indivisible attachment component. The other district must then obtain mass at least 1 entirely from \(\sigma\), which is impossible. It misses a valid divisible rule-C configuration.

The interval-sum test is valid for its **fixed attachment masses**, not a completeness theorem for all rule-C arrangements.

### 3.11 The finite-library model has no automatic global certificate

The coverage and district-count equations are sound if each pattern partitions its split state and uses disjoint whole-state attachments. With fixed full-graph M1 inputs, their assembly preserves local district feasibility.

But:

- A restricted-library minimization supplies a feasible solution/upper bound, not an all-map lower bound.
- Heuristic pricing does not certify that no improving column exists.
- Exact reduced cost includes the district-count dual:
  \[
  \bar c_p=c_p-\sum_{v\in\sigma(p)\cup A(p)}\pi_v-k_p\theta,
  \]
  plus contributions from any other active master rows—not coverage duals alone.
- Rule C is an additional restriction, not established as necessary.
- The old shape filters and splits-first objective are not the current owner’s formulation.

The draft’s pricing sentence is in `docs/archive/lenses/review-2026-10-07/METHOD-carve-first.md`; no implementation establishes completeness.

### 3.12 Exact transport theorems do not apply verbatim to the floating-point implementation

The ideal forest and tree-rounding proofs are sound. The actual transport code drops tiny **positive** ZIPs:

`td/realize.py:160`:  
`tiny = [z for z in zs if m[z] < FLOW_TOL * scale]`

It adjusts one target and later places those ZIPs outside the transport solution.

A simple example has two mass-1 ZIPs and a tiny \(\varepsilon\)-mass ZIP, with targets \(1\) and \(1+\varepsilon\). Dropping the tiny ZIP can leave an unsplit transport solution; placing it with the other district changes a district’s mass despite that district touching no split transport ZIP.

Thus “no split ZIP implies exactly its planned mass” belongs to the ideal LP theorem, not necessarily the complete numerical implementation. This does not demonstrate a material observed error; it qualifies the claimed exact guarantee.

### 3.13 Local and numerical optimality claims are overstated

**Hess:** A no-incumbent solve returns the previous assignment:

`tools/exp81/hess.py:440`:  
`return start, steps`

The outer loop then tests:

`tools/exp81/hess.py:554`:  
`repeats = new == assign`

So “assignment repeats” can mean “the solve made no progress,” not coordinatewise optimality. A coordinatewise certificate requires an optimal fixed-centre solve followed by unchanged assignment/centroids.

**Drawing:** The final absolute gap is nonzero:

`tools/exp/contig/draw.py:89`:  
`FINAL_ABS_GAP = 1e-6        # then mip_rel_gap = 0 and this absolute gap (trap 12)`

“Optimal” is numerical optimality for the specified group model, not a symbolic exact optimum.

**Coarse border objective:** Adding \(10^{-3}\) per cut adjacency is a weighted secondary term, not necessarily a strict lexicographic tie-break. A sufficiently small border-length difference can be traded against cut count.

**Complexity:** A compact flow formulation can be exact without being easy. Finite cut-loop termination does not imply polynomial time; heuristic/library generation does not imply exhaustive search.

## 4. A single mathematical statement of the national problem

This is a **reference program**, not a proposed solution algorithm.

The settled rulings determine the feasible set and priority order. They do **not** uniquely specify a numerical shape or within-window balance objective. Those objective evaluators must therefore be explicit input parameters; silently substituting the present splits-first scorer would change the problem.

### 4.1 Input sets and data

- \(V\): the explicitly shipped 2025 CONUS ZCTAs.
- \(F\): the scenario’s fine channels.
- \(\mathcal H\): the permitted routing structures. For a fixed structure, take \(|\mathcal H|=1\); the five tested structures are not assumed exhaustive.
- For structure \(h\), planning channels \(C_h\) and routing
  \(\rho_h:V\times F\to C_h\), respecting the settled national/fallback rules.
- \(V_{hc}=\{z:\rho_h(z,f)=c\text{ for some }f\}\).
- Dollar masses
  \[
  d_{hcz}=\sum_{f:\rho_h(z,f)=c}r_fm_{zf},
  \]
  with \(r_f\) fixed from the **whole extract**, not recalculated after regional extraction.
- Land areas \(a_z\), state labels \(s(z)\), the committed P-adjacency graph, and current #140 width data.
- Static zero set \(Z^0_{hc}=\{z\in V_{hc}:d_{hcz}=0\}\).
- District dollar windows:
  national \([1000,1437.5]\), WH \([850,1150]\), FI \([765,1035]\), WIFI \([850,1150]\), in $M; whole-state WIFI cap 1600.
- A fixed record of the authorized Manhattan exception, not an exemption for every district that merely touches Manhattan.
- Numerical map evaluators \(\Phi_{\rm shape}(\lambda)\) and \(\Phi_{\rm balance}(\lambda)\), consistent with the owner’s preferences.

### 4.2 Variables

For each \(h,c\), allow district labels \(j=1,\ldots,54\):

- \(q_h\in\{0,1\}\): chosen routing structure.
- \(y_{hcj}\in\{0,1\}\): active district.
- \(x_{hcjz}\in\{0,1\}\): ZCTA ownership.
- \(b_{hcjs}\in\{0,1\}\): district touches state \(s\).
- \(w_{hcj}\in\{0,1\}\): eligibility to use the whole-state WIFI cap.
- Root binaries \(r_{hcjz}\) and nonnegative connectivity flows \(f_{hcj,uv}\).
- Split indicators \(p_{hcs}\in\{0,1\}\).

Write \(X_{hcj}=\{z:x_{hcjz}=1\}\).

### 4.3 Routing, coverage, and K

\[
\sum_hq_h=1,\qquad y_{hcj}\le q_h,
\]
\[
\sum_jx_{hcjz}=q_h\quad(z\in V_{hc}),
\]
\[
x_{hcjz}\le y_{hcj},\qquad
\sum_zx_{hcjz}\ge y_{hcj}.
\]

Let \(K_{hc}=\sum_jy_{hcj}\). Require
\[
K_{hc}\ge q_h,\qquad
48\le\sum_{h,c}K_{hc}\le54.
\]

The ledger assigns every \((z,f)\) to the district owning \(z\) in \(\rho_h(z,f)\). Therefore fine channels routed to one planning channel have one common ZCTA owner.

### 4.4 Hard dollar windows, including WIFI’s conditional cap

Let
\[
D_{hcj}=\sum_zd_{hcz}x_{hcjz}.
\]

Use exact dollars for the conceptual interval, or the explicitly specified whole-dollar rounding function when reproducing the scorer. Do not introduce solver feasibility tolerances as policy.

For channels other than WIFI:
\[
L_cy_{hcj}\le D_{hcj}\le U_cy_{hcj}.
\]

For WIFI:
\[
850y_{hcj}\le D_{hcj}\le1150y_{hcj}+450w_{hcj}.
\]

State incidence is exact:
\[
x_{hcjz}\le b_{hcj,s(z)},\qquad
b_{hcjs}\le\sum_{z\in V_{hc}:s(z)=s}x_{hcjz}.
\]

Allow the cap only for whole-state districts:
\[
w_{hcj}\le y_{hcj},
\]
\[
x_{hcjz}\ge w_{hcj}+b_{hcj,s(z)}-1.
\]

Thus, if \(w=1\), every touched state’s channel-footprint ZCTAs belong to that district. Coverage makes this equivalent to exclusive ownership of each touched state.

### 4.5 Hard P-connectivity

On the graph induced by \(V_{hc}\), let \(n=|V_{hc}|\). For each district:
\[
\sum_zr_{hcjz}=y_{hcj},\qquad r_{hcjz}\le x_{hcjz},
\]
\[
0\le f_{hcj,uv}\le(n-1)x_{hcju},\qquad
f_{hcj,uv}\le(n-1)x_{hcjv},
\]
\[
\sum_uf_{hcj,uz}-\sum_vf_{hcj,zv}
\ge x_{hcjz}-nr_{hcjz}.
\]

A rootless selected component contradicts the sum of its flow inequalities. Conversely, a spanning-tree flow satisfies them for every connected district.

This uses actual P-adjacency, not relay paths. Current shipped R5 land-gap adjacency is empty; any subsequently committed R5 data must enter this graph consistently.

### 4.6 Hard N-connectivity

For any candidate \(X\), construct its width graph \(H_{hc}(X)\) using:

- all of \(X\);
- the static zero-opportunity relays reachable from \(X\);
- current polygon, connector, and gap widths;
- no area contribution from relays outside \(X\).

For every nonempty proper \(A\subset X\) connected on the district’s **own P-graph**, with
\[
.05\,a(X)\le a(A)\le .5\,a(X),
\]
require
\[
\min_{T\subseteq R_{hc}(X)}
\operatorname{cap}_{H_{hc}(X)}
\bigl(\delta(A\cup T)\bigr)\ge W,
\]
except precisely the authorized Manhattan violation. \(W=10\) km, or \(1{,}000{,}000\) cm in the gate’s integer-width representation.

This is a finite constraint system. An explicit equivalent binary encoding can predefine the collection \(\mathcal B_{hc}\) of nonexempt neck-failing sets and impose, for every \(B\in\mathcal B_{hc}\),
\[
\sum_{z\in B}(1-x_{hcjz})
+\sum_{z\in V_{hc}\setminus B}x_{hcjz}
\ge y_{hcj}.
\]

This excludes exactly the forbidden ownership sets. Its potentially exponential size is not a tractability claim. A timeout in an attempted neck certification is **unknown**, not a mathematical violation or feasibility proof.

### 4.7 Splits and objective

Let \(R_{hcs}=\sum_jb_{hcjs}\). Enforce
\[
2p_{hcs}\le R_{hcs},\qquad
R_{hcs}\le q_h+53p_{hcs}.
\]
Then \(p_{hcs}=1\) exactly when at least two districts own territory in that channel-state.

The objective is
\[
\boxed{
\operatorname{lexmin}
\left(
\Phi_{\rm shape}(\lambda),
\Phi_{\rm balance}(\lambda),
\sum_{h,c,s}p_{hcs}
\right)
}
\]
subject to all hard constraints above.

Contiguity and the dollar window are feasibility requirements, not penalty terms. Shape has no hard gate. K moves inside the permitted total range.

### 4.8 Differences from the note’s §0

The reference problem:

- optimizes K rather than treating one sampled K vector as the problem;
- makes WIFI’s allowance conditional on actual ownership;
- includes correct routing, not merely a ledger-derived channel label;
- fixes full-graph relay information independently of regional solves;
- makes all ZCTAs—including zero-opportunity territory—assignment variables;
- contains no automatic η, free-list, support-size, diameter, sealing, rule-C, or split-cap restriction;
- distinguishes hard feasibility from shape/balance/split priorities;
- distinguishes the owner’s mathematical requirements from numerical solver and audit statuses.

Those additional restrictions may define experiments, but they are not consequences of the national problem.

## 5. Why national fails more often while IFA succeeds

### Verified observations

1. **National is not established infeasible.** The three inspected warm-start output packages record current-rule M1 and dollar-window passes.

2. **The previous planning failures were failures of restricted models.** Symmetric fitted bands, margins, support families, split lists, and distance limits all constrain those models. The later grid also omitted west8 and altered some policies, so 20/21 versus 15/15 is not a controlled one-variable comparison.

3. **Some difficult national groups spend their budget in the DAG restriction.** PA and FL provide direct examples; subsequent groups can remain unattempted. A whole undrawn NY group therefore does not establish that an exact NY solve itself timed out.

4. **Fixed attachments matter.** The PA example has four districts demanding compatible assignments around fixed whole-state bodies. The master contains no ZIP ownership geometry establishing those attachments can coexist.

5. **IFA uses connected coarsening and regional reuse.** `coarse.py` supplies a valid P-preserving contraction. The ladder reuses substantial geography rather than supplying seven independent national-scale solutions.

6. **Some blocks have little dollar flexibility.** The closed FI CA/OR/WA block is forced near its upper edge. This is not true of the falsely identified whole-state Florida example.

7. **The reported IFA passes incorporate the authorized Manhattan exception.** The national candidates inspected do not need that exception.

8. **Neither map’s solver tier establishes globally optimal shape or ZIP ownership.** The existing rank key is still splits-first:

   `tools/looks/score.py:550`:  
   `return (s["splits"], s["defects"], s["largest_extent_km"], s["states_per_district"], s["worst_dev"],`

   It therefore does not implement the supplied current priority order.

### Inferred explanations—not established causes

- IFA’s smaller, deliberately chosen regions and connected coarse units plausibly reduce binary assignment complexity and awkward competing attachments.
- National’s fixed support choices plausibly create more difficult geographic competition within split states.
- Unequal iteration effort and reuse plausibly explain part of the success-rate difference.
- Current neck-model mismatches may reject useful national repairs, but their contribution to the measured runtime/failure rate has not been quantified.
- Restricted-first scheduling plausibly contributes materially to the observed draw bottleneck; the logs do not quantify how an otherwise matched unrestricted solve would perform.

**Not supported:** “Four channels inherently prevent sealing,” “the whole national problem has no feasible solution,” “the unrestricted exact ZIP formulation cannot solve these groups,” or “the old passing map was drawn entirely by exact optimization.”

## Strongest case against this recommendation—and what would change it

The note already discloses many restrictions, preserves timeout-versus-infeasibility distinctions in several places, and correctly identifies the planning/drawing disconnect. Its principal experimental history should not be discarded because some certificate language is wrong.

What would change my recommendation is a version-pinned revision that supplies the unavailable implementations, aligns every feasibility-separating check with current M1, corrects C20 and drawing provenance, and distinguishes restricted-only logs from complete-model solves. Matched experiments would then be needed to elevate the proposed causal explanations into verified conclusions.

## Implications for the next formulation

The evidence favors treating ZIP ownership, current M1, and actual dollar windows as the reference feasible set, with every support, regional, or coarse restriction explicitly identified. Preserve channel separation where its assumptions hold, but do not inherit the merge tool’s ZIP-disjoint limitation as mathematics. Any claimed lower bound must cover the maps being compared, and any local rejection must be valid under the current gate. The next comparison should measure actual drawing stages and use the settled shape-before-balance-before-splits order, rather than master tiers or historical ranking as proxies.

Agent: oracle (openai-codex/gpt-6-astra, max)