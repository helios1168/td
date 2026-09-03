# Unit U5-crit — the welfare criterion as one Atkinson scalar *(wave 2, gated on U2-stab — not launched)*

**Status 2026-09-03 (A1 track, `wt/A1`): retired as a unit — folded into `docs/units/U12-menu.md`.** The criterion is two knobs `(δ, ε)` on one sponsor menu (`DOMAIN_economic-theory` §2.3, §2.9, D2); the Atkinson-ε content survives as U12's second knob. See `docs/BRIEF.md` §4.

## Spec (verbatim from `docs/LIT_economic-theory.md`:§0.5)

> **The fibration `Σ log g = n log ḡ − D(g)` is a re-derivation of a 1970 result and should be
> cited, not proved.** `D(g)` is the **mean logarithmic deviation** = Theil-L = the Atkinson index
> at inequality aversion ε = 1 (**atkinson1970**, **shorrocks1980**, **foster2000**). GROM 3's
> decomposition is Atkinson's equally-distributed-equivalent identity with `g` in place of income.
> This closes GROM 3 as an original claim and opens it as a citation — and it gives D2 a
> vocabulary the sponsor already owns ("how much inequality aversion?" rather than "what exchange
> rate?").

Paired with, verbatim from `docs/DOMAIN_economic-theory.md`:§2.3:

> Economic theory's claim is that this is *not a parameter to elicit* — it is a **choice of
> criterion**, and there are exactly three defensible ones on the table: utilitarian […],
> egalitarian/leximin […], and Nash (the current one, the interpolant). Presenting the sponsor
> with three named criteria and their three maps is a *smaller* ask than eliciting an exchange
> rate.

## Files owned

`docs/MODEL_U5-crit.md` · `docs/VERIFY_U5-crit.md` · `docs/artifacts/U5-crit/**`

## Files forbidden

Every other unit's owned files · `docs/FRAME.md` · `docs/BRIEF.md` · `docs/LENS_*.md` ·
`docs/DOMAIN_*.md` · `docs/channel_note/**` · `CLAUDE.md` · all of `td/`, `tests/`, `tools/`,
`figures/`, `battery/`.

## Agent → verifier

`modeler` → `math-verify`

## Acceptance

VERIFIED on: (a) the fibration identity **is** Atkinson's ε=1 identity, stated with the citation
and *not* re-proved as programme work; (b) the three criteria are ε = 0, 1, ∞ of one family, and
the `p`-mean/Atkinson correspondence is stated correctly; (c) **the collapse** —
`echenique2024`'s inequality parameter is the same scalar, so `DOMAIN_economic-theory.md` §4's
step 2 (choose the criterion) and step 4 (audit stability) are **one** one-parameter decision
(`LIT_economic-theory.md` §3). This last is the unit's real content and the reason it is gated on
U2-stab. Fold in `bertsimas2011` (price of fairness: what the Nash map can be costing against the
utilitarian one, *a priori*, before any map is computed) and `bhaskar2023equity` (the first
published bound on how far the three maps can be apart, with its binary-valuation caveat).

Also required: `shorrocks1980` and `foster2000` licence the decomposition under regrouping
(within-region + between-region) and path independence — state what each buys and, per
`foster2000`, that path independence covers **the balance term only** and says nothing about the
incumbency term, which is where the split actually costs.

## Numbers to compute first

`DOMAIN_economic-theory.md` §5 N4 — the three criterion maps and the pairwise share of `M` they
move. **Blocked on ★6.** If the three coincide, FRAME §3's binding tolerance is not binding and
U12 closes for free; state the threshold.

## Inputs to read (paths and sections only)

`docs/DOMAIN_economic-theory.md` §2.3, §4 step 2 (D2), §5 N4, §8 Q2 · `docs/LIT_economic-theory.md`
§0.5, §1 in full, §3 (`echenique2024`) · `docs/LENS_GROMOV.md` Move 3 (the fibration as written) ·
`docs/FRAME.md` §3 (the tolerance), §9 (the empty-bundle open item) · `docs/VERIFY_U2-stab.md`
and `docs/MODEL_U2-stab.md` (read-only — the gate) · `~/resources/economic-theory/FOUNDATIONS.md`
(`Kalai 1977`, `Thomson 1994`, `Thomson 2011`, `Moulin 2019`, `Nash 1950`, `Schmeidler 1969`)

## Open questions for ★0

**★4** — which criterion is the channel's standard. This unit prepares the ask; it does not answer
it. **★6** for N4. Also `DOMAIN_economic-theory.md` §8 Q8: if "do not starve anybody" is literal,
the objective is the nucleolus, not a product — flag, do not act.

## Branch

`wt/U5-crit` (from `wt/workflow-dryrun`)

## Stop rule

Do not re-derive Atkinson. If the identity does not match the programme's `D(g)` exactly, report
the discrepancy rather than adjusting either side.

**stop and report rather than improvise**
