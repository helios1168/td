"""tools/exp (#92): the sweep runner, its manifests, the index, the ranked table and the shortlist.

The two-job grid runs the 51 scenario on the seed-0 fixture at `test_realize.FIXTURE_DELTA` (one
job per national δ) twice, through the command line as a lane would: the second call skips both.
It needs TIGER/Line 2025 state polygons (`data/public/` or `$TD_REPO`'s); SKIP without.
"""
from __future__ import annotations

import glob
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import tomllib

from tests import test_realize as tr
from tests import test_spec as ts

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
EXP = os.path.join(ROOT, "tools", "exp")


def _load(name):
    spec = importlib.util.spec_from_file_location(f"exp_{name}", os.path.join(EXP, f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


sweep, table = _load("sweep"), _load("table")


def _tool(name, *args):
    return subprocess.run([sys.executable, os.path.join(EXP, f"{name}.py"), *args], cwd=ROOT,
                          capture_output=True, text=True)


def _grid(tmp, lane, params, grid, public=None):
    path = os.path.join(tmp, f"{lane}.toml")
    lines = [f'lane = "{lane}"', 'formulation = "support"', "fixture = 0"]
    if public:
        lines.append(f'public = "{public}"')
    lines += ["[params]", *(f'{k} = {sweep._toml_value(v)}' for k, v in params.items()),
              "[grid]", *(f'"{k}" = {sweep._toml_value(v)}' for k, v in grid.items())]
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    notify = os.path.join(tmp, "notify.sh")
    with open(notify, "w", encoding="utf-8") as fh:
        fh.write(f'#!/bin/sh\necho "$1" >> {os.path.join(tmp, "notified")}\n')
    os.chmod(notify, 0o755)
    return path, notify


def test_a_two_job_grid_on_the_51_fixture_runs_once_and_is_indexed_and_ranked():
    public = ts._state_file()
    if public is None:
        return
    tmp = tempfile.mkdtemp(prefix="td-exp-")
    root = os.path.join(tmp, "exp")
    fixed = {"scenario": os.path.relpath(ts.S51, ROOT), "maps": False}
    for c, dl in tr.FIXTURE_DELTA.items():
        fixed[f"spec.channels.{c}.final_delta"] = 0.28 if c == "national" else dl
        if c != "national":
            fixed[f"spec.channels.{c}.delta"] = dl
    grid, notify = _grid(tmp, "smoke", fixed, {"spec.channels.national.delta": [0.27, 0.28]},
                         public)
    first = _tool("sweep", grid, "--jobs", "2", "--root", root, "--notify", notify)
    assert first.returncode == 0, first.stdout + first.stderr
    folders = sorted(glob.glob(os.path.join(root, "smoke", "*")))
    assert len(folders) == 2 and first.stdout.count("done   smoke-support-") == 2, first.stdout
    code = sweep.code_state()
    inst = sweep.instance({"fixture": 0})
    manifests = {}
    for folder in folders:
        m = json.load(open(os.path.join(folder, "manifest.json"), encoding="utf-8"))
        manifests[folder] = open(os.path.join(folder, "manifest.json"), "rb").read()
        assert re.fullmatch(r"smoke-support-[0-9a-f]{8}", m["run_id"])
        assert os.path.basename(folder) == m["run_id"] and m["folder"] == folder
        assert m["run_id"] == sweep.run_id("smoke", "support", m["params"], code, inst,
                                           m["scenario"]["sha256"])
        assert m["scenario"] == {"path": ts.S51, "sha256": sweep.sha256_file(ts.S51),
                                 "snapshot": "scenario.toml"}
        assert [o["pid"] for o in m["owners"]] and all(o["host"] and o["started"]
                                                       for o in m["owners"])
        assert len(m["owners"]) == 2 and sweep.abandoned(m)
        assert m["status"] == "done" and m["audit"] == "pass", (m["stop_reason"], m["audit"])
        assert m["stop_reason"] == "FI optimal; WH optimal; WIFI optimal; national optimal"
        p = m["provenance"]
        assert re.fullmatch(r"[0-9a-f]{40}", p["commit"]) and p["commit"] == code["commit"]
        assert isinstance(p["dirty"], bool) and (p["diff_sha256"] is None) == (not p["dirty"])
        assert p["host"] and p["instance"] == "fixture seed 0"
        assert p["instance_sha256"] == inst["instance_sha256"] and len(p["instance_sha256"]) == 64
        assert p["queued_at"] <= m["started_at"] <= m["finished_at"] and m["seconds"] > 0
        assert m["params"]["threads"] == 1 and m["params"]["maps"] is False
        assert m["params"]["spec.channels.WH.delta"] == tr.FIXTURE_DELTA["WH"]
        assert set(m["solver"]) == {"national", "WH", "FI", "WIFI"}
        assert all(s["status"] == "optimal" and s["gap"] == 0.0 for s in m["solver"].values())
        assert {"worst_dev", "mean_dev"} <= set(m["metrics"])
        files = os.listdir(folder)
        assert not [f for f in files if os.path.isdir(os.path.join(folder, f))], files
        assert {"manifest.json", "log.txt", "scenario.toml", "spec.toml", "run.json",
                "solver.json", "scorecard.md", "ledger.csv", "districts.csv"} <= set(files), files
        raw = tomllib.load(open(os.path.join(folder, "spec.toml"), "rb"))
        assert raw["channels"]["national"]["delta"] == m["params"]["spec.channels.national.delta"]
    assert sorted(json.loads(manifests[f])["params"]["spec.channels.national.delta"]
                  for f in folders) == [0.27, 0.28]

    second = _tool("sweep", grid, "--jobs", "2", "--root", root, "--notify", notify)
    assert second.returncode == 0 and "0 done, 0 failed, 2 skipped" in second.stdout, second.stdout
    assert all(open(os.path.join(f, "manifest.json"), "rb").read() == manifests[f] for f in folders)
    notified = open(os.path.join(tmp, "notified"), encoding="utf-8").read().splitlines()
    assert len(notified) == 2 and notified[1].startswith("sweep smoke/support: 0 done"), notified

    assert _tool("index", "--root", root).returncode == 0
    rows = [json.loads(line) for line in open(os.path.join(root, "index.jsonl"), encoding="utf-8")]
    assert len(rows) == 2 and {r["folder"] for r in rows} == set(folders)
    assert all(r["status"] == "done" and r["audit"] == "pass" and r["params"] for r in rows)
    rid = rows[0]["run_id"]
    shown = _tool("table", "--root", root, "--shortlist", rid, "--tier", "2", "--note", "smoke")
    assert shown.returncode == 0 and "## smoke" in shown.stdout, shown.stderr
    assert all(f in shown.stdout for f in folders) and "| 2 | smoke |" in shown.stdout
    short = json.load(open(os.path.join(root, "shortlist.json"), encoding="utf-8"))
    assert short == [{"run_id": rid, "tier": 2, "note": "smoke"}]
    assert not glob.glob(os.path.join(root, "**", "*.png"), recursive=True)


def _manifest(folder):
    return json.load(open(os.path.join(folder, "manifest.json"), encoding="utf-8"))


def _bogus_grid(tmp, table="bogus_a"):
    """A grid whose one job fails fast: its scenario file has an unknown table."""
    scenario = os.path.join(tmp, "bogus.toml")
    with open(scenario, "w", encoding="utf-8") as fh:
        fh.write(f"[{table}]\nx = 1\n")
    grid, notify = _grid(tmp, "broken", {"scenario": scenario}, {"time_limit": [5]}, public=tmp)
    return grid, notify, scenario


def test_a_failed_job_records_its_stop_reason_and_reruns_only_when_asked():
    tmp = tempfile.mkdtemp(prefix="td-exp-")
    root = os.path.join(tmp, "exp")
    grid, notify = _grid(tmp, "broken", {"scenario": os.path.relpath(ts.S51, ROOT),
                                         "spec.no_such_table.x": 1}, {"time_limit": [5]}, public=tmp)
    got = _tool("sweep", grid, "--root", root, "--notify", notify)
    assert got.returncode == 1 and "0 done, 1 failed, 0 skipped" in got.stdout, got.stdout
    (folder,) = glob.glob(os.path.join(root, "broken", "*"))
    m = _manifest(folder)
    assert m["status"] == "failed" and m["finished_at"]
    assert m["stop_reason"].startswith("SpecError") and "no_such_table" in m["stop_reason"]
    assert m["metrics"] == {} and m["audit"] is None
    assert "1 skipped" in _tool("sweep", grid, "--root", root, "--notify", notify).stdout
    again = _tool("sweep", grid, "--root", root, "--notify", notify, "--retry-failed")
    assert "0 done, 1 failed, 0 skipped" in again.stdout, again.stdout


def test_a_missing_scenario_or_extract_stops_the_sweep_and_still_notifies():
    tmp = tempfile.mkdtemp(prefix="td-exp-")
    root = os.path.join(tmp, "exp")
    grid, notify = _grid(tmp, "nosuch", {"scenario": "scenarios/no_such_scenario.toml"},
                         {"time_limit": [5]}, public=tmp)
    got = _tool("sweep", grid, "--root", root, "--notify", notify)
    assert got.returncode == 2 and "no_such_scenario" in got.stderr, got.stdout + got.stderr
    path = os.path.join(tmp, "noextract.toml")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(f'lane = "noextract"\nformulation = "support"\nextract = "{tmp}/no_such.json.gz"\n'
                 f'[params]\nscenario = "{os.path.relpath(ts.S51, ROOT)}"\n[grid]\ntime_limit = [5]\n')
    got = _tool("sweep", path, "--root", root, "--notify", notify)
    assert got.returncode == 2 and "no_such.json.gz" in got.stderr, got.stdout + got.stderr
    notified = open(os.path.join(tmp, "notified"), encoding="utf-8").read().splitlines()
    assert len(notified) == 2 and all(" stopped: " in n for n in notified), notified
    assert "no_such_scenario" in notified[0] and "no_such.json.gz" in notified[1], notified
    assert not os.path.exists(root)


def test_a_live_owned_run_refuses_a_second_sweep_and_an_abandoned_one_is_cleared():
    tmp = tempfile.mkdtemp(prefix="td-exp-")
    root = os.path.join(tmp, "exp")
    grid, notify, _ = _bogus_grid(tmp)
    (folder,), skipped = sweep.prepare(sweep.load_grid(grid), root)   # owned by this live process
    assert skipped == [] and not sweep.abandoned(_manifest(folder))
    marker = os.path.join(folder, "partial.txt")
    open(marker, "w").close()
    got = _tool("sweep", grid, "--root", root, "--notify", notify)
    assert got.returncode == 2 and "still owned" in got.stderr and str(os.getpid()) in got.stderr
    assert os.path.exists(marker) and _manifest(folder)["status"] == "queued"
    assert open(os.path.join(tmp, "notified"), encoding="utf-8").read().count(" stopped: ") == 1

    m = _manifest(folder)
    gone = subprocess.Popen(["true"])
    gone.wait()
    m["owners"] = [{**m["owners"][0], "pid": gone.pid}]
    sweep.write_manifest(folder, m)
    assert sweep.abandoned(m)
    got = _tool("sweep", grid, "--root", root, "--notify", notify)
    assert got.returncode == 1 and "0 done, 1 failed, 0 skipped" in got.stdout, got.stdout + got.stderr
    assert not os.path.exists(marker) and _manifest(folder)["status"] == "failed"
    m = _manifest(folder)
    m.update(status="running", owners=[{**m["owners"][0], "host": "elsewhere"}])
    sweep.write_manifest(folder, m)
    assert not sweep.abandoned(m)
    assert _tool("sweep", grid, "--root", root, "--notify", notify).returncode == 2


def test_a_scenario_edited_in_place_gets_a_new_run_id_and_a_job_runs_its_snapshot():
    tmp = tempfile.mkdtemp(prefix="td-exp-")
    root = os.path.join(tmp, "exp")
    grid, notify, scenario = _bogus_grid(tmp, "bogus_a")
    (first,), _ = sweep.prepare(sweep.load_grid(grid), root)
    with open(scenario, "w", encoding="utf-8") as fh:
        fh.write("[bogus_b]\nx = 1\n")
    job = subprocess.run([sys.executable, os.path.join(EXP, "sweep.py"), "--job", first], cwd=ROOT,
                         capture_output=True, text=True)
    assert job.returncode == 1 and "bogus_a" in _manifest(first)["stop_reason"], job.stderr
    assert "bogus_b" not in _manifest(first)["stop_reason"]
    got = _tool("sweep", grid, "--root", root, "--notify", notify)
    assert got.returncode == 1 and "0 done, 1 failed, 0 skipped" in got.stdout, got.stdout + got.stderr
    second = [f for f in glob.glob(os.path.join(root, "broken", "*")) if f != first]
    assert len(second) == 1 and "bogus_b" in _manifest(second[0])["stop_reason"]
    assert _manifest(second[0])["scenario"]["sha256"] == sweep.sha256_file(scenario)
    assert _manifest(first)["scenario"]["sha256"] != sweep.sha256_file(scenario)
    assert "1 skipped" in _tool("sweep", grid, "--root", root, "--notify", notify).stdout


def test_a_job_process_solves_on_its_one_thread_count():
    """In a process of its own, with warnings as errors: the pin would size this process's HiGHS
    pools (trap 18).  Both solver paths: the master's highspy and the realizer's SciPy linprog."""
    code = """if True:
        import importlib.util, sys
        sys.path.insert(0, '.')
        s = importlib.util.spec_from_file_location('sw', 'tools/exp/sweep.py')
        m = importlib.util.module_from_spec(s)
        s.loader.exec_module(m)
        m.pin_threads(2)
        from td import master, realize
        h = master.highspy.Highs()
        h.setOptionValue('output_flag', False)
        h.addVar(0.0, 1.0)
        h.changeColCost(0, 1.0)
        h.run()
        print(h.getOptionValue('threads')[1], h.modelStatusToString(h.getModelStatus()))
        seen, real = [], realize.linprog
        def spy(*a, **k):
            seen.append(dict(k['options']))
            return real(*a, **k)
        realize.linprog = spy
        flow = realize.transport(['a', 'b'], {'a': 1.0, 'b': 1.0}, {'a': (0, 0), 'b': (1, 0)},
                                 {'x': (0, 0), 'y': (1, 0)}, {'x': 1.0, 'y': 1.0})
        print(seen[0]['threads'], sorted(flow))
    """
    got = subprocess.run([sys.executable, "-W", "error", "-c", code], cwd=ROOT, capture_output=True,
                         text=True)
    assert got.returncode == 0, got.stdout + got.stderr
    assert got.stdout.splitlines() == ["2 Optimal", "2 [('a', 'x'), ('b', 'y')]"], got.stdout


def test_a_grid_is_the_product_of_its_lists_over_its_params():
    jobs = sweep.expand({"params": {"scenario": "s.toml", "spec": {"channels": {"WH": {"k": 11}}}},
                         "grid": {"spec": {"channels": {"FI": {"k": [19, 20]}}}, "eta": [0.05, 0.1]}})
    assert [(j["spec.channels.FI.k"], j["eta"]) for j in jobs] == [(19, 0.05), (20, 0.05),
                                                                  (19, 0.1), (20, 0.1)]
    assert all(j["spec.channels.WH.k"] == 11 and j["threads"] == 1 for j in jobs)
    for bad in ({"grid": {"k": 3}}, {"grid": {"k": []}}, {"params": {"k": 1}, "grid": {"k": [2]}},
                {"params": {"threads": 0}}):
        try:
            sweep.expand(bad)
        except sweep.SweepError:
            pass
        else:
            raise AssertionError(f"no SweepError for {bad}")
    code = {"commit": "0" * 40, "dirty": False, "diff_sha256": None}
    inst = {"instance_sha256": "1" * 64}
    a = sweep.run_id("a1", "support", jobs[0], code, inst)
    assert a == sweep.run_id("a1", "support", dict(reversed(jobs[0].items())), code, inst)
    assert a != sweep.run_id("a1", "support", jobs[1], code, inst)
    assert a != sweep.run_id("a1", "support", jobs[0], {**code, "commit": "2" * 40}, inst)
    assert a != sweep.run_id("a1", "support", jobs[0], {**code, "dirty": True,
                                                        "diff_sha256": "3" * 64}, inst)
    assert a != sweep.run_id("a1", "support", jobs[0], code, {"instance_sha256": "4" * 64})


def test_every_scenario_survives_the_spec_toml_round_trip():
    for path in glob.glob(os.path.join(ROOT, "scenarios", "**", "*.toml"), recursive=True):
        raw = tomllib.load(open(path, "rb"))
        assert tomllib.loads(sweep.dump_toml(raw)) == raw, path


def test_the_table_ranks_by_the_owner_order_and_flags_review():
    def row(rid, status="done", audit="pass", **m):
        return {"run_id": rid, "lane": "x", "folder": f"/runs/exp/x/{rid}", "status": status,
                "audit": audit, "metrics": m}

    def looks(eligible, splits, defects, worst=0.1):
        return dict(eligible=eligible, splits=splits, thin_links=defects, small_pieces=0,
                    crowded_states=0, contiguity_pieces=0, largest_extent_km=900.0,
                    states_per_district=3, worst_dev=worst, mean_dev=worst / 2)
    rows = [row("failed", status="failed"), row("bare", worst_dev=0.01, mean_dev=0.0),
            row("s13", **looks(True, 13, 4)), row("s13b", **looks(True, 13, 4, worst=0.05)),
            row("s14", **looks(True, 14, 1)), row("s15", **looks(True, 15, 0)),
            row("noteligible", **looks(False, 5, 0)), row("bandfail", audit="fail", **looks(True, 14, 2))]
    assert [r["run_id"] for r in sorted(rows, key=table.rank_key)] == [
        "s13b", "s13", "s14", "bandfail", "s15", "noteligible", "bare", "failed"]
    assert table.review(rows) == {"s14", "bandfail"}
    text = table.tables(rows, [{"run_id": "s14", "tier": 1, "note": "a | b"}])
    assert text.startswith("## x\n") and "| 3 | s14 |" in text and "| REVIEW | 1 | a \\| b |" in text
    assert "| 4 | bandfail | done | fail | yes | 14 | 2 |" in text and text.count("| REVIEW |") == 2
