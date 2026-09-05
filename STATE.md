# State — national channel territory design

**Updated:** 2026-09-05 · **Branch:** `main` (the hub; new `wt/*` tracks branch from it) ·
**Head:** the consolidation commit on top of `3c8a643` · **Tests:** 222 pass, 0 fail (2026-09-05)

## Now

**The live instance is `instance_descaled_v2.json.gz` at `k = 18`** (≈$18B, sponsor-confirmed
2026-09-04, not to be re-derived). `main` became the hub on 2026-09-05: fast-forwarded to
`national-channel` (a strict descendant, 198 commits), that worktree retired, the gitignored
inputs moved to the repo root, `docs/math_note/` restored from `contiguity-harness`. The same
day `wt/runs` and `wt/A1` were merged with the user's approval (three state-file conflicts,
zero code conflicts): the hub carries the 14+1 pin-cost catalogue (`docs/RUNS.md`), the HiGHS
hang fix in `td/solvers/centers.py::assign()`, A1's wave 1 (U8-band, U9-bandthm) and the v2
re-anchor. The merge review established: **the two tracks' k=18 draws are byte-identical**
(`cmp`, not inferred) — A1 drew with the unpatched LP and runs with the patched one, so the
solver fix did not move the draw and every A1 v2 number is directly comparable with the
catalogue's baseline; one nats scale for every lever (see `## Facts`); no contradictions
between the tracks. Verified after the merge: 222 tests; a fresh k=18 seed-2 draw with the
merged solver is byte-identical to A1's `draw_k18_v2_20260904/k18/draw.csv`.

*Later on 2026-09-05 — the tree was restructured for a cheap start-up (this commit):* state
consolidated into this file (CLAUDE.md carries invariants only, `HANDOFF.md` deleted, FRAME §0
back to framing revisions, history in `docs/STATE_LOG.md`); A1's lens / domain plans / brief /
units promoted to the hub paths (neutral copies in `docs/archive/hub-2026-09-02/`, user
decision); `TEST_PLAN`, `RESULTS`, `RESEARCH_GUIDE` archived; `docs/CODE_MAP.md` holds the
file map and run recipes; Serena indexes markdown (marksman) and its memories collapsed to
one; `/state` rewritten around this file; headroom removed, `rtk` installed; pycache-only
fossils deleted. No `td/`, `tools/` or `tests/` behaviour changed (docstring paths only).

*What it means.* One resume point, on the live instance. The k=13 seed-3-vs-seed-9 decision,
the atlas, and `REVIEW_GROMOV` R1's 41.9 %-saturation premium arithmetic are v1 history.
*What's next, all user-gated:* the sponsor's hand-drawn-states call, then wave 2 (see `## Next`).

## Next

- [ ] **Sponsor's call: which states, if any, are hand-drawn** (A12). `docs/RUNS.md`'s region
      table is the price list, in the same nats as the premium ladder.
- [ ] **Wave 2** — U10-round, U11-roster (priority raised: roster gap 0.043 → 0.249 nats),
      U4-disp, U13-base; briefs `docs/units/U8–U13` are written against v1 — re-read first.
      Then U12-menu (needs U8 + U11 + U13).
- [ ] **★11** — rewrite A1's charter step 3 in `APPROACHES.md` to "roster enumeration over
      band-constrained EG programs" (unblocked; `collapsed-on-softness` does not fire).
- [ ] **Source-document corrections wave 1 implies** (user-gated): `DOMAIN_optimization`
      §2.12 first-mover rule REFUTED (use `max_i(u_i/g*_i − ν_i M_z) − 2nd-max`); §2.10 holds at
      `δ = 0` too and `≤ 2k−1` supersedes `≤ 2k`; §2.11 "**a** supergradient — quote
      `(T/k)Σ|ν_i|`"; §8 `borgwardt2019` corroborating only. `DOMAIN_economic-theory` N7 grids on
      the spread not `δ₀`; §2.8 proportionality row refuted, EF1 row per `kawase2026balanced`.
- [ ] **★8** `fotakis2014` scope correction (D6) · **★9** the sponsor's `δ` as U12's menu
      (frontier rises 0.051 nats over a 33× widening — governance, not value) with **★4** `ε` ·
      **★10** tie-break policy on U11's evidence · carried ★1 ★2 ★3 ★5 ★7 · U3-inv retired.
- [ ] Re-measure on v2 before quoting: the (★) roster-free screen (v1: 60.8025, 0.865 nats
      over the draw); R1's saturation-driven premium arithmetic (saturation 29.6 % on v2).
- [ ] `caveman` proxy: `caveman setup --install` was blocked by the auto-mode classifier on
      2026-09-05 — the user runs it, then `caveman claude` (plan: `~/.claude/plans/help-me-simplify-and-splendid-turtle.md` C6).
- [ ] Queued fixes: `docs/channel_note/ceiling.py:75` `SATURATION = 0.05` vs measured 29.6 %
      and `channel_note` §5.1's arithmetic (R1); `MODEL_U8-band` §5.1 `ĝ > 0` scoped to finite
      `δ`, §5.2 SCIP as cross-check only; U8's v2 re-run not through `code-verify`;
      `docs/RUNS.md` reports deltas only; `build_artifact.py` asserts none of `RUNS_PLAN` §7;
      certificates 1–4 not adapted to anchored draws; palette at k ≥ 13; HiGHS root cause
      (scipy 1.18.1 option merging) only if it recurs; `docs/math_note/toy_{grid,path}.py`
      import the deleted `code/gfx` (broken since the prune).

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
