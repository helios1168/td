"""Small-model checks for Group 2 warm-start checkpoints."""
from pathlib import Path
import json
import subprocess
import sys
import tempfile

import numpy as np

from td.solvers import level0
from tools.group2_checkpoint import CheckpointStore, model_fingerprint, reconstruct_vector
from tools.group2_run import constrain_problem


def toy():
    class Cells:
        M = np.array([[0.5], [0.5], [1.0]])
        channels = ("N_WH",)
        state_list = ("AA", "BB", "CC")
    return level0.build_level0(Cells(), {"N": ("N_WH",)}, edges=[(0, 1), (1, 2)],
                               L=0.8, U=1.2, eta=0.05, fixed_used={"N": 2})


def result(problem):
    solved = level0.solve_passes(problem, [level0.cover_pass(problem, ["N"])],
                                 engine="scipy", time_limit=5)
    return dict(z=solved["z"], y=solved["y"], status="time_limit", certified=True)


def test_reconstructed_result_is_a_full_model_feasible_vector():
    problem = toy()
    x = reconstruct_vector(problem, result(problem))
    level0.check_point(problem, x)
    assert x.shape == (problem.n_var,)
    assert x[problem.off_f:problem.off_u].sum() > 0


def test_round_trip_is_json_atomic_and_never_copies_certification():
    problem = toy()
    with tempfile.TemporaryDirectory() as temp:
        store = CheckpointStore(Path(temp), {"instance": "toy", "source": "v1"})
        path = store.save("national", "cover_N", result(problem), problem)
        raw = json.loads(path.read_text())
        assert raw["schema"] == 1 and "certified" not in raw["metadata"]
        loaded = store.load("national", "cover_N", problem)
        assert loaded is not None and "certified" not in loaded["metadata"]
        level0.check_point(problem, loaded["x"])
        assert not list(Path(temp).glob(".*.tmp"))


def test_fingerprint_rejects_changed_provenance_or_model():
    problem = toy()
    with tempfile.TemporaryDirectory() as temp:
        first = CheckpointStore(temp, {"instance": "toy", "source": "v1"})
        first.save("national", "cover_N", result(problem), problem)
        assert CheckpointStore(temp, {"instance": "toy", "source": "v2"}).load(
            "national", "cover_N", problem) is None
        changed = level0.build_level0(type("Cells", (), dict(
            M=np.array([[0.5], [0.5], [1.0]]), channels=("N_WH",),
            state_list=("AA", "BB", "CC")))(),
            {"N": ("N_WH",)}, edges=[], L=0.8, U=1.2, eta=0.05, fixed_used={"N": 2})
        assert first.load("national", "cover_N", changed) is None
        assert model_fingerprint(problem, first.provenance) != model_fingerprint(changed, first.provenance)


def test_corrupt_or_infeasible_checkpoint_is_ignored_and_latest_skips_it():
    problem = toy()
    with tempfile.TemporaryDirectory() as temp:
        store = CheckpointStore(temp, {"instance": "toy"})
        good = store.save("national", "cover_N", result(problem), problem)
        bad = store.path("national", "contacts")
        bad.write_text("{not json")
        assert store.load("national", "contacts", problem) is None
        assert store.latest("national", problem)["pass_name"] == "cover_N"
        raw = json.loads(good.read_text())
        raw["warm_start"][0] = 0.5
        good.write_text(json.dumps(raw))
        assert store.load("national", "cover_N", problem) is None
        assert store.latest("national", problem) is None


def test_nonfinite_vectors_and_top_level_json_list_are_rejected():
    problem = toy()
    solved = result(problem)
    for key in ("x", "z", "y"):
        bad = dict(solved)
        if key == "x":
            bad[key] = reconstruct_vector(problem, solved)
        bad[key] = np.asarray(bad[key], float).copy()
        bad[key].flat[0] = np.nan
        try:
            reconstruct_vector(problem, bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"non-finite {key} was accepted")
    with tempfile.TemporaryDirectory() as temp:
        store = CheckpointStore(temp, {"instance": "toy"})
        store.path("national", "cover_N").parent.mkdir(exist_ok=True)
        store.path("national", "cover_N").write_text("[]")
        assert store.load("national", "cover_N", problem) is None


def test_connected_checkpoint_round_trips_in_a_fresh_process():
    problem = toy()
    with tempfile.TemporaryDirectory() as temp:
        store = CheckpointStore(temp, {"instance": "toy", "source": "v1"})
        store.save("national", "cover_N", result(problem), problem)
        code = f'''\
import numpy as np
from td.solvers import level0
from tools.group2_checkpoint import CheckpointStore
class Cells:
    M = np.array([[0.5], [0.5], [1.0]])
    channels = ("N_WH",)
    state_list = ("AA", "BB", "CC")
problem = level0.build_level0(Cells(), {{"N": ("N_WH",)}}, edges=[(0, 1), (1, 2)],
                               L=0.8, U=1.2, eta=0.05, fixed_used={{"N": 2}})
loaded = CheckpointStore({temp!r}, {{"instance": "toy", "source": "v1"}}).load(
    "national", "cover_N", problem)
assert loaded is not None
level0.check_point(problem, loaded["x"])
assert loaded["x"][problem.off_f:problem.off_u].sum() > 0
'''
        subprocess.run([sys.executable, "-c", code], check=True, capture_output=True, text=True)


def test_partial_pure_state_result_is_rejected_before_checkpointing():
    cells = type("Cells", (), dict(M=np.ones((2, 2)), channels=("N_WH", "N_FI"),
                                    state_list=("AA", "BB")))()
    problem = level0.build_level0(cells, {"N": ("N_WH", "N_FI")}, edges=[(0, 1)],
                                  L=0.8, U=1.2, eta=0.05)
    problem = constrain_problem(problem, {"N": 1})
    z = np.zeros((problem.n_state, problem.k))
    y = np.zeros((problem.n_state, problem.k))
    z[0, 0] = 1.0
    y[0, 0] = 0.5
    try:
        reconstruct_vector(problem, {"z": z, "y": y})
    except ValueError as exc:
        assert "conditional_purity" in str(exc)
    else:
        raise AssertionError("partial pure state result was accepted")
