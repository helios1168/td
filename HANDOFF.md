# Handoff: the full-problem track, 2026-09-11

The entry point for a new session or agent team picking up this track with no chat history.
`PLAN.md` stays the running log (its `## Next step` has the full findings); this page says where
things are, how to set up, what is running, and what comes next. Like `PLAN.md`, it is deleted
in the last commit before a merge into `main`.

## Where things are

- Repo `git@github.com:helios1168/td.git`, branch `worktree-full-problem` (the user pushes it:
  `git push origin worktree-full-problem`). The branch is about 80 commits ahead of `main`; `main` has 4 commits the branch does
  not (the latest `a3924e8`, a `State:` checkpoint). Never merge into `main` unasked: merges are
  fast-forward and the user's call.
- On the user's Mac the hub checkout is `/Users/ntlee/projects/td` and this track's worktree is
  `.claude/worktrees/full-problem` (locked). Results live under the worktree's
  `battery/results/full_problem/` (gitignored).
- Recent commits: `e15daa3` v4 landed and re-ran; `e931b87` the `--force-national` and
  `--dist-max-state` switches (suite 811 pass); `6568e99` the forced-national findings in
  `PLAN.md`; this commit, `tools/full_problem_runs/` and this page.

## Setting up a fresh clone

- Python: CPython 3.13.15 and the frozen pins, never upgraded (the zip50 anchor depends on
  them): `uv venv --python 3.13.15 .venv && uv pip install --python .venv/bin/python3 -r
  requirements.txt`, then on macOS the `cbcbox` codesign fix in the note at the foot of
  `requirements.txt`. Do not run `uv sync`: on 2026-09-11 one replaced the hub `.venv` with
  Python 3.12 and no pyproj, matplotlib or highspy mid-run, and the venv had to be rebuilt.
- Confidential inputs, gitignored, copied by hand from the user's Mac (never commit them, never
  send them to any service): `instance_descaled_v4_conus.json.gz` (the live v4 CONUS file,
  6,478 zips), `instance_descaled_v4.json.gz` (the raw v4 export), `data/geo/` (the gazetteer
  cache), and for the maps `data/tiger/2025/tl_2025_us_zcta520.*` (822 MB) or `TD_ZCTA_SHP`
  pointing at a copy. `docs/CODE_MAP.md ## Gitignored inputs` has the full list.
- Reference results to copy with them (the whole `battery/results/full_problem/` is 1.9 GB):
  `grid_20260911_v4/` (v4 with every rule; the reference cell for the forced study is
  `full/X_n16w11f20_d100_d900n6_full`), `grid_20260911_v4_force*/` (the forced study) and
  `hot/` (symlinked summary figures, its `README.md` maps names to run directories).
- `TD_ROOT` names the directory holding `.venv`, the instance and `data/` for the scripts in
  `tools/full_problem_runs/`; it defaults to the repo root. On the Mac it is the hub,
  `/Users/ntlee/projects/td`.
- Tests: `.venv/bin/python3 tests/run_all.py` from the repo root (811 pass at `e931b87`).

## The problem in brief

CWIFI territory design on CONUS: about $48B of opportunity over national (sub-channels N_WH and
N_FI), WH and FI, each carved into districts of roughly equal opportunity, one wholesaler per
district. Level 0 (`td/solvers/level0.py`, driven by `tools/full_plan.py`) is a MILP at state x
channel grain that picks each state's bundles (N, WH, FI, WH_PLUS, FI_PLUS, WHFI, WHFI_PLUS) and
shares, stage by stage in priority order (national, WH, FI, catch-all, sweep).
`tools/plan_realise.py` cuts states into zips, repairs contiguity and staffs districts;
`tools/plan_maps.py` and `tools/plan_summary.py` draw them; `tools/full_grid.py` runs many cells.
The formulation is `docs/FULL_PROBLEM.md`, the model line by line `docs/MODEL_FULL.md`.

"Full rules" means split caps CA 3, TX 2, NY 3; the band break on CA and TX (their districts may
carry the capped excess past U); the level-0 sweep (every residual cell joins an adjacent
district, so unheld mass is 0) and the plus pair; MT, WA and WY in one other-first all-channel
district; at most 900 km between any two states' centroids and six states per district; each
bundle's band 10% either side of its own mean; district counts as ceilings.

Dollars: the file is descaled. The user's $17.6B for v3 national (8,479.8 units) gives about
$2.08MM per unit, so v4 carries national $17.9B (8,613.5), WH $11.1B (5,341) and FI $18.6B
(8,968). A count k gives a target of channel mass / k: WH 11 is $1.01B, FI 20 $931MM, FI 21
$886MM, national 18 $993MM.

## The current study: national forced for listed states (FI 20)

The user's rule: every dollar of a listed state's national sits in pure national (N) districts,
or the run fails and names the state. Group 1 is TX NY FL NJ IL AZ NC PA MI OH VA GA CO MD
(60.5% of national); group 2 adds WA UT IN LA MN CT (67.6%), with WA's pair cap relaxed to 1,200
km (its best district under 900 km is WA+ID+OR at 181, below any floor). Only national is forced;
WH and FI stay free. All cells ran full rules with WH 11 and FI 20. Every solved cell passes
`force_check.py`; unheld mass is 0 in each.

| group, national k | TX split cap | outcome | grid |
|---|---|---|---|
| G1 10 to 12 | 2 | infeasible: TX alone blocks (two TX districts both need the floor) | `_force` |
| G1 10 to 12 | 1 | solves; 10 N districts, 43 in all, WH and merged districts as unforced | `_force3` |
| G1 13 | 2 | proven infeasible at 600 s | `_force3` |
| G1 13 to 16 | 1 | solves (not yet compared or linked in `hot/`) | `_force4` |
| G1 14 to 16 | 2 | solves but fragments: 15 to 23 districts in pieces | `_force`, `_force2` |
| G1 with CO | any | CO's best N district is 442, below the floor at every k, while UT is other-first | |
| G2 10 to 13, LA forced | 1 or 2 | infeasible: TX+LA 1,057 against the TX district's 1,040 | `_force2`, `_force3`, `_force4` |
| G2 10 to 13, LA not forced | 1 | solves; 18 states, 5,562.2 of national in N | `_force4` |
| G2 14, CO not forced | 2 | solves; 43 districts, but one N district at 1,335 and one 2,287 km wide | `_force2` |
| G2 15, all 20 states | 2 | solves; 44 districts, 10 in pieces, the cleanest G2 cell | `_force2` |
| G2 16, all 20 states | 2 | N stage fine, FI stage no incumbent in 180 s; the 600 s re-run was still running at this commit | `_force4` |

Group 2 runs without the other-first district: MT+WY cannot reach its floor once WA and UT are
forced. Grids are `battery/results/full_problem/grid_20260911_v4_force{,2,3,4}/`, each with
`grid.md`, `status.json` and one directory per cell; a failed cell's `failure.json` names the
stage and reason (`infeasible` is a proof, `no_incumbent` a time limit).

These choices were made in session and are the user's to confirm: G1 without CO at every k; TX in
one N district as the fix; G2 without other-first; LA not forced at k 13 and below; CO forced in
G2 only at k 15 and above (that one is the user's own rule).

## Why districts still come out in pieces

Level 0 enforces contiguity only on the state rook graph. The realiser cuts a split state by a
power diagram that never reads an edge (the contiguous cut is adopted for WH only), then repairs
by moving stray pieces, refusing any move that worsens a district's band. With `--split-cut
contiguous` on every bundle (`SPLIT_CUT_BUNDLES=N,WH,FI,WH_PLUS,FI_PLUS,WHFI,WHFI_PLUS
tools/full_problem_runs/rerealise.sh`, realiser only, no re-solve) districts in pieces fall
from 8 to 4 on the unforced 16-11-20 (band violations 15 to 19), 10 to 6 on G2 k 15, 15 to 14
on G1 k 14. What remains, from `unrepaired.py`:

1. The split-state cut was not border-aware. Fixed in `9439874` (a share now seeds at the
   district's border); the N AL,FL,MS,TN stray is gone. WH_03's 113-zip CT end remains: its NY
   share must join NJ to CT and is too small to (see the FI 21 section).
2. Band-locked repair in forced cells: the sweep pushes some districts far over U, so no
   neighbour can take a piece. Still the main source of pieces in the S cells.
3. No cell-graph edge across DC-VA. Fixed in `d341461` (edge 20037 to 22209).

Contiguity is measured on the Voronoi cell graph of the zip points; the maps draw real ZCTA
polygons, so a district can look scattered on screen and still be connected (CLAUDE.md trap 23).

## The national-only study (in flight)

The user's correction after the FI 21 run: its point is to find which states must get a
national-only district, and national-only districts must not spread into non-group states. The
setup, the grid in flight (`grid_20260911_fi21_P5`), the findings so far and the resume steps
are in `PLAN.md ## Next step`; figures land in
`battery/results/full_problem/fi21_national_only_summaries/`. Bead `td-9ek.20.8`.

## The FI 21 run (2026-09-11 late night, done)

National k 10 to 16, WH 11, FI 21, full rules with caps CA 3 TX 2 NY 2 FL 2 and band break CA
TX NY FL, run in the sandvault clone (`/Users/Shared/sv-ntlee/repos/td`, results under this
worktree's `battery/results/full_problem/grid_20260911_fi21_*`). Each grid has a `_newcut` twin:
the same cells re-realised with the border-aware cut and the DC-VA edge. `PLAN.md ## Next step`
has the commits and findings; in short:

- The new `--cover-national` rule with N_WH finishing in seq_WH is infeasible at every k
  (`_C`, 14 cells): the national crumbs seq_N leaves cannot fill a WH_PLUS slot. Route joint
  found no incumbent at 600 s.
- The user's fallback, grid `_S`: G1 (G2) forced into pure N except CO (WA, CO, LA), which sit
  in the other-first all-channel district, with the new caps. It needs TX in one N district up
  to k 13 (G1) and 14 (G2); the `_tx1` cells are in `_S_retry1`, `_S_retry2`.
- `_U2` is unforced plus the v4 reference n16w11f20 with the old caps.

| cell | districts | N/WH/FI | states in 3 channels | max extent km | staffing value | in pieces (before, B+C) |
|---|---|---|---|---|---|---|
| REF_n16w11f20_oldcaps | 46 | 14/10/19 | 34 | 1360 | 239.70 | 4, 2 |
| U_n10 | 43 | 10/10/20 | 35 | 1360 | 225.27 | 2, 2 |
| U_n11 | 43 | 10/10/20 | 35 | 1655 | 225.23 | 2, 2 |
| U_n12 | 44 | 11/10/20 | 31 | 1770 | 229.95 | 2, 2 |
| U_n13 | 44 | 11/10/20 | 32 | 1429 | 229.99 | 2, 2 |
| U_n14 | 46 | 13/10/20 | 31 | 1360 | 239.21 | 5, 1 |
| U_n15 | 47 | 14/10/20 | 32 | 1360 | 243.84 | 3, 1 |
| U_n16 | 47 | 14/10/20 | 32 | 1360 | 243.76 | 5, 3 |
| S1_n10 tx1 | 43 | 10/10/20 | 33 | 1383 | 225.43 | 5, 5 |
| S1_n11 tx1 | 43 | 10/10/20 | 33 | 1383 | 225.45 | 4, 4 |
| S1_n12 tx1 | 44 | 11/10/20 | 31 | 1383 | 230.18 | 7, 6 |
| S1_n13 tx1 | 44 | 11/10/20 | 29 | 1383 | 230.21 | 5, 5 |
| S1_n14 | 46 | 13/10/20 | 23 | 1443 | 239.44 | 6, 6 |
| S1_n15 | 47 | 13/10/21 | 28 | 1655 | 243.38 | 4, 4 |
| S1_n16 | 46 | 13/10/20 | 28 | 1443 | 239.46 | 8, 7 |
| S2_n10 tx1 | 43 | 10/10/20 | 29 | 1423 | 225.78 | 5, 4 |
| S2_n11 tx1 | 43 | 10/10/20 | 27 | 1491 | 225.79 | 5, 6 |
| S2_n12 tx1 | 44 | 11/10/20 | 31 | 1778 | 230.48 | 5, 5 |
| S2_n13 tx1 | 44 | 11/10/20 | 30 | 1778 | 230.45 | 4, 4 |
| S2_n14 tx1 | 45 | 12/10/20 | 30 | 1778 | 235.04 | 5, 4 |
| S2_n15 | 46 | 13/10/20 | 30 | 1443 | 239.63 | 9, 5 |
| S2_n16 | 47 | 14/10/20 | 27 | 1443 | 244.02 | 6, 5 |

Unheld mass is 0 on every channel of every cell; `force_check.py` is OK on every S cell. The
plan opens fewer N districts than the ceiling at every k. WH_03's (WH_04's in G2) CT end, 113
zips, stays in pieces in every cell but S1 n14 and n15: its NY share is too small to join NJ to
CT, and a bridge in the cut (tried, reverted) wrecks the band.

Environment notes for the sandbox: set `TD_ZCTA_SHP` to the hub's
`data/tiger/2025/tl_2025_us_zcta520.shp` (the default path is under the home directory), and
run `full_grid.py` from a code snapshot (`git archive <commit>`) so edits cannot reach a running
grid. The cell files are `cells_input.json` in each grid directory.

## Open decisions (the user's)

1. Which FI 21 cell goes forward (table above), and whether TX in one N district is acceptable
   under forcing (TX=2 is infeasible at low k with either group).
2. Adopt the contiguous cut for every bundle (all FI 21 cells used it), and what to do about
   WH_03's CT end: a level-0 floor on a split share that must join two of its district's states,
   or accept the piece (`td-9ek.20.6`, `td-9ek.9`).
3. From `PLAN.md`: which v4 cell replaces the frozen v3 rank 1 for stakeholders; the "other"
   floor; ND SD NE on FI alone; the extent cap versus none; 16-11-20 versus 18-11-19; route R;
   whether WH_03's CT piece needs a repair extension; the merge itself.

## Tools for this study (`tools/full_problem_runs/`)

| script | what it does |
|---|---|
| `cells.py` | writes a `full_grid.py` cell file for a group and a set of counts, with the rules above |
| `run_grid.sh CELLS OUT [CONC]` | the grid, `rerealise.sh` on every solved cell, `force_check.py` into `OUT/force_check.txt` |
| `rerealise.sh DIR...` | realise with every adopted rule, maps, summary figure; `SPLIT_CUT_BUNDLES` widens the contiguous cut |
| `force_check.py CELLS GRID` | every forced state's national in pure N districts, per cell |
| `probe_force.py CELLS TAG OUT [--pairs]` | leave-one-out over a failed cell's forced states, to name the blocker |
| `compare.py A B` | grid rows, per-bundle masses, shared districts, districts in pieces |
| `unrepaired.py RUN...` | districts still in pieces, with the repair's reasons |

## Conventions that bite

- One `--threads` value per process (trap 18); cells run at 2 threads, 180 s per pass, 13 to 17
  minutes each. On a 12-core machine run 3 or 4 cells at once; more oversubscribes and turns
  solvable cells into `no_incumbent`.
- "greedy plan failed ...; solving cold" in a log is normal. The grid's `residual_mass` column is
  the realiser's per-bundle residual, not unheld mass; unheld mass is the per-channel residual at
  the end of `step_plan_realise.log`.
- Write no em-dashes and no filler words in docs, commits or comments (the user's style rule).
  Never write `STATE.md` from the track; docs under `docs/` need a line in
  `.claude/doc-owners.txt`; `docs/foundations/` is read-only.
- The user pushes as a rule. Never push to `main`, never force-push.

## Execution (suggested for a multi-agent team)

- Long pole: the FI 21 grid, 7 cells per group at about 15 minutes each, 3 or 4 at a time (about
  30 minutes per group, 1.5 hours for all three). Start it the moment the user picks the
  forcing; it reuses the reference cell for comparison and recomputes nothing else.
- In parallel, disjoint files: one agent on the border-aware split-state cut and the DC-VA edge
  (`tools/plan_realise.py` and its tests), measured with `unrepaired.py` on copies of existing
  runs; one agent comparing and linking round 4 and the FI 21 cells (`hot/`, `PLAN.md`).
- Not delegated: the user's decisions above, anything touching `main`, and the review of a
  realiser change before it re-realises any figure in `hot/`.
