# Literature — optimization — the band-constrained Eisenberg–Gale certificate (`EG^bal_S`)

**Date:** 2026-09-03 · **Framework:** 0.1 · **Track:** A1 (branch `wt/A1`) ·
**Reads:** `docs/tracks/A1/DOMAIN_optimization.md` §6 (2026-09-03; every `§2.x` reference below is to that A1 copy, not to the hub's `docs/DOMAIN_optimization.md`), with context from `docs/APPROACHES.md` §A1,
`docs/LENS_GROMOV.md` (2026-09-03), `docs/MODEL_U1-cert.md` §6, `docs/FRAME.md` §6 ·
**Queries logged:** 56 (19 Consensus conceptual/near-title · 4 WebSearch · 28 Crossref near-title
resolutions · 5 OpenAlex citation-graph walks) · **DOIs resolved:** 46/46 (Crossref, 2026-09-03;
retraction flag checked on the two most load-bearing via OpenAlex — both clean) ·
**Deduplicated against:** `docs/RESEARCH_ADDITIONS.bib`, `docs/LIT_economic-theory.bib`,
`docs/channel_note/references.bib`, `docs/RESEARCH_FINDINGS.md`.

> **Where the entries live.** `docs/LIT_optimization.bib` — 46 entries, tiered by tag, ready to
> merge. The brief asked for an append to `docs/RESEARCH_ADDITIONS.bib`; the editing tool available
> to this run could only overwrite that 522-line tracked file wholesale, which was judged an
> unacceptable clobber risk, so the entries follow the project's own sibling convention
> (`docs/LIT_economic-theory.bib`) instead. **No key in `LIT_optimization.bib` appears in any of the
> other three `.bib` files** (checked by grep across `docs/`), so they concatenate cleanly and
> folding the additions into `RESEARCH_ADDITIONS.bib` later needs no renaming — append everything
> after its header block.

**Priority worked in the brief's order** — Q1, Q2, Q4, Q5 to depth; Q6 to depth; Q3, Q7, Q8, Q9 at
one fan-out plus targeted resolution. **Stopped at:** the Consensus quota (3 searches remaining at
finish), before a second forward citation walk on `budish2013` and `borgwardt2019`. Those two walks
are the first thing to do if this brief is re-opened.

---

## 0. Headlines — what changes the plan

- **`EG^bal_S` is a named object, and the name is "Eisenberg–Gale market."** `jainvazirani2010`
  defines an *EG convex program* as **any** program `max Σ_i m_i log u_i` with `u` linearly
  constrained; `im2018` is the same object as *proportional fairness over a polytope*, and
  `kelly1998` (already in our bib) is the canonical instance. **§2.10 is a citation plus one solve,
  not a construction.** `MODEL_U1-cert` §8.2's "a new solve path is required" stands, but the
  *object* needs no defence.
- **But the price reading does not survive intact, and this is the sharpest finding.**
  `jalota2023` proves that once agents carry *their own* linear constraints, the EG optimum is
  **no longer a market equilibrium at the stated budgets** — equilibrium is recovered only after a
  fixed-point *perturbation of the budgets*. So §2.10's `q_{zi} = p_z + ν_i M_z` is sound as a
  **KKT/multiplier** statement and must **not** be published as "an agent-specific competitive
  price" without the budget-perturbation caveat. The CEEI reading goes to economic-theory (§7 row 1)
  with `jalota2023` attached. `he2018`'s *priority-specific prices* is the nearest thing to a
  legitimate agent-specific-price precedent, and it buys its legitimacy by a different route.
- **U15 needs no new mathematics.** `lenstra1990`'s extreme-point lemma (support of a vertex of the
  assignment LP is a pseudoforest ⇒ fewer fractionally assigned units than agents) is the canonical
  `≤ k−1`; `shmoystardos1993` is the same argument with one extra side row per agent; the
  general accounting "`#fractional ≤ #tight side rows`" is the **rank lemma** of `lauravisingh2011`
  Ch. 2 and `bansal2012`. **`math-verify` should cite this pattern rather than re-derive it**
  (`MODEL_U1-cert` §8.4 closes). What is *not* citable is the sharp `≤ 2k−1`, which depends on our
  budget-identity dependency — that stays a `[claim]`.
- **Q4 has a theorem, and our band fails its hypothesis.** `budish2013` characterises exactly when
  a fractional allocation decomposes into integral ones satisfying **the same** constraints:
  *bihierarchy*. Our band is a **weighted** per-agent constraint (`Σ_z M_z x_{zi}` in dollars, not a
  count), which is outside the bihierarchy class, so **§2.13's 325-binary MIP is not avoidable by a
  rounding theorem** — D2′ must be decided computationally. The fallbacks are `akbarpour2020`
  (downgrade the band from constraint to *goal*, get it approximately) and `gandhi2006`
  (dependent rounding: per-agent sums preserved to within one item, unweighted).
- **Q5 returns nothing, and that is a result.** No published submodularity, subadditivity or
  concave-envelope bound for `S ↦ EG_S`. `chakrabarty2014` is submodularity of the *feasible-set*
  function inside an EG program, not of the agent set; `mavrov2023` maximises a smoothed Nash
  welfare over size-`k` constrained committees but the welfare is over *voters*, not over the
  selected set. **§8 Q11's answer is "no" — (★) is a small original result**, and §2.14 should be
  written as such. Compute it first (§5 row 0a), then claim it.

---

## 1. Q1 — Eisenberg–Gale / Fisher markets with per-agent quantity or capacity constraints

**Verdict: yes, it is a named object; (a) the equilibrium reading survives only with a caveat;
(b) existence is a theorem for the polytope class; (c) an algorithm accepting side constraints
exists but is not a clean proportional-response drop-in.**

**Jain, K. & Vazirani, V. V.** *Eisenberg–Gale Markets: Algorithms and Game-Theoretic Properties.*
Games and Economic Behavior 70(1):84–106, 2010 · DOI `10.1016/j.geb.2008.11.011`
> Defines the class of **EG markets**: any convex program `max Σ_i m_i log u_i` in which the
> constraints on the utilities `u` are linear. Obtains combinatorial ascending-price algorithms for
> several members, and classifies the class by efficiency, fairness, competition monotonicity and
> *rationality of equilibria* — showing a "surprisingly rich set of possibilities", i.e. not all EG
> markets behave like linear Fisher.
> **Bears on §2.10.** This is the name for `EG^bal_S`: our band adds `2k` linear rows on the
> district masses, which are linear in `x` and hence linear in the `u`-defining data. The
> convexity, Slater and strong-duality claims of §2.10 are the class's standard properties, and
> `math-verify` should cite rather than re-prove them. It also warns that the *good* structural
> properties of linear Fisher (rationality, combinatorial algorithms) do **not** transfer for free.
> `foundation`

**Jalota, D., Pavone, M., Qi, Q. & Ye, Y.** *Fisher markets with linear constraints: equilibrium
properties and efficient distributed algorithms.* Games and Economic Behavior 141:223–260, 2023 ·
DOI `10.1016/j.geb.2023.06.007` · (OpenAlex `W4382395702`, not retracted, checked 2026-09-03)
> The exact model: a Fisher market where **each agent carries additional linear constraints**
> beyond budget and good-capacity. Shows this "fundamentally alters the properties of the market
> equilibrium as well as the optimal allocations" — in particular the EG optimum is not an
> equilibrium at the original budgets. Introduces the **budget-perturbed social optimisation
> problem** (BP-SOP), prices from BP-SOP's capacity duals, a fixed-point iteration for the
> perturbations (convergence shown numerically), and an ADMM scheme with convergence guarantees for
> *homogeneous* linear constraints.
> **Bears on §2.10's price reading, §2.12's "exchange rate", and §7 row 1.** It answers Q1(a)
> **negatively in the strong form**: `q_{zi} = p_z + ν_i M_z` is a KKT multiplier expression, not a
> competitive price, unless budgets are perturbed. It answers Q1(c) **positively but weakly**:
> ADMM/tâtonnement does accept the side constraints, at the cost of an outer fixed point. This is
> the single entry that most changes what §2.12 is allowed to say to a sponsor.
> `contradicts-or-sharpens`

**Im, S., Kulkarni, J. & Munagala, K.** *Competitive Algorithms from Competitive Equilibria.*
Journal of the ACM 65(1):3, 2017 · DOI `10.1145/3136754`
> Establishes **proportional fairness** — the EG/Nash solution — as the organising object for
> allocation over an arbitrary downward-closed **polytope** of feasible rates, and derives
> competitive scheduling algorithms from the equilibrium's properties.
> **Bears on §2.10 and §2.11.** Confirms the class-level result that the EG optimum over a general
> polytope retains the fairness and KKT structure; supplies the "polytope scheduling" vocabulary
> under which the frontier `δ ↦ EG^bal(δ)` is legible to an OR audience.
> `foundation`

**Jäger, S., Lindermayr, A. & Megow, N.** *The Power of Proportional Fairness for Nonclairvoyant
Polytope Scheduling.* SIAM Journal on Computing 55(2):247–279, 2026 ·
DOI `10.1137/25m1763974`
> Current frontier for proportional fairness (`Σ log`) over polytopal feasible sets; sharpens the
> guarantees of `im2018`.
> **Bears on §2.11.** Cite only if the frontier's shape needs literature context; it is the live
> edge of the polytope-EG thread and confirms the thread is not dormant.
> `frontier`

**Garg, J., Tao, Y. & Végh, L. A.** *Approximating Equilibrium under Constrained Piecewise Linear
Concave Utilities with Applications to Matching Markets.* SODA 2022, 2269–2284 ·
DOI `10.1137/1.9781611977073.91`
> Algorithms for approximate equilibrium in markets with **constrained** piecewise-linear-concave
> utilities, i.e. the computational side of the constrained-EG object.
> **Bears on §2.11's "not on the path" list and on `MODEL_U1-cert` §8.2.** This is the closest
> published answer to "is there a combinatorial algorithm that accepts side constraints": yes,
> approximate, and for a different constraint family. It does not replace §2.11's OA route.
> `tool-we-lack`

**Chaudhury, B. R., Kroer, C., Mehta, R. & Nan, T.** *Competitive Equilibrium for Chores: from Dual
Eisenberg–Gale to a Fast, Greedy, LP-based Algorithm.* EC '24, p. 40 · DOI `10.1145/3670865.3673516`
> A greedy **Frank–Wolfe** method over an EG-shaped program in which **each iteration solves only a
> simple LP**; reports 5–20 iterations on every instance tried, including a real paper-bidding
> dataset, and explicitly notes it is the first highly practical method for its class.
> **Bears on §2.11 and §5 row 1 — this is the closest operational precedent for the primary route.**
> Our OA/tangent master is a different LP-only architecture, but the message transfers: LP
> subproblems on an EG objective converge in tens of iterations at real scale, and the paper gives
> the convergence-rate language to justify the design. Also directly relevant to Q6.
> `tool-we-lack`

**Birnbaum, B., Devanur, N. R. & Xiao, L.** *Distributed algorithms via gradient descent for Fisher
markets.* EC '11, 127–136 · DOI `10.1145/1993574.1993594`
> Shows **proportional response dynamics is mirror descent** (Bregman gradient descent) on a convex
> program capturing linear-Fisher equilibria, with an `O(1/t)` rate under a weakened smoothness
> condition, and extends it to spending-constraint utilities.
> **Bears on `MODEL_U1-cert` §8.2's failure mode (i).** It explains *why* PR does not take side
> constraints — it is unconstrained mirror descent on a specific geometry — and names the repair
> (projected/constrained mirror descent), which is the cheapest thing to try before the OA master
> if §2.11's loop misbehaves.
> `foundation`

**Low, S. H. & Lapsley, D. E.** *Optimization flow control — I: basic algorithm and convergence.*
IEEE/ACM Transactions on Networking 7(6):861–874, 1999 · DOI `10.1109/90.811451`
> Dual gradient-projection algorithm for `max Σ_r U_r(x_r)` subject to **linear capacity rows**,
> with the link multipliers as prices; asynchronous convergence proof.
> **Bears on §2.11 and §2.12.** The canonical demonstration that a `Σ log` program with linear
> capacity constraints has a decentralised dual algorithm whose multipliers *are* the operational
> prices — the engineering precedent for reading `ν_i` as an exchange rate, and a cheap alternative
> solve path at 16k variables. Pairs with `kelly1998`, already in our bib.
> `foundation`

**Echenique, F., Miralles, A. & Zhang, J.** *Constrained Pseudo-Market Equilibrium.* American
Economic Review 111(11):3699–3732, 2021 · DOI `10.1257/aer.20201769` · (OpenAlex `W2973080784`,
not retracted, checked 2026-09-03)
> Pseudo-market (CEEI-style) equilibrium under **general linear constraints**. Constraints generate
> pecuniary externalities internalised via prices: agents pay in proportion to how much their
> purchase tightens the binding constraints. The outcome is *constrained*-efficient, and fair to the
> extent the constraints treat agents symmetrically.
> **Bears on §2.10 and on §7 row 1.** The nearest published relative of `EG^bal_S` on the
> economics side, superseding `budish2011` as "the nearest thing in our bib". Its
> "pay for the constraint you tighten" reading is precisely our surcharge `ν_i M_z`, and its
> symmetry proviso is the honest caveat: our band treats all 13 districts symmetrically, so the
> fairness reading is available — but see `jalota2023` before asserting it.
> `foundation`

**Kroer, C. & Peters, D.** *Computing Lindahl Equilibrium for Public Goods with and without Funding
Caps.* EC '25, p. 129 · DOI `10.1145/3736252.3742510`
> In the *capped* setting each good has an upper bound on the funding it can absorb; existence was
> previously only via fixed points. Shows a **new convex program continues to work when the cap
> constraints are added**, and its optima are equilibria — resolving a long-standing open question.
> **Bears on §2.10's structural optimism.** The best recent evidence that adding capacity caps to a
> Nash-welfare convex program preserves both computability and the equilibrium reading. Caps are on
> *goods* there and on *agents* here, so it is an analogy, not a citation for our case.
> `frontier`

**Miralles, A. & Pycia, M.** *Foundations of pseudomarkets: Walrasian equilibria for discrete
resources.* Journal of Economic Theory 196:105303, 2021 · DOI `10.1016/j.jet.2021.105303`
> First and Second Welfare Theorems for assignment without transfers under **any linear
> constraints**, despite failure of local non-satiation.
> **Bears on §7 row 1.** The licence for talking about `EG^bal_S`'s optimum in welfare terms at all
> under a band; hand to economic-theory rather than cite here.
> `foundation`

**He, Y., Miralles, A., Pycia, M. & Yan, J.** *A Pseudo-Market Approach to Allocation with
Priorities.* American Economic Journal: Microeconomics 10(3):272–314, 2018 · DOI `10.1257/mic.20150259`
> Agents face **priority-specific prices** — one good, several prices, depending on the agent's
> class — and buy utility-maximising random assignments; the result is fair and constrained-Pareto
> efficient.
> **Bears on §2.10's `q_{zi}` and §2.12.** The clearest published precedent for an *agent-specific
> effective price* in a market-design setting, and a demonstration that it can be defended. Note the
> difference: their price differentiation is exogenous (priority class), ours is endogenous (which
> side of the band the district sits on).
> `contradicts-or-sharpens`

---

## 2. Q2 — support / split-unit bounds for constrained equilibria, and the canonical `≤ k−1`

**Verdict: the canonical citation exists and is not from the market literature; the
"`+ #tight side rows`" generalisation is standard iterative-rounding accounting; the sharp
`≤ 2k−1` is ours.**

**Lenstra, J. K., Shmoys, D. B. & Tardos, É.** *Approximation algorithms for scheduling unrelated
parallel machines.* Mathematical Programming 46(1–3):259–271, 1990 · DOI `10.1007/bf01585745`
> The extreme-point lemma: any vertex of the natural assignment LP has a **pseudoforest** support
> graph, hence **strictly fewer fractionally assigned jobs than machines**, which is what makes the
> `(2)`-approximation rounding work.
> **Bears on `MODEL_U1-cert` §8.4, §2.10's U15 and §5 row 0a.** *This is the canonical citation the
> brief asks for.* `brieden2017` Lem. 4 is the clustering-flavoured restatement; LST is the source
> and is what `math-verify` should cite so the `≤ k−1` count is retired from the proof burden. The
> pseudoforest phrasing also gives the right mental model for what the band does: it adds rows, so
> it adds edges the forest may carry.
> `foundation`

**Shmoys, D. B. & Tardos, É.** *An approximation algorithm for the generalized assignment problem.*
Mathematical Programming 62(1–3):461–474, 1993 · DOI `10.1007/bf01585178`
> Extends LST to the generalised assignment problem: each machine carries an extra **capacity row**,
> and the extreme-point/rounding argument survives with the count degraded by the number of extra
> rows.
> **Bears directly on §2.10's U15 and §2.13's problem size.** This is the published instance of
> "`≤ k−1 + #tight side rows`" in the form nearest our band: one linear resource row per agent,
> weighted (processing times, not counts) — exactly our `Σ_z M_z x_{zi}`. **The coarse `≤ 2k` is a
> corollary of this pattern, not a new bound.**
> `foundation`

**Lau, L. C., Ravi, R. & Singh, M.** *Iterative Methods in Combinatorial Optimization.* Cambridge
University Press, 2011 · DOI `10.1017/cbo9780511977152`
> The **rank lemma**: at a vertex of `{x : Ax ≤ b, x ≥ 0}` the number of nonzero coordinates equals
> the rank of the tight constraint system. Whole book is the machinery for turning that into
> rounding guarantees.
> **Bears on §2.10's coarse count and on §2.13.** The one-line justification for "`n` supply rows +
> `k` gain rows + `≤ k` tight band rows ⇒ `≤ n + 2k` nonzeros". A survey/textbook, included under
> the `foundation` exception because it is the standard reference for the counting argument.
> `foundation`

**Bansal, N., Khandekar, R., Könemann, J., Nagarajan, V. & Peis, B.** *On generalizations of network
design problems with degree bounds.* Mathematical Programming 141(1–2):479–506, 2012 ·
DOI `10.1007/s10107-012-0537-8`
> Extends iterative relaxation to *laminar crossing* degree constraints and to matroid intersection
> and lattice polyhedra; gives additive hardness showing the "+ #side rows" degradation is
> essentially unavoidable in general.
> **Bears on §2.10's U15 as a warning.** If a future variant of the band is nested (regional bands
> inside the national band), the accounting is laminar and this is the reference; it also says the
> additive loss cannot be beaten in general, so the `≤ 2k−1` sharpening buys the last unit only
> because of our budget identity.
> `frontier`

**Chakrabarty, D., Devanur, N. R. & Vazirani, V. V.** *Rationality and Strongly Polynomial
Solvability of Eisenberg–Gale Markets with Two Agents.* SIAM Journal on Discrete Mathematics
24(3):1117–1136, 2010 · DOI `10.1137/070693072`
> Two-agent EG markets are **rational** (rational equilibria exist) and strongly polynomially
> solvable when the feasible-utility polytope has a combinatorial LP description; the general EG
> class is *not* known to be rational, per `jainvazirani2010`.
> **Bears on §2.10's failure mode (ii) and on `math-verify`.** A caution: the tidy support and
> rationality structure of linear Fisher is a *special-case* property, not an EG-class property. Do
> not assume `EG^bal_S`'s optimum has rational coordinates or a canonical support; the
> vertex-dependence discipline (`MODEL_U1-cert` failure mode 9) is not paranoia, it is the class's
> known behaviour.
> `contradicts-or-sharpens`

---

## 3. Q3 — perturbation / comparative statics of the constrained EG value function

**Verdict: continuity and generic differentiability in the *market data* are published; nothing
characterises the shape of the value function in a *capacity parameter*. See absence ledger row C.**

**Megiddo, N. & Vazirani, V. V.** *Continuity Properties of Equilibrium Prices and Allocations in
Linear Fisher Markets.* WINE 2007, LNCS 4858:362–367 · DOI `10.1007/978-3-540-77105-0_39`
> Equilibrium prices are continuous in the market data (budgets, utilities); allocations are not,
> in general.
> **Bears on §2.11 and §2.12's degeneracy caveat.** The published statement of what is and is not
> stable in an EG optimum. It supports quoting the *prices* `p_z` across a `δ` grid and warns
> against quoting the *allocation*/first-mover list without the two-solver intersection discipline
> §2.12 already imposes.
> `foundation`

**Bonnisseau, J.-M., Florig, M. & Jofré, A.** *Differentiability of Equilibria for Linear Exchange
Economies.* Journal of Optimization Theory and Applications 109(2):265–288, 2001 ·
DOI `10.1023/a:1017558204399` — companion: *Continuity and Uniqueness of Equilibria for Linear
Exchange Economies*, JOTA 109(2):237–263, 2001 · DOI `10.1023/a:1017517020329`
> On an open dense full-measure subset of the data the equilibrium price is **real-analytic**, with
> an explicit local formula; globally it is **locally Lipschitz**; on the boundary of the uniqueness
> region it is never locally Lipschitz.
> **Bears on §2.11's grid choice and §2.12's multiplier-uniqueness assumption.** The right shape
> intuition: smooth on the generic set, non-Lipschitz exactly where the equilibrium stops being
> unique — which is where a *degenerate, balance-tight* polytope sits. It predicts that ranging
> between grid points will fail precisely at the interesting `δ`, corroborating
> `MODEL_U1-cert` failure mode 5 from the theory side.
> `frontier`

---

## 4. Q4 — rounding a fractional constrained equilibrium under the same constraints

**Verdict: the exact-decomposition question has a clean answer (`budish2013`) whose hypothesis our
band fails; the approximate routes are `akbarpour2020` and `gandhi2006`; the value-guaranteed EG
rounding literature is unconstrained. §2.13's MIP survives. See absence ledger row E.**

**Budish, E., Che, Y.-K., Kojima, F. & Milgrom, P.** *Designing Random Allocation Mechanisms: Theory
and Applications.* American Economic Review 103(2):585–623, 2013 · DOI `10.1257/aer.103.2.585`
> Characterises when a fractional (expected) allocation can be implemented as a lottery over
> **integral allocations satisfying exactly the same constraints**: the constraint structure must be
> a **bihierarchy** (two nested hierarchies of *counting* constraints).
> **Bears on §2.13 and on D2′ — this is the paper that decides whether a solver is needed.** Our
> constraint set is `n` unit-supply rows plus `2k` per-agent rows on `Σ_z M_z x_{zi}`. The supply
> rows and the agent rows do form two hierarchies, but the agent rows are **weighted by `M_z`**, not
> counts, and bihierarchy is a theorem about counting constraints. **So the exact-decomposition
> escape is unavailable and §2.13's 325-binary MIP stays on the path.** Worth stating explicitly in
> `MODEL` prose, because "why not just decompose?" is the obvious referee question.
> `foundation`

**Akbarpour, M. & Nikzad, A.** *Approximate Random Allocation Mechanisms.* Review of Economic
Studies 87(6):2473–2510, 2020 · DOI `10.1093/restud/rdz066`
> Generalises `budish2013`: if some feasibility constraints may be treated as **goals** rather than
> hard constraints, then under weak conditions any expected allocation can be implemented by
> randomising over integral allocations satisfying the hard constraints **exactly** and the goals
> **approximately**. Also proves existence of `ε`-competitive equilibria in large markets with
> indivisible items and feasibility constraints.
> **Bears on §2.13 and on D2′'s blocking sub-case.** The principled fallback if
> `t*/(T/k) > δ_sponsor` makes the band integrally infeasible: demote the band to a goal, meet the
> supply constraint exactly, report the realised `δ`. This is a *better* report than "infeasible",
> and it is citable rather than improvised.
> `frontier`

**Gandhi, R., Khuller, S., Parthasarathy, S. & Srinivasan, A.** *Dependent rounding and its
applications to approximation algorithms.* Journal of the ACM 53(3):324–360, 2006 ·
DOI `10.1145/1147954.1147956`
> Dependent randomised rounding on bipartite graphs: preserves marginals, preserves each vertex's
> fractional degree to within one unit (**degree-preservation**), and gives negative correlation.
> **Bears on §2.13.** The cheapest non-MIP repair to try first: round the `≤ 2k−1` split units with
> dependent rounding, which keeps each district's *count* of units within one — but note it controls
> counts, not `M`-mass, so the band violation it leaves is `≤ max_{z∈F} M_z`, which at our split
> masses is exactly the quantity `MODEL_U1-cert` failure mode 9 says must be measured before it is
> quoted.
> `tool-we-lack`

**Cole, R., Devanur, N. R., Gkatzelis, V., Jain, K., Mai, T., Vazirani, V. V. & Yazdanbod, S.**
*Convex Program Duality, Fisher Markets, and Nash Social Welfare.* EC '17, 459–460 ·
DOI `10.1145/3033274.3085109`
> Shows the **spending-restricted** market — EG/Shmyrev *with an extra side constraint added to the
> convex program* — has an integrality gap of exactly 2 for Nash welfare, and gives a simple recipe
> for dualising convex programs with linear constraints and a convex objective, "almost at par with
> LP duality".
> **Bears on §2.10's duality derivation and on §2.13's value guarantee.** Two uses: (i) the
> mechanical dualisation recipe is the cleanest published route to our `(p, μ^±)` dual and its
> weak-duality certificate; (ii) it is a worked precedent for "add a linear side constraint to EG,
> keep the price reading, and round with a proved factor" — the shape of what §2.13 wants, in a
> different constraint family.
> `foundation`

**Cookson, B., Ebadian, S. & Shah, N.** *Constrained Fair and Efficient Allocations.* AAAI 39:
13718–13726, 2025 · DOI `10.1609/aaai.v39i13.33499`
> Maximum Nash welfare under feasibility constraints: MNW allocations are `1/2`-EF1 and Pareto
> optimal under arbitrary **matroid** constraints, with extensions to a non-matroid family that
> **explicitly includes balancedness**.
> **Bears on §2.10 and §2.13's justification.** The current frontier for "MNW under a balance-style
> constraint" and the closest published statement that the MNW-under-constraint object retains its
> fairness guarantees. Their balancedness is a cardinality balance, ours is an `M`-mass band, so it
> is a strong analogy rather than a citation for our guarantee.
> `frontier`

**Cole, R. & Gkatzelis, V.** *Approximating the Nash Social Welfare with Indivisible Items.* SIAM
Journal on Computing 47(3):1211–1236, 2018 · DOI `10.1137/15m1053682` —
**already in `docs/channel_note/references.bib` as `cole2018`; not duplicated.**
> Noted here because its method — build a *modified* market equilibrium whose prices reveal how to
> round — is the template §2.13 is a constrained instance of.

---

## 5. Q5 — selecting the agent set: `max_{|S|=k} EG_S`

**Verdict: nothing. No submodularity, subadditivity or concave-envelope bound for `S ↦ EG_S` or
`S ↦ EG^bal_S`. (★) appears to be original to this problem's utility structure. See absence
ledger rows A and B; §8 Q11 resolves to "not published — write it up".**

**Chakrabarty, D., Goel, G., Vazirani, V. V., Wang, L. & Yu, C.** *Submodularity Helps in Nash and
Nonsymmetric Bargaining Games.* SIAM Journal on Discrete Mathematics 28(1):99–115, 2014 ·
DOI `10.1137/110821433`
> Imposing **submodularity on the function defining the feasible utility set** of a Nash bargaining
> game yields rational equilibria and a convex program generalising Eisenberg–Gale.
> **Bears on §2.14 and `LENS_GROMOV` OQ4 — as the nearest miss, not as support.** The one place
> "submodularity" and "Eisenberg–Gale" appear together in the literature, and the submodularity is
> on the *constraint side*, not on the agent set. It is the paper a referee will point at; §2.14
> should cite it precisely to say why it does not apply.
> `contradicts-or-sharpens`

**Li, W. & Vondrák, J.** *Estimating the Nash Social Welfare for coverage and other submodular
valuations.* SODA 2021, 1119–1130 · DOI `10.1137/1.9781611976465.69`
> Gives a `(1/e)(1−1/e)²`-approximation of the **optimal value** (not the allocation) of Nash social
> welfare for coverage valuations, sums of matroid rank functions, and matching-based valuations —
> i.e. a computable bound on `max_π NSW` obtained from the valuation structure alone.
> **Bears on §2.14 and on §5 row 0a — the closest published relative of (★).** Same *type* of
> object: estimate the EG optimum's value cheaply from structure rather than solving. Different
> mechanism: theirs is a multilinear/concave-extension argument on submodular valuations, ours is
> AM–GM through a max-`k`-coverage premium `P_S` on an additive `common + w·S_i` structure. Cite as
> the closest antecedent when writing (★) up.
> `frontier`

**Mavrov, I.-A., Munagala, K. & Shen, Y.** *Fair Multiwinner Elections with Allocation Constraints.*
EC '23, 964–990 · DOI `10.1145/3580507.3597685`
> Optimises a **smoothed Nash welfare over size-`k` committees subject to arbitrary additional
> constraints**, and shows the optimum lies in an `e^β`-approximate "restrained core" for
> `β`-self-bounding utilities.
> **Bears on §2.14 / U16 — the closest published *problem shape*.** "Maximise a Nash-type welfare
> over a size-`k` selection under side constraints" is exactly our roster problem. But the `k`
> selected objects are *goods* valued by a fixed voter set, whereas in `max_S EG^bal_S` the selected
> objects are the **agents whose log-utilities are being summed** — so the objective's argument set
> changes with `S`, which is what makes submodularity fail to be obvious. Cite to locate our problem
> and to state the difference.
> `frontier`

**Gokhale, S., Sagar, H., Vaish, R. & Yadav, J.** *Approximating One-Sided and Two-Sided Nash Social
Welfare With Capacities.* AAMAS 2025, 914–922 · DOI `10.65109/xonp8439`
> Constant-factor approximations for Nash welfare under **capacity constraints** limiting how many
> items an agent may receive (one-sided) or how many workers a firm may take (two-sided), for
> submodular and subadditive valuations respectively; establishes a computational separation between
> Nash and utilitarian welfare in the two-sided case.
> **Bears on §2.10, §2.13 and stage 2.** Two uses: it is a capacity-constrained NSW existence and
> approximation result (our band, in counting form), and its *two-sided* half — workers and firms
> with capacities — is the closest published framing of our stage-2 rectangular matching if the
> roster and the map are ever solved jointly. **Caveat:** the Crossref record carries an inconsistent
> container (`AAMAS '04`) and a zero reference count; the DOI resolves and the author/title/page
> data are consistent with AAMAS 2025, but re-verify before it enters the note.
> `frontier`

---

## 6. Q6 — solving concave `Σ log` at `n·k ≈ 16k` variables with no conic solver

**Verdict: the architecture is standard and has a benchmarked open-source implementation; no
published run reports cut counts for a *pure-continuous* concave `Σ log` program at this size. See
absence ledger row G.**

**Lundell, A., Kronqvist, J. & Westerlund, T.** *The supporting hyperplane optimization toolkit for
convex MINLP.* Journal of Global Optimization 84:1–41, 2022 · DOI `10.1007/s10898-022-01128-0`
> **SHOT**: an open-source (COIN-OR) polyhedral-outer-approximation solver combining ECP and
> extended supporting hyperplane linearisations, integrated **single-tree** with the MIP subsolver
> via lazy constraints; benchmarked on all 406 convex problems of MINLPLib against the
> state of the art.
> **Bears on §2.11's primary route and on §5 row 1 — the "tool-we-lack" that may already exist.**
> Before writing our own tangent loop, check whether SHOT can be driven from Python on this machine:
> it *is* §2.11's architecture, already tuned, and its single-tree lazy-constraint mode is exactly
> what trap 14 warns about (dual reductions must be off), so the warning transfers verbatim. If SHOT
> is unavailable, the paper's reported iteration counts are the yardstick our loop should be judged
> against.
> `tool-we-lack`

**Kronqvist, J. & Misener, R.** *A disjunctive cut strengthening technique for convex MINLP.*
Optimization and Engineering 22:1315–1345, 2021 · DOI `10.1007/s11081-020-09551-6`
> Strengthens outer-approximation cuts by exploiting disjunctive structure; two cut types, the
> second dominating; used with the extended supporting hyperplane algorithm, "significantly"
> reducing both iterations and time.
> **Bears on §2.11's mitigation list.** The modern alternative to `Lemarechal1995` stabilisation
> when the OA loop thrashes: strengthen the cuts rather than damp the iterates. Applies only once
> §2.13's binaries exist (it needs a disjunction), so it is a stage-3 tool, not a stage-2 one.
> `frontier`

**Ben-Tal, A. & Nemirovski, A.** *On Polyhedral Approximations of the Second-Order Cone.*
Mathematics of Operations Research 26(2):193–205, 2001 · DOI `10.1287/moor.26.2.193.10561`
> A second-order cone admits a **polyhedral** `ε`-approximation with `O(log(1/ε))` extra variables
> and constraints — conic geometry is reachable through LP at logarithmic cost.
> **Bears on `LENS_GROMOV` OQ2 and §2.1's retirement.** The theoretical answer to "no conic solver
> on the machine": conic representability is not a hard barrier, only a modelling cost. It does not
> resurrect §2.1 (the perspective term's *strength* is a separate matter from its representability),
> but it removes "unavailable" as a permanent verdict and pairs with `lubin2018`, already in our bib.
> `foundation`

**Chaudhury, Kroer, Mehta & Nan (EC '24)** — see §1; the strongest practical data point for solving
an EG-shaped `Σ log` program with **LP subproblems only**, which is §2.11's primary route.

---

## 7. Q7 — stability radius and second-best margins for the assignment problem

**Verdict: the object has a standard name (*stability radius* / *stability region*), a polynomial
algorithm, and a standard enumeration method for the near-optimal set (*k-best*, Murty).**

**Chakravarti, N. & Wagelmans, A. P. M.** *Calculation of stability radii for combinatorial
optimization problems.* Operations Research Letters 23(1–2):1–7, 1998 ·
DOI `10.1016/s0167-6377(98)00031-5`
> Algorithms computing the **stability radius** of an optimal (or approximate) solution of a binary
> program with min-sum or min-max objective, running in polynomial time whenever the underlying
> problem is polynomially solvable; extends to the tolerance approach.
> **Bears on §2.15 and §5 row 0c.** The name and the algorithm for what §2.15 calls "the margin",
> and the licence for the `k`-re-solve construction: for the assignment problem the radius is
> polynomially computable, so the margin is a *computed quantity with a citation*, not a bespoke
> diagnostic. Report it as a stability radius.
> `foundation`

**Sotskov, Yu. N., Leontev, V. K. & Gordeev, E. N.** *Some concepts of stability analysis in
combinatorial optimization.* Discrete Applied Mathematics 58(2):169–190, 1995 ·
DOI `10.1016/0166-218x(93)e0126-j`
> Survey fixing the vocabulary — stability region, stability ball, stability radius, post-optimality
> analysis — across TSP, assignment, shortest path, scheduling.
> **Bears on §2.15's reporting convention (§7 row 4).** Use its terms so the tie report is legible;
> included under the `foundation` exception as the vocabulary source.
> `foundation`

**Lin, C.-J. & Wen, U.-P.** *Sensitivity analysis of the optimal assignment.* European Journal of
Operational Research 149(1):35–46, 2003 · DOI `10.1016/s0377-2217(02)00439-3`
> The assignment problem is **inherently degenerate**, so classical Type-I basis ranging is
> useless — the basis can change while the optimal assignment does not. Defines **Type-II** ranging
> (the range over which the current optimal *assignment* stays optimal) and **Type-III** (the range
> over which the value function's slope is constant), with algorithms.
> **Bears on §2.15 and, by analogy, on §2.11's assumption (ii).** This is the correction our
> stability report needs: `Chvatal1983`-style objective-coefficient ranging on a degenerate
> assignment LP returns the wrong interval. **Report the Type-II range, not the basis range.** The
> same distinction is the LP-side statement of `MODEL_U1-cert` failure mode 5.
> `tool-we-lack`

**Miller, M. L., Stone, H. S. & Cox, I. J.** *Optimizing Murty's ranked assignment method.* IEEE
Transactions on Aerospace and Electronic Systems 33(3):851–862, 1997 · DOI `10.1109/7.599256`
> Engineering of **Murty's** `k`-best-assignment algorithm: dual-variable inheritance during
> partitioning, subproblem ordering by lower bound, optimised partition order; 100 best solutions of
> a 100×100 instance in ~0.6 s, near-linear in both `k` and `N`.
> **Bears on §2.15 and §2.14's merge.** The right algorithm for "the set of rosters within the
> tier-2 floor": Murty's partition, not `k` independent re-solves. At `k = 13` this is
> sub-millisecond, and it produces the *ordered* list §2.15(iii) needs for interval reporting.
> `tool-we-lack`

**Eppstein, D.** *k-Best Enumeration.* In *Encyclopedia of Algorithms*, Springer, 2016, 1003–1006 ·
DOI `10.1007/978-1-4939-2864-4_733`
> Survey of `k`-best enumeration including `k` best matchings in weighted graphs.
> **Bears on §2.15's reporting.** Confirms "the set of optimal solutions within `ε`" has a standard
> name (`k`-best / ranked enumeration) and a standard complexity story; `foundation` by the survey
> exception.
> `foundation`

---

## 8. Q8 [carried] — power diagrams, constrained least-squares assignment, and the `O(nk)` cell certificate under a band

**Verdict: yes — a band is a *bounded-shape* constraint, and the vertex-to-power-diagram
correspondence is published for exactly that class. `borgwardt2019` is the load-bearing entry.**

**Borgwardt, S. & Happach, F.** *Good Clusterings Have Large Volume.* Operations Research
67(1):215–231, 2019 · DOI `10.1287/opre.2018.1779`
> Vertices of the **bounded-shape partition polytope** (clusterings with per-cluster size/weight
> constraints given by *lower and upper bounds*) correspond to clusterings admitting a **separating
> power diagram**, one cell per cluster. Characterises the edges of the polytope, gives an explicit
> description of the normal cones, measures a clustering's quality by the **volume of the normal
> cone** at its vertex, and computes "most stable" sites.
> **Bears on §2.10's `O(nk)` dual check, U15 and — unexpectedly — §2.4/§8 Q3.** Our band
> `(1−δ)T/k ≤ m_i ≤ (1+δ)T/k` is *verbatim* a bounded-shape constraint, so **the power-diagram
> certificate survives the band**: `cert_power_diagram`'s `O(nk)` contract extends, with the band
> multipliers entering the site weights. Second, the normal-cone volume is a **stability radius for
> the map itself**, which is a candidate answer to "how far can the data move before the partition
> changes" and a structurally different route to §2.4's modulus than the transportation distance.
> `frontier`

**Bansil, M. & Kitagawa, J.** *A Newton Algorithm for Semidiscrete Optimal Transport with Storage
Fees.* SIAM Journal on Optimization 31(4):2586–2613, 2021 · DOI `10.1137/20m1357226`
> Damped-Newton algorithm for semi-discrete OT with storage fees, "corresponding to a problem with
> **hard capacity constraints**"; convergence proved **without connectedness assumptions on the
> source measure**, plus stability results for the associated Laguerre cells.
> **Bears on §2.10 and on the 547-component obstacle.** Two payoffs. (i) Capacity-constrained
> semi-discrete OT keeps Laguerre/power cells — independent corroboration of `borgwardt2019` from
> the geometry side. (ii) The no-connectedness hypothesis is the rare result that *does not*
> assume away our disconnected footprint (`CLAUDE.md`, 547 components).
> `frontier`

**Bansil, M. & Kitagawa, J.** *Quantitative Stability in the Geometry of Semi-discrete Optimal
Transport.* International Mathematics Research Notices 2022(10):7354–7389 ·
DOI `10.1093/imrn/rnaa355`
> Quantitative stability of Laguerre cells in measure without regularity assumptions on the source;
> quantitative invertibility of the map *dual variables ↦ cell measures* under a
> Poincaré–Wirtinger inequality; explicit constants throughout.
> **Bears on §2.4, §2.12 and §8 Q3 — the closest published thing to the displacement modulus.**
> "How much do the cells move when the potentials move" is the inverse of what §2.4 wants, and the
> invertibility result turns it into the right direction: a bound of the form *cell-measure change
> ≥ c · potential change*. It is stated for a quadratic OT cost and a continuous source, so it is a
> template, not a citation — but it is the first entry in this file that gives §8 Q3 a concrete
> shape to aim at.
> `tool-we-lack`

**Jung, C. & Redenbach, C.** *An analytical representation of the 2d generalized balanced power
diagram.* Computational Geometry 121:102101, 2024 · DOI `10.1016/j.comgeo.2024.102101`
> Analytic representation of the vertices and edges of the **generalized balanced power diagram**
> (cells induced by elliptic, i.e. anisotropic, distances), with an algorithm to compute the whole
> diagram rather than a discretised label image.
> **Bears on `LENS_GROTHENDIECK` OQ2's "anisotropic cells" half.** If the band's agent-specific
> surcharge `ν_i M_z` is read geometrically it deforms the cells anisotropically; this is the
> vocabulary and the computational route. Low priority — we have no evidence yet that the band's
> cells are anything but ordinary power cells, and `borgwardt2019` suggests they are not.
> `frontier`

---

## 9. Q9 [carried] — stability, displacement and inverse optimization: `objective-gap ≥ φ(mass moved)`

**Verdict: no instance-specific modulus for partitioning or assignment. But the *object* has a
name — a **Hölderian error bound** / **growth condition** — and a mature literature that says what
form `φ` may take and how to prove one. See absence ledger row D.**

**Hoffman, A. J.** *On approximate solutions of systems of linear inequalities.* Journal of Research
of the National Bureau of Standards 49(4):263, 1952 · DOI `10.6028/jres.049.027`
> **Hoffman's bound**: for a polyhedron `P = {x : Ax ≤ b}` there is a constant `κ(A)` with
> `dist(x, P) ≤ κ(A)·‖(Ax − b)_+‖` — the distance to feasibility is linearly controlled by the
> violation.
> **Bears on §2.4 and §8 Q3.** The origin of every "gap controls distance" result, and the reason
> to expect `φ` to be **linear** (an error bound with exponent 1) on a polyhedron, rather than the
> square root a generic convex problem would give. That is the single most useful prior for
> attempting the modulus.
> `foundation`

**Bolte, J., Nguyen, T. P., Peypouquet, J. & Suter, B. W.** *From error bounds to the complexity of
first-order descent methods for convex functions.* Mathematical Programming 165(2):471–507, 2017 ·
DOI `10.1007/s10107-016-1091-6`
> Shows **Łojasiewicz/Kurdyka inequalities ⟺ error bounds ⟺ growth conditions** for convex
> functions, and converts them into complexity rates; gives the exact family
> `f(x) − f* ≥ c · dist(x, argmin)^α`.
> **Bears on §2.4, §8 Q3 and D3′ — this is the name for the modulus.** `objective-gap ≥ φ(mass
> moved)` is a **Hölderian error bound with `φ(t) = c·t^α`**, and this paper says what has to be
> proved to get one (a KŁ exponent for `Σ log g_i` on the assignment polytope) and what it buys.
> **The right way to attack §8 Q3 is to prove a KŁ exponent, not to invent a bespoke argument.**
> `tool-we-lack`

**Drusvyatskiy, D. & Lewis, A. S.** *Error Bounds, Quadratic Growth, and Linear Convergence of
Proximal Methods.* Mathematics of Operations Research 43(3):919–948, 2018 ·
DOI `10.1287/moor.2017.0889`
> Establishes the equivalence of error bounds and **quadratic growth** (`α = 2`) for a broad class,
> and links both to linear convergence.
> **Bears on §2.4.** The `α = 2` case, which is what a *strongly*-concave surrogate would give.
> `Σ log g_i` is not strongly concave in `x` (it is concave in the `g`, which are a rank-`k` linear
> image), so the honest expectation is `α ∈ [1, 2]` and the exponent is the thing to measure. Pairs
> with `bolte2017` as the pair a `math-verify` unit would work from.
> `tool-we-lack`

**Chan, T. C. Y., Mahmood, R. & Zhu, I. Y.** *Inverse Optimization: Theory and Applications.*
Operations Research 73(3):1046–1074, 2025 · DOI `10.1287/opre.2022.0382`
> Comprehensive review of inverse optimization: given decisions, infer the objective/constraints
> that render them (approximately) optimal; consolidates model properties, reformulations and
> computational methods.
> **Bears on §2.4's *other* direction and on FRAME §3.5.** Inverse optimization answers "what
> objective makes the sponsor's hand-drawn map optimal", which is a live alternative framing of the
> U10 baseline comparison (§5 row 6): instead of scoring the baseline as a `(δ, V)` point, fit the
> `λ, θ` that would rationalise it. A survey, tagged `foundation` by the exception.
> `foundation`

**Ahuja, R. K. & Orlin, J. B.** *Inverse Optimization.* Operations Research 49(5):771–783, 2001 ·
DOI `10.1287/opre.49.5.771.10607`
> The foundational results: inverse LP under `L1`/`L∞` is an LP; inverse shortest-path, assignment
> and min-cut under `L1` with unit weights reduce to a problem of the same kind; polynomial
> solvability transfers.
> **Bears on §2.4.** If the inverse framing above is pursued, **inverse assignment is as easy as
> assignment** — so the U10 rationalisation is a milliseconds-scale computation, not a project.
> `foundation`

---

## Shortlist — five papers for the exact niche

| # | entry | one line |
|---|---|---|
| 1 | **`jainvazirani2010`** — Jain & Vazirani, GEB 2010 | Names `EG^bal_S`: it is an **Eisenberg–Gale market**, so §2.10 stops being a construction and becomes a citation plus one solve. |
| 2 | **`jalota2023`** — Jalota, Pavone, Qi & Ye, GEB 2023 | The only paper on *per-agent* linear constraints in a Fisher market, and it says the equilibrium reading **breaks** without a budget perturbation — this constrains what §2.12 may tell a sponsor. |
| 3 | **`lenstra1990`** — Lenstra, Shmoys & Tardos, Math. Prog. 1990 | The canonical `≤ k−1` extreme-point/pseudoforest lemma `MODEL_U1-cert` §8.4 asked for; with `shmoystardos1993` it also supplies the `+ #tight side rows` pattern, retiring the coarse `≤ 2k` from the proof burden. |
| 4 | **`budish2013`** — Budish, Che, Kojima & Milgrom, AER 2013 | Settles D2′'s escape route: exact integral decomposition under the same constraints needs a **bihierarchy of counting constraints**; our `M`-weighted band is not one, so §2.13's MIP stays. |
| 5 | **`borgwardt2019`** — Borgwardt & Happach, Oper. Res. 2019 | The band is a **bounded-shape** constraint, whose polytope vertices are exactly the clusterings with a **separating power diagram** — so `cert_power_diagram`'s `O(nk)` certificate survives at `δ > 0`, and the normal-cone volume is a second candidate for §2.4's modulus. |

*Runners-up, both engineering:* `lundell2022` (SHOT — §2.11's architecture already implemented and
benchmarked; check availability before writing the tangent loop) and `chaudhury2024eg`
(Frank–Wolfe with LP subproblems on an EG program, 5–20 iterations at real scale).

---

## Absence ledger

Every row states the query strings, where they were run, the date, and the nearest miss. All searches
run 2026-09-03 unless noted. "Consensus" covers Semantic Scholar + PubMed + Scopus + arXiv indexing
of the venues the brief names (Math. Prog., MPC, Oper. Res., INFORMS JoC, SIOPT, EJOR, Discrete
Optim., Manag. Sci., ACM EC, SAGT, WINE, ITCS, GEB, JPE, DCG, SIIMS, OMS, JOGO).

| # | claim | queries | venues / route | date | nearest miss |
|---|---|---|---|---|---|
| A | **No published submodularity, subadditivity or concave-envelope result for `S ↦ EG_S` or `S ↦ EG^bal_S`** (the map from the *agent set* to the EG optimum). | C4 "submodularity of Nash social welfare in the set of agents selection"; C12 "selecting a subset of k agents to maximize Nash social welfare committee selection"; W1 "submodularity of Nash welfare or Eisenberg-Gale value as a function of the set of agents" | Consensus (EC/STOC/SODA/GEB/JET/SIDMA indexed); Google via WebSearch | 2026-09-03 | `chakrabarty2014` — submodularity of the function defining the **feasible utility set**, not of the agent set. `mavrov2023` — Nash welfare over size-`k` constrained committees, but the agent set (voters) is fixed and only the *goods* are selected. |
| B | **The screening bound (★) `EG_S ≤ k log((B_tot + w·P_S)/k)` for the `common(z) + w·S_i(z)` utility structure has not appeared.** | C4, C12, W1 above; C3 "rounding fractional allocation Nash social welfare integral guarantee" | Consensus; WebSearch | 2026-09-03 | `livondrak2021` — a computable bound on the NSW *optimum value* from valuation structure, for coverage/matroid-rank valuations, via a multilinear-extension argument. Same object type, different mechanism, different valuation class. `cole2017duality`'s integrality-gap-2 result bounds the gap between fractional and integral NSW but not the fractional optimum itself. |
| C | **No characterisation of the *shape* (piecewise structure, breakpoints, identity of first-moving goods) of the value function of an EG program as a per-agent capacity band widens.** | C14 "comparative statics competitive equilibrium prices with respect to endowment supply Lipschitz"; W3 "value function of Eisenberg-Gale convex program parametric capacity constraint breakpoints piecewise structure"; C1 "Fisher market equilibrium with capacity constraints convex program" | Consensus; WebSearch (returned the EG-markets and matching-markets threads but nothing on parametric value functions — the search engine's own summary confirmed the gap) | 2026-09-03 | `megiddo2007` — continuity of equilibrium *prices* (not allocations) in the market **data**, not in a capacity parameter. `bonnisseau2001diff` — real-analyticity of equilibrium prices on a generic set of endowments, and failure of local Lipschitzness on the uniqueness boundary; the right shape intuition, wrong parameter. **Consequence:** §2.12's first-mover list stays a computation, not a characterisation; `LENS_GROMOV` M12's "concave-rising vs flat-then-jump" remains a genuinely open empirical question. |
| D | **No result of the form `objective-gap ≥ φ(mass that must move)` for balanced partitioning, districting or the assignment problem.** | C8 "inverse optimization suboptimality distance to optimal solution perturbation bound"; W2 "'error bound' OR 'growth condition' objective gap lower bound distance to optimal solution set optimization"; C6 "stability radius of optimal solution assignment problem sensitivity analysis" | Consensus; WebSearch; `chan2025` survey read directly for the inverse-optimization branch | 2026-09-03 | `bolte2017`/`drusvyatskiy2018` — Hölderian error bounds `f(x) − f* ≥ c·dist(x, argmin)^α` are exactly the right *form*, but generic: no instance-specific `c, α` for `Σ log` on an assignment polytope. `bansil2022` — quantitative invertibility of dual-variables ↦ cell-measures for semi-discrete OT, with explicit constants; the closest thing to a modulus, but for a quadratic OT cost on a continuous source. `borgwardt2019` — normal-cone volume as a stability measure for a clustering; a different modulus (data-perturbation, not objective-gap). **§8 Q3 stays open; the ledger now says what to try.** |
| E | **No rounding theorem gives a value guarantee for rounding a fractional constrained-EG allocation under the same per-agent *weighted* capacity band.** | C3; C19 "rounding fractional assignment preserving capacity constraints bihierarchy implementation integral"; C15 "iterative rounding extreme point rank lemma degree bounded network design side constraints" | Consensus (STOC/FOCS/SODA/JACM/ToA/AER/ReStud indexed) | 2026-09-03 | `budish2013` — exact decomposition under the same constraints, but **requires a bihierarchy of counting constraints**; our band is `M`-weighted. `akbarpour2020` — approximate, with the band demoted to a "goal". `gandhi2006` — dependent rounding preserves per-agent *counts* to ±1, not weighted sums. `cole2017duality`/`cole2018` — value-guaranteed rounding of a market equilibrium, but the market is spending-restricted, not agent-capacity-constrained. **Consequence: §2.13's 325-binary MIP is not removable by citation; D2′ is a computation.** |
| F | **No proportional-response or combinatorial equilibrium algorithm accepts per-agent linear side constraints and returns exact duals.** | C1; C10 "linear Fisher market equilibrium spending graph forest structure sparsity of allocation"; C16 "Eisenberg-Gale market equilibrium rationality irrational equilibria polytope constraints" | Consensus; forward citation walk on `jalota2023` (OpenAlex `W4382395702`, 11 citing works, all read) | 2026-09-03 | `jalota2023` — ADMM with guarantees only for **homogeneous** linear constraints, plus an outer fixed point for the budget perturbation whose convergence is validated numerically, not proved. `gargtaovegh2022` — approximate equilibrium under constrained PLC utilities. `birnbaum2011` — PR is mirror descent, so the constrained variant is *projected* mirror descent, which nobody has written down for this market. **Confirms `MODEL_U1-cert` §8.2: a new solve path is required.** |
| G | **No reported cut counts or accuracy figures for LP outer approximation on a *pure-continuous concave* `Σ log` program at ~16k variables.** | C5 "extended cutting plane outer approximation convex MINLP computational performance cut count" | Consensus (JOGO, Optim. Eng., Ann. OR, Comput. Chem. Eng., Math. Prog. indexed) | 2026-09-03 | `lundell2022` — 406 MINLPLib convex instances with full iteration statistics, but they are **mixed-integer** and far smaller; the pure-continuous concave case is a degenerate special case nobody benchmarks because an NLP solver is assumed available. `chaudhury2024eg` — 5–20 LP-subproblem iterations on EG-shaped chores instances at realistic scale; **the closest operational data point, and the number §2.11 should be judged against**. `kronqvistmisener2021` reports iteration reductions but again for MINLP. **Consequence: the `code-verify` item "every OA master optimum is a valid upper bound at every iteration" must be tested on our instance; there is no published run to inherit the answer from.** |

**Two absence claims from the predecessor that this run *retires* rather than confirms:**
`MODEL_U1-cert` §8.4's "no canonical citation for `≤ k−1`" is **false** — `lenstra1990` is it
(searched via W4 "Lenstra Shmoys Tardos 1990 lemma extreme point fractionally assigned jobs
fewer than machines forest", confirmed against the Math. Prog. record). And §8 Q2's "is our object
published?" is **answered yes** for `EG^bal_S` as a class member (`jainvazirani2010`), though **no**
for our specific band-parametrised value function (ledger row C).

---

## Query log

**Consensus (19 conceptual and near-title):**
C1 `Fisher market equilibrium with capacity constraints convex program` ·
C2 `support size sparsity of market equilibrium allocation basic feasible solution transportation` ·
C3 `rounding fractional allocation Nash social welfare integral guarantee` ·
C4 `submodularity of Nash social welfare in the set of agents selection` ·
C5 `extended cutting plane outer approximation convex MINLP computational performance cut count` ·
C6 `stability radius of optimal solution assignment problem sensitivity analysis` ·
C7 `k-best solutions ranking assignment problems enumeration algorithm` ·
C8 `inverse optimization suboptimality distance to optimal solution perturbation bound` ·
C9 `semi-discrete optimal transport Laguerre cells capacity constrained power diagram algorithm` ·
C10 `linear Fisher market equilibrium spending graph forest structure sparsity of allocation` ·
C11 `pseudo-market mechanism with distributional constraints course allocation prices externality` ·
C12 `selecting a subset of k agents to maximize Nash social welfare committee selection` ·
C13 `number of fractionally allocated goods at most n-1 fractionally Pareto optimal allocation` ·
C14 `comparative statics competitive equilibrium prices with respect to endowment supply Lipschitz` ·
C15 `iterative rounding extreme point rank lemma degree bounded network design side constraints` ·
C16 `Eisenberg-Gale market equilibrium rationality irrational equilibria polytope constraints` ·
C17 `network utility maximization proportional fairness logarithmic utility dual link prices algorithm` ·
C18 `generalized power diagram anisotropic constrained clustering existence balanced cells` ·
C19 `rounding fractional assignment preserving capacity constraints bihierarchy implementation integral`

**WebSearch (4):**
W1 `submodularity of Nash welfare or Eisenberg-Gale value as a function of the set of agents` ·
W2 `"error bound" OR "growth condition" objective gap lower bound distance to optimal solution set optimization` ·
W3 `value function of Eisenberg-Gale convex program parametric capacity constraint breakpoints piecewise structure` ·
W4 `Lenstra Shmoys Tardos 1990 lemma extreme point fractionally assigned jobs fewer than machines forest`

**Crossref `query.bibliographic` near-title resolutions (28), all 2026-09-03:** Jalota *Fisher markets
with linear constraints* · Echenique *Constrained Pseudo-Market Equilibrium* · Cole *Convex Program
Duality Fisher Markets Nash Social Welfare* · Cole & Gkatzelis *Approximating the NSW with
Indivisible Items* · Lundell *supporting hyperplane optimization toolkit* · Lenstra Shmoys Tardos
*scheduling unrelated parallel machines* · Budish Che Kojima Milgrom *Designing Random Allocation
Mechanisms* · Akbarpour Nikzad *Approximate Random Allocation Mechanisms* · Chakravarti Wagelmans
*stability radii* · Megiddo Vazirani *Continuity properties … linear Fisher markets* · Chan Mahmood
Zhu *Inverse Optimization: Theory and Applications* · Miller Stone Cox *Murty's ranked assignment* ·
Lin Wen *Sensitivity analysis of the optimal assignment* · Gandhi Khuller Parthasarathy Srinivasan
*Dependent rounding* · Ben-Tal Nemirovski *polyhedral approximations of the second-order cone* ·
Li Vondrák *Estimating the NSW for coverage* · Gokhale *One-Sided and Two-Sided NSW With Capacities*
· Kroer Peters *Lindahl Equilibrium … Funding Caps* · Miralles Pycia *Foundations of Pseudomarkets* ·
Birnbaum Devanur Xiao *gradient descent for Fisher markets* · Jain Vazirani *Eisenberg-Gale markets*
· Im Kulkarni Munagala *Competitive algorithms from competitive equilibria* · Garg Tao Végh
*constrained PLC utilities* · Jäger Lindermayr Megow *proportional fairness nonclairvoyant polytope
scheduling* · Mavrov Munagala Shen *Fair Multiwinner Elections with Allocation Constraints* ·
Chaudhury Kroer Mehta Nan *Competitive Equilibrium for Chores* · Cookson Ebadian Shah *Constrained
Fair and Efficient Allocations* · Bansal *network design problems with degree bounds* · Lau Ravi
Singh *Iterative Methods in Combinatorial Optimization* · Bonnisseau Florig Jofré *Differentiability
of Equilibria* · Bansil Kitagawa *Newton algorithm … storage fees* / *Quantitative stability …* ·
Low Lapsley *Optimization flow control I* · Kronqvist Misener *disjunctive cut strengthening* ·
Sotskov Leontev Gordeev *stability analysis in combinatorial optimization* · Chakrabarty Goel
Vazirani Wang Yu *Submodularity helps in Nash …* · Bolte *From error bounds to complexity* ·
Drusvyatskiy Lewis *Error bounds, quadratic growth* · Hoffman *approximate solutions of systems of
linear inequalities* · Eppstein *k-Best Enumeration* · Shmoys Tardos *generalized assignment* ·
Borgwardt Happach *Good Clusterings Have Large Volume* · Jung Redenbach *2d generalized balanced
power diagram* · Ahuja Orlin *Inverse Optimization* · direct DOI fetch of `10.65109/xonp8439`.

**OpenAlex citation-graph walks (5):** `doi:10.1016/j.geb.2023.06.007` record (56 references,
`cited_by_count` 11, not retracted) and forward walk `cites:W4382395702` (11 works — surfaced
`gargtaovegh2022`, the SODA'22 constrained-PLC paper, and `jager2026`) ·
`doi:10.1257/aer.20201769` record (not retracted) and forward walk `cites:W2973080784` (13 works —
surfaced the Hylland–Zeckhauser computational thread and *Allocation with Weak Priorities and General
Constraints*, both routed to economic-theory) · one failed walk (`cites:W2963519321`, zero results,
wrong id).

---

## Not searched — declared gaps

- **Contiguity under a band.** Out of scope per FRAME §7; FOUNDATIONS §8 is seeded and dormant.
- **Robust / distributionally-robust EG** (would bear on §2.8). Deliberately skipped: §2.8 is blocked
  on A4 for want of a `δ`, and searching it would produce entries no unit can use.
- **The statistics half of Q7** — what a data refresh actually perturbs, and the noise floor against
  which `8.1e-3` nats is judged. §7 row 4 sends this to statistics/econometrics; nothing here.
- **Second forward citation walk** on `budish2013` and `borgwardt2019`. Both are load-bearing and
  both are >5 years old with substantial forward citation; the walk was cut by the Consensus quota
  and is the highest-value continuation.
- **Mechanism-design exposure of the book** (`LENS_GROMOV` OQ6). Owned by
  `DOMAIN_economic-theory`; `fotakis2014` is already in our bib.
