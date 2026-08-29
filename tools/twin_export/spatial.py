"""spatial.py -- the spatial structure that is *meant* to survive into the twin.

Rank jitter destroys which ZCTA holds which value; what has to be preserved is the shape of
the field: how strongly neighbours resemble each other (Moran's I), how that resemblance
decays with graph distance (`hop_rank_corr`), and how much smoothing has to be applied to a
white-noise draw to reproduce it (`fit_smoothing`).  These three are also the privacy
argument: the audit shows the neighbourhood-level statistics matching while the
individual-level ones do not.
"""
from __future__ import annotations

import math
from collections import deque

import numpy as np
from scipy import sparse
from scipy.stats import rankdata


def row_normalized_adj(G, n=None):
    """Row-normalised adjacency of a graph whose nodes are 0..n-1.  CSR, float64."""
    n = int(n if n is not None else G.number_of_nodes())
    if G.number_of_edges() == 0:
        return sparse.csr_matrix((n, n))
    e = np.array([(int(u), int(v)) for u, v in G.edges], dtype=np.int64)
    rows = np.concatenate([e[:, 0], e[:, 1]])
    cols = np.concatenate([e[:, 1], e[:, 0]])
    W = sparse.csr_matrix((np.ones(rows.size), (rows, cols)), shape=(n, n))
    deg = np.asarray(W.sum(axis=1)).ravel()
    inv = np.where(deg > 0, 1.0 / np.maximum(deg, 1e-30), 0.0)
    return sparse.diags(inv).dot(W).tocsr()


def morans_i(W, x):
    """Moran's I with a row-normalised W (so S0 = n and I = x'Wx / x'x on centred x)."""
    x = np.asarray(x, dtype=float)
    x = x - x.mean()
    den = float(x.dot(x))
    if den <= 0 or W.nnz == 0:
        return float("nan")
    return float(x.dot(W.dot(x)) / den)


def hop_rank_corr(G, x, hops=5, n_sources=2000, max_pairs=200000, rng=None, n=None):
    """Spearman correlation of `x` across node pairs at graph distance 1..`hops`.

    Sampled BFS: `n_sources` sources drawn without replacement under a fixed seed, each
    expanded to `hops`, pairs accumulated until `max_pairs`.  Returns
    {h: dict(rho, n_pairs, n_sources)}.
    """
    x = np.asarray(x, dtype=float)
    n = int(n if n is not None else G.number_of_nodes())
    rng = np.random.default_rng(0) if rng is None else rng
    r = rankdata(x)
    nbr = [[] for _ in range(n)]
    for u, v in G.edges:
        nbr[int(u)].append(int(v))
        nbr[int(v)].append(int(u))

    srcs = rng.permutation(n)[:min(n_sources, n)]
    per_hop_u = dict((h, []) for h in range(1, hops + 1))
    per_hop_v = dict((h, []) for h in range(1, hops + 1))
    total = 0
    dist = np.full(n, -1, dtype=np.int32)
    for s in srcs:
        s = int(s)
        touched = [s]
        dist[s] = 0
        q = deque([s])
        while q:
            u = q.popleft()
            du = dist[u]
            if du >= hops:
                continue
            for v in nbr[u]:
                if dist[v] < 0:
                    dist[v] = du + 1
                    touched.append(v)
                    q.append(v)
                    if v > s:                       # each unordered pair once per source
                        per_hop_u[du + 1].append(s)
                        per_hop_v[du + 1].append(v)
                        total += 1
        for u in touched:
            dist[u] = -1
        if total >= max_pairs:
            break

    out = {}
    for h in range(1, hops + 1):
        iu = np.asarray(per_hop_u[h], dtype=np.int64)
        iv = np.asarray(per_hop_v[h], dtype=np.int64)
        if iu.size < 2:
            out[h] = dict(rho=float("nan"), n_pairs=int(iu.size), n_sources=int(len(srcs)))
            continue
        a, b = r[iu], r[iv]
        a = a - a.mean()
        b = b - b.mean()
        den = math.sqrt(float(a.dot(a)) * float(b.dot(b)))
        rho = float(a.dot(b) / den) if den > 0 else float("nan")
        out[h] = dict(rho=rho, n_pairs=int(iu.size), n_sources=int(len(srcs)))
    return out


def smooth_field(W, x, k=2, w=1.0):
    """Standardised (I + wW)^k x -- the smoothing operator used to build twin fields."""
    x = np.asarray(x, dtype=float)
    y = x.copy()
    for _ in range(int(k)):
        y = y + w * W.dot(y)
    sd = y.std(ddof=0)
    if sd <= 0:
        return x - x.mean()
    return (y - y.mean()) / sd * (x.std(ddof=0) or 1.0) + x.mean()


def fit_smoothing(W, target_moran, k=2, lo=0.0, hi=3.0, iters=40, rng=None, n=None):
    """Bisect w in [lo, hi] so that a smoothed white-noise field has Moran's I = target.

    Deterministic: the probe field is drawn from a fixed seed, so the same target always
    returns the same w.
    """
    n = int(n if n is not None else W.shape[0])
    rng = np.random.default_rng(20260829) if rng is None else rng
    probe = rng.standard_normal(n)
    if not np.isfinite(target_moran):
        return 0.0

    def mi(w):
        return morans_i(W, smooth_field(W, probe, k=k, w=w))

    f_lo, f_hi = mi(lo), mi(hi)
    if target_moran <= f_lo:
        return float(lo)
    if target_moran >= f_hi:
        return float(hi)
    a, b = lo, hi
    for _ in range(iters):
        m = 0.5 * (a + b)
        if mi(m) < target_moran:
            a = m
        else:
            b = m
    return float(0.5 * (a + b))


def neighbour_rank_corr(G, x, n=None):
    """Spearman correlation of `x` across every adjacent pair (the hop-1 statistic, exact)."""
    x = np.asarray(x, dtype=float)
    r = rankdata(x)
    e = np.array([(int(u), int(v)) for u, v in G.edges], dtype=np.int64)
    if e.size == 0:
        return float("nan"), 0
    a, b = r[e[:, 0]], r[e[:, 1]]
    a = a - a.mean()
    b = b - b.mean()
    den = math.sqrt(float(a.dot(a)) * float(b.dot(b)))
    return (float(a.dot(b) / den) if den > 0 else float("nan")), int(e.shape[0])


def khop_mean(W, x, k=3):
    """Mean of `x` over the k-hop neighbourhood, via k applications of row-normalised W."""
    y = np.asarray(x, dtype=float).copy()
    for _ in range(int(k)):
        y = W.dot(y)
    return y


def bfs_levels(nbr, source, max_hops):
    """Distances from `source` up to `max_hops` as a dict node -> hop (source included)."""
    dist = {int(source): 0}
    q = deque([int(source)])
    while q:
        u = q.popleft()
        du = dist[u]
        if du >= max_hops:
            continue
        for v in nbr[u]:
            if v not in dist:
                dist[v] = du + 1
                q.append(v)
    return dist


def neighbour_lists(G, n):
    nbr = [[] for _ in range(int(n))]
    for u, v in G.edges:
        nbr[int(u)].append(int(v))
        nbr[int(v)].append(int(u))
    return nbr


def multi_source_voronoi(nbr, seeds, n, allowed=None):
    """Multi-source BFS Voronoi: every node takes the label of the seed that reaches it
    first (ties -> lowest seed index).  `allowed[i][j]` (optional) is a per-seed mask of
    nodes that seed may claim, used for the in-state variant."""
    label = np.full(int(n), -1, dtype=np.int64)
    q = deque()
    for i, s in enumerate(seeds):
        s = int(s)
        if label[s] < 0:
            label[s] = i
            q.append(s)
    while q:
        u = q.popleft()
        li = label[u]
        for v in nbr[u]:
            if label[v] < 0 and (allowed is None or allowed(li, v)):
                label[v] = li
                q.append(v)
    if (label < 0).any():                          # unreached (disconnected / masked out)
        missing = np.flatnonzero(label < 0)
        q = deque(int(u) for u in np.flatnonzero(label >= 0))
        while q and (label < 0).any():
            u = q.popleft()
            for v in nbr[u]:
                if label[v] < 0:
                    label[v] = label[u]
                    q.append(v)
        still = np.flatnonzero(label < 0)
        if still.size:
            label[still] = 0
        del missing
    return label


def haversine_km(lon1, lat1, lon2, lat2):
    R = 6371.0088
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dp = p2 - p1
    dl = np.radians(np.asarray(lon2) - np.asarray(lon1))
    a = np.sin(dp / 2.0) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2.0) ** 2
    return 2.0 * R * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))
