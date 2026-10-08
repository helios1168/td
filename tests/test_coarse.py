"""tools/exp/contig/coarse.py: coarse units are connected and cover the state's graph vertices,
and the unit partition returns in-band connected groups."""
from __future__ import annotations

import importlib.util
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
HERE = os.path.join(ROOT, "tools", "exp", "contig")
sys.path.insert(0, HERE)
_spec = importlib.util.spec_from_file_location("coarse", os.path.join(HERE, "coarse.py"))
coarse = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(coarse)


def test_units_connected_and_cover_ny():
    from td import geo
    import run as contig
    ny = contig.induced_graph(geo.polygon_graph(), ("NY",))
    assert len(ny["vertices"]) == 1826
    # a district code that splits NY's graph: by first ZIP digit pair, so units must split it
    district = {z: z[:3] for z in ny["vertices"]}
    unit = coarse.assign_units(ny["vertices"], ny["edges"], district)
    assert set(unit) == set(ny["vertices"])
    adj = coarse.adjacency(ny["edges"])
    by = {}
    for z, u in unit.items():
        by.setdefault(u, []).append(z)
    for u, zs in by.items():
        assert len(coarse.components(zs, adj)) == 1, u
        assert len({district[z] for z in zs}) == 1, u


def test_toy_partition_in_band_connected():
    # ring a-b-c-d-e-f-a, mass 2 each; K 2 in [5, 7] means two arcs of three units, the
    # cheapest pair of opposite edges being a-b + d-e or b-c + e-f (2.0 km)
    units = list("abcdef")
    mass = dict(zip(units, [2, 2, 2, 2, 2, 2]))
    edges = {("a", "b"): 1.0, ("b", "c"): 1.0, ("c", "d"): 0.5, ("d", "e"): 1.0,
             ("e", "f"): 1.0, ("a", "f"): 3.0}
    g = {"units": units, "mass": {u: float(m) for u, m in mass.items()}, "edges": edges}
    out = coarse.partition(g, 2, 5.0, 7.0, time_limit=30, log=lambda *_: None)
    grp = out["group"]
    adj = coarse.adjacency(edges)
    for h in range(2):
        zs = [u for u in units if grp[u] == h]
        assert 5.0 <= sum(mass[u] for u in zs) <= 7.0
        assert len(coarse.components(zs, adj)) == 1
    assert abs(out["cut_km"] - 2.0) < 1e-9
