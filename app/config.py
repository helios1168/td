"""Paths and defaults for the scenario app.

The app runs in its own virtualenv (`.venv-app`) and never imports `td`.  The solver stack is
version-frozen (`requirements.txt` header: "the zip50 anchor depends on these exact versions"),
so the app drives it by subprocess through `SOLVER_PYTHON`.  Everything here is therefore a
path or a default, not an import.

Two roots, and they are not the same one.  `REPO` is the hub checkout, because the gitignored
inputs (the instances, `data/geo/`, `battery/results/`) live there and are never copied into a
worktree.  `CODE` is this checkout, because the drivers a run launches are the ones sitting
beside this file, which on a track branch are not the hub's.

Only CONUS instances are offered.  Blank-state, Alaska and Hawaii zips enter no step (the
ground-set invariant), and every driver asserts it at load, so an instance that carries them
would only fail later and more confusingly.
"""
from __future__ import annotations

import os
from pathlib import Path

REPO = Path(os.environ.get("TD_REPO", "/Users/ntlee/projects/td"))
CODE = Path(__file__).resolve().parents[1]

# Overridable independently of TD_REPO: a worktree has no `.venv` of its own (CLAUDE.md,
# "Environment"), so a run against a worktree needs the hub's interpreter under a different var.
SOLVER_PYTHON = Path(os.environ.get("TD_SOLVER_PYTHON", REPO / ".venv" / "bin" / "python3"))
OPT_PYTHON = Path(os.environ.get("TD_OPT_PYTHON", REPO / ".venv-opt" / "bin" / "python3"))

INSTANCES = sorted(REPO.glob("instance_descaled_*_conus.json.gz"))
INSTANCE = REPO / "instance_descaled_v2_conus.json.gz"

RESULTS = REPO / "battery" / "results"
APP_RESULTS = RESULTS / "app"
GEO_CACHE = REPO / "data" / "geo"
REP_CACHE = RESULTS / "app_reps"

# Grid defaults. k runs 10 to 20 by 2 because that is the review's range; delta is fixed at 10%
# by the same decision, and is an input here only so a one-off can move it.
KS = [10, 12, 14, 16, 18, 20]
DELTA = 0.10
SEEDS = "0-4"
WORKERS = 2
THETA = 0.40
LAM = 0.30
FILLER = "full"
TIME_LIMIT = 600
