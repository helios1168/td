# Code Conventions

- `from __future__ import annotations` + full type hints throughout.
- Module docstrings are narrative prose explaining *why* the module exists and what it
  supersedes/replaces, not just what it does -- cross-reference test names
  (`tests/test_X.py::test_Y`) and design docs (`docs/*.md`, `research/**/NWAY.md`) as the
  source of truth for rationale rather than re-deriving it in-line.
- Function/method docstrings state invariants and edge cases tersely (one-liners), not full
  narrative.
- Graph node attributes use module-level string constants (e.g. `CAND`, `BOOK`, `FREE` in
  `td/model.py`), never magic string literals at call sites.
- Prose (including in docstrings) uses `--` (double-hyphen), not an em-dash.
- Match existing style exactly when editing; don't refactor or reformat adjacent code.
