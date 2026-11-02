2026-11-01 · m5-studio/snowflake-v2 · Agent: session (claude-opus-5-5)

# The Tableau table rebuilt: DATA_WITHNEWCHANNEL_UNION_W_JOINKEYS_V2

Supersedes `notes/2026-11-01_snowflake-decision-dataset.md`. The owner runs one script,
`tools/snowflake/01_opportunity_sales.sql`, with the SET lines of `$TD_REPO/owner_sql/vars.sql` (9 now), and sends back
one CSV; every query for the owner goes into that script's last result (owner, 2026-11-01: "we want one query, one
output file I share with you"). Read `tools/snowflake/DATASET_LOG.md` Key decisions and the 2026-11-01 entries first.

## Tasks

- Done: statement 17 builds `DATA_WITHNEWCHANNEL_UNION_W_JOINKEYS_V2` (the live table's 24 columns and types,
  TERR_WHOLESALER renamed OLD_TERR_WHOLESALER, NEW_TERR_WHOLESALER and NEW_TERR_CHANNEL added) and `TERRITORIES_V2`
  (the two territory tables keyed like `_v2`, for Tableau's territory join). The live table is never written.
- Done, column mapping (owner's words in the log): CBD_ID = CRD, FIRM = broker name, PARENT NULL, DIST_CH the old
  channel in firm 1's names, NEW_DIST the new channel, CHANNEL `uni_latest.sql`'s CASE, MM_OPP per cell (repeated per
  holder where 2+ hold), ACTUAL_SALES_AMOUNT the sales, SALES_AMOUNT firm 1's comp'd (NULL for firm 2),
  TERR_WHOLESALER_CLEAN_NAME and TERRITORY_WHOLESALER_TERRITORY_ID the new holder, SALES_WHOLESALER the seller (on
  opportunity rows and no-seller sales: the old holder), SALES_WHOLESALER_CLEAN_NAME the seller's territory-table name,
  address IDs and HAS_TERRITORY flags NULL, no filters.
- Done: firm 1's recorded IFA/IMO, FI/IMO and IMO are the sale's new channel again (the old table did this; extract
  `data/safe/legacy_imo_2026-11-01-1808.csv`).
- Done: TABLEAU layer (18, 18b): SIZES, VS LIVE, CHECKS (must be 0), SCHEMA, IMO AND RAYMOND JAMES, BOOK BY CHANNEL,
  TERRITORIES_V2 sizes and checks, ADDRESS COLUMNS and ROWS.
- Not run in Snowflake since the IFA/IMO fix; the owner's last look ("we're good") was on an earlier `_v2`.

## Critical references

- `tools/snowflake/01_opportunity_sales.sql` statement 17 (`tmp_union`, `_v2`, `TERRITORIES_V2`), 18 (`tmp_tb_out`),
  18b (`tmp_tb_out2`), 19 (the one result).
- `tools/snowflake/union_test.sh`: the Tableau table's checks; `tools/snowflake/explore/legacy_imo.sql`: the old
  tables' IMO and Raymond James mapping (run once).

## Learnings

- `git grep` searches tracked files only: scan new files with plain `grep -r` before `git add`, and stop on a hit.
- Two sessions wrote this worktree at once (the owner closed one): `40abbc2` carried the other session's
  TERRITORIES_V2 work, logged by it in `357f7cf`. Check `git log` for commits you did not make before each commit.
- The old union needed no old-vs-new holder choice because its holders never moved; ours do (2.4% of firm 1's
  opportunity, 15% of firm 2's): pair DIST_CH with OLD_TERR_WHOLESALER, CHANNEL with TERR_WHOLESALER_CLEAN_NAME.

## Next steps

1. Owner reruns the script; read the CSV: every CHECKS row 0 (sales and TABLEAU), SCHEMA (23 SAME, TERR_WHOLESALER
   only in live, 3 only in V2), firm 1 SALES NEW CHANNEL IFA/IMO about $1,012MM, FI/IMO about $289MM, IMO about
   $2,674MM; IMO AND RAYMOND JAMES (why the live table's IMO rows missed the extract's third part); SOURCE label check.
2. The address join (`$s1_addr`, `$s2_addr`: ADDRESS COLUMNS and ROWS parts), designed from that CSV.

## Open owner decisions

- Raymond James, firm 2: our IFA/IMO ($28.6MM) and FI/IMO ($3.1MM) on two keys, or IFA and FI as the old table had.
- Firm 2's opportunity: the old firm 2 table had none; `_v2` has firm 2's own (a sheet summing MM_OPP without a SOURCE
  filter doubles). Keep, or 0.
- Citizens and HSBC, firm 2: FI/IMO in the old table (dropped by its filter); now their firm's channel.
- An old-state territory join (old holder key and channel), not built.
- Still open from before: Alliance Global, Q41 AMER's holder, Q44 AFS's, the second audit, landing (owner: not now).
