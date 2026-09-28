# Resetting the legacy issue queue for the support refactor

**Status:** judgement calls made without asking while executing td#53 (A1 of the td#52 plan) on m2-studio, 2026-09-28, m2 session 01a0e728 fork 01a0e72b. td#53 was still open, not yet landed, when these were filed. What was built: `facts/refactor-archive-and-queue`.

**Context.** The td#52 plan, section 10, accounts for all 51 pre-refactor issues: #3 kept, 11 folded into successors (#1, #7, #11, #16, #19, #32, #45, #47, #48 and #51 into new plan issues, #46 into S11 of #52) and 39 archived with a link to the tag `archive/pre-support-2026-09`. #53's acceptance puts the `archived` label on the archived set only.

**Decision.**
- All 50 closed legacy issues, folded and archived alike, were closed with reason "not planned".
- The `archived` label went only on the 39 archived issues, not on the 11 folded ones (#46 among them).
- The four pre-refactor milestones (1 to 4), and the stale labels such as `ready`, `doing` and `owner-decision` left on closed issues, were not touched.

**Alternatives rejected.**
- Closing folded issues with `--duplicate-of`: their successors are new-scope issues, not duplicates.
- Labelling the folded issues `archived` too: #53's acceptance reserves the label for the archived set.
- Cleaning up the old milestones and stale labels: outside #53's stated scope.

**Consequences.** Label queries on closed issues can still return legacy issues carrying `ready`, `doing` or `owner-decision`; open-issue queries are unaffected. Milestones 1 to 4 stay open, empty of open work, until someone closes them.
