"""test_plan_compose.py: tools/plan_compose.py on three hand-built single-bundle runs.

Six zips over three states A, B, C, three reps, and one `tools/full_plan.py` run per bundle:
`N` taking all of A and half of B, `WH` and `FI` each taking all three states.  That is the
shape the decomposition of `docs/FULL_PROBLEM.md` section 4 promises a grid can run one channel
at a time and assemble here, and it is small enough that every number the compose reports can be
recomputed in the test.

Three used slots and three reps, so "each district staffed once, no rep held twice" is a real
assertion rather than a consequence of a short rep pool. With more slots than reps
`channel.match` leaves districts unstaffed by design.

The joint Hungarian is checked against a brute force over every injection of reps into slots on
the gain matrix `td.stage2_state.state_gain_matrix` builds, not against another matching code
path.  `--realise` is a smoke test with `plan_compose.run_tool` replaced by a recorder: this
test never runs level 2.
"""
from __future__ import annotations

import csv
import gzip
import itertools
import json
import math
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
for _p in (HERE, os.path.join(ROOT, "tools"), ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np                                  # noqa: E402

from td import channels, stage2_state               # noqa: E402
from td import instance as td_instance              # noqa: E402
import full_plan                                    # noqa: E402
import plan_compose as cli                          # noqa: E402

ZIPS = [f"{10000 + i:05d}" for i in range(6)]
STATES = ["A", "A", "B", "B", "C", "C"]
STATE_LIST = ["A", "B", "C"]
REPS = ["rep0", "rep1", "rep2"]

# one run per bundle: N takes A whole and half of B, WH and FI take everything
RUNS = [("stage_N", "N", {"A": 1.0, "B": 0.5}),
        ("stage_WH", "WH", {"A": 1.0, "B": 1.0, "C": 1.0}),
        ("stage_FI", "FI", {"A": 1.0, "B": 1.0, "C": 1.0})]

BAND = (0.5, 2.0)


def _base_instance(path: str) -> None:
    """A format-1 file: six unit-mass zips on a path, two reps holding book on each."""
    share = {z: {REPS[i % 3]: 0.3, REPS[(i + 1) % 3]: 0.2} for i, z in enumerate(ZIPS)}
    obj = dict(
        format=td_instance.FORMAT,
        nodes=dict(z=ZIPS, m_rel=[1.0] * 6, share=[share[z] for z in ZIPS], state=STATES,
                   share_free=[0.1] * 6),
        edges=dict(u=ZIPS[:-1], v=ZIPS[1:]),
    )
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        json.dump(obj, fh)


def _instance(root: str):
    """The per-cell instance every run planned against, and its fine-label form."""
    base = os.path.join(root, "base.json.gz")
    _base_instance(base)
    v2 = channels.synthesize_channels(td_instance.load_descaled(base), seed=0)
    path = os.path.join(root, "instance_v2.json.gz")
    channels.write_v2(v2, path)
    return path, channels.fine_split(v2)


def _write_run(run_dir: str, bundle: str, y: dict, instance: str, fine, *,
               band=BAND, slot_id: str = "P001") -> None:
    """The four things `tools/full_plan.py` leaves behind, for a one-slot run."""
    cell = os.path.join(run_dir, "projections", bundle)
    os.makedirs(cell, exist_ok=True)
    chans = full_plan._bundle_channels(bundle)
    proj = channels.project(fine, bundle, states=sorted(y))
    channels.write_v1(proj, os.path.join(cell, "instance_descaled.json.gz"))

    cells = channels.aggregate(fine, STATE_LIST)
    cidx = {c: i for i, c in enumerate(cells.channels)}
    M_B = np.asarray(cells.M, float)[:, [cidx[c] for c in chans]].sum(axis=1)
    with open(os.path.join(cell, "state_shares.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["state", "district", "share", "target_mass"])
        for st, share in sorted(y.items()):
            w.writerow([st, "D01", share, M_B[STATE_LIST.index(st)] * share])

    mass = float(sum(M_B[STATE_LIST.index(st)] * sh for st, sh in y.items()))
    slots = [dict(id=slot_id, bundle=bundle, used=True, mass=mass, contacts=len(y), y=dict(y),
                  center=sorted(y)[0], extent_km=None, radius_km=None)]
    plan = dict(state_list=STATE_LIST, bundles=[bundle], slots=slots, per_state={},
                passes=[dict(name=f"cover_{bundle}", value=1.0, certified=True, stage="joint")],
                moves=[], anchors=[])
    params = dict(instance=instance, state_list=STATE_LIST, channels=list(cells.channels),
                  bundles=[bundle], k=3, band_lo=0.5, band_hi=2.0,
                  L=band[0], U=band[1], synthesize=False, seed=0)
    staffing = dict(assignment={"0": "rep0"}, gains={"0": 1.0}, value=0.0, criterion="nash",
                    reps=list(REPS), districts=[0], unmatched_reps=REPS[1:],
                    unstaffed_districts=[], balance={})
    for name, obj in (("plan.json", plan), ("params.json", params),
                      ("staffing.json", staffing)):
        with open(os.path.join(run_dir, name), "w", encoding="utf-8") as fh:
            json.dump(obj, fh)


def _build(root: str, runs=RUNS):
    """One run directory per entry of `runs`; returns the instance path and the directories."""
    instance, fine = _instance(root)
    dirs = []
    for name, bundle, y in runs:
        run_dir = os.path.join(root, name)
        os.makedirs(run_dir, exist_ok=True)
        _write_run(run_dir, bundle, y, instance, fine)
        dirs.append(run_dir)
    return instance, fine, dirs


def _compose(root: str, *, runs=RUNS, extra=()) -> str:
    instance, _, dirs = _build(root, runs)
    out = os.path.join(root, "composed")
    assert cli.main(["--out", out, "--instance", instance, *dirs, *extra]) == 0
    return out


def _read(out: str, name: str) -> dict:
    with open(os.path.join(out, name), encoding="utf-8") as fh:
        return json.load(fh)


def test_the_union_is_every_input_s_used_slots_with_unique_ids():
    """Three runs that each numbered their one slot `P001` compose to three distinct slots.

    Order is each input's own order inside its bundles, because that is what
    `tools/plan_realise.py::used_by_bundle` uses to line a slot up with the district column of
    the `state_shares.csv` copied beside it.
    """
    with tempfile.TemporaryDirectory() as root:
        plan = _read(_compose(root), "plan.json")

        assert [rec["id"] for rec in plan["slots"]] == ["N:P001", "WH:P001", "FI:P001"]
        assert [rec["bundle"] for rec in plan["slots"]] == ["N", "WH", "FI"]
        assert plan["bundles"] == ["FI", "N", "WH"]
        assert all(rec["used"] for rec in plan["slots"])
        assert [rec["run"] for rec in plan["slots"]] == ["stage_N", "stage_WH", "stage_FI"]
        assert [s["name"] for s in plan["sources"]] == ["stage_N", "stage_WH", "stage_FI"]
        assert [p["run"] for p in plan["passes"]] == ["stage_N", "stage_WH", "stage_FI"]
        assert plan["sources"][0]["params"]["k"] == 3, "each source carries its own params"


def test_residual_by_channel_is_recomputed_against_the_union():
    """A state's residual on a channel is 1 less what the union's slots take of it.

    Each input saw its own bundle only, so no input's `residual_by_channel` is the answer: the
    N run leaves WH and FI wholly residual and the WH run leaves N_WH residual.  Only the
    compose can see that B keeps half its national mass and C keeps all of it.
    """
    with tempfile.TemporaryDirectory() as root:
        plan = _read(_compose(root), "plan.json")
        resid = {st: plan["per_state"][st]["residual_by_channel"] for st in STATE_LIST}

        assert resid["A"] == {"N_WH": 0.0, "N_FI": 0.0, "WH": 0.0, "FI": 0.0}
        assert resid["B"] == {"N_WH": 0.5, "N_FI": 0.5, "WH": 0.0, "FI": 0.0}
        assert resid["C"] == {"N_WH": 1.0, "N_FI": 1.0, "WH": 0.0, "FI": 0.0}

        # the per-slot shares survive beside the residual, keyed by the composed id
        assert plan["per_state"]["A"]["N:P001"] == 1.0
        assert plan["per_state"]["C"].get("N:P001") is None
        assert plan["per_state"]["B"]["WH:P001"] == 1.0


def test_an_overlapping_pair_is_refused_and_allow_overlap_composes_it():
    """`WH_PLUS` carries `N_WH`, so a WH_PLUS run beside an N run takes one cell twice.

    Level 0's cover row is per run, so neither run can see it; the per-bundle projections cannot
    express it either, which is why the refusal is here and not a warning.
    """
    runs = [("stage_N", "N", {"A": 1.0, "B": 0.5}),
            ("stage_WHP", "WH_PLUS", {"A": 1.0, "B": 1.0, "C": 1.0})]
    with tempfile.TemporaryDirectory() as root:
        try:
            _compose(root, runs=runs)
        except ValueError as exc:
            assert "--allow-overlap" in str(exc) and "two inputs" in str(exc), exc
        else:
            raise AssertionError("an overlapping pair must be refused")

    with tempfile.TemporaryDirectory() as root:
        plan = _read(_compose(root, runs=runs, extra=["--allow-overlap"]), "plan.json")
        cells = {(row["state"], row["channel"]) for row in plan["overlaps"]}
        assert cells == {("A", "N_WH"), ("B", "N_WH")}, cells
        assert all(row["share"] > 1.0 - 1e-9 for row in plan["overlaps"])
        # A takes N_WH from both runs, so its residual clips at 0 rather than going negative
        assert plan["per_state"]["A"]["residual_by_channel"]["N_WH"] == 0.0


def test_two_inputs_over_one_bundle_are_refused():
    """The projections of a shared bundle would overwrite each other in the composed run."""
    runs = [("stage_N", "N", {"A": 1.0}), ("stage_N2", "N", {"B": 1.0})]
    with tempfile.TemporaryDirectory() as root:
        try:
            _compose(root, runs=runs)
        except ValueError as exc:
            assert "disjoint bundles" in str(exc), exc
        else:
            raise AssertionError("two runs over one bundle must be refused")


def test_one_hungarian_over_the_union_staffs_each_district_once():
    """The union's staffing is one injection, and its value is the optimum of the gain matrix.

    Each input staffed its own channel from the whole pool and all three picked `rep0`; the
    union cannot, and the report says so.  The optimum is brute-forced over every injection of
    the three reps into the three slots, which is the definition `channel.match` implements.
    """
    with tempfile.TemporaryDirectory() as root:
        out = _compose(root)
        plan, staffing = _read(out, "plan.json"), _read(out, "staffing.json")

        assign = {int(k): v for k, v in staffing["assignment"].items()}
        assert sorted(assign) == [0, 1, 2], "every used slot is a column, keyed by its index"
        assert len(set(assign.values())) == 3, "no rep holds two districts"
        assert staffing["unstaffed_districts"] == [] and staffing["unmatched_reps"] == []

        fine = channels.fine_split(
            td_instance.load_descaled(_read(out, "params.json")["instance"]))
        cells = channels.aggregate(fine, STATE_LIST)
        g, R, slot_ids = stage2_state.state_gain_matrix(
            cells, full_plan._plan_object(plan["slots"], STATE_LIST),
            theta=0.40, lam=0.30, filler_capture="theta")
        assert g.shape == (3, 3) and slot_ids == [0, 1, 2]
        best = max(sum(math.log(g[i, j]) for j, i in enumerate(perm))
                   for perm in itertools.permutations(range(len(R)), len(slot_ids)))
        assert abs(staffing["value"] - best) < 1e-9
        for j, rep in assign.items():
            assert abs(staffing["gains"][str(j)] - g[R.index(rep), j]) < 1e-12


def test_the_projections_are_copied_into_the_composed_run():
    """`tools/plan_realise.py` reads the composed directory, so the projections must be in it.

    Copied, not linked: the driver caches each bundle's contiguity graph inside the projection
    directory and a link would put that cache in an input run.
    """
    with tempfile.TemporaryDirectory() as root:
        out = _compose(root)
        for bundle in ("N", "WH", "FI"):
            cell = os.path.join(out, "projections", bundle)
            assert not os.path.islink(cell)
            for name in ("instance_descaled.json.gz", "state_shares.csv"):
                assert os.path.exists(os.path.join(cell, name)), (bundle, name)
        with open(os.path.join(out, "projections", "N", "state_shares.csv"),
                  encoding="utf-8", newline="") as fh:
            rows = list(csv.DictReader(fh))
        assert {r["state"] for r in rows} == {"A", "B"}


def test_a_missing_projection_names_the_input_that_owes_it():
    with tempfile.TemporaryDirectory() as root:
        instance, _, dirs = _build(root)
        os.remove(os.path.join(dirs[1], "projections", "WH", "state_shares.csv"))
        try:
            cli.main(["--out", os.path.join(root, "composed"), "--instance", instance, *dirs])
        except FileNotFoundError as exc:
            assert dirs[1] in str(exc) and "state_shares.csv" in str(exc), exc
        else:
            raise AssertionError("a missing projection must refuse the compose")


def test_the_band_is_carried_only_when_the_inputs_agree():
    """Two runs at different `k` have different `[L, U]` and the union has no one band."""
    with tempfile.TemporaryDirectory() as root:
        params = _read(_compose(root), "params.json")
        assert (params["L"], params["U"]) == BAND
        assert params["driver"] == "plan_compose"
        assert params["filler_capture"] == "theta" and params["theta"] == 0.40
        assert len(params["inputs"]) == 3

    with tempfile.TemporaryDirectory() as root:
        instance, fine, dirs = _build(root)
        _write_run(dirs[2], "FI", RUNS[2][2], instance, fine, band=(0.1, 9.0))
        out = os.path.join(root, "composed")
        assert cli.main(["--out", out, "--instance", instance, *dirs]) == 0
        params = _read(out, "params.json")
        assert params["L"] is None and params["U"] is None
        assert set(params["bands_by_input"]) == {"stage_N", "stage_WH", "stage_FI"}


def test_realise_and_maps_drive_the_downstream_tools():
    """`--realise` hands the composed directory to level 2; `--maps` implies it."""
    calls = []
    orig = cli.run_tool
    cli.run_tool = lambda name, argv: (calls.append((name, list(argv))), 0)[1]
    try:
        with tempfile.TemporaryDirectory() as root:
            out = _compose(root, extra=["--realise", "--geo-cache", "unused"])
            assert calls == [("plan_realise.py", [out, "--geo-cache", "unused"])]
        calls.clear()
        with tempfile.TemporaryDirectory() as root:
            out = _compose(root, extra=["--maps", "--geo-cache", "unused"])
            assert [n for n, _ in calls] == ["plan_realise.py", "plan_maps.py",
                                             "plan_summary.py"]
            assert calls[-1][1] == [out]
    finally:
        cli.run_tool = orig


def test_a_tool_that_has_not_landed_is_skipped_not_raised():
    """A compose that asked for a driver written on a sibling track must not die after the
    plan is already on disk."""
    assert cli.run_tool("no_such_driver.py", ["x"]) == 0
