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

# Overridable independently of TD_REPO: a worktree has no `.venv` of its own (CLAUDE.md,
# "Environment"), so a run against a worktree needs the hub's interpreter under a different var.
SOLVER_PYTHON = Path(os.environ.get("TD_SOLVER_PYTHON", REPO / ".venv" / "bin" / "python3"))
INSTANCE = REPO / "instance_descaled_v2.json.gz"

RESULTS = REPO / "battery" / "results"
APP_RESULTS = RESULTS / "app"
SCENARIOS = REPO / "battery" / "scenarios"

# Under `battery/results/` on purpose: `figures/` is tracked, because a committed map is a
# primary artifact, and app renderings are neither reviewed nor committed.
FIGURES = APP_RESULTS / "figures"

# The Headline tab's one hard-wired case: the committed k=18 draw the headline cell was solved
# against, and the shipped Track 2 anchored delta=5% cell it is compared to.
COMMITTED_DRAW = RESULTS / "draw_k18_v2_20260904" / "k18" / "draw.csv"
HEADLINE_CELL = RESULTS / "borders_k18_v2_20260907" / "track2_anchored" / "d0.05" / "d0.05"
GEO_CACHE = REPO / "data" / "geo"
STATE_SHARES = APP_RESULTS / "state_shares.json"
