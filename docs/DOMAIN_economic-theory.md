# economic-theory plan — the A1 track: joint coverage optimisation, after measurement

> Promoted from `docs/tracks/A1/` to the hub path on 2026-09-05 (user decision); the neutral
> 2026-09-02 hub plan is `docs/archive/hub-2026-09-02/DOMAIN_economic-theory.md`.

**Date:** 2026-09-03 (branch `wt/A1`) · **Framework:** 0.1 ·
**Reads:** `docs/APPROACHES.md` §A1 (the charter, taken verbatim as the problem),
`docs/FRAME.md` (§3, §5, §6 as extended 2026-09-03, §8–§10), `docs/LENS_GROMOV.md` (2026-09-03,
this branch), `docs/LENS_GROTHENDIECK.md` (inherited unchanged), `docs/MODEL_U7-meas.md` §1–§6,
`docs/MODEL_U1-cert.md` §5–§6, `docs/VERIFY_U1-cert.md` §0, §6–§7, `docs/MODEL_U2-stab.md`,
`docs/VERIFY_U2-stab.md`, `docs/DOMAIN_optimization.md` §2, §7–§8 (for non-duplication),
`docs/BRIEF.md`, `docs/units/*.md`, `~/resources/economic-theory/FOUNDATIONS.md` (seeded
2026-09-02, 95 entries), `docs/LIT_economic-theory.md` + `.bib` (46 entries, inherited
unchanged) ·
**Supersedes:** `docs/DOMAIN_economic-theory.md` of 2026-09-02 (the hub's version, written
before any measurement) — **on this branch only**. That file is the predecessor and is cited
below as **[pred]**.

**Citation rule.** Entries in **bold** are keys in `~/resources/economic-theory/FOUNDATIONS.md`.
Entries in `code` are keys in `docs/LIT_economic-theory.bib`. Entries in ★`code` are
pre-existing keys held in `docs/RESEARCH_ADDITIONS.bib` / `docs/RESEARCH_FINDINGS.md` and are
cited for positioning only, never as this plan's evidence — there is exactly one, ★`fotakis2014`,
and §2.7 says precisely what it does and does not license. Anything marked `[claim]` is this
plan's assertion, not a cited result; anything marked `[measured]` carries a source in FRAME §6
or a unit model.

**Section numbering is preserved from [pred]** so that `docs/BRIEF.md`, `docs/units/*.md` and
`docs/LIT_economic-theory.md` cross-references still resolve: §2.1–§2.7 keep their subjects,
§3's five statements keep their numbers, §4's steps keep D1–D5, §5 keeps N1–N6, §7 and §8's
Q1–Q8 keep theirs. New material is appended (§2.8–§2.10, N7–N11, D6–D7, Q9–Q12) and is marked
**new**.

---

## 0. What the measurements did to [pred] — retired, kept, changed

Between [pred] and this file, three things landed: `U7-meas` (the premium ladder), `U1-cert`
(the EG bound, verified) and the A1 charter with `LENS_GROMOV`'s band-constrained reformulation
`EG^bal_S`. FRAME §6's 2026-09-03 rows are the arithmetic. The verdict on [pred], method by
method:

| [pred] item | verdict | why |
|---|---|---|
| §2.1 EF1 / PO audit | **changed, and re-scoped** | Still the right audit, but its target moved: the object to audit is no longer the delivered coverage against an unconstrained MNW ideal, it is the *band-constrained* optimum. `barman2023gac`'s feasible envy-freeness — which [pred] parked until an operational rule appeared — is live now, because the band **is** the assignment constraint. And the guarantee [pred] hoped to inherit was never inheritable: `EG_{S₁₃} − V = 0.760` nats `[measured]` is the distance from the delivered draw to the MNW optimum. |
| §2.2 EG / CEEI relaxation, duals as the premium bound | **kept, and discharged as stated** | `U1-cert` computed it: `EG_{S₁₃} = 60.697416` vs `V = 59.937470`, bracket `7e-15`, three of four certificates collapse into its dual `[measured]`. [pred]'s stated failure mode ("the integrality gap may swamp the bound") is measured and does **not** fire — `≤ k−1` splits, `M(F)` 2.4–3.2% of `T`, vertex-dependent. A different failure fired instead: the bound is over a feasible set the sponsor rejects (`M`-spread ≥ 50%). That is what §2.8 replaces it with. |
| §2.3 choose the welfare criterion (Atkinson ε) | **kept, and sharpened by one measured fact** | The criterion question stands. What is new is that it is **two** knobs, not one: `δ` (the balance band, on `M`) and `ε` (inequality aversion, on `g`). `M`-spread 0.781% against `g`-spread 60.65% `[measured]` is a factor of 77.6 — proof that a sponsor who states `δ` has said nothing about `ε`. [pred] §2.3 implicitly treated one choice as settling both. |
| §2.4 stability audit | **kept, cheapened, and now conditional on the band** | `U2-stab` VERIFIED 13/13: `eeckhout2000`'s SPC holds under the induced preferences, the stable roster is greedy top-pair, and no unselected rep can block a max-weight roster (P3.3) — so the audit is **169 comparisons, not 1,443**. New: `g_ij = B_j + w·b_ij` with `B_j` near-equal *because the map is balanced*, which bounds the size of any block; widening the band re-introduces a size term into every rep's ranking. **Stability is a function of `δ`.** |
| §2.5 selection as a cooperative game | **kept, and re-scoped downward** | `littlechild1973` + additivity already deleted the sampler. What measurement adds: books among the selected 13 are near-disjoint (83 contested zips, 6.12% of `M`; greedy attains the `P₁₃` MILP optimum) `[measured]`, so `f` is *near-modular* on the relevant rosters. Near-modularity makes the Shapley value nearly "your own book", which is simultaneously the most defensible and the most gameable answer — it hands §2.5 to §2.7. |
| §2.6 the 98 as claimants | **kept, and upgraded from analogy to a number** | The aggregate claim of the best alternative roster over the delivered one is `P₁₃ − P_S = 0.92%` of total book = `0.043` nats `[measured]`. A claims argument now has a magnitude. `aignerhorev2022` (envy-free matchings) makes the across-the-boundary axiom computable, as [pred] and `LIT` §2 already noted. |
| §2.7 strategy-proofness by restricted message space | **changed materially — this is where the charter moved the most** | `LENS_GROMOV` M13.2: books now enter the draw **only** through the objective of one concave program per roster. That is a much smaller attack surface than "the drawing reads books", and it admits a theorem [pred] could not state: **at fixed roster the EG map and prices are invariant under `G`; the roster *selection* is not** `[claim]`. §2.7 is rewritten around that split. ★`fotakis2014`'s scope is stated precisely for the first time. |
| §2.8–§2.10 | **new** | `EG^bal_S` as CEEI-with-quantity-bands (§2.8); the band duals as an exchange rate, and the shadow-price-vs-preference distinction (§2.9); roster selection as a 13-seat, 111-bidder market without transfers (§2.10). |
| [pred] §4 step 3's *decision* D3 ("is the EG bound decorative?") | **retired — answered NO** | `U1-cert` P3: the split-unit budget is `≤ k−1` and the measured split mass is small. The bound is not decorative. D3 is re-used below for a different question and its old text is withdrawn. |
| [pred] §5 N2 (`ρ = 0`?) | **retired — answered YES** | `VERIFY_U2-stab` row 1: `ρ` occurs nowhere in `td/channel.py`; the delivered `g` carries no compactness term. The `ρ` half of D1 is closed. The `d = 0` half (**A2**) is still open. |
| [pred] §5 N4's premise ("three criterion maps") | **changed** | The `ε = 0` map is not a separate object to build: it is FRAME §10 Q8's transportation LP, and `DOMAIN_optimization` owns the solve. Economic theory owns only the reading. |
| [pred] §7's Shapley-sampling hand-off to statistics | **retired** | `littlechild1973` closed form; `LIT` §0.1 already struck it and this file records the strike as final. |

**One thing [pred] got right and measurement confirmed.** [pred]'s through-line — *the programme
has never named its welfare criterion, and the criterion is what decides the balance/continuity
tolerance* — survives intact and is now quantified. It is the same sentence FRAME §3 writes as
"the binding tolerance has never been elicited" and `LENS_GROMOV` writes as **U12**.

---

## 1. What the lenses handed over, in this domain's terms

`LENS_GROTHENDIECK` is inherited unchanged; its rows below are carried from [pred] §1 with any
change marked. `LENS_GROMOV` (2026-09-03) is new and supplies rows 9–16.

| lens construct (file §) | becomes | or: no counterpart, because |
|---|---|---|
| **Coverage / composite value `V(π,σ)`** (GROTH §3) | Nash social welfare at a zero baseline over the selected agents, with additive valuations. **Caragiannis et al. 2019**, **Eisenberg & Gale 1959**. *Unchanged from [pred].* | |
| **The `τ`-deformation** (GROTH §2) | The path from identical to heterogeneous additive valuations; endpoints are named objects (**Thomson 2011**, **Moulin 2019**), the path is not. *Unchanged.* Superseded operationally: `LENS_GROMOV` M8 argues `δ ↦ EG^bal(δ)` replaces `τ ↦ π*(τ)` as the experiment. | the homotopy itself has no counterpart — economic theory does not deform valuation profiles continuously. |
| **Equal-budget market (EG)** (GROTH §2 step 2) | Competitive equilibrium from equal incomes on goods `Z` endowed with `M`. **Eisenberg & Gale 1959**, **Hylland & Zeckhauser 1979**, **Varian 1974**; `budish2011` for the version that survives combinatorial constraints. **Nash 1950** supplies the axiom that makes it manipulation-relevant (scale invariance) — see §2.7. | |
| **Displacement metric** (GROTH §5a) | | No counterpart, as [pred] said. Economic theory ranks allocations and forms welfare *ratios* (`bertsimas2011`, **Bei et al. 2022**); it does not metrise the space of allocations. Hand back to optimization. |
| **Inflation group `G = (ℝ_{>0})^R`** (GROTH §5b) | The message space of a direct mechanism. `green1986`'s Nested Range Condition is the test; **Myerson 1979** licenses restricting to truthful direct rules; `bull2007` is the modern evidence formulation. **Changed:** the group now acts on the *objective of one concave program*, which is a far sharper question — §2.7. | |
| **The two supports** (GROTH §5b) | | No counterpart. A support/geometry fact. |
| **Fibration `Σ log g = n log ḡ − D(g)`** (GROM 2026-09-02, M3) | Atkinson's equally-distributed-equivalent identity at `ε = 1`; `D(g)` is the mean logarithmic deviation. `atkinson1970`, `shorrocks1980`, `foster2000`. Cite, do not prove (`LIT` §0.5). | |
| **The premium `P`** and the ladder `P₀ ≤ P*(A) ≤ P_S ≤ P₁₃ ≤ P_free` | The utilitarian (`ε = 0`) objective and its exact maxima under successively weaker restrictions. **Measured** `[measured]`: 37.82 / 37.82 / 51.43 / 52.34 / 79.44 % of book. The gaps are the utilitarian value of, respectively, re-matching (0), redrawing (13.61%), re-rostering (0.92%), and raising `k` (27.1%, out of scope). | |
| **`EG^bal_S(δ)`** — EG with per-agent quantity bands on `M` (GROM M8) | **A Fisher market with equal budgets and per-agent quantity constraints on a second, common measure.** This is not textbook CEEI: the equilibrium survives with *personalised* prices `p_z + ν_i M_z`, not common ones. Nearest published models: `budish2011` (approximate CEEI under combinatorial constraints), `barman2025market` (a common market value plus subjective valuations), `barman2023gac` (envy restricted to feasible bundles). §2.8. | |
| **The band duals `μ_i^±`** (GROM M11.2, U14) | Shadow prices in nats per unit of `M`. Economically: the **marginal rate of transformation** between balance and continuity on the frontier — *not* the sponsor's marginal rate of substitution. §2.9. | |
| **The frontier `δ ↦ EG^bal(δ)`** (GROM U13) | A menu. **Roth 2002** (design as engineering) and **Moulin 2019** (what to hand a committee) are the citations for presenting a choice from a menu rather than eliciting a scalar. `bertsimas2011` gives the a-priori magnitude of the trade before any solve. | |
| **The softness test** `EG^bal(δ) − V ≤ 5e-3` (GROM M12) | Whether the fairness/efficiency choice is *material*. If soft, every band-feasible allocation is welfare-equivalent and the criterion question is moot — which is itself the answer to FRAME §3's tolerance. | |
| **Roster enumeration over `EG^bal_S`** (GROM M13.1, U16) | Selection as a market: 13 indivisible seats, 111 agents, no transfers, principal's value nearly determined by book. `benporath2014` (costly verification, favoured-agent optimum) is the model; **Gale & Shapley 1962** / **Roth 1982** the structure; **Shapley & Shubik 1971** ruled out for want of transfers. §2.10. | |
| **`max_S EG^bal_S` and whether `S ↦ EG^bal_S` is submodular** (GROM U19, Q4) | A characteristic function on wholesaler coalitions — the cooperative game of §2.5, now defined on the *band-constrained* fibre value rather than on coverage `f`. `deng1999` (core ⇔ LP integrality), `chen2020coreness` (truncated submodular profit games), `goemans2004` (the honest complexity). Note: `littlechild1973`'s closed form applies to `f`, **not** to `S ↦ EG^bal_S`. | |
| **Nash-tie fragility `U17`** (8.1e-3 nats on seed 9) | Multiplicity of the mechanism's output at the programme's own tolerance. **Mariotti 1998** predicts exactly this on a finite alternative set (a lottery, not a point); **Hylland & Zeckhauser 1979** is the mechanism that embraces it. §2.10. | |
| **`U6` — the data-noise floor** | | No counterpart. A measurement question — §7. |
| **`U5` / A4 — regional bias in `M`** | | No counterpart *and* invisible to every method here: `VERIFY_U1-cert` §6 confirms a regional bias shifts the certificate and the thing it certifies together. Still the highest-value hand-off on §7's table. |

**The single most consequential re-reading, restated after measurement.** [pred] said the
programme had mis-cast an *allocation with a participation margin* as a byproduct of an
assignment. That stands. What measurement adds is the magnitude, and it is small: the entire
selection margin is worth `0.043` nats `[measured]`, and the entire redraw at the delivered
roster is worth at most `0.760` nats before the band bites. **The economics of this problem is
no longer about how much value is on the table. It is about which of several
welfare-indistinguishable answers the sponsor is entitled to be shown, and whether the rule
that picks among them can be gamed.**

---

## 2. Candidate methods

### 2.1 The fairness audit — EF1 / PO — retargeted at the band-constrained optimum

*(subject preserved from [pred] §2.1; content changed)*

- **Rests on:** **Caragiannis et al. 2019** (MNW over indivisible goods is PO and EF1),
  **Eisenberg & Gale 1959**, **Varian 1974**; and, new, `barman2023gac` (feasible
  envy-freeness FEF/FEFx — envy evaluated only against bundles the agent could actually have
  received under the assignment constraints) and `barman2025market` (goods carrying both a
  common market value and agent-specific subjective values).
- **Assumptions, and whether FRAME §5/§6 meet them.**
  - Additive valuations — **met** (`u_i(z)` is a per-zip sum, `docs/MODEL.md`).
  - Goods not chores, all `u_i(z) ≥ 0` — **met** under headroom, with the caveat that 69 zips
    exceed it by `≤ 4.2e-7` relative (`MODEL_U1-cert` §5.2) — immaterial here.
  - All goods allocated, one bundle per agent — **met** (FRAME §4).
  - `ρ = 0` — **met, and now established**: `VERIFY_U2-stab` row 1 confirms `ρ` appears nowhere
    in `td/channel.py`. [pred]'s N2 half-closes here.
  - **Zero baseline `d = 0` — still NOT established.** FRAME **A2** (the 98 keep covering the
    residual channel) is unconfirmed since 2026-08-31. `LIT` absence A4 records that if `d > 0`
    there is no weaker EF1-flavoured theorem to fall back on — only **Mariotti 1998** /
    **Xu & Yoshihara 2005**, and those deliver a lottery.
  - **New, and it is the assumption the charter adds: the allocation is band-constrained.**
    **Caragiannis et al. 2019** characterises the *unconstrained* MNW optimum. Under a quantity
    band the maximiser of `Σ log u_i` is not the MNW allocation of the instance, and the EF1
    guarantee lapses — not because a hypothesis is violated but because the object is different.
    `barman2023gac` is the entry that handles it: under assignment constraints the right notion
    is **FEFx**, envy against bundles the envier could feasibly have held.
- **What it would produce.** (a) The `13 × 13` envy matrix on the delivered coverage — FRAME
  §3.4's per-wholesaler continuity report in a form carrying a theorem — with the verdict stated
  three ways: plain EF1 (the wrong test under a band), FEFx w.r.t. the band (the right one), and
  proportionality (`u_i(A_{σ(i)}) ≥ u_i(Z)/k`, the property FRAME §3's "do not starve anybody"
  most nearly names). (b) The same three verdicts at the `EG^bal` rounded optimum, which is what
  A1 would actually deliver. (c) A statement of *how much* fairness the band costs, in the same
  units as §2.9's exchange rate.
- **What it cannot say.** Nothing about the 98 — envy across the selection boundary is a
  different axiom (`aignerhorev2022`; §2.6). Nothing about whether a fairness failure matters:
  that is D2.
- **Failure mode.** Two live, one retired. *(retired)* [pred]'s failure (i) — the `ρ > 0`
  lapse — cannot fire, `ρ = 0`. *(live)* (ii) If **A2** makes `d > 0`, the citations become
  **Mariotti 1998** / **Xu & Yoshihara 2005** and the deliverable is a lottery, which collides
  with FRAME §2's low-reversibility row. *(live, new)* (iii) The measured `g`-spread of **60.65%**
  `[measured]` makes a *large* envy verdict the prior, not a surprise. If plain EF1 fails by a
  wide margin the honest report is not "the draw is unfair" but "EF1 was never the right test on
  a band-constrained allocation" — and it must be written that way, or the audit will be read as
  an indictment of the delivered map.

### 2.2 The Eisenberg–Gale / CEEI relaxation, with the duals as the premium bound

*(subject preserved; **discharged** — this method has been executed)*

- **Rests on:** **Eisenberg & Gale 1959**, **Hylland & Zeckhauser 1979**, **Nash 1950**.
- **Status.** Executed by `U1-cert` and verified. `EG_{S₁₃} = 60.697416`, `V = 59.937470`,
  gap `0.759946` nats, bracket `7.1e-15`; three of four existing certificates are degenerations
  of its dual, the fourth (the integer balance floor) is primal-only `[measured]`.
- **Assumptions, re-checked against FRAME §6.** Concavity — met. Equal budgets ⇔ equal
  entitlement — met by business intent (FRAME §7 rules out non-equal entitlements). Divisible
  goods — not met; the descent costs `≤ k−1 = 12` split units, **proved on the MBB face and
  verified**, with measured split mass `M(F)` 2.4–3.2% of `T` and vertex-dependent (quote only
  with the mass, never bare — `MODEL_U1-cert` §5.9).
- **What it produced, and what it cannot say.** It answered FRAME §10 Q3 (the missing premium
  bound) at the delivered roster. It cannot say anything about a *different* roster (§2.10), and
  — the finding that matters — **it bounds over a feasible set the sponsor rejects**: the EG
  vertex realising the 0.760 nats has `M`-spread `≥ 50%` on two independent solves `[measured]`.
- **Failure mode, resolved and replaced.** [pred] worried the integrality gap would swamp the
  bound; it does not. The failure that fired is infeasibility of the extremiser, and §2.8 is the
  repair. Retained here as the `δ = ∞` endpoint of §2.8's family and as the citation anchor.

### 2.3 The welfare criterion, chosen not inherited — and it is **two** knobs

*(subject preserved; sharpened)*

- **Rests on:** `atkinson1970` (the equally-distributed-equivalent identity and the ε-family),
  `shorrocks1980` (generalised entropy is exactly the additively decomposable class),
  `foster2000` (MLD is the unique path-independent decomposable measure), **Kalai 1977**
  (egalitarian/proportional solutions and the interpersonal comparison they require),
  **Kalai & Smorodinsky 1975**, **Thomson 1994**, **Thomson 2011**, **Moulin 2019**,
  **Nash 1950**; `bertsimas2011` (the price of fairness, a priori); `bhaskar2023equity` (the
  first published bound on how far the `p`-mean family's optima can be apart, binary-valuation
  caveat); `echenique2024` (stability and efficiency as different members of one
  inequality-indexed family).
- **Assumptions.** Interpersonal comparability of `g_i` — **assumed throughout the programme,
  never argued**, and it is FRAME **A4** wearing a different hat. **Kalai 1977** is the entry
  that makes the assumption visible. `foster2000`'s path-independence covers the **balance term
  only** and is silent on the incumbency term — which, per `U1-cert` §6, is where the two-stage
  split actually costs (0.760 nats). Say so; do not over-claim the decomposition.
- **What it would produce — and the one new thing.** [pred] said: present three named criteria
  (ε = 0 utilitarian, ε = 1 Nash/delivered, ε → ∞ leximin) instead of eliciting an exchange
  rate. That stands. **The new content is that ε is not the only knob and cannot substitute for
  the other.** `ε` is inequality aversion over realised gains `g`; `δ` is the balance band over
  opportunity `M`. The programme has been reporting `δ`-language (0.781% spread) as if it settled
  `ε`-questions, and the measurement shows the two came apart by a factor of **77.6**
  (`g`-spread 60.65% vs `M`-spread 0.781%) `[measured]`. That single ratio is the most useful
  sentence economic theory has for the sponsor, and it is a direct instance of
  `LENS_GROTHENDIECK`'s yoga *never ask one number to serve both balance and continuity*.
- **What it cannot say.** Which `(δ, ε)` the sponsor should pick — FRAME §2's decision right.
- **Failure mode.** If `EG^bal(δ) − V ≤ 5e-3` for every `δ` the sponsor would consider
  (`LENS_GROMOV` M12's softness test), the ε-question is moot inside the band and the exercise
  is wasted — which is itself the finding, and is one parametric solve away. Conversely if the
  criteria diverge sharply, the programme has been making a distributive choice on leadership's
  behalf since inception, which is [pred]'s original charge and still the risk.
- **Bonus, unchanged and still standing.** **Kalai 1977** is the FOUNDATIONS entry for the
  empty-bundle fallback (`log g_i → −∞`): lexicographic MNW maximises the number of positive-gain
  agents first, then the product on that set. FRAME §9's "open, but answerable from the
  literature" — one paragraph and one test.

### 2.4 Roster **stability**, now decidable in 169 comparisons — and a function of the band

*(subject preserved; the audit is cheaper and the new content is the δ-dependence)*

- **Rests on:** **Gale & Shapley 1962**, **Roth & Sotomayor 1990**, **Roth 1984** (stability, not
  efficiency, decides survival), **Roth 1982** (only the proposing side can safely be asked);
  `eeckhout2000` (SPC ⇒ the stable matching is unique and is greedy top-pair), `clark2006` (the
  weaker No Crossing Condition, for when alignment is perturbed), `consuegra2013` (SPC is
  sufficient, **not** necessary — never write "iff"), `niederle2009` (with aligned preferences an
  announced unstable roster is renegotiated by the parties themselves), `echenique2024`.
- **Assumptions, and their status.** Two-sidedness by the induced ranking (`u_i(A_j)` for both
  sides) — a modelling choice, stated. No transfers — met (FRAME §7). Quota `k = 13` with 111 on
  one side — met, the college-admissions form. **Alignment** — established and verified:
  `VERIFY_U2-stab` rows 1–3, with `g_ij = B_j + w·b_ij`, `w = (1−λ)(1−θ) = 0.42` exactly
  `[measured]`.
- **What it would produce.** (a) The blocking-pair enumeration, and it is now **169
  comparisons, not 1,443** — `MODEL_U2-stab` P3.3 (VERIFIED) proves no unselected wholesaler can
  block a max-weight roster, so only the `13 × 13` selected submatrix matters. (b) The
  greedy-vs-Hungarian comparison, which `eeckhout2000` predicts will differ. (c) **New, and this
  is the method's real content under the A1 charter: the stability verdict as a function of the
  band `δ`.**
- **The δ-dependence, stated so it can be attacked** `[claim]`. Write `g_ij = B_j + w·b_ij`.
  Both sides rank pairs by `g_ij`; a blocking pair `(i, j)` gains
  `g_ij − g_{i,σ(i)} = (B_j − B_{σ(i)}) + w(b_ij − b_{i,σ(i)})`.
  - At the delivered draw the band is tight (`M`-spread 0.781%), so `B_j ≈ B` and blocking is
    driven **only** by fit `b`: the market is *horizontally* differentiated, and the gain from
    any block is at most `w·max_i,j Δb`.
  - As `δ` grows the `B_j` spread grows with it, adding a rep-independent size term to every
    comparison. In the limit all 13 rank districts identically by size: the market becomes
    **vertically** differentiated, every rep wants the biggest territory, and blocking pairs are
    about queue position rather than fit.
  - So **balance is what makes the delivered roster nearly stable, and buying premium by widening
    the band buys instability.** This is a testable prediction and it is the economics
    counterpart of `LENS_GROMOV` M12's borderline analysis — the zips that move first as `δ`
    crosses `δ*` are also the zips that first break the roster.
  - It does **not** say blocking pairs vanish at `δ = 0.0078`: greedy ≠ Hungarian generically
    even on a monotone transform of `b` (`VERIFY_U2-stab` row 8's `3 × 3` witness). It bounds
    their *size*.
- **What it cannot say.** Whether stability should override welfare (★3, a business call), and
  whether **Roth 1982**'s two-sided strategy-proofness obstruction weakens when the stable
  matching is unique — `MODEL_U2-stab` §8.3 flags this as unsettled and it stays unsettled.
- **Failure mode.** [pred] feared the audit was vacuous under aligned preferences; `U2-stab`
  proves it is not (`eeckhout2000` + the `3 × 3` witness). The live risk is the opposite:
  `U2-stab` P3.4 predicts the Hungarian roster coincides with the stable one **~70%** of the time
  at this shape — a *prediction*, at the 13×13 slack, not a measurement — so the audit may
  return "no blocking pair" and be read as a clean bill of health when it is a coin flip.
  Report the margin, not just the verdict. **U17** compounds this: at an 8.1e-3-nat Nash-tie
  margin `[measured]`, the roster whose stability is being audited is itself not uniquely
  determined at the programme's own floor.

### 2.5 Selection as a cooperative game — near-modular, and it hands itself to §2.7

*(subject preserved; re-scoped downward by the disjointness measurement)*

- **Rests on:** **Gillies 1959** (core), **Shapley 1967** (Bondareva–Shapley), **Shapley 1971**
  (convex games — and the diagnosis that this one is not), **Shapley 1953** / **Young 1985**
  (attribution and its axiomatic defence), **Shapley & Shubik 1969**, **Myerson 1977**;
  `littlechild1973` (closed-form Shapley for `v(S) = max_{i∈S} c_i`), `deng1999` (core non-empty
  **iff** the associated LP has an integer optimum), `deng2000` (total balancedness),
  `goemans2004` (core non-emptiness is NP-complete for facility-location games — the honest cost),
  `chen2020coreness` (truncated submodular profit games: emptiness decidable in P),
  `kern2003` (least core and nucleolus when the core is empty), `deng1994`, `chalkiadakis2012`.
- **Assumptions.** A characteristic function exists — met, `f(S) = Σ_z max_{i∈S} S_i(z)`.
  **Transferable utility — NOT met**; there are no side payments (FRAME §7) and `V` is a log-sum,
  so the machinery applies to the *surplus* game `f`, never to `V`. This restriction was [pred]'s
  and it is load-bearing; `docs/units/U6-sel.md` already carries it.
- **What measurement changed.** Among the selected 13 the books are near-disjoint: 83 contested
  zips, 6.12% of `M`, and greedy attains the `P₁₃` MILP optimum `[measured]`. On the near-optimal
  rosters `f` is therefore **near-modular**, and three things follow.
  1. `φ_i(f) ≈ S_i(Z)` — the Shapley value degenerates toward "your own book". That is the most
     defensible possible answer to "why him and not me" (**Young 1985**: any rule rewarding
     higher marginal contribution *is* the Shapley value) **and** the most gameable one. §2.7
     inherits it.
  2. The core-emptiness argument still bites (`LIT` §0.2: a single tie forces
     `x_1 + x_2 = 1` with `x_i ≥ 1`), but the **excess** is small — the least core
     (`kern2003`) will quantify a small number, not a scandal. Report the least-core value, not
     the binary "core empty".
  3. `LENS_GROMOV` **U19** asks the same question about a different function: is
     `S ↦ EG^bal_S` submodular, or at least near-modular over the `P₁₃`-slack rosters? If yes,
     the roster enumeration of M13.1 is *provably* enough rather than heuristically enough. Note
     that `littlechild1973` does **not** transfer — `EG^bal_S` is not a sum of airport games —
     so the fallback is `castro2009` / `castro2017` sampling with one EG solve per sample, which
     is expensive. **This is the theorem-shaped item in this section.**
- **What it cannot say.** Whether the Shapley ranking should override the welfare-optimal roster.
  Where they disagree that is a finding (D4).
- **Failure mode.** `goemans2004` says core questions on facility-like structures are NP-complete
  in general; our tractability, if any, comes from `deng1999`'s integrality route on *our*
  formulation. Scope N5 with `goemans2004` cited, or the estimate will be wrong.

### 2.6 The 98 as claimants — now with a magnitude

*(subject preserved; upgraded from framing to computation, capped as before)*

- **Rests on:** **Aumann & Maschler 1985** (contested estate, coincident with the nucleolus),
  **Schmeidler 1969** (the nucleolus itself), `kern2003` (least core / nucleolus by LPs),
  `aignerhorev2022` (envy-free matchings: no *unmatched* agent envies a matched one — the axiom
  across the selection boundary), `gan2019` (`m < n` house allocation, unit demand),
  `smith2000` (field evidence: the losing side of a realignment responds to procedural and
  distributive justice, not to efficiency arguments), `arnold2009` (fairness judgements are formed
  against multiple referents, including out-group ones — so the `13 × 13` matrix is not the whole
  comparison the affected population makes).
- **Assumptions.** Fixed entitlements — **not met**; nobody has stated what a wholesaler is
  entitled to. Estate insufficient for claims — met (111 claims, 13 seats). Divisible estate —
  not met; this is why it is an analogy for the *estate* and a computation for the *excess*.
- **What measurement adds, and it is the whole upgrade.** The aggregate claim of the best
  alternative roster over the delivered one is `P₁₃ − P_S = 0.92%` of total book `≈ 0.043` nats
  `[measured]`. In the programme's own units, **the strongest collective statement any set of
  unselected wholesalers can make about the roster is worth under one percent of the book.**
  That is a number a sponsor can be handed, and it is much more useful than a bankruptcy
  narrative. Per-wholesaler, the individual version is `φ_i(f)` (§2.5) and it is exact and cheap.
  `MODEL_U2-stab` P4.2/P4.3 (VERIFIED) already establishes the sharp negative result on the
  other side: **EFM together with full staffing is infeasible under H1 with `n > k`** — the only
  envy-free matching is the empty one, so "no unselected wholesaler envies a selected one" is
  unachievable by construction and must never be promised.
- **What it cannot say.** Anything actionable about transfers or transition packages — FRAME §7.
- **Failure mode.** Over-reach, as before. This stays one paragraph plus two numbers (the 0.92%
  and the Shapley ranking). If it starts producing recommended payouts it has left scope.

### 2.7 Strategy-proofness with the attack surface narrowed to one concave program

*(subject preserved; **materially rewritten** — this is where the A1 charter changed the most)*

- **Rests on:** `green1986` (Nested Range Condition: the revelation principle survives message
  restriction **iff** NRC holds — the load-bearing citation, replacing **Hurwicz 1972**),
  `bull2007` (hard evidence, normality), `deneckere2008` (beyond NRC), `benporath2012`
  (implementation with partial provability; *arbitrarily small* transfers suffice),
  `kartik2012` (with evidence, Maskin monotonicity is no longer necessary — this **sharpens**
  [pred]'s use of **Maskin 1999**), `benporath2014` (optimal allocation with costly verification,
  no transfers — the favoured-agent mechanism), `mylovanov2017` (ex-post verification, limited
  penalties), `benporath2019` (no commitment needed), `caragiannis2012` (probabilistic
  verification), `milgrom1981` (unravelling under a credible audit threat);
  **Crawford & Varian 1979** (the Nash-product criterion *is* manipulable by preference
  distortion), **Gibbard 1973** / **Satterthwaite 1975**, **Myerson 1979**,
  **Vickrey 1961** / **Clarke 1971** / **Groves 1973**, **Nash 1950**.
- **What the charter changed.** Under A1 the draw reads books **only** through the objective of
  one concave program per roster (`LENS_GROMOV` M13.2). Three consequences, and the third is new
  to this file.

  **(a) What ★`fotakis2014` actually forbids, stated precisely.** ★`fotakis2014` (held in
  `docs/RESEARCH_ADDITIONS.bib`, not in FOUNDATIONS; cited for positioning only) is a facility
  *location* result: for `k ≥ 3` facilities, **deterministic anonymous** strategyproof mechanisms
  have unbounded approximation ratio when agents report positions on a line/metric. Three of its
  hypotheses are worth checking against A1 rather than assuming: (i) *anonymity* — A1's
  formulation is **rep-indexed**, so it is not anonymous, and `DOMAIN_optimization` §2.1 makes
  that the point of the formulation; (ii) the reported type is an agent's **location**, whereas
  ours is a per-agent *measure* over 1,229 zips and enters an objective, not a facility-placement
  rule; (iii) the mechanism's output there is a location vector, ours is a partition plus a
  roster. **So ★`fotakis2014` does not directly apply, and the programme's `RESEARCH_FINDINGS`
  §9-G invariant ("books enter at stage 2 only, because fotakis2014") over-reads it.** What
  survives, and it is enough to keep the governance concern alive, is the generic
  **Gibbard 1973** / **Satterthwaite 1975** obstruction on an unrestricted domain — from which
  the escape is exactly domain restriction, which is what (b) and (c) are about. Correcting this
  over-read is a deliverable in its own right: FINDINGS §9-G, `REVIEW_GROMOV`, `CHANNEL.md` §0
  and `APPROACHES.md` all repeat it.

  **(b) `green1986` is the test, and it applies to a smaller object now.** The `G`-invariant
  message space (normalised per-rep profiles plus audited magnitudes, `LENS_GROTHENDIECK` §5b)
  is a partial-verification mechanism; NRC is the checkable algebraic condition on
  `(ℝ_{>0})^R`-orbits that decides whether the revelation principle survives. `docs/units/U3-inv.md`
  already owns this and it is unchanged by measurement. `bull2007` is the modern statement of what
  structure audited data must have; `deneckere2008` is the fallback if NRC fails.

  **(c) `G`-invariance of the EG **duals** — the lens's Q6, answered in a form that splits the
  problem cleanly.** `[claim]`, and it is the highest-value new item in this plan.
  Let `G = (ℝ_{>0})^R` act by `u_i ↦ γ_i u_i`.
  - **P-G1.** For any fixed roster `S` and any band `δ`, the argmax `x*` of `EG^bal_S`, the
    per-zip prices `p_z` and the band multipliers `μ_i^±` are **unchanged**, and the value shifts
    by the constant `Σ_{i∈S} log γ_i`. *Reason:* the objective is `Σ_i log(u_i·x_i)` and the
    feasible set does not involve `u`; scaling `u_i` adds `log γ_i` to the `i`-th term. This is
    exactly **Nash 1950**'s scale-invariance axiom and the reason the Eisenberg–Gale program is
    the canonical manipulation-tolerant welfare aggregator (**Eisenberg & Gale 1959**).
  - **P-G2.** `max_S EG^bal_S` is **not** invariant: roster `S` is preferred to `S'` iff
    `EG^bal_S + Σ_{i∈S} log γ_i > EG^bal_{S'} + Σ_{i∈S'} log γ_i`, so a wholesaler can buy their
    way into the roster by inflating `γ_i`, and the inflation is *unbounded* in effect because
    `log` is unbounded above.
  - **Therefore: the map is `G`-invariant at fixed roster; the selection is not.** This is the
    formal handle `LENS_GROMOV` Q6 asked for, and it converts FINDINGS §9-G's policy preference
    ("compute selection from audited revenue; use reports only within-retained") into a theorem
    about where audited data is *required* and where reported data is *harmless*.
  - **P-G3 — the caveat that must be checked before any of this is quoted.** The programme's
    `u_i` is **not** of the form `γ_i·v_i`. It is
    `u_i(z) = c2·T_z + c_free·S_free(z) + λ·M_z + w·S_i(z)` with `T_z = Σ_j S_j(z)`, so inflating
    `S_i` moves both rep `i`'s own term *and* the common term `c2·T_z` that every rep sees.
    `u_i` is **affine, not homogeneous, in the reported book**, and P-G1 does not apply as-is.
    The size of the failure is governed by `c2` against `w = c1 − c2 = 0.42` `[measured]` and is
    computable in one pass. **The design fix is exact and cheap:** define the draw's valuation
    homogeneously in the rep's own reported book — normalised profile `S_i(z)/S_i(Z)` times an
    audited magnitude — and P-G1 becomes a theorem about the delivered map rather than a hope.
    That is precisely `LENS_GROTHENDIECK` §5b's invariant subalgebra, arriving from the dual side.
- **Assumptions, against FRAME §5/§6.** Self-reported inputs — **contested, and it is the whole
  point**; FRAME **A7** treats honest reporting as a current fact and gaming as a future risk.
  Unrestricted preference domain (needed for Gibbard–Satterthwaite to bite) — **not met**;
  valuations are additive and structured, which is a genuine escape hatch. Audited book at
  zip × wholesaler grain — **unknown**, and it is ★2 / **U11**, a user question.
- **What it would produce.** (i) The corrected scope statement for ★`fotakis2014` (a
  documentation fix in four files). (ii) P-G1/P-G2/P-G3 as propositions for `math-verify` — one
  page, no instance needed for the first two, one pass over the export for the third.
  (iii) The audited/reported split as a *rule*: audited magnitudes for selection, reported
  profiles for the draw. (iv) The one sentence [pred] wanted the sponsor to hear, now smaller:
  VCG would solve this outright and is excluded only by FRAME §7's no-transfers scope
  (**Clarke 1971**, **Groves 1973**) — and `benporath2012` says *arbitrarily small* transfers
  suffice, which is a materially cheaper ask than VCG-scale ones.
- **What it cannot say.** Nothing here covers **selective** (per-zip) inflation, which is outside
  `G`. `LENS_GROTHENDIECK` §5b already flags it and `U3-inv` is instructed to state the smallest
  group action that would cover it.
- **Failure mode.** P-G3 is the failure mode: if the `c2·T_z` coupling is material, P-G1 is a
  statement about a model the programme does not run, and quoting it would be worse than not
  having it. **Check P-G3 first, then state P-G1.** Second failure: `green1986`'s NRC may fail on
  the invariant message correspondence, in which case the "strategy-proof by construction" claim
  is void and `deneckere2008` bounds what is still implementable.

### 2.8 **new** — `EG^bal_S`: CEEI with per-agent quantity bands, and what the equilibrium reading survives

The heterogeneous replacement for equal-size districting that `LENS_GROTHENDIECK` descent 2
promised, in the form the A1 charter actually needs.

```
EG^bal_S(δ) = max { Σ_{i∈S} log Σ_z u_i(z) x_{zi} :  Σ_i x_{zi} = 1,  x ≥ 0,
                    (1−δ)·T/k ≤ Σ_z M_z x_{zi} ≤ (1+δ)·T/k  ∀ i∈S }
```

- **Rests on:** **Eisenberg & Gale 1959** (the program), **Hylland & Zeckhauser 1979** (equal
  artificial budgets without money — the origin of CEEI), **Varian 1974** (the envy criterion
  CEEI satisfies, and the proof step that fails here), **Nash 1950** (scale invariance);
  `budish2011` (**the** citation for "exact CEEI fails once the feasible set is combinatorial;
  approximate CEEI with near-equal budgets exists, is EF1 and is strategyproof in large
  markets"), `barman2025market` (a common market value plus subjective valuations — the closest
  published model to `u_i(z) = M_z·w_i(z)`), `barman2023gac` (feasible envy-freeness under
  agent-specific size/budget constraints — the right fairness notion under a band).
- **Assumptions, and whether FRAME §5/§6 meet them.**
  - Concavity, additivity, all goods allocated, equal budgets — **met**, as §2.2.
  - **The band is a constraint on a *second, common* measure `M`, not on the agents' own
    valuations.** Met by construction and it is the structural novelty. `barman2025market` is
    the only published model with this two-measure shape; it does **not** carry a quantity band.
  - Divisibility — not met; `≤ k−1` splits, verified (`U1-cert` P3a), and `LENS_GROMOV` **U15**
    asks whether the extra `2k` band rows raise it to `≤ 2k−1`. That is an optimization/LP-rank
    question and is handed over in §7, **not** answered here.
  - A feasible band exists — **met and measured**: the delivered draw sits at `δ = 0.0078`, so
    `EG^bal_{S₁₃}(δ)` is feasible for every `δ ≥ 0.0078` and the sandwich
    `59.9375 ≤ EG^bal_{S₁₃}(δ) ≤ 60.6974` holds `[measured]`.
- **Does the equilibrium reading survive the bands? — the answer, and it is a qualified yes.**
  Attach `p_z ≥ 0` to coverage and `μ_i^+, μ_i^- ≥ 0` to the upper and lower band rows. The KKT
  conditions give, for each `i ∈ S`, a maximum-bang-per-buck condition against a **personalised**
  price
  ```
  π_i(z) = p_z + ν_i·M_z ,   ν_i = μ_i^+ − μ_i^- ,
  ```
  i.e. rep `i` buys zip `z` only where `u_i(z)/π_i(z)` is maximal, and spends a unit budget.
  `[claim]` So:
  - **What survives:** prices exist, budgets are equal, each agent optimises against prices, and
    the allocation is Pareto-efficient *within the band-feasible set*. It is a competitive
    equilibrium with quotas — the same shape `budish2011` reaches by perturbing budgets instead
    of prices.
  - **What is lost: price anonymity.** `ν_i` differs across agents, so the price vector is no
    longer common. **Varian 1974**'s envy-freeness argument for CEEI runs through the *common*
    price vector (if `i` could afford `j`'s bundle they would have bought it), and it breaks
    exactly here. This is the precise sense in which "balance is the equal-budget condition"
    (`LENS_GROTHENDIECK` descent 2) is **not** the whole story: an *equal-budget* market is
    envy-free; an *equal-quantity* market is not.
  - `ν_i > 0` means rep `i`'s band binds from above — they would buy more opportunity at the
    market price and are prevented. `ν_i < 0` means the lower band binds — they are being
    force-fed opportunity they do not want. Both are informative and both are the sponsor's
    doing.
- **Fairness properties: kept, lost, replaced** `[claim]`, and each is cheap to check.
  | property | at `EG_S` (no band) | at `EG^bal_S(δ)` | citation |
  |---|---|---|---|
  | Pareto optimality | yes, globally | yes, **within the band-feasible set only**; the band costs up to `EG_S − EG^bal_S(δ)` nats of unconstrained welfare | **Eisenberg & Gale 1959** |
  | Envy-freeness (fractional) | yes, via common prices | **lost** — prices are personalised | **Varian 1974** |
  | EF1 (integral) | yes at the MNW optimum | **lost**; replaced by **FEFx** — envy only against band-feasible bundles | **Caragiannis et al. 2019**, `barman2023gac` |
  | Proportionality `u_i(A_i) ≥ u_i(Z)/k` | yes (equal budgets) | **the first casualty** — an agent whose value concentrates on high-`M` zips is capped by the upper band | **Hylland & Zeckhauser 1979**, `budish2011` |
  | Scale invariance in `u_i` | yes | **yes** — the band constrains `x`, not `u` (§2.7 P-G1) | **Nash 1950** |
  The proportionality row is the one to test first, because **proportionality is the property
  FRAME §3's "do not starve anybody" most nearly names**, and the band is the thing that breaks
  it. A two-agent counterexample is immediate: `k = 2`, one agent valuing only a zip carrying 60%
  of `M`; the band forbids giving it to them.
- **What it would produce.** The number a decision actually needs (`U1-cert` §5.3's own words):
  `EG^bal_{S₁₃}(δ)` at the sponsor's `δ`, with its duals; the fairness verdicts above at that
  point; and the statement of what the band cost, in nats and in fairness properties, rather than
  in nats alone.
- **What it cannot say.** Anything about a different roster (§2.10); anything about `M` being
  wrong (§7); anything about integrality beyond the split count (optimization, §7).
- **Failure mode.** (i) If `δ` is loose enough that no band row is tight, `ν_i = 0`, the
  personalised prices collapse to common ones, and this section reduces to §2.2 — which is the
  good case and should be detected rather than assumed. (ii) If a lower band row binds for some
  rep, `EG^bal` may hand a rep opportunity with `u_i` near zero and the log objective
  ill-conditions (`DOMAIN_optimization` §2.2's guard applies). (iii) `barman2025market`'s
  impossibility — SD-EF1 on both the market value and the subjective values is unachievable in
  general — is a *direct contradiction* of any reading in which balance and continuity are the
  same fairness demand. Do not write that reading down.

### 2.9 **new** — the band duals as the balance↔continuity exchange rate: shadow price vs elicited preference

`LENS_GROMOV` **U12 → U14**: the tolerance FRAME §3 calls binding and "never elicited". The
economics content is a distinction the programme has not drawn.

- **Rests on:** **Nash 1950**, **Kalai 1977** (interpersonal comparison is a *choice*, not a
  measurement), **Kalai & Smorodinsky 1975**, **Thomson 1994**, **Thomson 2011**,
  **Moulin 2019** (what to hand a committee), **Roth 2002** (design as engineering: the
  presentational details decide whether a mechanism works), **Hylland & Zeckhauser 1979**;
  `atkinson1970` (the ε vocabulary), `bertsimas2011` (the price of fairness, a priori),
  `echenique2024` (the inequality parameter as the index of one family), `smith2000`,
  `arnold2009` (how the affected population will actually read the answer).
- **The distinction, stated so it can be used.** By the envelope theorem the band multipliers
  give
  ```
  d EG^bal_{S₁₃}(δ) / dδ = (T/k)·Σ_{i∈S} (μ_i^+ + μ_i^-)   [claim]
  ```
  — nats of continuity per unit of band width. That is a **marginal rate of transformation**: a
  fact about the feasible set, computed by the programme, requiring no input from anybody. The
  "exchange rate" FRAME §3 says has never been elicited is a **marginal rate of substitution**: a
  fact about the sponsor's preferences. **They coincide only at the sponsor's own optimum.**
  Computing `μ` therefore does not elicit the sponsor's rate, and it must not be presented as
  though it did. What it does is convert an unanswerable question into an answerable one, exactly
  as `LENS_GROMOV` M11.2 says: not *"how much continuity would you trade for balance?"* but
  *"at δ = 5% the marginal territory-dollar of balance costs X nats of continuity — is that the
  right δ?"*
- **How to put it to the sponsor.** As a **menu, not an elicitation**. Compute
  `EG^bal_{S₁₃}(δ)` on the grid `δ ∈ {0.0078, 0.02, 0.05, 0.10, 0.33}` (`U13`), plot `(δ, V)`
  with the delivered MNW point marked (`DOMAIN_optimization` §2.5's trap-2 discipline), and hand
  over three columns per row: the band, the continuity value in book share, and the fairness
  verdicts of §2.8's table. **Moulin 2019** is the citation for presentability, **Roth 2002** for
  why the presentation is part of the mechanism, and `smith2000` / `arnold2009` for why the
  losing side will read the *procedure* rather than the number. Menu-choice is also the native
  form of a pseudo-market (**Hylland & Zeckhauser 1979**), which is what the sponsor is being
  asked to parameterise.
- **The second knob, and it must be on the same page.** `δ` is on `M`; `ε` is on `g`. The
  measurement says they came apart by 77.6× `[measured]`. A sponsor asked only for `δ` has
  answered a question about territory size and not about what any wholesaler receives. Put both
  on the menu, or the elicitation is incomplete by construction.
- **What it cannot say.** Which point on the menu. And it cannot rescue an ill-posed `M`
  (**A4**): every `μ_i` is a functional of `M`, so a regional bias in the sizing biases the
  exchange rate in the same direction and is undetectable from inside (`VERIFY_U1-cert` §6).
- **Failure mode.** `EG^bal(δ)` is a concave value function; its derivative is set-valued at a
  kink. If the sponsor's `δ` sits at a kink, quoting one shadow price is wrong — report the
  left and right derivatives (the sub-differential interval). Cheap to detect, and the kinks are
  interesting in their own right: a kink is where a large zip becomes movable (FRAME §6: zip
  10017 alone is ~14% of a territory).

### 2.10 **new** — roster selection as a 13-seat, 111-bidder market without transfers

`LENS_GROMOV` M13.1 and **U16/U17/U19**; the caller's question *is there a known mechanism?*

- **Rests on:** `benporath2014` (a principal allocates an indivisible object among agents who
  privately know the principal's value of giving it to them; **no transfers**; verification at a
  cost; the optimum is a **favoured-agent mechanism** — fix `i*` and threshold `v*`, if all
  others report below `v*` then `i*` gets it unchecked, otherwise the highest reporter is checked
  and gets it only if confirmed), `mylovanov2017` (ex-post verification with bounded penalties —
  and our only available penalty *is* losing the seat), `benporath2019` (implementable without
  commitment — which matters because FRAME §2 says leadership signs, and a channel that must
  pre-commit to an audit rule it will not want to follow is not implementable here),
  `milgrom1981` (unravelling: a credible audit threat plus sceptical discounting of unaudited
  claims gets most of the way without universal audit), `caragiannis2012` (probabilistic
  verification — the sampled-audit version); **Gale & Shapley 1962**, **Roth 1982**,
  **Roth 1984**, **Roth & Sotomayor 1990** (the college-admissions structure and its incentive
  limits); **Shapley & Shubik 1971**, **Shapley & Scarf 1974**, **Kelso & Crawford 1982**
  (checked and ruled out, below); **Hylland & Zeckhauser 1979**, **Mariotti 1998** (the tie
  problem); **Aumann 1987** (a third party sending correlated recommendations — the sponsor's
  actual position).
- **Is there a known mechanism? — yes for one seat, and the 13-seat version is the named gap.**
  `benporath2014` is *the* model of this problem: indivisible allocation, no transfers, private
  information about the principal's value, costly verification. `LIT` §4 already records that the
  multi-object extension is the gap. So the honest answer to the sponsor is: **the one-seat
  problem is solved and the solution is a favoured-agent-with-audit-threshold rule; the 13-seat
  problem is not, and the practical route is `milgrom1981` unravelling plus `caragiannis2012`
  sampled verification.** That is a design, not a yes/no, and it replaces ★2's binary framing of
  U11.
- **What is *not* the right model, checked rather than assumed.**
  - **Shapley & Shubik 1971** (assignment game): core = competitive price vectors, but it needs
    **transferable utility**. FRAME §7 puts compensation out of scope, so there is no price on a
    seat and the assignment-game core is unavailable. *Not met.*
  - **Shapley & Scarf 1974** / top-trading-cycles: needs initial endowments. This is greenfield —
    no wholesaler holds a national-channel seat. *Not met.*
  - **Kelso & Crawford 1982** gross substitutes: the condition under which a decentralised
    salary/price process clears. Our reps' preferences over seats are **aligned** (§2.4), which
    is vertical differentiation, the polar opposite of the horizontal sorting gross substitutes
    is designed for. *Not the right check; note and move on.*
  - **Gale & Shapley 1962** with quota 13 **is** the right structure, and **Roth 1982** bounds
    what it can give: deferred acceptance is strategy-proof for the proposing side only. If the
    sponsor ever runs an actual process, propose from the wholesalers' side.
- **Premium nearly determined by book disjointness — and what that implies.** Measured: 83
  contested zips among the 13 (6.12% of `M`), greedy attains the `P₁₃` MILP optimum, and
  `P₀ = P*(A)` exactly on seed 3 `[measured]`. So the selection rule is, to first order, *pick
  the 13 largest (near-disjoint) books*. Two consequences pull in opposite directions.
  - **Defensibility (good):** §2.5's Shapley value degenerates to own-book, so "why him and not
    me" has a one-number answer that **Young 1985** axiomatically defends.
  - **Manipulability (bad):** a rule that is nearly "rank by reported book magnitude" is the most
    inflatable rule available, and §2.7 P-G2 says selection is exactly where `G`-invariance
    fails. **The two findings are the same finding.** Audited magnitudes are therefore not a
    precaution here; they are load-bearing on the only part of A1 that is not already invariant.
- **The Nash-tie margin `U17` as a market fact.** The best alternative Nash optimum is `1.37e-2`
  nats away on seed 3 and **`8.1e-3` on seed 9** — 1.6× the tier-2 floor `[measured]`. So the
  mechanism's output is not unique at the programme's own tolerance, and the selection among
  near-optima is currently made by an arbitrary tie-break inside the Hungarian solver. Economic
  theory has exactly two honest responses:
  1. **Mariotti 1998** — on a finite alternative set the classical axioms deliver a *lottery*,
    not a point; **Hylland & Zeckhauser 1979** is the mechanism that embraces it (ex-ante
    efficient random assignment with artificial budgets).
  2. Name the tie-break as **policy** and disclose it, keeping determinism.
  Recommendation: **(2), with disclosure and with the near-optimal roster set reported alongside
  `S₁₃`.** FRAME §2's low-reversibility row and `smith2000`'s justice finding both say a lottery
  over people's careers will not survive contact with the affected population, however defensible
  it is ex ante. This is D7.
- **What it cannot say.** Whether the sponsor will audit; whether any of the 98 will actually
  object. And it must not drift into compensation (FRAME §7).
- **Failure mode.** `U16` may find that the near-optimal roster set is large; then the tie-break
  is doing more work than any argument in this section, and the report must lead with that rather
  than with `S₁₃`. Second: `benporath2014`'s favoured-agent structure has an obvious optics
  problem in a sales organisation ("who is the favoured agent?"); the model is right and the
  presentation is a genuine risk — `Roth 2002`'s point exactly.

---

## 3. Solution concept and how it is verified

**An answer, in this domain's terms, is a coverage `(π, σ)` together with these statements.**
Statements 1–5 keep [pred]'s numbering and subjects; each has moved.

| # | statement | status after measurement | verified by |
|---|---|---|---|
| 1 | **Efficiency with a gap.** `V(π,σ) ≥ EG^bal_S(δ) − ε` at the sponsor's band, with `ε` the duality gap and the prices reported. | **Changed:** the bound must be the *band-constrained* one. The unconstrained version is done (`0.760` nats, `U1-cert`) and is an upper bound on it. | `math-verify` on `V ≤ EG^bal_S(δ)` (`LENS_GROMOV` M8 argues `U1-cert` P1's proof goes through verbatim with the band added — check it, do not assume it); `code-verify` on the solve, the bracket and the rounding gap (**U18**). |
| 2 | **Fairness, named.** Not "EF1 or a stated failure" but the §2.8 table: PO within the band, FEFx rather than EF1, and an explicit proportionality verdict. | **Changed:** EF1 is the wrong test under a band; `barman2023gac` supplies the right one. | `math-verify` on which properties survive quantity constraints (§2.8's `[claim]` table, with the two-agent proportionality counterexample); `code-verify` on the `13 × 13` matrix. The matrix **is** FRAME §3.4. |
| 3 | **Criterion, chosen not inherited.** The delivered map is the optimum of a named `(δ, ε)` pair the sponsor selected. | **Changed:** two knobs, not one; and the menu (§2.9) is the deliverable, not three maps. | Not verifiable by an agent — a sponsor decision. The deliverable is the frontier with the MNW point marked. |
| 4 | **Stability of the roster,** with its margin, and its `δ`-dependence. | **Changed:** 169 comparisons (`U2-stab` P3.3), and the verdict is a function of `δ` (§2.4). | `code-verify`: enumeration over the `13 × 13` submatrix, plus the same at two or three `δ` on the frontier. Cheap and decisive. |
| 5 | **Selection defensibility.** The exact Shapley ranking (`littlechild1973` + additivity), the least-core value rather than a binary core verdict, and the near-optimal roster set with the tie margin. | **Changed:** cheaper (no sampler), and `U17` adds the margin as a required output. | `math-verify` on `f` being a sum of airport games and on `deng1999`'s integrality test being the right one; `code-verify` on the closed form against a 5-player brute force. |
| **6** | **new — the price of the band.** The sponsor's chosen `δ` reported with `dEG^bal/dδ` (or its sub-differential interval) and with what the band cost in fairness properties, not only in nats. | new | `math-verify` on the envelope identity and on the personalised-price KKT reading (§2.8, §2.9 `[claim]`s); `code-verify` on the duals at each grid `δ`. |
| **7** | **new — the invariance split.** A statement of where reported book may be read (the draw, at fixed roster: `G`-invariant by P-G1) and where audited magnitude is required (selection: not invariant, P-G2), with P-G3's affine-coupling check reported. | new | `math-verify` on P-G1/P-G2/P-G3; `code-verify` on the magnitude of the `c2·T_z` coupling on the export. |

**What verification must *not* accept.** A bound stated only in nats (`LENS_GROMOV` M13.6, FRAME
§10 Q7). An EF1 claim on a band-constrained allocation. Any EF1/PO claim while **A2** is open.
Any core/Shapley statement applied to `V` rather than to the surplus game `f` (§2.5's TU caveat).
A bare `M(F)` or a bare split-set number without the vertex caveat (`MODEL_U1-cert` §5.9). Any
`S₁₃`-conditional number quoted without the `U17` tie margin. **And, new: any invocation of
★`fotakis2014` as forbidding a book-reading draw, until §2.7(a)'s scope correction is written.**

---

## 4. Recommended path, with the decision points

**The through-line, restated after measurement.** [pred] said economic theory's contribution is
not a better solver but the observation that three of FRAME's open items are one item — the
unnamed welfare criterion. That survives, and measurement adds a second through-line that is
sharper and more urgent: **A1's remaining value is small (≤ 0.76 nats at this roster, ≤ 0.043
from re-rostering) and its remaining risk is concentrated in one place — the selection step,
which is the only part of the formulation that is not invariant to book inflation.** Order
everything so the cheap audits land before the sponsor is asked anything, and so the invariance
split is settled before any book-reading draw is proposed for deployment.

**Step 1 — audits on the delivered artifact (hours; no new theory; no sponsor input).**
In order: `(a)` the `13 × 13` matrix with three verdicts — EF1, FEFx, proportionality (§2.1,
§2.8); `(b)` the blocking-pair enumeration over the `13 × 13` submatrix, with the greedy-vs-
Hungarian comparison and the tie margin (§2.4); `(c)` the exact Shapley ranking and the least-core
value (§2.5, §2.6). All three are independent and parallel.
> **D1 (kept, re-scoped).** [pred] framed D1 as "if EF1 fails, the certified claim loses its last
> fairness content". **Half of it is closed:** `ρ = 0` is established, so the `ρ` branch is dead.
> The live half is **A2 / `d = 0`**. And the new content is that a *large* envy verdict is now the
> prior (60.65% `g`-spread), so D1's real question is **which fairness notion the programme will
> report** — plain EF1 (which the band makes inapplicable) or FEFx (which it does not). Decide
> that before running (a), or the number will be misread.

**Step 2 — the menu, not the criterion (§2.9).** Once `U13`'s frontier exists
(`DOMAIN_optimization` owns the solve), build the sponsor-facing menu: `(δ, V, book-share, μ,
fairness verdicts)` per row, with the MNW point marked.
> **D2 (kept, sharpened).** [pred]: *which of three criteria is the channel's standard?*
> Now: **which `(δ, ε)`?** — two knobs, and the evidence that they are two is the 77.6× ratio.
> `bertsimas2011` gives the a-priori magnitude of the trade before the menu is computed; if the
> menu turns out flat (`LENS_GROMOV` M12's softness test), record that D2 does not matter and
> close **U12** for free. **★4 is the ask, and it is now a menu choice rather than an
> elicitation.**

**Step 3 — the band-constrained bound and its duals (§2.8, §2.9).** This replaces [pred]'s step 3
entirely.
> **D3 (retired and re-issued).** [pred]'s D3 — *is the EG bound decorative because of the
> integrality gap?* — is **answered NO** and withdrawn (`U1-cert` P3; `≤ k−1` splits, small
> measured mass). The re-issued **D3** is: **does the equilibrium reading survive the band well
> enough to be quoted to a sponsor?** Concretely, is the personalised-price KKT reading of §2.8
> correct, and is proportionality lost at the sponsor's `δ`? If proportionality survives, the
> band is cheap in fairness as well as in nats and the menu is easy. If it does not, FRAME §3's
> "do not starve anybody" and FRAME §3.1's balance requirement are in direct conflict and the
> sponsor must be told.

**Step 4 — selection defensibility and the claims framing (§2.5, §2.6, §2.10).**
> **D4 (kept, cheapened).** [pred]: if the Shapley ranking disagrees with the welfare-optimal
> roster on more than a seat or two, leadership must know before announcement. Still right, and
> now cheap (closed form, no sampler) — and now with a magnitude to put beside it: the whole
> collective claim of the unselected is **0.92% of book / 0.043 nats** `[measured]`. Report both
> or the disagreement will be read as larger than it is.

**Step 5 — the incentive question, restructured around the invariance split (§2.7).**
> **D5 (kept, and it is now two decisions).** [pred] reduced FRAME §9's blocking item to **U11**
> ("is audited book available at zip × wholesaler grain?"). That stands as **★2**. What P-G1/P-G2
> add is that the answer is only needed **for selection**, not for the draw: at fixed roster the
> map and prices are `G`-invariant. So D5 splits:
> **D5a** — accept the invariance split as the design rule (audited magnitudes for selection,
> reported profiles for the draw), conditional on P-G3's coupling check and on `green1986`'s NRC
> (`U3-inv`)? **D5b** — if audited data is unavailable, is `benporath2014`/`milgrom1981`'s
> audit-threat design (verify only the top reporters, discount unaudited claims) acceptable to
> the sponsor? Also state, in one sentence: VCG would solve this outright and is excluded only by
> FRAME §7's no-transfers scope, and `benporath2012` says *arbitrarily small* transfers suffice.

**Step 6 — new. Correct the ★`fotakis2014` over-read (§2.7a).** A documentation fix in
`RESEARCH_FINDINGS` §9-G, `REVIEW_GROMOV`, `CHANNEL.md` §0 and `APPROACHES.md`, plus one sentence
in `MODEL.md`. Free, blocks nothing, and it removes a false impossibility that is currently doing
argumentative work in four files.
> **D6 — new.** Does the programme accept that the "books enter at stage 2 only" invariant rests
> on Gibbard–Satterthwaite generically rather than on ★`fotakis2014` specifically? If yes, the
> invariant is *weaker* than advertised and the A1 formulation is not forbidden by it — which is
> what `DOMAIN_optimization` §8 Q7 already argues from the other side.

**Step 7 — new. Decide the tie-break policy (§2.10, `U17`).**
> **D7 — new.** `S₁₃` is not unique at the programme's own floor (8.1e-3 nats on seed 9). Choose:
> (i) name and disclose the tie-break and report the near-optimal roster set alongside, or
> (ii) randomise (**Hylland & Zeckhauser 1979**, **Mariotti 1998**). Recommend (i) on FRAME §2
> and `smith2000` grounds. Either way the margin must be reported with every `S₁₃`-conditional
> number, which is `LENS_GROMOV` **U17**'s instruction.

**Explicitly deferred.** Compensation, transition packages, the residual channels (FRAME §7).
§2.6 stays one paragraph plus two numbers.

**Sequencing.** Steps 1, 4, 6 and 7 are independent and need nothing from anybody. Step 2 needs
`U13` from optimization. Step 3 needs `U13`'s duals. Step 5 needs ★2 or the sponsor.

---

## 5. Numbers to compute first (cheap, decisive)

N1–N6 keep [pred]'s numbering and subjects, with status. N7–N11 are new and are cut for the A1
charter. Every one is hours on the instance, which ★6 has lifted in full (FRAME §0).

| # | number | status | decides | overturns if |
|---|---|---|---|---|
| N1 | The `13 × 13` matrix `u_i(A_j)` with **three** verdicts: EF1, FEFx w.r.t. the band, proportionality | **changed** — the verdict set is new (§2.8) | FRAME §3.4; §3 statement 2 | a wide EF1 failure that is *not* an FEFx failure ⇒ the programme has been reporting the wrong fairness notion, not an unfair map |
| N2 | Is `ρ = 0`, and does **A2** force `d > 0`? | **half retired** — `ρ = 0` established (`VERIFY_U2-stab` row 1). The `d` half is open and is ★1 | whether N1 carries **Caragiannis et al. 2019** | `d > 0` ⇒ re-cite to **Mariotti 1998** / **Xu & Yoshihara 2005**; expect a lottery (`LIT` absence A4: no weaker EF1 theorem exists) |
| N3 | Blocking-pair count — **now `13 × 13` = 169, not `13 × 111`** | **changed** (`U2-stab` P3.3) | roster stability; FRAME §2's reversibility row | any blocking pair ⇒ `Roth 1984` / `niederle2009` unravelling applies to the announcement. Report the *gain* of each block, not only the count |
| N4 | The criterion maps and the `M` they move | **changed** — no longer three maps; the `ε = 0` map is FRAME §10 Q8's transportation LP and belongs to optimization. Economic theory computes only the **menu rows** (§2.9) | D2 | the menu is flat within `5e-3` nats ⇒ FRAME §3's binding tolerance is not binding and **U12** closes for free |
| N5 | Core test on the surplus game `f` | **changed** — use `deng1999` integrality, not the balancedness LP; and report the **least core** (`kern2003`), not a binary verdict | whether any coalition-proof selection exists | the least-core excess is *large* ⇒ §2.6's claims framing is the honest one. Small ⇒ report the number and move on. Scope with `goemans2004` |
| N6 | Exact Shapley value of all 111 on `f`, top-13 vs delivered roster | **kept, cheapened** — `littlechild1973` + additivity, `O(#zips · n log n)`, no sampler | D4 | large disagreement ⇒ the welfare-optimal roster is not the attribution-defensible one. Expect *small* disagreement: books are near-disjoint, so `φ_i(f) ≈ S_i(Z)` |
| **N7** | **new** — `EG^bal_{S₁₃}(δ)` and its duals `μ_i^±` on `δ ∈ {0.0078, 0.02, 0.05, 0.10, 0.33}`, with `ν_i = μ_i^+ − μ_i^-` per rep | new; this is `LENS_GROMOV` **U13/U14** and the single most decisive number in the file | D2, D3, §3 statements 1 and 6 | `EG^bal(δ) − V ≤ 5e-3` for every plausible `δ` ⇒ **the premium is soft inside the band, A1's redraw is decorative, and the charter hands the problem to A5** |
| **N8** | **new** — at each `δ`: the number of reps whose band binds, and the sign of `ν_i` | new | whether the equilibrium reading is "CEEI" (all `ν_i = 0`) or "CEEI with personalised prices" (§2.8) | all `ν_i = 0` at the sponsor's `δ` ⇒ §2.8 collapses to §2.2, price anonymity is restored, and **Varian 1974**'s envy argument is back in force. This is the *good* case and it is one read of the dual vector |
| **N9** | **new** — the proportionality gap `u_i(A_{σ(i)}) − u_i(Z)/k` per selected rep, at the delivered draw and at each `δ` | new; §2.8's first-casualty row | whether FRAME §3's "do not starve anybody" is satisfied or is in conflict with the balance requirement | any rep below proportionality at the sponsor's `δ` ⇒ the two stated business goals conflict, and the sponsor must be told before signing |
| **N10** | **new** — the size of the `c2·T_z` coupling: how far `u_i` is from homogeneous in `S_i`, i.e. P-G3 | new; §2.7(c) | whether P-G1's `G`-invariance of the map is a statement about the model the programme runs, or only about a nearby one | coupling material ⇒ P-G1 must not be quoted for the current `u_i`, and the design fix (normalised profile × audited magnitude) becomes a *requirement*, not an option |
| **N11** | **new** — the near-optimal roster set: every `S` within `5e-3` and within `1.5e-2` nats of `S₁₃`, and its cardinality | new; `LENS_GROMOV` **U16/U17** | D7, and every `S₁₃`-conditional number in FRAME §6 | cardinality is large ⇒ the tie-break, not the objective, is choosing the roster, and the report must lead with that |

**Not on this list, deliberately.** The frontier *solve* itself (`U13`), the rounding gap
(`U18`), the split-count-under-bands question (`U15`) and the `max_S EG^bal_S` bound (`U19`)
are optimization objects; economic theory consumes their duals and their values. `DOMAIN_optimization`
owns them and this file does not restate them.

---

## 6. Search brief for `lit-search`

**What is already done, and must be deduplicated against.** `docs/LIT_economic-theory.md` ran
[pred]'s six questions in full on 2026-09-02 (46 entries, all DOIs resolved, absence ledger A1–A7,
39 conceptual queries + 30 resolution calls). **Do not re-run Q1–Q6 of that brief.** Four of them
are closed: Q3 (aligned-preference stability) by `eeckhout2000` + `echenique2024`; Q5 (the
coverage game) by `littlechild1973` + `deng1999`; Q6 (territory design as a mechanism) by
`lal1986` + absence A6; and Q1's fibration half by `atkinson1970`. Deduplicate against
`LIT_economic-theory.bib`, `docs/RESEARCH_FINDINGS.md`, `docs/RESEARCH_ADDITIONS.bib`,
`docs/channel_note/references.bib` and `~/resources/economic-theory/FOUNDATIONS.md`.

**Questions, in priority order. All six are new; none was asked before measurement.**

1. **Fisher markets / Eisenberg–Gale with per-agent *quantity* constraints on a second, common
   measure.** Precisely: `max Σ_i log(u_i·x_i)` over an assignment polytope with
   `L ≤ Σ_z M_z x_{zi} ≤ U` per agent, where `M` is a common measure distinct from every `u_i`.
   Is this a named object (constrained CEEI; Fisher market with quotas/capacities; EG with side
   constraints; "market equilibrium with quantity rationing")? **Do the duals retain a price
   reading, and is the personalised-price form `p_z + ν_i M_z` of §2.8 the known one?** Which of
   {PO, EF, EF1, proportionality} survive, and is there a published counterexample to
   proportionality under a quantity band? *(Bears on §2.8, §3 statements 1/2/6, D3, N7–N9. This is
   the load-bearing question in the brief; nearest known anchors are `budish2011`,
   `barman2025market`, `barman2023gac`, **Hylland & Zeckhauser 1979**.)*
2. **The shadow price of a fairness constraint as a sponsor-facing object.** Is there a
   literature — welfare economics, operations, public economics — that treats the multiplier on
   an equity constraint as the quantity to *report to a decision-maker* rather than to optimise
   away, and that distinguishes it from an elicited marginal rate of substitution? Keywords:
   "price of fairness" with duals, "equity constraint shadow price", "constrained welfare
   maximisation multiplier interpretation", menu-based preference elicitation for social
   planners. *(Bears on §2.9, D2, ★4. Anchors: `bertsimas2011`, **Kalai 1977**, **Moulin 2019**,
   **Roth 2002**.)*
3. **Multi-object allocation with costly or partial verification and no transfers.** `LIT` §4
   established that `benporath2014` solves the *single*-object case and named the multi-object
   extension as the gap. Has it been closed since — `k` identical or heterogeneous objects,
   `n ≫ k` agents, no transfers, costly/ex-post verification, bounded penalties? Include the
   sampled/probabilistic variants (`caragiannis2012`) and any application to internal
   allocation of positions within a firm. *(Bears on §2.10, D5a/D5b, ★2. Anchors:
   `benporath2014`, `mylovanov2017`, `benporath2019`, `milgrom1981`, `green1986`.)*
4. **Scale invariance of Nash welfare as a manipulation-resistance property, and where it
   breaks.** §2.7's P-G1/P-G2 say the EG *allocation and prices* are invariant to per-agent
   valuation rescaling while the *selection* of which agents participate is not. Is that split
   stated anywhere — "Nash welfare is invariant to individual utility scaling but agent selection
   under Nash welfare is manipulable by scaling"? And is there a treatment of an objective that
   is *affine but not homogeneous* in the reported type (our `c2·T_z` coupling, P-G3)? Keywords:
   scale invariance, unit invariance, homogeneity of valuations, participation manipulation,
   Nash welfare with agent selection. *(Bears on §2.7(c), §3 statement 7, D5a, N10. Anchors:
   **Nash 1950**, **Eisenberg & Gale 1959**, **Crawford & Varian 1979**, `green1986`.)*
5. **Stability of a matching as a function of a capacity/size constraint on the objects.** §2.4
   claims `[claim]` that tightening a size band on the *territories* makes the induced market
   horizontally differentiated (fit-driven, small blocks) and loosening it makes it vertically
   differentiated (size-driven, large blocks). Is the horizontal/vertical transition indexed by a
   capacity band studied in matching theory, and does anything quantify the *magnitude* of a
   blocking pair's gain as a function of the common component `B_j`? *(Bears on §2.4, N3, and on
   whether D2's `δ` and ★3's stability question are one decision. Anchors: `echenique2024`,
   `eeckhout2000`, `niederle2009`, **Kelso & Crawford 1982**, **Roth & Sotomayor 1990**.)*
6. **Reporting non-unique optima of an allocation mechanism.** `U17`: `S₁₃` is not unique at the
   programme's own tolerance. Is there guidance — market design, social choice, or applied
   practice — on whether to disclose a tie-break, report the near-optimal set, or randomise, when
   the allocation is over people's assignments and is low-reversibility? Include the ex-ante /
   ex-post fairness ("best of both worlds") thread that `LIT`'s time-box left unsearched.
   *(Bears on §2.10, D7, N11. Anchors: **Hylland & Zeckhauser 1979**, **Mariotti 1998**,
   **Aumann 1987**, `smith2000`, `arnold2009`.)*

**Literatures to sweep.**
*Market equilibrium / fair division:* EC, WINE, SAGT, AAMAS, IJCAI, AAAI, ACM TEAC, GEB, JET,
Math. Programming, SICOMP — `Fisher market`, `Eisenberg-Gale`, `competitive equilibrium equal
incomes`, `constrained market equilibrium`, `quantity rationing`, `capacitated fair division`,
`feasible envy-freeness`, `proportionality under constraints`. Anchors from FOUNDATIONS:
**Eisenberg & Gale 1959**, **Hylland & Zeckhauser 1979**, **Varian 1974**,
**Caragiannis et al. 2019**, **Nash 1950**, **Moulin 2019**, **Thomson 2011**.
*Welfare economics / operations:* OR, Management Science, JPubE, SCW — `price of fairness`,
`equity-efficiency trade-off duals`, `constrained social welfare multiplier`. Anchors:
**Kalai 1977**, **Kalai & Smorodinsky 1975**, **Thomson 1994**.
*Mechanism design with evidence / verification:* Econometrica, AER, JET, GEB, TEAC — `costly
verification`, `multiple objects`, `evidence`, `partial verifiability`, `favored agent`. Anchors:
**Myerson 1979**, **Maskin 1999**, **Gibbard 1973**, **Satterthwaite 1975**,
**Vickrey 1961** / **Clarke 1971** / **Groves 1973**, **Crawford & Varian 1979**.
*Matching:* Econometrica, JPE, AER, MOR, GEB — `aligned preferences`, `common ranking`,
`capacity constraints and stability`, `vertical vs horizontal differentiation in matching`.
Anchors: **Gale & Shapley 1962**, **Roth 1982**, **Roth 1984**, **Roth & Sotomayor 1990**,
**Kelso & Crawford 1982**, **Shapley & Shubik 1971**, **Shapley & Scarf 1974**.
*Cooperative games:* IJGT, GEB, MOR, TCS — `submodular game core`, `least core`, `nucleolus of a
covering game` (the thread `LIT` explicitly time-boxed out). Anchors: **Gillies 1959**,
**Shapley 1967**, **Shapley 1953**, **Young 1985**, **Schmeidler 1969**,
**Aumann & Maschler 1985**, **Shapley & Shubik 1969**, **Myerson 1977**.

**Deliverable.** Entries as `citation · venue/year · DOI · 2–4 sentence annotation naming which
§2 method or §4 decision point it bears on · tag ∈ {foundation, frontier,
contradicts-or-sharpens, tool-we-lack}`. Plus a **five-paper shortlist** — the five that would
most change §4 if read this week. **Every absence claim must state where it was looked for**
(venues, keywords, citation-graph walks). Two absences from the 2026-09-02 ledger should be
re-tested against question 1, because the band-constrained object did not exist when they were
written: **A2** (no continuous heterogeneity modulus) and **A3** (no MNW with a participation
margin and a boundary axiom).

**Note for the searcher.** Write to `docs/LIT_economic-theory.md` as a **new dated section**,
not by rewriting the 2026-09-02 content — that file is inherited unchanged by charter and its
existing entries are cited by `BRIEF.md`, `docs/units/*.md` and this file by key.

---

## 7. Out of this domain — hand to

| item | to | why |
|---|---|---|
| The `EG^bal_S(δ)` solve itself, the parametric frontier, the rounding gap (**U18**), and whether the band raises the split count to `≤ 2k−1` (**U15**) | **optimization** | Algorithms, LP rank and duality machinery. §2.8/§2.9 supply the interpretation of the duals; the solve is not ours. `DOMAIN_optimization` owns the exponential-cone / outer-approximation question. |
| `max_S EG^bal_S` and whether `S ↦ EG^bal_S` is submodular or near-modular (**U19**) | **optimization**, then back here | The *bound* is optimization's; §2.5 reads the same function as a cooperative game and needs the structural answer before `deng1999`/`kern2003` can be applied to it. `littlechild1973`'s closed form does **not** transfer to it — state that in the hand-off. |
| The `τ`-homotopy modulus (GROTH OQ1) | **optimization / applied-math** | Superseded in priority by `EG^bal(δ)` (`LENS_GROMOV` M8) but not answered. |
| Displacement as a metric and as a certificate (GROTH §5a, OQ5; `DOMAIN_optimization` §2.4, §8 Q3) | **optimization / applied-math** | No economic-theory counterpart, per §1 — unchanged from [pred]. Still the highest-leverage unknown for FRAME §3.5. |
| The tier-2 noise floor at `n=1,229, k=13` (**U6**), and whether an `8.1e-3`-nat margin is inside or outside the noise (**U17**) | **econometrics / data-science** | A measurement question about an estimator's noise. `U17` makes it newly urgent: the tie-break question (D7) is only real if `8.1e-3` exceeds the noise. |
| Regional bias in the sizing estimate `M` (**A4**, **U5**) | **econometrics** | **Still the highest-value hand-off on this table**, and `VERIFY_U1-cert` §6 now confirms why: a regional bias shifts the certificate, the prices, the band multipliers and the thing they certify **together**, and is undetectable from inside. It silently invalidates §2.3's interpersonal comparability, §2.8's bands and §2.9's exchange rate at once. |
| Shapley-value estimation over 111 players | **retired — nobody** | `littlechild1973` + additivity gives the exact value in `O(#zips · n log n)`. [pred]'s hand-off to statistics is struck. Re-open **only** if the characteristic function is redefined as `S ↦ max EG^bal_S`, in which case `castro2009` / `castro2017` apply and each sample costs one EG solve. |
| The "two supports" / full-ZCTA-graph question | **geometry / optimization**, out of scope (FRAME §7) | Unchanged. |
| Compensation, quota design, transition packages | **nobody — FRAME §7** | Noted only because §2.7 and §2.10 touch it: the no-transfers scope is what creates the incentive impossibility, `benporath2012` says *arbitrarily small* transfers suffice, and only leadership can reverse the scope. |

---

## 8. Open questions (inputs to `/research-plan`)

Q1–Q8 keep [pred]'s numbering; Q9–Q12 are new.

1. **Is the disagreement point zero? (A2 / ★1.)** **Unchanged and still open** — unconfirmed
   since 2026-08-31. It decides whether **Caragiannis et al. 2019** applies at all, and `LIT`
   absence A4 records that if `d > 0` there is no weaker EF1 theorem to fall back on, only a
   lottery. *(User → sponsor. One question.)*
2. **Which welfare criterion — now, which `(δ, ε)`? (§2.3, §2.9, D2, ★4.)** **Changed:** two
   knobs, and the menu (§2.9) is the ask rather than an elicitation. The measured 77.6× gap
   between `M`-spread and `g`-spread is the evidence that one knob will not do.
   *(User → sponsor, after N7 shows whether the menu is flat.)*
3. **Is audited system-of-record book available at zip × wholesaler grain? (★2 / U11.)**
   **Changed — smaller.** P-G1/P-G2 say it is needed **only for selection**; the draw at fixed
   roster is `G`-invariant. And `benporath2014`/`milgrom1981`-style audit-threat designs mean the
   answer need not be all-or-nothing. *(User.)*
4. **Should stability be a hard requirement on the roster? (★3.)** **Changed:** `U2-stab`
   established the question is live and decidable in 169 comparisons, and §2.4 adds that the
   answer depends on `δ` — so ★3 and ★4 may be one decision, not two. *(User → sponsor, gated on
   N3.)*
5. **Does the core of the selection game exist, and does the programme want to know? (★5.)**
   **Changed — de-escalated.** With near-disjoint books the least-core excess should be small, so
   the politically awkward sentence ("no selection is coalition-proof") comes with a small number
   attached. Report the least core, not the binary. *(User.)*
6. **Is `ρ = 0`?** **CLOSED — yes.** `VERIFY_U2-stab` row 1: `ρ` appears nowhere in
   `td/channel.py`. Recorded so the question is not asked a third time.
7. **Does a `G`-invariant drawing retain enough premium to be worth having? (GROTH OQ4.)**
   **Changed, and mostly answered by P-G1:** at fixed roster it retains *all* of it, because the
   map is invariant. The residual is P-G3's coupling (N10) and the selection step (P-G2). What
   remains open is the *selection* version of the question: how much premium is lost by selecting
   on audited magnitudes rather than reported ones — which needs ★2. *(Programme, then user.)*
8. **Does "do not starve anybody" mean the nucleolus?** **Changed — sharpened into a testable
   alternative.** §2.8 says the property that phrase most nearly names is **proportionality**,
   and the band is what breaks it (N9). So the sponsor question is now two: *is the floor a
   proportional share of one's own valuation (an EG property), or the minimised loudest complaint
   (**Schmeidler 1969**)?* One sentence, and they are different programmes.
9. **new — Does the equilibrium reading survive the band well enough to quote? (D3.)** §2.8's
   personalised-price KKT reading and its fairness table are `[claim]`s. If §6 question 1 returns
   the object under a name, this is a citation; if not, it is a `math-verify` unit. *(Programme.)*
10. **new — Is the `c2·T_z` coupling material? (P-G3, N10.)** Gates whether P-G1 may be quoted
    about the model the programme actually runs. A programme fact, hours of work, and it decides
    whether the homogeneous redefinition of `u_i` (normalised profile × audited magnitude) is an
    option or a requirement. *(Programme.)*
11. **new — Does the programme accept the ★`fotakis2014` scope correction? (D6.)** Four files
    currently carry an impossibility that, on inspection, has hypotheses (anonymity; reported
    locations) the A1 formulation does not satisfy. Correcting it weakens the "books enter at
    stage 2 only" invariant to a generic Gibbard–Satterthwaite argument — which is honest, and
    which removes a false blocker from A1. *(Programme, then user, because it changes a settled
    item's stated reason.)*
12. **new — What is the tie-break policy? (D7, U17.)** `S₁₃` is not unique at `5e-3` nats.
    Disclose the tie-break and report the near-optimal set, or randomise. Recommend the former on
    FRAME §2 and `smith2000` grounds, but it is a decision and it must be made *before* a roster
    is announced, not after someone asks. *(User, on programme's evidence — N11 and U6.)*
