"""tests/test_mandates.py -- the mandate register, docs/problem/MANDATES.md (#107).

The register fails the suite when a row lacks a field, a status is not `hard`, `deferred` or
`waived`, a deferred or waived row names no trigger test, a check names a file that does not
exist (unless an issue is building it), or a trigger holds (an expired deferral).

M1's named check must exist and must fail each committed broken fixture under
`tests/fixtures/m1/` (#108): a detached piece, a corner-only touch, a zero-opportunity ZCTA with no
owner, and an island joined only by a connector the owner has not approved; it passes the connected
one.  The fixture world is eleven 10 km squares (`zctas.csv`) whose graph `geo.polygon_edges`
builds, so the corner rule is the one the committed graph uses.  The neck cases (#121) bring their
own worlds (`<case>/zctas.csv`): a part joined by a 5 km passage fails and the same shape at
10 km passes, a part under 5% on a 2 km passage passes, a ferry with no land alternative within
the district's states passes, a bridge whose sides land within the state joins fails, a dense
ZCTA of small area on a short border passes (M1 is by land area; it is listed as a mass neck),
and two parts under 5% each, on short borders on either side, do not combine into a neck.

A trigger is a function `trigger_<name>()` in this module.  It returns the reason the mandate
must come back once its return condition holds, and None while it does not.  The 2026-09-01
deferral of contiguity, replayed against the 2026-09-28 ZIP graph (`reference/2025/`, #62),
must fail: its reason was 547 components among sold ZIPs, and that graph spans every CONUS ZCTA.
"""
from __future__ import annotations

import contextlib
import csv
import gzip
import importlib.util
import json
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
                 "connector list", "zero-opportunity ZIPs", "No tolerance", "same polygon graph",
                 "narrower than 10 km", "one connected part of it holding at least 5% of its land",
                 "has width 0"):
        assert term in definition, f"M1's definition lost {term!r}"
    from td import audit           # the check's constants are the owner's (#121)
    assert (audit.NECK_W_KM, audit.NECK_SHARE) == (10.0, 0.05)


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
BROKEN = ("detached_piece", "corner_only", "uncovered_zero_opportunity", "unapproved_crossing",
          "neck_narrow", "connector_land_would_do")
PASSING = ("connected", "neck_wide", "neck_small_part", "connector_needed", "neck_dense_small_zcta",
           "neck_two_small_parts", "connector_land_too_narrow")


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
    own = os.path.join(FIXTURES, case, "zctas.csv")     # a neck case brings its own world
    with open(own if os.path.exists(own) else os.path.join(FIXTURES, "zctas.csv"), newline="") as fh:
        rows = list(csv.DictReader(fh))
    ids, geoms = [r["zcta"] for r in rows], shapely.from_wkt([r["wkt"] for r in rows])
    got = geo.polygon_edges(ids, geoms)
    connectors = geo.read_connectors(path=os.path.join(FIXTURES, case, "connectors.csv"))
    state = {r["zcta"]: r["state"] for r in rows}
    edge = {z: {} for z in ids}
    for a, b, m in got["edges"]:
        edge[a][b] = edge[b][a] = m / 1000.0
    xy = {z: (g.centroid.x / 1000.0, g.centroid.y / 1000.0) for z, g in zip(ids, geoms)}
    approved = geo.approved_connectors(connectors)
    polygon = {"vertices": ids, "state": state,
               "edges": [(a, b) for a, b, _ in got["edges"]] + approved,
               "border": {(a, b): m for a, b, m in got["edges"]}, "connectors": approved,
               "aland": {z: g.area for z, g in zip(ids, geoms)}}
    return gate.score.Geography(state, xy, edge, polygon), got


def test_m1_names_a_check_that_exists():
    check = _register()["M1"]["check"]
    assert not BUILT_BY.search(check), check
    for ref in ("td/audit.py::check_m1", "tools/mandates/check.py::m1"):
        assert f"`{ref}`" in check, (ref, check)
    assert _check_paths_exist(check) == [], check


def test_the_gate_prints_diagnostic_and_fails_a_diagnostic_folder():
    """Sol's review of #121 (P1): M1's gate CLI prints DIAGNOSTIC for a diagnostic folder and
    exits 1, though its M1 passes; the same folder unmarked exits 0."""
    import contextlib
    import io
    import shutil
    gate = _gate()
    g, _ = _world(gate, "connected")
    check = gate.m1
    gate.m1 = lambda d, _g=None: check(d, g)
    try:
        with tempfile.TemporaryDirectory() as tmp:
            d = os.path.join(tmp, "run")
            shutil.copytree(os.path.join(FIXTURES, "connected"), d)
            for diag, code in ((None, 0), ({"diagnostic": True, "diagnostic_band": 0.15,
                                            "diagnostic_label": "backfilled"}, 1)):
                if diag:
                    with open(os.path.join(d, "run.json"), "w") as fh:
                        json.dump(diag, fh)
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    got = gate.main([d])
                assert got == code and ("DIAGNOSTIC (backfilled)" in out.getvalue()) == bool(diag), out.getvalue()
                assert "M1 pass" in out.getvalue(), out.getvalue()
    finally:
        gate.m1 = check


def test_the_corner_fixture_touches_at_a_point_and_is_no_edge():
    _, got = _world(_gate(), "connected")
    pairs = {(a, b) for a, b, _ in got["edges"]}
    assert ("10006", "10007") in got["corner_only"] and ("10006", "10007") not in pairs
    assert ("10007", "10012") in pairs and ("10003", "10008") not in pairs


def test_m1_fails_each_broken_fixture_and_passes_the_connected_one():
    gate = _gate()
    got = {}
    for case in BROKEN + PASSING:
        g, _ = _world(gate, case)
        got[case] = gate.m1(os.path.join(FIXTURES, case), g)
    assert all(got[c]["status"] == "pass" for c in PASSING), {c: got[c]["check"].items for c in PASSING}
    assert all(got[c]["status"] == "fail" for c in BROKEN), {c: got[c]["summary"] for c in BROKEN}
    from td import audit
    items = {c: [i for i in got[c]["check"].items if audit.MASS_NECK not in i] for c in got}
    listed = {c: [i for i in got[c]["check"].items if audit.MASS_NECK in i] for c in got}
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
    # necks (owner, 2026-10-05, #121): a 5 km passage fails, a 10 km one passes, and a connector
    # whose sides land would join within the district's states is a passage 0 km wide
    assert items["neck_narrow"] == [
        "X/X_01: neck 5.00 km wide cuts off 1 ZIPs (10003...), 46.2% of its land area and 33.3% of "
        "its mass; cut 10002-10003 5.00 km"]
    assert items["connector_land_would_do"] == [
        "X/X_01: neck 0.00 km wide cuts off 1 ZIPs (10001...), 50.0% of its land area and 50.0% of "
        "its mass; cut 10001-10003 0.00 km"]       # two equal halves: either is the part cut off
    assert all(counts[c]["necks"] == 0 for c in PASSING)
    # land must be a real passage (owner, 2026-10-05, #121): the same bridge beside a land strip
    # 5 km wide keeps its full width
    assert items["connector_land_too_narrow"] == []
    # by land area only (owner, 2026-10-05, "Area only"): a dense ZCTA of 1 km² on a 1 km border
    # passes M1 and is listed beside it as a mass neck; two parts under 5% do not combine
    assert counts["neck_dense_small_zcta"]["mass_necks"] == 1
    assert items["neck_dense_small_zcta"] == [] and listed["neck_dense_small_zcta"] == [
        "X/X_01: mass neck (diagnostic, not M1) 1.00 km wide cuts off 1 ZIPs (10001...), 99.8% of "
        "its land area and 9.1% of its mass; cut 10001-10002 1.00 km"]
    assert items["neck_two_small_parts"] == [] and listed["neck_two_small_parts"] == []


# ------------------------------------------------------------------------------ T1, tracking (#120)
def test_t1_names_the_tracking_check():
    check = _register()["T1"]["check"]
    assert not BUILT_BY.search(check), check
    assert "`tools/mandates/check.py::tracking`" in check, check
    assert _check_paths_exist(check) == [], check


@contextlib.contextmanager
def _tracked_world(gate):
    """(tmp, base, registry): `base/runs/exp/lane/good` a complete run folder (ledger, manifest, a
    current `render.json` written as `tools/maps/render.py` writes it) and a registry naming it.
    The renderer's `$TD_REPO` inputs (`render.INPUTS`) point into `base` while it is open."""
    import hashlib
    render = gate._load("maps_render", "tools", "maps", "render.py")
    saved = render.TD_REPO
    with tempfile.TemporaryDirectory() as tmp:
        base = os.path.join(tmp, "td")
        render.TD_REPO = base
        try:
            run = os.path.join(base, "runs", "exp", "lane", "good")
            os.makedirs(run)
            files = {"ledger.csv": "zip_code\n", "districts.csv": "channel,district\n", "run.json": "{}",
                     "manifest.json": "{}", "summary.png": "png", "zip_pages.pdf": "pdf"}
            for name, text in files.items():
                with open(os.path.join(run, name), "w") as fh:
                    fh.write(text)
            for name in render.INPUTS:
                path = render.input_path(run, name)
                if name.startswith("$TD_REPO/"):
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    with open(path, "w") as fh:
                        fh.write(name)
            fac = os.path.join(tmp, "tables.json")
            with open(fac, "w") as fh:
                fh.write('{"fac": {}}')
            sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()   # noqa: E731
            entry = {"id": "good", "tier": 1, "rank": 1, "label": "a layout (K 2)", "run": "runs/exp/lane/good",
                     "images": ["runs/exp/lane/good/summary.png", "runs/exp/lane/good/zip_pages.pdf"], "notes": ""}
            with open(os.path.join(run, "render.json"), "w") as fh:
                json.dump({"renderer": {"code_sha256": render.code_sha256()}, "label": "good: a layout (K 2)",
                           "corridor": False, "m1": {"status": "pass"}, "fac": {"path": fac, "sha256": sha(fac)},
                           "inputs": {n: sha(render.input_path(run, n)) for n in render.INPUTS},
                           "images": {n: sha(os.path.join(run, n)) for n in ("summary.png", "zip_pages.pdf")}}, fh)
            registry = os.path.join(tmp, "shortlist.json")
            with open(registry, "w") as fh:
                json.dump({"tiers": {"1": "presentable", "3": "reference"}, "maps": [entry]}, fh)
            yield tmp, base, registry
        finally:
            render.TD_REPO = saved


def _rewrite(registry: str, edit) -> None:
    with open(registry) as fh:
        cfg = json.load(fh)
    edit(cfg)
    with open(registry, "w") as fh:
        json.dump(cfg, fh)


def test_tracking_passes_a_complete_world_and_fails_each_gap():
    """Mandate T1's check (#120): a complete run folder and shortlist pass; a run folder with a
    ledger and no manifest fails, as do an entry with no manifest, a missing image, an image
    outside its run folder, no or a stale `render.json`, a recorded M1 the gate no longer gives,
    and an id used twice across tiers."""
    import shutil
    gate = _gate()
    passing = lambda d: "pass"      # noqa: E731  -- the fixture ledgers are not maps
    with _tracked_world(gate) as (tmp, base, registry):
        assert gate.tracking(base, registry, passing) == []
        run = os.path.join(base, "runs", "exp", "lane", "good")

        bare = os.path.join(base, "runs", "exp", "lane", "group", "bare")
        os.makedirs(bare)
        open(os.path.join(bare, "ledger.csv"), "w").close()
        got = gate.tracking(base, registry, passing)
        assert got == ["run folder with a ledger and no manifest.json: runs/exp/lane/group/bare"], got
        shutil.rmtree(bare)

        assert any("render records M1 pass, the gate now says fail" in f
                   for f in gate.tracking(base, registry, lambda d: "fail"))

        os.rename(os.path.join(run, "manifest.json"), os.path.join(tmp, "m"))
        assert any("no manifest.json" in f for f in gate.tracking(base, registry, passing))
        os.rename(os.path.join(tmp, "m"), os.path.join(run, "manifest.json"))

        with open(os.path.join(run, "ledger.csv"), "a") as fh:
            fh.write("00501\n")
        assert any("render not current: ledger.csv changed" in f
                   for f in gate.tracking(base, registry, passing))

    with _tracked_world(gate) as (tmp, base, registry):
        run = os.path.join(base, "runs", "exp", "lane", "good")
        os.remove(os.path.join(run, "zip_pages.pdf"))
        assert any("image runs/exp/lane/good/zip_pages.pdf missing" in f
                   for f in gate.tracking(base, registry, passing))

    with _tracked_world(gate) as (tmp, base, registry):
        with open(os.path.join(base, "elsewhere.png"), "w") as fh:
            fh.write("png")
        _rewrite(registry, lambda c: c["maps"][0]["images"].append("elsewhere.png"))
        assert any("elsewhere.png is not in its run folder" in f
                   for f in gate.tracking(base, registry, passing))

    with _tracked_world(gate) as (tmp, base, registry):
        _rewrite(registry, lambda c: c["maps"][0].update(label="another label"))
        assert any("render not current: rendered with label" in f
                   for f in gate.tracking(base, registry, passing))
        os.remove(os.path.join(base, "runs", "exp", "lane", "good", "render.json"))
        assert any("render not current: no render.json" in f
                   for f in gate.tracking(base, registry, passing))

    with _tracked_world(gate) as (tmp, base, registry):
        _rewrite(registry, lambda c: c["maps"].append({**c["maps"][0], "tier": 3}))
        assert "shortlist id good used by 2 entries (tiers 1, 3)" in gate.tracking(base, registry, passing)


def test_tracking_fails_a_changed_or_unrecorded_manifest():
    """A render is stale once the run's manifest.json changes (approved default 5, #120), and a
    `render.json` that records no sha256 of an input in `render.INPUTS` is stale too."""
    gate = _gate()
    render = gate._load("maps_render", "tools", "maps", "render.py")
    passing = lambda d: "pass"      # noqa: E731
    with _tracked_world(gate) as (tmp, base, registry):
        run = os.path.join(base, "runs", "exp", "lane", "good")
        with open(os.path.join(run, "manifest.json"), "w") as fh:
            fh.write('{"parent_run": null}')
        assert render.current(run) == (False, "manifest.json changed since the render")
        assert any("render not current: manifest.json changed" in f
                   for f in gate.tracking(base, registry, passing))

    with _tracked_world(gate) as (tmp, base, registry):
        run = os.path.join(base, "runs", "exp", "lane", "good")
        path = os.path.join(run, "render.json")
        with open(path) as fh:
            rec = json.load(fh)
        del rec["inputs"]["manifest.json"]
        with open(path, "w") as fh:
            json.dump(rec, fh)
        assert render.current(run) == (False, "the render records no sha256 of manifest.json")
        assert any("render not current: the render records no sha256 of manifest.json" in f
                   for f in gate.tracking(base, registry, passing))
