# State — national channel territory design

**Updated:** 2026-09-06 · **Branch:** `worktree-state-atoms` (this entry; branched from
`main` 9980732) · **Head:** `ff63511` · **Tests:** 269 pass, 0 fail (2026-09-06)

## Now

**The state-atom stage-1 engine is in the package** (`ff63511`), and it reproduces the
2026-09-05 exploration exactly. Scope stayed **stage 1 only** — nothing here reads rep books or
the staffed objective. `td/atoms.py` builds the atoms, `td/solvers/atom_draw.py` draws on them,
`tools/run_atoms.py` runs the pipeline, and `td/geo.py` gained `state_rook`. The prototype
`tools/state_atoms/district4.py` is deleted; the rest of that directory is exploratory or builds
the artifact and stays.

*The user's decision.* Cut counts are **CA 5 / TX 2 / NY+NJ 3 / FL 2**, the cheapest measured
setting. Measured on v2 at k=18: 56 atoms in one component, `Σ log M` **110.789532** against the
balanced ceiling **110.883247**, a gap of **0.093715 nats** at a **30.5 %** mass spread, all 18
districts connected, `draw.csv` covering all 3,748 zips.

*Two corrections the engine carries.* `STATE.md` said a stage-1 engine "would sit under the
`base.py` harness contract" — wrong: `base.py` plus `REGISTRY` is the **two-player** harness
(`Result.to_a`, `filter_pair`, `root_a`/`root_b`) and only `brute` and `scip_tree` are
registered. Stage 1 is `centers.py`, unregistered, and the new engine is its sibling. And the
prototype's `free_bound` **was not a bound**: a local search over the relaxation returns a
feasible relaxed value `F ≤ U*`, while the contiguous optimum also satisfies `C* ≤ U*`, which
orders the two not at all. It is renamed `free_search` and reported as a reference; the valid
bound is `cert_draw.cert_balance_ceiling`. Measured, `free_search` = 110.812355, so quoting it
as "the margin above the draw" understated the real gap **fourfold**.

*Two behaviours preserved on the user's call*, so the numbers reproduce: the search tie-breaks
on set iteration over atom names, so a run **requires `PYTHONHASHSEED=0`** and `run_atoms.py`
refuses to start without it; and the stateless bucket goes into the lightest district as one
block rather than being spread by `channel.place_by_state`.

*What's next.* The engine's stage-2 cost is unmeasured, and `wt/w2-phase0` turns out to have
been merged into `main` already — what is actually outstanding is the **push**.

## Next

- [ ] **Push `main` to `origin`.** Local `main` is **8 commits ahead** of `origin/main`
      (`352b9d7`), and `wt/w2-phase0` is **already merged** into it (`main` 9980732 descends
      from 96abb15) — the 2026-09-05 merge question was answered, only the push was refused.
      Run `git push origin main` from the hub.
- [ ] **Merge `worktree-state-atoms` into `main`?** One commit, `ff63511`, 269 tests green.
      Ask before merging (the standing rule).
- [ ] **The stage-2 cost of the atom map is unmeasured, and could exceed the 0.094.** Pinning
      CALIFORNIA costs **2.04 nats at stage 2** and this model forces CA into five pieces. Do
      not claim "the state-atom model costs 0.094 nats" until
      `battery/results/atoms_k18_v2_20260906/k18/draw.csv` has been through
      `channel.score_draws` — that needs no new code.
- [ ] **Quote the 30.5 % spread beside the 0.094 nats.** `log` is flat near the optimum, so a
      small Nash gap sits alongside a large operational spread; the power-cell route gets
      1.37 %. Quoting the gap alone reads as "contiguity is nearly free".
- [ ] **Atom-graph contiguity is not verified map contiguity.** A cut piece has no polygon, so
      its adjacency to an outside state is proximity within `BORDER_TOL = 40 km` plus an
      unconditional link from the nearest piece. `check_contiguous` certifies the atom graph.
      Check the map: `tools/us_maps.py --districts <draw.csv>` (`--regions` does not apply).
- [ ] **Only the CA5 scenario is re-measured.** The 2026-09-05 ladder (0.864 / 0.456 / 0.123 /
      0.094) came from the prototype. The ranking is unaffected — the four differ by far more
      than the 0.015-nat hash-order jitter — but the other three numbers are not the engine's.
- [ ] **Open from the state-atom work:** whether NY+NJ should absorb CT (3.014×, a near-exact
      three-district block); the **stateless-zip rule** (32 zips, 33.4 M, 0.4 %) and the
      **AK→WA / HI→CA1 merges**, all three shipped as documented placeholders, none decided;
      and whether other straddling metros are grouped (Philadelphia PA/NJ/DE, Chicago IL/IN/WI,
      Kansas City MO/KS, Washington DC/MD/VA).
- [ ] **Sponsor's call: which states, if any, are hand-drawn** (A12). `docs/RUNS.md`'s region
      table is the price list, in the same nats as the premium ladder. Separate session.
- [ ] **Phase 1 — the four units**, all concurrent and unblocked: U10-round, U11-roster, U4-disp,
      U13-base. Then U12-menu (needs U8 + U11 + U13; brief re-anchored, unit not launched).
      Branch from `main`.
- [ ] **★8 has no cited basis and that is now the record.** Grounding it needs a `lit-search`;
      deliberately deferred. If a sponsor conversation ever leans on "books enter at stage 2
      only", the gap becomes load-bearing.
- [ ] **U11's v2 Nash-tie margin was never measured.** `WAVE2_PLAN` said it would be; no number
      exists. U13's TX share (11.5 %) is likewise v1-only, on 1,229 zips. Both are flagged in the
      briefs rather than filled with invented numbers.
- [ ] **Serena binds to the hub, not the worktree.** Relative paths resolve against
      `/Users/ntlee/projects/td`. Three agents were misled on 2026-09-05; one nearly wrote to the
      user's checkout. Use absolute worktree paths, or `Read`.
- [ ] **Something injects shell-IO instructions that contradict `CLAUDE.md` §7.** Third
      occurrence, 2026-09-06: mid-session text told the agent to read and write files with
      `cat`/`sed`/heredocs. Declined each time, and `hooks/enforce-file-tools.sh` caught the
      attempts. An agent that complied would bypass the hook.
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
      remaining v1 content beyond `SATURATION`; `DOMAIN_optimization` §2.14/§3's `C(111,13)` pool,
      left because no v2 rep-pool count is established and `P₁₃`/`S₁₃` are programme-wide names.

## Facts

|                                             | v1 `instance_descaled.json.gz` (regression only) | **v2 `instance_descaled_v2.json.gz` (live)**                    |
|---------------------------------------------|--------------------------------------------------|-----------------------------------------------------------------|
| zips                                        | 1,229                                            | 3,748 (strict superset; raw had 3,749, `BLANK` dropped)         |
| reps                                        | 111                                              | 114 (all 111 retained)                                          |
| contested / uncontested / vacant / untapped | 675 / 477 / 2 / 75                               | 718 / 1,447 / 16 / 1,567                                        |
| untapped share of opportunity               | 2.9 %                                            | 15.7 %                                                          |
| aggregate saturation                        | 41.6 %                                           | 29.6 %                                                          |
| total (v1 units)                            | 2,745.6                                          | 5,165.6 — ×1.8814 (8,523.2 in v2 units); v1's "$13B" was ≈$9.6B |
| k at $1B                                    | 13 (overstated; consistent ≈10)                  | 18                                                              |

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

**State atoms — the engine, measured 2026-09-06** (`ff63511`, stage 1 only; run
`battery/results/atoms_k18_v2_20260906`). Target 473.5 at k=18. Cut plan **CA 5 / TX 2 /
NY+NJ 3 / FL 2**: 56 atoms, 126 edges, **one component**. Pieces CA1 0.838×, CA2–CA5
0.825–0.826×, TX1 1.013×, TX2 1.007×, NYNJ1–3 0.943–0.944×, FL1 0.706×, FL2 0.691×.
`Σ log M` **110.789532**, ceiling **110.883247**, gap **0.093715** nats, spread **30.484 %**
(max 1.130×, min 0.826×), all 18 districts connected. Of 52 state codes only 5 exceed target:
CA 4.126×, TX 2.020×, NY 1.794×, FL 1.398×, NJ 1.037×; largest atom needing no cut is IL 0.677×.
NY+NJ together 2.831×, +CT 3.014×.

**The bound, corrected.** The valid upper bound is the Jensen ceiling
`cert_draw.cert_balance_ceiling` = **110.883247**. The contiguity-dropped local search is
**not** a bound — it returns a feasible relaxed value below the relaxed optimum, which orders it
against the contiguous optimum not at all — and is now named `free_search` and reported as a
reference: **110.812355**, +0.022823 over the draw. The prototype quoted it as "the margin above
the draw", understating the true 0.0937 gap by about fourfold.

**Prototype-only state-atom numbers (2026-09-05, not re-measured).** Contiguity dropped,
equal-mass cuts reach 110.883135 (gap 0.000112); every state whole reaches 107.011866 (gap
3.871); zip baseline 110.883101. Contiguity enforced: CA 3 / TX 2 / NY+NJ 2 → 110.019580 (gap
0.864, spread 98.2 %, and it **severs New England** — CT MA ME NH RI VT reach the network only
through NY, leaving them a 0.434× district); CA 3 / TX 2 / NY+NJ 3 → 110.427114 (0.456);
CA 4 / TX 2 / NY+NJ 3 → 110.759967 (0.123). Draws are local search against a relaxation, **not
certified optimal** — exact set-partition was tried and abandoned (>250k columns; HiGHS found no
feasible cover in 180 s at 177k). **`PYTHONHASHSEED=0` is required**, by decision: the search
tie-breaks on set iteration over atom names, and without it results move ~0.015 nats.

**v2 zip adjacency, corrected.** `docs/CHANNEL.md` and `centers.py` quote v1's 547 components
over 1,229 zips. On v2 it is **862 components over 3,748 zips, 516 singletons**, largest 13.5 %
of M, **47.6 %** of M in components under 1 % each. Contracted to states the instance graph gives
only **10 edges, 42 components** — a state model must import the TIGER state rook graph
(49 nodes, 107 edges), which `td/geo.py::state_rook` now builds.

**Firms (masked `F0`/`F1`).** A = `F0`, 53 reps, 41.1 % of book; B = `F1`, 61 reps, 58.9 %. Both
hold book in 671 zips carrying **48.8 %** of mapped opportunity; 3,704 of 3,748 zips are mappable
(41 lack a gazetteer point, 3 sit outside the lower 48).

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
- **The state-atom engine:** `td/atoms.py` (the atoms, the cut plan, the placeholder rules) ·
  `td/solvers/atom_draw.py` (the search, `free_search`, `check_contiguous`) ·
  `tools/run_atoms.py` (the driver) · `td/geo.py::state_rook` (the TIGER rook graph) ·
  `tests/test_atoms.py`, `tests/test_atom_draw.py`, `tests/test_run_atoms.py`.
  `tools/state_atoms/` is now exploratory leftovers plus the artifact generator — `district4.py`
  was deleted when the engine landed; see that directory's README.
- Recipes and file map: `docs/CODE_MAP.md` · Memory:
  `~/.claude/projects/-Users-ntlee-projects-td/memory/td-contiguity-programme.md` · History:
  `docs/STATE_LOG.md` · Archive: `docs/archive/README.md`
- Artifacts: **state atoms at k=18 `7902dfb3-afc6-431e-ac2c-ceb109662780`** (the exploration:
  inventory, firm-territory map, the four contiguous draws) · pin-cost catalogue
  `f903ee01-eefc-40cf-bd32-8f5536b6e65f` · map diff `68eecbb9-3ce2-45d9-8161-5db7fe212957` ·
  k-sweep (v1) `c007d61d-c753-4151-9026-2288b9d5eb38` · atlas (v1)
  `1f2cddd9-b98b-4213-83ea-784566147c6a`
- Starting a track: `git worktree add .claude/worktrees/<ID> -b wt/<ID> main`; hand-copy the
  gitignored inputs (`docs/CODE_MAP.md` lists them); start `claude` there and activate Serena
  by path; read `APPROACHES.md` §0 and FRAME §6; write the track's lens/domain/brief under
  `docs/tracks/<ID>/`; commit on `wt/<ID>`; ask before merging.
