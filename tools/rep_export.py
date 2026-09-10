"""rep_export.py -- the incumbent reps' book, as ratios and polygons, for the app's Map tab.

    .venv/bin/python3 tools/rep_export.py instance_descaled_v2_conus.json.gz \\
        --out battery/results/app_reps/instance_descaled_v2_conus --geo-cache data/geo

writes `<out>/reps.json`.  The Streamlit app never opens an instance -- confidentiality keeps
the descaled masses on the solver side -- so this driver is the seam that turns "who sells what,
where" into something the app can draw with no book of its own: a rep's share of a zip's book,
a zip's share of the whole channel's book, and the Voronoi territory each rep's book tiles.

Nothing here is a mass.  Every number leaving this file is a ratio of one unmeasured total: a
zip's own book (`shares`, `free`) or the whole channel's (`weight`, `book_share`, `free_share`).
The instance is opened only to compute those ratios; the totals themselves never reach the file,
the same promise `tools/staff.py`'s `staffing.json` already makes for a rep's Nash `gain`.

A zip's `top` rep is the argmax of its own shares, "" when nobody there holds a positive share
(a vacancy, or genuinely no sales).  `n` counts the zip's candidates with a positive share -- 0,
1 or 2+, the split the rep map colours by.  Cells are the real 2025 TIGER/Line ZCTA polygons
(`td.geo.zcta_polygons`), one per zip the instance carries, untapped zips included, so no
territory swallows ground nobody claims; a zip with no ZCTA still gets an entry in `zips`, it is
simply not drawable.  Nothing here tessellates: the cells are the published boundaries, the same
ground `geom.json`'s `cells` draw, so the rep map and the district map agree by construction.

Polygons reuse `tools/geom_export.py` outright: `_rings`, `_adjacency`, `_parts`, `palette` and
`write` are the same functions a `geom.json` district export calls, and `us_maps.dissolve` and
`color_districts` are the same builders.  `territories` dissolves the cells by
`top` (an unclaimed cell dissolves into nothing); `footprints[rep]` is the union of every zip's
cell where `rep` holds a positive share, so a contested zip's cell sits in more than one rep's
footprint; `contested` is the union of cells with `n >= 2`.  Colours come from the same 50-entry
palette, assigned over the territories' own adjacency so two touching territories never share a
hue.
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                "..")))

from td import geo, model, telemetry                                        # noqa: E402
from td import instance as descaled                                         # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def _geom_export():
    """`tools/geom_export.py` as a module.  `tools/` is not a package, so this loads it by
    path, the same route `geom_export.py` itself uses for `us_maps`."""
    mod = sys.modules.get("geom_export")
    if mod is None:
        path = os.path.join(HERE, "geom_export.py")
        spec = importlib.util.spec_from_file_location("geom_export", path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules["geom_export"] = mod
        spec.loader.exec_module(mod)
    return mod


# ------------------------------------------------------------------------------- the shares
def shares(d) -> tuple:
    """`(reps, zips, book_share, free_share)` -- every number a ratio of one channel total.

    `zips[z]` carries `top`, `shares` (of z's own book), `free`, `n` and `weight` (of the whole
    channel's book).  `book_share[rep]` and `free_share` are that same whole-channel total's
    split between the reps and the filler.  The total itself is a raw mass: it is used to
    divide and then discarded, and never appears in the return value.
    """
    reps_order = model.reps(d.G, sorted(d.G))
    per_zip = {}
    totals = {r: 0.0 for r in reps_order}
    free_total = 0.0
    grand = 0.0
    for z in d.G:
        S = model.books(d.G, z)
        free = model.free_book(d.G, z)
        per_zip[z] = (S, free)
        for r, s in S.items():
            if r in totals:
                totals[r] += s
        free_total += free
        grand += sum(S.values()) + free

    zips = {}
    for z, (S, free) in per_zip.items():
        total_z = sum(S.values()) + free
        if total_z > 0:
            zshares = {r: s / total_z for r, s in S.items() if s > 0}
            free_z = free / total_z
        else:
            zshares, free_z = {}, 0.0
        top = max(zshares, key=lambda r: (zshares[r], r)) if zshares else ""
        zips[z] = dict(top=top, shares=zshares, free=free_z, n=len(zshares),
                       weight=(total_z / grand if grand > 0 else 0.0))

    book_share = {r: (totals[r] / grand if grand > 0 else 0.0) for r in reps_order}
    free_share = free_total / grand if grand > 0 else 0.0
    return reps_order, zips, book_share, free_share


# --------------------------------------------------------------------------- the polygon half
def export(d, zcta_polys: dict, states, simplify: float) -> dict:
    """The `reps.json` payload for one loaded instance.

    `zcta_polys` is `td.geo.zcta_polygons`'s `{zcta5: polygon}` in `LAEA`.  A zip with no ZCTA
    still gets a `zips` entry, it is simply not drawn.  `states` is `td.geo.states_outline`'s
    GeoDataFrame, or `None` for no basemap -- the branch `geom_export.export` also takes, so the
    tests need neither shapefile nor network.

    Territories, footprints and the contested hatch are all dissolved from the real ZCTA
    polygons, the same source `geom.json`'s `cells` come from, so the rep map and the district
    map draw the same ground.  Nothing here builds a Voronoi tessellation.
    """
    ge = _geom_export()
    um = ge._us_maps()

    with telemetry.phase("shares"):
        reps_order, zips, book_share, free_share = shares(d)

    cells = {z: zcta_polys[z] for z in sorted(zips) if z in zcta_polys}
    if len(cells) < 2:
        raise ValueError(f"{len(cells)} zip(s) with a ZCTA polygon: a map needs 2")

    with telemetry.phase("dissolve"):
        top_of = {z: zips[z]["top"] for z in cells if zips[z]["top"]}
        territory_polys = um.dissolve(cells, top_of)
        colors = um.color_districts(ge._adjacency(territory_polys), ge.palette())
        territories = {r: dict(rings=ge._rings(territory_polys[r], simplify), color=colors[r])
                       for r in territory_polys}

    with telemetry.phase("footprints"):
        footprints = {}
        for r in reps_order:
            marked = {z: r for z in cells if zips[z]["shares"].get(r, 0.0) > 0}
            polys = um.dissolve(cells, marked)
            footprints[r] = dict(rings=ge._rings(polys.get(r), simplify))

        contest_marked = {z: "x" for z in cells if zips[z]["n"] >= 2}
        contest_polys = um.dissolve(cells, contest_marked)
        contested = dict(rings=ge._rings(contest_polys.get("x"), simplify))

    states_out = {}
    if states is not None:
        for code, geom in zip(states["STUSPS"].astype(str), states.geometry):
            rings = ge._rings(geom, simplify)
            if not rings:
                continue
            p = ge._parts(geom)[0].representative_point()
            states_out[str(code)] = dict(rings=rings,
                                         label=[round(p.x, ge.NDIGITS), round(p.y, ge.NDIGITS)])

    return dict(crs=ge.CRS, reps=reps_order, book_share=book_share, free_share=free_share,
               zips=zips, territories=territories, footprints=footprints, contested=contested,
               states=states_out)


def main(argv=None) -> int:
    ge = _geom_export()
    ap = argparse.ArgumentParser(description="write an instance's rep territories, as ratios "
                                             "and polygons, to <out>/reps.json")
    ap.add_argument("instance", help="the descaled instance (.json.gz)")
    ap.add_argument("--out", required=True, help="directory reps.json is written into")
    ap.add_argument("--geo-cache", default=geo.DEFAULT_DEST,
                    help="gazetteer and state shapefile cache")
    ap.add_argument("--zcta-shp", default=geo.ZCTA_SHP,
                    help="the TIGER/Line ZCTA520 shapefile the cells come from")
    ap.add_argument("--simplify", type=float, default=ge.SIMPLIFY,
                    help="ring tolerance in metres; 0 keeps every vertex")
    ap.add_argument("--no-basemap", action="store_true",
                    help="skip the shapefile: clip to the padded hull of the points, no states")
    a = ap.parse_args(argv)

    T = telemetry.Timings("reps")
    with T.phase("load"):
        d = descaled.load_descaled(a.instance)
        geo.assert_conus(d)

        zcta_polys = geo.zcta_polygons(sorted(d.G), a.zcta_shp)
        states = None if a.no_basemap else geo.states_outline(a.geo_cache)

    g = export(d, zcta_polys, states, a.simplify)   # shares/dissolve/footprints phases inside
    g["instance"] = os.path.basename(a.instance)
    with T.phase("write"):
        path = ge.write(os.path.join(a.out, "reps.json"), g)
    T.write(a.out)

    n_top = sum(1 for z in g["zips"].values() if z["top"])
    print(f"reps: {len(g['reps'])} rep(s), {len(g['zips'])} zip(s), {n_top} with a top rep, "
          f"{len(g['territories'])} territor{'y' if len(g['territories']) == 1 else 'ies'}, "
          f"{os.path.getsize(path) / 1e6:.2f} MB -> {path}")
    return 0


if __name__ == "__main__":
    sys.exit(telemetry.maybe_profile(main)())
