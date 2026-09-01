# Gromov-method review of `channel_note.tex` (2026-09-01, updated post-recon)

A structured review of the note and the formulation, run twice: against head `acb34f9`,
then re-checked against `72e5f07` (literature recon + FINDINGS §9-A1). Three moves fired
(14→5, 11, 8); the first produced a **measured correction**, verified computationally
against `instance_descaled.json.gz`. Propositions and certificates are sound as stated;
what changes is the *pricing* of the scheme around them.

---

## R1. The saturation assumption is wrong by an order of magnitude (measured)

`ceiling.py:75` hard-codes `SATURATION = 0.05`; the note's §5.1 sizing, CLAUDE.md's
"~90% of u_i" line, and FINDINGS §4C/C6 ("α ≈ 0.9 expected") all inherit it. The real
shares are in the export. Measured (2026-09-01, this review):

| quantity | assumed | measured |
|---|---|---|
| aggregate saturation Σ(T+S_free)/ΣM | 5% | **41.9%** |
| median per-zip t_z | — | **46.8%** (p90 = 110%) |
| opportunity in zips with t_z > 30% | — | **48.0%** |
| opportunity share of incumbent's u_i | 89.6% | ≈ 59% |
| hold-vs-not utility swing | 6.7% | **≈ 42%** |
| max incumbency premium / total welfare | ~6% | **≈ 25%** (bound: every zip to its top incumbent) |

The note's own threshold sentence — "at 5% the map is drawn by opportunity with a modest
continuity tilt; at 30% it would not be" — is crossed by the aggregate. Consequences:

- **§5.2's "derived rather than assumed" claim fails on the real instance.** In eq. (split),
  the incumbency term ranges over ≈ n·log(1+P/W₀) ≈ **3.7 nats** across allocations, while
  D(g) at solver-realistic imbalances (≤ a few %) is 10⁻⁴–10⁻² nats. On the region of
  interest the ordering *inverts*: the two-stage scheme survives as a business constraint
  ("territories shall be opportunity-balanced"), not as a derived consequence.
- **The optimization effort is on the smallest term.** Balance is solved to 4.5×10⁻⁵ nats;
  the 5-seed portfolio explores 7.1×10⁻² nats of staffing value; ~3.7 nats of premium swing
  between allocations is unexplored and unbounded. Elevates C3 and §9-F6 (Benders feedback).
- **Fixes needed:** `SATURATION` → measured value + rewrite §5.1's paragraph; retract
  "derived rather than assumed"; correct CLAUDE.md's sizing line; correct FINDINGS C6's
  α-expectation (ghodsi2018 near-tightness claim weakens at α ≈ 0.6).
- **A tension the recon didn't flag:** at 42% saturation the pressure to make stage 1
  book-aware is large, but §9-G's invariant ("books enter at stage 2 only", fotakis2014)
  pushes the other way — and `score_draws`/F6 already breach it mildly by selecting maps on
  book-derived value. Decision needed; audited system-of-record books (per §9-G) are the
  likely escape. The certified draw itself is untouched — Prop. equal is about the common
  measure M.

## R2. The lexicographic call (the 132 dots) is decidable by the programme's own tolerance

Two facts the FINDINGS §9-D path doesn't use:

- **Near-equality rung:** Δ ≈ ½Σδ_j², so the log objective is *second-order flat* at
  balance (ceiling gap 4.51×10⁻⁵ nats ⇔ RMS deviation 0.26% of target — worth one lemma in
  the note; it converts nats to district dollars).
- **Noise-floor argument:** the compact assignment costs 4.66×10⁻⁵ nats of stage-1 Nash —
  **two orders of magnitude below the programme's own tier-2 acceptance floor
  (5×10⁻³ nats)** — while staying inside the same deviation band. By the project's own
  tolerance, dots and cells are Nash-*indistinguishable*, and the polish's tie-break rule
  ("ties toward the more compact destination") already dictates the cells.

The one missing number before adopting: **the stage-2 staffing value of the cells map**.
At real saturation (R1) relabelling 132 zips moves g_ij materially (~42% swing per
zip-book, not 6.7%), so rescoring is mandatory, and open question 1 as posed in the note is
mis-framed — the note itself says stage-1 Nash "is not the quantity of interest"; the
tie-break criterion should be staffing value. Recommended order: C4 (measure robustness) →
stage-2 rescore of the cells → adopt unless staffing drops by more than the portfolio
spread (7.1×10⁻² nats). §9-D's frontier sweep remains the right picture to present.

## R3. The EG fractional bound (= FINDINGS C3), upgraded in priority and purpose

Independently converged with C3. Post-R1 its role is bigger than "decompose the 4.5e-5
residual": it is the **only missing upper bound in the composed retreat audit** — balance
is priced (analytic ceiling), compactness is priced conditionally (duals/MILP), the joint
(map, staffing) value has a lower bound only (59.9375 nats). One concave solve
(~16k variables, seconds), conditional on the winner's 13 staff, bounds every
(partition, staffing) pair for that staff, geometry ignored — the same epistemic role as
certificate (ii)'s constructive half. At 42% saturation the gap it measures is nats-scale.
Recommend as certificate 5.

## R4. Textual/math fixes to `channel_note.tex` (all local, none affect results)

1. **Prop. hungarian:** "injections σ from representatives to districts" don't exist for
   m > k; the proof's object (matchings saturating the smaller side) is right — fix the
   statement and note Σ_i runs over matched i.
2. **Prop. equal proof:** {m > 0 : Σm = M(Z)} is not compact (not closed); the AM–GM
   argument two sentences later is complete — drop the compactness claim.
3. **Notation collision:** n = |Z| (Lem. transport) vs n = staffed reps (eq. split/mnw).
4. **Sign:** `\chPinNash` carries its own minus sign, so §8 renders "a cost of −4.66×10⁻⁵
   nats" — reads as a gain. Make the macro positive.
5. **Free strengthening:** chNashBest 69.563143 vs ceiling 69.563145 — the portfolio itself
   proves the ceiling *reachable to within 2×10⁻⁶ nats*; upgrade "not proved: reachable".
6. §5.1's sizing paragraph: rewrite at measured saturation (R1).
7. (Concur with FINDINGS A3 on re-scoping "≤ k−1 splits" to "some basic optimum"; the run
   hitting k−1 exactly is the generic nondegenerate case, not a signal.)

## Moves that did not fire (diagnostic)

- **Move 1** (build the language): formulations are one-liners and successive
  reformulations got shorter (contiguity → band + compactness → power diagram). Healthy.
- **Move 12** (soft/hard): fires only as confirmation — certificate (ii) shows balance is
  *soft* here (2×10⁻⁶ reachable geometry-free; all seeds land < 1%), so no structure lives
  in balance refinement. The hardness sits in geometry (joint centers) and θ.
- **Move 9** (bound by the generator): no unobservable mechanism anywhere.
- **Move 3** (symmetry audit): mostly discharged — the note never applies the ceiling to
  heterogeneous g. Residual: Lloyd/transportation is paid for by squared-*Euclidean*
  geometry; the LAEA projection preserves area (right for M-weights), not distances (what
  the objective consumes). One sentence + an AK/HI handling check closes it.

## Recommended order of work

1. R1: replace the hard-coded saturation, rewrite §5.1, retract "derived", fix CLAUDE.md +
   FINDINGS C6; then decide the book-aware-stage-1 vs §9-G-invariant tension.
2. R2: C4, then stage-2 rescore of the cells map; adopt/decline by staffing value.
3. R3: EG bound as certificate 5 (= C3, upgraded).
4. R4: the seven note fixes, foldable into the §9-B citation pass.
