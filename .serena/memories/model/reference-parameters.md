# Reference parameters, the utility, and the per-zip sizing

Utility (`td/model.py`, duplicated in `td/channel.py`):
`u_i(z) = c1·S_i(z) + c2·(T_z - S_i(z)) + c_free·S_free(z) + λ·M_z`, with `c1 = 1-λ`,
`c2 = θ(1-λ)`, and `c_free` in {c2, c1, λ} by `filler_capture` (`theta` gives c2, `full` gives
c1). Stage 1 (the draw) sees `(z, M_z, q_z)` only; books enter at stage 2 (the match).

Reference values (`channel_note.tex` §5.1, re-measured on v2 2026-09-04): `θ = 0.40`,
`λ = 0.30`, so `c1 = 0.70`, `c2 = 0.28`, `c1 - c2 = 0.42`. The app defaults to
`filler_capture="full"`; the drivers default to `theta`, so a no-flag clip stays comparable to
the committed map (`mem:decisions/app-2026-09-08`).

Per-zip sizing at aggregate saturation 29.588%: a zip whose whole book sits with one incumbent
is worth `u_incumbent = 0.507·M_z` against `u_other = 0.383·M_z`. Of the incumbent's utility
**59.1% is the pure opportunity term** `λ·M_z` and **24.5% the incumbency premium**
`(c1-c2)·S_i(z)`; the hold-versus-not swing is **32.5%**.

The v1 figures (89.6% / 6.7% against an assumed 5% saturation) were wrong. The Gromov review R1
(`git show 81bd59f:docs/REVIEW_GROMOV.md`) measured v1 `Σ(T+S_free)/ΣM` at 41.9% on 2026-09-01
(median per-zip `t_z` 46.8%, p90 110%; 48.0% of opportunity in zips above 30%), giving an
opportunity share of about 59% and a swing of about 42%. R1's downstream premium arithmetic is
v1 and stale.

Two saturation definitions coexist: `ΣT/ΣM` = 29.588% and `Σ(T+S_free)/ΣM` = 29.8107% on v2
(`docs/units/P0C-screen.md`). Name the one you quote.

Consistency check: `(1-λ)(1-θ) = 0.42` reproduces the v1 measured swing of about 42% to 0.0017
(`mem:model/u2-stab`).

Source: `main:STATE.md` `## Facts` (a3924e8); `worktree-full-problem:PLAN.md` "What the codebase
has"; agent-memory modeler/project_u2-stab-traps.
