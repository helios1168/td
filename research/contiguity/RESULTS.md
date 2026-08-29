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
