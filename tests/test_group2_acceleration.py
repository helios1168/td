"""Safety regressions for Group 2 checkpointing and seeded solves."""
from __future__ import annotations

import dataclasses
import tempfile
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from td.solvers import level0
from td.solvers import milp_engines
from tools import group2_checkpoint, group2_initializer
import tools.group2_run as group2_run
from tools.group2_run import constrain_problem, make_accelerated_runner, planner_args


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

        saved_factory = group2_run.make_accelerated_runner
        group2_run.make_accelerated_runner = fail_factory
        try:
            code = group2_run.main(["--case", "choose", "--hub", str(hub),
                                    "--out", str(root / "out"), "--seed-time-limit", "0"])
            assert code == 1
        finally:
            group2_run.make_accelerated_runner = saved_factory
        assert (full_plan._build, full_plan._pass_list, full_plan._run_passes) == originals
