# Mathematical Review: National Channel Territory Design and Staffing

**Author:** Antigravity  
**Date:** September 14, 2026  
**Subject:** Multi-Scale Formulations, Support-Based Exact Partitioning, Scale Invariance, and Axiomatic Feasible Envy-Freeness ([`docs/MODEL_FULL.md`](docs/MODEL_FULL.md)).

---

## 1. Executive Summary & Problem Setting

The territory design problem formulated in [`docs/MODEL_FULL.md`](docs/MODEL_FULL.md) addresses the simultaneous partitioning of commercial sales opportunity across the 48 contiguous United States and Washington, D.C. ($S=49$ planning states) into $K$ balanced sales districts. Concurrently, it models the allocation of incumbent sales representatives across four fine business channels:
$$C = \{N_{\text{WH}}, N_{\text{FI}}, \text{WH}, \text{FI}\}$$
admitting seven permissible channel bundles:
$$\mathfrak{B} = \{N, \text{WH}, \text{FI}, \text{WH\_PLUS}, \text{FI\_PLUS}, \text{WHFI}, \text{WHFI\_PLUS}\}$$
where $N = \{N_{\text{WH}}, N_{\text{FI}}\}$, $\text{WH} = \{\text{WH}\}$, $\text{FI} = \{\text{FI}\}$, and $\text{WHFI} = \{\text{WH}, \text{FI}\}$.

Formulated as a monolithic optimization problem over $6,459$ commercial ZIP codes (or $33,791$ total Census ZCTAs), this represents an intractable **Mixed-Integer Non-Convex Non-Linear Program (MINLP)**:
* Hard topological contiguity constraints on irregular planar graphs.
* Bundle-specific opportunity capacity bounds $[L_B, U_B]$.
* Non-linear Nash Social Welfare objective ($\max \sum \log g_{i,j}$) over bipartite matchings between reps and territory boundaries.

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
1. **Combinatorial Explosion in Multi-Channel Sequences:** On multi-channel runs (WH with 11--14 districts and FI with 21--26 districts), the flow-tree binary MILP suffered branch-and-bound divergence, exceeding 600-second timeouts.
2. **Topological Disconnection under Convex Power Cells:** By the Brenier-Aurenhammer theorem, optimal transport produces convex polyhedral cells. When intersected with non-convex state geometries (coastal peninsulas, bays, panhandles), discrete ZIPs fractured into disconnected topological islands.
3. **Heuristic Boundary Slacks & Unheld Mass:** Post-hoc greedy repair heuristics introduced $\pm 2\%$ capacity slacks ($\sigma = 0.02\tau_B$), resulting in unheld opportunity mass ($>0.5\%$) and boundary violations.
4. **Timing Inversion:** Matching reps at Level 0 on continuous state shares $y_{s,j}$ assumed uniform spatial opportunity, causing severe book disruption once discrete ZIP boundaries were finalized.

---

## 3. The Support-Based Exact Reformulation Framework (The Latest Approach)

To resolve the failure modes of the legacy pipeline, we developed and deployed the **Support-Based Exact Reformulation Framework** (`tools/group2_support.py`, `tools/solve_global_multichannel.py`).

### 3.1 Combinatorial Support Enumeration on Planning Graph $G=(V,E)$
Instead of continuous fluid variables with post-hoc repair, we pre-compute the admissible support space $\mathcal{S}$:
$$\mathcal{S} = \{S \subseteq V \mid G[S] \text{ is connected}, |S| \le \bar{s}, \text{diam}(S) \le D_{\max}\}$$
* **Cardinality Bound:** $|S| \le 6$ states/units per district.
* **Spatial Centroid Pruning:** $\max_{u,v \in S} \|c_u - c_v\|_2 \le 900\text{ km}$ (expanded to $1,200\text{ km}$ for the Pacific Northwest).
* Contiguity is guaranteed **a priori by construction**.

### 3.2 The Master Support Partitioning MILP
Let $x_S \in \{0, 1\}$ indicate support activation, and $y_{v,S} \in [0, 1]$ indicate the continuous share of unit $v$ allocated to district $S$:
$$\min_{x, y} \sum_{S \in \mathcal{S}} \sum_{v \in S} \text{Cost}(v, S) \, y_{v, S} + \rho \sum_{S \in \mathcal{S}} \text{Diam}(S) \, x_S$$
subject to:
$$\sum_{S \in \mathcal{S}} x_S = K$$
$$\sum_{S \in \mathcal{S} : v \in S} y_{v, S} = 1 \quad \forall v \in V \quad \text{(Zero Unheld Mass)}$$
$$\eta \, x_S \le y_{v, S} \le x_S \quad \forall S \in \mathcal{S}, v \in S \quad (\eta = 0.05)$$
$$L_K \, x_S \le \sum_{v \in S} M_v \, y_{v, S} \le U_K \, x_S \quad \forall S \in \mathcal{S} \quad \text{(Exact Capacity Bands)}$$
$$y_{v, S} \in \{0, 1\} \quad \forall v \in V_{\text{indivisible}}, S \in \mathcal{S} \quad \text{(Whole-State Integrity)}$$
$$\sum_{S \in \mathcal{S} : \{u, v\} \subseteq S} x_S \ge 1 \quad \forall (u, v) \in \mathcal{C}_{\text{couple}} \quad \text{(Macro Articulation)}$$

### 3.3 Theoretical Guarantees & Independent Certification
* **100% Rook Contiguity:** Every activated support $S$ with $x_S^* = 1$ is an induced connected subgraph of $G$.
* **Zero Unheld Mass:** $\sum_{S} M(S) = \sum_{v} M_v$ exactly ($0.00\%$ unheld mass).
* **Zero Heuristic Slack:** District masses strictly satisfy $L_K \le M(S) \le U_K$.
* **Provable Solvability in $<3$ Seconds:** Master problems have $<5,000$ binary columns, solving in $0.8\text{--}2.8$ seconds via HiGHS.
* **Independent Validator:** Every solution is independently certified against 7 physical invariants.

---

## 4. Unified Multi-Channel Architecture & Western Merged Realization

### 4.1 The Sparse Geography Paradox
Across seven rural Western states ($S_{\text{west}} = \{\text{CO}, \text{ID}, \text{MT}, \text{ND}, \text{NE}, \text{SD}, \text{WY}\}$), commercial sales opportunity is low ($M \approx 431$ descaled units in WHFI, $689$ in WHFI\_PLUS). Under standalone single-channel models, allocating National representatives ($\tau_N \approx 615$) requires spanning non-contiguous territories and violates the 900 km centroid limit.

### 4.2 Dedicated Regional Merged Channel (WIFI/WHFI)
To solve this, we dedicate a regional merged channel ($WIFI \in \{1, \dots, 6\}$) covering $S_{\text{west}}$, servicing multi-channel accounts within compact, drivable clusters, while preserving single-channel purity ($N, WH, FI$) across the remaining 42 states:
$$K = N + WH + FI + WIFI$$

### 4.3 Certified 36-Scenario Pareto Catalog
We realized and certified **36 Pareto-optimal operational scenarios** spanning total districts $K \in \{46, \dots, 53\}$:
* **Recommended Baseline ($K=51$):** `51_total_13n_11wh_24fi_3wifi` (13 National, 11 WH, 24 FI, 3 WIFI). 100% contiguity, 0.00% unheld mass.
* **Varying WIFI Series ($K \in \{48, 49, 50\}$):** Holding $FI=21, WH=11$ strictly fixed while stepping $WIFI \in \{2, 3, 4, 5, 6\}$:
  * $N=14$: `48_total_14n_11wh_21fi_2wifi`, `49_total_14n_11wh_21fi_3wifi`, `50_total_14n_11wh_21fi_4wifi`
  * $N=13$: `48_total_13n_11wh_21fi_3wifi`, `49_total_13n_11wh_21fi_4wifi`, `50_total_13n_11wh_21fi_5wifi`
  * $N=12$: `48_total_12n_11wh_21fi_4wifi`, `49_total_12n_11wh_21fi_5wifi`, `50_total_12n_11wh_21fi_6wifi`
* **Multi-Tier Trade-Offs ($K \in \{51, 52, 53\}$):** Systematically stepping National tiers ($N=12, 13, 14$), FI granularity ($FI=24, 25, 26$), and WH capacity ($WH=10, 11, 13, 14$).

All scenarios are cataloged in `summary.csv` and `scenarios.csv` ($1,166,040$ rows), with 0 violations.

---

## 5. Data Descaling and Scale Invariance

### 5.1 Descaled Representation
Raw dollars are normalized by $\kappa > 0$ (median positive ZIP opportunity):
$$m_{\text{rel}}(z) = \frac{M_z}{\kappa}, \quad s_i(z) = \frac{S_i(z)}{M_z} \implies M(z) = \frac{\text{real } M_z}{\kappa}, \quad S_i(z) = \frac{\text{real } S_i(z)}{\kappa}$$
National opportunity sum is $W_0 \approx 3,268.41$ descaled units; target district capacity is $\tau \approx 180\text{--}200$ descaled units.

### 5.2 Proposition: Scale Invariance of Nash Welfare
> **Proposition 1 (Scale Invariance):**  
> Scaling every currency field uniformly by $\kappa > 0$ yields $g_{i,j}^{\kappa} = \kappa g_{i,j}$. The objective transforms as:
> $$\sum_{i=1}^n \log g_{i, \pi(i)}^{\kappa} = \sum_{i=1}^n \log g_{i, \pi(i)} + n \log \kappa$$
> Since $n \log \kappa$ is an additive constant independent of the allocation $w$ and assignment $\pi$, $\arg\max$ is strictly invariant. All objective differences, certificates, and optimality gaps are identical across scale.

### 5.3 Why Multiplicative Normalization Fails to Restore Curvature
Dividing by $M_{\text{tot}}$ simply shifts the objective by a constant. Dividing by district opportunity $M_j$ leaves the ratio:
$$\frac{\Delta_{i,j} / M_j}{G_{0,j} / M_j} = \frac{\Delta_{i,j}}{G_{0,j}}$$
strictly **dimensionless**. Because ambient district opportunity dwarfs individual book differences ($G_{0,j} \gg \Delta_{i,j}$), the Taylor expansion remains linear:
$$\log\left( \frac{G_{0,j}}{M_j} + \frac{\Delta_{i,j}}{M_j} \right) \approx \log\left(\frac{G_{0,j}}{M_j}\right) + \frac{\Delta_{i,j}}{G_{0,j}}$$
Only an **additive translation** ($g - d$) shifts the operating point of $\log(x)$ toward its steep curvature regime.

---

## 6. The Disagreement Point Dilemma: Classical EF1 vs. Feasible Envy-Freeness (FEFx)

### 6.1 Why $d > 0$ Voids Classical EF1
Under unconstrained fair division with $d = \mathbf{0}$, maximizing Nash welfare guarantees Pareto Optimality (PO) and Envy-Free up to One Item (EF1) (Caragiannis et al., 2019). However, introducing $d > \mathbf{0}$ creates divergent marginal gains $\frac{u_i(z)}{u_i - d_i}$ when agents approach their threat point, breaking the local exchange argument.

### 6.2 The Reality: Capacity Bands Already Invalidate Classical EF1
In sales districting, **Theorem 1 of Caragiannis et al. is already invalidated on the ground**:
1. **Capacity bands ($L \le M_j \le U$):** Forbid arbitrary item transfers.
2. **Topological contiguity:** Forbids transferring disconnected items.
Empirical utility spread on CONUS exceeds $60\%$. Classical EF1 is not inheritable.

### 6.3 Transition to Feasible Envy-Freeness (FEFx)
Under Generalized Assignment Constraints (Barman et al., EC 2023), the correct axiom is **Feasible Envy-Freeness (FEFx)**:
$$A_k \in \mathcal{F}_i \implies \forall z \in A_k, \; u_i(A_i) \ge u_i(A_k \setminus \{z\})$$
where $\mathcal{F}_i$ is the operational feasible territory set for representative $i$ (compact, contiguous, capacity-compliant). *"A wholesaler cannot envy a bundle they could not work."*

### 6.4 Asymmetric Claims Objective & Feasibility Guard
We formulate staffing as an **asymmetric claims problem** (O'Neill, 1982; Thomson, 2003):
$$\max_{\pi} \sum_{i \in R} \log\left( g_{i, \pi(i)} - d_i \right)$$
subject to the **Bargaining Set Non-Emptiness Guard**:
$$d_i = \alpha_i S_i(Z) + d_{\text{floor}}$$
where $d_{\text{floor}} = \gamma \min_j G_{0,j}$ ($\gamma \in [0.5, 0.8]$), and $\alpha_i \in (0, 1)$ scales claims proportionally:
$$\alpha_i = \min\left( 1.0, \; \frac{M(\text{Region})}{\sum_{k \in \text{overlap}} S_k(\text{Region})} \right) \cdot (1 - \epsilon)$$
* **Guarantees feasibility:** $g_{i,j} - d_i > 0$ for all valid assignments.
* **Restores sharp concavity:** Denominators drop from $\approx 200$ to $\approx 15$, amplifying protection against book starvation by over $100\times$.
* **FEFx Compliance:** Prunes illegitimate cross-country envy while protecting earned incumbent continuity.

---

## 7. Planar Polygon Dissolution & Full Geographic Crosswalk

### 7.1 Eliminating the Swiss-Cheese Effect
Naive GIS exports plotting only commercial opportunity ZIPs ($3,713$ out of $33,791$ Census ZCTAs) leave vast rural white gaps.
* **Planar Dissolution Pipeline (`tools/geom_export.py`, `tools/export_tableau_datasets.py`):**
  1. Voronoi proximity tessellation assigns unpopulated ZIP centroids to the nearest district center in LAEA projection.
  2. Dissolved polygons are strictly intersected with US Census state boundary shapefiles.
  3. Cleaned geometries are transformed to WGS84 (`EPSG:4326`) and exported to `tableau_district_reach.geojson` ($1,809$ district polygons across all 36 scenarios).

### 7.2 The Master 33,791-ZCTA Crosswalk
For database integration, we constructed the full nationwide crosswalk:
$$\mathcal{D} = 33,791 \text{ Census ZCTAs} \times 5 \text{ sub-channels} \times 36 \text{ scenarios} = 6,082,380 \text{ rows}$$
compressed into `all_scenarios_nationwide_zcta_long.zip` ($27.2$~MB) with the 12-column canonical schema:
`scenario, zip_code, current_channel, canonical_channel, state, model_channel, bundle, district, district_channels, rep, m_rel, has_commercial_opportunity`.

---

## 8. Synthesis Matrix

| Component | Mathematical Paradigm | Theoretical Strengths | Practical Performance / Status |
| :--- | :--- | :--- | :--- |
| **Legacy Level 0** | Multi-Commodity Flow MILP | Strict Pareto hierarchy; compact flow trees. | Combinatorial timeout on multi-channel problems ($>600$s). |
| **Legacy Level 2** | Optimal Transport + Graph Repair | Optimal Euclidean compactness via power cells. | Induces disconnected islands; $\pm 2\%$ capacity slacks. |
| **Latest Approach** | **Support-Based Exact MILP** | **100% rook contiguity by construction**; 0.00% unheld mass; exact capacity bands. | **Solves in $<3$ seconds** via HiGHS; certified across all 36 scenarios. |
| **Western Model** | **Dedicated Merged WIFI** | Resolves sparse density without diluting urban channels ($K=N+WH+FI+WIFI$). | Successfully realized for $WIFI \in [1, 6]$ across $K \in [46, 53]$. |
| **Stage 2 Staffing** | Asymmetric Claims Matching | Operates $\log(g_i - d_i)$ in steep curvature regime; protects legacy books. | Scale invariant; polynomial solve via Kuhn-Munkres. |
| **Fairness Audit** | FEFx Matrix Audit | Evaluates envy only over operational feasible set $\mathcal{F}_i$. | Replaces unconstrained EF1, which is voided by capacity bands. |
| **Spatial GIS** | Planar Polygon Dissolution | Exact state splits; zero Swiss-cheese omissions in Tableau. | $1,809$ polygons in GeoJSON; $6.08\text{M}$ ZCTA records. |

---

## 9. Conclusion & Operational Status

The evolution to the **Support-Based Exact Reformulation** achieves:
1. **Sub-3-Second Global Optimality:** Eliminating flow variables bypasses combinatorial timeouts entirely.
2. **Exact Mathematical Rigor:** 100% contiguity and 0.00% unheld mass are guaranteed a priori and verified by independent certification.
3. **Geographic Realism:** Regional merged channels (WIFI) resolve rural territories while preserving single-channel specialization.
4. **Axiomatic Fairness:** Feasible Envy-Freeness (FEFx) under asymmetric claims restores steep curvature to protect incumbent books.

All datasets, maps, and schemas are fully generated, verified, and committed to the repository.
