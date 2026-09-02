# economic-theory plan — the national channel territory problem

**Date:** 2026-09-02 · **Framework:** 0.1-dev · **Reads:** `docs/FRAME.md`,
`docs/LENS_GROTHENDIECK.md`, `docs/LENS_GROMOV.md`,
`~/resources/economic-theory/FOUNDATIONS.md` (seeded 2026-09-02, 95 entries) ·
**Supersedes:** none

Citations in **bold** are keys in `FOUNDATIONS.md` and are the only citations permitted here.
Anything marked `[claim]` is this plan's assertion, not a cited result.

---

## 1. What the lenses handed over, in this domain's terms

| lens construct | becomes | or: no counterpart, because |
|---|---|---|
| **Coverage / composite value `V(π,σ)`** (GROTH §3) | The outcome of a fair-division problem with additive valuations: `V` *is* Nash social welfare at a zero disagreement point, over the selected agents. **Caragiannis et al. 2019**, **Eisenberg & Gale 1959** | |
| **The `τ`-deformation** (GROTH §2) | The path from *identical* additive valuations (`τ=0`) to *heterogeneous* additive valuations (`τ≈0.42`). Under identical valuations utilitarian, egalitarian and Nash criteria all coincide and every fairness axiom is vacuous; heterogeneity is what makes a criterion bite at all (**Thomson 2011**, **Moulin 2019**). The endpoints are named objects; | the homotopy itself has no counterpart — economic theory does not deform valuation profiles continuously. It is an optimization/geometry object. |
| **Equal-budget market (EG)** (GROTH §2 step 2) | Competitive equilibrium from equal incomes. Goods = zips endowed with `M`, agents = the selected wholesalers, budgets ≡ 1, additive valuations `u_i`. **Eisenberg & Gale 1959** is the program; **Hylland & Zeckhauser 1979** is the origin of the equal-artificial-budget device for indivisible positions without money; **Varian 1974** supplies the envy criterion the equilibrium satisfies. The duals `p_z` are competitive prices. | |
| **Relativisation over the roster `{EG_S}`** (GROTH §4) | Two readings, and they answer different questions. (i) *Matching*: a many-to-one two-sided market with quota `k` and a participation margin — **Gale & Shapley 1962**, **Roth & Sotomayor 1990**. (ii) *Coalitional*: `S ↦ max EG_S` is a characteristic function on wholesaler coalitions, so the base is a cooperative game — **Gillies 1959** (core), **Shapley 1967** (balancedness test). | |
| **Displacement metric** (GROTH §5a) | | No counterpart. Economic theory *ranks* allocations and forms welfare **ratios** (the "price of X" family, e.g. **Bei et al. 2022**); it does not metrise the space of allocations. Displacement is a transport/optimization object and must be handed back. |
| **Inflation group `G = (ℝ_{>0})^R`, invariants** (GROTH §5b) | The message space of a direct mechanism, and `G`-invariance is strategy-proofness against uniform misreport. **Crawford & Varian 1979** is the on-point precedent (a Nash-product criterion *is* manipulable by preference distortion); **Hurwicz 1972** is what such restriction costs; **Gibbard 1973** / **Satterthwaite 1975** bound what any unrestricted rule could achieve; **Myerson 1979** licenses studying only truthful direct rules. | |
| **The two supports** (`M` on all ZCTAs, `S` on 1,229) (GROTH §5b) | | No counterpart. A support/geometry fact. |
| **Fibration `Σ log g = n log ḡ − D(g)`** (GROM 3) | The classical efficiency–equity decomposition: base = **utilitarian** total surplus `Σ_i g_i`, fiber = **egalitarian** equalisation of `g` on a level set of that surplus, and MNW is the interpolant between them. **Kalai 1977** (egalitarian/proportional solutions, and the explicit interpersonal comparison they require), **Thomson 1994**, **Moulin 2019**. `D(g)` is a generalised-entropy inequality index. |  |
| **The premium `P`** (GROM 3–4) | The utilitarian objective, i.e. the total surplus of the (map, roster) pair. Nothing in the programme has optimised it. **Shapley & Shubik 1969** is the reading under which surplus-derived allocations tend to be core-stable, and the check that fails when the technology is indivisible. | |
| **The roster bound `P₁₃`** (GROM 4) | The characteristic function `f(S) = Σ_z max_{i∈S} S_i(z)` of a **coverage game** among the 111. It is monotone *submodular*, hence the game is concave, **not** convex — so **Shapley 1971**'s automatic core non-emptiness does **not** apply and the core may be empty. **Shapley 1967** is the computable test. **Shapley 1953** / **Young 1985** give the per-wholesaler attribution. | |
| **The 98 unselected** (GROM 4; FRAME A2) | Claimants on an estate too small for the claims: 111 wholesalers, 13 seats. **Aumann & Maschler 1985** is the canonical model; **Schmeidler 1969** (nucleolus) is the "minimise the loudest complaint" rule that matches FRAME §3's "do not starve anybody" better than a product criterion does. | |
| **Audited vs reported book** (GROM 13.1) | Restriction of the mechanism's message space to verifiable statistics. **Hurwicz 1972**'s impossibility is stated for *unrestricted* self-reporting environments and does not bind on inputs that are not reports `[claim]`. | |
| **Word purges: "certified", "nats", "map"** (GROM 13) | | No counterpart. Presentation, not theory. |
| **Tier-2 noise floor `5e-3` nats** (FRAME §10.4; GROM U6) | | No counterpart. A statistics/measurement question — §7. |

**The single most consequential re-reading.** FRAME §3's acceptance test and §2's "affected"
row describe a problem economic theory already owns: an **allocation with a participation
margin**. The programme has treated selection as a byproduct of a max-weight assignment. In
this domain it is the primary object, it has its own fairness and stability theory, and — via
FRAME assumption **A2** — it is what determines whether the disagreement point is zero at all.

---

## 2. Candidate methods

### 2.1 Restate the delivered artifact as a Nash-welfare allocation and audit EF1 / Pareto optimality

- **Rests on:** **Caragiannis et al. 2019** (MNW over indivisible goods is Pareto-efficient and
  envy-free up to one good), with **Eisenberg & Gale 1959** for the convex-program pedigree and
  **Varian 1974** for the envy criterion EF1 relaxes.
- **Assumptions, against FRAME §5/§6.** Additive valuations: **met** — `u_i(z)` is a per-zip sum
  (`docs/MODEL.md`). Goods, not chores: **met** — all `u_i(z) ≥ 0` under the headroom condition.
  All goods allocated: **met** — FRAME §4 hard constraint, 1,229 of 1,229. Each agent receives
  one bundle: **met**. **Zero baseline: NOT established.** FOUNDATIONS is explicit that
  subtracting a constant from each utility voids the guarantee, and FRAME **A2** (the 98 keep
  covering the residual channel — *unconfirmed for two days*) says every selected wholesaler
  gave up an outside option. If A2 holds, `d ≠ 0` and the EF1 theorem does not apply as cited.
- **Produces.** (a) A statement of whether the *delivered* coverage is EF1 among the 13, checked
  directly: `13 × 13` comparisons of `u_i(A_j)` against `u_i(A_{σ(i)})`, minus the single largest
  zip. This is FRAME §3.4's "per-wholesaler continuity report" in a form that carries a theorem
  rather than a table. (b) The observation that the delivered draw maximises `W`, not `V`, so it
  **inherits no EF1 or PO guarantee at all** `[claim]` — the guarantee attaches to the MNW
  optimum of `V`, which has never been computed.
- **Cannot say.** Anything about the 98. Envy across the selection boundary is total and EF1 is
  meaningless there; that is method 2.6's problem, not this one.
- **Failure mode.** Two, both live. (i) The geometric penalty `ρ·C(π)`: at `ρ > 0` the objective
  is no longer Nash welfare and the Caragiannis characterisation lapses silently. Any EF1 claim
  must state `ρ = 0` or be withdrawn. (ii) If A2 makes `d > 0`, the correct citations become
  **Mariotti 1998** and **Xu & Yoshihara 2005** (nonconvex feasible set with a nonzero baseline),
  which deliver a *lottery* or a weaker characterisation rather than a point — and the
  programme's determinism claim needs restating.

### 2.2 The Eisenberg–Gale / CEEI relaxation, with the duals as the premium bound

- **Rests on:** **Eisenberg & Gale 1959** (+ **Hylland & Zeckhauser 1979** for equal budgets
  without money; **Nash 1950** for the axioms that hold on the relaxed convex set).
- **Assumptions.** Concavity of the relaxed program: **met** — `Σ log` of a linear map. Convex
  feasible set: **met only after fractional relaxation**; the integral problem is nonconvex, which
  is precisely **Nash 1950**'s stated convexity gap and the reason **Mariotti 1998** exists. Equal
  budgets ⇔ equal entitlement: **met by business intent** (FRAME §4 soft, §7 explicitly rules
  out non-equal entitlements). Divisible goods: **not met**; the descent back to integral costs at
  most `k−1 = 12` split zips (a standard LP-basis fact, handed to optimization in §7).
- **Produces.** One number that replaces four certificates: the EG optimum is an upper bound on
  every integral coverage with the same staff set `[claim, GROTH §4]`, so `V(delivered) ≤ EG_S`
  is a genuine optimality gap **on the objective the business signs**, not on the anonymous
  surrogate. It also produces prices `p_z`, which is what makes FRAME §3.5's acceptance test
  expressible without a logarithm.
- **Cannot say.** Anything about selection — `EG_S` is conditional on `S`. And it cannot certify
  the *integral* optimum, only bound it.
- **Failure mode.** The bound is loose by exactly the integrality gap, which is bounded in *count*
  of split zips but not in *value*; FRAME §6 records the largest single zip at 1.07% of total `M`
  ≈ 14% of one territory, so 12 splits is not obviously negligible. If the gap swamps the premium
  the bound is decorative. **This is checkable and must be checked before the bound is quoted.**

### 2.3 Choose the welfare criterion explicitly, instead of inheriting it

- **Rests on:** **Kalai 1977** (proportional/egalitarian, dropping scale invariance for explicit
  interpersonal comparison), **Kalai & Smorodinsky 1975**, **Thomson 1994** and **Thomson 2011**
  (positioning one criterion against the family), **Moulin 2019** (the version to hand a
  committee), **Nash 1950** (what the product criterion's axioms actually are).
- **Assumptions.** Interpersonal comparability of `g_i`: **assumed throughout the programme,
  never argued.** FRAME **A4** (is `M` a trustworthy common measure?) is exactly this assumption
  and is open. **Kalai 1977** is the entry that makes the assumption visible rather than implicit.
- **Produces.** The answer to FRAME §3's binding-but-never-elicited tolerance ("how much
  continuity loss will the business accept for balance", GROM **U12**). Economic theory's claim
  is that this is *not a parameter to elicit* — it is a **choice of criterion**, and there are
  exactly three defensible ones on the table: utilitarian (maximise `P`; the base of GROM's
  fibration), egalitarian/leximin (**Kalai 1977**, and its "loudest complaint" cousin
  **Schmeidler 1969**), and Nash (the current one, the interpolant). Presenting the sponsor with
  three named criteria and their three maps is a *smaller* ask than eliciting an exchange rate,
  and **Moulin 2019** is the citation that makes it presentable.
- **Cannot say.** Which criterion the sponsor should pick. That is FRAME §2's decision right.
- **Failure mode.** If the three criteria produce visually indistinguishable maps the exercise
  is wasted effort — which is itself the finding (the exchange rate does not matter), and is
  cheap to establish. If they diverge sharply, the programme has been silently making a
  distributive choice on leadership's behalf since inception.
- **Bonus, and it closes a standing open item.** FRAME §9 lists "empty bundles / lexicographic
  MNW" as open-but-answerable. **Kalai 1977** is the FOUNDATIONS entry for the fallback when the
  product criterion is undefined (an empty bundle sends `log g_i → −∞`): lexicographic MNW
  maximises the number of positive-gain agents first, then the product on that set. One
  paragraph and one test, as FRAME already predicted.

### 2.4 Audit the roster for **stability**, not only for optimality

- **Rests on:** **Gale & Shapley 1962**, **Roth & Sotomayor 1990**, **Roth 1984** (the field
  evidence that *stability*, not efficiency, decides whether a mechanism survives), **Roth 1982**
  (only the proposing side can safely be asked for truthful preferences).
- **Assumptions.** Two-sidedness: territories have no intrinsic preferences, so this needs the
  induced ranking — territory `j` prefers the wholesaler with higher `u_i(A_j)`, wholesaler `i`
  prefers the territory with higher `u_i(A_j)`. That is a **met** construction, not an
  assumption, but it is a modelling choice that must be stated. No transfers: **met** —
  compensation is FRAME §7 out of scope. Quota `k=13` with 111 on one side: **met**; this is the
  college-admissions form.
- **Produces.** A blocking-pair enumeration over the delivered coverage: is there a
  (wholesaler, territory) pair that each prefers to its assignment? The delivered roster is
  max-weight on log gains; **a max-weight matching need not be stable** `[claim]`, and an
  unstable roster is exactly the object FRAME §2 calls low-reversibility and §3 calls "must be
  defensible line by line". **Roth 1984** is the argument to make to leadership: unstable
  assignments unravel, and the 98 non-selected are the constituency that unravels them.
- **Cannot say.** Whether stability should override welfare. If a blocking pair exists, the
  trade-off is a business call.
- **Failure mode.** With aligned preferences (both sides rank by the same `u_i(A_j)`) blocking
  pairs may be impossible for structural reasons, making the audit vacuous. That is a
  five-minute check and worth doing before the full enumeration.

### 2.5 Selection as a cooperative game: is "the 13" defensible?

- **Rests on:** **Gillies 1959** (core), **Shapley 1967** (Bondareva–Shapley: non-empty core ⇔
  balanced, and the balancedness LP *is* the certificate to report), **Shapley 1971** (convex
  games — and the diagnosis that this game is not one), **Shapley 1953** and **Young 1985**
  (the attribution rule, and the axiom to hand a committee that objects to additivity),
  **Shapley & Shubik 1969** (why market-derived allocations tend to be core-stable and when
  indivisibility breaks it), **Myerson 1977** (the value under graph-restricted cooperation, if
  geography is ever reintroduced).
- **Assumptions.** A characteristic function exists: **met**, `f(S) = Σ_z max_{i∈S} S_i(z)` or,
  better, `S ↦ max EG_S`. Transferable utility: **NOT met** — there are no side payments (FRAME
  §7) and `V` is a log-sum, so the core/Shapley machinery applies to the *surplus* game `f`, not
  to `V`. This restriction must be stated or the whole method is misapplied.
- **Produces.** Two things the programme cannot currently produce. (a) A **balancedness
  certificate** (**Shapley 1967**) — a computable test of whether any 13-seat selection is
  immune to a coalition of wholesalers arguing they should have been chosen instead. (b) A
  **Shapley value** (**Shapley 1953**) for each of the 111, i.e. an average-marginal-contribution
  ranking that is the defensible answer to "why him and not me". **Young 1985** is the
  monotonicity axiomatisation to deploy if leadership objects to additivity, and it says exactly
  what leadership will want to hear: any rule that rewards higher marginal contribution with a
  higher share *is* the Shapley value.
- **Cannot say.** The Shapley ranking need not agree with the welfare-optimal roster. Where they
  disagree, that is a finding, not an error.
- **Failure mode.** `f` is monotone **submodular**, so the game is concave and **Shapley 1971**
  gives no core guarantee; the core may be empty, in which case the balancedness LP returns
  infeasible and the honest report is "no selection is coalition-proof" — still a result, and one
  worth having before a sponsor is told the roster is defensible. Computing the exact Shapley
  value over 111 players is `2^111` and must be Monte-Carlo sampled (an optimization/statistics
  hand-off, §7).

### 2.6 The 98 as claimants: a bankruptcy problem, bounded by scope

- **Rests on:** **Aumann & Maschler 1985** (contested-estate division, and its coincidence with
  the nucleolus), **Schmeidler 1969** (the nucleolus itself, computable by a sequence of LPs).
- **Assumptions.** Fixed entitlements: **NOT met** — nobody has stated what a wholesaler is
  entitled to. Estate insufficient for claims: **met** (111 claims, 13 seats). Divisible estate:
  **not met** — seats are indivisible, which is why this is an analogy and not a computation.
- **Produces.** Vocabulary and a defensible narrative for the single most politically loaded
  output of the programme, plus the observation that FRAME §3's *"do not starve anybody"* is
  a **nucleolus-shaped** objective (minimise the loudest complaint) and not a Nash-product one.
  If that is what leadership means, the programme is optimising the wrong functional.
- **Cannot say.** Anything actionable about transfers or transition packages — FRAME §7 puts
  compensation out of scope and this method must respect that boundary.
- **Failure mode.** Over-reach. This is a framing method; if it starts producing recommended
  payouts it has left the scope FRAME §7 drew, and should be cut back to a single paragraph.

### 2.7 Strategy-proofness by restricted message space — the blocking decision

- **Rests on:** **Crawford & Varian 1979** (the Nash-product criterion is manipulable by
  preference distortion — the on-point precedent, and the reference that establishes the question
  was considered), **Hurwicz 1972** (no informationally decentralised mechanism is simultaneously
  efficient, individually rational and incentive-compatible), **Gibbard 1973** / **Satterthwaite
  1975** (unrestricted preferences ⇒ manipulable), **Myerson 1979** (revelation principle: study
  truthful direct rules without loss), **Vickrey 1961** / **Clarke 1971** / **Groves 1973** (the
  VCG escape), **Maskin 1999** (which rules are implementable at all when agents play
  strategically).
- **Assumptions.** Self-reported inputs: **contested, and this is the whole point.** FRAME
  §4 policy and **A7** treat honest reporting as a current fact and gaming as a future governance
  risk; GROM 13.1 and **U11** say the variable is *reported vs audited*, not *stage 1 vs stage 2*.
  Unrestricted preference domain (needed for Gibbard–Satterthwaite to bite): **not met** —
  valuations are additive and structured, which is a restricted domain and a real escape hatch.
- **Produces.** Three results, in increasing value. (a) **VCG is named and ruled out**: transfers
  would make truthful reporting dominant (**Clarke 1971**, **Groves 1973**), and transfers are
  out of scope (FRAME §7, compensation), so the impossibility the programme faces is
  *self-imposed by scope* — a one-sentence result worth stating to the sponsor, because it is
  reversible by them and by nobody else. (b) **Restricting the message space** to `G`-invariants
  (normalised per-rep profiles, GROTH §5b) plus audited magnitudes yields a drawing rule that is
  strategy-proof against uniform inflation **by construction**, with no theorem required
  `[claim]`; **Hurwicz 1972** then says the price is efficiency, and that price is measurable —
  re-run the draw on invariants only and compare premium retained. (c) **Maskin 1999** is the
  test to apply before proposing any rule to a body that will game it.
- **Cannot say.** Nothing here covers *selective* (per-zip) inflation, which is outside `G`.
  That gap needs either audited data (**U11**) or a genuinely new argument.
- **Failure mode.** The restricted-domain escape is only as good as the restriction. If a
  wholesaler can reshape their *profile* (moving reported book between zips at constant total),
  `G`-invariance buys nothing, and the honest answer reverts to "audited data or no
  book-awareness". **U11 decides this and is a question for the user, not a computation.**

---

## 3. Solution concept and how it is verified

**An answer, in this domain's terms, is a coverage `(π,σ)` together with five statements:**

| # | statement | verified by |
|---|---|---|
| 1 | **Efficiency with a gap.** `V(π,σ) ≥ EG_S − ε` for the selected `S`, with `ε` the EG duality gap reported in prices, not nats (2.2). | `math-verify` on the claim `EG_S ≥ max{V(π,σ) : im σ = S}`; `code-verify` on the solve and the gap. |
| 2 | **Fairness, named.** Either EF1 among the selected at `ρ = 0` and `d = 0` (2.1), **or** an explicit statement of which of those two hypotheses fails and what weaker guarantee replaces it (**Mariotti 1998** / **Xu & Yoshihara 2005**). | `math-verify` on the hypothesis check; `code-verify` on the `13×13` envy audit. A produced envy matrix *is* FRAME §3.4. |
| 3 | **Criterion, chosen not inherited.** The map is the optimum of a named welfare criterion — utilitarian, egalitarian, or Nash — that the sponsor selected (2.3). | Not verifiable by an agent. A sponsor decision; the deliverable is the three maps and their difference. |
| 4 | **Stability of the roster.** No blocking (wholesaler, territory) pair under the induced preferences, or an enumerated list of them (2.4). | `code-verify`: direct enumeration, `13 × 111`. Cheap and decisive. |
| 5 | **Selection defensibility.** Either a balancedness certificate for the chosen 13 (**Shapley 1967**) or the honest report that the core is empty, plus a sampled Shapley ranking of the 111 (2.5). | `math-verify` on the game's submodularity and on the balancedness LP being the right test; `code-verify` on the sampling. |

**What this replaces.** FRAME §3's acceptance test asks for six things; items 1–2 and 5 above
supply criteria 4 and 5 (continuity per person, distance-to-best) in a form that carries a
theorem. Item 4 supplies a criterion FRAME does not currently have and that FRAME §2's
low-reversibility row implies it needs.

**What verification must *not* accept.** A bound stated in nats (GROM 13.6). A fairness claim
at `ρ > 0`. An EF1 claim without A2 resolved. Any core/Shapley statement applied to `V` rather
than to the surplus game `f` (2.5's transferable-utility caveat).

---

## 4. Recommended path, with the decision points

**The through-line.** Economic theory's contribution here is *not* a better solver. It is that
three of FRAME's open items are the same item — the programme has never named its welfare
criterion, and the criterion is what decides the balance-vs-continuity exchange rate (§3
tolerance), the empty-bundle tie-break (§9), and whether "do not starve anybody" means Nash or
nucleolus. Everything below is ordered so that the cheap audits land before that question is
put to the sponsor, because the audits determine whether the question matters.

**Step 1 — audits on the delivered artifact (no new theory, hours).** In order:
`(a)` the `13×13` envy matrix and the EF1 verdict (2.1) — this is FRAME §3.4, and it is the
first thing the room will ask for; `(b)` the blocking-pair enumeration (2.4); `(c)` the
`ρ = 0` / `d = 0` hypothesis check that decides whether (a) carries a theorem or is just a
table. **Decision point D1:** if EF1 fails on the delivered coverage, the headline "certified"
claim (already flagged by GROM 13.2) loses its last fairness content and the note must be
rewritten before anything is presented.

**Step 2 — the criterion, as three maps (2.3).** Compute the utilitarian map (maximise `P`,
which is GROM's `P*(A)` and `P₁₃` ladder), the egalitarian/leximin map (**Kalai 1977**), and
the delivered Nash map, and put the three side by side. **Decision point D2 — the sponsor's,
and it should replace FRAME §3's un-elicited exchange rate:** *which of these three is the
channel's fairness standard?* If the three maps are close, record that and move on; if they
diverge, the programme has been choosing on leadership's behalf.

**Step 3 — the EG bound as the single certificate (2.2).** Only after step 1, because the bound
is worth quoting only if the integrality gap (≤ 12 split zips, but up to ~14% of a territory
each) does not swamp the premium. **Decision point D3:** if it does, the EG bound is decorative
and the useful bound is GROM's submodular `P₁₃` ladder instead — which is an optimization
object, §7.

**Step 4 — selection defensibility (2.5) and the claims framing (2.6).** The balancedness test
first (it is a single LP and may return "core empty", which ends the branch cleanly), then the
sampled Shapley ranking. **Decision point D4:** if the Shapley ranking disagrees with the
welfare-optimal roster on more than a seat or two, leadership needs to know *before* the roster
is announced, because the disagreement is exactly the argument a non-selected wholesaler will
make.

**Step 5 — the incentive question (2.7), gated on the user.** **Decision point D5, and it is the
one blocking item FRAME §9 records, restated smaller:** GROM 13.1 is right that "may the drawing
see books?" is the wrong question. The right one is **U11 — is audited system-of-record revenue
available at zip × wholesaler grain, and how far is it from reported book?** If yes, the
blocking decision dissolves (audited data is not a report, so **Hurwicz 1972** does not bind on
it) and the premium is capturable. If no, the fallback is the `G`-invariant message space, whose
cost is measurable by re-running the draw on normalised profiles. Also state, in one sentence to
the sponsor, that VCG would solve this outright and is excluded only by FRAME §7's no-transfers
scope — that exclusion is theirs to reverse.

**Explicitly deferred.** Anything about compensation, transition packages, or the residual
FI/wirehouse channels (FRAME §7). Method 2.6 stays a framing paragraph.

**Sequencing note.** Steps 1, 2 and 4 are independent and parallelisable. Step 3 depends on
step 1's `ρ` verdict. Step 5 depends only on the user.

---

## 5. Numbers to compute first (cheap, decisive)

All six are hours of work on the existing instance, and each one can overturn something
currently written down.

| # | number | decides | overturns if |
|---|---|---|---|
| N1 | The `13 × 13` envy matrix `u_i(A_j)` and the EF1 verdict on the delivered coverage (2.1) | FRAME §3.4 and item 2 of §3 above; the last fairness content of the word "certified" | any `i` envies `j` by more than one zip ⇒ the delivered draw is not EF1 and the guarantee was never inherited |
| N2 | Whether `ρ = 0` and whether A2 forces `d > 0` (2.1) | whether N1 carries **Caragiannis et al. 2019** or is a bare table | either fails ⇒ re-cite to **Mariotti 1998** / **Xu & Yoshihara 2005** and expect a lottery, not a point |
| N3 | Blocking-pair count over `13 × 111` under induced preferences (2.4) | roster stability, and FRAME §2's reversibility row | any blocking pair ⇒ **Roth 1984**'s unravelling argument applies to the announcement |
| N4 | The three criterion maps: utilitarian `P`-max, leximin, delivered Nash — and the pairwise share of `M` they move (2.3) | D2, and whether the never-elicited exchange rate matters at all | the three coincide ⇒ FRAME §3's binding tolerance is not binding, and **U12** closes for free |
| N5 | Balancedness LP for the selected 13 on the surplus game `f` (**Shapley 1967**) (2.5) | whether any coalition-proof selection exists | infeasible ⇒ "the roster is defensible" cannot be claimed by any selection, and the honest framing is 2.6's claims problem |
| N6 | Sampled Shapley value of all 111 on `f`, and its top-13 vs the delivered roster (2.5) | D4 — the "why him and not me" answer | large disagreement ⇒ the welfare-optimal roster is not the attribution-defensible one, and leadership must be told which they are signing |

**Not on this list, deliberately.** GROM's U1–U4 and U10 (the `g`-spread, the premium ladder,
the hand-drawn baseline) are prerequisites for several of the above but are optimization
measurements, not economic-theory ones; they belong to GROM's own recommended order and should
run first. N1–N3 do not depend on them.

---

## 6. Search brief for `lit-search`

**Questions, in priority order.**

1. **Nash welfare with heterogeneous-but-proportional valuations.** GROM 3 derives
   `Σ_i log g_i = n·log ḡ − D(g)` with a partition-dependent base, giving "equal-size districting
   is exactly MNW-optimal on level sets of total welfare, and only there". Is that fiberwise
   reading of the equal-split result stated anywhere? And what replaces it globally when agents'
   valuations are agent-specific but **correlated through a common measure** `M` — i.e.
   `u_i(z) = M_z · w_i(z)` with `w_i` bounded near 1? A modulus in the heterogeneity parameter is
   the target. *(Bears on §2.1, §2.3, D2.)*
2. **MNW with a participation margin.** Maximum Nash welfare where only `k` of `n` agents receive
   bundles and the rest receive nothing. Does EF1 survive among the selected? What is the right
   fairness axiom *across* the selection boundary? Does a nonzero outside option for the
   unselected (FRAME **A2**) change the answer? *(Bears on §2.1, §2.6, D1.)*
3. **Stability vs welfare-optimality in one-sided-preference assignment.** When both sides rank
   by a common pair value `u_i(A_j)`, is a max-weight matching automatically stable, or are there
   standard counterexamples? *(Bears on §2.4, N3 — and may make N3 vacuous, which would be worth
   knowing in advance.)*
4. **Strategy-proofness by restricted message space.** Mechanisms whose input is a *verifiable*
   or *invariant* statistic rather than a free report — "verifiable types", "partially verifiable
   information", "evidence games", "hard information". Precisely: what does the Hurwicz /
   Gibbard–Satterthwaite family forbid once the allocation rule's input is not a report?
   *(Bears on §2.7, D5, GROM **U11**.)*
5. **Max-coverage games as cooperative games.** `f(S) = Σ_z max_{i∈S} S_i(z)` is monotone
   submodular. Is the core of the induced game characterised? Is there a closed form or a
   sampling bound for its Shapley value at `n ≈ 100`? *(Bears on §2.5, N5, N6 — and this one
   straddles optimization; flag if it turns out to live there.)*
6. **Sales-territory alignment in the economics/marketing-science literature specifically as a
   fair-division or incentive problem** — not as a districting heuristic. Does anyone treat
   territory design as a mechanism the salesforce will game? *(Bears on §2.7 and on whether
   FRAME's "niche is unoccupied" claim survives contact with a second literature.)*

**Literatures to sweep.** *Fair division / computational social choice*: EC, AAMAS, IJCAI, AAAI,
ACM TEAC, GEB, JET, SCW — keywords `Nash social welfare`, `EF1`, `identical additive valuations`,
`competitive equilibrium equal incomes`, `partial allocation`, `agent selection`. Anchors from
FOUNDATIONS: **Caragiannis et al. 2019**, **Eisenberg & Gale 1959**, **Cole & Gkatzelis 2018**,
**Lee 2017**, **Amanatidis et al. 2023**, **Moulin 2019**, **Thomson 2011**.
*Matching / market design*: Econometrica, JPE, AER, MOR — `many-to-one matching`, `quota`,
`aligned preferences`, `stable vs optimal assignment`. Anchors: **Gale & Shapley 1962**,
**Roth & Sotomayor 1990**, **Roth 1982**, **Roth 1984**, **Kelso & Crawford 1982**.
*Mechanism design with verifiable information*: Econometrica, JET, GEB, TEAC — `partially
verifiable types`, `evidence`, `hard information`, `strategy-proofness on restricted domains`.
Anchors: **Hurwicz 1972**, **Gibbard 1973**, **Satterthwaite 1975**, **Myerson 1979**,
**Maskin 1999**, **Crawford & Varian 1979**.
*Cooperative games*: IJGT, GEB, MOR — `submodular game core`, `covering game`, `Shapley value
sampling`. Anchors: **Gillies 1959**, **Shapley 1967**, **Shapley 1971**, **Shapley 1953**,
**Young 1985**, **Shapley & Shubik 1969**.
*Sales-force / territory design*: Marketing Science, Management Science, EJOR — `sales territory
alignment`, `salesforce compensation and territory`, `quota gaming`.

**Deliverable.** Entries as `citation · venue/year · DOI · 2–4 sentence annotation naming which
§2 method or §4 decision point it bears on · tag ∈ {foundation, frontier,
contradicts-or-sharpens, tool-we-lack}`. Plus a **five-paper shortlist** — the five that would
most change §4 if read this week. Every absence claim must state where it was looked for
(which venues, which keywords, which citation-graph walks), because FRAME's headline "the niche
is unoccupied" rests on exactly such a claim and it has been checked in one literature only.

**Note for the searcher.** `docs/RESEARCH_FINDINGS.md` already holds ~130 verified entries from
the 2026-09-01 recon, and `docs/RESEARCH_ADDITIONS.bib` the BibTeX. Deduplicate against both
before adding; the value here is the fair-division / mechanism-design / matching axis, which
that recon covered thinly.

---

## 7. Out of this domain — hand to

| item | to | why |
|---|---|---|
| The `τ`-deformation modulus; whether `τ ↦ π*(τ)` is piecewise constant (GROTH OQ1) | **applied-math / optimization** | A homotopy/sensitivity question about a parametric program. Economic theory names the endpoints, not the path. |
| The EG solve itself, the integrality gap, the ≤ `k−1` split-zip descent, damped Newton / semi-discrete OT | **optimization** | Algorithms and duality machinery. §2.2 supplies the interpretation, not the solver. |
| GROM's `P₁₃` submodular ladder, greedy `(1−1/e)`, the max-`k`-coverage upper-bound certificate | **optimization** | GROM OQ1 already routes this correctly. §2.5 reads the same function as a cooperative game; the *bound* is optimization's. |
| Whether EG + convex geometric penalty retains a power-diagram structure (GROTH OQ2) | **optimization / geometry** | |
| The displacement metric and displacement-as-certificate (GROTH §5a, OQ5) | **optimization / applied-math** | No economic-theory counterpart, per §1. |
| The tier-2 noise floor recalibration (GROM **U6**, FRAME §10.4) | **econometrics / data-science** | A measurement question about an estimator's noise, not a welfare question. |
| Regional bias in the sizing estimate `M` (FRAME **A4**, GROM **U5**) | **econometrics** | This is an identification/measurement audit of the common measure. **It silently invalidates every certificate and every method in §2 above** — 2.3's interpersonal comparability rests on it directly. Highest-value hand-off on this table. |
| Shapley-value estimation over 111 players (sampling design, variance, stopping) | **statistics / optimization** | §2.5 states what to compute; the sampler's error bars are theirs. |
| The "two supports" / full-ZCTA-graph question (GROTH OQ7, GROM OQ6) | **geometry / optimization** | |
| Compensation, quota design, transition packages | **nobody — FRAME §7** | Out of scope by the sponsor's own boundary. Noted only because §2.7's VCG result touches it: the no-transfers scope is what creates the incentive impossibility, and only leadership can reverse it. |

---

## 8. Open questions (inputs to `/research-plan`)

1. **Is the disagreement point zero?** FRAME **A2** — the 98 keep covering the residual channel —
   has been unconfirmed for two days and is treated in FRAME as a staffing-semantics detail. It is
   not: it decides whether **Caragiannis et al. 2019** applies at all, and therefore whether the
   programme has any fairness guarantee. **Escalate A2's priority.** *(User → sponsor. One
   question.)*
2. **Which welfare criterion is the channel's standard?** Utilitarian, egalitarian/leximin, or
   Nash (§2.3, D2). The programme has been answering this implicitly since inception. FRAME §3's
   "binding tolerance that has never been elicited" is this question wearing a parameter's
   clothes, and the criterion form is a much easier ask than an exchange rate. *(User → sponsor,
   after N4 shows whether it matters.)*
3. **Is audited system-of-record book available at zip × wholesaler grain?** (GROM **U11**,
   §2.7, D5.) This is the smallest form of FRAME §9's only blocking item and it dissolves it if
   the answer is yes. *(User.)*
4. **Should stability be a hard requirement on the roster?** (§2.4, N3.) FRAME's acceptance test
   has no stability criterion; **Roth 1984** argues it is what determines survival. Adding it is a
   scope change and therefore the user's call. *(User → sponsor, gated on N3 finding any
   blocking pair.)*
5. **Does the core of the selection game exist, and does the programme want to know?** (§2.5,
   N5.) An empty core is a publishable-quality honest finding and a politically awkward one. The
   programme should decide before computing it whether "no selection is coalition-proof" is a
   sentence it is willing to write. *(User.)*
6. **Is `ρ = 0` in the delivered artifact?** (N2.) A programme fact, not a decision, but it gates
   every fairness claim and nobody has stated it in FRAME. *(Programme, minutes.)*
7. **Does §2.7(b)'s `G`-invariant drawing retain enough premium to be worth having?** GROTH OQ4
   asks the same thing and calls it the difference between "safe and worthless" and "safe and
   worth doing". It is measurable without any business input and should be scheduled regardless
   of how question 3 resolves. *(Programme.)*
8. **Does the *sponsor's* "do not starve anybody" mean the nucleolus?** (§2.6.) If FRAME §3's
   phrasing is literal, the objective is minimise-the-loudest-complaint (**Schmeidler 1969**) and
   not maximise-a-product. One sentence to the sponsor, and it is a different programme if the
   answer is yes. *(User → sponsor.)*
