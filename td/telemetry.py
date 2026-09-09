"""telemetry.py -- one driver run's timing record: nested phases, accumulated ticks, wall/CPU/RSS
totals, written next to the driver's other outputs.

Stdlib only, so importing this from library code (`td/solvers/centers.py`) costs nothing and
carries no dependency of its own::

    T = telemetry.Timings("clip")                 # driver name; created at the top of main
    with T.phase("load"): ...                     # nestable; a phase inside a phase gets depth 1
    with T.phase("solve") as ph:
        ...
        ph.note(nodes=res.mip_node_count, dual_bound=..., gap=res.mip_gap, status=...)
    T.tick("lp.assign", seconds)                   # accumulate many small calls under one name
    T.write(out_dir)                               # <out_dir>/timings.json

A `Timings` is the *active* one (module-level `current()`) from the moment it is created until
`write()` or `close()` pops it, so code with no `Timings` in hand -- `td/solvers/centers.py`'s
`assign`, or a pure function like `tools/geom_export.py`'s `export` -- can still record a tick or
a phase through the module-level `tick`/`phase` hooks below, which are no-ops with none active.
That is what keeps a library import-clean: it calls `telemetry.tick(...)`, never constructs or
threads a `Timings` itself.

A worker process (`tools/run_draw.py`'s process pool) has no access to the parent's `Timings` --
`multiprocessing` starts a fresh interpreter -- so a pool job makes its own scratch `Timings`,
reads back what it caught, and `close()`s it without writing a file; the parent sums the totals
into its own `Timings` under the same name (`Timings.tick(..., n=...)` takes the count along with
the seconds, for exactly that kind of bulk merge).
"""
from __future__ import annotations

import cProfile
import json
import os
import resource
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timezone

_stack: list["Timings"] = []
_pending_profiler: "cProfile.Profile | None" = None


def current() -> "Timings | None":
    """The active `Timings`, innermost first -- `None` if nothing has been created (or the last
    one created has already been written or closed)."""
    return _stack[-1] if _stack else None


def tick(name: str, seconds: float, *, n: int = 1) -> None:
    """Forward to the active `Timings`; a no-op with none active.  The hook library code calls
    (`td/solvers/centers.py`'s `assign`) so it stays import-clean -- it never sees a `Timings`."""
    t = current()
    if t is not None:
        t.tick(name, seconds, n=n)


@contextmanager
def phase(name: str):
    """The same hook as `tick`, for a named span: forwards to the active `Timings.phase`, or
    yields a `_Phase` that goes nowhere when none is active.  For a pure function (`export` in
    `tools/geom_export.py`) that has no `Timings` to hold and must not change its own signature
    to accept one."""
    t = current()
    if t is None:
        yield _Phase({"note": {}})
    else:
        with t.phase(name) as ph:
            yield ph


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _cpu_time() -> float:
    """This process's own CPU time plus its reaped children's -- `time.process_time()` never
    counts a child, and a pool worker's CPU is only visible here once it has been joined."""
    t = os.times()
    return time.process_time() + t.children_user + t.children_system


def _peak_rss_mb() -> float:
    """Peak resident set size in MB.  `ru_maxrss` is bytes on macOS and kilobytes on Linux --
    the same field, two units -- so the platform decides the divisor."""
    ru = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return ru / (1024.0 * 1024.0) if sys.platform == "darwin" else ru / 1024.0


class _Phase:
    """What `Timings.phase`/`telemetry.phase` yield.  `note(**kv)` attaches metadata to the
    phase's record; with no active `Timings` the record is a throwaway dict nobody reads."""

    def __init__(self, record: dict) -> None:
        self._record = record

    def note(self, **kv) -> None:
        self._record["note"].update(kv)


class Timings:
    """One driver run.  Active (pushed onto the module stack) from construction until `write`
    or `close` pops it, so `telemetry.tick`/`telemetry.phase` reach it without being threaded
    through every call in between."""

    def __init__(self, driver: str) -> None:
        self.driver = driver
        self.argv = list(sys.argv)
        self.phases: list[dict] = []
        self.ticks: dict[str, dict] = {}
        self._open: list[dict] = []            # phase records currently entered, for depth
        self._started_iso = _now_iso()
        self._wall0 = time.monotonic()
        self._cpu0 = _cpu_time()
        self._profiler = _pending_profiler
        _stack.append(self)

    def _pop(self) -> None:
        if _stack and _stack[-1] is self:
            _stack.pop()
        elif self in _stack:
            _stack.remove(self)

    def close(self) -> None:
        """Deactivate without writing anything -- a scratch `Timings` used only to catch ticks
        inside a pool worker (`tools/run_draw.py`'s `draw_job`), read back by the caller."""
        self._pop()

    @contextmanager
    def phase(self, name: str):
        depth = len(self._open)
        record = dict(name=name, depth=depth, start=time.monotonic() - self._wall0,
                     wall=0.0, cpu=0.0, note={})
        t0_wall, t0_cpu = time.monotonic(), _cpu_time()
        self._open.append(record)
        self.phases.append(record)
        try:
            yield _Phase(record)
        finally:
            self._open.pop()
            record["wall"] = time.monotonic() - t0_wall
            record["cpu"] = _cpu_time() - t0_cpu

    def tick(self, name: str, seconds: float, *, n: int = 1) -> None:
        rec = self.ticks.setdefault(name, {"n": 0, "wall": 0.0})
        rec["n"] += n
        rec["wall"] += float(seconds)

    def write(self, out_dir: str) -> str:
        """`<out_dir>/timings.json`, and, under `TD_PROFILE=1`, `<out_dir>/profile.prof` from
        the profiler `maybe_profile` started.  A directory can hold more than one driver's
        output (a clip run's own directory, followed by the geom export chained after it): if
        `timings.json` is already there and belongs to a different driver, this writes
        `timings.<driver>.json` instead, leaving the first file alone; the same driver writing
        twice (a rerun) still overwrites its own file.  `profile.prof` follows the same rule as
        `profile.<driver>.prof`.  Deactivates this `Timings` (see `close`)."""
        payload = dict(
            driver=self.driver, argv=self.argv,
            started=self._started_iso, finished=_now_iso(),
            wall=time.monotonic() - self._wall0,
            cpu=_cpu_time() - self._cpu0,
            rss_peak_mb=_peak_rss_mb(),
            phases=self.phases, ticks=self.ticks,
        )
        os.makedirs(out_dir, exist_ok=True)
        name = "timings.json"
        existing = os.path.join(out_dir, name)
        if os.path.exists(existing):
            with open(existing, encoding="utf-8") as fh:
                other_driver = json.load(fh).get("driver")
            if other_driver != self.driver:
                name = f"timings.{self.driver}.json"
        path = os.path.join(out_dir, name)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
            fh.write("\n")
        if os.environ.get("TD_PROFILE") == "1" and self._profiler is not None:
            prof_name = "profile.prof" if name == "timings.json" else f"profile.{self.driver}.prof"
            self._profiler.dump_stats(os.path.join(out_dir, prof_name))
        self._pop()
        return path


def maybe_profile(main):
    """`main` -> a wrapper that runs it under `cProfile` when `TD_PROFILE=1` in the environment,
    otherwise `main` unchanged.

    The profiler is stashed where the next `Timings` created inside `main` will pick it up
    (`Timings.__init__` reads `_pending_profiler`), since profiling has to wrap the whole call --
    `Timings` itself is created inside `main`, so the wrapper cannot hand it over directly.
    `Timings.write` dumps the stats once `main` reaches it, which is also where profiling in
    effect stops (`Profile.dump_stats` disables the profiler as part of writing the file).
    """
    def wrapper(*args, **kwargs):
        if os.environ.get("TD_PROFILE") != "1":
            return main(*args, **kwargs)
        global _pending_profiler
        prof = cProfile.Profile()
        _pending_profiler = prof
        prof.enable()
        try:
            return main(*args, **kwargs)
        finally:
            prof.disable()
            _pending_profiler = None
    return wrapper
