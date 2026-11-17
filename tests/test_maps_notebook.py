"""tools/snowflake/05_maps.ipynb: the notebook runs on Python 3.12 (owner, 2026-11-17); every code cell also parses as Python 3.9
(the stricter, older bound), the setup cell stops naming a package that cannot be imported, and its drawing cell,
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
    # the lower bound: the notebook targets 3.12, but the older 3.9 grammar is the stricter parse and stays harmless
    for i, src in enumerate(_cells()):
        ast.parse(src, f"cell {i}", feature_version=(3, 9))
        compile(src, f"cell {i}", "exec")


def test_the_setup_cell_names_the_uploads():
    setup = _cells()[0]
    assert "td_maps" in setup and "look.py" in setup and "areas.csv.gz" in setup and "session.file.get" in setup
    assert "upload tools/maps/look.py and" in setup and "reference/2025/areas.csv.gz" in setup


def test_the_setup_cell_stops_naming_the_missing_package():
    setup = _cells()[0]
    check = setup[:setup.index("from snowflake")]       # the version printout, before the Snowflake session
    assert "sys.version" in check and "pip install geopandas" in check
    for pkg in ("matplotlib", "shapely", "pyproj", "geopandas", "pandas"):
        assert f'"{pkg}"' in check
    saved = sys.modules.get("geopandas", ...)
    sys.modules["geopandas"] = None                      # makes `import geopandas` raise ImportError
    try:
        exec(compile(check, "setup check", "exec"), {})
        raise AssertionError("no error for the missing geopandas")
    except RuntimeError as e:
        assert str(e).startswith("geopandas cannot be imported") and "Packages" in str(e) and "pip install geopandas" in str(e)
    finally:
        if saved is ...:
            del sys.modules["geopandas"]
        else:
            sys.modules["geopandas"] = saved


def _drawing(n=4):
    """(look, drawing-cell namespace, ctx): `n` ZIPs 00001.. as squares 0.1 degree apart in a CO / KS frame."""
    import geopandas as gpd
    from shapely.geometry import box

    look = _load_look()
    ns = {"look": look}
    exec(next(c for c in _cells() if c.startswith("# Drawing")), ns)
    sq = lambda x, y: box(-100 + x, 40 + y, -99.9 + x, 40.1 + y)
    zips = [f"{i + 1:05d}" for i in range(n)]
    shapes = gpd.GeoSeries([sq(0, 0), sq(0.1, 0), sq(5, 0), sq(0, 0.1)] + [sq(0.2 * i, 0.5) for i in range(max(n - 4, 0))],
                           crs="EPSG:4326").to_crs(epsg=5070)
    polys = dict(zip(zips, shapes))
    st = dict(zip(["CO", "KS"], gpd.GeoSeries([box(-102, 39, -99.95, 41), box(-99.95, 39, -94, 41)], crs="EPSG:4326").to_crs(epsg=5070)))
    ctx = SimpleNamespace(polys=polys, st=st, gap=look.no_zcta_land(polys, st), weights={"A": {"31000": 9e6}, "B": {"31000": 7e6}},
                          areas={"31000": ("Testville, CO Metro Area", -99.9, 40.05)})
    return look, ns, ctx


def test_the_drawing_cell_writes_both_pdfs():
    import pandas as pd

    look, ns, ctx = _drawing()
    zips = list(ctx.polys)
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


def _paths(fig, hatched=False):
    """The ZIP outlines the page's main map draws in a collection of z-order 2 (kept) or 1 with a hatch (open): their bounds."""
    ax = fig.axes[0]
    cs = [c for c in ax.collections if (c.get_hatch() if hatched else c.get_zorder() == 2)]
    return [tuple(round(v) for v in p.get_extents().extents) for c in cs for p in c.get_paths()]


def test_the_read_cell_keeps_aks_and_his_out_of_the_territory_query():
    read = _cells()[1]
    assert "WHERE terr_channel IN ('WH', 'FI') AND COALESCE(state, '') NOT IN ({nc})" in read


def test_the_fifths_draw_every_positive_zip_once_whatever_the_labels():
    import pandas as pd

    look, ns, ctx = _drawing(9)
    zips = list(ctx.polys)
    for vals in ([1, 2, 3, 4, 5], [3, 3, 3, 3, 3], [1e-9, 2e-9, 3e-9, 4e-9, 5e-9], [5, 5, 7, 7, 7], [0, 4, 4, 0, 9]):
        df = pd.DataFrame({"ZIP_CODE": zips[:5], "V": vals})
        cats, colours = ns["fifths"](df, "V", "Blues", ctx.polys)
        drawn = sorted(z for zs in cats.values() for z in zs)
        assert drawn == sorted(df.loc[df["V"] > 0, "ZIP_CODE"]), (vals, cats)
        assert set(cats) == set(colours) and len(cats) == min(5, sum(v > 0 for v in vals))
    # the page itself: one outline per positive ZIP
    cats, colours = ns["fifths"](pd.DataFrame({"ZIP_CODE": zips[:5], "V": [1e-9, 2e-9, 3e-9, 4e-9, 5e-9]}), "V", "Blues", ctx.polys)
    fig = ns["category_page"]("t", cats, colours, ctx, ["A"], ["c"])
    assert len(_paths(fig)) == 5


def test_the_territory_page_paints_each_zip_once_as_its_first_kept_holder_in_a_stable_legend():
    import pandas as pd

    look, ns, ctx = _drawing(7)
    z = list(ctx.polys)
    row = lambda w, k, zz: dict(SOURCE="A", WHOLESALER=w, KEPT=k, ZIP_CODE=zz, TERR_CHANNEL="WH")
    # Ann: z0, z1, z2; Bob (kept) also z1, z3; Cal (not kept): z1, z2, z4; Dee (not kept) alone on z5; z6 is held by Cal only
    terr = pd.DataFrame([row("Ann", "Y", z[0]), row("Ann", "Y", z[1]), row("Ann", "Y", z[2]), row("Bob", "Y", z[1]),
                         row("Bob", "Y", z[3]), row("Cal", "N", z[1]), row("Cal", "N", z[2]), row("Cal", "N", z[4]),
                         row("Dee", "N", z[5]), row("Cal", "N", z[6]), row("Ann", "Y", z[0])])
    figs = list(ns["territory_pages"](terr, ctx))
    assert len(figs) == 1
    kept = _paths(figs[0])
    # kept-held ZIPs z0..z3, each once, though z1 and z2 are also held by a not-kept holder
    assert sorted(kept) == sorted(tuple(round(v) for v in ctx.polys[k].bounds) for k in z[:4])
    # the hatched open layer is the not-kept-only ZIPs z4, z5, z6, not z1 or z2
    hatch = [pp for c in figs[0].axes[0].collections if c.get_hatch() for pp in c.get_paths()]
    covered = lambda k: any(pp.contains_point(ctx.polys[k].representative_point().coords[0]) for pp in hatch)
    assert [covered(k) for k in z] == [False] * 4 + [True] * 3
    assert "7 ZIPs: 4 held by the 2 kept wholesalers, 3 only by a wholesaler not kept.  2 ZIPs with 2 holders" in figs[0].texts[1].get_text()
    legend = lambda f: [t.get_text() for t in f.legends[0].get_texts()]
    marks = lambda f: sorted((t.get_text(), round(t.get_position()[0]), round(t.get_position()[1])) for t in f.axes[0].texts)
    shuffled = list(ns["territory_pages"](terr.sample(frac=1, random_state=3).reset_index(drop=True), ctx))[0]
    assert legend(shuffled)[:2] == ["01 Ann", "02 Bob"] == legend(figs[0])[:2]
    assert legend(shuffled) == legend(figs[0]) and marks(shuffled) == marks(figs[0])
