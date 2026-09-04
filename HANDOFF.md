# Handoff — national channel territory design / A1 track merged (`national-channel`)

**Updated:** 2026-09-03 · **Branch:** `national-channel`, fast-forwarded to `wt/A1` (the A1
track) with the user's approval and pushed; `wt/A1` and its worktree `.claude/worktrees/A1`
continue from the same head · **Head:** `8546de6` · **Tests:** 184 pass, 0 fail (2026-09-03 at
`74eff38`; merge was a fast-forward, not re-run)

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
- **Key docs:** `docs/APPROACHES.md` (§0 "what every track inherits", the A0–A5 charters) ·
  hub stage-2/3 copies `docs/LENS_*.md`, `docs/DOMAIN_*.md`, `docs/BRIEF.md`, `docs/units/U0–U7`
  (neutral, restored from `a4eb488`) · **A1's re-runs under `docs/tracks/A1/`** (`README.md`
  there maps the paths; units U8–U13, ★8–★12) ·
  `docs/LIT_optimization.md` + `.bib`, `docs/LIT_economic-theory.md` (2026-09-03 section) +
  `LIT_economic-theory_A1.bib` · `docs/MODEL_U7-meas.md` + `CODEVERIFY_U7-meas.md`,
  `tools/measure/premium.py` · `docs/MODEL_U1-cert.md` + `VERIFY_U1-cert.md` ·
  `docs/LENS_GROTHENDIECK.md` (inherited) · hub docs `CHANNEL.md`, `MODEL.md`, `DATA.md`,
  `RESEARCH_FINDINGS.md`, `REVIEW_GROMOV.md`.
- **The measurement CLI:** `tools/measure/premium.py instance_descaled.json.gz
  battery/results/draw_k13_20260901 --out battery/results/meas_20260903` (both draw layouts;
  outputs the premium ladder, U1/U4/U8, verdict conversions).

## Starting a track (A2–A5, or resuming A1)
1. `git worktree add /Users/ntlee/projects/td/.claude/worktrees/<ID> -b wt/<ID> national-channel`.
2. Hand-copy the gitignored inputs from this worktree: `instance_descaled.json.gz`, `data/geo/`,
   `battery/results/draw_k13_20260901/`, `battery/results/sweep_20260902_s10/k13/`,
   `battery/results/meas_20260903/`.
3. Start `claude` **from that directory** (Serena binds to the launch directory; confirm with
   `initial_instructions` before any `python-typed` run).
4. Read `docs/APPROACHES.md` §0's inherited facts and FRAME §6 before the charter; ★6 is lifted.
5. Write the track's `/gromov`, `/domain` and `/research-plan` outputs under `docs/tracks/<ID>/`
   (pass the path as the skill argument); never overwrite the hub copies at `docs/`.
6. Commit on `wt/<ID>`; ask before merging. Facts, code and verified unit results merge promptly;
   the track's lens/domain/brief stay under `docs/tracks/<ID>/` until it wins or dies.

## Next actions
- [x] **★12 — merged.** `national-channel` fast-forwarded to `wt/A1` at `8546de6` on 2026-09-03
      (user approved); future track work still asks before merging.
- [ ] **Launch U8-band** (`docs/tracks/A1/units/U8-band.md`) from a session started in
      `.claude/worktrees/A1` —
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
