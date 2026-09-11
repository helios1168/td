"""test_plan_summary.py: tools/plan_summary.py on a toy run directory.

No network, no gazetteer and no real shapefile: `geo.states_outline`, `geo.zcta_polygons` and
`run_draw.coordinates` are stubbed so `geom_export.export` runs for real on a hand-built toy:
`geo.zcta_polygons`'s stand-in returns the same touching unit squares `geo.states_outline`'s
boxes tile, so a district's real-ZCTA dissolve has an arithmetic answer (`tests/test_geom_export
.py` uses the same pattern with its own fixture).

Six zips, three states, two bundles with a district: `N` holds every zip in two districts, `WH`
holds the first three and drops the rest, and no district carries `FI` at all, the toy's
"a bundle with no district gets no map" case.
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
import run_draw                                    # noqa: E402

ZIPS = [f"{10000 + i:05d}" for i in range(6)]
STATES = ["S0", "S0", "S1", "S1", "S2", "S2"]
N_DISTRICT = ["N_01", "N_01", "N_01", "N_02", "N_02", "N_02"]
WH_DISTRICT = ["WH_01", "WH_01", "WH_01", "", "", ""]
WHOLESALERS = {"N_01": "R0001", "N_02": "R0002", "WH_01": "R0003"}

# one unit square per zip, side by side: squares of the same district (or the same state) share
# an edge, so the real-ZCTA dissolve of any run of them is a single polygon
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


def _zcta_polygons_stub(zips, *a, **kw):
    squares = _squares()
    return {z: squares[z] for z in zips if z in squares}


def _coordinates_stub(zips, *a, **kw):
    centres = {z: ((i + 0.5) * SIDE, SIDE / 2.0) for i, z in enumerate(ZIPS)}
    have = [z for z in zips if z in centres]
    missing = [z for z in zips if z not in centres]
    return {z: centres[z] for z in have}, missing


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
    orig = (td_geo.states_outline, td_geo.zcta_polygons, run_draw.coordinates)
    td_geo.states_outline = lambda *a, **kw: _states_gdf()
    td_geo.zcta_polygons = _zcta_polygons_stub
    run_draw.coordinates = _coordinates_stub
    try:
        return cli.summary(run_dir, "unused", dpi=60, simplify=0.0)
    finally:
        td_geo.states_outline, td_geo.zcta_polygons, run_draw.coordinates = orig


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
        # one geom cache pickle per bundle with a district: N and WH, never the empty FI
        cache = os.path.join(run_dir, "maps", "cache")
        assert sorted(os.listdir(cache)) == ["N_geom.pkl", "WH_geom.pkl"]


def test_groups_parse_and_reach_the_structure_panel_legend():
    assert cli._parse_groups("G1=tx, ny;G2 adds=WA") == [("G1", ["TX", "NY"]), ("G2 adds", ["WA"])]
    for bad in ("G1", "=TX", "A=X;B=Y;C=Z;D=W"):
        try:
            cli._parse_groups(bad)
        except Exception:
            pass
        else:
            raise AssertionError(f"{bad!r} must be refused")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from shapely.geometry import box
    fig, ax = plt.subplots()
    states = {"TX": box(0, 0, 1, 1), "NY": box(2, 0, 3, 1), "WA": box(4, 0, 5, 1)}
    run = {"patterns": {s: "three channels" for s in states}, "splits": {}}
    cli.structure_panel(ax, run, states, groups=[("G1", ["TX", "NY"]), ("G2 adds", ["NY", "WA"])])
    labels = [t.get_text() for t in ax.get_legend().get_texts()]
    plt.close(fig)
    assert "G1: NY TX  (2)" in labels and "G2 adds: WA  (1)" in labels


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


def test_wholesaler_counts_reads_used_slots_with_a_positive_share():
    """The count is over slots, not bundles: two used slots of the same bundle count twice."""
    plan = dict(
        slots=[dict(id="P001", bundle="N", used=True), dict(id="P002", bundle="N", used=True),
               dict(id="P003", bundle="WH", used=True),
               dict(id="P004", bundle="FI", used=False)],
        per_state={"S0": {"P001": 1.0, "P003": 1.0}, "S1": {"P001": 0.0},
                  "S2": {"P002": 1.0, "P004": 1.0}},
    )
    assert cli.wholesaler_counts(plan) == {"S0": 2, "S1": 0, "S2": 1}
    assert cli.wholesaler_counts({"per_state": {"S9": {}}}) == {"S9": 0}


def test_a_split_state_is_counted_per_business_channel_and_mass_sums_the_bundles_own_rows():
    """S1's zips go to two national districts and one WH district, so it hatches on the
    structure panel and counts as split for National only.  `mass_by_bundle["N"]` sums both
    halves of the national book for one zip; `mass_by_bundle["WH"]` is the WH row alone."""
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
        assert run["mass_by_bundle"]["N"][ZIPS[0]] == 4.0         # N_WH 2.0 + N_FI 2.0
        assert run["mass_by_bundle"]["WH"][ZIPS[0]] == 3.0
        assert ZIPS[3] not in run["mass_by_bundle"]["WH"]         # dropped, not zero


def test_bundle_split_states_counts_per_bundle_not_per_business_channel():
    """S1 holds two `N` districts (split) but only one `WH` district (not split)."""
    with tempfile.TemporaryDirectory() as tmp:
        run_dir = os.path.join(tmp, "run")
        os.makedirs(run_dir)
        _write_run(run_dir)
        run = cli.load_assignment(os.path.join(run_dir, "assignment.csv"))

        assert cli.bundle_split_states("N", run) == {"S1"}
        assert cli.bundle_split_states("WH", run) == set()
        assert cli.bundle_split_states("FI", run) == set()


def test_the_district_label_puts_the_wholesaler_under_the_id():
    meta = {"N_01": {"wholesaler": "R0001"}, "N_02": {"wholesaler": ""}}
    assert cli._label("N_01", meta) == "N_01\nR0001"
    assert cli._label("N_02", meta) == "N_02"
    assert cli._label("N_03", {}) == "N_03"
    assert cli._label("WHFI_PLUS_07", {"WHFI_PLUS_07": {"wholesaler": "R0009"}}) == \
        "WIFI_07\nR0009"


def test_display_id_shows_whfi_plus_as_wifi():
    assert cli.display_id("WHFI_PLUS_07") == "WIFI_07"
    assert cli.display_id("WHFI_01") == "WHFI_01"           # WHFI, not WHFI_PLUS: unchanged
    assert cli.display_id("N_03") == "N_03"
    assert cli.display_id("WH_PLUS_02") == "WH_PLUS_02"


def test_bundle_title_is_the_fixed_reading_or_the_bundle_name():
    assert cli.bundle_title("N") == "National only"
    assert cli.bundle_title("WHFI_PLUS") == "WIFI: national + WH + FI, one wholesaler"
    assert cli.bundle_title("SOMETHING_NEW") == "SOMETHING_NEW"


def test_ordered_bundles_is_the_fixed_reading_order_then_unknowns_by_name():
    assert cli.ordered_bundles({"FI", "N", "WHFI_PLUS"}) == ["N", "FI", "WHFI_PLUS"]
    assert cli.ordered_bundles({"ZZZ", "N", "AAA"}) == ["N", "AAA", "ZZZ"]


def test_wholesaler_count_counts_distinct_non_empty_wholesalers():
    meta = {"N_01": {"wholesaler": "R0001"}, "N_02": {"wholesaler": "R0002"},
            "WH_01": {"wholesaler": "R0001"}, "FI_01": {"wholesaler": ""}}
    assert cli.wholesaler_count(meta) == 2
    assert cli.wholesaler_count({}) == 0


def test_the_states_column_reads_as_whole_states_and_shares():
    row = {"states": "AZ:0.775496,CO:1,NM:1"}
    assert cli.states_of(row) == [("AZ", 0.775496), ("CO", 1.0), ("NM", 1.0)]
    assert cli.states_text(row) == "AZ 78 %, CO, NM"
    assert cli.states_text({}) == ""


def test_no_kappa_means_the_masses_stay_descaled():
    """The descaled instances strip the scale, so nothing on disk carries one and the figure
    says descaled mass rather than dollars."""
    assert cli.kappa_of({}, None) is None
    assert cli.kappa_of({"instance": "/nowhere/instance.json.gz"}, None) is None
    assert cli.kappa_of({"kappa": 1234.0}, None) == 1234.0
    assert cli.kappa_of({"kappa": 1234.0}, 7.0) == 7.0


def test_draw_bundle_map_passes_label_room_and_leader_radii_to_place_labels():
    """The small northeast states and a split CA need more label room and a longer leader
    search than `us_maps._place_labels`'s own defaults; `draw_bundle_map` must hand its two
    module constants through rather than falling back to the library defaults."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots()
    try:
        payload = {
            "states": {},
            "districts": {"D1": {"color": "#336699"}},
            "district_reach": {"D1": {"rings": [[[0.0, 0.0], [0.0, 10.0], [10.0, 10.0],
                                                 [10.0, 0.0], [0.0, 0.0]]],
                                     "color": "#336699"}},
        }
        meta = {"D1": {"wholesaler": "R0001", "mass": "5", "staffed": "1"}}
        run = {"zips_by_bundle": {"N": {"90001": "D1"}}, "zip_state": {"90001": "S0"}}

        captured = {}
        orig = cli.us_maps._place_labels

        def fake_place_labels(fig_, ax_, order, anchors, footprint, **kw):
            captured.update(kw)

        cli.us_maps._place_labels = fake_place_labels
        try:
            cli.draw_bundle_map(fig, ax, "N", payload, meta, run, None)
        finally:
            cli.us_maps._place_labels = orig

        assert captured["min_ratio"] == cli.LABEL_ROOM
        assert captured["leader_radii"] == cli.LEADER_RADII
    finally:
        plt.close(fig)


def test_place_labels_with_a_wider_leader_radii_moves_a_too_small_label_away_from_its_anchor():
    """A footprint of zero always fails `min_ratio`, so the label must move; with
    `leader_radii=(0.2, 0.3)` on a 0-100 axes the moved label should land at least 20 units
    (the inner radius) from its anchor, not at the old hard-coded 5-9 unit distance."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots()
    try:
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 100)
        anchors = {"D1": (50.0, 50.0)}
        footprint = {"D1": 0.0}
        cli.us_maps._place_labels(fig, ax, ["D1"], anchors, footprint, fontsize=8,
                                  leader_radii=(0.2, 0.3))
        lx, ly = ax.texts[0].get_position()
        dist = ((lx - 50.0) ** 2 + (ly - 50.0) ** 2) ** 0.5
        assert dist >= 0.2 * 100 - 1e-6
    finally:
        plt.close(fig)
