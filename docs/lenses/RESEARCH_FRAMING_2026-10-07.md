# Research framing: td's defining features and their analogues in the optimisation literature

Revision 2 (2026-10-08), after the owner's annotations on revision 1. Draft for annotation; no
search has run yet. Builds on `docs/REFERENCES.md` and the checkpoint
`docs/lenses/REVIEW_2026-10-07.md`. Owner questions from revision 1 are answered inline under
"Owner asked".

## 1. The defining features, stripped of geography

1. **A planar graph partition into connected parts.** ZCTAs with rook adjacency, K parts, every
   part connected. The connected k-partition family that districting lives in.

2. **A fixed capacity interval per part, and K as a range.** Each part's mass must lie in
   [L, U] in dollars, independent of K. Bin packing language: bins with a fixed size window, the
   number of bins free within a range.

   *Owner asked: why does classic districting use balance around total/K?* Because its K is
   given from outside (a state's seat count comes from apportionment, a council's size from its
   charter) and the legal rule is one person, one vote: deviation is measured from the ideal
   population, total/K. The target is derived from K. Ours is the reverse: the target per
   district is the fixed quantity (a $ figure the business set) and K is whatever count fits.
   That is why districting's balance machinery matches us less well than packing's, and why
   lane A's old τ-band results no longer hold under D3.

   *Owner (rev 2): keep exploring the districting analogue, and challenge whether fixing the
   target and letting K float beats the districting approach of fixing K.* Two things to test,
   not assume. First, the two forms are interchangeable at a cost: fixing K and a band around
   total/K is a special case of our form with L = U·(1−δ)/(1+δ) scaled to that K, so a grid
   over K with a τ-band (what #125 did) and a fixed [L, U] with free K search the same space in
   different orders; which is faster, and which gives better bounds, is an empirical question
   for the toy. Second, fixing K unlocks the mature districting toolchain. GerryChain (MGGG's
   ReCom implementation), its Julia port, Validi–Buchanan's exact codes, Gurnee–Shmoys's
   column-based codes and the optimal-districting repos are all built for fixed K with
   population balance around total/K, contiguity on a dual graph, and county-split counting.
   Running them on our graph with $ as population is cheap to try and is a research item below
   ("Open-source districting tools").

3. **A unit hierarchy with a cost for breaking a unit.** The objective counts broken states,
   then fragments. In packing terms states are items, districts are bins, and an item may be
   fragmented at a cost: bin packing with item fragmentation (kb: `casazza2016`). In districting
   terms, county splits.

   *Owner asked: consider the other levels of granularity.* The hierarchy is not two levels.
   Between state and ZCTA sit Census divisions, CSAs, CBSAs (MSA and μSA), counties and tracts,
   and the `geography` tab is sizing them. For the research this adds a feature: **multi-level
   partitioning**. The literature has a direct analogue in multilevel graph and hypergraph
   partitioners (coarsen, partition the coarse graph, refine back down), whose coarsening
   hierarchy is exactly a choice of intermediate units. Two uses for us: an intermediate unit
   (county or CBSA) as the carving grain inside a split state, and a metro unit as the thing
   whose splitting is counted, if the owner ever wants that.

4. **Rule C.** At most one fragmented item per bin. Packing-with-fragmentation papers study
   variants limiting fragments per bin or per item, so there may be structure and bounds.

5. **Pieces must be geometrically attachable.** A fragment counts only if it, with its attach
   states, is connected and neck-free: a capacitated connected partition with prescribed
   terminals.

6. **A thickness condition: the neck.** *Owner asked for a precise definition and an analogue.*

   M1's neck (`docs/problem/MANDATES.md` M1; `td/audit.py` `district_necks`): a district fails
   when one connected part A of it, holding at least 5% of the district's land area and no more
   land than the rest, reaches the rest only through a passage narrower than 10 km, the width
   being the total shared ZCTA border length across the cut. Mass plays no part. An approved
   connector has unlimited width unless the two sides are joined by land inside the district's
   states, where it has width 0.

   As a graph quantity: vertices weighted by land area, edges weighted by shared border length.
   A neck is a cut (A, rest) with edge weight below 10 km whose smaller side holds at least 5%
   of the area and is connected. Dropping the connectivity of A, this is a **minimum balanced
   cut**, and the condition "no such cut exists" is a lower bound on the graph's **edge
   expansion** (Cheeger constant, conductance) with a floor on the small side. In network terms
   it is a weighted edge-connectivity requirement. Three consequences for the research:
   - the exact check is a minimum cut under a side-size floor, NP-hard in general but small per
     district; the audit already solves it with a time limit;
   - inside an optimisation it would be a family of cut rows (like the contiguity cut rows,
     but with a width threshold), so the contiguity-formulation literature is the right place to
     look for how to separate them;
   - the literature's compactness measures (Polsby–Popper, cut edges) are proxies for this,
     not the same condition.

   *Owner asked how this interacts with other Census geographies (feature 3).* Contracting ZCTAs
   into a coarser unit removes cuts and never adds them: every cut of the coarse graph is a cut
   of the fine graph with the same border length. So a neck found at county or CBSA level is a
   neck at ZCTA level (if its area share also holds), while a ZCTA-level neck can vanish when
   the unit containing it is contracted. A coarse-level neck check is therefore a valid screen
   in one direction only, which is the same relation the contracted attach sets had in the
   review. Utah's 84621 pinch lies inside one county, so it is invisible at county grain.

7. **Objective and search structure.** *Owner asked whether the framing can be condensed into
   one formulation in another language.* It can, and the condensed form is clarifying:

   **Hypergraph partitioning with connectivity of the blocks.** Vertices are ZCTAs (or any
   finer unit). Each state is a hyperedge containing its ZCTAs; each intermediate geography
   (county, CBSA, CSA) is another family of hyperedges, nested. A map is a partition of the
   vertices into blocks (districts). Then:
   - **split states** = the number of hyperedges cut by the partition (the **cut-net** metric);
   - **cuts** (Σ over split states of districts − 1) = the **connectivity − 1 metric** (λ − 1),
     the other standard hypergraph objective;
   - **balance** = block weight in [L, U] with a free number of blocks;
   - **rule C** = each block meets at most one cut hyperedge of the state family;
   - **M1** = each block is connected in the underlying planar graph and has no balanced cut
     under 10 km.

   The two split objectives are the two objectives the hypergraph-partitioning literature has
   studied for decades (VLSI, sparse matrices), with multilevel heuristics (hMETIS, KaHyPar,
   PaToH) that handle millions of vertices and nested hyperedge families. What that literature
   lacks is the connectivity and neck conditions on blocks and the per-block rule C. Where it
   helps: fast high-quality incumbents, a vocabulary in which the lexicographic objective is
   already standard, and the coarsening hierarchy of feature 3 as a first-class object.

   *Owner (rev 2): investigate this separately (the `hypergraph` tab) with a robust research
   pipeline that keeps contiguity.* The pipeline, in order:
   1. **Literature.** Hypergraph partitioning with the cut-net and λ−1 objectives and balance
      windows: the multilevel method (coarsening, initial partition, refinement), exact methods
      and bounds, and any work that adds block connectivity in a primal graph ("connected
      hypergraph partitioning", "partitioning with contiguity", graph partitioning with
      connectivity constraints in VLSI floorplanning or parallel mesh partitioning, where
      connected blocks are also wanted).
   2. **Contiguity inside the method.** Three places to keep M1: (a) during refinement, allow a
      move only if both blocks stay connected (what ReCom and flip chains do, and what mesh
      partitioners call contiguity repair); (b) coarsening only along primal edges, so every
      coarse vertex is connected and connectivity survives uncoarsening; (c) a repair and gate
      pass at the end with `td.audit`. Which combination keeps the λ−1 quality is the
      experiment.
   3. **Rule C and necks as block constraints.** Rule C is a per-block count of met cut
      hyperedges; a neck is a balanced min cut inside a block. Both are checkable per block in
      refinement; whether a partitioner can be told about them is a code question (KaHyPar's
      and Mt-KaHyPar's constraint hooks, or a custom refinement loop).
   4. **Prototype on the toy.** Run an off-the-shelf partitioner on the toy map's hypergraph with
      $ weights, then add (2a) and (3), and compare splits, cuts, M1 pass and time against
      carve-first on the same scenarios.
   5. **Bound.** Whether the hypergraph form gives a usable lower bound on cut-net (its LP, or
      the fragmentation bound of feature 4) is the certificate question of section 1.8 in this
      language.

8. **One level or two.** *Owner asked whether the two-level (state master plus ZCTA map)
   structure is needed, or whether one solve with a heuristically restricted search space would
   do.* Separate the two things the two levels provide:
   - **An incumbent.** One level suffices. A single ZCTA-level model with a split binary per
     state is too big exactly (33k ZCTAs, K up to 55; `validi2022`'s largest exact contiguity
     solve is 1,511 units), but restricting the search space collapses it: fix every state
     the screen says can stay whole, leave only candidate states' ZCTAs free, and the model is
     a few thousand free variables. Multilevel hypergraph partitioning and ReCom-style search
     work at the full scale directly. Carve-first is itself a one-level heuristic in this sense:
     the library is a restricted search space.
   - **A certificate.** This is what the coarse level is for. s_lower is a valid bound only if
     every M1-feasible map projects to a plan inside A's domain (an aggregation relaxation). The
     kb has a warning: `shahmizad2026` takes lower bounds only from full plans, not from its
     sketch. If one level is wanted, the bound must come from a relaxation of the one-level
     model instead (its LP or Lagrangian bound, or a cut-based bound from the hypergraph form),
     which is an open question for the research rather than something to assume.

   So: one level for finding maps, with the search space restricted by the screen and rule C;
   the second level only if a certificate is wanted, and then its validity is a lemma to prove,
   not a given.

## 2. Analogous problem classes, ranked by what they can tell us

| Class | What it gives us | Where it stops |
|---|---|---|
| Hypergraph partitioning (cut-net and λ−1 metrics, multilevel methods) | One language for splits, cuts, balance and the unit hierarchy; fast incumbents at full scale | No block connectivity, no necks, no rule C |
| Bin packing with item fragmentation, fragments-per-bin limits | Lower bounds on broken items under a fixed window; structure results; rule C as a studied variant | No adjacency |
| Cutting stock / column generation | How to price patterns, dual bounds, what restricted masters prove | The pricer (carve a state) is itself hard and geometric |
| Balanced connected partition with prescribed terminals | Complexity and exact methods for carving a state | Mostly k = 2 or unit weights |
| Hierarchical districting (sketch then detail, whole-county rules) | Coarse-to-fine formulations; when refinement fails | Balance around total/K |
| Aggregation and projection relaxations | Conditions for a coarse bound to be valid | Generic; the lemma is ours to write |
| Balanced minimum cut, edge expansion, weighted connectivity | The neck as a known quantity; separation of width-threshold cut rows | Cost inside a MILP |
| Forest harvest scheduling, zone design (AZP), school and police districting | Other contiguity encodings, large-instance heuristics | Different objectives |

## 3. Research questions, by feature

Main line:
- **Fragmentation bounds.** Does packing-with-fragmentation give a lower bound on broken states
  stronger than the arithmetic screen, and does the one-fragment-per-bin variant have known
  bounds or feasibility conditions? MD and CT are instances of such a condition.
- **One-level incumbents.** What do multilevel hypergraph partitioners and districting local
  search achieve on cut-net and λ−1 objectives with balance windows, and how has block
  connectivity been added to them?
- **Certificates.** Under what conditions is a coarse-level split bound valid for the fine
  level, why do the closest districting papers decline to claim one from a sketch, and what
  one-level relaxations give a bound instead?
- **Pricing without an exact pricer.** What does column generation prove about restricted
  masters, and has anyone priced connected columns exactly at our scale?
- **Open-source districting tools.** GerryChain and its Julia port, exact districting codes
  (Validi–Buchanan, Gurnee–Shmoys, Swamy et al.), and hypergraph partitioners (KaHyPar,
  Mt-KaHyPar, hMETIS, PaToH): what each takes as input, which of our constraints it can hold
  (contiguity, balance window, split counting, rule C, necks), and what it would cost to run on
  our graph with $ as population at fixed K.
- **Fixed target or fixed K.** The two balance forms search the same space; which gives faster
  solves and better bounds on the toy.

Supporting:
- **Carving.** Balanced connected k-partition with prescribed terminals: complexity, exact
  methods, scale.
- **Necks.** Balanced minimum cut and expansion conditions inside a partition model; cheap
  exact checks.
- **Granularity.** Multilevel coarsening as a model for the intermediate geographies the
  `geography` tab is sizing; what the hierarchical districting papers say about which grain
  to carve at.

## 4. Open for the owner

- Does the hypergraph reading (section 1.7) capture every feature, and should it become the
  working language for the research?
- One level or two (section 1.8): is a certificate still wanted, or is a strong incumbent with
  an honest "no bound" enough for the stakeholder maps?
- Packets are drafted only after this document is settled.
