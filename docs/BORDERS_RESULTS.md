# State-border snapping — the overnight run, 2026-09-07

*Results of `docs/BORDERS_PLAN.md`. Run directory `battery/results/borders_k18_v2_20260907/`
(gitignored; hub only). Code on `worktree-vbl`. Both tracks warm-start from the committed
k = 18 seed-2 draw and share the band δ, the completion step and the metric row.*

## The answer in three lines

1. **At δ = 5% every state can lie whole in one district except CA, TX, NY and FL.** Track 2
   finds such a map (8 splits: CA in five districts, NY in three, TX and FL in two), certified
   minimal when each district keeps its committed home state, and within two of the mass
   bound (6) without that restriction. Its realised spread is 7.2% (free) or 9.0% (anchored).
2. **At δ = 10% one more CA cut goes away and nothing else changes** (7 splits, certified under
   anchoring; free incumbent 7, bound 6). The spread doubles to 17%. Not worth it.
3. **Track 1, which only moves the committed map's borders, never gets there.** It inherits the
   committed owner sets, and those force crossings (PA+MD+DE is 18% light, D06 without AZ is
   32% light), so five to eight small states stay split at every δ. It does cut the
   outside-owner share from 9.15% to about 3% and the border-segment count from 1,591 to
   about 700.

Recommendation: ship Track 2 at δ = 5%, anchored. The morning maps to compare are listed at
the end. The sponsor's residual decisions are then only inside CA, TX, NY and FL. One caveat
on "the same map with its borders moved": anchoring preserves each district's home state and
number, but the West is rearranged in both Track 2 forms (D06 takes CO, NM, AZ, KS, NE; D17
takes the Northwest through the Dakotas; D02 shrinks to NV plus a CA piece). Only Track 1
keeps the committed shapes, at the price of the residual splits above.

## Track 1 — the penalised, banded LP on the committed map

Owner sets from the committed map (plurality home per district; a state with no home
district goes to its single top holder). Penalty λ as a multiple of the committed map's mean
d²; band δ two-sided; ten Lloyd rounds from the committed centres, no Nash polish. All nine
cells converged in four to seven rounds; every LP is sub-second.

Two readings of "outside owner sets" are given: against the committed map's owner sets (the
sponsor's state lines) and against the labelling's own, since `refine` recomputes owner sets
each round and the two drift apart at δ = 0 and δ = 10%.

| cell | spread | max dev | outside (committed owners) | outside (own owners) | split states | zips changed | border segs | stage 2 |
|---|---|---|---|---|---|---|---|---|
| committed | 1.37% | 1.00% | 9.15% | 9.15% | 24: AL,AZ,DC,GA,ID,IL,IN,KS,LA,MA,MD,MI,MT,NC,ND,NE,NJ,NM,NV,OH,OK,SC,TN,WY | 0 | 1591 | 95.755 |
| snap | 51.01% | 29.10% | 0.00% | 2.15% | 0 | 519 | 938 | 95.656 |
| δ 0, λ 100 | 1.75% | 1.30% | 3.72% | 5.83% | 6: AZ,ID,IL,NC,NJ,SD | 500 | 720 | 95.813 |
| δ 1%, λ 100 | 2.50% | 1.48% | 3.24% | 3.21% | 8: AZ,DC,ID,IL,NC,NJ,SD,WV | 510 | 706 | 95.830 |
| δ 2%, λ 100 | 3.59% | 1.83% | 3.09% | 3.06% | 8: AZ,DC,ID,IL,NC,NJ,SD,WV | 523 | 718 | 95.826 |
| δ 5%, λ 100 | 10.33% | 5.50% | 2.34% | 1.92% | 5: AZ,ID,IL,IN,VA | 602 | 700 | 95.797 |
| δ 10%, λ 100 | 19.75% | 10.16% | 1.84% | 3.76% | 8: AL,DC,IA,IN,MN,MS,NC,TN | 786 | 662 | 95.707 |
| δ 2%, λ 1 | 4.78% | 2.91% | 5.42% | 6.19% | 15: AL,AZ,DC,ID,IL,IN,LA,MT,NC,NE,NJ,NV,OK,SD,TN | 447 | 639 | 95.783 |
| δ 2%, λ 10 | 3.77% | 2.24% | 3.11% | 3.07% | 8: AZ,DC,ID,IL,NC,NJ,SD,WV | 524 | 719 | 95.824 |

"Split states" counts states with ≥ 1% of their mass in each of ≥ 2 districts, excluding CA,
TX, NY and FL, whose own owner sets span several districts. The spread is roughly twice the
max deviation because the band is two-sided. The pure snap (no LP) shows what state lines
cost without rebalancing: 51% spread.

What Track 1 cannot do: the split list is never empty, and it is not monotone in δ, because
the LP chooses the cheapest forced crossing afresh at each δ. The residual is structural, not
a tuning matter: the committed owner sets pin PA+MD+DE to one district and CO+UT+NM to
another, and neither reaches τ(1 − δ) without taking mass from a neighbour.

## Track 2 — the state-level minimum-splits MILP

Per δ: the MILP over 49 units (lower 48 plus DC) and 18 districts with single-commodity-flow
contiguity on the rook graph, then the lexicographic balance pass (max deviation, then
spread), then the zip-level realisation inside each split state by the transportation LP with
five Lloyd rounds. Two forms: **free** (districts anonymous) and **anchored** (each district
forced to keep its committed home state, sponsor decision 4). HiGHS with `mip_rel_gap = 0`,
600 s per δ, the five δ in parallel.

The MILP does not close in general. The plan's "seconds" was wrong. A time-limited cell
reports its incumbent and the dual bound; "certified ≥" below is that bound less the
objective's constant and the tie-break's half-split allowance, rounded up. At δ ≥ 5% the bound
is the mass bound: CA at 4.13τ needs four districts, TX, NY and FL each need two, so six
splits are unavoidable at any δ ≤ 10%.

"Outside (own owners)" is not a border measure for Track 2: after realisation a district can
hold a CA piece without CA being its plurality state, so that piece counts as outside under
the owner-set rule. The border measure for Track 2 is the split-state list itself, which is
exact by construction, plus the split-zip rounding (`n_fractional`, at most one zip per
district touching a split state).

### Free

| δ | status | splits | certified ≥ | split states (shares) | pass spread | realised spread | zips changed | stage 2 |
|---|---|---|---|---|---|---|---|---|
| 0 | time limit | 17 | 9 | AL, AZ, CA (5), FL, KS, MD, NC, NJ, NY (3), TX (3), WI, WV | 0.00% | 1.66% | 648 | 95.932 |
| 1% | time limit | 12 | 9 | AZ 50/50; CA (5); FL 73/27; NC 91/9; NJ 82/18; NY 56/36/8; TX 49/50/1 | 1.36% | 1.75% | 594 | 95.816 |
| 2% | time limit | 9 | 8 | CA (5); FL 73/27; NJ 85/15; NY 56/36/8; TX 50/50 | 3.28% | 3.61% | 783 | 95.765 |
| 5% | time limit | 8 | 6 | CA D06 13 / D10 25 / D14 25 / D17 13 / D18 23; FL D07 72 / D15 28; NY D01 58 / D04 37 / D05 5; TX D03 50 / D16 50 | 8.89% | 7.21% | 932 | 95.803 |
| 10% | time limit | 7 | 6 | CA D02 22 / D10 26 / D14 26 / D18 25; FL 75/25; NJ D12 96 / D05 4; NY 61/39; TX 47/53 | 17.27% | 17.08% | 1011 | 95.701 |

### Anchored (each district keeps its committed home state)

| δ | status | splits | certified ≥ | split states (shares) | pass spread | realised spread | zips changed | stage 2 |
|---|---|---|---|---|---|---|---|---|
| 0 | time limit | 18 | 9 | 13 states | 0.00% | 1.42% | 932 | 95.810 |
| 1% | time limit | 24 | 9 | 17 states, many 1% crumbs into D06 | 1.51% | 2.76% | 843 | 95.736 |
| 2% | time limit | 9 | 8 | CA (5); FL 73/27; NJ 85/15; NY 56/36/8; TX 50/50 | 3.01% | 3.34% | 784 | 95.780 |
| 5% | **optimal** | 8 | 8 | CA D02 19 / D10 25 / D14 25 / D17 8 / D18 23; FL D07 72 / D15 28; NY D01 58 / D04 37 / D05 5; TX D03 51 / D16 49 | 9.30% | 8.98% | 776 | 95.788 |
| 10% | **optimal** | 7 | 7 | CA D02 8 / D10 26 / D14 26 / D17 14 / D18 24; FL D07 75 / D15 25; NY D01 61 / D04 39; TX D03 47 / D16 53 | 18.01% | 16.81% | 978 | 95.880 |

Anchored δ = 5% closed in 168 s and δ = 10% in 386 s. The three tighter cells did not close
and their incumbents at δ ≤ 1% are poor (the η = 1% floor lets D06 touch many states at
exactly 1%); the free incumbents are the better maps there.

The one open split at δ = 10%: the free bound says 6 might be possible, which would mean NJ
alone as a district (1.037τ fits in [0.9τ, 1.1τ]) with PA+MD+DE+WV making τ(1 − δ) on its
own. HiGHS did not find or refute it in 600 s. It is a one-split question and only matters if
10% is chosen.

## Stage 2

Every cell's stage-2 value lies in 95.70 to 95.93 against the committed map's 95.755, with the
same number of unmatched reps. Moving the borders onto state lines costs nothing measurable at
staffing. The incumbency tie-break at level 2 (`--incumbency-tiebreak`) is built and off; it
was not run tonight.

## What was verified

- `docs/VERIFY_state_splits.md`: the scf contiguity block is exact given a binary root; the
  plan's ε, its `y ≤ z` contact rule and its one-LP balance pass were each refuted and
  corrected before the build (`BORDERS_PLAN.md` carries the amendments).
- `docs/CODEVERIFY_state_borders.md`: Track 1's eight model-to-code mappings verified, none
  refuted; `assign(penalty=None, band=0)` is array-identical to commit `b38c9ce`.
- `docs/CODEVERIFY_state_splits.md`: Track 2's five formulation mappings verified; the plan's
  row count (11,317 as built, not 6,583) and "seconds" refuted.
- 306 tests, 0 failures.

## Known gaps

- The committed map's own state composition is not contiguous at the state level (D09 has
  crumbs in ND, NY, TN; D18's CA piece is cut off from ID and MT), so the plan's warm-start
  upper bound never existed.
- `realise` moves the shared centre array as it cuts split states in turn, so the CA cut
  depends on the order in which split states are processed. Deterministic, undocumented in
  the plan, not yet judged.
- Maps are dots and Voronoi catchments; the `--regions` power diagram is not drawn for a
  penalised labelling. `tools/us_maps.py --clip-states` (off by default) clips each catchment
  to its state polygon; on the Track 1 δ = 5% cell it takes the segment count from 700 to 389.
- The free MILP's gap could be closed with a tighter flow relaxation (pair-form arc capacity,
  a per-district state-count bound in place of N − 1). Daytime work, and only needed if a
  free-form certificate is wanted at δ ≤ 2%.

## Maps to look at

All 19 cells, both map styles, with a compare slider against the committed map, are published
as the artifact "Borders on State Lines",
`https://claude.ai/code/artifact/ca561d23-fa10-49cd-80c0-4d69625d2857` (private, version
"Overnight run 2026-09-07"). The recommended cell has its own artifact for further analysis,
"The Five Percent Map", `https://claude.ai/code/artifact/322e6a55-a576-4adf-8dc5-8fd2f4ca6c5a`:
the map with the compare slider, the split-state, district and every-state composition tables,
and the full two-level model in the channel note's notation (the (splits) program with anchors
and single-commodity-flow contiguity, the two balance-pass LPs, the (targets) transportation LP,
the three claims, and what is and is not certified). On disk, under
`battery/results/borders_k18_v2_20260907/`, each cell has
`figures/districts.png` (dots) and `figures/district_regions_voronoi.png` (fill).

- `committed/` — the map as it stands.
- `track2_anchored/d0.05/d0.05/` — the recommendation: 8 splits, certified, spread 9.0%.
- `track2_free/d0.05/d0.05/` — the same split count with D06 rather than D02 holding a CA
  piece, spread 7.2%.
- `track2_anchored/d0.10/d0.1/` — 7 splits, certified, spread 16.8%.
- `d0.05_lam100/` — Track 1 at δ = 5%: the committed map with its borders moved, five small
  states still split.
- `snap/` — the no-LP baseline.
