# docs/archive — superseded documents

Nothing here is load-bearing. Each file is kept because a live document cites it by name;
read the successor instead. Serena ignores this directory (`.serena/project.yml`
`ignored_paths`), so nothing in it surfaces in symbol search.

| file | what it was | superseded by | moved |
|---|---|---|---|
| `TEST_PLAN.md` | harness spec for the two-player merger programme ("plan only; no code written"); cites `OPTIONS.md` / `raw/*.md`, which never existed here | `tests/run_all.py` and the tier notes in `CLAUDE.md` | 2026-09-05 |
| `RESULTS.md` | empirical record of `scip_tree` on the pre-`td/` contiguity harness (`battery/results/contiguity/`) | `docs/RUNS.md` (v2 catalogue), `docs/MODEL_U8-band.md` (the live solver's numbers) | 2026-09-05 |
| `RESEARCH_GUIDE.md` | the 2026-09-01 overnight literature brief | discharged by `docs/RESEARCH_FINDINGS.md` and `docs/LIT_*.md` | 2026-09-05 |
| `hub-2026-09-02/BRIEF.md` | the hub's neutral stage-4 brief (units U0–U7) | `docs/BRIEF.md` — the A1 track's brief, promoted to the hub | 2026-09-05 |
| `hub-2026-09-02/DOMAIN_optimization.md` | the hub's neutral optimisation plan (§2.1 rep-indexed MINLP) | `docs/DOMAIN_optimization.md` — A1's re-run: §2.1 retired to a contingency, §2.10–§2.15 new, D1′ replaces the τ-homotopy | 2026-09-05 |
| `hub-2026-09-02/DOMAIN_economic-theory.md` | the hub's neutral economic-theory plan | `docs/DOMAIN_economic-theory.md` — A1's re-run: §2.8–§2.10 new; D3 re-issued, D5 split, D6, D7 | 2026-09-05 |
| `hub-2026-09-02/LENS_GROMOV.md` | the hub's 2026-09-02 Gromov lens | `docs/LENS_GROMOV.md` — A1's re-run: Moves 8/11/12/13; `EG^bal_S(δ)` replaces `EG_S`; ledger U13–U19 | 2026-09-05 |

**Why the A1 copies were promoted.** The A1 track (`docs/APPROACHES.md` §A1) re-ran stages
2–4 on 2026-09-03 with the instance measured, was merged into the hub on 2026-09-05, and its
versions explicitly supersede the neutral ones. Until 2026-09-05 they lived under
`docs/tracks/A1/` so the hub copies stayed neutral for other tracks; the user decided on
2026-09-05 to promote them, because the duplicate basenames made the docs ambiguous to
Serena's markdown index. The ask-before-merging rule still applies to future tracks: a new
track's lens / domain / brief go under `docs/tracks/<ID>/` until it wins or dies. The six A1
unit briefs (`U8-band` … `U13-base`) moved to `docs/units/` at the same time; they were written
with `docs/` paths, so nothing inside them needed rewriting. The 2026-09-03 wording "on this
branch only" in the promoted files' headers is historical.
