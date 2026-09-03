"""U1-cert: the four named specialisations of the EG fibre program (proposition P2).

Run:  /Users/ntlee/projects/td/.venv/bin/python3 docs/artifacts/U1-cert/check_p2.py
from the worktree root.  Deterministic; the only seed is the toy's, 20260903.

  P2.1  cert_balance_ceiling   specialisation `u_i = lam*M`, `rho = 0`.
        EG_S = k log(lam*T/k), and the *dual* attains it at the price vector p_z = (k/T) M_z --
        an O(n)-checkable certificate.  Checked against
        `td/solvers/cert_draw.py::cert_balance_ceiling`.
  P2.2  cert_integer_balance_floor   NOT a specialisation.  Its LP relaxation has value 0, so
        it carries no dual bound at all; what it measures is the *slack in P1* at `u_i = lam*M`
        -- the achievability side of the same sandwich.  Checked by exhaustion:
        `ceiling - max_integral sum_j log M_j <= k eps^2 / (2 (1-eps)^2)` with `eps = t*/target`.
  P2.3  cert_assignment_at_centers   specialisation `u_i = lam*M`, `rho > 0`, centers pinned,
        integrality reimposed, and the log-balance term traded for an epsilon-constraint band.
        Checked against brute-force enumeration of all 3^8 integral assignments in the band.
  P2.4  cert_power_diagram   the KKT conditions of the *same* program at `rho > 0` before
        integrality.  Three claims, of which the third is conditional:
          (a) every EG optimum is supported on the power diagram of the pinned centers with
              weights `omega_j = 1/(rho m*_j)`  [unconditional];
          (b) `omega` is a *dual-optimal* weight vector of the transportation LP at targets
              `m*` -- its dual objective equals the primal cost  [unconditional];
          (c) the duals HiGHS actually returns satisfy `rho*beta_j - 1/m*_j = const`, i.e.
              `beta = omega + const`, **iff the LP at m* is nondegenerate**.  Both cases are
              exhibited: rho = 0.005 (support = n+k-1, identity to 5e-16) and rho = 0.02
              (support = n+k-2, identity fails while both duals attain the same bound).
"""
from __future__ import annotations

import itertools
import math
import sys

import numpy as np
from scipy.optimize import linprog

sys.path.insert(0, __file__.rsplit("/", 1)[0])
sys.path.insert(0, ".")
import eg  # noqa: E402
from td.solvers import cert_draw, centers as C_  # noqa: E402

FAIL = []


def report(name, ok, detail=""):
    print(f"[{'PASS' if ok else 'FAIL'}] {name}  {detail}")
    if not ok:
        FAIL.append(name)


def main():
    t = eg.toy()
    M, S, k, xy = t["M"], t["S"], t["k"], t["xy"]
    n = len(M)
    T = float(M.sum())
    lam = 0.30
    target = T / k

    # ------------------------------------------------------------------ P2.1 the ceiling
    U0 = np.tile((lam * M)[:, None], (1, k))               # u_i == lam*M, every fibre the same
    _, _, _, prim0, dual0 = eg.eg_solve(U0, iters=20_000)
    closed = k * math.log(lam * T / k)
    p_star = (k / T) * M                                   # the claimed optimal price vector
    dual_at_p = eg.eg_dual(U0, p_star)
    report("P2.1a  EG_S at u = lam*M equals k log(lam T / k)",
           abs(prim0 - closed) < 1e-9 and abs(dual0 - closed) < 1e-9,
           f"primal {prim0:.12f}  dual {dual0:.12f}  closed form {closed:.12f}")
    report("P2.1b  the dual attains it at p_z = (k/T) M_z",
           abs(dual_at_p - closed) < 1e-12,
           f"D(p*) = {dual_at_p:.12f}  (an O(n) certificate, no solver)")
    lab = np.array([0, 0, 1, 1, 2, 2, 0, 1])
    cert1 = cert_draw.cert_balance_ceiling(M, lab, k)
    report("P2.1c  = cert_balance_ceiling's ceiling_nash (at lam = 1)",
           abs(cert1["ceiling_nash"] - k * math.log(T / k)) < 1e-12,
           f"cert ceiling {cert1['ceiling_nash']:.12f}, EG at lam=1 {k*math.log(T/k):.12f}")
    report("P2.1d  headroom u_i(z) <= M_z => the ceiling bounds V, not only W",
           eg.headroom_ok(M, S),
           "max_i u_i(z)/M_z = "
           f"{float((eg.utilities(M, S).max(axis=1) / M).max()):.9f} <= 1")

    # ---------------------------------------------- P2.2 the integer floor does NOT collapse
    cols = n * k
    A_eq = np.zeros((n, cols + 1))
    for z in range(n):
        A_eq[z, z * k:(z + 1) * k] = 1.0
    A_ub = np.zeros((2 * k, cols + 1))
    b_ub = np.zeros(2 * k)
    for j in range(k):
        A_ub[j, j::k][:n] = M
        A_ub[j, cols] = -1.0
        b_ub[j] = target
        A_ub[k + j, j::k][:n] = -M
        A_ub[k + j, cols] = -1.0
        b_ub[k + j] = -target
    c = np.zeros(cols + 1)
    c[cols] = 1.0
    lp = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=np.ones(n),
                 bounds=[(0, 1)] * cols + [(0, None)], method="highs")
    report("P2.2a  the integer floor's LP relaxation has value 0 (no dual bound exists)",
           lp.success and abs(lp.fun) < 1e-9, f"LP optimum t = {lp.fun:.3e}")

    best_nash, best_t = -math.inf, math.inf
    for a in itertools.product(range(k), repeat=n):
        a = np.array(a)
        m = np.array([M[a == j].sum() for j in range(k)])
        if (m <= 0).any():
            continue
        best_nash = max(best_nash, float(np.log(m).sum()))
        best_t = min(best_t, float(np.abs(m - target).max()))
    ceiling = k * math.log(T / k)
    epsr = best_t / target
    bnd = k * epsr ** 2 / (2 * (1 - epsr) ** 2)
    report("P2.2b  ceiling - max_integral sum log M_j <= k eps^2 / (2(1-eps)^2)",
           (ceiling - best_nash) <= bnd + 1e-12,
           f"slack {ceiling - best_nash:.6e} <= {bnd:.6e}   (t* = {best_t:.6f}, "
           f"eps = {epsr:.6f})")

    # -------------------------- P2.3 assignment at pinned centers = the integral restriction
    ctr = np.array([(M[lab == j, None] * xy[lab == j]).sum(axis=0) / M[lab == j].sum()
                    for j in range(k)])
    d2 = ((xy[:, None, :] - ctr[None, :, :]) ** 2).sum(axis=2)
    cost = M[:, None] * d2
    c3 = cert_draw.cert_assignment_at_centers(xy, M, lab, ctr, time_limit=60.0)
    delta = c3["slack"]
    brute = math.inf
    for a in itertools.product(range(k), repeat=n):
        a = np.array(a)
        m = np.array([M[a == j].sum() for j in range(k)])
        if np.abs(m - target).max() > delta + 1e-9:
            continue
        brute = min(brute, float(cost[np.arange(n), a].sum()))
    report("P2.3  cert_assignment_at_centers = brute force over the same band",
           abs(c3["opt_cost"] - brute) < 1e-6 * max(brute, 1.0),
           f"MILP {c3['opt_cost']:.9f}  brute {brute:.9f}  (band delta = {delta:.6f})")

    # ---------------------------------- P2.4 power weights ARE the EG multipliers at rho > 0
    for rho, degenerate in ((0.005, False), (0.02, True)):
        X, m = eg.eg_solve_penalised(M, cost, rho)
        score = 1.0 / m[None, :] - rho * d2
        best = score.max(axis=1)
        insupp = all(float((best[z] - score[z, np.flatnonzero(X[z] > 1e-6)]).max()) < 1e-7
                     for z in range(n))
        report(f"P2.4a rho={rho}  supp(X*) subset of argmax_j (1/m_j - rho d^2)", insupp,
               f"{int((X > 1e-6).sum())} support entries, n+k-1 = {n + k - 1}")

        omega = 1.0 / (rho * m)
        alpha = M * np.min(d2 - omega[None, :], axis=1)
        dual_obj = float(alpha.sum() + m @ omega)
        prim_cost = float((cost * X).sum())
        viol = float((alpha[:, None] + M[:, None] * omega[None, :] - cost).max())
        report(f"P2.4b rho={rho}  omega = 1/(rho m*) is dual-OPTIMAL for the transport LP",
               abs(dual_obj - prim_cost) < 1e-8 * max(1.0, prim_cost) and viol < 1e-9,
               f"dual {dual_obj:.9f} = primal cost {prim_cost:.9f}, max violation {viol:.2e}")

        pw = C_.power_weights(xy, M, ctr, targets=m)
        beta = np.asarray(pw["weights_raw"], float)
        dev = rho * beta - 1.0 / m
        dev = dev - dev.mean()
        nondeg = int((X > 1e-6).sum()) == n + k - 1
        holds = float(np.abs(dev).max()) < 1e-9
        report(f"P2.4c rho={rho}  HiGHS beta satisfies rho*beta_j - 1/m_j = const "
               f"({'expected to FAIL: LP degenerate' if degenerate else 'LP nondegenerate'})",
               holds == (not degenerate) and nondeg == (not degenerate),
               f"max deviation {float(np.abs(dev).max()):.3e}; support "
               f"{int((X > 1e-6).sum())} vs n+k-1 = {n + k - 1}")
        report(f"P2.4d rho={rho}  both dual vectors attain the same bound",
               abs(pw["lp_bound"] - dual_obj) < 1e-8 * max(1.0, prim_cost),
               f"HiGHS lp_bound {pw['lp_bound']:.9f}, omega's dual {dual_obj:.9f}")

    print()
    print("FAILURES:", FAIL if FAIL else "none")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
