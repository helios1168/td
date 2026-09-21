# HiGHS and scipy: pins, engine, sizes

- `centers.assign()` pins `method="highs-ds"` with `options={"time_limit": 60.0}`; the bare
  `highs` call hangs on v2 under scipy 1.18.1 (trap 14).
- Background solver runs use `python3 -u`: `frontier.py` block-buffers its output.
- **Level-1 engine since 2026-09-09**: highspy 1.15 with flow roots fixed to the anchor
  states, the `portfolio` strategy (`tools/state_splits.py`), certificate by cutoff
  (`with_cutoff`). At k = 18: 6,498 variables, 1,764 binaries, 11,317 rows; certifies in 49 s
  under the portfolio. Under scipy's HiGHS the k = 20 cell stopped at the 600 s cap with a
  one-split gap; the portfolio closes it in 70 s alone on the machine
  (`mem:facts/level1-certified-splits`).
- One `threads` value per process (trap 18): the portfolio parent uses 2. Pass
  `mip_rel_gap=0.0` for any certificate (trap 12). Keep the objective in feasibility searches
  (trap 19).
- `scipy.optimize.milp` takes no warm start (`mem:verify/oracles-milp`).
- **Level 0 (full problem)**: slot count is the size lever. About 95 slots gives about 34k
  variables, 9.4k binaries, 60k rows; 150 slots gives 54k / 15k / 101k. `build_level0` raises
  when U is None, because without an upper band the coverage passes build one giant district
  per bundle.
- Code anchors (valid at 2026-09-10): `SplitProblem`, `build_milp`, `balance_pass`,
  `eps_lexicographic`, `_highs_lp`, `_scip_solve`, `with_cutoff`, `fix_roots` in
  `td/solvers/state_splits.py` and `td/solvers/milp_engines.py`; line numbers are in
  `git show worktree-full-problem:PLAN.md`. Use Serena `find_symbol` rather than trusting them.

Source: `main:STATE.md` `## Facts` (a3924e8); `worktree-full-problem:PLAN.md` "What the
codebase has" and §5.
