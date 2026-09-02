# Unit U3-inv — may the drawing read books? The invariant message space, against the Nested Range Condition

## Spec (verbatim from `docs/DOMAIN_economic-theory.md`:§2.7(b))

> **Restricting the message space** to `G`-invariants (normalised per-rep profiles, GROTH §5b)
> plus audited magnitudes yields a drawing rule that is strategy-proof against uniform inflation
> **by construction**, with no theorem required `[claim]`; **Hurwicz 1972** then says the price is
> efficiency, and that price is measurable — re-run the draw on invariants only and compare
> premium retained.

The claim to be tested, verbatim from `docs/LENS_GROTHENDIECK.md`:§5b:

> Let `G = (ℝ_{>0})^R` act by rep-uniform inflation of reported books, `S_{i,·} ↦ γ_i·S_{i,·}` —
> the natural model of the incentive the 98 unselected reps have. Its invariants include `M_z`,
> the candidate sets `cand(z)`, and each rep's **normalised geographic profile**
> `S_{i,z}/S_i(Z)`. Hence:
>
> > **A drawing rule that reads reported books only through normalised per-rep profiles is
> > invariant under uniform inflation, by construction.** `[claim]`
>
> That is a direct, checkable answer to FRAME §10.5 that needs no mechanism-design theorem […]
> It does not cover selective (per-zip) inflation, and it discards book magnitude.

And the correction the literature already returned, verbatim from `docs/LIT_economic-theory.md`:§4
(`green1986`):

> **Bears on: §2.7(b) and D5, and it replaces Hurwicz as the load-bearing citation.** DOMAIN §2.7
> claims that restricting the message space to `G`-invariants yields strategy-proofness "by
> construction, with no theorem required `[claim]`". Green–Laffont is the theorem, and it is
> conditional: the claim holds only if the invariant-message correspondence satisfies NRC. That
> is a checkable algebraic condition on `(ℝ_{>0})^R`-orbits and it must be checked before the
> claim is written.

## Files owned

- `docs/MODEL_U3-inv.md`
- `docs/VERIFY_U3-inv.md` (written by `math-verify`)
- `docs/artifacts/U3-inv/**`

## Files forbidden

Every other unit's owned files · `docs/FRAME.md` · `docs/BRIEF.md` · `docs/LENS_*.md` ·
`docs/DOMAIN_*.md` · `docs/MODEL.md` (read-only — **do not write the design rule into it**;
`LENS_GROTHENDIECK.md` descent 5 proposes that and it is the main session's call after this unit
reports) · `docs/LIT_economic-theory.{md,bib}` (read-only) · `docs/RESEARCH_FINDINGS.md` ·
`docs/RESEARCH_ADDITIONS.bib` · `docs/channel_note/**` · `CLAUDE.md` · all of `td/`, `tests/`,
`tools/`, `figures/`, `battery/`.

## Agent → verifier

`modeler` → `math-verify`

## Acceptance

`math-verify` returns **VERIFIED or REFUTED** on P1 and P2, with a runnable artifact (the NRC
check is algebraic and small enough to verify symbolically on the orbit structure and numerically
on toy profiles):

- **P1 (the invariants).** Characterise the invariant subalgebra of the `G = (ℝ_{>0})^R` action
  `S_{i,·} ↦ γ_i S_{i,·}`. Confirm or correct the lens's list (`M_z`, `cand(z)`, normalised
  profiles `S_{i,z}/S_i(Z)`) — is it complete, and is a rule reading only these *exactly* the
  `G`-invariant rules, or merely a subset of them? A drawing rule may legitimately be invariant
  without factoring through that particular generating set.
- **P2 (NRC).** State `green1986`'s Nested Range Condition precisely for this message
  correspondence and **decide it**: does the `G`-invariant message space satisfy NRC, so that the
  revelation principle survives and restriction buys strategy-proofness with no further argument?
  If NRC **fails**, say so and route to `deneckere2008` (what remains implementable beyond NRC) —
  a clean refutation here is a more valuable result than a laboured confirmation, because it is
  the difference between a design rule that can be written into `MODEL.md` today and one that
  cannot.

Required at PLAUSIBLE-or-better:

- **P3 (the hole, named and sized).** Selective (per-zip) inflation at constant total is **outside
  `G`** and `G`-invariance buys nothing against it (`LENS_GROTHENDIECK.md` §5b;
  `DOMAIN_economic-theory.md` §2.7 failure mode). State the smallest group action that *would*
  cover it, and whether any invariant survives it at all. If the honest answer is "audited data or
  no book-awareness", write that sentence.
- **P4 (the model the programme is actually in).** One section positioning `benporath2014` —
  optimal allocation of an indivisible object, **no transfers**, verification at a cost, optimum
  is a *favoured-agent* mechanism — as the model D5 actually sits in, per
  `LIT_economic-theory.md` §0.3. Say what changes at `13` seats rather than one (the stated gap),
  and note `mylovanov2017` (ex-post verification, bounded penalty — the wholesaler who
  overstates can only lose the seat, not be fined) and `milgrom1981` (unravelling: a credible
  audit *threat* plus discounting of unaudited claims may be cheaper than universal audit).
- **P5 (the transfers boundary, priced).** `benporath2012` says *arbitrarily small* transfers
  suffice for implementation, which is a materially smaller ask of the sponsor than the VCG
  sentence `DOMAIN_economic-theory.md` §2.7(a) proposes. State both, in one paragraph, as the
  scope question they are — FRAME §7 puts transfers out of scope and only leadership can reverse
  that. **Recommend nothing about compensation design.**

## Numbers to compute first

No §5 number gates this unit — it is the one wave-1 unit that is genuinely instance-free at the
theory level. Two measurements are downstream of it and must be named as *what would be measured
next*, not attempted:

| source | number | why it is downstream |
|---|---|---|
| `DOMAIN_economic-theory.md` §8 Q7 / `LENS_GROTHENDIECK.md` OQ4 | **what fraction of the premium a `G`-invariant drawing retains** | the difference between "safe and worthless" and "safe and worth doing"; measurable with no business input, and it should be scheduled regardless of how ★2 resolves |
| `LENS_GROMOV.md` U4 | zips contested **among the selected 13** and their share of `M` | if small, the whole book-awareness decision is worth close to nothing and is settled by data instead of by principle |

State the threshold on the second explicitly: below what share of `M` does this unit's entire
question stop mattering?

## Inputs to read (paths and sections only)

- `docs/DOMAIN_economic-theory.md` §2.7 in full, §4 step 5 (D5), §8 Q3 and Q7
- `docs/LIT_economic-theory.md` §0.3 and §4 in full (`green1986`, `milgrom1981`, `bull2007`,
  `deneckere2008`, `benporath2012`, `kartik2012`, `benporath2014`, `mylovanov2017`,
  `benporath2019`, `caragiannis2012`), and absence row A6
- `docs/LIT_economic-theory.bib` (read-only — the keys)
- `~/resources/economic-theory/FOUNDATIONS.md` — `Hurwicz 1972`, `Gibbard 1973`,
  `Satterthwaite 1975`, `Myerson 1979`, `Maskin 1999`, `Crawford & Varian 1979`
- `docs/LENS_GROTHENDIECK.md` §5b (the group and its invariants), descent 5
- `docs/LENS_GROMOV.md` Move 13.1 (reported vs audited — the word split that dissolves the
  dichotomy), Move 9 (why the governance answer must be structural: the misreporting generator is
  a self-interested optimiser, so "bound the stupidity" points the wrong way)
- `docs/FRAME.md` §4 policy row, §8 A7, §10 Q5, §9 (the blocking item as currently written)
- `docs/DATA.md` (what the exporter actually emits — shares, `m_rel`; this constrains what a
  message space *can* be)
- `docs/RESEARCH_FINDINGS.md` §9-G (the books-enter-at-stage-2-only invariant this unit may
  propose rewriting) — **read only, do not edit**

## Open questions for ★0

- **★2 — is audited system-of-record book available at zip × wholesaler grain, and how far is it
  from reported book?** This is the *only* input that decides which of this unit's branches is
  live, and both lenses agree it is the smaller, answerable form of FRAME §9's blocking decision.
  **Do not wait on it** — write both branches (audited available / not available) and mark which
  results hold in which.
- If NRC holds, the deliverable is a rewrite of `RESEARCH_FINDINGS` §9-G's invariant to *"reported
  books enter at stage 2 only; audited revenue may enter anywhere"* (`LENS_GROMOV.md` 13.1).
  **Propose the wording in `MODEL_U3-inv.md`; do not apply it** — §9-G is not this unit's file.

## Branch

`wt/U3-inv` (from `wt/workflow-dryrun`)

## Stop rule

This unit is the one most at risk of drifting into recommending a mechanism. It must not: FRAME §7
puts compensation and transition packages out of scope, and `DOMAIN_economic-theory.md` §2.6 warns
that the adjacent method "should be cut back to a single paragraph" if it starts producing payouts.
Characterise the message space, decide NRC, name the hole, position `benporath2014` — and stop.

If NRC turns out to be undecidable without knowing whether the audited measure exists, say exactly
that and hand it to ★2 rather than assuming an answer.

**stop and report rather than improvise**
