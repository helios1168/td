# Handoff — the `runs` track (`wt/runs`)

**Updated:** 2026-09-04 · **Branch:** `wt/runs`, pushed · **Head:** `9e81d6b`
(branched from `national-channel` at `e3cc5d2`) · **Tests:** 184 pass, 0 fail (run 2026-09-04
in this worktree)

## Start here
- **Resume point:** `docs/FRAME.md` §0 — the 2026-09-04 `d7c4503` `wt/runs` entry is the top one.
- **Results:** `docs/RUNS.md` — the catalogue's numbers, the region table, the solver-fix
  writeup. `docs/RUNS_PLAN.md` is the plan it executed (now fully done, §1–§8).
- **Artifact:** https://claude.ai/code/artifact/f903ee01-eefc-40cf-bd32-8f5536b6e65f — headline
  table, pin-cost charts, 15 scenario sections with maps and per-district tables.
- **Status header:** `CLAUDE.md` (thin — it points here and at FRAME §0).
- **Memory:** `~/.claude/projects/-Users-ntlee-projects-td/memory/td-contiguity-programme.md`;
  the merge rule is `ask-before-merging-to-hub.md`.
- **Caution:** run tests with `/Users/ntlee/projects/td/.venv/bin/python3 tests/run_all.py`
  from this worktree (no `.venv` here). `instance_descaled.json.gz` (old, regression only),
  `instance_descaled_v2.json.gz` (new, cleaned — use this one), `instance_descaled_v2.raw.json.gz`
  (new, uncleaned, provenance only), `data/geo/` and `battery/results/` are all gitignored.
- **Serena binds to the session's launch directory** — start `claude` from this worktree, or
  confirm `initial_instructions`' active-project path before any edit.
- **Solver change on this branch:** `td/solvers/centers.py::assign()` now pins
  `method="highs-ds"` with `options={"time_limit": 60.0}` instead of the bare
  `method="highs"` — the auto-selecting method (and `highs-ds` with no `options` at all) hangs
  indefinitely on the new instance. Full writeup and verification in `docs/RUNS.md`.
- **Hub background (not this branch's job to update):** `docs/APPROACHES.md`, `docs/CHANNEL.md`,
  `docs/MODEL.md`, `docs/DATA.md`, `docs/RESEARCH_FINDINGS.md`, `docs/REVIEW_GROMOV.md` — the
  problem, the model, and the literature map. `wt/A1`'s track lives at `docs/tracks/A1/` and is
  independent of this branch (confirmed no file overlap as of 2026-09-04).
- **Published artifacts (hub, unrelated to this branch's):** k-Sweep (all nine k,
  `c007d61d-c753-4151-9026-2288b9d5eb38`) · Atlas (5 maps, certified k=13 draw,
  `1f2cddd9-b98b-4213-83ea-784566147c6a`).

## Next actions
- [ ] The open decision this catalogue exists to inform: **which states, if any, are
      hand-drawn** — a sponsor call, not a solver one. `docs/RUNS.md`'s region table is the
      price list.
- [ ] `td/solvers/centers.py`'s HiGHS fix has an unexplained root cause (a scipy 1.18.1 /
      HiGHS option-merging quirk) — not chased further than confirming the fix is narrow and
      correct. Worth a scipy/HiGHS upstream bug report if this recurs elsewhere.
- [ ] Still open from `RUNS_PLAN.md`: no merge to `national-channel` without asking — the
      standing rule. This branch has not proposed one.
