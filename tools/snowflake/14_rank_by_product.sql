-- Wholesaler ranking controlled for product: each firm is charged only for the opportunity in the
-- products it sells, against each product's own market rate.  Reads only the two source tables;
-- creates nothing.  Two statements:
--   Statement 1  checks: every row with must_be_zero = TRUE must show 0
--   Statement 2  the ranking
--
--   product set   = the PRODUCT_V2 values a firm has sales in
--   territory     = territories rows, expanded from each firm's DIST_CH to target CHANNEL through the
--                   pairs the source table holds (extra channels are out of scope, owner 2026-10-19)
--   rate          = per target channel x product: credited sales / held opportunity, where held
--                   opportunity is the opportunity in cells held by someone whose firm sells the
--                   product.  Over all opportunity, a product one firm sells would be divided by
--                   the opportunity in zips that firm does not cover, and its holders would read high.
--   expected      = per held (zip, channel, product in the holder's firm's set):
--                   opportunity / holders whose firm sells that product x rate
--   credited      = sales inside + out_credit x sales outside (owner 2026-10-19: outside included)
--   unmeasured    = sales in a (channel, product) with no held opportunity: neither credited nor
--                   expected, reported in sales_unmeasured
--   perf_index    = (credited + prior) / (expected + prior) per channel; index_overall over all
-- Vacancy IDs, if any appear as sellers, go in `filler`.

------------------------------------------------------------------------------------------------
-- Statement 1.  Checks.
------------------------------------------------------------------------------------------------
WITH
src AS (
  SELECT ZIP_CODE                      AS zip_code,
         SOURCE                        AS firm,
         DIST_CH                       AS original_channel,
         CHANNEL                       AS channel,
         PRODUCT_V2                    AS product,
         MM_OPP                        AS opp,
         ACTUAL_SALES_AMOUNT           AS sales,
         SALES_WHOLESALER_TERRITORY_ID AS seller,
         FISCAL_YR                     AS fiscal_yr
  FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys),
terr_src AS (
  SELECT DISTINCT SOURCE AS firm, CLEAN_ID AS wholesaler, ZIP_CODE AS zip_code, CHANNEL AS original_channel
  FROM ssdb_integration.lr_strategy.territories),
ch AS (SELECT DISTINCT firm, original_channel FROM src),
f AS (
  SELECT firm, 'firm_' || DENSE_RANK() OVER (ORDER BY firm) AS firm_label
  FROM (SELECT DISTINCT firm FROM src WHERE firm IS NOT NULL) x),
fp AS (SELECT DISTINCT firm, product FROM src WHERE sales > 0),
cp AS (SELECT channel, product FROM src GROUP BY 1, 2 HAVING SUM(opp) > 0)
SELECT 'source rows' AS check_name, COUNT(*) AS value, FALSE AS must_be_zero FROM src
UNION ALL SELECT 'fiscal years (expect 1)', COUNT(DISTINCT fiscal_yr), FALSE FROM src
UNION ALL SELECT 'territory rows', COUNT(*), FALSE FROM terr_src
UNION ALL SELECT 'rows with NULL firm, channel, original channel or product',
  COUNT_IF(firm IS NULL OR channel IS NULL OR original_channel IS NULL OR product IS NULL), TRUE FROM src
UNION ALL SELECT '(zip, channel, product) with opportunity on both firms',
  COUNT(*), TRUE FROM (SELECT zip_code, channel, product FROM src WHERE COALESCE(opp, 0) <> 0
                       GROUP BY 1, 2, 3 HAVING COUNT(DISTINCT firm) > 1)
UNION ALL SELECT 'zips not 5 characters (source / territories)',
  (SELECT COUNT_IF(LENGTH(zip_code) <> 5) FROM src) + (SELECT COUNT_IF(LENGTH(zip_code) <> 5) FROM terr_src), TRUE
UNION ALL SELECT 'territory rows whose channel matches DIST_CH only ignoring case/spaces',
  COUNT(*), TRUE FROM terr_src t
  WHERE NOT EXISTS (SELECT 1 FROM ch c WHERE c.firm = t.firm AND c.original_channel = t.original_channel)
    AND EXISTS (SELECT 1 FROM ch c WHERE c.firm = t.firm
                AND UPPER(TRIM(c.original_channel)) = UPPER(TRIM(t.original_channel)))
UNION ALL SELECT 'territory rows in channels absent from the source table (out of scope, dropped)',
  COUNT(*), FALSE FROM terr_src t
  WHERE NOT EXISTS (SELECT 1 FROM ch c WHERE c.firm = t.firm
                    AND UPPER(TRIM(c.original_channel)) = UPPER(TRIM(t.original_channel)))
UNION ALL SELECT 'original channels split across target channels',
  COUNT(*), FALSE FROM (SELECT firm, original_channel FROM src GROUP BY 1, 2 HAVING COUNT(DISTINCT channel) > 1)
UNION ALL SELECT 'products sold by ' || f.firm_label, COUNT(fp.product), FALSE
  FROM f LEFT JOIN fp ON fp.firm = f.firm GROUP BY f.firm_label
UNION ALL SELECT 'products sold by both firms', COUNT(*), FALSE
  FROM (SELECT product FROM fp GROUP BY 1 HAVING COUNT(*) > 1)
UNION ALL SELECT 'pct of ' || f.firm_label || ' sales in a (channel, product) with no opportunity (unmeasured)',
  ROUND(100 * SUM(CASE WHEN cp.product IS NULL THEN s.sales ELSE 0 END) / NULLIF(SUM(s.sales), 0), 2), FALSE
  FROM src s JOIN f ON f.firm = s.firm
  LEFT JOIN cp ON cp.channel = s.channel AND cp.product = s.product
  GROUP BY f.firm_label
UNION ALL SELECT 'pct of sales with no seller ID (left out)',
  ROUND(100 * SUM(CASE WHEN seller IS NULL THEN sales ELSE 0 END) / NULLIF(SUM(sales), 0), 2), FALSE FROM src;

------------------------------------------------------------------------------------------------
-- Statement 2.  The ranking.  To keep it, put this in front of WITH:
--   CREATE OR REPLACE TABLE ssdb_integration.lr_strategy.wholesaler_rank AS
------------------------------------------------------------------------------------------------
WITH
params AS (SELECT CAST(1.0 AS DOUBLE) AS out_credit,      -- outside-territory sales count in full
                  CAST(1.0 AS DOUBLE) AS shrink_cells),   -- prior: one typical held zip-channel cell

src AS (
  SELECT ZIP_CODE                      AS zip_code,
         SOURCE                        AS firm,
         DIST_CH                       AS original_channel,
         CHANNEL                       AS channel,
         PRODUCT_V2                    AS product,
         MM_OPP                        AS opp,
         ACTUAL_SALES_AMOUNT           AS sales,
         SALES_WHOLESALER_TERRITORY_ID AS seller,
         SALES_WHOLESALER_CLEAN_NAME   AS seller_name
  FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys),

terr_src AS (
  SELECT SOURCE AS firm, CLEAN_ID AS wholesaler, CLEAN_NAME AS wholesaler_name,
         ZIP_CODE AS zip_code, CHANNEL AS original_channel
  FROM ssdb_integration.lr_strategy.territories),

filler AS (    -- vacancy IDs that appear as sellers; '__none__' matches nothing
  SELECT key FROM (VALUES ('__none__')) AS v(key)),

firm_products AS (  -- each firm's product set: what it has sales in
  SELECT DISTINCT firm, product FROM src WHERE sales > 0),

opp_cp AS (    -- opportunity per zip x target channel x product
  SELECT zip_code, channel, product, SUM(opp) AS opp
  FROM src GROUP BY zip_code, channel, product
  HAVING SUM(opp) > 0),

ch_map AS (    -- each firm's DIST_CH -> target channel
  SELECT DISTINCT firm, original_channel, channel FROM src),

terr AS (      -- territory in target channels
  SELECT DISTINCT t.firm, t.wholesaler, t.zip_code, m.channel
  FROM terr_src t
  JOIN ch_map m ON m.firm = t.firm AND m.original_channel = t.original_channel),

held AS (      -- held (zip, channel) x the holder's firm's products that have opportunity there
  SELECT t.firm, t.wholesaler, t.zip_code, t.channel, o.product, o.opp
  FROM terr t
  JOIN firm_products fp ON fp.firm = t.firm
  JOIN opp_cp o ON o.zip_code = t.zip_code AND o.channel = t.channel AND o.product = fp.product),

held_opp AS (  -- opportunity held by someone who sells the product, once per cell
  SELECT channel, product, SUM(opp) AS opp
  FROM (SELECT DISTINCT zip_code, channel, product, opp FROM held) x
  GROUP BY channel, product),

rate AS (      -- per target channel x product: credited sales / held opportunity
  SELECT h.channel, h.product, s.sales / h.opp AS rate
  FROM held_opp h
  JOIN (SELECT channel, product, SUM(sales) AS sales FROM src
        WHERE seller IS NOT NULL AND seller NOT IN (SELECT key FROM filler)
        GROUP BY channel, product) s
    ON s.channel = h.channel AND s.product = h.product),

holders AS (   -- holders per (zip, channel, product): only firms that sell the product
  SELECT zip_code, channel, product, COUNT(DISTINCT firm || '|' || wholesaler) AS n_holders
  FROM held GROUP BY zip_code, channel, product),

held_cell AS ( -- each holder's expected per held zip x channel
  SELECT h.firm, h.wholesaler, h.zip_code, h.channel, SUM(h.opp / n.n_holders * r.rate) AS expected
  FROM held h
  JOIN holders n ON n.zip_code = h.zip_code AND n.channel = h.channel AND n.product = h.product
  JOIN rate r    ON r.channel = h.channel AND r.product = h.product
  GROUP BY h.firm, h.wholesaler, h.zip_code, h.channel),

expected AS (
  SELECT firm, wholesaler, channel, COUNT(*) AS held_cells, SUM(expected) AS expected
  FROM held_cell GROUP BY firm, wholesaler, channel),

prior AS (     -- one typical held cell's expected, per channel
  SELECT c.channel, MAX(p.shrink_cells) * AVG(c.expected) AS prior
  FROM held_cell c CROSS JOIN params p
  GROUP BY c.channel),

ws AS (        -- each seller's net sales per zip x channel x product
  SELECT firm, seller AS wholesaler, zip_code, channel, product, SUM(sales) AS sales
  FROM src
  WHERE seller IS NOT NULL AND seller NOT IN (SELECT key FROM filler)
  GROUP BY firm, seller, zip_code, channel, product),

credited AS (  -- inside = a held (zip, channel, product); unmeasured = a (channel, product) nobody holds
  SELECT w.firm, w.wholesaler, w.channel,
         SUM(CASE WHEN r.rate IS NOT NULL AND h.wholesaler IS NOT NULL THEN w.sales ELSE 0 END) AS sales_in,
         SUM(CASE WHEN r.rate IS NOT NULL AND h.wholesaler IS NULL     THEN w.sales ELSE 0 END) AS sales_out,
         SUM(CASE WHEN r.rate IS NULL                                  THEN w.sales ELSE 0 END) AS sales_unmeasured
  FROM ws w
  LEFT JOIN rate r ON r.channel = w.channel AND r.product = w.product
  LEFT JOIN held h ON h.firm = w.firm AND h.wholesaler = w.wholesaler
                  AND h.zip_code = w.zip_code AND h.channel = w.channel AND h.product = w.product
  GROUP BY w.firm, w.wholesaler, w.channel),

wc AS (        -- people with territory, with only outside sales, or both
  SELECT COALESCE(e.firm, c.firm)             AS firm,
         COALESCE(e.wholesaler, c.wholesaler) AS wholesaler,
         COALESCE(e.channel, c.channel)       AS channel,
         COALESCE(e.held_cells, 0)            AS held_cells,
         COALESCE(e.expected, 0)              AS expected,
         COALESCE(c.sales_in, 0)              AS sales_in,
         COALESCE(c.sales_out, 0)             AS sales_out,
         COALESCE(c.sales_unmeasured, 0)      AS sales_unmeasured
  FROM expected e
  FULL OUTER JOIN credited c
    ON c.firm = e.firm AND c.wholesaler = e.wholesaler AND c.channel = e.channel),

scored AS (
  SELECT wc.*,
         wc.sales_in + p.out_credit * wc.sales_out              AS credited,
         CASE WHEN wc.expected > 0 THEN pr.prior ELSE 0 END     AS prior
  FROM wc
  LEFT JOIN prior pr ON pr.channel = wc.channel
  CROSS JOIN params p),

o AS (
  SELECT scored.*,
         CASE WHEN expected > 0 THEN (credited + prior) / (expected + prior) END            AS perf_index,
         SUM(credited + prior) OVER (PARTITION BY firm, wholesaler)
           / NULLIF(SUM(expected + prior) OVER (PARTITION BY firm, wholesaler), 0)          AS index_overall,
         SUM(sales_in + prior) OVER (PARTITION BY firm, wholesaler)
           / NULLIF(SUM(expected + prior) OVER (PARTITION BY firm, wholesaler), 0)          AS index_territory_only,
         SUM(sales_out) OVER (PARTITION BY firm, wholesaler)
           / NULLIF(SUM(sales_in + sales_out) OVER (PARTITION BY firm, wholesaler), 0)      AS out_share,
         expected / NULLIF(SUM(expected) OVER (PARTITION BY firm, wholesaler), 0)           AS channel_weight
  FROM scored),

names AS (     -- one display name per ID: the territories table's, else the source table's
  SELECT COALESCE(t.firm, s.firm) AS firm, COALESCE(t.wholesaler, s.wholesaler) AS wholesaler,
         COALESCE(t.wholesaler_name, s.wholesaler_name) AS wholesaler_name
  FROM (SELECT firm, wholesaler, MAX(wholesaler_name) AS wholesaler_name FROM terr_src GROUP BY 1, 2) t
  FULL OUTER JOIN
       (SELECT firm, seller AS wholesaler, MAX(seller_name) AS wholesaler_name
        FROM src WHERE seller IS NOT NULL GROUP BY 1, 2) s
    ON s.firm = t.firm AND s.wholesaler = t.wholesaler)

SELECT DENSE_RANK() OVER (ORDER BY index_overall DESC NULLS LAST)                          AS rank_overall,
       o.firm, o.wholesaler, n.wholesaler_name, index_overall, index_territory_only, out_share,
       channel, channel_weight,
       CASE WHEN perf_index IS NOT NULL
            THEN RANK() OVER (PARTITION BY channel, perf_index IS NULL ORDER BY perf_index DESC) END AS rank_in_channel,
       perf_index, held_cells, expected, sales_in, sales_out, sales_unmeasured, credited
FROM o
LEFT JOIN names n ON n.firm = o.firm AND n.wholesaler = o.wholesaler
ORDER BY rank_overall, o.firm, o.wholesaler, channel_weight DESC NULLS LAST;
