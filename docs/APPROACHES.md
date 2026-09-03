# Approaches — balanced territory design and roster selection for the national channel

**Date:** 2026-09-02 · **Framework:** 0.1 · **Reads:** `docs/FRAME.md` (§3, §10 twice),
`docs/LENS_GROTHENDIECK.md` (concepts, descent, open questions), `docs/LENS_GROMOV.md`
(Move 14 ledger, open questions), `docs/DOMAIN_optimization.md` §2.1, §2.5, §2.6, §7,
`docs/DOMAIN_economic-theory.md` §7–8, `docs/BRIEF.md` §1–§7, `docs/RESEARCH_FINDINGS.md`
§3C, §9-G/H/I, `CLAUDE.md` · **Supersedes:** none

This file names methodology **families**, not methods. Each `## <ID>` section is a charter
that a track — one tmux window or worktree — takes verbatim; the track re-runs stages 2–6 under
it and reports on FRAME §3's six criteria. Numbers here are FRAME §6's or carry a citation.
Anything that reads `instance_descaled.json.gz` is gated on **★6** (BRIEF §5).

Seeded domains: `optimization`, `economic-theory` only (global `CLAUDE.md` §5).

## 0. Summary table

| ID | family | decides, in order | measure | domains | kill experiment | state |
|---|---|---|---|---|---|---|
| A0 | draw-then-match | k → partition on `M` → roster by Hungarian on `log g` | stage 1 common (`M`); stage 2 per-agent (`u_i`) | optimization, economic-theory | A3 ties or beats A0 on `V` (★6) | running |
| A1 | joint coverage | (partition, roster) together by rep-indexed MINLP; EG relaxation as the bound | per-agent `V(π,σ)` throughout; balance as a band | optimization, economic-theory | `P₀ ≈ P*(A)` and few zips contested among the 13 (★6) | running — **kill test passed 2026-09-03** (`MODEL_U7-meas` §6: matching gap 0, map gap 0.64 nats, roster 0.04; ceiling 0.76 nats at `S₁₃` from U1-cert) |
| A2 | roster-first, invariant draw | roster by max-coverage on audited book → sites from `G`-invariant profiles → balanced transport | audited book (per-agent, un-inflatable) then `M` (common) | economic-theory (mechanism design), optimization | fibre spread `spread_S EG_S` small (★6); no audited book (★2) | planned |
| A3 | sales-ops baseline | group states to ≈ `$total/k` by hand → top-book rep per bucket | `M` by state (common), book share (per-agent) | none | none — it is the baseline; dies as a *candidate* if `V` and C1 both lose (★6) | planned |
| A4 | coarse-grain districting | grain (metro / branch) → exact partition of ~hundreds of units, contiguity optional → roster → zip map derived | `M` at the coarse grain (common) | optimization; geometry unseeded | largest metro's `M` exceeds the C1 band (★6 + public ZCTA→CBSA crosswalk) | planned |
| A5 | ensemble selection | sample the balance band → staff each sample → choose by staffing value; certify by ensemble position | `V` after staffing, reported as a percentile | optimization; statistics/MCMC unseeded | ensemble spread of `V` at the band ≤ tier-2 floor (★6) | planned |

## A0 Draw-then-match — incumbent

**Family** — Two stages: partition the footprint on opportunity alone, then assign wholesalers
to the fixed partition by an exact max-weight matching on log gains.

**What is decided, in what order**
1. `k = total/$1B` by arithmetic (FRAME §6: 13).
2. The partition: k-means++ seeding → transportation-LP balanced assignment → Lloyd →
   Nash polish, over a portfolio of seeds (`td/solvers/centers.py`). Reads `M_z` and
   coordinates only. The 6 coordinate-less zips are placed by state afterwards.
3. The roster: Hungarian on `log g_{ij}` over 111 × 13, selecting 13 (`td/channel.py`).
4. Portfolio choice: `channel.score_draws` ranks stage-1 draws by how well they staff — the
   mild, tolerated breach of "books enter at stage 2 only" (FRAME A9).

**Optimised / against what measure** — Stage 1 maximises `W(π) = Σ_j log M(A_j)` minus a
compactness term: a **common** measure, which is what makes balance a theorem
(`test_nash_welfare_is_equal_size_districting`). Stage 2 maximises `Σ_i log g_{i,σ(i)}` on
per-agent `u_i` at fixed `π`. The pair `(π,σ)` is never optimised jointly; `W` is not known to
bound `V` (LENS_GROTHENDIECK §3).

**Domains needed** — `optimization` (transport LP, power diagrams, MILP certificates) and
`economic-theory` (MNW, EF1, stability audit). Both seeded and both planned.

**The six criteria under this approach**
- C1 count and size — **met, by computation**: 0.781% spread at k=13, 4.51e-5 nats under the
  analytic ceiling (FRAME §6).
- C2 coverage — **met, by construction**: 1,229 of 1,229.
- C3 roster — **met, by construction**: injective matching, 13 of 111.
- C4 continuity per person — **unmet; by computation, trivially**: the `i`-th term of `V` with
  `λ = 0` (LENS_GROTHENDIECK descent 8). Never emitted.
- C5 distance-to-best in business units — **unmet; not at all as built**: four certificates plus
  a fifth specified, all in nats, all consuming only the anonymous quotient (BRIEF §6.6). A
  translation needs the displacement modulus (U4-disp), which is unproved.
- C6 reproducible and auditable — **met, by computation**: `tools/run_draw.py` on the descaled
  export; 151 tests.

**Stage reached** — 5b: `VERIFY_U2-stab.md` 13/13 VERIFIED; `FRAME.md` §0.

**Kill experiment** — Score the hand-drawn baseline (A3) with `V` and with C4. If A3 ties or
beats the committed draw on `V` within the tier-2 floor, A0's headline claim is false
(LENS_GROMOV Move 4, ledger U10). Depends on ★6 and FRAME §6's committed draw. A second,
softer kill: LENS_GROMOV U1 — if the spread of realised `g_i` is far from the 0.781% spread of
`M`, the headline balance number measures the wrong thing. **Fired 2026-09-03:** realised-gain
spread 60.65% on the committed draw (`MODEL_U7-meas` U1, FRAME §6).

**Why it might beat A0** — Not applicable; this is A0. Its case against the others is
FRAME §9's settled business constraint "territories shall be opportunity-balanced" and
BRIEF §7's warning that two measured numbers (`P₀ ≈ P*(A)`, few contested among the 13) would
show the premium is reachable by relabelling alone, in which case A0 plus a roster polish is
the whole answer.

**Inherits** — everything in the hub: `LENS_GROTHENDIECK.md`, `LENS_GROMOV.md`,
`DOMAIN_optimization.md`, `DOMAIN_economic-theory.md`, `LIT_economic-theory.md`, `BRIEF.md`,
`units/`, `MODEL_U2-stab.md`, `VERIFY_U2-stab.md`.

## A1 Joint coverage optimisation

**Family** — One decision: choose the (map, roster) pair that maximises the value the business
signs, `V(π,σ) = Σ_j log u_{σ(j)}(A_j)`, by a rep-indexed mixed-integer program whose
continuous relaxation is the equal-budget Fisher market.

**What is decided, in what order**
1. `k` by arithmetic, as A0.
2. A candidate roster set (111 → a few dozen) from the `P₁₃` max-coverage solve
   (DOMAIN_optimization §2.3) — a restriction for tractability, not a decision.
3. **Partition and roster together**: `x_{zi}` (zip `z` to rep `i`) and `y_i` (rep `i`
   staffs), `Σ_i y_i = k`, `x ≤ y`, objective `Σ_i y_i log(g_i / y_i)` — the perspective
   reformulation of DOMAIN_optimization §2.1 — subject to an explicit opportunity band per
   territory, since balance is no longer a theorem once the measure is per-agent.
4. The fixed-roster Eisenberg–Gale relaxation as the single certificate; the existing four are
   its degenerations at `u_i ≡ λM` (LENS_GROTHENDIECK "The general case"; U1-cert).

**Optimised / against what measure** — `V` on **per-agent** measures `u_i` throughout. Balance
on the common measure `M` enters as a constraint band (or as the `(premium, balance)` frontier
of DOMAIN_optimization §2.5, with the MNW point marked to stay clear of trap 2). FRAME §10 Q2's
answer under this approach is LENS_GROTHENDIECK descent 2: the heterogeneous replacement for
equal-size districting is the equal-budget equilibrium, not a weighted theorem.

**Domains needed** — `optimization` (perspective MINLP, exponential-cone relaxation, B&B;
seeded) and `economic-theory` (EG/CEEI interpretation, the duals as prices; seeded).

**The six criteria under this approach**
- C1 — **by computation**: the band is a constraint, so met if feasible; the width is a sponsor
  input that has never been elicited (FRAME §3 Tolerance's ±10% is the only number; LENS_GROMOV
  U12).
- C2 — **by construction**: `Σ_i x_{zi} = 1`.
- C3 — **by construction**: `Σ y = k`, `x ≤ y`.
- C4 — **by construction**: each `g_i` is the continuity term for rep `i`; the report is the
  objective's own summands.
- C5 — **by computation, in nats**: a branch-and-bound gap on `V` bounds balance, premium and
  compactness at once (DOMAIN_optimization §2.1). Business units need the EG duals read as
  prices on zips and a displacement bound from them (LENS_GROTHENDIECK OQ5; U4-disp) —
  plausible, unproved.
- C6 — **by computation**, conditional on a reproducible exponential-cone or OA solve on the
  work machine; the solver stack is the risk (`CLAUDE.md` traps 12, 14).

**Kill experiment** — LENS_GROMOV ledger U2–U4 in one script: `P₀` (premium of the committed
draw), `P*(A)` (best matching at the committed partition), and the count of zips contested
among the selected 13. If `P₀ ≈ P*(A)` and the count is small, redrawing cannot buy premium and
A1 collapses to A0 plus a relabel (BRIEF §7). DOMAIN_optimization §2.6's τ-homotopy is the
same test in parametric form. Depends on ★6 and FRAME §6's 41.9%.

**Why it might beat A0** — FRAME §10 Q1 and §6: the incumbency premium is ~3.7 nats of swing
against 1e-4–1e-2 nats of balance, and A0 optimises only the small term. LENS_GROTHENDIECK §3
shows `W` is neither a bound on nor a projection of `V`, so A0's map has never been graded on
what the business signs. DOMAIN_optimization §2.1 adds that rep-indexing dissolves the `S_k`
symmetry hazard *because* saturation is 41.9%. Cost the charter must carry: the draw reads
books, so it is exactly the formulation FRAME §9's blocking decision forbids until audited
book (★2) or a `G`-invariant input rule (A2) is adopted; DOMAIN_optimization §8 Q7 argues this
blocks deployment, not formulation.

**Inherits** — `LENS_GROTHENDIECK.md` unchanged (its EG concept is this approach's core);
`LIT_economic-theory.md` unchanged. Re-run `/gromov` and both `/domain` plans under this
charter; `units/U1-cert.md` carries over as the first unit.

## A2 Roster-first, inflation-invariant draw

**Family** — Reverse the stages: select the 13 first from statistics a wholesaler cannot
inflate, then draw balanced territories around the selected wholesalers' book geography,
reading only inflation-group invariants.

**What is decided, in what order**
1. `k` by arithmetic.
2. **The roster**, from audited system-of-record book: max-`k`-coverage of book mass
   (`P₁₃`, monotone submodular; LENS_GROMOV OQ1) — greedy with the `(1 − 1/e)` guarantee or
   exact by MILP at 111 × 13.
3. **Sites**: each selected wholesaler's normalised geographic book profile — a `G`-invariant
   (LENS_GROTHENDIECK §5b, concepts table) — gives a centroid or a per-zip affinity.
4. **The map**: the same transportation LP as A0 with equal `M` masses and cost from
   distance to the site and/or the invariant affinity — integral up to `k − 1` split zips.
   The roster is already fixed, so no matching step follows.

**Optimised / against what measure** — Step 2 on audited book, **per-agent but
un-inflatable**; step 4 on the common measure `M` for balance, with the invariant affinity as
the tie-breaker. Books enter the draw only through the quotient by `G = (ℝ_{>0})^R`, so
FRAME §10 Q5's requirement is met **by construction** rather than by theorem.

**Domains needed** — `economic-theory` (mechanism design: restricted message space,
`green1986` Nested Range Condition, `benporath2014`; seeded, DOMAIN_economic-theory §2.7) and
`optimization` (submodular selection bound, transport LP; seeded).

**The six criteria under this approach**
- C1 — **by computation**: the transport LP enforces equal `M` masses exactly, as A0's does.
- C2 — **by construction**.
- C3 — **by construction**: the roster is chosen first and is the site set; every territory has
  its wholesaler by definition.
- C4 — **by computation**, and expected favourable by construction since territories are grown
  around each wholesaler's own book.
- C5 — **partly by computation, in business units for the roster**: `P₁₃` is an upper bound on
  the book any 13-roster can hold, so "no roster retains more than X% more book" is a
  certificate in book share (LENS_GROMOV Move 4). The map part stays in nats unless U4-disp.
- C6 — **by computation**, but needs a second export route for audited book with the same
  no-dollar guards as `export_instance.py` (FRAME §5).

**Kill experiment** — Two. (i) ★2: if audited book is not available at zip × wholesaler grain,
step 2 has no un-inflatable input and the approach is A1 with the stages reordered. (ii)
LENS_GROTHENDIECK OQ6: measure `spread_S EG_S` on a handful of staff sets; if the fibres are
close, roster-first is bookkeeping and the ordering buys nothing. Depends on ★6, ★2 and
FRAME §6's 675 contested zips (the count among the 13 is LENS_GROMOV U4).

**Why it might beat A0** — FRAME §10 Q9 asks exactly this, and §10 Q5 states the need: a
drawing that reads reported books is unfixable against misreporting (RESEARCH_FINDINGS §9-G,
`fotakis2014`), while one that ignores them leaves up to ~25% of welfare (FRAME §6) on the
table. LENS_GROTHENDIECK descent 5 converts the blocking decision from "books: yes or no" into
"which invariants", and LENS_GROMOV Move 13 splits "books" into reported vs audited — this
approach is the one that takes both literally. DOMAIN_economic-theory §8 Q7 flags the open
risk: a `G`-invariant draw may be "safe and worthless" if it retains little premium.

**Inherits** — none unchanged. `LENS_GROTHENDIECK.md` §5b and `units/U3-inv.md` are the
starting material; re-run both lenses with this charter.

## A3 Hand-drawn state-grouped alignment — the sales-ops baseline

**Family** — No optimisation. Group whole states into buckets that look like `$total/k` each,
then give each bucket to the wholesaler with the most book in it.

**What is decided, in what order**
1. `k` by arithmetic.
2. **The map** at state grain: contiguous groups of states accumulated to ≈ 1/13 of `M`,
   by a stated greedy rule (largest remaining neighbour first) so the construction is
   reproducible rather than literally by hand. States above the band must be split; the rule
   for splitting (by metro or by zip3) is part of the charter and must be written down.
3. **The roster**: for each bucket, the wholesaler with the largest book inside it; conflicts
   (one wholesaler top in two buckets) resolved by the larger share. This is the greedy
   top-pair matching, which U2-stab identifies as the unique stable roster under aligned
   preferences (`eeckhout2000`; BRIEF §3).

**Optimised / against what measure** — Nothing is optimised. Balance is eyeballed on `M` by
state (common); staffing is by book share (per-agent). FRAME §10 Q2 does not arise.

**Domains needed** — none. `economic-theory` supplies the observation that step 3 is the stable
roster, for free.

**The six criteria under this approach**
- C1 — **by construction at state grain, likely failing the band**: FRAME §6 puts TX at 11.5%
  and FL at 6.7% of `M` against a 1/13 ≈ 7.7% target, so an unsplit-state rule cannot land
  inside ±10%; the splitting rule decides whether C1 is met at all.
- C2 — **by construction**: every zip is in its state.
- C3 — **by construction**, given the conflict rule.
- C4 — **by construction**: the assignment rule *is* the continuity number.
- C5 — **not at all**: no bound of any kind.
- C6 — **by computation**: a script over state totals and per-rep book by state; needs no
  coordinates.

**Kill experiment** — None kills it as a *baseline*; FRAME §3 requires it to exist. It dies as
a *candidate* if it loses to A0 on both `V` and C1 by more than the tier-2 floor
(LENS_GROMOV U10). Depends on ★6 and the state-level `M` split in FRAME §6.

**Why it might beat A0** — FRAME §3 names it as the baseline to beat and records that the
headline claim is unevidenced without it. LENS_GROMOV Move 4 warns it is premium-greedy and
balance-sloppy and "may therefore win" on the term worth ~3.7 nats; BRIEF §2 repeats the
warning. It is also the most explainable map (FRAME §4 governance), and its roster is the
stable one.

**Inherits** — none; skip stage 2 entirely and go to a single `python-typed` → `code-verify`
unit. Nothing in the lens files applies.

## A4 Coarse-grain districting

**Family** — Decide the unit before the map: aggregate opportunity and book to metros (CBSA)
or to the two firms' branches, solve an exact districting problem over a few hundred units
with contiguity available as an option, then derive the zip map from the coarse one.

**What is decided, in what order**
1. **The grain** (FRAME A12): CBSA via the public ZCTA→CBSA crosswalk, or firm branch if the
   export can carry a branch key without identifying a firm. Zips in no CBSA get a stated rule.
2. `k` by arithmetic on the aggregated `M`.
3. **The coarse partition**: an exact center-based (Hess) MILP or `scip_tree`-class solve over
   the coarse units, with `mip_rel_gap = 0.0` (trap 12) and, optionally, contiguity on the
   metro adjacency graph, where the 547-component objection (FRAME §4) does not apply.
4. **The roster**: Hungarian on `log g` at the coarse grain, as A0.
5. **The zip map** is derived, not decided: every zip inherits its metro's territory.

**Optimised / against what measure** — `Σ_j log M(A_j)` on the **common** measure at the
coarse grain, as A0, so the equal-size theorem and the analytic ceiling transfer verbatim.
What changes is the unit of decision and hence the unit of every certificate.

**Domains needed** — `optimization` (exact districting, symmetry handling; seeded —
FOUNDATIONS §8 per DOMAIN_optimization §7). GIS / geometry for the crosswalk and adjacency:
**not seeded**.

**The six criteria under this approach**
- C1 — **by computation**, coarser: the granularity floor is the largest metro, not the largest
  zip (FRAME §6: zip 10017 alone is 1.07% of `M`, ~14% of a territory, so a metro can
  plausibly exceed a whole territory).
- C2 — **by construction**, once the crosswalk is total.
- C3 — **by construction**, as A0.
- C4 — **by computation**, as A0.
- C5 — **by computation, and in business units by construction**: with ~hundreds of units an
  exact solve closes the gap to zero, and "no map beats this by more than one metro's
  opportunity" is a displacement statement without passing through the log (FRAME §10 Q7).
- C6 — **by computation**, plus a public crosswalk that adds no confidentiality exposure.

**Kill experiment** — Aggregate `M` to CBSA and compare the largest metro to `$total/k`
plus the C1 band. If it exceeds the band, the grain must be split inside that metro and the
approach degenerates to A0 with extra bookkeeping. Depends on ★6 (the instance's `m_rel` by
zip) and the public crosswalk; no book data needed.

**Why it might beat A0** — FRAME §10 Q10 and A12: if sales ops signs territories by metro or
branch, the zip map is a derived artifact and the tie-breaking degeneracy that produces the
132 dots (FRAME §6) and the second-order-flat objective (FRAME §10 Q4) may not exist at the
signed grain. It answers FRAME A6 (operational coverage rules are metro-shaped) and the
governance requirement that the map be explainable (FRAME §4). RESEARCH_FINDINGS §9-H notes
contiguity may be recoverable on a graph that is not the sold-zip graph; the metro graph is
such a graph. **Frame change flagged:** turning contiguity back on contradicts FRAME §7 ("out
of scope"); a track that wants it must say so in `TRACK_REPORT.md` and let the hub decide.

**Inherits** — none. `LENS_GROMOV.md` OQ6 and `LENS_GROTHENDIECK.md` "the two supports" are
the motivation; re-run both lenses at the coarse grain.

## A5 Ensemble selection

**Family** — Do not optimise the map at all. Sample the set of balance-feasible partitions,
staff every sample, choose the one that staffs best, and certify by the chosen map's position
in the ensemble rather than by a gap to an optimum.

**What is decided, in what order**
1. `k` by arithmetic; the balance band as the feasible set (a constraint on the sampler, not a
   spread to minimise — trap 2 does not fire).
2. **The ensemble**: a large sample of band-feasible partitions from a seeded chain
   (recombination-style moves on the full ZCTA graph, or repeated randomised transport
   solves) — RESEARCH_FINDINGS §3B's pattern, which A0's five-seed portfolio is the smallest
   instance of.
3. **Staff every sample** by Hungarian on `log g` (milliseconds each; `CLAUDE.md`).
4. **Choose** by staffing value `V` and C4, and report the choice as a percentile of the
   ensemble.

**Optimised / against what measure** — Nothing is optimised over maps; `V` on **per-agent**
`u_i` is the ranking statistic, balance on the common `M` is the feasibility set. Books enter
only through the matching, so the "books at stage 2 only" invariant (RESEARCH_FINDINGS §9-G)
holds exactly — the ensemble is drawn blind, and books only pick from it.

**Domains needed** — `optimization` (matching, transport; seeded). Sampling and ensemble
statistics (MCMC mixing, outlier tests): **not seeded**; RESEARCH_FINDINGS §3B lists the
districting-ensemble literature.

**The six criteria under this approach**
- C1 — **by construction**: only band-feasible partitions are sampled.
- C2 — **by construction**.
- C3 — **by computation**, per sample.
- C4 — **by computation**, per sample, and it is the selection statistic.
- C5 — **by computation, in a different unit**: "staffs better than X% of balance-feasible
  maps" is readable without nats but is a distributional claim, not a bound on the best map.
  Whether the sponsor accepts a percentile where FRAME §3.5 asks for a bound is a scope
  question the track must raise.
- C6 — **by computation**: seeded chain, fixed sample size.

**Kill experiment** — Draw a modest ensemble at the band and compute the spread of `V` after
staffing. If it is within the tier-2 floor (FRAME §6: 5e-3 nats), every feasible map staffs
the same and selection is decorative; A0's portfolio spread of 7.1e-2 nats (FRAME §6) is the
weak prior that it is not. Depends on ★6.

**Why it might beat A0** — FRAME §10 Q4 and LENS_GROTHENDIECK descent 4: the objective is
second-order flat near the optimum, so *any* nat-tolerance makes near-optimal maps
indistinguishable — the honest response is to treat them as a population and select on the
term that varies, which is the ~3.7-nat premium (FRAME §6). It keeps the incentive invariant
A1 and A2 must argue for. It is also the cheapest approach to build, since every component
exists in `td/`.

**Inherits** — none unchanged; `LENS_GROMOV.md`'s Move 14 ledger (U1, U7 "is the premium
soft?") is the motivation. Re-run both lenses with this charter.

## Distinctness

- **A0 / A1** — A1 decides the partition and the roster in one solve on `V`; A0 decides the
  partition without ever seeing a roster.
- **A0 / A2** — A2 decides the roster before any geometry exists; A0 decides it last.
- **A0 / A3** — A3 decides at state grain by a greedy rule with no objective; A0 decides at
  zip grain as the maximiser of one.
- **A0 / A4** — A4 decides the decision unit itself and may decide contiguity; A0 takes the zip
  as given and never decides contiguity.
- **A0 / A5** — A5 decides by selecting from a sampled population on staffing value; A0 decides
  by the argmax of a map-only objective.
- **A1 / A2** — A1 lets books shape the map directly; A2 fixes the roster first and lets books
  shape the map only through their inflation-invariant quotient.
- **A1 / A3** — A1 optimises the signed value exactly; A3 optimises nothing.
- **A1 / A4** — A4 decides the grain and solves anonymously on `M` at it; A1 stays at zip grain
  and names territories by rep.
- **A1 / A5** — A1 seeks the optimum of `V`; A5 refuses to optimise the map and reports a
  percentile instead of a gap.
- **A2 / A3** — Both pick reps by book share, but A2 selects the roster from audited book as a
  global max-coverage before any map exists, while A3 picks a rep per bucket after the map.
- **A2 / A4** — A2 decides sites from wholesaler book profiles; A4 decides units from public
  geography and never reads book at the drawing step.
- **A2 / A5** — A2 draws around a fixed roster; A5 draws blind and lets the roster vary per
  sample.
- **A3 / A4** — A4 solves an exact program at the coarse grain and can certify; A3 groups by
  rule and certifies nothing.
- **A3 / A5** — A5 samples thousands of maps and chooses; A3 constructs one.
- **A4 / A5** — A4 changes the unit of decision; A5 keeps the zip and changes the mechanism
  from optimisation to sampling.

## Not approaches (refinements, assigned)

- **Q8 — transport LP at fixed roster with cost `−u_i(z)`, alternated with Hungarian** → **A0**
  as its roster polish (FRAME §10 calls it one cost-matrix change to `centers.py`); it is
  also A1's fixed-`y` linearised restriction (DOMAIN_optimization §2.1), so A1 gets it free.
- **Q11 — home-office / national-accounts carve-out (A11)** → **A0** (hub): a pre-draw step
  that changes `k` for every approach identically; a sponsor question, not a track.
- **Q12 — team territories, `b`-matching (A13)** → **A1**: capacities are a one-line change to
  the rep-indexed formulation; for A0 it replaces Hungarian with a harder problem
  (RESEARCH_FINDINGS §4B). Gated on the sponsor's answer to A13.
- **Contiguity on the full ZCTA graph (RESEARCH_FINDINGS §9-H, LENS_GROTHENDIECK OQ7,
  LENS_GROMOV OQ6)** → **A4**, as its contiguity option on the metro graph. Requires the
  FRAME §7 exclusion to be lifted; the hub decides.
- **Stability-based roster (greedy top-pair, U2-stab; ★3)** → **A3**, whose assignment rule
  is exactly that matching; for **A0** it stays an audit unit, not a mechanism change.
- **Welfare criterion as Atkinson `ε` (U5-crit, ★4) and the `(premium, balance)` Pareto
  frontier (DOMAIN_optimization §2.5)** → **A1**: changes of functional form and of the
  balance band inside the same joint decision.
- **Eisenberg–Gale as "certificate 5" / the collapse of the four certificates (U1-cert)** →
  **A1**: its relaxation, not a separate family.
- **τ-homotopy (DOMAIN_optimization §2.6), matheuristic polish (§2.7), Benders (§2.9)** →
  kill experiments and engineering for **A1**; not tracks.
- **Displacement as the acceptance unit (U4-disp)** → **A0**: a certificate shape every
  approach would adopt; A0 owns it because its certificates are the ones to convert.
- **The 132 dots: cells vs drawn map** → **A0**: a tie-break inside one draw.
- **Vacant / untapped ownership, `filler_capture`, θ directionality** → **A0**: model parameters
  shared by all approaches (FRAME §9).
- **The measurement stage (U7-meas; DOMAIN_optimization §5, DOMAIN_economic-theory §5)** →
  the **hub**, not a track: it is the kill experiment for A0, A1, A2 and A5 at once and should
  run once, on ★6.
