"""Launching a driver detached, and knowing whether it is still running.

A grid takes minutes, so a driver is started detached and the UI polls for its output rather
than waiting on it: a Streamlit script rerun must never be blocked by a solver, and the run
must survive the browser tab closing.
"""
from __future__ import annotations

import os
import shlex
import signal
import subprocess
from datetime import datetime
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


def launch(run: Path, argv: list[str], *, cwd: Path, env: dict | None = None) -> int:
    """Start `argv` detached, its output appended to `<run>/run.log`, and record the pid and
    start time in `run`'s own `step.json` (`app.store.update_step`) so `store.status` can find
    it. Never waited on here either: `_alive` is what later notices it finished."""
    from . import store
    run = Path(run)
    with open(run / LOG, "ab") as log:
        proc = subprocess.Popen(argv, cwd=str(cwd), stdout=log, stderr=subprocess.STDOUT,
                                env=env, start_new_session=True)
    started = datetime.now().isoformat(timespec="seconds")
    store.update_step(run, pid=proc.pid, started=started)
    return proc.pid


def launch_chain(chain: list[tuple[Path, list[str]]], *, cwd: Path,
                 env: dict | None = None) -> int:
    """Run a whole chain, draw then clip then geom, as one detached shell; each command's own
    output goes to its own run directory's `run.log`. One pid covers the whole chain, so it is
    recorded on every distinct run directory's `step.json`: a member still waiting on an
    earlier command reads `running` for exactly that reason (`app.store.status`)."""
    from . import store
    parts = []
    logged: set[Path] = set()
    for run, argv in chain:
        run = Path(run)
        cmd = " ".join(shlex.quote(a) for a in argv)
        # a later member in the same dir (geom after clip) appends rather than truncates
        redirect = ">>" if run in logged else ">"
        logged.add(run)
        parts.append(f"{cmd} {redirect} {shlex.quote(str(run / LOG))} 2>&1")
    script = " && ".join(parts)
    proc = subprocess.Popen(["/bin/sh", "-c", script], cwd=str(cwd), env=env,
                            start_new_session=True)
    started = datetime.now().isoformat(timespec="seconds")
    seen: set[Path] = set()
    for run, _argv in chain:
        run = Path(run)
        if run in seen:
            continue
        seen.add(run)
        store.update_step(run, pid=proc.pid, started=started)
    return proc.pid
