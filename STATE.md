# State — national channel territory design

**Updated:** 2026-09-07 · **Branch:** `main` · **Head:** `b7d6e0c` · **Tests:** 306 pass,
0 fail (2026-09-07)

## Now

**The borders plan is built, verified and run; the morning decision is which track and δ
ships.** Session of 2026-09-06 night into 2026-09-07, worktree `.claude/worktrees/vbl`, branch
`worktree-vbl`, commits `a3846b2` (Track 1 solver and driver, Track 2 solver, shared report
helper), `4bf74c7` (Track 2 driver, anchoring, own-owner reading, verification reports),
`c892548` (`docs/BORDERS_RESULTS.md`), merged to `main` as `b7d6e0c` on 2026-09-07 at the
sponsor's request and pushed. 306 tests, 0 fail.
Run directory `battery/results/borders_k18_v2_20260907/` (hub, gitignored), every cell with
`draw.csv`, dot and Voronoi maps. All maps published as artifact
`ca561d23-fa10-49cd-80c0-4d69625d2857` ("Borders on State Lines", compare slider against the
committed map, tables, instance maps; re-rendered 2026-09-07 with a Voronoi diagram per state
and bold state lines, `3c8a6e8`). The recommended cell alone, with its composition tables and
the full model in the channel note's notation, is artifact
`322e6a55-a576-4adf-8dc5-8fd2f4ca6c5a` ("The Five Percent Map"), the sponsor's analysis page.
Two more on 2026-09-07: `3e983b90-8f87-4dfd-aa28-4e1cd6eee497` ("Borders in Motion", every
optimisation step replayed on the map, both tracks) and
`d87b53b0-f394-417e-aab5-0fba8d3c6cb0` ("Districting from Duality", the study guide and
reading list). `realise` now records per-round iterates per split state for the replay.
"Borders in Motion" crashed on first publish (DC's polygon fell to the islet filter and an empty
`reduce` killed the script); fixed and republished, but not yet looked at in a browser. Its
builder is `tools/motion_page/`, and **`docs/MOTION_PLAN.md` is the overnight plan** to
verify it with headless Chrome screenshots per step and improve it (deep links, the figure
palette, striped split states, the power-cell cut per Lloyd round, transitions, hover, the
Track 1 owner-set overlay, optionally the MILP's incumbent trajectory through `highspy`).

**What the run says** (`docs/BORDERS_RESULTS.md`). At δ = 5% a map exists with every state
whole except CA (five districts), NY (three), TX and FL (two): Track 2, 8 splits, certified
minimal when each district keeps its committed home state (`--anchor-homes`, closed in 168 s),
and within two of the mass bound of 6 without that restriction. Realised spread 9.0% anchored,
7.2% free; stage 2 unchanged (95.79 vs 95.755, 96 unmatched reps in every cell). At δ = 10% one
CA cut goes away (7 splits, certified anchored) for double the spread. Track 1, which only moves
the committed map's borders, keeps five to eight small states split at every δ because the
inherited owner sets force crossings (PA+MD+DE 18% light, D06 without AZ 32% light); it cuts
the outside-owner share from 9.15% to about 3% and border segments from 1,591 to about 700.
Recommendation: Track 2 at δ = 5%, anchored. Caveat: anchoring keeps district numbers and home
states, but the West is rearranged in both Track 2 forms; only Track 1 keeps the committed
shapes.

**What the verifiers changed.** `docs/VERIFY_state_splits.md` refuted three parts of the Track 2
formulation before the build (ε now bounded over every feasible `y`; `y ≥ 0.01·z` so a bridge
state carries mass; a two-LP balance pass, max deviation then spread), and refuted the plan's
"seconds": HiGHS does not close the free MILP at any δ in 600 s, and the reported gap is over an
objective carrying the constant S = 49, so a 1.8% gap is one split. `docs/CODEVERIFY_*.md`:
Track 1 eight mappings verified, none refuted, `assign(penalty=None, band=0)` array-identical
to `b38c9ce`; Track 2 five mappings verified, row count 11,317 as built. Plan facts corrected
in place: outside-owner share is 9.15% (not 9.46%), NJ has one owner district, S = 49, and the
committed map's own state composition is not contiguous on the rook graph.

*Next decision.* Which map ships: Track 2 anchored δ = 5% (recommended), free δ = 5%, anchored
δ = 10%, or Track 1 δ = 5%. Then whether the `--incumbency-tiebreak` rerun on the chosen cell
is wanted, and whether the West's rearrangement is acceptable to the sponsor.

## Next

- [ ] **Overnight: `docs/MOTION_PLAN.md`.** Build, verify in headless Chrome, and improve the
      "Borders in Motion" page in the order the plan gives; update the artifact in place by URL;
      ask before merging.
- [ ] **Morning decision: which map ships.** Gated on the sponsor reading
      `docs/BORDERS_RESULTS.md` and the four maps it lists. The recommendation is Track 2
      anchored δ = 5% (8 splits, certified; CA, TX, NY, FL the only split states). The
      residual decisions after that are inside those four states only.
- [ ] **Rerun the chosen cell with `--incumbency-tiebreak`** and report the stage-2 and map
      difference. Built and off; not run tonight.
- [ ] **The free MILP does not close at δ ≤ 2%** (incumbents 9, 12, 17; bounds 8, 9, 9). Only
      matters if a free-form certificate at a tight δ is wanted. Tightening: pair-form arc
      capacity and a per-district state-count bound in place of N − 1
      (`docs/CODEVERIFY_state_splits.md` 6a).
- [ ] **`realise` is order-dependent**: it moves the shared centre array as it cuts split
      states in turn. Deterministic, undocumented, unjudged. Fix is to recentroid from a copy
      per state or process states in a fixed named order; judge on the CA cut of the shipped
      cell.
- [ ] **The δ = 10% free question**: the bound admits 6 splits, which would need NJ alone as
      a district. Unresolved in 600 s; only matters if 10% is chosen.
- [ ] **`--regions` must not be drawn for a penalised labelling.** Dots and `--regions-voronoi`
      only; `--clip-states` (off by default) clips catchments to state polygons and takes the
      Track 1 δ = 5% segment count from 700 to 389. Per-state power diagram is daytime work.
- [ ] **Atom-route leftovers, retired 2026-09-06.** `worktree-ca5-map` (unmerged, locked),
      `battery/results/atoms_k18_v2_20260906`, the engine in `td/atoms.py` /
      `td/solvers/atom_draw.py` / `tools/run_atoms.py`, artifact
      `7902dfb3-afc6-431e-ac2c-ceb109662780`. Do not merge or extend. Remove the worktree when
      convenient; the code stays until a cleanup is asked for.
- [ ] **Decide whether `--regions-voronoi` reports the mass denominator beside the area one.**
      §3a settled that the area denominator misreports dense metro districts, and
      `tools/measure/district_pieces.py` already computes area, mass and ZIP-count shares, so
      this is a reporting choice with no measurement left in it. Gated on nothing but the call.
- [ ] **The sponsor review is a Streamlit tab now, and rendering it takes about ten minutes.**
      `app/main.py`'s Review tab carries the `--regions-fixed` pair only (merged 2026-09-06,
      `e0c7d6e`). Pre-render before a meeting or set `rebuild=False`. The borders cells are not
      in the app.
- [ ] **Option 2 Route B is the remaining build** — remove `improve()` from `centers.draw`,
      close balance with weights. Judge it against iteration 15's 2.1051% / 0.000283, **not**
      against the 4.0041% single shot. Superseded in practice if a Track 2 map ships.
- [ ] **Sponsor's call: which states, if any, are hand-drawn** (A12). `docs/RUNS.md`'s region
      table is the price list. Separate session; the borders result changes the question.
- [ ] **Phase 1 — the four units**, all concurrent and unblocked: U10-round, U11-roster, U4-disp,
      U13-base. Then U12-menu (needs U8 + U11 + U13; brief re-anchored, unit not launched).
      Branch from `main`.
- [ ] **★8 has no cited basis and that is now the record.** Grounding it needs a `lit-search`;
      deliberately deferred.
- [ ] **U11's v2 Nash-tie margin was never measured.** U13's TX share (11.5 %) is likewise
      v1-only. Both are flagged in the briefs rather than filled with invented numbers.
- [ ] **Serena binds to the hub, not the worktree.** Relative paths resolve against
      `/Users/ntlee/projects/td`. Use absolute worktree paths, or `Read`.
- [ ] **Something injects shell-IO instructions that contradict `CLAUDE.md` §7.** Every agent
      of 2026-09-07 (nine of them) reported the same mid-session text and declined it;
      `hooks/enforce-file-tools.sh` caught the main session's own slips (a `grep` on a file, a
      heredoc, a redirect). An agent that complied would bypass the hook.
- [ ] **`D04`/`SOUTHWEST` share a colour and look adjacent** in `SOUTHWEST_anchor`. Reported
      only.
- [ ] `chOppShare` prints 59.1 or 59.2 depending on whether `ceiling.py:75` stores `SATURATION`
      at 3 s.f. — a rounding-order artefact, not a wrong measurement.
- [ ] **★9** the sponsor's `δ` as U12's menu with **★4** `ε` · **★10** tie-break policy on U11's
      evidence · carried ★1 ★2 ★3 ★5 ★7. (★8 and ★11 landed; U3-inv retired.)
- [ ] **Bibliography gap:** `kawase2026balanced`, `borgwardt2019`, `fotakis2014` all resolve but
      live only in the per-domain `.bib` files — none is in
      `docs/math_note/territory_bibliography.bib` (78 entries), and there is no `.md`/`.csv`
      sibling, so the three-format sync is unsatisfied.
- [ ] Deferred: HiGHS root cause (scipy 1.18.1 option merging) only if it recurs; `ceiling.py`'s
      remaining v1 content beyond `SATURATION`; `DOMAIN_optimization` §2.14/§3's `C(111,13)` pool.

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

**Owner sets on the committed k=18 draw, measured 2026-09-06** (`draw_k18_v2_20260904/k18`,
seed 2; τ = 473.513; 52 state codes including `??` at 0.070τ). Home state by plurality of mass:
NY (D01, D04), CA (D02, D10, D14, D17, D18), TX (D03, D16), PA (D05), CO (D06), FL (D07, D15),
NC (D08), MI (D09), IL (D11), NJ (D12), MO (D13); 41 states have no home district. Mass outside
the owner sets **9.46%** (90.54% inside). Blocks that a 10% band cannot close: NY+NJ+CT+MA+NH+RI+
VT+ME = 3.19τ for three districts against PA+MD+DE = 0.82τ; D06 without its AZ and TX slivers
is 0.68τ. Full composition table in `docs/BORDERS_PLAN.md`.

**State atoms — the engine, measured 2026-09-06; route retired the same day, numbers kept for
the record** (`ff63511`, stage 1 only; run
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

**Reference parameters and the per-zip sizing** (`channel_note.tex` §5.1, re-measured on v2
2026-09-04). At `θ = 0.40`, `λ = 0.30` — so `c1 = 0.70`, `c2 = 0.28`, `c1 − c2 = 0.42` — and
aggregate saturation 29.588 %, a zip whose whole book sits with one incumbent is worth
`u_incumbent = 0.507·M_z` against `u_other = 0.383·M_z`. Of the incumbent's utility **59.1 % is
the pure opportunity term** `λ·M_z` and **24.5 % the incumbency premium** `(c1−c2)·S_i(z)`; the
hold-vs-not swing is **32.5 %**. The v1 figures for the same quantities were 89.6 % / 6.7 %
against an assumed 5 % saturation, and were wrong: the Gromov review R1
(`git show 81bd59f:docs/REVIEW_GROMOV.md`) measured v1 aggregate
`Σ(T+S_free)/ΣM` at **41.9 %** on 2026-09-01 (median per-zip `t_z` 46.8 %, p90 110 %; 48.0 % of
opportunity in zips above 30 %), giving an opportunity share of ≈59 % and a swing of ≈42 %. Note
the two definitions differ: this row's `Σ(T+S_free)/ΣM` reads **29.8107 %** on v2 where `ΣT/ΣM`
reads 29.588 % (`docs/VERIFY_P0C-screen.md`). R1's downstream premium arithmetic is v1 and stale.

**Power-cell detail, measured 2026-09-06.** The 17 split zips at equal-split targets are
`07042`, `07670`, `08618`, `20814`, `28104`, `30066`, `32837`, `60462`, `60914`, `70364`,
`73072`, `77845`, `85254`, `90731`, `91786`, `93401`, `94104`; after `20814` (3.699 % of a mean
district) come `60462` 2.067 %, `85254` 1.620 %, `94104` 1.494 %, `91786` 1.351 %. At own-masses
targets the count is again exactly 17 for 22.08 % of a mean district, largest `19067` at
4.108 %. Worst per-district mass change under the own-masses snap: D12 +4.25 % of mean, D05
−3.33 %. **D01's 55 %-by-area second part is the single rural ZIP `18337`** (Milford, Pike
County PA, ~85 km from the core), whose catchment is 44.56 % of D01's area and 0.14 % of its
opportunity while the 148-ZIP NY/NJ core is 55.44 % of the area and 99.86 % of the mass. Moving
`18337` to D05 or D12 makes D01 one piece at 100 % and costs 9e-6 nats, but puts one zip of
3,704 outside its own power cell — a departure from zero for a number that measures the wrong
thing, so the draw is left alone and both denominators are reported.

**v2 zip adjacency, corrected.** `centers.py` still quotes v1's 547 components
over 1,229 zips (`docs/PROBLEM.md` §5 is corrected). On v2 it is **862 components over 3,748 zips, 516 singletons**, largest 13.5 %
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

- `docs/PROBLEM.md` — the problem, the two stages, sizing, the zero-mismatch requirement ·
  `docs/MODEL.md` — the N-way model and open decisions (§6),
  the propositions (§7), the two stages as programs (§8, §9), the certificates (§10), the
  power-cell routes (§11), the VBL comparison (§12), the verified absences (§13) ·
  `docs/foundations/FRAME.md` — problem statement (§6 measured rows, §9 settled/open)
- `docs/foundations/APPROACHES.md` — §0 what every track inherits, charters A0–A5 · `docs/foundations/BRIEF.md` +
  `docs/units/` — A1's plan, units U0–U13 · `docs/foundations/LENS_*.md`, `docs/foundations/DOMAIN_*.md`, `docs/foundations/LIT_*` —
  A1's (promoted) lenses, domain plans, literature
- `docs/RUNS.md` (+ `RUNS_PLAN.md`) — the pin-cost catalogue · `docs/MODEL_U8-band.md`,
  `CODEVERIFY_U8-band.md`, `MODEL_U9-bandthm.md`, `VERIFY_U9-bandthm.md` — wave 1 ·
  `MODEL_U7-meas.md`, `MODEL_U1-cert.md` (+ verifies) — the measurements · `docs/DATA.md` — the
  data route
- `docs/WAVE2_PLAN.md` — the wave-2 execution plan: 9 tracks, 3 phases, per-track files, model
  assignments, merge order, and the four corrections to this file's record
- **The power-cell contiguity register:** `docs/MODEL.md` §11 — every route to zero mismatched
  dots, with its verdict; the requirement itself is `docs/PROBLEM.md` §8 and every measurement is
  in `## Facts` above. (Folded 2026-09-07 from `docs/OPTIONS_power-cell-contiguity.md`, deleted.)
  `td/solvers/centers.py::power_weights` now returns `fractional` (the split zips' row indices),
  surfaced as `power_diagram_of_draw`'s `split_zips`.
- **Showing the zero, and measuring pieces honestly:** `us_maps.py --regions-fixed <draw.csv>`
  (`figures_fixed_diagram`) renders `figures/district_regions_fixed_committed.png` and
  `district_regions_fixed_snapped.png` — one held diagram, both labellings, 266 outside against
  0 · `tools/measure/district_pieces.py` gives each district's largest piece by area, by mass and
  by ZIP count, which is what §3a needed to refute the 55%.
- **The next build:** `docs/BORDERS_PLAN.md` — state-border snapping of the committed draw:
  model, grid, files, the run command, verification · `docs/MODEL.md` §12 — the VBL comparison
  and Options A–E, parked (folded 2026-09-07 from the markdown channel note, since deleted; the
  LaTeX note `docs/channel_note/channel_note.tex` is unaffected and stays the typeset source).
- **The state-atom engine (retired 2026-09-06):** `td/atoms.py` (the atoms, the cut plan, the placeholder rules) ·
  `td/solvers/atom_draw.py` (the search, `free_search`, `check_contiguous`) ·
  `tools/run_atoms.py` (the driver) · `td/geo.py::state_rook` (the TIGER rook graph) ·
  `tests/test_atoms.py`, `tests/test_atom_draw.py`, `tests/test_run_atoms.py`.
  `tools/state_atoms/` is now exploratory leftovers plus the artifact generator — `district4.py`
  was deleted when the engine landed; see that directory's README.
- Recipes and file map: `docs/CODE_MAP.md` · Memory:
  `~/.claude/projects/-Users-ntlee-projects-td/memory/td-contiguity-programme.md` · History:
  `docs/STATE_LOG.md` · Archive: `docs/foundations/archive/README.md`
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
