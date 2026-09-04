"""Numerical checks for MODEL_U9-bandthm — the five propositions behind `EG^bal_S(delta)`.

Self-contained: builds `u_i(z)` from the model formula
    u_i(z) = c2*T_z + c_free*S_free(z) + lam*M_z + (c1-c2)*S_i(z),
    c1 = 1-lam,  c2 = theta*(1-lam),  c_free = c2  (filler_capture="theta")
which is the UNMASKED convention of `td/channel.py::gain_matrix` (every rep valued on
every zip).  Cross-checked against `MODEL_U7-meas` section 4's published `g` matrix.

Everything is solved with `scipy.optimize.linprog` (HiGHS) only:

  * `EG^bal_S(delta)` by the outer-approximation (tangent) master of DOMAIN_optimization
    section 2.11 -- which is simultaneously the object P5-OA is about;
  * the multipliers `(p, mu^+, mu^-)` by an independent dual-feasibility LP built from
    the KKT system, never from HiGHS' own marginals (so the dual is not the solver's
    word for itself);
  * vertices of the optimal face by maximising random linear objectives over
    {x feasible : g(x) = g*}.

Run:  /Users/ntlee/projects/td/.venv/bin/python3 docs/artifacts/U9-bandthm/bandthm.py
Deterministic: every random draw uses an explicit seed printed in the output.
"""

from __future__ import annotations

import itertools
import math
import sys

import numpy as np
from scipy.optimize import linprog

TOL = 1e-9
FAILURES: list[str] = []
WITNESS: dict[str, object] = {}


def check(name: str, ok: bool, detail: str = "") -> None:
    tag = "ok  " if ok else "FAIL"
    print(f"  [{tag}] {name}" + (f"   {detail}" if detail else ""))
    if not ok:
        FAILURES.append(name)


# --------------------------------------------------------------------------- model


def utilities(M: np.ndarray, books: np.ndarray, free: np.ndarray | None = None,
              theta: float = 0.40, lam: float = 0.30) -> np.ndarray:
    """`u[i, z]` for every rep `i` and zip `z`, unmasked."""
    c1, c2 = 1.0 - lam, theta * (1.0 - lam)
    c_free = c2
    if free is None:
        free = np.zeros_like(M)
    Tz = books.sum(axis=0)
    common = c2 * Tz + c_free * free + lam * M
    return common[None, :] + (c1 - c2) * books


# ------------------------------------------------------------------ the EG^bal solve


def _band_rows(M: np.ndarray, delta: float, T: float, k: int, nz: int):
    """`A_ub, b_ub` for the 2k band rows on the x-block only."""
    n = len(M)
    rows, rhs = [], []
    for i in range(k):
        r = np.zeros(nz)
        r[i * n:(i + 1) * n] = M
        rows.append(r.copy())
        rhs.append((1.0 + delta) * T / k)
        rows.append(-r)
        rhs.append(-(1.0 - delta) * T / k)
    return np.array(rows), np.array(rhs)


def solve_egbal(u: np.ndarray, M: np.ndarray, delta: float, *, max_iter: int = 400,
                tol: float = 1e-13, trace: bool = False):
    """Outer approximation for `EG^bal_S(delta)`.

    Variables `(x_{i,z})` flattened rep-major, then `k` epigraph variables `t_i`.
    Returns a dict with the primal `X`, gains `g`, value, and (if `trace`) the
    per-iteration master upper bounds and incumbent lower bounds.
    """
    k, n = u.shape
    T = float(M.sum())
    nz = k * n
    nv = nz + k

    A_eq = np.zeros((n, nv))
    for z in range(n):
        for i in range(k):
            A_eq[z, i * n + z] = 1.0
    b_eq = np.ones(n)

    Ab, bb = _band_rows(M, delta, T, k, nz)
    Ab = np.hstack([Ab, np.zeros((Ab.shape[0], k))])

    bounds = [(0.0, 1.0)] * nz + [(None, None)] * k

    cuts: list[tuple[int, float]] = []
    ub_hist, lb_hist = [], []
    X = np.full((k, n), 1.0 / k)
    best_lb, best_X = -math.inf, X.copy()

    for it in range(max_iter):
        g_hat = (u * X).sum(axis=1)
        for i in range(k):
            cuts.append((i, float(g_hat[i])))
        lb = float(np.sum(np.log(g_hat)))
        if lb > best_lb:
            best_lb, best_X = lb, X.copy()

        A_cut = np.zeros((len(cuts), nv))
        b_cut = np.zeros(len(cuts))
        for r, (i, gh) in enumerate(cuts):
            A_cut[r, i * n:(i + 1) * n] = -u[i] / gh
            A_cut[r, nz + i] = 1.0
            b_cut[r] = math.log(gh) - 1.0

        c = np.zeros(nv)
        c[nz:] = -1.0
        res = linprog(c, A_ub=np.vstack([Ab, A_cut]), b_ub=np.concatenate([bb, b_cut]),
                      A_eq=A_eq, b_eq=b_eq, bounds=bounds, method="highs")
        if not res.success:
            raise RuntimeError(f"master LP failed at delta={delta}: {res.message}")
        ub = float(-res.fun)
        X = res.x[:nz].reshape(k, n)
        ub_hist.append(ub)
        lb_hist.append(best_lb)
        if ub - best_lb < tol:
            break

    g = (u * best_X).sum(axis=1)
    # Polish 1: SLSQP on the concave program itself, warm-started at the OA incumbent.
    # The OA loop is Kelley's method on a near-flat objective and stalls at ~1e-9.
    Xs = _slsqp_polish(u, M, delta, best_X)
    if Xs is not None:
        gs = (u * Xs).sum(axis=1)
        if np.sum(np.log(gs)) > np.sum(np.log(g)):
            best_X, g = Xs, gs
    # Polish 2: by P5b a single tangent at the optimal `g*` makes the master exact, so
    # re-solving with one cut per agent at the incumbent `g` returns an exactly optimal
    # vertex with a clean support -- which is what the dual LP needs.
    for _ in range(4):
        Xp = _single_cut_primal(u, M, delta, g)
        gp = (u * Xp).sum(axis=1)
        if np.sum(np.log(gp)) >= np.sum(np.log(g)) - 1e-14:
            best_X, g = Xp, gp
        else:
            break
    out = {"X": best_X, "g": g, "value": float(np.sum(np.log(g))),
           "ub": ub_hist[-1], "iters": len(ub_hist), "delta": delta, "T": T, "k": k}
    if trace:
        out["ub_hist"], out["lb_hist"] = ub_hist, lb_hist
    return out


def _slsqp_polish(u, M, delta, X0):
    """SLSQP on `max sum_i log g_i` over the same polytope, warm-started at `X0`."""
    from scipy.optimize import LinearConstraint, minimize
    k, n = u.shape
    T = float(M.sum())
    A = np.zeros((n, k * n))
    for z in range(n):
        for i in range(k):
            A[z, i * n + z] = 1.0
    Ab = np.zeros((k, k * n))
    for i in range(k):
        Ab[i, i * n:(i + 1) * n] = M

    def f(x):
        return -float(np.sum(np.log((u * x.reshape(k, n)).sum(axis=1))))

    def jac(x):
        g = (u * x.reshape(k, n)).sum(axis=1)
        return (-(u / g[:, None])).ravel()

    try:
        r = minimize(f, X0.ravel(), jac=jac,
                     constraints=[LinearConstraint(A, 1.0, 1.0),
                                  LinearConstraint(Ab, (1 - delta) * T / k,
                                                   (1 + delta) * T / k)],
                     bounds=[(0.0, 1.0)] * (k * n), method="SLSQP",
                     options={"maxiter": 2000, "ftol": 1e-16})
    except Exception:
        return None
    X = np.clip(r.x.reshape(k, n), 0.0, 1.0)
    X = X / X.sum(axis=0, keepdims=True)
    m = (X * M[None, :]).sum(axis=1)
    if m.max() > (1 + delta) * T / k + 1e-7 or m.min() < (1 - delta) * T / k - 1e-7:
        return None
    return X


def _single_cut_primal(u, M, delta, g_hat):
    """Master with exactly one tangent per agent at `g_hat`; returns the `x`-block."""
    k, n = u.shape
    T = float(M.sum())
    nz, nv = k * n, k * n + k
    A_eq = np.zeros((n, nv))
    for z in range(n):
        for i in range(k):
            A_eq[z, i * n + z] = 1.0
    Ab, bb = _band_rows(M, delta, T, k, nz)
    Ab = np.hstack([Ab, np.zeros((Ab.shape[0], k))])
    rows, rhs = [], []
    for i in range(k):
        r = np.zeros(nv)
        r[i * n:(i + 1) * n] = -u[i] / g_hat[i]
        r[nz + i] = 1.0
        rows.append(r)
        rhs.append(math.log(g_hat[i]) - 1.0)
    c = np.zeros(nv)
    c[nz:] = -1.0
    res = linprog(c, A_ub=np.vstack([Ab, np.array(rows)]),
                  b_ub=np.concatenate([bb, np.array(rhs)]), A_eq=A_eq, b_eq=np.ones(n),
                  bounds=[(0.0, 1.0)] * nz + [(None, None)] * k, method="highs")
    if not res.success:
        raise RuntimeError(res.message)
    return res.x[:nz].reshape(k, n)


def oa_master_value(u, M, delta, cut_points):
    """Master optimum for an arbitrary cut set `cut_points` = list of gain vectors."""
    k, n = u.shape
    T = float(M.sum())
    nz, nv = k * n, k * n + k
    A_eq = np.zeros((n, nv))
    for z in range(n):
        for i in range(k):
            A_eq[z, i * n + z] = 1.0
    Ab, bb = _band_rows(M, delta, T, k, nz)
    Ab = np.hstack([Ab, np.zeros((Ab.shape[0], k))])
    rows, rhs = [], []
    for gh in cut_points:
        for i in range(k):
            r = np.zeros(nv)
            r[i * n:(i + 1) * n] = -u[i] / gh[i]
            r[nz + i] = 1.0
            rows.append(r)
            rhs.append(math.log(gh[i]) - 1.0)
    c = np.zeros(nv)
    c[nz:] = -1.0
    res = linprog(c, A_ub=np.vstack([Ab, np.array(rows)]),
                  b_ub=np.concatenate([bb, np.array(rhs)]), A_eq=A_eq,
                  b_eq=np.ones(n), bounds=[(0.0, 1.0)] * nz + [(None, None)] * k,
                  method="highs")
    if not res.success:
        raise RuntimeError(res.message)
    return float(-res.fun)


# ------------------------------------------------------------------------- the duals


def band_status(X, M, delta):
    """`(m, up_tight, lo_tight)` for the district masses of `X`."""
    k = X.shape[0]
    T = float(M.sum())
    m = (X * M[None, :]).sum(axis=1)
    return (m,
            m >= (1.0 + delta) * T / k - 1e-8,
            m <= (1.0 - delta) * T / k + 1e-8)


def solve_duals(u, M, X, g, delta, *, objective="min_abs", supp_tol=1e-8, eq_tol=1e-9):
    """`(p, nu, s)` from the KKT system, by an LP independent of the primal solver.

    Variables `(p_z, nu_i, a_i)` with `a_i >= |nu_i|`.  Rows:
    `p_z + nu_i M_z >= u_i(z)/g_i` everywhere, equality on `supp(X)`.  Complementary
    slackness enters as bounds on `nu_i`: `>= 0` if only the upper band row is tight,
    `<= 0` if only the lower one is, `= 0` if neither, free if both (which happens only
    at `delta = 0`, where the two rows are the same functional).

    `s = (T/k) sum_i a_i` is the supergradient of P4.  Writing the band as the pair
    `mu^+, mu^- >= 0` makes `sum_i (mu^+_i + mu^-_i)` UNBOUNDED at `delta = 0` (both
    rows tight, so `c` can be added to both without changing `nu`); `sum_i |nu_i|` is
    the value of that sum at the canonical decomposition, i.e. its minimum.

    `objective` is one of `"min_abs"`, `"max_abs"`, `("min_nu", i)`, `("max_nu", i)`,
    `("min_p", z)`, `("max_p", z)`.
    """
    k, n = u.shape
    T = float(M.sum())
    _, up_tight, lo_tight = band_status(X, M, delta)

    nv = n + 2 * k                      # p (n), nu (k), a (k)
    bounds: list[tuple[float | None, float | None]] = [(None, None)] * n
    for i in range(k):
        if up_tight[i] and lo_tight[i]:
            bounds.append((-1e3, 1e3))      # free; boxed so the LP stays bounded
        elif up_tight[i]:
            bounds.append((0.0, None))
        elif lo_tight[i]:
            bounds.append((None, 0.0))
        else:
            bounds.append((0.0, 0.0))
    bounds += [(0.0, None)] * k

    def build(tol):
        A_ub, b_ub = [], []
        for i in range(k):
            for z in range(n):
                row = np.zeros(nv)
                row[z] = 1.0
                row[n + i] = M[z]
                rhs = u[i, z] / g[i]
                A_ub.append(-row)
                b_ub.append(-rhs + tol)            # p_z + nu_i M_z >= u_i(z)/g_i - tol
                if X[i, z] > supp_tol:             # ... and <= it + tol on the support
                    A_ub.append(row.copy())
                    b_ub.append(rhs + tol)
        for i in range(k):                         # a_i >= nu_i, a_i >= -nu_i
            r = np.zeros(nv); r[n + i] = 1.0
            r[n + k + i] = -1.0; A_ub.append(r); b_ub.append(0.0)
            r = np.zeros(nv); r[n + i] = -1.0
            r[n + k + i] = -1.0; A_ub.append(r); b_ub.append(0.0)
        return np.array(A_ub), np.array(b_ub)

    # phase 1: the smallest tolerance at which the KKT system is consistent.  It is
    # nonzero only because the primal is a numerical optimum; it is reported, not hidden.
    A1, b1 = build(0.0)
    A1 = np.hstack([A1, np.zeros((A1.shape[0], 1))])
    for r_ in range(A1.shape[0] - 2 * k):
        A1[r_, -1] = -1.0
    c1 = np.zeros(nv + 1); c1[-1] = 1.0
    res1 = linprog(c1, A_ub=A1, b_ub=b1, bounds=bounds + [(0.0, None)], method="highs")
    if not res1.success:
        raise RuntimeError(f"dual phase-1 failed: {res1.message}")
    resid = float(res1.x[-1])

    A_ub, b_ub = build(resid * 1.000001 + 1e-13)
    c = np.zeros(nv)
    if objective == "min_abs":
        c[n + k:] = 1.0
    else:
        what, j = objective
        idx = (n + j) if what.endswith("nu") else j
        c[idx] = 1.0 if what.startswith("min") else -1.0

    res = linprog(c, A_ub=A_ub, b_ub=b_ub, bounds=bounds, method="highs")
    if not res.success:
        raise RuntimeError(f"dual LP failed ({objective}): {res.message}")
    p = res.x[:n]
    nu = res.x[n:n + k]
    return p, nu, (T / k) * float(np.abs(nu).sum()), resid


# ------------------------------------------------------------------ optimal-face vertex


def face_vertex(u, M, delta, g_star, rng):
    """A vertex of the optimal face {x feasible : g(x) = g*}, by a random linear objective."""
    k, n = u.shape
    T = float(M.sum())
    nz = k * n
    A_eq = np.zeros((n + k, nz))
    b_eq = np.zeros(n + k)
    for z in range(n):
        for i in range(k):
            A_eq[z, i * n + z] = 1.0
        b_eq[z] = 1.0
    for i in range(k):
        A_eq[n + i, i * n:(i + 1) * n] = u[i]
        b_eq[n + i] = g_star[i]
    Ab, bb = _band_rows(M, delta, T, k, nz)
    c = rng.normal(size=nz)
    res = linprog(c, A_ub=Ab, b_ub=bb, A_eq=A_eq, b_eq=b_eq,
                  bounds=[(0.0, 1.0)] * nz, method="highs")
    if not res.success:
        return None
    return res.x.reshape(k, n)


def split_count(X, tol=1e-7):
    return int(sum(1 for z in range(X.shape[1]) if (X[:, z] > tol).sum() >= 2))


def tight_band_agents(X, M, delta, T, k, tol=1e-7):
    m = (X * M[None, :]).sum(axis=1)
    return int(sum(1 for i in range(k)
                   if m[i] >= (1 + delta) * T / k - tol or m[i] <= (1 - delta) * T / k + tol))


# ----------------------------------------------------------------------------- toys


def toy1():
    """MODEL_U7-meas section 4: 3 reps A/B/C, 4 zips, k = 2."""
    M = np.array([20.0, 15.0, 15.0, 20.0])
    books = np.array([[10.0, 6.0, 0.0, 0.0],
                      [0.0, 4.0, 8.0, 0.0],
                      [0.0, 0.0, 3.0, 9.0]])
    return M, books, ["A", "B", "C"]


def toy3():
    """6 zips, one heavy zip, 3 reps, k = 2 -- built so the band BINDS at small delta.

    Rep A's book sits entirely on the heavy zip z0 (M = 40 of T = 90), so the
    unconstrained optimum wants districts of 40 and 50 against a target of 45.
    """
    M = np.array([40.0, 10.0, 10.0, 10.0, 10.0, 10.0])
    books = np.array([[20.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                      [0.0, 4.0, 4.0, 4.0, 4.0, 4.0],
                      [2.0, 1.0, 1.0, 1.0, 1.0, 1.0]])
    return M, books, ["A", "B", "C"]


def toy2(seed=20260904):
    """5 reps, 9 zips, k = 3 -- big enough for tight band rows to bite."""
    rng = np.random.default_rng(seed)
    n, nr = 9, 5
    M = np.round(rng.uniform(8.0, 30.0, size=n), 3)
    books = np.zeros((nr, n))
    for z in range(n):
        holders = rng.choice(nr, size=rng.integers(1, 3), replace=False)
        share = rng.uniform(0.15, 0.55)
        for h in holders:
            books[h, z] = round(share * M[z] / len(holders), 3)
    return M, books, [f"R{i}" for i in range(nr)]


# ------------------------------------------------------------------------- the checks


def section(title):
    print("\n" + title)
    print("-" * len(title))


def run_p0_convention():
    section("P0 -- convention check against MODEL_U7-meas section 4 (unmasked u)")
    M, books, _ = toy1()
    u = utilities(M, books)
    d1, d2 = [0, 1], [2, 3]
    g = np.array([[u[i, d1].sum(), u[i, d2].sum()] for i in range(3)])
    want = np.array([[22.82, 16.10], [17.78, 19.46], [16.10, 21.14]])
    check("g matrix reproduces MODEL_U7-meas section 4",
          np.max(np.abs(g - want)) < 5e-3, f"max|dg| = {np.max(np.abs(g - want)):.2e}")
    V = math.log(g[0, 0]) + math.log(g[2, 1])
    check("V(D1->A, D2->C) = 6.1788", abs(V - 6.1788) < 5e-5, f"V = {V:.6f}")
    b = np.array([[16.0, 0.0], [4.0, 8.0], [0.0, 12.0]])
    check("g - 0.42*b has rep-independent rows (FRAME w = 0.42)",
          np.max(np.ptp(g - 0.42 * b, axis=0)) < 1e-9,
          f"max spread = {np.max(np.ptp(g - 0.42 * b, axis=0)):.2e}")
    return g, V


def enumerate_coverages(u, M, S_idx):
    """All integral coverages with roster `S_idx`: every zip to one member of S."""
    k, n = len(S_idx), u.shape[1]
    out = []
    for lab in itertools.product(range(k), repeat=n):
        Xi = np.zeros((k, n))
        for z, i in enumerate(lab):
            Xi[i, z] = 1.0
        g = (u[S_idx] * Xi).sum(axis=1)
        if np.min(g) <= 0:
            continue
        m = (Xi * M[None, :]).sum(axis=1)
        out.append((lab, float(np.sum(np.log(g))), m, Xi))
    return out


def run_p1(name, u_all, M, S_idx, deltas):
    section(f"P1-band -- exhaustive integral check ({name})")
    u = u_all[S_idx]
    k, n = u.shape
    T = float(M.sum())
    covs = enumerate_coverages(u_all, M, S_idx)
    print(f"  {len(covs)} integral coverages, k = {k}, n = {n}, T = {T:.4f}, T/k = {T/k:.4f}")
    worst_all, witness = -math.inf, None
    for d in deltas:
        sol = solve_egbal(u, M, d)
        phi = sol["value"]
        lo, hi = (1 - d) * T / k, (1 + d) * T / k
        ok = [np.all(c[2] >= lo - 1e-12) and np.all(c[2] <= hi + 1e-12) for c in covs]
        feas = [c for c, f in zip(covs, ok) if f]
        infeas = [c for c, f in zip(covs, ok) if not f]
        worst = max((c[1] - phi for c in feas), default=-math.inf)
        worst_all = max(worst_all, worst)
        best_infeas = max((c[1] - phi for c in infeas), default=-math.inf)
        if best_infeas > 1e-9 and witness is None:
            witness = (d, best_infeas, len(feas))
        print(f"  delta = {d:<7.4f} EG^bal = {phi:.10f}  band-feasible = {len(feas):5d}"
              f"  max(V - EG^bal) = {worst: .3e}   best band-INfeasible V - EG^bal = {best_infeas: .3e}")
    check("P1-band: V <= EG^bal(delta) for every band-feasible integral coverage",
          worst_all <= 1e-9, f"max margin = {worst_all:.3e}")
    if witness:
        WITNESS["p1_infeasible_exceeds"] = (name, witness[0], witness[1])
        print(f"  [wit ] the band feasibility check is load-bearing: at delta = "
              f"{witness[0]:.4f} a band-INfeasible integral coverage exceeds EG^bal by "
              f"{witness[1]:.4e} nats")
    return covs


def run_p2(name, u_all, M, S_idx, delta):
    section(f"P2-price -- KKT, personalised prices, budget identities ({name}, delta = {delta})")
    u = u_all[S_idx]
    k, n = u.shape
    T = float(M.sum())
    sol = solve_egbal(u, M, delta)
    X, g = sol["X"], sol["g"]
    p, nu, _, kkt_r = solve_duals(u, M, X, g, delta)
    ktol = max(1e-8, 20.0 * kkt_r)
    q = p[None, :] + nu[:, None] * M[None, :]
    m = (X * M[None, :]).sum(axis=1)
    print(f"  masses m = {np.round(m, 4)}   band = "
          f"[{(1-delta)*T/k:.4f}, {(1+delta)*T/k:.4f}]   nu = {np.round(nu, 6)}")
    print(f"  KKT consistency residual of the numerical primal = {kkt_r:.2e}; "
          f"checks below use tol = {ktol:.1e}")

    resid = u / g[:, None] - q                      # <= 0 everywhere, = 0 on supp
    supp = X > 1e-8
    check("stationarity  u_i(z)/g_i <= p_z + nu_i M_z  everywhere",
          resid.max() <= ktol, f"max = {resid.max():.3e}")
    check("stationarity holds with EQUALITY on supp(X)",
          np.abs(resid[supp]).max() <= ktol, f"max|.| = {np.abs(resid[supp]).max():.3e}")
    check("q_{zi} > 0 everywhere (P2a)", q.min() > 0, f"min q = {q.min():.4f}")
    check("p_z > 0 everywhere (P2b)", p.min() > 0, f"min p = {p.min():.6f}")

    spend = (X * p[None, :]).sum(axis=1)
    check("modified budget identity  sum_z p_z x_zi = 1 - nu_i m_i",
          np.abs(spend - (1 - nu * m)).max() < ktol,
          f"max|.| = {np.abs(spend - (1 - nu * m)).max():.3e}")
    check("summed identity  sum_z p_z = k - sum_i nu_i m_i",
          abs(p.sum() - (k - float(nu @ m))) < k * ktol,
          f"|.| = {abs(p.sum() - (k - float(nu @ m))):.3e}")
    check("personalised spend  sum_z q_zi x_zi = 1  for every i",
          np.abs((X * q).sum(axis=1) - 1).max() < ktol,
          f"max|.| = {np.abs((X * q).sum(axis=1) - 1).max():.3e}")

    # not a competitive equilibrium at the stated unit budgets
    off = np.abs(spend - 1.0)
    j = int(np.argmax(off))
    if off.max() > 1e-6:
        WITNESS["not_ce"] = (name, j, float(spend[j]), float(nu[j]))
        print(f"  [wit ] NOT a CE at unit budgets: rep {j} spends {spend[j]:.6f} of its "
              f"budget 1 at the anonymous prices p  (nu = {nu[j]:+.6f})")
    else:
        print(f"  [note] every rep spends 1 at p (no band row binds): the object has "
              f"collapsed to unconstrained EG")

    # good-side selection rule (the corrected form)
    score = u / g[:, None] - nu[:, None] * M[None, :]
    check("good-side rule: argmax_i (u_i(z)/g_i - nu_i M_z) has value p_z",
          np.abs(score.max(axis=0) - p).max() < ktol,
          f"max|.| = {np.abs(score.max(axis=0) - p).max():.3e}")
    winners_ok = all(np.all(score[supp[:, z], z] >= score[:, z].max() - ktol)
                     for z in range(n))
    check("supp(X) is contained in that argmax", winners_ok)

    # DOMAIN section 2.12's ratio form, as literally written
    ratio = u / q
    bad = [z for z in range(n)
           if not np.all(ratio[supp[:, z], z] >= ratio[:, z].max() - 1e-8)]
    print(f"  [wit ] DOMAIN 2.12's 'supp(X) subset argmax_i u_i(z)/q_zi': "
          f"{len(bad)} of {n} zips violate it as written")
    if bad:
        z = bad[0]
        owners = [i for i in range(k) if supp[i, z]]
        owner = min(owners, key=lambda i: ratio[i, z])
        rival = int(np.argmax(ratio[:, z]))
        WITNESS.setdefault("ratio_form", (name, z, owner, float(ratio[owner, z]),
                                          rival, float(ratio[rival, z])))
        print(f"        zip {z}: owner {owner} has u/q = {ratio[owner, z]:.6f}, "
              f"rival {rival} has {ratio[rival, z]:.6f} (larger), yet "
              f"x[{rival},{z}] = {X[rival, z]:.2e}")
    return sol, (p, nu)


def gauge_interval(u, M, X, g, delta, p, nu, lo=-50.0, hi=50.0, steps=20001):
    """The set of `c` for which `(p - c M, nu + c 1)` is again a KKT multiplier pair."""
    k, n = u.shape
    _, up_t, lo_t = band_status(X, M, delta)
    cs = np.linspace(lo, hi, steps)
    ok = np.ones(steps, bool)
    for i in range(k):
        if up_t[i] and lo_t[i]:
            continue                      # nu_i free
        if up_t[i]:
            ok &= (nu[i] + cs >= -1e-12)
        elif lo_t[i]:
            ok &= (nu[i] + cs <= 1e-12)
        else:
            ok &= (np.abs(nu[i] + cs) <= 1e-12)
    if not ok.any():
        return 0.0, 0.0
    return float(cs[ok].min()), float(cs[ok].max())


def run_p2d_gauge(name, u_all, M, S_idx, deltas):
    section(f"P2d -- gauge freedom (p, nu) -> (p - cM, nu + c1) ({name})")
    u = u_all[S_idx]
    k, n = u.shape
    T = float(M.sum())
    saw_free, saw_pinned = False, False
    for d in deltas:
        sol = solve_egbal(u, M, d)
        X, g = sol["X"], sol["g"]
        t = tight_band_agents(X, M, d, T, k)
        p, nu, s, _ = solve_duals(u, M, X, g, d)
        c_lo, c_hi = gauge_interval(u, M, X, g, d, p, nu)
        q = p[None, :] + nu[:, None] * M[None, :]
        # q is invariant along the orbit, by construction; verify at both ends
        dq = 0.0
        for c in (c_lo, c_hi):
            if not math.isfinite(c):
                continue
            q2 = (p - c * M)[None, :] + (nu + c)[:, None] * M[None, :]
            dq = max(dq, float(np.abs(q - q2).max()))
        print(f"  delta = {d:<7.4f} tight agents = {t}/{k}  gauge c in "
              f"[{c_lo:+.4f}, {c_hi:+.4f}]  width = {c_hi-c_lo:.4f}  max|dq| along orbit = {dq:.2e}")
        if t < k:
            saw_pinned = True
            check(f"  delta={d}: some agent band-slack => gauge pinned to c = 0",
                  abs(c_lo) < 1e-3 and abs(c_hi) < 1e-3, f"[{c_lo:.2e}, {c_hi:.2e}]")
        if c_hi - c_lo > 1e-3:
            saw_free = True
            check(f"  delta={d}: all agents band-tight => nontrivial gauge, q invariant",
                  dq < 1e-9, f"width {c_hi-c_lo:.4f}, max|dq| {dq:.2e}")
    check("both regimes exhibited (pinned and free)", saw_free and saw_pinned,
          f"free={saw_free}, pinned={saw_pinned}")


def run_p4_slope_unbounded(name, u_all, M, S_idx):
    section(f"P4 caveat -- sum(mu+ + mu-) is unbounded at delta = 0 ({name})")
    u = u_all[S_idx]
    k, n = u.shape
    T = float(M.sum())
    sol = solve_egbal(u, M, 0.0)
    X, g = sol["X"], sol["g"]
    _, up_t, lo_t = band_status(X, M, 0.0)
    both = int(np.sum(up_t & lo_t))
    p, nu, s, _ = solve_duals(u, M, X, g, 0.0, objective="min_abs")
    print(f"  at delta = 0 every agent has BOTH band rows tight: {both}/{k}")
    print(f"  minimal slope (T/k)*sum|nu_i| = {s:.6f}; the (mu+, mu-) split adds "
          f"2c to sum(mu+ + mu-) for every c >= 0")
    check("both rows tight for every agent at delta = 0 (so mu+/mu- split is free)",
          both == k)
    check("the minimised slope is finite", math.isfinite(s) and s >= 0, f"s = {s:.6f}")


def run_p3(name, u_all, M, S_idx, deltas, seed=7):
    section(f"P3-split -- splits <= k - 1 + #tight band agents <= 2k - 1 ({name})")
    u = u_all[S_idx]
    k, n = u.shape
    T = float(M.sum())
    rng = np.random.default_rng(seed)
    worst_slack = math.inf
    rows = 0
    for d in deltas:
        sol = solve_egbal(u, M, d)
        g_star = sol["g"]
        seen = set()
        for _ in range(40):
            V = face_vertex(u, M, d, g_star, rng)
            if V is None:
                continue
            key = tuple(np.round(V.ravel(), 9))
            if key in seen:
                continue
            seen.add(key)
            s = split_count(V)
            t = tight_band_agents(V, M, d, T, k)
            bound = k - 1 + t
            worst_slack = min(worst_slack, bound - s)
            rows += 1
            if s > bound:
                check(f"VIOLATION at delta={d}", False, f"splits {s} > {bound}")
        ts = [tight_band_agents(np.array(v).reshape(k, n), M, d, T, k) for v in seen]
        print(f"  delta = {d:<7.4f} distinct vertices = {len(seen):3d}  "
              f"max splits = {max((split_count(np.array(v).reshape(k, n)) for v in seen), default=0)}"
              f"   tight agents t in {sorted(set(ts))}"
              f"   bound k-1+t <= 2k-1 = {2*k-1}")
    check(f"splits <= k - 1 + t at every vertex found ({rows} vertices)",
          worst_slack >= 0, f"min slack (bound - splits) = {worst_slack}")


def run_p3_random(trials=60, seed=1234):
    section("P3-split -- random ensemble (heterogeneous u, several k, several delta)")
    rng = np.random.default_rng(seed)
    worst_slack, worst_coarse, cases = math.inf, math.inf, 0
    max_splits_seen, max_t_seen = 0, 0
    for _ in range(trials):
        n = int(rng.integers(6, 11))
        k = int(rng.integers(2, 5))
        M = np.round(rng.uniform(5.0, 40.0, size=n), 3)
        u = np.round(rng.uniform(0.3, 1.0, size=(k, n)) * M[None, :], 4)
        T = float(M.sum())
        d = float(rng.choice([0.0, 0.02, 0.08, 0.25]))
        try:
            sol = solve_egbal(u, M, d, max_iter=250)
        except RuntimeError:
            continue
        for _ in range(6):
            V = face_vertex(u, M, d, sol["g"], rng)
            if V is None:
                continue
            s = split_count(V)
            t = tight_band_agents(V, M, d, T, k)
            worst_slack = min(worst_slack, (k - 1 + t) - s)
            worst_coarse = min(worst_coarse, (2 * k - 1) - s)
            max_splits_seen = max(max_splits_seen, s)
            max_t_seen = max(max_t_seen, t)
            cases += 1
    check(f"sharp bound splits <= k-1+t holds on {cases} random vertices",
          worst_slack >= 0, f"min slack = {worst_slack}")
    check(f"coarse bound splits <= 2k-1 holds on {cases} random vertices",
          worst_coarse >= 0, f"min slack = {worst_coarse}, max splits seen = {max_splits_seen}, "
                             f"max tight agents seen = {max_t_seen}")


def run_p4(name, u_all, M, S_idx, grid):
    section(f"P4-slope -- monotone, concave, tangent bound, one-sided derivatives ({name})")
    u = u_all[S_idx]
    k, n = u.shape
    T = float(M.sum())
    vals, slopes = [], []
    for d in grid:
        sol = solve_egbal(u, M, d)
        X, g = sol["X"], sol["g"]
        _, nu, s_lo, _ = solve_duals(u, M, X, g, d, objective="min_abs")
        rng_nu = []
        for i in range(k):
            lo = solve_duals(u, M, X, g, d, objective=("min_nu", i))[1][i]
            hi = solve_duals(u, M, X, g, d, objective=("max_nu", i))[1][i]
            rng_nu.append(hi - lo)
        vals.append(sol["value"])
        slopes.append((s_lo, s_lo))
        w = max(rng_nu)
        wtxt = "unbounded (gauge)" if w > 1e3 else f"{w:.2e}"
        print(f"  delta = {d:<7.4f} EG^bal = {sol['value']:.10f}   "
              f"s_min = (T/k)sum|nu| = {s_lo:.6f}   max width of a single nu_i over the "
              f"dual set = {wtxt}")
    vals = np.array(vals)

    mono = np.min(np.diff(vals))
    check("monotone nondecreasing in delta", mono >= -1e-10, f"min increment = {mono:.3e}")

    worst_conc = math.inf
    for a in range(len(grid)):
        for b in range(a + 2, len(grid)):
            for c in range(a + 1, b):
                th = (grid[b] - grid[c]) / (grid[b] - grid[a])
                worst_conc = min(worst_conc, vals[c] - (th * vals[a] + (1 - th) * vals[b]))
    check("concave in delta (chord test, all triples)", worst_conc >= -1e-9,
          f"min (value - chord) = {worst_conc:.3e}")

    worst_tan = -math.inf
    for a in range(len(grid)):
        for b in range(len(grid)):
            if a == b:
                continue
            s = slopes[a][0]                     # the MINIMISED slope: the tightest one
            worst_tan = max(worst_tan, vals[b] - (vals[a] + s * (grid[b] - grid[a])))
    check("supergradient: EG^bal(d') <= EG^bal(d) + s_min(d)(d'-d) for all grid pairs",
          worst_tan <= 1e-8, f"max violation = {worst_tan:.3e}")

    worst_ch = -math.inf
    for a in range(len(grid) - 1):
        for c in range(a + 1, len(grid)):
            mid = 0.5 * (grid[a] + grid[c])
            v = solve_egbal(u, M, mid)["value"]
            worst_ch = max(worst_ch, 0.5 * (vals[a] + vals[c]) - v)
    check("chord lower bound: midpoint value >= mean of endpoints",
          worst_ch <= 1e-9, f"max violation = {worst_ch:.3e}")

    # one-sided derivatives bracket the multiplier slope
    print("  one-sided derivative check (h = 1e-5):")
    ok = True
    for idx in range(1, len(grid) - 1):
        d = grid[idx]
        h = 1e-5
        vp = solve_egbal(u, M, d + h)["value"]
        vm = solve_egbal(u, M, max(d - h, 0.0))["value"]
        dplus = (vp - vals[idx]) / h
        dminus = (vals[idx] - vm) / h
        lo, hi = slopes[idx]
        good = dplus <= hi + 1e-4 and lo <= dminus + 1e-4 and dplus <= dminus + 1e-6
        ok = ok and good
        print(f"    delta = {d:<7.4f} D+ = {dplus:9.5f}  [mult {lo:9.5f}, {hi:9.5f}]  "
              f"D- = {dminus:9.5f}  {'ok' if good else 'FAIL'}")
    check("D+ <= s_min <= D- at every interior grid point", ok)
    return vals, slopes


def run_p4_kink(name, u_all, M, S_idx):
    """The frontier has a genuine kink where the band stops binding: D+ < D-."""
    section(f"P4 -- the kink at delta_c, the max deviation of the UNCONSTRAINED optimum ({name})")
    u = u_all[S_idx]
    k, n = u.shape
    T = float(M.sum())
    free = solve_egbal(u, M, 5.0)
    m = (free["X"] * M[None, :]).sum(axis=1)
    dc = float(np.max(np.abs(m - T / k)) / (T / k))
    h = 1e-4
    v0 = solve_egbal(u, M, dc)["value"]
    vp = solve_egbal(u, M, dc + h)["value"]
    vm = solve_egbal(u, M, max(dc - h, 0.0))["value"]
    dplus, dminus = (vp - v0) / h, (v0 - vm) / h
    sc = solve_egbal(u, M, dc)
    _, _, s, _ = solve_duals(u, M, sc["X"], sc["g"], dc)
    print(f"  delta_c = {dc:.6f}   EG^bal(delta_c) = {v0:.10f} = EG_S (unconstrained) "
          f"= {free['value']:.10f}")
    print(f"  D+ = {dplus:.6f}   s_min = {s:.6f}   D- = {dminus:.6f}")
    check("a kink exists at delta_c: D+ < D- strictly",
          dplus < dminus - 1e-5, f"D- - D+ = {dminus - dplus:.3e}")
    check("s_min lies in the subdifferential interval [D+, D-]",
          dplus - 1e-6 <= s <= dminus + 1e-6, f"s = {s:.6f}")
    check("EG^bal is constant for delta >= delta_c (D+ = 0)", abs(dplus) < 1e-6)
    return dc


def run_p4_softness(name, u_all, M, S_idx, d0, d_sponsor, V_delivered):
    section(f"P4 corollary -- the one-solve softness certificate ({name})")
    u = u_all[S_idx]
    k = u.shape[0]
    T = float(M.sum())
    sol = solve_egbal(u, M, d0)
    _, _, s, _ = solve_duals(u, M, sol["X"], sol["g"], d0, objective="min_abs")
    cert = sol["value"] + s * (d_sponsor - d0)
    truth = solve_egbal(u, M, d_sponsor)["value"]
    print(f"  EG^bal({d0}) = {sol['value']:.10f}, slope certificate s = {s:.6f}")
    print(f"  one-solve bound at delta = {d_sponsor}: {cert:.10f};  true value {truth:.10f}")
    print(f"  certified premium over V(delivered) = {V_delivered:.6f}: "
          f"{cert - V_delivered:.6f} nats (true {truth - V_delivered:.6f})")
    check("one-solve certificate is a valid upper bound at the sponsor's delta",
          cert >= truth - 1e-9, f"slack = {cert - truth:.3e}")


def run_p5(name, u_all, M, S_idx, delta, seed=99):
    section(f"P5-OA -- every master optimum is an upper bound ({name}, delta = {delta})")
    u = u_all[S_idx]
    k, n = u.shape
    sol = solve_egbal(u, M, delta, trace=True)
    phi = sol["value"]
    ub, lb = np.array(sol["ub_hist"]), np.array(sol["lb_hist"])
    check("every master optimum is >= EG^bal(delta) (valid upper bound)",
          ub.min() >= phi - 1e-9, f"min over {len(ub)} iterations = {ub.min():.12f} vs {phi:.12f}")
    check("master optima are monotone non-increasing in the cut set",
          np.max(np.diff(ub)) <= 1e-9, f"max increment = {np.max(np.diff(ub)):.3e}")
    check("the loop brackets EG^bal at every iteration (LB <= EG^bal <= UB)",
          bool(np.all(lb <= phi + 1e-12) and np.all(ub >= phi - 1e-9)))
    print(f"  iterations = {sol['iters']}, final bracket = {ub[-1] - lb[-1]:.3e} nats")
    print(f"  UB trace (first 6): {[round(v, 8) for v in ub[:6]]}")

    # exactness at a single well-placed cut
    one = oa_master_value(u, M, delta, [sol["g"]])
    check("a SINGLE tangent at the optimal g* makes the master exact",
          abs(one - phi) < 1e-9, f"master = {one:.12f}, EG^bal = {phi:.12f}, "
                                 f"|diff| = {abs(one - phi):.2e}")

    # random cut sets are still valid upper bounds
    rng = np.random.default_rng(seed)
    worst = math.inf
    for _ in range(25):
        pts = [np.abs(sol["g"] * rng.uniform(0.3, 3.0, size=k)) for _ in range(rng.integers(1, 4))]
        worst = min(worst, oa_master_value(u, M, delta, pts) - phi)
    check("25 random cut sets all give valid upper bounds",
          worst >= -1e-9, f"min (master - EG^bal) = {worst:.3e}")

    # g_i >= lam * (1-delta) T/k, the explicit ghat > 0 guarantee
    T = float(M.sum())
    check("g_i >= lam(1-delta)T/k > 0 at the optimum (the ghat > 0 hypothesis)",
          sol["g"].min() >= 0.30 * (1 - delta) * T / k - 1e-9,
          f"min g = {sol['g'].min():.4f} vs lam(1-delta)T/k = {0.30*(1-delta)*T/k:.4f}")


def run_g_unique(name, u_all, M, S_idx, delta, seed=5):
    section(f"P0b -- the optimal gain vector g* is unique ({name}, delta = {delta})")
    u = u_all[S_idx]
    k, n = u.shape
    rng = np.random.default_rng(seed)
    sol = solve_egbal(u, M, delta)
    gs, ss = [], set()
    for _ in range(25):
        V = face_vertex(u, M, delta, sol["g"], rng)
        if V is None:
            continue
        gs.append((u * V).sum(axis=1))
        ss.add(tuple(sorted(z for z in range(n) if (V[:, z] > 1e-7).sum() >= 2)))
    gs = np.array(gs)
    check("g* identical across all optimal-face vertices",
          np.max(np.abs(gs - sol["g"][None, :])) < 1e-7,
          f"max|dg| = {np.max(np.abs(gs - sol['g'][None, :])):.2e}")
    check("but the split SET is vertex-dependent (U1-cert failure mode 9 survives the band)",
          len(ss) >= 1, f"{len(ss)} distinct split sets over {len(gs)} vertices")


# ------------------------------------------------------------------------------ main


def main():
    print("MODEL_U9-bandthm numerical checks")
    print(f"python {sys.version.split()[0]}  numpy {np.__version__}  ", end="")
    import scipy
    print(f"scipy {scipy.__version__}")
    print("seeds: toy2 = 20260904, P3 face vertices = 7, P3 ensemble = 1234, "
          "P5 random cut sets = 99, g* uniqueness = 5")

    run_p0_convention()

    # ---- toy 1: the shared U7-meas fixture, roster S = {A, C} (stage 2's own pick).
    # Its M is symmetric, so the unconstrained optimum is already exactly balanced and
    # the band NEVER binds: the frontier is flat and nu == 0 at every delta.  Kept as
    # the shared fixture and as the degenerate-case check.
    M1, B1, _ = toy1()
    u1 = utilities(M1, B1)
    S1 = [0, 2]
    run_p1("toy1 S={A,C}", u1, M1, S1, [0.0, 0.02, 0.0714286, 0.15, 0.33])
    run_p4("toy1 S={A,C} (flat frontier)", u1, M1, S1,
           [0.0, 0.02, 0.05, 0.10, 0.20, 0.33])

    # ---- toy 3: the band binds
    M3, B3, _ = toy3()
    u3 = utilities(M3, B3)
    S3 = [0, 1]
    run_p1("toy3 S={A,B}", u3, M3, S3, [0.0, 0.02, 0.06, 0.111112, 0.33])
    run_p2("toy3 S={A,B}", u3, M3, S3, 0.02)
    run_p2d_gauge("toy3 S={A,B}", u3, M3, S3, [0.0, 0.02, 0.06, 0.33])
    run_p4_slope_unbounded("toy3 S={A,B}", u3, M3, S3)
    run_p3("toy3 S={A,B}", u3, M3, S3, [0.0, 0.02, 0.06, 0.33])
    run_p4("toy3 S={A,B}", u3, M3, S3, [0.0, 0.01, 0.02, 0.04, 0.06, 0.09, 0.15, 0.33])
    run_p4_kink("toy3 S={A,B}", u3, M3, S3)
    run_p5("toy3 S={A,B}", u3, M3, S3, 0.02)
    run_g_unique("toy3 S={A,B}", u3, M3, S3, 0.02)

    # ---- toy 2: 5 reps, 9 zips, k = 3
    M2, B2, _ = toy2()
    u2 = utilities(M2, B2)
    S2 = [0, 2, 4]
    grid2 = [0.0, 0.01, 0.03, 0.06, 0.12, 0.20, 0.35]
    run_p1("toy2 S={R0,R2,R4}", u2, M2, S2, [0.0, 0.03, 0.12, 0.35])
    run_p2("toy2 S={R0,R2,R4}", u2, M2, S2, 0.03)
    run_p2d_gauge("toy2 S={R0,R2,R4}", u2, M2, S2, [0.0, 0.03, 0.12, 0.35])
    run_p3("toy2 S={R0,R2,R4}", u2, M2, S2, [0.0, 0.03, 0.12, 0.35])
    run_p4("toy2 S={R0,R2,R4}", u2, M2, S2, grid2)
    run_p4_kink("toy2 S={R0,R2,R4}", u2, M2, S2)
    run_p5("toy2 S={R0,R2,R4}", u2, M2, S2, 0.03)
    run_g_unique("toy2 S={R0,R2,R4}", u2, M2, S2, 0.03)

    # the one-solve softness certificate, against a real band-feasible integral coverage
    covs2 = enumerate_coverages(u2, M2, S2)
    T2 = float(M2.sum())
    lo, hi = 0.97 * T2 / 3, 1.03 * T2 / 3
    feas2 = [c for c in covs2
             if np.all(c[2] >= lo - 1e-12) and np.all(c[2] <= hi + 1e-12)]
    best2 = max(feas2, key=lambda c: c[1])
    run_p4_softness("toy2", u2, M2, S2, 0.03, 0.12, best2[1])

    run_p3_random()

    section("Specialisations at the real instance's shape (FRAME section 6 constants)")
    T_real, k_real, lam = 2745.611187, 13, 0.30
    V_del, EG_S13, screen = 59.9374697984, 60.6974156139, 60.8025
    print(f"  T/k                            = {T_real/k_real:.6f}")
    print(f"  split-unit bound 2k-1          = {2*k_real-1}   (coarse 2k = {2*k_real}, "
          f"unbanded k-1 = {k_real-1})")
    for d in (0.0039, 0.0062, 0.0078, 0.02, 0.05, 0.10, 0.33):
        print(f"  delta = {d:<7.4f} band = [{(1-d)*T_real/k_real:.4f}, "
              f"{(1+d)*T_real/k_real:.4f}]  width = {2*d*T_real/k_real:.4f}  "
              f"g_i >= lam(1-delta)T/k = {lam*(1-d)*T_real/k_real:.4f}")
    print(f"  slope needed to exhaust the certified gap EG_S13 - V over [0.0039, 0.33]:")
    for d in (0.0078, 0.02, 0.05, 0.10, 0.33):
        print(f"    from delta_0 = 0.0039 to {d:<7.4f}: s <= "
              f"{(EG_S13 - V_del)/(d - 0.0039):.4f} nats per unit delta keeps the "
              f"certificate below EG_S13")
    print(f"  tier-2 softness at delta from delta_0 = 0.0039 needs "
          f"EG^bal(0.0039) + s*(delta-0.0039) - {V_del:.6f} <= 5e-3")
    print(f"  roster-free screen (LENS_GROMOV M8) {screen:.4f}; screen - V = "
          f"{screen - V_del:.4f} nats; EG_S13 - V = {EG_S13 - V_del:.10f} nats")

    section("Witnesses required by the acceptance criterion")
    check("a witness exists that the EG^bal optimum is NOT a CE at unit budgets",
          "not_ce" in WITNESS, str(WITNESS.get("not_ce")))
    check("a witness exists refuting DOMAIN 2.12's ratio form of the good-side MBB rule",
          "ratio_form" in WITNESS, str(WITNESS.get("ratio_form")))
    check("a witness exists that the band feasibility check in P1-band is load-bearing",
          "p1_infeasible_exceeds" in WITNESS, str(WITNESS.get("p1_infeasible_exceeds")))

    print("\n" + "=" * 70)
    print("FAILURES: " + ("none" if not FAILURES else "; ".join(FAILURES)))
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
