# CODEVERIFY — Track 2, `td/solvers/state_splits.py`

Model: `docs/BORDERS_PLAN.md` §"Track 2 — the state-level minimum-splits MILP" (lines 89–157, as
amended by the three corrections) plus `docs/VERIFY_state_splits.md`. Code: `td/solvers/
state_splits.py` (`build_milp`, `solve`, `eps_lexicographic`, `balance_pass`, `realise`,
`connected`) and `tests/test_state_splits.py`.

Environment: python 3.13.15, numpy 2.5.2, scipy 1.18.1, `/Users/ntlee/projects/td/.venv/bin/
python3`, run from `/Users/ntlee/projects/td/.claude/worktrees/vbl`. All MILPs at
`mip_rel_gap = 0.0` (trap 12). All seeds pinned in the artifacts.

## Summary

| # | mapping | verdict |
|---|---|---|
| 1 | `build_milp` rows ↔ the plan's formulation (objective, place, `η z ≤ y ≤ z`, band, scf) | **VERIFIED** |
| 2 | `connected` ↔ connectivity in the rook graph | **VERIFIED** |
| 3 | `eps_lexicographic` ↔ `0.5 / Σ_s M_s max_j D_sj`, and never buys a split | **VERIFIED** |
| 4 | `balance_pass` ↔ the two lexicographic LPs | **VERIFIED** |
| 5 | `realise` ↔ level 2 (whole states, targets, Lloyd rounds, `n_fractional`) | **VERIFIED** |
| 6a | size: 6,498 variables / 1,764 integral / **6,583 rows** | **REFUTED** — 11,317 rows |
| 6b | "`scipy.optimize.milp` on HiGHS … Seconds." | **REFUTED on synthetic real-shape instances** (300 s, 10.9 % gap); INCONCLUSIVE for the real instance |

4 VERIFIED, 2 REFUTED (both in the §"Size" bullet; neither is a soundness error), 0 INCONCLUSIVE
among the six mapping rows. Type check: `uvx pyright` on the two owned files → **4 errors**, all
`Bounds(lb=ndarray, ub=ndarray)` scipy-stub artifacts (`centers.py` shows the same class of
noise, 3 errors — repo baseline, not a regression). Tests: `tests/run_all.py` → **305 passed, 0
failed, 0 skipped**, of which 10 are `test_state_splits.py`. Oracle scripts: **0 failing checks**
in `codeverify_state_splits_edge.py`, 1 failing check in `codeverify_state_splits.py` (row 6a).

Artifacts (all under `docs/verify/`, rerunnable from the worktree root):

```
/Users/ntlee/projects/td/.venv/bin/python3 docs/verify/codeverify_state_splits.py
/Users/ntlee/projects/td/.venv/bin/python3 docs/verify/codeverify_state_splits_edge.py
/Users/ntlee/projects/td/.venv/bin/python3 docs/verify/codeverify_state_splits_scale.py 300
/Users/ntlee/projects/td/.venv/bin/python3 tests/run_all.py
uvx pyright --pythonpath /Users/ntlee/projects/td/.venv/bin/python3 td/solvers/state_splits.py tests/test_state_splits.py
```

## Mapping table

| model object | code symbol |
|---|---|
| `min Σ_s(Σ_j z_sj − 1) + ε Σ M_s D_sj y_sj` | `state_splits.py:128-130` (`c`); `solve` reports `splits = z.sum() − S` at :234 |
| `Σ_j y_sj = 1` | block `"place"`, :146 |
| `y_sj ≤ z_sj` | block `"yz"`, :148 |
| `y_sj ≥ η z_sj`, η = 0.01 (plan bullet "Contact means mass") | block `"yz_lo"`, :153; `eta` default at :106 |
| band `τ(1−δ) ≤ Σ M_s y_sj ≤ τ(1+δ)` | block `"band"`, :159 (mass rows divided by τ) |
| `Σ_s r_sj = 1`, `r_sj ≤ z_sj`, r binary | blocks `"root"` :162, `"rz"` :164; `integrality` :195 |
| arc capacity `≤ (N−1) z` at both ends | blocks `"flow_tail"`/`"flow_head"`, :174-180 |
| net inflow `≥ z_sj − N r_sj` | block `"net"`, :182 |
| `ε = 0.5 / Σ_s M_s max_j D_sj` | `eps_lexicographic`, :244-258 |
| balance pass, two LPs | `balance_pass`, :261-339 (`res1` :315, `res2` :329) |
| level 2 (`assign` with `targets=`, 5 Lloyd rounds) | `realise`, :370-473; `rounds: int = 5` :371 |
| rook-graph connectivity | `connected`, :342-361 |
| warm start `y⁰` feasible at δ = 1.3 % | **no counterpart** (see Gaps) |
| CLI `tools/state_splits.py --incumbency-tiebreak` | **absent**; `realise(tiebreak=)` is the hook it would use |

---

### 1 — `build_milp` ↔ the formulation

```
CLAIM     the plan's MILP (objective, place, eta z <= y <= z, band, scf contiguity)
          <-> state_splits.build_milp / solve
ATTACK    (a) brute force: enumerate every z in {0,1}^(S x k) (4,096 / 64 patterns), drop the
          disconnected or empty columns using a hand-written BFS, and price the remaining ones
          with a *dense hand-built* share LP (min eps*M D y s.t. sum_j y = 1, eta z <= y <= z,
          band).  Five settings: 6-path EVEN d=0.001, 6-path ODD d=0.005, 6-path COMB d=0.03,
          the VERIFY-1b 3-state bridge (masses 1,2,1, tau=2, d=0, where eta bites), 6-cycle
          random masses/D d=0.05.  Compare split count AND objective value.
          (b) symbolic read-back: densify `A` and rebuild all eight blocks by hand from the
          plan's algebra on a 5-state, 3-district, 5-edge instance (eta = 0.02, delta = 0.07),
          including the arc-orientation convention, variable bounds and integrality.
          (c) scf alone: strip every block but root/rz/flow/net, pin z by bounds, and ask HiGHS
          for feasibility on all 2^6 subsets of five 6-node graphs (path, cycle, 2x3 grid,
          two triangles, star+edge) -> compare against BFS.
          (d) degenerate: S=1; k=1 with no edges (must be infeasible) and with a path (must be
          feasible); tau <= 0, shape mismatch, self-loop and out-of-range edges (must raise);
          eta = 0.9 forced infeasible; a zero-mass state.
VERDICT   VERIFIED
BASIS     numeric equality, tier 1 (CERT_TOL = 1e-8): split counts equal exactly in 5/5 cases;
          objectives agree to < 1e-7 absolute (e.g. 6-path ODD 1.035270554 both ways, bridge
          1.250000000 both ways).  scf: 320 subsets, 0 mismatches against BFS (matches
          VERIFY claim 1).  Band, `sum_j y = 1` and `y >= eta` hold on every returned solution,
          and every *realised* column ({s : y_sj > 0}) is connected -- VERIFY 1b's bridge is
          closed by the `yz_lo` block.  All 8 hand-rebuilt blocks matched `A` exactly, and the
          8 blocks account for all 131 rows (no undocumented row).
ARTIFACT  docs/verify/codeverify_state_splits.py  (functions m1, m1_rows, m1_scf) and
          docs/verify/codeverify_state_splits_edge.py
CAVEATS   Two deviations from the plan's *text*, neither changing the feasible set:
          (i) `N` in the flow bound is `S`, not the plan's literal 50; any N >= #states is sound
          (VERIFY §1 hypothesis), and S is the tightest such value.
          (ii) capacity is imposed per *directed arc* at both ends, not on `f_uv + f_vu` per arc
          pair as the plan/VERIFY row table assume.  Equally correct (the (=>) argument only
          needs zero capacity on arcs leaving the component) but a weaker LP relaxation, and it
          is half of row 6a's row-count gap.
          Also: `solve()["objective"]` is `res.fun`, which is the plan's objective **plus S**
          (`c[z] = 1` with no `-1` offset).  `splits` subtracts S and is right; only the
          reported `objective` carries the constant.  Brute force above compensates for it.
          Not covered: k > 4 or S > 6 for the enumeration oracle (2^(S k) blows up).
```

### 2 — `connected`

```
CLAIM     connected(z_col, edges) <-> "{s : z_sj = 1} connected in the state rook graph"
ATTACK    a hand-written BFS (queue-based; the module uses a stack-based DFS) run on every
          subset of: 6 fixed graphs (empty, single edge, path6, two disjoint triangles, star,
          a reversed/partial edge list) at S = 1, 3, 6, plus 200 random graphs on 2..7 nodes
          with a random edge count including 0 and complete.  Singletons, the empty set and
          edge lists given in reversed orientation are all included.
VERDICT   VERIFIED
BASIS     exact boolean agreement on 9,018 subsets, 0 mismatches.  The empty-set convention
          (True) matches the docstring; it never reaches the MILP, where `sum_s r_sj = 1`
          forbids an empty column (checked in row 1c).
ARTIFACT  docs/verify/codeverify_state_splits.py (m2)
CAVEATS   does not check that the *caller* passes the same edge list the MILP was built with.
```

### 3 — `eps_lexicographic`

```
CLAIM     eps = 0.5 / sum_s M_s max_j D_sj, and the tie-break never trades a split for
          compactness (the plan's amended bullet, VERIFY section 2)
ATTACK    (a) formula recomputed independently on 50 random (S, k) up to 8 x 4;
          (b) 60 random 6-state toys (path and cycle, k = 2, delta in {0, 2, 5, 10}%): solve
          twice, at `eps_lexicographic` and at eps = 0, and compare split counts -- if the
          tie-break ever bought a split the counts would differ;
          (c) the VERIFY section-2 counterexample rebuilt: 4-state path, M = 10, tau = 20,
          delta = 0, D = [[1,100],[100,1],[1,100],[100,1]], solved at the *plan's original*
          eps = 0.5 / V(y0) as well.
VERDICT   VERIFIED
BASIS     (a) 0/50 deviations at 1e-15 relative.  (b) 60/60 identical split counts; and the
          eps-solution is never less compact than the eps=0 one (0/60 worse by > 1e-6), so the
          term does rank ties rather than being inert.  (c) the module's eps returns 0 splits
          where the withdrawn calibration returns 2 -- the regression VERIFY refuted is closed,
          and `tests/test_state_splits.py::test_eps_never_buys_a_split` pins it.
ARTIFACT  docs/verify/codeverify_state_splits.py (m3)
CAVEATS   the "never buys a split" property is proved by the bound `eps * term <= 0.5` for any
          feasible y (checked in the test), and the 60 trials are corroboration at k = 2 only.
          Magnitude on the real instance (eps ~ 1e-11 in dollars-times-degrees^2) is untested;
          HiGHS' absolute tolerances could in principle swamp a tie-break that small on real
          data.  The mass rows are conditioned by tau, the objective is not.
```

### 4 — `balance_pass`

```
CLAIM     fix z; LP1 minimises max_j |mass_j - tau|, LP2 minimises the spread at t*; z unchanged,
          band kept, eta kept, spread never wider than the MILP's
ATTACK    an independent pair of *dense* LPs written from the plan's text (own variable layout,
          own u/l columns, method="highs" rather than the module's "highs-ds"), compared on 80
          random 6-state toys (path/cycle, k in {2,3}, delta in {2,5,10}%), plus a targeted
          400-trial search at the grid's widest delta = 10% with k in {2,3,4} aimed exactly at
          VERIFY section 3b's failure mode.  Also checked: y = 0 wherever z = 0, y >= eta
          wherever z = 1, rows sum to 1, band holds without band rows being carried.
VERDICT   VERIFIED
BASIS     80/80: max deviation equals the oracle LP1 optimum to < 1e-6; spread never exceeds the
          oracle LP2 optimum by > 1e-6; z untouched in all trials; band and eta hold in all
          trials.  Spread-vs-MILP: 0 widenings in 80 + 400 = 480 feasible trials (worst
          difference 0.0).  This is the plan's amendment working: VERIFY 3b's counterexample was
          against a *single* LP, and the second LP removes it.
ARTIFACT  docs/verify/codeverify_state_splits.py (m4, oracle_balance),
          docs/verify/codeverify_state_splits_edge.py (targeted delta = 10% search)
CAVEATS   "spread <= the MILP's spread" is empirical, not proved: LP2 is restricted to
          {maxdev <= t*}, which can exclude the MILP's own y, so a widening is not structurally
          impossible -- only unobserved in 480 trials at S = 6.  The invariant that *is*
          guaranteed is `max_dev(pass) <= max_dev(MILP) <= delta`.  `t_star` is inflated by
          (1+1e-9)+1e-12 before LP2; that slack is far below tier-1 CERT_TOL and cannot carry a
          district outside the band at any realistic tau, but it is a hard-coded fudge.
```

### 5 — `realise`

```
CLAIM     level 2: unsplit states whole; each split state cut by centers.assign to targets
          y_sj*M_s; up to 5 Lloyd rounds that never raise the state's sum M d^2; a rejected
          round leaves the labels alone; n_fractional <= (districts touching - 1) per state
ATTACK    25 random zip-level toys (6 states on a path, 3..7 zips each, random within-state
          jitter, k in {2,3}, delta in {5,10}%): solve -> balance_pass -> realise(rounds=5), then
          check every clause directly against the level-1 answer.  Rejection behaviour attacked
          separately on the FAR-centres fixture (centres deliberately placed for the old shares)
          by running realise at every round cap 0..6 and checking that once `rounds_used`
          saturates below the cap -- i.e. a round was refused or repeated -- more rounds change
          no label.  Degenerate: a state owning no zips, a state touching no district (must
          raise), an out-of-range state_idx (must raise).
VERDICT   VERIFIED
BASIS     25/25 on every clause: unsplit states land in exactly their single z district;
          realised district mass per split state is within one zip's mass of y_sj*M_s (the
          rounding bound the plan claims); n_fractional <= #{j : z_sj} - 1 in every case;
          cost_rounds non-increasing with len == rounds_used + 1; the state's mass is conserved
          to 1e-7.  Round caps 0..6 on the FAR fixture: rounds_used saturates at 1 from cap 2
          onward and labels are byte-identical for caps 2..6, so the refused round is a genuine
          no-op.  The acceptance test is `new_cost > cost + COST_TOL -> break` (:457), i.e.
          "accept only if the cost does not rise", exactly as the brief states.
ARTIFACT  docs/verify/codeverify_state_splits.py (m5),
          docs/verify/codeverify_state_splits_edge.py
CAVEATS   `cost` and `new_cost` are measured against *different* centre sets (the round moves
          the centres), so "cost_rounds is non-increasing" is a statement about a moving
          objective, not a fixed-centre Lloyd descent.  That is inherent to recentroiding from
          full membership and is what the plan asks for, but it means the sequence is not a
          descent of one function.
          `C` is mutated across split states inside `realise`: a later split state is cut
          against centres already moved by an earlier one.  Deterministic (state index order)
          and never wrong, but the plan does not say it, and the result depends on state order.
          Not covered: `centers.assign`'s own correctness (verified elsewhere), the
          `place_by_state` completion, and any real-instance geometry.
```

### 6a — size (REFUTED)

```
CLAIM     plan §Size: "882 binaries z, 882 binary r, 882 continuous y, 2 x 107 x 18 flow
          variables; 6,583 rows" at S = 49, k = 18, E = 107
ATTACK    build the real-shape problem twice with synthetic data (a planar 7x7 grid graph topped
          up to 107 edges with D from the embedding, and a random connected graph with 107
          edges) and read `n_var`, `integrality.sum()` and the `rows` block table off the object.
VERDICT   REFUTED (row count).  Variables VERIFIED.
BASIS     variables 6,498 = 882 z + 882 y + 882 r + 3,852 flow, of which 1,764 integral --
          matches the plan and VERIFY section 5 at S = 49.  Rows: **11,317**, not 6,583:

              place 49 | yz 882 | yz_lo 882 | band 18 | root 18 | rz 882
              flow_tail 3,852 | flow_head 3,852 | net 882

          The gap is 4,734 rows and is fully explained, exactly:
            + 882  `yz_lo` (`eta z <= y`).  The eta bullet was added to the plan as one of the
                   three corrections, but the §Size row table was not updated with it.
            + 3,852 capacity.  The plan/VERIFY count 2 rows per edge per district
                   (`f_uv + f_vu <= (N-1) z_u` and `... <= (N-1) z_v`); the code writes 4
                   (each directed arc against each endpoint), 4 x 107 x 18 = 7,704.
          6,583 + 882 + 3,852 = 11,317 exactly, so this is a stale plan number plus a
          formulation choice, not a construction bug -- correctness is row 1's business and
          passed there.  VERIFY section 5 already anticipated the arc-wise variant ("10,508 if
          ... the capacity is imposed per directed arc rather than per arc pair").
          Fix: either update the plan's §Size line to 11,317 (and note the arc-wise capacity),
          or tighten the code to the pair form -- the pair form is also the stronger relaxation,
          which row 6b suggests is worth having.
ARTIFACT  docs/verify/codeverify_state_splits.py (m6),
          docs/verify/codeverify_state_splits_scale.py
CAVEATS   the edge list is synthetic with |E| = 107; row counts depend only on S, k, |E|, so the
          count transfers, but the real rook adjacency was not rebuilt here (VERIFY C5 did that).
```

### 6b — runtime "Seconds" (REFUTED on synthetic real-shape instances)

```
CLAIM     plan §Size: "`scipy.optimize.milp` on HiGHS with `mip_rel_gap = 0.0` (trap 12).
          Seconds."
ATTACK    solve both real-shape instances above at k = 18, delta = 5%, mip_rel_gap = 0.0, with a
          300 s time limit.
VERDICT   REFUTED for these instances; INCONCLUSIVE for the channel's real instance.
BASIS     planar 7x7 (D from a planar embedding, the geometry closest to the channel):
          status 1, time limit reached at 300.0 s, incumbent 6 splits, **relative gap 0.109**.
          Random graph, random D: 300.0 s, incumbent 582 splits, gap 0.922.  Neither is
          "seconds"; the planar one is still 11% from a certificate after five minutes.  This is
          the weak-scf-relaxation risk VERIFY section 1b flagged ("expect the branch-and-bound
          work, not the row count, to decide the runtime"), and note `solve()` *raises* on a
          time limit, so a slow real instance is a hard failure, not a degraded answer.
ARTIFACT  docs/verify/codeverify_state_splits_scale.py 300
CAVEATS   synthetic masses/D, not the channel's.  Real D from 18 fixed committed centres over
          contiguous states is far more structured (a state's cheapest districts are its
          neighbours'), which typically collapses the tree, so this does not prove the real
          instance is slow.  It does mean "Seconds" is unevidenced and the CLI should pass a
          `time_limit` and be prepared to report a gap.  The k! symmetry the plan says the
          tie-break breaks "in practice" is the obvious suspect at k = 18.
```

## Gaps (model with no code, code with no model)

- **Warm start `y⁰`** (plan bullet "Warm start / sanity"): no counterpart anywhere in
  `state_splits.py`; `solve` passes no `x0` (HiGHS via `scipy.optimize.milp` has no warm-start
  hook), and nothing computes or checks `y⁰`'s split count as an upper bound. VERIFY §4 listed
  five quantities the CLI must print to settle "feasible at δ = 1.3%"; none exists yet.
- **CLI `tools/state_splits.py`** with `--incumbency-tiebreak` does not exist. `realise`'s
  `tiebreak=` is the hook it would use; `centers.assign` does have `penalty=`, so the
  `NotImplementedError` branch is currently dead on this checkout.
- **Cleanness reporting** (border-segment count from `us_maps`, split-zip count) is only half
  present: `realise` returns `districts` and `n_fractional` per split state; the border-segment
  count has no counterpart (CLI-level).
- **Code with no model text**: the τ-scaling of the mass rows (documented in the module
  docstring, absent from the plan — harmless, the feasible set is identical); `COST_TOL = 1e-12`;
  `solve`'s renormalisation of `y` rows after zeroing at `z = 0`; `time_limit=` on `solve`; the
  centre mutation across split states in `realise`.

## Environment notes

- `git` cannot be run from this session (a wrapper refuses any command with `git` among its
  operands in the worktree), so commit identity is not recorded here; nothing in the report
  depends on it.
- `pytest` is not installed in `.venv`; the entry point is `tests/run_all.py`.
- The `figures/` anchor set is not touched by this unit; no byte-identity anchor applies.
