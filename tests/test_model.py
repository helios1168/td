"""
test_nway.py -- the N-way primitives (contig_methods/model.py; NWAY.md Phase 1).

Hand instances only; no solver.  The load-bearing test is `test_two_rep_reduction`: on a
two-rep graph every N-way primitive must agree with `base.py` to floating-point equality.
That is what lets the existing two-player corpus stay interpretable under the new model.
"""
from __future__ import annotations

import math
import os
import sys

import networkx as nx
import numpy as np


from td import model
from td.solvers import base       # noqa: E402

THETA, LAM = 0.40, 0.30


# ------------------------------------------------------------------ hand instances
def two_rep_path(n=8):
    """The `test_base.path_instance` shape: legacy rep_a/rep_b + A/B, no `cand`/`S`."""
    G = nx.path_graph(n)
    for i in range(n):
        G.nodes[i].update(rep_a="A1", rep_b="B1",
                          A=1.0 + 0.9 * (n - 1 - i) / (n - 1),
                          B=1.0 + 0.9 * i / (n - 1),
                          M=4.0 + 0.1 * i)
    return G


def three_rep_path(n=9):
    """P_n where the middle third is contested by a third rep C1.

    Candidate sets: {A1,B1} on the ends, {A1,B1,C1} in the middle -- so the instance
    exercises ragged candidate sets, not just a uniform k.
    """
    G = nx.path_graph(n)
    third = n // 3
    for i in range(n):
        mid = third <= i < 2 * third
        S = {"A1": 1.0 + 0.9 * (n - 1 - i) / (n - 1), "B1": 1.0 + 0.9 * i / (n - 1)}
        cand = ["A1", "B1"]
        if mid:
            S["C1"] = 1.2
            cand.append("C1")
        T = sum(S.values())
        need = max(s + THETA * (T - s) for s in S.values())
        G.nodes[i].update(cand=tuple(cand), S=S, M=need + 1.0)
    return G


def uniform_three_rep_triangle():
    """K3 where every node is contested by all three reps -- the densest small case."""
    G = nx.complete_graph(3)
    for i in range(3):
        S = {"A1": 1.0 + i, "B1": 2.0, "C1": 3.0 - i}
        T = sum(S.values())
        need = max(s + THETA * (T - s) for s in S.values())
        G.nodes[i].update(cand=("A1", "B1", "C1"), S=S, M=need + 0.5)
    return G


# ------------------------------------------------------------------------ tests
def test_two_rep_reduction():
    """Every N-way primitive equals its `base.py` counterpart on a two-rep graph."""
    G = two_rep_path(8)
    nodes = sorted(G)
    ua, ub = base.utilities(G, nodes, THETA, LAM)
    U, R = model.utilities(G, nodes, theta=THETA, lam=LAM)
    assert R == ["A1", "B1"], R
    assert np.allclose(U[0], ua), (U[0], ua)
    assert np.allclose(U[1], ub), (U[1], ub)

    # a handful of allocations, contiguous and not
    for to_a in ({0, 1, 2}, {0, 1, 2, 3, 4}, set(), set(nodes), {0, 5}):
        to_owner = model.to_owner_from_to_a(nodes, to_a, "A1", "B1")
        oi = model.owner_index(nodes, to_owner, R)
        x = base.mask(nodes, to_a)

        ga, gb = base.gains(ua, ub, x)
        g = model.gains(U, oi)
        assert math.isclose(g[0], ga, rel_tol=0, abs_tol=1e-12), (g[0], ga)
        assert math.isclose(g[1], gb, rel_tol=0, abs_tol=1e-12), (g[1], gb)

        assert model.perimeter(G, nodes, to_owner) == base.perimeter(G, nodes, to_a)

        for rho in (0.0, 2e-3):
            per = base.perimeter(G, nodes, to_a)
            o_base = base.objective(ua, ub, x, rho, per)
            o_nway = model.objective(U, oi, rho, per)
            if math.isinf(o_base):
                assert math.isinf(o_nway)
            else:
                assert math.isclose(o_nway, o_base, rel_tol=0, abs_tol=1e-12)

        pb = base.pieces(G, nodes, to_a)
        pn = model.pieces(G, nodes, to_owner)
        assert pn["pair_components"] == pb["pair_components"]
        assert pn["excess_pieces"] == pb["excess_pieces"], (pn, pb, to_a)
        assert model.is_feasible(G, nodes, to_owner) == base.is_feasible(G, nodes, to_a)


def test_two_rep_reduction_disconnected():
    """The reduction also holds when the subproblem graph is itself disconnected (C.0 #1)."""
    G = two_rep_path(4)
    H = nx.relabel_nodes(two_rep_path(3), {0: 10, 1: 11, 2: 12})
    G = nx.union(G, H)
    nodes = sorted(G)
    ua, ub = base.utilities(G, nodes, THETA, LAM)
    U, R = model.utilities(G, nodes, theta=THETA, lam=LAM)
    for to_a in ({0, 1, 10}, {0, 2, 11}, {0, 1, 2, 3}):
        to_owner = model.to_owner_from_to_a(nodes, to_a, "A1", "B1")
        pb = base.pieces(G, nodes, to_a)
        pn = model.pieces(G, nodes, to_owner)
        assert pn["excess_pieces"] == pb["excess_pieces"], (to_a, pn, pb)
        assert pn["pair_components"] == pb["pair_components"]


def test_round_trip_to_a():
    G = two_rep_path(6)
    nodes = sorted(G)
    to_a = {0, 1, 4}
    to_owner = model.to_owner_from_to_a(nodes, to_a, "A1", "B1")
    assert model.to_a_from_to_owner(nodes, to_owner, "A1") == to_a


def test_candidates_and_books_shim():
    """Legacy nodes read as two candidates; native nodes read their own fields."""
    G = two_rep_path(3)
    assert model.candidates(G, 0) == ("A1", "B1")
    assert set(model.books(G, 0)) == {"A1", "B1"}
    H = three_rep_path(9)
    assert model.candidates(H, 0) == ("A1", "B1")
    assert model.candidates(H, 4) == ("A1", "B1", "C1")
    assert model.reps(H, sorted(H)) == ["A1", "B1", "C1"]


def test_utilities_zero_off_candidate():
    """A rep gets 0 on zips it cannot own, so `gains` stays a plain masked sum."""
    G = three_rep_path(9)
    nodes = sorted(G)
    U, R = model.utilities(G, nodes, theta=THETA, lam=LAM)
    C = model.candidate_matrix(G, nodes, R)
    assert (U[~C] == 0).all()
    assert (U[C] > 0).all()


def test_utility_formula_by_hand():
    """u_i = c1*S_i + c2*(T - S_i) + lam*M, checked against an arithmetic evaluation."""
    G = uniform_three_rep_triangle()
    nodes = sorted(G)
    U, R = model.utilities(G, nodes, theta=THETA, lam=LAM)
    c1, c2 = 1.0 - LAM, THETA * (1.0 - LAM)
    for j, z in enumerate(nodes):
        S = model.books(G, z)
        Tz = sum(S.values())
        for k, i in enumerate(R):
            want = c1 * S[i] + c2 * (Tz - S[i]) + LAM * G.nodes[z]["M"]
            assert math.isclose(U[k, j], want, rel_tol=0, abs_tol=1e-12)


def test_objective_minus_inf_on_starved_rep():
    """A rep with an empty bundle sends sum log g to -inf (NWAY.md 6.1)."""
    G = uniform_three_rep_triangle()
    nodes = sorted(G)
    U, R = model.utilities(G, nodes, theta=THETA, lam=LAM)
    starved = {z: "A1" for z in nodes}                 # B1 and C1 get nothing
    oi = model.owner_index(nodes, starved, R)
    assert math.isinf(model.objective(U, oi))
    spread = dict(zip(nodes, R))                       # one node each
    oi2 = model.owner_index(nodes, spread, R)
    assert math.isfinite(model.objective(U, oi2))


def test_pieces_detects_disconnected_rep():
    """A rep holding two separated stretches of a path is caught by excess_pieces."""
    G = three_rep_path(9)
    nodes = sorted(G)
    good = {z: ("A1" if z < 3 else "C1" if z < 6 else "B1") for z in nodes}
    assert model.pieces(G, nodes, good)["excess_pieces"] == 0
    assert model.is_feasible(G, nodes, good)
    split = dict(good)
    split[0], split[8] = "A1", "A1"
    split[1], split[2] = "B1", "B1"                    # A1 now holds {0} and nothing adjacent
    assert model.pieces(G, nodes, split)["excess_pieces"] > 0
    assert not model.is_feasible(G, nodes, split)


def test_is_feasible_rejects_non_candidate():
    G = three_rep_path(9)
    nodes = sorted(G)
    bad = {z: "C1" for z in nodes}                     # C1 is not a candidate at the ends
    assert not model.is_feasible(G, nodes, bad)
    v = model.violations(G, nodes, bad)
    assert any("non-candidate" in s for s in v), v


def test_violations_reports_unassigned():
    G = three_rep_path(9)
    nodes = sorted(G)
    partial = {z: "A1" for z in nodes[:4]}
    v = model.violations(G, nodes, partial)
    assert any("unassigned" in s for s in v), v


def test_headroom_violations():
    G = uniform_three_rep_triangle()
    assert model.headroom_violations(G, theta=THETA) == []
    G.nodes[0]["M"] = 0.0
    bad = model.headroom_violations(G, theta=THETA)
    assert [z for z, *_ in bad] == [0], bad


def test_headroom_matches_two_rep_condition():
    """At two reps the N-way condition is `M >= max(A + theta*B, B + theta*A)`."""
    G = two_rep_path(5)
    assert model.headroom_violations(G, theta=THETA) == []
    G.nodes[2]["M"] = 0.0
    A, B = G.nodes[2]["A"], G.nodes[2]["B"]
    assert max(A + THETA * B, B + THETA * A) > 0
    assert [z for z, *_ in model.headroom_violations(G, theta=THETA)] == [2]


def test_fairness_reduces_to_base_ef1():
    """EF1 verdict matches `base.fairness` on two-rep allocations."""
    G = two_rep_path(8)
    nodes = sorted(G)
    ua, ub = base.utilities(G, nodes, THETA, LAM)
    U, R = model.utilities(G, nodes, theta=THETA, lam=LAM)
    for to_a in ({0, 1, 2, 3}, {0}, {0, 1, 2, 3, 4, 5, 6}):
        x = base.mask(nodes, to_a)
        to_owner = model.to_owner_from_to_a(nodes, to_a, "A1", "B1")
        oi = model.owner_index(nodes, to_owner, R)
        assert model.fairness(U, oi)["ef1"] == base.fairness(ua, ub, x)["ef1"], to_a


def test_fairness_three_rep_runs():
    """The n-agent EF1 audit is well defined on a genuine 3-rep allocation."""
    G = three_rep_path(9)
    nodes = sorted(G)
    U, R = model.utilities(G, nodes, theta=THETA, lam=LAM)
    alloc = {z: ("A1" if z < 3 else "C1" if z < 6 else "B1") for z in nodes}
    f = model.fairness(U, model.owner_index(nodes, alloc, R))
    assert set(f) == {"ef1", "n_ef1_failures", "envy_over_umax", "prop_shortfall"}
    assert f["envy_over_umax"] >= 0.0
    assert isinstance(f["ef1"], bool)


def test_reps_order_is_deterministic():
    G = three_rep_path(9)
    nodes = sorted(G)
    assert model.reps(G, nodes) == model.reps(G, nodes)
    U1, R1 = model.utilities(G, nodes, theta=THETA, lam=LAM)
    U2, R2 = model.utilities(G, nodes, reps_order=R1, theta=THETA, lam=LAM)
    assert R1 == R2 and np.array_equal(U1, U2)


def test_candidate_arity_is_a_subproblem_matter_not_a_schema_one():
    """Empty and single candidate lists are legal; `is_contested` is the predicate.

    They were briefly a hard error, which made `candidates()` unusable on exactly the
    uncontested / vacant / untapped nodes the loader produces.
    """
    G = nx.path_graph(3)
    G.nodes[0].update(cand=(), S={}, M=5.0)
    G.nodes[1].update(cand=("A1",), S={"A1": 1.0}, M=5.0)
    G.nodes[2].update(cand=("A1", "B1"), S={"A1": 1.0, "B1": 2.0}, M=9.0)
    assert model.candidates(G, 0) == ()
    assert model.candidates(G, 1) == ("A1",)
    assert [model.is_contested(G, z) for z in (0, 1, 2)] == [False, False, True]


def test_duplicate_candidates_raise():
    G = nx.path_graph(1)
    G.nodes[0].update(cand=("A1", "A1"), S={"A1": 1.0}, M=5.0)
    try:
        model.candidates(G, 0)
    except ValueError as e:
        assert "duplicate" in str(e)
    else:
        raise AssertionError("expected ValueError for duplicate candidates")


# ------------------------------------------------------- unowned book (vacancy filler)
def filler_path(n=6):
    """Every zip contested by A1/B1, with a slab of book carrying no incumbent."""
    G = nx.path_graph(n)
    for i in range(n):
        S = {"A1": 1.0 + 0.5 * i, "B1": 2.0}
        free = 3.0
        T = sum(S.values()) + free
        need = max(v + THETA * (T - v) for v in list(S.values()) + [free])
        G.nodes[i].update(cand=("A1", "B1"), S=S, S_free=free, M=need + 1.0)
    return G


def test_filler_is_never_a_candidate_but_counts_as_book():
    """S_free raises every candidate's utility and adds no rep of its own."""
    G = filler_path()
    nodes = sorted(G)
    U, R = model.utilities(G, nodes, theta=THETA, lam=LAM)
    assert R == ["A1", "B1"], R                       # no phantom filler rep
    H = G.copy()
    for z in H:
        H.nodes[z]["S_free"] = 0.0
    U0, R0 = model.utilities(H, nodes, theta=THETA, lam=LAM)
    assert R0 == R
    assert (U > U0).all(), "unowned book must raise every candidate's utility"


def test_filler_capture_modes_are_ordered_and_exact():
    """c_free is c2 / c1 / lam, and full > theta because c1 > c2 for theta < 1."""
    G = filler_path()
    nodes = sorted(G)
    c1, c2 = 1.0 - LAM, THETA * (1.0 - LAM)
    got = {}
    for mode in ("theta", "full", "opportunity"):
        U, R = model.utilities(G, nodes, theta=THETA, lam=LAM, filler_capture=mode)
        got[mode] = U
    base = {"theta": c2, "full": c1, "opportunity": LAM}
    for mode, U in got.items():
        for j, z in enumerate(nodes):
            S = model.books(G, z)
            T = sum(S.values())
            free = model.free_book(G, z)
            for k, i in enumerate(R):
                want = (c1 * S[i] + c2 * (T - S[i]) + base[mode] * free
                        + LAM * G.nodes[z]["M"])
                assert math.isclose(U[k, j], want, rel_tol=0, abs_tol=1e-12), (mode, z, i)
    assert (got["full"] > got["theta"]).all()          # c1 > c2 whenever theta < 1


def test_filler_capture_rejects_unknown_mode():
    G = filler_path()
    try:
        model.utilities(G, sorted(G), theta=THETA, lam=LAM, filler_capture="whatever")
    except ValueError as e:
        assert "filler_capture" in str(e)
    else:
        raise AssertionError("expected ValueError for an unknown filler_capture")


def test_no_free_book_reduces_to_the_plain_model():
    """Absent S_free, every capture mode gives the two-rep answer -- no silent drift."""
    G = two_rep_path(8)
    nodes = sorted(G)
    ua, ub = base.utilities(G, nodes, THETA, LAM)
    for mode in ("theta", "full", "opportunity"):
        U, R = model.utilities(G, nodes, theta=THETA, lam=LAM, filler_capture=mode)
        assert np.allclose(U[0], ua) and np.allclose(U[1], ub), mode


def test_headroom_counts_the_unowned_book():
    G = filler_path()
    assert model.headroom_violations(G, theta=THETA) == []
    G.nodes[0]["S_free"] = 500.0
    assert [z for z, *_ in model.headroom_violations(G, theta=THETA)] == [0]
