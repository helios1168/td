# VERIFY — Track 2, the state-level minimum-splits MILP

Target: `docs/BORDERS_PLAN.md` lines 86–144 (`## Track 2 — the state-level minimum-splits
MILP`). Artifacts: `docs/verify/state_splits_checks.py` (C1, C1b, C2, C2b, C3, C5) and
`docs/verify/state_splits_c3_band.py` (C3 addendum). Both deterministic, seeds pinned;
python 3.13.15, numpy 2.5.2, scipy 1.18.1; every MILP solved with `mip_rel_gap = 0.0`.

```
/Users/ntlee/projects/td/.venv/bin/python3 docs/verify/state_splits_checks.py
/Users/ntlee/projects/td/.venv/bin/python3 docs/verify/state_splits_c3_band.py
```

## Verdicts

| # | Claim | Verdict |
|---|---|---|
| 1 | the scf block admits a district's z-set iff it is connected and non-empty | **VERIFIED** (needs `r` integral) |
| 1b | contiguity of the *realised* district (`y_sj > 0`) | **REFUTED** — a paid bridge state buys a disconnected district |
| 2 | `ε = 0.5 / Σ M_s D_sj y⁰_sj` keeps the tie-break under half a split for every feasible `y` | **REFUTED** — and it buys splits |
| 3a | the balance pass keeps every band constraint | **VERIFIED** |
| 3b | the balance pass never widens the spread | **REFUTED** at δ = 10% |
| 4 | `y⁰` is feasible at δ = 1.3% | **INCONCLUSIVE** (confidential data) |
| 5 | 900 + 900 + 900 + 2·107·18 variables | **VERIFIED** given S = 50, E = 107; **6 638 rows**; the prose's own node count is 49, not 50 |

## 1 — the scf contiguity block

Formal: fix `j`, fix `z ∈ {0,1}^S`. The block (`r_s ≤ z_s`, `Σ_s r_s = 1`, `f_uv + f_vu ≤
(N−1)z_u` and `≤ (N−1)z_v` per rook edge, net inflow at `s ≥ z_s − N·r_s`, `f ≥ 0`) is
feasible **iff** `{s : z_s = 1}` is non-empty and connected in the rook graph.

Attack: brute force over all 2^6 subsets of six 6-node graphs (path, cycle, 2×3 grid, star+edge,
two disjoint triangles, a graph with a cut vertex), comparing LP feasibility against BFS.
**384 subsets, 0 mismatches** (C1). The empty set is rejected — `Σ_s r_s = 1` with `r ≤ z`
forces a root inside the set, so every district is non-empty. That is intended (18 districts
must all exist) and is anyway implied by the band whenever δ < 1: `Σ_s M_s y_sj ≥ τ(1−δ) > 0`
forces some `y_sj > 0`, hence some `z_sj = 1`. So the `Σ_s r_sj = 1` row is redundant for
non-emptiness but load-bearing for contiguity; keep it.

Soundness argument behind the numbers: (⇐) route a spanning tree of the set toward the root;
each arc carries at most `|S|−1 ≤ N−1`, so the capacity is exactly, but only just, enough
(C1 shows capacity `|S|−2` fails). (⇒) summing the consumption rows over a component `C` not
containing the root gives `0 ≥ |C| > 0` — no flow crosses out of `C` because every edge leaving
it ends on an unselected node with zero capacity.

**Hypotheses that must hold in the build**: `r` is integral (the plan lists it under binaries);
`N ≥ 50 ≥ #states`; `f` split into two non-negative orientations per edge (the plan's
`2 × 107 × 18` count implies this). C1b shows what a *continuous* `r` costs: with `r` split
0.5/0.5 the LP admits the disconnected set `{0,1} ∪ {4,5}`, i.e. any z-set whose components are
smaller than `N/2`. Harmless for correctness, but it is why scf relaxations are weak — expect
the branch-and-bound work, not the row count, to decide the runtime.

## 1b — but contiguity is imposed on `z`, not on the district

Contiguity binds the z-set; `y_sj ≤ z_sj` allows `z_sj = 1, y_sj = 0`. A state can therefore be
bought as a **bridge** for one split, and the district realised at level 2 (which owns only
states with `y_sj > 0`) is disconnected. Smallest instance (C2b): path A–B–C, masses 1, 2, 1,
τ = 2, δ = 0. The optimum is `z_0 = {A,B,C}`, `y_0 = {A, C}`, `z_1 = y_1 = {B}` — district 0 is
A ∪ C, disconnected, at a cost of 1 split. Nothing in the formulation forbids it; the split
counter is the only price. Either drop the state from the split report when `y_sj = 0`, or add
`z_sj ≤ y_sj / y_min` (equivalently force `y_sj ≥ η z_sj`) so a z-flag implies real mass.

## 2 — the ε calibration

The claim, literally: for every feasible `y`, `ε Σ_s Σ_j M_s D_sj y_sj < 0.5`. False. The term
is linear in `y` on a polytope whose only per-state row is `Σ_j y_sj = 1`, so its maximum over
feasible `y` is at most `Σ_s M_s max_j D_sj` and generally close to it; `ε` is calibrated at
`y⁰`, one particular point. On the synthetic 50×18 geometry in C2(c),
`Σ_s M_s max_j D_sj / Σ_s M_s D_sj y⁰_sj = 48.1`, so the tie-break term can reach **24 splits**,
not 0.5.

The operational claim ("never buys one") also fails, and the smallest counterexample I found is
4 states (C2b in the script, section (b)): path A–B–C–D, `M = 10` each, `K = 2`, `τ = 20`,
`δ = 0`, `D = [[1,100],[100,1],[1,100],[100,1]]` (A, C prefer district 0; B, D prefer district 1).

- minimum split count = **0** (`{A,B} | {C,D}` is connected and exactly balanced),
  confirmed by solving with `ε = 0`;
- `V(y⁰) = 40` for the crossed composition `y⁰`, so `ε_plan = 0.0125`;
- at `ε_plan` the MILP returns **2 splits**, objective 2.5 versus 25.25 for the 0-split
  optimum. The tie-break bought two splits.

Why: the guarantee needs `V(y*) ≤ 2·V(y⁰)` where `y*` is the compactness-best solution at the
minimum split count. That holds automatically only when `y⁰` itself attains the minimum split
count. Whenever the MILP finds *fewer* splits than the committed map (the interesting case),
the min-split solutions can be far less compact than `y⁰` and the ordering inverts.

Correct calibration, checkable a priori (the plan should use it):

```
eps = 0.5 / sum_s M_s * max_j D_sj          # term <= 0.5 for every feasible y
```

On the synthetic instance this is `0.0208 × ε_plan`, and it recovers the 0-split optimum in the
counterexample. If that is felt to be too small numerically, the sharp version is
`ε < 1 / Σ_s M_s (max_j D_sj − min_j D_sj)`, which only needs the *range* of the term to be
below one split; either way the constant must not depend on `y⁰`.

## 3 — the balance pass

**Band (VERIFIED).** The pass LP (`min t`, `t ≥ |Σ_s M_s y_sj − τ|`, `Σ_j y_sj = 1`,
`0 ≤ y ≤ z`, `z` fixed) has the MILP's own `y` in its feasible set, so
`t* ≤ max_j |mass_j − τ|_MILP ≤ δτ`, and every district mass stays inside `[τ(1−δ), τ(1+δ)]`
without the band rows being carried over. `z` is fixed, so the split count and contiguity are
untouched. C3(ii) exhibits the intended behaviour: 3 states on a path, `M = 3` each, τ = 4.5,
δ = 0.2, minimum splits = 1; the MILP puts 80% of the middle state in district 0 (masses
5.4 / 3.6, the band's upper edge), the pass returns 50/50 (masses 4.5 / 4.5, `t* = 0`).

**Spread (REFUTED).** The pass minimises `max_j |mass_j − τ|`, not `max_j mass_j − min_j mass_j`.
Because `Σ_j (mass_j − τ) = 0`, `maxdev ≤ spread ≤ 2·maxdev`, so min-maxdev pins the spread only
within a factor 2, and ties in `t` are broken arbitrarily by the simplex. Counterexample at the
grid's largest δ (`state_splits_c3_band.py`, δ = 0.10, 5 states, 3 districts, `M =
[1.9222, 1.4486, 1.0872, 0.2696, 0.6765]`, τ = 1.8014, the `y` the MILP would return being an
LP optimum against a random tie-break cost inside the band):

```
masses MILP [1.9222 1.7637 1.7182]  spread 0.2040  maxdev 0.1208
masses pass [1.9222 1.8014 1.6805]  spread 0.2417  maxdev 0.1208
```

Same `t`, spread up 18%. None found at δ ≤ 5% in 2 000+ feasible trials each, so this is a
tail effect at wide bands, not a routine one — but the plan's test ("the balance pass never
widens the spread") will eventually fail as written. Fix: either state the invariant as
*max deviation* (true), or make the pass lexicographic — minimise `t`, then minimise
`max_j mass_j − min_j mass_j` at `t = t*`; the second LP is the same size.

## 4 — `y⁰` feasible at δ = 1.3%

**INCONCLUSIVE**: the composition of the committed draw comes from the confidential instance,
which is not in this worktree. For the CLI to settle it, it must print, for the committed
labelling restricted to the MILP's universe (lower 48 + DC, i.e. **after** removing AK, HI and
the `??` zips):

1. `tau_reduced = (Σ_s M_s over the included states) / 18` — note this is *not* the full-instance
   τ; dropping 0.09τ of mass moves it, and the band must be applied to the reduced τ;
2. per district `j`, `mass_j = Σ_s M_s y⁰_sj` and `dev_j = mass_j / tau_reduced − 1`;
3. `max_j |dev_j|` — the claim is this is `≤ 0.013`;
4. per district, whether `{s : y⁰_sj > 0}` is connected in the state rook graph — feasibility of
   `y⁰` needs contiguity too, and a zip-level district can touch two states that are not
   adjacent to each other (it would then need a bridge state, §1b, and `y⁰`'s split count in
   the warm start must include it);
5. the split count `Σ_s (|{j : y⁰_sj > 0}| − 1)`, which is the upper bound being claimed.

## 5 — size

Variables at the plan's `S = 50`, `K = 18`, `E = 107`: `z` 900 + `r` 900 + `y` 900 +
flow `2·107·18 = 3852` = **6 552**, of which 1 800 integral. The edge count checks out: a
hand-entered lower-48 + DC rook adjacency (C5, symmetry verified) gives **107** edges once the
Four-Corners point contacts (UT–NM, AZ–CO) are excluded and DC–MD, DC–VA are included; 105
without DC, the standard figure.

Constraint rows (bounds `0 ≤ y ≤ 1` and the binary ranges are variable bounds, not rows):

| block | rows |
|---|---|
| `Σ_j y_sj = 1` | 50 |
| `y_sj ≤ z_sj` | 900 |
| `r_sj ≤ z_sj` | 900 |
| band (two-sided) | 18 |
| `Σ_s r_sj = 1` | 18 |
| edge capacity, 2 rows per edge per district | 3 852 |
| net inflow `≥ z_sj − N r_sj` | 900 |
| **total** | **6 638** |

(10 508 if the band is written as two one-sided rows and the capacity is imposed per directed
arc rather than per arc pair.) Small; "seconds" is plausible for the row count, though the weak
scf relaxation (§1b) is where any surprise will come from.

**Inconsistency to fix**: the prose says `s` ranges over "the 49 lower-48 states plus DC" — that
is 48 states + DC = 49 nodes — while the size line uses 50. At `S = 49` the counts are 882 each
for `z`, `r`, `y`, 6 498 variables and 6 583 rows. `N = 50` in the flow bound is still safe
(any `N ≥ #states` works), but the split counter `Σ_s (Σ_j z_sj − 1)` and the `Σ_j y_sj = 1`
row count follow the true node set, so the node list has to be pinned before the build.

## Caveats

- The MILP counterexamples use freely chosen `D` matrices, not squared distances from a planar
  embedding. §2's failure mode (min-split solutions much less compact than `y⁰`) is a property
  of the calibration, not of the geometry, but its *magnitude* on the real instance is unknown;
  the 48× ratio in C2(c) is a synthetic planar geometry, not the channel.
- §3's spread counterexample uses a random tie-break cost as a stand-in for the compactness
  objective, and appears only at δ ≥ 10%.
- Tolerances: LP/MILP feasibility at HiGHS defaults, `mip_rel_gap = 0.0`; all comparisons here
  are exact-integer (split counts) or separated by ≥ 1e-2 in the reported quantity, well above
  tier-1 `CERT_TOL = 1e-8`.
- Not checked: level 2 (`centers.assign` with `targets=`), the Lloyd rounds, the
  `place_by_state` completion, and anything requiring the confidential instance.
