"""geom_export.py -- a zip table's polygons as JSON, so the app can draw a map with no solver.

    .venv/bin/python3 tools/geom_export.py --table <run>/draw.csv --out <run>

writes `<run>/geom.json`.  The Streamlit app runs in its own venv and never imports `td`, so it
cannot build territory itself: shapely, geopandas and the state/ZCTA shapefiles all live on the
solver side.  This driver is that seam.  It hands the app plain coordinate lists:

    {"crs": "laea",
     "districts":       {"D01": {"rings": [[[x, y], ...], ...], "color": "#rrggbb",
                                 "holes": [[[x, y], ...], ...]}, ...},
     "district_reach":  {"D01": {"rings": [[[x, y], ...], ...], "color": "#rrggbb"}, ...},
     "states":          {"TX":  {"rings": [[[x, y], ...], ...], "label": [x, y]}, ...},
     "cells":           {"75001": {"rings": [[[x, y], ...], ...]}, ...},
     "proximity_edges": [["75001", "75002"], ...],
     "proximity_zips":  ["75001", "75002", ...],
     "cells_source":    "tl_2025_us_zcta520.shp simplify=250m"}

Coordinates are the table's own LAEA metres (`td.geo.LAEA`).  Nothing is reprojected: the app
plots them on cartesian axes with a 1:1 aspect, which for an equal-area projection is the map.

`rings` carries exterior rings only, one per polygon part, and a district is legitimately
multi-part (stage 1 is centre-based, so another district's zips can split it).  Rings are
simplified in metres, which is what keeps the file small enough to ship to a browser on every
rerun.

A district may also carry `"holes"`: real gaps between its own zips' ZCTAs (unpopulated land,
water, an unassigned area, decision 1), one interior ring per gap, same simplify tolerance and
rounding as `rings` -- present only when the district has at least one (a hole-free district
gets no `"holes"` key at all, not an empty list, so a run before this change and a run after it
without a single hole produce the same district shape).  This is a **separate** key from
`rings`, not extra rings mixed into it, specifically so `rings` keeps meaning exactly what it
means today and every existing `fill="toself"` call site keeps working unmodified
(`app/mapfig.py`'s `staffed_figure`, both branches): an interior ring folded into `rings` there
would render as a solid blob rather than a see-through hole.  `figure()`'s outline-only district
loop is the one consumer that strokes `holes`, making the gap actually visible on the board.
Every other ring collection in this file drops interior rings the way `rings` always has --
this includes a donut ZCTA's own `cells` entry, which still shows solid: at 0.35 fill opacity a
hole and its surroundings are indistinguishable there, and cutting it would double `cells`'
vertex count for a visual difference nobody can see, so `cells` and `districts` are now
deliberately different in this one respect.

`cells` are the real 2025 TIGER/Line ZCTA polygons (`td.geo.zcta_polygons`), one per placed zip,
simplified at `CELLS_SIMPLIFY` metres rather than the `--simplify` used for districts/states --
tighter, because a ZCTA boundary is the thing the map is now claiming to show, not a synthetic
catchment.  `districts` are the dissolve of those same real polygons: a district's shape is the
union of its own zips' real ZCTAs, so unpopulated land, water and any unassigned area between
zips shows as a real gap (`rings` loses the ground, `holes` draws its outline) rather than being
tiled over.  `cells_source` records the shapefile basename and the simplify tolerance actually
used, so a stale `geom.json` is identifiable.

`district_reach` is the one drawn layer that is not a published boundary, and it exists because
the union of a district's real ZCTAs has no single outline to read a map by.  The instance
carries 3,713 of the 33,300 CONUS ZCTAs, so a district's real territory is a scatter: on the
k = 18 live run `districts` holds 1,038 rings over 596 holes, a median of 62 parts per district,
and closing gaps under 80 km still leaves a median of 8.  So this layer dissolves the **same
proximity tessellation** `proximity_edges` is built from, state-clipped, and gives one clean
region per district -- the district's *reach*, the ground it is nearest to, not the ground it
holds.  It carries exterior rings only and is meant to be **stroked, never filled**: a fill
would claim territory between the district's zips that the district does not own.  `districts`
remains the honest union, and is what the fills draw.

`proximity_edges` is a **reachability model, not a border graph**, and the name says so: it is
the rook adjacency of the Voronoi tessellation of the zip points, which is the one thing here
still built that way.  It has to be.  The instance carries 3,713 of the 33,300 CONUS ZCTAs, so
real shared boundaries alone leave the zips in 817 components with 474 isolated singletons,
which no districting can use; the tessellation gives every point of the map to its nearest zip
and closes those gaps.  Measured on the k = 18 live run, the two graphs share 4,462 edges of the
tessellation's 10,528 and real adjacency's 4,843, a Jaccard of 0.411.  So two zips joined by a
`proximity_edges` entry are near each other; they are not necessarily neighbours on any
published map, and a district that reads as scattered on screen is not a contiguity failure.

`proximity_zips` is that tessellation's own key set, exported explicitly rather than left for a
consumer to infer from `cells` -- a zip whose point clips away to nothing on the 1:20m coastline
has no proximity cell but can still have a ZCTA, so a consumer that built the graph's vertex set
as "every zip in `cells`" would silently admit it as an isolated, edge-less vertex and make the
split's contiguity guard infeasible.  The tessellation's cells are computed and then discarded:
only their key set and their rook adjacency are exported, never a ring.  Everything the map
draws -- `cells`, `districts`, and the rep territories in `reps.json` -- comes from the real
ZCTA polygons instead, and the district colouring is assigned over their adjacency too.

Measured on the CONUS k = 10 live run at the 2 km/250 m defaults, after `td.geo.zcta_polygons`
was made to subset by zip before reprojecting: `export()` (`proximity`/`dissolve`/`colour`/`cells`
plus the uninstrumented ring-building loop after them) takes about 9.2 s, 5.8 s of it the
`dissolve` phase alone, real ZCTA unions costing far more than the old Voronoi ones did; the
`load` phase (`ziptable.read`, `geo.states_outline`, `geo.zcta_polygons`) takes about 1.3 s;
10.7 s wall for the whole driver.  `geom.json` grows from about 0.91 MB to about 3.6 MB.

Colours come from a generated 50-entry palette (two lightness rotations of 25 evenly spaced
hues, enough for the k = 50 other channels reach) assigned by `us_maps.color_districts` over the
adjacency of the real-ZCTA dissolve, the same geometry `districts` exports, so the hues separate
the ground the reader sees.  That territory does not tile the plane, so adjacency is taken within
`ADJ_TOLERANCE` metres rather than by plain `intersects`, which would miss a pair separated by a
sliver of unassigned land: on the k = 18 live run `intersects` gives 13 adjacent pairs and 1 km
gives 15.  See `_adjacency`.  The palette is fixed and the assignment is greedy in a sorted
order, so the same table always produces the same colours.

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

from td import geo, telemetry, ziptable                                     # noqa: E402

CRS = "laea"
SIMPLIFY = 2000.0              # metres; the coastline is 1:20m generalised already
CELLS_SIMPLIFY = 250.0         # metres; real ZCTA rings, the tolerance the user chose for these
ADJ_TOLERANCE = 1000.0         # metres; two districts this close read as neighbours, `_adjacency`
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


HUE_APART = 0.25               # a quarter turn of the wheel: neighbours at least this far apart


def _hue(hex_colour: str) -> float:
    r, g, b = (int(hex_colour.lstrip("#")[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    return colorsys.rgb_to_hls(r, g, b)[0]


def color_distinct(adj: dict, palette: list, apart: float = HUE_APART) -> dict:
    """Greedy graph colouring with hue distance: `{district: colour}` where two neighbours never
    share a colour and, as far as the palette allows, sit at least `apart` of the wheel from
    each other in hue.

    `us_maps.color_districts` forbids only the identical entry, and a palette of 25 hues then
    hands two neighbours hues 14 degrees apart, or one hue at two lightnesses, which a reader
    cannot tell apart on a map (the user, 2026-09-11).  Vertices are taken in Welsh-Powell order
    (highest degree first, id as tie-break).  Each takes, among the entries no neighbour holds,
    the one whose smallest hue distance to any coloured neighbour is largest, capped at `apart`
    so that every entry far enough away ties and the least-used of them wins (then the palette
    order), keeping the map's colours varied.  With no free entry at all the vertex takes the
    least-used colour, a duplicate rather than an exception.
    """
    hue = {c: _hue(c) for c in palette}
    rank = {c: i for i, c in enumerate(palette)}
    ids = sorted(adj, key=lambda d: (-len(adj[d]), str(d)))
    used, out = {c: 0 for c in palette}, {}

    def distance(a: float, b: float) -> float:
        d = abs(a - b) % 1.0
        return min(d, 1.0 - d)

    for d in ids:
        taken = {out[e] for e in adj[d] if e in out}
        free = [c for c in palette if c not in taken] or list(palette)
        hues = [hue[c] for c in taken]

        def score(c):
            gap = min((distance(hue[c], h) for h in hues), default=1.0)
            return (-min(gap, apart), used[c], rank[c])

        c = min(free, key=score)
        out[d] = c
        used[c] += 1
    return out


def _proximity_edges(cells: dict) -> list:
    """`[[z1, z2], ...]`, sorted: the rook adjacency of the proximity tessellation, `z1 < z2`.

    This is a reachability model, not a border graph.  The instance carries 3,713 of the 33,300
    CONUS ZCTAs, so real shared boundaries alone leave 817 components and 474 isolated zips;
    the tessellation closes those gaps by giving every point of the map to its nearest zip.
    Measured against real ZCTA adjacency it shares 4,462 edges of its 10,528 and their 4,843.
    Two zips joined here are near each other, not necessarily neighbours on any published map.

    Same STRtree pattern as `_adjacency`, but on the cells themselves rather than the dissolved
    districts, and before `_rings` simplifies them: `preserve_topology` simplifies each polygon
    on its own, so two neighbours' simplified rings no longer coincide and a shared boundary can
    no longer be measured.  A shared boundary of positive length is a rook edge; a corner touch
    or a point of tangency has zero length and is dropped.
    """
    import numpy as np
    import shapely
    ids = sorted(cells)
    geoms = [cells[z] for z in ids]
    ia, ib = shapely.STRtree(geoms).query(geoms, predicate="intersects")
    keep = ia < ib
    ia, ib = ia[keep], ib[keep]
    lengths = shapely.length(shapely.intersection(np.asarray(geoms)[ia], np.asarray(geoms)[ib]))
    touching = lengths > 0
    return sorted([ids[i], ids[j]] for i, j in zip(ia[touching], ib[touching]))


def _adjacency(polys: dict, tolerance: float = ADJ_TOLERANCE) -> dict:
    """`{district: set(district)}` over districts whose territory lies within `tolerance`
    metres of each other in `polys`.

    Read off dissolved polygons rather than off the zips: two districts are neighbours exactly
    when their territory meets in the geometry `polys` holds, which is the relation the
    colouring has to respect.  This is available here and is not in `us_maps`' own colouring,
    which runs before any polygon exists and has to approximate it with nearest neighbours.

    `polys` is the real-ZCTA dissolve, the same geometry `districts` exports, so the hues are
    assigned over the ground the reader actually sees.  That territory does not tile the plane
    (decision 1: unpopulated land, water and unassigned areas are real gaps), so plain
    `intersects` would miss a pair separated by a sliver and let two districts that read as
    neighbours share a hue.  The tolerance closes that: measured on the k = 18 live run,
    `intersects` finds 13 adjacent pairs, 1 km finds 15, 5 km 16 and 50 km 23.  1 km is the
    knee, and it also absorbs `CELLS_SIMPLIFY`, since a simplified ring can pull back by up to
    its own tolerance and open a gap that is not in the source data.
    """
    import shapely
    ids = sorted(polys, key=str)
    geoms = [polys[d] for d in ids]
    adj = {d: set() for d in ids}
    tree = shapely.STRtree(geoms)
    ia, ib = (tree.query(geoms, predicate="intersects") if tolerance <= 0
              else tree.query(geoms, predicate="dwithin", distance=tolerance))
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


def _rings_and_holes(geom, simplify: float) -> tuple:
    """`(rings, holes)` of a (multi)polygon: `rings` is exactly `_rings(geom, simplify)`;
    `holes` is the interior rings of the same parts, same simplify tolerance and rounding, so a
    caller who needs both (districts only -- see the module docstring) does not pay for
    `geom.simplify` twice.  A district's own zips can leave a real gap between them
    (unpopulated land, water, or an unassigned area, decision 1), and this is how that gap is
    exported: never into `rings`, which keeps `fill="toself"` at every existing call site
    (`app/mapfig.py`'s `staffed_figure`, both branches) exactly as safe as it is today.
    """
    if geom is None or geom.is_empty:
        return [], []
    if simplify > 0:
        geom = geom.simplify(simplify, preserve_topology=True)
    rings, holes = [], []
    for part in _parts(geom):
        ring = [[round(x, NDIGITS), round(y, NDIGITS)] for x, y in part.exterior.coords]
        if len(ring) >= 4:
            rings.append(ring)
        for interior in part.interiors:
            hole = [[round(x, NDIGITS), round(y, NDIGITS)] for x, y in interior.coords]
            if len(hole) >= 4:
                holes.append(hole)
    return rings, holes


def export(rows: list, states_gdf, zcta_polys: dict, cells_source: str,
          simplify: float = SIMPLIFY) -> dict:
    """The `geom.json` payload for one zip table.

    `states_gdf` is `td.geo.states_outline`'s GeoDataFrame, or `None` for no basemap -- which
    also means no per-state clipping and no state rings, the same branch `ziptable.render`
    takes so the tests need neither shapefile nor network.  A row with no district, or with no
    coordinates, holds no ground and is skipped.

    `zcta_polys` is `td.geo.zcta_polygons`'s `{zcta5: polygon}`, already in `LAEA`.  Every
    placed zip must have an entry -- there is no fallback to the Voronoi catchment for a missing
    one, only a `ValueError` naming which zips are missing -- so a stale or mismatched ZCTA
    source fails loudly rather than silently drawing a wrong shape.  `cells_source` is recorded
    verbatim into the output for the same reason.

    `cells` no longer means "this zip has a Voronoi cell" -- it means "this zip has a real ZCTA
    polygon", and coverage of the two need not match (a zip whose point clips away to nothing on
    the 1:20m coastline has no Voronoi cell but can still have a ZCTA).  `proximity_zips` is the
    Voronoi cell dict's own key set, exported explicitly rather than left for a `proximity_edges`
    consumer to infer from `cells`: a graph built as `{z for z in zips if z in geom["cells"]}`
    would silently admit an isolated, edge-less vertex for a zip that has a ZCTA but no Voronoi
    cell, which can make a contiguity guard downstream infeasible for no visible reason.
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

    missing = [z for z in keys if z not in zcta_polys]
    if missing:
        shown = ", ".join(missing[:8])
        raise ValueError(f"{len(missing)} placed zip(s) with no ZCTA polygon: {shown}"
                         f"{', ...' if len(missing) > 8 else ''} ({cells_source})")
    zcta_cells = {z: zcta_polys[z] for z in keys}

    clip = um.clip_region([xy[z] for z in keys], states_gdf)
    with telemetry.phase("proximity"):
        # The proximity tessellation.  It is never drawn and never dissolved into anything the
        # map shows: its only product is `proximity_edges`, the reachability graph -- see the
        # module docstring, decision 2.
        prox = um.voronoi_cells(keys, xy, clip,
                                zip_state=None if state_polys is None else zip_state,
                                state_polys=state_polys)
    with telemetry.phase("dissolve"):
        polys = um.dissolve(zcta_cells, districts)
        reach_polys = um.dissolve(prox, districts)      # outline only, see `district_reach`
    with telemetry.phase("colour"):
        # Adjacency off the reach, the tiling the reader sees as territory (`district_reach`
        # is filled and stroked on every map).  The real-ZCTA unions were used before, and
        # with 3,713 of 33,300 ZCTAs in the instance two districts' unions rarely touch at
        # all, so most map neighbours were never neighbours to the colouring and shared hues
        # (the user, 2026-09-11).
        adj = _adjacency(reach_polys)
        colors = color_distinct(adj, palette())

    out = {"crs": CRS, "districts": {}, "district_reach": {}, "states": {}, "cells": {},
          "proximity_edges": [], "proximity_zips": [], "cells_source": cells_source}
    for d in sorted(polys, key=str):
        rings, holes = _rings_and_holes(polys[d], simplify)
        entry = {"rings": rings, "color": colors[d]}
        if holes:
            entry["holes"] = holes        # omitted, not `[]`, for a hole-free district
        out["districts"][str(d)] = entry
    for d in sorted(reach_polys, key=str):
        rings = _rings(reach_polys[d], simplify)      # exteriors only: this layer is a stroke
        if rings:
            out["district_reach"][str(d)] = {"rings": rings, "color": colors.get(d, "#111111")}
    if states_gdf is not None:
        for code, geom in zip(states_gdf["STUSPS"].astype(str), states_gdf.geometry):
            rings = _rings(geom, simplify)
            if not rings:
                continue
            p = _parts(geom)[0].representative_point()          # inside the largest part
            out["states"][str(code)] = {"rings": rings,
                                        "label": [round(p.x, NDIGITS), round(p.y, NDIGITS)]}
    with telemetry.phase("cells"):
        out["cells"] = {str(z): {"rings": _rings(zcta_cells[z], CELLS_SIMPLIFY)}
                        for z in sorted(zcta_cells)}
        out["proximity_edges"] = _proximity_edges(prox)
        out["proximity_zips"] = sorted(prox)      # the vertex set `proximity_edges` is over
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
    ap.add_argument("--zcta-shp", default=geo.ZCTA_SHP, help="ZCTA520 shapefile path")
    ap.add_argument("--simplify", type=float, default=SIMPLIFY,
                    help="ring tolerance in metres; 0 keeps every vertex")
    ap.add_argument("--no-basemap", action="store_true",
                    help="skip the shapefile: clip to the padded hull of the points, no states")
    a = ap.parse_args(argv)

    T = telemetry.Timings("geom")
    with T.phase("load"):
        rows = ziptable.read(a.table)
        states = None if a.no_basemap else geo.states_outline(a.geo_cache)
        keys = sorted({r["zip"] for r in rows
                      if r["district"] and r["x"] is not None and r["y"] is not None})
        zcta_polys = geo.zcta_polygons(keys, a.zcta_shp)
    cells_source = f"{os.path.basename(a.zcta_shp)} simplify={CELLS_SIMPLIFY:g}m"
    g = export(rows, states, zcta_polys, cells_source, a.simplify)  # voronoi/dissolve/colour inside
    with T.phase("write"):
        path = write(os.path.join(a.out, "geom.json"), g)
    print(f"geom: {len(g['districts'])} district(s), {len(g['states'])} state(s), "
          f"{len(g['cells'])} cell(s), {os.path.getsize(path) / 1e6:.2f} MB -> {path}")
    T.write(a.out)
    return 0


if __name__ == "__main__":
    sys.exit(telemetry.maybe_profile(main)())
