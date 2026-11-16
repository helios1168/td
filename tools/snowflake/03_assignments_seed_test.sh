#!/bin/sh
# Runs 03_assignments_seed.sql in DuckDB on a made-up TERRITORIES table and checks the roster against the answer worked
# out by hand: two spellings of one person are one row, a vacancy and a blank name are no row, firm 2's BD and BK count
# as WH and FI, one person in two sources has two rows, WH and FI wholesalers come first.
# Prints "03_assignments_seed_test: ok" or stops at the failed check.  Run from anywhere: sh 03_assignments_seed_test.sh
set -e
here=$(cd "$(dirname "$0")" && pwd)
{
cat <<'SQL'
ATTACH ':memory:' AS ssdb_integration; CREATE SCHEMA ssdb_integration.lr_strategy;
CREATE TABLE ssdb_integration.lr_strategy.terr_t (source TEXT, name TEXT, zip_code TEXT, state TEXT, channel TEXT,
  clean_name TEXT, clean_id TEXT);
INSERT INTO ssdb_integration.lr_strategy.terr_t (source, name, zip_code, state, channel, clean_name) VALUES
  ('A','Ann Lee','2134','MA','WH',NULL), ('A','Ann Lee','02135','MA','WH','  '), ('A','x','02135','NH','fi',' ann  lee'),
  ('A','Abe Orr','02134','MA','IFA',NULL), ('A','Open','02136','MA','FI',NULL), ('A','  ','02137','MA','FI',NULL),
  ('B','Ann Lee','02134','MA','BD',NULL), ('B','Gil Hu','02134','ma','BK',NULL), ('B','Gil Hu','02134','MA','RA',NULL);
CREATE TABLE full_result AS
SQL
# DuckDB has no LISTAGG ... WITHIN GROUP: string_agg with ORDER BY.  REGEXP_REPLACE as in 02_model_extract_test.sh
sed -e "s/LISTAGG(\([a-z]*\), ' ') WITHIN GROUP (ORDER BY [a-z]*)/string_agg(\1, ' ' ORDER BY \1)/" \
    -e "s/\\\\\\\\s+', ' ')/\\\\s+', ' ', 'g')/g" -e '/^use /d' -e '/^SET /d' \
    -e 's/IDENTIFIER(\$terr_tbl)/ssdb_integration.lr_strategy.terr_t/' "$here/03_assignments_seed.sql"
cat <<'SQL'
SELECT CASE WHEN got = want THEN 'ok' ELSE error('roster: got ' || got || ', want ' || want) END
FROM (SELECT string_agg(concat_ws('|', source, wholesaler, current_channels, zips_wh, zips_fi, zips_other, states, kept, role), ' / ' ORDER BY rowid) AS got,
             'A|Ann Lee|FI WH|2|1|0|MA NH|| / A|Abe Orr|IFA|0|0|1|MA|| / B|Ann Lee|BD|1|0|0|MA|| / B|Gil Hu|BK RA|0|1|1|MA||' AS want
      FROM full_result);
SELECT '03_assignments_seed_test: ok';
SQL
} | duckdb -bail -noheader -list
