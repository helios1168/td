# Unit state_splits — Track 2, the state-level minimum-splits MILP

Status: open

Adversarial verification (`math-verify`, `docs/BORDERS_PLAN.md` lines 86-144) and code
verification (`code-verify`, 2026-09-06) of the state-level minimum-splits MILP: the
single-commodity-flow contiguity block, the objective's incumbency tie-break calibration, the
two-stage balance pass, and their implementation in `td/solvers/state_splits.py`
(`build_milp`, `solve`, `eps_lexicographic`, `balance_pass`, `realise`, `connected`). There is no
`MODEL_*.md`; `docs/BORDERS_PLAN.md` is the model.

## Model

none yet

## Verify

From `docs/VERIFY_state_splits.md` (2026-09-05 or earlier, `math-verify`). Target:
`docs/BORDERS_PLAN.md` lines 86-144.

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
