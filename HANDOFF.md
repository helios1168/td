# Handoff — national channel territory design / A1 track (`wt/A1`)

**Updated:** 2026-09-04 · **Branch:** `wt/A1` (worktree `.claude/worktrees/A1`) ·
**Head:** `ed5a9a8` · **Tests:** 208 pass, 0 fail (184 pre-existing + 24 new, run 2026-09-04 at
`ddd162d` in this worktree; `ed5a9a8` is docs-only)

**One line:** A1 wave 1 landed and is verified — **D1′ says the premium is NOT SOFT**, so A1
continues and wave 2 is unblocked. Four items are user-gated and waiting.

## Start here
- **Resume point:** `docs/FRAME.md` §0 (the 2026-09-04 entry; §6 has the measured rows)
- **Status header:** `CLAUDE.md`
- **Memory:** `~/.claude/projects/-Users-ntlee-projects-td/memory/td-contiguity-programme.md`;
  the merge rule is `ask-before-merging-to-hub.md`
- **Caution:** run tests with `/Users/ntlee/projects/td/.venv/bin/python3 tests/run_all.py`
  from this worktree. `instance_descaled.json.gz`, `data/geo/` and `battery/results/`
  (`draw_k13_20260901`, `sweep_20260902_s10/k13`, `meas_20260903`, `u8_band_20260904`) are
  gitignored and were hand-copied in; a fresh worktree needs them again.
- **Serena binds to the session's launch directory.** Launch `python-typed` only from a session
  started in `.claude/worktrees/A1`, and **activate by *path*** — six registered projects are
  named `td`, so activating by name is a coin flip across checkouts. Confirm with
  `get_current_config` before the first symbol edit.
- **Key docs:** `docs/APPROACHES.md` (§0 "what every track inherits", the A0–A5 charters) ·
  **A1's re-runs under `docs/tracks/A1/`** (`README.md` there maps the paths; units U8–U13,
  ★8–★12) — the hub copies at `docs/` are the neutral `a4eb488` versions and do **not** carry
  the band material · wave 1's outputs: `docs/MODEL_U8-band.md` + `CODEVERIFY_U8-band.md`,
  `docs/MODEL_U9-bandthm.md` + `VERIFY_U9-bandthm.md`, `td/solvers/eg_band.py`,
  `tools/measure/frontier.py`, `figures/u8_band/frontier.png` ·
  `docs/MODEL_U7-meas.md` + `CODEVERIFY_U7-meas.md`, `tools/measure/premium.py` ·
  `docs/MODEL_U1-cert.md` + `VERIFY_U1-cert.md` · `docs/LIT_optimization.md` + `.bib`,
  `docs/LIT_economic-theory.md` (2026-09-03 section) + `LIT_economic-theory_A1.bib` ·
  hub docs `CHANNEL.md`, `MODEL.md`, `DATA.md`, `RESEARCH_FINDINGS.md`, `REVIEW_GROMOV.md`
- **The two CLIs:**
  `tools/measure/premium.py instance_descaled.json.gz battery/results/draw_k13_20260901 --out battery/results/meas_20260903`
  (the premium ladder, U1/U4/U8, verdict conversions) ·
  `tools/measure/frontier.py instance_descaled.json.gz battery/results/draw_k13_20260901 --out battery/results/u8_band_20260904`
  (the gate, the `δ` frontier, D1′, `δ*`, first movers, N8/N9, the plot)

## Next actions

**User-gated — reported, not done. Ask before acting on any of these.**
- [ ] **Merge `wt/A1` into `national-channel`?** Four commits (`954d9eb`, `f199e92`, `69997ac`,
      `ddd162d`). Nothing merges without this answer.
- [ ] **★11 — rewrite A1's charter step 3** in `APPROACHES.md` from "rep-indexed MINLP" to
      "roster enumeration over band-constrained EG programs". A hub edit. U8 has now reported,
      so this is unblocked. Note `collapsed-on-softness` does **not** fire — the premium is not
      soft.
- [ ] **Source-document corrections wave 1 implies** (hub files, all user-gated):
      `DOMAIN_optimization` §2.12's first-mover rule is **REFUTED** (replace with the additive
      margin `max_i(u_i/g*_i − ν_i M_z) − 2nd-max`); §2.10's "multipliers for `δ > 0`" is weaker
      than the truth (all constraints are affine, so `δ = 0` too) and its coarse `≤ 2k` is
      superseded by the unconditional `≤ 2k−1`; §2.11's supergradient should read "**a**
      supergradient — the quotable one is the minimised `(T/k)Σ|ν_i|`"; §8's `borgwardt2019` is
      corroborating, not load-bearing. `DOMAIN_economic-theory` N7 grids on the spread `0.0078`
      rather than `δ₀ = 0.0039`, and §2.8's proportionality row is **refuted** (no rep is below
      proportionality at any `δ`) with its EF1 row corrected by `kawase2026balanced`.
- [ ] **★8** — accept the `fotakis2014` scope correction (D6); edits four hub files.
- [ ] **★9** — the sponsor's band `δ`, put as U12's menu, not an elicitation; **★4** is its
      second knob `ε`. **New evidence:** the frontier rises only 0.077 nats across an 84-fold
      widening of `δ`, so the choice is nearly free on value grounds — a governance question,
      not a trade-off.
- [ ] **★10** — tie-break policy (disclose vs randomise), on U11's evidence; `S₁₃`'s margin is
      8.1e-3 nats on seed 9.

**Unblocked work.**
- [ ] **Wave 2 — U10-round, U11-roster, U4-disp.** All were gated on U8's D1′ verdict; all are
      now free. Briefs at `docs/tracks/A1/units/`. U11 reuses `eg_band.py` as its solver.
- [ ] **Wave 3 — U12-menu** (needs U8 + U11 + U13). **U13-base** is independent and can start
      now.
- [ ] Carried: ★1 (are the 98 released), ★2 (audited book — now a data-quality question only),
      ★3 (stability as a criterion, after U6-sel), ★5 (least core), ★7 (`/domain econometrics`).
      **U3-inv is retired** (user, 2026-09-04) — books are measured from the data warehouse, not
      self-reported, so the strategy-proofness question has no referent.

**Queued fixes / known-stale.**
- [ ] `docs/MODEL_U8-band.md` §5.1's `ĝ > 0` guarantee is now scoped to finite `δ`; the
      `delta=None` path is guarded by an explicit per-iterate check (`CODEVERIFY` row 1).
- [ ] Hub items untouched by this branch: seed-3 vs seed-9 k=13 map; which states are
      hand-drawn (A12); certificates 1–4 not adapted to anchored draws; palette at k ≥ 13;
      `REVIEW_GROMOV` R1 fixes and the rename pass *certified → balance-certified*.

## Starting a track (A2–A5, or resuming A1)
1. `git worktree add /Users/ntlee/projects/td/.claude/worktrees/<ID> -b wt/<ID> national-channel`.
2. Hand-copy the gitignored inputs from this worktree: `instance_descaled.json.gz`, `data/geo/`,
   `battery/results/draw_k13_20260901/`, `battery/results/sweep_20260902_s10/k13/`,
   `battery/results/meas_20260903/`.
3. Start `claude` **from that directory**, and activate Serena to it **by path**.
4. Read `docs/APPROACHES.md` §0's inherited facts and FRAME §6 before the charter; ★6 is lifted.
5. Write the track's `/gromov`, `/domain` and `/research-plan` outputs under `docs/tracks/<ID>/`
   (pass the path as the skill argument); never overwrite the hub copies at `docs/`.
6. Commit on `wt/<ID>`; ask before merging. Facts, code and verified unit results merge promptly;
   the track's lens/domain/brief stay under `docs/tracks/<ID>/` until it wins or dies.
