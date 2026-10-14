# main_unsealed: 2026-10-13 overnight main maps re-judged under the 2026-10-14 M1 water/empty-land rule

Gate: this worktree (`m5-studio/night-run`, `af57c22`), `tools/mandates/check.py` and
`tools/looks/score.py --dollars-csv --m1-json` with default switches (TD_NECK_GAP_WIDTH and
TD_NECK_PRE_2026_10_14_LAND_RULE unset). Render: `tools/maps/zip_pages.py` default style,
`--fac main_overnight_2026-10-13/fac_usd.json`. Sources copied, never modified.

| map | label | M1 detail | split states | worst $ deviation | pages |
|---|---|---|---|---|---|
| ne-48-bal-r2 (K 48: FI 21, WH 10, WIFI 3, national 14) | **passes** | M1 pass: 0 districts in pieces, 0 detached pieces, 0 necks, 0 unowned, 0 no-row, 0 double. 48/48 districts inside their windows (WIFI_03 $1,231M on the whole-state allowance). Manhattan exception not needed. Was `fails M1` (1 neck) on 2026-10-13. | 8 distinct: CA FL NC NJ NY OH PA TX (FI: CA FL NC NY OH PA; WH: CA NJ; national: CA FL NY TX; WIFI none) | 16.85% (national); FI 12.4%, WH 12.1%, WIFI 9.6% | [zip_pages.pdf](ne-48-bal-r2/zip_pages.pdf), [zip_summary.png](ne-48-bal-r2/zip_summary.png), zip_FI/WH/WIFI/national.png in the same folder |

6 mass necks are listed beside M1 (diagnostic, fail nothing): FI_16 and national_12 (10017, NYC), WH_04 (90067), WH_05 (20006), WH_08 (60606), WH_10 (10036).

## Decisions

- Only `ne-48-bal` has a final stage with every district inside its window. Every other point with a
  final folder (all `-wide`) has 6 to 21 districts outside their windows; the rest of the grid
  is infeasible or stopped with no ledger. Nothing else copied; the `-wide` points were skipped per the brief and would fail the window anyway.
- `score.txt` still says `eligible: no` with `audit: M1 polygon contiguity fails`: that line is read from the
  copied `scorecard.md`, written at draw time under the old rule (1 neck). The M1 line in the same file
  (and `m1.json`) is the new-rule verdict, pass. `scorecard.md` was not regenerated.
- `check.py` rc 0 (M1 pass); `score.py` rc 0.
