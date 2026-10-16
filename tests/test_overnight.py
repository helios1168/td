"""tools/exp/contig/overnight.py (the main-map overnight grid, 2026-10-13) on toy specs and
hand-computed values: the δ fit, the split rule, the spec copy, the retry, labels, the re-run
direction, the scheduler, a stage's kill, the resume helpers and GRID.json."""
from __future__ import annotations

import collections
import importlib.util
import json
import math
import os
import re
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


def test_plan_point_delta_floor_widens_only_its_channel():
    """A `-wide` point (2026-10-13): the master's smallest feasible δ raises that channel's final
    δ; the window, τ and the other channels are as without it, and τ outside the window stays
    infeasible."""
    p = overnight.plan_point({"national": 2, "WIFI": 2}, _toy(), CELLS, "rule", {"WIFI": 0.2345})
    assert p["channels"]["WIFI"]["final_delta"] == 0.2345 and p["channels"]["national"]["final_delta"] == 0.15
    assert p["channels"]["WIFI"]["hi_m"] == 1150.0 and p["infeasible"] == {}
    low = overnight.plan_point({"national": 2, "WIFI": 2}, _toy(), CELLS, "rule", {"WIFI": 0.01})
    assert low["channels"]["WIFI"]["final_delta"] == 0.1052
    bad = overnight.plan_point({"national": 2, "WIFI": 4}, _toy(), CELLS, "rule", {"WIFI": 0.3})
    assert list(bad["infeasible"]) == ["WIFI"]


def test_wide_floor_reads_replan_json():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "replan.json")
        assert overnight.wide_floor(path, {}) is None
        with open(path, "w") as fh:
            json.dump({"channels": {"WH": {"final_delta": 0.1305, "smallest_delta": {"delta": 0.15071, "status": "converged"}},
                                    "FI": {"final_delta": 0.14, "smallest_delta": {"delta": 0.1, "status": "converged"}},
                                    "national": {"final_delta": 0.2, "status_at_declared": "feasible"}}}, fh)
        assert overnight.wide_floor(path, {}) == {"WH": 0.1508}
        assert overnight.wide_floor(path, {"WH": 0.2}) is None                 # already above it
        with open(path, "w") as fh:
            json.dump({"channels": {"WH": {"final_delta": 0.1, "smallest_delta": {"delta": 0.6}}}}, fh)
        assert overnight.wide_floor(path, {}) is None                          # past WIDE_MAX


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
            "allowance": False, "waiver": False, "ok": ok}


def test_label_order_m1_then_dollars_then_scorer():
    good, bad = {"status": "pass", "summary": "ok"}, {"status": "fail", "summary": "1 district in pieces"}
    ok, out = _row("WH", 900.0, ok=True), _row("WH", 840.8, d="WH_09")
    assert overnight.label_of(bad, [out], False, ["x"], 0)[0] == "fails M1"
    assert overnight.label_of(good, [ok, out], False, ["x"], 0) == ("ineligible ($)", "WH_09 840.8M outside 850.0-1,150.0M")
    assert overnight.label_of(good, [ok], True, [], 0) == ("eligible", "")
    assert overnight.label_of(good, [ok], False, ["audit: a fails", "main K 47 outside 48-54"], 0) == \
        ("ineligible", "audit: a fails; main K 47 outside 48-54")
    # the final gate's own exit code decides first: m1.json passing does not make a failed or unfinished gate pass
    for rc in (1, 2, None):
        label, reason = overnight.label_of(good, [ok], True, [], rc)
        assert label == "fails M1" and "the gate (check.py) exited" in reason, (rc, label, reason)
    bad_verdict = {"passes": False, "excepted": [], "blocking": ["X/Y: neck 1 km wide"]}
    assert overnight.label_of(good, [ok], True, [], 1, bad_verdict)[0] == "fails M1"
    manhattan = {"passes": True, "excepted": [("p", ["10001"])], "blocking": []}
    assert overnight.label_of(bad, [ok], True, [], 1, manhattan) == ("eligible", "")      # the Manhattan exception
    assert overnight.label_of(bad, [ok], True, [], 2, manhattan)[0] == "fails M1"         # only for a gate that exited 1


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
             "states": ["NJ", "NY"], "whole_states": False, "cap": None, "allowance": False, "waiver": False, "ok": False},
            {"channel": "WIFI", "district": "WIFI_01", "usd": 1.543e9, "lo": 0.85e9, "hi": 1.15e9,
             "states": ["CO", "ID"], "whole_states": True, "cap": 1.6e9, "allowance": True, "waiver": False, "ok": True}]
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


def test_an_interrupt_ends_and_reaps_the_stage_and_its_session():
    """The stage runs in its own session, so a Ctrl-C reaches only the launcher: `child` ends the stage's process
    group on any unwinding, leaving nothing running and nothing in LIVE."""
    import _thread
    import signal
    # the stage starts a grandchild and sleeps; both are in the stage's group
    # the second grandchild ignores SIGINT: the leader exits on the group's SIGINT and it is left running
    script = ("import signal, subprocess, sys, time; "
              "g = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)']); "
              "d = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'], "
              "preexec_fn=lambda: signal.signal(signal.SIGINT, signal.SIG_IGN)); "
              "print(g.pid, d.pid, flush=True); time.sleep(60)")
    with tempfile.TemporaryDirectory() as tmp:
        log = os.path.join(tmp, "s.log")
        seen = {}

        def interrupt():
            for _ in range(200):
                with overnight.LIVE_LOCK:
                    live = list(overnight.LIVE)
                if live and open(log).read().strip():
                    pids = open(log).read().split()
                    if len(pids) == 2:
                        seen["stage"], seen["grandchild"], seen["deaf"] = live[0].pid, int(pids[0]), int(pids[1])
                        break
                time.sleep(0.05)
            _thread.interrupt_main()
        threading.Thread(target=interrupt, daemon=True).start()
        t0, grace = time.time(), overnight.STOP_GRACE
        overnight.STOP_GRACE = 3.0       # the SIGINT-ignoring member is killed when the grace is up
        try:
            overnight.child([sys.executable, "-c", script], log, 60, time.time() + 120)
        except KeyboardInterrupt:
            pass
        else:
            raise AssertionError("the interrupt never reached the launcher")
        finally:
            overnight.STOP_GRACE = grace
    assert time.time() - t0 < 30 and not overnight.LIVE and {"stage", "grandchild", "deaf"} <= set(seen)
    for pid in (seen["stage"], seen["grandchild"], seen["deaf"]):
        for _ in range(50):         # a killed grandchild is reaped by init a moment later
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                break
            time.sleep(0.1)
        else:
            os.killpg(seen["stage"], signal.SIGKILL)
            raise AssertionError(f"process {pid} of the interrupted stage is still running")


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


def test_collect_hashes_and_merge():
    with tempfile.TemporaryDirectory() as tmp:
        for rel, body in (("w8-48-bal/r1/ledger.csv", b"a"), ("w8-48-bal/r1/m1.json", b"b"),
                          ("w8-50-bal/draw/ledger.csv", b"c")):
            os.makedirs(os.path.dirname(os.path.join(tmp, rel)), exist_ok=True)
            with open(os.path.join(tmp, rel), "wb") as fh:
                fh.write(body)
        ours = overnight.hash_tree(tmp, ["w8-48-bal", "w8-50-bal"])
    assert sorted(ours) == ["w8-48-bal/r1/ledger.csv", "w8-48-bal/r1/m1.json", "w8-50-bal/draw/ledger.csv"]
    listing = "".join(f"{s}  ./{p}\n" for p, s in ours.items())
    theirs = overnight.parse_shasum(listing)
    assert theirs == ours and overnight.compare_hashes(theirs, {**ours, "w8-48-bal/r1/summary.png": "x"}) == []
    bad = {**ours, "w8-48-bal/r1/m1.json": "0" * 64}
    del bad["w8-50-bal/draw/ledger.csv"]
    assert overnight.compare_hashes(theirs, bad) == ["differs w8-48-bal/r1/m1.json", "missing w8-50-bal/draw/ledger.csv"]
    code = {"commit": "c", "dirty": False, "diff_sha256": None}
    doc = overnight.grid_doc("m5", "/x", "abc", time.time() + 60, code)
    remote = overnight.grid_doc("m2", "/x", "abc", time.time() + 60, code)
    remote["points"]["w8-48-bal"].update(status="done", label="eligible", final="w8-48-bal/r1")
    remote["points"]["w8-48-bal-WH10"] = overnight.record(
        {"id": "w8-48-bal-WH10", "structure": "west8", "k": {"WH": 10}}, "m2", "w8-48-bal")
    assert overnight.remote_unlabelled(remote, "m2") == [
        "w8-48-bal-WH10", "w8-50-bal", "w8-50-filight", "w8-52-bal", "w8-52-filight", "w8-cmp-seed"]
    got = overnight.merge_remote(doc, remote, "m2", {"from": "m2"})
    assert len(got) == 7 and doc["points"]["w8-48-bal"]["label"] == "eligible"
    assert doc["points"]["w8-48-bal-WH10"]["parent"] == "w8-48-bal"
    assert doc["points"]["w8-48-bal"]["collected"] == {"from": "m2"} and doc["points"]["w1-48"]["status"] == "queued"
    for bad_remote in ({**remote, "extract_sha256": "zzz"}, {**remote, "host": "m5"}):
        try:
            overnight.check_remote(doc, bad_remote, "m2")
        except ValueError:
            pass
        else:
            raise AssertionError("a GRID.json of another extract or host was merged")


def _rec(pid, label, structure="ne_plains", final=None, reason=None, parent=None):
    ks = {"national": 15, "WH": 11, "FI": 20, "WIFI": 3}
    return {"id": pid, "structure": structure, "k": ks, "label": label, "reason": reason, "final": final,
            "status": "done" if label else "running", "parent": parent}


def _ordered(pid, label, key=None):
    return {"id": pid, "label": label, "key": key}


def test_morning_order_ranks_labels_and_pairs():
    rows = [_ordered("ne-52-filight", "eligible", (3, 1.0)), _ordered("w1-48", "stopped"),
            _ordered("ne-50-bal", "eligible", (2, 5.0)), _ordered("ne-52-bal", "eligible", (2, 0.5)),
            _ordered("ne-50-filight", "fails M1", (1, 0.0)), _ordered("nw49-48", "infeasible"),
            _ordered("w8-48-bal", "ineligible ($)", (4, 0.0)), _ordered("x", "error"), _ordered("y", "odd")]
    got = [r["id"] for r in overnight.morning_order(rows)]
    assert got == ["ne-52-bal", "ne-52-filight", "ne-50-bal", "ne-50-filight", "w8-48-bal", "nw49-48",
                   "w1-48", "x", "y"]


def test_needs_your_eye_skips_el_paso():
    ep = ("IFA/IFA_02: neck 5.10 km wide cuts off 3 ZIPs (79734...), 1.0% of its land area and 0.5% of its "
          "mass; cut 79718-79734 6.14 km")
    other = ("WH/WH_03: neck 4.00 km wide cuts off 9 ZIPs (10001...), 2.0% of its land area and 1.0% of its "
             "mass; cut 10001-10002 4.00 km")
    m = {"m1": {"flips": [{"district": "IFA/IFA_02", "strict": [ep], "gap_width": []},
                          {"district": "WH/WH_03", "strict": [], "gap_width": [other]}]},
         "dollars": [{"channel": "WIFI", "district": "WIFI_01", "usd": 1543.0, "lo": 850.0, "hi": 1150.0,
                      "cap": 1600.0, "allowance": True, "ok": True}],
         "land": [{"channel": "national", "state": "CA", "ratio": "32.10", "largest": "national_01",
                   "largest_km2": "90000.0", "smallest": "national_02", "smallest_km2": "2800.0", "over": "1"},
                  {"channel": "FI", "state": "TX", "ratio": "3.00", "over": "0"}]}
    got = overnight.eye_items("ne-48-bal", m)
    assert len(got) == 3
    assert "WH/WH_03, a neck across coverage gaps only" in got[0] and "79718" not in " ".join(got)
    assert "WIFI_01 1,543.0M on the whole-state allowance (up to 1,600.0M)" in got[1]
    assert "national CA in-state land ratio 32.10 beyond R = 10" in got[2]


REPORT = ("# r1\ndir: d\neligible: yes\nK: national 15 WH 11 FI 20 WIFI 3 = 49\n"
          "channel-state splits: 7: national:CA\ndefects: 2.5 = thin 1 + small 0 + crowded 0 + pieces 1.5\n"
          "shape: extent 1,234.5 km, 4 states per district\nbalance: worst 9.50%, mean 3.25%\n")


def test_morning_files_from_a_toy_grid():
    from PIL import Image
    doc = overnight.grid_doc("m5", "/hub/instance_descaled_usd.json.gz", "abcdef0123456789", time.time() + 60,
                             {"commit": "e82d6a4aaaa", "dirty": False, "diff_sha256": None})
    with tempfile.TemporaryDirectory() as tmp:
        fin = os.path.join(tmp, "ne-cmp-tierP", "r1")
        os.makedirs(fin)
        with open(os.path.join(fin, "score.txt"), "w") as fh:
            fh.write(REPORT)
        score.write_dollars(os.path.join(fin, "dollars.csv"), [
            {"channel": "WH", "district": f"WH_0{i}", "usd": u, "lo": 0.85e9, "hi": 1.15e9, "states": ["NY"],
             "whole_states": False, "cap": None, "allowance": False, "waiver": False, "ok": True}
            for i, u in ((1, 0.9e9), (2, 1.1e9))])
        with open(os.path.join(fin, "m1.json"), "w") as fh:
            json.dump({"strict": {"status": "pass"}, "gap_width": {"status": "pass"}, "flips": []}, fh)
        with open(os.path.join(fin, "land.csv"), "w") as fh:
            fh.write("channel,state,ratio,over\nWH,NY,12.50,1\nFI,PA,,0\n")
        Image.new("RGB", (300, 200), "red").save(os.path.join(fin, "summary.png"))
        assert overnight.map_png(fin) == os.path.join(fin, "summary.png")
        Image.new("RGB", (300, 200), "blue").save(os.path.join(fin, "zip_summary.png"))
        assert overnight.map_png(fin) == os.path.join(fin, "zip_summary.png")
        for c in ("WIFI", "national"):
            open(os.path.join(fin, f"zip_{c}.png"), "w").close()
        assert overnight.map_pages(fin) == [os.path.join(fin, x) for x in ("zip_summary.png", "zip_national.png", "zip_WIFI.png")]
        recs = [_rec("ne-cmp-tierP", "eligible", final="ne-cmp-tierP/r1"),
                _rec("w1-48", "stopped", "w1", reason="not started before the 8 h stop"),
                _rec("w8-48-bal", None, "west8")]
        rows = overnight.morning_order([overnight.point_row(tmp, r) for r in recs])
        assert [r["label"] for r in rows] == ["eligible", "stopped", "error"]
        assert rows[0]["key"] == (7, 2.5, 1234.5, 4, 0.095, 0.0325)
        md = overnight.morning_md(doc, rows, ["x"], "2026-10-13T12:00:00+00:00")
        pdf = os.path.join(tmp, "MORNING.pdf")
        overnight.morning_pdf(pdf, [(r["final"] and os.path.join(tmp, r["final"], "summary.png"),
                                     overnight.title_of(r["rec"])) for r in rows])
        with open(pdf, "rb") as fh:
            raw = fh.read()
    assert raw.startswith(b"%PDF") and len(re.findall(rb"/Type\s*/Page\b(?!s)", raw)) == 3
    lines = md.splitlines()
    table = [x for x in lines if re.match(r"^\| [123] \|", x)]
    assert table[0].startswith("| 1 | ne-cmp-tierP | ne_plains | national 15, WH 11, FI 20, WIFI 3 = 49 | 7 | 2.5 | ")
    assert "WH_01 -10.0% (900.0M)" in table[0] and "pass / pass" in table[0] and "12.5 (1 > R)" in table[0]
    assert "[map](ne-cmp-tierP/r1/summary.png)" in table[0]
    assert "| **stopped** | — |" in table[1] and "| **error** | — |" in table[2]
    assert "- **w8-48-bal** (error): no label (status running)" in lines
    assert any("#133" in x for x in lines) and "- x" in lines and "1 eligible, 1 stopped, 1 error." in md
    assert "`e82d6a4`" in md and "sha256 `abcdef012345`" in md


def test_index_rows_from_dollars_and_planned_tau():
    with tempfile.TemporaryDirectory() as tmp:
        fin = os.path.join(tmp, "ne-48-bal", "r2")
        os.makedirs(fin)
        score.write_dollars(os.path.join(fin, "dollars.csv"), [
            {"channel": c, "district": d, "usd": u, "lo": lo, "hi": hi, "states": ["NY"], "whole_states": cap,
             "cap": 1.6e9 if cap else None, "allowance": u > hi, "waiver": False, "ok": ok}
            for c, d, u, lo, hi, cap, ok in (
                ("WH", "WH_01", 0.8e9, 0.85e9, 1.15e9, False, False), ("WH", "WH_02", 1.0e9, 0.85e9, 1.15e9, False, True),
                ("WH", "WH_03", 1.15e9, 0.85e9, 1.15e9, False, True),
                ("WIFI", "WIFI_01", 1.543e9, 0.85e9, 1.15e9, True, True))])
        drawn = dict(_rec("ne-48-bal", "fails M1", final="ne-48-bal/r2"), k={"WH": 3, "WIFI": 1})
        plan = {"channels": {"national": {"usd_m": 15000.0, "k": 12, "whole_state_cap": False},
                             "WIFI": {"usd_m": 3200.0, "k": 4, "whole_state_cap": False}}}
        undrawn = dict(_rec("nw49-48", "infeasible", "nw49", reason="national: no plan"),
                       k={"national": 12, "WIFI": 4}, plan=plan)
        rows = [overnight.point_row(tmp, r) for r in (drawn, undrawn)]
        got = overnight.index_rows(rows)
    a, b = got
    assert (a["n"], a["k_total"], a["k_text"], a["drawn"]) == (1, 4, "WH 3 · WIFI 1", True)
    assert a["meaning"].startswith("WIFI = 15 NE+plains")
    wh, wifi = a["channels"]
    assert (wh["target_m"], wh["lo_m"], wh["hi_m"], wh["cap_m"], wh["out"]) == (1000.0, 850.0, 1150.0, None, 1)
    assert math.isclose(wh["avg_m"], 2950 / 3) and math.isclose(wh["avg_dev"], -50 / 3000)
    assert (wh["min_m"], wh["max_m"]) == (800.0, 1150.0)
    assert math.isclose(wh["min_dev"], -0.2) and math.isclose(wh["max_dev"], 0.15) and not wh["planned"]
    assert wifi["target_m"] == 1000.0 and wifi["cap_m"] == 1600.0 and wifi["out"] == 0      # window midpoint
    assert math.isclose(wifi["avg_dev"], 0.543) and wifi["min_m"] == wifi["max_m"] == 1543.0
    assert (b["n"], b["drawn"], b["k_total"], b["reason"]) == (2, False, 16, "national: no plan")
    nat, wifi = b["channels"]
    assert nat["planned"] and math.isclose(nat["avg_m"], 1250.0) and math.isclose(nat["avg_dev"], 0.0)
    assert math.isclose(wifi["avg_m"], 800.0) and math.isclose(wifi["avg_dev"], -0.2)
    assert nat["min_m"] is None and nat["out"] is None and wifi["cap_m"] is None
    md = overnight.index_md(got)
    assert "| **1** | ne-48-bal | ne_plains: " in md[4 + 2] and "| 983 (-1.7%) | 800 (-20.0%) | 1,150 (+15.0%) | 1 |" in md[6]
    assert "| infeasible; planned τ, not drawn | 16 = N 12 · WIFI 4 | national 12 | 1,250 |" in md[8]
    assert "| τ 1,250 (+0.0%) | — | — | — |" in md[8] and "| τ 800 (-20.0%) |" in md[9]
    pages = overnight.index_pages(got, (2600, 1500))
    assert len(pages) == 1 and pages[0].size == (2600, 1500)


def test_titles_and_fac_for_renders():
    rec = _rec("ne-50-bal", "fails M1")
    assert overnight.title_of(rec) == "ne-50-bal: ne_plains, K national 15, WH 11, FI 20, WIFI 3 = 49; FAILS M1"
    assert overnight.title_of(rec, "draw").endswith("(draw, not the final folder)")
    kid = _rec("ne-50-bal-WH10", "eligible", parent="ne-50-bal")
    assert overnight.title_of(kid).endswith("; eligible (re-run of ne-50-bal)")
    with tempfile.TemporaryDirectory() as tmp:
        fac = json.load(open(overnight.fac_file(tmp)))["fac"]
        for name in ("draw", "r1", "r2"):
            os.makedirs(os.path.join(tmp, "ne-50-bal", name))
            if name != "r2":
                open(os.path.join(tmp, "ne-50-bal", name, "ledger.csv"), "w").close()
        jobs = overnight.render_jobs(tmp, [{**rec, "final": "ne-50-bal/r1"}])
    assert fac == dict.fromkeys(sorted(score.DOLLARS), 1.0)
    assert [(os.path.basename(f), t.endswith("FAILS M1")) for f, t in jobs] == [("draw", False), ("r1", True)]


def test_smoke_slots_and_compare():
    assert overnight.peak_rss(3 * 2 ** 30, "darwin") == 3 * 2 ** 30
    assert overnight.peak_rss(1024, "linux") == 2 ** 20
    assert overnight.suggest_slots("m2", 3 * 2 ** 30) == 8
    assert overnight.suggest_slots("m2", 4 * 2 ** 30) == 6
    assert overnight.suggest_slots("m2", 40 * 2 ** 30) == 1
    assert overnight.suggest_slots("m5", 9 * 2 ** 30) == 12
    a = {"point": "ne-48-bal", "host": "m5", "extract_sha256": "e", "ledger_sha256": "l",
         "statuses": {"WH": "optimal"}, "code": {"commit": "c", "diff_sha256": None}, "peak_rss_bytes": 1}
    assert overnight.compare_smoke(a, {**a, "host": "m2"}) == []
    got = overnight.compare_smoke(a, {**a, "ledger_sha256": "m", "code": {"commit": "d", "diff_sha256": None}})
    assert got == ["ledger_sha256: 'l' vs 'm'", "code: ('c', None) vs ('d', None)"]
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "smoke.json")
        with open(path, "w") as fh:
            json.dump(a, fh)
        assert overnight.read_json_at(path) == a


def test_modules_load_whole_across_threads():
    """Points start on threads (2026-10-13 launch: 'contig_replan' seen half-loaded): every thread
    gets the module with its functions."""
    name = "contig_replan_threads"
    sys.modules.pop(name, None)
    path = os.path.join(overnight.HERE, "replan.py")
    got, start = [], threading.Barrier(8)

    def go():
        start.wait()
        got.append(hasattr(overnight._load(name, path), "banned_text"))
    ts = [threading.Thread(target=go) for _ in range(8)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    sys.modules.pop(name, None)
    assert got == [True] * 8


def test_subcommands_parse():
    p = overnight.parser()
    c = p.parse_args(["collect", "--from", "m2"])
    assert (c.src, c.ssh, c.remote_root, c.anyway, c.root) == ("m2", None, None, False, overnight.GRID_ROOT)
    m = p.parse_args(["morning", "--no-render"])
    assert m.no_render and m.jobs == 4 and m.func is overnight.cmd_morning
    s = p.parse_args(["smoke", "--compare", "a.json", "m2:/tmp/b.json"])
    assert s.compare == ["a.json", "m2:/tmp/b.json"] and s.point == "ne-48-bal" and s.func is overnight.cmd_smoke


# ------------------------------------------------ the base specs (the pre-launch gates, Slice 7)
NE_PLAINS = {"ME", "NH", "VT", "MA", "RI", "CT", "ID", "MT", "ND", "NE", "SD", "WY", "NM", "OK", "KS"}
WEST = {"CO", "ID", "MT", "ND", "NE", "NM", "SD", "WY"}
ALL = set(tdspec.CONUS_STATES)
FIVE = {"national_chase", "wells_wh", "wells_fi", "wh", "fi"}
NATIONAL_FINE = {"national_chase", "wells_wh", "wells_fi"}


def _base(structure):
    path = os.path.join(overnight.ROOT, overnight.STRUCTURES[structure][0])
    with open(path, encoding="utf-8") as fh:
        return tdspec.load(path), fh.read(), overnight.STRUCTURES[structure][1]


def _free(cs):
    return sorted(u for u, m in cs.modes.items() if m == "free")


def test_base_specs_load_and_fit_every_point():
    assert set(overnight.STRUCTURES) == {p["structure"] for p in overnight.POINTS}
    cells = {(u, f): 1.0 for u in ALL for f in FIVE}
    for structure in overnight.STRUCTURES:
        sp, text, rule = _base(structure)
        assert sp.name == f"main_{structure}" and re.search(r'(?m)^name = ".*"$', text)
        assert set(sp.fine_channels) == FIVE
        assert {"career", "edj", "imo", "priafs"} <= set(sp.planned_elsewhere)   # no owner total
        mass = overnight.unit_mass(sp, cells)                                     # units are states
        assert math.fsum(m for c in mass.values() for m in c.values()) == len(ALL) * len(FIVE)
        for pt in overnight.POINTS:
            if pt["structure"] == structure:
                assert set(pt["k"]) == set(sp.channels), pt["id"]
        free = {c: _free(cs) for c, cs in sp.channels.items()}
        if rule == "rule":
            assert not any(free.values()), structure                              # #76 per point
        else:
            assert free.pop("WIFI") == [] and all(free.values()), structure       # whole-state cap


def test_base_footprints():
    ne, _, _ = _base("ne_plains")
    assert ne.channels["WIFI"].units == NE_PLAINS and set(ne.channels["WIFI"].domain.values()) == {frozenset(FIVE)}
    assert all(ne.channels[c].units == ALL - NE_PLAINS for c in ("national", "WH", "FI"))
    assert ne.national.units == ALL - NE_PLAINS
    assert [_free(ne.channels[c]) for c in ("national", "WH", "FI")] == [            # s13_WH11's (D10)
        ["CA", "FL", "NY", "TX"], ["CA", "FL", "NJ", "NY", "PA", "TX"],
        ["CA", "FL", "NC", "NY", "OH", "PA", "TN", "TX"]]
    assert ne.channels["WIFI"].max_size == 9 and not ne.channels["WIFI"].listed_only

    w8, _, _ = _base("west8")
    s51 = tdspec.load(os.path.join(overnight.ROOT, "scenarios", "51_total_13n_11wh_24fi_3wifi.toml"))
    assert all(w8.channels[c] == s51.channels[c] for c in ("national", "WH", "FI"))  # D11
    assert w8.national == s51.national
    wifi = w8.channels["WIFI"]
    assert wifi.units == WEST and set(wifi.domain.values()) == {frozenset(FIVE)}
    assert (wifi.listed_only, wifi.extra_supports, wifi.max_size, wifi.max_dist_km) == (False, (), 8, 5000.0)
    assert set(wifi.modes.values()) == {"whole"}

    nw49, _, _ = _base("nw49")
    assert nw49.channels["national"].units == ALL and nw49.national.units == ALL
    assert set(nw49.channels["national"].domain.values()) == {frozenset(NATIONAL_FINE)}
    assert nw49.channels["WIFI"].units == ALL
    assert set(nw49.channels["WIFI"].domain.values()) == {frozenset({"wh", "fi"})}

    nw34, _, _ = _base("nw34")
    n34, n = nw34.channels["national"], ne.channels["national"]
    assert n34.units == ALL - NE_PLAINS and nw34.national.units == ALL - NE_PLAINS
    assert ((n34.eta, n34.max_size, n34.max_dist_km, n34.dist_km, n34.contact_caps, n34.margin)
            == (n.eta, n.max_size, n.max_dist_km, n.dist_km, n.contact_caps, n.margin))
    assert all(f == (FIVE if u in NE_PLAINS else {"wh", "fi"}) for u, f in nw34.channels["WIFI"].domain.items())
    assert nw34.channels["WIFI"].units == ALL

    w1, _, _ = _base("w1")
    assert list(w1.channels) == ["WIFI"] and w1.national is None
    assert w1.channels["WIFI"].units == ALL and set(w1.channels["WIFI"].domain.values()) == {frozenset(FIVE)}
    for s in ("nw49", "nw34", "w1"):                     # scenario 50's support values (policy)
        sp, _, _ = _base(s)
        w = sp.channels["WIFI"]
        assert (w.eta, w.max_size, w.max_dist_km, w.dist_km["CA"], w.margin) == (0.05, 6, 900.0, 1600.0, True)


def test_base_specs_take_the_launchers_rewrites():
    banned_text = overnight._replan().banned_text
    for structure in overnight.STRUCTURES:
        sp, text, rule = _base(structure)
        pt = next(p for p in overnight.POINTS if p["structure"] == structure)
        plan = {"channels": {c: {"k": k, "final_delta": 0.05} for c, k in pt["k"].items()}}
        copy = overnight.point_spec_text(text, pt["id"], plan)
        got = tdspec.parse(tomllib.loads(copy))
        assert got.name == pt["id"]
        assert {c: (cs.k, cs.delta, cs.final_delta) for c, cs in got.channels.items()} == \
            {c: (k, 0.02, 0.05) for c, k in pt["k"].items()}
        free = ({c: _free(cs) for c, cs in sp.channels.items() if _free(cs)} if rule == "base"
                else {c: ["CA", "TX"] for c in sp.channels})               # replan.py --free's rewrite
        out = tdspec.parse(tomllib.loads(banned_text(copy, [], free=free)))
        assert {c: _free(cs) for c, cs in out.channels.items() if c in free} == free, structure


# ------------------------------------------------------------------------------ the final label
class _FakeGrid:
    def __init__(self):
        self.added, self.updated, self.stages = [], {}, []

    def deadline(self):
        return time.time() + 600

    def update(self, pid, **fields):
        self.updated.setdefault(pid, {}).update(fields)

    def add(self, rec):
        self.added.append(rec)

    def stage(self, pid, name, info):
        self.stages.append(name)


class _FinalRunner(overnight.Runner):
    """A runner whose stages are canned: `gate` returns `rc`/`stop` and writes `evidence` (a callable of the
    folder and the path) when given."""

    def __init__(self, root, extract, rc=0, stop=None, evidence=None):
        super().__init__(_FakeGrid(), root, "m5", extract, {})
        self.rc, self.stop, self.evidence, self.calls = rc, stop, evidence, []

    def stage(self, pid, name, cmd, log, cap, env=None):
        self.calls.append((name, cmd))
        if name == "gate" and self.evidence:
            self.evidence(cmd[-3], cmd[-1])
        return {"rc": self.rc, "stop": self.stop, "seconds": 0.0}


def _final_folder(tmp, m1_a=900.0, m1_b=900.0, m1_status="pass", dollars_ok=1, border=True):
    """A dollar extract whose `wh` rate is 1e6 (cells a1, a2 and the rest) and a final folder `r1` whose districts
    WH_01, WH_02 own a1, a2; `dollars.csv` says in-window (`dollars_ok`) whatever the extract's masses are."""
    from td import data
    whole = score.DOLLARS["wh"] / 1e6
    extract = os.path.join(tmp, "extract.json.gz")
    data.write(data.Extract(("wh",), ["a1", "a2", "a3"], ["wh"] * 3, [m1_a, m1_b, whole - m1_a - m1_b],
                            [{}] * 3, [0.0] * 3), extract)
    final = os.path.join(tmp, "toy-pt", "r1")
    os.makedirs(final)
    open(os.path.join(final, "ledger.csv"), "w").write(
        "zip_code,current_channel,state,model_channel,district,reason,m_rel\n"
        "a1,wh,A,WH,WH_01,,1.0\na2,wh,A,WH,WH_02,,1.0\n")
    open(os.path.join(final, "districts.csv"), "w").write("channel,district,drawn_mass\nWH,WH_01,1\nWH,WH_02,1\n")
    ok = {"status": m1_status, "summary": "toy"}
    json.dump({"gap_width": ok, "strict": ok}, open(os.path.join(final, "m1.json"), "w"))
    open(os.path.join(final, "dollars.csv"), "w").write(
        "channel,district,usd_m,lo_m,hi_m,whole_state_cap_m,allowance,ok\n"
        f"WH,WH_01,900.0,850,1150,,0,{dollars_ok}\nWH,WH_02,900.0,850,1150,,0,{dollars_ok}\n")
    open(os.path.join(final, "score.txt"), "w").write("# toy\ndir: x\neligible: yes\n")
    return extract, final


def _evidence(final, path, necks=0, side=("10001",)):
    doc = {"folder": os.path.abspath(final), "rc": 1, "status": "fail", "summary": "1 detached piece",
           "diagnostic": None, "counts": {"necks": necks}, "items": ["WH/WH_01: detached piece of 1 ZIPs (10001...)"],
           "sides": {"necks": {}, "pieces": [["WH_01", "10001", 1, list(side)]]}}
    json.dump(doc, open(path, "w"))


def _label_final(tmp, **kw):
    runner_kw = {k: kw.pop(k) for k in ("rc", "stop", "evidence") if k in kw}
    extract, final = _final_folder(tmp, **kw)
    runner = _FinalRunner(tmp, extract, **runner_kw)
    pt = {"id": "toy-pt", "structure": "ne_plains", "k": {"WH": 2}, "parent": None}
    return runner, runner._label_final(pt, os.path.join(tmp, "toy-pt"), final)


def test_the_final_label_needs_a_completed_gate_on_the_final_folder():
    with tempfile.TemporaryDirectory() as tmp:
        runner, got = _label_final(tmp)
        assert got[:2] == ("eligible", "") and [n for n, _ in runner.calls] == ["gate"]
        gate_cmd = runner.calls[0][1]
        assert gate_cmd[2].endswith("ifa_index_night.py") and gate_cmd[-4:-2] == ["--gate", got[2]]
        assert gate_cmd[-1] == os.path.join(tmp, "toy-pt", "gate-evidence.json")
    for rc in (2, 137, None):               # a gate that crashed or was killed never passes, whatever m1.json says
        with tempfile.TemporaryDirectory() as tmp:
            label, reason = _label_final(tmp, rc=rc)[1][:2]
            assert label == "fails M1" and "the gate (check.py) exited" in reason, (rc, label)
    with tempfile.TemporaryDirectory() as tmp:       # exit 1 with no evidence adjudicates nothing
        label, reason = _label_final(tmp, rc=1, m1_status="fail")[1][:2]
        assert label == "fails M1" and "gate evidence unavailable" in reason
    with tempfile.TemporaryDirectory() as tmp:       # killed at its cap: the point is stopped
        try:
            _label_final(tmp, stop="cap")
        except overnight.Stop as e:
            assert e.label == "stopped" and "final gate" in e.reason
        else:
            raise AssertionError("a gate killed at its cap was labelled")


def test_the_final_label_takes_the_manhattan_exception_from_the_gate_evidence_only():
    with tempfile.TemporaryDirectory() as tmp:       # a Manhattan-only piece, necks measured: m1.json's fail is waived
        label, reason = _label_final(tmp, rc=1, m1_status="fail", evidence=_evidence)[1][:2]
        assert (label, reason) == ("eligible", "")
    with tempfile.TemporaryDirectory() as tmp:       # the piece is not Manhattan
        label, reason = _label_final(tmp, rc=1, m1_status="fail",
                                     evidence=lambda f, p: _evidence(f, p, side=("30001",)))[1][:2]
        assert label == "fails M1" and "outside the Manhattan exception" in reason
    with tempfile.TemporaryDirectory() as tmp:       # Manhattan-only, but the necks were never measured
        label, reason = _label_final(tmp, rc=1, m1_status="fail",
                                     evidence=lambda f, p: _evidence(f, p, necks=None))[1][:2]
        assert label == "fails M1" and "outside the Manhattan exception" in reason
    with tempfile.TemporaryDirectory() as tmp:       # a stale record of another folder is not this gate's
        def stale(final, path):
            _evidence(final + "-other", path)
        label = _label_final(tmp, rc=1, m1_status="fail", evidence=stale)[1][0]
        assert label == "fails M1"


def test_the_final_label_judges_the_window_on_unrounded_full_extract_dollars():
    for m1, want in ((849.99999975, "ineligible ($)"), (850.0, "eligible"), (1150.0, "eligible"),
                     (1150.00000025, "ineligible ($)")):
        with tempfile.TemporaryDirectory() as tmp:
            runner, got = _label_final(tmp, m1_a=m1)          # dollars.csv says ok: the full extract decides
            assert got[0] == want, (m1, got[:2])
            if want != "eligible":
                assert got[1].startswith("WH_01 ") and "outside" in got[1]
    with tempfile.TemporaryDirectory() as tmp:       # the earned re-run is read off the exact rows too
        runner, got = _label_final(tmp, m1_a=849.99999975)
        assert "re-run toy-pt-WH1" in got[1] and [r["id"] for r in runner.grid.added] == ["toy-pt-WH1"]
    with tempfile.TemporaryDirectory() as tmp:       # a ledger district districts.csv lacks stops the point
        extract, final = _final_folder(tmp)
        open(os.path.join(final, "districts.csv"), "w").write("channel,district,drawn_mass\nWH,WH_01,1\n")
        try:
            _FinalRunner(tmp, extract)._label_final({"id": "toy-pt", "structure": "ne_plains", "k": {"WH": 2},
                                                     "parent": None}, os.path.join(tmp, "toy-pt"), final)
        except overnight.Stop as e:
            assert e.label == "error" and "exact dollar window" in e.reason and "WH_02" in e.reason
        else:
            raise AssertionError("a ledger district missing from districts.csv was labelled")
