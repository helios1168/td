-- Wholesaler ranking with opportunity brought to the territory's own grain through the
-- distribution company.  Reads only the two source tables; creates nothing.  Two statements:
--   Statement 1  checks: every row with must_be_zero = TRUE must show 0
--   Statement 2  the ranking
--
-- Why: the territories table has no distribution company, only each firm's original channel
-- (DIST_CH), while the target channel is set per distribution company.  So:
--   1. opportunity per zip x distribution company (it sits on one firm's rows)
--   2. each firm's own grouping, distribution company -> that firm's DIST_CH, from its own rows
--   3. a territory row (firm, zip, DIST_CH) holds exactly the distribution companies its firm files
--      under that DIST_CH, in that zip; no expansion to whole target channels
--   4. a (zip, distribution company) held by n wholesalers (either firm) gives each 1/n
--   5. a sale is inside the territory when its seller holds (zip, DIST_CH) of that sale's row
-- rate = the market rate per target channel; index = credited / expected, as in 08.
--
-- Edit: if the distribution company is CBD_ID rather than FIRM, change `FIRM AS dist_company`
-- in the `src` CTE of both statements.  Vacancy IDs, if any appear as sellers, go in `filler`.

------------------------------------------------------------------------------------------------
-- Statement 1.  Checks.
------------------------------------------------------------------------------------------------
WITH
src AS (
  SELECT ZIP_CODE                      AS zip_code,
         SOURCE                        AS firm,
         FIRM                          AS dist_company,
         DIST_CH                       AS original_channel,
         CHANNEL                       AS channel,
         MM_OPP                        AS opp,
         ACTUAL_SALES_AMOUNT           AS sales,
         SALES_WHOLESALER_TERRITORY_ID AS seller,
         FISCAL_YR                     AS fiscal_yr
  FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys),
terr_src AS (
  SELECT DISTINCT SOURCE AS firm, CLEAN_ID AS wholesaler, ZIP_CODE AS zip_code, CHANNEL AS original_channel
  FROM ssdb_integration.lr_strategy.territories),
dc_map AS (
  SELECT DISTINCT firm, dist_company, original_channel FROM src WHERE dist_company IS NOT NULL),
ch AS (
  SELECT DISTINCT firm, original_channel FROM src),
f AS (
  SELECT firm, 'firm_' || DENSE_RANK() OVER (ORDER BY firm) AS firm_label
  FROM (SELECT DISTINCT firm FROM src WHERE firm IS NOT NULL) x),
opp_dc AS (
  SELECT zip_code, dist_company, SUM(opp) AS opp FROM src GROUP BY 1, 2 HAVING SUM(opp) > 0)
SELECT 'source rows' AS check_name, COUNT(*) AS value, FALSE AS must_be_zero FROM src
UNION ALL SELECT 'fiscal years (expect 1)', COUNT(DISTINCT fiscal_yr), FALSE FROM src
UNION ALL SELECT 'territory rows', COUNT(*), FALSE FROM terr_src
UNION ALL SELECT 'rows with NULL firm, target channel or original channel',
  COUNT_IF(firm IS NULL OR channel IS NULL OR original_channel IS NULL), TRUE FROM src
UNION ALL SELECT 'rows carrying opportunity with no distribution company',
  COUNT_IF(COALESCE(opp, 0) <> 0 AND dist_company IS NULL), TRUE FROM src
UNION ALL SELECT 'distribution companies filed under more than one DIST_CH within a firm',
  COUNT(*), TRUE FROM (SELECT firm, dist_company FROM dc_map GROUP BY 1, 2 HAVING COUNT(*) > 1)
UNION ALL SELECT '(zip, distribution company) with opportunity on both firms',
  COUNT(*), TRUE FROM (SELECT zip_code, dist_company FROM src WHERE COALESCE(opp, 0) <> 0
                       GROUP BY 1, 2 HAVING COUNT(DISTINCT firm) > 1)
UNION ALL SELECT 'zips not 5 characters (source / territories)',
  (SELECT COUNT_IF(LENGTH(zip_code) <> 5) FROM src) + (SELECT COUNT_IF(LENGTH(zip_code) <> 5) FROM terr_src), TRUE
UNION ALL SELECT 'territory rows whose channel matches DIST_CH only ignoring case/spaces',
  COUNT(*), TRUE FROM terr_src t
  WHERE NOT EXISTS (SELECT 1 FROM ch c WHERE c.firm = t.firm AND c.original_channel = t.original_channel)
    AND EXISTS (SELECT 1 FROM ch c WHERE c.firm = t.firm
                AND UPPER(TRIM(c.original_channel)) = UPPER(TRIM(t.original_channel)))
-- owner, 2026-10-19: the territories table's extra channels are outside the scope of this analysis
UNION ALL SELECT 'territory rows in channels absent from the source table (out of scope, dropped)',
  COUNT(*), FALSE FROM terr_src t
  WHERE NOT EXISTS (SELECT 1 FROM ch c WHERE c.firm = t.firm
                    AND UPPER(TRIM(c.original_channel)) = UPPER(TRIM(t.original_channel)))
UNION ALL SELECT 'distribution companies with more than one target channel',
  COUNT(*), FALSE FROM (SELECT dist_company FROM src WHERE dist_company IS NOT NULL
                        GROUP BY 1 HAVING COUNT(DISTINCT channel) > 1)
UNION ALL SELECT 'pct of opportunity filed under a DIST_CH of ' || f.firm_label
                 || ' (the rest is charged to nobody in that firm)',
  ROUND(100 * SUM(CASE WHEN m.firm IS NOT NULL THEN o.opp ELSE 0 END) / NULLIF(SUM(o.opp), 0), 2), FALSE
  FROM opp_dc o CROSS JOIN f
  LEFT JOIN (SELECT DISTINCT firm, dist_company FROM dc_map) m
    ON m.firm = f.firm AND m.dist_company = o.dist_company
  GROUP BY f.firm_label
UNION ALL SELECT 'pct of sales with no seller ID (left out)',
  ROUND(100 * SUM(CASE WHEN seller IS NULL THEN sales ELSE 0 END) / NULLIF(SUM(sales), 0), 2), FALSE FROM src;

------------------------------------------------------------------------------------------------
-- Statement 2.  The ranking.  To keep it, put this in front of WITH:
--   CREATE OR REPLACE TABLE ssdb_integration.lr_strategy.wholesaler_rank AS
------------------------------------------------------------------------------------------------
WITH
params AS (SELECT CAST(1.0 AS DOUBLE) AS out_credit,      -- outside-territory sales count in full
                  CAST(1.0 AS DOUBLE) AS shrink_zips),    -- prior: one typical held zip

src AS (
  SELECT ZIP_CODE                      AS zip_code,
         SOURCE                        AS firm,
         FIRM                          AS dist_company,
         DIST_CH                       AS original_channel,
         CHANNEL                       AS channel,
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

rate AS (      -- the market rate per target channel
  SELECT channel, DIV0(SUM(sales), SUM(opp)) AS rate
  FROM src GROUP BY channel),

opp_dc AS (    -- 1. opportunity per zip x distribution company (with its target channel)
  SELECT zip_code, dist_company, channel, SUM(opp) AS opp
  FROM src WHERE dist_company IS NOT NULL
  GROUP BY zip_code, dist_company, channel
  HAVING SUM(opp) > 0),

dc_map AS (    -- 2. each firm's grouping: distribution company -> that firm's DIST_CH
  SELECT DISTINCT firm, dist_company, original_channel
  FROM src WHERE dist_company IS NOT NULL),

held AS (      -- 3. territory rows -> the distribution companies their firm files under that DIST_CH
  SELECT DISTINCT t.firm, t.wholesaler, t.zip_code, t.original_channel, o.dist_company, o.channel, o.opp
  FROM terr_src t
  JOIN dc_map m ON m.firm = t.firm AND m.original_channel = t.original_channel
  JOIN opp_dc o ON o.zip_code = t.zip_code AND o.dist_company = m.dist_company),

holders AS (   -- 4. holders per (zip, distribution company), across both firms
  SELECT zip_code, dist_company, channel, COUNT(DISTINCT firm || '|' || wholesaler) AS n_holders
  FROM held GROUP BY zip_code, dist_company, channel),

held_zip AS (  -- each holder's share of opportunity, per zip x target channel
  SELECT h.firm, h.wholesaler, h.zip_code, h.channel, SUM(h.opp / n.n_holders) AS opp_share
  FROM (SELECT DISTINCT firm, wholesaler, zip_code, dist_company, channel, opp FROM held) h
  JOIN holders n ON n.zip_code = h.zip_code AND n.dist_company = h.dist_company AND n.channel = h.channel
  GROUP BY h.firm, h.wholesaler, h.zip_code, h.channel),

expected AS (
  SELECT z.firm, z.wholesaler, z.channel, COUNT(*) AS held_zips, SUM(z.opp_share * r.rate) AS expected
  FROM held_zip z JOIN rate r ON r.channel = z.channel
  GROUP BY z.firm, z.wholesaler, z.channel),

prior AS (     -- one typical held zip's expected, per target channel
  SELECT z.channel, MAX(p.shrink_zips) * AVG(z.opp_share) * MAX(r.rate) AS prior
  FROM held_zip z JOIN rate r ON r.channel = z.channel CROSS JOIN params p
  GROUP BY z.channel),

inside_key AS ( -- 5. where each holder's sales count as inside: (zip, DIST_CH) held with opportunity
  SELECT DISTINCT firm, wholesaler, zip_code, original_channel FROM held),

ws AS (        -- each seller's net sales per zip x DIST_CH x target channel
  SELECT firm, seller AS wholesaler, zip_code, original_channel, channel, SUM(sales) AS sales
  FROM src
  WHERE seller IS NOT NULL AND seller NOT IN (SELECT key FROM filler)
  GROUP BY firm, seller, zip_code, original_channel, channel),

credited AS (
  SELECT w.firm, w.wholesaler, w.channel,
         SUM(CASE WHEN k.wholesaler IS NOT NULL THEN w.sales ELSE 0 END) AS sales_in,
         SUM(CASE WHEN k.wholesaler IS NULL     THEN w.sales ELSE 0 END) AS sales_out
  FROM ws w
  LEFT JOIN inside_key k ON k.firm = w.firm AND k.wholesaler = w.wholesaler
                        AND k.zip_code = w.zip_code AND k.original_channel = w.original_channel
  GROUP BY w.firm, w.wholesaler, w.channel),

wc AS (        -- people with territory, with only outside sales, or both
  SELECT COALESCE(e.firm, c.firm)             AS firm,
         COALESCE(e.wholesaler, c.wholesaler) AS wholesaler,
         COALESCE(e.channel, c.channel)       AS channel,
         COALESCE(e.held_zips, 0)             AS held_zips,
         COALESCE(e.expected, 0)              AS expected,
         COALESCE(c.sales_in, 0)              AS sales_in,
         COALESCE(c.sales_out, 0)             AS sales_out
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
       perf_index, held_zips, expected, sales_in, sales_out, credited
FROM o
LEFT JOIN names n ON n.firm = o.firm AND n.wholesaler = o.wholesaler
ORDER BY rank_overall, o.firm, o.wholesaler, channel_weight DESC NULLS LAST;
