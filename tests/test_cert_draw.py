"""
test_cert_draw.py -- post-hoc certificates for a stage-1 draw (td/solvers/cert_draw.py).

The load-bearing test is `test_integer_floor_matches_brute_force`: on instances small enough
to enumerate, the MILP's `t*` must equal the brute-force minimum max-deviation **exactly**.
That is what makes the symmetry breaking (heaviest zip pinned to district 0, districts 1..k-1
ordered by mass) safe to trust at sizes no test can enumerate -- a break that cut off the
optimum would show up here as a `t*` that is too large.

Everything else checks that a certificate never claims more than it proved: `proved` is True
only when the engine returned status 0 (trap 15), and `time_limit=0` gets an honest
"not attempted" rather than a number.

Fixtures are synthetic and tiny; no instance file, no network, no geometry cache.
"""
from __future__ import annotations

import itertools
import math

import numpy as np

from td.solvers import cert_draw
from td.solvers import centers as centers_mod


# ------------------------------------------------------------------------- fixtures
def two_clusters():
    """Six unit-mass points, three around each of two well-separated centers."""
    xy = np.array([[0.0, 0.0], [0.5, 0.3], [-0.4, 0.2],
                   [10.0, 0.0], [10.5, 0.3], [9.6, 0.2]])
    M = np.ones(6)
    centers = np.array([[0.0, 0.0], [10.0, 0.0]])
    good = np.array([0, 0, 0, 1, 1, 1])
    return xy, M, centers, good


def brute_min_max_dev(M, k):
    """Smallest max_j |M_j - target| over every assignment of `M` into `k` labelled parts."""
    M = np.asarray(M, float)
    target = M.sum() / k
    best = math.inf
    for lab in itertools.product(range(k), repeat=M.size):
        mass = np.bincount(np.array(lab), weights=M, minlength=k)
        best = min(best, float(np.abs(mass - target).max()))
    return best


# ------------------------------------------------- 2. the integer balance floor is exact
def test_integer_floor_matches_brute_force():
    """k=2 over six weights: the MILP's t* is the enumerated optimum, to the last bit."""
    M = np.array([5.0, 3.0, 3.0, 2.0, 2.0, 1.5])       # sums to 16.5; no exact split at 8.25
    want = brute_min_max_dev(M, 2)
    assert want > 0, "fixture must not be exactly splittable, or the test proves nothing"
    got = cert_draw.cert_integer_balance_floor(M, 2, time_limit=30.0)
    assert got["proved"] is True, got["status"]
    assert got["solver_status"] == 0
    assert math.isclose(got["t"], want, rel_tol=0, abs_tol=1e-9), (got["t"], want)


def test_integer_floor_matches_brute_force_k3():
    """k=3 exercises the mass-ordering symmetry break; it must not cut off the optimum."""
    M = np.array([4.0, 3.0, 3.0, 2.0, 2.0, 1.0])
    want = brute_min_max_dev(M, 3)
    got = cert_draw.cert_integer_balance_floor(M, 3, time_limit=30.0)
    assert got["proved"] is True, got["status"]
    assert math.isclose(got["t"], want, rel_tol=0, abs_tol=1e-9), (got["t"], want)


def test_integer_floor_reports_a_reachable_partition():
    """`t` is primal: the labels it returns really do achieve it."""
    M = np.array([5.0, 3.0, 3.0, 2.0, 2.0, 1.5])
    got = cert_draw.cert_integer_balance_floor(M, 2, time_limit=30.0, warm_labels=[0] * 5 + [1])
    lab = np.array(got["labels"])
    mass = np.bincount(lab, weights=M, minlength=2)
    target = M.sum() / 2
    assert math.isclose(float(np.abs(mass - target).max()), got["t"], abs_tol=1e-9)
    assert math.isclose(got["t_rel"], got["t"] / target, abs_tol=1e-12)
    # the reference draw (one zip against five) is far worse than the floor
    assert got["reference_max_dev"] > got["t"]


def test_constructed_primal_is_a_real_partition():
    """The LPT+polish primal is only worth reporting if its labels really achieve `t`."""
    rng = np.random.default_rng(7)
    M = rng.uniform(0.2, 8.0, size=300)
    k = 7
    got = cert_draw.cert_integer_balance_floor(M, k, time_limit=1.0)
    target = M.sum() / k
    lab = np.array(got["labels"])
    assert lab.min() >= 0 and lab.max() < k and lab.size == M.size
    mass = np.bincount(lab, weights=M, minlength=k)
    assert math.isclose(float(np.abs(mass - target).max()), got["t"], abs_tol=1e-9)
    assert got["t_greedy"] <= got["t_lpt"] + 1e-12        # the polish never makes it worse
    assert got["t"] <= got["t_greedy"] + 1e-12            # and the report takes the better one
    # LPT alone already beats a random balanced-by-count split by orders of magnitude
    rough = np.bincount(np.arange(M.size) % k, weights=M, minlength=k)
    assert got["t"] < float(np.abs(rough - target).max())


def test_integer_floor_k1_is_trivially_zero():
    got = cert_draw.cert_integer_balance_floor(np.array([1.0, 2.0, 3.0]), 1)
    assert got["proved"] is True and got["t"] == 0.0


# --------------------------------------------------------- 1. the analytic ceiling
def test_ceiling_gap_is_zero_on_a_perfect_partition():
    M = np.full(12, 2.5)
    labels = np.repeat(np.arange(3), 4)
    c = cert_draw.cert_balance_ceiling(M, labels, 3)
    assert math.isclose(c["gap_nats"], 0.0, abs_tol=1e-12), c["gap_nats"]
    assert math.isclose(c["achieved_nash"], 3 * math.log(10.0), abs_tol=1e-12)
    assert c["spread_rel"] == 0.0 and c["max_dev_rel"] == 0.0
    assert c["proved"] is True


def test_ceiling_gap_matches_hand_computation():
    """Four unit zips, 3 against 1: gap = 2 log 2 - log 3 = log(4/3)."""
    M = np.ones(4)
    labels = np.array([0, 0, 0, 1])
    c = cert_draw.cert_balance_ceiling(M, labels, 2)
    assert math.isclose(c["achieved_nash"], math.log(3.0), abs_tol=1e-12)
    assert math.isclose(c["ceiling_nash"], 2 * math.log(2.0), abs_tol=1e-12)
    assert math.isclose(c["gap_nats"], math.log(4.0 / 3.0), abs_tol=1e-12), c["gap_nats"]
    assert math.isclose(c["gap_rel"], 1.0 - 3.0 / 4.0, abs_tol=1e-12)
    assert math.isclose(c["max_dev_rel"], 0.5, abs_tol=1e-12)


def test_ceiling_is_scale_free():
    """Rescaling every M shifts both sides by k log kappa; the gap in nats is untouched."""
    M = np.array([3.0, 1.0, 4.0, 1.0, 5.0, 9.0])
    labels = np.array([0, 0, 1, 1, 2, 2])
    a = cert_draw.cert_balance_ceiling(M, labels, 3)
    b = cert_draw.cert_balance_ceiling(1e6 * M, labels, 3)
    assert math.isclose(a["gap_nats"], b["gap_nats"], rel_tol=1e-12)


def test_ceiling_reports_minus_inf_on_an_empty_district():
    c = cert_draw.cert_balance_ceiling(np.ones(3), np.array([0, 0, 2]), 3)
    assert c["achieved_nash"] == -math.inf and c["gap_nats"] == math.inf
    assert c["empty_districts"] == [1]


# ------------------------------------------- 3. assignment optimality at pinned centers
def test_assignment_at_centers_finds_the_swap():
    """Two points swapped across the clusters: the MILP must undo exactly that swap."""
    xy, M, centers, good = two_clusters()
    bad = good.copy()
    bad[2], bad[3] = 1, 0                              # equal masses still, so slack stays 0
    res = cert_draw.cert_assignment_at_centers(xy, M, bad, centers, time_limit=30.0)
    assert res["proved"] is True, res["status"]
    assert res["improved"] is True
    assert res["rel_gap"] > 0.0
    lab = np.array(res["improving_labels"])
    # the improvement is a valid assignment: balanced within the draw's own slack, and cheaper
    d2 = ((xy[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
    cost = lambda L: float((M * d2[np.arange(M.size), L]).sum())   # noqa: E731
    assert cost(lab) < cost(bad)
    assert math.isclose(cost(lab), res["opt_cost"], rel_tol=1e-12)
    mass = np.bincount(lab, weights=M, minlength=2)
    assert np.abs(mass - M.sum() / 2).max() <= res["slack"] + 1e-9
    assert set(lab[:3].tolist()) == {lab[0]} and set(lab[3:].tolist()) == {lab[3]}
    assert res["n_relabelled"] == 2
    # the band constrains max-deviation, not Nash, so the Nash change is reported, not assumed;
    # here the masses are equal either way, so it is exactly zero
    assert math.isclose(res["nash_delta"], 0.0, abs_tol=1e-12)
    assert math.isclose(res["draw_nash"], res["opt_nash"], abs_tol=1e-12)


def test_assignment_at_centers_confirms_an_optimal_draw():
    xy, M, centers, good = two_clusters()
    res = cert_draw.cert_assignment_at_centers(xy, M, good, centers, time_limit=30.0)
    assert res["proved"] is True, res["status"]
    assert res["improved"] is False
    assert abs(res["rel_gap"]) < 1e-9, res["rel_gap"]
    assert res["improving_labels"] is None
    assert res["slack_is_default"] is True


def test_assignment_slack_can_be_widened():
    """A looser balance window can only lower the optimal cost -- it is a relaxation."""
    xy, M, centers, good = two_clusters()
    tight = cert_draw.cert_assignment_at_centers(xy, M, good, centers, time_limit=30.0)
    loose = cert_draw.cert_assignment_at_centers(xy, M, good, centers, slack=1.0,
                                                 time_limit=30.0)
    assert loose["opt_cost"] <= tight["opt_cost"] + 1e-9
    assert loose["slack_is_default"] is False and loose["slack"] == 1.0


# ------------------------------------------------------------------ honest statuses
def test_no_time_means_no_claim():
    """`time_limit=0` must return a not-proved status, never a number dressed as a proof."""
    M = np.array([5.0, 3.0, 3.0, 2.0, 2.0, 1.5])
    floor = cert_draw.cert_integer_balance_floor(M, 2, time_limit=0.0)
    assert floor["proved"] is False
    assert "not_attempted" in floor["status"]
    assert floor["solver_status"] is None
    # the constructed partition still stands -- it is an upper bound on t*, not a claim about it
    assert floor["t_source"] == "greedy_lpt_polish"
    assert floor["t_rel_lower"] == 0.0
    lab = np.array(floor["labels"])
    mass = np.bincount(lab, weights=M, minlength=2)
    assert math.isclose(float(np.abs(mass - M.sum() / 2).max()), floor["t"], abs_tol=1e-12)

    xy, Mx, centers, good = two_clusters()
    res = cert_draw.cert_assignment_at_centers(xy, Mx, good, centers, time_limit=0.0)
    assert res["proved"] is False and res["opt_cost"] is None
    assert res["improving_labels"] is None
    # what IS known without a solver is still reported, and is not a claim
    assert res["draw_cost"] > 0


def test_proved_is_keyed_on_the_engine_status_only():
    """Trap 15: `proved` follows the solver's own stop reason, whatever we call it."""
    rng = np.random.default_rng(0)
    M = rng.uniform(1.0, 5.0, size=120)
    for tl in (1e-3, 2.0):
        got = cert_draw.cert_integer_balance_floor(M, 5, time_limit=tl)
        assert got["proved"] == (got["solver_status"] == 0), (tl, got["status"])
        if not got["proved"]:
            assert "not_proved" in got["status"]
            # a bound pair is still allowed -- but never labelled optimal
            assert got["t_rel_lower"] is not None


# ------------------------------------------------------------------- merged report
def test_certify_merges_all_four_and_says_what_is_not_proved():
    xy, M, centers, good = two_clusters()
    rep = cert_draw.certify(xy, M, good, centers, 2, time_limit=30.0)
    assert set(rep) >= {"balance_ceiling", "integer_balance_floor",
                        "assignment_at_centers", "power_diagram", "summary", "proved_all"}
    assert isinstance(rep["summary"], list) and len(rep["summary"]) == 5
    assert all(isinstance(line, str) and line for line in rep["summary"])
    blob = " ".join(rep["summary"])
    assert "NOT PROVED" in blob
    assert "heuristic" in blob.lower()          # the centers are never certified
    # this fixture is perfectly balanced and correctly assigned: everything closes
    assert rep["proved_all"] is True
    assert rep["balance_ceiling"]["gap_nats"] < 1e-12
    assert rep["assignment_at_centers"]["improved"] is False


def test_certify_reports_an_improvable_draw_as_such():
    xy, M, centers, good = two_clusters()
    bad = good.copy()
    bad[2], bad[3] = 1, 0
    rep = cert_draw.certify(xy, M, bad, centers, 2, time_limit=30.0)
    assert rep["assignment_at_centers"]["improved"] is True
    assert "NOT optimal" in " ".join(rep["summary"])


# ------------------------------------------ 4. the power-diagram duals, the solver-free bound
def test_power_diagram_confirms_an_optimal_draw():
    """The good draw IS the power diagram of its centers, so nothing sits outside its cell."""
    xy, M, centers, good = two_clusters()
    res = cert_draw.cert_power_diagram(xy, M, good, centers)
    assert res["proved"] is True, res["status"]
    assert res["is_power_diagram"] is True
    assert res["n_outside_cell"] == 0
    assert abs(res["rel_gap"]) < 1e-9, res["rel_gap"]
    assert len(res["weights"]) == 2 and min(res["weights"]) == 0.0   # canonical shift


def test_power_diagram_catches_the_swap_the_milp_catches():
    """Two certificates, one finding: both must call the same swapped draw suboptimal.

    They are computed by different machinery -- a MILP against a max-deviation band, and one
    LP's duals against mass equalities -- so agreement here is a real cross-check, not a
    tautology.  The dual bound is the *stronger* statement about the equal-mass problem and
    the cheaper one to verify; what it adds over the MILP is `n_outside_cell`, which names the
    zips rather than only the gap.
    """
    xy, M, centers, good = two_clusters()
    bad = good.copy()
    bad[2], bad[3] = 1, 0
    power = cert_draw.cert_power_diagram(xy, M, bad, centers)
    milp = cert_draw.cert_assignment_at_centers(xy, M, bad, centers, time_limit=30.0)
    assert power["proved"] is True and power["is_power_diagram"] is False
    assert power["n_outside_cell"] == 2                    # exactly the two swapped points
    assert power["rel_gap"] > 0.0 and milp["improved"] is True
    # the masses are equal either way here, so the band buys the MILP nothing and the two
    # optima coincide -- which is the case where they are directly comparable
    assert math.isclose(power["lp_bound"], milp["opt_cost"], rel_tol=1e-9)


def test_power_bound_is_never_above_the_draw_it_certifies():
    """A lower bound that exceeded the incumbent would be unsound, not merely loose."""
    xy, M, centers, good = two_clusters()
    for lab in (good, np.array([0, 1, 0, 1, 0, 1])):
        res = cert_draw.cert_power_diagram(xy, M, lab, centers)
        assert res["lp_bound"] <= res["draw_cost"] + 1e-9, res


def test_the_default_targets_are_the_draws_own_masses():
    """The default is the draw's own balance, and it has to be, for the gap to be a gap.

    A 4-2 draw is *infeasible* for a 3-3 target, so the bound over 3-3 assignments can exceed
    its cost and `rel_gap` would come out negative -- a number that certifies nothing.  The
    default sidesteps that: at its own masses the draw is feasible by construction, and here it
    is also the nearest-center split, so the gap closes to zero.  Asking at 3-3 explicitly must
    be *refused* as a gap rather than reported as one.
    """
    xy = np.array([[0.0, 0.0], [0.5, 0.3], [-0.4, 0.2], [0.2, -0.5],
                   [10.0, 0.0], [10.5, 0.3]])
    M = np.ones(6)
    centers = np.array([[0.0, 0.0], [10.0, 0.0]])
    lab = np.array([0, 0, 0, 0, 1, 1])

    at_own = cert_draw.cert_power_diagram(xy, M, lab, centers)
    assert at_own["targets_are_draw_masses"] is True
    assert at_own["draw_meets_targets"] is True
    assert at_own["proved"] is True
    assert at_own["targets"] == [4.0, 2.0]
    assert at_own["n_outside_cell"] == 0 and abs(at_own["rel_gap"]) < 1e-9

    at_equal = cert_draw.cert_power_diagram(xy, M, lab, centers, targets=[3.0, 3.0])
    assert at_equal["targets_are_draw_masses"] is False
    assert at_equal["draw_meets_targets"] is False
    assert at_equal["draw_target_max_dev"] == 1.0
    assert at_equal["rel_gap"] is None                 # refused, not reported
    assert at_equal["lp_bound"] > at_equal["draw_cost"]        # the very trap being guarded
    assert "NOT a gap" in at_equal["proves"]


def test_certify_carries_the_power_certificate_and_its_caveat():
    xy, M, centers, good = two_clusters()
    rep = cert_draw.certify(xy, M, good, centers, time_limit=30.0, floor_time_limit=30.0)
    assert "power_diagram" in rep
    assert rep["power_diagram"]["proved"] is True
    line = next(s for s in rep["summary"] if s.startswith("POWER-DIAGRAM"))
    assert "NOT PROVED" in line
    assert any("all four certificates" in s for s in rep["summary"])


# ============================================================ ANCHORED DRAWS  (B9)
# `centers.draw(locked=)` pins some zips to districts.  All four certificates were written for
# the unanchored draw and each is unsound, vacuous or simply answering a different question when
# handed a pinned scenario -- which is what the pin-cost catalogue (`docs/CODE_MAP.md`) is built on.
# Every test below first EXHIBITS the wrong answer the un-anchored call gives, then asserts the
# anchored one.  The oracle throughout is lock-respecting brute force.

def anchored_two_clusters():
    """`two_clusters` with zip 2 -- which sits beside center 0 -- pinned into district 1.

    Geometrically absurd on purpose: that is exactly the situation a pin creates, and exactly
    the one certificates 3 and 4 misread when they are free to move the pinned zip back.
    """
    xy, M, centers, _ = two_clusters()
    locked = np.array([-1, -1, 1, -1, -1, -1])
    labels = np.array([0, 0, 1, 1, 1, 1])
    return xy, M, centers, labels, locked


def locked_partitions(M, k, locked):
    """Every lock-respecting assignment, as district-mass vectors."""
    M = np.asarray(M, float)
    locked = np.asarray(locked, int)
    free = np.flatnonzero(locked < 0)
    base = np.bincount(locked[locked >= 0], weights=M[locked >= 0], minlength=k)
    for lab in itertools.product(range(k), repeat=free.size):
        yield base + np.bincount(np.array(lab, int), weights=M[free], minlength=k)


def brute_locked_max_dev(M, k, locked, targets):
    """min over LOCK-RESPECTING assignments of `max_j |M_j - targets_j|`."""
    targets = np.asarray(targets, float)
    return min(float(np.abs(m - targets).max()) for m in locked_partitions(M, k, locked))


# ---------------------------------------------------- 1. the ceiling, anchored
def test_ceiling_is_vacuous_on_an_anchored_draw_and_the_anchored_one_is_not():
    """The Jensen ceiling stays TRUE under a pin, but stops being reachable -- so quoting it
    charges the draw for a gap no lock-respecting partition could ever have closed."""
    M = np.array([6.0, 6.0, 1.0, 1.0, 1.0, 1.0])       # T = 16, k = 2, equal split 8
    locked = np.array([0, 0, -1, -1, -1, -1])          # both 6s pinned to district 0
    labels = np.array([0, 0, 1, 1, 1, 1])              # masses 12 / 4 -- the anchored optimum

    naive = cert_draw.cert_balance_ceiling(M, labels, 2)
    assert math.isclose(naive["ceiling_nash"], 2 * math.log(8.0), abs_tol=1e-12)
    assert math.isclose(naive["gap_nats"], math.log(4.0 / 3.0), abs_tol=1e-12)
    # ...and yet NO lock-respecting partition gets anywhere near that ceiling
    best = max(float(np.log(m).sum()) for m in locked_partitions(M, 2, locked) if (m > 0).all())
    assert best < naive["ceiling_nash"] - 0.28, (best, naive["ceiling_nash"])
    assert math.isclose(best, float(np.log([12.0, 4.0]).sum()), abs_tol=1e-12)

    anch = cert_draw.cert_balance_ceiling(M, labels, 2, locked=locked)
    assert anch["anchored"] is True
    assert anch["targets"] == [12.0, 4.0]              # the water-fill, district 0 saturated
    assert anch["saturated_districts"] == [0]
    assert math.isclose(anch["ceiling_nash"], math.log(48.0), abs_tol=1e-12)
    assert math.isclose(anch["jensen_ceiling_nash"], 2 * math.log(8.0), abs_tol=1e-12)
    assert math.isclose(anch["gap_nats"], 0.0, abs_tol=1e-12), anch["gap_nats"]
    assert anch["proved"] is True


def test_anchored_ceiling_bounds_every_lock_respecting_partition():
    """The point of a ceiling: nothing feasible may exceed it.  Enumerated, over random pins."""
    rng = np.random.default_rng(11)
    for _ in range(40):
        k = int(rng.integers(2, 4))
        n = int(rng.integers(k + 2, 7))
        M = np.round(rng.uniform(0.5, 9.0, n), 3)
        locked = np.full(n, -1)
        for z in rng.choice(n, size=int(rng.integers(1, n - 1)), replace=False):
            locked[z] = int(rng.integers(0, k))
        labels = np.where(locked >= 0, locked, rng.integers(0, k, n))
        if len(set(labels.tolist())) < k:
            continue
        c = cert_draw.cert_balance_ceiling(M, labels, k, locked=locked)
        for m in locked_partitions(M, k, locked):
            if (m > 0).all():
                assert float(np.log(m).sum()) <= c["ceiling_nash"] + 1e-9, (M, locked, m)
        # and it is never looser than the free Jensen ceiling
        assert c["ceiling_nash"] <= c["jensen_ceiling_nash"] + 1e-12


def test_ceiling_flags_that_no_locks_were_supplied():
    """A caller who forgets `locked` gets the free ceiling; it must at least say so."""
    c = cert_draw.cert_balance_ceiling(np.ones(4), np.array([0, 0, 1, 1]), 2)
    assert c["anchored"] is False and c["locked_supplied"] is False
    assert "locked" in c["does_not_prove"]


# ------------------------------------------------- 2. the integer floor, anchored
def test_integer_floor_understates_the_floor_and_breaks_the_locks():
    """Two separate failures of the un-anchored call on a pinned instance."""
    M = np.array([6.0, 6.0, 1.0, 1.0, 1.0, 1.0, 1.0])   # T = 17, k = 2, equal split 8.5
    locked = np.array([0, 0, -1, -1, -1, -1, -1])
    k, target = 2, 8.5

    naive = cert_draw.cert_integer_balance_floor(M, k, time_limit=30.0)
    truth_vs_equal = brute_locked_max_dev(M, k, locked, np.full(k, target))
    assert math.isclose(truth_vs_equal, 3.5, abs_tol=1e-12)
    # (a) on the SAME yardstick it reports a floor no pinned partition can reach
    assert naive["t"] < truth_vs_equal - 1e-9, (naive["t"], truth_vs_equal)
    # (b) the partition it offers as constructive proof moves a pinned zip
    lab = np.array(naive["labels"])
    assert (lab[locked >= 0] != locked[locked >= 0]).any()

    anch = cert_draw.cert_integer_balance_floor(M, k, time_limit=30.0, locked=locked)
    lab = np.array(anch["labels"])
    assert (lab[locked >= 0] == locked[locked >= 0]).all()      # the locks now hold
    assert anch["targets"] == [12.0, 5.0]
    want = brute_locked_max_dev(M, k, locked, anch["targets"])
    assert math.isclose(anch["t"], want, rel_tol=0, abs_tol=1e-9), (anch["t"], want)
    # the equal-split number is still reported, and it is the honest 3.5, not 0.5
    assert anch["t_vs_equal_split"] >= truth_vs_equal - 1e-9


def test_anchored_floor_matches_lock_respecting_brute_force():
    """Exactness on the three instances where the inherited symmetry breaking is UNSOUND.

    Measured with the breaks left in (see the B9 report): case A's `t* = 0` becomes `t = 4`
    under "heaviest zip into district 0"; case B's `t* = 0.5` doubles under a free-mass
    ordering of districts 1..k-1; case C goes INFEASIBLE under a total-mass ordering.  Each
    fixture has an anchor district that is saturated, which is what destroys the label symmetry
    both breaks assume.
    """
    cases = [
        # (M, k, locked)  -- the locked zip is listed first in each
        (np.array([10.0, 4.0, 1.0, 1.0]), 2, np.array([0, -1, -1, -1])),
        (np.array([8.0, 1.0, 1.0, 1.0, 1.0, 1.0]), 3, np.array([1, 2, -1, -1, -1, -1])),
        (np.array([8.0, 1.0, 1.0, 1.0, 1.0]), 3, np.array([2, -1, -1, -1, -1])),
    ]
    for M, k, locked in cases:
        got = cert_draw.cert_integer_balance_floor(M, k, time_limit=30.0, locked=locked)
        assert got["proved"] is True, (M, got["status"])
        want = brute_locked_max_dev(M, k, locked, got["targets"])
        assert math.isclose(got["t"], want, rel_tol=0, abs_tol=1e-9), (M, got["t"], want)
        lab = np.array(got["labels"])
        assert (lab[locked >= 0] == locked[locked >= 0]).all()
        mass = np.bincount(lab, weights=M, minlength=k)
        assert math.isclose(float(np.abs(mass - np.array(got["targets"])).max()), got["t"],
                            abs_tol=1e-9)


def test_anchored_floor_primal_is_a_real_lock_respecting_partition():
    """At a size no enumeration reaches, the constructive primal must still respect the pins."""
    rng = np.random.default_rng(3)
    M = rng.uniform(0.2, 8.0, size=200)
    k = 6
    locked = np.full(200, -1)
    locked[rng.choice(200, size=40, replace=False)] = rng.integers(0, 3, size=40)
    got = cert_draw.cert_integer_balance_floor(M, k, time_limit=2.0, locked=locked)
    lab = np.array(got["labels"])
    assert (lab[locked >= 0] == locked[locked >= 0]).all()
    mass = np.bincount(lab, weights=M, minlength=k)
    assert math.isclose(float(np.abs(mass - np.array(got["targets"])).max()), got["t"],
                        abs_tol=1e-9)
    assert got["t"] <= got["t_greedy"] + 1e-12
    assert math.isclose(sum(got["targets"]), float(M.sum()), rel_tol=1e-12)


# ------------------------------------ 3. assignment at pinned centers, anchored
def test_assignment_at_centers_relabels_an_anchored_zip():
    """Without a `movable` mask the MILP "improves" the draw by undoing the pin."""
    xy, M, centers, labels, locked = anchored_two_clusters()

    naive = cert_draw.cert_assignment_at_centers(xy, M, labels, centers, time_limit=30.0)
    assert naive["improved"] is True                       # the "improvement" is the pin's undoing
    assert np.array(naive["improving_labels"])[2] != locked[2]

    anch = cert_draw.cert_assignment_at_centers(xy, M, labels, centers, time_limit=30.0,
                                                locked=locked)
    assert anch["proved"] is True, anch["status"]
    assert anch["locked_respected"] is True
    assert anch["improved"] is False, anch["rel_gap"]
    assert abs(anch["rel_gap"]) < 1e-9, anch["rel_gap"]
    assert anch["n_locked"] == 1


def test_anchored_assignment_still_finds_a_real_improvement():
    """The mask must not turn the certificate into a rubber stamp: a free-zip swap is still
    caught, and the returned labels keep the pin."""
    xy, M, centers, _, locked = anchored_two_clusters()
    bad = np.array([1, 0, 1, 1, 1, 0])                     # zips 0 and 5 swapped across clusters
    res = cert_draw.cert_assignment_at_centers(xy, M, bad, centers, time_limit=30.0,
                                               locked=locked)
    assert res["proved"] is True, res["status"]
    assert res["improved"] is True
    lab = np.array(res["improving_labels"])
    assert lab[2] == locked[2]                             # the pin held through the improvement
    assert res["locked_respected"] is True
    d2 = ((xy[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
    assert float((M * d2[np.arange(6), lab]).sum()) < float((M * d2[np.arange(6), bad]).sum())


# ------------------------------------------- 4. the power-diagram duals, anchored
def test_power_diagram_misreads_an_anchored_draw():
    """The pinned zip cannot sit in its own power cell, so the free-cell check condemns a draw
    that is in fact optimal given the pin."""
    xy, M, centers, labels, locked = anchored_two_clusters()

    naive = cert_draw.cert_power_diagram(xy, M, labels, centers)
    assert naive["proved"] is True
    assert naive["is_power_diagram"] is False
    assert naive["rel_gap"] > 0.10, naive["rel_gap"]       # ~16.5% of a gap that is not there
    # and the single zip it condemns is precisely the pinned one, which CANNOT be in its cell
    assert naive["n_outside_cell"] == 1
    cell = centers_mod.power_labels(xy, centers, naive["weights"])
    assert np.flatnonzero(cell != labels).tolist() == [2]

    anch = cert_draw.cert_power_diagram(xy, M, labels, centers, locked=locked)
    assert anch["proved"] is True, anch["status"]
    assert anch["anchored"] is True and anch["n_locked"] == 1
    assert anch["n_outside_cell"] == 0                     # every FREE zip is in its own cell
    assert anch["is_power_diagram"] is True
    assert abs(anch["rel_gap"]) < 1e-9, anch["rel_gap"]
    assert anch["lp_bound"] <= anch["draw_cost"] + 1e-9
    # the bound is the locked cost plus the free subproblem's dual bound, and it is tight here
    assert math.isclose(anch["lp_bound"], anch["locked_cost"] + anch["lp_bound_free"],
                        rel_tol=1e-12)
    assert anch["free_targets"] == [2.0, 3.0]


def test_anchored_power_bound_is_never_above_the_draw():
    """A lower bound above its own incumbent is unsound, not loose -- check it over random pins."""
    rng = np.random.default_rng(5)
    xy = rng.uniform(-5.0, 5.0, size=(24, 2))
    M = rng.uniform(0.5, 4.0, size=24)
    centers = np.array([[-3.0, -3.0], [3.0, -3.0], [0.0, 3.0]])
    for _ in range(6):
        labels = rng.integers(0, 3, size=24)
        if len(set(labels.tolist())) < 3:
            continue
        locked = np.full(24, -1)
        sel = rng.choice(24, size=6, replace=False)
        locked[sel] = labels[sel]                          # a pin must agree with the draw
        res = cert_draw.cert_power_diagram(xy, M, labels, centers, locked=locked)
        assert res["proved"] is True, res["status"]
        assert res["lp_bound"] <= res["draw_cost"] + 1e-9 * abs(res["draw_cost"]), res
        assert res["rel_gap"] >= -1e-9


def test_power_diagram_rejects_a_draw_that_disagrees_with_its_locks():
    xy, M, centers, labels, locked = anchored_two_clusters()
    bad = labels.copy()
    bad[2] = 0                                             # contradicts locked[2] == 1
    for fn, kw in ((cert_draw.cert_power_diagram, {}),
                   (cert_draw.cert_assignment_at_centers, dict(time_limit=0.0))):
        try:
            fn(xy, M, bad, centers, locked=locked, **kw)
        except ValueError:
            continue
        raise AssertionError(f"{fn.__name__} accepted labels that contradict `locked`")


# ------------------------------------------------------ anchoring is opt-in and inert
def test_all_locked_free_reproduces_the_unanchored_certificates():
    """`locked` with no entry >= 0 must reproduce the un-anchored answer exactly."""
    xy, M, centers, good = two_clusters()
    none = np.full(6, -1)

    a = cert_draw.cert_balance_ceiling(M, good, 2)
    b = cert_draw.cert_balance_ceiling(M, good, 2, locked=none)
    for key in ("ceiling_nash", "achieved_nash", "gap_nats", "max_dev", "target"):
        assert a[key] == b[key], key
    assert b["anchored"] is False

    a = cert_draw.cert_integer_balance_floor(M, 2, time_limit=30.0)
    b = cert_draw.cert_integer_balance_floor(M, 2, time_limit=30.0, locked=none)
    assert a["t"] == b["t"] and a["labels"] == b["labels"] and a["t_lpt"] == b["t_lpt"]

    a = cert_draw.cert_assignment_at_centers(xy, M, good, centers, time_limit=30.0)
    b = cert_draw.cert_assignment_at_centers(xy, M, good, centers, time_limit=30.0, locked=none)
    assert a["opt_cost"] == b["opt_cost"] and a["improved"] == b["improved"]

    a = cert_draw.cert_power_diagram(xy, M, good, centers)
    b = cert_draw.cert_power_diagram(xy, M, good, centers, locked=none)
    assert a["lp_bound"] == b["lp_bound"] and a["n_outside_cell"] == b["n_outside_cell"]


def test_residual_targets_is_the_anchored_nash_maximiser():
    """The claim `cert_balance_ceiling` rests on, checked directly against a search.

    `locked + residual_targets` must maximise `sum_j log(locked_j + f_j)` over the free mass.
    The proof is KKT (see the docstring); this is the adversarial half -- nothing feasible may
    beat it, so throw random feasible points and a coordinate descent at it.
    """
    rng = np.random.default_rng(19)
    for _ in range(120):
        k = int(rng.integers(2, 7))
        A = np.zeros(k)
        n_anch = int(rng.integers(1, k + 1))
        A[:n_anch] = rng.uniform(0.0, 6.0, n_anch)     # deliberately often over the equal share
        S = float(rng.uniform(0.1, 8.0))
        total = float(A.sum() + S)
        f = centers_mod.residual_targets(total, A, k)
        assert (f >= -1e-12).all() and math.isclose(f.sum(), S, rel_tol=1e-9, abs_tol=1e-12)
        best = float(np.log(A + f).sum())
        for _ in range(200):                           # random feasible challengers
            g = rng.dirichlet(np.ones(k)) * S
            m = A + g
            if (m > 0).all():
                assert float(np.log(m).sum()) <= best + 1e-9
        for _ in range(200):                           # and local moves off the water-fill
            i, j = rng.integers(0, k, 2)
            if i == j or f[j] <= 0:
                continue
            step = float(rng.uniform(0, f[j]))
            g = f.copy()
            g[i] += step
            g[j] -= step
            m = A + g
            if (m > 0).all():
                assert float(np.log(m).sum()) <= best + 1e-12


def test_certificates_accept_a_real_anchored_draw():
    """End to end: `centers.draw(locked=)` produces the draw, `certify` reports on it.

    The certificates exist to be quoted on draws this pipeline makes, so the wiring is worth a
    test of its own -- targets agreeing between the draw and the certificate is the join that
    would silently rot.
    """
    rng = np.random.default_rng(4)
    xy = rng.uniform(-10.0, 10.0, size=(60, 2))
    M = rng.uniform(1.0, 5.0, size=60)
    k = 4
    locked = np.full(60, -1)
    locked[rng.choice(60, size=9, replace=False)] = rng.integers(0, 2, size=9)
    if len(set(locked[locked >= 0].tolist())) < 2:      # both anchor districts must be used
        locked[np.flatnonzero(locked >= 0)[0]] = 0
        locked[np.flatnonzero(locked >= 0)[-1]] = 1

    res = centers_mod.draw(xy, M, k, seed=1, locked=locked)
    lab = np.asarray(res["labels"], int)
    assert (lab[locked >= 0] == locked[locked >= 0]).all()

    # the floor gets a short leash on purpose: dropping symmetry break 1 makes the anchored tree
    # bigger, and what this test checks is the wiring, not the dual side
    rep = cert_draw.certify(xy, M, lab, res["centers"], k, time_limit=30.0,
                            floor_time_limit=2.0, locked=locked)
    assert rep["anchored"] is True
    # the draw's own targets and the certificate's water-fill are the same object
    assert np.allclose(rep["balance_ceiling"]["targets"], res["targets"], rtol=0, atol=1e-9)
    # the ceiling really is a ceiling for this draw, and the floor really is reachable
    assert rep["balance_ceiling"]["achieved_nash"] <= rep["balance_ceiling"]["ceiling_nash"] + 1e-9
    assert rep["balance_ceiling"]["gap_nats"] >= -1e-12
    floor = rep["integer_balance_floor"]
    assert np.array_equal(np.array(floor["labels"])[locked >= 0], locked[locked >= 0])
    assert floor["t"] <= rep["balance_ceiling"]["max_dev"] + 1e-9   # the draw cannot beat it
    power = rep["power_diagram"]
    assert power["proved"] is True, power["status"]
    assert power["lp_bound"] <= power["draw_cost"] + 1e-6 * abs(power["draw_cost"])
    assert rep["assignment_at_centers"]["locked_respected"] is True


def test_certify_threads_the_locks_and_says_the_draw_is_anchored():
    xy, M, centers, labels, locked = anchored_two_clusters()
    rep = cert_draw.certify(xy, M, labels, centers, 2, time_limit=30.0, locked=locked)
    assert rep["anchored"] is True
    blob = " ".join(rep["summary"])
    assert "ANCHORED" in blob
    assert rep["balance_ceiling"]["anchored"] is True
    assert rep["assignment_at_centers"]["improved"] is False
    assert rep["power_diagram"]["is_power_diagram"] is True
    assert np.array_equal(np.array(rep["integer_balance_floor"]["labels"])[locked >= 0],
                          locked[locked >= 0])
