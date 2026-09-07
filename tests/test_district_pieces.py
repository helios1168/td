"""tools/measure/district_pieces.py -- the largest-part share on three denominators.

The point of the module is that the three can disagree, and the tests plant the disagreement
rather than asserting on a real draw: a district made of a dense cluster of small catchments
plus one distant catchment big enough to rival the cluster's whole area reproduces D01's
shape, where the area share is near half and the mass share is near one.

No test here reads a gitignored input; every geometry is built in-process.
"""
import importlib.util
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


def _mod():
    """tools/ is not a package on the path; load the script the way run_all.py loads tests."""
    path = os.path.join(ROOT, "tools", "measure", "district_pieces.py")
    spec = importlib.util.spec_from_file_location("measure_district_pieces", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


dp = _mod()


def _box(x0, y0, x1, y1):
    from shapely.geometry import box
    return box(x0, y0, x1, y1)


def test_single_piece_is_one_on_every_denominator():
    """Two touching unit squares dissolve to one part, so all three shares are exactly 1."""
    cells = {"a": _box(0, 0, 1, 1), "b": _box(1, 0, 2, 1)}
    fr = dp.piece_fractions(cells, {"a": "D1", "b": "D1"}, {"a": 3.0, "b": 7.0})
    r = fr["D1"]
    assert r["n_parts"] == 1
    assert r["area"] == 1.0 and r["mass"] == 1.0 and r["zips"] == 1.0
    assert r["n_zips"] == 2
    assert abs(r["m_total"] - 10.0) < 1e-12


def test_area_and_mass_disagree_on_the_D01_shape():
    """A dense core plus one big empty outlier: area near half, mass near one."""
    cells = {f"c{i}": _box(i, 0, i + 1, 1) for i in range(4)}      # core, area 4
    cells["far"] = _box(100, 0, 102, 2)                            # outlier, area 4
    lab = {k: "D1" for k in cells}
    val = {f"c{i}": 100.0 for i in range(4)}
    val["far"] = 1.0
    r = dp.piece_fractions(cells, lab, val)["D1"]
    assert r["n_parts"] == 2
    assert abs(r["area"] - 0.5) < 1e-9                             # the misleading number
    assert abs(r["mass"] - 400.0 / 401.0) < 1e-9                   # the honest one
    assert abs(r["zips"] - 0.8) < 1e-9
    # parts come back largest-area first, and every part is accounted for
    assert abs(sum(a for a, _m, _n in r["parts"]) - 1.0) < 1e-9
    assert abs(sum(m for _a, m, _n in r["parts"]) - 1.0) < 1e-9
    assert sum(n for _a, _m, n in r["parts"]) == 5


def test_each_zip_is_charged_to_exactly_one_part():
    """Three disjoint clusters: the charge is a partition, so the counts sum to n_zips."""
    cells = {}
    for c, x in enumerate((0, 50, 200)):
        for i in range(3):
            cells[f"z{c}{i}"] = _box(x + i, 0, x + i + 1, 1)
    lab = {k: "D1" for k in cells}
    r = dp.piece_fractions(cells, lab, {k: 1.0 for k in cells})["D1"]
    assert r["n_parts"] == 3
    assert sum(n for _a, _m, n in r["parts"]) == r["n_zips"] == 9
    assert abs(r["mass"] - 1 / 3) < 1e-9 and abs(r["zips"] - 1 / 3) < 1e-9


def test_districts_are_kept_apart_and_unlabelled_zips_ignored():
    cells = {"a": _box(0, 0, 1, 1), "b": _box(1, 0, 2, 1), "c": _box(5, 0, 6, 1)}
    fr = dp.piece_fractions(cells, {"a": "D1", "b": "D2"}, {"a": 1.0, "b": 1.0, "c": 9.0})
    assert set(fr) == {"D1", "D2"}
    assert fr["D1"]["n_zips"] == fr["D2"]["n_zips"] == 1
    assert fr["D1"]["m_total"] == 1.0
