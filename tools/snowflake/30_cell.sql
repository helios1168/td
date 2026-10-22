-- CELL: one row per ZIP_CODE x CBD_ID x CHANNEL x PRODUCT_V2, the unit of market both firms share
-- (DATASET_LOG.md, Settled).  Holds the cell's MM_OPP, each firm's net ACTUAL_SALES_AMOUNT and every DEF_
-- column; the rules are written here and nowhere else, and described in DATASET_LOG.md, Definitions.
-- FIRM_1 is the first SOURCE in sort order, FIRM_2 the second.  "Sells" = positive net
-- ACTUAL_SALES_AMOUNT over the scope named.
-- The _V2 columns match on ZIP_CODE x CBD_ID x PRODUCT_V2 across all CHANNELs (CHANNEL is each firm's own
-- desk label, DATASET_LOG.md, 2026-10-21 Q15).
-- Run statement 1, then 2 (checks: every MUST_BE_ZERO row must be 0), then 3 (definition counts).

-- Statement 1.  The table.
CREATE OR REPLACE TABLE ssdb_integration.lr_strategy.CELL AS
WITH
src AS (             -- SOURCE -> 1, 2
  SELECT SOURCE, DENSE_RANK() OVER (ORDER BY SOURCE) AS N
  FROM (SELECT DISTINCT SOURCE FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys) x),
u AS (
  SELECT r.*, s.N
  FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys r
  JOIN src s ON s.SOURCE = r.SOURCE),
cell AS (
  SELECT ZIP_CODE, CBD_ID, CHANNEL, PRODUCT_V2,
         MAX(STATE)  AS STATE,
         MAX(FIRM)   AS FIRM,
         MAX(PARENT) AS PARENT,
         COALESCE(SUM(MM_OPP), 0)                                        AS MM_OPP,
         COALESCE(SUM(CASE WHEN N = 1 THEN ACTUAL_SALES_AMOUNT END), 0)  AS ACTUAL_SALES_AMOUNT_FIRM_1,
         COALESCE(SUM(CASE WHEN N = 2 THEN ACTUAL_SALES_AMOUNT END), 0)  AS ACTUAL_SALES_AMOUNT_FIRM_2
  FROM u
  GROUP BY ZIP_CODE, CBD_ID, CHANNEL, PRODUCT_V2),
cell_all AS (        -- ZIP_CODE x CBD_ID x PRODUCT_V2 over all CHANNELs: do both firms sell?
  SELECT ZIP_CODE, CBD_ID, PRODUCT_V2,
         SUM(ACTUAL_SALES_AMOUNT_FIRM_1) > 0 AND SUM(ACTUAL_SALES_AMOUNT_FIRM_2) > 0 AS BOTH_SELL
  FROM cell
  GROUP BY ZIP_CODE, CBD_ID, PRODUCT_V2),
product_sold AS (    -- PRODUCT_V2 each firm sells, nationally
  SELECT PRODUCT_V2,
         SUM(CASE WHEN N = 1 THEN ACTUAL_SALES_AMOUNT ELSE 0 END) > 0 AS SOLD_1,
         SUM(CASE WHEN N = 2 THEN ACTUAL_SALES_AMOUNT ELSE 0 END) > 0 AS SOLD_2
  FROM u GROUP BY PRODUCT_V2),
offer_all AS (       -- CBD_ID x PRODUCT_V2 each firm sells, in any ZIP_CODE and any CHANNEL
  SELECT CBD_ID, PRODUCT_V2,
         SUM(CASE WHEN N = 1 THEN ACTUAL_SALES_AMOUNT ELSE 0 END) > 0 AS SOLD_1,
         SUM(CASE WHEN N = 2 THEN ACTUAL_SALES_AMOUNT ELSE 0 END) > 0 AS SOLD_2
  FROM u GROUP BY CBD_ID, PRODUCT_V2)
SELECT c.ZIP_CODE, c.CBD_ID, c.CHANNEL, c.PRODUCT_V2, c.STATE, c.FIRM, c.PARENT,
       c.MM_OPP, c.ACTUAL_SALES_AMOUNT_FIRM_1, c.ACTUAL_SALES_AMOUNT_FIRM_2,
       -- DEF_ZIP_VALID: ZIP_CODE is 5 digits and not 00000
       COALESCE(LENGTH(c.ZIP_CODE) = 5 AND TRIM(c.ZIP_CODE, '0123456789') = '' AND c.ZIP_CODE <> '00000', FALSE)
         AS DEF_ZIP_VALID,
       -- DEF_CHANNEL_GROUP: IFA apart from National, WH and FI
       CASE WHEN c.CHANNEL = 'IFA' THEN 'IFA'
            WHEN c.CHANNEL IN ('National', 'WH', 'FI') THEN 'National+WH+FI' END
         AS DEF_CHANNEL_GROUP,
       -- DEF_PRODUCT_SCOPE: which firms sell this PRODUCT_V2 anywhere
       CASE WHEN p.SOLD_1 AND p.SOLD_2 THEN 'both'
            WHEN p.SOLD_1 THEN 'firm_1 only'
            WHEN p.SOLD_2 THEN 'firm_2 only'
            ELSE 'neither' END
         AS DEF_PRODUCT_SCOPE,
       -- DEF_CONTESTED_SOLD_V2 (A): both firms have positive net sales in this ZIP_CODE x CBD_ID x PRODUCT_V2,
       -- summed over all CHANNELs; set on every CHANNEL row of that cell
       COALESCE(ca.BOTH_SELL, FALSE)
         AS DEF_CONTESTED_SOLD_V2,
       -- DEF_CONTESTED_OFFERED_V2 (B): both firms sell this PRODUCT_V2 to this CBD_ID, in any ZIP_CODE and any
       -- CHANNEL; set on every CHANNEL row of that CBD_ID x PRODUCT_V2
       COALESCE(oa.SOLD_1 AND oa.SOLD_2, FALSE)
         AS DEF_CONTESTED_OFFERED_V2
FROM cell c
LEFT JOIN product_sold p ON p.PRODUCT_V2 IS NOT DISTINCT FROM c.PRODUCT_V2
LEFT JOIN cell_all ca ON ca.ZIP_CODE IS NOT DISTINCT FROM c.ZIP_CODE AND ca.CBD_ID IS NOT DISTINCT FROM c.CBD_ID
                     AND ca.PRODUCT_V2 IS NOT DISTINCT FROM c.PRODUCT_V2
LEFT JOIN offer_all oa ON oa.CBD_ID IS NOT DISTINCT FROM c.CBD_ID AND oa.PRODUCT_V2 IS NOT DISTINCT FROM c.PRODUCT_V2;

-- Statement 2.  Checks.
WITH
src AS (SELECT SOURCE, DENSE_RANK() OVER (ORDER BY SOURCE) AS N
        FROM (SELECT DISTINCT SOURCE FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys) x),
u AS (SELECT r.*, s.N FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys r JOIN src s ON s.SOURCE = r.SOURCE)
SELECT 'SOURCE values, minus 2' AS CHECK_NAME, (SELECT COUNT(*) FROM src) - 2 AS VALUE, TRUE AS MUST_BE_ZERO
UNION ALL SELECT 'SOURCEs with MM_OPP, minus 1 (two would count a cell twice)',
       (SELECT COUNT(DISTINCT SOURCE) FROM u WHERE COALESCE(MM_OPP, 0) <> 0) - 1, TRUE
UNION ALL SELECT 'CELL keys appearing twice',
       (SELECT COUNT(*) FROM (SELECT ZIP_CODE, CBD_ID, CHANNEL, PRODUCT_V2 FROM ssdb_integration.lr_strategy.CELL
                              GROUP BY ZIP_CODE, CBD_ID, CHANNEL, PRODUCT_V2 HAVING COUNT(*) > 1) x), TRUE
UNION ALL SELECT 'MM_OPP: CELL total minus source total',
       ROUND((SELECT SUM(MM_OPP) FROM ssdb_integration.lr_strategy.CELL) - (SELECT COALESCE(SUM(MM_OPP), 0) FROM u), 6), TRUE
UNION ALL SELECT 'ACTUAL_SALES_AMOUNT_FIRM_1: CELL total minus source total',
       ROUND((SELECT SUM(ACTUAL_SALES_AMOUNT_FIRM_1) FROM ssdb_integration.lr_strategy.CELL)
           - (SELECT COALESCE(SUM(ACTUAL_SALES_AMOUNT), 0) FROM u WHERE N = 1), 6), TRUE
UNION ALL SELECT 'ACTUAL_SALES_AMOUNT_FIRM_2: CELL total minus source total',
       ROUND((SELECT SUM(ACTUAL_SALES_AMOUNT_FIRM_2) FROM ssdb_integration.lr_strategy.CELL)
           - (SELECT COALESCE(SUM(ACTUAL_SALES_AMOUNT), 0) FROM u WHERE N = 2), 6), TRUE
UNION ALL SELECT 'cells with CHANNEL outside IFA, National, WH, FI (DEF_CHANNEL_GROUP NULL)',
       (SELECT COUNT(*) FROM ssdb_integration.lr_strategy.CELL WHERE DEF_CHANNEL_GROUP IS NULL), FALSE
UNION ALL SELECT 'cells with an invalid ZIP_CODE (DEF_ZIP_VALID false)',
       (SELECT COUNT(*) FROM ssdb_integration.lr_strategy.CELL WHERE NOT DEF_ZIP_VALID), FALSE
UNION ALL SELECT 'cells with NULL CBD_ID',
       (SELECT COUNT(*) FROM ssdb_integration.lr_strategy.CELL WHERE CBD_ID IS NULL), FALSE
UNION ALL SELECT 'cells whose rows carry 2+ FIRM or PARENT (CELL keeps the largest)',
       (SELECT COUNT(*) FROM (SELECT ZIP_CODE, CBD_ID, CHANNEL, PRODUCT_V2 FROM u
                              GROUP BY ZIP_CODE, CBD_ID, CHANNEL, PRODUCT_V2
                              HAVING COUNT(DISTINCT FIRM) > 1 OR COUNT(DISTINCT PARENT) > 1) x), FALSE
ORDER BY MUST_BE_ZERO DESC, CHECK_NAME;

-- Statement 3.  What each definition covers: cells and shares of MM_OPP and of each firm's sales.
WITH
t AS (SELECT SUM(MM_OPP) AS O, SUM(ACTUAL_SALES_AMOUNT_FIRM_1) AS S1, SUM(ACTUAL_SALES_AMOUNT_FIRM_2) AS S2
      FROM ssdb_integration.lr_strategy.CELL),
d AS (
  SELECT 'DEF_ZIP_VALID' AS DEFINITION, CAST(DEF_ZIP_VALID AS VARCHAR) AS DEF_VALUE, MM_OPP,
         ACTUAL_SALES_AMOUNT_FIRM_1 AS S1, ACTUAL_SALES_AMOUNT_FIRM_2 AS S2 FROM ssdb_integration.lr_strategy.CELL
  UNION ALL SELECT 'DEF_CHANNEL_GROUP', DEF_CHANNEL_GROUP, MM_OPP, ACTUAL_SALES_AMOUNT_FIRM_1, ACTUAL_SALES_AMOUNT_FIRM_2
  FROM ssdb_integration.lr_strategy.CELL
  UNION ALL SELECT 'DEF_PRODUCT_SCOPE', DEF_PRODUCT_SCOPE, MM_OPP, ACTUAL_SALES_AMOUNT_FIRM_1, ACTUAL_SALES_AMOUNT_FIRM_2
  FROM ssdb_integration.lr_strategy.CELL
  UNION ALL SELECT 'DEF_CONTESTED_SOLD_V2', CAST(DEF_CONTESTED_SOLD_V2 AS VARCHAR), MM_OPP, ACTUAL_SALES_AMOUNT_FIRM_1, ACTUAL_SALES_AMOUNT_FIRM_2
  FROM ssdb_integration.lr_strategy.CELL
  UNION ALL SELECT 'DEF_CONTESTED_OFFERED_V2', CAST(DEF_CONTESTED_OFFERED_V2 AS VARCHAR), MM_OPP, ACTUAL_SALES_AMOUNT_FIRM_1, ACTUAL_SALES_AMOUNT_FIRM_2
  FROM ssdb_integration.lr_strategy.CELL)
SELECT d.DEFINITION, d.DEF_VALUE, COUNT(*) AS CELLS,
       ROUND(100 * SUM(d.MM_OPP) / MAX(t.O), 1) AS PCT_OF_MM_OPP,
       ROUND(100 * SUM(d.S1) / MAX(t.S1), 1)    AS PCT_OF_FIRM_1_SALES,
       ROUND(100 * SUM(d.S2) / MAX(t.S2), 1)    AS PCT_OF_FIRM_2_SALES
FROM d CROSS JOIN t
GROUP BY d.DEFINITION, d.DEF_VALUE
ORDER BY d.DEFINITION, d.DEF_VALUE;
