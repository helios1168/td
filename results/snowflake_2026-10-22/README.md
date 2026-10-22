# Stakeholder package, 2026-10-22: Snowflake dataset and map pages

Thirteen scenarios, six WIFI-family (main) maps and seven IFA maps. Owner signed off on the PDFs and dataset on 2026-10-22.

## Files

| File | What |
|---|---|
| `all_scenarios_nationwide_zcta_long.csv.gz` | 1,232,100 rows, one per (scenario, ZCTA, fine channel), 12 columns |
| `all_scenarios_districts.csv` | 654 rows, one per (scenario, district): name, states, planned and drawn $M |
| `load.sql` | `CREATE TABLE IF NOT EXISTS`, `PUT`/`COPY`, row-count check (`ssdb_integration.lr_strategy`) |
| [`../main_snowflake_2026-10-22/WIFI_6_pages.pdf`](https://github.com/helios1168/td/blob/m5-studio/ifa-snowflake-upload/results/main_snowflake_2026-10-22/WIFI_6_pages.pdf) | the six WIFI maps, 25 pages; per-scenario files in `../main_snowflake_2026-10-22/pages/<scenario>/` |
| [`IFA_K48-K54_pages.pdf`](https://github.com/helios1168/td/blob/m5-studio/ifa-pages-all/results/ifa_pages_2026-10-17/IFA_K48-K54_pages.pdf) | the seven IFA maps, 14 pages (branch `m5-studio/ifa-pages-all`, titles `IFA <K> districts`) |

## Scenarios

Name: `<FAMILY>_K<total>_<CH><k>...`, channels in order N, WH, FI, WIFI, empty ones left out; IFA is `IFA_K<k>`. No internal map id appears in a name or on a page. A name shared by two maps gets a suffix on the later one.

| Scenario | Map (internal id) | Source run folder (`runs/exp/`, gitignored, m5) |
|---|---|---|
| `WIFI_K48_N14_WH10_FI21_WIFI3` | ne-48-bal | `national_2026-10-14/warm/ne-48-bal/merged` |
| `WIFI_K48_N14_WH10_FI21_WIFI3_R2` | ne-48-bal-r2 (the only fully exact draw) | `sealed_2026-10-14/main_unsealed/ne-48-bal-r2` |
| `WIFI_K49_N15_WH11_FI20_WIFI3` | ne-cmp-tierP | `national_2026-10-14/warm/ne-cmp-tierP/merged` |
| `WIFI_K50_N16_WH11_FI20_WIFI3` | ne-50-filight | `national_2026-10-14/warm/ne-50-filight/merged` |
| `WIFI_K50_N15_WIFI35` | nw34-50 | `national_2026-10-14/grid2/warm/nw34-50/merged` (run on m2, copied to m5) |
| `WIFI_K52_WIFI52` | w1-52 after the WIFI_24 balance move | `national_2026-10-15_p3/w1-52-bal/merged` |
| `IFA_K48` ... `IFA_K54` | IFA K48-K54 | `sealed_2026-10-14/ifa/K<k>` |

Gate status of each map: `runs/exp/national_2026-10-14/REGATE_2026-10-15.md` and `INDEX.md`. `WIFI_K52_WIFI52` passes M1 only under the owner's Manhattan exception (#140); the pages do not say so.

## Regenerate

```bash
export TD_REPO=/Users/Shared/sv-ntlee/td
"$TD_REPO/.venv/bin/python3" tools/export/snowflake.py data   results/snowflake_<date>    # dataset, ~10 s
"$TD_REPO/.venv/bin/python3" tools/export/snowflake.py render results/snowflake_<date>    # pages + WIFI_pages.pdf, IFA_pages.pdf, ~3 min
```

The scenario list lives in `SCENARIOS` at the top of `tools/export/snowflake.py`; add a map there. Checked 2026-10-22: `data` reproduces this folder's two data files byte for byte. `render` titles IFA pages `IFA_K48 · IFA: 48 districts`, not the shipped `IFA 48 districts`.

## Column notes

- `zip_code`, county and place codes load as `VARCHAR` (leading zeros).
- `district` ids are per scenario: join on (`scenario`, `district`).
- `m_rel` is $M (usd extract); `has_commercial_opportunity` is `m_rel > 0`; `rep` is `None` everywhere (no staffing, OD3).
- 33,300 CONUS ZCTAs per scenario; the archived export had 33,791 (with AK, HI, PR as `Unserved`).
- Schema source: `archive/pre-support-2026-09:exports/database/all_scenarios_nationwide_zcta_long.csv.gz`.
