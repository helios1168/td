# Group 2 geography and contiguity research handoff

## Purpose

This document consolidates the original full-problem handoff and the later Group 2 memory
session. Its immediate purpose is to give several independent frontier models the same precise
question: how should the planner find a geography-valid incumbent without weakening the fixed
business rules?

The immediate deliverable is an algorithm and experiment design, not a new territory map. Any
proposed method must distinguish a temporary optimization relaxation from a change to the
accepted business problem.

## Original handoff in brief

- Work in `/Users/Shared/sv-ntlee/repos/td/.claude/worktrees/agy-math-review` on branch `worktree-agy-math-review`.
- The fixed scenario is 14 National, 11 Wealth, and 21 FI districts. It uses the existing 90 to 110 percent opportunity bands, 5 percent staffing tolerance, six-state cap, distance and connectivity rules, and conditional state-level purity.
- The original national MILP found no incumbent within 180 or 600 seconds. A diagnostic without connectivity and distance solved quickly, so the handoff proposed splitting California into two ZIP-derived macro-regions and starting decomposition without loosening the business bands.

The original full-problem track also established that state-plan connectivity and final ZIP
connectivity are separate gates. Level 0 connects contacted planning units on a state rook graph.
The realizer later cuts split shares into ZIPs and can still create pieces. Border-aware cuts
helped earlier cells, but band-locked repair and small bridge shares remained failure modes.

The historical Group 2 list contained 20 priority states. Requiring all 20 was proved infeasible
because Colorado's connected support under the current geographic limits could supply at most
548.754666 National units, below the 553.724691 district floor. The user then removed Colorado
from the priority and required list. The current list has 19 states, while Colorado remains
eligible as supporting territory:

`TX NY FL NJ IL AZ NC PA MI OH VA GA MD WA UT IN LA MN CT`

The active research case is planner-selected National states, exact district counts, and
supporting states allowed. The old required-20 case is historical evidence, not the case to rerun.

## Work completed in this session

- Added a deterministic in-memory `CA1` and `CA2` planning view while retaining California as the parent for purity and final output.
- Added parent-coupled purity, macro-region metadata, and a configurable national-contact cap for macro children.
- Added focused tests for the parent purity, contact cap, planner arguments, and recorded metadata.
- Validation passed: 54 Group 2 tests passed, and the full suite passed with 925 tests when pinned to the 2025 ZCTA shapefile.

Three solver runs established the useful boundary:

1. With one National contact allowed per California child, the model was proven infeasible in 1.5 seconds. Each child carries more National opportunity than one district's upper band, so that cap is mathematically impossible under parent purity.
2. With two contacts and all spatial constraints enabled, the solver found no incumbent in 180 seconds. This is inconclusive, not a proof of infeasibility.
3. With two contacts but connectivity and state-pair distance constraints removed, the complete state-level plan solved.

## Current stopping point and key finding

The third run is the important result for the next session. Here, "relaxed national model" means only the spatial constraint families were removed:

- removed: single-commodity-flow connectivity rows and state-pair distance-cap rows;
- retained: exact district counts, 90 to 110 percent opportunity bands, staffing tolerance, six-planning-unit cap, parent-level purity, priority-state coverage, and the existing split and band-break rules.

Under that relaxation, the National coverage stages solved as follows:

- Group 2 priority coverage optimum: 5,654.8946 in 0.053 seconds.
- Full coverage optimum: 8,613.4952 in 3.793 seconds with zero optimality gap.
- Contact minimization optimum: 54 contacts in 36.624 seconds.

"Full coverage optimum" means that all 8,613.4952 units of available National opportunity were assigned across exactly 14 National districts while satisfying the retained business constraints. It does not mean the territories form valid geographic shapes, and it is not the final end-to-end optimum.

This isolates the bottleneck: the requested counts, bands, and parent purity are mutually feasible. The difficulty comes from enforcing connectivity and distance simultaneously. The relaxed solution is visibly nongeographic, for example one National district contains `CA1`, South Dakota, and Wisconsin, while another contains `CA2` and Missouri.

The run then produced exact counts for all three channels and a preliminary state-grain staffing value of 239.883 with zero unstaffed opportunity. It stopped before ZIP realization because the purity audit treated a serialized `0.999999` share for Mississippi as a violation. This appears to be a tolerance or rounding artifact, not a substantive purity failure.

### Where this sits in the pipeline

```text
California macro-regions
        |
        v
Relaxed state/channel plan      CURRENT RESULT
        |
        v
Geography-valid state plan      NEXT SESSION
        |
        v
ZIP-level realization/draw      NOT REACHED
        |
        v
Final staffing, FEFx, and map
```

There is no result figure yet. The run did not reach ZIP-level realization, so no `assignment.csv` or PNG map exists. Plotting the relaxed state plan would show scattered diagnostic groupings and could be mistaken for a valid territory proposal.

## The fixed geography problem

### Planning objects

Let `V` be the state-grain planning units, except that California is represented by `CA1` and
`CA2`. Let `G = (V, E)` be their rook-adjacency graph. Each unit `v` has National opportunity
`w_v`, a centroid, a parent state, and eligibility metadata.

For National district slot `j`:

- `z_vj` is 1 when district `j` contacts planning unit `v`.
- `y_vj` is the fraction of unit `v` assigned to district `j`.
- `m_j = sum_v w_v y_vj` is the district's National opportunity.

The relaxed incumbent supplies a business-feasible starting assignment `(z, y)`. It violates
geography and is evidence of projected feasibility only.

### Hard constraints for an accepted National plan

An accepted plan must satisfy all of the following at once:

1. Exactly 14 National districts are used.
2. Every National district is within its 90 to 110 percent opportunity band. The recorded
   National band for this instance is `[553.724691, 676.774623]`.
3. National opportunity is fully covered: for each eligible planning unit,
   `sum_j y_vj = 1`, subject to the existing channel and eligibility semantics.
4. Contact and share agree: `0.05 z_vj <= y_vj <= z_vj`.
5. A district contacts at most six planning units.
6. The contacted nodes `{v : z_vj = 1}` induce a connected subgraph of `G` for every district.
   Connector-only or zero-share Steiner states are not currently allowed because every contact
   carries at least a 5 percent share.
7. No district contains a forbidden centroid pair. The ordinary maximum is 900 km. A pair
   involving Washington may use the existing 1,200 km state override. The implemented rule is a
   pairwise diameter restriction, not a route-length or radius restriction.
8. Parent-state conditional purity remains exact. If any child of a parent state contacts a pure
   National district, the parent's full National share must be assigned across pure National
   districts, with none assigned through a mixed bundle. For California this couples `CA1` and
   `CA2`.
9. Each California child may contact at most two pure National districts. The runner currently
   defaults this option to one, so every research run must explicitly request two until that
   default is changed.
10. The current Group 2 priority list excludes Colorado, supporting states are allowed, and the
    existing split caps and band-break semantics remain in force.

The downstream fixed counts are 11 Wealth and 21 FI. National feasibility should be solved first,
but a candidate is operationally useful only if it can be frozen and the later sequential stages
can still solve without changing the National assignment.

### Two distinct geography gates

1. State-plan gate: every district satisfies planning-graph connectivity, the pair-distance rule,
   the six-planning-unit cap, counts, bands, coverage, and parent purity.
2. ZIP-realization gate: after shares are cut to ZIPs, every realized district is connected on the
   ZIP-cell graph and still satisfies bands, purity, coverage, counts, and staffing audits.

A connected state plan is necessary for the current workflow but is not sufficient for a valid
ZIP map. Each proposed technique must say which gate it addresses.

## Well-formed research question

Given the exact business-feasible relaxed incumbent and planning-unit data `(V, E, w, centroids,
parent mapping)`, find a full-coverage assignment to 14 National districts that satisfies every
hard constraint above. Prefer a method that changes as little of the relaxed assignment as
practical, but treat feasibility as the primary objective.

> What is the smallest implementable decomposition, exact reformulation, cut-generation scheme,
> or repair neighborhood that can convert the proven business-feasible relaxed assignment into a
> state-plan incumbent satisfying connectivity and pair-distance simultaneously, without changing
> district counts, opportunity bands, minimum contact share, parent purity, the planning-unit cap,
> or the 900/1,200 km distance policy?

If the unchanged problem is infeasible, the method should produce a defensible certificate or a
targeted conflict set. A timeout, a failed greedy repair, or failure to find a warm start is not an
infeasibility result.

### Questions each frontier model should answer

1. Is the best next method an exact formulation, relaxation plus separation, connected-district
   column generation, graph decomposition, large-neighborhood search, or a hybrid? Why does it fit
   this instance better than the alternatives?
2. How should the relaxed incumbent be used? Specify the repair variables, neighborhoods, or
   distance-from-incumbent objective. State which decisions may move and which remain fixed.
3. How will connectivity be enforced or separated? Give the exact cut, subproblem, dynamic
   program, flow model, or connected-set representation. Explain why it is valid with fractional
   shares and the 5 percent minimum contact.
4. How will the pair-distance conflict graph be integrated so that connectivity repair does not
   repeatedly create over-distance districts?
5. How will California's two macro children and parent-coupled purity be handled without restoring
   the disproved one-contact cap?
6. What symmetry can be removed safely? Explain why the proposed symmetry breaking preserves the
   projected feasible set.
7. What is the shortest experiment that distinguishes formulation weakness from true
   infeasibility? Include stopping rules and the evidence recorded at each stop.
8. How will the method produce either a solver-valid incumbent or a checkable infeasibility or
   conflict artifact?
9. What new failure modes could the method introduce at ZIP realization, and what state-plan
   information can reduce those risks before realization?
10. What is the minimal code surface to change, and which independent checker should validate the
    result?

Candidate families worth comparing include a business master with connectivity and distance
separation cuts, stronger rooted-connectivity formulations, set partitioning over connected and
distance-valid supports, regional graph decomposition, conflict-graph-first support generation,
and large-neighborhood repair that reoptimizes several affected districts together. Additional
macro-regions are also in scope as a modeling proposal, but they must retain parent purity and
reproducible ZIP membership.

Any heuristic proposal must end with the original MILP checker accepting the point. Any proposed
constraint relaxation remains diagnostic unless it is fully restored before acceptance.

## Required response from each independent model

Each model should return a read-only design memo with:

1. A one-paragraph diagnosis of the likely bottleneck.
2. Its recommended method, stated mathematically enough to implement.
3. A proof sketch that the method preserves every hard constraint at acceptance.
4. Pseudocode for the master, repair, or cut loop.
5. A bounded experiment matrix with time limits and decisive outputs.
6. The independent validation checks and certificate format.
7. Expected failure modes and a fallback method.
8. A ranked comparison with at least two alternative approaches.
9. A minimal implementation plan naming likely repository symbols, but no edits.

Answers must distinguish `proved infeasible`, `feasible incumbent found`, and `no incumbent within
the limit`. They must not recommend loosening opportunity bands unless the unchanged model is
first proved infeasible and the user separately asks for a minimum-violation study.

## Open items

1. Export a compact, confidential-safe research instance containing planning-unit aggregates,
   adjacency, centroids or the derived distance-conflict graph, parent mapping, band bounds, and
   the relaxed incumbent. Models without this data can design algorithms but cannot establish
   instance feasibility.
2. Copy or regenerate the three macro-run result directories. They are cited below but are not
   present in this worktree, so their detailed artifacts cannot currently be inspected here.
3. Recheck each one-family diagnostic with a useful budget and the relaxed incumbent as a starting
   point. The existing 60-second no-incumbent outcomes are too weak to identify which family is
   individually decisive.
4. Build one independent acceptance checker for counts, coverage, bands, minimum shares, parent
   purity, connected components, pair distances, and planning-unit count.
5. Decide how close a geography-valid assignment should remain to the relaxed incumbent after
   feasibility is achieved. Candidate secondary metrics include changed contacts, moved
   opportunity, or changed state-district pairs.
6. Correct the purity audit so serialization-scale values such as `0.999999` are handled by a
   documented numerical tolerance without masking real violations.
7. Decide whether the six-unit cap should count macro children or parent states. Current code
   counts planning units, so splitting California consumes two contacts in that cap.
8. Decide whether more macro-regions are a modeling tool of last resort or part of the intended
   state-plan grain. Parent purity and ZIP-level reproducibility must remain explicit either way.
9. After a valid National plan exists, freeze it and solve Wealth 11 and FI 21. If a downstream
   stage fails, define a bounded cross-channel repair rather than silently changing National.
10. Run ZIP realization, contiguity repair, final staffing, FEFx, and map generation only after the
    state-plan checker passes.

## Recommended next steps

1. Give this handoff unchanged to each frontier model and collect independent read-only memos.
2. Build the compact research-instance export and the independent checker before implementing any
   proposed solver change.
3. Compare the memos on correctness, preservation of hard constraints, certificate quality,
   implementation size, and expected solve time.
4. Implement the smallest high-confidence method behind a feature flag in the Group 2 runner.
5. Run a staged ladder: relaxed-incumbent validation, distance-only restoration,
   connectivity-only restoration, both spatial families, then the unchanged full National pass.
6. Freeze the first fully checked National incumbent and proceed through Wealth, FI, ZIP
   realization, staffing, FEFx, and the first meaningful map.

## Copy-paste prompt for frontier models

```text
Work read-only. Do not edit, commit, push, or launch a long solve.

Read agy-job/reports/GROUP2_MEMORY_SESSION_HANDOFF.md, then inspect only the repository symbols and
aggregate artifacts needed to understand the Group 2 National model. Treat confidential inputs
and outputs as local-only. Do not display customer-level rows.

Independently solve the research-design question in the handoff: propose the smallest implementable
method that can turn the business-feasible relaxed 14-district National assignment into an
incumbent satisfying graph connectivity and the 900/1,200 km pair-distance rule simultaneously.
All listed business constraints are hard. Temporary relaxations are allowed only inside an
algorithm that restores and independently verifies every hard constraint before acceptance.

Do not treat a timeout as infeasibility. State what instance data you inspected, separate proven
facts from hypotheses, and use the required response format in the handoff. Give exact cuts,
subproblems, neighborhoods, or formulations rather than generic advice. End with one recommended
approach, a bounded experiment plan, and the evidence that would accept or reject it.
```

## Evidence and artifacts

- One-contact infeasibility: `battery/results/group2_macro_ca2_n14w11f21_20260914_run1`
- Full-spatial two-contact timeout: `battery/results/group2_macro_ca2_n14w11f21_20260914_run2`
- Relaxed successful plan: `battery/results/group2_macro_ca2_n14w11f21_20260914_run3_relaxed`
- Most useful relaxed-run files: `plan.json`, `macro_regions.json`, `plan_purity.json`, `staffing.json`, `run_request.json`, and `projections/*/state_shares.csv`.
- Session implementation files: `tools/group2_run.py`, `tests/test_group2_run.py`, and `tests/test_group2_acceleration.py`.

These outputs are confidential. Inspect or report aggregates, shapes, and counts only. Do not display customer-level rows.

The three `battery/results/group2_macro_*` directories are not present in this worktree as of this
update. Their summary values above come from the prior session record and should be verified
against copied artifacts before they are used as current experimental evidence.

## Working-tree safety

The worktree contains uncommitted Group 2 implementation and test changes plus unrelated
math-review document changes. Preserve them and do not commit the whole tree. The research handoff
is the only file changed for this update.
