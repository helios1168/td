# td — Serena entry point (the only memory)

Greenfield balanced districting for a new national annuity channel: maximum Nash welfare over
a per-rep utility model, two stages (draw k balanced compact districts; match reps by Hungarian
on log gains). Live instance `instance_descaled_v2.json.gz`, k = 18.

Where things are — do not duplicate them here:
- State (what landed, what's next): `STATE.md` `## Now`, `## Next`. Never `docs/STATE_LOG.md`.
- Environment, tests, traps, conventions: `CLAUDE.md` (root; project conventions:
  `from __future__ import annotations`, full type hints, narrative module docstrings that cite
  `tests/test_X.py::test_Y` and `docs/*.md`, `--` not em-dash in prose, match existing style).
- File map and run recipes: `docs/CODE_MAP.md`.
- Problem / model: `docs/CHANNEL.md`, `docs/MODEL.md`; problem statement `docs/FRAME.md`.
- Superseded documents: `docs/archive/README.md` says what replaced what.

Markdown is indexed (marksman): headings are symbols, so fetch one section with
`find_symbol("<heading>", relative_path="<file>.md", include_body=True)` instead of reading
the file. `docs/archive/**`, `docs/STATE_LOG.md` and `figures/**` are ignored.
