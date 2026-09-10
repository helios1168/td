# Unit U14-fullprob: the full multi-channel problem and its decomposition by bundle

Status: open

Track `full-problem` (worktree `.claude/worktrees/full-problem`, branch `worktree-full-problem`).
The formulation lives in `docs/FULL_PROBLEM.md`; this file is the unit's permanent record.

## Spec

Extend the single-channel pipeline (stage 1 draw, level 1 minimum-splits MILP, level 2
realisation, stage 2 Nash match) to CWIFI: national, WH and FI on CONUS, each cut into contiguous
districts inside the band [0.8τ, 1.2τ] with τ = $1B, one rep per district and at most one district
per rep, channels in priority order national, WH, FI, the residual called other. The new decision
is the channel plan per state: keep three channels, merge WH and FI, or drop national (whose
opportunity falls back into WH and FI).

## Files owned

`docs/FULL_PROBLEM.md` · `td/channels.py` · `td/stage2_state.py` · `td/solvers/level0.py` ·
`tools/full_plan.py` · `tools/verify/U14-fullprob/` · `tests/test_instance_v2.py` ·
`tests/test_instance_export_v2.py` · `tests/test_channels.py` · `tests/test_stage2_state.py` ·
`tests/test_level0.py` · `tests/test_full_plan_cli.py` · small edits to `td/instance.py`,
`td/model.py`, `td/channel.py`, `td/solvers/state_splits.py`, `td/solvers/milp_engines.py`,
`tools/instance_export/export_instance.py`.

## Files forbidden

`docs/foundations/` · `app/` until wave 3 · `battery/figures/` · `STATE.md`.

## Acceptance

1. Loader and exporter handle `td_instance_descaled/2` (nodes long by zip and channel); format 1
   loads unchanged as the one channel `national`.
2. `td/channels.py` projects a bundle to a format-1 instance on which every existing driver runs
   unchanged; conservation of M, S and S_free per zip under the synthetic split and under
   `fine_split`.
3. Level 0 solves on the synthetic CONUS instance under both routes; route S with national cover
   forced, band ±5%, K_N = 18, committed anchors and centres reproduces today's 8 splits.
4. The decomposition proposition (`## Model`) verified by `math-verify` with an artifact under
   `tools/verify/U14-fullprob/`.
5. `tests/run_all.py` at 0 fail.

## Model

Target: the decomposition proposition of `docs/FULL_PROBLEM.md` §4. For a fixed channel plan π,
the joint problem F separates by bundle into copies of the single-channel problem on the projected
instance (Z_B, M^B, S^B), with the rep constraint the only coupling, resolved by one Hungarian over
the union of districts. Statement and proof in the doc; this section records the verdict.

none yet

## Verify

none yet

## Code verify

none yet
