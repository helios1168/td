"""Independent small MILPs for the Group 2 experiment constraints."""
from types import SimpleNamespace
import csv
import tempfile

import networkx as nx
import numpy as np

from td import atoms
from td import channels
from td.instance import Descaled
from td.solvers import level0, state_splits
from tools.group2_run import (GROUP2, _expand_parents, _macro_region_view, constrain_problem,
                              group2_priority, plan_audit, planner_args, realized_audit, valid)
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


def test_macro_children_share_parent_level_purity_and_one_national_contact_cap():
    cells = SimpleNamespace(M=np.ones((2, 1)), channels=("N_WH",),
                            state_list=["CA1", "CA2"])
    problem = level0.build_level0(cells, {"N": ("N_WH",)}, edges=[(0, 1)],
                                  L=0.4, U=1.2, eta=0.05, fixed_used={"N": 2})
    changed = constrain_problem(problem, {"N": 2}, unit_parent={"CA1": "CA", "CA2": "CA"})
    p0, p1 = changed.rows["conditional_purity"]
    witness = np.zeros(problem.n_var)
    first, _ = problem.slots["N"]
    witness[problem.off_z + first] = 1.0
    witness[problem.off_y + first] = 1.0
    # CA1 contacting pure N forces sibling CA2's full N share into pure N too.
    assert (changed.A[p0:p1] @ witness < -0.9).any()

    c0, c1 = changed.rows["macro_national_contact"]
    two_contacts = np.zeros(problem.n_var)
    two_contacts[problem.off_z + first:problem.off_z + first + 2] = 1.0
    assert (changed.A[c0:c1] @ two_contacts > changed.ub[c0:c1] + 0.9).any()

    relaxed = constrain_problem(problem, {"N": 2}, unit_parent={"CA1": "CA", "CA2": "CA"},
                                macro_national_contacts=2)
    r0, r1 = relaxed.rows["macro_national_contact"]
    assert (relaxed.A[r0:r1] @ two_contacts <= relaxed.ub[r0:r1] + 1e-9).all()


def test_macro_contact_cap_must_be_positive():
    try:
        constrain_problem(toy([1.0]), {"N": 1}, macro_national_contacts=0)
    except ValueError as exc:
        assert "macro_national_contacts" in str(exc)
    else:
        raise AssertionError("zero macro contact cap was accepted")


def test_macro_region_view_remaps_only_planning_state_and_records_parent_geometry():
    G = nx.Graph()
    G.add_node("a", state="CA", M=2.0, M_c={"N_WH": 2.0}, S_c={}, S_free_c={})
    G.add_node("b", state="CA", M=1.0, M_c={"N_WH": 1.0}, S_c={}, S_free_c={})
    G.add_node("c", state="NV", M=1.0, M_c={"N_WH": 1.0}, S_c={}, S_free_c={})
    G.add_edges_from([("a", "b"), ("b", "c")])
    d = Descaled(G=G, contested=[], uncontested={}, vacant=[], untapped=[], firm={},
                 meta={"channels": ["N_WH"]}, channels=("N_WH",))
    atom_graph = nx.Graph([("CA1", "CA2"), ("CA2", "NV")])
    built = atoms.Atoms(mass={"CA1": 2.0, "CA2": 1.0, "NV": 1.0}, graph=atom_graph,
                        zips_of={"CA1": ["a"], "CA2": ["b"], "NV": ["c"]},
                        pieces={"CA": ("CA1", "CA2")})
    view = _macro_region_view(
        d, built, {"a": (1000.0, 2000.0), "b": (3000.0, 4000.0), "c": (0.0, 0.0)},
        {"CA": (("CA",), 2)}, seed=2)

    assert d.G.nodes["a"]["state"] == "CA"
    assert view.data.G.nodes["a"]["state"] == "CA1"
    assert view.data.G.nodes["b"]["state"] == "CA2"
    assert view.data.G.nodes["c"]["state"] == "NV"
    assert view.unit_parent == {"CA1": "CA", "CA2": "CA"}
    assert view.record["units"]["CA1"]["centroid_km"] == [1.0, 2.0]
    assert view.record["units"]["CA2"]["adjacent_units"] == ["CA1", "NV"]
    assert len(view.record["partition_sha256"]) == 64


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


def test_macro_planner_arguments_replace_parent_with_children():
    parents = {"CA1": "CA", "CA2": "CA"}
    assert _expand_parents(["CA", "TX"], parents) == ["CA1", "CA2", "TX"]
    cmd = planner_args(Path("/hub"), Path("/out"), "choose", 180, "fixed", True, parents)
    assert "--national-states" not in cmd
    assert "CA" not in cmd[cmd.index("--max-splits") + 1].split(",")
    assert "CA" not in cmd[cmd.index("--band-break") + 1].split(",")


def test_plan_audit_collapses_macro_units_and_detects_sibling_purity_gap():
    parents = {"CA1": "CA", "CA2": "CA"}
    plan = dict(
        slots=[dict(used=True, bundle="N", y={"CA1": 1.0}),
               dict(used=True, bundle="WH_PLUS", y={"CA2": 1.0})],
        per_state={})
    report = plan_audit(plan, "choose", "cap", True, parents)
    assert report["national_states"] == ["CA"]
    assert report["purity_violations"] == [
        dict(state="CA", channel="N", pure_share=0.0, mixed_share=1.0,
             planning_unit="CA2")]

    missing = plan_audit(
        dict(state_list=["CA1", "CA2"],
             slots=[dict(used=True, bundle="N", y={"CA1": 1.0})], per_state={}),
        "choose", "cap", True, parents)
    assert missing["purity_violations"] == [
        dict(state="CA", channel="N", pure_share=0.0, mixed_share=0,
             planning_unit="CA2")]


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
