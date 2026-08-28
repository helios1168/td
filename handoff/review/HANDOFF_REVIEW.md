# Wholesaler Territory Division — Review Handoff

**Read `../HANDOFF.md` first, then this file. Written for a fresh context window.**

This supplements the main handoff. It records an adversarial review of
`../papers/nash_territory_division_20260826.tex`, one settled decision that changes the
model, one correction to the review itself, and what remains open.

**One decision supersedes the main handoff.** `../HANDOFF.md` §1 lists the fairness baseline as
"pre-merger production — chosen deliberately." That decision was tested and reversed. **The
disagreement point is now `d = (0,0)`.** Section 2 below is the rationale; it is settled, not
open for relitigation, but the reasoning is recorded so it can be challenged on real data.

Everything else in `../HANDOFF.md` stands, including the net-headroom convention, which was
tested and is unaffected (§3).

**Objection 2 (capacity) now has a verdict too, recorded separately.** `objection2_capacity.md`
tested the retirement condition from §5 below (fit a crude concave response, check whether the
allocation moves) and found: a symmetric capacity ceiling is cosmetic, but a ceiling correlated
with legacy book size is not, and at plausible multiples reproduces the **rejected**
`d=(S_a,S_b)` map almost exactly. Read it before treating the `d=0` decision above as having
closed the door on legacy-book-size asymmetry -- it closed one door to it, not the only one.

---

## 1. What was done

Six objections were raised against the paper. Each carries a severity and a condition that
would retire it. The full review with citations is `review_nash_territory.md` (revision 2).

Every claim below was recomputed against the code, not read off the paper. A reimplementation
of the outer approximation carrying an explicit disagreement point (`code/dzero.py`,
`nash_exact_d`) reproduces the paper's Section 7 result exactly — product 24.09117, g_a=4.9787,
g_b=4.8388, k=25, bound gap −8.9e−16 — and matches brute-force enumeration on 80/80 instances
at n=12 under both baselines. Findings rest on that agreement.

**Scope caveat, applies throughout.** Every number here comes from `../code/zip50.py`'s
synthetic instance (corr(A_z,B_z) = +0.685). Structural findings generalise; specific
magnitudes will not. See §6.

---

## 2. The decision: disagreement point moves to zero

### What was wrong

`d = (S_a, S_b)` was described as "what they hold if the territory is not redivided." After a
merger neither rep can unilaterally revert to their legacy book — the merged firm assigns
territories. A Nash disagreement point must be an outcome a player can *guarantee itself* by
refusing to agree. Pre-merger production is an accounting fact, not a threat.

The consequence is concrete: **EF1 does not transfer.** EF1 is a theorem about maximum Nash
*welfare* — the product with a zero baseline (Caragiannis et al. 2019,
`10.1145/3355902`). Subtracting an allocation-independent constant changes the maximiser and
carries no guarantee. Brute-forced over 3,579 random instances (`code/ef1_test.py`): EF1 fails
in **1.3% of instances under d=(S_a,S_b), 0% under d=(0,0)**, worst case leaving residual envy
of 14.5% of the envier's own bundle.

### The test that settled it

Retirement condition set in advance: re-solve at d=(0,0); if ≤1 zip moves, the objection is
cosmetic. **Three zips moved. Not retired.** (`code/retire.py`, `code/retire2.py`;
`figures/disagreement_point_test.png`.)

- All three move from *a* to *b*. Rep *a* loses 7.61% of true bundle utility and 4.5 points of
  opportunity share (53.4% -> 48.9%).
- Across theta in [0.2,0.6] x lambda in [0.1,0.5] the count ranges **2 to 8 and is never <=1
  anywhere in the box**. This is the same box over which the paper correctly shows insensitivity
  to theta and lambda: the map is stable against parameter choice, unstable against baseline
  choice.
- Under the paper's own 10%/6% noise model, **d=(S_a,S_b) violates EF1 in 74/200 draws (37%);
  d=(0,0) in 0/200.** At the point estimate the pre-merger baseline clears EF1 by 0.0100, the
  zero baseline by 0.9759 — 97x further from the boundary.
- Cost of switching: **1.44%** of the bargaining product.

### Why zero rather than an explicit tilt

**The pre-merger baseline is already an asymmetric Nash weight, chosen implicitly.** Asymmetric
Nash at d=0 with omega=0.54 reproduces the pre-merger-baseline allocation *exactly*, 0 zips
differing (`code/omega.py`). So `d=(S_a,S_b)` is not a distinct solution concept — it is
`max g_a^omega g_b^(1-omega)` with omega set by an accident of the data. That weight is
unstable: **0.51–0.56 across the parameter box, sd 0.014 under data noise** (`code/omega2.py`).
A book-proportional rule would use S_a/(S_a+S_b) = 0.625. The baseline matches neither symmetry
nor proportionality.

**EF1 is knife-edge at symmetry, so there is no compromise position** (`figures/baseline_decision.png`):

| omega | EF1 violated (noise draws) |
|---|---|
| 0.44 | 100% |
| 0.46 | 95% |
| **0.48 – 0.52** | **0%** |
| 0.54 (= implicit baseline weight) | 50% |
| >= 0.56 | 100% |

The choice is binary: EF1 with no seniority tilt, or a tilt with no EF1.

### What it costs, and why zero wins

| option | zips to a | a's book | b's book | a's opp. share | a vs pre-merger | b vs pre-merger |
|---|---|---|---|---|---|---|
| d=(S_a,S_b) | 25 | 7.979 | 6.639 | 53.4% | +166.0% | +268.8% |
| **d=(0,0)** | 22 | 7.371 | 7.232 | 48.9% | +145.7% | +301.8% |

Both reps gain substantially either way — the merged firm captures headroom neither could reach
alone. The decisive asymmetry is defensibility. Under d=0: neither rep's history entitles them
to more, the split maximises the product of what each ends with, neither envies the other beyond
one zip. Under d=(S_a,S_b): rep *a* gets more because they brought more, weighted at 0.54 — a
number derived from no principle that moves when the data is re-pulled.

**If distribution wants the tilt anyway:** do not return to the baseline. Set omega explicitly
at a number someone signs (0.625 if the principle is book-proportional), state that EF1 no
longer holds, report omega-sensitivity with the map. `code/omega.py::asym_nash` does this.

### Paper edits implied

- `d=(0,0)` throughout.
- EF1 restated as a theorem, citing Caragiannis et al. 2019.
- **Rename the criterion: maximum Nash welfare, not Nash bargaining.** With a zero threat point
  that is what it is, and the fair-division literature is explicitly normative — which is also
  the honest framing given the committee, not the reps, decides (objection 5).
- **Delete Section 5's lambda\* limitation and the egalitarian fallback.** See §3.
- Reframe the asymmetric-Nash paragraph as the escape hatch for an explicit seniority policy,
  warning that it forfeits EF1.

---

## 3. Headroom convention is unaffected — and lambda* disappears

Asked whether the baseline followed from the net-headroom decision: **it does not.** The
conventions differ only in the coefficient on `B_z` — net gives `theta(1-lambda)`, gross gives
`(theta-lambda)`, negative iff lambda > theta, which is the incoherence `../HANDOFF.md` rejects.
Neither expression contains `S_a` (verified symbolically, `code/coupling.py`).

Separable in effect too: switching convention moves 2 zips holding the baseline at the book, 0
holding it at zero; switching baseline moves 3 zips under either convention.

They touch only in the double-counting of `A_z`: with a nonzero baseline, own sales enter twice
with opposite signs — weight `c1=0.70` inside `u_a` on zips won, weight `1.00` subtracted outside
over all zips. **Setting d=0 removes the second appearance and leaves net headroom intact.**

**Bank this:** measured lambda\* is 0.0286 (net) and 0.0295 (gross) under the book baseline,
reproducing the HANDOFF's identity `lambda*_net = lambda*_gross/(1+lambda*_gross)` to three
decimals. Under d=(0,0) utilities are positive by construction, the bargaining set is never
empty, and **lambda\* does not exist under either convention.** Trap 10 in `../HANDOFF.md` is
void once the baseline is zero.

---

## 4. Correction to the review

Revision 1 of the review credited the model with a robustness property it does not have, and
this is recorded rather than quietly dropped.

The claim was that net headroom makes sandbagging counterproductive. Two errors. The
disincentive comes from the *subtracted baseline*, not the convention. And only the direction
that failed was tested. Full sweep (`code/coupling5.py`):

| baseline | best gain, under-reporting | best gain, over-reporting | worst case |
|---|---|---|---|
| d=(S_a,S_b) | −0.89% | **+21.16%** | +21.16% |
| d=(0,0) | +2.69% | +0.00% | **+2.69%** |

The nonzero baseline does not make reporting incentive-compatible — it flips the profitable
direction from sandbagging to inflation, worse by ~8x. Crawford & Varian 1979
(`10.1016/0165-1765(79)90118-6`) cuts against the formulation, not for it.

**Not decision-relevant here** — sales are reliably measured, not self-reported, so no
manipulation channel is live. Recorded because it removes what had looked like the strongest
argument *for* the pre-merger baseline.

---

## 5. Open objections

| # | Objection | Severity | Retirement condition |
|---|---|---|---|
| 2 | Linear `u`, no capacity constraint; theta constant across zips | Structural | **Tested, confirmed for the capacity half -- see `objection2_capacity.md`.** Book-proportional capacity reproduces the rejected `d=(S_a,S_b)` map at plausible multiples; a symmetric ceiling is cosmetic; theta-heterogeneity sub-claim still untested |
| 3 | "5 vs 34" sensitivity compares per-draw to union statistics | Structural | Restate both per-draw (5.4 vs 0.9); report the flip-probability distribution |
| 4 | Appendix B random-subset test has no power; scale mismatch | Contained | Replace uniform sampling with local search; label the utility convention |
| 5 | Reps are not players — the committee decides | Structural | State in the paper whether the criterion is descriptive or normative |
| 6 | Dense overlap components unsupported | Structural | **Run `census` on real data — the live gate** |

**Objection 2 is the one a referee will press hardest.** Skiera & Albers 1998
(`10.1287/mksc.17.3.196`) exists because territory alignment should maximise contribution
through an estimated concave response function, not a linear proxy — linearity in effort is
what produces corner solutions. The utilitarian row in Appendix A (a takes 46 zips) is absurd
*because* capacity is missing, and the same omission is silently present in the Nash solution.

**Objection 3 detail** (`code/probe4.py`): under 10%/6% noise over 500 draws, 35 of 50 zips
*ever* flip, 9 flip in >25% of draws, mean moved *per draw* is 5.4. The paper's "34" is a union
across draws; the parameter figure is per-draw. Like for like it is 5.4 vs 0.9 — a real 6x
effect, so the conclusion survives, but stated ~6x too strongly. The union statistic grows
monotonically with draw count. **The 9 zips flipping in >25% of draws is the adjudication list.**

**Objection 4 detail** (`code/probe3.py`): 400k uniform draws from 2^50 samples 3.55e−10 of the
space and concentrates near |S|=25. A 1-flip/1-swap local search from the prefix optimum
immediately reaches 24.09117 — the exact solver's answer. Appendix B's numbers also appear to
be on gross utilities rather than gains, and 210.253 does not reproduce from `zip50.py` under
either convention; the seed or instance differs.

---

## 6. What generalises and what does not

**Structural — expect these to hold on real books:**
- A nonzero baseline is equivalent to *some* implicit asymmetric-Nash weight.
- That implied weight is unstable under data noise.
- EF1 is knife-edge at symmetry; any material tilt forfeits it.
- Headroom convention and baseline are independent axes.
- lambda\* is an artefact of the nonzero baseline.

**Instance-specific — recompute before quoting:** omega=0.54, the 3-zip displacement, the
7.6%/8.9% split, the 37% EF1 violation rate, the 1.3% brute-force violation rate.

---

## 7. Next steps, in order

1. **`T.census(G)` on the real ZCTA graph.** The sole remaining gate. It decides whether the
   two-player theory applies at all, and the synthetic lattice already returned one dense
   component covering 100% of opportunity. Everything downstream — theta estimation, contiguity,
   the MINLP — is wasted effort if the national problem does not decompose into 1-to-1 pairs.
2. **Re-run §2's comparison on real data in the same session** — one data load confirms whether
   the 3-zip displacement is representative or synthetic.
3. **Objection 2**: DONE for the capacity half, see `objection2_capacity.md` -- confirmed, not
   retired, and get a non-book-size capacity signal before using one operationally. The
   theta-heterogeneity sub-claim (transfer capture varying with relationship depth) is still open.
4. **Objections 3 and 4**: text and appendix fixes; cheap, do them alongside the paper edits.

Kill criteria from `review_nash_territory.md` §10 are unchanged: dense census components; reps
not treatable as players; state scope binding harder than contiguity; corr(A_z,B_z) near zero.

---

## 8. Files

```
review/
  HANDOFF_REVIEW.md              this file
  review_nash_territory.md       full review, revision 2, with citations
  figures/
    disagreement_point_test.png  3 zips move; EF1 under noise; parameter box
    baseline_decision.png        EF1 knife-edge in omega; cost to each rep
  code/
    dzero.py                     nash_exact_d — outer approximation with explicit (da,db);
                                 drop-in for territory.nash_exact. Self-test in __main__
                                 validates against the paper and brute force.
    omega.py                     asym_nash — asymmetric Nash; recovers the implied omega
    omega2.py                    stability of the implied omega across parameters and noise
    ef1_test.py                  brute-force EF1 counterexample search
    retire.py / retire2.py       the d=0 comparison and its robustness sweeps
    coupling.py                  symbolic proof that headroom and baseline are independent
    coupling4.py / coupling5.py  incentive direction; the §4 correction
    decide.py                    the decision table
    probe3.py / probe4.py        Appendix B power analysis; sensitivity disambiguation
    mkfig.py / figdec.py         figure generation
    implicit_parameter_audit_kernel.py
                                 generic helpers: recover_implied_value,
                                 implied_value_stability, property_frontier, decision_table
```

**Running the code.** Needs numpy, scipy (>=1.9 for `scipy.optimize.milp`), networkx, sympy,
matplotlib. Scripts expect `/tmp/z50.pkl`, produced by `python ../code/zip50.py`. Several
scripts `sys.path.insert` their own directory, so run them from `review/code/`. `dzero.py` and
`omega.py` are the two worth keeping; the rest are evidence for specific claims.

**Method note.** The pattern in §2 — embed a contested default in a parameterised family,
recover the value the default implicitly equals, test whether that value is stable — is general.
It is what turned a philosophical objection into a decision. `implicit_parameter_audit_kernel.py`
carries model-agnostic helpers for it (each takes a `solve` callable). In Claude Science this is
published as the `implicit-parameter-audit` skill; elsewhere, use the file directly.

---

## 9. Opening prompt for the new chat

> I am reviewing and implementing a fair territory-division model for a merger of two annuity
> wholesaling forces. Read `HANDOFF.md` first for the model, settled decisions and code
> inventory, then `review/HANDOFF_REVIEW.md` for an adversarial review that reversed one of
> those decisions — the disagreement point is now zero, not pre-merger production — and lists
> what remains open. My data is a networkx graph of ZCTAs with Rook adjacency and per-node firm
> sales and opportunity. I want to start with [the census / objection 2 / the paper edits].

**Note on tooling.** The review findings came from executing the model a few thousand times —
brute-force enumeration, MILP sweeps across parameter grids, resampling under noise. If the next
chat is drafting paper text, any Claude chat will do. If it is settling objection 2 or running
the census, it needs a Python environment with scipy and a MILP solver.
