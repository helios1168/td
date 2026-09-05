# National channel territory design — Claude Code setup

**State:** `STATE.md` — read `## Now`, then `## Next`. History is `docs/STATE_LOG.md`; read it
only when a question needs it. This file carries invariants only and is never stamped.

## Start-up protocol

1. `STATE.md` `## Now` and `## Next` (Serena `find_symbol`, or one Read). Nothing else is
   required to resume.
2. `docs/CODE_MAP.md` when you need a file or a recipe; `docs/CHANNEL.md` / `docs/MODEL.md` for
   the problem and the model; `STATE.md` `## Where` for the rest.
3. Never read `docs/STATE_LOG.md`, `docs/archive/`, or a whole `docs/*.md` unprompted — take the
   section you need via Serena (headings are symbols).

## Environment

- `.venv/bin/python3` from the repo root `/Users/ntlee/projects/td` — the system python has no
  numpy/scipy/networkx. A `wt/*` worktree has no `.venv`; use the repo root's.
- MacTeX at `/Library/TeX/texbin`, **not** on `PATH` in non-interactive shells: prefix
  `export PATH=/Library/TeX/texbin:$PATH` when building a note.
- Never write under `battery/figures/`. `figures/` **is tracked** (a map is a primary artifact):
  regenerate with `tools/us_maps.py` and commit alongside the change.
- `data/`, `battery/results/` and `instance_descaled*.json.gz` (confidential) are gitignored;
  `docs/CODE_MAP.md` lists what a worktree must hand-copy.
- Serena binds to the session's launch directory; activate by *path* before the first symbol
  edit. Background solver runs with `python3 -u`.

## Tests

`.venv/bin/python3 tests/run_all.py` — 222 fast tests, 0 fail (2026-09-05). `TD_SLOW=1` adds the
slow anchor tier. `tests/test_engines.py` is the self-contained two-player smoke test.

## Traps that still apply

2. **Equalisation can destroy value.** Never replace the Nash objective with an explicit
   balance minimisation — Nash-as-balance is the point (`docs/CHANNEL.md`).
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

**Two-tier acceptance:** tier 1 `CERT_TOL = 1e-8`; tier 2 `base.EPS_CERT = 5e-3` nats, grounded
on a measured data-noise floor (re-measure on the real instance). The full trap list is in git
history: `git show contiguity-harness:CLAUDE.md`.
