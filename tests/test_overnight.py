"""tools/exp/contig/overnight.py (the main-map overnight grid, 2026-10-13) on toy specs and
hand-computed values: the δ fit, the split rule, the spec copy, the retry, labels, the re-run
direction, the scheduler, a stage's kill, the resume helpers and GRID.json."""
from __future__ import annotations

import collections
import importlib.util
import json
import os
import sys
import tempfile
import threading
import time
import tomllib

from td import spec as tdspec

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "contig_overnight", os.path.join(HERE, "..", "tools", "exp", "contig", "overnight.py"))
overnight = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(overnight)
score = overnight.score

TOY = """[scenario]
name = "toy"
fine_channels = ["national_chase", "wh"]
planned_elsewhere = ["career", "edj", "fi", "ifa", "imo", "priafs", "wells_fi", "wells_wh"]

[channels.national]
k = 2
domain = [{ units = "all", fine = ["national_chase"] }]
mode = "whole"
free = ["CA"]
eta = 0.05
delta = 0.1

[channels.WIFI]
k = 2
domain = [{ units = "all", fine = ["wh"] }]
mode = "whole"
eta = 0.05
"""
CELLS = {("CA", "national_chase"): 1500.0, ("TX", "national_chase"): 700.0,
         ("NY", "national_chase"): 300.0, ("CA", "wh"): 1000.0, ("TX", "wh"): 900.0}


def _toy():
    return tdspec.parse(tomllib.loads(TOY))


def test_fit_delta_by_hand():
    assert overnight.fit_delta(1207.0, 14, 1000.0, 1437.5) == 0.1714      # 207 / 1207 = 0.17150
    assert overnight.fit_delta(950.0, 2, 850.0, 1150.0) == 0.1052         # 100 / 950 = 0.10526
    assert overnight.fit_delta(1543.0, 1, 850.0, 1600.0) == overnight.K1_FINAL_DELTA
    assert overnight.fit_delta(1700.0, 1, 850.0, 1600.0) is None
    assert overnight.fit_delta(850.0, 3, 850.0, 1150.0) is None           # on the edge: no band
    assert overnight.fit_delta(800.0, 3, 850.0, 1150.0) is None


def test_plan_point_rule_window_and_whole_state_cap():
    p = overnight.plan_point({"national": 2, "WIFI": 2}, _toy(), CELLS, "rule")
    n, w = p["channels"]["national"], p["channels"]["WIFI"]
    assert p["infeasible"] == {}
    assert (n["usd_m"], n["tau_m"], n["free"]) == (2500.0, 1250.0, ["CA", "TX"])      # > 625
    assert (n["lo_m"], n["hi_m"], n["final_delta"]) == (1000.0, 1437.5, 0.15)          # 187.5 / 1250
    assert (w["tau_m"], w["free"], w["whole_state_cap"], w["hi_m"]) == (950.0, ["CA", "TX"], False, 1150.0)
    assert w["final_delta"] == 0.1052
    bad = overnight.plan_point({"national": 2, "WIFI": 4}, _toy(), CELLS, "rule")
    assert list(bad["infeasible"]) == ["WIFI"] and "τ outside the dollar window" in bad["infeasible"]["WIFI"]
    cells = {**CELLS, ("CA", "wh"): 900.0, ("TX", "wh"): 643.0}
    base = overnight.plan_point({"national": 2, "WIFI": 1}, _toy(), cells, "base")
    assert base["channels"]["national"]["free"] == ["CA"]                # the spec's own list
    w = base["channels"]["WIFI"]
    assert (w["free"], w["whole_state_cap"], w["hi_m"], w["final_delta"]) == ([], True, 1600.0, 0.10)
    try:
        overnight.plan_point({"national": 2}, _toy(), CELLS, "rule")
    except ValueError:
        pass
    else:
        raise AssertionError("a K for some channels only was planned")


def test_point_spec_text_sets_k_and_both_deltas():
    plan = {"channels": {"national": {"k": 3, "final_delta": 0.15}, "WIFI": {"k": 1, "final_delta": 0.01}}}
    text = overnight.point_spec_text(TOY, "pt-1", plan)
    assert text.startswith("# main-map overnight grid point pt-1")
    sp = tdspec.parse(tomllib.loads(text))
    assert sp.name == "pt-1"
    n, w = sp.channels["national"], sp.channels["WIFI"]
    assert (n.k, n.delta, n.final_delta) == (3, 0.02, 0.15)
    assert (w.k, w.delta, w.final_delta) == (1, 0.01, 0.01)               # declared at most the final


def test_retry_keys_on_the_drawings_own_status():
    contig = {"channels": {"national": {"status": "connected", "plan_delta": 0.05},
                           "WH": {"status": "unknown", "plan_delta": 0.07},
                           "FI": {"status": "infeasible", "plan_delta": 0.09},
                           "WIFI": {"status": "optimal", "plan_delta": 0.1}}}
    assert overnight.needs_retry(contig) == ["FI", "WH"]
    assert overnight.retry_delta(contig, ["FI", "WH"]) == 0.14
    assert overnight.needs_retry({"channels": {"WIFI": {"status": "connected"}}}) == []


def _row(ch, usd, lo=850.0, hi=1150.0, cap=None, ok=False, d=None):
    return {"channel": ch, "district": d or f"{ch}_01", "usd": usd, "lo": lo, "hi": hi, "cap": cap,
            "allowance": False, "ok": ok}


def test_label_order_m1_then_dollars_then_scorer():
    good, bad = {"status": "pass", "summary": "ok"}, {"status": "fail", "summary": "1 district in pieces"}
    ok, out = _row("WH", 900.0, ok=True), _row("WH", 840.8, d="WH_09")
    assert overnight.label_of(bad, [out], False, ["x"])[0] == "fails M1"
    assert overnight.label_of(good, [ok, out], False, ["x"]) == ("ineligible ($)", "WH_09 840.8M outside 850.0-1,150.0M")
    assert overnight.label_of(good, [ok], True, []) == ("eligible", "")
    assert overnight.label_of(good, [ok], False, ["audit: a fails", "main K 47 outside 48-54"]) == \
        ("ineligible", "audit: a fails; main K 47 outside 48-54")


def test_rerun_direction():
    ks = {"national": 15, "WH": 11, "FI": 20, "WIFI": 3}
    assert overnight.rerun_k([_row("WH", 840.0)], ks) == {**ks, "WH": 10}
    assert overnight.rerun_k([_row("FI", 1100.0, 765.0, 1035.0)], ks) == {**ks, "FI": 21}
    assert overnight.rerun_k([_row("WIFI", 1700.0, cap=1600.0)], ks) == {**ks, "WIFI": 4}
    assert overnight.rerun_k([_row("WH", 840.0), _row("WH", 1200.0, d="WH_02")], ks) is None
    assert overnight.rerun_k([_row("WIFI", 800.0)], {"WIFI": 1}) is None
    assert overnight.rerun_k([_row("X", 5.0, lo=None, hi=None)], {"X": 2}) is None
    assert overnight.rerun_k([_row("WH", 900.0, ok=True)], ks) is None
    assert overnight.rerun_id("ne-50-bal", ks, {**ks, "WH": 10}) == "ne-50-bal-WH10"


def test_dollars_and_score_files_read_back():
    gate = [{"channel": "WH", "district": "WH_01", "usd": 840.8e6, "lo": 0.85e9, "hi": 1.15e9,
             "states": ["NJ", "NY"], "whole_states": False, "cap": None, "allowance": False, "ok": False},
            {"channel": "WIFI", "district": "WIFI_01", "usd": 1.543e9, "lo": 0.85e9, "hi": 1.15e9,
             "states": ["CO", "ID"], "whole_states": True, "cap": 1.6e9, "allowance": True, "ok": True}]
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "dollars.csv")
        score.write_dollars(path, gate)
        rows = overnight.read_dollars(path)
        sc = os.path.join(tmp, "score.txt")
        with open(sc, "w") as fh:
            fh.write("# r\ndir: d\neligible: no\n  - audit: a fails\n  - $ WH_01 840.8M outside\nK: WH 11\n")
        no = overnight.read_score(sc)
        with open(sc, "w") as fh:
            fh.write("# r\ndir: d\neligible: yes\nK: WH 11\n")
        yes = overnight.read_score(sc)
    assert rows[0] == {"channel": "WH", "district": "WH_01", "usd": 840.8, "lo": 850.0, "hi": 1150.0,
                       "cap": None, "allowance": False, "ok": False}
    assert (rows[1]["usd"], rows[1]["cap"], rows[1]["allowance"], rows[1]["ok"]) == (1543.0, 1600.0, True, True)
    assert no == (False, ["audit: a fails", "$ WH_01 840.8M outside"])
    assert yes == (True, [])


def test_schedule_first_fit_reruns_and_deadline():
    pts = [{"id": "a", "k": {"x": 1, "y": 1, "z": 1}}, {"id": "b", "k": {"x": 1, "y": 1, "z": 1}},
           {"id": "c", "k": {"x": 1}}]
    lock, ran, live, peak = threading.Lock(), [], [0], [0]

    def work(p):
        with lock:
            live[0] += overnight.slots_of(p)
            peak[0] = max(peak[0], live[0])
        time.sleep(0.05)
        with lock:
            live[0] -= overnight.slots_of(p)
            ran.append(p["id"])
        return [{"id": "a2", "k": {"x": 1}}] if p["id"] == "a" else []
    assert overnight.schedule(pts, 5, time.time() + 60, work, poll=0.01) == []
    assert sorted(ran) == ["a", "a2", "b", "c"] and peak[0] <= 5
    assert ran.index("c") < ran.index("b")                                 # c filled a's leftover slots
    ran.clear()
    assert overnight.schedule(pts, 5, time.time() - 1, work, poll=0.01) == pts and ran == []
    try:
        overnight.schedule([{"id": "w", "k": {"x": 1}}], 1, time.time() + 60, work)
    except ValueError:
        pass
    else:
        raise AssertionError("a point larger than the slots was scheduled")


def test_child_cap_deadline_and_exit():
    sleep = [sys.executable, "-c", "import time; time.sleep(30)"]
    with tempfile.TemporaryDirectory() as tmp:
        log = os.path.join(tmp, "s.log")
        cap = overnight.child(sleep, log, 0.5, time.time() + 60)
        late = overnight.child(sleep, log, 60, time.time() + 0.5)
        past = overnight.child(sleep, log, 5, time.time() - 1)
        ok = overnight.child([sys.executable, "-c", "print('hi')"], log, 30, time.time() + 60)
        text = open(log).read()
    assert cap["stop"] == "cap" and cap["rc"] != 0 and cap["seconds"] < 10
    assert late["stop"] == "deadline" and late["seconds"] < 10
    assert past == {"rc": None, "seconds": 0.0, "stop": "deadline"}
    assert ok["rc"] == 0 and ok["stop"] is None and "hi" in text
    assert not overnight.LIVE


def test_resume_keeps_finished_folders_and_sets_others_aside():
    with tempfile.TemporaryDirectory() as tmp:
        d = os.path.join(tmp, "draw")
        assert not overnight.finished(d)
        os.makedirs(d)
        open(os.path.join(d, "ledger.csv"), "w").close()
        for status, want in (("running", False), ("done", True)):
            with open(os.path.join(d, "manifest.json"), "w") as fh:
                json.dump({"status": status}, fh)
            assert overnight.finished(d) is want
        r1 = os.path.join(tmp, "r1")
        assert overnight.set_aside(r1) is None
        for n in (1, 2):
            os.makedirs(r1)
            open(os.path.join(r1, "x"), "w").close()
            assert overnight.set_aside(r1) == f"{r1}.stale{n}"
            assert os.path.exists(os.path.join(f"{r1}.stale{n}", "x")) and not os.path.exists(r1)


def test_grid_lists_every_point_once():
    doc = overnight.grid_doc("m5", "/x/instance_descaled_usd.json.gz", "abc", time.time() + 3600,
                             {"commit": "c", "dirty": False, "diff_sha256": None})
    pts = doc["points"]
    assert len(pts) == len(overnight.POINTS) == 21
    assert collections.Counter(p["status"] for p in pts.values()) == {"queued": 15, "elsewhere": 6}
    assert all((p["host"] == "m2") == (p["structure"] == "west8") for p in pts.values())
    chans = {"ne_plains": {"national", "WH", "FI", "WIFI"}, "west8": {"national", "WH", "FI", "WIFI"},
             "nw49": {"national", "WIFI"}, "nw34": {"national", "WIFI"}, "w1": {"WIFI"}}
    for p in overnight.POINTS:
        assert set(p["k"]) == chans[p["structure"]] and 48 <= sum(p["k"].values()) <= 52
    assert overnight.order(overnight.POINTS)[0]["id"] == "w1-52"
    assert any("#133" in x for x in doc["assumptions"])
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "GRID.json")
        g = overnight.Grid(path, doc)
        g.update("w1-48", label="stopped")
        g.add(overnight.record({"id": "w1-48-WIFI47", "structure": "w1", "k": {"WIFI": 47}}, "m5", "w1-48"))
        back = json.load(open(path))
        assert back["points"]["w1-48"]["label"] == "stopped"
        assert back["points"]["w1-48-WIFI47"]["parent"] == "w1-48"
        assert not os.path.exists(path + ".tmp")
        assert abs(g.deadline() - (time.time() + 3600)) < 5


def test_commands_carry_the_settled_flags():
    plan = {"channels": {"national": {"free": ["CA", "TX"]}, "WIFI": {"free": []}}}
    rp = overnight.replan_cmd("b.toml", "/p", "/plans", "/x.json.gz", plan)
    assert rp[rp.index("--free") + 1] == "national=CA,TX" and "--keep" not in rp
    assert rp[rp.index("--time-limit") + 1] == "600"
    assert "--keep" in overnight.replan_cmd("b.toml", "/p", "/plans", "/x", {"channels": {"WIFI": {"free": []}}})
    d = overnight.draw_cmd("s.toml", "/o", "/plans", "/x", 4)
    assert d[d.index("--land-ratio") + 1] == "10" and "--sequential" in d and "--delta" not in d
    assert d[d.index("--jobs") + 1] == "4" and d[d.index("--time-limit") + 1] == "4500"
    d = overnight.draw_cmd("s.toml", "/o", "/plans", "/x", 4, 0.14)
    assert d[d.index("--delta") + 1] == "0.14"
    r = overnight.repair_cmd("/s", "/o", "/plans", "/x", 2, 2, "ne-48-bal")
    assert r[r.index("--h0") + 1] == "8" and r[r.index("--max-zctas") + 1] == "2000"
    assert r[r.index("--budget") + 1] == "1800" and "--keep-support" in r and "--flow" in r
    assert overnight.slots_of({"k": {"WIFI": 48}}) == 2
    assert overnight.slots_of({"k": dict.fromkeys(("national", "WH", "FI", "WIFI"), 1)}) == 4

