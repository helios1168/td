"""tools/looks/study.py on a toy ledger with hand-computed values."""
from __future__ import annotations

import importlib.util
import math
import os
import sys
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
    # no outline and no water connectors: the land-hull measures equal the v1 ones (2026-10-14)
    assert a["hull_land_km2"] == 4.0 and a["hull_fill_v1"] == 1.0 and a["bite_v1"] == 0.25
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


def _square(land_edges, extra_edges=(), outline=None):
    """District D on the corners of a 4 km square (1 km2 each) and district E: e_land (2, 1) tied to
    d1 by land, e_water (2, 3) tied to d3 by an edge that `land_edges` lacks (a bridge or ferry),
    e_out (1, 2) tied to d4 only through f (6, 6), outside D's hull."""
    z = {"d1": (0, 0, "D"), "d2": (4, 0, "D"), "d3": (0, 4, "D"), "d4": (4, 4, "D"), "e_land": (2, 1, "E"),
         "e_water": (2, 3, "E"), "e_out": (1, 2, "E"), "f": (6, 6, "E")}
    names = list(z)
    ref = study.Ref(names, [z[n][0] for n in names], [z[n][1] for n in names], [1.0] * len(names),
                    list(land_edges) + list(extra_edges), land_edges=land_edges, outline=outline)
    rows = [{"zip_code": n, "state": "S", "model_channel": "X", "district": z[n][2], "county": "c1", "cbsa": "",
             "m_rel": "1", "current_channel": "x"} for n in names]
    out, _ = study.measure_map("toy", rows, ref)
    return next(r for r in out if r["district"] == "D")


def test_hull_fill_over_land_only():
    # owner, 2026-10-14: "yes make your updates in 1." (land-only outline, no counting across water).
    # The outline is the south half of D's 4x4 hull: the north half is ocean, so 4 km2 of land
    # over 8 km2 of land hull is 0.5, where v1 over the full 16 km2 says 0.25.
    import shapely
    d = _square([], outline=shapely.box(-1, -1, 7, 2))
    assert d["hull_km2"] == 16.0 and d["hull_land_km2"] == 8.0
    assert d["hull_fill"] == 0.5 and d["hull_fill_v1"] == 0.25 and d["hull_fill_raw"] == 0.5
    # a hull wholly over water has no land to fill: fill 1, no bite
    w = _square([], outline=shapely.box(100, 100, 101, 101))
    assert w["hull_land_km2"] == 0.0 and w["hull_fill"] == 1.0 and w["bite"] == 0.0 and w["bite_v1"] > 0


def test_bite_counts_only_land_reachable_in_the_hull():
    # owner, 2026-10-14: a neighbour's ZIP bites only when no water separates it from the district
    land = [("d1", "e_land"), ("e_out", "f"), ("f", "d4")]
    d = _square(land, extra_edges=[("d3", "e_water")])
    # v1 counts all three ZIPs with a centroid in the hull; v2 only e_land: e_water hangs on a
    # water connector and e_out reaches D only through f, outside the hull
    assert d["bite_v1"] == 3 / 16 and d["bite"] == 1 / 16
    assert d["bite_states"].startswith("S:0.06")
    # land everywhere: a connector that is land (a `road` gap) keeps the ZIP in
    d = _square(land + [("d3", "e_water")])
    assert d["bite"] == 2 / 16 and d["bite_v1"] == 3 / 16


def test_arms_roughness_and_water_wrap():
    # owner calibration, 2026-10-14: "the tentacles or trees that come out of the main 'blob'".
    # A 20x20 km body with and without a 1 km wide, 10 km long arm; the outline is a 40 km box
    # whose south and west edges are the body's (coast there), the rest of its boundary land.
    import shapely
    box = shapely.box
    outline = box(0, 0, 40, 40)

    def measures(*pieces):
        shapes = {f"p{i}": g for i, g in enumerate(pieces)}
        ref = study.Ref(list(shapes), [0.0] * len(shapes), [0.0] * len(shapes), [1.0] * len(shapes), [],
                        outline=outline, shapes=shapes)
        return study.shape_measures(ref, list(shapes))

    # ZCTAs tile as a coverage (shared edges carry the same vertices), which the study's union relies on
    square = shapely.Polygon([(0, 0), (20, 0), (20, 9), (20, 10), (20, 20), (0, 20)])
    body = measures(square)
    arm = measures(square, box(20, 9, 30, 10))
    # the arm is 10 of 410 km2 and narrower than every W, so it adds 10/410 on top of what rounding
    # the body's four corners removes ((4 - pi) r^2 of the 400 km2: 5.4% at r = 5, 1.3% at r = 2.5)
    assert math.isclose(body["arm_share"], (4 - math.pi) * 25 / 400, abs_tol=0.01)
    assert math.isclose(body["arm_share_w5"], (4 - math.pi) * 6.25 / 400, abs_tol=0.005)
    assert 0.02 < arm["arm_share"] - body["arm_share"] < 0.03
    assert 0.02 < arm["arm_share_w5"] - body["arm_share_w5"] < 0.03
    # a disc of diameter 40 fits nowhere in a 20 km body
    assert body["arm_share_w40"] == 1.0 and arm["arm_share_w40"] == 1.0
    # roughness: the square's north and east sides are land boundary, 40 km less COAST_KM at the two corners
    # where they meet the coast (39 km); the arm adds 20 (21 around it, less the 1 km of east side it replaces)
    root = lambda area: 2 * math.sqrt(math.pi * area)                      # noqa: E731
    assert math.isclose(body["roughness"], 39 / root(400), rel_tol=1e-3)
    assert math.isclose(arm["roughness"], 59 / root(410), rel_tol=1e-3)
    # water_wrap: the hull of the ocean fixture is half water
    assert _square([], outline=box(-1, -1, 7, 2))["water_wrap"] == 0.5
    # no shapes, no measure
    assert math.isnan(_square([])["arm_share"]) and _square([])["water_wrap"] == 0.0


def test_long_island_is_not_bitten_across_the_sound():
    # owner, 2026-10-14: "Long Island vs Connecticut across the Sound must no longer count".  On the
    # real 2025 polygon graph: a district of every CT and RI ZIP has Long Island ZIPs (Suffolk,
    # Nassau, Queens, Kings) with a centroid in its hull, and no land path from it to them.
    hub = study.HUB
    if not os.path.exists(study.OUTLINE_ZIP) or not os.path.exists(os.path.join(study.geo.REFERENCE_DIR, "connectors.csv")):
        print(f"SKIP  test_looks_study.py: no {study.OUTLINE_ZIP} (set $TD_REPO to the hub, {hub!r}); "
              "the Long Island test did not run", file=sys.stderr)
        return
    ref = study.Ref.load()
    zr = study.geo.read_reference()
    zr = zr[zr["graph_vertex"] == "1"]
    long_island = {"36103", "36059", "36081", "36047"}
    cells = {z: {"d": "CTRI", "s": s, "county": c, "cbsa": "", "m": 1.0, "usd": 1.0}
             for z, s, c in zip(zr["zcta"], zr["state"], zr["county"]) if s in ("CT", "RI")}
    cells.update({z: {"d": "LI", "s": s, "county": c, "cbsa": "", "m": 1.0, "usd": 1.0}
                  for z, s, c in zip(zr["zcta"], zr["state"], zr["county"]) if c in long_island})
    d = next(r for r in study.measure_channel("toy", "X", cells, ref) if r["district"] == "CTRI")
    assert d["bite_v1"] > 0 and d["bite"] == 0.0 and d["bite_states"] == ""
    assert d["hull_land_km2"] < d["hull_km2"] and d["hull_fill"] > d["hull_fill_v1"]


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
