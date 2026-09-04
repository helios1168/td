"""
test_eg_band.py -- the band-constrained fibre (td/solvers/eg_band.py, tools/measure/frontier.py,
unit U8-band).

Synthetic only: no instance file, no network, nothing gitignored.  Two tests carry the unit.

`test_oa_bound_never_below_truth` is the safety property the whole architecture rests on: every
tangent is a global overestimator of `log`, so the OA master optimum is a valid upper bound on
`EG^bal(delta)` at *every* iteration, not only at convergence.  If that failed, a stopped loop
would report a number that is not a bound.

`test_utility_convention_matches_gain_matrix` is the unit's silent-failure guard: `frontier`'s
`U` must be `channel.gain_matrix`'s **unmasked** convention.  `model.utilities` is masked (`0`
where not a candidate) and on the real instance lands ~27 nats -- *below* `V` -- so a
wrong-convention run mimics a refutation of P1-band rather than a units error.

The fixture is `docs/MODEL_U7-meas.md` §4's toy (three reps A/B/C, four zips,
`M = [20, 15, 15, 20]`), the same one `tests/test_measure.py` pins the premium ladder on.
"""
from __future__ import annotations

import importlib.util
import math
import os
import sys

import networkx as nx
import numpy as np

from td import channel                                            # noqa: E402
from td.solvers import eg_band                                    # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
THETA, LAM = 0.40, 0.30


def _frontier():
    """tools/ is not a package on the path; load the script the way run_all.py loads tests."""
    path = os.path.join(ROOT, "tools", "measure", "frontier.py")
    spec = importlib.util.spec_from_file_location("measure_frontier", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod                  # @dataclass resolves through sys.modules
    spec.loader.exec_module(mod)
    return mod


frontier = _frontier()


# ------------------------------------------------------------------ fixtures
TOY_BOOKS = {"z1": {"A": 10.0},
             "z2": {"A": 6.0, "B": 4.0},
             "z3": {"B": 8.0, "C": 3.0},
             "z4": {"C": 9.0}}
TOY_M = {"z1": 20.0, "z2": 15.0, "z3": 15.0, "z4": 20.0}
TOY_D = {"z1": "D1", "z2": "D1", "z3": "D2", "z4": "D2"}


def toy():
    """The N-way schema `channel`/`model` read: `cand`, `S`, `M`, `S_free`, `state` on a path."""
    G = nx.Graph()
    zips = sorted(TOY_BOOKS)
    for z in zips:
        G.add_node(z, cand=tuple(sorted(TOY_BOOKS[z])), S=dict(TOY_BOOKS[z]),
                   M=float(TOY_M[z]), S_free=0.0, state="XX")
    nx.add_path(G, zips)
    return G


def toy_U(staff):
    """`U[z, i]` on the toy in the unmasked convention, through the code under test."""
    G = toy()
    nodes = sorted(G)
    U = frontier.utility_matrix(G, nodes, staff, theta=THETA, lam=LAM, filler_capture="theta")
    M = np.array([float(G.nodes[z]["M"]) for z in nodes])
    return U, M


# ------------------------------------------------------------------ the utility convention
def test_utility_convention_matches_gain_matrix():
    """`frontier.utility_matrix` summed over a district IS `channel.gain_matrix`'s `g`."""
    G = toy()
    staff = ("A", "C")
    districts = channel.districts_from(TOY_D)
    U, _ = toy_U(staff)
    nodes = sorted(G)
    jd = {d: j for j, d in enumerate(districts)}
    lab = np.array([jd[TOY_D[z]] for z in nodes], int)

    g, R, D = channel.gain_matrix(G, TOY_D, reps_order=list(staff), districts=districts,
                                  theta=THETA, lam=LAM, filler_capture="theta")
    assert R == list(staff) and D == list(districts)
    for j in range(len(districts)):
        for i in range(len(staff)):
            assert abs(U[lab == j, i].sum() - g[i, j]) < 1e-12


def test_masked_convention_would_be_wrong():
    """The masked utilities differ, and differ downward -- the failure this unit guards against."""
    from td import model
    G = toy()
    staff = ("A", "B", "C")
    U, _ = toy_U(staff)
    masked, R = model.utilities(G, sorted(G), reps_order=list(staff), theta=THETA, lam=LAM)
    masked = masked.T                                   # model returns (rep, zip)
    assert R == list(staff)
    assert (masked <= U + 1e-12).all()                  # masking can only remove utility
    assert (masked == 0.0).any()                        # and it does: A is no candidate at z3/z4
    assert masked.sum() < U.sum()                       # 96.75% of entries differ on the real one


# ------------------------------------------------------------------ the OA bound
def test_oa_bound_never_below_truth():
    """Every master optimum is an upper bound at every iteration; every primal is a lower one."""
    U, M = toy_U(("A", "B", "C"))
    for delta in (0.02, 0.05, 0.20, None):
        ref = eg_band.solve_band(U, M, delta)
        assert ref.converged, ref.status
        for cap in (1, 2, 3, 4, 6, 9):
            sol = eg_band.solve_band(U, M, delta, max_cuts=cap)
            assert sol.upper >= ref.upper - 1e-9, (delta, cap, sol.upper, ref.upper)
            assert sol.primal <= ref.upper + 1e-9, (delta, cap, sol.primal, ref.upper)
            assert sol.n_cuts <= cap


def test_toy_bracket_is_tier_1():
    """The bracket closes to 1e-8 nats on every band width the frontier visits."""
    for staff in (("A", "C"), ("A", "B", "C")):
        U, M = toy_U(staff)
        for delta in (0.0, 0.02, 0.05, 0.10, 0.33, None):
            sol = eg_band.solve_band(U, M, delta)
            assert sol.converged, (staff, delta, sol.status)
            assert sol.bracket <= eg_band.CERT_TOL, (staff, delta, sol.bracket)


def test_toy_against_brute_force():
    """A grid over fractional splits is feasible, hence a lower bound the OA must dominate."""
    U, M = toy_U(("A", "C"))
    # M = [20, 15, 15, 20] and k = 2 put T/k = 35 exactly on a tenths grid, so delta = 0 is
    # representable; a coarser grid would report -inf and prove nothing.
    for delta, steps in ((0.0, 10), (0.05, 10), (0.5, 10)):
        truth = eg_band.brute_force_band(U, M, delta, steps=steps)
        sol = eg_band.solve_band(U, M, delta)
        assert math.isfinite(truth), (delta, "no grid point is band-feasible")
        assert sol.upper >= truth - 1e-9, (delta, sol.upper, truth)
        assert sol.primal >= truth - 1e-9, (delta, sol.primal, truth)


def test_large_delta_relaxes_to_unconstrained_eg():
    """`EG^bal(delta) -> EG_S`: at a wide band no row binds and the multipliers vanish."""
    U, M = toy_U(("A", "B", "C"))
    free = eg_band.solve_band(U, M, None)
    wide = eg_band.solve_band(U, M, 0.9)
    assert abs(wide.upper - free.upper) < 1e-7
    assert wide.slope == 0.0
    assert np.abs(wide.duals.nu).max() == 0.0


def test_slope_is_the_minimised_aggregate():
    """U9 P4.3: report `(T/k) sum |nu_i|`, not the solver's `(T/k) sum (mu+ + mu-)`.

    At `delta > 0` complementary slackness forbids both multipliers of one agent being positive
    at an optimal dual, so the two coincide -- which is what makes the canonical one safe to
    substitute.  At `delta = 0` the raw aggregate is unbounded above and only `sum |nu|` is
    reproducible, so the byte-identical re-run of acceptance 5 depends on this choice.
    """
    U, M = toy_U(("A", "B", "C"))
    for delta in (0.0, 0.02, 0.05, 0.10):
        sol = eg_band.solve_band(U, M, delta)
        scale = float(M.sum()) / U.shape[1]
        assert abs(sol.slope - scale * np.abs(sol.duals.nu).sum()) < 1e-12
        assert sol.slope <= sol.slope_raw + 1e-12
        if delta > 0.0:
            assert abs(sol.slope - sol.slope_raw) < 1e-9, (delta, sol.slope, sol.slope_raw)
        # every supergradient is valid for D1', so the canonical one must still dominate
        for dp in (delta + 0.01, delta + 0.05, 0.9):
            assert sol.curve_bound(dp) >= eg_band.solve_band(U, M, dp).upper - 1e-9


def test_monotone_and_concave_on_the_grid():
    """Free before any solve: the value rises with `delta` and its slope falls."""
    U, M = toy_U(("A", "B", "C"))
    grid = (0.0, 0.01, 0.02, 0.05, 0.10, 0.33)
    vals, slopes = [], []
    for delta in grid:
        sol = eg_band.solve_band(U, M, delta)
        vals.append(sol.upper)
        slopes.append(sol.slope)
    assert all(b >= a - 1e-9 for a, b in zip(vals, vals[1:])), vals
    assert all(b <= a + 1e-9 for a, b in zip(slopes, slopes[1:])), slopes


def test_curve_bound_dominates_the_curve():
    """D1's licence: one solve's value and slope bound `EG^bal` at every other `delta`."""
    U, M = toy_U(("A", "B", "C"))
    base = eg_band.solve_band(U, M, 0.01)
    for delta in (0.0, 0.005, 0.02, 0.05, 0.10, 0.33, 0.9):
        here = eg_band.solve_band(U, M, delta)
        assert base.curve_bound(delta) >= here.upper - 1e-9, (delta, base.curve_bound(delta),
                                                              here.upper)


# ------------------------------------------------------------------ the O(nk) dual certificate
def test_dual_bound_is_a_bound_and_needs_no_solver():
    """Weak duality wants only `mu >= 0` and `q > 0` -- not optimality, not a solver's word.

    `feasible` plus `bound - primal <= CERT_TOL` is the whole certificate, and it is `O(nk)`
    arithmetic: an upper bound in hand, a feasible allocation beside it, tier 1 apart.  The
    reduced-cost residuals are only *how close to KKT* the multipliers are, and they inherit
    the square root of the objective bracket -- a `5e-9` bracket buys prices good to `~1e-4`,
    which is a fact about first-order conditions, not a defect.
    """
    U, M = toy_U(("A", "B", "C"))
    for delta in (0.0, 0.02, 0.05, 0.33):
        sol = eg_band.solve_band(U, M, delta)
        check = eg_band.check_dual(U, M, delta, sol.X, sol.g, sol.duals)
        assert check.feasible, (delta, check)
        assert check.min_price > 0.0 and check.min_mu >= 0.0, (delta, check)
        assert check.bound >= sol.primal - 1e-12, (delta, check.bound, sol.primal)
        assert check.bound - sol.primal <= eg_band.CERT_TOL, (delta, check.bound - sol.primal)
        assert check.dual_violation_rel >= -1e-3, (delta, check.dual_violation_rel)
        assert check.cs_residual_rel <= 1e-3, (delta, check.cs_residual_rel)
        assert check.budget_residual <= 1e-3, (delta, check.budget_residual)


def test_dual_bound_at_zero_mu_is_the_unconstrained_eg_dual():
    """With the band dropped, `D` collapses to `sum_z p_z - k + sum_i log max_z u/p` exactly."""
    U, M = toy_U(("A", "B", "C"))
    sol = eg_band.solve_band(U, M, None)
    p = sol.duals.p
    k = U.shape[1]
    expected = float(p.sum() - k + np.log((U / p[:, None]).max(axis=0)).sum())
    assert abs(eg_band.eg_band_dual_bound(U, M, None, sol.duals) - expected) < 1e-12


def test_negative_multiplier_is_not_a_bound():
    """A dual vector that fails its own feasibility check reports `inf`, never a number."""
    U, M = toy_U(("A", "B", "C"))
    k = U.shape[1]
    bad = eg_band.BandDuals(p=np.ones(U.shape[0]), mu_plus=np.zeros(k),
                            mu_minus=np.full(k, -1.0))
    assert eg_band.eg_band_dual_bound(U, M, 0.05, bad) == math.inf


# ------------------------------------------------------------------ the reporting layer
def test_delta0_is_a_max_deviation_not_a_spread():
    """`MODEL_U8-band.md` §6: the two differ by up to a factor of two, and D1' turns on it."""
    G = toy()
    setting = frontier.build_setting(G, TOY_D, {"D1": "A", "D2": "C"},
                                     theta=THETA, lam=LAM, filler_capture="theta")
    assert setting.k == 2
    assert abs(setting.m_delivered.sum() - setting.T) < 1e-12
    target = setting.T / setting.k
    assert abs(setting.delta0 - float(np.abs(setting.m_delivered - target).max() / target)) < 1e-15
    # this toy draw is exactly balanced, so both read 0; the inequality is the general fact
    assert setting.delta0 <= setting.spread0 + 1e-15


def test_delta0_on_an_unbalanced_draw():
    """A 40/30 split of a 70-unit toy: max deviation 0.1428..., spread 0.2857... -- a factor 2."""
    G = toy()
    skew = {"z1": "D1", "z2": "D1", "z3": "D1", "z4": "D2"}     # M = 50 vs 20
    setting = frontier.build_setting(G, skew, {"D1": "A", "D2": "C"},
                                     theta=THETA, lam=LAM, filler_capture="theta")
    assert abs(setting.delta0 - (50.0 - 35.0) / 35.0) < 1e-12
    assert abs(setting.spread0 - (50.0 - 20.0) / 35.0) < 1e-12
    assert abs(setting.spread0 / setting.delta0 - 2.0) < 1e-12


def test_softness_verdict_is_the_certificate_not_the_solve():
    """D1' reads one solve's `(value, slope)` pair; the floor is the tier-2 5e-3 nats."""
    U, M = toy_U(("A", "B", "C"))
    sol = eg_band.solve_band(U, M, 0.02)
    solved = {d: eg_band.solve_band(U, M, d).upper for d in (0.02, 0.05, 0.10)}
    rows = frontier.softness(sol, V=sol.upper - 1e-4, deltas=(0.02, 0.05, 0.10), solved=solved)
    assert [r.delta for r in rows] == [0.02, 0.05, 0.10]
    assert rows[0].soft and abs(rows[0].bound - sol.upper) < 1e-12
    for r in rows:
        assert abs(r.bound - sol.curve_bound(r.delta)) < 1e-12
        assert r.soft == (r.gap <= frontier.SMALL_NATS)
        # U9 section 10.A's mandatory guard: the tangent must dominate the solved curve
        assert r.tangent_valid, (r.delta, r.slack)
        assert r.slack is not None and r.slack >= -frontier.TANGENT_TOL


def test_shape_reports_violations_rather_than_fixing_them():
    U, M = toy_U(("A", "B", "C"))
    pts = []
    for delta in (0.0, 0.02, 0.05, 0.33):
        pt, _ = frontier.evaluate(frontier.Setting(
            nodes=("z1", "z2", "z3", "z4"), districts=("D1",), staff=("A", "B", "C"),
            U=U, M=M, V=0.0, g_delivered=np.zeros(3), m_delivered=np.zeros(3),
            delta0=0.0, spread0=0.0), delta, cuts=None, scip=False)
        pts.append(pt)
    sh = frontier.shape(pts)
    assert sh.monotone and sh.concave, sh


def test_vertex_report_counts_tight_bands_and_respects_the_split_cap():
    """U9 P3-split: `splits <= k - 1 + t <= 2k - 1`, with the `-1` unconditional."""
    U, M = toy_U(("A", "B", "C"))
    n, k = U.shape
    for delta in (0.02, 0.05, 0.33):
        sol = eg_band.solve_band(U, M, delta)
        lo, hi = eg_band.band_rhs(M, k, delta)
        rep = eg_band.vertex_report(sol.X, U, M, sol.g, lo, hi)
        assert rep.expected == n + k - 1 + rep.n_tight_bands
        assert rep.split_cap == k - 1 + rep.n_tight_bands
        assert rep.n_split <= rep.split_cap <= 2 * k - 1, (delta, rep)
        assert rep.n_agents_band_slack + len(rep.tight_agents) == k
        assert rep.degenerate == (rep.n_support != rep.expected)
        assert rep.rank is not None and rep.rank <= rep.n_support


def test_cleaning_the_vertex_does_not_move_it():
    """§10.B: cleaning at 1e-6 must dissolve dirt, not the solution."""
    U, M = toy_U(("A", "B", "C"))
    for delta in (0.02, 0.05, 0.33):
        sol = eg_band.solve_band(U, M, delta)
        lo, hi = eg_band.band_rhs(M, U.shape[1], delta)
        rep = eg_band.vertex_report(sol.X, U, M, sol.g, lo, hi)
        assert rep.clean_max_g_rel < 1e-9, (delta, rep.clean_max_g_rel)
        assert rep.clean_max_band_violation < 1e-9, (delta, rep.clean_max_band_violation)
        assert rep.n_split <= rep.n_split_raw           # cleaning can only remove splits
        Xc = eg_band.clean_vertex(sol.X)
        assert np.abs(Xc.sum(axis=1) - 1.0).max() < 1e-12


def test_gauge_is_pinned_by_one_slack_agent():
    """U9 P2b: an agent with both bands strictly slack forces `nu_i = 0` and pins `p`, `nu`."""
    U, M = toy_U(("A", "B", "C"))
    lo, hi = eg_band.band_rhs(M, U.shape[1], 0.33)
    sol = eg_band.solve_band(U, M, 0.33)
    rep = eg_band.vertex_report(sol.X, U, M, sol.g, lo, hi)
    assert rep.n_agents_band_slack >= 1 and rep.gauge_pinned
    assert np.abs(sol.duals.nu[list(set(range(U.shape[1])) - set(rep.tight_agents))]).max() == 0.0


def test_good_side_score_maximum_is_the_price():
    """`MODEL_U9-bandthm` P2.5: `max_i (u_i(z)/g_i - nu_i M_z) = p_z`, and `supp(X)` attains it."""
    U, M = toy_U(("A", "B", "C"))
    for delta in (0.02, 0.05, 0.33):
        sol = eg_band.solve_band(U, M, delta)
        score = eg_band.good_side_scores(U, M, sol.g, sol.duals)
        scale = max(float(np.abs(sol.duals.p).max()), 1.0)
        assert np.abs(score.max(axis=1) - sol.duals.p).max() / scale < 1e-3, delta
        z, i = np.nonzero(sol.X > 1e-9)
        assert np.abs(score[z, i] - sol.duals.p[z]).max() / scale < 1e-3, delta


def test_first_movers_rank_by_the_corrected_margin():
    U, M = toy_U(("A", "B", "C"))
    sol = eg_band.solve_band(U, M, 0.05)
    fm = eg_band.first_movers(U, M, sol.g, sol.duals)
    score = eg_band.good_side_scores(U, M, sol.g, sol.duals)
    assert fm.margin.shape == (U.shape[0],)
    assert (fm.margin_abs >= -1e-12).all()
    assert list(fm.margin[fm.order]) == sorted(fm.margin[fm.order])
    for z in range(U.shape[0]):
        assert score[z].argmax() == fm.owner[z]
        assert abs(fm.best[z] - score[z].max()) < 1e-12


def test_published_ratio_rule_is_refuted():
    """§2.12's `argmax_i u_i(z)/q_zi` disagrees with P2.5 -- U9 measured 5/6 and 6/9 on its toys.

    At `nu = 0` the ratio's denominator `p_z` does not depend on `i`, so it degenerates to
    `argmax_i u_i(z)` -- the failure is structural, not a tolerance.
    """
    U, M = toy_U(("A", "B", "C"))
    sol = eg_band.solve_band(U, M, None)                  # nu == 0, the cleanest counterexample
    correct = eg_band.first_movers(U, M, sol.g, sol.duals).owner
    refuted = (U / sol.duals.prices(M)).argmax(axis=1)
    assert (refuted == U.argmax(axis=1)).all()            # the ratio collapses to argmax_i u_i(z)
    assert (correct != refuted).any(), "the toy no longer separates the two rules"


def test_solver_versions_are_recorded():
    """Acceptance 5: no in-repo pattern records solver versions, so this unit adds one."""
    v = frontier.solver_versions()
    assert set(v) >= {"scipy", "numpy", "highspy", "pyscipopt"}
    assert v["scipy"] != "absent" and v["highspy"] != "absent"


# ------------------------------------------------------------------ the cross-check
def test_scip_agrees_with_the_oa_bound():
    """The independent second solver, on the toy.  Only `getDualbound()` is ever read."""
    try:
        import pyscipopt                                          # noqa: F401
    except ImportError:                                           # pragma: no cover
        return
    U, M = toy_U(("A", "B", "C"))
    for delta in (0.02, 0.33):
        oa = eg_band.solve_band(U, M, delta)
        sc = eg_band.solve_scip(U, M, delta, g_lower=oa.g * 0.5, time_limit=120.0)
        assert sc.settings["limits/gap"] == 0.0 and sc.settings["limits/absgap"] == 0.0
        assert sc.settings["misc/allowstrongdualreds"] is False
        assert sc.settings["misc/allowweakdualreds"] is False
        if sc.status != "optimal":                                # trap 15: no bound, not a bound
            assert sc.dual_bound is None
            continue
        assert sc.dual_bound is not None
        assert sc.dual_bound >= oa.primal - 1e-6, (delta, sc.dual_bound, oa.primal)
        assert abs(sc.dual_bound - oa.upper) <= 1e-6, (delta, sc.dual_bound, oa.upper)
