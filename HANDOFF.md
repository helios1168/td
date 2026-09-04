# Handoff — national channel territory design (`national-channel`, the hub)

**Updated:** 2026-09-04 · **Branch:** `national-channel`, pushed · **Head:** `b3931fa`
(state commit `2ce052e`) · **Tests:** 184 pass, 0 fail (run 2026-09-04 at `b3931fa` in this
worktree)

## Start here
- **Resume point:** `docs/FRAME.md` §0 — the 2026-09-04 entry is the top one; §6 carries the
  measured rows.
- **Status header:** `CLAUDE.md` (thin — it points here and at FRAME §0).
- **Memory:** `~/.claude/projects/-Users-ntlee-projects-td/memory/td-contiguity-programme.md`;
  the merge rule is `ask-before-merging-to-hub.md`. A session-scoped copy also lives at
  `~/.claude/projects/-Users-ntlee/memory/td-national-channel.md`.
- **Caution:** run tests with `/Users/ntlee/projects/td/.venv/bin/python3 tests/run_all.py`
  from this worktree. `instance_descaled.json.gz`, `data/geo/` and `battery/results/` are
  gitignored and were hand-copied here; **this worktree has `draw_k13_20260901` and
  `sweep_20260902_s10` but not `meas_20260903`** (that one is only in `.claude/worktrees/A1`).
- **Serena binds to the session's launch directory.** Launch `python-typed` only from a session
  started in the worktree that owns the files, and check `initial_instructions`' active-project
  path first.
- **Key docs:** `docs/APPROACHES.md` (§0 "what every track inherits", the A0–A5 charters) ·
  hub stage-2/3 copies `docs/LENS_*.md`, `docs/DOMAIN_*.md`, `docs/BRIEF.md`, `docs/units/U0–U7`
  (neutral, restored from `a4eb488`) · **A1's re-runs under `docs/tracks/A1/`** (`README.md`
  there maps the paths; units U8–U13, ★8–★12) · `docs/LIT_optimization.md` + `.bib`,
  `docs/LIT_economic-theory.md` (2026-09-03 section) + `LIT_economic-theory_A1.bib` ·
  `docs/MODEL_U7-meas.md` + `CODEVERIFY_U7-meas.md`, `tools/measure/premium.py` ·
  `docs/MODEL_U1-cert.md` + `VERIFY_U1-cert.md` · `docs/LENS_GROTHENDIECK.md` (inherited) ·
  hub docs `CHANNEL.md`, `MODEL.md`, `DATA.md`, `RESEARCH_FINDINGS.md`, `REVIEW_GROMOV.md`.
- **The measurement CLI:** `tools/measure/premium.py instance_descaled.json.gz
  battery/results/draw_k13_20260901 --out battery/results/meas_<date>` (both draw layouts;
  outputs the premium ladder, U1/U4/U8, verdict conversions).
- **Stage-1 figures:** `tools/us_maps.py instance_descaled.json.gz --out figures/<dir>/
  --districts <draw.csv> --regions <draw.csv>` (~3 s per k with the gazetteer cached). It also
  emits the four base figures into `--out`; delete them if you only want the two maps.
  `--regions` is the power diagram; `--regions-voronoi` is the superseded catchment fill.
- **Published artifacts:** k-Sweep (all nine k, `c007d61d-c753-4151-9026-2288b9d5eb38`) ·
  Atlas (5 maps, certified k=13 draw, `1f2cddd9-b98b-4213-83ea-784566147c6a`).

## Starting a track (A2–A5, or resuming A1)
1. `git worktree add /Users/ntlee/projects/td/.claude/worktrees/<ID> -b wt/<ID> national-channel`.
2. Hand-copy the gitignored inputs: `instance_descaled.json.gz`, `data/geo/`,
   `battery/results/draw_k13_20260901/`, `battery/results/sweep_20260902_s10/k13/`, and
   `battery/results/meas_20260903/` from `.claude/worktrees/A1` (it is not in the hub worktree).
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
- [x] **Stage-1 sweep fully mapped** (`b3931fa`, 2026-09-04): k = 8, 9, 11, 12, 14, 15 rendered,
      artifact `c007d61d` republished with a section per k.
- [ ] **U8-band** (`docs/tracks/A1/units/U8-band.md`) — the band-constrained kill test; its
      one-solve D1′ certificate can end A1. **A session was running it, with U9-bandthm, in
      `.claude/worktrees/A1` on 2026-09-04** — check that worktree's `git status` and its own
      `HANDOFF.md` before starting anything on those units.
- [ ] Alongside U8 (independent): U9-bandthm, U13-base, U6-sel. **U3-inv is retired** (user
      decision 2026-09-04 — the books are measured from the data warehouse, not self-reported;
      ★2 becomes a data-quality question).
- [ ] Then U10-round, U11-roster, U4-disp (gated on U8); U12-menu (U8 + U11 + U13).
- [ ] **★11** — rewrite A1's charter step 3 in `APPROACHES.md` after U8 reports.
- [ ] **★9** — the sponsor's band `δ`, put as U12's menu, not an elicitation; **★4** is its
      second knob `ε`.
- [ ] **★10** — tie-break policy (disclose vs randomise), on U11's evidence; `S₁₃`'s margin is
      8.1e-3 nats on seed 9.
- [ ] **★8** — accept the `fotakis2014` scope correction (D6); edits four hub files.
- [ ] Carried: ★1 (are the 98 released), ★2 (now data quality, see above), ★3 (stability as a
      criterion, after U6-sel), ★5 (least core), ★7 (`/domain econometrics`).
- [ ] **Queued hub fixes, none started:** `REVIEW_GROMOV` R1 — `docs/channel_note/ceiling.py:75`
      still hard-codes `SATURATION = 0.05` against a measured 41.9%, and `channel_note` §5.1 carries
      the old arithmetic; the rename pass *certified → balance-certified*; `CLAUDE.md`'s
      "$1B ± 10% probably not reachable" sentence is stale (BRIEF §6.5).
- [ ] Hub items still open: seed-3 vs seed-9 k=13 map (the decision FRAME §0's 2026-09-02 entry
      raises); which states are hand-drawn (A12); certificates 1–4 not adapted to anchored
      draws; palette at k ≥ 13 (`SOUTHWEST` and `D07` share a hue in the 12-colour palette).
