"""NeckGraph's gap_width flag (G1 prototype, owner 2026-10-08): a Voronoi-adjacent pair across land
in no ZCTA widens a passage, so a coverage gap no longer reads as a neck."""
from td import audit


def test_gap_width_turns_coverage_gap_neck_into_none():
    # A chain a-b-c of ZCTAs, 50 km borders, plus s reaching b through a 1 km polygon edge; s and c
    # are Voronoi neighbours across a 30 km land gap that no polygon edge spans.
    vs = ["a", "b", "c", "s"]
    edges = [("a", "b"), ("b", "c"), ("b", "s")]
    poly = {"vertices": vs, "edges": edges, "state": dict.fromkeys(vs, "TX"),
            "border": {("a", "b"): 50000.0, ("b", "c"): 50000.0, ("b", "s"): 1000.0},
            "connectors": [], "aland": dict.fromkeys(vs, 1e8),
            "voronoi_gaps": {("c", "s"): 30000.0}}
    [nk] = audit.district_necks(set(vs), {}, audit.NeckGraph(poly))
    assert nk.zips == ("s",) and nk.width_km == 1.0
    assert audit.district_necks(set(vs), {}, audit.NeckGraph(poly, gap_width=True)) == []
    # A gap pair across a state line adds nothing.
    poly["state"] = dict(poly["state"], s="NM")
    assert len(audit.district_necks(set(vs), {}, audit.NeckGraph(poly, gap_width=True))) == 1
