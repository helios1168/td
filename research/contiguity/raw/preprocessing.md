# Preprocessing, Decomposition, Reduction, and Heuristics/Warm-Starts for Connected 2-Partition Nash MILP

Scope: literature survey for fixing the outer-approximation + lazy-connectivity-cut solver used in
`districting.py::solve_contiguous_nash`. Problem: two-player connected bipartition of a Rook-adjacency
planar graph (ZCTAs), maximize log g_a + log g_b with g linear in 0/1 assignment, both sides connected.
Failure mechanisms observed on the `td` synthetic battery (see `battery/FINDINGS.md`):
(a) pre-existing disconnection in the free (unconstrained) optimum, (b) pure scale (>=125 units),
(c) heavy-tailed unit values inflating contiguity cost and flipping which instances fail.
Verification: every DOI below was fetched from `https://api.crossref.org/works/<DOI>` (or matched via a
`query.bibliographic` crossref search whose returned title/authors/year I checked against the citation)
before being marked VERIFIED.

---

## 1. Graph reduction / variable fixing before the IP

### 1.1 Validi, Buchanan & Lykhovyd (2022), "Imposing Contiguity Constraints in Political Districting Models" — VERIFIED
DOI `10.1287/opre.2021.2141` (Operations Research 70(2):867-892). Crossref-confirmed title/authors/journal/year.
Summary: surveys existing contiguity formulations (flow-based, single-commodity, and Shirabe's), introduces
two new **cut-based** formulations, and shows analytically that the cut-based model is the strongest (its LP
relaxation dominates the flow-based ones). Crucially for preprocessing, they use a **Lagrangian relaxation of
the balance/compactness objective to fix variables**: a unit whose reduced cost in the relaxation certifies it
cannot belong to a given district in any optimal solution is fixed in place before branch-and-cut runs. Their
branch-and-cut with these fixes produced, for the first time, provably optimally-compact districting plans for
21 US states at the census-tract level (up to ~1,500 vertices with contiguity), a scale directly comparable to
the td 400-800 ZCTA real-data target.
Guarantee: **optimality-preserving** — fixing is driven by a certified Lagrangian bound, not a heuristic; the
final solution is still exact/optimal, just found faster.
Addresses: (b) pure scale, directly — this is the state-of-the-art scale result for exact contiguous
districting IPs, and their target sizes (n~1,500) exceed td's real-data range. Indirectly (a) pre-existing
disconnection — fixing undisputed vertices reduces the search space in which spurious splits could occur, but
their method does not explicitly detect "free-optimum" disconnection the way `td`'s proposed component-quotient
idea does.
Implementation cost: **high**. Their code is C++ (`github.com/zhelih/districting`), not a drop-in Python
package; porting the Lagrangian-fixing routine to work with HiGHS via `scipy.optimize.milp` or PuLP would be a
multi-week reimplementation, though the fixing *logic* (solve Lagrangian dual, read reduced costs, fix
above/below threshold) is not exotic and could be built directly against `territory.py`'s existing outer-approx
loop.

### 1.2 Zhang, Validi, Buchanan & Hicks (2024), "Linear-size formulations for connected planar graph partitioning and political districting" — VERIFIED
DOI `10.1007/s11590-023-02070-0` (Optimization Letters). Crossref-confirmed.
Summary: follow-up to 1.1 specifically exploiting **planarity**. Contiguity/connectivity formulations normally
require exponentially many (or, for the best known cut-based formulation, O(n^2)) constraints; this paper shows
that for **planar** graphs a *linear-size* extended formulation suffices, using the planar dual and a clever
encoding of "no district crosses a given dual cycle." Because ZCTA Rook-adjacency graphs are planar by
construction, this result applies directly to `td`'s setting.
Guarantee: optimality-preserving, exact reformulation (not a relaxation) — it changes formulation size, not the
feasible region.
Addresses: (b) pure scale — smaller constraint matrix means fewer cuts to separate and smaller LPs per
node, which is the direct lever on HiGHS's iteration/time limits.
Implementation cost: **medium-high**. Requires building the planar dual graph of the ZCTA adjacency (networkx
has `nx.check_planarity` and can return a planar embedding, from which a dual can be constructed), and encoding
the new linear-size constraints in the MILP. More tractable than 1.1 because it's a formulation change, not an
algorithmic Lagrangian-fixing loop, but it does require care with the planar embedding (which must be kept
consistent if any preprocessing step contracts or removes nodes first).

### 1.3 Buchanan, Wang & Butenko (2018), "Algorithms for Node-Weighted Steiner Tree and Maximum-Weight Connected Subgraph" — VERIFIED
DOI `10.1002/net.21825` (Networks). Crossref-confirmed.
Summary: from the same author group as 1.1/1.2, but attacks the single-connected-side problem directly (NWSTP /
MWCS) rather than 2-district partitioning. Introduces preprocessing/reduction rules (based on connectivity
structure — cut vertices, low-degree contraction) that give "the first improvements over exhaustive search" for
exact MWCS on general graphs, i.e., a reduction+B&B combination purpose-built for the node-weighted connected
subgraph problem that `td`'s zero-value-glue setting reduces to (see §2).
Guarantee: optimality-preserving (reductions are proven safe: they either fix a variable or contract an edge
without changing the optimum).
Addresses: (c) somewhat — MWCS reduction rules are partly designed around skewed/sparse weight distributions
(nodes with zero or near-zero prize are the first to be reduced away), which is structurally identical to td's
real-data "mostly zero-value glue" case. Also (b) scale, since reductions shrink the graph before any B&B.
Implementation cost: **medium**. No public solver artifact was found in search results (unlike SCIP-Jack,
§2.3); the reduction rules would need to be reimplemented from the paper directly against networkx.

### 1.4 "Component-quotient" idea (fixing stray components of the free optimum) — NOT FOUND AS PRIOR ART, likely novel-as-framed
No published paper matching "fix undisputed connected components of the unconstrained optimum, then re-solve
the MINLP on the quotient graph" was found under that name. The closest published relatives are:
- Validi et al.'s Lagrangian variable-fixing (1.1), which fixes *individual vertices*, not whole components,
  and is driven by a certified dual bound rather than "this component happens to already be internally
  agreed-upon in the LP-relaxed/free solution."
- Reduction techniques for PCST/MWCS (§2) that contract or delete *provably* safe substructures (e.g., leaves
  with negative net reduced weight, degree-2 chains) — these are safe by construction, unlike heuristically
  fixing "the free optimum's stray components," which is a **relaxation of exactness** unless one can prove the
  fixed assignment cannot be beaten by any contiguous solution.
Guarantee: **none certified in the literature for td's specific proposal.** Fixing a stray component in place
because "both the solver and human re-assignment prefer the split" (per `CLAUDE.md` Trap 11) is a heuristic
choice, not a proof; it should be validated empirically (does the fixed value ever differ from the true
constrained optimum on cases where both can be computed?) rather than assumed lossless. This is flagged in
"Could not verify" below.
Addresses: (a) pre-existing disconnection, by definition — this is precisely the failure mode it targets.
Implementation cost: **low** — `networkx.connected_components` on the free-optimum's induced subgraphs A and B,
detect components not containing the "seed"/largest block, fix their assignment, and re-run the MINLP on the
quotient graph with those vertices merged into two super-nodes (one per side) plus their external adjacency
carried over. Straightforward with existing `territory.py`/`districting.py` data structures.

---

## 2. Zero-value glue units as node-weighted / prize-collecting Steiner problems

### 2.1 Problem framing
In td's real-data regime (400-800 ZCTAs per pair, most zero-valued on A/B/M), the connectivity requirement for
each side reduces to: given a sparse set of "active" (positive-utility) nodes that must all be included, find
the minimum-cost (here, cost = number of "wasted" zero-value connector nodes, or a compactness/perimeter
penalty on them) connected subgraph joining them — a **node-weighted Steiner tree** if the active set is fixed,
or a **prize-collecting Steiner tree (PCST)** / **maximum-weight connected subgraph (MWCS)** if which active
nodes to include is itself a decision (some low-value active zips may not be worth the connection cost). The
*generalized* two-sided version — both A's territory AND B's territory must independently be connected, and
every glue node goes to exactly one side — is the "generalized prize-collecting Steiner forest" (GPCSF)
structure: multiple terminal groups must each be connected by a shared, partitioned edge/node set.

### 2.2 Álvarez-Miranda, Ljubić & Mutzel (2013), "The Maximum Weight Connected Subgraph Problem" — VERIFIED
DOI `10.1007/978-3-642-38189-8_11` (in *Facets of Combinatorial Optimization: Festschrift for Martin Grötschel*).
Summary: the standard survey/formalization of MWCS — given node weights (positive and negative), find a
connected induced subgraph of maximum total weight. Directly maps to td's problem if one assigns each glue node
a small negative weight (opportunity cost of including it / perimeter penalty) and each active node its true
utility, then asks for the maximum-weight connected subgraph on each side. Covers ILP formulations (single-
commodity flow, cut-based) and their LP-relaxation strength, which parallels the Validi et al. contiguity
formulation comparison (§1.1) but on the MWCS side.
Guarantee: exact formulations discussed are optimality-preserving by construction (valid ILPs); no
approximation-only content in the base survey.
Addresses: (a) and (c). If a side's optimal assignment is reframed as "maximum-weight connected subgraph"
rather than "arbitrary connected partition," the zero-value/negative-value glue nodes are handled by the
formulation itself rather than needing to be pre-fixed, and skewed weights are exactly what MWCS/PCST
formulations are designed around (most of graph has weight ~0, small share of high-value "prizes").
Implementation cost: medium — reframing the per-side subproblem as MWCS is a genuine model change, not just a
solver swap, and interacts with the requirement that BOTH sides partition the same vertex set (i.e., you can't
just solve two independent MWCS problems — a node given to A's MWCS is *removed* from B's, so the two solves
are coupled, not independent, and the coupling is exactly what the Nash objective already handles jointly. This
is really an argument for reformulating the *contiguity* constraint via an MWCS/PCST-style connectivity
substructure, not for decomposing the bilevel Nash+contiguity problem into two separate Steiner solves.)

### 2.3 PCST/MWCS solvers survey — VERIFIED (5 papers)
- Fischetti, Leitner, Ljubić, Luipersbeck, Monaci, Resch, Salvagnin & Sinnl (2017), "Thinning out Steiner
  trees: a node-based model for uniform edge costs." DOI `10.1007/s12532-016-0111-0` (Math. Prog. Computation
  9:203-229). Crossref-confirmed. Node-only ILP formulation (drops edge variables entirely when edge costs are
  uniform, as they are in `td`'s Rook-adjacency setting where "cost" = 1 glue node used). Won the DIMACS11
  Steiner-tree challenge. **Directly relevant**: td's connectivity cost is unit-per-node (or per-perimeter-edge,
  which is also uniform on the Rook grid), so this "thinned" node-based formulation is a near-exact fit and
  likely smaller/faster than a generic edge-based Steiner ILP.
- Leitner, Ljubić, Luipersbeck & Sinnl (2018), "A Dual Ascent-Based Branch-and-Bound Framework for the
  Prize-Collecting Steiner Tree and Related Problems." DOI `10.1287/ijoc.2017.0788` (INFORMS J. Computing
  30(2):402-420). Crossref-confirmed. Generalizes Wong's dual-ascent to the asymmetric PCST, and shows STP,
  PCSTP, MWCS, and NWSTP are all instances of one framework (APCSTP) — meaning one solver/codebase covers all
  the variants relevant to td's glue-node problem.
- Gamrath, Koch, Maher, Rehfeldt & Shinano (2017), "SCIP-Jack — a solver for STP and variants with
  parallelization extensions." DOI `10.1007/s12532-016-0114-x` (Math. Prog. Computation 9:231-296).
  Crossref-confirmed. **The concrete open-source artifact**: SCIP-Jack solves 11 Steiner-family problems
  including PCST, rooted PCST, and MWCS, using SCIP (which, like HiGHS, is open-source, though SCIP additionally
  supports a fuller MINLP/branch-and-cut-and-price framework than scipy's HiGHS wrapper).
- Rehfeldt, Koch & Maher (2019), "Reduction Techniques for Prize-Collecting Steiner Tree Problems." DOI
  `10.1002/net.21857` (Networks). Crossref-confirmed. Presents "numerous new reduction methods" that shrink
  >90% of benchmark instances to triviality before B&B — this is the reduction layer SCIP-Jack uses, and is the
  most mature published analogue to td's "component-quotient" preprocessing idea (§1.4), except proven safe.
- Rehfeldt & Koch (2022), "On the Exact Solution of Prize-Collecting Steiner Tree Problems." DOI
  `10.1287/ijoc.2021.1087` (INFORMS J. Computing). Crossref-confirmed. Solves benchmark instances up to 10
  million edges in under 2 hours — evidence that PCST-family exact solving scales far beyond td's 400-800-ZCTA
  target, *if* the glue-node subproblem can be isolated from the fairness (Nash) objective.
Guarantee (all five): optimality-preserving (branch-and-bound / exact reduction, not heuristic truncation)
unless a time limit is hit.
Addresses: primarily (c) value concentration — PCST/MWCS solvers are explicitly built for instances where most
nodes have zero or negative prize and a few have large prize, which is structurally identical to both td's
heavy-tail mechanism and its real-data sparse-active-zip regime. Also (b) scale, per the 10M-edge result above.
Does not directly address (a), since these solve single-terminal-set connectivity, not the free-optimum-splits-
first-then-must-be-reconciled problem.
Implementation cost: **medium-high for full adoption, low for ideas only**. SCIP-Jack is a C-based solver
requiring a SCIP install (open-source, LGPL, but a heavier dependency than HiGHS-via-scipy); wiring `td`'s
per-side connectivity subproblem through SCIP-Jack instead of scipy's MILP would be a substantial integration.
Cheaper alternative: **borrow the reduction rules only** (degree-2 contraction, non-terminal leaf pruning,
"bottleneck" tests) and implement them directly as networkx preprocessing before handing the reduced graph to
the existing HiGHS-based outer-approximation loop — this captures most of the scale/value-concentration benefit
without an new solver dependency.

### 2.4 Generalized / two-sided connectivity (both sides connected) — thin literature
Targeted search for "generalized prize-collecting Steiner forest" surfaced approximation-only papers (Han et
al. 2017, 3-approx; Jia et al. 2021, 3-approx for submodular penalties — both **UNVERIFIED**, found only via
Consensus abstracts, DOIs not fetched/confirmed) that formalize connecting *disjoint groups* of terminals but do
not address the "every non-terminal node must be assigned to exactly one of two groups, and both resulting sets
must be connected" structure td actually needs. No paper was found solving exactly the "connected bipartition
with sparse node weights" problem as a Steiner-family reduction target; the balanced-connected-k-partition
literature (§2.5) is the closer match despite not using Steiner-tree language.
Addresses: theoretically could address (a)+(c) but not demonstrated in the literature at the fidelity td needs.
Implementation cost: n/a — no ready formulation to borrow; would require original modeling work combining §1.1's
cut-based contiguity ILP with §2.3's node-based PCST reduction rules.

### 2.5 Balanced connected k-partition — VERIFIED, closest structural match
Miyazawa, Moura, Ota & Wakabayashi (2021), "Partitioning a graph into balanced connected classes: Formulations,
separation and experiments." DOI `10.1016/j.ejor.2020.12.059` (European Journal of Operational Research).
Crossref-confirmed.
Summary: studies exactly "partition a node-weighted graph into k connected, balanced classes," i.e., td's
problem with k=2 and "balanced" swapped for "Nash-fair." Contributes ILP formulations, valid inequalities, and
a separation routine for connectivity cuts (lazy constraint generation, structurally identical to what
`districting.py` already does), tested computationally. The k=2 special case of the underlying decision problem
(max-min balanced connected bipartition) is polynomial by a classical result reachable via this same paper's
citations, though the general k>=3 problem is NP-hard even on planar unit-weight graphs (per a broader
complexity search; see also Soltan/Yannakakis/Zussman 2017/2020 "Doubly Balanced Connected Graph Partitioning,"
DOI `10.1137/1.9781611974782.126` / `10.1145/3381419`, not independently crossref-verified for exact title match
beyond the returned metadata, treat as **VERIFIED via crossref return** since both were returned directly by a
crossref DOI-style bibliographic match with consistent authors/venue).
Guarantee: exact ILP formulations optimality-preserving; separation is lazy-constraint (same paradigm as td's
current lazy connectivity cuts), so this paper's main contribution is *better cuts/valid inequalities* for the
same class of algorithm td already runs, not a different paradigm.
Addresses: (b) scale (their separation/valid-inequality work is aimed at making exactly this kind of B&C scale
further) and, incidentally, (c) since balance-type constraints interact with weight skew similarly to Nash
fairness.
Implementation cost: **medium** — the paper's connectivity-cut separation routines could plausibly be
transplanted into `districting.py`'s existing lazy-cut loop as *additional* or *stronger* cuts, without
replacing the outer-approximation/Nash machinery.

---

## 3. Coarse-to-fine / multilevel

### 3.1 Karypis & Kumar (1998), "A Fast and High Quality Multilevel Scheme for Partitioning Irregular Graphs" — VERIFIED
DOI `10.1006/jpdc.1997.1404` (J. Parallel and Distributed Computing 48:96-129; this is METIS's foundational
paper). Crossref-confirmed.
Summary: the canonical multilevel graph partitioning method: coarsen the graph (matching/contraction) down to a
small size, partition the coarse graph (fast, often exactly, since it's small), then uncoarsen with local
refinement (Kernighan-Lin/Fiduccia-Mattheyses style) at each level to fix up the boundary.
Guarantee: **heuristic, not optimality-preserving.** METIS-style multilevel partitioning has no exactness
certificate; it is a fast approximate partitioner, useful for balance/edge-cut objectives, not for exact Nash
welfare maximization with a hard contiguity constraint. Refinement at each level generally preserves
connectivity of a k-way partition only if the local-search moves are restricted to preserve it (not METIS's
default; a boundary-KL move can disconnect a partition), so an off-the-shelf METIS run does **not** guarantee
contiguous output — it would need contiguity-aware refinement bolted on.
Addresses: (b) scale, as a coarse *first pass* to get a fast starting bipartition (then exact-solve at the fine
level only within a corridor of disputed nodes near the boundary — effectively another form of "fixing
undisputed regions," complementary to §1.4). Does not directly address (a) or (c); could even worsen (c) since
coarsening tends to average/smooth heavy-tailed weights, hiding the very skew that causes trouble at the fine
level.
Implementation cost: **low-medium** to use as a coarsening heuristic for a warm start (aggregate ZCTAs to
county or 3-digit-ZIP supernodes, solve the small exact Nash+contiguity problem there, use the resulting
coarse partition to seed which fine-level ZCTAs are "obviously" A vs B before running the full MILP) — networkx
can do simple contraction; getting refinement to *respect* the exact contiguity constraint (rather than
METIS's own heuristic refinement) is the real engineering work, and would need to be hand-built rather than
calling `pymetis`/`networkx-metis` as a black box.

### 3.2 Gurnee & Shmoys (2021), "Fairmandering: A column generation heuristic for fairness-optimized political districting" — VERIFIED
Fetched directly at DOI `10.1137/1.9781611976830.9`; crossref returned matching title/authors/venue/year
(SIAM ACDA 2021).
Summary: two-stage method — (1) a randomized divide-and-conquer **column generation** heuristic that produces
an ensemble of many distinct, individually-valid (contiguous, balanced) district plans by recursively splitting
the graph, generating candidate districts as "columns"; (2) a **master selection** ILP (a set-partitioning-style
problem) that picks one column per district slot to optimize an arbitrary piecewise-linear fairness objective.
Column generation is inherently a decomposition/coarse-to-fine method: candidate districts are built
bottom-up on subgraphs before the top-level selection problem is solved.
Guarantee: the master selection stage is exact given its column pool (bounded by whatever objective bound the
selection ILP's LP relaxation gives), but the overall pipeline is a heuristic w.r.t. the *original* problem
because the column pool is not exhaustive — no global optimality certificate versus the true fine-level optimum.
It **does** produce a legitimate upper bound on achievable fairness *restricted to the generated column set*,
and every produced plan is a genuine feasible (contiguous, balanced) solution, so it is usable as a strong warm
start / fallback.
Addresses: (b) scale (this is explicitly a "scalable to large states" method) and structurally, since districts
are two-sided partitions of a graph, it is adjacent to (a) — because each column is contiguous by
construction, using such a scheme to generate an initial *feasible*, contiguous bipartition sidesteps the
free-optimum-splits-first failure mode entirely for the warm start (though the final answer would still need
Nash-exact refinement).
Implementation cost: **medium-high**. Column generation with a custom pricing subproblem (here, itself a
constrained shortest-path/tree-growing procedure per district) is a nontrivial matheuristic to port; the
authors' code is public (per search results referencing `arxiv:2103.11469` and GitHub artifacts) but built for
k-way political districting with population-balance objectives, not two-player Nash welfare — the master
selection objective would need to be replaced with (or extended to support) the Nash log-sum, and column
pricing would need to reflect per-zip A/B/M utility rather than population/compactness.

---

## 4. Heuristics and matheuristics for warm-starting or fallback

### 4.1 DeFord, Duchin & Solomon (2021), "Recombination: A Family of Markov Chains for Redistricting" — VERIFIED
DOI `10.1162/99608f92.eb30390f` (Harvard Data Science Review). Crossref-confirmed.
Summary: introduces ReCom, a Markov chain on graph partitions: at each step, merge two adjacent districts,
draw a **random spanning tree** on the merged subgraph, then cut an edge of that tree to re-split into two
*guaranteed-connected* pieces satisfying a balance target. Implemented in the open-source `GerryChain` Python
package. Widely used for large-scale ensemble sampling of legislatively-valid (contiguous, population-balanced)
district plans, including at the precinct/census-block level (comparable density to ZCTA-level data).
Guarantee: **feasibility-preserving, not optimality-seeking** — every state of the chain is a valid contiguous
partition (by construction of the spanning-tree cut), but ReCom is a sampler / local-search move set with no
lower-bound or upper-bound certificate on any fairness objective; it explores the space rather than proving
anything about it. Can be biased (Metropolis-Hastings-style acceptance) toward higher Nash welfare to turn it
into a heuristic *optimizer*, but that requires nontrivial reweighting; used naively it is not even hill-
climbing.
Addresses: (a) directly, as a warm-start generator — a single ReCom merge-split move applied to the
raw graph (rather than to an already-split partition) is essentially "given a merged region, find *any*
connected 2-split of it," which is exactly the reconciliation step needed when the free optimum's stray
components must be re-attached to a single component per side. Also generally useful against (b)/(c) as a
fast, always-feasible fallback when the exact MINLP times out — GerryChain runs comfortably at multi-thousand-
node scale.
Implementation cost: **low**. `gerrychain` is a pip-installable, actively maintained Python package built on
networkx graphs; wiring it to consume `td`'s existing graph object (fixing rep_a/rep_b assignment as a "start
plan," using A_z+lam*M_z / B_z+lam*M_z as node weights for a 50/50-ish balance target as a *proxy* objective) is
plausibly a day or two of integration work, and gives (i) an always-feasible fallback solution and (ii) — with
appropriately many ReCom steps started from the free optimum — a warm-start incumbent to hand to the exact
MILP as an initial feasible solution / MIP start, which HiGHS supports.

### 4.2 Ríos-Mercado & Fernández (2009), "A reactive GRASP for a commercial territory design problem with multiple balancing requirements" — VERIFIED
DOI `10.1016/j.cor.2007.10.024` (Computers & Operations Research 36(3):755-776). Crossref-confirmed.
Summary: GRASP (Greedy Randomized Adaptive Search Procedure) for territory design with contiguity and multiple
balance requirements, motivated by a real commercial (beverage distribution) application — structurally the
closest *industry* analogue to td's rep-territory problem. "Reactive" here means the RCL (restricted candidate
list) greediness parameter self-tunes based on recent solution quality, and a filtering step skips local search
on unpromising constructions to save time.
Guarantee: heuristic, **feasible solutions only** — GRASP as a metaheuristic provides no dual/upper bound; it
is a construct-then-local-search loop with restarts, standard for territory design in the OR literature (this
paper plus a small family of companion papers by the same group — bi-objective scatter search, tabu-based
variants — form the standard heuristic toolkit for the problem class, but none of the variants found in this
search provide bounds).
Addresses: (a)/(b)/(c) generically as a robust fallback: GRASP constructions are typically built directly
respecting contiguity by growing territories from seeds (avoiding the "free optimum splits first" pathology by
never solving a free/uncontiguous relaxation at all), so it never encounters (a). Scales to whatever size the
construction/local-search step scales to (GRASP is not MILP-based, so (b)'s HiGHS-specific limits don't apply,
though genuinely large instances slow local search). Skewed weights (c) mainly affect *how good* the resulting
heuristic solution is relative to true optimum, which GRASP cannot quantify without an independent bound.
Implementation cost: **medium**. No off-the-shelf open-source package was found for this specific GRASP variant
(unlike GerryChain); it would need reimplementation (seed selection, greedy growth respecting the Rook adjacency
and an A/B assignment target, local search moves that swap boundary zips while preserving contiguity) — a
moderate custom-coding project, on the order of the effort to write `districting.py` itself, though considerably
simpler since it need not certify optimality.

### 4.3 Bozkaya, Erkut & Laporte (2003), "A tabu search heuristic and adaptive memory procedure for political districting" — VERIFIED
DOI `10.1016/s0377-2217(01)00380-0` (European Journal of Operational Research 144:12-26). Crossref-confirmed.
Summary: tabu search with an adaptive memory (pool of elite solutions recombined periodically) for political
districting with population balance, compactness, and (as a hard constraint, checked at each move) contiguity.
Guarantee: heuristic, feasible-only, no bound — same caveat as §4.2.
Addresses: same profile as §4.2 — avoids (a) by construction (moves are contiguity-preserving swaps of
boundary units), practical fallback for (b)/(c).
Implementation cost: medium, similar to §4.2 (tabu search with move-list and aspiration criteria is a
well-trodden but nontrivial implementation).

### Which heuristics give *both* a feasible solution and an upper/lower bound?
Of everything surveyed, only three provide anything beyond a feasible incumbent:
1. **Validi et al.'s Lagrangian fixing (§1.1)** and **Rehfeldt/Koch-style PCST reduction+dual-ascent (§2.3)**
   give certified dual bounds (Lagrangian / dual-ascent lower bounds on cost, upper bounds on prize) alongside
   a feasible primal — these are exact-method internals, not standalone heuristics, but they are the only
   surveyed techniques with a **provable optimality gap**.
2. **Column generation (Fairmandering, §3.2)** gives a bound *restricted to its generated column pool* (an
   upper bound on fairness achievable by any selection from that pool), which is informative but not a bound on
   the true unrestricted optimum.
GRASP (§4.2), tabu search (§4.3), and ReCom (§4.1) are pure primal heuristics/samplers with **no bound**
whatsoever; their only role in an exact pipeline is as a warm-start incumbent (to prune the B&B tree faster and
give a stopping-early fallback answer with a known, if uncertified, quality).

---

## 5. Symmetry, degeneracy, and near-tied objectives (cut thrashing)

Search for districting-specific "flat objective" / tie-breaking literature returned mostly generic material:
- Symmetry-breaking constraints for districting ILPs are described in general terms (assign the district
  containing the largest/lowest-indexed unit a fixed label, breaking the permutation symmetry among district
  *labels*) but this only removes label symmetry — it says nothing about **near-tied but label-fixed**
  allocations, which is td's actual "flat objective / cut thrashing" concern (many different partitions all
  within epsilon of the same Nash welfare, so successive separation cuts oscillate between similar-value
  incumbents rather than converging). No paper matching that specific phenomenon under any of "objective
  perturbation," "lexicographic tie-breaking," or "compactness as tie-breaker" was found and independently
  DOI-verified in this pass; the general ILP symmetry literature (e.g., the well-known Margot survey "Symmetry
  in Integer Linear Programming," found via search but not fetched/verified here — **UNVERIFIED**, treat as a
  pointer only) covers *combinatorial* symmetry (relabeling), not *near-degenerate objective landscape* cut
  thrashing.
- The practical remedy implied across the districting-IP literature (Validi et al. 1.1, Miyazawa et al. 2.5) is
  exactly what td's own `rho` parameter already does: add a small secondary objective (perimeter/compactness)
  as a tie-breaker so the LP relaxation is no longer flat along the Nash-optimal-value hyperplane, which
  provably eliminates cut thrashing caused by *exact* ties (though not by near-ties within numerical tolerance).
This is flagged as a genuine literature gap in "Could not verify" below rather than papered over.

## 6. Value concentration and IP hardness under skewed weights

### 6.1 Pisinger (2005), "Where are the hard knapsack problems?" — VERIFIED
DOI `10.1016/j.cor.2004.03.002` (Computers & Operations Research 32(9):2271-2284). Crossref-confirmed (note: a
second, near-duplicate crossref record under DOI `10.1016/s0305-0548(04)00036-x` also matched this title/author/
year and may be the pre-2005 "in press" DOI for the same article — flagging the duplication rather than
resolving it, since both point to the identical bibliographic record).
Summary: systematically shows that "hardness" for the 0-1 knapsack problem is not about size but about
**weight/profit correlation and spread** — instances with strongly correlated, low-range weights/profits are
easy for dynamic programming; instances specifically engineered to defeat bounds (e.g., "spanner" instances)
are hard for branch-and-bound regardless of size. Directly relevant framing for mechanism (c): heavy-tailed
A_z/B_z values are a distributional analogue of Pisinger's hard-instance classes, since a few dominant-value
units make the LP bound loose (fractional relaxation puts weight on the few big items) while the combinatorial
choice of *which* small items fill out the rest remains genuinely combinatorially hard.
Guarantee: n/a — this is a hardness/benchmarking study, not an algorithm.
Addresses: (c) directly, as the theoretical grounding for *why* value concentration should be expected to hurt
B&B performance (loose LP bounds, many near-tied combinations of small items), independent of any districting-
specific mechanism.
Implementation cost: n/a (diagnostic, not a technique) — but it does suggest concrete **remedies** standard in
the knapsack/MILP literature and worth testing on td's C9 heavy-tail cases: (i) **scaling** node values to
reduce numerical spread before handing them to HiGHS (preserves ranking, changes conditioning); (ii) **cover
cuts** / lifted cover inequalities (well-studied for knapsack-type constraints, e.g. Yang et al. 2021
multivariable branching for 0-1 knapsack, INFORMS J. Computing — found via Consensus, **UNVERIFIED** DOI not
independently fetched in this pass) — since td's per-side balance/welfare constraints are knapsack-like, adding
cover cuts on the A-side and B-side value sums is a plausible, low-cost intervention; (iii) tightening big-M
constants in the current MILP formulation using the true achievable range of g_a, g_b rather than generic
bounds, which shrinks the LP feasible region without changing the IP optimum.

---

## Ranked shortlist (top 5) for THIS problem

1. **Reduction rules from PCST/MWCS solvers (§2.3, especially Rehfeldt/Koch/Maher's reduction techniques and
   Buchanan/Wang/Butenko's NWSTP algorithms)**, reimplemented directly in networkx as a preprocessing pass
   before the existing HiGHS MILP — not adopting SCIP-Jack wholesale, just its safe reduction rules (leaf
   pruning on zero-value nodes, degree-2 contraction). Best fit because it's optimality-preserving, targets
   mechanism (c) (which is td's newest and least-understood failure mode) and mechanism (b) simultaneously, and
   is implementable without a new solver dependency.
2. **GerryChain / ReCom (§4.1)** as a warm-start + fallback generator. Lowest implementation cost of anything
   surveyed (pip-installable, mature), directly targets mechanism (a) by never constructing an uncontiguous
   free optimum in the first place, and gives HiGHS a MIP-start incumbent for the exact solve.
3. **Validi/Buchanan/Lykhovyd Lagrangian fixing + cut-based contiguity formulation (§1.1) and its linear-size
   planar refinement (§1.2)**. Highest ceiling on mechanism (b) — this is the literature's actual state-of-the-
   art scale result for exact contiguous districting — but highest implementation cost (C++ port / substantial
   reimplementation).
4. **Component-quotient preprocessing as td already proposes (§1.4)**, validated empirically rather than
   assumed exact — cheapest to implement, targets mechanism (a) precisely, but needs a verification harness
   (compare fixed-in-place answer against the true constrained optimum on small cases) since no paper certifies
   this exact heuristic as lossless.
5. **Balanced-connected-k-partition cut/separation routines (§2.5, Miyazawa et al.)** as additional valid
   inequalities inside the existing lazy-cut loop — medium cost, medium payoff, but the closest published
   problem statement to td's actual k=2 balanced-connected-partition structure, so its cuts are the most
   likely of anything surveyed to transplant cleanly.

## Could not verify / open questions

- **The "component-quotient" fixing idea as td has framed it** (fix stray components of the *free* Nash
  optimum in place) has no direct published precedent found in this search; existing "fixing" literature (§1.1,
  §1.4 discussion) fixes individual vertices via a certified dual bound, not whole heuristically-chosen
  components. Whether td's proposed version is optimality-preserving is **open** and should be tested
  empirically before being trusted at scale.
- **Generalized two-sided connectivity Steiner formulations** (§2.4) — no paper was found that solves "connected
  bipartition with sparse node weights" as a named Steiner-family reduction target; the two approximation papers
  found (Han et al. 2017; Jia et al. 2021) are UNVERIFIED (DOIs not fetched) and address a different structure
  (disjoint terminal groups, not an exhaustive bipartition).
- **Symmetry/tie-breaking under near-flat objectives (cut thrashing)** (§5) — no districting-specific paper on
  this exact phenomenon was found and verified; Margot's general ILP symmetry survey was located but not
  DOI-verified in this pass and, in any case, addresses combinatorial relabeling symmetry rather than
  near-degenerate objective landscapes.
- **Cover cuts / lifted inequalities for knapsack-like balance constraints** (§6.1) — Yang et al. (2021)
  multivariable branching paper is plausible but its DOI was not independently fetched/confirmed via crossref in
  this pass; treat as UNVERIFIED and re-check before citing.
- **Pisinger's duplicate DOI** (§6.1) — two crossref records (`10.1016/j.cor.2004.03.002` and
  `10.1016/s0305-0548(04)00036-x`) both matched the same title/authors/year; likely an artifact of a 2004
  "articles in press" DOI later superseded by the final 2005 issue DOI, but this was not further disambiguated.
- **Doubly Balanced Connected Graph Partitioning** (Soltan, Yannakakis & Zussman, §2.5) — returned by a
  bibliographic crossref search with consistent metadata but not fetched by exact DOI lookup; treat as
  provisionally verified only, re-confirm with a direct `/works/<DOI>` fetch before relying on it further.
