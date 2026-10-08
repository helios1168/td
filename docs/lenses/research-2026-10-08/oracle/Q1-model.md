# Q1 — direct division carver: conditional decomposition, unmeasured solve cost

## Verdict

A direct per-state partition model is a useful Middle Atlantic pilot. It is not yet demonstrated cheaper than adapting existing code, and cut-border minimization does not encode the owner's entire visual requirement. Correct the count ranges, preserve exact M1 admission, and benchmark a genuinely scoped instance before building coarsening or promising runtime.

## 1. When decomposition is exact

Conditional on sealed division boundaries, binding fixed-dollar windows, and rule C, every state whose mass exceeds U must split. If every state in that division must split, a district touching two original states would violate rule C. Thus districts are single-state. This is a mathematical consequence of those conditions, not of sealing alone.

Using the approximate masses already reported and IFA window [$1,000M,$1,437.5M]:

- NJ $3,552M: K=3 only.
- PA $4,120M: K=3 or 4, not necessarily 3.
- NY $5,470M: K=4 or 5.

The four local count combinations total 10, 11, 11 and 12. The aggregate division range 10–13 is weaker: 13 cannot be achieved under this single-state decomposition. Full-precision masses must confirm the enumeration before execution. Global IFA K remains a coupling: retain local alternatives rather than choosing every state's K independently and forgetting their sum.

This does not generalize to every division. Under-L states may attach to pieces of a split neighbor, and their allocation couples the carve jobs. DC is its own unit, not an implicit part of MD. F1 reserves MD alone as a waived IFA district; MD is not forced to split by ordinary U. Zero-dollar ZCTAs remain owned territory, not removable slack. Multipart ZCTAs remain indivisible vertices under the existing authoritative representation; graph connectivity must not be advertised as a stronger new polygon-component guarantee.

## 2. Direct model

For a fixed state and K, binary x[v,j] assigns every shipped vertex exactly once. Impose each district's full-precision dollar sum in [L,U]. Add connectedness and minimize a declared shape proxy, initially shared-border cut length. Original-state split count is already fixed for this pilot; cuts equal K minus one within each state, so enumerate smaller K first or retain all K for global coordination.

Cut length is a useful comparison objective, not a guarantee of nice shapes. An enclosed compact metro district may have a short boundary and leave an unattractive surrounding district. Neither holes nor tendrils are categorically excluded. Owner visual review remains necessary; do not silently replace the settled ranking with this proxy.

Rooted single-commodity flow is a valid connectivity formulation if each district has a valid selected root and all assigned vertices consume flow. Fixed seed roots restrict the search; disclose that restriction. Variable roots preserve the broader domain but require root-selection/supply constraints and create symmetry. Zero-dollar vertices still consume connectivity flow.

Lack of callbacks does not forbid separator formulations: solve, detect disconnected components, add valid connectivity rows, resolve. More importantly, existing code already implements both ingredients: `tools/exp/contig/draw.py:746–772` describes connectivity cut loops, single-commodity flow for districts with root bodies, border objectives, and a neck-aware cut loop. Its rooted-body interface may need adaptation for an entirely free state; it is not proof that a new flow implementation is shorter.

## 3. Necks: admission versus optimization

Gate each candidate on its exact final ZIP set with full authoritative audit context. `td/audit.py:565–617` defines a connected smaller side with qualifying land area and a cut narrower than 10 km; unresolved search is not a pass. Keep connector semantics from `audit.py:532–559`: land alternatives are evaluated across represented states, not merely the induced planning graph.

A no-good excluding one complete invalid district set is safe for fixed geometry and audit inputs, but weak. It must exclude that exact set, not every district containing a witness or sharing a state support. A plain witness cut can be invalid when district area or other membership changes. Reuse existing verified NeckCut machinery where its assumptions apply; otherwise exact-set exclusions are an honest conservative pilot, not a promise of fast convergence. An unknown gate result supplies no infeasibility certificate and must not create a correctness cut.

Passing the gate establishes admissibility under current M1 semantics, not shape optimality. Claim optimality only when solver bounds and the retained cut domain justify it; mip_rel_gap=0 requests proof but does not make time-limited runs optimal.

## 4. Scale and coarsening

No evidence supports '600 vertices in minutes' or '150 clusters in seconds.' Flow has roughly O(K|E|) continuous arc variables plus O(K|V|) assignments and substantial symmetry. Root restrictions, bottlenecks, balance windows and solver bounds matter more than vertex count alone. A published benchmark's largest instance is not a universal tractability threshold; the inherited 1,511-unit claim was not source-verified here and should not guide an exact/coarse cutoff.

The genuine scoped experiment has not run. `td/spec.py:562–599` already accepts explicit graph vertices and edges. Extract filtering alone did not scope the preceding run. Also inspect zero-dollar land handling: build's `land` dictionary at lines 589–590 includes only extract-present vertices; authoritative neck area must not inherit that omission.

Coarsening restricts possible partitions and hides internal necks. Connected aggregates and proper edge-capacity aggregation preserve useful structural properties, but coarse infeasibility is not fine infeasibility. Coarse optimality is not fine optimality. Freeze full audit graph throughout. No evidence favors merging across the shortest borders; weak shared borders may be useful future district boundaries. Treat aggregation design as an experiment, not established recipe.

## 5. Smallest build answering the owner

Do not build the proposed coarsener and new optimizer together first.

1. Specify one generic regional partition input: shipped footprint, frozen dollars, [L,U], K, original-state identities, planning graph and full audit context. No channel-specific solver branch.
2. Scope NJ correctly and test coverage, zero-dollar vertices, immutable rates and audit connector context. Read the existing `_solve_group` root/body path to decide reuse versus a small standalone model.
3. Run one K=3 NJ pilot, using exact dollar windows and a declared cut-length proxy. Record build time, model size, time to first incumbent, bound, audit time and failures separately. Invalid/fallback drawings remain diagnostics.
4. If scoped existing machinery can expose that contract with little change, reuse it. If its plan/share/body machinery obstructs the direct problem, implement the minimal standalone connected partition model behind the same interface. Do not duplicate the audit or renderer.
5. Only after one valid pilot, compare adaptive geographic aggregates against connected spatial aggregates on NY under identical windows/K/budget. Retain PA K=3 and 4 and NY K=4 and 5 for global selection.

The '1 hour adapter versus 3–4 hour new model' comparison is unsupported. Existing code contains more of the proposed new model than the reply acknowledged. Scoping plus one valid pilot is the measurement that can justify either route. No implementation authorized by this review; sealing and any new search restrictions remain owner decisions.

LEARNED: Existing draw._solve_group already provides flow, connectivity-cut and neck-cut machinery; direct-model reuse merits inspection before a new optimizer.
LEARNED: Conditional on sealed Middle Atlantic and rule C, approximate IFA masses permit NJ K=3, PA K=3–4, NY K=4–5; global count coordination remains necessary.
DECIDED: Recommend a genuinely scoped NJ pilot before coarsening or a fresh optimizer; runtime and effort claims lack measurements.
