# Handoff — the `runs` track (`wt/runs`)

**Updated:** 2026-09-04 · **Branch:** `wt/runs`, pushed · **Head:** `2f83d48`
(branched from `national-channel` at `e3cc5d2`) · **Tests:** 184 pass, 0 fail (run 2026-09-04
in this worktree)

## Start here
- **Resume point:** `docs/FRAME.md` §0 — the 2026-09-04 `wt/runs` entry is the top one.
- **Task detail:** `docs/RUNS_PLAN.md` — self-contained, start at its §0. It has already done
  steps 1–5 and §1–§2 (worktree, Serena, gitignored inputs, tests, old-instance regression,
  new-instance validation and the `BLANK`-pseudo-zip fix); §4 onward (scenario specs, the run
  catalogue, maps, the artifact) has not run.
- **Status header:** `CLAUDE.md` (thin — it points here and at FRAME §0).
- **Memory:** `~/.claude/projects/-Users-ntlee-projects-td/memory/td-contiguity-programme.md`;
  the merge rule is `ask-before-merging-to-hub.md`.
- **Caution:** run tests with `/Users/ntlee/projects/td/.venv/bin/python3 tests/run_all.py`
  from this worktree (no `.venv` here). `instance_descaled.json.gz` (old, regression only),
  `instance_descaled_v2.json.gz` (new, cleaned — use this one), `instance_descaled_v2.raw.json.gz`
  (new, uncleaned, provenance only), `data/geo/` and `battery/results/` are all gitignored.
- **Serena binds to the session's launch directory** — start `claude` from this worktree, or
  confirm `initial_instructions`' active-project path before any edit.
- **Real total ≈ $18B** (sponsor-confirmed, new instance) ⇒ working target k≈18. Every region
  (§3 of `RUNS_PLAN.md`) is now oversized as a single district at that target — CAROLINAS and
  SOUTHWEST are the closest fits, CALIFORNIA the furthest.
- **Hub background (not this branch's job to update):** `docs/APPROACHES.md`, `docs/CHANNEL.md`,
  `docs/MODEL.md`, `docs/DATA.md`, `docs/RESEARCH_FINDINGS.md`, `docs/REVIEW_GROMOV.md` — the
  problem, the model, and the literature map. `wt/A1`'s track lives at `docs/tracks/A1/` and is
  independent of this branch (confirmed no file overlap as of 2026-09-04).
- **Published artifacts (hub, unrelated to this branch's future one):** k-Sweep (all nine k,
  `c007d61d-c753-4151-9026-2288b9d5eb38`) · Atlas (5 maps, certified k=13 draw,
  `1f2cddd9-b98b-4213-83ea-784566147c6a`). This branch's eventual artifact must be a **new** one.

## Next actions
- [ ] §4 — write the 14 scenario specs at `docs/artifacts/runs/scenarios/*.json`
      (`<region>_fix.json` / `<region>_anchor.json`, 7 regions).
- [ ] §5 — run the catalogue (`docs/artifacts/runs/run_all.sh`): unpinned baseline + 14 scenarios,
      `instance_descaled_v2.json.gz`, `--k 14-22 --seeds 0-9`, ~14 min total. Verify 0 unstaffed
      and masses summing to the instance total on every run.
- [ ] §6 — one power-diagram map per scenario at k=18, plus the instance's `opportunity.png` once.
- [ ] §7 — `docs/artifacts/runs/build_artifact.py`: reuse the k-Sweep's stylesheet, embed maps as
      lossless WebP, publish as a **new** artifact (never touch `c007d61d`).
- [ ] §8 — write `docs/RUNS.md` (provenance, validation, region table, artifact URL), commit on
      `wt/runs`, push. **Do not merge to `national-channel` without asking** — the standing rule.
- [ ] Open finding to carry into §7/§8's writeup: at k=18 every region is oversized as a single
      district (k-equivalents 1.13–4.13); this is reported, not resolved by regrouping.
