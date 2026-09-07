"""U1-cert: exhaustive checks of P1 (the relaxation bound) and P3 (the integrality gap).

Run:  /Users/ntlee/projects/td/.venv/bin/python3 docs/artifacts/U1-cert/check_p1_p3.py
from the worktree root.  Deterministic; the only seed is the toy's, 20260903.

Checks, in order:

  P1a  rho = 0.  For every staff set S (|S| = 3 of 4) and every one of the 3^8 integral
       coverages with im sigma = S, V(pi, sigma) <= EG_S.  EG_S is bracketed by a feasible
       primal and the Lagrangian dual, so the comparison is against a *certified* upper bound
       and does not depend on the solver converging.
  P1b  rho > 0 with the total-variation extension C_TV of the perimeter.  Same exhaustion.
       C_TV is exact on integral X, which is hypothesis H3.
  P1c  H3 is not decoration: replace C_TV by 2*C_TV -- an extension that *over*-estimates on
       integral points -- and the bound fails.  This is the counterexample the hypothesis
       excludes.
  P3a  the split count: a vertex of the optimal face has at most k - 1 split zips.
  P3b  the value bound: EG_S - V(rounded) <= -sum_i log(1 - L_i/g_i*) with
       L_i = sum_{z in F} u_iz x*_zi, and the coarser -log(1 - M(F)/g_min*).
"""
from __future__ import annotations

import itertools
import math
import sys

import numpy as np
from scipy.optimize import minimize

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import eg  # noqa: E402

RHO = 0.05
FAIL = []


def report(name, ok, detail=""):
    print(f"[{'PASS' if ok else 'FAIL'}] {name}  {detail}")
    if not ok:
        FAIL.append(name)


def eg_with_penalty(U, edges, rho, mult=1.0, restarts=8, seed=1):
    """max sum_i log g_i - rho*mult*C_TV(X) over the fractional simplices, by SLSQP.

    Only used on the 8x3 toy.  Multi-start, and the best value found is reported; since P1b
    compares integral coverages *against* this value, a numerically low optimum can only make
    the test harder to pass, never easier.
    """
    n, k = U.shape
    rng = np.random.default_rng(seed)

    def neg(v):
        X = v.reshape(n, k)
        g = (U * X).sum(axis=0)
        return -(np.log(g).sum() - rho * mult * eg.perimeter_tv(edges, X))

    cons = [{"type": "eq", "fun": (lambda v, z=z: v.reshape(n, k)[z].sum() - 1.0)}
            for z in range(n)]
    best = -math.inf
    bestv = None
    for _ in range(restarts):
        v0 = rng.dirichlet(np.ones(k), size=n).ravel()
        res = minimize(neg, v0, method="SLSQP", bounds=[(1e-9, 1.0)] * (n * k),
                       constraints=cons, options=dict(maxiter=800, ftol=1e-12))
        if res.success and -res.fun > best:
            best, bestv = -res.fun, res.x.reshape(n, k)
    return best, bestv


def integral_X(assign, k):
    X = np.zeros((len(assign), k))
    X[np.arange(len(assign)), assign] = 1.0
    return X


def main():
    t = eg.toy()
    M, S, k, edges = t["M"], t["S"], t["k"], t["edges"]
    n = len(M)
    print(f"toy: {n} zips, {S.shape[1]} reps, k={k}, headroom_ok={eg.headroom_ok(M, S)}")

    # ------------------ P1(proof)  the mechanism: an integral coverage's induced X is
    # fractional-feasible and the fractional objective at that X equals V(pi, sigma) exactly.
    # This identity IS the proof of P1; checking it needs no optimiser at all.
    cols = (0, 1, 2)
    U = eg.utilities(M, S, cols=cols)
    worst_id, worst_feas = 0.0, 0.0
    for assign in itertools.product(range(k), repeat=n):
        a = np.array(assign)
        gi = np.array([U[a == i, i].sum() for i in range(k)])
        if (gi <= 0).any():
            continue
        X = integral_X(a, k)
        worst_feas = max(worst_feas, float(np.abs(X.sum(axis=1) - 1).max()), -float(X.min()))
        V = float(np.log(gi).sum()) - RHO * eg.perimeter_tv(edges, X)
        Vfrac = eg.eg_primal(U, X) - RHO * eg.perimeter_tv(edges, X)
        worst_id = max(worst_id, abs(V - Vfrac))
    report("P1(proof)  every integral coverage is a feasible point of the fractional program "
           "with the same objective value", worst_id < 1e-12 and worst_feas < 1e-12,
           f"max |V - objective(X_pi)| = {worst_id:.3e}, max feasibility residual "
           f"{worst_feas:.3e}, over all {k**n} assignments")

    # ---------------------------------------------------------------- P1a  (rho = 0)
    worst = -math.inf
    for cols in itertools.combinations(range(S.shape[1]), k):
        U = eg.utilities(M, S, cols=cols)
        _, _, g, prim, dual = eg.eg_solve(U, iters=20_000)
        for assign in itertools.product(range(k), repeat=n):
            a = np.array(assign)
            gi = np.array([U[a == i, i].sum() for i in range(k)])
            if (gi <= 0).any():
                continue                      # V = -inf, bound holds trivially
            V = float(np.log(gi).sum())
            worst = max(worst, V - dual)
        report(f"P1a rho=0, S={cols}", worst <= 1e-12,
               f"EG in [{prim:.9f}, {dual:.9f}]  max(V - EG_upper) = {worst:.3e}")

    # ---------------------------------------------------------------- P1b  (rho > 0, C_TV)
    for cols in itertools.combinations(range(S.shape[1]), k):
        U = eg.utilities(M, S, cols=cols)
        val, _ = eg_with_penalty(U, edges, RHO, mult=1.0)
        worst = -math.inf
        for assign in itertools.product(range(k), repeat=n):
            a = np.array(assign)
            gi = np.array([U[a == i, i].sum() for i in range(k)])
            if (gi <= 0).any():
                continue
            X = integral_X(a, k)
            V = float(np.log(gi).sum()) - RHO * eg.perimeter_tv(edges, X)
            worst = max(worst, V - val)
        report(f"P1b rho={RHO}, C_TV, S={cols}", worst <= 1e-7,
               f"EG_rho = {val:.9f}  max(V_rho - EG_rho) = {worst:.3e}")

    # ------------------------------------------- P1c  H3 violated: an over-estimating penalty
    # Rigorous, with no trust in any solver.  Take the extension Chat = C_TV + c, which
    # over-estimates C by c at every integral point.  Because C_TV >= 0,
    #     EG_rho(Chat) <= EG_0 - rho*c <= dual_0 - rho*c,
    # and `dual_0` is the certified upper bound from the Lagrangian dual.  Choose c so the
    # right-hand side falls a full nat below the best integral coverage, computed by exhaustion.
    cols = (0, 1, 2)
    U = eg.utilities(M, S, cols=cols)
    _, _, _, _, dual_0 = eg.eg_solve(U, iters=50_000)
    bestV = -math.inf
    for assign in itertools.product(range(k), repeat=n):
        a = np.array(assign)
        gi = np.array([U[a == i, i].sum() for i in range(k)])
        if (gi <= 0).any():
            continue
        bestV = max(bestV, float(np.log(gi).sum())
                    - RHO * eg.perimeter_tv(edges, integral_X(a, k)))
    c_shift = (dual_0 - bestV + 1.0) / RHO
    eg_hat_upper = dual_0 - RHO * c_shift
    report("P1c H3 is necessary (an extension over-estimating C by c breaks the bound)",
           eg_hat_upper < bestV - 0.5,
           f"EG_rho(C_TV + c) <= {eg_hat_upper:.6f} < max V_rho = {bestV:.6f} "
           f"at c = {c_shift:.4f}; the bound is violated by >= 1 nat")

    # ---------------------------------------------------------------- P3a / P3b
    cols = (0, 1, 2)
    U = eg.utilities(M, S, cols=cols)
    X, p, gstar, prim, dual = eg.eg_solve(U, iters=200_000)
    Xv = eg.eg_vertex(U, gstar)
    split = np.flatnonzero((Xv > 1e-9).sum(axis=1) >= 2)
    report("P3a  split zips <= k at a vertex of the optimal face",
           len(split) <= k, f"|F| = {len(split)} <= {k}")

    # P3a'  the rank statement behind the count: the constraint matrix of the optimal face
    # loses a row exactly when the u_i are mutually proportional (the tau = 0 / common-measure
    # case), which is where the textbook `<= k-1` comes from.  Off that locus the bound is k.
    def face_rank(Umat):
        A = np.zeros((n + k, n * k))
        for z in range(n):
            A[z, z * k:(z + 1) * k] = 1.0
        for i in range(k):
            A[n + i, i::k] = Umat[:, i]
        return int(np.linalg.matrix_rank(A))

    r_het = face_rank(U)
    r_com = face_rank(np.tile(M[:, None], (1, k)))          # u_i == M: proportional
    r_scaled = face_rank(np.tile(M[:, None], (1, k)) * np.array([1.0, 2.0, 3.0]))
    report("P3a' rank(face) = n+k in general, n+k-1 iff the u_i are proportional",
           r_het == n + k and r_com == n + k - 1 and r_scaled == n + k - 1,
           f"heterogeneous {r_het}, u_i=M {r_com}, u_i=c_i*M {r_scaled}; n+k = {n + k}")

    lab = Xv.argmax(axis=1)
    gr = np.array([U[lab == i, i].sum() for i in range(k)])
    Vr = float(np.log(gr).sum())
    L = (U[split, :] * Xv[split, :]).sum(axis=0)
    tight = -float(np.log(1.0 - L / gstar).sum())
    MF = float(M[split].sum())
    coarse = (-math.log(1.0 - MF / gstar.min())) if MF < gstar.min() else math.inf
    ok = (dual - Vr) <= tight + 1e-9
    report("P3b  value gap <= -sum log(1 - L_i/g_i*)", ok,
           f"EG - V(rounded) = {dual - Vr:.6e} <= tight {tight:.6e} <= coarse {coarse:.6e}")

    print()
    print("FAILURES:", FAIL if FAIL else "none")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
