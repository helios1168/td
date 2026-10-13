---
date: 2026-10-13T14:44:04-0500
author: Nicolas Lee
commit: 95c0338
branch: m5-studio/national-overnight
repository: td-national-overnight
topic: "Main-map overnight grid results and the move to regional sealing Implementation Strategy"
tags: [implementation, strategy, main-map, overnight-grid, regional-sealing, merge, zip-pages, morning, M1, dollar-gate]
status: complete
last_updated: 2026-10-13T14:44:04-0500
last_updated_by: Nicolas Lee
type: implementation_strategy
---

# Handoff: overnight grid done; owner chose regional sealing for the main map

## Task(s)
1. **Plan + implement the overnight grid** (design `.rpiv/artifacts/designs/2026-10-13_01-09-34_main-map-overnight-grid.md`, plan `.rpiv/artifacts/plans/2026-10-13_04-04-35_main-map-overnight-grid.md`): **completed**. All 7 phases landed (`ba1e07c`..`6acac19`) plus overnight fixes (below). Grid ran 04:47–12:48 on m5 + m2, collected 12:52, final MORNING built.
2. **Overnight results**: **completed**. 20 of 21 settled points have *no plan inside their dollar windows* (master's smallest feasible δ > the window-fitted δ). 17 `-wide` siblings (δ floored to the master's smallest feasible, planner decision while owner slept, recorded in GRID.json assumptions) were drawn: all **fail M1**. Best map: `ne-48-bal/r2` (the one in-window point): 0 pieces, **1 neck** (national_08, Delaware Memorial Bridge 08023, 5.67 km), all 48 districts in window; GRID relabelled from "stopped" (stop hit during its last score step; old GRID kept as `GRID.before_relabel.json`).
3. **Contiguity fixes tried**: repair pass 3 with `--open-units` (killed: every window infeasible) and the #124 C support-ban loop (`plancheck.py`, IFA round-3 DE+NJ-without-PA bans + proved-infeasible supports): **completed, failed**: bans moved pieces, never cleared them (w1-50-wide got worse: 4 pieces/8 necks). Abandoned.
4. **Renderer changes** (owner requests): ZIP pages default with a state summary page first + metro labels (**merged**, `070f4d0`); MORNING.pdf carries every point's full ZIP pages (**merged**, `a46fe3f`); MORNING index pages (K, channel structure, targets, avg/min/max $ with deviation; **merged**, `95c0338`). Census region/division zoom pages: **built, NOT reviewed or merged**, branch `m5-studio/zip-census-views` @ `1662a7d` (flag `--views`, default off; test PNGs in `/tmp/td-zip-region-test/`).
5. **Regional sealing quick test** on w1-50-wide: **completed**, branch `m5-studio/regional-seal` (`cd180a5`, `0da6044`, pushed, not merged). Sealing cleared DC, New England and the Delaware bridge; NYC still has 1 piece + 1 neck. **Owner decision (2026-10-13 ~14:40): go with regional sealing for the main map.** Next work = extend it (planned, not started).

## Critical References
- `docs/problem/MANDATES.md`, `AGENTS.md` (M1 first; masking; only owner merges to main; traps 12/15/18/19).
- `docs/RESULTS.md` IFA #126 rounds 2–3 (~lines 1125–1200) and the IFA CONUS regional merges on `origin/m5-studio/ifa-conus` (`merge.py`, `runs/exp/contig/_specs/ifa_conus_merge.toml`) and `origin/m5-studio/ifa-ny` (`ifa_ny_k5_window.toml`, Queens/Nassau 109-ZIP window).
- The design + plan artifacts above (dollar windows, D1–D15).

## Recent changes
- `tools/exp/contig/overnight.py`: `_load` under `_LOAD_LOCK` (thread race made every point "error", `54f5afa`); `plan_point(..., floor)` + point `delta_floor` (`584b051`); `WIDE_MAX`, `wide_floor`, `_chain` replans a `-wide` point until it plans (`4e38abf`); `map_png`/`map_pages` (`a46fe3f`); `index_rows`/`index_md`/`index_pages`/`page_size` (`95c0338`).
- `tools/maps/summary.py`: WIFI-only run caption fallback (`e729723`).
- `tools/maps/zip_pages.py`: state summary page (`zip_summary.png`), CBSA metro labels (`070f4d0`).
- Tests: `tests/test_overnight.py`, `tests/test_maps.py`. Full suite 436 passed, 0 failed (m5, 95c0338).
- On `m5-studio/regional-seal`: `tools/exp/contig/merge.py` ported from ifa-conus (+ "states=national folder" source, `--rate`, relative extract path in run.json), `run.py`/`repair.py --states` (land term on the state-induced graph).

## Learnings
- **Root cause of the main-map pieces**: the unsealed support master pairs states whose drawn shares never touch (it doesn't know where in a split state the share lands; the draw puts it at the metro). Recurring spots: NYC (NY-only district with an upstate body + Manhattan sliver, 10001/10002; necks 11414-11420, 10016-10017, 11377), DC (DC+DE+MD+NJ/PA: DC island, 20001), New England (ME+NH+NY+VT / CT+…+RI+VT with an NYC share: 03031, 02802), Delaware Memorial Bridge (DE+NJ without PA: 08023-08069/08070 5.67 km). IFA hit the same and solved them only by regional sealing; Manhattan stayed open even there (ifa_conus_v2 tier 3).
- **Sealing vs not on w1-50-wide** (comparison image `/Users/Shared/sv-ntlee/td/runs/exp/regional_2026-10-13/compare_northeast.png`): gap-width M1 2 pieces/2 necks → 1/1 (NYC only); sealed-area districts outside $ window 6/15 → 0/15; whole map 16 → 10 (all in the unsealed part); defects 10.7 → 6.3; cost: split states 11 → 13 (MD, VA), multistate districts 16 → 18, land ratios worse (NY 753, VA 278, MD 64). Main benefit for CONUS: per-region K/δ fits the dollar window, which the national plan cannot.
- Regional details from the test: NJ alone has no K with τ in window → NJ+PA (K 5); DC+DE+MD+VA needs a DE–VA forbid pair; `margin = false` in region specs (as IFA) or NY's master is infeasible; NY+NJ K 7 hung HiGHS ~2 h past its limit (add a hard wall-clock kill); region scorecards show τ fractions ~10x too small (national mass / regional K): judge on the merged gate.
- Within-state necks that sealing does not touch (seen in other points): Cincinnati/KY 41011-45202, Utah 84621, El Paso 79718-79734, LA/SF, NJ 08505-08611.
- `-wide` points use δ up to 0.33, so 13–22 districts land outside windows; they are diagnostics, not deliverables.
- Infra: crontab/launchd not permitted for the sandbox user; background jobs used `setsid` + a 5-min watchdog loop (`~/overnight/wdloop.sh`) + `caffeinate`. m2 work goes through `ssh m2` (owner granted full m2 use for this run); m2 checkout: `~/.pi/worktrees/td-national-overnight` (detached at origin branch).
- Renders of $M runs need `--fac <grid>/fac_usd.json` and `TD_NECK_GAP_WIDTH=1`; render on m5 (m2 lacks `data/public/tl_2025_us_zcta520.zip` in the worktree path).

## Artifacts
- Plan: `.rpiv/artifacts/plans/2026-10-13_04-04-35_main-map-overnight-grid.md` (status ready; Step 4 review table inside). Design: `.rpiv/artifacts/designs/2026-10-13_01-09-34_main-map-overnight-grid.md`.
- Grid (m5, gitignored): `/Users/Shared/sv-ntlee/td/runs/exp/main_overnight_2026-10-13/` — `GRID.json`, `MORNING.md`, `MORNING.pdf` (88 pages: 5 index + maps), `<point>/<stage>/` with ledger, `zip_pages.pdf`, `zip_summary.png`, `score.txt`, `dollars.csv`, `m1.json`, `land.csv`; ban-loop folders `<point>/pc/`, `<point>/pcb/`; first attempt set aside as `main_overnight_2026-10-13.attempt1_0446`.
- Regional test (m5): `/Users/Shared/sv-ntlee/td/runs/exp/regional_2026-10-13/` — regions `ctri/draw`, `mannev/draw`, `ny5/r2`, `njpa/r1b`, `mdva2/r1`, `pa/draw`; specs `_specs/`; merged map `merged/` (zip_pages.pdf); `compare_northeast.png`.
- Published results: branch `m5-studio/overnight-results` @ `4702e14` (`results/main_overnight_2026-10-13/`), https://github.com/helios1168/td/tree/m5-studio/overnight-results/results/main_overnight_2026-10-13
- Branches pushed: `m5-studio/national-overnight` @ `95c0338`, `m5-studio/regional-seal`, `m5-studio/overnight-results`. Local only: `m5-studio/zip-census-views` @ `1662a7d` (unreviewed), `m5-studio/zip-summary-page`, `m5-studio/morning-index` (both merged).
- Driver/scripts (m5 `~/overnight/`): `driver.sh`, `wdloop.sh`, `watchdog.sh`, `plancheck_c.sh`, `plancheck_b.sh`, `mk_ban_spec.py`, `relabel_stopped.py`, `new_pages_sweep.py`; logs there. Grid driver finished (`all.done`); nothing of this work is running.

## Action Items & Next Steps
1. **Design the CONUS regional-sealing main map** (owner approved sealing). Suggested route: `/skill:design` (or a quick design note) covering: region partition for each channel structure (start with ne_plains, our best structure; IFA used New England, NY, NJ, PA, South Atlantic, South Central, Midwest, West), per-region K so τ lies in each channel's dollar window and totals stay at 48–52, δ via `overnight.fit_delta`, forbid pairs (DE–VA, DE+NJ without PA), `margin = false`, a hard wall-clock kill per draw, merge + full-graph gate (G3 and strict).
2. **NYC step** (needed either way): port IFA's Queens/Nassau window (`origin/m5-studio/ifa-ny` `ifa_ny_k5_window.toml`) and/or a rule that no upstate NY district takes a Manhattan piece; Manhattan was open in IFA too.
3. **Head-to-head test**: seal CONUS for ne_plains K 48 and compare against unsealed `ne-48-bal/r2` (0 pieces, 1 neck, all in window).
4. Optional quick win: fix `ne-48-bal`'s single bridge neck (seal NJ+PA for national, or the DE+NJ-without-PA ban on national) → possibly the first fully passing main map.
5. Review `m5-studio/zip-census-views` (`/tmp/td-zip-region-test/` PNGs) and merge if good; owner asked for region/division zoom pages.
6. Housekeeping: record results in `docs/RESULTS.md` (doc owners: `.claude/doc-owners.txt`) and `STATE.md`; open an owner-decision issue for the dollar windows (20/21 infeasible), WIFI window/$1.6B/national floor (owner decisions still to file in PROBLEM.md per design), R = 10 (#133), and the `-wide` assumption.

## Other Notes
- Never merge to `main` (owner only). Work on `m5-studio/<topic>` branches via worktrees (`/wt <topic>`); background work via non-blocking subagents in worktrees (owner preference: never block the main chat).
- Owner preferences this session: maps rendered with the new ZIP-pages layout (summary page first, metro labels), MORNING.pdf with index + full maps, GitHub links for sharing.
- Masking: dollar extract `$TD_REPO/instance_descaled_usd.json.gz` (sha256 98cc87bc8ba5…) carries rep shares; gitignored; never publish it. `$TD_PY=/Users/Shared/sv-ntlee/td/.venv/bin/python3`, `TD_REPO=/Users/Shared/sv-ntlee/td`.
- `origin` is HTTPS though AGENTS.md says SSH; pushes worked.
- A claude-bridge "prompt-capture" error appeared once mid-session (system prompt changed after `tool_search` loaded tools); a fresh session fixes it.
- Other sessions run `ifa/kgrid` solves on m5; not ours.
