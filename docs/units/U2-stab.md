# Unit U2-stab — is the delivered roster stable, and does the question have an answer before it is computed?

Status: done

**Status 2026-09-03 (A1 track, `wt/A1`): landed** (hub, `VERIFY_U2-stab` 13/13). Its blocking test is now 169 comparisons and moves into U6-sel. See `docs/foundations/BRIEF.md` §4.

## Spec (verbatim from `docs/foundations/LIT_economic-theory.md`:§0.4 and §3)

> **Q3 is not vacuous, and the answer sharpens N3.** Under aligned preferences (both sides rank
> by the same `u_i(A_j)`) the stable matching is **unique** and is the *greedy* top-pair matching
> (**eeckhout2000**, **clark2006**), which is **not** the max-weight matching. So the delivered
> Hungarian-on-logs roster is generically *unstable* and the blocking-pair enumeration will find
> pairs — N3 is decisive, not vacuous, and **echenique2024** shows why: stability and efficiency
> are *different members* of one optimal-transport family indexed by an inequality parameter.

And the absence this unit is asked to close, verbatim from `docs/foundations/LIT_economic-theory.md`:§Absence
ledger, row A5:

> **A5.** No published statement, with counterexample, that a max-weight matching under aligned
> (common pair-value) preferences need not be stable. […] **eeckhout2000** + **clark2006** imply
> it (SPC ⇒ unique stable matching = greedy top-pair, which differs from max-weight);
> **echenique2024** proves stability and efficiency are different members of one OT family. The
> one-line counterexample is *derivable* from these in two steps but is not written down. Cite the
> two and derive it; do not cite anything for the counterexample itself.

## Files owned

- `docs/MODEL_U2-stab.md`
- `docs/VERIFY_U2-stab.md` (written by `math-verify`)
- `tools/verify/U2-stab/**`

## Files forbidden

Every other unit's owned files · `docs/foundations/FRAME.md` · `docs/foundations/BRIEF.md` · `docs/foundations/LENS_*.md` ·
`docs/foundations/DOMAIN_*.md` · `docs/foundations/LIT_economic-theory.{md,bib}` (read-only; **do not append citations** —
that is U0-lit's and the bibliography skill's job) ·
`docs/RESEARCH_ADDITIONS.bib` · `docs/channel_note/**` · `CLAUDE.md` · all of `td/`, `tests/`,
`tools/`, `figures/`, `battery/`.

## Agent → verifier

`modeler` → `math-verify`

## Acceptance

`math-verify` returns **VERIFIED or REFUTED** on all three, with a runnable artifact:

- **P1 (the induced market is aligned).** Under `DOMAIN_economic-theory.md` §2.4's construction —
  territory `j` ranks wholesalers by `u_i(A_j)`, wholesaler `i` ranks territories by the same
  `u_i(A_j)` — the profile satisfies `eeckhout2000`'s Sequential Preference Condition, hence the
  stable matching is unique and equals the greedy top-pair matching. **State the tie-breaking
  hypothesis explicitly** (SPC needs strictness; ties among the 111 are plausible) and say what
  breaks without it. Cite `clark2006` for the weaker No Crossing Condition as the fallback if the
  `ρ` compactness term perturbs exact alignment; cite `consuegra2013` for the boundary —
  **never write "unique iff"**, SPC is sufficient only.
- **P2 (the counterexample).** An explicit smallest instance on which greedy top-pair ≠ Hungarian
  max-weight-on-logs, with both matchings computed and the blocking pair exhibited. This is
  absence A5 closed by derivation. Two forms are wanted and both are cheap: one on raw weights,
  one on **log** weights (the delivered roster maximises `Σ_i log g_{i,σ(i)}`, not `Σ_i g_{i,σ(i)}`
  — check whether the log changes the answer, since a monotone transform of the *pair values*
  leaves the ordinal preferences and hence stability untouched while changing the max-weight
  optimum).
- **P3 (the decisive prediction).** State, as a prediction the pending N3 measurement will confirm
  or refute: the delivered roster is unstable **unless** greedy happens to coincide with Hungarian
  on this instance, and that coincidence is itself a one-line check that should be N3's first line
  (`LIT_economic-theory.md` §3, `eeckhout2000` entry).

Also required, at PLAUSIBLE-or-better:

- **P4 (across the boundary).** One section on `aignerhorev2022`'s **envy-free matching** — no
  unmatched agent envies a matched one — as the fairness axiom for the 98, which
  `DOMAIN_economic-theory.md` §2.1 says it "cannot say" anything about and §2.6 substitutes a
  bankruptcy analogy for. State whether the delivered roster's EFM status is decidable by the same
  `13 × 111` sweep as the blocking-pair enumeration, and note the caveat the literature carries
  (the notion is ordinal and carries no Nash-welfare guarantee — absence A3).

## Numbers to compute first

From `DOMAIN_economic-theory.md` §5, **blocked on ★6** (no instance in this worktree, no code
against `td/`). For each, state the threshold that would flip the conclusion:

| §5 # | number | what this unit must state about it |
|---|---|---|
| N3 | blocking-pair count over `13 × 111` under induced preferences | the prediction (P3) and what a count of **zero** would mean — that greedy coincided with Hungarian here, which is information, not a null result |
| N2 | whether `ρ = 0` in the delivered artifact | whether exact alignment holds, hence whether SPC or only NCC applies |

Numbers this unit **may** compute: everything in P2, on its own toy instances (3–4 agents is
enough), under `tools/verify/U2-stab/`.

## Inputs to read (paths and sections only)

- `docs/foundations/DOMAIN_economic-theory.md` §2.4 (the method and the induced-preference construction), §3
  item 4, §5 N3, §8 Q4
- `docs/foundations/LIT_economic-theory.md` §0.4, §3 in full (`echenique2024`, `eeckhout2000`, `clark2006`,
  `consuegra2013`, `niederle2009`), §2 (`aignerhorev2022`, `gan2019`), absence ledger rows A3 and
  A5
- `docs/foundations/LIT_economic-theory.bib` (read-only — the keys to cite)
- `~/resources/economic-theory/FOUNDATIONS.md` — `Gale & Shapley 1962`, `Roth & Sotomayor 1990`,
  `Roth 1982`, `Roth 1984`
- `docs/MODEL.md` (what `u_i(A_j)` is), `docs/PROBLEM.md` §3 (stage 2 as Hungarian on logs)
- `docs/foundations/FRAME.md` §2 (the reversibility row — why an unstable roster matters), §3 (the acceptance
  test, which currently has **no** stability criterion)
- Read-only: `td/channel.py` around the rectangular Hungarian match (`:288`) — to confirm what is
  actually maximised. **Read only.**

## Open questions for ★0

- **★3 — should roster stability be a hard requirement?** This unit does **not** answer it and
  must not assume it. Adding a stability criterion is a scope change to FRAME §3's acceptance
  test and is the user's call. This unit's job is to establish that the question is live, so the
  user can be asked with evidence rather than in the abstract.
- **★1 (A2)** — if the 98 are *released* rather than retained, the outside option changes and the
  induced preferences may not be the right ones. Note the dependency; do not wait on it, the
  alignment argument is unaffected.
- **★6** — N3 and N2 stay predictions until it is lifted.

## Branch

`wt/U2-stab` (from `wt/workflow-dryrun`)

## Stop rule

`echenique2024`'s EC record is a **conference abstract**; the full text is arXiv:2402.13378 and
`LIT_economic-theory.md` records that its citation graph could not be walked. If a claim needs the
full paper, fetch it and say so, or mark the claim as resting on the abstract — **do not
paraphrase a result from a title or an abstract as though it were read**.

If P1 fails because ties break SPC on any realistic profile, that is the result: report "the
uniqueness argument does not apply, and stability must be checked directly" rather than patching
the hypothesis. Do **not** extend into computing the stable roster for the real instance, into the
nucleolus/least-core branch (that is U6-sel), or into recommending whether stability should
override welfare — `DOMAIN_economic-theory.md` §2.4 explicitly says that trade-off is a business
call.

**stop and report rather than improvise**

## Model

From `docs/MODEL_U2-stab.md` (2026-09-02). Answer in one line: the question is live, it is
*cheaper* than DOMAIN §3 item 4 thinks (169 comparisons, not 1,443), and its expected answer is
**not** the one `LIT_economic-theory.md` §0.4 predicts: at the actual 111-of-13 shape the
max-weight roster coincides with the unique stable roster far more often than the square-market
intuition behind "generically unstable" suggests.

**Propositions, grouped under the four acceptance items.**

- **P1 — the induced market is aligned, and what follows.** P1.1: the pair value is
  `g_{ij} = B_j + w·b_{ij}`, `w = (1−λ)(1−θ) > 0`, `ρ` does not appear. `[proved]` P1.2: the
  greedy top-pair matching `σ^G` is stable. `[proved]` P1.3: under H1+H2+H3 the stable matching is
  unique and equals `σ^G` (`eeckhout2000`'s SPC, `consuegra2013` for the boundary, `clark2006`'s
  NCC held in reserve). `[proved]` P1.4: H2, not distinctness, is the hypothesis to check;
  distinctness is false by construction. `[proved]`
- **P2 — the counterexample (absence A5, closed by derivation).** P2.1: the smallest shape on
  which greedy can differ from max-weight is `n = k = 2`. `[proved]` P2.2/P2.3: minimal witnesses,
  exhaustively (max entry 4 for the log form, 5 for the strict raw form). `[proved by computation]`
  P2.4: the derivation A5 asked for in two lines — the stable set depends only on ordinal data,
  the max-weight objective is cardinal. `[proved]` P2.5: on `2×2`, the log audit subsumes the raw
  one. `[proved]`, checked on 2,433,600 integer matrices, 0 violations. P2.6: P2.5 is a `2×2`
  artefact; it fails at `n ≥ 3`. `[proved by counterexample]`
- **P3 — the decisive prediction for N3.** P3.1: zero blocking pairs iff `σ^H = σ^G`. `[proved]`
  P3.2: if they differ, the first-deviation greedy pair blocks. `[proved]` P3.3: none of the 98
  unselected reps can ever block — the `13 × 111` sweep is really `13 × 13`. `[proved]` P3.4: the
  prediction and a correction to `LIT_economic-theory.md` §0.4 — the frequency of greedy
  coinciding with Hungarian-on-logs rises with `n`; on the structured toy the coincidence rate is
  0.80. `[conjectured for the real instance]` P3.5: what a count of zero means — not a null
  result, it says `σ^H = σ^G`. `[proved]`
- **P4 — across the selection boundary: envy-free matching.** P4.1: EFM is decidable from the
  same sweep, plus `d` (the outside-option vector), which does not exist. `[proved, given the
  instantiation]` P4.2: EFM is strictly stronger than the stability condition it resembles, and
  gets nothing free from N3. `[proved]` P4.3: on this instance EFM and full staffing are probably
  incompatible. `[proved, conditional on H1]` P4.4: the caveat the literature carries — EFM
  carries no Nash-welfare guarantee. `[cited: aignerhorev2022, gan2019]`

**Numbers computed** (§4; `tools/verify/U2-stab/stab.py`, seed 20260902, ≈31 s, exact integer
arithmetic).

| # | quantity | value |
|---|---|---|
| 1–3 | minimal max entries separating greedy/log-Hungarian, greedy/raw-Hungarian, raw-stable-but-log-unstable | `4`, `5`, `5` |
| 6 | exhaustive test of P3.3 on 3×2 matrices | 46,656 matrices; 0 unmatched-rep blocking pairs |
| 7–8 | structured 111×13 toy: ties, H2, blocking | 56,872 tied cell-pairs; H2 holds 13/13 rounds; 1 blocking pair |
| 9 | 200-replicate toy | greedy = log-Hungarian in 160/200 (80.0 %) |
| 10–11 | iid genericity / slack sweep at `k=13` | agreement `0.011 → 0.700` as `n: 13 → 111`; mean blocking pairs `4.63 → 0.35` |
| 12–13 | `w` at reference parameters / hold-vs-not swing | `0.42` / `0.4217` (FRAME §6's `≈42 %`, `|Δ| = 0.0017`) |
| 14 | cells the N3 sweep can skip a priori | 1,274 of 1,443; decisive sub-matrix `13×13 = 169` |

**Not computed, and deliberately:** N2 and N3 themselves — `instance_descaled.json.gz` was absent
from the worktree; everything about the real roster in §2 is a prediction, labelled as such.

**Open.** ★3 (should stability be a hard requirement?) is not answered, by instruction; N2 and N3
remain predictions until measured on the instance; Roth 1982's two-sided strategy-proofness
obstruction under uniqueness is not settled; P3.4's transfer to the real `g` depends on the real
`b_{ij}` sparsity; `d`, the outside-option vector, does not exist, so P4 stays conditional.

Full report: `git show 8b14eee:docs/MODEL_U2-stab.md`.

## Verify

From `docs/VERIFY_U2-stab.md` (2026-09-02, `math-verify`). **No row is REFUTED.** Two
documentation caveats are raised (rows 4 and 9); both are under-specification of auxiliary
numbers, not errors in the propositions they support.

| # | proposition | verdict |
|---|---|---|
| 1 | P1.1 `g_ij = B_j + w·b_ij`, `w=(1−λ)(1−θ)`, `ρ` absent | **VERIFIED** |
| 2 | P1.2 greedy is stable | **VERIFIED** |
| 3 | P1.3 under H1+H2+H3 stable set = `{σ^G}` | **VERIFIED** |
| 4 | P3.3 no unmatched rep blocks a max-weight roster | **VERIFIED (with caveat)** — the auxiliary counts 2,187/3,672 are tie-break dependent; P3.3's own content (0/0) is tie-break invariant |
| 5 | P2.4 stability ordinal, max-weight cardinal | **VERIFIED** |
| 6 | P3.1/P3.2 zero blocking iff `σ^H=σ^G`; first-deviation pair blocks | **VERIFIED** |
| 7 | P2.5 the 2×2 lemma | **VERIFIED** |
| 8 | P2.6 P2.5 fails at `n ≥ 3` | **VERIFIED** |
| 9 | P2.2/P2.3 minimality (max entry 4, 5, 5) | **VERIFIED (with caveat)** — P2.2's raw threshold of 5 depends on the distinctness hypothesis; without it, 4 suffices |
| 10 | P4.2/P4.3 EFM strictly stronger; EFM ∧ full staffing infeasible | **VERIFIED** |
| 11 | P1.4 tie identity, H2 vs distinctness on the toy | **VERIFIED** |
| 12 | P3.4 the ensemble frequencies | **VERIFIED (ensembles only)** — the transfer to the real `g` stays `[conjectured]` (blocked on the instance) |
| 13 | row 13 — `w·τ/(c2·τ+λ)` vs FRAME §6's 0.42 | **VERIFIED** |

No literature was fetched or checked — every `[cited: …]` attribution is outside this
verification; only mathematical content was checked. N2 and N3 themselves were not computed
(instance absent from the worktree).

**Artifacts**, moved out of the deleted per-unit artifacts directory to `tools/verify/U2-stab/`:
`verify_core.py`, `verify_row1_P11.py`, `verify_row23_P12_P13.py`,
`verify_row45_P33_P24.py`, `verify_row4_tiebreak_bracket.py`, `verify_row6_P31_P32.py`,
`verify_row7_P25.py`, `verify_row8_13.py`, `verify_row9_P22_P23.py`, `verify_row10_P42_P43.py`,
`verify_row11_P14.py`, `verify_row12_P34.py`.

Full report: `git show 8b14eee:docs/VERIFY_U2-stab.md`.

## Code verify

none yet
