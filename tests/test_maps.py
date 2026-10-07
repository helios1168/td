"""tests/test_maps.py -- the required-look renderer's #128 pieces (`tools/maps/`).

- The cross-state hatch: on a toy ZCTA crossing a state line, the hatched part a ZIP page draws
  equals the polygon less its filed state's polygon to within 1%, and the rest is drawn as
  before; a ZCTA that crosses nothing is drawn unchanged.  With the 2025 state and ZCTA files at
  hand (`$TD_REPO/data/public`), ZCTA 89421 (filed OR) spills its 935 km² of Nevada land.
- The footer: `spill.spill_only` on toys (a state counts only when the ledger holds it in one
  district and county land over 1 km² draws it in another), and on #127's
  `runs/exp/contig/whole127/ifa46-whole` when present: 0 ledger splits and the 32 states the
  #128 count gave.
- The summary's channel fill (`summary.draw_channel_map`): a state held whole is one state-shaped
  patch, a split state is drawn by ZCTA with its no-ZCTA land grey, and a spill is hatched on top.
- The caption: `summary.final_bands` takes `contig.json`'s repair band, else `run.json`'s
  `final_delta`, else the spec's, on a ±15% channel and a #127 map.
- `render.INPUTS` carries the state file and the overlay, and a render goes stale when either
  changes.
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
IFA46_SPILL_ONLY = ("AL AR AZ CA CO GA IA ID IL KS KY LA MD MN MO MS MT ND NE NH NM NV OK OR SD TN TX "
                    "UT VA WA WV WY").split()


def _load(name: str, file: str):
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, os.path.join(MAPS, file))
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
    return sys.modules[name]


def _toy():
    """A 10 x 10 km ZCTA filed in state A whose east 4 km lie in state B."""
    import shapely
    poly = shapely.box(0, 0, 10_000, 10_000)
    a, b = shapely.box(-50_000, -50_000, 6_000, 50_000), shapely.box(6_000, -50_000, 50_000, 50_000)
    return poly, a, b


def _area(path) -> float:
    """The area a matplotlib path fills (its rings, the nonzero rule as `_polygon_path` writes)."""
    import shapely
    total = 0.0
    for ring in path.to_polygons():
        total += shapely.Polygon(ring).area * (1 if shapely.LinearRing(ring).is_ccw else -1)
    return total


def test_the_hatched_part_is_the_polygon_less_its_filed_state():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    zp = _load("maps_zip_pages", "zip_pages.py")
    sp = zp.spill_mod
    poly, a, b = _toy()
    spill = sp.spill_part(poly, a)
    want = poly.difference(a).area
    assert abs(spill.area - want) <= 0.01 * want
    kept, hatched = sp.split_drawn(poly, spill)
    assert hatched is spill and abs(kept.area - poly.intersection(a).area) <= 1e-6 * poly.area
    assert sp.split_drawn(poly, None) == (poly, None)

    import shapely
    other = shapely.box(20_000, 0, 30_000, 10_000)
    fig, ax = plt.subplots()
    zp.draw(ax, {"D1": {"z1", "z2"}}, {"z1": poly, "z2": other}, {"D1": poly.union(other)}, {"D1": "#e6194b"},
            [], {}, None, None, labels=False, spill={"z1": spill})
    hatches = [p for p in ax.patches if p.get_hatch()]
    assert len(hatches) == 1 and abs(_area(hatches[0].get_path()) - want) <= 0.01 * want
    fill = ax.collections[0]
    areas = sorted(_area(p) for p in fill.get_paths())
    assert abs(areas[0] - poly.intersection(a).area) <= 0.01 * poly.area
    assert abs(areas[1] - other.area) <= 1e-6 * other.area           # crosses nothing: unchanged
    plt.close(fig)


def test_a_real_cross_state_zcta_spills_its_neighbour_land():
    sp = _load("maps_zip_pages", "zip_pages.py").spill_mod
    if not (os.path.exists(sp.STATE_FILE) and os.path.exists(sp.ZCTA_FILE)):
        print(f"SKIP  test_maps.py: no {sp.STATE_FILE} or {sp.ZCTA_FILE}")
        return
    land = sp.state_land(sp.fips_usps())
    assert land["89421"]["NV"] > 900e6
    got = sp.spill_geometry({"89421": "OR"})["89421"]
    assert abs(got.area - land["89421"]["NV"]) <= 0.01 * land["89421"]["NV"], (got.area, land["89421"])


def test_spill_only_names_states_split_only_by_cross_state_land():
    sp = _load("maps_zip_pages", "zip_pages.py").spill_mod
    owned = {("z1", "IFA"): "D1", ("z2", "IFA"): "D2", ("z3", "IFA"): "D2", ("z4", "IFA"): "D3",
             ("z5", "IFA"): "D3"}
    filed = {"z1": "OR", "z2": "NV", "z3": "UT", "z4": "UT", "z5": "ID"}
    land = {"z1": {"OR": 9e8, "NV": 5e8}, "z3": {"UT": 9e8, "ID": 0.5e6}, "z5": {"ID": 1e9, "WY": 2e6}}
    # NV: held in D2, drawn in D1 too -> counts.  UT: the ledger splits it (D2, D3) -> not spill-only.
    # ID: z3's 0.5 km² is under the 1 km² rule.  WY: no ZCTA filed there, so not in the domain.
    assert sp.spill_only(owned, filed, land) == {"IFA": ["NV"]}
    assert sp.spill_text(["NV"]) == "1 state looks split only because of cross-state ZIPs: NV"
    assert sp.spill_text([]).startswith("0 states look split only because of cross-state ZIPs: none")
    summary = _load("maps_summary", "summary.py")
    assert summary.spill_text(["NV", "UT"]) == sp.spill_text(["NV", "UT"])


def test_the_ifa46_whole_footer_names_its_32_spill_only_states():
    sp = _load("maps_zip_pages", "zip_pages.py").spill_mod
    if not (os.path.exists(os.path.join(WHOLE, "ledger.csv")) and os.path.exists(sp.STATE_FILE)):
        print(f"SKIP  test_maps.py: no {WHOLE} or {sp.STATE_FILE}")
        return
    owned, filed = sp.ledger_owned(os.path.join(WHOLE, "ledger.csv"))
    held = {}
    for (z, ch), d in owned.items():
        held.setdefault((ch, filed[z]), set()).add(d)
    assert sum(len(ds) > 1 for ds in held.values()) == 0                   # the ledger's split count
    assert sp.spill_only(owned, filed, sp.state_land(sp.fips_usps())) == {"IFA": IFA46_SPILL_ONLY}


def test_the_summary_fills_whole_states_whole_and_split_states_by_zcta():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import shapely
    import types
    summary = _load("maps_summary", "summary.py")
    poly, a, b = _toy()
    z2 = shapely.box(20_000, 0, 30_000, 10_000)                   # in B, held by D2
    z3 = shapely.box(30_000, 0, 40_000, 10_000)                   # in B, held by D3: B is split
    spill = poly.difference(a)
    geom = {"polys": {"z1": poly, "z2": z2, "z3": z3}, "move": list, "states": {"A": a, "B": b},
            "gap": shapely.box(40_000, 0, 41_000, 10_000).union(shapely.box(-2_000, 0, -1_000, 1_000)),
            "spill": {"z1": [("B", spill)]}}
    ps = types.SimpleNamespace(
        REACH_FILL_ALPHA=0.6, LABEL_ROOM=4.0, LEADER_RADII=(0.09, 0.16), us_maps=types.SimpleNamespace(TEXT="k"),
        _payload_state_labels=lambda ax, states: None, _reach_polygon=lambda info: None,
        bundle_title=lambda b: b, bundle_strip=lambda bundle, run, meta, kappa: "strip")
    run = {"zips_by_bundle": {"IFA": {"z1": "D1", "z2": "D2", "z3": "D3"}},
           "zip_state": {"z1": "A", "z2": "B", "z3": "B"}}
    payload = {"districts": {d: {"color": c} for d, c in (("D1", "#e6194b"), ("D2", "#3cb44b"), ("D3", "#4363d8"))}}
    fig, ax = plt.subplots()
    assert summary.draw_channel_map(ps, geom, fig, ax, "IFA", payload, {}, run, None) == "strip"
    filled = [p for p in ax.patches if p.get_facecolor()[3] > 0 and not p.get_hatch()]
    whole = [p for p in filled if matplotlib.colors.to_hex(p.get_facecolor())
             == matplotlib.colors.to_hex(summary._on_white("#e6194b", 0.6))]
    assert len(whole) == 1 and abs(_area(whole[0].get_path()) - a.area) <= 1e-6 * a.area   # A whole
    grey = [p for p in filled if matplotlib.colors.to_hex(p.get_facecolor()) == summary.UNASSIGNED]
    assert len(grey) == 1 and abs(_area(grey[0].get_path()) - 1e7) <= 1                  # B's gap only
    assert sorted(len(c.get_paths()) for c in ax.collections) == [1, 1]                   # z2, z3 by ZCTA
    (hatch,) = [p for p in ax.patches if p.get_hatch()]
    assert abs(_area(hatch.get_path()) - spill.area) <= 0.01 * spill.area
    assert hatch.get_zorder() > max(p.get_zorder() for p in filled)
    plt.close(fig)

    run["zips_by_bundle"]["IFA"].update(z2="D1", z3="D1")         # B now whole in D1, z1's own district
    fig, ax = plt.subplots()
    summary.draw_channel_map(ps, geom, fig, ax, "IFA", payload, {}, run, None)
    assert not [p for p in ax.patches if p.get_hatch()] and not ax.collections
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
    for name in ("UNASSIGNED", "SPILL_HATCH", "SPILL_TINT", "SPILL_HATCH_W"):
        assert getattr(summary, name) == getattr(zp, name), name
    assert summary.SPILL_KM2 == zp.spill_mod.SPILL_KM2


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
    if os.path.exists(os.path.join(PC_A, "run.json")):
        assert summary.final_bands(PC_A) == {"FI": 0.15, "WH": 0.1, "national": 0.1}
    else:
        print(f"SKIP  test_maps.py: no {PC_A}")
    if os.path.exists(os.path.join(WHOLE, "run.json")):
        assert summary.final_bands(WHOLE) == {"IFA": 3.1025}
    else:
        print(f"SKIP  test_maps.py: no {WHOLE}")


def test_render_inputs_track_the_state_file_and_the_overlay():
    render = _load("maps_render", "render.py")
    assert "$TD_REPO/data/public/tl_2025_us_state.zip" in render.INPUTS
    assert "$ROOT/reference/2025/zcta_overlay.csv.gz" in render.INPUTS
    assert render.input_path("/r", "ledger.csv") == os.path.join("/r", "ledger.csv")
    assert render.input_path("/r", "$ROOT/reference/2025/zcta_overlay.csv.gz") == os.path.join(
        render.ROOT, "reference", "2025", "zcta_overlay.csv.gz")
    saved = render.TD_REPO
    with tempfile.TemporaryDirectory() as tmp:
        render.TD_REPO = tmp
        try:
            run = os.path.join(tmp, "run")
            os.makedirs(run)
            for n in render.INPUTS:
                path = render.input_path(run, n)
                if not n.startswith("$ROOT/"):
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    with open(path, "w") as fh:
                        fh.write(n)
            fac = os.path.join(tmp, "tables.json")
            with open(fac, "w") as fh:
                fh.write("{}")
            with open(os.path.join(run, "render.json"), "w") as fh:
                json.dump({"renderer": {"code_sha256": render.code_sha256()}, "label": "x",
                           "fac": {"path": fac, "sha256": render.sha256_file(fac)}, "images": {},
                           "inputs": {n: render.sha256_file(render.input_path(run, n)) for n in render.INPUTS}}, fh)
            assert render.current(run, "x") == (True, "")
            with open(os.path.join(tmp, "data", "public", "tl_2025_us_state.zip"), "a") as fh:
                fh.write("2026")
            assert render.current(run, "x") == (
                False, "$TD_REPO/data/public/tl_2025_us_state.zip changed since the render")
        finally:
            render.TD_REPO = saved
