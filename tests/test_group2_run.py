"""Independent small MILPs for the Group 2 experiment constraints."""
from types import SimpleNamespace

import numpy as np

from td.solvers import level0, state_splits
from tools.group2_run import constrain_problem, plan_audit, planner_args
from pathlib import Path


def toy(masses, *, fixed=None, prior=None):
    cells = SimpleNamespace(M=np.asarray(masses, float).reshape(-1, 1),
                            channels=("N_WH",), state_list=[f"S{i}" for i in range(len(masses))])
    return level0.build_level0(cells, {"N": ("N_WH",)},
                               edges=[(i, i+1) for i in range(len(masses)-1)],
                               L=0.8, U=1.2, eta=0.05, fixed_used=fixed, prior=prior)


def solve(problem):
    return level0.solve_passes(problem, [level0.cover_pass(problem, ["N"])],
                               engine="scipy", time_limit=10)


def test_purity_rejects_partial_state_that_legacy_can_assign():
    # Neither 0.7 nor 1.4 can fill [0.8, 1.2] using whole states.
    problem = toy([0.7, 0.7], fixed={"N": 1})
    assert abs(solve(problem)["passes"][0]["value"] - 1.2) < 1e-6
    try:
        solve(constrain_problem(problem, {"N": 1}))
    except state_splits.SolveFailure:
        pass
    else:
        raise AssertionError("A partial pure state was accepted")


def test_purity_allows_full_state_split_between_two_districts():
    result = solve(constrain_problem(toy([2.0], fixed={"N": 2}), {"N": 2}))
    assert int(result["u"].sum()) == 2
    assert abs(float(result["y"].sum()) - 1.0) < 1e-6


def test_exact_count_closes_surplus_slots():
    problem = toy([1.0, 1.0], fixed={"N": 1})
    assert int(solve(problem)["u"].sum()) == 2
    result = solve(constrain_problem(problem, {"N": 1}))
    assert int(result["u"].sum()) == 1
    assert abs(result["passes"][0]["value"] - 1.0) < 1e-6


def test_prior_mixed_share_cannot_become_partial_pure():
    problem = toy([2.0], fixed={"N": 1}, prior=np.array([[0.5]]))
    assert abs(solve(problem)["passes"][0]["value"] - 1.0) < 1e-6
    try:
        solve(constrain_problem(problem, {"N": 1}))
    except state_splits.SolveFailure:
        pass
    else:
        raise AssertionError("Prior mixed coverage was ignored")


def test_all_three_pure_bundles_have_contact_implications():
    cells = SimpleNamespace(M=np.ones((1, 4)), channels=("N_WH", "N_FI", "WH", "FI"),
                            state_list=["TX"])
    problem = level0.build_level0(cells, {"N": ("N_WH", "N_FI"), "WH": ("WH",), "FI": ("FI",)},
                                  edges=[], L=0.8, U=1.2, eta=0.05)
    changed = constrain_problem(problem, {})
    start, stop = changed.rows["conditional_purity"]
    for b in ("N", "WH", "FI"):
        first, _ = problem.slots[b]
        witness = np.zeros(problem.n_var)
        witness[problem.off_z + first] = 1
        witness[problem.off_y + first] = 0.5
        assert (changed.A[start:stop] @ witness < -0.4).any()


def test_commands_differ_only_in_forced_national_requirement():
    choose = planner_args(Path("/hub"), Path("/out"), "choose", 180)
    all_states = planner_args(Path("/hub"), Path("/out"), "all", 180)
    assert all_states[:-2] == choose
    assert all_states[-2] == "--force-national"
    assert choose[choose.index("--k-mode")+1] == "fixed"
    assert "--sweep" not in choose


def test_plan_audit_rejects_partial_pure_wh_and_fi():
    slots = [dict(used=True, bundle=b, y={"TX": 0.5}) for b in ("WH", "WH_PLUS", "FI", "FI_PLUS")]
    report = plan_audit(dict(slots=slots, per_state={}), "choose")
    assert {r["channel"] for r in report["purity_violations"]} == {"WH", "FI"}
    assert not report["exact_counts"]


def test_cap_does_not_force_a_district_when_no_whole_state_fits():
    result = solve(constrain_problem(toy([0.7, 0.7]), {"N": 1}, "cap"))
    assert int(result["u"].sum()) == 0


def test_cap_above_available_slots_does_not_increase_slot_count():
    problem = toy([1.0])
    changed = constrain_problem(problem, {"N": 14}, "cap")
    assert changed.k == problem.k
    assert not changed.var_lb[changed.off_u:].any()


def test_cap_command_preserves_same_scenario_parameters():
    exact = planner_args(Path("/hub"), Path("/out"), "all", 180, "fixed")
    ceiling = planner_args(Path("/hub"), Path("/out"), "all", 180, "cap")
    exact[exact.index("--k-mode")+1] = "cap"
    assert exact == ceiling
