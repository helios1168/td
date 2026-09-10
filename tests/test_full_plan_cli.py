"""test_full_plan_cli.py: tools/full_plan.py, the argparse defaults, the failure record, and
one end-to-end run per route on a toy.

The defaults are a contract with `tools/borders_report.py` for the same reason
`tests/test_state_splits_cli.py` asserts them there: a plan scored under different stage-2
weights is not comparable to the committed map's own number.  `failure.json`'s keys are a
contract with `app/headline.py::failure`, so they are checked against
`tools/state_splits.py::_write_failure`'s own record rather than restated by hand.
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

import types                                   # noqa: E402

import numpy as np                             # noqa: E402

from td import channels                        # noqa: E402
from td import geo as td_geo                   # noqa: E402
from td import instance as td_instance         # noqa: E402
import borders_report                          # noqa: E402
import full_plan as cli                        # noqa: E402
import state_splits as ss_cli                  # noqa: E402
import us_maps                                 # noqa: E402

STATES = [f"S{i}" for i in range(6)]

# the six-state path, the same shape as tests/test_state_splits.py's `path_toy`
PATH_ADJ = {f"S{i}": tuple(f"S{j}" for j in (i - 1, i + 1) if 0 <= j < 6) for i in range(6)}

# `geo.state_rook`'s second return, the state polygons `_state_xy` takes centroids from.  Most
# tests stub it empty, which is what makes `--dist-max`, `--radius-max` and `--centers seeds`
# refuse and the plan's hull metrics null; these put the six states on a line 100 km apart
# (the centroid is in metres, `_state_xy` divides by 1000).
PATH_POLYS = {c: types.SimpleNamespace(centroid=types.SimpleNamespace(x=i * 100_000.0, y=0.0))
              for i, c in enumerate(STATES)}


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
    assert args.n_max is None and args.dist_max is None and args.radius_max is None
    # unset, no slot is centred on anything and no compactness pass runs
    assert args.centers is None and args.incumbency is None
    # the exact pin: unset, every cover pass holds its value and the plan is what it was
    assert args.cover_slack == 0.0
    # a real run is 49 states at about two MILPs each; the budget is what keeps `--driver reps`
    # from spending hours nobody asked for
    assert args.move_budget == 20


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


def test_failure_json_carries_the_pass_log_when_the_solver_attached_one():
    """`td.solvers.level0.solve_passes` hangs the pass log on the `SolveFailure` it raises.

    The key is written only when it is there, so a failure from anywhere else still writes
    exactly the record `tools/state_splits.py` writes and `app/headline.py::failure` reads.
    """
    exc = ss_cli.ss.SolveFailure(
        1, "Time limit reached. (HiGHS Status 13: primal_status is None)")
    exc.passes = [dict(name="cover_N", value=24.0, certified=True, status=0, seconds=1.5),
                  dict(name="contacts", value=None, certified=False,
                       status="no_incumbent", seconds=600.0)]
    with tempfile.TemporaryDirectory() as out:
        cli._write_failure(out, "joint", exc, 601.5)
        with open(os.path.join(out, "failure.json"), encoding="utf-8") as fh:
            rec = json.load(fh)
    assert rec["reason"] == "no_incumbent"
    assert [p["name"] for p in rec["passes"]] == ["cover_N", "contacts"]
    assert rec["passes"][1]["value"] is None
    assert {p["stage"] for p in rec["passes"]} == {"joint"}


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


def _run(tmp: str, route: str, extra=(), polys=None) -> str:
    out = os.path.join(tmp, f"out_{route}")
    inst = os.path.join(tmp, "inst.json.gz")
    _write_v1(inst)
    orig = td_geo.state_rook
    td_geo.state_rook = lambda *a, **kw: (PATH_ADJ, polys or {})
    try:
        rc = cli.main([inst, "--synthesize", "--route", route, "--driver", "geo",
                       "--engine", "scipy", "--strategy", "direct", "--k", "2",
                       "--time-limit", "30", "--out", out, *extra])
        assert rc == 0, rc
    finally:
        td_geo.state_rook = orig
    return out


def _check_plan(out: str) -> dict:
    with open(os.path.join(out, "plan.json"), encoding="utf-8") as fh:
        plan = json.load(fh)
    assert set(plan) == {"state_list", "bundles", "slots", "per_state", "passes", "moves",
                         "anchors"}
    assert plan["state_list"] == STATES
    for rec in plan["slots"]:
        assert set(rec) == {"id", "bundle", "used", "mass", "contacts", "y",
                            "center", "extent_km", "radius_km"}
    ids = [rec["id"] for rec in plan["slots"]]
    assert len(ids) == len(set(ids)), "slot ids must be unique across stages"

    bundle_of = {rec["id"]: rec["bundle"] for rec in plan["slots"]}
    for st, row in plan["per_state"].items():
        assert st in STATES
        covered = {c: 0.0 for c in channels.CHANNELS}
        for slot_id, share in row.items():
            if slot_id == "residual_by_channel":
                continue
            for c in cli._bundle_channels(bundle_of[slot_id]):
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


def test_warm_greedy_records_the_pseudo_pass_and_warm_none_does_not():
    """`--warm greedy` (the default) opens the stage's pass log with the greedy pseudo-entry,
    status `warm_start` (a failed build would read `warm_start_failed`); `--warm none` leaves
    the log as it was.  Both are recorded in `params.json`."""
    with tempfile.TemporaryDirectory() as tmp:
        plan = _check_plan(_run(tmp, "joint"))
        greedy = [p for p in plan["passes"] if p["name"] == "greedy"]
        assert len(greedy) == 1, plan["passes"]
        rec = greedy[0]
        assert rec["status"] == "warm_start" and rec["certified"] is False
        assert set(rec["value"]) == set(plan["bundles"]) and rec["seconds"] >= 0.0
        assert plan["passes"].index(rec) == 0, "the pseudo-entry leads the stage's log"
        with open(os.path.join(tmp, "out_joint", "params.json"), encoding="utf-8") as fh:
            assert json.load(fh)["warm"] == "greedy"

        plan = _check_plan(_run(tmp, "sequential", ["--warm", "none"]))
        assert not [p for p in plan["passes"] if p["name"] == "greedy"]
        with open(os.path.join(tmp, "out_sequential", "params.json"), encoding="utf-8") as fh:
            assert json.load(fh)["warm"] == "none"
    assert cli.build_argparser().parse_args(["i", "--out", "o"]).warm == "greedy"
    assert cli.build_argparser().parse_args(["i", "--out", "o"]).anchor == "none"


def test_anchor_greedy_roots_every_used_slot_at_its_greedy_seed():
    """`--anchor greedy` rebuilds the model with `z` anchored and the root fixed
    (`fix_roots`) at every greedy seed, one per used slot, and records them in `plan.json`.
    The model handed to `solve_passes` is captured to read the `r` bounds."""
    from td.solvers import level0

    seen = []
    orig = level0.solve_passes

    def capture(problem, passes, **kw):
        seen.append((problem, kw.get("warm_start")))
        return orig(problem, passes, **kw)

    level0.solve_passes = capture
    try:
        with tempfile.TemporaryDirectory() as tmp:
            plan = _check_plan(_run(tmp, "joint", ["--anchor", "greedy"]))
    finally:
        level0.solve_passes = orig
    anchors = [a for a in plan["anchors"] if a["source"] == "greedy"]
    assert anchors and {a["stage"] for a in anchors} == {"joint"}
    (problem, warm), = seen
    K, idx = problem.k, {c: i for i, c in enumerate(plan["state_list"])}
    for a in anchors:
        s, j = idx[a["state"]], a["slot"]
        assert problem.var_lb[problem.off_z + s * K + j] == 1.0
        assert problem.var_lb[problem.off_r + s * K + j] == 1.0
        assert all(problem.var_ub[problem.off_r + t * K + j] == 0.0
                   for t in range(problem.n_state) if t != s)
        assert plan["slots"][j]["used"] and a["bundle"] == plan["slots"][j]["bundle"]
    assert warm is not None and len({a["slot"] for a in anchors}) == len(anchors)
    # every slot the greedy used is anchored: the warm point's u block says which
    assert sorted(a["slot"] for a in anchors) == \
        [j for j in range(K) if warm[problem.off_u + j] > 0.5]

    try:
        cli.build_argparser().parse_args(["i", "--out", "o", "--anchor", "greedy",
                                          "--driver", "reps"])
        with tempfile.TemporaryDirectory() as tmp:
            _run(tmp, "joint", ["--anchor", "greedy", "--driver", "reps"])
        raise AssertionError("--anchor greedy must be refused under --driver reps")
    except ValueError as exc:
        assert "--anchor greedy" in str(exc)


def test_centers_seeds_gives_every_used_slot_a_centre_and_a_compactness_pass():
    """`--centers seeds` measures the tie-break about each slot's own greedy seed, so the pass
    runs for WH and FI and not only for the N slots a committed draw names.  The seeds are
    built whatever `--warm` and `--anchor` say, or the flag would be silently inert.
    """
    with tempfile.TemporaryDirectory() as tmp:
        out = _run(tmp, "joint", ["--centers", "seeds", "--warm", "none"], polys=PATH_POLYS)
        plan = _check_plan(out)
        assert [p["name"] for p in plan["passes"]].count("compactness") == 1
        with open(os.path.join(out, "params.json"), encoding="utf-8") as fh:
            params = json.load(fh)
        assert params["centers"] == "seeds", "the literal is recorded, not a path"
        assert params["radius_max"] is None
        used = [rec for rec in plan["slots"] if rec["used"] and rec["y"]]
        assert used and all(rec["center"] in STATES for rec in used)
        bundles = {rec["bundle"] for rec in used}
        assert len(bundles) > 1, "the toy must use more than the N bundle or this proves little"


def test_the_hull_metrics_are_the_slot_s_own_extent_and_radius():
    """`extent_km` is the widest centroid distance between two states a slot contacts and
    `radius_km` the widest from its centre; both are reported, neither is constrained.  On the
    100 km line they are recomputable from the slot's own shares."""
    idx = {c: i for i, c in enumerate(STATES)}
    with tempfile.TemporaryDirectory() as tmp:
        plan = _check_plan(_run(tmp, "joint", ["--centers", "seeds"], polys=PATH_POLYS))
        used = [rec for rec in plan["slots"] if rec["used"] and rec["y"]]
        assert used
        for rec in used:
            pos = [idx[st] * 100.0 for st in rec["y"]]
            assert abs(rec["extent_km"] - (max(pos) - min(pos))) < 1e-6, rec
            home = idx[rec["center"]] * 100.0
            assert abs(rec["radius_km"] - max(abs(p - home) for p in pos)) < 1e-6, rec
        for rec in plan["slots"]:
            if not rec["contacts"]:
                assert rec["extent_km"] is None and rec["radius_km"] is None

        # no polygons in the cache, no geometry to measure in: the keys are still there
        plan = _check_plan(_run(tmp, "sequential"))
        assert all(rec["extent_km"] is None and rec["radius_km"] is None
                   for rec in plan["slots"])


def test_a_slot_record_without_a_known_centre_says_so_rather_than_guessing():
    """`_slot_records(roots=None)`, which is how `_rep_moves` calls it: a move re-solves the
    contacts, so the stage's seed may no longer be one of them and naming it as the centre
    would be a claim the record cannot support.  `extent_km` needs no centre and is still
    measured."""
    problem = types.SimpleNamespace(k=2, bundle_of=("N", "N"))
    result = dict(z=np.array([[1, 0], [1, 0], [0, 1], [0, 0], [0, 0], [0, 0]], bool),
                  y=np.array([[1.0, 0.0], [0.5, 0.0], [0.0, 1.0], [0.0, 0.0],
                              [0.0, 0.0], [0.0, 0.0]]),
                  u=np.array([True, True]), masses=np.array([1.5, 1.0]))
    xy = np.array([[i * 100.0, 0.0] for i in range(6)])

    blind = cli._slot_records(problem, result, STATES, 1, state_xy=xy)
    assert [r["center"] for r in blind] == [None, None]
    assert [r["radius_km"] for r in blind] == [None, None]
    assert blind[0]["extent_km"] == 100.0 and blind[1]["extent_km"] == 0.0

    known = cli._slot_records(problem, result, STATES, 1, state_xy=xy, roots={0: 1, 1: 2})
    assert [r["center"] for r in known] == ["S1", "S2"]
    assert known[0]["radius_km"] == 100.0 and known[1]["radius_km"] == 0.0
    # no geometry at all: the keys stay, the numbers do not appear
    bare = cli._slot_records(problem, result, STATES, 1, roots={0: 1})
    assert bare[0]["extent_km"] is None and bare[0]["radius_km"] is None
    assert bare[0]["center"] == "S1"


def test_radius_max_caps_how_far_a_slot_reaches_from_its_root():
    """`--radius-max` with `--anchor greedy`: every used slot is rooted at its seed, so the cap
    is a bound on `z` and the plan's own `radius_km` has to respect it."""
    with tempfile.TemporaryDirectory() as tmp:
        out = _run(tmp, "joint", ["--anchor", "greedy", "--radius-max", "250",
                                  "--centers", "seeds"], polys=PATH_POLYS)
        plan = _check_plan(out)
        with open(os.path.join(out, "params.json"), encoding="utf-8") as fh:
            assert json.load(fh)["radius_max"] == 250.0
        used = [rec for rec in plan["slots"] if rec["used"] and rec["y"]]
        assert used
        for rec in used:
            assert rec["radius_km"] <= 250.0 + 1e-6, rec
    # without the state polygons the cap has nothing to measure in, and says so
    with tempfile.TemporaryDirectory() as tmp:
        try:
            _run(tmp, "joint", ["--radius-max", "250"])
            raise AssertionError("--radius-max without state polygons must be refused")
        except ValueError as exc:
            assert "--radius-max" in str(exc)


def test_k_fixed_pins_the_first_slots_and_reaches_params():
    """`--k-fixed N=1` fixes the N bundle's first slot as used, is recorded as a dict in
    `params.json`, and is refused for a bundle outside `--bundles` or a count above the
    bundle's slots."""
    with tempfile.TemporaryDirectory() as tmp:
        plan = _check_plan(_run(tmp, "joint", ["--k-fixed", "N=1"]))
        first_n = next(rec for rec in plan["slots"] if rec["bundle"] == "N")
        assert first_n["used"]
        with open(os.path.join(tmp, "out_joint", "params.json"), encoding="utf-8") as fh:
            assert json.load(fh)["k_fixed"] == {"N": 1}
    assert cli._parse_k_fixed("N=18, WH=11,FI=19") == {"N": 18, "WH": 11, "FI": 19}
    for bad in (["--k-fixed", "ZZ=1"], ["--k-fixed", "N=99"]):
        try:
            with tempfile.TemporaryDirectory() as tmp:
                _run(tmp, "joint", bad)
            raise AssertionError(f"{bad} must be refused")
        except ValueError:
            pass


def test_driver_reps_logs_every_move_and_the_catch_all_pass_runs():
    """`--driver reps` scores {keep, merge WH+FI, drop N} per state and logs all of them, kept
    or not; `--catch-all` adds one more model over the residual with the four-channel bundle.

    Only the moves the last model can express are offered: under route sequential the N slots
    belong to an earlier model, so "drop N" does not appear (the TODO in `_rep_moves`).
    """
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


def test_a_stage_with_no_slots_is_skipped_and_recorded():
    """A stage whose bundles have no residual mass above L gets zero slots, and a zero-slot
    model has no objective to build (`build_level0` raises rather than returning one).  That is
    exactly `--catch-all` after the sequential stages served everything, so the driver checks
    the slot count first and records the stage as skipped."""
    from td.solvers import level0

    cells = types.SimpleNamespace(M=np.zeros((6, 1)), channels=("A",),
                                  state_list=[f"S{i}" for i in range(6)])
    assert level0.slot_counts(cells, {"A": ("A",)}, L=0.8) == {"A": 0}
    try:
        level0.build_level0(cells, {"A": ("A",)}, edges=[(0, 1)], L=0.8, U=1.2, eta=0.05)
    except ValueError as e:
        assert "no slots" in str(e)
    else:
        raise AssertionError("a zero-slot model must be refused, not built")

    # end to end: the even toy's stages serve every channel, so the catch-all has nothing left
    with tempfile.TemporaryDirectory() as tmp:
        inst = os.path.join(tmp, "inst.json.gz")
        _write_v1(inst)
        out = os.path.join(tmp, "out_skip")
        orig = td_geo.state_rook
        td_geo.state_rook = lambda *a, **kw: (PATH_ADJ, {})
        try:
            rc = cli.main([inst, "--synthesize", "--route", "sequential", "--driver", "geo",
                           "--catch-all", "--engine", "scipy", "--strategy", "direct",
                           "--k", "2", "--time-limit", "30", "--out", out])
            assert rc == 0, rc
        finally:
            td_geo.state_rook = orig

        with open(os.path.join(out, "plan.json"), encoding="utf-8") as fh:
            plan = json.load(fh)
        catch = [p for p in plan["passes"] if p.get("stage") == "catch_all"]
        assert catch, "decision 1 reads off the catch-all, so it is recorded either way"
        assert all(p["status"] == "skipped" and p["slots"] == 0 for p in catch)
        assert not [r for r in plan["slots"] if r["bundle"] in cli.CATCH_ALL_BUNDLES]


def test_relax_pins_opens_the_contacts_pin_and_keeps_the_cover_pins():
    """`solve_passes` pins every pass with an appended row.  A move re-solves for contacts, so
    `pin_contacts` -- "no more contacts than the unmerged plan used" -- can only over-constrain
    it; the cover pins must stay, or minimising contacts closes every slot and the best move is
    always the empty plan."""
    from td.solvers import level0

    cells = types.SimpleNamespace(M=np.full((6, 1), 0.5), channels=("A",),
                                  state_list=[f"S{i}" for i in range(6)])
    prob = level0.build_level0(cells, {"A": ("A",)},
                               edges=[(i, i + 1) for i in range(5)], L=0.8, U=1.2, eta=0.05)
    pinned = level0.append_row(prob, "pin_cover_A", [prob.off_u], [1.0], -np.inf, 1.0)
    pinned = level0.append_row(pinned, "pin_contacts", [pinned.off_u], [1.0], -np.inf, 2.0)

    relaxed = cli._relax_pins(pinned, ["pin_contacts"])
    lo, hi = relaxed.rows["pin_contacts"]
    assert np.isinf(relaxed.ub[lo:hi]).all()
    lo, hi = relaxed.rows["pin_cover_A"]
    assert np.allclose(relaxed.ub[lo:hi], 1.0), "a coverage pin must survive"
    # the matrix is untouched, so every offset and any later append_row still lines up
    assert relaxed.A.shape == pinned.A.shape and relaxed.n_var == pinned.n_var
    assert np.allclose(pinned.ub[pinned.rows["pin_contacts"][0]], 2.0), "the input is not mutated"


def test_reps_driver_scores_a_merge_and_names_the_move_it_cannot_evaluate():
    """Two things the move log has to say.

    `merge_whfi` must come back with a real score rather than a solver failure: the moves are
    re-solved with the contacts pin relaxed, so a merge is no longer refused for having a
    different contact count than the plan it is being compared with.  `drop_n` is not
    expressible under route sequential -- the N slots belong to an earlier model -- and is
    recorded as such instead of being silently absent.
    """
    with tempfile.TemporaryDirectory() as tmp:
        inst = os.path.join(tmp, "inst.json.gz")
        _write_v1(inst)
        out = os.path.join(tmp, "out_moves")
        orig = td_geo.state_rook
        td_geo.state_rook = lambda *a, **kw: (PATH_ADJ, {})
        try:
            rc = cli.main([inst, "--synthesize", "--route", "sequential", "--driver", "reps",
                           "--move-budget", "2", "--engine", "scipy", "--strategy", "direct",
                           "--k", "2", "--time-limit", "30", "--out", out])
            assert rc == 0, rc
        finally:
            td_geo.state_rook = orig

        with open(os.path.join(out, "plan.json"), encoding="utf-8") as fh:
            moves = json.load(fh)["moves"]
        merges = [m for m in moves if m["move"] == "merge_whfi"]
        assert merges, "the merge move must be offered"
        assert all(m["value"] is not None for m in merges), \
            "a merge must be scored, not refused by a pin"
        drops = [m for m in moves if m["move"] == "drop_n"]
        assert drops and all(m["status"] == "not_evaluable_under_sequential" for m in drops)
        assert all(m["value"] is None for m in drops)


def _write_v2_fine(path: str) -> None:
    """A format-2 toy already carrying the four fine labels, so no `--synthesize` is needed.

    Two states.  The national mass is 1.0 in total, so at `--k 1` the band is [0.8, 1.2]; S0's
    WH and FI cells are 0.9 each, in band on their own, and S1 has neither.  Run with
    `--bundles N`, the sequential stages serve the national channels and leave WH and FI
    entirely to the catch-all.
    """
    rows = [
        ("z0", "S0", {"N_WH": (0.25, {"rep0": 0.2}), "N_FI": (0.25, {"rep1": 0.2}),
                      "WH": (0.9, {"rep0": 0.3}), "FI": (0.9, {"rep2": 0.3})}),
        ("z1", "S1", {"N_WH": (0.25, {"rep1": 0.2}), "N_FI": (0.25, {"rep2": 0.2}),
                      "WH": (0.0, {}), "FI": (0.0, {})}),
    ]
    z, chan, m_rel, share, share_free, state = [], [], [], [], [], []
    for zid, st, cells in rows:
        for c in channels.CHANNELS:
            m, sh = cells[c]
            z.append(zid); chan.append(c); m_rel.append(m)
            share.append(dict(sh)); share_free.append(0.0); state.append(st)
    obj = dict(
        format=td_instance.FORMAT_V2,
        nodes=dict(z=z, channel=chan, m_rel=m_rel, share=share, share_free=share_free,
                   state=state),
        edges=dict(u=["z0"], v=["z1"]),
        meta=dict(channels=list(channels.CHANNELS)),
    )
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        json.dump(obj, fh)


def test_catch_all_opens_a_slot_on_a_channel_the_stages_left():
    """The catch-all runs one single-channel bundle per fine channel with residual mass.

    A product bundle cannot: a `WHFI_PLUS` slot sits in all four cover rows, so its share is
    bounded by `min_c cover_ub[s, c]`, and once the national channels are served (they are,
    by `seq_N`) no catch-all slot can open anywhere.  Decision 1 reads "a fourth channel
    exists iff the catch-all used a slot", so that bundle made the answer always no.
    """
    with tempfile.TemporaryDirectory() as tmp:
        inst = os.path.join(tmp, "inst.json.gz")
        _write_v2_fine(inst)
        out = os.path.join(tmp, "out_catch")
        orig = td_geo.state_rook
        td_geo.state_rook = lambda *a, **kw: (PATH_ADJ, {})
        try:
            rc = cli.main([inst, "--route", "sequential", "--driver", "geo",
                           "--bundles", "N", "--catch-all", "--engine", "scipy",
                           "--strategy", "direct", "--k", "1", "--time-limit", "30",
                           "--out", out])
            assert rc == 0, rc
        finally:
            td_geo.state_rook = orig

        with open(os.path.join(out, "plan.json"), encoding="utf-8") as fh:
            plan = json.load(fh)
        catch = [rec for rec in plan["slots"]
                 if rec["bundle"] in cli.CATCH_ALL_BUNDLES and rec["used"] and rec["y"]]
        assert catch, "the catch-all must open a slot on the channels the stages left"
        assert {rec["bundle"] for rec in catch} == {"OTHER_WH", "OTHER_FI"}
        # each catch-all bundle carries exactly one fine channel
        for rec in catch:
            assert len(cli._bundle_channels(rec["bundle"])) == 1
        # S0's WH and FI are now fully served, and the national channels stay served
        row = plan["per_state"]["S0"]["residual_by_channel"]
        for c in ("WH", "FI", "N_WH", "N_FI"):
            assert abs(row[c]) <= 1e-6, (c, row[c])
        assert any(p.get("stage") == "catch_all" for p in plan["passes"])


MERGED_ADJ = {"S0": (), "S1": ("S2",), "S2": ("S1",)}


def _write_v2_merged(path: str) -> None:
    """The shape code verify R3 probed at row 2b, plus a state pure WH can serve.

    Three states, `--k 2` over a national mass of 2.0, so tau = 1.0, L = 0.8, U = 1.2.  S0
    carries WH 0.5 and FI 0.5: each below L on its own, 1.0 together and inside the band, and
    S0 is isolated in the rook graph, so no pure slot can reach it by way of a neighbour.  S2
    carries WH 1.2, which one pure WH slot serves on its own.  S1 carries the national mass.
    """
    rows = [
        ("z0", "S0", {"N_WH": (0.0, {}), "N_FI": (0.0, {}),
                      "WH": (0.5, {"rep0": 0.3}), "FI": (0.5, {"rep1": 0.3})}),
        ("z1", "S1", {"N_WH": (1.0, {"rep2": 0.3}), "N_FI": (1.0, {"rep3": 0.3}),
                      "WH": (0.0, {}), "FI": (0.0, {})}),
        ("z2", "S2", {"N_WH": (0.0, {}), "N_FI": (0.0, {}),
                      "WH": (1.2, {"rep4": 0.3}), "FI": (0.0, {})}),
    ]
    z, chan, m_rel, share, share_free, state = [], [], [], [], [], []
    for zid, st, cells in rows:
        for c in channels.CHANNELS:
            m, sh = cells[c]
            z.append(zid); chan.append(c); m_rel.append(m)
            share.append(dict(sh)); share_free.append(0.0); state.append(st)
    obj = dict(
        format=td_instance.FORMAT_V2,
        nodes=dict(z=z, channel=chan, m_rel=m_rel, share=share, share_free=share_free,
                   state=state),
        edges=dict(u=["z0", "z1"], v=["z1", "z2"]),
        meta=dict(channels=list(channels.CHANNELS)),
    )
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        json.dump(obj, fh)


def _passes_by_stage(plan: dict) -> dict:
    by_stage: dict[str, list[str]] = {}
    for rec in plan["passes"]:
        by_stage.setdefault(rec["stage"], []).append(rec["name"])
    return by_stage


def test_both_routes_open_a_merged_slot_for_what_the_pure_channels_cannot_serve():
    """`cover_merged`, the fourth coverage pass.  A WHFI slot used to enter no coverage
    objective, so route joint never opened a merged district (code verify R3, row 2b) and route
    sequential credited a merged slot in the same pass as a pure FI one.

    Both routes must now serve S0 with one WHFI slot, and the lexicographic order must hold:
    the pass runs after the pure ones, so S2, which a pure WH slot serves on its own, stays
    pure.
    """
    for route in ("joint", "sequential"):
        with tempfile.TemporaryDirectory() as tmp:
            inst = os.path.join(tmp, "inst.json.gz")
            _write_v2_merged(inst)
            out = os.path.join(tmp, f"out_{route}")
            orig = td_geo.state_rook
            td_geo.state_rook = lambda *a, **kw: (MERGED_ADJ, {})
            try:
                rc = cli.main([inst, "--route", route, "--driver", "geo",
                               "--bundles", "N,WH,FI,WHFI", "--engine", "scipy",
                               "--strategy", "direct", "--k", "2", "--time-limit", "30",
                               "--out", out])
                assert rc == 0, rc
            finally:
                td_geo.state_rook = orig

            with open(os.path.join(out, "plan.json"), encoding="utf-8") as fh:
                plan = json.load(fh)
            used = [rec for rec in plan["slots"] if rec["used"] and rec["y"]]
            merged = [rec for rec in used if rec["bundle"] == "WHFI"]
            assert len(merged) == 1, (route, used)
            assert set(merged[0]["y"]) == {"S0"}, (route, merged)
            assert abs(merged[0]["y"]["S0"] - 1.0) <= 1e-6, merged
            pure = [rec for rec in used if rec["bundle"] == "WH"]
            assert pure and all(set(rec["y"]) == {"S2"} for rec in pure), (route, pure)
            row = plan["per_state"]["S0"]["residual_by_channel"]
            assert abs(row["WH"]) <= 1e-6 and abs(row["FI"]) <= 1e-6, row

            # pure first, merged next, then the catch-all objective: within the stage that
            # carries the merged bundles, `cover_merged` sits after every other cover pass and
            # before contacts
            stage = [s for s, names in _passes_by_stage(plan).items()
                     if "cover_merged" in names]
            assert len(stage) == 1, plan["passes"]
            names = _passes_by_stage(plan)[stage[0]]
            i = names.index("cover_merged")
            assert all(names.index(n) < i for n in names if n.startswith("cover_")
                       and n != "cover_merged"), names
            assert i < names.index("contacts"), names


MOVE_ADJ = {"S0": ("S1", "S2"), "S1": ("S0",), "S2": ("S0", "S3"), "S3": ("S2",)}


def _write_v2_marginal(path: str) -> None:
    """Four states on the path S1 - S0 - S2 - S3, for `--cover-slack`.

    S3 carries the national mass 2.0, so at `--k 2` tau = 1.0, L = 0.8 and U = 1.2.  S1 carries
    WH 1.15 and S2 carries FI 1.15; S0 carries WH 0.05 and FI 0.05, which is what fills each of
    the two pure slots to U.  So S0 is 0.05 of the 1.2 a pure WH slot covers and 0.05 of the
    1.2 a pure FI slot covers, 4.2% of each: taking S0 out of both fits inside a 5% slack, and
    taking S1 or S2 out of theirs (95.8%) does not.
    """
    rows = [
        ("z0", "S0", {"N_WH": (0.0, {}), "N_FI": (0.0, {}),
                      "WH": (0.05, {"rep5": 0.5}), "FI": (0.05, {"rep6": 0.5})}),
        ("z1", "S1", {"N_WH": (0.0, {}), "N_FI": (0.0, {}),
                      "WH": (1.15, {"rep0": 0.4}), "FI": (0.0, {})}),
        ("z2", "S2", {"N_WH": (0.0, {}), "N_FI": (0.0, {}),
                      "WH": (0.0, {}), "FI": (1.15, {"rep1": 0.4})}),
        ("z3", "S3", {"N_WH": (1.0, {"rep2": 0.4}), "N_FI": (1.0, {"rep3": 0.4}),
                      "WH": (0.0, {}), "FI": (0.0, {})}),
    ]
    z, chan, m_rel, share, share_free, state = [], [], [], [], [], []
    for zid, st, cells in rows:
        for c in channels.CHANNELS:
            m, sh = cells[c]
            z.append(zid); chan.append(c); m_rel.append(m)
            share.append(dict(sh)); share_free.append(0.05); state.append(st)
    obj = dict(
        format=td_instance.FORMAT_V2,
        nodes=dict(z=z, channel=chan, m_rel=m_rel, share=share, share_free=share_free,
                   state=state),
        edges=dict(u=["z1", "z0", "z2"], v=["z0", "z2", "z3"]),
        meta=dict(channels=list(channels.CHANNELS)),
    )
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        json.dump(obj, fh)


def _run_marginal(tmp: str, cover_slack: float) -> dict:
    inst = os.path.join(tmp, "inst.json.gz")
    _write_v2_marginal(inst)
    out = os.path.join(tmp, f"out_{cover_slack}")
    orig = td_geo.state_rook
    td_geo.state_rook = lambda *a, **kw: (MOVE_ADJ, {})
    try:
        rc = cli.main([inst, "--route", "joint", "--driver", "reps",
                       "--bundles", "N,WH,FI,WHFI", "--cover-slack", str(cover_slack),
                       "--move-budget", "4", "--engine", "scipy", "--strategy", "direct",
                       "--k", "2", "--time-limit", "30", "--out", out])
        assert rc == 0, rc
    finally:
        td_geo.state_rook = orig
    with open(os.path.join(out, "plan.json"), encoding="utf-8") as fh:
        plan = json.load(fh)
    with open(os.path.join(out, "params.json"), encoding="utf-8") as fh:
        plan["params"] = json.load(fh)
    return plan


def test_cover_slack_is_what_lets_a_route_r_move_leave_a_pinned_cover_objective():
    """`--cover-slack EPS` widens each `pin_cover_*` row by `|v| EPS` for a move's re-solve.

    Route R's moves keep the cover pins -- without them minimising contacts closes every slot
    and the empty plan wins -- so at the exact pin any `merge_whfi` that takes a state's mass
    out of `cover_WH` or `cover_FI` is infeasible and route R is inert (code verify R3, row 4b).
    A merged slot's coverage counts in `cover_merged`, never in the pure objectives, so the
    slack a merge needs is the whole of that state's share of them: S0 is 4.2% of each here, so
    its merge is feasible and scored at 5%, while S1 and S2 carry 95.8% of theirs and are still
    refused.  Whether a scored merge is then accepted is a stage-2 question, not this flag's.

    The passes themselves are pinned exactly whatever EPS is, so the plan the coverage and
    contacts passes produce does not move: a run's slots are a property of the instance, and
    only the moves the driver may consider depend on the flag.
    """
    with tempfile.TemporaryDirectory() as tmp:
        pinned = _run_marginal(tmp, 0.0)
        assert pinned["params"]["cover_slack"] == 0.0
        exact = [m for m in pinned["moves"] if m["state"] == "S0" and m["move"] == "merge_whfi"]
        assert len(exact) == 1 and exact[0]["value"] is None, exact
        assert exact[0]["status"] == "infeasible", exact

        slacked = _run_marginal(tmp, 0.05)
        assert slacked["params"]["cover_slack"] == 0.05
        merged = [m for m in slacked["moves"]
                  if m["state"] == "S0" and m["move"] == "merge_whfi"]
        assert len(merged) == 1 and merged[0]["value"] is not None, merged

        # the base plan is the same at both, so a plan is comparable across EPS
        assert pinned["slots"] == slacked["slots"], "the passes are pinned exactly either way"

        # the slack is a budget, not a blanket relaxation: the two states that carry 95.8% of
        # a pure cover objective still cannot leave it
        for st in ("S1", "S2"):
            heavy = [m for m in slacked["moves"]
                     if m["state"] == st and m["move"] == "merge_whfi"]
            assert heavy and all(m["value"] is None for m in heavy), (st, heavy)

        # S3 carries national mass only, so at the exact pin `merge_whfi` forbids it nothing
        # and re-solves to the incumbent's own optimum.  The solver reports that a few ulps
        # above the incumbent, and an acceptance on a tie is a solver artefact, not the move.
        noop = [m for m in pinned["moves"] if m["state"] == "S3" and m["move"] == "merge_whfi"]
        keep = [m for m in pinned["moves"] if m["state"] == "S3" and m["move"] == "keep"]
        assert noop and keep and noop[0]["value"] is not None
        assert 0.0 < noop[0]["value"] - keep[0]["value"] < 1e-6, (noop, keep)
        assert not noop[0]["accepted"], noop
        assert not [m for m in slacked["moves"]
                    if m["state"] == "S3" and m["move"] == "merge_whfi" and m["accepted"]]


def _write_v1_uneven(path: str) -> list[float]:
    """One zip per state, masses `[4.5, 0.3 x 5]`, so a stage cannot cover everything.

    At `--k 2` this is tau = 3, L = 2.4, U = 3.6.  With `--n-max 1` only the heavy state can
    fill a slot at all, and only to `U / 4.5 = 0.8` of itself, so the first stage leaves a
    prior strictly inside (0, 1) -- which is what a double-counted prior needs in order to
    show.  On the even toy every stage covers its channels completely and the bug is invisible.
    """
    masses = [4.5, 0.3, 0.3, 0.3, 0.3, 0.3]
    zips = [f"{10000 + s * 10:05d}" for s in range(6)]
    reps = [f"rep{i}" for i in range(6)]
    obj = dict(
        format=td_instance.FORMAT,
        nodes=dict(z=zips, m_rel=list(masses),
                   share=[{reps[i]: 0.3, reps[(i + 1) % 6]: 0.2} for i in range(6)],
                   share_free=[0.1] * 6, state=list(STATES)),
        edges=dict(u=zips[:-1], v=zips[1:]),
    )
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        json.dump(obj, fh)
    return masses


def test_the_residual_is_one_minus_the_shares_actually_covered():
    """`run_stage` folds this solve's own `covered` into `prior`, never `1 - residual`.

    `Level0Problem.decode_zy` returns `residual = (1 - prior) - covered`, so folding
    `1 - residual` back would add `prior` a second time at every stage after the first.  The
    plan's `residual_by_channel` must equal one minus the shares the slots actually ask for,
    per state and per channel.  The toy is deliberately uncoverable (`_write_v1_uneven`): the
    even six-state toy has stage `seq_N` cover its channels completely, and a doubled prior
    clips to the same 1.0 there.
    """
    with tempfile.TemporaryDirectory() as tmp:
        inst = os.path.join(tmp, "inst.json.gz")
        _write_v1_uneven(inst)
        out = os.path.join(tmp, "out_residual")
        orig = td_geo.state_rook
        td_geo.state_rook = lambda *a, **kw: (PATH_ADJ, {})
        try:
            rc = cli.main([inst, "--synthesize", "--route", "sequential", "--driver", "geo",
                           "--n-max", "1", "--engine", "scipy", "--strategy", "direct",
                           "--k", "2", "--time-limit", "30", "--out", out])
            assert rc == 0, rc
        finally:
            td_geo.state_rook = orig

        with open(os.path.join(out, "plan.json"), encoding="utf-8") as fh:
            plan = json.load(fh)
        bundle_of = {rec["id"]: rec["bundle"] for rec in plan["slots"]}

        partial = 0
        for st, row in plan["per_state"].items():
            covered = {c: 0.0 for c in channels.CHANNELS}
            for slot_id, share in row.items():
                if slot_id == "residual_by_channel":
                    continue
                for c in channels.BUNDLES[bundle_of[slot_id]]:
                    covered[c] += float(share)
            for c, got in row["residual_by_channel"].items():
                assert abs(got - (1.0 - covered[c])) <= 1e-6, (st, c, got, covered[c])
                if 1e-6 < covered[c] < 1.0 - 1e-6:
                    partial += 1
        assert partial, "the toy must leave a prior strictly inside (0, 1) or it proves nothing"


def test_move_budget_caps_the_states_the_reps_driver_visits():
    """Every state costs a MILP per move, so an uncapped `--driver reps` is about 98 solves on
    the real 49.  The budget takes the heaviest states first and stops."""
    with tempfile.TemporaryDirectory() as tmp:
        inst = os.path.join(tmp, "inst.json.gz")
        _write_v1(inst)
        out = os.path.join(tmp, "out_budget")
        orig = td_geo.state_rook
        td_geo.state_rook = lambda *a, **kw: (PATH_ADJ, {})
        try:
            rc = cli.main([inst, "--synthesize", "--route", "sequential", "--driver", "reps",
                           "--move-budget", "2", "--engine", "scipy", "--strategy", "direct",
                           "--k", "2", "--time-limit", "30", "--out", out])
            assert rc == 0, rc
        finally:
            td_geo.state_rook = orig

        with open(os.path.join(out, "plan.json"), encoding="utf-8") as fh:
            plan = json.load(fh)
        visited = {m["state"] for m in plan["moves"]}
        assert len(visited) == 2, visited
        with open(os.path.join(out, "params.json"), encoding="utf-8") as fh:
            assert json.load(fh)["move_budget"] == 2


# ------------------------------------------------------------------------- the committed draw
# `--incumbency` and `--centers` read a committed `draw.csv` through
# `borders_report.load_committed`, which needs the confidential instance and the gazetteer.  The
# `Ctx` is built here by hand from a toy `draw.csv`, the way
# `tests/test_state_splits_cli.py::test_main_writes_timings_json_end_to_end` builds one, so the
# two helpers that read it are covered without either.
def _draw_csv(tmp: str, zips: list[str]) -> str:
    """`zip,district` over the toy: states S0..S2 are D01, S3..S5 are D02."""
    path = os.path.join(tmp, "draw.csv")
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["zip", "district"])
        for i, z in enumerate(zips):
            w.writerow([z, "D01" if i // 4 < 3 else "D02"])
    return path


def _toy_ctx(tmp: str, zips: list[str]):
    """A `borders_report.Ctx` over the six-state toy, labelled by a real `draw.csv`."""
    committed_full = us_maps.read_draw(_draw_csv(tmp, zips))
    labels0 = np.array([borders_report._label_of(committed_full[z]) for z in zips], int)
    state_idx = np.array([i // 4 for i in range(len(zips))], int)
    # one point per state, 100 km apart along a line, so the moments are not degenerate
    xy = np.array([[float(s) * 100.0, 0.0] for s in state_idx], float)
    M = np.ones(len(zips), float)
    k = int(labels0.max()) + 1
    home, owners = borders_report._owner_sets(labels0, state_idx, M, k, len(STATES))
    inst = os.path.join(tmp, "inst.json.gz")
    _write_v1(inst)
    return borders_report.Ctx(
        d=td_instance.load_descaled(inst), zips=zips, xy=xy, M=M, state_idx=state_idx,
        labels0=labels0, k=k, state_list=list(STATES),
        states_by_zip={z: STATES[i // 4] for i, z in enumerate(zips)},
        M_by_zip={z: 1.0 for z in zips}, missing=[], committed_full=committed_full,
        home=home, owners=owners, committed_rep_of=None)


def test_anchors_from_draw_put_committed_district_j_on_n_slot_start_plus_j():
    """`--incumbency`: district j of the committed draw is anchored in its home state, on the
    N bundle's slot `start + j`.  D01's mass is in S0..S2 and D02's in S3..S5, so the plurality
    home of district 0 is S0 and of district 1 is S3."""
    zips = [f"{10000 + s * 10 + i:05d}" for s in range(6) for i in range(4)]
    with tempfile.TemporaryDirectory() as tmp:
        ctx = _toy_ctx(tmp, zips)
        assert ctx.k == 2 and list(ctx.home) == [0, 3]

        assert cli._anchors_from_draw(ctx, STATES, 0, 5) == [(0, 0), (3, 1)]
        # the slot numbering is an offset, not a relabelling
        assert cli._anchors_from_draw(ctx, STATES, 3, 8) == [(0, 3), (3, 4)]
        # a bundle with room for one slot only anchors the district that fits
        assert cli._anchors_from_draw(ctx, STATES, 0, 1) == [(0, 0)]
        # a state the plan does not carry is dropped rather than mis-indexed
        assert cli._anchors_from_draw(ctx, ["S0", "S1"], 0, 5) == [(0, 0)]


def test_moments_from_draw_fill_only_the_n_slots():
    """`--centers`: only the N slots are the committed draw's own districts, so every other
    slot's column stays zero and carries no compactness tie-break."""
    zips = [f"{10000 + s * 10 + i:05d}" for s in range(6) for i in range(4)]
    with tempfile.TemporaryDirectory() as tmp:
        ctx = _toy_ctx(tmp, zips)
        D = cli._moments_from_draw(ctx, STATES, len(STATES), 5, 0, 2)

        assert D.shape == (len(STATES), 5)
        assert np.any(D[:, :2] > 0.0), "the two N slots must carry moments"
        assert not np.any(D[:, 2:]), "a non-N slot has no committed centre"
        # a state's moment is about the centre of the district it was drawn into, so every
        # state has a positive moment on one of the two columns
        assert np.all(D[:, :2].max(axis=1) > 0.0)
        # the same moments land on an offset N range and nowhere else
        shifted = cli._moments_from_draw(ctx, STATES, len(STATES), 5, 2, 4)
        assert np.allclose(shifted[:, 2:4], D[:, :2])
        assert not np.any(shifted[:, :2]) and not np.any(shifted[:, 4:])


def test_incumbency_and_centers_reach_an_end_to_end_run():
    """Both flags through `main`, with `load_committed` monkeypatched the way
    `tests/test_state_splits_cli.py` patches it.  `--centers` is what makes a compactness pass
    run at all (`_pass_list` adds it only for a nonzero D)."""
    zips = [f"{10000 + s * 10 + i:05d}" for s in range(6) for i in range(4)]
    with tempfile.TemporaryDirectory() as tmp:
        ctx = _toy_ctx(tmp, zips)
        draw = os.path.join(tmp, "draw.csv")
        inst = os.path.join(tmp, "inst.json.gz")
        out = os.path.join(tmp, "out")

        orig_load, orig_rook = borders_report.load_committed, td_geo.state_rook
        borders_report.load_committed = lambda *a, **kw: ctx
        td_geo.state_rook = lambda *a, **kw: (PATH_ADJ, {})
        try:
            rc = cli.main([inst, "--synthesize", "--route", "sequential", "--driver", "geo",
                           "--incumbency", draw, "--centers", draw,
                           "--engine", "scipy", "--strategy", "direct", "--k", "2",
                           "--time-limit", "30", "--out", out])
            assert rc == 0, rc
        finally:
            borders_report.load_committed, td_geo.state_rook = orig_load, orig_rook

        plan = _check_plan(out)
        assert any("compactness" in p["name"] for p in plan["passes"]), \
            "--centers must add a compactness pass"
        with open(os.path.join(out, "params.json"), encoding="utf-8") as fh:
            params = json.load(fh)
        assert params["incumbency"] == os.path.abspath(draw)
        assert params["centers"] == os.path.abspath(draw)
        # the anchors are `var_lb[z_sj] = 1`, so district 0's home state must be on N slot 0
        # and district 1's on N slot 1 -- not merely somewhere in the plan, which holds on
        # this toy anyway because cover_N is full
        n_slots = [rec for rec in plan["slots"] if rec["bundle"] == "N"]
        assert len(n_slots) >= 2
        assert "S0" in n_slots[0]["y"], n_slots[0]
        assert "S3" in n_slots[1]["y"], n_slots[1]


def test_centers_seeds_leaves_the_committed_draw_the_n_slots_it_named():
    """`--centers seeds --incumbency draw.csv`: the N slots the committed draw drew keep their
    own centres, and every other used slot takes its greedy seed.  The draw knows where its
    districts sit better than a seed does; the bundles it never drew had no tie-break at all
    before this.  The model handed to `solve_passes` is captured to read `D`.
    """
    from td.solvers import level0

    zips = [f"{10000 + s * 10 + i:05d}" for s in range(6) for i in range(4)]
    seen = []
    orig_solve = level0.solve_passes

    def capture(problem, passes, **kw):
        seen.append(problem)
        return orig_solve(problem, passes, **kw)

    with tempfile.TemporaryDirectory() as tmp:
        ctx = _toy_ctx(tmp, zips)
        draw = os.path.join(tmp, "draw.csv")
        inst = os.path.join(tmp, "inst.json.gz")
        out = os.path.join(tmp, "out")
        orig_load, orig_rook = borders_report.load_committed, td_geo.state_rook
        borders_report.load_committed = lambda *a, **kw: ctx
        td_geo.state_rook = lambda *a, **kw: (PATH_ADJ, PATH_POLYS)
        level0.solve_passes = capture
        try:
            rc = cli.main([inst, "--synthesize", "--route", "joint", "--driver", "geo",
                           "--incumbency", draw, "--centers", "seeds",
                           "--engine", "scipy", "--strategy", "direct", "--k", "2",
                           "--time-limit", "30", "--out", out])
            assert rc == 0, rc
        finally:
            borders_report.load_committed, td_geo.state_rook = orig_load, orig_rook
            level0.solve_passes = orig_solve

        plan = _check_plan(out)
        assert len(seen) == 1, "route joint is one model, and one build after the greedy"
        problem = seen[0]
        start, stop = problem.slots["N"]
        drawn = cli._moments_from_draw(ctx, STATES, len(STATES), problem.k, start, stop)
        assert np.allclose(problem.D[:, start:start + ctx.k], drawn[:, start:start + ctx.k])
        assert np.any(drawn[:, start:start + ctx.k] > 0.0)
        # every other used slot is centred on a state, so its column is zero exactly there
        seeded = [j for j in range(problem.k) if j >= start + ctx.k and problem.D[:, j].any()]
        assert seeded, "the bundles the draw never drew must take their seeds"
        idx = {c: i for i, c in enumerate(STATES)}
        for j in seeded:
            centre = plan["slots"][j]["center"]
            assert centre is not None and problem.D[idx[centre], j] == 0.0
        with open(os.path.join(out, "params.json"), encoding="utf-8") as fh:
            params = json.load(fh)
        assert params["centers"] == "seeds" and params["incumbency"] == os.path.abspath(draw)


def test_synthesize_writes_the_v2_instance_it_solved():
    """A synthetic run is only reproducible if the instance it invented is on disk beside the
    plan (trap 22's rule for a gazetteer vintage applies to a synthesized split too)."""
    with tempfile.TemporaryDirectory() as tmp:
        out = _run(tmp, "sequential")
        v2 = os.path.join(out, "instance_v2.json.gz")
        assert os.path.exists(v2)
        d = td_instance.load_descaled(v2)
        assert d.channels
