---
name: bibliography
description: Verified-citation workflow for literature/territory_bibliography.{md,csv,bib}. Use whenever adding, checking, or citing a reference; searching for papers or prior work; extending the bibliography; writing a related-work section; or editing .bib entries. Enforces DOI resolution against fabrication, citation-graph traversal against silent incompleteness, three-format sync, and the brace-protection rule plainnat requires.
---

# Verified citations

Two failure modes make unverified citation expensive, and both are mechanical to prevent.

**Fabrication.** A plausible author-year-journal triple is easy to generate and hard to spot.
A citation either resolves to a real paper saying what you claim, or it does not.

**Silent incompleteness.** Keyword search returns what shares vocabulary with your query, not
what the field considers foundational. The seminal paper often used different words — it named
the field before the current terms existed. Citation-graph traversal finds it; keyword search
does not.

Full rationale, worked examples and the reuse story: **`literature/LITERATURE_WORKFLOW.md`**.
Read it when extending the bibliography's *scope*; this file is enough for adding entries.

## This project's files

`literature/territory_bibliography.{md,csv,bib}` — three synchronised formats of one dataset
(78 entries). The `.md` is the annotated deliverable, the `.csv` is diffable, the `.bib` drops
into the manuscript. **Generate them from one source so they cannot drift**; if you edit one by
hand, update all three in the same change.

## Adding a reference — the non-negotiable steps

1. **Resolve the DOI. Including the ones you are sure of.** Fetch the work and check the returned
   title, authors, and year against what you expected. This costs a second and converts a claim
   about a citation into a citation. It catches real errors: OpenAlex returns the author of
   Nash's 1953 *Two-Person Cooperative Games* as "John C. Nash" rather than John F. Nash.
   Metadata is not authoritative merely because a database returned it.
2. **Check the retraction flag** in the same pass.
3. **Annotate for reuse, not storage.** Two things per entry:
   - *What it establishes* — the paper's actual contribution, one or two sentences.
   - *Why it bears on this problem* — what you would cite it **for**, and against which claim.

   A bibliography with only metadata says papers exist. One with relevance notes says which to
   reach for. Skipping this is the usual failure.
4. **Note the gaps explicitly** — threads you know are relevant and did not search. Without that,
   absence reads as coverage.

## Searching, when the reference isn't known yet

- **Fan out broad first (6–10 conceptual queries, batched), and expect noise.** In the run this
  workflow came from, "sales territory alignment salesforce districting optimization" returned a
  paper on GPT-3 news summarisation as its top hit; two of eight queries landed. That is a normal
  yield, not a reason to stop. The purpose is learning which of your guesses about the relevant
  literatures are real.
- **Then switch to near-title queries** — the highest-yield step. "Experiences with a sales
  districting model criteria implementation" returns Hess & Samuels 1971. Recall proposes the
  target; retrieval confirms it exists and supplies correct metadata. Recall alone gives a
  citation you cannot defend; retrieval alone will not surface a 1971 paper.
- **Walk the citation graph one step** on the two or three most central hits, both directions.
  Backward finds foundations, forward finds what extends or contests them; neither reliably
  appears in keyword search. A forward walk on a 2005 retrospective surfaced the entire modern
  commercial-districting thread here. **This is the step that gets dropped, and it is the one
  that finds what keyword search misses.**

## Writing into the `.tex`

- **Cite only keys that exist.** `grep "^@" literature/territory_bibliography.bib` to confirm
  before citing. Never invent a key and never cite a paper that isn't in the `.bib`.
- **Brace-protect proper nouns** in any new entry — `{Nash}`, `{MINLP}`, `{COSTA}`. `plainnat`
  lowercases titles otherwise.
- After editing, build and check the log:
  `export PATH=/Library/TeX/texbin:$PATH && make`, then grep
  `nash_territory_division.blg` for `Citation ... undefined`. An undefined citation does **not**
  fail the build — it silently ships a `[?]`. (The `/paper` command does both steps.)

## The constraint worth stating out loud

When handing this bibliography to any downstream reader — a Project, a chat, a subagent:

> Cite only from the attached bibliography. If a claim needs a source that is not in it, say so
> rather than supplying one.

That converts the file from context into a constraint, which is what stops fabrication.
