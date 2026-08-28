# Contiguity encodings for k=2 districting integer programs — literature survey

Scope note on the target problem: two-player fair division of 400-800 ZCTAs on a
Rook-adjacency planar graph, k=2 districts (a "connected bipartition" — S and its
complement Z\S both connected), sparse "active" units + zero-value glue units,
open-source solvers only (scipy/HiGHS, or python-mip+CBC, or pyscipopt/SCIP, or
OR-Tools). Currently: outer-approximation (Kelley cuts on the Nash log objective)
interleaved with lazily-added separator cuts via fresh `scipy.optimize.milp` (HiGHS)
solves each round — i.e., a re-solve-from-scratch loop, not a branch-and-cut callback.
Observed failure modes: (a) pre-existing disconnection of the unconstrained optimum,
(b) pure scale (>=125 units), (c) heavy-tailed unit values moving which instances fail
and inflating contiguity cost 2-5x.

All DOIs below were checked against `https://api.crossref.org/works/<DOI>` (title,
authors, container-title, year) unless marked UNVERIFIED.

---

## 1. Candidate encodings / methods

### 1.1 Shirabe flow-based contiguity ("SHIR")

**Citation:** Takeshi Shirabe (2005), "A Model of Contiguity for Spatial Unit
Allocation," *Geographical Analysis* 37(1):2-16. DOI 10.1111/j.1538-4632.2005.00605.x.
VERIFIED (Crossref title/author/journal match; Crossref lists year as 2004 due to
online-first dating, print year is 2005 per the journal and all secondary sources).
Companion/extension: Takeshi Shirabe (2009), "Districting Modeling with Exact
Contiguity Constraints," *Environment and Planning B: Planning and Design*
36(6):1053-1066. DOI 10.1068/b34104. VERIFIED.

**Summary:** Introduce a directed flow variable per district-center-and-edge pair.
Flow originates at a fixed district "center" (root) and is consumed one unit at a
time by every other vertex assigned to that district; a vertex can receive flow of
type j only if it is assigned to district j, and flow cannot re-enter the root. This
single-commodity, per-root flow structure is a compact, single-shot MILP encoding of
"every included vertex is reachable from the root within the induced subgraph" — it
is exactly a spanning-arborescence/feasibility flow condition, not an exponential
cut family. For a Hess-style (n^2-variable) districting model it adds O(n*m) flow
variables (bounded above by O(n^2) on planar/sparse graphs since m=O(n)); for a
labeling model restricted to k districts it is smaller. Widely regarded (per
Buchanan's 2023 survey, "Political Districting") as "arguably the most popular
contiguity constraints in the literature."

**Formulation size, k=2 (Hess-style):** n^2 assignment variables + 2 root indicators
+ O(n*m) flow variables (one commodity per root, i.e. 2 commodities for k=2, so
~2*2*m = O(m) flow variables if roots are fixed in advance, or O(n*m) if root choice
is also a variable). With Rook-planar m<=3n-6, so flow variables are O(n) per
commodity once roots are fixed — this is a major simplification specific to k=2 with
fixed roots (exactly the current td.py setup, which fixes roots per side).
Constraints: O(n) flow-conservation/coupling constraints per commodity.

**Exact in one solve vs lazy:** Single MILP, no lazy separation needed — this is the
formulation's main selling point. All constraints are stated up front; contiguity is
enforced by a polynomial-size flow-feasibility system, not an exponential cut family.

**Guarantee:** Global optimality certificate at LP-relaxation-based branch-and-bound
termination, same as any exact MILP encoding — no approximation.

**Computational evidence:** No large-scale computational study in the original 2005/
2009 papers (they are the modeling papers, not the scale-testing papers). Downstream
adopters report: Validi, Buchanan & Lykhovyd (2022, see below) use SHIR as a baseline
comparator against their new formulations on county- and tract-level US districting
instances (up to several thousand units); Duque, Church & Middleton (2011, see
1.3) implement a SHIR-style "FlowPRM" and find it the fastest of their three
formulations on n<=49-unit synthetic instances but still unable to solve 4 of 10
test cases (n=49, various p) to optimality within a 3-hour CPLEX 11.2 cutoff — direct
evidence that even the flow encoding hits scale trouble by n~50 with weak node-level
compactness or population-balance side constraints. Swamy, King & Jacobson (2023,
Operations Research) use the Shirabe flow model at the multilevel-partition sub-scale
for US congressional districting.

**Failure-mode relevance:** (b) Pure scale — flow variable count and continuous LP
relaxation slack grow with n*m, and it is known empirically to need Lagrangian/
variable-fixing acceleration (Validi et al. fixed 1,094,116 -> 12,425 Hess variables,
a 99% reduction, before flow+separator constraints became tractable at n~1,500) to
reach that scale — so raw SHIR alone plausibly still exhibits mechanism (b). It does
NOT directly address (a) pre-existing disconnection (that's a property of the free-
Nash optimum, independent of encoding) or (c) value concentration (a numerics/
branching issue, not a topology-of-constraints issue) — though a compact,
single-shot formulation gives the branch-and-bound solver a cleaner LP relaxation to
work with under (c), which may help indirectly.

**Open-source implementability:** Directly implementable as an upfront, single
`scipy.optimize.milp` call (fixed roots means the flow-conservation constraints are
linear equalities/inequalities, no lazy generation needed) — this is a genuine
architecture change from the current lazy-separator loop, not just a solver swap.
Also implementable in python-mip+CBC or pyscipopt without any callback machinery.

---

### 1.2 (a,b)-separator cut inequalities ("CUT" / lazy branch-and-cut)

**Citation:** Hamidreza Validi, Austin Buchanan, Eugene Lykhovyd (2022),
"Imposing Contiguity Constraints in Political Districting Models," *Operations
Research* 70(2):867-892. DOI 10.1287/opre.2021.2141. VERIFIED (Crossref title/
authors/journal/year match). Won the 2021 INFORMS Computing Society Harvey J.
Greenberg Research Award.

**Summary:** For nonadjacent vertices a,b and a vertex set C that separates them
(no a-b path in G[V\C]), the inequality x_{aj}+x_{bj} <= 1 + sum_{c in C} x_{cj}
forbids a and b being assigned to the same district j unless some separator vertex
is also in j (bridging them). There are exponentially many such inequalities (one
per separator), so they are added lazily in a branch-and-cut loop whenever an
integer-feasible but disconnected solution is found. The paper reviews SHIR and CUT
(both pre-existing) and introduces two new formulations, MCF (multi-commodity flow)
and LCUT (a strengthened, length-bounded separator cut exploiting population lower
bounds), giving four formulations total. LCUT is shown to be the strongest (tightest
LP relaxation) of the four. The paper proves that, contrary to conventional wisdom,
imposing contiguity does not make the underlying districting MILP harder to solve in
practice, and — using a CUT-based branch-and-cut — produces provably optimal,
compact districting plans for 21 different US states at the census-tract level for
the first time.

**Formulation size, k=2:** Base model (Hess or labeling) unchanged; CUT/LCUT add
zero variables and (in the worst case) an exponential number of constraints, but
only a small number are ever materialized because they are separated lazily from
integer-infeasible-for-contiguity incumbents. Separation (finding a violated a,b-
separator) is solvable in O(n^2 log n) time for fractional solutions and O(n^2) for
integer solutions on planar graphs (a key structural fact proved in this paper).
Because the target problem is exactly k=2, a and b range only within one side at a
time and "C" is a vertex cutset of that side's induced subgraph — the same
complexity bound applies directly.

**Exact in one solve vs lazy:** Requires lazy constraint generation / branch-and-cut
(a proper callback architecture: separate violated cuts at each integer incumbent,
add them, continue B&B) OR an outer loop that resolves-from-scratch after adding
found violated cuts — this is structurally identical to what `districting.py`
already does today with its own separator-cut loop, except the paper's version adds
LCUT's length-bounded strengthening and formal separation-complexity guarantees, and
(crucially) is run inside a true branch-and-cut with warm starts rather than a
cold, fresh MILP solve every round.

**Guarantee:** Exact — a finite branch-and-cut with lazy separation still returns a
certified global optimum (all missing constraints are re-checked/added until no
violation remains); this matches the outer-approximation + separator-cut
architecture already used in `districting.py`.

**Computational evidence:** In experiments with a moment-of-inertia (MOI) objective,
the authors find few separator inequalities are needed in practice, and instances
with up to 1,500 vertices are solved to proven optimality (per the summary in
Buchanan's 2023 survey "Political Districting," citing this paper directly) — this
is far beyond the ~125-unit wall in the target problem's failure mode (b), though
under a different (MOI, not Nash-log) objective and with true branch-and-cut, not
re-solve-from-scratch. The main OR paper additionally reports optimal compact plans
for 21 US states at census-tract granularity (tens of thousands of tracts per
state) using the CUT-based branch-and-cut with variable-fixing preprocessing
(heuristic ~4s + Lagrangian ~3s reduced 1,094,116 Hess variables to 12,425, a 99%
reduction, before the main B&C run).

**Failure-mode relevance:** (b) Pure scale — this is the paper's headline result:
CUT/LCUT-based branch-and-cut scales to instances an order of magnitude past the
current 125-unit wall, PROVIDED it runs as true lazy branch-and-cut with warm starts
and variable fixing, not a cold re-solve loop. (a) Pre-existing disconnection is
orthogonal to the encoding — it's a property of the unconstrained optimum, so no
contiguity *encoding* fixes it; the project's own proposed component-quotient
preprocessing is the right complementary fix. (c) Value concentration: no direct
evidence either way, but a much smaller number of active (lazily-added) constraints
than SHIR's dense a-priori flow variables may make heavy-tailed objective
coefficients less likely to blow up branch-and-bound node counts, since the LP
relaxations stay smaller. Not tested by this paper against heavy-tailed unit values.

**Open-source implementability:** The separation subroutine (find min a,b-vertex-cut
in a planar graph, O(n^2)) is simple to implement in pure Python/networkx (min-cut on
node-split graph, or use `networkx.minimum_node_cut`). The catch is that
`scipy.optimize.milp`/HiGHS via scipy has no native lazy-constraint callback — so a
faithful re-implementation needs either (i) python-mip + CBC, which supports lazy
constraint callbacks (`model.lazy_constrs`), or (ii) pyscipopt (SCIP), which has a
full constraint-handler/lazy-cut callback API, or (iii) keep the current re-solve-
from-scratch loop (which the project already does) but adopt LCUT's stronger,
length-U separator inequalities to cut the number of rounds needed. Note: CUT/LCUT
without a true callback (i.e., in a cold re-solve loop) is exactly what
`districting.py` already implements — so the actionable upgrade here is (1) LCUT's
length-U strengthening, and (2) migrating off `scipy.optimize.milp` to python-mip+CBC
or pyscipopt to get real B&C warm-starting.

---

### 1.3 Ordered-area / hierarchical assignment ("OrderPRM" / Cova-Church)

**Citation:** Juan C. Duque, Richard L. Church, Richard S. Middleton (2011), "The
p-Regions Problem," *Geographical Analysis* 43(2):104-126. DOI
10.1111/j.1538-4632.2010.00810.x. VERIFIED. Builds on: Thomas J. Cova and Richard L.
Church (2000), "Contiguity Constraints for Single-Region Site Search Problems,"
*Geographical Analysis* 32(4):306-329 (ordered-area assignment origin; not
independently DOI-verified here, cited secondhand via Buchanan's 2023 survey
reference list, UNVERIFIED as a standalone check but internally consistent across
two independent sources).

**Summary:** Introduces THREE k-region MIP formulations and directly compares them
computationally: **TreePRM** (spanning-forest with adapted Miller-Tucker-Zemlin (MTZ)
subtour-elimination constraints — tour-breaking constraints borrowed from the TSP);
**OrderPRM** (each region has one designated root; other units are assigned an
"order" o and a unit can be assigned to region k at order o only if some neighbor is
assigned to k at order o-1 — a hop-distance-from-root labeling, closely related to
the "distance-based"/"DAG-based" contiguity constraints later catalogued by
Buchanan's group); **FlowPRM** (a direct re-implementation of Shirabe 2005's flow
idea, one sink per region). All three are single-shot MILPs (TreePRM's MTZ
constraints are also single-shot, not lazy) except for a "recursive cycle-breaking"
variant of TreePRM that lazily adds violated-cycle cutset inequalities (structurally
identical to CUT/1.2, restricted to cycles rather than general separators).

**Formulation size, general k, n areas (closed forms given in the paper's Table 3,
with sum|N_i| the total adjacency-list length, ~ m for planar Rook graphs):**
- TreePRM: constraints = 1 + n^3 - n^2 + 3n + 2*sum|N_i| (the n^3 term comes from
  triangle-consistency constraints on region-membership indicators t_ij: dominant
  driver of size); variables = n^2 + sum|N_i|.
- OrderPRM: constraints = n*p*(n-p+1) + n + p*(1+(n^2-n)/2); variables =
  n*p*(n-p+2) + (n^2-n)/2. For k=2 this is O(n^2) constraints/variables — the
  ordering index o ranges up to n-p+1 in the worst case, and this "worst-case
  contiguity order" (a long snaking chain) is exactly what happens under sparse
  active-unit-plus-zero-value-glue geography, i.e., exactly this project's real-data
  shape.
- FlowPRM: constraints = p*((n^2-n)/2 + 1) + 2np + n + 2p*sum|N_i|; variables =
  2np + p*sum|N_i| + (n^2-n)/2. Smallest in constraints of the three, grows with
  both n and p (unlike TreePRM, which the paper notes is p-insensitive).
For k=2 specifically, p=2 collapses all three formulas to low-order-polynomial-in-n
expressions, but TreePRM's n^3 term still dominates unless n is very small.

**Exact in one solve vs lazy:** All three are single-shot MILPs as originally posed
(no lazy generation); the paper's second half proposes lazy "recursive cycle-
breaking" as an acceleration for TreePRM specifically (Pseudocode 1: solve without
MTZ cycle-breaking constraints, detect cycles, add cutset inequalities forbidding
that exact cycle's edge set, re-solve, repeat) — an explicit re-solve-from-scratch
loop (their own CPLEX runs re-solve each round), directly analogous to
`districting.py`'s current architecture.

**Guarantee:** All exact (proven-optimal when CPLEX terminates); no approximation
built in.

**Computational evidence — the most directly relevant scale data found in this
survey.** CPLEX 11.2 on a single desktop (2.99 GHz, 8 GB RAM), 10 synthetic 4x4/5x5/
7x7 lattice instances (n=16, 25, 49; p=3-10), 3-hour cutoff per run: TreePRM solved
40% to proven optimality (60% timed out at 3h); OrderPRM solved 30% (worst — order
index blow-up for small p); FlowPRM (Shirabe-style) solved 50%, the best of the
three, and additionally failed to find ANY feasible solution for 2 of the n=49
instances within 3h. With acceleration (initial-seed root-fixing for
Order/FlowPRM, recursive cycle-breaking for TreePRM): TreePRM 50% optimal,
OrderPRM 50% optimal, FlowPRM 60% optimal, and the two previously-infeasible n=49
cases became feasible (though not proven optimal). **This is direct, quantitative
evidence that even Shirabe's flow encoding — the "exact in one solve, no lazy
generation" formulation — starts failing to converge to proven optimality by
n=25-49 on generic CPLEX with no further structural exploitation, i.e., well below
the target problem's 400-800-unit real-data scale and even below the project's
already-documented n>=125 scale wall for HiGHS.** This corroborates failure mode
(b) independent of the specific solver (CPLEX vs. HiGHS) and independent of exact
encoding family (flow vs. order vs. tree) — scale is a shared pain point across all
three "single-shot" families absent extra acceleration (root-fixing, warm starts,
symmetry-breaking, lazy separation).

**Failure-mode relevance:** (b) Directly documents scale failure at surprisingly
small n (25-49) even for exact single-shot flow encodings absent extra tricks —
strong caution against assuming SHIR alone solves the scale problem. (a)/(c) not
addressed or tested in this paper (synthetic homogeneous lattices, not tested under
heavy-tailed values or pre-existing disconnection).

**Open-source implementability:** All three formulations are simple to state
directly as `scipy.optimize.milp` linear constraints (no lazy generation needed for
the base TreePRM/OrderPRM/FlowPRM); the accelerated "recursive cycle-breaking"
variant of TreePRM is exactly a re-solve-from-scratch loop, directly portable to the
current architecture with no callback requirement.

---

### 1.4 MTZ-style single-commodity flow / spanning-tree subtour elimination (general)

Covered above as TreePRM (1.3) and as the "tree-based" and "DAG-based" variants
catalogued in Buchanan's 2023 survey (Zoltners & Sinha 1983 tree-based constraints,
noted explicitly as INVALID — they cut off feasible contiguous solutions, not just
inefficient; DAG-based and distance-based relaxations of them are valid but weaker
than SHIR/CUT). Not separately re-covered here to avoid duplication; see 1.3 and the
survey extract in Section 3.

---

### 1.5 Williams spanning-tree extended formulation (planar graphs)

**Citation:** Justin C. Williams (2002), "A Linear-Size Zero-One Programming Model
for the Minimum Spanning Tree Problem in Planar Graphs," *Networks* 39(1):53-60.
DOI: not independently Crossref-verified (Networks/Wiley DOI lookup was not
attempted directly; cited via Buchanan's 2023 survey reference [109], cross-checked
against a second, independent secondary source — UNVERIFIED via Crossref API but
bibliographically consistent across two sources). **Correction to the task brief:**
the task description cites "Williams 2002 (Env. & Planning B) spanning-tree/
ordered-pair formulation" — this venue attribution appears to be incorrect. Williams
published two 2002 papers, neither in Environment and Planning B: (i) the Networks
paper above (the actual spanning-tree extended formulation), and (ii) Justin C.
Williams (2002), "A Zero-One Programming Model for Contiguous Land Acquisition,"
*Geographical Analysis* 34(4):330-349, DOI 10.1111/j.1538-4632.2002.tb01093.x
(VERIFIED via Crossref: title/author/journal/year match). Williams DID publish in
Environment and Planning B, but in 2003 and on a different topic: "Convex Land
Acquisition with Zero-One Programming," *Environment and Planning B: Planning and
Design* (2003), DOI 10.1068/b12925 (found via Crossref query match; not the
spanning-tree paper). The spanning-tree formulation has documented ERRATA: Hamidreza
Validi and Austin Buchanan (2019), "A note on 'A linear-size zero-one programming
model for the minimum spanning tree problem in planar graphs,'" *Networks*
73(1):135-142 — corrects mistakes in the original Williams extended formulation.

**Summary:** A linear-size (O(n)) extended formulation for spanning trees
specifically in PLANAR graphs (exploits planarity's O(n) edge bound and a clever
dual/primal-planar-graph correspondence) — dramatically smaller than a naive
subtour-elimination or MTZ formulation. Buchanan's 2023 survey notes this can be used
as a modeling primitive to build a linear-size, provably-integral formulation for
partitioning a planar graph's vertices into k connected components — but Zhang,
Validi, Buchanan & Hicks (2024, see 1.6) find that once population-balance (or,
by direct analogy, any side-payment/value constraint) is added, the polytope's
integrality is DESTROYED and the model performs WORSE than the baseline Hess model.
This is a significant negative result for adapting a "pure" spanning-tree encoding
to a fair-division setting with per-side value totals as decision-relevant
quantities (directly analogous to this project's g_a, g_b gain totals).

**Formulation size, k=2:** O(n) variables and constraints (planar-graph spanning
tree is linear-size by construction) — asymptotically the SMALLEST of any
encoding surveyed here, when population/value constraints are absent.

**Exact in one solve vs lazy:** Single-shot, linear-size, and — for the pure
spanning-tree/partitioning problem with no side constraints — INTEGRAL (LP
relaxation = IP optimum), a rare and valuable property. This integrality is lost
once value-balance constraints are added (see above), which is exactly this
project's situation (g_a, g_b are value sums over each side).

**Guarantee:** Exact (when integral, the LP relaxation itself certifies optimality
with no branching needed at all); once value constraints destroy integrality, only
the ordinary MILP branch-and-bound guarantee remains.

**Computational evidence:** Zhang, Validi, Buchanan & Hicks (2024) test the
extended spanning-tree formulation against Hess on population-balanced political
districting and report it performs WORSE once balance constraints are added (see
1.6 for full citation and detail); no positive scale numbers reported for the
value-constrained case specifically.

**Failure-mode relevance:** Not a good fit for this project's Nash-welfare setting:
the g_a, g_b value totals are exactly the kind of side constraint shown to destroy
this formulation's chief advantage (integrality). Listed for completeness and to
flag a modeling dead end that a naive reading of "spanning-tree = smallest
encoding" might otherwise suggest is attractive.

**Open-source implementability:** Straightforward to implement as upfront linear
constraints in any MILP solver, but per above, not recommended once value totals
enter the objective/constraints.

---

### 1.6 Linear-size extended formulation, connected planar-graph k-partitioning

**Citation:** Jack Zhang, Hamidreza Validi, Austin Buchanan, Illya V. Hicks (2024),
"Linear-size formulations for connected planar graph partitioning and political
districting," *Optimization Letters* 18(1):19-31 (published online 2023-10-05).
DOI 10.1007/s11590-023-02070-0. VERIFIED (Crossref title/authors/journal match).

**Summary:** Builds directly on the Williams spanning-tree extended formulation
(1.5) to give an O(n)-variable, O(n)-constraint, PERFECT (integral) extended
formulation for partitioning a planar graph's n vertices into k connected
components — asymptotically the smallest exact encoding surveyed here for the
*pure* connectivity problem. Applied to political districting with contiguity and
population balance imposed as hard constraints and compactness optimized. As
already flagged in 1.5, the paper's own headline negative finding is that once
population balance is added as a hard constraint, the formulation's integrality
is destroyed and it underperforms the Hess baseline — an important caveat for any
attempt to reuse this encoding when this project's g_a/g_b value totals play a
role structurally analogous to population balance.

**Formulation size, k=2:** O(n) variables, O(n) constraints, O(n) nonzeros for the
pure connectivity problem (this is the paper's headline efficiency claim);
size/tightness degrade once value/balance constraints are layered in.

**Exact in one solve vs lazy:** Single-shot MILP; no lazy separation needed for the
pure partitioning problem.

**Guarantee:** Integral (LP-relaxation-exact) for pure connected k-partitioning;
ordinary MILP guarantee (not integral) once value constraints are added.

**Computational evidence:** Comparative testing against Hess on population-balanced
US districting instances; reported to perform worse than Hess once balance is
imposed (per Buchanan's 2023 survey summary of this same paper, listed there as
reference [113]/[the accepted version]). No specific instance-size/solve-time table
was located in the material fetched for this survey; flagged in "Could not verify"
below.

**Failure-mode relevance:** Same caveat as 1.5 — likely NOT a good fit given this
project's per-side value totals (g_a, g_b) are structurally the same kind of
"balance" constraint shown to break this formulation's advantage.

**Open-source implementability:** Reference implementation on GitHub
(github.com/JackDaihanZhang/Linear-size-formulations-for-connected-planar-graph-
partitioning-and-political-districting) — not inspected for solver dependencies
in this pass; likely Gurobi-based given the surrounding literature's convention
(the sibling Validi-Buchanan-Lykhovyd repo, github.com/zhelih/districting, is
explicitly Gurobi-based, tested with Gurobi 9.1.2).

---

### 1.7 Connectivity cutset constraints for forest harvest scheduling

**Citation:** Rodolfo Carvajal, Miguel Constantino, Marcos Goycoolea, Juan Pablo
Vielma, Andrés Weintraub (2013), "Imposing Connectivity Constraints in Forest
Planning Models," *Operations Research* 61(4):824-836. DOI 10.1287/opre.2013.1183.
VERIFIED (Crossref title/authors/journal/year match). Won the 2015 INFORMS Section
on Energy, Natural Resources & the Environment Best Publication Award in Natural
Resources.

**Summary:** Forest harvest scheduling requires selecting a connected subset of
harvest units (e.g., for wildlife-corridor or habitat constraints) subject to
area/adjacency restrictions, over multiple time periods (dynamic) and possibly
without a fixed root (unrooted connectivity — i.e., "is this subset connected"
rather than "is this subset connected to a specific known root", which is a HARDER
variant than the SHIR/CUT setting where roots can be fixed in advance). The paper
formulates connectivity via cutset-style constraints and solves via branch-and-cut
with lazy constraint generation (constraint-generation procedure that separates
violated connectivity inequalities at integer incumbents, closely paralleling
CUT/1.2, but for a "select connected SUBSET" problem rather than a "partition into
two connected complementary halves" problem — technically different because there
is no complementary side that must ALSO be connected).

**Formulation size:** Not resolved to closed-form n/m expressions in the material
retrieved for this survey (see "Could not verify" section); the paper reports
handling forest-planning instances 2-3x larger than prior studies via this
branch-and-cut lazy approach.

**Exact in one solve vs lazy:** Lazy branch-and-cut (constraint-generation/
callback-based), NOT single-shot.

**Guarantee:** Exact — branch-and-cut with complete lazy separation is a certified
global-optimum method (same guarantee class as CUT/LCUT in 1.2).

**Computational evidence:** Root-node LP bounds obtained in under 21 minutes across
tested instances, "often much faster"; substantial variability in difficulty across
instance/variant combinations — rooted variants easier than unrooted, static easier
than dynamic (multi-period). Scales to forest-planning instances 2-3x larger than
prior connectivity-constrained forest models.

**Failure-mode relevance:** (b) Directly relevant as another data point that lazy
branch-and-cut with strong root-node bounds can push scale substantially past
naive/dense encodings — but the "unrooted, harder" framing is a caution: the current
project's problem is actually the EASIER "rooted" case (both a-side and b-side roots
are fixed per `districting.py`'s existing architecture per HANDOFF.md), so this
paper's harder unrooted results are a pessimistic bound, and rooted performance
should be materially better, consistent with SHIR/CUT's own root-fixing practice.
(a)/(c) not directly tested (forest planning, not fair-division/value-concentration
context) but the "rooted is easier" and "static (single time-slice) is easier"
findings are qualitatively consistent with mechanism (a): pre-fixing/pre-resolving
known-good structure before the hard MILP reduces difficulty, supporting the
project's own proposed component-quotient preprocessing fix.

**Open-source implementability:** Needs a lazy-constraint-callback-capable solver
(the original paper used a commercial solver with callbacks — likely CPLEX/Gurobi
based on the era and group); portable in spirit to python-mip+CBC (`lazy_constrs`)
or pyscipopt. Not implementable as a single upfront `scipy.optimize.milp` call
without converting to a re-solve loop (which loses the warm-start benefit that likely
explains much of its speed).

---

### 1.8 Connected-subgraph / prize-collecting Steiner-tree formulations (general graph theory, non-districting)

**Citations:**
- Eduardo Álvarez-Miranda, Ivana Ljubić, Petra Mutzel (2013), "The Maximum Weight
  Connected Subgraph Problem," in *Facets of Combinatorial Optimization: Festschrift
  for Martin Grötschel*, Springer, pp. 245-270. DOI 10.1007/978-3-642-38189-8_11.
  VERIFIED (Crossref title/authors/container match).
- Matteo Fischetti, Markus Leitner, Ivana Ljubić, Martin Luipersbeck, Michele Monaci,
  Max Resch, Domenico Salvagnin, Markus Sinnl (2017), "Thinning out Steiner trees: a
  node-based model for uniform edge costs," *Mathematical Programming Computation*
  9(2):203-229. (Cited via Buchanan's 2023 survey reference [48]; DOI not
  independently re-verified in this pass but bibliographic details are internally
  consistent — treat as UNVERIFIED pending direct Crossref check.)

**Summary:** These formulate selecting a SINGLE maximum-weight connected subgraph
(not a 2-way partition into two complementary connected halves) via node-based cut/
separator formulations, closely related in spirit to Validi et al.'s CUT/LCUT
(1.2) — both rely on separating violated a,b-vertex-separator inequalities lazily.
Álvarez-Miranda, Ljubić & Mutzel's node-based formulation (built on node-separator
inequalities, no edge/flow variables at all) is reported to outperform prior
edge/flow-based formulations in running time and — notably for this project's
failure mode (c) — in STABILITY with respect to variation in node weights, i.e.,
value concentration/heterogeneity in node weights was explicitly identified and
tested as a robustness axis in this literature, unlike in the districting papers
above.

**Formulation size:** Node-variable-only (no per-edge or per-commodity flow
variables), separator inequalities added lazily — same general profile as CUT/LCUT:
small base model, exponential-but-lazily-separated cut family.

**Exact in one solve vs lazy:** Lazy branch-and-cut (separation of violated node
separators at each incumbent).

**Guarantee:** Exact (branch-and-cut to optimality with SCIP-Jack and similar
solvers is the state of the art for this problem class, per the "Solving Steiner
trees: Recent advances, challenges, and perspectives" survey by Ljubić et al. 2021 —
not independently verified here but consistent with search results).

**Computational evidence:** Not independently retrieved in this pass (see "Could
not verify"); the stability-under-node-weight-variation claim is qualitatively the
single most directly relevant finding in this entire survey to failure mode (c),
since it is the only source found that explicitly frames node-weight
heterogeneity as a formulation-robustness axis rather than treating all weights as
homogeneous/uniform.

**Failure-mode relevance:** (c) Value concentration — the most directly on-point
literature evidence for this specific failure mode, even though the underlying
problem (single connected subgraph, not 2-way partition) differs from this
project's. Suggests that node-based, separator-driven formulations (i.e., CUT/LCUT-
family, NOT flow-based SHIR/MCF) may be inherently more robust to heavy-tailed unit
values, because they do not require flow variables whose magnitudes/big-M
coefficients scale with the heaviest-tailed values.

**Open-source implementability:** SCIP-Jack (open source, built on SCIP/pyscipopt)
is the reference implementation for this problem family and directly supports the
node-separator, lazy branch-and-cut approach; a good template to study even though
it targets subgraph selection rather than 2-way partitioning.

---

### 1.9 Cutting-plane / lazy contiguity for spatial aggregation (map generalization)

**Citation:** Johannes Oehrlein, Jan-Henrik Haunert (2017), "A cutting-plane method
for contiguity-constrained spatial aggregation," *Journal of Spatial Information
Science* 2017(15):89-120. DOI 10.5311/josis.2017.15.379. VERIFIED (Crossref title/
authors/journal/year match).

**Summary:** Aggregates elements of a planar partition (e.g., cartographic
generalization / choropleth-map region-building) into larger regions that must be
size-thresholded, homogeneous, contiguous, and compact, via an ILP solved with a
lazy cutting-plane method: contiguity is enforced by generating violated
connectivity cuts only as needed rather than upfront, i.e., structurally the same
family as CUT/1.2 and the recursive cycle-breaking of TreePRM/1.3, applied to a
different downstream objective (aggregation/generalization rather than districting
or fair division).

**Formulation size / computational evidence:** Not resolved with confidence in this
pass — automated extraction of the PDF's tables and specific instance-size/solve-
time numbers was unsuccessful (the tool available for this survey could not
reliably parse the PDF's numeric tables); the paper is confirmed (via its own
digital-commons landing page and abstract) to test aggregation instances and to use
a cutting-plane/lazy approach, and downstream secondary sources describe the
approach as CPLEX-based with global-optimality guarantees, but exact n and solve-
time numbers should be treated as UNCONFIRMED pending a direct re-read.

**Guarantee:** Exact — cutting-plane/branch-and-cut methods that generate all
necessary connectivity cuts before terminating give a certified optimum.

**Failure-mode relevance:** Same general family as 1.2 — most relevant to (b) via
the lazy-cut mechanism, but without confirmed instance-size evidence in this pass,
treat as a secondary/corroborating source rather than primary computational
evidence.

**Open-source implementability:** Same profile as CUT/1.2 — needs a lazy-constraint-
capable solver for a faithful re-implementation, though the current re-solve-loop
architecture already approximates this.

---

## 2. Ranked shortlist for THIS problem (k=2, 400-800 ZCTAs, sparse active + zero-
value glue, currently HiGHS re-solve loop, three known failure mechanisms)

1. **CUT/LCUT separator inequalities (Validi, Buchanan & Lykhovyd 2022 OR, DOI
   10.1287/opre.2021.2141), migrated onto a true lazy-callback solver** —
   Rationale: this is the only formulation in this survey with *direct* published
   evidence of scaling to 1,500+ vertices to proven optimality, it directly targets
   failure mode (b), and it is structurally the closest match to
   `districting.py`'s existing separator-cut architecture — the actionable change
   is swapping the re-solve-from-scratch HiGHS loop for python-mip+CBC or pyscipopt
   with a genuine lazy-constraint callback (warm starts + LCUT's length-U
   strengthening), not a wholesale redesign.

2. **Node-based separator/connected-subgraph formulations (Álvarez-Miranda, Ljubić
   & Mutzel 2013, DOI 10.1007/978-3-642-38189-8_11) as a template for robustness
   under (c)** — Rationale: the only source in this survey explicitly identifying
   node-weight heterogeneity/stability as a formulation-design axis; worth mining
   SCIP-Jack's implementation for how it manages numerically heavy-tailed node
   weights in the branch-and-cut, since this maps directly onto failure mode (c).

3. **Shirabe flow (SHIR, DOI 10.1111/j.1538-4632.2005.00605.x /
   10.1068/b34104) as the single-shot fallback / sanity baseline** — Rationale:
   simplest to implement correctly (no callback machinery required at all — pure
   upfront MILP), gives a "known good, if slow" baseline to validate any new
   lazy-cut implementation against on small-to-medium instances, and with roots
   already fixed per side (per HANDOFF.md), the flow-variable count collapses to
   O(n) per side rather than O(n^2) — cheap to try first.

4. **Carvajal, Constantino, Goycoolea, Vielma & Weintraub (2013) lazy branch-and-
   cut connectivity constraints (DOI 10.1287/opre.2013.1183), specifically their
   documented rooted-vs-unrooted and static-vs-dynamic difficulty gradient** —
   Rationale: this problem's rooted, static (single time-period) setting is
   explicitly the EASIEST case in their own difficulty ranking, giving qualitative
   confidence that a properly-rooted lazy branch-and-cut (as in item 1) should
   scale comfortably past 400-800 units; also a source of concrete lazy-callback
   engineering practice (root-node LP bound quality, warm-starting) to borrow.

5. **Duque, Church & Middleton (2011) three-way comparison (SHIR/order/tree, DOI
   10.1111/j.1538-4632.2010.00810.x) as a cautionary benchmark, NOT a
   recommendation** — Rationale: not proposed for adoption, but its finding that
   even Shirabe-style flow encodings fail to reach proven optimality by n=25-49 on
   a generic commercial solver without root-fixing/acceleration is the strongest
   available warning that "switch encoding families" alone, absent solver-level
   fixes (warm starts, root-fixing, symmetry-breaking), will not by itself clear
   the scale wall — reinforcing that the highest-leverage actionable fix is solver/
   architecture (item 1's callback migration), not formulation choice per se.

**Explicitly NOT recommended:** the Williams/Zhang-Validi-Buchanan-Hicks linear-size
spanning-tree extended formulations (1.5, 1.6) — despite being asymptotically the
smallest exact encodings surveyed, both have a documented, specific failure mode
(integrality destroyed, performance worse than Hess baseline) precisely when
value/balance constraints are added, and this project's g_a/g_b Nash-welfare gains
are exactly this kind of constraint.

---

## 3. Could not verify / open questions

- **Formulation size / instance-size / solve-time numbers for Oehrlein & Haunert
  (2017)** — DOI and venue verified, but the automated PDF extraction available in
  this research pass could not reliably read the paper's numeric tables (multiple
  attempts returned garbled/binary content or generic non-quantitative summaries).
  A follow-up pass should fetch the JOSIS HTML/full-text view directly (rather than
  the PDF) or use a dedicated PDF-table extractor.

- **Precise variable/constraint counts for MCF (multi-commodity flow) and LCUT
  (length-U separator) in Validi, Buchanan & Lykhovyd (2022)** — the paper's own
  landing-page/abstract and secondary write-ups confirm the four-formulation
  taxonomy (SHIR, CUT, MCF, LCUT) and that MCF/SHIR use a "bidirected" graph
  representation, and that LCUT dominates the other three in LP-relaxation strength,
  but exact closed-form variable/constraint counts (as a function of n, m for
  general k, specialized to k=2) were not extracted with full confidence from the
  sources reached in this pass — the NSF PAR and Optimization Online mirrors of the
  paper returned as corrupted/unparseable binary content to the available PDF-
  reading tool. A follow-up should read the archived arXiv or Optimization Online
  PDF directly via a dedicated PDF text extractor, or consult the paper's
  companion GitHub repo (github.com/zhelih/districting) source code/README for the
  MCF and LCUT constraint definitions.

- **Formulation size and closed-form n/m expressions for Carvajal, Constantino,
  Goycoolea, Vielma & Weintraub (2013)** — the branch-and-cut architecture,
  root-node-LP-bound timing (<21 min), and rooted/unrooted, static/dynamic
  difficulty ranking are confirmed via secondary summaries, but exact variable/
  constraint-count formulas and specific instance sizes (number of harvest units)
  were not extracted with confidence; the DSpace/MIT and researchgate mirrors were
  not directly fetched as full text in this pass.

- **Williams (2002) Networks DOI** — cited via two independent secondary sources
  (Buchanan's 2023 survey reference list, cross-referenced against the Networks
  volume/issue/page convention used elsewhere) but not independently confirmed
  against the Crossref API directly in this pass; flag as UNVERIFIED and re-check
  before citing in any downstream document as a "VERIFIED" source. The companion
  Geographical Analysis land-acquisition paper (same first author, same year) IS
  independently Crossref-verified.

- **Fischetti, Leitner, Ljubić et al. (2017) "Thinning out Steiner trees" DOI** —
  cited only via Buchanan's 2023 survey reference list; not independently checked
  against Crossref in this pass.

- **Cova & Church (2000) DOI** — the ordered-area-assignment origin paper cited by
  Duque, Church & Middleton (2011); appears consistently across two independent
  bibliographies (Buchanan 2023 survey and the p-Regions paper's own reference
  list) but its DOI was not independently verified against Crossref in this pass.

- **No source found that directly tests any contiguity encoding against BOTH heavy-
  tailed node/unit values AND large scale (400-800 units) simultaneously** — the
  Álvarez-Miranda/Ljubić/Mutzel node-weight-stability finding (1.8) is the closest
  proxy found, but it is for a different underlying problem (single connected
  subgraph selection, not 2-way connected bipartition) and was not confirmed with
  specific quantitative stability numbers in this pass — this remains a genuine gap
  in the literature as searched, and the project's own C9 battery case may be the
  most direct evidence available on this specific interaction.

- **The 2-district (k=2) "connected bipartition" special case is not treated as a
  distinct named problem class anywhere found in this survey** — every source
  treats k=2 as a trivial special case of general-k districting/p-regions/
  connectivity, with no dedicated complexity or algorithmic results exploiting the
  fact that the complement of a connected k=2 district is also constrained to be
  connected (as opposed to k>=3 where only individual districts, not their unions,
  need be connected). This may be worth flagging as a genuine research gap: the
  "both S and complement connected" structure (sometimes called 2-connected
  graph partition or connected graph bisection in other literatures) may admit
  tighter formulations than a naive k=2 instantiation of general-k machinery, but
  no such specialized result was located in this pass.
