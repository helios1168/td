"""tests/test_mandates.py -- the mandate register, docs/problem/MANDATES.md (#107).

The register fails the suite when a row lacks a field, a status is not `hard`, `deferred` or
`waived`, a deferred or waived row names no trigger test, a check names a file that does not
exist (unless an issue is building it), or a trigger holds (an expired deferral).

M1's named check must exist and must fail each committed broken fixture under
`tests/fixtures/m1/` (#108): a detached piece, a corner-only touch, a zero-opportunity ZCTA with no
owner, and an island joined only by a connector the owner has not approved; it passes the connected
one.  The fixture world is eleven 10 km squares (`zctas.csv`) whose graph `geo.polygon_edges`
builds, so the corner rule is the one the committed graph uses.

A trigger is a function `trigger_<name>()` in this module.  It returns the reason the mandate
must come back once its return condition holds, and None while it does not.  The 2026-09-01
deferral of contiguity, replayed against the 2026-09-28 ZIP graph (`reference/2025/`, #62),
must fail: its reason was 547 components among sold ZIPs, and that graph spans every CONUS ZCTA.
"""
from __future__ import annotations

import csv
import gzip
import importlib.util
import os
import re
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
REGISTER = os.path.join(ROOT, "docs", "problem", "MANDATES.md")
REFERENCE = os.path.join(ROOT, "reference", "2025")

FIELDS = ("status", "owner's words", "definition", "check", "latest value", "waiver history",
          "return trigger")
STATUSES = ("hard", "deferred", "waived")
FIELD_LINE = re.compile(r"^- \*\*(.+?):\*\*\s*(.*)$")
TRIGGER_REF = re.compile(r"tests/test_mandates\.py::(\w+)")
BUILT_BY = re.compile(r"built by #\d+")


def parse(text: str) -> dict[str, dict[str, str]]:
    """{mandate id: {field: value}}, one entry per `##` section.  The id is the heading up to its
    colon; a field is a `- **name:** value` line plus the indented lines under it."""
    rows: dict[str, dict[str, str]] = {}
    row = field = None
    for line in text.splitlines():
        if line.startswith("## "):
            mid = line[3:].split(":", 1)[0].strip()
            if mid in rows:
                raise ValueError(f"mandate {mid!r} appears twice")
            row = rows[mid] = {}
            field = None
            continue
        if row is None:
            continue
        m = FIELD_LINE.match(line)
        if m:
            field = m.group(1).strip().lower()
            row[field] = m.group(2).strip()
        elif field is not None and line.startswith((" ", "\t")) and line.strip():
            row[field] = (row[field] + " " + line.strip()).strip()
        elif not line.strip():
            continue
        else:
            field = None
    return rows


def _check_paths_exist(check: str) -> list[str]:
    """Each backticked path the check names, as `path` or `path::function`, that is missing."""
    missing = []
    for ref in re.findall(r"`([^`]+)`", check):
        path, _, func = ref.partition("::")
        full = os.path.join(ROOT, path)
        if not os.path.isfile(full):
            missing.append(ref)
        elif func:
            with open(full, encoding="utf-8") as fh:
                if not re.search(rf"^def {re.escape(func)}\(", fh.read(), re.M):
                    missing.append(ref)
    return missing


def problems(rows: dict[str, dict[str, str]], triggers=None) -> list[str]:
    """Every way the register fails; empty when it holds.  `triggers` maps a trigger name to its
    function, by default this module's `trigger_*` functions."""
    if triggers is None:
        triggers = {k: v for k, v in globals().items() if k.startswith("trigger_") and callable(v)}
    out = []
    for mid, row in rows.items():
        for f in FIELDS:
            if not row.get(f):
                out.append(f"{mid}: no {f!r}")
        status = row.get("status", "")
        if status and status not in STATUSES:
            out.append(f"{mid}: status {status!r} is not one of {STATUSES}")
        check = row.get("check", "")
        if check and not re.search(r"`[^`]+`", check):
            out.append(f"{mid}: the check names no file")
        elif check and not BUILT_BY.search(check):
            out += [f"{mid}: the check names {ref!r}, which does not exist"
                    for ref in _check_paths_exist(check)]
        if status in ("deferred", "waived"):
            names = TRIGGER_REF.findall(row.get("return trigger", ""))
            if not names:
                out.append(f"{mid}: {status} without a trigger test")
            for name in names:
                fn = triggers.get(name)
                if fn is None:
                    out.append(f"{mid}: trigger test {name!r} does not exist")
                    continue
                reason = fn()
                if reason:
                    out.append(f"{mid}: {status} has expired, {name} holds: {reason}")
    return out


# ------------------------------------------------------------------------------ triggers
def trigger_full_zcta_graph(ref_dir: str = REFERENCE):
    """The 2026-09-01 deferral's return condition, "the full-ZCTA-graph experiment": the committed
    ZIP graph has every CONUS ZCTA as a vertex, so the 547 components among sold ZIPs no longer
    describe it."""
    import networkx as nx
    from td import geo
    ref = geo.read_reference(ref_dir)
    if not len(ref) or (ref["graph_vertex"] != "1").any():
        return None
    edges = geo.read_reference(ref_dir, name="zcta_graph_edges.csv.gz")
    g = nx.Graph()
    g.add_nodes_from(ref["zcta"])
    g.add_edges_from(zip(edges["a"], edges["b"]))
    return (f"the ZIP graph in {os.path.relpath(ref_dir, ROOT)} spans all {len(ref)} CONUS "
            f"ZCTAs in {nx.number_connected_components(g)} components")


# ------------------------------------------------------------------------------ the register
def _register():
    with open(REGISTER, encoding="utf-8") as fh:
        return parse(fh.read())


def test_register_rows_are_complete_and_none_has_expired():
    rows = _register()
    assert rows, f"{REGISTER} has no rows"
    assert not problems(rows), problems(rows)


def test_register_keeps_m1_and_masking():
    rows = _register()
    assert {"M1", "Masking"} <= set(rows), sorted(rows)


def test_m1_keeps_the_owners_terms():
    """The owner's 2026-10-04 terms; a change to them is an owner decision and edits this test."""
    definition = _register()["M1"]["definition"]
    for term in ("2025 TIGER ZCTA polygons", "rook", "positive length", "corner does not count",
                 "connector list", "zero-opportunity ZIPs", "No tolerance", "same polygon graph"):
        assert term in definition, f"M1's definition lost {term!r}"


# ------------------------------------------------------------------------------ fixtures
ROW = """\
## X1: a fixture mandate

- **status:** {status}
- **owner's words:** owner, 2026-10-05, a fixture.
- **definition:** a fixture.
- **check:** `tests/test_mandates.py::test_register_keeps_m1_and_masking`
- **latest value:** not measured.
- **waiver history:** none.
- **return trigger:** {trigger}
"""


def _row(status="hard", trigger="none", drop=None):
    text = ROW.format(status=status, trigger=trigger)
    if drop:
        text = "\n".join(ln for ln in text.splitlines() if not ln.startswith(f"- **{drop}:**"))
    return parse(text)


def test_a_complete_hard_row_passes():
    assert problems(_row()) == []


def test_a_row_missing_any_field_fails():
    for f in FIELDS:
        found = problems(_row(drop=f))
        assert any(f"no {f!r}" in p for p in found), (f, found)


def test_a_status_outside_the_three_fails():
    for status in ("listed", "settled", "reported", "Hard"):
        assert any("is not one of" in p for p in problems(_row(status=status))), status


def test_a_deferred_or_waived_row_without_a_trigger_test_fails():
    for status in ("deferred", "waived"):
        for trigger in ("none", "when a full ZCTA graph exists",
                        "`tests/test_mandates.py::trigger_no_such_test`"):
            found = problems(_row(status, trigger))
            assert any("trigger test" in p for p in found), (status, trigger, found)


def test_a_deferral_whose_trigger_does_not_hold_passes_and_one_that_holds_fails():
    ref = "`tests/test_mandates.py::trigger_toy`"
    assert problems(_row("deferred", ref), {"trigger_toy": lambda: None}) == []
    found = problems(_row("waived", ref), {"trigger_toy": lambda: "the reason is gone"})
    assert any("has expired" in p for p in found), found


def test_a_check_that_names_a_missing_file_fails_unless_an_issue_builds_it():
    rows = _row()
    rows["X1"]["check"] = "`tools/mandates/no_such_check.py`"
    assert any("does not exist" in p for p in problems(rows))
    rows["X1"]["check"] = "`tools/mandates/no_such_check.py`, built by #108"
    assert problems(rows) == []
    rows["X1"]["check"] = "the audit"
    assert any("names no file" in p for p in problems(rows))


def test_the_2026_09_01_contiguity_deferral_replayed_on_the_2026_09_28_graph_fails():
    """The archived row (`archive/pre-support-2026-09:docs/problem/PROBLEM.md`), as a deferral
    with the trigger it should have had."""
    text = """\
## C0: adjacency contiguity

- **status:** deferred
- **owner's words:** "Adjacency contiguity is not required | settled | 2026-09-01 | user | 547
  components. Reopenable only by the full-ZCTA-graph experiment." (`d50bd42`)
- **definition:** every district is one connected piece on the ZIP graph.
- **check:** `td/audit.py`
- **latest value:** not measured.
- **waiver history:** 2026-09-01, set aside for simplicity.
- **return trigger:** `tests/test_mandates.py::trigger_full_zcta_graph`
"""
    found = problems(parse(text))
    assert len(found) == 1 and "C0: deferred has expired" in found[0], found
    assert "spans all 33300 CONUS ZCTAs" in found[0], found


def test_full_zcta_graph_trigger_does_not_hold_on_a_sold_zip_graph():
    """Before #62 the graph held sold ZIPs only: a ZCTA that is not a vertex keeps the deferral."""
    with tempfile.TemporaryDirectory() as tmp:
        with gzip.open(os.path.join(tmp, "zcta_reference.csv.gz"), "wt") as fh:
            fh.write("zcta,graph_vertex\n00001,1\n00002,0\n")
        assert trigger_full_zcta_graph(tmp) is None


# ------------------------------------------------------------------------------ M1's check (#108)
FIXTURES = os.path.join(ROOT, "tests", "fixtures", "m1")
BROKEN = ("detached_piece", "corner_only", "uncovered_zero_opportunity", "unapproved_crossing")


def _gate():
    spec = importlib.util.spec_from_file_location(
        "mandates_check", os.path.join(ROOT, "tools", "mandates", "check.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _world(gate, case: str):
    """(Geography, polygon_edges output) of the fixture world for `case`: the rook edges of its
    squares plus the case's approved connectors; its ZIP graph is the same rook graph."""
    import shapely
    from td import geo
    with open(os.path.join(FIXTURES, "zctas.csv"), newline="") as fh:
        rows = list(csv.DictReader(fh))
    ids, geoms = [r["zcta"] for r in rows], shapely.from_wkt([r["wkt"] for r in rows])
    got = geo.polygon_edges(ids, geoms)
    connectors = geo.read_connectors(path=os.path.join(FIXTURES, case, "connectors.csv"))
    state = {r["zcta"]: r["state"] for r in rows}
    edge = {z: {} for z in ids}
    for a, b, m in got["edges"]:
        edge[a][b] = edge[b][a] = m / 1000.0
    xy = {z: (g.centroid.x / 1000.0, g.centroid.y / 1000.0) for z, g in zip(ids, geoms)}
    polygon = {"vertices": ids, "state": state,
               "edges": [(a, b) for a, b, _ in got["edges"]] + geo.approved_connectors(connectors)}
    return gate.score.Geography(state, xy, edge, polygon), got


def test_m1_names_a_check_that_exists():
    check = _register()["M1"]["check"]
    assert not BUILT_BY.search(check), check
    for ref in ("td/audit.py::check_m1", "tools/mandates/check.py::m1"):
        assert f"`{ref}`" in check, (ref, check)
    assert _check_paths_exist(check) == [], check


def test_the_corner_fixture_touches_at_a_point_and_is_no_edge():
    _, got = _world(_gate(), "connected")
    pairs = {(a, b) for a, b, _ in got["edges"]}
    assert ("10006", "10007") in got["corner_only"] and ("10006", "10007") not in pairs
    assert ("10007", "10012") in pairs and ("10003", "10008") not in pairs


def test_m1_fails_each_broken_fixture_and_passes_the_connected_one():
    gate = _gate()
    got = {}
    for case in BROKEN + ("connected",):
        g, _ = _world(gate, case)
        got[case] = gate.m1(os.path.join(FIXTURES, case), g)
    assert got["connected"]["status"] == "pass", got["connected"]["check"].items
    assert all(got[c]["status"] == "fail" for c in BROKEN), {c: got[c]["summary"] for c in BROKEN}
    items = {c: got[c]["check"].items for c in got}
    counts = {c: got[c]["check"].counts for c in got}
    tau = "0.182 τ"                                     # 1 of 11 over K = 2
    assert items["detached_piece"] == [
        f"X/X_01: detached piece of 1 ZIPs (10007...), {tau}, cause cut off by other districts"]
    assert items["corner_only"] == [
        f"X/X_02: detached piece of 1 ZIPs (10007...), {tau}, cause cut off by other districts"]
    assert counts["uncovered_zero_opportunity"]["pieces"] == 0
    assert items["uncovered_zero_opportunity"] == ["X: 1 of 11 ZCTAs have no owner",
                                                    "X: 1 ZCTAs of MA have no owner"]
    assert items["unapproved_crossing"] == [
        f"X/X_02: detached piece of 1 ZIPs (10008...), {tau}, cause no approved connector"]
    # the scorer's largest piece is on the ledger (#116): the island is detached, the blank no piece
    assert got["unapproved_crossing"]["largest"] == ("X", "X_02", 1, 0.1818, "IS")
    assert got["uncovered_zero_opportunity"]["largest"] is None
