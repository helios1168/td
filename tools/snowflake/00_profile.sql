-- Profile of the live table: counts and shapes only, no names, no amounts.  Rename `raw`.
-- The output (grp, k, v) is what tools/snowflake/ needs to build a synthetic table outside work;
-- the only strings in it are the channel values.  Run at work; never save the filler keys.
CREATE OR REPLACE TEMPORARY TABLE filler_keys (key VARCHAR);
INSERT INTO filler_keys VALUES ('<filler key>');           -- typed at work, never saved

WITH t AS (SELECT r.*, f.key IS NOT NULL AS filler
           FROM raw r LEFT JOIN filler_keys f ON r.wholesaler = f.key),
cell AS (SELECT zip_code, channel, COUNT(*) AS n, COUNT(DISTINCT wholesaler) AS n_ws,
                COUNT(DISTINCT opportunity) AS n_opp, COUNT_IF(opportunity > 0) AS n_pos
         FROM t GROUP BY 1, 2),
ws AS (SELECT wholesaler, COUNT(DISTINCT firm) AS n_firm, COUNT(DISTINCT zip_code) AS n_zip,
              COUNT(DISTINCT channel) AS n_ch FROM t WHERE NOT filler GROUP BY 1),
fm AS (SELECT firm, COUNT(DISTINCT wholesaler) AS n_ws FROM t WHERE NOT filler GROUP BY 1)
SELECT 'size' AS grp, 'rows' AS k, COUNT(*) AS v FROM t
UNION ALL SELECT 'size', 'zips', COUNT(DISTINCT zip_code) FROM t
UNION ALL SELECT 'size', 'cells', COUNT(*) FROM cell
UNION ALL SELECT 'size', 'wholesalers', COUNT(*) FROM ws
UNION ALL SELECT 'size', 'firms', COUNT(*) FROM fm
UNION ALL SELECT 'size', 'filler_rows', COUNT_IF(filler) FROM t
UNION ALL SELECT 'size', 'zips_under_5_chars', COUNT(DISTINCT IFF(LENGTH(zip_code::VARCHAR) < 5, zip_code, NULL)) FROM t
UNION ALL SELECT 'null', 'zip_code', COUNT_IF(zip_code IS NULL) FROM t
UNION ALL SELECT 'null', 'channel', COUNT_IF(channel IS NULL) FROM t
UNION ALL SELECT 'null', 'firm', COUNT_IF(firm IS NULL) FROM t
UNION ALL SELECT 'null', 'wholesaler', COUNT_IF(wholesaler IS NULL) FROM t
UNION ALL SELECT 'null', 'opportunity', COUNT_IF(opportunity IS NULL) FROM t
UNION ALL SELECT 'null', 'sales', COUNT_IF(sales IS NULL) FROM t
UNION ALL SELECT 'sign', 'opportunity_zero', COUNT_IF(opportunity = 0) FROM t
UNION ALL SELECT 'sign', 'opportunity_negative', COUNT_IF(opportunity < 0) FROM t
UNION ALL SELECT 'sign', 'sales_zero', COUNT_IF(sales = 0) FROM t
UNION ALL SELECT 'sign', 'sales_negative', COUNT_IF(sales < 0) FROM t
UNION ALL SELECT 'channel_rows', channel, COUNT(*) FROM t GROUP BY channel
UNION ALL SELECT 'channel_cells', channel, COUNT(*) FROM cell GROUP BY channel
UNION ALL SELECT 'channel_wholesalers', channel, COUNT(DISTINCT IFF(filler, NULL, wholesaler)) FROM t GROUP BY channel
UNION ALL SELECT 'rows_per_cell', n::VARCHAR, COUNT(*) FROM cell GROUP BY n
UNION ALL SELECT 'wholesalers_per_cell', n_ws::VARCHAR, COUNT(*) FROM cell GROUP BY n_ws
UNION ALL SELECT 'opportunity_layout',
                 CASE WHEN n = 1 THEN 'one_row' WHEN n_opp = 1 AND n_pos = n THEN 'repeated'
                      WHEN n_pos <= 1 THEN 'on_one_row' ELSE 'split' END, COUNT(*) FROM cell GROUP BY 2
UNION ALL SELECT 'zips_per_wholesaler_2^k', FLOOR(LOG(2, GREATEST(n_zip, 1)))::VARCHAR, COUNT(*) FROM ws GROUP BY 2
UNION ALL SELECT 'channels_per_wholesaler', n_ch::VARCHAR, COUNT(*) FROM ws GROUP BY 2
UNION ALL SELECT 'firms_per_wholesaler', n_firm::VARCHAR, COUNT(*) FROM ws GROUP BY 2
UNION ALL SELECT 'wholesalers_per_firm_2^k', FLOOR(LOG(2, GREATEST(n_ws, 1)))::VARCHAR, COUNT(*) FROM fm GROUP BY 2
ORDER BY grp, k;
