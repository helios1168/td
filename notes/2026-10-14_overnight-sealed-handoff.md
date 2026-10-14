2026-10-14 · main · 53fdf9f · Agent: supervisor (claude-opus-5-5)

# Handoff: the 2026-10-14 autonomous overnight (sealed main map, IFA grid, M1 water rule)

The owner delegated every decision for the night (#105, comment of 2026-10-14). Morning package: `runs/exp/sealed_2026-10-14/MORNING.md` (gitignored, m5), renders in `maps/`, running log `STATUS.md`.

## Tasks
- IFA K48-54 passing grid: **done**. All seven pass (M1 fails only on Manhattan, the owner's one exception; every district in $1,000-1,437.5M). South Atlantic redrawn with MD shared. Code on `m5-studio/ifa-night` (5e151f5, pushed, not landed).
- Main map, 15 grid points (ne_plains x6, nw49 x3, nw34 x3, w1 x3; west8 dropped): **partial**. 1 of 15 has a passing map: ne-48-bal, the unsealed 2026-10-13 r2 re-judged under tonight's gate (0 pieces, 0 necks, 48/48 in window, 8 split states). The sealed attempts produced none.
- M1 water/empty-land rule (#140): **landed** on main (53fdf9f).
- Regional arithmetic and partition search: **landed** (1873080, `tools/exp/region_arith.py`).
- Shape calibration: **done, negative**. 80 owner verdicts (2 sheets); no rule generalises (best 8/74 errors, 6-9 held out). Data in `runs/exp/looks_calibration_2026-10-14/`.
- Review workflow `build-review.js` (worker, audit, code + scope review, fixes, verifier): **landed** in sv-ntlee (a2bd1ce).

## Critical references
- `runs/exp/sealed_2026-10-14/MORNING.md` and `STATUS.md` (m5).
- `notes/2026-10-14_overnight-deferred.md`: every unlanded branch, open owner decision and cleanup item.
- `notes/2026-10-14_carve-first-lite-handoff.md`: the parallel track this night's findings feed.

## Changes
- `td/audit.py`: R1 connectors unlimited width; R2 gap width default on; R3 zero-opportunity ZCTAs widen passages; R5 land-only gaps join pieces (inactive: no gap file, owner deferred).
- `tools/exp/contig/merge.py`: its two comparison audits pin the gap-width switch.
- `tools/looks/score.py`: m1_both compares detached pieces too.
- `tools/exp/region_arith.py`, `tests/test_region_arith.py`: new.
- `tools/exp/contig/coarse.py:255`: default spec path in scenarios/regions/ifa (afe055e).

## Learnings
- One symmetric band per region, τ(1±δ) with δ from the dollar window, is the binding limit. A region whose connected blocks differ in $ density has no plan even when every district could sit inside the window (ne_plains WH west block ~$900M/district against a band of [918, 1150]). Splitting regions into components fixed some cases; the east block (21 states, national K6) still had no plan.
- Sealing ne_plains removes the corridor states the unsealed plan used as fillers.
- Corridor and big-WIFI draws at tight bands need far longer than a night allows (337 s/channel timed out; 6,000 s caps still left 15-16k ZCTAs undrawn at ±2%).
- `--drawable-alone` was not the cause of infeasibility (tested off: still none).
- Async subagent runs default to a 1-hour limit: pass timeoutMs and commit early; two workers timed out and were recovered from their captured patches.
- Fresh reviewers re-ask settled rulings; record rulings on the issue so the record answers them.

## Next steps
1. Owner reviews MORNING.md and the 8 passing maps (`maps/`), flags districts by eye (`shape/FLAGS.md` lists candidates).
2. Decide the band formulation: plan against the absolute dollar window (asymmetric band per district) in the master, or move the main map to carve-first (window as a column filter).
3. Land or close the branches in the deferred list after review.
4. Approve the M1 row wording for PROBLEM.md (`notes/2026-10-14_m1-water-empty-land-proposal.md`).

## Open owner decisions
- PROBLEM.md M1 row (above).
- Dollar windows relied on tonight (#130).
- Glue donor rule (#140): failing donors may give zero-opportunity ZCTAs if no failure grows.
- Shape limits (#135, #138): calibration showed no generalising threshold; candidate next measure: cut sinuosity.
- Band formulation (new): asymmetric window in the master vs carve-first.
