# Oracle review: is the td research well posed, and will it land in time?

Time: it is 00:34 on 2026-10-08, the owner's local time. The owner wants scenario maps by
08:00. The research being reviewed is meant to land on a workable method within the next one
to two hours. Judge everything against that clock.

## Read, in this order (absolute paths; all read-only)
1. /Users/Shared/sv-ntlee/td/docs/problem/MANDATES.md (hard requirements, owner-only)
2. /Users/Shared/sv-ntlee/td/docs/problem/PROBLEM.md
3. /Users/Shared/sv-ntlee/td/WATCHDOG.md
4. /Users/Shared/sv-ntlee/td/docs/lenses/REVIEW_2026-10-07.md (checkpoint: decisions, the
   carve-first formulation, rule C, the CT/MD findings, routes)
5. /Users/Shared/sv-ntlee/td/docs/lenses/review-2026-10-07/CONSOLIDATED.md (three review rounds)
6. /tmp/iss/research/RESEARCH_FRAMING.md (the planning document under annotation)
7. /tmp/iss/research/P1.md … P7.md (the drafted literature-search packets, not yet run) and
   COMMON.md (their shared preamble)
8. For the current code's objects, skim /Users/Shared/sv-ntlee/td/docs/MODEL.md §1–§4 headings
   and /Users/Shared/sv-ntlee/td/docs/problem/SPLITS.md §2.

## Your job
1. **Primitives.** Identify the axioms, primitives and foundational concepts of the problem
   statement as it actually stands (the mandates, the owner's decisions D1–E3, the goal "strictly
   contiguous territories with as few state splits as possible"). Refine them into the smallest
   set of the sharpest concepts that give a language in which the problem is a tractable
   mathematical optimisation problem. Aim for very few, extraordinarily clear primitives. For
   each: name, one-sentence definition, what in the mandates or decisions it comes from, and
   what it is NOT (the nearby concept it must not be confused with).
2. **Alignment audit.** Check every piece of reasoning so far (the carve-first formulation, the
   rule C row, the certificate claim, the packing and hypergraph readings in the framing
   document, the seven packets) against those primitives. List each place where the reasoning
   uses a concept outside the primitive set, or conflates two of them, or where a primitive is
   missing from a formulation (e.g. the neck in a model that only has contiguity).
3. **Well-posedness of the research.** For each packet P1–P7: is its question well posed in the
   primitives, is it answerable from literature in about an hour, and would its answer change
   what gets built tonight? Mark each KEEP / CUT / MERGE / REWRITE with a one-line reason and,
   for REWRITE, the replacement question.
4. **Will it land?** Give a frank assessment: given one to two hours of research and the rest of
   the night for implementation on the existing code (the support master, the M1 gate in
   td.audit, the whole-unit planner of #127, the carve heuristics not yet written), what is the
   most probable path to scenario maps by 08:00 that pass M1 and the dollar band with few
   splits, and what should be dropped to get there. Separate "needed for maps by 08:00" from
   "needed for a certificate" from "nice to know".
5. **Simplest formulation.** Propose, in the primitives, the simplest formulation of the whole
   problem you can defend, and say what it gives up relative to the current one.

## Rules
- Do not run code, do not edit any file but your output. No web research: this is a review of
  what exists, from first principles.
- Quote the source (file and line or section) for every claim about what the project says.
- Be direct. If the research is not going to land in time, say so and say what would.
- Output: /tmp/iss/research/ORACLE.md, under 2,500 words, sections numbered 1–5 as above, then
  `LEARNED:` and `DECIDED: none` lines.
