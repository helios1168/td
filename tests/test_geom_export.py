"""
test_geom_export.py -- the polygon export (tools/geom_export.py) on a synthetic two-state map.

No network, no shapefile and no instance: the basemap is a hand-built GeoDataFrame of two square
"states" in the same shape `td.geo.states_outline` returns (an `STUSPS` column and a geometry
column), and the table is twelve zips laid out on a grid across them.  The squares are in metres
so the export's rounding and its default simplify tolerance are exercised at the scale the real
LAEA map uses.

Layout, all coordinates in metres:

    AA = [0, 200k] x [0, 200k]          BB = [200k, 400k] x [0, 200k]
    D01 at x = 50k, D02 at x = 150k     D03 at x = 250k and x = 350k

so D01 touches D02, D02 touches D03 across the shared state line, and D01 and D03 do not touch.
The whole of both states is somebody's territory: per-state clipping tiles each square with that
square's own zips, which is the property the coverage test pins down.
"""
from __future__ import annotations

import importlib.util
import json
import math
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from td import geo, ziptable                                                # noqa: E402

SIDE = 200_000.0
TOUCHING = (("D01", "D02"), ("D02", "D03"))          # by construction, see the module docstring


def _geom_export():
    """tools/ is not a package (the route tests/test_ziptable.py uses)."""
    path = os.path.join(ROOT, "tools", "geom_export.py")
    spec = importlib.util.spec_from_file_location("geom_export_for_tests", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _basemap():
    """Two square states sharing the edge x = SIDE, as `geo.states_outline` would return them."""
    import geopandas as gpd
    from shapely import box
    return gpd.GeoDataFrame(
        {"STUSPS": ["AA", "BB"]},
        geometry=[box(0.0, 0.0, SIDE, SIDE), box(SIDE, 0.0, 2 * SIDE, SIDE)],
        crs=geo.LAEA)


def _table():
    """Twelve zip-table rows: three columns of four zips, two states, three districts."""
    rows = []
    for i, (x, state, district) in enumerate(((50_000.0, "AA", "D01"),
                                              (150_000.0, "AA", "D02"),
                                              (250_000.0, "BB", "D03"),
                                              (350_000.0, "BB", "D03"))):
        for j, y in enumerate((25_000.0, 75_000.0, 125_000.0)):
            rows.append(dict(zip=f"{10000 + 100 * i + j:05d}", state=state, x=x, y=y,
                             opportunity=1.0 + i, district=district, rep=""))
    rows.sort(key=lambda r: r["zip"])
    return rows


def _ring_area(rings) -> float:
    """Total shoelace area of a district's exterior rings.  The parts are disjoint and the
    export drops holes, so the sum is the district's own area."""
    total = 0.0
    for r in rings:
        s = sum(r[i][0] * r[i + 1][1] - r[i + 1][0] * r[i][1] for i in range(len(r) - 1))
        total += abs(s) / 2.0
    return total


# ------------------------------------------------------------------------------------ palette
def test_palette_is_fifty_distinct_colours():
    gx = _geom_export()
    p = gx.palette()
    assert len(p) == 50 and len(set(p)) == 50
    assert all(len(c) == 7 and c[0] == "#" and int(c[1:], 16) >= 0 for c in p)


# ------------------------------------------------------------------------------------- export
def test_export_carries_every_district_and_every_state():
    gx = _geom_export()
    g = gx.export(_table(), _basemap())

    assert g["crs"] == "laea"
    assert sorted(g["districts"]) == ["D01", "D02", "D03"]
    assert sorted(g["states"]) == ["AA", "BB"]
    for code, s in g["states"].items():
        x, y = s["label"]
        lo = 0.0 if code == "AA" else SIDE
        assert lo <= x <= lo + SIDE and 0.0 <= y <= SIDE     # inside its own square


def test_every_ring_closes_and_every_coordinate_is_finite():
    gx = _geom_export()
    g = gx.export(_table(), _basemap())
    parts = [d["rings"] for d in g["districts"].values()] + \
            [s["rings"] for s in g["states"].values()]
    assert parts and all(rings for rings in parts)
    for rings in parts:
        for r in rings:
            assert len(r) >= 4 and r[0] == r[-1]
            assert all(len(p) == 2 and math.isfinite(p[0]) and math.isfinite(p[1]) for p in r)


def test_touching_districts_never_share_a_colour():
    gx = _geom_export()
    colors = {d: v["color"] for d, v in gx.export(_table(), _basemap())["districts"].items()}
    for a, b in TOUCHING:
        assert colors[a] != colors[b], (a, b, colors[a])
    assert gx.export(_table(), _basemap())["districts"]["D02"]["color"] == colors["D02"]


def test_the_districts_cover_the_states():
    """Per-state clipped cells tile each state, so the three districts account for both squares."""
    gx = _geom_export()
    g = gx.export(_table(), _basemap(), simplify=0.0)
    got = sum(_ring_area(d["rings"]) for d in g["districts"].values())
    assert abs(got / (2 * SIDE * SIDE) - 1.0) < 1e-9, got
    assert abs(_ring_area(g["states"]["AA"]["rings"]) / (SIDE * SIDE) - 1.0) < 1e-9


def test_simplify_never_grows_the_export():
    gx = _geom_export()
    rows, states = _table(), _basemap()
    fine = gx.export(rows, states, simplify=0.0)
    coarse = gx.export(rows, states, simplify=20_000.0)
    def vertices(g):
        return sum(len(r) for d in g["districts"].values() for r in d["rings"])

    assert vertices(coarse) <= vertices(fine)
    assert sorted(coarse["districts"]) == sorted(fine["districts"])


# ---------------------------------------------------------------------------------------- cli
def test_cli_writes_geom_json_without_a_basemap():
    """`--no-basemap` clips to the padded hull of the points, the branch that needs no
    shapefile; the districts are still there, the states are not."""
    gx = _geom_export()
    with tempfile.TemporaryDirectory() as tmp:
        table = ziptable.write(os.path.join(tmp, "draw.csv"), _table())
        out = os.path.join(tmp, "run")
        assert gx.main(["--table", table, "--out", out, "--no-basemap"]) == 0

        assert os.path.exists(os.path.join(out, "timings.json"))

        with open(os.path.join(out, "geom.json"), encoding="utf-8") as fh:
            g = json.load(fh)
        assert g["crs"] == "laea" and g["states"] == {}
        assert sorted(g["districts"]) == ["D01", "D02", "D03"]
        for d in g["districts"].values():
            assert d["rings"] and d["color"].startswith("#")
            for r in d["rings"]:
                assert r[0] == r[-1]
