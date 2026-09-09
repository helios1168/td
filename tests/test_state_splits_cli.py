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

import gzip
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

from td import geo as td_geo                   # noqa: E402
from td import instance as td_instance         # noqa: E402
import borders_report                          # noqa: E402
import state_splits as cli                     # noqa: E402
from test_state_splits import CENTRES, EVEN, path_toy   # noqa: E402


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


# ------------------------------------------------------------------------------ end to end
def _write_gz_instance(path, zips, states_by_zip, M_by_zip, reps) -> None:
    """The `td_instance_descaled/1` export format (`tests/test_run_draw_locks.py`'s pattern):
    every rep cycled onto a couple of zips each, so `channel.stage2` can staff the map."""
    share = {}
    for i, z in enumerate(zips):
        r1, r2 = reps[i % len(reps)], reps[(i + 1) % len(reps)]
        share[z] = {r1: 0.3, r2: 0.2}
    obj = dict(
        format=td_instance.FORMAT,
        nodes=dict(z=zips, m_rel=[M_by_zip[z] for z in zips], share=[share[z] for z in zips],
                  state=[states_by_zip[z] for z in zips]),
        edges=dict(u=[], v=[]),
    )
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        json.dump(obj, fh)


def test_main_writes_timings_json_end_to_end():
    """The "clip" driver's telemetry.  `borders_report.load_committed` and `geo.state_rook`
    read a real committed draw and a real shapefile respectively; both are monkeypatched here
    so the run needs neither, on the six-state, k=2, zero-split `EVEN` toy from
    `test_state_splits.py` wired into a real `Descaled` instance (so `borders_report.cell_row`'s
    Nash and stage-2 measurements have a graph to read).  Confirms `main()` writes
    `timings.json` next to its usual `params.json`/`grid.csv`."""
    toy = path_toy(EVEN, centres=CENTRES)
    state_list = [f"S{i}" for i in range(6)]
    zips = [f"{10000 + s * 10 + i:05d}" for s in range(6) for i in range(4)]
    states_by_zip = {z: state_list[int(s)] for z, s in zip(zips, toy["state_idx"])}
    M_by_zip = {z: float(m) for z, m in zip(zips, toy["M"])}
    labels0 = np.repeat([0, 0, 0, 1, 1, 1], 4)
    committed_full = {z: ("D01" if lab == 0 else "D02") for z, lab in zip(zips, labels0)}
    reps = ["rep0", "rep1", "rep2", "rep3"]

    home, owners = borders_report._home_and_owners(labels0, toy["state_idx"], toy["M"], 2,
                                                    len(state_list))

    adj = {}
    for i in range(6):
        nbrs = []
        if i > 0:
            nbrs.append(f"S{i - 1}")
        if i < 5:
            nbrs.append(f"S{i + 1}")
        adj[f"S{i}"] = tuple(nbrs)

    with tempfile.TemporaryDirectory() as tmp:
        inst_path = os.path.join(tmp, "inst.json.gz")
        _write_gz_instance(inst_path, zips, states_by_zip, M_by_zip, reps)
        d = td_instance.load_descaled(inst_path)

        ctx = borders_report.Ctx(
            d=d, zips=zips, xy=toy["xy"], M=toy["M"], state_idx=toy["state_idx"],
            labels0=labels0, k=2, state_list=state_list, states_by_zip=states_by_zip,
            M_by_zip=M_by_zip, missing=[], committed_full=committed_full, home=home,
            owners=owners, committed_rep_of=None)

        orig_load, orig_rook = borders_report.load_committed, td_geo.state_rook
        borders_report.load_committed = lambda *a, **kw: ctx
        td_geo.state_rook = lambda *a, **kw: (adj, {})
        try:
            out = os.path.join(tmp, "out")
            rc = cli.main([inst_path, "--draw", "unused.csv", "--k", "2",
                          "--delta", "0.001", "--time-limit", "10", "--no-maps",
                          "--out", out])
            assert rc == 0, rc
        finally:
            borders_report.load_committed, td_geo.state_rook = orig_load, orig_rook

        assert os.path.exists(os.path.join(out, "timings.json"))
