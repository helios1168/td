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

---
---

# 2026-09-03 — A1 track additions

**Date:** 2026-09-03 · **Branch:** `wt/A1` · **Framework:** 0.1 ·
**Reads:** `docs/DOMAIN_economic-theory.md` (2026-09-03) §6, questions 1–6 (every `§2.x` below is to that A1 copy); context from
`docs/APPROACHES.md` §A1, `docs/LENS_GROMOV.md` (2026-09-03), `DOMAIN_economic-theory` §2.8–§2.10
and §4, `docs/FRAME.md` §6 ·
**Queries logged:** 36 conceptual/near-title (6 Consensus, 30 WebSearch) + 46
Crossref/OpenAlex/arXiv resolution calls · **DOIs resolved:** 37/38 (Crossref, 2026-09-03; the
38th states its reason; no retraction or update-to notice returned on any record) ·
**BibTeX:** `docs/LIT_economic-theory_A1.bib` (a merge candidate; it does **not** replace
`docs/LIT_economic-theory.bib`, and `docs/RESEARCH_ADDITIONS.bib` was not touched) ·
**Deduplicated against:** `docs/LIT_economic-theory.bib` (the 46 entries above),
`docs/RESEARCH_ADDITIONS.bib`, `docs/RESEARCH_FINDINGS.md`, `docs/channel_note/references.bib`,
`~/resources/economic-theory/FOUNDATIONS.md` — no DOI and no key below appears in any of them.

**Scope.** The 2026-09-02 questions Q1–Q6 were **not** re-run, per the brief. The six questions
below are the 2026-09-03 brief's, worked in its priority order. Section numbering is
`A1-Q1 … A1-Q6` so that the existing `## 1 … ## 6` cross-references in `BRIEF.md` and
`docs/units/*.md` still resolve. Entries in **bold** are keys in `LIT_economic-theory_A1.bib`;
entries in `code` are keys already held in `LIT_economic-theory.bib`; ★`code` are keys in
`RESEARCH_ADDITIONS.bib`.

---

## 0. Headlines — what changes the plan

1. **The object of §2.8 has a name, a published pricing theorem, and a published fairness
   theorem — and the fairness theorem says exactly what §2.8 guessed.**
   **echenique2021constrained** (AER 2021) prices *constraints*, not only goods: agents pay to
   the extent their purchase moves a binding constraint, which is literally
   `π_i(z) = p_z + ν_i·M_z`. Its fairness clause is the decisive sentence: the outcome is
   **fair whenever the constraints do not single out individual agents.** A1's band is *per
   agent*, so it does single them out, and envy-freeness is lost by theorem rather than by
   conjecture. §2.8's `[claim]` rows for the prices and for envy can be **cited, not proved**;
   only the proportionality row remains open. This is the largest single change to §4 step 3 / D3.
2. **EF1 is not simply "lost" under a band, and the honest statement is quantitative.**
   **wang2026matroidnsw** proves the Max-NSW allocation under matroid constraints is a tight
   **1/2-EF1** (with PO), and **kawase2026balanced** proves that maximising Nash welfare *over
   balanced allocations* need not be EF1 **while balanced EF1+fPO allocations nonetheless exist**.
   So the correct §2.8 row is: the band does not destroy EF1 as an achievable property, it
   destroys **MNW's** EF1 guarantee, and in the known constrained case the loss is a factor of 2.
   §2.1's D1 ("which fairness notion will be reported") must be decided with this in hand or N1
   will be written up wrongly.
3. **N7's headline number has an a-priori upper bound that needs no solver.**
   **breugem2022vertical** (Management Science) gives an analytical upper bound on the utility
   lost when a decision-maker imposes *per-player outcome constraints* — the same shape as
   `EG^bal_{S₁₃}(δ)`'s band — depending only on high-level parameters. That is `bertsimas2011`'s
   role for §2.9, but for our actual constraint rather than for a fairness *objective*. Compute it
   before `U13` runs: if the bound is already inside `5e-3` nats, `LENS_GROMOV` M12's softness
   test is settled without the parametric solve and **U12** closes for free.
4. **The MRT-vs-MRS distinction §2.9 draws is a 1979 result with a named method attached, and
   there is a 2023 paper arguing the programme's exact presentational position.**
   **haimes1979tradeoffs** is the theorem that KKT multipliers *are* the trade-off rates to hand a
   decision-maker, embedded in the Surrogate Worth Trade-off method whose whole point is that the
   analyst computes the rate and the DM supplies the *worth*. **acland2023weighting** argues that
   folding equity into weights conflates two things the DM must be allowed to separate, and that
   the deliverable is a metric set, not a weighted scalar. Together they retire the "elicit an
   exchange rate" framing of ★4 in favour of §2.9's menu — with citations.
5. **`LIT` §4's named gap is half closed, and the surviving half is now stated precisely.**
   **chua2023multiunit** (SCW 2023) solves optimal allocation of **multiple identical units** with
   costly verification and no transfers; the favoured-agent logic generalises. A forward walk on
   it (11 citers, 2026-09-03) found only information-design and robustness variants — **no
   heterogeneous multi-object version**. Since A1's 13 seats are interchangeable at the point of
   *selection*, §2.10's "the 13-seat version is the named gap" should be **downgraded**: the
   multi-unit case is solved, and D5b can quote a mechanism rather than an analogy.

---

## A1-Q1. Fisher / Eisenberg–Gale with per-agent quantity constraints on a second, common measure
*(the load-bearing question — bears on §2.8, §2.9, §3 statements 1/2/6, D3, N7–N9)*

**Answer in one line.** Yes, it is a named object, twice over: an **Eisenberg–Gale market**
(Jain–Vazirani) when written as a concave program over a polytope, and a **Fisher market with
agent-specific linear constraints** / a **constrained pseudo-market** when written as an
equilibrium. The personalised price `p_z + ν_i M_z` **is** the known form. PO survives (within the
band); envy-freeness is lost by theorem when the constraint singles out individual agents; EF1
degrades by a measured factor rather than vanishing; **proportionality under a quantity band on a
second measure is the one row still without a citation** — absence **A10**.

- **echenique2021constrained** — Echenique, F., Miralles, A. & Zhang, J. (2021). *Constrained
  Pseudo-Market Equilibrium*. American Economic Review 111(11), 3699–3732.
  DOI 10.1257/aer.20201769. `[frontier]`
  *Establishes:* a pseudo-market (equal artificial budgets, no money) solution for resource
  allocation subject to general constraints — bihierarchical, knapsack, combinatorial. Constraints
  create pecuniary externalities that are **internalised via prices**: an agent pays to the extent
  their purchase affects the value of a relevant constraint at equilibrium prices. The outcome is
  constrained-efficient, and it is **fair whenever the constraints do not single out individual
  agents**.
  *Bears on:* §2.8's whole `[claim]` block and D3. The pricing rule is our `π_i(z) = p_z + ν_i·M_z`
  with `ν_i` the multiplier on rep `i`'s band row, so the personalised-price KKT reading is a
  citation rather than a `math-verify` unit. And the fairness clause settles §2.8's envy row in
  the negative *for the reason §2.8 gives*: a per-agent band singles agents out, so Varian's
  common-price envy argument is unavailable. It is also the correct home for `LENS_GROMOV` U14 —
  the band duals are the constraint prices of a real equilibrium concept, not an LP artefact.
- **jalota2023fisher** — Jalota, D., Pavone, M., Qi, Q. & Ye, Y. (2023). *Fisher markets with
  linear constraints: Equilibrium properties and efficient distributed algorithms*. Games and
  Economic Behavior 141, 223–260. DOI 10.1016/j.geb.2023.06.007. `[frontier]`
  *Establishes:* a Fisher market in which **each agent carries additional linear constraints**
  (knapsack, proportionality). Adding them "fundamentally alters the properties of the market
  equilibrium as well as the optimal allocations": the Eisenberg–Gale optimum is no longer a
  competitive equilibrium at common prices, and the repair is a **budget-perturbed** social
  optimisation problem (BP-SOP) whose capacity duals are the prices; a fixed-point scheme computes
  the perturbations and an ADMM scheme decentralises the computation.
  *Bears on:* §2.8 head-on, and it is the closest published analogue of `EG^bal_S(δ)`. Two
  consequences. (i) It confirms §2.8's failure mode (i): if no band row binds, the object collapses
  to §2.2 — that is precisely the unperturbed case, and it should be *detected* from the duals.
  (ii) It supplies the **alternative repair** to personalised prices: perturb budgets instead,
  which is `budish2011`'s device arriving from the market side. `DOMAIN_optimization` should see
  this before `U13` is specified, because BP-SOP is a different and possibly better-conditioned
  program than the band-constrained EG.
- **jain2010egmarkets** — Jain, K. & Vazirani, V. V. (2010). *Eisenberg–Gale markets: Algorithms
  and game-theoretic properties*. Games and Economic Behavior 70(1), 84–106.
  DOI 10.1016/j.geb.2008.11.011. `[foundation]`
  *Establishes:* the class of **Eisenberg–Gale markets** — markets whose equilibria are captured
  by maximising `Σ_i m_i log u_i` over a polytope of feasible utility vectors — containing linear
  Fisher markets and Kelly's rate-control framework; combinatorial strongly-polynomial algorithms
  for several members, presented as ascending-price auctions, and a classification by efficiency,
  fairness and competition monotonicity.
  *Bears on:* the naming question in the brief, answered. `EG^bal_S(δ)` is an EG market in exactly
  this sense — the band is one more row of the polytope. Cite this for "the object is not
  bespoke", and heed the paper's own warning: the desirable properties (rational equilibria,
  competition monotonicity) hold for *some* members and fail for others, so membership buys the
  vocabulary and not the guarantees.
- **he2018pseudomarket** — He, Y., Miralles, A., Pycia, M. & Yan, J. (2018). *A Pseudo-Market
  Approach to Allocation with Priorities*. American Economic Journal: Microeconomics 10(3),
  272–314. DOI 10.1257/mic.20150259. `[frontier]`
  *Establishes:* allocation of indivisible objects without transfers where agents receive token
  budgets and face **priority-specific (agent-varying) prices**; the assignments are fair in the
  priority-respecting sense and constrained Pareto-efficient, and the mechanism is asymptotically
  incentive-compatible. Hylland–Zeckhauser is the no-priorities special case.
  *Bears on:* §2.8's "what is lost: price anonymity", and §2.10. It is the precedent for a
  **defensible** market with non-anonymous prices: the personalisation is justified by a stated
  priority and the fairness notion is weakened to match. If A1 ships a map whose duals are
  personalised, this is the paper that says what may still be claimed — and it implies the
  programme must be able to name what the personalisation *encodes* (here: the sponsor's balance
  band), or the map is simply non-anonymous with no story.
- **neary1980rationing** — Neary, J. P. & Roberts, K. W. S. (1980). *The theory of household
  behaviour under rationing*. European Economic Review 13(1), 25–42.
  DOI 10.1016/0014-2921(80)90045-8. `[foundation]`
  *Establishes:* the duality treatment of quantity rationing via **virtual prices** — the price at
  which an unconstrained agent would freely choose the rationed quantity — and the Slutsky
  decomposition of rationed demand in terms of it, for finite as well as infinitesimal rations.
  *Bears on:* §2.8 and §2.9, and it is the oldest and cleanest citation for the reading. `ν_i` is a
  virtual-price adjustment: `ν_i > 0` means rep `i` is rationed from above and would buy more `M`
  at the market price; `ν_i < 0` means force-fed. The rationing literature also supplies the
  vocabulary a sponsor finds intuitive ("the band is a ration"), and it is why N8's sign test is
  informative rather than diagnostic noise.
- **kawase2026balanced** — Kawase, Y. & Mahara, R. (2026). *Fair and Efficient Balanced Allocation
  for Indivisible Goods*. Proceedings of the AAAI Conference on Artificial Intelligence 40,
  17067–17075. DOI 10.1609/aaai.v40i20.38755. `[contradicts-or-sharpens]`
  *Establishes:* under the **balancedness** constraint (any two agents' bundles differ in size by
  at most one) EF1 + fPO allocations exist and are polynomial-time computable in the
  two-valuation-type and personalised-bivalued cases; and — the load-bearing negative —
  **maximising Nash social welfare over balanced allocations does not guarantee EF1**.
  *Bears on:* §2.8's fairness table and D1/D3 directly, and it **corrects** that table as written.
  The band does not make EF1 unattainable; it makes *the MNW rule* stop delivering it. So the
  honest N1 report is three-way: the delivered (MNW-under-band) map's EF1 verdict, its FEFx
  verdict, and the statement that band-feasible EF1+fPO maps exist in nearby special cases —
  which is a much stronger position with the sponsor than "EF1 was the wrong test".
- **wang2026matroidnsw** — Wang, Y., Chen, X. & Nong, Q. (2026). *The Fairness of Maximum Nash
  Social Welfare Under Matroid Constraints and Beyond*. In Web and Internet Economics (WINE 2024),
  Lecture Notes in Computer Science, 172–189. DOI 10.1007/978-3-032-08560-3_10. `[frontier]`
  *Establishes:* under matroid constraints the Max-NSW allocation is Pareto-optimal and satisfies a
  **tight 1/2-EF1** (resolving an open question); `max{1/a², 1/2}`-EF1 for 2-valued valuations,
  `max{1/p, 1/4}` for strongly `p`-extendible systems, and 1/4 for general independence systems.
  *Bears on:* §2.8's EF1 row, §3 statement 2, and the **A2** retest. This is the first *modulus* on
  how far a constraint pushes MNW off EF1 — a factor, not a lapse. Our band is a knapsack-type
  (not matroid) constraint on a second measure, so the theorem does not transfer as-is; but it
  fixes the shape of the statement the programme should be trying to make, and gives the number to
  beat.
- **mancho2026equalsized** — Mancho, A., Markakis, E. & Protopapas, N. (2026). *Fairness under
  Equal-Sized Bundles: Impossibility Results and Approximation Guarantees*. ACM Transactions on
  Economics and Computation. DOI 10.1145/3843229. (Conference version: SAGT 2025, LNCS, 191–208.)
  `[frontier]`
  *Establishes:* fair division where every agent must receive a bundle of **fixed size**, with the
  flip-based notions EFF1/EFFX — envy tested by *swapping* items rather than removing them, since
  removal breaks feasibility; approximation guarantees, and a sharp contrast with unconstrained
  EFX in which the standard techniques fail.
  *Bears on:* §2.8's choice of fairness notion, and it is a *second* answer alongside
  `barman2023gac`'s FEFx. Under an exact-size constraint the natural repair is not "envy only
  against feasible subsets" but "envy up to a **swap**", because every feasible bundle is the same
  size. A1's band is two-sided (`(1∓δ)T/k`), so the swap formulation is arguably the closer
  analogue, and N1 should compute both.
- **biswas2018cardinality** — Biswas, A. & Barman, S. (2018). *Fair Division Under Cardinality
  Constraints*. IJCAI 2018, 91–97. DOI 10.24963/ijcai.2018/13. `[foundation]`
  *Establishes:* with goods partitioned into categories and a per-category cap per agent, EF1 and
  approximate-MMS existence and algorithms carry over from the unconstrained setting; under
  *identical* valuations EF1 survives even matroid constraints.
  *Bears on:* the base case for §2.8, and the entry point to the constrained-fair-division thread.
  Its identical-valuations result maps onto A0 (opportunity-only draw, every rep values `M` alike):
  under A0's valuations a band-feasible EF1 map exists. Under A1's heterogeneous `u_i` that does
  not follow — a clean way to state what A1 costs in fairness terms.
- **dror2023matroid** — Dror, A., Feldman, M. & Segal-Halevi, E. (2023). *On Fair Division under
  Heterogeneous Matroid Constraints*. Journal of Artificial Intelligence Research 76, 567–611.
  DOI 10.1613/jair.1.13779. `[frontier]`
  *Establishes:* EF1 algorithms when **each agent has a different feasibility constraint** —
  partition matroids with heterogeneous capacities for `n` agents with binary valuations, two
  agents with general additive valuations, three agents with identical base-orderable matroids.
  *Bears on:* the structural feature that makes A1 hard: our band is per-agent, hence
  *heterogeneous*, and this is the only paper that isolates that as the difficulty. Its results are
  for cardinality-type matroids rather than measure bands, and they stop at small `n` for general
  additive valuations — which is why absence **A8** below is stated as it is.
- **aziz2022vigilant** — Aziz, H. & Brandl, F. (2022). *The vigilant eating rule: A general
  approach for probabilistic economic design with constraints*. Games and Economic Behavior 135,
  168–187. DOI 10.1016/j.geb.2022.06.002. `[tool-we-lack]`
  *Establishes:* a general simultaneous-eating rule producing probabilistic allocations that
  satisfy efficiency and fairness properties under a broad class of distributional constraints,
  unifying probabilistic serial and its constrained variants.
  *Bears on:* the fallback if `EG^bal` is rejected as too opaque, and the natural companion to
  D7's option (ii). It is a *rule* the sponsor could be shown running rather than a program to be
  solved — `Roth 2002`'s presentability point. Fractional output, so it needs the same rounding
  treatment as `U18`.
- **garg2026approxce** — Garg, J., Tao, Y. & Végh, L. A. (2026). *Approximating competitive
  equilibrium by Nash welfare*. Games and Economic Behavior 158, 142–166.
  DOI 10.1016/j.geb.2026.03.004. `[contradicts-or-sharpens]`
  *Establishes:* Nash-welfare maximisation and competitive equilibrium coincide for **homogeneous**
  concave utilities and diverge otherwise; introduces *Gale-substitute* utilities, under which the
  Nash-welfare optimum is an approximate CE (each agent gets at least half their best CE utility,
  and is approximately envy-free); conversely every CE attains at least `(1/e)^{1/e} ≈ 0.69` of
  maximum Nash welfare, tight.
  *Bears on:* §2.8's "does the equilibrium reading survive", and obliquely §2.7's P-G3. It is the
  precise statement of *when* "the EG optimum is a market equilibrium" is a theorem rather than a
  slogan, and the answer is a homogeneity condition. Our `u_i` is linear in `x`, so the utilities
  are fine and the divergence in A1 comes from the constraint set — which is what
  **echenique2021constrained** and **jalota2023fisher** price. Cite this to keep the two sources of
  divergence apart in writing.
- **echenique2021participation** — Echenique, F., Miralles, A. & Zhang, J. (2021). *Fairness and
  efficiency for allocations with participation constraints*. Journal of Economic Theory 195,
  105274. DOI 10.1016/j.jet.2021.105274. `[frontier]`
  *Establishes:* pseudo-market existence, efficiency and fairness results for probabilistic
  allocation problems where agents carry **participation constraints** (they must be willing to
  take part, or may be left out), extending the constrained pseudo-market machinery to that case.
  *Bears on:* the **A3** retest below, and §2.6. It is the nearest published treatment of a market
  with a participation margin, and it shows what is recoverable: prices and constrained efficiency
  survive, and the fairness notion weakens to a participation-conditional one. What it does *not*
  do is fix `k` recipients out of `n` by design, or state an axiom across the boundary — so A3
  stands, narrowed.

---

## A1-Q2. The shadow price of a fairness constraint as a sponsor-facing object
*(bears on §2.9, D2, ★4, N7)*

- **haimes1979tradeoffs** — Haimes, Y. Y. & Chankong, V. (1979). *Kuhn-Tucker multipliers as
  trade-offs in multiobjective decision-making analysis*. Automatica 15(1), 59–72.
  DOI 10.1016/0005-1098(79)90087-6. `[foundation]`
  *Establishes:* the sensitivity interpretation of KKT multipliers in ε-constraint multiobjective
  programs and, with it, the theoretical basis of the **Surrogate Worth Trade-off method**: the
  analyst computes the trade-off rates from the multipliers and presents them; the decision-maker
  replies with a *surrogate worth* — how much they value that rate — and the interaction converges
  on the preferred solution.
  *Bears on:* §2.9's central distinction, which turns out to be 47 years old and to have a
  procedure attached. "Marginal rate of transformation, computed by the programme" versus
  "marginal rate of substitution, held by the sponsor" is exactly SWT's analyst/DM split, and its
  convergence argument answers "what do we do after handing over the menu". Cite this instead of
  deriving the envelope identity from scratch; §3 statement 6's `math-verify` unit shrinks to
  checking that `EG^bal` satisfies SWT's regularity, plus the kink caveat §2.9 already states.
- **breugem2022vertical** — Breugem, T. & Van Wassenhove, L. N. (2022). *The Price of Imposing
  Vertical Equity Through Asymmetric Outcome Constraints*. Management Science 68(11), 7977–7993.
  DOI 10.1287/mnsc.2021.4287. `[frontier]`
  *Establishes:* an analytical **upper bound on the total-utility loss** from imposing outcome
  constraints that guarantee each player a minimum share of total utility, for a planner
  maximising total utility over a general convex set; the bound depends only on high-level
  parameters, and the applications (health delivery, vaccine prioritisation) show when it is close
  to tight.
  *Bears on:* N7 and D2, and it is the paper `bertsimas2011` is *not*. `bertsimas2011` prices a
  fairness **objective**; this prices a per-player **constraint**, which is what `δ` is. Compute
  the bound from the programme's own high-level parameters before `U13` runs: if it is already
  below `5e-3` nats, `LENS_GROMOV` M12's softness test is answered with arithmetic and **U12**
  closes for free.
- **bertsimas2012efficiency** — Bertsimas, D., Farias, V. F. & Trichakis, N. (2012). *On the
  Efficiency-Fairness Trade-off*. Management Science 58(12), 2234–2250.
  DOI 10.1287/mnsc.1120.1549. `[foundation]`
  *Establishes:* the sequel to `bertsimas2011` — the efficiency–fairness frontier across the whole
  **α-fairness** family (α = 0 utilitarian, α = 1 proportional/Nash, α → ∞ max-min), with guidance
  on choosing α for a given allocation problem and an air-traffic-management case study.
  *Bears on:* §2.3's second knob and D2. `α` is `ε`; this is the operations-side statement that the
  criterion choice is a *design decision with a computable cost*, and its case study is the model
  for §2.9's menu. Cite alongside `atkinson1970` so the menu carries both the welfare-economics and
  the OR vocabulary — the sponsor will recognise one of them.
- **karsu2015inequity** — Karsu, Ö. & Morton, A. (2015). *Inequity averse optimization in
  operational research*. European Journal of Operational Research 245(2), 343–359.
  DOI 10.1016/j.ejor.2015.02.035. `[foundation]`
  *Establishes:* the reference classification of how equity concerns enter optimisation models,
  and — critically for us — it separates **equitability** (concern about the distribution of an
  anonymous outcome vector) from **balance** (concern that pre-defined entities receive comparable
  amounts), listing the modelling devices appropriate to each.
  *Bears on:* §2.3's "two knobs" claim, from the OR side and with names. `δ` is Karsu–Morton
  *balance* on `M`; `ε` is *equitability* on `g`. The programme has been using one word for both,
  and this is the citation that says the field distinguishes them. One paragraph in the note; the
  77.6× measurement is the evidence, this is the vocabulary.
- **acland2023weighting** — Acland, D. J. & Greenberg, D. H. (2023). *Distributional weighting and
  welfare/equity tradeoffs: a new approach*. Journal of Benefit-Cost Analysis 14(1), 68–92.
  DOI 10.1017/bca.2023.5. `[contradicts-or-sharpens]`
  *Establishes:* a separation of *utility-weights* (correcting willingness-to-pay for diminishing
  marginal utility — legitimate, part of measuring aggregate welfare) from *equity-weights*
  (encoding a moral judgement about whose welfare counts more). The argument is that equity-weights
  are **inappropriate** in the analyst's model because they conflate welfare and equity information
  and pre-empt a judgement belonging to accountable decision-makers; the recommendation is to
  report a metric set that lets the DM apply their own values.
  *Bears on:* §2.9 and ★4, and it sharpens the programme's position from "ask the sponsor for
  `(δ, ε)`" to "we should **not** be choosing `ε` at all, and the deliverable is the metric set".
  It is also the strongest available answer to [pred]'s standing charge that the programme has been
  making a distributive choice on leadership's behalf: the fix is presentational, and it is cheap.
- **pirttila2010leaky** — Pirttilä, J. & Uusitalo, R. (2010). *A 'Leaky Bucket' in the Real World:
  Estimating Inequality Aversion using Survey Data*. Economica 77(305), 60–76.
  DOI 10.1111/j.1468-0335.2008.00729.x. `[tool-we-lack]`
  *Establishes:* that Okun's leaky-bucket question recovers a usable inequality-aversion parameter
  from ordinary survey respondents, that the recovered `ε` predicts their views on related policy
  questions — and that **the estimate depends dramatically on how the question is framed**.
  *Bears on:* D2's mechanics, if the sponsor will answer at all. It is the instrument for eliciting
  `ε` (a few leaky-bucket questions, not an abstract exchange rate), and simultaneously the
  warning: two framings of the same question produce two different `ε`, so the elicitation must be
  fixed in advance and disclosed like any other part of the mechanism (`Roth 2002`).
- **cadham2023eliciting** — Cadham, C. J. & Prosser, L. A. (2023). *Eliciting Trade-Offs Between
  Equity and Efficiency: A Methodological Scoping Review*. Value in Health 26(6), 943–952.
  DOI 10.1016/j.jval.2023.02.006. `[tool-we-lack]`
  *Establishes:* a scoping review of the methods actually used to elicit equity–efficiency
  trade-offs from decision-makers and the public — benefit trade-off, leaky bucket, person
  trade-off — with the functional forms fitted (Atkinson CRRA dominating) and their reliability.
  *Bears on:* the practical half of D2. If the sponsor is to be asked anything, this is the menu of
  instruments and their known failure rates. Health-economics venue, but the object elicited is
  exactly `ε` in `atkinson1970`'s parameterisation, which is the programme's own knob.

---

## A1-Q3. Multi-object allocation with costly or partial verification and no transfers
*(bears on §2.10, D5a/D5b, ★2 — and it updates `LIT` §4's named gap)*

- **chua2023multiunit** — Chua, G. A., Hu, G. & Liu, F. (2023). *Optimal multi-unit allocation with
  costly verification*. Social Choice and Welfare 61(3), 455–488.
  DOI 10.1007/s00355-023-01463-5. `[tool-we-lack]`
  *Establishes:* the **multi-unit** extension of `benporath2014` — a principal with several
  identical objects, at most one per agent, no transfers, and the ability to check any agent's
  report at a cost. The optimum is characterised (an *n*-ascending mechanism trading efficient
  allocation against checking cost), preserving the favoured-agent logic of the single-object case.
  *Bears on:* **§2.10 and D5b, and it closes half of `LIT` §4's named gap.** A1 allocates 13 seats,
  at most one per wholesaler, with no transfers and a costly audit — that is this model with
  `k = 13` identical units, provided the seats are treated as interchangeable at the point of
  *selection* (they are: selection precedes assignment). §2.10's "the 13-seat version is not
  solved" should be rewritten — the identical-object version is solved and the heterogeneous-object
  version is the residual gap (absence **A11**).
- **li2020punishments** — Li, Y. (2020). *Mechanism design with costly verification and limited
  punishments*. Journal of Economic Theory 186, 105000. DOI 10.1016/j.jet.2020.105000.
  `[frontier]`
  *Establishes:* the allocation problem where the principal can inspect at a cost **and** punish a
  caught liar, but the punishment is bounded; the optimal mechanism has a two-threshold structure —
  agents below a lower threshold and above an upper threshold are each pooled — rather than the
  clean favoured-agent cut.
  *Bears on:* the realistic version of D5b, alongside `mylovanov2017`. Our only punishment is
  losing the seat, i.e. a bounded one, and this says the optimum then *pools* the top reporters
  rather than ranking them. That matters because §2.10's measured finding is that selection is
  nearly "rank by reported book magnitude": a bounded-punishment optimum that pools the top is a
  materially different governance story from a ranking, and it is the one to put to the sponsor.
- **erlanson2020collective** — Erlanson, A. & Kleiner, A. (2020). *Costly verification in
  collective decisions*. Theoretical Economics 15(3), 923–954. DOI 10.3982/TE3101. `[frontier]`
  *Establishes:* costly verification applied to a **collective** decision (a binary public choice)
  rather than to allocation of a private object; characterises optimal mechanisms without transfers
  when the designer may verify reports.
  *Bears on:* the shape of the question if the sponsor reframes selection as a committee decision
  rather than an allocation — which is how a channel head is likely to describe it. Included so
  §2.10's model choice is *made* rather than assumed: the allocation framing
  (**chua2023multiunit**) and the collective-decision framing are different mechanisms with
  different optima.

---

## A1-Q4. Scale invariance of Nash welfare as manipulation resistance, and where it breaks
*(bears on §2.7(c) P-G1/P-G2/P-G3, §3 statement 7, D5a, N10)*

**Answer in one line.** The invariance half of P-G1 is textbook and uncontroversial; the
*selection* half (P-G2) is **not stated anywhere I could find**, and neither is the
affine-but-not-homogeneous case of P-G3 — absence **A12**. What the literature does supply is the
adjacent and sobering result that the EG/Nash rule is manipulable in the **relative** report even
where it is invariant in scale, with quantified worst cases.

- **branzei2022strategic** — Brânzei, S., Gkatzelis, V. & Mehta, R. (2022). *Nash Social Welfare
  Approximation for Strategic Agents*. Operations Research 70(1), 402–415.
  DOI 10.1287/opre.2020.2056. `[contradicts-or-sharpens]`
  *Establishes:* the Fisher-market / proportional-fairness mechanism run on **reported** valuations
  as a game; equilibrium existence, and tight bounds on the Nash-welfare loss at equilibrium
  relative to the truthful optimum.
  *Bears on:* §2.7 and the honest scoping of P-G1. Scale invariance says a rep gains nothing by
  multiplying their whole reported book by `γ_i` **at fixed roster**; it says nothing about
  re-shaping the profile across zips, and this paper prices exactly that residual manipulation.
  §2.7's "what it cannot say" paragraph on selective per-zip inflation now has a citation and a
  bound rather than a caveat, and `U3-inv` should quote it when stating the smallest group action
  that would cover the attack.
- **cole2013mechanism** — Cole, R., Gkatzelis, V. & Goel, G. (2013). *Mechanism design for fair
  division: allocating divisible items without payments*. EC 2013, 251–268.
  DOI 10.1145/2482540.2482582. `[tool-we-lack]`
  *Establishes:* proportional fairness (= Nash = CEEI) is not truthfully implementable; the
  **Partial Allocation mechanism** restores truthfulness by deliberately discarding a fraction of
  the resource, guaranteeing each agent at least `1/e ≈ 0.368` of their proportionally-fair
  utility, and no truthful mechanism can guarantee more than 0.5.
  *Bears on:* D5a's cost side. It is the exact price of "make the draw strategy-proof rather than
  merely `G`-invariant", in the programme's own currency, and it is a **coverage** cost — which
  FRAME §4's every-zip-assigned constraint forbids, exactly as `caragiannis2019efx` does for EFX.
  The two together give the sponsor a consistent sentence: full coverage is what rules out both the
  strong fairness guarantee and the truthful mechanism.
- **psomas2022nom** — Psomas, A. & Verma, P. (2022). *Fair and Efficient Allocations Without
  Obvious Manipulations*. Advances in Neural Information Processing Systems 35 (NeurIPS 2022).
  **DOI: unresolved** — NeurIPS proceedings are not Crossref-registered; canonical record at
  `proceedings.neurips.cc/paper_files/paper/2022/hash/57250222014c35949476f3f272c322d2-Abstract-Conference.html`,
  preprint arXiv:2206.11143. `[contradicts-or-sharpens]`
  *Establishes:* under the weak incentive requirement of **non-obvious manipulability** (NOM),
  fairness and efficiency become largely compatible — but there is **no NOM mechanism that always
  outputs a Nash-welfare-maximising allocation**, already at `n = 2` agents and four items; the
  same holds for utilitarian and egalitarian welfare.
  *Bears on:* §2.7's residual claim and D5a. It is the cleanest available statement that the
  incentive problem with a Nash-welfare rule is not an artefact of demanding full
  strategy-proofness: it survives the weakest sensible relaxation. Quote it so that §2.7(a)'s
  ★`fotakis2014` scope correction does not read as "and therefore the incentive concern goes away".

---

## A1-Q5. Stability of a matching as a function of a capacity/size constraint on the objects
*(bears on §2.4's `[claim]` δ-dependence, N3, and on whether ★3 and ★4 are one decision)*

**Answer in one line.** The horizontal↔vertical transition indexed by a size band is **not** a
studied object — absence **A13**. What exists, and is worth having, is (i) a theorem that stability
generically *fails to exist* once distributional constraints bind, (ii) the capacity-manipulation
literature, which says quotas are strategically live, and (iii) a framework for the *magnitude* of
instability rather than its presence.

- **kamada2024fairconstraints** — Kamada, Y. & Kojima, F. (2024). *Fair Matching under Constraints:
  Theory and Applications*. The Review of Economic Studies 91(2), 1162–1199.
  DOI 10.1093/restud/rdad046. `[frontier]`
  *Establishes:* in a general model of matching with constraints, a stable matching **typically
  does not exist**; the paper therefore characterises feasible, individually-rational and *fair*
  matchings as fixed points of a function, identifies the class of individual-school constraints
  admitting a student-optimal fair matching, and validates the theory on daycare-allocation data.
  *Bears on:* §2.4 and D2/★3, and it is a genuine warning. §2.4's `[claim]` reasons about how the
  band changes *which* pairs block; this says that once the constraint binds, stability may not be
  the available concept at all, and the discipline substitutes fairness (no justified envy). If N3
  is to be run at two or three `δ` on the frontier (as §3 statement 4 asks), the report must be
  prepared for "no stable roster exists at this `δ`" as an answer, and must decide in advance what
  it reports instead.
- **sonmez1997capacities** — Sönmez, T. (1997). *Manipulation via Capacities in Two-Sided Matching
  Markets*. Journal of Economic Theory 77(1), 197–204. DOI 10.1006/jeth.1997.2316.
  `[contradicts-or-sharpens]`
  *Establishes:* hospitals can gain by **under-reporting capacity**, the US intern match is
  manipulable in this way, and **no solution is both stable and non-manipulable via capacities**.
  *Bears on:* §2.4 and §2.7 jointly, and it identifies an attack surface the programme has not
  considered. `δ` and `k` are capacities in this sense: if anyone in the channel can influence the
  band or the seat count, they have a manipulation that `G`-invariance does not touch, because it
  is not a valuation report at all. One sentence in §2.7's "what it cannot say", and a line in
  `U3-inv`. (Crossref renders the author as "Tayfun Sömnez", a transposition; the correct surname
  is Sönmez, and the `.bib` records the discrepancy.)
- **anshelevich2013anarchy** — Anshelevich, E., Das, S. & Naamad, Y. (2013). *Anarchy, stability,
  and utopia: creating better matchings*. Autonomous Agents and Multi-Agent Systems 26(1),
  120–140. DOI 10.1007/s10458-011-9184-3. `[tool-we-lack]`
  *Establishes:* the welfare loss from insisting on stability in matchings with cardinal utilities
  (price-of-anarchy / price-of-stability bounds under structural conditions on preferences), and
  conditions under which **approximately stable** matchings exist that are close to socially
  optimal.
  *Bears on:* N3's deliverable format. §2.4 already says "report the margin, not just the verdict";
  this is the framework that makes the margin meaningful — an α-stable matching is one in which no
  blocking pair gains more than a factor α, which is exactly the quantity `w·max Δb` that §2.4's
  band argument bounds. It converts §2.4's `[claim]` from prose into a computable statistic at
  each `δ`.
- **chade2017sorting** — Chade, H., Eeckhout, J. & Smith, L. (2017). *Sorting through Search and
  Matching Models in Economics*. Journal of Economic Literature 55(2), 493–544.
  DOI 10.1257/jel.20150777. `[foundation]`
  *Establishes:* the unified survey of sorting under non-transferable, transferable and imperfectly
  transferable utility, with the vertical (common-ranking) versus horizontal (idiosyncratic-fit)
  distinction as its organising axis, and the conditions for assortative matching in each.
  *Bears on:* §2.4's vocabulary, and it is the reference for the *terms* of the `[claim]` even
  though nobody has indexed the transition by a capacity band. It also flags an assumption §2.4
  makes implicitly: `g_ij = B_j + w·b_ij` is an *additively separable* common-plus-idiosyncratic
  value, which is a special case in this literature and not the general one. Say so when the claim
  is written.

---

## A1-Q6. Reporting non-unique optima of an allocation mechanism
*(bears on §2.10, D7, N11, `LENS_GROMOV` U17)*

- **erdil2008tiebreaking** — Erdil, A. & Ergin, H. (2008). *What's the Matter with Tie-Breaking?
  Improving Efficiency in School Choice*. American Economic Review 98(3), 669–689.
  DOI 10.1257/aer.98.3.669. `[foundation]`
  *Establishes:* breaking ties exogenously before running deferred acceptance preserves stability
  but imposes **artificial constraints** that cost welfare; a polynomial "stable improvement cycle"
  algorithm recovers a student-optimal stable matching under weak priorities.
  *Bears on:* D7, and it is the discipline's canonical statement that **a tie-break is a policy
  choice with a measurable price**, not an implementation detail. Our situation has the same shape:
  the Hungarian solver's arbitrary tie-break is choosing among rosters within `8.1e-3` nats. The
  paper's remedy — search the tie class for a better member rather than accept the arbitrary one —
  *is* N11's near-optimal roster enumeration, which now has a precedent rather than a rationale.
- **abdulkadiroglu2009spvseff** — Abdulkadiroğlu, A., Pathak, P. A. & Roth, A. E. (2009).
  *Strategy-proofness versus Efficiency in Matching with Indifferences: Redesigning the NYC High
  School Match*. American Economic Review 99(5), 1954–1978. DOI 10.1257/aer.99.5.1954.
  `[foundation]`
  *Establishes:* in the actual NYC redesign, theory plus field-data simulation favoured **single**
  tie-breaking (one lottery used at every school) over independent tie-breaking, and any
  inefficiency of a realised tie-break cannot be removed without damaging participants' incentives.
  *Bears on:* D7 directly, and it answers the brief's question — "is there guidance on whether to
  disclose a tie-break?" — with a worked precedent in a low-reversibility market over people's
  placements. Two transferable points: the tie-break rule was chosen deliberately, ex ante, and
  published; and the efficiency lost to it was accepted as the price of incentives. Both support
  §2.10's recommendation (i).
- **ashlagi2020tiebreaking** — Ashlagi, I. & Nikzad, A. (2020). *What matters in school choice
  tie-breaking? How competition guides design*. Journal of Economic Theory 190, 105120.
  DOI 10.1016/j.jet.2020.105120. `[frontier]`
  *Establishes:* the comparison between common and independent tie-breaking is decided by the
  **balance of supply and demand**: with a surplus of seats a common lottery is less equitable and
  there are efficiency trade-offs; with a shortage of seats a common lottery dominates in the
  stochastic order of the rank distribution.
  *Bears on:* D7's specifics. A1 is unambiguously the shortage case — 13 seats, 111 claimants — so
  the literature's recommendation is the *common* (single, global) tie-break, disclosed. That is a
  concrete, defensible answer to D7 rather than a preference, and adopting it costs nothing.
- **aziz2024bestofboth** — Aziz, H., Freeman, R., Shah, N. & Vaish, R. (2024). *Best of Both
  Worlds: Ex Ante and Ex Post Fairness in Resource Allocation*. Operations Research 72(4),
  1674–1688. DOI 10.1287/opre.2022.2432. `[frontier]`
  *Establishes:* a randomised allocation that is **ex-ante envy-free and ex-post EF1**
  simultaneously, computable efficiently; an impossibility once economic efficiency is also
  demanded, and a positive result when the ex-post guarantee is slightly relaxed.
  *Bears on:* the thread `LIT`'s 2026-09-02 time-box left unsearched, now searched, and D7's option
  (ii). If the programme ever chooses a lottery over near-optimal rosters, this is what it buys and
  what it costs — and the impossibility with efficiency is why a lottery cannot be sold as free.
  Read with §2.10's recommendation against a lottery on FRAME §2 and `smith2000` grounds: this says
  the *technical* case for randomising is real, which makes D7 a genuine trade-off rather than an
  obvious call.
- **broome1984selecting** — Broome, J. (1984). *Selecting People Randomly*. Ethics 95(1), 38–55.
  DOI 10.1086/292596. `[foundation]`
  *Establishes:* the philosophical account of fairness as the proportional satisfaction of
  **claims**, on which a lottery gives each claimant "surrogate satisfaction"; and the argument
  that if equal claims require equal chances, then near-equal claims cannot plausibly require zero
  chance for the slightly weaker claimant.
  *Bears on:* §2.6 and D7, and it is the missing normative half of the claims framing §2.6 already
  runs. Our measurement is exactly Broome's premise: the strongest collective claim of the
  unselected is `0.92%` of book / `0.043` nats — near-equal claims. Broome is therefore the
  strongest case *against* the programme's recommendation, and the write-up must answer him rather
  than ignore him. Cite as the counter-argument, with `smith2000` and FRAME §2's low-reversibility
  row as the rebuttal.
- **schmidt2023favoritism** — Schmidt, R. J. & Trautmann, S. T. (2023). *Implementing (Un)fair
  Procedures: Containing Favoritism When Unequal Outcomes are Inevitable*. The Journal of Law,
  Economics, and Organization 39(1), 199–234. DOI 10.1093/jleo/ewab019.
  `[contradicts-or-sharpens]`
  *Establishes:* experimentally, that allocators selecting one person from several candidates
  favour those similar to themselves, and that four interventions differ sharply in containing it —
  **transparency of the process**, a private randomisation device, **delegation to a public
  randomisation device**, and allowing the allocator to avoid information about recipients; beliefs
  and fairness judgements explain which work.
  *Bears on:* §2.10's stated failure mode — `benporath2014`'s favoured-agent mechanism has an
  optics problem in a sales organisation — and it turns that worry into evidence. The
  favoured-agent structure is precisely the arrangement this literature associates with
  favouritism, and the finding that public delegation and transparency work while *private*
  randomisation does not is directly actionable for D5b and D7.
- **feliciani2024lotteries** — Feliciani, T., Luo, J. & Shankar, K. (2024). *Funding lotteries for
  research grant allocation: An extended taxonomy and evaluation of their fairness*. Research
  Evaluation 33, article rvae025. DOI 10.1093/reseval/rvae025. `[frontier]`
  *Establishes:* a taxonomy of partially-random selection procedures by how much work randomness
  does — from none (ordinary review) through **tie-breaking lotteries** to extensive lotteries —
  and a simulation evaluation of each against three fairness desiderata (merit, unbiasedness,
  distributive spread). Low-randomness types, tie-breaking lotteries specifically, behave
  essentially like ordinary review.
  *Bears on:* D7, with an unusually close analogy: a small number of positions, many near-equal
  claimants, a noisy merit score, reputational stakes. The finding that a *tie-breaking* lottery
  does not meaningfully change the fairness profile is the argument that D7's two options are less
  far apart than they look — which lowers the stakes of the decision, and is worth saying to the
  sponsor before they agonise over it.

---

## Shortlist — five papers that would most change §4 if read this week

1. **echenique2021constrained** (Constrained Pseudo-Market Equilibrium, AER 2021) — because it
   names A1's object, derives our personalised price `p_z + ν_i M_z` as constraint pricing, and its
   fairness clause ("fair whenever the constraints do not single out individual agents") decides
   §2.8's envy row by theorem. Converts two `[claim]`s and one `math-verify` unit into citations.
2. **jalota2023fisher** (Fisher markets with linear constraints, GEB 2023) — because it is the same
   object from the algorithmic side, states that per-agent constraints *fundamentally alter* the
   equilibrium, and offers budget perturbation as an alternative repair to personalised prices.
   `DOMAIN_optimization` needs it before `U13` is specified.
3. **kawase2026balanced** (Fair and efficient balanced allocation, AAAI 2026) — because it proves
   that MNW-over-a-balance-band need not be EF1 *while band-feasible EF1+fPO allocations exist*.
   That rewrites §2.8's fairness table, decides D1's "which notion do we report", and turns N1 from
   an indictment into a three-way comparison.
4. **breugem2022vertical** (The price of vertical equity through outcome constraints, MS 2022) —
   because it bounds N7's headline number from high-level parameters alone, before any parametric
   solve, and could settle `LENS_GROMOV` M12's softness test with arithmetic.
5. **chua2023multiunit** (Optimal multi-unit allocation with costly verification, SCW 2023) —
   because it closes the half of `LIT` §4's named gap that matters: 13 near-identical seats, no
   transfers, costly audit. §2.10's "the 13-seat problem is not solved" is now wrong as written, and
   D5b can quote a mechanism.

Runners-up, and the pair to read if only the presentation matters: **haimes1979tradeoffs** (the
multiplier *is* the trade-off rate to show a decision-maker — with a 1979 procedure attached) and
**acland2023weighting** (do not encode the equity judgement in the model; report metrics).

---

## Absence ledger — 2026-09-03

Every row was searched on **2026-09-03**. "Consensus" = the Consensus academic index (Semantic
Scholar / PubMed / Scopus / arXiv); venue coverage for these fields includes EC, AAMAS, IJCAI,
AAAI, SAGT, WINE, GEB, JET, AER, Econometrica, ReStud, SCW, MOR, TEAC, Management Science, EJOR,
Operations Research and JEL. Query IDs refer to the query log below. **A2 and A3 are the
2026-09-02 rows re-tested against question 1, as the brief instructs; their verdicts are updated,
not replaced.**

| claim | queries | venues / indexes searched | date | nearest miss |
|---|---|---|---|---|
| **A8 (new).** No published model of Eisenberg–Gale / CEEI with a per-agent **quantity band on a second, common measure** distinct from every agent's valuation — i.e. `L ≤ Σ_z M_z x_{zi} ≤ U` with `u_i(z) = M_z w_i(z)`. The *pieces* are all published; the combination is not. | C6, C7, W35, W36, W58, W62 | Consensus (market equilibrium + fair division), Crossref bibliographic, GEB / AER / AEJ:Micro / JET near-title, EC–WINE–SAGT–AAAI–IJCAI via Crossref, forward walks on **jalota2023fisher** (11 citers) and **echenique2021constrained** (13 citers) | 2026-09-03 | **jalota2023fisher** — per-agent linear constraints, but on the agent's own consumption in goods units, and the fairness analysis is about budget perturbation rather than a second measure. **echenique2021constrained** — fully general constraints and the right pricing, but no two-measure structure and no Nash/EG value statement. `barman2025market` (held) — two measures, no band. **dror2023matroid** — heterogeneous per-agent constraints, but cardinality/matroid, and small `n` for general additive valuations. **Verdict: the combination is genuinely unoccupied; the pricing question it raises is nevertheless answered (A9), so this is a modelling gap, not an obstacle.** |
| **A9 (new — resolves in the affirmative; recorded so it is not searched a third time).** The personalised-price form `π_i(z) = p_z + ν_i M_z` **is** the known form. | C6, W35, W36, W37 | as A8, plus the general-equilibrium rationing literature via Crossref (EER, ReStud) | 2026-09-03 | Not an absence. **echenique2021constrained** (constraint pricing: agents pay for the constraints they move), **neary1980rationing** (virtual prices under quantity rationing), **he2018pseudomarket** (priority-specific prices in a pseudo-market). §2.8's KKT reading should be cited to these three and not proved. |
| **A10 (new).** No published counterexample or theorem about **proportionality** (`u_i(A_i) ≥ u_i(Z)/k`) failing under a per-agent *quantity band on a second measure*. The constrained-fair-division literature works in EF1/EFX/MMS, not in proportionality. | C8, W47, W57, W62 | Consensus, EC/WINE/SAGT/AAAI/IJCAI via Crossref, ACM TEAC / JAIR / AIJ near-title, `suksompong2021constraints` survey read for pointers | 2026-09-03 | **mancho2026equalsized** (EFX-analogue impossibilities under exactly-equal bundle sizes); **wang2026matroidnsw** (EF1 → tight 1/2-EF1 under matroid constraints); **kawase2026balanced** (MNW over balanced allocations is not EF1); the MMS-under-cardinality-constraints line (Biswas–Barman and successors) — MMS is a *relaxation* of proportionality, so these bound it only indirectly. **§2.8's two-agent proportionality counterexample remains this programme's own to write; N9 is the right way to settle it empirically.** |
| **A11 (new).** No **heterogeneous** multi-object costly-verification mechanism with `n ≫ k` and no transfers. | W39, W43, W44, forward walk on **chua2023multiunit** | Consensus, AER / Econometrica / JET / TE / SCW / GEB near-title, OpenAlex forward walk (11 citers of `10.1007/s00355-023-01463-5`, all information-design, distributional-robustness or inspection-accuracy variants) | 2026-09-03 | **chua2023multiunit** closes the **identical-units** case — this is the update to `LIT` §4. **li2020punishments** and `mylovanov2017` (held) handle bounded penalties for one object; `caragiannis2012` (held) is the sampled-verification variant. **The gap is now narrow and precisely stated: `k` heterogeneous objects, one per agent.** For A1 it is probably not binding, because selection precedes assignment and the seats are interchangeable at that point. |
| **A12 (new).** The split P-G1/P-G2 — *the Nash/EG allocation and prices are invariant to per-agent utility rescaling, but which agents are selected under `max_S EG_S` is not* — is not stated anywhere found. Nor is any treatment of an objective **affine but not homogeneous** in the reported type (our `c2·T_z` coupling, P-G3). | W45, W60, W64 | Consensus, arXiv cs.GT, GEB / JET / OR near-title, EC–NeurIPS–AAAI records, Crossref bibliographic on "scale invariance" combined with "participation" / "selection" | 2026-09-03 | Scale invariance itself is `Nash 1950` and is treated as *definitional* throughout (the hedonic-games and NSW-approximation literatures state it in passing). **branzei2022strategic** prices the residual manipulation in the *relative* report at a fixed agent set; **psomas2022nom** rules out even non-obvious manipulability for an MNW rule; `crawford1979` (FOUNDATIONS) is the classical distortion result. None conditions on *who participates*. **P-G1/P-G2/P-G3 stay `math-verify` units; P-G2 in particular is a small original observation and should be written as one.** |
| **A13 (new).** The **horizontal↔vertical transition indexed by a capacity/size band** — §2.4's `[claim]` that tightening `δ` makes the induced roster market fit-driven and loosening it makes it size-driven — is not a studied object, and nothing quantifies a blocking pair's gain as a function of the common component `B_j`. | C9, W41, W50, W54, W55, W61 | Consensus, Econometrica / JPE / AER / ReStud / JET / MOR / GEB near-title, the AAMAS/IJCAI capacity-modification thread, JEL survey read for pointers | 2026-09-03 | **kamada2024fairconstraints** — under binding constraints a stable matching typically does not exist at all, which is a *stronger and different* statement than §2.4's; **sonmez1997capacities** — capacities are themselves manipulable, so `δ` and `k` are attack surfaces; **anshelevich2013anarchy** — the α-stability framework that would let the magnitude be *computed*, though it does not index it by a band; **chade2017sorting** — the vertical/horizontal vocabulary, with no capacity index. `echenique2024` (held) remains the closest one-parameter family, but its parameter is inequality aversion, not size. **§2.4's claim is unsupported and computable: run N3 at three `δ` and report α-stability, not a verdict.** |
| **A2 (re-tested against question 1).** No modulus continuous in a heterogeneity parameter for MNW/EF1 guarantees. **Still open — but the *shape* of the wanted statement now exists for a different parameter.** | C8, W47, W57, W62, plus the WINE/SAGT/TEAC constrained-fair-division sweep | as A10 | 2026-09-03 | **wang2026matroidnsw** is the first *tight multiplicative modulus* on how far a **constraint** pushes Max-NSW off EF1 (1/2, tight, for matroids; 1/4 for independence systems). That is the template A2 wants, with the constraint structure in place of the valuation-heterogeneity parameter `τ`. **mancho2026equalsized** gives approximation guarantees indexed by bundle size. `nguyen2023types` / `bhaskar2023equity` (held) remain the discrete-type versions. **Verdict: A2 stands as a gap in `τ`, and the band-constrained reformulation supplies a second and arguably more useful parameter to state a modulus in — `δ`. That is a better research question than the original.** |
| **A3 (re-tested against question 1).** No MNW treatment where only `k` of `n` agents receive bundles by design, with a fairness axiom across the selection boundary. **Still open — narrowed on the market side.** | C6, W35, W63, forward walk on **echenique2021constrained** | Consensus, AER / JET / GEB near-title, EC/AAMAS/IJCAI/AAAI via Crossref, OpenAlex forward walk | 2026-09-03 | **echenique2021participation** is the nearest new miss and a real advance: a pseudo-market with **participation constraints** retaining prices, constrained efficiency and a participation-conditional fairness notion. But participation there is the agent's own (individual rationality / opt-out), not the designer fixing `k` recipients, and there is no Nash-welfare statement or boundary axiom. `aignerhorev2022` (held) still owns the axiom, ordinally and for matchings; `gan2019` (held) still owns `m < n` house allocation with unit demand. **Verdict: A3 stands. The bundle-valued, Nash-welfare, designer-fixed-`k` version with a boundary axiom does not exist — and `MODEL_U2-stab` P4.2/P4.3's negative result explains why nobody would look for the strong version.** |

### Threads known to be relevant and deliberately not searched (time-box)

- The **nucleolus of a coverage/covering game** specifically — carried over unclosed from
  2026-09-02, and still the next query if N5 returns "core empty".
- The **Gonik-style truth-inducing quota** lineage — carried over unclosed.
- **Distributionally robust** costly verification (surfaced in the A11 forward walk,
  `10.1287/opre.2022.0662`) — relevant only if the sponsor's prior over books is contested, which
  is **A4**'s question and belongs to econometrics.
- **Discrete convex analysis** for matching under constraints (the Kojima–Tamura–Yokoo lineage,
  surfaced under C9) — the algorithmic route to A1-Q5, and it belongs to `DOMAIN_optimization` if
  the δ-dependent stability audit is ever built rather than enumerated.
- The **arXiv full text of `echenique2024`**, whose citation graph could not be walked on
  2026-09-02, remains unwalked.

---

## Query log — 2026-09-03

Numbering continues from the 2026-09-02 log (C1–C5, W1–W34).

**Consensus (6).** C6 `Fisher market equilibrium with per-agent quantity constraints personalized
prices` · C7 `Eisenberg-Gale convex program with side constraints market equilibrium fairness` ·
C8 `fair division indivisible goods cardinality constraints envy-freeness proportionality` ·
C9 `capacity or quota size constraints change the set of stable matchings from fit-driven to
size-driven preferences` · C10 `disclosing tie-breaking rule versus lottery when allocation
mechanism has multiple optimal solutions procedural fairness` · C11 `shadow price of an equity
constraint reported to decision maker constrained welfare maximisation multiplier interpretation`

**WebSearch (30).** W35 `Echenique Miralles Zhang "Constrained Pseudo-market Equilibrium" American
Economic Review 2021` · W36 `He Miralles Pycia Yan "A Pseudo-Market Approach to Allocation with
Priorities" personalized prices` · W37 `Neary Roberts "theory of household behaviour under
rationing" virtual prices European Economic Review 1980` · W38 `Haimes Chankong "Kuhn-Tucker
multipliers as trade-offs in multiobjective decision-making analysis" Automatica 1979` ·
W39 `multi-object allocation costly verification no transfers mechanism design "multiple objects"
favored agent extension` · W40 `Erdil Ergin "What's the matter with tie-breaking? Improving
efficiency in school choice" AER 2008` · W41 `Sönmez "Manipulation via capacities in two-sided
matching markets" Journal of Economic Theory 1997` · W42 `Freeman Shah Vaish "Best of Both Worlds:
Ex-Ante and Ex-Post Fairness in Resource Allocation" EC 2020` · W43 `"Optimal multi-unit allocation
with costly verification" Social Choice and Welfare 2023 authors` · W44 `Yunan Li "Mechanism design
with costly verification and limited punishments" Journal of Economic Theory 2020 multiple
objects` · W45 `Nash social welfare scale invariance manipulation misreporting utility scaling
strategyproofness "Nash bargaining" distortion of preferences` · W46 `Kawase "Fair and Efficient
Balanced Allocation for Indivisible Goods" balanced constraint EF1 fPO DOI` · W47 `Suksompong
"Constraints in fair division" survey SIGecom Exchanges 2021` · W48 `Dror Feldman Segal-Halevi "On
Fair Division under Heterogeneous Matroid Constraints" JAIR` · W49 `Broome "Selecting people
randomly" Ethics 1984 lottery fairness` · W50 `Anshelevich Das Naamad "Anarchy, stability, and
utopia: creating better matchings" approximate stability blocking pair gain` · W51 `Karsu Morton
"Inequity averse optimization in operational research" European Journal of Operational Research
2015` · W52 `Bertsimas Farias Trichakis "On the efficiency-fairness trade-off" Management Science
2012 alpha-fairness price` · W53 `Cole Gkatzelis Goel "Mechanism design for fair division"
allocating divisible items without payments EC 2013 truthful Nash welfare` · W54 `stable matching
comparative statics capacity quota change welfare "rural hospital theorem" effect of capacities on
stable matchings` · W55 `Chade Eeckhout Smith "Sorting through search and matching models in
economics" Journal of Economic Literature 2017 vertical horizontal heterogeneity` ·
W56 `Abdulkadiroglu Pathak Roth "Strategy-proofness versus efficiency in matching with
indifferences: redesigning the NYC high school match" AER 2009` · W57 `"maximin share" OR
proportionality fails under cardinality constraints counterexample fair division quota lower bound
guarantee` · W58 `Jalota Ye "Fisher markets with linear constraints" Games and Economic Behavior
2023 budget perturbed social optimization DOI` · W59 `eliciting inequality aversion parameter
decision maker "leaky bucket" social planner equity efficiency trade-off elicitation experiment` ·
W60 `"Nash social welfare" mechanism agent participation selection manipulate by scaling reported
valuations which agents are served` · W61 `matching market "common value" component versus
idiosyncratic fit blocking pairs magnitude size of firms vertical differentiation stability` ·
W62 `"price of" cardinality OR balancedness constraints Nash social welfare loss bound as function
of constraint tightness fair division` · W63 `fair division "only k agents" receive bundles
selection of recipients Nash welfare envy across selected and unselected boundary` ·
W64 `"Fair and Efficient Allocations Without Obvious Manipulations" Psomas Verma NeurIPS 2022 Nash
social welfare not obviously manipulable`

**Citation-graph walks (OpenAlex, one step, 2026-09-03).** Forward on **jalota2023fisher**
(W4382395702, 11 citers — yielded **garg2026approxce** and the constrained-PLC-utility /
matching-market thread; the remainder are 5G network-slicing applications and online-learning
variants, none closer). Forward on **echenique2021constrained** (W2973080784, 13 citers — yielded
**echenique2021participation**, **aziz2022vigilant**, the Hylland–Zeckhauser complexity thread, and
Lin–Nguyen–Nguyen–Altinkemer's *Allocation with Weak Priorities and General Constraints*, EC 2021,
`10.1145/3465456.3467581`, a two-page abstract not retained). Forward on **chua2023multiunit**
(W4372294827, 11 citers — **all** information-design, distributionally-robust or inspection-accuracy
variants; **this is the walk that establishes absence A11**). Backward on **jalota2023fisher**
(56 references, ids only, not expanded — the relevant ancestors are `budish2011`,
**jain2010egmarkets** and the Eisenberg–Gale line, all already held or added here).

**Crossref / OpenAlex / arXiv resolution calls: 46.** Three corrections caught by resolution, all
worth recording: (i) the plausible guess `10.1016/j.geb.2023.06.004` for Jalota et al. is wrong —
the DOI is `10.1016/j.geb.2023.06.007`; (ii) Crossref renders the author of *Manipulation via
Capacities in Two-Sided Matching Markets* as **"Tayfun Sömnez"**, a transposition, the correct
surname being Sönmez — the `.bib` records the discrepancy; (iii) *Best of Both Worlds* has an EC
2020 record that is a two-page abstract (`10.1145/3391403.3399537`, Freeman–Shah–Vaish) and a full
Operations Research 2024 article with a **fourth author** (Aziz) — cite the journal version.

---

## Where this stopped (2026-09-03)

The brief's priority order was worked in full and Q1 first and deepest: A1-Q1 carries 14 entries
and both citation-graph walks, A1-Q2 seven, A1-Q3 three, A1-Q4 three, A1-Q5 four, A1-Q6 seven; the
shortlist and the absence ledger are complete, and **A2 and A3 were re-tested against question 1 as
instructed**. Stopped after the absence ledger, per the time-box. Not done, in the order I would
resume: (a) the **A10** proportionality question pushed one level further into the
MMS-under-cardinality-constraints lineage, which bounds proportionality indirectly and which I read
only through abstracts; (b) the discrete-convex-analysis route to A1-Q5 (Kojima–Tamura–Yokoo),
which is an optimization hand-off and was left there; (c) a *backward* walk on
**echenique2021constrained**, which was not run — only its forward walk was; (d) the 2026-09-02
carry-overs, unchanged: the nucleolus of a coverage game, the Gonik quota lineage, and the arXiv
full text of `echenique2024`.
