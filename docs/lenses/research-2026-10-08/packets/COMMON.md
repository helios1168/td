## Context (read first)
td builds sales territory maps over the ~33,300 CONUS ZCTAs (rook adjacency on 2025 TIGER
polygons): K districts per channel, each one connected piece on the map with no neck (rule M1:
no connected part holding >=5% of the district's land area that reaches the rest through a cut
whose total shared border is under 10 km), each district's mass in dollars inside a fixed window
[L, U] (e.g. FI $765M-$1,035M) that does not depend on K, K free within a range (e.g. IFA 46-55),
and the fewest states split across districts, then the fewest fragments. Equivalent readings:
(i) bin packing with item fragmentation: states are items, districts are bins with a size window,
fragmenting an item costs; "rule C" says a bin may hold fragments of at most one item;
(ii) hypergraph partitioning: ZCTAs are vertices, each state a hyperedge; split states = cut-net
metric, fragments-1 = lambda-1 metric, blocks must be connected and neck-free in the planar graph.
Current method ("carve-first"): (A) an exact MILP over supports (connected sets of whole states)
with an integer count of districts per support, state shares and a binary s_v per split state,
giving a certified lower bound s_lower on split states; (B) a heuristic that carves a split state
into k connected in-band pieces each attached to whole states; (P) a library of such gate-passed
districts and a set-partitioning MILP choosing K of them, lexicographically minimising splits,
then fragments, then shape, then balance. Framing document: the file RESEARCH_FRAMING.md next to
this task (read it).

## Rules for every result
- Never cite from memory. For each cited result give: paper, authors, year, DOI, theorem/section,
  and a passage QUOTED from the source text you fetched in this session. If you could only read
  the abstract or a secondary source, write `claimed` instead of a quote and say why.
- Read `/Users/Shared/sv-ntlee/kb/references.bib` first and reuse an existing key if the paper is
  there; otherwise propose `<firstauthor><year>`. The project's verified rows are in
  `/Users/Shared/sv-ntlee/td/docs/REFERENCES.md`; do not re-derive those, cite them by key.
- For each paper with a DOI, check OpenAlex (https://api.openalex.org/works/https://doi.org/<doi>)
  for `is_retracted` and record the result.
- Label direct evidence, your interpretation, and your inference distinctly.
- Prefer open copies: arXiv, Optimization Online, author pages, NSF PAR. Paywalled-only = claimed.
- Do not download anything into any repo. Write only your output file.
- No sales data, rep names or firm names exist in your inputs; do not invent any.
- Output file, format:
  1. One-paragraph answer to the question.
  2. Results, most decision-relevant first. For each: key, DOI, result, quote, open-copy URL,
     retraction check, and a line "Maps to td: <A master / rule C / B carve / P library / M1
     gate / band / certificate>; transfers | needs proof | known hard; why".
  3. Gaps: what you looked for and did not find.
  4. `LEARNED[kb]: <topic>: <what it proves> (<key>, DOI <doi>, <Thm/§>: "<quote>", read <date>)`
     lines, one per result; `claimed` in place of the quote where you did not read it.
