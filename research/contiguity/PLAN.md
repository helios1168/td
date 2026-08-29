# Contiguity-option development programme — PLAN

**Approved:** 2026-08-28 · **Owner:** Nicolas Lee · **Source of truth for the programme.**
This file supersedes `OPEN_QUESTIONS.md` §A items 1, 2, 5, 6, 8, 9 and `TEST_PLAN.md` §6 (real
opportunity file) — see §"Decisions taken 2026-08-28" below. `OPTIONS.md` (option briefs) and
`TEST_PLAN.md` (harness spec, tiers, metrics, acceptance) remain authoritative where this file
does not override them.

## 0. Resume — read this first in a fresh session

**State on 2026-08-29 (evening):** on `contiguity-harness`: U0a–U1a, **U1b, U2, U4, U7 merged**;
**S0 smoke done** (`RESULTS.md` §S0: brute ground truth on T0; legacy control certifies 0/6 named
failures; CLAUDE.md traps 12–13 recorded). In flight in worktrees: U3 (`wt/u3`), U5 (`wt/u5`),
the method wave W4 (plan), W5, W6 (plan), W7, W8, W9a (`wt/w*`). Next ★: W4/W6 plans, then merges,
S0 rerun with each method, ★3 before S1. User decisions taken today: all three twin privacy
aggregates may leave; work graph is a pyarrow edge cache on the ZCTA 2025 vintage (edge set
identical to TIGER2020 — `data/README.md`). Earlier that day: kick-off steps 1–5 done on branch `contiguity-harness` (U0a anchors,
U0b `districting.py` hygiene, U0c deps/params, **U1a contract frozen** —
`battery/code/contig_methods/base.py`, registry, `fake.py`, `tests/test_base.py`; 23 fast tests
green, zip50 anchor byte-identical). Next: ★ brief the parallel wave (step 6: U1b, U2, U3, U4, U5,
U7). Findings while building: (i) the legacy loop's "optimal" is certified only to HiGHS'
default `mip_rel_gap=1e-4` (C8 pair at ρ=0: 6.3e-4 nats) — `districting.solve_contiguous_nash`
gained `milp_options` so U2 can build a tight `current` variant, and the contract has a
`gap_limit` status; (ii) the `cbcbox` wheel's GCC dylibs fail macOS code-signing (SIGKILL) —
fix documented in `requirements.txt`, guarded by `tests/test_env.py`. The programme runs on
`contiguity-harness` with one worktree branch `wt/<unit>` per unit.

**Kick-off sequence (main session, in order):**

1. `git checkout -b contiguity-harness main`.
2. **U0a** — generate the byte-identity anchors (`battery/code/tests/anchors/`) by running
   `code/mkfig_zip50.py` *before* touching any solver file. This is the regression guard for
   everything after it.
3. **U0b** — `code/districting.py` hygiene (Part C.4). Main session, serial. Anchor must stay green.
4. **U0c** — `requirements.txt` (+ `pyscipopt`, `mip`, `highspy`, `geopandas`, `shapely`,
   `pyogrio`, `pandas`), `.gitignore` (`data/tiger/`, `data/twin_*`), the four missing
   `params` keys in `code/synth.py`. Verify S1–S7 bit-identical (`code/TAIL_DISTRIBUTION_NOTE.md`
   procedure).
5. **U1a** — the harness contract `battery/code/contig_methods/base.py` (Part C.1). Fable fork
   subagent or main session. ★ review, then **freeze** — every later unit implements against it.
6. Parallel wave in worktrees: U1b, U2, U3, U4, U5, U7 (Part C.5, Part D, Part G.5). Each unit
   follows the ★ checkpoint protocol (Part A). U3 is the twin-export tool that the user runs on
   the confidential work machine; hand it over as soon as it passes on the stand-in.
7. **S0 smoke** with `current` + `brute` → ★ stage gate → method wave W4–W9a → **S1**.

**Environment facts a fresh session needs:** `.venv/bin/python3` from the repo root (system
python has nothing); `export PATH=/Library/TeX/texbin:$PATH` for `make`; machine is an Apple M2
Max, 12 cores / 32 GB → 11 workers; **never write under `battery/figures/`** (primary artifacts);
harness output goes to `battery/results/contiguity/<run_id>/`. `code/mkfig_zip50.py` is the
numeric anchor (~2 min). `verify_algebra.py` certifies the *superseded* model — it is not a guard.

**How to run a unit:** put the unit's Part C/D/G section verbatim in the brief, plus files owned,
files forbidden, the acceptance command, and "stop and report rather than improvise".
Use plan mode / `AskUserQuestion` for every ★. Model per unit: Part E. Own-plan-step units: Part F.

**Work-machine leg (user-run, off the critical path):** U3 produces `tools/twin_export/`; the
user runs `python -m twin_export stats|twin|audit` there against M, A, B, rep maps and their
existing geopandas/networkx Rook graph; reviews `twin_audit.json` + the audit figure; brings back
`twin_stats.json` (~100 KB) and `twin_instance.json.gz` (~1 MB). Nothing per-ZCTA that is real
leaves; geometry never leaves (TIGER is rebuilt here).

## Decisions taken 2026-08-28 (do not re-ask)

| decision | value |
|---|---|
| Implementation location | this repo: `battery/code/contig_methods/`, results `battery/results/contiguity/` |
| Parallel-work mode | subagents in git worktrees; main session is the only review surface; agent teams / Agent View not used for building; one Workflow script for the S1 fan-out |
| Compactness weight ρ | **ρ = 0 is the model.** ρ>0 was a crutch for the multi-tree loop (Traps 4, 7). Headline results at ρ=0 everywhere; ρ=2e-3 only as a secondary column for the `current` control. Tie-break by lexicographic perimeter post-pass, never a penalty. G1 in-out stabilisation is required for the control. |
| Travel-cost objective κ (OPEN_QUESTIONS 28b) | **explored explicitly (W11)** as a model experiment; adoption needs distribution sign-off |
| Real data | cannot leave the work machine. C10 → **synthetic twin** (Part C.2): aggregates + σ=0.10 rank-jittered instance on public ZCTA IDs, national scope, user-audited. Work machine has M, A, B, rep maps, geopandas + networkx Rook graph + states, pip, internet. |
| Dependencies approved | `pyscipopt`, `mip`, `highspy`, `geopandas`, `shapely`, `pyogrio`; TIGER ZCTA5 2020 download here |
| Adjacency | TIGER Rook built here, cached `data/zcta_adjacency.npz`; twin's edge list cross-checked (Jaccard ≥ 0.999) |
| Graphics | new `code/gfx/` library, paper-grade matplotlib PNGs only; old figure scripts frozen as the anchor |
| Regional instances | R1 NY+ (NY,NJ,CT,PA,VT,MA), R2 CA+ (CA,OR,NV,AZ), R3 TX — public data only (U8) |
| Dense components | component-level MNW recommended over leximin (W12); user decides at ★ |
| Screening scope | G2/G4 hygiene + G1 kept; G3 and H dropped unless A/B blocked |
| Still the user's call at stage gates | S2 cap/workers (A.4); finalists; ρ=2e-3 secondary column kept?; S3 dry run on synthetic values (A.7); merge-to-main timing (A.10); MNW vs leximin (W12) |

---

# Plan: contiguity-option development programme

**Date:** 2026-08-28 · **Integration branch:** `contiguity-harness` off `main`; units on `wt/<unit>` worktrees; main session merges.

## Context

`research/contiguity/` ranked eight options (A–H) for the `solve_contiguous_nash`
convergence failures (Trap 11) and specified a benchmark harness (`TEST_PLAN.md`). **No harness
or method code exists.** Decisions taken today that change the plan:

1. **Real data cannot leave the work machine.** `TEST_PLAN.md` §6 / `OPEN_QUESTIONS.md` A.1
   (opportunity file dropped into `battery/data/`) is void. C10 is rebuilt as a **synthetic
   twin**: a script runs on the work machine (which has M, A, B, rep maps, geopandas + networkx
   Rook adjacency + states, pip, internet), emits fitted aggregates + a rank-jittered
   (σ=0.10) synthetic instance on real public ZCTA IDs (national, ~33k), and the user audits
   what leaves before it does.
2. Approved: `pyscipopt`, `mip`, `highspy`, `geopandas/shapely/pyogrio`, TIGER ZCTA5 2020
   download here (public).
3. Parallel mode: **subagents in git worktrees**, main session as the only review surface,
   human checkpoint before each major leg.

Outcome: (i) harness + twin pipeline first; (ii) options A–F in parallel workstreams against
the frozen contract; (iii) S1 screening → finalists → S2/S3 overnight → `RESULTS.md`, paper §5,
`CLAUDE.md` Trap 11 update.

---

## Part A — Parallel-work mode

**Chosen: subagents + `isolation: "worktree"`, main session coordinates.** Each unit edits a
disjoint file set on its own branch; results return to the main session; `maxTurns` caps give a
hard stop for review. Agent teams rejected (experimental flag, teammates cannot prompt the
user, higher cost — the `base.py` contract replaces the cross-talk they would provide). Agent
View only for dispatching the S2/S3 overnight *runs* as independent sessions. One deterministic
`Workflow` script for the S1 fan-out (repeatable, no mid-run input needed).

### Checkpoint protocol (every unit, every workstream)

```
★0 Brief approved   main session shows: files owned, contract consumed/produced,
                    acceptance test, open questions answered  → AskUserQuestion
 1 Plan             Plan-type subagent (read-only) returns steps + risks
★1 Plan reviewed    summary shown in main session
 2 Build            general-purpose subagent, isolation=worktree, maxTurns cap, commits on wt/<unit>
 3 Verify           subagent runs the unit's acceptance test + tests/run_all.py
                    (+ test_zip50_anchor.py whenever districting/territory/synth are touched)
★2 Diff reviewed    main session shows git diff --stat + test output
 4 Merge            main session merges wt/<unit> → contiguity-harness; runs S0 if a method landed
★3 Stage gate       before S1 / S2 / S3: run matrix, caps, worker count approved
```

**Serial-only files** (main session, never a subagent): `requirements.txt`, `.gitignore`,
`code/districting.py`, `code/territory.py`, `CLAUDE.md`, `research/contiguity/*.md`, and the
`params`-keys edit to `code/synth.py`. Every subagent brief carries: the unit brief, `base.py`,
the acceptance test, and **"never write under `battery/figures/`"**.

---

## Part B — Workstreams, dependency graph, open questions

```
U0a anchors → U0b districting hygiene → U0c deps+params → U1a CONTRACT (critical path)
                                                              │
        ┌──────────────┬──────────────┬──────────────┬────────┴──────┬──────────────┐
      U1b tiers+bench  U2 current/    U3 twin export  U4 twin loader  U5 synth calib  U7 gfx library
                       brute/bounds   (→ work machine ★ audit)        (S8_twin…)      (Part D)
        └──────────────┴──────┬───────┴──────────────┴───────────────┴──────────────┘
                              ▼  S0 smoke (current+brute)  ★
   W4 flow(+C PWL)  W5 warm F1/F3  W6 SCIP tree  W7 CBC tree  W8 prep E1/E3
   W9a loop_v2 (G1 in-out + G2 min-separator, ρ=0 control) + lexi-perimeter post-pass   (all parallel)
                              ▼  U6 T3 wiring → S1 screening (Workflow, ρ=0) → RESULTS.md ★ finalists
                              ▼  S2 overnight (ρ=0 headline, ρ=2e-3 secondary, T3) → S3 dry run → S4 state ★
   W11 travel-cost objective κ (model experiment on the same harness; needs U1a + U5/U4 seeds) ★ sign-off
   U8 regional real-geography instances (R1 NY+, R2 CA+, R3 TX; public data only) → T3c   (after U4+U5)
   W12 component-level MNW for dense components (1A×2B …) on the S1 winner              ★ MNW vs leximin
                              ▼  W10 CLAUDE.md Trap 11 + paper §5 + OPEN_QUESTIONS closure
```

### Open questions to settle before each workstream starts

| WS | Question (source) | Answer / owner |
|---|---|---|
| U0–U1 | A.6 where implementation lives | **Decided:** this repo, `battery/code/contig_methods/`, results `battery/results/contiguity/`. |
| U1 | A.9 ρ policy | **Decided 2026-08-28: ρ=0 is the model and the headline in every stage.** ρ was an engineering crutch for the multi-tree loop (Traps 4, 7), not part of the model; A/B/C/D enforce contiguity as a hard constraint and need no penalty. ρ=2e-3 kept only as a secondary column for `current` continuity with battery/paper numbers; 2e-4/1e-5 dropped. Tie-breaking among Nash-optimal contiguous allocations, if wanted, is the **lexicographic perimeter post-pass** (W9a), never a penalty. |
| U1 | A.5 screening scope | G2/G4 folded into U0b/U2 variants; **G1 in-out now required** so the `current` control is meaningful at ρ=0 (W9a `loop_v2`); G3/H dropped unless A/B blocked. **Confirm at ★3.** |
| W11 | 28b travel-cost objective `u_i(z) −= κ·d(z,p_i)` — explore? | **Yes, explicitly (W11).** A model experiment separate from the solver options: measure κ* (emergence of contiguity), welfare redistribution vs. hard-contiguity at κ=0, and both combined. Adoption needs distribution sign-off; exploration does not. |
| W11 | Rep bases `p_i` | Twin/synth: the territory seeds. Real bases are per-rep data and stay on the work machine; `twin_export` adds **territory-radius aggregates** (quantiles of hop/km distance from a rep's opportunity-weighted centroid to its zips) to calibrate κ's scale. |
| W11 | Distance metric and κ units | Both graph hops and km (equal-area); report a scale-free `κ' = κ·median(d)/median(u)`. Decide at W11 ★1. |
| U1 | B.22 scaling | Harness rescales Σ(u_a+u_b)=100 per pair; `--no-rescale` invariance test decides G4. No decision. |
| U0b | E.36 `solve_contiguous` old baseline | **Untouched.** |
| U3 | Work-machine inputs | **Answered:** M, A, B, rep_a, rep_b all exist → every fit is real; `alpha` calibrated to measured misalignment. |
| U3 | Geography / scope | **Answered:** national, ~33k ZCTAs; twin ≈1 MB gzipped. |
| U3 | Privacy dial | **Answered:** rank jitter σ=0.10 default; user reviews `twin_audit.json` before export (★). |
| U3 | A.7 synthetic values for S3 dry run | Twin is synthetic throughout, so S3 = "production-shaped dry run". **User confirms at ★3 for S3.** |
| U4 | A.2 adjacency source | **Both:** edge list travels with the twin (public-derivable); rebuilt from TIGER here; `edge_diff` asserts Jaccard ≥ 0.999. |
| W4 | Roots: keep argmax/argmin fixing (a restriction) or selectable roots | Flow uses selectable roots (`Σr_z=1, r_z≤x_z`); decide final at W4 ★1. `brute` reports `opt_has_ratio_roots` to size the loss. |
| W4 | B.16 PWL ε | Measure ε∈{1e-4, 1e-6}. |
| W5 | F3 kept only if it beats F1 | Rule set (TEST_PLAN §7). |
| W6 | B.15 A′ native-log certifies globally? `trySol` works? | Smoke test on C1 first thing in W6; report at ★1 before building the Conshdlr. |
| W8 | B.13 E1 two-sided safety | Short proof or restrict to the two obviously-safe rules. **T1 has no zero-value zips → acceptance must run on T3 / `p_active` instances.** |
| W8 | E3 never labelled `optimal` | Rule set. |
| S2 | A.4 cap 20 min, 11 workers | **User confirms at ★3.** |
| S2 | Which 3 finalists | **User, from `RESULTS.md` after S1.** |
| W10 | A.10 merge to `main` | Proposed: after S1 results exist. **User.** |

### Effort (engineering)

| unit | effort | parallel with |
|---|---|---|
| U0a/U0b/U0c (main, serial) | 1 h / 3 h / 1 h | — |
| U1a contract (critical) | ½ day | — |
| U1b tiers + bench | 1 day | U2–U5 |
| U2 current/brute/bounds | 1 day | U1b, U3–U5 |
| U3 twin export | 2 days + user run on work machine | U1b, U2, U4, U5 |
| U4 twin loader + TIGER | 1 day | U1b, U2, U3, U5 |
| U5 synth calibration | 1 day | U1b–U4 |
| U6 T3 wiring (main) | 2 h | after U1b+U4+U5 |
| W4 flow (+C) | 1 day | W5–W8 |
| W5 warm F1/F3 | 1 day | W4, W6–W8 |
| W6 SCIP tree | 2 days | W4, W5, W7, W8 |
| W7 CBC tree | 1 day | W4–W6, W8 |
| W8 prep E1/E3 | 1 day | W4–W7 |
| W9a loop_v2 (G1+G2) + lexi-perimeter post-pass | 1 day | W4–W8 |
| W11 travel-cost κ experiment | 1½ days (½ design, 1 build+runs) | after U1a + U5; runs alongside S1 |
| S1 / S2 / S3 compute | 20–65 min / overnight / overnight | — |
| W10 docs + paper | ½ day | — |

---

## Part C — The "do first" code piece

### C.0 Spec-vs-code conflicts resolved in the contract

| # | TEST_PLAN says | Code does | Resolution |
|---|---|---|---|
| 1 | `pieces = 1/1` on `optimal` | 3 of 6 named-failure **pair subgraphs are already disconnected** (C1-seed2 A0/B0 {67,2}; C5-resp A2/B2 {35,12,11,2,1}; C7 A1/B1 {40,4}); `districting.py:127` skips components with no outside neighbour → de-facto component-wise feasibility | **Feasible ⇔ for every component K of the filtered pair graph, S∩K and K∖S are each connected or empty.** Report `pair_components, pieces_a, pieces_b, excess_pieces`; `optimal` requires `excess_pieces==0`. `brute.py` enumerates under this definition. |
| 2 | `gap=(UB−LB)/|UB|` | objective `log g_a+log g_b−ρ·per` shifts by `2 log s` under rescale → relative gap not scale-invariant | Primary `gap_nats = UB−LB` (matches `nash_exact`'s units, ≤1e-8 acceptance); secondary `gap_rel = 1−exp(−gap_nats)`. |
| 3 | method `UB` bounds the contiguous optimum | `districting.py:81` hard-fixes roots = a *restriction* | `Result.ub_scope ∈ {"global","rooted"}`; cross-method `UB*` uses global only; harness downgrades rooted `optimal` → `status_eff="optimal_rooted"`, `valid_certificate=False`. |
| 4 | C7 A3/B3 is iteration-limit | JSON says `solver failed` (HiGHS 20 s per-MILP limit, `:116`) | `current.py` maps "time" in message → `time_limit`, keeps last iterate. |
| 5 | `respect_state` is a method flag | `:76` deletes edges itself; silent no-op without `state` | Harness deletes cross-state edges and passes the filtered graph with `respect_state=False` to `current`; raises if no `state` attr; validator checks. |
| 6 | cache adjacency as parquet | no pandas/pyarrow in venv | `data/zcta_adjacency.npz` (numpy only); geopandas imported only inside `twin.build_rook_adjacency`. |
| 7 | no test framework | none in repo | `battery/code/tests/` plain `test_*.py` + `run_all.py` auto-discovery (pytest-compatible). |
| 8 | regenerate from `params` | `synth.py:195-201` omits `book_ratio, theta, lam, n_metros` (all default in C1–C9) | add the four keys (no draw change); loader tolerates absence. |
| 9 | regime (d) zero-value zips | `ua/ub` → NaN at A=B=M=0 (`districting.py:80`, `territory.py:150`) | ratio guard `np.where(ub>0, ua/ub, np.where(ua>0, inf, 1.0))` — identical on positive data. |

T1 utility scale today: Σ(u_a+u_b) ∈ [2.3, 129] → rescale factor 0.8–43×; absolute seeds {1,3,5,8,11} stay in range at Σu=100, so G4 is opt-in (`current_q` variant), decided by the `--no-rescale` invariance runs.

### C.1 Harness skeleton (U1a, U1b, U2)

```
battery/code/contig_methods/__init__.py   REGISTRY by auto-discovery (module exposes NAME, EXACT, MAX_N?, VARIANTS?, solve)
battery/code/contig_methods/base.py       Result, Trace, objective, validators, fairness audit, covariates
battery/code/contig_methods/current.py    adapter over districting.solve_contiguous_nash
battery/code/contig_methods/brute.py      exhaustive ground truth n ≤ 20 (bitset BFS, component-wise feasibility)
battery/code/contig_methods/bounds.py     ub_free_fractional (prefix_table + one split zip), ub_free_nash (nash_exact + gap)
battery/code/instances.py                 InstanceSpec, PairInstance, tiers T0–T4, NAMED_FAILURES, build_pair (filter→rescale)
battery/code/contiguity_bench.py          CLI driver, Pool(workers, maxtasksperchild=1), rows.jsonl (append+fsync), summary.csv, instances.csv
battery/code/tests/{run_all.py, test_base, test_bounds, test_brute, test_current, test_instances, test_zip50_anchor, anchors/}
battery/results/contiguity/<run_id>/{rows.jsonl, summary.csv, instances.csv, jobs.json, assign/*.npz}
```

**Contract (`base.py`) — frozen at U1a merge:**
- Units: `u_a=c1A+c2B+λM`, `u_b=c2A+c1B+λM` as `territory._fields` (`territory.py:134`); **objective `obj(S)=log g_a+log g_b` with contiguity as a hard constraint — ρ defaults to 0 everywhere.** `−ρ·perimeter(S)` is admitted only as an explicit secondary axis (`rho>0`) for `current` continuity with battery numbers; `perimeter` is always reported as a diagnostic. For W11 the harness supplies node attrs `d_a, d_b` and `kappa`, and utilities become `u_i −= κ·d_i` (methods must read `u_a, u_b` from `base.utilities(G, nodes, theta, lam, kappa)`, never recompute them). All row quantities on the rescaled pair, `scale` recorded.
- Tie-breaking (W9a): `base.lexi_perimeter(G, nodes, to_a, opt_value, method)` — fix `log g_a+log g_b ≥ opt_value − 1e-9`, minimise perimeter with hard contiguity (reuses the chosen engine). An exact post-pass; reported as `perimeter_lexi`, never changes `LB/UB`.
- `solve(G, nodes, *, theta, lam, rho, respect_state, time_limit, seed, warm_start=None, reductions=None, trace=None) -> Result`. `G` = pair subgraph copy (attrs `A,B,M,state,pos` only, already filtered/rescaled); `nodes=sorted(G)`; methods self-enforce `time_limit`, set 1 solver thread, are deterministic in `seed`, never mutate `G`.
- `Result(status, to_a, LB, UB, ub_scope, eps, iters, n_cuts, n_tangents, nodes, t_first_feasible, t_total, trace, extra, message)`; `STATUSES=("optimal","time_limit","iteration_limit","heuristic","infeasible","error")`. `optimal` ⇒ feasible ∧ `UB−LB ≤ 1e-8+eps` ∧ global scope. Heuristics: `UB=None`. Time-capped: `to_a` may be the last infeasible iterate with `LB=None` (harness stores as `last_iterate`).
- `Trace` is **harness-owned**: methods call `trace.incumbent(to_a, obj)` / `trace.bound(ub)`; harness fills `Result.trace=[(t,LB,UB)]` and survives its SIGALRM backstop (`1.25·cap+30 s`).
- Harness recomputes (never trusts): `g_a, g_b, product, perimeter, LB, pieces_*, excess_pieces, ef1_ab, ef1_ba, envy_over_umax, prop_shortfall_*, cost_of_contiguity, UB_free_*, product_free, gap_*, t_total`. Trusts: `status, UB, ub_scope, eps, iters, n_cuts, n_tangents, nodes, t_first_feasible, extra`.
- Validators (row always written with `valid`, `violations`): partition; `optimal ⇒ excess_pieces==0`; `product ≤ product_free(1+1e-9)`; `|LB−LB_recomputed| ≤ 1e-9`; state filter applied (`edge_share_deleted` recorded); `optimal ⇒ UB−LB ≤ 1e-8+eps`; rooted downgrade; post-hoc `LB > UB*_global+1e-8` flags a bug.
- Fairness at d=0: `ef1_ab = v_a(T)−max_{z∈T}u_a(z) ≤ g_a` (and mirror); `envy_over_umax = max(envy⁺/u_max of envied bundle)`; `prop_shortfall = max(0, ½Σu_i − g_i)/max_z u_i(z)`.
- Covariates per pair: `n, n_edges, pair_components, articulation_points, block_tree_is_path, free_pieces_*, free_perimeter, gini_u, top5_share_u, active_frac, edge_share_deleted, n_states`.

**`current.py`:** calls `D.solve_contiguous_nash(..., respect_state=False, max_iter, time_limit=min(20, cap), deadline, on_iter=cb)` (U0b additions). `UB = min_k` master objective (or `−res.mip_dual_bound` on HiGHS time-out), `ub_scope="rooted"`, `extra={root_a, root_b}`. `to_a` = best *feasible* iterate from `trace` if any, else last iterate with `LB=None`. Variants: `current_unbounded` (`max_iter=10**6`), `current_q` (`g0_seeds="quantile"`).

**`bounds.py`:** fractional bound via `prefix_table` (`territory.py:142`): for each prefix k with next zip z, `t*=clip((ua_z·gb[k]−ub_z·ga[k])/(2ua_z ub_z),0,1)`, `UB_free_frac = log max_k (ga[k]+t*ua_z)(gb[k]−t*ub_z)`; `UB_free_nash = log g_a+log g_b+max(0,gap)` from `nash_exact` (`territory.py:170`). Both bound obj since `ρ·per ≥ 0`.

**`instances.py` tiers:** T0 = `S1_aligned` n∈{40,50,60}, 4×4 reps, seeds 1–10, pairs 8–20 zips (~15) + hand graphs (P8, trident, C10) for tests. T1 = every pair of C1_aligned_seed{1,2}, C2_entangled_a0/a05, C3_slivers_ms02, C4_separate/contested, C5_states_free, C6_tight/loose, C9_heavytail_seed{1,2} with `n_expected` from `battery/figures/C*.json`. T2 = C7_scale_n400 (205/125/44/26) + C7b `S1_aligned` n=800 seeds 1–2. T3 = C.3. T4 = C5_states_resp + T3a with `--respect-state`. `NAMED_FAILURES` = the six. `select_pairs` re-implements `case_pipeline.pair_solves` (`:42-77`) without solving.

**`contiguity_bench.py` CLI:** `--stage {S0..S4} --methods --tiers --instances REGEX --cap --rho 0[,2e-3] --kappa 0[,…] --respect-state --workers 11 --run-id --dry-run --max-iter --seed --no-rescale --lexi --save-assignments --resume`. Presets (**ρ=0 default everywhere**): S0 = T0+named, `current,current_inout,brute(+flow,warm)`, 60 s; S1 = T0+T1+T2, all, 60 s, ρ=0 (+ ρ=2e-3 for `current` only); S2 = T1+T2+T3, finalists, ρ∈{0, 2e-3}, 1200 s; S3 = T3a, 3600 s; S4 = T4, 1200 s. `--kappa` runs are W11's experiment matrix. Phase 1 computes covariates+bounds → `instances.csv`; phase 2 `imap_unordered` jobs → `rows.jsonl`. Output root constant; assert refuses any path containing `battery/figures`. `summary.csv` per method×ρ×tier: `certified_frac, rooted_optimal_frac, feasible_frac, median_t_to_cert, median_gap_nats_at_cap, worst_gap, mean_cost_of_contiguity, ef1_frac, named_failures_certified k/6, errors, gap_at_{5,20,60,300,1200}s`; `instances.csv` gets `UB_star_global` and per-method `gap_vs_UB_star`.

### C.2 Work-machine export (U3) — `tools/twin_export/`, runs on the work machine only

Self-contained (numpy/scipy/pandas/networkx; geopandas optional); vendors `validate/overlap_graph/census` from `territory.py:30-130` into `_territory_vendored.py` with a sync test here. `python -m twin_export {stats|twin|validate|audit}`.

Inputs (all present per user): `--graph` (networkx Rook + `state`), `--opportunity zcta,M`, `--sales zcta,A,B`, `--reps zcta,rep_a,rep_b`.

**`twin_stats.json` (≈60–120 KB, aggregates only, `--strip-scale` on by default):** marginals for M, A, B, A/M, B/M — lognormal MLE, dPlN/normal-Laplace MLE (α,β,ν,τ; Reed–Jorgensen density; L-BFGS-B from Hill start), KS/AD, ΔLL, `prefer_dpln`, quantiles p01–p99 (no max), `coarse_cdf` (200 equal-probability bins, bin means, <N merged); conditional share curves by M-decile (`mean/sd log(A/M)`, `P(A>0|d)`, same for B), `corr(logA,logB)`, partial corr given decile, activity corr; headroom slack quantiles at θ=0.4; spatial (Moran's I of log M/A/B/activity, neighbour rank corr, `rank_corr_by_hop[1..5]`); graph (n, m, degree hist, components, articulation points, bicomp size quantiles, state-cross share, no-polygon count); territories (reps/firm, zips-per-rep and pieces-per-rep quantiles, misalignment Jaccard/ARI/NMI, rep state purity, census@0.02: components, 1-1 share, orphan share, pair-size quantiles, dense share); per-state blocks (<N merged to OTHER); `twin_check` (same keys recomputed on the twin + tolerances + pass). **k-anonymity guard:** every number passes `Agg.put(key, value, n_support)`; `n_support < N` (default 20) raises; JSON writer refuses lists >250 except `coarse_cdf`.

**`twin_instance.json.gz` (≈1 MB):** `meta{seed, rank_sigma=0.10, coarsen, swap_rounds, alpha, n_rep_a, n_rep_b, theta, graph_hash, tiger_vintage}`, `nodes{z, state, A, B, M, rep_a, rep_b}` (columnar), `edges{u, v}`, `audit{...}`. Synthesis: rank M (zeros bottom) → jitter `r'=r+σ·n·ε` (+ optional adjacent swaps / `--coarsen decile`) → bottom `1−p_active` → M=0, rest inverse-CDF of `coarse_cdf` → rescale ΣM=40n/50 → activity fields for A, B (graph-smoothed Gaussian, per-decile thresholds, fitted activity corr) → `log(A/M), log(B/M)` from decile μ/σ with partial corr, ε_A graph-smoothed one step → headroom repair (scale A,B down jointly; report fraction) → rep maps: seeds ∝ M, multi-source BFS Voronoi on the Rook graph (in-state if measured purity > 0.95), B seeds copy A's with prob `alpha` else random-walk 4 hops, `alpha` bisected to the measured Jaccard. Validation: vendored `validate` == [], census@0.02, `twin_check.pass`.

**Privacy audit (`twin_audit.json`, printed before writing):** per M/A/B: Pearson on log, Spearman, share of ZCTAs within 1 % / 5 % rank, exact-rank matches vs expected under σ, exact-value matches (must be 0), 3-hop neighbourhood correlation (what is meant to survive), activity-flag agreement. User signs off at ★ by comparing individual-level vs neighbourhood-level columns. **Geometry does not leave** — TIGER is public; only ZCTA IDs, edge list, state (all public-derivable) travel, and `graph_hash`.

### C.3 Repo-side ingestion (U4, U5, U6)

**`battery/code/twin.py` (U4):** `fetch_tiger()` (TIGER2020 `tl_2020_us_zcta520.zip`, ~500 MB → `data/tiger/`, gitignored); `build_rook_adjacency(shp)` (geopandas/shapely only here: `sindex.query(predicate="intersects")`, keep pairs with `intersection().length > 0`; centroids from `INTPTLON/LAT`) → `save/load_adjacency("data/zcta_adjacency.npz")` (committed, ~2 MB); `load_twin(path, check_edges=True)` → networkx G in repo schema (`rep_a, rep_b, A, B, M, state, pos` equal-area xy in [0,1]², `G.graph["twin"]=True`); `edge_diff` asserts Jaccard ≥ 0.999 and prints diffs; `twin_pairs(G, min_share=0.02, bands=(200,400,800), per_band=2, largest=4)` → T3a specs.

**`code/synth.py` (U5):** new kwargs default off and draw from a child generator `rng2 = default_rng([seed, 7919])` so S1–S7 stay bit-identical: `p_active` (smoothed field thresholded → `A=B=M=0`), `share_curve` (per-decile μ/σ replacing `_share` at `:154-156`), `assign="graph"` (multi-source BFS Voronoi + `alpha`/`b_hops` for B), plus fitted `tail/m_tail_*`, `sales_tail*`, `saturation`, `book_ratio`, `rho_books` (bisection on a probe to match fitted log-corr), `n_rep_a/b≈90`. `calibrate(stats) -> overrides`; `SCENARIOS["S8_twin"]`; `scenario()` gains the `calibrated` branch. `params` gains the new keys. `tests/test_synth_compat.py`: regenerate every `C*.json`, assert pair lists, `n_zips`, `corr_AB, Sa, Sb, Mtot` to full precision and free-Nash `product` to 1e-9.

**T3 (U6):** T3a = twin sliced by census (2 pairs nearest 200/400/800 + 4 largest ≈ 10); T3b = `S8_twin` n∈{2000,4000,8000}, 10×10 reps, seeds 1–2, 2 largest pairs each (≈12), `-ln` vs `-ht` variants when the fit prefers dPlN. Report `active_frac` per pair (decides whether E1 matters).

### C.4 `districting.py` hygiene (U0b, main session, byte-identity guarded)

| change | where | default = old |
|---|---|---|
| `deadline=None`: per-MILP `time_limit=min(time_limit, deadline−now)`; ≤0 → `status="time limit"` with iterate | `:113-115` | yes |
| `on_iter=None` callback `dict(it, x, ga, gb, master_obj, dual_bound, added, n_cuts, n_tangents, pieces, perimeter_true)` | after `:139` | yes |
| non-convergence returns carry `to_a, k, g_a, g_b, product, perimeter, perimeter_true, pieces, iters, message` (`solver failed` too when `res.x` exists) | `:117`, `:148` | mkfig never hits these |
| `pieces`, `perimeter_true` added to the `optimal` dict | `:144-147` | additive |
| ratio guard | `:80` (+ `territory.py:150`) | identical on positive data |
| `g0_seeds=None` (`"quantile"` → geomspace as `territory.py:199`), `z_bound=50.0`, `seed`, `threads` recorded only | `:99`, `:104-105` | yes |

Do not touch `solve_contiguous` (E.36). Anchor: `mkfig_zip50.py` §6 lines (three ρ rows) modulo `time=` tokens; byte-identical `figures/{nash_solution,zip50_nash_milp,nash_contestability}.png` via sha256 in `tests/anchors/`.

### C.5 Unit table (files owned → no overlap in the parallel wave)

| unit | owns | consumes → produces | acceptance | needs |
|---|---|---|---|---|
| **U0a** (main) | `tests/{run_all.py, anchors/*, test_zip50_anchor.py}` | — → anchor hashes/stdout | anchor test passes twice | — |
| **U0b** (main) | `code/districting.py`, guard in `code/territory.py:150` | C.4 | anchor green; `perimeter_true==perimeter` at ρ>0 on C8 pair | U0a |
| **U0c** (main) | `requirements.txt`, `.gitignore`, `synth.py` params keys | venv + pyscipopt, mip, highspy, geopandas, shapely, pyogrio, pandas | S1–S7 bit-identical (TAIL note procedure) | U0b |
| **U1a** | `contig_methods/{__init__,base}.py`, `tests/test_base.py`, `contig_methods/fake.py` | C.1 contract | validator negative cases; fake method hits every status | U0c |
| **U1b** | `instances.py`, `contiguity_bench.py`, `tests/test_instances.py` | U1a → tiers, jobs, rows, summary | `select_pairs` reproduces all C*.json; `--dry-run` counts; full S0 with `brute` | U1a |
| **U2** | `contig_methods/{current,brute,bounds}.py` + 3 tests | U1a → three methods | brute == naive on n≤10; bound ordering `frac ≥ nash ≥ OPT` on T0; `current.LB ≤ OPT`, equal iff `opt_has_ratio_roots`; named failures yield `time_limit/iteration_limit` rows with UB + last iterate | U1a |
| **U3** | `tools/twin_export/**` | C.2 → stats, twin, audit | end-to-end on a stand-in (`synth.make_instance(n=5000, n_rep=90)` with fake ZCTA ids); `twin_check.pass`; k-anon guard trips on a planted leak; vendored-code sync test | — |
| **U4** | `battery/code/twin.py`, `tests/test_twin.py`, `data/zcta_adjacency.npz` | C.3 → loader, cache, `twin_pairs` | reproducible adjacency build; loads U3 stand-in; `edge_diff` detects a perturbed edge list | U0c |
| **U5** | `code/synth.py` (exclusive in wave), `tests/test_synth_compat.py` | C.3 → calibrated generator | compat test full precision; knobs off ⇒ bit-identical; `p_active` instance validates | U0c |
| **U6** (main) | `instances.py` T3 block, presets | U1b+U4+U5 → T3/T4 | `--dry-run --tiers T3` ≈ 22 instances; `current` on smallest T3a pair | U1b, U4, U5 |
| **U7** gfx | `code/gfx/**`, `tests/test_gfx.py` | Part D → style, primitives, producers | every producer renders from a fixture JSON/jsonl in < 10 s; n=30k map renders in < 60 s with no seam haze; text-overlap lint passes; old scripts untouched | U1a (row/instance schemas) |
| **W4–W8** | one `contig_methods/<name>.py` + one test each | TEST_PLAN §7 acceptance, **at ρ=0** | as §7 | U1a + U2 |
| **W9a** | `contig_methods/loop_v2.py` (G1 in-out λ=0.5, G2 min vertex-cut separators, scale-adaptive seeds; `districting.py` untouched), `base.lexi_perimeter`, `tests/test_loop_v2.py` | U1a → `current_inout` control at ρ=0; lexi post-pass | B.17: certifies at ρ=0 on every T1 pair `current` certifies at ρ=2e-3; iteration count vs `current` on C9 pairs; lexi never lowers `LB` | U1a + U2 |
| **W11** | `battery/code/travel_cost.py` (bases from seeds, `d_a/d_b` by hops and km, κ grid, κ* search), `tests/test_travel_cost.py`, `gfx/producers/kappa_sweep.py`, `research/contiguity/TRAVEL_COST.md` (main session) | U1a utilities + U5/U4 seeds → κ experiment rows (`kappa` column in `rows.jsonl`) | on T1+T3: κ* per pair where free Nash reaches `excess_pieces==0`; welfare shift (g_a, g_b, product) vs. hard-contiguity κ=0; free-vs-contiguous agreement at κ*; all rows validate; `twin_export` emits territory-radius aggregates | U1a, U5 (S8_twin seeds), U4 (twin seeds) |

Critical path: U0a → U0b → U0c → U1a → U1b → S0. Long pole for T3: U3 → work-machine run + ★ audit → U4 → U6.

---

## Part D — Graphics: from-scratch library and the common figure set (U7)

### What exists (survey 2026-08-28) and why it is replaced, not extended

- `battery/code/mapviz.py` is the only shared library (Voronoi cells → `PolyCollection`, `MAP_RC`); it works but assumes the unit square (`pad=0.035` absolute, `mapviz.py:116`), hardcodes seam widths (`:156`, `:198`) that turn into haze at n≈30k, and has a `len(P)<4` return-shape bug (`:123-126`).
- Everything else is re-implemented per script: firm-A/B colours differ **within one figure** (`case_pipeline.py:170-171` green vs `:196-197` red) and across files (`#2166ac/#b2182b` vs `#4878cf/#d65f5f`); dpi is 150/200/300 across the five paper-width figures; `mkfig_census.py:9-12` copies `MAP_RC` by hand and its panel c is hand-transcribed literals (`:45-52`); `mkfig_zip50.py:265-267, :306-313` draw one artist per edge/ridge (fails at scale).
- `figures/zip50_distributions.png` has **no producer script anywhere in git history**; the other three paper figures come from `mkfig_zip50.py`. `census_stress.png` and all `battery/figures/*.png` are unused by the paper.
- **Old scripts stay frozen** (`mkfig_zip50.py`, `case_pipeline.make_figure`, `c8_rho_sweep.py`, `mkfig_census.py`, `mapviz.py`) — they remain the byte-identity anchor. The new library is for all new outputs; porting the paper figures is a later, separate decision.

### Library layout — `code/gfx/` (importable as `gfx`; matplotlib + numpy + scipy only)

```
gfx/style.py      PALETTE (A="#2166ac", B="#b2182b", neutral="#4d4d4d", unsolved=(.9,.9,.9), status colours,
                  method colours = tab10 by REGISTRY order, sequential cmaps: u_a Blues, u_b Reds, M YlOrBr),
                  RC (MAP_RC + figure.titlesize + savefig.dpi=200), FIGSIZE presets (paper_wide=(11,3.7), card=(13,8)),
                  save(fig, path) — single dpi/bbox policy, writes PNG + sidecar .json of the inputs' hash;
                  lint_text_overlap(fig) — the mkfig_census.py:65-69 idea, run by every producer
gfx/geom.py       polys_from_pos(G, pad_frac=0.035) (Voronoi, vectorised clip; pad relative to bbox),
                  polys_from_shapes(gdf) (TIGER polygons for the twin — replaces Voronoi outright),
                  edge_segments(G, pos) → LineCollection input; partition_boundary(polys|edges, side_of) → segments;
                  seam_width(n) → 0.25 for n≤500, →0 at n≥5000; auto aspect (equal-area xy assumed; raise on lon/lat)
gfx/maps.py       choropleth(ax, polys, color_of, legend), heatmap(ax, polys, values, cmap, vmin/vmax, cbar),
                  boundary(ax, segments), adjacency(ax, segments), seeds(ax, pos) (metro/rep stars scaled to n)
gfx/charts.py     grouped_bars(ax, labels, series: dict), cert_table(ax, header, rows), sweep_curve(ax, x, y, band),
                  gap_vs_time(ax, traces: dict[method → [(t,LB,UB)]], cap), ecdf(ax, values_by_method),
                  status_grid(ax, methods × instances, status), heat_matrix(ax, rows, cols, values), frontier(ax, pts, labels)
                  — annotation dodge is automatic (adjust by bbox), never hand offsets
gfx/producers/    one CLI per figure family, input = JSON/jsonl only, never a live solve:
    instance_card.py   ← InstanceSpec + rows      run_summary.py ← rows.jsonl + instances.csv + summary.csv
    method_trace.py    ← rows (trace field)       twin_audit.py  ← twin_stats.json (+ twin_check, audit blocks)
    twin_map.py        ← twin_instance.json.gz    calib_compare.py ← S8_twin vs S1 marginals
tests/test_gfx.py  fixtures under tests/fixtures/gfx/ (a T0 pair, a 30-row rows.jsonl, a stand-in twin_stats)
```

Rules: every figure is reproducible from files on disk (`python -m gfx.producers.<name> <inputs> --out <png>`); producers never import solvers; palette and dpi come only from `style.py`; A is always blue, B always red, everywhere; per-rep colours use a fixed 20-colour cycle with a warning past 20; every producer calls `lint_text_overlap`.

### Common figure set — what each piece produces, and where

| Piece | Figure (producer) | Panels | Consumed at |
|---|---|---|---|
| Instance (any tier, any pair) | **instance card** (`instance_card`) | pre-merger A/B territories · free-Nash map · best contiguous incumbent (grey = unsolved) · u_a/u_b heatmaps on a shared scale · covariate box (n, components, articulation pts, active frac, Gini, block-tree path?) | U1b acceptance; every named failure; T3 largest pairs |
| Method × instance | **trace** (`method_trace`) | gap-vs-time (LB/UB in nats, cap line) · cuts/tangents per round · pieces per round | W4–W8 acceptance; named-failure deep dives |
| Benchmark run (`run_id`) | **run summary** (`run_summary`) | certified share per method×tier (bars) · time-to-certificate ECDF · gap@cap box per method · named-failure status grid (6 × methods) · mechanism matrix (method × (a)–(d), share certified) · cost-of-contiguity vs. articulation points / active frac (scatter) | ★3 stage gates; `RESULTS.md`; paper §5 table source |
| ρ policy | **ρ frontier** (`run_summary --rho`) | product vs perimeter per method with ρ labels (C8 pattern, auto-dodged) | S2 review |
| Twin export (work machine + here) | **twin audit** (`twin_audit`) | fitted-vs-empirical marginals (quantile plots from `coarse_cdf`, lognormal vs dPlN overlays) · share-by-decile curves with bands · Moran's I / hop-correlation bars · individual-vs-neighbourhood correlation bars (the privacy sign-off panel) · census pair-size histogram real vs twin (from `twin_check`) | ★ privacy audit; `battery/data/README.md` |
| Twin instance | **twin map** (`twin_map`) | national M heatmap on TIGER polygons · rep territories A and B · a 400–800-zip pair zoomed with adjacency | U4 acceptance; T3 documentation |
| Synth calibration | **calibration compare** (`calib_compare`) | S1 vs S8_twin vs twin: M/A/B marginals, active frac, corr, headroom slack | U5 acceptance |
| Paper (later, separate decision) | port of the four §5–§7 figures + the missing `zip50_distributions` producer | — | W10 |

Scale rules baked into `geom.py`: `LineCollection` for edges/boundaries; seams off above 5k cells; marker sizes scale with `1/sqrt(n)`; TIGER polygons used directly for the twin (no Voronoi); positions assumed equal-area projected (`twin.load_twin` supplies `pos` in LAEA, rescaled to [0,1]²).

---

## Part E — Model assignment per unit

| Unit / task | Model | Why |
|---|---|---|
| Coordination, merges, ★ reviews, `base.py` contract (U1a), `districting.py` hygiene (U0b), theory items (B.13 two-sided E1 proof, C.0 contract decisions), `RESULTS.md` synthesis, paper §5 (W10) | **Fable 5** (this session; `subagent_type: "fork"` when a unit needs the full conversation context, e.g. U1a) | Contract and theory decisions propagate to every other unit; correctness over cost. |
| W6 SCIP single tree (Conshdlr + A′), W4 flow + PWL log, U3 twin export (MLE fits, privacy audit), U5 synth calibration, U1b tiers + bench | **Opus 5** | Real design freedom and subtle numerics (solver callbacks, dPlN MLE, draw-order preservation); benefit from strong reasoning, not full context. |
| U2 current/brute/bounds, U4 TIGER loader, U7 gfx, W5 warm starts, W7 CBC tree (mirrors W6's design), W8 prep E1/E3, W9a loop_v2 + lexi post-pass, all `tests/*`, `tools/twin_export` stand-in run | **Sonnet 5** | Fully specified by the plan or by a sibling's design; implementation-heavy, low ambiguity. |
| W11 travel-cost κ: design (utility change, κ* definition, what "emergence" means on a discrete graph, sign-off memo) | **Fable 5 fork** for design; **Opus 5** for build + runs | Touches the settled utility model; the memo goes to distribution. |
| Explore / literature legs, grep sweeps, doc syncing (`OPEN_QUESTIONS.md` closures) | **Sonnet 5** (Explore agent) | Cheap, read-only. |
| S1 screening fan-out | **Workflow** script; workers are Bash jobs, not model calls | Deterministic compute; no model needed per job. |
| Haiku 4.5 | not used | No unit is small enough to trade accuracy for cost. |

Plan-type subagents at ★1 use Opus 5, except W6 and U1a which use a Fable fork.

---

## Part F — Who plans: own plan step vs. work from this plan

| Mode | Units | Mechanics |
|---|---|---|
| **Work from this plan** (no own planning; brief = the relevant Part C/D section verbatim + files owned + acceptance test) | U0a, U0b, U0c, U1a, U2, U4, U7, W5, W8, W9a, all tests | ★0 brief → build (worktree, `maxTurns`) → verify → ★2 diff. The subagent may deviate only by stopping and reporting; the main session decides. |
| **Own plan step first** (Plan-type subagent returns steps + risks; reviewed at ★1 before any build agent is spawned) | U1b, U3, U5, W4, W6, W7, **W11** | These have genuine design choices the plan leaves open (root selection in flow; PWL encoding; Conshdlr vs native log; MLE start/bounds; `rho_books` bisection; job scheduling; for W11: distance metric, κ grid, κ* definition, negative-utility handling in the OA). The approved plan becomes the build brief. |
| **Main session, no subagent** | merges, `requirements.txt`, `districting.py`, `CLAUDE.md`, `research/contiguity/*.md`, U6 | Serial-only files. |

Every build brief carries the same five lines: files you own; files you must not touch; the contract you consume (`base.py` path); your acceptance command; "never write under `battery/figures/`; commit on your branch; stop and report if the plan is wrong rather than improvising".

---

## Part G — Generator v2 and regional real-geography instances (U5 expanded, U8 new, W12 new)

### G.1 What the current generator cannot produce (`code/synth.py:100-206`)

| Gap | Cause | Consequence |
|---|---|---|
| Dense components by design (1A×2B, 2A×1B) | only incidental: S2's extra B seed, `sliver` flips (`:127-137`) | C2 is the only dense case; no controlled experiment |
| Zero-value zips | `_share` floor .02 (`:156`), density floor .20 (`:121`), `_dpln` > 0 | mechanism (d) untestable; `active_frac ≡ 1` |
| Strong metro concentration | equal-weight metros, 70 % clustered, floor .20; only the noise tail is heavy | Gini/top-1 % share far below what real sales show |
| Real geography / states | Delaunay on random points; `n_states` = random Voronoi labels | `respect_state` never meets a real border |

### G.2 New knobs (all default-off, drawn from `rng2 = default_rng([seed, 7919])` → S1–S7 bit-identical)

| knob | effect | target statistic (calibrated from twin_stats when it exists, else literature/public data) |
|---|---|---|
| `split_b: int` / `split_a: int` | place an extra B (A) seed inside k randomly chosen A (B) territories → designed 1A×2B / 2A×1B components; `split_pos ∈ {"core","edge"}` decides whether the extra rep sits on the metro core or the periphery | census dense share, pair-size ratio inside the component |
| `activity: dict(p_glue, p_untapped, slope, smooth_k)` | three states per zip from a graph-smoothed field with logistic-in-log-density probabilities: **glue** `A=B=M=0`, **untapped** `M>0, A=B=0`, **active** | `active_frac`, `active_pieces` (components of the active subgraph), share of M on untapped zips |
| `metro_weights="zipf", zipf_s=1.0` | metro m gets cluster share and density mass ∝ 1/m^s | share of M in largest metro, top-3 metros |
| `gamma=1.0` | `M ∝ dens^γ` before noise (superlinear urban scaling, γ∈[1.1,1.3]) | Gini(M), top-1 %/top-10 % share |
| `core_tail=(alpha, frac)` | Pareto core mixed into the density field for the top `frac` of zips | top-1 % share, Moran's I |
| `density_field=None` | external per-node density (public population × income on real geography) replaces the Gaussian mixture | — |
| `assign="graph"`, `b_hops` | multi-source BFS Voronoi on the adjacency graph (needed for real geography) | zips-per-rep, pieces-per-rep |

New scenarios: `S8_twin` (calibrated, Part C.3), `S9_dense` (`split_b=2, split_a=1`), `S10_glue` (`activity=dict(p_glue=.45, p_untapped=.15)`), `S11_metro` (`metro_weights="zipf", gamma=1.2, core_tail=(1.5,.02)`), `S12_regional` (G.3). Each gets a battery case (C11–C14) run through the *harness*, not `run_battery.py`.

### G.3 Regional real-geography instances (U8 — no work-machine dependency)

`battery/code/regions.py`: `REGIONS = {"R1_NY": [NY,NJ,CT,PA,VT,MA], "R2_CA": [CA,OR,NV,AZ], "R3_TX": [TX], "R3b_TX+": [TX,NM,OK,AR,LA]}`. Inputs, all public: TIGER ZCTA5 2020 (U4), the Census **ZCTA→state relationship file** (straddlers → largest-share state; `multi_state` kept), 2020 Decennial ZCTA population and ACS median household income (Census API or downloaded tables, cached under `data/public/`). Build: filter ZCTAs to the region → Rook adjacency within region → LAEA `pos` → `density_field = (pop·income)^γ` → `make_instance(..., density_field=…, assign="graph", activity=…)` with `n_rep_a=n_rep_b` = round(90 × region share of national density). Real state lines feed `respect_state`. Approx sizes: R1 ≈ 5,300 ZCTAs, R2 ≈ 2,800, R3 ≈ 1,900. Tier **T3c** = regional pairs (bands 200/400/800 + largest), lognormal and heavy-tail variants; T4 gains regional `--respect-state` runs where the NY/NJ/CT straddle is the realistic C5 case. Priority order: R1, R2, R3.

### G.4 Dense components: component-level MNW (W12) — recommendation

In any dense component every zip has exactly two candidate owners (its legacy A-rep, its legacy B-rep), so the decision stays **one binary per zip**; the objective becomes `Σ_i log g_i` over every rep in the component (3 terms for 1A×2B). Still convex, still OA-exact, EF1 (Caragiannis et al.) is stated for n agents; contiguity is per rep. Replaces the bilateral-on-overlap illustration (`case_pipeline.py:57-63`) and is the concrete form of `CLAUDE.md` Next Step 3 ("leximin over dense components") — **recommend MNW over leximin** (Pareto-efficient, same machinery; leximin loses efficiency and hits Trap 2). Open for the user: MNW vs leximin at the component level; whether a rep's bundle may include zips outside its legacy overlap (default no). Harness support: `base.utilities` returns per-rep `u`, `Result.to_owner: dict[node → rep]`, validators per rep; `brute.py` extended to 2-choice-per-zip enumeration. Tested on `S9_dense` and C2.

### G.5 Units added

| unit | owns | consumes → produces | acceptance | needs |
|---|---|---|---|---|
| **U5** (expanded) | `code/synth.py` knobs in G.2, `SCENARIOS` S8–S12, `calibrate`, `tests/test_synth_compat.py` | — | knobs off ⇒ bit-identical C1–C9; each scenario validates; `S10_glue` reaches target `active_frac` ± .02; `S11_metro` Gini within ± .05 of target | U0c |
| **U8** regions | `battery/code/regions.py`, `data/public/` fetchers, `tests/test_regions.py` | U4 adjacency + public tables → T3c specs | R1/R2/R3 build reproducibly; state counts match the relationship file; `respect_state` deletes the expected cross-state edge share | U4, U5 |
| **W12** component MNW | `contig_methods/base.py` per-rep extension (main session), `component.py` wrapper mapping a dense component onto the chosen engine, `brute.py` 2-choice extension, `tests/test_component.py` | U1a, winner of S1 → component rows | brute match on ≤20-zip dense components; per-rep contiguity; product ≥ every bilateral illustration's product on C2 | S1 finalists |

Models: U5/U8 Opus 5 (design freedom in the activity/concentration models), W12 Fable fork for the contract extension then Opus 5 build. Planning: U5, U8, W12 own plan step (★1).

---

## Verification (end-to-end)

1. `.venv/bin/python3 battery/code/tests/run_all.py` green after every merge; `TD_SLOW=1` adds the zip50 anchor (2 min) whenever `districting/territory/synth` changed.
2. `contiguity_bench.py --stage S0 --methods current,brute --dry-run` then real run: every T0 row has `brute` optimal, `current.LB ≤ brute.OPT`, validators pass, six named failures produce rows with UB and last iterate; `battery/figures/` untouched (`git status`).
3. `--no-rescale` on T0/T1: free-Nash `to_a` identical; report `current` differences (G4 decision).
3b. ρ=0 headline: every method's S1 rows at ρ=0; `current` at ρ=0 vs ρ=2e-3 shows the thrash (B.17), `current_inout` (W9a) removes it; `--lexi` perimeters ≤ raw perimeters with `LB` unchanged.
3c. κ experiment (W11): κ-sweep rows validate; `kappa_sweep` figure shows κ* per pair and the welfare shift; memo `TRAVEL_COST.md` states what adoption would require from distribution.
3d. Generator v2 (Part G): `test_synth_compat` green with every new knob off; `S10_glue` gives `active_frac` on target and `active_pieces > 1`; `S11_metro` Gini/top-1 % on target; R1/R2/R3 build from public data with real state lines and the expected cross-state edge share; W12 matches brute force on small dense components and dominates the bilateral illustration on C2.
4. Twin: run `twin_export` on the stand-in here, then on the work machine; user reviews `twin_audit.json` **and the `twin_audit` figure** (★); here `load_twin` + `edge_diff` Jaccard ≥ 0.999; `twin_check.pass`; `test_synth_compat` green after U5.
4b. Graphics: `tests/test_gfx.py` renders every producer from fixtures; `instance_card` on the six named failures and `twin_map` on the loaded twin (n≈33k, < 60 s, no haze); `mkfig_zip50.py` anchor still byte-identical (old scripts untouched).
5. S1 screening via Workflow → `RESULTS.md` table (certified %, median t-to-cert, gap@60 s, named failures k/6, mechanism matrix) → ★ finalists → S2/S3/S4 → update `CLAUDE.md` Trap 11, `OPEN_QUESTIONS.md` §A/§B closures, paper §5.
