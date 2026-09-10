"""Reading and building the incumbent rep layout, `reps.json`, that the Map and Reps tabs draw.

The app never opens the instance itself, so `reps.json` is written by a solver-venv driver,
`tools/rep_export.py`, launched detached the same way every other driver is. The export lives
outside `config.APP_RESULTS`, under `config.REP_CACHE`, keyed by the instance's own name rather
than by when it ran: an instance's layout does not change between runs, so there is at most one
export per instance and a second visit reuses it instead of asking again.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import streamlit as st

from app import config, runner, store


def reps_dir(instance: Path) -> Path:
    """`config.REP_CACHE / <instance stem>`, e.g. `.../app_reps/instance_descaled_v2_conus`."""
    stem = Path(instance).name.removesuffix(".json.gz")
    return config.REP_CACHE / stem


def reps_path(instance: Path) -> Path | None:
    path = reps_dir(instance) / "reps.json"
    return path if path.exists() else None


@st.cache_data(show_spinner=False)
def load(path: str, mtime: float) -> dict:
    return json.loads(Path(path).read_text())


def ensure(instance: Path, *, key: str) -> dict | None:
    """The loaded `reps.json` for `instance`, or, when it has not been built yet, a "Build rep
    territories" button that launches the export and returns `None` while it runs.

    `key` names the calling tab: the Map and Reps tabs both call this on the same rerun, and
    two buttons with the same label and no key are a `StreamlitDuplicateElementId`."""
    path = reps_path(instance)
    if path:
        return load(str(path), path.stat().st_mtime)

    out = reps_dir(instance)
    if (out / store.STEP).exists() and store.status(out) == "running":
        st.info("Building rep territories...")
        with st.expander("Log"):
            st.code(runner.log_tail(out) or "(no output yet)")
        return None

    if st.button("Build rep territories", key=f"build-reps-{key}"):
        out.mkdir(parents=True, exist_ok=True)
        argv = [str(config.SOLVER_PYTHON), str(config.CODE / "tools" / "rep_export.py"),
               str(instance), "--out", str(out), "--geo-cache", str(config.GEO_CACHE)]
        store.write_step(out, kind="reps", parent=None, params={"instance": str(instance)},
                         argv=argv, outputs={"reps": "reps.json", "timings": "timings.json"})
        runner.launch(out, argv, cwd=config.CODE, env={**os.environ, "PYTHONHASHSEED": "0"})
        st.rerun()
    return None
