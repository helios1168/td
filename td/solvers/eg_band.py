"""eg_band.py -- `EG^bal_S(delta)`, the band-constrained Eisenberg-Gale fibre (unit U8-band).

    EG^bal_S(delta) = max_X  sum_i log g_i(X),      g_i(X) = sum_z u_i(z) x_zi
         s.t.  sum_i x_zi = 1                 for every zip z        [duals p_z, free]
               sum_z M_z x_zi <= (1+d) T/k    for every agent i      [duals mu_i^+ >= 0]
               sum_z M_z x_zi >= (1-d) T/k    for every agent i      [duals mu_i^- >= 0]
               x >= 0

`docs/MODEL_U8-band.md` is the spec.  The value upper-bounds `V` for every **integral** coverage
at roster `S` whose districts respect the band, because such a coverage's indicator matrix is
feasible here (`MODEL_U1-cert` P1 plus one feasibility check).  `delta=None` drops the band rows
and gives the unconstrained fibre `EG_S`.

Three things this module produces, in decreasing order of how much trust they need
---------------------------------------------------------------------------------
``eg_band_dual_bound``   arithmetic, `O(nk)`, **no solver in the trusted path**.  For any
                         `mu^± >= 0` and any `p` making `q_zi = p_z + nu_i M_z` positive,

                             D = sum_z p_z + sum_i (log r_i - 1)
                                 + (T/k) sum_i [(1+d) mu_i^+ - (1-d) mu_i^-],
                             r_i = max_z u_i(z) / q_zi

                         is an upper bound on `EG^bal_S(delta)` by weak duality, whatever
                         produced the multipliers.  Only `mu >= 0` and `q > 0` are needed -- not
                         optimality, not convergence, not a solver's word for anything.  At
                         `mu = 0` it is exactly `docs/artifacts/U1-cert/eg.py::eg_dual`.

``solve_band``           the LP outer approximation on HiGHS.  Epigraph variables `t_i` and
                         tangent rows `t_i <= log ghat_i + (g_i - ghat_i)/ghat_i`.  Every tangent
                         is a *global* overestimator of `log`, so the master optimum is a valid
                         upper bound on `EG^bal(delta)` **at every iteration**, not only at
                         convergence -- that is the safety property the whole architecture rests
                         on.  The master's own `x` is feasible for the true program, so
                         `sum_i log g_i(x)` is a matching lower bound and the pair is a bracket.
                         The master's band duals are a supergradient of a concave majorant of
                         `EG^bal`, so ``BandSolution.curve_bound`` is valid at every iteration too
                         (`MODEL_U8-band.md` §4).

``solve_scip``           SCIP with native `log` through its expression graph, the independent
                         second solver.  `limits/gap 0.0` and `limits/absgap 0.0` (trap 12),
                         dual reductions off (trap 14), and only ``getDualbound()`` is read.  A
                         `timelimit` or any non-optimal stop returns `dual_bound=None` -- no
                         bound, never a bound (trap 15).

The `(0, None)` bounds trap
---------------------------
Every LP here bounds `x` by `[0, inf)`, never `[0, 1]`.  The feasible sets are identical, since
`sum_i x_zi = 1` with `x >= 0` already forces `x_zi <= 1`, but an explicit upper bound lets HiGHS
park a reduced cost on it and the returned duals then violate dual feasibility by an arbitrary
amount -- measured at `-0.80` with `[0, 1]` against `-5e-17` with `[0, inf)` on the real k=13
instance (`td/solvers/centers.py:316-322`).
"""
from __future__ import annotations

import itertools
import math
import time
from dataclasses import dataclass
from typing import Any, Iterator, Sequence

import numpy as np
from scipy import sparse
from scipy.optimize import linprog

CERT_TOL: float = 1e-8               # tier 1, in nats (CLAUDE.md "Two-tier acceptance")
MAX_CUTS: int = 200                  # the unit's stop rule; not a tuning knob
DUAL_TOL: float = 1e-7               # relative, for the O(nk) dual-feasibility verdict
SUPPORT_TOL: float = 1e-9            # the raw dirt floor; only ever used for the "before" count
CLEAN_TOL: float = 1e-6              # VERIFY_U9-bandthm §10.B: count splits above this, cleaned
BAND_TOL: float = 1e-9               # relative slack below this counts a band row as tight
STALL_TOL: float = 1e-15             # improvement in the master value below this is no progress
STALL_ROUNDS: int = 5
LP_TOL_LADDER: tuple[float | None, ...] = (1e-9, 1e-8, None)   # trap 14's retry ladder
SCIP_TIME_LIMIT: float = 1800.0
SCIP_FEASTOL: float = 1e-9


# ------------------------------------------------------------------------ the dual vector
@dataclass(frozen=True)
class BandDuals:
    """`(p, mu^+, mu^-)` in the program's own sign convention: both `mu` families are `>= 0`."""

    p: np.ndarray                    # (n,) supply duals, free in sign
    mu_plus: np.ndarray              # (k,) upper band
    mu_minus: np.ndarray             # (k,) lower band

    @property
    def nu(self) -> np.ndarray:
        """`nu_i = mu_i^+ - mu_i^-`, the net band multiplier, in nats per unit of `M`."""
        return np.asarray(self.mu_plus, float) - np.asarray(self.mu_minus, float)

    def prices(self, M: np.ndarray) -> np.ndarray:
        """`q[z, i] = p_z + nu_i M_z`, the agent-specific effective price (§2.10)."""
        M = np.asarray(M, float)
        return np.asarray(self.p, float)[:, None] + M[:, None] * self.nu[None, :]


@dataclass(frozen=True)
class DualCheck:
    """The solver-free `O(nk)` verdict on a dual vector, in `cert_power_diagram`'s contract.

    `feasible` is what makes `bound` a bound: weak duality needs only `mu >= 0` and `q > 0`.
    The `reduced` / complementary-slackness residuals are *quality* diagnostics -- they say how
    close the multipliers are to optimal, not whether the bound holds.
    """

    bound: float                     # D(p, mu), a valid upper bound iff `feasible`
    min_price: float                 # min_zi q_zi; must be > 0 for D to be finite
    min_mu: float                    # min over both band families; must be >= 0
    dual_violation: float            # min(reduced.min(), 0), reduced = q - u/g
    dual_violation_rel: float
    cs_residual_rel: float           # |reduced| on supp(X), relative
    band_cs_residual_rel: float      # mu^+ (hi - m) and mu^- (m - lo), relative to |primal|
    budget_residual: float           # max_i |sum_z p_z x_zi - (1 - nu_i m_i)|
    feasible: bool


@dataclass(frozen=True)
class VertexReport:
    """Is the returned point a vertex of the optimal face, and is its split count real?

    `VERIFY_U9-bandthm` §10.B: a support threshold below the solver's dirt floor manufactures
    phantom splits -- `math-verify` reproduced 108 apparent violations of the `k-1+t` bound
    across 517 vertices at `x > 1e-9`, and every one dissolved on cleaning.  So the vertex is
    cleaned at `1e-6` and renormalised before anything is counted, and `clean_*` record what
    that cost: if `g` moved or a mass left the band, the cleaned point is not the solved one and
    the counts below are not about it.

    The rank test is the sharp form.  The optimal face is cut out by the `n` supply rows, the
    `t` tight band rows and the `k` gain rows, so a vertex of it has
    `|supp| <= n + t + k - 1` (one dependency), i.e. `splits <= k - 1 + t <= 2k - 1` -- U9's
    P3-split, whose `-1` is now unconditional (`VERIFY_U9-bandthm` §10.F).
    """

    n_support: int
    n_split: int                     # zips carried by two or more agents, after cleaning
    n_split_raw: int                 # before cleaning -- the difference is solver dirt
    n_tight_bands: int               # `t`, counting rows: an agent may contribute at most one
    tight_agents: tuple[int, ...]
    n_agents_band_slack: int         # agents with both bands slack, hence `nu_i = 0` forced
    gauge_pinned: bool               # one strictly slack agent pins `p` and `nu` (U9 P2b)
    expected: int                    # n + k - 1 + t
    split_cap: int                   # k - 1 + t
    rank: int | None                 # rank of (supply | tight bands | gains) on the support
    is_vertex: bool | None           # rank == |supp|
    clean_max_g_rel: float           # max_i |g_clean - g| / g
    clean_max_band_violation: float  # worst excursion outside [lo, hi] after cleaning, relative
    degenerate: bool


@dataclass(frozen=True)
class FirstMovers:
    """Zips ranked by the good-side selection margin: the near-ties flip owner first.

    The rule is `MODEL_U9-bandthm` **P2.5**, not `DOMAIN_optimization` §2.12 as published.
    Stationarity of `EG^bal` reads `u_i(z)/g_i - nu_i M_z <= p_z` with equality on `supp(X)`,
    so the good-side score is the **additive** `u_i(z)/g_i - nu_i M_z`, whose maximum over `i`
    is exactly `p_z`.  §2.12's ratio form `u_i(z)/q_zi` drops the `1/g_i` normalisation and is
    already false at `nu = 0`, where `argmax_i u_i(z)/p_z` collapses to `argmax_i u_i(z)`.
    U9 measured the published form failing on 6 of 9 zips (toy2) and 5 of 6 (toy3).
    """

    order: np.ndarray                # (n,) zip indices, increasing margin
    margin: np.ndarray               # (n,) (best - runner-up) / |best|, scale-free per zip
    margin_abs: np.ndarray           # (n,) best - runner-up, in the units of p_z
    best: np.ndarray                 # (n,) max_i score = p_z at an optimum
    owner: np.ndarray                # (n,) argmax agent
    runner_up: np.ndarray            # (n,) second-best agent            # (n,) second-best agent


# ------------------------------------------------------------------------ the solves
@dataclass(frozen=True)
class BandSolution:
    """One `EG^bal_S(delta)` solve: a bracket, the duals, and the cut pool to carry onward."""

    delta: float | None              # None = the band rows were dropped (the `EG_S` fibre)
    X: np.ndarray                    # (n, k) the master's allocation
    g: np.ndarray                    # (k,) gains at `X`
    m: np.ndarray                    # (k,) district masses at `X`
    primal: float                    # sum_i log g_i -- a valid LOWER bound
    upper: float                     # the master optimum -- a valid UPPER bound
    slope: float                     # (T/k) sum_i |nu_i| -- the CANONICAL supergradient
    slope_raw: float                 # (T/k) sum_i (mu_i^+ + mu_i^-) -- solver-dependent
    duals: BandDuals
    cuts: np.ndarray                 # (R, k) the tangent points, valid at every delta
    n_cuts: int
    lp_tol: float | None             # the tolerance rung the master actually solved at
    polish_delta: float              # P5.4 re-solve minus the pool's value; <= 0 means adopted
    converged: bool
    status: str

    @property
    def bracket(self) -> float:
        """`upper - primal`, in nats.  Tier 1 is `<= 1e-8`."""
        return float(self.upper - self.primal)

    def curve_bound(self, delta_prime: float) -> float:
        """`upper + slope * (delta' - delta)` -- valid for every `delta'` by concavity (§4).

        `slope` is the **minimised** aggregate `(T/k) sum_i |nu_i|`, not the raw
        `(T/k) sum_i (mu_i^+ + mu_i^-)` HiGHS returns (`MODEL_U9-bandthm` P4.3).  Every optimal
        dual gives a valid supergradient, but the raw aggregate is unbounded above at `delta = 0`
        -- adding `c >= 0` to both multipliers of a two-sided-tight agent changes nothing else --
        so it is neither the tightest certificate nor a reproducible number.  At `delta > 0`
        complementary slackness makes at most one of `mu_i^±` positive at any optimal dual, so
        the two agree; `slope_raw` is carried beside `slope` to show that they do.
        """
        if self.delta is None:
            return float(self.upper)           # the band was dropped: the curve is flat above
        return float(self.upper + self.slope * (float(delta_prime) - self.delta))


@dataclass(frozen=True)
class ScipBound:
    """SCIP's dual bound, or `None`.  A non-optimal stop is no bound, never a bound (trap 15)."""

    delta: float | None
    dual_bound: float | None
    primal_bound: float | None
    status: str
    seconds: float
    settings: dict[str, Any]


def band_rhs(M: np.ndarray, k: int, delta: float) -> tuple[float, float]:
    """`(lo, hi) = ((1-delta) T/k, (1+delta) T/k)`, the band's right-hand side."""
    target = float(np.asarray(M, float).sum()) / float(k)
    return (1.0 - float(delta)) * target, (1.0 + float(delta)) * target


def eg_band_dual_bound(U: np.ndarray, M: np.ndarray, delta: float | None,
                       duals: BandDuals) -> float:
    """`D(p, mu)` -- weak duality, `O(nk)`, no solver.  `inf` if `q` is not positive."""
    U = np.asarray(U, float)
    M = np.asarray(M, float)
    k = U.shape[1]
    mu_p = np.asarray(duals.mu_plus, float)
    mu_m = np.asarray(duals.mu_minus, float)
    if delta is None and (np.any(mu_p != 0.0) or np.any(mu_m != 0.0)):
        raise ValueError("delta=None drops the band rows; their multipliers must be zero")
    if np.any(mu_p < 0.0) or np.any(mu_m < 0.0):
        return math.inf                        # not dual feasible: no bound
    q = duals.prices(M)
    if np.any(q <= 0.0):
        return math.inf                        # the inner sup is unbounded
    r = (U / q).max(axis=0)
    d = math.fsum(np.asarray(duals.p, float).tolist()) + math.fsum(np.log(r).tolist()) - k
    if delta is not None:
        lo, hi = band_rhs(M, k, delta)
        d += float(hi * mu_p.sum() - lo * mu_m.sum())
    return float(d)


def check_dual(U: np.ndarray, M: np.ndarray, delta: float | None, X: np.ndarray,
               g: np.ndarray, duals: BandDuals, *, tol: float = DUAL_TOL) -> DualCheck:
    """Verify the multipliers against all `nk` stationarity rows and the `2k` band rows."""
    U = np.asarray(U, float)
    M = np.asarray(M, float)
    X = np.asarray(X, float)
    g = np.asarray(g, float)
    k = U.shape[1]
    q = duals.prices(M)
    reduced = q - U / g[None, :]               # >= 0 at a KKT point, == 0 on supp(X)
    scale = float(np.abs(q).max()) or 1.0
    support = X > SUPPORT_TOL
    primal = float(np.log(g).sum())

    m = (M[:, None] * X).sum(axis=0)
    band_cs = 0.0
    if delta is not None:
        lo, hi = band_rhs(M, k, delta)
        band_cs = float(max(np.abs(duals.mu_plus * (hi - m)).max(),
                            np.abs(duals.mu_minus * (m - lo)).max()))
    budget = float(np.abs((np.asarray(duals.p, float)[:, None] * X).sum(axis=0)
                          - (1.0 - duals.nu * m)).max())

    min_mu = float(min(np.min(duals.mu_plus, initial=0.0),
                       np.min(duals.mu_minus, initial=0.0)))
    min_price = float(q.min())
    return DualCheck(
        bound=eg_band_dual_bound(U, M, delta, duals),
        min_price=min_price,
        min_mu=min_mu,
        dual_violation=float(min(reduced.min(), 0.0)),
        dual_violation_rel=float(min(reduced.min(), 0.0) / scale),
        cs_residual_rel=(float(np.abs(reduced[support]).max() / scale)
                         if support.any() else 0.0),
        band_cs_residual_rel=float(band_cs / max(abs(primal), 1.0)),
        budget_residual=budget,
        feasible=bool(min_price > 0.0 and min_mu >= -tol * scale),
    )


def clean_vertex(X: np.ndarray, *, tol: float = CLEAN_TOL) -> np.ndarray:
    """Zero every share below `tol` and renormalise each zip's row back to one.

    `VERIFY_U9-bandthm` §10.B: counting splits at the solver's dirt floor invents them.  Whether
    the cleaning was free is not assumed -- `vertex_report` recomputes `g` and the masses on the
    cleaned point and reports how far they moved.
    """
    X = np.asarray(X, float).copy()
    X[X < tol] = 0.0
    row = X.sum(axis=1, keepdims=True)
    return np.divide(X, row, out=np.zeros_like(X), where=row > 0.0)


def vertex_report(X: np.ndarray, U: np.ndarray, M: np.ndarray, g: np.ndarray,
                  lo: float, hi: float, *, clean_tol: float = CLEAN_TOL,
                  band_tol: float = BAND_TOL, rank: bool = True) -> VertexReport:
    """Clean the vertex, then count splits, tight bands and the rank of the optimal face."""
    X = np.asarray(X, float)
    U = np.asarray(U, float)
    M = np.asarray(M, float)
    n, k = X.shape

    n_split_raw = int(((X > SUPPORT_TOL).sum(axis=1) >= 2).sum())
    Xc = clean_vertex(X, tol=clean_tol)
    gc = (U * Xc).sum(axis=0)
    mc = (M[:, None] * Xc).sum(axis=0)
    span = max(abs(hi), abs(lo), 1.0)
    slack = band_tol * span
    tight = tuple(int(i) for i in range(k)
                  if (hi - mc[i]) <= slack or (mc[i] - lo) <= slack)
    strictly_slack = int(sum(1 for i in range(k)
                             if (hi - mc[i]) > slack and (mc[i] - lo) > slack))

    supp = Xc > clean_tol
    n_support = int(supp.sum())
    n_split = int((supp.sum(axis=1) >= 2).sum())
    t = len(tight)

    rk: int | None = None
    if rank and n_support:
        zs, ags = np.nonzero(supp)
        A = np.zeros((n + t + k, n_support))
        A[zs, np.arange(n_support)] = 1.0                       # supply rows
        for r, i in enumerate(tight):
            A[n + r, ags == i] = M[zs[ags == i]]                # tight band rows
        for i in range(k):
            A[n + t + i, ags == i] = U[zs[ags == i], i]         # gain rows
        rk = int(np.linalg.matrix_rank(A))

    return VertexReport(
        n_support=n_support, n_split=n_split, n_split_raw=n_split_raw,
        n_tight_bands=t, tight_agents=tight, n_agents_band_slack=strictly_slack,
        gauge_pinned=bool(strictly_slack >= 1),
        expected=n + k - 1 + t, split_cap=k - 1 + t,
        rank=rk, is_vertex=None if rk is None else bool(rk == n_support),
        clean_max_g_rel=float(np.abs(gc - g).max() / max(float(np.abs(g).min()), 1e-300)),
        clean_max_band_violation=float(max(0.0, (mc - hi).max(), (lo - mc).max()) / span),
        degenerate=bool(n_support != n + k - 1 + t))


def good_side_scores(U: np.ndarray, M: np.ndarray, g: np.ndarray,
                     duals: BandDuals) -> np.ndarray:
    """`score[z, i] = u_i(z)/g_i - nu_i M_z`; `max_i score[z, i] = p_z` at an optimum (P2.5)."""
    U = np.asarray(U, float)
    M = np.asarray(M, float)
    return U / np.asarray(g, float)[None, :] - M[:, None] * duals.nu[None, :]


def first_movers(U: np.ndarray, M: np.ndarray, g: np.ndarray,
                 duals: BandDuals) -> FirstMovers:
    """Rank zips by the P2.5 good-side margin -- the near-ties move first as `delta` moves."""
    score = good_side_scores(U, M, g, duals)
    # sort the negated scores stably rather than reversing an ascending sort: on an exact tie
    # the reversed form picks the LAST tied agent and disagrees with `argmax`, which makes the
    # owner column depend on nothing but tie order.  Stable-on-negated breaks ties by lowest
    # agent index, deterministically, which acceptance 5's byte-identical re-run needs.
    order_i = np.argsort(-score, axis=1, kind="stable")     # best first
    best = np.take_along_axis(score, order_i[:, :1], axis=1)[:, 0]
    second = np.take_along_axis(score, order_i[:, 1:2], axis=1)[:, 0]
    gap = best - second
    margin = gap / np.where(np.abs(best) > 0.0, np.abs(best), 1.0)
    return FirstMovers(order=np.argsort(margin, kind="stable"), margin=margin,
                       margin_abs=gap, best=best,
                       owner=order_i[:, 0], runner_up=order_i[:, 1])


# ------------------------------------------------------------------------ the OA master
def _tangent_rows(U: np.ndarray, ghat: np.ndarray) -> tuple[sparse.coo_matrix, np.ndarray]:
    """`t_i - g_i/ghat_i <= log ghat_i - 1`, one row per agent, over `[t | x]`."""
    n, k = U.shape
    rows = np.concatenate([np.arange(k), np.tile(np.arange(k), n)])
    cols = np.concatenate([np.arange(k), k + np.arange(n * k)])
    data = np.concatenate([np.ones(k), -(U / ghat[None, :]).ravel()])
    A = sparse.coo_matrix((data, (rows, cols)), shape=(k, k + n * k))
    return A, np.log(ghat) - 1.0


def _solve_master(c: np.ndarray, A_ub: Any, b_ub: np.ndarray, A_eq: Any, b_eq: np.ndarray,
                  bounds: list[tuple[float | None, float | None]], rung: int) -> tuple[Any, int]:
    """The master LP, down the tolerance ladder of trap 14 on any HiGHS "Solve error".

    The ladder is not a tuning knob: the cut loop stalls at the LP's own primal feasibility
    tolerance, because a cut violated by less than it is not seen as violated at all.  Measured
    on the `MODEL_U7-meas` toy: the bracket floors at `6.7e-8` under the `1e-7` default,
    `1.7e-9` at `1e-9`.  Tier 1 needs the tight rung; trap 14 says HiGHS 1.15 can answer
    "Solve error" there, so a failed rung falls through instead of aborting.
    """
    message = "no tolerance rung attempted"
    for idx in range(rung, len(LP_TOL_LADDER)):
        tol = LP_TOL_LADDER[idx]
        opts = (None if tol is None
                else dict(primal_feasibility_tolerance=tol, dual_feasibility_tolerance=tol))
        res = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds,
                      method="highs-ds", options=opts)
        if res.success:
            return res, idx
        message = str(res.message)
    raise RuntimeError(f"EG^bal master LP failed at every tolerance rung: {message}")


def solve_band(U: np.ndarray, M: np.ndarray, delta: float | None, *,
               cuts: np.ndarray | None = None, max_cuts: int = MAX_CUTS,
               tol: float = CERT_TOL) -> BandSolution:
    """LP outer approximation for `EG^bal_S(delta)`; `delta=None` drops the band rows.

    `cuts` is a `(R, k)` pool of tangent points from a previous solve.  Tangents are valid at
    every `delta` -- only the band right-hand side moves -- so carrying the pool across the grid
    is what makes the frontier cheap.
    """
    U = np.asarray(U, float)
    M = np.asarray(M, float)
    n, k = U.shape
    if M.shape != (n,):
        raise ValueError(f"M has shape {M.shape}, expected ({n},)")
    if (U <= 0.0).any():
        raise ValueError("every u_i(z) must be positive: the tangents need g > 0")

    ncol = k + n * k
    zip_of = np.repeat(np.arange(n), k)
    agent_of = np.tile(np.arange(k), n)
    A_eq = sparse.coo_matrix((np.ones(n * k), (zip_of, k + np.arange(n * k))),
                             shape=(n, ncol)).tocsc()
    b_eq = np.ones(n)

    band: list[sparse.coo_matrix] = []
    b_band = np.zeros(0)
    if delta is not None:
        lo, hi = band_rhs(M, k, delta)
        mass = sparse.coo_matrix((np.repeat(M, k), (agent_of, k + np.arange(n * k))),
                                 shape=(k, ncol))
        band = [mass, sparse.coo_matrix((-mass.data, (mass.row, mass.col)), shape=(k, ncol))]
        b_band = np.concatenate([np.full(k, hi), np.full(k, -lo)])

    c = np.concatenate([-np.ones(k), np.zeros(n * k)])
    bounds: list[tuple[float | None, float | None]] = (
        [(None, None)] * k + [(0.0, None)] * (n * k))

    pool = ([np.asarray(row, float) for row in np.atleast_2d(np.asarray(cuts, float))]
            if cuts is not None and np.size(cuts) else [])
    if not pool:
        # the Slater point x == 1/k (§2.10), so ghat_i = u_i(Z)/k exactly -- not a heuristic.
        # P5.3's floor `g_i >= lam (1-delta) T/k` is the guarantee that every iterate stays
        # positive; assert the seed clears it rather than substituting the weaker constant.
        pool = [(U * np.full((n, k), 1.0 / k)).sum(axis=0)]
    if min(float(np.min(ghat)) for ghat in pool) <= 0.0:
        raise ValueError("every tangent point needs ghat > 0 (MODEL_U9-bandthm P5.3)")
    rows, rhs = [], []
    for ghat in pool:
        A, b = _tangent_rows(U, ghat)
        rows.append(A)
        rhs.append(b)

    X = np.zeros((n, k))
    g = np.zeros(k)
    upper = math.inf
    primal = -math.inf
    p = np.zeros(n)
    mu_p = np.zeros(k)
    mu_m = np.zeros(k)
    status = "no solve"
    converged = False
    rung = 0
    stall = 0
    prev = math.inf

    while True:
        res, rung = _solve_master(c, sparse.vstack(band + rows).tocsc(),
                                  np.concatenate([b_band] + rhs), A_eq, b_eq, bounds, rung)
        upper = float(-res.fun)
        X = np.asarray(res.x, float)[k:].reshape(n, k)
        g = (U * X).sum(axis=0)
        primal = float(np.log(g).sum()) if (g > 0.0).all() else -math.inf
        p = -np.asarray(res.eqlin.marginals, float)
        if delta is not None:
            ineq = -np.asarray(res.ineqlin.marginals, float)
            mu_p = np.maximum(ineq[:k], 0.0)          # clipping keeps weak duality airtight
            mu_m = np.maximum(ineq[k:2 * k], 0.0)
        status = "optimal"

        if upper - primal <= tol:
            converged = True
            break
        stall = stall + 1 if prev - upper <= STALL_TOL else 0
        prev = min(prev, upper)
        if stall >= STALL_ROUNDS:
            status = (f"stalled at the LP tolerance floor after {len(pool)} tangents, "
                      f"bracket {upper - primal:.3e} nats")
            break
        if len(pool) >= max_cuts:
            status = (f"cut limit: {max_cuts} tangents, bracket {upper - primal:.3e} nats")
            break
        pool.append(g.copy())
        A, b = _tangent_rows(U, g)
        rows.append(A)
        rhs.append(b)

    # P5.4: a single tangent per agent placed at `g*` makes the master EXACT, and its duals ARE
    # the original program's `(p, mu^±)` -- the accumulated pool's are only asymptotically so.
    # The polish solve is one LP, and it is adopted only when it does not loosen the bound, so
    # the reported `(upper, slope)` stay a matched pair from one concave majorant.
    polish_delta = math.nan
    if converged:
        A, b = _tangent_rows(U, g)
        res_p, rung = _solve_master(c, sparse.vstack(band + [A]).tocsc(),
                                    np.concatenate([b_band, b]), A_eq, b_eq, bounds, rung)
        upper_p = float(-res_p.fun)
        X_p = np.asarray(res_p.x, float)[k:].reshape(n, k)
        g_p = (U * X_p).sum(axis=0)
        polish_delta = upper_p - upper
        if (g_p > 0.0).all() and upper_p <= upper:
            upper, X, g = upper_p, X_p, g_p
            primal = float(np.log(g).sum())
            p = -np.asarray(res_p.eqlin.marginals, float)
            if delta is not None:
                ineq = -np.asarray(res_p.ineqlin.marginals, float)
                mu_p = np.maximum(ineq[:k], 0.0)
                mu_m = np.maximum(ineq[k:2 * k], 0.0)
            status = "optimal (P5.4-polished)"

    m = (M[:, None] * X).sum(axis=0)
    scale = float(M.sum()) / k
    nu = mu_p - mu_m
    return BandSolution(delta=None if delta is None else float(delta), X=X, g=g, m=m,
                        primal=primal, upper=upper,
                        slope=0.0 if delta is None else float(scale * np.abs(nu).sum()),
                        slope_raw=0.0 if delta is None else float(scale * (mu_p + mu_m).sum()),
                        duals=BandDuals(p=p, mu_plus=mu_p, mu_minus=mu_m),
                        cuts=np.array(pool, float), n_cuts=len(pool),
                        lp_tol=LP_TOL_LADDER[rung], polish_delta=float(polish_delta),
                        converged=converged, status=status)


# ------------------------------------------------------------------------ the cross-check
def solve_scip(U: np.ndarray, M: np.ndarray, delta: float | None, *,
               g_lower: np.ndarray | None = None,
               time_limit: float = SCIP_TIME_LIMIT,
               feastol: float = SCIP_FEASTOL) -> ScipBound:
    """The independent cross-check: SCIP's expression graph on the native `log`."""
    from pyscipopt import Model, log as scip_log, quicksum

    U = np.asarray(U, float)
    M = np.asarray(M, float)
    n, k = U.shape
    settings = {"limits/gap": 0.0, "limits/absgap": 0.0,
                "misc/allowstrongdualreds": False, "misc/allowweakdualreds": False,
                "numerics/feastol": float(feastol), "limits/time": float(time_limit)}

    sm = Model("EG_bal")
    sm.hideOutput()
    for key, val in settings.items():
        sm.setParam(key, val)

    x = [[sm.addVar(lb=0.0, ub=1.0, vtype="C") for _ in range(k)] for _ in range(n)]
    lo_g = (np.asarray(g_lower, float) if g_lower is not None
            else np.full(k, float(U.min()) * 1e-6))
    gv = [sm.addVar(lb=float(lo_g[i]), ub=float(U[:, i].sum()), vtype="C") for i in range(k)]

    for z in range(n):
        sm.addCons(quicksum(x[z][i] for i in range(k)) == 1.0)
    for i in range(k):
        # `<=`, never `==`: an equality lets presolve multi-aggregate the gain away (trap 14)
        sm.addCons(gv[i] <= quicksum(float(U[z, i]) * x[z][i] for z in range(n)))
    if delta is not None:
        lo, hi = band_rhs(M, k, delta)
        for i in range(k):
            mass = quicksum(float(M[z]) * x[z][i] for z in range(n))
            sm.addCons(mass <= hi)
            sm.addCons(mass >= lo)

    # the objective stays linear and `log` lives in a constraint: pyscipopt will not take a sum
    # of nonlinear expressions as an objective, and the epigraph form is the same program
    tv = [sm.addVar(lb=-sm.infinity(), ub=sm.infinity(), vtype="C") for _ in range(k)]
    for i in range(k):
        sm.addCons(tv[i] <= scip_log(gv[i]))
    sm.setObjective(quicksum(tv[i] for i in range(k)), "maximize")
    t0 = time.time()
    sm.optimize()
    seconds = time.time() - t0
    status = str(sm.getStatus())
    dual = float(sm.getDualbound())
    primal = float(sm.getPrimalbound())
    sm.freeProb()
    # trap 15: a timelimit / abort stop is NOT a bound, however plausible the number looks
    return ScipBound(delta=None if delta is None else float(delta),
                     dual_bound=dual if status == "optimal" else None,
                     primal_bound=primal if status == "optimal" else None,
                     status=status, seconds=seconds, settings=settings)


# ------------------------------------------------------------------------ the toy oracle
def _splits(steps: int, k: int) -> Iterator[tuple[float, ...]]:
    """Every way of dividing one unit of coverage into `steps` parts among `k` agents."""
    for cut in itertools.combinations(range(steps + k - 1), k - 1):
        prev = -1
        part = []
        for c in cut:
            part.append(c - prev - 1)
            prev = c
        part.append(steps + k - 2 - prev)
        yield tuple(v / steps for v in part)


def brute_force_band(U: np.ndarray, M: np.ndarray, delta: float | None, *,
                     steps: int) -> float:
    """`EG^bal` by exhaustive search over a grid of fractional splits -- the toy oracle only.

    `steps` divides each zip's unit of coverage into `steps` parts, so the search is
    `binom(steps + k - 1, k - 1) ** n`.  Usable at `n <= 4`, `k <= 3`; there for the tests.
    A grid search is a *lower* bound on the true optimum, so a test compares it as such.
    """
    U = np.asarray(U, float)
    M = np.asarray(M, float)
    n, k = U.shape
    grid = list(_splits(steps, k))
    lo, hi = (band_rhs(M, k, delta) if delta is not None else (-math.inf, math.inf))
    best = -math.inf
    for combo in itertools.product(grid, repeat=n):
        X = np.array(combo, float)
        m = (M[:, None] * X).sum(axis=0)
        if m.min() < lo - 1e-12 or m.max() > hi + 1e-12:
            continue
        g = (U * X).sum(axis=0)
        if (g <= 0.0).any():
            continue
        best = max(best, float(np.log(g).sum()))
    return best
