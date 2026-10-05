"""The master on M1's polygon graph (#114): `td.spec.build` plans on `geo.polygon_graph()`, so the unit
graph, the support family and the drawability rows have an edge only for a shared boundary of
positive length or an approved connector; and the in-state connectors #114 proposes add no edge
until the owner approves them.

The toy world is 10 km squares in `geo.CRS` loaded through `geo.polygon_graph` from a temporary
reference directory.  The rest read only the committed `reference/2025/`.
"""
from __future__ import annotations

import os
import tempfile

import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString, box

from td import geo, spec, supports

from tests import test_spec as ts

KM = 1000.0
# AL: a1, a2 side by side; AR: r1 meets a2 at one corner only; AZ: z1 lies 5 km below a1 across
# water, reachable only by the connector a1-z1
SQUARES = {"a1": ("AL", box(0, 0, 10 * KM, 10 * KM)), "a2": ("AL", box(10 * KM, 0, 20 * KM, 10 * KM)),
           "r1": ("AR", box(20 * KM, 10 * KM, 30 * KM, 20 * KM)),
           "z1": ("AZ", box(0, -15 * KM, 10 * KM, -5 * KM))}
FERRY = {"a": "a1", "b": "z1", "kind": "ferry", "crossing": "a1-z1 ferry", "gap_km": 5.0,
         "source": "test"}


def _toy_world(status: str) -> tuple:
    """(reference frame, polygon graph) of `SQUARES` with the ferry a1-z1 at `status`, loaded by
    `geo.polygon_graph` from the files a polygon build writes."""
    ids = sorted(SQUARES)
    geoms = [SQUARES[z][1] for z in ids]
    got = geo.polygon_edges(ids, geoms)
    assert [(a, b) for a, b, _ in got["edges"]] == [("a1", "a2")]
    assert got["corner_only"] == [("a2", "r1")]
    ref = pd.DataFrame({"zcta": ids, "graph_vertex": "1", "state": [SQUARES[z][0] for z in ids],
                        "county": "", "cbsa": "",
                        "x": [str(g.centroid.x) for g in geoms], "y": [str(g.centroid.y) for g in geoms],
                        "aland_gaz": "1"})
    d = tempfile.mkdtemp(prefix="td-polygon-")
    ref.to_csv(os.path.join(d, "zcta_reference.csv.gz"), index=False)
    pd.DataFrame(got["edges"], columns=["a", "b", "border_m"]).to_csv(
        os.path.join(d, geo.POLYGON_EDGES), index=False)
    pd.DataFrame([dict(FERRY, status=status)], columns=list(geo.CONNECTOR_COLUMNS)).to_csv(
        os.path.join(d, geo.CONNECTORS), index=False)
    return geo.read_reference(d), geo.polygon_graph(d)


def _family(ref, graph) -> supports.Family:
    s = spec.parse(ts._toy_raw(max_dist_km=1e9))
    ext = ts.data.Extract(("f", "g"), sorted(SQUARES), ["f"] * len(SQUARES), [1.0] * len(SQUARES),
                          [{}] * len(SQUARES), [0.0] * len(SQUARES))
    return supports.family(spec.build(s, ext, ref, graph), "X")


def test_a_support_joined_only_by_a_corner_or_an_unapproved_crossing_is_not_in_the_family():
    ref, graph = _toy_world("proposed")
    fam = _family(ref, graph)
    assert set(fam.supports) == {frozenset(["AL"]), frozenset(["AR"]), frozenset(["AZ"])}
    assert frozenset(["AL", "AR"]) not in fam          # a2 and r1 share only a corner
    assert frozenset(["AL", "AZ"]) not in fam          # the ferry is not approved
    ref, graph = _toy_world("approved")
    fam = _family(ref, graph)
    assert frozenset(["AL", "AZ"]) in fam and frozenset(["AL", "AR"]) not in fam
    # a graph that counted the corner, as a Voronoi diagram may, would admit {AL, AR}
    corner = dict(graph, edges=graph["edges"] + [("a2", "r1")])
    assert frozenset(["AL", "AR"]) in _family(ref, corner)


def test_the_51_plans_on_the_committed_polygon_graph():
    """The default instance is on `geo.polygon_graph()`: its unit graph is that graph's, so the
    Voronoi graph's water contacts with no approved connector (NY-RI across Block Island Sound,
    IL-MI across Lake Michigan) and the Four Corners touch (AZ-CO) are no supports; the seven
    states the polygon graph does not connect within are reported, not stopped on."""
    s = spec.load(ts.S51)
    inst = spec.build(s, ts._all_conus(s), ts._reference())
    g = geo.polygon_graph()
    assert len(inst.units.unit_of) == len(g["vertices"]) == 33300
    pairs = {tuple(sorted((g["state"][a], g["state"][b]))) for a, b in g["edges"]
             if g["state"][a] != g["state"][b]}
    assert {tuple(sorted((u, v))) for u in inst.units.unit_adj for v in inst.units.unit_adj[u]} == pairs
    nat = supports.family(inst, "national")
    for pair in (("NY", "RI"), ("IL", "MI"), ("AZ", "CO")):
        assert pair not in pairs and frozenset(pair) not in nat, pair
    assert frozenset(["NY", "NJ"]) in nat
    assert sorted(inst.report["disconnected"]) == ["CA", "NV", "NY", "TN", "UT", "VA", "WY"]
    assert inst.report["disconnected_whole"] == ["NV", "TN", "UT", "WY"]


def test_the_proposed_in_state_connectors_add_no_edge_and_one_joins_each_detached_group():
    rows = [r for r in geo.read_connectors() if r["source"] == geo.STATE_PROPOSAL]
    g = geo.polygon_graph()
    groups = geo.state_groups(g["vertices"], g["edges"], g["state"])
    assert sorted(groups) == ["CA", "NV", "NY", "TN", "UT", "VA", "WY"]
    assert len(rows) == sum(len(c) - 1 for c in groups.values()) == 11
    assert {r["status"] for r in rows} == {"proposed"}
    assert not {(r["a"], r["b"]) for r in rows} & set(g["edges"])
    detached = {z: s for s, comps in groups.items() for c in comps[1:] for z in c}
    for r in rows:
        assert g["state"][r["a"]] == g["state"][r["b"]], r
        assert r["a"] in detached or r["b"] in detached, r
    approved = [dict(r, status="approved") if r["source"] == geo.STATE_PROPOSAL else r
                for r in geo.read_connectors()]
    assert set(geo.polygon_graph(connectors=approved)["edges"]) == set(g["edges"]) | {
        (r["a"], r["b"]) for r in rows}


def test_state_crossings_name_an_in_state_road_else_the_nearest_zcta_of_the_state():
    """State AL is a1 and a2, 10 km apart, a road across the land in no ZCTA between them, and
    a3, 30 km off with no road; b1, another state's ZCTA, is reached by a road from a1 too."""
    ids = ["a1", "a2", "a3", "b1"]
    geoms = [box(0, 0, 10 * KM, 10 * KM), box(20 * KM, 0, 30 * KM, 10 * KM),
             box(0, 40 * KM, 10 * KM, 50 * KM), box(0, -20 * KM, 10 * KM, -10 * KM)]
    roads = gpd.GeoDataFrame({"FULLNAME": ["Gap Rd", "South Rd"]}, crs=geo.CRS, geometry=[
        LineString([(5 * KM, 5 * KM), (25 * KM, 5 * KM)]),
        LineString([(5 * KM, 5 * KM), (5 * KM, -15 * KM)])])
    got = geo.state_crossings(ids, geoms, [["a1"], ["a2"], ["a3"]], roads)
    assert [(r["a"], r["b"], r["kind"], r["crossing"], r["gap_km"]) for r in got] == [
        ("a1", "a2", "road", "Gap Rd", 10.0),
        ("a1", "a3", "nearest", "a3 to a1: no road across land in no ZCTA within the state; "
                                "nearest ZCTA of the state", 30.0)]
    assert all(r["status"] == "proposed" and r["source"] == geo.STATE_PROPOSAL for r in got)
