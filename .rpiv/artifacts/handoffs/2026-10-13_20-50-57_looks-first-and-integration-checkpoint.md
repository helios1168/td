---
date: 2026-10-13T20:50:57-0500
author: Nicolas Lee
commit: 1239ee2
branch: m5-studio/national-overnight
repository: td-national-overnight
topic: "Looks-first reframing, quick tests T1/T5 done, checkpoint toward main Implementation Strategy"
tags: [implementation, strategy, main-map, ifa, looks, compactness, hub-rule, regional-sealing, carve-first, integration, exec-render, looks-study]
status: complete
last_updated: 2026-10-13T20:50:57-0500
last_updated_by: Nicolas Lee
type: implementation_strategy
---

# Handoff: looks-first reframing; T1 and T5 done; T2–T4 and the main integration wait on owner answers

Continues `.rpiv/artifacts/handoffs/2026-10-13_14-44-04_overnight-grid-to-regional-sealing.md` (overnight grid, sealing test). Read that one first for the grid, the best maps and the run folders.

## Task(s)
1. **Research on options** (completed, committed): what IFA's "constraint C" was and what IFA actually used (`.rpiv/artifacts/research/2026-10-13_ifa-split-state-constraints.md`); the 2026-10-07 hypergraph framing and every alternative in the lenses (`.rpiv/artifacts/research/2026-10-13_hypergraph-framing-and-alternatives.md`). Conclusion given to the owner: carve-first is the structural fix for cross-state pieces by construction, not for Manhattan or shape; sealing is the cheap partial; #124 A/B/C and pair bans are dead ends.
2. **Problem reframing** (discussed, NOT yet written into PROBLEM.md): owner (2026-10-13 evening) said **looks and compactness matter most**; executives see the map as laypeople; the canonical reference is the US Census regions map; the metro-core-vs-rural-ring split is indefensible to reps; fairness = opportunity AND effort (travel); the owner proposed forcing splits THROUGH the dense metro core. Agreed framing: looks criteria L1–L6 (state-line borders, simple cuts, blob/no bite, no arms, nesting in Census divisions, every piece has a hub with oversized hubs cut into wedges), an effort band, balance after looks. Five owner questions still open (band hard with a growing free list? definition of compact? certificate or incumbent? Manhattan ruling for the main map? rule C status?).
3. **Quick tests**: T1 looks/effort study **done** and merged (`tools/looks/study.py`, 3c1bd25); T5 executive render style **done** and merged (`--style exec` in `tools/maps/zip_pages.py`, 1239ee2). T2 (support shape filter on ne_plains K 48), T3 (NY K 5 hub rule), T4 (Census-division sealing of ne_plains K 48) **not started**, waiting on the owner's verdicts below.
4. **Checkpoint toward main** (assessed, not started): branch survey done, plan written in chat (below). Owner has not yet answered the two decisions (strip kgrid's committed run outputs; start an integration branch).
5. MORNING.pdf now carries full ZIP pages per point (a46fe3f) and 5 index pages (95c0338); results published on `m5-studio/overnight-results` @ ec89e14.

## Critical References
- `docs/problem/MANDATES.md` (M1 incl. necks and G1/G3), `docs/problem/PROBLEM.md` (band D2/D3/E1–E3, F1, G2, Looks-first row), `WATCHDOG.md`.
- `docs/lenses/review-2026-10-07/METHOD-carve-first.md` (on origin/m5-studio/explore-hypergraph; exported at /tmp/td-lenses/ on m5) and `docs/lenses/RESEARCH_FRAMING_2026-10-07.md` §1.7–1.8.
- The two research notes in `.rpiv/artifacts/research/` dated 2026-10-13.

## Recent changes (all on m5-studio/national-overnight, pushed)
- `tools/exp/contig/overnight.py`: `map_pages` (every channel's zip page into MORNING.pdf), `index_rows`/`index_md`/`index_pages`/`page_size` (index pages first; WIFI target = window midpoint, stated in the legend).
- `tools/looks/study.py` (new, 520 lines): per-district hull_fill, bite (+bite_states), longest_axis, aspect, cut proxy (cut_edges, cut_counties), land_km2, land_per_usd, wmean_dist_km, r90_km, doughnut tests (core_without_ring / ring_without_core, hard ≥50%/<30%; soft ≥15% at 4x ratio), hub and hub_share; Census regions/divisions as reference pseudo-ledgers. Test `tests/test_looks_study.py`. CODE_MAP rows added.
- `tools/maps/zip_pages.py`: `--style exec` writes `zip_exec_<channel>.png` (dissolved districts, gap fill, 9-colour greedy palette, id·$ labels, metro names, legend) and inserts them in zip_pages.pdf after the summary page; default output unchanged. Test in `tests/test_maps.py`.
- Suite: 441 passed, 0 failed (m5, 1239ee2).

## Learnings
- **T1 numbers** (`runs/exp/looks_study_2026-10-13/SUMMARY.md`, published): Census divisions max bite 0.21, min hull_fill 0.52, 3 hard doughnuts (metros cut by state lines), land/$ spread 51x. Real maps: max bite 0.29–0.61, min hull_fill 0.24–0.48, 3–15 doughnuts, land/$ 200x–6,800x. Worst shapes are Mid-Atlantic/Ohio valley (ne-48-bal N-08 DC+DE+MD+NJ bite 0.41 with PA in hull; N-11 IN+KY+MI+TN+VA 0.40). The Lake Michigan district (ne-52-filight-wide national_11) scores bite 0.18, inside the Census range: a hull metric alone does not catch it; needs states-per-district or span cap. ne-48-bal doughnuts: NYC core-without-ring (FI_16, national_12), St. Louis ring-without-core (FI_09, WH_08), Philadelphia ring-without-core (national_08). No `ifa_kgrid` ledgers were found under runs/exp/contig on m5 (they are on the kgrid branch's committed tree, not in the hub clone's working tree); IFA set was ifa_conus_v1/v2/nony + ifa49-arm1-seq(+repair-fast).
- **T5**: exec style's gap fill assigns no-ZCTA land by longest border, leaving wrong-coloured patches in NV/UT; WIFI 50-district page crowded in the NE. Both pending fixes.
- **#124 "C"** = replan_rounds + ban_supports (fires only on proved-infeasible windows; never fired); IFA's map came from regional sealing + hand predicate bans (#126 r3: DE+NJ-without-PA 65 supports, NM-without-TX 16) + UT free; coarse.py (congressional coarsening) drew NY K 5; Queens/Nassau closed by a 109-ZIP window; Manhattan an owner-accepted exception at every K.
- **Branch survey (checkpoint)**: main @ 617b42e (10-08), STATE.md dated 10-07 (stale). national-overnight: 23 commits from main, clean. ifa-kgrid @ 4b5c99a: branched 1d56c62 (10-07), 25 behind main but merges onto main cleanly; 174 MB of run outputs force-committed under runs/exp/contig (gitignored path) + results/ifa_kgrid_2026-10-13 bundle (K48–54 all "eligible with Manhattan neck and MD F1 excepted"). kgrid ↔ national conflicts: only td/audit.py, tests/test_neck_gapwidth.py, tools/exp/contig/export_long.py, tools/exp/contig/run.py (gap-width ported twice; --states vs --land-ratio). National's three are supersets; regional-seal already carries --states/merge.py/repair.py on top of national (merge.py differs from kgrid by 33 lines, deliberate: states=national-folder source, --rate, relative extract path). coarse.py + tests/test_coarse.py + rulec_enum.py exist only on ifa-ny / ifa-midwest / ifa-midatl tips (not on kgrid). m5-studio/131 is a WIP gap-width default (td/geo.py gaps, stale tests). The 37 IFA region specs live in gitignored runs/exp/contig/_specs/ (survive only via kgrid's force-add). Overnight maps never entered the shortlist registry (T1 mandate). 20 worktrees on m5.
- Subagent routing: owner wants no Fable 5.1 subagents; use Sonnet 5.5 high (`model: "claude-bridge/claude-sonnet-5-5", thinking: "high"`) for tool-heavy work, Muse Spark (artifacts-analyzer) for read-only summaries. Verify with `rg -o '"model":"[^"]+"'` on the task output file.

## Artifacts
- Research: `.rpiv/artifacts/research/2026-10-13_ifa-split-state-constraints.md`, `.rpiv/artifacts/research/2026-10-13_hypergraph-framing-and-alternatives.md` (committed be4010b, 6adcc59).
- Looks study outputs (m5, gitignored): `/Users/Shared/sv-ntlee/td/runs/exp/looks_study_2026-10-13/{SUMMARY.md,maps.csv,districts.csv,fig_hull_vs_bite.png,fig_map_extremes.png,fig_doughnuts.png}`; published https://github.com/helios1168/td/tree/m5-studio/overnight-results/results/looks_study_2026-10-13
- Exec renders: `/tmp/td-exec-render/{ne-48-bal-r2,regional-merged}/zip_exec_*.png` (m5, temp); published https://github.com/helios1168/td/tree/m5-studio/overnight-results/results/exec_render_2026-10-13
- MORNING: `/Users/Shared/sv-ntlee/td/runs/exp/main_overnight_2026-10-13/MORNING.pdf` (88 pages); published results/main_overnight_2026-10-13 on m5-studio/overnight-results.
- Sealing comparison image: `/Users/Shared/sv-ntlee/td/runs/exp/regional_2026-10-13/compare_northeast.png`.
- Branches: m5-studio/national-overnight @ 1239ee2 (pushed), m5-studio/overnight-results @ ec89e14 (pushed), m5-studio/regional-seal @ 0da6044 (pushed, not merged), local merged: looks-study 3c1bd25, exec-render 475c888, morning-index, zip-summary-page; local unreviewed: m5-studio/zip-census-views @ 1662a7d.
- Lenses export: /tmp/td-lenses/docs/lenses/ (from origin/m5-studio/explore-hypergraph).

## Action Items & Next Steps
1. **Get the owner's answers** (asked, pending): (a) which districts in SUMMARY.md's worst-bite table are unacceptable → bite/hull_fill thresholds; (b) is a metro cut at a state line (Census-style doughnut) acceptable → scope of the hub rule; (c) effort band: a land/$ spread to defend, or measure only; (d) strip the 174 MB run outputs from kgrid's history (recommended) or merge as-is; (e) start `m5-studio/integrate`; plus the five problem-statement questions (band hard with growing free list; definition of compact; certificate vs incumbent; Manhattan ruling for the main map; rule C status).
2. **Write the new PROBLEM.md row** once (1) is answered: looks ahead of balance, L1–L6 as proposals with thresholds marked pending calibration, effort band, Manhattan ruling. File one issue with the pilot comparison table as acceptance.
3. **T2** support-family shape filter on ne_plains K 48 (score supports by state-grain hull fill/bite + states-per-district/span cap, drop bad ones, re-plan, draw, compare to ne-48-bal/r2). ~2 h solver.
4. **T3** NY K 5 hub rule: on the IFA K 5 setup (origin/m5-studio/ifa-ny: `ifa_ny_k5_window.toml`, coarse.py), window row "each piece holds ≥ 1/4 of the NYC core m_rel or an upstate hub (CBSA core)"; pass = Long Island + north wedge from Manhattan + three upstate hub-and-ring, no neck. ~3 h.
5. **T4** Census-division sealing of ne_plains K 48 with T2/T3 devices, overnight; compare on the T1 table.
6. **Integration branch** (after (d)/(e)): from main, merge national-overnight, regional-seal, then kgrid code+results with the 4 files resolved (take national's audit.py/test_neck_gapwidth/export_long; regional-seal's run.py/merge.py/repair.py); add coarse.py+test from ifa-ny tip and rulec_enum from midwest; move region specs to `scenarios/regions/<map>/`; STATE.md, RESULTS.md rows for both lines, CODE_MAP, doc owners, shortlist entries for the overnight maps; delete merged branches, prune worktrees. ~1 day. Then generalise overnight.py to IFA (channel + E2 window), add the IFA row to score.py's WINDOWS/TARGET, one results-publish command; retire kgrid.sh. ~1 day.
7. Exec-style fixes: gap fill by enclosing district; WIFI label crowding. Review/merge zip-census-views.

## Other Notes
- Never merge to main; owner only. Subagents commit on their own branches, no push; review before merging into national-overnight. No Fable 5.1 subagents.
- Masking: $ per district and m_rel fine; never rep shares, sales, rep/firm names; `instance_descaled_usd.json.gz` is gitignored and never published.
- Env: `export TD_REPO=/Users/Shared/sv-ntlee/td`; `$TD_REPO/.venv/bin/python3`; renders need `--fac $TD_REPO/runs/exp/main_overnight_2026-10-13/fac_usd.json` and `TD_NECK_GAP_WIDTH=1`.
- Nothing is running on m5 or m2 from this work. Other sessions' ifa/kgrid processes on m5 are not ours.
- Subagent output files live under /var/folders/rv/.../pi-subagents-601/.../tasks/<id>.output; a subagent in an isolated worktree writes to a temp path under /private/var/folders/.../pi-agent-<id>/, so artifacts it "wrote to .rpiv" must be copied out (recover from the write tool-call in the output JSONL).
