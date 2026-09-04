# Tech Stack

- Python >=3.11 (`pyproject.toml`).
- Core deps: `numpy`, `scipy`, `networkx`.
- Optional: `pyscipopt` (stage-1 engine, `td/solvers/scip_tree.py`), pinned in
  `requirements.txt` instead of `pyproject.toml` deliberately -- it needs a local SCIP build,
  so `pip install -e .` must not fail without it. Imported at module scope; the solver
  registry (`td/solvers/__init__.py`) skips that entry when the import fails.
- No linter/formatter/type-checker config in the repo (no ruff/mypy/flake8/black config
  found) -- style is convention-only, see `mem:conventions`.
