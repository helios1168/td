# `tools/snowflake/`: opportunity and sales by channel and territory, both source firms

SQL the owner runs at work in Snowflake, tested first in DuckDB, on made-up tables with the real columns or on extracts
kept in `data/safe/extract_<date>/` (gitignored, never committed). Started fresh on 2026-10-30.
Read `DATASET_LOG.md`, Conventions, before writing SQL here: table variables, one result per file, testing.

| file | answers |
|---|---|
| `DATA_MODEL.md` | what the analysis's objects, maps, states and views are |
| `DATASET_LOG.md` | conventions, settled decisions, open questions, dated findings |
| `01_opportunity_sales.sql` | layers 01 and 02 in one Run All file: both sources' opportunity routed by firm (statements 1-7: `TMP_O1_FIRM`, `TMP_O1_CELLS_S1`, `TMP_O1_CELLS_S2`, `TMP_O1_DATASET`), then sales credited to the seller beside the opportunity each wholesaler holds, at ZIP grain (8-14: `TMP_O2_SALES`, `TMP_O2_DATASET`, the table to look at); one result set under `LAYER`: views 1, 2a, 2b, 3, sales sizes, the tie-out of the base sales table, checks. Tests: `sh 01_opportunity_test.sh` (opportunity), `sh 02_sales_test.sh` (all) |
| `explore/transfers.sql` | how opportunity changes hands with the channel swap, from `TMP_O2_DATASET`: transfers (from -> to wholesaler by old and new channel) and each wholesaler's book before and after with its sales; run after `01_opportunity_sales.sql` in the same worksheet; names appear, read it at work. Test: `sh explore/transfers_test.sh` |
| `explore/profile.sql` | the opportunity profile: the firm key, firm 1's channel per firm, labels, holders, routing against `crd_dist_override`; one result set. Test: `sh explore/profile_test.sh` |
| `explore/override_review.sql` | the firms where `crd_dist_override` and firm 1's route disagree, every name of their CRDs (Q38). Test: `sh explore/override_review_test.sh` |
| `explore/lpl_checks.sql` | Q43, firm 1's LPL opportunity not tying out: LPL's feed rows with the company ID the owner's query gives them (A1-A3), and every company with regions of its own (B1); one result set. Test: `sh explore/lpl_checks_test.sh` |
| `explore/amer_holder.sql` | Q41 and Q44: a company's own regions (`SET company_id`: 805 AMER, 438 AFS), what covers its opportunity ZIPs, who sells to it. Test: `sh explore/amer_holder_test.sh` |
| `explore/schema.sql` | the source tables' columns (run 2026-10-30) |
| `audit.js` | the audit workflow: the documents' claims checked against the code, `DATA_MODEL.md` the reference (`DATASET_LOG.md`, Conventions, Audit) |
| `$TD_REPO/owner_sql/` (git-excluded, never committed) | the owner's queries, verbatim (`s1_sales.sql`, `s1_opp_sales.sql`; they supersede `$TD_REPO/mm_query.sql`), and `vars.sql`, the real `SET` lines for the table variables |

Everything before 2026-10-30 (the union-based SQL `00`-`30`, its log and handoffs) is in the tag
`archive/snowflake-2026-10`, e.g. `git show archive/snowflake-2026-10:tools/snowflake/DATASET_LOG.md`.
