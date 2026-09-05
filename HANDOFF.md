# Handoff — national channel territory design (`national-channel`, the hub)

**Updated:** 2026-09-05 · **Branch:** `national-channel` — `wt/runs` and `wt/A1` merged in on
2026-09-05 with the user's approval · **Head / Tests:** see the state commit that follows the
merge (expected 222 pass, 0 fail — A1's 222 include every test on both tracks)

**One line:** **The live instance is `instance_descaled_v2.json.gz` at `k = 18`.** The hub now
holds the runs track's 14+1 pin-cost catalogue and HiGHS fix, and the A1 track's wave 1 plus its
v2 re-anchor — **`D1′ is NOT SOFT on the live instance`** (gap 0.725–0.776 nats against the 5e-3
floor, no `δ*`). The two tracks' k=18 draws are byte-identical (compared, not inferred).

## Start here
- **Resume point:** `docs/FRAME.md` §0 — the 2026-09-05 merge entry is the top one; the six
  2026-09-04 entries under it are the two tracks' and the hub's, in commit-time order; §6 carries
  the measured rows (v1 and v2 side by side).
- **Status header:** `CLAUDE.md` (thin — it points here and at FRAME §0).
- **Results of the two tracks:** `docs/RUNS.md` (the catalogue's numbers, the region table, the
  solver-fix writeup; `docs/RUNS_PLAN.md` is the plan it executed) · `docs/MODEL_U8-band.md` +
  `CODEVERIFY_U8-band.md`, `docs/MODEL_U9-bandthm.md` + `VERIFY_U9-bandthm.md` (A1 wave 1, v1) ·
  FRAME §0's 2026-09-04 night entry (A1's v2 re-anchor numbers).
- **Memory:** `~/.claude/projects/-Users-ntlee-projects-td/memory/td-contiguity-programme.md`;
  the merge rule is `ask-before-merging-to-hub.md`.
- **Caution:** run tests with `/Users/ntlee/projects/td/.venv/bin/python3 tests/run_all.py`
  from this worktree (no `.venv` here). Gitignored and hand-copied, so a fresh worktree needs
  them again: `instance_descaled_v2.json.gz` (**live**, cleaned; in `.claude/worktrees/runs`
  and `.claude/worktrees/A1`), `instance_descaled_v2.raw.json.gz` (uncleaned, provenance only;
  runs worktree), `instance_descaled.json.gz` (v1, regression only), `data/geo/`, and
  `battery/results/`: **v2** — `draw_k18_v2_20260904`, `u8_band_v2_20260904`,
  `meas_v2_20260904` (A1 worktree), `runs_20260904/` (the 15 catalogue runs, runs worktree);
  **v1** — `draw_k13_20260901`, `sweep_20260902_s10` (here), `meas_20260903`,
  `u8_band_20260904` (A1 worktree).
- **Solver change (from `wt/runs`):** `td/solvers/centers.py::assign()` pins
  `method="highs-ds"` with `options={"time_limit": 60.0}` instead of the bare `method="highs"` —
  the auto-selecting method (and `highs-ds` with no `options` at all) hangs indefinitely on v2
  under scipy 1.18.1. Verified: 184/184 at the time, v1 regression byte-identical at 8 of 9 k
  (k=9 tie-noise ~3e-6 nats), and A1's unpatched k=18 draw is byte-identical to the patched
  baseline. Full writeup in `docs/RUNS.md`.
- **Background a solver run with `python3 -u`.** `frontier.py` block-buffers stdout to the task
  log, so a 34-minute run showed an empty file throughout; `sample <pid>` was the only way to
  tell which stage it was in.
- **Serena binds to the session's launch directory.** Launch `python-typed` only from a session
  started in the worktree that owns the files, and **activate by *path*** — six registered
  projects are named `td`, so activating by name is a coin flip across checkouts. Confirm with
  `get_current_config` before the first symbol edit.
- **Key docs:** `docs/APPROACHES.md` (§0 "what every track inherits", the A0–A5 charters) ·
  hub stage-2/3 copies `docs/LENS_*.md`, `docs/DOMAIN_*.md`, `docs/BRIEF.md`, `docs/units/U0–U7`
  (neutral, restored from `a4eb488`; they do **not** carry the band material) · **A1's re-runs
  under `docs/tracks/A1/`** (`README.md` there maps the paths; units U8–U13, ★8–★12) · wave 1's
  code: `td/solvers/eg_band.py`, `tools/measure/frontier.py`, `figures/u8_band{,_v2}/frontier.png`
  · `tools/measure/instance_diff.py` · `docs/MODEL_U7-meas.md` + `CODEVERIFY_U7-meas.md`,
  `tools/measure/premium.py` · `docs/MODEL_U1-cert.md` + `VERIFY_U1-cert.md` ·
  `docs/LIT_optimization.md` + `.bib`, `docs/LIT_economic-theory.md` (2026-09-03 section) +
  `LIT_economic-theory_A1.bib` · hub docs `CHANNEL.md`, `MODEL.md`, `DATA.md`,
  `RESEARCH_FINDINGS.md`, `REVIEW_GROMOV.md`.
- **The three measurement CLIs** (v2 forms — these are the live ones):
  `tools/run_draw.py instance_descaled_v2.json.gz --k 18 --seeds 0-9 --workers 8 --out battery/results/draw_k18_v2_20260904` ·
  `tools/measure/premium.py instance_descaled_v2.json.gz battery/results/draw_k18_v2_20260904 --out battery/results/meas_v2_20260904`
  (the premium ladder, U1/U4/U8, verdict conversions) ·
  `tools/measure/frontier.py instance_descaled_v2.json.gz battery/results/draw_k18_v2_20260904 --out battery/results/u8_band_v2_20260904 --figure figures/u8_band_v2/frontier.png`
  (the gate, the `δ` frontier, D1′, `δ*`, first movers, N8/N9, the plot).
  The v1 runs reproduce by swapping the instance and draw back and adding
  `--gate-reference 60.6974156139` to `frontier.py`.
- **The catalogue:** `bash docs/artifacts/runs/run_all.sh` (15 runs, ~14 min), then
  `make_maps.sh` and `build_artifact.py --date <date>`; scenario specs in
  `docs/artifacts/runs/scenarios/`. Note the two shell scripts date their output directory by
  `date +%Y%m%d`, so a re-run lands in `runs_<today>`, not `runs_20260904`.
- **Reproducing the v1↔v2 comparison:**
  `tools/measure/instance_diff.py <old> <new> [--json out.json]` — recovers the descaling
  divisor `K` from the unchanged zips, reports the real per-zip change `f = ratio/K`, the
  composition shift, the saturation decomposition, and what a naive row-sum of opportunity
  would have inflated each export by. Run it on any future instance before trusting a sizing
  figure.
- **Stage-1 figures:** `tools/us_maps.py <instance> --out figures/<dir>/ --districts <draw.csv>
  --regions <draw.csv>` (~3 s per k with the gazetteer cached). It also emits the four base
  figures into `--out`; delete them if you only want the two maps. `--regions` is the power
  diagram; `--regions-voronoi` is the superseded catchment fill.
- **Published artifacts:** Pin-cost catalogue (v2, k=18; `f903ee01-eefc-40cf-bd32-8f5536b6e65f`)
  · Opportunity Map Diff (v1 vs v2; `68eecbb9-3ce2-45d9-8161-5db7fe212957`) · k-Sweep (v1, all
  nine k; `c007d61d-c753-4151-9026-2288b9d5eb38`) · Atlas (v1, 5 maps, certified k=13 draw;
  `1f2cddd9-b98b-4213-83ea-784566147c6a`).

## The instance (settled: user, 2026-09-04)

≈$18B is correct and is not to be re-derived; **v2 supersedes v1 and `k = 18`**. Measured:

| | `instance_descaled.json.gz` (v1, all of wave 1) | `instance_descaled_v2.json.gz` (**live**) |
|---|---|---|
| zips | 1,229 | **3,748** — v1 is a strict subset (the raw export had 3,749; the `BLANK` pseudo-zip was dropped) |
| reps | 111 | **114** (all 111 retained) |
| contested / uncontested / vacant / untapped | 675 / 477 / 2 / 75 | **718** / 1,447 / 16 / **1,567** |
| untapped share of opportunity | 2.9% | **15.7%** |
| aggregate saturation | 41.6% | **29.6%** |
| total, real (v1 units) | 2,745.6 | 5,165.6 — **×1.8814** (8,523.2 in v2's own units) |

**Read the growth carefully.** ×1.8814 over all opportunity but only **×1.6333 over worked
zips**, and the **contested set — the part A1 optimises — grew only 675 → 718**. v2's gain is
overwhelmingly *untapped* market. Consequences: v1's true total was ≈$9.6B, so its `k = 13` was
overstated (consistent `k` ≈ 10) and the k=13 draw, atlas and seed-3-vs-seed-9 question are v1
history; `REVIEW_GROMOV` R1's premium arithmetic, built on 41.9% saturation, is stale at 29.6%.

## What the two tracks say together (FRAME §0, 2026-09-05)

One instance, one `k`, one draw — so one nats scale. Balance is free (`δ₀ ≈ 1%`; widening the
band 33-fold buys back 0.051 nats). The incumbency premium is **0.72–0.78 nats and not soft**.
The roster is worth **0.249 nats** (v1: 0.043). Hand-drawing a region as one district costs on
balance **0.008 (CAROLINAS) to 2.04 (CALIFORNIA) nats** — pinning CALIFORNIA costs ~3× the
whole premium; CAROLINAS / SOUTHWEST / FLORIDA pins each cost less than the roster gap, and
FLORIDA `fix` / CAROLINAS `anchor` out-staff the baseline at stage 2 (+0.029 / +0.012).

## Starting a track (A2–A5, or resuming A1)
1. `git worktree add /Users/ntlee/projects/td/.claude/worktrees/<ID> -b wt/<ID> national-channel`.
2. Hand-copy the gitignored inputs: `instance_descaled_v2.json.gz` and `data/geo/` (from the
   runs or A1 worktree), `battery/results/draw_k18_v2_20260904/`,
   `battery/results/meas_v2_20260904/`, `battery/results/u8_band_v2_20260904/` (A1 worktree),
   and `battery/results/runs_20260904/` if the catalogue is needed (runs worktree). v1 inputs
   only for a regression.
3. Start `claude` **from that directory**, and activate Serena to it **by path**.
4. Read `docs/APPROACHES.md` §0's inherited facts and FRAME §6 before the charter; ★6 is lifted.
5. Write the track's `/gromov`, `/domain` and `/research-plan` outputs under `docs/tracks/<ID>/`
   (pass the path as the skill argument); never overwrite the hub copies at `docs/`.
6. Commit on `wt/<ID>`; ask before merging. Facts, code and verified unit results merge promptly;
   the track's lens/domain/brief stay under `docs/tracks/<ID>/` until it wins or dies.

## Next actions
- [x] **★12 — merged.** `national-channel` fast-forwarded to `wt/A1` at `8546de6` on 2026-09-03.
- [x] **Stage-1 sweep fully mapped** (`b3931fa`, 2026-09-04; v1).
- [x] **`wt/runs` + `wt/A1` merged** into `national-channel` on 2026-09-05 (user approved);
      three state files reconciled by hand, zero code conflicts. Future track work still asks
      before merging.
- [x] ~~Draw v2 at k = 18; re-run the frontier and the premium ladder on v2.~~ Done on `wt/A1`
      (FRAME §0, 2026-09-04 night): `δ₀ = 0.009970`, `V = 95.755191659241`, `EG_{S₁₈} =
      96.532152`, D1′ NOT SOFT at every `δ`, no `δ*`; ladder 41.53 / 41.53 / 54.42 / 59.27 /
      84.17 % of book, match gap 0, map gap 0.663, roster gap 0.249 nats.
- [ ] **The sponsor's call this catalogue exists to inform: which states, if any, are
      hand-drawn** (A12). `docs/RUNS.md`'s region table is the price list, now in the same nats
      as the premium ladder (above).
- [ ] **Wave 2** (user-gated) — U10-round, U11-roster, U4-disp, and U13-base. Briefs at
      `docs/tracks/A1/units/`; U11 reuses `eg_band.py` as its solver. **Re-read the briefs first:
      they are written against v1 assumptions.** **U11-roster's priority is now higher than its
      brief assumes** — the roster gap grew 0.043 → 0.249 nats (5.8×) from v1 to v2. Then wave 3,
      U12-menu (needs U8 + U11 + U13).
- [ ] **★11 — rewrite A1's charter step 3** in `APPROACHES.md` from "rep-indexed MINLP" to
      "roster enumeration over band-constrained EG programs". A hub edit; U8 has reported, so it
      is unblocked. `collapsed-on-softness` does **not** fire — the premium is not soft.
- [ ] **Source-document corrections wave 1 implies** (hub files, user-gated):
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
      second knob `ε`. **Evidence on v2:** the frontier rises only 0.0513 nats across a 33-fold
      widening of `δ` (v1: 0.077 across 84-fold), so the choice is nearly free on value grounds —
      a governance question, not a trade-off.
- [ ] **★10** — tie-break policy (disclose vs randomise), on U11's evidence; `S₁₃`'s margin was
      8.1e-3 nats on v1 seed 9 — re-measure on `S₁₈`.
- [ ] **Still to re-measure on v2 before quoting:** the (★) roster-free screen (v1: 60.8025,
      0.865 nats over the delivered draw), and R1's saturation-driven premium arithmetic
      (saturation is 29.6% on v2 and the ladder is in hand). FRAME §6 rows carry both v1 and v2
      where measured; anything still v1-only is marked as such.
- [ ] `td/solvers/centers.py`'s HiGHS fix has an unexplained root cause (a scipy 1.18.1 /
      HiGHS option-merging quirk) — not chased further than confirming the fix is narrow and
      correct. Worth a scipy/HiGHS upstream bug report if this recurs elsewhere.
- [ ] Carried: ★1 (are the 98 released), ★2 (audited book — now a data-quality question only),
      ★3 (stability as a criterion, after U6-sel), ★5 (least core), ★7 (`/domain econometrics`).
      **U3-inv is retired** (user, 2026-09-04) — books are measured from the data warehouse, not
      self-reported, so the strategy-proofness question has no referent.

**Queued fixes / known-stale.**
- [ ] `REVIEW_GROMOV` R1 — `docs/channel_note/ceiling.py:75` still hard-codes `SATURATION = 0.05`
      against a measured 41.9% (v1) / 29.6% (v2), and `channel_note` §5.1 carries the old
      arithmetic; the rename pass *certified → balance-certified*.
- [ ] `docs/MODEL_U8-band.md` §5.1's `ĝ > 0` guarantee is now scoped to finite `δ`; the
      `delta=None` path is guarded by an explicit per-iterate check (`CODEVERIFY` row 1). §5.2's
      SCIP tie-break rule should be narrowed to "SCIP is a cross-check, not a source of the
      reported bound" (`CODEVERIFY` F7). The v2 re-run of U8 has not been through `code-verify`.
- [ ] Doc nits recorded in FRAME §0's merge entry: A1's v1 frontier table mislabels the D1′
      one-solve bounds as direct gaps; `docs/RUNS.md` reports deltas only; `build_artifact.py`
      asserts none of `RUNS_PLAN.md` §7's checks.
- [ ] Hub items still open: certificates 1–4 not adapted to anchored draws; palette at k ≥ 13
      (`SOUTHWEST` and `D07` shared a hue at k=13; unverified at k=18). The seed-3 vs seed-9 k=13
      map decision is **superseded** by k = 18.
