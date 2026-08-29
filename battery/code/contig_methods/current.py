"""
current.py -- wraps the legacy `districting.solve_contiguous_nash` as a
contig_methods plug-in (PLAN.md C.1, U2).

`ub_scope = "rooted"`: the legacy loop fixes a root zip on each side (roots =
argmax / argmin utility ratio, `base.ratio`'s zero-value guard), so its dual bound
certifies a *restriction* of the contiguous problem (one side must contain a
specific zip), not the true global feasible set (PLAN.md C.0 #3).  The harness
downgrades a rooted "optimal" to `status_eff = "optimal_rooted"`.

Status mapping (CLAUDE.md trap 12, found 2026-08-29 through the harness validator):
the loop's own "optimal" means only "no violated separator/tangent cut was found",
which `scipy.optimize.milp` certifies to HiGHS' *default* `mip_rel_gap = 1e-4` unless
`milp_options=dict(mip_rel_gap=0.0)` is passed (see `current_tight` below) -- so it is
downgraded to "gap_limit" here unless the harness-recomputable `UB - LB <= CERT_TOL`.
"iteration limit" -> "iteration_limit".  "time limit" (the loop's own deadline
check), or a "solver failed" whose message names a time budget, -> "time_limit".
Any other "solver failed" -> "error", still carrying the last iterate if the failed
MILP returned one.

`UB` is the running min, across every `on_iter` callback, of the master's dual bound
(falling back to the master objective when HiGHS reports no dual bound, e.g. under a
per-round time-out) -- both already in the log-product maximisation units the harness
uses.  `to_a` is the best *feasible* iterate seen across the whole run (tracked from
the same callback stream, not just the returned "last" iterate, since the final
iterate can itself be infeasible on a time/iteration-limited run); if none was ever
feasible, the last iterate is carried with `LB = None`.

Soundness caveat found while validating this wrapper on disconnected pair graphs
(T0 sweep, 2026-08-29): the legacy separator cuts assume a single global root per
side; on a pair graph with more than one connected component that assumption is not
merely insufficient but WRONG -- a cut aimed at a component containing neither root
can force uniform propagation through a stray component that can never reach either
root, excluding truly-feasible (sometimes strictly better) points from the master's
own relaxation.  When that happens districting's dual-bound sequence is no longer a
valid upper bound at all: it can end up below an objective this wrapper itself proved
achievable at an earlier, since-discarded iterate.  This wrapper detects that
(`LB > UB` after harness-side recomputation) and reports `status="heuristic"`,
`UB=None` rather than a self-contradicting bound -- see test_current.py's
`test_current_disconnected_pair_regression` for a concrete instance.  Not fixed here:
districting.py is out of scope for U2.  This sharpens the already-documented
"mechanism 1" (CLAUDE.md trap 11 / PLAN.md C.0 #1), which only described the loop
*failing to converge* on disconnected pairs -- it can also *falsely converge* to a
provably suboptimal point.

Variants: `current_unbounded` (`max_iter=10**6`, so only the deadline can stop it),
`current_q` (data-scaled quantile tangent seeds instead of the legacy absolute
`{1, 3, 5, 8, 11}` -- see districting.py's `g0_seeds` docstring), `current_tight`
(`milp_options=dict(mip_rel_gap=0.0)` on every master solve -- the variant that
actually certifies to `base.CERT_TOL`; see test_current.py's C8-pair check, which is
the trap-12 numbers reproduced through this wrapper).
"""
from __future__ import annotations

import math
import time

import numpy as np

import districting as D
from . import base

NAME = "current"
EXACT = True
MAX_N = None
VARIANTS = {
    "current_unbounded": dict(max_iter=10 ** 6),
    "current_q": dict(g0_seeds="quantile"),
    "current_tight": dict(milp_options=dict(mip_rel_gap=0.0)),
    # tight + no iteration cap: the legacy loop's time-capped behaviour (S0 showed every
    # named failure stopping on max_iter=30 in 1-20 s, never reaching the 60 s cap)
    "current_tu": dict(milp_options=dict(mip_rel_gap=0.0), max_iter=10 ** 6),
}


def solve(G, nodes, *, theta, lam, rho, respect_state, time_limit, seed,
          warm_start=None, reductions=None, trace=None, kappa=0.0,
          max_iter=30, g0_seeds=None, milp_options=None, **opts) -> base.Result:
    nodes = list(nodes)
    n = len(nodes)
    ua, ub = base.utilities(G, nodes, theta, lam, kappa)
    r = base.ratio(ua, ub)
    root_a = nodes[int(np.argmax(r))]
    root_b = nodes[int(np.argmin(r))]

    own_ub = [math.inf]
    best = [None, None]  # [obj, to_a] -- best feasible incumbent seen across the run

    def _consider(to_a, obj):
        if obj is not None and math.isfinite(obj) and (best[0] is None or obj > best[0]):
            best[0], best[1] = obj, set(to_a)

    def on_iter(info):
        db = info["dual_bound"]
        val = db if math.isfinite(db) else info["master_obj"]
        if val < own_ub[0]:
            own_ub[0] = val
        if trace is not None:
            trace.bound(val)
        x = info["x"]
        to_a = {nodes[i] for i in range(n) if x[i]}
        if base.is_feasible(G, nodes, to_a):
            obj = base.objective(ua, ub, base.mask(nodes, to_a), rho, info["perimeter_true"])
            _consider(to_a, obj)
            if trace is not None and math.isfinite(obj):
                trace.incumbent(to_a, obj)

    start = time.time()
    inner_cap = min(20.0, time_limit)
    res = D.solve_contiguous_nash(
        G, nodes, theta=theta, lam=lam, rho=rho, respect_state=False,
        max_iter=max_iter, time_limit=inner_cap, verbose=False,
        deadline=start + time_limit, on_iter=on_iter, g0_seeds=g0_seeds,
        seed=seed, milp_options=milp_options)

    raw = res.get("status", "")
    message = res.get("message", "")
    iters = res.get("iters", 0)
    n_cuts = res.get("n_cuts", 0)
    n_tangents = res.get("n_tangents", 0)

    to_a_last = res.get("to_a")
    if to_a_last is not None and base.is_feasible(G, nodes, to_a_last):
        per_true = res.get("perimeter_true")
        if per_true is None:
            per_true = base.perimeter(G, nodes, to_a_last)
        obj_last = base.objective(ua, ub, base.mask(nodes, to_a_last), rho, per_true)
        _consider(to_a_last, obj_last)

    if best[1] is not None:
        to_a_out, LB_out = best[1], best[0]
    else:
        to_a_out, LB_out = to_a_last, None

    UB_out = own_ub[0] if math.isfinite(own_ub[0]) else None

    # Soundness check, found while validating this wrapper (2026-08-29, disconnected
    # T0 pairs): districting.py's separator cuts assume a single global root per
    # side, and on a pair graph with more than one connected component that
    # assumption is not just insufficient but WRONG -- a cut aimed at a component
    # containing neither root can force uniform propagation through a stray
    # component that can never reach either root, excluding truly-feasible (and
    # sometimes strictly better) points from its own master relaxation. When that
    # happens, the loop's own dual-bound sequence is no longer a valid upper bound:
    # it can dip below an objective we ourselves proved achievable at an earlier,
    # discarded iterate (own_ub tracks districting's bound faithfully; best[]
    # tracks every harness-feasible incumbent seen, which can beat it). Rather than
    # report a self-contradicting UB < LB, drop the untrustworthy bound and fall
    # back to "heuristic" (the one status the contract ties to UB=None) -- this is
    # a limitation of the wrapped legacy solver on disconnected pair graphs, not
    # fixable here (districting.py is out of scope for U2).
    unsound_bound = (UB_out is not None and LB_out is not None
                     and LB_out > UB_out + base.CERT_TOL)
    if unsound_bound:
        UB_out = None
        status = "heuristic"
        message = (message + "; " if message else "") + \
            "current: districting's own dual bound was below a harness-feasible " \
            "incumbent (disconnected pair graph, separator cuts unsound here) " \
            "-- UB dropped, reporting heuristic"
    elif raw == "optimal":
        if UB_out is not None and LB_out is not None and (UB_out - LB_out) <= base.CERT_TOL:
            status = "optimal"
        else:
            status = "gap_limit"
    elif raw == "iteration limit":
        status = "iteration_limit"
    elif raw == "time limit":
        status = "time_limit"
    elif raw == "solver failed":
        status = "time_limit" if "time" in message.lower() else "error"
    else:
        status = "error"
        message = message or f"current: unrecognised legacy status {raw!r}"

    return base.Result(status=status, to_a=to_a_out, LB=LB_out, UB=UB_out,
                       ub_scope="rooted", iters=iters, n_cuts=n_cuts,
                       n_tangents=n_tangents,
                       extra=dict(root_a=root_a, root_b=root_b), message=message)
