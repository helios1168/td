"""
bounds.py -- valid upper bounds on the CONTIGUOUS Nash optimum that do not solve
contiguity at all (PLAN.md C.1).  Not a contig_methods *method*: no NAME/solve, so
`contig_methods.discover()` skips this file.  Both bounds obj(S) for every contiguous
S because they drop the contiguity constraint and rho*perimeter >= 0 only makes the
true optimum smaller still:

    obj(S) = log g_a(S) + log g_b(S) - rho*perimeter(S)  <=  log g_a(S) + log g_b(S)
           <=  UB_free_nash  <=  UB_free_frac                       (this module)

`ub_free_frac` -- the LP/fractional relaxation of the free (no-contiguity) Nash
problem: sort zips by utility ratio (`base.ratio`), and for every prefix k allow the
next zip in the order to be split fractionally between the two sides.  Because
(ga + t*ua_z)(gb - t*ub_z) is concave (in fact quadratic, coefficient -ua_z*ub_z <= 0)
in t on [0, 1], the closed-form vertex clipped to [0, 1] is the exact maximum over t
for that k; the loop over k = 0..n-1 sweeps every "prefix + fractional next zip"
position and so covers the whole relaxation, including the pure-integer prefixes at
its t in {0, 1} boundaries.  When ua_z*ub_z == 0 the quadratic degenerates to linear
in t -- maximise over the two endpoints directly instead of dividing by zero.

`ub_free_nash` -- the actual free (no-contiguity) Nash optimum via
`territory.nash_exact`'s outer approximation, offset by its own reported bound gap
(`max(0, gap)`) so the number returned is provably >= the true free optimum even
though `nash_exact` only certifies to `tol` (default 1e-9), not machine precision.
"""
from __future__ import annotations

import math

import numpy as np

import territory as T
from . import base


def ub_free_frac(ua, ub) -> float:
    """Fractional relaxation bound on the free Nash log-product, in nats.

    Exact if some prefix (integer k) is optimal; otherwise a genuine relaxation, so it
    can exceed the true free optimum (module docstring).  Returns -inf if no prefix or
    fractional split gives two positive gains (cannot happen once M_z > 0 somewhere on
    both ratio ends, but the guard costs nothing).
    """
    ua = np.asarray(ua, float)
    ub = np.asarray(ub, float)
    n = len(ua)
    order = np.argsort(-base.ratio(ua, ub), kind="stable")
    ga = np.concatenate([[0.0], np.cumsum(ua[order])])
    gb = np.concatenate([[ub.sum()], ub.sum() - np.cumsum(ub[order])])

    best = -math.inf
    for k in range(n):
        z = order[k]
        ua_z, ub_z = float(ua[z]), float(ub[z])
        ga_k, gb_k = float(ga[k]), float(gb[k])
        denom = 2.0 * ua_z * ub_z
        if denom > 0:
            t = (ua_z * gb_k - ub_z * ga_k) / denom
            t = min(1.0, max(0.0, t))
        else:
            # linear in t (one or both of ua_z, ub_z is 0): compare the two endpoints
            f0 = ga_k * gb_k
            f1 = (ga_k + ua_z) * (gb_k - ub_z)
            t = 0.0 if f0 >= f1 else 1.0
        gA = ga_k + t * ua_z
        gB = gb_k - t * ub_z
        if gA > 0 and gB > 0:
            val = math.log(gA) + math.log(gB)
            if val > best:
                best = val
    return best


def ub_free_nash(G, nodes, theta: float = 0.40, lam: float = 0.30, kappa: float = 0.0) -> dict:
    """Free (no-contiguity) Nash optimum, offset by its own certified gap.

    Returns dict(UB, to_a, product, gap).  `UB = log(product) + max(0, gap)` where
    `product = g_a * g_b` at the reported (near-)optimal free allocation; `gap` is
    `territory.nash_exact`'s own `dual - primal` in nats.  Raises NotImplementedError
    at kappa > 0: there is no free-Nash shortcut once utilities carry a travel-cost
    term (W11) -- the ratio-threshold / outer-approximation structure this leans on is
    unaffected algebraically, but no test here has exercised it, so it is refused
    rather than silently assumed correct.
    """
    if kappa:
        raise NotImplementedError(
            "ub_free_nash: no free-Nash shortcut is validated at kappa > 0 (W11 travel cost)")
    nodes = list(nodes)
    n = len(nodes)
    A = np.array([G.nodes[z]["A"] for z in nodes], float)
    B = np.array([G.nodes[z]["B"] for z in nodes], float)
    M = np.array([G.nodes[z]["M"] for z in nodes], float)
    res = T.nash_exact(A, B, M, theta, lam)
    if res.get("status") != "optimal":
        raise RuntimeError(
            f"ub_free_nash: territory.nash_exact did not report optimal "
            f"(status={res.get('status')!r})")
    x = res["x"]
    to_a = {nodes[i] for i in range(n) if x[i]}
    ga, gb = float(res["g_a"]), float(res["g_b"])
    product = ga * gb
    gap = float(res.get("gap", 0.0))
    UB = math.log(ga) + math.log(gb) + max(0.0, gap)
    return dict(UB=UB, to_a=to_a, product=product, gap=gap)
