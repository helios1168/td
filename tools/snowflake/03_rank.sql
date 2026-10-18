-- Rank wholesalers on one merged-company scale by an opportunity-adjusted performance index.
--
-- Volume within a channel favours the channelized firm's specialists, who spend all their time
-- in it.  A rate does not: penetration = sales / opportunity of the cells a wholesaler works.
--   expected = footprint opportunity x the channel's pooled penetration (both firms together)
--   index    = sales / expected, shrunk toward 1 by `shrink_cells` typical footprint cells, so a
--              thin footprint in a channel cannot produce an extreme rank
--   index_overall = the expected-weighted mean of a wholesaler's channel indexes (stay / go);
--   rank_in_channel ranks the channel index (which channel).
-- Footprint, for now: the (zip, channel) cells where the wholesaler's net sales are positive
-- (owner, 2026-10-18).  That leaves out zero-sales zips, so every rate reads high; it reads high
-- for both firms.
--
-- Needs, in the session (see README.md):
--   raw(zip_code, firm, wholesaler, channel, opportunity, sales)   -- channel = the firm's own
--   channel_map(firm, source_channel, channel)                     -- the channelized firm's channels
--   filler_keys(key)                                               -- vacancy sentinels
-- Run first; it must return 0, or those rows' sales and opportunity are silently left out:
--   SELECT COUNT(*) FROM raw r LEFT JOIN channel_map cm
--     ON cm.firm = r.firm AND cm.source_channel = r.channel WHERE cm.channel IS NULL;
WITH
params AS (SELECT CAST(1.0 AS DOUBLE) AS shrink_cells),
m AS (       -- every row, in the channelized firm's channels
  SELECT r.zip_code, r.firm, r.wholesaler, cm.channel,
         CAST(r.opportunity AS DOUBLE) AS opportunity, CAST(r.sales AS DOUBLE) AS sales
  FROM raw r
  JOIN channel_map cm ON cm.firm = r.firm AND cm.source_channel = r.channel
  WHERE r.zip_code IS NOT NULL),
cell AS (    -- the market: one row per (zip, channel); opportunity is stored once per cell
  SELECT zip_code, channel, SUM(opportunity) AS opp
  FROM m
  GROUP BY zip_code, channel),
ws AS (      -- a wholesaler's net sales per cell; the footprint is where they are positive
  SELECT firm, wholesaler, zip_code, channel, SUM(sales) AS sales
  FROM m
  WHERE wholesaler NOT IN (SELECT key FROM filler_keys)
  GROUP BY firm, wholesaler, zip_code, channel
  HAVING SUM(sales) > 0),
wc AS (      -- wholesaler x channel; sales in cells without positive opportunity are kept apart
  SELECT w.firm, w.wholesaler, w.channel,
         SUM(CASE WHEN c.opp > 0 THEN 1 ELSE 0 END)       AS cells,
         SUM(CASE WHEN c.opp > 0 THEN w.sales ELSE 0 END) AS sales,
         SUM(CASE WHEN c.opp > 0 THEN c.opp ELSE 0 END)   AS opp,
         SUM(CASE WHEN c.opp > 0 THEN 0 ELSE w.sales END) AS sales_no_opp
  FROM ws w
  JOIN cell c ON c.zip_code = w.zip_code AND c.channel = w.channel
  GROUP BY w.firm, w.wholesaler, w.channel),
ch AS (      -- the channel benchmark, pooled over both firms: penetration, and the shrink weight
  SELECT wc.channel,
         SUM(wc.sales) / NULLIF(SUM(wc.opp), 0)                AS channel_rate,
         MAX(x.shrink_cells) * SUM(wc.opp) / NULLIF(SUM(wc.cells), 0) AS shrink_opp
  FROM wc CROSS JOIN params x
  GROUP BY wc.channel),
idx AS (
  SELECT wc.*, ch.channel_rate,
         wc.sales / NULLIF(wc.opp, 0)                       AS rate,
         wc.opp * ch.channel_rate                           AS expected,
         wc.sales / NULLIF(wc.opp * ch.channel_rate, 0)     AS index_raw,
         (wc.sales + ch.shrink_opp * ch.channel_rate)
           / NULLIF((wc.opp + ch.shrink_opp) * ch.channel_rate, 0) AS perf_index
  FROM wc JOIN ch ON ch.channel = wc.channel),
o AS (
  SELECT idx.*,
         COUNT(*) OVER (PARTITION BY firm, wholesaler)                     AS n_channels,
         expected / NULLIF(SUM(expected) OVER (PARTITION BY firm, wholesaler), 0) AS channel_weight,
         SUM(perf_index * expected) OVER (PARTITION BY firm, wholesaler)
           / NULLIF(SUM(expected) OVER (PARTITION BY firm, wholesaler), 0) AS index_overall,
         RANK() OVER (PARTITION BY channel ORDER BY perf_index DESC)       AS rank_in_channel,
         COUNT(*) OVER (PARTITION BY channel)                              AS ranked_in_channel
  FROM idx)
SELECT DENSE_RANK() OVER (ORDER BY index_overall DESC) AS rank_overall,
       firm, wholesaler, n_channels, index_overall,
       channel, channel_weight, rank_in_channel, ranked_in_channel, perf_index, index_raw,
       rate, channel_rate, cells, opp, sales, expected, sales_no_opp
FROM o
ORDER BY rank_overall, wholesaler, channel_weight DESC
