# Unknowns ledger

Every open unknown has a U-number and a grade: **E** settleable by computation, **B** needs a
business answer, **T** needs a theorem. Every "number to compute" anywhere in the project maps
onto a U-number. An answered unknown keeps its number and is restated as answered with the
source. Numbers are never reused.

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

U1 to U13 seeded 2026-09-21 from `docs/lenses/GROMOV_2026-09-03.md` (Move 14 ledger, A1 track,
k = 13 on v1). Statuses are as of 2026-09-03; the k = 18 v2 instance and the full-problem track
may have changed them. Re-measure before citing.

## Untriaged sources

- `docs/lenses/GROMOV_2026-09-21.md` names N1 to N8 (Opus 5 run on `MATH_REVIEW.md` §3). Not yet
  triaged; they become U14 onward through the `triage` skill.
- `PROBLEM.md` "Questions for the lenses" 1 to 12.
