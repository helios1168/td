--The columns of every table the analysis reads, from INFORMATION_SCHEMA.  Run All; send statement 3's output (text).
--Snowflake docs, read 2026-10-30 (https://docs.snowflake.com/en/sql-reference/info-schema, .../info-schema/tables,
--.../info-schema/columns): one INFORMATION_SCHEMA per database; unquoted names are stored in uppercase, so filter in
--uppercase; only objects the current role can access are returned; a query without a selective enough filter fails
--("Information schema query returned too much data"), so every query filters on TABLE_SCHEMA.
use secondary roles all;

--1. Find the tables: ours and yours in LR_STRATEGY, newest first.  Add a LIKE for each source's own table prefix (kept
--out of the repo); then type the names into statement 2's list.
SELECT table_name, table_type, row_count, bytes, created, last_altered
FROM ssdb_integration.information_schema.tables
WHERE table_schema = 'LR_STRATEGY'
  AND (table_name LIKE '%MM%' OR table_name LIKE '%FIRM%'
       OR table_name LIKE '%OPP%' OR table_name LIKE '%TERR%' OR table_name LIKE '%MAP%' OR table_name LIKE '%SALES%')
ORDER BY last_altered DESC;

--2. The columns, one row each.  EDIT the second list: type the real names over the <...> placeholders (an untyped
--placeholder matches nothing).
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_schema AS
SELECT table_catalog, table_schema, table_name, ordinal_position, column_name, data_type, is_nullable, comment
FROM life_prod.information_schema.columns
WHERE table_schema = 'LIF_MURKYLAKE'
  AND table_name IN ('SLS_RPT_DETAIL', 'WC_SALES_DISTRICT', 'WC_SALES_TEAM', 'WC_SBL_CONTACT', 'WC_SBL_ADDR', 'WHSLR',
                     'WC_EDW_CONSOL_BRKR_DEALER_MGA_MASTER', 'WC_MARKET_METRICS_OPPORTUNITY', 'RGN_WHSLR',
                     'GEOGRAPHIC_REGION')
UNION ALL
SELECT table_catalog, table_schema, table_name, ordinal_position, column_name, data_type, is_nullable, comment
FROM ssdb_integration.information_schema.columns
WHERE table_schema = 'LR_STRATEGY'
  AND table_name IN ('MGA_MAP', 'MM_MAP', 'OPP_ORIGINAL', '<SOURCE 2 CRD MAP>', '<SOURCE 1 TERRITORIES>',
                     '<SOURCE 2 TERRITORIES>', '<SOURCE 2 SALES>', '<FIRST-PASS MASTER>');

SELECT * FROM ssdb_integration.lr_strategy.tmp_schema ORDER BY table_catalog, table_schema, table_name, ordinal_position;

--3. One line per table, to paste as text.  A table missing here: its name differs (statement 1) or the role cannot
--see it.
SELECT table_catalog || '.' || table_schema || '.' || table_name AS tbl, COUNT(*) AS n_cols,
       LISTAGG(column_name || ' ' || data_type, ', ') WITHIN GROUP (ORDER BY ordinal_position) AS cols
FROM ssdb_integration.lr_strategy.tmp_schema
GROUP BY 1
ORDER BY 1;
