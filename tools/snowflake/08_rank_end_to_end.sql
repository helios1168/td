-- Wholesaler ranking, end to end.  Run top to bottom in one Snowsight worksheet.
--   Part 0  edit: table names, column choices, fiscal year, vacancy keys   (the only edits)
--   Part 1  checks: one result grid; every row with must_be_zero = TRUE must show 0
--   Part 2  the ranking
-- Method: tools/snowflake/RUNBOOK.md.  index = credited sales / expected sales, one merged scale.

------------------------------------------------------------------------------------------------
-- Part 0.  Edit here only.
------------------------------------------------------------------------------------------------
-- Sales and opportunity, long across both firms; one row per whatever grain the table has.
CREATE OR REPLACE TEMPORARY VIEW os AS
SELECT ZIP_CODE                    AS zip_code,
       SOURCE                      AS firm,              -- the wholesaling firm (one of the two merging)
       SALES_WHOLESALER_CLEAN_NAME AS sales_wholesaler,  -- who made the sale; must match territory's key
       TERR_WHOLESALER_CLEAN_NAME  AS terr_wholesaler,   -- whose territory it is (checks only)
       CHANNEL                     AS original_channel,  -- the firm's own channel, as in the territory table
       NEW_DIST                    AS channel,           -- the target (channelized firm's) channel
       MM_OPP                      AS opp,               -- on one firm's rows, NULL on the other's
       SALES_AMOUNT                AS sales
FROM <db>.<schema>.<opportunity_sales table>
WHERE FISCAL_YR = '<fiscal year>';                       -- one period; the territory is today's

-- Territories, in original channels.
CREATE OR REPLACE TEMPORARY VIEW terr_src AS
SELECT SOURCE     AS firm,
       CLEAN_NAME AS wholesaler,                         -- same key as os.sales_wholesaler
       ZIP_CODE   AS zip_code,
       CHANNEL    AS original_channel
FROM <db>.<schema>.<territory table>;

-- Vacancy / filler keys that appear as a sales wholesaler.  Leave the table empty if there are none.
CREATE OR REPLACE TEMPORARY TABLE filler_keys (key VARCHAR);
-- INSERT INTO filler_keys VALUES ('<filler key>');

------------------------------------------------------------------------------------------------
-- Part 1.  Checks.  must_be_zero rows must show 0; the others are information.
------------------------------------------------------------------------------------------------
WITH
ch_map AS (SELECT DISTINCT firm, original_channel, channel FROM os),
terr AS (
  SELECT DISTINCT t.firm, t.wholesaler, t.zip_code, m.channel
  FROM terr_src t
  JOIN ch_map m ON m.firm = t.firm AND m.original_channel = t.original_channel),
cell_firms AS (
  SELECT zip_code, channel, COUNT(DISTINCT firm) AS n
  FROM os WHERE COALESCE(opp, 0) <> 0 GROUP BY 1, 2)
SELECT 'os rows'                                         AS check_name, COUNT(*) AS value, FALSE AS must_be_zero FROM os
UNION ALL SELECT 'territory rows',                         COUNT(*), FALSE FROM terr_src
UNION ALL SELECT 'territory rows after channel expansion', COUNT(*), FALSE FROM terr
UNION ALL SELECT 'os rows with NULL firm or target channel',
  COUNT_IF(firm IS NULL OR channel IS NULL), TRUE FROM os
UNION ALL SELECT 'os rows with NULL zip (their sales count as outside)',
  COUNT_IF(zip_code IS NULL), FALSE FROM os
UNION ALL SELECT 'zips not 5 characters (os)',            COUNT_IF(LENGTH(zip_code) <> 5), TRUE FROM os
UNION ALL SELECT 'zips not 5 characters (territory)',     COUNT_IF(LENGTH(zip_code) <> 5), TRUE FROM terr_src
UNION ALL SELECT 'territory firms not found in os',
  COUNT(DISTINCT firm), TRUE FROM terr_src WHERE firm NOT IN (SELECT DISTINCT firm FROM os WHERE firm IS NOT NULL)
UNION ALL SELECT 'territory rows whose original channel has no mapping',
  COUNT(*), TRUE FROM terr_src t
  WHERE NOT EXISTS (SELECT 1 FROM ch_map m WHERE m.firm = t.firm AND m.original_channel = t.original_channel)
UNION ALL SELECT 'cells with opportunity on both firms (would count twice)',
  COUNT(*), TRUE FROM cell_firms WHERE n > 1
UNION ALL SELECT 'firms carrying opportunity (expect 1)',
  COUNT(DISTINCT firm), FALSE FROM os WHERE COALESCE(opp, 0) <> 0
UNION ALL SELECT 'original channels split across target channels',
  COUNT(*), FALSE FROM (SELECT firm, original_channel FROM ch_map GROUP BY 1, 2 HAVING COUNT(*) > 1)
UNION ALL SELECT 'pct of sales with no sales wholesaler (left out)',
  ROUND(100 * SUM(CASE WHEN sales_wholesaler IS NULL THEN sales ELSE 0 END) / NULLIF(SUM(sales), 0), 2), FALSE FROM os
UNION ALL SELECT 'sales wholesalers with no territory rows',
  COUNT(DISTINCT sales_wholesaler), FALSE FROM os o
  WHERE sales <> 0 AND sales_wholesaler NOT IN (SELECT key FROM filler_keys)
    AND NOT EXISTS (SELECT 1 FROM terr_src t WHERE t.firm = o.firm AND t.wholesaler = o.sales_wholesaler)
UNION ALL SELECT 'territory wholesalers with no sales',
  COUNT(DISTINCT wholesaler), FALSE FROM terr_src t
  WHERE NOT EXISTS (SELECT 1 FROM os o WHERE o.firm = t.firm AND o.sales_wholesaler = t.wholesaler AND o.sales <> 0)
UNION ALL SELECT 'pct of sales where terr_wholesaler is not in the territory table',
  ROUND(100 * SUM(CASE WHEN o.terr_wholesaler IS NOT NULL AND t.wholesaler IS NULL THEN o.sales ELSE 0 END)
        / NULLIF(SUM(o.sales), 0), 2), FALSE
  FROM os o
  LEFT JOIN (SELECT DISTINCT firm, wholesaler, zip_code, original_channel FROM terr_src) t
    ON t.firm = o.firm AND t.wholesaler = o.terr_wholesaler
   AND t.zip_code = o.zip_code AND t.original_channel = o.original_channel
UNION ALL SELECT 'pct of sales in cells without opportunity',
  ROUND(100 * SUM(CASE WHEN COALESCE(c.opp, 0) <= 0 THEN o.sales ELSE 0 END) / NULLIF(SUM(o.sales), 0), 2), FALSE
  FROM os o
  LEFT JOIN (SELECT zip_code, channel, SUM(opp) AS opp FROM os GROUP BY 1, 2) c
    ON c.zip_code = o.zip_code AND c.channel = o.channel;

------------------------------------------------------------------------------------------------
-- Part 2.  The ranking.  To keep it: CREATE OR REPLACE TABLE <db>.<schema>.wholesaler_rank AS
------------------------------------------------------------------------------------------------
WITH
params AS (SELECT CAST(1.0 AS DOUBLE) AS out_credit,     -- outside-territory sales count in full
                  CAST(1.0 AS DOUBLE) AS shrink_cells),  -- prior: one typical held cell

opp AS (       -- zip x target channel; NULLs on the other firm's rows add nothing
  SELECT zip_code, channel, SUM(opp) AS opp
  FROM os GROUP BY zip_code, channel),

rate AS (      -- the market rate per target channel
  SELECT channel, DIV0(SUM(sales), SUM(opp)) AS rate
  FROM os GROUP BY channel),

ch_map AS (    -- original -> target channel, per firm
  SELECT DISTINCT firm, original_channel, channel FROM os),

terr AS (      -- territory in target channels; DISTINCT so two originals into one target count once
  SELECT DISTINCT t.firm, t.wholesaler, t.zip_code, m.channel
  FROM terr_src t
  JOIN ch_map m ON m.firm = t.firm AND m.original_channel = t.original_channel),

holders AS (
  SELECT zip_code, channel, COUNT(DISTINCT firm || '|' || wholesaler) AS n_holders
  FROM terr GROUP BY zip_code, channel),

held AS (      -- each holder's share of each held cell with opportunity
  SELECT t.firm, t.wholesaler, t.zip_code, t.channel, o.opp / h.n_holders AS opp_share
  FROM terr t
  JOIN opp o     ON o.zip_code = t.zip_code AND o.channel = t.channel
  JOIN holders h ON h.zip_code = t.zip_code AND h.channel = t.channel
  WHERE o.opp > 0),

expected AS (
  SELECT h.firm, h.wholesaler, h.channel, COUNT(*) AS held_cells, SUM(h.opp_share * r.rate) AS expected
  FROM held h JOIN rate r ON r.channel = h.channel
  GROUP BY 1, 2, 3),

prior AS (     -- one typical held cell's expected, per channel
  SELECT h.channel, MAX(p.shrink_cells) * AVG(h.opp_share) * MAX(r.rate) AS prior
  FROM held h JOIN rate r ON r.channel = h.channel CROSS JOIN params p
  GROUP BY h.channel),

ws AS (        -- each seller's net sales per cell; vacancy rows and rows with no seller left out
  SELECT firm, sales_wholesaler AS wholesaler, zip_code, channel, SUM(sales) AS sales
  FROM os
  WHERE sales_wholesaler IS NOT NULL AND sales_wholesaler NOT IN (SELECT key FROM filler_keys)
  GROUP BY 1, 2, 3, 4),

credited AS (  -- inside = a held cell with opportunity; everything else is outside
  SELECT w.firm, w.wholesaler, w.channel,
         SUM(CASE WHEN h.wholesaler IS NOT NULL THEN w.sales ELSE 0 END) AS sales_in,
         SUM(CASE WHEN h.wholesaler IS NULL     THEN w.sales ELSE 0 END) AS sales_out
  FROM ws w
  LEFT JOIN held h ON h.firm = w.firm AND h.wholesaler = w.wholesaler
                  AND h.zip_code = w.zip_code AND h.channel = w.channel
  GROUP BY 1, 2, 3),

wc AS (        -- people with territory, with only outside sales, or both
  SELECT COALESCE(e.firm, c.firm)             AS firm,
         COALESCE(e.wholesaler, c.wholesaler) AS wholesaler,
         COALESCE(e.channel, c.channel)       AS channel,
         COALESCE(e.held_cells, 0)            AS held_cells,
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
  FROM scored)

SELECT DENSE_RANK() OVER (ORDER BY index_overall DESC NULLS LAST)                          AS rank_overall,
       firm, wholesaler, index_overall, index_territory_only, out_share,
       channel, channel_weight,
       CASE WHEN perf_index IS NOT NULL
            THEN RANK() OVER (PARTITION BY channel, perf_index IS NULL ORDER BY perf_index DESC) END AS rank_in_channel,
       perf_index, held_cells, expected, sales_in, sales_out, credited
FROM o
ORDER BY rank_overall, firm, wholesaler, channel_weight DESC NULLS LAST;
