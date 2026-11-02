use role rl_ssdb_Integration_Lr_Strategy_Rw;
use database ssdb_Integration;
use schema lr_strategy;

--DATA_WITHNEWCHANNEL_UNION_W_JOINKEYS_V2's columns against the live Tableau table's, by name: position, type, status.
--Expect 26 rows: 23 SAME, TERR_WHOLESALER ONLY IN LIVE, OLD_TERR_WHOLESALER (position 3) and NEW_TERR_WHOLESALER
--(position 25) ONLY IN V2.  Any TYPE DIFFERS row is a Tableau field that may change type.  Run on its own.
WITH c AS (
  SELECT table_name, column_name, ordinal_position, data_type, character_maximum_length, numeric_precision, numeric_scale
  FROM ssdb_integration.information_schema.columns
  WHERE table_schema = 'LR_STRATEGY'
    AND table_name IN ('DATA_WITHNEWCHANNEL_UNION_W_JOINKEYS', 'DATA_WITHNEWCHANNEL_UNION_W_JOINKEYS_V2'))
SELECT COALESCE(v.column_name, l.column_name) AS column_name, l.ordinal_position AS live_pos, v.ordinal_position AS v2_pos,
       l.data_type AS live_type, v.data_type AS v2_type,
       CASE WHEN l.column_name IS NULL THEN 'ONLY IN V2'
            WHEN v.column_name IS NULL THEN 'ONLY IN LIVE'
            WHEN l.data_type = v.data_type AND EQUAL_NULL(l.character_maximum_length, v.character_maximum_length)
             AND EQUAL_NULL(l.numeric_precision, v.numeric_precision) AND EQUAL_NULL(l.numeric_scale, v.numeric_scale)
            THEN 'SAME' ELSE 'TYPE DIFFERS' END AS status
FROM (SELECT * FROM c WHERE table_name = 'DATA_WITHNEWCHANNEL_UNION_W_JOINKEYS') l
FULL JOIN (SELECT * FROM c WHERE table_name = 'DATA_WITHNEWCHANNEL_UNION_W_JOINKEYS_V2') v
  ON v.column_name = l.column_name
ORDER BY COALESCE(v.ordinal_position, l.ordinal_position);
