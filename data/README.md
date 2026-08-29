# `data/`

Contents relevant to the contiguity development programme (PLAN.md Part C.3, unit U4).

## `zcta_adjacency.npz` (committed, ~700 KB)

Rook adjacency (shared-boundary length > 0) over every ZCTA5 in TIGER2020, built by
`battery/code/twin.py::build_rook_adjacency` and cached with `save_adjacency`. numpy-only
format (`np.load(allow_pickle=False)` succeeds) so the fast test suite and
`battery/code/twin.py::load_twin` / `twin_pairs` never import geopandas.

Arrays:

| key | shape / dtype | meaning |
|---|---|---|
| `zcta` | `(n,) '<U5'` | ZCTA5 ids, ascending sort order |
| `edges` | `(m,2) int32` | index pairs into `zcta`, `i < j`, no duplicates |
| `lon`, `lat` | `(n,) float32` | internal point (`INTPTLON20`/`INTPTLAT20`), degrees, source CRS |
| `x`, `y` | `(n,) float32` | internal point reprojected to EPSG:2163 and rescaled to `[0,1]^2` with aspect preserved (one axis fills `[0,1]`, the other is `<= 1`) |
| `meta_json` | `(1,) '<U8000'` | JSON string: `vintage, build_date, crs, source_crs, n, m, build_seconds` |

Build provenance (this run, 2026-08-29, TIGER2020 `tl_2020_us_zcta520.zip`):

```
n = 33,791 ZCTAs, m = 90,429 rook edges
92,130 candidate pairs from the spatial-index query, 90,429 (98.2%) had a
positive-length shared boundary (the rest touch at a single point or share only
a bounding-box overlap)
build time: 65.6s wall (read 0.9s, sindex query 8.7s, vectorised shapely
intersection+length 56.9s, reprojection negligible)
190 connected components: one giant CONUS component (32,921 ZCTAs), 151 isolates
(islands / remote ZCTAs with no adjacent ZCTA polygon), the rest small
archipelago-like clusters (Hawaii, coastal Alaska, Puerto Rico, etc.)
degree: min 0, mean 5.35, max 25
.npz size: 717,100 bytes (well under the ~2 MB budget; savez_compressed)
```

CRS: internal points are reprojected from TIGER's native NAD83 (EPSG:4269) to
**EPSG:2163** ("US National Atlas Equal Area" -- a Lambert Azimuthal Equal-Area
projection centered at `lat_0=45, lon_0=-100` on a sphere; equivalent to
`+proj=laea +lat_0=45 +lon_0=-100`, the form PLAN.md names) before the `[0,1]^2`
rescale. National scope pulls Alaska/Hawaii/Puerto Rico into the same frame as CONUS,
so the rescaled `x, y` are a correct equal-area embedding but not a visually pleasing
one for a CONUS-only map; that is a graphics-layer concern (PLAN.md Part D / U7), not
this cache's.

Rebuild: `.venv/bin/python3 battery/code/twin.py build --out data/zcta_adjacency.npz`
(downloads TIGER2020 to `data/tiger/` first if absent). Reproducibility is checked by
the SLOW test `battery/code/tests/test_twin_build.py` (`TD_SLOW=1 ... -k twin_build`).

## `tiger/` (gitignored, not committed)

TIGER2020 ZCTA5 download target (`tl_2020_us_zcta520.zip`, ~528 MB, and its extracted
shapefile parts). Fetched by `twin.py::fetch_tiger()` from
`https://www2.census.gov/geo/tiger/TIGER2020/ZCTA520/tl_2020_us_zcta520.zip`; skipped if
already present. Never `git add` this directory (`.gitignore` already excludes
`data/tiger/`).

## `twin_*` (gitignored, not committed; not present yet)

Reserved for `twin_instance.json.gz` / `twin_stats.json`, produced on the work machine by
`tools/twin_export/` (PLAN.md Part C.2, unit U3) and copied in by hand after the user's
privacy audit. Not landed as of this unit (U4); `battery/code/twin.py::make_standin_twin`
is a locally fabricated stand-in used only by `battery/code/tests/test_twin.py` -- real
ZCTA ids/edges from `zcta_adjacency.npz`, synthetic A/B/M/rep maps -- and must never be
mistaken for privacy-audited data.
