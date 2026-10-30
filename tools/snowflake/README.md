# `tools/snowflake/`: opportunity and sales by channel and territory, both source firms

SQL the owner runs at work in Snowflake, tested first in DuckDB, on made-up tables with the real columns or on extracts
kept in `data/safe/extract_<date>/` (gitignored, never committed). Started fresh on 2026-10-30.
Read `DATASET_LOG.md`, Conventions, before writing SQL here: table variables, one result per file, testing.

| file | answers |
|---|---|
| `DATA_MODEL.md` | what the analysis's objects, maps, states and views are |
| `DATASET_LOG.md` | conventions, settled decisions, open questions, dated findings |
| `explore/profile.sql` | the opportunity profile: the firm key, firm 1's channel per firm, labels, holders, routing against `crd_dist_override`; one result set. Test: `sh explore/profile_test.sh` |
| `explore/override_review.sql` | the firms where `crd_dist_override` and firm 1's route disagree, every name of their CRDs (Q38). Test: `sh explore/override_review_test.sh` |
| `explore/schema.sql` | the source tables' columns (run 2026-10-30) |
| `audit.js` | the audit workflow: the documents' claims checked against the code, `DATA_MODEL.md` the reference (`DATASET_LOG.md`, Conventions, Audit) |
| `$TD_REPO/owner_sql/` (git-excluded, never committed) | the owner's queries, verbatim (`s1_sales.sql`, `s1_opp_sales.sql`; they supersede `$TD_REPO/mm_query.sql`), and `vars.sql`, the real `SET` lines for the table variables |

Everything before 2026-10-30 (the union-based SQL `00`-`30`, its log and handoffs) is in the tag
`archive/snowflake-2026-10`, e.g. `git show archive/snowflake-2026-10:tools/snowflake/DATASET_LOG.md`.
