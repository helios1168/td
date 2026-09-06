"""Paths and environment for the scenario app.

The app runs in its own virtualenv (`.venv-app`) and never imports `td`.  The solver stack is
version-frozen (`requirements.txt` header: "the zip50 anchor depends on these exact versions"),
so the app drives it by subprocess through `SOLVER_PYTHON`.  Everything here is therefore a
path, not an import.

`TD_REPO` overrides the repository the app reads from; it defaults to the hub checkout, because
the gitignored inputs (`instance_descaled_v2.json.gz`, `data/geo/`, `battery/results/`) live
there and are not copied into a worktree.
"""
from __future__ import annotations

import os
from pathlib import Path

REPO = Path(os.environ.get("TD_REPO", "/Users/ntlee/projects/td"))

SOLVER_PYTHON = REPO / ".venv" / "bin" / "python3"
INSTANCE = REPO / "instance_descaled_v2.json.gz"

RESULTS = REPO / "battery" / "results"
APP_RESULTS = RESULTS / "app"
SCENARIOS = REPO / "battery" / "scenarios"

FIGURES = REPO / "figures" / "app"
