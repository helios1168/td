# Territory division, fair allocation, and bargaining — annotated bibliography

Working bibliography for a post-merger sales-territory allocation model: dividing ZIP-level territory between two merging distribution forces. 32 entries in 7 sections. Every DOI was resolved against OpenAlex on 2026-08-27; author names, years, venues and titles come from those records rather than from recall, and none of the entries carries a retraction flag.

Each entry states what the paper establishes and why it bears on this problem. Two metadata cautions carried from the source records: OpenAlex lists the author of Nash's 1953 *Two-Person Cooperative Games* as "John C. Nash" (it is John F. Nash), and Binmore, Osborne & Rubinstein's *Noncooperative Models of Bargaining* resolves to a working-paper record typed as a preprint, though the canonical version is a Handbook chapter.

## How to use this file

Attach it to a Claude Project as knowledge, or paste it at the head of a chat. It is written so that a model reading it can cite these papers accurately without re-searching: the DOI links resolve, the author-year strings are correct, and the relevance notes say what each citation is *for*. Ask for "the citation for X" and the answer should come from this file. Anything **not** in here has not been verified — treat a citation that does not appear below as a claim requiring a fresh lookup.


## Sales territory design and alignment

**[Hess & Samuels 1971](https://doi.org/10.1287/mnsc.18.4.p41)** — Experiences with a Sales Districting Model: Criteria and Implementation. *Management Science*. Cited by 142.  
First published sales-districting model: equalise workload/potential over contiguous units, solved by a location-allocation heuristic.  
*Bearing on this problem:* The benchmark any territory-division paper is compared to. Establishes that balance-based districting is 50 years old, so novelty must lie elsewhere.

**[Lodish 1971](https://doi.org/10.1287/mnsc.18.4.p25)** — Callplan: An Interactive Salesman's Call Planning System. *Management Science*. Cited by 150.  
CALLPLAN: interactive optimisation of salesperson call frequency by account, with an estimated response function.  
*Bearing on this problem:* Origin of the concave-effort-response tradition; the companion argument to Skiera & Albers on why linear utility is contested.

**[Zoltners & Sinha 1983](https://doi.org/10.1287/mnsc.29.11.1237)** — Sales Territory Alignment: A Review and Model. *Management Science*. Cited by 180.  
Formalises territory alignment as an assignment problem over sub-units with a survey of criteria and a solvable model.  
*Bearing on this problem:* Canonical statement of the problem this work generalises. Cite when framing scope.

**[Skiera & Albers 1998](https://doi.org/10.1287/mksc.17.3.196)** — COSTA: Contribution Optimizing Sales Territory Alignment. *Marketing Science*. Cited by 88.  
Maximises total contribution using an estimated concave sales-response function per territory, rather than balancing surrogates.  
*Bearing on this problem:* The strongest challenge to a linear utility. A referee will ask why the response function is not estimated; this is the paper they have in mind.

**[Drexl & Haase 1999](https://doi.org/10.1287/mnsc.45.10.1307)** — Fast Approximation Methods for Sales Force Deployment. *Management Science*. Cited by 80.  
Fast approximation algorithms for joint territory design and effort allocation at realistic scale.  
*Bearing on this problem:* Precedent that the deployment problem needs heuristics at national scale; relevant to the lazy-callback scaling gap.

**[Zoltners & Lorimer 2000](https://doi.org/10.1080/08853134.2000.10754234)** — Sales Territory Alignment: An Overlooked Productivity Tool. *Journal of Personal Selling and Sales Management*. Cited by 40.  
Argues misalignment is a large and routinely ignored source of lost sales productivity.  
*Bearing on this problem:* Motivation and business framing; useful for a non-technical audience.

**[Zoltners & Sinha 2005](https://doi.org/10.1287/mksc.1050.0133)** — The 2004 ISMS Practice Prize Winner—Sales Territory Design: Thirty Years of Modeling and Implementation. *Marketing Science*. Cited by 107.  
Thirty-year retrospective on deploying territory-alignment models in industry, including realignment disruption and adoption failure modes.  
*Bearing on this problem:* The implementation-reality citation. Its cited-by list is the best single entry point to the modern commercial-districting literature.

**[Mantrala et al. 2010](https://doi.org/10.1007/s11002-010-9111-4)** — Sales force modeling: State of the field and research agenda. *Marketing Letters*. Cited by 79.  
Survey of the sales-force modelling field with an explicit research agenda.  
*Bearing on this problem:* Orientation for adjacent work (sizing, compensation, call planning) that the model does not cover.


## Districting and contiguity formulations

**[SalazarAguilar et al. 2011](https://doi.org/10.1007/s11067-010-9151-6)** — New Models for Commercial Territory Design. *Networks and Spatial Economics*. Cited by 81.  
Commercial territory design with multiple balance criteria and dispersion objectives, solved exactly and heuristically.  
*Bearing on this problem:* Nearest published analogue to the applied setting; useful for defending objective choices.

**[RíosMercado & Pérez 2012](https://doi.org/10.1016/j.omega.2012.08.002)** — Commercial territory design planning with realignment and disjoint assignment requirements. *Omega*. Cited by 54.  
Territory design with realignment costs and disjoint-assignment requirements.  
*Bearing on this problem:* Closest match to a merger realignment: it prices moving units away from an incumbent, which the current model does not.

**[Validi et al. 2021](https://doi.org/10.1287/opre.2021.2141)** — Imposing Contiguity Constraints in Political Districting Models. *Operations Research*. Cited by 58.  
Compares and strengthens contiguity formulations for districting IPs; cut-based and flow-based encodings with computational dominance results.  
*Bearing on this problem:* Directly supersedes the separator-cut encoding used here. The answer to the national-scale performance gap.


## Cooperative bargaining theory

**[Nash 1950](https://doi.org/10.2307/1907266)** — The Bargaining Problem. *Econometrica*. Cited by 7,912.  
Axiomatises the two-person bargaining solution: Pareto efficiency, symmetry, scale invariance, IIA select the point maximising the product of gains over the disagreement point.  
*Bearing on this problem:* The source of the criterion. Note the convexity assumption on the feasible set, which indivisible units violate.

**[Nash 1953](https://doi.org/10.2307/1906951)** — Two-Person Cooperative Games. *Econometrica*. Cited by 3,217.  
Extends the bargaining solution to the two-person cooperative game with threats, deriving the disagreement point endogenously.  
*Bearing on this problem:* Relevant to any argument that the threat point should be modelled rather than assumed. NOTE: OpenAlex records the author as 'John C. Nash'; it is John F. Nash.

**[Kalai & Smorodinsky 1975](https://doi.org/10.2307/1914280)** — Other Solutions to Nash's Bargaining Problem. *Econometrica*. Cited by 1,817.  
Replaces IIA with individual monotonicity, selecting the solution that equalises fractions of maximum attainable gain.  
*Bearing on this problem:* The main alternative criterion. Systematically favours the party with the lower baseline.

**[Kalai 1977](https://doi.org/10.2307/1913954)** — Proportional Solutions to Bargaining Situations: Interpersonal Utility Comparisons. *Econometrica*. Cited by 766.  
Axiomatises proportional/egalitarian solutions, dropping scale invariance in favour of interpersonal utility comparison.  
*Bearing on this problem:* The reference for any explicit entitlement or seniority weighting, and the natural fallback when the product criterion is undefined.

**[Rubinstein 1982](https://doi.org/10.2307/1912531)** — Perfect Equilibrium in a Bargaining Model. *Econometrica*. Cited by 5,398.  
Alternating-offers game with discounting has a unique subgame-perfect equilibrium; its limit supports the Nash solution non-cooperatively.  
*Bearing on this problem:* Establishes what must be true for a bargaining solution to be descriptive: players must actually make offers. If a committee decides, the criterion is normative instead.

**[Binmore et al. 1990](https://doi.org/10.22004/ag.econ.275482)** — Noncooperative Models of Bargaining. *RePEc: Research Papers in Economics* (preprint). Cited by 107.  
Survey of non-cooperative bargaining models and the conditions under which they justify cooperative solution concepts.  
*Bearing on this problem:* Background for the descriptive-versus-normative distinction. Record type is a working paper; the canonical version is the Handbook chapter.

**[Thomson 1994](https://doi.org/10.1016/s1574-0005%2805%2980067-0)** — Chapter 35 Cooperative models of bargaining. *Handbook of game theory and economic applications* (book-chapter). Cited by 136.  
Handbook survey of cooperative bargaining: axioms, solutions, and the relations among them.  
*Bearing on this problem:* Best single citation for positioning one criterion against the family.

**[CollardWexler et al. 2018](https://doi.org/10.1086/700729)** — “Nash-in-Nash” Bargaining: A Microfoundation for Applied Work. *Journal of Political Economy*. Cited by 188.  
Provides microfoundations for 'Nash-in-Nash' bargaining used in applied IO, clarifying what the bilateral-product assumption requires.  
*Bearing on this problem:* Template for stating what a bargaining assumption buys and costs in an applied model.


**[Warren 2025](https://doi.org/10.1007/s00030-025-01118-7)** — Continuum Nash bargaining solutions. *Nonlinear Differential Equations and Applications NoDEA* **32**:109. Cited by 1.  
Characterises the Nash bargaining solution over a continuum of goods; at a zero disagreement point the solution is an optimal-transport map, so the allocation boundary is a Laguerre-cell tessellation.  
*Bearing on this problem:* Independent corroboration of the d=(0,0) baseline, and the natural route to N>2 wholesalers — semi-discrete transport gives Laguerre cells, which are contiguous by construction.

## Bargaining on non-convex / discrete sets

**[Mariotti 1998](https://doi.org/10.1007/s003550050114)** — Nash bargaining theory when the number of alternatives can be finite. *Social Choice and Welfare*. Cited by 57.  
Develops bargaining theory when the alternative set is finite rather than convex.  
*Bearing on this problem:* The correct citation for a discrete allocation set, where the classical axioms deliver a lottery rather than a point.

**[Xu & Yoshihara 2005](https://doi.org/10.1016/j.geb.2005.09.003)** — Alternative characterizations of three bargaining solutions for nonconvex problems. *Games and Economic Behavior*. Cited by 34.  
Characterises Nash, Kalai-Smorodinsky and egalitarian solutions on non-convex problems.  
*Bearing on this problem:* Companion to Mariotti; needed if a nonzero baseline is retained on a discrete feasible set.


## Fair division and maximum Nash welfare

**[Eisenberg & Gale 1959](https://doi.org/10.1214/aoms/1177706369)** — Consensus of Subjective Probabilities: The Pari-Mutuel Method. *The Annals of Mathematical Statistics*. Cited by 426.  
The Eisenberg-Gale convex program, whose optimum is the product-of-utilities allocation.  
*Bearing on this problem:* Why maximising a product of linear utilities is a well-behaved convex problem; the mathematical ancestor of the log-concavity argument.

**[Varian 1974](https://doi.org/10.1016/0022-0531%2874%2990075-1)** — Equity, envy, and efficiency. *Journal of Economic Theory*. Cited by 1,030.  
Defines envy-freeness and relates equity to efficiency in allocation.  
*Bearing on this problem:* Origin of the envy criterion that EF1 relaxes.

**[Thomson 2011](https://doi.org/10.1016/s0169-7218%2810%2900021-3)** — Fair Allocation Rules. *Handbook of social choice and welfare* (book-chapter). Cited by 242.  
Handbook survey of fair allocation rules and their axiomatic characterisations.  
*Bearing on this problem:* Reference work for choosing and defending a fairness criterion.

**[Lee 2017](https://doi.org/10.1016/j.ipl.2017.01.012)** — APX-hardness of maximizing Nash social welfare with indivisible items. *Information Processing Letters*. Cited by 16.  
Maximising Nash social welfare with indivisible items is APX-hard.  
*Bearing on this problem:* Explains why exhaustive validation stops at small n, and why exact solvability here is a property of special structure rather than of the problem.

**[Cole & Gkatzelis 2018](https://doi.org/10.1137/15m1053682)** — Approximating the Nash Social Welfare with Indivisible Items. *SIAM Journal on Computing*. Cited by 101.  
First constant-factor approximation for maximising Nash social welfare with indivisible items.  
*Bearing on this problem:* Establishes the computational standing of the criterion; cite alongside the hardness result.

**[Caragiannis et al. 2019](https://doi.org/10.1145/3355902)** — The Unreasonable Fairness of Maximum Nash Welfare. *ACM Transactions on Economics and Computation*. Cited by 294.  
Maximum Nash welfare (product of utilities, zero baseline) over indivisible goods is Pareto efficient and envy-free up to one good.  
*Bearing on this problem:* The theorem that licenses an EF1 claim. It requires a ZERO baseline; subtracting a constant from each utility voids the guarantee.

**[Moulin 2019](https://doi.org/10.1146/annurev-economics-080218-025559)** — Fair Division in the Internet Age. *Annual Review of Economics*. Cited by 97.  
Accessible survey of fair division, including maximum Nash welfare and its fairness guarantees.  
*Bearing on this problem:* The citation to hand a non-specialist or a committee.

**[Amanatidis et al. 2023](https://doi.org/10.1016/j.artint.2023.103965)** — Fair division of indivisible goods: Recent progress and open questions. *Artificial Intelligence*. Cited by 90.  
Current survey of fair division of indivisible goods: EF1, EFX, MMS, and open problems.  
*Bearing on this problem:* Fastest route to the state of the art and to what is still unresolved.


## Strategic misreporting

**[Crawford & Varian 1979](https://doi.org/10.1016/0165-1765%2879%2990118-6)** — Distortion of preferences and the Nash theory of bargaining. *Economics Letters*. Cited by 60.  
Agents can gain by misrepresenting preferences to a bargaining solution; the Nash solution is manipulable.  
*Bearing on this problem:* The reference for reporting incentives. Matters only where inputs are self-reported; cite to establish that the question was considered.


## Mixed-integer nonlinear programming

**[Kronqvist et al. 2018](https://doi.org/10.1007/s11081-018-9411-8)** — A review and comparison of solvers for convex MINLP. *Optimization and Engineering*. Cited by 302.  
Benchmarks solvers for convex mixed-integer nonlinear programs, including outer-approximation methods.  
*Bearing on this problem:* Supports the claim that a concave objective over a MILP-representable set is the tractable class, and guides solver choice.

**[Sahinidis 2019](https://doi.org/10.1007/s11081-019-09438-1)** — Mixed-integer nonlinear programming 2018. *Optimization and Engineering*. Cited by 132.  
Survey of mixed-integer nonlinear programming: formulations, algorithms, software.  
*Bearing on this problem:* General MINLP citation for methods sections.


## Contiguity: encodings, algorithms, preprocessing

**[Shirabe 2005](https://doi.org/10.1111/j.1538-4632.2005.00605.x)** — A Model of Contiguity for Spatial Unit Allocation. *Geographical Analysis*. Cited by 161.  
Introduces the flow-based contiguity formulation (SHIR): a directed flow variable per district-root-and-edge pair enforces that every included vertex is reachable from a fixed root within its assigned district, as a single upfront MILP needing no lazy cuts.  
*Bearing on this problem:* The flow-based fallback baseline for `districting.py`'s contiguity constraint; no callback machinery needed, but flow-variable count grows with n·m, so it is best used as a small/medium-instance sanity check rather than the production formulation.

**[Shirabe 2009](https://doi.org/10.1068/b34104)** — Districting Modeling with Exact Contiguity Constraints. *Environment and Planning B: Planning and Design*. Cited by 97.  
Companion paper restating and refining the flow-based contiguity model for districting IPs with exact contiguity constraints.  
*Bearing on this problem:* The most commonly cited statement of the SHIR formulation; corroborates the flow-based approach as the field's most widely adopted always-on contiguity encoding.

**[Duque et al. 2011](https://doi.org/10.1111/j.1538-4632.2010.00810.x)** — The p-Regions Problem. *Geographical Analysis*. Cited by 108.  
Introduces and computationally compares three k-region MIP formulations (a spanning-forest tree model, an order/hop-distance model, and a Shirabe-style flow model), finding all three fail to reach proven optimality on 40–70% of instances with as few as 25–49 units under a 3-hour cutoff.  
*Bearing on this problem:* The strongest available warning that changing contiguity-encoding families alone will not fix the solver's scale wall — even the flow encoding stalls well below the project's own 125-unit failure threshold absent solver-level acceleration.

**[Zhang et al. 2024](https://doi.org/10.1007/s11590-023-02070-0)** — Linear-size formulations for connected planar graph partitioning and political districting. *Optimization Letters*. Cited by 2.  
Gives a linear-size, LP-integral extended formulation for partitioning a planar graph into k connected pieces, built on Williams' spanning-tree formulation, but shows the polytope's integrality (and its performance edge over the Hess model) is destroyed once population/value-balance constraints are added.  
*Bearing on this problem:* A cautionary result rather than a fix — the project's g_a/g_b value totals are exactly this kind of balance constraint, so this asymptotically smallest encoding is not recommended for the Nash-welfare setting.

**[Validi & Buchanan 2022](https://doi.org/10.1007/s12532-022-00221-5)** — Political districting to minimize cut edges. *Mathematical Programming Computation*. Cited by 20.  
Companion paper to the contiguity-formulation survey, formulating and solving political districting with a cut-edge-minimizing compactness objective at scale using the same cut-based, lazily separated contiguity constraints.  
*Bearing on this problem:* Reinforces that lazily generated separator cuts inside a single branch-and-cut tree, not an always-on flow formulation, is the encoding family that scales — directly paralleling `districting.py`'s own separator-cut architecture.

**[Carvajal et al. 2013](https://doi.org/10.1287/opre.2013.1183)** — Imposing Connectivity Constraints in Forest Planning Models. *Operations Research*. Cited by 112.  
Formulates connectivity for forest-harvest scheduling via cutset constraints separated lazily in branch-and-cut, for the harder unrooted case where no fixed root is known in advance, scaling to instances 2–3x larger than prior connectivity-constrained forest models.  
*Bearing on this problem:* Confirms that `districting.py`'s easier rooted setting, where both sides' roots are already fixed, should scale better than this paper's harder unrooted results, and that rooted, static problems are consistently easier — supporting the project's own component-quotient preprocessing idea.

**[Álvarez-Miranda et al. 2013](https://doi.org/10.1007/978-3-642-38189-8_11)** — The Maximum Weight Connected Subgraph Problem. *Facets of Combinatorial Optimization: Festschrift for Martin Grötschel*. Cited by 35.  
Surveys and compares node-based versus flow-based ILP formulations for the maximum-weight connected subgraph problem, showing the node-based separator formulation is both faster and more stable under variation in node weights.  
*Bearing on this problem:* The single most directly relevant piece of evidence for the heavy-tail failure mechanism — suggests that node-based, separator-driven contiguity formulations are inherently more robust to heavy-tailed per-zip values than flow-based ones.

**[Oehrlein & Haunert 2017](https://doi.org/10.5311/josis.2017.15.379)** — A cutting-plane method for contiguity-constrained spatial aggregation. *Journal of Spatial Information Science*. Cited by 9.  
Applies a lazy cutting-plane method to enforce contiguity in size-thresholded, homogeneous spatial aggregation (map generalization), separating violated connectivity cuts only as needed rather than upfront.  
*Bearing on this problem:* A secondary corroborating source for the lazy-separator-cut family `districting.py` already uses, applied to a different downstream (map-generalization) objective.

**[Buchanan et al. 2018](https://doi.org/10.1002/net.21825)** — Algorithms for Node-Weighted Steiner Tree and Maximum-Weight Connected Subgraph. *Networks*. Cited by 12.  
Develops preprocessing/reduction rules (cut-vertex detection, low-degree contraction) purpose-built for exact node-weighted Steiner tree and maximum-weight connected subgraph problems, giving the first improvements over exhaustive search for this problem class.  
*Bearing on this problem:* These reductions target exactly the sparse, mostly-zero-value glue-node structure real ZCTA data will have, shrinking the graph before any branch-and-bound runs.

**[Fischetti et al. 2017](https://doi.org/10.1007/s12532-016-0111-0)** — Thinning out Steiner trees: a node-based model for uniform edge costs. *Mathematical Programming Computation*. Cited by 74.  
Gives a node-only ILP formulation for Steiner trees that drops edge variables entirely under uniform edge costs, winning the DIMACS11 Steiner-tree challenge.  
*Bearing on this problem:* A near-exact structural fit for a Rook-adjacency grid where connectivity cost is uniform per glue node or per perimeter edge, likely smaller and faster than a generic edge-based Steiner formulation.

**[Leitner et al. 2018](https://doi.org/10.1287/ijoc.2017.0788)** — A Dual Ascent-Based Branch-and-Bound Framework for the Prize-Collecting Steiner Tree and Related Problems. *INFORMS Journal on Computing*. Cited by 26.  
Generalizes Wong's dual-ascent method to a branch-and-bound framework that unifies the Steiner tree, prize-collecting Steiner tree, maximum-weight connected subgraph, and node-weighted Steiner tree problems under one solver architecture.  
*Bearing on this problem:* Means a single codebase/solver could cover every glue-node variant relevant to the ZCTA problem's zero-value-connector structure.

**[Gamrath et al. 2017](https://doi.org/10.1007/s12532-016-0114-x)** — SCIP-Jack — a solver for STP and variants with parallelization extensions. *Mathematical Programming Computation*. Cited by 43.  
Presents SCIP-Jack, the open-source SCIP-based solver for eleven Steiner-family problems including prize-collecting Steiner tree and maximum-weight connected subgraph.  
*Bearing on this problem:* The concrete open-source reference implementation for the node-based, lazy branch-and-cut approach recommended for robustness under heavy-tailed unit values.

**[Rehfeldt et al. 2019](https://doi.org/10.1002/net.21857)** — Reduction techniques for the prize collecting Steiner tree problem and the maximum-weight connected subgraph problem. *Networks*. Cited by 13.  
Presents numerous new reduction methods for prize-collecting Steiner tree problems that shrink over 90% of benchmark instances to triviality before branch-and-bound even begins.  
*Bearing on this problem:* The most mature published analogue to the project's own proposed component-quotient preprocessing idea, except these reductions are formally proven safe rather than a heuristic guess.

**[Rehfeldt & Koch 2022](https://doi.org/10.1287/ijoc.2021.1087)** — On the Exact Solution of Prize-Collecting Steiner Tree Problems. *INFORMS Journal on Computing*. Cited by 9.  
Solves prize-collecting Steiner tree benchmark instances with up to ten million edges to proven optimality in under two hours.  
*Bearing on this problem:* Evidence that exact PCST-family solving scales far beyond the project's 400–800-ZCTA target, if the glue-node connectivity subproblem can be isolated from the Nash-welfare objective.

**[Miyazawa et al. 2021](https://doi.org/10.1016/j.ejor.2020.12.059)** — Partitioning a graph into balanced connected classes: Formulations, separation and experiments. *European Journal of Operational Research*. Cited by 32.  
Studies exactly the problem of partitioning a node-weighted graph into k connected, balanced classes, contributing ILP formulations, valid inequalities, and a lazy connectivity-cut separation routine.  
*Bearing on this problem:* The closest published problem statement to `districting.py`'s own k=2 connected-bipartition structure; its separation routines are the most likely of any surveyed paper to transplant directly into the existing lazy-cut loop as stronger valid inequalities.

**[Duran & Grossmann 1986](https://doi.org/10.1007/BF02592064)** — An outer-approximation algorithm for a class of mixed-integer nonlinear programs. *Mathematical Programming*. Cited by 1217.  
Proves finite convergence of outer approximation for convex MINLPs linear in the 0-1 variables, alternating an NLP relaxation with an MILP master that accumulates Kelley-tangent linearizations.  
*Bearing on this problem:* The theorem `districting.py`'s own outer-approximation loop already leans on for its Nash-log cuts; it says nothing about the separately added connectivity cuts, which follow a different convergence argument.

**[Fletcher & Leyffer 1994](https://doi.org/10.1007/BF01581153)** — Solving mixed integer nonlinear programs by outer approximation. *Mathematical Programming*. Cited by 538.  
Repairs a gap in Duran and Grossmann's original outer-approximation algorithm that could cut off the true optimum when NLP subproblems have degenerate multipliers, tightening the master formulation while preserving finite convergence.  
*Bearing on this problem:* Relevant only if the log-welfare linearization has degenerate KKT multipliers at near-ties, which is plausible under the project's low-rho, near-flat objective landscape.

**[Quesada & Grossmann 1992](https://doi.org/10.1016/0098-1354(92)80028-8)** — An LP/NLP based branch and bound algorithm for convex MINLP optimization problems. *Computers & Chemical Engineering*. Cited by 321.  
Introduces single-tree LP/NLP-based branch-and-bound, adding outer-approximation cuts as lazy constraints inside one branch-and-bound tree rather than re-solving a fresh MILP master from scratch each round.  
*Bearing on this problem:* The single highest-leverage fix identified for `districting.py`'s pure-scale failure mode, eliminating the repeated re-solve-from-scratch cost that lets HiGHS hit iteration/time limits above roughly 125 units.

**[Bonami et al. 2008](https://doi.org/10.1016/j.disopt.2006.10.011)** — An algorithmic framework for convex mixed integer nonlinear programs. *Discrete Optimization*. Cited by 666.  
Describes the Bonmin solver's five convex-MINLP algorithm variants, including a hybrid single-tree outer-approximation-in-branch-and-cut, and confirms empirically that single-tree methods consistently beat multi-tree outer approximation as instance size grows.  
*Bearing on this problem:* Independent corroboration that the single-tree architecture is the right fix for `districting.py`'s scale wall, though Bonmin itself offers no Python callback for injecting the project's own connectivity cuts.

**[Kronqvist et al. 2016](https://doi.org/10.1007/s10898-015-0322-3)** — The extended supporting hyperplane algorithm for convex mixed-integer nonlinear programming. *Journal of Global Optimization*. Cited by 62.  
Introduces the extended supporting-hyperplane algorithm, which generates cuts from boundary points found via line search rather than tangents at NLP-subproblem optima, typically needing fewer cuts than plain outer approximation on mildly curved feasible regions.  
*Bearing on this problem:* Could reduce the outer-approximation round count that heavy-tailed unit values currently inflate 2–5x, since the Nash log-welfare surface is close to piecewise-linear once dominated by many summed unit values.

**[Hooker & Ottosson 2003](https://doi.org/10.1007/s10107-003-0375-9)** — Logic-based Benders decomposition. *Mathematical Programming*. Cited by 479.  
Generalizes Benders decomposition to any master/subproblem split where subproblem infeasibility can be certified and turned into a combinatorial no-good-style cut added back to the master, proving finite convergence via exhaustion of a finite cut set.  
*Bearing on this problem:* The correct convergence theory for `districting.py`'s separator-cut loop — a different theory from outer approximation's convex-cut argument, confirming that the two cut families inside one loop do not share a convergence proof.

**[Codato & Fischetti 2006](https://doi.org/10.1287/opre.1060.0286)** — Combinatorial Benders' Cuts for Mixed-Integer Linear Programming. *Operations Research*. Cited by 352.  
Specializes logic-based Benders decomposition to pure 0-1 MILP masters, showing that combinatorial Benders cuts retain finite convergence because the master's feasible set is finite.  
*Bearing on this problem:* Formalizes exactly what `districting.py`'s separator-cut loop already does, and suggests deriving one stronger aggregated cut per disconnected component rather than many weak per-edge cuts.

**[Vielma & Nemhauser 2011](https://doi.org/10.1007/s10107-009-0295-4)** — Modeling disjunctive constraints with a logarithmic number of binary variables and constraints. *Mathematical Programming*. Cited by 248.  
Gives piecewise-linear encodings needing only O(log k) binary variables for a k-segment approximation, instead of O(k).  
*Bearing on this problem:* Would keep the binary count small if the Nash log-welfare objective were replaced by an epsilon-certified piecewise-linear MILP, which matters once heavy-tailed values widen the range the approximation grid must cover.

**[Boland et al. 2015](https://doi.org/10.1287/ijoc.2015.0646)** — A Criterion Space Search Algorithm for Biobjective Mixed Integer Programming: The Triangle Splitting Method. *INFORMS Journal on Computing*. Cited by 53.  
Introduces the Triangle Splitting Method, a criterion-space search algorithm that enumerates the Pareto frontier of a biobjective mixed-integer program via a sequence of epsilon-constraint MILPs.  
*Bearing on this problem:* Gives a formally exact way to treat (g_a, g_b) as a biobjective problem and select the Nash-welfare-maximizing point from the finite frontier — useful chiefly as a verification/audit tool for the outer-approximation solution rather than a wholesale replacement.

**[Lemaréchal et al. 1995](https://doi.org/10.1007/BF01585555)** — New variants of bundle methods. *Mathematical Programming*. Cited by 294.  
Diagnoses why plain Kelley cutting planes zigzag and converge slowly when the objective is nearly flat near the optimum, and fixes this with the level method, which projects the next trial point into a target-gap level set instead of taking the master's raw optimum.  
*Bearing on this problem:* Matches `districting.py`'s reported symptom exactly — a near-flat, low-rho objective causing multi-round cut-loop thrashing — and gives a provably faster-converging alternative.

**[Ben-Ameur & Neto 2007](https://doi.org/10.1002/net.20137)** — Acceleration of cutting-plane and column generation algorithms: Applications to network design. *Networks*. Cited by 72.  
Gives a cheaper in-out stabilization of cutting-plane and column-generation algorithms, separating at a point between a stable interior point and the master's optimum rather than at the raw optimum.  
*Bearing on this problem:* A lower-engineering-cost alternative to the level method for the same flat-objective thrashing problem, needing only a line-search step rather than a new subproblem type.

**[Fischetti & Salvagnin 2010](https://doi.org/10.1007/978-3-642-13520-0_17)** — An In-Out Approach to Disjunctive Optimization. *Integration of AI and OR Techniques in Constraint Programming for Combinatorial Optimization Problems (CPAIOR 2010)*. Cited by 13.  
Applies the in-out stabilization idea specifically to branch-and-cut masters where cuts are generated lazily against a combinatorial/disjunctive feasible set, not just a smooth convex one.  
*Bearing on this problem:* Confirms in-out stabilization applies to the connectivity-separator cut loop itself, not only the Nash-welfare outer-approximation loop, potentially avoiding oscillation between disconnected near-tied partitions.

**[Pisinger 2005](https://doi.org/10.1016/j.cor.2004.03.002)** — Where are the hard knapsack problems? *Computers & Operations Research*. Cited by 328.  
Shows 0-1 knapsack hardness is driven by weight/value correlation and coefficient spread — a few dominant-value items create a loose LP relaxation — rather than by instance size alone.  
*Bearing on this problem:* The closest available theoretical grounding for the project's heavy-tail failure mechanism; per-zip A_z/B_z values function like knapsack coefficients, and standard remedies (coefficient scaling, pre-fixing dominant nodes) are directly testable against the C9 battery case.

**[Karypis & Kumar 1998](https://doi.org/10.1006/jpdc.1997.1404)** — Multilevel k-way Partitioning Scheme for Irregular Graphs. *Journal of Parallel and Distributed Computing*. Cited by 1144.  
METIS's foundational multilevel graph-partitioning method: coarsen the graph, partition the small coarse graph, then uncoarsen with local refinement.  
*Bearing on this problem:* A fast heuristic first pass to get a starting bipartition and fix obviously one-sided ZCTAs before running the full contiguity MILP only on the disputed boundary corridor; off-the-shelf refinement alone does not guarantee a contiguous output.

**[Gurnee & Shmoys 2021](https://doi.org/10.1137/1.9781611976830.9)** — Fairmandering: A column generation heuristic for fairness-optimized political districting. *SIAM Conference on Applied and Computational Discrete Algorithms (ACDA21)*. Cited by 13.  
Fairmandering's column-generation heuristic recursively builds an ensemble of contiguous, balanced candidate districts, then solves a set-partitioning master problem to select one column per district under an arbitrary fairness objective.  
*Bearing on this problem:* Because every generated column is contiguous by construction, this sidesteps the free-optimum-splits-first failure mode entirely as a warm-start generator, though the master objective would need to be adapted to the two-player Nash log-sum.

**[DeFord et al. 2021](https://doi.org/10.1162/99608f92.eb30390f)** — Recombination: A Family of Markov Chains for Redistricting. *Harvard Data Science Review*. Cited by 37.  
Introduces ReCom, a Markov chain that merges two adjacent districts, draws a random spanning tree, and cuts an edge to re-split into two guaranteed-connected pieces near a balance target, implemented in the open-source GerryChain package.  
*Bearing on this problem:* A low-cost, pip-installable warm-start and fallback generator that never constructs an unconstrained-but-disconnected optimum in the first place, directly targeting the pre-existing-disconnection failure mode and giving the solver a feasible MIP-start incumbent.

**[Ríos-Mercado & Fernández 2009](https://doi.org/10.1016/j.cor.2007.10.024)** — A reactive GRASP for a commercial territory design problem with multiple balancing requirements. *Computers & Operations Research*. Cited by 108.  
A reactive GRASP metaheuristic for commercial territory design with contiguity and multiple balance requirements, motivated by a real beverage-distribution application.  
*Bearing on this problem:* The closest industry analogue to the rep-territory problem; GRASP constructions grow territories from seeds and so are contiguous by construction, never encountering the free-optimum-disconnection failure mode, at the cost of no optimality bound.

**[Bozkaya et al. 2003](https://doi.org/10.1016/s0377-2217(01)00380-0)** — A tabu search heuristic and adaptive memory procedure for political districting. *European Journal of Operational Research*. Cited by 210.  
A tabu search heuristic with an adaptive memory of elite solutions for political districting under population balance, compactness, and hard contiguity checked at every move.  
*Bearing on this problem:* Same profile as the GRASP heuristic above — a practical, always-contiguous fallback for when the exact MINLP times out, with no bound on solution quality.

**[King et al. 2018](https://doi.org/10.1007/s10589-017-9936-3)** — The geo-graph in practice: creating United States Congressional Districts from census blocks. *Computational Optimization and Applications*. Cited by 14.  
Develops the geo-graph model for enforcing contiguity at scale when building US Congressional districts directly from census blocks.  
*Bearing on this problem:* A further cut-engineering reference on lazy contiguity generation at real census-geography scale, useful for mining implementation detail beyond the main Validi/Buchanan/Lykhovyd papers.


## Fair division on graphs (connected bundles)

**[Bouveret et al. 2017](https://doi.org/10.24963/ijcai.2017/20)** — Fair Division of a Graph. *Proceedings of the Twenty-Sixth International Joint Conference on Artificial Intelligence (IJCAI 2017)*. Cited by 42.  
Founds the fair-division-of-a-graph model — items are vertices of a graph and each agent's bundle must induce a connected subgraph — and shows a connected maximin-share allocation always exists on trees but not on cycles, while deciding connected proportionality or envy-freeness is NP-hard even on paths.  
*Bearing on this problem:* Establishes the baseline vocabulary and first hardness result the rest of this literature builds on; Rook-adjacency ZCTA graphs are planar and far from tree-like, so the tree-only maximin-share existence guarantee does not transfer directly.

**[Bilò et al. 2022](https://doi.org/10.1016/j.geb.2021.11.006)** — Almost envy-free allocations with connected bundles. *Games and Economic Behavior*. Cited by 21.  
Characterizes exactly which graphs guarantee a connected EF1 allocation for two agents: precisely those whose biconnected-component tree is a path, computable in O(m) time by a discrete cut-and-choose protocol that also achieves each agent's graph-restricted maximin share simultaneously.  
*Bearing on this problem:* Because a Rook-adjacency grid region is biconnected whenever it has no articulation points, this gives an unconditional, cheap, certified EF1-and-MMS fallback for the two-wholesaler problem whenever the disputed census component lacks a chokepoint ZCTA.

**[Suksompong 2019](https://doi.org/10.1016/j.dam.2019.01.036)** — Fairly allocating contiguous blocks of indivisible items. *Discrete Applied Mathematics*. Cited by 29.  
For contiguous (path) allocations between exactly two agents, proves an envy bound of at most the single largest per-item valuation gap and a matching equitability guarantee, with a price-of-fairness table showing egalitarian welfare costs nothing extra under equitability for two agents.  
*Bearing on this problem:* Gives an absolute, instance-size-independent loss bound usable as a sanity check: if the MINLP's contiguity cost ever exceeds the largest per-zip valuation gap, something is likely mis-specified rather than merely expensive.

**[Igarashi & Peters 2019](https://doi.org/10.1609/aaai.v33i01.33012045)** — Pareto-Optimal Allocation of Indivisible Goods with Connectivity Constraints. *Proceedings of the AAAI Conference on Artificial Intelligence (AAAI 2019)*. Cited by 18.  
Shows finding any Pareto-optimal connected allocation is NP-hard on trees/forests via reductions that require three or more agents, and exhibits path instances with no allocation simultaneously Pareto-optimal and EF1 — again only in constructions using three or more agents.  
*Bearing on this problem:* The oft-repeated claim that Nash welfare with connectivity is EF1-incompatible rests on constructions needing 3+ agents and is not established for exactly the two-wholesaler case — a genuine gap worth flagging rather than assuming the counterexamples transfer down to n=2.

**[Lonc & Truszczyński 2020](https://doi.org/10.1613/jair.1.11702)** — Maximin Share Allocations on Cycles. *Journal of Artificial Intelligence Research*. Cited by 14.  
Studies the graph-restricted maximin share specifically on cycles, showing it need not exist there even though it always exists on trees, but also proves that for exactly two agents a connectivity-respecting maximin-share allocation always exists on any connected graph, regardless of topology.  
*Bearing on this problem:* Confirms two-agent maximin-share existence is graph-independent for the wholesaler problem; only the quality of that guarantee depends on topology, addressed by the price-of-connectivity result below.

**[Bei et al. 2022](https://doi.org/10.1137/20m1388310)** — The Price of Connectivity in Fair Division. *SIAM Journal on Discrete Mathematics*. Cited by 14.  
Defines the Price of Connectivity — the worst-case ratio between unconstrained and graph-restricted maximin share — and shows it is exactly 4/3 (tight) for two agents on any biconnected graph, degrading to the number of pieces created by deleting a cut vertex when one exists.  
*Bearing on this problem:* The closest published quantitative bound on how much hard contiguity can cost a two-agent fair division, and it formally explains why a low-degree cut vertex is the worst topological case — matching the project's own empirically observed pre-existing-disconnection failure mode.

**[Deligkas et al. 2021](https://doi.org/10.24963/ijcai.2021/20)** — The Parameterized Complexity of Connected Fair Division. *Proceedings of the Thirtieth International Joint Conference on Artificial Intelligence (IJCAI 2021)*. Cited by 7.  
Proves that connected fair division (proportionality, envy-freeness, EF1, or EFX) is NP-hard even with exactly two agents and identical unit valuations, via a reduction from equitable connected graph partitioning, and that tractability additionally requires bounding the graph's clique-width or treewidth.  
*Bearing on this problem:* Shows restricting to two wholesalers does not by itself rescue tractability; ZCTA Rook grids have unbounded treewidth and clique-width, consistent with the project's finding that scale, not agent count, drives MILP failure.

**[Bouveret et al. 2019](https://doi.org/10.1007/s10458-019-09415-z)** — Chore division on a graph. *Autonomous Agents and Multi-Agent Systems*. Cited by 11.  
Extends graph fair division to chores (disutility items), showing that goods and chores instances are not symmetric under a naive utility-sign flip.  
*Bearing on this problem:* Low direct relevance today since M_z/A_z/B_z are goods, but worth keeping in reserve if a future extension needs to treat undesirable, high-cost-to-serve ZCTAs as chores rather than low-value goods.

**[Igarashi 2023](https://doi.org/10.1609/aaai.v37i5.25705)** — How to Cut a Discrete Cake Fairly. *Proceedings of the AAAI Conference on Artificial Intelligence (AAAI 2023)*. Cited by 9.  
Studies a hybrid discrete/continuous "discrete cake" model on a path where one item per cut point may be fractionally split between two agents, improving on pure-EF1 path results.  
*Bearing on this problem:* Low direct relevance since ZCTAs are genuinely indivisible, but useful as the boundary case that disappears once true indivisibility is enforced.

**[Igarashi & Zwicker 2023](https://doi.org/10.1007/s10107-023-01945-5)** — Fair division of graphs and of tangled cakes. *Mathematical Programming*. Cited by 3.  
Connects discrete graph fair division to a continuous "tangled cake" built by gluing intervals per a graph structure, showing exactly the Hamiltonian ("stringable") graphs guarantee envy-free connected division for any number of agents.  
*Bearing on this problem:* A theoretically elegant bridge to the continuum optimal-transport literature (M. Warren 2025) on the other side of the same discrete/continuum divide; its open n≥3 conjecture is not an immediate concern for a strictly bilateral model but is useful vocabulary for a future leximin extension to three or more wholesalers.

**[Bei et al. 2025](https://doi.org/10.1137/22m1500502)** — Dividing a Graphical Cake. *SIAM Journal on Discrete Mathematics*. Cited by 3.  
Generalizes graphical cake-cutting from paths/cycles to arbitrary graphs, where the cake is spread over a graph's edges or vertices, and shows proportionality with connected pieces is not always achievable on general graphs.  
*Bearing on this problem:* A continuum analogue of Bouveret et al. 2017's discrete impossibility results, establishing that graph topology beyond path/cycle is an active research frontier on the continuum side too.


## Gaps in this bibliography

Three threads relevant to the model are **not** covered here and would need their own search:

1. Estimation of transfer capture from historical territory reassignments — staggered difference-in-differences and synthetic control. The applied-econometrics literature, not the OR one.
2. Sales-force turnover and retention effects of realignment, which is what makes the fairness criterion consequential rather than cosmetic.
3. Leximin and other criteria for three or more claimants, needed if the overlap graph does not decompose into pairs.
