#!/bin/sh
# Runs 03_assignments.sql in DuckDB with a made-up shortlist sheet (state x channel slots) and checks the table and the
# result against answers worked out by hand: a REGIONAL person matched to a CRBG "Last, First" holder whatever the case
# and spacing, kept WIFI with the codes of two full state names; a NATIONAL person on two states; a person on two
# channels (TWO ANSWERS); an unknown state (NARNIA) and channel (BOSS) flagged; a name no holder has (EDIT NOT MATCHED,
# source SHEET); open seats (no name) setting nothing; WH or FI holders not on the sheet KEPT N; a holder in neither WH
# nor FI left at the default.  The edit block (EXAMPLE only) is untouched.
# Prints "03_sheet_test: ok" or stops at the failed check.  Run from anywhere: sh 03_sheet_test.sh
set -e
here=$(cd "$(dirname "$0")" && pwd)
{
cat <<'SQL'
ATTACH ':memory:' AS ssdb_integration; CREATE SCHEMA ssdb_integration.lr_strategy;
CREATE TABLE ssdb_integration.lr_strategy.terr_t (source TEXT, name TEXT, zip_code TEXT, state TEXT, channel TEXT,
  clean_name TEXT, clean_id TEXT);
INSERT INTO ssdb_integration.lr_strategy.terr_t (source, name, zip_code, state, channel, clean_name) VALUES
  ('CRBG','Lee, Ann','02134','MA','WH',NULL), ('CRBG','Orr, Abe','03031','NH','FI',NULL), ('CRBG','Kim, Dot','02134','MA','IFA',NULL),
  ('CRBG','Fay, Al','06001','CT','WH',NULL), ('EQH','Gil Hu','02134','MA','WH',NULL), ('EQH','Bo  Ray','06001','CT','FI',NULL),
  ('EQH','Cy Day','02134','MA','WH',NULL), ('EQH','Zed Zo','43001','OH','IFA',NULL), ('EQH','Zed Zo','75001','TX','IFA',NULL),
  ('EQH','Zed Zo','04001','ME','IFA',NULL), ('EQH','Open','02134','MA','FI',NULL);
CREATE TABLE ssdb_integration.lr_strategy.sheet_t (name TEXT, state TEXT, comment TEXT, channel TEXT);
INSERT INTO ssdb_integration.lr_strategy.sheet_t VALUES
  ('Ann Lee','MASSACHUSETTS',NULL,'REGIONAL'), ('ann  lee',' New  Hampshire','x','regional'),
  ('Abe Orr','Texas',NULL,'NATIONAL'), ('Abe Orr','Ohio',NULL,'NATIONAL'),
  ('Gil Hu','MAINE',NULL,'WH'), ('Gil Hu','Maine',NULL,'REGIONAL'),
  ('Dot Kim','Narnia',NULL,'WH'), ('Bo Ray','Connecticut',NULL,'BOSS'), ('New Hire','Iowa',NULL,'WH'),
  ('  ','Utah',NULL,'WH'), (NULL,'Utah',NULL,'NATIONAL');
SQL
# The same DuckDB translation as 03_assignments_test.sh.
sed -e "s/LISTAGG(\([a-z]*\), ' ') WITHIN GROUP (ORDER BY [a-z]*)/string_agg(\1, ' ' ORDER BY \1)/" \
    -e "s/\\\\\\\\s+', ' ')/\\\\s+', ' ', 'g')/g" -e '/^use /d' -e '/^SET /d' -e 's/TEMPORARY TABLE/TABLE/' \
    -e 's/TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()/TIMESTAMP DEFAULT now()/' \
    -e 's/^SELECT status, source, wholesaler, current_channels, zips_wh, zips_fi, zips_other, states, kept, role, assigned_states FROM ($/CREATE TABLE full_result AS &/' \
    -e "s/LISTAGG(DISTINCT \(.*\), ' ') WITHIN GROUP (ORDER BY \(.*\))\$/string_agg(DISTINCT \1, ' ' ORDER BY \2)/" \
    -e 's/ FROM VALUES$/ FROM (VALUES/' -e "s/('WYOMING', 'WY')) c ON/('WYOMING', 'WY')) v(column1, column2)) c ON/" \
    -e 's/IDENTIFIER(\$sheet_tbl)/ssdb_integration.lr_strategy.sheet_t/g' \
    -e 's/IDENTIFIER(\$terr_tbl)/ssdb_integration.lr_strategy.terr_t/' \
    -e 's/IDENTIFIER(\$assign_tbl)/ssdb_integration.lr_strategy.assign_t/' "$here/03_assignments.sql"
cat <<'SQL'
CREATE MACRO chk(name, got, want) AS CASE WHEN got IS NOT DISTINCT FROM want THEN 'ok'
  ELSE error(name || ': got ' || COALESCE(CAST(got AS VARCHAR), 'NULL') || ', want ' || CAST(want AS VARCHAR)) END;
SELECT
 chk('the table',
     (SELECT string_agg(concat_ws('|', source, wholesaler, kept, role, assigned_states, status), ' / ' ORDER BY source, wholesaler)
      FROM ssdb_integration.lr_strategy.assign_t),
     'CRBG|Fay, Al|N|WIFI||EDITED / CRBG|Kim, Dot|Y|WH|NARNIA|ASSIGNED_STATES CODE NOT A STATE (OR TWICE)'
     || ' / CRBG|Lee, Ann|Y|WIFI|MA NH|EDITED / CRBG|Orr, Abe|Y|NATIONAL|OH TX|EDITED'
     || ' / EQH|Bo  Ray|Y|BOSS|CT|KEPT OR ROLE NOT A LISTED VALUE / EQH|Cy Day|N|WIFI||EDITED'
     || ' / EQH|Gil Hu|Y|WIFI|ME|TWO ANSWERS IN ONE EDIT STATEMENT / EQH|Zed Zo||||DEFAULT'),
 chk('the unmatched name',
     (SELECT string_agg(concat_ws('|', source, wholesaler, kept, role, assigned_states), ' / ') FROM full_result
      WHERE status = 'EDIT NOT MATCHED: NO SUCH WHOLESALER'),
     'SHEET|New Hire|Y|WH|IA');
SELECT '03_sheet_test: ok';
SQL
} | duckdb -bail -noheader -list
