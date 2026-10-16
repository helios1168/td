"""scip_engine.py -- `repair.py --engine scip` (#142 phase 2, P1): a window's MILP solved by arm c.

`draw._solve_group` builds a window's model inline and solves it in the same function with its own
`highspy.Highs`, and `draw.py` is not ours to change.  So, as `capture.py` does, this patches the
`highspy` that draw.py sees for the block: `ScipHighs` is the real `highspy.Highs` (the model, its
rows added one at a time as draw.py adds them, its options) whose `run` reads the group graph from
the caller's frame, rebuilds the model as an `inst_io.Inst` and solves it with `arms.scip_solve`:
PySCIPOpt with the constraint handler of arm c (a disconnected integer solution is cut off by lazy
integer a,b-separator rows, `sepcuts`), at `mip_rel_gap` 0 and absolute gap `arms.ABS_GAP`, one
thread, the time limit draw.py set.  Everything else is draw.py's own: the geodesic-DAG restriction
first, the neck rows and their loop, the band, the cap, the objective, the layered separator rows
and the construct seeds.

What `_solve_group` then reads back is HiGHS's vocabulary: `getModelStatus` is `kOptimal` (a
connected optimum proved to `ABS_GAP`), `kInfeasible` (SCIP's proof that no connected drawing of
the model exists) or `kTimeLimit`; `getInfo().primal_solution_status` is 2 when SCIP holds an
incumbent (always connected: the handler checks every solution) and 0 when it holds none.  A start
solution draw.py gives HiGHS (`setSolution`) is given to SCIP.  draw.py asks for a loose absolute
gap until it holds a connected drawing and then for `FINAL_ABS_GAP`; SCIP always solves at
`ABS_GAP`, and the repeat solve of an unchanged model is answered from the first (`ScipHighs.run`).

A SCIP solve runs in a child process (`solve_isolated`), so that a native fault (SIGSEGV inside
`model.optimize()` on a 1,396-ZCTA window, #142) ends the child and not the driver.  The child's
death is the engine's own stop reason, `crash` (with the signal), never `infeasible` and no ground
for window growth.  A crashed solve is repeated once, with the same time limit (on nw49-48 the
fault came at the limit itself, 1350 s of 1350, so the time left would be none), with
SCIP's primal heuristics off; a crash again leaves the window `unknown` (`kSolveError` to
`_solve_group`: no incumbent, so the group's status stays `unknown`).  Every solve, with its
setting and stop reason, is in the list `installed` yields (`repair.solve_window` files it under
each `tried` record's `engine_runs`).
"""
from __future__ import annotations

import contextlib
import importlib
import importlib.util
import os
import pickle
import signal
import subprocess
import sys
import tempfile
import time
import traceback
import types

import highspy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import arms  # noqa: E402
import capture  # noqa: E402
import inst_io  # noqa: E402


def column_labels(loc: dict, n: int) -> list:
    """`capture.column_labels`, with the columns a neck cut adds ([`n`, i]: a pair indicator or a
    `t`, `draw.NeckCut`) labelled too."""
    out = [None] * n
    for kind, name in (("x", "col"), ("y", "ycol"), ("c", "ccol"), ("e", "lcol"), ("s", "scol"),
                       ("f", "fcol")):
        for key, i in loc.get(name, {}).items():
            out[i] = [kind, *(key if isinstance(key, tuple) else (key,))]
    return [lab if lab is not None else ["n", i] for i, lab in enumerate(out)]


def instance_of(h, loc: dict) -> inst_io.Inst:
    """The window's MILP as it stands in `h`, with the group graph of `_solve_group`'s locals `loc`."""
    model = capture.lp_arrays(h)
    zs = list(loc["zs"])
    doc = {"schema": inst_io.SCHEMA, "id": "repair-window", "meta": {}, "model": model,
           "labels": column_labels(loc, len(model["cost"])),
           "graph": {"gadj": {a: sorted(b) for a, b in loc["gadj"].items()},
                     "vert_of": dict(loc["vert_of"]), "root": dict(loc["root"]),
                     "js": list(loc["js"]), "lo": loc["lo"], "hi": loc["hi"]},
           "draw": {"m": {z: float(loc["m"].get(z, 0.0)) for z in zs}, "zs": zs}}
    return inst_io.Inst(doc, "repair-window")


CHILD_SOLVER = "arms:scip_solve"    # "module:function" or "path/file.py:function" the child runs
LOG_TAG = "LOG "                    # a child's stdout line carrying one `log` line


def _resolve(spec: str):
    """The function named by `spec` ("module:function", or "path/file.py:function")."""
    where, _, name = spec.rpartition(":")
    if where.endswith(".py"):
        mod_spec = importlib.util.spec_from_file_location("scip_child_solver", where)
        mod = importlib.util.module_from_spec(mod_spec)
        mod_spec.loader.exec_module(mod)
    else:
        mod = importlib.import_module(where)
    return getattr(mod, name)


def _child(task_path: str, out_path: str) -> int:
    """The child process: runs the solver named in the pickled task, `log` lines going to the
    parent on stdout (anything else a library prints is sent to stderr), the result pickled to
    `out_path`."""
    try:
        import resource
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))        # no multi-GB core of a faulting solve
    except (ImportError, ValueError, OSError):
        pass
    pipe = os.fdopen(os.dup(1), "w", buffering=1)
    os.dup2(2, 1)
    with open(task_path, "rb") as fh:
        task = pickle.load(fh)

    def log(line):
        pipe.write(LOG_TAG + str(line).replace("\n", " ") + "\n")
        pipe.flush()

    try:
        inst = inst_io.Inst(task["doc"], "repair-window")
        out = _resolve(task["solver"])(inst, task["time_limit"], log, start=task["start"],
                                       heuristics=task["heuristics"])
        done = ("done", out)
    except BaseException:
        done = ("error", traceback.format_exc())
    with open(out_path, "wb") as fh:
        pickle.dump(done, fh, protocol=pickle.HIGHEST_PROTOCOL)
    return 0


def _signal_name(rc: int) -> str:
    try:
        return signal.Signals(-rc).name
    except ValueError:
        return f"signal {-rc}"


def solve_isolated(inst, time_limit: float, log, start=None, heuristics: bool = True) -> tuple:
    """`arms.scip_solve`'s (result, incumbent's columns or None), run in a child process.  If the
    child dies without a result (a signal, or an exit code of its own) the result is
    `status` "crash", with `signal` (its name, or None) and `exit_code`, no drawing and no bound:
    nothing the solve was doing is a proof.  An exception inside the solver is raised here, as it
    would be in process."""
    t0 = time.time()
    with tempfile.TemporaryDirectory(prefix="scip-child-") as tmp:
        task, out_path = os.path.join(tmp, "task.pkl"), os.path.join(tmp, "out.pkl")
        with open(task, "wb") as fh:
            pickle.dump({"doc": inst.doc, "time_limit": float(time_limit), "start": start,
                         "heuristics": heuristics, "solver": CHILD_SOLVER}, fh,
                        protocol=pickle.HIGHEST_PROTOCOL)
        proc = subprocess.Popen([sys.executable, os.path.abspath(__file__), "--child", task, out_path],
                                stdout=subprocess.PIPE, text=True)
        try:
            for line in proc.stdout:
                if line.startswith(LOG_TAG):
                    log(line[len(LOG_TAG):].rstrip("\n"))
            rc = proc.wait()
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait()
            proc.stdout.close()
        done = None
        if rc == 0 and os.path.exists(out_path):
            with open(out_path, "rb") as fh:
                done = pickle.load(fh)
    if done is not None:
        kind, val = done
        if kind == "error":
            raise RuntimeError("the SCIP child raised:\n" + val)
        return val
    sig = _signal_name(rc) if rc < 0 else None
    why = f"killed by {sig}" if sig else f"exit code {rc} without a result"
    res = arms._result("c", status="crash", seconds=time.time() - t0, signal=sig, exit_code=rc,
                       solver="pyscipopt (child process)", note=f"the SCIP child process was {why}")
    return res, None


class ScipHighs(highspy.Highs):
    """`highspy.Highs` for `draw._solve_group` whose `run` is `arms.scip_solve` (`solve_isolated`)."""

    runs_sink = None            # the list `installed` yields; one record per SCIP solve

    def __init__(self):
        super().__init__()
        self.options = {}
        self.start = None
        self.solved = None          # (columns, rows) of the last SCIP solve and what it returned
        self.runs = 0               # SCIP solves
        self.status = highspy.HighsModelStatus.kNotset
        self.info = types.SimpleNamespace(objective_function_value=0.0, primal_solution_status=0,
                                          mip_dual_bound=-np.inf, mip_node_count=0)
        self.x = None
        self.crash = None           # the note of a solve that crashed twice

    def setOptionValue(self, name, value):
        self.options[name] = value
        return super().setOptionValue(name, value)

    def setSolution(self, sol, *args):
        self.start = np.array(sol.col_value, dtype=float)
        return super().setSolution(sol, *args)

    def run(self):
        frame = sys._getframe(1)
        if frame.f_code.co_name != "_solve_group":
            raise RuntimeError(f"Highs.run called from {frame.f_code.co_name}, not _solve_group")
        loc = frame.f_locals
        key = (self.getNumCol(), self.getNumRow())
        if self.solved is not None and self.solved[0] == key and self.solved[1] == "optimal":
            return highspy.HighsStatus.kOk         # the same model, already proved to ABS_GAP
        inst, limit, log = instance_of(self, loc), float(self.options.get("time_limit", 1e20)), loc["log"]
        res, x = self._attempt(inst, limit, log, True)
        if res["status"] == "crash":
            log(f"  c: SCIP crashed ({res['note']}) after {res['seconds']:.0f}s; "
                f"retrying once with primal heuristics off")
            res, x = self._attempt(inst, limit, log, False)
        self.runs += 1
        self.solved = (key, res["status"])
        self.x = x
        has = x is not None
        self.crash = res["note"] if res["status"] == "crash" else None
        self.status = {"optimal": highspy.HighsModelStatus.kOptimal,
                       "infeasible": highspy.HighsModelStatus.kInfeasible,
                       "crash": highspy.HighsModelStatus.kSolveError}.get(
            res["status"], highspy.HighsModelStatus.kTimeLimit)
        self.info = types.SimpleNamespace(
            objective_function_value=float(res["objective"]) if has else 0.0,
            primal_solution_status=2 if has else 0,
            mip_dual_bound=float(res["bound"]) if res["bound"] is not None else -np.inf,
            mip_node_count=int(res["nodes"] or 0))
        return highspy.HighsStatus.kOk

    def _attempt(self, inst, limit, log, heuristics):
        """One isolated SCIP solve at `limit` seconds, recorded."""
        res, x = solve_isolated(inst, limit, log, start=self.start, heuristics=heuristics)
        if self.runs_sink is not None:
            self.runs_sink.append({"solve": self.runs + 1, "heuristics": heuristics,
                                   "status": res["status"], "signal": res.get("signal"),
                                   "exit_code": res.get("exit_code"), "limit": round(limit, 1),
                                   "seconds": round(res["seconds"] or 0.0, 1), "nodes": res["nodes"]})
        return res, x

    def modelStatusToString(self, st):
        if st == highspy.HighsModelStatus.kSolveError and self.crash:
            return "SCIP crash, unknown: " + self.crash
        return super().modelStatusToString(st)

    def getModelStatus(self):
        return self.status

    def getInfo(self):
        return self.info

    def getSolution(self):
        return types.SimpleNamespace(col_value=[] if self.x is None else self.x.tolist())


@contextlib.contextmanager
def installed(draw):
    """A context in which `draw._solve_group` solves its MILPs with `ScipHighs`; yields the list
    that gets a record per SCIP solve (setting, stop reason, signal, seconds)."""
    runs = []

    class Bound(ScipHighs):
        runs_sink = runs

    with capture.patched(draw, highspy=capture.Shim(Bound)):
        yield runs


if __name__ == "__main__" and len(sys.argv) == 4 and sys.argv[1] == "--child":
    sys.exit(_child(sys.argv[2], sys.argv[3]))
