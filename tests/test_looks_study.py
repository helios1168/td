"""tools/looks/study.py on a toy ledger with hand-computed values."""
from __future__ import annotations

import importlib.util
import math
import os
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "looks_study", os.path.join(HERE, "..", "tools", "looks", "study.py"))
study = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(study)

# Each ZIP is 1 km2.  A holds the corners of a 2 km square, B the one ZIP at its centre, C a small
# triangle far east.  A and B share state S and county c1; C is in state T.
ZIPS = {"a1": (0, 0, "A"), "a2": (2, 0, "A"), "a3": (0, 2, "A"), "a4": (2, 2, "A"), "b1": (1, 1, "B"),
        "c1": (10, 0, "C"), "c2": (10, 1, "C"), "c3": (11, 0, "C")}
MASS = {"a1": 1, "a2": 1, "a3": 1, "a4": 1, "b1": 8, "c1": 1, "c2": 1, "c3": 1}
CBSA = {"a1": "k", "a2": "k", "a3": "k", "b1": "k"}        # a4 and C are rural


def _ref():
    names = list(ZIPS)
    edges = [("b1", a) for a in ("a1", "a2", "a3", "a4")] + [("c1", "c2"), ("c1", "c3")]
    return study.Ref(names, [ZIPS[z][0] for z in names], [ZIPS[z][1] for z in names], [1.0] * len(names),
                     edges, {"k": "Kay Metro Area"})


def _rows():
    return [{"zip_code": z, "state": "S" if d != "C" else "T", "model_channel": "X", "district": d,
             "county": "c1" if d != "C" else "c9", "cbsa": CBSA.get(z, ""), "m_rel": str(MASS[z]),
             "current_channel": "x"} for z, (_, _, d) in ZIPS.items()]


def test_hull_bite_axis_cut_and_effort():
    out, conflicts = study.measure_map("toy", _rows(), _ref(), {"x": 2.0})
    a, b, c = (next(r for r in out if r["district"] == d) for d in "ABC")
    assert conflicts == 0
    # A: a 2x2 square hull of area 4 holding its own 4 km2 of land, B's ZIP inside it
    assert a["hull_km2"] == 4.0 and a["hull_fill"] == 1.0 and a["bite"] == 0.25
    assert a["bite_states"] == "S:0.250"
    assert math.isclose(a["longest_axis_km"], 2 * math.sqrt(2), abs_tol=0.05) and a["aspect"] == 2.0
    # B is one point: no hull, nothing to bite
    assert b["hull_km2"] == 0.0 and b["hull_fill"] == 1.0 and b["bite"] == 0.0
    # C: 3 km2 on a triangle of 0.5 km2: fill capped at 1, raw 6
    assert c["hull_fill"] == 1.0 and c["hull_fill_raw"] == 6.0 and c["cut_edges"] == 0
    # the cut: four A-B edges and county c1 in state S, seen from both districts
    assert a["cut_edges"] == b["cut_edges"] == 4 and a["cut_counties"] == b["cut_counties"] == 1
    assert a["cut_detail"] == "S:e4/c1"
    # $ = 2 * m_rel; A's land 4 km2 over $8M; the four corners sit sqrt(2) from their centroid
    assert a["usd_m"] == 8.0 and a["land_per_usd"] == 0.5
    assert math.isclose(a["wmean_dist_km"], math.sqrt(2), abs_tol=0.05)
    assert math.isclose(a["r90_km"], math.sqrt(2), abs_tol=0.05)
    assert b["wmean_dist_km"] == 0.0 and b["states"] == "S"


def test_doughnut_and_hub():
    out, _ = study.measure_map("toy", _rows(), _ref())
    a, b = (next(r for r in out if r["district"] == d) for d in "AB")
    # CBSA k (4 ZIPs, 11 m_rel): B holds 8/11 of its mass on 1/4 of its land, A the other 3 ZIPs
    assert b["core_without_ring"].startswith("Kay Metro Area (m 73%, land 25%)") and b["doughnut"] == 1
    assert a["ring_without_core"] == "Kay Metro Area (land 75%, m 27%)" and a["doughnut"] == 1
    assert b["hub"] == "Kay Metro Area" and b["hub_share"] == 1.0
    assert a["hub"] == "Kay Metro Area" and a["hub_share"] == 0.75
    # C holds no CBSA
    c = next(r for r in out if r["district"] == "C")
    assert c["doughnut"] == 0 and c["hub"] == ""


def test_census_pseudo_ledger_and_aggregate():
    rows = [{"state": s, "model_channel": "X", "district": "X_01", "zip_code": s} for s in ("DC", "MD", "CA", "AK")]
    div = {r["district"] for r in study.census_rows(rows, "division")}
    reg = {r["district"] for r in study.census_rows(rows, "region")}
    assert div == {"X:South Atlantic", "X:Pacific"} and reg == {"X:South", "X:West"}     # AK has no row
    assert sum(len(v.split()) for v in study.DIVISIONS.values()) == 49 == len(study.REGION_OF)
    out, _ = study.measure_map("toy", _rows(), _ref())
    m = study.aggregate("toy", "main", out, {})
    assert m["districts"] == 3 and m["bite_max"] == 0.25 and m["doughnuts"] == 2
    assert study.rank_key(m) == (2, 0.25, -m["hull_fill_min"])


def test_score_fields():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "score.txt")
        assert study.score_fields(p)["m1"] == ""
        with open(p, "w") as fh:
            fh.write("eligible: no\nM1: fail, 2 districts in pieces, 1 detached pieces, 3 necks, 0 x\n"
                     "channel-state splits: 12: FI:CA\n")
        got = study.score_fields(p)
    assert got == {"eligible": "no", "m1": "fail", "pieces": 2, "necks": 3, "splits": 12}
