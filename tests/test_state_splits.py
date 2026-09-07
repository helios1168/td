"""test_state_splits.py -- Track 2: the state-level minimum-splits MILP (td/solvers/state_splits.py).

Everything runs on one hand-built toy: six "states" 0..5 on a path graph, `per` zips each, two
districts whose centres sit at x = 1 and x = 4.  The masses are what each test varies, and they
are chosen so the answer is decidable by hand:

* `EVEN`   -- {0,1,2} | {3,4,5} splits the mass exactly, so the minimum is 0 splits;
* `ODD`    -- no whole-state grouping lands in a 0.5% band, so the minimum is 1 split;
* `COMB`   -- the only whole-state groupings inside the band are *disconnected* on the path, so
              contiguity must refuse them and buy a split instead (true up to a 10% band, which
              is why the balance-pass and level-2 tests use it too).  `test_contiguity_...`
              re-derives that by enumerating all 2^6 groupings, so the fixture cannot rot
              silently.

No instance file, no network, no `td.geo`: the rook graph enters as an edge list.
"""
from __future__ import annotations

import itertools

import numpy as np

from td.solvers import centers                            # noqa: E402
from td.solvers import state_splits                       # noqa: E402

EDGES = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5)]
CENTRES = np.array([[1.0, 0.0], [4.0, 0.0]])
EVEN = [10.0, 10.0, 10.0, 10.0, 10.0, 10.0]
ODD = [10.0, 10.0, 10.0, 10.0, 10.0, 11.0]
COMB = [10.0, 3.0, 10.0, 3.0, 10.0, 3.0]
FAR = np.array([[0.0, 0.0], [5.0, 0.0]])                  # centres placed for the old shares


def path_toy(masses, per=4, centres=CENTRES):
    """`per` zips per state in a tight cluster at x = s; returns the zip and state arrays."""
    masses = np.asarray(masses, float)
    S = masses.shape[0]
    off = np.linspace(-0.2, 0.2, per)
    xy = np.array([[s + dx, dy] for s in range(S) for dx, dy in zip(off, off[::-1])])
    M = np.repeat(masses / per, per)
    state_idx = np.repeat(np.arange(S), per)
    D = np.zeros((S, centres.shape[0]))
    for s in range(S):
        sel = state_idx == s
        d2 = ((xy[sel, None, :] - centres[None, :, :]) ** 2).sum(axis=2)
        D[s] = (M[sel, None] * d2).sum(axis=0) / M[sel].sum()
    return dict(xy=xy, M=M, state_idx=state_idx, M_s=masses, D=D, centres=centres,
                tau=float(masses.sum()) / centres.shape[0])


def build(masses, delta, eps=None, centres=CENTRES):
    toy = path_toy(masses, centres=centres)
    if eps is None:
        eps = state_splits.eps_lexicographic(toy["M_s"], toy["D"])
    prob = state_splits.build_milp(toy["M_s"], toy["D"], EDGES, float(toy["tau"]), delta, eps)
    return toy, prob


# ----------------------------------------------------------------------- the split count
def test_no_split_when_the_band_admits_a_whole_state_partition():
    """Equal states, k=2: {0,1,2} | {3,4,5} is exact, so the minimum is 0 splits."""
    _, prob = build(EVEN, 0.001)
    res = state_splits.solve(prob)
    assert res["splits"] == 0, res["z"]
    assert res["split_states"] == []
    assert (res["z"].sum(axis=1) == 1).all()             # every state whole
    assert set(np.flatnonzero(res["z"][:, 0])) in ({0, 1, 2}, {3, 4, 5})
    assert res["mip_gap"] <= 1e-9                        # trap 12: a certificate, not 1e-4


def test_one_split_when_the_band_forces_it():
    """Masses 10,10,10,10,10,11: no grouping is within 0.5% of tau, so one state must split."""
    _, prob = build(ODD, 0.005)
    res = state_splits.solve(prob)
    assert res["splits"] == 1, res["z"]
    assert len(res["split_states"]) == 1
    assert res["max_dev_rel"] <= 0.005 + 1e-9
    for j in range(prob.k):
        assert state_splits.connected(res["z"][:, j], EDGES)


def test_contiguity_refuses_a_disconnected_zero_split_grouping():
    """The only 0-split groupings inside the band are disconnected, so the MILP buys a split."""
    toy, prob = build(COMB, 0.03)
    tau, M_s = toy["tau"], toy["M_s"]
    in_band, connected_in_band = [], []
    for bits in itertools.product([0, 1], repeat=6):
        col = np.array(bits, bool)
        m0, m1 = M_s[col].sum(), M_s[~col].sum()
        if abs(m0 - tau) <= 0.03 * tau and abs(m1 - tau) <= 0.03 * tau:
            in_band.append(col)
            if (state_splits.connected(col, EDGES)
                    and state_splits.connected(~col, EDGES)):
                connected_in_band.append(col)
    assert in_band and not connected_in_band              # the fixture still bites

    res = state_splits.solve(prob)
    assert res["splits"] == 1, res["z"]
    for j in range(prob.k):
        assert state_splits.connected(res["z"][:, j], EDGES)
    assert res["max_dev_rel"] <= 0.03 + 1e-9


def test_eps_never_buys_a_split():
    """docs/VERIFY_state_splits.md section 2: on the 4-state path with crossed preferences the
    plan's `eps = 0.5 / V(y0)` returns 2 splits where 0 is optimal.  `eps_lexicographic` is
    calibrated over the whole polytope (`0.5 / sum_s M_s max_j D_sj`), so 0 splits it is."""
    M_s = np.full(4, 10.0)
    D = np.array([[1.0, 100.0], [100.0, 1.0], [1.0, 100.0], [100.0, 1.0]])
    edges = [(0, 1), (1, 2), (2, 3)]
    eps = state_splits.eps_lexicographic(M_s, D)
    assert eps * float((M_s * D.max(axis=1)).sum()) <= 0.5 + 1e-12

    prob = state_splits.build_milp(M_s, D, edges, 20.0, 0.0, eps)
    res = state_splits.solve(prob)
    assert res["splits"] == 0, res["z"]
    assert set(np.flatnonzero(res["z"][:, 0])) in ({0, 1}, {2, 3})


def test_eta_forbids_a_zero_share_bridge_state():
    """docs/VERIFY_state_splits.md section 1b: path A-B-C, masses 1, 2, 1, tau = 2, delta = 0.
    Without `y >= eta z` the cheapest single split flags B into both districts but sends it no
    mass, and district 0 is realised as the disconnected A + C."""
    M_s = np.array([1.0, 2.0, 1.0])
    D = np.array([[1.0, 4.0], [2.0, 2.0], [4.0, 1.0]])
    edges = [(0, 1), (1, 2)]
    prob = state_splits.build_milp(M_s, D, edges, 2.0, 0.0,
                                   state_splits.eps_lexicographic(M_s, D))
    res = state_splits.solve(prob)

    assert res["splits"] == 1 and res["split_states"] == [1]
    assert (res["y"][res["z"]] >= prob.eta - 1e-9).all(), res["y"]
    for j in range(prob.k):
        assert state_splits.connected(res["z"][:, j], edges)
        assert state_splits.connected(res["y"][:, j] > 0, edges)   # the *realised* district


# ----------------------------------------------------------------------- the balance pass
def test_balance_pass_keeps_z_and_never_widens_the_spread():
    """A wide band lets the MILP imbalance the districts; fixing z and minimising first the
    maximum deviation and then the spread tightens both, and cannot move mass into a district
    z left out (nor out of one z flagged -- the `eta` bound is carried over)."""
    _, prob = build(COMB, 0.10)
    res = state_splits.solve(prob)
    pas = state_splits.balance_pass(prob, res["z"])

    assert res["max_dev_rel"] > 0.05                      # the MILP did spend the band
    assert (pas["y"][~res["z"]] == 0.0).all()            # z unchanged: no new contacts
    assert (pas["y"][res["z"]] >= prob.eta - 1e-9).all()  # and none of them dropped
    assert np.allclose(pas["y"].sum(axis=1), 1.0)
    assert pas["max_dev_rel"] <= res["max_dev_rel"] + 1e-9
    assert pas["spread_rel"] <= res["spread_rel"] + 1e-9
    assert pas["max_dev_rel"] < 1e-6                      # one split state balances exactly


# ----------------------------------------------------------------------- the graph helper
def test_connected_on_a_known_connected_and_disconnected_column():
    assert state_splits.connected(np.array([1, 1, 1, 0, 0, 0], bool), EDGES)
    assert state_splits.connected(np.array([0, 0, 0, 1, 1, 1], bool), EDGES)
    assert not state_splits.connected(np.array([1, 0, 1, 0, 0, 0], bool), EDGES)
    assert not state_splits.connected(np.array([1, 1, 0, 0, 1, 0], bool), EDGES)
    assert state_splits.connected(np.zeros(6, bool), EDGES)   # vacuously


# ----------------------------------------------------------------------- level 2
def test_realise_hits_the_targets_to_within_one_zip():
    """Unsplit states go whole; the split state's zips are cut by `centers.assign`, so each
    district's mass misses its target by at most the one rounded zip."""
    toy, prob = build(COMB, 0.10)
    res = state_splits.solve(prob)
    pas = state_splits.balance_pass(prob, res["z"])
    out = state_splits.realise(toy["xy"], toy["M"], toy["state_idx"], res["z"], pas["y"],
                               CENTRES, rounds=5)

    assert res["split_states"]
    labels = out["labels"]
    assert (labels >= 0).all()
    for s in range(prob.n_state):
        if s not in res["split_states"]:                  # whole states stay whole
            assert len(set(labels[toy["state_idx"] == s])) == 1

    masses = np.bincount(labels, weights=toy["M"], minlength=prob.k)
    one_zip = toy["M"].max()
    assert np.abs(masses - pas["masses"]).max() <= one_zip + 1e-9
    assert out["n_fractional"] <= len(res["split_states"]) * (prob.k - 1)
    for s in res["split_states"]:
        assert out["states"][s]["districts"] == [0, 1]
        assert out["states"][s]["n_fractional"] <= prob.k - 1


def test_realise_lloyd_rounds_never_raise_the_split_state_cost():
    """With the centres placed for the old shares (`FAR`), recentroiding from full membership
    is worth having: at least one round runs and the split state's compactness falls."""
    toy, prob = build(COMB, 0.10, centres=FAR)
    res = state_splits.solve(prob)
    pas = state_splits.balance_pass(prob, res["z"])
    out = state_splits.realise(toy["xy"], toy["M"], toy["state_idx"], res["z"], pas["y"],
                               FAR, rounds=5)

    assert res["split_states"]
    for s in res["split_states"]:
        cost = out["states"][s]["cost_rounds"]
        assert len(cost) == out["rounds_used"][s] + 1
        assert all(b <= a + 1e-12 for a, b in zip(cost, cost[1:])), cost
        assert out["rounds_used"][s] >= 1 and cost[-1] < cost[0]
        # the state's own mass split is untouched by the rounds
        sel = toy["state_idx"] == s
        share = [float(toy["M"][sel][out["labels"][sel] == j].sum()) for j in range(prob.k)]
        assert abs(sum(share) - toy["M_s"][s]) < 1e-9


def test_realise_tiebreak_needs_the_penalty_keyword():
    """`tiebreak` rides on `centers.assign(..., penalty=...)`: either it is honoured and pulls
    zips toward the favoured district, or it raises rather than being silently dropped."""
    import inspect

    toy, prob = build(COMB, 0.10)
    res = state_splits.solve(prob)
    pas = state_splits.balance_pass(prob, res["z"])
    args = (toy["xy"], toy["M"], toy["state_idx"], res["z"], pas["y"], CENTRES)
    tb = np.zeros((toy["xy"].shape[0], prob.k))
    tb[:, 0] = 100.0                                      # district 0 is favoured everywhere

    if "penalty" in inspect.signature(centers.assign).parameters:
        plain = state_splits.realise(*args, rounds=0)
        pulled = state_splits.realise(*args, rounds=0, tiebreak=tb)
        assert (pulled["labels"] == 0).sum() >= (plain["labels"] == 0).sum()
    else:
        try:
            state_splits.realise(*args, rounds=0, tiebreak=tb)
        except NotImplementedError:
            pass
        else:
            raise AssertionError("tiebreak was accepted without centers.assign(penalty=)")
