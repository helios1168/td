---
name: domain-lens-conventions-td
description: Conventions the td project's /domain runs must follow — citation rule, section-numbering stability, revision-vs-supersede, branch discipline
metadata:
  type: project
---

Conventions for any `/domain <d>` run in the td repo.

**Why:** `docs/units/*.md`, `docs/BRIEF.md` and `docs/APPROACHES.md` cite DOMAIN files **by
section number** (`DOMAIN_optimization.md` §2.1, §2.4, §2.5, §2.6, §3, §4, §5, §6, §8 Q3/Q4/Q7).
Renumbering §2 silently breaks every one of them.

**How to apply:**

1. **Keep `§2.<n>` identifiers stable across revisions.** If a method is retired, keep its number
   and label it retired with the reason; add new methods at the next free number. Same for
   §8's `Q<n>` — answered questions stay numbered and are restated as answered.
2. **Citation rule, stated at the top of every file:** bold keys = `~/resources/<d>/FOUNDATIONS.md`
   entries (the only literature the plan asserts); lowercase code-font keys = entries that already
   exist in `docs/LIT_economic-theory.bib` / `docs/RESEARCH_ADDITIONS.bib`, cited as pointers not
   as support; anything else goes uncited into the §6 search brief. Verify every bold key resolves
   before finishing (`grep -o '\*\*[A-Z][A-Za-z]*[0-9]\{4\}' file | comm` against FOUNDATIONS).
3. **Only optimization and economic-theory are seeded.** Any other domain's FOUNDATIONS says "not
   yet seeded" — stop and report, do not plan from memory.
4. **Branch discipline.** Track work happens on `wt/<ID>` worktrees. A DOMAIN file written on a
   track supersedes the hub's *on that branch only*; say so in the header. Never merge into
   `national-channel` without asking.
5. **`docs/LIT_optimization.md` does not exist** — U0-lit has never run, so no optimization
   literature question has ever been answered. Do not cite it.

Related: [[domain-optimization-td-a1]]
