"""C3 addendum: does the balance pass widen the spread when the 'MILP y' is a realistic
band-constrained LP optimum (an extreme point that uses the whole band), rather than an
arbitrary feasible point?

Run:  /Users/ntlee/projects/td/.venv/bin/python3 \
        /Users/ntlee/projects/td/.claude/worktrees/vbl/docs/verify/state_splits_c3_band.py
"""

from __future__ import annotations

import sys
sys.path.insert(0, "/Users/ntlee/projects/td/.claude/worktrees/vbl/docs/verify")

import numpy as np
from scipy.optimize import linprog

from state_splits_checks import balance_pass, masses


def milp_like_y(M, z, tau, delta, cost, rng):
    """min cost . y  s.t.  sum_j y_sj = 1, band, 0 <= y <= z  -- what the MILP returns
    once z is fixed and the tie-break is the only thing left to optimise."""
    S, K = z.shape
    n = S * K
    A, lo, hi = [], [], []
    for s in range(S):
        r = np.zeros(n); r[s * K:(s + 1) * K] = 1.0
        A.append(r); lo.append(1.0); hi.append(1.0)
    for j in range(K):
        r = np.zeros(n)
        for s in range(S):
            r[s * K + j] = M[s]
        A.append(r); lo.append(tau * (1 - delta)); hi.append(tau * (1 + delta))
    A, lo, hi = np.array(A), np.array(lo), np.array(hi)
    bounds = [(0.0, float(z[s, j])) for s in range(S) for j in range(K)]
    res = linprog(cost.ravel(),
                  A_ub=np.vstack([A[np.isfinite(hi)], -A[np.isfinite(lo)]]),
                  b_ub=np.concatenate([hi[np.isfinite(hi)], -lo[np.isfinite(lo)]]),
                  bounds=bounds, method="highs")
    if res.status != 0:
        return None
    return res.x.reshape(S, K)


def main():
    rng = np.random.default_rng(2026)
    for delta in (0.01, 0.02, 0.05, 0.10, 0.25, 0.50):
        worst, n_ok = None, 0
        for _ in range(4000):
            S, K = 5, 3
            M = rng.uniform(0.2, 2.0, size=S)
            z = (rng.random((S, K)) < 0.6).astype(float)
            for s in range(S):
                if z[s].sum() == 0:
                    z[s, rng.integers(K)] = 1.0
            if not np.all(z.sum(0) > 0):
                continue
            tau = M.sum() / K
            cost = rng.uniform(0, 10, size=(S, K))
            y = milp_like_y(M, z, tau, delta, cost, rng)
            if y is None:
                continue
            n_ok += 1
            t, yp = balance_pass(M, z, tau)
            if t is None:
                continue
            v, vp = masses(M, y), masses(M, yp)
            d = (vp.max() - vp.min()) - (v.max() - v.min())
            if d > 1e-7 and (worst is None or d > worst[0]):
                worst = (d, M, z, y, v, vp, tau, np.abs(v - tau).max(), t)
        tag = "none" if worst is None else f"widened by {worst[0]:.4f}"
        print(f"delta = {delta:<5} feasible trials {n_ok:5d}   worst spread change: {tag}")
        if worst is not None:
            d, M, z, y, v, vp, tau, mdv, t = worst
            print(f"   M = {np.round(M, 4)}  tau = {tau:.4f}")
            print(f"   z =\n{z.astype(int)}")
            print(f"   y_MILP =\n{np.round(y, 4)}")
            print(f"   masses MILP {np.round(v, 4)} spread {v.max()-v.min():.4f} "
                  f"maxdev {mdv:.4f} (<= delta*tau = {delta*tau:.4f})")
            print(f"   masses pass {np.round(vp, 4)} spread {vp.max()-vp.min():.4f} "
                  f"maxdev {t:.4f}")


if __name__ == "__main__":
    main()
