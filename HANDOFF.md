# Handoff — national channel territory design / A1 track (`wt/A1`)

**Updated:** 2026-09-03 · **Branch:** `wt/A1` (worktree `.claude/worktrees/A1`; 13 commits over
`national-channel` at `a4eb488`, **not merged** — ask first) · **Head:** `d82a0fa` · **Tests:**
184 pass, 0 fail (2026-09-03 at `74eff38`)

## Start here
- **Resume point:** `docs/FRAME.md` §0 (the 2026-09-03 "end of the overnight run" entry; §6 has
  the measured rows).
- **Status header:** `CLAUDE.md`
- **Memory:** `~/.claude/projects/-Users-ntlee-projects-td/memory/td-contiguity-programme.md`;
  the merge rule is `ask-before-merging-to-hub.md`.
- **Caution:** run tests with `/Users/ntlee/projects/td/.venv/bin/python3 tests/run_all.py`
  from this worktree. `instance_descaled.json.gz`, `data/geo/` and `battery/results/`
  (`draw_k13_20260901`, `sweep_20260902_s10/k13`, `meas_20260903`) are gitignored and were
  hand-copied into this worktree; a fresh worktree needs them again.
- **Serena binds to the session's launch directory.** Launch `python-typed` only from a session
  started in `.claude/worktrees/A1`, and check `initial_instructions`' active-project path first.
- **Key docs (A1 versions on this branch):** `docs/APPROACHES.md` §A1 (charter) ·
  `docs/BRIEF.md` (units U8–U13, ★8–★12) · `docs/units/*.md` · `docs/LENS_GROMOV.md` (2026-09-03) ·
  `docs/DOMAIN_optimization.md`, `docs/DOMAIN_economic-theory.md` (2026-09-03) ·
  `docs/LIT_optimization.md` + `.bib`, `docs/LIT_economic-theory.md` (2026-09-03 section) +
  `LIT_economic-theory_A1.bib` · `docs/MODEL_U7-meas.md` + `CODEVERIFY_U7-meas.md`,
  `tools/measure/premium.py` · `docs/MODEL_U1-cert.md` + `VERIFY_U1-cert.md` ·
  `docs/LENS_GROTHENDIECK.md` (inherited) · hub docs `CHANNEL.md`, `MODEL.md`, `DATA.md`,
  `RESEARCH_FINDINGS.md`, `REVIEW_GROMOV.md`.
- **The measurement CLI:** `tools/measure/premium.py instance_descaled.json.gz
  battery/results/draw_k13_20260901 --out battery/results/meas_20260903` (both draw layouts;
  outputs the premium ladder, U1/U4/U8, verdict conversions).

## Next actions
- [ ] **★12 — merge `wt/A1` into `national-channel`?** Nothing merges without the user.
- [ ] **Launch U8-band** (`docs/units/U8-band.md`) from a session started in this worktree —
      the band-constrained kill test; its one-solve D1′ certificate can end A1. Alongside:
      U9-bandthm, U13-base, U6-sel, U3-inv (independent).
- [ ] Then U10-round, U11-roster, U4-disp (gated on U8); U12-menu (U8 + U11 + U13).
- [ ] **★11** — rewrite A1's charter step 3 in `APPROACHES.md` after U8 reports.
- [ ] **★9** — the sponsor's band `δ`, put as U12's menu, not an elicitation; **★4** is its
      second knob `ε`.
- [ ] **★10** — tie-break policy (disclose vs randomise), on U11's evidence; `S₁₃`'s margin is
      8.1e-3 nats on seed 9.
- [ ] **★8** — accept the `fotakis2014` scope correction (D6); edits four hub files.
- [ ] Carried: ★1 (are the 98 released), ★2 (audited book — now for selection only), ★3
      (stability as a criterion, after U6-sel), ★5 (least core), ★7 (`/domain econometrics`).
- [ ] Hub items untouched by this branch: seed-3 vs seed-9 k=13 map; which states are
      hand-drawn (A12); certificates 1–4 not adapted to anchored draws; palette at k ≥ 13;
      `REVIEW_GROMOV` R1 fixes and the rename pass *certified → balance-certified*;
      `CLAUDE.md`'s "$1B ± 10% probably not reachable" sentence is stale (BRIEF §6.5).
