"""geo.py -- ZCTA coordinates and a state basemap, cached under `data/geo/`.

Two public Census files, fetched once and never re-fetched while the cache is present::

    2020_Gaz_zcta_national.zip   ~1 MB    ZCTA5 -> internal point (lon, lat)
    cb_2020_us_state_20m.zip     ~700 KB  state boundaries, 1:20m generalised

Both are public geography.  Nothing confidential goes into `data/geo/`, and nothing there is
committed -- the directory is gitignored, and the download is the recipe.

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

# EPSG:2163 written out; `+ellps=sphere` keeps it identical to the adjacency build's grid
LAEA = "+proj=laea +lat_0=45 +lon_0=-100 +ellps=sphere"

# lower 48 + DC: everything else is either off-map or would compress CONUS to a postage stamp
NON_CONUS = frozenset({"AK", "HI", "PR", "VI", "GU", "MP", "AS"})


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
