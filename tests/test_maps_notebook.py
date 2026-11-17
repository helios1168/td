"""tools/snowflake/05_maps.ipynb: every code cell parses as Python 3.9 (the Snowflake warehouse runtime), and its drawing cell,
run here on made-up tables shaped like the 04 tables, writes both PDFs with the expected page counts.  The setup, read and run
cells need Snowflake and are only checked to parse.  The drawing cell takes the shared look from `look`: tools/maps/look.py
when it exists, else tools/maps/zip_pages.py (the same names)."""
import ast
import importlib.util
import json
import os
import pathlib
import sys
import tempfile
from types import SimpleNamespace

ROOT = pathlib.Path(__file__).resolve().parents[1]
NB = ROOT / "tools" / "snowflake" / "05_maps.ipynb"
MAPS = ROOT / "tools" / "maps"


def _cells():
    return ["".join(c["source"]) for c in json.loads(NB.read_text())["cells"] if c["cell_type"] == "code"]


def _load_look():
    path = MAPS / "look.py" if (MAPS / "look.py").exists() else MAPS / "zip_pages.py"
    spec = importlib.util.spec_from_file_location("look", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["look"] = mod
    spec.loader.exec_module(mod)
    if not hasattr(mod, "polygon_path"):    # zip_pages takes td/output.py's helper
        mod.polygon_path = mod._polygon_path
    return mod


def test_every_code_cell_parses_as_python_39():
    for i, src in enumerate(_cells()):
        ast.parse(src, f"cell {i}", feature_version=(3, 9))
        compile(src, f"cell {i}", "exec")


def test_the_setup_cell_names_the_uploads():
    setup = _cells()[0]
    assert "td_maps" in setup and "look.py" in setup and "areas.csv.gz" in setup and "session.file.get" in setup
    assert "upload tools/maps/look.py and" in setup and "reference/2025/areas.csv.gz" in setup


def test_the_drawing_cell_writes_both_pdfs():
    import geopandas as gpd
    import pandas as pd
    from shapely.geometry import box

    look = _load_look()
    ns = {"look": look}
    exec(next(c for c in _cells() if c.startswith("# Drawing")), ns)
    sq = lambda x, y: box(-100 + x, 40 + y, -99.9 + x, 40.1 + y)
    zips = ["00001", "00002", "00003", "00004"]
    shapes = gpd.GeoSeries([sq(0, 0), sq(0.1, 0), sq(5, 0), sq(0, 0.1)], crs="EPSG:4326").to_crs(epsg=5070)
    polys = dict(zip(zips, shapes))
    st = dict(zip(["CO", "KS"], gpd.GeoSeries([box(-102, 39, -99.95, 41), box(-99.95, 39, -94, 41)], crs="EPSG:4326").to_crs(epsg=5070)))
    ctx = SimpleNamespace(polys=polys, st=st, gap=look.no_zcta_land(polys, st), weights={"A": {"31000": 9e6}, "B": {"31000": 7e6}},
                          areas={"31000": ("Testville, CO Metro Area", -99.9, 40.05)})
    zip_role = pd.DataFrame({"ZIP_CODE": zips[:3], "ROLE": ["WIFI"] * 3, "N_ROLE_HOLDERS": [2, 1, 4], "N_ROLE_FIRMS": [2, 1, 2]})
    zip_cell = pd.DataFrame({"EST_SOURCE": ["A", "A", "B"], "ZIP_CODE": ["00001", "00003", "00001"], "OPP": [10e6, 5e6, 7e6],
                             "OPP_IN_ROLE": [10e6, 0, 7e6], "OPP_OUT_OF_ROLE": [0, 0, 0], "OPP_OPEN": [0, 5e6, 0],
                             "OPP_NO_HOLDER": [0, 0, 0]})
    zip_sales = pd.DataFrame({"SOURCE": ["A"], "ZIP_CODE": ["00001"], "SALES": [1e6]})
    # firm A WH: Ann (00001, 00002), Bob (00002 too: two holders, 00003), Cal not kept (00004); A FI: Bob; B WH: Ann; B FI: none
    row = lambda s, w, k, z, c: dict(SOURCE=s, WHOLESALER=w, KEPT=k, ZIP_CODE=z, TERR_CHANNEL=c)
    terr = pd.DataFrame([row("A", "Ann", "Y", "00001", "WH"), row("A", "Ann", "Y", "00002", "WH"), row("A", "Bob", "Y", "00002", "WH"),
                         row("A", "Bob", "Y", "00003", "WH"), row("A", "Cal", "N", "00004", "WH"), row("A", "Bob", "Y", "00003", "FI"),
                         row("B", "Ann", "Y", "00001", "WH")])
    pieces = pd.DataFrame({"SOURCE": ["A", "A", "A"], "WHOLESALER": ["Ann", "Ann", "Bob"], "ROLE": ["WIFI"] * 3,
                           "ZIP_CODE": ["00001", "00002", "00003"], "STATE": ["CO", "KS", "KS"], "TERR_CHANNEL": ["WH", "IFA", "FI"],
                           "PIECE_IN_ROLE": [1, 0, 1], "IN_ASSIGNED_STATE": [1, 0, None], "N_ROLE_HOLDERS": [2, None, 4]})
    w = dict(KEPT="Y", ROLE="WIFI", N_ZIPS=2, N_ZIPS_IN_ROLE=1, OPP_MAIN=10e6, OPP_IN_ROLE=10e6, OPP_OUT_OF_ROLE=0, OPP_OVERLAP=10e6)
    wsum = pd.DataFrame([dict(w, SOURCE="A", WHOLESALER="Ann", ASSIGNED_STATES="CO", STATES="CO KS", EST_SOURCE="A",
                              OPP_IN_ASSIGNED_STATES=10e6, SALES_MAIN=1e6, SALES_MAIN_IN_OWN_ZIPS=1e6),
                         dict(w, SOURCE="A", WHOLESALER="Ann", ASSIGNED_STATES="CO", STATES="CO KS", EST_SOURCE="B",
                              OPP_IN_ASSIGNED_STATES=7e6, SALES_MAIN=None, SALES_MAIN_IN_OWN_ZIPS=None),
                         dict(w, SOURCE="A", WHOLESALER="Bob", ASSIGNED_STATES="", STATES="KS", EST_SOURCE="A",
                              OPP_IN_ASSIGNED_STATES=None, SALES_MAIN=0.0, SALES_MAIN_IN_OWN_ZIPS=0.0)])
    assert ns["metro_weights"](zip_cell.assign(ZIP_CODE="00001"), pd.DataFrame({"ZIP_CODE": ["00001"], "CBSA": ["31000"]})) == \
        {"A": {"31000": 15e6}, "B": {"31000": 7e6}}
    out = tempfile.mkdtemp()
    figs = list(ns["territory_pages"](terr, ctx))
    assert [f._suptitle.get_text() for f in figs] == ["A WH territories today: 2 kept wholesalers",
                                                      "A FI territories today: 1 kept wholesalers",
                                                      "B WH territories today: 1 kept wholesalers"]
    assert "1 ZIPs with 2 holders in A WH" in figs[0].texts[1].get_text()
    over = ns["write_pdf"](os.path.join(out, "o.pdf"), figs + list(ns["overview_pages"](zip_role, zip_cell, zip_sales, ctx)))
    whol = ns["write_pdf"](os.path.join(out, "w.pdf"), ns["wholesaler_pages"](pieces, wsum, ctx, zip_role))
    # territories: A WH, A FI, B WH; overview: 1 role, 2 estimates x (status, opportunity), 1 sales source.  Wholesalers: Ann and Bob
    assert (over, whol) == (9, 2)
    assert os.path.getsize(os.path.join(out, "w.pdf")) > 1000
