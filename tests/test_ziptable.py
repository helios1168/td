"""
test_ziptable.py -- the zip table (td/ziptable.py): build, write, read, and what reads it back.

No network and no instance file: the instance is a hand-built `td.instance.Descaled` over a few
fake CONUS zips, and the render smoke test passes `states=None`, the same no-basemap branch
`tests/test_geo.py` uses.  The gazetteer join is faked by handing `build` an `xy` dict directly,
which is exactly the shape `tools/run_draw.py`'s `coordinates` returns.
"""
from __future__ import annotations

import importlib.util
import math
import os
import sys
import tempfile

import networkx as nx
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from td import geo, ziptable                                                # noqa: E402
from td import instance as descaled                                         # noqa: E402


def _us_maps():
    """tools/ is not a package (the route tests/test_geo.py uses)."""
    path = os.path.join(ROOT, "tools", "us_maps.py")
    spec = importlib.util.spec_from_file_location("us_maps_for_ziptable", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _instance(masses, states):
    """A `Descaled` over `masses`' zips; a zip with an empty state carries no `state` attribute,
    the way `td.instance.load_descaled` leaves one the export had no state for."""
    G = nx.Graph()
    for z, m in masses.items():
        attrs = dict(cand=(), S={}, M=float(m), S_free=0.0)
        if states.get(z):
            attrs["state"] = states[z]
        G.add_node(z, **attrs)
    return descaled.Descaled(G=G)


def _toy():
    """Four zips: one with no gazetteer point, one with no state, and a two-district labelling."""
    masses = {"90210": 4.0, "10001": 6.0, "02139": 3.0, "00501": 7.0}
    states = {"90210": "CA", "10001": "NY", "02139": "MA", "00501": ""}
    xy = {"90210": (-1.0, 2.0), "10001": (3.0, 4.0), "02139": (5.5, -6.25)}   # 00501 has none
    labels = {"90210": "D01", "10001": "D02", "02139": "D02", "00501": "D01"}
    return _instance(masses, states), xy, labels


# ------------------------------------------------------------------------------- round trip
def test_build_write_read_round_trip():
    d, xy, labels = _toy()
    rows = ziptable.build(d, xy, labels)

    assert [r["zip"] for r in rows] == ["00501", "02139", "10001", "90210"]   # sorted, zero kept
    assert list(rows[0]) == list(ziptable.COLUMNS) + [ziptable.REP]
    assert all(r["rep"] == "" for r in rows)                                  # no reps given
    by_zip = {r["zip"]: r for r in rows}
    assert by_zip["00501"]["x"] is None and by_zip["00501"]["y"] is None      # no gazetteer point
    assert by_zip["00501"]["state"] == ""                                     # unknown state
    assert by_zip["02139"]["x"] == 5.5 and by_zip["02139"]["y"] == -6.25
    assert by_zip["10001"]["opportunity"] == 6.0

    with tempfile.TemporaryDirectory() as tmp:
        path = ziptable.write(os.path.join(tmp, "sub", "draw.csv"), rows)
        assert ziptable.read(path) == rows                    # exact, floats included

        with open(path, encoding="utf-8") as fh:
            header = fh.readline().strip()
            first = fh.readline().strip()
        assert header == "zip,state,x,y,opportunity,district"   # no rep: six columns
        assert first == "00501,,,,7.0,D01"                    # empties, not zeros


def test_rep_column_round_trips_and_is_optional():
    """`rep` is written only when some row carries one, and reads back as "" when absent."""
    d, xy, labels = _toy()
    rows = ziptable.build(d, xy, labels, reps={"90210": "R7", "00501": "R7"})
    with tempfile.TemporaryDirectory() as tmp:
        path = ziptable.write(os.path.join(tmp, "draw.csv"), rows)
        with open(path, encoding="utf-8") as fh:
            assert fh.readline().strip() == "zip,state,x,y,opportunity,district,rep"
        back = ziptable.read(path)
        assert back == rows
        assert {r["zip"]: r["rep"] for r in back} == {"00501": "R7", "02139": "",
                                                       "10001": "", "90210": "R7"}

        six = os.path.join(tmp, "six.csv")
        with open(six, "w", encoding="utf-8") as fh:
            fh.write("zip,state,x,y,opportunity,district\n01103,MA,1.0,2.0,3.0,D01\n")
        assert ziptable.read(six)[0]["rep"] == ""


def test_read_rejects_a_file_missing_a_column():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "draw.csv")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("zip,district\n01103,D01\n")
        try:
            ziptable.read(path)
        except ValueError as e:
            assert "state" in str(e)
        else:
            raise AssertionError("expected ValueError for a two-column draw")


def test_labels_agrees_with_us_maps_read_draw():
    """The whole point of keeping the table in `draw.csv`: every existing reader still works."""
    um = _us_maps()
    d, xy, labels = _toy()
    with tempfile.TemporaryDirectory() as tmp:
        path = ziptable.write(os.path.join(tmp, "draw.csv"), ziptable.build(d, xy, labels))
        assert ziptable.labels(ziptable.read(path)) == um.read_draw(path) == labels


def test_masses_are_the_instance_masses():
    d, xy, labels = _toy()
    got = ziptable.masses(ziptable.build(d, xy, labels))
    assert got == {"90210": 4.0, "10001": 6.0, "02139": 3.0, "00501": 7.0}


# ----------------------------------------------------------------------------------- balance
def test_balance_against_hand_computed_numbers():
    """D01 = 4 + 7 = 11, D02 = 6 + 3 = 9, total 20, tau = 10 at k = 2."""
    d, xy, labels = _toy()
    rep = ziptable.balance(ziptable.build(d, xy, labels), 2)

    assert rep["total"] == 20.0 and rep["target"] == 10.0 and rep["n_districts"] == 2
    assert abs(rep["spread_rel"] - 0.2) < 1e-12                    # (11 - 9) / 10
    assert abs(rep["max_dev_rel"] - 0.1) < 1e-12                   # |11/10 - 1|
    assert abs(rep["nash"] - (math.log(11.0) + math.log(9.0))) < 1e-12
    assert abs(rep["ceiling"] - 2.0 * math.log(10.0)) < 1e-12
    assert abs(rep["gap"] - (rep["ceiling"] - rep["nash"])) < 1e-12
    assert rep["gap"] > 0                                          # unequal, so below the ceiling


def test_balance_counts_a_missing_district_against_the_k_way_target():
    """Two districts' worth of mass split three ways is not balanced, however even the two are."""
    d, xy, _ = _toy()
    rows = ziptable.build(d, xy, {z: "D01" for z in ("90210", "00501")}
                          | {z: "D02" for z in ("10001", "02139")})
    rep = ziptable.balance(rows, 3)
    assert rep["n_districts"] == 2 and abs(rep["target"] - 20.0 / 3.0) < 1e-12
    assert rep["max_dev_rel"] > 0.3


def test_balance_needs_a_positive_k_and_a_labelled_row():
    d, xy, labels = _toy()
    rows = ziptable.build(d, xy, labels)
    for args in ((rows, 0), ([dict(r, district="") for r in rows], 2)):
        try:
            ziptable.balance(*args)
        except ValueError:
            pass
        else:
            raise AssertionError(f"expected ValueError for {args[1]}")


# ------------------------------------------------------------------------------------ render
def _clustered(per=8, k=2):
    """~16 fake CONUS zips in `k` separated clusters -- enough ground for a Voronoi fill."""
    rng = np.random.default_rng(5)
    mids = [(-120.0, 37.0), (-75.0, 41.0)][:k]
    codes = ["CA", "NY"][:k]
    masses, states, labels = {}, {}, {}
    lons, lats, zips = [], [], []
    for j, (lo, la) in enumerate(mids):
        for i in range(per):
            z = f"{10000 + 1000 * j + i:05d}"
            zips.append(z)
            lons.append(lo + float(rng.normal(0, 1.2)))
            lats.append(la + float(rng.normal(0, 1.2)))
            masses[z] = float(rng.uniform(0.5, 30.0))
            states[z] = codes[j]
            labels[z] = f"D{j + 1:02d}"
    x, y = geo.project(lons, lats)
    xy = {z: (float(a), float(b)) for z, a, b in zip(zips, x, y)}
    return _instance(masses, states), xy, labels


def test_render_writes_both_figures_without_a_basemap():
    """`states=None`, so no network and no geo cache: the clip falls back to the padded hull.
    A row with no coordinate must not break the draw -- it is skipped, not dropped."""
    d, xy, labels = _clustered()
    d.G.add_node("00501", cand=(), S={}, M=5.0, S_free=0.0, state="NY")   # no point for this one
    labels["00501"] = "D02"
    rows = ziptable.build(d, xy, labels)
    assert sum(1 for r in rows if r["x"] is None) == 1

    with tempfile.TemporaryDirectory() as tmp:
        written = ziptable.render(rows, tmp, None)
        assert [os.path.basename(p) for p in written] == ["districts.png",
                                                          "district_regions_voronoi.png"]
        for p in written:
            assert os.path.getsize(p) > 10_000, (p, os.path.getsize(p))


def test_render_rejects_an_unknown_figure_name():
    d, xy, labels = _clustered()
    try:
        ziptable.render(ziptable.build(d, xy, labels), ".", None, which=("power",))
    except ValueError as e:
        assert "power" in str(e)
    else:
        raise AssertionError("expected ValueError for an unknown figure name")
