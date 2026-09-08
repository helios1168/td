"""test_state_splits_bounds.py -- the `--bounds` overrides: `bound_z` on the level-1 MILP
(td/solvers/state_splits.py) and their translation and level-2 half in tools/state_splits.py.

Level 1 runs on the same six-state path toy as test_state_splits.py (imported, not copied), so
every claim here is decidable against a solve of the unbounded problem beside it.  The
translation, freeze and pull helpers are pure functions on synthetic arrays: no instance file,
no `ctx`, and for the translation not even a solve.
"""
from __future__ import annotations

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
for _p in (HERE, os.path.join(ROOT, "tools")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from td.solvers import state_splits                          # noqa: E402
import state_splits as cli                                   # noqa: E402
from test_state_splits import CENTRES, COMB, EDGES, EVEN, ODD, path_toy   # noqa: E402

THREE = np.array([[0.5, 0.0], [2.5, 0.0], [4.5, 0.0]])       # k=3 centres for the fix test


def build(masses, delta, centres=CENTRES, **kw):
    toy = path_toy(masses, centres=centres)
    eps = state_splits.eps_lexicographic(toy["M_s"], toy["D"])
    prob = state_splits.build_milp(toy["M_s"], toy["D"], EDGES, float(toy["tau"]), delta, eps,
                                   **kw)
    return toy, prob


# ------------------------------------------------------------------------- the level-1 bounds
def test_force_makes_a_state_touch_a_district_it_otherwise_would_not():
    """EVEN at a 5% band with district 1 anchored in state 0 puts district 1 on the left block,
    so state 5 (the far right) never touches it.  Forcing `z[5, 1] = 1` makes it, and buys the
    splits that stretching district 1 across the path costs."""
    _, plain = build(EVEN, 0.05, anchors=[(0, 1)])
    base = state_splits.solve(plain)
    assert not base["z"][5, 1], base["z"]

    _, prob = build(EVEN, 0.05, anchors=[(0, 1)], bounds=[(5, 1, 1.0, 1.0)])
    res = state_splits.solve(prob)
    assert res["z"][5, 1] and res["z"][0, 1]
    assert res["splits"] > base["splits"]
    for j in range(prob.k):
        assert state_splits.connected(res["z"][:, j], EDGES)


def test_forbid_removes_a_touch_and_the_solver_still_closes():
    """ODD at a 0.5% band forces exactly one split, and puts state 0 (an end of the path) in
    district 0.  Forbidding that contact sends state 0 to district 1; the whole map flips, the
    split moves with it, and the count and the band are unchanged."""
    _, plain = build(ODD, 0.005)
    base = state_splits.solve(plain)
    assert base["splits"] == 1 and base["z"][0, 0]

    _, prob = build(ODD, 0.005, bounds=[(0, 0, 0.0, 0.0)])
    res = state_splits.solve(prob)
    assert not res["z"][0, 0] and res["z"][0, 1]
    assert res["splits"] == 1
    assert res["mip_gap"] <= 1e-9                            # trap 12: still a certificate
    assert res["max_dev_rel"] <= 0.005 + 1e-9
    for j in range(prob.k):
        assert state_splits.connected(res["z"][:, j], EDGES)


def test_fix_yields_exactly_the_given_district_set():
    """Three centres, six equal states: fixing state 0 to district 2 alone means `z[0]` is that
    one district and nothing else, which is the half of `fix` a two-district toy cannot show."""
    toy = path_toy(EVEN, centres=THREE)
    eps = state_splits.eps_lexicographic(toy["M_s"], toy["D"])
    fix = [(0, 0, 0.0, 0.0), (0, 1, 0.0, 0.0), (0, 2, 1.0, 1.0)]
    prob = state_splits.build_milp(toy["M_s"], toy["D"], EDGES, float(toy["tau"]), 0.05, eps,
                                   bounds=fix)
    res = state_splits.solve(prob)

    assert [int(j) for j in np.flatnonzero(res["z"][0])] == [2]
    assert res["splits"] == 0                                # {0,1} | {2,3} | {4,5} still fits
    for j in range(prob.k):
        assert state_splits.connected(res["z"][:, j], EDGES)


def test_an_impossible_fix_is_refuted_rather_than_searched_for():
    """State 0 fixed to both districts, states 1..5 fixed to district 1 alone.  Contiguity then
    leaves district 0 the single state 0, whose whole mass is a third of the band's floor, so no
    map exists: `SolveFailure` with `reason='infeasible'`, not a time limit and not a hang."""
    bounds = [(0, 0, 1.0, 1.0), (0, 1, 1.0, 1.0)]
    bounds += [(s, 0, 0.0, 0.0) for s in range(1, 6)] + [(s, 1, 1.0, 1.0) for s in range(1, 6)]
    _, prob = build(EVEN, 0.05, bounds=bounds)
    try:
        state_splits.solve(prob)
    except RuntimeError as exc:
        assert isinstance(exc, state_splits.SolveFailure)
        assert exc.reason == "infeasible" and exc.status == 2
    else:
        raise AssertionError("a fix the band cannot meet must be refuted")


def test_bound_z_refuses_an_out_of_range_or_crossed_bound():
    _, prob = build(EVEN, 0.05)
    for bad in ((9, 0, 1.0, 1.0), (0, 5, 0.0, 0.0), (0, 0, 1.0, 0.0), (0, 0, -1.0, 1.0)):
        try:
            state_splits.bound_z(prob, *bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"bound {bad} must be refused")


def test_bounds_are_applied_after_the_anchors():
    """An anchor sets the same lower bound `bound_z` writes, so the last word must be the
    bound's: `build_milp` applies `bounds` after `anchors`, not before."""
    _, prob = build(EVEN, 0.05, anchors=[(0, 1)], bounds=[(0, 1, 0.0, 0.0)])
    at = prob.off_z + 0 * prob.k + 1
    assert prob.var_lb[at] == 0.0 and prob.var_ub[at] == 0.0


# ------------------------------------------------------------------- the CLI's own translation
STATES = ["CA", "TX", "VT"]
ZIPS = ["05401", "75201", "90001"]


def test_the_translation_rejects_unknown_states_districts_and_zips():
    """Every name in the document is resolved before anything is solved, and an unresolvable
    one exits nonzero (`sys.exit`, hence `SystemExit`) rather than reaching the MILP."""
    bad = [
        {"force": [["ZZ", "D01"]]},                          # no such state
        {"force": [["TX", "D09"]]},                          # district beyond k
        {"forbid": [["TX", "d1"]]},                          # not the D01 spelling
        {"fix": {"QQ": ["D01"]}},
        {"fix": {"TX": []}},                                 # a state must touch something
        {"freeze": {"00000": "D01"}},                        # no such zip
        {"pull": {"75201": "D04"}},
        {"nonsense": []},                                    # unknown top-level key
        [],                                                  # not an object at all
    ]
    for spec in bad:
        try:
            cli.parse_bounds(spec, STATES, 3, ZIPS)
        except SystemExit:
            pass
        else:
            raise AssertionError(f"{spec!r} must be refused")


def test_the_translation_maps_names_to_indices_and_merges_a_fix():
    parsed = cli.parse_bounds(
        {"force": [["TX", "D02"]], "forbid": [["CA", "D03"]],
         "fix": {"VT": ["D01"]}, "freeze": {"05401": "D01"}, "pull": {"75201": "D02"}},
        STATES, 3, ZIPS)

    assert parsed["force"] == [(1, 1)] and parsed["forbid"] == [(0, 2)]
    assert parsed["fix"] == {2: [0]}
    assert parsed["freeze"] == {"05401": 0} and parsed["pull"] == {"75201": 1}
    assert sorted(parsed["triples"]) == [(0, 2, 0.0, 0.0), (1, 1, 1.0, 1.0),
                                         (2, 0, 1.0, 1.0), (2, 1, 0.0, 0.0), (2, 2, 0.0, 0.0)]


def test_a_document_that_both_forces_and_forbids_a_pair_is_refused():
    """A contradiction inside the document is the user's mistake, not an infeasible map, so it
    is named here rather than reported as `reason='infeasible'` after a solve."""
    for spec in ({"force": [["TX", "D01"]], "forbid": [["TX", "D01"]]},
                 {"force": [["TX", "D03"]], "fix": {"TX": ["D01"]}}):
        try:
            cli.parse_bounds(spec, STATES, 3, ZIPS)
        except SystemExit:
            pass
        else:
            raise AssertionError(f"{spec!r} must be refused")


def test_a_forbid_releases_the_anchor_it_contradicts():
    """`--anchor-homes` may hold district 1 in state 0 while a bound refuses exactly that pair;
    the anchor is dropped by name, the way `--unanchor` drops one, so the log does not go on
    claiming it."""
    anchors = [(0, 1), (2, 0)]
    triples = [(0, 1, 0.0, 0.0), (2, 0, 1.0, 1.0)]
    kept, dropped = cli._release_bound_anchors(anchors, triples)
    assert kept == [(2, 0)] and dropped == [(0, 1)]


# ------------------------------------------------------------------------ the level-2 half
def test_freeze_overwrites_the_labels_realise_chose():
    labels = np.array([0, 0, 1, 1], int)
    moved = cli._apply_freeze(labels, ["05401", "75201", "90001", "10001"],
                              {"75201": 1, "90001": 1})
    assert list(labels) == [0, 1, 1, 1]
    assert moved == 1                                        # 90001 was already there


def test_pull_beats_every_distance_in_its_own_state_and_leaves_the_rest_alone():
    """The bonus has to dominate the squared distances `centers.assign` weighs, and only for
    the pulled zip: an entry that leaked into another state's zips would silently re-cut it."""
    toy = path_toy(COMB)
    xy, state_idx = toy["xy"], toy["state_idx"]
    tb = cli._pull_tiebreak({"z6": 1}, [f"z{i}" for i in range(xy.shape[0])], xy, state_idx,
                            CENTRES)

    assert tb.shape == (xy.shape[0], 2)
    assert (tb[np.arange(xy.shape[0]) != 6] == 0.0).all()
    d2 = ((xy[state_idx == state_idx[6]][:, None, :] - CENTRES[None, :, :]) ** 2).sum(axis=2)
    assert tb[6, 1] > d2.max()
    assert tb[6, 0] == 0.0


def test_pull_moves_a_zip_realise_had_put_elsewhere():
    """End to end over level 2 on the toy: solve, balance, realise, then pull one zip of the
    split state across and see the label follow.  The pull is a preference, so the check is
    that the pulled zip lands where it was asked to while the state's targets still hold."""
    toy, prob = build(COMB, 0.10)
    res = state_splits.solve(prob)
    pas = state_splits.balance_pass(prob, res["z"])
    args = (toy["xy"], toy["M"], toy["state_idx"], res["z"], pas["y"], CENTRES)
    plain = state_splits.realise(*args, rounds=0)

    s0 = res["split_states"][0]
    idx = np.flatnonzero(toy["state_idx"] == s0)
    j0 = int(plain["labels"][idx[0]])
    j1 = next(int(j) for j in np.flatnonzero(res["z"][s0]) if int(j) != j0)
    codes = [f"z{i}" for i in range(toy["xy"].shape[0])]
    tb = cli._pull_tiebreak({codes[idx[0]]: j1}, codes, toy["xy"], toy["state_idx"], CENTRES)

    pulled = state_splits.realise(*args, rounds=0, tiebreak=tb)
    assert int(pulled["labels"][idx[0]]) == j1
    assert set(np.unique(pulled["labels"])) == set(np.unique(plain["labels"]))


def test_bounds_honoured_reads_the_solved_z_and_the_final_labels():
    """The report `splits.json` carries: a forced contact that held, a forbidden one that did,
    a fix compared as a set, freeze true by construction, and a pull that did not land."""
    z = np.array([[True, False, False], [True, True, False], [False, False, True]])
    labels = np.array([0, 2, 1])
    parsed = cli.parse_bounds(
        {"force": [["TX", "D02"]], "forbid": [["CA", "D02"]], "fix": {"VT": ["D03"]},
         "freeze": {"05401": "D01"}, "pull": {"75201": "D01"}},
        STATES, 3, ZIPS)
    got = cli._bounds_honoured(parsed, z, labels, ZIPS, STATES)

    assert got["force"] == [["TX", "D02", True]]
    assert got["forbid"] == [["CA", "D02", True]]
    assert got["fix"] == {"VT": True}
    assert got["freeze"] == {"05401": True}
    assert got["pull"] == {"75201": False}                   # 75201 is at index 1, label 2
