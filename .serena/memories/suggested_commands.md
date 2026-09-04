# Suggested Commands (Darwin)

- Always use a venv's `python3`, never system python (no numpy/scipy/networkx there).
- **This worktree has no `.venv`.** Use the main checkout's, three levels up:
  `/Users/ntlee/projects/td/.venv/bin/python3`.
- Tests: `.../.venv/bin/python3 tests/run_all.py` from the repo root.
  - Fast tier only by default.
  - `TD_SLOW=1 .../python3 tests/run_all.py` adds the slow anchor tier (one anchor takes ~2 min).
  - `-k <name>` filters by substring. Also runnable under plain `pytest tests`.
- LaTeX (`docs/channel_note/`): MacTeX at `/Library/TeX/texbin` is not on `PATH` in
  non-interactive shells -- prefix `export PATH=/Library/TeX/texbin:$PATH` before building.
- Never `cd` into or run anything from `~/iCloud` (`~/Library/Mobile Documents`) -- hangs
  brew/tmux/hooks with EINTR, and the cwd persists across calls in this harness.
