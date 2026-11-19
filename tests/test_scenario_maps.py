"""tools/maps/scenario_maps.py (issue #147): the scenario list parsed from 03, 03 with a scenario set, the refusal of a scenario
whose 03 status is not fine, the shape cache, and the pages drawn from a made-up roster, pieces and shapes (18 box states in 9
divisions, 2 ZIPs each, no Snowflake): 120 pages in order with exact titles, every person labelled where they have area, the legend on
every page, open seats hatched on A and B, no page outside the three views."""
import importlib.util
import collections
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


def test_products_sql_replaces_the_one_line_in_04_and_08_and_refuses_a_bad_value():
    sql = "SET scenario = '';\nSET exclude_products = 'FIXED';\nx\n"
    assert "SET exclude_products = '';" in sm.products_sql(sql, ())
    assert "SET exclude_products = 'INDEX RILA';" in sm.products_sql(sql, ("rila  index", "RILA"))      # upper case, sorted, once each
    assert sm.products_sql(sql, ("FIXED",)) == sql and sm.product_list(["fixed", "index  rila"]) == ("FIXED", "INDEX", "RILA")
    for bad in ("FIXED'; drop", "FIXED,INDEX", "FIXED_X", "é"):
        try:
            sm.products_sql(sql, (bad,))
            raise AssertionError(f"no error for {bad!r}")
        except SystemExit as e:
            assert "letters, digits and spaces only" in str(e), e
    for none in ("SET scenario = '';\n", sql + sql):
        try:
            sm.products_sql(none, ())
            raise AssertionError("no error without exactly one line")
        except SystemExit as e:
            assert "needs exactly 1" in str(e), e
    for name in ("04_assigned_coverage.sql", "08_seat_fit.sql"):                  # the real files: exactly one line, FIXED by default
        real = (ROOT / "tools" / "snowflake" / name).read_text(encoding="utf-8")
        assert "SET exclude_products = 'FIXED';" in real and sm.products_sql(real, ("FIXED",)) == real, name
        assert "SET exclude_products = '';" in sm.products_sql(real, ())


def test_the_run_folder_suffix_and_the_text_say_which_products():
    assert [sm.run_suffix(x) for x in ((), ("FIXED",), ("INDEX",), ("FIXED", "INDEX"))] == ["-allproducts", "", "-exINDEX", "-exFIXED-INDEX"]
    assert [sm.products_text(x) for x in ((), ("FIXED",), ("FIXED", "INDEX"))] == ["all products", "excluding FIXED", "excluding FIXED, INDEX"]


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
                rows.append(("S", est, z, code, "D", (1.0 + j) * USD, "NATIONAL", "R1 R2" if code == "AA" else None, CLASSES[(i + j) % 5], 1, "R1"))   # the 5 classes of a channel
        rows.append(("S", est, "AA1", "AA", "D", 5.0 * USD, "NATIONAL", "R1 R2", "GAP (UNHELD)", 0, None))          # AA1: GAP 5.0 beats the 1.0 cell
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
    assert gd.zips["LOW", "NATIONAL"]["AA1"] == ("AA", "GAP (UNHELD)", 6.0)          # 5.0 GAP beats the 1.0 cell of its own class; total 6.0
    assert gd.zips["LOW", "NATIONAL"]["AA2"][1] == CLASSES[1]               # no second cell: its own
    assert gd.zips["LOW", "REGIONAL"]["AA1"][1] == "OVERLAP" and list(gd.zips["LOW", "REGIONAL"]) == ["AA1"]
    assert gd.assigned["NATIONAL", "AA"] == "Ann N / Bo R" and gd.assigned["REGIONAL", "AA"] == "Cy W" and ("OPEN", "BA") not in gd.assigned
    assert gd.table["LOW", "OPEN", "OPEN SEAT HELD"] == 7.0 and gd.table["LOW", "NATIONAL", "GAP (UNHELD)"] > 5.0
    top = gd.pairs["LOW"]
    assert len(gd.pairs["HIGH"]) == 15 and top[0] == ("NATIONAL", "R1 Ann N", "R2 Bo R", 3, 119.0) and ("WH", "R1 Ann N", "R9", 1, 1.0) not in top
    try:
        sm.gap_prepare((CELL_COLS, [("S", "LOW", "AA1", "AA", "D", 1, "NATIONAL", None, "NO SUCH CLASS", 1, None)]), (PAIR_COLS, []), NAMES)
        raise AssertionError("no error for an unknown class")
    except SystemExit:
        pass


def test_the_gap_summary_page_says_which_products():
    for text in ("excluding FIXED", "all products"):
        gd = _gd()
        gd.products = text
        assert sm.draw_gap_summary("S", gd).texts[-1].get_text().splitlines()[0] == f"Products: {text}"


def test_gap_pages_are_a_summary_then_geography_channel_estimate_with_exact_titles_and_legend_sums():
    geo, gd = fake_geo(), _gd()
    sm._init(geo)
    got = list(sm.gap_pages("S", gd, geo))
    expect = ["D overlaps and gaps · summary"] + [f"D overlaps and gaps · {ch} · {est} estimate · {g}"
                                                     for g in ["CONUS"] + [d for d, _ in geo.divisions] for ch in ("FILL", "NATIONAL", "REGIONAL", "WH", "OPEN") for est in ("HIGH", "LOW")]
    assert [t for t, _ in got] == expect and len(got) == 101
    assert all(f.get_suptitle() == t for t, f in got)
    fills = [(t, f) for t, f in got[1:] if " · FILL · " in t]
    for title, fig in fills:                                             # every channel's unfilled $, exact per class, on the page's ZIPs
        _, _, est, gname = title.split(" · ")
        states = {g.name: g.states for g in geo.geographies}[gname]
        legend = " ".join(t.get_text() for t in fig.legends[0].get_texts())
        mine = [r for r in fake_cells() if r[1] == est.split()[0] and r[3] in states]
        for cls in [c for c, *_ in sm.FILL_CLASSES]:
            assert f"{cls}\n" in legend and f"${sum(r[5] for r in mine if r[8] == cls) / USD:,.1f} MM" in legend.split(cls + "\n")[1].split("\n")[0], (title, cls, legend)
        n = sum(int(t.get_text().split("\n")[1].split()[0].replace(",", "")) for t in fig.legends[0].get_texts() if " ZIPs" in t.get_text())
        assert n == len({r[2] for r in mine}), (title, n)                  # every ZIP once, in one colour
        assert ("not on the map" in legend) == (gname == "CONUS") and (gname != "CONUS" or "$0.0 MM unfilled" in legend), (title, legend)
    assert len(fills) == 20
    assert gd.fill["LOW"]["BA1"][1] == "OPEN SEAT HELD" and gd.fill["LOW"]["AA1"][1] == "GAP (UNHELD)"   # AA1: GAP 5.0 beats OVERLAP 2.0
    # no unfilled $: TO BARGAIN with OVERLAP or HELD BY ANOTHER $, else COVERED
    kinds = {cls: {r[2] for r in fake_cells() if r[1] == "LOW" and r[8] == cls} for cls in CLASSES}
    for z, (_, cls, d) in gd.fill["LOW"].items():
        if not any(d.get(c, 0) > 0 for c, *_ in sm.FILL_CLASSES):
            assert cls == (sm.BARGAIN[0] if d.get("OVERLAP", 0) > 0 or d.get("HELD BY ANOTHER", 0) > 0 else sm.NO_FILL[0]), (z, cls, d)
    assert {sm.BARGAIN[0], sm.NO_FILL[0]} <= {c for _, c, _ in gd.fill["LOW"].values()}
    for title, fig in got[1:]:
        if " · FILL · " in title:
            continue
        _, ch, est, gname = title.split(" · ")
        states = {g.name: g.states for g in geo.geographies}[gname]
        zs = {z: v for z, v in gd.zips.get((est.split()[0], ch), {}).items() if v[0] in states}
        legend = " ".join(t.get_text() for t in fig.legends[0].get_texts())
        for cls in CLASSES:
            mine = [v for v in zs.values() if v[1] == cls]
            on_page = (cls in sm.OPEN_CLASSES) == (ch == "OPEN")         # open seats only on the OPEN page, the rest never there
            assert (f"{cls}\n" in legend) == on_page and (not on_page or f"{cls}\n{len(mine):,} ZIPs · ${sum(v[2] for v in mine):,.1f} MM" in legend), (title, cls, legend)
        if ch == "OPEN" and "BA" in states and est == "LOW":
            assert "OPEN SEAT HELD\n1 ZIPs · $7.0 MM" in legend, legend          # the open seat BA1 is drawn
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


def test_the_conus_fill_page_ties_to_every_unfilled_dollar():
    geo = fake_geo()
    sm._init(geo)
    off = [("S", "LOW", "ZZ9", None, "D", 3.0 * USD, "OPEN", None, "OPEN SEAT UNHELD", 0, None),          # no state
           ("S", "LOW", "AA9", "AA", "D", 2.0 * USD, "REGIONAL", "R3", "GAP (HELD TODAY)", 0, None)]     # no ZCTA shape
    gd = sm.gap_prepare((CELL_COLS, fake_cells() + off), (PAIR_COLS, []), NAMES)
    fig = sm.draw_fill_page(gd, geo, "t", geo.geographies[0], "LOW")
    legend = " ".join(t.get_text() for t in fig.legends[0].get_texts())
    assert "not on the map (no state, or no ZCTA shape)\n$5.0 MM unfilled" in legend, legend
    on_map = sum(float(t.get_text().split("$")[1].split()[0].replace(",", "")) for t in fig.legends[0].get_texts()
                 if t.get_text().split("\n")[0] in [c for c, *_ in sm.FILL_CLASSES])
    assert abs(on_map + 5.0 - gd.fill_total["LOW"]) < 1e-9, (on_map, gd.fill_total["LOW"])


def test_off_map_round_off_is_not_a_negative_zero():
    geo = fake_geo()
    sm._init(geo)
    cells = [("S", "LOW", "AA1", "AA", "D", 0.1 * USD, "NATIONAL", "R1", "GAP (UNHELD)", 0, None),          # reviewer's case: summed in
             ("S", "LOW", "AB1", "AB", "D", 0.2 * USD, "REGIONAL", "R3", "GAP (UNHELD)", 0, None),          # another grouping, 0.1 + 0.2 + 0.3
             ("S", "LOW", "AC1", "AC", "D", 0.3 * USD, "REGIONAL", "R3", "GAP (UNHELD)", 0, None)]          # leaves -1e-16
    gd = sm.gap_prepare((CELL_COLS, cells), (PAIR_COLS, []), NAMES)
    legend = " ".join(t.get_text() for t in sm.draw_fill_page(gd, geo, "t", geo.geographies[0], "LOW").legends[0].get_texts())
    assert "\n$0.0 MM unfilled" in legend and "-0.0" not in legend, legend


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


SEAT_COLS = ["SECTION", "SCENARIO", "EST_SOURCE", "SEAT", "KIND", "HOLDER", "RANK", "BORDERS", "SEAT_MM_OPP", "N", "MUST_BE_ZERO"]
FIT_COLS = ["SCENARIO", "EST_SOURCE", "SEAT", "SEAT_MM_OPP", "KIND", "HOLDER", "SOURCE", "KEPT", "ROLE", "BORDERS", "U", "G", "DNASH", "RANK"]
SEATS = {"CC": 3e8, "BA": 7e8}                                          # seat -> its $ (MM_OPP is dollars)
CANDS = {"NEIGHBOUR": [("R3", 1, 1), ("R1", 2, 1), ("R2", 3, 0), ("R9", 4, 0)],    # (holder, rank, borders); rank 4 is not on the page
         "HOLDER": [("R2", 1, 0), ("R3", 2, 0), ("R1", 3, 0), ("R9", 4, 0)]}
LOADS = {"LOW": [("R1", 100.0, 1e9), ("R2", 200.0, 1e8)], "HIGH": [("R1", 100.0, 2e9)]}   # holder, area km2, assigned $; R3 and R9: no load row
SEAT_KM2 = {"BA": 300.0, "CC": 100.0}


def fake_seat_result(tie=0):
    rows = []
    for est in ("LOW", "HIGH"):
        for seat, usd in SEATS.items():
            for kind, cands in CANDS.items():
                rows += [("SEAT", "S", est, seat, kind, h, rank, b, usd, None, None) for h, rank, b in reversed(cands)]    # worst rank first
        rows += [("SEATS", "S", est, None, None, None, None, None, None, len(SEATS), 0), ("TIE", "S", est, "BA", None, None, None, None, None, tie, 1)]
    return rows


def fake_fit():
    return [("S", est, seat, usd, kind, h, "CRBG", "Y", "WIFI", b, 0.5 + rank, 0.25, -1.5 * rank, rank)
            for est in ("LOW", "HIGH") for seat, usd in SEATS.items() for kind, cands in CANDS.items() for h, rank, b in cands]


def fake_load():
    return [dict(zip(sm.LOAD_COLS, ("S", est, h, "WIFI", "REGIONAL", area, usd, 1e9, 200.0, None, None))) for est, rs in LOADS.items() for h, area, usd in rs]


def _seat(names=NAMES):
    return sm.seat_prepare({"result": (SEAT_COLS, fake_seat_result()), "fit": (FIT_COLS, fake_fit())}, names, fake_load(), SEAT_KM2)


class GapConn(Conn):
    """07's result on execute_stream, the TD_GAP tables and the names on cursor().execute."""
    def __init__(self, summary, seat=None, fit=None, person=None):
        super().__init__([])
        self.summary, self.seat, self.fit, self.person = summary, seat, fit, person

    def execute_stream(self, stream):
        self.streams.append(stream.read())
        if "fake 08" in self.streams[-1]:                   # 08's one result
            return [Cur(SEAT_COLS, self.seat(self.streams[-1]) if callable(self.seat) else self.seat if self.seat is not None else fake_seat_result())]
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
                    cols, self.rows = PERSON_COLS, conn.person or [("S", est, "R1", "CRBG", "NATIONAL", "AA", 1.0, 2) for est in ("LOW", "HIGH")]
                elif "td_seat_fit" in sql:
                    cols, self.rows = FIT_COLS, conn.fit or fake_fit()
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


def test_states_are_adjacent_when_their_shapes_buffered_by_1000_m_meet_and_the_table_is_one_insert():
    geo = fake_geo()
    pairs = sm.state_adjacency(geo.states)
    adj = {}
    for a, b in pairs:
        adj.setdefault(a, set()).add(b)
    assert adj["AA"] == {"AB", "BA", "BB"} and adj["BB"] == {"AA", "AB", "AC", "BA", "BC", "CA", "CB", "CC"}      # rook and corner
    assert all(a in adj[b] for a, b in pairs) and len(pairs) == sum(len(v) for v in adj.values()) and "AC" not in adj["AA"]
    near = {"X": box(0, 0, 1000, 1000), "Y": box(2999, 0, 4000, 1000), "Z": box(6002, 0, 7000, 1000)}   # X-Y 1,999 m apart, Y-Z 2,002 m
    assert sm.state_adjacency(near) == [("X", "Y"), ("Y", "X")], sm.state_adjacency(near)
    conn = GapConn(GOOD)
    out, old = io.StringIO(), sys.stdout
    sys.stdout = out
    try:
        sm.make_state_adj(conn, geo.states)
    finally:
        sys.stdout = old
    create, insert = conn.queries
    assert create.startswith("CREATE OR REPLACE TABLE ssdb_integration.lr_strategy.td_state_adj (state_a") and "(state_a, state_b) VALUES ('AA', 'AB')" in insert
    assert len(sm.re.findall(r"\('\w\w', '\w\w'\)", insert)) == len(pairs) and "('AB', 'AA')" in insert


def test_load_after_is_the_opportunity_only_load_with_the_seat_added_and_a_band():
    load = {("E", "R1"): dict(zip(sm.LOAD_COLS, ("S", "E", "R1", "WIFI", "REGIONAL", 100.0, 1e9, 1e9, 200.0, None, None))),
            ("E", "R2"): dict(zip(sm.LOAD_COLS, ("S", "E", "R2", "WIFI", "REGIONAL", 50.0, 2e9, 1e9, 200.0, None, None)))}
    # (1e9 + 5e8) / (1e9 x ((100 + 300) / 200) ^ 0.5) = 1.5 / 1.41421 = 1.06066
    ratio, band = sm.load_after(load, "E", "R1", 5e8, 300.0)
    assert abs(ratio - 1.5 / 2 ** 0.5) < 1e-12 and band == "0.8 to 1.25"
    assert sm.load_after(load, "E", "R1", 0.0, 300.0) == (1e9 / (1e9 * 2 ** 0.5), "under 0.8")          # 0.707
    assert sm.load_after(load, "E", "R2", 1e9, 50.0) == (3e9 / (1e9 * 0.5 ** 0.5), "over 1.25")          # (2e9 + 1e9) / (1e9 x (100 / 200) ^ 0.5) = 4.24
    assert sm.load_after(load, "E", "R3", 5e8, 300.0) == (None, "") and sm.load_after(load, "X", "R1", 5e8, 300.0) == (None, "")   # no load row: blank
    assert sm.load_after(load, "E", "R1", 5e8, None) == (None, "")


def test_the_masked_seat_csv_has_no_names_or_sales_and_each_row_once_the_names_csv_has_them():
    one = _seat()
    cols, rows = one.masked
    assert cols == SEAT_COLS + ["LOAD_BAND"] and len(rows) == 32 and {r[0] for r in rows} == {"SEAT"}
    band = {(r[2], r[3], r[4], r[5]): r[-1] for r in rows}
    # R1 (LOW: 100 km2, $1e9, median 200, base $1e9) + BA ($7e8, 300 km2): 1.7e9 / (1e9 x 2 ^ .5) = 1.202; CC ($3e8, 100 km2): 1.3e9 / 1e9 = 1.3
    assert band["LOW", "BA", "NEIGHBOUR", "R1"] == "0.8 to 1.25" and band["LOW", "CC", "NEIGHBOUR", "R1"] == "over 1.25"
    assert band["LOW", "BA", "NEIGHBOUR", "R2"] == "under 0.8"                  # (1e8 + 7e8) / (1e9 x 2.5 ^ .5) = 0.506
    assert band["HIGH", "BA", "NEIGHBOUR", "R1"] == "over 1.25"                 # 2.7e9 / 1.41421e9: the estimate's own load row
    assert band["LOW", "BA", "NEIGHBOUR", "R3"] == "" and band["LOW", "BA", "HOLDER", "R1"] == ""     # no load row; HOLDERs have no band
    with tempfile.TemporaryDirectory() as d:
        masked, names = sm.write_seat_csvs(d, {"A": one, "B": _seat(), "C": sm.seat_prepare({"result": (SEAT_COLS, fake_seat_result()), "fit": (FIT_COLS, fake_fit())},
                                                                                              NAMES, fake_load()[:1], SEAT_KM2)})
        m = list(sm.csv.DictReader(open(masked, encoding="utf-8")))
        n = list(sm.csv.DictReader(open(names, encoding="utf-8")))
    assert not {"NAME", "U", "G", "DNASH", "LOAD_AFTER"} & set(m[0]) and "LOAD_BAND" in m[0]
    # A and B are the same, C has only R1's LOW load row: every row of A and B once ("A B"), the rows C differs in ("C")
    assert collections.Counter(r["SCENARIO"] for r in m) == {"A B C": 28, "A B": 4, "C": 4}      # the 4 rows whose band C lacks differ
    assert {"NAME", "U", "G", "DNASH", "LOAD_AFTER"} <= set(n[0])
    r1 = next(r for r in n if r["SCENARIO"].startswith("A B") and (r["EST_SOURCE"], r["SEAT"], r["KIND"], r["HOLDER"]) == ("LOW", "BA", "NEIGHBOUR", "R1"))
    assert r1["NAME"] == "Ann N" and r1["LOAD_AFTER"] == "1.202" and r1["U"] == "2.5" and r1["DNASH"] == "-3.0"
    h1 = next(r for r in n if (r["EST_SOURCE"], r["SEAT"], r["KIND"], r["HOLDER"]) == ("LOW", "BA", "HOLDER", "R1"))
    assert h1["LOAD_AFTER"] == "" and next(r for r in n if r["HOLDER"] == "R9")["NAME"] == ""      # a key with no name: blank


def test_a_tie_not_zero_refuses_the_seat_output_and_names_the_item():
    sql = "SET scenario    = '';\nselect 'fake 08';\n"
    buf = io.StringIO()
    old, sys.stdout = sys.stdout, buf
    try:
        bad = sm.fetch_seat(GapConn(GOOD, fake_seat_result(tie=2)), "S", sql, _split)
        good = sm.fetch_seat(GapConn(GOOD), "S", sql, _split)
    finally:
        sys.stdout = old
    assert bad is None and "SEAT OUTPUT NOT WRITTEN" in buf.getvalue() and "TIE LOW BA (N 2)" in buf.getvalue() and "SEATS" not in buf.getvalue()
    assert good["result"][0] == SEAT_COLS and good["fit"][0] == FIT_COLS and len(good["fit"][1]) == len(fake_fit())


def test_the_seat_page_lists_the_top_3_of_each_kind_in_rank_order_with_no_sales():
    gd = _gd()
    gd.seat = _seat()
    fig = sm.draw_seat_page(gd, "t", "LOW")
    text = "\n".join(t.get_text() for t in fig.texts)
    ba, cc = (next(t.get_text() for t in fig.texts if t.get_text().startswith(seat)).split("\n") for seat in ("BA", "CC"))
    assert text.index("BA   ") < text.index("CC   ")                         # the bigger seat first
    assert ba[0] == "BA   \\$700.0 MM" and cc[0] == "CC   \\$300.0 MM"       # $ escaped for mathtext
    want = ["N1 R3 Cy W", "N2 R1 Ann N", "N3 R2 Bo R", "H1 R2 Bo R", "H2 R3 Cy W", "H3 R1 Ann N"]
    assert len(ba) == 8 and all(l.strip().startswith(w) for l, w in zip(ba[1:7], want)), ba          # 3 + 3, rank 4 (R9) left out
    assert "borders" in ba[1] and "borders" in ba[2] and "borders" not in ba[3] and ba[2].rstrip().endswith("0.8 to 1.25") and ba[3].rstrip().endswith("under 0.8")
    assert ba[1].rstrip().endswith("borders")                                  # R3 has no load row: no band
    assert "R9" not in text and not {"U", "G", "DNASH"} & set(text.split()) and "-1.5" not in text and "0.25" not in text
    other = sm.draw_seat_page(gd, "t", "HIGH")
    assert next(t.get_text() for t in other.texts if t.get_text().startswith("BA")).split("\n")[2].rstrip().endswith("over 1.25")   # R1 HIGH
    gd.seat = None
    none = sm.draw_seat_page(gd, "t", "LOW")
    assert "No open-seat ranking" in none.texts[-1].get_text() and none.get_suptitle() == "t"
    geo = fake_geo()
    sm._init(geo)
    gd.seat_pages = True
    refused = [t for t, _ in sm.gap_pages("S", gd, geo)]                      # 08 ran for the run, refused for this scenario: the pages say so
    gd.seat = _seat()
    drawn = [t for t, _ in sm.gap_pages("S", gd, geo)]
    assert refused == drawn and len(drawn) == 103 and drawn[1:3] == [f"D overlaps and gaps · seat fit · {e} estimate" for e in ("HIGH", "LOW")]
    assert len(list(sm.gap_pages("S", _gd(), geo))) == 101                      # no 08 in the run: no seat pages


def test_main_writes_the_four_csvs_and_the_gaps_pdf_and_skips_when_07_is_missing():
    import types
    fake = {"snowflake": types.ModuleType("snowflake"), "snowflake.connector": types.ModuleType("snowflake.connector"),
            "snowflake.connector.util_text": types.ModuleType("snowflake.connector.util_text")}
    fake["snowflake.connector.util_text"].split_statements = _split
    saved = {k: sys.modules.get(k) for k in fake}
    sys.modules.update(fake)
    keep = {k: getattr(sm, k) for k in ("connect", "load_geo", "fetch_scenario", "MAPS_DIR", "SQL07", "SQL08", "EDITS", "CHUNK", "assemble")}
    labels = []
    sm.assemble = lambda path, pages: (labels.extend(l for _, l in pages), keep["assemble"](path, pages))[1]

    class Ctx:
        def __init__(self, conn): self.conn = conn
        def __enter__(self): return self.conn
        def __exit__(self, *a): return False

    def run(summary, sql07, scen="CA1_R105N", roster=None, sql08=os.path.join(tempfile.gettempdir(), "08_does_not_exist.sql"), seat=None, extra=(), fit=None, person=None):
        with tempfile.TemporaryDirectory() as d:
            sm.MAPS_DIR, sm.SQL07, sm.SQL08, sm.EDITS = d, sql07, sql08, os.path.join(d, "none.sql")
            sm.connect = lambda: Ctx(GapConn(summary, seat, fit, person))
            sm.load_geo = lambda conn: fake_geo()
            sm.fetch_scenario = lambda conn, name, *a: (roster(name) if roster else ROSTER, fake_pieces())
            buf = type("Out", (io.StringIO,), {"reconfigure": lambda self, **kw: None})()
            old, sys.stdout = sys.stdout, buf
            try:
                rc = sm.main(["--scenario", scen, "--jobs", "1", *extra])
            finally:
                sys.stdout = old
            files = sorted(f for _, _, fs in os.walk(d) for f in fs)
            run_dir = next(os.path.join(d, x) for x in os.listdir(d) if os.path.isdir(os.path.join(d, x)))
            run.folder = os.path.basename(run_dir)
            pdfs = {f: len(sm.re.findall(rb"/Type\s*/Page[^s]", open(os.path.join(run_dir, f), "rb").read())) for f in files if f.endswith(".pdf")}
            csv_rows = {f: len(open(os.path.join(run_dir, f), encoding="utf-8").read().splitlines()) for f in files if f.endswith(".csv")}
            return rc, buf.getvalue(), files, pdfs, csv_rows

    try:
        f07 = os.path.join(tempfile.gettempdir(), "07_fake_gap.sql")
        with open(f07, "w") as f:
            f.write("SET scenario    = '';\nselect 1;\n")
        f08 = os.path.join(tempfile.gettempdir(), "08_fake_seat.sql")
        with open(f08, "w") as f:
            f.write("SET scenario    = '';\nSET exclude_products = 'FIXED';\nselect 'fake 08';\n")
        gap_files = sorted(f"gap_{k}.csv" for k in ("cell", "pair", "person", "summary", "load"))
        rc, out, files, pdfs, csvs = run(GOOD, f07)                          # CONUS only: 12 map pages, a summary and 6 gap pages
        assert rc == 0 and files == sorted(gap_files + ["dashboard.html", "maps.pdf"]), files          # the dashboard (#153) next to the PDF
        assert pdfs == {"maps.pdf": 12 + 11} and "safe to send to an agent" in out, (pdfs, out)
        assert out.count("08_seat_fit.sql is not in this checkout") == 1 and "seat_fit" not in out.replace("08_seat_fit.sql", "")   # no 08: no seat file, a page saying so
        assert csvs["gap_cell.csv"] == 1 + len(fake_cells()) and csvs["gap_summary.csv"] == 1 + len(GOOD)
        assert out.startswith("products: excluding FIXED") and "(excluding FIXED)" in out and not run.folder.endswith(("-allproducts", "FIXED")), (out, run.folder)
        rc, out, files, pdfs, csvs = run(GOOD, f07, extra=["--include-all-products"])      # no product left out: the folder says so
        assert rc == 0 and out.startswith("products: all products") and run.folder.endswith("-allproducts"), (out, run.folder)
        rc, out, files, pdfs, csvs = run(GOOD, f07, extra=["--exclude-products", "index", "--exclude-products", "rila VARIABLE"])
        assert rc == 0 and "products: excluding INDEX, RILA, VARIABLE" in out and run.folder.endswith("-exINDEX-RILA-VARIABLE"), (out, run.folder)
        try:
            run(GOOD, f07, extra=["--include-all-products", "--exclude-products", "INDEX"])
            raise AssertionError("both switches were accepted")
        except SystemExit:
            pass
        # two scenarios the same: every page and row once
        rc, out, files, pdfs, csvs = run(GOOD, f07, "CA1_R105N,CA2_R105N")
        assert rc == 0 and pdfs == {"maps.pdf": 23} and csvs["gap_cell.csv"] == 1 + len(fake_cells()), (pdfs, csvs)
        # CA2 moves Ann (CRBG, NATIONAL) to WIFI: NATIONAL and REGIONAL pages A, B and C CRBG differ (6 more); C EQH, WH and gaps shared
        moved = lambda name: [r if r[1] != "Ann N" or name == "CA1_R105N" else r[:3] + ("WIFI",) + r[4:] for r in ROSTER]
        rc, out, files, pdfs, csvs = run(GOOD, f07, "CA1_R105N,CA2_R105N", moved)
        assert rc == 0 and pdfs == {"maps.pdf": 23 + 6}, pdfs
        # CA1_R105R's 07 refused: the 12 map pages are all three scenarios', the 7 gap pages the other two's, not "all scenarios"
        labels.clear()
        rc, out, files, pdfs, csvs = run(lambda sql: BAD if "CA1_R105R" in sql else GOOD, f07, "CA1_R105N,CA2_R105N,CA1_R105R")
        assert rc == 1 and pdfs == {"maps.pdf": 23} and labels == ["all scenarios"] * 12 + ["CA1_R105N · CA2_R105N"] * 11, (rc, pdfs, labels)
        # with 08: a summary, 2 seat pages and the 10 FILL and channel pages (13 gap pages); seat_fit.csv is safe to send, the names file is not
        rc, out, files, pdfs, csvs = run(GOOD, f07, sql08=f08)
        assert rc == 0 and files == sorted(gap_files + ["dashboard.html", "maps.pdf", "seat_fit.csv", "seat_fit_names.csv", "seat_plan.csv", "seat_plan_names.csv"]) and pdfs == {"maps.pdf": 12 + 13}, (files, pdfs, out)
        assert csvs["seat_fit.csv"] == 1 + 32 and csvs["seat_fit_names.csv"] == 1 + 32 and "td_state_adj: " in out, csvs
        send, screen = out.split("names and sales: your screen only:")
        assert "seat_fit.csv" in send.split("safe to send to an agent")[1] and "seat_fit_names.csv" not in send and "seat_fit_names.csv" in screen, out
        assert "dashboard.html" not in send and "dashboard.html" in screen, out          # the dashboard holds names: your screen only
        # the optimal plan (seat_optimize.py): one summary line per estimate, seat_plan.csv safe to send (2 estimates x 2 seats, one plan: no holder to re-add), its names file not
        assert "CA1_R105N LOW: re-adds 0 of 48, vacancies 0, plan BA=R2 CC=R9" in out and csvs["seat_plan.csv"] == 1 + 4 and csvs["seat_plan_names.csv"] == 1 + 4, (out, csvs)
        assert "seat_plan.csv" in send.split("safe to send to an agent")[1] and "seat_plan_names.csv" not in send and "seat_plan_names.csv" in screen, out
        rc, out2, files, pdfs, csvs = run(GOOD, f07, "CA1_R105N,CA2_R105N", sql08=f08)      # two scenarios the same: every page and row once
        assert rc == 0 and pdfs == {"maps.pdf": 12 + 13} and csvs["seat_fit.csv"] == 1 + 32 and out2.count("td_state_adj: ") == 1, (pdfs, csvs, out2)
        # CA1_R105R's 08 refused (TIE not 0): its two seat pages say so, the other two share the real ones: 12 + 11 shared + 2 + 2
        bad08 = lambda sql: fake_seat_result(tie=2) if "CA1_R105R" in sql else fake_seat_result()
        rc, out, files, pdfs, csvs = run(GOOD, f07, "CA1_R105N,CA2_R105N,CA1_R105R", sql08=f08, seat=bad08)
        assert rc == 1 and pdfs == {"maps.pdf": 12 + 11 + 4} and "TIE LOW BA (N 2)" in out and csvs["seat_fit.csv"] == 1 + 32, (rc, pdfs, out)
        # an estimate with more open seats than seat_optimize.MAX_SEATS, or a sheet over the roster cap: no plan for it, the line printed,
        # every other output written as in the normal run above, exit 1 (LOW has 15 open seats here, HIGH its 2)
        full = lambda est, n: [("S", est, f"Z{i:02d}", 1e8, "NEIGHBOUR", "R1", "CRBG", "Y", "WIFI", 1, 1.0, 10.0, None, 1) for i in range(n)]
        big = full("LOW", 15) + [r for r in fake_fit() if r[1] == "HIGH" and r[4] == "NEIGHBOUR"]
        rc, out, files, pdfs, csvs = run(GOOD, f07, sql08=f08, fit=big)
        want = sorted(gap_files + ["dashboard.html", "maps.pdf", "seat_fit.csv", "seat_fit_names.csv", "seat_plan.csv", "seat_plan_names.csv"])
        assert rc == 1 and files == want and pdfs == {"maps.pdf": 12 + 13}, (rc, files, pdfs, out)
        assert "SEAT PLAN NOT MADE: CA1_R105N LOW: 15 open seats > 14" in out and "NOT DRAWN: CA1_R105N (seat plan only)" in out and "HIGH: re-adds" in out, out
        assert csvs["seat_plan.csv"] == 1 + 2 and "seat_plan.csv" in out.split("names and sales: your screen only:")[0], csvs      # HIGH's two seats only
        sheet = [("S", est, f"R{i}", "CRBG", "NATIONAL" if i == 1 else "WH", "AA" if i == 1 else "", 1.0, 2) for est in ("LOW", "HIGH") for i in range(1, 51)]
        rc, out, files, pdfs, csvs = run(GOOD, f07, sql08=f08, person=sheet)
        assert rc == 1 and files == want and pdfs == {"maps.pdf": 12 + 13} and out.count("SEAT PLAN NOT MADE: CA1_R105N: 50 people on the sheet > 49") == 1, (rc, files, pdfs, out)
        assert csvs["seat_plan.csv"] == 1 and "re-adds" not in out, csvs
        rc, out, files, pdfs, csvs = run(BAD, f07, sql08=f08)               # 07 refused: 08 does not run, the table is not made
        assert rc == 1 and files == ["maps.pdf"] and pdfs == {"maps.pdf": 12} and "td_state_adj" not in out, (files, out)
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


# ---- the draft assignment (issue #152, phase 2): a made-up keys-only ledger and M1 file on the same 18 box states

DRAFT_NAMES = {"R1": "Ann N", "R2": "Bo R", "R3": "Cy W", "R4": "Di X", "R5": "Ed Y"}
DRAFT_LEDGER_COLS = ["SCENARIO", "ROLE", "ZIP_CODE", "STATE", "PERSON", "REASON"]
DRAFT_M1_COLS = ["SCENARIO", "ROLE", "PERSON", "N_PIECES", "PIECE", "N_ZCTAS", "CRBG_USD", "TAU_SHARE", "VERDICT", "NOTE", "EQH_USD", "TAU_SHARE_EQH"]


def fake_draft():
    """(ledger rows, m1 rows) as dicts.  NATIONAL and REGIONAL are the same in S1 and S2, WH differs.  NATIONAL: R1 has AA and AB, R2 AC,
    R3 BA, R4 CA and CC1 (two pieces, FAIL), R5 CB1; CF1 is unreachable; the other states have no one."""
    def led(sc, role, owner):
        return [dict(zip(DRAFT_LEDGER_COLS, (sc, role, z, z[:2], p, "whole state"))) for z, p in owner.items()]
    nat = {"AA1": "R1", "AA2": "R1", "AB1": "R1", "AB2": "R1", "AC1": "R2", "AC2": "R2", "BA1": "R3", "BA2": "R3",
           "CA1": "R4", "CA2": "R4", "CC1": "R4", "CB1": "R5", "CF1": ""}
    ledger = led("S1 S2", "NATIONAL", nat) + led("S1 S2", "WIFI", {"AA1": "R1", "AA2": "R1", "AB1": "R2", "AB2": "R2"})
    ledger += led("S1", "WH", {"AA1": "R1", "AB1": "R2"}) + led("S2", "WH", {"AA1": "R2", "AB1": "R2"})
    row = lambda sc, role, p, n, i, usd, v, note="": dict(zip(DRAFT_M1_COLS, (sc, role, p, n, i, 5, usd, 1.0, v, note, usd, 1.0)))
    m1 = [row("S1 S2", "NATIONAL", "R1", 1, 1, 2444611470.25, "PASS"), row("S1 S2", "NATIONAL", "R2", 1, 1, 100e6, "PASS"),
          row("S1 S2", "NATIONAL", "R3", 1, 1, 100e6, "PASS"), row("S1 S2", "NATIONAL", "R4", 2, 1, 900e6, "FAIL"),
          row("S1 S2", "NATIONAL", "R4", 2, 2, 100e6, "FAIL"), row("S1 S2", "NATIONAL", "R5", 1, 1, 50e6, "PASS"),
          row("S1 S2", "WIFI", "R1", 1, 1, 10e6, "PASS"), row("S1 S2", "WIFI", "R2", 1, 1, 10e6, "PASS"),
          row("S1", "WH", "R1", 1, 1, 10e6, "PASS"), row("S1", "WH", "R2", 1, 1, 10e6, "PASS"), row("S2", "WH", "R2", 1, 1, 20e6, "PASS")]
    return ledger, m1


def _draft_pages(scenarios=("S1", "S2"), divisions=False):
    ledger, m1 = fake_draft()
    geo = fake_geo()
    if not divisions:
        geo.geographies = geo.geographies[:1]                                 # CONUS only, as the command without --divisions
    return sm.draft_figs(geo, ledger, m1, DRAFT_NAMES, list(scenarios))


def _colour(fig, gid):
    cols = [c for c in fig.axes[0].collections if c.get_gid() == gid]
    assert len(cols) == 1, (gid, len(cols))
    rgba = {tuple(r) for r in cols[0].get_facecolor()}
    assert len(rgba) == 1, f"{gid} is drawn in {len(rgba)} colours"
    return rgba.pop(), len(cols[0].get_paths())


def test_draft_pages_are_one_per_channel_with_the_scenarios_that_share_them_in_the_title():
    per = _draft_pages()
    assert [t for t, _ in per["S1"]] == ["Draft · NATIONAL · S1, S2 · CONUS", "Draft · REGIONAL · S1, S2 · CONUS", "Draft · WH · S1 · CONUS"]
    assert [t for t, _ in per["S2"]][2] == "Draft · WH · S2 · CONUS"
    assert per["S1"][0][1] is per["S2"][0][1] and per["S1"][2][1] is not per["S2"][2][1]          # shared: drawn once
    div = _draft_pages(divisions=True)["S1"]                                                          # with --divisions: 3 channels x (CONUS + 9)
    assert len(div) == 30 and div[3][0] == "Draft · NATIONAL · S1, S2 · D1" and div[-1][0] == "Draft · WH · S1 · D9"
    for _, fig in (x for v in per.values() for x in v):
        assert fig.get_suptitle() == [t for t, f in per["S1"] + per["S2"] if f is fig][0]
        assert any("Pieces per M1 on the drawn 2025 ZCTA graph." in t.get_text() for t in fig.texts)
        assert any("provisional until bargaining (#149)" in t.get_text() for t in fig.texts)


def test_each_persons_zctas_are_one_colour_and_touching_people_differ():
    fig = _draft_pages()["S1"][0][1]
    brand = {tuple(sm.to_rgba(c)) for c in sm.BRAND}
    colour = {}
    for p, n in (("R1", 4), ("R2", 2), ("R3", 2), ("R4", 3), ("R5", 1)):
        colour[p], got = _colour(fig, p)
        assert got == n and colour[p] in brand, (p, got)
    for a, b in (("R1", "R2"), ("R1", "R3"), ("R3", "R4"), ("R4", "R5")):    # AB-AC, AA-BA, BA-CA, CA2-CB1 touch
        assert colour[a] != colour[b], (a, b)
    again = _draft_pages()["S1"][0][1]
    assert _colour(again, "R1")[0] == colour["R1"]                            # deterministic: the same page is the same picture


def test_states_with_no_one_in_the_role_are_white_and_unreachable_zctas_black():
    fig = _draft_pages()["S1"][0][1]
    (open_,) = [c for c in fig.axes[0].collections if c.get_gid() == "open"]
    assert [tuple(r) for r in open_.get_facecolor()] == [(1.0, 1.0, 1.0, 1.0)] and len(open_.get_paths()) == 18 - 7   # AA AB AC BA CA CB CC have people
    assert tuple(open_.get_edgecolor()[0]) == tuple(sm.to_rgba(sm.OPEN_EDGE))
    assert _colour(fig, "unreachable") == ((0.0, 0.0, 0.0, 1.0), 1)
    assert "open in this role" in [t.get_text() for t in fig.legends[0].get_texts()]
    assert "unreachable ZCTAs (1)" in [t.get_text() for t in fig.legends[0].get_texts()]


def test_the_legend_has_key_name_verdict_pieces_and_dollars_and_each_person_is_labelled_once_on_the_largest_piece():
    fig = _draft_pages()["S1"][0][1]
    legend = [t.get_text() for t in fig.legends[0].get_texts()]
    assert "R1 Ann N\nPASS · 1 piece · \\$2,445 MM CRBG" in legend, legend                   # $ escaped for mathtext, $MM of CRBG_USD
    assert "R4 Di X\nFAIL · 2 pieces · \\$1,000 MM CRBG" in legend, legend
    labels = [t for t in fig.axes[0].texts if t.get_text().startswith("R")]
    assert sorted(t.get_text() for t in labels) == ["R1 Ann N", "R2 Bo R", "R3 Cy W", "R4 Di X", "R5 Ed Y"]
    r4 = next(t for t in labels if t.get_text().startswith("R4"))
    assert abs(r4.xy[0] - S / 2) < S / 4 + 1 and abs(r4.xy[1] - 2.5 * S) < S / 4 + 1, r4.xy      # CA's pair of ZCTAs, not CC1 (x 2S)


def test_main_reads_the_names_from_the_query_and_writes_one_pdf_with_each_shared_page_once():
    import gzip
    import types
    keep = {k: getattr(sm, k) for k in ("connect", "load_geo", "MAPS_DIR")}
    seen = []

    class Ctx:
        def __init__(self, rows): self.rows = rows
        def __enter__(self):
            conn, rows = self, self.rows

            class C(Cur):
                def execute(self, sql):
                    seen.append(sql)
                    self.rows = rows
            self.cursor = lambda: C()
            return self
        def __exit__(self, *a): return False

    def run(argv, rows):
        with tempfile.TemporaryDirectory() as d:
            ledger, m1 = fake_draft()
            src = os.path.join(d, "draft")
            os.makedirs(src)
            with gzip.open(os.path.join(src, "draft_ledger.csv.gz"), "wt", encoding="utf-8", newline="") as f:
                w = sm.csv.DictWriter(f, DRAFT_LEDGER_COLS)
                w.writeheader()
                w.writerows(ledger)
            with open(os.path.join(src, "draft_m1.csv"), "w", encoding="utf-8", newline="") as f:
                w = sm.csv.DictWriter(f, DRAFT_M1_COLS)
                w.writeheader()
                w.writerows(m1)
            sm.MAPS_DIR = os.path.join(d, "maps")
            sm.connect = lambda: Ctx(rows)
            sm.load_geo = lambda conn: fake_geo()
            buf = type("Out", (io.StringIO,), {"reconfigure": lambda self, **kw: None})()
            old, sys.stdout = sys.stdout, buf
            try:
                rc = sm.main(["--draft", src] + argv)
            finally:
                sys.stdout = old
            files = sorted(os.path.relpath(os.path.join(r, f), sm.MAPS_DIR) for r, _, fs in os.walk(sm.MAPS_DIR) for f in fs)
            pdf = next(os.path.join(sm.MAPS_DIR, f) for f in files)
            return rc, buf.getvalue(), files, len(sm.re.findall(rb"/Type\s*/Page[^s]", open(pdf, "rb").read()))

    try:
        names = list(DRAFT_NAMES.items())
        rc, out, files, pages = run([], names)
        assert rc == 0 and len(files) == 1 and files[0].endswith("draft.pdf") and pages == 4, (rc, files, pages)      # 3 shared + WH of S2
        assert os.path.join(sm.MAPS_DIR, files[0]) in out.replace("\\", os.sep) or files[0].replace("\\", "/") in out.replace("\\", "/"), out
        assert len(seen) == 1 and "td_holder_key" in seen[0] and "td_assignments" in seen[0]                           # one names query, no 03, 04 or 07
        rc, out, files, pages = run(["--scenario", "S1"], names)
        assert rc == 0 and pages == 3, (rc, pages)
        rc, out, files, pages = run([], names[:4])                                                                       # R5 has no name: said, and drawn by key
        assert rc == 1 and "NO NAME for R5" in out and pages == 4, out
        try:
            run(["--scenario", "NOPE"], names)
            raise AssertionError("no error for an unknown scenario")
        except SystemExit:
            pass
    finally:
        for k, v in keep.items():
            setattr(sm, k, v)


def test_the_ps1_passes_draft_and_the_scenarios_to_python():
    ps1 = (ROOT / "tools" / "maps" / "scenario_maps.ps1").read_text(encoding="utf-8")
    assert "[string]$Draft" in ps1 and '"--draft", $Draft' in ps1 and "if ($Draft)" in ps1
    assert ps1.index("if ($Draft)") < ps1.index("elseif ($List)")                                                       # draft before the 03 modes
    assert ps1.count('"--scenario"; $_') == 2                                                                         # -Scenario works with -Draft


if __name__ == "__main__":
    for k, v in list(globals().items()):
        if k.startswith("test_"):
            v()
            print("ok", k)


def test_draft_refuses_product_switches():
    for extra in (["--include-all-products"], ["--exclude-products", "FIXED"]):
        try:
            sm.main(["--draft", "x"] + extra)
            raise AssertionError(f"no error for --draft with {extra}")
        except SystemExit as e:
            assert e.code == 2, e.code                                # argparse's usage error, before anything is read
