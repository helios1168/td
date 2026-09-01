"""
test_centers.py -- stage 1: center-based balanced districting (td/solvers/centers.py).

The load-bearing test is `test_balance_beats_geometry`: the mass equalities are hard, so a
draw must split a heavy cluster rather than hand it a district and a half.  That is the whole
point of the capacitated formulation -- plain k-means would keep the cluster whole and miss
the target by 100%.

Fixtures are synthetic and small (<= 200 points, k <= 3); no instance file, no network.
"""
from __future__ import annotations

import math

import numpy as np

from td import channel                                  # noqa: E402
from td.solvers import centers                          # noqa: E402


def three_clusters(seed=0, per=50, sigma=0.5):
    """Three well-separated Gaussian blobs of `per` points, equal total mass per blob."""
    rng = np.random.default_rng(seed)
    mids = np.array([[0.0, 0.0], [10.0, 0.0], [5.0, 8.0]])
    xy = np.vstack([m + sigma * rng.normal(size=(per, 2)) for m in mids])
    M = np.full(3 * per, 1.0)
    truth = np.repeat(np.arange(3), per)
    return xy, M, truth


def heavy_cluster(seed=1, sigma=0.5):
    """One cluster carrying 2/3 of the mass plus two light ones: k=3 must cut the heavy one."""
    rng = np.random.default_rng(seed)
    heavy = np.array([0.0, 0.0]) + sigma * rng.normal(size=(100, 2))
    light1 = np.array([12.0, 0.0]) + sigma * rng.normal(size=(50, 2))
    light2 = np.array([6.0, 10.0]) + sigma * rng.normal(size=(50, 2))
    xy = np.vstack([heavy, light1, light2])
    M = np.concatenate([np.full(100, 2.0), np.full(50, 1.0), np.full(50, 1.0)])
    return xy, M                                        # total 300, target 100 per district


# ----------------------------------------------------------------- geometry recovery
def test_draw_recovers_separated_clusters():
    """Equal-mass blobs, k=3: each district is one blob, and the split is exact."""
    xy, M, truth = three_clusters()
    res = centers.draw(xy, M, 3, seed=0)
    labels = res["labels"]
    got = {int(t): np.bincount(labels[truth == t], minlength=3).argmax() for t in range(3)}
    assert len(set(got.values())) == 3, got            # a bijection blob -> district
    for t, d in got.items():
        share = (labels[truth == t] == d).mean()
        assert share > 0.9, (t, d, share)              # the blob's majority stays together
    assert res["spread_rel"] < 0.05, res["masses"]


def test_metrics_compactness_is_the_within_district_moment():
    xy, M, _ = three_clusters()
    res = centers.draw(xy, M, 3, seed=0)
    m = centers.metrics(M, res["labels"], xy)
    assert m["compactness"] > 0
    assert math.isclose(sum(m["compactness_per_district"]), m["compactness"], abs_tol=1e-9)
    # three tight blobs: the draw's moment is the blobs' own spread, an order of magnitude
    # below an equally *balanced* but scattered partition (round-robin across the blobs)
    scattered = centers.metrics(M, np.arange(M.size) % 3, xy)
    assert m["compactness"] < 0.1 * scattered["compactness"]


# --------------------------------------------------------------- balance is the objective
def test_balance_beats_geometry():
    """A cluster holding 2/3 of the mass gets cut: balance is the objective, not compactness."""
    xy, M = heavy_cluster()
    res = centers.draw(xy, M, 3, seed=0)
    mass = np.array(res["masses"])
    assert np.abs(mass - 100.0).max() / 100.0 < 0.05, mass
    heavy_labels = set(res["labels"][:100].tolist())
    assert len(heavy_labels) >= 2, "the heavy cluster must be split across districts"


def test_assign_alone_is_balanced_before_rounding():
    """Fixed centers, one LP: at most k-1 fractional zips and the masses land on target."""
    xy, M = heavy_cluster()
    c = centers.seed_centers(xy, M, 3, 0)
    labels, n_frac = centers.assign(xy, M, c)
    assert n_frac <= 3, n_frac
    m = centers.metrics(M, labels)
    assert m["max_dev_rel"] < 0.05, m["masses"]


def test_assign_integrality_on_clusters():
    xy, M, _ = three_clusters()
    c = centers.seed_centers(xy, M, 3, 7)
    labels, n_frac = centers.assign(xy, M, c)
    assert n_frac <= 3, n_frac
    assert set(labels.tolist()) == {0, 1, 2}


def test_improve_only_helps_the_nash_objective():
    xy, M = heavy_cluster()
    rng = np.random.default_rng(3)
    labels = rng.integers(0, 3, size=xy.shape[0])       # a deliberately bad start
    before = centers.metrics(M, labels)["nash"]
    after = centers.metrics(M, centers.improve(xy, M, labels))["nash"]
    assert after >= before - 1e-12


# --------------------------------------------------------------------- determinism
def test_same_seed_same_labels():
    xy, M, _ = three_clusters()
    a = centers.draw(xy, M, 3, seed=11)
    b = centers.draw(xy, M, 3, seed=11)
    assert np.array_equal(a["labels"], b["labels"])
    assert math.isclose(a["nash"], b["nash"], rel_tol=0, abs_tol=1e-12)


def test_seed_centers_is_deterministic_and_seed_dependent():
    xy, M, _ = three_clusters()
    assert np.array_equal(centers.seed_centers(xy, M, 3, 5),
                          centers.seed_centers(xy, M, 3, 5))
    got = {centers.seed_centers(xy, M, 3, s).tobytes() for s in range(8)}
    assert len(got) > 1, "different seeds must be able to give different seedings"


# ------------------------------------------------------------------ metrics sanity
def test_nash_of_a_perfect_partition_is_k_log_total_over_k():
    k, per = 4, 10
    M = np.full(k * per, 2.5)
    labels = np.repeat(np.arange(k), per)
    m = centers.metrics(M, labels)
    want = k * math.log(M.sum() / k)
    assert math.isclose(m["nash"], want, rel_tol=0, abs_tol=1e-9), (m["nash"], want)
    assert m["spread_rel"] == 0.0 and m["max_dev_rel"] == 0.0
    assert m["sizes"] == [per] * k


def test_metrics_reports_minus_inf_on_an_empty_district():
    M = np.array([1.0, 1.0, 1.0])
    m = centers.metrics(M, np.array([0, 0, 2]))         # district 1 empty
    assert m["nash"] == -math.inf and m["k"] == 3


# --------------------------------------------------------------- stage-2 handoff
def test_to_district_round_trip():
    xy, M, _ = three_clusters(per=20)
    res = centers.draw(xy, M, 3, seed=0)
    zips = [f"z{i:04d}" for i in range(xy.shape[0])]
    td = centers.to_district(zips, res["labels"])
    assert len(td) == len(zips)
    assert all(isinstance(d, int) for d in td.values())
    assert [td[z] for z in zips] == res["labels"].tolist()
    # and it is exactly what stage 2 consumes (districts_from orders by first appearance
    # over sorted zips, so it is a permutation of the labels, not their sort)
    assert sorted(channel.districts_from(td)) == sorted(set(res["labels"].tolist()))


def test_to_district_rejects_a_length_mismatch():
    try:
        centers.to_district(["a", "b"], np.array([0, 1, 0]))
    except ValueError as e:
        assert "labels" in str(e)
    else:
        raise AssertionError("expected ValueError on a zip/label length mismatch")


# ------------------------------------------------------------------------ portfolio
def test_portfolio_is_sorted_by_nash():
    xy, M, _ = three_clusters(per=20)
    seeds = [0, 1, 2, 3]
    ranked = centers.portfolio(xy, M, 3, seeds)
    assert len(ranked) == len(seeds)
    vals = [r["nash"] for r in ranked]
    assert vals == sorted(vals, reverse=True), vals
    assert {r["seed"] for r in ranked} == set(seeds)


def test_seed_centers_rejects_k_above_n():
    try:
        centers.seed_centers(np.zeros((2, 2)), np.ones(2), 3, 0)
    except ValueError as e:
        assert "k" in str(e)
    else:
        raise AssertionError("expected ValueError for k > n")


# ----------------------------------------------- the duals, and the power diagram they draw
def test_power_labels_at_zero_weight_is_the_voronoi_diagram():
    """The weights are the whole difference: drop them and the cells are nearest-center."""
    C = np.array([[0.0, 0.0], [10.0, 0.0], [5.0, 8.0]])
    pts = np.array([[1.0, 1.0], [9.0, 1.0], [5.0, 7.0], [4.9, 3.0], [5.1, 3.0]])
    near = ((pts[:, None, :] - C[None, :, :]) ** 2).sum(axis=2).argmin(axis=1)
    assert np.array_equal(centers.power_labels(pts, C, np.zeros(3)), near)


def test_a_larger_weight_takes_ground_from_its_neighbour():
    """`w_j` enlarges cell `j`, and only a common shift is a no-op."""
    C = np.array([[0.0, 0.0], [10.0, 0.0]])
    pts = np.array([[4.0, 0.0], [6.0, 0.0]])
    assert np.array_equal(centers.power_labels(pts, C, [0.0, 0.0]), [0, 1])
    assert np.array_equal(centers.power_labels(pts, C, [50.0, 0.0]), [0, 0])   # 0 reaches over
    assert np.array_equal(centers.power_labels(pts, C, [7.0, 7.0]), [0, 1])    # shift-invariant


def test_power_weights_returns_a_feasible_dual_vector():
    """The bound is only a bound if `alpha_z + M_z beta_j <= M_z d^2(z, c_j)` really holds.

    This is the property the whole certificate rests on, and the one that silently fails if the
    LP is posed with an explicit upper bound of 1: HiGHS then parks a reduced cost on the bound
    and the returned duals violate the constraint by an arbitrary amount.
    """
    xy, M, _ = three_clusters(per=30)
    C = centers.seed_centers(xy, M, 3, 0)
    res = centers.power_weights(xy, M, C)
    assert abs(res["max_dual_violation_rel"]) < 1e-9, res["max_dual_violation"]
    assert res["max_cs_residual_rel"] < 1e-9, res["max_cs_residual"]
    assert res["n_fractional"] <= 3 - 1                       # at most k-1 at a basic solution


def test_power_cells_reproduce_the_lp_assignment():
    """Complementary slackness, checked as a labelling: the cells *are* the LP's own answer.

    Only the split zips may differ -- a fractional variable has no single cell to be in -- so
    the disagreement is bounded by `n_fractional`, not asserted to be zero.
    """
    xy, M, _ = three_clusters(per=40)
    C = centers.seed_centers(xy, M, 3, 1)
    res = centers.power_weights(xy, M, C)
    disagree = int((res["labels"] != res["lp_labels"]).sum())
    assert disagree <= res["n_fractional"], (disagree, res["n_fractional"])


def test_lp_bound_is_below_every_integer_assignment():
    """The dual objective bounds the cost of any assignment meeting the targets, from below."""
    rng = np.random.default_rng(3)
    xy, M, _ = three_clusters(per=25)
    C = centers.seed_centers(xy, M, 3, 2)
    res = centers.power_weights(xy, M, C)
    d2 = centers._dist2(xy, C)
    n, target = xy.shape[0], M.sum() / 3
    for _ in range(40):                       # random balanced-ish labellings, none may beat it
        lab = rng.permutation(np.arange(n) % 3)
        mass = np.bincount(lab, weights=M, minlength=3)
        if np.abs(mass - target).max() > 1e-9:
            continue                          # only feasible ones are bounded by the dual
        assert float((M * d2[np.arange(n), lab]).sum()) >= res["lp_bound"] - 1e-6


def test_a_balanced_draw_on_equal_blobs_is_its_own_power_diagram():
    """Three equal blobs, k=3: the draw is compactness-optimal, so no zip leaves its cell."""
    xy, M, truth = three_clusters(per=40)
    res = centers.draw(xy, M, 3, seed=0)
    pw = centers.power_weights(xy, M, res["centers"])
    assert int((pw["labels"] != res["labels"]).sum()) == 0


def test_power_weights_rejects_a_zero_mass_zip():
    """The dual argument divides by `M_z`; a zero would make the power weights meaningless."""
    xy = np.array([[0.0, 0.0], [1.0, 0.0], [2.0, 0.0], [3.0, 0.0]])
    try:
        centers.power_weights(xy, np.array([1.0, 0.0, 1.0, 1.0]), xy[:2])
    except ValueError as e:
        assert "M" in str(e)
    else:
        raise AssertionError("expected ValueError for a zero-mass zip")
