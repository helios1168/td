# Group 2 geography and contiguity design memo

Date: 2026-09-14
Status: implemented; bounded full-coverage Group 2 run independently proved infeasible
Author: Codex
Worktree: /Users/Shared/sv-ntlee/repos/td/.claude/worktrees/group2-flow-memo
Branch: worktree-group2-flow-memo
Base commit: 25b67ed4092935c57358097d2b7958937bf6bb28

**Recommendation: first test the existing flow formulation with bounds derived from the
six-unit cap, keeping every pair-distance constraint active.** Use the relaxed assignment to
guide a bounded repair search, then release all repair restrictions. This is a smaller change
than introducing column generation or a new solver.

This memo records the independent design delivered in the conversation. It incorporates a
repository-only downstream inventory and a bounded review of the flow proof. No other
frontier model's design memo was consulted.

## Evidence and provenance

The initial research review was read-only. The user later authorized implementation in this
worktree. Focused solver, acceptance, runner, and mapping tests were run. A bounded Group 2
repair run was later launched and stopped after the unrestricted National target was reported
infeasible in 0.300 seconds. The full 510-second experiment matrix was not launched.

The source review used
/Users/Shared/sv-ntlee/repos/td/.claude/worktrees/agy-math-review at the base commit above,
including its uncommitted Group 2 implementation. The implementation was recreated and extended
independently in this worktree. Historical source line anchors below refer to the inspected
source worktree and may have shifted in the implemented files.

Inspected material included the handoff, the aggregate run specification, and the relevant
symbols in level0, the Group 2 runner, initializer, symmetry and checkpoint helpers, the MILP
engine, full_plan, and plan_realise. No customer-level rows were displayed. No current aggregate
opportunity vector, full research-instance export, or relaxed solution vector was available
for direct validation.

All three handoff-cited macro-run directories were confirmed missing:

- battery/results/group2_macro_ca2_n14w11f21_20260914_run1
- battery/results/group2_macro_ca2_n14w11f21_20260914_run2
- battery/results/group2_macro_ca2_n14w11f21_20260914_run3_relaxed

The reported one-contact infeasibility, two-contact spatial timeout, full relaxed National
coverage of 8,613.4952, and 54-contact optimum remain handoff-reported evidence. They were not
independently reproduced.

Source SHA-256 fingerprints recorded when creating this memo:

~~~text
9e57b983c5c605395f56ac02b1bb5e00b3be75f5af329cf6a9711e9ee3f93a13  agy-job/reports/GROUP2_MEMORY_SESSION_HANDOFF.md
e39118b0375851a0210e4950b264c74ae2c59da6985540d7379e93ad3a70ad36  td/solvers/level0.py
d03e1893f843bff9cb3d2dd7dfc9a07f7eb8e65a407c3f1420149c951723fa1f  tools/group2_run.py
0e7a5e5c288ea12a8921f73fa2fca772c640bbca88354a174a2522aa45ed3705  tools/group2_symmetry.py
51993d6737146a3ec7ee31662567938dd3e13aa2e5ff7d58171b02204d118cf6  tools/group2_checkpoint.py
a4d73d965fc6bbebf17e0d74f641285707515f9ca5f43c4b986ab284e5793bdc  tools/full_plan.py
fc6dc390018bb09c29db423ff9398ea1de6d048fca0d5f9a66cebd4ec3403bec  tools/plan_realise.py
~~~

## Implementation status

The runner now supports the recommended repair path for the active planner-selected, exact-count,
supporting-state case. `--repair-from` accepts a compatible checkpoint, full-precision `z`/`y`
JSON, or `plan.json`. It makes full National coverage explicit for positive-mass planning units,
then runs contact-Hamming neighborhoods at radii 8 and 24 for 10 seconds each, followed by an
unrestricted 70-second solve. `--separator-fallback` enables the bounded business-and-distance
master with valid connectivity boundary cuts when repair ends without a candidate or proof.

The default `--flow-bounds tight` replaces the National SCF constants with 5 and 6 only after
checking that the model contains the exact per-slot six-contact rows. `--flow-bounds original`
keeps the prior constants for matched experiments. California defaults to two deterministic ZIP
macro-regions, parent-coupled purity, and two National contacts per child.

Every National candidate is checked from the solver's raw `z` and `y` values. Acceptance requires
the independent semantic checks and reconstruction against the complete hard-constraint matrix.
The run writes the target, relaxed reference, validation report, full-precision certificate,
progress, model hashes, and macro partition metadata under the output directory. Restricted
neighborhood infeasibility is never reported as target infeasibility.

After successful ZIP realization and the final geography, band, coverage, purity, and graph
membership gates, the runner invokes the existing `tools/plan_maps.py` and
`tools/plan_summary.py --no-cache`. The latter must produce `maps/summary.png`. These three files
are byte-identical to the mapping stack in the full-problem worktree:

~~~text
0462b01242eafe8c0375a4feddaafa1648378b3620c9b5533fb1e15528deba9b  tools/plan_maps.py
5c27cd2289cd2e61139f24333cdb0b757930bcc5cbf160a04ddab40bef8b0075  tools/plan_summary.py
6f50d92c9f9f0455ed15af5819470364b36f349c702bae699541c1119cae480d  tools/us_maps.py
~~~

The intended production command is:

~~~bash
TD_REPO=/Users/Shared/sv-ntlee/repos/td \
/Users/Shared/sv-ntlee/repos/td/.venv/bin/python3 -u tools/group2_run.py \
  --case choose --count-mode fixed --supporting-states \
  --macro-national-contacts 2 --flow-bounds tight \
  --repair-from RELAXED_REFERENCE.json --separator-fallback \
  --time-limit 180 --out FRESH_OUTPUT_DIRECTORY
~~~

Implementation validation completed with 136 focused solver, Group 2, and mapping tests, followed
by the repository runner with the pinned 2025 ZCTA shapefile: 944 passed, 0 failed, 0 skipped.
No `summary.png` was generated because the bounded Group 2 attempt failed before ZIP realization.

## Post-run verification

The launched case used exact counts N=14, WH=11, and FI=21, all 19 Group 2 states forced to
National, CONUS supporting states, full eligible National coverage, a six-unit district contact
cap, the 900 km pair-distance rule with the 1,200 km Washington override, and the nominal
National band [553.724691, 676.774623]. The radius 8, radius 24, and unrestricted repair models
all returned infeasible. The unrestricted result is decisive for that frozen target.

An independent verifier rebuilt the distance conflicts from the exported coordinates and policy,
then exhaustively enumerated maximal cliques in the distance-compatibility graph. For each required
unit it computed an upper bound on the total opportunity available to any distance-valid support
of at most six units containing that unit. Seven units cannot reach the district floor even before
connectivity, split caps, district count, and cross-district constraints are imposed:

| Unit | Maximum compatible opportunity | Shortfall below 553.724691 |
|---|---:|---:|
| CO | 548.754666 | 4.970024 |
| ID | 341.321233 | 212.403458 |
| MT | 263.275277 | 290.449413 |
| ND | 238.881152 | 314.843539 |
| NE | 282.167471 | 271.557220 |
| SD | 238.881152 | 314.843539 |
| WY | 341.321233 | 212.403458 |

Full coverage requires each listed unit to have positive share in at least one National district,
which forces a contact. Every such district must reach the lower band. Any one of the seven local
obstructions proves the complete target infeasible. Longer solves, original flow bounds, or the
separator fallback cannot repair this contradiction. The runnable verification is in
`tools/verify/group2_n14_distance/`.

## 1. Diagnosis

The reported relaxed solution establishes projected business feasibility, not geographic
feasibility. A concrete formulation weakness appears in build_level0: flow capacities use
\(|V|-1\), and root supply uses \(|V|\), although a district contacts at most six units. These
constants allow unnecessarily diffuse fractional roots and flows in the LP relaxation.
Tightening them could improve search substantially, but that performance claim is a hypothesis.
The unchanged spatial problem might still be infeasible. The geographic instance and original
relaxed vector are needed to distinguish these possibilities.

Source: td/solvers/level0.py:195, build_level0.

## 2. Recommended mathematical method

Let \(B\) contain the frozen business constraints: exactly 14 National districts, full eligible
National coverage, prescribed bands, \(0.05z_{vj}\le y_{vj}\le z_{vj}\), six planning units per
district, parent purity, existing split rules, and each California child contacting at most two
pure National districts. Preserve the 19-state priority list, with Colorado still eligible as
supporting territory. Do not reinstate the historical required-20 case.

The handoff's nominal National band is \([553.724691,676.774623]\). The effective-band issue in
Section 9 must be settled from the exported rows before interpreting experimental feasibility
or infeasibility. The formulation below assumes a single consistent frozen band contract.

Full coverage must be explicit. The existing cover rows are upper bounds; maximizing coverage
and stopping at an arbitrary incumbent does not establish full coverage. For the handoff's
eligible National units, impose

\[
\sum_{j=1}^{14}y_{vj}=1,
\]

with exported channel eligibility and prior-coverage semantics determining the precise rows.
These equalities define the handoff's full-coverage target. Adding them is not an equivalent
reformulation of the broader staged planner, which can choose partial pure-National coverage.
The equivalence claim concerns flow tightening after this target model has been fixed.

### Tighten the existing connectivity formulation

Replace each undirected adjacency edge with two directed arcs. Retain binary contacts
\(z_{vj}\), binary roots \(r_{vj}\), and nonnegative flows \(f_{abj}\), imposing

\[
\sum_v r_{vj}=1,\qquad r_{vj}\le z_{vj},
\]

\[
f_{abj}\le5z_{aj},\qquad f_{abj}\le5z_{bj},
\]

\[
z_{vj}-6r_{vj}
\le
\sum_{a:(a,v)}f_{avj}-\sum_{b:(v,b)}f_{vbj}.
\]

Also reduce flow variable upper bounds to five. More generally, use \(q-1,q\), where \(q\) is
a proven contact bound for the affected slots. Do not apply six to slots without that bound.
For optional slots, retain the existing root equation \(\sum_v r_{vj}=u_j\); all 14 National
slots in this target are used.

### Keep distance conflicts explicit throughout repair

Construct

\[
F=\{\{a,b\}:\|p_a-p_b\|_2>D_{ab}\},
\]

using the implementation's projected coordinates and distance calculation. Here \(D_{ab}=1200\)
km for a pair involving Washington and \(900\) km otherwise. Enforce

\[
z_{aj}+z_{bj}\le1
\quad\text{for every }\{a,b\}\in F,\ j.
\]

Washington's override does not relax distances between the other states in its district.
Do not substitute a geodesic, route-length, or radius rule.

Optional conflict-clique inequalities \(\sum_{v\in Q}z_{vj}\le1\) are valid strengthening but
unnecessary for the first experiment.

### Use the relaxed solution as a repair target

For its contacts \(\bar z\), define

\[
H(z)=
\sum_{\bar z_{vj}=1}(1-z_{vj})
+\sum_{\bar z_{vj}=0}z_{vj}.
\]

Minimize \(H\) as a nonconstant search objective. Try temporary neighborhoods \(H\le8\), then
\(H\le24\), then remove the bound entirely. Reoptimize all National districts together. Every
contact and share may move; no relaxed geographic grouping becomes an anchor. Counts,
coverage, bands, purity, eligibility, geographic policies, and contact limits remain fixed.

Once feasibility exists, moved opportunity

\[
M(y)=\tfrac12\sum_{v,j}w_v|y_{vj}-\bar y_{vj}|
\]

can be a secondary objective, implemented with standard absolute-value epigraph variables.
Do not preserve the reported 54-contact optimum as a hard constraint: geography may require
more contacts.

### California remains coupled

Preserve parent-purity rows across CA1 and CA2, and explicitly request
--macro-national-contacts 2. Both children count separately toward six.

Current planner_args removes the old CA=3 cap when California is split. It does not retain a
parentwide three-district cap, nor transfer that cap to either child. Adding it would change
the current model. The two child caps can allow California to contact four distinct pure
National districts.

## 3. Preservation proof and safe symmetry

For any connected support \(S_j\) of at most six units, choose a root and a spanning tree.
Send each nonroot vertex one unit of flow along its root path. A tree arc carries its
downstream subtree size, at most five. Nonroots have net inflow one; the root sends
\(|S_j|-1\le5\). Thus every connected support admits the tightened flow representation.

Conversely, suppose a selected component contains no root. Both endpoint capacity constraints
force all flows crossing from that component to unselected units to zero. Selected vertices
in another component have no adjacency edge to it. Summing its balance inequalities gives

\[
|C|\le0,
\]

a contradiction. Therefore the selected support is connected.

These flows represent contact connectivity, not opportunity transportation. Fractional shares
cause no problem: every selected contact receives at least 5 percent, and no zero-share
connector is introduced.

The flow reformulation leaves \(z,y\) and every business row unchanged. Keeping every conflict
row preserves the diameter policy. It therefore preserves the projected feasible set of the
frozen full-coverage target, provided roots and flows carry no additional restrictions or
costs that would prevent the spanning-tree representation.

Reuse canonicalize_slot_symmetry, which chooses the lowest-index contacted unit as root:

\[
z_{sj}\le\sum_{t\le s}r_{tj}.
\]

Any connected support can be rerooted there, so this removes representation symmetry without
changing territory membership. Respect the helper's checks for anchored or priced roots and
custom root/flow constraints.

Retain mass ordering only among interchangeable slots. Disable it if introducing slot-specific
fixed neighborhoods, unless all associated labels are consistently permuted. Do not additionally
order geographic roots across districts: that ordering need not agree with mass ordering.

For the Hamming search, use a consistent mass-canonical labeling of the relaxed target and
candidates, or remove mass ordering in both matched experiments. Distance from the relaxed
assignment is a heuristic preference. Report movement after matching interchangeable district
labels so relabeling does not masquerade as territory movement.

Source: tools/group2_symmetry.py:62, canonicalize_slot_symmetry.

## 4. Pseudocode

~~~text
load frozen aggregate instance and relaxed contacts/shares
validate business semantics and relaxed business feasibility
build reference model with all hard rules and explicit full coverage

for formulation in [original flow bounds, six-unit flow bounds]:
    retain every distance-conflict row
    apply existing safe root canonicalization
    use the same nonconstant contact-change objective

    for radius, seconds in [(8, 10), (24, 10), (unrestricted, 70)]:
        solve with all business and spatial constraints active
        record raw solver status, bounds, nodes, and elapsed time

        if an integral candidate exists:
            reject nonfinite or materially fractional input
            independently check contacts, shares, and geography
            reconstruct spanning-tree roots and flows
            check against the untouched reference MILP
            if both checks pass:
                retain candidate and stop feasibility search

        if infeasible:
            if radius is restricted:
                record neighborhood infeasibility only
            else:
                export model and begin certificate verification

if neither formulation supplies an accepted candidate:
    try bounded connectivity separation described in Section 7

freeze an accepted National assignment
attempt Wealth 11 and FI 21 within separate budgets
proceed to ZIP realization only after the complete state-plan gate
~~~

The relaxed point is not a valid full-model warm start. Only independently checked points should
enter the production checkpoint path. A prior neighborhood's feasible point may seed the next
only after checking it against that next model.

## 5. Bounded experiment matrix

These are proposed future experiments, not runs performed during this review.

| Experiment | Limit | Decisive output |
|---|---:|---|
| Export and validate instance, effective rules, and relaxed point | 30 s | Consistent research instance or named missing/contradictory fields |
| Recheck spatially relaxed full-coverage model | 30 s | Business-feasible witness or discrepancy with the historical result |
| Distance-only restoration | 60 s | Witness, verified infeasibility, or no incumbent |
| Connectivity-only restoration, tightened flows | 60 s | Same three outcomes |
| Both families, original flow bounds | 90 s | Matched baseline using the pseudocode's neighborhood schedule |
| Both families, tightened flow bounds | 90 s | Accepted geographic witness or comparative search evidence |
| Connectivity-separation fallback | 90 s total | Checked witness, infeasible master, or recorded cut-loop progress |
| Certificate/conflict verification when relevant | 60 s | Verified artifact or incomplete verification |

Maximum National investigation budget: **510 seconds**, including preprocessing, model
rebuilding, and checking. Missing input stops the ladder; regenerating missing runs is not
silently added to this budget. Use a global deadline and shrink solve limits to reserve checking
time within each cell.

Stop a feasibility cell at its first independently accepted witness. Use identical instance
hashes, objectives, symmetry settings, thread counts, seeds, and neighborhood schedules for
the matched comparison. Keep two threads per process; do not resize HiGHS's process-global
thread pool during a run.

Record model dimensions, presolved dimensions, LP objective, fractionality, first-incumbent time,
node count, primal/dual bounds, and maximum validation residuals. For diagnostic incumbents,
also record connected components and forbidden pairs.

A tightened-model success after a matched baseline timeout supports the formulation-weakness
hypothesis. It does not prove the original formulation could never solve. Two timeouts resolve
neither feasibility nor the hypothesis. No bounded experiment guarantees a decisive result.

After National acceptance, allow **60 seconds each** for Wealth and FI with National frozen.
A later failure concerns extension of that particular National plan. It is not proof that every
National plan fails. Preserve National's fingerprint across those stages. Any later repair that
reopens National must be explicit, bounded, and followed by renewed acceptance checks.

## 6. Independent validation and certificates

Use two complementary checks:

- A semantic checker derived directly from the aggregate instance: exact counts, channel
  eligibility and coverage, minimum shares, nominal and effective bands, parent purity, split
  caps, child contact caps, six-unit counts, connected components, and every forbidden pair.
- A matrix check against the untouched full target model. reconstruct_vector already constructs
  spanning-tree flow witnesses; check_point checks rows, bounds, and integrality.

Check finite values and raw integrality before reconstruction, because reconstruction thresholds
contact values. An accepted result must not depend on clipping or renormalizing invalid shares.

Retain full-precision values. Record the numerical tolerances and both normalized and
opportunity-unit residuals. Six-decimal plan.json shares are insufficient as the sole acceptance
evidence. A serialization discrepancy should trigger comparison with the original vector, not
an enlarged business band. The implementation plan must document the checker tolerances before
runs, including the conversion from normalized band rows to opportunity units.

Store a local certificate bundle containing:

~~~text
instance and model hashes; variable/row maps; exact run settings
full-precision z, y, u and reconstructed r, f
per-district support, spanning tree, mass and distance margins
coverage, purity, split and contact-cap residuals
semantic-check report and original-MILP-check report
raw solver status, primal/dual bounds, time and node count
restriction scope and any generated cuts
~~~

Distinguish outcomes explicitly:

- **Feasible incumbent found:** both acceptance checks pass. Optimality is unnecessary.
- **Proved infeasible:** verified evidence applies to the unrestricted frozen target, or to a
  valid relaxation whose infeasibility implies that result.
- **No incumbent within the limit:** no feasibility conclusion.

Preserve raw status separately from incumbent availability; HiGHS documents time-limit and
infeasibility statuses separately.
[HiGHS status documentation](https://ergo-code.github.io/HiGHS/dev/structures/enums/#HighsModelStatus)

A floating-point solver log is reproducibility evidence, not an independently checkable
mathematical proof. For stronger infeasibility evidence, use an exact LP Farkas certificate
where applicable, or a verified MIP proof for the exported model. Preserve the coefficient
representation so a certificate is tied to the actual target rather than rounded output.

For an LP expressed as \(Ax\le b\), with variable bounds included, a checkable Farkas witness is
\(\lambda\ge0\), \(\lambda^\top A=0\), and \(\lambda^\top b<0\). LP infeasibility of a relaxation
proves target infeasibility. LP feasibility does not settle integer feasibility.

SCIP documents exact solving and VIPR certificate checking, including presolve and
certificate-completion qualifications; installed support would need verification before use.
[SCIP certificate guidance](https://www.scipopt.org/doc/html/FAQ.php)

A smaller targeted artifact can enumerate every connected, distance-valid support of size at
most six containing a mandatory unit. If every support's total available opportunity is below
the district floor, that unit cannot be covered. The enumeration must be complete; a partial
search supplies no such certificate. If the requested certificate cannot be checked within its
budget, report incomplete verification.

Do not reuse the historical Colorado bound as a current certificate without checking its
graph, unit mapping, and assumptions against the CA1/CA2 instance. Colorado remains eligible
supporting territory, and full coverage includes any Colorado opportunity eligible under the
frozen target.

Sources: tools/group2_checkpoint.py:71, reconstruct_vector;
td/solvers/level0.py:795, check_point.

## 7. Failure modes, ZIP risks, and fallback

The tightened formulation may still have a weak relaxation, or the instance may require
extensive contact changes. The unrestricted final neighborhood prevents repair-radius failures
from being mistaken for global infeasibility.

The first fallback is a business-and-distance master with connectivity separated externally.
Remove flow and root rows, including any root-canonicalization rows, and fix unused auxiliary
variables to zero or remove them. For a disconnected selected component \(C\), selected
\(a\in C\), and selected \(b\notin C\), add

\[
z_{aj}+z_{bj}-1
\le
\sum_{v\in N_G(C)}z_{vj},
\]

where \(N_G(C)\) is the external vertex boundary.

Any connected support containing both endpoints must select a boundary vertex. At the
disconnected incumbent, the left side is one and the right side zero. Thus the cut is valid
globally and excludes that defect. Add cuts for all observed components, deduplicate them, and
retain every distance row.

Within the 90-second fallback budget, repeatedly solve the current master for at most ten
seconds, inspect every returned integer candidate, append violated cuts, and continue. Reserve
time for validation. If a slice returns no integer candidate, record that outcome and use any
remaining time on the same master. Do not claim convergence from a limited number of rounds.

This loop is exact at integer acceptance. It need not solve each intermediate master to
optimality. Keep all cuts across restarts; a timeout or restricted-neighborhood infeasibility
remains inconclusive. Unrestricted master infeasibility implies target infeasibility because
all generated cuts are valid for the target.

Neither flow tightening nor separation establishes ZIP realizability. Relevant risks include
indivisible ZIP opportunity, several districts competing for the same border passage, and
5-percent bridge shares that cannot supply a connected ZIP path.

Export intended support-tree edges, actual cross-border ZIP adjacencies, candidate border seeds,
missing graph vertices, and district band margins. Use these as realization guidance. Rejecting
an entire state support requires proof that every admissible realization fails, not one failed
cut heuristic. A ZIP connectivity failure at one fractional allocation does not by itself
justify a no-good cut forbidding all allocations on that support.

Current realization also needs explicit acceptance controls:

- Group 2 omits --band-slack, leaving the realizer's default extra slack active. Strict
  experiments should explicitly use zero.
- Repair uses "no worse excess" guards, which do not guarantee band feasibility.
- The realizer can return successfully while reporting disconnected or out-of-band districts.
- ZIP component checks must account for assigned ZIPs absent from the graph.
- The state and ZIP band checks must use the same resolved effective-band contract.

After realization, independently verify the complete ZIP graph, coverage, bands, purity,
counts, staffing tolerance, and required staffing/FEFx audits. Use the pinned geometry vintage
and model graph. Keep the separate 5-percent staffing tolerance distinct from the minimum
contact-share parameter.

## 8. Ranked alternatives

| Rank | Approach | Assessment |
|---|---|---|
| 1 | Six-unit flow bounds, active distance conflicts, bounded joint repair | Smallest identified formulation change; preserves the existing solver and validation path |
| 2 | Business/distance master with connectivity cuts | Removes flow variables and root symmetry; restart overhead and repeated disconnected incumbents may dominate |
| 3 | Complete connected, distance-valid support enumeration with a share-allocation master | Attractive because supports contain at most six units; larger implementation and potentially many supports |
| 4 | Fixed regional decomposition or additional macro-regions | May simplify geography, but can exclude valid cross-region solutions or change planning-unit semantics |

Support enumeration would require a master that allows shared units and allocates continuous
shares, enforcing the 5-percent minimum, coverage, purity, and contact limits. It is not ordinary
state set partitioning. Infeasibility of a restricted column pool proves nothing about omitted
supports. A complete support formulation can be exact; heuristic generation alone cannot
certify global infeasibility.

Additional macro-regions should follow failure of the smaller methods. Parent purity and
deterministic ZIP membership alone do not guarantee equivalence when the six-unit cap counts
children. Any such proposal must identify the changed planning grain explicitly.

## 9. Minimal implementation plan

Begin with typed, aggregate-only ResearchInstance, CandidateWitness, and ValidationReport
records. Export business rows, planning graph, coordinates/conflicts, parent mapping, macro
provenance, and the full-precision relaxed assignment.

The likely implementation surface is:

| File or symbol | Proposed responsibility |
|---|---|
| tools/group2_run.py:151, constrain_problem | Preserve exact counts, parent purity, and explicit two-contact child caps |
| tools/group2_run.py:365, planner_args | Preserve/export the current split and band-break semantics; expose the research flag |
| tools/group2_run.py:404, make_accelerated_runner | Invoke target export, bounded research orchestration, and the acceptance gate |
| td/solvers/level0.py:195, build_level0 | Change flow capacities, root coefficient, and flow variable bounds using the proven cap |
| tools/group2_symmetry.py:62, canonicalize_slot_symmetry | Reuse safe within-district root canonicalization |
| tools/group2_checkpoint.py:71, reconstruct_vector | Reuse spanning-tree witness construction after raw input checks |
| td/solvers/level0.py:795, check_point | Reuse original-model row/bound/integrality acceptance |
| New aggregate checker module | Independently validate all semantic constraints and emit the certificate report |
| td/solvers/level0.py:606, append_row | Reuse only if implementing the separator fallback |

Add targeted small-graph equivalence and invalid-witness tests when implementation is
authorized. Include connected supports at the cap, disconnected supports, forbidden-pair
bridges, fractional-contact rejection, CA sibling purity, two-contact caps, slot relabeling,
coverage deficiencies, and serialization round trips. Do not change a signature before
checking its references.

### missing_context

- **Effective upper bounds:** band_break can add contact-dependent allowances above nominal
  \(U\). With California macros, TX/NY/FL retain that mechanism; current masses were not
  inspected, so active allowances are unknown. Export actual coefficients. If any allowance
  is positive, reconcile the handoff's literal upper-band requirement with existing semantics
  before claiming unchanged-model equivalence or infeasibility.
- **Original witness:** the missing run directories prevent direct validation of the reported
  relaxed assignment and its complete settings.
- **Exact research instance:** the full aggregate graph, masses, parent mapping, eligibility,
  priors, effective bands, and original vector must be supplied under one instance hash.
- **Certificate tooling:** installed support for exact MIP proof production and checking has
  not been inspected.

### learned

- The existing flow constants ignore the six-unit cap.
- The current runner valid() does not constitute a geography or full-coverage acceptance gate.
- California macro splitting removes the old CA=3 cap; the explicit per-child pure-National
  limit is separate.
- State-plan connectivity and ZIP-level connectivity require distinct acceptance checks.
- Full-coverage equalities specify the handoff's target, while the existing planner's coverage
  upper bounds permit a broader set of plans.

### followups

- Export a consistent research instance and verify the missing relaxed witness.
- Resolve effective-band semantics from actual rows before any feasibility claim.
- Implement the independent acceptance checker before changing solver behavior.
- Make ZIP repair slack explicit and require final ZIP/staffing audits.
- Retain immutable National assignment provenance during Wealth and FI extension attempts.

Proceed first with the six-unit flow reformulation and the **510-second experiment ladder**.
Accept it on a doubly checked geographic incumbent; establish infeasibility only with correctly
scoped verified evidence. Otherwise report **no incumbent within the limit** and use the bounded
separator fallback. No opportunity bands, counts, purity rules, contact minima, or geographic
policies should be loosened to obtain an accepted result.
