-- The territories table with opportunity and sales appended, by target channel: one output row per
-- territories row and target CHANNEL its DIST_CH maps to (out-of-scope rows: one row, CHANNEL NULL).
-- Reads only the two source tables; creates nothing.  Two statements:
--   Statement 1  checks: every row with MUST_BE_ZERO = TRUE must show 0
--   Statement 2  the territories rows, enriched
--
-- A territories row is (SOURCE, CLEAN_ID, ZIP_CODE, CHANNEL); territories.CHANNEL holds DIST_CH values
-- of that SOURCE.  In the output that value is in DIST_CH, and CHANNEL is the target channel, as in
-- the union table.  The union table maps DIST_CH -> CHANNEL per SOURCE; DIST_CH values do not
-- correspond across SOURCEs (owner, 2026-10-20), so CHANNEL, ZIP_CODE and PRODUCT_V2 are all they share.
--
-- Sales: read directly.  The union table's rows carry the same SOURCE and the same DIST_CH values, so
--   a territories row's sales are that SOURCE's ACTUAL_SALES_AMOUNT in (ZIP_CODE, DIST_CH, CHANNEL),
--   split into the holder's (SALES_WHOLESALER_TERRITORY_ID = CLEAN_ID) and everyone else's.
--
-- Opportunity: MM_OPP is non-null only on the rows of one SOURCE (the carrier).  Each SOURCE sells its
--   own set of PRODUCT_V2 values (those it has ACTUAL_SALES_AMOUNT > 0 in) and gets MM_OPP for those only.
--   - carrier SOURCE (OPPORTUNITY_METHOD 'exact'): MM_OPP on its own rows, (ZIP_CODE, DIST_CH, CHANNEL).
--   - other SOURCE (OPPORTUNITY_METHOD 'sales_mix_held'): the carrier's MM_OPP per (ZIP_CODE, CHANNEL),
--     for this SOURCE's products, divided among this SOURCE's DIST_CH values held in that ZIP_CODE
--     by each DIST_CH's national share of this SOURCE's sales in that CHANNEL, rescaled over the held
--     ones (equal shares if none of them has sales in that CHANNEL).  Every (ZIP_CODE, CHANNEL) a
--     SOURCE holds is then charged once.
--     Calibrated on the carrier, where the exact figure is known (17_split_rule_calibration.sql,
--     owner's run 2026-10-20): 66 people, median error 2.2%, 16.7% off by over 10%, 1.5% by over 25%,
--     correlation 0.99.  It uses the SOURCE's own sales to size each DIST_CH's share: one national
--     share per DIST_CH, so no one's own sales move their own opportunity, but a DIST_CH that sells
--     weakly overall is given less opportunity.
--   OPPORTUNITY repeats on every holder of the same (SOURCE, ZIP_CODE, DIST_CH); OPPORTUNITY_SHARE
--   divides it by HOLDERS_SAME_SOURCE, so summing OPPORTUNITY_SHARE over rows does not double count.
--   Across SOURCEs nothing is divided: each SOURCE's row shows its own products' opportunity.
--
-- Territories rows whose CHANNEL is not a DIST_CH of that SOURCE in the union table are kept with
-- IN_SCOPE = FALSE, CHANNEL NULL and zeros (owner, 2026-10-19: those channels are outside the scope).

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
pairs AS (
  SELECT SOURCE, DIST_CH, CHANNEL,
         SUM(CASE WHEN ACTUAL_SALES_AMOUNT > 0 THEN ACTUAL_SALES_AMOUNT ELSE 0 END) AS POS_SALES
  FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys
  GROUP BY SOURCE, DIST_CH, CHANNEL),
held AS (
  SELECT DISTINCT SOURCE, ZIP_CODE, CHANNEL FROM ssdb_integration.lr_strategy.territories)
SELECT 'territories rows' AS CHECK_NAME, COUNT(*) AS VALUE, FALSE AS MUST_BE_ZERO
FROM ssdb_integration.lr_strategy.territories
UNION ALL SELECT 'duplicate territories rows (SOURCE, CLEAN_ID, ZIP_CODE, CHANNEL)',
  COUNT(*) - COUNT(DISTINCT SOURCE || '|' || CLEAN_ID || '|' || ZIP_CODE || '|' || CHANNEL), FALSE
  FROM ssdb_integration.lr_strategy.territories
UNION ALL SELECT 'union rows with NULL SOURCE, ZIP_CODE, DIST_CH, CHANNEL or PRODUCT_V2',
  COUNT_IF(SOURCE IS NULL OR ZIP_CODE IS NULL OR DIST_CH IS NULL OR CHANNEL IS NULL OR PRODUCT_V2 IS NULL), FALSE
  FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys
UNION ALL SELECT 'SOURCEs whose rows carry MM_OPP, minus 1 (two carriers would need another rule)',
  ABS((SELECT COUNT(*) FROM carrier) - 1), TRUE
UNION ALL SELECT '(ZIP_CODE, CHANNEL, PRODUCT_V2) with MM_OPP on both SOURCEs (would count twice)',
  COUNT(*), TRUE
  FROM (SELECT ZIP_CODE, CHANNEL, PRODUCT_V2 FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys
        WHERE COALESCE(MM_OPP, 0) <> 0 GROUP BY 1, 2, 3 HAVING COUNT(DISTINCT SOURCE) > 1)
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
UNION ALL SELECT 'non-carrier (SOURCE, CHANNEL) with no sales in any DIST_CH (falls back to equal shares)',
  COUNT(*), FALSE
  FROM (SELECT SOURCE, CHANNEL FROM pairs WHERE SOURCE NOT IN (SELECT SOURCE FROM carrier)
        GROUP BY SOURCE, CHANNEL HAVING SUM(POS_SALES) = 0)
UNION ALL SELECT 'DIST_CH -> CHANNEL pairs of ' || l.SOURCE_LABEL || ' holding under 1% of the DIST_CH''s sales',
  COUNT_IF(p.POS_SALES < 0.01 * x.TOT), FALSE
  FROM pairs p JOIN labels l ON l.SOURCE = p.SOURCE
  JOIN (SELECT SOURCE, DIST_CH, SUM(POS_SALES) AS TOT FROM pairs GROUP BY 1, 2) x
    ON x.SOURCE = p.SOURCE AND x.DIST_CH = p.DIST_CH
  GROUP BY l.SOURCE_LABEL
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

-- carrier SOURCE: exact
opp_exact AS (       -- per (SOURCE, ZIP_CODE, DIST_CH, CHANNEL): its own MM_OPP, its own products
  SELECT u.SOURCE, u.ZIP_CODE, u.DIST_CH, u.CHANNEL, SUM(u.MM_OPP) AS MM_OPP
  FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys u
  JOIN carrier c  ON c.SOURCE = u.SOURCE
  JOIN products p ON p.SOURCE = u.SOURCE AND p.PRODUCT_V2 = u.PRODUCT_V2
  GROUP BY u.SOURCE, u.ZIP_CODE, u.DIST_CH, u.CHANNEL),

-- other SOURCE: sales_mix_held
pairs AS (           -- its DIST_CH -> CHANNEL pairs, with positive sales in each
  SELECT u.SOURCE, u.DIST_CH, u.CHANNEL,
         SUM(CASE WHEN u.ACTUAL_SALES_AMOUNT > 0 THEN u.ACTUAL_SALES_AMOUNT ELSE 0 END) AS POS_SALES
  FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys u
  WHERE u.SOURCE NOT IN (SELECT SOURCE FROM carrier)
  GROUP BY u.SOURCE, u.DIST_CH, u.CHANNEL),

held AS (            -- (SOURCE, ZIP_CODE, DIST_CH, CHANNEL) held in territories
  SELECT DISTINCT t.SOURCE, t.ZIP_CODE, p.DIST_CH, p.CHANNEL, p.POS_SALES
  FROM ssdb_integration.lr_strategy.territories t
  JOIN pairs p ON p.SOURCE = t.SOURCE AND p.DIST_CH = t.CHANNEL),

held_w AS (          -- each held DIST_CH's share of the CHANNEL in that ZIP_CODE
  SELECT SOURCE, ZIP_CODE, DIST_CH, CHANNEL,
         CASE WHEN SUM(POS_SALES) OVER (PARTITION BY SOURCE, ZIP_CODE, CHANNEL) > 0
              THEN POS_SALES / SUM(POS_SALES) OVER (PARTITION BY SOURCE, ZIP_CODE, CHANNEL)
              ELSE 1.0 / COUNT(*) OVER (PARTITION BY SOURCE, ZIP_CODE, CHANNEL) END AS W
  FROM held),

channel_opp AS (     -- the carrier's MM_OPP per (ZIP_CODE, CHANNEL), for each other SOURCE's products
  SELECT p.SOURCE, u.ZIP_CODE, u.CHANNEL, SUM(u.MM_OPP) AS MM_OPP
  FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys u
  JOIN carrier c  ON c.SOURCE = u.SOURCE
  JOIN products p ON p.PRODUCT_V2 = u.PRODUCT_V2 AND p.SOURCE NOT IN (SELECT SOURCE FROM carrier)
  GROUP BY p.SOURCE, u.ZIP_CODE, u.CHANNEL),

opp_mix AS (         -- per (SOURCE, ZIP_CODE, DIST_CH, CHANNEL)
  SELECT w.SOURCE, w.ZIP_CODE, w.DIST_CH, w.CHANNEL, SUM(o.MM_OPP * w.W) AS MM_OPP
  FROM held_w w
  JOIN channel_opp o ON o.SOURCE = w.SOURCE AND o.ZIP_CODE = w.ZIP_CODE AND o.CHANNEL = w.CHANNEL
  GROUP BY w.SOURCE, w.ZIP_CODE, w.DIST_CH, w.CHANNEL),

opp_cell AS (
  SELECT SOURCE, ZIP_CODE, DIST_CH, CHANNEL, MM_OPP FROM opp_exact
  UNION ALL
  SELECT SOURCE, ZIP_CODE, DIST_CH, CHANNEL, MM_OPP FROM opp_mix),

ch_map AS (          -- (SOURCE, DIST_CH) -> target CHANNEL, as the union table pairs them
  SELECT DISTINCT SOURCE, DIST_CH, CHANNEL FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys),

sales_cell AS (      -- per (SOURCE, ZIP_CODE, DIST_CH, CHANNEL): all sales
  SELECT SOURCE, ZIP_CODE, DIST_CH, CHANNEL, SUM(ACTUAL_SALES_AMOUNT) AS ACTUAL_SALES_AMOUNT
  FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys
  GROUP BY SOURCE, ZIP_CODE, DIST_CH, CHANNEL),

sales_seller AS (    -- per (SOURCE, ZIP_CODE, DIST_CH, CHANNEL, SALES_WHOLESALER_TERRITORY_ID)
  SELECT SOURCE, ZIP_CODE, DIST_CH, CHANNEL, SALES_WHOLESALER_TERRITORY_ID,
         SUM(ACTUAL_SALES_AMOUNT) AS ACTUAL_SALES_AMOUNT
  FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys
  WHERE SALES_WHOLESALER_TERRITORY_ID IS NOT NULL
  GROUP BY SOURCE, ZIP_CODE, DIST_CH, CHANNEL, SALES_WHOLESALER_TERRITORY_ID),

holders AS (         -- holders of each (SOURCE, ZIP_CODE, DIST_CH) in territories (territories.CHANNEL = DIST_CH)
  SELECT SOURCE, ZIP_CODE, CHANNEL, COUNT(DISTINCT CLEAN_ID) AS HOLDERS_SAME_SOURCE
  FROM ssdb_integration.lr_strategy.territories
  GROUP BY SOURCE, ZIP_CODE, CHANNEL)

SELECT t.SOURCE, t.NAME, t.ZIP_CODE, t.STATE,
       t.CHANNEL                                                               AS DIST_CH,
       m.CHANNEL,                                                              -- the target channel
       t.CLEAN_NAME, t.CLEAN_ID,
       m.SOURCE IS NOT NULL                                                    AS IN_SCOPE,
       COALESCE(h.HOLDERS_SAME_SOURCE, 0)                                      AS HOLDERS_SAME_SOURCE,
       CASE WHEN m.SOURCE IS NULL THEN NULL
            WHEN t.SOURCE IN (SELECT SOURCE FROM carrier) THEN 'exact'
            ELSE 'sales_mix_held' END                                          AS OPPORTUNITY_METHOD,
       COALESCE(o.MM_OPP, 0)                                                   AS OPPORTUNITY,
       COALESCE(o.MM_OPP, 0) / NULLIF(h.HOLDERS_SAME_SOURCE, 0)                AS OPPORTUNITY_SHARE,
       COALESCE(ss.ACTUAL_SALES_AMOUNT, 0)                                     AS SALES_BY_HOLDER,
       COALESCE(s.ACTUAL_SALES_AMOUNT, 0) - COALESCE(ss.ACTUAL_SALES_AMOUNT, 0) AS SALES_BY_OTHERS,
       COALESCE(s.ACTUAL_SALES_AMOUNT, 0)                                      AS SALES_TOTAL
FROM ssdb_integration.lr_strategy.territories t
LEFT JOIN ch_map m
  ON m.SOURCE = t.SOURCE AND m.DIST_CH = t.CHANNEL
LEFT JOIN holders h
  ON h.SOURCE = t.SOURCE AND h.ZIP_CODE = t.ZIP_CODE AND h.CHANNEL = t.CHANNEL
LEFT JOIN opp_cell o
  ON o.SOURCE = t.SOURCE AND o.ZIP_CODE = t.ZIP_CODE AND o.DIST_CH = t.CHANNEL AND o.CHANNEL = m.CHANNEL
LEFT JOIN sales_cell s
  ON s.SOURCE = t.SOURCE AND s.ZIP_CODE = t.ZIP_CODE AND s.DIST_CH = t.CHANNEL AND s.CHANNEL = m.CHANNEL
LEFT JOIN sales_seller ss
  ON ss.SOURCE = t.SOURCE AND ss.ZIP_CODE = t.ZIP_CODE AND ss.DIST_CH = t.CHANNEL AND ss.CHANNEL = m.CHANNEL
 AND ss.SALES_WHOLESALER_TERRITORY_ID = t.CLEAN_ID
ORDER BY t.SOURCE, t.CLEAN_ID, t.ZIP_CODE, t.CHANNEL, m.CHANNEL;
