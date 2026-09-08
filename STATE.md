# State — national channel territory design

**Updated:** 2026-09-07 · **Branch:** `main` · **Head:** `73c9046` · **Tests:** 321 pass,
0 fail (2026-09-07)

Three sections. History: `git log --grep '^State:' -p -- STATE.md`.

## Now

Two tracks landed 2026-09-07, the workflow redesign as `833dd31` and the headline track as
`1a2546a`; both worktrees are removed. 321 tests, 0 fail.

The headline track ships `docs/HEADLINE.md`, the map end to end, plus per-state caps
(`--cap`/`--unanchor`) and the app's Headline tab. It found that the shipped map's **realised max
deviation is 5.25%, outside its own 5% band** (4.68% is a pre-realisation quantity), that **NY at
2 is refuted** while **CA at 4 is only unsearched**, and that the band, not the cap, is the lever.

`fceb127` then fixed the New York close-up: D01 held `QUAL`'s grey slot and disappeared into the
close-ups' context grey, so slot 12 is plum. CA, TX and FL re-render byte-identical.

Next decision: which map ships, still **Track 2 anchored δ = 5%** recommended, gated on the
sponsor reading the grid tables below.

## Next

- [ ] **Which map ships.** Track 2 anchored δ = 5% (recommended), free δ = 5%, anchored δ = 10%,
      or Track 1 δ = 5% — gated on the sponsor reading the grid tables in `## Facts` below. Then
      whether to rerun the chosen cell with `--incumbency-tiebreak`, and whether the West's
      rearrangement is acceptable. Say "5.25% realised", not "within 5%". If CA in four matters
      to the sponsor, the open question is whether it is reachable at δ = 5%: an hour of HiGHS
      returned no incumbent, which refutes nothing.
- [ ] **Phase 1 — the four units**, all concurrent and unblocked: U10-round, U11-roster, U4-disp,
      U13-base. Then U12-menu (needs U8 + U11 + U13; brief re-anchored, unit not launched).
      Branch from `main`.
- [ ] **Sponsor's call: which states, if any, are hand-drawn** (A12). Region pin-cost table now
      in `STATE.md` `## Facts`. Separate session; the borders result changes the question.
- [ ] **The shell-IO instructions that contradict `CLAUDE.md` §7 come from bypass-permissions
      mode.** Read directly in a hub session's system prompt on 2026-09-07: under
      `defaultMode: bypassPermissions` the harness instructs "read files with cat, head, or
      sed -n … make file changes with sed, heredocs". That is why every agent of 2026-09-07
      saw it. `hooks/enforce-file-tools.sh` still blocks it, so the two fight on every slip.
      Decide: keep the hook and let it win, or narrow §7.
- [ ] **Decide whether `--regions-voronoi` reports the mass denominator beside the area one.**
      §3a settled that the area denominator misreports dense metro districts, and
      `tools/measure/district_pieces.py` already computes area, mass and ZIP-count shares, so
      this is a reporting choice with no measurement left in it. Gated on nothing but the call.
- [ ] **Post-merge follow-ups the workflow track left open.** Nine research questions the folded
      findings files carried (`git show a16c304:PLAN.md`, `## Decisions needed`: C1, C2, C4-C7,
      the Gromov R4 textual fixes, OPTIONS §9/§10 items); `docs/channel_note/` and
      `docs/math_note/` LaTeX sources have no owner row; the bibliography three-format gap.
- [ ] **★ bookkeeping.** ★8 has no cited basis and that is the record. Grounding it needs a
      `lit-search`, deliberately deferred. **★9** the sponsor's `δ` as U12's menu with **★4** `ε`
      · **★10** tie-break policy on U11's evidence · carried ★1 ★2 ★3 ★5 ★7. (★11 landed;
      U3-inv retired.)

## Facts

|                                             | v1 `instance_descaled.json.gz` (regression only) | **v2 `instance_descaled_v2.json.gz` (live)**                    |
|---------------------------------------------|--------------------------------------------------|-------------------------------------------------------------------|
| zips                                        | 1,229                                            | 3,748 (strict superset; raw had 3,749, `BLANK` dropped)         |
| reps                                        | 111                                              | 114 (all 111 retained)                                          |
| contested / uncontested / vacant / untapped | 675 / 477 / 2 / 75                               | 718 / 1,447 / 16 / 1,567                                        |
| untapped share of opportunity               | 2.9 %                                            | 15.7 %                                                          |
| aggregate saturation                        | 41.6 %                                           | 29.6 %                                                          |
| total (v1 units)                            | 2,745.6                                          | 5,165.6 — ×1.8814 (8,523.2 in v2 units); v1's "$13B" was ≈$9.6B |
| k at $1B                                    | 13 (overstated; consistent ≈10)                  | 18                                                              |

v2's growth is untapped market: ×1.6333 over worked zips, contested only 675 → 718.

**CONUS ground set, decided 2026-09-07** (`docs/PROBLEM.md` §6): the 32 blank-state, 2 AK and
1 HI zips (0.49 % of M) are handled separately and enter no modeling, optimization or districting
work. Live instance for all of it: `instance_descaled_v2_conus.json.gz`, 3,713 zips, 113 reps,
M 8,481.81, τ = 471.21 at k = 18. The whole-instance figures below (3,748 zips, τ = 473.51)
predate the decision; do not mix the two bases. The shipped headline map re-measured on the
CONUS set: spread 12.02 %, max deviation 6.26 % (D18 −6.26 %, D17 +5.76 %, D16 +5.18 %), against
8.98 % / 5.25 % on the whole instance. CONUS draw `draw_k18_v2conus_20260907/k18`: seed 3
committed by stage 2 (95.7312), spread 1.585 % completed, nash 110.7954.

**One nats scale, one instance, one draw (k=18 seed 2, `δ₀ = 0.009970`, `V = 95.755192`,
`EG_{S₁₈} = 96.532152`).** Balance is free (widening the band 33-fold buys 0.051 nats). The
incumbency premium is **0.72–0.78 nats and NOT SOFT** (D1′: 146–155× the 5e-3 floor, no `δ*`).
The roster is worth **0.249 nats** (v1 0.043). Match gap 0, map gap 0.663. Pinning a region
costs **0.008 (CAROLINAS) to 2.04 (CALIFORNIA) nats** — CALIFORNIA ≈ 3× the whole premium;
FLORIDA `fix` / CAROLINAS `anchor` out-staff the baseline at stage 2 (+0.029 / +0.012).
Premium ladder v2: `P₀` 41.53 %, `P_S` 54.42 %, `P₁₈` 59.27 %, `P_free` 84.17 % of book.

**Region pin-cost catalogue, recomputed 2026-09-04** (`tools/run_draw.py --k 14-22 --seeds 0-9`,
15 runs; total M 8,523.2, target at k=18 is 473.5; Δ columns against the unpinned baseline at
k=18, nash `110.88310108262327` / stage2 `95.75519165924106`, in nats — exact at fixed k since
every scenario partitions the same total into the same number of districts). `fix` is a closed
district (never touched by the solver, k reduced by one); `anchor` is open (locked in, solver
fills the rest by water-fill). `nash Δ` is identical between `fix` and `anchor` for every region,
since both pin the same mass to the same district; `stage-2 Δ` diverges and isn't always
negative.

| region | pinned M | vs target (k=18) | natural k | fix: nash Δ | fix: stage-2 Δ | anchor: nash Δ | anchor: stage-2 Δ |
|---|---:|---:|---:|---:|---:|---:|---:|
| CALIFORNIA | 1,953.8 | +312.6% | 4.36 | −2.037 | −2.126 | −2.037 | −2.217 |
| TEXAS | 972.1 | +105.3% | 8.77 | −0.368 | −0.430 | −0.368 | −0.412 |
| MIDWEST | 876.5 | +85.1% | 9.72 | −0.257 | −0.224 | −0.257 | −0.223 |
| NEWYORK | 849.6 | +79.4% | 10.03 | −0.229 | −0.409 | −0.229 | −0.413 |
| FLORIDA | 661.9 | +39.8% | 12.88 | −0.068 | **+0.029** | −0.068 | −0.019 |
| SOUTHWEST | 606.8 | +28.1% | 14.05 | −0.036 | −0.089 | −0.036 | −0.013 |
| CAROLINAS | 535.2 | +13.0% | 15.92 | −0.008 | −0.013 | −0.008 | +0.012 |

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

**Owner sets on the committed k=18 draw, measured 2026-09-06, corrected 2026-09-07**
(`draw_k18_v2_20260904/k18`, seed 2; τ = 473.513; 52 state codes including `??` at 0.070τ). Home
state by plurality of mass: NY (D01, D04), CA (D02, D10, D14, D17, D18), TX (D03, D16), PA (D05),
CO (D06), FL (D07, D15), NC (D08), MI (D09), IL (D11), NJ (D12), MO (D13); 41 states have no
home district. Mass outside the owner sets **9.15%** (90.85% inside) — the 9.46% first quoted on
2026-09-06 was a hand count, superseded by `tools/borders_report.py`'s measurement on
2026-09-07. Blocks that a 10% band cannot close: NY+NJ+CT+MA+NH+RI+
VT+ME = 3.19τ for three districts against PA+MD+DE = 0.82τ; D06 without its AZ and TX slivers
is 0.68τ. Full composition table: `git show ae2b18d:docs/BORDERS_PLAN.md`.

**State-border snapping, overnight run 2026-09-07** (`battery/results/borders_k18_v2_20260907/`;
full build and narrative `git show ae2b18d:docs/BORDERS_PLAN.md`,
`git show ae2b18d:docs/BORDERS_RESULTS.md`). At δ = 5% every state can lie whole in one district
except CA, TX, NY and FL (Track 2 anchored: 8 splits, certified minimal; realised spread 9.0%,
free form 7.2%). At δ = 10% one more CA cut goes away (7 splits, certified anchored; bound 6
free) and spread doubles to 17% — not worth it. Track 1 (border-snapping the committed map only)
never reaches zero residual splits: it inherits the committed owner sets, which force 5-8 small
states to stay split at every δ (PA+MD+DE is 18% light of a full district, D06 without AZ is
32% light); it does cut the outside-owner share from 9.15% to about 3% and border segments from
1,591 to about 700. Stage-2 value stays in 95.70-95.93 across every cell (committed 95.755), so
moving borders onto state lines costs nothing measurable at staffing.

*Track 1 grid* (owner sets from the committed map; band δ two-sided; ten Lloyd rounds, no Nash
polish; "split states" excludes CA/TX/NY/FL, whose own owner sets span several districts):

| cell | spread | max dev | outside (committed owners) | outside (own owners) | split states | zips changed | border segs | stage 2 |
|---|---|---|---|---|---|---|---|---|
| committed | 1.37% | 1.00% | 9.15% | 9.15% | 24 | 0 | 1591 | 95.755 |
| snap | 51.01% | 29.10% | 0.00% | 2.15% | 0 | 519 | 938 | 95.656 |
| δ 0, λ 100 | 1.75% | 1.30% | 3.72% | 5.83% | 6 | 500 | 720 | 95.813 |
| δ 1%, λ 100 | 2.50% | 1.48% | 3.24% | 3.21% | 8 | 510 | 706 | 95.830 |
| δ 2%, λ 100 | 3.59% | 1.83% | 3.09% | 3.06% | 8 | 523 | 718 | 95.826 |
| δ 5%, λ 100 | 10.33% | 5.50% | 2.34% | 1.92% | 5 | 602 | 700 | 95.797 |
| δ 10%, λ 100 | 19.75% | 10.16% | 1.84% | 3.76% | 8 | 786 | 662 | 95.707 |

(λ ∈ {1, 10} at δ = 2%, showing the soft regime: spread 4.78%/3.77%, outside 5.42%/3.11%, split
states 15/8.)

*Track 2 grid* (state-level minimum-splits MILP, `mip_rel_gap = 0`, 600s per δ; "certified ≥" is
the dual bound less the tie-break's half-split allowance; **bold** = closed to optimality):

| form | δ | splits | certified ≥ | pass spread | realised spread | zips changed | stage 2 |
|---|---|---|---|---|---|---|---|
| free | 0 | 17 | 9 | 0.00% | 1.66% | 648 | 95.932 |
| free | 1% | 12 | 9 | 1.36% | 1.75% | 594 | 95.816 |
| free | 2% | 9 | 8 | 3.28% | 3.61% | 783 | 95.765 |
| free | 5% | 8 | 6 | 8.89% | 7.21% | 932 | 95.803 |
| free | 10% | 7 | 6 | 17.27% | 17.08% | 1011 | 95.701 |
| anchored | 0 | 18 | 9 | 0.00% | 1.42% | 932 | 95.810 |
| anchored | 1% | 24 | 9 | 1.51% | 2.76% | 843 | 95.736 |
| anchored | 2% | 9 | 8 | 3.01% | 3.34% | 784 | 95.780 |
| anchored | **5%** | **8** | **8** | 9.30% | 8.98% | 776 | 95.788 |
| anchored | **10%** | **7** | **7** | 18.01% | 16.81% | 978 | 95.880 |

Only anchored δ = 5% and δ = 10% closed (168s, 386s); every other cell reports a time-limited
incumbent. One open question, low priority (only matters if δ = 10% is chosen): the free bound
at δ = 10% says 6 splits might be possible (NJ alone plus PA+MD+DE+WV); HiGHS neither found nor
refuted it in 600s.

**The shipped map, measured 2026-09-07** (`docs/HEADLINE.md` is the end-to-end write-up). The
level-1 ground set is 49 units, mass 8,468.3, **τ = 470.459**, and the states over τ are
**CA 4.153, TX 2.026, NY 1.805, FL 1.392, NJ 1.043** (`--dump-state-shares`). Do not compare
these with the state-atom block's ratios below: that base keeps the coordinate-less zips and
divides by τ = 473.513. **The realised maximum deviation is 5.25%, outside the nominal 5% band**;
the 4.68% that satisfies the band is `pass_max_dev`, a state-level quantity on continuous shares,
before `realise` makes whole zips of them and before AK, HI and the coordinate-less zips are
placed. `grid.csv` carries all three side by side with nothing marking which is authoritative, so
"within 5%" needs the distinction in the sentence. Recomputed independently from the instance and
the shipped draw: stage 2 95.78785, spread 0.089824, Nash 110.873686, 776 zips changed, every zip
assigned once, mass conserved to floating precision. Level-1 objective 57.00483235477814, 8
splits, gap 0, byte-identical `draw.csv` on a rerun through the override code with no caps.

**Per-state caps, measured 2026-09-07.** **NY at 2 is refuted** (HiGHS Status 8 in seconds: two
anchored districts need 1.90τ, the state supplies 1.805τ). **CA at 4 is not refuted and not
found**: legal at δ = 5%, exactly on the floor (4.200τ of band against 4.153τ, a window 4.7% of
a district), and an hour of branch and bound ended with no incumbent at all (Status 13,
`primal_status is None`). Refused by the floor, refuted by the solver, and searched without
success are three different answers. TX and FL are already at their floor of 2, so the map is
tight, and the band is the lever: **CA capped at 4 at δ = 10% solves**, giving 7 splits, CA in 4, NY
falls to 2, NJ splits, spread 16.70%, stage 2 95.7458, time-limited incumbent at a 1.79% gap
(`figures/overrides/ca4_d10/`).

**Artifacts published 2026-09-07** (private): "Borders on State Lines" (all 19 cells, compare
slider), `https://claude.ai/code/artifact/ca561d23-fa10-49cd-80c0-4d69625d2857`; "The Five
Percent Map" (the recommended cell, full model), `https://claude.ai/code/artifact/322e6a55-a576-4adf-8dc5-8fd2f4ca6c5a`;
"Borders in Motion" (the optimisation replayed step by step),
`https://claude.ai/code/artifact/3e983b90-8f87-4dfd-aa28-4e1cd6eee497`; "Districting from
Duality" (the study guide), `https://claude.ai/code/artifact/d87b53b0-f394-417e-aab5-0fba8d3c6cb0`.

**State atoms — the engine, measured 2026-09-06; route retired the same day, numbers kept for
the record** (`ff63511`, stage 1 only; run
`battery/results/atoms_k18_v2_20260906`). Target 473.5 at k=18. Cut plan **CA 5 / TX 2 /
NY+NJ 3 / FL 2**: 56 atoms, 126 edges, **one component**. Pieces CA1 0.838×, CA2–CA5
0.825–0.826×, TX1 1.013×, TX2 1.007×, NYNJ1–3 0.943–0.944×, FL1 0.706×, FL2 0.691×.
`Σ log M` **110.789532**, ceiling **110.883247**, gap **0.093715** nats, spread **30.484 %**
(max 1.130×, min 0.826×), all 18 districts connected. Of 52 state codes only 5 exceed target:
CA 4.126×, TX 2.020×, NY 1.794×, FL 1.398×, NJ 1.037× (whole-instance τ = 473.5, every zip kept;
the level-1 ground set drops the coordinate-less ones and reads higher, block above);
largest atom needing no cut is IL 0.677×.
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
reads 29.588 % (`docs/units/P0C-screen.md`). R1's downstream premium arithmetic is v1 and stale.

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
