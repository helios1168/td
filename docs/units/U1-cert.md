# Unit U1-cert — does the Eisenberg–Gale dual subsume the four existing certificates?

## Spec (verbatim from `docs/DOMAIN_optimization.md`:§3 and §2.2)

> **Verification handed to `math-verify`:**
> […]
> - that the fractional relaxation's value upper-bounds every integral coverage with the same
>   roster (§2.2) — the lens marks this `[claim, immediate but unverified]`;
> - that the four existing certificates are degenerations of §2.2's dual at `u_i ≡ λM` (Groth §3
>   descent) — **this is the "five collapse into one" claim and it is the load-bearing one**;
> - the `≤ k−1` split-zip descent, if §6 does not return a citation.

Supporting statement of the object, verbatim from `docs/LENS_GROTHENDIECK.md`:§"The general case,
stated":

> **Fibre.** For a staff set `S`, the relaxation over fractional assignments `X` supported on `S`
> is concave; it is the Eisenberg–Gale program of the Fisher market `(S, Z, M, budgets ≡ 1, u)`
> penalised by `ρ·C`. Its value upper-bounds every integral coverage with `im σ = S` `[claim]`;
> its duals are prices on `Z`; at a basic optimum at most `|S| − 1` units are split `[standard]`.
>
> **Degeneration.** At `u_i ≡ λM` for all `i` the fibres become isomorphic and staff-independent;
> the optimum is `k·log(λM(Z)/k)` — the analytic balance ceiling — every equal-mass partition
> attains it, and the `ρ`-term selects a power diagram of the centers with the duals as weights.

## Files owned

- `docs/MODEL_U1-cert.md` (the model; created by `modeler`)
- `docs/VERIFY_U1-cert.md` (the verdict; created by `math-verify`)
- `docs/artifacts/U1-cert/**` (throwaway runnable artifacts — the toy instances and the symbolic
  or numeric checks `math-verify` requires)

## Files forbidden

Every other unit's owned files (`docs/MODEL_U2-stab.md`, `docs/MODEL_U3-inv.md`,
`docs/LIT_optimization.md`, `docs/RESEARCH_ADDITIONS.bib`, …) · `docs/FRAME.md` ·
`docs/BRIEF.md` · `docs/LENS_*.md` · `docs/DOMAIN_*.md` · `docs/RESEARCH_FINDINGS.md` ·
`docs/REVIEW_GROMOV.md` · `docs/channel_note/**` · `CLAUDE.md` · **all of `td/`, `tests/`,
`tools/`, `figures/`, `battery/`** (read-only at most; this unit writes no project code) ·
`instance_descaled.json.gz` (absent from this worktree; do not go looking for it in the main
checkout).

## Agent → verifier

`modeler` → `math-verify`

## Acceptance

`math-verify` returns **VERIFIED or REFUTED** (not INCONCLUSIVE) on **both** of the following,
each backed by a runnable artifact under `docs/artifacts/U1-cert/`:

- **P1 (the relaxation bound).** For a fixed staff set `S`, `EG_S ≥ V(π,σ)` for every integral
  coverage with `im σ = S` — stated with its hypotheses, including what `ρ > 0` does to it
  (`DOMAIN_economic-theory.md` §2.1 failure mode (i) warns the fairness reading lapses at `ρ > 0`;
  state whether the *bound* does too).
- **P2 (the collapse).** Each of the four existing certificates — the analytic balance ceiling,
  the integer balance floor, assignment optimality at pinned centers, and `cert_power_diagram` —
  is a degeneration or restriction of `EG_S`'s dual, obtained by a **named** specialisation
  (`u_i ≡ λM`; `ρ` on/off; centers pinned). A certificate that does *not* arise this way must be
  named as such — a partial collapse is a legitimate and useful result, an unstated one is not.

Additionally required, at PLAUSIBLE-or-better standing:

- **P3 (the integrality gap in value, not count).** The `≤ k−1` split-unit bound is a *count*.
  `DOMAIN_economic-theory.md` §2.2 failure mode: FRAME §6 records the largest single zip at 1.07%
  of total `M` ≈ **14% of one territory**, so 12 splits is not obviously negligible. Give a bound
  on the *value* of the gap in terms of the largest split unit's mass, or state explicitly that
  none exists and the bound is therefore quotable only alongside the split masses.
- A one-paragraph statement of **what the bound does not cover** — misreporting, and error in `M`
  (`DOMAIN_optimization.md` §3.4).

## Numbers to compute first

From `DOMAIN_optimization.md` §5 — **all blocked on ★6 and on the instance's absence** (FRAME §5).
Do **not** attempt to reach the instance. Instead, for each, state the threshold that would flip
this unit's conclusion, so the measurement (when it runs) either confirms or refutes without
rework:

| § 5 # | number | what this unit must state about it |
|---|---|---|
| 7 | `EG_R` — the concave relaxation over all 111 reps | at what looseness the outer term of the sandwich `V ≤ max_S EG_S ≤ EG_R` becomes useless |
| — | largest split-unit mass at a basic EG optimum | the value at which P3's gap swamps the ~3.7-nat premium and the bound becomes decorative |
| 2 | spread of realized gains `g_i` vs the published 0.781% spread of `M` | which of the two the certificate is a statement about (`LENS_GROMOV.md` M3 consequence 1) |

Numbers this unit **may** compute: anything on a hand-built toy instance of its own construction
(3–5 reps, 6–12 zips) under `docs/artifacts/U1-cert/`. Toy instances are how P2's specialisations
get checked and how a refutation gets its counterexample.

## Inputs to read (paths and sections only)

- `docs/DOMAIN_optimization.md` §2.2, §3, §8 Q4 (the load-bearing framing)
- `docs/LENS_GROTHENDIECK.md` §2 (the τ-deformation and step 2), §4 (relativisation, the sandwich),
  "The general case, stated", descent 3
- `docs/LENS_GROMOV.md` Move 3 (the fibration; what the certificates certify)
- `docs/MODEL.md` (the N-way model — `u_i(z)`, `c1`, `c2`, `λ`, `θ`, the headroom condition)
- `docs/FRAME.md` §6 (the four certificate numbers; the 1.07% largest zip), §10 Q3
- `docs/REVIEW_GROMOV.md` R3 (the EG bound as "certificate 5" — this unit's claim is that it is
  not a fifth but *the* one)
- `docs/LIT_economic-theory.md` §1 and §2 (`atkinson1970` for the fibration identity — **cite, do
  not re-derive**; `budish2011` for the honest approximate-CEEI form of the equal-budget claim)
- `docs/LIT_optimization.md` §Q1/§Q5 **if U0-lit has landed** — otherwise proceed and mark the
  `≤ k−1` descent as proved-here-pending-citation
- Read-only, for the four certificates' actual contracts: `td/solvers/cert_draw.py`,
  `td/channel.py::allocate_districts`. **Read only. No edits.**

## Open questions for ★0

- **★6** — if code against the instance is later permitted, this unit's P3 threshold becomes a
  measurement rather than a conditional.
- Not a blocker but worth surfacing on report: if P2 **refutes** — the four certificates do not all
  collapse — then `LENS_GROTHENDIECK.md`'s central reframing is weaker than it reads
  (`DOMAIN_optimization.md` §8 Q4) and the note keeps its five-certificate structure. Report that
  in those words; do not soften it.

## Branch

`wt/U1-cert` (from `wt/workflow-dryrun`)

## Stop rule

If P1 turns out to require a hypothesis the instance may not satisfy (e.g. strict positivity of
every `g_i`, or `ρ = 0`), **state the hypothesis and stop** — do not weaken the claim until it is
provable, and do not assume the instance satisfies it. If P2 collapses three of four certificates
and the fourth resists, report three-of-four with the obstruction named; do not force the fourth.
If the `≤ k−1` descent cannot be proved and U0-lit has not returned a citation, mark it
**open** and carry P1/P2 without it — it is a supporting fact, not a premise.

**stop and report rather than improvise**
