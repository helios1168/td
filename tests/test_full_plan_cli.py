"""test_full_plan_cli.py: tools/full_plan.py, the argparse defaults, the failure record, and
one end-to-end run per route on a toy.

The defaults are a contract with `tools/borders_report.py` for the same reason
`tests/test_state_splits_cli.py` asserts them there: a plan scored under different stage-2
weights is not comparable to the committed map's own number.  `failure.json`'s keys are a
contract with `app/headline.py::failure`, so they are checked against
`tools/state_splits.py::_write_failure`'s own record rather than restated by hand.

The end-to-end tests need `td.channels`, `td.stage2_state` and `td.solvers.level0`, which land
alongside this file; `tests/run_all.py` imports every test module before it filters, so the
import is guarded here and the tests skip while a module is missing.  The integration agent
removes the guard.
"""
from __future__ import annotations

import csv
import gzip
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
if os.path.join(ROOT, "tools") not in sys.path:
    sys.path.insert(0, os.path.join(ROOT, "tools"))

from td import geo as td_geo                   # noqa: E402
from td import instance as td_instance         # noqa: E402
import full_plan as cli                        # noqa: E402
import state_splits as ss_cli                  # noqa: E402

try:                                            # written concurrently; see the docstring
    from td import channels as _channels        # noqa: F401
    from td import stage2_state as _stage2      # noqa: F401
    from td.solvers import level0 as _level0    # noqa: F401
    HAVE_LEVEL0 = True
except Exception:                               # pragma: no cover - the wave-1 window only
    HAVE_LEVEL0 = False

STATES = [f"S{i}" for i in range(6)]

# the six-state path, the same shape as tests/test_state_splits.py's `path_toy`
PATH_ADJ = {f"S{i}": tuple(f"S{j}" for j in (i - 1, i + 1) if 0 <= j < 6) for i in range(6)}


# --------------------------------------------------------------------------- argparse defaults
def test_stage2_weight_flags_default_to_borders_report_s_own_constants():
    """Unset, `--theta`/`--lam`/`--filler-capture` reproduce `tools/borders_report.py`'s
    constants, so a plan's `staffing.json` value is comparable to the committed map's."""
    args = cli.build_argparser().parse_args(["instance.json.gz", "--out", "out"])
    assert args.theta == cli.borders_report.THETA
    assert args.lam == cli.borders_report.LAM
    assert args.filler_capture == cli.borders_report.FILLER_CAPTURE


def test_band_and_k_defaults_are_the_settled_business_numbers():
    """tau = national mass / k at today's committed k = 18, floor 0.8 tau and cap 1.2 tau
    (docs/FULL_PROBLEM.md decisions 7 and section 5)."""
    args = cli.build_argparser().parse_args(["instance.json.gz", "--out", "out"])
    assert args.k == 18
    assert args.band_lo == 0.8 and args.band_hi == 1.2
    assert args.route == "sequential" and args.driver == "geo"
    assert args.catch_all is False
    assert args.priority == "N,WH,FI"
    assert args.bundles is None                 # resolved from td.channels.DEFAULT_BUNDLES
    assert args.n_max is None and args.dist_max is None


def test_engine_and_strategy_defaults_match_the_state_splits_driver():
    args = cli.build_argparser().parse_args(["instance.json.gz", "--out", "out"])
    assert args.engine == ss_cli.DEFAULT_ENGINE
    assert args.strategy == ss_cli.DEFAULT_STRATEGY


def test_filler_capture_rejects_a_value_outside_td_model_s_choices():
    try:
        cli.build_argparser().parse_args(
            ["instance.json.gz", "--out", "out", "--filler-capture", "bogus"])
    except SystemExit:
        pass
    else:
        raise AssertionError("expected SystemExit for an unknown --filler-capture value")


# -------------------------------------------------------------------------- the failure record
def test_a_failed_pass_writes_the_same_record_state_splits_writes():
    """`app/headline.py::failure` is the only reader of `failure.json` and keys off `reason`
    and `solve_seconds`, so this driver's record must carry the same keys and the same
    `reason` mapping as `tools/state_splits.py`'s."""
    infeasible = ss_cli.ss.SolveFailure(
        2, "The problem is infeasible. (HiGHS Status 8: model_status is Infeasible)")
    empty = ss_cli.ss.SolveFailure(
        1, "Time limit reached. (HiGHS Status 13: primal_status is None)")

    with tempfile.TemporaryDirectory() as out:
        ref_dir = os.path.join(out, "ref")
        mine = os.path.join(out, "mine")
        os.makedirs(ref_dir)
        os.makedirs(mine)
        ss_cli._write_failure(ref_dir, "d0.05", 0.05, infeasible, 3.26)
        cli._write_failure(mine, "cover_N", infeasible, 3.26)
        with open(os.path.join(ref_dir, "failure.json"), encoding="utf-8") as fh:
            ref = json.load(fh)
        with open(os.path.join(mine, "failure.json"), encoding="utf-8") as fh:
            rec = json.load(fh)

        assert set(rec) == set(ref)
        assert rec["reason"] == "infeasible" and rec["status"] == 2
        assert rec["message"] == infeasible.solver_message
        assert rec["solve_seconds"] == 3.3
        assert rec["cell"] == "cover_N"

        cli._write_failure(mine, "contacts", empty, 3600.4)
        with open(os.path.join(mine, "failure.json"), encoding="utf-8") as fh:
            rec = json.load(fh)
        assert rec["reason"] == "no_incumbent" and rec["solve_seconds"] == 3600.4


# ------------------------------------------------------------------------------- state geometry
def test_state_list_comes_from_the_instance_not_a_hard_coded_49():
    """A toy has its own state codes; the level-0 cells are built over whatever the instance
    carries, and `_state_edges` is what refuses a code the rook graph does not know."""
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "inst.json.gz")
        _write_v1(path)
        d = td_instance.load_descaled(path)
        assert cli._state_list(d) == STATES


def test_state_edges_refuse_a_state_the_rook_graph_does_not_know():
    orig = td_geo.state_rook
    td_geo.state_rook = lambda *a, **kw: (PATH_ADJ, {})
    try:
        assert cli._state_edges(STATES, "unused") == [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5)]
        try:
            cli._state_edges(STATES + ["ZZ"], "unused")
        except ValueError as exc:
            assert "ZZ" in str(exc)
        else:
            raise AssertionError("expected a ValueError for a state outside the rook graph")
    finally:
        td_geo.state_rook = orig


# ------------------------------------------------------------------------------------ end to end
def _write_v1(path: str) -> list[str]:
    """A format-1 toy: six states, four zips each, every rep on a couple of zips.

    The same export shape `tests/test_state_splits_cli.py::_write_gz_instance` writes, plus a
    `share_free` column so the filler term of the stage-2 utility is not identically zero.
    """
    zips = [f"{10000 + s * 10 + i:05d}" for s in range(6) for i in range(4)]
    reps = [f"rep{i}" for i in range(6)]
    share = []
    for i, _ in enumerate(zips):
        share.append({reps[i % len(reps)]: 0.3, reps[(i + 1) % len(reps)]: 0.2})
    obj = dict(
        format=td_instance.FORMAT,
        nodes=dict(z=zips, m_rel=[1.0] * len(zips), share=share,
                   share_free=[0.1] * len(zips),
                   state=[STATES[i // 4] for i in range(len(zips))]),
        edges=dict(u=[zips[i] for i in range(len(zips) - 1)],
                   v=[zips[i + 1] for i in range(len(zips) - 1)]),
    )
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        json.dump(obj, fh)
    return zips


def _run(tmp: str, route: str) -> str:
    out = os.path.join(tmp, f"out_{route}")
    inst = os.path.join(tmp, "inst.json.gz")
    _write_v1(inst)
    orig = td_geo.state_rook
    td_geo.state_rook = lambda *a, **kw: (PATH_ADJ, {})
    try:
        rc = cli.main([inst, "--synthesize", "--route", route, "--driver", "geo",
                       "--engine", "scipy", "--strategy", "direct", "--k", "2",
                       "--time-limit", "30", "--out", out])
        assert rc == 0, rc
    finally:
        td_geo.state_rook = orig
    return out


def _check_plan(out: str) -> dict:
    with open(os.path.join(out, "plan.json"), encoding="utf-8") as fh:
        plan = json.load(fh)
    assert set(plan) == {"state_list", "bundles", "slots", "per_state", "passes", "moves"}
    assert plan["state_list"] == STATES
    for rec in plan["slots"]:
        assert set(rec) == {"id", "bundle", "used", "mass", "contacts", "y"}
    ids = [rec["id"] for rec in plan["slots"]]
    assert len(ids) == len(set(ids)), "slot ids must be unique across stages"

    bundle_of = {rec["id"]: rec["bundle"] for rec in plan["slots"]}
    from td import channels

    for st, row in plan["per_state"].items():
        assert st in STATES
        covered = {c: 0.0 for c in channels.CHANNELS}
        for slot_id, share in row.items():
            if slot_id == "residual_by_channel":
                continue
            for c in channels.BUNDLES[bundle_of[slot_id]]:
                covered[c] += float(share)
        for c, v in covered.items():
            assert v <= 1.0 + 1e-6, (st, c, v)
            assert row["residual_by_channel"][c] >= -1e-6
    assert os.path.exists(os.path.join(out, "params.json"))
    assert os.path.exists(os.path.join(out, "staffing.json"))
    assert os.path.exists(os.path.join(out, "timings.json"))
    assert os.path.isdir(os.path.join(out, "projections"))
    return plan


def test_end_to_end_sequential_writes_a_plan_and_projections():
    """The whole driver on the six-state path toy with `state_rook` monkeypatched: a v1 file
    expanded by `--synthesize`, three sequential stages, and one projection per used bundle.

    Pinned to `--engine scipy --strategy direct` for the reason
    `tests/test_state_splits_cli.py` pins it: HiGHS's thread pool is process-global and sized
    by the first thread count a process asks for (trap 18), and `tests/run_all.py` is one long
    lived process.
    """
    if not HAVE_LEVEL0:
        return
    with tempfile.TemporaryDirectory() as tmp:
        out = _run(tmp, "sequential")
        plan = _check_plan(out)
        used = {rec["bundle"] for rec in plan["slots"] if rec["used"] and rec["y"]}
        assert used
        for bundle in used:
            cell = os.path.join(out, "projections", bundle)
            assert os.path.exists(os.path.join(cell, "instance_descaled.json.gz"))
            with open(os.path.join(cell, "state_shares.csv"), encoding="utf-8") as fh:
                rows = list(csv.DictReader(fh))
            assert rows and set(rows[0]) == {"state", "district", "share", "target_mass"}
            # target_mass is M^B_s * y_sj, so the column sums to the bundle's slot mass
            want = sum(rec["mass"] for rec in plan["slots"]
                       if rec["bundle"] == bundle and rec["used"] and rec["y"])
            got = sum(float(r["target_mass"]) for r in rows)
            assert abs(got - want) <= 1e-6 * max(1.0, want), (bundle, got, want)


def test_end_to_end_joint_runs_the_lexicographic_passes():
    """Route joint over one model: the pass log must name the coverage passes and contacts,
    in that order, and the plan must satisfy the same per-channel coverage bound."""
    if not HAVE_LEVEL0:
        return
    with tempfile.TemporaryDirectory() as tmp:
        out = _run(tmp, "joint")
        plan = _check_plan(out)
        names = [p["name"] for p in plan["passes"]]
        assert names, "route joint must record its passes"
        cover = [i for i, n in enumerate(names) if "cover" in n]
        contacts = [i for i, n in enumerate(names) if "contacts" in n]
        assert cover and contacts
        assert max(cover) < min(contacts), names       # coverage is lexicographically first
        for rec in plan["passes"]:
            assert {"name", "value", "certified", "status", "seconds"} <= set(rec)


def test_driver_reps_logs_every_move_and_the_catch_all_pass_runs():
    """`--driver reps` scores {keep, merge WH+FI, drop N} per state and logs all of them, kept
    or not; `--catch-all` adds one more model over the residual with the four-channel bundle.

    Only the moves the last model can express are offered: under route sequential the N slots
    belong to an earlier model, so "drop N" does not appear (the TODO in `_rep_moves`).
    """
    if not HAVE_LEVEL0:
        return
    with tempfile.TemporaryDirectory() as tmp:
        inst = os.path.join(tmp, "inst.json.gz")
        _write_v1(inst)
        out = os.path.join(tmp, "out_reps")
        orig = td_geo.state_rook
        td_geo.state_rook = lambda *a, **kw: (PATH_ADJ, {})
        try:
            rc = cli.main([inst, "--synthesize", "--route", "sequential", "--driver", "reps",
                           "--catch-all", "--engine", "scipy", "--strategy", "direct",
                           "--k", "2", "--time-limit", "30", "--out", out])
            assert rc == 0, rc
        finally:
            td_geo.state_rook = orig

        plan = _check_plan(out)
        assert plan["moves"], "--driver reps must log its moves"
        assert {m["state"] for m in plan["moves"]} <= set(STATES)
        assert {m["move"] for m in plan["moves"]} <= set(cli.MOVES)
        assert "keep" in {m["move"] for m in plan["moves"]}
        assert sum(m["accepted"] for m in plan["moves"]) <= len(STATES)
        stages = [p["stage"] for p in plan["passes"]]
        assert "catch_all" in stages


def test_synthesize_writes_the_v2_instance_it_solved():
    """A synthetic run is only reproducible if the instance it invented is on disk beside the
    plan (trap 22's rule for a gazetteer vintage applies to a synthesized split too)."""
    if not HAVE_LEVEL0:
        return
    with tempfile.TemporaryDirectory() as tmp:
        out = _run(tmp, "sequential")
        v2 = os.path.join(out, "instance_v2.json.gz")
        assert os.path.exists(v2)
        d = td_instance.load_descaled(v2)
        assert d.channels
