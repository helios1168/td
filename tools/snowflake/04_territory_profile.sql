-- Profile of the territory table against raw: counts and firm-level ratios, no names, no amounts.
-- Needs raw, channel_map, territory and filler_keys as in 05_rank_territory.sql.  Firms show as
-- firm_1 / firm_2 (by name order), so the output can leave work.
WITH
f AS (SELECT firm, 'firm_' || DENSE_RANK() OVER (ORDER BY firm) AS firm_label
      FROM (SELECT firm FROM raw UNION SELECT firm FROM territory)),
m AS (SELECT r.zip_code, r.firm, r.wholesaler, cm.channel, r.opportunity, r.sales
      FROM raw r JOIN channel_map cm ON cm.firm = r.firm AND cm.source_channel = r.channel
      WHERE r.wholesaler NOT IN (SELECT key FROM filler_keys)),
t AS (SELECT DISTINCT firm, wholesaler, zip_code, channel FROM territory),
cell AS (SELECT r.zip_code, cm.channel, SUM(r.opportunity) AS opp     -- across firms: NULLs add nothing
         FROM raw r JOIN channel_map cm ON cm.firm = r.firm AND cm.source_channel = r.channel
         GROUP BY 1, 2),
tw AS (SELECT firm, wholesaler, COUNT(DISTINCT zip_code) AS n_zip, COUNT(DISTINCT channel) AS n_ch
       FROM t GROUP BY 1, 2),
s AS (SELECT m.firm, m.sales,
             CASE WHEN t.wholesaler IS NOT NULL THEN 'own_territory'
                  WHEN EXISTS (SELECT 1 FROM t t2 WHERE t2.zip_code = m.zip_code AND t2.channel = m.channel)
                       THEN 'others_territory'
                  ELSE 'no_territory' END AS where_sold
      FROM m LEFT JOIN t ON t.firm = m.firm AND t.wholesaler = m.wholesaler
                        AND t.zip_code = m.zip_code AND t.channel = m.channel)
SELECT 'size' AS grp, 'territory_rows' AS k, COUNT(*) AS v FROM territory
UNION ALL SELECT 'size', 'territory_wholesalers', COUNT(*) FROM tw
UNION ALL SELECT 'size', 'territory_cells', COUNT(*) FROM (SELECT DISTINCT zip_code, channel FROM t)
UNION ALL SELECT 'size', 'duplicate_territory_rows', (SELECT COUNT(*) FROM territory) - (SELECT COUNT(*) FROM t)
UNION ALL SELECT 'size', 'wholesalers_with_sales_no_territory',
  COUNT(*) FROM (SELECT DISTINCT firm, wholesaler FROM m WHERE sales > 0) x
  WHERE NOT EXISTS (SELECT 1 FROM tw WHERE tw.firm = x.firm AND tw.wholesaler = x.wholesaler)
UNION ALL SELECT 'size', 'wholesalers_with_territory_no_sales',
  COUNT(*) FROM tw WHERE NOT EXISTS (SELECT 1 FROM m WHERE m.firm = tw.firm AND m.wholesaler = tw.wholesaler AND m.sales > 0)
UNION ALL SELECT 'size', 'territory_channels_not_in_map',
  COUNT(*) FROM t WHERE channel NOT IN (SELECT DISTINCT channel FROM channel_map)
UNION ALL SELECT 'holders_per_cell_same_firm', n::VARCHAR, COUNT(*)
  FROM (SELECT firm, zip_code, channel, COUNT(*) AS n FROM t GROUP BY 1, 2, 3) GROUP BY 2
UNION ALL SELECT 'zips_per_wholesaler_2^k', f.firm_label || ':' || FLOOR(LOG(2, GREATEST(n_zip, 1)))::VARCHAR, COUNT(*)
  FROM tw JOIN f USING (firm) GROUP BY 2
UNION ALL SELECT 'channels_per_wholesaler', f.firm_label || ':' || n_ch::VARCHAR, COUNT(*)
  FROM tw JOIN f USING (firm) GROUP BY 2
UNION ALL SELECT 'rows_by_where_sold', f.firm_label || ':' || where_sold, COUNT(*)
  FROM s JOIN f USING (firm) WHERE sales > 0 GROUP BY 2
UNION ALL SELECT 'pct_sales_by_where_sold', f.firm_label || ':' || where_sold,
  ROUND(100 * SUM(sales) / SUM(SUM(sales)) OVER (PARTITION BY f.firm_label))
  FROM s JOIN f USING (firm) GROUP BY f.firm_label, where_sold
-- opportunity must sit on one firm's rows only; the other firm's cells must still find it
UNION ALL SELECT 'opp_rows_nonzero', f.firm_label, COUNT(*)
  FROM raw r JOIN f USING (firm) WHERE COALESCE(r.opportunity, 0) <> 0 GROUP BY 2
UNION ALL SELECT 'territory_cells_without_opp', f.firm_label, COUNT(*)
  FROM t JOIN f USING (firm)
  LEFT JOIN cell c ON c.zip_code = t.zip_code AND c.channel = t.channel
  WHERE COALESCE(c.opp, 0) <= 0 GROUP BY 2
UNION ALL SELECT 'pct_sales_in_cells_without_opp', f.firm_label,
  ROUND(100 * SUM(CASE WHEN COALESCE(c.opp, 0) <= 0 THEN m.sales ELSE 0 END) / NULLIF(SUM(m.sales), 0), 1)
  FROM m JOIN f USING (firm)
  LEFT JOIN cell c ON c.zip_code = m.zip_code AND c.channel = m.channel GROUP BY 2
ORDER BY grp, k
