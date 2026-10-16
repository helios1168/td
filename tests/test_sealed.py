"""tools/exp/contig/sealed.py (the sealed-region driver, 2026-10-14) and glue.py on toy specs, toy
polygon graphs and hand-computed values: P.json validation, a region's spec copy and plan, the
dry-run command chain of a two-region point, the retry at `k_alt`, the shape limits, the labels, the
index, the glue repair (a path through zero-opportunity ZCTAs, a donor that would be cut or
necked, a ZCTA with opportunity never moved), independent regions per channel (the combined
ledger), the scorer's eligibility in the label, the shape stage's cap, and the resume guards (glue
folder, extract hash, reserved names)."""
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
import time
import tomllib
import types

from td import data, output
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


def test_partition_refuses_overlap_gaps_unlisted_channels_and_bad_numbers():
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


def test_partition_takes_each_channel_s_regions_independently():
    nat = _doc()["points"][0]["channels"]["national"]
    with tempfile.TemporaryDirectory() as tmp:
        # a state set in one channel only partly in another's, and the same name for different sets
        wifi = {"regions": [{"name": "south", "states": ["CA", "NY"], "k": 2}], "rest": True}
        (pt,) = _validate(_doc(channels={"national": nat, "WIFI": wifi}), tmp)
        assert not pt["aligned"]
        runs = {r["name"]: r for r in pt["runs"]}
        assert sorted(runs) == ["rest-WIFI", "rest-national", "south-WIFI", "south-national"]
        assert runs["south-national"]["ks"] == {"national": 2} and runs["south-WIFI"]["states"] == ("CA", "NY")
        assert runs["rest-national"]["ks"] == {"national": 4} and runs["rest-WIFI"]["ks"] == {"WIFI": 2}
        # a channel with no region of the other's state set: a run of its own
        only_nat = {"national": nat, "WIFI": {"regions": [], "rest": True}}
        (pt,) = _validate(_doc(channels=only_nat), tmp)
        assert not pt["aligned"] and sorted(r["name"] for r in pt["runs"]) == ["rest-WIFI", "rest-national", "south"]
        # one state set under two names is one run, named for both
        other = {"regions": [{"name": "alpha", "states": ["CA", "TX"], "k": 2}], "rest": True}
        (pt,) = _validate(_doc(channels={"national": nat, "WIFI": other}), tmp)
        assert pt["aligned"] and [r["name"] for r in pt["runs"]] == ["alpha-south", "rest"]
        assert pt["runs"][0]["ks"] == {"national": 2, "WIFI": 2}
        (pt,) = _validate(_doc(), tmp)
        assert pt["aligned"]                                   # the channels agree: merge.py takes the runs' folders


def test_partition_refuses_names_the_driver_writes_itself():
    with tempfile.TemporaryDirectory() as tmp:
        for bad in ("SEALED.json", "sealed.MD", "SEALED.json.tmp", "_plans"):
            _refused(_doc(id=bad), tmp, f"point '{bad}'", "SEALED.json")
        for bad in ("merged", "Merged", "combined", "spec-merge.toml", "merged_extract.json.gz", "merged.stale1", "alt",
                    "launcher_error.txt", "gate.log"):
            ch = {"regions": [{"name": bad, "states": ["CA", "TX"], "k": 2}], "rest": True}
            _refused(_doc(channels={"national": ch, "WIFI": _doc()["points"][0]["channels"]["WIFI"]}), tmp,
                     f"region '{bad}'", "other than the driver's own", "spec-merge.toml")
        ch = {"regions": [{"name": "mergedx", "states": ["CA", "TX"], "k": 2}], "rest": True}      # only the names themselves
        (pt,) = _validate(_doc(channels={"national": ch, "WIFI": _doc()["points"][0]["channels"]["WIFI"]}), tmp)
        assert pt["runs"][0]["name"] == "mergedx-south"


def test_partition_accepts_the_example_file_on_the_real_structures():
    path = os.path.join(HERE, "..", "scenarios", "regions", "main", "sealed_example.json")
    (pt,) = sealed.load_partition(path)
    assert pt["id"] == "ne-48-bal" and [r["name"] for r in pt["runs"]] == ["corridor", "rest-FI-WH-national", "rest-WIFI"]
    assert pt["aligned"]
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
    assert names == ["replan", "draw", "r1", "glue"] * 2 + ["merge", "gate", "score", "land", "shape"]
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
    assert dict(stages)["shape"] == "1800"
    assert re.search(r"sealed\.py shape --folder \S+/toy-pt/merged --name toy-pt --out-dir \S+/toy-pt/merged$", lines["shape"])
    assert "/combined" not in text and "[combine" not in text and "/south/extract.json.gz" not in text and "/rest/extract.json.gz" not in text
    assert "k_alt" not in text
    assert "--drawable-alone" not in off.getvalue()                                      # --no-drawable-alone


def _with_overrides(over, channels=("national",)):
    doc = _doc()
    for c in channels:
        doc["points"][0]["channels"][c]["overrides"] = over
    return doc


def test_partition_overrides_are_validated_and_carried_to_the_runs():
    with tempfile.TemporaryDirectory() as tmp:
        (plain,) = _validate(_doc(), tmp)
        assert all(r["overrides"] == {} for r in plain["runs"]) and plain["channels"]["national"]["overrides"] == {}
        (pt,) = _validate(_with_overrides({"free_rule": "R1", "max_dist_km": 1200, "max_size": 4}), tmp)
        want = {"free_rule": "R1", "max_dist_km": 1200.0, "max_size": 4}
        assert pt["channels"]["national"]["overrides"] == want and pt["channels"]["WIFI"]["overrides"] == {}
        assert [r["overrides"] for r in pt["runs"]] == [{"national": want}] * 2        # south and rest, WIFI has none
        for bad, words in (({"free_rul": "R1"}, ("unknown overrides key 'free_rul'",)),
                           ({"free_rule": "R2"}, ("free_rule must be one of R1, base, rule",)),
                           ({"max_dist_km": 0}, ("max_dist_km must be a number above 0",)),
                           ({"max_dist_km": True}, ("max_dist_km must be a number above 0",)),
                           ({"max_dist_km": "1200"}, ("max_dist_km must be a number above 0",)),
                           ({"max_size": 0}, ("max_size: must be an integer of 1 or more",)),
                           ({"max_size": 2.5}, ("max_size: must be an integer of 1 or more",))):
            _refused(_with_overrides(bad), tmp, "point toy-pt national", *words)
        _refused(_with_overrides([1]), tmp, "overrides must be an object")


def test_the_free_rule_override_changes_one_channels_split_list_and_nothing_else():
    text = TOY.replace('free = ["CA", "NY"]', 'free = ["CA", "FL", "NY"]')
    cells = {**CELLS, ("FL", "national_chase"): 100.0}
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "t.toml")
        with open(path, "w") as fh:
            fh.write(text)
        sp = tdspec.load(path)
    S, ks = ("CA", "FL", "NY", "TX"), {"national": 4, "WIFI": 4}      # national τ 1150, τ/2 575: CA NY TX above it
    free = {r: sealed.region_plan(sp, S, ks, cells, "rule", False, {"national": {"free_rule": r}} if r else None)
            for r in ("R1", "base", "rule", None)}
    assert free["R1"]["channels"]["national"]["free"] == ["CA", "FL", "NY", "TX"]    # base ∪ τ/2
    assert free["base"]["channels"]["national"]["free"] == ["CA", "FL", "NY"]
    assert free["rule"]["channels"]["national"]["free"] == ["CA", "NY", "TX"]
    assert free[None]["channels"]["national"]["free"] == ["CA", "NY", "TX"]           # the point's rule
    for r in ("R1", "base", "rule"):                                                   # the other channel and the rest are as without
        assert free[r]["channels"]["WIFI"] == free[None]["channels"]["WIFI"] and free[r]["infeasible"] == {}
        assert list(free[r]["channels"]) == ["WIFI", "national"] and free[r]["absent"] == free[None]["absent"]
    assert sealed.region_plan(sp, S, ks, cells, "rule", False, {}) == free[None]
    assert sealed.region_plan(sp, S, ks, cells, "base")["channels"]["national"]["free"] == ["CA", "FL", "NY"]
    # the split list is clipped to the region, as the point's rule's is
    small = sealed.region_plan(sp, ("CA", "FL"), {"national": 2}, cells, "rule", False, {"national": {"free_rule": "R1"}})
    assert small["channels"]["national"]["free"] == ["CA", "FL"]


def test_the_overrides_reach_the_channels_block_of_the_spec_copy():
    with tempfile.TemporaryDirectory() as tmp:
        sp = tdspec.load(_toy_file(tmp))
    over = {"national": {"free_rule": "R1", "max_dist_km": 1200.0, "max_size": 4}}
    plan = sealed.region_plan(sp, ("CA", "TX"), {"national": 2, "WIFI": 2}, CELLS, "base", True, over)
    raw = tomllib.loads(sealed.run_spec_text(TOY, "toy-pt", "south", ("CA", "TX"), plan, max_size=5, overrides=over))
    n, w = raw["channels"]["national"], raw["channels"]["WIFI"]
    assert (n["max_dist_km"], n["max_size"], n["free"]) == (1200.0, 4, ["CA", "TX"])     # --max-size 5 yields to the override
    assert w["max_size"] == 5 and "max_dist_km" not in w
    tdspec.parse(raw)
    none = tomllib.loads(sealed.run_spec_text(TOY, "toy-pt", "south", ("CA", "TX"), plan, max_size=5))
    assert none["channels"]["national"]["max_size"] == 5 and "max_dist_km" not in none["channels"]["national"]
    # the dry run prints the same copy, and the merged window follows the run's overrides
    with tempfile.TemporaryDirectory() as tmp:
        (pt,) = _validate(_with_overrides({"max_dist_km": 1200, "max_size": 4}), tmp)
        a = types.SimpleNamespace(root=os.path.join(tmp, "root"), extract="/x/e.json.gz", max_size=5, drawable_alone=True,
                                  window_band=True)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            assert sealed.cmd_dry_run(a, [pt], CELLS, dict(sealed.CAPS), set()) == 0
    copies = re.findall(r"^--- spec copy .*?\n(.*?)^---$", out.getvalue(), re.M | re.S)
    assert len(copies) == 2
    for body in copies:
        n = tomllib.loads(body)["channels"]["national"]
        assert (n["max_dist_km"], n["max_size"]) == (1200.0, 4)
        assert tomllib.loads(body)["channels"]["WIFI"]["max_size"] == 5


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
    assert sealed.drawing_failures(held) == {}                   # drawn, with detached pieces: the repair and the glue take it


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
def test_a_hard_shape_limit_on_a_missing_or_nan_value_is_not_a_pass():
    row = {"map": "toy-pt", "channel": "WIFI", "district": "WIFI_01", "hull_fill": 0.5, "bite": 0.05, "aspect": 2.0,
           "longest_axis_km": 800.0, "doughnut": 0, "doughnut_soft": 0}
    limits = {"bite": {"max": 0.3}}
    assert sealed.shape_unmeasured([row], limits) == []
    for bad in (None, float("nan"), float("inf"), "0.1"):
        rows = [dict(row, bite=bad)]
        assert [g["measure"] for g in sealed.shape_unmeasured(rows, limits)] == ["bite"]
    gone = {k: v for k, v in row.items() if k != "bite"}
    assert [g["district"] for g in sealed.shape_unmeasured([gone], limits)] == ["WIFI_01"]
    for bad in (None, float("nan")):
        with tempfile.TemporaryDirectory() as tmp:          # hard: labelled error, never passes
            drv, pt = _merge_driver(tmp, limits={"hard": True, "limits": limits})
            _merged_folder(tmp, "toy-pt", shape_rows=[dict(row, bite=bad)])
            try:
                drv._merge(pt)
            except sealed.Stop as e:
                assert e.label == "error" and "hard limits" in e.reason and "non-finite" in e.reason
            else:
                raise AssertionError(f"labelled a map whose hard-limited bite was {bad!r}")
        with tempfile.TemporaryDirectory() as tmp:          # report only: as before, the label stands
            drv, pt = _merge_driver(tmp, limits={"hard": False, "limits": limits})
            merged = _merged_folder(tmp, "toy-pt", shape_rows=[dict(row, bite=bad)])
            assert drv._merge(pt)[0] == "passes"
            assert json.load(open(os.path.join(merged, "shape.json")))["error"] is None


def test_a_combine_that_hangs_is_killed_at_its_cap_and_at_the_hours_stop():
    nat = _doc()["points"][0]["channels"]["national"]
    wifi = {"regions": [{"name": "south", "states": ["CA", "NY"], "k": 2}], "rest": True}
    doc = _doc(channels={"national": nat, "WIFI": wifi})
    hang = lambda args, out, spec, extract: [sys.executable, "-c", "import time; time.sleep(120)"]
    real, sealed.combine_cmd = sealed.combine_cmd, hang
    try:
        with tempfile.TemporaryDirectory() as tmp:
            drv, pt = _merge_driver(tmp, doc=doc, caps=dict(sealed.CAPS, combine=1.0), real=("combine",))
            os.makedirs(os.path.join(tmp, "toy-pt"), exist_ok=True)
            t0 = time.time()
            try:
                drv._merge(pt)
            except sealed.Stop as e:
                assert e.label == "stopped" and "combine killed at its cap" in e.reason
            else:
                raise AssertionError("a hung combine was waited for")
            assert time.time() - t0 < 40 and drv.grid.get("toy-pt")["stages"]["combine"]["stop"] == "cap"
            assert "merge" not in [n for n, _ in drv.calls]
        with tempfile.TemporaryDirectory() as tmp:           # the --hours stop ends it too, whatever the cap
            drv, pt = _merge_driver(tmp, doc=doc, real=("combine",))
            os.makedirs(os.path.join(tmp, "toy-pt"), exist_ok=True)
            drv.deadline = time.time() + 1.0
            t0 = time.time()
            try:
                drv._merge(pt)
            except sealed.Stop as e:
                assert e.label == "stopped" and "during combine" in e.reason
            else:
                raise AssertionError("the launcher ran past its stop")
            assert time.time() - t0 < 40
    finally:
        sealed.combine_cmd = real


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


def test_point_ids_differing_only_in_case_are_listed_twice():
    with tempfile.TemporaryDirectory() as tmp:
        doc = _doc()
        doc["points"].append(dict(doc["points"][0], id="TOY-PT"))
        _refused(doc, tmp, "TOY-PT", "listed twice")


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
        for col in ("hub", "states", "channel", "cut_detail"):     # text columns: a number limit never compares
            json.dump({"limits": {col: {"max": 1}}}, open(path, "w"))
            try:
                sealed.load_limits(path)
                raise AssertionError(f"accepted a limit on the text column {col}")
            except sealed.PartitionError as e:
                assert f"'{col}'" in str(e) and "numeric" in str(e)
        assert set(sealed.LIMIT_COLUMNS) <= set(sealed._study().DISTRICT_COLUMNS)


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


def test_glue_keeps_a_donor_s_failures_by_identity_and_size_not_by_count():
    # B holds a detached piece {z4}; the only path takes z4 and B's cut vertex z3: B ends with as many pieces
    # as before (two), but the one left, {b2}, is new: a count test passes it, the identity test refuses it
    adj = _graph([("a1", "a2"), ("a5", "z4"), ("z4", "y"), ("y", "z3"), ("z3", "a2"), ("b1", "z3"), ("z3", "b2"),
                  ("y", "c1")])
    owner = {"a1": "A", "a2": "A", "a5": "A", "z4": "B", "z3": "B", "b1": "B", "b2": "B", "y": "C", "c1": "C"}
    mass = {"a1": 5.0, "a2": 4.0, "a5": 3.0, "b1": 2.0, "b2": 1.0, "c1": 6.0}
    assert len(glue.audit.district_pieces(owner, adj, mass)["B"]) == 2
    new, rep = glue.glue_channel(owner, adj, mass, NO_NECKS, tau=10.0)
    assert new["z3"] == "B" and new["z4"] == "B" and new["a5"] == "A"          # A's path is refused
    assert [g["district"] for g in rep["glued"]] == ["B"]                      # B's own piece is joined through y, as it may
    assert "donor B would gain a piece" in rep["left"][0]["reason"] and rep["left"][0]["district"] == "A"
    # the same graph with z3 a leaf of B's body: the path takes the detached piece and a leaf, B ends clean
    adj2 = _graph([("a1", "a2"), ("a5", "z4"), ("z4", "y"), ("y", "z3"), ("z3", "a2"), ("b1", "z3"), ("b1", "b2"),
                   ("y", "c1")])
    new, rep = glue.glue_channel(owner, adj2, mass, NO_NECKS, tau=10.0)
    assert new["z4"] == "A" and new["y"] == "A" and new["z3"] == "A" and rep["left"] == []
    assert len(glue.audit.district_pieces(new, adj2, mass)["B"]) == 1


def test_glue_refuses_a_donor_whose_neck_is_new_or_enlarged_even_when_the_count_is_the_same():
    adj = _graph([("a1", "a2"), ("a2", "z3"), ("z3", "a5"), ("z3", "b1"), ("b1", "b2")])
    owner = {"a1": "A", "a2": "A", "a5": "A", "z3": "B", "b1": "B", "b2": "B"}
    mass = {"a1": 5.0, "a2": 4.0, "a5": 3.0, "b1": 2.0, "b2": 2.0}
    whole, cut = frozenset({"z3", "b1", "b2"}), frozenset({"b1", "b2"})

    def necks(before, after):
        return lambda zs: [frozenset(x) for x in (before if frozenset(zs) == whole else after if frozenset(zs) == cut else ())]
    new, rep = glue.glue_channel(owner, adj, mass, necks([{"b2"}], [{"b1"}]))          # one neck before, one after: another part
    assert new == owner and "donor B would gain a neck" in rep["left"][0]["reason"]
    new, rep = glue.glue_channel(owner, adj, mass, necks([{"b2"}], [{"b1", "b2"}]))    # the same neck, enlarged
    assert new == owner and "donor B would gain a neck" in rep["left"][0]["reason"]
    new, rep = glue.glue_channel(owner, adj, mass, necks([{"b1", "b2"}], [{"b2"}]))    # the same neck, smaller: kept
    assert new["z3"] == "A" and rep["left"] == []
    new, rep = glue.glue_channel(owner, adj, mass, necks([], [{"b2"}]))                # a clean donor stays clean
    assert new == owner and "donor B would gain a neck" in rep["left"][0]["reason"]


def test_glue_reads_the_gates_adjacency_with_the_land_only_gap_edges():
    state = {"a1": "A", "a2": "A", "a3": "A", "b1": "B", "b2": "B"}
    polygon = {"vertices": sorted(state), "edges": [("a1", "a2"), ("a2", "b1"), ("a3", "b1"), ("b1", "b2")],
               "state": state,
               "gaps": {("a2", "a3"): 40.0, ("a1", "b1"): 10.0}}           # a1-b1 face each other across two states
    adj = glue.gate_adjacency(polygon)
    assert adj == glue.audit.adjacency(polygon, gaps=True) and "a3" in adj["a2"] and "b1" not in adj["a1"]
    old = os.environ.get(glue.audit.GAP_WIDTH_ENV)
    os.environ[glue.audit.GAP_WIDTH_ENV] = "0"
    try:
        flat = glue.gate_adjacency(polygon)
    finally:
        os.environ.pop(glue.audit.GAP_WIDTH_ENV) if old is None else os.environ.update({glue.audit.GAP_WIDTH_ENV: old})
    assert "a3" not in flat["a2"] and flat == glue.audit.adjacency(polygon)
    # A = a1 a2 a3 is one piece across the gap edge a2~a3, so there is nothing to glue; without gap edges a3 is
    # a piece, and the glue would move B's zero-opportunity ZCTA b1 into A
    owner, mass = {"a1": "A", "a2": "A", "a3": "A", "b1": "B", "b2": "B"}, {"a1": 3.0, "a2": 2.0, "a3": 1.0, "b2": 1.0}
    new, rep = glue.glue_channel(owner, adj, mass, NO_NECKS)
    assert new == owner and rep == {"glued": [], "left": [], "moved": {}}
    new, rep = glue.glue_channel(owner, flat, mass, NO_NECKS)
    assert new["b1"] == "A" and rep["moved"] == {"b1": ["B", "A"]}


def test_glue_keeps_an_unresolved_neck_unresolved_and_refuses_a_donor_move_that_leaves_one():
    adj = _graph([("a1", "a2"), ("a2", "z3"), ("z3", "a5"), ("z3", "b1"), ("b1", "b2")])
    owner = {"a1": "A", "a2": "A", "a5": "A", "z3": "B", "b1": "B", "b2": "B"}
    mass = {"a1": 5.0, "a2": 4.0, "a5": 3.0, "b1": 2.0, "b2": 2.0}
    cut = frozenset({"b1", "b2"})
    unresolved = lambda zs: [glue.UnresolvedNeck({"b1"})] if frozenset(zs) == cut else []     # B without z3: unresolved
    new, rep = glue.glue_channel(owner, adj, mass, unresolved)
    assert new == owner and "donor B would have an unresolved neck check" in rep["left"][0]["reason"]
    proved = lambda zs: [frozenset({"b1"})] if frozenset(zs) == cut else []                    # the same set, a proved neck
    new, rep = glue.glue_channel(owner, adj, mass, proved)
    assert new == owner and "donor B would gain a neck" in rep["left"][0]["reason"]
    new, rep = glue.glue_channel(owner, adj, mass, NO_NECKS)
    assert new["z3"] == "A"
    # neck_counter keeps the gate's status instead of flattening it to the part cut off
    Neck = glue.audit.Neck
    real = glue.necks_gate.gate_necks
    glue.necks_gate.gate_necks = lambda zs, m, ng, *a: [Neck(1.0, ("b1",), 0.1, 0.1, (), "proved"),
                                                         Neck(2.0, ("b2",), 0.1, 0.1, (), "unresolved")]
    try:
        poly = {"vertices": ["b1", "b2"], "edges": [("b1", "b2")], "state": {"b1": "B", "b2": "B"},
                "border": {("b1", "b2"): 1000.0}, "connectors": [], "aland": {"b1": 1e8, "b2": 1e8}}
        got = glue.neck_counter(poly, {"b1": 1.0, "b2": 1.0})[0](["b1", "b2"])
    finally:
        glue.necks_gate.gate_necks = real
    assert [isinstance(x, glue.UnresolvedNeck) for x in got] == [False, True] and got == [{"b1"}, {"b2"}]


# ------------------------------------------------------------------------------ a drawing with detached pieces
CONTIG_PIECES = {"channels": {
    "national": {"status": "connected", "connected": False, "undrawn_zctas": 0, "fixed_split": ["NY#1"], "groups": []},
    "WIFI": {"status": "optimal", "connected": True, "undrawn_zctas": 0, "fixed_split": [], "groups": []}}}


def test_a_drawing_that_succeeded_with_detached_pieces_goes_on_to_the_repair_and_the_glue():
    with tempfile.TemporaryDirectory() as tmp:
        drv, pt, run = _stub_driver(tmp, None, [])
        real = sealed.Driver._attempt
        drv._attempt = lambda *a: real(drv, *a)
        rdir = os.path.join(tmp, "toy-pt", "south")
        out = os.path.join(rdir, "draw")
        os.makedirs(out)
        open(os.path.join(out, "ledger.csv"), "w").write("zip_code\n")
        json.dump({"status": "done"}, open(os.path.join(out, "manifest.json"), "w"))
        json.dump(CONTIG_PIECES, open(os.path.join(out, "contig.json"), "w"))
        open(os.path.join(rdir, "spec.toml"), "w").write("# canned\n")
        drv.drawable_alone = True
        drv._chain(pt, run, rdir)
        assert drv.calls == ["south.r1", "south.r2", "south.glue"]      # a piece is for the repair, not a failed drawing
        rec = drv.grid.get("toy-pt")["runs"]["south"]
        assert rec["status"] == "done" and rec["draw_failing"] == [] and rec["draw"] == {"WIFI": "optimal", "national": "connected"}


def test_an_interrupted_repair_pass_with_only_a_ledger_is_not_the_next_source():
    """A pass killed at its cap can leave a `ledger.csv` with no `contig.json` or `run.json` and a
    manifest still `running`: glue reads the draw folder, not that one."""
    with tempfile.TemporaryDirectory() as tmp:
        drv, pt, run = _stub_driver(tmp, None, [[]])
        rdir = os.path.join(tmp, "toy-pt", "south")
        r1 = os.path.join(rdir, "r1")
        os.makedirs(r1)
        open(os.path.join(r1, "ledger.csv"), "w").write("zip_code\n")
        json.dump({"status": "running"}, open(os.path.join(r1, "manifest.json"), "w"))
        assert not sealed.repair_done(r1)
        glued = []
        drv.stage = lambda pid, name, cmd, log, cap, env=None: (
            glued.append(cmd[3]) if name == "south.glue" else None) or {"rc": 0, "stop": None, "seconds": 0.0}
        drv._chain(pt, run, rdir)
        assert glued == [os.path.join(rdir, "draw")]
        os.makedirs(r1, exist_ok=True)                          # the driver moved the interrupted pass aside
        open(os.path.join(r1, "ledger.csv"), "w").write("zip_code\n")
        json.dump({"status": "done"}, open(os.path.join(r1, "manifest.json"), "w"))
        assert not sealed.repair_done(r1)                       # done, ledger, but no contig.json / run.json
        for f in ("contig.json", "run.json"):
            open(os.path.join(r1, f), "w").write("{}")
        assert sealed.repair_done(r1)


# ------------------------------------------------------------------------------ a resumed glue folder
def _glue_folder(rdir, status, moved, full):
    g = os.path.join(rdir, "glue")
    os.makedirs(g)
    json.dump({"channels": {"national": {"glued": [], "left": [], "moved": moved}}}, open(os.path.join(g, "glue.json"), "w"))
    json.dump({"status": status}, open(os.path.join(g, "manifest.json"), "w"))
    if full:
        for f in ("ledger.csv", "contig.json", "run.json"):
            open(os.path.join(g, f), "w").write("{}" if f.endswith("json") else "zip_code\n")
    return g


def _resume(tmp, status, moved, full):
    drv, pt, run = _stub_driver(tmp, None, [[]])
    rdir = os.path.join(tmp, "toy-pt", "south")
    os.makedirs(rdir)
    g = _glue_folder(rdir, status, moved, full)
    drv._chain(pt, run, rdir)
    return drv, g, drv.grid.get("toy-pt")["runs"]["south"]


def test_a_glue_folder_is_reused_only_when_done_and_complete_and_the_interrupted_one_is_moved_aside():
    with tempfile.TemporaryDirectory() as tmp:      # glue.json written, the folder never finished (killed before the ledger)
        drv, g, rec = _resume(tmp, "running", {"z": ["A", "B"]}, False)
        assert "south.glue" in drv.calls and os.path.exists(g + ".stale1") and not os.path.exists(g)
    with tempfile.TemporaryDirectory() as tmp:      # done, but a ZCTA moved and the ledger is missing
        drv, g, rec = _resume(tmp, "done", {"z": ["A", "B"]}, False)
        assert "south.glue" in drv.calls and os.path.exists(g + ".stale1")
    with tempfile.TemporaryDirectory() as tmp:      # done with nothing to glue: kept, the source folder goes on
        drv, g, rec = _resume(tmp, "done", {}, False)
        assert "south.glue" not in drv.calls and rec["final"] == os.path.join("toy-pt", "south", "draw")
        assert rec["glue"] == {"national": {"glued": 0, "left": [], "moved": 0}}
    with tempfile.TemporaryDirectory() as tmp:      # done and complete: kept, the glued folder is the final one
        drv, g, rec = _resume(tmp, "done", {"z": ["A", "B"]}, True)
        assert "south.glue" not in drv.calls and rec["final"] == os.path.join("toy-pt", "south", "glue")
        assert not os.path.exists(g + ".stale1")
    assert sealed.glue_done(os.path.join(CONTIG, "nowhere")) is False


# ------------------------------------------------------------------------------ the extract on a resume
def test_a_resume_on_changed_extract_contents_under_the_same_root_is_refused():
    with tempfile.TemporaryDirectory() as tmp:
        (pt,) = _validate(_doc(), tmp)
        extract = os.path.join(tmp, "extract.json.gz")
        open(extract, "wb").write(b"toy")
        sealed.open_state(tmp, "m5", extract, 1.0, "p", "sha", [pt])
        sealed.open_state(tmp, "m5", extract, 1.0, "p", "sha", [pt])        # the same bytes resume
        open(extract, "wb").write(b"toy, rebuilt")
        try:
            sealed.open_state(tmp, "m5", extract, 1.0, "p", "sha", [pt])
        except SystemExit as e:
            assert "another extract" in str(e) and "use a new --root" in str(e)
        else:
            raise AssertionError("resumed on an extract with other contents")
        doc = json.load(open(os.path.join(tmp, sealed.STATE_JSON)))
        del doc["extract_sha256"]
        json.dump(doc, open(os.path.join(tmp, sealed.STATE_JSON), "w"))
        open(extract, "wb").write(b"toy")
        try:
            sealed.open_state(tmp, "m5", extract, 1.0, "p", "sha", [pt])
        except SystemExit as e:
            assert "no hash" in str(e)
        else:
            raise AssertionError("resumed on a state file with no extract hash")


# ------------------------------------------------------------------------------ the merge stage
class _MergeStub(sealed.Driver):
    """A driver whose stages are canned except those named in `real`, which run through `overnight.child`;
    `on_merge` stands in for merge.py's output."""

    def __init__(self, *a, real=(), on_merge=None, rcs=None, **kw):
        super().__init__(*a, **kw)
        self.real, self.calls, self.on_merge, self.rcs = set(real), [], on_merge, rcs or {}

    def stage(self, pid, name, cmd, log, cap, env=None):
        self.calls.append((name, cmd))
        if name in self.real:
            return super().stage(pid, name, cmd, log, cap, env)
        if name == "merge" and self.on_merge:
            self.on_merge()
        return {"rc": self.rcs.get(name, 0), "stop": None, "seconds": 0.0}


def _toy_dollar_extract(whole=11360.0, district=900.0) -> data.Extract:
    """A dollar extract ($M cells) whose `wh` rate is exactly 1e6: the district's cell `a1` is $900M, the rest `a2`."""
    return data.Extract(("wh",), ["a1", "a2"], ["wh", "wh"], [district, whole - district], [{}, {}], [0.0, 0.0])


def _merge_driver(tmp, doc=None, caps=None, limits=None, real=(), on_merge=None, rcs=None):
    (pt,) = _validate(doc or _doc(), tmp)
    extract = os.path.join(tmp, "extract.json.gz")
    data.write(_toy_dollar_extract(), extract)
    grid = sealed.open_state(tmp, "m5", extract, 1.0, "p", "sha", [pt])
    drv = _MergeStub(grid, tmp, "m5", extract, CELLS, {pt["id"]: pt}, caps or dict(sealed.CAPS), set(), None,
                     limits or sealed.load_limits(None), real=real, on_merge=on_merge, rcs=rcs)
    for run in pt["runs"]:
        drv.note(pt["id"], run["name"], status="done", final=os.path.join(pt["id"], run["name"], "glue"))
    return drv, pt


SCORE_47 = "# toy\ndir: x\neligible: no\n  - main K 47 outside 48-52\nK: national 20 WIFI 27 = 47\n"
DOLLARS = ("channel,district,usd_m,lo_m,hi_m,whole_state_cap_m,allowance,ok\n"
           "WIFI,WIFI_01,900.0,850,1150,,0,1\n")


def _merged_folder(tmp, pid, score="# toy\ndir: x\neligible: yes\n", shape_rows=None):
    merged = os.path.join(tmp, pid, "merged")
    os.makedirs(merged, exist_ok=True)
    json.dump({"status": "done"}, open(os.path.join(merged, "manifest.json"), "w"))
    open(os.path.join(merged, "ledger.csv"), "w").write(
        "zip_code,current_channel,state,model_channel,district,reason,m_rel\n"
        "a1,wh,A,WIFI,WIFI_01,,900.0\n")
    open(os.path.join(merged, "districts.csv"), "w").write("channel,district,drawn_mass\nWIFI,WIFI_01,900.0\n")
    ok = {"status": "pass", "summary": "0 districts in pieces, 0 necks"}
    json.dump({"gap_width": ok, "strict": ok}, open(os.path.join(merged, "m1.json"), "w"))
    open(os.path.join(merged, "dollars.csv"), "w").write(DOLLARS)
    open(os.path.join(merged, "score.txt"), "w").write(score)
    if shape_rows is not None:
        json.dump(shape_rows, open(os.path.join(merged, sealed.SHAPE_ROWS), "w"))
    return merged


def test_a_connected_in_band_map_with_total_k_47_is_labelled_ineligible_from_the_scorer():
    with tempfile.TemporaryDirectory() as tmp:
        drv, pt = _merge_driver(tmp)
        merged = _merged_folder(tmp, "toy-pt", SCORE_47, shape_rows=[])
        label, reason, final, extra = drv._merge(pt)
        assert label == "ineligible" and "main K 47 outside 48-52" in reason and final == merged
        assert [n for n, _ in drv.calls] == ["gate", "score", "land", "shape"]
        assert extra["summary"]["m1_gap_width"] == "pass" and extra["summary"]["bands"]["WIFI"]["out"] == 0
    with tempfile.TemporaryDirectory() as tmp:
        drv, pt = _merge_driver(tmp)
        _merged_folder(tmp, "toy-pt", shape_rows=[])
        assert drv._merge(pt)[:2] == ("passes", "")
    with tempfile.TemporaryDirectory() as tmp:       # a score.txt with no eligible line is an error, not a pass
        drv, pt = _merge_driver(tmp)
        _merged_folder(tmp, "toy-pt", "# toy\nno verdict here\n", shape_rows=[])
        try:
            drv._merge(pt)
        except sealed.Stop as e:
            assert e.label == "error" and "no eligible line" in e.reason
        else:
            raise AssertionError("labelled a map the scorer never judged")
    ok, bad = {"status": "pass", "summary": "ok"}, {"status": "fail", "summary": "1 necks"}
    rows = [{"district": "WIFI_01", "channel": "WIFI", "usd": 900.0, "lo": 850.0, "hi": 1150.0, "cap": None, "ok": True}]
    why = ["main K 47 outside 48-52"]
    assert sealed.label_point(ok, rows, [], False, False, why) == ("ineligible", "main K 47 outside 48-52")
    assert sealed.label_point(bad, rows, [], False, False, why)[0] == "fails M1"          # M1 and the band come first
    assert sealed.label_point(ok, rows + [dict(rows[0], ok=False, usd=800.0)], [], False, False, why)[0] == "outside band"
    assert "ineligible" in sealed.LABELS


def test_a_gate_stage_that_exits_nonzero_vetoes_a_pass_whatever_m1_json_says():
    with tempfile.TemporaryDirectory() as tmp:
        drv, pt = _merge_driver(tmp, rcs={"gate": 1})
        _merged_folder(tmp, "toy-pt", shape_rows=[])          # m1.json, dollars.csv and score.txt all say pass
        label, reason, final, extra = drv._merge(pt)
        assert label == "fails M1" and "gate (check.py) exited 1" in reason
    with tempfile.TemporaryDirectory() as tmp:               # the gate's tail goes into the reason
        drv, pt = _merge_driver(tmp, rcs={"gate": 1})
        _merged_folder(tmp, "toy-pt", shape_rows=[])
        open(os.path.join(tmp, "toy-pt", "gate.log"), "w").write("x\nDIAGNOSTIC (band), not a deliverable\n")
        assert "DIAGNOSTIC" in drv._merge(pt)[1]
    ok, rows = {"status": "pass", "summary": "ok"}, [{"district": "W_01", "channel": "WIFI", "usd": 900.0, "lo": 850.0,
                                                       "hi": 1150.0, "cap": None, "ok": True}]
    assert sealed.label_point(ok, rows, [], False)[0] == "passes"
    assert sealed.label_point(ok, rows, [], False, gate_rc=2, gate_tail="boom") == ("fails M1", "the gate (check.py) exited 2: boom")
    assert sealed.label_point(ok, rows, [], False, gate_rc=None)[0] == "fails M1"       # a gate that never reported


def test_a_manhattan_only_failed_gate_passes_the_label_and_every_other_item_still_vetoes():
    ok, bad = {"status": "pass", "summary": "ok"}, {"status": "fail", "summary": "1 necks"}
    rows = [{"district": "W_01", "channel": "WIFI", "usd": 900.0, "lo": 850.0, "hi": 1150.0, "cap": None, "ok": True}]
    manhattan = {"passes": True, "excepted": [("a neck in Manhattan", ["10001"])], "blocking": []}
    assert sealed.label_point(bad, rows, [], False, gate_rc=1, verdict=manhattan) == ("passes", "")
    other = {"passes": False, "excepted": [("a Manhattan neck", ["10001"])], "blocking": ["IFA/IFA_01: neck of 3 ZIPs"]}
    label, why = sealed.label_point(bad, rows, [], False, gate_rc=1, gate_tail="x", verdict=other)
    assert label == "fails M1" and "neck of 3 ZIPs" in why and "exited 1" in why
    assert sealed.label_point(bad, rows, [], False, gate_rc=2, verdict=manhattan)[0] == "fails M1"    # not a completed gate
    assert sealed.label_point(bad, rows, [], False, gate_rc=None, verdict=manhattan)[0] == "fails M1"
    assert sealed.label_point(bad, rows + [dict(rows[0], ok=False, usd=800.0)], [], False, gate_rc=1,
                              verdict=manhattan)[0] == "outside band"                                 # the band still decides
    assert sealed.label_point(bad, rows, [], False, gate_rc=1)[0] == "fails M1"                       # no verdict: raw M1
    assert sealed.manhattan_verdict("/nowhere", 0) is None and sealed.manhattan_verdict("/nowhere", 2) is None
    crash = sealed.manhattan_verdict(os.path.join(tempfile.gettempdir(), "no-such-gate-folder"), 1)
    assert crash["passes"] is False and "gate evidence unavailable" in crash["blocking"][0]          # no evidence is a veto


def test_the_gate_stage_is_a_capped_child_that_records_its_own_evidence_and_a_stale_record_is_a_veto():
    chain = dict((s, (c, cap)) for s, c, cap, _ in sealed.point_chain("p", "/p", [(("A",), "/f")], "/spec", "/full",
                                                                        None, dict(sealed.CAPS)))
    cmd, cap = chain["gate"]
    assert cmd[-4:] == ["--gate", "/p/merged", "--out", "/p/gate-evidence.json"]
    assert cmd[1] == "-u" and os.path.samefile(cmd[2], sealed.ifa_index.__file__) and cmd[2].endswith("ifa_index_night.py")
    assert cap == sealed.overnight.CAP_S["gate"]
    assert sealed.evidence_path("/p/merged") == "/p/gate-evidence.json"
    with tempfile.TemporaryDirectory() as tmp:
        merged = os.path.join(tmp, "merged")
        os.makedirs(merged)
        doc = {"folder": os.path.abspath(merged), "rc": 1, "status": "fail", "summary": "s", "diagnostic": None,
               "counts": {"necks": 0}, "items": ["IFA/IFA_01: detached piece of 1 ZIPs (10001...)"],
               "sides": {"necks": {}, "pieces": [["IFA_01", "10001", 1, ["10001"]]]}}
        path = sealed.evidence_path(merged)
        json.dump(doc, open(path, "w"))
        good = sealed.manhattan_verdict(merged, 1)
        assert sealed.ifa_index.read_gate_evidence(path, merged, 1)["sides"]["pieces"] == {
            ("IFA_01", "10001", 1): frozenset({"10001"})}
        assert good["passes"] and good["excepted"] == [("IFA/IFA_01: detached piece of 1 ZIPs (10001...)", ["10001"])]
        json.dump(dict(doc, rc=2), open(path, "w"))                    # another exit code than the one the driver saw
        assert "gate evidence unavailable" in sealed.manhattan_verdict(merged, 1)["blocking"][0]
        json.dump(dict(doc, folder="/elsewhere/merged"), open(path, "w"))
        assert "gate evidence unavailable" in sealed.manhattan_verdict(merged, 1)["blocking"][0]
    with tempfile.TemporaryDirectory() as tmp:                         # the merge removes a record it did not write
        drv, pt = _merge_driver(tmp, rcs={"gate": 1})
        _merged_folder(tmp, "toy-pt", shape_rows=[])
        stale = os.path.join(tmp, "toy-pt", sealed.ifa_index.EVIDENCE)
        json.dump(dict(doc, folder=os.path.join(tmp, "toy-pt", "merged")), open(stale, "w"))
        assert drv._merge(pt)[0] == "fails M1" and not os.path.exists(stale)


def test_a_manhattan_only_pass_drops_both_m1_reasons_and_keeps_every_other_veto():
    """`score.eligibility` gives an M1 failure two reasons, the scorer's `M1:` and the scorecard row's `audit:`."""
    bad = {"status": "fail", "summary": "1 necks"}
    rows = [{"district": "W_01", "channel": "WIFI", "usd": 900.0, "lo": 850.0, "hi": 1150.0, "cap": None, "ok": True}]
    manhattan = {"passes": True, "excepted": [("a neck in Manhattan", ["10001"])], "blocking": []}
    raw, dup = "M1: fail, 1 necks", f"audit: {sealed.score.audit.M1_CHECK} fails"
    routing, cover = "audit: ZIP contiguity fails", "audit: coverage fails"
    assert sealed.scorer_eligibility(False, [dup, raw], manhattan, 1) == (True, [])
    assert sealed.scorer_eligibility(False, [dup, raw, routing, cover], manhattan, 1) == (False, [routing, cover])
    assert sealed.scorer_eligibility(False, [dup, raw, "M1: not checked"], manhattan, 1) == (False, ["M1: not checked"])
    assert sealed.scorer_eligibility(False, [dup, raw], manhattan, 0) == (False, [dup, raw])
    assert sealed.scorer_eligibility(False, [dup, raw], {**manhattan, "passes": False}, 1) == (False, [dup, raw])
    assert sealed.label_point(bad, rows, [], False, False, [dup, raw], gate_rc=1, verdict=manhattan) == ("passes", "")
    assert sealed.label_point(bad, rows, [], False, False, [dup, raw, routing], gate_rc=1,
                              verdict=manhattan) == ("ineligible", routing)


def test_a_manhattan_only_pass_drops_the_scorer_s_raw_m1_reason_and_no_other_veto():
    bad = {"status": "fail", "summary": "1 necks"}
    rows = [{"district": "W_01", "channel": "WIFI", "usd": 900.0, "lo": 850.0, "hi": 1150.0, "cap": None, "ok": True}]
    manhattan = {"passes": True, "excepted": [("a neck in Manhattan", ["10001"])], "blocking": []}
    raw, other = "M1: fail, 1 necks", "main K 47 outside 48-52"
    assert sealed.scorer_eligibility(False, [raw], manhattan, 1) == (True, [])
    assert sealed.scorer_eligibility(False, [raw, other], manhattan, 1) == (False, [other])
    assert sealed.scorer_eligibility(False, [], manhattan, 1) == (False, [])                # a bare `eligible: no`
    assert sealed.scorer_eligibility(False, ["M1: not checked"], manhattan, 1) == (False, ["M1: not checked"])
    assert sealed.scorer_eligibility(False, [raw], manhattan, 0) == (False, [raw])           # no failed gate: no waiver
    assert sealed.scorer_eligibility(False, [raw], {**manhattan, "passes": False}, 1) == (False, [raw])
    assert sealed.scorer_eligibility(False, [raw], None, 1) == (False, [raw])
    assert sealed.label_point(bad, rows, [], False, False, [raw], gate_rc=1, verdict=manhattan) == ("passes", "")
    assert sealed.label_point(bad, rows, [], False, False, [raw, other], gate_rc=1,
                              verdict=manhattan) == ("ineligible", other)
    assert sealed.label_point(bad, rows, [], False, False, [], gate_rc=1, verdict=manhattan)[0] == "ineligible"
    # through the merge: the scorer says `eligible: no` with only the raw M1 reason
    real = sealed.manhattan_verdict
    try:
        sealed.manhattan_verdict = lambda folder, rc: manhattan if rc == 1 else None
        for lines, want in ((f"eligible: no\n  - {raw}\n", "passes"), (f"eligible: no\n  - {raw}\n  - {other}\n", "ineligible")):
            with tempfile.TemporaryDirectory() as tmp:
                drv, pt = _merge_driver(tmp, rcs={"gate": 1})
                _merged_folder(tmp, "toy-pt", f"# toy\ndir: x\n{lines}", shape_rows=[])
                label, reason, _, extra = drv._merge(pt)
                assert label == want and (want == "passes" or reason == other), (label, reason)
    finally:
        sealed.manhattan_verdict = real


def test_the_merge_judges_the_dollar_window_on_unrounded_full_extract_masses():
    total = sealed.score.DOLLARS["wh"] / 1e6
    # WH_01 and WH_02 share a state (neither is a whole-state district), a1/a2 are their cells of the dollar extract
    for m1, want in ((849.99999975, "outside band"), (850.0, "passes"), (1150.0, "passes"),
                     (1150.00000025, "outside band")):
        with tempfile.TemporaryDirectory() as tmp:
            drv, pt = _merge_driver(tmp)
            merged = _merged_folder(tmp, "toy-pt", shape_rows=[])
            ext = data.Extract(("wh",), ["a1", "a2", "a3"], ["wh"] * 3, [m1, 900.0, total - m1 - 900.0],
                               [{}] * 3, [0.0] * 3)
            data.write(ext, drv.extract)
            open(os.path.join(merged, "ledger.csv"), "w").write(
                "zip_code,current_channel,state,model_channel,district,reason,m_rel\n"
                "a1,wh,A,WH,WH_01,,1.0\na2,wh,A,WH,WH_02,,1.0\n")      # the ledger's own m_rel decides nothing
            open(os.path.join(merged, "districts.csv"), "w").write(
                "channel,district,drawn_mass\nWH,WH_01,1\nWH,WH_02,1\n")
            rates = sealed.score.dollar_rates(ext)
            scored = sealed.score.dollar_gate(
                [{"zip_code": "a1", "current_channel": "wh", "state": "A", "model_channel": "WH", "district": "WH_01",
                  "m_rel": str(m1)}], [{"channel": "WH", "district": "WH_01"}], rates)[0]
            label, reason, _, extra = drv._merge(pt)
            assert label == want, (m1, label, reason)
            if want == "outside band":
                assert not scored["ok"] and "WH_01" in reason      # the scorer compares unrounded dollars too (#105)
                assert extra["summary"]["bands"]["WH"]["out"] == 1


def test_the_exact_window_needs_the_ledgers_districts_to_be_districts_csvs():
    ledger = ("zip_code,current_channel,state,model_channel,district,reason,m_rel\n"
              "a1,wh,A,WH,WH_01,,1.0\na2,wh,A,WH,WH_02,,1.0\n")
    mass = {("a1", "wh"): 900.0, ("a2", "wh"): 900.0}
    cases = (("channel,district,drawn_mass\nWH,WH_01,1\nWH,WH_02,1\n", True),
             ("channel,district,drawn_mass\nWH,WH_01,1\n", False),                         # WH_02 is owned, not listed
             ("channel,district,drawn_mass\nWH,WH_01,1\nWH,WH_02,1\nWH,WH_03,1\n", False),   # WH_03 owns nothing
             ("channel,district,drawn_mass\nWH,WH_01,1\nFI,WH_02,1\n", False))            # WH_02 listed in another channel
    for districts, ok in cases:
        with tempfile.TemporaryDirectory() as tmp:
            open(os.path.join(tmp, "ledger.csv"), "w").write(ledger)
            open(os.path.join(tmp, "districts.csv"), "w").write(districts)
            try:
                rows = sealed.exact_rows(tmp, mass, {"wh": 1e6})
            except ValueError as e:
                assert not ok and "different districts" in str(e), (districts, e)
            else:
                assert ok and [r["district"] for r in rows] == ["WH_01", "WH_02"], districts
    # through the merge: the unlisted district is an error, never a label that skips its window
    with tempfile.TemporaryDirectory() as tmp:
        drv, pt = _merge_driver(tmp)
        merged = _merged_folder(tmp, "toy-pt", shape_rows=[])
        ext = data.Extract(("wh",), ["a1", "a2", "a3"], ["wh"] * 3, [900.0, 900.0, sealed.score.DOLLARS["wh"] / 1e6 - 1800.0],
                           [{}] * 3, [0.0] * 3)
        data.write(ext, drv.extract)
        open(os.path.join(merged, "ledger.csv"), "w").write(ledger)
        open(os.path.join(merged, "districts.csv"), "w").write("channel,district,drawn_mass\nWH,WH_01,1\n")
        try:
            drv._merge(pt)
        except sealed.Stop as e:
            assert e.label == "error" and "exact dollar window" in e.reason and "WH_02" in e.reason, e.reason
        else:
            raise AssertionError("a ledger district missing from districts.csv was labelled")


def test_a_ledger_cell_the_extract_lacks_stops_the_merge_unless_it_is_zero_mass_no_cell_territory():
    for row, want in (("a9,wh,A,WIFI,WIFI_01,,0.0\n", "error"),
                      (f"a9,wh,A,WIFI,WIFI_01,{sealed.ifa_index.audit.NO_CELL},0.0\n", "passes"),
                      (f"a9,wh,A,WIFI,WIFI_01,{sealed.ifa_index.audit.NO_CELL},0.5\n", "error"),
                      (f"a1,wh,A,WIFI,WIFI_01,{sealed.ifa_index.audit.NO_CELL},0.0\n", "error")):   # a1 is in the extract
        with tempfile.TemporaryDirectory() as tmp:
            drv, pt = _merge_driver(tmp)
            merged = _merged_folder(tmp, "toy-pt", shape_rows=[])
            open(os.path.join(merged, "ledger.csv"), "a").write(row)
            try:
                label = drv._merge(pt)[0]
            except sealed.Stop as e:
                label = e.label
                assert "exact dollar window" in e.reason
            assert label == want, (row, label)


def test_the_merge_waives_a_manhattan_only_failed_gate_and_vetoes_the_rest():
    real = sealed.manhattan_verdict
    try:
        for verdict, want in (({"passes": True, "excepted": [("n", ["10001"])], "blocking": []}, "passes"),
                              ({"passes": False, "excepted": [], "blocking": ["a neck without Manhattan"]}, "fails M1")):
            sealed.manhattan_verdict = lambda folder, rc, v=verdict: v if rc == 1 else None
            with tempfile.TemporaryDirectory() as tmp:
                drv, pt = _merge_driver(tmp, rcs={"gate": 1})
                _merged_folder(tmp, "toy-pt", shape_rows=[])
                label, reason, final, extra = drv._merge(pt)
                assert label == want, (label, reason)
                assert extra["summary"]["m1_manhattan_excepted"] == (["n"] if want == "passes" else [])
    finally:
        sealed.manhattan_verdict = real


def test_every_sealed_scoring_command_carries_the_full_dollar_extract_and_a_floor_district_stays_outside():
    extract = "/hub/instance_descaled_usd.json.gz"
    cmd = sealed.score_cmd("/m", extract)
    assert cmd[-2:] == ["--extract", extract] and "--dollars-csv" in cmd and cmd.count("--extract") == 1
    chain = dict((s, c) for s, c, _, _ in sealed.point_chain("p", "/p", [(("A",), "/f")], "/spec.toml", extract, None,
                                                             dict(sealed.CAPS)))
    assert chain["score"] == sealed.score_cmd("/p/merged", extract) and chain["merge"][chain["merge"].index("--base-extract") + 1] == extract
    with tempfile.TemporaryDirectory() as tmp:
        drv, pt = _merge_driver(tmp)
        _merged_folder(tmp, "toy-pt", shape_rows=[])
        drv._merge(pt)
        (score_call,) = [c for n, c in drv.calls if n == "score"]
        assert score_call[-2:] == ["--extract", drv.extract]
    # why: the merged extract holds fewer cells, so its rates are 2% high; a district $0.1M under its floor reads inside
    total, d1 = sealed.score.DOLLARS["wh"] / 1e6, 849.9
    ledger = [{"zip_code": z, "current_channel": "wh", "state": "A", "model_channel": "WH", "district": "WH_01",
               "m_rel": str(m)} for z, m in (("a1", d1),)]
    rates = {}
    with tempfile.TemporaryDirectory() as tmp:
        for name, whole in (("dollar", total), ("merged", total / 1.02)):
            path = os.path.join(tmp, name + ".json.gz")
            data.write(data.Extract(("wh",), ["a1", "a2"], ["wh", "wh"], [d1, whole - d1], [{}, {}], [0.0, 0.0]), path)
            rates[name] = sealed.score.rates_of(path)
    gate = lambda r: sealed.score.dollar_gate(ledger, [{"channel": "WH", "district": "WH_01"}], r)[0]
    assert math.isclose(rates["dollar"]["wh"], 1e6) and not gate(rates["dollar"])["ok"]
    assert gate(rates["merged"])["ok"]            # what scoring on the merged extract would have called inside


def test_every_district_s_shape_measures_are_kept_beside_the_merged_ledger():
    rows = [{"map": "toy-pt", "channel": "WIFI", "district": "WIFI_01", "hull_fill": 0.5, "bite": 0.05, "aspect": 2.0,
             "longest_axis_km": 800.0, "doughnut": 0, "doughnut_soft": 0},
            {"map": "toy-pt", "channel": "WIFI", "district": "WIFI_02", "hull_fill": 0.2, "bite": 0.4, "aspect": 5.0,
             "longest_axis_km": 1500.0, "doughnut": 1, "doughnut_soft": 1}]
    with tempfile.TemporaryDirectory() as tmp:
        limits = {"hard": False, "limits": {"bite": {"max": 0.3}}}
        drv, pt = _merge_driver(tmp, limits=limits)
        merged = _merged_folder(tmp, "toy-pt", shape_rows=rows)
        label, _, _, extra = drv._merge(pt)
        shape = json.load(open(os.path.join(merged, "shape.json")))
        assert label == "passes" and shape["error"] is None                    # report only
        assert shape["districts"] == sealed.SHAPE_ROWS and shape["summary"]["WIFI"]["bite_max"] == 0.4
        assert [(b["district"], b["measure"]) for b in shape["breaches"]] == [("WIFI_02", "bite")]
        assert json.load(open(os.path.join(merged, sealed.SHAPE_ROWS))) == rows       # every district, not only the summary
        assert extra["summary"]["shape_breaches"] == 1
    # the stage itself writes the rows (json and csv) from the study's measures
    with tempfile.TemporaryDirectory() as tmp:
        real, sealed.measure_shape = sealed.measure_shape, lambda folder, name: rows
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                sealed.cmd_shape(types.SimpleNamespace(folder="f", name="toy-pt", out_dir=tmp))
        finally:
            sealed.measure_shape = real
        assert json.load(open(os.path.join(tmp, sealed.SHAPE_ROWS))) == rows
        lines = open(os.path.join(tmp, "shape-districts.csv")).read().splitlines()
        assert lines[0].startswith("map,channel,district") and len(lines) == 3 and "WIFI_02" in lines[2]


def test_a_shape_measurement_that_hangs_is_killed_at_its_cap_and_at_the_hours_stop():
    hang = lambda folder, name, out: [sys.executable, "-c", "import time; time.sleep(120)"]
    real, sealed.shape_cmd = sealed.shape_cmd, hang
    try:
        with tempfile.TemporaryDirectory() as tmp:           # soft limits: the cap kill is reported, the label stands
            drv, pt = _merge_driver(tmp, caps=dict(sealed.CAPS, shape=1.0), real=("shape",))
            merged = _merged_folder(tmp, "toy-pt")
            t0 = time.time()
            label, reason, final, extra = drv._merge(pt)
            assert time.time() - t0 < 40 and label == "passes"
            assert drv.grid.get("toy-pt")["stages"]["shape"]["stop"] == "cap"
            err = json.load(open(os.path.join(merged, "shape.json")))["error"]
            assert "killed at its cap" in err and extra["summary"]["shape_error"] == err
        with tempfile.TemporaryDirectory() as tmp:           # hard limits: a shape that never finished is not a pass
            drv, pt = _merge_driver(tmp, caps=dict(sealed.CAPS, shape=1.0), real=("shape",),
                                    limits={"hard": True, "limits": {"bite": {"max": 0.3}}})
            _merged_folder(tmp, "toy-pt")
            t0 = time.time()
            try:
                drv._merge(pt)
            except sealed.Stop as e:
                assert e.label == "stopped" and "hard limits" in e.reason and "cap" in e.reason
            else:
                raise AssertionError("a hung shape measure under hard limits was labelled")
            assert time.time() - t0 < 40
        with tempfile.TemporaryDirectory() as tmp:           # the --hours stop ends it too, whatever the cap
            drv, pt = _merge_driver(tmp, real=("shape",))
            _merged_folder(tmp, "toy-pt")
            drv.deadline = time.time() + 1.0
            t0 = time.time()
            try:
                drv._merge(pt)
            except sealed.Stop as e:
                assert e.label == "stopped" and "during shape" in e.reason
            else:
                raise AssertionError("the launcher ran past its stop")
            assert time.time() - t0 < 40
    finally:
        sealed.shape_cmd = real


# ------------------------------------------------------------------------------ independent regions per channel
def _row(zip_, fine, state, model, district):
    return {**dict.fromkeys(output.COLUMNS, ""), "scenario": "toy", "zip_code": zip_, "current_channel": fine,
            "state": state, "model_channel": model, "district": district,
            "district_channels": model if district else "", "m_rel": 1.0}


def _run_folder(path, rows, channels):
    os.makedirs(path)
    output.write_ledger(os.path.join(path, "ledger.csv"), rows)
    with open(os.path.join(path, "districts.csv"), "w", newline="") as fh:
        fh.write("channel,district,district_name,copy,support,planned_mass,drawn_mass,pieces\n")
        for c, j in sorted({(r["model_channel"], r["district"]) for r in rows if r["district"]}):
            fh.write(f"{c},{j},,{j}#1,CA,1.0,1.0,0\n")
    json.dump({"channels": {c: {"status": "optimal"} for c in channels}, "m1": {"status": "pass"}},
              open(os.path.join(path, "run.json"), "w"))
    json.dump({"status": "done", "provenance": {"commit": "abc123"}}, open(os.path.join(path, "manifest.json"), "w"))
    return path


INDEPENDENT = [
    # (run, states, channels, rows): the national regions are {CA, TX} and the rest, the WIFI regions {CA, NY} and the rest
    ("south-national", ("CA", "TX"), ["national"], [
        _row("90001", "national_chase", "CA", "national", "national_01"),
        _row("75001", "national_chase", "TX", "national", "national_01"),
        _row("90001", "wh", "CA", "WIFI", "")]),                         # WIFI's cell, drawn in the other region
    ("south-WIFI", ("CA", "NY"), ["WIFI"], [
        _row("90001", "wh", "CA", "WIFI", "WIFI_01"), _row("10001", "wh", "NY", "WIFI", "WIFI_01"),
        _row("10001", "national_chase", "NY", "national", "")]),
    ("rest-national", ("FL", "NY"), ["national"], [
        _row("33101", "national_chase", "FL", "national", "national_01"),
        _row("10001", "national_chase", "NY", "national", "national_01")]),
    ("rest-WIFI", ("FL", "TX"), ["WIFI"], [
        _row("33101", "wh", "FL", "WIFI", "WIFI_01"), _row("75001", "wh", "TX", "WIFI", "WIFI_01"),
        _row("33101", "national_chase", "FL", "national", "")]),
]


def _independent_runs(tmp):
    runs = [{"name": n, "states": st, "ks": {c: 1 for c in chans}} for n, st, chans, _ in INDEPENDENT]
    folders = {n: _run_folder(os.path.join(tmp, "runs", n), rows, chans) for n, _, chans, rows in INDEPENDENT}
    return runs, folders


def _combine(runs, folders, out):
    """`combine_point` with a scenario and an extract file beside the output (its manifest hashes both)."""
    tmp = os.path.dirname(out)
    spec, extract = os.path.join(tmp, "spec-merge.toml"), os.path.join(tmp, "extract.json.gz")
    for path in (spec, extract):
        if not os.path.exists(path):
            os.makedirs(tmp, exist_ok=True)
            open(path, "w").write(path)
    return sealed.combine_point(runs, folders, out, spec, extract)


def test_combine_takes_each_cell_from_the_run_that_owns_its_channel_in_its_state():
    with tempfile.TemporaryDirectory() as tmp:
        runs, folders = _independent_runs(tmp)
        out = os.path.join(tmp, "combined")
        got = _combine(runs, folders, out)
        led = output.read_ledger(os.path.join(out, "ledger.csv"))
        cells = {(r["zip_code"], r["current_channel"]): (r["district"], r["model_channel"]) for r in led}
        assert got == {"cells": 8, "districts": 4} and len(led) == 8
        assert cells == {("90001", "national_chase"): ("south-national/national_01", "national"),
                         ("75001", "national_chase"): ("south-national/national_01", "national"),
                         ("90001", "wh"): ("south-WIFI/WIFI_01", "WIFI"), ("10001", "wh"): ("south-WIFI/WIFI_01", "WIFI"),
                         ("10001", "national_chase"): ("rest-national/national_01", "national"),
                         ("33101", "national_chase"): ("rest-national/national_01", "national"),
                         ("33101", "wh"): ("rest-WIFI/WIFI_01", "WIFI"), ("75001", "wh"): ("rest-WIFI/WIFI_01", "WIFI")}
        dist = list(csv_rows(os.path.join(out, "districts.csv")))
        assert sorted(r["district"] for r in dist) == sorted({j for j, _ in cells.values()})
        m = json.load(open(os.path.join(out, "manifest.json")))        # its own manifest (T1), not a source's
        assert (m["run_id"], m["lane"], m["status"], m["stop_reason"]) == ("combined", "contig", "done", "combined")
        assert m["formulation"] == "sealed_combine" and m["command"] and m["finished_at"]
        assert m["scenario"]["sha256"] and m["provenance"]["instance_sha256"] and len(m["provenance"]["commit"]) == 40
        assert m["provenance"] != {"commit": "abc123"} and {"dirty", "diff_sha256", "host"} <= set(m["provenance"])
        assert [(r["run"], r["commit"], r["folder"]) for r in m["source_runs"]] == [
            (n, "abc123", os.path.abspath(folders[n])) for n, *_ in INDEPENDENT]
        assert m["combined_from"] == {n: os.path.abspath(f) for n, f in folders.items()}
        rj = json.load(open(os.path.join(out, "run.json")))
        assert rj["channels"]["WIFI"]["status"] == "south-WIFI optimal; rest-WIFI optimal" and "m1" in rj
        # a district a run never listed in districts.csv is refused, not merged
        os.remove(os.path.join(folders["rest-WIFI"], "districts.csv"))
        open(os.path.join(folders["rest-WIFI"], "districts.csv"), "w").write(
            "channel,district,district_name,copy,support,planned_mass,drawn_mass,pieces\n")
        try:
            _combine(runs, folders, out)
        except ValueError as e:
            assert "rest-WIFI" in str(e) and "not in districts.csv" in str(e)
        else:
            raise AssertionError("combined a district with no districts.csv row")
        m = json.load(open(os.path.join(out, "manifest.json")))
        assert m["status"] == "failed" and "not in districts.csv" in m["stop_reason"]


def test_a_combined_folder_of_independent_channels_is_a_run_of_its_own_in_the_tracker_index():
    """Mandate T1: `tools/exp/index.py` needs `run_id`, `lane`, `formulation`, `folder` and `status` of
    every manifest it finds; the combined folder's is written by `run.write_manifest`, with the source
    runs' folders and commits as its lineage."""
    spec = importlib.util.spec_from_file_location("exp_index_t", os.path.join(CONTIG, "..", "index.py"))
    index = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(index)
    with tempfile.TemporaryDirectory() as tmp:
        runs, folders = _independent_runs(tmp)
        out = os.path.join(tmp, "exp", "contig", "toy-pt", "combined")
        _combine(runs, folders, out)
        (row,) = index.rebuild(os.path.join(tmp, "exp"))
        assert (row["run_id"], row["lane"], row["formulation"], row["status"]) == ("combined", "contig", "sealed_combine", "done")
        assert row["folder"] == out and row["commit"] and row["commit"] != "abc123" and row["instance_sha256"]
        assert row["params"]["runs"]["south-national"] == {"states": ["CA", "TX"], "channels": ["national"]}


def csv_rows(path):
    import csv
    with open(path, newline="") as fh:
        yield from csv.DictReader(fh)


def test_a_cell_of_no_run_s_channel_comes_from_the_first_run_holding_its_state_and_no_cell_twice():
    with tempfile.TemporaryDirectory() as tmp:
        runs = [{"name": "a", "states": ("CA",), "ks": {"national": 1}}, {"name": "b", "states": ("CA", "TX"), "ks": {"national": 1}}]
        folders = {"a": _run_folder(os.path.join(tmp, "a"), [_row("90001", "career", "CA", "", ""),
                                                             _row("90001", "national_chase", "CA", "national", "national_01")], ["national"]),
                   "b": _run_folder(os.path.join(tmp, "b"), [_row("90001", "career", "CA", "", ""),
                                                             _row("75001", "career", "TX", "", ""),
                                                             _row("90001", "national_chase", "CA", "national", "national_01")], ["national"])}
        _combine(runs, folders, os.path.join(tmp, "out"))
        led = output.read_ledger(os.path.join(tmp, "out", "ledger.csv"))
        by = {(r["zip_code"], r["current_channel"]): r["district"] for r in led}
        assert by == {("90001", "career"): "", ("75001", "career"): "", ("90001", "national_chase"): "a/national_01"}


def test_a_run_of_some_channels_reads_an_extract_cut_to_their_fine_channels():
    with tempfile.TemporaryDirectory() as tmp:
        sp = tdspec.load(_toy_file(tmp))
        src = os.path.join(tmp, "toy-extract.json.gz")
        ext = data.Extract(("national_chase", "wh"), ["90001", "90001", "75001"], ["national_chase", "wh", "wh"],
                           [1.0, 2.0, 3.0], [{"R1": 0.5}, {"R2": 1.0}, {"R1": 0.25}], [0.1, 0.2, 0.3],
                           {"R1": "F1", "R2": "F2"}, {"note": "kept"})
        data.write(ext, src)
        plan = sealed.region_plan(sp, ("CA", "TX"), {"national": 2}, CELLS, "base")
        assert list(plan["channels"]) == ["national"] and plan["outside"] == ["WIFI"] and plan["absent"] == []
        assert sealed.run_fine(sp, ["national"]) == {"national_chase"}
        both = sealed.region_plan(sp, ("CA", "TX"), {"national": 2, "WIFI": 2}, CELLS, "base")
        assert both["outside"] == []
        drv, pt, run = _stub_driver(tmp, None, [])
        drv.extract = src
        drv.state_of = {"90001": "CA", "75001": "TX"}
        assert drv.run_extract(sp, run, both, os.path.join(tmp, "r")) == src                   # nothing outside: the extract itself
        rdir = os.path.join(tmp, "r")
        os.makedirs(rdir)
        mine = dict(run, ks={"national": 2})
        path = drv.run_extract(sp, mine, plan, rdir)
        assert path == os.path.join(rdir, "extract.json.gz") and not os.path.exists(path + ".tmp")
        cut = data.load(path)
        assert cut.channels == ("national_chase",) and cut.z == ["90001"] and cut.channel == ["national_chase"]
        assert cut.meta["note"] == "kept" and data.load(src).z == ["90001", "90001", "75001"]       # the source is untouched
        assert cut.m_rel == [1.0]                                                                   # the model's column stays
        assert cut.share == [{}] and cut.share_free == [0.0] and cut.firm == {}                    # no sales data in the cut
        assert data.load(src).firm and any(data.load(src).share)                                    # the source carries it


CT_TOY = """[scenario]
name = "toy-ct"
fine_channels = ["national_chase", "wh"]
planned_elsewhere = ["career", "edj", "fi", "ifa", "imo", "priafs", "wells_fi", "wells_wh"]

[channels.national]
k = 2
domain = [{ units = "all - CT", fine = ["national_chase"] }]
mode = "whole"
eta = 0.05

[channels.WH]
k = 2
domain = [{ units = "all - CT", fine = ["wh"] }]
mode = "whole"
eta = 0.05

[channels.WIFI]
k = 1
domain = [{ units = ["CT"], fine = ["national_chase", "wh"] }]
mode = "whole"
eta = 0.05
"""


def test_a_national_only_region_with_ct_does_not_read_the_cts_national_chase_cells_that_wifi_owns():
    """`main_ne_plains` plans national_chase in CT under WIFI, in every other state under national: a
    run of national over CA + CT keeps CA's national_chase cells only."""
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "toy-ct.toml")
        open(path, "w").write(CT_TOY)
        sp = tdspec.load(path)
        cells = {("CA", "national_chase"): 1500.0, ("CT", "national_chase"): 400.0, ("CA", "wh"): 1000.0, ("CT", "wh"): 300.0}
        plan = sealed.region_plan(sp, ("CA", "CT"), {"national": 2}, cells, "base")
        assert list(plan["channels"]) == ["national"] and plan["outside"] == ["WH", "WIFI"]
        assert sealed.run_cells(sp, ["national"]) >= {("CA", "national_chase")} and ("CT", "national_chase") not in sealed.run_cells(sp, ["national"])
        src = os.path.join(tmp, "toy-extract.json.gz")
        data.write(data.Extract(("national_chase", "wh"), ["90001", "06001", "90001", "06001"],
                                ["national_chase", "national_chase", "wh", "wh"], [1.0, 2.0, 3.0, 4.0],
                                [{}, {}, {}, {}], [0.0] * 4, {}, {}), src)
        drv, pt, run = _stub_driver(tmp, None, [])
        drv.extract, drv.state_of = src, {"90001": "CA", "06001": "CT"}
        rdir = os.path.join(tmp, "r")
        os.makedirs(rdir)
        cut = data.load(drv.run_extract(sp, dict(run, ks={"national": 2}), plan, rdir))
        assert cut.z == ["90001"] and cut.channel == ["national_chase"] and cut.channels == ("national_chase",)


def test_dry_run_of_independent_regions_cuts_the_extract_and_merges_the_combined_ledger():
    nat = _doc()["points"][0]["channels"]["national"]
    wifi = {"regions": [{"name": "south", "states": ["CA", "NY"], "k": 2}], "rest": True}
    with tempfile.TemporaryDirectory() as tmp:
        (pt,) = _validate(_doc(channels={"national": nat, "WIFI": wifi}), tmp)
        root = os.path.join(tmp, "root")
        os.makedirs(root)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            sealed.cmd_dry_run(types.SimpleNamespace(root=root, extract="/x/extract.json.gz", max_size=None,
                                                     drawable_alone=True), [pt], CELLS, dict(sealed.CAPS), set())
        assert os.listdir(root) == []
    text = out.getvalue()
    for name, other in (("south-national", "WIFI"), ("south-WIFI", "national"), ("rest-national", "WIFI"), ("rest-WIFI", "national")):
        block = text.split(f"==== run {name} ")[1].split("==== ")[0]
        assert f"channels of other regions with cells here ({other})" in block
        assert re.search(rf"sealed\.py replan \S+ .*--extract \S+/{name}/extract\.json\.gz ", block)
        assert re.search(rf"run\.py \S+ .*--extract \S+/{name}/extract\.json\.gz ", block)
        assert re.search(rf"glue\.py .*--extract \S+/{name}/extract\.json\.gz ", block)
    merge = re.search(r"^\[merge, .*$", text, re.M).group(0)
    assert "regions are independent per channel" in text and re.search(r"[A-Z+]+=\S+/toy-pt/combined ", merge)
    assert re.search(r"^\[combine, cap 600 s\] .*sealed\.py combine --runs \S+/toy-pt/combine-args\.json --out \S+/toy-pt/combined ",
                     text, re.M)
    assert "/glue " not in merge


def test_a_point_of_independent_regions_is_merged_from_the_combined_ledger():
    nat = _doc()["points"][0]["channels"]["national"]
    wifi = {"regions": [{"name": "south", "states": ["CA", "NY"], "k": 2}], "rest": True}
    with tempfile.TemporaryDirectory() as tmp:
        doc = _doc(channels={"national": nat, "WIFI": wifi})
        made = []
        drv, pt = _merge_driver(tmp, doc=doc, real=("combine",),       # the combine stage runs as the child it is
                                on_merge=lambda: made.append(_merged_folder(tmp, "toy-pt", shape_rows=[])))
        assert sorted(r["name"] for r in pt["runs"]) == ["rest-WIFI", "rest-national", "south-WIFI", "south-national"]
        for n, st, chans, rows in INDEPENDENT:           # the final folders the runs left, by the run names validate gave
            _run_folder(os.path.join(tmp, "toy-pt", n, "glue"), rows, chans)
        label, reason, final, extra = drv._merge(pt)
        assert label == "passes" and made
        merge = dict(drv.calls)["merge"]
        assert merge[merge.index("--out") - 1].endswith("toy-pt/combined") and "/glue" not in " ".join(merge)
        assert [n for n, _ in drv.calls][:2] == ["combine", "merge"]
        assert drv.grid.get("toy-pt")["stages"]["combine"]["rc"] == 0
        led = output.read_ledger(os.path.join(tmp, "toy-pt", "combined", "ledger.csv"))
        assert len(led) == 8 and {r["district"] for r in led if r["district"]} >= {"south-national/national_01"}
