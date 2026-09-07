"""Shared machinery for unit U1-cert: the Eisenberg-Gale fibre program and its dual.

Nothing here is project code -- it is a throwaway artifact so that `math-verify` can re-run
every number in `docs/MODEL_U1-cert.md`.  Two things matter about the design:

1. **The reported bound never trusts the algorithm.**  `eg_solve` runs proportional-response
   dynamics, which is a heuristic as far as this unit is concerned.  What is *reported* is a
   pair: `primal` (the objective at a feasible fractional X -- a lower bound on EG_S by
   feasibility) and `dual` (the value of the Lagrangian dual at the iterate's prices -- an
   upper bound on EG_S by weak duality, valid for **any** strictly positive price vector).
   Both are checkable in O(nk) arithmetic from the returned arrays.
2. **Exact conventions.**  `u_i(z)` is the *unmasked* utility -- the one `td/channel.py`
   `gain_matrix` uses (every rep is evaluated on every zip, candidacy ignored), not
   `td/model.py` `utilities` (which zeroes non-candidates).  P1 compares like with like: the
   integral coverages it bounds are exactly the ones `channel.stage2` scores.

The dual, derived once here so the arithmetic is auditable.  Primal:

    max_{x >= 0}  sum_i log g_i(x),   g_i(x) = sum_z u_iz x_zi,   sum_i x_zi <= 1  for all z

Lagrangian on the supply rows with multipliers p_z >= 0:

    D(p) = sum_z p_z + sum_i max_{x_.i >= 0} [ log(sum_z u_iz x_zi) - sum_z p_z x_zi ]

For one agent, writing the spend s_z = p_z x_zi >= 0 gives sum_z u_iz x_zi <= r_i * sum_z s_z
with r_i = max_z u_iz / p_z, attained by spending only on an argmax good; then
max_{S >= 0} [log(r_i S) - S] = log r_i - 1 at S = 1.  Hence

    D(p) = sum_z p_z - k + sum_i log( max_z u_iz / p_z ),     EG <= D(p)  for every p > 0.

At u_iz = M_z and p_z = (k/T) M_z with T = sum_z M_z this is exactly k*log(T/k), the analytic
balance ceiling -- which is proposition P2.1.
"""
from __future__ import annotations

import numpy as np


# --------------------------------------------------------------------- the fibre program
def eg_primal(U: np.ndarray, X: np.ndarray) -> float:
    """`sum_i log g_i` at a feasible fractional assignment.  A lower bound on EG_S."""
    g = (U * X).sum(axis=0)
    return float(np.log(g).sum())


def eg_dual(U: np.ndarray, p: np.ndarray) -> float:
    """`sum_z p_z - k + sum_i log max_z (u_iz / p_z)`.  An upper bound on EG_S for any p > 0."""
    if np.any(p <= 0):
        raise ValueError("the dual bound needs strictly positive prices")
    k = U.shape[1]
    r = (U / p[:, None]).max(axis=0)
    return float(p.sum() - k + np.log(r).sum())


def eg_solve(U: np.ndarray, iters: int = 60_000):
    """Proportional response on the linear Fisher market with budgets 1.

    Returns `(X, p, g, primal, dual)`.  `primal <= EG_S <= dual` holds *whatever* the
    iteration did; the iteration only decides how tight the pair is.
    """
    n, k = U.shape
    B = np.ones(k)
    b = np.tile(B / n, (n, 1))                       # b[z, i] = agent i's spend on zip z
    for _ in range(iters):
        p = b.sum(axis=1)
        X = b / p[:, None]
        g = (U * X).sum(axis=0)
        b = B[None, :] * (U * X) / g[None, :]
    p = b.sum(axis=1)
    X = b / p[:, None]
    g = (U * X).sum(axis=0)
    return X, p, g, eg_primal(U, X), eg_dual(U, p)


def eg_vertex(U: np.ndarray, g_star: np.ndarray):
    """A vertex of `{x >= 0 : sum_i x_zi = 1, sum_z u_iz x_zi = g_star_i}`.

    The set of EG optima is exactly this polytope (the optimal gain vector is unique by strict
    concavity of `sum log` on the convex set of achievable gains), so a vertex of it is an EG
    optimum whose support has at most `rank` entries -- proposition P3a.  The rank is `n + k`
    in general and `n + k - 1` exactly when the `u_i` are mutually proportional, which is why
    the textbook `<= k - 1` split-unit count is a common-measure (tau = 0) statement and the
    honest heterogeneous bound is `<= k`.
    """
    from scipy import sparse
    from scipy.optimize import linprog

    n, k = U.shape
    cols = np.arange(n * k)
    place = sparse.coo_matrix((np.ones(n * k), (np.repeat(np.arange(n), k), cols)),
                              shape=(n, n * k))
    gain = sparse.coo_matrix((U.ravel(), (np.tile(np.arange(k), n), cols)), shape=(k, n * k))
    A = sparse.vstack([place, gain]).tocsc()
    b = np.concatenate([np.ones(n), np.asarray(g_star, float)])
    res = linprog(np.zeros(n * k), A_eq=A, b_eq=b, bounds=(0, None), method="highs-ds")
    if not res.success:
        raise RuntimeError(f"vertex LP failed: {res.message}")
    return np.asarray(res.x, float).reshape(n, k)


def eg_solve_penalised(M: np.ndarray, cost: np.ndarray, rho: float,
                       iters: int = 400_000, eta: float = 0.05):
    """The tau = 0 fibre with a *linear* geometric penalty, by entropic mirror ascent.

        max_X  sum_j log m_j - rho * sum_{z,j} cost_zj x_zj,
        m_j = sum_z M_z x_zj,   sum_j x_zj = 1,  x >= 0

    Concave, so mirror ascent on the product of simplices converges.  Returns `(X, m)`.
    Used only on the toy; the propositions it checks are stated and proved independently.
    """
    n, k = cost.shape
    X = np.full((n, k), 1.0 / k)
    for _ in range(iters):
        m = (M[:, None] * X).sum(axis=0)
        X = X * np.exp(eta * (M[:, None] / m[None, :] - rho * cost))
        X /= X.sum(axis=1, keepdims=True)
    return X, (M[:, None] * X).sum(axis=0)


# ------------------------------------------------------------------- the geometric penalty
def perimeter_tv(edges, X: np.ndarray) -> float:
    """`C_TV(X) = 1/2 sum_{(u,v) in E} sum_i |x_ui - x_vi|`.

    Convex, and **exact on integral X**: an edge whose endpoints share an owner contributes 0,
    an edge whose endpoints differ contributes 1/2 * 2 = 1.  So it is the convex extension of
    `td/model.py::perimeter` that hypothesis H3 of P1 asks for.
    """
    return 0.5 * sum(float(np.abs(X[u] - X[v]).sum()) for u, v in edges)


# --------------------------------------------------------------------------- toy instance
def toy(seed: int = 20260903):
    """A hand-built instance: 4 reps, 8 zips, k = 3, a path graph, planar coordinates.

    Deliberately small enough that every integral coverage can be enumerated
    (`C(4,3) * 3^8 = 26,244` of them) and every claim checked by exhaustion rather than by
    argument.  Books are chosen to sit well inside the headroom condition
    `M_z >= max_i (S_i + theta*(T_z - S_i))` so that `u_i(z) <= M_z` holds -- the hypothesis
    the balance ceiling needs (P2.1 corollary).
    """
    del seed                                     # the toy is fully deterministic
    zips = [f"Z{j}" for j in range(8)]
    reps = [f"R{i}" for i in range(4)]
    xy = np.array([[0.0, 0.0], [1.0, 0.2], [2.0, 0.1], [3.0, 0.0],
                   [0.2, 1.0], [1.1, 1.2], [2.2, 1.1], [3.1, 0.9]])
    M = np.array([10.0, 14.0, 9.0, 12.0, 11.0, 16.0, 8.0, 13.0])
    # per-rep books as a share of M, kept sparse and well under headroom
    share = np.zeros((8, 4))
    share[0, 0] = 0.35; share[0, 1] = 0.10
    share[1, 1] = 0.40
    share[2, 2] = 0.25; share[2, 0] = 0.05
    share[3, 3] = 0.30; share[3, 2] = 0.15
    share[4, 0] = 0.20
    share[5, 1] = 0.22; share[5, 3] = 0.18
    share[6, 2] = 0.30
    share[7, 3] = 0.45; share[7, 1] = 0.05
    S = share * M[:, None]
    edges = [(0, 1), (1, 2), (2, 3), (4, 5), (5, 6), (6, 7),
             (0, 4), (1, 5), (2, 6), (3, 7)]
    return dict(zips=zips, reps=reps, xy=xy, M=M, S=S, edges=edges, k=3)


def utilities(M: np.ndarray, S: np.ndarray, theta: float = 0.40, lam: float = 0.30,
              cols=None) -> np.ndarray:
    """`u_i(z) = c1 S_i + c2 (T_z - S_i) + lam M_z`, unmasked, in `td/channel.py`'s form."""
    c1, c2 = 1.0 - lam, theta * (1.0 - lam)
    T = S.sum(axis=1)
    common = c2 * T + lam * M
    U = common[:, None] + (c1 - c2) * S
    return U if cols is None else U[:, list(cols)]


def headroom_ok(M: np.ndarray, S: np.ndarray, theta: float = 0.40,
                lam: float = 0.30) -> bool:
    return bool((utilities(M, S, theta, lam).max(axis=1) <= M + 1e-12).all())
