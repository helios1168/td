# Research findings — literature reconnaissance for the national-channel programme

**Run:** 2026-09-01 (overnight), per `docs/RESEARCH_GUIDE.md` · **Method:** seven parallel
research agents, one per section cluster, each required to verify every citation in a fetched
source (OpenAlex, Crossref, arXiv/ar5iv, Semantic Scholar, dblp, publisher pages) before
reporting, and to record search provenance for every absence claim. ~130 verified entries.
BibTeX for the recommended additions: `docs/RESEARCH_ADDITIONS.bib`.

Tags: `[foundation]` `[frontier]` `[contradicts-or-sharpens]` `[tool-we-lack]`.
★ = already in `docs/channel_note/references.bib` (not re-summarised).

---

## 0. Headline findings

Ordered by consequence. Every item below is expanded, with citations, in the sections that
follow.

1. **Stage 1 is a published named method — under at least four names.** The transportation-LP
   assignment at fixed centers is the **Aurenhammer–Hoffmann–Aronov constrained least-squares
   assignment** (Algorithmica 1998), equivalently **semi-discrete optimal transport** with
   squared-Euclidean cost; the full Lloyd loop is **weight-balanced k-means**
   (Borgwardt–Brieden–Gritzmann, iteration count provably ≤ n^O(dk)) / **constrained k-means**
   (Bennett–Bradley–Demiriz 2000) / the **generalized Lloyd algorithm for centroidal power
   diagrams** (Bourne–Roper 2015: fixed points characterized, energy-decreasing, convergence
   theorem); and Cohen-Addad–Klein–Young (SIGSPATIAL 2018) ran *exactly this algorithm on
   exactly this problem* (balanced districting on US census data). In the OR districting
   literature the family is the **Hess model / location-allocation heuristic** (Hess et al.,
   Operations Research 1965 — note: a different paper from ★hess1971). Presenting it as
   bespoke will read as a literature gap to any OR referee; naming it buys a convergence
   theorem, a redistricting precedent, and an explainability selling point (convex cells,
   average < 6 sides) for free.

2. **⚠ `figures/district_regions.png` is drawn wrong — and the fix yields a free exact
   certificate.** Three agents flagged this independently. A mass-balanced least-squares
   assignment is separated by a **power diagram** (Voronoi with an additive per-center
   weight), not a plain Voronoi diagram; the two differ exactly where balancing forces them
   to, so some zips plot inside the wrong cell. The weights are the **dual variables of the
   mass-balance rows of the transportation LP we already solve**. Reading them out gives, by
   complementary slackness, an exact solver-independent optimality certificate for the
   assignment at fixed centers (each zip minimises `d²(z,c_j) − w_j`) — stronger and cheaper
   than the pinned-centers MILP, which becomes a cross-check. Treat as a correctness bug in
   `tools/us_maps.py`, not cosmetics.

3. **Proposition "MNW on a common measure = equal-size districting" is a known named
   theorem — twice — and its indivisible form is NP-hard.** Divisible/relaxed form:
   Σ log is symmetric + strictly concave ⇒ **strictly Schur-concave** ⇒ uniquely maximised
   at the equal vector (majorization; Marshall–Olkin–Arnold, Ch. 3); economics name:
   symmetry + **Pigou–Dalton** (Moulin 2003); networking name: **proportional fairness**
   (Kelly 1997/98). Cite, don't prove. Integer form: MNW under identical additive
   valuations **remains NP-hard** (Barman–Krishnamurthy–Vaish) — it *is* balanced multiway
   number partitioning — with a PTAS (Nguyen–Rothe) and an **additive PTAS via target load
   balancing** (Inoue–Kobayashi → Buchem et al.). So "the $1B target needs no constraint,
   balance falls out" is exact in the relaxation and misleading at the integer level; the
   0.78% winner spread should be reported against the balanced-partition gap, not zero.

4. **The ≤ k−1 split-zips lemma is published, in our exact (mass-weighted) generality.**
   Brieden–Gritzmann–Klemm (EJOR 2017), Lemma 4: at most k−1 fractionally assigned points,
   ≤ 2(k−1) fractional components, by acyclicity of the assignment graph. Their Theorem 5
   turns it into a quotable rounding bound: ε-balance achievable with
   ε ≥ max_z M_z / κ_j — a spread bound in business units. Underlying basis fact:
   Dantzig 1963 / Ahuja–Magnanti–Orlin 1993 (spanning-tree bases, m+n−1 positive
   variables); OT phrasing: Peyré–Cuturi Prop. 3.4. Cite, don't prove.

5. **The "~1,500 units is the published state of the art" claim (CLAUDE.md, CHANNEL.md) is
   stale by two orders of magnitude.** The Validi–Buchanan group now reports provably
   optimal plans for **all** US congressional and legislative instances (whole-counties
   objective, combinatorial Benders; Shahmizad–Buchanan, MPC in revision) and experiments at
   **175,000 vertices** with inexact contiguity (Jolly–Buchanan 2026). Our 1,229 zips is
   small; the binding difficulty is the log objective and the 547-component graph, not size.

6. **The lexicographic-MNW open decision (MODEL.md §6, empty bundles) is already answered
   by our own anchor.** ★caragiannis2019's MNW definition *is* the lexicographic one:
   first maximise the number of agents with positive value, then the product over those.
   Adopt it verbatim; close the decision.

7. **The choice of log is not identified by the balance goal.** Brandl–Suksompong–Teh
   (arXiv 2026): under a degeneracy of exactly our type, MNW, leximin, and *every* strictly
   concave additive welfarist rule coincide. A Σ M_j² objective (convex quadratic, SCIP-native,
   no OA cuts) has the same equal-split optimum in the degenerate regime. Cheap decisive
   test: re-run the k=13 draw with the quadratic and diff the partition.

8. **Two verified absences that are ours to claim** (search provenance in §8):
   (a) **no price-of-connectivity bound for Nash welfare exists** — the 2026 sequel paper
   that would contain it (Bei–Lam–Lu–Suksompong, DAM 385) does not contain the word "Nash";
   (b) **no districting paper formulates districting as Nash-welfare maximisation** — our
   bridge appears novel. Additional open niches: capacity-constrained power diagrams have
   never been applied to *sales/commercial* territory design (all applications are
   political/graphics/materials); no model jointly performs territory alignment and rep
   **retention/selection**; no incentive-ratio result for max-product matching with a
   selection margin.

9. **Stage 2 is also a named object with known limits.** It is **Nash social welfare
   matching** (Jain–Vaish AAAI 2024; Gokhale et al. AAMAS 2025). Our exactness is an
   artifact of capacity 1 per district (Σ log separable ⇒ linear assignment); NP-hard at
   capacity 2 with values in {0,1,2}. The MNW axiomatizations (Suksompong 2023; Yuen–
   Suksompong 2023: unique welfarist rule satisfying EF1) are for endogenous bundles and do
   **not** automatically transfer to our fixed-bundle matching — a gap the note should not
   paper over. Known impossibilities that apply: no strategyproof + Pareto-optimal rule on
   our (linear) domain except dictatorship (Schummer 1996); for k ≥ 3 facilities no
   deterministic anonymous strategyproof placement with bounded approximation (Fotakis–
   Tzamos) — so **stage 1 must never read rep reports** (it currently doesn't; make that an
   explicit design invariant). Countervailing: MNW's incentive ratio is exactly 2
   (Bei et al., AIJ 2025) — manipulation is bounded; and on **binary** valuations
   deterministic MNW with lexicographic tie-breaking is *group strategyproof* (Halpern et
   al., WINE 2020) — binarising books would buy truthfulness with no change of rule.

10. **The Nash-vs-utilitarian matching choice has a hidden cost** (Halpern–Shah, SAGT 2019):
    an assignment is envy-freeable by transfers **iff** it maximises *utilitarian* welfare
    over bundle reassignments. Whenever our Nash matching differs from the utilitarian one —
    the very case that motivates Nash — no compensation scheme can make it envy-free.
    Two-line test on the certified draw: Hungarian on g vs Hungarian on log g.

---

## 1. n-player Nash bargaining and Nash welfare (guide §1)

### 1A. Axiomatics; where the bargaining pedigree stops

- **kaneko1979** — Kaneko & Nakamura, "The Nash Social Welfare Function", *Econometrica* 47,
  1979. DOI 10.2307/1914191. `[foundation]` **The pivot citation.** Converts the Nash
  bargaining solution into a social welfare function over a fixed population via Arrow-style
  axioms — the licence for a Nash product over anonymous districts. Cite this, not ★nash1950,
  wherever the note leans on the bargaining reading.
- **harsanyi1963** — Harsanyi, "A Simplified Bargaining Model for the n-Person Cooperative
  Game", *Int. Economic Review* 4, 1963. DOI 10.2307/2525487. `[foundation]` The canonical
  n-player extension — but of *coalitional* bargaining with threat points; buys us the name
  only.
- **roth1979** — Roth, *Axiomatic Models of Bargaining*, Springer LNEMS 170, 1979.
  DOI 10.1007/978-3-642-51570-5. `[foundation]` Use to state which axioms die under
  anonymity: scale-invariance is vacuous on a common measure, individual rationality empty
  at d = 0; what survives (symmetry + Pareto + Pigou–Dalton) is an inequality-index
  argument, not a bargaining argument.
- **rachmilevitch2015** — "A characterization of the asymmetric Nash solution", *Rev. Econ.
  Design* 19(2), 2015. DOI 10.1007/s10058-015-0167-8. `[frontier]` Minimal weighted-Nash
  characterization; the weights are bargaining powers, not entitlements — entitlements need
  §1E.
- **trockel2008** — "The Nash product is a utility representation of the Pareto ordering",
  *Economics Letters*, 2008. DOI 10.1016/j.econlet.2007.04.017. `[contradicts-or-sharpens]`
  The Nash product per se carries no bargaining content — it lives in the axioms and d.
  Supports using Σ log M_j over districts without pretending they bargain.
- **landau2008** — Landau, Reid, Yershov, "A fair division solution to the problem of
  redistricting", *Social Choice and Welfare*, 2008. DOI 10.1007/s00355-008-0336-6.
  `[foundation]` The one genuine fair-division-applied-to-districting paper — agents are the
  two *parties*, districts are the objects. Citable precedent for our two-player origin; not
  for a product over districts.
- **brandl2021** — Brandl, Brandt, Greger, Peters, Stricker, Suksompong, "Funding public
  projects: A case for the Nash product rule", *J. Math. Economics*, 2021.
  DOI 10.1016/j.jmateco.2021.102585. `[frontier]` Closest published "Nash product justified
  without a bargaining story" (participatory budgeting) — still agent-indexed.
- **kalcsics2005** — Kalcsics, Nickel, Schröder, "Towards a unified territorial design
  approach", *TOP* 13(1):1–56, 2005. DOI 10.1007/BF02578982. `[tool-we-lack]` The commercial
  territory-design survey our stage 1 actually sits in; treats balance as a ±τ constraint,
  never as a Nash product — the contrast is where our contribution lives (see §3).

### 1B. MNW computational lineage

- **eisenberg1961** — Eisenberg, "Aggregation of Utility Functions", *Management Science*
  7(4), 1961. DOI 10.1287/mnsc.7.4.337. `[foundation]` The correct citation for "our
  objective is an Eisenberg–Gale program"; its degree-one homogeneity hypothesis is the
  general form of our scale-invariance proposition (inherited, not new).
- **jain2010** — Jain & Vazirani, "Eisenberg–Gale markets: Algorithms and game-theoretic
  properties", *GEB* 70:84–106, 2010. DOI 10.1016/j.geb.2008.11.011. `[tool-we-lack]`
  **Where the "EG over a partition matroid" conjecture belongs** — EG programs over arbitrary
  combinatorial polytopes, with rationality results that bear on trap 12 and whether
  tier-1 `CERT_TOL` is even the right kind of tolerance. Read before writing the claim into
  the note.
- **devanur2008** — Devanur, Papadimitriou, Saberi, Vazirani, *JACM* 2008.
  DOI 10.1145/1411509.1411512. `[foundation]` Combinatorial poly-time algorithm for linear
  Fisher markets.
- **livondrak2021** (FOCS 2021, DOI 10.1109/FOCS52979.2021.00012), **garg2021rado**
  (STOC 2021, DOI 10.1145/3406325.3451031 — Rado valuations: the closest published class to
  a partition-matroid setting), **garg2023** (STOC 2023 / JACM 2026, DOI 10.1145/3807505),
  **dobzinski2023** (arXiv:2309.04656), **bei2026nsw** (arXiv:2504.09669) — `[frontier]`
  the O(1)-approximation ladder for submodular/subadditive/weighted NSW; garg2023's
  matching-plus-local-search template is what a *joint* stage-1+2 formulation would look
  like, and the best argument that our split is the pragmatic one.
- **fenghuli2026** — Feng, Hu, Li, "New Convex Programming Technique for Nash Social
  Welfare and Scheduling", arXiv:2604.24120. `[tool-we-lack]` **Directly actionable:** a
  compact polynomial-size LP relaxation of weighted NSW at additive ln(1+ε) loss — a
  candidate independent dual bound to cross-check `allocate_districts`, solvable by a stock
  LP solver. Four months old; unused in districting.

### 1C. The common-measure degeneracy — names and citations (guide's key task)

- **marshall2011** — Marshall, Olkin, Arnold, *Inequalities: Theory of Majorization and Its
  Applications*, 2nd ed., Springer, 2011. DOI 10.1007/978-0-387-68276-1. `[foundation]`
  **The canonical citation.** Symmetric + strictly concave ⇒ strictly Schur-concave; the
  equal vector is the majorization minimum on a fixed-sum simplex ⇒ unique maximiser.
  Equivalently AM–GM with its equality condition. Three lines instead of a proposition.
- **moulin2003** — Moulin, *Fair Division and Collective Welfare*, MIT Press, 2003.
  DOI 10.7551/mitpress/2954.001.0001. `[foundation]` The economics name: symmetry +
  Pigou–Dalton + Pareto.
- **kelly1997/kelly1998** — Kelly, *Eur. Trans. Telecom.* 8, 1997 (DOI 10.1002/ett.4460080106);
  Kelly, Maulloo, Tan, *JORS* 49, 1998 (DOI 10.2307/3010473). `[foundation]` The networking
  name: **proportional fairness**; under symmetric constraints the PF allocation is equal.
  Independent rediscovery — one sentence in the note.
- **barmanKV2018greedy** — Barman, Krishnamurthy, Vaish, "Greedy Algorithms for Maximizing
  Nash Social Welfare", arXiv:1801.09046 (AAMAS 2018 — venue unconfirmed in a fetched
  record; cite arXiv). `[contradicts-or-sharpens]` **The sharpest correction to CLAUDE.md:**
  MNW "remains NP-hard" under identical valuations (verbatim); 1.061-greedy.
- **nguyen2014** — Nguyen & Rothe, *DAM* 2014. DOI 10.1016/j.dam.2014.09.010.
  `[foundation]` PTAS for NSW under identical additive valuations; establishes the setting
  as a named subproblem.
- **inoue2022** — Inoue & Kobayashi, IPCO 2022, DOI 10.1007/978-3-031-06678-8_25 (journal:
  *JORSJ* 68:133, 2025). `[tool-we-lack]` **Additive PTAS via target load balancing** —
  error in ε·v_max, i.e., dollars-per-largest-zip: a business-readable acceptance criterion
  for stage 1, unlike nats.
- **buchem2021** — Buchem, Rohwedder, Vredeveld, Wiese, ICALP 2021,
  DOI 10.4230/LIPIcs.ICALP.2021.42. `[tool-we-lack]` The additive-PTAS machinery; "target
  load balancing with target $1B on 13 machines" is stage 1 minus geometry.
- **fengli2025** — Feng & Li, *TheoretiCS* 4, 2025. DOI 10.46298/theoretics.25.17.
  `[contradicts-or-sharpens]` The general weighted-NSW approximation ratio is *governed by*
  the identical-additive-valuations gap — our instance is the hard core of the field, not a
  degenerate corner. Strong framing sentence for the note.
- **barmanKV2018ec** (EC 2018, DOI 10.1145/3219166.3219176), **barman2020**
  (IJCAI 2020, DOI 10.24963/ijcai.2020/7 — identical *subadditive*), **darmann2015**
  (*EJOR* 2015, DOI 10.1016/j.ejor.2015.05.071 — OR-venue complexity). `[foundation]`

### 1D. Lexicographic refinements and empty bundles

- ★**caragiannis2019** — already defines MNW lexicographically (maximise count of
  positive-utility agents, then the product). **Adopt verbatim; close MODEL.md §6's
  empty-bundle decision.** Operationally: first maximise the number of non-empty districts
  (binds only in pathological draws at k=13/$13B), then Σ log.
- **halpern2020** — Halpern, Procaccia, Psomas, Shah, WINE 2020,
  DOI 10.1007/978-3-030-64946-3_26. `[contradicts-or-sharpens]` Binary valuations: all MNW
  allocations share a utility profile; leximin and MNW coincide; and the rule is **group
  strategyproof** (see §4).
- **brandl2026** — Brandl, Suksompong, Teh, "Fair Division with Binary Valuations:
  Characterizations", arXiv:2607.10064. `[contradicts-or-sharpens]` Under the degeneracy,
  MNW = leximin = *every* strictly concave additive welfarist rule. The most consequential
  finding for solver work — the log is not identified; a quadratic may serve (headline 7).
- **plaut2018** — Plaut & Roughgarden, SODA 2018, DOI 10.1137/1.9781611975031.165.
  `[foundation]` leximin++ — the natural tie-breaker if trap 4 (mass ties) bites.
- **amanatidis2021** — *TCS* 863:69–85, 2021, DOI 10.1016/j.tcs.2021.02.020. `[frontier]`
  MNW ⇒ EFX only up to two distinct values — bounds what fairness the draw buys under
  heterogeneous M_z.
- **wang2024matroid** — arXiv:2411.01462. `[frontier]` MNW under matroid constraints keeps
  only 1/2-EF1 — the fairness-side test of the "EG over a partition matroid" reading.

### 1E. Weighted MNW as entitlements (if territories go non-equal by design)

- **chakraborty2021** — *ACM TEAC* 2021, DOI 10.1145/3457166. `[foundation]` WEF1; max
  weighted Nash welfare ⇒ WEF1.
- **chakraborty2021revisited** — arXiv:2112.04166. `[frontier]` The competing weighted
  notions disagree; read before picking weights.
- **suksompong2022** — *Math. Social Sciences* 117:101–108, 2022,
  DOI 10.1016/j.mathsocsci.2022.03.004. `[frontier]` Binary MWNW: resource/population
  monotone, group-strategyproof, poly-time — the only monotonicity proof found for a
  weighted Nash rule.
- **brown2024** — arXiv:2401.02918. `[frontier]` Weighted-NSW approximation degrades in
  D_KL(w‖uniform): mild deliberate imbalance is nearly free — quantitative answer if the
  business asks for oversized territories.

---

## 2. Fair division on graphs; the price of contiguity (guide §2)

### 2A. Connected fair division, 2022–2026

- **chen2024cutsets** — Chen & Zwicker, "Cutsets and EF1 Fair Division of Graphs",
  arXiv:2402.05884; AAMAS 2024 EA. `[frontier]` Forbidden cutset structures blocking EF1
  under connectivity; our 547-component graph is the degenerate limit — the citation for
  "contiguity was obstructive, not merely inconvenient."
- **gahlawat2026incomplete** — Gahlawat & Zehavi, *JAAMAS* 40, 2026,
  DOI 10.1007/s10458-026-09760-w; FSTTCS 2023. `[frontier]` *Incomplete* CFD — only p
  vertices allocated, rest unassigned; mapped complexity. The right frame for "who owns
  untapped/vacant zips" (MODEL.md §6).
- **ajaykrishnan2025beyond** — arXiv:2512.22475, FSTTCS 2025. `[frontier]` Exact EF-ICFD
  hard even on stars; ε-relaxation ⇒ efficient approximation scheme — independent,
  principled justification for our two-tier acceptance band.
- **blazej2025mms** — arXiv:2508.06343. `[frontier]` Connected-MMS frontier (block graphs,
  cacti, …) — nothing about many-component graphs; our instance is outside every
  domesticated class.
- **hosseini2025nonmonotonicity** — arXiv:2511.03629. `[frontier]` Cut-value valuations —
  closest treatment of value-on-the-boundary (cf. our perimeter term).
- **mancho2025equalsized** — Mancho, Markakis, Protopapas, SAGT 2025, arXiv:2507.20899.
  `[tool-we-lack]` Fixed-size bundles: MNW guarantees tight 1/2-EFF1 — the only found result
  where MNW retains a fairness guarantee under an explicit balance constraint. Cite next to
  Proposition 1.

### 2B. Price of connectivity for Nash welfare — the load-bearing absence

- **bei2026welfareloss** — Bei, Lam, Lu, Suksompong, "Welfare loss in connected resource
  allocation", *DAM* 385:1–23, 2026, DOI 10.1016/j.dam.2026.01.007; arXiv:2405.03467.
  `[frontier]` The direct sequel to ★bei2022: egalitarian and utilitarian price of
  connectivity, tight bounds. **Full-text scan of the ar5iv rendering: the string "Nash"
  does not appear.** Conclusion: **no price-of-connectivity bound for Nash welfare exists,
  on any graph class including paths and trees** (provenance: §8).
- **arunachaleswaran2019cakensw** — WINE 2019, DOI 10.1007/978-3-030-35389-6_5.
  `[foundation]` 3+o(1)-approx for NSW over *connected* cake divisions + APX-hardness —
  bounds the gap within the connected class; the connectivity *price* was never taken.
- **segalhalevi2018monotonicity** — *Math. Social Sciences* 2018,
  DOI 10.1016/j.mathsocsci.2018.07.001. `[contradicts-or-sharpens]` The only qualitative
  Nash cost of connectivity: the connected Nash-optimal rule loses proportionality. A
  ready-made lower-bound construction if we prove the price ourselves.

### 2C. Contiguity relaxations — the pivot, formalized

- **madathil2023compact** — Madathil, "Fair Division of a Graph into Compact Bundles",
  IJCAI 2023, DOI 10.24963/ijcai.2023/316. `[tool-we-lack]` **Our pivot has a name:
  (α,β)-compactness** — V covered by α balls of radius β; connectivity = (1, m−1); α > 1
  licenses disconnected multi-center bundles. Strongly NP-hard for α ≥ 3 even on *edgeless*
  graphs (our regime's caricature). Gives stage 1 a citable predicate and a principled knob
  in place of a binary contiguity flag.
- **jolly2026** — Jolly & Buchanan, "A guide to inexact contiguity constraints",
  Optimization Online, posted 2026-08-17, submitted. `[frontier]` `[contradicts-or-sharpens]`
  Tree-based (★zoltners1983!), distance-based (Mehrotra et al. 1998), and DAG-based inexact
  contiguity, benchmarked to 175k vertices, with counts of real districts satisfying each.
  **Center-based assignment is distance-based inexact contiguity in disguise** — the
  citation that turns our abandonment of exact contiguity into a recognized modelling
  choice.
- **barnes2021compactness** — Barnes & Solomon, *Political Analysis* 29(4), 2021,
  DOI 10.1093/pan/… (arXiv:1803.02857). `[contradicts-or-sharpens]` Compactness scores are
  implementation-sensitive ⇒ **our 8.53% is measure-relative**; check the ordering survives
  a second measure before treating it as decision-grade.
- **ryzhov2025geographical** — Ryzhov, Carlsson, Zhu, arXiv:2511.19722. `[frontier]`
  Group-fair geographic partitioning; optimum is a generalized additively weighted Voronoi
  diagram (resolves a 1951 Dvoretzky et al. question) — independent confirmation of the
  power-diagram structure, and a template for multi-attribute balance.
- **elkind2023separation** — *Computational Geometry* 113:102006, 2023,
  DOI 10.1016/j.comgeo.2023.102006; IJCAI 2021 distinguished paper. `[frontier]` Under real
  geometric constraints exact proportional targets are unattainable in any multiplicative
  approximation — a *band* is the only coherent goal (cf. our $1B ± 10% ceiling finding).
- **jost2025** — Jost, Escobedo, Kirchheim, "Why Districting Becomes NP-hard",
  arXiv:2510.25614. `[foundation]` Exact P/NP-hard boundary as constraint groups
  (balance/contiguity/compactness) drop or relax — cite a threshold result instead of an
  empirical excuse for the pivot.
- **dharangutte2025** — Dharangutte, Gao, Huang, Yu, FORC 2025, arXiv:2501.17277.
  `[frontier]` Two-weight balanced districting with star districts: n^(1/2−δ)-inapproximable
  in general, O(log n) planar. Star districts are the theory counterpart of center-based;
  our tractability comes from geometry, not combinatorics.

---

## 3. Districting: political, sales-territory, service (guide §3)

### 3A. Political districting — exact methods, the 2023–2026 frontier

- **shahmizad2026** — Shahmizad & Buchanan, "Political districting to maximize whole
  counties", *Math. Programming Computation* (in revision; Optimization Online 2025/10).
  `[frontier]` `[contradicts-or-sharpens]` Combinatorial Benders (master picks whole
  counties, subproblem repairs/validates); **provably optimal plans for all US congressional
  and legislative instances**. Kills the "1,500 units is the ceiling" framing; also the
  template for closing our open-loop draw/match split with feedback cuts.
- **shahmizad2025** — Shahmizad & Buchanan, "Political Districting to Minimize County
  Splits", *Operations Research* 73(2):752–774, 2025. DOI 10.1287/opre.2023.0094.
  `[frontier]` Source of DAG contiguity; **also uses ordering constraints
  (z_{i1} ≥ z_{i2} ≥ …) for symmetry — a top-venue precedent for our mass-sorting device.**
  Its counting argument for county-split lower bounds is the integer-side twin of our
  split-zips lemma (same forest bookkeeping, opposite direction); companion Election Law J.
  paper (DOI 10.1089/elj.2024.0040) refutes a folk belief about minimum splits — check
  before asserting tightness of "≤ k−1 splits" (it is "there exists an optimum with", not
  "every optimum").
- **belotti2025** — Belotti, Buchanan, Ezazipour, "Political districting to optimize the
  Polsby-Popper compactness score…", *Operations Research* 73(5):2330–2350, 2025.
  DOI 10.1287/opre.2024.1078. `[frontier]` MISOCP for a perimeter-ratio compactness
  *objective* at census-block scale — the model to copy if §7.1 needs a legally grounded
  compactness notion.
- **ezazipour2025** — Ezazipour, Belotti, Buchanan, Walteros, "Finding Pareto-optimal
  districting plans", submitted to M&SOM (major revision 2025-11). `[tool-we-lack]`
  Metadata only (no abstract retrievable anywhere). **The title names our open decision.**
  Watch Optimization Online / email the authors before settling §7.1 by fiat.
- **zhang2025ijoc** — Zhang, Silveira, Validi, Smith, Buchanan, Hicks, "Partitioning a
  graph into low-diameter clusters", *IJOC*, to appear. DOI 10.1287/ijoc.2025.1448.
  `[frontier]` Exact bounded-diameter partitioning — a certified compactness *constraint*
  that survives a disconnected graph (metric, not adjacency, diameter).
- **swamy2023** — Swamy, King, Jacobson, *Operations Research* 71(2):536–562, 2023.
  DOI 10.1287/opre.2022.2311. `[frontier]` Multilevel matching-based contraction — a cheap
  way to shrink 1,229 zips before any MILP, and a worked multiobjective districting example.
- **brous2025** — Brous & Shmoys, SIAM ACDA 2025, arXiv:2508.07446. `[frontier]` Stochastic
  hierarchical partitioning → column generation inside an IP → local search. The closest
  published relative of `score_draws`, upgraded to an optimizing master.
- **chopra2023** — Chopra, Park, Shim, *Parallel Processing Letters* 33(1–2), 2023.
  DOI 10.1142/S0129626423400017. `[frontier]` Exact optimum for South Carolina; read for
  formulation strengthening.
- **smith2024** — Smith & Boutilier, arXiv:2406.09457. `[tool-we-lack]` Inverse
  optimization for districting — sideways use: infer the implied λ/θ that makes the
  incumbent territory map optimal (sanity check against the business's existing alignment).
- **validi2022 (★validi2021)** — note their headline "districting does not get harder when
  contiguity is imposed" is a live counterpoint: our obstruction is *connectivity* of the
  sold-zip graph, not difficulty. See reframing R-C4 (full-ZCTA-graph experiment).
- *Absence:* **no SAT/CP/CP-SAT exact districting engine with certified optimality** exists
  (provenance §8) — the exact frontier is all branch-and-cut/Benders MILP; our
  transportation-LP core supplies the LP relaxation that lane would give up.

### 3B. Ensembles, sampling, and the portfolio pattern (guide §7.3)

- **cannon2026** — Cannon, Duchin, Randall, Rule, *SIAM Review* 68(2):349–381, 2026.
  DOI 10.1137/24M166944X. `[foundation]` RevReCom: proved stationary distribution (spanning
  tree distribution) — the canonical null model, at a cost.
- **charikar2022** (arXiv:2206.04883) and **gold2026** (arXiv:2606.01333)
  `[contradicts-or-sharpens]` ReCom is exponentially slowly mixing (proof + adversarial
  families). **If any text implies our portfolio spread approximates a null distribution,
  these contradict it.** The honest claim: the portfolio is a *diverse solution pool*.
- **cannon2024stoc** — STOC 2024, DOI 10.1145/3618260.3649699. `[frontier]` First provably
  poly-time balanced-partition sampling under the spanning-tree distribution (grids).
- **cannon2025** — arXiv:2508.11130. `[tool-we-lack]` Direct O(n) balanced tree-weighted
  2-partition sampling — the current best randomized draw-generator primitive.
- **autry2023** — *SIAM J. Applied Math*, 2023, DOI 10.1137/21M1418010. `[foundation]`
  Metropolized forest recombination — sample from a *specified* distribution.
- **mccartan2023** — McCartan & Imai, *AoAS* 17(4), 2023, DOI 10.1214/23-AOAS1763.
  `[tool-we-lack]` SMC redistricting sampler with importance weights — the only route to a
  statement like "the winner is in the top q% of achievable draws," which our portfolio
  currently cannot support.
- **clelland2026** — arXiv:2603.18347. `[frontier]` Bonsai: independent (non-MCMC) partition
  samplers with characterized distributions.
- **The portfolio pattern has names.** (1) *District ensemble + master selection problem* —
  ★gurnee2021's own phrasing; their master is an **IP over the pool**, returning a
  pool-optimal plan *and a pool-restricted bound* — `score_draws` merely ranks, leaving a
  bound on the table. (2) *Diverse MIP solution pools*: **danna2009** (Danna & Woodruff,
  *ORL* 37(4):255–260, 2009) `[foundation]` — the formal statement of why the portfolio
  exists; **ahanor2023** (DiversiTree, arXiv:2204.03822) `[tool-we-lack]` — diversity-aware
  node selection inside B&B, the principled replacement for random-restart Lloyd diversity.
  (3) Scenario-then-recourse (stochastic programming): the *weakest* match — do **not**
  claim it; we have no uncertainty model.
- **mehrotra1998** — Mehrotra, Johnson, Nemhauser, *Management Science* 44(8):1100–1114,
  1998. DOI 10.1287/mnsc.44.8.1100. `[foundation]` Branch-and-price over districts-as-
  columns — the original generate-then-select AND the origin of distance-based contiguity:
  two of our design choices trace to this one paper.
- **abrishami2019** — arXiv:1910.09618. `[tool-we-lack]` An LP metric between graph
  partitions — a principled portfolio-diversity measure for `score_draws`.

### 3C. Sales-territory alignment (our actual application)

- **kalcsics2019** — Kalcsics & Ríos-Mercado, "Districting Problems", *Location Science*
  2nd ed., Springer, 2019, 705–743. DOI 10.1007/978-3-030-32177-2_25. `[foundation]` The
  current reference survey; cite for framing in CHANNEL.md.
- **riosmercado2021** — Ríos-Mercado, Álvarez-Socarrás, Castrillón-Escobar, López-Locés,
  *Computers & OR* 126:105106, 2021. DOI 10.1016/j.cor.2020.105106.
  `[contradicts-or-sharpens]` **Load-bearing warning:** same location-allocation
  architecture as ours, with *two* balancing activities — and the abstract states the
  location-allocation theoretical properties "no longer hold" under multiple-activity
  balance. Our clean transportation LP (and the ≤ k−1 lemma) exists *because* we balance a
  single attribute. Adding workload/book as a second hard balance destroys the structure.
- **salazar2012** — Salazar-Aguilar, Ríos-Mercado, González-Velarde, Molina, *AOR*
  199(1):343–360, 2012. DOI 10.1007/s10479-011-1045-6. `[foundation]` The field's answer to
  dispersion-vs-balance: report the Pareto front, let the decision-maker pick — precedent
  for §7.1.
- **bender2016** — Bender, Meyer, Kalcsics, Nickel, *Transp. Research E* 96:135–157, 2016.
  DOI 10.1016/j.tre.2016.09.007. `[frontier]` Multi-period redesign with change as a
  modelled cost — the field's default is an explicit change penalty, whereas our welfare
  decomposition delivers incumbent-preservation as a theorem. That contrast is a
  contribution.
- **yanik2019** — *ITOR* 26(5):1676–1697, 2019. DOI 10.1111/itor.12633. `[frontier]`
  Multi-period, multi-criteria, *gradual* (fractional) assignment — how the field justifies
  shared units.
- **moyagarcia2020** — Moya-García & Salazar-Aguilar, ISOR 284, Springer, 2020, 191–206.
  DOI 10.1007/978-3-030-34312-5_10. `[frontier]` Territory design *for salesforce sizing* —
  the nearest relative of stage-2-as-retention; abstract withheld, metadata verified only.
  One PDF away from revising the "retention-selection is unstudied" claim.
- **zoltners2011oxford** — DOI 10.1093/oxfordhb/9780199569458.003.0011. `[foundation]`
  Sizing and alignment as one decision (qualitative).
- **haase2014** — Haase & Müller, *EJOR* 237(2):677–689, 2014.
  DOI 10.1016/j.ejor.2014.01.061. `[tool-we-lack]` Bounds for sales-force deployment *with*
  contiguity — dual-bound template in our own application domain.
- **chen2025www** — Chen, Wang, Shu, Liu, Wang, WWW Companion 2025, 143–151.
  DOI 10.1145/3701716.3715207. `[frontier]` Deployed industrial sales-territory system:
  O(|V|)-size global Polsby–Popper term in the objective + hierarchical pre-segmentation —
  compactness-in-objective without a lexicographic pass, and our component decomposition
  done deliberately.
- **elizondo2014** — Elizondo-Amaya, Ríos-Mercado, Díaz, *Computers & OR* 44:193–205, 2014.
  DOI 10.1016/j.cor.2013.11.006. `[foundation]` Lagrangian dual bounds for territory design
  with a primal heuristic in the loop — our domain already reports heuristic + gap as
  standard practice (see §7.5).
- *Absence:* **no published model jointly performs territory alignment and rep
  retention/selection** (choosing which named incumbents survive); nearest are
  moyagarcia2020 (headcount, not identity) and zoltners2011oxford. Also: no territory paper
  derives incumbent-preservation from the objective (all penalize change explicitly), and
  no *sales* paper states the ≤ k−1 corollary. Provenance §8.

### 3D. Service districting & balanced clustering with centers (the decided stage 1)

- **hess1965** — Hess, Weaver, Siegfeldt, Whelan, Zitlau, "Nonpartisan Political
  Redistricting by Computer", *Operations Research* 13(6):998–1006, 1965.
  DOI 10.1287/opre.13.6.998. `[foundation]` **The canonical name for stage 1** (distinct
  from ★hess1971). `centers.py` is a mass-weighted Hess model; say so.
- **bennett2000 (a.k.a. bradley2000)** — Bennett, Bradley, Demiriz, "Constrained K-Means
  Clustering", MSR-TR-2000-65, 2000. `[foundation]` Assignment step as min-cost
  flow/transportation — our exact core, published 2000. (MSR author order:
  Bennett–Bradley–Demiriz; PDF is image-only, integrality wording verified via the
  k-means-constrained implementation docs.)
- **malinen2014** — Malinen & Fränti, S+SSPR 2014, LNCS 8621, 32–41,
  DOI 10.1007/978-3-662-44415-3_4; revisited de Maeyer–Sieranoja–Fränti, *ACI* 3(2), 2023,
  DOI 10.3934/aci.2023008; extended "Fixed-sized clusters k-Means", arXiv:2501.16113, 2025.
  `[foundation]` Count-balanced Lloyd via Hungarian O(n³); our mass-weighted transportation
  formulation is the better-conditioned family member — cite the pair to show the lineage.
- **zhu2010** — *Knowledge-Based Systems* 23(8):883–889, 2010.
  DOI 10.1016/j.knosys.2010.06.003. `[foundation]` Size-constrained assignment as network
  flow — the other ML-side name.
- **negreiros2006** — Negreiros & Palhano, *Computers & OR* 33(6):1639–1663, 2006.
  DOI 10.1016/j.cor.2004.11.011. `[foundation]` The OR-side name: capacitated centred
  clustering (CCCP); ours is CCCP with equality capacities and squared-Euclidean cost.
- **mulvey1984** — *EJOR* 18(3):339–348, 1984. DOI 10.1016/0377-2217(84)90155-3.
  `[foundation]` The originating capacitated-clustering paper.
- **caro2004** — Caro, Shirabe, Guignard, Weintraub, *JORS* 55(8):836–849, 2004.
  DOI 10.1057/palgrave.jors.2601729. `[foundation]` School redistricting: contiguity
  relaxed in favour of capacity feasibility — our exact trade, in public service.
- **male1978** — Male & Liebman, *J. Env. Eng. Div. ASCE* 104(1):1–14, 1978.
  DOI 10.1061/JEEGAV.0000720. `[foundation]` Origin of workload-balanced service
  districting; first district-then-route two-stage split (structurally our draw-then-match).
- **borgwardt2014** — Borgwardt, Brieden, Gritzmann, *Math. Intelligencer* 36(2):37–44,
  2014. DOI 10.1007/s00283-014-9448-2. `[foundation]` The machinery in production (Bavarian
  land consolidation) — precedent for explaining split units to stakeholders.
- **behroozi2020** — Behroozi & Carlsson, survey, ISOR 284, Springer, 2020, 57–74.
  DOI 10.1007/978-3-030-34312-5_4 (primary: Carlsson, *IJOC* 24(4):565–577, 2012,
  DOI 10.1287/ijoc.1110.0479). `[foundation]` The geometric-districting bridge; the
  continuous-measure analogue of our balance constraint.

---

## 4. Mechanism design and matching (guide §4, §7.4)

### 4A. Strategyproofness and MNW; facility location

- **schummer1996** — *Social Choice and Welfare* 14(1):47–56, 1996.
  DOI 10.1007/s003550050050. `[foundation]` `[contradicts-or-sharpens]` On linear-preference
  exchange domains every strategyproof + Pareto-optimal rule is dictatorial. Our u_i is
  linear in S_i — applies as stated. There is no strategyproof-and-efficient stage 2 to find.
- **amanatidis2017** — Amanatidis, Birmpas, Christodoulou, Markakis, EC 2017,
  arXiv:1705.10706. `[foundation]` Every truthful two-agent additive mechanism is
  selection-from-a-menu + exchange; max-product is not — structural proof of manipulability,
  and the shape any truthful replacement must take.
- **halpern2020** — WINE 2020 (see §1D). `[tool-we-lack]` **The escape hatch:** on binary
  additive valuations, deterministic MNW + lexicographic tie-breaking is *group
  strategyproof*, EF1, PO. If books enter as incumbency indicators, our existing rule
  becomes truthful unchanged.
- **barman2022** — Barman & Verma, AAAI 2022, DOI 10.1609/aaai.v36i5.20407. `[frontier]`
  Extends to matroid-rank valuations — check whether capped books min(S_i(z), cap) land
  inside.
- **bei2025incentive** — Bei, Tao, Wu, Yang, *Artificial Intelligence* 344:104335, 2025.
  DOI 10.1016/j.artint.2025.104335 (WINE 2023). `[frontier]` **MNW incentive ratio is
  exactly 2** (divisible): a misreport at most doubles the manipulator's utility — the
  governance number.
- **chen2012** — Chen, Deng, Zhang, Zhang, ICALP 2012, DOI 10.1007/978-3-642-31585-5_42.
  `[foundation]` Fisher-market incentive ratios < 2 (linear), tight and size-insensitive:
  111 reps are no safer than 5.
- **cole2013** — Cole, Gkatzelis, Goel, EC 2013, DOI 10.1145/2492002.2482582.
  `[tool-we-lack]` Partial Allocation mechanism: truthful without money, guarantees 1/e of
  the max-product value; no truthful mechanism exceeds 1/2. The honest price list for a
  truthful cardinal stage 2 — large next to our 4.5e-5-nat gap.
- **procaccia2013** — Procaccia & Tennenholtz, *ACM TEAC* 2013 (EC 2009),
  DOI 10.1145/2542174.2542175. `[foundation]` Approximate mechanism design without money —
  the frame in which strategic stage-1 questions are well-posed.
- **lu2010** — Lu, Sun, Wang, Zhu, EC 2010, DOI 10.1145/1807342.1807393. `[foundation]`
  Already at 2 facilities, deterministic SP approximation grows with n.
- **fotakis2014** — Fotakis & Tzamos, *ACM TEAC* 2(4), 2014, DOI 10.1145/2665005
  (ICALP 2013). `[frontier]` `[contradicts-or-sharpens]` **k ≥ 3 facilities: deterministic
  anonymous strategyproof mechanisms have unbounded approximation.** At k=13, a
  strategyproof center-based draw does not exist at any price — stage 1 must not read
  reports (it doesn't; make it an invariant).
- **pegden2017** — Pegden, Procaccia, Yu, arXiv:1710.08781. `[frontier]` I-cut-you-freeze:
  guarantees from strategic districting agents *without* truthful elicitation — the
  protocol-design alternative if the channel ever has contending factions.

### 4B. Matching with selection; Hungarian-on-logs as a rule

- **jain2024** — Jain & Vaish, "Maximizing Nash Social Welfare under Two-Sided
  Preferences", AAAI 2024, DOI 10.1609/AAAI.V38I9.28839. `[frontier]`
  `[contradicts-or-sharpens]` **The closest paper to stage 2.** Two-sided NSW matching is
  NP-hard even at firm capacity 2 with valuations in {0,1,2}. Our exactness = capacity-1
  separability; the tractability is fragile.
- **gokhale2025** — Gokhale, Sagar, Vaish, Viswanathan, Yadav, AAMAS 2025,
  arXiv:2411.14007. `[frontier]` Approximation algorithms for capacitated one-/two-sided
  NSW; the weighted two-sided variant is the natural home for rep seniority.
- **suksompong2023** — *Economics Letters* 222:110956, 2023. `[frontier]` MNW is the unique
  additive welfarist rule satisfying EF1 — but for endogenous bundles; transfer to
  fixed-bundle matching is an open gap. **yuen2023** — *Economics Letters* 224:111030,
  2023: removes additivity — if we want a welfarist stage-2 rule with an EF1-flavored
  guarantee, Σ log is the only candidate.
- **roth1986** — *Econometrica* 54(2):425–427, 1986. DOI 10.2307/1913160. `[foundation]`
  `[contradicts-or-sharpens]` Rural hospitals theorem: the matched set is invariant across
  *stable* matchings — a property of stability, not optimization. Which 98 reps are dropped
  is a pure artifact of the objective and reported books; no market invariance to hide
  behind when a rep contests non-retention.
- **hatfield2005** — Hatfield & Milgrom, *AER* 95(4):913–935, 2005.
  DOI 10.1257/0002828054825466 (+ Hatfield–Kojima 2008, Aygün–Sönmez 2013 corrections).
  `[foundation]` Matching with contracts — the framework for making the θ capture term a
  contract term; whether our θ-augmented choice is substitutable is open and checkable.
- **abebe2020** — Abebe, Cole, Gkatzelis, Hartline, SODA 2020, arXiv:1903.07797.
  `[tool-we-lack]` Truthful cardinal one-sided matching benchmarked against the Nash
  bargaining solution — the nearest existing object to "a truthful Hungarian-on-logs"
  (one-sided, square, randomized; ours is rectangular with a selection margin).
- **auricchio2023** — Auricchio & Zhang, arXiv:2307.12305. `[frontier]` Manipulability of
  max-vertex-weighted bipartite b-matching with private edge sets — exactly our mechanism
  class and our reps' private information; characterizes when the optimal mechanism happens
  to be truthful.
- *Absence:* no axiomatic characterization of max-product bipartite matching as a *matching
  rule*, and no treatment of the selection margin (who is retained) as the designed output
  of a cardinal-welfare mechanism. Provenance §8.

### 4C. Externalities (the θ term)

- **sasaki1996** — Sasaki & Toda, *JET* 70(1):93–108, 1996. DOI 10.1006/jeth.1996.0077.
  `[foundation]` `[contradicts-or-sharpens]` With externalities, stable matchings need not
  exist. **Nash-optimal matching under externalities retains no known incentive or
  stability property** — the direct answer to the guide's §4 question.
- **pycia2023** — Pycia & Yenmez, *Review of Economic Studies* 90(2):948–974, 2023.
  `[frontier]` `[tool-we-lack]` The modern repair: stability exists iff choice functions are
  substitutable *with* externalities. Checkable question: is our θ-augmented choice
  substitutable? Either answer is a result.
- **bodine-baron2011** — SAGT 2011, DOI 10.1007/978-3-642-24829-0_12. `[frontier]`
  Two-sided *exchange* stability: a weaker-but-nonempty notion our matching could be asked
  to satisfy; cardinal-utility externality precedent.
- **branzei2013** — Brânzei, Procaccia, Zhang, IJCAI 2013. `[foundation]` Fairness notions
  under positive externalities (our θ ≥ 0 case).
- **velez2016** — Velez, *Theoretical Economics* 11(1):381–410, 2016. DOI 10.3982/te1651.
  `[foundation]` `[tool-we-lack]` **Swap-based envy** is the correct envy notion under
  externalities (swapping bundles ≠ receiving the other's bundle when θ > 0) — our note's
  n-agent EF1 should be restated in this form or weakened.
- **aziz2022ext** — Aziz, Suksompong, Sun, Walsh, arXiv:2110.09066 (AAAI 2023 per authors).
  `[frontier]` EF1/EFX extended to additive externalities — algebraically the shape of our
  c2·(T_z − S_i) term; tells us which guarantees survive θ.
- **ghodsi2018** — Ghodsi, Saleh, Seddighin, arXiv:1805.06191. `[frontier]` Network
  externalities with an **α-self-reliance** parameter — at our ~90% own-term dominance
  (λ=0.3, ~5% saturation) their EMMS guarantees are near-tight. Compute α on the real
  instance.

### 4D. Disruption, transition, compensation

- **halpern2019subsidy** — Halpern & Shah, "Fair Division with Subsidy", SAGT 2019,
  DOI 10.1007/978-3-030-30473-7_25. `[tool-we-lack]` `[contradicts-or-sharpens]`
  Envy-freeable by transfers ⇔ utilitarian-optimal over bundle reassignments. **If our Nash
  matching ≠ the utilitarian matching, no compensation package can make it envy-free.**
  Two-line test on the certified draw (headline 10).
- **kleinelmalem2026** — Klein Elmalem, Gonen, Segal-Halevi, arXiv:2504.16852 (rev.
  2026-02). `[frontier]` `[tool-we-lack]` Urban-renewal reallocation where old endowments
  legitimately shape new entitlements, with payment vectors minimizing maximum envy AND an
  **indirect elicitation method with truthful-revelation conditions** — our transition
  problem with apartments for territories; the most concrete answer to "how should books
  enter the model given misreporting incentives."
- **waiser2021** — Waiser, *J. Marketing Research* 58(1):182–201, 2020/21.
  DOI 10.1177/0022243720969174. `[frontier]` `[tool-we-lack]` Constrained delegation
  extracts managers' private territory knowledge — organizational-design route to truthful
  reports, possibly far cheaper than cole2013's 1/e sacrifice.
- *Absence:* no mechanism-design treatment of compensation for territory/district
  reassignment anywhere. Follow-ups the sweep could not close: the Gonik-style
  truth-inducing quota literature (search budget exhausted before verification), and
  whether budget-balanced reallocation mechanisms (Blumrosen–Dobzinski line) ever touched
  districting. Provenance §8.

---

## 5. Optimization machinery (guide §5)

### 5A. Exact MNW: conic and OA

- ★**caragiannis2019 §8** `[FLAG]` — Spliddit's MILP lower-bounds log by a piecewise-linear
  function **exact at integral utility values** — our tangent loop under another name, with
  cuts placed a priori rather than separated. Cite as precedent for `scip_tree`.
- **charkhgard2022** — *ANZIAM J.* 64(2):119–134, 2022. DOI 10.1017/S1446181122000074.
  `[tool-we-lack]` "Do Not Sum, Just Multiply": Nash-product objectives as conic programs
  for general OR problems — the OR-side home of our formulation.
- **saghand2022** — Saghand & Charkhgard, *ITOR* 29(3):1659–1687, 2022.
  DOI 10.1111/itor.12964. `[tool-we-lack]` **MIL-MMP → MISOCP** (geometric-mean cones),
  solved directly by Gurobi/CPLEX. g_i is linear in the binaries, so this replaces the whole
  tangent-cut loop — and traps 14/15 machinery — with one MISOCP call. Highest-value solver
  change identified in the sweep.
- **mosek_cookbook** — MOSEK Modeling Cookbook §5.2.2 (v3.4.0). `[tool-we-lack]`
  `t ≤ log x ⟺ (x,1,t) ∈ K_exp`: max Σ log g_i is 13 exponential cones; MOSEK ≥9 solves
  MIECP natively. SCIP has no exp cone — precisely why our engine grew a tangent loop.
- **ye2021** — Ye & Xie, arXiv:2106.09123. `[tool-we-lack]` Principled SOC/polyhedral outer
  approximation of the exponential cone (the theory our hand-rolled cuts lack).
- **lubin2018** — Lubin, Yamangil, Bent, Vielma, *Math. Programming* 172:139–168, 2018.
  DOI 10.1007/s10107-017-1191-y. `[contradicts-or-sharpens]` Extended-formulation OA:
  separable objectives should be cut per-term (t_i ≤ log g_i in (g_i, t_i) space), not on
  the aggregate — check whether `scip_tree` does this.
- **coey2020** — Coey, Lubin, Vielma, *MPC* 12(2):249–293, 2020,
  DOI 10.1007/s12532-020-00178-3. `[frontier]` `[tool-we-lack]` OA with conic certificates
  (Pajarito) — the modern replacement for `cert_exact.py`'s hand-rolled AM–GM OA.
- ★**eisenberg1959** `[re-read]` — one convex solve of the EG program over the fractional
  assignment polytope = a dual bound sharper than `allocate_districts` (sees per-zip
  utilities, not just component masses). Free experiment.
- **fravel2026** — Fravel, Hildebrand, Goedert, Travis, Pierson, *Math. Methods of OR*
  103:21–86, 2026. DOI 10.1007/s00186-026-00919-5; arXiv:2305.17298. `[frontier]` MILP dual
  bounds for nonconvex districting objectives beside heuristics — the closest published
  precedent for our ceiling + cert_draw design; read before claiming novelty, and for how
  they keep the relaxation non-vacuous (ours is provably vacuous).
- *Absence:* no paper solves MNW via mixed-integer exponential-cone programming — MISOCP is
  the proven route; MNW-via-exp-cone is unoccupied. Provenance §8.

### 5B–C. Balance bounds; transportation integrality

- **graham1969** — *SIAM J. Applied Math* 17(2):416–429, 1969. DOI 10.1137/0117039.
  `[foundation]` LPT ≤ 4/3 − 1/(3m): at k=13, ≤ 1.3077 — the quotable a-priori guarantee
  for the balance-floor incumbent.
- **michiels2007** — *J. Comb. Optim.* 13(1):19–32, 2007. DOI 10.1007/s10878-006-9010-z.
  `[contradicts-or-sharpens]` Karmarkar–Karp's tight k-way ratios: at k=13 KK's worst case
  is *worse* than LPT's (though better on average) — keep quoting Graham; run KK for the
  incumbent.
- **korf1998** (*AIJ* 106:181–203, DOI 10.1016/S0004-3702(98)00086-1) and **schreiber2018**
  (*JACM* 65(4), DOI 10.1145/3184400). `[tool-we-lack]` Complete anytime multiway number
  partitioning (CKK/RNP) — will likely close the 13-way floor *exactly* where the
  vacuous-LP MILP cannot, upgrading "constructive incumbent" to "proved floor."
- **dantzig1963** — *Linear Programming and Extensions*, Princeton UP, 1963. `[foundation]`
  **ahuja1993** — Ahuja, Magnanti, Orlin, *Network Flows*, Prentice Hall, 1993.
  `[foundation]` The canonical statements of the m+n−1 spanning-tree basis property — stop
  proving the split lemma. **peyre2019** — *Computational Optimal Transport*, FnT ML
  11(5–6), 2019, DOI 10.1561/2200000073 — the OT phrasing (Prop. 3.4).
  **shmoystardos1993** — *Math. Programming* 62:461–474, DOI 10.1007/BF01585178
  `[tool-we-lack]` — the canonical rounding of few-fractional-variable assignment LPs with
  bounded local violation.
- *Note:* all these guarantees are makespan-side; no tight LPT/KK ratio exists against a
  Nash objective — the ratio transfers as a bound on balance, not on nats. Be explicit.

### 5D. Symmetry

- **margot2002/2003** — *Math. Programming* 94:71–90 and 98:3–21.
  DOI 10.1007/s10107-002-0358-2, 10.1007/s10107-003-0394-6. `[foundation]` Isomorphism
  pruning.
- **ostrowski2011** — *Math. Programming* 126:147–178, DOI 10.1007/s10107-009-0273-x.
  `[foundation]` Orbital branching — the standard first thing to try.
- **kaibel2008** — Kaibel & Pfetsch, *Math. Programming* 114:1–36,
  DOI 10.1007/s10107-006-0081-5. `[foundation]` `[FLAG]` The **partitioning orbitope** —
  the polyhedrally correct version of our "sort the district masses" trick (+ orbitopal
  fixing: Bendotti et al., *Math. Prog.* 186:337–372, 2019).
- **pfetsch2019** — Pfetsch & Rehn, *MPC* 11:37–93, DOI 10.1007/s12532-018-0140-y.
  `[frontier]` Controlled comparison in SCIP: static ordering constraints alone are NOT
  enough on genuinely symmetric instances; orbital methods matter. Cheapest step: turn on
  SCIP's built-in symmetry handling and measure.

### 5E. Column generation / branch-and-price — the credible exact stage 1

- **mehrotra1998** (see §3B) — district-as-column set partitioning: **no k! label group
  exists in the formulation at all** (structurally better than orbitopes or sorting), and
  center choice is freed from the Hess restriction.
- **johnson1993** — Johnson, Mehrotra, Nemhauser, "Min-cut clustering", *Math. Programming*
  62:133–151, DOI 10.1007/BF01585164. `[foundation]` The honest preview: the pricer is
  itself an NP-hard MIP.
- **ceselli2005** — Ceselli & Righini, *Networks* 45(3):125–142, DOI 10.1002/net.20059.
  `[frontier]` Exact B&P for capacitated p-median; struggles at p ≥ n/4 — our p ≈ n/95 is
  the favourable regime (few, large columns).
- **aloise2012** — Aloise, Hansen, Liberti, *Math. Programming* 131:195–220,
  DOI 10.1007/s10107-010-0349-7. `[frontier]` `[tool-we-lack]` **Exact MSSC at 2,300+
  entities — ~2× our n.** The proven route to certifying a center-based stage 1 at our
  scale.
- **cordero2025** — *Networks* 85:245–260, 2025, DOI 10.1002/net.22257. `[tool-we-lack]`
  CG with spectral-clustering-warm-started pricing for connected partitioning.
- **garfinkel1970** — *Management Science* 16(8):B-495, DOI 10.1287/mnsc.16.8.b495.
  `[foundation]` The original enumerate-then-set-partition; historical bookend.
- *Absence + research risk:* no exact B&P for districting with a Nash/log objective — the
  master becomes conic, so pricing duals need derivation. Provenance §8.

### 5F. k-means exactness — closing the un-certified Lloyd gap

- **peng2007** — Peng & Wei, *SIAM J. Optimization* 18(1):186–205, DOI 10.1137/050641983.
  `[foundation]` The Peng–Wei SDP relaxation — the lower bound everything below builds on.
- **iguchi2017** — Iguchi, Mixon, Peterson, Villar, *Math. Programming* 165:605–642,
  DOI 10.1007/s10107-016-1097-0. `[tool-we-lack]` **Probably-certifiably-correct k-means:
  a quasilinear post-hoc dual certificate test for a proposed clustering** — exactly the
  missing stage-1 certificate, with reference code (solevillar/clustering_certificate).
- **mixon2017** — arXiv:1710.00956. `[tool-we-lack]` Monte-Carlo approximation certificates
  (subsampled Peng–Wei) — the pragmatic fallback; fits our two-tier philosophy.
- **awasthi2015** — ITCS 2015, DOI 10.1145/2688073.2688116. `[foundation]` Relaxation
  tightness needs center separation — our well-separated regional blobs are the favourable
  regime; interior near-ties are where tightness fails.
- **piccialli2022** — Piccialli, Sudoso, Wiegele, *IJOC* 34(4):2144–2162,
  DOI 10.1287/ijoc.2022.1166. `[frontier]` `[tool-we-lack]` SOS-SDP: **exact MSSC to 4,000
  points**, open source — an off-the-shelf exact solver past our 1,229.
- **croella2026** — Croella, Piccialli, Sudoso, *EJOR* 2026, DOI 10.1016/j.ejor.2026.07.045.
  `[frontier]` `[tool-we-lack]` Divide-and-conquer MSSC bounds (<3% gaps at scale),
  explicitly for assessing heuristic clusterings — our problem statement verbatim; its
  decomposition maps onto our 547 components.
- **kanungo2004** (DOI 10.1016/j.comgeo.2004.03.003) / **arthur2007** (k-means++, SODA
  2007). `[foundation]` The a-priori bounds (9+ε; Θ(log k)) are loose at k=13 — the
  argument for an instance-specific certificate instead.

---

## 6. Graph theory (guide §6)

### 6A. Győri–Lovász and successors

- **gyori1976** (Colloq. Math. Soc. J. Bolyai 18, 485–494) / **lovasz1977** (*Acta Math.
  Acad. Sci. Hung.* 30:241–251, DOI 10.1007/BF01896190). `[foundation]` The theorem.
  **hoyer2016** (arXiv:1605.01474) — modern exposition; k=4 polynomial line.
- **chandran2018** — ICALP 2018, DOI 10.4230/LIPIcs.ICALP.2018.32. `[foundation]` The
  weighted (vertex-weighted) Győri–Lovász, first constructive proof.
- **borndorfer2021** — APPROX/RANDOM 2021, DOI 10.4230/LIPIcs.APPROX/RANDOM.2021.27.
  `[frontier]` **The clean statement of "when is the balance ceiling achievable with
  contiguity":** k-connected ⇒ connected k-partition within ±w_max of any targets — plus a
  3-approximation. Our graph is not even 1-connected: the ceiling is *not* achievable with
  contiguity, cleanly, by hypothesis failure rather than empirical defeat.
- **casel2023** (WG 2023, DOI 10.1007/978-3-031-43380-1_11), **niklanovits2025** (ESA 2025,
  DOI 10.4230/LIPIcs.ESA.2025.10). `[frontier]` The 2023–25 algorithmic frontier
  (graph-class restrictions; connected dominating sets). No exact poly algorithm for any
  k ≥ 5 on general graphs — explicitly open.
- **soltan2020** — SODA 2017 / *ACM Trans. Algorithms* 16(2), DOI 10.1145/3381419.
  `[tool-we-lack]` **Doubly balanced** connected partitioning (two simultaneous balance
  criteria) constructive at k=2 — the closest analogue of our opportunity+book tension;
  suggests the stage split may be provably collapsible on small subproblems.

### 6B. Balanced connected partition

- **chlebikova1996** (*IPL* 60:225–230, DOI 10.1016/S0020-0190(96)00175-5) `[foundation]`;
  **chen2019** (arXiv:1910.02470, COCOA) `[frontier]`; **moura2023** (*J. Comb. Optim.*
  45(5), DOI 10.1007/s10878-023-01058-x — (k/2+ε)-approx, ETH bounds) `[frontier]`;
  **moura2026** (*Math. Programming*, DOI 10.1007/s10107-025-02321-1 — the connected
  (sub)partition polytope; best cut arsenal if contiguity ever returns) `[frontier]`.
- *Absence:* no 2023–26 improvement to a,b-separator *separation itself* beyond
  ★validi2021/★validibuchanan2022 — the field moved to inexact families, new objectives,
  polytopes, and hardness maps. No better exact separator tool is waiting. Provenance §8.

### 6C. Power diagrams and semi-discrete optimal transport — stage 1's true home

- **aurenhammer1987** — *SIAM J. Computing* 16(1):78–96, DOI 10.1137/0216006.
  `[foundation]` Power diagrams: cells always convex, lifted convex hull.
- **aha1998 (aurenhammer1998)** — Aurenhammer, Hoffmann, Aronov, *Algorithmica*
  20(1):61–76, DOI 10.1007/PL00009187. `[foundation]` `[FLAG]` **Our construction:**
  constrained least-squares assignment ≡ power-diagram partition; prescribed sizes
  achievable for any sites; = a transportation problem; the LP duals are the weights.
- **brieden2012** — *SIAM J. Discrete Math* 26(2):415–434, DOI 10.1137/110832707.
  `[foundation]` The polyhedral theory, in the **mass-weighted** (not cardinality) case —
  our case.
- **bbg2013/bbg2017** — Borgwardt, Brieden, Gritzmann, arXiv:1308.4004 and *EJOR*
  263(2):349–355, DOI 10.1016/j.ejor.2017.04.054. `[foundation]` `[FLAG]` **Weight-balanced
  k-means** — our algorithm, named, with iteration bound n^O(dk). The citation for
  `td/solvers/centers.py`.
- **bgk2017 (brieden2017)** — Brieden, Gritzmann, Klemm, *EJOR* 263(1):18–34,
  DOI 10.1016/j.ejor.2017.04.018. `[foundation]` `[FLAG]` The unified constrained-
  clustering-via-diagrams framework applied to district design — **contains our Lemma 4
  (≤ k−1 splits, mass-weighted) and Theorem 5 (rounding bound)**; closest published
  analogue of our whole stage 1.
- **cohenaddad2018** — SIGSPATIAL 2018, DOI 10.1145/3274895.3274979. `[frontier]` Our loop
  on US census data; convex cells, avg < 6 sides, balance to ±1.
- **fryer2011** — Fryer & Holden, *J. Law & Economics* 54(3):493–535, DOI 10.1086/661511.
  `[contradicts-or-sharpens]` Axiomatized compactness; **maximally compact plans ARE power
  diagrams** — reframes compactness-vs-Nash as choosing a point on a characterized family.
- **balzer2009** (ACM TOG 28(3), DOI 10.1145/1531326.1531392 — origin of
  "capacity-constrained") and **degoes2012** (Blue noise through optimal transport, ACM TOG
  31(6), DOI 10.1145/2366145.2366190 — capacity constraint = semi-discrete OT; centers and
  weights optimized *jointly* in power-diagram space). `[tool-we-lack]`
- **xin2016** — ACM TOG 35(6), DOI 10.1145/2980179.2982428. `[tool-we-lack]`
  Super-linearly convergent capacity-weight solver — replaces the LP if it ever bottlenecks.
- **bourne2015** — *SIAM J. Numer. Anal.* 53(6):2545–2569, DOI 10.1137/141000993.
  `[foundation]` `[FLAG]` Critical points = centroidal power diagrams; generalized Lloyd is
  energy-decreasing with a convergence theorem — adopt by citation.
- **merigot2011** (CGF 30(5), DOI 10.1111/j.1467-8659.2011.02032.x), **levy2015**
  (ESAIM:M2AN 49(6), DOI 10.1051/m2an/2015055), **kmt2019** (Kitagawa–Mérigot–Thibert,
  *JEMS* 21(9):2603–2651, DOI 10.4171/jems/889 — damped Newton, proved global linear
  convergence), **merigot2021** (arXiv:2003.00855 — THE survey). `[foundation/tool-we-lack]`
  The semi-discrete-OT solver stack: 13-dimensional smooth convex weight problem in place
  of the 1,229×13 LP, if scale ever bites.
- **luo2025** — Luo & Mixon, "BalLOT", arXiv:2512.05926. `[frontier]` Balanced k-means as
  OT with integrality guarantees for the couplings on typical data.
- **alpers2015** — *Phil. Mag.* 95(9):1016–1028, DOI 10.1080/14786435.2015.1015469.
  `[foundation]` "Generalized balanced power diagrams"; anisotropic cells — the route to
  travel-time metrics.
- **fiedler2022** — arXiv:2203.10864. `[contradicts-or-sharpens]` Importance-sampling
  coresets provably do NOT apply to weight-constrained clustering — kills "subsample the
  zips."
- *Absence:* **no application of capacity-constrained power diagrams / semi-discrete OT to
  commercial or sales territory design** — all applications are political, graphics, or
  materials. A genuine open niche. Provenance §8.

---

## 7. The niche, and the shortlist (guide deliverable)

**The five papers closest to "maximum Nash welfare balanced districting without contiguity,
with post-hoc certificates":**

1. **brieden2017 / bgk2017** (EJOR) — balanced clustering via diagrams applied to district
   design: our stage-1 machinery, including the split lemma, minus the Nash framing.
2. **cohenaddad2018** (SIGSPATIAL) — balanced centroidal power diagrams for districting:
   our exact algorithm on our exact problem class, no certificates, no welfare objective.
3. **fravel2026** (Math. Methods of OR) — dual bounds for nonconvex districting objectives
   reported beside heuristics: our certificate culture, different objective.
4. **jain2024** (AAAI) — two-sided Nash social welfare matching: our stage 2, as a
   computational object.
5. **mancho2025** (SAGT) — MNW under equal-size-bundle constraints: the nearest theory
   result to "Nash + balance," cardinality version.

**Is the niche occupied? No.** Each neighbour holds one or two of the four components
(balance-by-diagram, no-contiguity, Nash objective, post-hoc certificates); none holds
three. Specifically verified absences: no Nash-welfare formulation of districting; no
price-of-connectivity for Nash; no sales-territory application of the power-diagram
machinery; no joint alignment + retention-selection model. The combination — Nash-as-balance
districting on a disconnected footprint, certified post hoc, with a retention-selecting
matching stage — appears to be ours. The flip side: nobody has stress-tested the bridge for
us, and the components individually are all known (see §0.1–4), so the note's contribution
claims must be re-scoped to the *combination* and the two open theorems (§9, G).

---

## 8. Absence-claim ledger (where we looked)

Load-bearing negatives, with provenance as reported by the verifying agents:

1. **Price of connectivity for Nash welfare — none exists.** Full-text scan of
   arXiv:2405.03467 (ar5iv): "Nash" absent. Eleven search strings over EC, AAAI, IJCAI,
   AAMAS, SAGT, WINE, FSTTCS, SIDMA, GEB, AIJ, DAM, MOR; full-text/abstract checks of
   arXiv:2205.10836 (utilitarian/egalitarian only), 2508.06343, 2402.05884, 2512.22475,
   2507.20899; surveys: Suksompong "Constraints in Fair Division" (SIGecom Exch. 19(2)),
   Amanatidis et al. 2208.08782 (both PDFs resisted text extraction — the one caveat), Hsu
   thesis 2510.12158. A snippet suggests MNW-under-connectivity is listed somewhere as an
   open direction (unpinned; consistent with absence).
2. **No Nash-welfare formulation of districting.** Searches combining Nash welfare /
   geometric mean / product-of-districts with districting/redistricting across OpenAlex and
   web search; the kalcsics2005/2019 survey neighbourhood; participatory-budgeting Nash line.
   Every Nash-product paper indexes the product by agents with preferences. kaneko1979 is
   the licence for the move; no precedent executes it.
3. **No joint territory-alignment + rep-retention model.** Crossref bibliographic queries,
   OpenAlex title searches, web searches (strings recorded in the §3 agent report); full ToC
   of *Optimal Districting and Territory Design* (ISOR 284) enumerated; kalcsics2019 and
   behroozi2020 checked for coverage. Caveat: moyagarcia2020's chapter text unread
   (abstract withheld) — one PDF from revision.
4. **No sales/commercial application of capacity-constrained power diagrams / semi-discrete
   OT.** Searches across OT/Laguerre/power-diagram × sales-territory terms; both surveys
   whose scope covers sales territories checked.
5. **No SAT/CP exact districting.** Searches over CP-SAT/SAT/CP × districting 2024–26;
   CP 2026 proceedings listing browsed. Nearest: a school-boundary framework
   (arXiv:2509.17130) with no optimality claim.
6. **No axiomatic characterization of max-product bipartite matching; no analysis of the
   selection margin as mechanism output; no incentive ratio for matching-with-selection.**
   Five search strings over EC, AAMAS, AAAI, IJCAI, SODA, WINE, SAGT, Econ. Letters, TEAC,
   AIJ; the hospital-residents corpus. Nearest prior: auricchio2023 (equilibria, not
   incentive ratios).
7. **No 2023–26 improvement to a,b-separator separation.** 2024–26 searches; Buchanan's
   full publication list through 2026-08; optimization-online listings; moura2026's
   contribution statement.
8. **No mechanism-design treatment of compensation for territory reassignment.** Searches
   recorded in the §4 agent report; two follow-ups left open there (Gonik-style quota
   schemes unverified — search budget exhausted; Blumrosen-line reallocation × districting).
9. **No exact branch-and-price for districting with a Nash/log master; no MNW via
   mixed-integer exponential cones.** CG/districting and NSW/conic searches; MOSEK docs
   fetched. MISOCP (saghand2022) is the proven adjacent route.
10. **No exact poly Győri–Lovász for k ≥ 5** — stated as open in borndorfer2021, reaffirmed
    niklanovits2025 (moot for us: 547 components fail every hypothesis).

Unverified leads flagged by agents (do not cite without fetching): BKV-greedy's AAMAS 2018
venue; the "sharp angles in redistricting Pareto frontiers" claim attributed to
mccartan2023shortbursts; malinen2014's internal wording; bennett2000's own integrality
wording (image-only PDF).

---

## 9. Proposed reframings, changes, and callouts (synthesized, prioritized)

### A. Corrections to committed artifacts (do first — cheap, and two are correctness issues)

- **A1. Redraw `district_regions.png` as a power diagram** and emit the 13 power weights
  (= transportation-LP duals of the mass-balance rows) from `cert_draw.py`. Fixes a
  correctness bug in a primary artifact AND adds an exact, solver-independent,
  human-checkable optimality certificate for the assignment at fixed centers. The
  pinned-centers MILP demotes to a cross-check. (aha1998, bbg2017, brieden2012;
  flagged independently by three agents.)
- **A2. Update the stale scale claim** in `CLAUDE.md` / `docs/CHANNEL.md`: exact districting
  now certifies all US instances at county level (shahmizad2026) and runs at 175k vertices
  (jolly2026); our difficulty is the objective and the 547 components, not 1,229 zips.
- **A3. Re-scope the "≤ k−1 splits" statement**: it is "there exists a basic optimum with
  ≤ k−1 splits" (brieden2017 Lemma 4), not "every optimum"; verify `cert_draw.py` checks
  the former. The Buchanan group's Election Law J. paper is a cautionary tale about split
  folk-claims.

### B. Rename our constructions and retire proofs (a citation pass over `channel_note`)

- Stage 1 = mass-weighted **Hess model** / **weight-balanced (constrained) k-means** /
  **capacitated Lloyd for centroidal power diagrams** / **semi-discrete OT**: cite hess1965,
  bennett2000, bbg2013+bbg2017, bourne2015 (convergence theorem — adopt it), cohenaddad2018
  (districting precedent), merigot2021 (one-paragraph OT statement).
- Proposition "MNW = equal split on a common measure" → Schur-concavity/majorization
  (marshall2011) + Pigou–Dalton (moulin2003) + proportional fairness (kelly1997/98).
- Split lemma → brieden2017 Lemma 4 + dantzig1963/ahuja1993; quote Theorem 5's
  ε ≥ max_z M_z/κ_j as the business-facing spread bound.
- Scale invariance → inherited from eisenberg1961's homogeneity.
- Lead the note with kaneko1979 (Nash *social welfare function*), not nash1950; state which
  bargaining axioms are vacuous under a common measure (roth1979, trockel2008).
- Position against **commercial territory design** (kalcsics2019, kalcsics2005), not only
  political districting: their norm is balance-as-±τ-constraint; ours is
  balance-as-concave-maximizer (trap 2's justification) — that contrast is the contribution.
- Frame the contiguity pivot as (α,β)-compactness / distance-based inexact contiguity
  (madathil2023, jolly2026), with borndorfer2021 as the theorem for why the ceiling is
  unreachable with contiguity (needs k-connectivity; we have 547 components).

### C. Cheap decisive experiments (each ≤ a night; several settle open decisions)

- **C1. Quadratic-objective test** (brandl2026): re-run the k=13 draw maximizing −Σ M_j²
  and diff the partition. Near-identical ⇒ validates the degeneracy AND licenses dropping
  the OA machinery from stage 1 (log stays in stage 2 + certificates).
- **C2. Envy-freeability test** (halpern2019subsidy): Hungarian on g vs on log g over the
  certified districts. Same permutation ⇒ a transfer scheme with bounded subsidy exists;
  different ⇒ no compensation can make our matching envy-free — state it as a cost of Nash,
  next to the compactness decision.
- **C3. EG fractional dual bound** (eisenberg1959): one convex solve over the fractional
  assignment polytope — a ceiling that sees per-zip utilities; decomposes our 4.5e-5-nat
  residual into geometry vs integrality.
- **C4. Compactness-measure robustness** (barnes2021): recompute the 8.53% under a second
  measure (moment-of-inertia / Polsby–Popper); if the ordering flips, §7.1 partly dissolves.
- **C5. Binarized-books test** (halpern2020): re-run stage 2 with 1[S_i(z)>0]; if the
  selected 13 barely move, binarize and gain group strategyproofness for free.
- **C6. α-self-reliance** (ghodsi2018): compute on the real instance (expected ~0.9); their
  EMMS guarantees are then near-tight for us.
- **C7. Stage-1 certificate via k-means machinery** (iguchi2017 → piccialli2022 →
  croella2026): run the quasilinear dual-certificate test on the existing draw first;
  escalate to SOS-SDP (exact to 4,000 points) only if it fails. Closes the last un-certified
  stage-1 gap without designing anything.

### D. The compactness-vs-Nash lexicographic decision (§7.1)

Recommended resolution path, in order:
1. **Draw the frontier, don't pick a rule** (mccartan2023shortbursts; salazar2012 is the
   field norm): sweep the balance band, record (nats, compactness) — stage 2 is
   milliseconds. A knee near the adopted draw settles it; a smooth front makes it a business
   preference to present with a picture.
2. **fryer2011 reframe**: the compactness-optimal plan under axioms IS a power diagram, so
   once A1 lands, the question becomes "which point on a characterized family," and
   lexicographic MNW is a tie-break within it, not an override.
3. **Watch ezazipour2025** ("Finding Pareto-optimal districting plans," in revision at
   M&SOM) before finalizing — the in-press paper is on exactly this.
4. Run C4 first: if 8.53% is measure-fragile, the decision shrinks.

### E. Close two open decisions outright

- **Empty bundles / lexicographic MNW**: adopt ★caragiannis2019's lexicographic definition
  verbatim (headline 6). One paragraph + one test.
- **Untapped/vacant zips**: frame as *incomplete* fair division (gahlawat2026,
  ajaykrishnan2025) — allocating only p of the units is a studied object, and the
  ε-relaxation result independently justifies the two-tier band on principled grounds.

### F. Solver roadmap (ordered by value/risk)

1. **MISOCP replacement of the tangent loop** (saghand2022/charkhgard2022): Π g_i with
   linear g_i is an MIL-MMP → geometric-mean-cone MISOCP, solved natively by Gurobi/CPLEX;
   MOSEK exp-cones (13 cones) as the alternative. Deletes the separation loop, the trap-14
   dual-reduction workarounds, and the trap-15 retry ladder; the conic duality gap becomes
   the certificate. Do before further engine work.
2. **Extended-formulation OA check** (lubin2018): if the tangent loop stays, cut per-term
   (t_i ≤ log g_i), not the aggregate — verify what `scip_tree` does.
3. **Balance floor via complete Karmarkar–Karp** (schreiber2018): likely closes the 13-way
   floor exactly; keep quoting Graham's 4/3 − 1/39 as the a-priori ratio (michiels2007
   shows KK's worst case is worse at k=13).
4. **SCIP symmetry**: enable built-in symmetry handling and measure (pfetsch2019) before
   hand-rolling orbitopes; mass-sorting alone is probably insufficient, though it is
   top-venue standard practice (shahmizad2025).
5. **Set-partitioning branch-and-price** (mehrotra1998 → johnson1993 → aloise2012): the
   credible exact stage 1 with free centers and structurally zero label symmetry; our
   p ≈ n/95 is the favourable regime. Research risk: the Nash master is conic — pricing
   duals need derivation. Schedule after 1–4.
6. **Benders feedback** (shahmizad2026): a cut from stage 2 back to stage 1 is the
   principled `score_draws`; also upgrade the portfolio to Fairmandering's master-selection
   IP for a pool-restricted bound.
7. **Certificate endgame**: MIPLIB-style three-way status (certified/bounded/open) in
   `docs/RESULTS.md` (gleixner2021), performance profiles (beiranvand2017), VIPR as the
   eventual machine-checkable target (cheung2017; szeider2026 removes the
   no-exact-rational-stack objection; eifler2023 for exact repair of float incumbents).

### G. Incentives and governance (before reps see the model)

- Make **"books enter at stage 2 only"** an explicit design invariant in `docs/MODEL.md`
  (fotakis2014 makes any report-reading stage 1 unfixable at k=13). Our current design is
  right by accident; write it down.
- **Separate retention from reported books**: compute selection from audited system-of-record
  revenue; use reports only within-retained — the 98/111 losing majority currently has
  maximal inflation incentive, and roth1986 gives no invariance cover.
- Report **incentive ratio 2** (bei2025incentive, chen2012) as the governance number; the
  rectangular-with-selection version is an open theorem worth proving (nearest prior:
  auricchio2023).
- Restate the note's n-agent EF1 in **swap-based** form (velez2016) — plain EF1 is the wrong
  object once θ > 0.
- For transition packages: kleinelmalem2026 is the template (indirect elicitation with
  truthfulness conditions); halpern2019subsidy bounds what transfers can and cannot fix
  (test C2); waiser2021 for the organizational route.

### H. Contiguity: leave it, with one caveat

Do not attempt to restore adjacency contiguity (borndorfer2021's hypotheses fail; no better
separator machinery exists post-2022). One experiment could still change the picture:
★validi2021's own headline is that contiguity does not make districting harder — and our 547
components live on the **sold-zip** graph. On the full ZCTA adjacency graph (vacant and
untapped zips are already kept in our model as glue), each regional component is plausibly
connected, and contiguous territories might be reachable after all. `data/README.md` has the
rebuild recipe. Low priority; would remove the main modelling concession if it worked.

### I. Publishable openings (ranked)

1. **Price of connectivity for Nash welfare** — verified unclaimed; generalize to the
   (α,β)-compactness axis (connectivity = (1,m−1)); segalhalevi2018's proportionality
   failure is a ready lower-bound construction. Even paths/stars would be publishable.
2. **Nash-welfare balanced districting** as a bridge (the note itself) — re-scoped to the
   combination + the equivalences, per §7.
3. **Capacity-constrained power diagrams for sales-territory design** — application niche
   verified empty.
4. **Joint alignment + retention-selection** ("Nash-optimal territory design and salesforce
   selection"), with incumbent-preservation as a theorem (welfare decomposition) where the
   field pays a modelling cost (bender2016) — verify moyagarcia2020's PDF first.
5. **Incentive ratio of max-product matching with a selection margin** — open, concrete,
   and the governance question the business will actually ask.
