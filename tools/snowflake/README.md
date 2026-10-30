# `tools/snowflake/`: opportunity and sales by channel and territory, both source firms

SQL the owner runs at work in Snowflake, tested first in DuckDB on extracts kept in `data/safe/extract_<date>/`
(gitignored, never committed). Started fresh on 2026-10-30.
Read `DATASET_LOG.md`, Conventions, before writing SQL here: table variables, one result per file, testing.

| file | answers |
|---|---|
| `DATA_MODEL.md` | what the analysis's objects, maps, states and views are |
| `DATASET_LOG.md` | conventions, settled decisions, open questions, dated findings |
| `$TD_REPO/owner_sql/` (git-excluded, never committed) | the owner's queries, verbatim (`s1_sales.sql`, `s1_opp_sales.sql`; they supersede `$TD_REPO/mm_query.sql`), `vars.sql`, the real `SET` lines for the table variables, and `rules_s1.sql`, which makes the rule table `s1_channel_rule` |

Everything before 2026-10-30 (the union-based SQL `00`-`30`, its log and handoffs) is in the tag
`archive/snowflake-2026-10`, e.g. `git show archive/snowflake-2026-10:tools/snowflake/DATASET_LOG.md`.
