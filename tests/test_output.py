"""td.output: the ledger, its schema, the district names, the maps and the run's stops (#71).

The toy run uses real 2025 ZCTAs (Manhattan, Newark, Philadelphia, Greenwich) from the committed
reference table on a hand-drawn ZIP graph, so its CBSAs, names and principal cities are real and
it needs no download: NY holds one district, NJ + PA the other, CT has no opportunity and is
dropped, channel Y has none and is dropped whole, and one Philadelphia ZIP is not a graph vertex.
Its maps read a synthetic ZCTA520 file (`_synthetic_public`): a 2 km square per ZCTA, written
under the real file's name and field, so the map code reads it as it reads the national file.
One test reads the real TIGER/Line 2025 ZCTA520 file (`data/public/` or `$TD_REPO`'s; SKIP
without).  The schema test reads the tagged `scenarios.csv` header with git (SKIP without the tag).
"""
from __future__ import annotations

import collections
import contextlib
import csv
import functools
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

from td import audit, data, geo, master, output, spec

from tests import test_spec as ts

NY, NJ, PA, CT = ("10001", "10002", "10003", "10004"), ("07102", "07103", "07104", "07105"), \
    ("19103", "19104", "19106", "19107"), ("06830", "06831")
OFF = "19108"                   # in the extract, not a vertex of the toy graph
MASS = {**dict.fromkeys(NY, 1.0), **dict.fromkeys(NJ, 0.375), **dict.fromkeys(PA, 0.625),
        **dict.fromkeys(CT, 0.0), OFF: 0.5}


def _toy_spec(**channel):
    raw = {"scenario": {"name": "toy", "fine_channels": ["f", "g"]},
           "channels": {"X": {"k": 2, "domain": [{"units": "all", "fine": ["f"]}], "eta": 0.1,
                              "max_dist_km": 1e9, **channel},
                        "Y": {"k": 1, "domain": [{"units": "all", "fine": ["g"]}], "eta": 0.1}}}
    return spec.parse(raw)


def _toy_inputs():
    """(extract, graph): every ZIP in f with MASS and in g with 0; chains inside each state and
    the edges NY-NJ, NJ-PA, NY-CT."""
    zs = sorted(MASS)
    extract = data.Extract(("f", "g"), [z for z in zs for _ in "fg"], [f for _ in zs for f in "fg"],
                           [m for z in zs for m in (MASS[z], 0.0)], [{}] * 2 * len(zs),
                           [0.0] * 2 * len(zs))
    edges = [(a, b) for st in (NY, NJ, PA, CT) for a, b in zip(st, st[1:])]
    edges += [(NY[-1], NJ[0]), (NJ[-1], PA[0]), (NY[0], CT[0])]
    return extract, {"vertices": sorted(set(zs) - {OFF}), "edges": edges}


def _synthetic_public(zips) -> str:
    """A temp `public` dir whose `tl_2025_us_zcta520.zip` holds a 2 km square, in `geo.CRS`, around
    each of `zips`' 2025 reference points, with the real file's `ZCTA5CE20` field."""
    import zipfile
    import geopandas as gpd
    from shapely.geometry import box
    at = ts._reference().set_index("zcta")
    xy = [(float(at.at[z, "x"]), float(at.at[z, "y"])) for z in sorted(zips)]
    gdf = gpd.GeoDataFrame({"ZCTA5CE20": sorted(zips)},
                           geometry=[box(x - 1000, y - 1000, x + 1000, y + 1000) for x, y in xy],
                           crs=geo.CRS)
    public, shp = tempfile.mkdtemp(prefix="td-public-"), tempfile.mkdtemp(prefix="td-shp-")
    gdf.to_file(os.path.join(shp, "tl_2025_us_zcta520.shp"), engine="pyogrio")
    with zipfile.ZipFile(os.path.join(public, output.ZCTA_FILE), "w") as zf:
        for f in os.listdir(shp):
            zf.write(os.path.join(shp, f), f)
    shutil.rmtree(shp)
    return public


@functools.cache
def _toy_public():
    return _synthetic_public(set(MASS))


@functools.cache
def _toy_run():
    out = tempfile.mkdtemp(prefix="td-output-")
    os.rmdir(out)                       # a run makes its own directory
    extract, graph = _toy_inputs()
    res = output.run(_toy_spec(), extract, out, graph, ts._reference(), _toy_public(), source="toy")
    return res, output.read_ledger(res.paths["ledger"])


@contextlib.contextmanager
def _saved_figures():
    """[(path, figure)] for every figure saved inside the block: the maps' axes, read back."""
    from matplotlib.figure import Figure
    saved, save = [], Figure.savefig

    def spy(fig, path, *args, **kw):
        saved.append((path, fig))
        return save(fig, path, *args, **kw)
    Figure.savefig = spy
    try:
        yield saved
    finally:
        Figure.savefig = save


def _real_zcta_public():
    for public in (geo.PUBLIC_DIR, os.path.join(os.environ.get("TD_REPO", ""), "data", "public")):
        if output.zcta_file(public):
            return public
    print(f"SKIP  test_output.py: no {output.ZCTA_FILE} in data/public or $TD_REPO/data/public; "
          "the real-polygon map test did not run", file=sys.stderr)
    return None


def _tag_header():
    try:
        p = subprocess.Popen(["git", "show", f"{audit.TAG}:scenarios.csv"], cwd=geo.ROOT,
                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        line = p.stdout.readline()
        p.kill()
        p.wait()
    except OSError:
        line = ""
    if not line:
        print(f"SKIP  test_output.py: no {audit.TAG}:scenarios.csv; the schema test did not run",
              file=sys.stderr)
        return None
    return line.strip().split(",")


# ------------------------------------------------------------------------------ the ledger
def test_the_ledger_keeps_the_tagged_scenarios_csv_columns_in_order():
    head = _tag_header()
    if head is None:
        return
    assert head == list(output.LEGACY_COLUMNS), head
    res, _ = _toy_run()
    with open(res.paths["ledger"], encoding="utf-8") as fh:
        written = next(csv.reader(fh))
    assert written[:len(head)] == head and written == list(output.COLUMNS), written


def test_a_toy_run_passes_the_audit_and_writes_every_output():
    res, rows = _toy_run()
    assert res.verdict == "pass", [(c.name, c.items[:3]) for c in res.checks if c.status == "fail"]
    checks = {c.name: c for c in res.checks}
    assert checks["dropped for zero opportunity"].status == "listed"
    assert checks["certificate tier"].status == "pass"
    assert checks["geography manifest is 2025"].status == "pass"
    for key in ("solver", "ledger", "scorecard", "districts", "run"):
        assert os.path.exists(res.paths[key]), key
    assert set(res.paths["maps"]) == {"X"} and os.path.exists(res.paths["maps"]["X"])
    report = json.load(open(res.paths["run"], encoding="utf-8"))
    assert report["maps"] == "drawn" and report["maps_missing_polygons"] == []
    assert report["not_placed_zips"] == 1 and report["dropped_channels"] == ["Y"]
    assert report["dropped_units"]["X"] and "CT" in report["dropped_units"]["X"]


def test_every_cell_has_one_row_and_a_blank_district_says_why():
    _, rows = _toy_run()
    assert sorted((r["zip_code"], r["current_channel"]) for r in rows) == \
        sorted((z, f) for z in MASS for f in "fg")
    by = {(r["zip_code"], r["current_channel"]): r for r in rows}
    for z in set(MASS) - {OFF}:
        g = by[z, "g"]
        assert (g["model_channel"], g["district"], g["reason"]) == ("Y", "", output.DROPPED)
    for z in CT:
        assert (by[z, "f"]["district"], by[z, "f"]["reason"]) == ("", output.DROPPED)
    assert {(by[OFF, f]["district"], by[OFF, f]["reason"]) for f in "fg"} == {("", output.NOT_PLACED)}
    owned = [r for r in rows if r["district"]]
    assert {r["zip_code"] for r in owned} == set(NY + NJ + PA)
    assert len({by[z, "f"]["district"] for z in NY}) == 1
    assert len({by[z, "f"]["district"] for z in NJ + PA}) == 1
    assert all(r["rep"] == "" for r in rows)
    assert all(r["district_channels"] == (r["model_channel"] if r["district"] else "") for r in rows)
    assert {r["cbsa"] for r in rows if r["zip_code"] in PA} == {"37980"}
    assert all(r["county"] and r["state"] for r in rows)


def test_districts_are_named_after_their_heaviest_cbsa():
    _, rows = _toy_run()
    names = {r["district"]: r["district_name"] for r in rows if r["district"]}
    assert sorted(names.values()) == ["X New York-Newark-Jersey City, NY-NJ",
                                      "X Philadelphia-Camden-Wilmington, PA-NJ-DE-MD"], names


def test_names_that_collide_take_their_next_cbsa_then_an_ordinal():
    def row(j, cbsa, m, state="NY"):
        return {"district": j, "model_channel": "WH", "state": state, "cbsa": cbsa, "m_rel": m}
    titles = {"1": "Big, NY", "2": "Next, NY", "3": "Other, NJ"}
    rows = [row("a", "1", 5.0), row("a", "2", 1.0), row("b", "1", 4.0), row("b", "3", 2.0),
            row("c", "1", 3.0), row("d", "1", 2.0), row("e", "", 1.0, "WY"),
            {**row("f", "1", 9.0), "model_channel": "FI"}]
    names = output.name_districts(rows, titles)
    assert names == {"a": "WH Big, NY / Next, NY", "b": "WH Big, NY / Other, NJ",
                     "c": "WH Big, NY (1)", "d": "WH Big, NY (2)", "e": "WH rural WY",
                     "f": "FI Big, NY"}, names
    assert len(set(names.values())) == len(names)


# ------------------------------------------------------------------------------ the maps
def test_maps_are_drawn_only_from_the_ledger_file():
    res, _ = _toy_run()
    tmp = tempfile.mkdtemp(prefix="td-maps-")
    path = os.path.join(tmp, "ledger.csv")
    with open(res.paths["ledger"], encoding="utf-8") as src, open(path, "w", encoding="utf-8") as dst:
        r = csv.DictReader(src)
        w = csv.DictWriter(dst, fieldnames=r.fieldnames, lineterminator="\n")
        w.writeheader()
        for row in r:
            if row["district"]:
                row["district"], row["district_name"] = "X_09", "X one"
            w.writerow(row)
    drawn = output.draw_maps(path, os.path.join(tmp, "maps"), ts._reference(), public=_toy_public())
    assert list(drawn) == ["X"] and drawn["X"]["districts"] == ["X_09"]
    assert os.path.exists(drawn["X"]["path"]) and drawn["X"]["zctas"] == len(NY + NJ + PA)
    assert {"New York", "Newark", "Jersey City", "Philadelphia"} <= set(drawn["X"]["labels"])
    shutil.rmtree(tmp)


def test_maps_fill_each_ledger_zcta_polygon_in_its_district_color_and_draw_no_points():
    from matplotlib.collections import PatchCollection, PathCollection
    res, rows = _toy_run()
    owned = {r["zip_code"]: r["district"] for r in rows if r["district"]}
    tmp = tempfile.mkdtemp(prefix="td-maps-")
    with _saved_figures() as saved:
        drawn = output.draw_maps(res.paths["ledger"], tmp, ts._reference(), public=_toy_public())
    assert [p for p, _ in saved] == [drawn["X"]["path"]] and os.path.exists(drawn["X"]["path"])
    ax = saved[0][1].axes[0]
    assert not [c for c in ax.collections if isinstance(c, PathCollection)]      # no scatter
    fills = [c for c in ax.collections if isinstance(c, PatchCollection)]
    assert sorted(len(c.get_paths()) for c in fills) == sorted(
        collections.Counter(owned.values()).values())                          # one per ZCTA
    colors = [tuple(c.get_facecolor()[0]) for c in fills]
    assert all(len({tuple(f) for f in c.get_facecolor()}) == 1 for c in fills)
    assert len(set(colors)) == len(fills) == len(set(owned.values()))
    assert drawn["X"]["zctas"] == len(owned) and drawn["X"]["missing"] == []
    shutil.rmtree(tmp)


def test_a_ledger_zcta_the_polygon_file_lacks_is_listed_and_the_rest_are_drawn():
    res, rows = _toy_run()
    owned = {r["zip_code"] for r in rows if r["district"]}
    public = _synthetic_public(set(MASS) - {PA[-1]})
    tmp = tempfile.mkdtemp(prefix="td-maps-")
    drawn = output.draw_maps(res.paths["ledger"], tmp, ts._reference(), public=public)
    assert drawn["X"]["missing"] == [PA[-1]] and drawn["X"]["zctas"] == len(owned) - 1
    out = tempfile.mkdtemp(prefix="td-output-")
    os.rmdir(out)
    extract, graph = _toy_inputs()
    got = output.run(_toy_spec(), extract, out, graph, ts._reference(), public)
    assert got.report["maps_missing_polygons"] == [PA[-1]]
    assert json.load(open(got.paths["run"]))["maps_missing_polygons"] == [PA[-1]]
    shutil.rmtree(tmp)
    shutil.rmtree(public)


def test_without_the_zcta_file_the_run_draws_no_map_and_says_so():
    out = tempfile.mkdtemp(prefix="td-output-")
    os.rmdir(out)
    extract, graph = _toy_inputs()
    empty = tempfile.mkdtemp(prefix="td-public-")
    res = output.run(_toy_spec(), extract, out, graph, ts._reference(), empty)
    assert res.verdict == "pass" and "maps" not in res.paths
    assert not os.path.exists(os.path.join(out, "maps"))
    assert json.load(open(res.paths["run"]))["maps"] == output.MAPS_SKIPPED
    assert output.draw_maps(res.paths["ledger"], os.path.join(out, "maps"), ts._reference(),
                            public=empty) == {}
    assert not os.path.exists(os.path.join(out, "maps"))
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        assert output.main_maps([out, "--public", empty]) == 1
    assert output.MAPS_SKIPPED in err.getvalue()
    assert not os.path.exists(os.path.join(out, "maps"))
    shutil.rmtree(out)


def test_maps_read_only_the_run_zctas_from_the_real_2025_zcta520_file():
    public = _real_zcta_public()
    if public is None:
        return
    import pyogrio
    res, rows = _toy_run()
    owned = sorted({r["zip_code"] for r in rows if r["district"]})
    calls, read, polygons, got = [], pyogrio.read_dataframe, output.zcta_polygons, []

    def spy(path, *args, **kw):
        calls.append((path, kw.get("where")))
        return read(path, *args, **kw)

    def kept(zips, public):
        got.append(polygons(zips, public))
        return got[-1]
    pyogrio.read_dataframe, output.zcta_polygons = spy, kept
    try:
        tmp = tempfile.mkdtemp(prefix="td-maps-")
        drawn = output.draw_maps(res.paths["ledger"], tmp, ts._reference(), public=public)
    finally:
        pyogrio.read_dataframe, output.zcta_polygons = read, polygons
    zcta_reads = [w for p, w in calls if p.endswith(output.ZCTA_FILE)]
    assert zcta_reads == ["ZCTA5CE20 IN (" + ",".join(repr(z) for z in owned) + ")"], zcta_reads
    polys, = got
    assert sorted(polys) == owned and all(p.is_valid and not p.is_empty for p in polys.values())
    x, y = ts._reference().set_index("zcta").loc["10001", ["x", "y"]].astype(float)
    assert polys["10001"].buffer(1.0).contains(__import__("shapely").Point(x, y))   # EPSG:5070
    assert drawn["X"]["zctas"] == len(owned) and drawn["X"]["missing"] == []
    shutil.rmtree(tmp)


def test_principal_cities_are_the_ones_the_2025_cbsa_title_names():
    areas = output.read_areas()
    titles, places = output.cbsa_titles(areas), output._places(areas, ts._reference())
    want = {"35620": ["New York", "Newark", "Jersey City"], "49180": ["Winston-Salem"],
            "34980": ["Nashville-Davidson", "Murfreesboro", "Franklin"],
            "31140": ["Louisville/Jefferson County"],
            "26420": ["Houston", "Pasadena", "The Woodlands"]}
    for code, cities in want.items():
        got = output.principal_cities(titles[code], places)
        assert [c for c, _, _ in got] == cities, (titles[code], got)
    ny = output.principal_cities(titles["35620"], places)[0]
    x, y = ts._reference().set_index("zcta").loc["10001", ["x", "y"]].astype(float)
    assert abs(ny[1] - x) < 20_000 and abs(ny[2] - y) < 20_000     # Manhattan, in EPSG:5070 m


def test_top_metros_rank_by_2025_population():
    pop = output.cbsa_population(ts._reference())
    top = sorted(pop, key=lambda c: -pop[c])[:3]
    assert top[0] == "35620" and pop["35620"] > pop["31080"] > pop["16980"], top


def test_a_full_extract_is_drawn_on_the_committed_graph():
    ref = ts._reference()
    vertices = sorted(ref.loc[ref["graph_vertex"].astype(int) == 1, "zcta"])
    extract = data.Extract(("f",), vertices, ["f"] * len(vertices), [1.0] * len(vertices),
                           [{}] * len(vertices), [0.0] * len(vertices))
    g = output.declared_graph(extract, ref, public=tempfile.mkdtemp())   # no polygons needed
    report = json.load(open(os.path.join(geo.REFERENCE_DIR, "REPORT.json"), encoding="utf-8"))
    assert g["vertices"] == vertices and len(g["edges"]) == report["graph"]["edges"]


def test_a_zip_with_no_opportunity_is_no_vertex_of_the_declared_graph():
    """OD2 (#72 B2): a ZIP at zero in every channel is for display only, so the declared graph is
    rebuilt over the other ZIPs; a ZIP at zero in one channel only keeps its vertex."""
    public = ts._state_file()
    if public is None:
        return
    zero, partial = NY[0], NJ[0]
    zs = sorted(NY + NJ + PA)
    m = {z: (0.0, 0.0) if z == zero else (0.0, 1.0) if z == partial else (1.0, 0.0) for z in zs}
    extract = data.Extract(("f", "g"), [z for z in zs for _ in "fg"], [f for _ in zs for f in "fg"],
                           [x for z in zs for x in m[z]], [{}] * 2 * len(zs), [0.0] * 2 * len(zs))
    ref = ts._reference()
    g = output.declared_graph(extract, ref, public)
    assert zero not in g["vertices"] and partial in g["vertices"]
    at = ref.set_index("zcta").loc[[z for z in zs if z != zero]]
    want = geo.zip_graph(dict(zip(at.index, zip(at["x"].astype(float), at["y"].astype(float)))),
                         dict(zip(at.index, at["state"])), data.state_polygons(public))
    assert g["vertices"] == want["vertices"] and g["edges"] == want["edges"]
    assert all(zero not in e[:2] for e in g["edges"])



def test_a_zip_positive_only_in_a_channel_planned_elsewhere_is_no_vertex_and_has_no_row():
    """#79: the run scopes the extract to the scenario's fine channels before it declares the
    graph, so a ZIP with opportunity only in a channel planned elsewhere is no vertex and has no
    ledger row, and `run.json` counts the cells left out per channel."""
    public = ts._state_file()
    if public is None:
        return
    raw = {"scenario": {"name": "toy_scoped", "fine_channels": ["f"], "planned_elsewhere": ["h"]},
           "channels": {"X": {"k": 2, "domain": [{"units": "all", "fine": ["f"]}], "eta": 0.1,
                              "max_dist_km": 1e9}}}
    s = spec.parse(raw)
    only_h = CT[0]                              # positive in h alone
    zs = sorted(NY + NJ + PA)
    cells = [(z, "f", MASS[z]) for z in zs] + [(z, "h", 2.0) for z in NY] + [(only_h, "h", 3.0)]
    extract = data.Extract(("f", "h"), [z for z, _, _ in cells], [f for _, f, _ in cells],
                           [m for _, _, m in cells], [{}] * len(cells), [0.0] * len(cells))
    declared, graphs = output.declared_graph, []

    def spy(ext, ref, pub=geo.PUBLIC_DIR):
        graphs.append(declared(ext, ref, pub))
        return graphs[-1]
    out = tempfile.mkdtemp(prefix="td-output-")
    os.rmdir(out)
    output.declared_graph = spy
    try:
        res = output.run(s, extract, out, None, ts._reference(), public, maps=False, source="toy")
    finally:
        output.declared_graph = declared
    assert len(graphs) == 1 and only_h not in graphs[0]["vertices"]
    assert set(graphs[0]["vertices"]) == set(zs)
    rows = output.read_ledger(res.paths["ledger"])
    assert all(r["zip_code"] != only_h for r in rows)
    assert {r["current_channel"] for r in rows} == {"f"}
    assert sorted(r["zip_code"] for r in rows) == zs
    report = json.load(open(res.paths["run"], encoding="utf-8"))
    assert report["planned_elsewhere"] == {"h": len(NY) + 1}
    assert report["not_placed_zips"] == 0 and report["zips"] == len(zs)
    assert res.verdict == "pass", [(c.name, c.items[:3]) for c in res.checks if c.status == "fail"]


def test_run_json_records_the_margin_per_channel():
    """#84: X turns the margin off and Y keeps the default; run.json says so per channel.  g gets
    f's masses, so Y is planned rather than dropped."""
    extract, graph = _toy_inputs()
    m = [MASS[z] for z in extract.z]
    both = data.Extract(extract.channels, extract.z, extract.channel, m, extract.share,
                        extract.share_free)
    out = tempfile.mkdtemp(prefix="td-output-")
    os.rmdir(out)
    res = output.run(_toy_spec(margin=False), both, out, graph, ts._reference(), maps=False)
    report = json.load(open(res.paths["run"], encoding="utf-8"))["channels"]
    assert {c: r["margin"] for c, r in report.items()} == {"X": False, "Y": True}
    shutil.rmtree(out)


# ------------------------------------------------------------------------------ pieces
def test_pieces_come_from_the_ledger_and_the_scorecard_run_json_and_districts_csv_agree():
    """NY's middle ZIPs have no cell in channel X: the map's district holds them at zero mass as
    connectors, but the ledger does not, so the district is in two pieces there."""
    extract, graph = _toy_inputs()
    keep = [i for i, (z, f) in enumerate(zip(extract.z, extract.channel))
            if not (f == "f" and z in NY[1:3])]
    m = [2.0 if extract.channel[i] == "f" and extract.z[i] in (NY[0], NY[-1]) else extract.m_rel[i]
         for i in keep]
    sparse = data.Extract(extract.channels, [extract.z[i] for i in keep],
                          [extract.channel[i] for i in keep], m, [extract.share[i] for i in keep],
                          [extract.share_free[i] for i in keep])
    out = tempfile.mkdtemp(prefix="td-output-")
    os.rmdir(out)
    res = output.run(_toy_spec(), sparse, out, graph, ts._reference(), maps=False)
    contiguity = {c.name: c for c in res.checks}["ZIP contiguity"]
    report = json.load(open(res.paths["run"], encoding="utf-8"))["channels"]["X"]
    with open(res.paths["districts"], encoding="utf-8") as fh:
        per = {r["district"]: int(r["pieces"]) for r in csv.DictReader(fh)}
    assert contiguity.counts["split"] == report["districts"] == sum(1 for n in per.values() if n) == 1
    assert contiguity.counts["pieces"] == report["pieces"] == sum(per.values()) == 1
    assert report["pieces_by_cause"] == {output.CONNECTOR: 1}
    assert contiguity.items and all("unreported" not in i for i in contiguity.items)
    assert all(output.CONNECTOR in i for i in contiguity.items), contiguity.items
    shutil.rmtree(out)


def test_a_ledger_piece_inside_a_realizer_piece_keeps_its_cause():
    from td import realize
    rows = [{"model_channel": "X", "district": "X_01", "zip_code": z, "m_rel": 1.0}
            for z in ("a", "b", "c", "d")]
    graph = {"vertices": ["a", "b", "c", "d", "e"], "edges": [("a", "b"), ("c", "e"), ("e", "d")]}
    d = realize.Drawing("X", {z: "A#1" for z in "abcde"}, {"A#1": 4.0}, {}, {},
                        [realize.Piece("A#1", ("c", "d", "e"), 2.0, "corridor")])
    split = output.ledger_pieces(rows, graph, {"X": d})
    assert [(p.zips, p.cause) for p in split["X", "X_01"]] == [(("c",), "corridor"), (("d",), "corridor")]
    d.pieces = []
    assert {p.cause for p in output.ledger_pieces(rows, graph, {"X": d})["X", "X_01"]} == {output.CONNECTOR}


# ------------------------------------------------------------------------------ the stops
def test_a_channel_with_no_plan_stops_the_run_after_writing_the_solver_report():
    """Also #88: the domain components and their floor are printed before the solve and kept in
    `solver.json`, even when the run stops."""
    out = tempfile.mkdtemp(prefix="td-output-")
    extract, graph = _toy_inputs()
    printed = io.StringIO()
    try:
        with contextlib.redirect_stdout(printed):
            output.run(_toy_spec(k=3, delta=0.0, final_delta=0.0), extract, out, graph,
                       ts._reference(), maps=False)
    except output.RunError as e:
        assert "no plan for X" in str(e) and "infeasible" in str(e), str(e)
    else:
        raise AssertionError("no RunError")
    doc = json.load(open(os.path.join(out, "solver.json")))
    assert doc["X"]["solver"]["status"] == "infeasible"
    comps = doc["X"]["components"]
    assert len(comps["components"]) == 1 and comps["components"][0]["units"] == \
        ["NJ", "NY", "PA"] and abs(comps["components"][0]["mass_tau"] - 3.0) < 1e-12, comps
    assert comps["allocation"] == [3] and comps["floor"] < 1e-12, comps
    assert spec.component_lines({"X": comps})[0] in printed.getvalue().splitlines(), \
        printed.getvalue()
    shutil.rmtree(out)


def test_an_infeasible_band_reports_the_smallest_master_delta_and_keeps_the_band():
    """OD1 and S10 (#72 B3): a declared band proven infeasible gets its smallest master δ in
    `solver.json` and the stop's reason, and the run does not go on at it."""
    out = tempfile.mkdtemp(prefix="td-output-")
    extract, graph = _toy_inputs()
    s = _toy_spec(k=3, delta=0.0, final_delta=0.0, mode="clipped")
    inst = spec.build(s, data.conus(extract, ts._reference()), ts._reference(), graph)
    want = master.smallest_delta(inst, "X")
    assert want.method == "exact" and want.status == "exact" and want.delta > 0.5, want
    try:
        output.run(s, extract, out, graph, ts._reference(), maps=False)
    except output.RunError as e:
        assert f"smallest master δ {want.delta:.6g} (exact, exact)" in str(e), str(e)
        assert "declared bands are kept" in str(e), str(e)
    else:
        raise AssertionError("no RunError")
    got = json.load(open(os.path.join(out, "solver.json")))["X"]
    assert got["solver"]["status"] == "infeasible"
    assert got["smallest_delta"]["delta"] == want.delta and got["smallest_delta"]["status"] == "exact"
    assert set(os.listdir(out)) == {"solver.json"}          # no ledger at the found δ
    shutil.rmtree(out)


def test_a_channel_with_no_verdict_gets_no_smallest_delta_search():
    """A master that ends without a verdict (here a zero time limit) is unknown, not infeasible:
    no smallest δ is searched or written."""
    out = tempfile.mkdtemp(prefix="td-output-")
    extract, graph = _toy_inputs()
    try:
        output.run(_toy_spec(), extract, out, graph, ts._reference(), maps=False, time_limit=0.0)
    except output.RunError as e:
        assert "(time limit), no verdict, so no smallest δ was searched" in str(e), str(e)
    else:
        raise AssertionError("no RunError")
    got = json.load(open(os.path.join(out, "solver.json")))["X"]
    assert got["solver"]["status"] == "time limit" and "smallest_delta" not in got
    shutil.rmtree(out)


def test_the_stop_words_each_smallest_delta_by_what_its_search_proves():
    """#72 B3: an exact optimum is proved; a bisection's lower end is a δ a step proved
    infeasible; an exact solve that stopped without a verdict gives the solver's bound, never
    "infeasible at", and says unknown."""
    rep = {"status": "infeasible"}
    D = master.Delta
    exact = output.no_plan("X", 0.0, rep, D("X", "exact", "exact", 0.875, 0.875, 0.0))
    assert exact.endswith("smallest master δ 0.875 (exact, exact)"), exact
    bis = output.no_plan("X", 0.0, rep, D("X", "bisection", "converged", 0.9, 0.8, 0.1))
    assert bis.endswith("smallest master δ in (0.8, 0.9] (bisection, converged): feasible at 0.9, "
                        "infeasible at 0.8"), bis
    zero = output.no_plan("X", 0.1, rep, D("X", "bisection", "converged", 0.0, None, 0.1))
    assert zero.endswith("smallest master δ 0 (bisection, converged): feasible at 0"), zero
    stuck = output.no_plan("X", 0.0, rep, D("X", "bisection", "unknown", None, 0.5, 0.1))
    assert stuck.endswith("smallest master δ unknown (bisection, unknown): infeasible at 0.5"), stuck
    bound = output.no_plan("X", 0.0, rep, D("X", "exact", "unknown", 0.875, 0.875, 0.0))
    assert bound.endswith("smallest master δ unknown (exact, unknown): feasible at 0.875, "
                          "solver bound 0.875"), bound
    blank = output.no_plan("X", 0.0, rep, D("X", "exact", "unknown", None, None, 0.0))
    assert blank.endswith("smallest master δ unknown (exact, unknown), nothing proven"), blank
    none = output.no_plan("X", 0.0, rep, D("X", "bisection", "infeasible", None, 9.0, 0.1))
    assert none.endswith("and no δ is feasible (bisection)"), none
    for text in (exact, bound, blank):
        assert "infeasible at" not in text, text
    assert output.delta_reading(D("X", "exact", "exact", 0.875, 0.875, 0.0)) == {
        "proved": True, "feasible_at": 0.875, "infeasible_at": None, "solver_bound": None}
    assert output.delta_reading(D("X", "bisection", "converged", 0.9, 0.8, 0.1)) == {
        "proved": False, "feasible_at": 0.9, "infeasible_at": 0.8, "solver_bound": None}
    assert output.delta_reading(D("X", "exact", "unknown", 0.875, 0.8, 0.0)) == {
        "proved": False, "feasible_at": 0.875, "infeasible_at": None, "solver_bound": 0.8}


def test_an_exact_search_stopped_without_a_verdict_stays_unknown_in_the_stop_and_solver_json():
    """#72 B3 repro: the exact δ-MILP keeps a valid incumbent and a tight bound but reports a
    time limit (injected), so its lower end is the solver's bound, and a plan exists there."""
    from dataclasses import replace
    from unittest.mock import patch
    out = tempfile.mkdtemp(prefix="td-output-")
    extract, graph = _toy_inputs()
    s = _toy_spec(k=3, delta=0.0, final_delta=0.0, mode="clipped")
    real = master._run

    def timed_out(*a, **kw):
        sol = real(*a, **kw)
        return replace(sol, status="time limit") if sol.status == "optimal" else sol

    with patch("td.master._run", side_effect=timed_out):
        try:
            output.run(s, extract, out, graph, ts._reference(), maps=False)
        except output.RunError as e:
            msg = str(e)
        else:
            raise AssertionError("no RunError")
    assert "smallest master δ unknown (exact, unknown): feasible at 0.875, solver bound" in msg, msg
    assert "infeasible at" not in msg, msg
    got = json.load(open(os.path.join(out, "solver.json")))["X"]["smallest_delta"]
    assert got["method"] == "exact" and got["status"] == "unknown", got
    assert got["reading"]["proved"] is False and got["reading"]["infeasible_at"] is None, got
    assert got["reading"]["feasible_at"] == got["delta"] and got["reading"]["solver_bound"] == got["lower"]
    assert set(os.listdir(out)) == {"solver.json"}
    shutil.rmtree(out)


def test_a_bisected_smallest_delta_reports_its_bracket_in_the_stop_and_solver_json():
    """#72 B3: a free channel's smallest δ is bisected; its lower end is a δ a step proved
    infeasible, so it reads as such, and the answer is a bracket, not a proof."""
    out = tempfile.mkdtemp(prefix="td-output-")
    extract, graph = _toy_inputs()
    try:
        output.run(_toy_spec(k=3, delta=0.0, final_delta=0.0, mode="free"), extract, out, graph,
                   ts._reference(), maps=False)
    except output.RunError as e:
        msg = str(e)
    else:
        raise AssertionError("no RunError")
    got = json.load(open(os.path.join(out, "solver.json")))["X"]["smallest_delta"]
    assert got["method"] == "bisection" and got["status"] == "converged", got
    r = got["reading"]
    assert r == {"proved": False, "feasible_at": got["delta"], "infeasible_at": got["lower"],
                 "solver_bound": None}, got
    assert any(st["delta"] == got["lower"] and st["verdict"] == "infeasible" for st in got["steps"])
    assert (f"smallest master δ in ({got['lower']:.6g}, {got['delta']:.6g}] (bisection, converged): "
            f"feasible at {got['delta']:.6g}, infeasible at {got['lower']:.6g}") in msg, msg
    shutil.rmtree(out)

def test_a_hook_that_td_hooks_lacks_stops_the_run_before_solving():
    import td.hooks as hooks
    assert not [k for k, v in vars(hooks).items() if callable(v) and not k.startswith("_")]
    extract, graph = _toy_inputs()
    try:
        output.run(_toy_spec(hook="split_metro"), extract, tempfile.mkdtemp(), graph,
                   ts._reference(), maps=False)
    except spec.SpecError as e:
        assert "split_metro" in str(e)
    else:
        raise AssertionError("no SpecError")


def _named_spec(channel: str, other: str = "Y", scenario: str = "toy"):
    raw = {"scenario": {"name": scenario, "fine_channels": ["f", "g"]},
           "channels": {channel: {"k": 2, "domain": [{"units": "all", "fine": ["f"]}], "eta": 0.1,
                                 "max_dist_km": 1e9},
                        other: {"k": 1, "domain": [{"units": "all", "fine": ["g"]}], "eta": 0.1}}}
    return spec.parse(raw)


def _refused(call, *names):
    try:
        call()
    except output.RunError as e:
        assert all(repr(n) in str(e) for n in names), str(e)
    else:
        raise AssertionError(f"no RunError for {names}")


def test_a_channel_that_cannot_name_a_file_stops_the_run_before_it_writes():
    extract, graph = _toy_inputs()
    root = tempfile.mkdtemp(prefix="td-paths-")
    sentinel = os.path.join(root, "escaped.png")
    with open(sentinel, "wb") as fh:
        fh.write(b"KEEP")
    out = os.path.join(root, "run")
    for bad in ("../../escaped", "/tmp/escaped", "a/b", "..", ".", "a b"):
        _refused(lambda: output.run(_named_spec(bad), extract, out, graph, ts._reference(),
                                    _toy_public()), bad)
    _refused(lambda: output.run(_named_spec("WH", "wh"), extract, out, graph, ts._reference(),
                                _toy_public()), "WH", "wh")
    assert sorted(os.listdir(root)) == ["escaped.png"] and open(sentinel, "rb").read() == b"KEEP"
    shutil.rmtree(root)


def test_the_maps_command_refuses_a_ledger_channel_or_a_maps_dir_that_leaves_the_run():
    res, _ = _toy_run()
    root = tempfile.mkdtemp(prefix="td-paths-")
    sentinel = os.path.join(root, "escaped.png")
    with open(sentinel, "wb") as fh:
        fh.write(b"KEEP")
    run_dir = os.path.join(root, "run")
    os.makedirs(run_dir)
    with open(res.paths["ledger"], encoding="utf-8") as fh:
        text = fh.read()
    with open(os.path.join(run_dir, "ledger.csv"), "w", encoding="utf-8") as fh:
        fh.write(text.replace(",X,", ",../../escaped,"))
    _refused(lambda: output.draw_maps(os.path.join(run_dir, "ledger.csv"),
                                      os.path.join(run_dir, "maps"), ts._reference(),
                                      public=_toy_public(), root=run_dir), "../../escaped")
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        assert output.main_maps([run_dir, "--public", _toy_public()]) == 1
    assert "'../../escaped'" in err.getvalue()
    assert sorted(os.listdir(run_dir)) == ["ledger.csv"] and open(sentinel, "rb").read() == b"KEEP"
    # a valid ledger whose map file is a link out of the run: nothing is drawn through it
    shutil.copy(res.paths["ledger"], os.path.join(run_dir, "ledger.csv"))
    elsewhere = tempfile.mkdtemp(prefix="td-elsewhere-")
    os.symlink(os.path.join(elsewhere, "map_X.png"), os.path.join(run_dir, "map_X.png"))
    with contextlib.redirect_stderr(io.StringIO()):
        assert output.main_maps([run_dir, "--public", _toy_public()]) == 1
    assert os.listdir(elsewhere) == []
    shutil.rmtree(root)
    shutil.rmtree(elsewhere)


def test_a_scenario_that_cannot_name_the_default_run_directory_is_refused():
    """An absolute name would replace runs/ in the default --out; this one points into `tmp`."""
    tmp = tempfile.mkdtemp(prefix="td-paths-")
    name, path = os.path.join(tmp, "escaped"), os.path.join(tmp, "s.toml")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(f'[scenario]\nname = "{name}"\nfine_channels = ["f"]\n\n'
                 '[channels.X]\nk = 1\neta = 0.1\ndomain = [{ units = "all", fine = ["f"] }]\n')
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        assert output.main_run([path, "--fixture", "0"]) == 1
    assert f"scenario {name!r}" in err.getvalue(), err.getvalue()
    assert os.listdir(tmp) == ["s.toml"]
    shutil.rmtree(tmp)


def test_the_cli_lists_run_and_maps():
    from td import __main__ as cli
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        assert cli.main(["--help"]) == 0
    assert "run <spec>" in buf.getvalue() and "maps <run dir>" in buf.getvalue()
    with contextlib.redirect_stderr(io.StringIO()):
        try:
            cli.main(["run", "no.toml"])
        except SystemExit as e:
            assert e.code == 2                  # --extract or --fixture is required
        else:
            raise AssertionError("argparse accepted a run with no extract")
