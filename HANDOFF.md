# Handoff — national channel territory design / A1 track (`wt/A1`)

**Updated:** 2026-09-04 · **Branch:** `wt/A1` (worktree `.claude/worktrees/A1`) ·
**Head:** `ed5a9a8` · **Tests:** 208 pass, 0 fail (184 pre-existing + 24 new, run 2026-09-04 at
`ddd162d` in this worktree; `ed5a9a8` is docs-only)

**One line:** A1 wave 1 landed and is verified — **D1′ says the premium is NOT SOFT** on the v1
instance at k = 13. **⚠ EVERYTHING IS ON HOLD** (user, 2026-09-04): a **new instance, 3× larger,
landed the same day** and the sponsor's sizing moved to k ≈ 18, so nothing merges and no unit
launches until the user settles the instance-and-`k` question. **Do not merge. Do not launch
wave 2.**

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
- [ ] **HELD — merge `wt/A1` into `national-channel`?** Six commits (`954d9eb`, `f199e92`,
      `69997ac`, `ddd162d`, `ed5a9a8`, `4e5f566`). **The analysis is done and the merge is
      safe** — it just is not authorised. Not a fast-forward: `wt/A1` is 6 ahead, the hub 3
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

**⚠ HELD — the instance moved under us (user decision, 2026-09-04: "hold everything").**

A new instance landed in `.claude/worktrees/runs/` at 18:26 on 2026-09-04, **while wave 1 was
running**. Measured directly, not taken on report:

| | `instance_descaled.json.gz` (v1, all of wave 1) | `instance_descaled_v2.json.gz` (new) |
|---|---|---|
| zips | 1,229 | **3,748** (3.05×) |
| reps | 111 | 114 |
| total descaled `M` | 2,745.6 | **8,523.2** (3.10×) |

The `runs` session reports it as sponsor-confirmed, replacing the $13B / k ≈ 13 assumption with
**k ≈ 18**, and describes it as "cleaned of one bad data node" — but the size change is the
headline, and the dollar figures cannot be checked from here (descaling removes the scale by
design). **`FRAME.md` §9's "k = 13 at a $1B target — settled" and assumption A1 are reopened.**

*What this does and does not do to wave 1.* It does **not** invalidate it: U8's manifest pins
`instance_sha256 = cf7d66c0…` and `draw_sha256`, so "NOT SOFT" is a certified fact about **v1 at
k = 13, roster `S₁₃`**. It is not yet a fact about v2 at k ≈ 18. The mechanism is *plausibly*
scale-free — the verdict came from the **level** at `δ₀`, not the slope — but that is a
hypothesis, not a result. Scale is not the obstacle: `n·k` goes 15,977 → ~67,000 and the OA
converged in 15–57 tangents at 1e-9 brackets; what changes is every *number* (`δ₀`, `V`,
`EG_S`, and the roster itself, 13 of 111 → ~18 of 114).

- [ ] **HELD — wave 2 (U10-round, U11-roster, U4-disp) and U13-base.** Technically unblocked by
      the D1′ verdict, deliberately not launched: three units against a possibly-superseded
      instance is waste. Briefs at `docs/tracks/A1/units/`; U11 reuses `eg_band.py`.
- [ ] **HELD — wave 3, U12-menu** (needs U8 + U11 + U13).
- [ ] **The decision that unblocks all of it:** does v2 supersede v1, and is `k ≈ 18` settled?
      A sponsor question. When answered, the cheapest first move is **one re-run of
      `tools/measure/frontier.py` on v2 at the new `k`** — a single solve re-tests whether NOT
      SOFT survives and re-anchors every downstream number before any wave-2 unit is spent.
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
