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
| U38 | PU9 | Compactness objective: diameter or an alternative | B/T | B1 (#64). 2026-09-29: T part answered in `docs/MODEL.md` §3.5 (#64): Claims 1–3 hold for any w_S ≥ 0 that depends on S alone. The business choice is open, OD6 (#75). 2026-10-02 (#81): E part measured on the 18-split candidate, support diameter against a ZIP-grain Hess planner (`docs/RESULTS.md` #81): **evidence inconclusive**. Hess lowers its own score 4–9% and fixes diameter-0 single-state spread and long-drawn small supports, but raises support diameter 1–22%, splits and contacts on FI and WH, leaves five η shortfalls after repair, runs about 480 times as long and is a local optimum with no bound. Remaining experiment: the "hess from support" variant (`m5-studio/81-variant`), with the owner's reading of the side-by-side maps |
| U39 | PU10 | Is the corridor floor (lightest chain across a separating unit) the right necessary condition, and how often does it bind on the real extract? Council: as printed, it is not necessary when v separates three or more components (C6). | T/E | B1 (#64), B2 (#65), D1 (#73). 2026-09-29: restated in `docs/MODEL.md` §4.2 (#64): the component-versus-rest floor, proved necessary in Proposition D; B2 checks it, and D1 measures how often it binds |

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
