# Unit U2-stab — is the delivered roster stable, and does the question have an answer before it is computed?

**Status 2026-09-03 (A1 track, `wt/A1`): landed** (hub, `VERIFY_U2-stab` 13/13). Its blocking test is now 169 comparisons and moves into U6-sel. See `docs/tracks/A1/BRIEF.md` §4.

## Spec (verbatim from `docs/LIT_economic-theory.md`:§0.4 and §3)

> **Q3 is not vacuous, and the answer sharpens N3.** Under aligned preferences (both sides rank
> by the same `u_i(A_j)`) the stable matching is **unique** and is the *greedy* top-pair matching
> (**eeckhout2000**, **clark2006**), which is **not** the max-weight matching. So the delivered
> Hungarian-on-logs roster is generically *unstable* and the blocking-pair enumeration will find
> pairs — N3 is decisive, not vacuous, and **echenique2024** shows why: stability and efficiency
> are *different members* of one optimal-transport family indexed by an inequality parameter.

And the absence this unit is asked to close, verbatim from `docs/LIT_economic-theory.md`:§Absence
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
- `docs/artifacts/U2-stab/**`

## Files forbidden

Every other unit's owned files · `docs/FRAME.md` · `docs/BRIEF.md` · `docs/LENS_*.md` ·
`docs/DOMAIN_*.md` · `docs/LIT_economic-theory.{md,bib}` (read-only; **do not append citations** —
that is U0-lit's and the bibliography skill's job) · `docs/RESEARCH_FINDINGS.md` ·
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
enough), under `docs/artifacts/U2-stab/`.

## Inputs to read (paths and sections only)

- `docs/DOMAIN_economic-theory.md` §2.4 (the method and the induced-preference construction), §3
  item 4, §5 N3, §8 Q4
- `docs/LIT_economic-theory.md` §0.4, §3 in full (`echenique2024`, `eeckhout2000`, `clark2006`,
  `consuegra2013`, `niederle2009`), §2 (`aignerhorev2022`, `gan2019`), absence ledger rows A3 and
  A5
- `docs/LIT_economic-theory.bib` (read-only — the keys to cite)
- `~/resources/economic-theory/FOUNDATIONS.md` — `Gale & Shapley 1962`, `Roth & Sotomayor 1990`,
  `Roth 1982`, `Roth 1984`
- `docs/MODEL.md` (what `u_i(A_j)` is), `docs/CHANNEL.md` §3 (stage 2 as Hungarian on logs)
- `docs/FRAME.md` §2 (the reversibility row — why an unstable roster matters), §3 (the acceptance
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
