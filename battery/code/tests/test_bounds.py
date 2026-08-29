"""
test_bounds.py -- contig_methods/bounds.py: fractional and free-Nash upper bounds on
the contiguous Nash optimum (PLAN.md C.1, C.5, U2).

Acceptance: on >= 20 T0-like pairs, `ub_free_frac(ua, ub) >= ub_free_nash(...).UB >=
brute's OPT` (tolerance 1e-9), and `ub_free_nash.UB - log(product_free) ==
max(0, gap)` by construction.  `bounds.py` is not a contig_methods *method* (no NAME),
so it must not appear in the registry.
"""
from __future__ import annotations

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
for p in (os.path.join(ROOT, "code"), os.path.join(ROOT, "battery", "code")):
    if p not in sys.path:
        sys.path.insert(0, p)

import synth, territory as T                          # noqa: E402
from contig_methods import REGISTRY, base, bounds, brute  # noqa: E402

THETA, LAM = 0.40, 0.30


def _t0_pairs(ns=(40, 50, 60), seeds=range(1, 11), lo=8, hi=20, limit=22):
    out = []
    for n in ns:
        for seed in seeds:
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


def test_bounds_module_not_a_registered_method():
    assert not hasattr(bounds, "NAME")
    assert not hasattr(bounds, "solve")
    assert "bounds" not in REGISTRY


def test_bound_ordering_and_construction():
    pairs = _t0_pairs()
    assert len(pairs) >= 20, f"only {len(pairs)} T0-like pairs generated"
    n_checked = 0
    for H, nodes in pairs:
        ua, ub = base.utilities(H, nodes, THETA, LAM)
        frac = bounds.ub_free_frac(ua, ub)
        nash = bounds.ub_free_nash(H, nodes, THETA, LAM)
        bres = brute.solve(H, nodes, theta=THETA, lam=LAM, rho=0.0,
                           respect_state=False, time_limit=30, seed=0)
        OPT = bres.LB

        assert frac >= nash["UB"] - 1e-9, (nodes, frac, nash["UB"])
        assert nash["UB"] >= OPT - 1e-9, (nodes, nash["UB"], OPT)

        log_product = math.log(nash["product"])
        assert abs((nash["UB"] - log_product) - max(0.0, nash["gap"])) < 1e-9
        n_checked += 1
    assert n_checked >= 20


def test_ub_free_nash_kappa_not_implemented():
    pairs = _t0_pairs(limit=1)
    H, nodes = pairs[0]
    try:
        bounds.ub_free_nash(H, nodes, THETA, LAM, kappa=0.1)
        raise AssertionError("kappa > 0 should raise NotImplementedError")
    except NotImplementedError:
        pass


def test_ub_free_frac_degenerate_zero_value_zips():
    """A ua*ub == 0 prefix step (regime (d) glue) must not divide by zero and must
    still return a finite, valid bound."""
    import networkx as nx
    G = nx.path_graph(6)
    for i in range(6):
        A = 1.0 + 0.9 * (5 - i) / 5.0
        B = 1.0 + 0.9 * i / 5.0
        G.nodes[i].update(A=A, B=B, M=4.0)
    for z in (2, 3):
        G.nodes[z].update(A=0.0, B=0.0, M=0.0)
    nodes = sorted(G)
    ua, ub = base.utilities(G, nodes, THETA, LAM)
    frac = bounds.ub_free_frac(ua, ub)
    assert math.isfinite(frac)
    nash = bounds.ub_free_nash(G, nodes, THETA, LAM)
    assert frac >= nash["UB"] - 1e-9
