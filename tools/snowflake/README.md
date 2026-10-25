# `tools/snowflake/`: a safe copy of the live sales table

How to make a synthetic copy of the live sales table that can leave work, so SQL can be
written and tested against it outside work. Nothing here holds data; the salt and the filler
keys are typed at work and never saved.

| file | what it does |
|---|---|
| `00_profile.sql` | counts and shapes of `raw` (no names, no amounts), enough to generate a synthetic table outside work; also send `DESCRIBE TABLE raw` |
| `01_build_safe.sql` | builds `scratch.td_safe` from `raw(zip_code, firm, wholesaler, channel, opportunity, sales)` |
| `02_check_and_export.sql` | the checks that must pass, then the unload to `td_safe.csv.gz` |
| `03_rank.sql` | ranks wholesalers on one merged-company scale by sales / expected sales; needs `raw`, `channel_map(firm, source_channel, channel)` and `filler_keys` in the session |
| `04_territory_profile.sql` | counts and firm-level ratios of `territory` against `raw`, safe to bring back: coverage, orphans, share of sales in own / other / no territory |
| `05_rank_territory.sql` | ranks against assigned territories; out-of-territory sales credited (`out_credit`, default 1), with a territory-only index beside it; needs `territory(firm, wholesaler, zip_code, channel)` too |
| `07_rank_wholesalers.sql` | the ranking on `opportunity_sales` (original and target channel on each row) and `territory` in original channels; market rate per channel, each cell's opportunity split among its holders |
| `08_rank_end_to_end.sql` | the whole run on the owner's two tables: one mapping block to edit, a checks grid, then `07`'s ranking |
| `09_channel_match_diagnostic.sql` | after `08` Part 0: territory channel values beside sales `DIST_CH` values per firm, to find why territory rows have no mapping |
| `10_rank_sanity.sql` | after `08` is kept as `ssdb_integration.lr_strategy.wholesaler_rank`: median index by firm and channels held, a fairness check on the real data |
| `11_rank_diagnostic.sql` | when `10` shows a jump between channels-held groups: who has no sales at all, and how each original channel spreads over target channels |
| `12_rank_by_dist_company.sql` | the ranking straight from the two source tables, opportunity brought to each territory's (zip, firm, DIST_CH) through the distribution company; replaces `08`'s expansion to whole target channels |
| `13_product_profile.sql` | per product: share of opportunity and of each firm's sales, and which firm's rows carry its opportunity; the input to controlling for product sets |
| `14_rank_by_product.sql` | the ranking controlled for product only, straight from the two source tables: each firm charged for its own products, rate per channel x product over held opportunity; territories expanded to target channels as in `08` |
| `15_territories_enriched.sql` | the territories table with opportunity and sales appended, one row per territories row, in the source tables' own column names: each SOURCE's own PRODUCT_V2 set; the carrier SOURCE's MM_OPP exact by DIST_CH, the other SOURCE's by CHANNEL divided over its held DIST_CH by sales mix (calibrated with `17`) |
| `16_split_exposure.sql` | how many (zip, target channel) cells have several DIST_CHs held by several people: where the split rule in `15` reaches individuals |
| `17_split_rule_calibration.sql` | tests rules for dividing CHANNEL-level MM_OPP among DIST_CH values on the carrier SOURCE, whose per-DIST_CH MM_OPP is known: per-person error of each rule |
| `18_worked_example.sql` | walks chosen territories rows (a ZIP_CODE, wholesalers from either SOURCE, or both) step by step through `15`: opportunity by product, the DIST_CH split, OPPORTUNITY_SHARE, sales; output has real names and amounts, keep it at work |
| `19_structure_profile.sql` | the structure of the two source tables for a synthetic copy, safe to bring back as one CSV: column shapes, row grain, DIST_CH -> CHANNEL, products, where MM_OPP sits, people and holders, geography, FIRM and PARENT; SOURCE as firm_1/firm_2, DIST_CH and PRODUCT_V2 as codes, amount distributions divided by their median |
| `20_synthetic_tables.sql` | `synthetic_union` and `synthetic_territories`: coded copies of both source tables (the real rows, every name, ID, DIST_CH, product, FIRM, PARENT and CBD_ID coded, amounts divided by a median cell), same columns, so 15-19 run on them; `synthetic_key` maps codes back and stays at work; checks that must be 0 before download |
| `21_name_match.sql` | `NAME_MATCH`: a crosswalk from the union's territory-wholesaler names to the territories names, one row per SOURCE x name, matched by the ZIP_CODE x DIST_CH each name covers (name similarity as a check); checks; the review list; real names, keep at work |
| `22_code_opp_firm2.sql` | `synthetic_opp_original`, `synthetic_opp_matched`, `synthetic_crd_cbd`: coded copies of firm_2's opportunity file, its first-attempt match and the CRD-to-CBD_ID table, with the key of `20` extended insert-only (backup first; never re-run `20` statement 1); BROKER_NAME, FIRM_CRD and ZIP_CODE stay clear; OPP divided by the MM_OPP divisor; checks that must be 0 before download; the key stays at work |
| `23_crd_match.sql` | `OPP_MAPPED` (firm_2's opportunity file with the `DIST_CH`, product and `ZIP_CODE` maps applied and the reason a row is dropped) and `CRD_MATCH`: one row per `FIRM_CRD`, its `CBD_ID` by equality with `firm_1`'s `MM_OPP`, then `opp_matched` and `crd_cbd`; checks; the review list; every map in codes through `synthetic_key`, so it runs on real values |
| `24_union_opp.sql` | `UNION_OPP`: the union in firm_1's layout with firm_2's opportunity: `MM_OPP` joined onto the one firm_2 sales row per `ZIP_CODE` x `DIST_CH` x `CBD_ID` x `PRODUCT_V2` where the seller is the holder, else a new opp-only row (`CBD_ID` from `CRD_MATCH`, `NEW_DIST` / `CHANNEL` from the company or a `DIST_CH` default, holder from territories); `ROW_ORIGIN` and lineage columns at the end; checks; file `MM_OPP` beside `firm_2` sales by `DIST_CH` x `NEW_DIST` x `CHANNEL`; run after `23` |
| `DATASET_LOG.md` | the one tracking file: naming conventions, every `DEF_` definition, settled decisions, open questions, dated log |
| `30_cell.sql` | `CELL`: one row per ZIP_CODE x CBD_ID x CHANNEL x PRODUCT_V2 with MM_OPP, each firm's sales and the `DEF_` columns; checks; definition counts |
| `synth.py` | writes a synthetic `raw`, `channel_map`, `territory` and answer key to `data/safe/` from the profile's shape (no live data); `--check` runs `03`-`05` on it in DuckDB |

Run both in one Snowsight worksheet session (the filler-key table is temporary). Edit the
source table name and fill in the salt and the filler keys first. Copy the file to
`data/safe/` in the hub; it is gitignored.

## What survives, what does not

| kept | replaced |
|---|---|
| ZIP codes (public) and channel names | firm and wholesaler ids: `FX…` / `WX…`, ranked by a salted hash, not by book |
| the row count and the rows per (zip, channel) | each row's firm and wholesaler: shuffled across rows, so no territory survives |
| which values are NULL, 0, negative or positive | every number: opportunity is one random lognormal per cell, sales a random part of it |
| vacancy rows, as wholesaler `VACANT` | the filler keys' names |

A cell's sales sum to less than 0.9 of its opportunity, so share and headroom logic sees
sensible values. The shuffle can put one wholesaler twice in a cell; check 4 counts those rows.
If the source splits a cell's opportunity over several rows, each part gets the whole made-up
value.

## Why not Snowflake's own tools

- `SNOWFLAKE.DATA_PRIVACY.GENERATE_SYNTHETIC_DATA` copies categorical strings through: "a
  string column with few unique values … Generated data uses actual values from the source
  data" ([docs](https://docs.snowflake.com/en/user-guide/synthetic-data), read 2026-10-18).
  Firm and wholesaler are categorical, so real names would leave. It also works row by row,
  so one opportunity per cell and sales within opportunity do not hold.
- Masking policies hide values per role at query time: hashes or `***` instead of usable
  numbers, over a table that is still real.
