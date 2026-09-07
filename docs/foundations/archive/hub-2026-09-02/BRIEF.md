# Research brief — the national channel territory problem

> **Hub copy, restored 2026-09-03 from `a4eb488`.** This is the neutral 2026-09-02 version every track starts from. The instance has since been measured — read `docs/FRAME.md` §6's 2026-09-03 rows and `docs/APPROACHES.md` §0's "what every track inherits" before using the numbers here. The A1 track's re-run of this file, with the measurements folded in, is at `docs/tracks/A1/BRIEF.md`.

**Date:** 2026-09-02 · **Framework:** 0.1-dev ·
**Reads:** `docs/FRAME.md`, `docs/LENS_GROMOV.md`, `docs/LENS_GROTHENDIECK.md`,
`docs/DOMAIN_optimization.md`, `docs/DOMAIN_economic-theory.md`, `docs/LIT_economic-theory.md`,
`docs/LIT_economic-theory.bib` · **Supersedes:** none

> **Two gaps to declare before §1.**
>
> **(a) One domain hand-off has no `DOMAIN_*.md`.** `DOMAIN_optimization.md` §7 and
> `DOMAIN_economic-theory.md` §7 both route **U6** (the tier-2 noise floor at `n=1,229, k=13`)
> and **U5 / A4** (regional bias in the sizing estimate `M`) to **econometrics / data-science**,
> and the full-ZCTA-graph question to **applied-math / geometry**. Neither domain has been
> planned and neither has a seeded `FOUNDATIONS.md` (only `optimization` and `economic-theory`
> are seeded). Those units are **not cut** here. U5 is the more serious of the two:
> `DOMAIN_economic-theory.md` §7 calls it the highest-value hand-off on its table because a
> regional bias in `M` invalidates every certificate silently. **Recommend running `/domain
> econometrics` before wave 2** — it is the only route to U5 and U6.
>
> **(b) `docs/LIT_optimization.md` does not exist.** `DOMAIN_optimization.md` §6 wrote a
> nine-question search brief and it has never been run, while economic-theory's *has* (and
> overturned three of its own domain plan's items — `LIT_economic-theory.md` §0). Three
> load-bearing claims in the optimization plan are explicitly marked *"not in FOUNDATIONS, must
> be sourced (§6) or proved"* (`DOMAIN_optimization.md` §2.2, §2.4). **U0 below runs it, in
> parallel with wave 1, and it gates wave 2.**

---

## 1. The problem in five sentences (from FRAME §1–3)

A new "national" channel is being stood up by carving the two largest firms out of the existing
financial-institutions and wirehouse channels, and somebody must say before launch which parts of
the country each new territory covers and who covers it (FRAME §1). The decision is three things
at once — the number of territories, a partition of the 1,229 zips carrying sales, and a roster
selecting ~13 of 111 wholesalers — signed by national sales leadership, low-reversibility, and
defensible line by line (FRAME §2). A certified `k=13` draw already exists: 0.781% opportunity
spread, 13 of 13 staffed, 4.51e-5 nats under the analytic balance ceiling, four certificates, 151
tests (FRAME §9). What framing exposed is that the acceptance test a business owner would sign has
six criteria and **three are unmet** — per-wholesaler continuity, a distance-to-best in business
units rather than nats, and a hand-drawn baseline to beat (FRAME §3). And the 2026-09-01 review
measured real saturation at **41.9%**, not the 5% assumed, which makes the incumbency premium
(~3.7 nats of swing) roughly four orders of magnitude larger than the balance residual that has
received all of the effort (FRAME §6, §9).

## 2. What the lenses found

Both lenses land on the same nut from opposite directions, and neither is a restatement of the
other.

**Grothendieck (`LENS_GROTHENDIECK.md` §3, §2).** *The map is chosen by a functional of the map
alone; its value is a functional of the pair.* Stage 1 maximises `W(π) = Σ_j log M(A_j)`; the
business signs `V(π,σ) = Σ_j log u_{σ(j)}(A_j)`. `W` is **not** an upper bound on `max_σ V(π,·)`,
not a lower bound, and not a projection with a known modulus — the two-stage step has never been
checked (§3). Widening to fractional assignment with per-agent measures makes the mismatch
*vanish* rather than move: the fibre relaxation is the **Eisenberg–Gale program of a Fisher
market** with equal budgets, in which balance is the equal-budget condition rather than a theorem,
the premium is priced by the duals, and the four existing certificates are **degenerations of one
duality gap** at `u_i ≡ λM` (§2, "five certificates is a symptom"). Two further deliverables: the
right notion of *sameness* between maps is **displacement** (mass that must move), because a
nat-tolerance on a second-order-flat functional makes near-optimal maps indistinguishable by
construction (§5a); and the **inflation group** `G = (ℝ_{>0})^R` identifies which statistics a
drawing rule may read to be un-inflatable by construction — normalised per-rep profiles (§5b).

**Gromov (`LENS_GROMOV.md`, moves 3/4/13).** Move 3 names the symmetry that paid for the
equal-size theorem — **agent anonymity**, broken by exactly the 41.9% term — and shows the
objective *fibers*: `Σ_i log g_i = n log ḡ − D(g)`, base = maximise the premium `P` (~3.7 nats,
never posed), fibre = equalise the gains (1e-4–1e-2 nats, exhaustively certified). The equal-size
theorem is true **verbatim, as a fiberwise statement**; the base was silently assumed to be a
point. Consequence nobody has written down: stage 1 equalises `M`, the fibre objective is equal
`g`, and **the spread of `g` has never been reported**. Move 4 answers "the premium is unbounded"
with *nobody has counted*: the ladder `P₀ ≤ P*(A) ≤ P₁₃ ≤ P_free` is four cheap numbers, and the
count that actually decides the blocking question is **zips contested among the selected 13**, not
among all 111. Move 13 purges six words, one load-bearing: **"books" is two objects** — reported
vs audited — so the blocking decision is not *stage 1 vs stage 2*. Move 4 also warns that the
hand-drawn baseline is premium-greedy and balance-sloppy and may therefore **win**, making the
programme's headline claim not merely unevidenced but plausibly false.

## 3. What each domain proposes

**Optimization (`DOMAIN_optimization.md` §4).** Not a philosophical problem but a *formulation*
problem. The centrepiece is a **rep-indexed MINLP with a perspective reformulation of the staffing
indicator** (§2.1) — territories named by their rep rather than anonymously, which dissolves the
`S_k` symmetry hazard *because* saturation is 41.9%, and in which every existing artifact
reappears as a fixed-variable restriction (fix `y` ⇒ stage 2; fix `y` and linearise ⇒ the
transportation LP). Around it: the fixed-roster **concave relaxation** as the certificate that
subsumes the existing four (§2.2), the **premium ladder** as three small exact solves (§2.3),
**displacement from the duals** as the acceptance unit — flagged as *the one genuinely unproved
step in the plan* (§2.4), and the `(premium, balance)` **Pareto frontier** as the honest way to
settle the never-elicited exchange rate (§2.5). Its recommended path puts measurement first
(Stage 0) and states that two of those numbers can **cancel the rest of the plan**; the τ-homotopy
(§2.6) is nominated as "the cheapest decisive experiment in either lens". Its own reading of the
blocking decision (§4, D2) is that the methods are indifferent to which book they are handed, so
it blocks *deployment*, not *formulation*.

**Economic theory (`DOMAIN_economic-theory.md` §4, sharpened by `LIT_economic-theory.md` §0).**
The contribution is not a better solver: **three of FRAME's open items are one item** — the
programme has never named its welfare criterion, and the criterion decides the balance-vs-
continuity exchange rate, the empty-bundle tie-break, and whether "do not starve anybody" means
Nash or nucleolus (§4). Its methods are audits the programme cannot currently produce: the EF1 /
Pareto audit whose hypotheses (`ρ = 0`, `d = 0`) have never been checked (§2.1), roster
**stability** (§2.4), selection defensibility as a cooperative game (§2.5), and strategy-proofness
by **restricted message space** (§2.7). The literature sweep then overturned four of its own
items: the fibration is **Atkinson's ε=1 identity**, 55 years old — cite it, stop proving it
(headline 5); the Shapley value of the roster game has a **closed form** via `littlechild1973` +
additivity, so the Monte-Carlo hand-off is unnecessary (headline 1); the core is provably empty on
a two-line instance and `deng1999` replaces the balancedness LP with an integrality check
(headline 2); and under aligned preferences the stable roster is the **greedy top-pair** matching
(`eeckhout2000`), which is *not* the delivered Hungarian max-weight roster — so the stability
audit is **guaranteed to fire** (headline 4). `green1986`'s Nested Range Condition, not Hurwicz,
is the load-bearing citation for the `G`-invariance claim, and `benporath2014` says the audited-
book route is a **solved model with an explicit optimal mechanism**, not an open question
(headline 3).

**Where they agree, and it matters:** both domains independently route the same three objects to
each other (EG duality, the `P₁₃` ladder, displacement), and both put *measurement before
formulation*. The measurement stage is exactly what this plan's constraints forbid — see §7.

## 4. The plan — units and dependency table

**Scope constraints applied** (user, this invocation): one week of subagent time · two or three
units first · both domains represented · **nothing touches `td/` code yet**.

The last constraint is load-bearing and it reshapes the plan. Both domains' recommended paths open
with a measurement stage (`DOMAIN_optimization.md` §5, nine numbers; `DOMAIN_economic-theory.md`
§5, six numbers). Every one of those requires running code against `instance_descaled.json.gz`,
which is (i) forbidden here and (ii) **not present in this worktree** (FRAME §5 — it lives at the
main checkout root, gitignored). So wave 1 is cut entirely from the **theory that does not need
the instance**, and each unit is required to state its result **conditionally**, naming the
threshold in the pending measurement that would flip it. That is a real cost, recorded in §7.

| unit | one-line spec | agent → verifier | depends on | size | model |
|---|---|---|---|---|---|
| **U0-lit** | Run `DOMAIN_optimization.md` §6's nine-question search brief; write `docs/LIT_optimization.md` + append to `docs/RESEARCH_ADDITIONS.bib`. | `lit-search` → (none; absence ledger is self-verifying) | — | M | opus |
| **U1-cert** | Prove or refute that the fixed-roster Eisenberg–Gale relaxation upper-bounds every integral coverage with that roster, and that the four existing certificates are degenerations of its dual at `u_i ≡ λM`. | `modeler` → `math-verify` | — (citations improve with U0) | **L** | opus |
| **U2-stab** | Prove that under the induced aligned preferences the unique stable roster is the greedy top-pair matching and the delivered Hungarian max-weight roster is generically unstable; write the counterexample the literature leaves underived (absence A5). | `modeler` → `math-verify` | — | **S–M** | opus |
| **U3-inv** | Test `DOMAIN_economic-theory.md` §2.7(b)'s `[claim]` against `green1986`'s Nested Range Condition: does a drawing rule reading only `G`-invariants preserve the revelation principle, and what does it forbid? | `modeler` → `math-verify` | — | **M** | opus |
| *U4-disp* | Establish or refute a modulus `objective-gap ≥ φ(mass moved)` — displacement as a certificate (`DOMAIN_optimization.md` §2.4, §8 Q3). | `modeler` → `math-verify` | **U0** (Q7: stability radius / inverse optimization) | M–L | opus |
| *U5-crit* | The criterion family as one Atkinson scalar `ε`: state ε=0/1/∞ as the three defensible criteria, fold in `bertsimas2011`'s price of fairness and `echenique2024`'s claim that stability is the *same* scalar. | `modeler` → `math-verify` | **U2-stab** | M | opus |
| *U6-sel* | Selection defensibility: closed-form Shapley via `littlechild1973` + additivity, and core-emptiness via `deng1999` integrality rather than Bondareva–Shapley. | `modeler` → `math-verify` | ★5 | M | opus |
| *U7-meas* | The measurement stage — `DOMAIN_optimization.md` §5 (nine numbers) and `DOMAIN_economic-theory.md` §5 (N1–N6). | `python-typed` → `code-verify` | **★6 and the instance** | L | opus |

*Italic rows are named and specified but **not** launched under this budget.*

**Order.** U0, U1-cert, U2-stab and U3-inv are **fully independent** and run in parallel — no
shared files, no shared claims, and none needs the instance. Wave 2 (U4-disp, U5-crit, U6-sel) is
gated as shown. U7-meas is gated on **★6** and on the instance being reachable, and it is the unit
both domains would have run *first* absent this plan's constraints.

**Recommended first wave: U0-lit + U1-cert + U2-stab + U3-inv.** That is three modeler units
(the user's "two or three") plus one literature run that costs no modeling time and gates wave 2.

## 5. Decisions needed from the user (★)

| ★ | question | gates | who answers |
|---|---|---|---|
| **★6** | **May a unit run code against the instance?** This plan's own constraint says no; both domains' plans open with measurement, the instance is not in this worktree, and every number in `DOMAIN_optimization.md` §5 and `DOMAIN_economic-theory.md` §5 is blocked until it is lifted. | **U7-meas entirely**, plus the conditional clauses in all three wave-1 units | user (programme) |
| **★1** | **A2 — are the 98 unselected released, or do they keep covering the residual channel?** Unconfirmed since 2026-08-31. `DOMAIN_economic-theory.md` §8 Q1 escalates it: it decides whether `d = 0`, hence whether `caragiannis2019`'s EF1/PO guarantee applies **at all** — and absence A4 records that if `d > 0` there is no weaker EF1 theorem to fall back on, only a lottery. | the entire EF1 branch (`DOMAIN_economic-theory.md` §2.1, N1, D1) | user → sponsor |
| **★2** | **U11 — is audited system-of-record book available at zip × wholesaler grain, and how far is it from reported book?** Both lenses agree this is the *smaller* form of FRAME §9's only blocking item and dissolves it if the answer is yes. | which branch of **U3-inv** is the live one; D5 | user |
| **★3** | **Should roster stability be a hard requirement?** FRAME §3's acceptance test has no stability criterion; `roth1984` argues it decides survival. Adding it is a scope change. **Ask after U2-stab reports**, not before — U2 decides whether the question is live. | a sixth acceptance criterion | user → sponsor |
| **★4** | **Which welfare criterion is the channel's standard?** Restated by `LIT_economic-theory.md` §0.5 as *one scalar* — Atkinson inequality aversion ε (0 = utilitarian, 1 = Nash/current, ∞ = leximin) — which is a materially easier ask than FRAME §3's never-elicited exchange rate. | **U5-crit**; D2 | user → sponsor |
| **★5** | **Does the programme want to know whether the core is empty?** `LIT_economic-theory.md` §0.2 shows the coverage game's core is empty whenever two wholesalers tie on a single zip, so "no selection is coalition-proof" is a sentence that will very likely have to be written. Decide before computing, per `DOMAIN_economic-theory.md` §8 Q5. | **U6-sel** | user |
| **★7** | Run `/domain econometrics` to unblock U5/A4 (regional bias in `M`) and U6 (the noise floor)? | the two hand-offs with no domain file | user |

Lower-priority sponsor questions already recorded in FRAME §8 and not repeated as ★: A1 ($1B a
target or a constraint), A6 (any operational coverage rule), and `DOMAIN_economic-theory.md` §8 Q8
(does "do not starve anybody" literally mean the nucleolus).

## 6. Challenges to settled items (listed, not acted on)

Per the stage rule, these are surfaced for the user and **not** acted on by any unit.

1. **"Staffing is exact and selects the roster" (FRAME §9, settled 2026-09-01).** Exact ≠ stable.
   `eeckhout2000` + `clark2006` imply the unique stable roster under aligned preferences is the
   greedy top-pair matching, which is not the Hungarian max-weight roster; `echenique2024` proves
   the two are different members of one family. The item is settled as *optimality* and the
   challenge is to what optimality buys. **U2-stab is scoped to establish this and stop** — it
   does not reopen the settled item.
2. **"Every zip carrying sales is assigned to exactly one territory" (FRAME §4, hard).**
   `caragiannis2019efx` shows a partial allocation achieving EFX at ≥ ½ the maximum Nash welfare;
   `chaudhury2021` gets EFX by withholding fewer than `n = 13` goods. The hard coverage constraint
   is what forces the programme down to EF1. Worth pricing for the sponsor, not relaxing.
3. **"No transfers" (FRAME §7, out of scope).** `DOMAIN_economic-theory.md` §2.7(a) notes VCG
   would solve the incentive problem outright and the impossibility is therefore self-imposed by
   scope; `benporath2012` sharpens it — *arbitrarily small* transfers suffice, a materially
   smaller ask than VCG-scale ones. Only leadership can reverse this.
4. **"Adjacency contiguity is not required" (FRAME §9, settled on the 547-component count).** The
   decision is not challenged; its *stated reason* is. `LENS_GROTHENDIECK.md` §5b/descent 6: 547
   is a component count on the support of `S`, while the objective is a functional of `M`, whose
   support is all ZCTAs. The recommendation is to stop quoting 547 as a property of the problem —
   a wording fix, not a reopening.
5. **"The niche is unoccupied" (`RESEARCH_FINDINGS`, carried into FRAME).** It survives a second
   literature, but `LIT_economic-theory.md` absence A6 says the *reason* must be restated:
   marketing science has known since `lal1986` that reps privately know territory potential and
   misreport it — the field answered with a compensation menu, not with a change to the drawing
   rule. The stronger, more defensible claim.
6. **"A certified k=13 draw exists."** `LENS_GROMOV.md` 13.2: all five certificates consume only
   the anonymous quotient, so the bare word reads to a sponsor as *proved near-best*. Rename to
   **balance-certified**. This is a free rename pass for the main session, not a unit.

## 7. What is deliberately not being done

- **The measurement stage.** Both domains open with it; this plan cannot run it (★6 + the instance
  is absent from this worktree). This is the single largest deviation from what either domain
  recommended, and it means **every wave-1 result is conditional**. Each unit carries the
  thresholds that would flip it, so no rework is wasted — but `DOMAIN_optimization.md` §4 warns
  that two of those numbers can *cancel* the rest of the plan (if `P₀ ≈ P*(A)` and the
  contested-among-the-13 count is small, the premium is not reachable by redrawing and the
  two-stage scheme was right all along). We are proving things that a morning of measurement might
  moot. Accepted knowingly under the constraint; recorded here as the assumption.
- **Anything that writes `td/`, `tests/`, `tools/` or `figures/`.** Units may write throwaway
  verification artifacts (`math-verify` requires a runnable one) but only under their own owned
  paths.
- **Building the rep-indexed MINLP** (`DOMAIN_optimization.md` §2.1). It is the centrepiece, and
  it is gated on D1 (the τ-homotopy) which is gated on measurement.
- **§2.8 robustness to `M`-bias** — no input exists until A4 is answered; `DOMAIN_optimization.md`
  §8 Q8 asks whether to cut it entirely. **§2.9 Benders** — explicitly deferred as engineering
  ahead of evidence.
- **U6 (the tier-2 noise floor) and U5/A4 (regional bias in `M`)** — no `DOMAIN_econometrics.md`
  (★7).
- **Contiguity on the full ZCTA graph** (FRAME §7), **compensation / transition packages / the
  residual channels** (FRAME §7), and **non-equal entitlements** (FRAME §7).
- **The Move 13 rename pass.** Free, blocks nothing, belongs to the main session and not to a
  unit.
