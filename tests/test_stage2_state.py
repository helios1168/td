"""
test_stage2_state.py -- stage 2 at state x channel grain (td/stage2_state.py).

The load-bearing test is `test_state_gain_matches_channel_gain_matrix`: on an integral
whole-state plan the aggregated gain equals `channel.gain_matrix` on the projected instance,
exactly, because the utility is linear in the cell.  That identity is what lets a level-0
channel-plan move be scored without re-drawing the map, so it is asserted rather than
asserted-about.

`CellTable` is duck-typed here: `stage2_state` reads six attributes and never imports
`td.channels`, so a `SimpleNamespace` is a complete stand-in.
"""
from __future__ import annotations

import itertools
import math
import types

import networkx as nx
import numpy as np

from td import channel, channels as ch, model, stage2_state as s2s
from td.instance import Descaled

THETA, LAM = 0.40, 0.30
STATES = ["AZ", "CA", "NV"]
CHANNELS = ("N_WH", "N_FI", "WH", "FI")
REPS = ["R0", "R1", "R2"]


def cell_table():
    """3 states x 4 channels x 3 reps.  R2 holds no book anywhere (trap 4)."""
    M = np.array([[10.0, 8.0, 6.0, 4.0],           # AZ
                  [20.0, 16.0, 12.0, 8.0],         # CA
                  [5.0, 4.0, 3.0, 2.0]], float)    # NV
    S = np.zeros((3, 3, 4), float)
    S[0, 0, 0] = 1.0                                # R0 books national-WH in AZ
    S[0, 1, 0] = 2.0                                # and in CA
    S[1, 0, 2] = 1.0                                # R1 books WH in AZ
    S[1, 1, 2] = 2.0                                # and WH + FI in CA
    S[1, 1, 3] = 1.0
    S_free = np.array([[0.5, 0.5, 0.5, 0.5],
                       [1.0, 1.0, 1.0, 1.0],
                       [0.0, 0.0, 0.0, 0.0]], float)
    return types.SimpleNamespace(state_list=list(STATES), channels=CHANNELS,
                                 reps=list(REPS), M=M, S=S, S_free=S_free)


def two_slot_plan():
    """A national slot over all three states, a WH+FI slot splitting AZ, and one unused."""
    return s2s.Plan(
        slots=[s2s.Slot(("N_WH", "N_FI"), {"AZ": 1.0, "CA": 1.0, "NV": 1.0}, True),
               s2s.Slot(("WH", "FI"), {"AZ": 0.5, "NV": 1.0}, True),
               s2s.Slot(("WH", "FI"), {}, False)],
        state_list=list(STATES))


# --------------------------------------------------------------- the refactored block
def test_coefficients_are_the_values_gain_matrix_used():
    for fc, want in (("theta", (0.7, 0.28, 0.28)), ("full", (0.7, 0.28, 0.7)),
                     ("opportunity", (0.7, 0.28, 0.3))):
        got = model.coefficients(THETA, LAM, fc)
        assert np.allclose(got, want, rtol=0, atol=1e-12), (fc, got)
    for fc in model.FILLER_CAPTURE:
        c1, c2, c_free = model.coefficients(THETA, LAM, fc)
        assert (c1, c2) == (1.0 - LAM, THETA * (1.0 - LAM))
        assert c_free == {"theta": c2, "full": c1, "opportunity": LAM}[fc]


def test_coefficients_rejects_an_unknown_filler_capture():
    try:
        model.coefficients(THETA, LAM, "nonsense")
    except ValueError as e:
        assert "filler_capture" in str(e)
    else:
        raise AssertionError("an unknown filler_capture must raise")


# ------------------------------------------------------------------------- utilities
def test_state_utilities_by_hand():
    cells = cell_table()
    u = s2s.state_utilities(cells, theta=THETA, lam=LAM, filler_capture="theta")
    assert u.shape == (3, 3, 4)
    # R0 at (AZ, N_WH): S = 1, T = 1, S_free = 0.5, M = 10
    #   0.7*1 + 0.28*(1 - 1) + 0.28*0.5 + 0.3*10
    assert math.isclose(u[0, 0, 0], 0.7 + 0.0 + 0.14 + 3.0, rel_tol=0, abs_tol=1e-12)
    # R2 at (AZ, WH): no book of its own, T = 1 (R1's), S_free = 0.5, M = 6
    assert math.isclose(u[2, 0, 2], 0.28 * 1.0 + 0.14 + 1.8, rel_tol=0, abs_tol=1e-12)
    # the whole array against the definition
    c1, c2, c_free = model.coefficients(THETA, LAM, "theta")
    T = cells.S.sum(0)
    for i in range(3):
        for s in range(3):
            for c in range(4):
                want = (c1 * cells.S[i, s, c] + c2 * (T[s, c] - cells.S[i, s, c])
                        + c_free * cells.S_free[s, c] + LAM * cells.M[s, c])
                assert math.isclose(u[i, s, c], want, rel_tol=0, abs_tol=1e-12)


def test_filler_capture_moves_the_utility():
    cells = cell_table()
    us = {fc: s2s.state_utilities(cells, theta=THETA, lam=LAM, filler_capture=fc)
          for fc in model.FILLER_CAPTURE}
    # only the S_free term differs, and NV has no filler book at all
    assert not np.allclose(us["theta"][:, 0, :], us["full"][:, 0, :])
    assert np.allclose(us["theta"][:, 2, :], us["opportunity"][:, 2, :])


def test_a_rep_subset_keeps_the_total_book_in_T():
    """T is a property of the cell: a rep left out of the subproblem still holds its book."""
    cells = cell_table()
    full = s2s.state_utilities(cells, theta=THETA, lam=LAM)
    sub = s2s.state_utilities(cells, ["R2", "R0"], theta=THETA, lam=LAM)
    assert np.allclose(sub[0], full[2])
    assert np.allclose(sub[1], full[0])


# ----------------------------------------------------------------------- gain matrix
def test_state_gain_matrix_over_used_slots_only():
    cells, plan = cell_table(), two_slot_plan()
    g, reps, slot_ids = s2s.state_gain_matrix(cells, plan, theta=THETA, lam=LAM)
    assert slot_ids == [0, 1]                     # slot 2 is unused, so it has no column
    assert reps == REPS
    assert g.shape == (3, 2)

    u = s2s.state_utilities(cells, theta=THETA, lam=LAM)
    want1 = 0.5 * (u[:, 0, 2] + u[:, 0, 3]) + 1.0 * (u[:, 2, 2] + u[:, 2, 3])
    assert np.allclose(g[:, 1], want1, atol=1e-12)
    want0 = u[:, :, :2].sum(2).sum(1)             # every state at share 1
    assert np.allclose(g[:, 0], want0, atol=1e-12)

    # R2 on slot 1, spelled out: half of AZ's WH and FI cells plus all of NV's
    az = (0.28 * 1.0 + 0.28 * 0.5 + 0.3 * 6.0) + (0.28 * 0.5 + 0.3 * 4.0)
    nv = 0.3 * 3.0 + 0.3 * 2.0
    assert math.isclose(g[2, 1], 0.5 * az + nv, rel_tol=0, abs_tol=1e-12)


def test_unknown_state_or_channel_is_refused():
    cells = cell_table()
    bad_state = s2s.Plan([s2s.Slot(("WH",), {"ZZ": 1.0}, True)], list(STATES))
    bad_chan = s2s.Plan([s2s.Slot(("XX",), {"AZ": 1.0}, True)], list(STATES))
    for plan in (bad_state, bad_chan):
        try:
            s2s.state_gain_matrix(cells, plan, theta=THETA, lam=LAM)
        except ValueError:
            pass
        else:
            raise AssertionError("an unknown state or channel must raise")


# --------------------------------------------------------------------------- stage 2
def test_state_stage2_shape_matches_channel_stage2():
    cells, plan = cell_table(), two_slot_plan()
    out = s2s.state_stage2(cells, plan, theta=THETA, lam=LAM)

    keys = {"assignment", "gains", "value", "criterion", "reps", "districts",
            "unmatched_reps", "unstaffed_districts", "balance"}
    assert set(out) == keys
    assert out["districts"] == [0, 1] and out["criterion"] == "nash"
    assert set(out["assignment"]) <= {0, 1} and len(out["assignment"]) == 2
    assert out["unstaffed_districts"] == []
    assert len(out["unmatched_reps"]) == 1        # 3 reps, 2 slots
    assert out["balance"]["k"] == 2
    # slot 0 holds all national mass, slot 1 half of AZ's WH+FI and all of NV's
    mass = [(10 + 8) + (20 + 16) + (5 + 4), 0.5 * (6 + 4) + (3 + 2)]
    assert math.isclose(out["balance"]["total"], sum(mass), rel_tol=0, abs_tol=1e-12)
    assert math.isclose(out["balance"]["max"], max(mass), rel_tol=0, abs_tol=1e-12)


def test_state_stage2_value_is_the_hand_hungarian():
    cells, plan = cell_table(), two_slot_plan()
    g, reps, _ = s2s.state_gain_matrix(cells, plan, theta=THETA, lam=LAM)
    best = max(math.log(g[i, 0]) + math.log(g[j, 1])
               for i, j in itertools.permutations(range(3), 2))
    out = s2s.state_stage2(cells, plan, theta=THETA, lam=LAM)
    assert math.isclose(out["value"], best, rel_tol=0, abs_tol=1e-12)
    assert math.isclose(out["value"], sum(math.log(v) for v in out["gains"].values()),
                        rel_tol=0, abs_tol=1e-12)


def test_utilitarian_criterion_maximises_the_raw_sum():
    cells, plan = cell_table(), two_slot_plan()
    g, _, _ = s2s.state_gain_matrix(cells, plan, theta=THETA, lam=LAM)
    best = max(g[i, 0] + g[j, 1] for i, j in itertools.permutations(range(3), 2))
    out = s2s.state_stage2(cells, plan, theta=THETA, lam=LAM, criterion="utilitarian")
    assert math.isclose(out["value"], best, rel_tol=0, abs_tol=1e-12)


def test_candidacy_masks_the_rep_with_no_book():
    """R2 books nothing, so with candidacy on it is not a candidate anywhere (trap 20:
    the other reps' utilities are untouched, because nobody is released)."""
    cells, plan = cell_table(), two_slot_plan()
    free = s2s.state_stage2(cells, plan, theta=THETA, lam=LAM)
    held = s2s.state_stage2(cells, plan, theta=THETA, lam=LAM, candidacy=True)
    # slot 0's only book is R0's, slot 1's only book is R1's
    assert held["assignment"] == {0: "R0", 1: "R1"}
    assert held["unmatched_reps"] == ["R2"]
    assert "R2" in free["reps"]                   # still priced, just not matchable
    # masking never changes a gain, only which pairs are allowed
    g, _, _ = s2s.state_gain_matrix(cells, plan, theta=THETA, lam=LAM)
    assert math.isclose(held["gains"][0], g[0, 0], rel_tol=0, abs_tol=1e-12)
    assert math.isclose(held["gains"][1], g[1, 1], rel_tol=0, abs_tol=1e-12)
    assert held["value"] <= free["value"] + 1e-12       # a restriction cannot help


def test_candidacy_changes_which_pairs_win_not_the_gains():
    """A case where the masked optimum is not the free one, so the mask is load bearing.

    `test_candidacy_masks_the_rep_with_no_book` has only one legal assignment left after
    masking, so it stays green even if the penalty in `_match_masked` is too small to beat a
    swap.  Here R0 is the free optimum on slot 1 and is not a candidate there, so the mask has
    to move the match rather than merely confirm it.
    """
    # One state, a big WH cell and an equal FI cell.  R1 owns nearly all the WH book and a
    # sliver of the FI book; R0 owns a sliver of WH; R2 books nothing.  R1 is the best rep on
    # the WH slot by a wide margin, so the free match puts it there -- but it is the only
    # candidate on the FI slot, so candidacy has to move it and give WH to R0.
    M = np.array([[0.0, 0.0, 20.0, 20.0]])
    S = np.zeros((3, 1, 4), float)
    S[0, 0, 2] = 0.1                                # R0's sliver of WH
    S[1, 0, 2] = 10.0                               # R1 owns WH
    S[1, 0, 3] = 0.1                                # and the only FI book
    cells = types.SimpleNamespace(state_list=["X"], channels=CHANNELS, reps=list(REPS),
                                  M=M, S=S, S_free=np.zeros((1, 4), float))
    plan = s2s.Plan([s2s.Slot(("WH",), {"X": 1.0}, True),
                     s2s.Slot(("FI",), {"X": 1.0}, True)], ["X"])
    g, R, slot_ids = s2s.state_gain_matrix(cells, plan, theta=THETA, lam=LAM)

    free = s2s.state_stage2(cells, plan, theta=THETA, lam=LAM)
    held = s2s.state_stage2(cells, plan, theta=THETA, lam=LAM, candidacy=True)
    assert free["assignment"][0] == "R1", "the free optimum puts R1 on the WH slot"
    assert held["assignment"] == {0: "R0", 1: "R1"}
    assert free["assignment"] != held["assignment"], \
        "the fixture must have the mask actually move the match"
    # the gains are read off the same matrix either way
    for slot, rep in held["assignment"].items():
        assert math.isclose(held["gains"][slot], g[R.index(rep), slot_ids.index(slot)],
                            rel_tol=0, abs_tol=1e-12)
    assert held["value"] < free["value"], "a real restriction, not a relabelling"


def test_candidacy_raises_when_two_slots_share_their_only_candidate():
    """Hall's condition, which a per-column staffability check cannot see.

    Both slots sit on AZ's WH and FI cells, where R1 is the only rep with book, so each column
    has a candidate and `_check_staffable` passes -- but one rep cannot hold two slots.
    """
    cells = cell_table()
    plan = s2s.Plan([s2s.Slot(("WH", "FI"), {"AZ": 1.0}, True),
                     s2s.Slot(("WH", "FI"), {"AZ": 0.5}, True)], list(STATES))
    s2s.state_stage2(cells, plan, theta=THETA, lam=LAM)          # fine without candidacy
    try:
        s2s.state_stage2(cells, plan, theta=THETA, lam=LAM, candidacy=True)
    except ValueError as e:
        assert "distinct representatives" in str(e)
        assert "1" in str(e), "the unstaffed slot must be named"
    else:
        raise AssertionError("two slots sharing their only candidate must raise")


def test_candidacy_does_not_change_the_utilities():
    """The masked run reads the same gain matrix; releasing would inflate S_free."""
    cells, plan = cell_table(), two_slot_plan()
    before = s2s.state_utilities(cells, theta=THETA, lam=LAM).copy()
    s2s.state_stage2(cells, plan, theta=THETA, lam=LAM, candidacy=True)
    assert np.allclose(s2s.state_utilities(cells, theta=THETA, lam=LAM), before)


def test_unused_slot_is_never_matched():
    cells = cell_table()
    plan = s2s.Plan([s2s.Slot(("N_WH", "N_FI"), {"AZ": 1.0}, True),
                     s2s.Slot(("WH", "FI"), {"CA": 1.0}, False)], list(STATES))
    out = s2s.state_stage2(cells, plan, theta=THETA, lam=LAM)
    assert out["districts"] == [0]
    assert set(out["assignment"]) == {0}
    assert out["balance"]["k"] == 1


def test_a_used_slot_nobody_can_staff_raises():
    cells = cell_table()
    empty = s2s.Plan([s2s.Slot(("N_WH", "N_FI"), {"AZ": 1.0}, True),
                      s2s.Slot(("WH", "FI"), {}, True)], list(STATES))
    try:
        s2s.state_stage2(cells, empty, theta=THETA, lam=LAM)
    except ValueError as e:
        assert "slot 1" in str(e) and "staffed" in str(e)
    else:
        raise AssertionError("a used slot with no positive gain must raise")

    # same guard under candidacy: NV has no book at all, so nobody is a candidate there
    nv_only = s2s.Plan([s2s.Slot(("WH", "FI"), {"NV": 1.0}, True)], list(STATES))
    s2s.state_stage2(cells, nv_only, theta=THETA, lam=LAM)          # fine without candidacy
    try:
        s2s.state_stage2(cells, nv_only, theta=THETA, lam=LAM, candidacy=True)
    except ValueError as e:
        assert "slot 0" in str(e)
    else:
        raise AssertionError("a slot with no candidate must raise under candidacy")


def test_empty_plan_is_a_zero_value():
    cells = cell_table()
    out = s2s.state_stage2(cells, s2s.Plan([], list(STATES)), theta=THETA, lam=LAM)
    assert out["value"] == 0.0 and out["districts"] == []
    assert out["balance"] == dict(k=0)


# ---------------------------------------------- the identity against the zip-level code
def v2_graph():
    """Four zips in two states, node attrs long by channel plus the v1 totals."""
    per_zip = {
        0: ("AZ", {"N_WH": 10.0, "N_FI": 6.0, "WH": 4.0, "FI": 2.0},
            {"R0": {"N_WH": 1.0}, "R1": {"WH": 0.5}}, {"N_WH": 0.5, "FI": 0.25}),
        1: ("AZ", {"N_WH": 8.0, "N_FI": 5.0, "WH": 3.0, "FI": 3.0},
            {"R1": {"WH": 1.0, "FI": 0.5}}, {"WH": 0.5}),
        2: ("CA", {"N_WH": 20.0, "N_FI": 12.0, "WH": 9.0, "FI": 6.0},
            {"R0": {"N_WH": 2.0, "FI": 1.0}, "R2": {"WH": 1.5}}, {"N_FI": 1.0}),
        3: ("CA", {"N_WH": 15.0, "N_FI": 9.0, "WH": 7.0, "FI": 5.0},
            {"R2": {"WH": 0.5, "FI": 2.0}}, {"WH": 0.25, "FI": 0.25}),
    }
    G = nx.path_graph(4)
    for z, (st, M_c, S_c, free_c) in per_zip.items():
        M_c = {c: M_c.get(c, 0.0) for c in CHANNELS}
        S_c = {r: {c: v.get(c, 0.0) for c in CHANNELS} for r, v in S_c.items()}
        free_c = {c: free_c.get(c, 0.0) for c in CHANNELS}
        G.nodes[z].update(
            state=st, M_c=M_c, S_c=S_c, S_free_c=free_c,
            M=sum(M_c.values()),
            S={r: sum(v.values()) for r, v in S_c.items()},
            S_free=sum(free_c.values()),
            cand=tuple(sorted(S_c)),
        )
    return G


def test_state_gain_matches_channel_gain_matrix():
    """Exact by linearity: aggregating cells then matching equals projecting then matching."""
    G = v2_graph()
    d = Descaled(G=G, contested=sorted(G), firm={r: "F" for r in REPS}, channels=CHANNELS)
    state_list = ["AZ", "CA"]
    cells = ch.aggregate(d, state_list)

    for bundle in (("N_WH", "N_FI"), ("WH", "FI"), ("WH", "N_WH")):
        plan = s2s.Plan([s2s.Slot(bundle, {s: 1.0 for s in state_list}, True)], state_list)
        g, reps, _ = s2s.state_gain_matrix(cells, plan, reps=list(cells.reps),
                                           theta=THETA, lam=LAM)
        pd = ch.project(d, bundle)
        to_district = {z: "D0" for z in pd.G}
        g_ref, R_ref, _ = channel.gain_matrix(pd.G, to_district, reps_order=list(cells.reps),
                                              theta=THETA, lam=LAM)
        assert R_ref == reps
        assert np.allclose(g[:, 0], g_ref[:, 0], rtol=0, atol=1e-9), bundle
