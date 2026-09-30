# Code map

What is in the tree and how to run it. Stub since the 2026-09-28 clean slate (td#54): the
support-master package, `td/`, arrives in M3 (#52 §6), and each issue that adds a module adds
its row here. Everything removed from `main` is in the tag `archive/pre-support-2026-09`.

## Files

| file | role |
|---|---|
| `AGENTS.md` | project invariants for agents |
| `STATE.md` | the resume point |
| `README.md` | what the repo is and how to set it up |
| `export/export_instance.py`, `export/README.md` | the work-machine exporter and its runbook; standard library only |
| `docs/CODE_MAP.md` | this file |
| `docs/MODEL.md` | the support-master model: cells, units, supports, the master and its drawability rows, Claims 1–3, the realizer, the ledger and the audit; every claim tagged proved, claimed or policy |
| `docs/REFERENCES.md` | what td relies on each paper for: one row per claim, with its key, result, kb page and status |
| `docs/problem/PROBLEM.md`, `docs/problem/UNKNOWNS.md` | the settled/open ledger and the U-numbered unknowns |
| `docs/lenses/` | one file per lens or council pass, dated, never edited after |
| `docs/memory/` | facts and decisions; `INDEX.md` is one line per file, written through the `memory-curator` |
| `data/README.md` | what `data/` holds; nothing else in it is tracked |
| `tests/run_all.py` | the test runner |
| `tests/test_docs_owners.py` | the doc-ownership allowlist (`.claude/doc-owners.txt`) and the `STATE.md` shape |
| `tests/test_export_instance.py` | the exporter |
| `td/data.py` | v3 extract loader, CONUS rule and seeded sparse fixture |
| `tests/test_data.py` | loader round-trip, fixture concentration and ZIP graph checks |

## Run

```bash
"$TD_PY" tests/run_all.py 2>&1 | rg -v '^\s*PASS '
```

## What a worktree must hand-copy

Nothing yet. The confidential extract, `instance_descaled*.json.gz`, stays at the hub root and
is gitignored; a worktree that needs it reads it from `$TD_REPO`.
