"""
flow_pwl.py -- Option D + Option C: the Shirabe flow contiguity of `flow.py` with the outer
approximation replaced by an *a-priori* chord under-estimator of `log` (PLAN.md W4 D2/D3,
OPTIONS.md §5).  One MILP.  No loop at all.

The idea
--------
`flow.py` still iterates, because the tangent cuts have to be discovered.  Here the log is
under-estimated up front by a piecewise-linear function whose error is bounded in closed
form, so the whole problem is a single MILP whose value is within a known `eps` of the
true optimum.  That trades an unbounded number of master solves for a fixed number of
extra rows, and turns the OA convergence question (CLAUDE.md trap 11: the two cut families'
iteration bounds multiply) into an arithmetic one.

D2 -- no SOS2, no lambdas, no binaries
--------------------------------------
`log` is concave, so on a grid `p_0 < p_1 < ... < p_k` the chord through
`(p_{i-1}, log p_{i-1})` and `(p_i, log p_i)` lies *below* log inside `[p_{i-1}, p_i]` and
*above* it outside.  The piecewise-linear interpolant of a concave function is concave, so
for `g` in segment j and any other chord i, concavity gives `PWL(g) <= L_i(g)`; therefore

        PWL(g)  =  min_i L_i(g)          for every g in [p_0, p_k].

A maximisation of `z <= PWL(g)` is then just `k` plain inequality rows `z <= L_i(g)` -- the
textbook SOS2 / convex-combination machinery is unnecessary for a *concave* function being
maximised.  The one thing it needs is the hard domain bound `g >= p_0`: below `p_0` the
first chord runs above `log` and the "under-estimator" claim fails.  D4's `g_lo`
(`flow.gain_bounds`) supplies exactly that bound, and `build_core` puts it on the column.

D3 -- how many segments, in closed form
---------------------------------------
On a log-spaced grid every segment has the same ratio `t = (g_hi/g_lo)^(1/k)`, so every
segment has the same worst-case chord error.  Maximising `log g - L(g)` over `[p, tp]` gives
`g* = p(t-1)/log t`, and the error is *scale free*:

        E(t) = sigma - 1 - log sigma,        sigma = log t / (t - 1)        (~ (log t)^2 / 8)

`segments_for` bisects for the smallest `k` with `E <= eps_target/2` per side, capped at
`k_max`.  The **achieved** total `eps = E_a + E_b` is reported in `Result.eps`, whether or
not the target was met: an `eps` bigger than asked for still yields an honest certificate,
because the harness validator allows `UB - LB <= CERT_TOL + eps`.

The bound chain (why `optimal` is claimable at all)
---------------------------------------------------
Let `V` be the MILP's optimal value in the surrogate objective and `D >= V` its dual bound.

  * `PWL <= log` pointwise, so for the *true* optimiser `S*`,
    `obj(S*) <= PWL_a(g_a*) + PWL_b(g_b*) - rho*per* + eps <= V + eps <= D + eps`.
    Hence `UB := D + eps` is a valid global upper bound.  (`ub_scope="global"`: the flow
    formulation fixes no roots.)
  * At the MILP's own `x`, the *true* objective is at least the surrogate value, so
    `LB >= V`.  `LB` is recomputed here from `base.objective` on the rounded allocation, and
    the spanning-tree incumbent is taken too if it happens to be better -- both are genuine
    feasible points, so both are valid lower bounds.

`optimal` is claimed only when `D - LB <= base.CERT_TOL`, which is exactly the condition
under which `UB - LB = D + eps - LB <= CERT_TOL + eps` -- the validator's own test.  This is
why `mip_rel_gap` and `mip_abs_gap` are pinned to 0 in `flow.run_milp` (CLAUDE.md trap 12).

Variants: `flow_pwl` (eps target 1e-6), `flow_pwl_e4` (1e-4 -- the row-count / accuracy
trade, and the fallback when `k_max` binds).
"""
from __future__ import annotations

import math
import time
from typing import Optional

import numpy as np

from . import base
from .flow import (Rows, build_core, gain_bounds, run_milp, safe_exp,
                   tree_cut_incumbent, _dual_bound, _merge_flags, _round_x)

NAME = "flow_pwl"
EXACT = True
MAX_N = None
VARIANTS = {
    "flow_pwl_e4": dict(eps_target=1e-4),
}

K_MAX = 2000


# ============================================================== D3: the segment arithmetic
def chord_error(t: float) -> float:
    """Max gap between `log` and its chord over any interval of ratio `t` (scale free).

        E(t) = sigma - 1 - log sigma,   sigma = log t / (t - 1)

    The series `E = L^2/8 - L^3/24 + ...` (`L = log t`) is used for `L < 1e-3`, where the
    closed form loses most of its significant digits to cancellation.
    """
    if not (t > 1.0):
        return 0.0
    L = math.log(t)
    if L < 1e-3:
        return L * L / 8.0 * (1.0 - L / 3.0)
    sigma = L / (t - 1.0)
    return sigma - 1.0 - math.log(sigma)


def segments_for(R: float, eps_side: float, k_max: int = K_MAX):
    """Smallest `k <= k_max` whose log-spaced grid over a range of ratio `R` has chord error
    at most `eps_side`; returns `(k, achieved_error)`."""
    if not (R > 1.0) or not np.isfinite(R):
        return 1, 0.0
    if chord_error(R) <= eps_side:
        return 1, chord_error(R)
    lo, hi = 1, 2
    while hi < k_max and chord_error(R ** (1.0 / hi)) > eps_side:
        hi = min(k_max, hi * 2)
    if chord_error(R ** (1.0 / hi)) > eps_side:
        return int(hi), chord_error(R ** (1.0 / hi))
    while lo < hi:
        mid = (lo + hi) // 2
        if chord_error(R ** (1.0 / mid)) <= eps_side:
            hi = mid
        else:
            lo = mid + 1
    return int(lo), chord_error(R ** (1.0 / lo))


def add_chords(core, side: str, g_lo: float, g_hi: float, k: int, ext: Rows) -> int:
    """`k` chord rows over the log-spaced grid `g_lo * t^i`, i = 0..k."""
    if k < 1 or not (g_hi > g_lo > 0):
        return 0
    grid = np.geomspace(g_lo, g_hi, k + 1)
    for i in range(1, len(grid)):
        p0, p1 = float(grid[i - 1]), float(grid[i])
        if p1 <= p0:
            continue
        core.chord(side, p0, p1, ext)
    return len(grid) - 1


# ================================================================================== solve
def solve(G, nodes, *, theta, lam, rho, respect_state, time_limit, seed,
          warm_start=None, reductions=None, trace=None, kappa=0.0,
          eps_target=1e-6, k_max=K_MAX, root_mode="chain", caps="tight", bound_g=True,
          n_trees=8, reserve=0.05, **opts) -> base.Result:
    t0 = time.perf_counter()
    nodes = list(nodes)
    n = len(nodes)
    ua, ub = base.utilities(G, nodes, theta, lam, kappa)
    H = G.subgraph(nodes)
    extra = dict(eps_target=float(eps_target), root_mode=root_mode, caps=caps,
                 bound_g=bool(bound_g), retried_without_tol=False,
                 retried_random_seed=False, k_max_binding=False)

    if n == 0:
        return base.Result(status="infeasible", extra=extra, message="flow_pwl: empty pair")
    if float(np.maximum(ua, 0).sum()) <= 0 or float(np.maximum(ub, 0).sum()) <= 0:
        return base.Result(status="infeasible", extra=extra,
                           message="flow_pwl: one side has no positive utility anywhere "
                                   "-- no allocation gives both gains > 0")

    # ---- incumbent: D4's product floor, the LB floor, and t_first_feasible ----------
    inc_to_a, inc_obj = tree_cut_incumbent(H, nodes, ua, ub, rho, seed=seed,
                                           n_trees=n_trees, warm_start=warm_start)
    best_lb, best_to_a = -math.inf, None
    if inc_to_a is not None and math.isfinite(inc_obj):
        best_lb, best_to_a = inc_obj, set(inc_to_a)
        if trace is not None:
            trace.incumbent(best_to_a, best_lb)

    product_floor = safe_exp(inc_obj) if best_to_a is not None else None
    g_lo_a, g_hi_a, g_lo_b, g_hi_b = gain_bounds(ua, ub, product_floor=product_floor,
                                                 bound_g=bound_g)
    # the grid needs a strictly positive left end; at kappa > 0 with negative utilities the
    # min-positive-u floor is unavailable, so fall back to a numerical domain guard (which
    # only widens the range, hence only widens eps -- it never invalidates the bound chain
    # unless the optimum itself has a gain below it, which g_hi*1e-12 makes fanciful).
    guarded = False
    if not (g_lo_a > 0):
        g_lo_a, guarded = g_hi_a * 1e-12, True
    if not (g_lo_b > 0):
        g_lo_b, guarded = g_hi_b * 1e-12, True
    extra["g_lo_guarded"] = guarded

    R_a = g_hi_a / g_lo_a if g_lo_a > 0 else 1.0
    R_b = g_hi_b / g_lo_b if g_lo_b > 0 else 1.0
    k_a, eps_a = segments_for(R_a, eps_target / 2.0, k_max)
    k_b, eps_b = segments_for(R_b, eps_target / 2.0, k_max)
    eps = float(eps_a + eps_b)
    extra.update(k_a=int(k_a), k_b=int(k_b), eps_a=float(eps_a), eps_b=float(eps_b),
                 g_lo_a=float(g_lo_a), g_hi_a=float(g_hi_a), g_lo_b=float(g_lo_b),
                 g_hi_b=float(g_hi_b), L_a=float(math.log(R_a)), L_b=float(math.log(R_b)),
                 warm_product=product_floor,
                 k_max_binding=bool(k_a >= k_max or k_b >= k_max))

    core = build_core(H, nodes, ua, ub, rho, root_mode=root_mode, caps=caps,
                      g_lo_a=g_lo_a, g_hi_a=g_hi_a, g_lo_b=g_lo_b, g_hi_b=g_hi_b)
    ext = Rows()
    add_chords(core, "a", g_lo_a, g_hi_a, k_a, ext)
    add_chords(core, "b", g_lo_b, g_hi_b, k_b, ext)
    extra.update(n_cols=core.n_col, n_rows=core.n_static_rows + ext.n, n_chords=ext.n,
                 n_arcs=core.n_arcs, n_components=len(core.comps))

    rem = time_limit - (time.perf_counter() - t0) - reserve
    if rem <= 0:
        return base.Result(status="time_limit", to_a=best_to_a,
                           LB=(best_lb if best_to_a is not None else None), eps=eps,
                           extra=extra, iters=0,
                           message="flow_pwl: wall clock exhausted before the MILP")

    res, flags = run_milp(core, ext, rem, deadline=t0 + time_limit - reserve)
    _merge_flags(extra, flags)
    nodes_bb = int(getattr(res, "mip_node_count", 0) or 0)
    st = getattr(res, "status", 4)
    D = _dual_bound(res)

    if st == 2:
        return base.Result(status="infeasible", eps=eps, iters=1, nodes=nodes_bb,
                           extra=extra, message="flow_pwl: MILP infeasible")
    if st not in (0, 1) or getattr(res, "x", None) is None:
        return base.Result(status=("time_limit" if st == 1 else "error"), to_a=best_to_a,
                           LB=(best_lb if best_to_a is not None else None),
                           UB=(None if D is None else D + eps), eps=eps, iters=1,
                           nodes=nodes_bb, extra=extra,
                           message=f"flow_pwl: milp status {st} -- {getattr(res, 'message', '')}")

    x = _round_x(res, n)
    to_a = {nodes[i] for i in range(n) if x[i]}
    if base.is_feasible(G, nodes, to_a):
        per = base.perimeter(G, nodes, to_a)
        obj = base.objective(ua, ub, base.mask(nodes, to_a), rho, per)
        if math.isfinite(obj) and obj > best_lb:
            best_lb, best_to_a = obj, to_a
            if trace is not None:
                trace.incumbent(to_a, obj)

    UB = None if D is None else D + eps
    if UB is not None and trace is not None:
        trace.bound(UB)
    LB = best_lb if best_to_a is not None else None

    if D is None or LB is None:
        status = "heuristic" if best_to_a is not None else "error"
        UB = None if status == "heuristic" else UB
        message = ("flow_pwl: no usable dual bound" if D is None
                   else "flow_pwl: no feasible iterate")
    elif D - LB <= base.CERT_TOL:
        # the certificate is checked *before* the time limit: the bound chain is valid
        # whatever made HiGHS stop, so a run that hit the cap having already closed the gap
        # is still an eps-certified optimum, not a time_limit
        status = "optimal"
        message = "" if st == 0 else "flow_pwl: certified at the time limit"
    elif st == 1:
        status = "time_limit"
        message = "flow_pwl: MILP hit the time limit"
    else:
        status = "gap_limit"
        message = (f"flow_pwl: MILP dual bound {D:.12g} exceeds the best true objective "
                   f"{LB:.12g} by more than CERT_TOL")
    return base.Result(status=status, to_a=best_to_a, LB=LB, UB=UB, ub_scope="global",
                       eps=eps, iters=1, n_cuts=0, n_tangents=0, nodes=nodes_bb,
                       extra=extra, message=message)
