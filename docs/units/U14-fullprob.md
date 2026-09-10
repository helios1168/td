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
   loads unchanged as the one channel `national`. Since 2026-09-11 the exporter also accepts the
   three national sub-channels (Chase, Wells WH, Wells FI, any letter case) in place of
   `national`, kappa on their per-zip sum, and `fine_split` is then exact (N_WH = Wells WH,
   N_FI = Chase + Wells FI); `docs/FULL_PROBLEM.md` §2.
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
the union of districts. Statement and proof in the doc.

## Verify

VERIFIED 2026-09-10, all four clauses (a) additivity of u over cells, (b) separability of stage 1
by bundle at fixed π and k_B, (c) injectivity as the only coupling with one assignment over the
union, (d) per-channel floors break Lemma 6. 60 checks, 0 failures, sympy identities plus
numeric oracles. Artifact `tools/verify/U14-fullprob/verify_decomposition.py`, write-up
`tools/verify/U14-fullprob/REPORT.md`. Two requirements it leaves for the code: one global rep
order on every `gain_matrix` call, and candidacy restrictions through the penalty assignment of
`tools/staff.py`, never `channel.match`.

## Code verify

2026-09-10, three reports under `tools/verify/U14-fullprob/`, each with a runnable artifact.

- `CODEVERIFY_level0.md` (`verify_level0.py`, 45 checks): fifteen mapping rows of §5 confirmed
  row by row; one defect, the centroid-distance cap indexed per pair instead of per (pair,
  slot); the no-incumbent timeout path unchecked. Fixed in the integration commit.
- `CODEVERIFY_channels.md` (`verify_channels.py`, 107 checks): `channels.py` and
  `stage2_state.py` implement §2 to §4 as written; the projected gain equals the state-level
  gain at 1e-9 and the sum over bundles equals the cell-level gain for every `filler_capture`.
  Three small defects (a channel-less instance silently zeroed by `fine_split`, Hall's
  condition missed by the candidacy guard, channel order taken from the node column instead
  of `meta`). Fixed in the integration commit.
- `CODEVERIFY_full_plan.md` (`full_plan_probes/`): seventeen claims confirmed, three defects
  (a zero-slot stage crashes, the catch-all runs on a product bundle and never fires where
  national is served, route R's moves run on the pinned problem so no merge is accepted).
  Fixed in the integration commit. `--incumbency` and `--centers` are exercised only by the
  regression run, which reproduced today's 8 splits.

Regression (route S, national only, band 1 ± 0.05, K = 18 used of 19, committed anchors and
centres, synthetic instance): 8 splits, CA 5, NY 3, TX 2, FL 2, the committed map's count.
Cover pass certified in 15 s; the contacts pass hit the 600 s limit at incumbent 85 and the
compactness pass brought it to 57 contacts, uncertified. Level 1 certifies the same count in
49 s, so the level-0 form of the same problem is slower; see the timing table in
`tools/verify/U14-fullprob/TIMINGS.md`.
