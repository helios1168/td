"""test_milp_engines.py -- td/solvers/milp_engines.py: the highs/scip/cpsat engines, the
root-fix, cutoff and heuristic pure functions, and the out-of-process worker round trip.

Reuses the toy fixtures `tests/test_state_splits.py` already builds (`EDGES`, `EVEN`, `ODD`,
`COMB`, `build`) rather than rebuilding them: the same six-state path graph, decidable by hand.
Every test here runs in `.venv` (`highspy` and `pyscipopt` are installed there); only the CP-SAT
round trip needs `.venv-opt`, and returns early when it has not been built.
"""
from __future__ import annotations

import numpy as np

from td.solvers import milp_engines as me
from td.solvers import state_splits as ss
from tests.test_state_splits import COMB, EDGES, EVEN, ODD, build


def test_exact_engines_match_scipys_split_count():
    for masses, delta in ((EVEN, 0.001), (ODD, 0.005), (COMB, 0.03)):
        _, prob = build(masses, delta)
        base = ss.solve(prob)
        for engine in ("highs", "scip"):
            res = me.solve_problem(prob, engine, time_limit=30.0)
            assert res["splits"] == base["splits"], (engine, masses, res["z"])
            assert res["status"] == 0
            assert res["engine"] == engine
            assert res["mip_gap"] <= 1e-9
            for j in range(prob.k):
                assert ss.connected(res["z"][:, j], EDGES)


def test_fix_roots_leaves_the_split_count_unchanged():
    _, prob = build(EVEN, 0.001)
    base = ss.solve(prob)
    fixed = me.fix_roots(prob, anchors=[(0, 0), (3, 1)])
    res = ss.solve(fixed)
    assert res["splits"] == base["splits"]

    at = fixed.off_r + 0 * fixed.k + 0
    assert fixed.var_lb[at] == 1.0 and fixed.var_ub[at] == 1.0
    for s in range(1, fixed.n_state):
        assert fixed.var_ub[fixed.off_r + s * fixed.k + 0] == 0.0
    # a copy: the original problem's r-block bounds are untouched
    assert prob.var_ub[prob.off_r + 1 * prob.k + 0] == 1.0


def test_with_cutoff_certifies_optimality_and_admits_the_optimum():
    """`with_cutoff(problem, s_star)` appends `sum z <= n_state + s_star - 1`, i.e. restricts
    to `splits <= s_star - 1` (the plan's own row).  Called with the true optimum `s*` that
    asks "does a map beating s* exist" and must be infeasible -- that infeasibility is the
    certificate the `*-cutoff` bench variant reports.  Called with `s* + 1` it asks "does a map
    at least as good as s*", which the known optimum itself satisfies."""
    _, prob = build(COMB, 0.10)
    s_star = ss.solve(prob)["splits"]

    tight = me.with_cutoff(prob, s_star)
    try:
        me.solve_problem(tight, "highs", time_limit=30.0)
    except ss.SolveFailure as exc:
        assert exc.reason == "infeasible"
    else:
        raise AssertionError(f"a map with fewer than {s_star} splits should not exist")

    loose = me.with_cutoff(prob, s_star + 1)
    res = me.solve_problem(loose, "highs", time_limit=30.0)
    assert res["status"] == 0
    assert res["splits"] <= s_star


def test_lp_heuristic_returns_a_feasible_upper_bound():
    _, prob = build(COMB, 0.10)
    s_star = ss.solve(prob)["splits"]
    out = me.lp_heuristic(prob)
    assert set(out) == {"z", "y", "splits", "seconds"}
    assert out["splits"] >= s_star
    for j in range(prob.k):
        assert ss.connected(out["z"][:, j], EDGES)
    for s in range(prob.n_state):
        assert out["z"][s].any()                        # every state touches a district
    assert np.allclose(out["y"].sum(axis=1), 1.0)
    assert out["seconds"] < 10.0


def test_the_cpsat_worker_round_trips():
    """The full out-of-process seam: `.npz` out, `milp_worker.py` under `.venv-opt`, JSON back.
    Returns early with no assertion when `.venv-opt` has not been built yet (see
    `tools/bench/README.md`); `config.OPT_PYTHON` (`app/config.py`) is the same path."""
    if not me.OPT_PYTHON.exists():
        print(f"SKIP: .venv-opt not built at {me.OPT_PYTHON}; see tools/bench/README.md")
        return
    _, prob = build(ODD, 0.005)
    base = ss.solve(prob)
    res = me.solve_problem(prob, "cpsat", time_limit=30.0)
    assert res["engine"] == "cpsat"
    assert res["status"] in (0, "time_limit")
    assert res["splits"] >= base["splits"]          # discretised: an upper bound, never better
    for j in range(prob.k):
        assert ss.connected(res["z"][:, j], EDGES)
