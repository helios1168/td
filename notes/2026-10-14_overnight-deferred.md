2026-10-14 · main · 53fdf9f · Agent: supervisor (claude-opus-5-5)

# Deferred from the 2026-10-14 overnight (pick up later)

Each item: what, where it stands, why deferred.

## Code awaiting review or landing
- **Sealed driver** `tools/exp/contig/sealed.py`, `glue.py` on `m5-studio/sealed` (4963113, pushed). build-review ended max-rounds; open concerns: strict rejection also fires on a `fixed_split` aggregate status (code-R1), resume guards for interrupted repair/glue/combine, reserved artifact names, combined-folder manifest tracking (T1). Tonight ran the older snapshot 43ca971 (branch `m5-studio/night-run`).
- **Looks study v2** on `m5-studio/study-v2` (168d51f, pushed): land-only hull_fill, no-cross-water bite (owner-approved #138), water_wrap, arm_share, roughness. Recovered after a worker timeout; not reviewed. Bite denominator moved to the land hull (worker's call; keep or revert).
- **Looks explainer PDF** on `m5-studio/looks-explainer` (f879791): review ended max-rounds with wording concerns (effort proxies are not trip lengths; Census reference rows disclosure). Its examples now come only from shortlisted maps.
- **IFA night helpers** on `m5-studio/ifa-night` (5e151f5): kgrid_night.sh, region_night.sh, sa_merge_night.sh, state_extract.py, SA specs. Run scripts, not reviewed.
- **region_arith** landed (1873080); remaining review concerns: qualify win/forced-top results by window and fit_delta restrictions.
- **M1 gate** landed (53fdf9f); follow-ups: `td/output.py` ledger_pieces does not use audit.adjacency (piece counts in run.json/districts.csv ignore R5; harmless while R5 is inactive; protected path); merge.py G3 sentence says "gate-default verdict" (should say strict).
- `m5-studio/zip-census-views` (1662a7d): zoomed Census region/division pages; never reviewed.

## Owner decisions still open
- PROBLEM.md M1 row: proposed wording in `notes/2026-10-14_m1-water-empty-land-proposal.md` (owner-owned file, not edited).
- Dollar windows (#130): national $1,000M floor, WIFI $850-1,150M and $1.6B whole-state allowance relied on tonight under delegation.
- Glue donor rule (#140 comment): failing donors may donate if no failure grows; confirm or tighten.
- Shape limits (#135, #138): the calibration fit (74 labelled districts) found no rule that generalises; candidate next measure: cut sinuosity (cut-line length over endpoint distance). Fit data: runs/exp/looks_calibration_2026-10-14/fit.md (keys key_sheet1.csv, key_sheet2.csv).
- #136, #137, #139, #141 untouched tonight.

## Method findings to act on
- **Symmetric band per region** (τ(1±δ), δ from fit_delta) is the binding limit for sealed main maps: regions whose components or blocks have different $ density fail even when every district could sit in the dollar window. Options: plan against the absolute window [L, U] in the master (asymmetric band), or carve-first (selection over pre-checked columns, where the window is a column filter). This is the main input for the carve-first track.
- Sealing ne_plains removes the corridor states the unsealed plan used as fillers; the east block cannot then be planned in band.
- Coupled NY-corridor draws need long time limits (337 s/channel timed out; 6,000 s cap used later).
- Missing-land R5 needs reference/2025/zcta_gap_land.csv.gz (python -m td geo --gap-land; needs ~3,000 TIGER FACES files, none on disk). Owner: defer.

## Housekeeping
- Stale worktrees under ~/.pi/worktrees (td-sealed, td-m1-water, td-region-arith, td-study-v2, td-ifa-night, td-night-run, td-calib, td-looks-explainer) and branches `cal`, `m5-studio/calibration-sheet`: remove after the owner's morning review.
- Heartbeat schedule `td-night-heartbeat3`: delete when the night closes.

## Added 2026-10-14 evening
- `m5-studio/window-band` (8a22136): reviewed clean in two build-review runs; land after the owner's look (touches td/master.py, approved on #112).
- `m5-studio/warm-start` (53dac30): warm.py/balance.py, not reviewed.
- sealed.py score stage: pass `--extract` (the full dollar extract) to score.py; merged_extract overstates FI ~2%.
- NY pieces after warm repair: ne-50-bal, ne-52-filight (FI_19), ne-52-bal (FI_18, FI_07), nw49-48/52 (WIFI, 9 ZIPs): bigger NY repair windows.
