"""arms.py -- four solvers of the same model and objective (#142, A1).

    solve(arm, inst, time_limit, threads, log) -> result dict

The model is an instance's (`inst_io.Inst`): draw.py's group MILP, with the same objective, whose
connectivity (one piece per district on the group graph) is enforced

- arm `a`: by draw.py itself, `draw._solve_group` on the exported call with `dag` False, the
  single-commodity flow rows (`flow`) and per-layer separators (`layers`), then its
  solve-check-cut loop as implemented (it also starts from `construct`'s drawing when it finds
  one, which the other arms are not given);
- arm `b`: HiGHS solve, find the detached components of the integer optimum, add the minimal
  a,b-separator rows of `sepcuts` (no flow), solve again, until the optimum is connected;
- arm `c`: PySCIPOpt (SCIP 10) with a constraint handler whose `conscheck`, `consenfolp`,
  `consenfops` and `conslock` reject a disconnected integer solution and add the same rows as
  lazy cuts at the node; with `frac_root` it also separates fractional rows (`sepcuts`) at the
  root;
- arm `d`: HiGHS with `kCallbackMipDefineLazyConstraints`, if `probe_highs_lazy` shows the callback
  can define a constraint; else the arm returns status `not usable` with what the probe saw.

Every arm runs at `mip_rel_gap` 0 (trap 12; HiGHS and SCIP at an absolute gap of `ABS_GAP`, as
draw.py's final solves), with `threads` for HiGHS (SCIP builds without parallel mode run one),
one process, `time_limit` seconds of wall time in all.  A result:

    arm, status (optimal | feasible | infeasible | unknown | not usable), objective, bound, gap
    (relative), nodes, seconds, rounds, cuts, owner {ZCTA: district} (every status with a drawing),
    note, solver

`optimal` is a connected optimum proved to `ABS_GAP`; `feasible` a connected drawing without the
proof; `infeasible` a proof that no connected drawing exists in the group; `unknown` neither.
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import capture  # noqa: E402
import inst_io  # noqa: E402
import sepcuts  # noqa: E402

ABS_GAP = 1e-6
ARMS = ("a", "b", "c", "d")


def _result(arm: str, **kw) -> dict:
    out = {"arm": arm, "status": "unknown", "objective": None, "bound": None, "gap": None,
           "nodes": None, "seconds": None, "rounds": 0, "cuts": 0, "owner": None, "note": "",
           "solver": ""}
    out.update(kw)
    return out


def _gap(obj, bound):
    if obj is None or bound is None:
        return None
    return abs(obj - bound) / max(1e-12, abs(obj))


# ------------------------------------------------------------------------------ arm a
def arm_a(inst, time_limit: float, threads: int, log=print, flow: bool = True,
          layers: bool = True) -> dict:
    """draw.py's complete model (`dag` False) by draw.py's own solve path."""
    import highspy
    draw = capture.load_draw()
    snap = inst.doc["draw"]
    args, kw = capture.rebuild_args(snap)
    args = args[:19] + (float(time_limit),)
    kw.update(dag=False, flow=flow, layers=layers, log=log)
    seen = {"nodes": 0, "runs": 0, "bound": None}

    class H(highspy.Highs):
        def run(self):
            r = super().run()
            info = self.getInfo()
            seen["runs"] += 1
            seen["nodes"] += max(0, int(info.mip_node_count))
            if np.isfinite(info.mip_dual_bound):        # each solve's bound holds for the original
                seen["bound"] = max(seen["bound"] or -np.inf, info.mip_dual_bound)
            return r

    t0 = time.time()
    old = draw.THREADS
    draw.THREADS = threads
    try:
        with capture.centres_patch(draw, snap), capture.patched(draw, highspy=capture.Shim(H)):
            g = draw._solve_group(*args, **kw)
    finally:
        draw.THREADS = old
    status = {"optimal": "optimal", "connected": "feasible", "infeasible": "infeasible"}.get(g.status, "unknown")
    owner = dict(g.owner) if g.owner else None
    bound = g.bound if g.bound is not None else seen["bound"]
    gap = g.gap if g.gap is not None else _gap(g.objective, bound)
    return _result("a", status=status, objective=g.objective, bound=bound, gap=gap,
                   nodes=seen["nodes"], seconds=time.time() - t0, rounds=g.iterations, cuts=g.cuts,
                   owner=owner, note=g.note, solver=f"highs {highspy.Highs().version()} via draw.py",
                   flow=flow, layers=layers)


# ------------------------------------------------------------------------------ arm b
def arm_b(inst, time_limit: float, threads: int, log=print, max_per_component=None) -> dict:
    """HiGHS solve, separate integer a,b-separator rows, solve again."""
    import highspy
    t0 = time.time()
    G = sepcuts.Graphs(inst)
    h = inst.highs(threads=threads)
    inf = highspy.kHighsInf
    out = _result("b", solver=f"highs {h.version()}")
    nodes, bound = 0, None
    while True:
        left = t0 + time_limit - time.time()
        if left <= 0.5:
            out["note"] = "time limit"
            break
        h.setOptionValue("time_limit", float(left))
        h.run()
        out["rounds"] += 1
        st, info = h.getModelStatus(), h.getInfo()
        nodes += max(0, int(info.mip_node_count))
        if np.isfinite(info.mip_dual_bound):
            bound = info.mip_dual_bound if bound is None else max(bound, info.mip_dual_bound)
        log(f"  b round {out['rounds']}: {h.modelStatusToString(st)}, objective "
            f"{info.objective_function_value:.6g}, bound {info.mip_dual_bound:.6g}, "
            f"{out['cuts']} cuts, {time.time() - t0:.1f}s")
        if st == highspy.HighsModelStatus.kInfeasible:
            out["status"], out["note"] = "infeasible", f"proved at round {out['rounds']}"
            break
        if info.primal_solution_status != 2:
            out["note"] = f"no incumbent ({h.modelStatusToString(st)})"
            break
        x = np.array(h.getSolution().col_value)
        rows = G.integer_cuts(x, max_per_component)
        optimal = st == highspy.HighsModelStatus.kOptimal
        if not rows:
            out.update(objective=float(info.objective_function_value), owner=inst.owner_of(x),
                       status="optimal" if optimal else "feasible")
            if not optimal:
                out["note"] = "time limit: connected incumbent"
            break
        inst_io.add_rows(h, rows)
        out["cuts"] += len(rows)
        if not optimal:
            out["note"] = "time limit with a detached incumbent"
            break
    out.update(bound=bound, nodes=nodes, seconds=time.time() - t0)
    out["gap"] = _gap(out["objective"], bound)
    if out["status"] == "optimal":
        out["bound"], out["gap"] = out["objective"], 0.0
    return out


# ------------------------------------------------------------------------------ arm c
def scip_model(inst):
    """(a PySCIPOpt model of the instance's base MILP, its variables by column)."""
    from pyscipopt import Model, quicksum
    model = Model("bnc")
    model.hideOutput()
    xs = []
    for i in range(inst.n):
        ub = None if np.isinf(inst.ub[i]) else float(inst.ub[i])
        lb = None if np.isinf(inst.lb[i]) else float(inst.lb[i])
        xs.append(model.addVar(name=f"v{i}", vtype="B" if inst.integer[i] and lb == 0 and ub == 1
                               else ("I" if inst.integer[i] else "C"), lb=lb, ub=ub,
                               obj=float(inst.cost[i])))
    model.setMinimize()
    for r in range(inst.n_rows):
        a, b = inst.row_start[r], inst.row_start[r + 1]
        expr = quicksum(float(v) * xs[int(i)] for i, v in zip(inst.row_idx[a:b], inst.row_val[a:b]))
        lo, hi = inst.row_lo[r], inst.row_hi[r]
        if lo == hi:
            model.addCons(expr == float(lo))
            continue
        if np.isfinite(lo):
            model.addCons(expr >= float(lo))
        if np.isfinite(hi):
            model.addCons(expr <= float(hi))
    return model, xs


def arm_c(inst, time_limit: float, threads: int, log=print, frac_root: bool = False,
          max_per_component=None) -> dict:
    """PySCIPOpt with a constraint handler adding integer separator rows as lazy cuts."""
    return scip_solve(inst, time_limit, log, frac_root, max_per_component)[0]


def scip_solve(inst, time_limit: float, log=print, frac_root: bool = False,
               max_per_component=None, start=None, heuristics: bool = True) -> tuple:
    """(arm c's result, the incumbent's value of every column or None): `arm_c`'s solver, one
    thread (SCIP built without parallel mode), importable by `repair.py --engine scip`
    (`scip_engine.py`).  `start`, a value for every column, is given to SCIP as a primal solution
    before the solve (kept only if it is feasible for the model and the handler).  With
    `heuristics` false SCIP's primal heuristics are off (`scip_engine.py`'s retry after a native
    crash of the default setting)."""
    import pyscipopt
    from pyscipopt import SCIP_PARAMSETTING, SCIP_RESULT, Conshdlr, quicksum
    t0 = time.time()
    G = sepcuts.Graphs(inst)
    model, xs = scip_model(inst)
    xcols = sorted(inst.xcol.values())
    stats = {"cuts": 0, "calls": 0, "frac": 0}

    def add_rows(handler, rows):
        for lo, hi, idx, val in rows:
            expr = quicksum(float(v) * xs[int(i)] for i, v in zip(idx, val))
            handler.model.addCons(expr <= float(hi), local=False, modifiable=False, removable=False,
                                  stickingatnode=False)
            stats["cuts"] += 1

    class Conn(Conshdlr):
        def _cut_if_detached(self, vec) -> list:
            return G.integer_cuts(vec, max_per_component)

        def _vector(self, getter):
            x = np.zeros(inst.n)
            for i in xcols:
                x[i] = getter(xs[i])
            return x

        def conscheck(self, constraints, solution, checkintegrality, checklprows, printreason, completely):
            x = self._vector(lambda v: self.model.getSolVal(solution, v))
            return {"result": SCIP_RESULT.INFEASIBLE if G.detached(np.round(x)) else SCIP_RESULT.FEASIBLE}

        def _enforce(self, getter):
            stats["calls"] += 1
            x = self._vector(getter)
            if np.max(np.abs(x[xcols] - np.round(x[xcols]))) > 1e-6:
                return {"result": SCIP_RESULT.FEASIBLE}         # branching comes first
            rows = G.integer_cuts(np.round(x), max_per_component)
            if not rows:
                return {"result": SCIP_RESULT.FEASIBLE}
            add_rows(self, rows)
            return {"result": SCIP_RESULT.CONSADDED}

        def consenfolp(self, constraints, nusefulconss, solinfeasible):
            return self._enforce(lambda v: v.getLPSol())

        def consenfops(self, constraints, nusefulconss, solinfeasible, objinfeasible):
            return self._enforce(lambda v: self.model.getSolVal(None, v))

        def conslock(self, constraint, locktype, nlockspos, nlocksneg):
            for i in xcols:
                self.model.addVarLocks(xs[i], nlockspos + nlocksneg, nlockspos + nlocksneg)

        def conssepalp(self, constraints, nusefulconss):
            if not frac_root or self.model.getDepth() > 0:
                return {"result": SCIP_RESULT.DIDNOTFIND}
            x = self._vector(lambda v: v.getLPSol())
            rows = G.fractional_cuts(x)
            if not rows:
                return {"result": SCIP_RESULT.DIDNOTFIND}
            for lo, hi, idx, val in rows:
                cut = self.model.createEmptyRowUnspec(name="sep", lhs=None, rhs=float(hi), local=False,
                                                      modifiable=False, removable=True)
                self.model.cacheRowExtensions(cut)
                for i, v in zip(idx, val):
                    self.model.addVarToRow(cut, xs[int(i)], float(v))
                self.model.flushRowExtensions(cut)
                self.model.addCut(cut, forcecut=True)
                stats["frac"] += 1
            return {"result": SCIP_RESULT.SEPARATED}

    hdlr = Conn()
    model.includeConshdlr(hdlr, "conn", "district connectivity by separator rows",
                          sepapriority=100 if frac_root else -1, enfopriority=-100, chckpriority=-100,
                          sepafreq=1 if frac_root else -1, propfreq=-1, eagerfreq=-1, maxprerounds=0,
                          needscons=False)
    cons = model.createCons(hdlr, "conn_all", initial=False, separate=frac_root, enforce=True,
                            check=True, propagate=False)
    model.addPyCons(cons)
    model.setRealParam("limits/gap", 0.0)
    model.setRealParam("limits/absgap", ABS_GAP)
    log(f"  c: model built in {time.time() - t0:.1f}s ({inst.n} columns, {inst.n_rows} rows)")
    started = None
    if start is not None:
        sol = model.createSol()
        for i, v in enumerate(xs):
            model.setSolVal(sol, v, float(start[i]))
        started = bool(model.addSol(sol, free=True))
        log(f"  c: start solution {'accepted' if started else 'rejected'}")
    if not heuristics:
        model.setHeuristics(SCIP_PARAMSETTING.OFF)
        log("  c: SCIP primal heuristics off")
    model.setRealParam("limits/time", float(max(1.0, time_limit - (time.time() - t0))))
    model.optimize()
    status = model.getStatus()
    out = _result("c", solver=f"pyscipopt {pyscipopt.__version__}", nodes=int(model.getNNodes()),
                  seconds=time.time() - t0, cuts=stats["cuts"], rounds=stats["calls"],
                  note=f"scip status {status}; fractional rows {stats['frac']}"
                       + ("" if started is None else f"; start {'accepted' if started else 'rejected'}"))
    full = None
    if model.getNSols() > 0:
        sol = model.getBestSol()
        full = np.array([model.getSolVal(sol, v) for v in xs])
        x = np.zeros(inst.n)
        x[xcols] = full[xcols]
        out.update(objective=float(model.getSolObjVal(sol)), owner=inst.owner_of(x))
        if G.detached(np.round(x)):
            raise RuntimeError("arm c: SCIP returned a disconnected solution")
    out["bound"] = float(model.getDualbound()) if np.isfinite(model.getDualbound()) else None
    if status == "optimal":
        out["status"] = "optimal"
        out["bound"], out["gap"] = out["objective"], 0.0
    elif status == "infeasible":
        out["status"] = "infeasible"
    elif out["owner"] is not None:
        out["status"] = "feasible"
        out["gap"] = _gap(out["objective"], out["bound"])
    return out, full


# ------------------------------------------------------------------------------ arm d
def probe_highs_lazy(log=print) -> dict:
    """A 20-node probe of highspy's `kCallbackMipDefineLazyConstraints` on a tiny connectivity
    problem: pick 4 of the 20 nodes of a path at least cost, where the two ends are cheap, so that
    the optimum without a connectivity rule is two far-apart pairs (a lazy constraint must forbid
    it).  Tried twice: through the wrapper (`cbMipDefineLazyConstraints.subscribe`) and through
    the raw `setCallback` + `startCallback`.  {"usable": bool, "attempts": [{"how", "invoked",
    "selection", "error"}], "input_fields": the attributes of `HighsCallbackInput` (what a
    callback can hand back), "observed": a sentence}.  Usable means: the callback is invoked and
    its input can define a row."""
    import highspy
    from highspy import cb
    n = 20
    out = {"usable": False, "attempts": [], "observed": "", "highspy": highspy.Highs().version(),
           "input_fields": sorted(x for x in dir(cb.HighsCallbackInput) if not x.startswith("_"))}

    def model():
        h = highspy.Highs()
        h.setOptionValue("output_flag", False)
        h.setOptionValue("mip_rel_gap", 0.0)
        for i in range(n):
            h.addVar(0.0, 1.0)
            h.changeColCost(i, 0.0 if i in (0, 1, n - 2, n - 1) else 1.0)
            h.changeColIntegrality(i, highspy.HighsVarType.kInteger)
        h.addRow(4.0, 4.0, n, np.arange(n, dtype=np.int32), np.ones(n))
        return h

    for how in ("wrapper subscribe", "raw setCallback/startCallback"):
        att = {"how": how, "invoked": 0, "selection": None, "error": ""}
        calls = []
        h = model()
        try:
            if how.startswith("wrapper"):
                h.cbMipDefineLazyConstraints.subscribe(lambda event: calls.append(event))
                h.enableCallbacks()
            else:
                h.setCallback(lambda *a: calls.append(a), None)
                h.startCallback(cb.HighsCallbackType.kCallbackMipDefineLazyConstraints)
            h.run()
            x = h.getSolution().col_value
            att["selection"] = [i for i in range(n) if x[i] > 0.5]
        except Exception as e:      # the observed error is the finding
            att["error"] = f"{type(e).__name__}: {e}"
        att["invoked"] = len(calls)
        out["attempts"].append(att)
    invoked = max(a["invoked"] for a in out["attempts"])
    out["observed"] = (f"callback invoked {invoked} times in {len(out['attempts'])} attempts; "
                       + "; ".join(f"{a['how']}: selection {a['selection']}{(' error ' + a['error']) if a['error'] else ''}"
                                   for a in out["attempts"])
                       + f"; HighsCallbackInput offers {out['input_fields']}")
    out["usable"] = invoked > 0 and any(k in f for f in out["input_fields"] for k in ("lazy", "cons", "row", "cut"))
    return out


def arm_d(inst, time_limit: float, threads: int, log=print) -> dict:
    """HiGHS with the lazy-constraint callback if it can define a constraint, else `not usable`."""
    t0 = time.time()
    probe = probe_highs_lazy(log)
    if not probe["usable"]:
        return _result("d", status="not usable", seconds=time.time() - t0, solver="highs lazy callback",
                       note=probe["observed"] or "probe: callback not invoked", probe=probe)
    raise NotImplementedError("the probe says the callback is usable; arm d's loop is not written")


SOLVERS = {"a": arm_a, "b": arm_b, "c": arm_c, "d": arm_d}


def solve(arm: str, inst, time_limit: float, threads: int = 1, log=print, **kw) -> dict:
    if arm not in SOLVERS:
        raise ValueError(f"arm {arm!r} not in {ARMS}")
    return SOLVERS[arm](inst, time_limit, threads, log, **kw)
