# Oracle review: deadline, primitives, research scope

Source shorthand: **M** = `docs/problem/MANDATES.md`; **P** = `docs/problem/PROBLEM.md`; **W** = `WATCHDOG.md`; **R** = `docs/lenses/REVIEW_2026-10-07.md`; **C** = `docs/lenses/review-2026-10-07/CONSOLIDATED.md`; **F** = `/tmp/iss/research/RESEARCH_FRAMING.md`. Other packet references name files under `/tmp/iss/research/`.

Assumptions: clock starts at supplied 00:34; checkpoint describes implementation state. Documents, not runtime, reviewed. Latest explicit owner decisions supersede older text; reviewers’ inferred consequences do not automatically amend owner decisions.

## 1. Primitives

Five suffice. Supports, patterns, packing and hypergraphs are representations—not additional requirements.

| Primitive | Definition | Source | Not |
|---|---|---|---|
| **Territory atom** | One indivisible 2025 ZCTA within its planning-channel footprint, carrying additive dollar opportunity, land area and original-state identity. | M, M1 coverage/multipart rulings; R, D3/E1/E3; MODEL §1 | Positive-opportunity cell alone; county; polygon component. Zero-dollar atoms remain territory. |
| **District admissibility** | An atom set passes exact polygon-plus-approved-connector connectivity and has no prohibited connected smaller-side area cut. | M, M1 “Necks”; W §2 | Graph connectivity alone, compactness, or positive border contact between coarse units. |
| **Eligible partition** | Disjoint admissible districts cover each channel footprint exactly once, preserve cell ownership, satisfy applicable dollar windows and allowed district counts. | M, M1 coverage; R, bands/D1–E3/adopted formulation; W §3 | Fractional state shares; display fill; channel-average eligibility. |
| **State incidence** | A state’s incidence count is number of districts owning any of its atoms; counts ≥2 mean split, and count−1 means cuts. | P, “Looks first (restated 2026-10-05)” | Positive-mass holders, connected fragments, or renamed county units. Count separately per channel. |
| **Preference and policy** | Rank eligible partitions by splits, cuts, defects, shape, balance; rule C separately restricts each district to touching at most one split state. | R, D6 and “Rule C”; P, looks-first row | Rule C as consequence of M1, or η/support caps as universal geography laws. Preserve owner’s flagged-REVIEW exception for defects. |

M1’s neck predicate needs precision: connected side \(A\), \(0.05\,a(D)\le a(A)\le0.5\,a(D)\), cut width below 10 km. Complement may be disconnected. Connector width depends on existence of a **≥10-km-wide** land alternative within states touched by district—not merely any land path. [M, M1]

Masking and tracked/shortlisted output remain hard delivery requirements, not optimisation primitives. [M, Masking/T1]

## 2. Alignment audit

### Inherited decisions and source drift

1. **Dollar rules changed.** W §3, MODEL §1 and SPLITS §2.2 retain older τ/±10% language. R D3 replaces both checks with per-district target windows; E2 changes IFA’s lower edge; E3 makes WIFI’s window depend on its dollar mean. COMMON and F §1.2 incorrectly universalise K-independent windows. A τ-envelope cannot substitute for direct dollar eligibility. [C, round 3]

2. **K approval remains ambiguous.** D1 explicitly says IFA K≥50. R calls its rationale overtaken; C’s round-2 commentary infers 46–55. Changed rationale alone does not revoke explicit decision. Report 46–49 as requiring confirmation, not already approved. [R, D1; C, owner answers round 2]

3. **Zero-dollar ownership counts.** SPLITS §2.1’s positive-opportunity definition conflicts with later P’s any-ZCTA rule. MODEL §1’s dropped-channel blank ownership also cannot silently override footprint coverage. Incidence, coverage and certificate domains must use actual territory ownership.

4. **MD is unresolved infeasibility, not search difficulty.** R “Findings” reports no IFA rule-C plan at E2. No faster carver cures that. R1–R4 remain alternatives, not approvals. County relabelling under R2 must not erase original-state splits or silently change rule C’s state meaning.

### Formulation and certificate

5. **Carve-first is sound as restricted incumbent search.** Whole-state columns plus complete root-state patterns prevent incompatible pieces being selected separately. “M1-clean with no repair” requires identical full ZIP unions, connectors, dollars and zero-dollar ownership at generation and final audit. Existing district seeds need reconciliation into compatible patterns; individually good districts need not tile a state. [R, adopted B/P; C, R13]

6. **Pattern cost needs its structural invariant.** \(\sum y_p\) counts split states only when each selected pattern splits exactly one original state, complete root coverage is exclusive, and attach states remain whole. Joint MD+PA patterns need actual state-incidence accounting; \((k_p-1)\) then need not equal total cuts. [R, P and R1]

7. **Rule C row is appropriate within declared support model.** With F2 holder links, \(n_S=1\) allows at most one split state; \(n_S\ge2\) is impossible for multistate supports. It constrains actual split states, not all candidates. Zero-mass contacts still require explicit ownership treatment. [R, Rule C; MODEL §§1,3]

8. **Certificate language remains conditional.** A’s η, modes, caps, support family and dollar rules define a restricted domain. Every claimed covered map must project into its relaxation; merely checking some column attributes is insufficient. Certificate requires valid bound/proof status, not timeout incumbent. Matching bound can establish optimality within named covered domain, never global “minimal” under current reporting contract. [R, Certificate; P, #103/#119 row]

9. **Support master is not automatically a column pricer.** Enumerating useful requests needs no dual theory. Genuine reduced-cost pricing needs actual column costs, coverage coefficients and K dual; heuristic failure cannot certify absence of improving columns. [C, round 3; P3]

### Analogue errors

10. **Fixed-target and τ bands do not search identical spaces.** F §1.2/§3 assertion is false. Example: total 20, K=2, target window [8,12] admits masses 8 and 12; ±15% around mean 10 does not. Enumerating K while retaining original dollar windows is equivalent to variable-K search; replacing windows is not.

11. **Planarity is unproved and unnecessary.** Multipart atoms and connectors invalidate assuming standard planar-dual structure without verification. Remove “planar” from COMMON and P5/P6 premises unless proved for actual graph. [M, M1 multipart/connectors; F §1.1]

12. **Neck ≠ conductance or ordinary min-cut.** F §1.6 and P6 conflate absolute width, width/area ratios and unrestricted small-side cuts. Dropping connected-side condition changes predicate; connector capacities are district-state-dependent. F’s connector summary also omits ≥10-km land-alternative requirement. Reuse exact gate; literature analogies are not equivalence proofs.

13. **Coarsening needs connected bags.** A connected coarse side lifts to a connected fine side only with connected contracted bags and faithful edges. Preserve areas and district-dependent connector semantics. Coarse pass does not certify fine pass. F §1.6/P7 omit these conditions. Connected bags alone also do not make an arbitrary coarse partition connected. [F §1.7 pipeline]

14. **Hypergraph objective is useful; universal hierarchy is not.** State cut-net and λ−1 exactly express incidence objectives. They do not enforce M1, rule C or dollar windows. Intermediate geography families are not established here as nested ZCTA partitions; treat that as unproved, not input fact. [F §§1.3,1.7]

15. **Packing compatibility is not pairwise conflict.** A connected state chain can form one district without every state touching root or each other. P1’s adjacency-to-fragmented-item premise narrows feasible footprints; “bin packing with conflicts” cannot represent connected-support compatibility unchanged.

16. **“Can stay whole” does not imply “fix whole.”** F §1.8 converts absence of individual forced-split evidence into simultaneous fixing. Such fixing is heuristic restriction, never certificate-safe deduction. COMMON further omits defects from ranking and understates certificate restrictions.

## 3. Packet decisions

These are deadline recommendations—not cancellation of owner-requested longer-term investigations. COMMON’s quote, DOI and retraction requirements make broad verified surveys especially unlikely within one hour.

| Packet | Well posed / hour-answerable / tonight impact | Decision |
|---|---|---|
| **P1** | Partly; conflates connectivity with conflicts. Narrow arithmetic answer feasible; broad survey not. Little direct map impact. | **CUT tonight.** Existing forced-split and capacity screens suffice; defer stronger packing bounds. |
| **P2** | Core projection question sound; multi-paper historical survey too broad. Prevents overclaims, not missing maps. | **MERGE with P3.** Short certificate checklist: covered domain, valid relaxation, proof status, restricted-library limitations. |
| **P3** | Sound after naming actual columns/objective. Broad scale inventory unlikely in hour. Exact pricing not required tonight. | **MERGE with P2.** Stop once honest incumbent/bound reporting contract is written. |
| **P4** | Tool matrix and balance comparison overloaded; equivalence premise false. One adapter assessment possible. | **REWRITE:** “Can one existing districting move generator preserve fixed dollar windows and reduce original-state splits, with every accepted result checked by td.audit, using current seeds without rebuilding pipeline?” No package tournament. |
| **P5** | Rooted connected pieces may overrestrict pieces whose union with attaches is admissible. Complexity/fastest-method survey too broad. Direct implementation relevance high. | **REWRITE:** “Which minimal grow/recombine/local-transfer heuristic partitions one requested state completely, respects residual windows, and validates every piece-plus-attach union with existing M1 gate?” Unknown remains unknown. |
| **P6** | Predicate incomplete around connectors; proposed quantities non-equivalent. “Cheapest exact” unsupported within hour. Gate correctness essential, replacement unnecessary. | **REWRITE:** “What are current gate’s exact acceptance and timeout semantics, and how will unchanged gate validate each affected district within search budget?” Implementation inspection, not literature hunt. |
| **P7** | Useful broad topic; ranking NY/CA grain requires actual experiments, not literature alone. No immediate requirement. | **CUT tonight.** Optional connected coarsening remains heuristic acceleration; final validation stays ZCTA-level. |

No dedicated hypergraph packet matches owner’s separate request in F §1.7. P4/P7 scatter it across tool and coarsening surveys. Record it explicitly as deferred research; do not claim completed coverage.

## 4. Will it land?

**Seven broad searches, synthesis, new carving, integration and complete scenario maps by 08:00: low probability.** Checkpoint says no implementation launched; MD blocks settled IFA track, main-map K needs reconsideration, and seeded FI20 is only near-ready starting point described. [R, Status/Findings]

### Needed for maps by 08:00

- **00:34–01:00:** freeze one dollar/coverage/M1 contract. Resolve IFA route and K approval; no silent rule-C removal or band change. Screen counts using \(\lceil M/U\rceil\le K\le\lfloor M/L\rfloor\), with WIFI handled per candidate K.
- **01:00–02:00:** integration pilot using documented FI20 seed and existing whole-unit planner. Establish tracked run, unchanged M1 gate, direct dollar checks, state splits/cuts and render. R reports FI20 ≤6 splits against forced floor 5; this is source evidence, not fresh validation.
- **02:00–05:30:** reuse admissible whole-state groups and seed partitions. Implement narrow P5 heuristic for unmet patterns; maintain best complete eligible partition. Use arithmetic windows and cheap connectivity checks before expensive neck validation. No unknown-as-infeasible cuts.
- **05:30–08:00:** stop expanding architecture. Validate complete scenario ownership and dollars, rescore, render, register shortlist and audit tracking. Reserve time for failures, not new formulations. [M, T1; R, P]

Schedule is proposed budget, not owner-approved parameter change. Most probable deliverable is seed-based improvement with honest unresolved gaps—not certified fewest-split maps. If IFA decision remains blocked, say incomplete; partial main-map results do not satisfy full goal. [W §1 and concern 6]

### Needed for certificate, not map construction

Projection/domain proof, correctly scoped lower bound, gap-zero proof or infeasibility certificate, and reconciliation with original-state split counting. Restricted-library optimality alone proves neither global optimum nor global infeasibility. [P, #103/#119; R, Certificate]

### Nice to know

Packing structure theorems, exact connected-column pricing, full tool comparison, hypergraph replacement, fastest neck algorithm, optimal geography grain.

Drop these from deadline path—not M1, dollar checks, coverage, masking or T1. No executor handoff requested by this review; no additional architecture required before pilot.

## 5. Simplest defensible formulation

For each channel \(c\), choose partition \(\mathcal D_c\) of footprint atoms.

Require:

\[
\operatorname{M1}(D)=\mathrm{pass},\qquad
L_c(K_c)\le \sum_{z\in D}d_{zc}\le U_c(K_c),
\qquad K_c=|\mathcal D_c|.
\]

Enforce approved scenario count constraints and exact cell ownership.

Define:

\[
r_{sc}=|\{D\in\mathcal D_c:D\cap Z_s\ne\varnothing\}|,\qquad
b_{sc}=\mathbf1[r_{sc}\ge2].
\]

Where rule C applies:

\[
\sum_{s:D\cap Z_s\ne\varnothing}b_{sc}\le1
\quad\text{for every district }D.
\]

Minimise lexicographically:

\[
\left(\sum_{sc}b_{sc},\
\sum_{sc}\max(0,r_{sc}-1),\
\mathrm{defects},\mathrm{shape},\mathrm{balance}\right).
\]

Keep owner-review exception for defect improvements. [P, looks-first row]

**Practical restricted version:** existing whole-state columns plus complete compatible carve patterns; finite candidate-K enumeration preserves dollar windows, including WIFI. Joint-pattern extensions count actual state incidence, not one split per pattern.

**Gives up:** exhaustive search and universal optimality claims; does not give up territory, necks, dollars or split semantics. η/caps remain declared search restrictions where retained, not newly asserted mandates. Restricted model can be computationally useful; formulation alone does not make full problem tractable.

LEARNED: none  
DECIDED: none