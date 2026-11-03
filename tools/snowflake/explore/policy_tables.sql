use role rl_ssdb_Integration_Lr_Strategy_Rw;
use database ssdb_Integration;
use schema lr_strategy;

--Which tables this role can read carry a policy number (owner, 2026-11-03: "is there anyway to get cbd_id, firm name,
--and dist_ch at the policy number through any of our queries? the catch is I don't have direct access to the sls_rpt
--table").  Every table and view in the database with a column named like POLIC or PLCY, with its company, firm and
--channel columns if it has them.  Run on its own; not tested.
SELECT table_schema, table_name,
       LISTAGG(CASE WHEN column_name ILIKE '%POLIC%' OR column_name ILIKE '%PLCY%' THEN column_name END, ', ')
         WITHIN GROUP (ORDER BY ordinal_position) AS policy_columns,
       LISTAGG(CASE WHEN column_name ILIKE '%BRKR%' OR column_name ILIKE '%CBD%' OR column_name ILIKE '%BROKER%'
                      OR column_name ILIKE '%FIRM%' OR column_name ILIKE '%DIST_CH%' OR column_name ILIKE '%CHANNEL%'
                    THEN column_name END, ', ') WITHIN GROUP (ORDER BY ordinal_position) AS firm_and_channel_columns
FROM ssdb_integration.information_schema.columns
GROUP BY table_schema, table_name
HAVING COUNT(CASE WHEN column_name ILIKE '%POLIC%' OR column_name ILIKE '%PLCY%' THEN 1 END) > 0
ORDER BY table_schema, table_name;
