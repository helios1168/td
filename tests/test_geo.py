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
