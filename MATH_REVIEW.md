# Mathematical Review: National Channel Territory Design and Staffing

**Author:** Antigravity  
**Date:** September 13, 2026  
**Subject:** Mathematical formulation, theoretical underpinnings, data descaling invariance, and axiomatic fairness under Feasible Envy-Freeness ([`docs/MODEL_FULL.md`](file:///Users/Shared/sv-ntlee/repos/td/.claude/worktrees/agy-math-review/docs/MODEL_FULL.md)).

---

## 1. Executive Summary & Problem Setting

The territory design problem formulated in [`docs/MODEL_FULL.md`](file:///Users/Shared/sv-ntlee/repos/td/.claude/worktrees/agy-math-review/docs/MODEL_FULL.md) addresses the simultaneous partitioning and staffing of a national sales channel. The operational goal is to carve the financial-institutions (FI) and wirehouse (WH) channels across the 48 contiguous United States and DC into $k$ balanced sales districts of approximately \$1B opportunity each, satisfying geographic contiguity, channel bundling rules, and assignment of incumbent sales representatives to maximize social welfare.

Formulated as a monolithic optimization problem, this represents a **Mixed-Integer Non-Convex Non-Linear Program (MINLP)**:
* Over $6,400$ discrete geographic units (ZIP codes) and $49$ states.
* Four fine business channels ($N_{\text{WH}}, N_{\text{FI}}, \text{WH}, \text{FI}$) with seven admissible bundle combinations.
* Hard topological contiguity constraints on irregular planar graphs.
* Non-linear Nash Social Welfare objective ($\max \sum \log g_{i,j}$) over bipartite matchings between reps and territory boundaries.

To make this computationally tractable, the system adopts a **hierarchical multi-scale decomposition**:
1. **Level 0 (Macro Planning):** A state-by-channel MILP solved lexicographically pass-by-pass on the state rook graph $G_S$.
2. **Level 2 (Micro Realization):** A transportation LP (power diagram) per split state, followed by topological repair heuristics on the ZIP-level Voronoi cell graph $G_{\text{cell}}$.
3. **Stage 2 (Wholesaler Staffing):** A maximum-weight bipartite matching on logarithmic gains solved via the Hungarian method.

---

## 2. Detailed Mathematical Architecture

### 2.1 Level 0: Macro-Level Channel Planning (State-by-Channel MILP)
Level 0 abstracts geography to the state level ($S=49$). For each slot $j \in J$ belonging to bundle $B_j$, the decision variables are:
* $y_{s,j} \in [0, 1]$: Continuous share of state $s$ allocated to slot $j$ (product form across channels $c \in B_j$).
* $z_{s,j} \in \{0, 1\}$: Binary contact indicator ($y_{s,j} > 0$).
* $u_j \in \{0, 1\}$: Binary slot utilization indicator.
* $r_{s,j} \in \{0, 1\}$: Contiguity tree root indicator.
* $f_{a,j} \in [0, N-1]$: Single-commodity flow on directed arc $a \in A_S$ where $N = |S| = 49$.

#### Key Structural Constraints:
* **Product-form Coverage:**
  $$\sum_{j : c \in B_j} y_{s,j} \le 1 - p_{s,c} \quad \forall s \in S, c \in C$$
* **Contact Sizing and Activation:**
  $$\eta z_{s,j} \le y_{s,j} \le z_{s,j} \le u_j \quad \forall s, j$$
* **Bundle-Specific Capacity Bands:**
  $$L_{B_j} u_j \le \sum_{s \in S} W_{s,j} y_{s,j} \le U_{B_j} u_j + \sum_{s \text{ capped}} a_s z_{s,j} \quad \forall j$$
* **Single-Commodity Flow Contiguity:**
  $$\sum_{s \in S} r_{s,j} = u_j, \quad r_{s,j} \le z_{s,j}$$
  $$f_{a,j} \le (N-1) z_{\text{tail}(a),j}, \quad f_{a,j} \le (N-1) z_{\text{head}(a),j}$$
  $$z_{s,j} - N r_{s,j} \le \sum_{a \in \delta^-(s)} f_{a,j} - \sum_{a \in \delta^+(s)} f_{a,j} \quad \forall s, j$$

### 2.2 Level 2: Micro-Level ZIP Realization (Optimal Transport & Graph Repair)
Level 0 passes state shares $y_{s,j}$ to Level 2. Unsplit states ($z_{s,j}=1$ for a unique $j$) are allocated entirely to district $j$. Split states are partitioned via a transportation LP:
$$\min_{x} \sum_{z \in s} \sum_{j} M_z \|p_z - c_j\|^2 x_{z,j}$$
subject to:
$$\sum_{j} x_{z,j} = 1 \quad \forall z \in s, \qquad \sum_{z \in s} M_z x_{z,j} = y_{s,j} M_s \quad \forall j$$
Centroids $c_j$ are updated iteratively via up to five Lloyd iterations, accepting updates only if variance does not increase. Disconnected pieces are resolved post-LP by discrete graph repair on the Voronoi dual $G_{\text{cell}}$ with a mass tolerance slack $\sigma = 0.02 \tau_B$.

### 2.3 Stage 2: Centralized Nash Welfare Staffing
Given district opportunity sets $A_j$ and bundles $B_j$, rep $i$'s gain from running district $j$ is:
$$g_{i,j} = \sum_{z \in A_j} \sum_{c \in B_j} \left[ c_1 S_i(z,c) + c_2 (T_{z,c} - S_i(z,c)) + c_{\text{free}} S_{\text{free}}(z,c) + \lambda M_{z,c} \right]$$
where $c_1 = 1 - \lambda$, $c_2 = \theta(1 - \lambda)$, and $c_{\text{free}} \in \{c_2, c_1, \lambda\}$.

The assignment problem is:
$$\max_{w} \sum_{i \in R} \sum_{j \in J_{\text{used}}} \log(g_{i,j}) w_{i,j}$$
$$\text{s.t.} \quad \sum_{i} w_{i,j} \le 1, \quad \sum_{j} w_{i,j} \le 1, \quad \sum_{i,j} w_{i,j} = \min(|R|, |J_{\text{used}}|), \quad w_{i,j} \in \{0, 1\}$$
Solved via the Kuhn-Munkres (Hungarian) algorithm on the cost matrix $C_{i,j} = -\log(g_{i,j})$.

---

## 3. Data Descaling and Invariance Analysis

### 3.1 Opportunity-Scaled (Descaled) Data Units
The optimization solvers do **not** operate on raw dollars. In [`td/instance.py`](file:///Users/Shared/sv-ntlee/repos/td/.claude/worktrees/agy-math-review/td/instance.py#L1-L20), raw instance data is normalized by $\kappa > 0$ (the median positive ZIP opportunity across the footprint):
$$m_{\text{rel}}(z) = \frac{M_z}{\kappa}, \quad s_i(z) = \frac{S_i(z)}{M_z} \implies M(z) = \frac{\text{real } M_z}{\kappa}, \quad S_i(z) = \frac{\text{real } S_i(z)}{\kappa}$$
Across CONUS, the total partition-invariant welfare mass is $W_0 \approx 3,268.41$ descaled units, and district target capacity is $\tau \approx 180\text{--}200$ descaled units (rather than $\approx \$1\text{B}$).

### 3.2 Proposition: Scale Invariance of Nash Welfare
> **Proposition 1 (Scale Invariance):**  
> Scaling every currency field by a constant $\kappa > 0$ scales gains $g_i^{\kappa} = \kappa g_i$. The objective transforms as:
> $$\sum_{i=1}^n \log g_i^\kappa = \sum_{i=1}^n \log g_i + n \log \kappa$$
> Since $n \log \kappa$ is an additive constant independent of the allocation $w$ and assignment $\pi$, $\arg\max$ is invariant. All objective differences, certificates, and optimality gaps are identical.

### 3.3 Why Multiplicative Normalization Fails to Restore Curvature
Normalizing utility by overall opportunity ($M_{\text{tot}}$ or district $M_j$) does **not** solve the flat-curvature problem:
1. **Global normalization ($g_i / M_{\text{tot}}$):** Subtracts $n \log M_{\text{tot}}$, leaving the argmax and Hessian identical.
2. **District normalization ($g_{i,j} / M_j$):** Scales both baseline $G_0$ and incumbent share $\Delta_{i,j}$, leaving the ratio $\frac{\Delta_{i,j}}{G_{0,j}}$ **strictly dimensionless**.
Because $\frac{\Delta}{G_0} \ll 1$, the first-order Taylor expansion remains linear:
$$\log(G_0 + \Delta) \approx \log(G_0) + \frac{\Delta}{G_0}$$
Multiplicative scaling cannot alter a dimensionless ratio. Only an **additive translation** ($g_i - d_i$) shifts the operating point of $\log(x)$ toward its steep curvature regime.

---

## 4. The Disagreement Point Dilemma: Classical EF1 vs. Feasible Envy-Freeness (FEFx)

### 4.1 The $d = 0$ Guarantee: Caragiannis et al. (2019)
The choice of $d = 0$ in [`docs/math_note/math_note.tex`](file:///Users/Shared/sv-ntlee/repos/td/.claude/worktrees/agy-math-review/docs/math_note/math_note.tex#L84-L94) was made to inherit the landmark fair-division theorem of Caragiannis et al. (2019):
* Under unconstrained fair division of indivisible goods with additive valuations and $d = \mathbf{0}$, maximizing Nash Social Welfare $\prod u_i(A_i)$ is provably **Pareto Optimal (PO)** and **Envy-Free up to One Item (EF1)**.

### 4.2 Why $d > 0$ Voids Classical EF1
Subtracting a non-zero disagreement point $d > 0$ breaks the local exchange argument. In $\max \prod (u_i - d_i)$, an agent $i$ near their disagreement point ($u_i - d_i \to \epsilon$) has an artificially inflated marginal gain $\frac{u_i(z)}{\epsilon}$. The optimizer aggressively transfers items from unconstrained agents to agent $i$, causing unconstrained agents to strongly envy agent $i$ across many goods, violating EF1.

### 4.3 The Reality: Capacity Bands Already Invalidate EF1
As established in [`docs/foundations/DOMAIN_economic-theory.md`](file:///Users/Shared/sv-ntlee/repos/td/.claude/worktrees/agy-math-review/docs/foundations/DOMAIN_economic-theory.md#L482-L510) (§2.1, §2.8), the real districting problem **already violates the hypotheses of Caragiannis et al.**:
* **Capacity balance bands** ($L \le M_j \le U$) forbid arbitrary item transfers.
* **Geographic contiguity** forbids transferring disconnected ZIPs.
The delivered map already exhibits a representative utility spread of over $60\%$. Classical EF1 is not inheritable under assignment constraints.

### 4.4 The Solution: Feasible Envy-Freeness (FEFx) & Asymmetric Claims
Following Barman et al. (EC 2023, [`barman2023gac`](file:///Users/Shared/sv-ntlee/repos/td/.claude/worktrees/agy-math-review/docs/foundations/LIT_economic-theory.md#L225-L236)), the correct axiom under Generalized Assignment Constraints is **Feasible Envy-Freeness (FEFx)**:
$$\forall j \ne i, \quad V_j \in \mathcal{F}_i \implies \exists z \in V_j \text{ s.t. } u_i(V_i) \ge u_i(V_j \setminus \{z\})$$
where $\mathcal{F}_i$ denotes the set of territories that rep $i$ could feasibly hold (satisfying contiguity, drivability from home base, and capacity bands). *"A wholesaler cannot envy a bundle they could not work."*

### 4.5 Asymmetric Claims Objective & Feasibility Guard
We drop symmetric anonymity in favor of an **asymmetric claims problem** (O'Neill, 1982; Thomson, 2003):
$$\max_{\pi} \sum_{i \in R} \log\left( g_{i, \pi(i)} - d_i \right)$$
with the **Bargaining Set Non-Emptiness Guard**:
$$d_i = \alpha_i S_i(Z) + d_{\text{floor}}$$
where $d_{\text{floor}} = \gamma \min_j G_{0,j}$ ($\gamma \in [0.5, 0.8]$) guarantees a baseline floor, and $\alpha_i \in (0, 1)$ is determined via proportional bankruptcy sharing:
$$\alpha_i = \min\left( 1.0, \; \frac{M(\text{Region})}{\sum_{k \in \text{overlap}} S_k(\text{Region})} \right) \cdot (1 - \epsilon)$$
* **Guarantees interior feasibility:** $g_{i,j} - d_i > 0$ for all valid assignments.
* **Restores sharp concavity:** Operating point denominator drops from $\approx 200$ to $\approx 15$, amplifying the penalty against book starvation by over $100\times$.
* **FEFx Compliance:** Eliminates spurious cross-country envy while protecting earned incumbent continuity.

---

## 5. Structural Tensions & Pipeline Trade-Offs

### 5.1 The Stage 2 Timing Inversion (State Shares vs. Realized Boundaries)
* **The Documented Theory:** Assumes Level 0 (plan) $\rightarrow$ Level 2 (realize zips $A_j$) $\rightarrow$ Stage 2 (match reps on realized $A_j$).
* **The Implemented Reality:** Stage 2 matching runs **at Level 0** at state-channel aggregation:
  $$g_{i,j}^{\text{state}} = \sum_{s} y_{s,j} \sum_{c \in B_j} u_i(s, c)$$
  The resulting assignment is saved to `staffing.json`. Level 2 then performs the spatial cut and contiguity repair, attaching the pre-assigned reps without re-solving the assignment problem.

State shares $y_{s,j}$ model territory as a continuously divisible fluid. However, sales books $S_i(z, c)$ are discrete, geographically clustered point masses. Matching at Level 0 is optimal for the **expectation under uniform spatial distribution**, but systematically suboptimal for the **realized geographic map**.

### 5.2 Optimal Transport vs. Topological Graph Contiguity
* **Theoretical Property:** By the Brenier-Aurenhammer theorem of semi-discrete optimal transport, the continuous LP solution partitions space into a power diagram with convex polyhedral cells.
* **Topological Breakdown:** Discrete ZIP codes embedded inside non-convex state geometries (coastal peninsulas, bays, panhandles) frequently produce disconnected island components when intersected with convex power cells.
* **Algorithmic Fallback:** The pipeline discards exact optimization in favor of discrete greedy graph heuristics: shedding fragments, priority-queue frontier growth on $G_{\text{cell}}$, and bridging across borders with a $2\%$ band relaxation ($\sigma = 0.02\tau_B$).

---

## 6. Synthesis Assessment Matrix

| Component | Mathematical Paradigm | Theoretical Soundness | Practical Vulnerability |
| :--- | :--- | :--- | :--- |
| **Level 0 Plan** | Multi-commodity MIP | **High**: Exact Pareto hierarchy, tight formulation, guarantees state connectivity. | Continuous state shares $y_{s,j}$ ignore spatial clustering of localized sales books. |
| **Level 2 Cut** | Optimal Transport (Power Diagrams) | **Moderate**: Optimal compactness in Euclidean $\mathbb{R}^2$. | Induces disconnected spatial fragments on irregular/non-convex boundaries. |
| **Level 2 Repair** | Discrete Graph Heuristics | **Empirical**: Restores contiguity on $G_{\text{cell}}$. | Heuristic; introduces $\pm 2\%$ capacity violations to fix topology. |
| **Stage 2 Matching** | Asymmetric Nash Matching | **High**: Scale invariant, polynomial solve time via Hungarian method. | At $d=0$, flat curvature treats book disruption as near-zero cost. |
| **Fairness Audit** | FEFx Matrix Audit | **High**: Evaluates envy only over feasible territories $\mathcal{F}_i$. | Replaces unconstrained EF1, which is voided by capacity bands and contiguity. |

---

## 7. Strategic Recommendations

1. **Implement Asymmetric Claims-Centered Staffing (Refinement 1):** Replace the zero disagreement baseline with the claims-scaled reservation floor $d_i = \alpha_i S_i + d_{\text{floor}}$, restoring steep curvature to protect incumbents from catastrophic book displacement.
2. **Deploy the FEFx Fairness Audit Suite:** Update `tools/measure/audits.py` with the three-way verdict: plain EF1, FEFx with respect to capacity and contiguity bands, and proportionality $u_i(A_i) \ge u_i(Z)/k$.
3. **Execute Terminal Stage 2 Re-Match Pass:** Run a second Kuhn-Munkres matching pass at the conclusion of Level 2 using the exact realized ZIP territories $A_j$ to eliminate distortion from continuous state-share approximations.
4. **Enforce Contiguity-Constrained Spatial Splitting:** Promote the graph-based `--split-cut contiguous` partitioner on $G_{\text{cell}}$ to eliminate post-hoc heuristic repair slacks.
