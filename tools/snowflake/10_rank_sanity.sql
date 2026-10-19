-- Sanity check on the ranking, by firm and by how many channels a wholesaler holds territory in.
-- Needs the ranking kept as ssdb_integration.lr_strategy.wholesaler_rank (08 Part 2, with the
-- CREATE OR REPLACE TABLE line).  Firm-level medians and counts only, firms as firm_1 / firm_2.
-- What to look for: generalists (3-4 channels) and specialists (1) of the same firm should not sit
-- far apart on index_territory_only; a large gap is worth a look before the ranks are used.
WITH
w AS (
  SELECT firm, wholesaler,
         MAX(index_overall)        AS index_overall,
         MAX(index_territory_only) AS index_territory_only,
         MAX(out_share)            AS out_share,
         COUNT(perf_index)         AS channels_held
  FROM ssdb_integration.lr_strategy.wholesaler_rank
  GROUP BY firm, wholesaler),
f AS (SELECT firm, 'firm_' || DENSE_RANK() OVER (ORDER BY firm) AS firm_label
      FROM (SELECT DISTINCT firm FROM w) x)
SELECT f.firm_label, w.channels_held,
       COUNT(*)                                   AS wholesalers,
       COUNT_IF(w.index_overall IS NULL)          AS unranked,
       ROUND(MEDIAN(w.index_overall), 3)          AS median_index,
       ROUND(MEDIAN(w.index_territory_only), 3)   AS median_index_territory_only,
       ROUND(MEDIAN(w.out_share), 3)              AS median_out_share
FROM w JOIN f ON f.firm = w.firm
GROUP BY 1, 2
ORDER BY 1, 2;
