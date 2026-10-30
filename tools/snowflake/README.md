# `tools/snowflake/`: opportunity and sales by channel and territory, both source firms

SQL the owner runs at work in Snowflake, tested first in DuckDB on extracts kept in `data/safe/extract_<date>/`
(gitignored, never committed). Started fresh on 2026-10-30.

| file | answers |
|---|---|
| `DATA_MODEL.md` | what the analysis's objects, maps, states and views are |
| `DATASET_LOG.md` | conventions, settled decisions, open questions, dated findings |
| `$TD_REPO/owner_sql/` (git-excluded, never committed) | the owner's queries, verbatim; supersede `$TD_REPO/mm_query.sql`. `s1_sales.sql`: source 1 sales, before the market metrics transformations |

Everything before 2026-10-30 (the union-based SQL `00`-`30`, its log and handoffs) is in the tag
`archive/snowflake-2026-10`, e.g. `git show archive/snowflake-2026-10:tools/snowflake/DATASET_LOG.md`.
