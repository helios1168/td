# State — national channel territory design

**Updated:** 2026-09-05 · **Branch:** `main` (the hub; new `wt/*` tracks branch from it) ·
**Head:** the wave-2 plan commit on top of `352b9d7` · **Tests:** 222 pass, 0 fail (2026-09-05)

## Now

**Wave 2 is planned but not executed.** `docs/WAVE2_PLAN.md` (this commit) is the execution
plan — 9 tracks in 3 phases, with per-track model assignments, worktree names and merge order.
Nothing in it has run: no unit launched, no correction applied, no re-measure taken. The tree is
otherwise unchanged from `352b9d7` — 222 tests, live instance at k=18.

*What the planning found.* Three things filed as cleanup actually **gate** the units, which is
why the plan is phased rather than a flat fan-out:

- **`MODEL_U8-band.md` was never re-anchored to v2, and its v2 re-run was never verified.** Its
  whole §9 is k=13; `82dbe98` wrote only data — the gitignored manifest, one tracked figure, and
  the headlines in `## Facts`. Wave 2 would consume a verified v1 document beside an unverified
  v2 manifest, so U8's v2 `code-verify` is a prerequisite (P0-B), not a loose end.
- **The wave-2 briefs are v1 artifacts, and two units' premises moved.** U4-disp's first-mover
  tie set went from 75 exact ties (2.90 % of `T`) to `n_exact_ties = 0`; U10-round's acceptance
  #2 is unsatisfiable as written, demanding a SCIP vertex that `CODEVERIFY_U8-band` F7 narrowed
  to a cross-check `certified_upper` never adopts.
- **The (★) roster-free screen has no implementation.** It was arithmetic in a docs-only commit
  (`795ea8e`); `60.8025` survives only as a display literal at
  `docs/artifacts/U9-bandthm/bandthm.py:957`. Its primitive `B_tot` is emitted by no tool, and
  U11's branch-and-bound stop rule depends on it.

*Four corrections to this file's own record*, all folded into the plan: the `borgwardt2019`
downgrade belongs to `LIT_optimization.md` §8, **not** `DOMAIN_optimization` §8 (slip inherited
from `VERIFY_U9-bandthm.md:419`); N7's defect is that it grids on the **spread**, and the fix is
to grid on `δ₀`; the two `MODEL_U8-band` §5.1/§5.2 fixes already landed in `ddd162d` / `ed5a9a8`,
leaving only a small residue; and `TD_SLOW=1` adds nothing — no test module has set `SLOW = True`
since the `acfdbfe` prune, so the slow tier `CLAUDE.md` advertises does not exist.

*What it means.* A fresh session can execute wave 2 from `docs/WAVE2_PLAN.md` without
reconstructing any of the above. The user's four planning decisions are recorded there
(all 4 units concurrent · U13 parameterised on A12 · all loose-end groups in scope · verified
tracks auto-merge, **this batch only**).

*What's next.* Execute **Phase 0** — it gates everything else. The one decision still
outstanding is the sponsor's hand-drawn-states call (A12), being taken in a separate session.

## Next

**`docs/WAVE2_PLAN.md` owns the wave-2 rows below** — it carries the per-track file lists, line
numbers, evidence citations, model assignments and merge order. Execute in phase order.

- [ ] **Sponsor's call: which states, if any, are hand-drawn** (A12). `docs/RUNS.md`'s region
      table is the price list, in the same nats as the premium ladder. Separate session.
- [ ] **Phase 0 — gates everything.** `wt/w2-inputs` (source-doc corrections → ★11 → ★8 → brief
      re-anchor, in that order) · `wt/w2-u8close` (MODEL_U8-band v2 section + residue, then
      `code-verify` the v2 re-run) · `wt/w2-screen` (emit `B_tot` from `premium.py`, recompute
      the (★) screen, `ceiling.py` saturation, `channel_note` §5.1).
- [ ] **Phase 1 — the four units**, all concurrent: U10-round, U11-roster (roster gap 0.043 →
      0.249 nats), U4-disp, U13-base. Then U12-menu (needs U8 + U11 + U13; its brief is
      re-anchored in Phase 0 but the unit is not launched).
- [ ] **Phase 2 — loose ends**, independent: `wt/w2-fixes` (`math_note/toy_*.py` broken imports;
      `RUNS.md` absolute baseline; `build_artifact.py` assertions; palette **check**, not fix —
      `RUNS_PLAN.md:294-298` says do not widen scope) · `wt/w2-cert` (certificates 1–4 for
      anchored draws — soundness-bearing, the pin-cost catalogue rests on it).
- [ ] **★9** the sponsor's `δ` as U12's menu (frontier rises 0.051 nats over a 33× widening —
      governance, not value) with **★4** `ε` · **★10** tie-break policy on U11's evidence ·
      carried ★1 ★2 ★3 ★5 ★7. (★8 and ★11 are Phase 0; U3-inv retired.)
- [ ] **Bibliography gap:** `kawase2026balanced`, `borgwardt2019`, `fotakis2014` all resolve but
      live only in the per-domain `.bib` files — none is in
      `docs/math_note/territory_bibliography.bib` (78 entries), and there is no `.md`/`.csv`
      sibling, so the three-format sync is unsatisfied. Phase 0's corrections cite all three.
- [ ] `caveman` proxy: `caveman setup --install` was blocked by the auto-mode classifier on
      2026-09-05 — the user runs it, then `caveman claude` (plan:
      `~/.claude/plans/help-me-simplify-and-splendid-turtle.md` C6).
- [ ] Deferred, not in the plan: HiGHS root cause (scipy 1.18.1 option merging) only if it
      recurs; `ceiling.py`'s remaining v1 content beyond `SATURATION`; `CLAUDE.md`'s `TD_SLOW=1`
      line, which advertises a slow tier that no test module populates.

## Facts

| | v1 `instance_descaled.json.gz` (regression only) | **v2 `instance_descaled_v2.json.gz` (live)** |
|---|---|---|
| zips | 1,229 | **3,748** (strict superset; raw had 3,749, `BLANK` dropped) |
| reps | 111 | **114** (all 111 retained) |
| contested / uncontested / vacant / untapped | 675 / 477 / 2 / 75 | **718** / 1,447 / 16 / **1,567** |
| untapped share of opportunity | 2.9 % | **15.7 %** |
| aggregate saturation | 41.6 % | **29.6 %** |
| total (v1 units) | 2,745.6 | 5,165.6 — ×1.8814 (8,523.2 in v2 units); v1's "$13B" was ≈$9.6B |
| k at $1B | 13 (overstated; consistent ≈10) | **18** |

v2's growth is untapped market: ×1.6333 over worked zips, contested only 675 → 718.

**One nats scale, one instance, one draw (k=18 seed 2, `δ₀ = 0.009970`, `V = 95.755192`,
`EG_{S₁₈} = 96.532152`).** Balance is free (widening the band 33-fold buys 0.051 nats). The
incumbency premium is **0.72–0.78 nats and NOT SOFT** (D1′: 146–155× the 5e-3 floor, no `δ*`).
The roster is worth **0.249 nats** (v1 0.043). Match gap 0, map gap 0.663. Pinning a region
costs **0.008 (CAROLINAS) to 2.04 (CALIFORNIA) nats** — CALIFORNIA ≈ 3× the whole premium;
FLORIDA `fix` / CAROLINAS `anchor` out-staff the baseline at stage 2 (+0.029 / +0.012).
Premium ladder v2: `P₀` 41.53 %, `P_S` 54.42 %, `P₁₈` 59.27 %, `P_free` 84.17 % of book.

Solver: `assign()` pins `method="highs-ds"` with `options={"time_limit": 60.0}` — the bare
`highs` call hangs on v2 under scipy 1.18.1. Background solver runs with `python3 -u`
(`frontier.py` block-buffers). Activate Serena by *path*.

## Where

- `docs/CHANNEL.md` — the problem, the two stages, sizing · `docs/MODEL.md` — the N-way model
  and open decisions (§6) · `docs/FRAME.md` — problem statement (§6 measured rows, §9 settled/open)
- `docs/APPROACHES.md` — §0 what every track inherits, charters A0–A5 · `docs/BRIEF.md` +
  `docs/units/` — A1's plan, units U0–U13 · `docs/LENS_*.md`, `docs/DOMAIN_*.md`, `docs/LIT_*` —
  A1's (promoted) lenses, domain plans, literature
- `docs/RUNS.md` (+ `RUNS_PLAN.md`) — the pin-cost catalogue · `docs/MODEL_U8-band.md`,
  `CODEVERIFY_U8-band.md`, `MODEL_U9-bandthm.md`, `VERIFY_U9-bandthm.md` — wave 1 ·
  `MODEL_U7-meas.md`, `MODEL_U1-cert.md` (+ verifies) — the measurements · `docs/DATA.md`,
  `docs/RESEARCH_FINDINGS.md`, `docs/REVIEW_GROMOV.md` — data route, literature map, R1–R4
- `docs/WAVE2_PLAN.md` — the wave-2 execution plan: 9 tracks, 3 phases, per-track files, model
  assignments, merge order, and the four corrections to this file's record
- Recipes and file map: `docs/CODE_MAP.md` · Memory:
  `~/.claude/projects/-Users-ntlee-projects-td/memory/td-contiguity-programme.md` · History:
  `docs/STATE_LOG.md` · Archive: `docs/archive/README.md`
- Artifacts: pin-cost catalogue `f903ee01-eefc-40cf-bd32-8f5536b6e65f` · map diff
  `68eecbb9-3ce2-45d9-8161-5db7fe212957` · k-sweep (v1) `c007d61d-c753-4151-9026-2288b9d5eb38` ·
  atlas (v1) `1f2cddd9-b98b-4213-83ea-784566147c6a`
- Starting a track: `git worktree add .claude/worktrees/<ID> -b wt/<ID> main`; hand-copy the
  gitignored inputs (`docs/CODE_MAP.md` lists them); start `claude` there and activate Serena
  by path; read `APPROACHES.md` §0 and FRAME §6; write the track's lens/domain/brief under
  `docs/tracks/<ID>/`; commit on `wt/<ID>`; ask before merging.
