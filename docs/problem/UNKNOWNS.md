# Unknowns ledger

Every open unknown has a U-number and a grade: **E** settleable by computation, **B** needs a
business answer, **T** needs a theorem. Every "number to compute" anywhere in the project maps
onto a U-number. An answered unknown keeps its number and is restated as answered with the
source. Numbers are never reused.

## Open: the support master (U30–U39)

The plan's unknowns PU1–PU10 (#52 §9), numbered by the owner's answer to OQ3 on 2026-09-28:
PU1 = U30 through PU10 = U39. "Settled in" names the #52 plan item and its issue.

| id | plan | unknown | grade | settled in |
|---|---|---|---|---|
| U30 | PU1 | Claim 1: decoding equivalence. Council: (iii) holds only under the same support family and policy rows (C3). | T | B2 (#65); proof in `docs/MODEL.md` §5 (#64, 2026-09-29) |
| U31 | PU2 | Claim 2: the exact smallest-δ MILP. Council: exact for the master only (C4). | T | B2 (#65); proof in `docs/MODEL.md` §5 (#64, 2026-09-29) |
| U32 | PU3 | Support family size at caps 6 and 7 | E | C2 (#67) |
| U33 | PU4 | Claim 3: tree rounding keeps each district's drawn mass within the heaviest split ZIP it touches. Proof sketched and tested numerically; this bound is what makes μ_S sufficient. Council: the argument holds for an exact vertex, before repair (C5). | T | B2 (#65) proof, C4 (#69) tests; proof in `docs/MODEL.md` §5 (#64, 2026-09-29) |
| U34 | PU5 | How many pieces per map the minimal realizer leaves in free and clipped mode, and from which causes; counted both as pieces and as districts in pieces (C17) | E | C4 (#69), the trigger for C4b; E1 (#74) |
| U35 | PU6 | Price of clipping and of pieces | E | D1 (#73) |
| U36 | PU7 | Rurality cap schedule g | B/E | B1 (#64), D1 (#73). 2026-09-29: the form is stated in `docs/MODEL.md` §6 (#64); the schedule is open, D1 (#73) |
| U37 | PU8 | Whole-metro feasibility per channel | E | D1 (#73) |
| U38 | PU9 | Compactness objective: diameter or an alternative | B/T | B1 (#64). 2026-09-29: T part answered in `docs/MODEL.md` §3.5 (#64): Claims 1–3 hold for any w_S ≥ 0 that depends on S alone. The business choice is open, OD6 (#75). 2026-10-02 (#81): E part measured on the 18-split candidate, support diameter against a ZIP-grain Hess planner (`docs/RESULTS.md` #81): **evidence inconclusive**. Hess lowers its own score 4–9% and fixes diameter-0 single-state spread and long-drawn small supports, but raises support diameter 1–22%, splits and contacts on FI and WH, leaves five η shortfalls after repair, runs about 480 times as long and is a local optimum with no bound. The "hess from support" variant (same loop, seeded at the support map's centroids) reaches the same plan on national and WH. On FI it stops at another local optimum, 1.2% above the Hess arm on Hess, with support diameter 5.4% above arm 1 and arm 1's contacts and split units, so Hess does not require FI's extra fragmentation, though the lower of the two optima keeps it. Remaining experiment: the owner's reading of the side-by-side maps |
| U39 | PU10 | Is the corridor floor (lightest chain across a separating unit) the right necessary condition, and how often does it bind on the real extract? Council: as printed, it is not necessary when v separates three or more components (C6). | T/E | B1 (#64), B2 (#65), D1 (#73). 2026-09-29: restated in `docs/MODEL.md` §4.2 (#64): the component-versus-rest floor, proved necessary in Proposition D; B2 checks it, and D1 measures how often it binds |

## Open: balance (U40–U52)

From the 2026-10-01 Gromov council (`docs/lenses/COUNCIL_2026-10-01.md`, triaged 2026-10-04).
Each entry carries one line of context, since this file is read on its own.

| id | unknown | grade | status |
|---|---|---|---|
| U40 | WH island floor: in the 51 (fixed 8-state WIFI excluded from WH), the west holds 1.615 WH districts, so at K_WH = 11 every connected WH map has a west district at ≤ −19.25%. Same mechanism governs combined-channel designs that cut WH in two. Recompute 1.615 | T | open; #88 reports it |
| U41 | Before repair, drift (drawn − planned) sums to zero over each exchange component, so ZIP swaps move districts only toward their component's mean | T | open; #85 |
| U42 | An L1 balance objective Σ_S \|Σ_v M_v t_{v,S} − τ n_S\| is linear and keeps Claims 1–3; Claim 1(iii) and Prop D become inequalities | T | open; a candidate balance pass after splits are fixed (#80), not the objective (U49) |
| U43 | What sets national's margin-off δ\* = 0.067 on the 51: a closed set of states, a rule row, or the distance cap | E | open; #73 |
| U44 | Per channel, the gap between δ\*(μ=0) and the best audited drawing; the ZIP-level floor | E | open |
| U45 | How close two districts sharing a split state get by exchanging boundary ZIPs | E | open; sizes #85 |
| U46 | When a balanced support plan lifts to a connected ZIP partition | T | open; MODEL C10 |
| U47 | Within an exchange component, drift bounded by the heaviest boundary ZIP rather than μ_S | T | open |
| U48 | Heavy ZIPs as binary atoms in the master: Claim 3 holds with μ_S ≤ ε·\|split units of S\| | T | open |
| U49 | The balance loss: worst district, sum, count within ±x%, or leximin | B | **answered 2026-10-04: balance is a plain ±15% band, not the objective.** Maps rank by channel-state splits, visual defects, shape, then worst and mean deviation (PROBLEM.md row 2026-10-04) |
| U50 | Is a district the region it covers (zero-opportunity ZIPs included) or its opportunity ZIPs? Decides piece counts, thin links, and whether districts may cross empty ZIPs | B | open; #82 |
| U51 | May K per channel and the WIFI region move? | B | **answered 2026-10-02: yes.** K set from per-channel dollar targets (2026-10-01; within ±10% of target and main total 48–54, 2026-10-04); combined region moved (no WIFI; New England; New England + ID MT ND SD WY NE KS OK NM). `docs/memory/facts/scenario-sweeps-2026-10.md`; #75 |
| U52 | Is a ZIP holding 0.13τ–0.36τ territory, or a booking address to place apart? | B | open; #83 |

## Reserved (U14–U29)

Reserved by the owner's answer to OQ3 on 2026-09-28:

- **U14–U19**: as `docs/lenses/GROMOV_2026-09-03.md` defines them (its unknowns table).
- **U20–U27**: N1–N8 of `docs/lenses/GROMOV_2026-09-21.md`, numbered in order when the
  `triage` skill takes them. Any N that duplicates one of U30–U39 is marked as a duplicate of
  it, not numbered twice.
- **U28–U29**: unused.

## Archived (U1–U13)

Archived 2026-09-28 (td#54): they belong to the Nash-staffing model, which the support-master
scope archived (#52 S1). They were seeded 2026-09-21 from `docs/lenses/GROMOV_2026-09-03.md`
(Move 14 ledger, A1 track, k = 13 on v1); the statuses are as of 2026-09-03 and are not
re-measured. The rows are kept so the numbers are not reused.

| id | unknown | grade | status |
|---|---|---|---|
| U1 | spread of realised `g_i` vs `M`-spread | E | **measured: 60.65% vs 0.781%** (seed 9: 59.47% vs 0.836%). A0's soft kill fires. |
| U2 | `P₀` | E | **measured: 37.82% of book** |
| U3 | `P*(A)` | E | **measured: 37.82%** — the matching is already premium-optimal; seed 9's relabel buys 0.14% of book and loses 0.008 nats of `V` |
| U4 | contested among the 13, and `M`-share | E | **measured: 83 zips, 6.12% of `M`** |
| U5 | regional bias in `M` | B | open; invisible to the EG dual too (U1-cert §5.6) |
| U6 | data-noise floor on this instance | E | open; not touched by either unit |
| U7 | is the premium soft inside the balance band? | E | **restated as U13**: soft iff `EG^bal_{S₁₃}(δ) − V ≤ 5e-3` |
| U8 | `corr(S_i, M)` | E | **measured: 0.650 pooled**, 0.23–0.93 per selected rep; the ladder bites moderately |
| U9 | saturation robustness to headroom repairs | E | open; 69 zips at `u/M > 1` by ≤ 4.2e-7 (U1-cert §5.2) |
| U10 | the hand-drawn baseline's position | E | open; now to be scored as a point on the `(δ, V)` frontier, not as a `V` comparison alone |
| U11 | audited book at zip × wholesaler grain | B | open; unchanged |
| U12 | the balance↔continuity exchange rate | B → **E+B** | the band duals of `EG^bal` compute it as a shadow price (U14); the business answer becomes "is this the right δ" |

U13 is defined in `docs/lenses/GROMOV_2026-09-03.md` (U7's restatement) and was never given a
row here.
