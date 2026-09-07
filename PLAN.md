# PLAN — branch `worktree-headline`

Branch-local handoff. Written 2026-09-07 before context compaction; the next step is plan mode
for the interactive pipeline. Nothing below is implemented.

## Goal

A Streamlit app that runs the headline pipeline end to end, interactively, on one case only:
the Track 2 anchored δ = 5% map (`docs/HEADLINE.md` is the write-up; read it first). Business
users apply overrides at named steps and rerun from that step with the headline map as the
base reference. Worked example: restrict California to 3 districts, rerun, see how the rest of
the map turns out.

## What already exists

- **The app.** `app/` (618 lines: `config.py`, `scenario.py`, `engines.py`, `runner.py`,
  `runs.py`, `main.py`), `tools/app.sh`, own venv `.venv-app` from `app/requirements.txt`,
  `docs/APP.md` (§4 architecture). It never imports `td`; it launches drivers by subprocess
  (detached, log in the run dir, UI polls), reads `draw.csv` + `metrics.json`, renders maps by
  calling `tools/us_maps.py` (about 40 s per render, static PNG). Runs land in
  `battery/results/app/<scenario>_<timestamp>/`. Engine registry has `power-cells` and
  `state-atoms`; the borders pipeline is not in the app. Tabs: Define-and-run, Results, Review.
- **The pipeline, as code.** Driver `tools/state_splits.py::main` (`run_cell`, lines 208–265)
  is the whole headline pipeline in ~60 lines and is the thing to decompose into steps:
  1. `borders_report.load_committed(instance, draw, geo_cache)` → `Ctx` (zips, xy, M, state_idx,
     labels0, k, home, owners, states_by_zip, M_by_zip, missing).
  2. `_state_masses_and_moments(ctx, geo_cache)` → `M_s`, `D` (49 × 18), `edges` (rook, 107),
     `tau` (470.459), `C` (committed centres). `ss.eps_lexicographic(M_s, D)`.
  3. `ss.build_milp(M_s, D, edges, tau, delta, eps, eta=0.01, anchors=[(home_s, j)])` →
     `SplitProblem` (matrix form; `rows` maps block name → row range; variable blocks z, y, r,
     f). `ss.solve(problem, time_limit, strict=False)` → `z`, `y`, `splits`, `status`,
     `mip_gap`, `spread_rel`, `split_states`. 168 s at δ = 5% anchored; 600 s limit.
  4. `ss.balance_pass(problem, z)` → `y`, `spread_rel`, `max_dev_rel`. Sub-second.
  5. `ss.realise(xy_k, M_k, state_idx_k, z, y, C, rounds=5, tiebreak=None)` → `labels`,
     `centers`, `n_fractional`, `rounds_used`, `states[s]["iterates"]`. Seconds.
  6. `channel.place_by_state(...)` for AK/HI/unknown; `run_draw.complete(...)` for the 41
     coordinate-less zips; `borders_report.cell_row` / `write_cell` / `write_grid`;
     `splits.json`; `render_cell_maps` (about 2 min).
- **The headline cell on disk** (copied into this worktree):
  `battery/results/borders_k18_v2_20260907/track2_anchored/d0.05/d0.05/` (`draw.csv`,
  `splits.json` with full `z`, `y`, `y_shares`, `state_list`; `figures/`), `params.json` and
  `grid.csv` one level up. Committed draw: `battery/results/draw_k18_v2_20260904/k18/`.
  Instance: `instance_descaled_v2.json.gz` (worktree root). `data/geo`, `data/tiger` are
  symlinks to the hub.
- **Tests.** `.venv/bin/python3 tests/run_all.py` (306 pass). `tests/test_state_splits.py`
  has the six-state path toy. The worktree has no `.venv`; use the hub's
  `/Users/ntlee/projects/td/.venv/bin/python3`.

## Override points, and what each needs

| step | override | mechanism | exists? |
|---|---|---|---|
| level 1 | at most $m_s$ districts in state $s$ | new row $\sum_j z_{sj} \le m_s$ in `build_milp` | no; one new keyword, one row block |
| level 1 | state $s$ whole in district $j$ | `anchors` + $m_s = 1$ | anchors yes, cap no |
| level 1 | district $j$ must / must not touch $s$ | fix $z_{sj}$ via `var_lb`/`var_ub` | trivial once exposed |
| level 1 | band δ, floor η | already arguments | yes |
| level 1 | fixed shares $y_{sj}$ | bounds on `y` block | trivial once exposed |
| level 2 | rounds, incumbency tiebreak | already arguments | yes |
| any | "keep the headline where I did not touch it" | see below | no |

**Feasibility must be checked before solving.** A state of mass $M_s$ needs at least
$\lceil M_s / ((1+\delta)\tau) \rceil$ districts. CA is 4.126τ, so under δ = 5% it needs 4, and
"CA in 3" is infeasible for any arrangement of the other states: three districts would have to
carry 4.13τ, so one holds at least 1.376τ against a cap of 1.05τ. The app must compute this
floor per state from `M_s`, refuse or explain, and offer the δ that would admit it (δ ≥ 37.6%
for CA in 3). Same floor for TX (2.02τ → 2), NY (1.79τ → 2), FL (1.40τ → 2). This is the mass
bound of `docs/BORDERS_RESULTS.md`, closed form.

**"Headline as base reference" is a modelling choice to make in plan mode.** Options: (a)
warm-start only (HiGHS through `scipy.optimize.milp` has no warm-start interface; would need
`highspy`); (b) fix every $z_{sj}$ of the headline that the override does not touch (rigid,
fast, may be infeasible); (c) penalise changes to the headline's $z$ in the objective, bounded
like ε so it never buys a split (a second lexicographic level); (d) rerun free under the
override and report the diff against the headline. (c) or (d) are the honest ones.

## Constraints to keep

- The app never imports `td`; keep the subprocess seam (`docs/APP.md` §4). A step-wise driver
  means either a new driver that can start from a saved step's outputs, or the app calling
  `tools/state_splits.py` with new flags per step. Decide in plan mode.
- MILP runs are minutes; the app's runner is already asynchronous. Level 2 and the balance
  pass are seconds and can run inline.
- Maps are static PNGs by decision (2026-09-06); the compare slider exists only in artifacts.
- Never write under `battery/figures/`; app renders go to `battery/results/app/figures/`.
- Memory: delegate implementation to an Opus subagent after the plan; ask before merging to the
  hub. Serena resolves relative paths against the hub: pass absolute worktree paths.
- Bash git is aliased through a launcher the isolation hook rejects: use `\git`.
  `enforce-file-tools.sh` blocks heredocs, `cat`, `grep` on files: use Write/Read/Edit.

## Artifacts touched this session (already published, in place)

- "The Five Percent Map" `322e6a55-a576-4adf-8dc5-8fd2f4ca6c5a`: level 0 section added, Track 1 removed.
- "Districting from Duality" `d87b53b0-f394-417e-aab5-0fba8d3c6cb0`: committed-draw section added, Track 1 removed.

## Open facts recorded this session

- Seed 2 was chosen by stage-2 value among ten seeds (`metrics.json`); `CHANNEL_NOTE.md` §5.2
  says otherwise and is out of date.
- The four split states' district sets are pairwise disjoint, so `realise`'s alphabetical
  order is inert on the headline cell.
- Opportunity is not double counted: the exporter keeps one M per zip and raises on conflict;
  the instance shows no 1/n saturation signature. Unverifiable from here: whether the
  work-machine input was pre-summed upstream.
