# Problem ledger

The problem statement is `docs/PROBLEM.md` (single channel) and `docs/FULL_PROBLEM.md` (multi-channel).
This file is the ledger of what is settled and what is open about it. One row per item; a
revised row is struck through and restated with a new date, never deleted. Rows below the
seed line are appended by the `triage` skill from lens, council, and review output.

## Settled / open

Seeded 2026-09-21 from the frozen `docs/foundations/FRAME.md` §9 (rows dated 2026-08-31 to
2026-09-02, pre-dating the full-problem track). Rows are copied verbatim; conditions may have
changed since. Re-settle rather than edit.

| item | status | date | owner | why |
|---|---|---|---|---|
| The problem is greenfield balanced territory design, not the two-player merger problem | **settled** | 2026-08-31 | user | The carve-out has no bilateral overlap structure; the pair census does not apply. |
| ~~`k = 13` at a $1B target~~ → **`k = 18` on v2** | **re-settled** | 2026-09-04 | user | The sponsor confirmed ≈$18B (not to be re-derived). The old $13B/k=13 came from an overstated total — the descaled ratio ×1.8814 puts v1 at ≈$9.6B, i.e. `k ≈ 10`. Assumption A1 still attached, now against $18B. |
| ~~Instance sizing: 1,229 zips / 111 wholesalers / ~$13B~~ → **3,748 zips / 114 wholesalers / ≈$18B** (v2) | **re-settled** | 2026-09-04 | user | `instance_descaled_v2.json.gz` supersedes v1. v1 is a strict subset; the growth is overwhelmingly **untapped** market (untapped zips 75 → 1,567; contested only 675 → 718). Supersedes `CHANNEL.md` §6 and the 2026-09-01 row. |
| Adjacency contiguity is not required | **settled** | 2026-09-01 | user | 547 components. Reopenable only by the full-ZCTA-graph experiment. |
| Territories are drawn on opportunity, then staffed — two stages | **settled as a business constraint** | 2026-09-01 | user | Survives as "territories shall be opportunity-balanced"; the claim that it was *derived* was retracted at 41.9% saturation. |
| Staffing is exact and selects the roster | **settled** | 2026-09-01 | programme | Exact, milliseconds, 13 of 111. |
| A certified k=13 draw exists (0.781% spread, 13/13 staffed, 4.5e-5 nats under ceiling) | **settled** | 2026-09-01 | programme | Four certificates; 151 tests. |
| The territory map is a power diagram of its centers, with the duals as a solver-free certificate | **settled** | 2026-09-01 | programme | `937460e`; independently reproduces the MILP's 8.53% as 8.22%. |
| Real saturation is 41.9%, not the 5% assumed | **settled (measured)** | 2026-09-01 | programme | `REVIEW_GROMOV` R1, computed against the export. Invalidates the sizing paragraph that assumed it. |
| Balance is not the binding difficulty | **settled** | 2026-09-02 | programme | Solved to 4.5e-5 nats against a ~3.7-nat premium term. Effort is on the smallest term. |
| **Does territory-drawing get to see wholesaler books?** | **open — blocking** | 2026-09-02 | **user** | ~3.7 nats of value says yes; the incentive-safety invariant says no; audited system-of-record book is the likely escape. Everything about the premium term waits on this. |
| **The acceptance test in business units** (§3.5) — nats → dollars/book-share | **open** | 2026-09-02 | programme | Five certificates nobody outside the programme can read. Blocks presentation, not computation. |
| **Per-wholesaler continuity report** (§3.4) | **open** | 2026-09-02 | programme | The first question the room will ask; never produced. |
| **The hand-drawn baseline** (§3) | **open** | 2026-09-02 | programme | The "better than what we'd have done anyway" claim is currently unevidenced. |
| The 132 dots: adopt the power cells or keep the drawn map | **open** | 2026-09-01 | user, on programme's evidence | Nash-indistinguishable by the programme's own tier-2 floor; the deciding number is the staffing value of the cells map, not yet computed. |
| Who owns vacant (2) and untapped (75) zips | **open** | 2026-08-31 | user | They carry opportunity but no incumbent; the allocation rule is a business call. |
| How vacancy book is capitalised (`filler_capture`) | **open** | 2026-08-31 | user | The default is the no-change case, and is probably not the right answer. |
| Whether capture depends on *which* wholesaler is displaced (θ directionality) | **open** | 2026-08-31 | user | Currently one scalar. Directionality multiplies the identification problem. |
| Empty bundles / lexicographic tie-breaking | **open, but answerable from the literature** | 2026-09-01 | programme | The programme's own anchor citation already defines it; one paragraph and one test. |
| A2 — that the unselected are not released | **open** | 2026-08-31 | user → sponsor | Unconfirmed for two days; changes what staffing means if wrong. |
| Whether any operational coverage rule exists (A6) | **open** | 2026-09-02 | user → sponsor | If one does, §4 is missing a hard constraint. |
| The note's fairness claim at stage 2 (EF1 "survives the move") | **open** | 2026-09-02 | programme | Stage 2 is unit-demand — removing a wholesaler's only territory empties the bundle — so EF1 is vacuous there. `channel_note` §3 must restate the claim for the joint allocation only, or in swap-based form (`RESEARCH_FINDINGS` §9-G). Recorded in `CHANNEL.md` §0 on `national-channel`; not yet in the note. |
| Two `FRAME.md` copies on two branches | **settled** | 2026-09-02 | user | `wt/workflow-dryrun` merged into `national-channel`; one `FRAME.md`. |
| A11–A13 (home-office carve-out, decision grain, team territories) | **open** | 2026-09-02 | user → sponsor | Each is a one-question ask that changes the problem statement, not a parameter: A11 changes `k`, A12 changes the unit, A13 changes the matching's shape. |

<!-- seed line: rows above are the FRAME.md §9 copy; append below -->

## Questions for the lenses

Seeded from `FRAME.md` §10 (2026-09-02). A question a lens answers moves to a U-number in
`UNKNOWNS.md` or to a settled row above.

1. The objective decomposes into a partition-invariant part, a balance part and an incumbency
   part. At 41.9% saturation the incumbency part is ~3.7 nats of swing against 1e-4–1e-2 nats
   of balance. **Is the two-stage separation still the right decomposition of this problem, or
   is it a decomposition of the small term?**
2. Balance was proved to be a consequence of the objective on a common measure. Saturation
   means the measure is *not* common — each wholesaler values the same zip differently, by up
   to ~42%. **What survives of the equal-size result when the measure stops being common, and
   is there a weighted or per-agent statement that replaces it exactly rather than
   approximately?**
3. Certificates exist for balance (analytic ceiling), for compactness at fixed centers
   (duals), and a lower bound for the joint map-plus-staffing value. **What is the natural
   upper bound for the incumbency premium, and is there a reason none has appeared?**
4. The programme's tier-2 acceptance floor (5e-3 nats) is two orders *above* the gap between
   the two candidate maps. **Is a tolerance that renders the main open decision undecidable a
   correctly calibrated tolerance, or is the floor measuring the wrong noise?**
5. Territory-drawing that reads reported books is unfixable against misreporting; territory-
   drawing that ignores them leaves ~25% of total welfare on the table. **Is there a
   formulation in which the drawing depends only on quantities a wholesaler cannot inflate,
   without discarding the continuity value?**
6. The footprint has 547 components on sold zips but is plausibly connected on the full ZCTA
   graph, where the connecting zips are exactly the ones carrying no book. **Is "the glue is
   the worthless part" a structural feature of this problem or an artifact of restricting
   attention to sold zips?**
7. Certificates are denominated in nats — a unit derived from the objective's own functional
   form. **Is there an invariant statement of distance-to-optimal in the problem's own units
   (opportunity, misplaced book) that does not pass through the logarithm?**
8. Fix the roster `S` (13 wholesalers). Maximising the utilitarian value `Σ_z u_{σ(z)}(z)`
   subject to equal-`M` territory masses is a **transportation LP** — the same LP `centers.py`
   already solves, with cost `−u_i(z)` (plus, optionally, the same `M_z d²` compactness term)
   in place of `M_z d²` — integral up to `k−1` split zips. It optimises the premium term
   *exactly* under the balance the business asked for, with no logarithm. **Is its value a
   new rung `P*_bal(S)` in the premium ladder between `P*(A)` and `P₁₃`, and is alternating
   it with the Hungarian step a coordinate ascent whose fixed points are what the joint
   formulation would find?**
9. The stages could run in the other order: select the 13 first (max-coverage / audited
   book, `P₁₃`), then draw the map around the selected wholesalers' book centroids as sites,
   reading only their normalised geographic profiles. **Does roster-first lose anything that
   draw-first keeps, and does it satisfy the inflation-invariance the incentive argument
   demands, by construction?**
10. Books and sizing both follow metros. **At the grain of metro areas (or of the two firms'
    branches), does the tie-breaking degeneracy that produces the 132 dots and the
    second-order-flat objective exist at all — and is the zip map then a derived artifact
    rather than the decision?** (A12.)
11. If some share of the sized opportunity is home-office business with no geography (A11),
    the common-measure argument is being applied to a quantity that is not partitionable.
    **What is the right treatment of non-geographic opportunity — a `k+1`-th territory, a
    pre-draw carve-out, or a per-territory credit — and how does each change `k`?**
12. With one wholesaler per territory the matching is an injection and the solver is
    Hungarian; with team coverage of a dense metro it becomes a capacitated `b`-matching,
    where Nash-welfare matching is NP-hard already at capacity 2 (`RESEARCH_FINDINGS` §4B).
    **Is exactness at stage 2 an artifact of a rule the sponsor has not actually stated?**
    (A13.)
