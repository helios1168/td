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
