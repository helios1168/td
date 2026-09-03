# Unit U6-sel — is "the 13" defensible? *(wave 2, gated on ★5 — not launched)*

**Status 2026-09-03 (A1 track, `wt/A1`): carried, re-scoped, now a `python-typed` → `code-verify` unit** (★6 lifted). Scope: the 13 × 13 audits on the delivered artifact — EF1 / FEFx-w.r.t.-band / proportionality (N1, N9), the 169-pair blocking test with each block's gain (N3, from U2-stab), closed-form Shapley of all 111 via `littlechild1973` + additivity and the least core via `deng1999` / `kern2003` (N5, N6) — per `DOMAIN_economic-theory.md` §2.1, §2.4–§2.6, §4 step 1. Files owned become `tools/measure/audits.py`, `tests/test_audits.py`, `docs/MODEL_U6-sel.md`, `docs/CODEVERIFY_U6-sel.md`. ★5 gates N5 only. Branch `wt/A1`. See `docs/BRIEF.md` §4.

## Spec (verbatim from `docs/LIT_economic-theory.md`:§0.1 and §0.2)

> **The Shapley value of the roster game has a closed form; the §2.5 Monte-Carlo hand-off to
> statistics is unnecessary.** `f(S) = Σ_z max_{i∈S} S_i(z)` is a *sum over zips of airport
> games*, and **littlechild1973** gives the exact Shapley value of an airport game
> `v(S) = max_{i∈S} c_i` in closed form. Additivity of the Shapley value […] then makes the exact
> value of all 111 players an `O(#zips · n log n)` computation — minutes, not `2^111` and no
> sampler.
>
> **The balancedness LP is the wrong first test; the right one is an integrality test, and the
> core is provably empty on a two-line instance.** **deng1999** proves that for games given by
> this class of integer programs the core is non-empty **iff** the associated LP has an integer
> optimum […]. And the coverage game's core is empty whenever two wholesalers tie on a zip
> (`f({1}) = f({2}) = f({1,2}) = 1` forces `x_1 + x_2 = 1` with `x_i ≥ 1`). **N5 can be answered
> before it is computed.**

## Files owned

`docs/MODEL_U6-sel.md` · `docs/VERIFY_U6-sel.md` · `docs/artifacts/U6-sel/**`

## Files forbidden

Every other unit's owned files · `docs/FRAME.md` · `docs/BRIEF.md` · `docs/LENS_*.md` ·
`docs/DOMAIN_*.md` · `docs/channel_note/**` · `CLAUDE.md` · all of `td/`, `tests/`, `tools/`,
`figures/`, `battery/`.

## Agent → verifier

`modeler` → `math-verify`

## Acceptance

VERIFIED or REFUTED on: (a) `f = Σ_z` (airport game), so `φ_i(f) = Σ_z φ_i(f_z)` by additivity and
each term is Littlechild–Owen's closed form — **checked against brute force on a 5-player toy
instance**, as `LIT_economic-theory.md` §5 requires before use; (b) the tie argument, i.e. an
explicit two-wholesaler instance on which the core is empty, and a statement of how generic ties
are; (c) `deng1999`'s integrality test is the right test here rather than Bondareva–Shapley, with
`goemans2004` cited on the honest cost (facility-location core non-emptiness is **NP-complete** in
general, so tractability comes from the specific formulation, not from the class) and
`chen2020coreness` on which side truncated-submodular profit games fall.

Required: the transferable-utility caveat stated once, prominently — core/Shapley machinery
applies to the **surplus game `f`**, not to `V` (a log-sum with no side payments,
`DOMAIN_economic-theory.md` §2.5). Applying it to `V` invalidates the method.

Required if the core is empty: `kern2003`'s **least core / nucleolus** as the "how far from
coalition-proof, in the objective's own units" fallback — which is the bridge making
`DOMAIN_economic-theory.md` §2.5 and §2.6 one computation instead of two narratives.

## Numbers to compute first

`DOMAIN_economic-theory.md` §5 N5 (the core test) and N6 (exact Shapley for all 111, and its
top-13 against the delivered roster). **Blocked on ★6.** State the threshold for D4: how large a
disagreement between the Shapley ranking and the welfare-optimal roster must be before leadership
has to be told which one they are signing.

## Inputs to read (paths and sections only)

`docs/DOMAIN_economic-theory.md` §2.5, §2.6, §4 step 4 (D4), §5 N5–N6, §7, §8 Q5 ·
`docs/LIT_economic-theory.md` §0.1, §0.2, §5 in full, absence row A7 · `docs/LENS_GROMOV.md`
Move 4 (the ladder — `f` is the same function read as a bound) · `docs/FRAME.md` §2 (defensible
line by line), §3 (roster criterion) · `~/resources/economic-theory/FOUNDATIONS.md`
(`Gillies 1959`, `Shapley 1967`, `Shapley 1971`, `Shapley 1953`, `Young 1985`, `Schmeidler 1969`,
`Aumann & Maschler 1985`)

## Open questions for ★0

**★5 — does the programme want to know whether the core is empty?** `LIT_economic-theory.md` §0.2
makes "no selection is coalition-proof" the *likely* answer, and `DOMAIN_economic-theory.md` §8 Q5
says decide before computing whether that is a sentence the programme is willing to write. **This
unit does not launch until ★5 is answered.** Also **★6** for N5/N6.

## Branch

`wt/U6-sel` (from `wt/workflow-dryrun`)

## Stop rule

Do not produce recommended payouts or transition packages — FRAME §7 puts compensation out of
scope and `DOMAIN_economic-theory.md` §2.6 caps that method at a single framing paragraph. If the
Shapley closed form fails its brute-force check, report the failure; do not fall back to sampling
without saying the closed form was refuted.

**stop and report rather than improvise**
