# National channel territory design — Claude Code setup

**State:** `STATE.md` — read `## Now`, then `## Next`. History: `git log --grep '^State:' -p --
STATE.md`. This file carries invariants only and is never stamped.

## Start-up protocol

1. `STATE.md` `## Now` then `## Next` is the resume point. The SessionStart hook
   (`~/.claude/hooks/td-session-start.sh`) prints them plus the derived track list and the local
   `PLAN.md ## Next step` on every session start; nothing else is required to resume.
2. `docs/CODE_MAP.md` for files and recipes; `docs/PROBLEM.md` / `docs/MODEL.md` for the problem
   and the model.
2a. If the task is "what does this scenario do" — pin a region, change k, swap the engine — run
   it in the Streamlit app (`tools/app.sh`, `docs/APP.md`) instead of building a Claude
   artifact. Artifacts are for fixed, reviewed deliverables; a scenario question needs an
   engine behind it, and the app has one.
3. Never read `docs/foundations/archive/`, or a whole `docs/*.md` unprompted — take the
   section you need via Serena (headings are symbols).

## Environment

- `.venv/bin/python3` from the repo root `/Users/ntlee/projects/td` — the system python has no
  numpy/scipy/networkx. A `wt/*` worktree has no `.venv`; use the repo root's.
- The Streamlit scenario app has its own venv, `.venv-app`, built from `app/requirements.txt`.
  Never install into `.venv` for the app: those pins are frozen and the zip50 anchor depends on
  them. The app never imports `td`; it drives the drivers by subprocess (`docs/APP.md`).
- MacTeX at `/Library/TeX/texbin`, **not** on `PATH` in non-interactive shells: prefix
  `export PATH=/Library/TeX/texbin:$PATH` when building a note.
- Never write under `battery/figures/`. `figures/` **is tracked** (a map is a primary artifact):
  regenerate with `tools/us_maps.py` and commit alongside the change.
- `data/`, `battery/results/` and `instance_descaled*.json.gz` (confidential) are gitignored;
  `docs/CODE_MAP.md` lists what a worktree must hand-copy.
- Serena binds to the session's launch directory; activate by *path* before the first symbol
  edit. Background solver runs with `python3 -u`.

## Tests

`.venv/bin/python3 tests/run_all.py` — 331 fast tests, 0 fail (2026-09-07). `TD_SLOW=1` adds
nothing: no module sets `SLOW = True`. `tests/test_engines.py` is the self-contained two-player
smoke test.

## Docs discipline

One owner per file, listed in `.claude/doc-owners.txt`; `docs/foundations/` is read-only and
never edited. A track's running log is its worktree `PLAN.md` (`## Goal`, `## Next step`,
`## Done`, `## Decisions needed`, `## Files owned / forbidden`), committed on the branch and
deleted in the last commit before merge. The permanent record of a unit is `docs/units/<id>.md`,
carrying a `Status:` line and `## Model`, `## Verify`, `## Code verify` sections. Verifier
artifacts are committed under `tools/verify/<id>/`; they are never test-discovered. Bugs and
small todos live in code as a `TODO` at the site (the runner has no `xfail`), never in `## Next`.
History: `git log --grep '^State:' -p -- STATE.md`.

## Worktrees

Create with `git worktree add .claude/worktrees/<name> -b worktree-<name>` then
`git worktree lock --reason "keep" .claude/worktrees/<name>`, never `EnterWorktree(name)`; enter
an existing one by path. A worktree has no `.venv`; use the hub's. Serena must be given absolute
worktree paths (relative paths resolve against the hub and can write to the user's checkout,
trap 16 below). Merges into `main` are fast-forward and asked for first; after merge, unlock,
remove, and delete the branch.

## Subagents

Noisy work (inventories, grep sweeps, verifier runs) goes to a subagent; only the verdict returns
to the main context.

## Traps that still apply

2. **Equalisation can destroy value.** Never replace the Nash objective with an explicit
   balance minimisation — Nash-as-balance is the point (`docs/PROBLEM.md` §1).
4. **Fairness alone is degenerate** — every rep with no book at `z` values `z` identically.
12. `scipy.optimize.milp` defaults `mip_rel_gap` to 1e-4; pass `mip_rel_gap=0.0` for a certificate.
13. **Separator cuts must be component-wise** — one root per district per component, or the
    dual bound is unsound.
14. HiGHS 1.15 "Solve error" under 1e-9 tolerances; SCIP needs `misc/allow{strong,weak}dualreds`
    off for any lazily separated model, `ga ≤ Σu·x` not `==`, and a gain lower bound from the
    incumbent. scipy 1.18.1's `linprog(method="highs")` hangs on v2 — `centers.assign()` pins
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

**Two-tier acceptance:** tier 1 `CERT_TOL = 1e-8`; tier 2 `base.EPS_CERT = 5e-3` nats, grounded
on a measured data-noise floor (re-measure on the real instance). The full trap list is in git
history: `git show contiguity-harness:CLAUDE.md`.
