"""tools/exp/contig/sealed.py (the sealed-region driver, 2026-10-14) and glue.py on toy specs, toy
polygon graphs and hand-computed values: P.json validation, a region's spec copy and plan, the
dry-run command chain of a two-region point, the retry at `k_alt`, the shape limits, the labels, the
index, and the glue repair (a path through zero-opportunity ZCTAs, a donor that would be cut or
necked, a ZCTA with opportunity never moved)."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import math
import os
import re
import sys
import tempfile
import tomllib
import types

from td import spec as tdspec

HERE = os.path.dirname(os.path.abspath(__file__))
CONTIG = os.path.join(HERE, "..", "tools", "exp", "contig")


def _import(name, file):
    spec = importlib.util.spec_from_file_location(name, os.path.join(CONTIG, file))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


sealed = _import("contig_sealed", "sealed.py")
glue = _import("contig_glue", "glue.py")
overnight = sealed.overnight

TOY = """[scenario]
name = "toy"
fine_channels = ["national_chase", "wh"]
planned_elsewhere = ["career", "edj", "fi", "ifa", "imo", "priafs", "wells_fi", "wells_wh"]

[channels.national]
k = 2
domain = [{ units = "all", fine = ["national_chase"] }]
mode = "whole"
free = ["CA", "NY"]
eta = 0.05
delta = 0.1
max_size = 3

[channels.WIFI]
k = 2
domain = [{ units = "all", fine = ["wh"] }]
mode = "whole"
eta = 0.05
"""
CELLS = {("CA", "national_chase"): 1500.0, ("TX", "national_chase"): 700.0, ("NY", "national_chase"): 2300.0,
         ("FL", "national_chase"): 2100.0, ("CA", "wh"): 1000.0, ("TX", "wh"): 900.0, ("NY", "wh"): 1000.0,
         ("FL", "wh"): 1000.0}
TOTALS = {"toy-pt": {"national": 6, "WIFI": 4}}


def _toy_file(tmp):
    path = os.path.join(tmp, "toy.toml")
    with open(path, "w") as fh:
        fh.write(TOY)
    return path


def _doc(**over):
    pt = {"id": "toy-pt", "structure": "toy", "channels": {
        "national": {"regions": [{"name": "south", "states": ["CA", "TX"], "k": 2}], "rest": True},
        "WIFI": {"regions": [{"name": "south", "states": ["CA", "TX"], "k": 2}], "rest": True}}}
    pt.update(over)
    return {"points": [pt]}


def _validate(doc, tmp, **kw):
    return sealed.validate_partition(doc, {"toy": (_toy_file(tmp), "base")}, TOTALS, **kw)


def _refused(doc, tmp, *words):
    try:
        _validate(doc, tmp)
    except sealed.PartitionError as e:
        text = str(e)
        assert all(w in text for w in words), (words, text)
        return text
    raise AssertionError(f"accepted, wanted {words}")


# ------------------------------------------------------------------------------ P.json
def test_partition_groups_channels_with_one_state_set_into_a_run_and_takes_the_rest_k_from_the_point():
    with tempfile.TemporaryDirectory() as tmp:
        (pt,) = _validate(_doc(), tmp)
    south, rest = pt["runs"]
    assert south["name"] == "south" and south["states"] == ("CA", "TX") and south["ks"] == {"national": 2, "WIFI": 2}
    assert rest["name"] == "rest" and len(rest["states"]) == 47 and "CA" not in rest["states"]
    assert rest["ks"] == {"national": 4, "WIFI": 2}                    # k_total 6 and 4 less the region's 2
    assert pt["channels"]["national"]["rest_k"] == 4


def test_partition_refuses_overlap_gaps_unlisted_channels_and_clashing_state_sets():
    with tempfile.TemporaryDirectory() as tmp:
        nat = {"regions": [{"name": "a", "states": ["CA", "TX"], "k": 2}, {"name": "b", "states": ["TX", "NY"], "k": 1}],
               "rest": True}
        _refused(_doc(channels={"national": nat, "WIFI": {"regions": [], "rest": True}}), tmp, "TX is also in region 'a'")
        # rest false: every footprint state must be in a region
        gap = {"regions": [{"name": "a", "states": ["CA", "TX"], "k": 2}], "rest": False}
        text = _refused(_doc(channels={"national": gap, "WIFI": {"regions": [], "rest": True}}), tmp,
                        "rest is false", "are in no region")
        assert "NY" in text
        _refused(_doc(channels={"national": {"regions": [], "rest": True}}), tmp, "channel WIFI of toy is not listed")
        # a state set in one channel only partly in another's: merge.py takes one partition per point
        wifi = {"regions": [{"name": "w", "states": ["CA", "NY"], "k": 2}], "rest": True}
        _refused(_doc(channels={"national": _doc()["points"][0]["channels"]["national"], "WIFI": wifi}), tmp,
                 "overlap", "one partition per point")
        # a channel with footprint states in a run must list a region of exactly that set
        only_nat = {"national": _doc()["points"][0]["channels"]["national"], "WIFI": {"regions": [], "rest": True}}
        _refused(_doc(channels=only_nat), tmp, "WIFI has footprint states in run 'south'")
        # rest with no k_total, k_total below the regions' K, a k_alt equal to k, a bad pair
        _refused(_doc(id="other", channels={
            "national": {"regions": [{"name": "s", "states": ["CA"], "k": 1}], "rest": True},
            "WIFI": {"regions": [{"name": "s", "states": ["CA"], "k": 1}], "rest": True}}), tmp, "rest needs k_total")
        _refused(_doc(channels={"national": {"regions": [{"name": "south", "states": ["CA", "TX"], "k": 6}], "rest": True,
                                             "k_total": 6}, "WIFI": _doc()["points"][0]["channels"]["WIFI"]}), tmp,
                 "leaves no district for the rest")
        _refused(_doc(channels={"national": {"regions": [{"name": "south", "states": ["CA", "TX"], "k": 2, "k_alt": 2,
                                                          "forbid": ["DE_VA"]}], "rest": True},
                                "WIFI": _doc()["points"][0]["channels"]["WIFI"]}), tmp, "k_alt equals k", "forbid pair")
        _refused(_doc(structure="nope"), tmp, "structure 'nope'")


def test_partition_accepts_the_example_file_on_the_real_structures():
    path = os.path.join(HERE, "..", "scenarios", "regions", "main", "sealed_example.json")
    (pt,) = sealed.load_partition(path)
    assert pt["id"] == "ne-48-bal" and [r["name"] for r in pt["runs"]] == ["corridor", "rest-FI-WH-national", "rest-WIFI"]
    corridor, rest, wifi = pt["runs"]
    assert corridor["ks"] == {"FI": 6, "WH": 3, "national": 3} and rest["ks"] == {"FI": 15, "WH": 7, "national": 11}
    assert wifi["ks"] == {"WIFI": 3} and len(corridor["states"]) + len(rest["states"]) + len(wifi["states"]) == 49
    for c, total in overnight.POINTS[0]["k"].items():
        assert sum(r["ks"].get(c, 0) for r in pt["runs"]) == total


# ------------------------------------------------------------------------------ the spec copy
def test_region_plan_and_spec_copy_by_hand():
    with tempfile.TemporaryDirectory() as tmp:
        sp = tdspec.load(_toy_file(tmp))
    plan = sealed.region_plan(sp, ("CA", "TX"), {"national": 2, "WIFI": 2}, CELLS, "base")
    nat, wifi = plan["channels"]["national"], plan["channels"]["WIFI"]
    assert nat["usd_m"] == 2200.0 and nat["tau_m"] == 1100.0 and nat["free"] == ["CA"]       # base free CA, NY not in the region
    assert nat["final_delta"] == 0.0909                                                       # 100 / 1100 below the window lo 1000
    assert wifi["tau_m"] == 950.0 and wifi["final_delta"] == 0.1052 and wifi["free"] == []    # 100 / 950 = 0.10526
    assert plan["absent"] == [] and plan["infeasible"] == {}
    text = sealed.run_spec_text(TOY, "toy-pt", "south", ("CA", "TX"), plan,
                                forbid={("CA", "TX"), ("DE", "VA")}, max_size=5)
    raw = tomllib.loads(text)
    assert raw["scenario"]["name"] == "toy-pt-south"
    n, w = raw["channels"]["national"], raw["channels"]["WIFI"]
    assert (n["k"], n["delta"], n["final_delta"], n["margin"], n["max_size"], n["free"]) == (2, 0.02, 0.0909, False, 5, ["CA"])
    assert (w["k"], w["delta"], w["final_delta"], w["margin"], w["max_size"]) == (2, 0.02, 0.1052, False, 5)
    assert n["forbid_pairs"] == [["CA", "TX"]] and w["forbid_pairs"] == [["CA", "TX"]]       # DE-VA is outside the run
    assert "free" not in w
    tdspec.parse(raw)                                                                         # still a spec


def test_region_with_a_channel_absent_and_a_k_outside_the_window():
    with tempfile.TemporaryDirectory() as tmp:
        sp = tdspec.load(_toy_file(tmp))
    cells = {k: v for k, v in CELLS.items() if k[1] == "national_chase"}
    plan = sealed.region_plan(sp, ("CA", "TX"), {"national": 2, "WIFI": 9}, cells, "base")
    assert plan["absent"] == ["WIFI"] and list(plan["channels"]) == ["national"]
    bad = sealed.region_plan(sp, ("CA", "TX"), {"national": 1, "WIFI": 2}, cells, "base")      # 2200 over one district
    assert "national" in bad["infeasible"] and "outside the dollar window" in bad["infeasible"]["national"]


# ------------------------------------------------------------------------------ the dry run
def test_dry_run_prints_the_chain_of_a_two_region_point_and_writes_nothing():
    with tempfile.TemporaryDirectory() as tmp:
        (pt,) = _validate(_doc(), tmp)
        root = os.path.join(tmp, "root")
        os.makedirs(root)
        a = types.SimpleNamespace(root=root, extract="/x/extract.json.gz", max_size=None, drawable_alone=True)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = sealed.cmd_dry_run(a, [pt], CELLS, dict(sealed.CAPS), {("CA", "TX")})
        assert rc == 0 and os.listdir(root) == []
        off = io.StringIO()
        with contextlib.redirect_stdout(off):
            sealed.cmd_dry_run(types.SimpleNamespace(root=root, extract="/x/e.json.gz", max_size=None, drawable_alone=False),
                               [pt], CELLS, dict(sealed.CAPS), set())
    text = out.getvalue()
    stages = re.findall(r"^\[(\w+), cap (\d+) s", text, re.M)
    names = [s for s, _ in stages]
    assert names == ["replan", "draw", "r1", "glue"] * 2 + ["merge", "gate", "score", "land"]
    assert dict(stages[:4]) == {"replan": "600", "draw": "2700", "r1": "1800", "glue": "600"}
    lines = {m.group(1): m.group(0) for m in re.finditer(r"^\[(\w+), cap .*$", text, re.M)}
    first = text.split("==== run rest")[0]
    assert "sealed.py replan" in first and "--states CA,TX" in first and "--time-limit 2295" in first
    assert re.search(r"sealed\.py replan .*--states CA,TX --time-limit 100 --drawable-alone", first)    # plancheck B on by default
    assert re.search(r"run\.py \S+/south/spec\.toml .*--land-ratio 10 .*--jobs 2 --states CA,TX", first)
    assert re.search(r"repair\.py \S+/south/draw --out \S+/south/r1 .*--keep-support --flow .*--states CA,TX", first)
    assert "--budget 1170" in first and "--window" not in first                                # two channels: no one window
    assert re.search(r"glue\.py \S+/south/r1 --out \S+/south/glue .*--states CA,TX", first)
    assert "forbid_pairs = [[\"CA\", \"TX\"]]" in first and 'margin = false' in first
    merge = lines["merge"]
    assert " CA+TX=" in merge and "/south/glue " in merge and "/rest/glue " in merge
    assert "--rate 1 --gap-width" in merge and "--window" not in merge
    assert "k_alt" not in text
    assert "--drawable-alone" not in off.getvalue()                                      # --no-drawable-alone


def test_repair_window_only_for_a_run_of_one_channel():
    with tempfile.TemporaryDirectory() as tmp:
        sp = tdspec.load(_toy_file(tmp))
    cells = {k: v for k, v in CELLS.items() if k[1] == "wh"}
    plan = sealed.region_plan(sp, ("CA", "TX"), {"national": 1, "WIFI": 2}, cells, "base")
    assert sealed.window_of(plan) == "850,1600"          # WIFI owns whole states alone: up to the $1.6B allowance
    two = sealed.region_plan(sp, ("CA", "TX"), {"national": 2, "WIFI": 2}, CELLS, "base")
    assert sealed.window_of(two) is None
    assert sealed.merge_window(sp) is None


# ------------------------------------------------------------------------------ the retry at k_alt
class _Stub(sealed.Driver):
    """A driver whose attempts and stages are canned: the order of the calls is what is tested."""

    def __init__(self, *a, outcomes, **kw):
        super().__init__(*a, **kw)
        self.outcomes, self.calls = list(outcomes), []

    def _attempt(self, pt, run, adir, ks, tag):
        self.calls.append((tag, dict(ks)))
        failing = self.outcomes.pop(0)
        plan = {"channels": {c: {"lo_m": 1.0, "hi_m": 2.0} for c in ks}}
        return {"dir": adir, "draw": os.path.join(adir, "draw"), "ks": ks, "plan": plan, "failing": failing,
                "failures": {c: {"reasons": ["drawing status infeasible"], "groups": []} for c in failing},
                "contig": {"channels": {c: {"status": "infeasible" if c in failing else "connected"} for c in ks}}}

    def stage(self, pid, name, cmd, log, cap, env=None):
        self.calls.append(name)
        return {"rc": 0, "stop": None, "seconds": 0.0}


CELLS_K = {**CELLS, ("CA", "national_chase"): 2500.0, ("TX", "national_chase"): 1700.0}   # south: $4,200M, K 3 or 4


def _stub_driver(tmp, k_alt, outcomes, cells=CELLS_K):
    doc = _doc()
    doc["points"][0]["channels"]["national"]["regions"][0].update(k=3, **({"k_alt": k_alt} if k_alt else {}))
    (pt,) = _validate(doc, tmp)
    extract = os.path.join(tmp, "extract.json.gz")
    open(extract, "wb").write(b"toy")
    grid = sealed.open_state(tmp, "m5", extract, 1.0, "p", "sha", [pt])
    drv = _Stub(grid, tmp, "m5", extract, cells, {pt["id"]: pt}, dict(sealed.CAPS), set(), None, sealed.load_limits(None),
                outcomes=outcomes)
    return drv, pt, pt["runs"][0]


def _stops(drv, pt, run, tmp):
    try:
        drv._chain(pt, run, os.path.join(tmp, "toy-pt", "south"))
    except sealed.Stop as e:
        assert e.label == sealed.NO_DRAWING, e.label
        return e
    raise AssertionError("a run with a failing drawing went on to the repair")


def _attempts(drv):
    return [c for c in drv.calls if isinstance(c, tuple)]


def test_a_drawing_that_ends_infeasible_is_redrawn_once_at_k_alt_and_the_better_one_goes_on():
    with tempfile.TemporaryDirectory() as tmp:
        drv, pt, run = _stub_driver(tmp, 4, [["national"], []])
        assert run["ks"] == {"national": 3, "WIFI": 2} and run["k_alt"] == {"national": 4}
        drv._chain(pt, run, os.path.join(tmp, "toy-pt", "south"))
        assert _attempts(drv) == [("", {"national": 3, "WIFI": 2}), (".alt", {"national": 4, "WIFI": 2})]
        rec = drv.grid.get("toy-pt")["runs"]["south"]
        assert rec["ks_used"] == {"national": 4, "WIFI": 2} and rec["draw_failing"] == []
        assert rec["status"] == "done" and rec["final"] == os.path.join("toy-pt", "south", "alt", "draw")
        assert "0 channels failing at k_alt, 1 at k" in rec["retry"]["result"]
        assert "south.r1" in drv.calls and "south.glue" in drv.calls          # the repair goes on from the alt folder


def test_the_retry_keeps_the_first_drawing_when_k_alt_is_no_better_and_needs_a_k_in_the_window():
    with tempfile.TemporaryDirectory() as tmp:
        drv, pt, run = _stub_driver(tmp, 4, [["national"], ["national"]])
        _stops(drv, pt, run, tmp)                                         # neither drawing is connected: the run stops
        rec = drv.grid.get("toy-pt")["runs"]["south"]
        assert rec["ks_used"] == {"national": 3, "WIFI": 2} and rec["draw_failing"] == ["national"]
        assert "0 channels" not in rec["retry"]["result"] and not any(isinstance(c, str) and c.startswith("south.r") for c in drv.calls)
    with tempfile.TemporaryDirectory() as tmp:
        drv, pt, run = _stub_driver(tmp, 1, [["national"]])               # 4,200M over one district: no final δ
        _stops(drv, pt, run, tmp)
        assert _attempts(drv) == [("", {"national": 3, "WIFI": 2})]
        assert "no final δ in the window" in drv.grid.get("toy-pt")["runs"]["south"]["retry"]["result"]
    with tempfile.TemporaryDirectory() as tmp:
        drv, pt, run = _stub_driver(tmp, None, [["national"]])            # no k_alt listed: no retry
        _stops(drv, pt, run, tmp)
        assert _attempts(drv) == [("", {"national": 3, "WIFI": 2})]
        assert drv.grid.get("toy-pt")["runs"]["south"]["retry"] is None


# ------------------------------------------------------------------------------ a strict drawing
CONTIG_BAD = {"channels": {
    "national": {"status": "connected", "connected": False, "undrawn_zctas": 6475, "fixed_split": [],
                 "groups": [{"districts": ["NC+SC#1", "NC+VA#1"], "units": ["NC"], "free_zctas": 853, "status": "connected",
                             "seconds": 42.6, "gap": 0.0},
                            {"districts": ["NY#1", "NY#2"], "units": ["NY"], "free_zctas": 1200, "status": "infeasible",
                             "seconds": 310.0, "gap": None}]},
    "WH": {"status": "optimal", "connected": True, "undrawn_zctas": 0, "fixed_split": [], "groups": []},
    "FI": {"status": "unknown", "connected": False, "undrawn_zctas": 0, "fixed_split": [],
           "groups": [{"districts": ["PA#1"], "units": ["PA"], "free_zctas": 40, "status": "unknown", "seconds": 900.0,
                       "gap": 0.3}]}}}


def test_a_drawing_with_undrawn_zctas_or_a_group_not_connected_is_a_failure():
    got = sealed.drawing_failures(CONTIG_BAD)
    assert sorted(got) == ["FI", "national"]                       # WH is optimal with nothing undrawn
    assert "6475 undrawn ZCTAs" in got["national"]["reasons"][0]
    assert [g["districts"] for g in got["national"]["groups"]] == [["NY#1", "NY#2"]]   # the group that failed, not the connected one
    assert got["FI"]["reasons"] == ["drawing status unknown"]
    text = sealed.failure_text(got)
    assert "national: 6475 undrawn ZCTAs" in text and "NY#1+NY#2 [NY] infeasible" in text and "FI: drawing status unknown" in text
    ok = {"channels": {"WH": CONTIG_BAD["channels"]["WH"], "x": {"status": "connected", "connected": True,
                                                                  "undrawn_zctas": 0, "fixed_split": []}}}
    assert sealed.drawing_failures(ok) == {}
    held = {"channels": {"x": {"status": "connected", "connected": False, "undrawn_zctas": 0, "fixed_split": ["A#1"]}}}
    assert "districts split by fixed bodies" in sealed.drawing_failures(held)["x"]["reasons"][0]


def test_a_fake_draw_folder_with_undrawn_zctas_is_never_repaired_or_merged():
    with tempfile.TemporaryDirectory() as tmp:
        drv, pt, run = _stub_driver(tmp, None, [])
        real = sealed.Driver._attempt                                 # the real attempt, reading the folder
        drv._attempt = lambda *a: real(drv, *a)
        rdir = os.path.join(tmp, "toy-pt", "south")
        out = os.path.join(rdir, "draw")
        os.makedirs(out)
        open(os.path.join(out, "ledger.csv"), "w").write("zip_code\n")
        json.dump({"status": "done"}, open(os.path.join(out, "manifest.json"), "w"))
        json.dump(CONTIG_BAD, open(os.path.join(out, "contig.json"), "w"))
        open(os.path.join(rdir, "spec.toml"), "w").write("# canned\n")
        drv.drawable_alone = True
        drv.pending["toy-pt"] = 1                                     # this run is the point's last: `finish` follows
        drv.region({"id": "toy-pt/south", "point": "toy-pt", "run": run, "need": 2})
        assert drv.calls == []                                        # no replan, no repair, no glue, no merge launched
        rec = drv.grid.get("toy-pt")
        assert rec["runs"]["south"]["status"] == sealed.NO_DRAWING and rec["runs"]["south"]["draw_failures"]["national"]
        assert rec["label"] == sealed.NO_DRAWING and "6475 undrawn ZCTAs" in rec["reason"] and "NY#1+NY#2" in rec["reason"]
        assert rec["final"] is None and not os.path.exists(os.path.join(tmp, "toy-pt", "merged"))


def test_plan_report_lists_the_supports_the_drawable_alone_check_banned():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "replan.json")
        json.dump({"channels": {"national": {"delta": 0.02, "status": "optimal", "plan_check": {
            "tested": [{"support": "CA+NV"}, {"support": "NY+NJ"}], "bans": [{"support": "NY+NJ"}],
            "unknown": [{"support": "OR+WA"}]}}, "WH": {"delta": 0.02}}}, open(path, "w"))
        rep = sealed.plan_report(path)
    assert rep["national"] == {"delta": 0.02, "status": "optimal", "bans": ["NY+NJ"], "unknown": ["OR+WA"], "tested": 2}
    assert rep["WH"]["bans"] == [] and rep["WH"]["tested"] == 0


# ------------------------------------------------------------------------------ labels, shape, index
def test_labels_follow_m1_then_band_then_hard_shape():
    ok = {"status": "pass", "summary": "ok"}
    rows = [{"district": "WIFI_01", "channel": "WIFI", "usd": 900.0, "lo": 850.0, "hi": 1150.0, "cap": None, "ok": True}]
    out = dict(rows[0], district="WIFI_02", usd=800.0, ok=False)
    br = [{"channel": "WIFI", "district": "WIFI_01", "measure": "bite", "value": 0.4, "limit": "max 0.3"}]
    assert sealed.label_point({"status": "fail", "summary": "1 necks"}, rows, [], False)[0] == "fails M1"
    assert sealed.label_point(ok, rows + [out], [], False)[0] == "outside band"
    assert sealed.label_point(ok, rows, br, False) == ("passes", "")                     # report only
    label, why = sealed.label_point(ok, rows, br, True)
    assert label == "fails shape" and "1 breaches" in why
    assert sealed.label_point(ok, rows, [], True) == ("passes", "")
    assert sealed.worst_run({"a": {"status": "done"}}) is None
    assert sealed.worst_run({"a": {"status": "infeasible", "reason": "x"}, "b": {"status": "stopped", "reason": "y"}})[0] == "stopped"


def test_shape_limits_file_and_breaches():
    rows = [{"channel": "WH", "district": "WH_01", "hull_fill": 0.5, "bite": 0.05, "aspect": 2.0, "longest_axis_km": 800.0,
             "doughnut": 0, "doughnut_soft": 0},
            {"channel": "WH", "district": "WH_02", "hull_fill": 0.2, "bite": 0.4, "aspect": 5.0, "longest_axis_km": 1500.0,
             "doughnut": 1, "doughnut_soft": 1}]
    got = sealed.shape_breaches(rows, {"hull_fill": {"min": 0.3}, "bite": {"max": 0.3}, "doughnut": {"max": 0}})
    assert sorted((b["district"], b["measure"]) for b in got) == [("WH_02", "bite"), ("WH_02", "doughnut"), ("WH_02", "hull_fill")]
    assert sealed.shape_breaches(rows, {}) == []
    s = sealed.shape_summary(rows)["WH"]
    assert s["hull_fill_min"] == 0.2 and s["bite_max"] == 0.4 and s["doughnuts"] == 1 and s["longest_axis_km_max"] == 1500.0
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "L.json")
        json.dump({"hard": True, "limits": {"bite": {"max": 0.3}}}, open(path, "w"))
        assert sealed.load_limits(path) == {"hard": True, "limits": {"bite": {"max": 0.3}}}
        assert sealed.load_limits(None) == {"hard": False, "limits": {}}       # report only by default
        json.dump({"limits": {"not_a_measure": {"max": 1}}}, open(path, "w"))
        try:
            sealed.load_limits(path)
            raise AssertionError("accepted an unknown measure")
        except sealed.PartitionError as e:
            assert "not_a_measure" in str(e)


def test_index_rows_and_markdown():
    doc = {"root": "/x/sealed", "extract": "e.json.gz", "partition": {"path": "P.json", "sha256": "ab" * 32},
           "points": {"toy-pt": {
               "id": "toy-pt", "structure": "toy", "label": "fails M1", "status": "done", "reason": "M1: fail, 1 necks",
               "runs": {"south": {"status": "done", "states": ["CA", "TX"], "ks": {"national": 2, "WIFI": 2},
                                  "ks_used": {"national": 3, "WIFI": 2}, "draw": {"national": "connected"},
                                  "retry": {"result": "0 channels failing at k_alt, 1 at k"},
                                  "glue": {"national": {"glued": 0, "left": [{"district": "national_01"}], "moved": 0}}},
                        "rest": {"status": "done", "states": ["NY"], "ks": {"national": 4, "WIFI": 2}}},
               "summary": {"m1_gap_width": "fail", "m1_strict": "fail", "splits": 3, "shape_error": None, "shape_breaches": 2,
                           "shape_hard": False,
                           "bands": {"national": {"districts": 7, "out": 1, "min_m": 990.0, "max_m": 1300.0, "avg_m": 1100.0}},
                           "shape": {"national": {"hull_fill_min": 0.42, "bite_max": 0.11, "aspect_max": 3.0,
                                                  "longest_axis_km_max": 1234.0, "doughnuts": 0, "doughnuts_soft": 1}}}}}}
    rows = sealed.index_rows(doc)
    nat = next(r for r in rows if r["channel"] == "national")
    assert nat["k"] == "4 + 3 = 7" and nat["regions"] == "rest (NY) K4; south (CA,TX) K3"
    assert nat["band"] == "1 of 7 out, 990-1,300M" and nat["m1"] == "fail / fail (strict)" and nat["splits"] == "3"
    assert "hull fill min 0.42" in nat["shape"] and "2 breaches (report only)" in nat["shape"]
    md = sealed.index_md(doc, "now")
    assert "| toy-pt | toy | national |" in md and "**fails M1**" in md
    assert "retry: 0 channels failing at k_alt, 1 at k" in md and "glue left 1 pieces for the owner" in md


def test_tasks_largest_state_set_first_and_slots_per_run():
    with tempfile.TemporaryDirectory() as tmp:
        (pt,) = _validate(_doc(), tmp)
    tasks = sealed.tasks_of([pt])
    assert [t["id"] for t in tasks] == ["toy-pt/rest", "toy-pt/south"] and all(t["need"] == 2 for t in tasks)


# ------------------------------------------------------------------------------ glue repair
def _graph(edges):
    adj = {}
    for a, b in edges:
        adj.setdefault(a, set()).add(b)
        adj.setdefault(b, set()).add(a)
    return adj


def _pieces(owner, adj, mass, j):
    return len(glue.audit.district_pieces(owner, adj, mass)[j])


NO_NECKS = lambda zs: 0


def test_glue_connects_a_piece_through_zero_opportunity_zctas_of_other_districts():
    # A: a1 a2 | a5 are cut by z3 (B) and z4 (C), both with no opportunity
    adj = _graph([("a1", "a2"), ("a2", "z3"), ("z3", "z4"), ("z4", "a5"), ("z3", "b1"), ("b1", "b2"), ("z4", "c1")])
    owner = {"a1": "A", "a2": "A", "a5": "A", "z3": "B", "b1": "B", "b2": "B", "z4": "C", "c1": "C"}
    mass = {"a1": 5.0, "a2": 4.0, "a5": 3.0, "b1": 2.0, "b2": 2.0, "c1": 6.0}           # z3, z4: zero
    new, rep = glue.glue_channel(owner, adj, mass, NO_NECKS, tau=10.0)
    assert new["z3"] == "A" and new["z4"] == "A" and _pieces(new, adj, mass, "A") == 1
    assert rep["moved"] == {"z3": ["B", "A"], "z4": ["C", "A"]} and rep["left"] == []
    (g,) = rep["glued"]
    assert g["district"] == "A" and g["piece"] == "a5" and g["path"] == ["z4", "z3"] and g["donors"] == {"B": 1, "C": 1}
    assert {z for z in new if new[z] != owner[z]} == {"z3", "z4"}
    for j in "ABC":                                                                       # every district's mass is unchanged
        assert math.fsum(mass.get(z, 0.0) for z in new if new[z] == j) == math.fsum(mass.get(z, 0.0) for z in owner if owner[z] == j)


def test_glue_refuses_when_a_donor_would_be_cut_and_leaves_the_piece_for_the_owner():
    # z3 is B's cut vertex: b1 - z3 - b2
    adj = _graph([("a1", "a2"), ("a2", "z3"), ("z3", "a5"), ("z3", "b1"), ("z3", "b2")])
    owner = {"a1": "A", "a2": "A", "a5": "A", "z3": "B", "b1": "B", "b2": "B"}
    mass = {"a1": 5.0, "a2": 4.0, "a5": 3.0, "b1": 2.0, "b2": 2.0}
    new, rep = glue.glue_channel(owner, adj, mass, NO_NECKS, tau=10.0)
    assert new == owner and rep["moved"] == {} and rep["glued"] == []
    (left,) = rep["left"]
    assert left["district"] == "A" and left["first"] == "a5" and left["zips"] == 1 and left["mass"] == 3.0
    assert left["tau_share"] == 0.3 and "donor B would gain a piece" in left["reason"]


def test_glue_tries_another_path_once_the_failing_donor_is_kept_out():
    # the short path through z3 cuts B; the longer one through y1, y2 (D) does not
    adj = _graph([("a2", "z3"), ("z3", "a5"), ("z3", "b1"), ("z3", "b2"), ("a1", "a2"), ("a2", "y1"), ("y1", "y2"),
                  ("y2", "a5"), ("y1", "d1")])
    owner = {"a1": "A", "a2": "A", "a5": "A", "z3": "B", "b1": "B", "b2": "B", "y1": "D", "y2": "D", "d1": "D"}
    mass = {"a1": 5.0, "a2": 4.0, "a5": 3.0, "b1": 2.0, "b2": 2.0, "d1": 1.0}
    new, rep = glue.glue_channel(owner, adj, mass, NO_NECKS)
    assert new["y1"] == "A" and new["y2"] == "A" and new["z3"] == "B" and _pieces(new, adj, mass, "A") == 1
    assert rep["glued"][0]["donors"] == {"D": 2} and rep["left"] == []


def test_glue_refuses_a_donor_that_would_gain_a_neck_and_never_crosses_positive_opportunity():
    adj = _graph([("a1", "a2"), ("a2", "z3"), ("z3", "a5"), ("z3", "b1"), ("b1", "b2")])
    owner = {"a1": "A", "a2": "A", "a5": "A", "z3": "B", "b1": "B", "b2": "B"}
    mass = {"a1": 5.0, "a2": 4.0, "a5": 3.0, "b1": 2.0, "b2": 2.0}
    gains = lambda zs: 1 if frozenset(zs) == frozenset({"b1", "b2"}) else 0               # B without z3 has a neck
    new, rep = glue.glue_channel(owner, adj, mass, gains)
    assert new == owner and "donor B would gain a neck" in rep["left"][0]["reason"]
    new, rep = glue.glue_channel(owner, adj, mass, NO_NECKS)                              # the same graph, no neck: z3 moves
    assert new["z3"] == "A"
    # the bridge has opportunity: it is never moved, whatever the cost of leaving the piece
    positive = dict(mass, z3=0.5)
    new, rep = glue.glue_channel(owner, adj, positive, NO_NECKS)
    assert new == owner and rep["moved"] == {}
    assert rep["left"][0]["reason"] == "no path of zero-opportunity ZCTAs held by other districts"


def test_glue_leaves_alone_a_district_that_is_one_piece_and_a_piece_with_no_zero_opportunity_path():
    adj = _graph([("a1", "a2"), ("b1", "b2")])
    owner = {"a1": "A", "a2": "A", "b1": "B", "b2": "B"}
    mass = {z: 1.0 for z in owner}
    new, rep = glue.glue_channel(owner, adj, mass, NO_NECKS)
    assert new == owner and rep == {"glued": [], "left": [], "moved": {}}
    adj2 = _graph([("a1", "a2"), ("b1", "b2")])                       # A's second ZCTA is on another island
    owner2 = {"a1": "A", "a2": "A", "x": "A", "b1": "B", "b2": "B"}
    new, rep = glue.glue_channel(owner2, adj2, {**mass, "x": 1.0}, NO_NECKS)
    assert new == owner2 and rep["left"][0]["first"] == "x"
