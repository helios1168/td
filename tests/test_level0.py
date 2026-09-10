"""test_level0.py -- td/solvers/level0.py, the channel-plan MILP at state x channel grain.

One hand-built toy throughout: six states 0..5 on a path graph, two fine channels `A` and
`B`, `tau = 1`, `L = 0.8`, `U = 1.2`, `eta = 0.05`, the scipy engine direct.  With fractional
shares and zero-mass bridges a connected path of total mass `T` is fully coverable iff
`T` lies in some `[nL, nU]`: `[0.8, 1.2]`, `[1.6, 2.4]`, `[2.4, ...]`.  So `T = 1.4` sits in
the one gap and leaves a residual, and an isolated state is made by committing its only
neighbour through `prior` (`cover_ub = 0 < eta` forbids the bridge).
"""
from __future__ import annotations

import dataclasses
import itertools
from types import SimpleNamespace

import numpy as np

from td.solvers import level0
from td.solvers import milp_engines as me
from td.solvers import state_splits as ss
from tests.test_state_splits import EDGES, EVEN, build

CHANNELS = ("A", "B")
BUNDLES = {"A": ("A",), "B": ("B",)}
BAND = dict(L=0.8, U=1.2, eta=0.05)
CONTIG = [0.5, 0.1, 0.5, 0.1, 0.5, 0.1]     # whole-state in-band partitions all disconnected


def cells(a, b=None):
    M = np.zeros((6, 2))
    M[:, 0] = a
    if b is not None:
        M[:, 1] = b
    return SimpleNamespace(M=M, channels=CHANNELS, state_list=[f"S{s}" for s in range(6)])


def build0(a, b=None, bundles=BUNDLES, **kw):
    kw = dict(BAND, **kw)
    return level0.build_level0(cells(a, b), bundles, edges=EDGES, **kw)


def run(prob, passes, **kw):
    return level0.solve_passes(prob, passes, **kw)


def assert_bands_and_contiguity(prob, out):
    for j in range(prob.k):
        if out["u"][j]:
            assert prob.L - 1e-6 <= out["masses"][j] <= prob.U + 1e-6, out["masses"]
            assert ss.connected(out["z"][:, j], EDGES), (j, out["z"][:, j])
        else:
            assert not out["z"][:, j].any()


# ------------------------------------------------------------------------------ coverage
def test_slot_counts_and_layout():
    prob = build0([0.5] * 6)
    assert level0.slot_counts(cells([0.5] * 6), BUNDLES, L=0.8) == {"A": 4, "B": 0}
    assert prob.slots == {"A": (0, 4), "B": (4, 4)}
    assert prob.k == 4 and prob.bundle_of == ("A",) * 4
    assert prob.n_var == prob.off_u + prob.k
    assert prob.W.shape == (6, 4) and np.allclose(prob.W, 0.5)
    assert prob.tau == 1.0 and abs(prob.delta - 0.2) < 1e-12
    assert prob.integrality[prob.off_u:].all()
    assert np.allclose(prob.M_s, 0.5)
    assert isinstance(prob, ss.SplitProblem)


def test_coverage_is_full_when_the_band_allows():
    """Six states of 0.5: three slots of 1.0 cover everything."""
    prob = build0([0.5] * 6)
    out = run(prob, [level0.cover_pass(prob, ["A"])])
    p = out["passes"][0]
    assert p["name"] == "cover_A" and p["certified"] and p["status"] == 0
    assert abs(p["value"] - 3.0) < 1e-6
    assert np.allclose(out["covered"][:, 0], 1.0, atol=1e-6)
    assert np.allclose(out["residual"][:, 0], 0.0, atol=1e-6)
    assert np.allclose(out["residual"][:, 1], 1.0)          # channel B: no mass, no slot
    assert int(out["u"].sum()) == 3
    assert_bands_and_contiguity(prob, out)


def test_coverage_leaves_a_residual_when_it_cannot():
    """Total 1.4 lies in the gap (1.2, 1.6): one slot holds at most 1.2, two need 1.6."""
    prob = build0([0.5, 0.5, 0.4, 0.0, 0.0, 0.0])
    out = run(prob, [level0.cover_pass(prob, ["A"])])
    assert abs(out["passes"][0]["value"] - 1.2) < 1e-6
    assert abs(out["residual"][:, 0] @ prob.M_s - 0.2) < 1e-6
    assert int(out["u"].sum()) == 1
    assert_bands_and_contiguity(prob, out)


def test_prior_reduces_coverage_and_isolates_a_state():
    """States 0..3 at 0.5 and state 5 at 0.3; state 4 is committed (`prior = 1`), so it
    cannot bridge and state 5 is unreachable: 2.0 covered, the 0.3 left as residual.  Without
    the prior the same masses cover fully (2.3 lies in [1.6, 2.4])."""
    masses = [0.5, 0.5, 0.5, 0.5, 0.0, 0.3]
    free = build0(masses)
    out = run(free, [level0.cover_pass(free, ["A"])])
    assert abs(out["passes"][0]["value"] - 2.3) < 1e-6

    prior = np.zeros((6, 2))
    prior[4, 0] = 1.0
    prob = build0(masses, prior=prior)
    assert prob.slots["A"] == (0, 3)
    out = run(prob, [level0.cover_pass(prob, ["A"])])
    assert abs(out["passes"][0]["value"] - 2.0) < 1e-6
    assert abs(out["residual"][5, 0] - 1.0) < 1e-6
    assert not out["z"][4].any() and not out["z"][5].any()
    assert_bands_and_contiguity(prob, out)


def test_u_none_raises():
    try:
        build0([0.5] * 6, U=None)
    except ValueError:
        pass
    else:
        raise AssertionError("build_level0 must refuse U=None")


# ---------------------------------------------------------------------------- contiguity
def test_contiguity_refuses_a_disconnected_whole_state_cover():
    """Two slots covering 1.8 with whole states exist only disconnected ({0,2} | {1,3,4,5}),
    so at full cover the contacts pass must buy one split: 7 contacts, every slot connected."""
    M_s = np.array(CONTIG)
    in_band, connected_in_band = [], []
    for bits in itertools.product([0, 1], repeat=6):
        col = np.array(bits, bool)
        m0, m1 = M_s[col].sum(), M_s[~col].sum()
        if 0.8 - 1e-9 <= m0 <= 1.2 + 1e-9 and 0.8 - 1e-9 <= m1 <= 1.2 + 1e-9:
            in_band.append(col)
            if ss.connected(col, EDGES) and ss.connected(~col, EDGES):
                connected_in_band.append(col)
    assert in_band and not connected_in_band              # the fixture still bites

    prob = build0(CONTIG)
    out = run(prob, [level0.cover_pass(prob, ["A"]), level0.contacts_pass(prob)])
    cov, con = out["passes"]
    assert abs(cov["value"] - 1.8) < 1e-6 and cov["certified"]
    assert con["value"] == 7 and con["certified"]
    assert out["contacts"] == 7 and int(out["u"].sum()) == 2
    assert np.allclose(out["covered"][:, 0], 1.0, atol=1e-6)
    assert_bands_and_contiguity(prob, out)
    for j in range(prob.k):
        z = out["z"][:, j]
        if z[0] and z[2]:
            assert z[1]


def test_ordering_rows_do_not_change_the_optimum():
    for masses in ([0.5] * 6, CONTIG):
        vals = []
        for order_mass in (True, False):
            prob = build0(masses, order_mass=order_mass)
            assert ("order_mass" in prob.rows) == order_mass
            assert "order_u" in prob.rows
            out = run(prob, [level0.cover_pass(prob, ["A"]), level0.contacts_pass(prob)])
            assert all(p["certified"] for p in out["passes"])
            vals.append([p["value"] for p in out["passes"]])
            if order_mass:
                m = out["masses"]
                assert all(m[j] >= m[j + 1] - 1e-6 for j in range(prob.k - 1)), m
        assert np.allclose(vals[0], vals[1])


def test_anchors_turn_mass_ordering_off_and_hold():
    prob = build0(CONTIG, anchors={4: 1})
    assert "order_mass" not in prob.rows and "order_u" in prob.rows
    assert prob.var_lb[prob.off_z + 4 * prob.k + 1] == 1.0
    out = run(prob, [level0.cover_pass(prob, ["A"]), level0.contacts_pass(prob)])
    assert out["z"][4, 1]
    assert abs(out["passes"][0]["value"] - 1.8) < 1e-6 and out["passes"][1]["value"] == 7


# -------------------------------------------------------------------------- pins and rows
def test_append_row_pins_a_value():
    """After the cover pin, `sum z <= 6` (no split) contradicts the 7 contacts full cover
    needs, so the contacts pass on that problem is infeasible."""
    prob = build0(CONTIG)
    out = run(prob, [level0.cover_pass(prob, ["A"])])
    pinned = out["problem"]
    assert "pin_cover_A" in pinned.rows
    assert pinned.A.shape[0] == prob.A.shape[0] + 1
    S, K = prob.n_state, prob.k
    tight = level0.append_row(pinned, "six", prob.off_z + np.arange(S * K), np.ones(S * K),
                              -np.inf, 6.0)
    try:
        run(tight, [level0.contacts_pass(tight)])
    except ss.SolveFailure as exc:
        assert exc.reason == "infeasible"
    else:
        raise AssertionError("a no-split full cover should not exist")


def test_a_pinned_maximisation_leaves_the_next_pass_feasible():
    """A cover pass is a maximisation solved as `min -c`; its minimised value is negative, so
    `v (1 + 1e-9)` would tighten the pin above the true optimum by more than HiGHS's
    feasibility tolerance at dollar scale.  Masses in the thousands: the contacts pass must
    still solve and hold the cover."""
    scale = 8000.0
    prob = build0(np.array(CONTIG) * scale, L=0.8 * scale, U=1.2 * scale)
    out = run(prob, [level0.cover_pass(prob, ["A"]), level0.contacts_pass(prob)])
    cov, con = out["passes"]
    assert abs(cov["value"] - 1.8 * scale) < 1e-3 * scale and cov["certified"]
    assert con["certified"] and con["value"] == 7
    assert abs((prob.W * out["y"]).sum() - 1.8 * scale) < 1e-3 * scale


def test_with_cutoff_on_a_level0_problem_means_fewer_contacts():
    prob = build0(CONTIG)
    pinned = run(prob, [level0.cover_pass(prob, ["A"])])["problem"]
    contacts = level0.contacts_pass(pinned)
    current = dataclasses.replace(pinned, c=contacts.c)
    # splits = contacts - n_state = 1 at the optimum; a 0-split map must not exist
    tight = me.with_cutoff(current, 1)
    assert type(tight) is level0.Level0Problem
    try:
        me.solve_problem(tight, "scipy", time_limit=30.0)
    except ss.SolveFailure as exc:
        assert exc.reason == "infeasible"
    else:
        raise AssertionError("with_cutoff(problem, 1) must refuse a 0-split full cover")
    loose = me.with_cutoff(current, 2)
    res = me.solve_problem(loose, "scipy", time_limit=30.0)
    assert res["status"] == 0 and res["contacts"] == 7 and res["splits"] == 1


def test_fix_roots_keeps_the_subclass_and_the_r_bounds():
    prob = build0(CONTIG)
    fixed = me.fix_roots(prob, [(0, 0)])
    assert type(fixed) is level0.Level0Problem
    assert fixed.var_lb[fixed.off_r + 0 * fixed.k + 0] == 1.0
    for s in range(1, fixed.n_state):
        assert fixed.var_ub[fixed.off_r + s * fixed.k + 0] == 0.0
    assert prob.var_ub[prob.off_r + 1 * prob.k + 0] == 1.0
    out = run(fixed, [level0.cover_pass(fixed, ["A"])])
    assert abs(out["passes"][0]["value"] - 1.8) < 1e-6


# ------------------------------------------------------------------------- caps, bundles
def test_forbid_bundle_empties_that_bundle_for_the_state():
    bundles = {"A": ("A",), "B": ("B",), "AB": ("A", "B")}
    prob = build0([0.5] * 6, [0.5] * 6, bundles=bundles)
    assert prob.slots["AB"] == (8, 16)
    out = run(prob, [level0.cover_pass(prob, ["AB"])])
    assert abs(out["passes"][0]["value"] - 6.0) < 1e-6

    forb = level0.forbid_bundle(prob, 0, "AB")
    assert type(forb) is level0.Level0Problem
    lo, hi = forb.slots["AB"]
    for j in range(lo, hi):
        assert forb.var_ub[forb.off_z + 0 * forb.k + j] == 0.0
        assert forb.var_ub[forb.off_y + 0 * forb.k + j] == 0.0
    assert prob.var_ub[prob.off_z + 0 * prob.k + lo] == 1.0          # a copy
    out = run(forb, [level0.cover_pass(forb, ["AB"])])
    assert abs(out["passes"][0]["value"] - 5.0) < 1e-6
    assert not out["z"][0, lo:hi].any()
    # state 0 is still coverable by a pure A slot and a pure B slot, each borrowing 0.3 of
    # state 1, and the rest re-packs into AB slots: everything covered
    out = run(forb, [level0.cover_pass(forb, ["A", "B", "AB"])])
    assert out["passes"][0]["name"] == "cover_A+B+AB"
    assert abs(out["passes"][0]["value"] - 6.0) < 1e-6
    assert not out["z"][0, lo:hi].any()
    assert np.allclose(out["covered"], 1.0, atol=1e-6)


def test_n_max_and_dist_max_caps_bind():
    """Six states of 0.2: one slot of six covers 1.2.  With at most three states per slot, or
    with states further than 2.5 apart kept out of one slot, no slot reaches 0.8."""
    masses = [0.2] * 6
    free = build0(masses)
    assert abs(run(free, [level0.cover_pass(free, ["A"])])["passes"][0]["value"] - 1.2) < 1e-6

    capped = build0(masses, n_max=3)
    assert "cap_n" in capped.rows
    assert abs(run(capped, [level0.cover_pass(capped, ["A"])])["passes"][0]["value"]) < 1e-9

    xy = np.array([[float(s), 0.0] for s in range(6)])
    far = build0(masses, dist_max=2.5, state_xy=xy)
    assert "cap_dist" in far.rows
    assert far.rows["cap_dist"][1] - far.rows["cap_dist"][0] == 6 * far.k   # 6 far pairs
    assert abs(run(far, [level0.cover_pass(far, ["A"])])["passes"][0]["value"]) < 1e-9

    # The cap is per (far pair, slot), not per far pair.  Three states at x = 0, 1, 2, each
    # 1.0 and so in band alone: only (0, 2) is farther than 1.5, and one slot each covers
    # everything.  Summing the slots into one row per pair instead would read "states 0 and 2
    # may not be contacted anywhere on the map" and leave one of them out, at cover 2.0.
    three = SimpleNamespace(M=np.ones((3, 1)), channels=("A",),
                            state_list=[f"S{s}" for s in range(3)])
    near = level0.build_level0(three, {"A": ("A",)}, edges=[(0, 1), (1, 2)], **BAND)
    assert abs(run(near, [level0.cover_pass(near, ["A"])])["passes"][0]["value"] - 3.0) < 1e-6
    split = level0.build_level0(three, {"A": ("A",)}, edges=[(0, 1), (1, 2)],
                                dist_max=1.5,
                                state_xy=np.array([[float(s), 0.0] for s in range(3)]), **BAND)
    assert split.rows["cap_dist"][1] - split.rows["cap_dist"][0] == split.k  # 1 far pair
    out = run(split, [level0.cover_pass(split, ["A"])])
    assert abs(out["passes"][0]["value"] - 3.0) < 1e-6, "every state is in band on its own"
    assert not any(out["z"][0, j] and out["z"][2, j] for j in range(split.k)), \
        "the far pair must still be kept out of any single slot"


def test_a_pass_that_returns_nothing_carries_the_log_out_on_the_exception():
    """A pass can come back with nothing usable: infeasible, or a time limit with no incumbent.

    `solve_passes` raises, and without the log attached the run could not say which pass died
    or what had already been pinned.  The log is the same list `solve_passes` appends to in
    order, so the passes that had already closed are in it too.  Made deterministic with an
    infeasible model -- `no_incumbent` is the same code path, and no time limit reproduces it.
    """
    prob = build0([0.5] * 6)
    passes = [level0.cover_pass(prob, ["A"]), level0.cover_pass(prob, ["B"])]

    # u_0 cannot be both binary and in [2, 3]: the first pass has nothing to return
    infeasible = level0.append_row(prob, "impossible", [prob.off_u], [1.0], 2.0, 3.0)
    try:
        run(infeasible, passes)
        raise AssertionError("expected a SolveFailure")
    except ss.SolveFailure as exc:
        log = getattr(exc, "passes", None)
        assert log, "the pass log must ride out on the exception"
        assert len(log) == 1, "the passes after the failure never ran"
        assert log[0]["name"] == "cover_A"
        assert log[0]["value"] is None and log[0]["certified"] is False
        assert log[0]["status"] == exc.reason == "infeasible"
        assert log[0]["seconds"] >= 0.0


def test_a_zero_objective_pass_is_recorded_not_solved():
    prob = build0([0.5] * 6)
    out = run(prob, [level0.cover_pass(prob, ["B"]), level0.cover_pass(prob, ["A"])])
    assert out["passes"][0] == dict(name="cover_B", value=0.0, certified=True, status=0,
                                    seconds=0.0)
    assert "pin_cover_B" not in out["problem"].rows
    assert abs(out["passes"][1]["value"] - 3.0) < 1e-6


def test_a_pass_slack_widens_its_pin_and_zero_slack_leaves_it_exact():
    """`Pass.slack` is the fraction of its own value a pass lets a later one give up.

    The pin is one appended row `c x <= v + |v| slack + |v| 1e-9 + 1e-12` on the minimised
    objective, and a maximisation's minimised value is negative, so the bound is `v (1 - slack)`
    there: the coverage may fall by that fraction.  At the default 0.0 the row is the exact pin
    every pass has always written.
    """
    prob = build0([0.5] * 6)
    cover = level0.cover_pass(prob, ["A"])

    exact = run(prob, [cover])
    v = -exact["passes"][0]["value"]                 # the minimised frame, so v <= 0
    lo, hi = exact["problem"].rows["pin_cover_A"]
    assert hi - lo == 1
    # `v + |v| * 0.0` is `v` bit for bit, so the default pin is the exact one it always was
    assert exact["problem"].ub[lo] == v + abs(v) * 1e-9 + 1e-12

    slacked = run(prob, [dataclasses.replace(cover, slack=0.1)])
    lo, hi = slacked["problem"].rows["pin_cover_A"]
    assert abs(slacked["problem"].ub[lo] - (v * 0.9 + abs(v) * 1e-9 + 1e-12)) < 1e-12
    assert slacked["problem"].ub[lo] > exact["problem"].ub[lo]
    # the slack is what a later pass may spend, not a discount on this pass's own optimum
    assert abs(slacked["passes"][0]["value"] - exact["passes"][0]["value"]) < 1e-9


def test_compactness_pass_equals_contacts_without_centres():
    prob = build0(CONTIG)
    assert prob.eps == 0.0 and not prob.D.any()
    assert np.array_equal(level0.compactness_pass(prob).c, level0.contacts_pass(prob).c)
    D = np.random.default_rng(0).random((6, prob.k))
    withD = build0(CONTIG, D=D)
    assert withD.eps == ss.eps_lexicographic(withD.M_s, D)
    assert "order_mass" not in withD.rows
    cp = level0.compactness_pass(withD)
    assert np.allclose(cp.c[withD.off_y:withD.off_y + 6 * withD.k],
                       withD.eps * (withD.W * D).ravel())


# ------------------------------------------------------------------- decode regression
def test_decode_zy_on_a_split_problem_equals_the_old_outputs():
    """The body that used to live in `state_splits._solve_scipy` and
    `milp_engines._decode_zy`, kept here verbatim as the regression."""
    _, prob = build(EVEN, 0.001)
    res = ss.solve(prob)
    z, y = res["z"], res["y"]
    S, k = prob.n_state, prob.k
    z0 = np.asarray(z, bool).reshape(S, k)
    y0 = np.clip(np.asarray(y, float).reshape(S, k), 0.0, 1.0)
    y0 = np.where(z0, y0, 0.0)
    y0 = y0 / y0.sum(axis=1, keepdims=True)
    masses = prob.M_s @ y0
    old = dict(z=z0, y=y0, masses=masses, splits=int(z0.sum() - S),
               split_states=[s for s in range(S) if int(z0[s].sum()) >= 2],
               spread_rel=float((masses.max() - masses.min()) / masses.mean()),
               max_dev_rel=float(np.abs(masses - prob.tau).max() / prob.tau))
    for new in (prob.decode_zy(z, y), me._decode_zy(prob, z, y)):
        assert set(new) == set(old)
        for key, val in old.items():
            assert np.allclose(new[key], val), key
    for key in ("masses", "splits", "spread_rel", "max_dev_rel"):
        assert np.allclose(res[key], old[key]), key
    assert res["split_states"] == old["split_states"]


# --------------------------------------------------------------------------- engines
def test_highs_and_scip_match_scipy_on_the_passes():
    prob = build0(CONTIG)
    passes = [level0.cover_pass(prob, ["A"]), level0.contacts_pass(prob)]
    base = run(prob, passes)
    for engine in ("highs", "scip"):
        out = run(prob, passes, engine=engine, time_limit=30.0)
        for p, q in zip(out["passes"], base["passes"]):
            assert p["certified"], (engine, p)
            assert abs(p["value"] - q["value"]) < 1e-6, (engine, p, q)
        assert out["contacts"] == 7
        assert_bands_and_contiguity(prob, out)
