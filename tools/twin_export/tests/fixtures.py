"""fixtures.py -- test fixtures and input writers for twin_export.

Deliberately repo-free: `lattice_instance` builds a small instance from scratch so the
tool's own tests need nothing but numpy/networkx, and `write_inputs` turns *any* graph in
the repo's node schema (rep_a, rep_b, A, B, M, state) into the four confidential input
files the CLI reads.  The repo-side SLOW test hands it a `code/synth.py` instance; that
import lives in the test, never in this package.

ZCTA ids are fake but shaped like real ones: five digits whose first two encode the state,
including a "00"-prefixed state so leading-zero handling is exercised.
"""
from __future__ import annotations

import csv
import os

import numpy as np
import networkx as nx


# ------------------------------------------------------------------------- ids
def fake_zctas(states):
    """5-digit ids whose leading digits encode the state; '00xxx' is always included.

    Real ZCTA prefixes work this way (a state owns one or more two-digit blocks and numbers
    within them), so a state with more than 1000 ZCTAs is given as many two-digit blocks as
    it needs, exactly as CA owns 90-96.
    """
    counts = {}
    order = []
    for s in states:
        if s not in counts:
            counts[s] = 0
            order.append(s)
        counts[s] += 1
    blocks = {}
    nxt = 0
    for s in order:
        k = max(1, -(-counts[s] // 1000))            # ceil division
        blocks[s] = list(range(nxt, nxt + k))
        nxt += k
    if nxt > 100:
        raise ValueError("fake_zctas: needs %d two-digit blocks, only 100 exist" % nxt)
    seen = {}
    out = []
    for s in states:
        k = seen.get(s, 0)
        seen[s] = k + 1
        out.append("%02d%03d" % (blocks[s][k // 1000], k % 1000))
    if len(set(out)) != len(out):
        raise ValueError("fake_zctas: produced duplicate ids")
    return out


# ------------------------------------------------------------------- generators
def lattice_instance(side=25, n_rep_a=6, n_rep_b=6, n_states=4, theta=0.40,
                     saturation=0.25, book_ratio=5.0 / 3.0, seed=0, p_zero=0.0,
                     tail=0.9):
    """A self-contained king-move lattice instance in the repo's node schema.

    Spatially correlated M (a smoothed lognormal field), share fields correlated with it,
    Voronoi rep maps for both firms, coarse state bands, and headroom enforced pointwise.
    """
    rng = np.random.default_rng(seed)
    G = nx.grid_2d_graph(side, side)
    for i in range(side - 1):
        for j in range(side - 1):
            G.add_edge((i, j), (i + 1, j + 1))
    coords = sorted(G.nodes)
    idx = dict((c, k) for k, c in enumerate(coords))
    H = nx.relabel_nodes(G, idx)
    n = H.number_of_nodes()

    xy = np.array(coords, dtype=float)
    # smooth field -> spatial autocorrelation
    f = rng.standard_normal(n)
    nbr = [[] for _ in range(n)]
    for u, v in H.edges:
        nbr[u].append(v)
        nbr[v].append(u)
    for _ in range(6):
        f = np.array([0.5 * f[i] + 0.5 * np.mean(f[nbr[i]]) for i in range(n)])
    f = (f - f.mean()) / (f.std() or 1.0)
    M = np.exp(1.0 + tail * f + 0.35 * rng.standard_normal(n))

    g = rng.standard_normal(n)
    for _ in range(4):
        g = np.array([0.5 * g[i] + 0.5 * np.mean(g[nbr[i]]) for i in range(n)])
    g = (g - g.mean()) / (g.std() or 1.0)
    share_a = 0.03 + 0.30 / (1.0 + np.exp(-1.2 * g))
    share_b = 0.03 + 0.30 / (1.0 + np.exp(-1.2 * (0.6 * g + 0.8 * rng.standard_normal(n))))
    A = M * share_a * np.exp(0.30 * rng.standard_normal(n))
    B = M * share_b * np.exp(0.30 * rng.standard_normal(n))

    if p_zero > 0:                                # spatially clustered zero-value glue
        h = rng.standard_normal(n)
        for _ in range(5):
            h = np.array([0.5 * h[i] + 0.5 * np.mean(h[nbr[i]]) for i in range(n)])
        thr = np.quantile(h, p_zero)
        dead = h <= thr
        M[dead] = 0.0
        A[dead] = 0.0
        B[dead] = 0.0

    tgt = saturation * M.sum()
    ta = tgt * book_ratio / (1.0 + book_ratio)
    A *= ta / A.sum()
    B *= (tgt - ta) / B.sum()
    need = np.maximum(A + theta * B, B + theta * A)
    bad = (M < 1.05 * need) & (M > 0)
    M[bad] = 1.05 * need[bad]
    live = M > 0
    A[~live] = 0.0
    B[~live] = 0.0
    need = np.maximum(A + theta * B, B + theta * A)
    bad = M < need
    M[bad] = 1.001 * need[bad]

    seeds_a = rng.choice(n, n_rep_a, replace=False)
    seeds_b = rng.choice(n, n_rep_b, replace=False)
    rep_a = np.argmin(np.linalg.norm(xy[:, None] - xy[seeds_a][None], axis=2), axis=1)
    rep_b = np.argmin(np.linalg.norm(xy[:, None] - xy[seeds_b][None], axis=2), axis=1)
    band = np.minimum((xy[:, 0] / side * n_states).astype(int), n_states - 1)

    for k in range(n):
        H.nodes[k].update(rep_a=int(rep_a[k]), rep_b=int(rep_b[k]), A=float(A[k]),
                          B=float(B[k]), M=float(M[k]), state="S%d" % int(band[k]),
                          pos=(float(xy[k, 0]) / max(side - 1, 1),
                               float(xy[k, 1]) / max(side - 1, 1)))
    return H


# ---------------------------------------------------------------------- writers
def write_inputs(G, outdir, zids=None, parquet=False, coords=False):
    """Write graph.csv/parquet, opportunity.csv, sales.csv, reps.csv, states.csv.

    Returns a dict of paths plus `zids`, the ZCTA id assigned to each graph node.
    """
    os.makedirs(outdir, exist_ok=True)
    nodes = list(G.nodes)
    states = [str(G.nodes[u].get("state", "S0")) for u in nodes]
    if zids is None:
        zids = fake_zctas(states)
    zof = dict(zip(nodes, zids))

    paths = {}
    edge_rows = [(zof[u], zof[v]) for u, v in G.edges]
    paths["graph_csv"] = os.path.join(outdir, "graph.csv")
    _write_csv(paths["graph_csv"], ["u", "v"], edge_rows)
    if parquet:
        import pandas as pd
        pq = os.path.join(outdir, "graph.parquet")
        pd.DataFrame(edge_rows, columns=["u", "v"]).to_parquet(pq, index=False)
        paths["graph_parquet"] = pq

    paths["opportunity"] = os.path.join(outdir, "opportunity.csv")
    _write_csv(paths["opportunity"], ["zcta", "M"],
               [(zof[u], repr(float(G.nodes[u]["M"]))) for u in nodes])
    paths["sales"] = os.path.join(outdir, "sales.csv")
    _write_csv(paths["sales"], ["zcta", "A", "B"],
               [(zof[u], repr(float(G.nodes[u]["A"])), repr(float(G.nodes[u]["B"])))
                for u in nodes])
    paths["reps"] = os.path.join(outdir, "reps.csv")
    _write_csv(paths["reps"], ["zcta", "rep_a", "rep_b"],
               [(zof[u], "RA-%s" % G.nodes[u]["rep_a"], "RB-%s" % G.nodes[u]["rep_b"])
                for u in nodes])
    paths["states"] = os.path.join(outdir, "states.csv")
    _write_csv(paths["states"], ["zcta", "state"],
               [(zof[u], str(G.nodes[u].get("state", "S0"))) for u in nodes])
    if coords:
        paths["coords"] = os.path.join(outdir, "coords.csv")
        pos = _positions(G, nodes)
        _write_csv(paths["coords"], ["zcta", "lon", "lat"],
                   [(zof[u], repr(pos[u][0]), repr(pos[u][1])) for u in nodes])
    paths["zids"] = zids
    return paths


def _positions(G, nodes):
    out = {}
    for u in nodes:
        p = G.nodes[u].get("pos")
        if p is None:
            p = (0.0, 0.0)
        # map a unit square onto a plausible CONUS lon/lat box
        out[u] = (-125.0 + 58.0 * float(p[0]), 25.0 + 24.0 * float(p[1]))
    return out


def _write_csv(path, header, rows):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    return path
