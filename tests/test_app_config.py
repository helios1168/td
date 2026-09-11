"""test_app_config.py: app/config.py resolves REPO without a hard-coded home path, so the
module works verbatim from a checkout at any path (a sandboxed agent user, CI) and still points
a linked worktree at the main checkout, where the gitignored inputs live.

No Streamlit import: `app.config` is a plain module of paths and defaults (docstring), so this
runs under the solver venv with the rest of the suite.
"""
from __future__ import annotations

import importlib
import os
import sys
import tempfile
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app import config                            # noqa: E402
from td.solvers import milp_engines               # noqa: E402


def _reload_with(td_repo):
    old = os.environ.pop("TD_REPO", None)
    if td_repo is not None:
        os.environ["TD_REPO"] = td_repo
    try:
        importlib.reload(config)
        return config.REPO
    finally:
        os.environ.pop("TD_REPO", None)
        if old is not None:
            os.environ["TD_REPO"] = old
        importlib.reload(config)


def test_td_repo_env_var_overrides_repo():
    """TD_REPO, when set, is exactly what REPO resolves to."""
    assert str(_reload_with("/tmp/not-a-real-td-checkout")) == "/tmp/not-a-real-td-checkout"


def test_repo_default_is_the_main_checkout_of_this_repository():
    """Unset TD_REPO, REPO is the main checkout: this checkout in a plain clone or on the hub, the
    hub from a linked worktree.  Either way it carries the package, so `td/instance.py` exists."""
    repo = _reload_with(None)
    assert repo == config.main_checkout(config.CODE)
    assert (repo / "td" / "instance.py").exists(), repo


def test_main_checkout_reads_a_plain_clone_a_worktree_and_an_export():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        clone = base / "clone"
        (clone / ".git").mkdir(parents=True)
        hub = base / "hub"
        (hub / ".git" / "worktrees" / "w").mkdir(parents=True)
        wt = base / "wt"
        wt.mkdir()
        (wt / ".git").write_text(f"gitdir: {hub / '.git' / 'worktrees' / 'w'}\n", encoding="utf-8")
        rel = hub / "nested" / "wt2"
        rel.mkdir(parents=True)
        (rel / ".git").write_text("gitdir: ../../.git/worktrees/w\n", encoding="utf-8")
        export = base / "export"
        export.mkdir()
        for fn in (config.main_checkout, milp_engines._main_checkout):
            assert fn(clone) == clone
            assert fn(wt) == hub
            assert fn(rel) == hub.resolve()
            assert fn(export) == export
