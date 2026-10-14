"""District reach GeoJSON for a run folder, in the shape the owner's Tableau upload already holds
(archive `tools/export_tableau_datasets.py::export_district_geojson`, 2026-09-14): one feature per
district, WGS84 (Multi)Polygon dissolved from the ledger's ZCTA polygons (the same `zip_pages`
geometry and colouring the ZIP map uses, so colours match the PNG), properties `scenario_id, bundle,
bundle_title, district_raw, district, wholesaler, mass, color` plus the simplestyle keys `fill, fill-opacity, stroke, stroke-width`
(the same colour) so viewers such as GitHub's preview colour each district, and kepler.gl's `fillColor, lineColor,
lineWidth` (RGB arrays).  Written as
`export/<scenario>_district_reach.geojson`, with `export/<scenario>_states.geojson` beside it (CONUS state
polygons with `state`, `name`, a black 2 px border and no fill, for borders and labels on top); the scenario id comes from export/scenarios.csv
(run tools/exp/contig/export_long.py first).

    TD_REPO=<repo with data/public> "$TD_PY" tools/exp/contig/export_geojson.py <run_dir> [--simplify M]
"""
import argparse, collections, csv, importlib.util, json, os, sys
import shapely
from pyproj import Transformer

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
BUNDLE_TITLE = {"IFA": "IFA", "N": "National only", "WH": "WH", "FI": "FI", "WHFI": "WIFI Merged"}


def rgb(hexcol: str) -> list:
    return [int(hexcol[i:i + 2], 16) for i in (1, 3, 5)]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--simplify", type=float, default=250.0, help="tolerance in metres (EPSG:5070), 0 for none")
    a = ap.parse_args(argv)
    run_dir = os.path.abspath(a.run_dir)
    spec = importlib.util.spec_from_file_location("zip_pages", os.path.join(ROOT, "tools", "maps", "zip_pages.py"))
    zp = importlib.util.module_from_spec(spec); spec.loader.exec_module(zp)
    with open(os.path.join(run_dir, "export", "scenarios.csv"), newline="") as fh:
        scen = next(csv.DictReader(fh))
    rows, mass, bundle = collections.defaultdict(list), collections.Counter(), {}
    with open(os.path.join(run_dir, "ledger.csv"), newline="") as fh:
        for r in csv.DictReader(fh):
            if r["district"]:
                rows[r["district"]].append(r["zip_code"])
                mass[r["district"]] += float(r["m_rel"] or 0.0)
                bundle[r["district"]] = r["model_channel"]
    polys, _, _ = zp.geometry()
    unions = {d: shapely.union_all([polys[z] for z in zs if z in polys]).buffer(150).buffer(-150)
              for d, zs in rows.items()}
    colour = zp.colouring(unions, zp.neighbours(unions))
    tr = Transformer.from_crs("EPSG:5070", "EPSG:4326", always_xy=True)
    feats = []
    for d in sorted(unions):
        g = unions[d].simplify(a.simplify, preserve_topology=True) if a.simplify else unions[d]
        g = shapely.transform(g, lambda xy: __import__("numpy").column_stack(tr.transform(xy[:, 0], xy[:, 1])))
        feats.append({"type": "Feature", "geometry": shapely.geometry.mapping(g),
                      "properties": {"scenario_id": scen["scenario"], "bundle": bundle[d],
                                     "bundle_title": BUNDLE_TITLE.get(bundle[d], bundle[d]), "district_raw": d,
                                     "district": d, "wholesaler": "", "mass": round(mass[d], 7), "color": colour[d],
                                     # simplestyle keys, so GitHub's and geojson.io's previews colour the districts
                                     "fill": colour[d], "fill-opacity": 0.6, "stroke": "#202020", "stroke-width": 1,
                                     # kepler.gl per-feature style keys (RGB arrays)
                                     "fillColor": rgb(colour[d]), "lineColor": [32, 32, 32], "lineWidth": 1,
                                     # colour class 0..len(PALETTE)-1: colour "by field" on this in a viewer and
                                     # its categorical palette (20 colours or fewer) never wraps
                                     "color_index": zp.PALETTE.index(colour[d])}})
    out = os.path.join(run_dir, "export", f"{scen['scenario']}_district_reach.geojson")
    with open(out, "w") as fh:
        json.dump({"type": "FeatureCollection", "features": feats}, fh)
    print(f"{out}: {len(feats)} districts, {os.path.getsize(out) / 1e6:.1f} MB")
    # the states layer: one polygon per CONUS state with its name, black 2 px border and no colour
    # of its own (in kepler.gl turn the layer's fill off, or drop its opacity, and label by `name`)
    from td import geo
    st = geo._read(os.path.join(zp.CACHE, "cb_2025_us_state_500k.zip"), ["STATEFP", "STUSPS", "NAME"])
    st = st[st["STATEFP"].isin(geo.CONUS_STATEFP)]
    sfeats = []
    for postal, name, g in zip(st["STUSPS"], st["NAME"], st.geometry):
        g = g.simplify(a.simplify, preserve_topology=True) if a.simplify else g
        g = shapely.transform(g, lambda xy: __import__("numpy").column_stack(tr.transform(xy[:, 0], xy[:, 1])))
        c = g.representative_point()
        sfeats.append({"type": "Feature", "geometry": shapely.geometry.mapping(g),
                       "properties": {"scenario_id": scen["scenario"], "state": postal, "name": name,
                                      "label_lon": round(c.x, 5), "label_lat": round(c.y, 5),
                                      "stroke": "#000000", "stroke-width": 2, "fill-opacity": 0,
                                      "lineColor": [0, 0, 0], "lineWidth": 2}})
    sout = os.path.join(run_dir, "export", f"{scen['scenario']}_states.geojson")
    with open(sout, "w") as fh:
        json.dump({"type": "FeatureCollection", "features": sorted(sfeats, key=lambda f: f["properties"]["state"])}, fh)
    print(f"{sout}: {len(sfeats)} states, {os.path.getsize(sout) / 1e6:.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
