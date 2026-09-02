---
name: grothendieck-toy-verification
description: Oracles, anchors and environment traps for verifying units in /Users/ntlee/tmp/framework-scratch/grothendieck-toy (unit T1-cut verified 2026-09-02)
metadata:
  type: project
---

Scratch repo `/Users/ntlee/tmp/framework-scratch/grothendieck-toy` runs a
modeler → math-verify → python-typed → code-verify pipeline per unit, with
`docs/MODEL_<id>.md` (§1 symbol table, §2 propositions, §4 numbers table with
script·seed·command per row), `docs/units/<id>.md` (files owned / forbidden /
acceptance), and code under `toy/`.

**Why:** the §4 table is designed to be re-run row by row; the "files owned"
list tells you exactly what is in scope and what is off-limits.

**How to apply:** when verifying a unit here —

*Oracles that worked (T1-cut, 2026-09-02).* Build the independent oracle so all
three mechanisms differ from the implementation, not just one: union-find vs the
impl's BFS, integer bitmasks vs `itertools.combinations`, doubled-integer
arithmetic vs `Fraction`. Add a driver that recomputes every MODEL §4 row through
the *public API of the owned file only* and compares three-way (code / MODEL
literal / oracle) — this is what exposes §4 rows with no code counterpart.
Mutation testing (10 hand-written single-edit mutants, run in a tempdir against
an unmodified test copy) is the cheapest way to find that a green suite is
vacuous; it found the real defect in T1-cut. Always check the oracle's test
family is non-degenerate (e.g. confirm π > 0 occurs on some random graphs before
claiming π ≥ 0 was tested).

*Anchors.* This project has NO byte-identity anchors — no `figures/`, no
captured-stdout fixtures. Don't look for them.

*Environment traps.*
- `/usr/bin/python3` is CPython 3.9.6 and has **no pytest**. Briefs' acceptance
  clauses say `python3 -m pytest toy/`, which fails as written. Use
  `uvx --with pytest --python 3.9 python -m pytest toy/ -q`. `uv` is at
  `/Users/ntlee/.local/bin/uv` (not on PATH by default in this shell).
- Tests import the module bare (`from cut import ...`), relying on pytest's
  rootdir sys.path insertion; fine today, fragile under `--import-mode=importlib`.
- `uvx pyright --pythonversion 3.9 <files>` is the type gate; pyright 1.1.411
  reports 0 errors on T1-cut.
- Repo has a git dir with **zero commits**, so `git log`/`git blame` give nothing.
- Scratch scripts go in `toy/scratch/codeverify_*` (the parent agent overrides
  the usual "never in the repo tree" rule for this project).

See [[codeverify-report-shape]] for the report format that was accepted.
