"""Small, independent checks for the bounded Group 2 warm initializer."""
from types import SimpleNamespace
from pathlib import Path
import subprocess
import sys

import numpy as np

from td.solvers import level0
from tools.group2_initializer import build_group2_warm_start
from tools.group2_run import constrain_problem


def _problem(mass, *, slots=1, prior=None):
    cells = SimpleNamespace(M=np.asarray(mass, float).reshape(-1, 1), channels=("N_WH",),
                            state_list=[f"S{i}" for i in range(len(mass))])
    original = level0.build_level0(cells, {"N": ("N_WH",)},
                                   edges=[(i, i + 1) for i in range(len(mass) - 1)],
                                   L=0.8, U=1.2, eta=0.05, fixed_used={"N": slots}, prior=prior)
    return constrain_problem(original, {"N": slots})


def _seed(problem, seconds=5):
    return build_group2_warm_start(problem, [level0.cover_pass(problem, ["N"])],
                                   time_limit=seconds)


def _fresh(name):
    """Run a live highspy assertion in its own process and thread pool.

    HiGHS sizes highspy's thread pool on its first solve.  The production
    Group 2 command is a fresh process with a fixed thread count, while the
    all-tests process deliberately exercises other counts first.  Do not
    reset that global pool from a unit test.
    """
    code = f"import tests.test_group2_initializer as t; t._{name}()"
    run = subprocess.run([sys.executable, "-c", code], cwd=Path(__file__).parents[1],
                         text=True, capture_output=True, check=False)
    if run.returncode:
        raise AssertionError(f"fresh initializer process failed:\n{run.stdout}\n{run.stderr}")


def _seed_is_a_complete_original_model_point():
    problem = _problem([1.0, 1.0], slots=2)
    seed = _seed(problem)
    assert seed.status == "seed"
    assert seed.vector is not None and seed.vector.shape == (problem.n_var,)
    level0.check_point(problem, seed.vector)


def test_seed_is_a_complete_original_model_point():
    _fresh("seed_is_a_complete_original_model_point")


def _seed_can_split_one_pure_state_across_same_channel_slots():
    problem = _problem([2.0], slots=2)
    seed = _seed(problem)
    assert seed.status == "seed"
    y = seed.vector[problem.off_y:problem.off_y + problem.n_state * problem.k].reshape(problem.n_state, problem.k)
    assert np.isclose(y.sum(), 1.0)
    assert np.count_nonzero(y[0] > 1e-6) == 2


def test_seed_can_split_one_pure_state_across_same_channel_slots():
    _fresh("seed_can_split_one_pure_state_across_same_channel_slots")


def _seed_respects_exact_used_count():
    problem = _problem([1.0, 1.0], slots=1)
    seed = _seed(problem)
    used = seed.vector[problem.off_u:problem.off_u + problem.k]
    assert seed.status == "seed" and np.isclose(used.sum(), 1.0)


def test_seed_respects_exact_used_count():
    _fresh("seed_respects_exact_used_count")


def _invalid_prior_cleanly_returns_no_seed():
    problem = _problem([2.0], slots=1, prior=np.array([[0.5]]))
    seed = _seed(problem)
    assert seed.vector is None and seed.status == "no_seed"


def test_invalid_prior_cleanly_returns_no_seed():
    _fresh("invalid_prior_cleanly_returns_no_seed")


def test_disabled_budget_returns_clean_no_seed():
    seed = _seed(_problem([1.0]), seconds=0)
    assert seed.status == "disabled" and seed.vector is None


def test_invalid_budget_or_thread_count_returns_clean_no_seed():
    problem = _problem([1.0])
    passed = [level0.cover_pass(problem, ["N"])]
    assert build_group2_warm_start(problem, passed, time_limit=-1).metadata["reason"] == "invalid_time_limit"
    assert build_group2_warm_start(problem, passed, threads=0).metadata["reason"] == "invalid_threads"


def _actual_seed_solves_a_miniature_case():
    problem = _problem([1.0, 1.0], slots=1)
    seed = _seed(problem)
    result = level0.solve_passes(problem, [level0.cover_pass(problem, ["N"])],
                                 engine="scipy", time_limit=5, warm_start=seed.warm_start)
    assert result["passes"][-1]["value"] >= 0.8
    assert seed.metadata["status"] == 7 and seed.metadata["auxiliary_optimal"] is True


def test_actual_seed_solves_a_miniature_case():
    _fresh("actual_seed_solves_a_miniature_case")
