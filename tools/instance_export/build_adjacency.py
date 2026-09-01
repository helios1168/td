#!/usr/bin/env python3
"""build_adjacency.py -- ZCTA Rook adjacency + state membership from local TIGER files.

Companion to export_instance.py, run on the work machine when no adjacency graph exists.
Reads the TIGER ZCTA shapefile you already have (a .shp or the original .zip) and writes
the two side inputs the exporter takes:

    edges.csv    u,v            one row per Rook-adjacent ZCTA pair   (--graph)
    states.csv   zip_code,state one row per ZCTA                      (--states, optional)

Everything here derives from public Census TIGER data -- nothing confidential is read or
written, so the outputs are safe to keep anywhere.

    python3 build_adjacency.py --zcta tl_2020_us_zcta520.zip \
                               --state tl_2020_us_state.zip --out ./adj

**Rook means shared boundary of positive length**, not mere touching: of ~92k candidate
pairs from the spatial index, ~1.7k touch only at a corner point and must be excluded.
Getting this wrong inflates the edge set by ~2% and silently changes every contiguity
answer.  The rule below is the one verified against the repo's 2020 build (33,791 ZCTAs,
90,429 edges, 190 components; TIGER 2025 gives the byte-identical edge set).

State membership is assigned by which state polygon contains the ZCTA's internal point
(INTPTLON/INTPTLAT, falling back to a representative point).  ZCTAs can cross state
lines; the internal-point rule picks one, which is all the region labelling needs.

Needs geopandas + shapely 2.x (`pip install geopandas`).  Python 3.9+.
"""
from __future__ import annotations

import argparse
import csv
import os
import re
import sys
import time

CHUNK = 200_000                 # bound peak memory on the intersection buffers

# the verified national build, for the self-check (2020 and 2025 vintages agree)
EXPECT = dict(n=33_791, m=90_429, components=190)


def _id_column(gdf, pattern, label):
    cols = [c for c in gdf.columns if re.fullmatch(pattern, c)]
    if not cols:
        raise SystemExit(f"{label}: no column matching {pattern!r} "
                         f"(got {[c for c in gdf.columns if c != 'geometry']})")
    return cols[0]


def read_zcta(path, verbose=True):
    import geopandas as gpd
    t0 = time.perf_counter()
    if verbose:
        print(f"reading {path}")
    gdf = gpd.read_file(path)
    zcol = _id_column(gdf, r"ZCTA5CE\d*", "zcta file")
    gdf = gdf.sort_values(zcol).reset_index(drop=True)
    if verbose:
        print(f"  {len(gdf)} ZCTAs ({zcol}) in {time.perf_counter()-t0:.1f}s")
    return gdf, zcol


def rook_edges(gdf, zcol, verbose=True):
    """Rook pairs (shared boundary length > 0) as sorted (u, v) ZCTA-id tuples."""
    import numpy as np
    import shapely

    t0 = time.perf_counter()
    geoms = gdf.geometry.to_numpy()
    ids = gdf[zcol].astype(str).to_numpy()
    idx_a, idx_b = gdf.sindex.query(gdf.geometry, predicate="intersects")
    keep = idx_a < idx_b            # drop self-matches and the mirrored (j, i) half
    idx_a, idx_b = idx_a[keep], idx_b[keep]
    if verbose:
        print(f"  {len(idx_a)} candidate pairs ({time.perf_counter()-t0:.1f}s); "
              "computing shared-boundary length")
    out = []
    for s in range(0, len(idx_a), CHUNK):
        ia, ib = idx_a[s:s + CHUNK], idx_b[s:s + CHUNK]
        length = shapely.length(shapely.intersection(geoms[ia], geoms[ib]))
        for i, j in zip(ia[length > 0], ib[length > 0]):
            u, v = ids[i], ids[j]
            out.append((u, v) if u < v else (v, u))
        if verbose:
            print(f"  ... {min(s+CHUNK, len(idx_a))}/{len(idx_a)} candidates "
                  f"({time.perf_counter()-t0:.1f}s)")
    out = sorted(set(out))
    if verbose:
        print(f"  {len(out)} rook edges ({time.perf_counter()-t0:.1f}s)")
    return out


def n_components(ids, edges):
    parent = {z: z for z in ids}

    def find(z):
        while parent[z] != z:
            parent[z] = parent[parent[z]]
            z = parent[z]
        return z

    for u, v in edges:
        ru, rv = find(u), find(v)
        if ru != rv:
            parent[ru] = rv
    return len({find(z) for z in ids})


def internal_points(gdf):
    """One point per ZCTA: TIGER's internal point when present, else a representative."""
    import geopandas as gpd
    lat = [c for c in gdf.columns if re.fullmatch(r"INTPTLAT\d*", c)]
    lon = [c for c in gdf.columns if re.fullmatch(r"INTPTLON\d*", c)]
    if lat and lon:
        pts = gpd.points_from_xy(gdf[lon[0]].astype(float), gdf[lat[0]].astype(float))
        return gpd.GeoSeries(pts, crs="EPSG:4269").to_crs(gdf.crs)
    return gdf.geometry.representative_point()


def state_membership(gdf, zcol, state_path, verbose=True):
    """zip -> state postal code, by which state polygon holds the ZCTA's internal point."""
    import geopandas as gpd
    states = gpd.read_file(state_path)
    scol = "STUSPS" if "STUSPS" in states.columns else _id_column(
        states, r"STUSPS\d*", "state file")
    states = states.to_crs(gdf.crs)
    pts = gpd.GeoDataFrame({zcol: gdf[zcol].astype(str)},
                           geometry=internal_points(gdf), crs=gdf.crs)
    hit = gpd.sjoin(pts, states[[scol, "geometry"]], how="left", predicate="within")
    hit = hit[~hit.index.duplicated()]          # a point on a border: keep one state
    out = dict(zip(hit[zcol], hit[scol]))
    missing = [z for z, s in out.items() if not isinstance(s, str)]
    if missing and verbose:
        print(f"  NOTE {len(missing)} ZCTA internal point(s) fall in no state polygon "
              f"(coastal water is typical); they get state '' -- e.g. {missing[:5]}")
    return {z: (s if isinstance(s, str) else "") for z, s in out.items()}


def main(argv=None):
    p = argparse.ArgumentParser(prog="build_adjacency", description=__doc__.split("\n")[0])
    p.add_argument("--zcta", required=True, help="TIGER ZCTA5 shapefile (.shp or .zip)")
    p.add_argument("--state", default=None, help="TIGER state shapefile (optional)")
    p.add_argument("--out", default="./adj")
    a = p.parse_args(argv)

    gdf, zcol = read_zcta(a.zcta)
    edges = rook_edges(gdf, zcol)
    ids = gdf[zcol].astype(str).tolist()
    comps = n_components(ids, edges)

    print(f"\nself-check against the verified national build "
          f"(expected n={EXPECT['n']:,} m={EXPECT['m']:,} components={EXPECT['components']})")
    print(f"  built                    n={len(ids):,} m={len(edges):,} components={comps}")
    if (len(ids), len(edges), comps) != (EXPECT["n"], EXPECT["m"], EXPECT["components"]):
        print("  MISMATCH -- fine for a non-national or non-2020/2025 extract, otherwise "
              "stop and compare vintages before using the edges.")
    else:
        print("  exact match")

    os.makedirs(a.out, exist_ok=True)
    ep = os.path.join(a.out, "edges.csv")
    with open(ep, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["u", "v"])
        w.writerows(edges)
    print(f"wrote {ep}  ({len(edges):,} edges)")

    if a.state:
        st = state_membership(gdf, zcol, a.state)
        sp = os.path.join(a.out, "states.csv")
        with open(sp, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["zip_code", "state"])
            w.writerows(sorted(st.items()))
        print(f"wrote {sp}  ({len(st):,} ZCTAs, "
              f"{len({s for s in st.values() if s})} states)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
