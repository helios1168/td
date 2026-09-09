"""district_split.py -- divide one district's zips among the reps who staff it.

Stage 1 draws districts and stage 2 matches one rep to each.  When several kept reps share a
district -- because each of them already sells inside it -- the district itself has to be
divided, and that division is the same maximum-Nash-welfare question one level down::

    max sum_i log g_i,   g_i = sum_z u_i(z) x_zi,   sum_i x_zi = 1

with `u_i(z)` the N-way utility of `td.model`, evaluated with candidacy *unrestricted* the way
`channel.gain_matrix` does: a rep staffing a district serves all of it, so its utility on a zip
where it holds no book is still real (`docs/PROBLEM.md`, and the plan's staffing decision).

Contiguity, and what replaces it when there is no cell graph
--------------------------------------------------------------
The sold-zip adjacency of the real instance is shattered (547 components over ~1,229 zips), so
a constraint on that graph is either vacuous or infeasible.  The Voronoi cell graph of a
district (one node per zip, an edge for every shared cell border) is connected instead, and
when it is supplied (`adjacency`) the greedy keeps every rep connected on it: `seed_labels`
repairs a shattered argmax by keeping each rep's largest piece per component and growing the
rest back on, and `greedy` then lets a zip leave only when it is not an articulation point of
its own rep's subgraph on that graph, and only to a rep that owns a neighbouring cell.  Without
`adjacency` there is no such guard, and `exact` never sees one either; `split` reports the
pieces the resulting labelling makes (`pieces`, `contiguous`) rather than constraining them.

Compactness is a separate concern and still a *guard on the moves*, not a constraint on the
answer, which is `centers.improve`'s route.  A zip may only move to one of the `n_near`
rep centres nearest to it, and ties in the Nash gain are broken toward the smaller `M_z d^2`.
Without that guard a Nash-greedy move would hand a rep a zip on the far side of the district for
an epsilon of balance.

Rep centres
-----------
Rep `i`'s centre starts at the `u_i`-weighted centroid of the zips where it holds book
(`S_i(z) > 0`) -- its existing footprint -- and falls back to the district's own M-weighted
centroid when it holds no book anywhere in the district.  During the search the centre is the
`u_i`-weighted centroid of the zips `i` currently owns, recomputed once per pass, which is
once per accepted move: `greedy` takes the single best move of a pass, so the two readings
coincide.  A rep whose current zips are all unpositioned keeps its footprint centre.  Zips with
no coordinates (the gazetteer has no internal point for them) are assigned by utility alone:
they carry no distance, so every rep is a legal destination for them and their tie-break cost
is zero.

The two engines
---------------
`greedy` is the default and runs in milliseconds; `exact` is a pyscipopt MINLP over the same
model (binaries `x`, a linear `g_i`, `t_i <= log g_i`, maximise `sum t_i`), warm-started from
the greedy incumbent under a time limit.  A SCIP answer is only *exact* when it closes the gap;
short of that it is a better or equal incumbent, and `status`/`gap` say so.  The greedy
incumbent is always reported.
"""
from __future__ import annotations

import math

import networkx as nx
import numpy as np

from .. import model

GAIN_TOL = 1e-12          # a move must raise sum_i log g_i by more than this to be taken
TINY_REL = 0.5            # g_i's SCIP lower bound, as a fraction of the smallest positive u


# ------------------------------------------------------------------ model -> arrays
def unrestricted_utilities(G, nodes, reps, masses, *, theta: float = 0.40,
                           lam: float = 0.30, filler_capture: str = "full") -> np.ndarray:
    """`U[i, j]` = rep `reps[i]`'s utility for `nodes[j]`, candidacy ignored.

    The same coefficients `channel.gain_matrix` uses -- `c1 = 1 - lam`, `c2 = theta*(1 - lam)`,
    `c_free` from `filler_capture` -- so a split of a district and the staffing that produced
    it are measured on one scale.  Books come from the instance graph `G`; `masses` is
    `{zip: M_z}` read from the zip table, because the table is the unit that carries mass
    (the plan's second invariant).
    """
    if filler_capture not in model.FILLER_CAPTURE:
        raise ValueError(f"filler_capture {filler_capture!r} not in {model.FILLER_CAPTURE}")
    c1, c2 = 1.0 - lam, theta * (1.0 - lam)
    c_free = {"theta": c2, "full": c1, "opportunity": lam}[filler_capture]
    nodes = list(nodes)
    U = np.zeros((len(reps), len(nodes)), float)
    for j, z in enumerate(nodes):
        S = model.books(G, z)
        T = float(sum(S.values()))
        common = c2 * T + c_free * model.free_book(G, z) + lam * float(masses[z])
        for i, r in enumerate(reps):
            U[i, j] = common + (c1 - c2) * float(S.get(r, 0.0))
    return U


def book_matrix(G, nodes, reps) -> np.ndarray:
    """Boolean `B[i, j]`: does rep `reps[i]` hold book on `nodes[j]`?  Rep i's territory."""
    nodes = list(nodes)
    B = np.zeros((len(reps), len(nodes)), bool)
    for j, z in enumerate(nodes):
        S = model.books(G, z)
        for i, r in enumerate(reps):
            B[i, j] = float(S.get(r, 0.0)) > 0.0
    return B


# ------------------------------------------------------------------ objective and centres
def gains(u: np.ndarray, labels: np.ndarray) -> np.ndarray:
    """`g_i` = the utility rep i draws from the zips it owns under `labels`."""
    g = np.zeros(u.shape[0], float)
    for i in range(u.shape[0]):
        sel = labels == i
        if sel.any():
            g[i] = float(u[i, sel].sum())
    return g


def objective(u: np.ndarray, labels: np.ndarray) -> float:
    """`sum_i log g_i`; `-inf` if any rep is starved, which is the honest Nash reading."""
    g = gains(u, labels)
    if (g <= 0).any():
        return -math.inf
    return float(np.log(g).sum())


def _positioned(xy: np.ndarray) -> np.ndarray:
    return np.isfinite(xy).all(axis=1)


def _district_center(xy: np.ndarray, M: np.ndarray) -> np.ndarray:
    """The district's own M-weighted centroid, over the zips that have coordinates."""
    ok = _positioned(xy)
    if not ok.any():
        return np.zeros(2, float)
    w = M[ok]
    if w.sum() <= 0:
        return xy[ok].mean(axis=0)
    return (w[:, None] * xy[ok]).sum(axis=0) / w.sum()


def rep_centers(u: np.ndarray, xy: np.ndarray, book: np.ndarray, M: np.ndarray) -> np.ndarray:
    """`(n_reps, 2)` footprint centres: `u_i`-weighted centroid of the zips where i holds book.

    A rep with no book (or no *positioned* book) inside the district gets the district's
    M-weighted centroid, so it starts at the middle rather than at the origin.
    """
    xy = np.asarray(xy, float)
    ok = _positioned(xy)
    fallback = _district_center(xy, np.asarray(M, float))
    out = np.repeat(fallback[None, :], u.shape[0], axis=0)
    for i in range(u.shape[0]):
        sel = ok & book[i] & (u[i] > 0)
        if not sel.any():
            continue
        w = u[i, sel]
        out[i] = (w[:, None] * xy[sel]).sum(axis=0) / w.sum()
    return out


def _label_centers(u: np.ndarray, xy: np.ndarray, labels: np.ndarray,
                   fallback: np.ndarray) -> np.ndarray:
    """`u_i`-weighted centroid of the zips rep i currently owns; `fallback[i]` when it has none."""
    ok = _positioned(xy)
    out = fallback.copy()
    for i in range(u.shape[0]):
        sel = ok & (labels == i) & (u[i] > 0)
        if not sel.any():
            continue
        w = u[i, sel]
        out[i] = (w[:, None] * xy[sel]).sum(axis=0) / w.sum()
    return out


# ------------------------------------------------------------------ the greedy engine
def _cell_graph(adjacency: dict) -> nx.Graph:
    """The Voronoi cell graph: one node per zip with a cell, an edge per shared cell border."""
    G = nx.Graph()
    G.add_nodes_from(adjacency)
    for j, nbrs in adjacency.items():
        for k in nbrs:
            G.add_edge(j, k)
    return G


def _reconnect(u: np.ndarray, labels: np.ndarray, adjacency: dict) -> None:
    """Repair a shattered argmax on the cell graph, in place.

    Within each connected component of the cell graph, a rep whose zips there split into
    several pieces keeps only the piece with the largest `u[i, piece].sum()` (ties go to the
    piece with the lower minimum index); the rest are freed.  Freed zips are then grown back
    on: repeatedly, the freed zip `j` and owned neighbour `k` maximising
    `(u[labels[k], j], -labels[k], -j)` is assigned `labels[j] = labels[k]`, until none remain.
    Every component keeps at least one owned piece per rep present in it, so growth always
    terminates and no rep loses all of its zips.
    """
    G = _cell_graph(adjacency)
    freed = set()
    for K in nx.connected_components(G):
        by_rep: dict = {}
        for z in K:
            by_rep.setdefault(int(labels[z]), []).append(z)
        for i, zs in by_rep.items():
            sub_pieces = list(nx.connected_components(G.subgraph(zs)))
            if len(sub_pieces) <= 1:
                continue
            best = max(sub_pieces, key=lambda p: (float(u[i, list(p)].sum()), -min(p)))
            for p in sub_pieces:
                if p is not best:
                    freed.update(p)
    while freed:
        best = None                     # (u[labels[k], j], -labels[k], -j, j, k)
        for j in freed:
            for k in adjacency.get(j, ()):
                if k in freed:
                    continue
                key = (float(u[int(labels[k]), j]), -int(labels[k]), -j)
                if best is None or key > best[0]:
                    best = (key, j, k)
        _, j, k = best
        labels[j] = labels[k]
        freed.discard(j)


def seed_labels(u: np.ndarray, adjacency: dict | None = None) -> np.ndarray:
    """`argmax_i u[i, z]`, then one best zip handed to each rep the argmax left empty.

    Ties go to the lowest rep index, so the seed is deterministic.  Utilities differ across
    reps only through `(c1 - c2) * S_i(z)`, so this is "each zip to the rep with the most book
    on it", and every zip nobody sells lands on one rep -- which is exactly what the balancing
    passes then spread out.  With `adjacency` (the Voronoi cell graph over the columns of `u`),
    `_reconnect` then repairs any rep this argmax split across a component (see the module
    docstring).  A zip absent from `adjacency` keeps its argmax label.
    """
    n_reps, n = u.shape
    if n < n_reps:
        raise ValueError(f"{n} zip(s) cannot be split among {n_reps} reps")
    labels = np.asarray(np.argmax(u, axis=0), int)
    counts = np.bincount(labels, minlength=n_reps)
    for i in range(n_reps):
        if counts[i]:
            continue
        movable = [z for z in range(n) if counts[labels[z]] > 1]
        if not movable:
            break
        z = max(movable, key=lambda z: (u[i, z], -z))
        counts[labels[z]] -= 1
        labels[z] = i
        counts[i] += 1
    if adjacency:
        _reconnect(u, labels, adjacency)
    return labels


def greedy(u: np.ndarray, M: np.ndarray, xy: np.ndarray, n_near: int = 3,
           centers0: np.ndarray | None = None, max_passes: int | None = None,
           adjacency: dict | None = None) -> np.ndarray:
    """Best-improvement single-zip moves that raise `sum_i log g_i`.  Returns new labels.

    One move per pass, centres recomputed at the head of every pass, so the centres a move is
    judged against are the ones the previous move produced.  A move from `a` to `b` is
    considered only when `b` is among the `n_near` centres nearest the zip (all reps, for a zip
    with no coordinates); it is taken only when the Nash gain exceeds `GAIN_TOL` and `a` keeps
    at least one zip and a positive gain.  Ties in the gain (relative 1e-12) go to the smaller
    `M_z d^2(z, c_b)`, then to the lower zip and rep index.  Deterministic throughout.

    With `adjacency` (the Voronoi cell graph over the columns of `u`), a zip `z` that is a key
    of `adjacency` may only leave if it is not an articulation point of its rep's subgraph of
    that graph, and only to a rep already owning one of `z`'s neighbouring cells; articulation
    points are recomputed once per rep at the head of each pass, not per candidate move.  A zip
    absent from `adjacency` is unconstrained, as without `adjacency` at all.
    """
    u = np.asarray(u, float)
    M = np.asarray(M, float)
    xy = np.asarray(xy, float)
    n_reps, n = u.shape
    labels = seed_labels(u, adjacency)
    if n_reps < 2:
        return labels
    ok = _positioned(xy)
    if centers0 is None:
        centers0 = np.repeat(_district_center(xy, M)[None, :], n_reps, axis=0)
    fallback = centers0
    all_reps = np.arange(n_reps)
    G = _cell_graph(adjacency) if adjacency else None
    for _ in range(int(max_passes if max_passes is not None else 20 * n)):
        c = _label_centers(u, xy, labels, fallback)
        diff = xy[:, None, :] - c[None, :, :]
        d2 = np.einsum("nkd,nkd->nk", diff, diff)
        near = np.argsort(d2[ok], axis=1)[:, :max(int(n_near), 1)] if ok.any() else None
        near_of = {}
        for pos, z in enumerate(np.flatnonzero(ok)):
            near_of[int(z)] = near[pos]
        g = gains(u, labels)
        counts = np.bincount(labels, minlength=n_reps)
        art = {}
        if G is not None:
            for i in range(n_reps):
                nodes_i = [j for j in adjacency if labels[j] == i]
                art[i] = set(nx.articulation_points(G.subgraph(nodes_i)))
        best = None                     # (delta, cost, z, b)
        for z in range(n):
            a = int(labels[z])
            if counts[a] <= 1:
                continue
            ga = g[a] - u[a, z]
            if ga <= 0:
                continue
            allowed = None
            if adjacency is not None and z in adjacency:
                if z in art[a]:
                    continue
                allowed = {int(labels[k]) for k in adjacency[z]} - {a}
            for b in (near_of[z] if z in near_of else all_reps):
                b = int(b)
                if b == a:
                    continue
                if allowed is not None and b not in allowed:
                    continue
                gb = g[b] + u[b, z]
                if gb <= 0:
                    continue
                delta = math.log(ga) + math.log(gb) - math.log(g[a]) - math.log(g[b])
                if delta <= GAIN_TOL:
                    continue
                cost = float(M[z] * d2[z, b]) if ok[z] else 0.0
                if best is None:
                    best = (delta, cost, z, b)
                    continue
                tied = abs(delta - best[0]) <= 1e-12 * max(abs(delta), 1.0)
                if delta > best[0] and not tied:
                    best = (delta, cost, z, b)
                elif tied and (cost, z, b) < (best[1], best[2], best[3]):
                    best = (delta, cost, z, b)
        if best is None:
            break
        labels[best[2]] = best[3]
    return labels


# ------------------------------------------------------------------ the exact engine
def exact(u: np.ndarray, warm_labels: np.ndarray, time_limit: float = 60.0):
    """`(labels, objective, gap, status)` from a pyscipopt MINLP warm-started at `warm_labels`.

    `g_i` is linear in the binaries and `t_i <= log(g_i)` is SCIP's own `log` expression, so
    the concavity is the solver's to exploit; maximising `sum t_i` is tight at the optimum
    because every `t_i` is pushed up.  `g_i`'s lower bound is half the smallest positive
    utility, which no non-starved rep can undercut, so it excludes exactly the assignments the
    objective already values at `-inf`.  With no incumbent at all the warm labels come back
    unchanged and the gap is `inf`.
    """
    from pyscipopt import Model, log as scip_log

    u = np.asarray(u, float)
    n_reps, n = u.shape
    pos = u[u > 0]
    tiny = TINY_REL * float(pos.min()) if pos.size else 1e-9

    m = Model("district_split")
    m.hideOutput()
    x = [[m.addVar(vtype="B", name=f"x_{i}_{z}") for z in range(n)] for i in range(n_reps)]
    for z in range(n):
        m.addCons(sum(x[i][z] for i in range(n_reps)) == 1)
    ts = []
    for i in range(n_reps):
        ub = max(float(u[i].sum()), tiny)
        g = m.addVar(lb=tiny, ub=ub, name=f"g_{i}")
        m.addCons(g == sum(float(u[i, z]) * x[i][z] for z in range(n)))
        t = m.addVar(lb=math.log(tiny), ub=math.log(ub), name=f"t_{i}")
        m.addCons(t <= scip_log(g))
        ts.append(t)
    m.setObjective(sum(ts), "maximize")

    warm = np.asarray(warm_labels, int)
    sol = m.createPartialSol()
    for z in range(n):
        m.setSolVal(sol, x[int(warm[z])][z], 1.0)
    m.addSol(sol)

    m.setParam("limits/time", float(time_limit))
    m.optimize()
    status = str(m.getStatus())
    if m.getNSols() == 0:
        return warm.copy(), objective(u, warm), math.inf, status
    labels = np.zeros(n, int)
    best = m.getBestSol()
    for z in range(n):
        vals = [m.getSolVal(best, x[i][z]) for i in range(n_reps)]
        labels[z] = int(np.argmax(vals))
    gap = float(m.getGap())
    return labels, objective(u, labels), gap, status


# ------------------------------------------------------------------ the whole answer
def split(u: np.ndarray, M: np.ndarray, xy: np.ndarray, reps, *,
          book: np.ndarray | None = None, n_near: int = 3,
          use_exact: bool = False, time_limit: float = 60.0,
          adjacency: dict | None = None) -> dict:
    """Split the zips among `reps` and report the answer, the method and how sure it is.

    `labels` comes back as one rep name per zip, in the order the columns of `u` were given.
    A rep with no positive utility anywhere in the district cannot hold a positive gain, so it
    is dropped from the run and named in `dropped_reps` rather than making the objective
    `-inf`.  With `use_exact`, SCIP runs warm-started from the greedy labelling and its answer
    is kept only when it is at least as good; `status` and `gap` say whether it closed.

    With `adjacency` (the Voronoi cell graph, over the same zip columns as `u`), the greedy is
    contiguity-guarded (see the module docstring) and the result carries `pieces`, one count
    per kept rep, and `contiguous`, true iff every rep holds one connected piece per component
    it appears in; SCIP is unconstrained regardless, and both come back `None` without
    `adjacency`.
    """
    u = np.asarray(u, float)
    reps = list(reps)
    if u.shape[0] != len(reps):
        raise ValueError(f"u has {u.shape[0]} rows for {len(reps)} reps")
    keep = [i for i in range(len(reps)) if u.shape[1] and u[i].max() > 0]
    dropped = [reps[i] for i in range(len(reps)) if i not in keep]
    if len(keep) < 1:
        raise ValueError("no rep has positive utility anywhere in the district")
    kept = [reps[i] for i in keep]
    uk = u[keep]
    if book is not None:
        book = np.asarray(book, bool)[keep]

    M = np.asarray(M, float)
    xy = np.asarray(xy, float)
    centers0 = rep_centers(uk, xy, book, M) if book is not None else None
    labels = greedy(uk, M, xy, n_near=n_near, centers0=centers0, adjacency=adjacency)
    seed = seed_labels(uk, adjacency)
    value = objective(uk, labels)
    method, gap, status = "greedy", None, "heuristic"

    if use_exact and len(kept) >= 2:
        xl, xv, xgap, xstatus = exact(uk, labels, time_limit=time_limit)
        gap, status = xgap, xstatus
        if xv >= value:
            labels, value, method = xl, xv, "scip"

    if adjacency:
        G = _cell_graph(adjacency)
        rep = model.pieces(G, list(G), {j: int(labels[j]) for j in G})
        pieces_out = {kept[i]: rep["pieces_per_rep"].get(i, 0) for i in range(len(kept))}
        contiguous = rep["excess_pieces"] == 0
    else:
        pieces_out, contiguous = None, None

    g = gains(uk, labels)
    return dict(
        labels=[kept[i] for i in labels],            # one rep name per zip, in the input order
        reps=kept,
        gains={r: float(g[i]) for i, r in enumerate(kept)},
        objective=float(value),
        method=method,
        gap=gap,
        status=status,
        moves=int((labels != seed).sum()),
        dropped_reps=dropped,
        pieces=pieces_out,
        contiguous=contiguous,
    )
