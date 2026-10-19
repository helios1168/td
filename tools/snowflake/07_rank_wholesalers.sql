-- Rank wholesalers on one merged-company scale: credited sales / expected sales.
--
-- Inputs, in the session:
--   opportunity_sales(zip_code, firm, wholesaler, original_channel, channel, opp, sales)
--       long across firms; channel = the target channel; opp on one firm's rows, NULL on the other's
--   territory(firm, wholesaler, zip_code, original_channel)
--   filler_keys(key)                                 -- vacancy sentinels
--
--   rate      = the channel's market rate: all sales / all opportunity
--   expected  = the wholesaler's share of each held cell's opportunity x rate; a cell held by n
--               wholesalers (either firm) gives each 1/n, so every cell is charged once
--   credited  = sales in the territory + out_credit x sales outside it (owner, 2026-10-19: included)
--   perf_index    = (credited + prior) / (expected + prior), per channel held; the prior is
--                   `shrink_cells` typical held cells, so a thin territory cannot rank extreme
--   index_overall = the same over all the wholesaler's channels (stay / go)
-- Sales in a held cell with no positive opportunity count as outside: credited, nothing expected.
-- The average index is near 1, not exactly 1: vacancy sales are in the rate but nobody's credit
-- (pulls it down), opportunity nobody holds is in the rate but nobody's expected (pushes it up).
-- Both move everyone in a channel by the same factor.
WITH
params AS (SELECT CAST(1.0 AS DOUBLE) AS out_credit, CAST(1.0 AS DOUBLE) AS shrink_cells),

opp AS (       -- cell opportunity: NULLs on the other firm's rows add nothing
  SELECT zip_code, channel, SUM(opp) AS opp
  FROM opportunity_sales
  GROUP BY zip_code, channel),

rate AS (      -- the market rate per channel
  SELECT channel, DIV0(SUM(sales), SUM(opp)) AS rate
  FROM opportunity_sales
  GROUP BY channel),

ch_map AS (    -- original -> target channel, per firm
  SELECT DISTINCT firm, original_channel, channel
  FROM opportunity_sales),

terr AS (      -- territory in target channels; DISTINCT so two original channels into one target count once
  SELECT DISTINCT t.firm, t.wholesaler, t.zip_code, m.channel
  FROM territory t
  JOIN ch_map m ON m.firm = t.firm AND m.original_channel = t.original_channel),

holders AS (
  SELECT zip_code, channel, COUNT(DISTINCT wholesaler) AS n_holders
  FROM terr
  GROUP BY zip_code, channel),

terr_cell AS ( -- each holder's share of each held cell with opportunity
  SELECT t.firm, t.wholesaler, t.zip_code, t.channel, o.opp / h.n_holders AS opp_share
  FROM terr t
  JOIN opp o     ON o.zip_code = t.zip_code AND o.channel = t.channel
  JOIN holders h ON h.zip_code = t.zip_code AND h.channel = t.channel
  WHERE o.opp > 0),

prior AS (     -- one typical held cell's expected, per channel
  SELECT tc.channel, MAX(p.shrink_cells) * AVG(tc.opp_share) * MAX(r.rate) AS prior
  FROM terr_cell tc
  JOIN rate r ON r.channel = tc.channel
  CROSS JOIN params p
  GROUP BY tc.channel),

ws AS (        -- each wholesaler's net sales per cell
  SELECT firm, wholesaler, zip_code, channel, SUM(sales) AS sales
  FROM opportunity_sales
  WHERE wholesaler NOT IN (SELECT key FROM filler_keys)
  GROUP BY firm, wholesaler, zip_code, channel),

inside AS (
  SELECT tc.firm, tc.wholesaler, tc.channel,
         COUNT(*)                   AS terr_cells,
         SUM(tc.opp_share)          AS opp_share,
         SUM(COALESCE(w.sales, 0))  AS sales_in
  FROM terr_cell tc
  LEFT JOIN ws w ON w.firm = tc.firm AND w.wholesaler = tc.wholesaler
                AND w.zip_code = tc.zip_code AND w.channel = tc.channel
  GROUP BY tc.firm, tc.wholesaler, tc.channel),

outside AS (
  SELECT w.firm, w.wholesaler, w.channel, SUM(w.sales) AS sales_out
  FROM ws w
  LEFT JOIN terr_cell tc ON tc.firm = w.firm AND tc.wholesaler = w.wholesaler
                        AND tc.zip_code = w.zip_code AND tc.channel = w.channel
  WHERE tc.wholesaler IS NULL
  GROUP BY w.firm, w.wholesaler, w.channel),

wc AS (        -- wholesaler x channel
  SELECT COALESCE(i.firm, o.firm)             AS firm,
         COALESCE(i.wholesaler, o.wholesaler) AS wholesaler,
         COALESCE(i.channel, o.channel)       AS channel,
         COALESCE(i.terr_cells, 0)            AS terr_cells,
         COALESCE(i.opp_share, 0)             AS opp_share,
         COALESCE(i.sales_in, 0)              AS sales_in,
         COALESCE(o.sales_out, 0)             AS sales_out
  FROM inside i
  FULL OUTER JOIN outside o
    ON o.firm = i.firm AND o.wholesaler = i.wholesaler AND o.channel = i.channel),

scored AS (
  SELECT wc.*, r.rate,
         wc.opp_share * r.rate                                    AS expected,
         wc.sales_in + p.out_credit * wc.sales_out                AS credited,
         CASE WHEN wc.terr_cells > 0 THEN pr.prior ELSE 0 END     AS prior
  FROM wc
  JOIN rate r ON r.channel = wc.channel
  LEFT JOIN prior pr ON pr.channel = wc.channel
  CROSS JOIN params p),

o AS (
  SELECT scored.*,
         CASE WHEN terr_cells > 0 THEN (credited + prior) / NULLIF(expected + prior, 0) END AS perf_index,
         SUM(credited + prior) OVER (PARTITION BY firm, wholesaler)
           / NULLIF(SUM(expected + prior) OVER (PARTITION BY firm, wholesaler), 0)        AS index_overall,
         SUM(sales_in + prior) OVER (PARTITION BY firm, wholesaler)
           / NULLIF(SUM(expected + prior) OVER (PARTITION BY firm, wholesaler), 0)        AS index_territory_only,
         SUM(sales_out) OVER (PARTITION BY firm, wholesaler)
           / NULLIF(SUM(sales_in + sales_out) OVER (PARTITION BY firm, wholesaler), 0)    AS out_share,
         expected / NULLIF(SUM(expected) OVER (PARTITION BY firm, wholesaler), 0)         AS channel_weight
  FROM scored)

SELECT DENSE_RANK() OVER (ORDER BY index_overall DESC NULLS LAST)                       AS rank_overall,
       firm, wholesaler, index_overall, index_territory_only, out_share,
       channel, channel_weight,
       CASE WHEN perf_index IS NOT NULL
            THEN RANK() OVER (PARTITION BY channel, perf_index IS NULL ORDER BY perf_index DESC) END AS rank_in_channel,
       perf_index, rate, terr_cells, opp_share, expected, sales_in, sales_out, credited
FROM o
ORDER BY rank_overall, wholesaler, channel_weight DESC NULLS LAST
