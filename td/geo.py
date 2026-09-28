"""geo.py -- the 2025 geography: the ZCTA reference table, its overlays and the ZIP graph.

`python -m td geo` fetches the #52 §5.2 sources into `data/public/` (gitignored, fetched once and
kept) and writes `reference/2025/`:

    zcta_reference.csv.gz   one row per CONUS ZCTA: gazetteer point and land area, measured land,
                            primary state, county, CBSA, CSA, METDIV, place and urban area,
                            urban land share, co-est2025 population, graph vertex flag
    zcta_overlay.csv.gz     (zcta, layer, geoid, land_m2) for layer county, place and uac: the
                            land of each piece of a ZCTA polygon overlaid on that layer
    zcta_graph_edges.csv.gz the ZIP graph over the CONUS ZCTAs (OD2, #57), one row per edge
    areas.csv.gz            (layer, geoid, name, ...) for the county, place, cbsa, csa, metdiv
                            and uac codes the other files use
    county_adjacency.csv.gz county_adjacency2025.txt restricted to CONUS
    MANIFEST.json           URL, vintage and sha256 of every source file
    REPORT.json             the build's checks: coverage, land, graph vertices, state components

Everything is 2025 vintage (S17); `check_manifest` rejects any other.  HUD placement is G2.

**Land.**  TIGER ZCTA polygons include their water, so a piece's polygon area is not its land.
Each (ZCTA, county) piece has that county's perennial water removed: the TIGER/Line FACES
whose LWFLAG is P.  The Census counts every other face (L land, I intermittent water, G
glacier) as land, so this is the gazetteer's own land, not an estimate.  AREAWATER alone failed
the land check, because its partly-land polygons do not say where their land is (#62); it is
read only for a county whose FACES file census.gov will not serve (`UNAVAILABLE`), where the
water is its polygons with AWATER > 0 less its all-land (intermittent) ones.  The place and
urban-area overlays run on those land pieces.  A ZCTA's primary county, place and
urban area are the ones holding the most of its land; its state is its primary county's, and
its CBSA, CSA and METDIV are too (S15: exports carry them per ZIP, and metros are county
unions).

**The ZIP graph** (OD2) is the rook graph of the Voronoi cells of the 2025 gazetteer points,
one diagram per state clipped to that state's TIGER/Line polygon (which includes its water), so
no cell crosses a state line.  Two cells are adjacent when they share a border of positive
length; a corner touch is not an edge.  The DC-VA pair of nearest points is the only manual
edge.  A ZIP whose cell clips away is not a vertex; it is reported, never inferred (trap 21).
Here the vertices are all CONUS ZCTAs, a stand-in until the extract arrives: `zip_graph` is
rerun on the extract's placed ZIPs in C2/E1.

Coordinates and areas are EPSG:5070 (NAD83 CONUS Albers, equal-area on GRS80), so measured
areas are comparable with the gazetteer's.
"""
from __future__ import annotations

import concurrent.futures
import gzip
import hashlib
import io
import json
import math
import os
import re
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUBLIC_DIR = os.path.join(ROOT, "data", "public")
REFERENCE_DIR = os.path.join(ROOT, "reference", "2025")

VINTAGE = "2025"
CRS = "EPSG:5070"
LAND_TOLERANCE = 0.005          # measured land against gazetteer ALAND, relative (#62)
MIN_PIECE_M2 = 1.0              # a piece with less land than this is a boundary sliver

# the lower 48 and DC, by state FIPS
CONUS_STATEFP = frozenset(
    "01 04 05 06 08 09 10 11 12 13 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 "
    "35 36 37 38 39 40 41 42 44 45 46 47 48 49 50 51 53 54 55 56".split())
OVERRIDE_PAIR = ("DC", "VA")    # OD2: the one manual edge

# Source files census.gov will not serve.  The owner's rule (#62): a file named here is listed
# in the manifest as unavailable, and a county whose FACES file is here takes its water from
# its 2025 AREAWATER file instead; no other vintage stands in.
_REJECTED = ("census.gov answers with a 'Request Rejected' page (2026-09-28, from m5 and m2); "
             "water from tl_2025_{g}_areawater.zip")
UNAVAILABLE = {f"tl_2025_{g}_faces.zip": _REJECTED.format(g=g)
               for g in ("19181", "36115", "37107", "39095", "42065", "50009", "51107")}

TIGER = "https://www2.census.gov/geo/tiger/TIGER2025"
GENZ = "https://www2.census.gov/geo/tiger/GENZ2025/shp"
GAZ = "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2025_Gazetteer"
POPEST = "https://www2.census.gov/programs-surveys/popest/datasets/2020-2025"

# name -> (url, use).  `place` and `faces` are one file per state or county: their url is the
# directory, and `source_files` lists the files.
SOURCES = {
    "gaz_zcta": (f"{GAZ}/2025_Gaz_zcta_national.zip", "ZCTA points and land area"),
    "zcta": (f"{TIGER}/ZCTA520/tl_2025_us_zcta520.zip", "ZCTA polygons for the overlays"),
    "state": (f"{TIGER}/STATE/tl_2025_us_state.zip", "states; the graph's clip polygons"),
    "cb_state": (f"{GENZ}/cb_2025_us_state_500k.zip", "map outlines (not read by the build)"),
    "county": (f"{TIGER}/COUNTY/tl_2025_us_county.zip", "counties with CBSA, CSA, METDIV"),
    "county_adjacency": ("https://www2.census.gov/geo/docs/reference/county_adjacency/"
                         "county_adjacency2025.txt", "county adjacency, for pieces"),
    "cb_county": (f"{GENZ}/cb_2025_us_county_500k.zip", "map outlines (not read by the build)"),
    "cbsa": (f"{TIGER}/CBSA/tl_2025_us_cbsa.zip", "CBSA names"),
    "csa": (f"{TIGER}/CSA/tl_2025_us_csa.zip", "CSA names"),
    "metdiv": (f"{TIGER}/METDIV/tl_2025_us_metdiv.zip", "metro division names"),
    "gaz_cbsa": (f"{GAZ}/2025_Gaz_cbsa_national.zip", "CBSA internal points"),
    "place": (f"{TIGER}/PLACE/", "place polygons, one file per state"),
    "gaz_place": (f"{GAZ}/2025_Gaz_place_national.zip", "place internal points"),
    "sub_est": (f"{POPEST}/cities/totals/sub-est2025.csv", "place population, 2025"),
    "uac": (f"{TIGER}/UAC20/tl_2025_us_uac20.zip", "urban areas"),
    "co_est": (f"{POPEST}/counties/totals/co-est2025-alldata.csv", "county population, 2025"),
    "faces": (f"{TIGER}/FACES/", "land/water faces, one file per county, for land"),
    "areawater": (f"{TIGER}/AREAWATER/", "water polygons, for the counties whose FACES file "
                  "is unavailable"),
}


# ------------------------------------------------------------------------------ sources
def source_files(name: str, county_geoids=()) -> list[str]:
    """The URLs of source `name`: one, or one per CONUS state (`place`) or county (`faces`, and
    `areawater` for the counties whose FACES file is unavailable)."""
    url = SOURCES[name][0]
    if name == "place":
        return [f"{url}tl_2025_{s}_place.zip" for s in sorted(CONUS_STATEFP)]
    if name == "faces":
        return [f"{url}tl_2025_{g}_faces.zip" for g in sorted(county_geoids)]
    if name == "areawater":
        return [f"{url}tl_2025_{g}_areawater.zip" for g in sorted(county_geoids)
                if f"tl_2025_{g}_faces.zip" in UNAVAILABLE]
    return [url]


def _valid_download(path: str) -> bool:
    """False for the HTML page census.gov serves, with status 200, when it throttles a client."""
    with open(path, "rb") as fh:
        head = fh.read(64)
    return head.startswith(b"PK") if path.endswith(".zip") else not head.lstrip().startswith(b"<")


def cached(url: str, public: str = PUBLIC_DIR, tries: int = 6) -> str:
    """Path of `url`'s file under `public`, downloading it only if absent or not valid."""
    path = os.path.join(public, os.path.basename(url))
    if os.path.exists(path) and _valid_download(path):
        return path
    os.makedirs(public, exist_ok=True)
    tmp = path + ".part"
    for attempt in range(tries):
        with urllib.request.urlopen(url, timeout=600) as fh, open(tmp, "wb") as out:
            while chunk := fh.read(1 << 20):
                out.write(chunk)
        if _valid_download(tmp):
            os.replace(tmp, path)
            return path
        time.sleep(5 * 2 ** attempt)
    os.remove(tmp)
    raise RuntimeError(f"{url}: census.gov kept returning a rejection page")


def fetch_all(urls: list[str], public: str = PUBLIC_DIR) -> list[str]:
    with concurrent.futures.ThreadPoolExecutor(4) as pool:
        return list(pool.map(lambda u: cached(u, public), urls))


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while chunk := fh.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def manifest_entry(name: str, urls: list[str], public: str = PUBLIC_DIR) -> dict:
    """URL, vintage and sha256 of a source.  A multi-file source lists each file's sha256, and
    its own sha256 is that of the sorted `name sha256` lines."""
    url, use = SOURCES[name]
    files = {os.path.basename(u): sha256(os.path.join(public, os.path.basename(u)))
             for u in urls if os.path.basename(u) not in UNAVAILABLE}
    entry = {"name": name, "url": url, "vintage": VINTAGE, "use": use}
    gone = {os.path.basename(u) for u in urls} & set(UNAVAILABLE)
    if gone:
        entry["unavailable"] = {f: UNAVAILABLE[f] for f in sorted(gone)}
    if len(urls) == 1 and url == urls[0]:
        entry["sha256"] = next(iter(files.values()))
    else:
        listing = "".join(f"{f} {h}\n" for f, h in sorted(files.items()))
        entry["sha256"] = hashlib.sha256(listing.encode()).hexdigest()
        entry["files"] = dict(sorted(files.items()))
    return entry


def check_manifest(manifest: dict) -> None:
    """Raise unless every source is 2025: its vintage field, its URL and each file name."""
    bad = []
    for e in manifest["sources"]:
        names = list(e.get("files", {})) or [os.path.basename(e["url"])]
        if e.get("vintage") != VINTAGE:
            bad.append(f"{e['name']}: vintage {e.get('vintage')!r}")
        if VINTAGE not in e["url"]:
            bad.append(f"{e['name']}: url {e['url']}")
        bad += [f"{e['name']}: file {f}" for f in names if VINTAGE not in f]
        if not re.fullmatch(r"[0-9a-f]{64}", e.get("sha256", "")):
            bad.append(f"{e['name']}: sha256 {e.get('sha256')!r}")
        gone = e.get("unavailable", {})
        bad += [f"{e['name']}: {f} unavailable but not in geo.UNAVAILABLE"
                for f in gone if f not in UNAVAILABLE]
        bad += [f"{e['name']}: {f} both hashed and unavailable"
                for f in gone if f in e.get("files", {})]
    missing = sorted(set(SOURCES) - {e["name"] for e in manifest["sources"]})
    bad += [f"{m}: not in the manifest" for m in missing]
    if bad:
        raise ValueError("manifest has non-2025 or incomplete sources: " + "; ".join(bad))


# ------------------------------------------------------------------------------ readers
def _read(path: str, columns: list[str], geometry: bool = True, where: str | None = None):
    import pyogrio
    df = pyogrio.read_dataframe(f"zip://{path}", columns=columns, read_geometry=geometry,
                                where=where)
    return df.to_crs(CRS) if geometry else df


def _gazetteer(path: str):
    """A gazetteer zip as a DataFrame of strings, header names stripped."""
    import pandas as pd
    df = pd.read_csv(path, sep="|", dtype=str, encoding="latin-1")
    df.columns = [c.strip() for c in df.columns]
    return df


# ------------------------------------------------------------------------------ the ZIP graph
def voronoi_cells(points: dict, clip) -> dict:
    """`{key: cell}`: the Voronoi cell of each point, clipped to `clip`.  Empty cells are dropped."""
    import shapely
    keys = sorted(points)
    if not keys:
        return {}
    if len(keys) == 1:
        return {keys[0]: clip}
    coords = [points[k] for k in keys]
    if len(set(coords)) != len(coords):
        raise ValueError("two ZIPs share a point; their Voronoi cells are not defined")
    x0, y0, x1, y1 = clip.bounds
    env = shapely.box(x0, y0, x1, y1).buffer(0.02 * max(x1 - x0, y1 - y0) + 1.0)
    cells = list(shapely.voronoi_polygons(shapely.MultiPoint(coords), extend_to=env,
                                          ordered=True).geoms)
    pts = shapely.points(coords)
    if len(cells) != len(keys) or not all(shapely.covers(cells, pts)):
        raise RuntimeError("voronoi_polygons did not return the cells in input order")
    shapely.prepare(clip)
    clipped = shapely.intersection(cells, clip)
    return {k: g for k, g in zip(keys, clipped) if not g.is_empty and g.area > 0}


def zip_graph(points: dict, zip_state: dict, state_polys: dict) -> dict:
    """The OD2 ZIP graph over the ZIPs in `points`.

    `points` is `{zip: (x, y)}` in `CRS`, `zip_state` `{zip: state}`, `state_polys`
    `{state: polygon}` in `CRS`.  Returns `{"vertices": [...], "edges": [(a, b, kind, border_m)],
    "missing": {zip: reason}}`: a ZIP is a vertex only if its state-clipped cell survives.
    `kind` is "rook" or "override" (the DC-VA pair of nearest vertices, if not already rook);
    `"override"` is that pair and its kind, or None.
    """
    import numpy as np
    import shapely
    missing = {z: "no state polygon" for z in points if zip_state.get(z) not in state_polys}
    by_state: dict = {}
    for z in points:
        if z not in missing:
            by_state.setdefault(zip_state[z], {})[z] = points[z]
    cells = {}
    for s, pts in sorted(by_state.items()):
        got = voronoi_cells(pts, state_polys[s])
        cells.update(got)
        missing.update({z: "cell clipped away" for z in pts if z not in got})
    ids = sorted(cells)
    geoms = np.asarray([cells[z] for z in ids])
    ia, ib = shapely.STRtree(geoms).query(geoms, predicate="intersects")
    keep = ia < ib
    ia, ib = ia[keep], ib[keep]
    border = shapely.length(shapely.intersection(geoms[ia], geoms[ib]))
    edges = {(ids[i], ids[j]): ("rook", float(b)) for i, j, b in zip(ia, ib, border) if b > 0}
    a_s, b_s = OVERRIDE_PAIR
    va = [z for z in ids if zip_state[z] == a_s]
    vb = [z for z in ids if zip_state[z] == b_s]
    override = None
    if va and vb:
        _, a, b = min((math.dist(points[a], points[b]), a, b) for a in va for b in vb)
        override = tuple(sorted((a, b)))
        edges.setdefault(override, ("override", 0.0))
    return {"vertices": ids,
            "edges": [(a, b, k, m) for (a, b), (k, m) in sorted(edges.items())],
            "missing": dict(sorted(missing.items())),
            "override": None if override is None else [*override, edges[override][0]]}


def state_components(vertices, edges, zip_state: dict) -> dict:
    """`{state: [component sizes, largest first]}` for each state whose ZIPs are not connected
    on the graph restricted to that state's ZIPs."""
    import networkx as nx
    g = nx.Graph()
    g.add_nodes_from(vertices)
    g.add_edges_from((a, b) for a, b, *_ in edges if zip_state[a] == zip_state[b])
    by_state: dict = {}
    for comp in nx.connected_components(g):
        s = zip_state[next(iter(comp))]
        by_state.setdefault(s, []).append(len(comp))
    return {s: sorted(c, reverse=True) for s, c in sorted(by_state.items()) if len(c) > 1}


# ------------------------------------------------------------------------------ the overlays
def primary(pieces, key: str, by: str = "land_m2"):
    """`{key: geoid}` of the piece with the most `by` per `key` (ties: the smaller geoid)."""
    top = pieces.sort_values([key, by, "geoid"], ascending=[True, False, True])
    return top.drop_duplicates(key).set_index(key)["geoid"]


def _threaded(fn, n: int, chunk: int = 2000) -> list:
    """`fn(lo, hi)` over `range(n)` in chunks on a thread pool (shapely releases the GIL)."""
    spans = [(lo, min(lo + chunk, n)) for lo in range(0, n, chunk)]
    with concurrent.futures.ThreadPoolExecutor(os.cpu_count() or 4) as pool:
        return list(pool.map(lambda s: fn(*s), spans))


def _overlay(left, right, left_key: str, right_key: str):
    """(left_key, right_key, area, geometry) of each nonempty intersection of two frames."""
    import numpy as np
    import pandas as pd
    import shapely
    ia, ib = shapely.STRtree(right.geometry.values).query(left.geometry.values,
                                                          predicate="intersects")
    lg = np.asarray(left.geometry.values)[ia]
    rg = np.asarray(right.geometry.values)[ib]

    def cut(lo, hi):
        a, b = lg[lo:hi], rg[lo:hi]
        inside = shapely.within(a, b)
        g = a.copy()
        g[~inside] = shapely.intersection(a[~inside], b[~inside])
        return g

    geom = np.concatenate(_threaded(cut, len(ia))) if len(ia) else lg
    out = pd.DataFrame({left_key: left[left_key].values[ia],
                        right_key: right[right_key].values[ib]})
    out["geometry"] = geom
    out["area"] = shapely.area(geom)
    return out[out["area"] > 0].reset_index(drop=True)


def _county_water(county_geoids, public: str):
    """(county geoid, polygon) arrays of each county's perennial water, in `CRS`: the union of
    its FACES with LWFLAG P, split into its polygons, or its AREAWATER fallback (module doc)."""
    import numpy as np
    import shapely

    def one(g):
        if f"tl_2025_{g}_faces.zip" in UNAVAILABLE:
            df = _read(os.path.join(public, f"tl_2025_{g}_areawater.zip"), ["AWATER"])
            geoms = np.asarray(df.geometry.values)
            wet = df["AWATER"].to_numpy(float) > 0
            water = shapely.difference(shapely.union_all(geoms[wet]),
                                       shapely.union_all(geoms[~wet]))
        else:
            df = _read(os.path.join(public, f"tl_2025_{g}_faces.zip"), ["LWFLAG"],
                       where="LWFLAG = 'P'")
            water = shapely.union_all(np.asarray(df.geometry.values))
        parts = shapely.get_parts(water)
        return g, parts[shapely.area(parts) > 0]

    with concurrent.futures.ThreadPoolExecutor(8) as pool:
        got = list(pool.map(one, county_geoids))
    return (np.concatenate([np.full(len(x[1]), x[0], dtype=object) for x in got]),
            np.concatenate([x[1] for x in got]))


def land_pieces(zctas, counties, water):
    """The (ZCTA, county) land pieces: each ZCTA polygon cut by county, less the county's
    perennial water (`_county_water`)."""
    import numpy as np
    import shapely
    pieces = _overlay(zctas, counties, "zcta", "county")
    w_county, w_geom = water
    geom = pieces["geometry"].values.copy()
    pi, wi = shapely.STRtree(w_geom).query(geom, predicate="intersects")
    same = pieces["county"].values[pi] == w_county[wi]
    pi, wi = pi[same], wi[same]
    order = np.lexsort((wi, pi))
    pi, wi = pi[order], wi[order]
    hit, first = np.unique(pi, return_index=True)
    groups = np.split(wi, first[1:])

    def dry(lo, hi):
        return shapely.difference(geom[hit[lo:hi]],
                                  [shapely.union_all(w_geom[g]) for g in groups[lo:hi]])

    if len(hit):
        geom[hit] = np.concatenate(_threaded(dry, len(hit), 500))
    pieces["geometry"] = geom
    pieces["land_m2"] = shapely.area(geom)
    return pieces[pieces["land_m2"] >= MIN_PIECE_M2].reset_index(drop=True)


def layer_pieces(land, layer, layer_key: str):
    """Land of each (ZCTA, layer area) piece: the land pieces overlaid on `layer`."""
    tagged = land[["zcta", "geometry"]].reset_index(names="piece")
    out = _overlay(tagged, layer, "piece", layer_key)
    out["zcta"] = land["zcta"].values[out["piece"].values]
    out = out.groupby(["zcta", layer_key], as_index=False)["area"].sum()
    out = out.rename(columns={layer_key: "geoid", "area": "land_m2"})
    return out[out["land_m2"] >= MIN_PIECE_M2]


# ------------------------------------------------------------------------------ the build
def build(public: str = PUBLIC_DIR, out: str = REFERENCE_DIR, log=print) -> dict:
    """Fetch the sources and write `reference/2025/`.  Returns the report."""
    import numpy as np
    import pandas as pd
    import shapely

    log("geo: fetching sources")
    urls = {n: source_files(n) for n in SOURCES if n not in ("faces", "areawater")}
    for n, us in urls.items():
        fetch_all(us, public)
    counties = _read(cached(SOURCES["county"][0], public),
                     ["GEOID", "STATEFP", "NAMELSAD", "CBSAFP", "CSAFP", "METDIVFP", "ALAND"])
    counties = counties[counties["STATEFP"].isin(CONUS_STATEFP)].reset_index(drop=True)
    urls["faces"] = source_files("faces", counties["GEOID"])
    urls["areawater"] = source_files("areawater", counties["GEOID"])
    fetch_all([u for n in ("faces", "areawater") for u in urls[n]
               if os.path.basename(u) not in UNAVAILABLE], public)
    manifest = {"vintage": VINTAGE, "crs": CRS,
                "sources": [manifest_entry(n, urls[n], public) for n in SOURCES]}
    check_manifest(manifest)

    log("geo: states, gazetteer, ZCTA polygons")
    states = _read(cached(SOURCES["state"][0], public), ["STATEFP", "STUSPS"])
    states = states[states["STATEFP"].isin(CONUS_STATEFP)].reset_index(drop=True)
    fips_usps = dict(zip(states["STATEFP"], states["STUSPS"]))
    gaz = _gazetteer(cached(SOURCES["gaz_zcta"][0], public))
    lon, lat = gaz["INTPTLONG"].astype(float).values, gaz["INTPTLAT"].astype(float).values
    import geopandas as gpd
    pts = gpd.GeoDataFrame({"zcta": gaz["GEOID"].str.zfill(5)},
                           geometry=gpd.points_from_xy(lon, lat), crs="EPSG:4269").to_crs(CRS)
    pts["lon"], pts["lat"] = gaz["INTPTLONG"].values, gaz["INTPTLAT"].values
    pts["aland_gaz"] = gaz["ALAND"].astype(np.int64).values
    hit = gpd.sjoin(pts, states, predicate="within", how="left")
    hit = hit[~hit.index.duplicated()]
    pts["point_state"] = hit["STUSPS"].values
    conus = pts[pts["point_state"].notna()].reset_index(drop=True)

    zctas = _read(cached(SOURCES["zcta"][0], public), ["ZCTA5CE20"])
    zctas = zctas.rename(columns={"ZCTA5CE20": "zcta"})
    counties = counties.rename(columns={"GEOID": "county"})

    log("geo: perennial water by county")
    water = _county_water(counties["county"], public)
    log("geo: land pieces (ZCTA x county, less water)")
    land = land_pieces(zctas, counties, water)
    land = land[land["zcta"].isin(set(conus["zcta"]))].reset_index(drop=True)

    log("geo: places and urban areas")
    places = pd.concat([_read(p, ["GEOID", "NAMELSAD", "STATEFP"])
                        for p in fetch_all(urls["place"], public)], ignore_index=True)
    uac = _read(cached(SOURCES["uac"][0], public), ["GEOID20", "NAMELSAD20"])
    by_place = layer_pieces(land, places, "GEOID")
    by_uac = layer_pieces(land, uac, "GEOID20")

    overlay = pd.concat([
        land.groupby(["zcta", "county"], as_index=False)["land_m2"].sum()
            .rename(columns={"county": "geoid"}).assign(layer="county"),
        by_place.assign(layer="place"), by_uac.assign(layer="uac")], ignore_index=True)
    overlay["land_m2"] = overlay["land_m2"].round().astype(np.int64)
    overlay = overlay[["zcta", "layer", "geoid", "land_m2"]].sort_values(
        ["zcta", "layer", "geoid"]).reset_index(drop=True)

    log("geo: reference table")
    cty = overlay[overlay["layer"] == "county"]
    ref = conus[["zcta", "lon", "lat", "aland_gaz", "point_state"]].copy()
    ref["x"] = conus.geometry.x.round().astype(np.int64).values
    ref["y"] = conus.geometry.y.round().astype(np.int64).values
    ref["aland_overlay"] = ref["zcta"].map(cty.groupby("zcta")["land_m2"].sum()).fillna(0)
    ref["aland_overlay"] = ref["aland_overlay"].astype(np.int64)
    ref["county"] = ref["zcta"].map(primary(cty, "zcta"))
    cinfo = counties.set_index("county")
    ref["state"] = ref["county"].map(lambda c: fips_usps.get(str(c)[:2]) if isinstance(c, str)
                                     else None)
    for col, src in (("cbsa", "CBSAFP"), ("csa", "CSAFP"), ("metdiv", "METDIVFP")):
        ref[col] = ref["county"].map(cinfo[src])
    pl = overlay[overlay["layer"] == "place"]
    ua = overlay[overlay["layer"] == "uac"]
    ref["place"] = ref["zcta"].map(primary(pl, "zcta"))
    ref["uac"] = ref["zcta"].map(primary(ua, "zcta"))
    ref["urban_share"] = (ref["zcta"].map(ua.groupby("zcta")["land_m2"].sum()).fillna(0)
                          / ref["aland_overlay"].where(ref["aland_overlay"] > 0)).round(4)

    # co-est2025 spread over each county's ZCTA-covered land, so county totals are kept
    est = pd.read_csv(cached(SOURCES["co_est"][0], public), dtype=str, encoding="latin-1")
    est = est[est["SUMLEV"] == "050"]
    cpop = pd.Series(est["POPESTIMATE2025"].astype(np.int64).values,
                     index=(est["STATE"] + est["COUNTY"]).values)
    covered = cty.groupby("geoid")["land_m2"].sum()
    share = cty["land_m2"] / cty["geoid"].map(covered)
    zpop = (share * cty["geoid"].map(cpop)).groupby(cty["zcta"]).sum()
    ref["pop2025"] = ref["zcta"].map(zpop).fillna(0).round().astype(np.int64)

    log("geo: ZIP graph")
    state_polys = dict(zip(states["STUSPS"], states.geometry))
    xy = dict(zip(ref["zcta"], zip(conus.geometry.x.values, conus.geometry.y.values)))
    zip_state = dict(zip(ref["zcta"], ref["state"]))
    graph = zip_graph({z: xy[z] for z in ref["zcta"] if isinstance(zip_state[z], str)},
                      zip_state, state_polys)
    ref["graph_vertex"] = ref["zcta"].isin(set(graph["vertices"])).astype(int)
    exceptions = state_components(graph["vertices"], graph["edges"], zip_state)
    edges = pd.DataFrame(graph["edges"], columns=["a", "b", "kind", "border_m"])
    edges["border_m"] = edges["border_m"].round().astype(np.int64)

    log("geo: area names, county adjacency")
    areas = _areas(counties, places, uac, set(overlay["geoid"]), public)
    adj = pd.read_csv(cached(SOURCES["county_adjacency"][0], public), sep="|", dtype=str,
                      encoding="latin-1")
    adj = adj.rename(columns={"County GEOID": "county", "Neighbor GEOID": "neighbor",
                              "Length": "length_m"})[["county", "neighbor", "length_m"]]
    conus_cty = set(counties["county"])
    adj = adj[adj["county"].isin(conus_cty) & adj["neighbor"].isin(conus_cty)
              & (adj["county"] != adj["neighbor"])]

    rel = (ref["aland_overlay"] - ref["aland_gaz"]).abs() / ref["aland_gaz"]
    report = {
        "vintage": VINTAGE, "crs": CRS,
        "conus_zctas": int(len(ref)),
        "conus_zctas_without_county": sorted(ref.loc[ref["county"].isna(), "zcta"]),
        "land_check": {"tolerance": LAND_TOLERANCE, "max_rel_err": round(float(rel.max()), 6),
                       "over_tolerance": sorted(ref.loc[rel > LAND_TOLERANCE, "zcta"])},
        "point_in_other_state": sorted(ref.loc[ref["point_state"] != ref["state"], "zcta"]),
        "counties_without_zcta": sorted(conus_cty - set(cty["geoid"])),
        "counties_without_estimate": sorted(conus_cty - set(cpop.index)),
        "counties_without_faces": {g: UNAVAILABLE[f"tl_2025_{g}_faces.zip"]
                                   for g in sorted(conus_cty)
                                   if f"tl_2025_{g}_faces.zip" in UNAVAILABLE},
        "graph": {
            "vertices": len(graph["vertices"]), "edges": int(len(edges)),
            "override_pair": graph["override"],
            "missing": graph["missing"],
            "state_components": exceptions,
        },
    }

    log("geo: writing " + out)
    os.makedirs(out, exist_ok=True)
    cols = ["zcta", "state", "county", "cbsa", "csa", "metdiv", "place", "uac", "lon", "lat",
            "x", "y", "aland_gaz", "aland_overlay", "urban_share", "pop2025", "point_state",
            "graph_vertex"]
    _write_csv(ref[cols].sort_values("zcta"), os.path.join(out, "zcta_reference.csv.gz"))
    _write_csv(overlay, os.path.join(out, "zcta_overlay.csv.gz"))
    _write_csv(edges, os.path.join(out, "zcta_graph_edges.csv.gz"))
    _write_csv(areas, os.path.join(out, "areas.csv.gz"))
    _write_csv(adj.sort_values(["county", "neighbor"]),
               os.path.join(out, "county_adjacency.csv.gz"))
    _write_json(manifest, os.path.join(out, "MANIFEST.json"))
    _write_json(report, os.path.join(out, "REPORT.json"))
    return report


def _areas(counties, places, uac, used: set, public: str):
    """(layer, geoid, name, parent, lon, lat, pop2025) for the codes the reference uses."""
    import pandas as pd
    rows = [counties.assign(layer="county", geoid=counties["county"], name=counties["NAMELSAD"],
                            parent=counties["CBSAFP"])]
    cbsa = _read(cached(SOURCES["cbsa"][0], public), ["GEOID", "NAMELSAD", "CSAFP"], False)
    gcb = _gazetteer(cached(SOURCES["gaz_cbsa"][0], public)).set_index("GEOID")
    rows.append(cbsa.assign(layer="cbsa", geoid=cbsa["GEOID"], name=cbsa["NAMELSAD"],
                            parent=cbsa["CSAFP"], lon=cbsa["GEOID"].map(gcb["INTPTLONG"]),
                            lat=cbsa["GEOID"].map(gcb["INTPTLAT"])))
    csa = _read(cached(SOURCES["csa"][0], public), ["GEOID", "NAMELSAD"], False)
    rows.append(csa.assign(layer="csa", geoid=csa["GEOID"], name=csa["NAMELSAD"]))
    md = _read(cached(SOURCES["metdiv"][0], public), ["GEOID", "NAMELSAD", "CBSAFP"], False)
    rows.append(md.assign(layer="metdiv", geoid=md["GEOID"], name=md["NAMELSAD"],
                          parent=md["CBSAFP"]))
    gpl = _gazetteer(cached(SOURCES["gaz_place"][0], public)).set_index("GEOID")
    sub = pd.read_csv(cached(SOURCES["sub_est"][0], public), dtype=str, encoding="latin-1")
    sub = sub[sub["SUMLEV"] == "162"]
    ppop = pd.Series(sub["POPESTIMATE2025"].values, index=(sub["STATE"] + sub["PLACE"]).values)
    p = places[places["GEOID"].isin(used)]
    rows.append(pd.DataFrame({"layer": "place", "geoid": p["GEOID"], "name": p["NAMELSAD"],
                              "lon": p["GEOID"].map(gpl["INTPTLONG"]),
                              "lat": p["GEOID"].map(gpl["INTPTLAT"]),
                              "pop2025": p["GEOID"].map(ppop)}))
    u = uac[uac["GEOID20"].isin(used)]
    rows.append(pd.DataFrame({"layer": "uac", "geoid": u["GEOID20"], "name": u["NAMELSAD20"]}))
    cols = ["layer", "geoid", "name", "parent", "lon", "lat", "pop2025"]
    out = pd.concat([r.reindex(columns=cols) for r in rows], ignore_index=True)
    for c in ("lon", "lat"):
        out[c] = out[c].astype("string").str.strip()
    return out.sort_values(["layer", "geoid"]).reset_index(drop=True)


def _write_csv(df, path: str) -> None:
    """Gzip with no timestamp, so an unchanged table rebuilds byte-identical."""
    buf = df.to_csv(index=False, lineterminator="\n").encode()
    with open(path, "wb") as fh, gzip.GzipFile(fileobj=fh, mode="wb", mtime=0,
                                               filename="") as gz:
        gz.write(buf)


def _write_json(obj, path: str) -> None:
    with open(path, "w") as fh:
        json.dump(obj, fh, indent=1, sort_keys=False)
        fh.write("\n")


# ------------------------------------------------------------------------------ readers of the output
def read_reference(ref_dir: str = REFERENCE_DIR, name: str = "zcta_reference.csv.gz"):
    import pandas as pd
    return pd.read_csv(os.path.join(ref_dir, name), dtype=str, keep_default_na=False)


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="python -m td geo", description=__doc__.splitlines()[0])
    ap.add_argument("--public", default=PUBLIC_DIR, help="download cache (default data/public)")
    ap.add_argument("--out", default=REFERENCE_DIR, help="output (default reference/2025)")
    a = ap.parse_args(argv)
    report = build(a.public, a.out, log=lambda m: print(m, flush=True))
    g = report["graph"]
    print(f"geo: {report['conus_zctas']} CONUS ZCTAs, {g['vertices']} graph vertices, "
          f"{g['edges']} edges, {len(g['missing'])} missing; land max rel err "
          f"{report['land_check']['max_rel_err']}, "
          f"{len(report['land_check']['over_tolerance'])} over tolerance; "
          f"{len(g['state_components'])} state(s) not connected")
    return 0


if __name__ == "__main__":
    sys.exit(main())
