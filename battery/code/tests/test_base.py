"""
test_base.py -- the contract (contig_methods/base.py) and its registry (PLAN.md U1a).

Hand instances only; no solver.  Acceptance: validator negative cases fire, the fake
method hits every status, the harness wrapper survives an error and a hang.
"""
from __future__ import annotations

import math
import os
import sys

import networkx as nx
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
for p in (os.path.join(ROOT, "code"), os.path.join(ROOT, "battery", "code")):
    if p not in sys.path:
        sys.path.insert(0, p)

import territory as T                       # noqa: E402
from contig_methods import REGISTRY, base   # noqa: E402

THETA, LAM = 0.40, 0.30


# ------------------------------------------------------------------ hand instances
def path_instance(n=8, state=None):
    """P_n with monotone utility ratio along the path (prefixes are contiguous)."""
    G = nx.path_graph(n)
    for i in range(n):
        A = 1.0 + 0.9 * (n - 1 - i) / (n - 1)      # a-heavy at the left end
        B = 1.0 + 0.9 * i / (n - 1)                # b-heavy at the right end
        G.nodes[i].update(A=A, B=B, M=4.0 + 0.1 * i, pos=(i / n, 0.5))
        if state is not None:
            G.nodes[i]["state"] = state(i)
    return G


def two_component_instance():
    """Two disjoint paths P4 + P3 -- the pair graph itself is disconnected (C.0 #1)."""
    G = path_instance(4)
    H = nx.relabel_nodes(path_instance(3), {0: 10, 1: 11, 2: 12})
    return nx.union(G, H)


def glue_instance():
    """P6 with two zero-value zips in the middle (regime (d))."""
    G = path_instance(6)
    for z in (2, 3):
        G.nodes[z].update(A=0.0, B=0.0, M=0.0)
    return G


def ua_ub(G):
    nodes = sorted(G)
    return nodes, *base.utilities(G, nodes, THETA, LAM)


# ------------------------------------------------------------------------- utilities
def test_utilities_match_territory_fields():
    G = path_instance()
    nodes, ua, ub = ua_ub(G)
    _, _, _, ua_t, ub_t = T._fields(G, nodes, THETA, LAM)
    assert np.array_equal(ua, ua_t) and np.array_equal(ub, ub_t)


def test_utilities_kappa_needs_distances_and_subtracts_them():
    G = path_instance()
    nodes = sorted(G)
    try:
        base.utilities(G, nodes, THETA, LAM, kappa=0.1)
        raise AssertionError("kappa > 0 without d_a/d_b should raise")
    except KeyError:
        pass
    for z in nodes:
        G.nodes[z].update(d_a=float(z), d_b=float(len(nodes) - z))
    ua0, ub0 = base.utilities(G, nodes, THETA, LAM)
    ua1, ub1 = base.utilities(G, nodes, THETA, LAM, kappa=0.1)
    assert np.allclose(ua0 - ua1, 0.1 * np.arange(len(nodes)))
    assert np.allclose(ub0 - ub1, 0.1 * (len(nodes) - np.arange(len(nodes))))


def test_ratio_guard():
    r = base.ratio(np.array([2.0, 1.0, 0.0]), np.array([1.0, 0.0, 0.0]))
    assert r[0] == 2.0 and r[1] == math.inf and r[2] == 1.0


def test_objective_and_rescale_shift():
    G = path_instance()
    nodes, ua, ub = ua_ub(G)
    x = base.mask(nodes, {0, 1, 2})
    obj = base.objective(ua, ub, x, rho=0.0)
    H, s = base.rescale_pair(G, nodes, THETA, LAM)
    ua2, ub2 = base.utilities(H, nodes, THETA, LAM)
    assert abs(ua2.sum() + ub2.sum() - base.RESCALE_TARGET) < 1e-9
    assert abs(base.objective(ua2, ub2, x) - (obj + 2 * math.log(s))) < 1e-9
    assert base.objective(ua, ub, base.mask(nodes, set())) == -math.inf
    assert G.nodes[0]["A"] != H.nodes[0]["A"]          # copy, not in place


# --------------------------------------------------------------------- geometry
def test_pieces_and_perimeter_on_path():
    G = path_instance(8)
    nodes = sorted(G)
    p = base.pieces(G, nodes, {0, 1, 2})
    assert p == dict(pair_components=1, pieces_a=1, pieces_b=1, excess_pieces=0)
    assert base.perimeter(G, nodes, {0, 1, 2}) == 1
    p = base.pieces(G, nodes, {0, 1, 5, 6})
    assert (p["pieces_a"], p["pieces_b"], p["excess_pieces"]) == (2, 2, 2)
    assert base.perimeter(G, nodes, {0, 1, 5, 6}) == 3
    assert base.pieces(G, nodes, set())["pieces_a"] == 0
    assert base.is_feasible(G, nodes, set(nodes))


def test_pieces_component_wise_feasibility():
    G = two_component_instance()
    nodes = sorted(G)
    # one connected piece per side inside each component -> feasible although pieces_a == 2
    p = base.pieces(G, nodes, {0, 1, 10})
    assert p["pair_components"] == 2 and p["pieces_a"] == 2 and p["pieces_b"] == 2
    assert p["excess_pieces"] == 0 and base.is_feasible(G, nodes, {0, 1, 10})
    # a whole component to one side is fine too
    assert base.is_feasible(G, nodes, {0, 1, 2, 3})
    # two a-pieces inside one component is not
    assert not base.is_feasible(G, nodes, {0, 3, 10})


def test_filter_pair_state_edges():
    G = path_instance(8, state=lambda i: "E" if i < 4 else "W")
    nodes = sorted(G)
    H, share = base.filter_pair(G, nodes, respect_state=False)
    assert H.number_of_edges() == 7 and share == 0.0
    assert set(H.nodes[0]) <= {"A", "B", "M", "state", "pos"}
    H, share = base.filter_pair(G, nodes, respect_state=True)
    assert H.number_of_edges() == 6 and abs(share - 1 / 7) < 1e-12
    assert base.check_state_filter(H, True) == []
    assert base.check_state_filter(G, True) != []
    G2 = path_instance(4)
    try:
        base.filter_pair(G2, sorted(G2), respect_state=True)
        raise AssertionError("missing state must raise")
    except ValueError:
        pass


# --------------------------------------------------------------------- fairness
def test_fairness_hand_case():
    ua = np.array([3.0, 1.0, 1.0]); ub = np.array([1.0, 1.0, 3.0])
    x = np.array([True, False, False])
    f = base.fairness(ua, ub, x)
    # a: g_a = 3, sees 2 on b's side, max 1 -> 2 - 1 <= 3 : EF1 (and envy-free)
    # b: g_b = 4, sees 1 on a's side -> EF
    assert f["ef1"] and f["envy_over_umax"] == 0.0
    assert f["prop_shortfall_a"] == 0.0 and f["prop_shortfall_b"] == 0.0
    x = np.array([False, False, False])       # a gets nothing
    f = base.fairness(ua, ub, x)
    assert not f["ef1_ab"] and f["ef1_ba"]
    assert abs(f["envy_over_umax"] - 5.0 / 3.0) < 1e-12       # envy 5 over u_max 3
    assert abs(f["prop_shortfall_a"] - 2.5 / 3.0) < 1e-12


# -------------------------------------------------------------------- covariates
def test_block_tree_is_path():
    assert base.block_tree_is_path(nx.path_graph(6))
    assert base.block_tree_is_path(nx.cycle_graph(6))
    bowtie = nx.Graph([(0, 1), (1, 2), (2, 0), (2, 3), (3, 4), (4, 2)])
    assert base.block_tree_is_path(bowtie)
    star = nx.star_graph(3)                    # cut vertex of degree 3 in the block tree
    assert not base.block_tree_is_path(star)
    assert base.block_tree_is_path(nx.union(nx.path_graph(3), nx.relabel_nodes(nx.cycle_graph(3), {0: 9, 1: 8, 2: 7})))


def test_covariates_fields():
    G = glue_instance()
    nodes, ua, ub = ua_ub(G)
    c = base.covariates(G, nodes, ua, ub, free_to_a={0, 1})
    assert c["n"] == 6 and c["n_edges"] == 5 and c["pair_components"] == 1
    assert c["articulation_points"] == 4 and c["block_tree_is_path"]
    assert abs(c["active_frac"] - 4 / 6) < 1e-12
    assert 0 <= c["gini_u"] < 1 and 0 < c["top5_share_u"] <= 1
    assert c["free_pieces_a"] == 1 and c["free_perimeter"] == 1 and c["n_states"] == 0


# --------------------------------------------------------------------- Result
def test_result_rejects_bad_status():
    for bad in (dict(status="solved"), dict(status="optimal", ub_scope="local")):
        try:
            base.Result(**bad)
            raise AssertionError(f"{bad} accepted")
        except ValueError:
            pass
    r = base.Result("heuristic", to_a=[3, 1, 2])
    assert isinstance(r.to_a, set) and r.to_json()["to_a"] == [1, 2, 3]


def test_trace_bookkeeping():
    tr = base.Trace()
    tr.incumbent({1}, -2.0); tr.incumbent({1, 2}, -1.0); tr.incumbent({3}, -1.5); tr.bound(0.5); tr.bound(0.7)
    assert tr.best_lb == -1.0 and tr.best_to_a == {1, 2} and tr.best_ub == 0.5
    assert tr.t_first_feasible is not None and len(tr.rows()) == 5
    assert tr.rows()[-1][1:] == (-1.0, 0.5)


# ------------------------------------------------------------- registry + fake method
def test_registry_discovers_fake_and_variants():
    assert "fake" in REGISTRY and REGISTRY["fake"].exact
    assert "fake_optimal" in REGISTRY and REGISTRY["fake_optimal"].kwargs == dict(behaviour="optimal")
    assert REGISTRY["fake_hang"].base_name == "fake"


def _run(behaviour, G=None, **kw):
    G = path_instance() if G is None else G
    nodes = sorted(G)
    spec = REGISTRY[f"fake_{behaviour}"]
    res = base.run_method(spec.solve, G, nodes, theta=THETA, lam=LAM, rho=0.0,
                          time_limit=kw.pop("time_limit", 5.0), backstop=kw.pop("backstop", None),
                          **spec.kwargs)
    ua, ub = base.utilities(G, nodes, THETA, LAM)
    free = T.nash_exact(*[np.array([G.nodes[z][k] for z in nodes]) for k in "ABM"], THETA, LAM)
    row = base.evaluate(G, nodes, res, theta=THETA, lam=LAM, rho=0.0,
                        product_free=free["product"], **kw)
    return res, row


def test_fake_hits_every_status():
    seen = {}
    for b in ("optimal", "gap_limit", "time_limit", "iteration_limit", "heuristic", "infeasible", "error"):
        res, row = _run(b)
        seen[res.status] = row
        assert res.t_total is not None and isinstance(res.trace, list)
    assert set(seen) == set(base.STATUSES), sorted(seen)
    ok = seen["optimal"]
    assert ok["valid"] and ok["valid_certificate"] and ok["status_eff"] == "optimal"
    assert ok["excess_pieces"] == 0 and abs(ok["gap_nats"]) < 1e-12 and ok["cost_of_contiguity"] >= -1e-12
    assert abs(ok["LB"] - ok["LB_claimed"]) < 1e-12
    tl = seen["time_limit"]
    assert tl["valid"] and tl["LB"] is None and tl["feasible"] is False and tl["obj_iterate"] is not None
    assert tl["gap_nats"] is None and tl["excess_pieces"] > 0
    il = seen["iteration_limit"]
    assert il["valid"] and il["gap_nats"] > base.CERT_TOL and not il["valid_certificate"]
    assert seen["heuristic"]["valid"] and seen["heuristic"]["gap_nats"] is None
    gl = seen["gap_limit"]
    assert gl["valid"] and abs(gl["gap_nats"] - 5e-4) < 1e-12 and not gl["valid_certificate"]
    assert seen["infeasible"]["valid"] and seen["infeasible"]["to_a"] is None if "to_a" in seen["infeasible"] else True
    err = seen["error"]
    assert err["valid"] and "RuntimeError" in err["message"]


def test_rooted_certificate_is_downgraded():
    res, row = _run("optimal_rooted")
    assert res.status == "optimal" and row["status_eff"] == "optimal_rooted"
    assert row["valid"] and not row["valid_certificate"]


def test_validator_negative_cases():
    expect = {
        "lie_lb": "LB claimed",
        "lie_pieces": "excess_pieces",
        "lie_gap": "gap_nats",
        "lie_outside": "outside the pair",
        "lie_heuristic_ub": "heuristic must report UB=None",
    }
    for b, needle in expect.items():
        res, row = _run(b)
        assert not row["valid"], b
        assert any(needle in v for v in row["violations"]), (b, row["violations"])
    # LB above the cross-method global UB* is a bug flag
    _, row = _run("optimal", UB_star_global=-100.0)
    assert not row["valid"] and any("UB*" in v for v in row["violations"])
    # a free product below the incumbent's product is a violation too
    G = path_instance(); nodes = sorted(G)
    res = REGISTRY["fake_optimal"].solve(G, nodes, theta=THETA, lam=LAM, rho=0.0, respect_state=False,
                                         time_limit=1, seed=0, behaviour="optimal")
    row = base.evaluate(G, nodes, res, product_free=1e-6)
    assert any("exceeds free product" in v for v in row["violations"])
    # state filter check
    Gs = path_instance(8, state=lambda i: "E" if i < 4 else "W")
    row = base.evaluate(Gs, sorted(Gs), res, respect_state=True)
    assert any("cross-state" in v for v in row["violations"])


def test_backstop_recovers_incumbent_from_trace():
    res, row = _run("hang", time_limit=0.05, backstop=lambda cap: 0.3)
    assert res.status == "time_limit" and "backstop" in res.message
    assert res.to_a is not None and res.LB is not None and row["valid"]
    assert res.t_total < 2.0 and res.t_first_feasible is not None


def test_fake_on_disconnected_pair_and_glue():
    for G in (two_component_instance(), glue_instance()):
        res, row = _run("optimal", G=G)
        assert row["valid"] and row["valid_certificate"], row["violations"]
        assert row["excess_pieces"] == 0
