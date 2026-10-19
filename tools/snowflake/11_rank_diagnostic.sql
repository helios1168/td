-- Why the index jumps between channels-held groups.  Run after 08 is kept as
-- ssdb_integration.lr_strategy.wholesaler_rank, in the same session (query B reads
-- ssdb_integration.lr_strategy.rank_os).  Counts, ratios and channel names only; firms as firm_1 / firm_2.

-- A. Per firm x channels held: who has no sales at all, and how sales and expected add up.
--    A group that is mostly no_sales_at_all is placeholder / vacant territories or IDs that do not
--    match between the two tables, not people selling badly.
WITH
w AS (
  SELECT firm, wholesaler,
         COUNT(perf_index)  AS channels_held,
         SUM(held_cells)    AS held_cells,
         SUM(sales_in)      AS sales_in,
         SUM(sales_out)     AS sales_out,
         SUM(expected)      AS expected
  FROM ssdb_integration.lr_strategy.wholesaler_rank
  GROUP BY firm, wholesaler),
f AS (SELECT firm, 'firm_' || DENSE_RANK() OVER (ORDER BY firm) AS firm_label
      FROM (SELECT DISTINCT firm FROM w) x)
SELECT f.firm_label, w.channels_held,
       COUNT(*)                                                          AS wholesalers,
       COUNT_IF(w.sales_in + w.sales_out = 0)                            AS no_sales_at_all,
       COUNT_IF(w.sales_in = 0 AND w.sales_out <> 0)                     AS sales_only_outside,
       ROUND(MEDIAN(w.held_cells), 0)                                    AS median_held_cells,
       ROUND(SUM(w.sales_in) / NULLIF(SUM(w.expected), 0), 3)            AS pooled_index_territory_only,
       ROUND(SUM(w.sales_out) / NULLIF(SUM(w.sales_in + w.sales_out), 0), 3) AS pooled_out_share,
       ROUND(100 * SUM(w.expected) / SUM(SUM(w.expected)) OVER (PARTITION BY f.firm_label), 1) AS pct_of_firm_expected
FROM w JOIN f ON f.firm = w.firm
GROUP BY 1, 2
ORDER BY 1, 2;

-- B. How each firm's original channels (DIST_CH) spread over target channels (CHANNEL), by row
--    share.  A territory row in an original channel is charged for every target it touches, so a
--    pair holding a sliver of the rows still adds a whole target channel to every holder of it.
WITH f AS (SELECT firm, 'firm_' || DENSE_RANK() OVER (ORDER BY firm) AS firm_label
           FROM (SELECT DISTINCT firm FROM ssdb_integration.lr_strategy.rank_os) x)
SELECT f.firm_label, o.original_channel, o.channel,
       COUNT(*)                                                                           AS n_rows,
       ROUND(100 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY f.firm_label, o.original_channel), 1) AS pct_of_original_rows,
       ROUND(100 * SUM(o.sales) / NULLIF(SUM(SUM(o.sales)) OVER (PARTITION BY f.firm_label, o.original_channel), 0), 1) AS pct_of_original_sales
FROM ssdb_integration.lr_strategy.rank_os o
JOIN f ON f.firm = o.firm
GROUP BY f.firm_label, o.firm, o.original_channel, o.channel
ORDER BY 1, 2, n_rows DESC;
