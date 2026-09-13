# Math and Implementation Review: `docs/MODEL_FULL.md`

**Review Date:** 2026-09-13  
**Reviewer:** Antigravity  
**Target Document:** [`docs/MODEL_FULL.md`](file:///Users/Shared/sv-ntlee/repos/td/.claude/worktrees/agy-math-review/docs/MODEL_FULL.md)  
**Target Codebase:** [`td/solvers/level0.py`](file:///Users/Shared/sv-ntlee/repos/td/.claude/worktrees/agy-math-review/td/solvers/level0.py), [`tools/full_plan.py`](file:///Users/Shared/sv-ntlee/repos/td/.claude/worktrees/agy-math-review/tools/full_plan.py), [`td/solvers/centers.py`](file:///Users/Shared/sv-ntlee/repos/td/.claude/worktrees/agy-math-review/td/solvers/centers.py), [`td/solvers/state_splits.py`](file:///Users/Shared/sv-ntlee/repos/td/.claude/worktrees/agy-math-review/td/solvers/state_splits.py), [`tools/plan_realise.py`](file:///Users/Shared/sv-ntlee/repos/td/.claude/worktrees/agy-math-review/tools/plan_realise.py), [`td/channel.py`](file:///Users/Shared/sv-ntlee/repos/td/.claude/worktrees/agy-math-review/td/channel.py), [`td/stage2_state.py`](file:///Users/Shared/sv-ntlee/repos/td/.claude/worktrees/agy-math-review/td/stage2_state.py).

---

## Executive Summary

The mathematical formulation in [`docs/MODEL_FULL.md`](file:///Users/Shared/sv-ntlee/repos/td/.claude/worktrees/agy-math-review/docs/MODEL_FULL.md) accurately captures the core equations, variables, and constraints implemented in the MILP model (`Level0Problem` in `td/solvers/level0.py`), the transportation LP (`td/solvers/centers.py`), the cell graph contiguity repair (`tools/plan_realise.py`), and the Nash matching algorithm (`td/channel.py` and `td/stage2_state.py`).

However, there are several **material discrepancies and operational deviations** between the document's theoretical description and the actual pipeline code. The most significant finding is an **architectural order reversal in staffing**: Stage 2 staffing is solved *before* Level 2 realization (at the state-share level) rather than *after* realization on the realized zip territories.

---

## 1. Material Deviations

### 1.1 Architectural Order of Staffing (Level 0 $\rightarrow$ Stage 2 $\rightarrow$ Level 2 vs Level 0 $\rightarrow$ Level 2 $\rightarrow$ Stage 2)
* **Document Statement (Lines 12–19, 176):**
  The document states that the problem is solved sequentially in three levels:
  1. Level 0 (The plan MILP at state $\times$ channel grain).
  2. Level 2 (The realization: zips into districts).
  3. Stage 2 (The staffing: maximum-weight assignment on log gains).
  Section 5 defines representative gains over realized zip sets $A_j$:
  $$g_{i,j} = \sum_{z \in A_j} \sum_{c \in B_j} \left[ c_1 S_i(z,c) + c_2 (T_{z,c} - S_i(z,c)) + c_{\text{free}} S_{\text{free}}(z,c) + \lambda M_{z,c} \right]$$
* **Code Implementation:**
  * In [`tools/full_plan.py`](file:///Users/Shared/sv-ntlee/repos/td/.claude/worktrees/agy-math-review/tools/full_plan.py#L1851-L1858), Stage 2 is executed immediately after Level 0 at **state $\times$ channel grain** via [`stage2_state.state_stage2`](file:///Users/Shared/sv-ntlee/repos/td/.claude/worktrees/agy-math-review/td/stage2_state.py#L191), saving `staffing.json`. Rep gains are approximated by weighting state-channel utilities by state share $y_{s,j}$:
    $$g_{i,j}^{\text{state}} = \sum_s y_{s,j} \sum_{c \in B_j} u_i(s, c)$$
  * In [`tools/plan_realise.py`](file:///Users/Shared/sv-ntlee/repos/td/.claude/worktrees/agy-math-review/tools/plan_realise.py#L16-L19,L1312), Level 2 reads `staffing.json` and attaches the predetermined rep to each district. **Matching is never re-solved on the realized zip sets $A_j$**.
  * While `td/channel.py::gain_matrix` and `td/channel.py::match` implement the zip-level assignment described in Section 5, the end-to-end full-problem driver binds staffing prior to zip realization.

### 1.2 Minimum State Share Parameter $\eta$ (0.05 vs 0.01)
* **Document Statement (Line 43):**
  $$\eta = 0.05 \quad \text{the smallest share of a state a district may hold (a contact is at least } \eta \text{)}$$
* **Code Implementation:**
  In [`tools/full_plan.py`](file:///Users/Shared/sv-ntlee/repos/td/.claude/worktrees/agy-math-review/tools/full_plan.py#L225), the CLI default for `--eta` is `0.01`:
  ```python
  ap.add_argument("--eta", type=float, default=0.01,
                  help="minimum share a state flagged z_sj=1 must actually send")
  ```
  `build_level0` requires `eta` as an explicit parameter. Running the full plan driver with default options sets $\eta = 0.01$, allowing five-fold smaller slivers than the $0.05$ stated in the document.

### 1.3 Band Half-Width $\delta$ and Defaults (0.10 vs 0.20)
* **Document Statement (Line 42):**
  $$L_B = (1 - \delta) \tau_B, \quad U_B = (1 + \delta) \tau_B, \quad \delta = 0.10$$
* **Code Implementation:**
  In [`tools/full_plan.py`](file:///Users/Shared/sv-ntlee/repos/td/.claude/worktrees/agy-math-review/tools/full_plan.py#L210-L216), default CLI arguments are `--band-lo 0.8` and `--band-hi 1.2` (corresponding to $\delta = 0.20$). While `--delta` can be explicitly specified to override them with $0.10$, the code default is $\pm 20\%$, not $\pm 10\%$.

### 1.4 `other_first` and `catch-all` Band Floors ($0.5\tau$ vs $1.0 L$)
* **Document Statement (Lines 131–132):**
  * `other_first`: WHFI_PLUS slots over named states with floor $L = 0.5 \tau$.
  * `catch-all`: one slot per fine channel over residual, floor $0.5 \tau$.
* **Code Implementation:**
  In [`tools/full_plan.py`](file:///Users/Shared/sv-ntlee/repos/td/.claude/worktrees/agy-math-review/tools/full_plan.py#L312-L315,L1484-L1495), the floor multiplier is controlled by `--other-floor`, which **defaults to 1.0**:
  ```python
  ap.add_argument("--other-floor", type=float, default=1.0, metavar="F",
                  help="the catch-all stage's band floor as a fraction of L (default 1.0)")
  ```
  Unless `--other-floor 0.5` is passed, the floor is $1.0 \times L$ ($=(1 - \delta)\tau$), not $0.5\tau$.

### 1.5 Lexicographic Order in `other_first` (`cover_last`)
* **Document Statement (Lines 114–121, 131):**
  Lexicographic optimization order is specified strictly as:
  1. `cover_B`
  2. `cover_merged`
  3. `contacts`
  4. `compactness`
* **Code Implementation:**
  In [`tools/full_plan.py`](file:///Users/Shared/sv-ntlee/repos/td/.claude/worktrees/agy-math-review/tools/full_plan.py#L631-L647,L1656), `other_first` runs with `cover_last=True`, which inverts the priority to **minimize contacts first, then maximize coverage**:
  ```python
  passes = contacts + cover if cover_last else cover + contacts
  ```
  This is done intentionally so that named states take the fewest contacts before absorbing remaining mass.

### 1.6 Initialization of District Centers at Level 2
* **Document Statement (Lines 147–148):**
  "...with the district centres $c_j$ initialised from the slot's seed states and moved by up to five Lloyd rounds..."
* **Code Implementation:**
  In [`tools/plan_realise.py`](file:///Users/Shared/sv-ntlee/repos/td/.claude/worktrees/agy-math-review/tools/plan_realise.py#L227-L243), [`initial_centers`](file:///Users/Shared/sv-ntlee/repos/td/.claude/worktrees/agy-math-review/tools/plan_realise.py#L227) initializes $c_j$ as the **target-weighted centroid of all states slot $j$ touches** (or mean of state centroids if unweighted), rather than the single greedy seed state chosen during Level 0.

### 1.7 Absence of `--band` Flag for Split-State Transportation LP
* **Document Statement (Line 155):**
  $$\sum_{z \in s} M_z x_{z,j} = y_{s,j} M_s \quad \forall j \quad \text{(a band of } \pm b \text{ around it under } \text{--band)}$$
* **Code Implementation:**
  * While the low-level solver [`td/solvers/centers.py::assign`](file:///Users/Shared/sv-ntlee/repos/td/.claude/worktrees/agy-math-review/td/solvers/centers.py#L154) has an unused `band: float = 0.0` argument, [`td/solvers/state_splits.py::realise`](file:///Users/Shared/sv-ntlee/repos/td/.claude/worktrees/agy-math-review/td/solvers/state_splits.py#L948) does not accept `band` and calls `assign` with `band=0.0`.
  * [`tools/plan_realise.py`](file:///Users/Shared/sv-ntlee/repos/td/.claude/worktrees/agy-math-review/tools/plan_realise.py) provides no `--band` argument for the transportation LP cut (only `--band-slack` for the post-LP contiguity repair).
  * Consequently, the split-state LP cut always enforces exact equality without banding.

### 1.8 Contiguous Split-State Cut Status
* **Document Statement (Lines 196–198):**
  "Contiguity at level 2 is enforced by repair on the cell graph, not by rows in the LP; the power diagram is not contiguity-aware, which is what the contiguous split-state cut on the branch `worktree-contig-cut` is testing."
* **Code Implementation:**
  The contiguous split-state cut is no longer merely external branch research; it is already fully ported into [`tools/plan_realise.py`](file:///Users/Shared/sv-ntlee/repos/td/.claude/worktrees/agy-math-review/tools/plan_realise.py#L59-L65,L295-L412) under `--split-cut contiguous` via [`contiguous_cut`](file:///Users/Shared/sv-ntlee/repos/td/.claude/worktrees/agy-math-review/tools/plan_realise.py#L295).

---

## 2. Nuances & Secondary Discrepancies

### 2.1 Compactness Objective Formulation
* **Document Statement (Line 120):**
  $$\text{compactness} \quad \min \sum_{s,j} \varepsilon W_{s,j} D_{s,j} y_{s,j}$$
* **Code Implementation:**
  In [`td/solvers/level0.py`](file:///Users/Shared/sv-ntlee/repos/td/.claude/worktrees/agy-math-review/td/solvers/level0.py#L1208-L1215), `compactness_pass` minimizes:
  $$\min \sum_{s,j} z_{s,j} + \sum_{s,j} \varepsilon W_{s,j} D_{s,j} y_{s,j}$$
  Since `pin_contacts` is already pinned before `compactness_pass` runs, this is mathematically equivalent in optimal solutions, but the linear cost vector explicitly retains unit costs on $z$. If $D \equiv 0$, the compactness pass is skipped altogether ([`tools/full_plan.py:650`](file:///Users/Shared/sv-ntlee/repos/td/.claude/worktrees/agy-math-review/tools/full_plan.py#L650)).

### 2.2 Unused Tie-break Penalty $\pi_{z,j}$ at Level 2
* **Document Statement (Line 153):**
  $$\min \sum_{z \in s} \sum_j M_z \left(\|p_z - c_j\|^2 + \pi_{z,j}\right) x_{z,j}$$
* **Code Implementation:**
  `tools/plan_realise.py` invokes `ss.realise` without a `tiebreak` parameter, so $\pi_{z,j} \equiv 0$ in all standard pipeline runs.

### 2.3 Pass Timeout Handling on Empty Plans
* **Document Statement (Lines 123):**
  "A pass that hits the time limit pins its incumbent and is recorded as uncertified."
* **Code Implementation:**
  In [`tools/full_plan.py`](file:///Users/Shared/sv-ntlee/repos/td/.claude/worktrees/agy-math-review/tools/full_plan.py#L687-L692), if the stage's first cover pass times out with an empty plan ($v \le 10^{-9}$), the code refuses to pin the incumbent and raises `ss.SolveFailure` so the driver or grid can fail/retry.

### 2.4 Unlisted Operational Features in Document
The code contains several active constraints and parameters not documented in `MODEL_FULL.md`:
* **`--dist-max-state ST=KM,...`**: Relaxes $d_{\text{max}}$ on a per-state basis (e.g. for large western states like MT and WY) in both Level 0 pair rows and Level 0 sweep.
* **`--national-states ST,...`**: Restricts pure $N$ districts to named states and forces remaining national mass into PLUS bundles.
* **`plus_pair` retry mechanism**: Automatically catches infeasibility in the sequential FI stage, forbids `WH_PLUS` on the clashing states, and re-solves WH and FI.

---

## 3. Verification Matrix

| Section / Feature | Relation / Description in `MODEL_FULL.md` | Implementation Status in Code | Notes |
| :--- | :--- | :--- | :--- |
| **Sets & Bundles** | $S$ (49), $C$ (4), 7 bundles, slots $J_B$, arcs $A_S$, zips $Z$, reps $R$ | **Exact match** | Defined in [`td/channels.py`](file:///Users/Shared/sv-ntlee/repos/td/.claude/worktrees/agy-math-review/td/channels.py) |
| **Data: $\eta$** | $\eta = 0.05$ | **Deviation** | CLI default is `0.01` in [`tools/full_plan.py`](file:///Users/Shared/sv-ntlee/repos/td/.claude/worktrees/agy-math-review/tools/full_plan.py#L225) |
| **Data: $\delta$** | $\delta = 0.10$ | **Deviation** | CLI default is $\delta = 0.20$ (`band_lo=0.8, band_hi=1.2`) |
| **Data: $n_{\max}, d_{\max}$** | $n_{\max} = 6$, $d_{\max} = 900\text{ km}$ | **Match** | Configurable via CLI flags |
| **Data: $a_s$** | $a_s = \max(0, W_s / \text{cap}_s - \tau_B)$ | **Exact match** | In `tools/full_plan.py::_band_break_allowance` |
| **Data: Utility Coeffs** | $c_1 = 1-\lambda, c_2 = \theta(1-\lambda), c_{\text{free}} \in \{c_2, c_1, \lambda\}$ | **Exact match** | In `td/model.py::coefficients` |
| **Level 0 Variables** | $y_{s,j}, z_{s,j}, u_j, r_{s,j}, f_{a,j}$ | **Exact match** | Built in `td/solvers/level0.py::build_level0` |
| **Level 0 Core Rows** | `cover`, `yz`, `yz_lo`, `zu`, `band_lo`, `band_hi`, `root`, `rz`, `flow_tail`, `flow_head`, `net` | **Exact match** | Row matrices built in `td/solvers/level0.py:387-446` |
| **Level 0 Extent Rows** | `cap_n`, `cap_dist`, `serve`, `max_splits`, `plus_pair`, `order_u`, `order_mass` | **Exact match** | In `td/solvers/level0.py:447-502` and helper functions |
| **Level 0 Objectives** | Lexicographic `cover_B`, `cover_merged`, `contacts`, `compactness`, `pin_<pass>` | **Exact match** | In `td/solvers/level0.py::solve_passes` |
| **Pass: `other_first`** | WHFI_PLUS over named states, floor $0.5\tau$ | **Deviation** | Default floor is $1.0L$; uses `cover_last` (contacts first) |
| **Pass: `catch-all`** | One slot per fine channel, floor $0.5\tau$ | **Deviation** | Default floor is $1.0L$; slots calculated via `ceil(avail / L_B)` |
| **Pass: `sweep`** | Deterministic residual cell absorption | **Exact match** | In `tools/full_plan.py::_sweep` |
| **Level 2 LP Model** | Power diagram transportation LP with exact mass targets | **Exact match** | In `td/solvers/centers.py::assign` |
| **Level 2 LP Band** | `(a band of ± b around it under --band)` | **Deviation** | `--band` not exposed in `state_splits.realise` or `plan_realise.py` |
| **Level 2 Contiguity** | Cell graph Voronoi rook graph, $\sigma = 0.02\tau_B$ band slack, bridging | **Exact match** | In `tools/plan_realise.py::repair` |
| **Level 2 Sweeps** | Winner takes overlap pieces; `--sweep-zips` for cell adjacency | **Exact match** | In `tools/plan_realise.py::_sweep_zips` |
| **Stage 2 Matching** | Nash welfare $\max \sum \log(g) w$, Hungarian assignment | **Exact match** | In `td/channel.py::match` and `td/stage2_state.py` |
| **Pipeline Order** | Level 0 $\rightarrow$ Level 2 $\rightarrow$ Stage 2 | **Deviation** | Actual execution is Level 0 $\rightarrow$ Stage 2 (state) $\rightarrow$ Level 2 |
