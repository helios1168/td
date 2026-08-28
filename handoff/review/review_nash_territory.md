# Adversarial review: Nash bargaining for post-merger territory division

**Revision 2.** Revision 1 raised six objections against
`papers/nash_territory_division_20260826.tex` and the supporting code. This revision records
the outcome of the retirement condition set for objection #1, which was run and returned a
*confirmation* rather than a retirement; the resulting decision to move to a zero disagreement
point; and a **correction to an error in revision 1** (§7), where a robustness property was
credited to the model that it does not have.

Claims marked *(verified)* were recomputed from `zip50.py`; *(replicated)* means a figure in the
paper was reproduced. All numbers derive from the synthetic 50-zip instance — see §9 for what
that does and does not license.

**Revision 3 note.** Objection 2's retirement condition (fit a crude concave response, check
whether the allocation moves) has since been run in full: `objection2_capacity.md`, alongside
this file. Verdict: confirmed, not retired — and more pointedly, a capacity ceiling correlated
with legacy book size reproduces the *rejected* `d=(S_a,S_b)` map from §6 below almost exactly at
plausible parameter values, while a symmetric ceiling (same number for both reps) is cosmetic.
The verdict table in §8 is updated accordingly; the body of §2 (Objection 2's steelman) is
otherwise unchanged and still correctly states the concern.

---

## 1. Steelman

Two merging wholesaling forces each hold a book across the same ZCTAs. Value a zip to each rep
as own sales retained, plus a capture fraction θ of the other's book, plus a credit λ on
untapped opportunity; give rep *a* a set *S* and score the split by the product of each rep's
gain. Maximising that product is Pareto efficient by construction, immune to the value
destruction that afflicts difference-minimising criteria, and — because `log g_a + log g_b` is
concave in expressions linear in the assignment variables — is a convex MINLP that outer
approximation solves to a certificate in 6–7 iterations at n=400. The argument the authors do
not make but could: the parameter the model appears to hang on, θ, turns out empirically not to
matter (a θ×λ sweep moves a mean of 0.9 zips of 50, *(verified)*), so the unestimated parameter
is not the critical path — the sales data is.

The engineering is sound. A reimplementation of the outer approximation carrying an explicit
disagreement point reproduces the paper's Section 7 result exactly — product 24.09117,
g_a=4.9787, g_b=4.8388, k=25, bound gap −8.9×10⁻¹⁶ — and agrees with brute-force enumeration on
80/80 instances at n=12 under both baselines *(verified)*. The certificate is a genuine bound,
the refusal to patch fragmentation greedily is right, and reporting λ-breakpoints instead of
local derivatives is better practice than most applied work in this area.

---

## 2. Grothendieck pass — is this the right object?

**Probes that came back clean.** Scaling *a*'s utility by 10³ leaves k=25 unchanged
*(verified)*, so Nash's invariance axiom survives the discrete implementation. The
concavification is real: `log g` is concave in a linear form, the tangent cuts are valid upper
bounds, and termination compares the incumbent's true log-product to the relaxation bound. The
utilitarian prefix claim is exact for the reason given. Equalisation is genuinely
value-destroying and the welfare-floor remedy is correctly specified.

### Objection 1 (Fatal — confirmed, now resolved): the disagreement point is not a disagreement point

`d = (S_a, S_b)` is described as "what they hold if the territory is not redivided." After a
merger that counterfactual is unavailable: neither rep can unilaterally revert to their legacy
book, because the merged firm assigns territories. A disagreement point in Nash's sense must be
an outcome a player can *guarantee itself* by refusing to agree. Pre-merger production is a
historical accounting fact, not a threat.

The consequence is that EF1 does not transfer. EF1 is a theorem about maximum Nash *welfare* —
the product of utilities with a zero baseline ([Caragiannis et al. 2019](https://doi.org/10.1145/3355902)).
Subtracting an allocation-independent constant changes the maximiser and carries no guarantee.
Brute-forced over 3,579 random instances with headroom enforced *(verified)*: **EF1 fails in
1.3% of instances under d=(S_a,S_b) and 0% under d=(0,0)**, worst case leaving residual envy of
14.5% of the envier's own bundle. Section 5's description of EF1 as "the strongest fairness
guarantee available for indivisible goods" belongs to a model the paper does not build.

**Retirement condition set in revision 1:** re-solve with d=(0,0); if the allocation moves by
≤1 zip, downgrade to cosmetic. **Result: 3 zips move. Not retired.** Details in §3.

**Resolution: adopt d=(0,0).** Rationale and the decision record are in §6.

### Objection 2 (Structural): u is an accounting identity presented as a utility

`u_a(z) = c₁A_z + c₂B_z + λM_z` is linear with globally fixed coefficients. Capacity is absent,
so utility is linear in territory size and a rep winning 46 zips is modelled as servicing all of
them at full effectiveness — the utilitarian row in Appendix A is absurd *because* of the
missing capacity constraint, and the same omission is silently present in the Nash solution. θ
is constant across zips though transfer capture depends on relationship depth. Travel enters
only as a penalty ρ on the objective, not as a cost in u, which is why ρ has no natural scale.

[Skiera & Albers 1998](https://doi.org/10.1287/mksc.17.3.196) exists precisely because territory
alignment should maximise contribution through an estimated concave sales-response function, not
a linear proxy — linearity in effort is what produces corner solutions.
[Zoltners & Sinha 2005](https://doi.org/10.1287/mksc.1050.0133) reviews thirty years in which
the response function, not the optimiser, was the hard part.

*Retirement condition:* fit a crude concave response and check whether the allocation moves.

---

## 3. The disagreement-point test, in full

![Three-panel result: 3 zips move; only the pre-merger baseline breaks EF1; never ≤1 zip anywhere in the parameter box](/Users/ntlee/.claude-science/orgs/d5c457c5-ce83-4d2d-98b5-1623aef60f2a/artifacts/proj_07e49f835fd0/fb8afe02-fb6b-4a44-9042-1c762e6bca94/v806427cf_disagreement_point_test.png)

**Three zips move, all in the same direction.** From *a* to *b*. The larger-book rep loses 7.61%
of true bundle utility and 4.5 points of opportunity share (53.4% → 48.9%) *(verified)*. That is
a transfer between two people whose compensation this sets, not a rounding difference.

**The gap is not a parameter artefact.** Across θ∈[0.2,0.6] × λ∈[0.1,0.5] the count ranges 2 to
8 and is **never ≤1 anywhere in the box** *(verified)* — worst at low λ, mildest at high λ, which
follows because heavy opportunity weighting washes out the baseline. This is the *same* box over
which the paper correctly shows insensitivity to θ and λ. The map is stable against parameter
choice and unstable against baseline choice, which localises the problem precisely.

**EF1 is far more fragile than the point estimate suggests.** At θ=0.4, λ=0.3 both maps happen
to satisfy EF1, but the margins are not comparable: the pre-merger baseline clears by 0.0100,
the zero baseline by 0.9759 — 97× further from the boundary. Under the paper's own 10%/6%
data-noise model, **the pre-merger baseline violates EF1 in 74 of 200 draws (37%), the zero
baseline in 0 of 200** *(verified)*. Since data uncertainty is established as the dominant error
source, the EF1 claim is not merely unproven under this baseline — it is unreliable at exactly
the noise level expected in production.

**Switching is nearly free in the objective.** Scoring the d=0 map under the d=(S_a,S_b)
objective costs 1.44% of the bargaining product *(verified)*. The two formulations are not
locked in a trade-off.

---

## 4. Headroom and baseline are independent decisions

Asked whether the pre-merger baseline follows from the net-headroom convention: it does not.
The conventions differ only in the coefficient on `B_z` — net gives `θ(1−λ)`, gross gives
`(θ−λ)`, negative iff λ>θ, which is the incoherence the HANDOFF rejects *(verified
symbolically)*. Neither expression contains `S_a`. The baseline is a separate subtraction
applied afterwards.

They are separable in effect as well as in algebra: switching convention moves 2 zips holding
the baseline at the book and 0 holding it at zero; switching baseline moves 3 zips under either
convention *(verified)*.

Where they touch is the double-counting of `A_z`. With a nonzero baseline, own sales enter twice
with opposite signs — weight `c₁=0.70` inside `u_a` on zips won, weight `1.00` subtracted outside
over all zips. The convention sets the coefficient inside `u`; the baseline decides whether `A_z`
is *also* subtracted outside. **Setting d=0 removes the second appearance and leaves the net
convention intact** — the HANDOFF's "do not relitigate" on net headroom stands.

**A consequence worth banking: λ\* is an artefact of the baseline, not the convention.** Measured
λ\* is 0.0286 (net, book baseline) and 0.0295 (gross, book baseline), reproducing the HANDOFF's
identity λ\*_net = λ\*_gross/(1+λ\*_gross) to three decimals *(verified)*. Under d=(0,0) utilities
are positive by construction, the bargaining set is never empty, and **λ\* does not exist under
either convention.** Section 5's "one limitation" and the egalitarian fallback below λ\* both
disappear on the switch.

---

## 5. Gromov pass — does it survive blurring?

**Probes that came back clean.** Parameter error: sweeping θ×λ moves a mean of 0.9 zips of 50
*(verified)* — the flat λ-interval [0.265, 0.506] is real and is the paper's strongest empirical
finding. Prefix shortfall at n=50 is 0.0008% against a 1-flip/1-swap local optimum *(verified)*,
below every other error source. Contiguity costs 0.06–0.32%.

### Objection 3 (Structural): "data uncertainty dominates" compares two different statistics

The headline — 5 zips moved by parameters against 34 by data — is the basis for prioritising data
quality over settling λ. Those are not the same statistic *(replicated)*:

| statistic under 10%/6% data noise, 500 draws | value |
|---|---|
| zips that *ever* flip across draws | **35 of 50** |
| zips flipping in >25% of draws | 9 |
| mean zips moved *per draw* | **5.4** |

The 34 is a union across draws; the parameter figure is a per-draw displacement. Like for like,
data noise moves 5.4 zips per draw against 0.9 — a real 6× effect, so the conclusion survives,
but the stated contrast overstates it roughly sixfold. The union statistic also grows
monotonically with draw count: at 5,000 draws it approaches 50 of 50, which would read as "the
model is entirely noise" while nothing changed.

*Retirement condition:* restate both per-draw, and report the flip-probability distribution. The
9 zips flipping in >25% of draws is the adjudication list.

### Objection 4 (Contained): Appendix B's random-subset experiment has no power

400,000 uniform draws from 2⁵⁰ is a sampled fraction of 3.55×10⁻¹⁰ *(verified)*, and uniform
subsets concentrate near |S|=25 with utilities near the mean — they never approach the frontier.
The finding replicates (best random 23.897 vs best prefix 24.091) and means nothing: a
1-flip/1-swap local search from the prefix optimum immediately reaches 24.09117 *(verified)*,
which is the exact solver's Section 7 answer. The experiment "confirms" a property the main text
correctly states is violated about half the time.

Separately the appendix columns are on a different scale from the main text (Nash 210.253 vs
24.091) and appear to be computed on gross utilities rather than gains; neither convention
reproduces 210.253 from `zip50.py` *(verified)*, so the seed or instance differs. Resolve before
anyone cites the table.

*Retirement condition:* replace uniform sampling with local search; label the utility convention.

---

## 6. Decision record: the disagreement point

**Decision: use d = (0,0).** Adopted after the retirement condition confirmed rather than
retired objection 1, and after incentive compatibility was ruled out as a consideration (sales
are measured, not self-reported — see §7).

![Two-panel decision basis: EF1 as a knife-edge property of omega=0.5, and what the choice costs each rep](/Users/ntlee/.claude-science/orgs/d5c457c5-ce83-4d2d-98b5-1623aef60f2a/artifacts/proj_07e49f835fd0/8c953ed8-aa0f-4b7a-8620-70f86bff0d28/v35ca8acc_baseline_decision.png)

**The finding that decides it: the pre-merger baseline is already an asymmetric Nash weight,
chosen implicitly.** Asymmetric Nash at d=0 with ω=0.54 reproduces the pre-merger-baseline
allocation exactly — 0 zips differ *(verified)*. So `d=(S_a,S_b)` is not a distinct solution
concept; it is `max g_a^ω g_b^(1−ω)` with ω set by an accident of the data. That implicit weight
is unstable: it ranges 0.51–0.56 across the defensible θ×λ box and wanders with sd 0.014 (mean
0.531) under the 10%/6% noise model *(verified)*. The model ships a seniority policy whose
strength nobody chose and which moves when the sales extract is refreshed.

ω=0.54 is also not a defensible entitlement number. A book-proportional rule would use
S_a/(S_a+S_b) = 0.625 *(verified)*. The baseline delivers neither symmetry nor proportionality.

**EF1 is a knife-edge property of ω=0.5, so there is no compromise position.** Under the noise
model *(verified)*:

| ω | EF1 violated |
|---|---|
| 0.44 | 100% |
| 0.46 | 95% |
| **0.48 – 0.52** | **0%** |
| 0.54 (= the implicit baseline weight) | 50% |
| ≥ 0.56 | 100% |

Any tilt large enough to matter destroys the guarantee. The choice is therefore binary: EF1 with
no seniority tilt (d=0), or a seniority tilt with no EF1 (explicit ω).

**What the choice costs.** Both reps gain substantially either way, because the merged firm
captures headroom neither could reach alone *(verified)*:

| option | zips to a | a's book | b's book | a's opp. share | a vs pre-merger | b vs pre-merger |
|---|---|---|---|---|---|---|
| d=(S_a,S_b) | 25 | 7.979 | 6.639 | 53.4% | +166.0% | +268.8% |
| **d=(0,0)** | 22 | 7.371 | 7.232 | 48.9% | +145.7% | +301.8% |

The switch costs *a* 7.6% and gives *b* 8.9%; the bargaining product falls 1.44%.

**Why d=0 wins.** Against a modest redistribution it buys: EF1 violated in 0/200 noise draws
rather than 74/200; a claim that is a theorem rather than a hope; and the disappearance of λ\*
along with the egalitarian-fallback branch (§4). The asymmetry in *defensibility* is decisive.
Under d=0 the statement to the room is that neither rep's history entitles them to more, the
split maximises the product of what each ends with, and neither envies the other beyond a single
zip. Under d=(S_a,S_b) the statement is that rep *a* gets more because they brought more,
weighted at 0.54 — a number derived from no principle that moves when the data is re-pulled.

**If distribution overrules this and wants the tilt:** do not return to the baseline. Set ω
explicitly at a number someone signs (0.625 if the principle is book-proportional), state that
EF1 no longer holds, and report ω-sensitivity alongside the map. An owned policy at ω=0.625 is
defensible; an unowned one at ω≈0.54±0.02 is not.

**Paper changes implied.** d=(0,0) throughout; EF1 restated as a theorem citing
[Caragiannis et al. 2019](https://doi.org/10.1145/3355902); the criterion renamed *maximum Nash
welfare* rather than Nash bargaining, since with a zero threat point that is what it is;
Section 5's λ\* limitation deleted; the asymmetric-Nash paragraph reframed as the escape hatch
for an explicit seniority policy, carrying the warning that it forfeits EF1.

---

## 7. Correction to revision 1

**Revision 1 credited the model with a robustness property it does not have.** The claim was
that the net-headroom convention makes sandbagging counterproductive, described as "a genuine
and unclaimed property worth stating in the paper." Two errors.

First, attribution: the disincentive comes from the *subtracted baseline*, not the headroom
convention. The marginal effect of reported `A_z` on *a*'s objective is `c₁−1 = −0.30` on a zip
won and `−1.00` on a zip ceded under d=(S_a,S_b); under d=0 it is `+c₁ = +0.70` and `0`
*(verified)*.

Second, and more seriously, revision 1 tested only the direction that failed. A full sweep of
unilateral misreporting *(verified)*:

| baseline | best gain, under-reporting | best gain, over-reporting | worst case |
|---|---|---|---|
| d=(S_a,S_b) | −0.89% | **+21.16%** | +21.16% |
| d=(0,0) | +2.69% | +0.00% | **+2.69%** |

The nonzero baseline does not make reporting incentive-compatible. It flips the profitable
direction from sandbagging to inflation, and inflation is the larger exposure by roughly 8×.
[Crawford & Varian 1979](https://doi.org/10.1016/0165-1765(79)90118-6) is the reference, and it
cuts against the formulation rather than for it.

**This does not affect the decision in §6.** The user has confirmed sales are reliably measured
rather than self-reported, so no manipulation channel is live. It is recorded because revision 1
overstated the model's robustness in a document others may read, and because it removes what had
looked like the strongest argument *for* the pre-merger baseline.

---

## 8. Verdict table

| # | Objection | Severity | Status | Decision affected |
|---|---|---|---|---|
| 1 | d=(S_a,S_b) is not a threat point; EF1 fails under it | **Fatal** | **Confirmed** (3 zips, never ≤1 across the box; 37% EF1 violation under noise) → **resolved: adopt d=0** | Settled |
| 2 | Linear u, no capacity; θ constant across zips | **Structural** | **Tested — confirmed, not retired** (`objection2_capacity.md`): book-proportional capacity reproduces the rejected d=(S_a,S_b) map at plausible multiples; symmetric ceiling is cosmetic; θ-heterogeneity sub-claim still open | Defensibility against the Skiera–Albers critique, and interacts directly with objection 1's resolution |
| 3 | 5-vs-34 sensitivity compares per-draw to union | **Structural** | Open — restate both per-draw (5.4 vs 0.9) | Data-cleaning budget; adjudication list |
| 4 | Appendix B has no power; scale mismatch unreconciled | **Contained** | Open — swap in local search | Credibility of the appendix only |
| 5 | Reps are not players — the committee decides | **Structural** | Open — state whether the criterion is descriptive or normative | How the output is presented |
| 6 | Dense overlap components unsupported | **Structural** | Open — **the live kill criterion**; run `census` | Whether any of this ships nationally |

Ranking under pushback, unchanged: #4 abandoned first, #2 and #6 held longest. Objection #1 is
no longer in contention.

**Clean probes, restated as evidence:** scale invariance holds; the outer approximation is a
genuine global method with a real certificate reproducing Section 7 exactly; the concavification
argument is correct; parameter insensitivity is solid and is the most useful result in the paper;
the refusal to repair fragmentation greedily is right; and the net-headroom convention survives
the baseline change untouched (§4).

---

## 9. Scope of these findings

Every number here comes from `zip50.py`'s synthetic mixture (corr(A_z,B_z) = +0.685). The
*structural* findings generalise and should be expected to hold on real books: that a nonzero
baseline is equivalent to some implicit ω, that the implied ω is unstable under data noise, that
EF1 is knife-edge at symmetry, and that headroom convention and baseline are independent axes.
The *specific* magnitudes — ω=0.54, the 3-zip displacement, the 7.6%/8.9% split, the 37%
violation rate — will not carry over. Re-run §3 and §6 on real data before quoting any of them.

---

## 10. Kill criteria

Abandon rather than patch if any of these hold on real data:

1. **`census` returns dense components covering most of the opportunity.** Two-player theory does
   not compose, leximin is unbuilt, and the synthetic lattice already produced exactly this. Most
   likely kill; checkable immediately.
2. **Reps cannot be treated as players** because the committee overrides on tenure, relationships,
   or retention. Then the bargaining framing is decoration on a constrained assignment problem,
   and the honest model is [Hess & Samuels 1971](https://doi.org/10.1287/mnsc.18.4.p41)-style
   districting with an explicit fairness constraint.
3. **State scope binds harder than contiguity.** If appointments and product availability force
   state-respecting territories, the feasible set may be small enough that the criterion is
   irrelevant. Enumerate before optimising.
4. **corr(A_z, B_z) is near zero.** The books barely overlap, few zips are contested, and this
   machinery answers a question nobody has.

---

## 11. The one next check

**Run `T.census(G)` on the real ZCTA graph.** With the disagreement point settled, this is the
sole remaining gate: it decides whether the two-player theory applies at all, and the paper's own
synthetic run returned one dense component covering 100% of opportunity. Everything downstream —
θ estimation, contiguity, the MINLP — is wasted effort if the national problem does not decompose
into 1-to-1 pairs.

Run the §3 comparison on the same data load while it is open, to confirm the 3-zip displacement
is representative of real books rather than of the synthetic instance.

---

## 12. Positioning against the literature

The territory-design line will read this as a districting paper and benchmark it against
[Hess & Samuels 1971](https://doi.org/10.1287/mnsc.18.4.p41),
[Zoltners & Sinha 1983](https://doi.org/10.1287/mnsc.29.11.1237),
[Skiera & Albers 1998](https://doi.org/10.1287/mksc.17.3.196) and
[Drexl & Haase 1999](https://doi.org/10.1287/mnsc.45.10.1307). Against that benchmark the
contribution is the *fairness criterion* — balance and contribution objectives are old; what is
new is scoring the split by a welfare product between two incumbent forces rather than optimising
a single firm's objective. That framing should be explicit; it is currently buried under the
MINLP machinery.

The contiguity encoding is standard and correctly implemented, but
[Validi, Buchanan & Lykhovyd 2021](https://doi.org/10.1287/opre.2021.2141) give formulations that
dominate both the single-commodity flow and lazy-cut encodings considered here, and the
commercial-districting variants in
[Salazar-Aguilar, Ríos-Mercado & Cabrera-Ríos 2011](https://doi.org/10.1007/s11067-010-9151-6)
and [Ríos-Mercado & López-Pérez 2012](https://doi.org/10.1016/j.omega.2012.08.002) handle
realignment-with-disjoint-assignment, which is nearly this problem. This is the answer to the
"scipy re-solves from scratch" gap.

With d=0 adopted, the bargaining-side positioning becomes straightforward and *stronger*: this is
maximum Nash welfare over indivisible goods.
[Caragiannis et al. 2019](https://doi.org/10.1145/3355902) supplies the EF1 and Pareto guarantees
as theorems, [Cole & Gkatzelis 2018](https://doi.org/10.1137/15m1053682) the approximation
algorithms, and [Lee 2017](https://doi.org/10.1016/j.ipl.2017.01.012) the APX-hardness that
explains why exhaustive validation stops at n=14. Exact solvability should be stated as a special
structure this instance class has — concave objective, linear gains — not a general property.
[Moulin 2019](https://doi.org/10.1146/annurev-economics-080218-025559) is the accessible survey
for a non-specialist audience. If an explicit seniority weight is ever adopted,
[Kalai 1977](https://doi.org/10.2307/1913954) is the reference for the proportional/entitlement
family. The nonconvex-bargaining literature —
[Mariotti 1998](https://doi.org/10.1007/s003550050114),
[Xu & Yoshihara 2005](https://doi.org/10.1016/j.geb.2005.09.003) — is no longer load-bearing once
the baseline is zero, though it remains the right citation for the point-cloud remark in §2 of
the paper.

One framing point survives the change. If the integration committee rather than the reps decides,
the descriptive claim still needs non-cooperative support:
[Rubinstein 1982](https://doi.org/10.2307/1912531) and the Binmore–Rubinstein–Wolinsky reading of
Nash as the limit of alternating offers require that players actually make offers. They do not
here. That does not make the criterion wrong — it makes it *normative*, a fairness standard the
firm imposes, and one sentence should say so rather than leaving "bargaining" to imply otherwise.
Under maximum Nash welfare that sentence is easier to write, since the fair-division literature
is explicitly normative and claims no descriptive content.
