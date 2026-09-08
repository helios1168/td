"""Launching a driver detached, and knowing whether it is still running.

A grid takes minutes, so a driver is started detached and the UI polls for its output rather
than waiting on it: a Streamlit script rerun must never be blocked by a solver, and the run
must survive the browser tab closing.
"""
from __future__ import annotations

import os
import signal
from pathlib import Path

LOG = "run.log"


def _alive(pid: int) -> bool:
    """Is the launched driver still running?

    `os.kill(pid, 0)` alone is not enough and gets this exactly backwards for a finished run.
    The driver is a child of the Streamlit server, `launch` never waits on it, and nothing else
    does either, so on exit it stays a zombie: `os.kill` keeps succeeding, `status` keeps
    reporting `running`, and a run that finished minutes ago never shows its result.  Reaping it
    here with `WNOHANG` is what turns that into `done`.

    `waitpid` speaks only for our own children.  A run launched before the server restarted is
    not one, and raises `ChildProcessError`; it cannot be a zombie either, since its parent is
    gone and init has already reaped it, so `os.kill` answers correctly for that case.
    """
    try:
        reaped, _ = os.waitpid(pid, os.WNOHANG)
        if reaped == pid:
            return False
    except ChildProcessError:
        pass
    except OSError:
        return False
    try:
        os.kill(pid, 0)
    except (ProcessLookupError, PermissionError):
        return False
    return True


def cancel(pid: int) -> None:
    """Stop a running driver. Its process group goes with it (`start_new_session`)."""
    if _alive(pid):
        os.killpg(os.getpgid(pid), signal.SIGTERM)


def log_tail(out: Path, lines: int = 30) -> str:
    path = out / LOG
    return "\n".join(path.read_text().splitlines()[-lines:]) if path.exists() else ""
