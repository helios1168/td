# Docs, units, state and tasks: the layout and its history

**Since the sandbox-fresh migration (2026-09-11)**, per the worktree's `AGENTS.md`:
- `STATE.md` holds only `## Now` (at most 1 KB), edited directly, commits prefixed `State:`.
  History: `git log --grep '^State:' -p -- STATE.md`.
- Settled numbers and decisions live in these Serena memories (`facts/*`, `decisions/*`); the
  old `STATE.md` `## Facts` is migrated into `facts/*`.
- The task list is Beads (`bd`, committed as `.beads/issues.jsonl`); the old `STATE.md`
  `## Next` rows are beads. A track is an epic bead; there is no `PLAN.md`.
- `.claude/agent-memory/` (per-subagent stores) is retired; its content is in `verify/*`,
  `domain/*`, `model/*` and `refs/*`.

**Kept from the 2026-09-07 redesign** (`833dd31`, brief `git show a16c304:PLAN.md`):
- One owner per topic: `docs/PROBLEM.md` (business problem facts), `docs/MODEL.md` (model
  facts), `docs/CODE_MAP.md` (files and recipes), `docs/APP.md`, `docs/units/<id>.md`, and
  `docs/foundations/` (frozen stage 1 to 4 docs, read-only). The allowlist is
  `.claude/doc-owners.txt`, checked by `tests/test_docs_owners.py`.
- One file per unit, `Status: open|done|dropped`, sections `## Model`, `## Verify`,
  `## Code verify`. Verifier artifacts are committed under `tools/verify/<id>/`, never
  test-discovered and never scratch (scratch is what lost U8-band's).
- Bugs go to a `TODO` at the site; the runner has no xfail.
- When a new doc seems needed, name its owner first; without one it belongs in an existing file
  or in git history.

Branches that predate the migration still carry a `PLAN.md` (for example
`worktree-full-problem`); its last commit before merge deletes it.

Units on `main`: P0C-screen, U0-lit, U1-cert, U2-stab, U3-inv (retired), U4-disp, U5-crit,
U6-sel, U7-meas, U8-band (done), U9-bandthm, U10-round, U11-roster, U12-menu, U13-base,
state_borders, state_splits.

Open follow-ups from the 2026-09-07 redesign (now beads): the research questions the folded
findings files carried (`git show a16c304:PLAN.md` `## Decisions needed`), `docs/channel_note/`
and `docs/math_note/` LaTeX sources with no owner row, and the bibliography three-format gap.

Source: host memory td-workflow-redesign-2026-09-07; `git show a16c304:PLAN.md`; worktree
`AGENTS.md` (2026-09-11).
