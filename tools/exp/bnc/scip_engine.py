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
"""
from __future__ import annotations

import os
import sys
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


class ScipHighs(highspy.Highs):
    """`highspy.Highs` for `draw._solve_group` whose `run` is `arms.scip_solve`."""

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
        res, x = arms.scip_solve(instance_of(self, loc), float(self.options.get("time_limit", 1e20)),
                                 log=lambda line: loc["log"](line), start=self.start)
        self.runs += 1
        self.solved = (key, res["status"])
        self.x = x
        has = x is not None
        self.status = {"optimal": highspy.HighsModelStatus.kOptimal,
                       "infeasible": highspy.HighsModelStatus.kInfeasible}.get(
            res["status"], highspy.HighsModelStatus.kTimeLimit)
        self.info = types.SimpleNamespace(
            objective_function_value=float(res["objective"]) if has else 0.0,
            primal_solution_status=2 if has else 0,
            mip_dual_bound=float(res["bound"]) if res["bound"] is not None else -np.inf,
            mip_node_count=int(res["nodes"] or 0))
        return highspy.HighsStatus.kOk

    def getModelStatus(self):
        return self.status

    def getInfo(self):
        return self.info

    def getSolution(self):
        return types.SimpleNamespace(col_value=[] if self.x is None else self.x.tolist())


def installed(draw):
    """A context in which `draw._solve_group` solves its MILPs with `ScipHighs`."""
    return capture.patched(draw, highspy=capture.Shim(ScipHighs))
