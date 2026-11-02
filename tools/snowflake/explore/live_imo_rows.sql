use role rl_ssdb_Integration_Lr_Strategy_Rw;
use database ssdb_Integration;
use schema lr_strategy;

--The live Tableau table's rows with an IMO label, by fiscal year x source x DIST_CH x NEW_DIST x CHANNEL: rows, $MM,
--rows with no seller ID (owner, 2026-11-01: "data_withnewchannel_union_w_joinkeys has IFA/IMO and FI/IMO rows in
--dist_ch, new_dist, and channel"; legacy_imo.sql's third part returned none).  Run on its own.
SELECT fiscal_yr, source, dist_ch, new_dist, channel, COUNT(*) AS n_rows,
       ROUND(SUM(mm_opp) / 1e6, 1) AS mm_opp_mm, ROUND(SUM(actual_sales_amount) / 1e6, 1) AS actual_sales_mm,
       ROUND(SUM(sales_amount) / 1e6, 1) AS sales_amount_mm,
       SUM(CASE WHEN sales_wholesaler_territory_id IS NULL THEN 1 ELSE 0 END) AS n_no_sales_id
FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys
WHERE dist_ch ILIKE '%IMO%' OR new_dist ILIKE '%IMO%' OR channel ILIKE '%IMO%'
GROUP BY ALL
ORDER BY fiscal_yr, source, dist_ch, new_dist, channel;
