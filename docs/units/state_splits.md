# Unit state_splits — Track 2, the state-level minimum-splits MILP

Status: open

Adversarial verification (`math-verify`, model folded into `## Model` below; full text
`git show ae2b18d:docs/BORDERS_PLAN.md` lines 86-144) and code
verification (`code-verify`, 2026-09-06) of the state-level minimum-splits MILP: the
single-commodity-flow contiguity block, the objective's incumbency tie-break calibration, the
two-stage balance pass, and their implementation in `td/solvers/state_splits.py`
(`build_milp`, `solve`, `eps_lexicographic`, `balance_pass`, `realise`, `connected`). There is no
`MODEL_*.md`; the model is `## Model` below.

## Model

The state-level minimum-splits MILP, over `s` = the 49 lower-48-plus-DC states (AK, HI and the
32 `??` zips, 0.09τ together, excluded and placed afterwards by `channel.place_by_state`);
`M_s` the state's mass, `c_j` the committed draw's 18 fixed centres, `D_sj` the exact moment of
state `s` about centre `j`. Folded from `docs/BORDERS_PLAN.md` (deleted 2026-09-07; full text
`git show ae2b18d:docs/BORDERS_PLAN.md`).

```
min   Σ_s (Σ_j z_sj − 1)  +  ε Σ_s Σ_j M_s D_sj y_sj        (split count; compactness tie-break)
s.t.  Σ_j y_sj = 1                       ∀ s                (all of s placed)
      0 ≤ y_sj ≤ z_sj,  z_sj ∈ {0,1}     ∀ s, j             (z marks contact)
      τ(1−δ) ≤ Σ_s M_s y_sj ≤ τ(1+δ)     ∀ j                (the band)
      {s : z_sj = 1} connected in the state rook graph  ∀ j (contiguity)
```

- **ε (corrected)**: `ε = 0.5 / Σ_s M_s · max_j D_sj` — must hold over every feasible `y`, not
  only at the committed map's own `y⁰` (the first draft scaled by `y⁰`; Verify #2 found a
  four-state counterexample where it buys 2 splits against a true optimum of 0).
- **Contact means mass.** `y_sj ≥ η · z_sj`, `η = 0.01` (Verify #1b: without it a bridge state
  can buy a split while its district is disconnected in fact).
- **Contiguity** by single-commodity flow, no lazy callbacks: a variable root `r_sj ≤ z_sj`,
  `Σ_s r_sj = 1` per district, flow on each rook edge bounded by `(N−1)·z_uj` / `(N−1)·z_vj`,
  net inflow at `s` at least `z_sj − N·r_sj` (N = 50).
- **Balance pass, lexicographic (corrected).** After the MILP, fix `z` and re-solve for `y` in
  two LPs: minimise the maximum deviation, then, holding that at its optimum, minimise the
  spread (Verify #3b: a single LP can return a wider spread at equal max deviation).
- **Level 2.** Per split state, `centers.assign` over that state's zips at targets `y_sj M_s`
  (convex power cells); five Lloyd rounds recentroiding every district touching the state.
  Unsplit states go whole to their district.
- **Does not close in general.** `mip_rel_gap = 0.0`, 600s per δ; the anchored form (each
  district keeps its committed home state) closed at δ = 5% (168s) and δ = 10% (386s); the free
  form and the tighter δ never closed in 600s. Reported splits below δ ≈ 3% are time-limited
  incumbents, not certificates.
- **The committed map is not a feasible warm start.** Its state composition passes the band at
  δ = 1.3% but fails contiguity at the state level (D09 holds crumbs in ND/NY/TN that no path
  of its own states reaches; D18's CA piece is cut off from ID/MT); 28 state-district contacts
  sit under η. No upper bound on the split count exists from `y⁰`.

Grid results (Track 2, free and anchored, all δ) are in the Serena memory
`facts/state-border-snapping`, dated 2026-09-07.

## Verify

From `docs/VERIFY_state_splits.md` (2026-09-05 or earlier, `math-verify`). Target:
`git show ae2b18d:docs/BORDERS_PLAN.md` lines 86-144 (folded into `## Model` above).

| # | claim | verdict |
|---|---|---|
| 1 | the scf block admits a district's z-set iff it is connected and non-empty | **VERIFIED** (needs `r` integral) |
| 1b | contiguity of the *realised* district (`y_sj > 0`) | **REFUTED** — a paid bridge state buys a disconnected district; contiguity binds the z-set, not the set of states actually holding mass. Fix: drop a state from the split report when `y_sj = 0`, or add `z_sj ≤ y_sj / y_min` |
| 2 | `ε = 0.5 / Σ M_s D_sj y⁰_sj` keeps the tie-break under half a split for every feasible `y` | **REFUTED** — and it buys splits: a 4-state counterexample has the tie-break purchase 2 splits against a true optimum of 0. The constant must not depend on `y⁰`; correct calibration is `eps = 0.5 / Σ_s M_s max_j D_sj` |
| 3a | the balance pass keeps every band constraint | **VERIFIED** |
| 3b | the balance pass never widens the spread | **REFUTED** at δ = 10% — the pass minimises max deviation, not spread, and `maxdev ≤ spread ≤ 2·maxdev` only pins it within a factor 2; a tail counterexample at the grid's widest δ widens spread 18%. Fix: state the invariant as max deviation, or make the pass lexicographic |
| 4 | `y⁰` is feasible at δ = 1.3% | **INCONCLUSIVE** (confidential data; the CLI must print five specific quantities to settle it, listed in the full report) |
| 5 | 900 + 900 + 900 + 2·107·18 variables | **VERIFIED** given S = 50, E = 107; **6,638 rows**; the prose's own node count is 49 states + DC, not 50 — pin the node list before the build |

Full report: `git show 8b14eee:docs/VERIFY_state_splits.md`.

## Code verify

From `docs/CODEVERIFY_state_splits.md` (2026-09-06, `code-verify`, against
`td/solvers/state_splits.py` and `tests/test_state_splits.py`, on the corrected plan). **4
VERIFIED, 2 REFUTED (both in the "Size" bullet; neither is a soundness error), 0 INCONCLUSIVE**
among the six mapping rows. Type check: 4 pre-existing-class errors only (scipy-stub artifacts).
Tests: `tests/run_all.py` → 305 passed, 0 failed.

| # | mapping | verdict |
|---|---|---|
| 1 | `build_milp` rows ↔ the plan's formulation (objective, place, `η z ≤ y ≤ z`, band, scf) | **VERIFIED** |
| 2 | `connected` ↔ connectivity in the rook graph | **VERIFIED** |
| 3 | `eps_lexicographic` ↔ `0.5 / Σ_s M_s max_j D_sj`, and never buys a split | **VERIFIED** — the withdrawn calibration's regression is closed and pinned by `test_eps_never_buys_a_split` |
| 4 | `balance_pass` ↔ the two lexicographic LPs | **VERIFIED** — the second LP closes VERIFY 3b's counterexample |
| 5 | `realise` ↔ level 2 (whole states, targets, Lloyd rounds, `n_fractional`) | **VERIFIED** |
| 6a | size: plan's "882 z / 882 r / 882 y / 6,583 rows" at S=49, k=18, E=107 | **REFUTED** (row count) — variables VERIFIED (6,498, 1,764 integral); actual rows are **11,317**, not 6,583. The gap is exactly explained: +882 for the `η z ≤ y` block (added to the plan as a correction but never reflected in the size line) and +3,852 because the code imposes capacity per directed arc (4 per edge per district) rather than per arc pair (2) as the plan/VERIFY table assumed — a stale number plus a formulation choice, not a construction bug |
| 6b | runtime: plan's "`scipy.optimize.milp` on HiGHS … Seconds" | **REFUTED on synthetic real-shape instances** — a planar 7×7-grid-shaped instance at k=18 does not close in 300s (10.9% gap); **INCONCLUSIVE for the channel's real instance** (real `D` from 18 fixed committed centres over contiguous states is far more structured and may collapse the tree, but this is unproven) |

**Gaps (model with no code, or code with no model), not yet closed:** the warm start `y⁰` has no
counterpart in `state_splits.py` (`solve` passes no `x0`; nothing computes or checks `y⁰`'s split
count as an upper bound); the CLI `tools/state_splits.py --incumbency-tiebreak` does not exist
(`realise`'s `tiebreak=` is the hook it would use); the border-segment count for cleanness
reporting has no counterpart at the CLI level.

**Known bug, not yet fixed (2026-09-07):** `realise` is order-dependent — it moves the shared
centre array as it cuts split states in turn, deterministic but unjudged; see the `TODO` at
`td/solvers/state_splits.py::realise`.

**Artifacts**, moved out of the deleted flat verify-scripts directory to
`tools/verify/state_splits/`: `state_splits_checks.py`, `state_splits_c3_band.py` (the
`math-verify` artifacts); `codeverify_state_splits.py`, `codeverify_state_splits_edge.py`,
`codeverify_state_splits_scale.py` (the `code-verify` artifacts).

Full report: `git show 8b14eee:docs/CODEVERIFY_state_splits.md`.
