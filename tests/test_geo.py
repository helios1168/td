"""td.geo: the ZIP graph on toy geometry, the manifest rule, and the committed reference/2025/.

The reference tests read the committed build output only; nothing here downloads.  They are
#62's acceptance: every CONUS ZCTA has a state and a 2025 county, Connecticut resolves to its
planning regions, measured land matches the gazetteer within 0.5%, the manifest is all 2025, and
each state's ZIPs are one component on the ZIP graph or are listed in REPORT.json.
"""
from __future__ import annotations

import copy
import json
import os

from td import geo

REF = geo.REFERENCE_DIR


def _square(x0, y0, x1, y1):
    import shapely
    return shapely.box(x0, y0, x1, y1)


# ------------------------------------------------------------------------------ toy graph
def test_zip_graph_rook_edges_cross_state_and_skip_corner_touch():
    # states A and B side by side; C touches B only at a corner
    polys = {"A": _square(0, 0, 10, 10), "B": _square(10, 0, 20, 10),
             "C": _square(20, 10, 30, 20)}
    points = {"a1": (2, 5), "a2": (8, 5), "b1": (15, 5), "c1": (25, 15)}
    state = {"a1": "A", "a2": "A", "b1": "B", "c1": "C"}
    g = geo.zip_graph(points, state, polys)
    assert g["vertices"] == ["a1", "a2", "b1", "c1"]
    assert {(a, b) for a, b, *_ in g["edges"]} == {("a1", "a2"), ("a2", "b1")}
    assert all(k == "rook" and m > 0 for *_, k, m in g["edges"])
    assert g["missing"] == {}


def test_zip_graph_dc_va_override_is_the_only_manual_edge():
    polys = {"DC": _square(0, 0, 10, 10), "VA": _square(11, 0, 30, 10),
             "MD": _square(40, 0, 50, 10)}
    points = {"d1": (5, 5), "v1": (13, 5), "v2": (28, 5), "m1": (45, 5)}
    state = {"d1": "DC", "v1": "VA", "v2": "VA", "m1": "MD"}
    g = geo.zip_graph(points, state, polys)
    kinds = {(a, b): k for a, b, k, _ in g["edges"]}
    assert kinds == {("d1", "v1"): "override", ("v1", "v2"): "rook"}
    assert g["override"] == ["d1", "v1", "override"]
    polys["VA"] = _square(10, 0, 30, 10)           # now DC and VA share a border
    g = geo.zip_graph(points, state, polys)
    assert g["override"] == ["d1", "v1", "rook"]
    assert {k for *_, k, _ in g["edges"]} == {"rook"}


def test_zip_graph_reports_missing_zips_instead_of_isolated_vertices():
    # a2's point lies outside A, and its cell among A's points misses A entirely
    polys = {"A": _square(0, 0, 10, 10)}
    points = {"a1": (5, 5), "a2": (40, 5), "x1": (1, 1)}
    state = {"a1": "A", "a2": "A", "x1": "ZZ"}
    g = geo.zip_graph(points, state, polys)
    assert g["vertices"] == ["a1"]
    assert g["missing"] == {"a2": "cell clipped away", "x1": "no state polygon"}


def test_state_components_lists_only_disconnected_states():
    zip_state = {"a": "A", "b": "A", "c": "A", "d": "B", "e": "B"}
    edges = [("a", "b", "rook", 1.0), ("c", "d", "rook", 1.0), ("d", "e", "rook", 1.0)]
    assert geo.state_components(list(zip_state), edges, zip_state) == {"A": [2, 1]}


# ------------------------------------------------------------------------------ manifest
def _manifest():
    with open(os.path.join(REF, "MANIFEST.json")) as fh:
        return json.load(fh)


def test_committed_manifest_is_all_2025_and_complete():
    m = _manifest()
    geo.check_manifest(m)
    assert {e["name"] for e in m["sources"]} == set(geo.SOURCES)
    assert "hud" not in json.dumps(m).lower()


def test_manifest_rejects_any_source_that_is_not_2025():
    m = _manifest()
    for mutate in (
        lambda e: e.__setitem__("vintage", "2020"),
        lambda e: e.__setitem__("url", e["url"].replace("2025", "2020")),
        lambda e: e.__setitem__("sha256", "0" * 63),
    ):
        bad = copy.deepcopy(m)
        mutate(bad["sources"][0])
        try:
            geo.check_manifest(bad)
        except ValueError:
            continue
        raise AssertionError("check_manifest accepted a doctored source")
    bad = copy.deepcopy(m)
    multi = next(e for e in bad["sources"] if "files" in e)
    f = next(iter(multi["files"]))
    multi["files"][f.replace("2025", "2020")] = multi["files"].pop(f)
    try:
        geo.check_manifest(bad)
    except ValueError:
        pass
    else:
        raise AssertionError("check_manifest accepted a 2020 file name")
    bad = copy.deepcopy(m)
    bad["sources"] = [e for e in bad["sources"] if e["name"] != "faces"]
    try:
        geo.check_manifest(bad)
    except ValueError:
        pass
    else:
        raise AssertionError("check_manifest accepted a manifest missing a source")


def test_manifest_accepts_only_the_named_unavailable_files():
    m = _manifest()
    water = next(e for e in m["sources"] if e["name"] == "faces")
    assert water.get("unavailable", {}) == {f: r for f, r in geo.UNAVAILABLE.items()
                                            if "faces" in f}
    fallback = next(e for e in m["sources"] if e["name"] == "areawater")
    assert {f.replace("areawater", "faces") for f in fallback["files"]} == set(water["unavailable"])
    assert set(_report()["counties_without_faces"]) == {f.split("_")[2] for f in fallback["files"]}
    bad = copy.deepcopy(m)
    water = next(e for e in bad["sources"] if e["name"] == "faces")
    water.setdefault("unavailable", {})["tl_2025_01001_faces.zip"] = "gone"
    try:
        geo.check_manifest(bad)
    except ValueError:
        return
    raise AssertionError("check_manifest accepted an unavailable file not in geo.UNAVAILABLE")


# ------------------------------------------------------------------------------ reference/2025
def _report():
    with open(os.path.join(REF, "REPORT.json")) as fh:
        return json.load(fh)


def test_every_conus_zcta_has_a_state_and_a_2025_county():
    ref = geo.read_reference()
    rep = _report()
    assert len(ref) == rep["conus_zctas"] and rep["conus_zctas_without_county"] == []
    fips = {v: k for k, v in _state_fips().items()}
    assert set(ref["state"]) == set(fips) and len(fips) == 49
    assert all(len(c) == 5 and fips[s] == c[:2] for s, c in zip(ref["state"], ref["county"]))
    counties = set(geo.read_reference(name="areas.csv.gz").query("layer == 'county'")["geoid"])
    assert set(ref["county"]) <= counties


def _state_fips():
    ref = geo.read_reference()
    return {c[:2]: s for s, c in zip(ref["state"], ref["county"])}


def test_connecticut_resolves_to_its_planning_regions():
    ref = geo.read_reference()
    ct = set(ref.loc[ref["state"] == "CT", "county"])
    assert ct == {f"091{i}0" for i in range(1, 10)}, sorted(ct)
    ov = geo.read_reference(name="zcta_overlay.csv.gz")
    ct_pieces = ov[(ov["layer"] == "county") & ov["geoid"].str.startswith("09")]
    assert set(ct_pieces["geoid"]) <= {f"091{i}0" for i in range(1, 10)}


def test_overlay_land_matches_gazetteer_land_within_half_a_percent():
    ref = geo.read_reference()
    gaz = ref["aland_gaz"].astype(float)
    over = ref["aland_overlay"].astype(float)
    rel = (over - gaz).abs() / gaz
    worst = ref.assign(rel=rel).nlargest(5, "rel")[["zcta", "rel"]].values.tolist()
    assert (rel <= geo.LAND_TOLERANCE).all(), worst
    ov = geo.read_reference(name="zcta_overlay.csv.gz")
    cty = ov[ov["layer"] == "county"].assign(land=lambda d: d["land_m2"].astype(int))
    sums = cty.groupby("zcta")["land"].sum()
    assert (sums.reindex(ref["zcta"]).values == ref["aland_overlay"].astype(int).values).all()


def test_zip_graph_vertices_are_explicit_and_state_components_are_listed():
    import networkx as nx
    ref = geo.read_reference()
    rep = _report()["graph"]
    edges = geo.read_reference(name="zcta_graph_edges.csv.gz")
    vertices = set(ref.loc[ref["graph_vertex"] == "1", "zcta"])
    assert len(vertices) == rep["vertices"] and len(edges) == rep["edges"]
    assert set(edges["a"]) | set(edges["b"]) <= vertices
    assert vertices | set(rep["missing"]) == set(ref["zcta"])
    assert not vertices & set(rep["missing"])
    assert set(edges["kind"]) <= {"rook", "override"}
    a, b, kind = rep["override_pair"]
    assert ((edges["a"] == a) & (edges["b"] == b) & (edges["kind"] == kind)).sum() == 1
    assert set(ref.set_index("zcta").loc[[a, b], "state"]) == {"DC", "VA"}
    assert (edges.loc[edges["kind"] == "rook", "border_m"].astype(float) >= 0).all()
    zip_state = dict(zip(ref["zcta"], ref["state"]))
    g = nx.Graph()
    g.add_nodes_from(vertices)
    g.add_edges_from((a, b) for a, b in zip(edges["a"], edges["b"])
                     if zip_state[a] == zip_state[b])
    found = {}
    for comp in nx.connected_components(g):
        found.setdefault(zip_state[next(iter(comp))], []).append(len(comp))
    split = {s: sorted(c, reverse=True) for s, c in found.items() if len(c) > 1}
    assert split == rep["state_components"]


# ------------------------------------------------------------------------------ the polygon graph (M1)
def test_polygon_edges_need_a_shared_length_and_skip_a_corner_touch():
    polys = {"p": _square(0, 0, 10, 10), "q": _square(10, 0, 20, 10), "r": _square(20, 10, 30, 20),
             "s": _square(40, 0, 50, 10)}
    got = geo.polygon_edges(list(polys), list(polys.values()))
    assert got["edges"] == [("p", "q", 10.0)]
    assert got["corner_only"] == [("q", "r")] and got["overlaps"] == []
    assert geo.components(list(polys), got["edges"]) == [["p", "q"], ["r"], ["s"]]


def test_a_nested_zcta_is_adjacent_only_through_a_shared_boundary():
    """Rook (M1): a box inside another without a hole overlaps it but shares no boundary, so it
    is no edge and is reported as an overlap; with the inner box as the outer's hole they share
    its 24 m ring and are an edge."""
    import shapely
    outer, inner = _square(0, 0, 10, 10), _square(2, 2, 8, 8)
    got = geo.polygon_edges(["o", "i"], [outer, inner])
    assert got == {"edges": [], "corner_only": [], "overlaps": [("i", "o")]}
    holed = shapely.Polygon(outer.exterior.coords, [inner.exterior.coords])
    got = geo.polygon_edges(["o", "i"], [holed, inner])
    assert got == {"edges": [("i", "o", 24.0)], "corner_only": [], "overlaps": []}
    m = shapely.MultiPolygon([outer, _square(20, 0, 30, 10)])    # the same at part level
    # offered as a rook pair, so only the part-level predicate can reject it
    assert geo.part_edges(["m", "i"], [m, inner], [("i", "m", 0.0)], [])["edges"] == []
    m = shapely.MultiPolygon([holed, _square(20, 0, 30, 10)])
    assert geo.part_edges(["m", "i"], [m, inner], [("i", "m", 24.0)], [])["edges"] == [
        ("i", 0, "m", 0, "rook")]


def test_a_multipart_zcta_is_one_vertex_adjacent_through_any_part():
    """Owner, 2026-10-05: a ZCTA's parts count as connected to each other, and it meets another
    ZCTA through a shared positive-length boundary of any part."""
    import shapely
    m = shapely.MultiPolygon([_square(0, 0, 10, 10), _square(30, 0, 40, 10)])
    got = geo.polygon_edges(["m", "n", "o"], [m, _square(40, 0, 50, 10), _square(10, 10, 20, 20)])
    assert got["edges"] == [("m", "n", 10.0)] and got["corner_only"] == [("m", "o")]
    by_part = geo.part_edges(["m", "n", "o"], [m, _square(40, 0, 50, 10), _square(10, 10, 20, 20)],
                             got["edges"], [{"a": "m", "b": "o", "status": "proposed"}])
    assert [(z, k) for z, k, _ in by_part["parts"]] == [("m", 0), ("m", 1), ("n", 0), ("o", 0)]
    assert by_part["edges"] == [("m", 0, "o", 0, "connector"), ("m", 1, "n", 0, "rook")]


def _polygon_report():
    with open(os.path.join(REF, geo.POLYGON_REPORT)) as fh:
        return json.load(fh)


def test_committed_polygon_graph_is_over_the_shipped_vertices_with_its_manifest():
    rep = _polygon_report()
    ref = geo.read_reference()
    vertices = set(ref.loc[ref["graph_vertex"] == "1", "zcta"])
    edges = geo.read_reference(name=geo.POLYGON_EDGES)
    assert rep["vertices"] == len(vertices) and rep["no_polygon"] == [] and len(edges) == rep["edges"]
    assert set(edges["a"]) | set(edges["b"]) <= vertices and (edges["a"] < edges["b"]).all()
    assert (edges["border_m"].astype(float) > geo.MIN_BORDER_M).all()
    assert rep["min_border_m"] == geo.MIN_BORDER_M == 0.0 and rep["crs"] == geo.CRS
    assert rep["command"] == geo.POLYGON_COMMAND
    zcta = next(e for e in _manifest()["sources"] if e["name"] == "zcta")
    assert rep["sources"][0] == zcta
    for e in rep["sources"]:
        assert e["vintage"] == "2025" and all("2025" in f for f in e.get("files", {})), e["name"]
    assert rep["component_sizes"] == [len(c) for c in geo.components(
        sorted(vertices), list(zip(edges["a"], edges["b"])))]
    diff = geo.read_reference(name=geo.POLYGON_DIFF)
    voronoi = geo.read_reference(name="zcta_graph_edges.csv.gz")
    assert (diff["change"] == "added").sum() == rep["against_voronoi"]["added"]
    assert (diff["change"] == "dropped").sum() == rep["against_voronoi"]["dropped"]
    assert rep["against_voronoi"]["voronoi_edges"] == len(voronoi)


def test_connectors_name_their_crossing_and_the_graph_adds_only_approved_ones():
    rows = geo.read_connectors()
    ref = geo.read_reference()
    vertices = set(ref.loc[ref["graph_vertex"] == "1", "zcta"])
    # kind `nearest`: the owner joined four islands with no crossing to their nearest ZCTA
    # (owner, 2026-10-05, #108)
    assert geo.CONNECTOR_KINDS == ("bridge", "tunnel", "road", "ferry", "nearest")
    assert rows and all(r["crossing"] and r["kind"] in geo.CONNECTOR_KINDS
                        and {r["a"], r["b"]} <= vertices and r["a"] < r["b"] for r in rows)
    assert {r["status"] for r in rows} <= set(geo.CONNECTOR_STATUSES)
    g = geo.polygon_graph()
    approved = {(r["a"], r["b"]) for r in rows if r["status"] == "approved"}
    polygon = set(map(tuple, geo.read_reference(name=geo.POLYGON_EDGES)[["a", "b"]].values))
    assert set(g["edges"]) == polygon | approved
    held = [dict(r, status="proposed") if i == 0 else r for i, r in enumerate(rows)]
    assert set(geo.polygon_graph(connectors=held)["edges"]) == polygon | approved - {
        (rows[0]["a"], rows[0]["b"])}


def test_the_owners_connector_review_joins_every_island():
    """Owner, 2026-10-05 (#108): every row approved, each island with no crossing joined to its
    nearest ZCTA; the polygon graph plus the approved connectors is one component."""
    rows = geo.read_connectors()
    rep = _polygon_report()
    assert {r["status"] for r in rows} == {"approved"} and rep["connectors"]["approved"] == len(rows)
    nearest = {(r["a"], r["b"]) for r in rows if r["kind"] == "nearest"}
    assert nearest == {("43436", "43446"), ("98230", "98281"), ("98245", "98297"), ("98353", "98366")}
    assert all(r["source"] == "owner 2026-10-05 (#108): nearest ZCTA" for r in rows
               if r["kind"] == "nearest")
    assert rep["islands_without_a_connector"] == [] and rep["components_with_approved_connectors"] == 1
    assert all(i["joined_to_main_by_approved"] for i in rep["islands"])
    g = geo.polygon_graph()
    assert len(geo.components(g["vertices"], g["edges"])) == 1
