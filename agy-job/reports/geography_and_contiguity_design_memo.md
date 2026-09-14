# Group 2 National Plan: Geography and Contiguity Design Memo

## 1. Diagnosis of the Bottleneck

The simultaneous enforcement of spatial constraints (single-commodity flow connectivity and pair-distance limits) alongside business constraints across 14 symmetric districts creates an overwhelmingly weak LP relaxation and a massive symmetry problem. The relaxed run demonstrates that the core business assignment is highly feasible and easy to solve. However, when indexed districts ($j=1..14$) are assigned over a spatial graph, the solver is forced into a deep, symmetric branch-and-bound tree where fractional connectivity and distance violations are nearly impossible to separate out efficiently without exploring equivalent permutations of the 14 districts.

## 2. Recommended Method: Support-Based Exact Reformulation

The recommended method is an exact **Set Partitioning Reformulation** over pre-generated valid geographic supports. Because the state graph is small ($|V| \approx 52$) and districts are strictly capped at 6 planning units, we can exhaustively enumerate all valid geographic supports and eliminate spatial constraints from the MILP entirely. 

Let $\mathcal{C}$ be the set of all valid supports $S \subseteq V$ such that:
- The induced subgraph $G[S]$ is connected.
- $\text{diameter}(S) \le D_{max}$ (900 km, or 1200 km for overrides).
- $|S| \le 6$.

**Variables:**
- $x_S \in \mathbb{Z}_{\ge 0}$: The number of National districts using exactly the support $S$.
- $y_{v,S} \ge 0$: The fractional opportunity of unit $v$ assigned to a district with support $S$.

**Master Problem:**
1. **Count:** $\sum_{S \in \mathcal{C}} x_S = 14$
2. **Coverage:** $\sum_{S \in \mathcal{C}: v \in S} y_{v,S} = 1$ for all eligible units $v \in V$.
3. **Bands:** $553.72 \cdot x_S \le \sum_{v \in S} w_v y_{v,S} \le 676.77 \cdot x_S \quad \forall S \in \mathcal{C}$
4. **Share limits:** $0.05 \cdot x_S \le y_{v,S} \le x_S \quad \forall S \in \mathcal{C}, v \in S$
5. **Parent Purity & Macro Limits:** Modeled via auxiliary variables tracking pure supports containing `CA1` or `CA2`.

By using anonymous support variables $x_S$ instead of district indices, we completely break the model's symmetry while guaranteeing spatial validity by construction. 

## 3. Proof Sketch of Hard Constraints

- **Exactly 14 districts:** Enforced directly by the sum over $x_S$.
- **Opportunity bands & Coverage:** Enforced by the standard linear inequalities over $y_{v,S}$.
- **Contact & Share agreement:** Enforced by the $0.05 \cdot x_S \le y_{v,S} \le x_S$ bounds. If a support is chosen ($x_S \ge 1$), it mandates at least a 5% contact share for every node in that support.
- **Connectivity, Max 6 Units, and Distance:** Enforced strictly by construction. Any support $S$ with disconnected nodes, $>6$ units, or distance violations is never added to $\mathcal{C}$.
- **Parent Purity:** Handled by linear expressions coupling supports containing `CA1` and `CA2`. Because the spatial footprint of any support is exact and fixed, the purity logic matches the original index-based model perfectly.

## 4. Pseudocode for the Master Formulation

```python
def generate_valid_supports(V, E, distances, max_size=6, max_dist=900):
    supports = []
    for S in all_connected_subgraphs(V, E, max_size):
        if is_pairwise_distance_valid(S, distances, max_dist):
            supports.append(S)
    return supports

def build_and_solve_master(supports, w, eligible_units, relaxed_assignment):
    model = MILP()
    x = {S: model.add_integer_var(lb=0, ub=14) for S in supports}
    y = {(v, S): model.add_continuous_var(lb=0) for S in supports for v in S}
    
    model.add_constraint(sum(x[S] for S in supports) == 14)
    
    for S in supports:
        opp = sum(w[v] * y[v, S] for v in S)
        model.add_constraint(opp >= 553.724691 * x[S])
        model.add_constraint(opp <= 676.774623 * x[S])
        for v in S:
            model.add_constraint(y[v, S] >= 0.05 * x[S])
            model.add_constraint(y[v, S] <= x[S])
            
    for v in eligible_units:
        model.add_constraint(sum(y[v, S] for S in supports if v in S) == 1.0)
        
    # Optional: Objective to minimize L1 deviation from relaxed_assignment y-shares
    model.set_objective(minimize_changes(y, relaxed_assignment))
    
    return model.solve()
```

## 5. Bounded Experiment Matrix

| Run | Step | Time Limit | Decisive Output |
|---|---|---|---|
| A | Generate $\mathcal{C}$ | 60s | Count of valid supports. (Fails if computationally explosive, e.g. $>500,000$). |
| B | Master MILP (Feasibility) | 300s | Provably infeasible certificate, OR a valid state-level incumbent. |
| C | Master MILP (Min-Change) | 600s | Valid incumbent minimizing delta from the relaxed assignment. |

## 6. Independent Validation Checks & Certificate

**Certificate Format:** A JSON dictionary mapping arbitrary IDs `1..14` to a sub-dictionary of `{ state: share }`, extracted directly from the non-zero $x_S$ and $y_{v,S}$ values. 

**Independent Checker:** A standalone script that reads the JSON certificate and the instance data `(V, E, w, centroids)`. It must assert:
1. Exactly 14 dictionaries exist.
2. $\sum y_v = 1.0$ for all eligible states.
3. For every district, the keys form a connected subgraph in `E`.
4. For every district, the maximum pairwise distance between keys is $\le 900/1200$ km.
5. `CA1`/`CA2` conditional parent purity rules are satisfied.

No MILP solver is required to run the independent checker. 

## 7. Expected Failure Modes and Fallback

- **Expected Failure Mode:** While connected subgraphs of size $\le 6$ are computationally small for planar graphs (~tens of thousands), highly dense regional connectivity or liberal overrides could cause the generation of $\mathcal{C}$ to exceed memory or time limits.
- **Fallback Method (LNS Repair):** If exact formulation generation is intractable, fall back to a **Large Neighborhood Search (LNS)**. Start from the relaxed incumbent. Iteratively select 2-4 districts with spatial violations, unassign their units, fix the other districts, and solve a heavily restricted version of the original MILP to repair only the destroyed subset. 

## 8. Ranked Comparison with Alternatives

1. **Support-Based Exact Formulation (Recommended):** Best for proving true infeasibility or finding a mathematically exact solution fast. It guarantees spatial constraints by construction and destroys solver symmetry.
2. **LNS / Fix-and-Optimize Repair:** Very pragmatic and scalable regardless of network density. It will rapidly find *a* feasible solution starting from the relaxed incumbent, but it cannot rigorously prove infeasibility if it fails.
3. **Lazy Separation Cuts (Branch-and-Cut):** Keep the original indexed formulation but drop spatial rows, adding them back as lazy cuts when violated by integer solutions. This suffers from the exact same massive symmetry as the original model and often stalls finding an incumbent.

## 9. Minimal Implementation Plan

- **Symbols:** Add a new `--method exact_support` flag in `tools/group2_run.py`.
- Add support generation utilities adjacent to existing graph tooling.
- Map the output $x_S$ and $y_{v,S}$ structures back into the standard `assignment.csv` format within the runner.
- No edits to core constraints, just a parallel model builder that bypasses `z_vj` and single-commodity flow rows entirely.
- Add an explicit independent certificate validator inside `tests/test_group2_run.py` to audit the output blindly.
