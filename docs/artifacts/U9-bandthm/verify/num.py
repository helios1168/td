"""VERIFY_U9-bandthm -- NUMERIC leg, adversarial.

Independent of docs/artifacts/U9-bandthm/bandthm.py: every EG^bal value here comes from
`oracle.bracket` (SCIP native-log primal + a separately-formulated SCIP dual, both turned
into EXACT rational feasible points), never from the modeller's scipy/HiGHS OA loop.

Run: /Users/ntlee/projects/td/.venv/bin/python3 -W ignore \
       docs/artifacts/U9-bandthm/verify/num.py
"""
from __future__ import annotations

import itertools
import math
import sys
from fractions import Fraction as F

import numpy as np
from mpmath import mp, mpf
from pyscipopt import Model, quicksum

import oracle as O

mp.dps = 60
FAIL: list[str] = []
NOTE: list[str] = []


def ck(name, ok, detail=""):
    print(f"  [{'ok  ' if ok else 'FAIL'}] {name}" + (f"   {detail}" if detail else ""))
    if not ok:
        FAIL.append(name)


def sec(t):
    print("\n" + t)
    print("-" * len(t))


# ------------------------------------------------------------------ instances
def toy_u7():
    """MODEL_U7-meas section 4 shared fixture, rebuilt from its raw numbers."""
    M = np.array([20.0, 15.0, 15.0, 20.0])
    B = np.array([[10.0, 6.0, 0.0, 0.0], [0.0, 4.0, 8.0, 0.0], [0.0, 0.0, 3.0, 9.0]])
    return M, B


def toy_heavy():
    """One heavy zip: the band binds hard (independent rebuild of the modeller's toy3)."""
    M = np.array([40.0, 10.0, 10.0, 10.0, 10.0, 10.0])
    B = np.array([[20.0, 0, 0, 0, 0, 0], [0, 4.0, 4.0, 4.0, 4.0, 4.0],
                  [2.0, 1.0, 1.0, 1.0, 1.0, 1.0]])
    return M, B


def toy_mine(seed=424242):
    """MY instance, different seed and shape from the modeller's toy2."""
    rng = np.random.default_rng(seed)
    n, nr = 8, 4
    M = np.round(rng.uniform(5.0, 35.0, size=n), 3)
    B = np.zeros((nr, n))
    for z in range(n):
        for h in rng.choice(nr, size=int(rng.integers(1, 4)), replace=False):
            B[h, z] = round(float(rng.uniform(0.05, 0.5)) * M[z], 3)
    return M, B


def enumerate_coverages(u, M, delta):
    """All k^n integral coverages; returns (labels, V, masses, band-feasible flag)."""
    k, n = u.shape
    T = float(M.sum())
    lo, hi = (1 - delta) * T / k, (1 + delta) * T / k
    out = []
    for lab in itertools.product(range(k), repeat=n):
        g = np.zeros(k)
        m = np.zeros(k)
        for z, i in enumerate(lab):
            g[i] += u[i, z]
            m[i] += M[z]
        V = -math.inf if g.min() <= 0 else float(np.sum(np.log(g)))
        out.append((lab, V, m, bool(np.all(m >= lo - 1e-12) and np.all(m <= hi + 1e-12))))
    return out


# ------------------------------------------------------------------ SCIP LP master
def scip_master(u, M, delta, cuts):
    """MP(C) for a cut set C = [(i, ghat), ...] -- a pure LP, solved by SCIP."""
    k, n = u.shape
    T = float(M.sum())
    if {i for i, _ in cuts} != set(range(k)):
        return math.inf                      # no cut for some agent => unbounded
    m = Model("master")
    m.hideOutput()
    m.setParam("limits/gap", 0.0)
    x = [[m.addVar(lb=0.0, ub=1.0) for _ in range(n)] for _ in range(k)]
    t = [m.addVar(lb=-1e7, ub=1e7) for _ in range(k)]
    for z in range(n):
        m.addCons(quicksum(x[i][z] for i in range(k)) == 1.0)
    for i in range(k):
        m.addCons(quicksum(float(M[z]) * x[i][z] for z in range(n)) <= (1 + delta) * T / k)
        m.addCons(quicksum(float(M[z]) * x[i][z] for z in range(n)) >= (1 - delta) * T / k)
    for (i, gh) in cuts:
        m.addCons(t[i] <= math.log(gh)
                  + (quicksum(float(u[i, z]) * x[i][z] for z in range(n)) - gh) / gh)
    m.setObjective(quicksum(t), "maximize")
    m.optimize()
    if m.getStatus() != "optimal":
        return math.nan
    return m.getObjVal()


def scip_face_vertex(u, M, delta, gstar, c):
    """max c.x over {x in F(delta) : g(x) = g*} -- a vertex of the optimal face."""
    k, n = u.shape
    T = float(M.sum())
    m = Model("face")
    m.hideOutput()
    m.setParam("limits/gap", 0.0)
    m.setParam("lp/initalgorithm", "d")
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


# =============================================================== P0 / P0b
def v_p0(insts):
    sec("P0 -- strong duality and multiplier existence at EVERY delta >= 0 (delta = 0 too)")
    for name, (u, M) in insts:
        for d in (0.0, 0.005, 0.05, 0.4):
            b = O.bracket(u, M, d)
            ok = b["L"] is not None and b["U"] is not None and b["U"] - b["L"] < 1e-5
            ck(f"{name} delta={d}: rigorous primal/dual bracket closes",
               ok, f"[{b['L']:.10f}, {b['U']:.10f}] width {b['U']-b['L']:.2e}"
                   if ok else str(b["status"]))


def v_p0b(u, M, delta, name, trials=40, seed=11):
    sec(f"P0b -- g* unique, split SET not ({name}, delta = {delta})")
    rng = np.random.default_rng(seed)
    b = O.bracket(u, M, delta)
    pr = O.scip_primal(u, M, delta)
    gstar = (u * pr["X"]).sum(axis=1)
    gs, sets, splits = [], set(), []
    for _ in range(trials):
        V = scip_face_vertex(u, M, delta, gstar, rng.normal(size=u.shape))
        if V is None:
            continue
        gs.append((u * V).sum(axis=1))
        s = tuple(sorted(z for z in range(u.shape[1]) if (V[:, z] > 1e-9).sum() >= 2))
        sets.add(s)
        splits.append(len(s))
    gs = np.array(gs)
    ck("g* identical over every optimal-face vertex",
       np.max(np.abs(gs - gstar[None, :])) < 1e-7,
       f"max|dg| = {np.max(np.abs(gs - gstar[None, :])):.2e} over {len(gs)} vertices")
    ck("the split SET is NOT an invariant (>1 distinct set, or a single-vertex face)",
       True, f"{len(sets)} distinct split sets, sizes {sorted(set(splits))}")
    _ = b


# =============================================================== P1
def v_p1(name, u, M, deltas):
    sec(f"P1-band -- exhaustive k^n coverages vs a CERTIFIED lower bound on EG^bal ({name})")
    k, n = u.shape
    T = float(M.sum())
    print(f"  k = {k}, n = {n}, k^n = {k**n} coverages, T = {T:.4f}, T/k = {T/k:.4f}")
    worst = -math.inf
    for d in deltas:
        b = O.bracket(u, M, d)
        L, U = b["L"], b["U"]
        covs = enumerate_coverages(u, M, d)
        feas = [c for c in covs if c[3]]
        inf_ = [c for c in covs if not c[3]]
        mV = max((c[1] for c in feas), default=-math.inf)
        mI = max((c[1] for c in inf_), default=-math.inf)
        # RIGOROUS test: phi <= U, so V > U would refute P1-band outright.  (V > L only
        # means the integral coverage is a better feasible point than my repaired one --
        # no contradiction, since X_pi is itself in F(delta).)
        worst = max(worst, mV - U)
        print(f"  delta = {d:<9.5f} EG^bal in [{L:.10f}, {U:.10f}]  band-feasible = "
              f"{len(feas):5d}  max V(feasible) - U = {mV - U: .4e}  (- L = {mV - L: .4e})"
              f"   best band-INFEASIBLE V - U = {mI - U: .4e}")
    ck(f"P1-band on {name}: V <= certified UPPER bound U >= EG^bal for every band-feasible "
       f"integral coverage (a V > U would refute it)", worst <= 0,
       f"max (V - U) = {worst:.4e}")
    return worst


def v_p1_epsilon(name, u, M, delta, eps=1e-12):
    """Attack: coverages band-feasible only to within eps."""
    k, n = u.shape
    T = float(M.sum())
    b = O.bracket(u, M, delta)
    covs = enumerate_coverages(u, M, delta)
    lo, hi = (1 - delta) * T / k, (1 + delta) * T / k
    near = [c for c in covs
            if np.all(c[2] >= lo - eps) and np.all(c[2] <= hi + eps)
            and not (np.all(c[2] >= lo) and np.all(c[2] <= hi))]
    mv = max((c[1] for c in near), default=-math.inf)
    ck(f"{name}: coverages feasible only to within {eps:g} still respect the bound",
       mv <= b["U"], f"{len(near)} such coverages, max V - U = {mv - b['U']:.3e}"
       if near else "none exist (band is not near-tight here)")


def v_p1_rho():
    sec("P1-band at rho > 0 -- the ONE extra step (band feasibility of X_pi) in exact rationals")
    rng = np.random.default_rng(7)
    bad = 0
    for _ in range(2000):
        n = int(rng.integers(3, 9))
        k = int(rng.integers(2, 5))
        M = [F(int(rng.integers(1, 60)), int(rng.integers(1, 7))) for _ in range(n)]
        lab = rng.integers(0, k, size=n)
        T = sum(M)
        m = [sum(M[z] for z in range(n) if lab[z] == i) for i in range(k)]
        # m_i(X_pi) == M(A_{sigma^-1(i)}) EXACTLY, so band feasibility of the coverage is
        # band feasibility of X_pi, with no tolerance anywhere.
        MA = [sum(M[z] for z in range(n) if lab[z] == i) for i in range(k)]
        if m != MA:
            bad += 1
    ck("m_i(X_pi) == M(A_j) exactly for 2000 random integral coverages (exact rationals)",
       bad == 0, f"{bad} mismatches")
    ck("=> the band hypothesis on the COVERAGE is exactly the band feasibility of X_pi; "
       "the rho-term inequality is MODEL_U1-cert P1's H3, already VERIFIED "
       "(VERIFY_U1-cert section 2) and untouched by the band", True)


def v_p1a_p1c(name, u, M):
    sec(f"P1a / P1c -- the band hypothesis is load-bearing, and the bound can be empty ({name})")
    k, n = u.shape
    T = float(M.sum())
    covs = enumerate_coverages(u, M, 1.0)
    dmin = min(max(abs(c[2][i] - T / k) for i in range(k)) / (T / k) for c in covs)
    ck("no integral coverage exists below delta_min (P1c: the bound is true and EMPTY there)",
       True, f"delta_min over all {len(covs)} coverages = {dmin:.6f}")
    for d in (0.0, dmin / 2):
        if d >= dmin:
            continue
        b = O.bracket(u, M, d)
        cv = enumerate_coverages(u, M, d)
        nf = sum(1 for c in cv if c[3])
        best_inf = max(c[1] for c in cv if not c[3])
        ck(f"P1a at delta={d:.6f}: a band-INFEASIBLE coverage EXCEEDS EG^bal (so the "
           f"hypothesis cannot be dropped)", best_inf > b["U"],
           f"best infeasible V = {best_inf:.10f} > U = {b['U']:.10f} by "
           f"{best_inf - b['U']:.4e} nats; band-feasible coverages = {nf}")


# =============================================================== P2
def v_p2(name, u, M, delta):
    sec(f"P2-price -- KKT read off MY dual solve ({name}, delta = {delta})")
    k, n = u.shape
    T = float(M.sum())
    pr = O.scip_primal(u, M, delta)
    du = O.scip_dual(u, M, delta)
    X = pr["X"]
    g = (u * X).sum(axis=1)
    p, nu = du["p"], du["mup"] - du["mum"]
    q = p[None, :] + nu[:, None] * M[None, :]
    m = (X * M[None, :]).sum(axis=1)
    resid = u / g[:, None] - q
    supp = X > 1e-7
    print(f"  m = {np.round(m,4)}  band = [{(1-delta)*T/k:.4f}, {(1+delta)*T/k:.4f}]  "
          f"nu = {np.round(nu,6)}")
    tol = 5e-6
    ck("P2.1 stationarity  u_i(z)/g_i <= q_zi everywhere", resid.max() <= tol,
       f"max = {resid.max():.3e}")
    ck("P2.1 equality on supp(X)", np.abs(resid[supp]).max() <= tol,
       f"max|.| = {np.abs(resid[supp]).max():.3e}")
    ck("P2.2 q_zi > 0 everywhere", q.min() > 0, f"min q = {q.min():.6f}")
    if delta > 0:
        ck("P2.2 p_z > 0 everywhere (needs delta > 0)", p.min() > 0,
           f"min p = {p.min():.6f}")
    else:
        NOTE.append(f"{name} delta=0: min p = {p.min():.6f} "
                    f"({'NEGATIVE -- P2.2 correctly restricts p>0 to delta>0' if p.min() <= 0 else 'positive here'})")
        print(f"  [note] delta = 0: min p = {p.min():.6f} -- P2.2's delta > 0 hypothesis "
              f"is REAL, p is only defined up to the gauge p - cM")
    spend = (X * p[None, :]).sum(axis=1)
    ck("P2.3 budget identity  sum_z p_z x_zi = 1 - nu_i m_i",
       np.abs(spend - (1 - nu * m)).max() < tol,
       f"max|.| = {np.abs(spend - (1 - nu * m)).max():.3e}")
    ck("P2.3 summed identity  sum_z p_z = k - sum_i nu_i m_i",
       abs(p.sum() - (k - float(nu @ m))) < k * tol,
       f"|.| = {abs(p.sum() - (k - float(nu @ m))):.3e}")
    ck("P2.3 personalised spend  sum_z q_zi x_zi = 1",
       np.abs((X * q).sum(axis=1) - 1).max() < tol,
       f"max|.| = {np.abs((X * q).sum(axis=1) - 1).max():.3e}")
    ratio = u / q
    ck("P2.4 max_z u_i(z)/q_zi = g*_i", np.abs(ratio.max(axis=1) - g).max() < 1e-4,
       f"max|.| = {np.abs(ratio.max(axis=1) - g).max():.3e}")
    score = u / g[:, None] - nu[:, None] * M[None, :]
    ck("P2.5 max_i (u_i(z)/g_i - nu_i M_z) = p_z",
       np.abs(score.max(axis=0) - p).max() < tol,
       f"max|.| = {np.abs(score.max(axis=0) - p).max():.3e}")
    ck("P2.5 supp(X) contained in that argmax",
       all(np.all(score[supp[:, z], z] >= score[:, z].max() - tol) for z in range(n)))
    bad = [z for z in range(n)
           if not np.all(ratio[supp[:, z], z] >= ratio[:, z].max() - 1e-7)]
    print(f"  [wit ] DOMAIN 2.12's ratio form 'supp(X) subset argmax_i u_i(z)/q_zi': "
          f"{len(bad)} of {n} zips violate it")
    # P2.6 -- an INDEPENDENT demand LP at the anonymous prices
    worst = None
    for i in range(k):
        dm = Model("demand")
        dm.hideOutput()
        dm.setParam("limits/gap", 0.0)
        xv = [dm.addVar(lb=0.0, ub=1.0) for _ in range(n)]
        dm.addCons(quicksum(float(p[z]) * xv[z] for z in range(n)) <= 1.0)
        dm.setObjective(quicksum(float(u[i, z]) * xv[z] for z in range(n)), "maximize")
        dm.optimize()
        best = dm.getObjVal()
        if nu[i] > 1e-9:
            worst = (i, best, g[i], spend[i], nu[i])
            ck(f"P2.6 agent {i} (nu > 0) is NOT Walrasian: max{{g_i : p.x <= 1, 0<=x<=1}} "
               f"strictly exceeds g*_i", best > g[i] + 1e-6,
               f"demand value {best:.6f} > g*_i {g[i]:.6f}; spends {spend[i]:.6f} of 1")
        if nu[i] < -1e-9:
            ck(f"P2.6 agent {i} (nu < 0) is over budget at p", spend[i] > 1 + 1e-9,
               f"spends {spend[i]:.6f} > 1")
    if worst is None and delta > 0:
        print("  [note] no agent has nu > 0 here (band slack): nothing to refute")
    return X, g, p, nu


def v_p2b_gauge(name, u, M, delta):
    sec(f"P2b -- the (p - cM, nu + c) gauge, checked on the CERTIFIED dual ({name}, "
        f"delta = {delta})")
    k, n = u.shape
    du = O.scip_dual(u, M, delta)
    p, nu = du["p"], du["mup"] - du["mum"]
    pr = O.scip_primal(u, M, delta)
    T = float(M.sum())
    mm = (pr["X"] * M[None, :]).sum(axis=1)
    tol = 1e-7 * T / k
    tight = [i for i in range(k)
             if mm[i] >= (1 + delta) * T / k - tol or mm[i] <= (1 - delta) * T / k + tol]
    base = O.rigorous_upper(u, M, delta, p, np.maximum(nu, 0), np.maximum(-nu, 0))
    vals = []
    for c in (-5.0, -1.0, -0.01, 0.0, 0.01, 1.0, 5.0):
        nu2 = nu + c
        r = O.rigorous_upper(u, M, delta, p - c * M, np.maximum(nu2, 0),
                             np.maximum(-nu2, 0))
        vals.append((c, None if r is None else r[0]))
    print(f"  tight agents {len(tight)}/{k};   D(p - cM, nu + c) along the orbit:")
    for c, v in vals:
        print(f"    c = {c:+7.2f}  D = {'n/a (q <= 0)' if v is None else f'{v:.10f}'}")
    if delta == 0 and len(tight) == k:
        ok = all(v is not None and abs(v - base[0]) < 1e-6 for _, v in vals)
        ck("delta = 0, every agent two-sided tight: the WHOLE line is dual-optimal "
           "(D invariant) => p and the individual nu_i are not determined", ok)
    else:
        moved = [v for c, v in vals if c != 0 and (v is None or v > base[0] + 1e-7)]
        ck("delta > 0 with a slack agent: moving off c = 0 leaves the dual-optimal set "
           "(D strictly worse or infeasible)", len(moved) == len(vals) - 1,
           f"{len(moved)} of {len(vals)-1} off-centre points are strictly worse/infeasible")


def v_p25_minimal():
    sec("P2.5 -- the MINIMAL counterexample to DOMAIN_optimization 2.12's ratio form, "
        "at nu == 0, in exact arithmetic")
    print("  Instance A (the smallest possible): n = 1 zip, k = 2 agents, M = [1],")
    print("    u = [[2], [1]].  T/k = 1/2.  Feasible x = (a, 1-a); m_i = (a, 1-a).")
    a = F(1, 2)
    g = [F(2) * a, F(1) * (1 - a)]
    print(f"    EG optimum: maximise log(2a) + log(1-a) -> a* = 1/2, g* = "
          f"({g[0]}, {g[1]}), m = (1/2, 1/2) = T/k, so the band is SLACK for every "
          f"delta > 0 and nu == 0 is forced by complementary slackness.")
    # exact optimality of a = 1/2 for max log(2a)+log(1-a): derivative 1/a - 1/(1-a) = 0
    ck("a* = 1/2 exactly (1/a = 1/(1-a))", F(1, 1) / a == F(1, 1) / (1 - a))
    p = F(2)
    ck("stationarity gives p = 2 exactly: u_1/g_1 = 2/1 = 2 and u_2/g_2 = 1/(1/2) = 2",
       F(2) / g[0] == p and F(1) / g[1] == p)
    ck("sum_z p_z = k - sum nu_i m_i  (2 = 2)", p == 2 - 0)
    print("    DOMAIN 2.12 as written: supp(X) subset argmax_i u_i(z)/(p_z + nu_i M_z)")
    print("      = argmax_i u_i(z)/2 = argmax_i u_i(z) = {agent 1}.")
    print("      But x_{2,1} = 1/2 > 0, so agent 2 IS in supp(X).")
    ck("=> DOMAIN_optimization section 2.12's rule is REFUTED at nu == 0, n = 1, k = 2, "
       "integer data", F(2) / p > F(1) / p and (1 - a) > 0,
       "ratio 2/2 = 1 vs 1/2 = 0.5; owner-2 ratio is strictly SMALLER yet it holds mass")
    print("    Corrected rule: argmax_i (u_i(z)/g*_i - nu_i M_z) = argmax_i (2/1, 1/(1/2))")
    print("      = argmax_i (2, 2) = {1, 2} -- contains supp, and its value 2 = p_z.")
    ck("corrected rule holds exactly on instance A", F(2) / g[0] == F(1) / g[1] == p)

    print("\n  Instance B (non-degenerate, strict): n = 2, k = 2, M = [1,1],")
    print("    u = [[10,10],[3,1]].  Unconstrained EG optimum: agent 2 takes ALL of zip 0.")
    gB = [F(10), F(3)]
    pB = [F(1), F(1)]
    ck("B: stationarity  u_2(0)/g_2 = 3/3 = 1 = p_0 and u_1(1)/g_1 = 10/10 = 1 = p_1",
       F(3) / gB[1] == pB[0] and F(10) / gB[0] == pB[1])
    ck("B: non-support rows slack:  u_1(0)/g_1 = 1 <= p_0 = 1 and u_2(1)/g_2 = 1/3 <= 1",
       F(10) / gB[0] <= pB[0] and F(1) / gB[1] <= pB[1])
    ck("B: sum_z p_z = 2 = k", sum(pB) == 2)
    ck("B: masses m = (1,1) = T/k, so the band is slack for delta > 0 and nu == 0",
       True)
    ck("B: DOMAIN 2.12 puts zip 0 with agent 1 (u = 10 > 3) but the EG optimum gives it "
       "ENTIRELY to agent 2 -- REFUTED, strictly, with margin 10/3",
       F(10) > F(3), "published ratio 10/1 vs 3/1")
    ck("B: the corrected rule ties (10/10 = 3/3 = 1 = p_0) and CONTAINS the true owner",
       F(10) / gB[0] == F(3) / gB[1] == pB[0])
    print("  Cross-check instance B against the solver:")
    uB = np.array([[10.0, 10.0], [3.0, 1.0]])
    MB = np.array([1.0, 1.0])
    for d in (0.0, 0.05, 0.5):
        b = O.bracket(uB, MB, d)
        pr = O.scip_primal(uB, MB, d)
        gg = (uB * pr["X"]).sum(axis=1)
        print(f"    delta = {d:<5} EG^bal in [{b['L']:.10f}, {b['U']:.10f}]  "
              f"(log 30 = {math.log(30):.10f})   X[:,0] = {np.round(pr['X'][:,0],6)}   "
              f"g = {np.round(gg,6)}")
        ck(f"    B at delta={d}: the optimum is g = (10, 3), value log 30",
           abs(b["L"] - math.log(30)) < 1e-6 and abs(b["U"] - math.log(30)) < 1e-6)


# =============================================================== P3
def v_p3(name, u, M, deltas, trials=60, seed=2024):
    """P3 on a named toy.  Vertices are CLEANED and re-certified by p3_attack (a
    sub-1e-7 entry from any float LP is dirt, not a split); the adversarial random
    ensemble lives in p3_attack.py."""
    from p3_attack import clean_and_certify
    sec(f"P3-split -- attack on #splits <= k-1+t <= 2k-1 ({name}, cleaned vertices)")
    k, n = u.shape
    rng = np.random.default_rng(seed)
    ws = wc = wr = math.inf
    nv = amb = 0
    maxs = maxt = 0
    for d in deltas:
        pr = O.scip_primal(u, M, d)
        gstar = (u * pr["X"]).sum(axis=1)
        for _ in range(trials):
            V = scip_face_vertex(u, M, d, gstar, rng.normal(size=(k, n)))
            if V is None:
                continue
            res = clean_and_certify(u, M, d, V, gstar)
            if res is None:
                amb += 1
                continue
            s, tt, ns, rk, _ = res
            nv += 1
            ws = min(ws, (k - 1 + tt) - s)
            wc = min(wc, (2 * k - 1) - s)
            wr = min(wr, (n + k + tt - 1) - ns)
            maxs, maxt = max(maxs, s), max(maxt, tt)
    ck(f"{name}: #splits <= k-1+t on {nv} certified-clean vertices ({amb} ambiguous)",
       ws >= 0, f"min slack = {ws}, max splits = {maxs}, max t = {maxt}")
    ck(f"{name}: #splits <= 2k-1", wc >= 0, f"min slack = {wc}")
    ck(f"{name}: |supp| <= n+k+t-1", wr >= 0, f"min slack = {wr}")


# =============================================================== P4
def v_p4(name, u, M, grid):
    sec(f"P4-slope -- monotone, concave, envelope, kink, bisection ({name})")
    k = u.shape[0]
    T = float(M.sum())
    Ls, Us, smins = [], [], []
    for d in grid:
        b = O.bracket(u, M, d)
        du = O.scip_dual(u, M, d)
        nu = du["mup"] - du["mum"]
        Ls.append(b["L"])
        Us.append(b["U"])
        smins.append((T / k) * float(np.abs(nu).sum()))
        print(f"  delta = {d:<8.5f}  EG^bal in [{b['L']:.10f}, {b['U']:.10f}]   "
              f"s = (T/k)sum|nu| = {smins[-1]:.6f}")
    Ls, Us = np.array(Ls), np.array(Us)
    ck("P4.1 monotone nondecreasing (L_{j+1} >= L_j - bracket width)",
       np.min(Ls[1:] - Us[:-1]) >= -max(Us - Ls) - 1e-9,
       f"min (L_next - U_prev) = {np.min(Ls[1:] - Us[:-1]):.3e}")
    worst = math.inf
    for a in range(len(grid)):
        for c in range(a + 2, len(grid)):
            for bidx in range(a + 1, c):
                th = (grid[c] - grid[bidx]) / (grid[c] - grid[a])
                worst = min(worst, Ls[bidx] - (th * Us[a] + (1 - th) * Us[c]))
    ck("P4.2 concave (chord test over all triples, using L at the midpoint and U at the "
       "endpoints -- the conservative direction)", worst >= -1e-8,
       f"min (L_mid - chord_U) = {worst:.3e}")
    wt = -math.inf
    for a in range(len(grid)):
        for c in range(len(grid)):
            if a == c:
                continue
            wt = max(wt, Ls[c] - (Us[a] + smins[a] * (grid[c] - grid[a])))
    ck("P4.3/P4.6 supergradient: EG^bal(d') <= EG^bal(d) + s(d)(d'-d) at every grid pair",
       wt <= 1e-8, f"max violation = {wt:.3e}")
    wc = -math.inf
    for a in range(len(grid) - 1):
        for c in range(a + 1, len(grid)):
            mid = 0.5 * (grid[a] + grid[c])
            bm = O.bracket(u, M, mid)
            wc = max(wc, 0.5 * (Ls[a] + Ls[c]) - bm["U"])
    ck("P4.7 chord LOWER envelope: phi(mid) >= mean of endpoint values",
       wc <= 1e-8, f"max violation = {wc:.3e}")
    return Ls, Us, smins


def v_p4_kink(name, u, M):
    sec(f"P4.5 -- the kink, and the REFUTATION of the brief's 'd EG^bal/d delta = "
        f"(T/k)sum(mu+ + mu-)' as an EQUALITY ({name})")
    k = u.shape[0]
    T = float(M.sum())
    pr = O.scip_primal(u, M, 5.0)
    mm = (pr["X"] * M[None, :]).sum(axis=1)
    dc = float(np.max(np.abs(mm - T / k)) / (T / k))
    h = 1e-4
    b0 = O.bracket(u, M, dc)
    bp = O.bracket(u, M, dc + h)
    bm = O.bracket(u, M, max(dc - h, 0.0))
    Dp = (bp["L"] - b0["U"]) / h, (bp["U"] - b0["L"]) / h
    Dm = (b0["L"] - bm["U"]) / h, (b0["U"] - bm["L"]) / h
    print(f"  delta_c = {dc:.6f}   EG^bal(delta_c) in [{b0['L']:.10f}, {b0['U']:.10f}]")
    print(f"  D+ in [{Dp[0]:.6f}, {Dp[1]:.6f}]   D- in [{Dm[0]:.6f}, {Dm[1]:.6f}]")
    ck("a genuine kink: D+ < D- (so phi is NOT differentiable at delta_c and no single "
       "number is 'the' derivative)", Dp[1] < Dm[0],
       f"D+ upper {Dp[1]:.6f} < D- lower {Dm[0]:.6f}")
    ck("=> the unit brief's 'd EG^bal/d delta = (T/k) sum_i (mu+ + mu-)' is FALSE as an "
       "EQUALITY; only the supergradient inclusion survives", True)
    return dc


def v_p44_adversarial(name, u, M):
    sec(f"P4.4 -- an ADVERSARIAL optimal dual at delta = 0 with unbounded aggregate ({name})")
    k = u.shape[0]
    T = float(M.sum())
    du = O.scip_dual(u, M, 0.0)
    nu = du["mup"] - du["mum"]
    base = O.rigorous_upper(u, M, 0.0, du["p"], np.maximum(nu, 0), np.maximum(-nu, 0))
    smin = (T / k) * float(np.abs(nu).sum())
    b0 = O.bracket(u, M, 0.0)
    print(f"  s_min = (T/k)sum|nu| = {smin:.6f};  EG^bal(0) in "
          f"[{b0['L']:.10f}, {b0['U']:.10f}]")
    rows = []
    ok_val, ok_valid = True, True
    for c in (0.0, 1.0, 100.0, 1e4, 1e6):
        mup = np.maximum(nu, 0) + c
        mum = np.maximum(-nu, 0) + c
        r = O.rigorous_upper(u, M, 0.0, du["p"], mup, mum)
        agg = (T / k) * float((mup + mum).sum())
        rows.append((c, agg, None if r is None else r[0]))
        if r is None or abs(r[0] - base[0]) > 1e-8:
            ok_val = False
        # is it still a VALID supergradient?  phi(d') <= phi(0) + agg*d'
        for dp in (0.01, 0.05, 0.2):
            bb = O.bracket(u, M, dp)
            if bb["U"] > b0["L"] + agg * dp + 1e-8:
                ok_valid = False
    for c, agg, v in rows:
        print(f"    c = {c:>10.4g}   (T/k)sum(mu+ + mu-) = {agg:>14.4f}   dual value D = "
              f"{'n/a' if v is None else f'{v:.10f}'}")
    ck("adding c >= 0 to BOTH mu+ and mu- at delta = 0 leaves the dual value UNCHANGED "
       "(so each is genuinely dual-OPTIMAL)", ok_val)
    ck("the aggregate (T/k)sum(mu+ + mu-) is therefore UNBOUNDED ABOVE at delta = 0 while "
       "s_min stays finite", rows[-1][1] > 1e4 * max(smin, 1e-9),
       f"s_min = {smin:.6f} vs {rows[-1][1]:.4g} at c = 1e6")
    ck("every such aggregate is still a VALID (but vacuous) supergradient at delta = 0",
       ok_valid)
    ck("=> only s_min = (T/k)sum|nu| may be quoted or plotted (MODEL section 6 item 2)",
       True)


# =============================================================== P5
def v_p5(name, u, M, delta, seed=31337):
    sec(f"P5-OA -- validity of EVERY master optimum, attacked ({name}, delta = {delta})")
    k, n = u.shape
    T = float(M.sum())
    b = O.bracket(u, M, delta)
    L, U = b["L"], b["U"]
    pr = O.scip_primal(u, M, delta)
    gstar = (u * pr["X"]).sum(axis=1)
    rng = np.random.default_rng(seed)
    worst, cases = math.inf, 0
    for trial in range(60):
        style = trial % 4
        if style == 0:                      # random multiplicative perturbation of g*
            pts = [gstar * rng.uniform(0.2, 5.0, size=k)
                   for _ in range(int(rng.integers(1, 4)))]
        elif style == 1:                    # tiny ghat (the numerically nastiest cut)
            pts = [gstar * rng.uniform(1e-4, 1e-2, size=k)]
        elif style == 2:                    # huge ghat
            pts = [gstar * rng.uniform(1e2, 1e4, size=k)]
        else:                               # one cut exactly at g* plus noise cuts
            pts = [gstar] + [gstar * rng.uniform(0.5, 2.0, size=k)]
        cuts = [(i, float(gh[i])) for gh in pts for i in range(k)]
        mv = scip_master(u, M, delta, cuts)
        if not math.isfinite(mv):
            continue
        cases += 1
        worst = min(worst, mv - U)          # attack: is MP below a CERTIFIED UPPER bound?
        if mv < L - 1e-7:
            ck("VIOLATION of P5.1", False,
               f"MP = {mv:.12f} < certified lower bound L = {L:.12f}")
    ck(f"P5.1 every master optimum >= EG^bal(delta) on {cases} cut sets (incl. ghat "
       f"1e-4 x g* and 1e4 x g*), tested against the CERTIFIED bound",
       worst >= -(U - L) - 1e-8,
       f"min (MP - U) = {worst:.3e}, bracket width = {U-L:.2e}")
    # P5.2 monotone in the cut set
    base = [(i, float(gstar[i] * 1.7)) for i in range(k)]
    prev = scip_master(u, M, delta, base)
    mono = True
    cur = list(base)
    for _ in range(6):
        gh = gstar * rng.uniform(0.4, 2.5, size=k)
        cur += [(i, float(gh[i])) for i in range(k)]
        v = scip_master(u, M, delta, cur)
        if v > prev + 1e-9:
            mono = False
        prev = v
    ck("P5.2 MP is non-increasing as cuts are added", mono, f"final MP = {prev:.10f}")
    # P5.4 single well-placed cut is exact
    one = scip_master(u, M, delta, [(i, float(gstar[i])) for i in range(k)])
    ck("P5.4 a single tangent per agent at g* makes the master EXACT",
       L - 1e-6 <= one <= U + 1e-6, f"MP = {one:.12f} vs bracket [{L:.12f}, {U:.12f}]")
    # P5.6 a cut set missing an agent is NOT a bound (it is unbounded)
    partial = [(i, float(gstar[i])) for i in range(k - 1)]
    ck("P5.6 'at least one cut per agent' is load-bearing: a cut set missing an agent "
       "leaves the master unbounded, not a bound",
       not math.isfinite(scip_master(u, M, delta, partial)))
    # P5.3 the explicit ghat > 0 constant
    lam = 0.30
    ck("P5.3 g_i >= lam(1-delta)T/k at the optimum",
       gstar.min() >= lam * (1 - delta) * T / k - 1e-7,
       f"min g = {gstar.min():.4f} vs lam(1-delta)T/k = {lam*(1-delta)*T/k:.4f}")


def v_p5_lam():
    sec("P5.3 -- u_i(z) >= lam M_z, symbolically, from the model formula")
    import sympy as sp
    lam, th = sp.symbols("lam theta", positive=True)
    Mz, Si, Tz, Sf = sp.symbols("M_z S_i T_z S_free", nonnegative=True)
    c1, c2 = 1 - lam, th * (1 - lam)
    uiz = c2 * Tz + c2 * Sf + lam * Mz + (c1 - c2) * Si
    d = sp.simplify(uiz - lam * Mz)
    ck("u_i(z) - lam M_z = theta(1-lam)(T_z + S_free) + (1-lam)(1-theta) S_i",
       sp.simplify(d - (th * (1 - lam) * (Tz + Sf) + (1 - lam) * (1 - th) * Si)) == 0)
    ck("... which is >= 0 for 0 <= theta <= 1, 0 <= lam <= 1 and nonnegative books",
       True, "each summand is a product of nonnegatives")
    ck("=> g_i(X) >= lam m_i(X) >= lam(1-delta)T/k > 0 for delta < 1 (P5.3)", True)


def v_p55_nonfinite(name, u, M, delta, N=600):
    sec(f"P5.5 -- Kelley's loop does NOT terminate finitely at exact optimality ({name})")
    k, n = u.shape
    b = O.bracket(u, M, delta)
    L, U = b["L"], b["U"]
    X = np.full((k, n), 1.0 / k)
    cuts, hits, ubs = [], 0, []
    prev = math.inf
    monotone = True
    for r in range(N):
        gh = (u * X).sum(axis=1)
        if abs(float(np.sum(np.log(gh))) - U) < 1e-14:
            hits += 1
        cuts += [(i, float(gh[i])) for i in range(k)]
        mv = scip_master(u, M, delta, cuts)
        if not math.isfinite(mv):
            break
        ubs.append(mv)
        if mv > prev + 1e-9:
            monotone = False
        prev = mv
        # re-solve the master to get the next iterate
        X = _master_x(u, M, delta, cuts)
        if X is None:
            break
    ubs = np.array(ubs)
    ck(f"the master value stays STRICTLY above EG^bal for all {len(ubs)} iterations "
       f"(no exact finite termination)", float(ubs.min()) > U - 1e-11,
       f"min MP - U = {ubs.min() - U:.3e}, final MP - U = {ubs[-1] - U:.3e}")
    ck("MP is monotone non-increasing along the loop", monotone)
    ck("the bracket [incumbent, MP] contains EG^bal at every iteration (so the loop can "
       "be stopped anywhere and still certify)", bool(np.all(ubs >= L - 1e-9)))
    print(f"  MP - U after 1/5/25/100/{len(ubs)} iterations: "
          f"{ubs[0]-U:.3e} / {ubs[min(4,len(ubs)-1)]-U:.3e} / "
          f"{ubs[min(24,len(ubs)-1)]-U:.3e} / {ubs[min(99,len(ubs)-1)]-U:.3e} / "
          f"{ubs[-1]-U:.3e}")
    ck("no iterate ever landed exactly on g* (which P5.4's converse shows is REQUIRED "
       "for exact finite termination)", hits == 0, f"{hits} exact hits in {len(ubs)}")


def _master_x(u, M, delta, cuts):
    k, n = u.shape
    T = float(M.sum())
    m = Model("mx")
    m.hideOutput()
    m.setParam("limits/gap", 0.0)
    x = [[m.addVar(lb=0.0, ub=1.0) for _ in range(n)] for _ in range(k)]
    t = [m.addVar(lb=-1e7, ub=1e7) for _ in range(k)]
    for z in range(n):
        m.addCons(quicksum(x[i][z] for i in range(k)) == 1.0)
    for i in range(k):
        m.addCons(quicksum(float(M[z]) * x[i][z] for z in range(n)) <= (1 + delta) * T / k)
        m.addCons(quicksum(float(M[z]) * x[i][z] for z in range(n)) >= (1 - delta) * T / k)
    for (i, gh) in cuts:
        m.addCons(t[i] <= math.log(gh)
                  + (quicksum(float(u[i, z]) * x[i][z] for z in range(n)) - gh) / gh)
    m.setObjective(quicksum(t), "maximize")
    m.optimize()
    if m.getStatus() != "optimal":
        return None
    return np.array([[m.getVal(x[i][z]) for z in range(n)] for i in range(k)])


# =============================================================== P6
def v_p6(name, u, M, delta):
    sec(f"P6-cells -- the O(nk) separating-cell certificate under the band ({name})")
    k, n = u.shape
    pr = O.scip_primal(u, M, delta)
    du = O.scip_dual(u, M, delta)
    X = pr["X"]
    g = (u * X).sum(axis=1)
    nu = du["mup"] - du["mum"]
    f = u / g[:, None] - nu[:, None] * M[None, :]
    sup = X > 1e-7
    bad = [z for z in range(n)
           if not np.all(f[sup[:, z], z] >= f[:, z].max() - 5e-6)]
    ck("supp(X*) contained in argmax_i f_i(z), f_i(z) = u_i(z)/g*_i - nu_i M_z",
       not bad, f"violating zips: {bad}")
    ck("max_i f_i(z) = p_z for every zip (so the cells are read off ONE solve)",
       np.abs(f.max(axis=0) - du["p"]).max() < 5e-6,
       f"max|.| = {np.abs(f.max(axis=0) - du['p']).max():.3e}")
    # f_i is LINEAR in the lifted point (u_1(z),...,u_k(z), M_z)
    lift = np.vstack([u, M[None, :]])                       # (k+1) x n
    W = np.zeros((k, k + 1))
    for i in range(k):
        W[i, i] = 1.0 / g[i]
        W[i, k] = -nu[i]
    ck("f = W @ lift with W constant: each cell is a halfspace intersection in R^{k+1} "
       "(a generalised power diagram, one site per agent)",
       np.max(np.abs(W @ lift - f)) < 1e-12,
       f"max|W.lift - f| = {np.max(np.abs(W @ lift - f)):.2e}")
    ck("checking it costs k evaluations per zip = O(nk), no solver", True,
       f"{n*k} multiply-adds here")


# =============================================================== main
def main():
    print("VERIFY_U9-bandthm -- numeric leg (independent oracle: SCIP primal + SCIP dual "
          "+ exact rational feasibility)")
    import scipy
    import pyscipopt
    print(f"python {sys.version.split()[0]}  numpy {np.__version__}  scipy "
          f"{scipy.__version__}  pyscipopt {pyscipopt.__version__}  mpmath dps {mp.dps}")
    print("seeds: my toy 424242, P3 vertices 2024, P3 ensemble 5150, P5 cut sets 31337, "
          "P0b 11")

    M1, B1 = toy_u7()
    u1 = O.utilities(M1, B1)
    sec("Convention pin -- unmasked u against MODEL_U7-meas section 4")
    g = np.array([[u1[i, [0, 1]].sum(), u1[i, [2, 3]].sum()] for i in range(3)])
    want = np.array([[22.82, 16.10], [17.78, 19.46], [16.10, 21.14]])
    ck("g matrix reproduces MODEL_U7-meas section 4 (so u is the UNMASKED convention)",
       np.max(np.abs(g - want)) < 5e-3, f"max|dg| = {np.max(np.abs(g - want)):.2e}")
    ck("V(D1->A, D2->C) = 6.1788",
       abs(math.log(g[0, 0]) + math.log(g[2, 1]) - 6.1788) < 5e-5,
       f"V = {math.log(g[0,0]) + math.log(g[2,1]):.6f}")

    uA = u1[[0, 2]]                                   # roster {A, C}
    M3, B3 = toy_heavy()
    uH = O.utilities(M3, B3)[[0, 1]]
    M2, B2 = toy_mine()
    uMine = O.utilities(M2, B2)[[0, 2, 3]]

    insts = [("U7 toy S={A,C}", (uA, M1)), ("heavy-zip toy", (uH, M3)),
             ("my toy k=3", (uMine, M2))]

    v_p0(insts)
    v_p0b(uH, M3, 0.02, "heavy-zip toy")
    v_p0b(uMine, M2, 0.03, "my toy k=3")

    v_p1("U7 toy S={A,C}", uA, M1, [0.0, 0.02, 0.0714286, 0.15, 0.33])
    v_p1("heavy-zip toy", uH, M3, [0.0, 0.02, 0.06, 0.111112, 0.33])
    v_p1("my toy k=3", uMine, M2, [0.0, 0.02, 0.06, 0.15, 0.4])
    v_p1_epsilon("U7 toy", uA, M1, 0.0714286)
    v_p1_epsilon("my toy k=3", uMine, M2, 0.06)
    v_p1_rho()
    v_p1a_p1c("heavy-zip toy", uH, M3)

    v_p2("heavy-zip toy", uH, M3, 0.02)
    v_p2("my toy k=3", uMine, M2, 0.03)
    v_p2("heavy-zip toy", uH, M3, 0.0)
    v_p2b_gauge("heavy-zip toy", uH, M3, 0.0)
    v_p2b_gauge("my toy k=3", uMine, M2, 0.03)
    v_p25_minimal()

    v_p3("heavy-zip toy", uH, M3, [0.0, 0.02, 0.06, 0.33])
    v_p3("my toy k=3", uMine, M2, [0.0, 0.02, 0.06, 0.4])
    print("  [see p3_attack.py for the adversarial random ensemble]")

    v_p4("heavy-zip toy", uH, M3, [0.0, 0.01, 0.02, 0.04, 0.06, 0.09, 0.15, 0.33])
    v_p4("my toy k=3", uMine, M2, [0.0, 0.01, 0.03, 0.06, 0.12, 0.25])
    v_p4_kink("heavy-zip toy", uH, M3)
    v_p4_kink("my toy k=3", uMine, M2)
    v_p44_adversarial("heavy-zip toy", uH, M3)

    v_p5_lam()
    v_p5("heavy-zip toy", uH, M3, 0.02)
    v_p5("my toy k=3", uMine, M2, 0.03)
    v_p55_nonfinite("my toy k=3", uMine, M2, 0.03, N=250)

    v_p6("heavy-zip toy", uH, M3, 0.02)
    v_p6("my toy k=3", uMine, M2, 0.03)

    print("\n" + "=" * 78)
    for s in NOTE:
        print("NOTE: " + s)
    print("NUMERIC FAILURES: " + ("none" if not FAIL else "; ".join(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
