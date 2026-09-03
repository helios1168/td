# Unit U0-lit — run the optimization literature brief

**Status 2026-09-03 (A1 track, `wt/A1`): landed in A1 form** — `docs/LIT_optimization.md` + `LIT_optimization.bib` (46 entries) answer `DOMAIN_optimization.md` §6 as re-cut for the A1 charter; the split-count citation this unit was waiting for is `lenstra1990`. See `docs/BRIEF.md` §4.

## Spec (verbatim from `docs/DOMAIN_optimization.md`:§6)

> **What FOUNDATIONS does not cover that this problem needs.** FOUNDATIONS is strong on
> MILP/MINLP machinery, flows, and districting-with-contiguity, and *silent* on: market-equilibrium
> convex programs, Nash welfare as an optimisation object, submodular approximation guarantees,
> power diagrams and semi-discrete transport, joint districting-plus-selection, and stability
> metrics on solutions. Those six gaps are the brief.
>
> **Deliverable.** Entries as `citation · venue/year · DOI · 2–4 sentence annotation naming which
> §2 method or §4 decision point it bears on · tag ∈ {foundation, frontier,
> contradicts-or-sharpens, tool-we-lack}`. Plus a **five-paper shortlist** — the five that would
> change what gets built. Every absence claim must state where it looked (venue, keyword, years),
> because the programme's own recon (`RESEARCH_FINDINGS` §0.5) already went stale once. Write
> `docs/LIT_optimization.md` and append to `docs/RESEARCH_ADDITIONS.bib`.

Work `DOMAIN_optimization.md` §6's nine numbered questions in the order given. **Q5 and Q7 are
the two that gate other units** and must be answered even if the time-box bites: Q5 (power
diagrams / constrained least-squares equivalence / the `≤ k−1` split-unit bound) gates U1-cert's
citation-vs-proof decision, and Q7 (stability radius, inverse optimization, "objective gap ≥
φ(mass moved)") decides whether U4-disp is a unit at all.

## Files owned

- `docs/LIT_optimization.md` (create)
- `docs/RESEARCH_ADDITIONS.bib` (**append only** — never rewrite or reorder existing entries)

## Files forbidden

`docs/BRIEF.md` · `docs/FRAME.md` · `docs/LENS_*.md` · `docs/DOMAIN_*.md` ·
`docs/LIT_economic-theory.{md,bib}` · `docs/MODEL_*.md` and every other unit's owned files ·
`docs/RESEARCH_FINDINGS.md` · `docs/channel_note/**` · `CLAUDE.md` · all of `td/`, `tests/`,
`tools/`, `figures/`.

## Agent → verifier

`lit-search` → **no verifier agent.** The absence ledger and query log are the self-verifying
artifact; the main session spot-checks a sample of DOIs against Crossref before anything is cited
in a note.

## Acceptance

1. All nine §6 questions have a populated section, or an explicit "time-boxed, not searched" entry
   in a "where this stopped" section naming what would be done first on resumption — **Q5 and Q7
   may not be the ones dropped**.
2. Every DOI resolved against Crossref, with the resolved/attempted counts stated. Any DOI that
   does not resolve is dropped, not guessed.
3. Deduplicated against `docs/RESEARCH_FINDINGS.md`, `docs/RESEARCH_ADDITIONS.bib`,
   `docs/LIT_economic-theory.bib`, `docs/channel_note/references.bib` and
   `~/resources/optimization/FOUNDATIONS.md` — state that the check was run.
4. A five-paper shortlist, each with one sentence on **what it changes in `DOMAIN_optimization.md`
   §2 or §4**.
5. An absence ledger in which every absence claim names venues, keywords and years searched, and
   a full query log.
6. Explicit verdicts on the three claims the domain plan marks as unsourced: the `≤ k−1` split-zip
   descent (§2.2), the constrained-least-squares ⇔ power-diagram equivalence and whether it
   survives at `τ > 0` (§2.2, §6 Q5), and any "objective gap ≥ φ(mass moved)" result (§2.4, §6 Q7).

## Numbers to compute first

None — this unit computes no numbers. It resolves DOIs and reports counts (queries run, DOIs
resolved / attempted, entries added, duplicates rejected).

## Inputs to read (paths and sections only)

- `docs/DOMAIN_optimization.md` §6 (the brief), §2 (what each method needs a citation for), §8
- `~/resources/optimization/FOUNDATIONS.md` (the 113 seeded entries — what is already held)
- `docs/LIT_economic-theory.md` §0 and its absence ledger (**the model for this file's shape**,
  and the dedup target — Q1/Q4 overlap its Q1/Q5; do not re-do that work, cite across)
- `docs/RESEARCH_FINDINGS.md` §0.5 (the stale-frontier warning) — do not edit
- `docs/FRAME.md` §6 (instance size: `n = 1,229`, `k = 13`, `|R| = 111` — the scale at which
  approximation guarantees are or are not worth having)

## Open questions for ★0

- None blocking. This unit is runnable today and blocks nothing upstream.
- If Q6 (is the rep-indexed formulation already published?) returns a direct hit, say so in the
  shortlist in those words — it changes the shape of the note, not the code.

## Branch

`wt/U0-lit` (from `wt/workflow-dryrun`)

## Stop rule

Time-box the sweep. If a question cannot be answered without a paywalled full text, record the
citation with what is known from the abstract and mark it unread — **do not infer results from a
title**. If Q5 or Q7 returns nothing after the venues and keywords in §6 are exhausted, write the
absence claim with its search record and stop: a well-documented absence on Q7 is the finding that
cancels U4-disp, and is worth more than a speculative near-miss.

**stop and report rather than improvise**
