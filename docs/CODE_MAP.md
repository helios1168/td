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
| `docs/problem/PROBLEM.md`, `docs/problem/UNKNOWNS.md`, `docs/problem/BALANCE.md` | the settled/open ledger, the U-numbered unknowns, and the balance brief for the lens and the council |
| `docs/lenses/` | one file per lens or council pass, dated, never edited after |
| `docs/memory/` | facts and decisions; `INDEX.md` is one line per file, written through the `memory-curator` |
| `data/README.md` | what `data/` holds; nothing else in it is tracked |
| `tests/run_all.py` | the test runner |
| `tests/test_docs_owners.py` | the doc-ownership allowlist (`.claude/doc-owners.txt`) and the `STATE.md` shape |
| `tests/test_export_instance.py` | the exporter |
| `td/data.py` | v3 extract loader, CONUS rule and seeded sparse fixture |
| `tests/test_data.py` | loader round-trip, fixture concentration and ZIP graph checks |
| `td/audit.py` | the §9 audit: checks a run's ledger and writes `scorecard.md`; `python -m td.audit catalog` scores the tagged catalog |
| `tests/test_audit.py` | each audit check on a toy plan with planted defects, and the tagged catalog's known defects |
| `docs/RESULTS.md` | measured results, aggregates only: the tagged catalog's scorecard |
| `docs/RUN_WALKTHROUGH.md` | a plain-English walkthrough of `python -m td run` on the 51 scenario, and why it stopped at ±10% |
| `td/geo.py`, `reference/2025/` | the 2025 geography: the ZCTA reference table, its overlays, the ZIP graph and the source MANIFEST (#62) |
| `tests/test_geo.py` | the reference table, the manifest's 2025-only rule and the graph's explicit vertex set |
| `td/spec.py`, `scenarios/` | a TOML scenario: channels, domains, units, pieces and modes; the partition and ZIP-connectivity checks (#67) |
| `td/supports.py` | the closed support family and its drawability terms: corridor floor, border cap, rounding margin (#67) |
| `tests/test_spec.py`, `tests/test_supports.py` | partition, disconnected-whole stop, closure, brute-force corridor floor, the C6/C7 counterexamples |
| `td/master.py` | the support master per channel: the MILP on highspy, decoding, and the smallest δ exact or by bisection (#68) |
| `tests/test_master.py` | brute force on toys, decoded bands and shares, drawability rows, exact against bisection |
| `td/realize.py` | the ZIP realizer: centres, the transport LP, tree rounding, the mode-guarded repair and piece causes (#69) |
| `tests/test_realize.py` | the #1/#7/#11 regressions, the Claim 3 bound, the forest stop, clipped repair, the C10 star |
| `td/output.py`, `td/__main__.py`, `td/hooks.py` | `python -m td run <spec>` and `python -m td maps`: master, realizer, ledger, audit, names, ZCTA polygon maps (#71); `python -m td geo` builds the reference (#62) |
| `tests/test_output.py`, `tests/test_end_to_end.py` | the ledger schema against the tag's `scenarios.csv`, names, maps, and fixture scenarios end to end |

## Run

```bash
"$TD_PY" tests/run_all.py 2>&1 | rg -v '^\s*PASS '
```

## What a worktree must hand-copy

Nothing. The confidential extract, `instance_descaled*.json.gz`, stays at the hub root and is
gitignored, and so do the public 2025 files in `data/public/` (`tl_2025_us_state.zip`,
`tl_2025_us_zcta520.zip`); a worktree reads them from `$TD_REPO`.
