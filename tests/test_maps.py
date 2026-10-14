"""tests/test_maps.py -- the required-look renderer's #128 pieces (`tools/maps/`).

- The summary's channel fill (`summary.draw_channel_map`): a state held whole is one state-shaped
  patch; a split state is drawn by ZCTA clipped to its filed state, so no colour crosses a state
  line, and its land in no ZCTA filed there (a neighbour's ZCTA's land across the line included)
  is shaded by the nearest district by default, or grey.
- `summary.nearest_gap` splits no-ZCTA land between the nearest districts.
- The clip is display only: an M1-failing toy keeps its "FAILS M1" title on the summary, and the
  footer says M1 is judged on whole ZCTAs.
- The caption: `summary.final_bands` takes `contig.json`'s repair band, else `run.json`'s
  `final_delta`, else the spec's, on a ±15% channel and a #127 map.
- The ZIP pages' summary page: per-state territory counts by channel and split states from a toy
  ledger (`zip_pages.state_territories`, `split_states`, `state_text`); the metros, the heaviest
  Metro Areas by $ named by their first principal city (`top_metros`, `metro_name`); and
  `place_labels` drops a label that would overlap one already placed.
- The executive style (`zip_pages.py --style exec`): `exec_page` writes `zip_exec_<channel>.png` for
  a toy run, its labels read `N-08 · $1.2B`, and a palette shorter than the neighbours need still colours every district.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
MAPS = os.path.join(ROOT, "tools", "maps")
TD_REPO = os.environ.get("TD_REPO", ROOT)
WHOLE = os.path.join(TD_REPO, "runs", "exp", "contig", "whole127", "ifa46-whole")
PC_A = os.path.join(TD_REPO, "runs", "exp", "contig", "plancheck", "nocomb_13_12_23-pc-A")


def _load(name: str, file: str):
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, os.path.join(MAPS, file))
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
    return sys.modules[name]


def _area(path) -> float:
    """The area a matplotlib path fills (its rings, the nonzero rule as `_polygon_path` writes)."""
    import shapely
    total = 0.0
    for ring in path.to_polygons():
        total += shapely.Polygon(ring).area * (1 if shapely.LinearRing(ring).is_ccw else -1)
    return total


def _states():
    """Two 100 km tall states, A west of x = 6 km and B east of it."""
    import shapely
    return shapely.box(-50_000, -50_000, 6_000, 50_000), shapely.box(6_000, -50_000, 50_000, 50_000)


def _channel_map(geom: dict, held: dict, filed: dict, gap_fill: str):
    """`draw_channel_map` on one toy channel, IFA: the figure, its axes."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import types
    summary = _load("maps_summary", "summary.py")
    ps = types.SimpleNamespace(
        REACH_FILL_ALPHA=0.6, LABEL_ROOM=4.0, LEADER_RADII=(0.09, 0.16), us_maps=types.SimpleNamespace(TEXT="k"),
        _payload_state_labels=lambda ax, states: None, _reach_polygon=lambda info: None,
        bundle_title=lambda b: b, bundle_strip=lambda bundle, run, meta, kappa: "strip")
    colours = ("#e6194b", "#3cb44b", "#4363d8", "#f58231")
    payload = {"districts": {f"D{i}": {"color": c} for i, c in enumerate(colours, 1)}}
    run = {"zips_by_bundle": {"IFA": held}, "zip_state": filed}
    fig, ax = plt.subplots()
    assert summary.draw_channel_map(ps, geom, fig, ax, "IFA", payload, {}, run, None, gap_fill=gap_fill) == "strip"
    return fig, ax


def test_the_summary_fills_whole_states_whole_and_clips_split_states_zctas():
    import matplotlib
    import matplotlib.pyplot as plt
    import shapely
    summary = _load("maps_summary", "summary.py")
    a, b = _states()
    z1 = shapely.box(0, 0, 10_000, 10_000)                        # filed A, its east 4 km in B
    z2 = shapely.box(20_000, 0, 30_000, 10_000)                   # in B
    z3 = shapely.box(30_000, 0, 40_000, 10_000)                   # in B
    z4 = shapely.box(-30_000, 0, -20_000, 10_000)                 # in A
    polys = {"z1": z1, "z2": z2, "z3": z3, "z4": z4}
    filed = {"z1": "A", "z2": "B", "z3": "B", "z4": "A"}
    b_gap = b.area - z2.area - z3.area                            # z1's land in B included
    corners = 8 * summary.OPEN_M ** 2 * (1 - 3.14159 / 4)         # the opening rounds 8 corners

    def geom():
        return {"polys": polys, "move": list, "states": {"A": a, "B": b}, "cut": {}}

    # A whole in D1: one state-shaped patch; B split (D2, D3): by ZCTA, its other land grey.
    fig, ax = _channel_map(geom(), {"z1": "D1", "z4": "D1", "z2": "D2", "z3": "D3"}, filed, "grey")
    filled = [p for p in ax.patches if p.get_facecolor()[3] > 0]
    whole = [p for p in filled if matplotlib.colors.to_hex(p.get_facecolor())
             == matplotlib.colors.to_hex(summary._on_white("#e6194b", 0.6))]
    assert len(whole) == 1 and abs(_area(whole[0].get_path()) - a.area) <= 1e-6 * a.area
    (grey,) = [p for p in filled if matplotlib.colors.to_hex(p.get_facecolor()) == summary.UNASSIGNED]
    assert abs(_area(grey.get_path()) - b_gap) <= corners + 1e-4 * b_gap
    assert sorted(len(c.get_paths()) for c in ax.collections) == [1, 1]                   # z2, z3
    plt.close(fig)

    # A split too (D1, D4): z1 is clipped at the state line; nothing filled crosses x = 6 km.
    fig, ax = _channel_map(geom(), {"z1": "D1", "z4": "D4", "z2": "D2", "z3": "D3"}, filed, "grey")
    paths = [p for c in ax.collections for p in c.get_paths()]
    assert sorted(round(_area(p)) for p in paths) == sorted(round(x) for x in (6e7, 1e8, 1e8, 1e8))
    for p in paths:
        x0, x1 = p.get_extents().x0, p.get_extents().x1
        assert x1 <= 6_000 + 1e-6 or x0 >= 6_000 - 1e-6, (x0, x1)
    assert len([p for p in ax.patches if p.get_facecolor()[3] > 0
                and matplotlib.colors.to_hex(p.get_facecolor()) == summary.UNASSIGNED]) == 2
    plt.close(fig)

    # The default: B's other land goes to its nearest districts, none of it grey.
    fig, ax = _channel_map(geom(), {"z1": "D1", "z4": "D1", "z2": "D2", "z3": "D3"}, filed, "nearest")
    assert not [p for p in ax.patches if matplotlib.colors.to_hex(p.get_facecolor()) == summary.UNASSIGNED]
    drawn = sum(_area(p) for c in ax.collections for p in c.get_paths())
    assert abs(drawn - (b_gap + z2.area + z3.area)) <= corners + 1e-3 * b.area
    plt.close(fig)


def test_nearest_gap_shades_no_zcta_land_by_the_nearest_district():
    import shapely
    summary = _load("maps_summary", "summary.py")
    west, east = shapely.box(0, 0, 10_000, 10_000), shapely.box(30_000, 0, 40_000, 10_000)
    gap = shapely.box(10_000, 0, 30_000, 10_000)                 # between them: split at x = 20 km
    got = summary.nearest_gap(gap, [west, east], ["W", "E"])
    w, e = shapely.union_all(got["W"]), shapely.union_all(got["E"])
    assert abs(w.area + e.area - gap.area) <= 1e-6 * gap.area
    assert abs(w.area - gap.area / 2) <= 0.05 * gap.area and w.centroid.x < 20_000 < e.centroid.x


def test_the_summary_and_zip_pages_share_their_style():
    summary, zp = _load("maps_summary", "summary.py"), _load("maps_zip_pages", "zip_pages.py")
    for name in ("UNASSIGNED", "OPEN_M"):
        assert getattr(summary, name) == getattr(zp, name), name


def test_the_clip_is_display_only_and_an_m1_failure_keeps_its_title():
    import inspect
    render, summary = _load("maps_render", "render.py"), _load("maps_summary", "summary.py")
    text = render.title("toy: a layout (K 2)", {"status": "fail", "summary": "1 detached piece",
                                                 "diagnostic": False})
    assert text == "toy: a layout (K 2), FAILS M1"
    params = {"final_bands_text": "IFA ±10%", "bands_text": "IFA ±10.0%", "dist_max": "900",
              "sizes_text": "IFA 6"}
    assert summary.title_text(text, params).splitlines()[0] == text
    assert summary.FOOTER_CLIP == ("ZCTAs drawn clipped to their filed state; M1 is judged on whole "
                                   "ZCTAs (ZIP pages)")
    assert summary.FOOTER_GAP["nearest"] == ("land in no ZCTA shaded by nearest district (exact on "
                                             "the ZIP pages)")
    assert inspect.signature(render.render).parameters["gap_fill"].default == "nearest"
    assert inspect.signature(summary.draw_channel_map).parameters["gap_fill"].default == "nearest"


def test_the_summary_page_counts_territories_and_splits_per_state():
    zp = _load("maps_zip_pages", "zip_pages.py")
    rows = [("national", "national_01", "TX"), ("national", "national_02", "TX"),
            ("national", "national_02", "OK"), ("WIFI", "WIFI_01", "TX"), ("WIFI", "WIFI_01", "TX"),
            ("WIFI", "WIFI_02", "OK"), ("WIFI", "WIFI_03", "OK"), ("WIFI", "WIFI_04", "NM")]
    counts = zp.state_territories(rows)
    assert counts == {"TX": {"national": 2, "WIFI": 1}, "OK": {"national": 1, "WIFI": 2},
                      "NM": {"WIFI": 1}}
    assert zp.split_states(counts) == {"national": ["TX"], "WIFI": ["OK"]}
    assert zp.state_text("TX", counts["TX"], ["national", "WIFI"]) == "TX\nN 2 · W 1"
    assert zp.state_text("NM", counts["NM"], ["national", "WIFI"]) == "NM\nW 1"


def test_the_metros_are_the_heaviest_metro_areas_by_their_principal_city():
    zp = _load("maps_zip_pages", "zip_pages.py")
    assert zp.metro_name("Dallas-Fort Worth-Arlington, TX Metro Area") == "Dallas–Fort Worth"
    assert zp.metro_name("New York-Newark-Jersey City, NY-NJ Metro Area") == "New York"
    assert zp.metro_name("Boise City, ID Metro Area") == "Boise City"
    areas = {"1": ("New York-Newark-Jersey City, NY-NJ Metro Area", -74.0, 40.7),
             "2": ("Dallas-Fort Worth-Arlington, TX Metro Area", -97.0, 32.8),
             "3": ("Aberdeen, SD Micro Area", -98.7, 45.5),
             "4": ("Boise City, ID Metro Area", -116.2, 43.6)}
    weight = {"1": 5.0, "2": 9.0, "3": 50.0, "4": 1.0, "5": 7.0, "6": 0.0}
    assert zp.top_metros(weight, areas, 2) == [("Dallas–Fort Worth", -97.0, 32.8), ("New York", -74.0, 40.7)]
    assert [m[0] for m in zp.top_metros(weight, areas)] == ["Dallas–Fort Worth", "New York", "Boise City"]


def test_place_labels_drops_a_label_that_would_overlap():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    zp = _load("maps_zip_pages", "zip_pages.py")
    fig, ax = plt.subplots(figsize=(4, 3))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    items = [(50, 50, "Alpha"), (50.2, 50.1, "Beta"), (10, 90, "Gamma"), (500, 50, "Outside")]
    placed = zp.place_labels(ax, items, near=zp.NEAR[:1], leader=[])
    assert [t.get_text() for t in placed] == ["Alpha", "Gamma"]
    assert len(ax.lines) == 2                                     # a dot per placed label only
    placed = zp.place_labels(ax, [(80, 20, "Delta")], near=zp.NEAR[:1], leader=[], avoid=placed)
    assert [t.get_text() for t in placed] == ["Delta"]
    plt.close(fig)


def _run(tmp: str, channels: dict, contig: dict | None = None, spec: str | None = None) -> str:
    os.makedirs(tmp, exist_ok=True)
    path = os.path.join(tmp, "scenario.toml")
    with open(path, "w") as fh:
        fh.write(spec or "")
    with open(os.path.join(tmp, "run.json"), "w") as fh:
        json.dump({"channels": channels, "spec": path}, fh)
    if contig is not None:
        with open(os.path.join(tmp, "contig.json"), "w") as fh:
            json.dump({"channels": contig}, fh)
    return tmp


def test_the_caption_prints_each_channels_final_band():
    summary = _load("maps_summary", "summary.py")
    with tempfile.TemporaryDirectory() as tmp:
        repaired = _run(os.path.join(tmp, "a"), {"FI": {"final_delta": None}, "WH": {"final_delta": 0.1}},
                        {"FI": {"repair_band": {"delta": 0.15}}, "WH": {}})
        assert summary.final_bands(repaired) == {"FI": 0.15, "WH": 0.1}
        whole = _run(os.path.join(tmp, "b"), {"IFA": {"delta": 3.1025, "final_delta": 3.1025}})
        assert summary.final_bands(whole) == {"IFA": 3.1025}
    assert [summary._pct(x) for x in (0.1, 0.15, 3.1025, 0.0938)] == ["10", "15", "310.2", "9.4"]
    # a window band (#112) prints as its asymmetric window, a channel without one as ±δ
    assert summary.window_text(0.947, 1.361) == "-5.3%/+36.1%"
    assert summary.window_text(0.85 / 0.87, 1.15 / 0.87) == "-2.3%/+32.2%"
    assert summary.band_text({"delta": 0.1}) is None
    assert summary.band_text({"delta": 0.1, "band_lo": 0.947, "band_hi": 1.361}) == "-5.3%/+36.1%"
    if os.path.exists(os.path.join(PC_A, "run.json")):
        assert summary.final_bands(PC_A) == {"FI": 0.15, "WH": 0.1, "national": 0.1}
    else:
        print(f"SKIP  test_maps.py: no {PC_A}")
    if os.path.exists(os.path.join(WHOLE, "run.json")):
        assert summary.final_bands(WHOLE) == {"IFA": 3.1025}
    else:
        print(f"SKIP  test_maps.py: no {WHOLE}")


def test_the_exec_style_writes_its_page_for_a_toy_run():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import shapely
    zp = _load("maps_zip_pages", "zip_pages.py")
    st = dict(zip(("A", "B"), _states()))
    polys = {"00001": shapely.box(-40_000, -40_000, 0, 40_000), "00002": shapely.box(0, -40_000, 6_000, 40_000),
             "00003": shapely.box(6_000, -40_000, 40_000, 0), "00004": shapely.box(6_000, 0, 40_000, 40_000)}
    rows = {"national_01": {"00001", "00002"}, "national_08": {"00003"}, "national_09": {"00004"}}
    usd = {"national_01": 1234.0, "national_08": 1180.0, "national_09": 960.0}
    assert zp.exec_text("national", "national_08", 1234.0) == "N-08 · \\$1.2B"
    unions = {d: shapely.union_all([polys[z] for z in zs]) for d, zs in rows.items()}
    near = zp.neighbours(unions)
    assert set(zp.colouring(unions, near, zp.EXEC_PALETTE[:2]).values()) <= set(zp.EXEC_PALETTE[:2])
    assert len(zp.EXEC_PALETTE) <= 10
    with tempfile.TemporaryDirectory() as tmp:
        fig, path = zp.exec_page("toy", "national", rows, polys, st, None, usd, tmp)
        plt.close(fig)
        assert os.path.basename(path) == "zip_exec_national.png" and os.path.getsize(path) > 0
