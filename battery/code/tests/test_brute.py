"""
test_brute.py -- contig_methods/brute.py: exhaustive ground truth for n <= 20
(PLAN.md C.1, C.5, U2).

Acceptance: `brute` matches an independent, deliberately-simple `_naive` reference
(all 2**n subsets, feasibility via `base.is_feasible`, which is itself nx-based and
frozen) on n <= 10 hand graphs and real synthetic pairs, including a pair whose
subgraph is disconnected and a graph with zero-value (A=B=M=0) zips; it finishes
comfortably under the 60 s budget at n = 20 on real planar pairs; and `n > MAX_N`
returns a clean "error" status rather than attempting the enumeration.
"""
from __future__ import annotations

import math
import os
import sys
import time

import networkx as nx

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
for p in (os.path.join(ROOT, "code"), os.path.join(ROOT, "battery", "code")):
    if p not in sys.path:
        sys.path.insert(0, p)

import synth, territory as T                    # noqa: E402
from contig_methods import REGISTRY, base, brute  # noqa: E402

THETA, LAM = 0.40, 0.30


# ------------------------------------------------------------------ hand instances
def path_instance(n=8):
    """Same construction as test_base.py's path_instance: monotone ratio along a
    path, so a prefix is optimal and ties are unlikely."""
    G = nx.path_graph(n)
    for i in range(n):
        A = 1.0 + 0.9 * (n - 1 - i) / (n - 1)
        B = 1.0 + 0.9 * i / (n - 1)
        G.nodes[i].update(A=A, B=B, M=4.0 + 0.1 * i, pos=(i / n, 0.5))
    return G


def two_component_instance():
    """P4 + P3, disjoint: the pair graph itself has two components (C.0 #1)."""
    G = path_instance(4)
    H = nx.relabel_nodes(path_instance(3), {0: 10, 1: 11, 2: 12})
    return nx.union(G, H)


def glue_instance():
    """P6 with two zero-value (A=B=M=0) zips in the middle (regime (d))."""
    G = path_instance(6)
    for z in (2, 3):
        G.nodes[z].update(A=0.0, B=0.0, M=0.0)
    return G


def star_instance():
    G = nx.star_graph(6)
    for i, z in enumerate(G.nodes()):
        G.nodes[z].update(A=1.0 + 0.3 * i, B=1.0 + 0.25 * (6 - i), M=3.0)
    return G


def cycle_instance(n=9):
    G = nx.cycle_graph(n)
    for i in range(n):
        G.nodes[i].update(A=1.0 + 0.5 * math.sin(i), B=1.0 + 0.5 * math.cos(i), M=3.0)
    return G


def three_component_instance():
    """Three small disjoint pieces with distinct (non-symmetric) utility profiles --
    two identical components would create a genuine objective tie with swappable
    to_a sets, which is not what this test is checking -- one carrying a zero-value
    glue zip.  n = 3 + 3 + 4 = 10, so the naive 2**n cross-check still applies."""
    G = nx.Graph()
    G.add_edges_from([(0, 1), (1, 2)])
    for i, (A, B, M) in zip((0, 1, 2), [(1.9, 1.0, 4.0), (1.5, 1.4, 4.2), (1.0, 1.9, 4.4)]):
        G.nodes[i].update(A=A, B=B, M=M, pos=(i, 0))
    G.add_edges_from([(10, 11), (11, 12)])
    for i, (A, B, M) in zip((10, 11, 12), [(0.6, 2.3, 3.6), (1.1, 1.7, 3.1), (2.0, 0.9, 3.9)]):
        G.nodes[i].update(A=A, B=B, M=M, pos=(i, 1))
    G.add_edges_from([(20, 21), (21, 22), (22, 23)])
    for i, (A, B, M) in zip((20, 21, 22, 23),
                            [(1.7, 0.8, 3.3), (0.0, 0.0, 0.0), (1.2, 1.6, 3.5), (0.9, 1.4, 3.0)]):
        G.nodes[i].update(A=A, B=B, M=M, pos=(i, 2))
    return G


# ---------------------------------------------------------------------- naive OPT
def _naive(G, nodes, theta=THETA, lam=LAM, rho=0.0):
    """All 2**n subsets; feasibility via base.is_feasible (nx-based, frozen contract
    -- independent of brute.py's bitmask machinery, so this is a real cross-check)."""
    nodes = list(nodes)
    ua, ub = base.utilities(G, nodes, theta, lam)
    n = len(nodes)
    best = (-math.inf, None)
    for mask in range(1 << n):
        to_a = {nodes[i] for i in range(n) if (mask >> i) & 1}
        if not base.is_feasible(G, nodes, to_a):
            continue
        x = base.mask(nodes, to_a)
        per = base.perimeter(G, nodes, to_a)
        obj = base.objective(ua, ub, x, rho, per)
        if obj > best[0]:
            best = (obj, to_a)
    return best


def _t0_small_pairs(lo=8, hi=10, limit=6):
    """A few real S1_aligned pairs at n <= 10, for the naive cross-check."""
    out = []
    for n in (40, 50, 60):
        for seed in range(1, 6):
            G = synth.scenario("S1_aligned", n=n, seed=seed)
            O = T.overlap_graph(G)
            for edge in O.edges():
                ra, rb = T.pair_endpoints(edge)
                zips = T.zips_for_pair(G, ra, rb)
                if lo <= len(zips) <= hi:
                    H0, _ = base.filter_pair(G, sorted(zips), respect_state=False)
                    H, _ = base.rescale_pair(H0, sorted(H0), THETA, LAM)
                    out.append((H, sorted(H)))
                    if len(out) >= limit:
                        return out
    return out


def test_brute_matches_naive_on_hand_and_real_instances():
    named = [
        ("path8", path_instance(8), 0.0),
        ("path8_rho", path_instance(8), 0.02),
        ("two_component", two_component_instance(), 0.0),
        ("glue_zero_value", glue_instance(), 0.0),
        ("star", star_instance(), 0.0),
        ("cycle9", cycle_instance(9), 0.0),
        ("three_component", three_component_instance(), 0.0),
    ]
    for i, (H, _nodes) in enumerate(_t0_small_pairs()):
        named.append((f"t0_pair_{i}", H, 0.0))

    for name, G, rho in named:
        nodes = sorted(G)
        assert len(nodes) <= 10, (name, len(nodes))
        res = REGISTRY["brute"].solve(G, nodes, theta=THETA, lam=LAM, rho=rho,
                                      respect_state=False, time_limit=30, seed=0)
        assert res.status == "optimal", (name, res.status, res.message)
        row = base.evaluate(G, nodes, res, theta=THETA, lam=LAM, rho=rho)
        assert row["valid"], (name, row["violations"])
        nobj, nto = _naive(G, nodes, rho=rho)
        assert abs(row["LB"] - nobj) < 1e-9, (name, row["LB"], nobj)
        # unique-optimum instances: the allocation itself should also match
        if nto is not None:
            assert res.to_a == nto, (name, sorted(res.to_a), sorted(nto))


def test_brute_multi_component_combination():
    """A pair graph with 3 components (including one carrying zero-value glue
    zips) exercises the Pareto-prune + outer-product combination path, not just
    the single-component fast path."""
    G = three_component_instance()
    nodes = sorted(G)
    assert nx.number_connected_components(G) == 3
    res = REGISTRY["brute"].solve(G, nodes, theta=THETA, lam=LAM, rho=0.0,
                                  respect_state=False, time_limit=30, seed=0)
    row = base.evaluate(G, nodes, res, theta=THETA, lam=LAM, rho=0.0)
    assert row["valid"] and row["excess_pieces"] == 0
    nobj, nto = _naive(G, nodes)
    assert abs(row["LB"] - nobj) < 1e-9
    assert res.to_a == nto


def test_brute_n20_finishes_fast():
    """PLAN.md C.5: < 60 s at n ~= 20 on a real planar pair."""
    biggest = None
    for n in (40, 50, 60):
        for seed in range(1, 11):
            G = synth.scenario("S1_aligned", n=n, seed=seed)
            O = T.overlap_graph(G)
            for edge in O.edges():
                ra, rb = T.pair_endpoints(edge)
                zips = T.zips_for_pair(G, ra, rb)
                if 18 <= len(zips) <= 20 and (biggest is None or len(zips) > len(biggest[1])):
                    H0, _ = base.filter_pair(G, sorted(zips), respect_state=False)
                    H, _ = base.rescale_pair(H0, sorted(H0), THETA, LAM)
                    biggest = (H, sorted(H))
        if biggest is not None and len(biggest[1]) == 20:
            break
    assert biggest is not None, "no n in [18, 20] pair found in the scan"
    H, nodes = biggest
    t0 = time.time()
    res = REGISTRY["brute"].solve(H, nodes, theta=THETA, lam=LAM, rho=0.0,
                                  respect_state=False, time_limit=60, seed=0)
    elapsed = time.time() - t0
    row = base.evaluate(H, nodes, res, theta=THETA, lam=LAM, rho=0.0)
    assert row["valid"], row["violations"]
    assert elapsed < 60.0, f"brute took {elapsed:.1f}s at n={len(nodes)}"
    print(f"[brute n={len(nodes)} timing] {elapsed:.2f}s, n_feasible={res.extra['n_feasible']}")


def test_brute_max_n_error():
    G = nx.path_graph(brute.MAX_N + 1)
    for i in range(brute.MAX_N + 1):
        G.nodes[i].update(A=1.0, B=1.0, M=2.0)
    nodes = sorted(G)
    res = REGISTRY["brute"].solve(G, nodes, theta=THETA, lam=LAM, rho=0.0,
                                  respect_state=False, time_limit=5, seed=0)
    assert res.status == "error"
    assert res.to_a is None and res.LB is None and res.UB is None
    row = base.evaluate(G, nodes, res, theta=THETA, lam=LAM, rho=0.0)
    assert row["valid"]
