"""test_state_splits_cli.py -- tools/state_splits.py: the `--unanchor` release rule, and the
failure record a cell writes when its MILP returns no map.

Pure-function tests on synthetic state/district/mass arrays; no instance file, no solve.  The
six-state path toy in test_state_splits.py has no anchors-per-state notion worth exercising here
(k=2, at most one anchor per state), so this builds the smallest `ctx`-shaped stand-in that
`_release_anchors` actually reads: `state_idx`, `labels0`, `M`, `k`.

`_write_failure`'s key names are a contract with `app/headline.py::failure`, which is the only
reader, so they are asserted here rather than left to the Streamlit tab nothing tests.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
if os.path.join(ROOT, "tools") not in sys.path:
    sys.path.insert(0, os.path.join(ROOT, "tools"))

import state_splits as cli                    # noqa: E402


class _Ctx:
    """The fields `_release_anchors` reads off a real `borders_report.Ctx`, built by hand."""
    def __init__(self, state_idx, labels0, M, k):
        self.state_idx = np.asarray(state_idx)
        self.labels0 = np.asarray(labels0)
        self.M = np.asarray(M, float)
        self.k = k


def test_unanchor_with_a_cap_keeps_the_highest_mass_districts_and_releases_the_rest():
    """State 0 is anchored in three districts (2, 4, 5) with committed masses 10, 6, 6.  A
    cap of 2 keeps the top two by mass -- district 2, then district 4 over the tied district 5
    by ascending index -- and releases only district 5, the minimum surplus."""
    ctx = _Ctx(state_idx=[0, 0, 0, 0, 0, 0, 1],
              labels0=[2, 2, 4, 4, 5, 5, 3],
              M=[5.0, 5.0, 3.0, 3.0, 3.0, 3.0, 1.0], k=6)
    anchors = [(0, 2), (0, 4), (0, 5)]
    kept, info = cli._release_anchors(anchors, {0: 2}, [0], ctx)

    assert kept == [(0, 2), (0, 4)]
    assert info[0] == ([2, 4], [5])


def test_unanchor_without_a_cap_releases_every_anchor():
    """No `--cap` on the state: `--unanchor` keeps its original behaviour and releases all of
    it, the same as before this state's cap-aware release existed."""
    ctx = _Ctx(state_idx=[0, 0], labels0=[2, 4], M=[5.0, 5.0], k=6)
    kept, info = cli._release_anchors([(0, 2), (0, 4)], {}, [0], ctx)

    assert kept == []
    assert info[0] == ([], [2, 4])


def test_unanchor_never_releases_more_than_the_cap_forces():
    """A cap at or above the anchored count needs no release at all."""
    ctx = _Ctx(state_idx=[0, 0], labels0=[2, 4], M=[5.0, 5.0], k=6)
    kept, info = cli._release_anchors([(0, 2), (0, 4)], {0: 2}, [0], ctx)

    assert kept == [(0, 2), (0, 4)]
    assert info[0] == ([2, 4], [])


def test_a_failed_cell_records_which_answer_the_solver_gave():
    """The two failures a headline rerun can hit write the same file with a different `reason`,
    and the reader in `app/headline.py` keys off that field and the seconds beside it."""
    infeasible = cli.ss.SolveFailure(
        2, "The problem is infeasible. (HiGHS Status 8: model_status is Infeasible)")
    empty = cli.ss.SolveFailure(
        1, "Time limit reached. (HiGHS Status 13: primal_status is None)")

    with tempfile.TemporaryDirectory() as out:
        cli._write_failure(out, "d0.05", 0.05, infeasible, 3.26)
        with open(os.path.join(out, "failure.json"), encoding="utf-8") as fh:
            rec = json.load(fh)
        assert rec == {"cell": "d0.05", "delta": 0.05, "reason": "infeasible", "status": 2,
                       "message": infeasible.solver_message, "solve_seconds": 3.3}

        cli._write_failure(out, "d0.05", 0.05, empty, 3600.4)
        with open(os.path.join(out, "failure.json"), encoding="utf-8") as fh:
            rec = json.load(fh)
        assert rec["reason"] == "no_incumbent" and rec["solve_seconds"] == 3600.4


# ------------------------------------------------------------------------------ stage-2 weights
def test_stage2_weight_flags_default_to_borders_report_s_own_constants():
    """`--theta`/`--lam`/`--filler-capture` exist so a cell can be scored under different
    stage-2 weights than the committed map's own; unset, they must reproduce
    `tools/borders_report.py`'s constants exactly, since that module's docstring promises a
    cell's `stage2_value` is only comparable to the committed one under the same weights."""
    args = cli.build_argparser().parse_args(
        ["instance.json.gz", "--draw", "draw.csv", "--out", "out"])
    assert args.theta == cli.borders_report.THETA
    assert args.lam == cli.borders_report.LAM
    assert args.filler_capture == cli.borders_report.FILLER_CAPTURE


def test_stage2_weight_flags_parse():
    args = cli.build_argparser().parse_args(
        ["instance.json.gz", "--draw", "draw.csv", "--out", "out",
         "--theta", "0.5", "--lam", "0.1", "--filler-capture", "full"])
    assert args.theta == 0.5
    assert args.lam == 0.1
    assert args.filler_capture == "full"


def test_filler_capture_rejects_a_value_outside_td_model_s_choices():
    """`choices=list(model.FILLER_CAPTURE)` refuses anything not in that tuple."""
    try:
        cli.build_argparser().parse_args(
            ["instance.json.gz", "--draw", "draw.csv", "--out", "out",
             "--filler-capture", "bogus"])
    except SystemExit:
        pass
    else:
        raise AssertionError("expected SystemExit for an unknown --filler-capture value")
