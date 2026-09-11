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
XY6 = np.array([[float(s), 0.0] for s in range(6)])     # the six states on a line, 1 apart


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


def test_a_bundle_is_banded_on_its_own_mean_not_the_global_one():
    """Two bundles of the same mass and different counts: 3.0 of channel A over 3 districts
    and 3.0 of channel B over 1, so A's mean is 1.0 and B's is 3.0 and one band around either
    mean is wrong for the other.  `band` gives each its own: the slot counts, the band rows,
    the greedy point and the solved plan all read the slot's own pair, while `L` and `U` stay
    the global pair the caller passed.
    """
    band = {"A": (0.8, 1.2), "B": (2.4, 3.6)}
    prob = build0([0.5] * 6, [0.5] * 6, band=band, L=0.8, U=1.2)
    assert (prob.L, prob.U) == (0.8, 1.2), "the global pair is what the caller passed"
    assert prob.slots == {"A": (0, 4), "B": (4, 6)}, "K_B = ceil(M^max_B / L_B)"
    lo, hi = prob.slots["B"]
    assert np.allclose(prob.L_j[:lo], 0.8) and np.allclose(prob.U_j[:lo], 1.2)
    assert np.allclose(prob.L_j[lo:hi], 2.4) and np.allclose(prob.U_j[lo:hi], 3.6)

    x, seeds, z, y, masses = _greedy(prob)
    assert len(seeds["A"]) == 3 and len(seeds["B"]) == 1
    # the greedy fills to the slot's own target `L_B` and never past its own `U_B`
    assert all(prob.L_j[j] - 1e-9 <= masses[j] <= prob.U_j[j] + 1e-9
               for j in range(prob.k) if masses[j] > 0), masses
    assert masses[lo] >= 2.4, "B's one district takes the path until it reaches its own L"
    out = run(prob, [level0.cover_pass(prob, ["A", "B"]), level0.contacts_pass(prob)])
    assert abs(out["passes"][0]["value"] - 6.0) < 1e-6, "both bundles cover in full"
    for j in range(prob.k):
        if out["u"][j]:
            assert prob.L_j[j] - 1e-6 <= out["masses"][j] <= prob.U_j[j] + 1e-6, (j, out["masses"])
            assert ss.connected(out["z"][:, j], EDGES)
    # the same six states, three districts on one channel and one on the other: the global
    # band would have refused B's district at 3.0 and A's at 1.0 could not have been in B's
    assert abs(out["masses"][lo] - 3.0) < 1e-6 and int(out["u"][lo:hi].sum()) == 1
    assert int(out["u"][:lo].sum()) == 3

    # the check names the slot's own band, not the global one
    bad = np.zeros(prob.n_var)
    bad[prob.off_u + lo] = 1.0
    try:
        level0.check_point(prob, bad)
        raise AssertionError("a used slot holding nothing must fail its band")
    except ValueError as exc:
        assert "outside its band [2.4, 3.6]" in str(exc), exc


def test_a_band_pair_and_an_unknown_bundle_are_refused():
    assert build0([0.5] * 6, band=(0.8, 1.2)).slots == build0([0.5] * 6).slots
    for band in ({"ZZ": (0.8, 1.2)}, {"A": (1.2, 0.8)}, {"A": (0.0, 1.2)}):
        try:
            build0([0.5] * 6, band=band)
            raise AssertionError(f"expected a ValueError for band={band}")
        except ValueError:
            pass


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


def test_dist_max_state_relaxes_the_cap_for_its_own_pairs_only():
    """Six states of 0.2 on a line, 1 apart, under `dist_max = 2.5`: no slot spans more than
    three states, so none reaches 0.8 and nothing is covered.  `dist_max_state = {0: 3.5}`
    lets state 0 share a slot with state 3, 3 apart, and {0, 1, 2, 3} reaches 0.8.  The pair
    (1, 4), also 3 apart, keeps the plain cap, and (0, 4), (0, 5) are beyond 3.5."""
    masses = [0.2] * 6
    plain = build0(masses, dist_max=2.5, state_xy=XY6)
    assert abs(run(plain, [level0.cover_pass(plain, ["A"])])["passes"][0]["value"]) < 1e-9

    wide = build0(masses, dist_max=2.5, state_xy=XY6, dist_max_state={0: 3.5})
    assert {(a, b) for a, b, _ in _far_pairs(wide)} == {(0, 4), (0, 5), (1, 4), (1, 5), (2, 5)}
    assert wide.rows["cap_dist"][1] - wide.rows["cap_dist"][0] == 5 * wide.k
    out = run(wide, [level0.cover_pass(wide, ["A"])])
    assert abs(out["passes"][0]["value"] - 0.8) < 1e-6
    used = np.flatnonzero(out["u"])
    assert len(used) == 1 and set(np.flatnonzero(out["z"][:, used[0]])) == {0, 1, 2, 3}

    try:
        build0(masses, state_xy=XY6, dist_max_state={0: 3.5})
    except ValueError as exc:
        assert "dist_max" in str(exc)
    else:
        raise AssertionError("an override without the cap it relaxes must be refused")


def test_unset_dist_max_state_and_an_empty_require_cover_leave_the_model_as_it_was():
    """`dist_max_state` None, empty, or below `dist_max` (it never tightens) builds exactly
    the model the plain cap builds, radius rows and anchors included; `require_cover` naming
    no channel changes no row bound."""
    bundles = {"A": ("A",), "AB": ("A", "B")}
    kw = dict(dist_max=2.5, radius_max=1.5, state_xy=XY6, anchors=[(0, 0)])
    base = build0([0.3] * 6, [0.2] * 6, bundles=bundles, **kw)
    for over in (None, {}, {0: 1.0}):
        other = build0([0.3] * 6, [0.2] * 6, bundles=bundles, dist_max_state=over, **kw)
        assert other.A.shape == base.A.shape and (other.A != base.A).nnz == 0, over
        for f in ("lb", "ub", "var_lb", "var_ub", "c", "integrality"):
            assert np.array_equal(getattr(other, f), getattr(base, f)), (over, f)
        assert other.rows == base.rows
    same = level0.require_cover(base, 0, ())
    assert np.array_equal(same.lb, base.lb) and np.array_equal(same.ub, base.ub)


def test_require_cover_makes_the_named_bundle_take_the_state_s_whole_channel():
    """Two bundles both carry channel A, as `N` and `WH_PLUS` both carry `N_WH`: `N` (A alone)
    and `P` (A and B).  A cover pass over `P` alone puts all of state 0 in `P` slots.  With
    `P` forbidden on state 0 and `require_cover(0, A)`, the same pass must leave state 0's A
    to the `N` slots, all of it.  Only the forced cover row moves, to its `cover_ub`, and a
    channel the model does not carry is skipped."""
    prob = build0([0.5] * 6, [0.5] * 6, bundles={"N": ("A",), "P": ("A", "B")})
    lo_n, hi_n = prob.slots["N"]
    lo_p, hi_p = prob.slots["P"]
    out = run(prob, [level0.cover_pass(prob, ["P"])])
    assert abs(out["y"][0, lo_p:hi_p].sum() - 1.0) < 1e-6, "P would carry state 0 whole"

    forced = level0.require_cover(level0.forbid_bundle(prob, 0, "P"), 0, ["A", "ZZ"])
    row0 = forced.rows["cover"][0]
    assert np.flatnonzero(forced.lb != prob.lb).tolist() == [row0]      # state 0, channel A
    assert forced.lb[row0] == prob.cover_ub[0, 0] and np.isinf(prob.lb[row0])   # a copy
    out = run(forced, [level0.cover_pass(forced, ["P"])])
    assert abs(out["y"][0, lo_n:hi_n].sum() - 1.0) < 1e-6
    assert not out["z"][0, lo_p:hi_p].any()
    assert abs(out["covered"][0, 0] - 1.0) < 1e-6


def test_radius_max_bounds_an_anchored_slot_to_its_root():
    """Six states of 0.2 at x = 0..5, anchored on state 0.  A 2 km radius takes states 3, 4
    and 5 out of that slot as a bound on `z`, not a row, and the anchor makes the slot used, so
    the 0.6 it can still reach is below `L` and the model has no plan at all.  Without the
    radius the same six states cover 1.2 in one slot."""
    masses = [0.2] * 6
    free = build0(masses)
    assert abs(run(free, [level0.cover_pass(free, ["A"])])["passes"][0]["value"] - 1.2) < 1e-6

    prob = build0(masses, anchors=[(0, 0)], radius_max=2.0, state_xy=XY6)
    assert prob.radius_max == 2.0 and prob.slot_root == (0, -1)
    K = prob.k
    for s in (3, 4, 5):
        assert prob.var_ub[prob.off_z + s * K + 0] == 0.0
        assert prob.var_ub[prob.off_y + s * K + 0] == 0.0
    for s in (0, 1, 2):
        assert prob.var_ub[prob.off_z + s * K + 0] == 1.0
    assert prob.var_ub[prob.off_z + 5 * K + 1] == 1.0, "slot 1 has no root and no z bound"
    try:
        run(prob, [level0.cover_pass(prob, ["A"])])
    except ss.SolveFailure as exc:
        assert exc.reason == "infeasible"
    else:
        raise AssertionError("an anchored slot capped to 0.6 of mass cannot reach L")

    bad = np.zeros(prob.n_var)
    bad[prob.off_z + 0 * K + 0] = 1.0                 # the anchor, so it is not what is named
    bad[prob.off_z + 5 * K + 0] = 1.0
    try:
        level0.check_point(prob, bad)
        raise AssertionError("a contact outside the radius must fail the check")
    except ValueError as exc:
        assert "beyond radius_max" in str(exc) and "slot 0's root 0" in str(exc)


def test_a_slot_with_no_root_takes_the_diameter_bound_instead():
    """A free root allows a diameter, not a radius: a rootless slot gets the `cap_dist` pair
    rows at `2 radius_max` and no `z` bound.  On the line at 1 km spacing only (0, 5) is more
    than 4 km apart, so it is one row per rootless slot."""
    both = build0([0.2] * 6, radius_max=2.0, state_xy=XY6)
    assert both.slot_root == (-1, -1) and both.k == 2
    lo, hi = both.rows["cap_dist"]
    assert hi - lo == 2, "one far pair on each of the two rootless slots"
    assert both.var_ub[both.off_z:both.off_z + 6 * both.k].all()

    one = build0([0.2] * 6, anchors=[(0, 0)], radius_max=2.0, state_xy=XY6)
    lo, hi = one.rows["cap_dist"]
    assert hi - lo == 1, "the rooted slot carries bounds, only slot 1 carries the pair row"


# ---------------------------------------------------------------------------- warm start
def _greedy(prob, **kw):
    """`greedy_plan` plus the row check and the decoded `z`, `y`, slot masses."""
    x, seeds = level0.greedy_plan(prob, **kw)
    level0.check_point(prob, x)
    Ax = prob.A @ x
    assert np.all(Ax >= prob.lb - 1e-6) and np.all(Ax <= prob.ub + 1e-6)
    assert np.all(x >= prob.var_lb - 1e-9) and np.all(x <= prob.var_ub + 1e-9)
    S, K = prob.n_state, prob.k
    z = x[prob.off_z:prob.off_z + S * K].reshape(S, K) > 0.5
    y = x[prob.off_y:prob.off_y + S * K].reshape(S, K)
    return x, seeds, z, y, (prob.W * y).sum(axis=0)


def test_greedy_plan_is_feasible_and_the_solver_does_at_least_as_well():
    """The greedy point passes every row, and a scipy solve of the cover pass is never below
    its coverage: equal on the even toy (three whole pairs), strictly above on `CONTIG`, where
    the greedy fills one slot of 1.1 and the MILP buys a split to cover 1.8."""
    prob = build0([0.5] * 6)
    x, seeds, z, y, masses = _greedy(prob)
    assert abs(masses.sum() - 3.0) < 1e-9 and seeds == {"A": [(0, 0), (2, 1), (4, 2)], "B": []}
    out = run(prob, [level0.cover_pass(prob, ["A"])], warm_start=x, warm_seconds=0.25)
    head, cover = out["passes"]
    assert head == dict(name="greedy", value={"A": 3.0, "B": 0.0}, certified=False,
                        status="warm_start", seconds=0.25)
    assert cover["value"] >= 3.0 - 1e-9
    for j in range(prob.k):
        assert ss.connected(z[:, j], EDGES) if z[:, j].any() else True

    prob = build0(CONTIG)
    x, seeds, z, y, masses = _greedy(prob)
    assert abs(masses.sum() - 1.1) < 1e-9
    out = run(prob, [level0.cover_pass(prob, ["A"])], warm_start=x)
    assert out["passes"][1]["value"] >= 1.1 + 0.5      # 1.8 at the optimum

    # an anchored state enters only its own slot, and seeds it
    prob = build0([0.5] * 6, anchors=[(5, 0)])
    x, seeds, z, y, masses = _greedy(prob)
    assert z[5, 0] and z[4, 0] and seeds["A"][0] == (5, 0) and not z[5, 1:].any()
    assert abs(masses.sum() - 3.0) < 1e-9


def test_greedy_plan_places_every_anchor_and_never_a_forbidden_contact():
    """Anchors `{2: 0, 5: 1}` (the dict form): slot 0 is seeded at state 2 and slot 1 at
    state 5, whatever a free seed would have chosen.  A contact with `var_ub = 0` (`bound_z`)
    is never entered.  A state anchored on two slots is shared between them, half each, and
    an anchored slot that cannot fill raises rather than returning an unplaced anchor."""
    prob = build0([0.5] * 6, anchors={2: 0, 5: 1})
    x, seeds, z, y, masses = _greedy(prob)
    assert z[2, 0] and z[5, 1] and seeds["A"][:2] == [(2, 0), (5, 1)]
    assert abs(masses.sum() - 2.0) < 1e-9        # {1, 2} and {4, 5}; 0 and 3 are stranded
    out = run(prob, [level0.cover_pass(prob, ["A"])], warm_start=x)
    assert out["passes"][1]["value"] >= 2.0 - 1e-9

    forbidden = build0([0.5] * 6, anchors={2: 0})
    ss.bound_z(forbidden, 3, 0, 0.0, 0.0)
    x, seeds, z, y, masses = _greedy(forbidden)
    assert z[2, 0] and not z[3, 0] and z[1, 0]

    shared = build0([2.0, 0.5, 0.5, 0.5, 0.0, 0.0], anchors=[(0, 0), (0, 1)])
    x, seeds, z, y, masses = _greedy(shared)
    assert z[0, 0] and z[0, 1] and abs(y[0, 0] - 0.5) < 1e-9 and abs(y[0, 1] - 0.5) < 1e-9
    assert abs(masses[0] - 1.0) < 1e-9 and abs(masses[1] - 1.0) < 1e-9

    # state 5 alone is 0.3 and its only neighbour is committed: the anchor cannot be met
    prior = np.zeros((6, 2))
    prior[4, 0] = 1.0
    stuck = build0([0.5, 0.5, 0.5, 0.5, 0.0, 0.3], prior=prior, anchors={5: 0})
    try:
        level0.greedy_plan(stuck)
        raise AssertionError("an anchored slot that cannot fill must raise")
    except ValueError as exc:
        assert "anchored slot 0" in str(exc)
    bad = np.zeros(stuck.n_var)
    try:
        level0.check_point(stuck, bad)
        raise AssertionError("an unplaced anchor must fail the check")
    except ValueError as exc:
        assert "anchored contact z[5, 0]" in str(exc)


def test_greedy_plan_leaves_a_slot_it_cannot_fill_unused():
    """Total 1.4 on states 0..2: one slot of 1.0, and the 0.4 left cannot reach 0.8 from any
    seed, so slot 1 is all zero (`u = 0`) rather than a below-band slot."""
    prob = build0([0.5, 0.5, 0.4, 0.0, 0.0, 0.0])
    x, seeds, z, y, masses = _greedy(prob)
    assert prob.k == 2 and abs(masses[0] - 1.0) < 1e-9 and masses[1] == 0.0
    assert not z[:, 1].any() and x[prob.off_u + 1] == 0.0 and x[prob.off_u] == 1.0
    assert seeds == {"A": [(0, 0)], "B": []}


def test_greedy_plan_respects_the_caps():
    """Six states of 0.2: at most three per slot, or far pairs kept apart, and no slot reaches
    0.8, so the plan is empty (what the MILP finds too); at four per slot one slot of exactly
    four states covers 0.8 and the `cap_n` row holds."""
    masses = [0.2] * 6
    for capped in (build0(masses, n_max=3),
                   build0(masses, dist_max=2.5,
                          state_xy=np.array([[float(s), 0.0] for s in range(6)]))):
        x, seeds, z, y, m = _greedy(capped)
        assert not x.any() and seeds == {"A": [], "B": []}
    four = build0(masses, n_max=4)
    x, seeds, z, y, m = _greedy(four)
    assert abs(m[0] - 0.8) < 1e-9 and int(z[:, 0].sum()) == 4 and not z[:, 1].any()


def test_greedy_plan_respects_the_radius():
    """The model only carries a diameter bound on a rootless slot, so the greedy is what keeps
    the warm start inside the radius itself.

    Six states of 0.5 at 1 km spacing.  At `radius_max = 0.5` no slot reaches past its own
    seed, and 0.5 is below `L`, so the point is empty -- while the pair rows at 2 x 0.5 = 1 km
    would still have allowed the neighbouring pair the greedy would otherwise have taken.
    Anchored at state 2 with a 1 km radius the slot may hold states 1, 2 and 3 and no others.
    """
    tight = build0([0.5] * 6, radius_max=0.5, state_xy=XY6)
    assert (1, 2) not in {(a, b) for a, b, _ in _far_pairs(tight)}, "the pair rows allow it"
    x, seeds, z, y, m = _greedy(tight)
    assert not x.any() and seeds == {"A": [], "B": []}

    anch = build0([0.5] * 6, anchors=[(2, 0)], radius_max=1.0, state_xy=XY6)
    x, seeds, z, y, m = _greedy(anch)
    assert seeds["A"][0] == (2, 0)
    assert set(np.flatnonzero(z[:, 0]).tolist()) <= {1, 2, 3}
    assert m[0] >= anch.L - 1e-9


def _far_pairs(prob):
    """The `(s, s', slot)` triples the `cap_dist` rows carry, read back the way the greedy
    reads them."""
    out = []
    if "cap_dist" not in prob.rows:
        return out
    a, b = prob.rows["cap_dist"]
    cap = prob.A.tocsr()[a:b]
    K = prob.k
    for i in range(b - a):
        cols = cap.indices[cap.indptr[i]:cap.indptr[i + 1]]
        pair = sorted({(c - prob.off_z) // K for c in cols})
        out.append((pair[0], pair[-1], int((cols[0] - prob.off_z) % K)))
    return out


def test_greedy_plan_splits_a_state_between_consecutive_slots():
    """Four states of 0.7: state 0 plus 3/7 of state 1 lands slot A on `tau = 1.0`; the next
    slot seeds from state 1's remaining 4/7 and takes state 2 whole.  Both slots contact
    state 1 and its shares add to one; the last 0.7 has no partner and stays uncovered."""
    prob = build0([0.7, 0.7, 0.7, 0.7, 0.0, 0.0])
    x, seeds, z, y, masses = _greedy(prob)
    both = [j for j in range(prob.k) if z[1, j]]
    assert len(both) == 2 and abs(y[1].sum() - 1.0) < 1e-9
    assert set(np.round(masses[both], 9)) == {1.0, 1.1}
    assert abs(masses.sum() - 2.1) < 1e-9 and int(x[prob.off_u:].sum()) == 2
    assert_bands_and_contiguity(prob, dict(u=x[prob.off_u:] > 0.5, masses=masses, z=z))


def test_greedy_plan_honours_max_splits():
    """The fixture above has the greedy split state 1 between two slots on its own; capping
    state 1 at one slot must change the greedy's own choice, not leave `check_point` (called
    inside `greedy_plan` itself) to catch an infeasible point."""
    prob = build0([0.7, 0.7, 0.7, 0.7, 0.0, 0.0])
    capped = level0.max_splits(prob, {"S1": 1})
    x, seeds, z, y, masses = _greedy(capped)        # raises if greedy_plan's own point fails
    assert int(z[1].sum()) <= 1


def test_fixed_used_slots_are_used_in_every_pass_or_the_pass_is_infeasible():
    """`fixed_used={"A": 2}` pins `u_0 = u_1 = 1`: both slots are used after every pass, the
    cover is at least `2L`, and the `u` ordering row between slot 0 and slot 1 is gone.  A
    count the mass cannot fill makes the pass infeasible, never a silent empty plan."""
    prob = build0([0.5] * 6, fixed_used={"A": 2})
    assert prob.var_lb[prob.off_u] == 1.0 and prob.var_lb[prob.off_u + 1] == 1.0
    assert prob.var_lb[prob.off_u + 2] == 0.0
    lo, hi = prob.rows["order_u"]
    assert hi - lo == 1                     # (2, 3) only: (0, 1) and (1, 2) say nothing
    out = run(prob, [level0.cover_pass(prob, ["A"]), level0.contacts_pass(prob)])
    assert out["u"][0] and out["u"][1]
    assert out["passes"][0]["value"] >= 2 * prob.L - 1e-9
    x, seeds, z, y, masses = _greedy(prob)
    assert x[prob.off_u] == 1.0 and x[prob.off_u + 1] == 1.0

    short = build0([0.5, 0.5, 0.4, 0.0, 0.0, 0.0], fixed_used={"A": 2})
    try:
        run(short, [level0.cover_pass(short, ["A"])])
        raise AssertionError("two used slots need 1.6 of mass; 1.4 cannot be feasible")
    except ss.SolveFailure as exc:
        assert exc.passes[-1]["status"] == "infeasible"
    try:
        build0([0.5] * 6, fixed_used={"A": 5})
        raise AssertionError("expected a ValueError for a count above the slot count")
    except ValueError:
        pass


def test_max_used_closes_the_slots_past_the_ceiling():
    """`max_used={"A": 1}` bounds `u_1, u_2, ...` (and their `z`, `y`) to zero: the cover pass
    opens one district where the mass would fill three, the greedy stops at one slot too, and
    a ceiling under a floor is refused."""
    prob = build0([0.5] * 6, max_used={"A": 1})
    assert prob.var_ub[prob.off_u] == 1.0
    assert (prob.var_ub[prob.off_u + 1:prob.off_u + prob.k] == 0.0).all()
    out = run(prob, [level0.cover_pass(prob, ["A"]), level0.contacts_pass(prob)])
    assert int(sum(out["u"])) == 1
    assert prob.L - 1e-9 <= out["passes"][0]["value"] <= prob.U + 1e-9
    x, seeds, z, y, masses = _greedy(prob)
    assert int(x[prob.off_u:].sum()) == 1 and len(seeds["A"]) == 1
    try:
        build0([0.5] * 6, fixed_used={"A": 2}, max_used={"A": 1})
        raise AssertionError("expected a ValueError for a ceiling under the floor")
    except ValueError:
        pass


def test_serve_states_forces_a_state_into_some_district():
    """`serve_states(problem, [1])` adds `sum_j z_1j >= 1`.  Under the contacts objective alone
    the empty plan (no slot used, 0 contacts) is optimal; with the row, state 1 must sit in a
    district, which needs state 0's mass too, so the optimum is 2 contacts.  The greedy
    attaches the state to the used slot next to it with room under `U`."""
    masses = [1.0, 0.1, 0.0, 0.0, 0.0, 0.0]
    plain = build0(masses)
    assert int(sum(run(plain, [level0.contacts_pass(plain)])["u"])) == 0
    prob = level0.serve_states(plain, [1])
    lo, hi = prob.rows["serve"]
    assert hi - lo == 1 and prob.lb[lo] == 1.0 and prob.ub[lo] == np.inf
    out = run(prob, [level0.contacts_pass(prob)])
    assert out["z"][1].any() and out["z"][0].any() and out["contacts"] == 2
    assert_bands_and_contiguity(prob, out)
    x, seeds, z, y, m = _greedy(prob)
    assert z[1].any() and abs(m.sum() - 1.1) < 1e-9
    assert level0.serve_states(plain, []) is plain


def test_max_splits_caps_how_many_slots_a_state_may_touch():
    """Full cover of `CONTIG` needs 7 contacts, and state 2 is the one split between the two
    slots (states 0..2 in one, 2..5 in the other, sharing state 2).  Capping state 2 at one
    slot removes the bridge: the best cover without it is 1.2 (states 1..4 alone), four
    contacts, and no state touches more than its cap."""
    prob = build0(CONTIG)
    out = run(prob, [level0.cover_pass(prob, ["A"]), level0.contacts_pass(prob)])
    assert abs(out["passes"][0]["value"] - 1.8) < 1e-6 and out["contacts"] == 7
    assert int(out["z"][2].sum()) == 2, "state 2 is the one the uncapped optimum splits"

    capped = level0.max_splits(prob, {"S2": 1})
    lo, hi = capped.rows["max_splits"]
    assert hi - lo == 1 and capped.lb[lo] == -np.inf and capped.ub[lo] == 1.0
    out = run(capped, [level0.cover_pass(capped, ["A"]), level0.contacts_pass(capped)])
    assert abs(out["passes"][0]["value"] - 1.2) < 1e-6, "the bridge through state 2 is gone"
    assert out["contacts"] == 4
    assert (out["z"].sum(axis=1) <= 1).all()
    assert_bands_and_contiguity(capped, out)

    # a state not in the problem is ignored, and the problem is returned unchanged
    assert level0.max_splits(prob, {"ZZ": 1}) is prob
    # a cap below 1 is refused, even for a state the model does not carry
    for bad in ({"S2": 0}, {"ZZ": -1}):
        try:
            level0.max_splits(prob, bad)
            raise AssertionError(f"expected a ValueError for {bad}")
        except ValueError:
            pass


def test_band_break_lets_a_slot_touching_the_capped_state_exceed_u():
    """State 0 alone carries 1.4, more than `U = 1.2`; state 5's 1.0 sits three zero-mass
    states away and never shares a slot with it.  Capping state 0 at one slot blocks the
    second slot that would otherwise finish covering it, so 0.2 of its mass goes uncovered;
    `band_break` lets the one allowed slot reach `U + 0.2` instead, at no cost to state 5's
    own slot, which a state 0 allowance never touches."""
    prob = build0([1.4, 0.0, 0.0, 0.0, 0.0, 1.0])
    capped = level0.max_splits(prob, {"S0": 1})
    out = run(capped, [level0.cover_pass(capped, ["A"])])
    covered_s0 = float(out["y"][0].sum())
    assert covered_s0 < 1.0 - 1e-6              # state 0's mass cannot all fit in one slot

    loosened = level0.band_break(capped, {"S0": 0.2})
    assert set(loosened.rows) == set(capped.rows)          # no row added or renamed
    out2 = run(loosened, [level0.cover_pass(loosened, ["A"])])
    covered_s0_2 = float(out2["y"][0].sum())
    assert abs(covered_s0_2 - 1.0) < 1e-6 and covered_s0_2 > covered_s0 + 1e-6

    j0 = int(np.flatnonzero(out2["z"][0])[0])
    j5 = int(np.flatnonzero(out2["z"][5])[0])
    assert j5 != j0
    assert out2["masses"][j0] > prob.U + 1e-6, "the allowed slot actually exceeded U"
    assert out2["masses"][j5] <= prob.U + 1e-6, "a slot with no contact with S0 stays at U"

    # a non-positive allowance and a state the problem does not carry are both ignored
    assert level0.band_break(capped, {"S0": 0.0}) is capped
    assert level0.band_break(capped, {"ZZ": 5.0}) is capped


# ------------------------------------------------------------------------------- plus pairing
def test_plus_pair_rows_bind_when_both_bundles_are_present():
    """One state, `WH_PLUS` mass 1.0 and `FI_PLUS` mass 1.5: unpaired, `WH_PLUS` covers fully
    at y=1.0 (mass 1.0, in band) and `FI_PLUS` caps at y=0.8 (mass 1.2 = U; a second, lighter
    slot would fall below L, so 0.8 is `FI_PLUS`'s own maximum), unequal.  `plus_pair` adds
    one equality row per state and the same cover pass then holds both to the tighter cap,
    0.8, exactly."""
    both = SimpleNamespace(M=np.array([[1.0, 1.5]]), channels=("A", "B"), state_list=["S0"])
    prob = level0.build_level0(both, {"WH_PLUS": ("A",), "FI_PLUS": ("B",)}, edges=[],
                               L=0.8, U=1.2, eta=0.05)
    cover = [level0.cover_pass(prob, ["WH_PLUS", "FI_PLUS"])]
    unpaired = run(prob, cover)["y"]
    assert abs(unpaired[0, 0] - 1.0) < 1e-6 and abs(unpaired[0, 2] - 0.8) < 1e-6

    paired = level0.plus_pair(prob)
    assert paired.rows["plus_pair"][1] - paired.rows["plus_pair"][0] == 1
    out = run(paired, cover)
    y = out["y"]
    assert abs(y[0, 0] - 0.8) < 1e-6 and abs(y[0, 2] - 0.8) < 1e-6
    assert abs(out["passes"][0]["value"] - 2.0) < 1e-6, "0.8*(1.0+1.5), down from the unpaired 2.2"

    # neither bundle present, or WH_PLUS alone with no target: unchanged
    ab_only = build0([0.5] * 6)
    assert level0.plus_pair(ab_only) is ab_only
    wh_only = level0.build_level0(both, {"WH_PLUS": ("A",)}, edges=[], L=0.8, U=1.2, eta=0.05)
    assert level0.plus_pair(wh_only) is wh_only


def test_plus_pair_target_pins_fi_plus_when_wh_plus_is_absent():
    """`FI_PLUS` alone: `target` pins a named state's total `FI_PLUS` share exactly, 0 for a
    state with no positive target (so the FI stage cannot serve it there instead), and a state
    absent from `target` gets no row and is free.  S0 (mass 2.0) is pinned to 0.4, exactly L
    alone, since its only neighbour S1 is pinned to 0 and cannot bridge it to anything else;
    S2..S5 (mass 0.5 each, absent from `target`) cover fully."""
    prob = build0([0.0] * 6, [2.0, 0.5, 0.5, 0.5, 0.5, 0.5], bundles={"FI_PLUS": ("B",)})
    target = {"S0": 0.4, "S1": 0.0}
    pinned = level0.plus_pair(prob, target=target)
    lo, hi = pinned.rows["plus_pair"]
    assert hi - lo == 2
    out = run(pinned, [level0.cover_pass(pinned, ["FI_PLUS"])])
    y = out["y"].sum(axis=1)
    assert abs(y[0] - 0.4) < 1e-6 and y[1] == 0.0
    assert np.allclose(y[2:], 1.0)

    # a zero target is also a bound, so the greedy plan never puts S1 in FI_PLUS and its
    # point satisfies the rows
    lo_j, hi_j = pinned.slots["FI_PLUS"]
    for off in (pinned.off_z, pinned.off_y):
        assert not pinned.var_ub[off + 1 * pinned.k + lo_j:off + 1 * pinned.k + hi_j].any()
    assert pinned.var_ub[pinned.off_y + lo_j:pinned.off_y + hi_j].all()
    greedy = level0.plus_pair(build0([0.0] * 6, [2.0, 0.5, 0.5, 0.5, 0.5, 0.5],
                                     bundles={"FI_PLUS": ("B",)}),
                              target={f"S{i}": 0.0 for i in range(1, 6)})
    x, _ = level0.greedy_plan(greedy)
    y = x[greedy.off_y:greedy.off_y + greedy.n_state * greedy.k].reshape(greedy.n_state, greedy.k)
    assert not y[1:].any()

    # a state absent from target names no row at all
    assert level0.plus_pair(prob, target={}) is prob


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


def test_moments_from_seeds_measure_from_the_seed_state():
    """`D[s, j]` is the squared centroid distance from `s` to the state slot `j` is seeded at,
    so the seed's own row is zero and a slot the greedy never used keeps a zero column."""
    prob = build0([0.5] * 6)
    x, seeds, z, y, masses = _greedy(prob)
    assert seeds == {"A": [(0, 0), (2, 1), (4, 2)], "B": []}
    D = level0.moments_from_seeds(prob, seeds, XY6)
    assert D.shape == (6, prob.k)
    for j, seed in ((0, 0), (1, 2), (2, 4)):
        assert np.allclose(D[:, j], [(s - seed) ** 2.0 for s in range(6)])
        assert D[seed, j] == 0.0
    assert not D[:, 3].any(), "slot 3 is unused, so it has no seed and no tie-break"
    assert level0.build_level0(cells([0.5] * 6), BUNDLES, edges=EDGES, D=D,
                               **BAND).eps == ss.eps_lexicographic(prob.M_s, D)


def test_compactness_with_seed_moments_pulls_a_slot_towards_its_seed():
    """Three states of 0.5 at x = 0, 1, 2: one slot of 1.2 is the whole plan (two would need
    1.6 of the 1.5 there is), it must touch all three states to reach 1.2, and which state
    gives up 0.6 of itself is free at equal coverage and equal contacts.  The seed moments are
    what settles it: seeded at state 0 the far state carries the fraction, seeded at state 2
    the near one does, and the coverage and contact values are the same either way."""
    three = SimpleNamespace(M=np.full((3, 1), 0.5), channels=("A",),
                            state_list=[f"S{s}" for s in range(3)])
    xy = np.array([[float(s), 0.0] for s in range(3)])
    edges = [(0, 1), (1, 2)]
    shares = {}
    for seed in (0, 2):
        base = level0.build_level0(three, {"A": ("A",)}, edges=edges, **BAND)
        D = level0.moments_from_seeds(base, {"A": [(seed, 0)]}, xy)
        assert np.allclose(D[:, 0], [(s - seed) ** 2.0 for s in range(3)]) and not D[:, 1].any()
        prob = level0.build_level0(three, {"A": ("A",)}, edges=edges, D=D, **BAND)
        assert prob.eps > 0.0
        out = run(prob, [level0.cover_pass(prob, ["A"]), level0.contacts_pass(prob),
                         level0.compactness_pass(prob)])
        cov, con, comp = out["passes"]
        assert all(p["certified"] for p in out["passes"]), out["passes"]
        assert abs(cov["value"] - 1.2) < 1e-6 and con["value"] == 3
        assert int(out["u"].sum()) == 1
        shares[seed] = out["y"][:, 0]
    # the tie-break ranks equal-contact solutions and buys none: both runs pin the same
    # coverage and the same three contacts, and only the shares move
    assert np.allclose(shares[0], [1.0, 1.0, 0.4], atol=1e-6), shares
    assert np.allclose(shares[2], [0.4, 1.0, 1.0], atol=1e-6), shares


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
