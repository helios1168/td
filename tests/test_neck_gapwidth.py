"""NeckGraph's gap_width flag (G1, owner 2026-10-08): a pair of ZCTAs across land in no ZCTA (the
land-only rows of `polygon["gaps"]`, else the Voronoi `dropped` rows, which can cross water and are
the width source the maps have been gated with since 2026-10-08) widens a passage, so a coverage gap
no longer reads as a neck; the pieces check never reads the Voronoi rows.  On by default since the owner's
2026-10-14 decision ("(a) Any water crossing ... except we should treat necks that are surrounded
by empty or zero-opportunity zips the same way we treat water", #131); `gap_width=False` and
`TD_NECK_GAP_WIDTH=0` are the opt-outs kept for comparison."""
from td import audit


def test_gap_width_turns_coverage_gap_neck_into_none():
    # A chain a-b-c of ZCTAs, 50 km borders, plus s reaching b through a 1 km polygon edge; s and c
    # are neighbours across a 30 km land gap (a land-only gap row) that no polygon edge spans.
    vs = ["a", "b", "c", "s"]
    edges = [("a", "b"), ("b", "c"), ("b", "s")]
    poly = {"vertices": vs, "edges": edges, "state": dict.fromkeys(vs, "TX"),
            "border": {("a", "b"): 50000.0, ("b", "c"): 50000.0, ("b", "s"): 1000.0},
            "connectors": [], "aland": dict.fromkeys(vs, 1e8),
            "gaps": {("c", "s"): 30000.0}}
    [nk] = audit.district_necks(set(vs), {}, audit.NeckGraph(poly, gap_width=False))
    assert nk.zips == ("s",) and nk.width_km == 1.0
    assert audit.district_necks(set(vs), {}, audit.NeckGraph(poly)) == []      # the default (R2)
    assert audit.district_necks(set(vs), {}, audit.NeckGraph(poly, gap_width=True)) == []
    # A gap pair across a state line adds nothing.
    poly["state"] = dict(poly["state"], s="NM")
    assert len(audit.district_necks(set(vs), {}, audit.NeckGraph(poly, gap_width=True))) == 1


def test_land_gap_widths_from_geo_are_used_when_present():
    # `polygon["gaps"]` is `geo.GAP_LAND`: land only, never across water (#131).
    vs = ["a", "b", "c", "s"]
    poly = {"vertices": vs, "edges": [("a", "b"), ("b", "c"), ("b", "s")], "state": dict.fromkeys(vs, "TX"),
            "border": {("a", "b"): 50000.0, ("b", "c"): 50000.0, ("b", "s"): 1000.0},
            "connectors": [], "aland": dict.fromkeys(vs, 1e8), "gaps": {("c", "s"): 30000.0}}
    assert audit.district_necks(set(vs), {}, audit.NeckGraph(poly, gap_width=True)) == []
    poly["gaps"] = {}       # empty: not consulted; the Voronoi fallback needs the reference files
    poly["voronoi_gaps"] = {}
    assert len(audit.district_necks(set(vs), {}, audit.NeckGraph(poly, gap_width=True))) == 1


def test_default_gate_voronoi_only_gap_passes_the_coverage_gap_neck():
    """The El Paso-style coverage gap: s hangs off b by a 1 km polygon edge and meets c across a 30 km
    gap that only the Voronoi `dropped` rows give (`polygon["gaps"]` is empty, as without
    `zcta_gap_land.csv.gz`).  The default gate (G1 on, owner 2026-10-08, #131: the status quo the owner
    accepted for widths, El Paso "a GREAT looking map") measures that width: no neck; G1 off keeps it."""
    vs = ["a", "b", "c", "s"]
    poly = {"vertices": vs, "edges": [("a", "b"), ("b", "c"), ("b", "s")], "state": dict.fromkeys(vs, "TX"),
            "border": {("a", "b"): 50000.0, ("b", "c"): 50000.0, ("b", "s"): 1000.0},
            "connectors": [], "aland": dict.fromkeys(vs, 1e8), "gaps": {}, "voronoi_gaps": {("c", "s"): 30000.0}}
    assert audit.district_necks(set(vs), {}, audit.NeckGraph(poly)) == []
    [nk] = audit.district_necks(set(vs), {}, audit.NeckGraph(poly, gap_width=False))
    assert nk.zips == ("s",) and nk.width_km == 1.0


def test_a_populated_neck_without_any_gap_row_still_fails():
    """No gap row of either kind: the neck through populated land (s, 1 km off b) fails with G1 on or
    off (owner, 2026-10-14: "Narrow land necks (Cincinnati, El Paso, Utah) would still fail")."""
    vs = ["a", "b", "c", "s"]
    poly = {"vertices": vs, "edges": [("a", "b"), ("b", "c"), ("b", "s")], "state": dict.fromkeys(vs, "TX"),
            "border": {("a", "b"): 50000.0, ("b", "c"): 50000.0, ("b", "s"): 1000.0},
            "connectors": [], "aland": dict.fromkeys(vs, 1e8), "gaps": {}, "voronoi_gaps": {}}
    for on in (True, False):
        [nk] = audit.district_necks(set(vs), {}, audit.NeckGraph(poly, gap_width=on))
        assert nk.zips == ("s",) and nk.width_km == 1.0


# ----------------------------------------------- check_m1's switch and score.m1_both (G3, 2026-10-13)
import importlib.util  # noqa: E402
import json  # noqa: E402
import os  # noqa: E402
import tempfile  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "looks_score", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools", "looks", "score.py"))
score = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(score)


def _gap_world() -> tuple:
    """(ledger, Geography): the toy above as one district X_01 of channel X, one fine channel f."""
    vs = ["a", "b", "c", "s"]
    poly = {"vertices": vs, "edges": [("a", "b"), ("b", "c"), ("b", "s")], "state": dict.fromkeys(vs, "TX"),
            "border": {("a", "b"): 50000.0, ("b", "c"): 50000.0, ("b", "s"): 1000.0},
            "connectors": [], "aland": dict.fromkeys(vs, 1e8), "gaps": {("c", "s"): 30000.0}}
    ledger = [{"zip_code": z, "current_channel": "f", "state": "TX", "model_channel": "X",
               "district": "X_01", "m_rel": "1.0"} for z in vs]
    return ledger, score.Geography(poly["state"], {}, {}, poly)


def test_check_m1_gap_width_argument_overrides_the_environment():
    ledger, g = _gap_world()
    old = os.environ.pop(audit.GAP_WIDTH_ENV, None)
    try:
        for env, arg, want in ((None, None, "pass"), ("1", None, "pass"), ("0", None, "fail"),
                               ("1", False, "fail"), (None, True, "pass"), ("0", True, "pass"),
                               (None, False, "fail")):
            if env is None:
                os.environ.pop(audit.GAP_WIDTH_ENV, None)
            else:
                os.environ[audit.GAP_WIDTH_ENV] = env
            m1 = score.m1_check(ledger, {"X": 1}, g, ["f"], gap_width=arg)
            assert (m1.status, m1.counts["gap_width"]) == (want, want == "pass"), (env, arg, m1.items)
            assert m1.counts["necks"] == (want == "fail")
    finally:
        os.environ.pop(audit.GAP_WIDTH_ENV, None)
        if old is not None:
            os.environ[audit.GAP_WIDTH_ENV] = old


def test_check_m1_default_gate_measures_the_neck_on_voronoi_rows_when_no_land_only_gap_file():
    """Without `zcta_gap_land.csv.gz` (`gaps` = {}) check_m1's width falls back on the Voronoi rows as
    since G1 (owner, 2026-10-08): the coverage-gap neck passes with G1 on, and R5 stays inactive
    (`gap_edges` 0: the Voronoi rows never join pieces)."""
    ledger, g = _gap_world()
    g.polygon["voronoi_gaps"] = g.polygon.pop("gaps")
    g.polygon["gaps"] = {}
    on = score.m1_check(ledger, {"X": 1}, g, ["f"], gap_width=True)
    assert on.status == "pass" and on.counts["necks"] == 0 and on.counts["gap_edges"] == 0, on.items
    off = score.m1_check(ledger, {"X": 1}, g, ["f"], gap_width=False)
    assert off.status == "fail" and off.counts["necks"] == 1, off.items


def test_m1_both_lists_the_flip_and_writes_m1_json():
    ledger, g = _gap_world()
    both = score.m1_both(ledger, {"X": 1}, g, ["f"])
    assert (both["strict"].status, both["gap_width"].status) == ("fail", "pass")
    [flip] = both["flips"]
    assert flip["district"] == "X/X_01" and flip["gap_width"] == []
    [item] = flip["strict"]
    assert item.startswith("X/X_01: neck 1.00 km wide cuts off 1 ZIPs (s...)"), item
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "m1.json")
        score.write_m1(path, both)
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
    assert (doc["strict"]["status"], doc["strict"]["gap_width"], doc["strict"]["necks"]) == ("fail", False, [item])
    assert (doc["gap_width"]["status"], doc["gap_width"]["gap_width"], doc["gap_width"]["necks"]) == ("pass", True, [])
    assert doc["flips"] == [flip]
    # no flip when both ways agree: s joined to b by a 20 km polygon edge is no neck either way
    _, g2 = _gap_world()
    g2.polygon["border"][("b", "s")] = 20000.0
    assert score.m1_both(ledger, {"X": 1}, g2, ["f"])["flips"] == []


def test_m1_both_compares_detached_piece_verdicts_too():
    """R5 (owner, 2026-10-14, #140): with the switch on, a district whose two parts a, b face each other
    only across land in no ZCTA (a land-only gap row) is one piece; strict it is in two.  That is a
    flip by a detached piece, not by a neck, and `m1_both` lists it with the piece as evidence and
    `write_m1` writes the pieces beside the necks (reviewer F3)."""
    vs = ["a", "b", "c"]
    poly = {"vertices": vs, "edges": [("a", "c"), ("b", "c")], "state": dict.fromkeys(vs, "TX"),
            "border": {("a", "c"): 20000.0, ("b", "c"): 20000.0}, "connectors": [],
            "aland": dict.fromkeys(vs, 1e8), "gaps": {("a", "b"): 30000.0}, "voronoi_gaps": {}}
    ledger = [{"zip_code": z, "current_channel": "f", "state": "TX", "model_channel": "X",
               "district": d, "m_rel": "1.0"} for z, d in (("a", "X_01"), ("b", "X_01"), ("c", "X_02"))]
    g = score.Geography(poly["state"], {}, {}, poly)
    both = score.m1_both(ledger, {"X": 2}, g, ["f"])
    assert (both["strict"].status, both["gap_width"].status) == ("fail", "pass")
    assert both["strict"].counts["pieces"] == 1 and both["gap_width"].counts["pieces"] == 0
    [flip] = both["flips"]
    assert flip["district"] == "X/X_01" and flip["gap_width"] == []
    [item] = flip["strict"]
    assert item.startswith("X/X_01: detached piece of 1 ZIPs"), item
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "m1.json")
        score.write_m1(path, both)
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
    assert doc["strict"]["necks"] == [] and doc["strict"]["pieces"] == [item]
    assert doc["gap_width"]["pieces"] == [] and doc["flips"] == [flip]
    # the same piece both ways (no gap row) is no flip
    quiet = dict(poly, gaps={})
    assert score.m1_both(ledger, {"X": 2}, score.Geography(poly["state"], {}, {}, quiet), ["f"])["flips"] == []
