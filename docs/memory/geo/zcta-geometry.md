# ZCTA geometry and the gazetteer vintage (decided 2026-09-09)

**Drawn shapes are real census polygons.** The user reported that the map's zip geometry did
not match a map of the USA: `geom.json["cells"]` had been a Voronoi tessellation of 2020
Gazetteer centroids clipped to state outlines. Three user calls:
- A district's shape is the dissolve of its real ZCTAs, gaps showing (not a filled catchment).
- The split's contiguity graph stays the Voronoi rook adjacency, so no split result moved.
- 250 m simplification, chosen from a measured menu: 250 m = 3.3 MB, 500 m = 2.0 MB,
  1 km = 1.2 MB, raw = 97 MB, against 0.65 MB of Voronoi cells.
Source shapefile `data/tiger/2025/tl_2025_us_zcta520.shp`, 100% coverage of the 3,704 placed
zips. ZCTAs are re-delineated only each decennial: the 2025 TIGER release carries the same
33,791 ZCTA5 codes as 2020, with refined geometry on 865 of 2,000 sampled polygons. There is no
2025 re-delineation to ask for.

**The gazetteer is the 2025 vintage** (merged to `main`). The 2020 file had no internal point
for 9 of the 3,713 CONUS zips (0.16% of M), which reached stage 1 unplaced and were assigned by
utility alone; 36 more of its points fall outside their own ZCTA. The 2025 file covers all
3,713, every point lands inside its own polygon, and its points equal TIGER's
`INTPTLAT20`/`INTPTLONG20` to the decimetre (a 1 MB cache fetch, no local-only dependency).
`TD_GAZ_VINTAGE=2020` selects the old file; the committed-map smoke test pins it because every
draw before 2026-09-09 was measured on it. Cost of the switch: 468 zips move over 1 km (70 over
5 km, max 72.6 km), 31 zips change district on the committed k = 18 map; certified level-1
splits are unchanged at k = 10 to 18 and go from 10 to 11 at k = 20
(`mem:facts/level1-certified-splits`).

**Nothing drawn is Voronoi any more** (user request): rep territories, district colouring
adjacency and `district_pieces` use real ZCTA polygons. Only the reachability graph stays
Voronoi (`mem:geo/zip-adjacency`). `geom.json` gained `district_reach`, the tessellation
dissolve, because the union of a district's real ZCTAs is about 1,038 rings over a median of 62
parts and cannot be read as a border. The board fills it at 0.35 in the district's hue and
shades each zip cell by opportunity quantile within that hue (user: hue for identity, lightness
for opportunity).

Source: host memory td-contiguity-programme (2026-09-09 entries); CLAUDE.md traps 21 to 23.
