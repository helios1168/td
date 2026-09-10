"""test_plan_to_app.py: tools/plan_to_app.py on a hand-built realised plan run.

Six zips over three states and two bundles: `N` with two used slots, `WH` with one that covers
only half of C, so one zip is uncovered and reads `other` in `assignment.csv` -- the case the
zip table has to turn back into an empty district.  Three members come out, one per business
channel: national (the `N` bundle's two districts), wh (one), and fi, which no slot serves and
which is therefore a map of zips in no district.  The gazetteer is monkeypatched away the way
`tests/test_plan_realise.py` does it, and `launch_geom` is stubbed, so the test needs no cache,
no shapefile and no ZCTA polygons.
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
for _p in (HERE, os.path.join(ROOT, "tools"), ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from app import store                                # noqa: E402
from td import channels                              # noqa: E402
from td import instance as td_instance               # noqa: E402
import plan_to_app as cli                            # noqa: E402
import run_draw                                      # noqa: E402

ZIPS = [f"{10000 + i:05d}" for i in range(6)]
STATES = ["A", "A", "B", "B", "C", "C"]
REPS = ["rep0", "rep1", "rep2"]
XY = {z: (float(i), 0.0) for i, z in enumerate(ZIPS)}

# bundle N takes every zip, two slots; WH takes all but the last, one slot
LABELS = {"N": ["N_01", "N_01", "N_01", "N_02", "N_02", "N_02"],
          "WH": ["WH_01"] * 5 + [""]}
REP_OF = {"N_01": "rep0", "N_02": "rep1", "WH_01": "rep2"}


class _Done:
    """What `launch_geom` returns, minus the process."""

    def wait(self) -> int:
        return 0


def _base_instance(path: str) -> None:
    share = {z: {REPS[i % 3]: 0.3, REPS[(i + 1) % 3]: 0.2} for i, z in enumerate(ZIPS)}
    obj = dict(
        format=td_instance.FORMAT,
        nodes=dict(z=ZIPS, m_rel=[1.0] * 6, share=[share[z] for z in ZIPS], state=STATES,
                   share_free=[0.1] * 6),
        edges=dict(u=ZIPS[:-1], v=ZIPS[1:]),
    )
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        json.dump(obj, fh)


def _build_run(run_dir: str) -> None:
    """What `full_plan.py` and `plan_realise.py` leave behind, for this toy plan."""
    base = os.path.join(run_dir, "base.json.gz")
    _base_instance(base)
    fine = channels.fine_split(channels.synthesize_channels(
        td_instance.load_descaled(base), seed=0))
    for bundle in ("N", "WH", "FI"):
        cell = os.path.join(run_dir, "projections", bundle)
        os.makedirs(cell, exist_ok=True)
        channels.write_v1(channels.project(fine, bundle, states=["A", "B", "C"]),
                          os.path.join(cell, "instance_descaled.json.gz"))

    slots = [dict(id="P001", bundle="N", used=True, mass=3.0, contacts=2, y={"A": 1.0, "B": 0.5}),
             dict(id="P002", bundle="N", used=True, mass=3.0, contacts=2,
                  y={"B": 0.5, "C": 1.0}),
             dict(id="P003", bundle="WH", used=True, mass=2.5, contacts=2,
                  y={"A": 1.0, "B": 1.0, "C": 0.5}),
             dict(id="P004", bundle="WH", used=False, mass=0.0, contacts=0, y={})]
    _write(run_dir, "plan.json", dict(state_list=["A", "B", "C"], bundles=["N", "WH"],
                                      slots=slots, per_state={}, passes=[], moves=[]))
    _write(run_dir, "staffing.json",
           dict(assignment={"0": "rep0", "1": "rep1", "2": "rep2"},
                gains={"0": 1.5, "1": 2.5, "2": 4.0}, value=8.0, criterion="nash", reps=REPS,
                districts=[0, 1, 2], unmatched_reps=[], unstaffed_districts=[], balance={}))
    _write(run_dir, "params.json", dict(instance=base, band_lo=0.8, band_hi=1.2, theta=0.4,
                                        lam=0.3, filler_capture="theta"))
    _write(run_dir, "timings.json", dict(driver="full_plan", wall=1.0, phases=[]))
    _write(run_dir, "realise.json", dict(
        run_dir=run_dir, rounds=5, overlaps=[], districts=[],
        bundles={"N": dict(status="ok", k=2, split_states=["B"], n_fractional=1,
                           residual_zips=0),
                 "WH": dict(status="ok", k=1, split_states=[], n_fractional=0,
                            residual_zips=1)}))

    with open(os.path.join(run_dir, "assignment.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["zip", "state", "channel", "file_channel", "district", "bundle",
                    "wholesaler", "M_cell"])
        for i, zp in enumerate(ZIPS):
            for c in ("N_WH", "N_FI"):
                name = LABELS["N"][i]
                w.writerow([zp, STATES[i], c, "national", name, "N", REP_OF[name], 1.0])
            name = LABELS["WH"][i]
            # an uncovered cell carries the pseudo-district and no bundle at all
            w.writerow([zp, STATES[i], "WH", "wh", name or "other", "WH" if name else "",
                        REP_OF.get(name, ""), 1.0])
            w.writerow([zp, STATES[i], "FI", "fi", "other", "", "", 1.0])


def _write(run_dir: str, name: str, obj) -> None:
    with open(os.path.join(run_dir, name), "w", encoding="utf-8") as fh:
        json.dump(obj, fh)


def _run(run_dir: str, out: str, *extra: str) -> None:
    coords, geom = run_draw.coordinates, cli.launch_geom
    run_draw.coordinates = lambda zips, cache=None: ({z: XY[z] for z in zips if z in XY},
                                                     [z for z in zips if z not in XY])
    cli.launch_geom = lambda python, table, run, geo_cache: _Done()
    try:
        assert cli.main([run_dir, "--name", "Toy Plan!", "--app-results", out,
                         "--geo-cache", "unused", *extra]) == 0
    finally:
        run_draw.coordinates, cli.launch_geom = coords, geom


def _rows(path) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def test_one_clip_run_per_channel_under_one_scenario():
    """Three channels, three runs, all `clip` (the kind the Map tab treats as the result) and
    all under the one slugified scenario, one member each. The member name carries the channel
    and the district count that channel's own map has."""
    with tempfile.TemporaryDirectory() as tmp:
        run_dir, out = os.path.join(tmp, "run"), os.path.join(tmp, "app")
        os.makedirs(run_dir)
        _build_run(run_dir)
        _run(run_dir, out)

        runs = store.discover(out)
        assert len(runs) == 3
        assert {store.read_step(r)["kind"] for r in runs} == {"clip"}
        assert {store.scenario_of(r, out) for r in runs} == {"toy-plan"}
        members = dict(store.members(out, "toy-plan"))
        assert sorted(members) == ["toy-plan_fi_k0_d20", "toy-plan_national_k2_d20",
                                   "toy-plan_wh_k1_d20"]
        assert all(len(v) == 1 for v in members.values())
        assert store.member_label("toy-plan_national_k2_d20") == "national · k2 · d20"


def test_the_table_carries_every_zip_with_its_label_and_rep():
    """The bundle's own labels and staffed reps, and the zip no slot serves reading empty: an
    unplaced zip is not district `other`, it is a zip with no district."""
    with tempfile.TemporaryDirectory() as tmp:
        run_dir, out = os.path.join(tmp, "run"), os.path.join(tmp, "app")
        os.makedirs(run_dir)
        _build_run(run_dir)
        _run(run_dir, out)

        by_member = {m: runs[0] for m, runs in store.members(out, "toy-plan")}
        for member, bundle in (("toy-plan_national_k2_d20", "N"), ("toy-plan_wh_k1_d20", "WH")):
            rows = _rows(store.table_path(by_member[member]))
            assert [r["zip"] for r in rows] == ZIPS
            assert [r["district"] for r in rows] == LABELS[bundle]
            assert [r["rep"] for r in rows] == [REP_OF.get(d, "") for d in LABELS[bundle]]
            assert [r["state"] for r in rows] == STATES


def test_the_step_carries_what_the_app_reads_back():
    """`instance_of` resolves through `params.instance`, `k_of` through `params.k`, and the
    metrics file holds the keys the Map tab's clip branch reads."""
    with tempfile.TemporaryDirectory() as tmp:
        run_dir, out = os.path.join(tmp, "run"), os.path.join(tmp, "app")
        os.makedirs(run_dir)
        _build_run(run_dir)
        _run(run_dir, out)

        run = dict(store.members(out, "toy-plan"))["toy-plan_national_k2_d20"][0]
        params = store.read_step(run)["params"]
        assert params["channel"] == "national" and params["bundles"] == ["N"]
        assert params["k"] == 2 and params["plan_run"] == run_dir
        assert os.path.exists(params["instance"])
        assert store.k_of(run, out) == 2
        assert store.read_view(run)["default_for"] == "toy-plan_national_k2_d20"
        assert (run / "timings.json").exists()

        with open(store.metrics_path(run), encoding="utf-8") as fh:
            metrics = json.load(fh)
        assert metrics["splits"] == 1 and metrics["split_states"] == ["B"]
        assert metrics["certified_splits"] is False
        assert metrics["stage2_value"] == 4.0            # slots 0 and 1, gains 1.5 + 2.5
        assert metrics["stage2_theta"] == 0.4 and metrics["stage2_filler"] == "theta"


def test_channels_selects_a_subset():
    with tempfile.TemporaryDirectory() as tmp:
        run_dir, out = os.path.join(tmp, "run"), os.path.join(tmp, "app")
        os.makedirs(run_dir)
        _build_run(run_dir)
        _run(run_dir, out, "--channels", "wh")

        runs = store.discover(out)
        assert len(runs) == 1
        assert store.read_step(runs[0])["params"]["channel"] == "wh"
