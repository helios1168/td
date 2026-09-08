"""geom_export.py -- a zip table's polygons as JSON, so the app can draw a map with no solver.

    .venv/bin/python3 tools/geom_export.py --table <run>/draw.csv --out <run>

writes `<run>/geom.json`.  The Streamlit app runs in its own venv and never imports `td`, so it
cannot build territory itself: shapely, geopandas and the state shapefile all live on the solver
side.  This driver is that seam.  It computes exactly the geometry `figure_district_regions`
draws when handed `zip_state` and `state_polys`, the per-state clipped Voronoi catchment of each
zip dissolved by district, and hands it over as plain coordinate lists:

    {"crs": "laea",
     "districts": {"D01": {"rings": [[[x, y], ...], ...], "color": "#rrggbb"}, ...},
     "states":    {"TX":  {"rings": [[[x, y], ...], ...], "label": [x, y]}, ...}}

Coordinates are the table's own LAEA metres (`td.geo.LAEA`).  Nothing is reprojected: the app
plots them on cartesian axes with a 1:1 aspect, which for an equal-area projection is the map.

`rings` carries exterior rings only, one per polygon part, and a district is legitimately
multi-part (stage 1 is centre-based, so another district's zips can split it).  Holes are
dropped: at 0.35 fill opacity a hole and its surroundings are indistinguishable, and keeping
them would double the vertex count for nothing.  Rings are simplified in metres, which is what
keeps the file small enough to ship to a browser on every rerun -- at the 2 km default a k = 18
CONUS map is a few hundred KB rather than several MB.

Colours come from a generated 50-entry palette (two lightness rotations of 25 evenly spaced
hues, enough for the k = 50 other channels reach) assigned by `us_maps.color_districts` over an
adjacency read off the polygons themselves, so two districts that share a border never share a
hue.  The palette is fixed and the assignment is greedy in a sorted order, so the same table
always produces the same colours.

Confidentiality: `geom.json` holds geography and identifiers only.  No opportunity, no book, no
rep.  Those travel in `draw.csv`, which stays under `battery/results/`.
"""
from __future__ import annotations

import argparse
import colorsys
import importlib.util
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                "..")))

from td import geo, ziptable                                                # noqa: E402

CRS = "laea"
SIMPLIFY = 2000.0              # metres; the coastline is 1:20m generalised already
NDIGITS = 1                    # decimetres: far below any simplify tolerance, and 2 bytes cheaper

N_HUES = 25                    # 25 hues x 2 lightnesses = 50, the largest k any channel asks for
HUE_STRIDE = 9                 # coprime with 25; 9/25 of the wheel is 130 degrees, see `palette`
SATURATION = 0.72
LIGHTNESS = (0.40, 0.62)       # both still read as their own hue at 0.35 fill opacity on white


def _us_maps():
    """`tools/us_maps.py` as a module.  `tools/` is not a package, so this loads it by path."""
    mod = sys.modules.get("us_maps")
    if mod is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "us_maps.py")
        spec = importlib.util.spec_from_file_location("us_maps", path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules["us_maps"] = mod
        spec.loader.exec_module(mod)
    return mod


# ------------------------------------------------------------------------------- the palette
def palette(n_hues: int = N_HUES, lightness=LIGHTNESS, saturation: float = SATURATION) -> list:
    """`len(lightness) * n_hues` hex colours: evenly spaced hues, once per lightness.

    Order matters as much as the set does.  `color_districts` walks the palette and takes the
    least-used entry a neighbour does not already hold, so with 18 districts over 50 colours it
    simply consumes the head of the list in order; laid out by ascending hue that hands the two
    highest-degree districts hues 14 degrees apart, which is no separation at all.  The hues are
    therefore emitted on a stride of `HUE_STRIDE / n_hues` of the wheel, coprime with `n_hues`
    so every hue is still used exactly once and consecutive entries sit 130 degrees apart.

    Each rotation after the first is offset by a fraction of a hue step, so the two rotations
    interleave around the wheel instead of pairing a light and a dark of the same hue, which are
    the two entries a reader is likeliest to confuse once the fill's opacity has washed both out.
    """
    out = []
    for i, light in enumerate(lightness):
        for j in range(n_hues):
            h = ((j * HUE_STRIDE + i / len(lightness)) % n_hues) / n_hues
            r, g, b = colorsys.hls_to_rgb(h, light, saturation)
            out.append("#%02x%02x%02x" % tuple(round(255 * v) for v in (r, g, b)))
    return out


def _adjacency(polys: dict) -> dict:
    """`{district: set(district)}` over districts whose territory touches.

    Read off the dissolved polygons rather than off the zips: the cells tile the land exactly,
    so two districts intersect precisely when they share a border, which is the relation the
    colouring has to respect.  This is available here and is not in `us_maps`' own colouring,
    which runs before any polygon exists and has to approximate it with nearest neighbours.
    """
    import shapely
    ids = sorted(polys, key=str)
    geoms = [polys[d] for d in ids]
    adj = {d: set() for d in ids}
    ia, ib = shapely.STRtree(geoms).query(geoms, predicate="intersects")
    for i, j in zip(ia, ib):
        if i < j:
            adj[ids[i]].add(ids[j])
            adj[ids[j]].add(ids[i])
    return adj


# ------------------------------------------------------------------------------- the geometry
def _parts(geom) -> list:
    """The polygon parts of a geometry, largest first.  Lines and points are dropped, which is
    what `make_valid` can leave behind on a self-touching ring."""
    gs = [g for g in getattr(geom, "geoms", [geom])
          if g.geom_type == "Polygon" and not g.is_empty]
    return sorted(gs, key=lambda g: -g.area)


def _rings(geom, simplify: float) -> list:
    """Exterior rings of a (multi)polygon as `[[x, y], ...]`, simplified in metres.

    `preserve_topology=True` so a simplified ring cannot cross itself and a thin part cannot
    collapse to a line, which would show up on the map as a district losing a peninsula.
    """
    if geom is None or geom.is_empty:
        return []
    if simplify > 0:
        geom = geom.simplify(simplify, preserve_topology=True)
    out = []
    for part in _parts(geom):
        ring = [[round(x, NDIGITS), round(y, NDIGITS)] for x, y in part.exterior.coords]
        if len(ring) >= 4:
            out.append(ring)
    return out


def export(rows: list, states_gdf, simplify: float = SIMPLIFY) -> dict:
    """The `geom.json` payload for one zip table.

    `states_gdf` is `td.geo.states_outline`'s GeoDataFrame, or `None` for no basemap -- which
    also means no per-state clipping and no state rings, the same branch `ziptable.render`
    takes so the tests need neither shapefile nor network.  A row with no district, or with no
    coordinates, holds no ground and is skipped.
    """
    um = _us_maps()
    drawn = [r for r in rows
             if r["district"] and r["x"] is not None and r["y"] is not None]
    if len(drawn) < 2:
        raise ValueError(f"{len(drawn)} labelled and placed zip(s): a Voronoi diagram needs 2")

    districts = {r["zip"]: r["district"] for r in drawn}
    xy = {r["zip"]: (r["x"], r["y"]) for r in drawn}
    zip_state = {r["zip"]: r["state"] for r in drawn}
    keys = sorted(districts)
    state_polys = (None if states_gdf is None
                   else dict(zip(states_gdf["STUSPS"].astype(str), states_gdf.geometry)))

    clip = um.clip_region([xy[z] for z in keys], states_gdf)
    cells = um.voronoi_cells(keys, xy, clip,
                             zip_state=None if state_polys is None else zip_state,
                             state_polys=state_polys)
    polys = um.dissolve(cells, districts)
    colors = um.color_districts(_adjacency(polys), palette())

    out = {"crs": CRS, "districts": {}, "states": {}}
    for d in sorted(polys, key=str):
        out["districts"][str(d)] = {"rings": _rings(polys[d], simplify), "color": colors[d]}
    if states_gdf is not None:
        for code, geom in zip(states_gdf["STUSPS"].astype(str), states_gdf.geometry):
            rings = _rings(geom, simplify)
            if not rings:
                continue
            p = _parts(geom)[0].representative_point()          # inside the largest part
            out["states"][str(code)] = {"rings": rings,
                                        "label": [round(p.x, NDIGITS), round(p.y, NDIGITS)]}
    return out


def write(path: str, geom: dict) -> str:
    """Write `geom` to `path` as compact JSON, creating the directory if it is absent."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(geom, fh, separators=(",", ":"))
    return path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="write a zip table's polygons to <out>/geom.json")
    ap.add_argument("--table", required=True, help="the zip table to draw (draw.csv)")
    ap.add_argument("--out", required=True, help="directory geom.json is written into")
    ap.add_argument("--geo-cache", default=geo.DEFAULT_DEST, help="state shapefile cache")
    ap.add_argument("--simplify", type=float, default=SIMPLIFY,
                    help="ring tolerance in metres; 0 keeps every vertex")
    ap.add_argument("--no-basemap", action="store_true",
                    help="skip the shapefile: clip to the padded hull of the points, no states")
    a = ap.parse_args(argv)

    rows = ziptable.read(a.table)
    states = None if a.no_basemap else geo.states_outline(a.geo_cache)
    g = export(rows, states, a.simplify)
    path = write(os.path.join(a.out, "geom.json"), g)
    print(f"geom: {len(g['districts'])} district(s), {len(g['states'])} state(s), "
          f"{os.path.getsize(path) / 1e6:.2f} MB -> {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
