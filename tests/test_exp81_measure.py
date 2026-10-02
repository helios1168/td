"""tools/exp81/measure.py (td#81) on a toy channel with hand-computed values."""
from __future__ import annotations

import importlib.util
import math
import os
from types import SimpleNamespace

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "exp81_measure", os.path.join(HERE, "..", "tools", "exp81", "measure.py"))
measure = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(measure)


def _toy():
    """ZIPs a, b, c, d on a line 1 km apart; U1 = {a, b} and U2 = {c, d}, centroids 5 km apart.
    X_01 holds a (mass 1) and d (mass 0); X_02 holds b (1) and c (2).  e has no cell in X and
    links a to d."""
    centroid = {"U1": (0.0, 0.0), "U2": (3.0, 4.0)}
    inst = SimpleNamespace(
        channels={"X": SimpleNamespace(k=2, final_band=(0.8, 3.2),
                                       spec=SimpleNamespace(final_delta=0.6))},
        units=SimpleNamespace(unit_of={"a": "U1", "b": "U1", "c": "U2", "d": "U2", "e": "U2"},
                              distance_km=lambda u, v: math.dist(centroid[u], centroid[v])))
    rows = [{"zip_code": z, "model_channel": "X", "district": j, "m_rel": m}
            for z, j, m in (("a", "X_01", 1.0), ("d", "X_01", 0.0),
                            ("b", "X_02", 1.0), ("c", "X_02", 2.0))]
    xy = {z: (1000.0 * i, 0.0) for i, z in enumerate("abcd")}
    adj = {"a": {"b", "e"}, "b": {"a", "c"}, "c": {"b", "d"}, "d": {"c", "e"}, "e": {"a", "d"}}
    csv_rows = [{"channel": "X", "district": "X_01", "support": "U1", "drawn_mass": "1",
                 "pieces": "1"},
                {"channel": "X", "district": "X_02", "support": "U1+U2", "drawn_mass": "3",
                 "pieces": "0"}]
    return measure.measure_channel(inst, "X", rows, xy, adj, csv_rows)


def test_balance():
    m = _toy()
    assert m["tau_m_rel"] == 2.0
    assert m["within_final_band"] == 2
    assert m["worst_deviation"] == 0.5
    assert m["deviation_range"] == [-0.5, 0.5]


def test_support_diameter_counts_positive_mass_units_only():
    m = _toy()
    d = {r["district"]: r for r in m["district_rows"]}
    assert d["X_01"]["support"] == ["U1"]          # d holds no mass, so U2 is no contact
    assert d["X_02"]["support"] == ["U1", "U2"]
    assert m["support_diameter_drawn_km"] == 5.0
    assert m["support_diameter_planned_km"] == 5.0
    assert m["contacts"] == 3
    assert m["split_units"] == 1 and m["split"] == {"U1": ["X_01", "X_02"]}


def test_hess_score_and_extent():
    m = _toy()
    d = {r["district"]: r for r in m["district_rows"]}
    assert math.isclose(d["X_02"]["hess_m_rel_km2"], 2.0 / 3.0)
    assert math.isclose(d["X_02"]["rms_km"], math.sqrt(2.0 / 9.0))
    assert d["X_01"]["hess_m_rel_km2"] == 0.0
    assert math.isclose(m["hess_m_rel_km2"], 2.0 / 3.0)
    assert d["X_01"]["extent_km"] == 3.0          # zero-mass ZIPs count for the extent
    assert m["max_extent_km"] == 3.0


def test_pieces_and_connector_bridging():
    m = _toy()
    d = {r["district"]: r for r in m["district_rows"]}
    assert d["X_01"]["pieces"] == 1                # a and d are not adjacent
    assert d["X_01"]["pieces_bridged"] == 0        # e, with no cell in X, links them
    assert m["pieces"] == 1 and m["districts_in_pieces"] == 1
    assert m["cross_checks"] == []


def test_extent_collinear():
    pts = [(float(i), 2.0 * i) for i in range(6)]
    assert math.isclose(measure.extent_km(pts), math.hypot(5.0, 10.0))
    assert measure.extent_km([(1.0, 1.0)]) == 0.0
