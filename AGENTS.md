# National channel territory design

Balanced territory design for a new national sales channel: carve the two largest firms out of
the financial-institutions and wirehouse channels into k districts of roughly equal opportunity
(about $1B each), then staff each district from the incumbent reps (`docs/PROBLEM.md`). Claude
Code orchestrates and Codex implements. Both read this file; it carries invariants only and is
never stamped.

## Start-up

1. `STATE.md` `## Now` is the resume point; then `bd ready` for the open work and `bd show <id>`
   for your bead. History: `git log --grep '^State:' -p -- STATE.md`.
2. `docs/CODE_MAP.md` for files and recipes; `docs/PROBLEM.md` / `docs/MODEL.md` for the problem
   and the model.
3. A scenario question (pin a region, change k, swap the engine) goes to the Streamlit app
   (`tools/app.sh`, `docs/APP.md`), which has an engine behind it. Artifacts are for fixed,
   reviewed deliverables.
4. Never read `docs/foundations/archive/`, or a whole `docs/*.md` unprompted; take the section you
   need via Serena (headings are symbols).

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
- Serena binds to the session's launch directory; activate by path before the first symbol
  edit. Background solver runs with `"$TD_PY" -u`.

## Tests

`"$TD_PY" tests/run_all.py 2>&1 | rg -v '^\s*PASS '` from the repo or worktree root prints only
the failures and the summary line: 545 fast tests, 0 fail (2026-09-11, sandbox). Do not wrap this
runner in `rtk test`: rtk cannot parse its output and keeps only the last 5 lines, which can hide
a FAIL. `TD_SLOW=1` adds nothing: no module sets `SLOW = True`. `tests/test_engines.py` is
the self-contained two-player smoke test. `tests/test_app_smoke.py` and `tests/test_mapfig.py`
need `.venv-app` to run for real; under `.venv` they skip, and `run_all.py -k` cannot select them
there because discovery imports every `test_*.py` before filtering and `.venv-app` has no
networkx. Run the module directly instead.

## Docs discipline

- One owner per file, listed in `.claude/doc-owners.txt` and enforced by
  `tests/test_docs_owners.py`. A new `docs/*.md` needs a line there and an owner row in
  `docs/CODE_MAP.md` `## Files`.
- `docs/foundations/` is read-only and never edited.
- The permanent record of a unit is `docs/units/<id>.md`, carrying a `Status: open|done|dropped`
  line and `## Model`, `## Verify`, `## Code verify` sections. Verifier artifacts are committed
  under `tools/verify/<id>/`; they are never test-discovered.
- Bugs and small todos live in code as a `TODO` at the site (the runner has no `xfail`).
- A track is an epic bead. There is no `PLAN.md`.
- `STATE.md` holds only `## Now`, at most 1 KB, edited directly; its commits take the prefix
  `State:`.

## Worktrees

A worktree is `.claude/worktrees/<id>` on branch `worktree-<id>`, created with plain git and
locked:

    git worktree add .claude/worktrees/<id> -b worktree-<id>
    git worktree lock --reason "keep" .claude/worktrees/<id>

Claude never uses `EnterWorktree(name)`; it enters an existing worktree by path. A worktree has
no `.venv`; use `$TD_PY`. Serena must be given absolute worktree paths (relative paths resolve
against the hub and can write to the user's checkout, trap 16). After a merge the orchestrator
unlocks and removes the worktree and deletes the branch.

## Beads workflow

Beads (`bd`) is the task queue, committed as `.beads/issues.jsonl`.

- `bd ready` lists unblocked beads; `bd show <id>` prints one in full. Start a bead with
  `bd update <id> --status in_progress` and finish it with `bd close <id>`.
- Labels: `thread:model` or `thread:impl`; `kind:verify-math` or `kind:verify-code`;
  `unit:<id>`; `author:claude` or `author:codex`.
- Metadata: `files` (the file set the bead owns; touch nothing outside it), `test` (the command
  that must pass), `memories` (the Serena memories to read first), `unit`, `accept` (the
  acceptance rule), `author`.
- A unit runs as one chain, each bead blocked by the one before: model, verify math,
  implementation, verify code. A verify bead goes by default to the agent that did not author the
  work.

## Memory

Serena project memories in `.serena/memories/` are the only memory store. They are topic-named:
`facts/...` for measured numbers, `solver/...` for solver behaviour, and so on. Read the ones a
bead's `memories` names before starting. Only Claude writes them. Every other agent ends its
report with one `LEARNED: <fact>` line per durable finding, and the orchestrator curates those
into memories.

## Git

- The orchestrator (the main Claude session) commits and merges into `main`.
- A spawned agent (a Codex run, a Claude subagent, a verify run) commits and pushes only its own
  `worktree-<id>` branch and never merges into `main`.
- Never use `gh`. Git goes over SSH only.

## Tool routing

- Know the name: Serena. `find_symbol` with `include_body` only when you will read or edit the
  body, `depth=1` for a class; `get_symbols_overview` for a file you have not seen;
  `find_referencing_symbols` for callers.
- Know the text: `rtk rg -n`, starting with `-l` or `-c` and `--max` (`--max-len 160` for code),
  then switch to Serena at the hit. This holds for non-Python files too.
- Know the line: read about 40 lines around it (Claude: Read with `offset`/`limit`; Codex:
  `sed -n a,bp`).
- Markdown headings are symbols (`STATE.md` `## Now`, unit sections). In a worktree, pass
  absolute paths.
- Read a whole file only when it is a non-code file under 200 lines or 8 KB, or when most of it
  changes.
- Structured files: `jq` or `rtk read -m`.
- Confidential data (`data/`, `battery/results/`, `instance_descaled*`): shapes, keys, counts and
  aggregates only, never rows.
- Edits: Claude uses Edit, `replace_symbol_body`, `rename_symbol` and `replace_in_files` (dry run
  first). Codex uses `apply_patch` only, one multi-file patch per logical change, then
  `get_diagnostics_for_file`, then the tests.
- Batch independent reads: one message, or one exec with `Promise.allSettled`.
- Every shell command goes through rtk. The hook rewrites plain commands; write `rtk test`,
  `rtk rg --max`, `rtk read -m` and `rtk proxy` yourself where the hook cannot.

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
