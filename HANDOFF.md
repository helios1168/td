# Handoff — national channel territory design / A1 track (`wt/A1`)

**Updated:** 2026-09-04 (night) · **Branch:** `wt/A1` (worktree `.claude/worktrees/A1`) ·
**Head:** `82dbe98` · **Tests:** **222 pass, 0 fail** (218 + 4 from `test_frontier`, run
2026-09-04 at `82dbe98` in this worktree)

**One line:** **The v2 re-anchor is done — `D1′ is NOT SOFT on the live instance`** (v2 at
`k = 18`, roster `S₁₈`: gap 0.725–0.776 nats against the 5e-3 floor, no `δ*`). The draw, the
frontier and the premium ladder have all been re-run on `instance_descaled_v2.json.gz`; wave 2 is
unblocked. The merge into `national-channel` remains user-gated.

## Start here
- **Resume point:** `docs/FRAME.md` §0 (the 2026-09-04 entry; §6 has the measured rows)
- **Status header:** `CLAUDE.md`
- **Memory:** `~/.claude/projects/-Users-ntlee-projects-td/memory/td-contiguity-programme.md`;
  the merge rule is `ask-before-merging-to-hub.md`
- **Caution:** run tests with `/Users/ntlee/projects/td/.venv/bin/python3 tests/run_all.py`
  from this worktree. `instance_descaled.json.gz`, **`instance_descaled_v2.json.gz` (the live
  one)**, `data/geo/` and `battery/results/` (**`draw_k18_v2_20260904`, `u8_band_v2_20260904`,
  `meas_v2_20260904`** on v2; `draw_k13_20260901`, `sweep_20260902_s10/k13`, `meas_20260903`,
  `u8_band_20260904` on v1) are gitignored and were hand-copied in or regenerated; a fresh
  worktree needs them again. v2 came from
  `/Users/ntlee/projects/td/.claude/worktrees/runs/instance_descaled_v2.json.gz`.
- **Background a solver run with `python3 -u`.** `frontier.py` block-buffers stdout to the task
  log, so a 34-minute run showed an empty file throughout; `sample <pid>` was the only way to
  tell which stage it was in.
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
- **Reproducing the v1↔v2 comparison:**
  `tools/measure/instance_diff.py <old> <new> [--json out.json]` — recovers the descaling
  divisor `K` from the unchanged zips, reports the real per-zip change `f = ratio/K`, the
  composition shift, the saturation decomposition, and what a naive row-sum of opportunity
  would have inflated each export by. Every number in FRAME §0's 2026-09-04 entry comes from
  it. Run it on any future instance before trusting a sizing figure.
- **The three CLIs** (v2 forms — these are the live ones):
  `tools/run_draw.py instance_descaled_v2.json.gz --k 18 --seeds 0-9 --workers 8 --out battery/results/draw_k18_v2_20260904` ·
  `tools/measure/premium.py instance_descaled_v2.json.gz battery/results/draw_k18_v2_20260904 --out battery/results/meas_v2_20260904`
  (the premium ladder, U1/U4/U8, verdict conversions) ·
  `tools/measure/frontier.py instance_descaled_v2.json.gz battery/results/draw_k18_v2_20260904 --out battery/results/u8_band_v2_20260904 --figure figures/u8_band_v2/frontier.png`
  (the gate, the `δ` frontier, D1′, `δ*`, first movers, N8/N9, the plot).
  The v1 runs reproduce by swapping the instance and draw back and adding
  `--gate-reference 60.6974156139` to `frontier.py`.

## Next actions

**User-gated — reported, not done. Ask before acting on any of these.**
- [ ] **HELD — merge `wt/A1` into `national-channel`?** Now **twelve** commits (the original six
      `954d9eb`, `f199e92`, `69997ac`, `ddd162d`, `ed5a9a8`, `4e5f566`, then `95e25fe`, `4ba7b77`,
      `fd619c7`, `9854fea`, `82dbe98` and this state commit). **The analysis below was done at six
      commits and its shape still holds** — the five since are state files, `tools/measure/`
      additions and one edit to `tools/measure/frontier.py`, a file the hub does not have — **but
      re-run `git merge-tree` before acting on it.** Not a fast-forward: the hub is 3
      ahead of the base `629e3da` (the hub's nine-k sweep maps). `git merge-tree` gives
      **exactly three conflicts — `CLAUDE.md`, `HANDOFF.md`, `docs/FRAME.md` — and zero code
      conflicts**; both sides simply restamped the same state files. Every code change on
      `wt/A1` is an **add**, never a modify (`git diff --name-status` over `td/ tools/ tests/`
      is four `A` lines, no `M`), and the hub's 3 commits touch no code at all — so the stage-1
      draw path is bit-for-bit unchanged and the `runs` plan's byte-identical
      `sweep_20260902_s10` re-run is unaffected. The `td-runs` session confirmed no objection:
      `RUNS_PLAN.md` only *points at* the three conflicted files and quotes no line from them,
      `wt/runs` has touched no code either, and its uncommitted work has zero overlap.
      Resolution when authorised: keep both entries in `FRAME.md` §0's prepend-and-demote chain
      (dated, both belong) and hand-merge the two stamps.
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

**The instance moved, and the question is now settled (user, 2026-09-04).** ≈$18B is correct and
is not to be re-derived; **v2 supersedes v1 and `k = 18`**. Measured directly:

| | `instance_descaled.json.gz` (v1, all of wave 1) | `instance_descaled_v2.json.gz` (**live**) |
|---|---|---|
| zips | 1,229 | **3,748** — v1 is a strict subset |
| reps | 111 | **114** (all 111 retained) |
| contested / uncontested / vacant / untapped | 675 / 477 / 2 / 75 | **718** / 1,447 / 17 / **1,567** |
| untapped share of opportunity | 2.9% | **15.7%** |
| aggregate saturation | 41.6% | **29.6%** |
| total, real (v1 units) | 2,745.6 | 5,165.6 — **×1.8814** |

**Read the growth carefully.** ×1.8814 over all opportunity but only **×1.6333 over worked
zips**, and the **contested set — the part A1 optimises — grew only 675 → 718**. v2's gain is
overwhelmingly *untapped* market. Two consequences: `FRAME.md` §9's old "k = 13" is superseded
(v1's true total was ≈$9.6B, so its consistent `k` was ≈10), and `REVIEW_GROMOV` R1's premium
arithmetic, built on 41.9% saturation, is stale at 29.6%.

*Wave 1 is scoped, not retracted.* U8's manifest pins `instance_sha256 = cf7d66c0…` and
`draw_sha256`, so "NOT SOFT" is a certified fact about **v1 at k = 13, roster `S₁₃`**. The
mechanism is plausibly scale-free — the verdict came from the **level** at `δ₀`, not the slope,
and the contested set barely grew — but that is a hypothesis. Scale is not the obstacle: `n·k`
goes 15,977 → ~67,000 and the OA converged in 15–57 tangents at 1e-9 brackets.
**`td/solvers/eg_band.py` and `tools/measure/frontier.py` are instance-agnostic and need no
change.**

- [x] ~~**1. Draw v2 at k = 18.**~~ **Done** — `battery/results/draw_k18_v2_20260904/k18/`,
      `--k 18 --seeds 0-9 --workers 8`, winner seed 2, 0 unstaffed, masses sum to 8,523.21,
      spread 1.368%, **`δ₀ = 0.009970`**, **`V = 95.755191659241`**. Draws are independent per
      `(k, seed)`, so this is bit-identical to the `k18` slice of `wt/runs`'s `--k 14-22` baseline.
- [x] ~~**2. Re-run the frontier on v2 at k = 18.**~~ **Done** —
      `battery/results/u8_band_v2_20260904/`, `figures/u8_band_v2/frontier.png`. **D1′: NOT SOFT**
      at every `δ` (0.730 / 0.748 / 0.777 nats at `δ = 0.02/0.05/0.10`, 146–155× the 5e-3 floor);
      **no `δ*`** on `[δ₀, 0.33]`; `EG_{S₁₈} = 96.532152`; monotone, concave, all brackets tier-1;
      SCIP `optimal` at both cross-checks, agreeing to `2.3e-9`. The gate was re-pointed in
      `82dbe98` — it now asserts the instance-agnostic `EG_S ≥ V`, with `--gate-reference` as an
      opt-in exact pin (v1 reproduces with `--gate-reference 60.6974156139`).
- [ ] **3. Wave 2** — U10-round, U11-roster, U4-disp — and U13-base. Briefs at
      `docs/tracks/A1/units/`; U11 reuses `eg_band.py` as its solver. **Re-read the briefs first:
      they are written against v1 assumptions.** **U11-roster's priority is now higher than its
      brief assumes** — the roster gap grew 0.043 → 0.249 nats (5.8×) from v1 to v2.
- [ ] **4. Then wave 3, U12-menu** (needs U8 + U11 + U13).
- [x] ~~Re-measure the premium ladder on v2.~~ **Done** — `battery/results/meas_v2_20260904/`.
      `P₀`/`P*(A)`/`P_S`/`P₁₃`/`P_free` = 41.53 / 41.53 / 54.42 / 59.27 / 84.17 % of book; match
      gap **0**, map gap 0.663 nats, **roster gap 0.249 nats**; U1 gains spread 60.17%, U4 124
      zips (7.82% of M), U8 `corr(T,M)` 0.745.
- [ ] **Still to re-measure on v2 before quoting:** the (★) roster-free screen, and R1's
      saturation-driven premium arithmetic (saturation is 29.6% on v2, and the ladder above is now
      in hand). FRAME §6 rows now carry both v1 and v2 where measured; anything still v1-only is
      marked as such.
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
