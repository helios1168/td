# Unit U4-disp — displacement as a certificate *(wave 2, gated on U0-lit — not launched)*

## Spec (verbatim from `docs/DOMAIN_optimization.md`:§2.4)

> **Assumptions.** That a *lower* bound on displacement-to-any-better-coverage can be read from
> the §2.2 duals. **This is the one genuinely unproved step in this plan** — it needs either a
> literature result (§6, "stability radius / inverse optimization") or a `math-verify` unit
> establishing a modulus `objective-gap ≥ φ(mass moved)`. Without it, displacement is a
> *descriptive* metric only.

`DOMAIN_optimization.md` §8 Q3 calls this **"the single highest-leverage unknown in the plan"**:
everything about acceptance in business units (FRAME §3.5, §10.7, and both lenses' units
complaint) rests on it.

## Files owned

`docs/MODEL_U4-disp.md` · `docs/VERIFY_U4-disp.md` · `docs/artifacts/U4-disp/**`

## Files forbidden

Every other unit's owned files · `docs/FRAME.md` · `docs/BRIEF.md` · `docs/LENS_*.md` ·
`docs/DOMAIN_*.md` · `docs/channel_note/**` · `CLAUDE.md` · all of `td/`, `tests/`, `tools/`,
`figures/`, `battery/`.

## Agent → verifier

`modeler` → `math-verify`

## Acceptance

VERIFIED or REFUTED on: a modulus `objective-gap ≥ φ(mass moved)` for the coverage problem, with
`φ` explicit and its hypotheses stated — **or** a clean impossibility/absence statement, in which
case acceptance stays in nats and FRAME §3.5 is answered instead by translating a branch-and-bound
gap through the near-equality rung `Δ ≈ ½Σδ_j²` (`REVIEW_GROMOV` R2). A REFUTED verdict here is a
real deliverable: it closes D4.

Second required statement: displacement *between two given maps* is a transportation problem
(`Hitchcock1941`, TU-integral) and is always available — separate the **descriptive** metric,
which is free, from the **bound**, which is what is in question. `LENS_GROTHENDIECK.md` §5a's
diagnosis — that a nat-tolerance on a second-order-flat functional is self-defeating *by
construction* — must be stated as the motivation and checked, not assumed.

## Numbers to compute first

`DOMAIN_optimization.md` §5 #8 — displacement (zips and `M`-mass) between the dots map and the
cells map, which converts the 4.66e-5-nat non-decision into a first-order quantity. **Blocked on
★6.** State the threshold at which the two maps become distinguishable in displacement.

## Inputs to read (paths and sections only)

`docs/DOMAIN_optimization.md` §2.4, §8 Q3, §4 D4 · `docs/LENS_GROTHENDIECK.md` §5a, descent 4 and
7 · `docs/FRAME.md` §3 (acceptance criterion 5), §6 (the tier floors), §10 Q4 and Q7 ·
`docs/REVIEW_GROMOV.md` R2 · **`docs/LIT_optimization.md` §Q7 — the gate** ·
`~/resources/optimization/FOUNDATIONS.md` (`Hitchcock1941`, `Schrijver1986`, `Chvatal1983`,
`GaleKuhnTucker1951`)

## Open questions for ★0

**★6.** Also gated on **U0-lit Q7**: if the search returns a stability-radius or inverse-
optimization result that already gives the modulus, this unit becomes a citation-and-instantiation
unit (size S) rather than a proof unit (size L). Do not launch before U0-lit reports.

## Branch

`wt/U4-disp` (from `wt/workflow-dryrun`)

## Stop rule

If no modulus exists and none can be proved, **stop and report the absence** — do not invent a
weaker metric to have something to deliver. The absence is what D4 needs.

**stop and report rather than improvise**
