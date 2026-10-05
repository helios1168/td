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
| `docs/problem/PROBLEM.md`, `docs/problem/UNKNOWNS.md`, `docs/problem/BALANCE.md`, `docs/problem/SPLITS.md` | the settled/open ledger, the U-numbered unknowns, the balance brief for the lens and the council, and the split brief for the council (#90) |
| `docs/problem/CONTIGUITY.md` | the contiguity brief for owner review (#106): M1 and the owner's rulings since, the history of contiguity in td with its waivers, the literature applied to td, ranked options and the CU unknowns |
| `docs/problem/MANDATES.md` | the owner-only register of hard requirements (M1 ZIP contiguity, masking): the owner's words, definition, check, latest value, waiver history and return trigger per row (#107) |
| `tests/test_mandates.py`, `tests/fixtures/m1/` | the register's rows: every field present, status `hard`, `deferred` or `waived`, checks that exist, and no deferral whose trigger holds; the 2026-09-01 contiguity deferral replayed on the 2026-09-28 graph fails; M1's check fails the broken fixtures (a detached piece, a corner-only touch, an unowned zero-opportunity ZCTA, an unapproved crossing) and passes the connected one |
| `tools/mandates/check.py` | the M1 run-folder gate (#108): `m1(run_dir)` is `td.audit.check_m1` on a run's ledger with the committed polygon graph and approved connectors, plus each district's largest detached piece as the scorer sizes it, on the ledger (#116); `--rescore <root>` gates every run folder, writes the table and M1's latest value in `docs/problem/MANDATES.md` (its only writer) |
| `docs/lenses/` | one file per lens or council pass, dated, never edited after |
| `docs/memory/` | facts and decisions; `INDEX.md` is one line per file, written through the `memory-curator` |
| `data/README.md` | what `data/` holds; nothing else in it is tracked |
| `tests/run_all.py` | the test runner |
| `tests/test_docs_owners.py` | the doc-ownership allowlist (`.claude/doc-owners.txt`) and the `STATE.md` shape |
| `tests/test_export_instance.py` | the exporter |
| `td/data.py` | v3 extract loader, CONUS rule and seeded sparse fixture |
| `tests/test_data.py` | loader round-trip, fixture concentration and ZIP graph checks |
| `td/audit.py` | the §9 audit: checks a run's ledger and writes `scorecard.md`, M1 (`check_m1`) among them; `python -m td.audit catalog` scores the tagged catalog |
| `tests/test_audit.py` | each audit check on a toy plan with planted defects, and the tagged catalog's known defects |
| `docs/RESULTS.md` | measured results, aggregates only: the tagged catalog's scorecard |
| `docs/RUN_WALKTHROUGH.md` | a plain-English walkthrough of `python -m td run` on the 51 scenario, and why it stopped at ±10% |
| `td/geo.py`, `reference/2025/` | the 2025 geography: the ZCTA reference table, its overlays, the ZIP graph and the source MANIFEST (#62) |
| `reference/2025/zcta_polygon_edges.csv.gz`, `zcta_polygon_vs_voronoi.csv.gz`, `connectors.csv`, `zcta_parts.csv.gz`, `zcta_part_edges.csv.gz`, `POLYGON_GRAPH.json` | M1's polygon graph (#108): rook adjacency of the TIGER 2025 ZCTA polygons over the shipped vertices, its edges added to and dropped from the Voronoi graph, the connector list (all approved by the owner on 2026-10-05; a rebuild keeps the owner's statuses and rows), the polygon parts and part-level edges the scorer uses for multipart pieces, and its manifest and report; `python -m td geo --polygon --public $TD_REPO/data/public` builds them |
| `tests/test_geo.py` | the reference table, the manifest's 2025-only rule and the graph's explicit vertex set |
| `td/spec.py`, `scenarios/` | a TOML scenario: channels, domains, units, pieces and modes; the partition and ZIP-connectivity checks (#67) |
| `td/supports.py` | the closed support family and its drawability terms: corridor floor, border cap, rounding margin (#67) |
| `tests/test_spec.py`, `tests/test_supports.py` | partition, disconnected-whole stop, closure, brute-force corridor floor, the C6/C7 counterexamples |
| `td/master.py` | the support master per channel: the MILP on highspy, decoding, and the smallest δ exact or by bisection (#68) |
| `tests/test_master.py` | brute force on toys, decoded bands and shares, drawability rows, exact against bisection |
| `td/realize.py` | the ZIP realizer: centres, the transport LP, tree rounding, the mode-guarded repair and piece causes (#69) |
| `tests/test_realize.py` | the #1/#7/#11 regressions, the Claim 3 bound, the forest stop, clipped repair, the C10 star |
| `td/territory.py` | the territory pass after the realizer (#116): every ZCTA of a channel's footprint owned, the zero-opportunity ones grown on the ZIP graph inside their unit, then state, then across a state, and joined where that lowers the pieces |
| `tests/test_territory.py` | a zero-opportunity ZCTA joining two pieces of one district, one held across a state line (a split, listed), a dropped unit owned and an unreached ZCTA left detached |
| `td/output.py`, `td/__main__.py`, `td/hooks.py` | `python -m td run <spec>` and `python -m td maps`: master, realizer, ledger, audit, names, ZCTA polygon maps (#71); `python -m td geo` builds the reference (#62) |
| `tests/test_output.py`, `tests/test_end_to_end.py` | the ledger schema against the tag's `scenarios.csv`, names, maps, and fixture scenarios end to end |
| `tools/exp81/` | #81's experiment code, not a production planner: `hess.py` the Hess-style ZIP planner, `run_hess.py` its solve and assemble driver, `measure.py` the per-map measures, `sidebyside.py` the side-by-side maps |
| `tools/exp/sweep.py`, `tools/exp/formulations.toml` | the experiment sweep runner (#92): expands a grid TOML, runs each job in its own process at one HiGHS thread count, and writes each run flat into `runs/exp/<lane>/<run_id>/` with its `manifest.json`; the formulations a grid may name |
| `tools/exp/index.py`, `tools/exp/table.py` | `runs/exp/index.jsonl` rebuilt from the manifests (rescored by `tools/looks/score.py` when present); the ranked Markdown table per lane or across lanes, and `runs/exp/shortlist.json` (run ids, tier, note) |
| `tests/test_exp_tracking.py` | a two-job grid on the 51 fixture run twice, a failed job, the grid product and run ids, the spec round trip, the table's order and `REVIEW` |
| `scenarios/experiments/` | experiment scenarios; `16n_12wh_24fi_nowifi_mtn1600.toml` is #81's (the 2026-10-01 18-split candidate) |
| `tools/exp/split_floor.py` | #94's split floor: per layout (no combined channel, NE, NE + plains) and IFA, each channel's forced splits and connected-parts floor at every K the $ rule allows (IFA's on the whole extract's $62.14B); arithmetic, no solve |
| `tests/test_split_floor.py` | #94's split floor on toys: forced splits by hand, the parts floor against brute force, the $-rule K range, the layouts as scenarios |
| `tests/test_exp81_hess.py`, `tests/test_exp81_measure.py`, `tests/test_exp81_sidebyside.py` | #81's experiment code on toys: the Hess loop against brute force, the measures by hand, the map legend |
| `tools/looks/score.py` | the looks scorer (#93): `score(run_dir)` gives a drawn run's eligibility (audit at ±15%, $ per district, main K, M1) and rank keys (channel-state splits, visual defects with polygon-graph pieces weighing 1 + mass/τ and multipart-only drawn pieces listed, shape, balance); the CLI ranks run folders and flags `REVIEW` |
| `tests/test_looks_score.py` | the looks scorer on toys: the display fill, each defect, the $ and K rules, `REVIEW` |

## Run

```bash
"$TD_PY" tests/run_all.py 2>&1 | rg -v '^\s*PASS '
```

## What a worktree must hand-copy

Nothing. The confidential extract, `instance_descaled*.json.gz`, stays at the hub root and is
gitignored, and so do the public 2025 files in `data/public/` (`tl_2025_us_state.zip`,
`tl_2025_us_zcta520.zip`); a worktree reads them from `$TD_REPO`.
