# Mathematical Review: National Channel Territory Design and Staffing

**Author:** Antigravity  
**Date:** September 14, 2026  
**Subject:** Support-based planning, discrete ZIP–channel realization, and staffing ([`docs/MODEL_FULL.md`](docs/MODEL_FULL.md)).
**Code-review baseline:** `agy-math-review-memo`, `426d912`. Sections 3–4 distinguish the implemented master from its downstream realization. Export checks in §3.6 are independent table audits, not fresh solver runs or ZIP-contiguity certificates. Proposed code changes are in [`PLAN.md`](PLAN.md); they are not implemented by this document. The `.tex` companion has not yet been synchronized.

---

## 1. Executive Summary & Problem Setting

The territory design problem formulated in [`docs/MODEL_FULL.md`](docs/MODEL_FULL.md) addresses the simultaneous partitioning of commercial sales opportunity across the 48 contiguous United States and Washington, D.C. ($S=49$ planning states) into $K$ balanced sales districts. Concurrently, it models the allocation of incumbent sales representatives across four fine business channels:
$$C = \{N_{\text{WH}}, N_{\text{FI}}, \text{WH}, \text{FI}\}$$
admitting seven permissible channel bundles:
$$\mathfrak{B} = \{N, \text{WH}, \text{FI}, \text{WH\_PLUS}, \text{FI\_PLUS}, \text{WHFI}, \text{WHFI\_PLUS}\}$$
where $N = \{N_{\text{WH}}, N_{\text{FI}}\}$, $\text{WH} = \{\text{WH}\}$, $\text{FI} = \{\text{FI}\}$, and $\text{WHFI} = \{\text{WH}, \text{FI}\}$.

A joint optimization of district boundaries, channel structure, and staffing would couple:
* Hard topological contiguity constraints on irregular graphs.
* Bundle-specific opportunity capacity bounds $[L_B, U_B]$.
* Nash welfare over gains determined by both district membership and representative assignment.

That joint problem is not what the support master solves. The committed commercial scenario table has $6,478$ ZIPs per scenario; the $33,791$-ZCTA nationwide crosswalk is a downstream geographic extension, not the master's optimization ground set. The master sees states and predefined macro units, including CA1 and CA2.

To make this computationally tractable, the operational architecture initially adopted a **three-level hierarchical decomposition**:
1. **Level 0 (Macro Planning):** A state-by-channel MILP solved lexicographically on the state rook graph $G_S$.
2. **Level 2 (Micro Realization):** A transportation LP (power diagram) per split state, followed by topological repair heuristics on the ZIP-level Voronoi cell graph $G_{\text{cell}}$.
3. **Stage 2 (Wholesaler Staffing):** A maximum-weight bipartite matching on logarithmic gains solved via the Hungarian method.

---

## 2. Legacy Architecture & Structural Failure Modes

### 2.1 The Legacy Sequence
* **Level 0 MILP:** Employed a single-commodity flow-tree formulation to enforce state contiguity ($r_{s,j} \le z_{s,j}$, flow conservation).
* **Level 2 Optimal Transport:** Partitions split states using semi-discrete power diagrams with Lloyd centroid updates, followed by discrete greedy frontier growth and bridging heuristics on $G_{\text{cell}}$.
* **Stage 2 Matching:** Bipartite matching on utility gains $g_{i,j}$ evaluated at the state-aggregation level.

### 2.2 Structural Failure Modes
1. **Large planning solves:** Historical multi-channel flow formulations reached 600-second limits. A timeout is not a proof of infeasibility or mathematical divergence.
2. **Power cells are not graph connectivity constraints:** Squared-distance transportation has a power-diagram interpretation before rounding. Intersecting cells with non-convex geography, sampling ZIPs, and rounding can produce disconnected district pieces.
3. **Repair and residuals:** The realizer permits configured band slack and can leave unrepaired pieces or unassigned cells. Slack alone does not establish either complete service or final capacity feasibility.
4. **Staffing timing:** State-share staffing treats book location proportionally within split units. Its gain matrix need not match the realized ZIP-level gains. A terminal match is needed to optimize staffing on those final districts.

---

## 3. Support-Based Planning and Discrete ZIP Realization

**Scope.** The support master replaces the flow-based planning formulation, not the ZIP realization layer. The scenario drivers still call `tools/plan_realise.py`, then perform additional fragment healing and residual-channel routing. "One sweep" means selecting all district supports and shares for one channel together. `tools/solve_global_multichannel.py` solves WH and FI separately; the scenario drivers also reuse previously solved channel plans and insert prescribed Western districts. There is no single master here jointly optimizing all channels, ZIP boundaries, and staffing.

### 3.1 Planning Units and Admissible Supports

Let $V$ be the planning units and $G=(V,E)$ their adjacency graph. `tools/group2_run.py::prepare_macro_regions` assigns each ZIP to one planning unit before optimization; a macro cut such as CA1/CA2 therefore has fixed ZIP membership, not merely a fractional California mass.

Support enumeration generates connected sets under a size cap and pair-specific distance limits:
$$\mathcal{S}_0=\{S\subseteq V:G[S]\text{ connected},\ |S|\le\bar{s},\ \|c_u-c_v\|_2\le D_{uv}\ \forall u,v\in S\}.$$
Here $D_{uv}$ is the maximum of the base distance limit and the configured overrides for $u$ and $v$. The reviewed entry points use size caps of 6 or 7 and distance overrides extending beyond 1,200 km. These are run parameters, not universal 900 km / six-unit guarantees.

The National support filter also removes combinations and explicitly appends supports, including the seven-unit New England-plus-NY support. Appended supports need validation against the declared rules; they cannot inherit every enumeration guarantee automatically. A connected support describes state/macro-unit contacts. It does not determine connected physical pieces inside split units.

### 3.2 The Implemented Master and Its District Decoder

For one channel or bundle $B$, let $M_v=M_v^B=\sum_{z\in Z_v}\sum_{c\in B}M_{z,c}$. The count $K$ and band $[L_K,U_K]$ are inputs. The code uses:
$$n_S\in\{0,\ldots,K\},\qquad t_{v,S}\in[0,1]\quad(v\in S).$$
$n_S$ is the number of districts using support $S$; $t_{v,S}$ is their **aggregate** share of unit $v$. These correspond to the code's `x` and `y`. The former binary-activation formulation did not describe this multiplicity.

For the full-coverage case, the intended coverage domain is the eligible unit set $V_B$. The principal rows in `tools/run_wifi_grid.py::solve_generic_channel` are:
$$\sum_S n_S=K,$$
$$\sum_{S:v\in S}t_{v,S}=1\quad(v\in V_B),$$
$$\eta_{v,S}n_S\le t_{v,S}\le1\quad(v\in S),$$
$$L_K n_S\le\sum_{v\in S}M_vt_{v,S}\le U_K n_S,$$
$$t_{v,S}\in\{0,1\}\quad\text{for units outside the configured splittable set},$$
$$\sum_{S:v\in S}n_S\le\operatorname{cap}_v\quad\text{for capped macro units}.$$

The generic grid solver uses $\eta_{v,S}=0.10$ at articulation vertices when $K\le14$, and $0.05$ otherwise. The separate `group2_support.py` and `solve_global_multichannel.py` routines use $0.25$ at articulation vertices and also add $t_{v,S}\le n_S$. These are different implementations, not interchangeable parameterizations of the note's former single model. In the generic solver an inactive support's positive-mass shares are forced to zero by its upper mass row; zero-mass shares lack that explicit activation link.

The generic solver adds coverage rows only for eligible units with at least one candidate support. It does not itself exclude ineligible vertices from the supplied supports. Thus complete coverage and domain exclusion require validation of the supplied support family; missing-support rows must not be silently treated as coverage proofs. `group2_support.py` additionally supports partial coverage of non-required units.

The implemented compactness objective is:
$$\min\ 0.001\sum_S\operatorname{Diam}(S)n_S.$$
`group2_support.py` also subtracts covered opportunity. With full coverage on the same ground set, that term is the constant $-\sum_vM_v$. There is no general per-unit assignment cost, Nash welfare term, or optimization of imbalance within the permitted band in this master.

The macro rule implemented above is a **contact cap**, not the earlier displayed pair-coupling inequality. An articulation-share lower bound is also not a pair-coupling rule and does not establish a physical corridor through the unit.

**District-instance decoding.** The generic scenario solver expands each active support into $j=(S,r)$, $r=1,\ldots,n_S$, with equal planned shares:
$$\bar y_{v,j}=t_{v,S}/n_S,\qquad \bar M_j=\sum_{v\in S}M_v\bar y_{v,j}.$$
It writes these to district slots and `state_shares.csv`. Consequently, integral $t_{v,S}=1$ does **not** imply whole-unit ownership by one district when $n_S>1$. Also, `solve_global_multichannel.py` currently repeats the aggregate shares without dividing by $n_S$ in its output decoder; its coverage validator can reject such repeated-support results. These discrepancies need code changes, not stronger claims in the theorem.

The master gives planning-level capacity bounds on a correctly decoded solution. It does not guarantee that the same masses are achievable with indivisible ZIPs. The connection to the final assignment is the separate procedure below.

### 3.3 From Planned Shares to Whole ZIPs

For each bundle, `td/channels.py::project` forms the scalar ZIP measure:
$$M_z^B=\sum_{c\in B}M_{z,c}.$$
`tools/plan_realise.py` then performs these steps:

1. **Prepare targets.** Read the district shares, compute masses on ZIPs with coordinates, and create an `other` pseudo-district for uncovered share. Residual shares at most $10^{-4}$ are treated as serialization rounding. `state_splits.realise` normalizes each state's targets to its placed mass.
2. **Assign unsplit units whole.** All placed ZIPs in a unit with one positive-share district receive that label.
3. **Solve a split-unit transportation relaxation.** Let $Z_v^p$ be the ZIPs with coordinates, $M_v^{B,p}=\sum_{z\in Z_v^p}M_z^B$, and $\widetilde y_{v,j}$ the normalized shares after the residual-column step, summing to one. For fixed centers, with $f_{zj}\ge0$:
   $$\min_f\sum_{z\in Z_v^p,j}M_z^B\|p_z-c_j\|^2f_{zj},\qquad
   \sum_jf_{zj}=1,\qquad
   \sum_{z\in Z_v^p}M_z^Bf_{zj}=\widetilde y_{v,j}M_v^{B,p}.$$
   On positive-mass ZIPs, a basic transportation solution splits at most $k_v-1$ ZIPs, where $k_v$ is the number of positive target columns, including `other` if present. This is a per-unit bound, not one global $K-1$ bound, and does not bound subsequent repairs.
4. **Round to one district label per ZIP.** `centers.assign` uses `X.argmax(axis=1)` and repairs empty required districts. Up to five Lloyd rounds refine the cut. The fractional matrix is not the delivered allocation.
5. **Optionally recut on the cell graph.** The scenario grids request `--split-cut contiguous` for N, WH, and FI. `contiguous_cut` seeds near adjacent district bodies, grows the district with the largest relative deficit, and assigns each claimed ZIP once. Unreached ZIPs retain their previous labels. This is a heuristic, not an exact integer transportation solve or a connectivity theorem.
6. **Complete missing coordinates and repair.** `channel.place_by_state` places coordinate-less ZIPs using state plurality with mass tie-breaks. The realizer repairs pieces subject to admissibility and a band-excess guard. Its guard is "do not worsen excess", not "make every district feasible".

For a bundle-level whole-ZIP label $b^B_{zj}\in\{0,1\}$, the realized target error is:
$$\Delta^B_{v,j}=\sum_{z\in Z_v}M_z^B b^B_{zj}-M_v^B\bar y_{v,j}.$$
These errors need measurement. Rounding, missing-coordinate placement, and repair do not impose $\Delta^B_{v,j}=0$.

### 3.4 Exclusive ZIP–Channel Ownership and Residual Routing

The final ownership grain is **one ZIP and one fine channel**, not an entire state, and not necessarily all channels of a ZIP together. Define the output indicators:
$$a_{z,c,j}\in\{0,1\},\qquad r_{z,c}\in\{0,1\},\qquad
\sum_j a_{z,c,j}+r_{z,c}=1.$$
$r_{z,c}=1$ denotes `other`. Complete service requires $r_{z,c}=0$ for every required cell. The cell contributes its full opportunity to its owner:
$$\widehat M_j=\sum_{z,c}M_{z,c}a_{z,c,j}.$$
These are the **final-output contract**, not extra rows currently solved by the master.

`plan_realise._claim_cells` maintains a unique-key ledger:
```text
cell_of[(zip, fine_channel)] = (district, bundle, representative)
```
It claims only unowned keys. Bundles with more business channels run first, so an earlier claim wins an overlap; losing bundles keep only unclaimed cells. The writer emits one row per ZIP and fine channel with the full source `M_cell`, never a fractional amount. This enforces exclusive ownership or residual status, but not necessarily complete service, original target shares, or full product-form bundle ownership after overlaps.

The optional `--sweep-zips` can claim remaining positive-mass cells for an existing district serving that state/channel, preferring adjacency and falling back to the largest holder. It reports groups with no candidate instead of proving they are covered. The reviewed varying-WIFI driver does not pass this flag; it uses additional post-processing instead:

* `run_wifi_grid.heal_assignment_contiguity` moves non-heaviest pieces of at most 250 ZIPs into neighboring districts. It changes whole ZIP labels within each bundle, with **no capacity or master-support guard**.
* `run_wifi_grid.merge_national_into_wh_fi` routes unassigned cells at a ZIP to its WHFI district if available; otherwise `N_WH` goes to that ZIP's WH district and `N_FI` to its FI district. A special rule attaches zero-mass California cells to an existing assignment at that ZIP. Cells with no destination remain `other`.

Residual routing is part of the channel policy. It can add national opportunity after WH/FI/WHFI capacity planning while retaining those original bundle names. A district's declared bundle and actual channel set therefore need separate reporting. When national falls back, its two fine channels may have different district owners; the combined national business-channel total is not an indivisible cell.

The source-channel export expands `N_FI` into National (Chase) and Wells FI with the same owner, and `N_WH` into Wells WH. This preserves one owner per source channel. The nationwide crosswalk is a later spatial extension and can retain unserved zero-opportunity ZCTAs.

### 3.5 Which Guarantees Survive to the Final Map?

| Property | What the current code establishes |
| :--- | :--- |
| Connected planning supports | Enumeration/checking on the state or macro-unit graph, subject to validating manually appended supports. |
| Master coverage and bands | On the modeled eligible ground set, for a feasible solution and a correct multiplicity decoder. |
| One owner per ZIP–channel | Unique cell ledger and one-row writer; residual `other` is a possible owner status. |
| Complete commercial service | A final residual check, not a consequence of the master alone. |
| Final capacity compliance | Must be recomputed from $\widehat M_j$ after all movement and channel routing. |
| Final ZIP connectivity | Must be checked on the declared ZIP graph after all movement; unsupported or missing graph vertices need an explicit verdict. |
| Staffing consistency | Requires one representative per final district and synchronized output tables; placeholder IDs are not a staffing optimization. |

The varying-WIFI and 48/49/50 grid drivers request **`--band-slack 0.1`**, widening the realizer's guard by $0.1\tau_B$, then run unguarded fragment healing and national routing. The final map therefore does not inherit a zero-slack band certificate. Positive articulation shares likewise do not prove ZIP-level connecting corridors.

"Sub-three-second global optimality" is not a theorem. The generic solver defaults to `mip_rel_gap=0.05`; the varying-WIFI driver requests 0.01 or 0.05 for new National solves. The other support entry points do not explicitly request zero relative gap. Feasibility checking, solver optimality to a tolerance, ZIP-level validation, and end-to-end runtime are different claims.

The grid's contiguity checker skips absent graph files and tests induced subgraphs that can omit assigned ZIPs absent from the graph. `run_vary_wifi_grid.py` also writes the literal `100% Contiguous (0 violations)` into the summary even when its separate check failed. A summary label is therefore not a certificate. None of these checks establishes Pareto optimality across scenarios.

### 3.6 Independent Checks of the Committed Exports

A read-only CSV audit at the review baseline found:

| Artifact / check | Result |
| :--- | :--- |
| `scenarios.csv` | 36 scenarios, 6,478 ZIPs per scenario, 1,166,040 rows. |
| Commercial primary key | Zero duplicate `(scenario, ZIP, source channel)` keys; all five source-channel rows present for every ZIP. |
| Commercial ownership | Zero `other`, blank, or unserved district labels. |
| Nationwide compressed long table | 6,082,380 rows, 33,791 ZCTAs per scenario, no duplicate keys or incomplete five-channel sets. |
| Nationwide residual | 88,380 unserved rows across the catalog; all have zero reported opportunity. |
| Representative-label consistency | 235 district–scenario combinations have multiple representative labels, affecting all 36 scenarios. |

The last discrepancy is consistent with fragment healing updating `district` but not `wholesaler`. The new grid assembly creates placeholder IDs (`R0001`, etc.) rather than running real-book matching. These fields must not be presented as verified optimal staffing.

This audit establishes the observed key/label properties of the committed exports. It does not independently establish conservation against the confidential source instance, final bands, ZIP connectivity, actual representative eligibility, or solver optimality. The raw run directories and solver environment were unavailable for a fresh end-to-end reproduction.

---

## 4. Unified Multi-Channel Architecture & Western Merged Realization

### 4.1 The Sparse Geography Paradox
The Western study uses $S_{\text{west}}=\{\text{CO},\text{ID},\text{MT},\text{ND},\text{NE},\text{SD},\text{WY}\}$. Its historical sizing reports about 431 descaled units in WHFI and 689 across all fine channels. These sparse markets motivate merged districts. Whether a standalone National district is feasible depends on its eligible neighboring units, band, and declared distance overrides; low density alone is not a proof of infeasibility.

### 4.2 Dedicated Regional Merged Channel (WIFI/WHFI)
The scenario drivers combine standalone channels with regional merged districts:
$$K=N+WH+FI+WIFI.$$
In `run_vary_wifi_grid.py`, Western district memberships for WIFI counts 2 through 6 are prescribed by `WIFI_PARTITIONS`, not selected jointly with N/WH/FI by a master. Their initial WHFI bands are set to $[5,600]$ in descaled units. Residual national opportunity is attached afterward as described in §3.4. These choices and their effects on final district masses are part of the scenario definition.

### 4.3 The 36-Scenario Catalog
The committed catalog contains **36 operational scenarios** spanning total districts $K\in\{46,\dots,53\}$. Their single-owner commercial labeling is verified in §3.6. The previous claims of a certified Pareto frontier and universally certified final bands/contiguity are not established by the reviewed pipeline.
* **Previously recommended baseline ($K=51$):** `51_total_13n_11wh_24fi_3wifi` (13 National, 11 WH, 24 FI, 3 WIFI). The recommendation is a historical selection, not an optimality certificate.
* **Varying WIFI Series ($K \in \{48, 49, 50\}$):** Holding $FI=21, WH=11$ strictly fixed while stepping $WIFI \in \{2, 3, 4, 5, 6\}$:
  * $N=14$: `48_total_14n_11wh_21fi_2wifi`, `49_total_14n_11wh_21fi_3wifi`, `50_total_14n_11wh_21fi_4wifi`
  * $N=13$: `48_total_13n_11wh_21fi_3wifi`, `49_total_13n_11wh_21fi_4wifi`, `50_total_13n_11wh_21fi_5wifi`
  * $N=12$: `48_total_12n_11wh_21fi_4wifi`, `49_total_12n_11wh_21fi_5wifi`, `50_total_12n_11wh_21fi_6wifi`
* **Multi-Tier Trade-Offs ($K \in \{51, 52, 53\}$):** Systematically stepping National tiers ($N=12, 13, 14$), FI granularity ($FI=24, 25, 26$), and WH capacity ($WH=10, 11, 13, 14$).

All scenarios are cataloged in `summary.csv` and `scenarios.csv` ($1,166,040$ rows). See §3.6 for the properties actually checked; do not interpret the summary's status strings as an independent final-map audit.

---

## 5. Data Descaling and Scale Invariance

### 5.1 Descaled Representation
Raw dollars are normalized by $\kappa > 0$ (median positive ZIP opportunity):
$$m_{\text{rel}}(z) = \frac{M_z}{\kappa}, \quad s_i(z) = \frac{S_i(z)}{M_z} \implies M(z) = \frac{\text{real } M_z}{\kappa}, \quad S_i(z) = \frac{\text{real } S_i(z)}{\kappa}$$
The historical $W_0\approx3,268.41$ figure is the common utility component of the welfare decomposition, not national opportunity mass. It cannot be used to derive a district target. A target must be computed from the declared instance, channel pool, prior coverage, and district count.

### 5.2 Proposition: Scale Invariance of Nash Welfare
> **Proposition 1 (Scale Invariance):**  
> Scaling every currency field uniformly by $\kappa > 0$ yields $g_{i,j}^{\kappa} = \kappa g_{i,j}$. The objective transforms as:
> $$\sum_{i=1}^n \log g_{i, \pi(i)}^{\kappa} = \sum_{i=1}^n \log g_{i, \pi(i)} + n \log \kappa$$
> With a fixed number $n$ of matched terms and an unchanged feasible set after scaling monetary constraints consistently, the shift $n\log\kappa$ is constant, so the argmax and objective differences in nats are invariant. This does not compare plans with different district counts. For centered gains, reservations must scale too. Absolute numerical feasibility tolerances and relative solver gap percentages are not covered by this invariance.

### 5.3 Why Multiplicative Normalization Fails to Restore Curvature
Dividing by $M_{\text{tot}}$ simply shifts the objective by a constant. Dividing by district opportunity $M_j$ leaves the ratio:
$$\frac{\Delta_{i,j} / M_j}{G_{0,j} / M_j} = \frac{\Delta_{i,j}}{G_{0,j}}$$
strictly **dimensionless**. When $|\Delta_{i,j}/G_{0,j}|$ is small, the first-order approximation is:
$$\log\left( \frac{G_{0,j}}{M_j} + \frac{\Delta_{i,j}}{M_j} \right) \approx \log\left(\frac{G_{0,j}}{M_j}\right) + \frac{\Delta_{i,j}}{G_{0,j}}.$$
The small-ratio premise must be measured, not assumed. District normalization subtracts a constant from a matching objective only when the same districts are all staffed; it need not preserve comparisons across maps or selected district subsets. Additive centering changes the preference objective rather than merely conditioning it, with no automatic retention or feasibility guarantee.

---

## 6. The Disagreement Point Dilemma: Classical EF1 vs. Feasible Envy-Freeness (FEFx)

### 6.1 Why the Unconstrained EF1 Guarantee Does Not Transfer to Centered Welfare
Under the hypotheses of the unconstrained additive-goods MNW theorem, including its treatment of zero-utility agents, MNW is Pareto optimal and EF1 (Caragiannis et al., 2019). Subtracting reservations changes the exchange ratios to terms involving $u_i-d_i$; that theorem does not establish EF1 for the centered objective.

### 6.2 Capacity and Connectivity Restrict the Exchange Argument
The territory problem does not satisfy the unconstrained theorem's hypotheses:
1. **Capacity bands ($L\le M_j\le U$):** An item transfer can violate either district's band.
2. **Contiguity:** A transfer can disconnect a district.

The guarantee is unavailable; this does not refute EF1 for a particular delivered map. Utility spread by itself is not an envy test. Fixed-district matching also optimizes over a different feasible set from unrestricted item allocation.

### 6.3 The Implemented Delivered-Map Fairness Audit

The accepted contract (`agy-job/contract.md`) defines a scoped whole-district, band-filtered EFX audit in `tools/measure/fefx.py`:
$$A_k\in\mathcal F_i\implies u_i(A_i)\ge u_i(A_k)-\min_{z\in A_k}u_i(z).$$
This is universal one-item removal. The primary feasibility filter is the district's capacity band; a separate diagnostic adds book overlap. There is no rep-home drivability test. The literature's feasible-subset formulation is not proved equivalent to this delivered-whole-district audit, and no existence guarantee is inherited. Matched representatives are the audited roster; unmatched representatives are excluded explicitly. An audit failure is a measured failure, not something the optimizer automatically prevents.

### 6.4 Optional Claims-Centered Staffing

For a fixed district map, the optional centered matching maximizes the sum of $\log(g_{ij}-d_i)$ over selected representative–district pairs. The implemented reservation is:
$$d_i=\alpha S_i(Z)+d_{\mathrm{floor}},\qquad
 d_{\mathrm{floor}}=\gamma\min_jG_{0j},\qquad
 \alpha=\min\left(1,\frac{M(Z)}{T(Z)}\right)(1-\epsilon).$$
The contract defines zero-total edge cases and permits $\gamma,\epsilon\in[0,1)$; defaults are $0.60$ and $0.05$. The scalar $\alpha$ is common, not rep-specific. State-grain and realized-ZIP reservations are computed separately and must not be mixed when comparing welfare.

This formula does **not** guarantee positive surplus or retained book. The matcher masks edges with $g_{ij}-d_i\le0$ and rejects a matching shortfall; it never clips forbidden edges into feasibility. For example, two districts each with mass 100 and its own incumbent's book 100 have own gain 100 and ambient gain 58 at the reference parameters. The default claims reservation is $0.95(100)+0.60(58)=129.8$, making every edge infeasible.

Any retention improvement or fairness result requires measurement. `--stage2-reservation` defaults to `none`; terminal ZIP-level matching is opt-in via `--stage2-rematch`. The reviewed scenario assembly scripts use placeholder representatives and do not invoke that rematch. Claims-centered staffing must not be described as a verified property of their catalog.

---

## 7. Planar Polygon Dissolution & Full Geographic Crosswalk

### 7.1 Eliminating the Swiss-Cheese Effect
Plotting only the commercial instance leaves rural gaps; the committed scenario table contains 6,478 ZIPs, while the nationwide crosswalk enumerates 33,791 Census ZCTAs. The extension is separate from commercial optimization and can leave zero-opportunity rows unserved (§3.6).
The nationwide long-table exporter (`tools/export_all_scenarios_nationwide_long.py`) first uses the exact commercial assignment for a ZIP–fine-channel key. For other ZCTAs it uses nearest district-reach polygons, a 250 km cutoff, state-level channel-presence rules, and the channel fallback ordering. Ties are reduced to one row by `drop_duplicates`; this is not a solver certificate or a documented deterministic geographic tie-break.

Reach polygons and the realizer's ZIP cell graph are different geographic objects. A filled reach map or a complete key table does not prove ZIP graph connectivity, original band compliance, or service to every ZCTA. The separate wide-crosswalk exporter uses a 150 km cutoff, so export policies must be named rather than assumed identical.

### 7.2 The Master 33,791-ZCTA Crosswalk
For database integration, we constructed the full nationwide crosswalk:
$$\mathcal{D} = 33,791 \text{ Census ZCTAs} \times 5 \text{ sub-channels} \times 36 \text{ scenarios} = 6,082,380 \text{ rows}$$
compressed into `all_scenarios_nationwide_zcta_long.zip` ($27.2$~MB) with the 12-column canonical schema:
`scenario, zip_code, current_channel, canonical_channel, state, model_channel, bundle, district, district_channels, rep, m_rel, has_commercial_opportunity`.

---

## 8. Synthesis Matrix

| Component | Mathematical Paradigm | Theoretical Strengths | Practical Performance / Status |
| :--- | :--- | :--- | :--- |
| **Legacy planning** | One flow commodity per district | State-contact connectivity; sequential or joint coverage passes. | Time-limited incumbents are not lexicographic optimality proofs. |
| **Support master** | Enumerated supports, integer multiplicities, aggregate shares | Planning-level count, coverage, and bands, conditional on support validation and correct decoding. | Separate channel solves; configured solver gaps; no universal runtime bound. |
| **ZIP realization** | Transportation LP, discrete labels, graph growth and repair | Assigns whole ZIPs per bundle; cell ledger prevents duplicate cell ownership. | Still used by the latest pipeline; final bands and connectivity need rechecking. |
| **Western model** | Prescribed regional memberships in the varying-WIFI grid | Adds regional WHFI districts. | National residuals are routed afterward, changing final masses and channel holdings. |
| **Staffing** | Optional log-gain or centered-surplus matching | Exact assignment objective for a fixed valid matrix. | Scenario grids use placeholder IDs; conflicting exported rep labels need repair. |
| **Fairness audit** | Whole-district band-filtered EFX diagnostic | Explicit valuation, roster, and feasibility scope. | Neither zero feasible envy nor retention is guaranteed. |
| **Nationwide crosswalk** | Commercial owners plus spatial extension | Unique source-channel keys in the audited table. | 6,082,380 rows; 88,380 unserved zero-opportunity rows. |

---

## 9. Conclusion & Operational Status

The support master is an aggregate planning model over candidate connected supports. The final result is produced by a separate discrete realization and post-processing pipeline, not by the master alone.

The committed commercial export has exactly one assigned district per ZIP–source-channel key in all 36 scenarios. That measured result does not certify final capacity bands, ZIP connectivity, actual staffing, or Pareto optimality. Those claims require validation of the final ownership ledger against source data and the run's declared constraints after every transformation.

[`PLAN.md`](PLAN.md) records the proposed consolidation, validation, and output-consistency fixes. No solver or export code was changed as part of this documentation correction.
