---
date: 2026-10-12T23:32:43-0500
author: Nicolas Lee
commit: 5f14464
branch: m5-studio/national-overnight
repository: td-national-overnight
topic: "Main-map pipeline with joint WIFI footprint and K grid: extend the IFA support-master → draw → repair → merge → export path to national/WH/FI/WIFI"
tags: [research, codebase, main-map, WIFI, K-grid, dollars, gap-width, land-balance, contiguity, overnight]
status: ready
last_updated: 2026-10-12T23:32:43-0500
last_updated_by: Nicolas Lee
---

# Research: Main-map pipeline with joint WIFI footprint and K grid

## Research Question
From the discover FRD (`.rpiv/artifacts/discover/2026-10-12_23-21-17_main-map-joint-wifi-grid.md`), with the orientation brief read first. Priorities: (1) a joint whole-state WIFI footprint and channel K grid, including the current seed, and the complement/routing seam each footprint implies; (2) the four-channel seam in run.py/draw.py/repair.py/merge.py against IFA's state-sealed path; (3) per-district dollar rules in planning, repair and scoring, and what a dollar-triggered repair needs; (4) the two gap-width implementations, the thin-unit floor and #133, each tagged verified code / untested prototype / IFA-only policy. Read-only: no source edits, no solver runs.

## Invariant (first, always)
**Every district, in every channel and every grid point, is one connected piece of territory on the drawn map (M1), audited on the full 2025 polygon graph.** This holds for WIFI districts as much as any other, and above all for a single large WIFI district under the $1.6B allowance. Planning may run on an induced graph; the M1 verdict never does (`td/audit.py:800`, `check_m1`). Both gap-width verdicts are reported (G3).

## Summary
- **The footprint and K are TOML-only.** A channel's domain is a list of (units, fine channel) entries; `td/spec.py` refuses overlaps, gaps and any leftover state name, and checks the #67 national purity/fallback rule. No channel name (`WIFI` included) is special anywhere in `td/`, `score.py` or the contig tools.
- **The main map runs unsealed and needs no merge.** The six tier-P maps came from `tools/exp/contig/set125.sh`: spec copy → `replan.py` → `run.py` → `repair.py` → gate/score/render, all on the full polygon graph. IFA's `--states` sealing and `merge.py` exist only on branches and key on ZIP alone, which four coextensive channels break.
- **One `m_rel` band runs end to end** (master τ-normalised rows → draw rows → repair's `final_band` → the audit's `check_bands`). The scorer checks dollars only as a channel average. Repair never triggers on dollars. Because national mixes fine channels with different $/m_rel rates, tier-P districts sat inside the `m_rel` band but under the dollar floor.
- **IFA's dollar approach worked only because IFA has one fine channel** (one rate, so the E2 dollar window is one `m_rel` window, 798.74–1,148.19). The owner chose to generalise it: dollar-scaled masses (G5), per-channel dollar windows, a gate that checks every district, re-run on failure, no repair arm.
- **Gap width:** scouts' G1 prototype is tested on its branch, default off, counts water too; the #131 builder counts dry land only but has never run (no data file, stale test, old fork). Both change only the audit, never the draw.
- **Thin-unit floor (G2/#132):** a NY-only, single-channel IFA prototype in `coarse.py`, never made to work (NY K5 infeasible; dilution repair aborted). Manhattan is the open M1 failure of `ifa_conus_v2`.
- **#133 land balance:** no code. Step 1 of choosing R (measured on 9 existing ledgers, below) shows a natural gap between 8.4 and 12.1.
- **The session settled a 21-point grid** across five structures, totals 48–52, with an 8 h budget on m5 + m2 (m2 verified identical to m5).

## Detailed Findings

### 1. Spec, domains and routing (main, verified code)
- `ChannelSpec` fields: `k, delta, final_delta, eta, domain, modes, max_size, max_dist_km, dist_km, contact_caps, extra_supports, listed_only, forbid_pairs, margin` (`td/spec.py:101-122`); `dist_cap` at `td/spec.py:128-129`.
- `_channel()` (`td/spec.py:294-388`) refuses a duplicate cell (308-318), an empty domain (319-320), a mode/free on a unit outside the domain (324-331), an extra support outside the domain (339-343), `listed` without extras (344-349), and caps/dist on a unit outside the domain (360-366). So when the WIFI footprint moves, every `free`/`dist_km`/`contact_caps`/`extra_supports`/`confine` entry naming a moved state must be pruned in the TOML, or the spec fails to load.
- `check_partition` (`td/spec.py:391-408`): every (unit, fine) cell in exactly one channel. `check_national` (`td/spec.py:411-442`): a unit with national keeps its national fine channels in the national channel; a unit without it sends each to the channel holding its fallback (`national_chase`, `wells_fi` → fi; `wells_wh` → wh). A fallback is needed only when some unit lacks national (426-428). `sets["all"]` is every unit (`td/spec.py:203`).
- `build` → `assemble` (`td/spec.py:562-672`): per channel `m[z]` sums the domain's fine cells, `τ = ΣM/K`, `band` and `final_band` are τ(1±δ). τ moves with both footprint and K.
- Exact-once coverage, zero-opportunity territory included: `Run.fine`/`Run.route` (`td/audit.py:92,114-115`), built in `td/output.py:404-433`; ledger `NO_CELL`/`DROPPED` rows (`td/output.py:336-384`); footprint and territory ownership (`td/territory.py:34-35,119`).

### 2. The two seed layouts
- **`ne_plains` (the lead-map layout; all six tier-P maps):** `/Users/Shared/sv-ntlee/td/runs/exp/contig/wh_dollar/s13_WH11.toml` (hub, **gitignored, not tracked**). WIFI = 15 whole states (ME NH VT MA RI CT ID MT ND NE SD WY NM OK KS), all five fine channels, `mode = "whole"`, enumerated supports, `max_size` 9, δ 0.1 (lines 49-58). National K15 over 34 states (7-19); WH K11 (21-33); FI K20 (35-47); `[national]` fallback (60-64). `set125.sh:20-45` copies it and rewrites K and δ.
- **The tracked seed:** `scenarios/51_total_13n_11wh_24fi_3wifi.toml`. WIFI = 8 west states (`:17`) in three fixed listed blocks with δ 1.0 (`:76-83`), so its band is inert. National K13 with `free`, `dist_km`, CA contact cap 4, `extra_supports` NE+NY, `confine`, MS `forbid_pairs` (`:30-48`). No current map uses it.

### 3. Master and draw (main, verified code)
- Master `build` (`td/master.py:131-190`): count (151), cover (153), η/share (160-161), hold (163), **band (165-166, masses ÷ τ)**, η-cap (168), contact (172), corridor (177-179), border (183), count cap (186), ban (189); objective Σ diameter·n. Smallest δ: `exact_delta` (437), `bisect_delta` (514), dispatch `smallest_delta` (565).
- Supports: `td/supports.py:213-256` (`family`), corridor floors (318-348), margin (364), diameter (372).
- `replan.py:276-292` takes the smallest δ per channel and accepts it only if ≤ `final_delta`.
- `run.py`: plan cache (`:92-100`), `contig_run` on the full polygon graph (`:149-210`), fallback ladder `WIDER = (0.05, 0.10, 0.15)` (`:79`), `write_folder` (`:413`), `write_manifest` (`:489-523`).
- Draw (`tools/exp/contig/draw.py`): `SPLIT_WEIGHT=1000` (71), `NeckCut` (120), `border_km` reads only polygon borders (191), lo/hi = τ(1±δ) in `m_rel` (272), `_solve_group` (746), **per-district band row on aggregated `m[z]` (911-916)**, neck cuts (998), solve-check-cut loop (1120). This is where #133's land-balance term would sit, next to the border term.

### 4. Four-channel seam vs IFA's state-sealed path
- **Main (verified):** `run.py` and `repair.py` build on the full `geo.polygon_graph()` (`run.py:164-181`, `repair.py:1048-1050,1122`). No `--states`, no `--window`.
- **Branches (untested prototype):** `m5-studio/national-scouts-2026-10-08:tools/exp/contig/run.py:149-159` (`induced_graph`), `:177-197` (planning sealed, audit full); `repair.py:1038-1051,1130-1135` (sealed build, `--window` clips every channel's final band to one `m_rel` interval).
- **Merge (untested prototype; `merge_ledgers` unit-tested on its branch):** scouts `merge.py:58-94` refuses any ZIP seen in two sources (62-66) and proves cells unchanged (83-92); `merge_extracts` (96-110) refuses shared ZIPs; `merge()` (122-169) builds on the induced union, checks `placed == held` by ZIP, re-gates on the full graph. ifa-conus adds `merge_spec` (213-232), `--window`, `--gap-width`, `--export`.
- **Why it doesn't transfer:** IFA has one cell per ZIP, so ZIP disjointness equals cell disjointness. In the main map one ZIP has cells in three channels. Splitting sources by state seals cross-state districts the main map needs; splitting by channel is refused by the ZIP check. A main-map merge would need to key on (ZIP, fine channel) cells and check placement per channel. **Not needed for the overnight run**, which is unsealed like #125.

### 5. Dollars
- Scorer (`tools/looks/score.py`): `BAND`, `DOLLAR_BAND`, `MAIN_K` (87-89); `TARGET` and `DOLLARS` (92-94); `dollar_rates` (263-268, E1 as coded); `dollars_per_district` is a **channel average** (271-276); `bands_at` in `m_rel` (296-306); `eligibility` (328-348) skips channels with no `TARGET` (so WIFI is never checked); IFA special case `DOLLARS["ifa"]/k` (380-383).
- Policy (not code): D3/E1/E2/E3 in `docs/problem/PROBLEM.md:62` and `WATCHDOG.md:56-65`, scorer change pending #130. **This session changed two of them** (owner decisions below).
- IFA's adapter (`IFA-only policy`): `DOLLARS_PER_M_REL = 1.2519681558` and `BAND_M = (1000, 1437.5)` (scouts `merge.py:41-42`, ifa-conus `merge.py:59-60`); the E2 window as 798.74–1,148.19 `m_rel` in repair `--window` and `coarse.py --lo/--hi` (ifa-midatl `coarse.py:246-249`). Band failures were handled by re-running or waiver (PA `ea0e85e`, MD under F1).
- Repair triggers (main, verified): detached pieces (`repair.py:162-165`) and necks (`:571-578`); rounds in `repair_channel` (`:680-739`); `outside_band` is reported, never a trigger; the window band is `ch.final_band` (`:356`). No dollar term anywhere in the file.
- E1 rates from this extract ($M per `m_rel`): wh 1.2501, fi 1.2426, wells_wh 1.2400, wells_fi 1.1776, national_chase 1.2340, ifa 1.2520.
- Scouts' D3 audit of tier-P (`m5-studio/national-scouts-2026-10-08:checkpoints/national-2026-10-08/`, untested script): national 13/15, WH 10/11, FI 20/20, WIFI 3/3 in band. Failures: national_01 −$48.4M, national_09 −$39.7M (both under the old $1,062.5M floor, at national K15), WH_09 −$9.2M.

### 6. Gap width (two implementations; both untested prototypes on main's terms)
- Main baseline (verified): `NECK_W_KM`/`NECK_SHARE`/`NECK_W_CM` (`td/audit.py:444-449`), `border_cm` (452), `NeckGraph` (474), `land_would_do` (531), `district_necks` (565), `check_m1` (800). No gap flag.
- **Scouts G1:** `m5-studio/national-scouts-2026-10-08:td/audit.py:491` (`gap_width=False`), 507-516 (Voronoi-only same-state pairs set as neck edges; **water counts too**), 888 (`TD_NECK_GAP_WIDTH == "1"`); test `tests/test_neck_gapwidth.py` passes on that branch. Evidence: El Paso (79718–79734, 6.14 km) the only flip on IFA CONUS (`dff4eec`). Also on ifa-midatl and ifa-conus.
- **#131 builder:** `m5-studio/131:td/geo.py:1251-1377` (dry-land gaps minus water), `geo.py:930-950` (`polygon["gaps"]`), `td/audit.py:492,508-511` (default on, additive), 802/884 (opt out with `=0`). **No `zcta_gap_land.csv.gz` exists, so it is inert; its test is stale; it forks from `d06c593`, before the WIFI/E3 fix `1293d41`.**
- **Both change only the audit.** Draw and repair use `polygon["border"]` (`draw.py:191`, `repair.py:224-232,1122`), so a map can be re-audited under either without redrawing. Gap width can only relax M1, never make a pass fail.
- Water-gap precedent: Queens/Nassau flip was water, not covered by G3 (`b113a5d`, `85c78d6`).

### 7. Thin-unit floor and Manhattan (G2/#132)
- `m5-studio/ifa-midatl:tools/exp/contig/coarse.py`: NY-only paths (31-35), unit mapping (62-113), `thin_units` (115-135; connector-only skip in `9531a21`, **untested**), `partition` MILP with the thin row (138-227, 195-198), CLI (234-313). `tests/test_coarse.py` covers the partition's thin row, not `thin_units`.
- History: NY K5 by congressional units gave Manhattan and Queens/Nassau necks (`a61ad59`, `6a6867e`); the floor made K5/K4 infeasible (`05effe7`, `2ef5361`); dilution repair aborted, Queens closed by a 109-ZIP window (`1ff8b90`). `ifa_conus_v2` is tier 3, failing M1 on Manhattan alone (5.50 km default / 6.99 km gap width; `tools/shortlist/shortlist.json:1937-1948`).
- `thin_units` calls `NeckGraph(polygon)`, so it would silently follow whichever gap-width default lands.

### 8. Land balance (#133) — step 1 measured this session
Read-only calculation over 9 ledgers with `geo.polygon_graph()["aland"]` (script `/tmp/td-land/scripts/land.py`, output `/tmp/td-land/out/land.json`). A split group is one channel's districts inside one state. Reproduces #133's figures exactly on `ifa_conus_nony` (IL 54.4, MI 34.3, MN 239.2 whole-district).

| map | in-state land ratio (largest ÷ smallest) per split group |
|---|---|
| `ifa_conus_nony` | MN 62 · IL 54 · PA 36 · MI 34 · NJ 7.7 · FL 7.3 · OH 6.4 · WI 4.8 · CA 4.1 · TX 3.6 · NC 3.2 · KS 2.8 · MA 1.9 · TN 1.3 · CT 1.1 |
| `ifa_conus_v2` | as above plus NY 171 |
| `ne_plains_wh11` | national NY 870 (sliver) / 31 (≥20% pieces) · national CA 32 · FI NY 31 · FI PA 20.5 · WH PA 12.1 · FI TN 11.7 · national TX 8.4 · WH CA 4.8 · WH NJ 3.1 · FI NC 2.8 · FI CA 2.2 · FI OH 1.3 · FI FL 1.2 · national FL 1.1 |
| `finonc_whnonj` (other tier-P similar) | national NY 870 / 31 · FI NY 31 · national CA 30 · WH PA 26 / 5.7 · FI PA 15 · national TX 8.4 · FI TN 4.9 · WH CA 4.8 · FI CA 2.0 · FI OH 1.7 · FL 1.0–1.3 |

- **No split group in any of the 9 maps falls between 8.4 and 12.1.** Every metro-vs-rest case is above.
- Whole-district land misleads (MN 239 vs 62 in-state). The 870 is a 135 km² sliver at 16% of its district's mass; the ≥20%-of-mass filter removes it without changing any other case.
- At R = 10, about 4–5 of ~12–14 split groups per main map would have to change (NY national and FI, CA national, PA FI and sometimes WH).

### 9. Exports, tracking, shortlist
- Main (verified): ledger schema `td/output.py:80-82`; `check.py m1` (`tools/mandates/check.py:71-97`), T1 `tracking` (176-219); scorer ranking `rank_key` = (splits, defects, extent, states/district, worst dev, mean dev) (`score.py:419-437`) — cuts are not a rank key despite the prose; `render.py:47,104-155` (`render.json`, `current`); `tools/shortlist/build.py:37,96-129,185-187` (registry, `INDEX.md`).
- Branch (untested prototype, IFA-tuned tables): `m5-studio/ifa-conus:tools/exp/contig/export_long.py` (generic runner; `CANON` table and scenario-id convention IFA-shaped), `export_geojson.py:20` (`BUNDLE_TITLE` lacks `national`/`WIFI` keys). Merge `--export` is IFA-only.
- Renders read untracked caches under m5's `runs/` (`docs/CODE_MAP.md:85-91`), so rendering stays on m5.

### 10. Per-state opportunity dollars and the K arithmetic
From the extract × E1 rates (read-only; `/tmp/td-grid/scripts/state_usd.py`, output `/tmp/td-grid/out/state_usd.json`). On-map totals: national $17,535M, WH $11,141M, FI $20,233M, **$48,909M**. Checks: 8-state west $1,543M (tracked $1.54B), New England $2,303M (tracked $2.30B).

| footprint | WIFI $M | national $M | WH $M | FI $M |
|---|---|---|---|---|
| `ne_plains` (15 states) | 3,370 (NE 2,303 + plains 1,067) | 16,896 | 10,139 | 18,504 |
| 8-state west | 1,543 | 16,981 | 10,754 | 19,631 |
| national all 49 + WIFI | 31,374 | 17,535 | — | — |
| national 34 + WIFI | 32,013 | 16,896 | — | — |
| single WIFI | 48,909 | — | — | — |

Feasible K per channel = K with channel $ ÷ K inside the window; headroom = 2·min(avg−L, U−avg)/(U−L), minimum over channels (scripts `kgrid.py`, `kgrid2.py`, `filight.py` in `/tmp/td-grid/scripts/`). Under the final windows: `ne_plains` N 12–16, WH 9–11, FI 18–24, WIFI fixed 3 (New England can only be 2 whole-state districts, CT+RI $1,073M and MA+NH+VT+ME $1,230M; plains 1); 8-state west N 12–16, WH 10–12, FI 19–25, WIFI 1; national-all N 13–17, WIFI 28–36; national-34 N 12–16, WIFI 28–37; single WIFI 43–57. With national's old $1,062.5M floor, national stopped at 15 and every district above it had to come from FI; the $1,000M floor lets national take K16 and saves two FI districts at the same total.

## The locked 21-point grid
Settings for every point: dollar-scaled masses and per-channel dollar windows (B1); land balance in the draw at R = 10 (in-state land, pieces ≥ 20% of district mass); scouts gap-width audit with both verdicts; WH K ≥ 8; whole-state carve-out.

| structure | id | national | WH | FI | WIFI | total | avg $M N / WH / FI / WIFI | headroom |
|---|---|---|---|---|---|---|---|---|
| ne_plains | `ne-48-bal` | 14 | 10 | 21 | 3 | 48 | 1,207 / 1,014 / 881 / — | 0.86 |
| ne_plains | `ne-50-bal` | 15 | 10 | 22 | 3 | 50 | 1,126 / 1,014 / 841 | 0.56 |
| ne_plains | `ne-50-filight` | 16 | 11 | 20 | 3 | 50 | 1,056 / 922 / 925 | 0.26 |
| ne_plains | `ne-52-bal` | 15 | 11 | 23 | 3 | 52 | 1,126 / 922 / 805 | 0.29 |
| ne_plains | `ne-52-filight` | 16 | 11 | 22 | 3 | 52 | 1,056 / 922 / 841 | 0.26 |
| ne_plains | `ne-cmp-tierP` | 15 | 11 | 20 | 3 | 49 | 1,126 / 922 / 925 | comparison |
| west8 | `w8-48-bal` | 14 | 11 | 22 | 1 | 48 | 1,213 / 978 / 892 / 1,543 | 0.85 |
| west8 | `w8-50-bal` | 15 | 11 | 23 | 1 | 50 | 1,132 / 978 / 854 | 0.60 |
| west8 | `w8-50-filight` | 16 | 12 | 21 | 1 | 50 | 1,061 / 896 / 935 | 0.28 |
| west8 | `w8-52-bal` | 15 | 12 | 24 | 1 | 52 | 1,132 / 896 / 818 | 0.31 |
| west8 | `w8-52-filight` | 16 | 12 | 23 | 1 | 52 | 1,061 / 896 / 854 | 0.28 |
| west8 | `w8-cmp-seed` | 13 | 11 | 24 | 1 | 49 | 1,306 / 978 / 818 | comparison |
| national all 49 + WIFI | `nw49-48`, `-50`, `-52` | 15 / 16 / 17 | — | — | 33 / 34 / 35 | 48 / 50 / 52 | N 1,169 / 1,096 / 1,031; WIFI 951 / 923 / 896 | 0.67 / 0.44 / 0.14 ⚠ |
| national 34 + WIFI | `nw34-48`, `-50`, `-52` | 14 / 15 / 16 | — | — | 34 / 35 / 36 | 48 / 50 / 52 | N 1,207 / 1,126 / 1,056; WIFI 942 / 915 / 889 | 0.61 / 0.43 / 0.26 |
| single WIFI | `w1-48`, `-50`, `-52` | — | — | — | 48 / 50 / 52 | 48 / 50 / 52 | 1,019 / 978 / 941 | 0.87 / 0.85 / 0.60 |

Structure definitions:
- **ne_plains / west8 (four sub-channels):** national, WH, FI over the complement; WIFI holds all five fine channels in the footprint, whole states. west8's WIFI K1 at $1,543M uses the $1.6B whole-state allowance; the seed's listed blocks and δ 1.0 are replaced by one whole-state WIFI support.
- **national + WIFI (two sub-channels):** national holds the national fine channels of the states that have national (all 49, or the 34 non-`ne_plains` states); WIFI holds wh and fi everywhere plus the national cells of states without national (the #67 fallback). WIFI states may split.
- **single WIFI:** all five fine channels in one channel across the country (the original layout, the baseline).
- Names are working labels for planning; the `ne_plains` spec must be committed under `scenarios/` before any run.

## Budget and run discipline (settled)
- **Machines:** m5 (M5 Max, 18 cores, 64 GB) 12 processes × 1 thread; m2 (M2 Max, 12 cores, 32 GB) 8 × 1. One thread count per process (trap 18).
- **Window:** about 8 h overnight; launch after the gates below.
- **Stop/retry (option A):** plan 10 min per channel, infeasible → label **infeasible**, skip; draw 75 min, one retry at δ +0.05; repair pass 1, pass 2 only if M1 still fails, 30 min each, two `unknown` end it → **fails M1**; dollar-gate failure → one re-run with the next K for the failing channel → **ineligible ($)**; hard stop at 8 h → **stopped**, reason in the manifest. Retries key on the solver's own stop reason (trap 15).
- **Risk:** single WIFI and national + WIFI put 33–52 districts in one channel across the country, a much larger single draw than any #125 channel. No main-map timing exists; schedule them on m5.

## Output and morning view (settled)
- One folder per point: `runs/exp/main_overnight_2026-10-13/<id>/` with `draw/`, `r1/`, `r2/`; each with `ledger.csv`, `districts.csv`, `run.json`, `manifest.json` (spec sha, K, footprint, host, commit, extract sha), `scorecard.md` with the label, **`dollars.csv`** (every district vs its window; $1.6B allowance noted), **`land.csv`** (in-state ratio per split group vs R), M1 both verdicts plus flips, maps (`summary.png/.svg`, `zip_*`, `render.json`). m2 runs come back to m5 hash-checked; renders on m5.
- `GRID.json` lists all 21 points at launch and is updated as each finishes; a point with no label at the end is an error.
- `MORNING.md`: one table, eligible first by the settled ranking, then fails M1, ineligible ($), infeasible, stopped; columns id, structure, K, splits, defects, worst $ deviation, M1 both ways, land ratio, label, links; balanced/FI-light pairs side by side; a "Needs your eye" list (non-El-Paso flips, $1.6B allowances, districts beyond R).
- `MORNING.pdf`: one page per point, summary map with a one-line title, same order.
- Eligible points are added to `tools/shortlist/shortlist.json` with `check.py --tracking` and `INDEX.md` rebuilt.

## m2 readiness record (done this session)
- m2 hub fast-forwarded `a5862b3` → `617b42e`, clean.
- Extract copied from m5: sha `39e2b475…` on both; m2's old file kept as `instance_descaled_m2-2026-09-29.json.gz`. **It was first named `instance_descaled.json.gz.m2-2026-09-29`, which the ignore pattern missed, leaving an untracked file with per-rep shares in m2's hub for about 25 minutes; renamed, `git check-ignore` confirms `.gitignore:18`, and `git log --all` shows no commit ever touched it.**
- `data/public`: 165 files, combined hash `7e9784be…` on both (m2's differing state zip kept as `.m2bak`, ignored by `.gitignore:22`). `reference/2025` hash `fbb86190…` on both.
- Tests: 388 passed, 0 failed on both. A tier-P ledger gated and scored on both gives byte-identical output.
- Process cleanup on m2 at the owner's instruction (stale `pi` sessions, `anvil-test` Emacs daemon, emacsclient, node/tsx service, two shells); owner quit Safari, turned off iCloud Photos, restarted m2. After restart `mediaanalysisd` 1.67 GB → 213 MB, `corespotlightd` 1.05 GB → 628 MB; `photolibraryd` was still at ~84% CPU processing the Photos change.
- m5: owner switched off the aerial wallpaper (CPU 4.3% → 0%; 1.24 GB stays until logout/restart). m5 `pi` sessions left alone at the owner's request.

## Code References
- `td/spec.py:101-129` — ChannelSpec, dist_cap
- `td/spec.py:203` — the `all` set
- `td/spec.py:294-388` — channel parsing and refusals
- `td/spec.py:391-442` — partition and #67 national rule
- `td/spec.py:562-672` — build, scope, assemble (τ, bands)
- `td/master.py:131-190` — master rows; band 165-166
- `td/master.py:437,514,565` — exact/bisect/smallest δ
- `td/supports.py:213-256,318-372` — family, corridor, margin, diameter
- `tools/exp/contig/replan.py:276-292` — smallest δ per channel
- `tools/exp/contig/run.py:79,92-100,149-210,413,489-523` — WIDER, plan cache, contig_run, write_folder, manifest
- `tools/exp/contig/draw.py:71,120,191,272,746,911-916,998,1120` — draw MILP and band row
- `tools/exp/contig/repair.py:162-165,224-232,356,571-578,680-739,1122` — triggers, edge widths, window band, rounds, NeckGraph
- `tools/exp/contig/set125.sh:20-65` — main-map launcher template
- `td/audit.py:92,114-115,254,431,444-458,474,531,565,800` — run routing, bands, pieces, necks, M1
- `td/output.py:80-82,336-384,404-461` — ledger schema, ledger, audit_run, ledger_pieces
- `td/territory.py:34-35,119` — footprint, ownership
- `td/geo.py:917-932` — polygon_graph (aland for land balance)
- `tools/looks/score.py:87-94,263-276,296-348,380-383,419-437` — constants, rates, eligibility, IFA special case, ranking
- `tools/mandates/check.py:71-97,176-219` — M1 gate, T1 tracking
- `tools/shortlist/build.py:37,96-129` — registry, INDEX
- `tools/maps/render.py:47,104-155` — render.json, current
- `scenarios/51_total_13n_11wh_24fi_3wifi.toml:12,17,24-48,76-83` — tracked seed
- `scenarios/50_ifa.toml:10,17` — IFA single channel over `all`
- `m5-studio/national-scouts-2026-10-08:td/audit.py:491,507-516,888` — G1 prototype (chosen)
- `m5-studio/national-scouts-2026-10-08:tools/exp/contig/run.py:149-159`, `repair.py:1130-1135`, `merge.py:41-94` — sealing, window, merge
- `m5-studio/131:td/geo.py:930-950,1251-1377`, `td/audit.py:492,508-511,802,884` — gap-land builder
- `m5-studio/ifa-midatl:tools/exp/contig/coarse.py:115-227` — thin_units, partition
- `m5-studio/ifa-conus:tools/exp/contig/export_long.py`, `export_geojson.py:20`, `merge.py:142-173,213-232` — exports, dual audit, merge_spec
- `m5-studio/explore-research:docs/lenses/NATIONAL_PLAN_2026-10-08.md` §4–5 — G5 (dollar-scaled masses) and its build items

## Integration Points

### Inbound References
- `tools/exp/contig/set125.sh:22-65` — calls replan.py, run.py, repair.py, render/check/score; the template for the overnight launcher
- `tools/mandates/check.py:71` — calls `score.m1_check` on a run folder's ledger
- `tools/shortlist/build.py:116,163` — reads `render.json` M1 status for INDEX
- `td/output.py:425` — builds `Channel(k, *final_band)` for the audit; where a dollar window would enter the audit

### Outbound Dependencies
- `td/data.py:87,145` — `load` / `conus`: where G5's dollar scaling would apply at load
- `td/geo.py:917` — polygon graph (M1, borders, aland)
- `instance_descaled.json.gz` at the hub root (gitignored; sha `39e2b475…` on both Studios)
- HiGHS via scipy; traps 12, 14, 15, 18, 19

### Infrastructure Wiring
- `TD_NECK_GAP_WIDTH` env (prototype: `=1` on) read only in `check_m1`
- `runs/exp/<lane>/<run_id>/manifest.json` (T1); `runs/` gitignored, renders on m5
- `.gitignore:18,22` — extract and `data/public` patterns

## Architecture Insights
- **One mass vector feeds every stage.** Changing what a cell's mass means (G5: dollars instead of `m_rel`) moves master, draw, repair and audit together with no change to their band rows. That's why B1 is cheaper than a dollar repair arm, and it's exactly what IFA got for free from having one fine channel.
- **Channel identity lives in domains, not names.** Footprints, sub-channel counts and the single-WIFI baseline are all spec files; `check_partition` and `check_national` are the guards.
- **Audit-only knobs are cheap to swap.** Gap width touches `border_cm` only; maps re-audit without redrawing. Land balance is the opposite: a draw term, so every map changes.
- **Separate parts of a channel take whole districts.** `ne_plains` WIFI is two disconnected parts, which pins WIFI K at 3.
- **Ranking code vs prose:** cuts are named in the settled ranking but are not in `rank_key`.

## Precedents & Lessons
8 similar past changes analysed (precedent sweep over all branches).

### Precedent: IFA merge pipeline built in one day
**Commit(s)**: `ba7db96`, `08b61bd`, `f172d69`, `38bcd2d` (2026-10-08)
**Blast radius**: ~10 files each across tools/exp/contig, tests, runs
**Follow-up fixes**: `1ec1be7`, `5d5176a`, `4a6cb4f`, `a234f5d`, `002ee6a` (source-tag syntax churn); `20cfe36` (reverted an unaudited 0.1733 band choice)
**Takeaway**: merge's API changed six times in a day for one channel; the main map avoids merge by running unsealed.

### Precedent: WIFI exemption flip-flop
**Commit(s)**: `f6b7afe` → `c989cbf` → `1293d41` (2026-10-08)
**Follow-up fixes**: five same-day re-audits; scouts and #131 forks still carry the superseded text
**Takeaway**: re-audit every seed under current rules; trust no cached ELIGIBLE (tier-P's is stale).

### Precedent: G1 prototype → G3 → water-gap exclusion
**Commit(s)**: `d312834`, `46d2d89`, `dc02c87`
**Follow-up fixes**: `46d2d89` flipped the default and broke its own test; `b113a5d`/`85c78d6` narrowed G3 to coverage gaps
**Takeaway**: report both verdicts; send every non-El-Paso flip to the owner.

### Precedent: scoped draw/repair for IFA regions
**Commit(s)**: `c511443`, `c6dbb1b`, `1590309`
**Follow-up fixes**: `ea0e85e` (neck fix broke the band), `e53027b` (TX neck survives 1,443-ZIP windows), `1ff8b90` (aborted dilution)
**Takeaway**: windows don't always close hard necks; bound budgets.

### Precedent: thin-floor iterations ending untested
**Commit(s)**: `05effe7`, `2ef5361`, `63c4f22`, `9531a21`
**Takeaway**: don't build on `9531a21`; `--attach` (`4e223f1`) worked where the floor failed.

### Precedent: export schema churn
**Commit(s)**: `21d9cb4`, `ef5d761`, `cc90996`→`2946e41`
**Takeaway**: start from `export_long.py` + `scenarios.csv` + G4 ids; extend its tables for main-map channels.

### Precedent: set125.sh → six tier-P maps → stale ELIGIBLE
**Commit(s)**: `0d0f685` and `66bab5d`/`33b2368`/`a2a3867`/`bd9c2e0` (2026-10-07)
**Takeaway**: reuse the launcher shape, never its verdicts.

### Precedent: G5 national fresh-grid ruling
**Commit(s)**: `cf27d47` (on `m5-studio/explore-research` only)
**Takeaway**: dollar-scaled masses were already the owner's choice; its open Q5 (national only vs whole main map) is answered by this session: the whole main map.

### Composite Lessons
- Policy churn kills cached verdicts — re-gate everything under the session's new windows (`1293d41`, `20cfe36`).
- IFA single-channel mechanics don't transfer to coextensive channels (sealing, `m_rel` windows, hardcoded rates) — `ba7db96`, `1590309`.
- New gates land off by default until evidenced (`12d3631`), but each extension needed review-fix rounds (`9c819e8`, `9ff80a5`, `c1384bb`, `2aa8319`).

## Historical Context (from `.rpiv/artifacts/`)
- `.rpiv/artifacts/discover/2026-10-12_23-21-17_main-map-joint-wifi-grid.md` — the FRD this research answers
- `.rpiv/artifacts/orientation/2026-10-13-ifa-to-national.md` — IFA-to-national orientation brief (its #133 note is stale)
- `.rpiv/artifacts/orientation/2026-10-13-overnight-decisions.md` — overnight decisions log

## Developer Context
**Q (discover: Stakeholder intent): For main-map overnight work, what counts as success for you and stakeholders?**
A: "Stakeholder maps".

**Q (discover: Correct fixed-WIFI framing): Keep the gates, with this stage limited to framing?**
A: "Change frame" — "we need to think about how we handle WIFI. that piece will also vary, i.e. we will not just fix those midwestern states to be wifi but will also run the grid across other options".

**Q (discover: Joint grid and unchanged gates): Propose whole-state WIFI footprint and K options, including the current seed?**
A: "Propose joint grid (Recommended)".

**Q (discover: Assess latest enhancements, defer knobs): Assess dollar-triggered repair, both gap-width implementations, thin-unit floors and #133, deferring knobs?**
A: "Assess all, defer knobs (Recommended)".

**Q (`/Users/Shared/sv-ntlee/td/runs/exp/contig/wh_dollar/s13_WH11.toml:49-58` vs `scenarios/51_total_13n_11wh_24fi_3wifi.toml:17,76-83`): which layout is the current seed?**
A: Use both, and also include a run with only national and WIFI. Clarified: the original channel was WIFI, everything mixed; the exercise tests breaking it into 3–4 sub-channels (national, WH, FI, leftover WIFI) depending on whether a state has its own national, WH or FI. In the two-sub-channel case WH + FI are WIFI.

**Q (`td/spec.py:308-318,411-442`): carve-out per whole state or per sub-channel?**
A: Whole state (option A).

**Q: is the original single WIFI channel a grid point?**
A: Grid point.

**Q (`tools/looks/score.py:337-345`, `docs/problem/PROBLEM.md:62` E3): how are WIFI district dollars judged?**
A: Target $1B (±15%, $850–1,150M). A WIFI district made only of whole states may go up to $1.6B (A1 + A3); maps using it record it. WIFI states may be split (an earlier "no WIFI splits" rule was dropped because it breaks the national + WIFI structure). **Replaces E3 — owner decision for the lander to file in PROBLEM.md.**

**Q (gap width: scouts `td/audit.py:491-516,888` vs #131 `td/geo.py:1251-1377`): which implementation?**
A: First the scouts prototype ("the el-paso example is a great one, that is something we want to let pass"); reopened and settled on **C**: scouts prototype for the overnight run, re-audit with the #131 builder before any map reaches stakeholders, El Paso re-checked; non-El-Paso flips to the owner.

**Q (`repair.py:162-165,571-578`; how IFA did it): how are dollar violations handled?**
A: B1 only — dollar-scaled masses, per-channel dollar windows, a gate checking every district, re-run on failure, no repair arm.

**Q (`docs/problem/PROBLEM.md:63` G2; `shortlist.json:1937-1948`): Manhattan rule on the main map?**
A: C1 — no rule; M1 audit, then repair's neck windows, then the owner.

**Q (#133; `draw.py:746`): land balance on the main map?**
A: D3 — in the draw. Definition after the step-1 measurement: in-state land, pieces ≥ 20% of district mass, R = 10. Overnight runs R = 10 only; tightening later.

**Q: national's dollar floor.**
A: National may go down to $1,000M (window $1,000–1,437.5M). **Changes D3's national band — owner decision for the lander to file.**

**Q: grid.**
A: The 21-point grid above, totals 48–52 with balanced and FI-light pairs; WH K ≥ 8.

**Q: budget.**
A: m5 + m2 (explicit OK for solver jobs on m2, with m2 verified first); 8 h; m5 12 × 1, m2 8 × 1; stop/retry option A. Launch timing set by the pre-launch gates.

**Q: setup permissions.**
A: Explicit permission to copy the extract and data to m2 and set it up; process kills only on explicit instruction (m2 items killed as instructed; m5 sessions left alone).

## Related Research
- None yet for this topic.

## Open Questions
Carried from the FRD (verbatim), with status:
- "Exact whole-state WIFI footprint alternatives and channel K grid: research proposes; planning fixes launch grid." — **Resolved this session:** the 21-point grid above.
- "Which dollar-repair architecture/pilots, gap-width implementation and thin-unit/land-balance mechanisms apply to main maps: research/design decides with evidence." — **Resolved:** B1; gap width C; no Manhattan rule; land balance in the draw at R = 10.
- "#133 land-ratio bound or replacement balance measure: owner decision deferred; placeholder R=10 is not approval." — **Partly resolved:** R = 10 and the in-state ≥20% definition adopted for the overnight run; the tighter ladder (step 3 feasibility, step 4 owner look) remains.
- "Solver budget, jobs, overnight duration, pilot authorization and launch timing: deferred to planning." — **Resolved except launch time**, which follows the gates.

Still open:
- **Pre-launch gates (planning):** overnight code landed and pulled on both Studios; tests pass on both; a smoke draw from the same spec matches across m5 and m2 with peak memory per process measured (m2 drops to 6–7 processes if memory is tight); m2's `photolibraryd` settled; the `ne_plains` spec committed under `scenarios/`.
- **Build items before launch (design/plan):** dollar-scaled extract with manifest record and `export_long` reversal plus round-trip test (G5); per-district dollar gate in the scorer, WIFI $850–1,150M / $1.6B whole-state rule, national $1,000M floor (#130); the scouts gap-width prototype landed on main with its test; the #133 land term in `_solve_group` with `land.csv` reporting; `dollars.csv`; the grid launcher, `GRID.json`, `MORNING.md`/`.pdf`.
- **Before stakeholders:** build `zcta_gap_land.csv.gz`, rewrite the #131 test, rebase #131 onto main, re-audit presented maps, re-check El Paso.
- **Owner decisions to file (lander):** WIFI window and $1.6B whole-state allowance replacing E3; national floor $1,000M; #133 definition and R = 10 for the main map; G2 stays IFA-only.
- **Timing risk:** single-channel WIFI and national + WIFI draws (33–52 districts in one channel) have no main-map timing.
- #111 and #112 remain owner decisions; #119 (all-M1 bound) stays optional; no "minimal" claim.
