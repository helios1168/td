"""geo.py -- ZCTA coordinates, ZCTA polygons, and a state basemap.

Two public Census files, fetched once and never re-fetched while the cache under `data/geo/`
is present::

    2020_Gaz_zcta_national.zip   ~1 MB    ZCTA5 -> internal point (lon, lat)
    cb_2020_us_state_20m.zip     ~700 KB  state boundaries, 1:20m generalised

and one local-only file, never fetched (`zcta_polygons`, 822 MB, `docs/CODE_MAP.md`)::

    tl_2025_us_zcta520.shp       ~822 MB  ZCTA5 -> real ZIP Code Tabulation Area polygon

Both fetched files are public geography.  Nothing confidential goes into `data/geo/`, and
nothing there is committed -- the directory is gitignored, and the download is the recipe.

Projection is the same Lambert azimuthal equal-area the adjacency build used (data/README.md,
EPSG:2163's parameters written out): `lat_0=45 lon_0=-100` on a sphere.  Equal-area matters
here because bubble *area* encodes value; a Mercator map would inflate the northern metros
against the southern ones for free.

The gazetteer header is tab-delimited with **trailing whitespace on the column names** -- a
long-standing quirk of the file.  `zcta_points` strips them; matching on the raw names would
silently miss `INTPTLONG` and return nothing.
"""
from __future__ import annotations

import csv
import functools
import io
import os
import urllib.request
import zipfile

DEFAULT_DEST = os.path.join("data", "geo")

GAZ_URL = ("https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2020_Gazetteer/"
           "2020_Gaz_zcta_national.zip")
GAZ_TXT = "2020_Gaz_zcta_national.txt"

STATES_URL = "https://www2.census.gov/geo/tiger/GENZ2020/shp/cb_2020_us_state_20m.zip"
STATES_DIR = "cb_2020_us_state_20m"

# 2025 TIGER/Line ZCTA520, local only -- 822 MB, not something to cache-fetch like the two
# files above.  A module constant so a caller can point it at another vintage.  ZCTA5 codes are
# re-delineated only once a decade, but the geometry is refined between releases (865/2,000
# sampled 2025 polygons differ from 2020), so the vintage matters even though the codes don't.
#
# `data/` is gitignored and a worktree carries none (`CLAUDE.md`), so the repo-relative path
# resolves only in a checkout that has the bundle; `TD_ZCTA_SHP` overrides, and the hub is the
# fallback a worktree session lands on.  Absolute machine paths do not belong in the source, so
# the fallback is the last resort rather than the default.
ZCTA_REL = os.path.join("data", "tiger", "2025", "tl_2025_us_zcta520.shp")
ZCTA_HUB = os.path.join(os.path.expanduser("~"), "projects", "td", ZCTA_REL)
ZCTA_SHP = (os.environ.get("TD_ZCTA_SHP")
            or (ZCTA_REL if os.path.exists(ZCTA_REL) else ZCTA_HUB))

# EPSG:2163 written out; `+ellps=sphere` keeps it identical to the adjacency build's grid
LAEA = "+proj=laea +lat_0=45 +lon_0=-100 +ellps=sphere"

# lower 48 + DC: everything else is either off-map or would compress CONUS to a postage stamp
NON_CONUS = frozenset({"AK", "HI", "PR", "VI", "GU", "MP", "AS"})


def assert_conus(d) -> None:
    """Raise unless every zip of the loaded instance `d` carries a lower-48-or-DC state.

    The modelled ground set is CONUS plus DC (`docs/PROBLEM.md` §6): a blank-state, AK or HI
    zip enters no step of the pipeline, so every driver calls this right after loading and
    exits nonzero on the whole instance rather than placing those zips somewhere quietly.
    """
    bad = sorted(z for z in d.G
                 if not d.G.nodes[z].get("state") or d.G.nodes[z]["state"] in NON_CONUS)
    if bad:
        shown = ", ".join(f"{z} ({d.G.nodes[z].get('state') or 'no state'})" for z in bad[:8])
        raise ValueError(f"{len(bad)} zip(s) outside CONUS+DC in the instance: {shown}"
                         f"{', ...' if len(bad) > 8 else ''}; use the _conus instance")


# ------------------------------------------------------------------ cache-if-absent fetch
def _fetch_zip(url, dest):
    """Download `url` into memory and return the ZipFile.  One printed line per fetch."""
    os.makedirs(dest, exist_ok=True)
    print(f"geo: downloading {url}")
    with urllib.request.urlopen(url, timeout=180) as fh:
        blob = fh.read()
    return zipfile.ZipFile(io.BytesIO(blob))


def _cached_member(dest, name, url):
    """Path to `name` under `dest`, extracting it from `url`'s zip only if absent."""
    path = os.path.join(dest, name)
    if os.path.exists(path):
        return path
    with _fetch_zip(url, dest) as zf:
        member = next(m for m in zf.namelist() if os.path.basename(m) == name)
        with zf.open(member) as src, open(path, "wb") as out:
            out.write(src.read())
    print(f"geo: cached {name} at {path}")
    return path


def _cached_shapefile(dest, subdir, url):
    """Path to the .shp of an extracted shapefile bundle, fetching the zip only if absent."""
    root = os.path.join(dest, subdir)
    shp = os.path.join(root, subdir + ".shp")
    if os.path.exists(shp):
        return shp
    os.makedirs(root, exist_ok=True)
    with _fetch_zip(url, dest) as zf:
        zf.extractall(root)
    print(f"geo: cached {subdir} shapefile at {root}")
    return shp


# ------------------------------------------------------------------ points
def zcta_points(dest: str = DEFAULT_DEST) -> dict:
    """`{zcta5: (lon, lat)}` from the 2020 Census gazetteer internal points.

    Keys are the 5-character GEOID as written, so they join straight against the instance's
    zip codes without any int round-trip (which would eat the leading zero of `01103`).
    """
    path = _cached_member(dest, GAZ_TXT, GAZ_URL)
    out = {}
    with open(path, newline="", encoding="latin-1") as fh:
        rdr = csv.DictReader(fh, delimiter="\t")
        rdr.fieldnames = [f.strip() for f in (rdr.fieldnames or [])]   # the header quirk
        for row in rdr:
            z = (row.get("GEOID") or "").strip()
            lat, lon = (row.get("INTPTLAT") or "").strip(), (row.get("INTPTLONG") or "").strip()
            if not z or not lat or not lon:
                continue
            try:
                out[z.zfill(5)] = (float(lon), float(lat))
            except ValueError:
                continue
    return out


@functools.lru_cache(maxsize=1)
def _transformer():
    from pyproj import Transformer
    return Transformer.from_crs("EPSG:4269", LAEA, always_xy=True)


def project(lons, lats):
    """NAD83 lon/lat -> LAEA `(x, y)` metres.  `always_xy`, so the argument order is lon first."""
    import numpy as np
    x, y = _transformer().transform(np.asarray(lons, float), np.asarray(lats, float))
    return np.asarray(x, float), np.asarray(y, float)


# ------------------------------------------------------------------ basemap
def states_outline(dest: str = DEFAULT_DEST):
    """State boundaries as a GeoDataFrame in `LAEA`, lower 48 + DC only.

    Territories and the non-contiguous states are dropped rather than plotted: keeping them
    would either stretch the frame across the Pacific or need an inset, and the instance has
    no book outside CONUS anyway.
    """
    import geopandas as gpd
    shp = _cached_shapefile(dest, STATES_DIR, STATES_URL)
    gdf = gpd.read_file(shp)
    gdf = gdf[~gdf["STUSPS"].isin(NON_CONUS)]
    return gdf.to_crs(LAEA)


def zcta_polygons(zips, path: str = ZCTA_SHP) -> dict:
    """`{zcta5: polygon}` in `LAEA`, from the local 2025 TIGER/Line ZCTA520 shapefile, restricted
    to `zips`.

    Subsets by `ZCTA5CE20` **before** reprojecting: reprojecting all 33,791 polygons costs about
    3 s, subsetting first to the few thousand a table actually places costs a fraction of that.
    Cached on `(path, zips)` (`_transformer`'s `functools.lru_cache` idiom, above), so a second
    call in the same process with the same zip set costs nothing.

    Unlike `zcta_points` and `states_outline`, the shapefile itself is never fetched: the bundle
    is 822 MB, and it already lives locally (`docs/CODE_MAP.md`).  Raises `FileNotFoundError`
    naming the expected path if it is absent, rather than silently falling back to anything else.

    Keyed by the 5-character `ZCTA5CE20` code, zero-padded like `zcta_points` -- harmless on this
    shapefile (`ZCTA5CE20` already ships zero-padded), but a `path` pointed at another vintage
    could carry a numeric-typed code column, which would otherwise turn `01001` into `1001` and
    fail every New England zip's lookup silently downstream instead of here.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"ZCTA shapefile not found at {path!r} -- expected the 2025 TIGER/Line "
            f"tl_2025_us_zcta520.shp bundle (ZCTA5CE20 column).  This file is local only, not "
            f"cache-fetched like the gazetteer or the state shapefile.")
    wanted = tuple(sorted({str(z).strip().zfill(5) for z in zips}))
    gdf = _zcta_gdf(path, wanted)
    return dict(zip(gdf["ZCTA5CE20"], gdf.geometry))


@functools.lru_cache(maxsize=8)
def _zcta_gdf(path: str, zips: tuple):
    """The `ZCTA5CE20`/geometry rows of `path` whose code is in `zips`, reprojected to `LAEA`.

    Split out from `zcta_polygons` only so `functools.lru_cache` can key on the exact `(path,
    zips)` request -- `zcta_polygons` does the zero-padding and the `FileNotFoundError` first,
    so the cache never holds a request that would have raised.
    """
    import geopandas as gpd
    gdf = gpd.read_file(path, columns=["ZCTA5CE20"], engine="pyogrio")
    gdf["ZCTA5CE20"] = gdf["ZCTA5CE20"].astype(str).str.strip().str.zfill(5)
    gdf = gdf[gdf["ZCTA5CE20"].isin(zips)]
    return gdf.to_crs(LAEA)


def state_rook(dest: str = DEFAULT_DEST) -> tuple[dict, dict]:
    """`({state: (neighbour, ...)}, {state: polygon})` -- the state rook graph and its polygons.

    Two states are adjacent when their shared boundary has positive **length**, so a corner
    touch is not an edge (rook, not queen).  Same cached shapefile and same lower-48-plus-DC
    filter as `states_outline`: 49 nodes, 107 edges.

    A state-atom draw cannot get this from the instance.  Contracted to states, v2's zip
    adjacency has 10 edges over 42 components -- it describes where the book is sold, not
    which states touch -- so the geography has to come from TIGER.
    """
    import shapely
    gdf = states_outline(dest).reset_index(drop=True)
    codes = gdf["STUSPS"].astype(str).to_numpy()
    geoms = gdf.geometry.to_numpy()
    ia, ib = gdf.sindex.query(gdf.geometry, predicate="intersects")
    keep = ia < ib
    ia, ib = ia[keep], ib[keep]
    shared = shapely.length(shapely.intersection(geoms[ia], geoms[ib]))
    adj: dict = {c: set() for c in codes}
    for i, j, ln in zip(ia, ib, shared):
        if ln > 0:
            adj[codes[i]].add(codes[j])
            adj[codes[j]].add(codes[i])
    return {c: tuple(sorted(adj[c])) for c in codes}, dict(zip(codes, geoms))
