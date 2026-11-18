#!/bin/sh
# Runs sheet_profile.sql in DuckDB on a made-up sheet and territories table and checks its one result against answers
# worked out by hand: a name matched to both firms whatever its case and spacing, "Last, First" flipped to match CRBG,
# a double space in a holder's name, a vacancy (OPEN) and a non-WH/FI holder left out of NOT IN SHEET, a blank name,
# state and channel, an empty comment not counted, a state no territory has (Texas, XX), a name with no holder.
# Prints "sheet_profile_test: ok" or stops at the failed check.  Run from anywhere: sh sheet_profile_test.sh
set -e
here=$(cd "$(dirname "$0")" && pwd)
{
cat <<'SQL'
ATTACH ':memory:' AS ssdb_integration; CREATE SCHEMA ssdb_integration.lr_strategy;
CREATE TABLE ssdb_integration.lr_strategy.terr_t (source TEXT, name TEXT, zip_code TEXT, state TEXT, channel TEXT,
  clean_name TEXT, clean_id TEXT);
INSERT INTO ssdb_integration.lr_strategy.terr_t (source, name, state, channel, clean_name) VALUES
  ('CRBG','Lee, Ann','MA','WH',NULL), ('CRBG','x','NH','FI','Orr, Abe'), ('CRBG','Kim, Dot','MA','IFA',NULL),
  ('EQH','Ann Lee','MA','FI','  '), ('EQH','Gil Hu','ma','WH',NULL), ('EQH','Open','MA','FI',NULL), ('EQH','Bo  Ray','CT','WH',NULL);
CREATE TABLE ssdb_integration.lr_strategy.sheet_t (name TEXT, state TEXT, comment TEXT, channel TEXT);
INSERT INTO ssdb_integration.lr_strategy.sheet_t VALUES
  ('Ann Lee','MA',NULL,'WH'), ('ann  lee','nh','',' wh'), ('Orr, Abe','Texas','keep','FI'), ('Bo Ray',NULL,NULL,NULL),
  ('No One','XX',NULL,'NATIONAL'), ('  ','MA',NULL,'FI');
SQL
sed -e "s/LISTAGG(DISTINCT h.src, ' ') WITHIN GROUP (ORDER BY h.src)/string_agg(DISTINCT h.src, ' ' ORDER BY h.src)/" \
    -e "s/'\\\\\\\\s+', ' ')/'\\\\s+', ' ', 'g')/g" -e '/^use /d' -e '/^SET /d' \
    -e 's/IDENTIFIER(\$sheet_tbl)/ssdb_integration.lr_strategy.sheet_t/' \
    -e 's/IDENTIFIER(\$terr_tbl)/ssdb_integration.lr_strategy.terr_t/' \
    -e 's/^WITH$/CREATE TABLE res AS WITH/' \
    -e 's/^SELECT section, item, n_rows, n_names FROM r ORDER BY o, item;$/SELECT row_number() OVER (ORDER BY o, item) AS i, section, item, n_rows, n_names FROM r;/' \
    "$here/sheet_profile.sql"
cat <<'SQL'
CREATE MACRO chk(name, got, want) AS CASE WHEN got IS NOT DISTINCT FROM want THEN 'ok'
  ELSE error(name || ': got ' || COALESCE(CAST(got AS VARCHAR), 'NULL') || ', want ' || CAST(want AS VARCHAR)) END;
SELECT chk('the result',
  (SELECT string_agg(concat_ws('|', section, item, COALESCE(CAST(n_rows AS VARCHAR), '-'), COALESCE(CAST(n_names AS VARCHAR), '-')), ' / ' ORDER BY i) FROM res),
  'ROWS|blank channel|1|1 / ROWS|blank name|1|- / ROWS|blank state|1|1 / ROWS|name written with a comma|1|1'
  || ' / ROWS|names on 2+ rows|-|1 / ROWS|rows|6|4 / ROWS|with a comment|1|1'
  || ' / CHANNEL|(blank)|1|1 / CHANNEL|FI|2|1 / CHANNEL|NATIONAL|1|1 / CHANNEL|WH|2|1'
  || ' / STATE|TEXAS|1|1 / STATE|XX|1|1'
  || ' / MATCH|CRBG|1|1 / MATCH|CRBG EQH|2|1 / MATCH|EQH|1|1 / MATCH|NO HOLDER|1|1'
  || ' / NOT IN SHEET|EQH|-|1');
SELECT 'sheet_profile_test: ok';
SQL
} | duckdb -bail -noheader -list
