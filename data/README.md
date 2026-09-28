# `data/`

Nothing here is tracked except this file.

- `data/public/` (gitignored) will cache the 2025 Census and HUD downloads that
  `python -m td geo` builds `reference/2025/` from (td#62, G1; td#63, G2). The sources, their
  URLs and sha256 go in `reference/2025/MANIFEST.json`, which is committed.
- The confidential extract, `instance_descaled*.json.gz`, lives at the hub root on m2 and is
  gitignored. It is produced on the work machine by `export/export_instance.py`; see
  `docs/memory/workflow/confidential-data.md` for what may and may not leave it.

The pre-2026-09-28 contents of this file (the 2020 ZCTA rook-adjacency recipe) are in the tag
`archive/pre-support-2026-09`.
