"""test_app_store.py -- app/store.py and app/steps.py: the run-directory ledger and the argv
builders that feed it.

Every run directory in this file is a fake, built by hand or through `store.write_step`, never
by actually invoking a driver (none of `run_draw.py`, `state_splits.py`, `geom_export.py`,
`staff.py`, `override.py` or `split_district.py` need exist for these to pass): `grid` only has
to produce the right directories, `step.json` contents and argv, and `launch_chain` only has to
run whatever argv it is given. `true` and `sh -c 'echo hi'` stand in for a driver.

No Streamlit or pandas import, same as `test_app_runner.py`, so this runs under the solver venv.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app import runner, steps, store           # noqa: E402


def _mkstep(run: Path, **outputs) -> dict:
    run.mkdir(parents=True, exist_ok=True)
    return store.write_step(run, kind="draw", parent=None, params={}, argv=["x"],
                            outputs=outputs)


# ------------------------------------------------------------------------------ new_run_dir
def test_new_run_dir_names_are_unique_even_back_to_back():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        paths = [store.new_run_dir(root, "draw", "collide") for _ in range(4)]
        assert len(set(paths)) == 4
        for p in paths:
            assert p.is_dir()
            assert p.name.startswith("draw_collide_")


def test_new_run_dir_slugifies():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        p = store.new_run_dir(root, "clip", "Grid Run #7 (VT)")
        assert "grid-run-7-vt" in p.name
        assert p.name.startswith("clip_")


# ------------------------------------------------------------------------------ step.json I/O
def test_write_read_update_step_round_trip():
    with tempfile.TemporaryDirectory() as tmp:
        run = Path(tmp) / "draw_x_1"
        run.mkdir()
        written = store.write_step(run, kind="draw", parent=None, params={"k": 18},
                                   argv=["a", "b"], outputs={"table": "k18/draw.csv"})
        assert written["pid"] is None and written["started"] is None
        assert store.read_step(run) == written

        updated = store.update_step(run, pid=4242, started="2026-09-08T00:00:00")
        assert updated["pid"] == 4242
        assert updated["kind"] == "draw"                # untouched fields survive the merge
        assert store.read_step(run)["pid"] == 4242


# ------------------------------------------------------------------------------ discover
def test_discover_orders_newest_first_by_name():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        names = ["draw_x_20260101_000000", "draw_x_20260101_000001", "draw_x_20260101_000002"]
        for n in names:
            _mkstep(root / n, table=f"{n}/draw.csv")
        (root / "not_a_run").mkdir()                     # no step.json: must not appear
        found = store.discover(root)
        assert [p.name for p in found] == list(reversed(names))


def test_discover_on_missing_root_is_empty():
    assert store.discover(Path("/no/such/root/at/all")) == []


# ------------------------------------------------------------------------------ status
def test_status_queued_running_done_failed():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)

        q = root / "draw_q_1"
        _mkstep(q, table="k18/draw.csv")
        assert store.status(q) == "queued"

        r = root / "draw_r_1"
        _mkstep(r, table="k18/draw.csv")
        proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(5)"])
        try:
            store.update_step(r, pid=proc.pid, started="now")
            assert store.status(r) == "running"
        finally:
            proc.kill()
            proc.wait()

        d = root / "draw_d_1"
        _mkstep(d, table="k18/draw.csv")
        (d / "k18").mkdir()
        (d / "k18" / "draw.csv").write_text("zip\n")
        assert store.status(d) == "done"                 # table wins regardless of pid

        f = root / "draw_f_1"
        _mkstep(f, table="k18/draw.csv")
        dead = subprocess.Popen([sys.executable, "-c", "pass"])
        dead.wait()                                       # fully reaped: os.kill must fail now
        store.update_step(f, pid=dead.pid, started="now")
        assert store.status(f) == "failed"

        f2 = root / "draw_f_2"
        _mkstep(f2, table="k18/draw.csv")
        (f2 / store.FAILURE).write_text(json.dumps({"reason": "infeasible"}))
        assert store.status(f2) == "failed"
        assert store.failure(f2) == {"reason": "infeasible"}
        assert store.failure(q) is None


# ------------------------------------------------------------------------------ lineage / children
def test_lineage_and_children_over_a_three_deep_chain():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        a = root / "draw_a_1"
        b = root / "clip_b_1"
        c = root / "staff_c_1"
        a.mkdir(); b.mkdir(); c.mkdir()
        store.write_step(a, kind="draw", parent=None, params={}, argv=[], outputs={})
        store.write_step(b, kind="clip", parent=a.name, params={}, argv=[], outputs={})
        store.write_step(c, kind="staff", parent=b.name, params={}, argv=[], outputs={})

        assert store.lineage(c, root) == [a, b, c]
        assert store.lineage(a, root) == [a]
        assert store.children(a, root) == [b]
        assert store.children(b, root) == [c]
        assert store.children(c, root) == []


# ------------------------------------------------------------------------------ grid
def test_grid_builds_six_chains_with_the_right_dirs_and_argv():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        ks = [10, 12, 14, 16, 18, 20]
        chains = steps.grid(
            root, name="review", ks=ks, delta=0.10, seeds="0-4", workers=2, theta=0.4, lam=0.3,
            filler_capture="full", time_limit=600, pins=None, python="/py/python3",
            repo="/repo", instance="/repo/instance_descaled_v2_conus.json.gz",
            geo_cache="/repo/data/geo")

        assert len(chains) == 6
        for k, chain in zip(ks, chains):
            assert len(chain) == 3
            (draw_dir, d_argv), (clip_dir, c_argv), (clip_dir2, g_argv) = chain
            assert clip_dir2 == clip_dir
            kk = f"k{k:02d}"

            draw_step = store.read_step(draw_dir)
            assert draw_step["kind"] == "draw" and draw_step["parent"] is None
            assert draw_step["outputs"] == {"table": f"{kk}/draw.csv",
                                            "metrics": f"{kk}/metrics.json"}

            clip_step = store.read_step(clip_dir)
            assert clip_step["kind"] == "clip" and clip_step["parent"] == draw_dir.name
            assert clip_step["outputs"] == {"table": "d0.1/draw.csv",
                                            "metrics": "d0.1/splits.json", "geom": "geom.json"}

            assert d_argv[:3] == ["/py/python3", "/repo/tools/run_draw.py",
                                  "/repo/instance_descaled_v2_conus.json.gz"]
            assert "--k" in d_argv and d_argv[d_argv.index("--k") + 1] == str(k)
            assert "--out" in d_argv and d_argv[d_argv.index("--out") + 1] == str(draw_dir)
            assert "--scenario" not in d_argv

            draw_table = draw_dir / f"{kk}/draw.csv"
            assert "--draw" in c_argv and c_argv[c_argv.index("--draw") + 1] == str(draw_table)
            assert "--delta" in c_argv and c_argv[c_argv.index("--delta") + 1] == "0.1"
            assert "--anchor-homes" in c_argv
            assert "--no-maps" in c_argv

            clip_table = clip_dir / "d0.1/draw.csv"
            assert g_argv[-4:] == ["--out", str(clip_dir), "--geo-cache", "/repo/data/geo"]
            assert "--table" in g_argv and g_argv[g_argv.index("--table") + 1] == str(clip_table)


def test_grid_writes_scenario_json_and_passes_the_flag_when_pins_are_given():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        pins = {"fix": {"NORTH": ["ME", "NH"]}, "anchor": {}}
        [chain] = steps.grid(
            root, name="pinned", ks=[18], delta=0.10, seeds="0-4", workers=2, theta=0.4,
            lam=0.3, filler_capture="full", time_limit=600, pins=pins, python="/py/python3",
            repo="/repo", instance="/repo/instance.json.gz", geo_cache="/repo/data/geo")
        (draw_dir, d_argv), _clip, _geom = chain
        scenario_path = draw_dir / "scenario.json"
        assert scenario_path.exists()
        assert json.loads(scenario_path.read_text()) == pins
        assert "--scenario" in d_argv
        assert d_argv[d_argv.index("--scenario") + 1] == str(scenario_path)


# ------------------------------------------------------------------------------ launch_chain
def test_launch_chain_runs_in_order_writes_both_logs_and_terminates():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        d1, d2 = root / "draw_a_1", root / "clip_b_1"
        d1.mkdir(); d2.mkdir()
        store.write_step(d1, kind="draw", parent=None, params={}, argv=[], outputs={})
        store.write_step(d2, kind="clip", parent=d1.name, params={}, argv=[], outputs={})

        chain = [(d1, ["true"]), (d2, ["sh", "-c", "echo hi"])]
        pid = runner.launch_chain(chain, cwd=root)

        deadline = time.time() + 10.0
        while time.time() < deadline and runner._alive(pid):
            time.sleep(0.02)
        assert not runner._alive(pid)

        assert (d1 / runner.LOG).exists()
        assert (d2 / runner.LOG).read_text().strip() == "hi"

        s1, s2 = store.read_step(d1), store.read_step(d2)
        assert s1["pid"] == pid == s2["pid"]
        assert s1["started"] is not None and s2["started"] is not None
