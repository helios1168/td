# How a /domain run works on td

Written 2026-09-03 after the A1-track rewrite. Since 2026-09-07 the stage 1 to 4 documents are
frozen under `docs/foundations/`; a new domain run must not write there without the user's
say-so.

**Read order that works.** `~/.claude/commands/domain.md` (or its skill), then
`~/resources/<domain>/FOUNDATIONS.md` in full, then `docs/foundations/APPROACHES.md` §<track>
(the charter is the problem statement), then `docs/foundations/FRAME.md` (§0, §3, §5 to §6, §8
to §10), every `LENS_*.md`, the measurement models (`docs/units/<id>.md` `## Model` /
`## Verify`), the predecessor `DOMAIN_*.md`, the sibling `DOMAIN_*.md` for non-duplication, and
`LIT_*.md` in full. Establish which track charter is live before reading anything else: the
same filename meant different things on different branches.

**Conventions.**
- Keep `§2.<n>` identifiers stable across revisions; a retired method keeps its number with the
  reason. Same for §8's `Q<n>`: answered questions stay numbered and are restated as answered.
  Units, BRIEF and APPROACHES cite DOMAIN files by section number.
- Citation rule, stated at the top of every file: bold keys are `~/resources/<d>/FOUNDATIONS.md`
  entries (the only literature the plan asserts); lowercase code-font keys are entries already
  in `docs/foundations/LIT_economic-theory.bib` or `literature/RESEARCH_ADDITIONS.bib`, cited as
  pointers, not support; anything else goes uncited into the §6 search brief. Verify every bold
  key resolves against FOUNDATIONS before finishing.
- Only optimization and economic-theory are seeded. Any other domain's FOUNDATIONS says "not yet
  seeded": stop and report, do not plan from memory.
- The economic-theory and optimization runs are parallel and must not overlap: economic theory
  takes the interpretive and mechanism-design questions, optimization the solver mechanics, LP
  rank, duality machinery and parametric solves. Both route the same three objects to each
  other (EG duality, the premium ladder, displacement); name the hand-off, do not restate it.
- Write exactly one file. Lens ledgers are the unit backlog: `LENS_GROMOV.md`'s Move 14 table
  numbers the unknowns (U1 to U19); map every "number to compute" onto a U-number.
- Tag `[measured]` (with a source), `[claim]` and `[standard]` consistently; `math-verify` on
  this project does real work and has refuted model claims.
- `docs/foundations/LIT_optimization.md` exists (U0-lit, 2026-09-03); check its content before
  citing.

Related: `mem:domain/economic-theory-conventions`, `mem:domain/optimization-verdicts`.

Source: `.claude/agent-memory/domain-lens/domain-lens-td-workflow.md` and
`domain-lens-conventions-td.md` (2026-09-03).
