"""test_app_runner.py -- app/runner.py: a finished driver must stop reading as `running`.

`app/` is otherwise untested (docs/APP.md section 5), because Streamlit cannot be driven
headlessly.  `_alive` is the exception worth covering: it is a plain function over a pid, it
decides everything `status` reports, and it got a finished run wrong for as long as the app has
existed.  The driver is a child of the Streamlit server and nobody waits on it, so on exit it
becomes a zombie, `os.kill(pid, 0)` keeps succeeding, and a run that finished minutes ago is
still shown in flight.  These tests run a real child and never wait on it, which is exactly the
shape that failed.

No Streamlit import: `app.runner` imports nothing that pulls in streamlit or pandas, so this
runs under the solver venv with the rest of the suite.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app import runner                            # noqa: E402


def test_a_child_that_exited_is_not_alive_even_though_nobody_waited_on_it():
    """The zombie case.  `subprocess.Popen` and then no `wait`, the way `runner.launch` leaves
    it: once the child exits, `_alive` must report False within a moment.  Before `_alive`
    reaped, `os.kill(pid, 0)` succeeded on the zombie and this loop never ended."""
    proc = subprocess.Popen([sys.executable, "-c", "pass"])
    deadline = time.time() + 10.0
    while time.time() < deadline:
        if not runner._alive(proc.pid):
            break
        time.sleep(0.05)
    else:
        raise AssertionError("a child that exited still reads as alive; the zombie is unreaped")

    # And it stays False once reaped: waitpid now raises ChildProcessError and os.kill has to
    # answer, which it does, because a reaped pid is gone.
    assert not runner._alive(proc.pid)


def test_a_running_child_is_alive_until_it_is_stopped():
    """The other direction, so the reap cannot be mistaken for `always False`: a child that is
    still running reads alive, and reads dead once killed."""
    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    try:
        assert runner._alive(proc.pid)
    finally:
        proc.kill()

    deadline = time.time() + 10.0
    while time.time() < deadline:
        if not runner._alive(proc.pid):
            break
        time.sleep(0.05)
    else:
        raise AssertionError("a killed child still reads as alive")


def test_a_pid_that_was_never_ours_is_answered_by_kill_not_waitpid():
    """`os.getppid()` is this process's parent and never its child, so `waitpid` raises
    `ChildProcessError` and the `os.kill` fallback carries the answer.  That is the path a run
    launched before a Streamlit restart takes."""
    assert runner._alive(os.getppid())
