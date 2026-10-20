-- The territories table with opportunity and sales appended: one output row per territories row.
-- Reads only the two source tables; creates nothing.  Two statements:
--   Statement 1  checks: every row with must_be_zero = TRUE must show 0
--   Statement 2  the territories rows, enriched
--
-- A territories row is (SOURCE, CLEAN_ID, ZIP_CODE, CHANNEL), CHANNEL in that firm's own DIST_CH names.
--
-- Sales: read directly.  The union table's rows carry the same firm and the same DIST_CH names, so a
--   territory row's sales are the firm's sales in (ZIP_CODE, DIST_CH = CHANNEL): by the holder
--   (SALES_WHOLESALER_TERRITORY_ID = CLEAN_ID) and by anyone else.
--
-- Opportunity: only one firm's rows carry MM_OPP, and the firms sell different product sets
--   (a firm's product set = the PRODUCT_V2 values it has sales in).  The two firms share only the
--   target CHANNEL and PRODUCT_V2, so:
--   A. the firm whose rows carry MM_OPP: its own rows, its own products, by its own DIST_CH, per zip.
--   B. a firm whose rows do not: opportunity per (zip, target channel, product) from whichever rows
--      carry it, for that firm's products only, shared out among the firm's DIST_CHs that map to the
--      target channel in proportion to the firm's own sales in each (DIST_CH, target channel) pair.
--      Each target channel's opportunity is then counted once per firm, and a pair that holds a
--      sliver of the firm's sales gets a sliver of the opportunity, not all of it.
--   Two holders of one (firm, zip, CHANNEL) each show the cell's opportunity; opportunity_share
--   divides it by holders_same_firm, so summing opportunity_share over rows does not double count.
--   Across firms nothing is divided: each firm's row shows that firm's own opportunity.
--
-- Territory rows in channels absent from the union table are kept, in_scope = FALSE, with zeros
-- (owner, 2026-10-19: those channels are outside the scope).

------------------------------------------------------------------------------------------------
-- Statement 1.  Checks.
------------------------------------------------------------------------------------------------
WITH
src AS (
  SELECT ZIP_CODE AS zip_code, SOURCE AS firm, DIST_CH AS original_channel, CHANNEL AS channel,
         PRODUCT_V2 AS product, MM_OPP AS opp, ACTUAL_SALES_AMOUNT AS sales,
         SALES_WHOLESALER_TERRITORY_ID AS seller
  FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys),
terr AS (
  SELECT SOURCE AS firm, CLEAN_ID AS wholesaler, ZIP_CODE AS zip_code, CHANNEL AS original_channel
  FROM ssdb_integration.lr_strategy.territories),
f AS (
  SELECT firm, 'firm_' || DENSE_RANK() OVER (ORDER BY firm) AS firm_label
  FROM (SELECT DISTINCT firm FROM src WHERE firm IS NOT NULL) x),
scope AS (SELECT DISTINCT firm, original_channel FROM src),
firm_products AS (SELECT DISTINCT firm, product FROM src WHERE sales > 0),
opp_carriers AS (SELECT DISTINCT firm FROM src WHERE COALESCE(opp, 0) <> 0),
opp_products AS (SELECT product FROM src GROUP BY product HAVING SUM(COALESCE(opp, 0)) > 0),
pairs AS (
  SELECT firm, original_channel, channel, SUM(CASE WHEN sales > 0 THEN sales ELSE 0 END) AS pos_sales
  FROM src GROUP BY firm, original_channel, channel),
weights AS (
  SELECT firm, channel,
         SUM(CASE WHEN tot > 0 THEN pos_sales / tot ELSE 1.0 / n END) AS w_sum
  FROM (SELECT p.*, SUM(pos_sales) OVER (PARTITION BY firm, channel) AS tot,
               COUNT(*) OVER (PARTITION BY firm, channel) AS n FROM pairs p) x
  GROUP BY firm, channel),
held AS (SELECT DISTINCT firm, zip_code, original_channel FROM terr)
SELECT 'territories rows' AS check_name, COUNT(*) AS value, FALSE AS must_be_zero FROM terr
UNION ALL SELECT 'duplicate territories rows (SOURCE, CLEAN_ID, ZIP_CODE, CHANNEL)',
  COUNT(*) - COUNT(DISTINCT firm || '|' || wholesaler || '|' || zip_code || '|' || original_channel), FALSE FROM terr
UNION ALL SELECT 'rows with NULL SOURCE, DIST_CH, CHANNEL or PRODUCT_V2 (union table)',
  COUNT_IF(firm IS NULL OR original_channel IS NULL OR channel IS NULL OR product IS NULL), TRUE FROM src
UNION ALL SELECT 'firms whose rows carry MM_OPP (expect 1)', COUNT(*), FALSE FROM opp_carriers
UNION ALL SELECT '(zip, channel, product) with MM_OPP on both firms (would count twice)',
  COUNT(*), TRUE FROM (SELECT zip_code, channel, product FROM src WHERE COALESCE(opp, 0) <> 0
                       GROUP BY 1, 2, 3 HAVING COUNT(DISTINCT firm) > 1)
UNION ALL SELECT 'territories rows whose CHANNEL matches DIST_CH only ignoring case/spaces',
  COUNT(*), TRUE FROM terr t
  WHERE NOT EXISTS (SELECT 1 FROM scope s WHERE s.firm = t.firm AND s.original_channel = t.original_channel)
    AND EXISTS (SELECT 1 FROM scope s WHERE s.firm = t.firm
                AND UPPER(TRIM(s.original_channel)) = UPPER(TRIM(t.original_channel)))
UNION ALL SELECT 'territories rows out of scope (CHANNEL absent from the union table)',
  COUNT(*), FALSE FROM terr t
  WHERE NOT EXISTS (SELECT 1 FROM scope s WHERE s.firm = t.firm AND s.original_channel = t.original_channel)
UNION ALL SELECT '(firm, target channel) whose DIST_CH weights do not sum to 1',
  COUNT_IF(ABS(w_sum - 1) > 1e-9), TRUE FROM weights
UNION ALL SELECT 'products sold by ' || f.firm_label, COUNT(fp.product), FALSE
  FROM f LEFT JOIN firm_products fp ON fp.firm = f.firm GROUP BY f.firm_label
UNION ALL SELECT 'products sold by both firms', COUNT(*), FALSE
  FROM (SELECT product FROM firm_products GROUP BY product HAVING COUNT(*) > 1)
UNION ALL SELECT 'pct of ' || f.firm_label || ' sales in products with no MM_OPP anywhere',
  ROUND(100 * SUM(CASE WHEN op.product IS NULL THEN s.sales ELSE 0 END) / NULLIF(SUM(s.sales), 0), 2), FALSE
  FROM src s JOIN f ON f.firm = s.firm LEFT JOIN opp_products op ON op.product = s.product
  GROUP BY f.firm_label
UNION ALL SELECT 'pct of ' || f.firm_label || ' sales in (zip, DIST_CH) cells no territories row holds',
  ROUND(100 * SUM(CASE WHEN h.firm IS NULL THEN s.sales ELSE 0 END) / NULLIF(SUM(s.sales), 0), 2), FALSE
  FROM src s JOIN f ON f.firm = s.firm
  LEFT JOIN held h ON h.firm = s.firm AND h.zip_code = s.zip_code AND h.original_channel = s.original_channel
  GROUP BY f.firm_label
UNION ALL SELECT 'DIST_CH -> target channel pairs of ' || f.firm_label || ' holding under 1% of the DIST_CH''s sales',
  COUNT_IF(p.pos_sales < 0.01 * x.tot), FALSE
  FROM pairs p JOIN f ON f.firm = p.firm
  JOIN (SELECT firm, original_channel, SUM(pos_sales) AS tot FROM pairs GROUP BY 1, 2) x
    ON x.firm = p.firm AND x.original_channel = p.original_channel
  GROUP BY f.firm_label;

------------------------------------------------------------------------------------------------
-- Statement 2.  The territories rows, enriched.  To keep it, put this in front of WITH:
--   CREATE OR REPLACE TABLE ssdb_integration.lr_strategy.territories_enriched AS
------------------------------------------------------------------------------------------------
WITH
src AS (
  SELECT ZIP_CODE AS zip_code, SOURCE AS firm, DIST_CH AS original_channel, CHANNEL AS channel,
         PRODUCT_V2 AS product, MM_OPP AS opp, ACTUAL_SALES_AMOUNT AS sales,
         SALES_WHOLESALER_TERRITORY_ID AS seller
  FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys),

firm_products AS (   -- each firm's product set: what it has sales in
  SELECT DISTINCT firm, product FROM src WHERE sales > 0),

opp_carriers AS (    -- the firm(s) whose rows carry MM_OPP
  SELECT DISTINCT firm FROM src WHERE COALESCE(opp, 0) <> 0),

-- A. a firm whose rows carry MM_OPP: its own rows, its own products, by its own DIST_CH
opp_direct AS (
  SELECT s.firm, s.zip_code, s.original_channel, SUM(s.opp) AS opp
  FROM src s
  JOIN opp_carriers c   ON c.firm = s.firm
  JOIN firm_products fp ON fp.firm = s.firm AND fp.product = s.product
  GROUP BY s.firm, s.zip_code, s.original_channel),

-- B. a firm whose rows do not: (zip, target channel, product) opportunity, shared out over its DIST_CHs
opp_zcp AS (
  SELECT zip_code, channel, product, SUM(opp) AS opp
  FROM src GROUP BY zip_code, channel, product
  HAVING SUM(opp) <> 0),

pairs AS (           -- each firm's DIST_CH -> target channel pairs, with its positive sales in each
  SELECT firm, original_channel, channel, SUM(CASE WHEN sales > 0 THEN sales ELSE 0 END) AS pos_sales
  FROM src GROUP BY firm, original_channel, channel),

weights AS (         -- share of a target channel's opportunity each DIST_CH takes; equal if no sales
  SELECT firm, original_channel, channel,
         CASE WHEN SUM(pos_sales) OVER (PARTITION BY firm, channel) > 0
              THEN pos_sales / SUM(pos_sales) OVER (PARTITION BY firm, channel)
              ELSE 1.0 / COUNT(*) OVER (PARTITION BY firm, channel) END AS w
  FROM pairs
  WHERE firm NOT IN (SELECT firm FROM opp_carriers)),

opp_mapped AS (
  SELECT w.firm, o.zip_code, w.original_channel, SUM(w.w * o.opp) AS opp
  FROM weights w
  JOIN firm_products fp ON fp.firm = w.firm
  JOIN opp_zcp o        ON o.channel = w.channel AND o.product = fp.product
  GROUP BY w.firm, o.zip_code, w.original_channel),

opp_cell AS (        -- per (firm, zip, DIST_CH)
  SELECT * FROM opp_direct
  UNION ALL
  SELECT * FROM opp_mapped),

scope AS (           -- (firm, DIST_CH) present in the union table, with how many target channels
  SELECT firm, original_channel, COUNT(DISTINCT channel) AS n_target_channels
  FROM src GROUP BY firm, original_channel),

sales_cell AS (      -- per (firm, zip, DIST_CH): all sales
  SELECT firm, zip_code, original_channel, SUM(sales) AS sales
  FROM src GROUP BY firm, zip_code, original_channel),

sales_seller AS (    -- per (firm, zip, DIST_CH, seller)
  SELECT firm, zip_code, original_channel, seller, SUM(sales) AS sales
  FROM src WHERE seller IS NOT NULL
  GROUP BY firm, zip_code, original_channel, seller),

holders AS (         -- holders of each (firm, zip, CHANNEL) in the territories table
  SELECT SOURCE, ZIP_CODE, CHANNEL, COUNT(DISTINCT CLEAN_ID) AS holders_same_firm
  FROM ssdb_integration.lr_strategy.territories
  GROUP BY SOURCE, ZIP_CODE, CHANNEL)

SELECT t.*,
       sc.firm IS NOT NULL                                   AS in_scope,
       COALESCE(sc.n_target_channels, 0)                     AS n_target_channels,
       COALESCE(h.holders_same_firm, 0)                      AS holders_same_firm,
       COALESCE(o.opp, 0)                                    AS opportunity,
       COALESCE(o.opp, 0) / NULLIF(h.holders_same_firm, 0)   AS opportunity_share,
       COALESCE(sh.sales, 0)                                 AS sales_by_holder,
       COALESCE(s.sales, 0) - COALESCE(sh.sales, 0)          AS sales_by_others,
       COALESCE(s.sales, 0)                                  AS sales_total
FROM ssdb_integration.lr_strategy.territories t
LEFT JOIN holders h
  ON h.SOURCE = t.SOURCE AND h.ZIP_CODE = t.ZIP_CODE AND h.CHANNEL = t.CHANNEL
LEFT JOIN scope sc
  ON sc.firm = t.SOURCE AND sc.original_channel = t.CHANNEL
LEFT JOIN opp_cell o
  ON o.firm = t.SOURCE AND o.zip_code = t.ZIP_CODE AND o.original_channel = t.CHANNEL
LEFT JOIN sales_cell s
  ON s.firm = t.SOURCE AND s.zip_code = t.ZIP_CODE AND s.original_channel = t.CHANNEL
LEFT JOIN sales_seller sh
  ON sh.firm = t.SOURCE AND sh.zip_code = t.ZIP_CODE AND sh.original_channel = t.CHANNEL
 AND sh.seller = t.CLEAN_ID
ORDER BY t.SOURCE, t.CLEAN_ID, t.ZIP_CODE, t.CHANNEL;
