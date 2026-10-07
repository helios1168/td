"""tools/exp/contig/wholeplan.py and pieces.py (td#127) on toys: a whole-unit district failing M1
is banned as its exact unit set and the re-plan passes; with no other plan the loop says "no
plan" and lists the ban; an unknown verdict is never a ban; the copy holds every unit whole; and a
state's county pieces are connected, pass M1 and cover the state."""
from __future__ import annotations

import importlib.util
import os
import sys
import tomllib

import pandas as pd

from td import audit
from td import spec as tdspec

from tests import test_realize as tr

HERE = os.path.dirname(os.path.abspath(__file__))
QUIET = dict(log=lambda *_: None)


def _module(name: str, file: str):
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            name, os.path.join(HERE, "..", "tools", "exp", "contig", file))
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
    return sys.modules[name]


def _wholeplan():
    return _module("contig_wholeplan", "wholeplan.py")


def _neck_toy(k: int, q_x: float = 10.0):
    """PA (p0, 100 km², mass 1), NY (n1-n2-n3, whole; 1, 1 and 10 km², mass 0.01 each) and NJ
    (q0, 100 km², mass 1) on a path; n1-n2 and n2-n3 share 1 km of border, p0-n1 and n3-q0 20 km.
    PA+NY is a neck: n3's 10 km² (over 5% of the land) hangs off a 1 km passage.  NY+NJ is not:
    the part past its 1 km passages, n1 (or n1 and n2), is under 5%.  NJ sits at x = `q_x` km, so
    PA+NY is the shorter support and the master's first choice."""
    edges = [("p0", "n1"), ("n1", "n2"), ("n2", "n3"), ("n3", "q0")]
    km = {("n1", "p0"): 20.0, ("n1", "n2"): 1.0, ("n2", "n3"): 1.0, ("n3", "q0"): 20.0}
    xy = {"p0": (0.0, 0.0), "n1": (1.0, 0.0), "n2": (2.0, 0.0), "n3": (3.0, 0.0), "q0": (q_x, 0.0)}
    mass = {"p0": 1.0, "q0": 1.0, "n1": 0.01, "n2": 0.01, "n3": 0.01}
    inst, _ = tr._toy({"PA": ["p0"], "NY": ["n1", "n2", "n3"], "NJ": ["q0"]}, edges, mass, xy,
                      k=k, delta=0.1, eta=0.05)
    polygon = {"vertices": sorted(xy), "edges": edges, "state": dict(inst.units.unit_of),
               "border": {e: 1000.0 * x for e, x in km.items()}, "connectors": [],
               "aland": {"p0": 1e8, "q0": 1e8, "n1": 1e6, "n2": 1e6, "n3": 1e7}}
    return inst, polygon


def test_a_district_failing_m1_is_banned_as_its_unit_set_and_the_replan_passes():
    """Round 1 plans PA+NY and NJ; PA+NY has a neck, so it is banned (exact unit set, with the
    neck as its reason) and round 2 plans PA and NJ+NY, which pass."""
    wp = _wholeplan()
    inst, polygon = _neck_toy(2)
    res = wp.loop(inst, "X", polygon, **QUIET)
    assert res["status"] == "passed", res
    assert [b["support"] for b in res["bans"]] == ["NY+PA"], res["bans"]
    assert res["bans"][0]["why"].startswith("neck") and res["bans"][0]["round"] == 1
    assert len(res["rounds"]) == 2 and res["rounds"][0]["new_bans"] == ["NY+PA"]
    assert sorted(wp._name(s) for s in res["plan"].n) == ["NJ+NY", "PA"]
    assert all(res["verdicts"][wp._name(s)]["status"] == "pass" for s in res["plan"].n)
    assert res["delta"] >= res["rounds"][-1]["exact_delta"]


def test_with_no_plan_left_the_loop_says_no_plan_and_lists_every_ban():
    """K = 1: the only support, NJ+NY+PA, has a neck; banned, the master has no plan."""
    wp = _wholeplan()
    inst, polygon = _neck_toy(1)
    res = wp.loop(inst, "X", polygon, **QUIET)
    assert res["status"] == "no plan", res
    assert [b["support"] for b in res["bans"]] == ["NJ+NY+PA"]
    assert res["bans"][0]["why"].startswith("neck")


def test_an_unknown_verdict_is_never_a_ban():
    wp = _wholeplan()
    inst, polygon = _neck_toy(2)
    res = wp.loop(inst, "X", polygon, check=lambda *_: {"status": "unknown", "why": "time"},
                  **QUIET)
    assert res["status"] == "unknown" and not res["bans"], res
    assert sorted(res["rounds"][0]["unknown"]) == ["NJ", "NY+PA"]


def test_m1_verdict_fails_a_district_in_two_pieces():
    wp = _wholeplan()
    inst, polygon = _neck_toy(2)
    v = wp.m1_verdict({"p0", "q0"}, inst.channels["X"].m, audit.adjacency(polygon),
                      audit.NeckGraph(polygon))
    assert v["status"] == "fail" and v["why"].startswith("2 pieces"), v


TOML = """[scenario]
name = "toy"
fine_channels = ["ifa"]

[channels.IFA]
k = 49
domain = [{ units = "all", fine = ["ifa"] }]
mode = "whole"
free = ["CA", "NY"]
eta = 0.05
max_size = 6
dist_km = { CA = 1600 }
delta = 0.02
final_delta = 0.1
"""


def test_the_copy_holds_every_unit_whole_with_its_bans_and_pieces():
    wp = _wholeplan()
    cut = [tdspec.Piece("CA_p1", "CA", frozenset({"06037"}))]
    text = wp.copy_text(TOML, "IFA", 46, 0.6, 0.6, [frozenset({"UT"}), frozenset({"NJ", "DE"})],
                        cut, "toy.toml")
    s = tdspec.parse(tomllib.loads(text))
    cs = s.channels["IFA"]
    assert cs.k == 46 and cs.delta == 0.6 and cs.final_delta == 0.6
    assert set(cs.modes.values()) == {"whole"}
    assert set(cs.ban_supports) == {frozenset({"UT"}), frozenset({"DE", "NJ"})}
    assert [p.name for p in s.pieces] == ["CA_p1"] and cs.dist_km["CA_p1"] == 1600


def _grid_state(n: int = 4):
    """NY as an n × n grid of ZIPs, each a 2 × 2 block of counties (36001, 36003, ...), mass 1
    per ZIP, 6 km of border per grid edge; K 2 gives τ = half the state, so 2 parts."""
    zs = {(x, y): f"1{x}{y}00" for x in range(n) for y in range(n)}
    county = {zs[x, y]: f"36{(x // 2) * (n // 2) + (y // 2):03d}" for x, y in zs}
    edges = [(zs[a], zs[b]) for a in zs for b in zs
             if a < b and abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1]
    xy = {zs[q]: (10.0 * q[0], 10.0 * q[1]) for q in zs}
    inst, _ = tr._toy({"NY": list(zs.values())}, edges, dict.fromkeys(zs.values(), 1.0), xy,
                      k=2, delta=0.1, eta=0.05)
    polygon = {"vertices": sorted(zs.values()), "edges": edges, "state": dict(inst.units.unit_of),
               "border": {tuple(e): 6000.0 for e in edges}, "connectors": [],
               "aland": dict.fromkeys(zs.values(), 1e8)}
    ref = pd.DataFrame({"zcta": list(county), "county": list(county.values()),
                        "x": [str(1000.0 * xy[z][0]) for z in county],
                        "y": [str(1000.0 * xy[z][1]) for z in county]})
    return inst, polygon, ref, county


def test_the_pieces_are_connected_pass_m1_and_cover_the_state():
    wp, pc = _wholeplan(), _module("contig_pieces", "pieces.py")
    inst, polygon, ref, county = _grid_state()
    adj, ng = audit.adjacency(polygon), audit.NeckGraph(polygon)
    tau = sum(inst.channels["X"].M.values()) / 2
    out, rec = pc.cut_state(inst, ref, "X", "NY", tau, wp.m1_verdict, adj, ng)
    assert [p.name for p in out] == ["NY_p1"] and rec["parts"] == 2
    rest = set(county.values()) - set().union(*(p.counties for p in out))
    parts = [set(p.counties) for p in out] + [rest]
    assert sorted(c for p in parts for c in p) == sorted(set(county.values()))     # cover, disjoint
    m = inst.channels["X"].m
    for p in parts:
        zips = {z for z, c in county.items() if c in p}
        assert pc.connected(zips, inst.units.zip_adj)
        assert wp.m1_verdict(zips, m, adj, ng)["status"] == "pass"
    assert rec["pieces"][0]["mass_tau"] == rec["remainder"]["mass_tau"] == 1.0
    assert rec["big_counties"] == []
