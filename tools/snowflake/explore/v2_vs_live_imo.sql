use role rl_ssdb_Integration_Lr_Strategy_Rw;
use database ssdb_Integration;
use schema lr_strategy;

--Raymond James and every IMO label, the live Tableau table beside DATA_WITHNEWCHANNEL_UNION_W_JOINKEYS_V2: DIST_CH ->
--NEW_DIST -> CHANNEL, rows, rows with no territory wholesaler, sales rows with no seller ID, $MM.  Run on its own.
WITH t AS (
            SELECT 'LIVE' AS tbl, source, dist_ch, new_dist, channel, firm, terr_wholesaler AS terr_wh,
                   sales_wholesaler_territory_id AS sales_id, mm_opp, actual_sales_amount
            FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys
  UNION ALL SELECT 'V2', source, dist_ch, new_dist, channel, firm, old_terr_wholesaler, sales_wholesaler_territory_id,
                   mm_opp, actual_sales_amount
            FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys_v2)
SELECT CASE WHEN firm ILIKE '%RAYMOND JAMES%' THEN 'RAYMOND JAMES' ELSE 'OTHER' END AS firm_group, source, tbl,
       dist_ch, new_dist, channel, COUNT(*) AS n_rows,
       SUM(CASE WHEN terr_wh IS NULL OR terr_wh = 'open' THEN 1 ELSE 0 END) AS n_rows_no_terr_wholesaler,
       SUM(CASE WHEN sales_id IS NULL AND actual_sales_amount <> 0 THEN 1 ELSE 0 END) AS n_sales_rows_no_sales_id,
       ROUND(SUM(mm_opp) / 1e6, 1) AS mm_opp_mm, ROUND(SUM(actual_sales_amount) / 1e6, 1) AS actual_sales_mm
FROM t
WHERE firm ILIKE '%RAYMOND JAMES%' OR dist_ch ILIKE '%IMO%' OR new_dist ILIKE '%IMO%' OR channel ILIKE '%IMO%'
GROUP BY ALL
ORDER BY firm_group, source, tbl, actual_sales_mm DESC;
