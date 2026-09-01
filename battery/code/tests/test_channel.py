"""
test_channel.py -- the national-channel two-stage problem (contig_methods/channel.py).

The load-bearing test is `test_nash_welfare_is_equal_size_districting`: on a common measure,
max sum_j log M_j is attained exactly at the equal split.  That identity is the reason the
~$1B target does not need to be a constraint, so it is asserted rather than asserted-about.
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

from contig_methods import channel, nway        # noqa: E402

THETA, LAM = 0.40, 0.30


def opportunity_path(n=12, reps=("R0", "R1", "R2")):
    """P_n where each rep's book sits in its own stretch; opportunity dominates utility."""
    G = nx.path_graph(n)
    per = max(n // len(reps), 1)
    for i in range(n):
        owner = reps[min(i // per, len(reps) - 1)]
        S = {owner: 4.0}
        G.nodes[i].update(cand=(owner,), S=S, M=100.0)     # 4% saturation, as in practice
    return G


# ------------------------------------------------------------- the stage-1 identity
def test_nash_welfare_is_equal_size_districting():
    """max sum_j log M_j over partitions is attained exactly at the equal split.

    Brute force over every way of cutting P_12 into 3 contiguous blocks: the argmax of the
    Nash objective is the balanced one.  This is the whole justification for treating $1B as
    an emergent target rather than a constraint.
    """
    G = opportunity_path(12)
    n = 12
    best, best_cut = -math.inf, None
    for a in range(1, n - 1):
        for b in range(a + 1, n):
            to_d = {z: (0 if z < a else 1 if z < b else 2) for z in range(n)}
            M = channel.district_opportunity(G, to_d)
            val = sum(math.log(v) for v in M.values())
            if val > best:
                best, best_cut = val, (a, b)
    assert best_cut == (4, 8), best_cut          # the equal split of 12 into 3
    bal = channel.balance_report(G, {z: (0 if z < 4 else 1 if z < 8 else 2) for z in range(n)})
    assert bal["spread_rel"] == 0.0
    assert math.isclose(bal["log_sum"], best, rel_tol=0, abs_tol=1e-12)


def test_unequal_split_scores_worse():
    G = opportunity_path(12)
    equal = {z: (0 if z < 4 else 1 if z < 8 else 2) for z in range(12)}
    skewed = {z: (0 if z < 2 else 1 if z < 6 else 2) for z in range(12)}
    assert (channel.balance_report(G, equal)["log_sum"]
            > channel.balance_report(G, skewed)["log_sum"])
    assert (channel.balance_report(G, equal)["spread_rel"]
            < channel.balance_report(G, skewed)["spread_rel"])


def test_balance_report_fields():
    G = opportunity_path(12)
    bal = channel.balance_report(G, {z: z // 4 for z in range(12)}, target=400.0)
    assert bal["k"] == 3 and bal["total"] == 1200.0
    assert bal["min"] == bal["max"] == 400.0
    assert bal["max_dev_rel"] == 0.0


# ------------------------------------------------------------------------ stage 2
def test_matching_puts_each_rep_on_its_own_book():
    """The obvious answer must come out: every rep gets the district holding its book."""
    G = opportunity_path(12, reps=("R0", "R1", "R2"))
    to_d = {z: z // 4 for z in range(12)}
    res = channel.stage2(G, to_d, theta=THETA, lam=LAM)
    assert res["assignment"] == {0: "R0", 1: "R1", 2: "R2"}, res["assignment"]
    assert not res["unmatched_reps"] and not res["unstaffed_districts"]


def test_nash_and_utilitarian_agree_here_but_are_different_objectives():
    G = opportunity_path(12)
    to_d = {z: z // 4 for z in range(12)}
    a = channel.stage2(G, to_d, criterion="nash", theta=THETA, lam=LAM)
    b = channel.stage2(G, to_d, criterion="utilitarian", theta=THETA, lam=LAM)
    assert a["assignment"] == b["assignment"]
    assert a["value"] != b["value"]              # sum log g vs sum g


def test_rectangular_matching_selects_which_reps_to_retain():
    """More reps than districts: the unmatched ones are exactly the not-retained."""
    G = opportunity_path(12, reps=("R0", "R1", "R2"))
    G.add_node(99, cand=("R3",), S={"R3": 4.0}, M=100.0)
    G.add_edge(11, 99)
    to_d = {z: min(z // 4, 2) for z in range(12)}
    to_d[99] = 2                                  # R3's zip folded into district 2
    res = channel.stage2(G, to_d, theta=THETA, lam=LAM)
    assert len(res["assignment"]) == 3
    assert len(res["unmatched_reps"]) == 1
    assert not res["unstaffed_districts"]
    assert set(res["assignment"].values()) | set(res["unmatched_reps"]) == {
        "R0", "R1", "R2", "R3"}


def test_gain_matrix_evaluates_every_rep_on_every_district():
    """Staffing is not limited by legacy candidacy -- that is the point of drawing first."""
    G = opportunity_path(12)
    to_d = {z: z // 4 for z in range(12)}
    g, R, D = channel.gain_matrix(G, to_d, theta=THETA, lam=LAM)
    assert g.shape == (len(R), len(D)) == (3, 3)
    assert D == [0, 1, 2], D                      # district order must not be str-sorted
    assert (g > 0).all(), "every rep must have positive utility on every district"
    for i, r in enumerate(R):                     # own district beats the others
        own = D.index(int(r[1:]))
        assert g[i, own] == g[i].max(), (r, g[i])


def test_gain_matrix_matches_a_hand_sum():
    G = opportunity_path(12)
    to_d = {z: z // 4 for z in range(12)}
    g, R, D = channel.gain_matrix(G, to_d, theta=THETA, lam=LAM)
    c1, c2 = 1.0 - LAM, THETA * (1.0 - LAM)
    for i, r in enumerate(R):
        for j, d in enumerate(D):
            want = 0.0
            for z in (z for z in to_d if to_d[z] == d):
                S = nway.books(G, z)
                T = sum(S.values())
                s = float(S.get(r, 0.0))
                want += c1 * s + c2 * (T - s) + LAM * G.nodes[z]["M"]
            assert math.isclose(g[i, j], want, rel_tol=0, abs_tol=1e-9), (r, d)


def test_unowned_book_reaches_stage2():
    """S_free raises every rep's utility on the district holding it."""
    G = opportunity_path(12)
    to_d = {z: z // 4 for z in range(12)}
    g0, R, D = channel.gain_matrix(G, to_d, theta=THETA, lam=LAM)
    for z in range(4):
        G.nodes[z]["S_free"] = 10.0
    g1, _, _ = channel.gain_matrix(G, to_d, reps_order=R, districts=D, theta=THETA, lam=LAM)
    assert (g1[:, 0] > g0[:, 0]).all()
    assert np.allclose(g1[:, 1:], g0[:, 1:])


def test_nash_match_rejects_a_zero_gain():
    g = np.array([[1.0, 2.0], [0.0, 3.0]])
    try:
        channel.match(g, "nash")
    except ValueError as e:
        assert "positive" in str(e)
    else:
        raise AssertionError("expected ValueError on a zero gain under nash matching")


def test_score_draws_ranks_best_first():
    G = opportunity_path(12)
    draws = [{z: z // 4 for z in range(12)},                      # balanced
             {z: (0 if z < 2 else 1 if z < 6 else 2) for z in range(12)}]   # skewed
    ranked = channel.score_draws(G, draws, theta=THETA, lam=LAM)
    assert [r["draw"] for r in ranked] == [0, 1], [r["value"] for r in ranked]
    assert ranked[0]["value"] >= ranked[1]["value"]


def test_empty_input_is_not_a_crash():
    G = opportunity_path(4)
    res = channel.stage2(G, {}, theta=THETA, lam=LAM)
    assert res["assignment"] == {} and res["balance"]["k"] == 0
