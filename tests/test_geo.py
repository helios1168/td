"""
test_geo.py -- ZCTA coordinates, the LAEA projection, and the four map builders.

**No network.**  The gazetteer test pre-seeds the cache file `td.geo.zcta_points` looks for,
which is the same path a real download would have written, so the cache-if-absent branch is
what gets exercised; the figure tests pass `states=None`, which is why that argument exists.

The header quirk is pinned deliberately: the real 2020 gazetteer ships tab-delimited columns
with **trailing whitespace on the names**, so `INTPTLONG ` never matches `INTPTLONG` and a
reader that forgets to strip returns coordinates for nothing at all.
"""
from __future__ import annotations

import importlib.util
import os
import sys
import tempfile

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from td import geo                                                          # noqa: E402


def _us_maps():
    """tools/ is not a package (same route tests/test_instance.py uses for the exporter)."""
    path = os.path.join(ROOT, "tools", "us_maps.py")
    spec = importlib.util.spec_from_file_location("us_maps", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# trailing blanks on the header names are the file's own quirk, not a typo here
FAKE_GAZ = (
    "GEOID\tALAND\tAWATER\tALAND_SQMI\tAWATER_SQMI\tINTPTLAT\tINTPTLONG  \n"
    "01103\t1000\t0\t0.386\t0.000\t42.101000\t-72.590000\n"
    "90001\t2000\t0\t0.772\t0.000\t33.973900\t-118.249000\n"
    "10001\t3000\t0\t1.158\t0.000\t40.750600\t-73.997300\n"
    "99501\t4000\t0\t1.544\t0.000\t61.216800\t-149.877000\n"
)


def _seed_cache(dest):
    os.makedirs(dest, exist_ok=True)
    with open(os.path.join(dest, geo.GAZ_TXT), "w", encoding="latin-1") as fh:
        fh.write(FAKE_GAZ)


# ------------------------------------------------------------------ gazetteer parsing
def test_zcta_points_reads_cached_gazetteer():
    with tempfile.TemporaryDirectory() as tmp:
        _seed_cache(tmp)
        pts = geo.zcta_points(tmp)          # must not touch the network
    assert len(pts) == 4, pts
    assert set(pts) == {"01103", "90001", "10001", "99501"}
    lon, lat = pts["01103"]                 # keyed by the 5-char zip, leading zero intact
    assert abs(lon - (-72.59)) < 1e-9 and abs(lat - 42.101) < 1e-9
    assert abs(pts["90001"][0] - (-118.249)) < 1e-9


def test_zcta_points_survives_the_trailing_space_header():
    """A reader that matches raw header names would return no longitudes at all."""
    with tempfile.TemporaryDirectory() as tmp:
        _seed_cache(tmp)
        pts = geo.zcta_points(tmp)
    assert all(np.isfinite(v).all() for v in map(np.asarray, pts.values()))
    assert all(-180 < lon < 0 for lon, _ in pts.values())      # all US: western hemisphere


# ------------------------------------------------------------------ projection
def test_project_is_finite_and_orders_east_west():
    lons = [-122.4, -100.0, -74.0]         # same latitude: only longitude may move x
    lats = [40.0, 40.0, 40.0]
    x, y = geo.project(lons, lats)
    assert np.isfinite(x).all() and np.isfinite(y).all()
    assert x[0] < x[1] < x[2], x           # west of the central meridian stays to the left
    assert abs(x[1]) < 1e-6                # lon_0 = -100 maps to x = 0
    n, s = geo.project([-100.0, -100.0], [30.0, 45.0])[1]
    assert n < s                           # and northward is up


# ------------------------------------------------------------------ figure builders
def _synthetic(n=10):
    """~10 fake CONUS zips with coordinates, opportunity and two firms' books."""
    rng = np.random.default_rng(11)
    zips = [f"{10000 + 137 * i:05d}" for i in range(n)]
    lons = np.linspace(-121.0, -71.0, n)
    lats = np.linspace(33.0, 45.0, n)
    x, y = geo.project(lons, lats)
    xy = {z: (float(a), float(b)) for z, a, b in zip(zips, x, y)}
    M = {z: float(v) for z, v in zip(zips, rng.uniform(0.2, 40.0, n))}
    a = {z: M[z] * float(f) for z, f in zip(zips, rng.uniform(0.0, 0.2, n))}
    b = {z: M[z] * float(f) for z, f in zip(zips, rng.uniform(0.0, 0.2, n))}
    return zips, xy, M, a, b


def test_figure_builders_write_png_without_a_basemap():
    um = _us_maps()
    _, xy, M, a, b = _synthetic()
    with tempfile.TemporaryDirectory() as tmp:
        out = [
            um.figure_opportunity(M, xy, None, os.path.join(tmp, "opportunity.png")),
            um.figure_firm_book(a, xy, None, os.path.join(tmp, "firm_a.png"),
                                firm="F0", cmap="Oranges", side="A"),
            um.figure_firm_book(b, xy, None, os.path.join(tmp, "firm_b.png"),
                                firm="F1", cmap="Purples", side="B"),
            um.figure_contestability(a, b, xy, None, os.path.join(tmp, "contestability.png"),
                                     firm_a="F0", firm_b="F1"),
        ]
        assert [os.path.basename(p) for p in out] == [
            "opportunity.png", "firm_a.png", "firm_b.png", "contestability.png"]
        for p in out:
            assert os.path.exists(p), p
            assert os.path.getsize(p) > 10_000, (p, os.path.getsize(p))


def test_marker_area_is_linear_in_value():
    """Area, not radius: doubling the value must double `s`, which matplotlib reads as area."""
    um = _us_maps()
    v = np.array([1.0, 2.0, 4.0])
    s = um._sizes(v, vmax=4.0, max_marker=200.0, min_marker=0.0)
    assert np.allclose(s, [50.0, 100.0, 200.0])


def test_off_map_and_missing_zips_are_reported_not_raised():
    um = _us_maps()
    points = {"10001": (-73.99, 40.75), "99501": (-149.88, 61.22)}   # NY + Anchorage
    xy, missing, off_map = um.conus_xy(["10001", "99501", "00000"], points)
    assert set(xy) == {"10001"}
    assert missing == ["00000"] and off_map == ["99501"]
    n, share = um.drop_share({"10001": 3.0, "99501": 1.0}, xy)
    assert n == 1 and abs(share - 0.25) < 1e-12


# ------------------------------------------------------------------ the districts map
def _clustered(per=10, k=3):
    """~30 fake CONUS zips in `k` well-separated clusters, with a district label each."""
    rng = np.random.default_rng(5)
    mids = [(-120.0, 37.0), (-97.0, 31.0), (-75.0, 41.0)][:k]
    zips, lons, lats, labels = [], [], [], {}
    for j, (lo, la) in enumerate(mids):
        for i in range(per):
            z = f"{10000 + 1000 * j + i:05d}"
            zips.append(z)
            lons.append(lo + float(rng.normal(0, 1.2)))
            lats.append(la + float(rng.normal(0, 1.2)))
            labels[z] = f"D{j + 1:02d}"
    x, y = geo.project(lons, lats)
    xy = {z: (float(a), float(b)) for z, a, b in zip(zips, x, y)}
    M = {z: float(v) for z, v in zip(zips, rng.uniform(0.5, 30.0, len(zips)))}
    return zips, xy, M, labels


def test_figure_districts_writes_png_without_a_basemap():
    um = _us_maps()
    _, xy, M, labels = _clustered()
    with tempfile.TemporaryDirectory() as tmp:
        p = um.figure_districts(labels, M, xy, None, os.path.join(tmp, "districts.png"))
        assert os.path.basename(p) == "districts.png"
        assert os.path.getsize(p) > 10_000, os.path.getsize(p)


def test_district_centroids_are_M_weighted():
    """A heavy zip pulls the label to itself; an unweighted mean would sit in the middle."""
    um = _us_maps()
    xy = {"a": (0.0, 0.0), "b": (10.0, 0.0)}
    cx, _ = um.district_centroids({"a": "D01", "b": "D01"}, {"a": 9.0, "b": 1.0}, xy)["D01"]
    assert abs(cx - 1.0) < 1e-9, cx


def test_neighbor_coloring_is_valid_on_a_small_adjacency():
    """Only neighbour-distinctness is promised, and it must actually hold."""
    um = _us_maps()
    adj = {"D01": {"D02", "D03"}, "D02": {"D01", "D03"}, "D03": {"D01", "D02", "D04"},
           "D04": {"D03"}}
    colors = um.color_districts(adj)
    assert set(colors) == set(adj)
    for d, nbrs in adj.items():
        for e in nbrs:
            assert colors[d] != colors[e], (d, e, colors[d])
    # a 3-clique needs 3 hues, and the pendant may reuse one -- global uniqueness is not
    # promised, so assert the count is at most, not exactly, the vertex count
    assert 3 <= len(set(colors.values())) <= 4


def test_neighbor_coloring_survives_a_palette_shorter_than_the_clique():
    """The palette can run out; that must degrade to a duplicate, not raise."""
    um = _us_maps()
    adj = {a: {b for b in "abcd" if b != a} for a in "abcd"}     # K4, 2 colours available
    colors = um.color_districts(adj, palette=["#111111", "#222222"])
    assert set(colors) == set(adj)
    assert set(colors.values()) <= {"#111111", "#222222"}


def test_centroid_neighbors_is_symmetric_and_local():
    um = _us_maps()
    cent = {f"D{i:02d}": (float(i), 0.0) for i in range(1, 7)}   # a line of six
    adj = um.centroid_neighbors(cent, n_near=1)
    for d, nbrs in adj.items():
        for e in nbrs:
            assert d in adj[e], (d, e)                           # symmetrised
    assert adj["D01"] == {"D02"}                                 # nearest is the next along


def test_figure_districts_colors_neighbors_apart():
    """The colouring the figure would use, on the figure's own centroids."""
    um = _us_maps()
    _, xy, M, labels = _clustered()
    cent = um.district_centroids(labels, M, xy)
    adj = um.centroid_neighbors(cent, n_near=2)
    colors = um.color_districts(adj)
    for d, nbrs in adj.items():
        for e in nbrs:
            assert colors[d] != colors[e]


def test_read_draw_round_trips_a_draw_csv():
    um = _us_maps()
    with tempfile.TemporaryDirectory() as tmp:
        p = os.path.join(tmp, "draw.csv")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("zip,district\n01103,D01\n90001,D02\n")
        got = um.read_draw(p)
    assert got == {"01103": "D01", "90001": "D02"}        # leading zero survives


def test_zip_neighbors_sees_interleaving_the_centroids_miss():
    """Two scattered districts whose centroids coincide still come out as neighbours.

    Districts here are center-based, not contiguous, so a district's M-weighted centroid can
    sit where it holds nothing.  These two interleave point-by-point and their centroids land
    on top of each other, so the centroid graph is uninformative and the zip graph is not.
    """
    um = _us_maps()
    xy = {f"z{i:02d}": (float(i), 0.0) for i in range(10)}
    districts = {f"z{i:02d}": ("D01" if i % 2 == 0 else "D02") for i in range(10)}
    adj = um.zip_neighbors(districts, xy, n_near=2)
    assert adj["D01"] == {"D02"} and adj["D02"] == {"D01"}
    colors = um.color_districts(adj)
    assert colors["D01"] != colors["D02"]


def test_merge_adjacency_unions_and_symmetrises():
    um = _us_maps()
    merged = um.merge_adjacency({"a": {"b"}}, {"b": {"c"}, "c": set()})
    assert merged["a"] == {"b"} and merged["b"] == {"a", "c"} and merged["c"] == {"b"}


def test_color_districts_spreads_over_the_palette():
    """Least-used-first, not first-fit: an edgeless graph must not collapse onto one hue."""
    um = _us_maps()
    adj = {f"D{i:02d}": set() for i in range(1, 7)}
    assert len(set(um.color_districts(adj).values())) == 6


# ------------------------------------------------------------------ the district regions map
# `states=None` throughout, so nothing here touches the network or the geo cache: the clip
# polygon falls back to the padded convex hull of the points, which is the branch that exists
# for exactly this reason.
def _regions(um, xy, labels):
    """`(clip, cells, polys)` for a synthetic draw, on the no-basemap path."""
    keys = sorted(k for k in labels if k in xy)
    clip = um.clip_region([xy[k] for k in keys], None)
    cells = um.voronoi_cells(keys, xy, clip)
    return clip, cells, um.dissolve(cells, labels)


def test_clip_region_without_a_basemap_is_the_padded_hull():
    """No states: the cells still need a finite boundary, and it must contain every point."""
    um = _us_maps()
    from shapely import Point
    _, xy, _, _ = _clustered()
    pts = [xy[z] for z in xy]
    clip = um.clip_region(pts, None, pad=0.05)
    assert clip.geom_type in ("Polygon", "MultiPolygon") and clip.area > 0
    for p in pts:
        assert clip.covers(Point(p)), p
    from shapely import MultiPoint
    hull = MultiPoint([tuple(p) for p in pts]).convex_hull
    assert clip.area > hull.area                       # padded outwards, not merely the hull


def test_voronoi_cells_are_a_bijection_with_the_points():
    """One cell per point, no cell claimed twice -- an off-by-one here mislabels territory."""
    um = _us_maps()
    from shapely import Point
    _, xy, _, labels = _clustered()
    keys = sorted(labels)
    clip, cells, _ = _regions(um, xy, labels)
    assert set(cells) == set(keys), set(keys) ^ set(cells)          # onto, and no extras
    for z in keys:
        assert cells[z].covers(Point(xy[z])), z                     # each cell holds its point
    for z in keys:                                                  # and nobody else's
        for w in keys:
            if w != z:
                assert not cells[z].contains(Point(xy[w])), (z, w)
    for i, z in enumerate(keys):                                    # interiors are disjoint
        for w in keys[i + 1:]:
            assert cells[z].intersection(cells[w]).area < 1e-6 * cells[z].area, (z, w)
    covered = sum(cells[z].area for z in keys)
    assert abs(covered - clip.area) < 1e-6 * clip.area              # and they tile the clip


def test_cell_matching_recovers_a_shuffled_diagram():
    """The fallback for `ordered=True` being unavailable, exercised on purpose.

    Shapely 2.1 on GEOS >= 3.12 returns the cells in input order and `voronoi_cells` takes
    that fast path, so this branch would otherwise never run on this box -- and it is the
    branch that saves the figure on any older stack.
    """
    um = _us_maps()
    import shapely
    from shapely import MultiPoint
    coords = [(0.0, 0.0), (10.0, 1.0), (3.0, 9.0), (11.0, 8.0), (5.0, 4.0)]
    cells = list(shapely.voronoi_polygons(MultiPoint(coords), ordered=True).geoms)
    perm = [3, 0, 4, 2, 1]
    idx = um.match_cells_to_points([cells[j] for j in perm], coords)
    assert sorted(idx) == list(range(len(coords)))          # a permutation: bijection
    assert [perm[j] for j in idx] == list(range(len(coords)))   # and it undoes the shuffle


def test_dissolved_districts_have_area_and_do_not_overlap():
    """Every district is real ground, and no point of one district's cells is in another."""
    um = _us_maps()
    from shapely import Point
    _, xy, _, labels = _clustered()
    _, cells, polys = _regions(um, xy, labels)
    assert set(polys) == set(labels.values())
    for d, g in polys.items():
        assert g.area > 0, d
    for z in sorted(labels)[::4]:                       # a sample of generator points
        p = Point(xy[z])
        assert polys[labels[z]].covers(p), z
        for d, g in polys.items():
            if d != labels[z]:
                assert not g.covers(p), (z, d)          # strictly inside its own, only


def test_district_borders_are_the_shared_edges_not_the_outline():
    """Two districts split left/right: the border is the seam, not the frame."""
    um = _us_maps()
    from shapely import LineString
    xy = {f"z{i:02d}": (float(i), float(i % 3)) for i in range(12)}
    labels = {k: ("D01" if xy[k][0] < 5.5 else "D02") for k in xy}
    clip, _, polys = _regions(um, xy, labels)
    segs = um.district_borders(polys, eps=1e-9)
    assert segs, "two adjacent districts must share a border"
    total = sum(LineString(s).length for s in segs)
    assert 0 < total < clip.exterior.length             # a seam, not the whole outline
    for s in segs:                                      # and it lies on both boundaries
        line = LineString(s)
        assert polys["D01"].buffer(1e-6).covers(line)
        assert polys["D02"].buffer(1e-6).covers(line)


def test_label_points_stay_inside_their_own_region_and_apart():
    """Two districts sharing a metro must not print their labels on top of each other."""
    um = _us_maps()
    from shapely import Point
    _, xy, M, labels = _clustered()
    # force the pathology: D02's value all sits next to D01's, so the weighted centroids meet
    M = {z: (100.0 if z in ("10000", "11000") else 0.1) for z in labels}
    _, _, polys = _regions(um, xy, labels)
    cent = um.district_centroids(labels, M, xy)
    sep = 0.035 * (max(p.bounds[2] for p in polys.values())
                   - min(p.bounds[0] for p in polys.values()))
    pts = um.label_points(sorted(polys), polys, cent, sep)
    assert set(pts) == set(polys)
    for d, p in pts.items():
        assert polys[d].covers(Point(p)), d                    # inside its own region
    ids = sorted(pts)
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            assert Point(pts[a]).distance(Point(pts[b])) > 0.0, (a, b)


def test_label_points_do_not_flee_to_a_sliver():
    """A crowded label may move only within the district's substantial ground."""
    um = _us_maps()
    from shapely import Point, box
    big = box(0.0, 0.0, 10.0, 10.0)
    sliver = box(50.0, 50.0, 50.01, 50.01)               # 1e-6 of the district's area
    polys = {"D01": big.union(sliver), "D02": box(10.0, 0.0, 20.0, 10.0)}
    pts = um.label_points(["D01", "D02"], polys, {"D01": (5.0, 5.0), "D02": (15.0, 5.0)},
                          min_sep=1000.0)                # unsatisfiable: nothing is that far
    assert big.covers(Point(pts["D01"])), pts["D01"]     # stays on the real territory
    assert not sliver.covers(Point(pts["D01"]))


def test_figure_district_regions_writes_png_without_a_basemap():
    um = _us_maps()
    _, xy, M, labels = _clustered()
    with tempfile.TemporaryDirectory() as tmp:
        p = um.figure_district_regions(labels, M, xy, None,
                                       os.path.join(tmp, "district_regions.png"))
        assert os.path.basename(p) == "district_regions.png"
        assert os.path.getsize(p) > 10_000, os.path.getsize(p)


def test_both_district_figures_share_one_colour_assignment():
    """`draw_palette` is the single source of the hues, so the two maps cannot drift apart."""
    um = _us_maps()
    _, xy, M, labels = _clustered()
    order, cent, colors = um.draw_palette(labels, M, xy)
    assert order == sorted(set(labels.values()))
    assert set(colors) == set(order) and set(cent) == set(order)
    assert um.draw_palette(labels, M, xy)[2] == colors          # deterministic
    adj = um.merge_adjacency(um.centroid_neighbors(cent, 4), um.zip_neighbors(labels, xy, 6))
    for d, nbrs in adj.items():
        for e in nbrs:
            assert colors[d] != colors[e], (d, e)
