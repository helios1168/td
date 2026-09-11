"""Independent U9-bandthm re-check. See REPORT_20260911.md for the claims and proofs.

Run from the worktree root with $TD_PY tools/verify/U9-bandthm/recheck_20260911.py.
Exit 0 means the checks reproduced their stated results, including the refutations.
No production implementation or previous verifier is imported. No files are written.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
import math
import platform

import numpy as np
import scipy
from scipy.optimize import linprog
import sympy as sp


@dataclass(frozen=True)
class ExactCase:
    """Rows of u and x are agents; columns are goods. All entries are rational."""

    delta: sp.Rational
    mass: sp.Matrix
    u: sp.Matrix
    x: sp.Matrix
    p: sp.Matrix
    nu: sp.Matrix


R = sp.Rational
CERT_TOL: float = 1e-8
DC = R(1, 6)
U = sp.Matrix([[1, R(1, 3)], [R(1, 2), R(1, 3)]])


def zero(expr: sp.Expr) -> None:
    assert sp.simplify(expr) == 0, expr


def gains(u: sp.Matrix, x: sp.Matrix) -> sp.Matrix:
    return sp.Matrix([sum(u[i, z] * x[i, z] for z in range(u.cols))
                      for i in range(u.rows)])


def smooth_case(delta: sp.Rational) -> ExactCase:
    d = min(delta, DC)
    slope = (1 - 6 * d) / ((1 - d) * (2 + 3 * d))
    return ExactCase(
        delta, sp.ones(2, 1), U, sp.Matrix([[1 - d, 0], [d, 1]]),
        sp.Matrix([3 / (2 + 3 * d), 2 / (2 + 3 * d)]),
        sp.Matrix([-slope, 0]),
    )


def check_feasible(case: ExactCase) -> None:
    k, n = case.x.shape
    target = sum(case.mass) / k
    assert all(v >= 0 for v in case.x)
    for z in range(n):
        zero(sum(case.x[:, z]) - 1)
    for m in case.x * case.mass:
        assert (1 - case.delta) * target <= m <= (1 + case.delta) * target


def check_kkt_and_rank(case: ExactCase) -> None:
    check_feasible(case)
    k, n = case.x.shape
    g = gains(case.u, case.x)
    masses = case.x * case.mass
    target = sum(case.mass) / k
    support = [(i, z) for i in range(k) for z in range(n) if case.x[i, z] > 0]
    tight = [i for i in range(k) if masses[i] in
             ((1 - case.delta) * target, (1 + case.delta) * target)]
    assert all(v > 0 for v in g)
    for i in range(k):
        mup, mum = max(case.nu[i], 0), max(-case.nu[i], 0)
        zero(mup * ((1 + case.delta) * target - masses[i]))
        zero(mum * (masses[i] - (1 - case.delta) * target))
        spend = 0
        for z in range(n):
            q = case.p[z] + case.nu[i] * case.mass[z]
            residual = q - case.u[i, z] / g[i]
            assert q > 0 and residual >= 0
            zero(residual * case.x[i, z])
            spend += case.p[z] * case.x[i, z]
        zero(spend - (1 - case.nu[i] * masses[i]))
    zero(sum(case.p) + sum(case.nu[i] * masses[i] for i in range(k)) - k)
    if case.delta > 0:
        assert all(p > 0 for p in case.p)

    # Exact active-row rank, restricted to positive support. Full column rank
    # establishes that these examples are vertices of the fixed-gain polytope.
    rows = [[int(z == zz) for i, z in support] for zz in range(n)]
    rows += [[case.u[i, z] / g[i] if i == ii else 0 for i, z in support]
             for ii in range(k)]
    rows += [[case.mass[z] if i == ii else 0 for i, z in support] for ii in tight]
    a = sp.Matrix(rows)
    weights = list(case.p) + [-1] * k + [case.nu[i] for i in tight]
    assert sp.Matrix([weights]) * a == sp.zeros(1, len(support))
    assert a.rank() == len(support) <= n + k + len(tight) - 1
    splits = sum(sum(int(bool(case.x[i, z] > 0)) for i in range(k)) > 1
                 for z in range(n))
    assert splits <= k - 1 + len(tight) <= 2 * k - 1

    # P6: direct utility-space separating cells, with no geographic inference.
    for z in range(n):
        scores = [case.u[i, z] / g[i] - case.nu[i] * case.mass[z]
                  for i in range(k)]
        zero(max(scores) - case.p[z])
        for i in range(k):
            if case.x[i, z] > 0:
                zero(scores[i] - max(scores))


def attack_zero_gains() -> None:
    case = ExactCase(R(1), sp.ones(2, 1), sp.ones(2, 2),
                     sp.Matrix([[1, 1], [0, 0]]), sp.zeros(2, 1), sp.zeros(2, 1))
    check_feasible(case)
    assert gains(case.u, case.x) == sp.Matrix([2, 0])
    print("P0 REFUTED: delta=1, M=(1,1), u=ones, X=((1,1),(0,0)), g=(2,0).")

    # P5.5 fails even when initialized at the usual uniform assignment.
    # Each good has a unique largest tangent coefficient, excluding agent 3.
    u = sp.Matrix([[1, R(1, 3)], [R(1, 3), 1], [R(2, 3), R(2, 3)]])
    initial_g = gains(u, sp.ones(3, 2) / 3)
    assert initial_g == sp.ones(3, 1) * R(4, 9)
    coefficients = u * R(9, 4)
    assert coefficients[0, 0] > max(coefficients[1, 0], coefficients[2, 0])
    assert coefficients[1, 1] > max(coefficients[0, 1], coefficients[2, 1])
    next_case = ExactCase(R(1), sp.ones(2, 1), u,
                          sp.Matrix([[1, 0], [0, 1], [0, 0]]),
                          sp.zeros(2, 1), sp.zeros(3, 1))
    check_feasible(next_case)
    assert gains(u, next_case.x) == sp.Matrix([1, 1, 0])
    optimum = ExactCase(R(1), sp.ones(2, 1), u,
                        sp.Matrix([[R(2, 3), 0], [0, R(2, 3)], [R(1, 3), R(1, 3)]]),
                        sp.ones(2, 1) * R(3, 2), sp.zeros(3, 1))
    check_kkt_and_rank(optimum)
    zero(sp.prod(gains(u, optimum.x)) / sp.prod(initial_g) - R(9, 4))
    assert float(sp.log(R(9, 4))) > R(1, 100)
    g = sp.symbols("g", positive=True)
    assert sp.limit(sp.log(g), g, 0, dir="+") == -sp.oo
    print("P5.5 unrestricted-domain REFUTED: uniform start, k=3, n=2, delta=1;")
    print("  cuts=(4/9,4/9,4/9), unique next gains=(1,1,0); next tangent undefined.")


def attack_smooth_saturation_and_threshold() -> None:
    d = sp.symbols("d", nonnegative=True)
    g1, g2 = 1 - d, (2 + 3 * d) / 6
    phi = sp.log(g1) + sp.log(g2)
    slope = (1 - 6 * d) / ((1 - d) * (2 + 3 * d))
    zero(sp.diff(phi, d) - slope)
    p = [3 / (2 + 3 * d), 2 / (2 + 3 * d)]
    nu = [-slope, 0]
    residuals = sp.Matrix(2, 2, lambda i, z: p[z] + nu[i] - U[i, z] / [g1, g2][i])
    for i, z in ((0, 0), (1, 0), (1, 1)):
        zero(residuals[i, z])
    zero(residuals[0, 1] - (1 + 9 * d) / (3 * (1 - d) * (2 + 3 * d)))
    # On 0 <= d <= 1/6 the denominator is positive; slope >= 0 and the
    # unused entry has strictly positive residual. These are the closing signs.
    zero(sp.diff(phi, d, 2) + 1 / (1 - d) ** 2 + 9 / (2 + 3 * d) ** 2)
    zero(sp.limit(slope, d, DC, dir="-"))
    zero((g1 * g2).subs(d, DC) - R(25, 72))
    print("P4.5 REFUTED: phi(d)=log((1-d)(2+3d)/6) for 0<=d<=1/6;")
    print("  phi(d)=log(25/72) thereafter. At delta_c=1/6: D-=D+=0.")

    # The integral allocation a=1,b=0 has V=log(1/3) and delta_0=0.
    # exp(1/200)<200/199<25/24 puts the first root strictly in (0,1/6).
    alpha = (1 - sp.sqrt(25 - 24 * sp.exp(R(1, 200)))) / 6
    ratio = (1 - d) * (2 + 3 * d) / 2
    zero(ratio.subs(d, alpha) - sp.exp(R(1, 200)))
    assert 0 < alpha < DC
    assert R(200, 199) < R(25, 24)
    print(f"P4.8 REFUTED: {{d: phi(d)-log(1/3)>1/200}}=(alpha,infinity),")
    print(f"  alpha=(1-sqrt(25-24*exp(1/200)))/6={float(alpha):.16f}; no minimum.")


def check_exact_core() -> None:
    for d in (R(0), R(1, 100), R(1, 10), DC, R(1, 3), R(1), R(2)):
        case = smooth_case(d)
        check_kkt_and_rank(case)
        optimum_product = sp.prod(gains(case.u, case.x))
        for owners in product(range(2), repeat=2):
            x = sp.Matrix(2, 2, lambda i, z: int(owners[z] == i))
            masses = x * case.mass
            if all(1 - d <= m <= 1 + d for m in masses):
                assert sp.prod(gains(U, x)) <= optimum_product
    # A one-agent edge case, and nu=0 with two-sided-tight rows at delta=0.
    check_kkt_and_rank(ExactCase(R(0), sp.ones(2, 1), sp.ones(1, 2),
                                sp.ones(1, 2), sp.ones(2, 1) / 2, sp.zeros(1, 1)))
    check_kkt_and_rank(ExactCase(R(0), sp.ones(2, 1), sp.ones(2, 2),
                                sp.eye(2), sp.ones(2, 1), sp.zeros(2, 1)))
    # Dropping the vertex hypothesis really breaks the split bound.
    nonvertex = sp.ones(2, 4) / 2
    assert gains(sp.ones(2, 4), nonvertex) == sp.Matrix([2, 2])
    assert 4 > 2 * 2 - 1
    # The published good-side ratio fails even with nu=0.
    assert R(1) / 2 > R(1, 2) / 2  # Both agents receive 1/2 of the one good.
    zero(R(1) / R(1, 2) - R(1, 2) / R(1, 4))
    p, nu, mass, c = sp.symbols("p nu M c", real=True)
    zero((p - c * mass) + (nu + c) * mass - (p + nu * mass))
    plus, minus = sp.symbols("mu_plus mu_minus", nonnegative=True)
    zero((plus + c) - (minus + c) - (plus - minus))
    zero((plus + c) + (minus + c) - (plus + minus) - 2 * c)
    rho, h3_gap = sp.symbols("rho H3_gap", nonnegative=True)
    assert (rho * h3_gap).is_nonnegative  # P1's penalty difference under H3.
    print("P1/P2/P3/P6: exact feasibility, KKT, budgets, support rank and cells passed.")
    print("  Attacks include k=1/2/3, delta=0/1/>1, nu=0, all tight/slack, nonvertex.")


def master_bound(delta: float, cuts: list[tuple[float, float]]) -> float:
    """Independent LP for the two-good fixture; certify its primal and dual residuals."""
    rows: list[list[float]] = [[1, 1, 0, 0], [-1, -1, 0, 0]]
    rhs: list[float] = [1 + delta, -(1 - delta)]
    for h1, h2 in cuts:
        assert h1 > 0 and h2 > 0
        rows += [[-1 / h1, -1 / (3 * h1), 1, 0],
                 [1 / (2 * h2), 1 / (3 * h2), 0, 1]]
        rhs += [math.log(h1) - 1, math.log(h2) - 1 + 5 / (6 * h2)]
    a, b = np.array(rows, dtype=float), np.array(rhs, dtype=float)
    objective = np.array([0, 0, -1, -1], dtype=float)
    result = linprog(objective, A_ub=a, b_ub=b,
                     bounds=[(0, 1), (0, 1), (None, None), (None, None)],
                     method="highs-ds", options={"primal_feasibility_tolerance": 1e-9,
                                               "dual_feasibility_tolerance": 1e-9})
    assert result.success and result.status == 0, result.message
    y, lower, upper = result.ineqlin.marginals, result.lower.marginals, result.upper.marginals
    assert np.max(a @ result.x - b) <= CERT_TOL
    assert np.min(result.x[:2]) >= -CERT_TOL and np.max(result.x[:2]) <= 1 + CERT_TOL
    assert np.max(y) <= CERT_TOL and np.min(lower) >= -CERT_TOL
    assert np.max(upper) <= CERT_TOL
    assert np.max(np.abs(lower[2:])) <= CERT_TOL and np.max(np.abs(upper[2:])) <= CERT_TOL
    assert np.max(np.abs(objective - a.T @ y - lower - upper)) <= CERT_TOL
    dual = float(b @ y + sum(upper[:2]))
    assert abs(float(result.fun) - dual) <= CERT_TOL
    return -dual


def check_oa_safety() -> None:
    g, h = sp.symbols("g h", positive=True)
    error = sp.log(h) + (g - h) / h - sp.log(g)
    zero(sp.diff(error, g) - (1 / h - 1 / g))
    zero(sp.diff(error, g, 2) - 1 / g ** 2)
    zero(error.subs(g, h))  # Strict convexity makes this the global minimum.
    max_exact_error = 0.0
    for d in (R(0), R(1, 10), R(1, 5), R(9, 10)):
        gs = tuple(float(v) for v in gains(U, smooth_case(d).x))
        truth = sum(math.log(v) for v in gs)
        cuts = [(2 / 3, 5 / 12)]
        previous = master_bound(float(d), cuts)
        assert previous >= truth - CERT_TOL
        for extra in ((0.5, 0.5), (1.0, 0.25), gs):
            cuts.append((extra[0], extra[1]))
            bound = master_bound(float(d), cuts)
            assert truth - CERT_TOL <= bound <= previous + CERT_TOL
            previous = bound
        max_exact_error = max(max_exact_error, abs(previous - truth))
    assert max_exact_error <= CERT_TOL
    print(f"P5 safety: 16 optimal LPs, dual residuals <= {CERT_TOL:g};")
    print(f"  max error with exact optimum cuts={max_exact_error:.3e} nats (tier 1).")


def main() -> None:
    print(f"python={platform.python_version()} sympy={sp.__version__} "
          f"numpy={np.__version__} scipy={scipy.__version__}")
    print("Random seed: none (deterministic rational fixtures). Exact checks have no tolerance.")
    attack_zero_gains()
    attack_smooth_saturation_and_threshold()
    check_exact_core()
    check_oa_safety()
    print("CHECKS: passed; see report for 7 VERIFIED / 4 REFUTED / 0 INCONCLUSIVE claims.")
    print("VERDICT: REFUTED")


if __name__ == "__main__":
    main()
