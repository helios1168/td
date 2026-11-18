#!/bin/sh
# Runs key_names.sql in DuckDB on a made-up sheet, territories table and holder key and checks its one result against
# answers worked out by hand: a holder on two sheet channels (TWO_CHANNELS 1, first), an "or" cell (either, on both its
# keys), a "Last, First" holder matched to a "First Last" sheet name, the slots and comments joined, a TBD seat naming
# nobody, a holder not on the sheet after the sheet's, a holder with no td_holder_key row left out.
# Prints "key_names_test: ok" or stops at the failed check.  Run from anywhere: sh key_names_test.sh
set -e
here=$(cd "$(dirname "$0")" && pwd)
{
cat <<'SQL'
ATTACH ':memory:' AS ssdb_integration; CREATE SCHEMA ssdb_integration.lr_strategy;
CREATE MACRO UUID_STRING(ns, nm) AS md5(ns || nm);
CREATE TABLE ssdb_integration.lr_strategy.terr_t (source TEXT, name TEXT, zip_code TEXT, state TEXT, channel TEXT,
  clean_name TEXT, clean_id TEXT);
INSERT INTO ssdb_integration.lr_strategy.terr_t (source, name, zip_code, state, channel, clean_name) VALUES
  ('CRBG','Lee, Ann','02134','MA','WH',NULL), ('CRBG','Lee, Ann','02135','MA','FI',NULL), ('EQH','Bo Ray','06001','CT','WH',NULL),
  ('EQH','Cy Day','03031','NH','FI',NULL), ('CRBG','Kim, Dot','02134','MA','IFA',NULL), ('EQH','Open','02139','MA','FI',NULL);
CREATE TABLE ssdb_integration.lr_strategy.hk_t (source TEXT, holder_id TEXT, holder_n INTEGER, first_seen TIMESTAMP);
INSERT INTO ssdb_integration.lr_strategy.hk_t SELECT source, UUID_STRING('6ba7b810-9dad-11d1-80b4-00c04fd430c8', nm), n, now()
FROM (VALUES ('CRBG','LEE, ANN',1), ('EQH','BO RAY',2), ('EQH','CY DAY',3)) v(source, nm, n);
CREATE TABLE ssdb_integration.lr_strategy.sheet_t (name TEXT, state TEXT, comment TEXT, channel TEXT);
INSERT INTO ssdb_integration.lr_strategy.sheet_t VALUES
  ('Ann Lee','MASSACHUSETTS','keep her','REGIONAL'), ('ann  lee','NEW HAMPSHIRE',NULL,'NATIONAL'),
  ('Ann Lee or Bo Ray','CALIFORNIA','pick one','NATIONAL'), ('TBD','UTAH',NULL,'WH');
SQL
# DuckDB: string_agg for LISTAGG ... WITHIN GROUP, unnest of string_split for SPLIT_TO_TABLE (python, stdlib only).
python3 - "$here/key_names.sql" <<'PY'
import re, sys
t = open(sys.argv[1]).read()
t = re.sub(r"(?m)^use .*\n|^SET .*\n", "", t)
t = t.replace("\\\\s", "\\s").replace("'\\s+', ' ')", "'\\s+', ' ', 'g')").replace("', '|')", "', '|', 'g')")
t = re.sub(r"LATERAL SPLIT_TO_TABLE\((x\.[a-z_]+), '\|'\) p",
           r"LATERAL (SELECT unnest(string_split(\1, '|')) AS value, generate_subscripts(string_split(\1, '|'), 1) AS index) p", t)
t = re.sub(r"LISTAGG\((.*?), ('[^']*')\)\s*WITHIN GROUP \(ORDER BY (.*?)\)( AS [a-z_]+)", r"string_agg(\1, \2 ORDER BY \3)\4", t, flags=re.S)
t = t.replace("IDENTIFIER($sheet_tbl)", "ssdb_integration.lr_strategy.sheet_t").replace("IDENTIFIER($terr_tbl)", "ssdb_integration.lr_strategy.terr_t")
t = t.replace("IDENTIFIER($holder_tbl)", "ssdb_integration.lr_strategy.hk_t").replace("CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.key_names AS", "CREATE TABLE res AS")
t = t.replace("FROM ssdb_integration.lr_strategy.key_names ORDER BY row_n", "FROM res ORDER BY row_n")
print(t)
PY
cat <<'SQL'
CREATE MACRO chk(name, got, want) AS CASE WHEN got IS NOT DISTINCT FROM want THEN 'ok'
  ELSE error(name || ': got ' || COALESCE(CAST(got AS VARCHAR), 'NULL') || ', want ' || CAST(want AS VARCHAR)) END;
SELECT chk('the result',
  (SELECT string_agg(concat_ws('|', key, name, current_channels, zips_wh, zips_fi, states, COALESCE(sheet_slots, '-'),
                               COALESCE(sheet_channels, '-'), COALESCE(CAST(two_channels AS VARCHAR), '-'), COALESCE(sheet_comments, '-')), ' / '
          ORDER BY CASE WHEN sheet_slots IS NULL THEN 1 ELSE 0 END, two_channels DESC, key) FROM res),
  'CRBG:R1|Lee, Ann|FI WH|1|1|MA|CALIFORNIA NATIONAL either; MASSACHUSETTS REGIONAL; NEW HAMPSHIRE NATIONAL|NATIONAL REGIONAL|1|keep her | pick one'
  || ' / EQH:R2|Bo Ray|WH|1|0|CT|CALIFORNIA NATIONAL either|NATIONAL|0|pick one / EQH:R3|Cy Day|FI|0|1|NH|-|-|-|-');
SELECT 'key_names_test: ok';
SQL
} | duckdb -bail -noheader -list
