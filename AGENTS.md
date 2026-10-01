# td: support-master territory design

Plan districts for each planning channel of a national channel: divide the channel's
(ZIP, fine channel) opportunity into K_c districts whose drawn masses lie in a band, with a
support-based master MILP, a ZIP realizer and an audited `(ZIP, fine channel) → district` ledger
(`docs/problem/PROBLEM.md`, #52). Staffing is out of scope. Everything before the 2026-09-28
clean slate is in the tag `archive/pre-support-2026-09`. This file carries invariants only and
is never stamped. The workflow is `/Users/Shared/sv-ntlee/WORKFLOW.md`.

## Environment

- `$TD_REPO` is the hub clone; `$TD_PY` is `$TD_REPO/.venv/bin/python3`. The system python has no
  numpy/scipy/networkx. A worktree has no `.venv`; use `$TD_PY`.
- One environment, `.venv`, from `requirements.txt`.
- Only the `docs/figures/` that `docs/RESULTS.md` cites are tracked; regenerate a cited figure
  and commit it alongside the change.
- `data/public/`, `runs/` and `instance_descaled*.json.gz` (it carries per-rep sales shares) are
  gitignored; `docs/CODE_MAP.md` lists what a worktree must hand-copy.
- Background solver runs with `"$TD_PY" -u`.

## Tests

`"$TD_PY" tests/run_all.py 2>&1 | rg -v '^\s*PASS '` from the repo or worktree root prints only
the failures and the summary line: 24 fast tests, 0 fail (2026-09-28, m2). Do not wrap this
runner in `rtk test`: rtk cannot parse its output and keeps only the last 5 lines, which can hide
a FAIL.

## Git

- `gh` is for issues, labels, and milestones only. Git goes over SSH.
- One owner per `docs/*.md`, listed in `.claude/doc-owners.txt` and enforced by
  `tests/test_docs_owners.py`; a new doc needs a line there and a row in `docs/CODE_MAP.md`.
- When sharing artifacts with the user, give GitHub web links
  (`https://github.com/helios1168/td/blob/<branch>/<path>`), not `file://` paths.

## Tool routing

- Masked: sales, wholesaler (rep) names and firm names never enter this repo, an issue, a memory
  or anything online. The exporter replaces reps and firms with surrogates (`R…`, `F…`). In the
  extract, the per-rep shares (`share`, `share_free`) and the `firm` map are sales data: the model
  does not use them, and they never leave the extract.
- Not confidential (owner, 2026-09-30): descaled opportunity (`m_rel`) and everything the model
  makes from it, meaning run output, ledgers, maps and per-ZIP values. They may appear in docs,
  issues and memories. Since 2026-10-01 the same holds for opportunity in dollars (per-channel
  totals and per-district $) as shown on the stakeholder maps; sales stay masked.

## Traps that still apply

12. `scipy.optimize.milp` defaults `mip_rel_gap` to 1e-4; pass `mip_rel_gap=0.0` for a certificate (`docs/memory/facts/highs-traps.md`).
14. HiGHS 1.15 fails with "Solve error" under 1e-9 tolerances, and scipy 1.18.1's `linprog(method="highs")` can hang; pin `highs-ds` with an explicit `options` dict (`docs/memory/facts/highs-traps.md`).
15. Key solver retries on the engine's own stop reason, never on a harness-facing status (`docs/memory/facts/tooling-traps.md`).
16. Serena resolves relative paths against the hub, not the active worktree; pass absolute paths, or use Read/Edit (`docs/memory/facts/tooling-traps.md`).
18. HiGHS's thread pool is process-global and sized by the first `threads` value a process uses; use one thread count per process (`docs/memory/facts/highs-traps.md`).
19. A zero-objective feasibility solve is slower, not faster; never drop the objective to "just find a feasible point" (`docs/memory/facts/highs-traps.md`).
21. The ZIP graph's vertex set ships explicitly; never infer it from which ZIPs have a polygon or a cell (`docs/memory/facts/geography-traps.md`).
22. All geography is 2025 vintage; never mix vintages or compare a number across them (`docs/memory/facts/geography-traps.md`).
23. The drawn map (ZCTA polygons) and the contiguity model (the Voronoi rook graph) are different tessellations; a district that looks scattered on screen is not evidence of a contiguity failure (`docs/memory/facts/geography-traps.md`).
