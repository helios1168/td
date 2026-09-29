# 2025 ZCTA reference build choices (td#62)

**Context.** td#62 (G1) builds `reference/2025/` with `td/geo.py`: the ZCTA reference table, its county, place and urban-area overlays, and OD2's ZIP graph (`mem:decisions/open-decisions-2026-09-28`). Its workers made four build choices without asking, on m5 on 2026-09-28 (runs `1f70192a` and `f9ef77a0`, m5 session 01a0e73f, forks 01a0e76f and 01a0e906). The owner approved the fallback in the fourth. #62 merged into td `main` at `eb4b09a` on 2026-09-29 (branch `m5-studio/62`, head `e746cbe`). The curator checked each choice against `td/geo.py`, `reference/2025/REPORT.json` and `tests/test_geo.py` at `eb4b09a` the same day, with `tests/run_all.py` at 38 passed and 0 failed. They were filed after landing because the owner had deferred them (`/Users/Shared/sv-ntlee/docs/memory/decisions/memory-system.md`, amendment of 2026-09-29). The measurements are in `mem:facts/zcta-2025-land-and-graph`.

**Decisions.**
1. **FACES is the land source, with a named AREAWATER fallback.** Each (ZCTA, county) piece loses that county's FACES faces with `LWFLAG` P (`_county_water`). The AREAWATER partly-land apportioning code was deleted. The seven counties whose FACES file census.gov would not serve (`UNAVAILABLE` in `geo.py`) take their water from their 2025 AREAWATER file instead. That water is the polygons with AWATER > 0 less the all-land ones. No other vintage stands in. The owner approved the fallback (#62 handoff comment 5876056561).
2. **DC–VA is recorded, not always added.** `zip_graph` finds the nearest DC–VA pair of vertices. The pair keeps its rook edge when the two cells already share a border, and gets an `override` edge only when they don't. `REPORT.json` gives the pair and its kind: `["20566", "22209", "rook"]` on the stand-in graph. `test_zip_graph_dc_va_override_is_the_only_manual_edge` covers both cases.
3. **Population spreads over ZIP-covered land.** Each county's `co-est2025` figure is spread over the county's land that falls inside ZCTAs, not over its full ALAND, so county totals are kept.
4. **Metro codes come from the primary county.** A ZIP's CBSA, CSA and METDIV are its primary county's, the county holding most of its land. The ZIP's state comes from that county too.

**Alternatives rejected.**
1. Keeping AREAWATER beside FACES for every county: it would double the download for no gain, since FACES is exact. AREAWATER alone left 13 CONUS ZCTAs over the 0.5% land check (`/Users/Shared/sv-ntlee/kb/census-geography.md`, "Land and water in TIGER/Line 2025").
2. Always adding a separate DC–VA override edge: OD2 names DC–VA as the one manual edge, and a second edge beside an existing rook edge would duplicate it.
3. Spreading over the county's full ALAND: this would drop the population of any county land that lies outside every ZCTA.
4. Giving each ZIP the CBSA with the largest land share: ZIP→county→metro would stop being one hierarchy, which OD5's county-built metros need.

**Consequences.** The land check passes on all 33,300 CONUS ZCTAs, including the seven fallback counties, and `REPORT.json` lists those counties under `counties_without_faces`. The manifest accepts only the named unavailable files (`test_manifest_accepts_only_the_named_unavailable_files`). While a file stays in `UNAVAILABLE`, the build takes its county's water from AREAWATER, even if census.gov serves the FACES file later. The graph facts describe the all-CONUS stand-in; C2/E1 rerun `zip_graph` on the extract's placed ZIPs.

**Status.** Settled for the 2025 reference build, landed in `eb4b09a` (2026-09-29).
