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

`python -m td geo --polygon` adds M1's polygon graph (#108, module section below):

    zcta_polygon_edges.csv.gz       (a, b, border_m): rook adjacency of the TIGER ZCTA polygons
    zcta_polygon_vs_voronoi.csv.gz  (a, b, change, border_m): its edges added to and dropped from
                                    the Voronoi ZIP graph
    connectors.csv                  the connector list across gaps, each row `proposed` until the
                                    owner approves it
    zcta_parts.csv.gz               (zcta, part, area_m2): the polygon parts of every ZCTA
    zcta_part_edges.csv.gz          (a, a_part, b, b_part, kind): the edges above at part level
                                    wherever a multipart ZCTA is an end, for the scorer's drawn
                                    pieces
    POLYGON_GRAPH.json              its manifest (sources, CRS, threshold, command) and report

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

**The polygon graph** (M1, `docs/problem/MANDATES.md`) is the rook graph of the TIGER/Line 2025
ZCTA520 polygons over the shipped vertex set (`graph_vertex`, trap 21): two ZCTAs are adjacent
when their boundaries share a length above `MIN_BORDER_M` = 0 m in `CRS`, so a corner touch
(length 0) is not an edge.  ZCTAs do not tile the land or the water, so the graph has islands:
water, and land in no ZCTA.  A *connector* joins two ZCTAs across such a gap; the build proposes
one per crossing it can name: every TIGER/Line 2025 primary or secondary road, or for an island
none reaches, any road of its counties and their neighbours, whose stretch outside every ZCTA
reaches ZCTAs of two components, and the ferries of `FERRIES`.  A new row is `proposed`; only
the owner sets `approved` (or `rejected`), the build keeps those statuses and every row the owner
added (kind `nearest`: an island with no crossing joined to its nearest ZCTA), and
`polygon_graph` adds only approved rows.  The owner approved every row on 2026-10-05 (#108):
bridges, tunnels, ferries, and roads across land in no ZCTA.

A multipart ZCTA is one vertex whose parts count as connected to each other, adjacent to another
ZCTA through any part (owner, 2026-10-05).  The part-level files let the looks scorer list a
separate drawn piece that only a multipart ZCTA makes, a visual defect and not an M1 failure.
"""
from __future__ import annotations

import collections
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


# ------------------------------------------------------------------------------ the polygon graph (M1)
POLYGON_EDGES = "zcta_polygon_edges.csv.gz"
POLYGON_DIFF = "zcta_polygon_vs_voronoi.csv.gz"
CONNECTORS = "connectors.csv"
POLYGON_REPORT = "POLYGON_GRAPH.json"
POLYGON_COMMAND = "python -m td geo --polygon --public $TD_REPO/data/public"
MIN_BORDER_M = 0.0          # an edge needs a shared boundary longer than this: a corner has length 0
TOUCH_M = 1.0               # a road's stretch outside every ZCTA this close to a polygon reaches it
ROAD_SEARCH_M = 30_000.0    # roads this close to an island's ZCTAs are searched for its crossings
CONNECTOR_COLUMNS = ("a", "b", "kind", "crossing", "gap_km", "status", "source")
CONNECTOR_STATUSES = ("proposed", "approved", "rejected")
# `nearest`: an island no road or scheduled ferry reaches, joined to its nearest ZCTA by the
# owner (2026-10-05, #108); the build never proposes one.
CONNECTOR_KINDS = ("bridge", "tunnel", "road", "ferry", "nearest")
ZCTA_PARTS = "zcta_parts.csv.gz"
PART_EDGES = "zcta_part_edges.csv.gz"
ROAD_SOURCES = {
    "prisecroads": (f"{TIGER}/PRISECROADS/", "primary and secondary roads, one file per state: "
                    "the crossings connectors name"),
    "roads": (f"{TIGER}/ROADS/", "all roads, one file per county, for the islands no primary or "
              "secondary road reaches"),
}
# (mainland ZCTA, island ZCTA, crossing): scheduled ferries to islands no road reaches, by their
# terminals' ZCTAs.  A hand list for the owner's one review (#108), not a TIGER/Line source.
FERRIES = (
    ("02543", "02568", "Woods Hole-Vineyard Haven ferry (Steamship Authority)"),
    ("02601", "02554", "Hyannis-Nantucket ferry (Steamship Authority)"),
    ("04841", "04853", "Rockland-North Haven ferry (Maine State Ferry Service)"),
    ("04841", "04863", "Rockland-Vinalhaven ferry (Maine State Ferry Service)"),
    ("04841", "04851", "Rockland-Matinicus ferry (Maine State Ferry Service)"),
    ("04855", "04852", "Port Clyde-Monhegan ferry"),
    ("49720", "49782", "Charlevoix-Beaver Island ferry"),
    ("43440", "43438", "Marblehead-Kelleys Island ferry"),
    ("43452", "43456", "Catawba-Put-in-Bay ferry (Miller Ferry)"),
    ("43452", "43446", "Catawba-Middle Bass ferry (Miller Ferry)"),
    ("90802", "90704", "Long Beach-Avalon ferry (Catalina Express)"),
    ("98136", "98070", "Fauntleroy-Vashon ferry (Washington State Ferries)"),
    ("98407", "98070", "Point Defiance-Tahlequah ferry (Washington State Ferries)"),
    ("54814", "54850", "Bayfield-La Pointe ferry (Madeline Island Ferry Line)"),
    ("54210", "54246", "Northport-Washington Island ferry (Washington Island Ferry Line)"),
    ("21817", "21824", "Crisfield-Ewell ferry (Smith Island)"),
    ("21817", "21866", "Crisfield-Tylerton ferry (Smith Island)"),
    ("21817", "23440", "Crisfield-Tangier ferry"),
    ("02809", "02872", "Bristol-Prudence Island ferry"),
    ("02882", "02807", "Point Judith-Block Island ferry"),
    ("06320", "06390", "New London-Fishers Island ferry"),
    ("10004", "10301", "Staten Island Ferry (Whitehall-St. George)"),
)


def polygon_edges(ids, geoms) -> dict:
    """Rook adjacency of `geoms` (polygons in `CRS`, keyed by `ids`): `{"edges": [(a, b,
    border_m)], "corner_only": [(a, b)], "overlaps": [(a, b)]}`, a < b.  A pair is an edge when the
    length its boundaries share exceeds `MIN_BORDER_M`; a pair that touches with no shared length
    and no common interior is `corner_only`; a pair whose interiors overlap is listed in
    `overlaps`, and is an edge only if it also shares boundary length (rook: one ZCTA nested in
    another without a hole is not adjacent).  The committed build has no overlapping pair."""
    import numpy as np
    import shapely
    ids, geoms = np.asarray(ids, dtype=object), np.asarray(geoms)
    ia, ib = shapely.STRtree(geoms).query(geoms, predicate="intersects")
    keep = ia < ib
    ia, ib = ia[keep], ib[keep]
    bound = shapely.boundary(geoms)

    def shared(lo, hi):
        return (shapely.length(shapely.intersection(bound[ia[lo:hi]], bound[ib[lo:hi]])),
                shapely.area(shapely.intersection(geoms[ia[lo:hi]], geoms[ib[lo:hi]])))

    parts = _threaded(shared, len(ia)) if len(ia) else []
    border = np.concatenate([p[0] for p in parts]) if parts else np.zeros(0)
    overlap = np.concatenate([p[1] for p in parts]) if parts else np.zeros(0)
    out = {"edges": [], "corner_only": [], "overlaps": []}
    for i, j, b, o in zip(ia, ib, border, overlap):
        a, z = sorted((ids[i], ids[j]))
        if o > 0:
            out["overlaps"].append((a, z))
        if b > MIN_BORDER_M:
            out["edges"].append((a, z, float(b)))
        elif o == 0:
            out["corner_only"].append((a, z))
    return {k: sorted(v) for k, v in out.items()}


def part_edges(ids, geoms, edges, connectors) -> dict:
    """The polygon graph at part level wherever a multipart ZCTA is an end: `{"parts": [(zcta,
    part, area_m2)] for every ZCTA, "edges": [(a, a_part, b, b_part, kind)]}`.  A part is a polygon
    of `shapely.get_parts`, in its order.  A rook pair of `edges` ((a, b, ...), a < b) with a
    multipart end gives each pair of parts whose boundaries share a length above `MIN_BORDER_M`,
    kind `rook` (an overlap alone is no edge); a connector row with a multipart end gives its
    nearest pair of parts, kind `connector`, whatever its status."""
    import numpy as np
    import shapely
    ids, geoms = np.asarray(ids, dtype=object), np.asarray(geoms)
    pieces = {z: shapely.get_parts(g) for z, g in zip(ids, geoms)}
    multi = {z for z, ps in pieces.items() if len(ps) > 1}
    parts = [(z, k, float(shapely.area(p))) for z in ids for k, p in enumerate(pieces[z])]
    pairs = [(a, b) for a, b, *_ in edges if a in multi or b in multi]
    pa, pb, la, lb = [], [], [], []
    for a, b in pairs:
        for i, p in enumerate(pieces[a]):
            for j, q in enumerate(pieces[b]):
                pa.append(p)
                pb.append(q)
                la.append((a, i))
                lb.append((b, j))
    pa, pb = np.asarray(pa), np.asarray(pb)
    near = shapely.intersects(pa, pb) if len(pa) else np.zeros(0, bool)
    border = np.zeros(len(pa))
    hit = np.flatnonzero(near)
    if len(hit):
        border[hit] = shapely.length(shapely.intersection(shapely.boundary(pa[hit]),
                                                          shapely.boundary(pb[hit])))
    out = [(*la[n], *lb[n], "rook") for n in hit if border[n] > MIN_BORDER_M]
    for r in connectors:
        a, b = r["a"], r["b"]
        if a in multi or b in multi:
            _, i, j = min((float(shapely.distance(p, q)), i, j) for i, p in enumerate(pieces[a])
                          for j, q in enumerate(pieces[b]))
            out.append((a, i, b, j, "connector"))
    return {"parts": parts, "edges": sorted(set(out))}


def components(vertices, edges) -> list:
    """The components of the graph, each a sorted list, largest first, then by smallest id."""
    import networkx as nx
    g = nx.Graph()
    g.add_nodes_from(vertices)
    g.add_edges_from((a, b) for a, b, *_ in edges)
    return sorted((sorted(c) for c in nx.connected_components(g)), key=lambda c: (-len(c), c[0]))


def _crossing_kind(names: list) -> str:
    text = " ".join(names)
    if re.search(r"\b(Tunl|Tunnel)\b", text):
        return "tunnel"
    if re.search(BRIDGE_NAME, text):
        return "bridge"
    return "road"


BRIDGE_NAME = r"\b(?:Brg|Bridge|Tunl|Tunnel|Cswy|Causeway|Viaduct|Xing)\b"


def _gap_chains(geoms, roads, near) -> list:
    """[(indices of the polygons a chain reaches, its road names longest first)] for the roads
    `near` (row indices of `roads`): each road's stretches outside the polygons it meets, chained
    where they touch."""
    import networkx as nx
    import numpy as np
    import shapely
    tree = shapely.STRtree(geoms)
    rg = np.asarray(roads.geometry.values)
    names = roads["FULLNAME"].fillna("").to_numpy()
    ri, zi = tree.query(rg[near], predicate="intersects")
    met = collections.defaultdict(list)
    for r, z in zip(ri, zi):
        met[near[r]].append(z)
    gaps, gap_names = [], []
    for i in near:
        rest = shapely.difference(rg[i], shapely.union_all(geoms[met[i]])) if met[i] else rg[i]
        for part in shapely.get_parts(rest):
            if part.length > 0:
                gaps.append(part)
                gap_names.append(names[i])
    if not gaps:
        return []
    gaps = np.asarray(gaps)
    ga, gb = shapely.STRtree(gaps).query(gaps, predicate="dwithin", distance=TOUCH_M)
    chains = nx.Graph()
    chains.add_nodes_from(range(len(gaps)))
    chains.add_edges_from(zip(ga, gb))
    out = []
    for chain in sorted(map(sorted, nx.connected_components(chains))):
        hit = np.unique(tree.query(gaps[chain], predicate="dwithin", distance=TOUCH_M)[1])
        length = collections.Counter()
        for p in chain:
            length[gap_names[p] or "unnamed road"] += gaps[p].length
        out.append((hit, [n for n, _ in sorted(length.items(), key=lambda kv: (-kv[1], kv[0]))]))
    return out


def _row(ids, geoms, i: int, j: int, names: list, source: str) -> dict:
    import shapely
    a, b = sorted((ids[i], ids[j]))
    top = names[:3]
    return {"a": a, "b": b, "kind": _crossing_kind(top), "crossing": " / ".join(top),
            "gap_km": round(float(shapely.distance(geoms[i], geoms[j])) / 1000.0, 2),
            "source": source}


def road_crossings(ids, geoms, comp: dict, roads, source: str) -> list:
    """Connector rows for the roads in `roads` (a frame with FULLNAME and geometry in `CRS`) that
    cross a gap between two components of `comp` ({zcta: component index}, 0 the largest).

    A chain (`_gap_chains`) reaching ZCTAs of two components, one not the largest, gives one row
    per pair of them, between their nearest two ZCTAs, named by the chain's longest road names.
    `gap_km` is the distance between those two polygons."""
    import numpy as np
    import shapely
    ids, geoms = np.asarray(ids, dtype=object), np.asarray(geoms)
    minor = np.asarray([comp[z] > 0 for z in ids])
    near = np.unique(shapely.STRtree(geoms[minor]).query(
        np.asarray(roads.geometry.values), predicate="dwithin", distance=ROAD_SEARCH_M)[0])
    out = []
    for hit, names in _gap_chains(geoms, roads, near):
        by_comp = collections.defaultdict(list)
        for h in hit:
            by_comp[comp[ids[h]]].append(h)
        if len(by_comp) < 2 or max(by_comp) == 0:
            continue
        cs = sorted(by_comp)
        for x in range(len(cs)):
            for y in range(x + 1, len(cs)):
                _, i, j = min((shapely.distance(geoms[i], geoms[j]), i, j)
                              for i in by_comp[cs[x]] for j in by_comp[cs[y]])
                out.append(_row(ids, geoms, i, j, names, source))
    return out


def bridge_crossings(ids, geoms, edges: set, roads, source: str) -> list:
    """Connector rows for the bridges and tunnels in `roads` (FULLNAME matching `BRIDGE_NAME`)
    anywhere: a chain (`_gap_chains`) of them gives one row per pair of the ZCTAs it reaches that
    is not already an edge of `edges` ({(a, b)}, a < b), so a bridge between two ZCTAs of one
    component (Mackinac, Chesapeake Bay) is proposed as well as one to an island."""
    import numpy as np
    ids, geoms = np.asarray(ids, dtype=object), np.asarray(geoms)
    near = np.flatnonzero(roads["FULLNAME"].fillna("").str.contains(BRIDGE_NAME, regex=True).to_numpy())
    out = []
    for hit, names in _gap_chains(geoms, roads, near):
        out += [_row(ids, geoms, i, j, names, source) for x, i in enumerate(hit) for j in hit[x + 1:]
                if tuple(sorted((ids[i], ids[j]))) not in edges]
    return out


def _dedupe_connectors(rows: list) -> list:
    """One row per ZCTA pair: the shortest gap's, ties by crossing name."""
    best = {}
    for r in sorted(rows, key=lambda r: (r["gap_km"], r["crossing"])):
        best.setdefault((r["a"], r["b"]), r)
    return [best[k] for k in sorted(best)]


def read_connectors(ref_dir: str = REFERENCE_DIR, path: str | None = None) -> list:
    """The connector rows of `connectors.csv` (or `path`), as dicts; an absent file has none."""
    import csv
    path = path or os.path.join(ref_dir, CONNECTORS)
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    bad = [f"{r['a']}-{r['b']}: status {r['status']!r}" for r in rows
           if r["status"] not in CONNECTOR_STATUSES]
    if bad:
        raise ValueError(f"{path}: " + "; ".join(bad))
    return rows


def polygon_graph(ref_dir: str = REFERENCE_DIR, connectors: list | None = None) -> dict:
    """M1's graph: `{"vertices", "edges", "state"}`, the shipped vertex set, the polygon edges plus
    the owner-approved connectors only (`connectors` defaults to `ref_dir`'s list), and each
    vertex's state."""
    ref = read_reference(ref_dir)
    ref = ref[ref["graph_vertex"] == "1"]
    edges = read_reference(ref_dir, name=POLYGON_EDGES)
    rows = read_connectors(ref_dir) if connectors is None else connectors
    return {"vertices": sorted(ref["zcta"]),
            "edges": list(zip(edges["a"], edges["b"])) + approved_connectors(rows),
            "state": dict(zip(ref["zcta"], ref["state"]))}


def approved_connectors(rows: list) -> list:
    """[(a, b)] of the connector rows the owner approved; a proposed or rejected row adds no edge."""
    return [(r["a"], r["b"]) for r in rows if r["status"] == "approved"]


def _road_files(public: str, kind: str, keys) -> list:
    url = ROAD_SOURCES[kind][0]
    return fetch_all([f"{url}tl_2025_{k}_{kind}.zip" for k in sorted(keys)], public)


def _read_roads(paths: list):
    import pandas as pd
    return pd.concat([_read(p, ["FULLNAME"]) for p in paths], ignore_index=True)


def polygon_build(public: str = PUBLIC_DIR, out: str = REFERENCE_DIR, log=print) -> dict:
    """Build the polygon graph, its Voronoi comparison and the connector list into `out` (module
    doc).  The connector rows already in `out` keep their status.  Returns the report."""
    import numpy as np
    import pandas as pd
    import shapely

    ref = read_reference(out)
    vertices = sorted(ref.loc[ref["graph_vertex"] == "1", "zcta"])
    with open(os.path.join(out, "MANIFEST.json"), encoding="utf-8") as fh:
        zcta_entry = next(e for e in json.load(fh)["sources"] if e["name"] == "zcta")
    zpath = cached(SOURCES["zcta"][0], public)
    if sha256(zpath) != zcta_entry["sha256"]:
        raise ValueError(f"{zpath} is not the ZCTA file MANIFEST.json hashes")
    log("geo: ZCTA polygons")
    df = _read(zpath, ["ZCTA5CE20"])
    df = df[df["ZCTA5CE20"].isin(set(vertices))].sort_values("ZCTA5CE20").reset_index(drop=True)
    ids, geoms = df["ZCTA5CE20"].to_numpy(), np.asarray(df.geometry.values)
    no_polygon = sorted(set(vertices) - set(ids))

    log("geo: polygon rook edges")
    got = polygon_edges(ids, geoms)
    comps = components(vertices, got["edges"])
    comp = {z: i for i, c in enumerate(comps) for z in c}
    vor = read_reference(out, name="zcta_graph_edges.csv.gz")
    vor_border = {tuple(sorted(p)): float(m) for *p, m in zip(vor["a"], vor["b"], vor["border_m"])}
    pol_border = {(a, b): m for a, b, m in got["edges"]}
    diff = ([(a, b, "added", m) for (a, b), m in sorted(pol_border.items()) if (a, b) not in vor_border]
            + [(a, b, "dropped", m) for (a, b), m in sorted(vor_border.items())
               if (a, b) not in pol_border])

    log("geo: connectors from primary and secondary roads")
    prisec = _road_files(public, "prisecroads", CONUS_STATEFP)
    prisec_roads = _read_roads(prisec)
    rows = road_crossings(ids, geoms, comp, prisec_roads, "TIGER/Line 2025 prisecroads")
    rows += bridge_crossings(ids, geoms, set(pol_border), prisec_roads, "TIGER/Line 2025 prisecroads")
    reached = {comp[r["a"]] for r in rows} | {comp[r["b"]] for r in rows}
    ferry_rows = []
    for a, b, crossing in FERRIES:
        if a not in comp or b not in comp or comp[a] == comp[b]:
            raise ValueError(f"ferry {a}-{b}: both must be vertices, in different components")
        i, j = np.searchsorted(ids, [a, b])
        ferry_rows.append({"a": min(a, b), "b": max(a, b), "kind": "ferry", "crossing": crossing,
                           "gap_km": round(float(shapely.distance(geoms[i], geoms[j])) / 1000.0, 2),
                           "source": "geo.FERRIES (hand list)"})
    reached |= {comp[r["b"]] for r in ferry_rows} | {comp[r["a"]] for r in ferry_rows}
    lonely = [i for i in range(1, len(comps)) if i not in reached]
    if lonely:
        log(f"geo: connectors from county roads for {len(lonely)} islands")
        adj = read_reference(out, name="county_adjacency.csv.gz")
        county = dict(zip(ref["zcta"], ref["county"]))
        home = {county[z] for i in lonely for z in comps[i]}
        near = home | set(adj.loc[adj["county"].isin(home), "neighbor"])
        roads = _road_files(public, "roads", near)
        rows += road_crossings(ids, geoms, {z: (c if c in lonely else 0) for z, c in comp.items()},
                               _read_roads(roads), "TIGER/Line 2025 roads")
    else:
        near, roads = set(), []
    proposals = _dedupe_connectors(rows + ferry_rows)
    old = {(r["a"], r["b"], r["crossing"]): r["status"] for r in read_connectors(out)}
    connectors = [{**r, "status": old.get((r["a"], r["b"], r["crossing"]), "proposed")}
                  for r in proposals]
    kept = [r for r in read_connectors(out) if r["status"] != "proposed" and
            (r["a"], r["b"], r["crossing"]) not in {(c["a"], c["b"], c["crossing"]) for c in connectors}]
    connectors += kept                  # an owner's decision is never dropped by a rebuild

    joined = components(range(len(comps)), [(comp[r["a"]], comp[r["b"]]) for r in connectors])
    approved = components(vertices, got["edges"] + approved_connectors(connectors))
    state = dict(zip(ref["zcta"], ref["state"]))
    islands = [{"component": i, "zctas": comps[i], "states": sorted({state[z] for z in comps[i]}),
                "connectors": sum(1 for r in connectors if i in (comp[r["a"]], comp[r["b"]])),
                "joined_to_main_by_any_row": 0 in next(c for c in joined if i in c),
                "joined_to_main_by_approved": comps[i][0] in approved[0]}
               for i in range(1, len(comps))]
    log("geo: multipart ZCTAs at part level")
    by_part = part_edges(ids, geoms, got["edges"], connectors)
    n_parts = collections.Counter(z for z, *_ in by_part["parts"])
    sources = [_road_entry("prisecroads", prisec, public)]
    if roads:
        sources.append(_road_entry("roads", roads, public))
    report = {
        "vintage": VINTAGE, "crs": CRS, "command": POLYGON_COMMAND,
        "adjacency": f"rook: boundaries share a length > {MIN_BORDER_M:g} m in {CRS}; a corner "
                     "touch (length 0) is not an edge",
        "min_border_m": MIN_BORDER_M, "touch_m": TOUCH_M, "road_search_m": ROAD_SEARCH_M,
        "sources": [zcta_entry] + sources,
        "vertices": len(vertices), "no_polygon": no_polygon, "edges": len(got["edges"]),
        "smallest_border_m": round(min(m for *_, m in got["edges"]), 3),
        "corner_only_pairs": len(got["corner_only"]), "overlapping_pairs": got["overlaps"],
        "against_voronoi": {"voronoi_edges": len(vor_border), "shared": len(vor_border) - sum(
            1 for d in diff if d[2] == "dropped"), "added": sum(1 for d in diff if d[2] == "added"),
            "dropped": sum(1 for d in diff if d[2] == "dropped")},
        "components": len(comps), "component_sizes": [len(c) for c in comps],
        "connectors": {"rows": len(connectors), **collections.Counter(r["kind"] for r in connectors),
                       **{s: sum(1 for r in connectors if r["status"] == s)
                          for s in CONNECTOR_STATUSES}},
        "components_with_approved_connectors": len(approved),
        "component_sizes_with_approved_connectors": [len(c) for c in approved],
        "multipart_zctas": sum(1 for n in n_parts.values() if n > 1),
        "part_edges": {"rook": sum(1 for e in by_part["edges"] if e[4] == "rook"),
                       "connector": sum(1 for e in by_part["edges"] if e[4] == "connector")},
        "county_road_counties": sorted(near),
        "islands": islands,
        "islands_without_a_connector": [i["zctas"] for i in islands if not i["connectors"]],
    }
    log("geo: writing " + out)
    _write_csv(pd.DataFrame(got["edges"], columns=["a", "b", "border_m"]).round({"border_m": 2}),
               os.path.join(out, POLYGON_EDGES))
    _write_csv(pd.DataFrame(diff, columns=["a", "b", "change", "border_m"]).round({"border_m": 2}),
               os.path.join(out, POLYGON_DIFF))
    pd.DataFrame(sorted(connectors, key=lambda r: (r["a"], r["b"], r["crossing"])),
                 columns=list(CONNECTOR_COLUMNS)).to_csv(os.path.join(out, CONNECTORS), index=False,
                                                         lineterminator="\n")
    _write_csv(pd.DataFrame(by_part["parts"], columns=["zcta", "part", "area_m2"]).round(
        {"area_m2": 0}), os.path.join(out, ZCTA_PARTS))
    _write_csv(pd.DataFrame(by_part["edges"], columns=["a", "a_part", "b", "b_part", "kind"]),
               os.path.join(out, PART_EDGES))
    _write_json(report, os.path.join(out, POLYGON_REPORT))
    return report


def _road_entry(name: str, paths: list, public: str) -> dict:
    """A manifest entry, as `manifest_entry`, for the road files a polygon build read."""
    files = {os.path.basename(p): sha256(p) for p in paths}
    listing = "".join(f"{f} {h}\n" for f, h in sorted(files.items()))
    return {"name": name, "url": ROAD_SOURCES[name][0], "vintage": VINTAGE,
            "use": ROAD_SOURCES[name][1], "sha256": hashlib.sha256(listing.encode()).hexdigest(),
            "files": dict(sorted(files.items()))}


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="python -m td geo", description=__doc__.splitlines()[0])
    ap.add_argument("--public", default=PUBLIC_DIR, help="download cache (default data/public)")
    ap.add_argument("--out", default=REFERENCE_DIR, help="output (default reference/2025)")
    ap.add_argument("--polygon", action="store_true",
                    help="build M1's polygon graph and connector list from the reference in --out")
    a = ap.parse_args(argv)
    if a.polygon:
        r = polygon_build(a.public, a.out, log=lambda m: print(m, flush=True))
        print(f"geo: polygon graph {r['vertices']} vertices, {r['edges']} edges, "
              f"{r['corner_only_pairs']} corner-only pairs, {r['components']} components; "
              f"{r['connectors']['rows']} connectors, "
              f"{len(r['islands_without_a_connector'])} islands without one; "
              f"{r['components_with_approved_connectors']} components with the approved ones")
        return 0
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
