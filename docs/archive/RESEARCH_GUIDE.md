# Research guide — literature reconnaissance for the national-channel programme

**Written:** 2026-09-01 · **For:** an overnight deep-research session · **Report back to:**
this repo (`docs/`), as an annotated bibliography organised by the sections below.

This is a *reconnaissance* brief: find, classify, and annotate the existing academic
literature that bears on what this repo has built, so we know (a) whose shoulders we are
standing on, (b) whether any of our "results" are known theorems with names, (c) whether
anything published contradicts or sharpens our propositions, and (d) which tools we have
not considered. Do not solve our problems; map the terrain around them.

---

## 0. The problem, in enough detail to search well

A firm is creating a "national" sales channel: partition ~1,229 US ZIP codes (each with an
opportunity value `M_z`; total ≈ $13B) into **k = 13 territories of roughly equal
opportunity** (~$1B each), then **assign 13 of 111 sales reps** to those territories
(rectangular assignment doubles as retention selection). Two facts organise everything:

1. **Maximum Nash welfare on a common measure IS equal-size districting.** Every zip lands
   in exactly one district, so `Σ_j M_j` is partition-invariant; maximising `Σ_j log M_j`
   at a fixed sum equalises the terms. Same optimum, not an approximation. (This is the
   Eisenberg–Gale objective over a partition matroid, as far as we can tell — confirm.)
2. **Contiguity died on contact with the data.** The sold-zip Rook adjacency graph has 547
   components (largest 5.1% of mass), so adjacency contiguity is vacuous, and stage 1 is
   **center-based compact assignment** (Hess-style): min `Σ M_z d²(z, c_j)` subject to
   equal district mass, centers updated Lloyd-style. The balanced-assignment core is a
   transportation LP whose basic optima split ≤ k−1 zips (spanning-forest argument).

Stage 2 maximises `Σ_i log g_{i,σ(i)}` (Nash on rep utilities `g_ij`) by the Hungarian
algorithm; utilities mix opportunity, own book, and colleague-book capture at rate θ:
`u_i(z) = (1−λ)S_i + θ(1−λ)(T_z − S_i) + λM_z`. Certification is post-hoc: an analytic
ceiling `Σ log M_j ≤ k log(ΣM/k)`, an integer balance-floor MILP (whose LP relaxation is
provably vacuous), and a pinned-centers assignment MILP (which proved our draw 8.53%
short of compactness-optimal within its own balance band — the adopt-or-not question is
open and lexicographic).

Full formal treatment: `docs/channel_note/channel_note.pdf` (21 pp). Known anchors already
in `docs/channel_note/references.bib` are marked ★ below — do not re-summarise them;
position new findings relative to them.

---

## 1. n-player Nash bargaining and Nash welfare

We use "Nash" in two roles: the **bargaining solution** (the two-player merger programme
this grew from) and **maximum Nash welfare (MNW)** as an allocation objective. Map both
and the bridge between them.

Find:
- Axiomatics of the n-player Nash bargaining solution and its asymmetric/weighted
  variants (Harsanyi, Kalai; weighted-Nash characterisations). Where does the
  bargaining-theoretic justification stop applying when players become *anonymous
  districts* rather than agents with threat points?
- MNW in fair division: ★caragiannis2019 ("unreasonable fairness") we have; find the
  computational lineage — Eisenberg–Gale convex programs, Fisher markets, Cole–Gkatzelis
  and successors on approximating MNW with indivisibles; NP-hardness and APX-hardness
  boundaries for MNW with indivisible goods.
- **The common-measure degeneracy.** Our Proposition "MNW = equal split when all agents
  value everything identically" must be folklore. Find its citable form (possibly in the
  Fisher-market literature: identical utilities ⇒ equal budgets ⇒ equal spending; or in
  Schur-concavity/majorization texts — Marshall–Olkin). We want the *name and canonical
  citation*, not a proof.
- Lexicographic refinements: leximin vs MNW, lexicographic MNW for empty-bundle/zero-value
  cases (our `MODEL.md` §6 open decision). Who has treated MNW with agents that can
  receive nothing?
- Weighted MNW where weights encode district "importance" — relevant if territories are
  ever non-equal by design.

Search phrases: "maximum Nash welfare indivisible", "Eisenberg-Gale integer",
"asymmetric Nash bargaining solution characterization", "lexicographic maximin Nash
welfare zero utilities", "Nash social welfare approximation algorithm".

## 2. Fair division on graphs, and the price of contiguity

Our two-player history lives here, and one open theory question is explicitly ours:
★bei2022 gives price-of-connectivity bounds but **none is known for Nash welfare**.

Find:
- Connected fair division: ★bouveret2017, ★bilo2022, ★suksompong2019, ★deligkas2021 are
  known. Find what came after (2022–2026): EF1/EFX/MNW on paths, trees, general graphs;
  complexity frontiers; any *price of connectivity for Nash welfare* result, however
  partial — this would directly bound what contiguity would have cost us.
- Contiguity relaxations: literature that replaces adjacency contiguity with compactness,
  convexity (geodesic convexity on graphs), or clustering — anyone who *documented the
  same pivot we made* (contiguity infeasible/vacuous on sparse real footprints).
- Fair division where the goods carry geometry (land division, cake-cutting on metric
  spaces) — the continuous analogue of our problem is equitable cake division with
  connected pieces; find the modern computational treatments.

## 3. Districting: political, sales-territory, and service

Find and separate the three literatures; they cite each other rarely.

- **Political districting exact methods**: ★validi2021, ★validibuchanan2022 (Lagrangian +
  branch-and-cut, ~1,500 units certified), ★shirabe2005 (flow), ★oehrlein2017. Find the
  2023–2026 frontier: larger certified instances? SAT/CP approaches? Improved symmetry
  handling beyond ★hess1971 centers?
- **Sampling/ensemble methods**: ★deford2021 (ReCom), ★gurnee2021. Find convergence
  results and whether ensembles have been used for *portfolio generation* the way our
  `score_draws` uses them (draw many, select downstream) — that pattern may have a name.
- **Sales-territory alignment**: ★zoltners2005, ★hess1971, ★riosmercado2009,
  ★salazaraguilar2011, ★rosmercado2012, ★bozkaya2003, ★duque2011. This is our actual
  application. Find: balance-on-multiple-attributes models (opportunity AND workload AND
  book), realignment/disruption minimisation (keeping zips with incumbents — our welfare
  decomposition's second term), and any treatment of **rep retention/selection joint with
  alignment** (our rectangular stage 2).
- **Service districting** (school zones, EMS, waste collection): balanced clustering with
  centers — the closest formulations to our decided stage 1. Capacitated centered
  clustering, "balanced k-means", same-size k-means, constrained k-means via min-cost
  flow (Bradley–Bennett–Demiriz lineage). Our transportation-LP assignment step almost
  certainly exists here under some name — find it and its integrality discussion.

## 4. Mechanism design and matching

We currently assume books `S_i(z)` are truthful data. The moment reps understand the
model, they have incentives. Map what is known:

- Strategyproof allocation under MNW / assignment objectives: impossibilities and
  approximate-strategyproofness for Nash welfare; facility-location mechanism design
  (centers chosen strategically is literally our stage 1 with strategic agents).
- Matching with retention: two-sided matching where one side is selected as well as
  matched (hospital-residents with quotas is close; "matching with contracts" for the
  θ-capture externality). Is our "unmatched = not retained" selection studied as a
  mechanism, and is Hungarian-on-logs (equivalently max-product matching) treated
  anywhere as a *fair* matching rule with axioms?
- Externalities in assignment: our `u_i(z)` depends on colleagues' books (θ term) —
  one-sided matching with externalities, and whether Nash-optimal matching under
  externalities keeps any incentive or stability property.
- Disruption/transition mechanisms: literature on compensating agents for territory
  changes (transfer schemes), if any.

## 5. Optimization: the machinery

- **Outer approximation for concave log objectives**: ★duran1986, ★fletcher1994,
  ★quesada1992, ★bonami2008, ★vielma2011 known. Find: modern OA for `Σ log` specifically
  (Nash welfare MILP/MINLP formulations; "log-sum" MISOCP reformulations — log is
  SOCP-representable via exponential cones: find who solves MNW with Mosek/exponential
  cone exactly, since that could replace our tangent loop).
- **Balanced partitioning bounds**: LPT/makespan (Graham) and bin-packing style bounds
  for the integer balance floor — our constructive certificate is LPT+polish; find the
  tight approximation guarantees so the certificate can quote one.
- **Transportation/assignment integrality**: the ≤ k−1 split-zips lemma is classical
  (basic solutions of transportation problems); find the canonical statement (Dantzig?
  network-flow texts) to cite instead of proving.
- **Symmetry in branch-and-bound**: orbital branching, isomorphism pruning
  (Margot; Ostrowski), symmetry-breaking constraints for anonymous-parts partitioning —
  sharper than our "sort the district masses" trick, and relevant if the floor MILP is
  ever to close its dual side.
- **Column generation / branch-and-price for districting**: set-partitioning formulations
  where a column is a whole district; this sidesteps label symmetry entirely and is the
  most credible route to an *exact* stage 1 with center choice — find the districting
  instances of it (Mehrotra–Johnson–Nemhauser lineage) and modern pricing tricks.
- **k-means exactness**: global optimisation of k-means/centered clustering (Peng–Wei
  SDP relaxations, branch-and-bound k-means) — bounds on how far Lloyd can be from
  optimal, which is exactly the un-certified gap our summary admits.

## 6. Graph theory

- **Győri–Lovász theorem** and successors: every k-connected graph admits a partition
  into k connected parts of prescribed sizes. The existence counterpart to balanced
  connected partition; find algorithmic versions (polynomial cases, approximations) and
  weighted variants — this is the clean theory statement of "when is the balance ceiling
  achievable *with* contiguity".
- Balanced connected partition complexity: BCP_k hardness, approximation ratios, and the
  max-min/min-max variants; spanning-tree methods.
- Separators and cut structure on planar/geographic graphs (our trap-13 machinery):
  anything newer than the sources in the note on lazy separator separation.
- Voronoi/power diagrams on networks: our territory map uses planar Voronoi; power
  diagrams (additively weighted) yield *balanced* partitions with convex cells
  (Aurenhammer; "balanced power diagrams" for districting — Klemm/Brieden–Gritzmann et
  al.). **This may be a strictly better stage-1 formulation than free centers** (convex
  territories by construction) — flag everything on capacity-constrained power diagrams.

## 7. Intersections — where our specific questions live

Rank findings here highest; these are the questions the repo actually has open.

1. **Compactness–balance lexicographics** (open question 1): multi-objective districting
   — who treats balance-then-compactness vs compactness-within-band, and is there a
   principled criterion for choosing? (Our concrete numbers: 8.53% compactness for
   4.7e-5 nats of Nash.)
2. **Price of contiguity for Nash welfare**: any bound, even for paths/trees (§2).
3. **Portfolio-then-select across a decomposed pipeline** (our stage-1-portfolio →
   stage-2-ranking): known in districting ensembles, stochastic programming
   (scenario-then-recourse), or AutoML-style selection? A name and precedent would
   sharpen the note's §6.
4. **MNW matching with selection under externalities** (stage 2's exact shape, §4).
5. **Certificate culture**: post-hoc certification of heuristic districting solutions
   (dual bounds reported beside heuristics) — who does this and how they report the
   "proved / not proved" split (our trap-15 discipline).

---

## Deliverable spec

- One annotated bibliography, organised by sections 1–7, each entry: full citation,
  venue+year, 2–4 sentence annotation stating **what it claims and how it bears on us**
  (which proposition, module, or open question), and a tag: `foundation` / `frontier` /
  `contradicts-or-sharpens` / `tool-we-lack`.
- A shortlist: the **five papers closest to** "maximum Nash welfare balanced districting
  without contiguity, with post-hoc certificates" — our exact niche — and an explicit
  statement of whether the niche appears occupied.
- Every claim of "no result exists" must state where you looked (venues, survey papers,
  search strings). Absence claims are load-bearing here (esp. §2 price-of-contiguity-for-
  Nash and §7.1).
- Flag directly: anything that shows one of our propositions is a known named theorem
  (cite it), and anything published that *contradicts* a claim in `channel_note.pdf`.
- Prefer surveys as entry points (fair division on graphs; districting OR surveys —
  Kalcsics; MNW surveys) and say which survey covers which section.

**Priorities if time-limited:** §7 > §3 (sales-territory + balanced clustering) > §5
(power diagrams via §6, column generation) > §1 > §2 > §4 > rest of §6.
