"""centers.py -- stage 1: center-based balanced districting on planar coordinates.

Stage 1 draws `k` districts of roughly equal opportunity.  The decided model (2026-09-01) is
**center-based compact assignment**, not contiguous districting: the sold-zip adjacency of the
real instance is shattered (547 components over ~1,229 zips), so a contiguity constraint is
either vacuous or infeasible, and the honest geometric requirement is *compactness* -- each
district a tight cluster of zips around a center, on equal-area planar coordinates.

What the objective is
---------------------
Every zip lands in exactly one district, so `sum_j M_j` is partition-invariant and maximising
`sum_j log M_j` at fixed sum equalises the terms (`channel.py`): maximum Nash welfare on a
common measure **is** equal-size districting.  Balance is therefore the objective, and
compactness is the tie-breaker among near-balanced solutions -- which is exactly what a
capacitated k-means does::

    min sum_z sum_j M_z * d^2(z, c_j) * x_zj
    s.t. sum_j x_zj = 1 (every zip placed),  sum_z M_z * x_zj = (sum M)/k (equal mass),  x >= 0

The mass equalities are *hard*, so a draw is balanced by construction and the compactness cost
only picks among the balanced assignments.  Zips are indivisible, but the largest zip is ~1.1%
of total `M`, so near-perfect balance is reachable by rounding.

Why the LP is nearly integral
-----------------------------
This is a transportation problem (a bipartite network) with `n + k` equalities, so a basic
solution has at most `n + k - 1` nonzeros; `n` of them are the whole-zip assignments, leaving
at most `k - 1` zips split between two districts.  `assign` rounds each split zip to its
largest component, which perturbs the district masses by at most one zip each -- expected and
fine at 1.1% per zip.  `improve` then repairs what the rounding cost.

No contiguity, no adjacency: this module is pure functions on arrays (`xy`, `M`, `k`, `rng`)
and depends on nothing else in `td/`.  `to_district` converts a labelling into the
`{zip_id: district}` mapping that `channel.stage2` consumes, so wiring stage 1 into stage 2 is
one call.
"""
from __future__ import annotations

import math

import numpy as np
from scipy import sparse
from scipy.optimize import linprog

FRAC_TOL = 1e-6          # a zip is "fractional" when its largest share is below 1 - this
GAIN_TOL = 1e-12         # a move must raise sum_j log M_j by more than this to be taken


def _as_rng(rng):
    """`np.random.default_rng` accepts a Generator, an int seed or None -- all three work."""
    return np.random.default_rng(rng)


def _dist2(xy: np.ndarray, centers: np.ndarray) -> np.ndarray:
    """`(n, k)` squared Euclidean distances.  Coordinates are equal-area planar, so this is
    a real area-weighted moment of inertia, not a lat/lon approximation."""
    diff = xy[:, None, :] - centers[None, :, :]
    return np.einsum("nkd,nkd->nk", diff, diff)


def _centroids(xy: np.ndarray, M: np.ndarray, labels: np.ndarray, k: int,
               prev: np.ndarray = None) -> np.ndarray:
    """M-weighted centroid per district; an empty district keeps its previous center."""
    out = np.zeros((k, xy.shape[1]), float)
    for j in range(k):
        sel = labels == j
        w = M[sel].sum()
        if sel.any() and w > 0:
            out[j] = (M[sel, None] * xy[sel]).sum(axis=0) / w
        elif prev is not None:
            out[j] = prev[j]
    return out


# ------------------------------------------------------------------------ seeding
def seed_centers(xy: np.ndarray, M: np.ndarray, k: int, rng=0) -> np.ndarray:
    """M-weighted k-means++ seeding: `(k, 2)` centers, deterministic given the seed.

    The first center is a zip drawn with probability proportional to `M`; each further center
    is drawn with probability proportional to `M_z * d^2(z, nearest chosen center)`.  Weighting
    by `M` rather than by count is the right prior here: the districts are equal in *mass*, so
    a dense-but-light region should not attract centers the way its zip count would suggest.
    """
    xy = np.asarray(xy, float)
    M = np.asarray(M, float)
    n = xy.shape[0]
    if k < 1 or n < k:
        raise ValueError(f"need 1 <= k <= n; got k={k}, n={n}")
    g = _as_rng(rng)
    p = M / M.sum()
    first = int(g.choice(n, p=p))
    idx = [first]
    d2 = ((xy - xy[first]) ** 2).sum(axis=1)
    for _ in range(k - 1):
        w = M * d2
        s = w.sum()
        # every remaining zip coincides with a chosen center (duplicate coordinates): fall
        # back to the mass prior rather than dividing by zero
        pick = int(g.choice(n, p=(w / s) if s > 0 else p))
        idx.append(pick)
        d2 = np.minimum(d2, ((xy - xy[pick]) ** 2).sum(axis=1))
    return xy[np.array(idx)].copy()


# --------------------------------------------------------------- balanced assignment
def assign(xy: np.ndarray, M: np.ndarray, centers: np.ndarray):
    """Balanced assignment to fixed centers by the transportation LP.  `(labels, n_fractional)`.

    Solves the LP in the module docstring with `scipy.optimize.linprog(method="highs")` on the
    flattened `n*k` variables (n=1,229, k=13 -> ~16k columns, which HiGHS eats).  The mass
    equality uses the exact target `(sum M)/k`; after rounding the split zips the realised
    masses deviate slightly, which is expected -- `improve` is what cleans it up.

    Conditioning: both the objective coefficients and the mass column are descaled (distances
    by their mean, masses by their mean) before solving.  HiGHS' feasibility tolerances are
    absolute, and the real instance's `M` is in dollars, so a raw solve would set the mass
    equalities at ~1e9 and the compactness costs at ~1e11.  The optimum is unchanged: scaling
    the objective is a positive rescale, and scaling the mass column and its right-hand side
    together leaves the feasible set identical.

    A district left empty by rounding (possible in principle, never seen in practice, since the
    LP gives every district positive mass) is repaired by handing it the nearest zip from a
    district holding more than one -- an empty district would make the Nash objective -inf.
    """
    xy = np.asarray(xy, float)
    M = np.asarray(M, float)
    centers = np.asarray(centers, float)
    n, k = xy.shape[0], centers.shape[0]
    if k == 1:
        return np.zeros(n, int), 0
    if n < k:
        raise ValueError(f"cannot fill {k} districts with {n} zips")

    d2 = _dist2(xy, centers)
    w = M / M.mean()                                     # descaled mass column
    c = (w[:, None] * d2).ravel()
    scale = c.mean()
    if scale > 0:
        c = c / scale

    cols = np.arange(n * k)
    rows_z = np.repeat(np.arange(n), k)                  # var (z, j) lives at z*k + j
    rows_j = np.tile(np.arange(k), n)
    A_place = sparse.coo_matrix((np.ones(n * k), (rows_z, cols)), shape=(n, n * k))
    A_mass = sparse.coo_matrix((np.repeat(w, k), (rows_j, cols)), shape=(k, n * k))
    A_eq = sparse.vstack([A_place, A_mass]).tocsc()
    b_eq = np.concatenate([np.ones(n), np.full(k, w.sum() / k)])

    res = linprog(c, A_eq=A_eq, b_eq=b_eq, bounds=(0.0, 1.0), method="highs")
    if not res.success:
        raise RuntimeError(f"transportation LP failed: {res.message}")

    X = np.asarray(res.x, float).reshape(n, k)
    labels = X.argmax(axis=1).astype(int)
    n_fractional = int((X.max(axis=1) < 1.0 - FRAC_TOL).sum())
    _repair_empty(labels, d2, k)
    return labels, n_fractional


def _repair_empty(labels: np.ndarray, d2: np.ndarray, k: int) -> None:
    """In place: give every empty district its nearest zip taken from a district of size >= 2."""
    counts = np.bincount(labels, minlength=k)
    for j in np.flatnonzero(counts == 0):
        donors = np.flatnonzero(counts[labels] > 1)
        if donors.size == 0:
            return
        z = int(donors[np.argmin(d2[donors, j])])
        counts[labels[z]] -= 1
        labels[z] = j
        counts[j] += 1


# ---------------------------------------------------------------------- local polish
def improve(xy: np.ndarray, M: np.ndarray, labels: np.ndarray, iters: int = 20,
            n_near: int = 3):
    """Greedy single-zip moves that raise `sum_j log M_j`.  Returns new labels (a copy).

    Accept rule, exactly as implemented:

    * a move of zip `z` from district `a` to `b` is *considered* only when `b` is one of the
      `n_near` centers nearest to `z` -- the compactness guard.  Without it a Nash-greedy move
      would happily send a California zip to a Florida district for an epsilon of balance;
      with it, a move stays local and compactness cannot grossly worsen.
    * among the considered destinations, take the one maximising
      `dlog = log(M_a - M_z) + log(M_b + M_z) - log M_a - log M_b`, and only if
      `dlog > GAIN_TOL` (a *strict* increase in the Nash objective).
    * ties in `dlog` (relative 1e-12) are broken by the smaller `M_z * d^2(z, c_b)`, i.e. the
      more compact destination.
    * a district is never emptied (that would make the objective -inf).

    Centroids are recomputed **once per pass**, and masses are updated incrementally within a
    pass, so a pass is a Gauss-Seidel sweep against slightly stale centers.  Passes run until
    one accepts no move, or `iters` passes have run.

    Measured cost of the trade at n=1,300, k=13: spread 5.4% -> 0.37% for a 4.5% rise in the
    moment of inertia.  Balance is the objective; that is the intended direction.
    """
    xy = np.asarray(xy, float)
    M = np.asarray(M, float)
    labels = np.asarray(labels, int).copy()
    k = int(labels.max()) + 1 if labels.size else 0
    if k < 2:
        return labels
    for _ in range(int(iters)):
        centers = _centroids(xy, M, labels, k)
        d2 = _dist2(xy, centers)
        near = np.argsort(d2, axis=1)[:, :max(int(n_near), 1)]
        mass = np.bincount(labels, weights=M, minlength=k).astype(float)
        counts = np.bincount(labels, minlength=k)
        moved = 0
        for z in range(labels.size):
            a = int(labels[z])
            if counts[a] <= 1:
                continue
            m = float(M[z])
            if mass[a] - m <= 0:
                continue
            best_b, best_gain, best_cost = -1, -math.inf, math.inf
            for b in near[z]:
                b = int(b)
                if b == a:
                    continue
                gain = (math.log(mass[a] - m) + math.log(mass[b] + m)
                        - math.log(mass[a]) - math.log(mass[b]))
                if gain <= GAIN_TOL:
                    continue
                cost = m * float(d2[z, b])
                tied = abs(gain - best_gain) <= 1e-12 * max(abs(gain), 1.0)
                if gain > best_gain and not tied:
                    best_b, best_gain, best_cost = b, gain, cost
                elif tied and cost < best_cost:              # compactness breaks the tie
                    best_b, best_gain, best_cost = b, gain, cost
            if best_b >= 0:
                mass[a] -= m
                mass[best_b] += m
                counts[a] -= 1
                counts[best_b] += 1
                labels[z] = best_b
                moved += 1
        if moved == 0:
            break
    return labels


# --------------------------------------------------------------------------- report
def metrics(M: np.ndarray, labels: np.ndarray, xy: np.ndarray = None,
            centers: np.ndarray = None) -> dict:
    """District masses and how balanced (and, given `xy`, how compact) the draw is.

    `nash` is the stage-1 objective `sum_j log M_j`, `-inf` if any district is empty -- the
    honest reading of maximum Nash welfare, matching `model.objective`.  `compactness` is
    `sum_z M_z * d^2(z, c_{label(z)})` against the supplied centers, or the M-weighted district
    centroids when none are given (in which case it is the districts' moment of inertia).
    """
    M = np.asarray(M, float)
    labels = np.asarray(labels, int)
    k = int(labels.max()) + 1 if labels.size else 0
    mass = np.bincount(labels, weights=M, minlength=k).astype(float)
    total = float(mass.sum())
    mean = total / k if k else 0.0
    out = dict(
        k=k,
        total=total,
        mean=mean,
        masses=[float(v) for v in mass],
        sizes=[int(v) for v in np.bincount(labels, minlength=k)],
        min=float(mass.min()) if k else 0.0,
        max=float(mass.max()) if k else 0.0,
        nash=float(np.log(mass).sum()) if k and (mass > 0).all() else -math.inf,
        spread_rel=float((mass.max() - mass.min()) / mean) if mean else 0.0,
        max_dev_rel=float(np.abs(mass - mean).max() / mean) if mean else 0.0,
    )
    if xy is not None and k:
        xy = np.asarray(xy, float)
        C = _centroids(xy, M, labels, k) if centers is None else np.asarray(centers, float)
        d2 = ((xy - C[labels]) ** 2).sum(axis=1)
        per = np.bincount(labels, weights=M * d2, minlength=k).astype(float)
        out["compactness"] = float(per.sum())
        out["compactness_per_district"] = [float(v) for v in per]
    return out


# ------------------------------------------------------------------------- pipeline
def draw(xy: np.ndarray, M: np.ndarray, k: int, seed=0, rounds: int = 10,
         improve_iters: int = 20, n_near: int = 3) -> dict:
    """Seed -> (assign, recenter)* -> polish.  One draw, as a dict of labels + centers + metrics.

    The loop is Lloyd's algorithm with the balanced assignment step in place of the nearest-
    center step: each round solves the transportation LP against the current centers, then
    moves each center to its district's M-weighted centroid.  It stops when the labels repeat
    or after `rounds` rounds (~10 is ample; the labels usually settle in 3-5).  `improve` then
    repairs the balance the integral rounding cost.

    Every round's assignment is exactly balanced *before* rounding, so unlike plain k-means
    there is no drift to a lopsided fixed point -- the rounds only buy compactness.
    """
    xy = np.asarray(xy, float)
    M = np.asarray(M, float)
    if (M <= 0).any():
        raise ValueError("every zip needs positive opportunity M (a zero makes log M_j -inf)")
    centers = seed_centers(xy, M, k, seed)
    labels, n_frac, used, converged = None, 0, 0, False
    for r in range(max(int(rounds), 1)):
        new, n_frac = assign(xy, M, centers)
        used = r + 1
        if labels is not None and np.array_equal(new, labels):
            labels, converged = new, True
            break
        labels = new
        centers = _centroids(xy, M, labels, k, prev=centers)
    polished = improve(xy, M, labels, iters=improve_iters, n_near=n_near)
    centers = _centroids(xy, M, polished, k, prev=centers)
    out = dict(labels=polished, centers=centers, seed=seed, rounds_used=used,
               converged=bool(converged), n_fractional=int(n_frac),
               n_moved=int((polished != labels).sum()))
    out.update(metrics(M, polished, xy, centers))
    return out


def portfolio(xy: np.ndarray, M: np.ndarray, k: int, seeds, **kw) -> list:
    """One `draw` per seed, best Nash first.

    The portfolio is the cheap half of the two-stage mitigation in `channel.score_draws`:
    stage 1 cannot see rep relationships, so generate several balanced draws and let stage 2
    (milliseconds) say which one staffs best.  Deliberately serial and dumb.
    """
    out = [draw(xy, M, k, seed=s, **kw) for s in seeds]
    out.sort(key=lambda r: -r["nash"])
    return out


def to_district(zips, labels) -> dict:
    """`{zip_id: district}` -- the mapping `channel.stage2` / `score_draws` take as a draw."""
    labels = np.asarray(labels, int)
    zips = list(zips)
    if len(zips) != labels.size:
        raise ValueError(f"{len(zips)} zips but {labels.size} labels")
    return {z: int(d) for z, d in zip(zips, labels)}
