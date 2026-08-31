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

## S1 screening — 2026-08-30 (`s1_2026-08-30`)

T0 (13 curated) + T1 (63 battery pairs, 30–82 zips) + T2 (12 scale pairs, 26–464 zips) = 88 instances; ρ=0 (+ ρ=2e-3 for `current_tu`); cap 60 s; 11 workers; 822 rows; ~50 min wall. 0 post-pass bugs **after** the `cbc_tree` correction below; 0 invalid rows.

| method | tier | rows | certified | gap_limit | feasible | median t→cert | worst gap vs UB* | named failures | errors |
|---|---|---|---|---|---|---|---|---|---|
| `brute` | T0 | 13 | 1.00 | 0.00 | 1.00 | 0.019 s | 0.0000 | 0/6 | 0 |
| `brute` | T1 | 18 | 1.00 | 0.00 | 1.00 | 0.012 s | 0.0000 | 0/6 | 0 |
| `cbc_tree` | T0 | 13 | 0.00 | 0.00 | 1.00 | — s | 0.0188 | 0/6 | 0 |
| `cbc_tree` | T1 | 62 | 0.00 | 0.00 | 0.68 | — s | 0.0272 | 0/6 | 0 |
| `cbc_tree` | T2 | 12 | 0.00 | 0.00 | 0.17 | — s | 0.0241 | 0/6 | 0 |
| `current_tu` | T0 | 13 | 0.00 | 0.08 | 1.00 | — s | 0.0000 | 0/6 | 0 |
| `current_tu` | T1 | 63 | 0.00 | 0.19 | 0.73 | — s | 0.0368 | 0/6 | 5 |
| `current_tu` | T2 | 12 | 0.00 | 0.08 | 0.25 | — s | 0.0000 | 0/6 | 0 |
| `current_tu` (ρ=0.002) | T0 | 13 | 0.00 | 0.00 | 1.00 | — s | 0.0000 | 0/6 | 0 |
| `current_tu` (ρ=0.002) | T1 | 63 | 0.00 | 0.00 | 0.98 | — s | 0.0000 | 0/6 | 0 |
| `current_tu` (ρ=0.002) | T2 | 12 | 0.00 | 0.00 | 0.92 | — s | 0.9814 | 0/6 | 0 |
| `flow` | T0 | 13 | 1.00 | 0.00 | 1.00 | 0.282 s | 0.0000 | 0/6 | 0 |
| `flow` | T1 | 63 | 0.73 | 0.00 | 1.00 | 0.699 s | 0.0053 | 2/6 | 0 |
| `flow` | T2 | 12 | 0.33 | 0.00 | 1.00 | 4.861 s | 0.0256 | 2/6 | 0 |
| `flow_pwl` | T0 | 13 | 1.00 | 0.00 | 1.00 | 0.181 s | 0.0000 | 0/6 | 0 |
| `flow_pwl` | T1 | 63 | 0.78 | 0.00 | 1.00 | 0.623 s | 0.0069 | 2/6 | 0 |
| `flow_pwl` | T2 | 12 | 0.42 | 0.00 | 1.00 | 2.626 s | 0.0256 | 2/6 | 0 |
| `loop_v2` | T0 | 13 | 1.00 | 0.00 | 1.00 | 0.200 s | 0.0000 | 0/6 | 0 |
| `loop_v2` | T1 | 63 | 0.78 | 0.00 | 0.78 | 0.687 s | 0.0000 | 2/6 | 1 |
| `loop_v2` | T2 | 12 | 0.42 | 0.00 | 0.42 | 5.136 s | 0.0000 | 2/6 | 0 |
| `prep_e1_flow` | T0 | 13 | 1.00 | 0.00 | 1.00 | 0.242 s | 0.0000 | 0/6 | 0 |
| `prep_e1_flow` | T1 | 63 | 0.73 | 0.00 | 1.00 | 0.708 s | 0.0053 | 2/6 | 0 |
| `prep_e1_flow` | T2 | 12 | 0.33 | 0.00 | 1.00 | 4.355 s | 0.0256 | 2/6 | 0 |
| `scip_tree` | T0 | 13 | 1.00 | 0.00 | 1.00 | 0.025 s | 0.0000 | 0/6 | 0 |
| `scip_tree` | T1 | 63 | 0.92 | 0.00 | 1.00 | 0.081 s | 0.0049 | 2/6 | 0 |
| `scip_tree` | T2 | 12 | 0.42 | 0.00 | 1.00 | 0.608 s | 0.0110 | 2/6 | 0 |
| `warm_f1` | T0 | 13 | 0.00 | 0.00 | 1.00 | — s | 0.0115 | 0/6 | 0 |
| `warm_f1` | T1 | 63 | 0.00 | 0.00 | 1.00 | — s | 0.0248 | 0/6 | 0 |
| `warm_f1` | T2 | 12 | 0.00 | 0.00 | 1.00 | — s | 0.0106 | 0/6 | 0 |

Named failures (ρ=0) — status / gap / t:

| instance | n | `scip_tree` | `loop_v2` | `flow` | `flow_pwl` | `cbc_tree` | `current_tu` |
|---|---|---|---|---|---|---|---|
| C9_heavytail_seed2__A2_B2 | 31 | optimal / 0e+00 / 0 s | optimal / 0e+00 / 0 s | optimal / 0e+00 / 1 s | optimal / 2e-07 / 2 s | heuristic / — / 1 s | time_limit / — / 60 s |
| C7_scale_n400__A1_B1 | 44 | optimal / 0e+00 / 1 s | optimal / 4e-14 / 16 s | optimal / 8e-15 / 15 s | optimal / 4e-07 / 7 s | heuristic / — / 61 s | heuristic / — / 52 s |
| C1_aligned_seed2__A0_B0 | 69 | optimal / 0e+00 / 2 s | optimal / 0e+00 / 38 s | optimal / 2e-13 / 50 s | optimal / 2e-07 / 53 s | heuristic / — / 61 s | time_limit / — / 60 s |
| C7_scale_n400__A0_B0 | 125 | optimal / 0e+00 / 1 s | optimal / 0e+00 / 1 s | optimal / 2e-15 / 4 s | optimal / 4e-07 / 3 s | heuristic / — / 10 s | time_limit / — / 60 s |
| C7_scale_n400__A3_B3 | 205 | time_limit / 3e-03 / 3 s | time_limit / — / 60 s | time_limit / — / 60 s | time_limit / — / 60 s | heuristic / — / 35 s | time_limit / — / 60 s |

Certified share by pair size (ρ=0):

| method | 0–20 | 21–45 | 46–82 | 83–125 | 126–205 | 206–464 |
|---|---|---|---|---|---|---|
| `scip_tree` | 31/31 | 20/20 | 23/28 | 2/3 | 0/4 | 0/2 |
| `loop_v2` | 31/31 | 20/20 | 14/28 | 2/3 | 0/4 | 0/2 |
| `flow` | 31/31 | 20/20 | 10/28 | 2/3 | 0/4 | 0/2 |
| `flow_pwl` | 31/31 | 20/20 | 14/28 | 2/3 | 0/4 | 0/2 |

**Reading.**

- `scip_tree` leads on every tier: 92 % of T1 certified (median 0.08 s), 42 % of T2; the uncertified T2 pairs are the 205/320/464-zip ones (mechanism (b)). `flow_pwl` ≈ `loop_v2` (78 % T1) > `flow` (73 %); all four agree exactly wherever they certify (0 bugs).
- **`cbc_tree` was corrected post hoc.** It claimed `optimal` with a global UB *below* `brute`'s optimum on `C2_entangled_a0` A0/B2 and A0/B3 (python-mip's lazy rows are not enforced reliably — W7's finding), and two of its jobs hung past the cap ignoring `max_seconds` and the SIGALRM backstop (killed; one rerun under `--scheduler proc`, one left missing). All 87 `cbc_tree` rows were demoted to `heuristic`/`UB=None` (`rows.jsonl.orig` keeps the originals) and the method is now `EXACT=False` in code (`664857c`). Option B is out.
- `current_tu` (legacy loop, tight+unbounded) certifies nothing at ρ=0 and hits trap 14 ('Solve error') on 5 T1 pairs; at ρ=2e-3 it is feasible on 92–100 % but still only `optimal_rooted` (the paper's ρ-penalised numbers are reproducible, not certified).
- `loop_v2`: feasible on only 78 % of T1 rows (time-limited runs end on an infeasible master iterate, `LB=None`) and one `error`; 0 row(s) with a poor feasible incumbent (gap vs UB* > 1 nat). Its certificates are sound; the primal side is weak without a warm start.
- `warm_f1` feasible on 100 % in ≤ 0.2 s; worst gap vs UB* 0.025 nats — the natural MIP start for SCIP.
- `prep_e1_flow` ≡ `flow` on every row: no zero-value zips in T0–T2 (E1 needs the glue regime, T3).
- Cost of contiguity stays ≈ 0.4 % on T0/T1; EF1 holds on every certified incumbent.

**Recommendation for S2/S3 finalists:** `scip_tree` (primary, with `warm_f1` as MIP start), `flow_pwl` (dependency-free oracle/cross-check up to ~125 zips), `loop_v2` (control for the paper's multi-tree argument). Drop `flow`, `cbc_tree`, `prep_*` (until T3), `current_*` except `current_tu` at ρ=2e-3 as the continuity column.

## S2 finalists — 2026-08-30 (`s2_2026-08-30`)

T1 + T2 (75 instances), ρ=0, **cap 1200 s**, 11 workers, hard-kill scheduler; methods `scip_tree`, `flow_pwl`, `loop_v2`, `current_tu` (control); 300 rows, 0 post-pass bugs, 0 invalid; ~5 h wall.

| method | tier | rows | certified | feasible | median t→cert | worst gap vs UB* | named failures | errors |
|---|---|---|---|---|---|---|---|---|
| `current_tu` | T1 | 63 | 0.00 | 0.81 | — s | 0.0368 | 0/6 | 5 |
| `current_tu` | T2 | 12 | 0.00 | 0.33 | — s | 0.0000 | 0/6 | 1 |
| `flow_pwl` | T1 | 63 | 0.97 | 1.00 | 1.150 s | 0.0016 | 2/6 | 0 |
| `flow_pwl` | T2 | 12 | 0.42 | 1.00 | 3.297 s | 0.0192 | 2/6 | 0 |
| `loop_v2` | T1 | 63 | 0.90 | 0.90 | 0.918 s | 0.0000 | 2/6 | 0 |
| `loop_v2` | T2 | 12 | 0.42 | 0.42 | 6.801 s | 0.0000 | 2/6 | 0 |
| `scip_tree` | T1 | 63 | 0.92 | 1.00 | 0.079 s | 0.0048 | 2/6 | 0 |
| `scip_tree` | T2 | 12 | 0.42 | 1.00 | 0.679 s | 0.0110 | 2/6 | 0 |

T2 (scale) pairs — status / gap / t at the 1200 s cap:

| instance | n | `scip_tree` | `flow_pwl` | `loop_v2` | `current_tu` |
|---|---|---|---|---|---|
| C7_scale_n400__A2_B2 | 26 | optimal / 2e-09 / 0 s | optimal / 6e-08 / 1 s | optimal / 0e+00 / 1 s | optimal_rooted / 0e+00 / 1 s |
| C7_scale_n400__A1_B1 | 44 | optimal / 0e+00 / 1 s | optimal / 4e-07 / 7 s | optimal / 4e-14 / 19 s | heuristic / — / 63 s |
| C7b_scale_n800_seed2__A2_B2 | 77 | optimal / 0e+00 / 1 s | optimal / 5e-07 / 16 s | optimal / 0e+00 / 28 s | gap_limit / 7e-07 / 215 s |
| C7b_scale_n800_seed1__A3_B3 | 114 | optimal / 1e-14 / 0 s | optimal / 3e-07 / 1 s | optimal / 0e+00 / 7 s | gap_limit / 1e-06 / 2 s |
| C7b_scale_n800_seed2__A1_B1 | 124 | time_limit / 4e-03 / 2 s | time_limit / 1e-03 / 1201 s | time_limit / — / 1200 s | time_limit / — / 1200 s |
| C7_scale_n400__A0_B0 | 125 | optimal / 0e+00 / 1 s | optimal / 4e-07 / 3 s | optimal / 0e+00 / 1 s | time_limit / — / 1200 s |
| C7b_scale_n800_seed2__A3_B3 | 135 | time_limit / 9e-04 / 5 s | time_limit / 1e-04 / 1200 s | time_limit / — / 1200 s | time_limit / — / 1200 s |
| C7b_scale_n800_seed1__A0_B0 | 169 | time_limit / 5e-03 / 36 s | time_limit / — / 1200 s | time_limit / — / 1200 s | error / — / 781 s |
| C7b_scale_n800_seed1__A2_B2 | 197 | time_limit / 6e-03 / 58 s | time_limit / — / 1200 s | time_limit / — / 1200 s | time_limit / — / 659 s |
| C7_scale_n400__A3_B3 | 205 | time_limit / 3e-03 / 3 s | time_limit / 6e-03 / 1200 s | time_limit / — / 1200 s | time_limit / — / 620 s |
| C7b_scale_n800_seed1__A1_B1 | 320 | time_limit / 1e-03 / 1 s | time_limit / 2e-04 / 1200 s | time_limit / — / 1200 s | time_limit / — / 352 s |
| C7b_scale_n800_seed2__A0_B0 | 464 | time_limit / 1e-02 / 4 s | time_limit / — / 1200 s | time_limit / — / 1200 s | time_limit / — / 1200 s |

Certified by pair size:

| method | 0–45 | 46–82 | 83–125 | 126–205 | 206–464 |
|---|---|---|---|---|---|
| `scip_tree` | 38/38 | 23/28 | 2/3 | 0/4 | 0/2 |
| `flow_pwl` | 38/38 | 26/28 | 2/3 | 0/4 | 0/2 |
| `loop_v2` | 38/38 | 22/28 | 2/3 | 0/4 | 0/2 |

**Reading.**

- **The 20× larger budget changed nothing above ~125 zips.** Every exact method certifies 38/38 pairs ≤ 45 zips and 2/3 at 83–125, and 0/6 at 126–464 — identical to S1's 60 s picture. Mechanism (b) is not a budget problem.
- `scip_tree` never uses the budget on the large pairs: it stops after 1–58 s with a valid 1e-3–1e-2 gap because its native-log retry ladder exhausts on LP numerical aborts (W6's open item) and the OA rung is not given the remaining time. Fixing that, plus `warm_f1` as `addSol` and fractional separation at the root, is the concrete next engineering step — the dual bound is already tight (gap 1e-3 at 320 zips after 1 s).
- `flow_pwl` does spend the 1200 s and gets to 1e-4–2e-4 nats on the 135- and 320-zip pairs without closing: the flow LP is the wall (Validi et al.'s crossover, measured here at ~125 zips). It is the best *bound* producer among the three at scale and certifies 97 % of T1 given time.
- `loop_v2` (multi-tree) ends the large pairs on infeasible master iterates (no incumbent) — the paper's argument that the multi-tree loop is the wrong architecture at scale stands, with numbers.
- `current_tu` (legacy control): 0 certified, 5 trap-14 errors on T1, 1 on T2; feasible on 81 % / 33 %.
- Cost of contiguity and EF1 unchanged from S1 (≈ 0.4 %, EF1 on every certified incumbent).

**Where this leaves the programme.** The formulation questions are settled (root-free component-wise cuts; native log or chord PWL; SCIP as engine). The remaining gap to the 400–800-zip production band is primal-side engineering in `scip_tree` (W6 follow-up), plus the reduction layer (E1) once real glue zips exist (T3). S3 (T3a at 3600 s) should wait for that follow-up and the twin; running it now would reproduce this table at higher cost.

## W6b — `scip_tree` ladder / primal follow-up — 2026-08-30 (`w6b_2026-08-30`, `w6b_s0`)

**Scope.** `battery/code/contig_methods/scip_tree.py` only (merged `930ae55`; 228 fast tests). Seven T2 pairs ≥ 124 zips + two certified controls, ρ=0, cap 1200 s, 4 workers, proc scheduler; S0 preset rerun as the non-regression gate. 0 post-pass bugs, all rows valid, `excess_pieces = 0`, EF1 on every incumbent.

**Root cause of the S2 picture.** A SCIP LP abort (`Exception: SCIP: error in LP solver!`, `getStatus() == "unknown"`) was rewritten to `time_limit` by `_finish` *before* `solve()` looked at it, and `solve()` continued the ladder only on status `error`. So the 1e-7 / 1e-6 / OA rungs never ran once: every S2 straggler stopped after its first rung, 1–58 s into a 1200 s budget, and five T1 pairs (C1-seed2 A3/B3, C4_contested ×3, C9-seed2 A3/B3) were hit the same way. The verdict now travels in `extra["retryable"]`, independent of the status the harness sees; every rung is logged in `extra["attempts"]` (feastol, formulation, SCIP status, wall, LB, UB, nodes, separated cuts).

**What else changed.** (i) `_short_stop`: SCIP's `limits/time` runs on SCIP's own clock and under harness load fired after 57 s of a 106 s rung — a `timelimit` below 75 % of the wall the rung actually had is retried like an abort. (ii) `tighten_back`: a merged gap in (1e-8, 1e-5] is the loosened rung's tolerance floor, not a search result, so the ladder tries only the originally-requested tolerance (native, then OA) and stops — without it the 124-zip pair burned 1027 s in an OA rung whose bound came back worse. (iii) `mip_start="f1"` (default): W5's F1 spanning-tree bisection for ≤ 5 % of the budget (cap 30 s) handed to `addSol`; it is the incumbent on all nine rows and, via `_gain_floor`, what keeps the native log's LPs stable from t = 0. (iv) Fractional separation at the root (`conssepalp`/`conssepasol`, threshold 0.5 on the LP support, ≤ 30 rounds × 40 cuts) — works with a `Conshdlr` that also enforces integer points in PySCIPOpt 6.2.1; validity unchanged (any u,v-separator is a valid root-free cut; `check_opt` audits every fractional cut against brute on T0). Effect small and mixed: helps 124/320/464 (OA bound at 464: 6.4789 with, 6.5468 without), neutral-to-slightly-worse on 169/205. (v) LP numerics sweep at 120 s on five pairs: `lp/scaling=2`, `lp/checkstability=False`, `lp/refactorinterval=10`, `tightenlpfeastol=False` all inside run-to-run spread (rejected); `lp/fastmip=0`, `lpfeastolfactor=1000` no-ops. Primal simplex (`scip_tree_psimplex` variant) keeps the 1e-6 native rung alive to the cap on the 464-zip pair (1.70e-3 vs 3.3–3.6e-3) but costs 10–20 % on three of the other four — kept as a variant, not promoted.

**S0 non-regression (`w6b_s0`).** 13/13 T0 certified, median t→cert 0.029 s (identical to §"S0 full"), max 0.067 s; 5/6 named failures in ≤ 0.7 s (same set). Total wall 62 s vs ~4 s before: the whole difference is C7 A3/B3 now *using* its 60 s cap (gap 1.5e-3 instead of 3e-3 after 3 s).

**The five T1 stragglers (`w6b_t1_stragglers`, cap 300 s, 5 workers).** The same bug had left five T1 pairs uncertified in S1 and S2 (gaps 3e-4–7e-3 after 0.3–32 s). With the ladder: C4_contested A1/B1 (50) and A3/B3 (62) certify on the first rung in 2.5 s / 0.7 s (the 1e-9 rung no longer aborts — F1 start, root separation, lighter load); C1-seed2 A3/B3 (82) certifies at the 1e-6 rung after 40 s (gap 2e-9); C9-seed2 A3/B3 (82) at the 1e-6 OA rung after 124 s (gap 0); C4 A2/B2 (61) reaches 2.7e-8 at the 1e-7 rung (SCIP `optimal`, 28 s) with the 1e-9 OA tighten-back rung aborting. `scip_tree` on T1 goes from 58/63 to 62/63 certified; the 46–82 band from 23/28 to 27/28.

**The seven large pairs at 1200 s.**

| instance | n | status | gap W6b | gap S2 | `flow_pwl` @1200 s | t | rungs run (feastol/form → SCIP status, s) |
|---|---|---|---|---|---|---|---|
| C7b_s2 A2/B2 (control) | 77 | optimal | 0 | 0 | 4.5e-07 | 0.8 s | 1e-9/nat → optimal |
| C7b_s1 A3/B3 (control) | 114 | optimal | 2e-13 | 1e-14 | 3.2e-07 | 0.1 s | 1e-9/nat → optimal |
| C7b_s2 A1/B1 | 124 | time_limit | **1.09e-07** | 4.26e-03 | 1.39e-03 | 219 s | 1e-9 unk 6 · 1e-7 unk 25 · **1e-6 optimal 157** · 1e-9/oa unk 30 |
| C7b_s2 A3/B3 | 135 | time_limit | **2.96e-08** | 8.81e-04 | 1.02e-04 | 280 s | 1e-9 unk 15 · 1e-7 unk 8 · 1e-6 unk 2 · **1e-6/oa optimal 250** · 1e-9/oa unk 5 |
| C7b_s1 A0/B0 | 169 | time_limit | 4.17e-03 | 4.89e-03 | — | 1200 s | 1e-9 unk 12 · 1e-7 unk 23 · 1e-6 timelimit 1164 |
| C7b_s1 A2/B2 | 197 | time_limit | 4.23e-03 | 5.76e-03 | — | 1200 s | 1e-9 unk 5 · 1e-7 unk 2 · 1e-6 timelimit 1193 |
| C7 A3/B3 | 205 | time_limit | **3.37e-04** | 3.36e-03 | 6.44e-03 | 1200 s | 1e-9 unk 3 · 1e-7 unk 10 · 1e-6 timelimit 1186 |
| C7b_s1 A1/B1 | 320 | time_limit | **1.33e-04** | 1.43e-03 | 1.73e-04 | 1200 s | 1e-9 unk 1 · 1e-7 unk 8 · 1e-6 timelimit 1192 |
| C7b_s2 A0/B0 | 464 | time_limit | **2.34e-03** | 1.16e-02 | — | 1200 s | 1e-9 unk 1 · 1e-7 unk 1 · 1e-6 unk 15 · 1e-6/oa timelimit 1183 |

No pair flips to `optimal`; all seven improve, five by 5–40 000×; four now beat `flow_pwl`'s 1200 s bound.

**Readings.**

- **`scip_tree`'s "scale wall at ~125 zips" was an unused-budget artefact, not a search limit.** §S2's conclusion stands for the *method families* (`flow_pwl` and `loop_v2` genuinely spend the budget), but not for `scip_tree`'s numbers: with the ladder running, 124 and 135 zips land at 1.1e-07 and 3.0e-08 — three to four orders below S2 — and stop *early* (219 s, 280 s) because nothing tighter is left to try. §S2's "mechanism (b) is not a budget problem" is withdrawn for this method.
- **Below ~160 zips the remaining wall is numerical, not combinatorial.** On 124 and 135 SCIP reaches its own `optimal` on a loosened rung, and the residual is that rung's feasibility-tolerance floor (recomputed gap ≈ 2·feastol; `CERT_TOL = 1e-8` is within a factor of 3 at 135). Every 1e-9 rung — native *and* OA — aborts in 0.5–30 s at these sizes. Closing the last 1e-7 needs a numerically different certificate (a bound that does not pass through SCIP's stored LP solution — e.g. a post-hoc exact LP bound over the final cut set, or SCIP's exact mode), not more time. **Caveat:** a bound from a rung at feastol f is a floating-point bound, rigorous only to O(f·‖duals‖). In practice it is often far tighter — the T1 re-run below certifies two pairs to ≤ 2e-9 from 1e-6 rungs — so the 1e-7 residuals on 124/135 *may* be tolerance rather than search, and the harness cannot tell the two apart. The cross-method post-pass (0 bugs) and brute force at n ≤ 20 are the independent checks; a rigorous certificate needs an exact post-hoc bound (W6c).
- **The workhorse rung is 1e-6 native.** In all seven, the 1e-9 and 1e-7 rungs abort in 0.6–25 s and the 1e-6 rung (or, on 135/464, 1e-6 OA) produces both the best LB and the best UB. The strict default is still right — it is what certifies everything below ~125 zips on the first rung in well under a second — but above that it is a 30-second probe, not the solve.
- **Mechanism (b) is primal above ~160 zips.** On 169 and 197 the LB moves 4e-4 and 8e-4 over 1200 s while the UB barely moves; these two are the only pairs still at S2's order of magnitude. The dual side is essentially done (gap 1e-4 at 320 zips); the incumbent is what is missing — the reduction layer (E1) and a stronger primal heuristic inside the tree are the levers, and they are exactly what real sparse-glue instances (T3) will exercise.
- `warm_f1` as MIP start: a small, non-uniform win (source of the incumbent on all nine rows; helps 320; on 464 the internal fallback happened to give the OA rung a better dive at a 120 s cap). Kept for the `_gain_floor` effect, not for its own LB.
- Any other PySCIPOpt-based method has the same exposure to SCIP's clock under load (`_short_stop` covers it inside `scip_tree` only).

**Where this leaves the programme.** Unchanged in direction, changed in numbers: `scip_tree` is the finalist at every size; 124–135-zip pairs are certified to the solver's tolerance floor (1e-7) and would certify at `CERT_TOL` with an exact post-hoc bound; 160–464-zip pairs hold 1e-4–4e-3 with the budget spent. S3 (T3a at 3600 s, once the twin lands) should run `scip_tree` (default) + `scip_tree_psimplex` + `flow_pwl` (bound cross-check). Follow-ups worth a unit: an exact post-hoc certificate (W6c), and the in-tree primal (E1 reductions + a repair-aware diving heuristic) for 160+ zips.

## Primal/dual diagnostic — 2026-08-30 (`w6b_ils_diag`)

**Question.** W6b left the 126–464-zip pairs uncertified with the budget spent and read the cause as primal (the bound looked done, the incumbent missing). Test in two halves: (1) can a strong external search beat `scip_tree`'s 1200 s incumbent? (2) if it can, does handing SCIP that allocation as a MIP start let the tree close the bound?

**Half 1 — iterated local search** (`ils_diag.py`: F1 multi-start + kick-and-descend perturbation over `warm._local_search`, 2×450 s per pair, starts = fresh F1 and the W6b incumbent):

| n | gain over W6b LB | found in | evidence of optimality |
|---|---|---|---|
| 169 | +3.1e-4 | 0.1 s | both starts converge to the **identical** value (6.458895639); 27k kicks, 668 restarts find nothing more |
| 197 | +1.2e-3 | 0.5 s | incumbent start wins; F1 start plateaus 1e-3 lower |
| 205 | 0 | — | W6b's incumbent never improved (25k kicks) |
| 320 | +9.6e-5 | 98 s | both starts within 1e-5 of each other |
| 464 | +1.6e-3 | 1.4 s | both starts converge to the identical value (6.475755908) |

Two findings: SCIP's 1200 s incumbents on 169/197/464 were not even 1-swap locally optimal (the first local-search pass improved them in ≤ 1.4 s — the in-callback repair's 25 % budget share cuts the descent short); and the search then hits a hard plateau that ~25k perturbations cannot leave, with independent starts agreeing to 9–10 digits on 169/464.

**Half 2 — `scip_tree` warm-started at the ILS best** (`scip_from_ils.py`, 1200 s per pair):

| n | LB (moved?) | UB: W6b → now | gap: W6b → now | nodes (1e-6 rung) |
|---|---|---|---|---|
| 169 | unchanged | 6.46275 → 6.46280 | 4.2e-3 → **3.9e-3** | 179k |
| 197 | unchanged | 6.45818 → 6.45820 | 4.2e-3 → **3.0e-3** | 135k |
| 205 | unchanged | 6.47078 → 6.47058 | 3.4e-4 → **1.35e-4** | 916k |
| 320 | +5.5e-6 (SCIP beat ILS) | 6.46897 → 6.46896 | 1.3e-4 → **2.4e-5** | 1.48M |
| 464 | unchanged | 6.47647 → 6.47641 | 2.3e-3 → **6.6e-4** | OA rung, 2.2k |

**Verdict: the residual gap is dual.** With the (almost certainly) optimal allocation in hand from t = 0, 1200 s of branching still cannot prove it: the bound crawls at ~5e-7 per 1000 nodes on 169/197 and the remaining 3–4e-3 extrapolates to hours-to-days of tree. 205 and 320 nearly close (1.35e-4, 2.4e-5 — another ~2× budget likely finishes them); 169/197 (C7b seed1, the value-concentrated 800-zip scenario) are the hard duals — difficulty tracks value structure, not n. The earlier reading "the bound is essentially done above ~160 zips; the incumbent is what is missing" is **withdrawn**: the incumbent was missing *and* cheap to find; the bound is the expensive half.

**Programme consequences.**
- **W6d (in-tree primal) shrinks to a wiring task, not a unit:** run `warm._local_search` to convergence on every accepted incumbent (or take `mip_start` through the ILS loop for ~5 s). Worth doing — it is +1e-3 LB on three pairs for seconds of work — but it does not close anything by itself.
- **The dual side is the real 160+ work:** deeper-than-root fractional separation, E1 reductions (fewer nodes to bound), or honestly reported 1e-3-scale certified gaps at production size. In economic terms the certified uncertainty is already ≤ 0.4 % of the Nash product on every pair, with the allocation itself agreed by two independent methods.
- W6c (exact post-hoc certificate) unchanged for the 125–160 tolerance-floor regime.

## Two-tier acceptance and the objective's noise floor — 2026-08-30 (`eps_noise_floor`)

**Decision (user, 2026-08-30).** Acceptance becomes two-tier. Tier 1 unchanged: `CERT_TOL = 1e-8`
rigorous certificates, required on T0/T1 and the named failures (W6c upgrades the 124–135-zip
tolerance-floor rows to this tier). Tier 2, for production sizes (T2+): a feasible, valid row
with best-available gap ≤ **`EPS_CERT = 5e-3` nats** counts as *ε-certified*, to be read together
with cross-method primal agreement (ILS plateau + `scip_tree` incumbent). Rationale: the
primal/dual diagnostic above showed the residual 160+ gap is dual slack over near-ties, and the
question "is the last 3e-3 worth proving" is answered by measuring what the objective is even
determined to.

**The noise-floor measurement** (`battery/results/contiguity/eps_noise_floor/eps_bootstrap.py`).
On the hardest dual pair, C7b_s1 A2/B2 (197 zips), 60 bootstrap draws under the contestability
noise model with **θ/λ held fixed** at reference (so parameter uncertainty is excluded):
`A_z, B_z ← ·lognormal(0, 0.10)`, `M_z ← ·lognormal(0, 0.06)` floored at `1.02(A+B)`, free Nash
solved exactly per draw (35 s total):

| statistic of the optimal log-product | value (nats) |
|---|---|
| std across draws | **8.4e-3** |
| IQR | 1.33e-2 |
| median \|shift vs base\| | 8.0e-3 |
| p90 \|shift vs base\| | 2.15e-2 |
| zips flipped vs base allocation | median 24 / 197 (p90 28) |

So `EPS_CERT = 5e-3` sits at ~0.6× the one-σ *data*-noise of the objective itself — and the
measured floor is a lower bound on the real uncertainty, since θ/λ ranges (which contestability
also sweeps) add more. In economic terms ε = 5e-3 bounds the unproven improvement at ≤ 0.5 % of
the Nash product (~0.25 % per gain), while a single re-measurement of the books moves the
optimum by ~0.8 % and reassigns ~12 % of the zips. The achievability side: the worst W6b/ILS
residual is 3.9e-3 (169 zips), so all seven large pairs are ε-certified today with ~25 %
headroom; 1e-3 would fail 169/197 and was rejected for that reason; 1e-2 exceeds the noise IQR
and certifies nothing the data could distinguish anyway.

**Implementation.** `contig_methods/base.py` gains `EPS_CERT` (method-level status semantics
untouched — `optimal` still requires `CERT_TOL`); `contiguity_bench.py` phase 3 stamps a per-row
`eps_certified` flag (feasible ∧ valid ∧ min(own gap, gap vs UB\*) ≤ ε, cumulative over tier 1)
into `rows_scored.jsonl` and an `eps_certified_frac` column into `summary.csv`.

**Consequence for the programme.** S3's pass criterion on T3 is tier 2 + primal agreement;
the dual-side work (deeper fractional separation, E1) is thereby an improvement track, not a
blocker. The ε value should be revisited once against the *twin's* noise floor when T3 lands
(same script, twin instance) — value concentration on real data could plausibly widen, not
narrow, the floor.

## W6d — in-tree primal wiring + 2× budget rerun — 2026-08-30 (`w6d_2026-08-30`, `w6d_s0`)

**Scope.** `scip_tree.py` only (merged `cf7b0b2`; 230 fast tests). Wiring per the primal/dual
diagnostic: every new incumbent — repaired points, SCIP's own accepted solutions
(`BESTSOLFOUND`), the warm start — is descended to convergence (`_polish`: no `ls_moves`
truncation, outside the repair budget share, 5 s per-call cap, reentrancy-guarded
re-injection), and the F1 MIP start goes through a 5 s kick-and-descend loop (`_ils_start`,
gated to n ≥ 100). Counters in `extra` (`n_polish`, `polish_spent`, `mip_start=warm_f1+ils`).

**S0 non-regression (`w6d_s0`).** 13/13 T0 certified, median t→cert 0.032 s (was 0.029 s),
0 errors — unchanged within noise; the ILS gate keeps small pairs untouched.

**The five large pairs at 2400 s** (ρ=0, 4 workers; W6b @1200 s and the ILS-warm-started
diagnostic @1200 s as baselines):

| instance | n | gap W6b | gap ILS-warm | **gap W6d @2400 s** | ε-cert (5e-3) | t | polish calls |
|---|---|---|---|---|---|---|---|
| C7b_s1 A0/B0 | 169 | 4.2e-3 | 3.9e-3 | 3.93e-3 | ✓ | 2400 s | 2 |
| C7b_s1 A2/B2 | 197 | 4.2e-3 | 3.0e-3 | 3.15e-3 | ✓ | 2400 s | 3 |
| C7 A3/B3 | 205 | 3.4e-4 | 1.35e-4 | 2.69e-4 | ✓ | 2400 s | 6 |
| C7b_s1 A1/B1 | 320 | 1.3e-4 | 2.4e-5 | **1.22e-6** | ✓ | 1883 s | 1 |
| C7b_s2 A0/B0 | 464 | 2.3e-3 | 6.6e-4 | 5.61e-4 | ✓ | 2116 s | 1 |

**Readings.**

- **All five pairs are ε-certified — the first full sweep of the large-pair set under the
  two-tier criterion.** Nothing above 3.9e-3; worst pair's unproven improvement ≤ 0.4 % of
  the Nash product with the allocation cross-method agreed.
- **320 nearly reaches tier 1** (1.22e-6, two orders below W6b, stopping at 1883 s with the
  ladder exhausted); it is the next candidate for a W6c exact post-hoc bound.
- **The dual wall on 169/197 is confirmed:** doubling the budget *and* the primal wiring
  moved their gaps by ~zero versus the ILS-warm baseline. The diagnostic's optimism on 205
  is withdrawn — at 2400 s a fresh tree landed at 2.7e-4, slightly *worse* than the
  diagnostic run's 1.35e-4 (tree/seed variance dominates at this gap scale; 1.35e-4 remains
  the best-known certificate for 205).
- **The wiring is essentially free** (≤ 6 polish calls, < 1 s total per pair) and every MIP
  start improved through the ILS loop — but a 5 s start-ILS is not the diagnostic's 900 s
  search: on 169/197 the run's incumbents sit ~1e-4 *below* the known ILS plateau values.
  Feeding the known-best allocations (or scaling the start-ILS budget with n) is a
  one-line follow-up; it changes LB cosmetics, not the dual wall.
- **Consequence:** below ~1e-3 on the value-concentrated pairs only dual-side work moves the
  needle — deeper-than-root fractional separation, E1 reductions on real sparse-glue
  instances, or W6c exact bounds. The ε tier is already met everywhere, so none of it blocks
  S3.
