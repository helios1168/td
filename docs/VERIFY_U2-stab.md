# Verification — `docs/MODEL_U2-stab.md` §7 handoff table

**Verifier:** `math-verify` · **Date:** 2026-09-02 · **Branch:** `wt/workflow-dryrun`
**Interpreter:** `/Users/ntlee/projects/td/.venv/bin/python3` — Python 3.13.15 · sympy 1.14.0 ·
numpy 2.5.2 · scipy 1.18.1 · networkx 3.6.1 · macOS (Darwin 25.6.0)
**Artifacts:** `docs/artifacts/U2-stab/verify_*.py` (this unit owns that directory).
Every script is standalone, seeded, and exits non-zero on failure.

**Independence rule applied throughout.** `docs/artifacts/U2-stab/stab.py` is the *claiming*
implementation and is never used as its own witness. All matchings in the verification are
recomputed by `verify_core.py` — brute-force enumeration over every injection `J → I`, exact
integer/`Fraction` arithmetic, no scipy. Where the instance is too large for enumeration
(rows 11, 12) the Hungarian oracle is cross-checked against an independent **networkx Blossom**
max-weight matching before use.

## Summary

| # | proposition | verdict | one line |
|---|---|---|---|
| 1 | **P1.1** `g_ij = B_j + w·b_ij`, `w=(1−λ)(1−θ)`, `ρ` absent | **VERIFIED** | sympy replay of the `gain_matrix` loop closes to 0 in all 3 filler modes; 540 numeric configs against the real `td/channel.py`; `rho` occurs nowhere in `channel.py` |
| 2 | **P1.2** greedy is stable | **VERIFIED** | 12,000 (matrix, tie-break) pairs, `n≤7, k≤3`, 6,423 of them with a tied round argmax — 0 unstable; all-ties matrices too |
| 3 | **P1.3** under H1+H2+H3 stable set = `{σ^G}` | **VERIFIED** | 2,230 H2-instances: stable set is exactly `{σ^G}`, over injections *and* over all partial matchings; both H1 and H2 shown load-bearing by explicit counterexamples |
| 4 | **P3.3** no unmatched rep blocks a max-weight roster | **VERIFIED** *(with caveat)* | exhaustive 3×2 (46,656), 4×2 (65,536), 3×3 (262,144), `φ ∈ {id, log, √, x³}`, over **all** argmax rosters: 0/0. Caveat: the auxiliary counts 2,187 / 3,672 are tie-break dependent |
| 5 | **P2.4** stability ordinal, max-weight cardinal | **VERIFIED** | stable set invariant under 6 strictly increasing `φ` on 3,000 instances; argmax moves on 199 of them; a strictly decreasing `φ` breaks it |
| 6 | **P3.1 / P3.2** zero blocking ⟺ `σ^H=σ^G`; first-deviation pair blocks | **VERIFIED** | 5,699 H2-instances × 4 `φ`; 1,798 deviating rosters, first-deviation pair in the blocking set every time; also holds for 36,631 arbitrary injections |
| 7 | **P2.5** the 2×2 lemma | **VERIFIED** | closed symbolically by an exact identity `p+q−(a+b) = (pq−ab+(p−a)(p−b))/p`; 521,850 rationals; 2,433,600 integer matrices reproduced exactly, 0 violations |
| 8 | **P2.6** P2.5 fails at `n ≥ 3` | **VERIFIED** | all 6 permutations of the recorded 3×3 witness recomputed by hand-checkable integers: log roster stable, raw roster unstable at `{(2,2)}`; independent RNG reproduces the ~1e-3 violation rate at n=3,4,5 and 0 at n=2 |
| 9 | **P2.2 / P2.3** minimality (max entry 4, 5, 5) | **VERIFIED** *(with caveat)* | independent exhaustive enumeration reproduces every threshold, witness and count. Caveat: P2.2's raw threshold of 5 depends on the *distinctness* hypothesis — without it, 4 suffices |
| 10 | **P4.2 / P4.3** EFM strictly stronger; EFM ∧ full staffing infeasible | **VERIFIED** | 11,342 (instance, partial-matching) pairs: EFM ⇒ no unmatched-rep block, never the converse; under H1 with `n>k` the only EFM is the empty one; H1 shown load-bearing |
| 11 | **P1.4** tie identity, H2 vs distinctness on the toy | **VERIFIED** | tie identity symbolic; 56,872 ties and 1,222/1,443 zero-book cells recounted by an independent all-pairs grouping; H2 13/13; blocking set `{(8,2)}` at round 6; H2 holds at 3 further seeds |
| 12 | **P3.4** the ensemble frequencies | **VERIFIED** *(ensembles only)* | different RNG family (Mersenne Twister) + seed + vectorised greedy: all 6 E6c fractions inside the 99% binomial CI, all 6 mean blocking counts within 5%, monotonicity reproduced. The *transfer* to the real `g` stays `[conjectured]` (★6) |
| 13 | row 13 — `w·τ/(c2·τ+λ)` vs FRAME §6's 0.42 | **VERIFIED** | exact rational `8799/20866 = 0.421690788843094`, matches `stab.py` to 1e-15, rounds to 0.4217, `|Δ| = 0.0017` |

**No row is REFUTED.** Two documentation caveats are raised (rows 4 and 9); both are
under-specification of *auxiliary* numbers, not errors in the propositions they support.

---

## Row 1 — P1.1

```
CLAIM:    For every district j and rep i,  g_ij = B_j + w·b_ij  with
          B_j = Σ_{z∈A_j}[c2·T_z + c_free·S_free(z) + λ·M_z],  b_ij = Σ_{z∈A_j} S_i(z),
          w = c1−c2 = (1−λ)(1−θ) > 0 for λ<1, θ<1; and ρ does not appear.
          Source: MODEL_U2-stab.md §2 P1.1 / §3 proof, against td/channel.py:252–286
          (the accumulation is line 283-284: `common + (c1 - c2) * s`).
MODE:     symbolic + numeric
ATTACK:   (a) all three `filler_capture` modes, not just the default `theta`;
          (b) boundary parameters θ=0, λ=0, θ=1, λ=1, θ=λ=0.99 — w collapses to 0 at θ=1
              and at λ=1, which is exactly §5 failure row 3, and the identity still holds;
          (c) the sharper corollary that B_j is *genuinely* rep-independent (B_j contains
              c2·T_z, which involves rep i's own book) — checked by proving
              g_ij − g_i'j − w(b_ij − b_i'j) ≡ 0;
          (d) 540 randomly-structured graphs run through the REAL `channel.gain_matrix`
              and compared against an independently written accumulation.
VERDICT:  VERIFIED
BASIS:    sympy `simplify(lhs−rhs) == 0` in all three modes (symbolic S_i(z), S_free(z),
          M_z, θ, λ); numeric max |Δ| ≤ 1e-12 relative on 540 configs — tight
          numeric-equality tier, well inside float round-off. `grep` confirms neither
          "rho" nor "ρ" occurs anywhere in td/channel.py, so ∂g/∂ρ = 0 by absence.
ARTIFACT: docs/artifacts/U2-stab/verify_row1_P11.py
CAVEATS:  Verified for `gain_matrix` as it stands. The `w>0` conclusion needs λ<1 AND θ<1
          strictly; the doc's own §5 row 3 already carries this.
```

## Row 2 — P1.2

```
CLAIM:    Under H1 and H3 with k ≤ n, the greedy top-pair matching σ^G is stable
          (no strictness required; ties harmless).  Source: §2 P1.2, proof §3.
MODE:     symbolic (argument) + numeric (exhaustive oracle)
ATTACK:   Ties are the obvious break, so they were forced: entry ranges as tight as
          {1,2} and {1,2,3} put a tied round argmax in 6,423 of 12,000 cases; three
          different tie-break rules (first, last, random) were run on every matrix;
          all-equal matrices at 1×1, 2×2, 3×3, 5×3 were run as the degenerate limit.
          k>n was checked to be outside the claim (no injection exists).
VERDICT:  VERIFIED
BASIS:    Independent brute force: the stable set is computed by testing the blocking
          predicate of §1 against every one of the n!/(n−k)! injections. σ^G is in it
          in 12,000/12,000 cases. Exact integer arithmetic, no tolerance.
ARTIFACT: docs/artifacts/U2-stab/verify_row23_P12_P13.py
CAVEATS:  H1 is built into the blocking predicate as the doc states it (an unmatched rep
          blocks whenever the district-side inequality holds). Sizes n ≤ 7, k ≤ 3.
```

## Row 3 — P1.3

```
CLAIM:    Under H1 + H2 + H3 the stable matching is unique and equals σ^G.
          Source: §2 P1.3, proof §3.
MODE:     symbolic (argument) + numeric (exhaustive oracle)
ATTACK:   (a) drop H2 — 1,546 of 1,770 H2-failing instances have |stable set| > 1, and an
              explicit constructed one, g = [[5,5],[5,3],[1,1]], has stable set
              {(0,1),(1,0)}. H2 is load-bearing.
          (b) drop H1 — with unmatched reps forbidden from blocking, g = [[2,4],[1,8],[9,4]]
              has 10 stable partial matchings including the empty one. H1 is load-bearing.
          (c) test the proof's *first* step directly: enumerate all PARTIAL matchings
              (districts allowed to be unstaffed), not just injections, and confirm the
              stable set is still exactly {σ^G}.
VERDICT:  VERIFIED
BASIS:    2,230 H2-satisfying instances: stable set == [σ^G] exactly, every time; and the
          partial-matching enumeration agrees on a separate 600-instance sweep. Exact
          integer arithmetic.
ARTIFACT: docs/artifacts/U2-stab/verify_row23_P12_P13.py
CAVEATS:  The eeckhout2000 / consuegra2013 / clark2006 attributions in §3 were NOT checked
          — no literature was fetched. Only the mathematical content is verified.
```

## Row 4 — P3.3

```
CLAIM:    Let σ maximise Σ_j φ(g_{σ(j),j}) over injections J→I, φ strictly increasing.
          Then no blocking pair (i,j) of σ has i ∉ im σ.  Source: §2 P3.3, proof §3.
MODE:     symbolic (argument) + numeric (exhaustive)
ATTACK:   (a) four φ, not the doc's two: id, log, √, x³;
          (b) three shapes, not one: 3×2 (46,656), 4×2 (65,536), 3×3 (262,144) — 374,336
              matrices, and for EACH matrix the predicate was tested on **every**
              max-weight roster, not just the one a solver happens to return, so the
              result is tie-break free;
          (c) strict monotonicity dropped — a constant φ immediately produces an
              unmatched-rep blocking pair (g=[[5,6],[1,2],[9,6]]), so the hypothesis is
              load-bearing, not decorative.
VERDICT:  VERIFIED
BASIS:    0 unmatched-rep blocking pairs in all 374,336 × 4 φ cases. Exact integer /
          Fraction arithmetic for id and x³; log and √ used only to select the argmax, the
          blocking predicate itself is evaluated on the raw integers. Independent
          matcher: enumeration over injections, never scipy.
ARTIFACT: docs/artifacts/U2-stab/verify_row45_P33_P24.py
CAVEATS:  **The auxiliary counts in §4 numbers-table row 6 are tie-break dependent.**
          "rosters with a blocking pair: raw 2,187, log 3,672" is not a well-defined
          quantity: it counts whichever single argmax scipy's Hungarian returns. Over ALL
          max-weight rosters the brackets are raw [1,266 (all block) … 3,318 (any blocks)]
          and log [3,456 … 3,738]; a lexicographic-first tie-break gives raw 2,257 /
          log 3,590. The reported 2,187 / 3,672 sit inside the brackets and are exactly
          reproducible under scipy's tie-break, so this is docs-vs-code agreement with an
          unstated convention, not an error — but the numbers should be labelled
          "(scipy tie-break)" or replaced by the bracket.
          P3.3's own content (0 / 0) is tie-break invariant and unaffected.
          Bracket reproduction: docs/artifacts/U2-stab/verify_row4_tiebreak_bracket.py
          The 1,274-of-1,443 arithmetic (98 × 13) is checked in the row-10 artifact.
```

## Row 5 — P2.4

```
CLAIM:    (i) For any strictly increasing φ, g and φ∘g have identical blocking predicates
          and hence identical stable sets. (ii) argmax_σ Σ_j φ(g_{σ(j),j}) moves with φ.
          Source: §2 P2.4, proof §3.
MODE:     symbolic (argument) + numeric
ATTACK:   Six φ were used, including two the doc does not name — x ↦ 2^x (violently convex)
          and x ↦ x+100 (pure shift, which changes every ratio and so every product-based
          objective while preserving order). A strictly DEcreasing φ (x ↦ −x) was run as the
          negative control; it breaks the invariance, confirming (i) is not vacuous.
VERDICT:  VERIFIED
BASIS:    3,000 instances, n ≤ 6, k ≤ 3: stable_set(φ∘g) == stable_set(g) for all six φ,
          0 exceptions, exact arithmetic. Part (ii) fires on 199/3,000 instances where
          log, √ or x³ moves the argmax away from id's — so the two halves of P2.4 are
          simultaneously non-vacuous.
ARTIFACT: docs/artifacts/U2-stab/verify_row45_P33_P24.py
CAVEATS:  φ is applied entrywise and identically to all cells, which is what the claim
          says. Nothing here covers rep-specific transforms (§5 failure row 8).
```

## Row 6 — P3.1 / P3.2

```
CLAIM:    P3.1: under H1+H2+H3, σ^H has no blocking pair iff σ^H = σ^G.
          P3.2: if r is the first greedy round with σ^H(j_r) ≠ i_r, then (i_r,j_r) blocks σ^H.
          Source: §2 P3.1/P3.2, proofs §3.
MODE:     symbolic (argument) + numeric
ATTACK:   (a) both directions of the iff tested separately;
          (b) σ^H taken as the max-weight roster under four φ AND, separately, as an
              ARBITRARY injection — P3.2's proof only uses "agrees with greedy before r",
              so the stronger statement was tested on 36,631 injections;
          (c) the proof's own intermediate step ("σ^H agrees with greedy on rounds < r")
              audited independently;
          (d) H2 dropped — g=[[3,3],[1,2],[1,1],[3,1]] then has a zero-blocking roster
              (3,0) that is not the greedy roster (0,1). H2 is load-bearing.
VERDICT:  VERIFIED
BASIS:    5,699 H2-instances × 4 φ: the iff holds without exception; 1,798 deviating
          rosters, and the independently recomputed first-deviation pair is in the
          enumerated blocking set every time. Exact integer arithmetic.
ARTIFACT: docs/artifacts/U2-stab/verify_row6_P31_P32.py
CAVEATS:  None beyond the H1/H2/H3 hypotheses, which are stated.
```

## Row 7 — P2.5

```
CLAIM:    On 2×2 positive matrices with maximum entry p and greedy diagonal {p,q} against
          the alternative {a,b} (a,b ≤ p):  pq > ab ⇒ p+q > a+b, and the non-strict
          version pq ≥ ab ⇒ p+q ≥ a+b (which is the one "greedy IS the log-max-weight
          matching ⇒ greedy is the raw-max-weight matching" actually needs).
          Source: §2 P2.5, proof §3.
MODE:     symbolic + numeric
ATTACK:   The doc's proof routes through concavity of a ↦ a(s−a) and an endpoint
          minimisation. That step was replaced by a checkable closed form rather than
          trusted: `a·b − p(a+b−p) ≡ (p−a)(p−b)` (sympy residual 0), which makes the
          endpoint argument a sign statement about a product of two nonnegatives.
          Then the whole lemma reduces to the exact identity
              p + q − (a+b)  ≡  ( pq − ab + (p−a)(p−b) ) / p    (sympy residual 0),
          so with pq−ab > 0, (p−a)(p−b) ≥ 0 and p > 0 the conclusion is forced
          (`sympy.ask(Q.positive(...)) -> True`). Falsification attempts: 400,000
          randomized rational tuples including the degenerate corners a=p, b=p and q→0;
          521,850 exhaustive rationals with denominator 7; and the hypothesis a,b ≤ p was
          DROPPED, which immediately yields a counterexample (p,q,a,b) = (2,2,1,3):
          pq = 4 > ab = 3 but p+q = 4 ≤ a+b = 4. So "p is the max entry" is load-bearing.
VERDICT:  VERIFIED
BASIS:    Identity closed symbolically (residual literally 0, not merely "did not
          simplify"), plus the matching-level statement re-run exhaustively: 2,433,600
          2×2 integer matrices with entries ≤ 40 and a unique per-round argmax —
          **exactly reproducing the doc's numbers-table row 4 count** — 0 violations.
ARTIFACT: docs/artifacts/U2-stab/verify_row7_P25.py
CAVEATS:  The doc's §3 proof says "minimised at an endpoint" without exhibiting
          (p−a)(p−b) ≥ 0; the step is correct but the artifact supplies the missing line.
```

## Row 8 — P2.6

```
CLAIM:    P2.5 is a 2×2 artefact; at n ≥ 3 there is an instance whose LOG roster is stable
          and whose RAW roster is not.  Source: §2 P2.6, proof §3, witness in
          stab_results.json E3_reverse_separation_search.random["n=3"].
MODE:     numeric
ATTACK:   The recorded 3×3 witness was recomputed from scratch over ALL 6 injections in
          integer arithmetic (the full table is printed by the artifact), and both argmaxes
          were checked to be unique (no tie hiding the result). H2 was verified to hold on
          the witness, so P1.2/P1.3 genuinely apply and "the log roster is stable" is not
          an accident of a degenerate instance. Separately, the ~1e-3 violation RATE was
          re-derived with an independent RNG (python `random.Random(1234567)`, not numpy
          PCG64) and an independently written violation predicate, and n=2 was run through
          the same generator as the negative control.
VERDICT:  VERIFIED
BASIS:    g = [[2638,3920,2123],[3750,368,6698],[406,5843,7243]].
            σ^G = σ^log = (1,0,2): sum 3750+3920+7243 = 14,913, product 106,472,100,000,
                                   blocking set ∅  — stable.
            σ^raw       = (0,2,1): sum 2638+5843+6698 = 15,179 (strictly larger),
                                   product 103,241,860,132 (strictly smaller),
                                   blocking set {(2,2)} — unstable.
          Hand-checkable: 7243 > 5843 (rep 2 prefers district 2 to its own district 1) and
          7243 > 6698 (district 2 prefers rep 2 to rep 1). Raw instability WITHOUT log
          instability — the exact converse of P2.5's contrapositive.
          Independent violation rates per 20,000 trials: n=3 1.40e-3, n=4 1.05e-3,
          n=5 1.65e-3, against stab.py's 1.13e-3 / 1.43e-3 / 1.05e-3 per 133,333 — same
          order, consistent under binomial noise. n=2: 0 violations in 20,000.
ARTIFACT: docs/artifacts/U2-stab/verify_row8_13.py
CAVEATS:  The counts 151 / 191 / 140 are RNG-specific and were not reproduced literally
          (nor should they be); only the rate and the witness are verified.
```

## Row 9 — P2.2 / P2.3

```
CLAIM:    P2.2: with four DISTINCT positive integers, the minimal max entry separating
          greedy from Hungarian-on-logs is 4, realised by 8 of 24 arrangements, first
          witness [[1,2],[3,4]] (greedy product 4, log optimum 6, blocking pair (1,1));
          for a STRICT raw separation the minimal max entry is 5, first witness
          [[1,3],[4,5]] (greedy sum 6, raw optimum 7).
          P2.3: minimal max entry at which the raw roster is stable while the log roster is
          not is 5, 8 witnesses, first [[1,2],[3,5]] (sums 6 > 5, products 5 < 6, blocking
          pairs raw 0 / log 1).  Source: §2 P2.2/P2.3, §4 numbers-table rows 1–3.
MODE:     numeric (independent exhaustive enumeration)
ATTACK:   Enumerated max entry 1 through 8 from below, so "minimal" is proved by the
          absence of any witness at every smaller bound, not asserted. Two enumeration
          universes were run side by side — distinct-entry arrangements and ALL matrices
          with a unique per-round argmax — to see whether the distinctness hypothesis is
          doing work. Matching by brute-force enumeration over injections; blocking sets by
          the §1 predicate; sums and products in exact integers.
VERDICT:  VERIFIED
BASIS:    Every threshold, witness matrix, count and objective value reproduces exactly:
          log separation first at max entry 4, 8 of 24, [[1,2],[3,4]], products 4 vs 6,
          blocking set [(1,1)]; strict raw separation first at 5 (distinct), 8 witnesses,
          [[1,3],[4,5]], sums 6 vs 7; P2.3 first at 5, 8 witnesses, [[1,2],[3,5]], sums
          (6,5), products (5,6), blocking sets [] and [(1,1)].
ARTIFACT: docs/artifacts/U2-stab/verify_row9_P22_P23.py
CAVEATS:  Two scope notes on P2.2, neither an error:
          (1) "max entry 4 is forced" is true but content-free — four DISTINCT positive
              integers already force a maximum of at least 4, so minimality here is a
              restatement of the hypothesis, not a computed threshold.
          (2) The raw threshold of 5 depends on distinctness. Drop it (keep only H2) and
              strict raw separation already occurs at max entry 4:
              [[1,3],[3,4]] and its three symmetries, greedy sum 5 vs raw optimum 6.
              P2.2 states the claim under distinctness so it stands, but the sentence
              reads as if 5 were the unconditional threshold.
```

## Row 10 — P4.2 / P4.3

```
CLAIM:    P4.2: EFM ⇒ no blocking pair involving an unmatched rep; the converse fails; and
          since P3.3 makes the consequent automatic, N3 = 0 carries zero information about
          EFM.  P4.3: with all k districts staffed, EFM holds iff g_ij ≤ d_i for every
          unselected i and every j; under H1 the maximum envy-free matching is the empty
          one.  Source: §2 P4.2/P4.3, proofs §3, instantiation P4.1
          (j acceptable to i ⟺ g_ij > d_i).
MODE:     symbolic (small explicit instances) + exhaustive truth table
ATTACK:   The truth table ranges over ALL partial matchings (districts may be unstaffed),
          because P4.3's conclusion is about the maximum EFM being empty and an
          injection-only enumeration would beg the question. H1 was then dropped as the
          negative control. The "zero information" punchline was tested as a genuine
          independence claim rather than an implication.
VERDICT:  VERIFIED
BASIS:    (a) 11,342 (instance, partial matching) pairs: EFM ⇒ no unmatched-rep blocking
              pair, 0 exceptions.
          (b) Converse fails, explicit witness: g = [[5,1],[9,1]], d = (0,0),
              σ = (rep 1, unstaffed). Rep 0 finds district 0 acceptable (5 > d_0 = 0) but
              5 ≤ g_10 = 9, so it envies without blocking. 1,594 further cases generically.
          (c) P4.3: on 300 instances with n > k and d_i = min_j g_ij − 1 (H1), the ONLY
              envy-free matching is the empty one — 0 exceptions.
          (d) H1 load-bearing: g = [[10,1],[2,2],[1,1]], d = (0,100,100) admits 7 EFMs
              including fully-staffing ones.
          (e) Independence: over 3,000 H1-instances, N3 = 0 with EFM false 2,783 times and
              N3 > 0 with EFM false 217 times, and N3 = 0 with EFM true **0** times. So
              N3 = 0 is compatible with EFM failing and never certifies it.
          (f) The 98 × 13 = 1,274 arithmetic checks out.
ARTIFACT: docs/artifacts/U2-stab/verify_row10_P42_P43.py
CAVEATS:  Verified for the P4.1 instantiation (acceptability = g_ij > d_i). The
          aignerhorev2022 characterisation and polynomial algorithm were NOT checked — no
          literature was fetched. P4.4's citations are outside scope.
```

## Row 11 — P1.4

```
CLAIM:    b_ij = b_i'j = 0 ⇒ g_ij = g_i'j = B_j exactly (ties are structural, so
          distinctness is false by construction); on the structured toy of the delivered
          shape there are 56,872 tied cell-pairs within district columns and 1,222 of 1,443
          zero-book cells, yet the argmax is unique at all 13 rounds, the log roster has 1
          blocking pair, and it sits at the first-deviation greedy pair (round 6, rep 8,
          district 2).  Source: §2 P1.4, §4 numbers-table rows 7–8.
MODE:     symbolic (identity) + numeric (independent recount)
ATTACK:   The toy generator had to be reused (it defines the instance), but every COUNT was
          recomputed by a different method: ties by an all-pairs comparison within each
          column rather than stab.py's value→count dictionary; greedy by verify_core's
          brute-force round loop; the log roster by scipy's Hungarian cross-checked against
          an independent **networkx Blossom** max-weight matching (identical rosters); the
          blocking set by the §1 predicate. Then E5 was re-run at three further seeds.
VERDICT:  VERIFIED
BASIS:    56,872 tied cell-pairs (exact match), 1,222/1,443 zero-book cells (exact match),
          H2 true at all 13 rounds, blocking set exactly {(8,2)}, first deviation at round
          6 of 13 (1-indexed; 0-indexed r = 5). Three other seeds: ties 56,048 / 56,877 /
          56,380, zero-book 1,213 / 1,221 / 1,216, H2 true 3/3, and where greedy and the
          log roster differ (2 of 3) the blocking count is 1 and it is the first-deviation
          pair — P3.2 again.
ARTIFACT: docs/artifacts/U2-stab/verify_row11_P14.py
CAVEATS:  The toy's sparsity (each rep books in 1–3 districts) is invented, as the doc
          itself flags in §5 row 9. Nothing here says anything about the real b_ij.
```

## Row 12 — P3.4

```
CLAIM:    On iid pair values with k = 13 fixed, frac(greedy = Hungarian-on-logs) rises
          0.011 → 0.098 → 0.226 → 0.435 → 0.609 → 0.700 at n = 13, 20, 30, 50, 80, 111 and
          the mean blocking-pair count falls 4.63 → 0.35 (4,000 trials each); and at
          13×13 / 111×13 the E6 fractions are 0.011 / 0.692.
          Source: §2 P3.4, §4 numbers-table rows 10–11.
MODE:     numeric
ATTACK:   Everything replaceable was replaced: RNG family (python Mersenne Twister vs numpy
          PCG64), seed (777777 vs 20260902+2), greedy implementation (vectorised numpy
          masked argmax vs a pure-python double loop), and blocking-pair counting
          (broadcast boolean algebra vs a nested loop). The Hungarian oracle was validated
          against an independent networkx Blossom matching on 60 random 30×6 log-instances
          before being used at scale (0 value mismatches).
VERDICT:  VERIFIED — for the ENSEMBLE statements, which is all this row covers.
BASIS:    All six E6c fractions fall inside the 99% binomial CI of the reported value at
          N = 4,000:
             n= 13  reported 0.0110  CI [0.0068, 0.0152]  reproduced 0.0103
             n= 20  reported 0.0978  CI [0.0857, 0.1098]  reproduced 0.0980
             n= 30  reported 0.2255  CI [0.2085, 0.2425]  reproduced 0.2368
             n= 50  reported 0.4350  CI [0.4148, 0.4552]  reproduced 0.4370
             n= 80  reported 0.6092  CI [0.5894, 0.6291]  reproduced 0.6038
             n=111  reported 0.6995  CI [0.6808, 0.7182]  reproduced 0.7003
          All six mean blocking counts agree within 5% relative (4.63/4.70, 2.43/2.38,
          1.49/1.46, 0.84/0.84, 0.50/0.52, 0.35/0.36), and the monotone rise in n is
          reproduced. E6 spot-checks: 13×13 reproduced 0.0110 vs reported 0.01085;
          111×13 reproduced 0.6930 vs reported 0.692, both inside the 99% CI.
ARTIFACT: docs/artifacts/U2-stab/verify_row12_P34.py
CAVEATS:  Tolerance tier: 99% binomial CI at the reported trial count — a sampling tier,
          not a numeric-equality tier; these are Monte-Carlo numbers and the doc reports
          them to 3 decimals without an interval, which slightly overstates their
          precision (e.g. n=13's 0.011 is 0.011 ± 0.004 at 99%).
          **The proposition P3.4 itself remains `[conjectured]`.** What is verified is the
          simulated ensembles; the transfer to the real g is blocked on ★6 and no
          verification of it is possible in this worktree. The doc labels it correctly.
```

## Row 13 — the FRAME §6 consistency check

```
CLAIM:    w·τ/(c2·τ + λ) = 0.4217 at θ = 0.40, λ = 0.30, τ = 0.419, against FRAME §6's
          reported hold-vs-not swing of ≈ 42% (difference 0.0017).
          Source: §4 numbers-table row 13 and the paragraph beneath it; FRAME.md:170.
MODE:     symbolic (exact rationals)
ATTACK:   Recomputed in exact rationals rather than floats, so the 4th decimal is not a
          round-off artefact. The DEFINITION was audited, not just the arithmetic: the
          quantity was re-derived independently as (u_hold − u_not)/u_not with
          u_hold = c1·τ + λ and u_not = c2·τ + λ per unit M_z, and shown identical.
          The θ → 1 limit was taken to confirm the swing collapses to 0, i.e. that this
          number is exactly the thing §5 failure row 3 says goes vacuous.
VERDICT:  VERIFIED
BASIS:    c1 = 7/10, c2 = 7/25, w = 21/50 = 0.42 (= (1−λ)(1−θ), checked symbolically);
          swing = 8799/20866 = 0.421690788843094 exactly. Matches stab.py's recorded
          0.4216907888430941 to < 1e-15 (tight numeric-equality tier). Rounds to 0.4217;
          |0.4216907… − 0.42| = 0.00169078… = 0.0017 to 4 dp. Both reported figures stand.
ARTIFACT: docs/artifacts/U2-stab/verify_row8_13.py
CAVEATS:  FRAME §6's "≈ 42%" is itself a measured/rounded figure sourced to
          REVIEW_GROMOV R1; agreement to 0.0017 is agreement with a 2-significant-figure
          number, which is consistency, not confirmation. The doc says exactly this
          ("a consistency check, not a new measurement") and is right to.
          τ = 0.419 is taken as given from FRAME §6; it was not re-measured (★6).
```

---

## What was NOT verified

- **No literature was fetched or checked.** Every `[cited: …]` attribution — eeckhout2000's
  SPC, consuegra2013's necessity counterexample, clark2006's NCC, aignerhorev2022's EFM
  existence and algorithm, gan2019, echenique2024, Roth 1982/1984, Gale & Shapley 1962 — is
  outside this verification. Only mathematical content was checked.
- **N2 and N3 themselves.** `instance_descaled.json.gz` is absent from this worktree (★6), so
  nothing about the real `g` was computed. Every instance-dependent statement in §2 remains a
  prediction, as §4 and §8 already say.
- **`td/channel.py` was read only.** No code under test was modified.
- **Sizes.** The exhaustive legs cover n ≤ 7, k ≤ 4 (rows 2, 3, 5, 6) and n ≤ 4, k ≤ 3 with
  full entry enumeration (rows 4, 7, 9). Rows 11 and 12 run at the delivered 111 × 13 shape
  but on simulated matrices.
