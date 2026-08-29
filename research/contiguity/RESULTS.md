# Contiguity harness — RESULTS

Written by the main session after each stage from `battery/results/contiguity/<run_id>/summary.csv`.

## S0 smoke — 2026-08-29 (`s0_2026-08-29`)

Curated T0 (13 pairs, n=8–20) + the six named failures; ρ=0; cap 60 s; 11 workers; 70 rows in ~1.5 min wall; 0 post-pass bugs; every row passes the validators; `battery/figures/` untouched.

| method | tier | rows | certified | rooted-optimal | gap_limit | feasible | median t→cert | mean cost of contiguity | EF1 | named failures |
|---|---|---|---|---|---|---|---|---|---|---|
| `brute` | T0 | 13 | 1.00 | 0.00 | 0.00 | 1.00 | 0.019 s | 0.0041 | 1.00 | 0/6 |
| `current` | T0 | 13 | 0.00 | 0.38 | 0.54 | 0.92 | — s | 0.0040 | 1.00 | 0/6 |
| `current` | T1 | 2 | 0.00 | 0.00 | 0.00 | 0.00 | — s | 0.0040 | 1.00 | 0/6 |
| `current` | T2 | 3 | 0.00 | 0.00 | 0.00 | 0.33 | — s | 0.0036 | 1.00 | 0/6 |
| `current` | T4 | 1 | 0.00 | 0.00 | 0.00 | 1.00 | — s | 0.0040 | 1.00 | 0/6 |
| `current_tight` | T0 | 13 | 0.00 | 0.92 | 0.00 | 0.92 | — s | 0.0041 | 1.00 | 0/6 |
| `current_tight` | T1 | 2 | 0.00 | 0.00 | 0.00 | 0.00 | — s | 0.0037 | 1.00 | 0/6 |
| `current_tight` | T2 | 3 | 0.00 | 0.00 | 0.00 | 0.33 | — s | 0.0035 | 1.00 | 0/6 |
| `current_tight` | T4 | 1 | 0.00 | 0.00 | 0.00 | 1.00 | — s | 0.0040 | 1.00 | 0/6 |
| `current_tu` | T0 | 13 | 0.00 | 0.92 | 0.08 | 1.00 | — s | 0.0041 | 1.00 | 0/6 |
| `current_tu` | T1 | 2 | 0.00 | 0.00 | 0.00 | 0.00 | — s | 0.0051 | 1.00 | 0/6 |
| `current_tu` | T2 | 3 | 0.00 | 0.00 | 0.00 | 0.33 | — s | 0.0036 | 1.00 | 0/6 |
| `current_tu` | T4 | 1 | 0.00 | 0.00 | 0.00 | 1.00 | — s | 0.0040 | 1.00 | 0/6 |

**Reading.**

- `brute` certifies all 13 T0 pairs (n=20 in ~2 s), so T0 ground truth is available for every method at no cost.
- `current_tight` (mip_rel_gap=0) reproduces the brute optimum on 12/13 T0 pairs as `optimal_rooted` (OPT−LB = 0; `opt_has_ratio_roots` is True on every T0 pair, so the root restriction did not bind there). Plain `current` stops at `gap_limit` on 7/13 (trap 12).
- The legacy loop can never produce a 1e-8 certificate: its termination test is a log-slack of 1e-6 per side, so a fully converged run reports gap ≈ 1e-6 nats (`current_tu` on T0_n40_s9, n=20: 1.18e-6 after 34 rounds). Acceptance (≤ 1e-8) is for the new methods; `current*` is the control.
- With `max_iter=30` (the battery's setting) every named failure stops in 1–20 s, far below the cap; `current_tu` (tight + unbounded) is the honest time-capped control: **0/6 certified at 60 s** — C9-seed2 A2/B2 (31), C1-seed2 A0/B0 (69), C7 A0/B0 (125), C7 A3/B3 (205) hit the cap on an infeasible iterate; C5-resp A2/B2 (61) and C7 A1/B1 (44) are downgraded to `heuristic` by the trap-13 guard (LB > the loop's own UB on a disconnected pair graph).
- Cost of contiguity on T0 is ~0.4 % of the free product; EF1 holds on every incumbent (both directions).

Named-failure rows (`current_tu`, cap 60 s):

| instance | n | status_eff | LB | UB | excess pieces | rounds | t |
|---|---|---|---|---|---|---|---|
| C9_heavytail_seed2__A2_B2 | 31 | time_limit | — | 6.50156 | 1 | 219 | 60 s |
| C7_scale_n400__A1_B1 | 44 | heuristic | 6.45654 | — | 0 | 107 | 40 s |
| C5_states_resp__A2_B2 | 61 | heuristic | 6.44244 | — | 0 | 146 | 60 s |
| C1_aligned_seed2__A0_B0 | 69 | time_limit | — | 6.45514 | 1 | 137 | 60 s |
| C7_scale_n400__A0_B0 | 125 | time_limit | — | 6.45531 | 1 | 157 | 60 s |
| C7_scale_n400__A3_B3 | 205 | time_limit | — | 6.47108 | 3 | 48 | 60 s |

Implications for the method wave: (i) every root-based formulation needs one root per pair component (CLAUDE.md trap 13) — three of the six named failures are disconnected pair graphs; (ii) certificates must come from the engine's dual bound, not a cut-loop termination test; (iii) T0 acceptance = exact match with `brute`.

## S0 full — 2026-08-29 (`s0c_2026-08-29`): every method family

Same instance set (curated T0 + six named failures), ρ=0, cap 60 s, 11 workers; 165 rows, 0 post-pass bugs, 0 invalid rows. All methods use root-free, component-wise connectivity (CLAUDE.md trap 13).

| method | T0 certified | T0 median t→cert | feasible (all rows) | cost of contiguity (T0) | EF1 (T0) | named failures | errors |
|---|---|---|---|---|---|---|---|
| `scip_tree` | 1.00 | 0.029 s | 1.00 | 0.0041 | 1.00 | 0/6 | 0 |
| `loop_v2` | 1.00 | 0.116 s | 0.95 | 0.0041 | 1.00 | 0/6 | 0 |
| `flow` | 1.00 | 0.250 s | 1.00 | 0.0041 | 1.00 | 0/6 | 0 |
| `flow_pwl` | 1.00 | 0.236 s | 1.00 | 0.0041 | 1.00 | 0/6 | 0 |
| `prep_e1_flow` | 1.00 | 0.245 s | 1.00 | 0.0041 | 1.00 | 0/6 | 0 |
| `brute` | 1.00 | 0.017 s | 1.00 | 0.0041 | 1.00 | 0/6 | 0 |
| `cbc_tree` | 0.46 | 0.287 s | 0.84 | 0.0076 | 0.85 | 0/6 | 0 |
| `warm_f1` | 0.00 | — s | 1.00 | 0.0079 | 1.00 | 0/6 | 0 |
| `current_tu` | 0.00 | — s | 0.79 | 0.0041 | 1.00 | 0/6 | 0 |

Named failures — status / gap (nats) / wall time at the 60 s cap:

| instance | n | `scip_tree` | `loop_v2` | `flow` | `flow_pwl` | `cbc_tree` | `current_tu` |
|---|---|---|---|---|---|---|---|
| C9_heavytail_seed2__A2_B2 | 31 | optimal / 0e+00 / 0 s | optimal / 0e+00 / 0 s | optimal / 0e+00 / 1 s | optimal / 2e-07 / 2 s | time_limit / — / 1 s | time_limit / — / 60 s |
| C7_scale_n400__A1_B1 | 44 | optimal / 0e+00 / 1 s | optimal / 4e-14 / 17 s | optimal / 8e-15 / 16 s | optimal / 4e-07 / 6 s | time_limit / — / 42 s | heuristic / — / 46 s |
| C5_states_resp__A2_B2 | 61 | optimal / 9e-16 / 0 s | optimal / 0e+00 / 1 s | optimal / 1e-14 / 1 s | optimal / 6e-07 / 0 s | time_limit / — / 2 s | heuristic / — / 60 s |
| C1_aligned_seed2__A0_B0 | 69 | optimal / 0e+00 / 2 s | optimal / 0e+00 / 45 s | optimal / 2e-13 / 53 s | optimal / 2e-07 / 60 s | time_limit / — / 61 s | time_limit / — / 60 s |
| C7_scale_n400__A0_B0 | 125 | optimal / 0e+00 / 1 s | optimal / 0e+00 / 2 s | optimal / 2e-15 / 4 s | optimal / 4e-07 / 3 s | time_limit / — / 9 s | time_limit / — / 60 s |
| C7_scale_n400__A3_B3 | 205 | time_limit / 3e-03 / 3 s | time_limit / — / 60 s | time_limit / — / 60 s | time_limit / — / 60 s | time_limit / — / 37 s | time_limit / — / 60 s |

**Reading.**

- The three mechanisms of Trap 11 are now separated by evidence. **(a) disconnection** and **(c) value concentration** are gone: C1-seed2 A0/B0 (two components), C5-resp A2/B2 (five components), C7 A1/B1 (two), C9-seed2 A2/B2 (heavy tail) all certify under every root-free formulation — the fix was the formulation (per-component / root-free connectivity), not the engine. **(b) pure scale** survives only at C7 A3/B3 (205 zips): `scip_tree` holds a 3e-3 gap with a feasible incumbent from 0.03 s; flow's LP is the wall (its first master never finishes); `loop_v2` and `flow_pwl` time out. Interpretation for the 400–800-zip production band: single-tree branch-and-cut with a primal repair heuristic is the route, and the primal side is what still needs work.
- `scip_tree` is the fastest certifier by 5–50× on every named failure it solves (native `log`, `feastol=1e-9`, dual reductions off).
- `flow_pwl` (one MILP, chord under-estimator, ε≈2e-7–6e-7 at k≈690) matches `flow` on certification and is usually faster; the chord formulation removes the SOS2 risk in OPTIONS.md §4 entirely.
- `cbc_tree`: python-mip 2.0's lazy-constraint callback does not reliably enforce a just-added row on this platform; the method is restart-based and never wrong but rarely conclusive (6/13 T0). Cross-check only.
- `warm_f1` is feasible on 100 % of rows in ≤ 0.1 s and is the natural MIP start for SCIP (`addSol` with the full vector).
- `prep_e1_flow`: no zero-value zips exist on T0/T1, so E1 is a documented no-op here; it needs the glue regime (T3 / `S10_glue`).
- EF1 holds on every certified T0 incumbent; cost of contiguity on T0 stays ≈ 0.4 % of the free product.

Open items carried into S1: `scip_tree`'s retry ladder stops early under harness load on C7 A3/B3 (3 s of a 60 s budget — the remaining time should go to the OA rung); `flow` returns no dual bound at all on the 205 pair (a root-LP bound would fix that); `loop_v2` had one infeasible last iterate on a named failure (feasible 0.95).
