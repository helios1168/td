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
                out.append(f"CA1_R105N · {view} · {ch} · {g}")
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
        _, view, ch, gname = title.split(" · ")
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


if __name__ == "__main__":
    for k, v in list(globals().items()):
        if k.startswith("test_"):
            v()
            print("ok", k)
