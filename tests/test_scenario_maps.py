"""tools/maps/scenario_maps.py (issue #147): the scenario list parsed from 03, 03 with a scenario set, the refusal of a scenario
whose 03 status is not fine, the shape cache, and the pages drawn from a made-up roster, pieces and shapes (18 box states in 9
divisions, 2 ZIPs each, no Snowflake): 120 pages in order with exact titles, every person labelled where they have area, the legend on
every page, open seats hatched on A and B, no page outside the three views."""
import importlib.util
import io
import itertools
import os
import pathlib
import sys
import tempfile

import shapely
from shapely.geometry import box

ROOT = pathlib.Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("scenario_maps", ROOT / "tools" / "maps" / "scenario_maps.py")
sm = importlib.util.module_from_spec(_spec)
sys.modules["scenario_maps"] = sm
_spec.loader.exec_module(sm)

BLOCK = """
--key edits: begin
--(edits by holder key R<n>, no names: INSERT INTO ssdb_integration.lr_strategy.tmp_m_edit (holder, kept, role, assigned_states, scenario) VALUES ...)
INSERT INTO ssdb_integration.lr_strategy.tmp_m_edit (holder, kept, role, assigned_states, scenario) VALUES
  ('R47', NULL, 'NATIONAL', NULL, 'CA1_R105N'),
  ('R108', NULL, 'WIFI', 'CA', 'CA1_R105N'),
  ('R47', NULL, 'WIFI', NULL, 'CA2_R105N');
INSERT INTO ssdb_integration.lr_strategy.tmp_m_edit (holder, kept, role, assigned_states, scenario) VALUES ('R105', 'Y', 'NATIONAL', 'TX OK', 'CA1_R105R');
INSERT INTO ssdb_integration.lr_strategy.tmp_m_edit (holder, kept, role, assigned_states, scenario) VALUES ('R9', 'N', NULL, NULL, NULL);
INSERT INTO ssdb_integration.lr_strategy.tmp_m_edit (holder, kept, role, assigned_states) VALUES ('R10', 'N', NULL, NULL);
--key edits: end
INSERT INTO ssdb_integration.lr_strategy.tmp_m_edit (holder, kept, role, assigned_states, scenario) VALUES ('R1', 'N', NULL, NULL, 'OUTSIDE');
"""


def test_list_parses_the_scenario_column_of_the_key_edits():
    assert sm.list_scenarios(BLOCK) == ["CA1_R105N", "CA2_R105N", "CA1_R105R"]      # NULL (shared), no column, outside the block: not listed
    try:
        sm.list_scenarios("select 1")
        raise AssertionError("no error without the key edits block")
    except SystemExit:
        pass


def test_the_key_edits_of_03_are_keys_and_no_names():
    sql = (ROOT / "tools" / "snowflake" / "03_assignments.sql").read_text(encoding="utf-8")
    body = sm.re.sub(r"--[^\n]*", "", sm.re.search(r"--key edits: begin(.*?)--key edits: end", sql, sm.re.S).group(1))
    for ins in sm.re.finditer(r"INSERT\s+INTO\s+\S+\s*\(([^)]*)\)\s*VALUES(.*?);", body, sm.re.S | sm.re.I):
        cols = [c.strip().lower() for c in ins.group(1).split(",")]
        assert cols[0] == "holder" and "wholesaler" not in cols and "source" not in cols, cols
        for tup in sm.re.finditer(r"\(\s*'([^']*)'", ins.group(2)):
            assert sm.re.fullmatch(r"R\d+", tup.group(1)), f"key edit {tup.group(1)!r} is not an R<n> key"


def test_list_on_03_gives_the_three_scenarios():
    sql = (ROOT / "tools" / "snowflake" / "03_assignments.sql").read_text(encoding="utf-8")
    assert sm.list_scenarios(sql) == ["CA1_R105N", "CA2_R105N", "CA1_R105R"], sm.list_scenarios(sql)


def test_scenario_sql_sets_the_scenario_and_splices_the_edits():
    sql = "SET scenario    = '';\nx\n--owner edits: begin\nINSERT old;\n--owner edits: end\ny\n"
    out = sm.scenario_sql(sql, "CA1_R105N", "INSERT mine;\n")
    assert "SET scenario    = 'CA1_R105N';" in out and "INSERT mine;\n--owner edits: end" in out and "INSERT old" not in out
    assert "INSERT old" in sm.scenario_sql(sql, "CA1_R105N")                       # no edits file: 03's own block stays
    for bad in ((sql.replace("SET scenario    = '';", ""), "A", None), (sql + sql, "A", None), (sql, "A'; drop", None),
                (sql, "A", "INSERT 'é';"), ("SET scenario = '';\n", "A", "INSERT x;")):
        try:
            sm.scenario_sql(*bad)
            raise AssertionError(f"no error for {bad[1:]}")
        except SystemExit:
            pass


class Cur:
    def __init__(self, cols=None, rows=()):
        self.description, self.rows = ([(c,) for c in cols] if cols else None), list(rows)

    def fetchall(self):
        return self.rows

    def execute(self, sql):
        self.sql = sql

    def close(self):
        pass


class Conn:
    """execute_stream gives each statement's cursor: the statuses on the last statement of the first call (03)."""
    def __init__(self, statuses):
        self.statuses, self.streams, self.queries = statuses, [], []

    def execute_stream(self, stream):
        self.streams.append(stream.read())
        return [Cur(), Cur(["STATUS", "WHOLESALER"], [(s, "x") for s in self.statuses] if len(self.streams) == 1 else [])]

    def cursor(self):
        conn = self

        class C(Cur):
            def execute(self, sql):
                conn.queries.append(sql)
                self.rows = [("CRBG", "Ann", "Y", "WH", "AA")] if "td_assignments" in sql else [("CRBG", "Ann", "Y", "WH", "z", "AA", "WH", 1)]
        return C()


def _split(f, remove_comments=False):
    return [(s, False) for s in f.read().split(";")]


def test_a_scenario_with_a_bad_status_is_refused_with_counts_and_no_names():
    sql03 = "SET scenario = '';\nselect 1;\n"
    bad = Conn(["EDITED", "DEFAULT", "EDIT NOT MATCHED: NO SUCH WHOLESALER", "EDIT NOT MATCHED: NO SUCH WHOLESALER"])
    buf = io.StringIO()
    old, sys.stdout = sys.stdout, buf
    try:
        assert sm.fetch_scenario(bad, "A", sql03, "select 2;", None, _split) is None
    finally:
        sys.stdout = old
    assert "NOT DRAWN" in buf.getvalue() and "'EDIT NOT MATCHED: NO SUCH WHOLESALER': 2" in buf.getvalue() and "'x'" not in buf.getvalue()
    assert len(bad.streams) == 1 and bad.queries == []                      # 04 and the reads did not run
    good = Conn(["DEFAULT", "EDITED", "EDITED (EITHER)"])
    roster, pieces = sm.fetch_scenario(good, "A", sql03, "select 2;", None, _split)
    assert "SET scenario = 'A'" in good.streams[0] and "select 2" in good.streams[1] and len(roster) == 1 and len(pieces) == 1



def test_a_scenario_whose_04_checks_are_not_zero_is_refused():
    sql03 = "SET scenario = '';\nselect 1;\n"

    class Conn04(Conn):
        def execute_stream(self, stream):
            self.streams.append(stream.read())
            if len(self.streams) == 1:
                return [Cur(["STATUS", "WHOLESALER"], [("EDITED", "x")])]
            cols = ["SECTION", "SOURCE", "K1", "K2", "N", "MM_OPP", "PCT", "MUST_BE_ZERO"]
            return [Cur(cols, [("ROSTER", None, "ok check", None, 0, None, None, 1), ("ROSTER", None, "bad check", None, 3, None, None, 1),
                               ("ROSTER", None, "a count", None, 9, None, None, 0)])]
    c = Conn04([])
    buf = io.StringIO()
    old, sys.stdout = sys.stdout, buf
    try:
        assert sm.fetch_scenario(c, "A", sql03, "select 2;", None, _split) is None
    finally:
        sys.stdout = old
    assert "NOT DRAWN" in buf.getvalue() and "bad check = 3" in buf.getvalue() and "ok check" not in buf.getvalue() and "a count" not in buf.getvalue()
    assert c.queries == []                                                  # the tables were not read


# ---- the made-up world: 18 box states (6 columns x 3 rows), division k = two neighbours in a row, 2 ZIPs per state
CODES = [r + c for r in "ABC" for c in "ABCDEF"]
S = 500_000.0


def fake_geo():
    states, zips = {}, {}
    for i, code in enumerate(CODES):
        x, y = (i % 6) * S, (i // 6) * S
        states[code] = box(x, y, x + S, y + S)
        zips[code + "1"], zips[code + "2"] = box(x, y, x + S / 2, y + S), box(x + S / 2, y, x + S, y + S)
    divisions = [(f"D{k + 1}", [CODES[(k // 3) * 6 + (k % 3) * 2], CODES[(k // 3) * 6 + (k % 3) * 2 + 1]]) for k in range(9)]
    return sm.make_geo(states, zips, divisions)


ROSTER = [("CRBG", "Ann N", "Y", "NATIONAL", "AA"), ("CRBG", "Bo R", "Y", "WIFI", "AB AC"), ("CRBG", "Cy W", "Y", "WH", "AD CA"),
          ("CRBG", "Hal R", "Y", "WIFI", ""), ("CRBG", "Ian X", "N", "", ""),
          ("EQH", "Ed N", "Y", "NATIONAL", "BA"), ("EQH", "Flo R", "Y", "WIFI", "BB BC"), ("EQH", "Gus W", "Y", "WH", "BD"),
          ("EQH", "Jo X", "N", "", "")]


def fake_pieces():
    kept = {(s, n): (k, r) for s, n, k, r, _ in ROSTER}
    pieces = []
    for i, code in enumerate(CODES):
        for src, names in (("CRBG", ["Ann N", "Bo R", "Cy W", "Hal R", "Ian X"]), ("EQH", ["Ed N", "Flo R", "Gus W", "Jo X"])):
            for j, z in enumerate((code + "1", code + "2")):
                name = names[(i + j) % len(names)]
                k, r = kept[src, name]
                for tc in ("WH", "FI"):
                    inrole = int(k == "Y" and ((r == "WH" and tc == "WH") or (r in ("WIFI", "NATIONAL"))))
                    pieces.append((src, name, k, r, z, code, tc, inrole))
    return pieces


def _drawn():
    geo = fake_geo()
    ctx = sm.prepare(ROSTER, fake_pieces(), geo)
    return geo, ctx


def _expected_titles(geo):
    out = []
    for g in ["CONUS"] + [d for d, _ in geo.divisions]:
        for ch in ("NATIONAL", "REGIONAL", "WH"):
            for view in ("A whole states", "B held in assigned states", "C today's territories CRBG", "C today's territories EQH"):
                out.append(f"{view} · {ch} · {g}")
    return out


def test_one_scenario_is_120_pages_in_order_with_exact_titles_and_the_labels_legend_and_hatching():
    geo, ctx = _drawn()
    role = {"NATIONAL": "NATIONAL", "REGIONAL": "WIFI", "WH": "WH"}
    geos = {g.name: g.states for g in geo.geographies}
    pieces = fake_pieces()
    seen, open_pages, hatched_pages = [], 0, 0
    for title, fig in sm.pages("CA1_R105N", ctx):
        seen.append(title)
        assert fig.get_suptitle() == title
        view, ch, gname = title.split(" · ")
        assert view in ("A whole states", "B held in assigned states", "C today's territories CRBG", "C today's territories EQH"), title
        states = geos[gname]
        ax = fig.axes[0]
        words = " ".join(t.get_text() for t in ax.texts)
        assert fig.legends and len(fig.legends[0].get_texts()) >= 1, f"no legend on {title}"
        legend = " ".join(t.get_text() for t in fig.legends[0].get_texts())
        mine = [(s, n, k, r, st) for s, n, k, r, st in ROSTER if k == "Y" and r == role[ch]]
        for s, n, k, r, st in mine:
            assigned = set(st.split()) & states
            if view[0] in "AB":
                expect = bool(assigned)
            else:
                expect = s == view.split()[-1] and any(p[1] == n and p[7] and p[5] in states for p in pieces)
            assert (n in words) == expect, f"{title}: label of {n} {'missing' if expect else 'unexpected'}"
            if expect:
                assert n in legend and r in legend, f"{title}: {n} not in the legend"
        if view[0] in "AB":
            owned = {s for _, _, _, _, st in mine for s in st.split()} & states
            has_open = bool(states - owned)
            hatch = [c for c in ax.collections if c.get_gid() == "open" and c.get_hatch()]
            assert bool(hatch) == has_open, f"{title}: open seat hatching {bool(hatch)}, open states {has_open}"
            open_pages += has_open
            hatched_pages += bool(hatch)
    assert seen == _expected_titles(geo) and len(seen) == 120
    assert open_pages > 40 and hatched_pages == open_pages


def test_a_crowded_out_label_is_still_set_and_shapeless_zips_are_counted():
    geo = fake_geo()
    pieces = fake_pieces() + [("CRBG", "Bo R", "Y", "WIFI", "99999", "AB", "WH", 1), ("CRBG", "Bo R", "Y", "WIFI", "88888", "ZZ", "WH", 1)]
    ctx = sm.prepare(ROSTER, pieces, geo)
    assert ctx.no_shape == 1                                    # 99999 is CONUS (state AB) with no shape; ZZ is not CONUS
    keep, sm.look.place_labels = sm.look.place_labels, lambda ax, items, **kw: []   # every label crowded out
    try:
        g = geo.geographies[0]
        fig = sm.draw_page(ctx, "t", g, "REGIONAL", "A whole states", None)
    finally:
        sm.look.place_labels = keep
    texts = {x.get_text() for ax in fig.axes for x in ax.texts}
    assert {"Bo R", "Flo R"} <= texts, texts


def test_pages_drawn_in_chunks_assemble_in_order_into_one_pdf():
    assert sm.chunks(25, 10) == [(0, 10), (10, 20), (20, 25)]
    geo = fake_geo()
    sm._init(geo)
    sm._CTX.clear()
    n = len(sm.specs(geo))
    parts = [sm.draw_chunk("CA1_R105N", ROSTER, fake_pieces(), lo, hi) for lo, hi in reversed(sm.chunks(n))]  # any order
    pngs = [png for _, ps, _ in sorted(parts) for png in ps]
    assert len(pngs) == n == 120 and all(png[:8] == b"\x89PNG\r\n\x1a\n" for png in pngs)
    first = sm.draw_chunk("CA1_R105N", ROSTER, fake_pieces(), 0, 1)[1][0]
    assert pngs[0] == first                                     # page 0 is the CONUS page, whichever chunk ran first
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "x.pdf")
        assert sm.assemble(path, [(png, "CA1_R105N") for png in pngs]) == 120
        assert len(sm.re.findall(rb"/Type\s*/Page[^s]", open(path, "rb").read())) == 120


def test_chunks_draw_in_spawned_processes_as_on_windows():
    import concurrent.futures, multiprocessing
    sys.path.insert(0, str(ROOT / "tools" / "maps"))           # the child imports scenario_maps by name, as on Windows
    import scenario_maps as sm2
    geo = fake_geo()
    with concurrent.futures.ProcessPoolExecutor(2, mp_context=multiprocessing.get_context("spawn"),
                                                initializer=sm2._init, initargs=(geo,)) as pool:
        got = [f.result() for f in [pool.submit(sm2.draw_chunk, "S", ROSTER, fake_pieces(), lo, hi) for lo, hi in ((0, 2), (2, 4))]]
    assert [lo for lo, _, _ in got] == [0, 2] and all(len(p) == 2 for _, p, _ in got)


def test_a_division_page_draws_only_its_states_and_the_pdf_is_pages_as_images():
    geo, ctx = _drawn()
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "x.pdf")
        titles = []
        n = sm.write_pdf(path, itertools.islice(sm.pages("S", ctx), 5), inspect=lambda t, f: titles.append(t))
        assert n == 5 and len(titles) == 5 and open(path, "rb").read(5) == b"%PDF-"
        try:
            sm.write_pdf(path, iter(()))
            raise AssertionError("no error for a PDF with no page")
        except RuntimeError:
            pass


def test_divisions_need_nine_each_with_a_state():
    geo = fake_geo()
    divs = {f"{k + 1}|D{k + 1}": shapely.union_all([geo.states[s] for s in cs]) for k, (_, cs) in enumerate(geo.divisions)}
    got = sm.assign_divisions(geo.states, divs)
    assert got == geo.divisions
    try:
        sm.assign_divisions(geo.states, {k: v for k, v in list(divs.items())[:8]})
        raise AssertionError("no error for 8 divisions")
    except SystemExit:
        pass


def test_shapes_are_cached_by_table_and_tolerance_and_read_from_snowflake_once():
    poly = shapely.to_wkb(box(-100, 38, -99, 39))

    class C2(Conn):
        def cursor(self):
            conn = self

            class C(Cur):
                def execute(self, sql):
                    conn.queries.append(sql)
                    self.rows = [("20", poly), ("21", None)]          # 21: no boundary (NULL), left out and reported
            return C()

    with tempfile.TemporaryDirectory() as d:
        conn = C2([])
        buf = io.StringIO()
        old, sys.stdout = sys.stdout, buf
        try:
            a = sm.load_table(conn, "state", d)
        finally:
            sys.stdout = old
        assert "1 rows have no boundary, left out: 21" in buf.getvalue(), buf.getvalue()
        n = len(conn.queries)
        b = sm.load_table(conn, "state", d)
        assert len(conn.queries) == n and any("COALESCE(ST_SIMPLIFY(geo_boundary, 250, TRUE), geo_boundary)" in q for q in conn.queries) and any("WKB" in q for q in conn.queries)
        assert list(a) == ["20"] and a["20"].equals(b["20"])
        assert os.listdir(d) == ["census_states_250m_5070.tsv.gz"]
        x0, y0, x1, y1 = a["20"].bounds
        assert 0 < x1 - x0 < 150_000 and 0 < y1 - y0 < 150_000                  # about 1 degree, in metres


# ---- view D (issue #148): overlaps and gaps, on fake TD_GAP_* data over the same 18 box states
CLASSES = [c for c, *_ in sm.GAP_CLASSES]
NAMES = {"R1": "Ann N", "R2": "Bo R", "R3": "Cy W"}
CELL_COLS = ["SCENARIO", "EST_SOURCE", "ZIP_CODE", "STATE", "NEW_DIST", "MM_OPP", "CHANNEL", "ASSIGNED", "CLASS", "N_HOLDERS", "HOLDERS"]
PAIR_COLS = ["SCENARIO", "EST_SOURCE", "CHANNEL", "HOLDER_A", "HOLDER_B", "N_ZIPS", "MM_OPP"]
PERSON_COLS = ["SCENARIO", "EST_SOURCE", "HOLDER", "SOURCE", "ROLE", "ASSIGNED_STATES", "OPP_ASSIGNED", "N_ZIPS_ASSIGNED"]
SUMMARY_COLS = ["SECTION", "SCENARIO", "EST_SOURCE", "CHANNEL", "ITEM", "N_ZIPS", "MM_OPP", "PCT", "MUST_BE_ZERO"]


USD = 1e6   # TD_GAP_* MM_OPP is in dollars: $1,000,000 must show as 1.0 $MM on the pages


def fake_cells():
    """Every ZIP has a NATIONAL cell for each estimate (class by ZIP index); AA1 also has a second, bigger NATIONAL cell of
    another class (the class with most $ wins) and a REGIONAL one; state AA is assigned R1 and R2 (names joined); one OPEN cell."""
    rows = []
    for est in ("LOW", "HIGH"):
        for i, code in enumerate(CODES):
            for j, z in enumerate((code + "1", code + "2")):
                rows.append(("S", est, z, code, "D", (1.0 + j) * USD, "NATIONAL", "R1 R2" if code == "AA" else None, CLASSES[(i + j) % 7], 1, "R1"))
        rows.append(("S", est, "AA1", "AA", "D", 5.0 * USD, "NATIONAL", "R1 R2", "GAP", 0, None))          # AA1: GAP 5.0 beats the 1.0 cell
        rows.append(("S", est, "AA1", "AA", "D", 2.0 * USD, "REGIONAL", "R3", "OVERLAP", 2, "R1 R2"))
        rows.append(("S", est, "BA1", "BA", "D", 7.0 * USD, "OPEN", None, "OPEN SEAT HELD", 1, "R1"))
    return rows


def fake_pairs():
    return [("S", est, "NATIONAL", "R1", "R2", 3, (100.0 + k) * USD) for est in ("LOW", "HIGH") for k in range(20)] + [("S", "LOW", "WH", "R1", "R9", 1, 1.0 * USD)]


def _gd():
    return sm.gap_prepare((CELL_COLS, fake_cells()), (PAIR_COLS, fake_pairs()), NAMES)


def test_a_zip_has_the_class_of_its_cells_with_the_most_dollars_and_names_come_from_keys():
    gd = _gd()
    assert gd.ests == ["HIGH", "LOW"]
    assert gd.zips["LOW", "NATIONAL"]["AA1"] == ("AA", "GAP", 6.0)          # 5.0 GAP beats the 1.0 cell of its own class; total 6.0
    assert gd.zips["LOW", "NATIONAL"]["AA2"][1] == CLASSES[1]               # no second cell: its own
    assert gd.zips["LOW", "REGIONAL"]["AA1"][1] == "OVERLAP" and list(gd.zips["LOW", "REGIONAL"]) == ["AA1"]
    assert gd.assigned["NATIONAL", "AA"] == "Ann N / Bo R" and gd.assigned["REGIONAL", "AA"] == "Cy W" and ("OPEN", "BA") not in gd.assigned
    assert gd.table["LOW", "OPEN", "OPEN SEAT HELD"] == 7.0 and gd.table["LOW", "NATIONAL", "GAP"] > 5.0
    top = gd.pairs["LOW"]
    assert len(gd.pairs["HIGH"]) == 15 and top[0] == ("NATIONAL", "R1 Ann N", "R2 Bo R", 3, 119.0) and ("WH", "R1 Ann N", "R9", 1, 1.0) not in top
    try:
        sm.gap_prepare((CELL_COLS, [("S", "LOW", "AA1", "AA", "D", 1, "NATIONAL", None, "NO SUCH CLASS", 1, None)]), (PAIR_COLS, []), NAMES)
        raise AssertionError("no error for an unknown class")
    except SystemExit:
        pass


def test_gap_pages_are_a_summary_then_geography_channel_estimate_with_exact_titles_and_legend_sums():
    geo, gd = fake_geo(), _gd()
    sm._init(geo)
    got = list(sm.gap_pages("S", gd, geo))
    expect = ["D overlaps and gaps · summary"] + [f"D overlaps and gaps · {ch} · {est} estimate · {g}"
                                                     for g in ["CONUS"] + [d for d, _ in geo.divisions] for ch in ("NATIONAL", "REGIONAL", "WH") for est in ("HIGH", "LOW")]
    assert [t for t, _ in got] == expect and len(got) == 61
    assert all(f.get_suptitle() == t for t, f in got)
    for title, fig in got[1:]:
        _, ch, est, gname = title.split(" · ")
        states = {g.name: g.states for g in geo.geographies}[gname]
        zs = {z: v for z, v in gd.zips.get((est.split()[0], ch), {}).items() if v[0] in states}
        legend = " ".join(t.get_text() for t in fig.legends[0].get_texts())
        for cls in CLASSES:
            mine = [v for v in zs.values() if v[1] == cls]
            assert f"{cls}\n{len(mine):,} ZIPs · ${sum(v[2] for v in mine):,.1f} MM" in legend, (title, cls, legend)
        assert sum(len(c.get_paths()) for c in fig.axes[0].collections if c.get_gid() in CLASSES) == len(zs)
        names = {t.get_text() for t in fig.axes[0].texts}
        assert ("Ann N / Bo R" in names) == (ch == "NATIONAL" and "AA" in states) and ("Cy W" in names) == (ch == "REGIONAL" and "AA" in states), title
    hatched = {c.get_gid() for c in got[1][1].axes[0].collections if c.get_hatch()}
    assert hatched <= {"OPEN SEAT HELD", "OPEN SEAT UNHELD"}
    text = " ".join(t.get_text() for t in got[0][1].texts)
    assert "HIGH estimate" in text and "LOW estimate" in text and "R1 Ann N" in text and "R2 Bo R" in text and "top 15" in text
    assert text.count("R1 Ann N") == 2 * 15 and "R9" not in text           # 15 pairs per estimate; the WH pair is outside the top 15
    assert "119.0" in text and "105.0" in text and "104.0" not in text     # the pairs 105..119 only


def test_gap_csvs_hold_each_row_once_with_the_scenarios_that_have_it():
    cols = ["EST_SOURCE", "SCENARIO", "X", "MM_OPP", "LOAD_RATIO"]
    gaps = {s: {k: (cols, rows) for k in ("cell", "pair", "person", "summary", "load")} for s, rows in (
        ("A", [("E", "A", "same", 1.001, 2.2677411315649), ("E", "A", "twice", 2.0, 1.0), ("E", "A", "twice", 2.0, 1.0), ("E", "A", "a and b", 3.0, 1.25)]),
        ("B", [("E", "B", "same", 1.004, 2.2677411315650), ("E", "B", "twice", 2.0, 1.0), ("E", "B", "twice", 2.0, 1.0), ("E", "B", "a and b", 3.0, 1.25),
               ("E", "B", "b only", 4.0, 1.0)]),
        ("C", [("E", "C", "same", 1.0, 2.2677411315649), ("E", "C", "twice", 2.0, 1.0), ("E", "C", "twice", 2.0, 1.0), ("E", "C", "a and b", 3.0, 1.251)]))}
    with tempfile.TemporaryDirectory() as d:
        paths = sm.write_gap_csvs(d, gaps)
        assert [os.path.basename(p) for p in paths] == [f"gap_{k}.csv" for k in ("cell", "pair", "person", "summary", "load")]
        got = open(paths[0], encoding="utf-8").read().splitlines()
    # dollars the same to the cent and a ratio the same to 9 digits are one row (the first scenario's numbers); 1.25 against 1.251
    # is not; a row twice in each scenario stays twice; the scenarios are always named; the column stays in place
    assert got == ["EST_SOURCE,SCENARIO,X,MM_OPP,LOAD_RATIO", "E,A B C,same,1.001,2.2677411315649", "E,A B C,twice,2.0,1.0", "E,A B C,twice,2.0,1.0",
                   "E,A B,a and b,3.0,1.25", "E,B,b only,4.0,1.0", "E,C,a and b,3.0,1.251"], got   # in the order first seen


def test_identical_pages_are_drawn_once_labelled_with_their_scenarios():
    got = sm.merge_pages({"A": [b"p0", b"p1", b"p2"], "B": [b"p0", b"q1", b"p2"], "C": [b"p0", b"p1", b"r2"]})
    assert got == [(b"p0", "all scenarios"), (b"p1", "A · C"), (b"q1", "B"), (b"p2", "A · B"), (b"r2", "C")]
    assert sm.merge_pages({"A": [b"p0"]}) == [(b"p0", "A")]
    # C's gap output refused: A and B share the gap page, which is not "all scenarios" of the run
    assert sm.merge_pages({"A": [b"g"], "B": [b"g"]}, ["A", "B", "C"]) == [(b"g", "A · B")]
    try:
        sm.merge_pages({"A": [b"p0"], "B": []})
        raise AssertionError("no error for scenarios with different page counts")
    except RuntimeError:
        pass


def test_load_is_dollars_against_the_area_adjusted_expectation():
    cc = ["EST_SOURCE", "ZIP_CODE", "CHANNEL", "ASSIGNED", "CLASS", "HOLDERS", "MM_OPP"]
    cells = [("E", "a1", "REGIONAL", "R1", "COVERED", "R1", 1e9), ("E", "a2", "REGIONAL", "R1", "GAP", None, 5e8),
             ("E", "b1", "REGIONAL", "R2", "COVERED", "R2", 5e8),
             ("E", "c1", "REGIONAL", "R1 R2", "COVERED", "R1", 4e8), ("E", "c2", "REGIONAL", "R1 R2", "GAP", None, 1e8),
             ("E", "c3", "REGIONAL", "R1 R2", "OVERLAP", "R1 R7", 2e8),
             ("E", "d1", "NATIONAL", "R3", "COVERED", "R3", 11e9), ("E", "o1", "OPEN", None, "OPEN SEAT UNHELD", None, 9e9)]
    pc = ["EST_SOURCE", "HOLDER", "ROLE", "ASSIGNED_STATES"]
    # state A is R1's, B R2's, C split between R1 and R2 (both WIFI), D R3's (NATIONAL); R9 has no $
    people = [("E", "R1", "WIFI", "A C"), ("E", "R2", "WIFI", "B C"), ("E", "R3", "NATIONAL", "D"), ("E", "R9", "WH", "E")]
    area = {"A": 100, "B": 400, "C": 300, "D": 200, "E": 50}
    cols, rows = sm.gap_load("S", {"cell": (cc, cells), "person": (pc, people)}, area)
    got = {r[2]: dict(zip(cols, r)) for r in rows}
    # $: R1 a1 + a2 + c1 (covered alone) + half of c2 and c3 = 1e9 + 5e8 + 4e8 + 5e7 + 1e8 = 2.05e9; R2 b1 + the halves = 6.5e8;
    # together 2.7e9, the channel's REGIONAL $, nothing counted twice
    assert (got["R1"]["ASSIGNED_USD"], got["R2"]["ASSIGNED_USD"]) == (2.05e9, 6.5e8)
    # area: R1 A + half of C = 250 km2, R2 B + half of C = 550, median 400 (the territories, ZIPs with no cell too)
    assert (got["R1"]["AREA_KM2"], got["R2"]["AREA_KM2"], got["R1"]["MEDIAN_AREA_KM2"]) == (250.0, 550.0, 400.0)
    assert abs(got["R1"]["EXPECTED_USD"] - 1.25e9 * (250 / 400) ** 0.5) < 1 and abs(got["R1"]["LOAD_RATIO"] - 2.05 / (1.25 * 0.625 ** 0.5)) < 0.001
    assert abs(got["R2"]["LOAD_RATIO"] - 0.65 / (1.25 * (550 / 400) ** 0.5)) < 0.001
    # national base: the channel's attributed $ (11e9) / 11 = 1e9, its own median: load 11
    assert got["R3"]["BASE_USD"] == 1e9 and got["R3"]["LOAD_RATIO"] == 11.0 and got["R3"]["AREA_KM2"] == 200.0
    assert "R9" not in got                                            # no assigned $: no load row


class GapConn(Conn):
    """07's result on execute_stream, the TD_GAP tables and the names on cursor().execute."""
    def __init__(self, summary):
        super().__init__([])
        self.summary = summary

    def execute_stream(self, stream):
        self.streams.append(stream.read())
        return [Cur(SUMMARY_COLS, self.summary(self.streams[-1]) if callable(self.summary) else self.summary)]

    def cursor(self):
        conn = self

        class C(Cur):
            def execute(self, sql):
                conn.queries.append(sql)
                self.rows, cols = [], []
                if "td_gap_cell" in sql:
                    cols, self.rows = CELL_COLS, fake_cells()
                elif "td_gap_pair" in sql:
                    cols, self.rows = PAIR_COLS, fake_pairs()
                elif "td_gap_person" in sql:
                    cols, self.rows = PERSON_COLS, [("S", "LOW", "R1", "CRBG", "NATIONAL", "AA", 1.0, 2)]
                elif "td_holder_key" in sql:
                    self.rows = list(NAMES.items())
                self.description = [(c,) for c in cols] or None
        return C()


GOOD = [("CHECK", "S", None, None, "all ZIPs classed", 0, 0.2, None, 1), ("CHECK", "S", None, None, "a count", 5, 9.0, None, 0)]
BAD = GOOD + [("CHECK", "S", "LOW", "WH", "ZIP in two classes", 3, 0.0, None, 1), ("CHECK", "S", None, None, "dollars lost", 0, 4.0, None, 1)]


def test_07_failing_must_be_zero_rows_refuse_the_gap_output_and_name_the_items():
    assert sm.gap_failures((SUMMARY_COLS, GOOD)) == [] and len(sm.gap_failures((SUMMARY_COLS, BAD))) == 2
    buf = io.StringIO()
    old, sys.stdout = sys.stdout, buf
    try:
        bad = sm.fetch_gap(GapConn(BAD), "S", "SET scenario    = '';\nselect 1;\n", _split)
        good = sm.fetch_gap(GapConn(GOOD), "S", "SET scenario    = '';\nselect 1;\n", _split)
    finally:
        sys.stdout = old
    assert bad is None and "ZIP in two classes" in buf.getvalue() and "dollars lost" in buf.getvalue() and "all ZIPs classed" not in buf.getvalue()
    assert good["names"] == NAMES and good["cell"][0] == CELL_COLS and len(good["pair"][1]) == len(fake_pairs()) and good["summary"] == (SUMMARY_COLS, GOOD)


def test_main_writes_the_four_csvs_and_the_gaps_pdf_and_skips_when_07_is_missing():
    import types
    fake = {"snowflake": types.ModuleType("snowflake"), "snowflake.connector": types.ModuleType("snowflake.connector"),
            "snowflake.connector.util_text": types.ModuleType("snowflake.connector.util_text")}
    fake["snowflake.connector.util_text"].split_statements = _split
    saved = {k: sys.modules.get(k) for k in fake}
    sys.modules.update(fake)
    keep = {k: getattr(sm, k) for k in ("connect", "load_geo", "fetch_scenario", "MAPS_DIR", "SQL07", "EDITS", "CHUNK", "assemble")}
    labels = []
    sm.assemble = lambda path, pages: (labels.extend(l for _, l in pages), keep["assemble"](path, pages))[1]

    class Ctx:
        def __init__(self, conn): self.conn = conn
        def __enter__(self): return self.conn
        def __exit__(self, *a): return False

    def run(summary, sql07, scen="CA1_R105N", roster=None):
        with tempfile.TemporaryDirectory() as d:
            sm.MAPS_DIR, sm.SQL07, sm.EDITS = d, sql07, os.path.join(d, "none.sql")
            sm.connect = lambda: Ctx(GapConn(summary))
            sm.load_geo = lambda conn: fake_geo()
            sm.fetch_scenario = lambda conn, name, *a: (roster(name) if roster else ROSTER, fake_pieces())
            buf = type("Out", (io.StringIO,), {"reconfigure": lambda self, **kw: None})()
            old, sys.stdout = sys.stdout, buf
            try:
                rc = sm.main(["--scenario", scen, "--jobs", "1"])
            finally:
                sys.stdout = old
            files = sorted(f for _, _, fs in os.walk(d) for f in fs)
            run_dir = next(os.path.join(d, x) for x in os.listdir(d) if os.path.isdir(os.path.join(d, x)))
            pdfs = {f: len(sm.re.findall(rb"/Type\s*/Page[^s]", open(os.path.join(run_dir, f), "rb").read())) for f in files if f.endswith(".pdf")}
            csv_rows = {f: len(open(os.path.join(run_dir, f), encoding="utf-8").read().splitlines()) for f in files if f.endswith(".csv")}
            return rc, buf.getvalue(), files, pdfs, csv_rows

    try:
        f07 = os.path.join(tempfile.gettempdir(), "07_fake_gap.sql")
        with open(f07, "w") as f:
            f.write("SET scenario    = '';\nselect 1;\n")
        gap_files = sorted(f"gap_{k}.csv" for k in ("cell", "pair", "person", "summary", "load"))
        rc, out, files, pdfs, csvs = run(GOOD, f07)                          # CONUS only: 12 map pages, a summary and 6 gap pages
        assert rc == 0 and files == sorted(gap_files + ["maps.pdf"]), files
        assert pdfs == {"maps.pdf": 12 + 7} and "safe to send to an agent" in out, (pdfs, out)
        assert csvs["gap_cell.csv"] == 1 + len(fake_cells()) and csvs["gap_summary.csv"] == 1 + len(GOOD)
        # two scenarios the same: every page and row once
        rc, out, files, pdfs, csvs = run(GOOD, f07, "CA1_R105N,CA2_R105N")
        assert rc == 0 and pdfs == {"maps.pdf": 19} and csvs["gap_cell.csv"] == 1 + len(fake_cells()), (pdfs, csvs)
        # CA2 moves Ann (CRBG, NATIONAL) to WIFI: NATIONAL and REGIONAL pages A, B and C CRBG differ (6 more); C EQH, WH and gaps shared
        moved = lambda name: [r if r[1] != "Ann N" or name == "CA1_R105N" else r[:3] + ("WIFI",) + r[4:] for r in ROSTER]
        rc, out, files, pdfs, csvs = run(GOOD, f07, "CA1_R105N,CA2_R105N", moved)
        assert rc == 0 and pdfs == {"maps.pdf": 19 + 6}, pdfs
        # CA1_R105R's 07 refused: the 12 map pages are all three scenarios', the 7 gap pages the other two's, not "all scenarios"
        labels.clear()
        rc, out, files, pdfs, csvs = run(lambda sql: BAD if "CA1_R105R" in sql else GOOD, f07, "CA1_R105N,CA2_R105N,CA1_R105R")
        assert rc == 1 and pdfs == {"maps.pdf": 19} and labels == ["all scenarios"] * 12 + ["CA1_R105N · CA2_R105N"] * 7, (rc, pdfs, labels)
        rc, out, files, pdfs, csvs = run(BAD, f07)                           # refused gap output, the maps still drawn, exit 1
        assert rc == 1 and files == ["maps.pdf"] and pdfs == {"maps.pdf": 12} and "dollars lost" in out, (files, out)
        rc, out, files, pdfs, csvs = run(GOOD, os.path.join(tempfile.gettempdir(), "07_does_not_exist.sql"))
        assert rc == 0 and files == ["maps.pdf"] and out.count("07_overlap_gap.sql is not in this checkout") == 1, (files, out)
    finally:
        for k, v in keep.items():
            setattr(sm, k, v)
        for k, v in saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v


if __name__ == "__main__":
    for k, v in list(globals().items()):
        if k.startswith("test_"):
            v()
            print("ok", k)
