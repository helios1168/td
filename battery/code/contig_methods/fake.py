"""
fake.py -- a test double that exercises every branch of the contract (PLAN.md U1a).

Not a solver.  `behaviour` (a variant option) selects what it returns:

    optimal          best *feasible* prefix of the ratio order, LB == UB (claims a certificate)
    optimal_rooted   same, but ub_scope="rooted"  -> harness downgrades to optimal_rooted
    time_limit       an infeasible iterate (all zips to a except the ratio-min one, then the
                     ratio-max zip flipped) with LB=None and a loose UB
    iteration_limit  best feasible prefix, UB loose (gap > tolerance)
    gap_limit        best feasible prefix, UB = LB + 5e-4 (engine rel-gap stop)
    heuristic        best feasible prefix, UB=None
    infeasible       no allocation
    error            raises RuntimeError                     -> run_method maps to "error"
    hang             logs one incumbent then sleeps past the cap -> backstop -> "time_limit"
    lie_lb           optimal but LB off by 1e-3               -> validator violation
    lie_pieces       "optimal" on a disconnected allocation    -> validator violation
    lie_gap          "optimal" with UB = LB + 1e-3             -> validator violation
    lie_outside      to_a contains a zip not in the pair       -> validator violation
    lie_heuristic_ub heuristic that reports a UB               -> validator violation

The "best feasible prefix" is exact only on instances where a prefix of the ratio order is
optimal (e.g. paths with monotone ratios); tests use such instances.
"""
from __future__ import annotations

import time

import numpy as np

from . import base

NAME = "fake"
EXACT = True
MAX_N = None
VARIANTS = {f"fake_{b}": dict(behaviour=b) for b in (
    "optimal", "optimal_rooted", "gap_limit", "time_limit", "iteration_limit", "heuristic", "infeasible",
    "error", "hang", "lie_lb", "lie_pieces", "lie_gap", "lie_outside", "lie_heuristic_ub")}


def _best_feasible_prefix(G, nodes, ua, ub, rho):
    order = np.argsort(-base.ratio(ua, ub), kind="stable")
    best = (-np.inf, set(), 0)
    for k in range(len(nodes) + 1):
        to_a = {nodes[i] for i in order[:k]}
        if not base.is_feasible(G, nodes, to_a):
            continue
        per = base.perimeter(G, nodes, to_a)
        obj = base.objective(ua, ub, base.mask(nodes, to_a), rho, per)
        if obj > best[0]:
            best = (obj, to_a, per)
    return best


def solve(G, nodes, *, theta, lam, rho, respect_state, time_limit, seed,
          warm_start=None, reductions=None, trace=None, kappa=0.0, behaviour="optimal", **opts):
    ua, ub = base.utilities(G, nodes, theta, lam, kappa)
    n = len(nodes)
    if behaviour == "error":
        raise RuntimeError("fake method asked to fail")
    if behaviour == "infeasible":
        return base.Result("infeasible", message="fake: no allocation")
    if behaviour == "hang":
        if trace is not None:
            trace.incumbent(set(), base.objective(ua, ub, base.mask(nodes, set()), rho, 0))
            k = n // 2
            to_a = set(nodes[:k])
            if base.is_feasible(G, nodes, to_a):
                trace.incumbent(to_a, base.objective(ua, ub, base.mask(nodes, to_a), rho,
                                                     base.perimeter(G, nodes, to_a)))
        time.sleep(time_limit * 10 + 5)
        return base.Result("optimal", to_a=set(), LB=0.0, UB=0.0)  # never reached
    obj, to_a, per = _best_feasible_prefix(G, nodes, ua, ub, rho)
    if trace is not None:
        trace.incumbent(to_a, obj)
    loose = obj + 0.5
    if behaviour == "optimal":
        if trace is not None: trace.bound(obj)
        return base.Result("optimal", to_a=to_a, LB=obj, UB=obj, iters=1, message="fake prefix")
    if behaviour == "optimal_rooted":
        return base.Result("optimal", to_a=to_a, LB=obj, UB=obj, ub_scope="rooted", iters=1)
    if behaviour == "time_limit":
        r = base.ratio(ua, ub)
        bad = set(nodes) - {nodes[int(np.argmin(r))]}
        bad.discard(nodes[int(np.argmax(r))])
        return base.Result("time_limit", to_a=bad, LB=None, UB=loose, iters=3,
                           message="fake: infeasible last iterate")
    if behaviour == "iteration_limit":
        if trace is not None: trace.bound(loose)
        return base.Result("iteration_limit", to_a=to_a, LB=obj, UB=loose, iters=30)
    if behaviour == "gap_limit":
        if trace is not None: trace.bound(obj + 5e-4)
        return base.Result("gap_limit", to_a=to_a, LB=obj, UB=obj + 5e-4, iters=4,
                           message="fake: engine rel-gap stop")
    if behaviour == "heuristic":
        return base.Result("heuristic", to_a=to_a, LB=obj, UB=None)
    if behaviour == "lie_lb":
        return base.Result("optimal", to_a=to_a, LB=obj + 1e-3, UB=obj + 1e-3)
    if behaviour == "lie_pieces":
        # alternate zips along the sorted order: disconnected on any graph with >= 3 zips
        # on a path; fall back to the prefix if that happens to be feasible
        alt = set(nodes[::2])
        return base.Result("optimal", to_a=alt, LB=None, UB=obj)
    if behaviour == "lie_gap":
        return base.Result("optimal", to_a=to_a, LB=obj, UB=obj + 1e-3)
    if behaviour == "lie_outside":
        return base.Result("optimal", to_a=to_a | {"__not_a_zip__"}, LB=obj, UB=obj)
    if behaviour == "lie_heuristic_ub":
        return base.Result("heuristic", to_a=to_a, LB=obj, UB=obj)
    raise ValueError(f"unknown fake behaviour {behaviour!r}")
