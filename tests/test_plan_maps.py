"""test_plan_maps.py: tools/plan_maps.py on a toy run directory.

No network and no gazetteer: `td.geo.zcta_points` is stubbed with six hand-placed points and
`states_outline` returns `None`, the no-basemap branch `tools/us_maps.py::clip_region`
documents.  `state_rook` is stubbed too, with square polygons at known centres, so `extent_km`
has an arithmetic answer rather than a plausible one.

The toy carries the two shapes the panels exist to show: a pure national district that leaves
two zips unserved (drawn grey), and one merged WH+FI district that appears on both of those
panels under the same id.
"""
from __future__ import annotations

import csv
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
import plan_maps as cli                            # noqa: E402

ZIPS = [f"{10000 + i:05d}" for i in range(6)]
STATES = ["S0", "S0", "S1", "S1", "S2", "S2"]
# a grid rather than a line: six collinear points have a degenerate Voronoi diagram
POINTS = {z: (-100.0 + 1.0 * (i // 2), 40.0 + 0.5 * (i % 2)) for i, z in enumerate(ZIPS)}

# state centres in LAEA metres: S0 to S1 is 100 km, S0 to S2 is 300 km
CENTRES = {"S0": (0.0, 0.0), "S1": (100_000.0, 0.0), "S2": (300_000.0, 0.0)}
ADJ = {"S0": ("S1",), "S1": ("S0", "S2"), "S2": ("S1",)}

# national: four zips in one pure N district, two served by nobody
# wh and fi: every zip in one merged WHFI district, the same id on both panels
NATIONAL = ["N_01", "N_01", "N_01", "N_01", cli.OTHER, cli.OTHER]
MERGED = ["M_01"] * 6
WHOLESALERS = {"N_01": "R0001", "M_01": "R0002"}


def _polys() -> dict:
    import shapely

    return {s: shapely.box(x - 5_000.0, y - 5_000.0, x + 5_000.0, y + 5_000.0)
            for s, (x, y) in CENTRES.items()}


def _write_run(run_dir: str) -> None:
    """A realised run: `assignment.csv` and `districts.csv`, no instance and no projection."""
    with open(os.path.join(run_dir, "assignment.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["zip", "state", "channel", "file_channel", "district", "bundle",
                    "wholesaler", "M_cell"])
        for i, (z, st) in enumerate(zip(ZIPS, STATES)):
            for chan in ("N_WH", "N_FI"):
                d = NATIONAL[i]
                w.writerow([z, st, chan, "national", d, "N" if d != cli.OTHER else "",
                            WHOLESALERS.get(d, ""), 1.0])
            for chan, panel in (("WH", "wh"), ("FI", "fi")):
                w.writerow([z, st, chan, panel, MERGED[i], "WHFI", WHOLESALERS["M_01"], 2.0])

    with open(os.path.join(run_dir, "districts.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["district", "bundle", "n_zips", "mass", "wholesaler", "pieces"])
        w.writerow(["N_01", "N", 4, 8.0, "R0001", 2])
        w.writerow(["M_01", "WHFI", 6, 24.0, "R0002", 1])


def _run(run_dir: str, extra=()) -> int:
    orig = (td_geo.zcta_points, td_geo.states_outline, td_geo.state_rook)
    td_geo.zcta_points = lambda *a, **kw: dict(POINTS)
    td_geo.states_outline = lambda *a, **kw: None
    td_geo.state_rook = lambda *a, **kw: (ADJ, _polys())
    try:
        return cli.main([run_dir, "--dpi", "60", *extra])
    finally:
        td_geo.zcta_points, td_geo.states_outline, td_geo.state_rook = orig


def _toy(tmp: str) -> str:
    run_dir = os.path.join(tmp, "run")
    os.makedirs(run_dir)
    _write_run(run_dir)
    return run_dir


def test_a_toy_run_renders_one_png_per_channel_and_an_overview():
    """One panel per business channel, never per bundle: the merged district is on two of
    them and the pure national one on the third."""
    with tempfile.TemporaryDirectory() as tmp:
        run_dir = _toy(tmp)
        assert _run(run_dir) == 0

        for name in ("national.png", "wh.png", "fi.png", "all.png"):
            path = os.path.join(run_dir, "maps", name)
            assert os.path.exists(path), name
            assert os.path.getsize(path) > 1000, (name, os.path.getsize(path))
        # a bundle panel is exactly what this driver no longer writes
        assert not os.path.exists(os.path.join(run_dir, "maps", "WHFI.png"))


def test_metrics_carry_one_row_per_district_with_extent_from_the_state_centroids():
    """`extent_km` is the widest gap between the district's own state centroids: N_01 spans
    S0 and S1, 100 km apart, and M_01 reaches S2 as well, 300 km from S0."""
    with tempfile.TemporaryDirectory() as tmp:
        run_dir = _toy(tmp)
        _run(run_dir)

        with open(os.path.join(run_dir, "maps", "metrics.csv"), encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        assert list(rows[0]) == list(cli.COLUMNS)
        by_district = {r["district"]: r for r in rows}
        assert sorted(by_district) == ["M_01", "N_01"]

        assert float(by_district["N_01"]["extent_km"]) == 100.0
        assert float(by_district["M_01"]["extent_km"]) == 300.0
        assert int(by_district["N_01"]["n_states"]) == 2
        assert int(by_district["M_01"]["n_states"]) == 3
        assert int(by_district["N_01"]["n_zips"]) == 4
        # M_cell summed over the district's own rows, which is what districts.csv reports
        assert float(by_district["N_01"]["mass"]) == 8.0
        assert float(by_district["M_01"]["mass"]) == 24.0
        # the bundle and the fine channels it carries, in td.channels.CHANNELS order
        assert by_district["N_01"]["bundle"] == "N"
        assert by_district["N_01"]["channels"] == "N_WH,N_FI"
        assert by_district["M_01"]["bundle"] == "WHFI"
        assert by_district["M_01"]["channels"] == "WH,FI"
        # districts.csv is where `pieces` and the wholesaler come from
        assert by_district["N_01"]["pieces"] == "2"
        assert by_district["M_01"]["wholesaler"] == "R0002"
        assert float(by_district["M_01"]["hull_area_km2"]) > 0.0


def test_the_fill_class_is_read_off_the_bundle_s_channels():
    """Solid for a pure bundle, diagonal when it carries a national channel too, cross when
    one district holds both WH and FI."""
    assert cli.fill_class("N") == "pure"
    assert cli.fill_class("WH") == "pure"
    assert cli.fill_class("FI") == "pure"
    assert cli.fill_class("WH_PLUS") == "plus"
    assert cli.fill_class("FI_PLUS") == "plus"
    assert cli.fill_class("WHFI") == "merged"
    assert cli.fill_class("WHFI_PLUS") == "merged"
    # a catch-all bundle carries one fine channel and is not in td.channels.BUNDLES
    assert cli.fill_class("OTHER_WH") == "pure"
    assert set(cli.HATCH) == {"pure", "plus", "merged"} and cli.HATCH["pure"] == ""


def test_the_drawn_label_puts_the_wholesaler_under_the_district_id():
    meta = {"N_01": {"wholesaler": "R0001"}, "N_02": {"wholesaler": ""}}
    assert cli.label_of("N_01", meta) == "N_01\nR0001"
    assert cli.label_of("N_02", meta) == "N_02"
    assert cli.label_of("N_03", {}) == "N_03"


def test_a_panel_takes_the_first_row_per_zip_and_reads_other_as_unplaced():
    """`tools/plan_realise.py` writes `other` for a zip no slot serves; that is the grey
    region, not a district, and a second row for the same (channel, zip) never wins."""
    rows = [
        dict(zip="10000", file_channel="wh", district="WH_01"),
        dict(zip="10000", file_channel="wh", district="WH_09"),
        dict(zip="10001", file_channel="wh", district=cli.OTHER),
        dict(zip="10000", file_channel="fi", district="FI_01"),
    ]
    panels = cli.by_panel(rows)
    assert panels["wh"] == {"10000": "WH_01", "10001": ""}
    assert panels["fi"] == {"10000": "FI_01"}
    assert panels["national"] == {}
