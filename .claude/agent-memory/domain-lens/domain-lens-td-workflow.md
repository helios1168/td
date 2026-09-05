---
name: domain-lens-td-workflow
description: How the /domain stage runs on the td project — reading order, output discipline, and the trap of planning from memory when a track charter has superseded the hub
metadata:
  type: project
---

Workflow notes for the `domain-lens` agent on td (national channel territory design).
Written 2026-09-03 after the A1-track rewrite of `docs/DOMAIN_economic-theory.md`.

**Why:** td runs the six-stage research framework with per-track worktrees (`wt/A0`…`wt/A5`),
so the same `docs/DOMAIN_*.md` filename means different things on different branches. A run
that reads the hub's version and plans from it will supersede the wrong document.
**How to apply:** at the start of every run, establish which track charter is live before
reading anything else.

- **Read order that works:** `~/.claude/commands/domain.md` → `~/resources/<domain>/FOUNDATIONS.md`
  in full → `docs/APPROACHES.md` §<track> (the charter is the problem statement, verbatim) →
  `docs/FRAME.md` (§0 resume, §3, §5–§6, §8–§10) → every `docs/LENS_*.md` on the branch → the
  measurement models (`MODEL_U*.md` §6, `VERIFY_U*.md` §0) → the predecessor `DOMAIN_*.md` →
  the sibling `DOMAIN_*.md` for non-duplication → `LIT_*.md` in full.
- **`FRAME.md` §0 is the only reliable state pointer.** `CLAUDE.md` lags it by a day or more.
- **The two `/domain` runs are parallel and must not overlap.** economic-theory takes the
  interpretive and mechanism-design questions; optimization takes solver mechanics, LP rank,
  duality machinery, parametric solves. Both plans route the *same* three objects to each other
  (EG duality, the premium ladder, displacement) — name the hand-off, do not restate the method.
- **Write exactly one file under `docs/`.** No summary or report files; the caller reads the
  final message.
- **Lens ledgers are the unit backlog.** `LENS_GROMOV.md`'s Move 14 table (U1…U19) numbers the
  named unknowns and later files cite them by number. Map every §5 "number to compute" onto a
  U-number where one exists.
- **Measured vs claimed discipline is enforced downstream.** `math-verify` on this project does
  real work and has refuted model claims. Tag `[measured]` (with a FRAME §6 or unit source),
  `[claim]` (this plan's assertion) and `[standard]` consistently, or the verifier will bounce it.

Domain-specific verdicts live in [[domain-economic-theory-td]].
