"""VERIFY_U9-bandthm -- the INDEPENDENT oracle.

Nothing here imports or reuses `docs/artifacts/U9-bandthm/bandthm.py`.  The modeller
solved `EG^bal_S(delta)` with a scipy/HiGHS outer-approximation loop and read its duals
from a KKT LP built on the same primal.  This module:

  * solves the PRIMAL with SCIP's native `log` (pyscipopt, expression graph)   -> X, g
  * solves the LAGRANGIAN DUAL as a separate convex program, also in SCIP      -> p, mu+-
  * turns each of the two into an EXACT rational feasible point and evaluates the
    objective / dual objective in 60-digit mpmath with directed rounding, giving a
    RIGOROUS bracket   L <= EG^bal_S(delta) <= U.

The dual, derived from scratch (rho = 0):

    L(x; p, mu) = sum_i log g_i - sum_z p_z (sum_i x_zi - 1)
                  - sum_i mu+_i (m_i - (1+d)T/k) - sum_i mu-_i ((1-d)T/k - m_i)

    sup_{x >= 0} L  =  sum_i [ log( max_z u_iz / q_zi ) - 1 ] + sum_z p_z
                       + (T/k)[ (1+d) sum_i mu+_i - (1-d) sum_i mu-_i ]      (q > 0)

  with q_zi = p_z + nu_i M_z, nu = mu+ - mu-.  Writing s_i = 1 / max_z(u_iz/q_zi), the
  constraint "s_i u_iz <= q_zi for all z" is LINEAR, so the dual is the concave program

    max  sum_i log s_i + k - sum_z p_z - (T/k)[(1+d) sum mu+ - (1-d) sum mu-]
    s.t. s_i u_iz <= p_z + (mu+_i - mu-_i) M_z   for all (i,z);   mu+ , mu- >= 0

  and D := -(that objective) is an upper bound on EG^bal for EVERY feasible point.
"""
from __future__ import annotations

from fractions import Fraction as F

import numpy as np
from mpmath import mp, mpf

mp.dps = 60

try:
    from pyscipopt import Model, quicksum
    from pyscipopt import log as scip_log
    HAVE_SCIP = True
except Exception:                                                    # pragma: no cover
    HAVE_SCIP = False


# --------------------------------------------------------------------------- model
def utilities(M, books, free=None, theta=0.40, lam=0.30):
    """Unmasked u[i,z] -- td/channel.py::gain_matrix convention, re-derived from
    docs/MODEL.md's formula (NOT copied from bandthm.py)."""
    M = np.asarray(M, float)
    books = np.asarray(books, float)
    c1, c2, c_free = 1.0 - lam, theta * (1.0 - lam), theta * (1.0 - lam)
    if free is None:
        free = np.zeros_like(M)
    Tz = books.sum(axis=0)
    return (c2 * Tz + c_free * free + lam * M)[None, :] + (c1 - c2) * books


# ------------------------------------------------------------------- SCIP primal
def scip_primal(u, M, delta, gap=0.0, tl=120):
    """max sum_i log g_i over F(delta), by SCIP with a native log constraint."""
    if not HAVE_SCIP:
        raise RuntimeError("pyscipopt unavailable")
    k, n = u.shape
    T = float(M.sum())
    m = Model("egbal")
    m.hideOutput()
    m.setParam("limits/gap", gap)
    m.setParam("limits/time", tl)
    m.setParam("numerics/feastol", 1e-9)
    x = [[m.addVar(lb=0.0, ub=1.0, vtype="C") for _ in range(n)] for _ in range(k)]
    glb = 0.30 * (1 - delta) * T / k * 0.5
    g = [m.addVar(lb=max(glb, 1e-6), ub=float(u[i].sum()) + 1.0) for i in range(k)]
    t = [m.addVar(lb=-1e6, ub=1e6) for _ in range(k)]
    for z in range(n):
        m.addCons(quicksum(x[i][z] for i in range(k)) == 1.0)
    for i in range(k):
        m.addCons(g[i] <= quicksum(float(u[i, z]) * x[i][z] for z in range(n)))
        m.addCons(quicksum(float(M[z]) * x[i][z] for z in range(n)) <= (1 + delta) * T / k)
        m.addCons(quicksum(float(M[z]) * x[i][z] for z in range(n)) >= (1 - delta) * T / k)
        m.addCons(t[i] <= scip_log(g[i]))
    m.setObjective(quicksum(t), "maximize")
    m.optimize()
    st = m.getStatus()
    X = np.array([[m.getVal(x[i][z]) for z in range(n)] for i in range(k)])
    return {"X": X, "obj": m.getObjVal(), "dualbound": m.getDualbound(), "status": st}


# ---------------------------------------------------------------------- SCIP dual
def scip_dual(u, M, delta, gap=0.0, tl=120):
    """The Lagrangian dual, solved as its own concave program in SCIP."""
    if not HAVE_SCIP:
        raise RuntimeError("pyscipopt unavailable")
    k, n = u.shape
    T = float(M.sum())
    m = Model("egbal_dual")
    m.hideOutput()
    m.setParam("limits/gap", gap)
    m.setParam("limits/time", tl)
    m.setParam("numerics/feastol", 1e-9)
    p = [m.addVar(lb=-1e4, ub=1e4) for _ in range(n)]
    mup = [m.addVar(lb=0.0, ub=1e4) for _ in range(k)]
    mum = [m.addVar(lb=0.0, ub=1e4) for _ in range(k)]
    s = [m.addVar(lb=1e-9, ub=1e6) for _ in range(k)]
    ls = [m.addVar(lb=-1e6, ub=1e6) for _ in range(k)]
    for i in range(k):
        m.addCons(ls[i] <= scip_log(s[i]))
        for z in range(n):
            m.addCons(float(u[i, z]) * s[i]
                      <= p[z] + (mup[i] - mum[i]) * float(M[z]))
    m.setObjective(quicksum(ls) + k - quicksum(p)
                   - (T / k) * ((1 + delta) * quicksum(mup)
                                - (1 - delta) * quicksum(mum)), "maximize")
    m.optimize()
    return {"p": np.array([m.getVal(v) for v in p]),
            "mup": np.array([m.getVal(v) for v in mup]),
            "mum": np.array([m.getVal(v) for v in mum]),
            "obj": m.getObjVal(), "status": m.getStatus()}


# ------------------------------------------------- rigorous certified bracket
def _frac(v, den=10 ** 12):
    return F(v).limit_denominator(den)


def rigorous_lower(u, M, delta, X, den=10 ** 10):
    """Repair X to an EXACTLY feasible rational point of F(delta) and return a rigorous
    lower bound on EG^bal(delta).

    Supply rows are made exact by absorbing the residual in the largest entry of each
    column.  The band is then made exact WITHOUT losing tightness:
      * delta > 0: mix with the uniform point U == 1/k, Y_l = (1-l)Y + l U.  Because
        m_i(Y_l) is affine in l and m_i(U) = T/k is strictly inside the band, a rational
        l slightly above the smallest admissible value gives exact feasibility, and the
        objective moves by O(l) = O(1e-6).
      * delta = 0: mix cannot help (the band is an equality), so mass is repaired by
        exact single-zip transfers, which preserve the supply rows and the box.
    """
    k, n = u.shape
    uF = [[_frac(float(u[i, z]), den) for z in range(n)] for i in range(k)]
    MF = [_frac(float(M[z]), den) for z in range(n)]
    TF = sum(MF)
    tgt = TF / k
    dF = _frac(delta, den)
    lo, hi = (1 - dF) * tgt, (1 + dF) * tgt
    Y = [[_frac(min(1.0, max(0.0, float(X[i, z]))), den) for z in range(n)]
         for i in range(k)]
    for z in range(n):
        col = [Y[i][z] for i in range(k)]
        j = max(range(k), key=lambda i: col[i])
        Y[j][z] = 1 - sum(col[i] for i in range(k) if i != j)
        if Y[j][z] < 0 or Y[j][z] > 1:
            return None

    def masses(W):
        return [sum(MF[z] * W[i][z] for z in range(n)) for i in range(k)]

    if dF > 0:
        need = F(0)
        for i, mi in enumerate(masses(Y)):
            if mi > hi:
                need = max(need, (mi - hi) / (mi - tgt))
            if mi < lo:
                need = max(need, (lo - mi) / (tgt - mi))
        lam = min(F(1), need + F(1, 10 ** 6)) if need > 0 else F(0)
        U = F(1, k)
        Y = [[(1 - lam) * Y[i][z] + lam * U for z in range(n)] for i in range(k)]
    else:
        for _ in range(50000):
            e = [v - tgt for v in masses(Y)]
            if all(v == 0 for v in e):
                break
            i = max(range(k), key=lambda a_: e[a_])
            j = min(range(k), key=lambda a_: e[a_])
            if e[i] <= 0 or e[j] >= 0:
                return None
            moved = False
            for z in range(n):
                room = min(Y[i][z], 1 - Y[j][z])
                if room <= 0:
                    continue
                t = min(room, e[i] / MF[z], (-e[j]) / MF[z])
                if t <= 0:
                    continue
                Y[i][z] -= t
                Y[j][z] += t
                moved = True
                break
            if not moved:
                return None
        else:
            return None

    if not all(sum(Y[i][z] for i in range(k)) == 1 for z in range(n)):
        return None
    if not all(0 <= Y[i][z] <= 1 for i in range(k) for z in range(n)):
        return None
    if not all(lo <= v <= hi for v in masses(Y)):
        return None
    g = [sum(uF[i][z] * Y[i][z] for z in range(n)) for i in range(k)]
    if any(v <= 0 for v in g):
        return None
    val = sum(mp.log(mpf(v.numerator) / mpf(v.denominator)) for v in g)
    return float(val) - 1e-25, [[float(v) for v in row] for row in Y]


def rigorous_upper(u, M, delta, p, mup, mum, den=10 ** 10):
    """Repair (p, mu+, mu-) to an EXACTLY dual-feasible point; return a rigorous UPPER
    bound on EG^bal(delta) (weak duality), or None."""
    k, n = u.shape
    uF = [[_frac(float(u[i, z]), den) for z in range(n)] for i in range(k)]
    MF = [_frac(float(M[z]), den) for z in range(n)]
    TF = sum(MF)
    dF = _frac(delta, den)
    pF = [_frac(float(v), den) for v in p]
    # canonical decomposition: it MINIMISES the band term for delta > 0 (P4.4)
    nuF = [_frac(float(mup[i] - mum[i]), den) for i in range(k)]
    upF = [max(F(0), v) for v in nuF]
    umF = [max(F(0), -v) for v in nuF]
    qF = [[pF[z] + nuF[i] * MF[z] for z in range(n)] for i in range(k)]
    if any(qF[i][z] <= 0 for i in range(k) for z in range(n)):
        return None
    # s_i := min_z q_zi / u_iz  -- feasible by construction, and optimal given (p, nu)
    sF = [min(qF[i][z] / uF[i][z] for z in range(n)) for i in range(k)]
    assert all(sF[i] * uF[i][z] <= qF[i][z] for i in range(k) for z in range(n))
    psi = (sum(mp.log(mpf(v.numerator) / mpf(v.denominator)) for v in sF)
           + k - sum(mpf(v.numerator) / mpf(v.denominator) for v in pF)
           - (mpf(TF.numerator) / mpf(TF.denominator) / k)
           * ((1 + mpf(dF.numerator) / mpf(dF.denominator))
              * sum(mpf(v.numerator) / mpf(v.denominator) for v in upF)
              - (1 - mpf(dF.numerator) / mpf(dF.denominator))
              * sum(mpf(v.numerator) / mpf(v.denominator) for v in umF)))
    return float(-psi) + 1e-25, ([float(v) for v in pF], [float(v) for v in nuF])


def bracket(u, M, delta):
    """Rigorous [L, U] for EG^bal_S(delta) from two INDEPENDENT SCIP solves."""
    pr = scip_primal(u, M, delta)
    du = scip_dual(u, M, delta)
    lo = rigorous_lower(u, M, delta, pr["X"])
    up = rigorous_upper(u, M, delta, du["p"], du["mup"], du["mum"])
    return {"L": None if lo is None else lo[0], "U": None if up is None else up[0],
            "X": pr["X"], "p": du["p"], "nu": du["mup"] - du["mum"],
            "scip_primal": pr["obj"], "scip_dual": du["obj"],
            "status": (pr["status"], du["status"])}
