"""milp_engines.py -- alternative solvers for the state-level minimum-splits MILP
(`td.solvers.state_splits.SplitProblem`), behind one seam: `solve_problem`.

`state_splits.solve` is one engine (`scipy`, `scipy.optimize.milp`'s HiGHS, no callbacks, no
threads).  This module adds three more against the same `SplitProblem`, so the bench
(`tools/bench/milp_bench.py`) can compare them on identical data:

    scipy   `state_splits.solve` itself, the baseline.
    highs   `highspy.Highs` direct: threads, `mip_rel_gap=0`, callbacks for the trajectory.
    scip    `pyscipopt.Model` built from the same rows; an event handler for the trajectory.
    cpsat   OR-Tools CP-SAT, out of process in `.venv-opt` (`milp_worker.py`): `y` and the
            flow are discretised, so its optimum is an upper bound, never a certificate.

Every engine returns the same shape `state_splits.solve` does (`z`, `y`, `masses`, `splits`,
`split_states`, `spread_rel`, `max_dev_rel`, `objective`, `status`, `mip_gap`) plus `nodes`,
`dual_bound`, `trajectory` (`[[t, primal, dual], ...]`) and `engine`.  `status` is `0` at proven
optimality, `"time_limit"` for a time-limited incumbent, and anything else is a `SolveFailure`
(`state_splits.SolveFailure`) with `reason` `"infeasible"` or `"no_incumbent"` -- the same two
outcomes `state_splits.failure_reason` names, so a caller that already handles one engine's
failures handles every engine's.

Three pure functions build variant problems rather than solving anything themselves, so the
bench can compose them freely:

    fix_roots(problem, anchors)    roots an anchored district at its home state (a connected
                                    set can be rooted anywhere, so no optimum is lost).
    with_cutoff(problem, s_star)   asks "does an (s*-1)-split map exist?" -- infeasible on the
                                    true optimum is a certificate, not just a better bound.
    lp_heuristic(problem)          a reweighted-L1 relaxation, milliseconds, no certificate.
"""
from __future__ import annotations

import dataclasses
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Callable

import numpy as np
from scipy import sparse
from scipy.optimize import linprog

from td.solvers import state_splits as ss
from td.solvers.state_splits import SolveFailure, SplitProblem

HERE = Path(__file__).resolve().parent
# Hardcoded, not derived from __file__: a worktree checkout has no `.venv-opt` of its own
# (CLAUDE.md "Environment"), so this must resolve to the hub regardless of which checkout this
# module was imported from (app/config.py's REPO is the same pattern for the same reason).
REPO = Path(os.environ.get("TD_REPO", "/Users/ntlee/projects/td"))
OPT_PYTHON = Path(os.environ.get("TD_OPT_PYTHON", str(REPO / ".venv-opt" / "bin" / "python3")))
WORKER = HERE / "milp_worker.py"           # the worker beside *this* checkout of the module

ENGINES = ("scipy", "highs", "scip", "cpsat")


# --------------------------------------------------------------------------------- the seam
def solve_problem(problem: SplitProblem, engine: str, *, time_limit: float | None,
                  cutoff: float | None = None, warm: dict | None = None,
                  threads: int | None = None, heuristic_effort: float | None = None,
                  on_incumbent: Callable[[dict], None] | None = None,
                  stop: object | None = None) -> dict:
    """Solve `problem` with `engine`, returning `state_splits.solve`'s shape plus `nodes`,
    `dual_bound`, `trajectory` and `engine`.

    `cutoff` is an objective upper bound passed to the solver (HiGHS `objective_bound`, SCIP
    `setObjlimit`): only a solution strictly better is accepted, which turns "prove no (s*-1)
    map exists" into a plain solve of `with_cutoff(problem, s_star - 1)` with `cutoff=s_star`
    rather than a fresh search.  `warm` is `{"z": (S, k) bool, "y": (S, k) float}` (what
    `lp_heuristic` and the `cpsat` worker return), given to the solver as a partial MIP start;
    the `r` and flow blocks are left for the solver's own repair heuristic to complete.

    `heuristic_effort` is HiGHS's `mip_heuristic_effort` (0..1, more primal search for less
    proof); `scip`, `scipy` and `cpsat` ignore it.  `on_incumbent`, when given, is called from
    inside `highs`'s and `scip`'s own improving-solution hook with `{"splits", "z", "y",
    "objective", "seconds"}` for every incumbent the solver finds; `scipy` and `cpsat` ignore it
    too (`scipy.optimize.milp` has no such hook, and the `cpsat` worker runs out of process).
    `stop` is a `multiprocessing.Event` (or anything with `.is_set()`, or a plain callable
    returning bool), polled from the same hook so a caller in another process can interrupt a
    running `highs`/`scip` solve; ignored by `scipy` and `cpsat` for the same reason as
    `on_incumbent`.

    `scipy` and `cpsat` accept neither `cutoff` nor `warm` (scipy has no such hooks through
    `scipy.optimize.milp`; the bench's variant table never asks CP-SAT for either).
    """
    if engine == "scipy":
        if cutoff is not None or warm is not None:
            raise NotImplementedError("the scipy engine takes neither cutoff nor warm")
        res = dict(ss.solve(problem, time_limit=time_limit, strict=False))
        res.setdefault("nodes", 0)
        res.setdefault("dual_bound",
                       res["objective"] if res["mip_gap"] <= 1e-9 else float("nan"))
        res["trajectory"] = []
        res["engine"] = "scipy"
        return res
    if engine == "highs":
        return _highs_solve(problem, time_limit=time_limit, cutoff=cutoff, warm=warm,
                            threads=threads, heuristic_effort=heuristic_effort,
                            on_incumbent=on_incumbent, stop=stop)
    if engine == "scip":
        return _scip_solve(problem, time_limit=time_limit, cutoff=cutoff, warm=warm,
                           threads=threads, on_incumbent=on_incumbent, stop=stop)
    if engine == "cpsat":
        if cutoff is not None or warm is not None:
            raise NotImplementedError("the cpsat engine takes neither cutoff nor warm")
        return _cpsat_solve(problem, time_limit=time_limit, threads=threads)
    raise ValueError(f"unknown engine {engine!r}; expected one of {ENGINES}")


def _stopped(stop: object) -> bool:
    """True if `stop` says the parent wants this solve interrupted: a `multiprocessing.Event`
    (or anything else with `.is_set()`), or a plain callable returning bool."""
    return stop.is_set() if hasattr(stop, "is_set") else bool(stop())


def _decode_zy(problem: SplitProblem, z: np.ndarray, y: np.ndarray) -> dict:
    """`z`, `y` -> the reporting fields `state_splits.solve` computes, shared by every engine
    so `scipy`, `highs`, `scip` and `cpsat` read back identically regardless of how each one
    represents its own variables."""
    S, k = problem.n_state, problem.k
    z = np.asarray(z, bool).reshape(S, k)
    y = np.clip(np.asarray(y, float).reshape(S, k), 0.0, 1.0)
    y = np.where(z, y, 0.0)
    row = y.sum(axis=1, keepdims=True)
    y = y / np.where(row > 0, row, 1.0)
    masses = problem.M_s @ y
    return dict(
        z=z, y=y, masses=masses,
        splits=int(z.sum() - S),
        split_states=[s for s in range(S) if int(z[s].sum()) >= 2],
        spread_rel=float((masses.max() - masses.min()) / masses.mean()),
        max_dev_rel=float(np.abs(masses - problem.tau).max() / problem.tau),
    )


def _decode_x(problem: SplitProblem, x: np.ndarray) -> dict:
    """Slice `z`, `y` out of a full solution vector in `problem`'s own variable layout.

    `z` is thresholded at 0.5 before `_decode_zy`'s `bool()` cast: a solver's own binary
    variable can come back as `-2e-16` rather than an exact `0.0` (SCIP does, HiGHS mostly
    doesn't), and `bool(-2e-16)` is `True` -- silently manufacturing an extra split."""
    S, k = problem.n_state, problem.k
    z = x[problem.off_z:problem.off_z + S * k].reshape(S, k) > 0.5
    y = x[problem.off_y:problem.off_y + S * k].reshape(S, k)
    return _decode_zy(problem, z, y)


# --------------------------------------------------------------------------------- pure functions
def fix_roots(problem: SplitProblem, anchors: list[tuple[int, int]]) -> SplitProblem:
    """A copy of `problem` with district `j`'s flow root fixed at its home state, for every
    `(home, j)` in `anchors`: `r[home, j] = 1` and `r[s, j] = 0` for every other state `s`.

    A connected set can be rooted at any of its members, so this loses no optimum; naming the
    root removes a source of symmetry the solver would otherwise search over for nothing
    (math-verify confirms before this is adopted for `build_milp(fix_roots=True)`)."""
    new = _clone(problem)
    for s, j in anchors:
        if not (0 <= s < new.n_state and 0 <= j < new.k):
            raise ValueError(f"anchor ({s}, {j}) out of range")
        for s2 in range(new.n_state):
            at = new.off_r + s2 * new.k + j
            if s2 == s:
                new.var_lb[at] = 1.0
                new.var_ub[at] = 1.0
            else:
                new.var_ub[at] = 0.0
    return new


def with_cutoff(problem: SplitProblem, s_star: int) -> SplitProblem:
    """A copy of `problem` with one row appended, `sum_sj z_sj <= n_state + s_star - 1`: an
    `(s_star - 1)`-split map is one more binding row away from the plain MILP, so asking this
    variant for feasibility (any objective) is the "does a smaller map exist" question, and an
    `infeasible` answer certifies `s_star` splits is optimal without closing a gap."""
    S, k = problem.n_state, problem.k
    sk = np.arange(S * k)
    row = sparse.coo_matrix((np.ones(S * k), (np.zeros(S * k, int), problem.off_z + sk)),
                            shape=(1, problem.n_var)).tocsc()
    A = sparse.vstack([problem.A, row]).tocsc()
    lb = np.concatenate([problem.lb, [-np.inf]])
    ub = np.concatenate([problem.ub, [float(problem.n_state + s_star - 1)]])
    rows = dict(problem.rows)
    start = problem.A.shape[0]
    rows["cutoff"] = (start, start + 1)
    new = _clone(problem)
    new.A, new.lb, new.ub, new.rows = A, lb, ub, rows
    return new


def _clone(problem: SplitProblem) -> SplitProblem:
    """A shallow copy of `problem` with `var_lb`/`var_ub` (and nothing else) deep-copied, since
    `fix_roots` and the bound-setting callers mutate those two arrays in place."""
    return dataclasses.replace(problem, var_lb=problem.var_lb.copy(), var_ub=problem.var_ub.copy())


def _to_ineq(problem: SplitProblem) -> tuple[sparse.csc_matrix, np.ndarray]:
    """`lb <= A x <= ub` -> one-sided `A_ub x <= b_ub`, splitting each finite side out (the same
    trick `state_splits.balance_pass` uses for `scipy.optimize.linprog`, which takes no ranged
    row directly)."""
    lo, hi = problem.lb, problem.ub
    parts_A, parts_b = [], []
    up = np.isfinite(hi)
    if up.any():
        parts_A.append(problem.A[up])
        parts_b.append(hi[up])
    down = np.isfinite(lo)
    if down.any():
        parts_A.append(-problem.A[down])
        parts_b.append(-lo[down])
    return sparse.vstack(parts_A).tocsc(), np.concatenate(parts_b)


def lp_heuristic(problem: SplitProblem) -> dict:
    """A reweighted-L1 relaxation: minimise `sum w_sj z_sj` over the LP relaxation (every
    integrality dropped) for up to 10 rounds, `w = 1 / (z_prev + eps)` so mass concentrates onto
    fewer `(s, j)` pairs each round (docs/VERIFY -- the standard sparsity surrogate for
    cardinality).  The relaxed `z` is then rounded at 0.5, repaired into a connected, fully
    covering pattern (every state needs at least one district; a disconnected district is
    reconnected by the shortest rook-graph path to its largest piece -- the full graph is
    connected, so this always terminates), then repaired again if the rounded pattern cannot
    meet the band (`state_splits.balance_pass` optimises `y` for a fixed `z` but never proves
    the band unreachable, so this is checked and fixed explicitly, not assumed).

    Milliseconds, no certificate: the repair can open more contacts than the true optimum needs,
    so `splits` here is an upper bound only, never reported as proven (trap 12 is about proofs,
    and this makes none)."""
    t0 = time.time()
    S, k = problem.n_state, problem.k
    A_ub, b_ub = _to_ineq(problem)
    bounds = list(zip(problem.var_lb.tolist(), problem.var_ub.tolist()))

    w = np.ones(S * k)
    z_relaxed = None
    for _ in range(10):
        c = np.zeros(problem.n_var)
        c[problem.off_z:problem.off_z + S * k] = w
        c[problem.off_y:problem.off_y + S * k] = problem.c[problem.off_y:problem.off_y + S * k]
        res = linprog(c, A_ub=A_ub, b_ub=b_ub, bounds=bounds, method="highs-ds",
                      options={"time_limit": 30.0, "presolve": True})
        if not res.success:
            break
        z_new = res.x[problem.off_z:problem.off_z + S * k]
        if z_relaxed is not None and np.abs(z_new - z_relaxed).max() < 1e-6:
            z_relaxed = z_new
            break
        z_relaxed = z_new
        w = 1.0 / (z_relaxed + 1e-3)
    if z_relaxed is None:
        raise SolveFailure(1, "lp_heuristic: the relaxed LP never solved")

    z_relaxed = z_relaxed.reshape(S, k)
    z_bin = z_relaxed > 0.5
    for s in range(S):
        if not z_bin[s].any():
            z_bin[s, int(np.argmax(z_relaxed[s]))] = True
    z_bin = _repair_connectivity(z_bin, z_relaxed, problem.edges)

    # `balance_pass` only optimises the deviation for a fixed z -- it never raises when the
    # band cannot be met, so a rounded z that looks fine can still be band-infeasible even
    # though the fractional z_relaxed it came from was not.  Repair by opening, one at a time,
    # the most-relaxed contact for whichever district is furthest out of band; bounded by S*k
    # so this always terminates (worst case: every state touches every district, which gives
    # `balance_pass` enough freedom that the band is met).
    pas = ss.balance_pass(problem, z_bin)
    for _ in range(S * k):
        if pas["max_dev_rel"] <= problem.delta + 1e-9:
            break
        j = int(np.argmax(np.abs(pas["masses"] / problem.tau - 1.0)))
        candidates = [s for s in range(S) if not z_bin[s, j]]
        if not candidates:
            break
        s = max(candidates, key=lambda s: z_relaxed[s, j])
        z_bin[s, j] = True
        z_bin = _repair_connectivity(z_bin, z_relaxed, problem.edges)
        pas = ss.balance_pass(problem, z_bin)

    return dict(z=z_bin, y=pas["y"], splits=int(z_bin.sum() - S), seconds=time.time() - t0)


def _components(col: np.ndarray, edges: list[tuple[int, int]]) -> list[list[int]]:
    """Connected components of `{s : col[s]}` in the rook graph, as a list of node lists."""
    nodes = set(int(s) for s in np.flatnonzero(col))
    adj: dict[int, list[int]] = {s: [] for s in nodes}
    for u, v in edges:
        if u in nodes and v in nodes:
            adj[u].append(v)
            adj[v].append(u)
    seen, comps = set(), []
    for start in nodes:
        if start in seen:
            continue
        comp, stack = [start], [start]
        seen.add(start)
        while stack:
            s = stack.pop()
            for t in adj[s]:
                if t not in seen:
                    seen.add(t)
                    comp.append(t)
                    stack.append(t)
        comps.append(comp)
    return comps


def _shortest_path(edges: list[tuple[int, int]], sources: set[int], targets: set[int]) -> list[int]:
    """BFS over the whole rook graph from any node in `sources` to the nearest node in
    `targets`; returns the path's interior (neither endpoint), the states to add to reconnect
    them.  The rook graph over the 49 states plus DC is connected, so this never fails to find
    one."""
    adj: dict[int, list[int]] = {}
    for u, v in edges:
        adj.setdefault(u, []).append(v)
        adj.setdefault(v, []).append(u)
    parent: dict[int, int | None] = {s: None for s in sources}
    frontier = list(sources)
    while frontier:
        nxt = []
        for s in frontier:
            if s in targets and s not in sources:
                path = [s]
                while parent[path[-1]] is not None:
                    path.append(parent[path[-1]])
                path.reverse()
                return path[1:-1]
            for t in adj.get(s, []):
                if t not in parent:
                    parent[t] = s
                    nxt.append(t)
        frontier = nxt
    raise RuntimeError("the rook graph is disconnected -- state_splits assumes it never is")


def _repair_connectivity(z_bin: np.ndarray, z_relaxed: np.ndarray,
                         edges: list[tuple[int, int]]) -> np.ndarray:
    """Add the fewest extra `(s, j)` contacts that make every district's column connected,
    bridging each smaller component to the largest one along a shortest rook-graph path."""
    S, k = z_bin.shape
    z_bin = z_bin.copy()
    for j in range(k):
        for _ in range(S + 1):
            comps = _components(z_bin[:, j], edges)
            if len(comps) <= 1:
                break
            comps.sort(key=len, reverse=True)
            main = set(comps[0])
            for comp in comps[1:]:
                path = _shortest_path(edges, main, set(comp))
                for s in path:
                    z_bin[s, j] = True
                main |= set(path) | set(comp)
    return z_bin


# --------------------------------------------------------------------------------- HiGHS direct
def _highs_lp(problem: SplitProblem):
    import highspy
    lp = highspy.HighsLp()
    lp.num_col_ = problem.n_var
    lp.num_row_ = problem.A.shape[0]
    lp.col_cost_ = problem.c
    lp.col_lower_ = problem.var_lb
    lp.col_upper_ = problem.var_ub
    lp.row_lower_ = problem.lb
    lp.row_upper_ = problem.ub
    lp.integrality_ = [highspy.HighsVarType.kInteger if v else highspy.HighsVarType.kContinuous
                       for v in problem.integrality]
    Acsc = problem.A.tocsc()
    mat = highspy.HighsSparseMatrix()
    mat.format_ = highspy.MatrixFormat.kColwise
    mat.start_ = Acsc.indptr.tolist()
    mat.index_ = Acsc.indices.tolist()
    mat.value_ = Acsc.data.tolist()
    lp.a_matrix_ = mat
    lp.sense_ = highspy.ObjSense.kMinimize
    return lp


def _highs_solve(problem: SplitProblem, *, time_limit, cutoff=None, warm=None,
                 threads=None, heuristic_effort=None, on_incumbent=None, stop=None) -> dict:
    import highspy

    h = highspy.Highs()
    status = h.passModel(_highs_lp(problem))
    if status == highspy.HighsStatus.kError:
        raise RuntimeError("HiGHS rejected the model")
    h.setOptionValue("output_flag", False)
    h.setOptionValue("mip_rel_gap", 0.0)
    if time_limit is not None:
        h.setOptionValue("time_limit", float(time_limit))
    if threads is not None:
        h.setOptionValue("threads", int(threads))
    if heuristic_effort is not None:
        h.setOptionValue("mip_heuristic_effort", float(heuristic_effort))
    if cutoff is not None:
        h.setOptionValue("objective_bound", float(cutoff))
    if warm is not None:
        _highs_warm_start(h, problem, warm)

    trajectory: list[list[float]] = []
    t0 = time.time()

    def _record(event) -> None:
        d = event.data_out
        trajectory.append([d.running_time, d.objective_function_value, d.mip_dual_bound])

    def _on_improving(event) -> None:
        _record(event)
        if on_incumbent is None:
            return
        # `mip_solution` is populated on kCallbackMipImprovingSolution (checked against
        # highspy 1.15); fall back to getSolution() for a build where it comes back empty.
        x = np.asarray(event.data_out.mip_solution, float)
        if x.size == 0:
            x = np.asarray(h.getSolution().col_value, float)
        if x.size == 0:
            return
        info = _decode_x(problem, x)
        on_incumbent(dict(splits=info["splits"], z=info["z"], y=info["y"],
                          objective=float(event.data_out.objective_function_value),
                          seconds=time.time() - t0))

    def _on_logging(event) -> None:
        _record(event)
        if stop is not None and _stopped(stop) and event.data_in is not None:
            event.data_in.user_interrupt = True

    h.cbMipImprovingSolution.subscribe(_on_improving)
    h.cbMipLogging.subscribe(_on_logging)
    h.startCallback(highspy.cb.HighsCallbackType.kCallbackMipImprovingSolution)
    h.startCallback(highspy.cb.HighsCallbackType.kCallbackMipLogging)
    h.run()

    info = h.getInfo()
    model_status = h.getModelStatus()
    has_incumbent = info.primal_solution_status == highspy.kSolutionStatusFeasible
    if model_status == highspy.HighsModelStatus.kInfeasible:
        raise SolveFailure(2, "HiGHS proved infeasibility")
    if not has_incumbent:
        raise SolveFailure(1, f"HiGHS stopped ({h.modelStatusToString(model_status)}) "
                             "with no incumbent")

    x = np.asarray(h.getSolution().col_value, float)
    result = _decode_x(problem, x)
    optimal = model_status == highspy.HighsModelStatus.kOptimal
    result.update(status=(0 if optimal else "time_limit"),
                 mip_gap=float(info.mip_gap), objective=float(info.objective_function_value),
                 nodes=int(info.mip_node_count), dual_bound=float(info.mip_dual_bound),
                 trajectory=trajectory, engine="highs")
    return result


def _highs_warm_start(h, problem: SplitProblem, warm: dict) -> None:
    """A sparse partial MIP start on the `z` and `y` blocks only; HiGHS's own repair heuristic
    fills in `r` and the flow (`highspy.Highs.setSolution`, the sparse-index overload)."""
    S, k = problem.n_state, problem.k
    z0 = np.asarray(warm["z"], bool).ravel().astype(float)
    y0 = np.asarray(warm["y"], float).ravel()
    idx = np.concatenate([np.arange(problem.off_z, problem.off_z + S * k),
                          np.arange(problem.off_y, problem.off_y + S * k)]).astype(np.int32)
    val = np.concatenate([z0, y0]).astype(np.float64)
    h.setSolution(len(idx), idx, val)


# --------------------------------------------------------------------------------- SCIP direct
def _scip_solve(problem: SplitProblem, *, time_limit, cutoff=None, warm=None,
               threads=None, on_incumbent=None, stop=None) -> dict:
    import pyscipopt

    S, k = problem.n_state, problem.k
    m = pyscipopt.Model()
    m.hideOutput()
    m.setMinimize()
    xs = [m.addVar(vtype=("B" if problem.integrality[i] else "C"),
                   lb=float(problem.var_lb[i]), ub=float(problem.var_ub[i]),
                   obj=float(problem.c[i]), name=f"v{i}")
         for i in range(problem.n_var)]

    Acsr = problem.A.tocsr()
    for r in range(Acsr.shape[0]):
        start, end = Acsr.indptr[r], Acsr.indptr[r + 1]
        idx, val = Acsr.indices[start:end], Acsr.data[start:end]
        if len(idx) == 0:
            continue
        expr = pyscipopt.quicksum(float(v) * xs[int(i)] for i, v in zip(idx, val))
        lo, hi = float(problem.lb[r]), float(problem.ub[r])
        if lo == hi:
            m.addCons(expr == lo)
        elif not np.isfinite(lo):
            m.addCons(expr <= hi)
        elif not np.isfinite(hi):
            m.addCons(expr >= lo)
        else:
            m.addCons(lo <= (expr <= hi))

    m.setParam("limits/gap", 0.0)
    if time_limit is not None:
        m.setParam("limits/time", float(time_limit))
    if threads is not None:
        m.setParam("lp/threads", int(threads))
    if cutoff is not None:
        m.setObjlimit(float(cutoff))
    if warm is not None:
        _scip_warm_start(m, xs, problem, warm)

    trajectory: list[list[float]] = []
    t0 = time.time()
    last = [0.0]

    def _on_event(model, event) -> None:
        now = time.time() - t0
        etype = event.getType()
        if etype == pyscipopt.SCIP_EVENTTYPE.BESTSOLFOUND:
            sol = model.getBestSol()
            obj = model.getSolObjVal(sol)
            trajectory.append([now, obj, model.getDualbound()])
            last[0] = now
            if on_incumbent is not None:
                z = np.array([model.getSolVal(sol, xs[problem.off_z + i])
                             for i in range(S * k)])
                y = np.array([model.getSolVal(sol, xs[problem.off_y + i])
                             for i in range(S * k)])
                info = _decode_zy(problem, z > 0.5, y)
                on_incumbent(dict(splits=info["splits"], z=info["z"], y=info["y"],
                                  objective=float(obj), seconds=now))
        elif now - last[0] >= 1.0:
            trajectory.append([now, model.getPrimalbound(), model.getDualbound()])
            last[0] = now
        if etype == pyscipopt.SCIP_EVENTTYPE.NODESOLVED and stop is not None and _stopped(stop):
            model.interruptSolve()

    m.attachEventHandlerCallback(_on_event, [pyscipopt.SCIP_EVENTTYPE.BESTSOLFOUND,
                                             pyscipopt.SCIP_EVENTTYPE.NODESOLVED])
    m.optimize()

    status = m.getStatus()
    if status == "infeasible":
        raise SolveFailure(2, "SCIP proved infeasibility")
    if m.getNSols() == 0:
        raise SolveFailure(1, f"SCIP stopped ({status}) with no incumbent")

    x = np.array([m.getVal(v) for v in xs])
    result = _decode_x(problem, x)
    result.update(status=(0 if status == "optimal" else "time_limit"),
                 mip_gap=float(m.getGap()), objective=float(m.getObjVal()),
                 nodes=int(m.getNNodes()), dual_bound=float(m.getDualbound()),
                 trajectory=trajectory, engine="scip")
    return result


def _scip_warm_start(m, xs, problem: SplitProblem, warm: dict) -> None:
    """A partial solution on `z` and `y`, the same split `lp_heuristic`/`cpsat` return; SCIP's
    own heuristics complete `r` and the flow before accepting or discarding it."""
    S, k = problem.n_state, problem.k
    z0 = np.asarray(warm["z"], bool).ravel()
    y0 = np.asarray(warm["y"], float).ravel()
    sol = m.createPartialSol()
    for i, v in enumerate(z0):
        m.setSolVal(sol, xs[problem.off_z + i], 1.0 if v else 0.0)
    for i, v in enumerate(y0):
        m.setSolVal(sol, xs[problem.off_y + i], float(v))
    m.addSol(sol)


# --------------------------------------------------------------------------------- CP-SAT, out of process
def _cpsat_solve(problem: SplitProblem, *, time_limit, threads=None) -> dict:
    """Write `problem`'s semantic inputs to a `.npz`, run `milp_worker.py` under `.venv-opt`,
    read its result JSON back.

    Run by file path, not `-m td.solvers.milp_worker`: that form imports `td.solvers`, whose
    `__init__.py` imports `base`, which imports `networkx` -- absent from `.venv-opt` by design
    (this venv exists so `ortools` never touches the frozen `.venv` pins).  `milp_worker.py`
    itself imports nothing from `td`, so running it as a plain script is exactly the "never
    imports `td`" contract, just invoked a different way than first drafted."""
    if not OPT_PYTHON.exists():
        raise RuntimeError(f"the cpsat engine needs .venv-opt (not found at {OPT_PYTHON}); "
                          "see tools/bench/README.md")
    S, k = problem.n_state, problem.k
    z_lb = problem.var_lb[problem.off_z:problem.off_z + S * k].reshape(S, k)
    z_ub = problem.var_ub[problem.off_z:problem.off_z + S * k].reshape(S, k)
    edges = (np.array(problem.edges, dtype=np.int64).reshape(-1, 2) if problem.edges
            else np.zeros((0, 2), np.int64))

    with tempfile.TemporaryDirectory() as tmp:
        npz_path = os.path.join(tmp, "problem.npz")
        json_path = os.path.join(tmp, "result.json")
        np.savez(npz_path, M_s=problem.M_s, D=problem.D, edges=edges,
                tau=np.array(problem.tau), delta=np.array(problem.delta),
                eta=np.array(problem.eta), z_lb=z_lb, z_ub=z_ub)
        with open(json_path, "w", encoding="utf-8") as fh:
            json.dump(dict(time_limit=float(time_limit) if time_limit is not None else 60.0,
                          num_workers=int(threads) if threads else 1), fh)
        proc = subprocess.run([str(OPT_PYTHON), str(WORKER), npz_path, json_path],
                             cwd=str(REPO), capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"the cpsat worker failed: {proc.stderr[-2000:]}")
        with open(json_path, encoding="utf-8") as fh:
            out = json.load(fh)

    status = out["status"]
    if status in ("OPTIMAL", "FEASIBLE"):
        result = _decode_zy(problem, np.array(out["z"]), np.array(out["y"]))
        dual_bound = float(out["dual_bound"])
        objective = float(out["objective"])
        gap = 0.0 if status == "OPTIMAL" else abs(objective - dual_bound) / max(abs(objective), 1e-9)
        result.update(status=(0 if status == "OPTIMAL" else "time_limit"), mip_gap=gap,
                     objective=objective, nodes=int(out["nodes"]), dual_bound=dual_bound,
                     trajectory=out["trajectory"], engine="cpsat")
        return result
    if status == "INFEASIBLE":
        raise SolveFailure(2, "CP-SAT proved the discretised problem infeasible")
    raise SolveFailure(1, f"CP-SAT stopped ({status}) with no incumbent")
