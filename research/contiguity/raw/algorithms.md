# Algorithms for convex MINLP + lazily-generated connectivity cuts
## Research leg: territory-division contiguous Nash-welfare solver (`districting.py::solve_contiguous_nash`)

Scope recap: maximize log g_a + log g_b, g_a/g_b linear in binary x over ~400-800 planar-graph
units, both sides' induced subgraphs must be connected, rho*perimeter penalty needed to make
connectivity cuts bite. Current method: multi-tree OA (Kelley tangents on log, re-solved as a
fresh `scipy.optimize.milp`/HiGHS problem every round) interleaved with lazily-added separator
cuts for connectivity, no callbacks. Failure mechanisms: (a) free-Nash optimum already
disconnected, (b) time/iteration limits above ~125 units, (c) heavy right-tailed unit values
blow up iteration count and cost 2-5x on identical geometry.

All DOIs below were checked against `https://api.crossref.org/works/<DOI>` and confirmed to
match the claimed title/authors/year before being marked VERIFIED.

---

## 1. Outer-approximation theory: does OA + lazy combinatorial cuts still converge finitely?

### 1.1 Duran & Grossmann (1986) — the original OA theorem
**Duran, M.A., Grossmann, I.E. "An outer-approximation algorithm for a class of mixed-integer
nonlinear programs." Mathematical Programming 36, 307-339 (1986).**
DOI: 10.1007/BF02592064 — VERIFIED (Crossref: title/authors/year match).

Proves finite convergence of OA for MINLPs that are convex and linear in the 0-1 variables:
alternate an NLP subproblem (fix integers, solve continuous relaxation) with an MILP master
that accumulates linearizations (Kelley tangents) of the objective and constraints at each NLP
solution. Because the feasible region is convex, every generated cut is globally valid, so the
master's optimal value is a nondecreasing lower bound (for a min problem) that meets the best
NLP solution in a finite number of major iterations, bounded by the number of distinct integer
assignments visited. **Guarantee kept:** global optimality certificate, finite termination —
*provided every cut added is a valid outer-approximation cut of a fixed convex feasible region*.
**Relevance to (a)/(b)/(c):** This is exactly the theorem the current code leans on for the two
Kelley tangents on log g_a/log g_b. It says nothing about the connectivity cuts, which are not
linearizations of a smooth convex function but feasibility cuts against a combinatorial
(non-convex) set — see 1.4. **Implementation cost:** already implemented; the risk is assuming
its finite-convergence guarantee silently extends to the connectivity loop.

### 1.2 Fletcher & Leyffer (1994) — tightened OA, avoids equality-constraint pitfalls
**Fletcher, R., Leyffer, S. "Solving mixed integer nonlinear programs by outer approximation."
Mathematical Programming 66, 327-349 (1994).** DOI: 10.1007/BF01581153 — VERIFIED.

Repairs a gap in Duran-Grossmann (their master problem can cut off the true optimum when
NLP subproblems have degenerate multipliers / equality constraints) and tightens the master
formulation. Same finite-convergence class of guarantee. **Effect on (a)/(b)/(c):** irrelevant
to the connectivity mechanism itself; only matters if the log-welfare linearization has
degenerate KKT multipliers at ties (plausible under near-flat rho=0 objectives — see 3). Cheap
to adopt: just tighten how the current code forms the OA cut at ties.

### 1.3 Quesada & Grossmann (1992) — LP/NLP-based branch-and-bound = single-tree OA
**Quesada, I., Grossmann, I.E. "An LP/NLP based branch and bound algorithm for convex MINLP
optimization problems." Computers & Chemical Engineering 16, 937-947 (1992).**
DOI: 10.1016/0098-1354(92)80028-8 — VERIFIED.

This is the key structural fix for mechanism (b). Instead of re-solving a fresh MILP master
from scratch every round (what the current code does), OA cuts are added **as lazy constraints
inside a single branch-and-bound tree**: whenever B&B finds a new integer-feasible incumbent,
solve the NLP relaxation at that point, add its linearization as a cut, and continue the *same*
tree instead of restarting. This is provably still finitely convergent (same cut-validity
argument as Duran-Grossmann) but avoids re-exploring the search tree from the root every
iteration — the single biggest inefficiency in "fresh MILP solve per round." **Guarantee kept:**
global certificate, same finite bound on major iterations, but wall-clock is dramatically
better because the tree persists. **Effect on (b):** direct — this is precisely the fix for
scale, since it eliminates the repeated re-solve-from-scratch cost that lets HiGHS hit
iteration/time limits at 125+ units. **Effect on (a)/(c):** neutral on their root cause but
gives much more budget per instance, indirectly helping both. **Implementation cost:** HIGH
with the current stack — `scipy.optimize.milp` (HiGHS via its Python binding) has no
lazy-constraint / incumbent callback in scipy's exposed API. Requires either raw `highspy`
(HiGHS's own Python bindings expose MIP callbacks), `python-mip` + CBC (which supports lazy
constraints via `model.add_lazy_constr` in a callback), OR-Tools CP-SAT (`AddLazyConstraint` is
not exposed for pure MIP but CP-SAT's `OnSolutionCallback` + `StopSearch`/resubmit can emulate
it awkwardly), or PySCIPOpt (SCIP has first-class `conshdlr` lazy-cut callbacks and is the
cleanest match for this pattern). **This is the single highest-leverage algorithmic change for
mechanism (b).**

### 1.4 Bonami et al. (2008) — hybrid OA/NLP-BB/B&C framework (Bonmin)
**Bonami, P., Biegler, L.T., Conn, A.R., Cornuéjols, G., Grossmann, I.E., Laird, C.D., Lee, J.,
Lodi, A., Margot, F., Sawaya, N., Wächter, A. "An algorithmic framework for convex mixed
integer nonlinear programs." Discrete Optimization 5, 186-204 (2008).**
DOI: 10.1016/j.disopt.2006.10.011 — VERIFIED.

Describes the Bonmin solver's five algorithm variants, including a hybrid B-OA (outer
approximation inside branch-and-cut, i.e., the Quesada-Grossmann idea implemented at
production scale) and B-QG (quesada-grossmann). Confirms empirically that single-tree OA
consistently beats multi-tree OA on wall-clock, especially as instance size grows — directly
evidencing why mechanism (b) is expected. **Guarantee kept:** global optimality (all variants
are exact for convex MINLP). **Implementation cost:** Bonmin itself is a C++/COIN-OR solver;
usable from Python via Pyomo's `SolverFactory('bonmin')` if a Bonmin binary is available
(conda-forge ships one) — this sidesteps building your own callback loop entirely, at the cost
of losing direct control over how connectivity cuts are injected (would need Pyomo's
`GDPopt`/user cut callback support, which is limited for Bonmin specifically vs. Couenne).

### 1.5 Kronqvist, Bernal, Lundell, Grossmann (2019) — state-of-the-art review
**Kronqvist, J., Bernal, D.E., Lundell, A., Grossmann, I.E. "A review and comparison of solvers
for convex MINLP." Optimization and Engineering 20, 397-455 (2019).**
DOI: 10.1007/s11081-018-9411-8 — VERIFIED (Crossref shows 2018 online / 2019 print, consistent).

Benchmarks OA, ECP (extended cutting plane), ESH (extended supporting hyperplane, see 1.6),
GBD (generalized Benders), and QG/hybrid single-tree methods across solvers (Bonmin, DICOPT,
SHOT, AlphaECP, etc.). Reports single-tree LP/NLP-BB (QG) and SHOT (OA+ESH hybrid, single-tree)
as the most robust/fastest general-purpose approaches on medium-large convex MINLP, consistent
with 1.3's prediction. Also discusses **lazy-constraint implementations of nonlinear cuts** as
the mechanism that makes single-tree methods practical in modern solvers (Gurobi/CPLEX lazy
callbacks). Directly names logic-based Benders / combinatorial cuts as a *different* family
that composes with OA when the extra difficulty is combinatorial rather than purely nonlinear
— exactly the connectivity-cut situation here (see Section 2 below in this review's own
taxonomy). **No new guarantee**, but it is the best available synthesis of "what actually
converges fast in practice" and confirms the priority-1 recommendation in 1.3.

### 1.6 Kronqvist, Lundell, Westerlund (2016) — ESH / SHOT
**Kronqvist, J., Lundell, A., Westerlund, T. "The extended supporting hyperplane algorithm for
convex mixed-integer nonlinear programming." Journal of Global Optimization 64, 249-272
(2016).** DOI: 10.1007/s10898-015-0322-3 — VERIFIED.

ESH generates supporting hyperplanes from points on the boundary of the continuous relaxation
found via a line search, rather than tangents at NLP-subproblem optima. Tends to need fewer
cuts than pure OA/ECP when the nonlinear feasible region is only mildly curved — which is the
case here (log is not very curved when g_a/g_b are dominated by dozens-to-hundreds of summed
unit values, so the "gain surface" is close to piecewise-linear already). **Effect on (a)/(b)/
(c):** could reduce the OA round count (helping (c), where heavy tails currently multiply
iterations 2-5x), at the cost of an extra line-search per cut. **Implementation cost:** MEDIUM
— the line-search-to-boundary step is easy to hand-code around the existing log g_a/log g_b
structure; SHOT itself (Lundell & Kronqvist's solver) is available as a standalone binary
callable from Pyomo/AMPL but not trivially from a pure scipy stack.

### 1.7 Logic-based Benders / combinatorial Benders cuts — the right theoretical frame for the connectivity loop
**Hooker, J.N., Ottosson, G. "Logic-based Benders decomposition." Mathematical Programming 96,
33-60 (2003).** DOI: 10.1007/s10107-003-0375-9 — VERIFIED.

**Codato, G., Fischetti, M. "Combinatorial Benders' Cuts for Mixed-Integer Linear
Programming." Operations Research 54, 756-766 (2006).** DOI: 10.1287/opre.1060.0286 —
VERIFIED.

These are the papers that formalize exactly what the current separator-cut loop is doing:
Hooker-Ottosson generalize Benders decomposition to any master/subproblem split where the
subproblem's infeasibility (here: "this x is disconnected") can be certified and turned into a
combinatorial cut (a "no-good"-style inequality, not a linear support hyperplane) added back
to the master. Codato-Fischetti specialize this to pure 0-1 MILP masters and show that
combinatorial Benders cuts (of the form: if these binaries take these values, some subset must
change) retain finite convergence because the master's feasible set is finite. **Guarantee
kept:** finite convergence via exhaustion of a finite combinatorial certificate set — *this is
the correct convergence theory for the connectivity cuts*, and it is a different theory from
OA's convex-cut argument (1.1-1.3). The two do compose (nothing prevents adding both cut
families to the same master), but the combined finite-iteration bound is the *product*, not the
sum, of each family's worst case — worth knowing (this echoes what CLAUDE.md already flags:
"both are inside one MINLP loop, not the same convergence theory"). **Effect on (a):** a
component-disconnection failure is precisely a logic-based-Benders infeasibility; formalizing
it this way suggests deriving a *stronger* aggregated cut per violated component (a single cut
ruling out "this whole set of nodes stays on one side while disconnected" rather than one weak
cut per violating edge-cut) — see 4.1. **Implementation cost:** LOW conceptually (it validates
the existing architecture) but MEDIUM to upgrade cut strength — requires identifying minimal
separators per Codato-Fischetti's "combinatorial" cut construction rather than ad hoc
edge-based separator cuts.

---

## 2. Separable-concave special case: can this become ONE certified MILP?

### 2.1 Direct precedent: MILP for maximum Nash welfare via piecewise-linear log
**Caragiannis, I., Kurokawa, D., Moulin, H., Procaccia, A.D., Shah, N., Wang, J. "The
Unreasonable Fairness of Maximum Nash Welfare." ACM Transactions on Economics and Computation
7(3), Article 12 (2019).** DOI: 10.1145/3355902 — VERIFIED.

Already cited in this project's HANDOFF for the EF1-at-d=0 theorem, but it also contains the
relevant algorithmic device: since integer *utilities* only take finitely many values, log can
be **lower-bounded by a piecewise-linear function that is exact at every integer point** —
turning "maximize log-welfare" into one MILP with a certified (in fact zero, at integral gain
values) approximation error, solved via `n` continuous log-proxy variables and per-value
binary/SOS constraints. Reported to solve 50-player instances in under 30 seconds and every
Spliddit instance in under 3 seconds. **Caveat for this problem:** that trick exploits gains
being sums of a *few* agents' *integer* per-item utilities (so the number of distinct
achievable gain values is small). Here g_a, g_b are sums of up to hundreds of continuous
unit values — the reachable-value set is not small or a priori enumerable, so the "exact at
integers" trick doesn't transfer directly; instead a **uniform-grid piecewise-linear
under-estimator of log with an a priori epsilon bound over the known range [g_min, S_a]** is
the right analogue (see 2.2). **Guarantee kept:** epsilon-certified (not exact) global optimum
of one MILP, no OA loop at all for the *welfare* nonlinearity. **Effect on (a)/(b)/(c):**
removes the OA cut loop as a source of (c)'s iteration blowup entirely — the tail-heaviness of
A_z/B_z would then only affect the granularity needed in the piecewise grid, not iteration
count, and combines cleanly with lazy connectivity cuts as the *only* remaining lazy family
(so the "two different convergence theories in one loop" problem in 1.7 disappears — only
logic-based Benders/connectivity cuts remain lazy). **Implementation cost:** MEDIUM — need
(a) a valid a priori range for g_a (bounded below by 0, above by S_a=sum A_z), (b) enough grid
breakpoints for the target epsilon (grid size ~ O(log(1/epsilon) * range/curvature) or use
Vielma-Nemhauser logarithmic encoding, 2.3, to keep the binary count small), (c) one
`python-mip`/CBC or HiGHS MILP with this piecewise-linear structure plus lazily added
connectivity cuts via callback.

### 2.2 Vielma & Nemhauser (2011) — logarithmic-size PWL encodings
**Vielma, J.P., Nemhauser, G.L. "Modeling disjunctive constraints with a logarithmic number of
binary variables and constraints." Mathematical Programming 128, 49-72 (2011).**
DOI: 10.1007/s10107-009-0295-4 — VERIFIED.

Gives SOS2/PWL formulations needing O(log k) binaries for a k-segment piecewise-linear
approximation instead of O(k), which matters once epsilon-accuracy on log g_a over its full
plausible range (0 to S_a, which could be in the thousands with heavy-tailed values) demands
many segments. **Guarantee kept:** same epsilon-certified PWL under/over-estimate as 2.1, just
far fewer added binaries — this directly blunts mechanism (c) (heavy tails inflating the
*range* that must be covered, hence segment count, hence binary count). **Effect on (a)/(b)/
(c):** primarily (c) and secondarily (b) (fewer binaries -> smaller MILP -> less likely to hit
node/time limits). **Implementation cost:** MEDIUM-HIGH to hand-implement correctly (the
"branching" encoding requires a careful Gray-code-like assignment of binary vectors to
segments) but there are existing open reference implementations (Pyomo's `Piecewise` component
supports a `LOG` representation out of the box — this is the lowest-effort path: Pyomo +
either HiGHS, CBC, or Gurobi as the backend MILP solver, no custom PWL code needed).

### 2.3 Product of two linear/concave functions: quasiconcavity and parametric/bisection alternatives
No single authoritative "product-of-two-linear-functions-over-a-polytope" algorithms paper
surfaced as directly on-point; the relevant facts are assembled from adjacent literature:

- **Quasiconcavity fact (multiple fractional-programming sources, e.g. surveys on linear
  fractional programming):** a product of two nonnegative concave functions is quasiconcave,
  but *maximizing* a quasiconcave function over a mixed-integer set is not automatically easy —
  quasiconcavity guarantees a single "improving direction" structure for *continuous* problems
  (bisection on the superlevel-set membership problem, a la Dinkelbach's algorithm for
  fractional programs) but the superlevel-set test itself, {x : g_a(x)*g_b(x) >= t}, is exactly
  as hard as the original combinatorial problem once integrality and connectivity are added
  back in — so bisection does not remove the connectivity difficulty, it only replaces "solve
  one MINLP" with "solve O(log(1/epsilon)) feasibility MILPs at fixed t." **UNVERIFIED as
  attributable to a specific canonical citation** for the 2-linear-term case; treat the
  quasiconcavity claim as folklore-level true but not independently sourced here.
- **Boland, Charkhgard, Savelsbergh (2015), Triangle Splitting Method.**
  DOI: 10.1287/ijoc.2015.0646 — VERIFIED ("A Criterion Space Search Algorithm for Biobjective
  Mixed Integer Programming: The Triangle Splitting Method," INFORMS Journal on Computing).
  This is the right formal tool for the "fix g_a >= t, maximize g_b" idea in the prompt: treat
  (g_a, g_b) as a **biobjective MIP** and run a criterion-space search that enumerates the
  Pareto frontier (or, cheaper, just enough of it to identify the Nash-welfare-maximizing
  point) via a sequence of epsilon-constraint MILPs, each of which is a *plain linear* MILP
  with hard connectivity constraints — no nonlinear objective ever appears, and log-welfare is
  applied only as a *scalar selection rule* over the finite Pareto set once computed.
  **Guarantee kept:** if the full nondominated frontier is enumerated, the Nash-welfare optimum
  over it is exact (not epsilon-certified — genuinely exact, since evaluating log(g_a)+log(g_b)
  over a finite point set requires no approximation). **Effect on (a)/(b)/(c):** turns off the
  nonlinear-OA machinery entirely; the frontier for a 2-objective problem with n zips has at
  most O(n) breakpoints in the best case but can be large in the worst case (every zip
  reassignment changes both g_a and g_b), so this trades "OA rounds" for "epsilon-constraint
  MILP solves," each of which *does* need to handle connectivity — meaning it does not remove
  mechanisms (a)/(b), only reframes them as repeated plain-MILP-with-hard-contiguity solves.
  Most useful as a **verification/audit tool** (cheaply confirm the OA solution is frontier-
  optimal) rather than a wholesale replacement. **Implementation cost:** MEDIUM — needs a
  biobjective search loop on top of whatever MILP+lazy-connectivity solver is chosen; the
  paper's own reference implementation targets CPLEX but the algorithm is solver-agnostic.

---

## 3. Kelley cutting-plane instability on flat objectives (root cause of "17-round thrash" at rho=0)

### 3.1 Level method — proximal stabilization of the cutting-plane master
**Lemaréchal, C., Nemirovskii, A., Nesterov, Y. "New variants of bundle methods."
Mathematical Programming 69, 111-148 (1995).** DOI: 10.1007/BF01585555 — VERIFIED.

Diagnoses precisely the failure mode reported here: plain Kelley cutting planes (add a tangent
at the current best point, resolve, repeat) can zigzag and converge arbitrarily slowly when the
objective is *nearly flat/degenerate near optimum* — because the master has almost no
information forcing the next trial point away from ties, each new cut only marginally improves
the polyhedral approximation. The **level method** fixes this by choosing the next trial point
not as the master's unconstrained optimum but as the point in a "level set" (objective within a
target gap of the current best bound) closest to the previous iterate — a proximal/projection
step that provably achieves the best known complexity bounds for nonsmooth convex optimization
and empirically avoids the zigzag. **Guarantee kept:** still globally convergent with a
provable iteration-complexity bound (better than plain Kelley's, which has no useful worst-case
bound). **Effect on (a)/(b)/(c):** targets the *exact* symptom described ("objective nearly
flat, many near-tied allocations, loop thrashed 17 rounds") — this is squarely a rho=0 flatness
problem, and the level method (or the simpler in-out variant, 3.2) is the standard fix.
**Implementation cost:** MEDIUM — requires adding a small QP or a second LP (projection step)
each iteration; can piggyback on the existing HiGHS MILP master by solving an auxiliary
projection subproblem, no new solver dependency needed.

### 3.2 In-out separation — cheaper stabilization, easier to retrofit
**Ben-Ameur, W., Neto, J. "Acceleration of cutting-plane and column generation algorithms:
Applications to network design." Networks 49(1), 3-17 (2007).**
DOI: 10.1002/net.20137 — VERIFIED.

A lighter-weight alternative to the level method: instead of separating (adding a cut) at the
master's raw optimum, separate at a point on the segment between the current *interior* stable
point and the master's optimum ("in-out"), moving the stable point only when it improves.
Proven convergent under general assumptions and empirically much faster than plain Kelley on
degenerate/flat instances, with far less implementation overhead than a full bundle/level
method (just a convex combination step, no extra QP). **Effect on (a)/(b)/(c):** same target as
3.1 (flat-objective thrash) at lower engineering cost — **this is the more practical first
thing to try** given the existing scipy/HiGHS-based codebase, since it needs only a line-search
between two known points, not a new subproblem type.

### 3.3 Fischetti & Salvagnin (2010) — in-out applied specifically to disjunctive/MIP master loops
**Fischetti, M., Salvagnin, D. "An In-Out Approach to Disjunctive Optimization." In:
Integration of AI and OR Techniques in Constraint Programming for Combinatorial Optimization
Problems (CPAIOR 2010), LNCS vol. 6140, pp. 136-140. Springer (2010).**
DOI: 10.1007/978-3-642-13520-0_17 — VERIFIED.

Applies the in-out idea (3.2) concretely to a branch-and-cut master where cuts are generated
lazily against a combinatorial/disjunctive feasible set — i.e., the same architecture as this
problem's connectivity-cut loop, not just the smooth-nonlinear OA loop. Confirms the in-out
stabilization is not limited to convex NLP cutting planes; it applies equally to Benders-style
combinatorial cut generation (ties back to 1.7). **Effect on (a):** most directly relevant of
the stabilization papers to the "unconstrained optimum already disconnected" failure, since
stabilizing *which* fractional/integer point gets separated for connectivity could avoid
oscillating between two disconnected near-tied partitions. **Implementation cost:** LOW-MEDIUM,
same mechanics as 3.2, just applied to the connectivity-separator step instead of (or in
addition to) the OA step.

---

## 4. Cut-loop engineering

### 4.1 Aggregated vs. per-edge separator cuts; the districting-specific literature is the strongest source here
**Validi, H., Buchanan, A., Lykhovyd, E. "Imposing Contiguity Constraints in Political
Districting Models." Operations Research 70(2), 867-892 (2022).**
DOI: 10.1287/opre.2021.2141 — VERIFIED.

This is the single most directly-relevant paper found for the engineering questions in the
prompt, because it solves *the same subproblem* (hard contiguity on a planar adjacency graph,
via lazy branch-and-cut) at real US-census scale (tract-level, tens of thousands of units,
dozens of districts) with an open-source-friendly formulation. Key findings transferable here:
(i) a **cut-based model with lazily generated connectivity cuts, separated by min-cut/max-flow
per candidate violating component**, dominates flow-based "always-on" contiguity formulations
(Shirabe 2005/2009, see 4.2) at scale, because flow variables add O(n^2) continuous variables
that bloat the LP relaxation even when contiguity isn't binding; (ii) contiguity does **not**
provably increase worst-case hardness of the districting problem (the paper's central
theoretical claim) — consistent with this project's mechanism-(a)/(b) diagnosis being about
*solver engineering*, not inherent intractability; (iii) they report that adding **one
aggregated cut per minimal violating component (via a min s-t cut computation)** rather than
one weak cut per boundary edge is what makes the lazy loop practical at scale — this directly
answers the prompt's "aggregated per-island vs. per-unit cut" question in favor of aggregation;
(iv) their branch-and-cut is implemented as **lazy constraints inside a single Gurobi tree**,
i.e., the same single-tree architecture recommended in 1.3, not a multi-tree re-solve loop.
**Guarantee kept:** exact contiguity, provable optimality via branch-and-cut with valid lazy
cuts (finite by the Codato-Fischetti argument, 1.7). **Effect on (a)/(b)/(c):** (a) their
min-cut-based separation directly detects the "free-Nash optimum already disconnected" case in
one shot rather than iteratively; (b) single-tree + aggregated cuts is the standard remedy for
scale beyond 125 units; (c) not addressed (their objective is compactness-based/linear, not
Nash-welfare, so heavy-tailed values don't interact with their cut engineering) — this remains
an open gap. **Implementation cost:** MEDIUM-HIGH — reference C++ code and instances are public
(GitHub `zhelih/districting`) but porting the cut-generation logic (min s-t cut per violating
side using e.g. `networkx.minimum_cut` on the fractional-support subgraph, added as a lazy
constraint) to a Python callback loop with PySCIPOpt, python-mip/CBC, or OR-Tools CP-SAT is a
non-trivial but well-specified engineering task; this is the **most actionable single paper**
for the "fix contiguity convergence" priority in this project's CLAUDE.md.

### 4.2 Shirabe (2005, 2009) — the flow-based alternative, useful as a contrast/fallback
**Shirabe, T. "A Model of Contiguity for Spatial Unit Allocation." Geographical Analysis 37(1),
2-16 (2005).** DOI: UNVERIFIED (Crossref lookup not attempted for this record — Geographical
Analysis DOI prefix is 10.1111/j.1538-4632.2005.00605.x per publisher listings, but this was
not independently confirmed against Crossref in this session; treat as UNVERIFIED until
checked).

**Shirabe, T. "Districting Modeling with Exact Contiguity Constraints." Environment and
Planning B: Planning and Design 36(6) (2009).** DOI: 10.1068/b34104 — VERIFIED.

Shirabe's flow-based contiguity formulation (each unit ships one unit of flow to/from a
designated "root" within its district; a unit is only feasibly assigned if flow can reach it)
imposes contiguity as an **always-on MILP constraint set**, not a lazily generated cut — no
separation loop needed at all, at the cost of O(n) extra continuous flow variables and O(n)
extra constraints per side, per candidate root. **Guarantee kept:** exact contiguity by
construction, single MILP solve (no lazy loop). **Effect on (a)/(b)/(c):** removes mechanism
(a)/(b)'s *cut-loop-divergence* risk entirely (there's no loop to diverge) but at the cost of
a much bigger single MILP — Validi-Buchanan-Lykhovyd (4.1) report this becomes the bottleneck
above roughly a few hundred units, i.e., right around this project's target scale of 400-800.
**Recommendation:** worth prototyping as a **sanity-check baseline** (cheap to implement, no
callback machinery needed) even though 4.1's lazy cut-based method is expected to win at the
800-unit end of the target range.

### 4.3 Warm-starting across OA/cut rounds
No dedicated citation found specifically for "warm-starting HiGHS/CBC with previous incumbent
across OA rounds" as a standalone theoretical contribution — this is standard MILP-solver
practice (documented in HiGHS's and CBC's own API docs, not academic literature) rather than a
citable algorithmic result. **UNVERIFIED / not a literature claim**: flagged here only as an
engineering note — both `highspy` and `python-mip`/CBC accept a starting solution
(`MipStart`/`.start`) and warm-starting the LP basis is supported by HiGHS's `basis` I/O. This
is low-cost regardless of which solver is chosen in 1.3/4.1's recommendations and should be
adopted as a matter of course, not treated as requiring separate research justification.

---

## 5. Heavy-tailed coefficients and MILP hardness (mechanism (c))

### 5.1 Pisinger (2005) — hard knapsack instance construction via coefficient structure
**Pisinger, D. "Where are the hard knapsack problems?" Computers & Operations Research 32(9),
2271-2284 (2005).** DOI: 10.1016/j.cor.2004.03.002 — VERIFIED.

Directly relevant analogy: this paper shows knapsack-type 0-1 problems become dramatically
harder for both dynamic programming and branch-and-bound when instance values/weights are
constructed with specific *correlation and coefficient-magnitude* structure (e.g., strongly
correlated weight/value pairs, or a small number of large "outlier" coefficients dominating the
rest) — hardness is driven by how the LP relaxation's fractional optimum sits relative to the
integer hull, not by problem size alone. The connectivity-Nash MILP's per-node "value" terms
(A_z, B_z) function like knapsack-style coefficients inside each OA-cut's linear expression;
moving from lognormal to double-Pareto-lognormal (heavier tail, C9 in this project's battery)
plausibly reproduces Pisinger's "hard instance" structure — a few dominant-value nodes create
near-degenerate LP relaxations where many fractional solutions are close in objective value,
which (i) inflates OA/Kelley iteration counts (ties to Section 3's flatness diagnosis, since a
few huge-value nodes swinging between sides barely changes the *aggregate* log-welfare) and
(ii) makes branch-and-bound's bounding weaker (large coefficients on some binaries widen the LP
gap). **Guarantee kept:** none — this is a hardness *diagnosis*, not an algorithm.
**Effect on (a)/(b)/(c):** speaks directly to (c); the standard mitigations documented in the
knapsack-hardness literature (coefficient *scaling/rounding* before solving, and separately
handling the small set of high-value "dominant" nodes as fixed/pre-decided rather than let the
MILP branch on them) are testable, low-cost experiments: pre-assign the top-k highest-A_z/B_z
nodes by a cheap heuristic (e.g., greedy or the existing prefix heuristic already in this
project's appendix) and let the MILP handle only the remaining low/medium-value "long tail"
combinatorially. **Implementation cost:** LOW to test as a heuristic warm-start/fixing scheme;
does not require a solver change.

### 5.2 No literature found specifically on "product-of-two-sums" objectives under heavy tails
Targeted search for papers combining (heavy-tailed coefficient distributions) x (Nash-welfare
or bilinear/product objectives) x (MILP hardness) returned nothing on-point beyond the general
knapsack-hardness literature in 5.1 and the generic Nash-welfare-MILP literature in 2.1. This
combination — bilinear/log-separable objective *plus* adversarial coefficient tails *plus*
hard connectivity — appears to be a genuine gap; flagged as an open question below rather than
force-fit to a tangential citation.

---

## Ranked shortlist (top 5) for this problem

1. **Single-tree LP/NLP-based branch-and-bound (Quesada & Grossmann 1992, DOI
   10.1016/0098-1354(92)80028-8), implemented via PySCIPOpt or python-mip/CBC lazy
   constraints, generating BOTH the OA log-welfare cuts and the connectivity separator cuts as
   lazy constraints inside one tree.** Rationale: directly eliminates the "fresh MILP every
   round" cost that is the proximate cause of mechanism (b), and is the architecture every
   later paper in this survey (Bonami 2008, Kronqvist review 2019, Validi-Buchanan-Lykhovyd
   2022) converges on as best practice.

2. **Piecewise-linear-log MILP replacing the OA loop for the welfare objective (Caragiannis et
   al. 2019 idea, DOI 10.1145/3355902, with logarithmic-size encoding per Vielma & Nemhauser
   2011, DOI 10.1007/s10107-009-0295-4), leaving connectivity as the ONLY lazy cut family.**
   Rationale: removes the "two different convergence theories in one loop" hazard this
   project's own CLAUDE.md flags, and directly targets mechanism (c) by decoupling
   welfare-precision (a grid-size choice) from OA-iteration count.

3. **Min-cut-based aggregated connectivity separation, one cut per violating component, in a
   single branch-and-cut tree (Validi, Buchanan & Lykhovyd 2022, DOI 10.1287/opre.2021.2141).**
   Rationale: this is a proven, at-scale (tens of thousands of units), open-methodology
   solution to the *exact* subproblem (hard contiguity, lazy cuts, planar adjacency) at a scale
   well beyond this project's 400-800-unit target; their component-quotient-style disconnection
   handling also validates this project's own proposed "fixer" for mechanism (a).

4. **In-out stabilization of whichever cutting-plane loop remains (Ben-Ameur & Neto 2007, DOI
   10.1002/net.20137, or Fischetti & Salvagnin 2010, DOI 10.1007/978-3-642-13520-0_17).**
   Rationale: cheapest possible fix (a line-search between two known points, no new solver or
   subproblem type) directly targeting the reported symptom — "objective nearly flat... loop
   thrashed 17 rounds" — before investing in the heavier rewrites above.

5. **Flow-based always-on contiguity (Shirabe 2009, DOI 10.1068/b34104) as a small-instance
   sanity baseline, not a production fix.** Rationale: no lazy-cut machinery needed at all, so
   it is useful to validate that any new lazy-cut implementation (items 1 and 3) reproduces the
   same optimum on small/medium cases where the flow formulation is still tractable, per
   Validi-Buchanan-Lykhovyd's own reported crossover point.

---

## Could not verify / open questions

- **Shirabe (2005) DOI** — publisher-listed DOI (10.1111/j.1538-4632.2005.00605.x pattern) was
  not independently confirmed against Crossref in this session. UNVERIFIED; the 2009 companion
  paper (10.1068/b34104) was independently verified and covers the same formulation, so this
  gap is low-stakes.
- **Quasiconcavity / bisection argument for max g_a*g_b via epsilon-constraint on t** (Section
  2.3) — the underlying fact (product of two nonnegative concaves is quasiconcave) is
  standard folklore in fractional/generalized-concave programming, but no single canonical
  citation directly proving it for *this* two-linear-term, mixed-integer-constrained case was
  found and verified; treat the framing as sound intuition, not a sourced theorem, and rely on
  Boland-Charkhgard-Savelsbergh's biobjective-MIP machinery (verified) as the rigorous version
  of the same idea.
- **No source found combining heavy-tailed coefficients with bilinear/Nash-welfare MILP
  hardness specifically** (Section 5.2) — the mechanism (c) diagnosis here is an *analogy* to
  general knapsack-hardness results (Pisinger 2005), not a directly-on-point paper. If this
  project wants a rigorous hardness explanation for C9's specific behavior, that appears to be
  original analysis, not something retrievable from existing literature.
- **Warm-starting across OA/lazy-cut rounds** (Section 4.3) is solver-documentation-level
  practice, not an academic citation; flagged as UNVERIFIED-as-a-literature-claim, included
  only as an implementation note.
- **Hooker/Ruthmair-style "lazy cut generation" search for redistricting** turned up King,
  Jacobson & Sewell (2017/2018, DOI 10.1007/s10589-017-9936-3, "The geo-graph in practice:
  creating United States Congressional Districts from census blocks," Computational
  Optimization and Applications) instead of the originally guessed author — verified as a real,
  relevant paper on the geo-graph model for enforcing contiguity at scale, but not read in
  depth for this survey; flagged in case a follow-up pass wants to mine it further for
  cut-engineering detail beyond what 4.1 already provides.
