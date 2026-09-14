"""Independent tests for Group 2 geography repair and acceptance."""
import dataclasses
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from td.solvers import level0
from tools import group2_geography
from tools.group2_run import drop_connectivity_for_diagnostic


def _problem(*, distance: bool = True) -> level0.Level0Problem:
    cells = SimpleNamespace(
        M=np.array([[0.3], [0.3], [0.3], [0.0]]),
        channels=("N_WH",),
        state_list=["A", "B", "C", "D"],
    )
    problem = level0.build_level0(
        cells, {"N": ("N_WH",)}, edges=[(0, 1), (1, 2), (2, 3)],
        L=0.8, U=1.0, eta=0.05, n_max=3,
        dist_max=2.1 if distance else None,
        state_xy=np.array([[0.0, 0.0], [1.0, 0.0], [2.0, 0.0], [3.0, 0.0]])
        if distance else None,
        fixed_used={"N": 1,}, max_used={"N": 1},
    )
    for s in range(3):
        problem = level0.require_cover(problem, s, ["N_WH"])
    return level0.tighten_flow_capacity(problem, 3, "N")


def _witness(problem: level0.Level0Problem) -> group2_geography.CandidateWitness:
    z = np.zeros((problem.n_state, problem.k))
    y = np.zeros_like(z)
    z[:3, 0] = 1.0
    y[:3, 0] = 1.0
    return group2_geography.CandidateWitness(z, y, "toy")


def _policy() -> group2_geography.GeographyPolicy:
    return group2_geography.GeographyPolicy(
        expected_count=1, contact_cap=3, distance_km=2.1,
        distance_overrides_km={}, macro_contact_cap=None)


def test_semantic_and_matrix_checks_accept_a_connected_full_coverage_witness():
    problem = _problem()
    report = group2_geography.validate_candidate(problem, _witness(problem), _policy())
    assert report.accepted, report.issues
    assert report.matrix["accepted"]
    assert report.metrics["required_cover_rows"] == 3
    assert report.districts[0]["units"] == ["A", "B", "C"]


def test_raw_fractionality_is_rejected_before_contact_reconstruction():
    problem = _problem()
    witness = _witness(problem)
    z = witness.z.copy()
    z[0, 0] = 0.51
    report = group2_geography.validate_candidate(
        problem, group2_geography.CandidateWitness(z, witness.y), _policy())
    assert not report.accepted
    assert any("fractional" in issue for issue in report.issues)


def test_candidate_witness_prefers_unrounded_solver_values():
    rounded = np.array([[True], [False]])
    raw = np.array([[0.51], [0.49]])
    witness = group2_geography.CandidateWitness.from_result({
        "z": rounded, "y": rounded.astype(float), "_raw_z": raw, "_raw_y": raw,
    })
    np.testing.assert_array_equal(witness.z, raw)
    np.testing.assert_array_equal(witness.y, raw)


def test_full_bundle_target_requires_each_positive_mass_unit_only():
    cells = SimpleNamespace(M=np.array([[1.0], [0.0]]), channels=("N_WH",),
                            state_list=["A", "B"])
    problem = level0.build_level0(
        cells, {"N": ("N_WH",)}, edges=[(0, 1)], L=0.8, U=1.2,
        eta=0.05, fixed_used={"N": 1}, max_used={"N": 1})
    target = group2_geography.require_full_bundle_coverage(problem)
    cover_lo, _ = target.rows["cover"]
    assert target.lb[cover_lo] == target.cover_ub[0, 0]
    assert np.isneginf(target.lb[cover_lo + 1])


def test_hamming_radius_is_the_true_contact_symmetric_difference():
    problem = _problem()
    reference = _witness(problem)
    changed = group2_geography.CandidateWitness(reference.z.copy(), reference.y.copy())
    changed.z[2, 0] = 0.0
    changed.y[2, 0] = 0.0
    changed.z[3, 0] = 1.0
    changed.y[3, 0] = 1.0
    assert group2_geography.hamming_distance(problem, changed, reference) == 2
    radius_model, constant = group2_geography.hamming_problem(problem, reference, 2)
    lo, hi = radius_model.rows["hamming_radius_N"]
    x = np.zeros(radius_model.n_var)
    x[radius_model.off_z:radius_model.off_z + radius_model.n_state * radius_model.k] = \
        changed.z.ravel()
    assert hi - lo == 1
    row_value = float((radius_model.A[lo] @ x).item())
    assert row_value + constant == 2.0
    assert row_value <= radius_model.ub[lo]


def test_connectivity_boundary_cuts_remove_the_disconnected_incumbent():
    problem = _problem(distance=False)
    witness = _witness(problem)
    witness.z[1, 0] = 0.0
    witness.y[1, 0] = 0.0
    witness.z[3, 0] = 1.0
    witness.y[3, 0] = 1.0
    cut, count = group2_geography.append_connectivity_cuts(problem, witness)
    assert count == 2
    x = np.zeros(cut.n_var)
    x[cut.off_z:cut.off_z + cut.n_state * cut.k] = witness.z.ravel()
    assert any(float((cut.A[lo] @ x).item()) > cut.ub[lo]
               for name, (lo, _hi) in cut.rows.items() if name.startswith("connectivity_cut_"))


def test_parent_purity_checks_every_macro_child():
    problem = _problem()
    witness = _witness(problem)
    policy = dataclasses.replace(_policy(), unit_parent={"A": "P", "B": "P"})
    witness.y[1, 0] = 0.5
    report = group2_geography.validate_candidate(problem, witness, policy)
    assert not report.accepted
    assert any("parent purity" in issue for issue in report.issues)


def test_repair_ladder_stops_at_the_first_independently_accepted_witness():
    problem = _problem()
    reference = _witness(problem)
    outcome = group2_geography.solve_repair_ladder(
        problem, reference,
        lambda candidate: group2_geography.validate_candidate(problem, candidate, _policy()),
        engine="scipy", schedule=((0, 3.0),))
    assert outcome.result is not None
    assert outcome.attempts[0].accepted
    assert outcome.result["passes"][0]["value"] == 0
    np.testing.assert_array_equal(outcome.result["u"], outcome.result["used"])


def test_separator_fallback_adds_cuts_until_the_returned_support_is_connected():
    cells = SimpleNamespace(M=np.array([[0.45], [0.0], [0.45]]), channels=("N_WH",),
                            state_list=["A", "B", "C"])
    target = level0.build_level0(
        cells, {"N": ("N_WH",)}, edges=[(0, 1), (1, 2)], L=0.8, U=1.0,
        eta=0.05, n_max=3, fixed_used={"N": 1}, max_used={"N": 1})
    target = level0.require_cover(target, 0, ["N_WH"])
    target = level0.require_cover(target, 2, ["N_WH"])
    master = drop_connectivity_for_diagnostic(target)
    z = np.array([[1.0], [0.0], [1.0]])
    y = z.copy()
    reference = group2_geography.CandidateWitness(z, y)
    accepted = group2_geography.ValidationReport(True, (), {}, (), {"accepted": True})
    outcome = group2_geography.solve_connectivity_separation(
        target, master, reference, lambda _candidate: accepted,
        engine="scipy", time_limit=6.0, slice_seconds=3.0)
    assert outcome.result is not None
    candidate = group2_geography.CandidateWitness.from_result(outcome.result)
    assert not group2_geography.disconnected_components(target, candidate)
    assert any(attempt.status == "disconnected_incumbent" for attempt in outcome.attempts)


def test_reference_export_preserves_full_precision_and_model_hash():
    with tempfile.TemporaryDirectory() as temporary:
        problem = _problem()
        witness = _witness(problem)
        witness.z[0, 0] = 0.9999999
        path = group2_geography.write_reference(
            Path(temporary) / "reference.json", problem, witness, {"case": "choose"})
        record = json.loads(path.read_text())
        assert record["z"][0][0] == 0.9999999
        assert len(record["model_sha256"]) == 64
        assert len(record["reference_sha256"]) == 64


def test_only_unrestricted_infeasibility_is_a_target_proof():
    restricted = group2_geography.RepairOutcome(
        None, (group2_geography.RepairAttempt(8, 1.0, "infeasible", 0.1),))
    unrestricted = group2_geography.RepairOutcome(
        None, (group2_geography.RepairAttempt(None, 1.0, "infeasible", 0.1),))
    assert not group2_geography.proves_unrestricted_infeasible(restricted)
    assert group2_geography.proves_unrestricted_infeasible(unrestricted)
