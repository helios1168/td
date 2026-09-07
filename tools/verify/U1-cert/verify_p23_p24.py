"""U1-cert verification D -- P2.3 (assignment at pinned centers) and P2.4 (power weights).

Own toy (9 zips, k = 3, own coordinates), own brute force, own transportation solves.  The
only project code called is the thing under test: `cert_draw.cert_assignment_at_centers` and
`centers.power_weights`.

P2.3 oracle: exhaustive enumeration of all 3^9 integral assignments inside the same
max-deviation band, compared against the MILP's `opt_cost`.
P2.4 oracle: the penalised fibre max_X sum_j log m_j - rho*sum M_z d^2 x_zj solved *outside*
the model's mirror ascent -- by minimising over the mass vector m with F(m) computed by an
exact transportation LP -- then the KKT identities checked by O(nk) arithmetic.

Run:  /Users/ntlee/projects/td/.venv/bin/python3 docs/artifacts/U1-cert/verify_p23_p24.py
from /Users/ntlee/projects/td/.claude/worktrees/A1 .
"""
from __future__ import annotations

import itertools
import math
import sys
from pathlib import Path

import numpy as np
import sympy as sp
from scipy import sparse
from scipy.optimize import linprog, minimize

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from td.solvers import cert_draw, centers  # noqa: E402

FAILURES: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  [{'ok ' if ok else 'FAIL'}] {name}" + (f"   {detail}" if detail else ""))
    if not ok:
        FAILURES.append(name)


def toy():
    xy = np.array([[0.0, 0.0], [1.0, 0.3], [2.1, 0.1], [0.3, 1.2], [1.4, 1.0],
                   [2.3, 1.3], [0.1, 2.2], [1.2, 2.4], [2.4, 2.1]])
    M = np.array([9.0, 13.0, 7.0, 11.0, 15.0, 8.0, 12.0, 6.0, 14.0])
    C = np.array([[0.4, 0.4], [1.8, 0.6], [1.2, 2.1]])
    return xy, M, C, 3


def d2mat(xy, C):
    return ((xy[:, None, :] - C[None, :, :]) ** 2).sum(axis=2)


def transport(M, cost, m):
    """min sum_{z,j} cost_zj x_zj  s.t. sum_j x = 1, sum_z M_z x_zj = m_j, x >= 0."""
    n, k = cost.shape
    cols = np.arange(n * k)
    A = sparse.vstack([
        sparse.coo_matrix((np.ones(n * k), (np.repeat(np.arange(n), k), cols)),
                          shape=(n, n * k)),
        sparse.coo_matrix((np.repeat(M, k), (np.tile(np.arange(k), n), cols)),
                          shape=(k, n * k)),
    ]).tocsc()
    b = np.concatenate([np.ones(n), np.asarray(m, float)])
    res = linprog(cost.ravel(), A_eq=A, b_eq=b, bounds=(0, None), method="highs")
    return res


def main() -> int:
    xy, M, C, k = toy()
    n = M.size
    d2 = d2mat(xy, C)
    cost = M[:, None] * d2
    T = M.sum()
    target = T / k

    print("=" * 78)
    print("P2.3 -- cert_assignment_at_centers vs exhaustive enumeration in the same band")
    lab0 = d2.argmin(axis=1)                       # a Voronoi draw, as the reference
    out = cert_draw.cert_assignment_at_centers(xy, M, lab0, C, time_limit=60.0)
    delta = out["slack"]
    print(f"  slack (draw's own max dev) = {delta:.6f}; MILP opt_cost = {out['opt_cost']!r}")
    check("trap 12: the certificate passes mip_rel_gap = 0.0", out["mip_rel_gap"] == 0.0)
    check("the MILP proved optimality (solver status 0)", out["proved"],
          out.get("solver_status_name", ""))
    best, arg = math.inf, None
    for lab in itertools.product(range(k), repeat=n):
        mass = np.bincount(lab, weights=M, minlength=k)
        if np.abs(mass - target).max() > delta + 1e-9:
            continue
        c = float(cost[np.arange(n), list(lab)].sum())
        if c < best:
            best, arg = c, lab
    print(f"  brute force over all 3^9 = {3**n} assignments: best in band = {best!r}")
    check("P2.3: MILP optimum equals the brute-force optimum in the same band",
          abs(best - out["opt_cost"]) < 1e-9, f"delta = {best - out['opt_cost']:.3e}")
    check("P2.3: the reference draw is feasible for its own test (opt <= draw)",
          out["opt_cost"] <= out["draw_cost"] + 1e-12)

    print("=" * 78)
    print("P2.4a -- KKT of the penalised fibre, symbolically")
    Mz, mj, rh, dz = sp.symbols("M_z m_j rho d2", positive=True)
    # stationarity in x_zj:  d/dx [ sum_j log m_j - rho sum M_z d2 x_zj ] = M_z/m_j - rho M_z d2
    stat = Mz / mj - rh * Mz * dz
    per_unit = sp.simplify(stat / Mz)
    check("symbolic: dividing the stationarity condition by M_z > 0 gives 1/m_j - rho d2",
          sp.simplify(per_unit - (1 / mj - rh * dz)) == 0, str(per_unit))
    om = sp.Symbol("omega_j", positive=True)
    check("symbolic: argmax_j (1/m_j - rho d2) = argmin_j (d2 - omega_j) with "
          "omega_j = 1/(rho m_j)",
          sp.simplify((1 / mj - rh * dz) * (-1 / rh) - (dz - 1 / (rh * mj))) == 0)
    check("symbolic: omega_j = 1/(rho m_j) is exactly the substitution that does it",
          sp.simplify((dz - om).subs(om, 1 / (rh * mj)) - (dz - 1 / (rh * mj))) == 0)

    print("=" * 78)
    print("P2.4b -- omega is a dual-OPTIMAL weight vector, for EVERY omega > 0 (exact)")
    # For any omega > 0 let X(omega) be the power-diagram assignment and m(omega) its masses.
    # Setting alpha_z = M_z min_j (d2_zj - omega_j) makes (alpha, omega) dual feasible for the
    # transportation LP at targets m(omega), with complementary slackness on supp X.  No
    # optimisation anywhere: this is arithmetic, and it is checked in exact rationals.
    from fractions import Fraction as Fr
    rng = np.random.default_rng(77)
    worst_v, worst_cs, worst_gap = 0, 0, 0
    for _ in range(200):
        n2, k2 = int(rng.integers(5, 12)), int(rng.integers(2, 5))
        d2q = [[Fr(int(rng.integers(1, 400)), 7) for _ in range(k2)] for _ in range(n2)]
        Mq = [Fr(int(rng.integers(1, 40)), 3) for _ in range(n2)]
        omq = [Fr(int(rng.integers(-200, 200)), 11) for _ in range(k2)]
        lab = [min(range(k2), key=lambda j: d2q[z][j] - omq[j]) for z in range(n2)]
        alq = [Mq[z] * min(d2q[z][j] - omq[j] for j in range(k2)) for z in range(n2)]
        mq = [sum((Mq[z] for z in range(n2) if lab[z] == j), Fr(0)) for j in range(k2)]
        v = min(Mq[z] * d2q[z][j] - alq[z] - Mq[z] * omq[j]
                for z in range(n2) for j in range(k2))
        cs = max(abs(Mq[z] * d2q[z][lab[z]] - alq[z] - Mq[z] * omq[lab[z]])
                 for z in range(n2))
        cost_q = sum(Mq[z] * d2q[z][lab[z]] for z in range(n2))
        dual_q = sum(alq) + sum(omq[j] * mq[j] for j in range(k2))
        worst_v = min(worst_v, v)
        worst_cs = max(worst_cs, cs)
        worst_gap = max(worst_gap, abs(cost_q - dual_q))
    check("EXACT rationals, 200 random cases: (alpha, omega) is dual feasible "
          "(min slack >= 0)", worst_v >= 0, f"min slack = {worst_v}")
    check("EXACT rationals: complementary slackness on the power cells is identically 0",
          worst_cs == 0, f"max residual = {worst_cs}")
    check("EXACT rationals: dual objective = primal cost, so omega is dual OPTIMAL at "
          "targets m(omega) and X(omega) is primal optimal", worst_gap == 0,
          f"max |dual - cost| = {worst_gap}")

    print("=" * 78)
    print("P2.4c -- the nondegeneracy caveat, at genuine fibre optima")
    rows = []
    for (xy_, M_, C_, rho) in cases():
        r = p24_case(xy_, M_, C_, rho)
        if r is not None:
            rows.append(r)
    nd = [r for r in rows if r["support"] == r["nk1"]]
    dg = [r for r in rows if r["support"] != r["nk1"]]
    for r in rows:
        tag = "NONDEG" if r["support"] == r["nk1"] else "degen "
        print(f"  {r['tag']:<16} {tag} support={r['support']}/{r['nk1']}  "
              f"lp_bound-cost={r['bound_delta']:.1e}  identity spread={r['spread']:.2e}")
    print(f"  cases: {len(nd)} nondegenerate, {len(dg)} degenerate")
    check("at least one nondegenerate and one degenerate case exercised",
          len(nd) >= 1 and len(dg) >= 1, f"{len(nd)} / {len(dg)}")
    check("NONDEGENERATE => HiGHS' beta satisfies rho*beta_j - 1/m*_j = const "
          "(max spread over all nondegenerate cases)",
          all(r["spread"] < 1e-7 for r in nd),
          f"max spread = {max((r['spread'] for r in nd), default=0):.2e}")
    check("the caveat reproduces: at some degenerate optimum the identity FAILS while "
          "power_weights' lp_bound is still exactly the LP cost",
          any(r["spread"] > 1e-3 for r in dg) and all(r["bound_ok"] for r in dg),
          f"max degenerate spread = {max((r['spread'] for r in dg), default=0):.2e}")
    holds = [r for r in dg if r["spread"] < 1e-7]
    print(f"  ATTACK on the 'iff': degenerate cases where the identity nevertheless holds: "
          f"{len(holds)}")
    check("the 'iff' survives this search in the <= direction too (no degenerate case with "
          "the identity holding was found)", len(holds) == 0)
    print("=" * 78)
    print("FAILURES:", "none" if not FAILURES else FAILURES)
    return 0 if not FAILURES else 1


def cases():
    """Toys and rho values, chosen to straddle the degenerate/nondegenerate boundary."""
    xy, M, C, k = toy()
    for rho in (0.0005, 0.001, 0.002, 0.005, 0.02, 0.05, 0.2):
        yield xy, M, C, rho
    rng = np.random.default_rng(2026)
    for _ in range(16):
        n = int(rng.integers(7, 11))
        xy2 = rng.random((n, 2)) * 3
        M2 = rng.uniform(4, 16, n)
        C2 = rng.random((3, 2)) * 3
        yield xy2, M2, C2, float(rng.choice([0.0005, 0.001, 0.005, 0.02, 0.1]))


def fibre_mstar(M, cost, T, k, rho, rounds=30, grid=13):
    """argmax over m of sum_j log m_j - rho*F(m), F by exact transportation LP.

    Nested grid refinement on the (k-1) free coordinates.  Independent of any mirror-ascent
    or proportional-response iteration.
    """
    lo = np.full(k - 1, 1e-6)
    hi = np.full(k - 1, T - 1e-6)
    best = None
    for _ in range(rounds):
        axes = [np.linspace(lo[i], hi[i], grid) for i in range(k - 1)]
        for pt in itertools.product(*axes):
            m = np.array(list(pt) + [T - sum(pt)])
            if (m <= 1e-9).any():
                continue
            r = transport(M, cost, m)
            if not r.success:
                continue
            val = float(np.log(m).sum() - rho * r.fun)
            if best is None or val > best[0]:
                best = (val, m.copy())
        step = [(hi[i] - lo[i]) / (grid - 1) for i in range(k - 1)]
        lo = np.array([max(1e-9, best[1][i] - step[i]) for i in range(k - 1)])
        hi = np.array([min(T - 1e-9, best[1][i] + step[i]) for i in range(k - 1)])
        if max(step) < 1e-12:
            break
    return best[1]


def p24_case(xy, M, C, rho):
    """Classify one (toy, rho) by degeneracy and test the HiGHS-beta identity there."""
    n, k = xy.shape[0], C.shape[0]
    d2 = d2mat(xy, C)
    cost = M[:, None] * d2
    T = float(M.sum())
    mstar = fibre_mstar(M, cost, T, k, rho)
    lp = transport(M, cost, mstar)
    if not lp.success:
        return None
    X = lp.x.reshape(n, k)
    supp = X > 1e-9
    pw = centers.power_weights(xy, M, C, targets=mstar)
    omega_h = np.asarray(pw["weights_raw"], float)
    ident = rho * omega_h - 1.0 / mstar
    return dict(rho=rho, tag=f"n={n},rho={rho}", support=int(supp.sum()), nk1=n + k - 1,
                bound_ok=abs(pw["lp_bound"] - float(lp.fun)) < 1e-6,
                bound_delta=abs(pw["lp_bound"] - float(lp.fun)),
                spread=float(ident.max() - ident.min()))


if __name__ == "__main__":
    sys.exit(main())
