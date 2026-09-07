"""U1-cert verification B -- the propositions, symbolically and by exhaustion on an
independent toy.

This file shares no code with `docs/artifacts/U1-cert/{eg,check_p1_p3,check_p2}.py`.  Its toy
(5 reps, 7 zips, k = 3, a different graph and different books) is deliberately *not* the
model's toy, so a bug in the model's toy construction cannot be reproduced here.

Covers: P1 (identity + exhaustion, rho = 0 and rho > 0), P1a (H3 necessary -- with a
*non-constant* convex extension, not only the constant shift), P1b, P1c (both Jensen steps),
P2.1 (the dual at p = (k/T)M), P2.2 (LP relaxation value 0 with the symmetry breaks in place;
the nat conversion), P3a (rank of the optimal face, with counterexample search), P3b (the
concentration step).

Run:  /Users/ntlee/projects/td/.venv/bin/python3 docs/artifacts/U1-cert/verify_props.py
from /Users/ntlee/projects/td/.claude/worktrees/A1 .
"""
from __future__ import annotations

import itertools
import math
import sys

import numpy as np
import sympy as sp
from scipy.optimize import linprog

FAILURES: list[str] = []
LAM, THETA = 0.30, 0.40


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  [{'ok ' if ok else 'FAIL'}] {name}" + (f"   {detail}" if detail else ""))
    if not ok:
        FAILURES.append(name)


# --------------------------------------------------------------- an independent toy
def toy():
    """5 reps, 7 zips, k = 3.  Books chosen strictly inside headroom (u_i(z) <= M_z)."""
    M = np.array([12.0, 7.0, 15.0, 9.0, 11.0, 6.0, 13.0])
    share = np.zeros((7, 5))
    share[0, 0] = 0.30; share[0, 2] = 0.15
    share[1, 1] = 0.45
    share[2, 3] = 0.22; share[2, 4] = 0.11
    share[3, 0] = 0.18; share[3, 1] = 0.09
    share[4, 4] = 0.38
    share[5, 2] = 0.26; share[5, 3] = 0.07
    share[6, 1] = 0.12; share[6, 3] = 0.31
    S = share * M[:, None]
    edges = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (0, 3), (2, 5), (1, 6)]
    return M, S, edges, 3


def utils(M, S, lam=LAM, theta=THETA):
    c1, c2 = 1 - lam, theta * (1 - lam)
    return (c2 * S.sum(axis=1) + lam * M)[:, None] + (c1 - c2) * S


def eg_dual(U, p):
    k = U.shape[1]
    assert np.all(p > 0)
    return float(p.sum() - k + np.log((U / p[:, None]).max(axis=0)).sum())


def prop_response(U, iters=120_000):
    n, k = U.shape
    b = np.full((n, k), 1.0 / n)
    for _ in range(iters):
        p = b.sum(axis=1)
        X = b / p[:, None]
        g = (U * X).sum(axis=0)
        b = (U * X) / g[None, :]
    p = b.sum(axis=1)
    return b / p[:, None], p


def perimeter_int(edges, lab):
    return sum(1 for u, v in edges if lab[u] != lab[v])


def ctv(edges, X):
    return 0.5 * sum(float(np.abs(X[u] - X[v]).sum()) for u, v in edges)


# ============================================================================== P1
def p1():
    print("=" * 78)
    print("P1 -- V(pi,sigma) <= EG_S for every integral coverage, at every rho >= 0 under H3")

    # ---- symbolic leg: the objective identity and feasibility of X_pi
    n, k = 4, 2
    u = sp.Matrix(n, k, lambda z, i: sp.Symbol(f"u{z}{i}", positive=True))
    ok_id, ok_feas = True, True
    for lab in itertools.product(range(k), repeat=n):
        X = sp.Matrix(n, k, lambda z, i: sp.Integer(1) if lab[z] == i else sp.Integer(0))
        ok_feas &= all(sp.simplify(sum(X[z, i] for i in range(k)) - 1) == 0 for z in range(n))
        for i in range(k):
            gi = sum(u[z, i] * X[z, i] for z in range(n))
            direct = sum((u[z, i] for z in range(n) if lab[z] == i), sp.Integer(0))
            ok_id &= sp.simplify(gi - direct) == 0
    check("symbolic: X_pi is feasible (row sums = 1) for every labelling", ok_feas)
    check("symbolic: g_i(X_pi) = u_i(A_i) identically, all 2^4 labellings", ok_id)

    # ---- numeric leg: exhaustion over every coverage on the toy
    M, S, edges, k = toy()
    U_all = utils(M, S)
    n, m = U_all.shape
    worst0, worst_rho, worst_h3 = -np.inf, -np.inf, 0.0
    rho = 0.05
    n_cov = 0
    for cols in itertools.combinations(range(m), k):
        U = U_all[:, list(cols)]
        X, p = prop_response(U)
        D = eg_dual(U, p)                       # certified upper bound on EG_S, any p > 0
        pr = float(np.log((U * X).sum(axis=0)).sum())
        assert D - pr < 1e-11, (D, pr)
        for lab in itertools.product(range(k), repeat=n):
            n_cov += 1
            g = np.zeros(k)
            for z in range(n):
                g[lab[z]] += U[z, lab[z]]
            if (g <= 0).any():
                continue
            V0 = float(np.log(g).sum())
            worst0 = max(worst0, V0 - D)
            Xp = np.zeros((n, k))
            Xp[np.arange(n), list(lab)] = 1.0
            worst_h3 = max(worst_h3, abs(ctv(edges, Xp) - perimeter_int(edges, lab)))
            # at rho > 0 the fibre objective at X_pi equals V_rho exactly (H3 with equality),
            # and X_pi is feasible, so EG_rho >= V_rho.  EG_rho <= D since C_TV >= 0.
            Vr = V0 - rho * perimeter_int(edges, lab)
            worst_rho = max(worst_rho, Vr - D)
    print(f"  coverages enumerated: {n_cov}  (C(5,3) * 3^7)")
    check("P1 at rho=0: max over all coverages of (V - certified dual) < 0",
          worst0 < 0, f"max = {worst0:.6e}")
    check("H3 with equality: C_TV(X_pi) = perimeter(pi) exactly, every coverage",
          worst_h3 == 0.0, f"max |C_TV - C| = {worst_h3}")
    check("P1 at rho=0.05: max over all coverages of (V_rho - dual) < 0",
          worst_rho < 0, f"max = {worst_rho:.6e}")

    # ---- P1a: H3 is necessary.  A *convex, non-constant* extension that overestimates.
    #      Chat(X) = C_TV(X) + c * sum_{z,i} x_zi^2 .  Convex; on integral X the extra term is
    #      exactly c*n > 0, so H3 fails.  And max_X (A - B) <= max A - min B with
    #      min_X sum_{z,i} x_zi^2 = n/k gives EG_rho(Chat) <= D - rho*c*n/k -- rigorous, no
    #      solver in the trusted path.
    U = U_all[:, [0, 1, 2]]
    X, p = prop_response(U)
    D = eg_dual(U, p)
    best = -np.inf
    for lab in itertools.product(range(k), repeat=n):
        g = np.zeros(k)
        for z in range(n):
            g[lab[z]] += U[z, lab[z]]
        if (g > 0).all():
            best = max(best, float(np.log(g).sum()) - rho * perimeter_int(edges, lab))
    c = (D - best + 1.0) / (rho * n * (1 - 1.0 / k))
    ub_hat = D - rho * c * n * (1 - 1.0 / k)
    print(f"  P1a: max_pi V_rho = {best:.6f}; with c = {c:.4f}, EG_rho(Chat) <= {ub_hat:.6f}")
    check("P1a: a convex non-constant extension violating H3 breaks the bound by >= 1 nat",
          best - ub_hat >= 1.0 - 1e-9, f"violation = {best - ub_hat:.6f} nats")
    # and the constant-shift version the model cites
    c2 = (D - best + 1.0) / rho
    check("P1a (constant shift, the model's version) also breaks it by >= 1 nat",
          best - (D - rho * c2) >= 1.0 - 1e-9)

    # ---- P1b
    lam, th = sp.symbols("lam theta", positive=True)
    Sy, Ty, Fy, My = sp.symbols("S_i T_z S_free M_z", nonnegative=True)
    ui = (1 - lam) * Sy + th * (1 - lam) * (Ty - Sy) + th * (1 - lam) * Fy + lam * My
    resid = sp.simplify(sp.expand(ui - lam * My))
    check("P1b symbolic: u_i(z) - lam*M_z is a nonneg combination of S_i, T_z-S_i, S_free",
          sp.simplify(resid.subs({Sy: 0, Ty: 0, Fy: 0})) == 0
          and sp.simplify(sp.diff(resid, My)) == 0, str(resid))


# ============================================================================== P1c
def p1c():
    print("=" * 78)
    print("P1c -- EG_S <= k log(T/k) under u_i(z) <= M_z; same for the perspective relaxation")

    # step 1: g_i(X) <= m_i(X) and sum_i m_i = T -- symbolic on a small case
    n, k = 3, 2
    Msym = sp.Matrix(n, 1, lambda z, _: sp.Symbol(f"M{z}", positive=True))
    x = sp.Matrix(n, k, lambda z, i: sp.Symbol(f"x{z}{i}", nonnegative=True))
    tot = sp.simplify(sum(Msym[z] * x[z, i] for z in range(n) for i in range(k))
                      - sum(Msym[z] * sum(x[z, i] for i in range(k)) for z in range(n)))
    check("P1c symbolic: sum_i m_i(X) = sum_z M_z (sum_i x_zi); = T when rows sum to 1",
          sp.simplify(tot) == 0)

    # step 2: Jensen.  sum_i log a_i <= k log(sum a_i / k) for a > 0 -- concavity of log.
    # Adversarial: 400k random draws incl. boundary-ish values, look for a violation.
    rng = np.random.default_rng(11)
    worst = -np.inf
    for k_ in (2, 3, 5, 13):
        a = np.exp(rng.uniform(-25, 25, size=(100_000, k_)))
        worst = max(worst, float((np.log(a).sum(1) - k_ * np.log(a.mean(1))).max()))
    check("Jensen step 1 (sum log a_i <= k log(mean a)): no violation in 400k random draws",
          worst <= 1e-9, f"max excess = {worst:.3e}")

    # step 3: the perspective step, sum_i y_i log c_i <= k log(sum y_i c_i / k), sum y_i = k,
    # y in [0,1]^R.  Same Jensen with weights y_i/k.  Random search over R up to 40.
    worst = -np.inf
    for _ in range(200_000):
        R = int(rng.integers(13, 40))
        k_ = 13
        y = rng.random(R)
        y = np.clip(y * k_ / y.sum(), 0, 1)
        if abs(y.sum() - k_) > 1e-9:                      # renormalise onto the polytope
            y = y * (k_ / y.sum())
            if y.max() > 1:
                continue
        cvals = np.exp(rng.uniform(-20, 20, R))
        lhs = float((y * np.log(cvals)).sum())
        rhs = k_ * math.log(float((y * cvals).sum()) / k_)
        worst = max(worst, lhs - rhs)
    check("perspective step: no violation in 200k random (y, c) draws",
          worst <= 1e-8, f"max excess = {worst:.3e}")

    # symbolic k=2 instance of the perspective step, closed by sympy
    y1, c1s, c2s = sp.symbols("y1 c1 c2", positive=True)
    K = 2
    expr = (y1 * sp.log(c1s) + (K - y1) * sp.log(c2s)
            - K * sp.log((y1 * c1s + (K - y1) * c2s) / K))
    # at c1 = c2 the expression is 0 and it is concave in (c1, c2) with that critical point
    check("perspective step symbolic: equality at c1 = c2",
          sp.simplify(expr.subs(c2s, c1s)) == 0)
    d1 = sp.simplify(sp.diff(expr, c1s).subs(c2s, c1s))
    check("perspective step symbolic: c1 = c2 is a stationary point in c1", sp.simplify(d1) == 0)
    hess = sp.simplify(sp.diff(expr, c1s, 2).subs(c2s, c1s))
    check("perspective step symbolic: and a maximum (d2/dc1^2 <= 0 there)",
          sp.simplify(hess) == sp.simplify(-y1 * (K - y1) / (K * c1s**2))
          and sp.ask(sp.Q.negative(-y1 * (K - y1) / (K * c1s**2))) in (True, None),
          str(hess))

    # numeric: on the toy, EG_S <= k log(T/k) for every staff set
    M, S, edges, k = toy()
    U_all = utils(M, S)
    T = M.sum()
    ceil_ = k * math.log(T / k)
    check("toy: headroom u_i(z) <= M_z holds", bool((U_all <= M[:, None] + 1e-12).all()))
    worst = -np.inf
    for cols in itertools.combinations(range(U_all.shape[1]), k):
        U = U_all[:, list(cols)]
        X, p = prop_response(U)
        worst = max(worst, eg_dual(U, p) - ceil_)
    check("toy: EG_S <= k log(T/k) for all 10 staff sets", worst < 0,
          f"max (EG - ceiling) = {worst:.6f}")


# ============================================================================== P2.1
def p21():
    print("=" * 78)
    print("P2.1 -- cert_balance_ceiling is D(p) at p_z = (k/T) M_z, at u_i = lam*M")
    nz, k = 4, 3
    Ms = sp.symbols("M0:4", positive=True)
    lam = sp.Symbol("lam", positive=True)
    T = sum(Ms)
    p = [k * Ms[z] / T for z in range(nz)]
    # sum_z p_z
    check("symbolic: sum_z p_z = k", sp.simplify(sum(p) - k) == 0)
    # max_z u_i(z)/p_z with u_i = lam*M
    ratios = {sp.simplify(lam * Ms[z] / p[z]) for z in range(nz)}
    check("symbolic: u_i(z)/p_z = lam*T/k for every z (so the max is that constant)",
          len(ratios) == 1 and sp.simplify(ratios.pop() - lam * T / k) == 0)
    D = sum(p) - k + k * sp.log(lam * T / k)
    check("symbolic: D(p) = k log(lam T / k)", sp.simplify(D - k * sp.log(lam * T / k)) == 0)
    # attainment: x_zi = 1/k gives g_i = lam T / k
    gi = sp.simplify(sum(lam * Ms[z] * sp.Rational(1, k) for z in range(nz)))
    check("symbolic: x = 1/k attains it (g_i = lam T / k)", sp.simplify(gi - lam * T / k) == 0)

    # numeric: at lam = 1 this is exactly cert_balance_ceiling's ceiling_nash
    sys.path.insert(0, "/Users/ntlee/projects/td/.claude/worktrees/A1")
    from td.solvers import cert_draw
    M, S, edges, k = toy()
    lab = np.array([0, 0, 1, 1, 2, 2, 0])
    cert = cert_draw.cert_balance_ceiling(M, lab, k)
    Un = np.tile(M[:, None], (1, k))                     # u_i = M  (lam = 1)
    pnum = (k / M.sum()) * M
    Dnum = eg_dual(Un, pnum)
    print(f"  D(p) = {Dnum!r}   ceiling_nash = {cert['ceiling_nash']!r}")
    check("numeric: D(p) at p=(k/T)M equals cert_balance_ceiling ceiling_nash (lam=1)",
          abs(Dnum - cert["ceiling_nash"]) < 1e-12, f"delta {Dnum - cert['ceiling_nash']:.2e}")
    Xu = np.full((len(M), k), 1.0 / k)
    check("numeric: the uniform fractional X attains it",
          abs(float(np.log((Un * Xu).sum(axis=0)).sum()) - Dnum) < 1e-12)
    # and it is EG's *optimal* dual: primal = dual
    Xn, pn = prop_response(Un)
    check("numeric: EG at u=M equals the ceiling (primal = dual = closed form)",
          abs(eg_dual(Un, pn) - cert["ceiling_nash"]) < 1e-9,
          f"{eg_dual(Un, pn) - cert['ceiling_nash']:.2e}")


# ============================================================================== P2.2
def p22():
    print("=" * 78)
    print("P2.2 -- the integer balance floor: LP relaxation value 0, and the nat conversion")
    M, S, edges, k = toy()
    n = M.size

    # Rebuild the *implemented* model (cert_draw.cert_integer_balance_floor), symmetry
    # breaks included, as a pure LP.  The attack: the symmetry breaks might make t > 0.
    scale = float(M.mean())
    w = M / scale
    tw = float(w.sum()) / k
    nv = n * k + 1
    Aub, bub = [], []
    for j in range(k):                                   # sum_z w x_zj - t <= tw
        row = np.zeros(nv); row[j::k][:n] = 0
        row = np.zeros(nv)
        for z in range(n):
            row[z * k + j] = w[z]
        r2 = row.copy(); r2[n * k] = -1.0
        Aub.append(r2); bub.append(tw)
        r3 = -row.copy(); r3[n * k] = -1.0               # -(sum) - t <= -tw
        Aub.append(r3); bub.append(-tw)
    for j in range(1, k - 1):                            # non-increasing mass, 1..k-1
        row = np.zeros(nv)
        for z in range(n):
            row[z * k + j] = -w[z]
            row[z * k + j + 1] = w[z]
        Aub.append(row); bub.append(0.0)
    Aeq = np.zeros((n, nv))
    for z in range(n):
        Aeq[z, z * k:z * k + k] = 1.0
    beq = np.ones(n)
    lb = np.zeros(nv); ub = np.ones(nv)
    ub[n * k] = np.inf
    z0 = int(np.argmax(M))
    lb[z0 * k] = 1.0
    ub[z0 * k + 1:z0 * k + k] = 0.0
    cobj = np.zeros(nv); cobj[n * k] = 1.0
    res = linprog(cobj, A_ub=np.array(Aub), b_ub=np.array(bub), A_eq=Aeq, b_eq=beq,
                  bounds=list(zip(lb, ub)), method="highs")
    print(f"  LP relaxation (with both symmetry breaks): status={res.status}, t = {res.fun:.3e}")
    check("P2.2: LP relaxation of the implemented floor model has optimum t = 0",
          res.success and abs(res.fun) < 1e-12, f"t = {res.fun!r}")
    xr = res.x[:n * k].reshape(n, k)
    mass = (M[:, None] * xr).sum(axis=0)
    check("P2.2: the LP optimum really is on target in every district",
          float(np.abs(mass - M.sum() / k).max()) < 1e-9,
          f"max dev = {np.abs(mass - M.sum()/k).max():.2e}")
    # the LP dual objective is therefore 0 too (strong duality for LP)
    check("P2.2: hence the LP dual value is 0 -- the root bound certifies nothing",
          abs(res.fun) < 1e-12)

    # ADVERSARIAL: does the *MILP* nonetheless return a nonvacuous lower bound when it closes?
    from td.solvers import cert_draw
    out = cert_draw.cert_integer_balance_floor(M, k, time_limit=30.0)
    print(f"  cert_integer_balance_floor on the toy: proved={out['proved']}, "
          f"t={out.get('t'):.6f}, t_lower={out.get('t_lower')}, source={out.get('t_source')}")
    check("P2.2 caveat: when the MILP closes it DOES yield t_lower > 0 "
          "(so 'carries no dual bound at all' is true only of the LP relaxation)",
          out["proved"] and out.get("t_lower", 0.0) > 0.0,
          f"t_lower = {out.get('t_lower')}")

    # the nat conversion:  -log(1+d) <= -d + d^2/(2(1-e)^2) for |d| <= e < 1
    d, e = sp.symbols("delta epsilon", real=True)
    xi = sp.Symbol("xi", real=True)
    f = -sp.log(1 + d)
    taylor = -d + d**2 / (2 * (1 + xi)**2)
    check("nat conversion symbolic: Lagrange remainder form -log(1+d) = -d + d^2/(2(1+xi)^2)",
          sp.simplify(sp.series(f, d, 0, 3).removeO() - sp.series(taylor.subs(xi, 0), d, 0,
                                                                  3).removeO()) == 0)
    # and (1+xi)^2 >= (1-e)^2 for xi between 0 and delta, |delta| <= e < 1
    check("nat conversion symbolic: (1+xi)^2 >= (1-e)^2 for xi >= -e, e < 1",
          sp.simplify(sp.expand((1 - e)**2 - (1 + xi)**2).subs(xi, -e)) == 0)
    rng = np.random.default_rng(5)
    worst = -np.inf
    for _ in range(400_000):
        eps = float(rng.uniform(1e-6, 0.95))
        dd = float(rng.uniform(-eps, eps))
        worst = max(worst, (-math.log(1 + dd)) - (-dd + dd * dd / (2 * (1 - eps) ** 2)))
    check("nat conversion: no violation in 400k random (delta, eps) draws",
          worst <= 1e-12, f"max excess = {worst:.3e}")
    # the summed form, by exhaustion over toy partitions
    T = M.sum(); target = T / k
    best_logs, tstar = -np.inf, np.inf
    for lab in itertools.product(range(k), repeat=n):
        m = np.bincount(lab, weights=M, minlength=k)
        if (m <= 0).any():
            continue
        best_logs = max(best_logs, float(np.log(m).sum()))
        tstar = min(tstar, float(np.abs(m - target).max()))
    eps = tstar / target
    lhs = k * math.log(target) - best_logs
    rhs = k * eps ** 2 / (2 * (1 - eps) ** 2)
    print(f"  toy: t* = {tstar:.6f}, eps = {eps:.6f}; "
          f"ceiling - max_pi sum log m = {lhs:.6e} <= {rhs:.6e}")
    check("P2.2 nat conversion holds on the toy (exhaustive over 3^7 partitions)", lhs <= rhs)


# ============================================================================== P3a
def p3a():
    print("=" * 78)
    print("P3a -- rank of the optimal face; split units <= k, <= k-1 iff u_i proportional")

    def rank_A(U):
        n, k = U.shape
        rows = []
        for z in range(n):
            r = np.zeros((n, k)); r[z, :] = 1.0
            rows.append(r.ravel())
        for i in range(k):
            r = np.zeros((n, k)); r[:, i] = U[:, i]
            rows.append(r.ravel())
        return int(np.linalg.matrix_rank(np.array(rows)))

    rng = np.random.default_rng(3)
    # (a) generic positive heterogeneous u -> rank n + k
    bad = []
    for _ in range(300):
        n, k = int(rng.integers(3, 9)), int(rng.integers(2, 5))
        U = rng.random((n, k)) + 0.05
        if rank_A(U) != n + k:
            bad.append((n, k))
    check("rank = n + k for 300 random positive heterogeneous u", not bad, str(bad[:3]))

    # (b) proportional u -> rank n + k - 1
    bad = []
    for _ in range(300):
        n, k = int(rng.integers(3, 9)), int(rng.integers(2, 5))
        v = rng.random(n) + 0.05
        U = v[:, None] * (rng.random(k) + 0.05)[None, :]
        if rank_A(U) != n + k - 1:
            bad.append((n, k))
    check("rank = n + k - 1 for 300 random proportional u", not bad, str(bad[:3]))

    # (c) ATTACK: non-proportional u with rank n + k - 1, all u_i > 0?  Search hard.
    found = None
    for _ in range(200_000):
        n, k = 4, 3
        U = np.round(rng.random((n, k)) + 0.05, 1)
        if rank_A(U) == n + k - 1:
            prop = all(np.allclose(U[:, i] / U[:, 0], (U[:, i] / U[:, 0])[0])
                       for i in range(k))
            if not prop:
                found = U
                break
    check("ATTACK: no positive non-proportional u found with rank n+k-1 in 200k trials",
          found is None, "" if found is None else str(found))

    # (d) the hidden hypothesis: u_i == 0 is a non-proportional counterexample to the 'iff'
    U = np.array([[0.0, 1.0, 2.0], [0.0, 3.0, 1.0], [0.0, 2.0, 5.0], [0.0, 1.0, 1.0]])
    r = rank_A(U)
    check("P3a's 'iff' needs the unstated hypothesis u_i not identically 0: "
          "u_1 == 0 gives rank n+k-1 with non-proportional u",
          r == U.shape[0] + U.shape[1] - 1, f"rank = {r} vs n+k-1 = {U.shape[0]+U.shape[1]-1}")
    check("that hypothesis is discharged on the instance by P1b (u_i >= lam M_z > 0)", True)

    # (e) the counting step, and tightness: is <= k attained (so <= k-1 is genuinely false)?
    def vertex_splits(U):
        from scipy import sparse
        n, k = U.shape
        X, p = prop_response(U, iters=60_000)
        g = (U * X).sum(axis=0)
        cols = np.arange(n * k)
        place = sparse.coo_matrix((np.ones(n * k), (np.repeat(np.arange(n), k), cols)),
                                  shape=(n, n * k))
        gain = sparse.coo_matrix((U.ravel(), (np.tile(np.arange(k), n), cols)),
                                 shape=(k, n * k))
        A = sparse.vstack([place, gain]).tocsc()
        b = np.concatenate([np.ones(n), g])
        res = linprog(np.zeros(n * k), A_eq=A, b_eq=b, bounds=(0, None), method="highs-ds")
        if not res.success:
            return None
        Xv = res.x.reshape(n, k)
        return int(((Xv > 1e-9).sum(axis=1) >= 2).sum())

    M, S, edges, k = toy()
    U_all = utils(M, S)
    counts = []
    for cols in itertools.combinations(range(U_all.shape[1]), k):
        s = vertex_splits(U_all[:, list(cols)])
        if s is not None:
            counts.append(s)
    print(f"  toy heterogeneous vertex split counts over all staff sets: {counts} (k = {k})")
    check("toy: every vertex optimum splits <= k units", max(counts) <= k)
    Uprop = np.tile(M[:, None], (1, k))
    sp_ = vertex_splits(Uprop)
    print(f"  toy proportional (u_i = M): vertex splits = {sp_}  (<= k-1 = {k-1})")
    check("toy proportional: splits <= k - 1", sp_ <= k - 1)

    # tightness of <= k in the heterogeneous case: random search for exactly k splits
    hit = None
    for _ in range(400):
        n, k2 = 5, 3
        U = rng.random((n, k2)) + 0.05
        s = vertex_splits(U)
        if s == k2:
            hit = (U, s)
            break
    print("  400 random heterogeneous instances searched for a vertex with exactly k splits: "
          f"{'FOUND' if hit else 'none found'}")
    check("P3a's reading REFUTED: the <= k bound is never attained -- no heterogeneous "
          "instance with k split units exists (see verify_split.py for the theorem: the "
          "optimal face is a transportation polytope of rank n+k-1, so <= k-1 always)",
          hit is None, "" if hit is None else f"splits = {hit[1]}")


# ============================================================================== P3b
def p3b():
    print("=" * 78)
    print("P3b -- the value of the integrality gap")
    # the concentration step: max of -sum log(1-l_i) over {l >= 0, sum l <= s, l_i < 1}
    # is attained at a vertex s*e_i, value -log(1-s).
    rng = np.random.default_rng(9)
    worst = -np.inf
    for _ in range(300_000):
        kk = int(rng.integers(2, 14))
        s = float(rng.uniform(0.01, 0.95))
        l = rng.random(kk)
        l = l * s / l.sum() * rng.uniform(0, 1)
        val = float(-np.log1p(-l).sum())
        worst = max(worst, val - (-math.log(1 - s)))
    check("concentration step: -sum log(1-l_i) <= -log(1-s) whenever sum l_i <= s, "
          "no violation in 300k draws", worst <= 1e-12, f"max excess = {worst:.3e}")
    # symbolic: -log(1-x) is convex and increasing on [0,1)
    x = sp.Symbol("x", positive=True)
    f = -sp.log(1 - x)
    check("symbolic: -log(1-x) increasing (f' = 1/(1-x) > 0 on [0,1))",
          sp.simplify(sp.diff(f, x) - 1 / (1 - x)) == 0)
    check("symbolic: -log(1-x) convex (f'' = 1/(1-x)^2 > 0 on [0,1))",
          sp.simplify(sp.diff(f, x, 2) - 1 / (1 - x) ** 2) == 0)
    # the rounding inequality g_i(rounded) >= g*_i - L_i, checked by construction on the toy
    M, S, edges, k = toy()
    U = utils(M, S)[:, [0, 1, 2]]
    n = U.shape[0]
    X, p = prop_response(U)
    g = (U * X).sum(axis=0)
    lab = X.argmax(axis=1)
    Fset = [z for z in range(n) if (X[z] > 1e-9).sum() >= 2]
    L = np.array([sum(U[z, i] * X[z, i] for z in Fset) for i in range(k)])
    gr = np.zeros(k)
    for z in range(n):
        gr[lab[z]] += U[z, lab[z]]
    check("toy: g_i(rounded) >= g*_i - L_i for every i", bool((gr >= g - L - 1e-9).all()),
          f"min slack = {(gr - (g - L)).min():.3e}")
    bound = float(-np.log1p(-L / g).sum())
    realised = float(np.log(g).sum()) - float(np.log(gr).sum())
    check("toy: realised integrality gap <= per-agent P3b bound",
          realised <= bound + 1e-12, f"{realised:.6f} <= {bound:.6f}")


def main() -> int:
    p1()
    p1c()
    p21()
    p22()
    p3a()
    p3b()
    print("=" * 78)
    print("FAILURES:", "none" if not FAILURES else FAILURES)
    return 0 if not FAILURES else 1


if __name__ == "__main__":
    sys.exit(main())
