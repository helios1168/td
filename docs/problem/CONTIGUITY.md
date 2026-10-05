# Contiguity (M1): a brief for owner review

Draft, 2026-10-05 (#106). It states the contiguity requirement, how td lost it and what the
literature offers, so the M1 experiment lanes (#108, #109, #114, #116) start from the record.
Nothing here is settled until the owner approves it on #106 and triage moves it into `PROBLEM.md`
or `UNKNOWNS.md`. `docs/problem/MANDATES.md` holds M1 itself; this brief does not restate or change
its row.

**Sources.** The history comes from six read-only recon seats and their synthesis, checked by an
independent citation audit; the literature from five researcher seats and their merge, checked by
an independent quote verifier that fetched every source. All of it is gitignored on m5 under
`runs/plan_2026-10-04/contiguity/` (`CONTIGUITY_HISTORY.md`, `AUDIT.out.md`,
`lit/LITERATURE_CONTIGUITY.md`, `lit/VERIFY.out.md`, `IMPACT.md`, `MANDATE.md`). §7 lists what the
audit and the verifier changed.

**Citations.** `path:line` is on `main`; `<sha>:<path>` is a historical commit; `archive:` means
`git show archive/pre-support-2026-09:<path>`. A session is a pi session id on m5 with a message id;
session times are UTC, commit times CDT. Papers are cited by key and result and listed in
`docs/REFERENCES.md`. Tags: **[proved]**, **[tested]**, **[claimed]**, **[policy]**; a **[note]**
is this brief's own observation, unverified.

**Owner provenance.** The record has four kinds of owner evidence, and this brief keeps them apart:
a *typed owner turn*; a *structured pick* (the owner chose an option an agent wrote); an
*owner-account comment* (posted from the shared GitHub account, composing session unknown); and an
*agent-recorded decision* (an agent wrote "decided by the user" in a doc or memory). Where none of
the first three exists, the brief says "no owner quote found".

## 1. The requirement

### 1.1 M1 (owner, 2026-10-04)

The owner set M1 on 2026-10-04 CDT, in structured picks and typed approvals recorded 2026-10-05
04:29–04:34 UTC (session `01a109e4`, ask `2b50dbdb`, answer `e3c90e3a`, approval `23b1e5a8`). The
owner's words, as `docs/problem/MANDATES.md` records them:

- **Graph:** "the drawn 2025 TIGER ZCTA polygons. A district is connected when it looks connected
  on the map."
- **Adjacency:** rook, "a shared boundary of positive length; a single touching point does not
  count."
- **Water:** "crossings count only through a committed connector list (bridges, tunnels, ferries)
  that the owner reviews once."
- **Coverage:** "zero-opportunity ZIPs are territory. Every CONUS ZCTA gets a district in every
  channel, and the ledger, not a display fill, assigns it."
- **Tolerance:** "none. Any detached piece beyond the connectors fails the map."

A shared boundary shorter than the scorer's thin-link threshold counts as connected and stays a
looks defect. The model plans and draws on the same polygon graph (OD2, answered 2026-10-04). A map
with a detached piece is ineligible **[policy]**.

Why it matters, in the owner's typed words: "This has been the defining central theme of this repo
and project from the start." (2026-10-05 02:39 UTC, `01a109e4`, `037ab820`), and "These items
should be treated as though they were a divine mandate that must be strictly adhered to."
(04:25 UTC, `16f426b0`).

### 1.2 Rulings since M1

| ruling | owner's words or source | date |
|---|---|---|
| **Multipart ZCTAs.** One ZCTA is one node, and its own parts always count as connected. Adjacency between ZCTAs counts through any part. A separate drawn piece caused only by a multipart ZCTA is a visual defect, not an M1 failure. Measured the same day: 1,429 of the 33,300 CONUS ZCTAs are multipart, and 348 have more than 10% of their area outside their largest part | owner-account comment on #106 recording the owner's ruling, sent to #108's worker; the owner's own words are not in the inputs | 2026-10-05 |
| **Splits are counted by polygon ownership.** A district owning any ZCTA of a state has split it, zero-opportunity ZCTAs included | `docs/problem/PROBLEM.md` "Looks first (restated 2026-10-05)"; #91 | 2026-10-05 |
| **OQ6.** "A district's part of a unit is not required to be connected." M1 is whole-district connectivity; requiring each share to be connected on its own is a restriction, not a consequence of M1 | owner-account comment on [#52](https://github.com/helios1168/td/issues/52#issuecomment-5866293503); `docs/lenses/COUNCIL_2026-10-05.md` finding 9 (E13) | 2026-09-28 |
| **With η > 0 the master's s\* and δ\* do not bound M1 maps.** They bound only the drawings that follow the master's family, modes, η and caps; which master certifies floors is open (#110) | `docs/lenses/COUNCIL_2026-10-05.md` findings 14–16; `PROBLEM.md` | 2026-10-05 |
| **Ledger coverage.** The ledger owns only the extract's ZCTAs today, about 3.7k of 33,300; owning every CONUS ZCTA in every channel is #116. Until then #108 sizes pieces after the display fill, labelled so | #116 body (owner 2026-10-05) | 2026-10-05 |

The follow-on issues: #108 builds the polygon graph and makes a detached piece fail the audit and
the scorer (running); #109 draws today's best plans with a contiguity-aware realizer; #114 moves the
master's unit graph and supports to the polygon graph; #116 makes the ledger own every ZCTA; #112
decides what gives way when a share cannot be drawn connected.

### 1.3 Where a district can break

A disconnected `whole` unit stops the run (`td/spec.py:33-34`, OQ6). So on the graph a run uses,
every whole unit is connected, and a district can break only through its shares of split units. A
district is connected exactly when the union of its whole units and its shares is connected. One
sufficient condition is that each share is connected and touches the part of the district it was
planned next to; it is not necessary, because a share may be in two pieces that are joined through
another state (`lit/R1.out.md` §4; finding 9) **[note]**. Two consequences:

- M1 becomes a condition on the 13–22 split states of a map, each divided among a few districts.
  Shares in two adjacent split states can depend on each other, so those states form one problem.
- The master's corridor floor (S27, `docs/MODEL.md` §4.2) addresses a split unit that is a cut
  vertex of its support, for example NY inside {NJ, NY, CT}. It does not bind a split unit that is
  a leaf, for example FL in {GA, SC, FL}: FL's share can be connected and still not touch GA or SC
  (recon seat L2's reading of the IMPACT examples) **[note]**.

### 1.4 Where we are (measured 2026-10-04)

Every one of the 75 drawn runs under `runs/` was rescored for detached ZIP pieces (`IMPACT.md`,
`measure/pieces.py`, m5). The measurement is on the 2025 Voronoi rook graph after the looks scorer's
display fill, not on the polygon graph M1 names, so it is a baseline, not an M1 verdict; #108's
rescore replaces it **[tested]**.

- **0 of 75 runs are ZIP-contiguous.** All 31 runs within ±10% have a detached piece, and 30 of
  them have one of at least 0.2τ. The median run's largest piece is about 0.4τ; the largest is
  0.52τ.
- The five runs whose largest piece is under 0.05τ all fail balance (worst 14–21%).

| map | pieces | ≥ 0.05τ | largest detached piece |
|---|---|---|---|
| tier 1 `ne_okks_s13` (13 splits) | 4 | 2 | WH_07: 176 ZIPs of FL, 0.45τ |
| tier 1 `ne6_clean` | 11 | 5 | national_09: all of GA + SC, cut off from its FL share, 0.48τ |
| tier 1 `ifa_49` | 12 | 8 | IFA_12: 29 NJ ZIPs, 0.29τ |
| deck A | 6 | 5 | FI_07: all of CT, 0.45τ |
| deck B | 6 | 5 | FI_06: CT + MA ZIPs, 0.52τ |
| deck C | 8 | 4 | FI_02: LA + MS, 0.47τ |

**Mechanism.** Each large piece has the same form: a district holds whole states plus a share of a
split state. The master counts the district connected because the split unit borders the whole
states. The realizer then places the share by the power diagram, which has no requirement to touch
those states. #81's Hess arm drew the same plan with a largest piece of 0.06τ against the power
diagram's 0.47τ (`docs/RESULTS.md`), which points at the realizer rather than the plan; neither arm
enforces ZIP contiguity **[tested]**.

**What each kind of result is worth now.** Unit-level facts (split sets, forced-split floors,
component floors, $ per district) remain valid as lower bounds. Achievable balance and "13 splits"
are optimistic under M1, by an unknown amount. Every drawn map, shortlist tier and deck option fails
M1 (`IMPACT.md`).

## 2. The history

### 2.1 Timeline

Dates are 2026. Ids C01–C36 are the recon's catalogue (`CONTIGUITY_HISTORY.md` §3).

| date | what happened |
|---|---|
| 08-27 – 08-31 | Two-wholesaler split on ZIPs. Exact contiguity machinery built and tested on synthetic planar graphs (C01–C13). On 08-28: "decision 2026-08-28: contiguity is a hard constraint" (`589c62b:battery/code/contig_methods/base.py:20`) |
| 09-01 – 09-02 | Sold-ZIP graph has 547 components; contiguity dropped for distance-based (Hess) assignment; FRAME records the waiver with a reopening condition (§2.3) |
| 09-05 – 09-14 | State atoms, ZIP repair, `contiguous_cut` (adopted first for WH, then all seven bundles: archive `docs/memory/decisions/full-problem-2026-09-11.md:31-33, 40`), connected state supports (C17–C27) |
| 09-25 – 09-30 | #52 picks the minimal realizer; OQ6 and OD2 answered; the clean slate archives the waiver row; support master, realizer, ledger and list-only audit land (C28–C31) |
| 10-01 – 10-05 | First real run lists 872 pieces; deck, #81, looks scorer, #85 swap rule (C32–C34) |
| 10-04 – 10-05 | Rescore: 0 of 75 runs contiguous. The owner confirms the 09-01 drop and settles M1; mandate register, watchdog, #106–#109 |

### 2.2 Approaches tried

Sizes and times are the seats' reports, not rerun.

| group | what it was and what it showed | status today |
|---|---|---|
| Exact pair-era methods, C01–C13, synthetic planar graphs | SCIP minimum-separator cuts (C03), flow models (C05, C06), CBC lazy constraints (C04), a rational exact branch-and-bound (C10), an N-way separator design (C13). Pairs of 8–464 ZIPs; five 169–464-ZIP pairs certified to gaps of 1.2e-6 to 3.9e-3 in 2,400 s. CBC gave false certificates; the N-way solver was never built | Archived; a starting point for a k-way realizer, not a drop-in engine. Its contract checked connectivity per component, which M1 must not inherit |
| Real ZCTA graph, C14 | A TIGER rook loader: 33,791 ZCTAs, 90,429 edges, 190 components. **No run on the real graph was found** | Recipe survives; #108 rebuilds the graph |
| Distance assignment, C16 | Hess balanced transport, then power cells; no adjacency rows | Its geometry is today's realizer |
| Unit-level contiguity, C17–C19, C25–C28 | State atoms; the minimum-splits MILP with state flow; connected support enumeration; corridor, border, count and Menger rows. A memo: "Neither flow tightening nor separation establishes ZIP realizability" | Today's master; necessary, not sufficient |
| ZIP repair and cuts, C20–C24, C27 (Voronoi) | `contiguous_cut` took WH_10 from 10 pieces to 1. A bridge seed took pieces from 15 to 2 but grew a share 14× and was reverted. Unguarded healing could print success while its check failed | Not ported; ideas without a guarantee |
| Today's pipeline, C29–C34 (Voronoi) | Border-aware centres, transport LP, forest rounding, one guarded repair; whole-unit stop; list-only audit; swap rule A; looks scorer; #81's Hess planner | No ZIP-connectivity guarantee anywhere (#108, #109) |

### 2.3 Waivers and relabellings

Each row is a point where contiguity was set aside, narrowed or replaced by something easier to
meet. "No owner quote found" means the seats' bounded searches found none, not that none exists.

| date | waived or relabelled | owner's words | what followed |
|---|---|---|---|
| 09-01 | "adjacency contiguity is dead"; "no adjacency contiguity, no glue re-export" (`d50bd42`). An agent argued compactness was what contiguity "was standing in for" (`d2d0c60:docs/channel_note/channel_note.tex:134-144`) | Typed, 2026-10-05: "ah yes my 2026-09-01 commit was indeed my call. i intended to continue on with the contiguity piece but had dropped it for simplicty [sic] sake of the rewrite" (`01a109e4`, `e4be725f`). No owner quote found for the compactness argument | No return trigger. The argument rested on the sold-ZIP graph; the full ZCTA graph was named and never run |
| 09-02 | "Adjacency contiguity is not required … Reopenable only by the full-ZCTA-graph experiment" (`7359c6e:docs/FRAME.md:305`) | No owner quote found; the row names "user" | #62 built the all-ZCTA graph on 09-28; nobody reopened the row |
| 09-06 | "that count must be zero", where the count was ZIPs outside their own power cell (`feaa1bc:docs/OPTIONS_power-cell-contiguity.md:38`); "visual map contiguity is the bar, exact graph contiguity is not required" (`a3846b2:STATE.md:8-15`) | No owner quote found; recorded as stakeholder and sponsor decisions | State atoms shipped although maps measured that day had pieces of 48–73% |
| 09-09 – 09-10 | "The split's contiguity graph stays the Voronoi rook adjacency" (`docs/memory/geo/zcta-geometry.md:7`); the restriction recast as "an extent cap … not sold-zip contiguity per channel" (`6568e99:PLAN.md`) | No owner quote found; memory and the decisions log attribute both to the user | M1 reverses the graph; the grain of "contiguous" stayed ambiguous |
| 09-11 | WH_03 kept its CT piece: "the fix belongs at level 0 … or WH_03 keeps its CT piece. Left open for the user" (#7); #14 asked for a ruling | No owner answer found | #14 archived unanswered on 09-28 |
| 09-14 | "100% rook contiguity by construction" (`9776c75:MATH_REVIEW.md:171`); a constant "100% Contiguous (0 violations)" (`9776c75:summary.csv`) | No owner quote found | Corrected 09-20 (`764f667`). A 09-20 lens relay still said "ZIP contiguity was measured infeasible and dropped" (m2 session `01a0c221`) |
| 09-25 | "Minimal rewrite, about 300 lines (Recommended)" over "Exact MILP per split unit … flow-based contiguity and exact bands"; then "Contiguity, within the final tolerance (Recommended)" and "Border centres now, graph cut on a trigger (Recommended)", whose fine print said "Beyond that the piece stays and is reported with its cause." | Structured picks (`01a0d9a9`, 15:39 and 15:57 UTC). The owner then typed: "under what conditions or cases would a planned share not be able to be drawn? wouldn't we want to resolve this at the planning stage then?" | No exact realizer. Repair is bounded by the band. The trigger "more than 2 pieces per map" (#52 rev 6) became "the threshold the owner sets" (rev 7); none was set |
| 09-25 – 09-30 | Audit spec: "Pieces are listed with their cause and their share of the district's mass" (`docs/MODEL.md:651-652`); the audit returns `listed` or `pass` (`e1f3d9a:td/audit.py:225-255`) | No owner quote found approving a disconnected map as eligible | #69's 10 fixture runs passed with 22 pieces; all 75 scorecards say `listed` |
| 09-28 | OQ6: "A district's part of a unit is not required to be connected." OD2: "Voronoi rook (Recommended)", "Placed extract ZIPs (Recommended)" | Owner-account comment on #52; structured picks (parent session `01a0e73e`, #57) | OQ6 is within-unit and consistent with M1; OD2 is superseded by M1 |
| 09-28 | The clean slate (`ce9f282`) drops the waiver row and its reopening condition | No owner quote found for losing that row | The trigger was lost |
| 10-01 | Owner, typed: "so no channel has to be fully connected across the map. … the districts themselves must be contiguius" (`01a0f177`, `6a63ded6`). Agent: "Agreed, and the model already works that way." (`cb9a7c10`). Council: "855 of 872 audited pieces are display artifacts … 17 pieces are real" (`COUNCIL_2026-10-01.md:70-73`) | Typed owner turn; no owner quote found for the council count | No ZIP-level recheck; the reply was wrong even on the Voronoi graph. Pieces counted, not weighed |
| 10-02 – 10-05 | #81: "ZIP contiguity is not enforced in either arm"; #93: contiguity pieces counted on the display fill in a plain sum of defects; #85: "the owner has not ruled; A is the conservative default" (orchestrator) | Structured picks "Support rules held", "Display-fill pieces", "Plain sum" (all "(Recommended)"). On #85 the owner typed: "wait why would a district ever have a detached piece? contiguity is a hard constraint here. elaborate" (`01a108ca`, `29e358f3`) | Experiment scope and metric choices, not consent to disconnected maps; #85 rule A is pending, not an owner waiver |

Not waivers: the 08-30 two-tier acceptance changed an optimality tolerance only, and choosing a
heuristic realizer does not by itself waive what the final map must satisfy.

### 2.4 How enforcement was lost: the design lesson

The 09-01 drop was a deliberate, temporary simplification by the owner, and the 09-25 picks were
explicit owner picks. Each later step was locally reasonable. What failed was the machinery around
them **[note]**:

1. **A deferral without an executable return trigger.** The reopening condition lived in a ledger
   row. When #62 met it, nothing fired; when the clean slate archived the row, the condition went
   with it. `docs/problem/MANDATES.md` and `tests/test_mandates.py` now keep every mandate and fail
   an expired deferral.
2. **Unit-level guarantees stood in for the drawn map.** Connected supports, corridor floors and
   whole-unit checks are necessary conditions. Several records called them sufficient
   ("by construction", "connected ZIP by ZIP") without a ZIP-level check.
3. **"Fail" became "list".** The audit spec listed pieces, the audit returned `listed`, and the
   scorer counted pieces without mass. No negative test had a detached district. #108 makes a
   detached piece a failure, pinned by broken fixtures.
4. **The owner's restatement did not reopen the requirement.** On 10-01 the owner said districts
   must be contiguous and was told the model already complied. A gate that runs on every map
   (#108) and a watcher that flags such reassurance (`WATCHDOG.md`) target this.

### 2.5 Records that still conflict with M1

- `AGENTS.md` trap 23 says the drawn map and "the contiguity model (the Voronoi rook graph)" are
  different tessellations and that a scattered-looking district "is not evidence of a contiguity
  failure". Under M1 the drawn polygon graph is the contiguity model. It needs an owner-gated
  revision once #108 lands.
- `docs/problem/BALANCE.md:41-42` says contiguity "is judged on a rook graph of Voronoi cells …
  not on the drawn ZCTA polygons".
- `docs/MODEL.md:651-652` lists pieces; #108 changes §9.
- Counts differ by convention: on `ne_okks_s13`, #93 reports 5 display-fill pieces and `IMPACT.md`
  4; WH_07 is 33 small pieces in the audit and one 176-ZIP piece after display fill; `ifa_49` has 7
  audit pieces and 12 after display fill. The three conventions (graph vertices, ledger ownership,
  display fill) are not yet reconciled (CU5).

## 3. The literature

Five researcher seats covered exact formulations (R1), split units and hierarchy (R2), power
diagrams and when cells are connected (R3), repair heuristics (R4), and adjacency, water and
practice (R5). Every quote below was fetched and matched at its source by the verifier
(`lit/VERIFY.out.md`); results the verifier could not check are tagged **[claimed]**. Times are not
comparable across rows: grain, K, objective, band, solver and hardware all differ.

### 3.1 Exact formulations and the largest instances solved

Connectivity is imposed exactly by flow (single- or multi-commodity), by separator cuts added
lazily, or by connected columns (branch-and-price). Each is exact on the graph it is given.

| method | largest instance solved, as reported | source |
|---|---|---|
| Cut and flow models, tracts | Indiana, 1,511 tracts, K 9, CUT in 13,435.36 s with extra time (Table 6, p.887). In one hour, all "solve instances as big as Kentucky (n = 1,115), but solve none of the larger instances" (§6.4, p.886) | `validi2022` |
| Cut-edge objective | "up to 532 census tracts to optimality in a one-hour time-limit" (§8) | `validibuchanan2022` |
| Exact separators, precincts | Iowa, n = 2,536 as seat R1 reports: "they solve in only five seconds" (p.22) | `jolly2026` |
| Branch-and-price | 95 instances solved, against 153 for a subtour model and 136 for flow (p.185) | `gliesch2023` |
| Commercial territory design | "up to 150 BUs and 8 territories" (manuscript p.26) | `salazaraguilar2011` |

- **Strength.** "P LCUT ⊆ P CUT = proj x P MCF ⊆ proj x P SHIR" (`validi2022` Thm 1, p.873):
  cuts and multi-commodity flow are equally strong, Shirabe's flow weaker. Separation is
  polynomial on a simple planar graph (Prop. 2, p.876).
- **The root LP is the bottleneck** (§7, p.887); California's LP took "five days" (§6.2, p.882),
  and "entirely new ideas may be needed" for Texas (5,265) and California (8,057) (§7).
- **Contiguity can be cheap:** "the exact same 21 tract-level instances are solved to optimality
  whether or not contiguity is imposed" (§7, p.887).
- **Only integer points need separating** (§6, p.881), so a solve–check–cut loop that rejects every
  disconnected integer solution is exact.
- **Single-commodity flow is competitive** (`validibuchanan2022` §8; `borndorfer2023`
  **[claimed]**). Shirabe's model is fragile: "Because of the big-M constraints, numerical stability
  issues rear their head on larger instances" (`jolly2026` §2.2.1, p.6). The districting literature
  has no exact branch-and-price (`buchanan2023` §5.3, p.11).
- **Compactness does not deliver contiguity:** "Explicit contiguity constraints are still needed."
  (`jolly2026` §5, p.24).

No source reports an unrestricted connected partition of about 33,000 units solved to proven
optimality.

### 3.2 Restricted models: fast, but they exclude connected plans

Tree, distance and DAG constraints root each district and require each assigned unit to have an
assigned predecessor. Outputs are connected, but "X(A tree) ⊆ X(A dist) ⊆ X(A dag) ⊆ X"
(`jolly2026` Prop. 1, p.9): each excludes connected plans.

- **Scale.** With Iowa's four districts "rooted at the four corners of the state" on 175,199
  blocks, the DAG model reached its optimum over the restricted set in 122.65 s, while "Only the
  exact model failed to solve, terminating before finding a feasible solution or even solving the
  root LP relaxation" (pp.21–24, Table 7).
- **Cost.** At most 28.74% of 7,097 enacted districts satisfy the DAG constraints (Table 2). Under
  tight balance "the tree-based constraints are too restrictive, to the point of being worthless"
  (§4.3, p.20).
- **Use.** A first pass, with a complete fallback that drops the restriction. `shahmizad2025`:
  "Any x that satisfies these DAG constraints gives connected districts, although the converse is
  not true." and "If we are unsuccessful with the DAG constraints, then we resort to using the a,
  b-separator constraints in callback." (p.767).

### 3.3 Split units: coarse plan, fine drawing

This is td's structure: a coarse plan over units, then a fine assignment inside split units.

- **Cluster → Sketch → Detail** (`shahmizad2025` §4). Detail lets a split county's tracts "be
  assigned only to districts 3, 5, and 9" and imposes contiguity on whole districts. "Even though
  the percentages from the sketch are ignored, the number of county splits will remain the same"
  (§4.3, p.766): shares are recomputed. Sketch takes "less than one second in 99% of cases"; seven
  of 140 instances needed "ad hoc tweaks" (§5, p.768). No isolated Detail size or time was found.
- **Maximum whole counties** (`shahmizad2026`, preprint). "Of the 140 instances, 126 were solved by
  our approach using default settings" (p.27), in about 24 hours; Florida stays open at [56, 57].
  Failures get an "'inconclusive' or 'fail'" status (§3, p.9), and bounds come "only for full plans
  that are generated entirely by the code" (§5.3, p.23).
- **td's failure, described** (`ruskey2025`). "It is clear that the resulting unit-level solution
  is discontiguous, even though the gray and pink portions within L 45 are themselves contiguous."
  (p.49). Constraint (3.60) "ensures that the connected portion of district j within L i is
  adjacent to the portion of district j outside L i in the already-assigned plan" (p.52). The
  disaggregation widens the band, "α = β = √(1+0.01) − 1" (p.52). Table 3.3 (p.67): 73.3 s (IL)
  and 362.2 s (PA) at K 17 on block groups, subproblem gaps of 1% and 10% (p.66), and failure rates
  of 31.0% (IL) and 51.4% (PA); what a failure counts was not checked.
- **Attachment by construction** (`carter2020` App. C.1, p.18): "Draw the whole districts such that
  the remainder of the county is connected and contains at least part of the border with c_i's
  parent in the spanning tree."
- **Coarsening is safe one way** (`swamy2022`): "merging a pair of units is equivalent to imposing
  a constraint that those two units have to be assigned to the same district" (§4.1, p.25).
  Restricted fine columns "discount many districts that would pass an eyeball test" (`gurnee2021`,
  arXiv p.5).

Three conditions recur **[note, from R1 and R2]**: contract only what is forced to one district and
connected on the required graph, keeping every genuine edge; solve jointly over split states that
share a district; and require the whole district, not each share, to be connected (OQ6). Ruskey's
(3.60) is sufficient only when the fixed part and each share are connected, and it excludes a
district whose share is joined through another state.

### 3.4 Power diagrams and transport: when cells are connected

- **Power cells fragment on non-convex domains:** "connectivity might get lost when X is
  non-convex" (`brieden2017` §3.1, p.15). In their experiments 51 municipalities (0.46%) were
  preassigned to restore connectivity, "due to the non-convexity of the states in general and
  particularly due to 'holes' in the state areas" (§4.3, p.24).
- **Fixed centres.** Squared distances produce "compact but disconnected territories" and are "not
  appropriate for the case of fixed centers" (`kalcsics2005` p.15, on Marlin). td's master fixes
  which districts enter each split state **[note]**. `cohenaddad2018`'s districts are "not
  guaranteed to be connected" (p.13); `eppstein2017`: "it may be necessary for some districts to be
  disconnected" (p.1); `hojati1996` reports a discontiguous district **[claimed]**.
- **The transport forest is not geography.** A basic solution has "at most p − 1 splits" and a split
  adjacency that "is cycle-free, i.e. a forest" (`kalcsics2005` p.19). The forest bounds rounding
  error, not pieces on the map.
- **Shortest-path diagrams are connected, with conditions.** With linear graph distance from fixed
  sites the cells are star-shaped (`brieden2017` Thm 10, p.19), but the relative-interior optimum is
  "crucial" (p.19), other distance transforms lose it (Thm 11, p.21), rounding may move "whole
  fractionally assigned branches" at a balance cost (p.20), and "elongated districts appear"
  (pp.29–30). `carlsson2013` gives a continuous analogue **[claimed]**.
- **R3's port extension is unproved.** Seat R3 proposed transport inside a split state with cost
  d(P_i, z), the distance from the ZIPs where district i's whole states touch it, extending Thm 10
  to port sets. There is no written proof; it needs a relative-interior optimum (a basic solution
  can lose it before rounding), positive weights (zero-opportunity ZIPs fall outside), a connected
  fixed body and existing ports **[note]**.

### 3.5 Repair heuristics

None found comes with a guarantee.

- `riosmercado2021` repairs connectivity first, but "Naturally, being a heuristic, there is no
  theoretical warranty that a feasible solution is obtained after the split resolution has taken
  place." (p.13); in their tests "none were found infeasible" (§5.5, p.20).
- `biswas2023` keeps "the largest-sized connected component" and reassigns the rest (§4.3, p.16);
  "a higher proportion of disconnected subgraphs, on being repaired, results in arbitrarily-shaped
  districts" (§5.6, p.21). `ahuja2015` assigns excess components to the least-active neighbour and
  then rebalances (§3.3).
- Recombination merges two districts and cuts a spanning tree; when no balanced edge exists "we draw
  a new tree" (`deford2021` §4.3.1), so a failed search is not infeasibility. `jin2026` keeps the
  largest component in composite moves (§3.2.2).
- For checks, "the point-adjacent units included in R(v) should not be considered adjacent"
  (`king2015` pp.428–429).

### 3.6 Adjacency, water and practice

- **Rook is the standard:** an edge when parcels "share a border of nonzero length (e.g., it is not
  enough to meet at a point)" (`validi2022` §2.3, author PDF p.6). North Carolina: "No point
  contiguity shall be permitted" ([2021 criteria](https://redistricting.lls.edu/wp-content/uploads/NC-20210821-adopted-redistricting-criteria.pdf)).
- **Water:** "districts divided by water are contiguous if a common means of transport (like a
  bridge or ferry route) connects the two sides" ([All About Redistricting](https://redistricting.lls.edu/redistricting-101/where-are-the-lines-drawn/)).
  The papers join disconnected graphs with least-weight or "least cost" edges (`validi2022` §6.1;
  `shahmizad2025` §2.2, p.759); M1 allows only owner-reviewed connectors, so neither transfers.
- **Graph connected is not map connected:** a multipart water tract meant "a district that is
  connected in the contiguity graph may not be contiguous on the map. In fact, this happened in our
  experiments." (`validi2022` §6.1, author PDF p.25). The owner's multipart ruling (§1.2) settles
  this for td.
- **ZCTAs:** "2020 ZCTAs may form noncontiguous areas (e.g., islands or enclaves)" ([Census
  guidance](https://www.census.gov/programs-surveys/geography/guidance/geo-areas/zctas.html), 2020
  product); `grubesic2006`, 2000 vintage, agrees. Water and corner adjacencies "can result in
  non-planar graphs" (`anderson2026` §2.3), which matters for polynomial separation.
- **Practice.** Redistricting samplers hold contiguity hard (`mccartan2022`, Methods). Commercial
  tools penalise or repair: `ahuja2015` multiplies the objective by "(1+α(n_con(P)−k))" (§3.2).
  Esri's documentation says territories "are contiguous" when no balance variables are set and
  nothing about contiguity when they are (ArcGIS Pro 3.5, "Create a territory solution").

### 3.7 Applied to td

These are the seats' inferences, not measurements on td data **[note]**.

**Master (whole states).** Keep the coarse master; the literature at scale decomposes the same
way. Build its unit adjacency from the polygon graph and approved connectors (#114), since a
Voronoi-derived contact can promise a border that the polygon graph does not have. Treat the
master's support as the districts *allowed* in a split state, not as fixed shares: Detail recomputes
shares, so an allowed contact can vanish, and splits must be counted on the drawn map. A no-good cut
back to the master is valid only for plans proved to have no M1 drawing over every share they
allow; a timeout, a restricted-model failure or an arbitrary root licenses no cut (R1, R2;
`COUNCIL_2026-10-05.md` finding 9).

**Split-state realizer.** The closest fit is a joint mixed-resolution Detail:

- vertices: one super-node per connected component of each district's fixed (whole-unit) ZIPs, plus
  every ZIP of every split state, zero-opportunity ZIPs included;
- edges: every genuine polygon-rook or connector edge between them;
- each split-state ZIP goes to one district its unit's support allows; masses sum exactly to the
  band;
- whole-district connectivity by integer separator cuts or single-commodity flow, where each vertex
  demands one unit of flow rather than its opportunity, so zero-opportunity ZIPs cannot escape it;
- solved jointly over split states that share a district;
- "connected and feasible" reported apart from "proved optimal".

Sizes are small next to the literature's (California has about 1,700–1,800 ZIPs in a handful of
districts), but nobody has timed this model on ZIPs, and whether HiGHS through highspy offers a
lazy-constraint callback is unchecked (CU1).

**Post-repair.** Component repair, recombination of two adjacent districts, and composite moves can
polish an M1 map or generate incumbents. They guarantee nothing, can unbalance and distort shape,
and every result must pass the #108 gate.

## 4. Options, ranked

How M1 is achieved is an open owner decision (`WATCHDOG.md` layer 4; #112 decides what gives way
when a share cannot be drawn connected). This ranking is a recommendation, not a decision. Every
option needs the same base: the polygon graph and the gate (#108), ledger ownership of every ZCTA
(#116), and the master on the polygon graph (#114). The ranking puts first what is exact and
certifiable, since M1 has no tolerance, then what the literature has shown at a relevant scale,
then fit to td.

| rank | option | exact? | evidence | risk |
|---|---|---|---|---|
| 1 | **Joint mixed-resolution Detail on split-state ZIPs** (§3.7), on the master's fixed plan, with separator cuts or unit-demand flow; #109 arm 1 | Exact and complete on the polygon graph for the fixed support | Shahmizad's Detail at tract and block scale; Ruskey's mechanism; exact separators at 2,536 precincts in 5 s | Untimed at ZIP scale; coupled states make larger joint problems; a fixed plan may have no drawing |
| 2 | **Rooted DAG or tree restriction as an accelerator inside 1**, with complete fallback that drops the restriction | Restricted; exact only through the fallback | 175,199 blocks in 122.65 s (restricted); Shahmizad's DAG-then-separator pattern | Roots must sit on genuine ports; multiple entry stretches; a share-only district has no port |
| 3 | **Master–realizer loop**: when 1 proves a fixed plan has no M1 drawing, cut it from the master and re-solve (combinatorial Benders); #109 arm 2 | Exact if each cut rests on a proof over every share the plan allows | `shahmizad2026` handles failures with an inconclusive status; finding 9's conditions | Valid cuts may be weak; what gives way (another split, a wider internal band, a moved share) is #112 |
| 4 | **ZIP-grain planning of split states** (#102), with hard connectivity rows added | Exact if the rows are complete | #81's Hess arm: largest piece 0.06τ, but no connectivity rows | #102 today has a split penalty and no connectivity rows; the largest unrestricted exact solves are ~1.5k units |
| 5 | **Port-distance transport (R3)** as a relaxation or warm start for 1 | No guarantee; the port extension is unproved | `brieden2017` Thm 10, for fixed sites only | Relative interior, zero weights, rounding; must never carry a connectivity label |
| 6 | **Component repair heuristics** (largest-component retention, recombination, composite moves) to polish or seed | Heuristic | `riosmercado2021`, `biswas2023`, `deford2021` | No guarantee; shape damage; balance drift |

Archived code that may shorten 1 and 2: the pair-era SCIP separator engine (C03), the flow models
(C05, C06), the N-way separator design (C13), and `contiguous_cut` (C21). None is a drop-in engine,
and module paths and dependencies are incomplete (CU8).

## 5. Unknowns

Numbered CU here; the lander numbers them from U59 at triage, or folds one into an existing U.
Grades: **E** settleable by computation, **B** needs a business answer, **T** needs a theorem.

| id | unknown | grade |
|---|---|---|
| CU1 | **Tractability of option 1.** For `ne_okks_s13`, deck A/B/C and `ifa_49`: the joint Detail's size per coupled group of split states, solve time and gap in HiGHS. Does highspy expose a lazy-constraint callback, or must it be single-commodity flow or a solve–check–cut loop? | E |
| CU2 | **Which of today's plans have an M1 drawing** at their fixed support within ±15%, and at what internal band (extends U54, U55; #109 arm 1) | E |
| CU3 | **Valid master cuts.** What infeasibility proof licenses removing a master plan when shares are continuous: a cut keyed on the support, on the share polytope, or on the joint group of coupled states? How weak are such cuts (finding 9; #109 arm 2) | T |
| CU4 | **Ports.** On today's maps, how many districts have no fixed body touching a split state they hold a share of (share-only districts, or entry only through another split state), which defeats rooted models and R3's ports | E |
| CU5 | **One count.** The M1 rescore on the polygon graph with full ledger ownership (#108, #116): pieces by mass per map, and the reconciliation of the audit, realizer and display-fill conventions (s13: 4 or 5 pieces; WH_07: 33 or 1; IFA 49: 7 or 12) | E |
| CU6 | **Connectors.** Which water crossings the owner approves (#108 proposes the list), and how many districts' connectivity depends on one | B |
| CU7 | **Multipart ZCTAs in the audit.** How the gate tells a piece caused only by a multipart ZCTA's own parts (a visual defect) from a detached district (an M1 failure), and how many districts on today's maps show the first | E |
| CU8 | **Archived code.** Can the pair-era separator and flow engines (C03, C05, C06, C13) and `contiguous_cut` (C21) be recovered and run against today's master, and do they need SCIP or run on HiGHS | E |
| CU9 | **R3's port extension.** Prove or refute that brieden2017 Thm 10 extends to port sets, state its conditions, and measure whether HiGHS's optimum keeps path closure after crossover | T/E |
| CU10 | **The price of M1.** On today's maps, how many split units and how many points of balance an M1 drawing costs against the unit-level plan; the size of the gap g under M1 (extends U56, SU9) | E |

## 6. What we want back

- **From the owner, on #106:** approval of this brief, or corrections. Owner decisions it points to
  but does not make: how M1 is achieved and what gives way (#112), the bounding master (#110), the
  connector list (#108), the revision of trap 23.
- **From #108:** the polygon graph, the connector proposal and the M1 rescore (CU5, CU7).
- **From #109:** option 1 on the shortlist maps, with arm 2 if a plan cannot be drawn (CU1–CU4,
  CU10).

## 7. Sources and corrections

**The citation audit** (`AUDIT.out.md`, an unadvised Opus pass) opened 30 of the history's
citations plus 9 more: 28 of the first 30 confirmed, no misquote, no misattributed owner quote. This
brief applies its corrections:

- The list-only audit is at `e1f3d9a:td/audit.py:225-255`; the synthesis's 305–337 are `main`'s
  line numbers.
- "100% Contiguous (0 violations)" is in `9776c75:summary.csv`, not `MATH_REVIEW.md`; "100% rook
  contiguity by construction" is at `9776c75:MATH_REVIEW.md:171`.
- `OPTIONS_power-cell-contiguity.md` is cited at `feaa1bc` (lines 38 and 421–422); the 08-30
  decision is in `research/contiguity/RESULTS.md`; the OD2 comment names parent session `01a0e73e`.
- `contiguous_cut` was first adopted for the WH bundle only (`full-problem-2026-09-11.md:31-33`)
  and later for all seven bundles (`:40`).
- The owner's 2026-10-05 confirmation is quoted verbatim, "simplicty" marked [sic].

**The quote verifier** (`lit/VERIFY.out.md`, an unadvised Opus pass) checked 219 quotes: 205
verified, 3 with the page unchecked, 1 at a wrong location, 1 wrong, 9 unverifiable. This brief:

- does not quote `validi2022`'s Indiana passage, which opens p.869, not p.868 as the seat had it,
  and takes the Indiana result from Table 6, p.887;
- quotes `salazaraguilar2011` as the author manuscript reads, "8 territories", not "eight";
- cites `validibuchanan2022` and `salazaraguilar2011` by section or manuscript page, since the
  journal pages could not be checked;
- quotes nothing from `borndorfer2023` (the ZIB report's wording could not be confirmed),
  `hojati1996` or `carlsson2013` (closed access), and tags their results **[claimed]**;
- adds `ruskey2025`'s failure rates (31.0% IL, 51.4% PA), which the seat did not report;
- cites `validi2021` under the registry key `validi2022` (same DOI, 10.1287/opre.2021.2141).

OpenAlex flagged none of the 42 works checked as retracted (queried 2026-10-05); `jolly2026`,
`ruskey2025` and `gliesch2023` have no OpenAlex record. Documents and vendor pages were not checked
against OpenAlex.
