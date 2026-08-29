"""_territory_vendored.py -- verbatim copies of the repo functions this tool needs.

The tool must run on the work machine with nothing but pip-installable packages, so it
cannot import the territory-division repo.  These six functions plus `REQUIRED` are copied
byte-for-byte (modulo this header) from `code/territory.py`; the repo-side test
`battery/code/tests/test_twin_export.py::test_vendored_territory_in_sync` compares them
function-by-function with `inspect.getsource` and prints a unified diff when they drift.

    source file    code/territory.py
    source commit  5646399a414b64cdd6b2ae9e10b861a7a08d4533
    source sha256  6f825d6df6ba2904275967abe6dcdfb4e9d9dd2a8d21235414661936daf0ef9e
    vendored on    2026-08-29
    functions      validate, overlap_graph, zips_for_pair, pair_endpoints, largest_pair,
                   census  (+ the REQUIRED tuple)

DO NOT EDIT the function bodies below.  If `territory.py` changes, re-copy and re-run the
sync test.
"""
from __future__ import annotations
import numpy as np, networkx as nx

REQUIRED = ("rep_a", "rep_b", "A", "B", "M")


# ----------------------------------------------------------------- validation
def validate(G, theta=0.40, lam=0.30):
    """Check attributes and the pointwise non-negative-headroom condition."""
    problems = []
    missing = [n for n in G if any(k not in G.nodes[n] for k in REQUIRED)]
    if missing:
        problems.append(f"{len(missing)} nodes missing required attributes (e.g. {missing[:3]})")
    A = np.array([G.nodes[n].get("A", 0.0) for n in G])
    B = np.array([G.nodes[n].get("B", 0.0) for n in G])
    M = np.array([G.nodes[n].get("M", 0.0) for n in G])
    bad = (M < A + theta * B) | (M < B + theta * A)
    if bad.any():
        problems.append(f"{int(bad.sum())} ZCTAs violate non-negative headroom "
                        f"(M_z < max(A+theta*B, B+theta*A)); worst deficit "
                        f"{float((np.minimum(M-A-theta*B, M-B-theta*A)).min()):.4f}")
    iso = list(nx.isolates(G))
    if iso:
        problems.append(f"{len(iso)} isolated ZCTAs in the adjacency graph")
    ncc = nx.number_connected_components(G)
    if ncc > 1:
        problems.append(f"adjacency graph has {ncc} components (islands / non-contiguous states)")
    return problems


# ------------------------------------------------------- overlap graph & census
def overlap_graph(G):
    """Bipartite graph of (firm-A rep, firm-B rep) pairs, edge weight = shared opportunity."""
    O = nx.Graph()
    for n, d in G.nodes(data=True):
        a, b = ("A", d["rep_a"]), ("B", d["rep_b"])
        O.add_node(a, side="A"); O.add_node(b, side="B")
        if O.has_edge(a, b):
            O[a][b]["M"] += d["M"]; O[a][b]["zips"] += 1
            O[a][b]["A"] += d["A"]; O[a][b]["B"] += d["B"]
        else:
            O.add_edge(a, b, M=d["M"], zips=1, A=d["A"], B=d["B"])
    return O


def zips_for_pair(G, rep_a, rep_b):
    """ZCTAs covered by firm-A rep `rep_a` and firm-B rep `rep_b` simultaneously."""
    return [n for n, d in G.nodes(data=True)
            if d["rep_a"] == rep_a and d["rep_b"] == rep_b]


def pair_endpoints(edge):
    """Normalise an overlap-graph edge to (rep_a_id, rep_b_id); endpoints are ('A'|'B', id)."""
    u, v = edge[0], edge[1]
    a, b = (u, v) if u[0] == "A" else (v, u)
    return a[1], b[1]


def largest_pair(G):
    """The (rep_a, rep_b) pair sharing the most opportunity."""
    O = overlap_graph(G)
    e = max(O.edges(data=True), key=lambda x: x[2]["M"])
    return pair_endpoints(e) + (e[2],)


def census(G, min_share=0.02, split=True):
    """
    Decompose the national problem. Returns per-component structure and a verdict on
    whether the two-player theory applies directly.

    With split=True (default), edges under min_share of their component's opportunity
    are trimmed BEFORE componentization, so map slivers cannot glue clean 1-1 pairs
    into one spurious "dense" component. (The original behaviour -- split=False --
    trimmed weak edges only when labelling a component's shape, never to split it,
    which made min_share decorative: under any boundary noise the census could only
    ever answer "dense". Demonstrated in census_stress.py.) Weak edges INSIDE a
    surviving group still count toward its M (same reps, same solve); weak edges
    CROSSING groups are orphaned -- their opportunity appears in no row, so
    1 - sum(r["share"]) is the orphaned share needing manual adjudication.
    """
    O = overlap_graph(G)
    totM = sum(d["M"] for _, d in G.nodes(data=True))
    out = []
    for comp in nx.connected_components(O):
        sub = O.subgraph(comp)
        Mc = sum(d["M"] for *_, d in sub.edges(data=True))
        strong_all = [(u, v) for u, v, d in sub.edges(data=True)
                      if d["M"] >= min_share * Mc]
        if split:
            H = nx.Graph(); H.add_nodes_from(comp); H.add_edges_from(strong_all)
            groups = list(nx.connected_components(H))
        else:
            groups = [set(comp)]
        for g in groups:
            gsub = O.subgraph(g)
            if gsub.number_of_edges() == 0:
                continue                      # rep isolated by trimming -> orphaned
            Mg = sum(d["M"] for *_, d in gsub.edges(data=True))
            reps_a = [x for x in g if x[0] == "A"]; reps_b = [x for x in g if x[0] == "B"]
            strong = [(u, v) for u, v, d in gsub.edges(data=True)
                      if d["M"] >= min_share * Mc]
            shape = ("1-1 pair" if len(reps_a) == 1 and len(reps_b) == 1
                     else f"dense ({len(reps_a)}A x {len(reps_b)}B, {len(strong)} strong edges)")
            out.append(dict(reps_a=reps_a, reps_b=reps_b, M=Mg, share=Mg / totM,
                            edges=gsub.number_of_edges(), strong_edges=len(strong),
                            shape=shape))
    out.sort(key=lambda r: -r["M"])
    return out


