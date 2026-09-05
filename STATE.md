# State — national channel territory design

**Updated:** 2026-09-05 · **Branch:** `wt/w2-phase0` (5 commits, **unmerged, unpushed**) ·
**Head:** `3e59445` · **Tests:** 237 pass, 0 fail (2026-09-05)

## Now

**Wave 2 Phase 0 and Phase 2 are executed and committed on `wt/w2-phase0`** — five commits on
`9cfcc2c`, 237 tests pass (222 baseline + 15 new from P2-B), branch **unmerged and unpushed**.
Phase 1's four units are not launched; Phase 0 no longer blocks them.

*What landed.* `3b968de` **P0-A**: 0a's eight source corrections; 0b rewrote A1's charter to
roster enumeration over band-constrained EG programs, touching **12 sites** because `:44`,
`:109`, `:388` all claimed "one solve"; 0d withdrew `fotakis2014`; 0c re-anchored five briefs.
`2d472de` **P0-B**: `MODEL_U8-band` §10 for v2, §9 kept byte-identical as v1 history, plus
`CODEVERIFY_U8-band-v2.md`. `8b7123b` **P0-C**: `B_tot` emitted from `premium.py::measure()`,
(★) recomputed, `SATURATION` → 29.6 %, `channel_note` §5.1 retracted; `VERIFY_P0C-screen.md`.
`4a724d6` **P2-A**, `3e59445` **P2-B**.

*What the verifiers refuted* — seven claims, two of which would have shipped wrong numbers:

- **The (★) screen direction was backwards.** The plan's `0.064 → 0.261` pairs v1's `P_S` slack
  against v2's `P₁₈`. On `P_S` — U11's actual per-roster prune — slack goes `0.0641 → 0.0219`:
  it **TIGHTENS 2.9×**. The loosening is real but lives on `P_k`, the roster-free bound.
- **`Σᵢgᵢ = B_tot + w·P₀` is NOT an independent oracle** (`WAVE2_PLAN.md:320` overstates it). It
  is one sum rearranged: doubling `free_book` in both paths leaves it passing while `B_tot`
  moves. `B_tot` is verified instead by independent transcription (Δ = 0.0e+00).
- **`MODEL_U8-band` §5.1's gate gains.** Not ≈206 (that is `mean(g_delivered)`); measured
  211.786–228.663. Conclusion survives: min clears the 140.638 floor by 1.506×.
- `channel_note` §5.1 had inherited v1's `D(g)`; true value **0.148 nats**, and the 1e-4–1e-2
  range is `D(M)`. The 30 % threshold is **not** crossed at 29.588 %, so the passage now rests
  on the measured 0.890-nat window. Inversion holds at **6.0×**, not orders of magnitude.

*What it means.* ★8 was executed **removal only**: `fotakis2014` withdrawn at all seven sites,
Gibbard–Satterthwaite withdrawn too (no citation exists anywhere in the corpus), **nothing put
in its place** — the invariant has no cited basis and stands as a prudential design choice, with
the misreporting exposure explicitly preserved. P2-B **established** cert 1's residual-targets
equivalence by KKT proof plus 4,000-case numeric check, and **refused** `WAVE2_PLAN`'s literal
cert-2 instruction after measuring that both inherited symmetry breaks cut off the optimum.

*What's next.* **Decide whether `wt/w2-phase0` merges to `main`** — the wave-2 decision said
verified tracks auto-merge *this batch only*, but nothing has merged and the push was refused by
the auto-mode classifier. Then launch Phase 1's four units.

## Next

- [ ] **Merge `wt/w2-phase0` into `main`?** Five commits, 237 tests green, every track through
      its verifier. The wave-2 decision said verified tracks auto-merge **this batch only**, but
      nothing merged. **The push was refused by the auto-mode classifier** — run
      `git push -u origin wt/w2-phase0` from the worktree.
- [ ] **Sponsor's call: which states, if any, are hand-drawn** (A12). `docs/RUNS.md`'s region
      table is the price list, in the same nats as the premium ladder. Separate session.
- [ ] **Phase 1 — the four units**, all concurrent, now unblocked: U10-round, U11-roster, U4-disp,
      U13-base. Then U12-menu (needs U8 + U11 + U13; brief re-anchored, unit not launched).
      Branch from `main` **after** the merge above, or from `wt/w2-phase0`.
- [ ] **★8 has no cited basis and that is now the record.** Grounding it needs a `lit-search`;
      deliberately deferred. If a sponsor conversation ever leans on "books enter at stage 2
      only", the gap becomes load-bearing.
- [ ] **U11's v2 Nash-tie margin was never measured.** `WAVE2_PLAN` said it would be; no number
      exists. U13's TX share (11.5 %) is likewise v1-only, on 1,229 zips. Both are flagged in the
      briefs rather than filled with invented numbers.
- [ ] **Serena binds to the hub, not the worktree.** Three agents hit this today; one nearly wrote
      to the user's checkout, one filed a false bug report against a landed correction, one got
      stale *content* (not just line numbers). Relative paths resolve against
      `/Users/ntlee/projects/td`. Use absolute worktree paths, or `Read`.
- [ ] **Something injects shell-IO instructions that contradict `CLAUDE.md` §7.** Two agents
      independently reported being told mid-session to use `cat`/`sed`/heredocs; both declined,
      and the hook caught the one attempt. An agent that complied would bypass the hook.
- [ ] **`D04`/`SOUTHWEST` share a colour and look adjacent** in `SOUTHWEST_anchor`. B10's recorded
      `SOUTHWEST`/`D07` collision was **refuted** (different colours in both maps, so it describes
      the k=13 run). This different pair may be the real failure. `RUNS_PLAN.md:294-298` forbade
      widening scope, so it is reported only.
- [ ] `chOppShare` prints 59.1 or 59.2 depending on whether `ceiling.py:75` stores `SATURATION`
      at 3 s.f. — a rounding-order artefact quoted at `channel_note.tex:502`, not a wrong
      measurement.
- [ ] **★9** the sponsor's `δ` as U12's menu with **★4** `ε` · **★10** tie-break policy on U11's
      evidence · carried ★1 ★2 ★3 ★5 ★7. (★8 and ★11 landed; U3-inv retired.)
- [ ] **Bibliography gap:** `kawase2026balanced`, `borgwardt2019`, `fotakis2014` all resolve but
      live only in the per-domain `.bib` files — none is in
      `docs/math_note/territory_bibliography.bib` (78 entries), and there is no `.md`/`.csv`
      sibling, so the three-format sync is unsatisfied. P0-A's corrections cite all three.
- [ ] `caveman` proxy: `caveman setup --install` was blocked by the auto-mode classifier on
      2026-09-05 — the user runs it, then `caveman claude`.
- [ ] Deferred: HiGHS root cause (scipy 1.18.1 option merging) only if it recurs; `ceiling.py`'s
      remaining v1 content beyond `SATURATION`; `CLAUDE.md`'s `TD_SLOW=1` line, which advertises
      a slow tier no test module populates; `DOMAIN_optimization` §2.14/§3's `C(111,13)` pool,
      left because no v2 rep-pool count is established and `P₁₃`/`S₁₃` are programme-wide names.

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

**Measured in Phase 0 (2026-09-05), all through a verifier.** `B_tot = 3268.4069219934404`
(`premium.py::measure()`, eq. `decomp`'s `W₀`). (★) screen: `96.554063` at `P_S`, `96.793010` at
`P₁₈`. Slack over `EG_{S₁₈}`: **0.0219 at `P_S`** (v1 0.0641 — the screen **tightens 2.9×** on
U11's per-roster prune) and 0.2609 at `P₁₈` (v1 0.1051 — the roster-free `P_k` rung loosens
2.5×). **Do not compare across rungs.** `D(g) = 0.148` nats on the delivered draw; `D(M) = 1.5e-4`
at a 1.37 % mass spread; realised *gain* spread 60.17 %. Premium window **0.890** nats exact
(0.912 is the first-order sum; the 0.022 gap is 4.5× the tier-2 floor), inverting `D(g)` by
**6.0×**. Saturation `ΣT/ΣM = 29.588 %`. Splits at `δ₀`: a-priori cap 35, sharp `k−1+t` cap 33
(t = 16), **measured 24** — quote the measured count, never the cap. Gate gains run
`211.786–228.663` (16 of 18 near 211.79), clearing the `140.638` floor by 1.506×.

Solver: `assign()` pins `method="highs-ds"` with `options={"time_limit": 60.0}` — the bare
`highs` call hangs on v2 under scipy 1.18.1. Background solver runs with `python3 -u`
(`frontier.py` block-buffers). **Serena resolves relative paths against the hub
`/Users/ntlee/projects/td`, not the active worktree** — pass absolute worktree paths, or use
`Read`; three agents were misled by this on 2026-09-05, one nearly writing to the user's checkout.

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
