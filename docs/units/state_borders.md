# Unit state_borders — Track 1, the penalised banded transportation LP

Status: done

Code verification (`code-verify`, 2026-09-06, against branch `worktree-vbl`) of the penalised
banded transportation LP, state-owner-set logic and the label/owner/LP/recentroid refinement loop
(`docs/BORDERS_PLAN.md` lines 60-86, 200-228): `td/solvers/centers.py` (`assign`, `power_labels`,
`power_weights`, penalty and band keywords) and `td/solvers/state_borders.py` (`owner_sets`,
`penalty_matrix`, `refine`, `pure_snap`). There is no `MODEL_*.md`; the plan is the model.

## Model

none yet

## Verify

none yet

## Code verify

From `docs/CODEVERIFY_state_borders.md` (2026-09-06, `code-verify`). **8 VERIFIED (9 rows incl.
1b), 0 REFUTED, 0 INCONCLUSIVE.** Tests: `tests/run_all.py` → 305 passed, 0 failed. Type check:
0 errors in `td/solvers/state_borders.py`; 3 pre-existing errors elsewhere (unchanged from
`b38c9ce`) plus 3 cosmetic errors in new code.

| # | model object (plan) | code symbol | verdict |
|---|---|---|---|
| 1 | penalised banded LP `min Σ M_z(d²+P)x`, `Σ_j x=1`, `τ(1±δ)` band | `centers.py:149 assign(..., penalty=, band=)` | **VERIFIED** |
| 1b | "`penalty=None, band=0.0` must reproduce the current path bit-for-bit" | same, vs `b38c9ce:td/solvers/centers.py` | **VERIFIED** |
| 2 | λ "a multiple of the committed draw's mass-weighted mean d²", penalty inside the descaled objective | `centers.py:203-210`; `state_borders.py:127`; `tools/state_borders.py:69-71` | **VERIFIED** |
| 3 | owner sets: plurality home, homeless fallback, unknown state excluded | `state_borders.py:31 owner_sets`, `:60 penalty_matrix` | **VERIFIED** |
| 4 | alternation: labels→owners→LP→recentroid, ≤10 rounds, stop on repeat, no `improve`, every iterate saved | `state_borders.py:101 refine` | **VERIFIED** |
| 5 | grid column "mass share outside owner sets"; split-state exclusion "own owner set has ≥2 districts" | `tools/borders_report.py:186 _owner_metrics`, `:241 cell_row` | **VERIFIED** |
| 6 | real grid cell `d0.02_lam100`: band held, outside-owner share = 0.0309 | `battery/results/borders_k18_v2_20260907/d0.02_lam100/draw.csv` | **VERIFIED** |
| 7 | `power_labels(penalty=)` / `power_weights(penalty=)` | `centers.py:312`, `centers.py:336` | **VERIFIED** — no production caller exists for either keyword today |
| 8 | pure-snap baseline: every zip outside its state's owner set moves to the nearest owner district | `state_borders.py:75 pure_snap` | **VERIFIED** |

**Findings (none change a verdict).** F1: `refine` raises (rather than degrading gracefully) on
an all-unknown-state input; not reachable on the real instance. F2: the objective's owner sets
drift each round (as the plan asks) while the reported grid metric scores against the committed
map's owner sets (also correct, but a different reference) — at δ=10% the two readings diverge
2×; the report should say which it quotes. F3: `lam_abs` is computed twice (driver and `refine`),
agreeing today but with no shared source of truth. F4: `power_weights(penalty=)` was untested
before this verification. F5: the driver can silently overwrite one cell's output with another's
under specific flag combinations. F6: `params.json` does not record whether the figures in its
directory came from the same invocation.

**Artifacts**, moved out of the deleted flat verify-scripts directory to
`tools/verify/state_borders/`: `oracle_assign_lp.py` (rows 1, 1b, 2), `oracle_owner_sets.py`
(row 3), `oracle_refine.py` (row 4), `oracle_grid_cell.py` (rows 5, 6, 8), `oracle_lam_abs.py`
(row 2, real instance), `oracle_power_penalty.py` (row 7).

Full report: `git show 8b14eee:docs/CODEVERIFY_state_borders.md`.
