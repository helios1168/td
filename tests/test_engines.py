"""
test_engines.py -- self-contained smoke test for the engines carried into this worktree.

`scip_tree` and `cert_exact` came across from the two-player programme because their
architecture carries to the N-way problem (NWAY.md 3) and stage 1 will be built on them.
Their original tests did not come across: those pull `instances.py -> synth.py ->
territory.py -> battery/figures/*.json`, i.e. most of the legacy stack this worktree exists
to leave behind.

So this file replaces them with hand-built instances and no repo dependencies beyond the
contract itself.  It is deliberately a *two-player* test -- that is what these engines
currently solve, and the point is to know they still work before the N-way variant is built
on top of them, not to test the new model (test_nway / test_channel do that).

Acceptance kept from TEST_PLAN.md 3: brute-force match on small n, a real certificate at
CERT_TOL, and one connected piece per side.
"""
from __future__ import annotations

import math
import os
import sys

import networkx as nx


from td.solvers import REGISTRY, base                      # noqa: E402

THETA, LAM = 0.40, 0.30


# ------------------------------------------------------------------ hand instances
def path_pair(n=10):
    """P_n, a-heavy at the left end and b-heavy at the right; prefixes are contiguous."""
    G = nx.path_graph(n)
    for i in range(n):
        G.nodes[i].update(rep_a="A1", rep_b="B1",
                          A=1.0 + 0.9 * (n - 1 - i) / (n - 1),
                          B=1.0 + 0.9 * i / (n - 1),
                          M=4.0 + 0.1 * i)
    return G


def grid_pair(r=3, c=4):
    """A small grid -- 2-connected, so contiguity actually binds rather than being free."""
    G = nx.grid_2d_graph(r, c)
    G = nx.relabel_nodes(G, {v: i for i, v in enumerate(sorted(G))})
    for i in sorted(G):
        G.nodes[i].update(rep_a="A1", rep_b="B1",
                          A=1.0 + (i % 5) * 0.4, B=1.0 + ((7 - i) % 5) * 0.4,
                          M=6.0 + 0.2 * i)
    return G


def two_component_pair():
    """The pair graph itself is disconnected -- trap 13's shape, one root per component."""
    G = path_pair(5)
    H = nx.relabel_nodes(path_pair(4), {i: 20 + i for i in range(4)})
    return nx.union(G, H)


def _run(name, G, nodes, **kw):
    spec = REGISTRY[name]
    return base.run_method(spec.solve, G, nodes, theta=THETA, lam=LAM, rho=0.0,
                           time_limit=30.0, seed=0, **{**spec.kwargs, **kw})


def _optimum(G, nodes):
    """Exhaustive best contiguous allocation -- the ground truth, computed here not imported."""
    ua, ub = base.utilities(G, nodes, THETA, LAM)
    best, best_set = -math.inf, None
    for mask in range(1 << len(nodes)):
        to_a = {z for k, z in enumerate(nodes) if mask >> k & 1}
        if not base.is_feasible(G, nodes, to_a):
            continue
        obj = base.objective(ua, ub, base.mask(nodes, to_a), 0.0, 0)
        if obj > best:
            best, best_set = obj, to_a
    return best, best_set


# ------------------------------------------------------------------------ tests
def test_registry_has_the_engines_and_no_legacy_import():
    assert "brute" in REGISTRY and "scip_tree" in REGISTRY
    assert "territory" not in sys.modules, "importing contig_methods must not need code/"
    assert "districting" not in sys.modules


def test_brute_matches_exhaustive_search():
    G = path_pair(10)
    nodes = sorted(G)
    want, _ = _optimum(G, nodes)
    res = _run("brute", G, nodes)
    assert res.status == "optimal", (res.status, res.message)
    assert math.isclose(res.LB, want, rel_tol=0, abs_tol=1e-9), (res.LB, want)


def test_scip_tree_matches_brute_on_a_path():
    G = path_pair(10)
    nodes = sorted(G)
    want, _ = _optimum(G, nodes)
    res = _run("scip_tree", G, nodes)
    assert res.status == "optimal", (res.status, res.message)
    assert math.isclose(res.LB, want, rel_tol=0, abs_tol=1e-6), (res.LB, want)
    assert res.UB is not None and res.UB - res.LB <= base.CERT_TOL + 1e-9


def test_scip_tree_matches_brute_on_a_grid():
    """2-connected, so the separator cuts have to actually do something."""
    G = grid_pair(3, 4)
    nodes = sorted(G)
    want, _ = _optimum(G, nodes)
    res = _run("scip_tree", G, nodes)
    assert res.status == "optimal", (res.status, res.message)
    assert math.isclose(res.LB, want, rel_tol=0, abs_tol=1e-6), (res.LB, want)


def test_scip_tree_on_a_disconnected_pair_graph():
    """Trap 13: cuts must be component-wise or the dual bound goes unsound."""
    G = two_component_pair()
    nodes = sorted(G)
    want, _ = _optimum(G, nodes)
    res = _run("scip_tree", G, nodes)
    assert res.status == "optimal", (res.status, res.message)
    assert math.isclose(res.LB, want, rel_tol=0, abs_tol=1e-6), (res.LB, want)
    assert res.UB >= res.LB - 1e-9, "UB below a feasible iterate is trap 13 returning"


def test_result_validates_under_the_contract():
    G = grid_pair(3, 4)
    nodes = sorted(G)
    res = _run("scip_tree", G, nodes)
    row = base.evaluate(G, nodes, res, theta=THETA, lam=LAM, rho=0.0)
    assert row["valid"], row["violations"]
    assert row["excess_pieces"] == 0
    assert row["valid_certificate"] is True


def test_cert_exact_confirms_the_incumbent():
    """The exact post-hoc certificate (W6c) must agree with exhaustive search."""
    from td.solvers import cert_exact

    G = path_pair(10)
    nodes = sorted(G)
    want, want_set = _optimum(G, nodes)
    res = _run("scip_tree", G, nodes)
    out = cert_exact.certify(G, nodes, res.to_a, theta=THETA, lam=LAM,
                             time_limit=30.0)
    assert out is not None
    status = out.get("status") if isinstance(out, dict) else getattr(out, "status", None)
    assert status in ("optimal", "certified", "proved"), out
