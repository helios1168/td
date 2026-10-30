# `tools/snowflake/`: opportunity and sales by channel and territory, both source firms

SQL the owner runs at work in Snowflake, tested first in DuckDB, on made-up tables with the real columns or on extracts
kept in `data/safe/extract_<date>/` (gitignored, never committed). Started fresh on 2026-10-30.
Read `DATASET_LOG.md`, Conventions, before writing SQL here: table variables, one result per file, testing.

| file | answers |
|---|---|
| `DATA_MODEL.md` | what the analysis's objects, maps, states and views are |
| `DATASET_LOG.md` | conventions, settled decisions, open questions, dated findings |
| `01_opportunity.sql` | layer 01: both sources' opportunity routed by firm, as temporary tables (`TMP_O1_FIRM`, `TMP_O1_CELLS_S1`, `TMP_O1_CELLS_S2`, and `TMP_O1_DATASET`, both sources stacked with wholesaler names, the table to look at); one result set of views 1, 2a, 2b, 3 by label, scope and checks. Test: `sh 01_opportunity_test.sh` |
| `02_sales.sql` | layer 02: both sources' sales credited to the seller beside the opportunity each wholesaler holds, at ZIP grain (`TMP_O2_DATASET`: every sale, under its own channel as `OLD_CHANNEL`; `SCOPE` flags the firms out of scope); run after `01_opportunity.sql` in the same worksheet; one result set of sizes, the tie-out of the base sales table and checks. Test: `sh 02_sales_test.sh` |
| `explore/profile.sql` | the opportunity profile: the firm key, firm 1's channel per firm, labels, holders, routing against `crd_dist_override`; one result set. Test: `sh explore/profile_test.sh` |
| `explore/override_review.sql` | the firms where `crd_dist_override` and firm 1's route disagree, every name of their CRDs (Q38). Test: `sh explore/override_review_test.sh` |
| `explore/lpl_checks.sql` | Q43, firm 1's LPL opportunity not tying out: LPL's feed rows with the company ID the owner's query gives them (A1-A3), and every company with regions of its own (B1); one result set. Test: `sh explore/lpl_checks_test.sh` |
| `explore/amer_holder.sql` | parked with Q41 (EDJ, AMER out of scope): AMER's holder, a company's own regions, what covers its opportunity ZIPs, who sells to it (`SET company_id`). Test: `sh explore/amer_holder_test.sh` |
| `explore/schema.sql` | the source tables' columns (run 2026-10-30) |
| `audit.js` | the audit workflow: the documents' claims checked against the code, `DATA_MODEL.md` the reference (`DATASET_LOG.md`, Conventions, Audit) |
| `$TD_REPO/owner_sql/` (git-excluded, never committed) | the owner's queries, verbatim (`s1_sales.sql`, `s1_opp_sales.sql`; they supersede `$TD_REPO/mm_query.sql`), and `vars.sql`, the real `SET` lines for the table variables |

Everything before 2026-10-30 (the union-based SQL `00`-`30`, its log and handoffs) is in the tag
`archive/snowflake-2026-10`, e.g. `git show archive/snowflake-2026-10:tools/snowflake/DATASET_LOG.md`.
