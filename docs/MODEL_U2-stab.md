# Model — unit U2-stab — is the delivered roster stable, and does the question have an answer before it is computed?

**Date:** 2026-09-02 · **Framework:** 0.1-dev ·
**Reads:** `docs/units/U2-stab.md`, `docs/DOMAIN_economic-theory.md` §2.4/§3/§5/§8,
`docs/LIT_economic-theory.md` §0.4/§2/§3/absence ledger A3+A5, `docs/LIT_economic-theory.bib`,
`~/resources/economic-theory/FOUNDATIONS.md` (Gale & Shapley 1962, Roth 1982, Roth 1984,
Roth & Sotomayor 1990), `docs/MODEL.md` §1, `docs/CHANNEL.md` §3, `docs/FRAME.md` §2/§3/§5/§6,
`td/channel.py` (read-only) ·
**Unit:** `docs/units/U2-stab.md` · **Artifacts:** `docs/artifacts/U2-stab/`

**Answer in one line.** The question is live, it is *cheaper* than DOMAIN §3 item 4 thinks
(169 comparisons, not 1,443), and its expected answer is **not** the one
`LIT_economic-theory.md` §0.4 predicts: at the actual 111-of-13 shape the max-weight roster
coincides with the unique stable roster far more often than the square-market intuition
behind "generically unstable" suggests.

---

## 1. Setup (symbol table)

Every symbol is defined here once. Values marked *(FRAME §6)* are reference values from
`docs/FRAME.md` §6; values marked *(code)* are read from `td/channel.py`.

| symbol | meaning | units | reference value |
|---|---|---|---|
| `I` | the wholesalers, `\|I\| = n` | — | `n = 111` *(FRAME §6)* |
| `J` | the districts drawn at stage 1, `\|J\| = k` | — | `k = 13` *(FRAME §6)* |
| `A_j ⊂ Z` | the zips of district `j`; `{A_j}` partitions the 1,229 sold zips | — | 1,229 zips *(FRAME §6)* |
| `S_i(z)` | rep `i`'s booked production at zip `z` | share of `M_z` | — |
| `T_z` | `Σ_i S_i(z)`, all booked production at `z` | share of `M_z` | — |
| `S_free(z)` | vacancy ("filler") book at `z` | share of `M_z` | 2 zips *(FRAME §6)* |
| `M_z` | opportunity at `z` | `M/median(M)` | — |
| `θ` | transfer capture | dimensionless | `0.40` *(FRAME §6 / CLAUDE.md)* |
| `λ` | headroom credit | dimensionless | `0.30` *(ibid.)* |
| `c1, c2` | `1−λ`, `θ(1−λ)` | dimensionless | `0.70`, `0.28` *(code)* |
| `c_free` | filler-capture coefficient, mode-dependent | dimensionless | `c2` (default) *(code)* |
| `w` | `c1 − c2 = (1−λ)(1−θ)`, the rep-dependent weight | dimensionless | `0.42` (E7) |
| `u_i(z)` | `c1·S_i(z) + c2·(T_z−S_i(z)) + c_free·S_free(z) + λ·M_z` | utility | — |
| `g_{ij}` | pair value `Σ_{z∈A_j} u_i(z)` — the **stage-2 gain matrix** | utility | `111 × 13` *(code)* |
| `B_j` | `Σ_{z∈A_j} [c2·T_z + c_free·S_free(z) + λ·M_z]`, rep-independent | utility | — |
| `b_{ij}` | `Σ_{z∈A_j} S_i(z)`, rep `i`'s book inside district `j` | book | — |
| `σ` | the **roster**: an injection `J → I`, `σ(j)` staffs `j` | — | delivered by `channel.match` |
| `μ` | `σ⁻¹`, partial: `μ(i)` is `i`'s district or `⊥` | — | — |
| `σ^H` | the **delivered roster**: `argmax_σ Σ_j log g_{σ(j),j}` (Hungarian on logs) | — | *(code)* |
| `σ^G` | the **greedy top-pair** matching (§3, P1.2) | — | — |
| `d_i` | rep `i`'s outside option (value of *not* being selected) | utility | **unknown — FRAME A2** |
| `τ` | aggregate saturation `Σ booked / Σ opportunity` | dimensionless | `0.419` *(FRAME §6, measured)* |
| `ρ` | compactness weight | nats / edge | stage-1 only — see P1.1 |
| N2, N3 | DOMAIN §5 numbers: "is `ρ = 0`", blocking-pair count | — | **both blocked on ★6** |

**Induced preferences (DOMAIN §2.4).** District `j` ranks reps by `g_{ij}` descending; rep `i`
ranks districts by the same `g_{ij}` descending. One function generates both sides — this is
*aligned* preferences in the sense of **echenique2024** / **niederle2009**.

**Blocking pair.** `(i,j)` blocks `σ` iff `[μ(i)=⊥ or g_{ij} > g_{i,μ(i)}]` **and**
`g_{ij} > g_{σ(j),j}`. `σ` is **stable** iff no pair blocks it.

**Hypotheses, named once and carried explicitly.**

- **H1 (individual rationality / all districts staffed).** `d_i < min_j g_{ij}` for every rep,
  i.e. every wholesaler prefers any territory to non-selection. This is FRAME §3 criterion 3's
  *"the unselected are named as not selected, not as released"* read as a preference statement,
  and it is **FRAME A2, unconfirmed** (★1).
- **H2 (per-round strictness).** At each of the `k` greedy rounds the argmax over the surviving
  `I_r × J_r` is unique. Strictly weaker than "all `g_{ij}` distinct", which is **false here by
  construction** (P1.4).
- **H3 (alignment).** Both sides rank by one common pair value. Proved, not assumed (P1.1).

---

## 2. Propositions (numbered, labeled)

Grouped under the four acceptance items of `docs/units/U2-stab.md`.

### P1 — the induced market is aligned, and what follows

- **P1.1 — the pair value is `g_{ij} = B_j + w·b_{ij}`, with `w = (1−λ)(1−θ) > 0`, and `ρ`
  does not appear.** `td/channel.py::gain_matrix` accumulates, per zip, a rep-independent
  term plus `(c1−c2)·S_i(z)`. Consequently H3 holds **exactly, at every `ρ ≥ 0`**: `ρ` acts on
  the stage-1 partition, not on the stage-2 pair value, so once `{A_j}` is fixed the market is
  aligned whatever drew it. `[proved]`
- **P1.2 — the greedy top-pair matching `σ^G` is stable.** Under H1 and H3, with `k ≤ n`.
  Requires no strictness; ties are harmless for this half. `[proved]`
- **P1.3 — under H1 + H2 + H3 the stable matching is *unique* and equals `σ^G`.** `[proved]`
  — the published one-to-one statement is **eeckhout2000**'s Sequential Preference Condition
  (aligned profiles satisfy SPC; SPC ⇒ uniqueness ⇒ the top-top-pair matching); the market here
  is *unbalanced* (111 vs 13) with an outside option, which is why the proof is given directly
  rather than quoted `[cited: eeckhout2000]`. **consuegra2013** shows SPC is **sufficient
  only** — false already at `n = 3` as a necessary condition — so this model never writes
  "unique iff". `[cited: consuegra2013]` **clark2006**'s No Crossing Condition is the weaker
  sufficient condition to fall back on **if** alignment is ever perturbed; P1.1 says it is not
  perturbed by `ρ`, so NCC is held in reserve for the travel-cost variant (§5 item 8), not used
  here. `[cited: clark2006]`
- **P1.4 — H2, not distinctness, is the hypothesis to check; distinctness is false by
  construction.** Any two reps with no book in `A_j` satisfy `g_{ij} = g_{i'j} = B_j` exactly.
  On a structured toy of the delivered shape there are **56,872** tied cell-pairs within
  district columns and 1,222 of 1,443 cells are zero-book, yet the argmax is unique at all 13
  rounds (E5), and at 200/200 replicates (E5b). `[proved]` (the tie identity)
  `[proved by computation]` (the toy counts).

### P2 — the counterexample (absence A5, closed by derivation)

- **P2.1 — the smallest shape on which greedy can differ from max-weight is `n = k = 2`.** At
  `k = 1` greedy and max-weight both return `argmax_i g_{i1}` for any strictly increasing
  weight. `[proved]`
- **P2.2 — minimal witnesses, exhaustively.** With four *distinct* positive integers (so that
  preferences are strict), max entry 4 is forced, and **8 of the 24 arrangements** separate
  greedy from Hungarian-on-logs; the first is `[[1,2],[3,4]]` (greedy product 4, log-optimum 6,
  blocking pair (rep 1, district 1)). For a **strict** raw-weight separation the minimal max
  entry is **5**, first witness `[[1,3],[4,5]]` (greedy sum 6, raw optimum 7). `[proved by
  computation]` (exhaustive)
- **P2.3 — the log form is not the raw form: a roster that is stable on raw weights is
  unstable on log weights.** Minimal witness `[[1,2],[3,5]]` (max entry 5, 8 witnesses at that
  max): raw-Hungarian = greedy = stable, sum 6 > 5, **zero** blocking pairs; log-Hungarian
  ≠ greedy, product 6 > 5, **one** blocking pair (rep 1, district 1). Since the delivered
  artifact maximises `Σ log g`, this is the form that applies. `[proved by computation]`
- **P2.4 — the derivation A5 asks for, in two lines.** (i) The stable set depends only on the
  *ordinal* data: for any strictly increasing `φ`, `g` and `φ∘g` have identical blocking
  predicates and hence identical stable sets. (ii) `argmax_σ Σ_j φ(g_{σ(j),j})` is *cardinal*
  and moves with `φ`. Therefore a max-weight matching agrees with the unique stable matching
  only by coincidence, and **which** coincidence depends on `φ` — the monotone transform leaves
  the stability question untouched while moving the optimum. `[proved]`
- **P2.5 — on `2 × 2`, the log audit subsumes the raw one.** If greedy is the log-max-weight
  (product) matching then it is also the raw-max-weight (sum) matching. Equivalently: raw
  instability implies log instability. `[proved]`, and checked on **2,433,600** integer
  matrices with entries ≤ 40 and unique per-round argmax: **0 violations**.
  `[proved by computation]`
- **P2.6 — P2.5 is a `2 × 2` artefact; it fails at `n ≥ 3`.** Random search finds
  151 / 191 / 140 violations in 133,333 trials at `n =` 3 / 4 / 5, with an explicit `3 × 3`
  witness on which the *log* roster is stable and the *raw* roster is not. So at `k = 13`
  neither audit substitutes for the other, and the audit that matters is the log one.
  `[proved by counterexample]`

### P3 — the decisive prediction for N3

- **P3.1 — zero blocking pairs ⟺ the delivered roster is the greedy roster.** Under
  H1 + H2 + H3, `σ^H` has no blocking pair iff `σ^H = σ^G`. `[proved]` (immediate from P1.2
  and P1.3.)
- **P3.2 — if they differ, the first-deviation greedy pair blocks, and is a one-line
  certificate.** Let `r` be the first greedy round with `σ^H(j_r) ≠ i_r`; then `(i_r, j_r)`
  blocks `σ^H`. `[proved]` On the structured toy this is exactly the single blocking pair
  found (E5: first deviation at round 6 of 13, pair (rep 8, district 2), and the enumerated
  blocking set is `{(8,2)}`). `[proved by computation]`
- **P3.3 — none of the 98 can ever block: the `13 × 111` sweep is really `13 × 13`.** A
  max-weight matching for **any** strictly increasing weight (raw or log) admits no blocking
  pair whose rep is unmatched — swapping the unmatched rep in would strictly raise the
  objective. Hence **1,274 of the 1,443 cells of the sweep are non-blocking a priori** and only
  the `13 × 13` sub-matrix on the selected reps can fire. `[proved]`, and checked exhaustively
  on all 46,656 `3 × 2` integer matrices with entries ≤ 6: 2,187 raw and 3,672 log rosters have
  a blocking pair, **0** have one involving an unmatched rep. `[proved by computation]`
  *This sharpens DOMAIN §3 item 4 and DOMAIN §5 N3, and it is the reason P4 is needed: stability
  is structurally silent about the selection margin.*
- **P3.4 — the prediction, and a correction to `LIT_economic-theory.md` §0.4.** §0.4 says the
  delivered roster is "generically unstable" and the enumeration "will find pairs". That reading
  is a *square-market* intuition. Holding `k = 13` and growing `n`, on iid pair values the
  frequency with which greedy coincides with Hungarian-on-logs rises monotonically
  **0.011 → 0.098 → 0.226 → 0.435 → 0.609 → 0.700** at `n =` 13, 20, 30, 50, 80, 111, and the
  mean blocking-pair count falls **4.63 → 0.35**; on the structured (common-baseline +
  sparse-book) toy of the delivered shape the coincidence rate is **0.80** with mean 0.245 and
  max 2 blocking pairs. **Prediction:** N3 returns a *small* count — most likely 0, 1 or 2, and
  certainly not the dozens a square market would give. `[conjectured]` — the ensembles are
  `[proved by computation]` statements about simulated matrices; the transfer to the real
  instance is the conjecture, and a counterexample would live in a real `g` whose book term
  `w·b_{ij}` is much more evenly spread across districts than the toy's 1-to-3-districts-per-rep
  sparsity.
- **P3.5 — what a count of zero means.** Not a null result: by P3.1 it says `σ^H = σ^G`, i.e.
  the max-log-weight roster *is* the unique stable roster — the strongest available outcome,
  and one that closes DOMAIN §8 question 4 (★3) in the affirmative for free. The one-line check
  that should be N3's first line is therefore *compute `σ^G` and compare*, not *enumerate*.
  `[proved]` (given P3.1)

### P4 — across the selection boundary: envy-free matching

- **P4.1 — EFM is decidable from the same sweep, plus one thing nobody has.**
  **aignerhorev2022** defines an envy-free matching on a bipartite *acceptability* graph (no
  unmatched agent envies a matched one), proves one always exists — **possibly empty** —
  characterises the maximum one and gives a polynomial algorithm `[cited: aignerhorev2022]`.
  Instantiating it here needs an acceptability relation, and the only defensible one is
  `j acceptable to i ⟺ g_{ij} > d_i`. Given `d`, the predicate reads off the same `13 × 111`
  matrix as N3 in the same sweep. Without `d` it does not: with `d ≡ 0` every pair is
  acceptable and all `98 × 13 = 1,274` unmatched cells are envy instances, so the notion fires
  vacuously. **EFM is decidable by the N3 sweep iff FRAME A2 is resolved into a `d` vector.**
  `[proved]` (given the instantiation)
- **P4.2 — EFM is strictly stronger than the stability condition it resembles, and gets
  nothing free from N3.** EFM ⇒ no blocking pair involving an unmatched rep; the converse
  fails (any `g_{ij} ∈ (d_i, g_{σ(j),j}]` is envy without blocking). But by **P3.3** the
  consequent is *automatic* for the delivered roster. Therefore `N3 = 0` carries **zero**
  information about EFM. `[proved]`
- **P4.3 — on this instance EFM and full staffing are probably incompatible.** With all 13
  districts staffed, EFM holds iff `g_{ij} ≤ d_i` for every unselected `i` and every `j` —
  i.e. no non-selected wholesaler finds any territory better than the residual channel. If any
  one does, the maximum envy-free matching is the **empty** matching, which FRAME §3
  criterion 3 forbids. So EFM is an axiom the programme cannot satisfy, and that is a property
  of `k`-of-`n` selection, not a defect of the draw — precisely absence **A3**.
  `[proved, conditional on H1]`
- **P4.4 — the caveat the literature carries.** EFM is ordinal/threshold-based and carries no
  Nash-welfare guarantee; **gan2019**'s `m < n` house-allocation results are unit-demand only
  and bound rather than solve the bundle-valued version. The bundle-valued, Nash-welfare
  version of the selection-boundary axiom does not exist (absence **A3**).
  `[cited: aignerhorev2022, gan2019]`

---

## 3. Proofs and sketches

**P1.1.** `td/channel.py::gain_matrix` sets `c1 = 1−λ`, `c2 = θ(1−λ)`, `c_free ∈ {c2, c1, λ}`
by mode, and for each zip `z ∈ A_j` accumulates
`common(z) + (c1−c2)·S_i(z)` with `common(z) = c2·T_z + c_free·S_free(z) + λ·M_z`.
Summing over `z ∈ A_j` gives `g_{ij} = B_j + w·b_{ij}` with `B_j = Σ_{z∈A_j} common(z)`,
`w = c1−c2 = (1−λ)(1−θ)`, `b_{ij} = Σ_{z∈A_j} S_i(z)`. `w > 0` for `λ<1, θ<1`. Both induced
rankings are generated by this one function, so H3 holds. `ρ` occurs nowhere in `gain_matrix`
or `match`; it enters only the stage-1 draw that fixes `{A_j}`. ∎
*Corollary used below:* district `j`'s ranking over reps is by `b_{ij}` alone (`B_j` is a
common additive constant), while rep `i`'s ranking over districts mixes `B_j` and `b_{ij}`.

**P1.2 (greedy is stable).** Greedy runs `k` rounds; at round `r` it picks
`(i_r, j_r) ∈ argmax {g_{ij} : i ∈ I_r, j ∈ J_r}` and deletes both. Suppose `(i,j)` blocks
`σ^G`. District `j` is filled at some round `r` (all `k` are, since `k ≤ n`). Let `r` be the
*first* round at which `i` or `j` leaves the pool. At the start of round `r`, `(i,j) ∈ I_r×J_r`,
so `g_{i_r j_r} ≥ g_{ij}`. If `i_r = i`, then `g_{i,μ(i)} = g_{i_r j_r} ≥ g_{ij}`, contradicting
`g_{ij} > g_{i,μ(i)}`. If `j_r = j`, then `g_{σ^G(j),j} = g_{i_r j_r} ≥ g_{ij}`, contradicting
`g_{ij} > g_{σ^G(j),j}`. One of the two holds because `j` leaves the pool by round `k`. ∎
*(No strictness used, so ties do not break this half.)*

**P1.3 (uniqueness).** First, any stable `σ` staffs all `k` districts: if `j` were unstaffed
then, since `k ≤ n`, some rep `i` is unmatched, and `(i,j)` blocks by H1
(`g_{ij} > d_i` and `j` prefers `i` to nobody). Now induct: suppose a stable `σ` agrees with
greedy on rounds `1..r−1`. Then `σ` restricted to `J_r` is an injection into `I_r`. Let
`(i_r,j_r)` be the round-`r` greedy pair, the *unique* argmax over `I_r × J_r` by H2. If
`σ(j_r) = i' ≠ i_r`, then `i' ∈ I_r` gives `g_{i_r j_r} > g_{i',j_r}` (strict, by uniqueness of
the argmax); and either `i_r` is unmatched — so H1 gives the rep-side condition — or
`μ(i_r) ∈ J_r ∖ {j_r}` and `g_{i_r j_r} > g_{i_r,μ(i_r)}` (strict, same reason). So `(i_r,j_r)`
blocks `σ`, contradicting stability. Hence `σ(j_r) = i_r`, and by induction `σ = σ^G`. With
P1.2 the stable set is exactly `{σ^G}`. ∎
*Relation to the literature:* this is **eeckhout2000**'s SPC conclusion specialised to aligned
preferences and extended to an unbalanced market with an outside option. **consuegra2013**
forbids the converse phrasing. **clark2006**'s NCC is the weaker hypothesis to invoke if
alignment is perturbed.

**P1.4.** `b_{ij} = 0 = b_{i'j} ⇒ g_{ij} = g_{i'j} = B_j`. So exact ties are structural. H2
constrains only the `k` round-maxima, which are the book-heavy cells; E5/E5b show the two
coexist on a toy of the delivered shape. ∎

**P2.1.** At `k = 1`, both greedy and `argmax_σ Σ φ(g_{σ(j),j})` reduce to
`argmax_i φ(g_{i1}) = argmax_i g_{i1}` for strictly increasing `φ`. ∎

**P2.4.** The blocking predicate is a conjunction of strict comparisons `g_{ij} > g_{i,μ(i)}`
(within a row) and `g_{ij} > g_{σ(j),j}` (within a column); a strictly increasing `φ` preserves
every such comparison. So the stable set is invariant. The objective `Σ_j φ(g_{σ(j),j})` is
not: P2.3 exhibits `φ = log` changing the argmax. ∎
*This is the two-step derivation the absence ledger says is derivable but unwritten: (1)
aligned ⇒ unique stable = greedy (**eeckhout2000**); (2) greedy is ordinal, max-weight is
cardinal.*

**P2.5.** Let the `2 × 2` matrix be positive with maximum entry `p`; greedy takes `p` first, so
`σ^G` is the "diagonal" `{p, q}` and the only alternative is `{a, b}` with `a, b ≤ p`. Suppose
`pq > ab` (greedy strictly wins on the product). Put `s = a+b ≤ 2p`. With `a ∈ [s−p, p]`,
`ab = a(s−a)` is concave, hence minimised at an endpoint, both giving `ab ≥ p(s−p)`. Then
`pq > ab ≥ ps − p²`, so `p(p+q) > ps`, so `p+q > s = a+b`: greedy also wins on the sum. ∎
Contrapositive: `p+q ≤ a+b ⇒ pq ≤ ab`, i.e. raw instability ⇒ log instability, on `2 × 2`.

**P2.6.** The witness is exhibited (E3, `n = 3`): greedy = log-Hungarian while
raw-Hungarian differs and carries a blocking pair. The endpoint-minimisation step in P2.5 has
no `n ≥ 3` analogue — a permutation can improve the sum through a chain of three cells without
improving the product — and that is exactly the step the counterexample breaks. ∎

**P3.1.** `⇐` is P1.2. `⇒`: if `σ^H` is stable then by P1.3 it is the unique stable matching,
which is `σ^G`. ∎

**P3.2.** By construction `σ^H` agrees with greedy on rounds `1..r−1`, so `σ^H` restricted to
`J_r` is an injection into `I_r`, and `σ^H(j_r) ∈ I_r ∖ {i_r}`. The two strict inequalities of
P1.3's induction step then apply verbatim. ∎

**P3.3.** Let `σ` maximise `Σ_j φ(g_{σ(j),j})` over injections `J → I`, `φ` strictly
increasing. Suppose `(i,j)` blocks with `i ∉ im σ`. Define `σ'` equal to `σ` except
`σ'(j) = i`; `σ'` is a valid injection because `i` was unused. The objective changes by
`φ(g_{ij}) − φ(g_{σ(j),j}) > 0` since `g_{ij} > g_{σ(j),j}`. This contradicts optimality of
`σ`. ∎ *(Both `φ = id` and `φ = log` are covered, so the statement holds for the raw and the
delivered log objective alike.)*

**P4.2.** EFM ⟺ `∀ i ∉ im σ, ∀ j: g_{ij} ≤ d_i` (all districts are staffed). A blocking pair
with unmatched `i` needs `g_{ij} > d_i` (H1) and `g_{ij} > g_{σ(j),j}`; the first is already
denied by EFM. Converse: pick `d_i < g_{ij} ≤ g_{σ(j),j}` — envy, no block. And by P3.3 the
consequent holds for `σ^H` regardless, so it is uninformative. ∎

**P4.3.** If some unselected `i` and district `j` have `g_{ij} > d_i`, then any matching that
staffs `j` is not envy-free. Since every matching that satisfies FRAME §3 criterion 3 staffs
all 13, no such matching is EFM; **aignerhorev2022**'s guaranteed EFM is then the empty one. ∎

---

## 4. Numbers computed

All from `docs/artifacts/U2-stab/stab.py`, seed **20260902**, single command line

```
/Users/ntlee/projects/td/.venv/bin/python3 docs/artifacts/U2-stab/stab.py \
    > docs/artifacts/U2-stab/stab_results.json
```

Python 3.13.15 · numpy 2.5.2 · scipy 1.18.1 · macOS (Darwin 25.6.0) · wall time ≈ 31 s.
Every minimality and exhaustiveness claim is computed in **exact integer arithmetic**
(products and sums of `int`, `Fraction` for products); floats appear only in E6/E6c/E7.

| # | quantity | value | block |
|---|---|---|---|
| 1 | minimal max entry, 2×2 distinct-int, greedy ≠ log-Hungarian | **4**, 8 of 24 arrangements; witness `[[1,2],[3,4]]`, products 4 vs 6, blocking pair (1,1) | E1 |
| 2 | minimal max entry, 2×2 distinct-int, greedy ≠ raw-Hungarian *strictly* | **5**, 8 witnesses; `[[1,3],[4,5]]`, sums 6 vs 7, blocking pair (1,1) | E1b |
| 3 | minimal max entry, raw-roster stable **but** log-roster unstable | **5**, 8 witnesses; `[[1,2],[3,5]]`, sums 6 > 5, products 5 < 6; blocking pairs raw **0**, log **1** | E2 |
| 4 | 2×2 exhaustive test of P2.5 (entries ≤ 40, unique per-round argmax) | **2,433,600** matrices, **0** violations | E3 |
| 5 | violations of P2.5 at `n =` 3 / 4 / 5 (133,333 trials each) | **151 / 191 / 140**; explicit 3×3 witness recorded | E3 |
| 6 | exhaustive test of P3.3 on 3×2 matrices, entries ≤ 6 | **46,656** matrices; rosters with a blocking pair: raw **2,187**, log **3,672**; with an *unmatched-rep* blocking pair: **0 / 0** | E4 |
| 7 | structured 111×13 toy: exact ties within district columns | **56,872** tied cell-pairs; **1,222 / 1,443** cells zero-book | E5 |
| 8 | same toy: per-round argmax unique (H2) | **13 of 13 rounds**; blocking pairs of `σ^H`: **1**, at the first-deviation greedy pair (round 6, rep 8, district 2) | E5 |
| 9 | structured toy over 200 replicates | greedy = log-Hungarian in **160/200 (80.0%)**; mean blocking pairs **0.245**, max **2**; H2 held **200/200** | E5b |
| 10 | iid genericity, `frac(greedy = log-Hungarian)` at 2×2 / 4×2 / 13×13 / 111×13 | **0.797 / 0.882 / 0.011 / 0.692** | E6 |
| 11 | slack sweep, `k = 13` fixed, `n =` 13/20/30/50/80/111 (4,000 trials each) | agreement **0.011 / 0.098 / 0.226 / 0.435 / 0.609 / 0.700**; mean blocking pairs **4.63 / 2.43 / 1.49 / 0.84 / 0.50 / 0.35**; max **15 / 9 / 7 / 5 / 8 / 5** | E6c |
| 12 | `w = c1 − c2` at the reference `θ = 0.40, λ = 0.30` | **0.42** | E7 |
| 13 | implied hold-vs-not swing at the measured `τ = 0.419` | **0.4217** vs FRAME §6's reported **0.42** (difference 0.0017) | E7 |
| 14 | cells of the N3 sweep that P3.3 rules out a priori | **1,274 of 1,443** (`98 × 13`); decisive sub-matrix **13 × 13 = 169** | P3.3 |

Row 13 is a consistency check, not a new measurement: FRAME §6's measured "hold-vs-not swing
≈ 42%" is recovered from `w·τ / (c2·τ + λ)` at the reference parameters, which confirms that
the rep-dependent part of `g` is a **first-order term**, not a perturbation — the market is
non-degenerate and the stability audit is not vacuous.

**Not computed, and deliberately:** N2 and N3 themselves. `instance_descaled.json.gz` is absent
from this worktree (FRAME §5) and ★6 is not lifted. Everything about the real roster in §2 is a
prediction, labelled as such.

---

## 5. Failure modes

| # | trigger (FRAME §5 gap / §6 bound) | what breaks | how it degrades |
|---|---|---|---|
| 1 | **★6** — no instance in this worktree (FRAME §5, last bullet) | N2 and N3 unmeasured | everything in P3 stays a prediction; P1, P2, P3.1–P3.3 and P4 are instance-independent and survive |
| 2 | **6-significant-figure export rounding** (FRAME §5) | manufactures ties at relative `1e-6`; **H2** may fail spuriously | test H2 at a relative tolerance ≥ `1e-6`, never on exact float equality. If H2 fails, P1.3's *uniqueness* lapses; P1.2 survives, so "delivered ≠ greedy" no longer implies unstable and the **direct `13 × 13` enumeration becomes the only test** — which is cheap. Report as "the uniqueness argument does not apply, and stability must be checked directly" |
| 3 | **`θ → 1` or `λ → 1`** (FRAME §6 reference `θ = 0.40`; `θ` is the un-identified parameter) | `w = (1−λ)(1−θ) → 0`, `g_{ij} → B_j`, every rep values every district identically, **no blocking pair can exist** and the audit is vacuous — DOMAIN §2.4's own stated failure mode | threshold: vacuous to within export precision when `w · spread_i(b_{ij}) < 10⁻⁶ · B_j`, i.e. `θ > 1 − 10⁻⁶·B_j / ((1−λ)·Δb_j)`. At the reference parameters row 13 shows a 42% modulation, four orders from that threshold — not live now, but it moves with the `θ` identification work |
| 4 | **FRAME A2 unconfirmed** (★1) — the 98 released rather than retained | **H1** fails for pairs with `d_i ≥ g_{ij}`; a stable matching may leave a district unstaffed, conflicting with FRAME §3 criterion 3 | H3 (alignment) is **unaffected** — run greedy on the acceptable sub-market and report unstaffed districts as a finding. P4 is blocked outright: without `d` there is no EFM predicate |
| 5 | **6 of 1,229 zips placed by state after the draw** (FRAME §5) | `A_j` changes after the draw, so `g` changes | audit the **placed** map, not the drawn one; structure untouched |
| 6 | **`--repair-headroom`** path (FRAME §5) | repaired `S_i`/`M_z` shift `g` values | values move, `g = B_j + w·b` form and all of §2 survive |
| 7 | `ρ > 0` in the delivered artifact (**N2**) | nothing here | P1.1: `ρ` is absent from `gain_matrix`. **N2 does not gate this unit** — it gates DOMAIN §2.1's EF1 claim, which is another unit's |
| 8 | a rep-specific term added to the pair value (travel cost `−κ·d(i,j)`, CLAUDE.md W11) | **H3 fails for any `κ > 0`**; the market stops being aligned and P1.2/P1.3 lapse | this is where **clark2006**'s No Crossing Condition is the fallback — and it must be *checked*, not assumed; **echenique2024**'s OT family is the frame for what replaces the single stable point |
| 9 | the toy sparsity in E5/E5b is invented | P3.4's transfer to the real instance | P3.4 is the only `[conjectured]` item; if the real `b_{ij}` is far denser, the coincidence rate falls toward the `13 × 13` square value (0.011) and blocking counts rise |

**Stop-rule compliance.** `echenique2024`'s EC record is a conference abstract and the full text
(arXiv:2402.13378) was **not** fetched or read for this unit. No proposition here rests on it;
it is cited once, in §5 row 8, for framing only, and its content is reported no further than
`docs/LIT_economic-theory.md` §3 records.

---

## 6. What this says about the problem in FRAME's terms

- **FRAME §2, the reversibility row.** "Low. A one-shot decision that must be defensible line by
  line." A blocking pair is precisely a line that is not defensible: a named wholesaler and a
  named territory that both prefer each other to what they were given. **Roth 1984** is the
  field evidence that stability, not efficiency, decides whether an assignment survives
  `[cited: Roth 1984]`, and **niederle2009** supplies the mechanism *in this preference
  structure*: under aligned preferences with complete information the parties renegotiate an
  announced unstable outcome toward the stable one themselves `[cited: niederle2009]`. The
  existence-and-algorithm backdrop is **Gale & Shapley 1962** with **Roth & Sotomayor 1990** as
  the standard reference `[cited: Gale & Shapley 1962, Roth & Sotomayor 1990]`.
- **FRAME §3's acceptance test has no stability criterion.** This unit does **not** recommend
  adding one — that is ★3 and DOMAIN §8 question 4, the user's call. What it supplies is the
  evidence to ask with: the question is well-posed (P1), non-vacuous (row 13), decidable in
  **169 comparisons** rather than 1,443 (P3.3), and answerable by a *one-line* check before any
  enumeration (P3.5).
- **FRAME §3 criterion 5 — "nobody signs a nat".** Stability is the one criterion on the list
  that needs no translation into business units: its output is a list of (wholesaler,
  territory) pairs, or the empty list. That is already the currency of the room.
- **FRAME §3 criterion 3 — "the unselected are named as not selected, not as released"** is
  hypothesis **H1**, and FRAME **A2** is unconfirmed. The acceptance test therefore already
  contains, unlabelled, the assumption this unit's stability argument runs on.
- **FRAME §6's measured saturation (41.9%) is what keeps the audit alive.** At the earlier
  assumed 5% saturation the rep-dependent term `w·b_{ij}` would have been a few percent of
  `B_j` and the market would have been near-degenerate in the sense of §5 row 3. At 41.9% it is
  a 42% modulation (row 13), so preferences genuinely differ across reps and blocking pairs are
  possible.
- **The selection margin is outside stability's reach.** P3.3 proves the 98 can never form a
  blocking pair with a max-weight roster. Anything the programme wants to say to the
  non-selected must come from the envy side (P4) — and P4.3 says the honest answer there is
  that envy-freeness across the boundary is unattainable jointly with full staffing. That is
  absence **A3**, and it is the formal version of DOMAIN §2.6's bankruptcy analogy.

---

## 7. Handoff to `math-verify`

Ordered by how much the unit's result depends on the proposition.

| # | proposition | expected mode | independent oracle |
|---|---|---|---|
| 1 | **P1.1** — `g_{ij} = B_j + w·b_{ij}`, `w = (1−λ)(1−θ)`, `ρ` absent | SYMBOLIC | re-derive by symbolic expansion of the `gain_matrix` accumulation loop (sympy, symbolic `S_i, T_z, M_z`) against `td/channel.py:266–283`; assert `∂g_{ij}/∂ρ = 0` by absence of the symbol |
| 2 | **P1.2** — greedy is stable | SYMBOLIC + NUMERIC | brute force: enumerate all injections `J → I` on random `n ≤ 7, k ≤ 3` instances, verify `σ^G` is in the stable set every time |
| 3 | **P1.3** — under H1+H2 the stable set is `{σ^G}` | SYMBOLIC + NUMERIC | same enumeration, assert `|stable set| = 1`; and assert `> 1` on instances constructed to violate H2 (deliberate ties at a round argmax) |
| 4 | **P3.3** — no unmatched rep can block a max-weight roster | SYMBOLIC | exhaustive re-enumeration of `3×2` and `4×2` integer matrices with an *independent* matching implementation (brute force over injections, not scipy), for `φ ∈ {id, log, √, x³}` |
| 5 | **P2.4** — stability is invariant under strictly increasing `φ`, max-weight is not | SYMBOLIC | random instances; compute the stable set by brute force under `g` and under `φ∘g` for several `φ`, assert equal; assert the max-weight argmax differs for at least one `φ` |
| 6 | **P3.1 / P3.2** — zero blocking ⟺ `σ^H = σ^G`; first-deviation pair blocks | SYMBOLIC + NUMERIC | brute force on toys; independently recompute the first-deviation round and check membership in the enumerated blocking set |
| 7 | **P2.5** — the `2 × 2` lemma | SYMBOLIC | sympy: given `p ≥ a,b > 0`, `q > 0`, `pq > ab`, derive `p+q > a+b` (or refute); cross-check by exhaustive rational enumeration |
| 8 | **P2.6** — P2.5 fails at `n ≥ 3` | NUMERIC | verify the recorded `3 × 3` witness by hand-checkable arithmetic: recompute both objectives over all 6 permutations |
| 9 | **P2.2 / P2.3** — minimality of the witnesses (max entry 4, 5, 5) | NUMERIC | independent exhaustive enumeration with a different matching implementation; confirm no separating matrix exists at a smaller max entry |
| 10 | **P4.2 / P4.3** — EFM strictly stronger; EFM ∧ full staffing infeasible | SYMBOLIC | small explicit instances with a stated `d` vector; truth table of (EFM, blocking-with-unmatched, all-staffed) |
| 11 | **P1.4** — tie identity, and H2 vs distinctness on the toy | NUMERIC | recount ties by an independent grouping; re-run E5 at three other seeds |
| 12 | **P3.4** — the ensemble frequencies | NUMERIC | re-run E6c with a different RNG family and seed; check each fraction lies inside a 99% binomial CI of the reported value |
| 13 | row 13 — `w·τ/(c2·τ+λ) = 0.4217` vs FRAME §6's 0.42 | NUMERIC | recompute symbolically in sympy at `θ=0.40, λ=0.30, τ=0.419` |

---

## 8. Open (what this unit could not settle)

1. **★3 — should stability be a hard requirement on the roster?** Not answered, by instruction.
   DOMAIN §8 question 4 and FRAME §3 both leave it to the user; this unit only establishes that
   the question is live, cheap and decidable.
2. **N2 and N3 remain predictions** until ★6 is lifted. This unit computed neither and must not
   be read as having done so.
3. **Whether Roth 1982's two-sided strategy-proofness obstruction binds when the stable matching
   is unique.** `[cited: Roth 1982]` states that no stable mechanism is strategy-proof for both
   sides and that deferred acceptance is strategy-proof for the proposing side only. Whether
   uniqueness (P1.3) weakens that obstruction is **not settled by anything read for this unit**,
   and no claim is made. It belongs with DOMAIN §2.7, another unit's.
4. **No characterisation of when the raw and log audits agree at `n ≥ 3`.** P2.5 is a `2 × 2`
   result and P2.6 refutes its extension; the general structure is open.
5. **P3.4's transfer to the real `g`** depends on the real `b_{ij}` sparsity, which is ★6.
6. **`echenique2024`'s optimal-transport family** — the claim that stability and efficiency are
   different members of one family indexed by an inequality parameter, and its identification
   with §1's Atkinson `ε` — rests on a conference abstract and was not read in full. Nothing
   here is built on it, and building on it requires fetching arXiv:2402.13378.
7. **`d`, the outside-option vector**, does not exist. Without it P4 is a conditional, and the
   EFM computation cannot be run even when ★6 lifts.
8. Explicitly **not** entered, per the stop rule: computing the stable roster for the real
   instance; the nucleolus / least-core branch (U6-sel); and any recommendation on whether
   stability should override welfare.
