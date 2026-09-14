"""Independent small MILPs for the Group 2 experiment constraints."""
from types import SimpleNamespace
import csv
import tempfile

import numpy as np

from td.solvers import level0, state_splits
from tools.group2_run import GROUP2, constrain_problem, group2_priority, plan_audit, planner_args, realized_audit, valid
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


def test_supporting_states_allowed_without_weakening_forcing():
    cmd = planner_args(Path("/hub"), Path("/out"), "all", 180, "fixed", True)
    assert "--national-states" not in cmd
    assert "--force-national" in cmd


def test_group_priority_can_choose_smaller_group_state_over_larger_support_state():
    cells = SimpleNamespace(M=np.array([[0.9], [1.1]]), channels=("N_WH",), state_list=["TX", "ID"])
    problem = level0.build_level0(cells, {"N": ("N_WH",)}, edges=[(0, 1)],
                                  L=0.8, U=1.2, eta=0.05, fixed_used={"N": 1})
    problem = constrain_problem(problem, {"N": 1})
    result = level0.solve_passes(problem, [group2_priority(problem), level0.cover_pass(problem, ["N"])],
                                 engine="scipy", time_limit=10)
    assert abs(float(result["y"][0].sum())-1) < 1e-6
    assert abs(float(result["y"][1].sum())) < 1e-6


def test_colorado_is_supporting_only_without_geographic_or_band_exception():
    assert len(GROUP2) == 19 and "CO" not in GROUP2
    cmd = planner_args(Path("/hub"), Path("/out"), "choose", 180, "fixed", True)
    assert "--national-states" not in cmd and "--force-national" not in cmd
    assert cmd[cmd.index("--dist-max-state")+1] == "WA=1200"
    assert cmd[cmd.index("--dist-max")+1] == "900"
    assert cmd[cmd.index("--delta")+1] == "0.1"
    forced = planner_args(Path("/hub"), Path("/out"), "all", 180, "fixed", True)
    assert "CO" not in forced[forced.index("--force-national")+1].split(",")
    cells = SimpleNamespace(M=np.array([[0.9], [1.1]]), channels=("N_WH",), state_list=["TX", "CO"])
    problem = level0.build_level0(cells, {"N": ("N_WH",)}, edges=[(0, 1)],
                                  L=0.8, U=1.2, eta=0.05, fixed_used={"N": 1})
    priority = group2_priority(problem)
    assert priority.c[problem.off_y] != 0
    assert priority.c[problem.off_y + problem.k] == 0
    assert level0.cover_pass(problem, ["N"]).c[problem.off_y + problem.k] != 0
    report = plan_audit(dict(slots=[dict(used=True, bundle="N", y={"CO": 1.0})],
                             per_state={}), "choose", "cap", True)
    assert report["supporting_national_states"] == ["CO"]
    assert not report["outside_group2"] and not report["purity_violations"]


def write_assignment(path, rows):
    with path.open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["state", "channel", "district", "bundle", "M_cell"])
        writer.writerows(rows)


def test_realized_audit_rejects_pure_national_with_mixed_or_unheld_remainder():
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / "assignment.csv"
        for district, bundle in (("plus", "FI_PLUS"), ("", ""), ("other", "")):
            write_assignment(path, [["TX", "N_WH", "n", "N", 5],
                                    ["TX", "N_FI", district, bundle, 5]])
            audit = realized_audit(path, "choose", "cap", True)
            assert not valid(audit)
            assert audit["purity_violations"] == [dict(state="TX", channel="N", mass_outside_pure=5.0)]
            assert audit["residual_mass"] == (0.0 if district == "plus" else 5.0)
            assert audit["coverage_complete"] == (district == "plus")


def test_realized_purity_allows_two_pure_districts_and_supporting_states():
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / "assignment.csv"
        write_assignment(path, [["ID", "N_WH", "n1", "N", 5],
                                ["ID", "N_FI", "n2", "N", 5]])
        audit = realized_audit(path, "choose", "cap", True)
        assert valid(audit)
        assert audit["counts"]["N"] == 2
        assert audit["supporting_national_states"] == ["ID"]
        assert not valid(realized_audit(path, "choose", "cap", False))


def test_realized_no_pure_national_allows_national_split_into_plus_bundles():
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / "assignment.csv"
        write_assignment(path, [["ID", "N_WH", "w", "WH_PLUS", 5],
                                ["ID", "N_FI", "f", "FI_PLUS", 5],
                                ["ID", "WH", "w", "WH_PLUS", 2],
                                ["ID", "FI", "f", "FI_PLUS", 3]])
        assert valid(realized_audit(path, "choose", "cap", True))
