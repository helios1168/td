"""test_app_config.py -- app/config.py: REPO must resolve without a hard-coded /Users/ntlee
literal, so the module works verbatim from a checkout at any path (a sandboxed agent user, CI),
while behaving identically on the hub.

No Streamlit import: `app.config` is a plain module of paths and defaults (docstring), so this
runs under the solver venv with the rest of the suite.
"""
from __future__ import annotations

import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app import config                            # noqa: E402


def test_td_repo_env_var_overrides_repo():
    """TD_REPO, when set, is exactly what REPO resolves to -- no home()/hub guess involved."""
    old = os.environ.get("TD_REPO")
    os.environ["TD_REPO"] = "/tmp/not-a-real-td-checkout"
    try:
        importlib.reload(config)
        assert str(config.REPO) == "/tmp/not-a-real-td-checkout"
    finally:
        if old is None:
            os.environ.pop("TD_REPO", None)
        else:
            os.environ["TD_REPO"] = old
        importlib.reload(config)


def test_repo_default_is_the_home_projects_td_hub():
    """Unset TD_REPO, REPO falls back to ~/projects/td -- the old hard-coded literal's value on
    this machine, but derived rather than written out, so it moves with the user's home."""
    old = os.environ.pop("TD_REPO", None)
    try:
        importlib.reload(config)
        from pathlib import Path
        assert config.REPO == Path.home() / "projects" / "td"
        if config.REPO.exists():       # true on the hub; a fresh checkout elsewhere has none
            assert (config.REPO / "td" / "instance.py").exists()
    finally:
        if old is not None:
            os.environ["TD_REPO"] = old
        importlib.reload(config)
