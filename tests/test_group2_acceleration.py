"""Safety regressions for Group 2 checkpointing and seeded solves."""
from __future__ import annotations

import dataclasses
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from td.solvers import level0
from td.solvers import milp_engines
from td.solvers import state_splits
from tools import group2_checkpoint, group2_geography, group2_initializer
from tools.group2_symmetry import canonicalize_slot_symmetry
import tools.group2_run as group2_run
from tools.group2_run import (constrain_problem, drop_connectivity_for_diagnostic,
                              drop_geography_for_diagnostic, make_accelerated_runner,
                              planner_args)


def _problem():
    cells = SimpleNamespace(M=np.array([[1.0], [1.0]]), channels=("N_WH",),
                            state_list=["TX", "NY"])
    base = level0.build_level0(cells, {"N": ("N_WH",)}, edges=[(0, 1)],
                                L=0.8, U=1.2, eta=0.05, fixed_used={"N": 1})
    return constrain_problem(base, {"N": 1})


def test_checkpoint_rejects_stale_and_malformed_payloads():
    with tempfile.TemporaryDirectory() as temporary:
        tmp_path = Path(temporary)
        problem = _problem()
        solved = level0.solve_passes(problem, [level0.cover_pass(problem, ["N"])],
                                     engine="scipy", time_limit=5.0)
        x = group2_checkpoint.reconstruct_vector(problem, solved)
        level0.check_point(problem, x)
        store = group2_checkpoint.CheckpointStore(tmp_path, {"case": "choose", "counts": {"N": 1}})
        store.save("N", "cover_N", {"passes": [], "x": x}, problem)
        loaded = store.load("N", "cover_N", problem)
        assert loaded is not None
        level0.check_point(problem, np.asarray(loaded["x"], float))

        stale = dataclasses.replace(problem, var_ub=problem.var_ub.copy())
        stale.var_ub[stale.off_u] = 0.0
        assert store.load("N", "cover_N", stale) is None

        path = tmp_path / "N--cover_N.json"
        path.write_text("not json")
        assert store.load("N", "cover_N", problem) is None


def test_initializer_never_mutates_or_returns_an_invalid_point():
    problem = _problem()
    before = (problem.A.copy(), problem.lb.copy(), problem.ub.copy(),
              problem.var_lb.copy(), problem.var_ub.copy())
    result = group2_initializer.build_group2_warm_start(
        problem, [level0.cover_pass(problem, ["N"])], time_limit=2.0)
    assert result.status in {"seed", "no_seed", "disabled"}
    if result.vector is not None:
        assert result.vector.shape == (problem.n_var,)
        level0.check_point(problem, result.vector)
    assert (problem.A != before[0]).nnz == 0
    for actual, expected in zip((problem.lb, problem.ub, problem.var_lb, problem.var_ub), before[1:]):
        assert np.array_equal(actual, expected)


def _feasibility_first_seed_preserves_exact_national_count_and_purity():
    problem = _problem()
    result = group2_initializer.build_group2_feasibility_start(
        problem, [level0.cover_pass(problem, ["N"])], time_limit=2.0, threads=2)
    assert result.status == "seed"
    assert result.vector is not None
    level0.check_point(problem, result.vector)
    used = result.vector[problem.off_u:problem.off_u + problem.k]
    assert int(np.rint(used.sum())) == 1
    assert result.metadata["national_exact_count"] == 1
    assert result.metadata["phase"] in {"greedy_feasible", "national_feasibility", "coverage_fallback"}


def test_feasibility_first_seed_preserves_exact_national_count_and_purity():
    code = ("import tests.test_group2_acceleration as t; "
            "t._feasibility_first_seed_preserves_exact_national_count_and_purity()")
    run = subprocess.run([sys.executable, "-c", code], cwd=Path(__file__).parents[1],
                         text=True, capture_output=True, check=False)
    if run.returncode:
        raise AssertionError(f"fresh feasibility process failed:\n{run.stdout}\n{run.stderr}")


def test_runner_uses_feasibility_first_seed_for_an_exact_national_stage():
    with tempfile.TemporaryDirectory() as temporary:
        problem = _problem()
        solved = level0.solve_passes(problem, [level0.cover_pass(problem, ["N"])],
                                     engine="scipy", time_limit=5.0)
        x = group2_checkpoint.reconstruct_vector(problem, solved)
        seen: list[np.ndarray | None] = []
        calls: list[tuple[object, object]] = []

        def run(problem, passes, args, stage, T, *, warm=None, **kwargs):
            seen.append(warm)
            return {"passes": []}

        def feasibility_start(actual, passes, **kwargs):
            calls.append((actual, passes))
            return SimpleNamespace(status="seed", vector=x,
                                   metadata={"phase": "national_feasibility"})

        def legacy_start(*args, **kwargs):
            raise AssertionError("runner bypassed the feasibility-first initializer")

        saved_feasibility = group2_initializer.build_group2_feasibility_start
        saved_legacy = group2_initializer.build_group2_warm_start
        group2_initializer.build_group2_feasibility_start = feasibility_start
        group2_initializer.build_group2_warm_start = legacy_start
        try:
            passes = [level0.cover_pass(problem, ["N"])]
            wrapped = make_accelerated_runner(
                run, checkpoint_dir=Path(temporary) / "points", resume_dir=None,
                provenance={"case": "choose"}, seed_seconds=1.0)
            wrapped(problem, passes,
                    SimpleNamespace(threads=2), "N", object())
        finally:
            group2_initializer.build_group2_feasibility_start = saved_feasibility
            group2_initializer.build_group2_warm_start = saved_legacy
        assert len(calls) == 1 and calls[0][0] is problem and calls[0][1] is passes
        assert seen == [x]
        assert seen[0] is not None
        level0.check_point(problem, seen[0])


def test_root_symmetry_preserves_exact_count_purity_and_is_idempotent():
    problem = _problem()
    symmetric = canonicalize_slot_symmetry(problem)
    assert "root_min_N" not in problem.rows
    assert "root_min_N" in symmetric.rows
    assert symmetric.A.shape[0] > problem.A.shape[0]
    assert canonicalize_slot_symmetry(symmetric) is symmetric

    passes = [level0.cover_pass(symmetric, ["N"])]
    result = level0.solve_passes(symmetric, passes, engine="scipy", time_limit=5.0)
    x = group2_checkpoint.reconstruct_vector(symmetric, result)
    assert x is not None
    level0.check_point(symmetric, x)
    assert int(np.rint(result["u"].sum())) == 1
    first, last = symmetric.rows["root_min_N"]
    assert np.all(symmetric.A[first:last] @ x <= 1e-7)

    # The symmetry rows only choose an SCF-root representation: the original
    # purity/count problem is unmodified and its projected coverage is retained.
    baseline = level0.solve_passes(problem, [level0.cover_pass(problem, ["N"])],
                                   engine="scipy", time_limit=5.0)
    assert abs(result["passes"][0]["value"] - baseline["passes"][0]["value"]) <= 1e-8


def test_connectivity_diagnostic_retains_business_rows_but_allows_disconnected_contacts():
    cells = SimpleNamespace(M=np.array([[1.0], [1.0]]), channels=("N_WH",),
                            state_list=["A", "B"])
    base = level0.build_level0(cells, {"N": ("N_WH",)}, edges=[], L=1.5, U=2.5,
                               eta=0.05, fixed_used={"N": 1}, max_used={"N": 1})
    problem = constrain_problem(base, {"N": 1})
    reduced = drop_connectivity_for_diagnostic(problem)
    for name in ("cover", "band_lo", "band_hi", "conditional_purity"):
        assert name in reduced.rows
    for name in ("root", "rz", "flow_tail", "flow_head", "net"):
        assert name not in reduced.rows
    result = level0.solve_passes(reduced, [level0.cover_pass(reduced, ["N"])],
                                 engine="scipy", time_limit=5.0)
    assert int(result["z"].sum()) == 2
    assert int(result["u"].sum()) == 1


def test_connectivity_diagnostic_also_removes_root_canonicalization_rows():
    symmetric = canonicalize_slot_symmetry(_problem())
    assert "root_min_N" in symmetric.rows
    reduced = drop_connectivity_for_diagnostic(symmetric)
    assert not any(name.startswith("root_min_") for name in reduced.rows)


def test_geography_diagnostic_removes_only_pair_distance_rows():
    cells = SimpleNamespace(M=np.array([[1.0], [1.0]]), channels=("N_WH",),
                            state_list=["A", "B"])
    base = level0.build_level0(cells, {"N": ("N_WH",)}, edges=[(0, 1)], L=0.5, U=2.5,
                               eta=0.05, fixed_used={"N": 1}, max_used={"N": 1},
                               dist_max=1.0, state_xy=np.array([[0.0, 0.0], [5.0, 0.0]]))
    problem = constrain_problem(base, {"N": 1})
    assert "cap_dist" in problem.rows
    reduced = drop_geography_for_diagnostic(problem)
    assert "cap_dist" not in reduced.rows
    for name in ("root", "net", "band_lo", "band_hi", "conditional_purity"):
        assert name in reduced.rows


def test_accelerated_runner_validates_seed_and_restores_solver_wrapper():
    with tempfile.TemporaryDirectory() as temporary:
        problem = _problem()
        original = object()
        seen = []

        def run(problem, passes, args, stage, T, *, warm=None, warm_seconds=0.0, diagnose=None):
            seen.append(warm)
            return {"passes": []}

        def bad_seed(*args, **kwargs):
            return SimpleNamespace(status="seed", vector=np.full(problem.n_var, np.nan), metadata={})

        saved_seed = group2_initializer.build_group2_warm_start
        group2_initializer.build_group2_warm_start = bad_seed
        try:
            wrapped = make_accelerated_runner(
                run, checkpoint_dir=Path(temporary) / "points", resume_dir=None,
                provenance={"case": "choose"}, seed_seconds=1.0)
            args = SimpleNamespace(engine="highs", threads=2)
            assert wrapped(problem, [], args, "N", original) == {"passes": []}
            assert seen == [None]             # non-finite seed was rejected at the seam
        finally:
            group2_initializer.build_group2_warm_start = saved_seed


def test_group2_default_keeps_legacy_warm_disabled():
    argv = planner_args(Path("/hub"), Path("/out"), "choose", 10.0)
    assert argv[argv.index("--warm") + 1] == "none"


def test_accelerated_runner_restores_engine_hook_when_stage_fails():
    with tempfile.TemporaryDirectory() as temporary:
        original_solve = milp_engines.solve_problem

        def failing(*args, **kwargs):
            raise RuntimeError("stage failure")

        wrapped = make_accelerated_runner(
            failing, checkpoint_dir=Path(temporary) / "points", resume_dir=None,
            provenance={"case": "choose"}, seed_seconds=0.0)
        try:
            wrapped(_problem(), [], SimpleNamespace(threads=2), "N", object())
        except RuntimeError as exc:
            assert str(exc) == "stage failure"
        else:
            raise AssertionError("the original stage failure must propagate")
        assert milp_engines.solve_problem is original_solve


def test_live_incumbent_is_checkpointed_before_a_solver_failure():
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        problem = _problem()
        solved = level0.solve_passes(problem, [level0.cover_pass(problem, ["N"])],
                                     engine="scipy", time_limit=5.0)
        original_solve = milp_engines.solve_problem

        def engine(current, *args, on_incumbent=None, **kwargs):
            assert on_incumbent is not None
            on_incumbent(dict(z=solved["z"], y=solved["y"], objective=-2.0,
                              seconds=0.25, splits=0))
            raise RuntimeError("failure after incumbent")

        def stage(current, passes, args, name, timings, **kwargs):
            return milp_engines.solve_problem(current, "highs", time_limit=5.0)

        milp_engines.solve_problem = engine
        try:
            wrapped = make_accelerated_runner(
                stage, checkpoint_dir=root / "checkpoints", resume_dir=None,
                provenance={"case": "choose"}, seed_seconds=0.0)
            try:
                wrapped(problem, [], SimpleNamespace(threads=2), "N", object())
            except RuntimeError as exc:
                assert str(exc) == "failure after incumbent"
            else:
                raise AssertionError("the solver failure must propagate")
        finally:
            milp_engines.solve_problem = original_solve

        stored = group2_checkpoint.CheckpointStore(
            root / "checkpoints", {"case": "choose"}).load("N", "pass_001_live", problem)
        assert stored is not None
        level0.check_point(problem, stored["x"])
        progress = json.loads((root / "stage_progress.json").read_text())
        assert progress[0]["passes"][0]["live_incumbents"] == 1


def test_restored_seed_is_checkpointed_before_an_immediate_stage_failure():
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        problem = _problem()
        solved = level0.solve_passes(problem, [level0.cover_pass(problem, ["N"])],
                                     engine="scipy", time_limit=5.0)
        x = group2_checkpoint.reconstruct_vector(problem, solved)
        provenance = {"case": "choose"}
        resume = group2_checkpoint.CheckpointStore(root / "resume", provenance)
        resume.save("N", "prior", {"x": x}, problem)

        def failing(*args, **kwargs):
            raise RuntimeError("fails before engine solve")

        points = root / "points"
        wrapped = make_accelerated_runner(
            failing, checkpoint_dir=points, resume_dir=root / "resume",
            provenance=provenance, seed_seconds=0.0)
        try:
            wrapped(problem, [], SimpleNamespace(threads=2), "N", object())
        except RuntimeError as exc:
            assert str(exc) == "fails before engine solve"
        else:
            raise AssertionError("the original stage failure must propagate")
        stored = group2_checkpoint.CheckpointStore(points, provenance).load("N", "seed", problem)
        assert stored is not None
        level0.check_point(problem, stored["x"])
        latest = group2_checkpoint.CheckpointStore(points, provenance).latest("N", problem)
        assert latest is not None
        level0.check_point(problem, latest["x"])


def test_seeded_and_cold_runner_progress_distinguish_warm_start_and_checkpoint():
    """A resumed feasible point is observable, while a cold run stays genuinely cold."""
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        problem = _problem()
        solved = level0.solve_passes(problem, [level0.cover_pass(problem, ["N"])],
                                     engine="scipy", time_limit=5.0)
        x = group2_checkpoint.reconstruct_vector(problem, solved)
        provenance = {"case": "choose"}
        resume = group2_checkpoint.CheckpointStore(root / "resume", provenance)
        resume.save("N", "prior", {"x": x}, problem)
        seen: list[np.ndarray | None] = []

        def run(problem, passes, args, stage, T, *, warm=None, **kwargs):
            seen.append(warm)
            return {"passes": []}

        cold = make_accelerated_runner(
            run, checkpoint_dir=root / "cold" / "checkpoints", resume_dir=None,
            provenance=provenance, seed_seconds=0.0)
        cold(problem, [], SimpleNamespace(threads=2), "N", object())
        cold_progress = json.loads((root / "cold" / "stage_progress.json").read_text())
        assert seen == [None]
        assert cold_progress[0]["seed"] == {}

        seeded = make_accelerated_runner(
            run, checkpoint_dir=root / "seeded" / "checkpoints", resume_dir=root / "resume",
            provenance=provenance, seed_seconds=0.0)
        seeded(problem, [], SimpleNamespace(threads=2), "N", object())
        seeded_progress = json.loads((root / "seeded" / "stage_progress.json").read_text())
        assert seen[1] is not None
        level0.check_point(problem, seen[1])
        seed_meta = seeded_progress[0]["seed"]
        assert seed_meta["source"] == "checkpoint"
        assert seed_meta["validated"] is True
        assert Path(seed_meta["checkpoint"]).name == "N--seed.json"


def test_main_restores_full_plan_wrappers_when_runner_factory_fails():
    """The factory is optional instrumentation, never a lasting global patch."""
    import full_plan

    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        hub = root / "hub"
        hub.mkdir()
        (hub / "instance_descaled_v4_conus.json.gz").write_bytes(b"not read by this test")
        originals = (full_plan._build, full_plan._pass_list, full_plan._run_passes)

        def fail_factory(*args, **kwargs):
            raise RuntimeError("factory failed")

        before_env = dict(os.environ)
        with patch.dict(os.environ, {}, clear=False):
            saved_factory = group2_run.make_accelerated_runner
            saved_prepare = group2_run.prepare_macro_regions
            group2_run.make_accelerated_runner = fail_factory
            group2_run.prepare_macro_regions = lambda *a, **kw: SimpleNamespace(
                data=None, unit_parent={}, graph=None, xy_km={}, record={})
            try:
                code = group2_run.main(["--case", "choose", "--hub", str(hub),
                                        "--out", str(root / "out"), "--seed-time-limit", "0"])
                assert code == 1
            finally:
                group2_run.make_accelerated_runner = saved_factory
                group2_run.prepare_macro_regions = saved_prepare
        assert dict(os.environ) == before_env
        assert (full_plan._build, full_plan._pass_list, full_plan._run_passes) == originals


def test_render_figures_uses_the_full_problem_map_and_summary_scripts():
    with tempfile.TemporaryDirectory() as temporary:
        run_dir = Path(temporary)
        calls = []

        def fake_run(command, **kwargs):
            calls.append((command, kwargs))
            if Path(command[2]).name == "plan_summary.py":
                (run_dir / "maps").mkdir()
                (run_dir / "maps" / "summary.png").write_bytes(b"png")
            return SimpleNamespace(returncode=0)

        with patch.object(group2_run.subprocess, "run", fake_run):
            result = group2_run.render_figures(run_dir, Path("/geo"))

        assert [Path(command[2]).name for command, _ in calls] == [
            "plan_maps.py", "plan_summary.py"]
        assert calls[1][0][-1] == "--no-cache"
        assert result["summary_png"].endswith("maps/summary.png")


def test_repair_runner_exports_and_accepts_a_checked_toy_reference():
    with tempfile.TemporaryDirectory() as temporary:
        _repair_runner_exports_and_accepts_a_checked_toy_reference(Path(temporary))


def _repair_runner_exports_and_accepts_a_checked_toy_reference(tmp_path):
    problem = _problem()
    solved = level0.solve_passes(
        problem, [level0.cover_pass(problem, ["N"])], engine="scipy", time_limit=5.0)
    reference = tmp_path / "relaxed.json"
    reference.write_text(json.dumps({"z": solved["z"].tolist(),
                                     "y": solved["y"].tolist()}))
    policy = group2_geography.GeographyPolicy(expected_count=1, contact_cap=6)
    accepted = []

    def should_not_run(*args, **kwargs):
        raise AssertionError("the ordinary pass runner must be bypassed during repair")

    wrapped = make_accelerated_runner(
        should_not_run, checkpoint_dir=tmp_path / "checkpoints", resume_dir=None,
        provenance={"case": "choose"}, seed_seconds=0.0, repair_from=reference,
        candidate_validator=lambda actual, witness, stage:
            group2_geography.validate_candidate(actual, witness, policy),
        on_accept=lambda *args: accepted.append(args))
    result = wrapped(problem, [], SimpleNamespace(engine="scipy", threads=2),
                     "seq_N", object())

    assert result["passes"][0]["name"] == "hamming_repair"
    assert accepted
    assert (tmp_path / "research" / "seq_N_reference.json").is_file()


def test_repair_runner_preserves_unrestricted_infeasibility_status():
    with tempfile.TemporaryDirectory() as temporary:
        _repair_runner_preserves_unrestricted_infeasibility_status(Path(temporary))


def _repair_runner_preserves_unrestricted_infeasibility_status(tmp_path):
    problem = _problem()
    solved = level0.solve_passes(
        problem, [level0.cover_pass(problem, ["N"])], engine="scipy", time_limit=5.0)
    reference = tmp_path / "relaxed.json"
    reference.write_text(json.dumps({"z": solved["z"].tolist(),
                                     "y": solved["y"].tolist()}))
    outcome = group2_geography.RepairOutcome(
        None, (group2_geography.RepairAttempt(None, 1.0, "infeasible", 0.1),))
    saved = group2_geography.solve_repair_ladder
    group2_geography.solve_repair_ladder = lambda *args, **kwargs: outcome
    try:
        wrapped = make_accelerated_runner(
            lambda *args, **kwargs: {}, checkpoint_dir=tmp_path / "checkpoints",
            resume_dir=None, provenance={"case": "choose"}, seed_seconds=0.0,
            repair_from=reference,
            candidate_validator=lambda actual, witness, stage:
                group2_geography.ValidationReport(True, (), {}, (), {"accepted": True}))
        try:
            wrapped(problem, [], SimpleNamespace(engine="scipy", threads=2),
                    "seq_N", object())
        except state_splits.SolveFailure as exc:
            assert exc.status == 2 and exc.reason == "infeasible"
        else:
            raise AssertionError("unrestricted infeasibility must propagate as a proof")
    finally:
        group2_geography.solve_repair_ladder = saved
