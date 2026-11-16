#!/bin/sh
# Runs 03_assignments.sql in DuckDB on a made-up TERRITORIES table with edit rows put in beside the EXAMPLE row, and
# checks the table and the result against answers worked out by hand: the default (WH or FI holder: Y, WIFI), an edit
# replacing it (matched whatever the case and spacing), an edit with a bad value, a wholesaler on two edits, an edit
# matching nobody, the EXAMPLE row ignored, two spellings of one person one row, a vacancy and a blank name no row.
# Prints "03_assignments_test: ok" or stops at the failed check.  Run from anywhere: sh 03_assignments_test.sh
set -e
here=$(cd "$(dirname "$0")" && pwd)
{
cat <<'SQL'
ATTACH ':memory:' AS ssdb_integration; CREATE SCHEMA ssdb_integration.lr_strategy;
CREATE TABLE ssdb_integration.lr_strategy.terr_t (source TEXT, name TEXT, zip_code TEXT, state TEXT, channel TEXT,
  clean_name TEXT, clean_id TEXT);
INSERT INTO ssdb_integration.lr_strategy.terr_t (source, name, zip_code, state, channel, clean_name) VALUES
  ('A','Ann Lee','2134','MA','WH',NULL), ('A','Ann Lee','02135','MA','WH','  '), ('A','x','02135','NH','fi',' ann  lee'),
  ('A','Abe Orr','02134','MA','IFA',NULL), ('A','Bo Ray','02139','MA','FI',NULL), ('A','Cal Poe','02134','MA','IFA',NULL),
  ('A','Open','02136','MA','FI',NULL), ('A','  ','02137','MA','FI',NULL),
  ('B','Ann Lee','02134','MA','WH',NULL), ('B','Gil Hu','02134','ma','FI',NULL), ('B','Gil Hu','02134','MA','PRI',NULL);
SQL
# DuckDB has no LISTAGG ... WITHIN GROUP: string_agg with ORDER BY.  REGEXP_REPLACE as in 02_model_extract_test.sh
sed -e "s/LISTAGG(\([a-z]*\), ' ') WITHIN GROUP (ORDER BY [a-z]*)/string_agg(\1, ' ' ORDER BY \1)/" \
    -e "s/\\\\\\\\s+', ' ')/\\\\s+', ' ', 'g')/g" -e '/^use /d' -e '/^SET /d' -e 's/TEMPORARY TABLE/TABLE/' \
    -e "s/^  ('EXAMPLE', 'Last, First', 'N', '')\$/  ('EXAMPLE', 'Last, First', 'N', ''), ('a', 'ann  LEE', 'n', ''), ('B', 'Gil Hu', 'Y', 'national'), ('A', 'Abe Orr', 'Y', 'BOSS'), ('A', 'No One', 'Y', 'WH'), ('B', 'Ann Lee', 'N', ''), ('B', 'ann lee', 'Y', 'WH')/" \
    -e 's/^SELECT status, source, wholesaler, current_channels, zips_wh, zips_fi, zips_other, states, kept, role FROM ($/CREATE TABLE full_result AS SELECT status, source, wholesaler, current_channels, zips_wh, zips_fi, zips_other, states, kept, role FROM (/' \
    -e 's/IDENTIFIER(\$terr_tbl)/ssdb_integration.lr_strategy.terr_t/' \
    -e 's/IDENTIFIER(\$assign_tbl)/ssdb_integration.lr_strategy.assign_t/' "$here/03_assignments.sql"
cat <<'SQL'
CREATE MACRO chk(name, got, want) AS CASE WHEN got IS NOT DISTINCT FROM want THEN 'ok'
  ELSE error(name || ': got ' || COALESCE(CAST(got AS VARCHAR), 'NULL') || ', want ' || CAST(want AS VARCHAR)) END;
SELECT
 chk('the table',
     (SELECT string_agg(concat_ws('|', source, wholesaler, current_channels, zips_wh, zips_fi, zips_other, states, kept, role, status), ' / ' ORDER BY source, wholesaler)
      FROM ssdb_integration.lr_strategy.assign_t),
     'A|Abe Orr|IFA|0|0|1|MA|Y|BOSS|KEPT OR ROLE NOT A LISTED VALUE / A|Ann Lee|FI WH|2|1|0|MA NH|N||EDITED / A|Bo Ray|FI|0|1|0|MA|Y|WIFI|DEFAULT'
     || ' / A|Cal Poe|IFA|0|0|1|MA|||DEFAULT / B|Ann Lee|WH|1|0|0|MA|Y|WH|ON 2+ EDIT ROWS / B|Gil Hu|FI PRI|0|1|1|MA|Y|NATIONAL|EDITED'),
 chk('the result: rows to fix first, then WH and FI wholesalers, the unmatched edit shown, EXAMPLE not',
     (SELECT string_agg(concat_ws('|', status, source, wholesaler, kept, role), ' / ' ORDER BY rowid) FROM full_result),
     'EDIT NOT MATCHED: NO SUCH WHOLESALER|A|No One|Y|WH / KEPT OR ROLE NOT A LISTED VALUE|A|Abe Orr|Y|BOSS / ON 2+ EDIT ROWS|B|Ann Lee|Y|WH'
     || ' / EDITED|A|Ann Lee|N| / DEFAULT|A|Bo Ray|Y|WIFI / DEFAULT|A|Cal Poe|| / EDITED|B|Gil Hu|Y|NATIONAL');
SELECT '03_assignments_test: ok';
SQL
} | duckdb -bail -noheader -list
