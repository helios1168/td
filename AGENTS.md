# National channel territory design

Balanced territory design for a new national sales channel: carve the two largest firms out of
the financial-institutions and wirehouse channels into k districts of roughly equal opportunity
(about $1B each), then staff each district from the incumbent reps (`docs/PROBLEM.md`). The main
pi session orchestrates; subagents implement, verify, and reframe. This file carries invariants
only and is never stamped. The workflow is `/Users/Shared/sv-ntlee/WORKFLOW.md`.

## Stores

| kind | home | writer |
|---|---|---|
| Resume point | `STATE.md` (`## Now`, under 1 KB) | orchestrator |
| Task queue | GitHub Issues, `gh` in bash; milestones per track | orchestrator opens and closes |
| Facts and decisions | `docs/memory/` (`INDEX.md` first, files by name) | orchestrator, from `LEARNED:` lines |
| Problem ledger | `docs/problem/PROBLEM.md` (settled/open), `UNKNOWNS.md` (U-numbers) | orchestrator via `triage` |
| Lens output | `docs/lenses/<LENS>_<date>.md`, never edited after | orchestrator |
| Unit record | `docs/units/<id>.md` with `Status:` and `## Model`, `## Verify`, `## Code verify` | orchestrator |
| Code knowledge | Serena symbol tools; `docs/CODE_MAP.md` for entry points and recipes | tools |

`docs/foundations/` is read-only and never edited; `docs/foundations/archive/` is never read.

## Loop

`orient` → pick an issue → `/plan` if more than one file → `execute` (one mission, one worktree)
→ verify by a different vendor → `land` (acceptance output, curate memory, close with evidence,
`STATE.md`, commit) → new session. `flush` before any compaction. Every subagent report ends
with `LEARNED: <fact>` lines or `LEARNED: none`; only the orchestrator writes `docs/memory/`.

## Environment

- `$TD_REPO` is the hub clone; `$TD_PY` is `$TD_REPO/.venv/bin/python3`. The system python has no
  numpy/scipy/networkx. A worktree has no `.venv`; use `$TD_PY`.
- The Streamlit scenario app has its own venv, `.venv-app`, built from `app/requirements.txt`.
  Never install into `.venv` for the app: those pins are frozen and the zip50 anchor depends on
  them. The app never imports `td`; it drives the drivers by subprocess (`docs/APP.md`).
- MacTeX at `/Library/TeX/texbin`, not on `PATH` in non-interactive shells: prefix
  `export PATH=/Library/TeX/texbin:$PATH` when building a note.
- Never write under `battery/figures/`. `figures/` **is tracked** (a map is a primary artifact):
  regenerate with `tools/us_maps.py` and commit alongside the change.
- `data/`, `battery/results/` and `instance_descaled*.json.gz` (confidential) are gitignored;
  `docs/CODE_MAP.md` lists what a worktree must hand-copy.
- Serena resolves relative paths against the launch directory; pass absolute paths in a
  worktree. Background solver runs with `"$TD_PY" -u`.

## Tests

`"$TD_PY" tests/run_all.py 2>&1 | rg -v '^\s*PASS '` from the repo or worktree root prints only
the failures and the summary line: 545 fast tests, 0 fail (2026-09-11, sandbox). Do not wrap this
runner in `rtk test`: rtk cannot parse its output and keeps only the last 5 lines, which can hide
a FAIL. `TD_SLOW=1` adds nothing: no module sets `SLOW = True`. `tests/test_engines.py` is
the self-contained two-player smoke test. `tests/test_app_smoke.py` and `tests/test_mapfig.py`
need `.venv-app` to run for real; under `.venv` they skip, and `run_all.py -k` cannot select them
there because discovery imports every `test_*.py` before filtering and `.venv-app` has no
networkx. Run the module directly instead.

## Git

- The orchestrator commits and merges into `main`. A subagent commits only on its own worktree
  branch and never merges.
- Commit prefixes: `State:` for `STATE.md`, `Memory:` for `docs/memory/`, `Lens:` for
  `docs/lenses/`. Issue numbers in every other commit message.
- `gh` is for issues, labels, and milestones only. Git goes over SSH.
- One owner per `docs/*.md`, listed in `.claude/doc-owners.txt` and enforced by
  `tests/test_docs_owners.py`; a new doc needs a line there and a row in `docs/CODE_MAP.md`.
- When sharing artifacts with the user, give GitHub web links
  (`https://github.com/helios1168/td/blob/<branch>/<path>`), not `file://` paths.

## Tool routing

- Symbols: `serena_get_symbols_overview` for an unseen file, `serena_find_symbol` with the body
  only to edit, `serena_find_referencing_symbols` for callers; headings in Markdown are symbols.
- Text: grep with `-l` or `-c` first, then Serena at the hit. Read about 40 lines around a line.
- Whole-file reads only for a non-code file under 200 lines or 8 KB.
- Structured files: `jq`. Confidential data (`data/`, `battery/results/`, `instance_descaled*`):
  shapes, keys, counts, and aggregates only, never rows, and never in an issue or a memory.
- `session_search` before re-deriving anything that sounds familiar.

## Traps that still apply

2. **Equalisation can destroy value.** Never replace the Nash objective with an explicit
   balance minimisation; Nash-as-balance is the point (`docs/PROBLEM.md` §1).
4. **Fairness alone is degenerate**: every rep with no book at `z` values `z` identically.
12. `scipy.optimize.milp` defaults `mip_rel_gap` to 1e-4; pass `mip_rel_gap=0.0` for a certificate.
13. **Separator cuts must be component-wise**: one root per district per component, or the
    dual bound is unsound.
14. HiGHS 1.15 "Solve error" under 1e-9 tolerances; SCIP needs `misc/allow{strong,weak}dualreds`
    off for any lazily separated model, `ga ≤ Σu·x` not `==`, and a gain lower bound from the
    incumbent. scipy 1.18.1's `linprog(method="highs")` hangs on v2; `centers.assign()` pins
    `highs-ds` with an explicit `options` dict.
15. Key solver retries on the engine's stop reason (`extra["retryable"]`), never the
    harness-facing status.
16. Serena resolves relative paths against the hub, not the active worktree; pass absolute
    paths, or use Read/Edit.
17. ★8, "books enter at stage 2 only", has no cited basis since 2026-09-05: `fotakis2014` and
    Gibbard–Satterthwaite were both withdrawn, deliberately with no replacement. Never re-derive
    a basis from memory, and never let the misreporting exposure read as resolved.
18. **HiGHS's thread pool is process-global** and sized by the first `threads` value a process
    uses; a later solve at a different count in the same process returns status "Not Set"
    instead of solving (highspy 1.15, found 2026-09-09). One thread count per process: the
    portfolio parent uses 2, its members their own, `tests/run_all.py` never mixes.
19. **A zero-objective feasibility solve is slower, not faster**, on the level-1 MILP: HiGHS
    found no 10-split map in 120 s with the objective dropped, 96 s with it kept. The objective
    guides the search; never strip it to "just find a feasible point".
20. **Unavailable is not released.** A rep who cannot take a district (out of scope, or claimed
    by a multi-rep district) must be excluded from *candidacy*, never passed to
    `model.release_reps`: releasing folds their book into `S_free`, which `gain_matrix` prices at
    `c1` under `filler_capture="full"`, the same rate a rep values its own book, inflating every
    other candidate's valuation of those zips and distorting the match for every neighbouring
    district. `tools/staff.py`'s `held` set is the mechanism; `--release` cannot express it.
21. **`geom.json["cells"]` no longer means "this zip has a Voronoi cell"** (2026-09-09): cells
    are real ZCTA polygons, and the contiguity graph's vertex set ships separately as
    `proximity_zips`. A zip whose Voronoi cell clips away to nothing on the coastline has a
    ZCTA but no cell, so inferring the graph from `cells` admits it as an isolated vertex and
    makes the split's contiguity guard infeasible. Never re-derive that vertex set by inference.
22. **The gazetteer vintage is part of a result** (2026-09-09). `geo.zcta_points` defaults to
    2025; `TD_GAZ_VINTAGE=2020` selects the old file. The two are not interchangeable: 468 zips
    move more than 1 km between them, 70 more than 5 km, and the 2020 file has no point at all
    for 9 of the live instance's 3,713 zips, which then reach stage 1 unplaced and are assigned
    by utility. On the committed k=18 map the switch alone moves 31 zips. Never compare a number
    across vintages, and pin 2020 when reproducing anything drawn before this date.
23. **The drawn map and the contiguity model are different tessellations** (2026-09-09). `cells`
    in `geom.json` are real ZCTA polygons; `proximity_edges` is the rook graph of the *Voronoi* cells
    of the zip points. Over the instance's 3,704 placed zips the two graphs share 4,462 edges of
    10,483 and 4,843 (Jaccard 0.411), and real ZCTA adjacency alone gives 816 components with
    474 singletons, which is why the Voronoi graph is the model. A district that reads as
    scattered on screen is not evidence of a contiguity failure.

**Two-tier acceptance:** tier 1 `CERT_TOL = 1e-8`; tier 2 `base.EPS_CERT = 5e-3` nats, grounded
on a measured data-noise floor (re-measure on the real instance). The full trap list is in git
history: `git show contiguity-harness:CLAUDE.md`.
