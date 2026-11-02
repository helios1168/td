use role rl_ssdb_Integration_Lr_Strategy_Rw;
use database ssdb_Integration;
use schema lr_strategy;

--Book per wholesaler, today vs new, by channel, from DATA_WITHNEWCHANNEL_UNION_W_JOINKEYS_V2: today = DIST_CH x
--OLD_TERR_WHOLESALER, new = CHANNEL x TERR_WHOLESALER_CLEAN_NAME (the new holder); today's PRI through CHANNEL's CASE
--(pri_afs).  Compare one SOURCE at a time; MM_OPP_CHANGE sums to 0 per source.  Run on its own.
WITH b AS (
            SELECT source, CASE WHEN dist_ch IN ('PRI', 'AFS') THEN 'pri_afs' ELSE dist_ch END AS channel,
                   COALESCE(old_terr_wholesaler, '(NO HOLDER)') AS wholesaler,
                   CAST(mm_opp AS DECIMAL(38, 6)) AS mm_opp_today, CAST(0 AS DECIMAL(38, 6)) AS mm_opp_new
            FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys_v2
  UNION ALL SELECT source, channel, COALESCE(terr_wholesaler_clean_name, '(NO HOLDER)'),
                   CAST(0 AS DECIMAL(38, 6)), CAST(mm_opp AS DECIMAL(38, 6))
            FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys_v2)
SELECT source, channel, wholesaler, SUM(mm_opp_today) AS mm_opp_today, SUM(mm_opp_new) AS mm_opp_new,
       SUM(mm_opp_new) - SUM(mm_opp_today) AS mm_opp_change
FROM b
GROUP BY ALL
HAVING SUM(mm_opp_today) <> 0 OR SUM(mm_opp_new) <> 0
ORDER BY source, channel, mm_opp_change;
