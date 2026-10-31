2026-10-31 · m5-studio/snowflake-v2 · 44833c2 · Agent: session (claude-opus-5-5)

# Opportunity and sales in one file; next: firm 1's sales mapping and the MGA agent code

Supersedes `notes/2026-10-30_snowflake-opp-build-ready.md`. Layers 01 and 02 are one Run All file,
`tools/snowflake/01_opportunity_sales.sql`, tested in DuckDB only: nothing has run in Snowflake yet. Read
`tools/snowflake/DATASET_LOG.md` (Conventions, Settled, Key decisions, the 2026-10-31 entry) and `README.md` first.

## Tasks

- Done: layer 01, opportunity routed by firm (`TMP_O1_FIRM`, `TMP_O1_CELLS_S1` and `_S2`, `TMP_O1_DATASET`), and
  layer 02, sales credited to the seller at ZIP grain (`TMP_O2_SALES`, `TMP_O2_DATASET`), in one file with one result
  set under `LAYER`.
- Done, in Settled with the owner's words: source 2's old channel in firm 1's names (option (a)); sales stay with the
  seller (Q31); a sale's old channel is its recorded one, and the dataset ties to the sales tables; EDJ, AMER and AFS
  are channels like the others; Q29's holder channels are fixed (Wells WH goes to the WH wholesaler from any origin).
- Done: `explore/lpl_checks.sql` (Q43), `explore/transfers.sql`, `explore/sales_crosswalk.sql` with `TMP_SALES_MAP`
  and its `CBD_ID`; `EQUAL_NULL` for NULL-safe equality; `audit.js` takes `from`.
- Partial: Q43 (checks written, not run). Not started: Q45, the MGA agent code; the second audit (owner: wait).

## Critical references

- `tools/snowflake/01_opportunity_sales.sql:385` `--9. Source 1's company ID -> the firms whose market metrics rows carry it, as layer 01 derives it from`; `:402` statement 10, firm 1's sales to a firm; `:510` `TMP_O2_DATASET`.
- `tools/snowflake/DATASET_LOG.md:152`-`:153`: the two key decisions behind that mapping; `:186` Q45.
- `tools/snowflake/explore/sales_crosswalk.sql:69` `--3. The mapping table: the crosswalk's keys and outputs, no amounts.`

## Changes

- `tools/snowflake/01_opportunity_sales.sql:51` statements 1-7, `:370` 8-14, `:688` 15; replaces `01_opportunity.sql` and `02_sales.sql`.
- `tools/snowflake/01_opportunity_test.sh`: 81 checks; `02_sales_test.sh`: 46, firm 1's sales fixture at `:47`.
- `tools/snowflake/explore/transfers.sql:18` (9 checks); `explore/sales_crosswalk.sql:40` (24); `explore/lpl_checks.sql` (15).
- `tools/snowflake/DATASET_LOG.md:60` Settled, `:137` Key decisions, `:168` open index (Q41, Q44, Q45), `:189` Log.
- `$TD_REPO/owner_sql/vars.sql` (git-excluded): `s1_sales` and `s2_sales` added.

## Learnings

- Paseo shows only agents its daemon started or imported; this herdr-started pi session appeared after `paseo import`
  with `--provider pi` and the worktree as `--cwd` (owner, 2026-10-31: "it works now").
- A pi session has no speak tool: voice input arrives as text asking for a spoken reply; answer in text and say so.
- Mutation runs: `cmp` the mutated copy first; a `sed` that matched nothing passed silently twice. Two tests needed new
  fixture rows (a blank-channel cell beside an IFA cell; a NULL product bucket) before their mutation failed.
- Hand-worked expected values were wrong three times, the query right each time: recompute before touching SQL.
- Parentheses in a double-quoted `sed` pattern broke bash; edit with Python and assert each match count.
- Before each commit, the carrier-name grep over `tools/snowflake` and `notes/*snowflake*` must come back empty.

## Next steps

1. The owner's "close look" at firm 1's sales mapping: walk statements 9-10, Key decisions rows `:152`-`:153` and the
   `FIRM_BASIS` values. For sizes the owner runs `01_opportunity_sales.sql` (five SET lines from `owner_sql/vars.sql`;
   the base sales table must exist) and copies its CSV to `data/safe/` (`SALES FIRM BASIS`, `Q35`, `TIE-OUT`,
   `CHECKS`); `explore/sales_crosswalk.sql` is read at work only (firm names with $).
2. Settle Q45 in one batched confirm. Then `owner_sql/s1_sales.sql` keeps `MGA_AGENT_CD`: `base_sales` (`:86`) and each
   grouping after it (`:158`, `:200`, `:282`, `:307`, `:369`, `:413`); save the new version verbatim in `owner_sql/`,
   pin its sha256 in a log entry, and rebuild the base sales table at work.
3. Carry it through statement 10 (grouping `:409`-`:419`), 12 and 13; firm 2 and opportunity rows carry none; add the
   column to the fixture (`02_sales_test.sh:47`) with checks and mutations; the crosswalk and the map gain it if Q45
   makes it a key (`RAW KEYS ON 2+ OUTPUTS` re-keyed); log; README.
4. Then the offered items below, in the owner's order.

## Open owner decisions

- Q45: MGA a column only, or a key for the firm (company 8's LPL split) or the channel (`MGA_MAP`)? Who edits
  `s1_sales.sql`? With MGA in the key a sale never shares a row with its cell's opportunity (sums still hold); or keep
  the dataset's grain and add a sales detail table.
- AFS off the new-channel list (no channel update; Q44 goes)? AMER (Q41) back to Parked?
- Firm 1 sales: apply the company-ID list (438, 57, 1967, 1822, 14, 1823) to sales directly, so a sale with no firm
  still gets its new channel?
- A manual sales firm override table in statement 8: key ID x channel, or also firm name; override anything, or fill
  only unresolved?
- Offered, unanswered: the map joined to both sales tables inside Run All; the book names (`OPP_BOOK_*`,
  `SALES_IN_BOOK_*`, buckets KEPT, LOST, GAINED, OUTSIDE) with bucket and channel-share parts in
  `explore/transfers.sql`; a territory table (needs Q28 and firm 1's territory key); `SALES_FIRM_ID` renamed
  `SALES_CBD_ID`.
- Firm 2's seller and holder meet on RVP name text: compare the 2025 sales RVPs with the territory table's, then an
  alias table, or `REGIONIDS` if it holds territory IDs.
- Q42 (`MM_AMOUNT`); Q43 (the owner runs `explore/lpl_checks.sql`); the audit, `from` "2026-10-30: the first audit
  (611 claims); what it corrects".
- A person's name in the author metadata of `notes/2026-10-12_main-map-joint-wifi-grid-discover.md` (another thread).
