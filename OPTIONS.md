# Open implementation decisions

These decisions define what the final deliverable must guarantee. They should be resolved before changing solver semantics or geographic policy; otherwise implementation choices may silently become business rules.

## D1 — Support multiplicity and whole-unit integrity

A **support** is the set of planning units from which a district is formed. The current model permits several districts to use the same support, but records each planning unit's share in aggregate across those districts. Decoding can therefore divide an aggregate share among repeated district instances.

### Options

1. **Unique support:** each support can produce at most one district. This is simple, but may exclude useful or necessary plans.
2. **Repeated supports with district-level whole-unit ownership:** multiple districts may use the same broad footprint, but each indivisible planning unit belongs to one specific district instance. This requires explicit district copies or a rigorously equivalent integer formulation.
3. **Repeated supports with fractional planning-unit shares:** retain the current aggregate interpretation. This is incompatible with a claim that planning units are indivisible.

### Recommendation

Choose option 2: permit repeated supports, but enforce whole-unit ownership at the individual district-instance level. This preserves flexibility without claiming indivisibility that the formulation does not provide.

## D2 — Final capacity policy

The master plan imposes nominal district-capacity bands. ZIP realization approximates those targets using indivisible ZIPs, and later fragment healing may move ZIPs without checking capacity. A master-feasible plan can therefore produce final districts outside the original bands.

### Options

1. **Strict nominal band:** every final district must satisfy the original bounds.
2. **Published realization tolerance:** final districts may exceed the nominal bounds by a specifically approved amount.
3. **Explicit exceptions:** violations are allowed only as named and reviewed exceptions.
4. **Target only:** bands guide optimization but are not publication constraints.

The failure policy must also be explicit: fail the scenario, publish it as noncompliant, or seek an approved exception. The implementation must not silently widen a band or discard opportunity.

### Recommendation

Use a declared ZIP-realization tolerance measured against the original nominal band. Recompute compliance after all healing and fallback routing, identify every exception, and never silently widen tolerances or drop opportunity. The tolerance is a business decision, not whatever the current algorithm happens to achieve.

## D3 — National fallback and bundle semantics

The pipeline currently plans WH, FI, and WIFI capacity before routing some national fallback opportunity. Fallback can therefore add mass that was absent from capacity planning.

Bundle meaning is also ambiguous. A district labeled as a combined bundle does not necessarily own every associated fine channel at every ZIP; the fine channels comprising a national business channel can have different district owners.

### Capacity options

1. Include fallback national opportunity in capacity planning from the outset.
2. Add fallback afterward, then recompute final capacity and report any failures.

### Ownership options

1. **Product-form bundle ownership:** at a ZIP, one district owns every fine channel in the bundle.
2. **Independent fine-channel ownership:** fine channels may have different owners; the bundle is only a planning or reporting label.

### Recommendation

Include expected fallback mass in planning whenever its destination policy is known, and make the final `(ZIP, fine channel) -> district` ledger authoritative. If the business requires true bundles, enforce product-form ownership explicitly. Otherwise, describe bundles as planning categories and report actual district channel sets rather than implying joint ownership.

## D4 — Authoritative geography and missing data

The system contains several distinct geographic objects: planning units, the contiguity graph, gazetteer points, rendered ZCTA polygons, support overrides, and optional nationwide extension. They are not interchangeable; rendered polygon adjacency is not the model's contiguity graph.

### Decisions required

Pin the following for every result:

1. graph-construction method and version;
2. gazetteer vintage;
3. authoritative planning adjacency;
4. permitted support overrides;
5. treatment of assigned ZIPs absent from the graph;
6. whether zero-opportunity nationwide ZIPs are in the certified optimization domain or are only a display/service extension.

For missing geographic evidence, choose an explicit policy: fail certification, mark the check unverified, exclude the ZIP under a documented rule, or attach it under a separate non-optimized extension policy.

### Recommendation

Ship a versioned geographic manifest with every result. Required missing graph evidence should fail certification or make the relevant check unverified; it must never be inferred from rendered polygons. Keep the commercial optimization domain separate from optional nationwide extension, and label extension assignments as non-solver-certified. Record the gazetteer vintage explicitly.

## D5 — Staffing status and certificate tier

Current scenario exports may use placeholder representative IDs such as `R0001`. These identify districts but do not prove that actual representatives were matched to territories.

Some solver runs also permit nonzero MIP gaps. Such runs may produce good feasible solutions, but do not establish exact global optimality.

### Staffing options

1. **District-only plans:** placeholders are clearly labeled and no staffing claim is made.
2. **Staffed plans:** require an actual roster, eligibility checks, one representative per district, synchronized outputs, and final ZIP-level matching.

### Certificate options

1. Exact solve with `mip_rel_gap=0.0` and a valid certificate.
2. Bounded solve publishing the incumbent, bound, and actual gap.
3. Feasible solution only, with no optimality claim.

Master optimality, final-ledger feasibility, and staffing validity are separate properties and must be reported separately.

### Recommendation

Call catalog outputs district-only plans unless actual roster matching has been run and verified. Never present placeholder IDs as staffing. Publish each run's actual solver status, bound, and gap, and reserve “globally optimal” for a valid exact certificate.

## Recommended decision package

| Decision | Recommended policy |
|---|---|
| D1 | Allow repeated supports; assign whole units to explicit district instances |
| D2 | Use an approved realization tolerance; fail or report every final breach |
| D3 | Plan known fallback mass; make the fine-channel ledger authoritative; enforce bundles only when commercially required |
| D4 | Pin a versioned graph and gazetteer manifest; treat missing evidence as failed or unverified; separate geographic extension |
| D5 | Treat the catalog as district-only by default; require roster matching for staffing; publish actual solver gaps |

D2 and D3 are the highest-impact sponsor decisions: they determine whether final maps are operationally compliant and what channel ownership means.
