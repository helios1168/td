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
        paths = [store.new_run_dir(root, "draw", 18) for _ in range(4)]
        assert len(set(paths)) == 4
        for p in paths:
            assert p.is_dir()
            assert p.name.startswith("k18_draw_")            # legacy int k, unpadded member


def test_new_run_dir_carries_kind_k_and_stamp_only():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        p = store.new_run_dir(root, "clip", 8)
        kk, kind, date, time = p.name.split("_")[:4]
        assert (kind, kk) == ("clip", "k8")
        assert len(date) == 8 and len(time.split("-")[0]) == 6


def test_new_run_dir_is_named_member_then_kind_then_stamp():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        p = store.new_run_dir(root, "clip", "custom_k10_d5")
        assert p.name.startswith("custom_k10_d5_clip_")


# ------------------------------------------------------------------------------ slugify / member_name
def test_slugify_turns_spaces_and_underscores_into_hyphens():
    assert store.slugify("My Scenario 2") == "my-scenario-2"
    assert store.slugify("custom_name") == "custom-name"
    assert store.slugify("  --Weird!!Name--  ") == "weird-name"


def test_slugify_falls_back_to_a_grid_stamp_when_empty():
    assert store.slugify("").startswith("grid-")
    assert store.slugify("###").startswith("grid-")          # nothing left after stripping


def test_member_name_formats_delta_as_a_bare_percent():
    assert store.member_name("custom", 8, 0.05) == "custom_k8_d5"
    assert store.member_name("custom", 10, 0.10) == "custom_k10_d10"
    assert store.member_name("custom", 10, 0.075) == "custom_k10_d7.5"


# ------------------------------------------------------------------------------ scenario ledger
def test_scenario_of_and_member_of_walk_lineage_like_k_of():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        parent = root / "custom_k10_d5_draw_1"
        parent.mkdir()
        store.write_step(parent, kind="draw", parent=None, params={}, argv=[], outputs={},
                         scenario="custom", member="custom_k10_d5")
        child = root / "custom_k10_d5_staff_1"
        child.mkdir()
        store.write_step(child, kind="staff", parent=parent.name, params={}, argv=[],
                         outputs={})                          # nothing of its own; inherits
        assert store.scenario_of(child, root) == "custom"     # from the parent's step.json
        assert store.member_of(child, root) == "custom_k10_d5"

        legacy = root / "k18_staff_1"
        legacy.mkdir()
        store.write_step(legacy, kind="staff", parent=None, params={}, argv=[], outputs={})
        assert store.scenario_of(legacy, root) is None
        assert store.member_of(legacy, root) is None


def test_label_reads_k_kind_and_time_off_the_ledger_even_for_old_names():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        old = root / "clip_grid-k18_20260908_144239"
        _mkstep(old)
        store.update_step(old, kind="clip", params={"k": 18}, started="2026-09-08T14:42:39")
        assert store.label(old, root) == "k18 · clip · 2026-09-08 14:42:39"
        child = root / "staff_k18_20260908_145341"
        _mkstep(child)
        store.update_step(child, kind="staff", parent=old.name, params={})
        assert store.k_of(child, root) == 18                    # inherited from the parent
        assert store.label(child, root) == "k18 · staff · 2026-09-08 14:53:41"


def test_label_uses_the_member_name_when_a_run_belongs_to_a_scenario():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        run = root / "custom_k10_d5_clip_20260908_181500"
        run.mkdir()
        store.write_step(run, kind="clip", parent=None, params={}, argv=[], outputs={},
                         scenario="custom", member="custom_k10_d5")
        store.update_step(run, started="2026-09-08T18:15:00")
        assert store.label(run, root) == "custom_k10_d5 · clip · 2026-09-08 18:15:00"


def test_scenarios_orders_newest_first_with_legacy_group_last():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)

        def make(name, scenario, member, when):
            run = root / name
            run.mkdir()
            store.write_step(run, kind="clip", parent=None, params={}, argv=[], outputs={},
                             scenario=scenario, member=member)
            store.update_step(run, started=when)
            return run

        old_legacy = make("k18_clip_20260101_000000", None, None, "2026-01-01T00:00:00")
        a1 = make("a_k10_d5_clip_20260102_000000", "a", "a_k10_d5", "2026-01-02T00:00:00")
        b1 = make("b_k10_d5_clip_20260103_000000", "b", "b_k10_d5", "2026-01-03T00:00:00")
        a2 = make("a_k12_d5_clip_20260104_000000", "a", "a_k12_d5", "2026-01-04T00:00:00")

        result = store.scenarios(root)
        assert [slug for slug, _runs in result] == ["a", "b", None]
        by_slug = dict(result)
        assert by_slug["a"] == [a2, a1]                          # newest first within the group
        assert by_slug["b"] == [b1]
        assert by_slug[None] == [old_legacy]


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
            root, name="Custom", ks=ks, delta=0.10, seeds="0-4", workers=2, theta=0.4, lam=0.3,
            filler_capture="full", time_limit=600, pins=None, python="/py/python3",
            repo="/repo", instance="/repo/instance_descaled_v2_conus.json.gz",
            geo_cache="/repo/data/geo")

        assert len(chains) == 6
        for k, chain in zip(ks, chains):
            assert len(chain) == 3
            (draw_dir, d_argv), (clip_dir, c_argv), (clip_dir2, g_argv) = chain
            assert clip_dir2 == clip_dir
            kk = f"k{k:02d}"
            member = f"custom_k{k}_d10"

            assert draw_dir.name.startswith(f"{member}_draw_")
            assert clip_dir.name.startswith(f"{member}_clip_")
            draw_step = store.read_step(draw_dir)
            assert draw_step["kind"] == "draw" and draw_step["parent"] is None
            assert draw_step["scenario"] == "custom" and draw_step["member"] == member
            assert draw_step["params"]["scenario_name"] == "Custom"
            assert draw_step["outputs"] == {"table": f"{kk}/draw.csv",
                                            "metrics": f"{kk}/metrics.json",
                                            "timings": "timings.json"}

            clip_step = store.read_step(clip_dir)
            assert clip_step["kind"] == "clip" and clip_step["parent"] == draw_dir.name
            assert clip_step["scenario"] == "custom" and clip_step["member"] == member
            assert clip_step["params"]["scenario_name"] == "Custom"
            assert clip_step["outputs"] == {"table": "d0.1/draw.csv",
                                            "metrics": "d0.1/splits.json", "geom": "geom.json",
                                            "timings": "timings.json"}

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


def test_grid_defaults_to_an_anonymous_slug_when_no_name_is_given():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        [chain] = steps.grid(
            root, ks=[18], delta=0.10, seeds="0-4", workers=2, theta=0.4, lam=0.3,
            filler_capture="full", time_limit=600, pins=None, python="/py/python3",
            repo="/repo", instance="/repo/instance.json.gz", geo_cache="/repo/data/geo")
        (draw_dir, _d_argv), _clip, _geom = chain
        draw_step = store.read_step(draw_dir)
        assert draw_step["scenario"].startswith("grid-")
        assert draw_step["member"] == f"{draw_step['scenario']}_k18_d10"


def test_grid_writes_scenario_json_and_passes_the_flag_when_pins_are_given():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        pins = {"fix": {"NORTH": ["ME", "NH"]}, "anchor": {}}
        [chain] = steps.grid(
            root, ks=[18], delta=0.10, seeds="0-4", workers=2, theta=0.4,
            lam=0.3, filler_capture="full", time_limit=600, pins=pins, python="/py/python3",
            repo="/repo", instance="/repo/instance.json.gz", geo_cache="/repo/data/geo")
        (draw_dir, d_argv), _clip, _geom = chain
        scenario_path = draw_dir / "scenario.json"
        assert scenario_path.exists()
        assert json.loads(scenario_path.read_text()) == pins
        assert "--scenario" in d_argv
        assert d_argv[d_argv.index("--scenario") + 1] == str(scenario_path)


# ------------------------------------------------------------------------------ stage-2 weights
def test_clip_argv_carries_the_stage2_weights():
    argv = steps.clip_argv("/py/python3", "/repo", "/repo/instance.json.gz", Path("/out"),
                           draw=Path("/draw/k18/draw.csv"), k=18, delta=0.1, time_limit=600,
                           theta=0.4, lam=0.3, filler_capture="full", geo_cache="/geo")
    assert "--theta" in argv and argv[argv.index("--theta") + 1] == "0.4"
    assert "--lam" in argv and argv[argv.index("--lam") + 1] == "0.3"
    assert "--filler-capture" in argv and argv[argv.index("--filler-capture") + 1] == "full"


def test_split_argv_carries_the_stage2_weights():
    argv = steps.split_argv("/py/python3", "/repo", "/repo/instance.json.gz", Path("/out"),
                            table=Path("/table/draw.csv"), district="D01", reps=["A", "B"],
                            theta=0.4, lam=0.3, filler_capture="opportunity")
    assert "--theta" in argv and argv[argv.index("--theta") + 1] == "0.4"
    assert "--lam" in argv and argv[argv.index("--lam") + 1] == "0.3"
    assert ("--filler-capture" in argv
           and argv[argv.index("--filler-capture") + 1] == "opportunity")


def test_staff_argv_appends_districts_only_when_given():
    argv = steps.staff_argv("/py/python3", "/repo", "/repo/instance.json.gz", Path("/out"),
                            table=Path("/table/draw.csv"), keep="R1,R2", theta=0.4, lam=0.3,
                            filler_capture="full")
    assert "--districts" not in argv

    scoped = steps.staff_argv("/py/python3", "/repo", "/repo/instance.json.gz", Path("/out"),
                              table=Path("/table/draw.csv"), keep="R1,R2", theta=0.4, lam=0.3,
                              filler_capture="full", districts=["D01", "D05"])
    assert "--districts" in scoped
    assert scoped[scoped.index("--districts") + 1] == "D01,D05"


def test_grid_records_the_stage2_weights_in_the_clip_step_too():
    """`grid` already records `theta`/`lam`/`filler_capture` in the draw run's `step.json`
    params; the clip run's own params must carry the same three, since the clip is scored on
    them too now."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        [chain] = steps.grid(
            root, ks=[18], delta=0.10, seeds="0-4", workers=2, theta=0.4, lam=0.3,
            filler_capture="full", time_limit=600, pins=None, python="/py/python3",
            repo="/repo", instance="/repo/instance_descaled_v2_conus.json.gz",
            geo_cache="/repo/data/geo")
        (draw_dir, _d_argv), (clip_dir, _c_argv), _geom = chain
        clip_step = store.read_step(clip_dir)
        assert clip_step["params"]["theta"] == 0.4
        assert clip_step["params"]["lam"] == 0.3
        assert clip_step["params"]["filler_capture"] == "full"


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
