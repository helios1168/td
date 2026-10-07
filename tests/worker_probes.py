"""Probes for #123's worker-process tests (`test_contig_realize.py`): a dict that acts when a
spawned worker process unpickles it, in this importable module so the worker can.

`Probe(d, acts)` pickles as the dict `d`; each act (depth, name, arg) runs `name(arg)` of this
module in a process `depth` spawns below the test (`_depth`: a repair channel 1, its windows 2;
a `WindowPool`'s windows started by the test 1) as it unpickles the dict, its shared data or a
task.  The acts record to files, so the test reads what the workers did.
"""
from __future__ import annotations

import os
import signal
import sys
import time


class Probe(dict):
    def __init__(self, d=(), acts=()):
        super().__init__(d)
        self.acts = tuple(acts)

    def __reduce__(self):
        return _unpickled, (dict(self), self.acts)


def _depth() -> int:
    import multiprocessing
    return len(multiprocessing.current_process()._identity)


def _unpickled(d: dict, acts: tuple) -> Probe:
    for depth, name, arg in acts:
        if depth == _depth():
            globals()[name](arg)
    return Probe(d, acts)


def _append(path: str, line: str) -> None:
    with open(path, "a") as fh:
        fh.write(line + "\n")


def lines(path: str) -> list:
    return open(path).read().splitlines() if os.path.exists(path) else []


def pid(path: str) -> None:
    _append(path, str(os.getpid()))


def sleep(arg: tuple) -> None:
    """Record the pid to `path`, then sleep `seconds`: a window stuck in a long solve, or a
    worker slow to start."""
    path, seconds = arg
    pid(path)
    time.sleep(seconds)


def fail_after(path: str) -> None:
    """Wait until a pid is in `path` (a window has started), then fail."""
    end = time.time() + 120
    while not lines(path) and time.time() < end:
        time.sleep(0.05)
    raise RuntimeError("probe: this channel fails")


def fail_first(path: str) -> None:
    """Record the pid; the first to record fails once another has, the others sleep 120 s."""
    pid(path)
    if lines(path)[0] != str(os.getpid()):
        time.sleep(120.0)
        return
    end = time.time() + 120
    while len(lines(path)) < 2 and time.time() < end:
        time.sleep(0.05)
    raise RuntimeError("probe: this drawing fails")


def sleep_under(arg: tuple) -> None:
    """`sleep` in a window whose parent's pid is in `parents`: one channel's windows stuck."""
    parents, path, seconds = arg
    if str(os.getppid()) in lines(parents):
        sleep((path, seconds))


def die_later(arg: tuple) -> None:
    """In a thread, once a window is stuck (a pid in `windows`) and `after` exists: write
    `dying` and exit at once, no cleanup, as a channel killed from outside does."""
    import threading
    windows, after, dying = arg

    def die():
        while not (lines(windows) and os.path.exists(after)):
            time.sleep(0.05)
        time.sleep(0.5)
        _append(dying, "")
        os._exit(1)
    threading.Thread(target=die, daemon=True).start()


def _linger(done: str, dying: str) -> None:
    _append(done, "")
    end = time.time() + 120
    while not os.path.exists(dying) and time.time() < end:
        time.sleep(0.05)
    time.sleep(1.0)


def linger(arg: tuple) -> None:
    """As this worker exits, its result sent: write `done`, then wait for `dying` and a second
    more, so its parent, joining it, next acts once that other channel is dead."""
    import multiprocessing.util
    multiprocessing.util.Finalize(None, _linger, args=arg, exitpriority=100)


class Unsendable(dict):
    """A dict that cannot be pickled: a task holding it fails in `Connection.send`."""
    def __reduce__(self):
        raise RuntimeError("probe: this task cannot be sent")


def _interrupt(seconds: float) -> None:
    time.sleep(1.0)
    os.kill(os.getppid(), signal.SIGINT)
    time.sleep(seconds)


def interrupt_parent_at_exit(seconds: float) -> None:
    """As this worker exits, its result sent: a second later (its parent joining it) send the
    parent SIGINT, a Ctrl-C, then take `seconds` more to exit."""
    import multiprocessing.util
    multiprocessing.util.Finalize(None, _interrupt, args=(seconds,), exitpriority=100)


def interrupt_parent_after(arg: tuple) -> None:
    """In a thread: once a window is running (a pid in `windows`), wait `delay` seconds and send
    the parent SIGINT, a Ctrl-C."""
    import threading
    windows, delay = arg

    def interrupt():
        while not lines(windows):
            time.sleep(0.05)
        time.sleep(delay)
        os.kill(os.getppid(), signal.SIGINT)
    threading.Thread(target=interrupt, daemon=True).start()


def block_sigterm(_) -> None:
    """A channel deaf to SIGTERM, as one stuck in a long solve is: only a kill stops it."""
    signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGTERM})


def threads(path: str) -> None:
    """Record `draw.THREADS` and whether HiGHS's thread pool is already sized: a solve at
    `threads` 2 is "Not Set" once a solve at 1 has sized it (trap 18)."""
    import highspy
    h = highspy.Highs()
    h.setOptionValue("output_flag", False)
    h.setOptionValue("threads", 2)
    h.addVar(0.0, 1.0)
    h.run()
    status = h.modelStatusToString(h.getModelStatus()).replace(" ", "_")
    _append(path, f"{sys.modules['contig_draw'].THREADS} {status}")
