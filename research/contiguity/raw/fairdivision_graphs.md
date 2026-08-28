# Fair division of a graph with connected bundles — theory for the 2-agent connected-MNW setting

Scope: territory division of ZCTAs (vertices of a connected Rook-adjacency planar graph) between
TWO wholesalers, additive positively-correlated valuations, disagreement point d=(0,0), rule =
maximum Nash welfare (MNW), hard requirement that BOTH bundles be connected. This note surveys
what the "fair division of a graph" literature says about exactly this setting.

All DOIs below were checked against `https://api.crossref.org/works/<DOI>` and titles/authors/years
confirmed to match; arXiv IDs were checked against `https://export.arxiv.org/api/query?id_list=<id>`.
Anything not independently confirmed this way is flagged UNVERIFIED.

---

## 1. Papers, with theorem statements bearing on the 2-agent connected case

### Bouveret, Cechlárová, Elkind, Igarashi & Peters (2017), "Fair Division of a Graph" — IJCAI 2017, pp.135–141. DOI 10.24963/ijcai.2017/20. **VERIFIED**

Founding paper of the model: items are vertices of a graph G, each agent's bundle must induce a
connected subgraph, additive utilities. Introduces the graph-restricted maximin share (G-MMS,
called "MMS" in the paper) as the natural analogue of MMS under connectivity, and studies
proportionality, envy-freeness and MMS. Key results: an MMS allocation always exists and is
computable in polynomial time when G is a tree (including paths and stars), but need not exist when
G is a cycle. Deciding whether a connected proportional or envy-free allocation exists is NP-hard,
even when G is a path. The star graph is used as the canonical example where connectivity bites
hardest (n−1 agents are forced into singleton leaves).

**Bearing on this problem:** establishes the baseline vocabulary (G-MMS) and the first hardness
result (NP-hardness of connected EF/PROP on paths) that all later papers, including ours, build on.
Rook-adjacency ZCTA graphs are planar and typically far from tree-like, so the tree-only existence
guarantee for MMS does not transfer to our setting.

### Bilò, Caragiannis, Flammini, Igarashi, Monaco, Peters, Vinci & Zwicker — ITCS 2019 (arXiv:1808.09406, 2018) / *Games and Economic Behavior* 131 (2022), DOI 10.1016/j.geb.2021.11.006. **VERIFIED**

The paper closest to an exact answer for the 2-agent case. Main results (their Table 1, restated for
n=2): a connected **EF1** allocation is *guaranteed to exist for n = 2 agents on any traceable graph*
(any graph with a Hamiltonian path — in particular every path and every 2-connected planar block
sequence), via a **discrete cut-and-choose protocol** (their Definition 3.1/Proposition 3.2): one
agent identifies a "lumpy tie" vertex v_j (the first vertex at which both the prefix-through-v_j and
the suffix-through-v_j are weakly preferred to the complementary piece), the other agent picks
whichever side (prefix or suffix) she prefers, and the first agent keeps the rest including v_j. This
runs in **O(m)** and was independently found to run in **O(log m)** query complexity by Oh, Procaccia
& Suksompong (2019) — cited inside the paper, UNVERIFIED as a standalone citation here.

**Theorem 3.10 (their full characterization for n=2):** for a *general* graph G (not just a path), the
following are equivalent: (1) G admits a bipolar numbering (an st-numbering: an ordering v_1,…,v_m
such that every prefix and suffix is connected); (2) G guarantees EF1 for 2 agents under arbitrary
monotone valuations; (3) G guarantees EF1 for 2 agents even restricted to identical, additive, binary
valuations; (4) G contains no "trident" (a vertex whose removal splits G into ≥3 components, or a
block adjacent to three cut vertices); (5) the block-tree (biconnected-component tree) of G is a
path. **A Rook-adjacency grid graph (our setting) is 2-connected/biconnected for any simply-connected
lattice region, hence has a single block and trivially satisfies condition (5)** — so a connected EF1
allocation is *guaranteed to exist for our two wholesalers on the full ZCTA graph* (not merely on a
component with special structure), and can be computed by their O(m)-time cut-and-choose protocol.
This guarantee is for the *whole* zip graph as one biconnected piece; once we restrict to the induced
subgraph on `zips_for_pair`, that subgraph might not remain 2-connected (e.g., after removing zips
belonging to other reps), so the block-tree-is-a-path condition should be checked on the actual
census component, not assumed.

The paper also proves that the discrete cut-and-choose EF1 allocation is *also guaranteed to give
each agent ≥ her MMS* under the same conditions (their Theorem A.3/Appendix A.1) — i.e., for two
agents on a graph admitting a bipolar numbering, cut-and-choose is simultaneously EF1 and G-MMS.

**Bearing on this problem:** gives an unconditional, cheap, certified-EF1 (and MMS) fallback/warm
start for exactly our two-agent case whenever the disputed component is biconnected — which subsumes
all pairwise ZCTA components without articulation-point pathologies. It does **not** claim Pareto
optimality or any Nash-welfare property for the returned allocation.

### Suksompong (2019), "Fairly Allocating Contiguous Blocks of Indivisible Items" — *Discrete Applied Mathematics* 260:227–236 (SAGT 2017 preliminary version), DOI 10.1016/j.dam.2019.01.036; arXiv:1707.00345. **VERIFIED**

Restricted to G = path, but gives the sharpest quantitative bounds for exactly n=2. Defines additive
ε-approximations of proportionality/envy-freeness/equitability. For **n = 2 agents specifically**:

- **Theorem 4:** a contiguous allocation exists with envy at most `u_i,max` for each agent (a
  u_max-envy-free allocation) — this factor is tight (cannot be improved even without contiguity: his
  Example 1 with n=2 forces envy arbitrarily close to u_max).
- **Theorem 2 / Theorem 3** (any n, hence n=2): a contiguous u_max-equitable allocation exists for any
  fixed left-to-right ordering of the agents, and one can additionally be chosen with egalitarian
  welfare equal to the best achievable egalitarian welfare over all contiguous allocations.
- **Price of fairness table (his Table 1), n = 2 rows:** utilitarian price of equitability = 3/2
  exactly (tight); egalitarian price of equitability = 1 (i.e. for two agents, maximizing egalitarian
  welfare among equitable allocations costs nothing extra); utilitarian price of proportionality = n
  − 1 + 1/n = 3/2 at n=2; egalitarian price of proportionality = 1 for all n.

**Bearing on this problem:** the u_max-envy-free / u_max-equitable constructions are usable
certified fallbacks with an explicit, small, additive loss bound (bounded by the single largest
per-zip value gap between the two reps) — tighter in spirit than an MMS-percentage bound, since it
is stated in absolute utility units and independent of instance size.

### Igarashi & Peters (2019), "Pareto-Optimal Allocation of Indivisible Goods with Connectivity Constraints" — AAAI 2019, pp.2045–2052, DOI 10.1609/aaai.v33i01.33012045; full arXiv:1811.04872. **VERIFIED**

This is the key negative result for combining efficiency with fairness under connectivity, and the
paper that our project's "Why Nash" writeup will need to cite carefully for what it does/does not say
about n=2.

- **Positive for any n (hence n=2):** a Pareto-optimal connected allocation can be found in polynomial
  time when G is a path (their recursive left-to-right algorithm, Theorem 3.1) or a star (bipartite
  matching reduction, Theorem 3.2). Both hold for *any number of agents*, not just n=2.
- **Hardness (Theorems 3.3–3.6):** finding *any* Pareto-optimal connected allocation is NP-hard
  (Turing-hardness) when G is a forest/tree, even with binary additive valuations, even at bounded
  pathwidth/diameter/degree-3 trees. Crucially, **this hardness is proved via a reduction from
  Exact-3-Cover that uses many agents** (one per element/set of the X3C instance) — it is *not* a
  2-agent hardness result. The paper does not claim, and its constructions do not establish, that
  finding a Pareto-optimal connected allocation is hard for exactly 2 agents; indeed for a path or
  star with 2 agents, Theorems 3.1/3.2 already give a polynomial algorithm regardless of how many
  agents are plugged in, so **PO alone is polynomial for 2 agents on paths/stars**, and its complexity
  on a general (non-tree, non-path/star) 2-agent graph is not resolved either way in this paper.
- **PO+EF1 (Table 1, Theorem 4.3):** on a path, there exist binary-additive instances (their Examples
  4.1 and 4.2) with **no** connected allocation that is simultaneously Pareto-optimal and EF1, and
  deciding whether one exists is NP-hard. **Both counterexamples use ≥3 agents** (Example 4.1 has 4
  agents; Example 4.2 has 3). The paper never exhibits a 2-agent instance where PO+EF1 is
  infeasible, and their Theorem 4.3 hardness reduction likewise uses an unbounded number of agents
  (built from an X3C instance). Whether a connected, Pareto-optimal, EF1 allocation always exists —
  and can be found efficiently — for exactly n=2 agents on a path (or more generally on graphs
  admitting a bipolar numbering) is therefore **not settled by this paper** and is flagged below as an
  open question directly relevant to our setting.
- Also proves (Prop. 4.4) that for a path with *identical* additive valuations, a connected PO+EF1
  allocation exists and is efficiently computable for any n — not directly ours since our two reps'
  valuations are correlated but not identical.
- States as a general remark (not a new theorem) that MNW-with-connectivity is NP-hard to compute
  whenever finding *any* PO allocation is NP-hard, since Nash-welfare maximizers are always
  Pareto-optimal — this transfers the tree/forest PO-hardness to Nash-welfare-with-connectivity
  hardness on trees, but again via constructions using many agents, not n=2.

**Bearing on this problem:** on a Rook-adjacency planar (non-tree) graph, neither the tree/path/star
positive nor negative results directly apply; more importantly, the specific
"MNW-with-connectivity is EF1-incompatible" folklore claim (repeated in Bilò et al. 2022's concluding
remarks, citing this paper) rests on constructions that need 3+ agents — it is **not** established
for exactly n=2, which is our case. This is a genuine gap worth flagging rather than assuming the
n≥3 counterexamples transfer down to n=2.

### Lonc & Truszczyński (2018/2020), "Maximin Share Allocations on Cycles" — IJCAI 2018, pp.410–416, DOI 10.24963/ijcai.2018/57; journal version *JAIR* 69:613–655 (2020), DOI 10.1613/jair.1.11702. **VERIFIED**

Studies G-MMS specifically on cycles (the next-simplest graph after trees/paths, and the one most
analogous to a "ring" of ZCTAs). Shows G-MMS allocations need not exist on a cycle even though they
always exist on trees (extending Bouveret et al. 2017's negative example), characterizes when they do
exist, and gives algorithms. Also contains (cited by Bei-Igarashi-Lu-Suksompong below) the fact that
for **n = 2 agents on an arbitrary graph, a G-MMS-achieving connected bipartition always exists**
(their Corollary 2, used as a black-box fact in the Price-of-Connectivity paper) — i.e., the n=2
existence guarantee for MMS holds unconditionally on *any* connected graph, not just paths/trees;
only the *degree* of approximation to the unconstrained MMS (see next entry) depends on graph
topology.

**Bearing on this problem:** confirms that 2-agent G-MMS existence is graph-independent; the open
question is only the *quality* (price of connectivity) of that guarantee, addressed next.

### Bei, Igarashi, Lu & Suksompong, "The Price of Connectivity in Fair Division" — AAAI 2021, pp.5151–5158, DOI 10.1609/aaai.v35i6.16651; *SIAM J. Discrete Math.* 36(2):1156–1186 (2022), DOI 10.1137/20m1388310. **VERIFIED** (full text read directly)

Defines Price of Connectivity, PoC(G,n) = sup_u MMS(u,n)/G-MMS(G,n,u) — the worst-case multiplicative
gap between the unconstrained MMS and the graph-restricted MMS. This is the closest thing in the
literature to a formal "price of contiguity" bound, though stated for MMS, not Nash welfare. For
**n = 2 agents** (their §3, summarized in their Table 1):

| Graph class (2 agents) | PoC(G,2) | Meaning |
|---|---|---|
| Vertex connectivity 1 (incl. all trees) | = k (max components after deleting the cut vertex) | ≥2, can be large for star-like cut structure |
| Vertex connectivity exactly 2 | = 4/3 exactly (Corollary 3.6) | |
| Vertex connectivity ≥ 3 | ≤ 4/3 (Theorem 3.4), and this is tight even at connectivity 5 (a Meszáros graph, Corollary 3.7) | conjectured (Conjecture 3.10, open) to be governed exactly by "(2,k)-linkedness" |

Since PoC(G,2)·G-MMS(G,2,u) ≥ MMS(2,u) and this is tight, and since for n=2 the connected allocation
achieving 1/PoC of MMS is polynomial-time computable via a spanning-tree-shrinking argument
(Theorem 3.1's proof) for connectivity-1 graphs, and a **3/4-approximation is achievable in
polynomial time for biconnected graphs** (Theorem 3.4's constructive strengthening, noted in-paper
right after the proof) — **a Rook-adjacency grid region that stays 2-connected (no articulation
points) guarantees each of our two wholesalers at least 3/4 of her unconstrained (non-contiguous)
MMS, via a polynomial algorithm, with 4/3 the worst-case gap and this tight.** If the disputed
component has a cut vertex (articulation point — e.g. a chokepoint ZCTA connecting two blobs), the
guarantee degrades to only `1/k` where k is the largest number of pieces created by deleting that cut
vertex — this is exactly analogous to Trap 11 mechanism #1 (pre-existing disconnection) in the
project's own findings, and confirms formally that a low-degree cut vertex is the worst topological
case for the 2-agent guarantee, not merely an empirical MINLP-convergence nuisance.

**Bearing on this problem:** gives a *quantitative, closed-form, graph-topology-dependent* bound on
how much connectivity can cost a 2-agent fair division under MMS, and it is the closest published
proxy we have to a theoretical price-of-connectivity number for our setting (MNW-specific bounds do
not exist — see "Could not verify" below). It also formally explains *why* articulation points
(cut vertices) are the structurally worst case, matching the empirical Trap-11 mechanism.

### Deligkas, Eiben, Ganian, Hamm & Ordyniak (2021), "The Parameterized Complexity of Connected Fair Division" — IJCAI 2021, pp.139–145, DOI 10.24963/ijcai.2021/20. **VERIFIED** (full text read directly)

Gives the sharpest complexity picture for small numbers of agents. Central negative fact directly on
point: **Proposition 3: for every fairness notion φ ∈ {PROP, EF, EF1, EFX}, φ-CFD is NP-hard even
when restricted to instances with exactly |A| = 2 agents and *identical* valuations u₁ = u₂ = 1**
(reduction from Equitable Connected Partition — i.e. even just splitting an unweighted graph into two
connected pieces of prescribed sizes is NP-hard in general). This shows that **restricting to two
agents alone does not make connected fair division tractable**; tractability additionally requires
restricting the graph (their Theorem 4/6: XP-tractable parameterized by clique-width + #agents, or by
treewidth + #agent-types) — ZCTA Rook grids have unbounded treewidth and unbounded clique-width in
general (grid graphs are a standard witness that both parameters grow with instance size), so **these
XP algorithms do not give a practical speed-up for our scale**, consistent with the project's Trap 11
mechanism #2 (pure MILP scale failure) rather than contradicting it. On the positive side, Theorem 4
(XP in clique-width + #agents, i.e. FPT when n is fixed at 2 and clique-width is bounded) is exactly
our case if a two-agent census component happens to have small clique-width (e.g., near-planar with
few "layers") — worth checking empirically on the C1–C9 battery components as an alternative exact
solver when the MILP times out.

**Bearing on this problem:** the "two agents" specialization in our model does not, by itself,
rescue tractability — confirms the project's finding that scale (not agent count) is the dominant
driver of MILP failure, and gives a precise complexity-theoretic reason (Proposition 3's
n=2-identical-valuations hardness) rather than treating it as an empirical curiosity.

### Bouveret, Cechlárová & Lesca (2019), "Chore Division on a Graph" — *Autonomous Agents and Multi-Agent Systems* 33(5):540–563, DOI 10.1007/s10458-019-09415-z. **VERIFIED**

Extends the graph fair-division model to chores (disutility items). Central finding: goods and chores
settings are *not* symmetric under a naive utility-sign flip — a chores instance cannot be solved by
transforming it into the "mirror" goods instance and negating. Not directly load-bearing for our
territory problem (M_z/A_z/B_z are goods, not chores), but relevant if a future extension treats
excess/undesirable ZCTAs (e.g., high cost-to-serve, low headroom) as chores rather than
low-value goods.

**Bearing on this problem:** low direct relevance today; flagged for the "capacity constraints"/chore
modeling item in HANDOFF.md's open list if that direction is pursued.

### Igarashi (2023), "How to Cut a Discrete Cake Fairly" — AAAI 2023, pp.5681–5688, DOI 10.1609/aaai.v37i5.25705; arXiv:2209.01348. **VERIFIED**

Studies discrete "cake" division on a path where a cut may split a single item between two agents
(a hybrid discrete/continuous relaxation), improving on the pure-EF1 path results by allowing one
item to be fractionally shared at each cut point. Not primarily about MNW-with-connectivity, but
relevant as the discrete analogue of the classical proportional/envy-free cake-cutting moving-knife
literature; establishes existence and efficient computation of connected envy-free "discrete cake"
allocations for any number of agents when at most one item per cut may be split. Because our ZCTAs
are genuinely indivisible (a single zip cannot be split between reps), this line is not directly
exploitable but is worth knowing as the boundary case that goes away once true indivisibility is
required.

**Bearing on this problem:** low direct relevance (assumes one splittable item per cut, which our
model forbids); included because it was named in the assignment.

### Igarashi & Zwicker (2021 arXiv / 2023 journal), "Fair Division of Graphs and of Tangled Cakes" — *Mathematical Programming* Ser. A/B, DOI 10.1007/s10107-023-01945-5; arXiv:2102.08560. **VERIFIED**

Connects graph fair division to a generalized continuous "tangled cake" (a topological space built by
gluing intervals per a graph structure), linking EFk-fair division of discrete graphs to
envy-free division of the corresponding continuum tangle. Shows exactly six "stringable" tangles
guarantee envy-free connected division for any number of agents, and these correspond exactly to
Hamiltonian (traceable) graphs. Proposes a forbidden-minor-type conjecture, mentioned as still open
in Bilò et al. (2022)'s concluding remarks, for extending the n=2 bipolar-numbering characterization
to n≥3 agents.

**Bearing on this problem:** theoretically elegant bridge between our discrete grid setting and the
continuum literature (Warren 2025's Laguerre-tessellation result lives on that continuum side); the
n≥3 open conjecture is not our immediate concern since we are strictly bilateral, but the framework
is useful vocabulary for any future 3+-wholesaler leximin extension (HANDOFF.md's open item #3).

### Bei, Elkind, Segal-Halevi & Suksompong, "Dividing a Graphical Cake" — *SIAM J. Discrete Math.* 39(1):19–54 (2025), DOI 10.1137/22m1500502. **VERIFIED**

Generalizes graphical cake-cutting to arbitrary graphs (rather than a path/cycle), where the cake
itself (not just discrete items) is spread over the edges/vertices of a graph — e.g. dividing a road
network. Shows that unlike interval cake-cutting, common fairness notions (proportionality) are not
always achievable with connected pieces on a general graph — a continuum analogue of the
Bouveret-et-al. 2017 discrete hardness/impossibility results. UNVERIFIED beyond title/author/venue —
full theorem statements for n=2 were not retrieved in this pass (would require the paywalled SIAM
full text); flagged as an item to re-check if a continuum relaxation of the ZCTA problem is ever
pursued.

**Bearing on this problem:** secondary; establishes that "graph" (not just path/cycle) topology is an
active continuum research frontier too, paralleling the discrete literature above.

### Caragiannis, Kurokawa, Moulin, Procaccia, Shah & Wang (2019), "The Unreasonable Fairness of Maximum Nash Welfare" — *ACM Trans. Econ. Comput.* 7(3), DOI 10.1145/3355902. **VERIFIED** (already the project's cited baseline)

Unconstrained (no connectivity) baseline: MNW is Pareto-optimal and EF1, and (for d=(0,0) at least,
per our project's settled model) restores the axiomatic Nash-bargaining correspondence. Every paper
above that touches "MNW+connectivity" (Bilò et al. 2022's concluding remarks; Igarashi & Peters 2019)
cites this paper as the thing that is lost once connectivity is imposed for n≥3 — reiterating that
the n=2-specific status of that loss is the open question flagged above.

---

## 2. What theory guarantees for our setting (table)

| Property | Unconstrained MNW (Caragiannis et al. 2019) | MNW with hard connectivity (2 agents) | Source |
|---|---|---|---|
| Pareto-optimality | Yes, by construction | Yes if the MNW-maximizing connected allocation is found (still PO among connected allocations by definition); computing *any* connected PO allocation is polynomial on paths/stars, NP-hard on general trees via a many-agent reduction (status for exactly 2 agents on trees/general graphs: **open**) | Caragiannis et al. 2019; Igarashi & Peters 2019 |
| EF1 | Yes, always (theorem) | **Not established either way for n=2.** Known counterexamples to "connected MNW is EF1" all use ≥3 agents (Bilò et al. 2022 §8's remark, citing Igarashi & Peters 2019's Examples 4.1–4.2, which use 3–4 agents) | Igarashi & Peters 2019; Bilò et al. 2022 |
| *Some* connected EF1 allocation (not necessarily the MNW one) | n/a | **Yes, unconditionally**, for any graph whose block-tree is a path (in particular any biconnected/2-connected graph, e.g. an articulation-point-free grid region), via discrete cut-and-choose, O(m) time | Bilò et al. 2022, Thm 3.10 |
| G-MMS (connectivity-respecting maximin share) | n/a (MMS undefined without partition structure) | **Yes, unconditionally**, on any connected graph (Lonc & Truszczyński 2018, Cor. 2); quantitative gap to unconstrained MMS is exactly 4/3 on biconnected graphs (tight), ≥2 and up to k on graphs with a cut vertex of degree-k branching | Lonc & Truszczyński 2018/2020; Bei-Igarashi-Lu-Suksompong 2021/2022 |
| Connected proportional / EF / EF1 / EFX decision problem, 2 agents, general graph | n/a | **NP-hard**, even with identical valuations u₁=u₂=1 (Equitable-Connected-Partition reduction) | Deligkas et al. 2021, Prop. 3 |
| Price of connectivity for **Nash welfare** specifically (2 agents) | 1 (no loss) | **No published closed-form bound found** — all quantitative "price of connectivity" results in the literature are for MMS (Bei-Igarashi-Lu-Suksompong) or utilitarian/egalitarian welfare (Suksompong 2019, on paths only); nothing dedicated to Nash welfare with hard connectivity was located | — (open; see §4) |

---

## 3. Constructive procedures usable as fallback / warm start (with loss bounds)

1. **Discrete cut-and-choose (Bilò et al. 2022, Def. 3.1/Prop. 3.2, O(m) or O(log m) via Oh et al. 2019)**
   — applicable whenever the census component's block-tree is a path (guaranteed on any 2-connected
   subgraph, e.g. an articulation-point-free ZCTA blob). Output is EF1 *and* simultaneously achieves
   each agent's G-MMS (Theorem A.3). No welfare-optimality guarantee, but it is a certified,
   near-instant fallback whenever `solve_contiguous_nash` times out or fails to converge, and its
   "lumpy tie" vertex is a natural warm-start seed (bisection point) for the MINLP's branch-and-bound.

2. **u_max-envy-free / u_max-equitable path algorithms (Suksompong 2019, Thms 4, 2–3)** — for paths
   specifically (our grid graphs are not paths, but a Hamiltonian-path traversal of a 2-connected
   region reduces to this case), gives an *absolute* (not multiplicative) envy bound of one
   maximum-per-zip valuation gap. Useful as a sanity check: if the MINLP's contiguity cost exceeds
   `u_max` in absolute terms, something is likely mis-specified rather than merely "expensive."

3. **G-MMS 3/4-approximation on biconnected graphs (Bei-Igarashi-Lu-Suksompong 2021, remark after
   Thm 3.4)** — explicit polynomial-time algorithm guaranteeing each agent 3/4 of her *unconstrained*
   MMS whenever the graph has vertex-connectivity ≥2; degrades toward 1/k on graphs with a k-way cut
   vertex. This gives a topology-driven early-warning signal: computing the vertex connectivity /
   articulation points of each census component before invoking the MINLP would predict, in
   closed form, roughly how costly contiguity should be — directly testable against the battery's
   observed 0.03–5% welfare costs and would help separate "mechanism 1" (pre-existing disconnection)
   instances from genuinely hard ones ahead of time.

None of these three procedures target Nash welfare directly — they are EF1/MMS/egalitarian
fallbacks, not MNW approximations. No paper in this search proposed a certified constant-factor (or
any-factor) approximation algorithm for *connected Nash welfare* specifically with 2 agents; that
remains a genuine gap (see below).

---

## 4. Could not verify / open questions

- **No paper computing "price of connectivity" for Nash welfare (2 agents or otherwise) was found.**
  All quantitative price-of-connectivity results are for MMS (Bei-Igarashi-Lu-Suksompong) or
  utilitarian/egalitarian welfare on paths (Suksompong 2019, Aumann & Dombb for the divisible case).
  Given that our project's own empirical Nash-welfare contiguity cost is 0.03–5% (worse under heavy
  tails), and MMS's biconnected bound is a tight 4/3 (25% loss) in the worst case, it is *not*
  obviously the same order of magnitude — Nash welfare (being a geometric mean, hence more sensitive
  to the *product* of gains rather than either agent's minimum) could in principle have either a
  tighter or looser worst-case bound than MMS's 4/3; this needs its own derivation or a targeted
  literature search we did not have room for (Consensus/further arXiv search under
  "Nash social welfare price of connectivity" or "graphical Nash bargaining" would be the next step).

- **Whether PO+EF1 always exists for exactly n=2 agents on a path (or any bipolar-numbered graph) is
  not resolved by any paper found.** Igarashi & Peters (2019)'s only counterexamples use 3 or 4
  agents; Bilò et al. (2022) leave the general-graph EF1 characterization strictly to n=2 without
  discussing PO jointly. Because our production setting is exactly n=2, this is the single most
  actionable open theoretical question from this survey: if PO+EF1 (or PO+G-MMS, which is known to
  coexist for n=2 whenever cut-and-choose applies, per Theorem A.3 above) turn out to always coexist
  at n=2, that would be a meaningfully stronger and more citable theoretical anchor for the paper's
  "Why Nash" section than the current, more hedged connectivity-cost-is-empirically-small argument.

- **Complexity of computing the connected-MNW-maximizing allocation for exactly 2 agents on a
  general (non-tree, non-path/star) planar graph** is not directly stated by any source found. It
  is implied to be at least as hard as computing *any* PO allocation, which is polynomial on
  paths/stars and open/unclear for 2-agent general planar graphs (the only hardness proof needs many
  agents). This gap matters because it is exactly the computational question the project's own
  MILP-based `solve_contiguous_nash` is trying to answer empirically; a positive complexity result
  (even pseudo-polynomial, along the lines of the path/star cases) could in principle replace or
  validate the MILP for the 2-agent case specifically, as distinct from the harder n≥3 or
  general-graph regimes the parameterized-complexity papers focus on.

- **"Dividing a Graphical Cake" (Bei-Elkind-Segal-Halevi-Suksompong, SIAM DM 2025)** — bibliographic
  metadata (title/authors/venue/year) verified via CrossRef, but the paper's specific n=2 theorem
  statements were not retrieved (full text not fetched in this pass); flag for follow-up if a
  continuum relaxation is pursued.

- **The Aurenhammer–Hoffmann–Aronov (1998) / Hartmann–Schuhmacher (2020) optimal-transport /
  power-diagram results** confirm that in the *continuum*, an optimal-transport partition into
  prescribed-mass clusters always takes the form of a power diagram (Laguerre tessellation) — this is
  exactly the mechanism M. Warren (2025) uses to get *automatic* contiguity in the continuum Nash
  bargaining limit. **No paper found shows an analogous "automatic contiguity" result for the
  discrete grid problem** — i.e., there is no known discrete threshold/ratio rule on a Rook grid whose
  bare Nash-welfare-maximizing zip assignment is guaranteed connected without an explicit hard
  constraint. This is consistent with, and helps explain theoretically, why the project's battery
  needs a genuine contiguity MILP rather than being able to rely on a cheap post-hoc-connected
  threshold rule the way the continuum Laguerre-cell picture would suggest is possible.

- **M. Warren (2025), "Continuum Nash bargaining solutions"** — DOI 10.1007/s00030-025-01118-7,
  published in *Nonlinear Differential Equations and Applications (NoDEA)* 32, article 109 (2025).
  **VERIFIED** via CrossRef. The arXiv preprint is **arXiv:1712.07202** ("Continuum Nash Bargaining
  Solutions", submitted 19 Dec 2017), **VERIFIED** via the arXiv API — same title and single author
  (Micah Warren), an 8-year gap between preprint and journal publication. This should be added to
  `territory_bibliography.bib`, which currently has no entry for it per the project's own notes.
