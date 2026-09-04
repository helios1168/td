# Task Completion Checklist

- Run the full fast test suite via the main checkout's venv (see `mem:suggested_commands`) and
  confirm 0 fail: `/Users/ntlee/projects/td/.venv/bin/python3 tests/run_all.py`.
- If the change touches code exercised by the slow anchor, also run with `TD_SLOW=1`.
- No separate lint/format/type-check step is configured in this repo -- tests are the gate.
