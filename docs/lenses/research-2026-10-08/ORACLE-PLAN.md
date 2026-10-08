# Oracle review: revise before implementation

## Inherited decisions

- **Absolute M1; attractive shapes; minimize original-state splits, then cuts.** County alignment unnecessary. Coarse geography is a proposal mechanism, not permission to redefine splits.
- D3/E2 dollar windows remain binding; WIFI uses **global** WIFI dollars/global WIFI K.
- F1 reserves **MD alone** as one IFA district; F2 permits IFA K 46–55. Main-map total remains 48–54.
- Plan-only. Sealing remains unapproved. Four solver processes maximum. No 58-map re-render.
- Supervisor agreed: narrow S0, preserve full audit graph, defer exhaustive trials until valid pilot.

## Diagnosis / contradiction check

**Division speed-up was never tested.** `td/spec.py:562–599` accepts explicit planning graph, but extract filtering alone leaves global vertices. `run.py:199–202` fills undrawn territory with fallback. Previous timeout therefore establishes neither failure nor runtime of genuinely scoped realization.

Other corrections:

- NY’s roughly $5.47B admits at most **five** $1B-floor districts. Six cannot work. Splitting $1.913B into two also cannot meet two $1B floors without transferring surrounding mass.
- “At most one carved piece” is neither contiguity nor rule C. Rule C counts **original split states**, not coarse units.
- County grouping already uses centroid-distance growth (`pieces.py:125–148`); “no spatial preference” is false. Its preference demonstrably failed owner’s visual test.
- Changing to border-length minimization alone does not prevent enclosed districts, tendrils, or holes.
- Exhausting free-state lists gives no unrestricted optimality certificate unless master domain and relaxation validity are established.

## 1. Contiguity guarantee

Section 1 needs this invariant:

> Each admitted district owns a fixed, nonempty ZCTA set within an explicit regional/channel footprint. Every relevant `(ZCTA, fine channel)` cell has exactly one owner, including zero-dollar cells. Each district passes authoritative connectivity and neck checks on that exact set. Assembly never adds/removes ZCTAs, changes routing, or merges district identities.

**Two graphs, different jobs:**

- Planning/drawing: induced subgraph on explicit regional footprint, selected from **shipped vertices**, never extract rows.
- Audit: unchanged full authoritative polygon graph, connector registry, borders, original-state identities and land areas.

Critical reason: connector width uses land alternatives throughout district’s represented states, not merely its owned ZIPs (`td/audit.py:532–559`). Restricting audit graph can remove an alternative and falsely treat connector as wide.

Actual gate semantics:

- Connectivity follows ZCTA adjacency, approved connectors included (`district_pieces`, `audit.py:431–441`; `geo.py:917–936`).
- Neck: **one connected smaller side**, approximately 5%–50% of district land area, cut width below 10 km. Remainder need not be connected. Dollars never determine neck eligibility (`audit.py:565–617`).
- Width rounding is conservative; do not introduce new tolerances.
- Unresolved neck search is **not admissible**. Helper returns `unknown`; full audit counts unresolved neck items against pass (`wholeplan.py:67–85`, `audit.py:910–918`).
- Multipart ZCTA remains one graph vertex. These routines do **not** independently certify every polygon component. Preserve current authoritative representation; do not promise stronger geometric guarantees or infer planarity.

**Merge hazards beyond coverage:** colliding district IDs join unrelated sets; routing places different fine channels of one planning-channel ZIP into different districts; connector/geometry versions differ; seam filling changes ownership; zero-dollar completion changes areas and therefore neck thresholds.

Use namespaced IDs and hashes of ZIP set plus gate inputs. Re-gate after every ownership change and after merge. Full `check_m1` also checks routing, duplicate ownership and missing rows (`audit.py:807–910`); local district checks cannot replace it.

## 2. Coarse units: evidence and recommendation

Read-only inspection of 2025 reference and polygon edges, approved connectors included:

| Division | ZCTAs | CSA coverage | CBSA coverage | metdiv coverage |
|---|---:|---:|---:|---:|
| New England | 1,846 | 64.9% | 79.3% | 15.5% |
| Middle Atlantic | 4,257 | 76.7% | 89.6% | 28.9% |
| East North Central | 5,211 | 68.5% | 78.3% | 11.5% |
| West North Central | 4,939 | 34.0% | 52.1% | 0% |
| South Atlantic | 5,284 | 57.1% | 77.7% | 17.6% |
| East South Central | 2,500 | 53.6% | 68.9% | 0% |
| West South Central | 3,806 | 49.4% | 69.5% | 7.2% |
| Mountain | 2,621 | 38.2% | 68.6% | 0% |
| Pacific | 2,836 | 64.1% | 90.4% | 25.8% |

Middle Atlantic has **18 CSA, 66 CBSA, eight metdiv and 150 county codes** represented. Draft estimates and “roughly district-sized” assertions lack support.

**Remainder is not one connected unit.** CSA remainders have four components in NY, six in PA; CBSA remainders have five and six. Named units also disconnect after assigning indivisible ZCTAs to reference geographies. Nineteen of 150 Middle Atlantic county groups disconnect on this graph.

Try two controlled proposals:

1. **Adaptive geography hierarchy:** state-intersected CSA → CBSA → metdiv where available → ZCTA refinement. Split every named/remainder group into connected components. Preserve components’ original state and parent labels. Expand oversized or unsuccessful units; never require geography labels to remain indivisible permanently.
2. **Connected spatial aggregation:** merge adjacent ZCTA groups within original states using existing border/centroid data, independent of administrative boundaries. Same solver, same gate; only proposal partition differs. Tests whether geographic labels help versus connected shape-oriented aggregates.

Start first proposal: existing labels make it cheapest. Second supplies meaningful comparison when owner rejects administrative outlines.

CSA/CBSA cross state lines: raw geography is **not** `state ⊃ CSA`. Intersect by state for proposed within-state cuts; retain cross-state metro identity as metadata.

Coarse-neck implication requires connected aggregates, additive areas, correctly summed border capacities and unchanged connector semantics. Otherwise even that one-way claim is unsafe. Coarse pass never replaces fine gate.

## 3. Channel-agnostic contract

Inputs need more than `[L,U]`:

- Explicit footprint, immutable original-state map, full-precision fine-channel dollar masses.
- Exact cell-routing policy, legal original-state split policy/rule C, F1 exception.
- Regional/global K constraints and boundary policy.
- Versioned planning graph, authoritative gate context, proposal partition.

**Routing is not proven binary.** `td/spec.py:411–414` supports national-absent fallback into channels holding WH/FI fine cells. Previous pure-versus-all-WIFI enumeration cannot be called “all combinations” without establishing allowed route catalog.

Resolve routing candidate and global WIFI `(M,K)` **before regional solve**; then WIFI gets common fixed window `0.85M/K…1.15M/K`. Global coordinator combines regional K choices and routing choices. Never reset WIFI mean locally.

Freeze dollar rates from full extract; subsetting must not renormalize national totals. `spec.py:660–669` currently constructs tau bands, while `wholeplan.py:106–115` optimizes delta. Neither implements proposed fixed-window contract unchanged.

## 4. Parallel plan and honest timing

Drop Cartesian product of every geography × K × division × channel. It multiplies duplicate work and compares different contracts.

Order:

1. Establish scoped-instance/gate/dollar correctness.
2. Full-precision mass and connected-component screens across allowed routing candidates.
3. Compare two proposal partitions under **identical routing, K/window and seed budget**.
4. Keep alternatives passing M1 and dollar windows; rank original-state splits/cuts, then inspect defects and shape.
5. Expand only promising variants across regions/channels; merge, audit, render, register.

Use four single-process jobs, **including gate solvers**; no nested four-worker pools. Background completion must notify. Unknown/fallback outputs are diagnostics, not accepted incumbents. Cache gates by immutable geometry/set identity.

S0 below: **approximately 4–8 engineering hours including tests**, contingent on adapter reuse; two-method pilot another **2–4 hours plus measured runs**. Estimates, not commitments. No evidence supports minute-long exact gates or ten-minute nationwide completion. A neck search alone allows 60 seconds per component.

Sealing, route catalog changes and budget increases need owner decisions. Geography labels as experimental proposals do not require new border policy. Keep existing process cap.

## 5. Suggested execution prompt — after approval only

Implement smallest experimental adapter; no channel-specific branch, solver framework or audit rewrite.

| Task | Files | Runnable acceptance |
|---|---|---|
| Explicit regional instance using existing `spec.build(..., graph=...)`; full audit graph separate; scoped cache keys | new `tools/exp/contig/division.py` | `tests/test_division.py`: Middle Atlantic has 4,257 shipped vertices, includes zero-dollar ZIPs, excludes outsiders; connector verdict matches authoritative graph |
| Fixed-dollar adapter and explicit routing contract; reuse existing rate helper | same adapter; reuse `tools/looks/score.py` | Mixed-rate aggregation exact; subset does not change rates; global WIFI window shared; MD-only waiver rejects MD+DC |
| Two proposal builders with connected-component decomposition | same adapter initially | Disconnected remainder splits; no duplicate/missing vertices; no invented adjacency; original-state counts unchanged |
| Admission and immutable merge | same adapter | Unknown rejected; duplicate IDs namespaced; missing/duplicate cells rejected; merged gate equals constituent checks when sets unchanged |
| One background pilot harness, notifications and artifacts | same adapter; documentation registration files | Cap four active solver processes; failed/unknown runs never marked accepted; manifests record scope, rates, gate identity and timings |

Do not modify `td/audit.py` thresholds. Reuse tests/runner conventions. No executor launch warranted before plan approval.

LEARNED: Scoped planning must retain full authoritative neck-audit context; connector widths depend on land alternatives across district states.
DECIDED: Recommend narrow S0 and two comparable proposal partitions; reject unmeasured exhaustive-matrix timing.