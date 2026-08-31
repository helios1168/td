---
description: Run the fast test suite, auto-enabling the slow zip50 anchor when solver files changed
allowed-tools: Bash(.venv/bin/python3 battery/code/tests/run_all.py), Bash(TD_SLOW=1 .venv/bin/python3 battery/code/tests/run_all.py), Bash(git diff:*), Bash(git status:*), Bash(git rev-parse:*), Read
---

Run this repo's test gate.

## Which tier

CLAUDE.md §7: the fast suite is the default, **but the zip50 anchor
(`test_zip50_anchor.py`, ~2 min) must run whenever `districting.py`, `territory.py`, or
`synth.py` change** — those are the files the anchor guards, and a baseline regression is
invisible without it.

Changed files, uncommitted and staged:

!`git status --short`

Changed vs. the integration branch:

!`git diff --name-only contiguity-harness...HEAD 2>/dev/null || echo "(no contiguity-harness branch here)"`

**Decide from those lists**, then run exactly one of:

- Any of `code/districting.py`, `code/territory.py`, `code/synth.py` present →
  `TD_SLOW=1 .venv/bin/python3 battery/code/tests/run_all.py`
- Otherwise →
  `.venv/bin/python3 battery/code/tests/run_all.py`

State which tier you picked and why in one line before running.

## Reporting

- Report the **pass/fail/skip counts verbatim**. Never summarise a failure as "mostly green".
- On failure: paste the failing test's actual output, name the file, and stop. Do not attempt a
  fix in the same breath unless I ask — I want to see the failure first.
- If you ran the fast tier and any `SKIP … (set TD_SLOW=1)` lines appear, list them so I know
  what wasn't covered.
- If the suite passes, say so in one line and stop. No summary of what the tests do.
