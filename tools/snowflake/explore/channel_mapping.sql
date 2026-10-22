-- Exploration (DuckDB, on the coded extract): what sets a row's CHANNEL (Q15).  Is CHANNEL a function of
-- SOURCE x DIST_CH x FIRM; which multi-channel CBD_IDs have firms in different channels and which have a
-- firm in several; how often a firm uses 2+ CHANNELs for one company in one ZIP; and how many contested
-- ZIP_CODE x CBD_ID x PRODUCT_V2 cells have both firms in the same CHANNEL.  Findings: DATASET_LOG.md,
-- 2026-10-21, Q15 answered.  "Uses" a CHANNEL = has a row (opportunity or sales) in it.
--   duckdb -box < tools/snowflake/explore/channel_mapping.sql      (run from the hub root)
ATTACH 'data/safe/extract_2026-10-20/ssdb.duckdb' AS s (READ_ONLY);
CREATE TEMP TABLE u AS SELECT * FROM s.lr_strategy.data_withnewchannel_union_w_joinkeys;
-- CBD_IDs with rows in 2+ CHANNELs (NULL CBD_ID left out)
CREATE TEMP TABLE mc AS
SELECT CBD_ID FROM u WHERE CBD_ID IS NOT NULL GROUP BY CBD_ID HAVING COUNT(DISTINCT CHANNEL) > 1;

.print '== CHANNEL as a function of SOURCE x DIST_CH: groups, and groups with 2+ CHANNELs'
SELECT COUNT(*) AS groups, COUNT_IF(n > 1) AS with_2plus_channels
FROM (SELECT SOURCE, DIST_CH, COUNT(DISTINCT CHANNEL) AS n FROM u GROUP BY ALL);

.print '== ... and of SOURCE x DIST_CH x FIRM'
SELECT COUNT(*) AS groups, COUNT_IF(n > 1) AS with_2plus_channels
FROM (SELECT SOURCE, DIST_CH, FIRM, COUNT(DISTINCT CHANNEL) AS n FROM u GROUP BY ALL);

.print '== the groups of SOURCE x DIST_CH x FIRM with 2+ CHANNELs (DIST_CH is NULL; the rows have no amounts)'
SELECT SOURCE, DIST_CH, FIRM, COUNT(DISTINCT CHANNEL) AS channels, COUNT(*) AS row_count,
       COUNT_IF(ACTUAL_SALES_AMOUNT > 0) AS rows_with_sales, COUNT_IF(COALESCE(MM_OPP, 0) <> 0) AS rows_with_mm_opp
FROM u GROUP BY SOURCE, DIST_CH, FIRM HAVING COUNT(DISTINCT CHANNEL) > 1 ORDER BY ALL;

.print '== same, with NULL DIST_CH left out: groups with 2+ CHANNELs'
SELECT COUNT(*) AS groups, COUNT_IF(n > 1) AS with_2plus_channels
FROM (SELECT SOURCE, DIST_CH, FIRM, COUNT(DISTINCT CHANNEL) AS n FROM u WHERE DIST_CH IS NOT NULL GROUP BY ALL);

.print '== multi-channel CBD_IDs: how many have each SOURCE in one CHANNEL only (the firms then sit in different CHANNELs)'
CREATE TEMP TABLE per_source AS
SELECT CBD_ID, SOURCE, COUNT(DISTINCT CHANNEL) AS n FROM u WHERE CBD_ID IN (SELECT CBD_ID FROM mc) GROUP BY ALL;
SELECT COUNT(*) AS multi_channel_cbd,
       COUNT_IF(max_n = 1) AS each_source_in_one_channel,
       COUNT_IF(max_n > 1) AS some_source_in_2plus_channels
FROM (SELECT CBD_ID, MAX(n) AS max_n FROM per_source GROUP BY CBD_ID);
.print '== ... which CBD_IDs those are'
SELECT CBD_ID FROM per_source GROUP BY CBD_ID HAVING MAX(n) = 1 ORDER BY CBD_ID;

.print '== per SOURCE, in one ZIP_CODE x CBD_ID of a multi-channel company: pairs, pairs with 2+ CHANNELs, % of positive sales of the SOURCE at those companies that sit in such pairs'
WITH z AS (SELECT SOURCE, ZIP_CODE, CBD_ID, COUNT(DISTINCT CHANNEL) AS n,
                  SUM(ACTUAL_SALES_AMOUNT) FILTER (WHERE ACTUAL_SALES_AMOUNT > 0) AS pos
           FROM u WHERE CBD_ID IN (SELECT CBD_ID FROM mc) GROUP BY ALL)
SELECT SOURCE, COUNT(*) AS pairs, COUNT_IF(n > 1) AS pairs_2plus_channels,
       ROUND(100 * SUM(pos) FILTER (WHERE n > 1) / SUM(pos), 1) AS pct_of_sales_in_those_pairs
FROM z GROUP BY SOURCE ORDER BY SOURCE;

.print '== ZIP_CODE x CBD_ID x PRODUCT_V2 where both firms have positive net sales: all CHANNELs summed; in the same CHANNEL; only in different CHANNELs'
WITH c AS (SELECT ZIP_CODE, CBD_ID, PRODUCT_V2, CHANNEL,
                  COALESCE(SUM(ACTUAL_SALES_AMOUNT) FILTER (WHERE SOURCE = 'firm_1'), 0) AS s1,
                  COALESCE(SUM(ACTUAL_SALES_AMOUNT) FILTER (WHERE SOURCE = 'firm_2'), 0) AS s2
           FROM u GROUP BY ALL),
k AS (SELECT ZIP_CODE, CBD_ID, PRODUCT_V2, SUM(s1) AS t1, SUM(s2) AS t2, COUNT_IF(s1 > 0 AND s2 > 0) AS channels_both_sell
      FROM c GROUP BY ALL)
SELECT COUNT_IF(t1 > 0 AND t2 > 0) AS both_sell,
       COUNT_IF(t1 > 0 AND t2 > 0 AND channels_both_sell > 0) AS same_channel,
       COUNT_IF(t1 > 0 AND t2 > 0 AND channels_both_sell = 0) AS different_channels_only
FROM k;
