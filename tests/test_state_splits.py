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
import json
import os
import subprocess
import sys

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
def test_an_anchor_holds_its_district_in_that_state():
    """EVEN at delta=0 has two zero-split optima, {0,1,2}|{3,4,5} with either labelling.
    Anchoring district 1 to state 0 picks the one where district 1 holds the left block."""
    toy = path_toy(EVEN)
    eps = state_splits.eps_lexicographic(toy["M_s"], toy["D"])
    prob = state_splits.build_milp(toy["M_s"], toy["D"], EDGES, toy["tau"], 0.0, eps,
                                   anchors=[(0, 1)])
    res = state_splits.solve(prob)
    assert res["splits"] == 0
    assert res["z"][0, 1] and res["z"][1, 1] and res["z"][2, 1]
    assert not res["z"][0, 0]
    try:
        state_splits.build_milp(toy["M_s"], toy["D"], EDGES, toy["tau"], 0.0, eps,
                                anchors=[(9, 0)])
    except ValueError:
        pass
    else:
        raise AssertionError("an out-of-range anchor must be refused")


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


# ----------------------------------------------------------------------- the per-state cap
def test_a_cap_at_the_ceiling_changes_nothing():
    """A cap of 2 on every state, k=2: no state can exceed 2 anyway, so the cap block is slack
    and the solution matches the uncapped one."""
    _, prob = build(ODD, 0.005)
    res = state_splits.solve(prob)
    prob_cap = state_splits.build_milp(prob.M_s, prob.D, EDGES, prob.tau, 0.005, prob.eps,
                                       caps={s: 2 for s in range(6)})
    res_cap = state_splits.solve(prob_cap)
    assert res_cap["splits"] == res["splits"]
    assert abs(res_cap["objective"] - res["objective"]) < 1e-9


def test_a_cap_of_one_forbids_the_split_the_band_forces():
    """ODD needs one state to split; capping every state at 1 (no state may touch two
    districts) makes the MILP infeasible.  The failure names itself `infeasible`, a refutation,
    and it is still a `RuntimeError` for every caller that predates `SolveFailure`."""
    _, prob = build(ODD, 0.005)
    prob = state_splits.build_milp(prob.M_s, prob.D, EDGES, prob.tau, 0.005, prob.eps,
                                   caps={s: 1 for s in range(6)})
    try:
        state_splits.solve(prob)
    except RuntimeError as exc:
        assert isinstance(exc, state_splits.SolveFailure)
        assert exc.reason == "infeasible" and exc.status == 2
    else:
        raise AssertionError("a cap of 1 on every state must forbid the forced split")


def test_failure_reason_separates_a_refutation_from_a_search_that_ran_out():
    """The mapping itself, tested apart from HiGHS: scipy's `status` is the only thing that
    tells a proof of infeasibility (2, HiGHS Status 8) from a time limit reached with no
    incumbent (1, HiGHS Status 13).  Under `strict=False`, the way every time-limited caller
    runs, `solve` returns an incumbent rather than raising, so a `1` reaching the raise is
    empty-handed; `failure_reason`'s docstring carries what `strict=True` does instead.  A real
    tiny-time-limit solve is not tested: presolve can close this toy before the clock is read,
    which would make the assertion depend on the machine."""
    assert state_splits.failure_reason(2) == "infeasible"
    assert state_splits.failure_reason(1) == "no_incumbent"
    for other in (0, 3, 4):
        assert state_splits.failure_reason(other) == "other"
    assert state_splits.SolveFailure(1, "Time limit reached.").reason == "no_incumbent"
    assert "Time limit reached." in str(state_splits.SolveFailure(1, "Time limit reached."))


def test_a_cap_outside_one_to_k_is_rejected():
    """k=2: caps={0: 0} and caps={0: 3} are outside [1, k]; caps={99: 1} is out of range."""
    _, prob = build(ODD, 0.005)
    for bad in ({0: 0}, {0: 3}, {99: 1}):
        try:
            state_splits.build_milp(prob.M_s, prob.D, EDGES, prob.tau, 0.005, prob.eps,
                                    caps=bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"cap {bad} must be rejected")


def test_a_cap_binds_only_the_state_it_names():
    """COMB at a 10% band: find a state whole in the uncapped optimum and cap it at 1.  The
    objective and split count are unchanged (the cap does not bind the optimum), and that state
    still holds exactly one district.  `z` itself is not asserted: ties mean the solver may
    return a different optimal vertex at the same objective."""
    toy, prob = build(COMB, 0.10)
    res = state_splits.solve(prob)
    whole = [s for s in range(6) if s not in res["split_states"]]
    assert whole
    s0 = whole[0]

    prob_cap = state_splits.build_milp(prob.M_s, prob.D, EDGES, prob.tau, 0.10, prob.eps,
                                       caps={s0: 1})
    res_cap = state_splits.solve(prob_cap)
    assert abs(res_cap["objective"] - res["objective"]) < 1e-9
    assert res_cap["splits"] == res["splits"]
    assert int(res_cap["z"][s0].sum()) == 1


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


# ----------------------------------------------------------------------- build_milp(fix_roots=)
def test_fix_roots_with_a_released_anchor_stays_feasible_and_matches_the_plain_optimum():
    """One anchor, (state 0, district 0), then a `bounds` forbid on that same pair releases it
    (`bound_z` runs after the anchor and silently overrides it, per `build_milp`'s own
    docstring).  `fix_roots=True` must not root a released anchor -- REPORT.md's guard, "the
    root-fixed model is infeasible" when it does, since `r <= z` and the released anchor's
    `z` is pinned to 0.  Rooted correctly (i.e. not rooted at all here, nothing survives), the
    two models are the same MILP off the `r`/`f` blocks and so must agree exactly."""
    toy = path_toy(EVEN)
    eps = state_splits.eps_lexicographic(toy["M_s"], toy["D"])
    anchors = [(0, 0)]
    bounds = [(0, 0, 0.0, 0.0)]                     # forbid: releases the only anchor

    plain = state_splits.build_milp(toy["M_s"], toy["D"], EDGES, toy["tau"], 0.0, eps,
                                    anchors=anchors, bounds=bounds)
    res_plain = state_splits.solve(plain)

    fixed = state_splits.build_milp(toy["M_s"], toy["D"], EDGES, toy["tau"], 0.0, eps,
                                    anchors=anchors, bounds=bounds, fix_roots=True)
    res_fixed = state_splits.solve(fixed)

    assert res_fixed["splits"] == res_plain["splits"] == 0
    assert abs(res_fixed["objective"] - res_plain["objective"]) < 1e-9
    assert not res_fixed["z"][0, 0]                 # the forbid held
    at = fixed.off_r + 0 * fixed.k + 0
    assert fixed.var_lb[at] == 0.0 and fixed.var_ub[at] == 1.0   # not rooted: the anchor was released


def test_fix_roots_keeps_a_surviving_anchor_rooted():
    """Two anchors; only one is released.  The surviving one is still rooted at its home
    state, and the result matches the plain (no `fix_roots`) model, per the root-fix claim."""
    toy = path_toy(EVEN)
    eps = state_splits.eps_lexicographic(toy["M_s"], toy["D"])
    anchors = [(0, 0), (3, 1)]

    plain = state_splits.build_milp(toy["M_s"], toy["D"], EDGES, toy["tau"], 0.0, eps,
                                    anchors=anchors)
    res_plain = state_splits.solve(plain)

    fixed = state_splits.build_milp(toy["M_s"], toy["D"], EDGES, toy["tau"], 0.0, eps,
                                    anchors=anchors, fix_roots=True)
    res_fixed = state_splits.solve(fixed)

    assert res_fixed["splits"] == res_plain["splits"]
    assert abs(res_fixed["objective"] - res_plain["objective"]) < 1e-9
    at = fixed.off_r + 3 * fixed.k + 1
    assert fixed.var_lb[at] == 1.0 and fixed.var_ub[at] == 1.0
    for s in range(fixed.n_state):
        if s != 3:
            assert fixed.var_ub[fixed.off_r + s * fixed.k + 1] == 0.0


# ----------------------------------------------------------------------- strategy="descent"
def test_descent_matches_direct_and_certifies_on_both_engines():
    """`strategy="descent"` lands on the same split count `strategy="direct"` does, certifies
    it (phase B's cutoff proof), and logs its phases -- on `scipy` and on `highs`, the two
    engines the app offers today."""
    for engine in ("scipy", "highs"):
        for masses, delta in ((ODD, 0.005), (COMB, 0.03)):
            _, prob = build(masses, delta)
            direct = state_splits.solve(prob, engine=engine, strategy="direct", time_limit=30.0)
            descent = state_splits.solve(prob, engine=engine, strategy="descent",
                                         time_limit=30.0, primal_seconds=5.0)
            assert descent["splits"] == direct["splits"], (engine, masses)
            assert descent["certified_splits"] is True
            assert descent["engine"] == engine and descent["strategy"] == "descent"
            assert descent["phases"]
            for j in range(prob.k):
                assert state_splits.connected(descent["z"][:, j], EDGES)


def test_descent_certifies_a_zero_split_optimum_at_once():
    """EVEN at delta=0.001: phase A already finds the 0-split optimum; phase B's cutoff
    (`sum z <= n_state - 1`, i.e. -1 splits) is infeasible at once, so it is proven, not
    guessed, and phase C closes the (trivial) tie-break in the same breath."""
    for engine in ("scipy", "highs"):
        _, prob = build(EVEN, 0.001)
        res = state_splits.solve(prob, engine=engine, strategy="descent", time_limit=30.0,
                                 primal_seconds=5.0)
        assert res["splits"] == 0
        assert res["certified_splits"] is True
        assert res["status"] == 0
        phase_names = [p["phase"] for p in res["phases"]]
        assert "incumbent" in phase_names and "descent" in phase_names


# ----------------------------------------------------------------------- strategy="portfolio"
# `strategy="portfolio"`'s parent-side HiGHS calls fix `threads=2` (the pool-sizing hazard in
# milp_engines.py's module docstring), one value for the whole process; every other HiGHS call
# in this test process uses `threads=None`.  A plain `multiprocessing.Process` around the whole
# `solve()` call would need to pickle a reference to a module-level function by
# `(__module__, __qualname__)`, and `tests/run_all.py` loads a test file twice under the same
# module name (once directly, once again when another test file imports from it) -- the two
# loads are different module objects, so pickle's identity check on the callback rejects the
# second one ("it's not the same object as tests.test_state_splits._run_portfolio").  A real
# subprocess sidesteps that: it imports `tests.test_state_splits` once, the ordinary way.
_PORTFOLIO_SCRIPT = """
import json, sys
sys.path.insert(0, sys.argv[1])
from tests.test_state_splits import build
from td.solvers import state_splits

masses, delta, time_limit = json.loads(sys.argv[2])
_, prob = build(masses, delta)
res = state_splits.solve(prob, strategy="portfolio", time_limit=time_limit)
members = sorted(set(p["member"] for p in res["phases"] if p["phase"] == "incumbent"))
print(json.dumps(dict(splits=res["splits"], certified_splits=res["certified_splits"],
                      status=res["status"], strategy=res["strategy"], engine=res["engine"],
                      members=members)))
"""


def test_portfolio_matches_direct_and_certifies():
    """`strategy="portfolio"` lands on the same split count `strategy="direct"` does and
    certifies it, on a toy with a split (ODD) and one with none (EVEN).  Run as a subprocess
    (see `_PORTFOLIO_SCRIPT`'s comment for why not a bare `multiprocessing.Process`)."""
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    for masses, delta in ((ODD, 0.005), (EVEN, 0.001)):
        _, direct_prob = build(masses, delta)
        direct = state_splits.solve(direct_prob, engine="scipy", strategy="direct")

        payload = json.dumps([masses, delta, 30.0])
        proc = subprocess.run([sys.executable, "-c", _PORTFOLIO_SCRIPT, root, payload],
                              capture_output=True, text=True, timeout=60)
        assert proc.returncode == 0, proc.stderr
        out = json.loads(proc.stdout.strip().splitlines()[-1])

        assert out["splits"] == direct["splits"], (masses, out)
        assert out["certified_splits"] is True
        assert out["strategy"] == "portfolio" and out["engine"] == "highs"
        assert out["members"]                           # at least one member reported in
