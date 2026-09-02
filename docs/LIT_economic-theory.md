# Literature — economic-theory — the national channel territory problem

**Date:** 2026-09-02 · **Framework:** 0.1-dev · **Reads:** `docs/DOMAIN_economic-theory.md` §6 ·
**Queries logged:** 39 conceptual/near-title (5 Consensus, 34 WebSearch) + 30 Crossref/OpenAlex
resolution calls · **DOIs resolved:** 46/46 (Crossref, 2026-09-02; 0 retraction flags) ·
**Deduplicated against:** `docs/RESEARCH_FINDINGS.md`, `docs/RESEARCH_ADDITIONS.bib`,
`docs/channel_note/references.bib`, `~/resources/economic-theory/FOUNDATIONS.md` — no DOI below
appears in any of them.

Entries in **bold** are keys in `LIT_economic-theory.bib`. Entries in *italic-star* form
(★`key`) are pre-existing keys in `RESEARCH_FINDINGS.md` or `FOUNDATIONS.md`, cited here for
positioning and **not** re-added.

---

## 0. Headlines — what changes the plan

1. **The Shapley value of the roster game has a closed form; the §2.5 Monte-Carlo hand-off to
   statistics is unnecessary.** `f(S) = Σ_z max_{i∈S} S_i(z)` is a *sum over zips of airport
   games*, and **littlechild1973** gives the exact Shapley value of an airport game
   `v(S) = max_{i∈S} c_i` in closed form. Additivity of the Shapley value (**Shapley 1953**,
   FOUNDATIONS) then makes the exact value of all 111 players an `O(#zips · n log n)`
   computation — minutes, not `2^111` and no sampler. **DOMAIN §2.5's "must be Monte-Carlo
   sampled" and §7's Shapley-sampling hand-off should both be struck.** (Sampling entries
   **castro2009** / **castro2017** are retained only as the fallback if the game is later
   redefined as `S ↦ max EG_S`, which is *not* a sum of airport games.)
2. **The balancedness LP is the wrong first test; the right one is an integrality test, and the
   core is provably empty on a two-line instance.** **deng1999** proves that for games given by
   this class of integer programs the core is non-empty **iff** the associated LP has an integer
   optimum — a sharper, cheaper certificate than Bondareva–Shapley. And the coverage game's core
   is empty whenever two wholesalers tie on a zip (`f({1}) = f({2}) = f({1,2}) = 1` forces
   `x_1 + x_2 = 1` with `x_i ≥ 1`). **N5 can be answered before it is computed**, and DOMAIN §8
   question 5 ("does the programme want to know?") is now urgent rather than optional.
   **kern2003** supplies the least-core fallback that keeps the branch alive when the core is
   empty.
3. **The incentive question has a named literature and a named condition, and Hurwicz is not the
   binding citation.** **green1986**'s Nested Range Condition is exactly "when does restricting
   the message space preserve the revelation principle" — DOMAIN §2.7(b)'s `G`-invariant
   drawing is a partial-verification mechanism and NRC is the test it must pass.
   **benporath2014** goes further: allocation of an indivisible object among agents, **no
   transfers**, principal can *verify* at a cost — the audited-book route (GROM **U11**, D5) is a
   solved model with an explicit optimal mechanism (favoured-agent), not an open question.
   **mylovanov2017** is the version with penalties instead of verification cost.
4. **Q3 is not vacuous, and the answer sharpens N3.** Under aligned preferences (both sides rank
   by the same `u_i(A_j)`) the stable matching is **unique** and is the *greedy* top-pair
   matching (**eeckhout2000**, **clark2006**), which is **not** the max-weight matching. So the
   delivered Hungarian-on-logs roster is generically *unstable* and the blocking-pair enumeration
   will find pairs — N3 is decisive, not vacuous, and **echenique2024** shows why: stability and
   efficiency are *different members* of one optimal-transport family indexed by an inequality
   parameter.
5. **The fibration `Σ log g = n log ḡ − D(g)` is a re-derivation of a 1970 result and should be
   cited, not proved.** `D(g)` is the **mean logarithmic deviation** = Theil-L = the Atkinson
   index at inequality aversion ε = 1 (**atkinson1970**, **shorrocks1980**,
   **foster2000**). GROM 3's decomposition is Atkinson's equally-distributed-equivalent identity
   with `g` in place of income. This closes GROM 3 as an original claim and opens it as a
   citation — and it gives D2 a vocabulary the sponsor already owns ("how much inequality
   aversion?" rather than "what exchange rate?").

---

## 1. Nash welfare with heterogeneous-but-proportional valuations *(brief Q1 — bears on §2.1, §2.3, D2)*

- **atkinson1970** — Atkinson, A. B. (1970). *On the measurement of inequality*. Journal of
  Economic Theory 2(3), 244–263. DOI 10.1016/0022-0531(70)90039-6. `[foundation]`
  *Establishes:* the equally-distributed-equivalent income and the family of inequality indices
  derived from a symmetric concave social welfare function; at inequality aversion ε = 1 the
  welfare function is `Σ log` and the index is `1 − exp(−MLD)`.
  *Bears on:* GROM 3's fibration and DOMAIN §1's `D(g)` row. `Σ_i log g_i = n log ḡ − n·MLD(g)`
  **is** Atkinson's identity, so the "base = utilitarian, fiber = egalitarian, MNW = interpolant"
  reading is not new — it is the standard reading of the Atkinson–Kolm family, and the correct
  citation for §2.3's "three defensible criteria" is that they are ε = 0, ε = 1, ε → ∞ of one
  family. Reframes D2 from an exchange rate to a single scalar the sponsor can be asked for.

- **shorrocks1980** — Shorrocks, A. F. (1980). *The Class of Additively Decomposable Inequality
  Measures*. Econometrica 48(3), 613–625. DOI 10.2307/1913126. `[foundation]`
  *Establishes:* the generalized-entropy class is exactly the class of additively decomposable
  inequality measures — within-group plus between-group, with the mean log deviation the unique
  member whose within-group weights are population shares.
  *Bears on:* §2.3, and directly on GROM's "partition-dependent base". If territories are ever
  grouped (by region, by tier, by seniority) the decomposition of `D(g)` into
  within-region + between-region inequality is licensed only for generalized-entropy indices —
  this is the theorem that says the fibration survives regrouping. Also the reason not to use
  a Gini-shaped balance metric: it does not decompose.

- **foster2000** — Foster, J. E. & Shneyerov, A. A. (2000). *Path Independent Inequality
  Measures*. Journal of Economic Theory 91(2), 199–222. DOI 10.1006/jeth.1999.2565.
  `[foundation]`
  *Establishes:* the mean logarithmic deviation is the unique path-independent decomposable
  inequality measure — decomposing by subgroup and then aggregating gives the same answer
  whatever order the aggregation is done in.
  *Bears on:* the two-stage architecture. Path independence is precisely the property that makes
  "draw the map, then staff it" and "staff first, then draw" agree on the inequality term.
  If the programme ever wants to argue the stage split is harmless *on the balance term*, this
  is the theorem; it says nothing about the incumbency term, which is where GROM says the split
  actually costs.

- **barman2025market** — Barman, S., Ebadian, S., Latifian, M. & Shah, N. (2025). *Fair Division
  with Market Values*. Proceedings of the AAAI Conference on Artificial Intelligence 39(13),
  13589–13596. DOI 10.1609/aaai.v39i13.33484. `[frontier]`
  *Establishes:* a model in which indivisible goods carry both agent-specific subjective
  valuations and a single **market value shared identically by all agents**; shows SD-EF1 with
  respect to *both* is impossible in general, but EF1 on the subjective valuations together with
  SD-EF1 on the market valuation is always achievable.
  *Bears on:* §2.1 and the whole `M`-plus-`w_i` structure. This is the closest published model to
  `u_i(z) = M_z·w_i(z)`: `M` is the market value, `w_i` the subjective tilt. It says the two
  fairness demands the programme has been treating as one — balanced *opportunity* and fair
  *continuity* — are formally distinct and **cannot both be met at the EF1-analogue level**.
  That is a direct contradiction of the "balance and continuity are the same objective" reading
  in DOMAIN §1, and it names the achievable compromise.

- **nguyen2023types** — Nguyen, T. T. & Rothe, J. (2023). *Fair and efficient allocation with few
  agent types, few item types, or small value levels*. Artificial Intelligence 314, 103820.
  DOI 10.1016/j.artint.2022.103820. `[frontier]`
  *Establishes:* fixed-parameter and pseudo-polynomial results for EF1/MMS/Nash-welfare-style
  objectives parameterised by the **number of distinct agent types**, the number of item types,
  or the number of value levels.
  *Bears on:* Q1's "modulus in the heterogeneity parameter". This is the nearest thing that
  exists: heterogeneity indexed *discretely* (how many distinct valuation profiles) rather than
  *continuously* (how far `w_i` is from 1). At 111 wholesalers with near-disjoint books the type
  count is ~111, so the parameterisation does not bite — but it is the right shape of statement
  to want, and the honest citation for "the continuous version has not been done" (absence A2).

- **bhaskar2023equity** — Bhaskar, U., Misra, N., Sethia, A. & Vaish, R. (2023). *The Price of
  Equity with Binary Valuations and Few Agent Types*. In Algorithmic Game Theory (SAGT 2023),
  LNCS, 271–289. DOI 10.1007/978-3-031-43254-5_16. `[frontier]`
  *Establishes:* bounds on the welfare loss from equitability-up-to-one-good across the whole
  `p`-mean family (utilitarian, Nash, egalitarian as special cases), expressed in the **number of
  agent types** rather than the number of agents — showing the agent-count bounds are pessimistic
  when types are few.
  *Bears on:* D2 / N4 directly. The three criterion maps of §2.3 are three points of the `p`-mean
  family, and this gives the first published bound on how far apart they can be as a function of
  heterogeneity. If the maps coincide (N4's "overturns if"), this is why; if they diverge, this
  bounds by how much. Binary-valuation restriction is the caveat.

- **bertsimas2011** — Bertsimas, D., Farias, V. F. & Trichakis, N. (2011). *The Price of
  Fairness*. Operations Research 59(1), 17–31. DOI 10.1287/opre.1100.0865. `[foundation]`
  *Establishes:* tight worst-case bounds on the utilitarian efficiency lost by imposing
  proportional fairness (= Nash) or max-min fairness, for a broad class of allocation problems —
  the proportional-fairness loss is `O(1/√n)` of optimum on the standard normalisation.
  *Bears on:* D2 and the §2.3 deliverable. This is the number to put next to the three maps: it
  says *a priori* how much premium `P` the Nash map can be costing against the utilitarian one,
  in the problem's own units, before any of the three maps is computed. It is also the correct
  OR-side companion to §2.3's Kalai/Thomson axiomatics, and it is the paper a sponsor who asks
  "what does fairness cost us" is actually asking for.

---

## 2. MNW with a participation margin *(brief Q2 — bears on §2.1, §2.6, D1)*

- **budish2011** — Budish, E. (2011). *The Combinatorial Assignment Problem: Approximate
  Competitive Equilibrium from Equal Incomes*. Journal of Political Economy 119(6), 1061–1103.
  DOI 10.1086/664613. `[foundation]`
  *Establishes:* existence of an **approximate** CEEI with budgets unequal but arbitrarily close,
  under combinatorial (capacity, scheduling) constraints where exact CEEI fails; the mechanism is
  approximately efficient, satisfies EF1 and a bounded-maximin criterion, and is strategyproof in
  large markets.
  *Bears on:* §2.2 head-on. DOMAIN §2.2 cites **Eisenberg & Gale 1959** and **Hylland &
  Zeckhauser 1979** for the equal-budget device; Budish is the paper that makes it work when the
  feasible set is combinatorial rather than a simplex — which is exactly the `k = 13` quota and
  the partition constraint. It also supplies the honest form of the §2.2 claim: the bound is
  an *approximate* equilibrium with a quantified budget perturbation, not an exact one, and the
  strategyproof-in-large result is a second, cheaper answer to §2.7 than the `G`-invariance
  construction.

- **aignerhorev2022** — Aigner-Horev, E. & Segal-Halevi, E. (2022). *Envy-free matchings in
  bipartite graphs and their applications to fair division*. Information Sciences 587, 164–187.
  DOI 10.1016/j.ins.2021.11.059. `[tool-we-lack]`
  *Establishes:* the notion of an **envy-free matching** — a matching in which *no unmatched
  agent envies a matched agent* — proves such matchings always exist (possibly empty),
  characterises the maximum one, and gives a polynomial algorithm; applies it to fair division
  where not every agent is served.
  *Bears on:* **this is the fairness axiom across the selection boundary that DOMAIN §2.1 says it
  "cannot say" anything about, and §2.6 substitutes a bankruptcy analogy for.** The 98 unselected
  are the unmatched side; EFM asks exactly the question a non-selected wholesaler asks. It is
  checkable on the delivered roster with the same `13 × 111` sweep as N3, and it converts §2.6
  from a framing paragraph into a computation. Caveat: the notion is ordinal/threshold-based and
  does not by itself carry a Nash-welfare guarantee (see absence A3).

- **gan2019** — Gan, J., Suksompong, W. & Voudouris, A. A. (2019). *Envy-freeness in house
  allocation problems*. Mathematical Social Sciences 101, 104–106.
  DOI 10.1016/j.mathsocsci.2019.07.005. `[frontier]`
  *Establishes:* polynomial-time decision and construction of envy-free assignments of `m` houses
  to `n` agents, **including the `m < n` case where some agents necessarily get nothing**, via
  iterative removal of contentious houses; and a probabilistic existence result when houses
  exceed agents by a log factor.
  *Bears on:* §2.6 and D1. The 13-of-111 selection is `m < n` house allocation with `m = 13`. This
  is the cleanest existence-and-algorithm statement in the participation-margin regime, and its
  "contentious house" removal is structurally the same object as GROM's contested-zip census.
  Unit demand only — it does not cover bundles — which is why it bounds the problem rather than
  solving it.

- **belahcene2021** — Belahcène, K., Mousseau, V. & Wilczynski, A. (2021). *Combining Fairness
  and Optimality when Selecting and Allocating Projects*. Proceedings of the Thirtieth
  International Joint Conference on Artificial Intelligence (IJCAI 2021), 38–44.
  DOI 10.24963/ijcai.2021/6. `[frontier]`
  *Establishes:* a model where a **subset of projects is selected and simultaneously allocated**,
  with fairness measured on the joint outcome; complexity results and exact methods for combining
  a fairness criterion with an optimality criterion in one problem.
  *Bears on:* the two-stage split. This is the closest published treatment of "selection and
  allocation are one problem, not two", i.e. the joint stage-1+stage-2 formulation DOMAIN §2.4
  and CLAUDE.md's open-loop draw/match note both circle. Read before any attempt to close the
  loop with feedback cuts.

- **caragiannis2019efx** — Caragiannis, I., Gravin, N. & Huang, X. (2019). *Envy-Freeness Up to
  Any Item with High Nash Welfare: The Virtue of Donating Items*. Proceedings of the 2019 ACM
  Conference on Economics and Computation (EC '19), 527–545. DOI 10.1145/3328526.3329574.
  `[contradicts-or-sharpens]`
  *Establishes:* for additive valuations there is always a **partial** allocation that is EFX and
  achieves at least half the maximum Nash welfare of the full instance; the factor 1/2 is tight.
  *Bears on:* §2.1's failure mode and FRAME §4's hard "every zip assigned" constraint. It says the
  cheapest route to a strong fairness guarantee is to *not allocate everything* — which FRAME
  forbids. Worth quoting to the sponsor precisely because it prices the constraint: the hard
  coverage requirement is what forces the programme down to EF1 rather than EFX.

- **chaudhury2021** — Chaudhury, B. R., Kavitha, T., Mehlhorn, K. & Sgouritsa, A. (2021). *A
  Little Charity Guarantees Almost Envy-Freeness*. SIAM Journal on Computing 50(4), 1336–1358.
  DOI 10.1137/20M1359134. `[frontier]`
  *Establishes:* an EFX allocation always exists in which fewer than `n` goods are left
  unallocated (donated), and no agent envies the donated pile.
  *Bears on:* the same trade as above, with a *count* rather than a welfare factor: at `n = 13`,
  at most 12 zips withheld buys EFX. That is the same order as §2.2's `k − 1 = 12` split-zip
  budget, which is a coincidence worth checking — if the same 12 zips do both jobs, the
  integrality gap and the fairness gap are one object.

- **barman2023gac** — Barman, S., Khan, A., Shyam, S. & Sreenivas, K. V. N. (2023). *Guaranteeing
  Envy-Freeness under Generalized Assignment Constraints*. Proceedings of the 24th ACM Conference
  on Economics and Computation (EC '23), 242–269. DOI 10.1145/3580507.3597698. `[frontier]`
  *Establishes:* **feasible** envy-freeness (FEF/FEFx) — envy evaluated only against subsets the
  envying agent could actually have received, given agent-specific sizes and budgets — with
  existence for divisible goods and FEFx existence plus a pseudo-polynomial algorithm for
  indivisible goods, allowing a charity set.
  *Bears on:* §2.1's envy matrix. If territories carry capacity (travel, producing-advisor count —
  CLAUDE.md's unbuilt capacity constraint), plain EF1 is the wrong test and FEFx is the right one:
  a wholesaler cannot envy a bundle they could not work. This is the entry to reach for the first
  time A6's operational coverage rule turns out to exist.

---

## 3. Stability vs welfare-optimality under aligned preferences *(brief Q3 — bears on §2.4, N3)*

- **echenique2024** — Echenique, F., Root, J. & Sandomirskiy, F. (2024). *Stable Matching as
  Transportation*. Proceedings of the 25th ACM Conference on Economics and Computation (EC '24),
  418. DOI 10.1145/3670865.3673585. `[frontier]`
  *Establishes:* for matching markets with **aligned preferences** (both sides ranked by a common
  pair value), stability, efficiency and fairness are the solutions to a *parametric family of
  optimal-transport problems* indexed by a parameter reflecting inequality aversion; the paper
  characterises the trade-offs and shows stability can produce large welfare inequality even
  among near-identical agents.
  *Bears on:* **Q3's answer, and it is the single most useful new entry.** (a) It settles that
  stability and welfare-optimality are *different* points of one family under exactly our
  induced-preference construction, so N3 is not vacuous. (b) The inequality parameter is the same
  scalar as §1's Atkinson ε — so §2.3's "choose the criterion" and §2.4's "audit stability" are
  the *same* one-parameter decision, which collapses two of DOMAIN §4's steps into one. (c) It
  connects to **Warren 2025** (FOUNDATIONS) on the transport side, which the programme already
  uses for the power-diagram structure. The EC record is an abstract; the full text is
  arXiv:2402.13378 and should be read from there.

- **eeckhout2000** — Eeckhout, J. (2000). *On the uniqueness of stable marriage matchings*.
  Economics Letters 69(1), 1–8. DOI 10.1016/S0165-1765(00)00263-9. `[foundation]`
  *Establishes:* the Sequential Preference Condition (SPC) — if agents can be ordered so that each
  side's rankings are consistent with a common sequence — is **sufficient** for the stable
  matching to be unique; aligned preferences satisfy it, and the unique stable matching is found
  by repeatedly matching the current top-top pair.
  *Bears on:* N3, decisively. Under the induced preferences of §2.4 both sides rank by
  `u_i(A_j)`, SPC holds, and therefore the stable roster is the **greedy top-pair** matching.
  The delivered roster is Hungarian **max-weight on logs**. Greedy ≠ max-weight in general, so
  the delivered roster is generically unstable and blocking pairs exist. §2.4's five-minute
  "is the audit vacuous?" check is answered here: it is not vacuous, it is *guaranteed to fire*
  unless greedy happens to coincide with Hungarian on this instance — which is itself a cheap
  test and should be N3's first line.

- **clark2006** — Clark, S. (2006). *The Uniqueness of Stable Matchings*. Contributions in
  Theoretical Economics 6(1), 1–28. DOI 10.2202/1534-5971.1283. `[foundation]`
  *Establishes:* the No Crossing Condition, a weaker sufficient condition for uniqueness than
  SPC, and its relation to assortative-matching structure.
  *Bears on:* the same argument, with a weaker hypothesis — useful if the induced preferences are
  perturbed (e.g. by the `ρ` compactness term breaking exact alignment) and SPC no longer holds
  exactly. Cite alongside eeckhout2000 rather than instead of it.

- **consuegra2013** — Consuegra, M. E., Kumar, R. & Narasimhan, G. (2013). *Comment on "On the
  Uniqueness of Stable Marriage Matchings"*. Economics Letters 121(3), 468.
  DOI 10.1016/j.econlet.2013.09.019. `[contradicts-or-sharpens]`
  *Establishes:* Eeckhout's claim that SPC is *necessary* for uniqueness is false already at
  `n = 3`; SPC is sufficient only.
  *Bears on:* precision of any claim the programme writes down. Cite eeckhout2000 for
  sufficiency and this for the boundary; do **not** write "the stable matching is unique iff".

- **niederle2009** — Niederle, M. & Yariv, L. (2009). *Decentralized Matching with Aligned
  Preferences*. NBER Working Paper 14840. DOI 10.3386/w14840. `[foundation]`
  *Establishes:* in a decentralised offer game with **aligned preferences** and complete
  information (or no frictions) there is an equilibrium yielding the stable match; without
  alignment, iterated elimination of weakly dominated strategies leaves multiple outcomes even
  under complete information.
  *Bears on:* §2.4's argument to leadership and FRAME §2's low-reversibility row. It says the
  aligned-preference structure the programme has by construction is exactly the structure under
  which an *announced* roster that is not stable will be renegotiated toward the stable one by
  the parties themselves — the mechanism behind **Roth 1984**'s unravelling, in our preference
  structure. Working paper; no journal version found (see query log).

---

## 4. Strategy-proofness by restricted message space *(brief Q4 — bears on §2.7, D5, U11)*

- **green1986** — Green, J. R. & Laffont, J.-J. (1986). *Partially Verifiable Information and
  Mechanism Design*. The Review of Economic Studies 53(3), 447–456. DOI 10.2307/2297639.
  `[foundation]`
  *Establishes:* when an agent of type `θ` can only send messages in a type-dependent set `M(θ)`,
  the revelation principle holds **iff** the message correspondence satisfies the **Nested Range
  Condition**; without NRC, indirect mechanisms can strictly outperform direct truthful ones.
  *Bears on:* **§2.7(b) and D5, and it replaces Hurwicz as the load-bearing citation.** DOMAIN
  §2.7 claims that restricting the message space to `G`-invariants yields strategy-proofness
  "by construction, with no theorem required `[claim]`". Green–Laffont is the theorem, and it is
  conditional: the claim holds only if the invariant-message correspondence satisfies NRC. That
  is a checkable algebraic condition on `(ℝ_{>0})^R`-orbits and it must be checked before the
  claim is written. It also formalises the GROM 13.1 distinction the domain plan already made:
  audited magnitudes are a restriction of `M(θ)`, not a free report.

- **milgrom1981** — Milgrom, P. R. (1981). *Good News and Bad News: Representation Theorems and
  Applications*. The Bell Journal of Economics 12(2), 380–391. DOI 10.2307/3003562.
  `[foundation]`
  *Establishes:* with verifiable claims and a sceptical receiver, disclosure **unravels** to full
  revelation — anything withheld is presumed to be the worst it could be.
  *Bears on:* the governance framing of A7 and the 98's incentive to inflate. If reported book is
  *verifiable on demand* (even at cost), unravelling means the programme does not need to audit
  everyone — it needs only a credible audit threat plus the presumption that unaudited claims are
  discounted. That is a cheaper policy than universal audit and it is the argument to put in
  front of the sponsor next to U11.

- **bull2007** — Bull, J. & Watson, J. (2007). *Hard evidence and mechanism design*. Games and
  Economic Behavior 58(1), 75–93. DOI 10.1016/j.geb.2006.03.003. `[foundation]`
  *Establishes:* a general evidence structure ("hard evidence") and conditions — normality /
  evidentiary-normality — under which the revelation principle extends and full implementation is
  possible; relates evidence structures to the NRC lineage.
  *Bears on:* the same slot as green1986, in the modern formulation. Use this to state what
  structure the audited system-of-record data must have for the §2.7 argument to go through.

- **deneckere2008** — Deneckere, R. & Severinov, S. (2008). *Mechanism design with partial state
  verifiability*. Games and Economic Behavior 64(2), 487–513. DOI 10.1016/j.geb.2007.12.006.
  `[frontier]`
  *Establishes:* characterisation of implementable social choice functions when the state is only
  partially verifiable, generalising Green–Laffont beyond NRC and identifying when the designer
  gains from indirect mechanisms.
  *Bears on:* the fallback if NRC fails on our invariant message space. Answers "what can still be
  implemented" rather than "is the revelation principle valid".

- **benporath2012** — Ben-Porath, E. & Lipman, B. L. (2012). *Implementation with partial
  provability*. Journal of Economic Theory 147(5), 1689–1724. DOI 10.1016/j.jet.2012.01.017.
  `[frontier]`
  *Establishes:* a measurability condition on the evidence structure that is necessary for
  implementation and, with ≥ 3 agents and small transfers, sufficient — including for
  state-dependent preferences.
  *Bears on:* §2.7's transfers boundary. It quantifies exactly how much of FRAME §7's
  no-transfers scope has to be relaxed: "small transfers beyond those called for by the function"
  — arbitrarily small, not VCG-scale. That is a materially smaller ask of the sponsor than the
  VCG sentence DOMAIN §2.7(a) proposes, and it should be offered alongside it.

- **kartik2012** — Kartik, N. & Tercieux, O. (2012). *Implementation with evidence*. Theoretical
  Economics 7(2), 323–355. DOI 10.3982/te723. `[frontier]`
  *Establishes:* with evidence, **Maskin monotonicity is no longer necessary** for Nash
  implementation; a weaker condition suffices, and with costly evidence, "evidence-monotonicity"
  characterises implementability.
  *Bears on:* §2.7(c) directly — it **sharpens** the plan's use of **Maskin 1999**. DOMAIN §2.7
  says "Maskin 1999 is the test to apply before proposing any rule". Once the input is audited
  data rather than a report, that test is the wrong one and this paper says so.

- **benporath2014** — Ben-Porath, E., Dekel, E. & Lipman, B. L. (2014). *Optimal Allocation with
  Costly Verification*. American Economic Review 104(12), 3779–3813. DOI 10.1257/aer.104.12.3779.
  `[tool-we-lack]`
  *Establishes:* a principal allocates an indivisible object among `I` agents who privately know
  the principal's value of giving it to them; **no monetary transfers**, but the principal may
  verify a report at a cost. The optimum is a **favoured-agent mechanism**: fix `i*` and a
  threshold `v*`; if all others report below `v*`, `i*` gets the object unchecked; otherwise the
  highest reporter is checked and gets it only if confirmed. All optima are randomisations over
  such mechanisms.
  *Bears on:* **D5, and it is the model the programme is actually in.** No transfers (FRAME §7),
  private information about own book, an audit that costs something. This gives an *optimal*
  answer to "how much auditing, of whom" rather than the binary "audited or not" that U11 poses.
  The `13` seats make it a multi-object version, which is the gap — but the single-object result
  is the right first read and it turns D5 from a yes/no question into a design.

- **mylovanov2017** — Mylovanov, T. & Zapechelnyuk, A. (2017). *Optimal Allocation with Ex Post
  Verification and Limited Penalties*. American Economic Review 107(9), 2666–2694.
  DOI 10.1257/aer.20140494. `[frontier]`
  *Establishes:* the same allocation problem where verification is ex post and the principal can
  impose only a bounded penalty on a caught liar; characterises the optimal mechanism.
  *Bears on:* the realistic version of D5. A wholesaler caught overstating book cannot be fined;
  the only penalty available is losing the seat. This is that model.

- **benporath2019** — Ben-Porath, E., Dekel, E. & Lipman, B. L. (2019). *Mechanisms With
  Evidence: Commitment and Robustness*. Econometrica 87(2), 529–566. DOI 10.3982/ECTA14991.
  `[frontier]`
  *Establishes:* in allocation problems with evidence, the optimal mechanism can be implemented
  **without commitment** and is robust — the principal has no incentive to deviate ex post.
  *Bears on:* governance. FRAME §2 says leadership signs the map; a mechanism that requires the
  channel to commit in advance to an audit rule it will not want to follow is not implementable
  in this organisation. This says it does not have to.

- **caragiannis2012** — Caragiannis, I., Elkind, E., Szegedy, M. & Yu, L. (2012). *Mechanism
  design: from partial to probabilistic verification*. Proceedings of the 13th ACM Conference on
  Electronic Commerce (EC '12), 266–283. DOI 10.1145/2229012.2229035. `[frontier]`
  *Establishes:* generalises Green–Laffont partial verification to **probabilistic** verification
  (a misreport is caught with some probability), characterises when the revelation principle
  survives, and gives the computational picture.
  *Bears on:* the computer-science-side formulation of §2.7(b), and the version that matches a
  *sampled* audit rather than a full one. The bridge between the economics entries above and the
  strategyproofness results already held in `RESEARCH_FINDINGS` §4A.

---

## 5. Max-coverage games as cooperative games *(brief Q5 — bears on §2.5, N5, N6)*

- **littlechild1973** — Littlechild, S. C. & Owen, G. (1973). *A Simple Expression for the Shapley
  Value in a Special Case*. Management Science 20(3), 370–372. DOI 10.1287/mnsc.20.3.370.
  `[tool-we-lack]`
  *Establishes:* for a game whose characteristic function is `v(S) = max_{i∈S} c_i` (the airport
  game), the Shapley value has a closed form: sort the `c_i` ascending, and each player pays an
  equal share of each successive increment among all players at or above it — computable in
  `O(n log n)`.
  *Bears on:* **N6 and DOMAIN §7's Shapley-sampling hand-off, which this removes.**
  `f(S) = Σ_z max_{i∈S} S_i(z)` is a *sum* of airport games, one per zip. The Shapley value is
  additive (**Shapley 1953**, FOUNDATIONS), so `φ_i(f) = Σ_z φ_i(f_z)` and each `φ_i(f_z)` is
  Littlechild–Owen's formula. Exact values for all 111 wholesalers over 1,229 zips, no sampling,
  no error bars, minutes of compute. This is the highest-value single finding in this sweep and
  it should be verified against a brute-force check on a 5-player toy instance before use.

- **deng1999** — Deng, X., Ibaraki, T. & Nagamochi, H. (1999). *Algorithmic Aspects of the Core of
  Combinatorial Optimization Games*. Mathematics of Operations Research 24(3), 751–766.
  DOI 10.1287/moor.24.3.751. `[foundation]`
  *Establishes:* a general integer-programming form for combinatorial optimisation games
  (covering, packing, partitioning) in which **the core is non-empty iff the associated LP
  relaxation has an integer optimal solution**; algorithms for core membership and construction.
  *Bears on:* **N5, and it replaces the balancedness LP as the test to run.** Bondareva–Shapley
  (**Shapley 1967**) has exponentially many constraints; this reduces the same question to an
  integrality check on an LP the programme is already solving (`allocate_districts` /
  the transportation LP). It also connects the core question to the integrality-gap question of
  §2.2 — they are the same duality gap, which is a structural result DOMAIN does not currently
  have.

- **deng2000** — Deng, X., Ibaraki, T., Nagamochi, H. & Zang, W. (2000). *Totally balanced
  combinatorial optimization games*. Mathematical Programming 87(3), 441–452.
  DOI 10.1007/s101070050005. `[foundation]`
  *Establishes:* characterises which combinatorial optimisation games are **totally** balanced
  (every subgame has non-empty core), via integrality of the associated LP on every subinstance.
  *Bears on:* the stronger form of N5. Non-empty core for the chosen 13 is weaker than "no
  sub-coalition of any size can object"; if leadership will face objections from arbitrary
  subgroups, total balancedness is the property to test and this is the test.

- **goemans2004** — Goemans, M. X. & Skutella, M. (2004). *Cooperative facility location games*.
  Journal of Algorithms 50(2), 194–214. DOI 10.1016/S0196-6774(03)00098-1.
  `[contradicts-or-sharpens]`
  *Establishes:* for facility-location cost games, deciding whether the core is non-empty is
  **NP-complete** (with and without transferable utility), as is deciding whether a given
  allocation is in the core; a fair cost allocation exists iff the LP relaxation has no
  integrality gap.
  *Bears on:* the honest cost of N5. Our game is a coverage game on a center-based (facility-like)
  structure, so "run the balancedness LP" is not automatically cheap — the general problem is
  NP-complete and the tractability, if any, comes from deng1999's integrality route on our
  specific formulation. **Cite this whenever N5 is scoped**, or the estimate will be wrong.

- **kern2003** — Kern, W. & Paulusma, D. (2003). *Matching Games: The Least Core and the
  Nucleolus*. Mathematics of Operations Research 28(2), 294–308.
  DOI 10.1287/moor.28.2.294.14477. `[tool-we-lack]`
  *Establishes:* polynomial algorithms for the least core and the nucleolus of matching games —
  the canonical "core is empty, now what" construction, computed by a sequence of LPs.
  *Bears on:* **N5's failure branch and §2.6.** DOMAIN §2.5 says an empty core means "the honest
  report is: no selection is coalition-proof". This says the report can be better than that: the
  **least core** quantifies *how far* from coalition-proof, in the objective's own units, and the
  nucleolus picks the selection minimising the loudest objection — which is exactly what §2.6
  argues FRAME §3's "do not starve anybody" means (**Schmeidler 1969**, FOUNDATIONS). This is the
  bridge that makes §2.5 and §2.6 one computation instead of two narratives.

- **deng1994** — Deng, X. & Papadimitriou, C. H. (1994). *On the Complexity of Cooperative
  Solution Concepts*. Mathematics of Operations Research 19(2), 257–266.
  DOI 10.1287/moor.19.2.257. `[foundation]`
  *Establishes:* the complexity landscape of core membership, core non-emptiness, the Shapley
  value and the bargaining set for games given by a succinct (graph/IP) representation.
  *Bears on:* scoping every claim in §2.5. The reference to cite for "why the exact Shapley value
  is generally hard" — which makes littlechild1973's escape a *finding* rather than an obvious
  fact.

- **chen2020coreness** — Chen, W., Shan, X., Sun, X. & Zhang, J. (2020). *Coreness of cooperative
  games with truncated submodular profit functions*. Theoretical Computer Science 822, 49–60.
  DOI 10.1016/j.tcs.2020.04.004. `[frontier]`
  *Establishes:* for profit games with truncated submodular characteristic functions, core
  emptiness is decidable in polynomial time and a core allocation constructible when non-empty;
  hardness and approximation results for the relative and absolute least core when it is empty.
  *Bears on:* §2.5's exact regime. `f(S) = Σ_z max_{i∈S} S_i(z)` is monotone submodular; this is
  the nearest published class and the source of the "core emptiness is *decidable*, cheaply"
  claim. Read together with goemans2004, which says it is not cheap in general — the difference
  is the structure, and identifying which side our `f` falls on is the concrete N5 task.

- **castro2009** — Castro, J., Gómez, D. & Tejada, J. (2009). *Polynomial calculation of the
  Shapley value based on sampling*. Computers & Operations Research 36(5), 1726–1730.
  DOI 10.1016/j.cor.2008.04.004. `[tool-we-lack]`
  *Establishes:* the permutation-sampling estimator of the Shapley value, its statistical
  properties and complexity.
  *Bears on:* the fallback only. If the characteristic function is redefined as `S ↦ max EG_S`
  (DOMAIN §2.5's "better" option) it is no longer a sum of airport games and littlechild1973 does
  not apply; then this is the method, and each sample costs one EG solve.

- **castro2017** — Castro, J., Gómez, D., Molina, E. & Tejada, J. (2017). *Improving polynomial
  estimation of the Shapley value by stratified random sampling with optimum allocation*.
  Computers & Operations Research 82, 180–188. DOI 10.1016/j.cor.2017.01.019. `[tool-we-lack]`
  *Establishes:* stratification by coalition size with Neyman-optimal allocation, reducing the
  estimator's variance for a fixed budget.
  *Bears on:* the sampler's design if the fallback is taken — the sampling-design half of DOMAIN
  §7's statistics hand-off, which is otherwise unspecified.

- **chalkiadakis2012** — Chalkiadakis, G., Elkind, E. & Wooldridge, M. (2012). *Computational
  Aspects of Cooperative Game Theory*. Synthesis Lectures on AI and Machine Learning, Springer.
  DOI 10.2200/S00355ED1V01Y201107AIM016. `[foundation]`
  *Establishes:* the standard survey of representations, core/least-core/nucleolus/Shapley
  computation, and complexity for succinctly represented games including coverage and induced
  subgraph games.
  *Bears on:* the single reference to hand anyone implementing §2.5. Included as `foundation`
  under the survey exception; it is the only survey in this file.

---

## 6. Sales-territory alignment as a fair-division / incentive problem *(brief Q6 — bears on §2.7 and FRAME's "niche unoccupied" claim)*

- **basu1985** — Basu, A. K., Lal, R., Srinivasan, V. & Staelin, R. (1985). *Salesforce
  Compensation Plans: An Agency Theoretic Perspective*. Marketing Science 4(4), 267–291.
  DOI 10.1287/mksc.4.4.267. `[foundation]`
  *Establishes:* the canonical principal–agent model of salesforce compensation — hidden effort,
  risk-averse agent, uncertain territory outcome — and the shape of the optimal commission
  schedule.
  *Bears on:* FRAME §7's scope boundary. This is the literature that *does* treat the salesforce
  as strategic, and it is entirely about **compensation**, not about the map. Cite it to state
  precisely where the programme's niche begins.

- **lal1986** — Lal, R. & Staelin, R. (1986). *Salesforce Compensation Plans in Environments with
  Asymmetric Information*. Marketing Science 5(3), 179–198. DOI 10.1287/mksc.5.3.179.
  `[contradicts-or-sharpens]`
  *Establishes:* when the salesperson privately knows their **territory potential**, the optimal
  plan is a **menu of contracts** that screens on that information; a single plan is dominated.
  *Bears on:* §2.7 and the "the niche is unoccupied" claim. Marketing science has known since
  1986 that reps privately know their territory's potential and will misreport it — but the
  response has always been a compensation menu, never a change to the territory-drawing rule.
  **The niche survives, but not for the reason FRAME states**: it is unoccupied because the field
  chose the compensation instrument, not because nobody noticed the incentive problem. That is a
  more defensible claim and it should replace the current one.

- **rao1990** — Rao, R. C. (1990). *Compensating Heterogeneous Salesforces: Some Explicit
  Solutions*. Marketing Science 9(4), 319–341. DOI 10.1287/mksc.9.4.319.
  `[contradicts-or-sharpens]`
  *Establishes:* explicit optimal menus (quota, quota bonus, constant commission) for a salesforce
  heterogeneous in ability, under asymmetric information.
  *Bears on:* the same boundary, with the closed forms. Also the citation for "heterogeneity
  across the 111 is a first-order design variable in this literature", which supports §2.3's
  claim that the criterion choice is a distributive decision, not a technicality.

- **caldieraro2009** — Caldieraro, F. & Coughlan, A. T. (2009). *Optimal Sales Force
  Diversification and Group Incentive Payments*. Marketing Science 28(6), 1009–1026.
  DOI 10.1287/mksc.1090.0493. `[frontier]`
  *Establishes:* territory **allocation** and compensation interact: allocating salespeople to
  negatively correlated territories plus a group commission can raise profit even when average
  territory performance falls; balanced allocation dominates imbalanced allocation in a large
  salesforce when a group component exists.
  *Bears on:* the only paper found that makes territory *design* an endogenous variable in an
  incentive model. It supports FRAME's balance objective from an unexpected direction — balance is
  optimal *given* a group-incentive component — and it flags a variable the programme has not
  modelled at all: correlation across territory outcomes. Worth one sentence in the note and no
  more, since compensation is out of scope.

- **syam2013** — Syam, N. B., Hess, J. D. & Yang, Y. (2013). *Sales contests versus quotas with
  imbalanced territories*. Marketing Letters 24(3), 229–244. DOI 10.1007/s11002-012-9211-4.
  `[contradicts-or-sharpens]`
  *Establishes:* territory imbalance hurts a sales *contest* more than a *quota* system — in a
  contest the strong-territory rep need only mimic the weak one's effort, so the weak rep shirks;
  handicapping fixes it but is rarely done.
  *Bears on:* FRAME §3's tolerance and the value of balance. This is the closest thing to a
  *quantified consequence of imbalance* in the economics literature, and it says the consequence
  depends on the compensation instrument — which the programme has declared out of scope. If the
  channel runs contests, the balance requirement is doing more work than the map's own objective
  admits; if it runs quotas, less.

- **smith2000** — Smith, K., Jones, E. & Blair, E. (2000). *Managing Salesperson Motivation in a
  Territory Realignment*. Journal of Personal Selling & Sales Management 20(4), 215–226.
  DOI 10.1080/08853134.2000.10754242. `[tool-we-lack]`
  *Establishes:* two field studies showing that after a realignment, expectancy-theory
  interventions work for reps whose potential **increased** and **justice-based** interventions
  work for reps whose potential **decreased**.
  *Bears on:* **§2.6 and the 98, and it is the empirical counterpart to the nucleolus argument.**
  It is direct evidence that the losing side of a realignment responds to *procedural and
  distributive justice*, not to efficiency arguments — which is the case for reporting a
  least-core / nucleolus number and a Shapley ranking rather than a welfare optimum. Also the
  citation for FRAME §2's "must be defensible line by line".

- **arnold2009** — Arnold, T. J., Landry, T. D., Scheer, L. K. & Stan, S. (2009). *The Role of
  Equity and Work Environment in the Formation of Salesperson Distributive Fairness Judgments*.
  Journal of Personal Selling & Sales Management 29(1), 61–80. DOI 10.2753/pss0885-3134290104.
  `[frontier]`
  *Establishes:* salespeople's distributive-fairness judgements are formed against *multiple*
  referents — other salespeople in the firm, other employees, salespeople outside the firm — and
  environmental conditions moderate which referent binds; outcomes include satisfaction, voice
  and exit.
  *Bears on:* the envy matrix of N1. It says the `13 × 13` internal envy comparison is only one of
  the referents the affected population actually uses, and that the 98-vs-13 comparison (an
  *outside-the-selected-group* referent) is a live one. Supports adding the
  across-the-boundary check of **aignerhorev2022** rather than stopping at internal EF1.

---

## Shortlist — five papers that would most change §4 if read this week

1. **littlechild1973** (Shapley value of the airport game, closed form) — because
   `f = Σ_z (airport game)` and additivity make N6 exact and cheap. Deletes a hand-off, deletes a
   sampling-error caveat, and makes D4 answerable this week rather than after a sampler is built.
2. **deng1999** (core non-empty iff the LP has an integer optimum) — because it replaces the
   exponential balancedness LP with an integrality check on an LP already in the codebase, and
   ties N5 to the §2.2 integrality gap as one object.
3. **echenique2024** (stable matching as transport, aligned preferences) — because it proves
   stability and welfare-optimality are different points of one inequality-indexed family under
   exactly our induced preferences, collapsing §2.3's criterion choice and §2.4's stability audit
   into one parameter, and connecting both to the transport structure the map already has.
4. **benporath2014** (optimal allocation with costly verification, no transfers) — because it is
   the programme's actual mechanism-design problem, stated and solved: it converts D5 from
   "may the drawing see books?" into "which agent is favoured and at what audit threshold".
5. **barman2025market** (fair division with market values) — because it is the only published
   model with a common market value plus subjective valuations, and it says the two fairness
   demands the programme has treated as one objective are formally incompatible at the
   EF1-analogue level, naming the achievable compromise.

Runner-up, and the one to read if only the audit matters: **eeckhout2000** — it predicts N3's
result before N3 is run.

---

## Absence ledger

Every row was searched on **2026-09-02**. "Consensus" = the Consensus academic index (Semantic
Scholar / PubMed / Scopus / arXiv). Venue coverage of the Consensus index for these fields
includes EC, AAMAS, IJCAI, AAAI, SAGT, WINE, GEB, JET, Econometrica, SCW, MOR, TEAC, Math.
Programming, Marketing Science, Management Science, EJOR.

| claim | queries | venues / indexes searched | date | nearest miss |
|---|---|---|---|---|
| **A1.** The fiberwise reading of the equal-split result — "equal-size districting is exactly MNW-optimal on level sets of total welfare, and only there" — is not stated in the fair-division literature. | C1, C4, W7, W8, W28, W29 | Consensus (fair division + welfare economics), Crossref bibliographic search, targeted JET/Econometrica near-title | 2026-09-02 | The identity itself is 55 years old in *inequality measurement*: **atkinson1970** (ε = 1), **shorrocks1980** (generalized entropy), **foster2000** (MLD unique path-independent). ★`marshall2011` (already held) gives the Schur-concavity half. No fair-division paper found that states the level-set/fiber form. **Recommendation: stop claiming it, cite it.** |
| **A2.** No modulus — no quantitative bound on MNW/EF1 guarantees continuous in a heterogeneity parameter τ for `u_i(z) = M_z·w_i(z)` with `w_i ∈ [1−τ, 1+τ]`. | C1, C4, W9, W25 | Consensus, arXiv (cs.GT), EC/AAAI/IJCAI/SAGT proceedings via Crossref | 2026-09-02 | **nguyen2023types** (parameter = *number of agent types*, discrete not continuous); **bhaskar2023equity** (price of equity in number of types, binary valuations only); **barman2025market** (common market value + subjective valuations, but no closeness parameter and no Nash bound); ★`fengli2025` (already held: the general weighted-NSW ratio is *governed by* the identical-valuations gap — the right framing, wrong direction). **This is a genuine gap and a publishable one.** |
| **A3.** No treatment of maximum Nash welfare where only `k` of `n` agents receive bundles by design, with a fairness axiom across the selection boundary. | C2, W18, W19 | Consensus, EC/AAMAS/IJCAI/AAAI via Crossref, MSS / GEB near-title | 2026-09-02 | **aignerhorev2022** defines exactly the right axiom (no unmatched agent envies a matched one) but for *matchings*, ordinally, with no Nash-welfare statement; **gan2019** handles `m < n` house allocation, unit demand only; **belahcene2021** selects and allocates *projects* but serves all agents; ★`gahlawat2026incomplete` (already held) leaves *items* unallocated, not agents. The bundle-valued, Nash-welfare version does not exist. |
| **A4.** No result on whether MNW's EF1 guarantee survives a nonzero disagreement point on indivisible goods. | W18, W34, C2 | Consensus, arXiv cs.GT, SCW / GEB near-title | 2026-09-02 | ★`mariotti1998` / ★`xu2005` (FOUNDATIONS) treat nonconvex bargaining with `d ≠ 0` but say nothing about EF1; ★`caragiannis2019` is stated at `d = 0` and FOUNDATIONS records that subtracting a constant voids it. **DOMAIN §2.1's failure mode (ii) is therefore correct and unrepaired by the literature** — if A2 makes `d > 0`, there is no weaker EF1-flavoured theorem to fall back on, only a lottery. |
| **A5.** No published statement, with counterexample, that a max-weight matching under aligned (common pair-value) preferences need not be stable. | C3, W1, W13, W24, W30 | Consensus, Econometrica / JPE / AER / MOR near-title, EC 2024 proceedings, NBER | 2026-09-02 | **eeckhout2000** + **clark2006** imply it (SPC ⇒ unique stable matching = greedy top-pair, which differs from max-weight); **echenique2024** proves stability and efficiency are different members of one OT family. The one-line counterexample is *derivable* from these in two steps but is not written down. Cite the two and derive it; do not cite anything for the counterexample itself. |
| **A6.** No mechanism-design treatment of sales-**territory design** (as opposed to compensation) in which the salesforce strategically reports the data the design consumes. | C5, W11, W21, W26, W33 | Consensus (Marketing Science, Management Science, JMR, JPSSM, Marketing Letters, QME, EJOR), Crossref near-title on Zoltners/Sinha/Skiera/Albers lineage | 2026-09-02 | **lal1986** and **rao1990** (rep privately knows territory potential — answered with a *compensation menu*, never with a change to the drawing rule); ★`waiser2021` (already held: manager misreports territory info, answered with constrained delegation); **caldieraro2009** (territory allocation endogenous, but the firm knows the potentials). **FRAME's "the niche is unoccupied" survives a second literature — but the reason must be restated:** the field chose the compensation instrument, it did not miss the incentive problem. |
| **A7.** The core of the coverage game `f(S) = Σ_z max_{i∈S} S_i(z)` is not characterised under that name. | W5, W12, W14, W23, W27 | Consensus, MOR / Math. Programming / TCS / J. Algorithms near-title, IJGT/GEB | 2026-09-02 | **deng1999** (core non-empty iff LP integral, for their IP class — the closest general test); **goemans2004** (facility-location core non-emptiness NP-complete); **chen2020coreness** (truncated submodular profit games, emptiness decidable in P). Note the *positive* half: the **Shapley value** of this exact `f` **is** in closed form via **littlechild1973** + additivity, so the "no closed form, must sample" half of the brief's Q5 is answered in the affirmative and DOMAIN §2.5/§7 should be corrected. |

### Threads known to be relevant and deliberately not searched (time-box)

- The **nucleolus of a coverage/covering game specifically** (as opposed to matching games —
  **kern2003** — and airport games). If N5 returns "core empty", this is the next query.
- **Ex-ante / randomised** fairness for the selection margin (best-of-both-worlds, ex-ante EF +
  ex-post EF1) — the natural home for a *lottery* over rosters, which is what
  ★`mariotti1998` predicts when `d ≠ 0`. Not searched.
- **Asymmetric / weighted** Nash welfare as a route to non-equal entitlements — FRAME §7 rules it
  out of scope and `RESEARCH_FINDINGS` §1E already covers it; not extended.
- The **Gonik-style truth-inducing quota** lineage, flagged as unclosed in
  `RESEARCH_FINDINGS` §4D, remains unclosed here.

---

## Query log

**Consensus (5).** C1 `Nash social welfare identical additive valuations perturbation similar
valuations fair division` · C2 `fair division allocating goods to only a subset of agents
participation selection envy-freeness` · C3 `stable matching aligned preferences common utility
maximum weight matching stability` · C4 `interpolation between identical and heterogeneous
valuations parameter fair division welfare guarantee degrade` · C5 `sales territory alignment
equity perceived fairness salesperson incentive compensation territory potential`

**WebSearch (34).** W1 `Niederle Yariv decentralized matching with aligned preferences stability`
· W2 `Eeckhout "On the uniqueness of stable marriage matchings" Economics Letters 2000` ·
W3 `Green Laffont "partially verifiable" types nested range condition mechanism design 1986` ·
W4 `Ben-Porath Dekel Lipman "optimal allocation with costly verification" American Economic
Review` · W5 `core of covering game submodular cooperative game maximum coverage nonempty core` ·
W6 `Castro Gomez Tejada polynomial calculation Shapley value based on sampling` ·
W7 `"mean logarithmic deviation" Atkinson inequality index Nash social welfare decomposition
utilitarian minus inequality` · W8 `Shorrocks "class of additively decomposable inequality
measures" Econometrica 1980` · W9 `fair division "similar valuations" OR "close valuations"
parameterized distance from identical valuations Nash welfare` · W10 `mechanism design with
evidence Ben-Porath Lipman "implementation with partial provability" hard evidence` ·
W11 `salesforce quota setting gaming sandbagging territory design incentive Marketing Science` ·
W12 `Shapley value of maximum coverage / facility location cooperative game complexity
approximation` · W13 `"common ranking property" OR "aligned preferences" unique stable matching
greedy not maximum weight matching` · W14 `Deng Ibaraki Nagamochi "Algorithmic aspects of the core
of combinatorial optimization games" covering games core` · W15 `Caragiannis Gravin Huang
"Envy-freeness up to any item with high Nash welfare: the virtue of donating items"` ·
W16 `Bertsimas Farias Trichakis "The Price of Fairness" Operations Research 2011 proportional
fairness efficiency loss` · W17 `Milgrom 1981 "Good News and Bad News: Representation Theorems and
Applications" Bell Journal unraveling verifiable disclosure` · W18 `fair division indivisible goods
individual rationality initial endowments EF1 outside options nonzero disagreement` ·
W19 `Gan Suksompong Voudouris "Envy-freeness in house allocation problems" fewer houses than
agents` · W20 `Budish 2011 "The Combinatorial Assignment Problem: Approximate Competitive
Equilibrium from Equal Incomes" Journal of Political Economy` · W21 `sales territory design
salesperson private information mechanism truthful reporting territory potential estimate` ·
W22 `Maleki Tran-Thanh Rogers Jennings "Bounding the estimation error of sampling-based Shapley
value approximation"` · W23 `"submodular" profit cooperative game "core" may be empty balancedness
covering location game Goemans Skutella` · W24 `Ferdowsian Niederle Yariv decentralized matching
aligned preferences published journal 2023` · W25 `"Nash social welfare" "restricted additive
valuations" approximation ratio` · W26 `Zoltners Sinha "sales territory alignment" fairness equity
reps resistance Management Science` · W27 `Goemans Skutella "cooperative facility location games"
core NP-complete Journal of Algorithms` · W28 `Atkinson 1970 "On the measurement of inequality"
Journal of Economic Theory equally distributed equivalent` · W29 `Foster Shneyerov "Path
independent inequality measures" Journal of Economic Theory 2000 mean logarithmic deviation` ·
W30 `Echenique Root Sandomirskiy "Stable matching as transport" EC 2024 aligned preferences optimal
transport` · W31 `Littlechild Owen "A simple expression for the Shapley value in a special case"
airport game closed form` · W32 `"Fair Division with Market Values" Barman IJCAI 2024 proceedings
DOI indivisible goods market value` · W33 `"territory" OR "district" design gaming manipulation
salesforce reported data mechanism design absence literature marketing` · W34 `Nash bargaining
solution nonzero disagreement point indivisible goods EF1 fails outside option fair division`

**Citation-graph walks (OpenAlex, one step, 2026-09-02).** Forward on **green1986**
(W2063413469, 277 citers — yielded the Lipman/Seppi and persuasion lineage, none closer than the
entries kept); forward on **deng1999** (W2113370239, 192 citers — yielded **goemans2004**,
**deng2000**, **kern2003**, **chalkiadakis2012**); forward on **gan2019** (W2966870506, 20 citers
— yielded **aignerhorev2022** and **belahcene2021**, the two entries that answer Q2's boundary
question); forward on **benporath2014** (W2150771475, 123 citers — yielded **mylovanov2017** and
**benporath2019**); backward on **deng1999** (28 references, IDs only — not expanded, references
predate 1999 and the relevant ones are already in FOUNDATIONS §3). The **echenique2024** EC record
carries an empty `referenced_works` list (conference abstract), so no walk was possible; the full
reference list is in arXiv:2402.13378 and was **not** walked — noted as a gap.

**Crossref/OpenAlex resolution calls: 30.** Two corrections caught by resolution, both worth
recording: (i) `10.1016/j.jet.2012.01.014` — a plausible guess for Ben-Porath & Lipman 2012 —
resolves to Jacquet & Tan, *Wage-vacancy contracts and coordination frictions*; the correct DOI is
`10.1016/j.jet.2012.01.017`. (ii) *Fair Division with Market Values* is **AAAI 2025**, not IJCAI
2024 as the first search suggested.

---

## Where this stopped

The brief's priority order was worked in full: Q1 → Q6, all six sections populated, shortlist and
absence ledger complete. **Stopped after the absence ledger**, per the time-box. Not done, in the
order I would resume: (a) the citation walk on the arXiv full text of **echenique2024**, which is
the one load-bearing entry whose graph could not be walked; (b) the nucleolus-of-a-coverage-game
query flagged above; (c) an ex-ante/randomised-fairness sweep for the `d ≠ 0` lottery case, which
absence A4 makes newly relevant.
