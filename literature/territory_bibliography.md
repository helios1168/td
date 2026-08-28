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


## Gaps in this bibliography

Three threads relevant to the model are **not** covered here and would need their own search:

1. Estimation of transfer capture from historical territory reassignments — staggered difference-in-differences and synthetic control. The applied-econometrics literature, not the OR one.
2. Sales-force turnover and retention effects of realignment, which is what makes the fairness criterion consequential rather than cosmetic.
3. Leximin and other criteria for three or more claimants, needed if the overlap graph does not decompose into pairs.
