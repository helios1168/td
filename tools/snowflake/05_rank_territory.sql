-- Rank wholesalers on one merged-company scale against their assigned territories.
--
--   expected  = territory opportunity x the channel's pooled rate (both firms together)
--   credited  = sales in the territory + out_credit x sales outside it
--               (owner, 2026-10-19: out-of-territory sales are included; out_credit = 1)
--   perf_index    = (credited + prior) / (expected + prior), per channel with territory; the prior
--                   is `shrink_cells` typical territory cells at the channel rate, so a thin
--                   territory cannot produce an extreme rank
--   index_overall = the same over all the wholesaler's channels (stay / go)
--   index_territory_only = index_overall without the outside sales, for comparison
-- Outside sales add production but no expected opportunity, so they lift the index.  A seller
-- keeps the credit; the territory's holder is not charged for it.  Sales in a territory cell with
-- no positive opportunity count as outside: credited, nothing expected.  The channel rate pools
-- every credited sale over every territory, so the merged company averages exactly 1.
--
-- Needs, in the session (see README.md):
--   raw(zip_code, firm, wholesaler, channel, opportunity, sales)   -- channel = the firm's own
--   channel_map(firm, source_channel, channel)                     -- the channelized firm's channels
--   territory(firm, wholesaler, zip_code, channel)                 -- channel = the channelized firm's
--   filler_keys(key)                                               -- vacancy sentinels
-- If the territory table has no channel, build `territory` as a view: a specialist's zips in
-- their home channel, a generalist's zips crossed with every channel.
-- Opportunity may sit on one firm's rows only, NULL on the other's: `cell` sums it across firms,
-- so each (zip, channel) counts it once and both firms are measured against it.  A territory cell
-- with no opportunity drops out of `expected` and its sales count as outside; 04_territory_profile
-- reports how many (`territory_cells_without_opp`, `pct_sales_in_cells_without_opp`).
-- Run first; all three must return 0:
--   SELECT COUNT(*) FROM raw r LEFT JOIN channel_map cm
--     ON cm.firm = r.firm AND cm.source_channel = r.channel WHERE cm.channel IS NULL;
--   SELECT COUNT(*) FROM territory t
--     WHERE t.channel NOT IN (SELECT DISTINCT channel FROM channel_map);
--   SELECT COUNT(*) FROM (SELECT r.zip_code, cm.channel FROM raw r JOIN channel_map cm      -- cells where
--       ON cm.firm = r.firm AND cm.source_channel = r.channel                              -- two firms
--     WHERE COALESCE(r.opportunity, 0) <> 0                                                 -- both carry
--     GROUP BY 1, 2 HAVING COUNT(DISTINCT r.firm) > 1);                                     -- opportunity
WITH
params AS (SELECT CAST(1.0 AS DOUBLE) AS shrink_cells, CAST(1.0 AS DOUBLE) AS out_credit),
m AS (       -- every row, in the channelized firm's channels
  SELECT r.zip_code, r.firm, r.wholesaler, cm.channel,
         CAST(r.opportunity AS DOUBLE) AS opportunity, CAST(r.sales AS DOUBLE) AS sales
  FROM raw r
  JOIN channel_map cm ON cm.firm = r.firm AND cm.source_channel = r.channel),
cell AS (    -- the market: one row per (zip, channel); opportunity is stored once per cell
  SELECT zip_code, channel, SUM(opportunity) AS opp
  FROM m WHERE zip_code IS NOT NULL
  GROUP BY zip_code, channel),
terr AS (    -- territory cells with positive opportunity
  SELECT DISTINCT t.firm, t.wholesaler, t.zip_code, t.channel, c.opp
  FROM territory t
  JOIN cell c ON c.zip_code = t.zip_code AND c.channel = t.channel
  WHERE c.opp > 0),
held AS (SELECT DISTINCT zip_code, channel FROM territory),
ws AS (      -- a wholesaler's net sales per cell
  SELECT firm, wholesaler, zip_code, channel, SUM(sales) AS sales
  FROM m
  WHERE wholesaler NOT IN (SELECT key FROM filler_keys)
  GROUP BY firm, wholesaler, zip_code, channel),
inside AS (
  SELECT t.firm, t.wholesaler, t.channel,
         COUNT(*)                                             AS terr_cells,
         SUM(CASE WHEN w.sales > 0 THEN 1 ELSE 0 END)         AS cells_with_sales,
         SUM(t.opp)                                           AS opp,
         SUM(COALESCE(w.sales, 0))                            AS sales_in
  FROM terr t
  LEFT JOIN ws w ON w.firm = t.firm AND w.wholesaler = t.wholesaler
                AND w.zip_code = t.zip_code AND w.channel = t.channel
  GROUP BY t.firm, t.wholesaler, t.channel),
outside AS (
  SELECT w.firm, w.wholesaler, w.channel,
         SUM(w.sales)                                         AS sales_out,
         SUM(CASE WHEN h.zip_code IS NULL THEN w.sales ELSE 0 END) AS sales_orphan   -- in nobody's territory
  FROM ws w
  LEFT JOIN terr t ON t.firm = w.firm AND t.wholesaler = w.wholesaler
                  AND t.zip_code = w.zip_code AND t.channel = w.channel
  LEFT JOIN held h ON h.zip_code = w.zip_code AND h.channel = w.channel
  WHERE t.wholesaler IS NULL
  GROUP BY w.firm, w.wholesaler, w.channel),
wc AS (      -- wholesaler x channel
  SELECT COALESCE(i.firm, o.firm) AS firm, COALESCE(i.wholesaler, o.wholesaler) AS wholesaler,
         COALESCE(i.channel, o.channel) AS channel,
         COALESCE(i.terr_cells, 0) AS terr_cells, COALESCE(i.cells_with_sales, 0) AS cells_with_sales,
         COALESCE(i.opp, 0) AS opp, COALESCE(i.sales_in, 0) AS sales_in,
         COALESCE(o.sales_out, 0) AS sales_out, COALESCE(o.sales_orphan, 0) AS sales_orphan
  FROM inside i
  FULL OUTER JOIN outside o ON o.firm = i.firm AND o.wholesaler = i.wholesaler AND o.channel = i.channel),
ch AS (      -- the channel benchmark, pooled over both firms
  SELECT wc.channel,
         SUM(wc.sales_in + x.out_credit * wc.sales_out) / NULLIF(SUM(wc.opp), 0) AS channel_rate,
         MAX(x.shrink_cells) * SUM(wc.opp) / NULLIF(SUM(wc.terr_cells), 0)       AS shrink_opp
  FROM wc CROSS JOIN params x
  GROUP BY wc.channel),
idx AS (
  SELECT wc.*, ch.channel_rate,
         wc.sales_in + x.out_credit * wc.sales_out                         AS credited,
         wc.opp * ch.channel_rate                                          AS expected,
         CASE WHEN wc.opp > 0 THEN ch.shrink_opp * ch.channel_rate ELSE 0 END AS prior
  FROM wc
  JOIN ch ON ch.channel = wc.channel
  CROSS JOIN params x),
o AS (
  SELECT idx.*,
         CASE WHEN opp > 0 THEN (credited + prior) / NULLIF(expected + prior, 0) END AS perf_index,
         SUM(credited + prior) OVER (PARTITION BY firm, wholesaler)
           / NULLIF(SUM(expected + prior) OVER (PARTITION BY firm, wholesaler), 0)   AS index_overall,
         SUM(sales_in + prior) OVER (PARTITION BY firm, wholesaler)
           / NULLIF(SUM(expected + prior) OVER (PARTITION BY firm, wholesaler), 0)   AS index_territory_only,
         SUM(sales_out) OVER (PARTITION BY firm, wholesaler)
           / NULLIF(SUM(sales_in + sales_out) OVER (PARTITION BY firm, wholesaler), 0) AS out_share,
         expected / NULLIF(SUM(expected) OVER (PARTITION BY firm, wholesaler), 0)    AS channel_weight
  FROM idx)
SELECT DENSE_RANK() OVER (ORDER BY index_overall DESC NULLS LAST)                  AS rank_overall,
       firm, wholesaler, index_overall, index_territory_only, out_share,
       channel, channel_weight,
       CASE WHEN perf_index IS NOT NULL
            THEN RANK() OVER (PARTITION BY channel, perf_index IS NULL ORDER BY perf_index DESC) END AS rank_in_channel,
       perf_index, channel_rate, terr_cells, cells_with_sales, opp, expected,
       sales_in, sales_out, sales_orphan, credited
FROM o
ORDER BY rank_overall, wholesaler, channel_weight DESC NULLS LAST
