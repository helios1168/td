# `data/`

Nothing here is tracked except this file.

- `data/public/` (gitignored) caches the 2025 Census downloads that `python -m td geo` builds
  `reference/2025/` from (td#62, G1): the 2025 gazetteer ZCTA, CBSA and place files; the
  TIGER/Line 2025 ZCTA520, state, county, CBSA, CSA, METDIV, UAC20 and per-state place
  shapefiles; the per-county TIGER/Line 2025 FACES files (about 3,100) whose LWFLAG P faces
  turn polygon area into land, and the 2025 AREAWATER files of the few counties whose FACES file
  census.gov will not serve; the 2025 cartographic state and county outlines;
  `county_adjacency2025.txt`; `co-est2025-alldata.csv` and `sub-est2025.csv`. A file is
  fetched only when it is absent or is not a valid download (census.gov throttles, or rejects a
  file outright, by answering HTTP 200 with an HTML page, which the build rejects and retries). A
  worktree fetches its own cache, or points `--public` at the hub's. Every file's URL and
  sha256 are in `reference/2025/MANIFEST.json`, which is committed; the files census.gov will
  not serve are listed there as unavailable (`td.geo.UNAVAILABLE`). The HUD crosswalk (td#63,
  G2) will be cached here too.
- The confidential extract, `instance_descaled*.json.gz`, lives at the hub root on m2 and is
  gitignored. It is produced on the work machine by `export/export_instance.py`; see
  `docs/memory/workflow/confidential-data.md` for what may and may not leave it.

The pre-2026-09-28 contents of this file (the 2020 ZCTA rook-adjacency recipe) are in the tag
`archive/pre-support-2026-09`.
