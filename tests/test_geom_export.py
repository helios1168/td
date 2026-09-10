"""
test_geom_export.py -- the polygon export (tools/geom_export.py) on a synthetic two-state map.

No network, no real shapefile and no instance: the basemap is a hand-built GeoDataFrame of two
square "states" in the same shape `td.geo.states_outline` returns (an `STUSPS` column and a
geometry column), and the table is twelve zips laid out on a grid across them.  The squares are
in metres so the export's rounding and its default simplify tolerance are exercised at the scale
the real LAEA map uses.  `zcta_polys` (the stand-in for `td.geo.zcta_polygons`) is likewise
hand-built: small offset squares around each zip's point, deliberately not the Voronoi
tessellation of the same points, so a test that checks `cells` came from `zcta_polys` and not
from the Voronoi diagram is actually exercising the swap rather than two shapes that happen to
coincide.

Layout, all coordinates in metres:

    AA = [0, 200k] x [0, 200k]          BB = [200k, 400k] x [0, 200k]
    D01 at x = 50k, D02 at x = 150k     D03 at x = 250k and x = 350k

so D01 touches D02, D02 touches D03 across the shared state line, and D01 and D03 do not touch.
The whole of both states is somebody's territory: per-state clipping tiles each square with that
square's own zips, which is the property the coverage test pins down.

`test_zcta_polygons_reads_the_real_hub_shapefile` is gated on `os.path.exists` of the hub's
local ZCTA520 file and prints a `SKIP` line rather than passing silently when it is absent, the
same convention `tests/test_borders_report.py` uses for the confidential instance.
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
CELL_HALF = 15_000.0                                 # zcta_polys fixture: half-side of each cell
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


def _zcta_polys(rows):
    """`{zip: box}`, a stand-in for `td.geo.zcta_polygons` in `LAEA`: a small square around
    each zip's own point, `CELL_HALF` metres on either side -- disjoint (the tightest column and
    row spacing in `_table` are 50k and 100k, both well over `2 * CELL_HALF`) and nowhere near
    the size of that zip's Voronoi cell, so a test that checks `cells`/`districts` came from
    this and not from the Voronoi tessellation is exercising a real swap."""
    from shapely import box
    return {r["zip"]: box(r["x"] - CELL_HALF, r["y"] - CELL_HALF,
                          r["x"] + CELL_HALF, r["y"] + CELL_HALF)
           for r in rows}


def _zigzag_box(cx, cy, half=CELL_HALF, n=20, amp=1000.0):
    """A `2*half`-wide square around `(cx, cy)`, its top edge replaced by an `n`-step zigzag of
    amplitude `amp` metres -- straight at `simplify=0`, but Douglas-Peucker at a tolerance above
    `amp` collapses it back to a flat edge, while a tolerance below `amp` leaves it alone.  Used
    to prove a coarse `simplify` genuinely drops vertices (a plain box cannot shed any: all four
    corners are load-bearing) and to pin `CELLS_SIMPLIFY` against the district `simplify`
    independently, by picking an `amp` between the two tolerances under test."""
    from shapely import Polygon
    x0, x1, y0, y1 = cx - half, cx + half, cy - half, cy + half
    top = [(x0 + (x1 - x0) * i / n, y1 + (amp if i % 2 == 0 else 0.0)) for i in range(n + 1)]
    return Polygon([(x0, y0), (x1, y0), *reversed(top), (x0, y0)])


def _seed_zcta_shp(dest, rows):
    """A `ZCTA5CE20` shapefile at `dest`, one small box per row's zip, in `EPSG:4269` degrees
    near (-100, 40) -- same convention `tests/test_geo.py`'s `_seed_states` uses for the state
    shapefile: plain small-scale fixture coordinates, not a real-world reprojection of `_table`'s
    LAEA metres (which `--zcta-shp` doesn't need to align with the drawn `x`/`y` at all, since
    the real cells are no longer clipped to anything -- decision 1)."""
    import geopandas as gpd
    from shapely import box
    codes = [r["zip"] for r in rows]
    geoms = [box(-100.0 + 0.01 * i, 40.0, -100.0 + 0.01 * i + 0.005, 40.005)
            for i in range(len(codes))]
    path = os.path.join(dest, "tl_2025_us_zcta520.shp")
    gpd.GeoDataFrame({"ZCTA5CE20": codes}, geometry=geoms, crs="EPSG:4269").to_file(path)
    return path


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
    rows = _table()
    g = gx.export(rows, _basemap(), _zcta_polys(rows), "test-fixture")

    assert g["crs"] == "laea"
    assert g["cells_source"] == "test-fixture"
    assert sorted(g["districts"]) == ["D01", "D02", "D03"]
    assert sorted(g["states"]) == ["AA", "BB"]
    for code, s in g["states"].items():
        x, y = s["label"]
        lo = 0.0 if code == "AA" else SIDE
        assert lo <= x <= lo + SIDE and 0.0 <= y <= SIDE     # inside its own square
    assert abs(_ring_area(g["states"]["AA"]["rings"]) / (SIDE * SIDE) - 1.0) < 1e-9


def test_every_ring_closes_and_every_coordinate_is_finite():
    gx = _geom_export()
    rows = _table()
    g = gx.export(rows, _basemap(), _zcta_polys(rows), "test-fixture")
    parts = [d["rings"] for d in g["districts"].values()] + \
            [s["rings"] for s in g["states"].values()] + \
            [c["rings"] for c in g["cells"].values()]
    assert parts and all(rings for rings in parts)
    for rings in parts:
        for r in rings:
            assert len(r) >= 4 and r[0] == r[-1]
            assert all(len(p) == 2 and math.isfinite(p[0]) and math.isfinite(p[1]) for p in r)


def test_touching_districts_never_share_a_colour():
    """Also the adjacency-source regression check for `_adjacency`: the fixture's `zcta_polys`
    squares never touch anything, not even another zip in the same district (`_zcta_polys`'s own
    docstring), so colouring off the real-ZCTA dissolve would see zero adjacent pairs and this
    would pass trivially with every district free to take the same colour.  It only pins down
    something real because colouring is computed off the Voronoi dissolve, which does tile."""
    gx = _geom_export()
    rows = _table()
    colors = {d: v["color"] for d, v in
             gx.export(rows, _basemap(), _zcta_polys(rows), "test-fixture")["districts"].items()}
    for a, b in TOUCHING:
        assert colors[a] != colors[b], (a, b, colors[a])
    got = gx.export(rows, _basemap(), _zcta_polys(rows), "test-fixture")["districts"]
    assert got["D02"]["color"] == colors["D02"]


def test_neighbours_sit_a_quarter_turn_apart_in_hue_when_the_palette_allows():
    """A path of four districts over the 50-entry palette: every neighbouring pair differs in
    hue by at least HUE_APART, so no two touching districts read as shades of one colour."""
    gx = _geom_export()
    adj = {"A": {"B"}, "B": {"A", "C"}, "C": {"B", "D"}, "D": {"C"}}
    colors = gx.color_distinct(adj, gx.palette())
    assert len(set(colors.values())) == 4
    for a, b in (("A", "B"), ("B", "C"), ("C", "D")):
        d = abs(gx._hue(colors[a]) - gx._hue(colors[b])) % 1.0
        assert min(d, 1.0 - d) >= gx.HUE_APART - 1e-9, (a, b, colors[a], colors[b])
    # a two-entry palette on a triangle: the third vertex must repeat, never raise
    tri = {"A": {"B", "C"}, "B": {"A", "C"}, "C": {"A", "B"}}
    two = gx.color_distinct(tri, gx.palette()[:2])
    assert len(set(two.values())) == 2


def test_a_districts_real_gap_lands_in_holes_not_in_rings():
    """A district whose own zips' real ZCTA union has a genuine interior gap (decision 1) must
    export that gap under `"holes"`, never folded into `"rings"` -- `rings` keeps meaning
    exactly what it means today so `app/mapfig.py`'s `staffed_figure` fill sites cannot regress.
    A hole-free district gets no `"holes"` key at all."""
    from shapely import Polygon, box
    gx = _geom_export()
    outer, inner = 15_000.0, 5_000.0
    donut = Polygon(shell=[(-outer, -outer), (outer, -outer), (outer, outer), (-outer, outer)],
                    holes=[[(-inner, -inner), (inner, -inner), (inner, inner), (-inner, inner)]])
    rows = [dict(zip="30000", state="AA", x=0.0, y=0.0, opportunity=1.0, district="H01", rep=""),
           dict(zip="30001", state="AA", x=500_000.0, y=0.0, opportunity=1.0, district="H02",
                rep="")]
    zctas = {"30000": donut,
            "30001": box(500_000.0 - outer, -outer, 500_000.0 + outer, outer)}
    g = gx.export(rows, None, zctas, "test-fixture", simplify=0.0)

    h01 = g["districts"]["H01"]
    assert "holes" in h01 and len(h01["holes"]) == 1
    hole_area = _ring_area(h01["holes"])
    assert abs(hole_area - (2 * inner) ** 2) < 1.0, hole_area
    hole_points = {tuple(p) for p in h01["holes"][0]}
    ring_points = {tuple(p) for ring in h01["rings"] for p in ring}
    assert not (hole_points & ring_points), "the hole leaked into rings"

    assert "holes" not in g["districts"]["H02"]


def test_districts_dissolve_their_zips_real_zcta_polygons():
    """Decision 1: a district's rings are the union of its own zips' real ZCTA polygons, not a
    tessellation.  The fixture squares are disjoint by construction, so the dissolved area must
    equal the plain sum of its zips' own square areas -- exactly the dissolve, nothing filled in
    and nothing clipped away."""
    gx = _geom_export()
    rows = _table()
    g = gx.export(rows, _basemap(), _zcta_polys(rows), "test-fixture", simplify=0.0)

    cell_area = (2 * CELL_HALF) ** 2
    counts: dict = {}
    for r in rows:
        counts[r["district"]] = counts.get(r["district"], 0) + 1
    for d, n in counts.items():
        got = _ring_area(g["districts"][d]["rings"])
        assert abs(got - n * cell_area) < 1.0, (d, got, n * cell_area)


def test_simplify_never_grows_the_export():
    """A plain box fixture cannot exercise this: all four corners of a rectangle are essential
    vertices, so Douglas-Peucker at any tolerance leaves them all in place and `coarse` would
    equal `fine` by construction regardless of whether simplification actually ran.  D01's own
    zip carries `_zigzag_box` instead: 21 extra points on its top edge that a 20 km tolerance
    (`amp=1000` well under it) collapses away, so `coarse` must come back with genuinely fewer
    vertices, not merely no more."""
    gx = _geom_export()
    rows = _table()
    zctas = _zcta_polys(rows)
    zctas[rows[0]["zip"]] = _zigzag_box(rows[0]["x"], rows[0]["y"])
    states = _basemap()
    fine = gx.export(rows, states, zctas, "test-fixture", simplify=0.0)
    coarse = gx.export(rows, states, zctas, "test-fixture", simplify=20_000.0)
    def vertices(g):
        return sum(len(r) for d in g["districts"].values() for r in d["rings"])

    assert vertices(coarse) < vertices(fine)
    assert sorted(coarse["districts"]) == sorted(fine["districts"])


def test_cells_come_from_the_zcta_source_not_the_voronoi_tessellation():
    """`cells` must be `zcta_polys` verbatim (simplified), not the per-state clipped Voronoi
    tessellation those zips used to draw before this change: each cell's area is the small fixed
    fixture-square area, an order of magnitude below what a Voronoi cell over the same twelve
    points would average, and every cell is present even though the squares do not tile
    either state (decision 1: real gaps are allowed)."""
    gx = _geom_export()
    rows = _table()
    g = gx.export(rows, _basemap(), _zcta_polys(rows), "test-fixture", simplify=0.0)

    assert set(g["cells"]) == {r["zip"] for r in rows}
    cell_area = (2 * CELL_HALF) ** 2
    voronoi_share = (2 * SIDE * SIDE) / len(rows)
    assert cell_area < voronoi_share / 3
    for z, c in g["cells"].items():
        got = _ring_area(c["rings"])
        assert abs(got - cell_area) < 1.0, (z, got)


def test_cells_use_cells_simplify_independently_of_the_district_tolerance():
    """Pins `CELLS_SIMPLIFY` (250 m) against the caller-chosen district `simplify` (here 2000 m)
    rather than just checking `cells_source` names a number: D01's zip is a `_zigzag_box` with
    1000 m amplitude, between the two tolerances, so the *same* underlying polygon must come
    back with its zigzag intact in `cells` (250 m cannot remove a 1000 m deviation) and flattened
    in `districts` (2000 m can) -- a `_rings(zcta_cells[z], simplify)` typo that used the
    district tolerance for cells too would flatten both and this would fail."""
    gx = _geom_export()
    rows = _table()
    zip0 = rows[0]["zip"]
    zctas = _zcta_polys(rows)
    zctas[zip0] = _zigzag_box(rows[0]["x"], rows[0]["y"])
    g = gx.export(rows, _basemap(), zctas, "test-fixture", simplify=2000.0)

    cell_vertices = len(g["cells"][zip0]["rings"][0])
    d01_parts = g["districts"]["D01"]["rings"]
    zigzag_part = max(d01_parts, key=len)     # D01 has 3 disjoint parts; this is the zigzag one

    assert cell_vertices > 10, cell_vertices          # 250 m: zigzag survives
    assert len(zigzag_part) <= 6, len(zigzag_part)     # 2000 m: zigzag collapses to a plain box


def test_district_reach_is_the_tessellation_dissolve_and_covers_the_zcta_union():
    """`district_reach` is the readable boundary: one region per district from the proximity
    tessellation, so it must be strictly larger than the union of that district's ZCTAs (which
    is a scatter of separate squares in this fixture) and made of fewer parts."""
    gx = _geom_export()
    rows = _table()
    g = gx.export(rows, _basemap(), _zcta_polys(rows), "test-fixture", simplify=0.0)

    assert set(g["district_reach"]) <= set(g["districts"])
    for d, reach in g["district_reach"].items():
        held = g["districts"][d]["rings"]
        assert _ring_area(reach["rings"]) > _ring_area(held), d      # reach covers the gaps too
        assert len(reach["rings"]) <= len(held), d                   # and in fewer parts
        assert reach["color"] == g["districts"][d]["color"], d       # one hue per district


def test_district_reach_carries_no_holes_because_it_is_stroked_not_filled():
    """A fill would claim ground the district does not hold, so this layer is exteriors only:
    it must never grow a `holes` key, whatever `districts` does."""
    gx = _geom_export()
    rows = _table()
    g = gx.export(rows, _basemap(), _zcta_polys(rows), "test-fixture", simplify=0.0)

    assert all("holes" not in info for info in g["district_reach"].values())


def test_proximity_edges_are_still_the_voronoi_rook_graph():
    """Decision 2: `proximity_edges` is unaffected by `cells` now coming from real ZCTA polygons --
    it is still the rook adjacency of the Voronoi cells of the same lattice as before this
    change (`docs/CODE_MAP.md`'s contiguity guard reads this graph, not real ZCTA adjacency).
    The twelve points are a regular 4-column x 3-row lattice (100k x 50k spacing) split into the
    two squares by per-state clipping, so the rook graph is 7 edges within AA, 7 within BB
    (3 horizontal + 4 vertical each), and 3 more where the two squares meet at x = SIDE -- 17 in
    all, no diagonals, exactly as it was when `cells` and `proximity_edges` shared a source."""
    gx = _geom_export()
    rows = _table()
    g = gx.export(rows, _basemap(), _zcta_polys(rows), "test-fixture", simplify=0.0)

    edges = g["proximity_edges"]
    assert len(edges) == 17
    assert edges == sorted(edges)
    assert all(a < b for a, b in edges)

    assert ["10000", "10101"] not in edges          # (x=50k,y=25k)-(x=150k,y=75k): diagonal
    assert ["10000", "10100"] in edges               # same row, adjacent columns
    assert ["10000", "10001"] in edges               # same column, adjacent rows
    assert ["10100", "10200"] in edges               # across the state line, x = SIDE


def test_proximity_zips_excludes_a_zip_whose_voronoi_cell_clips_to_nothing():
    """The latent solver bug this guards against: `tools/split_district.py` builds its
    contiguity graph's vertex set from zips that have a Voronoi cell, not from `cells` (which is
    real-ZCTA coverage now, a different set).  A zip whose point falls far outside every known
    state's land -- an outlier with an unrecognised state, the same as a coastline-clipped point
    -- still gets a real ZCTA `cells` entry (its zcta polygon does not depend on the Voronoi
    diagram at all) but must be **absent** from `proximity_zips`, exactly as it would have been
    silently absent from `cells` itself before this file used real ZCTA polygons."""
    gx = _geom_export()
    rows = _table()
    outlier = dict(zip="99999", state="ZZ", x=5_000_000.0, y=5_000_000.0,
                   opportunity=1.0, district="D03", rep="")
    rows = rows + [outlier]
    zctas = _zcta_polys(rows)
    g = gx.export(rows, _basemap(), zctas, "test-fixture", simplify=0.0)

    assert "99999" in g["cells"]
    assert "99999" not in g["proximity_zips"]
    assert set(g["proximity_zips"]) == {r["zip"] for r in rows if r["zip"] != "99999"}
    assert set(z for e in g["proximity_edges"] for z in e) <= set(g["proximity_zips"])


def test_export_raises_when_a_placed_zip_has_no_zcta_polygon():
    """No fallback to the Voronoi catchment for a missing ZCTA (decision 1): a clear error
    instead, naming the zip."""
    gx = _geom_export()
    rows = _table()
    zctas = _zcta_polys(rows)
    missing_zip = rows[0]["zip"]
    del zctas[missing_zip]
    try:
        gx.export(rows, _basemap(), zctas, "test-fixture")
        assert False, "expected a ValueError"
    except ValueError as e:
        assert missing_zip in str(e)


# ---------------------------------------------------------------------------------------- cli
def test_cli_writes_geom_json_without_a_basemap():
    """`--no-basemap` clips to the padded hull of the points, the branch that needs no state
    shapefile; the districts are still there, the states are not.  `--zcta-shp` points at a
    tiny seeded shapefile (`_seed_zcta_shp`), so this needs no network and no 822 MB download."""
    gx = _geom_export()
    with tempfile.TemporaryDirectory() as tmp:
        rows = _table()
        table = ziptable.write(os.path.join(tmp, "draw.csv"), rows)
        zcta_shp = _seed_zcta_shp(tmp, rows)
        out = os.path.join(tmp, "run")
        assert gx.main(["--table", table, "--out", out, "--no-basemap",
                       "--zcta-shp", zcta_shp]) == 0

        assert os.path.exists(os.path.join(out, "timings.json"))

        with open(os.path.join(out, "geom.json"), encoding="utf-8") as fh:
            g = json.load(fh)
        assert g["crs"] == "laea" and g["states"] == {}
        assert g["cells_source"] == f"{os.path.basename(zcta_shp)} simplify=250m"
        assert set(g["cells"]) == {r["zip"] for r in rows}
        assert sorted(g["districts"]) == ["D01", "D02", "D03"]
        for d in g["districts"].values():
            assert d["rings"] and d["color"].startswith("#")
            for r in d["rings"]:
                assert r[0] == r[-1]


# ------------------------------------------------------------------------------ geo.zcta_polygons
def test_zcta_polygons_raises_a_clear_error_when_the_file_is_absent():
    bogus = "/nonexistent/dir/tl_2025_us_zcta520.shp"
    try:
        geo.zcta_polygons(["01103"], bogus)
        assert False, "expected a FileNotFoundError"
    except FileNotFoundError as e:
        assert bogus in str(e)


def test_zcta_polygons_reads_a_seeded_shapefile_and_reprojects():
    """No network: a tiny seeded `ZCTA5CE20` shapefile, same convention as `_seed_zcta_shp`."""
    import geopandas as gpd
    from shapely import box
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "zcta.shp")
        gpd.GeoDataFrame({"ZCTA5CE20": ["01103", "90001"]},
                         geometry=[box(-73.0, 42.0, -72.0, 43.0), box(-119.0, 33.0, -118.0, 34.0)],
                         crs="EPSG:4269").to_file(path)
        polys = geo.zcta_polygons(["01103", "90001"], path)
    assert set(polys) == {"01103", "90001"}
    for g in polys.values():
        assert g.is_valid and g.area > 0
    assert "01103" != "90001" and polys["01103"].centroid.x != polys["90001"].centroid.x


def test_zcta_polygons_subsets_before_reprojecting_and_ignores_unrequested_codes():
    """A code present in the shapefile but not in `zips` must not come back -- proves the
    subset happens (fix for the "reprojects everything" cost bug), not just that a match works."""
    import geopandas as gpd
    from shapely import box
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "zcta.shp")
        gpd.GeoDataFrame({"ZCTA5CE20": ["01103", "90001", "10001"]},
                         geometry=[box(-73.0, 42.0, -72.0, 43.0), box(-119.0, 33.0, -118.0, 34.0),
                                  box(-74.0, 40.0, -73.0, 41.0)],
                         crs="EPSG:4269").to_file(path)
        polys = geo.zcta_polygons(["01103"], path)
    assert set(polys) == {"01103"}


def test_zcta_polygons_zero_pads_a_numeric_code_column():
    """A future vintage's numeric-typed `ZCTA5CE20` must still zero-pad, or "01001" silently
    becomes "1001" and every New England zip trips the caller's missing-zip `ValueError`."""
    import geopandas as gpd
    from shapely import box
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "zcta.shp")
        gpd.GeoDataFrame({"ZCTA5CE20": [1001]},          # int, not "01001"
                         geometry=[box(-73.0, 42.0, -72.0, 43.0)], crs="EPSG:4269").to_file(path)
        polys = geo.zcta_polygons(["01001"], path)
    assert set(polys) == {"01001"}


def test_zcta_polygons_reads_the_real_hub_shapefile():
    """Gated on the local 822 MB 2025 TIGER/Line ZCTA520 file: prints a `SKIP` line rather than
    passing silently when it is absent, the convention `tests/test_borders_report.py` uses for
    the confidential instance.  Verified facts (see the task brief): the k=10 live instance's
    3,704 placed zips are 100% covered -- "10001" is one of them.  Requests a handful of codes,
    not the whole 33,791-row file, exercising the subset-before-reproject path the loader now
    takes rather than the old read-everything one."""
    if not os.path.exists(geo.ZCTA_SHP):
        print(f"SKIP  test_zcta_polygons_reads_the_real_hub_shapefile  ({geo.ZCTA_SHP} absent)")
        return
    requested = ["10001", "90001", "60601", "00000"]     # "00000" is not a real ZCTA
    polys = geo.zcta_polygons(requested)
    assert set(polys) == {"10001", "90001", "60601"}
    assert polys["10001"].is_valid and polys["10001"].area > 0
