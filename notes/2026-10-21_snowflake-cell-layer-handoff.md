2026-10-21 · m5-studio/snowflake-safe-dataset · ce32304 · Agent: session (claude-opus-5-5)

# Handoff: merger wholesaler analytics, coded extract explored, `CELL` layer built

Work lives in the worktree `~/.pi/worktrees/td-snowflake`, all under `tools/snowflake/`. Owner runs the
SQL in Snowflake at work; every query is tested first in DuckDB here. Goal now: map opportunity
(`MM_OPP`) and sales cleanly to territories, then rank wholesalers within each firm and across firms by
contribution to firm sales, to firm channel sales, and by market share.

## Tasks

- Done: `15_territories_enriched.sql` keeps every territories row x target `CHANNEL` (owner reverted the lean filter).
- Done: `18_worked_example.sql` walks a chosen ZIP_CODE or wholesalers (either `SOURCE`) through `15`.
- Done: `19_structure_profile.sql` (safe profile, adds S10 `FIRM`/`PARENT`) and `20_synthetic_tables.sql` (coded copies `synthetic_union`, `synthetic_territories`, key `synthetic_key` stays at work).
- Done: coded extract received and loaded; explored; findings in `DATASET_LOG.md`.
- Done: naming conventions agreed; `DATASET_LOG.md` is the one tracking file; `30_cell.sql` built and tested.
- Not started: `31_cell_person.sql` (people on cells), blocked on Q3, Q9, Q10, Q15.
- Not started: `40_person_rank.sql` (the three rankings).
- Parked by owner: personal Snowflake account; GitHub release transfer; fully synthetic generator.

## Critical references

- `tools/snowflake/DATASET_LOG.md`: conventions, definitions, settled decisions, open questions, dated log. Read first.
- `tools/snowflake/30_cell.sql`: `CELL` and every `DEF_` rule.
- `/Users/Shared/sv-ntlee/td/data/safe/extract_2026-10-20/ssdb.duckdb`: coded extract under the real table names (gitignored, never commit).

## Changes

- `tools/snowflake/30_cell.sql:9`: `CREATE OR REPLACE TABLE ssdb_integration.lr_strategy.CELL`, key ZIP_CODE x CBD_ID x CHANNEL x PRODUCT_V2, five `DEF_` columns.
- `tools/snowflake/30_cell.sql:64`: checks grid; `:95` definition counts.
- `tools/snowflake/DATASET_LOG.md:16`: Conventions; `:46` Definitions; `:60` Settled; `:80` Open questions; `:98` Log.
- `tools/snowflake/DATASET_LOG.md:358`: correction, a `CBD_ID` can sit in several `CHANNEL`s.
- `tools/snowflake/explore/cbd_vs_channel.sql`, `explore/contested_cells.sql`: the explorations behind the log entries.
- `tools/snowflake/19_structure_profile.sql`, `20_synthetic_tables.sql`: `PARENT` added; `DIST_CH` codes `D1_01`.
- `tools/snowflake/README.md`: rows for `19`, `20`, `30`, `DATASET_LOG.md`.

## Learnings

- Coded extract: union = `synthetic_union.csv.gz`, 97,361 rows, 18 columns in order `SOURCE, TERR_WHOLESALER_CLEAN_NAME, SALES_WHOLESALER_CLEAN_NAME, CBD_ID, FIRM, PARENT, DIST_CH, NEW_DIST, CHANNEL, STATE, ZIP_CODE, PRODUCT_V2, SALES_WHOLESALER_TERRITORY_ID, TERRITORY_WHOLESALER_TERRITORY_ID, SALES_WHOLESALER_HAS_TERRITORY, TERRITORY_WHOLESALER_HAS_TERRITORY, MM_OPP, ACTUAL_SALES_AMOUNT`; no header; NULL written as `\\N`; amounts are integers x 10,000 (assumed, unconfirmed). Territories = two part files, 448,617 rows, `SOURCE, ZIP_CODE, STATE, CHANNEL, CLEAN_ID`. Row counts at work not yet confirmed.
- `data/safe/` was NOT gitignored in the hub; `/data/safe/`, `/data_*.csv.gz`, `/synthetic_*` were added to the hub's `.git/info/exclude`. A worktree may not inherit that; check `git status` before committing.
- DuckDB harness: attach a copy of `ssdb.duckdb` as `ssdb_integration` (writable, since `30` creates a table); define `SHA2` and `DIV0` macros when a script needs them.
- Both firms are annuity carriers: never call `firm_1` "the carrier". `firm_1` = first `SOURCE` in sort order = the one whose rows hold `MM_OPP`.
- Owner wants: full `database.schema.table` paths; source column names kept; no invented terms; minimal files; plain explanations; decisions recorded in `DATASET_LOG.md` with the owner's words.
- Head-to-head under A is thin (5.8% of `MM_OPP`) and biased toward cells a firm already won; B (30.4%) is the workable one. Owner wants both reported.
- The `worker` agent is broken (empty `extensions:` in `~/.pi/agent/agents/worker.md`); this session edited directly.

## Next steps

1. Ask the owner the open decisions below; record each answer in `DATASET_LOG.md` (quote under the question, rule to Settled, row out of Open questions).
2. Confirm `ssdb_integration.lr_strategy` is the dedicated database and schema, the x 10,000 amount factor, and the work row counts (97,361 union; 448,617 territories).
3. Write `31_cell_person.sql` (`CELL_PERSON`: cell x `SOURCE` x person, sales by seller and holder, `MM_OPP_ASSIGNED`, vacant rows), inheriting `DEF_` columns by the cell key; test on the coded extract; add any new `DEF_` row to Definitions.
4. Write `40_person_rank.sql` (`PERSON_RANK`, `RANK_SOURCE_SALES`, `RANK_SOURCE_CHANNEL_SALES`, `RANK_ALL_SHARE_SALES_OF_MM_OPP`, under A and B).
5. Later: decide whether `15` is retired in favour of `30`/`31`; review the branch (no independent review yet); merge is the owner's call.

## Open owner decisions

- Q15: for a `CBD_ID` in several `CHANNEL`s, is `CHANNEL` set by office/branch (keep it in the cell key) or by each firm's own classification (match firms on `CBD_ID` alone)?
- Q3: `firm_1` National `MM_OPP` sitting on a `DIST_CH` that does not sell there: follow the `DIST_CH` that sells to that distribution company (recommended) or keep as is.
- Q9: opportunity at distribution companies a firm never sells to: report as uncovered opportunity (recommended) or spread into territories by channel mix.
- Q10: vacant territory (`firm_2` rows with no `CLEAN_ID`, 5.6% of its opportunity): own "vacant" rows (recommended).
- Q12 / Q8: `firm_2` `PR05` (no `MM_OPP`): contribution ranking only (recommended).
- Q13: compare National, WH, FI per distribution company rather than per ZIP (recommended).
- Q2, Q4, Q5, Q6, Q7, Q14: see the Open questions index in `DATASET_LOG.md`.
- Leftover: delete the empty private repo `helios1168/td-extracts` (token lacks delete scope; owner can do it in repo settings).
