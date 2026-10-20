-- The territories table with opportunity and sales appended: one output row per territories row.
-- Reads the two source tables and the crosswalk; creates nothing (Statement 0 is a template you run
-- once, at work, to create the crosswalk).
--   Statement 0  (commented) create ssdb_integration.lr_strategy.dist_ch_crosswalk
--   Statement 1  checks: every row with MUST_BE_ZERO = TRUE must show 0
--   Statement 2  the territories rows, enriched
--
-- A territories row is (SOURCE, CLEAN_ID, ZIP_CODE, CHANNEL); territories.CHANNEL holds DIST_CH values
-- of that SOURCE.
--
-- Sales: read directly.  The union table's rows carry the same SOURCE and the same DIST_CH values, so
--   a territories row's sales are that SOURCE's ACTUAL_SALES_AMOUNT in (ZIP_CODE, DIST_CH = CHANNEL),
--   split into the holder's (SALES_WHOLESALER_TERRITORY_ID = CLEAN_ID) and everyone else's.
--
-- Opportunity: MM_OPP is non-null only on the rows of one SOURCE (the carrier).  Each SOURCE sells its
--   own set of PRODUCT_V2 values (those it has ACTUAL_SALES_AMOUNT > 0 in) and is given MM_OPP for
--   those products only.
--   - carrier SOURCE: MM_OPP on its own rows, in (ZIP_CODE, DIST_CH = CHANNEL).
--   - other SOURCE:   MM_OPP on the carrier's rows, in ZIP_CODE, for the carrier DIST_CH values that
--                     the crosswalk maps this DIST_CH to (OPP_DIST_CH).  No split, no sales weights.
--   OPPORTUNITY repeats on every holder of the same (SOURCE, ZIP_CODE, CHANNEL); OPPORTUNITY_SHARE
--   divides it by HOLDERS_SAME_SOURCE, so summing OPPORTUNITY_SHARE over rows does not double count.
--   Across SOURCEs nothing is divided: each SOURCE's row shows its own products' opportunity.
--
-- Territories rows whose CHANNEL is not a DIST_CH of that SOURCE in the union table are kept with
-- IN_SCOPE = FALSE and zeros (owner, 2026-10-19: those channels are outside the scope).

------------------------------------------------------------------------------------------------
-- Statement 0.  Template: create the crosswalk once, at work.  Its values name partners: keep it
-- there.  One row per (non-carrier SOURCE, its DIST_CH, a carrier DIST_CH it covers); a DIST_CH
-- covering several carrier DIST_CH values gets several rows.  The carrier SOURCE needs no rows.
------------------------------------------------------------------------------------------------
-- CREATE OR REPLACE TABLE ssdb_integration.lr_strategy.dist_ch_crosswalk (
--   SOURCE      VARCHAR,   -- the non-carrier SOURCE
--   DIST_CH     VARCHAR,   -- its DIST_CH value, as in the union table and territories.CHANNEL
--   OPP_DIST_CH VARCHAR    -- a carrier DIST_CH value whose MM_OPP it takes
-- );
-- INSERT INTO ssdb_integration.lr_strategy.dist_ch_crosswalk VALUES
--   ('<SOURCE>', '<DIST_CH>', '<carrier DIST_CH>'),
--   ('<SOURCE>', '<DIST_CH>', '<carrier DIST_CH>');

------------------------------------------------------------------------------------------------
-- Statement 1.  Checks.
------------------------------------------------------------------------------------------------
WITH
carrier AS (
  SELECT DISTINCT SOURCE FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys
  WHERE COALESCE(MM_OPP, 0) <> 0),
labels AS (
  SELECT SOURCE, 'source_' || DENSE_RANK() OVER (ORDER BY SOURCE) AS SOURCE_LABEL
  FROM (SELECT DISTINCT SOURCE FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys
        WHERE SOURCE IS NOT NULL) x),
scope AS (
  SELECT DISTINCT SOURCE, DIST_CH FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys),
products AS (
  SELECT DISTINCT SOURCE, PRODUCT_V2 FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys
  WHERE ACTUAL_SALES_AMOUNT > 0),
opp_products AS (
  SELECT PRODUCT_V2 FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys
  GROUP BY PRODUCT_V2 HAVING SUM(COALESCE(MM_OPP, 0)) > 0),
held AS (
  SELECT DISTINCT SOURCE, ZIP_CODE, CHANNEL FROM ssdb_integration.lr_strategy.territories)
SELECT 'territories rows' AS CHECK_NAME, COUNT(*) AS VALUE, FALSE AS MUST_BE_ZERO
FROM ssdb_integration.lr_strategy.territories
UNION ALL SELECT 'duplicate territories rows (SOURCE, CLEAN_ID, ZIP_CODE, CHANNEL)',
  COUNT(*) - COUNT(DISTINCT SOURCE || '|' || CLEAN_ID || '|' || ZIP_CODE || '|' || CHANNEL), FALSE
  FROM ssdb_integration.lr_strategy.territories
UNION ALL SELECT 'union rows with NULL SOURCE, ZIP_CODE, DIST_CH or PRODUCT_V2',
  COUNT_IF(SOURCE IS NULL OR ZIP_CODE IS NULL OR DIST_CH IS NULL OR PRODUCT_V2 IS NULL), FALSE
  FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys
UNION ALL SELECT 'SOURCEs whose rows carry MM_OPP, minus 1 (two carriers would need another rule)',
  ABS((SELECT COUNT(*) FROM carrier) - 1), TRUE
UNION ALL SELECT 'in-scope DIST_CH of a non-carrier SOURCE with no crosswalk row (would get no opportunity)',
  COUNT(*), TRUE FROM scope s
  WHERE s.SOURCE NOT IN (SELECT SOURCE FROM carrier)
    AND NOT EXISTS (SELECT 1 FROM ssdb_integration.lr_strategy.dist_ch_crosswalk x
                    WHERE x.SOURCE = s.SOURCE AND x.DIST_CH = s.DIST_CH)
UNION ALL SELECT 'crosswalk rows whose (SOURCE, DIST_CH) is not in the union table (typo?)',
  COUNT(*), TRUE FROM ssdb_integration.lr_strategy.dist_ch_crosswalk x
  WHERE NOT EXISTS (SELECT 1 FROM scope s WHERE s.SOURCE = x.SOURCE AND s.DIST_CH = x.DIST_CH)
UNION ALL SELECT 'crosswalk OPP_DIST_CH values that are not a carrier DIST_CH (typo?)',
  COUNT(*), TRUE FROM ssdb_integration.lr_strategy.dist_ch_crosswalk x
  WHERE NOT EXISTS (SELECT 1 FROM scope s JOIN carrier c ON c.SOURCE = s.SOURCE WHERE s.DIST_CH = x.OPP_DIST_CH)
UNION ALL SELECT 'carrier DIST_CH mapped from two DIST_CH of one SOURCE (its MM_OPP would count twice)',
  COUNT(*), TRUE FROM (SELECT SOURCE, OPP_DIST_CH FROM ssdb_integration.lr_strategy.dist_ch_crosswalk
                       GROUP BY SOURCE, OPP_DIST_CH HAVING COUNT(DISTINCT DIST_CH) > 1)
UNION ALL SELECT 'crosswalk pairs whose two DIST_CH share no CHANNEL (look at these)',
  COUNT(*), FALSE FROM ssdb_integration.lr_strategy.dist_ch_crosswalk x
  WHERE NOT EXISTS (
    SELECT 1 FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys a
    JOIN ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys b ON b.CHANNEL = a.CHANNEL
    WHERE a.SOURCE = x.SOURCE AND a.DIST_CH = x.DIST_CH
      AND b.SOURCE IN (SELECT SOURCE FROM carrier) AND b.DIST_CH = x.OPP_DIST_CH)
UNION ALL SELECT 'territories rows whose CHANNEL matches a DIST_CH only ignoring case/spaces',
  COUNT(*), TRUE FROM ssdb_integration.lr_strategy.territories t
  WHERE NOT EXISTS (SELECT 1 FROM scope s WHERE s.SOURCE = t.SOURCE AND s.DIST_CH = t.CHANNEL)
    AND EXISTS (SELECT 1 FROM scope s WHERE s.SOURCE = t.SOURCE
                AND UPPER(TRIM(s.DIST_CH)) = UPPER(TRIM(t.CHANNEL)))
UNION ALL SELECT 'territories rows out of scope (CHANNEL not a DIST_CH of that SOURCE)',
  COUNT(*), FALSE FROM ssdb_integration.lr_strategy.territories t
  WHERE NOT EXISTS (SELECT 1 FROM scope s WHERE s.SOURCE = t.SOURCE AND s.DIST_CH = t.CHANNEL)
UNION ALL SELECT 'PRODUCT_V2 values sold by ' || l.SOURCE_LABEL, COUNT(p.PRODUCT_V2), FALSE
  FROM labels l LEFT JOIN products p ON p.SOURCE = l.SOURCE GROUP BY l.SOURCE_LABEL
UNION ALL SELECT 'PRODUCT_V2 values sold by both SOURCEs', COUNT(*), FALSE
  FROM (SELECT PRODUCT_V2 FROM products GROUP BY PRODUCT_V2 HAVING COUNT(*) > 1)
UNION ALL SELECT 'pct of ' || l.SOURCE_LABEL || ' sales in PRODUCT_V2 values with no MM_OPP anywhere',
  ROUND(100 * SUM(CASE WHEN op.PRODUCT_V2 IS NULL THEN u.ACTUAL_SALES_AMOUNT ELSE 0 END)
        / NULLIF(SUM(u.ACTUAL_SALES_AMOUNT), 0), 2), FALSE
  FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys u
  JOIN labels l ON l.SOURCE = u.SOURCE
  LEFT JOIN opp_products op ON op.PRODUCT_V2 = u.PRODUCT_V2
  GROUP BY l.SOURCE_LABEL
UNION ALL SELECT 'pct of carrier MM_OPP in carrier DIST_CH values no crosswalk row reaches',
  ROUND(100 * SUM(CASE WHEN x.OPP_DIST_CH IS NULL THEN u.MM_OPP ELSE 0 END) / NULLIF(SUM(u.MM_OPP), 0), 2), FALSE
  FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys u
  JOIN carrier c ON c.SOURCE = u.SOURCE
  LEFT JOIN (SELECT DISTINCT OPP_DIST_CH FROM ssdb_integration.lr_strategy.dist_ch_crosswalk) x
    ON x.OPP_DIST_CH = u.DIST_CH
UNION ALL SELECT 'pct of ' || l.SOURCE_LABEL || ' sales in (ZIP_CODE, DIST_CH) no territories row holds',
  ROUND(100 * SUM(CASE WHEN h.SOURCE IS NULL THEN u.ACTUAL_SALES_AMOUNT ELSE 0 END)
        / NULLIF(SUM(u.ACTUAL_SALES_AMOUNT), 0), 2), FALSE
  FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys u
  JOIN labels l ON l.SOURCE = u.SOURCE
  LEFT JOIN held h ON h.SOURCE = u.SOURCE AND h.ZIP_CODE = u.ZIP_CODE AND h.CHANNEL = u.DIST_CH
  GROUP BY l.SOURCE_LABEL;

------------------------------------------------------------------------------------------------
-- Statement 2.  The territories rows, enriched.  To keep it, put this in front of WITH:
--   CREATE OR REPLACE TABLE ssdb_integration.lr_strategy.territories_enriched AS
------------------------------------------------------------------------------------------------
WITH
carrier AS (         -- the SOURCE whose rows carry MM_OPP
  SELECT DISTINCT SOURCE FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys
  WHERE COALESCE(MM_OPP, 0) <> 0),

products AS (        -- each SOURCE's product set: the PRODUCT_V2 values it has sales in
  SELECT DISTINCT SOURCE, PRODUCT_V2 FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys
  WHERE ACTUAL_SALES_AMOUNT > 0),

opp_map AS (         -- which carrier DIST_CH values each (SOURCE, DIST_CH) takes MM_OPP from
  SELECT DISTINCT u.SOURCE, u.DIST_CH, u.DIST_CH AS OPP_DIST_CH          -- the carrier: itself
  FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys u
  JOIN carrier c ON c.SOURCE = u.SOURCE
  UNION
  SELECT SOURCE, DIST_CH, OPP_DIST_CH                                    -- everyone else: the crosswalk
  FROM ssdb_integration.lr_strategy.dist_ch_crosswalk),

carrier_opp AS (     -- the carrier's MM_OPP per (ZIP_CODE, DIST_CH, PRODUCT_V2)
  SELECT u.ZIP_CODE, u.DIST_CH, u.PRODUCT_V2, SUM(u.MM_OPP) AS MM_OPP
  FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys u
  JOIN carrier c ON c.SOURCE = u.SOURCE
  GROUP BY u.ZIP_CODE, u.DIST_CH, u.PRODUCT_V2),

opp_cell AS (        -- per (SOURCE, ZIP_CODE, DIST_CH): MM_OPP of its mapped carrier DIST_CH, its own products
  SELECT m.SOURCE, o.ZIP_CODE, m.DIST_CH, SUM(o.MM_OPP) AS MM_OPP
  FROM opp_map m
  JOIN carrier_opp o ON o.DIST_CH = m.OPP_DIST_CH
  JOIN products p    ON p.SOURCE = m.SOURCE AND p.PRODUCT_V2 = o.PRODUCT_V2
  GROUP BY m.SOURCE, o.ZIP_CODE, m.DIST_CH),

scope AS (           -- (SOURCE, DIST_CH) present in the union table
  SELECT DISTINCT SOURCE, DIST_CH FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys),

sales_cell AS (      -- per (SOURCE, ZIP_CODE, DIST_CH): all sales
  SELECT SOURCE, ZIP_CODE, DIST_CH, SUM(ACTUAL_SALES_AMOUNT) AS ACTUAL_SALES_AMOUNT
  FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys
  GROUP BY SOURCE, ZIP_CODE, DIST_CH),

sales_seller AS (    -- per (SOURCE, ZIP_CODE, DIST_CH, SALES_WHOLESALER_TERRITORY_ID)
  SELECT SOURCE, ZIP_CODE, DIST_CH, SALES_WHOLESALER_TERRITORY_ID, SUM(ACTUAL_SALES_AMOUNT) AS ACTUAL_SALES_AMOUNT
  FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys
  WHERE SALES_WHOLESALER_TERRITORY_ID IS NOT NULL
  GROUP BY SOURCE, ZIP_CODE, DIST_CH, SALES_WHOLESALER_TERRITORY_ID),

holders AS (         -- holders of each (SOURCE, ZIP_CODE, CHANNEL) in territories
  SELECT SOURCE, ZIP_CODE, CHANNEL, COUNT(DISTINCT CLEAN_ID) AS HOLDERS_SAME_SOURCE
  FROM ssdb_integration.lr_strategy.territories
  GROUP BY SOURCE, ZIP_CODE, CHANNEL)

SELECT t.*,
       sc.SOURCE IS NOT NULL                                                   AS IN_SCOPE,
       COALESCE(h.HOLDERS_SAME_SOURCE, 0)                                      AS HOLDERS_SAME_SOURCE,
       COALESCE(o.MM_OPP, 0)                                                   AS OPPORTUNITY,
       COALESCE(o.MM_OPP, 0) / NULLIF(h.HOLDERS_SAME_SOURCE, 0)                AS OPPORTUNITY_SHARE,
       COALESCE(ss.ACTUAL_SALES_AMOUNT, 0)                                     AS SALES_BY_HOLDER,
       COALESCE(s.ACTUAL_SALES_AMOUNT, 0) - COALESCE(ss.ACTUAL_SALES_AMOUNT, 0) AS SALES_BY_OTHERS,
       COALESCE(s.ACTUAL_SALES_AMOUNT, 0)                                      AS SALES_TOTAL
FROM ssdb_integration.lr_strategy.territories t
LEFT JOIN holders h
  ON h.SOURCE = t.SOURCE AND h.ZIP_CODE = t.ZIP_CODE AND h.CHANNEL = t.CHANNEL
LEFT JOIN scope sc
  ON sc.SOURCE = t.SOURCE AND sc.DIST_CH = t.CHANNEL
LEFT JOIN opp_cell o
  ON o.SOURCE = t.SOURCE AND o.ZIP_CODE = t.ZIP_CODE AND o.DIST_CH = t.CHANNEL
LEFT JOIN sales_cell s
  ON s.SOURCE = t.SOURCE AND s.ZIP_CODE = t.ZIP_CODE AND s.DIST_CH = t.CHANNEL
LEFT JOIN sales_seller ss
  ON ss.SOURCE = t.SOURCE AND ss.ZIP_CODE = t.ZIP_CODE AND ss.DIST_CH = t.CHANNEL
 AND ss.SALES_WHOLESALER_TERRITORY_ID = t.CLEAN_ID
ORDER BY t.SOURCE, t.CLEAN_ID, t.ZIP_CODE, t.CHANNEL;
