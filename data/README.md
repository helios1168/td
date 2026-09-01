# `data/`

Empty in git. This file is the recipe for what used to live here.

## ZCTA Rook adjacency — dropped 2026-08-31, rebuild on demand

`zcta_adjacency.npz` (717 KB, national ZCTA5 Rook adjacency) was carried through the
2026-08-31 prune and then dropped: **nothing in this worktree reads it.** Its consumers
(`battery/code/twin.py`, `code/gfx/producers/twin_map.py`) went with the two-player stack, and
the national-channel route gets its graph from the work machine instead — `instance_export`
takes `--graph` from the firm's own pyarrow edge cache, and `td/instance.py` reads the edge
list out of the exported instance.

So adjacency is only needed here to build **test instances on real geography**. When that
happens, rebuild rather than restore: the file is a derived artifact and TIGER is public.

### How it was built

Builder: `battery/code/twin.py::build_rook_adjacency` / `save_adjacency` —
`git show contiguity-harness:battery/code/twin.py`. Reproducibility was checked by
`git show contiguity-harness:battery/code/tests/test_twin_build.py`.

```
.venv/bin/python3 battery/code/twin.py build --out data/zcta_adjacency.npz
```

Fetches `tl_2020_us_zcta520.zip` (~528 MB) from
`https://www2.census.gov/geo/tiger/TIGER2020/ZCTA520/` into `data/tiger/` if absent.

**Rook means shared boundary of positive length**, not mere touching — of 92,130 candidate
pairs from the spatial-index query, 90,429 (98.2%) survived that test; the rest touch at a
single point or only overlap in their bounding boxes. Getting this wrong inflates the edge
set by ~2% and silently changes every contiguity answer.

### What a correct rebuild produces

| | |
|---|---|
| n | 33,791 ZCTAs |
| m | 90,429 Rook edges |
| components | 190 — one giant CONUS component (32,921), 151 isolates (islands), the rest small archipelagos |
| degree | min 0, mean 5.35, max 25 |
| build time | ~66 s wall (the vectorised shapely intersection dominates at ~57 s) |

npz layout, numpy-only so `np.load(allow_pickle=False)` succeeds and no geopandas import is
needed at read time: `zcta` `(n,) '<U5'` ascending · `edges` `(m,2) int32` index pairs with
`i < j` · `lon`, `lat` `(n,) float32` internal points (`INTPTLON20`/`INTPTLAT20`) ·
`x`, `y` `(n,) float32` reprojected to **EPSG:2163** (US National Atlas Equal Area, Lambert
azimuthal, `lat_0=45 lon_0=-100`) and rescaled to `[0,1]²` preserving aspect ·
`meta_json` `(1,) '<U8000'`.

### Vintage does not matter

Checked 2026-08-29: TIGER **2025** `tl_2025_us_zcta520` run through the same builder gives
33,791 ZCTAs and 90,429 edges — a **byte-identical edge set** (Jaccard 1.000000) to the 2020
build. Both carry the 2020-census ZCTAs, so a work-machine graph on the 2025 vintage agrees
with a 2020 rebuild here, *provided* it used the Rook shared-boundary rule. `fetch_tiger`
hard-codes the 2020 filename; point it at a 2025 zip explicitly if you want that vintage.

Note the national footprint is 33,791 ZCTAs against the channel's **~1,229** — the national
cache was always far larger than this problem needs.

## `tiger/` — gitignored, never commit

TIGER download target. Already excluded by `.gitignore`.
