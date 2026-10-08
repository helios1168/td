ADOPT WITH CHANGES

Adopt an **incremental library of validated district patterns**, not an exhaustive carve-everything-first phase. This removes the least productive dependency in v2: waiting for a hard infeasibility proof before trying another arrangement. It does not make carving easy or prove that a finite library contains a usable map. Start with witnesses, solve a small selector, and generate the missing alternatives on demand.

Read-only review; no solver benchmarks run. Size estimates below are planning estimates, not measurements. No external paper is relied on; the formulation and pricing arguments are derived here. `Method` means `/tmp/iss/acb/review/METHOD-carve-first.md`; `Consolidated` means the adjacent `CONSOLIDATED.md`.

## 1. Soundness

### Coverage, K and rule C: correct with explicit admission rules

The selection rows in Method:34–39 work if:

- `x_g, y_p ∈ {0,1}`;
- a whole column contains one district owning **all** territorial ZCTAs of every state it covers;
- a pattern has **k_p ≥ 2 nonempty pieces**, partitions every territorial ZCTA of its root state σ exactly once, and contains all k_p resulting districts;
- its attach sets are pairwise disjoint, exclude σ, and contribute their complete territorial ZCTA sets;
- columns belong to one identified planning channel/footprint and share the same frozen data and policy context.

A one-piece pattern is a whole column, not a split. Otherwise `Σy_p` overcounts split states. Dropped/zero-opportunity states must remain in the territorial inventory; positive-mass coverage alone is insufficient.

**Rule C follows from selection, not a free-state filter.** An attach state may be a splitting candidate in other patterns. Selecting this pattern covers it, so its coverage row prevents selecting any other pattern that splits or owns it. Every selected district then has at most one actually split state. Do not reject attach states merely because they are candidates to split.

The separate “at most one pattern per σ” row is redundant; omit it. State coverage already implies it. K is exactly `Σx_g + Σk_p y_p` provided district IDs are globally unique after assembly.

**Short proof:** selected column state sets are disjoint and exhaustive. Within a pattern, root pieces partition their state and attach states have one owner. Thus the selected districts partition every required ZCTA. A root state contributes one split and k_p−1 cuts; other covered states contribute neither. Conversely, any rule-C map can be grouped into one pattern for each split state plus its wholly owned attachments, with remaining districts as whole columns—if the complete corresponding pattern universe and support policies are allowed. A finite generated library is only a restriction of that universe.

### Does every passed column imply an M1-clean assembled map?

**Yes, for an integral cover assembled without changing any validated district.** M1 depends on each district's own ZCTA union, graph, land areas and connector interpretation—not on its neighbours' district names (`td/audit.py:565–617`). Selection changes which districts coexist, not those inputs.

Required safeguards:

> Every district, including all zero-opportunity territory and attach components, passes the unchanged full-union gate before admission. No unresolved gate result is admitted. Assembly only namespaces IDs and routes fine-channel cells; it performs no fill, repair, boundary move or merging of districts. Re-run full ownership/routing/K/dollar/M1 audit on the assembled ledger. Any mismatch invalidates that output and is an integration error, not a support ban.

No repair is needed after correct assembly. Carving/repair heuristics may still be used **inside pattern generation** before admission.

### Objective: first two terms correct; remaining terms underspecified

Method:40–41 correctly counts splits and cuts under the admission rules above. Complete the remaining objective using actual scorer metrics, not proxies:

1. minimise splits; pin the achieved optimum when proved;
2. minimise cuts; pin;
3. minimise additive visual-defect count;
4. minimise maximum district extent, then maximum states per district;
5. minimise worst target-relative deviation, then mean deviation.

For column c with districts j, let `D_c=max_j d_j`, where `d_j=|USD_j/T−1|`; WIFI uses its approved dollar mean. Then `B ≥ D_c z_c` represents worst deviation. Mean is `Σ_c z_c Σ_j d_j / K`, not the mean of column averages: a four-district pattern must weigh four times a whole column. Extent and states-per-district similarly need maxima/epigraphs, not sums. Border length may guide carving; it does not replace these rank keys.

Some looks coefficients still depend on K: current small-piece/crowding diagnostics use τ (`tools/looks/score.py:210–228`). Recompute them for each K even when geometry and dollar eligibility are reusable. Retain the settled REVIEW alternative with an extra split; one strictly lexicographic optimum alone will not produce that shortlist alternative.

For the main map, use a joint selector for a fixed national/WH/FI/WIFI K combination, with coverage rows indexed by `(channel,state)`. Independently choosing each channel's lexicographic winner can miss the main-map winner: a channel may accept slightly greater extent without changing the main map's maximum, while improving its later balance key. Alternatively retain sufficient channel alternatives; do not claim global ranking from one winner per channel.

### Certificates: equality argument valid, draft domain claim too broad

Method:43 says #103 bounds “every C-rule plan.” Not automatically. Its η, modes, caps, support family, zero-mass treatment, rates and explicit bands still delimit the bound (`docs/MODEL.md:298–334`; `docs/problem/PROBLEM.md:58–61`). A library pattern can be M1-valid yet outside that class.

Replace Method:42–46,66–67 with:

> Record the certified lower bound L and its complete domain D. Validate the selected ledger's read-back against D. If covered, `L ≤ optimum_D ≤ s_drawn`, and `g=s_drawn−L`. Equality certifies attainment of that domain's split lower bound. No optimal library solve is needed for this sandwich argument: an audited feasible incumbent suffices. If coverage or certification is missing, report `not covered` or `unknown`, not a numeric certificate gap.

> “Best over the library” requires a proved optimal library solve; otherwise say “library incumbent.” Library infeasibility proves only that this library has no cover. g is an upper bound on excess splits over the domain optimum, not a measurement of loss caused solely by library incompleteness. Adding columns cannot worsen the exact library optimum, but heuristic pricing need not improve it.

Keep A3's wording restriction: say **“matches the certified [domain] lower bound”**, not unqualified “proved fewest-splits.” An all-M1 claim still needs a covering bound such as #119. Equality for one K also does not certify best over K46–55 or all main-map K combinations.

## 2. Against v2: likely advantages, losses and surviving requirements

**Likely better route to a first clean map; speedup not yet measured.**

- **FI20:** promising pilot. Existing FI20 drawings supply seeds, and validated patterns from different attempts can be recombined instead of discarding an entire plan after one failed state. Existing drawings must be rechecked against dollar bands and rule C; old eligibility is not transferable.
- **IFA46–55:** largest reuse advantage. Under E1/E2 the same dollar-bounded patterns can serve different K values. CT no longer fails the arithmetic screen, but CT+RI, MA's attachments, NY and other crowded states still need actual witnesses. Sparse attachment resources can make individually good patterns mutually incompatible; selection handles that competition.
- **Complete main map:** same benefit within each channel; opportunity/rates differ, so do not share patterns across channels merely because geometry matches. WIFI needs its own dollar-mean band for each K_WIFI. Include its whole-state columns and full audit.

What it loses: completeness of the search, meaningful global infeasibility from an empty/insufficient library, and continuous mass freedom after a pattern is frozen. A pattern bundles all pieces of one state, so pieces from different patterns cannot be mixed casually. Better balance or shape needs a new validated pattern. The expensive work can migrate from proof-search to excessive speculative carving and repeated M1 gates.

**Important change:** do not gate all ~2,000 whole-support candidates and enumerate attach combinations before trying a selector. Mass-filter first; prioritize A's seed plans and missing/valuable states; validate whole columns and patterns lazily. Only validated columns enter the deliverable selector. Keep untested candidates in a separate work queue.

### R1–R13 disposition

| Item | Carve-first effect |
|---|---|
| **R1 dollar adapter** | **Keep.** Same frozen extract rates and explicit E2/E3 bands everywhere. |
| **R2 proof extensions** | **Keep Claim 1/Proposition D for A's bound.** Proposition B and B's infeasibility-relaxation proof are unnecessary on a positive-witness-only path. A short composition proof replaces that feedback obligation. |
| **R3 drawable signature** | **Not required for the main path.** Keep explicit mass/windows in any generator reused; no need to extend drawable-alone solely to manufacture bans. |
| **R4 support/no-good bans** | **Drop from the main path.** A failed union is not admitted; partial-state alternatives remain available. |
| **R5 identity** | **Keep.** Assignment, graph/connectors, rates, policy and gate-version identities protect reused witnesses. |
| **R6 plan search layers** | **Replace** with library growth across root states, piece counts and attach choices. Selector naturally chooses additional splits only if corresponding patterns exist. E4 resource budget is still needed. |
| **R7 balance/ranking/g** | **Keep ranking and correct gap arithmetic.** Mandatory post-selection balance LP/recarve disappears. LP targets can optionally seed new patterns. |
| **R8 audit/render units** | **Keep, but correct its envelope workaround.** See below. |
| **R9 roots/deadlines** | **Keep** distinct heuristic seeds, root choice if a MILP is used, and validated-incumbent timeout handling. |
| **R10 K grid/main combinations** | **Keep.** Reuse dollar-valid columns across K; update K-dependent scores. Restricted-library infeasibility is not grounds to declare the baseline K impossible. |
| **R11 staging/top-three** | **Keep.** First witness/first complete cover before broad expansion. |
| **R12 canonical issue sections/tracking** | **Keep.** Method change does not fix packet mechanics. |
| **R13 zero territory/contract/checkpoints** | **Keep these parts.** List-valued joint-state carving is unnecessary under E2's chosen rule-C track; do not add that generality now. |

**R8 warning:** a symmetric τ-band enclosing the asymmetric target band is only a compatibility envelope. It accepts dollars outside the approved interval, and mixed fine-channel rates prevent treating raw m_rel as dollars. Preserve `ledger.m_rel`; independently construct the exact dollar-band check with correctly weighted cells. A broad-envelope scorecard pass must never stand in for D3/E2/E3 eligibility. Render/scorer/audit must use the same rate snapshot.

## 3. Pricing and library growth

### Exact pricing problem

For the first-pass LP, let π_v be the dual of state v's coverage equality and λ the dual of the K equality. With only those core rows and nonnegative LP variables:

- whole-column reduced cost: `rc(g)=0−Σ_{v∈g}π_v−λ`;
- pattern reduced cost: `rc(p)=1−π_σ−Σ_{v∈A(p)}π_v−λ k_p`.

Method:48–49 omits **K's dual**. That omission can prioritize the wrong piece counts and attachments.

Pattern pricing for σ therefore chooses:

- k≥2;
- a complete disjoint partition of σ's ZCTAs;
- pairwise-disjoint whole attach sets compatible with allowed district supports;
- districts satisfying explicit dollar bands, applicable η/modes/caps and M1;

to minimize the expression above. This is harder than one fixed-attachment carve: attachment selection is part of the problem. In the cuts pass the base cost becomes k−1, and duals of pinned earlier objective rows must also enter reduced cost. Coverage-only prizes are not exact pricing for the full lexicographic model. Start dual guidance on additive splits/cuts stages; handle later maxima explicitly rather than pretending they are additive costs.

### A heuristic pricer is enough for delivery, not certification of completion

Use duals to rank a short list of allowed holder configurations, then call the existing constructive carver. Add gate-passed patterns. Do not build exact pricing or branch-and-price as a prerequisite.

Limits:

- No negative column found by a heuristic proves nothing about missing columns.
- Even exact LP pricing completion would certify an LP statement, not the full integer optimum without further work.
- Zero/positive reduced-cost columns can still matter for integer feasibility or later drawn ranking. Do not reject A-guided candidate patterns solely because LP pricing does not like them.
- Restricted LP may initially be infeasible. Use a clearly labelled Phase-I feasibility LP/artificial columns for guidance, or seed a complete validated cover. Artificial columns can never enter a reported map or M1 pass.

Use A's independent bound for the certificate; do not repurpose the incomplete library LP value as an all-pattern lower bound. Delay dual pricing until simple A-guided growth demonstrates a bottleneck.

### When A's plan cannot be matched

Turn **each complete split-state holder configuration** into a carve request: every singleton copy, every attach set, full band-derived windows, and all state ZCTAs. Equal decoded shares are warm targets, not exact requirements. Test its whole districts too.

Keep every successful pattern even if another state in the same A plan fails. They may combine with patterns from other plans. An unknown request adds neither a pattern nor a ban; record it, try another configuration, and revisit within budget. Request alternative A plans/root states/piece counts as well as floor-attaining plans, or this degenerates back into v2's narrow proposal stream.

## 4. Scale, first measurements and stop rule

### Working size estimates—not exhaustive pattern counts

Historical families contain 1,975 FI supports on low6 and 1,963 IFA supports (`docs/RESULTS.md:991–993`); another layout had 3,903. These are **all support candidates**, not numbers of band-feasible/M1-passed whole columns. The current scenario must be enumerated afresh; `td/supports.py:213–255` applies size/distance/family filters.

| Quantity | FI20 estimate | IFA estimate |
|---|---|---|
| Candidate whole-support family | Order 2,000; allow several thousand if layout/family changes | Order 2,000 under the recorded family |
| After dollar-mass filtering, before M1 | Planning expectation: hundreds; exact count unknown | Planning expectation: tens to hundreds; exact count unknown |
| Initial useful validated patterns | Order 100–500 across roots/attachments | Order 300–1,000 across roots/attachments |
| Core selector rows | At most 49 state rows plus K per channel | 49 state rows plus K |

Pattern estimates describe a **pilot working library**, not guaranteed sufficient coverage or adopted caps. Historical FI20 lists seven split roots (`runs/exp/contig/border/ne_plains_wh11-r2-all/contig.json:281–289`). IFA's stored state masses already put at least thirteen named states above the new U≈1,148.19 m_rel: CA, CT, FL, IL, MA, MI, MN, NJ, NY, OH, PA, TX, WI (`whole127/ifa46-whole/districts.csv`, MA obtained by subtracting RI). Roughly 10–30 varied valid patterns per relevant root, plus optional split roots, motivates the orders above—not a claim about yield.

Complete enumeration is a different scale. With d possible multi-state holders, choosing up to four mutually compatible attachments can already have a combinatorial candidate count; even choosing four out of 49 gives **211,876** combinations before overlap/mass pruning or ZIP partitions. The full pattern universe is not “hundreds.” Do not enumerate its Cartesian product.

A few thousand columns with roughly 50 core rows should be a modest **matrix**, but integer search can still be hard. Gate/carve time is the more plausible first bottleneck. Store root partitions plus attach references, not duplicated full-state geometry in every pattern.

### Measure first

1. Enumerate raw and mass-filtered whole supports; time actual full-union gates, including unknowns and cache hits. Do not extrapolate from solver-only time.
2. Generate the complete **CT two-piece pattern with one RI attachment**, then NY4 and a FI20 seed configuration. Measure attempts, distinct validated patterns and time to first success.
3. Solve a toy exact cover and a library containing a known validated complete cover. Check that selector metrics exactly match assembled scorer metrics.
4. Run FI20 end to end. Record first audited map time, best split/cut/defect vector over time, A's bound, LP/integer gaps, columns/nonzeros, memory and time divided among carving, gating and selection.
5. Reuse the resulting IFA library across K46–55; measure added work rather than rerunning every carve. Then assemble complete main-map candidates.

Compare against a fixed-plan carve attempt on **the same rates, bands, seeds and compute budget**. #124's older timings are warning evidence, not an apples-to-apples speedup benchmark. No need to implement all v2 proof/cut machinery merely to obtain that comparator.

### Stop rule

E4 remains open. Approve explicit wall-time and memory budgets before real search; changing method does not authorize an unbounded library.

If selector reaches its approved time/memory limit—especially when it cannot recover a supplied feasible cover—**freeze library growth**, save the incumbent and solver evidence, and diagnose selection before launching more carves. Deduplicate identical patterns; retain the last working library and all validated witnesses. A bounded active-library restart may be proposed, but dropping columns is a search restriction, not a global infeasibility proof.

If selector quickly proves the current library infeasible, that is a **missing-pattern/compatibility problem**, not evidence that the MILP is too large. Use Phase-I/A-guided growth. If budget expires without an audited cover, return “no map found from this library,” never “no eligible map exists.” No-negative-price or a flat gap is not an exact stopping certificate.

## 5. E2 arithmetic check

Using E1's extract rate `r=1.251968155812553` million dollars per m_rel (`runs/sweep/grid_2026-10-01/tables.json:8`) and IFA's approved bounds [$1,000M,$1,437.5M]:

- `L=1000/r ≈ 798.74236` m_rel;
- `U=1437.5/r ≈ 1148.19214` m_rel;
- CT = 1333.625795626;
- RI = 342.558337;
- `CT+RI−2L ≈ 78.69941` m_rel ≈ **$98.53M**.

Thus **+78.7 m_rel is correct**. CT alone exceeds U; three holders would be short `3L−(CT+RI) ≈ 720.04295` m_rel under the same available-attachment premise.

Writing q for the CT mass assigned to the RI-attached district, the two mass windows intersect at approximately

`456.18402 ≤ q ≤ 534.88344`.

The other CT piece consequently has approximately 798.74236–877.44177 m_rel. Applicable η floors still need checking.

Replace Consolidated:95's “so the plan is feasible” with:

> CT's two-holder mass intervals are nonempty under E1/E2. This removes the arithmetic obstruction; ZIP granularity, full-union M1 and global compatibility remain unproved until an actual pattern/cover passes the gates.

## 6. Changes required and lane structure

**Adopt with these changes:**

1. Explicit binary, complete-partition, nonempty k≥2 admission contract; no later territory changes.
2. Lazy validated library, not exhaustive pre-carving or whole-family gating upfront.
3. Exact drawn ranking, including maxima, mean weighting, REVIEW alternatives and joint main-map comparison.
4. Domain-checked independent lower bounds; restricted-library status never promoted to global proof.
5. Correct pricing includes K and prior-pass duals; Phase I and A-guided growth precede optional dual heuristics.
6. Retain exact dollar audit and E1–E3 provenance; a τ-envelope is not eligibility.
7. Approve a resource-based E4 pilot budget and use the stop rules above. CT's arithmetic pass is not a carve certificate.

**Lanes I would file:**

- **A / #103 — money, bounds and seeds.** R1/R2, explicit E1–E3 bands, F2/rule-C bound with its full domain, K grid and alternate seed plans. Drop mandatory cut ingestion, infeasibility-feedback APIs and post-selection balance LP from the main path. A's role remains; its contract is not literally “unchanged.”
- **B / #129 — validated pattern generator.** Complete state partitions and attach sets, heuristic-first, full-union gate, reusable immutable witnesses. CT+RI and FI/NY benchmarks first. Exact MILP may find witnesses; no new infeasibility proof is required to release an `ok` pattern.
- **P / #130 — library selector and deliverables.** Lazy whole-column builder, selection MILP, candidate requests, full ledger/audit/ranking/render/tracking and shortlist. Start with fixtures; integrate real A/B output before claiming completion. Add dual-guided generation only if measured growth needs it.

Freeze one shared column/context schema first; then A, B and P can build in parallel. One integrator owns shared documents. No separate pricing framework, exact pricer or v2 ban subsystem until evidence requires it.

DECIDED: none; review recommendations only, no implementation or owner-policy change applied.
LEARNED: Complete single-root state patterns plus whole-state columns form an exact set-partitioning representation of rule-C maps when the full corresponding pattern universe and policy domain are included; finite libraries supply feasible incumbents, not global infeasibility proofs.
LEARNED: With E1's extract rate and E2's IFA −20%/+15% target band, CT+RI has 78.69941 m_rel of two-holder mass slack; this is an arithmetic condition, not an M1 drawability certificate.
