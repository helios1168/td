"""test_plan_summary.py: tools/plan_summary.py on a toy run directory.

No network, no gazetteer and no shapefile: the tessellation is stubbed with one unit square per
zip (touching squares, so a district dissolves to a single polygon and the "one polygon per
district" assertion has an arithmetic answer), and `states_outline` returns a three-row
GeoDataFrame of boxes over those squares.

Six zips, three states, two bundles: `N` holds every zip in two districts, `WH` holds the first
three and drops the rest, and no district carries `FI` at all, which is the empty-channel branch
the figure has to survive.
"""
from __future__ import annotations

import csv
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
if os.path.join(ROOT, "tools") not in sys.path:
    sys.path.insert(0, os.path.join(ROOT, "tools"))

from td import geo as td_geo                       # noqa: E402
import plan_summary as cli                         # noqa: E402

ZIPS = [f"{10000 + i:05d}" for i in range(6)]
STATES = ["S0", "S0", "S1", "S1", "S2", "S2"]
N_DISTRICT = ["N_01", "N_01", "N_01", "N_02", "N_02", "N_02"]
WH_DISTRICT = ["WH_01", "WH_01", "WH_01", "", "", ""]
WHOLESALERS = {"N_01": "R0001", "N_02": "R0002", "WH_01": "R0003"}

# one unit square per zip, side by side: squares of the same district share an edge, so the
# dissolve of any run of them is a single polygon
SIDE = 1000.0


def _squares() -> dict:
    import shapely

    return {z: shapely.box(i * SIDE, 0.0, (i + 1) * SIDE, SIDE) for i, z in enumerate(ZIPS)}


def _states_gdf():
    import geopandas as gpd
    import shapely

    box = {"S0": shapely.box(0.0, 0.0, 2 * SIDE, SIDE),
           "S1": shapely.box(2 * SIDE, 0.0, 4 * SIDE, SIDE),
           "S2": shapely.box(4 * SIDE, 0.0, 6 * SIDE, SIDE)}
    return gpd.GeoDataFrame({"STUSPS": list(box)}, geometry=list(box.values()),
                            crs=td_geo.LAEA)


def _write_run(run_dir: str) -> None:
    with open(os.path.join(run_dir, "assignment.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["zip", "state", "channel", "file_channel", "district", "bundle",
                    "wholesaler", "M_cell"])
        for z, st, n, wh in zip(ZIPS, STATES, N_DISTRICT, WH_DISTRICT):
            for chan in ("N_WH", "N_FI"):
                w.writerow([z, st, chan, "national", n, "N", WHOLESALERS[n], 2.0])
            w.writerow([z, st, "WH", "wh", wh or cli.OTHER, "WH" if wh else "",
                        WHOLESALERS.get(wh, ""), 3.0])
            w.writerow([z, st, "FI", "fi", cli.OTHER, "", "", 5.0])

    with open(os.path.join(run_dir, "districts.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["district", "bundle", "channels", "states", "n_zips", "mass",
                    "wholesaler", "staffed", "contiguous"])
        w.writerow(["N_01", "N", "N_WH N_FI", "S0:1,S1:0.5", 3, 10.0, "R0001", 1, 1])
        w.writerow(["N_02", "N", "N_WH N_FI", "S1:0.5,S2:1", 3, 11.0, "R0002", 1, 1])
        w.writerow(["WH_01", "WH", "WH", "S0:1,S1:0.5", 3, 9.0, "R0003", 0, 1])

    plan = dict(
        state_list=["S0", "S1", "S2"], bundles=["N", "WH", "FI"],
        slots=[dict(id="P001", bundle="N", used=True, y={"S0": 1.0, "S1": 0.5}),
               dict(id="P002", bundle="N", used=True, y={"S1": 0.5, "S2": 1.0}),
               dict(id="P003", bundle="WH", used=True, y={"S0": 1.0, "S1": 0.5}),
               dict(id="P004", bundle="FI", used=False, y={"S2": 1.0})],
        per_state={"S0": {"P001": 1.0, "P003": 1.0},
                   "S1": {"P001": 0.5, "P002": 0.5, "P003": 0.5},
                   "S2": {"P002": 1.0, "P004": 1.0}},
    )
    with open(os.path.join(run_dir, "plan.json"), "w", encoding="utf-8") as fh:
        json.dump(plan, fh)
    with open(os.path.join(run_dir, "params.json"), "w", encoding="utf-8") as fh:
        json.dump(dict(route="sequential", band_lo=0.8, band_hi=1.2, dist_max=None,
                       n_max=None, instance="/nowhere/instance.json.gz"), fh)
    with open(os.path.join(run_dir, "staffing.json"), "w", encoding="utf-8") as fh:
        json.dump(dict(reps=["R0001", "R0002", "R0003", "R0004"],
                       unmatched_reps=["R0004"]), fh)


def _run(run_dir: str) -> list:
    orig = (td_geo.states_outline, cli.zip_cells)
    td_geo.states_outline = lambda *a, **kw: _states_gdf()
    cli.zip_cells = lambda *a, **kw: _squares()
    try:
        return cli.summary(run_dir, "unused", dpi=60, simplify=0.0)
    finally:
        td_geo.states_outline, cli.zip_cells = orig


def test_a_toy_run_writes_the_png_and_the_svg():
    with tempfile.TemporaryDirectory() as tmp:
        run_dir = os.path.join(tmp, "run")
        os.makedirs(run_dir)
        _write_run(run_dir)
        written = _run(run_dir)

        assert [os.path.basename(p) for p in written] == ["summary.png", "summary.svg"]
        for path in written:
            assert os.path.exists(path), path
            assert os.path.getsize(path) > 5000, (path, os.path.getsize(path))
        # one pickle per bundle and one per channel with unheld ground; no `cells.pkl`, since
        # the tessellation itself is stubbed here rather than built
        cache = os.path.join(run_dir, "maps", "cache")
        assert sorted(os.listdir(cache)) == ["N_districts.pkl", "WH_districts.pkl",
                                             "unheld_FI.pkl", "unheld_WH.pkl"]


def test_each_district_dissolves_to_one_polygon():
    """Three squares in a row share edges, so the union is a `Polygon`, never a `MultiPolygon`;
    a district in pieces would come out multi-part and the map would show it."""
    with tempfile.TemporaryDirectory() as tmp:
        mapping = dict(zip(ZIPS, N_DISTRICT))
        polys = cli.dissolve_groups("N_districts", mapping, _squares, tmp)
        assert sorted(polys) == ["N_01", "N_02"]
        for name, geom in polys.items():
            assert geom.geom_type == "Polygon", (name, geom.geom_type)
            assert abs(geom.area - 3 * SIDE * SIDE) < 1e-6, name
        # second call is served from the pickle, same answer
        again = cli.dissolve_groups("N_districts", mapping, _no_cells, tmp)
        assert sorted(again) == ["N_01", "N_02"]


def _no_cells():
    raise AssertionError("the cache should have answered without the tessellation")


def test_the_state_pattern_classifier_on_the_five_hand_cases():
    assert cli.classify_state(set()) == "unserved"
    assert cli.classify_state({"N", "WH", "FI"}) == "three channels"
    assert cli.classify_state({"N", "WH"}) == "partial"
    assert cli.classify_state({"FI"}) == "partial"
    assert cli.classify_state({"N", "WHFI"}) == "WH+FI merged"
    assert cli.classify_state({"WHFI"}) == "WH+FI merged"
    # one rep for all three channels, the "all" district, outranks a WH+FI merge beside it
    assert cli.classify_state({"WHFI_PLUS"}) == "all merged"
    assert cli.classify_state({"WHFI", "WHFI_PLUS", "N"}) == "all merged"
    assert cli.classify_state({"FI_PLUS", "WH"}) == "national dropped"
    assert cli.classify_state({"WH_PLUS", "FI_PLUS"}) == "national dropped"
    # a plus bundle beside a national one is not a dropped national
    assert cli.classify_state({"N", "WH", "FI", "FI_PLUS"}) == "three channels"


def test_the_pattern_per_state_reads_the_used_slots_only():
    """`P004` is an unused slot, so S2 is served by `N` alone and its pattern is partial."""
    plan = dict(
        slots=[dict(id="P001", bundle="N", used=True), dict(id="P002", bundle="N", used=True),
               dict(id="P003", bundle="WH", used=True),
               dict(id="P004", bundle="FI", used=False)],
        per_state={"S0": {"P001": 1.0, "P003": 1.0},
                   "S1": {"P001": 0.5, "P002": 0.5, "P003": 0.5},
                   "S2": {"P002": 1.0, "P004": 1.0},
                   "S3": {"P001": 0.0}},
    )
    assert cli.state_patterns(plan) == {"S0": "partial", "S1": "partial", "S2": "partial",
                                        "S3": "unserved"}


def test_a_split_state_is_counted_per_business_channel():
    """S1's zips go to two national districts and one WH district, so it hatches on the
    structure panel and counts as split for National only."""
    with tempfile.TemporaryDirectory() as tmp:
        run_dir = os.path.join(tmp, "run")
        os.makedirs(run_dir)
        _write_run(run_dir)
        run = cli.load_assignment(os.path.join(run_dir, "assignment.csv"))

        assert run["splits"] == {"National": {"S1"}, "WH": set(), "FI": set()}
        assert run["districts"]["National"] == {"N_01", "N_02"}
        assert run["districts"]["WH"] == {"WH_01"}
        assert run["districts"]["FI"] == set()
        # the national book is two channel rows per zip, so its unheld mass counts both halves
        assert run["unheld"]["WH"] == set(ZIPS[3:])
        assert run["unheld"]["FI"] == set(ZIPS)
        assert run["residual"]["WH"] == 9.0                      # 3 zips x 3.0
        assert run["residual"]["FI"] == 30.0                     # 6 zips x 5.0
        assert run["residual"]["National"] == 0.0
        assert run["zips_by_bundle"]["N"] == dict(zip(ZIPS, N_DISTRICT))
        assert run["zips_by_bundle"]["WH"] == dict(zip(ZIPS[:3], WH_DISTRICT[:3]))


def test_a_bundle_reads_its_business_channels_from_the_districts_table():
    meta = {"N_01": {"bundle": "N", "channels": "N_WH N_FI"},
            "F_01": {"bundle": "FI_PLUS", "channels": "FI N_FI"},
            "M_01": {"bundle": "WHFI", "channels": "WH FI"}}
    assert cli.business_of("N", meta) == ("National",)
    assert cli.business_of("FI_PLUS", meta) == ("National", "FI")
    assert cli.business_of("WHFI", meta) == ("WH", "FI")
    # no row for the bundle: the name is the fallback
    assert cli.business_of("WH", meta) == ("WH",)
    assert cli.business_of("WH_PLUS", {}) == ("National", "WH")


def test_the_district_label_puts_the_wholesaler_under_the_id():
    meta = {"N_01": {"wholesaler": "R0001"}, "N_02": {"wholesaler": ""}}
    assert cli._label("N_01", meta) == "N_01\nR0001"
    assert cli._label("N_02", meta) == "N_02"
    assert cli._label("N_03", {}) == "N_03"


def test_the_states_column_reads_as_whole_states_and_shares():
    row = {"states": "AZ:0.775496,CO:1,NM:1"}
    assert cli.states_of(row) == [("AZ", 0.775496), ("CO", 1.0), ("NM", 1.0)]
    assert cli.states_text(row) == "AZ 78 %, CO, NM"
    assert cli.states_text({}) == ""


def test_district_colours_differ_between_neighbours_and_hold_across_panels():
    """Two districts touching on a panel never share a colour; a district on two panels has
    one colour; a district touching nothing may take any."""
    import shapely

    a, b, c = (shapely.box(0, 0, 1, 1), shapely.box(1, 0, 2, 1), shapely.box(2, 0, 3, 1))
    polys = {"N": {"N_01": a, "N_02": b}, "WHFI": {"WHFI_01": c}, "FI": {"FI_01": a}}
    meta = {"N_01": {"bundle": "N", "channels": "N_WH N_FI"},
            "N_02": {"bundle": "N", "channels": "N_WH N_FI"},
            "WHFI_01": {"bundle": "WHFI", "channels": "WH FI"},
            "FI_01": {"bundle": "FI", "channels": "FI"}}
    colors = cli.district_colors(polys, meta)
    assert set(colors) == {"N_01", "N_02", "WHFI_01", "FI_01"}
    assert colors["N_01"] != colors["N_02"]                     # touch on National
    # FI_01 (box a) and WHFI_01 (box c) do not touch, so both take the palette's least-used
    # entries: on the FI panel, coloured first with two districts, they still differ
    assert colors["FI_01"] != colors["WHFI_01"]
    adj = cli.panel_adjacency({"x": a, "y": b, "z": c})
    assert adj == {"x": {"y"}, "y": {"x", "z"}, "z": {"y"}}


def test_no_kappa_means_the_masses_stay_descaled():
    """The descaled instances strip the scale, so nothing on disk carries one and the figure
    says descaled mass rather than dollars."""
    assert cli.kappa_of({}, None) is None
    assert cli.kappa_of({"instance": "/nowhere/instance.json.gz"}, None) is None
    assert cli.kappa_of({"kappa": 1234.0}, None) == 1234.0
    assert cli.kappa_of({"kappa": 1234.0}, 7.0) == 7.0
