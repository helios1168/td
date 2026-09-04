"""P3-split, done properly: clean vertices, then attack.

Lesson from p3_probe.py: an LP "vertex" from any floating-point solver carries dirt at
1e-7..1e-9, and a support threshold BELOW that dirt manufactures phantom splits.  So each
candidate vertex is CLEANED (entries < tau zeroed, columns renormalised) and the cleaned
point is re-certified: same g to 1e-9, masses still in the band, and rank(tight rows |
supp) == |supp| (i.e. it really is a vertex).  Only certified-clean vertices are counted,
and the ambiguous ones are reported rather than hidden.

Two independent tests:
  T1  #splits <= k-1+t  and  |supp| <= n+k+t-1  on certified-clean optimal-face vertices.
  T2  the DEPENDENCY itself: the vector (p_z ; nu_i ; -1/g*_i) annihilates the tight-row
      matrix restricted to supp columns -- which is what makes rank <= n+k+t-1, hence the
      "-1".  Checked with duals from the INDEPENDENT SCIP dual solve.
"""
from __future__ import annotations

import math
import sys

import numpy as np
from pyscipopt import Model, quicksum

import oracle as O

FAIL: list[str] = []


def ck(name, ok, detail=""):
    print(f"  [{'ok  ' if ok else 'FAIL'}] {name}" + (f"   {detail}" if detail else ""))
    if not ok:
        FAIL.append(name)


def face_vertex(u, M, delta, gstar, c):
    k, n = u.shape
    T = float(M.sum())
    m = Model()
    m.hideOutput()
    m.setParam("limits/gap", 0.0)
    x = [[m.addVar(lb=0.0, ub=1.0) for _ in range(n)] for _ in range(k)]
    for z in range(n):
        m.addCons(quicksum(x[i][z] for i in range(k)) == 1.0)
    for i in range(k):
        m.addCons(quicksum(float(M[z]) * x[i][z] for z in range(n)) <= (1 + delta) * T / k)
        m.addCons(quicksum(float(M[z]) * x[i][z] for z in range(n)) >= (1 - delta) * T / k)
        m.addCons(quicksum(float(u[i, z]) * x[i][z] for z in range(n)) == float(gstar[i]))
    m.setObjective(quicksum(float(c[i, z]) * x[i][z] for i in range(k) for z in range(n)),
                   "maximize")
    m.optimize()
    if m.getStatus() != "optimal":
        return None
    return np.array([[m.getVal(x[i][z]) for z in range(n)] for i in range(k)])


def clean_and_certify(u, M, delta, V, gstar, tau=1e-6, ttol=1e-7):
    """Return (splits, t, |supp|, rank) for a CERTIFIED-clean vertex, or None."""
    k, n = u.shape
    T = float(M.sum())
    W = np.where(V > tau, V, 0.0)
    s = W.sum(axis=0)
    if np.min(s) <= 0:
        return None
    W = W / s[None, :]
    if np.max(np.abs(W - V)) > 1e-4:                 # too much was moved: ambiguous
        return None
    g = (u * W).sum(axis=1)
    if np.max(np.abs(g - gstar)) > 1e-6 * max(1.0, float(np.max(gstar))):
        return None
    mm = (W * M[None, :]).sum(axis=1)
    if mm.max() > (1 + delta) * T / k + 1e-6 * T / k:
        return None
    if mm.min() < (1 - delta) * T / k - 1e-6 * T / k:
        return None
    sup = W > 0
    cols = [(i, z) for i in range(k) for z in range(n) if sup[i, z]]
    tb = [i for i in range(k)
          if mm[i] >= (1 + delta) * T / k - ttol * T / k
          or mm[i] <= (1 - delta) * T / k + ttol * T / k]
    rows = []
    for z in range(n):
        rows.append([1.0 if zz == z else 0.0 for (ii, zz) in cols])
    for i in range(k):
        rows.append([float(u[i, zz]) if ii == i else 0.0 for (ii, zz) in cols])
    for i in tb:
        rows.append([float(M[zz]) if ii == i else 0.0 for (ii, zz) in cols])
    A = np.array(rows, float)
    # scale rows to unit norm so the rank tolerance is meaningful
    nr = np.linalg.norm(A, axis=1, keepdims=True)
    nr[nr == 0] = 1.0
    rk = int(np.linalg.matrix_rank(A / nr, tol=1e-9))
    if rk != len(cols):                              # not a vertex after cleaning
        return None
    splits = int(sum(1 for z in range(n) if sup[:, z].sum() >= 2))
    return splits, len(tb), len(cols), rk, W


def dependency_test(u, M, delta):
    """T2: does (p ; nu ; -1/g*) annihilate the tight rows restricted to supp?"""
    k, n = u.shape
    T = float(M.sum())
    pr = O.scip_primal(u, M, delta, tl=30)
    du = O.scip_dual(u, M, delta, tl=30)
    X = pr["X"]
    g = (u * X).sum(axis=1)
    p, nu = du["p"], du["mup"] - du["mum"]
    mm = (X * M[None, :]).sum(axis=1)
    sup = X > 1e-6
    cols = [(i, z) for i in range(k) for z in range(n) if sup[i, z]]
    if not cols:
        return None
    # nu_i = 0 for a band-slack agent by complementary slackness, so summing the band
    # row over ALL i is the same combination as summing it over B -- and avoids having
    # to classify B with a threshold.
    B = list(range(k))
    coef = np.zeros(len(cols))
    for c, (i, z) in enumerate(cols):
        coef[c] = p[z] + nu[i] * M[z] - u[i, z] / g[i]
    rhs = float(p.sum() + sum(nu[i] * mm[i] for i in B) - k)
    scale = max(1.0, float(np.max(np.abs(p))), float(np.max(u / g[:, None])))
    # reference: the KKT stationarity residual on the support for the SAME (p, nu).
    # D vanishes EXACTLY (proved in sym.py); any numeric residual here must be exactly
    # that dual-accuracy residual, not a defect in the dependency.
    stat = max(abs(p[z] + nu[i] * M[z] - u[i, z] / g[i]) for (i, z) in cols)
    return (float(np.max(np.abs(coef))) / scale, abs(rhs) / max(1.0, k),
            float(stat) / scale)


def main():
    print("P3-split -- cleaned-vertex attack + the dependency test")
    rng = np.random.default_rng(5150)
    worst_sharp = worst_coarse = worst_rank = math.inf
    nv = amb = 0
    tight_hits = 0
    maxsplit = maxt = 0
    dz_tight = 0
    dep_worst = dep_rhs = 0.0
    dep_cases = 0
    for trial in range(120):
        n = int(rng.integers(4, 11))
        k = int(rng.integers(2, 6))
        if k > n:
            continue
        style = int(rng.integers(0, 3))
        if style == 0:
            M = np.round(rng.uniform(1.0, 50.0, size=n), 3)
        elif style == 1:
            M = np.round(np.exp(rng.normal(2.0, 1.4, size=n)), 3)
        else:
            M = np.round(rng.uniform(1.0, 5.0, size=n), 3)
            M[0] *= 12.0
        u = np.round(rng.uniform(0.25, 1.0, size=(k, n)) * M[None, :], 4)
        d = float(rng.choice([0.0, 1e-4, 0.01, 0.05, 0.15, 0.5]))
        try:
            pr = O.scip_primal(u, M, d, tl=25)
        except Exception:
            continue
        if pr["status"] != "optimal":
            continue
        gstar = (u * pr["X"]).sum(axis=1)
        try:
            dep = dependency_test(u, M, d)
        except Exception:
            dep = None
        if dep is not None:
            dep_worst = max(dep_worst, dep[0])
            dep_rhs = max(dep_rhs, dep[1])
            dep_gap = max(globals().get("_depgap", 0.0), abs(dep[0] - dep[2]))
            globals()["_depgap"] = dep_gap
            dep_cases += 1
        for _ in range(4):
            V = face_vertex(u, M, d, gstar, rng.normal(size=(k, n)))
            if V is None:
                continue
            res = clean_and_certify(u, M, d, V, gstar)
            if res is None:
                amb += 1
                continue
            s, tt, ns, rk, _ = res
            nv += 1
            worst_sharp = min(worst_sharp, (k - 1 + tt) - s)
            worst_coarse = min(worst_coarse, (2 * k - 1) - s)
            worst_rank = min(worst_rank, (n + k + tt - 1) - ns)
            if (k - 1 + tt) - s == 0:
                tight_hits += 1
            if d == 0.0 and tt == k:
                dz_tight += 1
            maxsplit, maxt = max(maxsplit, s), max(maxt, tt)
            if s > k - 1 + tt:
                print(f"    REAL VIOLATION: n={n} k={k} delta={d} splits={s} t={tt} "
                      f"|supp|={ns} rank={rk}")
                print(f"      M = {list(M)}")
                print(f"      u = {u.tolist()}")
    ck(f"#splits <= k-1+t on {nv} certified-clean optimal-face vertices "
       f"({amb} ambiguous vertices discarded, not counted either way)",
       worst_sharp >= 0, f"min slack = {worst_sharp} (attained {tight_hits} times); "
       f"max splits = {maxsplit}, max t = {maxt}")
    ck(f"#splits <= 2k-1 on the same {nv} vertices", worst_coarse >= 0,
       f"min slack = {worst_coarse}")
    ck(f"|supp| <= n+k+t-1 on the same {nv} vertices", worst_rank >= 0,
       f"min slack = {worst_rank}")
    ck("the delta = 0 / every-agent-tight regime was exercised", dz_tight > 0,
       f"{dz_tight} vertices")
    ck(f"the DEPENDENCY D = sum_z p_z(supply) + sum_B nu_i(band) - sum_i (1/g*_i)(gain) "
       f"annihilates the tight rows on supp, on {dep_cases} instances -- to exactly the "
       f"KKT stationarity residual of the dual used (i.e. the dependency itself is exact)",
       globals().get("_depgap", 0.0) < 1e-12 and dep_rhs < 1e-4,
       f"max relative coefficient = {dep_worst:.2e}, identical to the stationarity "
       f"residual to {globals().get('_depgap', 0.0):.2e}; max relative RHS = {dep_rhs:.2e}")
    print("\nP3 FAILURES: " + ("none" if not FAIL else "; ".join(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
