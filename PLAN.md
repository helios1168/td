# Track: full-problem

Handoff plan for a fresh orchestrator session. Written 2026-09-10 from a planning session that
read the codebase, ran three explore agents and one Plan agent, and settled the design with the
user. Everything an orchestrator needs is here; the planning session's chat is not required.

## Goal

Extend the methodology, models and Streamlit app from one channel (national) to the full CWIFI
business problem: $48B across national, WH and FI on CONUS, each carved into contiguous districts
of about $1B (floor $800MM, cap $1.2B), one wholesaler per district and at most one district per
wholesaler, channels designed in priority order national, WH, FI, the residual called "other".
The decision that is new is the channel structure per state (keep three, merge WH and FI, drop
national). This track delivers the formulation (`docs/FULL_PROBLEM.md`), the level-0 plan solver,
the projection tool that lets every existing driver run per bundle, and the driver; the app
follows once solve times are known.

## Next step

Wave 2 in flight: integration agent closing seams; code-verify R1 (level0), R2 (channels,
stage2_state), R3 (full_plan) writing under `tools/verify/U14-fullprob/`; two solves running
detached (joint route with the geo driver on the synthetic instance; route-S regression
expecting 8 splits, output `battery/results/full_problem/seq_regression`). Then: commit I's
seams, place the three code-verify verdicts in `docs/units/U14-fullprob.md`, read the timing
table, decide route S versus J (the user's call), wave 3.

## Done

- 2026-09-10: worktree created and locked, branch `worktree-full-problem` from `main` `7325737`.
  Design settled (decisions log below). This file written.
- 2026-09-10: wave 1 landed, one commit per agent: bookkeeping `313380c`, loader `713cc63`,
  doc `82164cb`, channels `0373964`, stage 2 at state grain `260dc70`, exporter `fdbafa6`,
  math-verify VERIFIED `a59ba26`, level 0 `ea665cd`, driver `9956e9d`. Synthetic instance at
  `battery/results/full_problem/synthetic_v2.json.gz` (national 8481.8, wh 2953.6, fi 2962.4).
  Level-0 joint model on it: 95 slots, 34,390 variables, 64,689 rows. Exporter handed to the
  user for the work machine (README has the command; `--rep-ids` checks the national shares).

## Decisions needed

Open ★ items in §8 of the formulation: WHFI⁺ bundle on or off; rep pool size versus 48 to 60
districts and whether reps carry a channel tag; η and the centre-free tie-break; whether a state
may split geographically across plans. Route S versus J is decided from the timing table after wave 2.

## Files owned / forbidden

Owned: `PLAN.md`, `docs/FULL_PROBLEM.md`, `docs/units/U14-fullprob.md`, `td/channels.py`,
`td/stage2_state.py`, `td/solvers/level0.py`, `tools/full_plan.py`, `tools/verify/U14-fullprob/`,
`tests/test_instance_v2.py`, `tests/test_instance_export_v2.py`, `tests/test_channels.py`,
`tests/test_stage2_state.py`, `tests/test_level0.py`, `tests/test_full_plan_cli.py`; small
edits to `td/instance.py`, `td/model.py`, `td/channel.py`, `td/solvers/state_splits.py`,
`td/solvers/milp_engines.py`, `tools/instance_export/export_instance.py`,
`.claude/doc-owners.txt`, `docs/CODE_MAP.md`. Forbidden: `docs/foundations/`, `app/` until wave
3, `battery/figures/`, `STATE.md` (hub state; `/state` only at merge).

---

# Orchestrator context

## Environment and conventions that bite

- Worktree: `/Users/ntlee/projects/td/.claude/worktrees/full-problem`, branch
  `worktree-full-problem`, locked. Enter with `EnterWorktree(path=...)`, never `EnterWorktree(name=...)`.
- Python: the hub's `/Users/ntlee/projects/td/.venv/bin/python3`; the worktree has no `.venv`.
  Tests: `.venv/bin/python3 tests/run_all.py` run from the worktree root with the hub's python
  (546 pass, 0 fail on `main` at 2026-09-09). Background solver runs use `python3 -u`.
- Serena: pass absolute worktree paths (relative paths resolve against the hub).
- Confidential data is gitignored: `instance_descaled_v2_conus.json.gz` and `data/` live in the
  hub root; copy or reference by absolute path. `battery/results/` is gitignored.
- Docs hook: a Write to any `docs/*.md` not listed in `.claude/doc-owners.txt` is denied, and
  `tests/test_docs_owners.py` asserts every `docs/**/*.md` outside `docs/foundations/` matches a
  line. Add the owners line before writing the doc. `docs/foundations/` is frozen; `/frame` and
  `/approaches` write there by default, so do not run them.
- `docs/CODE_MAP.md ## Files` needs an owner row for each new doc.
- Never merge or fast-forward into `main` without asking. Commit on the track; the last commit
  before merge deletes this `PLAN.md`.
- Agents in one worktree share one git index: agents never commit; the orchestrator commits
  after each report. File sets per agent are disjoint (list below).
- Traps that apply here: 12 (`mip_rel_gap=0.0` for a certificate), 13 (component-wise
  separator cuts), 14 (SCIP dual reductions off for lazily separated models), 18 (HiGHS thread
  pool is process-global: one `threads` value per process; portfolio parent uses 2), 19 (never
  strip the objective to "just find a feasible point"), 20 (unavailable reps are excluded from
  candidacy, never released), 22 (gazetteer vintage is part of a result).
- Anti-slop (global CLAUDE.md §10) applies to the doc, commits and code comments: no em-dashes,
  no slop vocabulary, plain words.

## The business problem, in the owner's words (for the doc's §1)

We need to design territories on the CONUS map across multiple channels. So far we have only
worked with one channel. The channels are not fully designed yet and we want them to come out of
the methodology developed so far. Roughly three strategies, each of 1 to 4 channels. The most
challenging strategy is Combined WIFI, CWIFI, with $48B of opportunity across national, WH, FI
and whatever is left, called CWIFI other. Each channel is carved into contiguous districts of
roughly equal opportunity, target about $1B, floor $800MM. Priority order of design: national
first (the channel and data used so far), then WH, then FI, then other. The complexity comes from
the existing reps and their current territories and how we staff them in a weakly optimal sense;
every wholesaler serves at most one district in one channel. Example: Arizona has $836MM of CWIFI
opportunity, split national $541MM, WH $152MM, FI $143MM. Do we keep three channels in Arizona,
each (Arizona, channel) pair grouped with other states' same-channel pairs to reach $800MM; or
merge WH and FI into one; or go with WH and FI and drop national? This depends on the candidate
wholesalers with sales in Arizona across channels and on every other state's decision.

## Decisions log (2026-09-10, all from the user)

1. "Other" is the residual: cells left after national, WH and FI districts are cut. A fourth
   channel exists iff the catch-all pass over the residual produces at least one district.
2. Dropped national falls back into WH and FI: national is the two largest firms, one WH and
   one FI, and its opportunity reverts with no loss. At most three served channels per state,
   never four.
3. The fallback ratio is the zip's own WH:FI mass ratio (the data carries national as one row;
   no firm split). Zip with national mass and no WH or FI mass: state ratio, then 50/50, reported.
4. Merge drivers: explore rep books (route R) and a geographic extent cap (route G) in parallel.
   The "contiguity-type restriction" is an extent cap (max states per district, max centroid
   distance), not sold-zip contiguity per channel.
5. Priority reading: explore sequential (route S) and lexicographic joint (route J) in parallel;
   choose by how fast J solves.
6. A channel need not cover the whole map; states may be absent from a channel; districts must
   be contiguous at the channel level (a state with no B cannot bridge two B districts).
7. Upper band U = $1.2B (1.2τ).
8. Pass 1 of route J counts national mass in pure national slots only.
9. Catch-all pass on.
10. Data: the expanded instance arrives in the v2 format long by (zip, channel) with
    `current_channel ∈ {national, wh, fi}`; the national rows are exactly today's data. The
    exporter must be updated (below).
11. Execution optimised for wall-clock; tokens unconstrained; Opus or Fable executors where
    first-shot success saves time.
12. (later the same day) The three-channel extract is the new source of truth and the v2
    single-channel instance is discarded: national opportunity values may differ from v2, so
    κ, τ and the committed k = 18 map are recomputed on the new file, and the exporter's
    `--rep-ids` check against the previous export is not used. The extract is one combined
    sales plus opportunity file; a cell's opportunity is carried once across its rows
    (duplicates at 0), so the exporter sums opportunity within a (zip, channel) cell.
    Reported totals: national $17.6B, all three channels $48B.

## What the codebase has (facts from the explore agents, with anchors)

- Utilities: `u_i(z) = c1·S_i(z) + c2·(T_z − S_i(z)) + c_free·S_free(z) + λ·M_z`, `c1 = 1−λ`,
  `c2 = θ(1−λ)`, `c_free ∈ {c2, c1, λ}` by `filler_capture` (`td/model.py:135,146-149`;
  duplicated at `td/channel.py:268-271`). θ = 0.40, λ = 0.30.
- Stage 1: Hess/Lloyd draw on `(z, M_z, q_z)` only, books never enter (`td/solvers/centers.py`,
  `tools/run_draw.py`). Lemma 6: one scalar mass per district gives the transportation
  structure, at most k−1 split zips; a second balancing attribute breaks it (`docs/MODEL.md:446-450`).
- Level 1: minimum-splits MILP on 49 states (`td/solvers/state_splits.py`): `SplitProblem`
  (94-130, blocks z, y, r, f in row-major (s, j)), `build_milp` rows: place `Σ_j y_sj = 1` (231),
  `yz` (233), `yz_lo` η (238), band (244), root (247), `rz` (249), flow_tail/head (259-265), net
  (267-273), caps (275-280), anchors as `var_lb` on z (285-288). `bound_z` (139). `balance_pass`
  (two lexicographic LPs, pin at `v(1+1e-9)+1e-12`, 822-841). `eps_lexicographic` (756-770).
  `_solve_scipy` decode (735-747) duplicated in `td/solvers/milp_engines.py` `_decode_zy`
  (119-136); engine seam `_highs_lp` (358-378), `_scip_solve` (468-506); `with_cutoff`,
  `fix_roots`, `_clone` via `dataclasses.replace` (152-196). Portfolio strategy in
  `tools/state_splits.py` (484-706); driver shell `_main`, `Timings`, `params.json` (581-600),
  `_write_failure` (447-464, key contract asserted at `tests/test_state_splits_cli.py:78-96`),
  `write_state_shares` (377-392), `_state_masses_and_moments` and D_sj (396-422). `realise`
  raises when a state touches no district (`td/solvers/state_splits.py:945-946`).
  Sizes today at k = 18: 6,498 variables, 1,764 binaries, 11,317 rows; certifies in 49 s under
  the portfolio; anchored δ = 5% gives 8 splits (CA 5 districts, NY 3, TX 2, FL 2).
- Stage 2: `channel.gain_matrix` (`td/channel.py:252-285`, every rep on every district),
  `channel.match` (288-312, Hungarian on −log g, raises if any g ≤ 0), `channel.stage2` (315-333),
  `score_draws` (336-350). `tools/staff.py`: candidacy mask and `held` set (114-131, 183-196).
- Instance: `td_instance_descaled/1`, loader `td/instance.py:80-127` (`FORMAT` at 50), nodes
  `z, m_rel, share {rep: s_i(z)}, share_free, state`; edges; `firm`; `meta`. `S_i(z) = share·m_rel`.
  Exporter `tools/instance_export/export_instance.py`: `Instance` (144-155), `build` (157-348,
  sales join 225-251), `guard` (524-553), `write` (559-588), `rsig` rounding (137-140). Inputs
  `--sales zip_code,rep_id,firm,sales`, `--opportunity zip_code,M`, `--graph`, `--states`.
  Live instance `instance_descaled_v2_conus.json.gz`: 3,713 zips, 113 reps, mass 8,481.8,
  τ = 471.21 at k = 18 (κ = median positive M of the national data).
- State list order: `tools/borders_report.py:67-72`; homes `ctx.home` (86-102); state rook graph
  `td/geo.state_rook` (`td/geo.py:243-267`, polygons available for centroids).
- Tests to copy from: `tests/test_channel.py` (fixtures 23-31), `tests/test_state_splits.py`
  (`path_toy`, `EDGES` 30-52, contiguity by enumeration 106-125), `tests/test_instance.py`
  (`_exporter` importlib pattern 30-35), `tests/test_milp_engines.py` (engine gating 20-31),
  `tests/test_state_splits_cli.py` (argparse defaults 100-110, end to end with `state_rook`
  monkeypatched 151-210), `tests/test_borders_report.py` (real-file gate 28-30).
- App: never imports `td`; drives drivers by subprocess (`app/steps.py`, `app/runner.py`);
  runs keyed scenario → member `slug_k<k>_d<delta%>` → run dir (`app/store.py:41-45`); nothing
  keys on a channel. `docs/APP.md` documents schemas.

---

# The formulation (content of `docs/FULL_PROBLEM.md`)

Sections follow the `/frame` skeleton where it fits: no method words in §1.

### 0. Resume
Date, branch, what is settled (decisions log), what is open (★ in §8).

### 1. The business problem, in the owner's words
The statement above, condensed.

### 2. Cells and data
- Z zips (CONUS, 3,713), states s(z), proximity graph on Z, state rook graph G_S (49 nodes,
  107 edges).
- Channels in the file: {national, wh, fi}. Fine labels C = {N_WH, N_FI, WH, FI} are accounting
  only: N_WH(z) = N(z)·WH(z)/(WH(z)+FI(z)), N_FI likewise, applied to mass, books and filler;
  fallback per decision 3.
- Cell (z,c): mass M_{z,c}, rep book S_i(z,c), filler S_free(z,c), T_{z,c} = Σ_i S_i(z,c). Every
  quantity the utility reads is additive over cells.
- Exporter and loader: nodes keyed by (zip, channel) with a `channel` column, format
  `td_instance_descaled/2`; one κ for the file pinned to the national median so national
  `m_rel`, τ = 471.21 and k = 18 carry over unchanged; rep surrogate ids assigned once over the
  whole file and mapped to the v2 ids; both the sales and the opportunity tables carry a channel
  column (assumed per zip); graph, states and geo unchanged; format 1 loads as the one channel
  `national`. Until the real file lands, a deterministic synthetic split of the v2 CONUS instance
  stands in (hash of `seed:zip` via hashlib, never `hash()`; same fractions for M, every S_i and
  S_free at a zip, so per-cell headroom holds exactly).

### 3. Districts, bundles, plans, and the joint problem F
- Bundle: a served channel is a set B ⊆ C. Allowed family 𝔅, each on a switch:
  N = {N_WH, N_FI}, WH = {WH}, FI = {FI}, WH⁺ = {WH, N_WH}, FI⁺ = {FI, N_FI}, WHFI = {WH, FI},
  WHFI⁺ = {WH, FI, N_WH, N_FI} (off by default, ★B).
- Channel plan π(z): pairwise disjoint bundles covering part of C. The three business options
  per state are {N, WH, FI}, {N, WHFI}, {WH⁺, FI⁺}. Cells outside ∪π(z) are the residual.
- District j = (A_j, B_j): A_j ⊆ Z_B = {z : B ∈ π(z)}, connected in the proximity graph induced
  on Z_B, B_j ∈ 𝔅. It owns the cells A_j × B_j (product form: every zip in the district carries
  every channel of the bundle).
- τ = $1B, L = 0.8τ, U = 1.2τ.

      cover:      each cell in at most one district; uncovered = other
      band:       L ≤ M_j = Σ_{z∈A_j} Σ_{c∈B_j} M_{z,c} ≤ U
      reps:       σ injective from districts to reps, every district staffed
      gain:       g_i(j) = Σ_{z∈A_j} Σ_{c∈B_j} u_i(z,c),
                  u_i(z,c) = c1·S_i(z,c) + c2·(T_{z,c} − S_i(z,c)) + c_free·S_free(z,c) + λ·M_{z,c}
      objective:  max Σ_j log g_{σ(j)}(j)        (Nash over reps, stage 2 as today)

  F is today's problem with Z replaced by Z × C and a bundle on each district. The two-stage
  business constraint stays: the draw sees masses only, reps enter at stage 2.

### 4. Decomposition (Proposition; proof in the doc; math-verify artifact under `tools/verify/U14-fullprob/`)
Fix π. Then the districts of bundle B partition Z_B; with M^B_z = Σ_{c∈B} M_{z,c},
S^B_i(z) = Σ_{c∈B} S_i(z,c), T^B, S^B_free, linearity of u gives u^B_i(z) = Σ_{c∈B} u_i(z,c) in
single-channel form. Stage 1 at fixed k_B is Σ_B Σ_{j∈J_B} log M_j, separable by bundle, each
term the current problem on (Z_B, M^B) with Lemma 6's one scalar mass per district intact. Level 1,
level 2 and the gain matrix run unchanged on the projected instance. The only coupling across
bundles is the rep constraint, and stage 2 over the union of districts is one Hungarian
(`channel.match`). Consequence: one projection tool, no new zip-level solver. Flag: a merged WHFI
district must not carry per-channel floors; that is a second balancing attribute and breaks the
transportation structure.

### 5. Level 0: the plan at state × channel granularity
Cells (s,c), 49 × 4 = 196. Slots j ∈ J_B per bundle, K_B = ⌈M^max_B / L⌉ (M^max_B = all mass the
bundle could ever hold), bundle fixed per slot, so no bundle binaries. W_{s,j} = Σ_{c∈B_j} M_{s,c}.

      y_{s,j} ∈ [0,1]    share of s in slot j (all channels of B_j alike)
      z_{s,j} ∈ {0,1}    contact,  η z ≤ y ≤ z ≤ u_j
      u_j ∈ {0,1}        slot used
      cover:   Σ_{j : c∈B_j} y_{s,j} ≤ 1 − prior_{s,c}      ∀ (s,c)
      band:    L u_j ≤ Σ_s W_{s,j} y_{s,j} ≤ U u_j          ∀ j
      flow:    single-commodity flow per slot as level 1, root Σ_s r_{s,j} = u_j
      order:   u_j ≥ u_{j+1}, mass_j ≥ mass_{j+1} inside each J_B (symmetry)
      residual mass per (s,c) reported as other

Size: at about 95 slots (Σ_B K_B ≤ ⌈4·18/0.8⌉ + 7) about 34k variables, 9.4k binaries, 60k rows;
at 150 slots 54k / 15k / 101k. Today: 6,498 / 1,764 / 11,317. Slot count is the lever; the
driver prints it before solving. `build_level0` raises when U is None: without an upper band the
coverage passes build one giant district per bundle and balance is undefined.

### 6. Routes
Priority reading:
- S (sequential): level 0 with slots for N only, fix as prior, then WH and WH⁺ on what remains,
  then FI, FI⁺, WHFI, WHFI⁺. Three solves of a third the size. Regression anchor: N alone with
  cover forced to 1, band 1 ± 0.05, K_N = 18 all used, anchors from the committed homes, D from
  the committed centres must reproduce today's 8 splits.
- J (lexicographic joint): one model, passes in the `balance_pass` pattern (solve, pin value
  with a row at v(1+1e-9)+1e-12, next objective): cover_N (pure national slots only), cover_WH
  (WH and WH⁺ slots), cover_FI (FI and FI⁺), contacts (min splits, `c = 1` on z), compactness
  tie-break (ε·W·D with D from a projected stage-1 draw when available, else contacts only).
  A timed-out pass pins its incumbent and records `certified = false`. The portfolio strategy is
  reusable only for the contacts pass (unit cost on z); coverage passes run direct.

Merge driver (under band and contiguity alone a sparse pure district is always feasible, so a
priority objective never merges anything):
- R (rep books): level 0 generates; per-state moves {keep three, merge WH+FI, drop N} in priority
  order, each a `forbid_bundle` bound set, scored by the state-level stage-2 Nash value (one
  Hungarian on aggregated cells). A move changes contacts, so it cannot be scored with z fixed
  (the forbid bound collides with η z ≤ y); each move is a neighbourhood MILP: z fixed on every
  slot touching neither the moved state nor its rook neighbours, warm-started from the incumbent.
  The score is exact on whole states and a mass-proportional approximation on split ones (level 2
  decides which zips move). No rep term inside the MILP (bilinear; refused for the same reason
  the project refused joint draw+match).
- G (geographic): Σ_s z_{s,j} ≤ n_max per slot and/or z_{s,j} + z_{s',j} ≤ 1 when the state
  centroid distance exceeds Δ. Linear, centre-free. R selects among the (n_max, Δ) grid cells.

Catch-all pass (both routes, last): a bundle over the residual cells, districted where the band
allows; what it cannot cover is unserved. "Four channels" then has a definition: the catch-all
pass used at least one slot.

{S, J} × {R, G} are four drivers over one model. Zip-level realisation runs once for the chosen
plan: project per bundle, level 2 with a residual pseudo-column for uncovered mass (so `realise`
does not raise on a state touching no district and `centers.assign`'s target sum stays exact),
one global stage 2.

### 7. What exists, what is new
Reused: `SplitProblem`, `_block`, flow rows, η rows, `bound_z`, anchors, `with_cutoff`,
`fix_roots`, engine seam, `balance_pass` pattern, `eps_lexicographic`, `channel.gain_matrix`
formula, `channel.match`, `ss.realise`, driver shell of `tools/state_splits.py`. New: v2 loader
and exporter, `td/channels.py`, `td/stage2_state.py`, `td/solvers/level0.py`,
`tools/full_plan.py`, six test modules. One small refactor: `model.coefficients(theta, lam,
filler_capture)` replacing the duplicated c1/c2/c_free block in `td/model.py` and `td/channel.py`.

### 8. Assumptions and ★ decisions
Settled: U = 1.2τ; route G is an extent cap; cover_N counts pure national slots; catch-all on;
fallback ratio per decision 3. Open: ★B WHFI⁺ off, {N, WH} not a bundle. ★C rep pool size versus
48 to 60 districts; whether reps carry a channel tag; stage 2 as built leaves districts unstaffed
if reps < districts. ★D η and the centre-free tie-break. ★E a state may split geographically
across plans (level 0 allows it; per-state purity is one binary per state if refused).

### 9. Numbers to compute first
K_B per bundle and total slots on the synthetic instance; one level-0 solve time per route; the
route-S regression against today's 8 splits; residual mass under each route.

---

# Code plan

## Level-0 mapping onto `state_splits.py` (from the Plan agent, verified against source)

| today | anchor | level 0 |
|---|---|---|
| `SplitProblem` | `state_splits.py:94-130` | `Level0Problem(SplitProblem)`; `k` = K_total; new fields `off_u`, `W (S,K)`, `bundle_of (K,)`, `slots {B: (start, stop)}`, `L`, `U`, `cover_ub (S,C)`, `prior` |
| decode, duplicated | `state_splits.py:735-747`, `milp_engines.py:119-136` | add `SplitProblem.decode_zy(z, y)` holding today's body; `_solve_scipy` and `milp_engines._decode_zy` delegate. `Level0Problem.decode_zy` returns masses `(W*y).sum(0)`, `used`, per-channel `covered`, `contacts`, `splits = Σz − n_state` so `with_cutoff`'s row reads "fewer contacts" |
| `_block`, flow rows | 133-136, 254-273 | copy verbatim, `k` → K |
| place `Σ_j y_sj = 1` | 231 | cover per cell: `Σ_{j: c∈B_j} y_sj ≤ cover_ub[s,c]` |
| `yz`, `yz_lo` | 233-242 | unchanged; add `z_sj ≤ u_j` |
| band | 244-245 | two rows per slot: `Σ_s (W_sj/τ) y_sj − (L/τ) u_j ≥ 0`, `… − (U/τ) u_j ≤ 0` |
| root | 247 | `Σ_s r_sj − u_j = 0` |
| caps | 275-280 | `Σ_s z_sj ≤ n_max` per slot; pairwise `z_sj + z_s'j ≤ 1` for centroid distance > Δ |
| anchors, `bound_z` | 139-157, 285-288 | keep; add `forbid_bundle(problem, s, bundle)` |
| `eps_lexicographic` | 756-770 | same formula on `W` and `D (S,K)`; D zeros when no centres |
| symmetry | anchors from `ctx.home` + `fix_roots` | ordering rows inside each `J_B`; optional anchors and centres from a stage-1 draw on the bundle projection |
| `balance_pass` | 822-841 | `solve_passes`: per pass set `problem.c`, solve warm-started, pin with `append_row`, record `certified = status == 0` |

Variable layout stays four blocks plus `u`; `_decode_x` slices by `off_z, off_y, n_state, k`.

## Interface contract (every agent builds against this; disjoint files)

- `td/instance.py` (A1): `FORMAT_V2 = "td_instance_descaled/2"`; `load_descaled` accepts both;
  on v2, node attrs `M_c: dict[str, float]`, `S_c: dict[rep, dict[str, float]]`,
  `S_free_c: dict[str, float]` over the file's channels, totals `M`, `S`, `S_free`, `cand` as
  today; `Descaled.channels: tuple[str, ...]` (`()` on v1). v2 nodes are long by (zip, channel):
  columns `z, channel, m_rel, share, share_free, state`; `share` is the fraction of that cell's
  `m_rel`.
- `td/channels.py` (B1): `CHANNELS = ("N_WH","N_FI","WH","FI")`, `BUNDLES` as §3;
  `fine_split(d) -> Descaled` (decision 3); `CellTable(state_list, channels, reps, M (S,C),
  S (R,S,C), S_free (S,C))`; `aggregate(d, state_list) -> CellTable`;
  `slot_weights(cells, bundle_of) -> (S,K)`; `project(d, bundle, *, states=None) -> Descaled`
  (format-1 shape, `cand` recomputed, induced edges, `meta["bundle"]`);
  `synthesize_channels(d, *, seed=0) -> Descaled`; `write_v1(d, path)`, `write_v2(d, path)`.
- `td/stage2_state.py` (B2): `Slot(bundle, y: dict[str, float], used)`, `Plan(slots,
  state_list)`; `state_utilities(cells, reps, *, theta, lam, filler_capture) -> (R,S,C)`;
  `state_gain_matrix(cells, plan, ...) -> (g, reps, slot_ids)` over used slots only;
  `state_stage2(cells, plan, ..., criterion="nash", candidacy=False) -> dict` in the shape of
  `channel.stage2`. Also `model.coefficients(theta, lam, filler_capture) -> (c1, c2, c_free)`
  and both call sites.
- `td/solvers/level0.py` (C): as the table; `build_level0(cells, bundles, *, L, U, eta,
  n_max=None, dist_max=None, state_xy=None, prior=None, anchors=None, D=None, eps=None)
  -> Level0Problem`; `Pass(name, c, sense)`; `append_row(problem, name, cols, vals, lo, hi)`;
  `solve_passes(problem, passes, *, engine, strategy, time_limit, threads) -> dict` with
  `passes: [{name, value, certified, status, seconds}]`, `z`, `y`, `u`; `forbid_bundle`.
- `tools/full_plan.py` (D): `instance`, `--route {sequential,joint}`, `--driver {reps,geo}`,
  `--catch-all`, `--k` (τ = M_national/k), `--band-lo 0.8 --band-hi 1.2`, `--bundles`,
  `--priority N,WH,FI`, `--eta`, `--n-max`, `--dist-max`, `--prior PLAN.json`, `--centers`,
  `--incumbency`, `--theta/--lam/--filler-capture` (defaults from `borders_report`),
  `--engine/--strategy/--threads/--time-limit`, `--synthesize`, `--geo-cache`, `--out`.
  Outputs `params.json`; `plan.json` = `{state_list, bundles, slots: [{id, bundle, used, mass,
  contacts, y: {ST: share}}], per_state: {ST: {slot_id: share, residual_by_channel}},
  passes: [...]}`; `staffing.json`; `timings.json`; `failure.json` on `SolveFailure`;
  `projections/<bundle>/instance_descaled.json.gz` and `state_shares.csv`.
- `tools/instance_export/export_instance.py` (A2): `pick(s0, "channel", ...)` beside the
  columns at 167-172; sales join keyed on `(z, rep, channel)`; opportunity rows carry a channel;
  κ pinned to the national median; `--rep-ids v2.json.gz` map; `guard` extended; `write` emits
  v2 when channels are present.

## Wave 1: eight agents in one message, after the bookkeeping commit

Bookkeeping (orchestrator, before launching): add `docs/FULL_PROBLEM.md` to
`.claude/doc-owners.txt`; add its owner row to `docs/CODE_MAP.md ## Files`; create
`docs/units/U14-fullprob.md` (Status open; `## Model` target = the decomposition proposition);
commit. The doc write is denied without the owners line.

| agent | model | files owned | tests |
|---|---|---|---|
| A1 loader | Opus | `td/instance.py` | `tests/test_instance_v2.py`: v1 loads unchanged, v2 round trip, totals equal Σ channels, `channels` field |
| A2 exporter | Opus | `tools/instance_export/export_instance.py`, `tools/instance_export/README.md` | `tests/test_instance_export_v2.py` (importlib pattern of `tests/test_instance.py:30-35`); ships first to the work machine |
| B1 cells | Opus | `td/channels.py` | `tests/test_channels.py`: conservation of M, S, S_free per zip and per-cell headroom under `synthesize_channels`; `fine_split` ratios and fallbacks; `project` sums cells and recomputes `cand`; writes `battery/results/full_problem/synthetic_v2.json.gz` early and says so |
| B2 state stage 2 | Opus | `td/stage2_state.py`, `td/model.py`, `td/channel.py` (`coefficients` only) | `tests/test_stage2_state.py`: gain equals `channel.gain_matrix` on `project(d, B)` for an integral whole-state plan (exact by linearity); positivity guard on unused slots; existing `tests/test_channel.py` unchanged |
| C level 0 | Fable (or Opus) | `td/solvers/level0.py`, `td/solvers/state_splits.py`, `td/solvers/milp_engines.py` | `tests/test_level0.py`: six-state path × two channels; coverage full when the band allows, residual when not; contiguity refused by enumeration; `U=None` raises; ordering rows do not change the optimum; `prior` reduces coverage; `append_row` pins a value; `with_cutoff` on `Level0Problem` means fewer contacts; scipy default, highs/scip gated |
| D driver | Opus | `tools/full_plan.py` | `tests/test_full_plan_cli.py`: argparse defaults reproduce `borders_report` constants; `failure.json` keys; end to end on the toy with `state_rook` monkeypatched, `--engine scipy --strategy direct` |
| V math-verify | agent default | `tools/verify/U14-fullprob/` | VERIFIED / REFUTED on the decomposition proposition (§4): separability of Σ log M_j by bundle at fixed k_B, linearity of u under cell summation, single Hungarian coupling |
| W doc | Fable (or Opus) | `docs/FULL_PROBLEM.md` | orchestrator review against this file; no method words in §1; anti-slop |

Orchestrator during wave 1: commit each report's files as it lands, run
`tests/run_all.py` after each commit, review W and V.

## Wave 2: starts when C and B1 have landed

- I integration (Opus): run `tests/run_all.py`, close seams across the contract, then launch the
  long-pole solves in the background with `python3 -u`: the joint route with the geo driver on
  the synthetic instance, time limit 600 s per pass, threads 2, portfolio only on the contacts
  pass; and the route-S regression (band ±5%, K_N = 18, committed anchors and centres) expecting
  8 splits. Logs and the timing table go to `tools/verify/U14-fullprob/`.
- R1..R3 code-verify on `level0.py`, `channels.py` + `stage2_state.py`, `full_plan.py`, in
  parallel with I's runs.
- If C lands before D: start the long pole from a short script under
  `/Users/ntlee/.claude/jobs/<job>/tmp/` calling `build_level0` + `solve_passes` directly, so the
  solve does not wait for the driver.

## Wave 3, after the timing table

Route choice (S or J) from the table; level-2 hand-off per bundle (residual pseudo-column in
`realise`); app channel-plan token in `store.member_name` (`app/store.py:41-45`) and
`steps.grid` (`app/steps.py:124-191`) taking `projections/<bundle>/` as each chain's instance;
a new run kind `plan`.

## Verification

- `.venv/bin/python3 tests/run_all.py` at 0 fail after every commit (`tests/test_docs_owners.py`
  covers the doc line).
- Route S regression reproduces 8 splits under today's four settings.
- Route J certifies each pass or records `certified = false` with the time limit.
- One `--threads` per process (trap 18); `mip_rel_gap=0.0` for any certificate (trap 12).

## Execution (optimised for wall-clock; tokens unconstrained)

- Model per step. Orchestrator (Fable): bookkeeping commit, launches, per-report commits, review
  of W and V, route choice. C and W benefit most from first-shot correctness (MILP rows, the
  doc's mathematics): Fable subagents if the harness allows, else Opus. A1, A2, B1, B2, D, I:
  Opus. V and R1..R3: the `math-verify` and `code-verify` agent definitions.
- Dynamic workflow: not for wave 1; the Agent tool runs eight agents concurrently from one
  message with completion notifications, and a workflow script would be one more thing to debug.
  Reconsider for wave 2 if seam fixes turn into a review → verify → fix loop, which is the shape
  the Workflow tool is for.
- Schedule. t0: bookkeeping commit (≈10 min). t0+10: wave 1, eight agents at once. Wave 2 the
  moment C and B1 land, even with A2 or D still running. Wave 3 after the timing table.
- Long pole: the level-0 joint solve on the synthetic CONUS instance (about 95 slots; unknown,
  minutes to hours). It reuses B1's synthetic instance and today's level-1 solve as anchor;
  nothing at zip level is recomputed until a plan is chosen. Start it before D's seams close.
- Not delegated: the bookkeeping commit, the review of W's doc against this file, the route
  decision after the timings, the open ★ items (the user's), any merge into `main` (ask first).
