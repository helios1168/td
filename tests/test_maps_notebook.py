"""tools/snowflake/05_maps.ipynb: its drawing cell, run here on made-up tables shaped like the 04 tables, writes both PDFs
with the expected page counts.  The setup, read and run cells need Snowflake and are only checked to compile."""
import json
import os
import pathlib
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
NB = ROOT / "tools" / "snowflake" / "05_maps.ipynb"


def _cells():
    return ["".join(c["source"]) for c in json.loads(NB.read_text())["cells"] if c["cell_type"] == "code"]


def test_every_code_cell_compiles():
    for i, src in enumerate(_cells()):
        compile(src, f"cell {i}", "exec")


def test_the_drawing_cell_writes_both_pdfs():
    import geopandas as gpd
    import pandas as pd
    from shapely.geometry import box

    ns = {}
    exec(_cells()[2], ns)
    sq = lambda x, y: box(-100 + x, 40 + y, -99.9 + x, 40.1 + y)
    zips = gpd.GeoDataFrame({"ZIP_CODE": ["00001", "00002", "00003"]}, geometry=[sq(0, 0), sq(0.1, 0), sq(5, 0)],
                            crs="EPSG:4326").to_crs(epsg=5070)
    states = gpd.GeoDataFrame({"FIPS": ["08", "20"], "NAME": ["Colorado", "Kansas"]},
                              geometry=[box(-102, 39, -99.95, 41), box(-99.95, 39, -94, 41)], crs="EPSG:4326").to_crs(epsg=5070)
    zip_role = pd.DataFrame({"ZIP_CODE": ["00001", "00002", "00003"], "ROLE": ["WIFI", "WIFI", "WIFI"],
                             "N_ROLE_HOLDERS": [2, 1, 4], "N_ROLE_FIRMS": [2, 1, 2]})
    zip_cell = pd.DataFrame({"EST_SOURCE": ["A", "A", "B"], "ZIP_CODE": ["00001", "00003", "00001"], "OPP": [10e6, 5e6, 7e6],
                             "OPP_IN_ROLE": [10e6, 0, 7e6], "OPP_OUT_OF_ROLE": [0, 0, 0], "OPP_OPEN": [0, 5e6, 0],
                             "OPP_NO_HOLDER": [0, 0, 0]})
    zip_sales = pd.DataFrame({"SOURCE": ["A"], "ZIP_CODE": ["00001"], "SALES": [1e6]})
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
    out = tempfile.mkdtemp()
    over = ns["write_pdf"](os.path.join(out, "o.pdf"), ns["overview_pages"](zips, states, zip_role, zip_cell, zip_sales))
    whol = ns["write_pdf"](os.path.join(out, "w.pdf"), ns["wholesaler_pages"](zips, states, zip_role, pieces, wsum))
    # overview: 1 role, 2 estimates x (status, opportunity), 1 sales source.  Wholesalers: Ann and Bob
    assert (over, whol) == (6, 2)
    assert os.path.getsize(os.path.join(out, "w.pdf")) > 1000
