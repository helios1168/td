# State — national channel territory design

**Updated:** 2026-09-06 · **Branch:** `main` · **Head:** `3979a6b` · **Tests:** 275 pass,
0 fail (2026-09-06)

## Now

**The zero-mismatch guarantee is now showable, and the contiguity statistic that ranked the
districts was measuring the wrong denominator.** Two parallel worktrees, both merged into `main`
on 2026-09-06 at the user's instruction: `worktree-fixed-diagram` (`feaa1bc`) and
`worktree-d01` (`49b706a`), merged as `13a75c1` and `05dab7b`, followed by `3979a6b` which
corrected the records the merges left stale. Tests 275 pass, 0 fail.

**The fixed-diagram figure** (register §4a). `us_maps.py --regions-fixed <draw.csv>` builds one
power diagram — the committed draw's M-weighted centroids, one transportation LP at
exactly-equal-split targets — and draws both labellings on that single held diagram: the
committed draw at **266 of 3,704 outside**, the snapped labelling at **0 of 3,704**. Verified
end to end on merged `main`, not only by test: max dual violation 1.8e-18, the 17 split zips
ringed and named, six sliver cells stroked. The subtitle qualifies the zero with a *measured*
rebuild rather than a quoted one (15 of 3,704 at equal-split targets, 16 at own-masses), so the
figure cannot be read as a fixed-point claim. It costs **6 min 55 s** to render, because the
rebuild LP is on by default; `rebuild=False` is the switch.

**D01 is not fragmented** (register §3a). Under the snap it has two parts: a 148-ZIP NY/NJ core
holding **99.86% of its M**, and the single rural ZIP `18337` (Milford PA) at 0.14%, whose empty
catchment is **44.56% of D01's area**. The largest-piece statistic has an **area** denominator,
and area is not what stage 1 balances. On mass the snapped worst district is **D17 at 92.72%**,
not D01; on the committed draw the worst is D09 at 90.03%, not D14. The two denominators
disagree about *which* districts are the problem, on both labellings.

**Two corrections to the register, both now in it.** The committed drift is **258 at own-masses
targets and 266 at equal-split** — one number quoted for two measurements until now. And **six
cells sit under 1% of the map at k=18** (D14 0.04%, D01 0.06%, D12 0.13%, D10 0.86%, D07 0.87%,
D18 0.98%), not the three the k=13 v1 draw had.

*What's next, and the decision it needs.* Whether `--regions-voronoi` should report the mass
denominator beside the area one — `tools/measure/district_pieces.py` computes all three, so this
is a reporting choice, not a measurement. Then the app wiring for `--regions-fixed` is committed
but has never run in a browser. Review artifact `893379d7-2f28-4d0f-9a5d-edb3b8f076b0`
**predates both changes, so its panels still recentroid and its D01 row still reads 55%**.

## Next

- [ ] **Decide whether `--regions-voronoi` reports the mass denominator beside the area one.**
      §3a settled that the area denominator misreports dense metro districts, and
      `tools/measure/district_pieces.py` already computes area, mass and ZIP-count shares, so
      this is a reporting choice with no measurement left in it. Gated on nothing but the call.
      Until it is made, §3's table and the review artifact both say D01 is the worst district
      when on opportunity it is fourth best.
- [ ] **The `--regions-fixed` app wiring has never run in a browser.** `app/runner.py` passes the
      flag for centre-based engines and `app/main.py` shows both panels, but `.venv-app` did not
      exist in the worktree, so no Streamlit process has exercised it. Rebuild the app venv and
      click Render maps once. Note the render is **6 min 55 s**, not the 3 s the button's old help
      text claimed — if that is too slow in front of a sponsor, `rebuild=False` drops the second
      LP at the cost of the subtitle asserting its zero instead of measuring it.
- [ ] **Iteration 15's labelling was never saved.** The 2026-09-06 run wrote no per-iteration
      draw, so the best iterate's map contiguity is unmeasured and the snapped panels everywhere
      are the single-shot labelling. Re-run writing a `draw.csv` per iterate, then
      `--regions-voronoi` the best one. One transportation LP per iteration, a few minutes each.
- [ ] **Option 2 Route B is the remaining build** — remove `improve()` from `centers.draw`,
      close balance with weights. Judge it against iteration 15's 2.1051% / 0.000283, **not**
      against the 4.0041% single shot, or it will look better than it is. The split-zip floor
      says the room left is small.
- [ ] **`worktree-ca5-map` is still unmerged** (`ce1ef67` the map figures, `9363c14` the
      boundary map). The power-cell branch merged on 2026-09-06; the CA5 one did not, and its
      figures are the source of the atom-route fractions quoted throughout.
- [ ] **The two routes' gaps sit on different bases.** The atom gap 0.093715 is against the
      component-wise ceiling 110.883247 over the whole instance; the power-cell gaps are against
      `k·log(M/k)` = 110.766768 over the 3,704 plotted zips. Two orders of magnitude make the
      ranking unlikely to turn on it, but it is not certified — recompute on one base before any
      sponsor comparison.
- [ ] **The stage-2 cost of the atom map is unmeasured, and could exceed the 0.094.** Pinning
      CALIFORNIA costs **2.04 nats at stage 2** and this model forces CA into five pieces. Do
      not claim "the state-atom model costs 0.094 nats" until
      `battery/results/atoms_k18_v2_20260906/k18/draw.csv` has been through
      `channel.score_draws` — that needs no new code.
- [ ] **Quote the 30.5 % spread beside the 0.094 nats.** `log` is flat near the optimum, so a
      small Nash gap sits alongside a large operational spread; the power-cell route gets
      1.37 %. Quoting the gap alone reads as "contiguity is nearly free".
- [ ] **Map contiguity is measured, and D02/D11/D17/D06 fail it.** `--regions-voronoi` on the
      reproduced draw: largest contiguous piece 48% / 53% / 55% / 73% of territory respectively
      (14 other districts 98-100%). Decide: tolerable as delivered, or does `BORDER_TOL = 40 km`
      / the NY+NJ / CA cut need to change? `worktree-ca5-map`, commits `ce1ef67`, `9363c14`.
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
- [ ] **Something injects shell-IO instructions that contradict `CLAUDE.md` §7.** Fourth and
      fifth occurrences, 2026-09-06: both the `fixed-diagram` and the `d01` agent hit it
      mid-session, independently, and each declined. Earlier occurrences, same shape:
      mid-session text told the agent to read and write files with
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

**Map contiguity, measured 2026-09-06** (`tools/us_maps.py --regions-voronoi`, worktree
`ca5-map`, same draw). Dissolving each zip's Voronoi catchment by district: **D02's largest
piece is 48% of its territory, D11 53%, D17 55%, D06 73%**; D01/D03/D08/D09/D10/D13/D14/D16
(plus near-solid D07/D15/D18) are 98-100% one piece. The atom graph's one component certifies
`BORDER_TOL`-proximity reachability, not that every district is a single polygon.

**Power-cell contiguity, measured 2026-09-06** (draw `draw_k18_v2_20260904/k18`, 3,704 plotted
zips, total M 8,468.3, ceiling `k·log(M/k)` = **110.766768** — a different base from the atom
ceiling). Committed draw: **258 zips (7.0%, 1.66% of M) outside their own power cell at
own-masses targets and 266 (7.2%) at exactly-equal-split targets** — two measurements, quoted as
one number until 2026-09-06 — spread 1.2902%, `Σ log M` 110.766686, gap **0.000082**. Snapped at
equal-split targets: 0 outside by construction, spread 4.0041%, gap 0.000724. Best of 20
snap → recentroid iterates (**iteration 15**): spread **2.1051%**, `Σ log M` 110.766485, gap
**0.000283**. There is **no fixed point** — 20 iterations, no exact repeat, non-monotone, band
spread 2.1–5.6% / gap 0.00028–0.00128. Split zips **17 = `k−1` at both target choices**, carrying
17.03% of a mean district at equal-split (largest `20814`, 3.699%) and 22.08% at own-masses.
**Six cells are under 1% of the map** (D14 0.04%, D01 0.06%, D12 0.13%, D10 0.86%, D07 0.87%,
D18 0.98%); "three metro slivers" was the k=13 v1 count. Largest contiguous piece by **area**,
snapped: **D01 55%**, D09 96%, D14 97%, D10/D13 98%, D07/D08 99%, twelve districts 100%;
committed: nine districts under 80% (min D14 51%). **That denominator misreports dense metros**
— by **mass** the snapped worst is D17 92.72% and D01 is 99.86%, and the committed worst is D09
90.03%, so the two orderings disagree (§3a). Border segments 1,591 committed → 636 snapped.
**The zero is relative to one diagram:** rebuilt from the snapped labels, 16 of 3,704 (0.4%) fall
outside at own-masses targets and 15 at equal-split, and the split count drops 17 → 10. Since
2026-09-06 one figure does display the guarantee — `--regions-fixed` holds the centres and
weights instead of recentroiding — and every other rendering still recentroids.

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
- **The power-cell contiguity register:** `docs/OPTIONS_power-cell-contiguity.md` — every route
  to zero mismatched dots, with its evidence and verdict; §1 is the measurement record, §9 the
  recommended order, §3a why D01 reads 55%, §4a the fixed-diagram figure. This file is the
  durable one; `STATE.md` only names which option is live.
  `td/solvers/centers.py::power_weights` now returns `fractional` (the split zips' row indices),
  surfaced as `power_diagram_of_draw`'s `split_zips`.
- **Showing the zero, and measuring pieces honestly:** `us_maps.py --regions-fixed <draw.csv>`
  (`figures_fixed_diagram`) renders `figures/district_regions_fixed_committed.png` and
  `district_regions_fixed_snapped.png` — one held diagram, both labellings, 266 outside against
  0 · `tools/measure/district_pieces.py` gives each district's largest piece by area, by mass and
  by ZIP count, which is what §3a needed to refute the 55%.
- **The state-atom engine:** `td/atoms.py` (the atoms, the cut plan, the placeholder rules) ·
  `td/solvers/atom_draw.py` (the search, `free_search`, `check_contiguous`) ·
  `tools/run_atoms.py` (the driver) · `td/geo.py::state_rook` (the TIGER rook graph) ·
  `tests/test_atoms.py`, `tests/test_atom_draw.py`, `tests/test_run_atoms.py`.
  `tools/state_atoms/` is now exploratory leftovers plus the artifact generator — `district4.py`
  was deleted when the engine landed; see that directory's README.
- Recipes and file map: `docs/CODE_MAP.md` · Memory:
  `~/.claude/projects/-Users-ntlee-projects-td/memory/td-contiguity-programme.md` · History:
  `docs/STATE_LOG.md` · Archive: `docs/archive/README.md`
- **The scenario app:** `app/` + `tools/app.sh`, its own venv `.venv-app`, whole story in
  `docs/APP.md`. Define a scenario, run either stage-1 engine, see the map, save it. Scenario
  questions go here now, not into a new Claude artifact — the artifacts below stay as the fixed
  record they already are.
- Artifacts: **power-cell contiguity review `893379d7-2f28-4d0f-9a5d-edb3b8f076b0`** (the four
  maps: power diagram committed vs snapped, catchment committed vs snapped vs atoms, the
  per-district bars) · **state atoms at k=18 `7902dfb3-afc6-431e-ac2c-ceb109662780`** (the exploration:
  inventory, firm-territory map, the four contiguous draws) · pin-cost catalogue
  `f903ee01-eefc-40cf-bd32-8f5536b6e65f` · map diff `68eecbb9-3ce2-45d9-8161-5db7fe212957` ·
  k-sweep (v1) `c007d61d-c753-4151-9026-2288b9d5eb38` · atlas (v1)
  `1f2cddd9-b98b-4213-83ea-784566147c6a`
- Starting a track: `git worktree add .claude/worktrees/<ID> -b wt/<ID> main`; hand-copy the
  gitignored inputs (`docs/CODE_MAP.md` lists them); start `claude` there and activate Serena
  by path; read `APPROACHES.md` §0 and FRAME §6; write the track's lens/domain/brief under
  `docs/tracks/<ID>/`; commit on `wt/<ID>`; ask before merging.
