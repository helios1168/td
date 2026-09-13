# Implementation Plan: Asymmetric Claims-Centered Staffing and FEFx Fairness

**Architecture:** Tri-Agent Collaborative Framework  
* **Theoretical Authority & Mathematical Brain:** Antigravity  
* **Executive Orchestrator:** OpenAI Codex  
* **Lead Implementer:** OpenCode  
**Target Repository:** `td` (`/Users/Shared/sv-ntlee/repos/td`)  
**Active Worktree:** `agy-math-review` (`/Users/Shared/sv-ntlee/repos/td/.claude/worktrees/agy-math-review`)  
**Date:** September 13, 2026  

---

## 1. Executive Summary & Architectural Roles

This document outlines the multi-phase engineering plan to implement the mathematical enhancements established in [`MATH_REVIEW.md`](MATH_REVIEW.md) and [`MATH_REVIEW.pdf`](MATH_REVIEW.pdf). The primary goal is to resolve the flat-curvature pathology of the Nash Social Welfare objective ($\max \sum \log g_{i,j}$), transition the fairness audit from invalidated unconstrained EF1 to **Feasible Envy-Freeness (FEFx)**, and eliminate spatial aggregation distortion via a terminal Stage 2 re-matching pass.

### Tri-Agent Operating Model

```
+-------------------------------------------------------------------------+
|                              ANTIGRAVITY                                |
|                 (Theoretical Brain & Verification Authority)            |
|  - Axiomatic formulations (FEFx, claims bankruptcy scaling, duals)      |
|  - Mathematical invariance proofs & convexity verification              |
|  - Invariant validation, certificate checks, and audit signing          |
+------------------------------------+------------------------------------+
                                     | Defines Math Specs & Guardrails
                                     v
+-------------------------------------------------------------------------+
|                             OPENAI CODEX                                |
|                        (Executive Orchestrator)                         |
|  - Task dependency graph execution and sprint pacing                    |
|  - Sub-process dispatching to OpenCode                                  |
|  - Worktree isolation, branch management, and CI gating                 |
+------------------------------------+------------------------------------+
                                     | Dispatches Implementation Tasks
                                     v
+-------------------------------------------------------------------------+
|                               OPENCODE                                  |
|                           (Lead Implementer)                            |
|  - Python code modification (`td/`, `tools/`, `tests/`)                 |
|  - Unit & regression test development (`pytest`)                        |
|  - Performance profiling, vectorization, and CLI plumbing               |
+-------------------------------------------------------------------------+
```

---

## 2. Core Mathematical Specifications

### Specification 1: Asymmetric Claims-Centered Reservation Utilities ($d_i$)

#### Theoretical Target
Restore steep curvature to the logarithmic objective $\log(g_i - d_i)$ to protect incumbent representatives from catastrophic book displacement while guaranteeing bargaining set feasibility.

#### Mathematical Formulation
For each representative $i \in R$, replace the legacy zero disagreement baseline ($d=0$) with:
$$d_i = \alpha_i S_i(Z) + d_{\text{floor}}$$
where:
1. **$S_i(Z)$** is rep $i$'s total historical book mass across the contested region:
   $$S_i(Z) = \sum_{z \in Z} \sum_{c} S_i(z, c)$$
2. **$\alpha_i \in (0, 1)$** is the **Proportional Bankruptcy Claims Factor**:
   $$\alpha_i = \min\left( 1.0, \; \frac{M(\text{Region})}{\sum_{k \in \text{overlap}} S_k(\text{Region})} \right) \cdot (1 - \epsilon)$$
   with $\epsilon = 0.05$ (headroom buffer).
3. **$d_{\text{floor}}$** is the common ambient floor:
   $$d_{\text{floor}} = \gamma \cdot \min_{j \in J} G_{0,j}$$
   with $\gamma = 0.60$, where $G_{0,j} = \sum_{z \in V_j} [c_2 T_z + c_{\text{free}} S_{\text{free}, z} + \lambda M_z]$.

#### Guardrail / Invariant
Before constructing the Hungarian cost matrix $C_{i,j} = -\log(g_{i,j} - d_i)$, assert:
$$g_{i,j} - d_i \ge 10^{-6} \cdot d_{\text{floor}} > 0 \quad \forall (i, j)$$
If any assignment violates this guard, smoothly clip to $\epsilon_{\text{floor}} = 10^{-6} d_{\text{floor}}$ with a logged warning.

---

### Specification 2: Feasible Envy-Freeness (FEFx) Audit Suite

#### Theoretical Target
Replace the classical $13 \times 13$ unconstrained EF1 matrix in [`tools/measure/audits.py`](file:///Users/Shared/sv-ntlee/repos/td/tools/measure/audits.py) with the three-way verdict matrix under Generalized Assignment Constraints (Barman et al., 2023).

#### Mathematical Formulation
For each pair of representatives $i, k \in R$, evaluate envy only if district $A_k$ is **feasible** for representative $i$ ($A_k \in \mathcal{F}_i$):
1. **Capacity Band Feasibility:** $L \le M(A_k) \le U$.
2. **Spatial / Geographic Feasibility:** District $A_k$ overlaps with rep $i$'s candidate territory (e.g., centroid distance $d(\text{home}_i, \text{center}(A_k)) \le D_{\max}$ or $S_i(A_k) > 0$).

#### Audit Output Matrix
For each active pair $(i, k)$:
* **Plain EF1:** $\exists z \in A_k \text{ s.t. } u_i(A_i) \ge u_i(A_k \setminus \{z\})$.
* **FEFx (w.r.t. $\mathcal{F}_i$):** If $A_k \in \mathcal{F}_i$, $\forall z \in A_k, \; u_i(A_i) \ge u_i(A_k \setminus \{z\})$.
* **Proportionality:** $u_i(A_i) \ge \frac{1}{k} u_i(Z)$.

---

### Specification 3: Terminal Stage 2 Re-Match Pass

#### Theoretical Target
Eliminate the spatial distortion caused by matching reps on continuous Level 0 state shares ($y_{s,j}$) rather than realized discrete ZIP code boundaries ($A_j$).

#### Mathematical Formulation
At the conclusion of Level 2 (post-cut and post-repair):
1. Compute the exact discrete gain matrix on realized ZIP sets:
   $$g_{i,j}^{\text{discrete}} = \sum_{z \in A_j} \sum_{c \in B_j} u_i(z, c)$$
2. Solve maximum-weight bipartite matching on centered utilities:
   $$\pi^*_{\text{terminal}} = \arg\max_{\pi} \sum_{i} \log\left( g_{i, \pi(i)}^{\text{discrete}} - d_i \right)$$
3. Compute and log the **Spatial Aggregation Distortion Metric**:
   $$\Delta W = \sum_{i} \log(g_{i, \pi^*_{\text{terminal}}(i)}) - \sum_{i} \log(g_{i, \pi_{\text{Level0}}(i)})$$

---

## 3. Phased Implementation Roadmap

```
+--------------------------------------------------------------------------+
| PHASE 1: Baseline Audit & Test Harness                                   |
| - OpenCode: Build FEFx audit module in `tools/measure/audits.py`         |
| - OpenCode: Create synthetic & real footprint unit tests                 |
| - Codex: Verify baseline tests pass with zero regressions                |
+------------------------------------+-------------------------------------+
                                     v
+--------------------------------------------------------------------------+
| PHASE 2: Asymmetric Claims Centering in Stage 2 Staffing                 |
| - OpenCode: Implement claims bankruptcy scaling in `td/stage2_state.py`  |
| - OpenCode: Add `--stage2-reservation` flag to CLI entrypoints           |
| - Antigravity: Verify non-emptiness proofs & numerical conditioning      |
| - Codex: Benchmark against baseline on CONUS instance                    |
+------------------------------------+-------------------------------------+
                                     v
+--------------------------------------------------------------------------+
| PHASE 3: Terminal Stage 2 Re-Match Pass                                  |
| - OpenCode: Implement `--stage2-rematch` in `tools/full_plan.py`         |
| - OpenCode: Log discrete gain delta $\Delta W$ and certificate updates   |
| - Codex: Run regression test suite on multi-split states (CA, TX, FL)    |
+------------------------------------+-------------------------------------+
                                     v
+--------------------------------------------------------------------------+
| PHASE 4: Verification, Benchmarking & Leadership Deliverables            |
| - OpenCode: Generate comparative 13x13 FEFx audit tables                 |
| - Antigravity: Review and sign off on mathematical certificates          |
| - Codex: Package final artifacts and executive report                    |
+--------------------------------------------------------------------------+
```

---

## 4. Detailed Task Breakdown

### Phase 1: Baseline Audit & Test Harness
* **Task 1.1 (OpenCode):** Create `tools/measure/audits.py` with `compute_envy_matrix(assignment, footprint, G)` implementing:
  * Plain EF1 check.
  * FEFx constraint filter (`is_feasible_for_agent(agent, district, bands)`).
  * Proportionality shortfall calculation ($u_i(A_i) - u_i(Z)/k$).
* **Task 1.2 (OpenCode):** Author unit test suite `tests/test_audits.py` validating FEFx pruning on a 2-agent toy instance and a 13-agent CONUS instance.
* **Task 1.3 (Codex):** Run `$TD_PY -m pytest tests/test_audits.py` and ensure 100% test pass.

### Phase 2: Asymmetric Claims Centering in Stage 2 Staffing
* **Task 2.1 (OpenCode):** In `td/stage2_state.py`, implement `compute_reservation_vector(instance, region, gamma=0.6, epsilon=0.05)`.
* **Task 2.2 (OpenCode):** Update `solve_staffing()` to accept `reservation_vector` and form costs:
  $$C_{i,j} = -\log\left( \max(g_{i,j} - d_i, \; \epsilon_{\text{floor}}) \right)$$
* **Task 2.3 (OpenCode):** Expose CLI argument `--stage2-reservation {none, uniform, claims}` across `tools/full_plan.py`.
* **Task 2.4 (Antigravity):** Verify that all $d_i$ satisfy the non-emptiness condition and that $C_{i,j}$ remains strictly convex.
* **Task 2.5 (Codex):** Run comparative solve on CONUS footprint and confirm no negative utility crashes.

### Phase 3: Terminal Stage 2 Re-Match Pass
* **Task 3.1 (OpenCode):** In `tools/full_plan.py`, hook an optional post-Level 2 pass `execute_terminal_rematch(realized_districts, reps)`.
* **Task 3.2 (OpenCode):** Update `staffing.json` with terminal assignment and record matching migration statistics (`reps_swapped`, `welfare_delta`).
* **Task 3.3 (Codex):** Execute full pipeline run with `--stage2-rematch` on worktree `agy-math-review`.

### Phase 4: Verification & Final Report
* **Task 4.1 (OpenCode):** Run `tools/measure/audits.py` on baseline vs. refined plans, emitting `fairness_audit_comparison.json`.
* **Task 4.2 (Antigravity):** Validate the FEFx matrix and verify that incumbent book retention increased significantly without violating capacity bands.
* **Task 4.3 (Codex):** Commit all changes to branch `worktree-agy-math-review` with descriptive, atomic commit messages.

---

## 5. Verification Invariants & Testing Guardrails

The orchestrator (Codex) and implementer (OpenCode) must enforce the following invariants at every step:

1. **Strict Non-Negative Headroom:** Pointwise headroom $M_z \ge \max(A_z + \theta B_z, B_z + \theta A_z)$ must hold across all processed ZIP codes.
2. **Capacity Band Integrity:** Final districts must strictly respect $[L_{B_j}, U_{B_j}]$ subject only to declared state-cap break allowances $a_s$.
3. **No Code Edits to Protected Files:** Do not modify `docs/MODEL_FULL.md` or files outside the agreed feature scope.
4. **Absolute Solver Feasibility Tolerance:** Linear and Hungarian programming solvers must maintain feasibility within $10^{-9}$ gain units.
5. **Scale Invariance Preservation:** Scaling instance opportunity by constant $\kappa$ must yield numerically identical matching assignments.

---

## 6. Definition of Done (DoD)

The implementation sprint will be complete when:
- [ ] `tests/test_audits.py` passes with full test coverage of EF1, FEFx, and Proportionality.
- [ ] `--stage2-reservation claims` successfully executes on the CONUS instance without numerical instabilities.
- [ ] Terminal re-match pass (`--stage2-rematch`) runs and reports exact $\Delta W$ distortion.
- [ ] FEFx audit confirms zero feasible envy across active territorial assignments.
- [ ] All code changes pass flake8/black formatting and standard repository lint checks.
- [ ] Antigravity conducts final mathematical review and signs off on verification certificates.
