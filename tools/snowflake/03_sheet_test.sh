#!/bin/sh
# Runs 03_assignments.sql in DuckDB with a made-up shortlist sheet (state x channel slots) and checks the table and the
# result against answers worked out by hand: a REGIONAL person matched to a CRBG "Last, First" holder whatever the case
# and spacing, kept WIFI with the codes of two full state names; a NATIONAL person on two states; a person on two
# channels (TWO ANSWERS); an unknown state (NARNIA) and channel (BOSS), a blank state and a blank channel flagged; a name no holder has (EDIT NOT MATCHED,
# source SHEET); a cell with several names (Cal Poe OR/ Di Fox: OR then a slash is one split, Ed Gray/Zed Zo oR new two, jo lin or Ty Ash: the word OR in any
# case, a slash without spaces, three names, a name only inside such a cell not KEPT N) each name on its own, STATUS EDITED
# (EITHER, also when the person has a single-name row on the same channel too: Jo Lin), a split name no holder has EDIT NOT MATCHED, a person in an or-cell and on another channel TWO ANSWERS (an error
# status wins over EITHER); open seats (no name, a tab-only name) setting nothing; WH or FI holders not on the sheet KEPT N; a holder in neither WH
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
  ('EQH','Zed Zo','04001','ME','IFA',NULL), ('EQH','Open','02134','MA','FI',NULL), ('EQH','Al Pim','84001','UT','WH',NULL),
  ('CRBG','Ng, Mo','84001','UT','FI',NULL), ('CRBG','Poe, Cal','50001','IA','WH',NULL), ('EQH','Di Fox','50001','IA','WH',NULL),
  ('EQH','Ed Gray','89001','NV','WH',NULL), ('EQH','Jo Lin','84002','UT','FI',NULL), ('CRBG','Ty Ash','84003','UT','FI',NULL),
  ('EQH','Ivy Ode','43002','OH','IFA',NULL);
CREATE TABLE ssdb_integration.lr_strategy.sheet_t (name TEXT, state TEXT, comment TEXT, channel TEXT);
INSERT INTO ssdb_integration.lr_strategy.sheet_t VALUES
  ('Ann Lee','MASSACHUSETTS',NULL,'REGIONAL'), ('ann  lee',' New  Hampshire','x','regional'),
  ('Abe Orr','Texas',NULL,'NATIONAL'), ('Abe Orr','Ohio',NULL,'NATIONAL'),
  ('Gil Hu','MAINE',NULL,'WH'), ('Gil Hu','Maine',NULL,'REGIONAL'),
  ('Dot Kim','Narnia',NULL,'WH'), ('Bo Ray','Connecticut',NULL,'BOSS'), ('New Hire','Iowa',NULL,'WH'),
  ('  ','Utah',NULL,'WH'), (NULL,'Utah',NULL,'NATIONAL'), (chr(9),'Utah',NULL,'WH'),
  ('Al Pim','Utah',NULL,NULL), ('Mo Ng','Utah',NULL,'WH'), ('Mo Ng','  ',NULL,'WH'),
  ('Cal Poe OR/ Di Fox','Iowa',NULL,'WH'), ('Ed Gray/Zed Zo oR new two','Nevada',NULL,'NATIONAL'), ('Ed Gray','Nevada',NULL,'WH'),
  ('jo lin or Ty Ash','Utah',NULL,'FI'), ('Jo Lin','Utah',NULL,'FI'),
  ('TBD','Utah',NULL,'WH'), ('n/a','Utah',NULL,'NATIONAL'), (' Open ','Utah',NULL,'FI');
CREATE MACRO UUID_STRING(ns, nm) AS md5(ns || nm);
CREATE TABLE ssdb_integration.lr_strategy.hk_t (source TEXT, holder_id TEXT, holder_n INTEGER, first_seen TIMESTAMP);
SQL
# The same DuckDB translation as 03_assignments_test.sh.
sed -e "s/LISTAGG(\([a-z]*\), ' ') WITHIN GROUP (ORDER BY [a-z]*)/string_agg(\1, ' ' ORDER BY \1)/" \
    -e "s/\\\\\\\\s+', ' ')/\\\\s+', ' ', 'g')/g" -e "s/\\\\\\\\s/\\\\s/g" -e "s/', '|')/', '|', 'g')/" \
    -e "s/LATERAL SPLIT_TO_TABLE(\\(x\\.[a-z_]*\\), '|') p/LATERAL (SELECT unnest(string_split(\\1, '|')) AS value) p/" -e "s/[\$]scenario/''/g" -e '/^use /d' -e '/^SET /d' -e 's/TEMPORARY TABLE/TABLE/' \
    -e 's/TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()/TIMESTAMP DEFAULT now()/' \
    -e 's/^SELECT status, source, wholesaler, current_channels, zips_wh, zips_fi, zips_other, states, kept, role, assigned_states FROM ($/CREATE TABLE full_result AS &/' \
    -e "s/LISTAGG(DISTINCT \(.*\), ' ')\$/string_agg(DISTINCT \1, ' '/" -e "s/^ *WITHIN GROUP (ORDER BY \(.*\))\$/ ORDER BY \1)/" \
    -e 's/ FROM VALUES$/ FROM (VALUES/' -e "s/('WYOMING', 'WY')) c ON/('WYOMING', 'WY')) v(column1, column2)) c ON/" \
    -e 's/IDENTIFIER(\$sheet_tbl)/ssdb_integration.lr_strategy.sheet_t/g' \
    -e 's/IDENTIFIER(\$holder_tbl)/ssdb_integration.lr_strategy.hk_t/' \
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
     || ' / CRBG|Lee, Ann|Y|WIFI|MA NH|EDITED / CRBG|Ng, Mo|Y|WH|BLANK_STATE UT|ASSIGNED_STATES CODE NOT A STATE (OR TWICE)'
     || ' / CRBG|Orr, Abe|Y|NATIONAL|OH TX|EDITED / CRBG|Poe, Cal|Y|WH|IA|EDITED (EITHER) / CRBG|Ty Ash|Y|FI|UT|EDITED (EITHER)'
     || ' / EQH|Al Pim|Y|BLANK CHANNEL|UT|KEPT OR ROLE NOT A LISTED VALUE'
     || ' / EQH|Bo  Ray|Y|BOSS|CT|KEPT OR ROLE NOT A LISTED VALUE / EQH|Cy Day|N|WIFI||EDITED'
     || ' / EQH|Di Fox|Y|WH|IA|EDITED (EITHER) / EQH|Ed Gray|Y|WH|NV|TWO ANSWERS IN ONE EDIT STATEMENT'
     || ' / EQH|Gil Hu|Y|WIFI|ME|TWO ANSWERS IN ONE EDIT STATEMENT / EQH|Ivy Ode||||DEFAULT'
     || ' / EQH|Jo Lin|Y|FI|UT|EDITED (EITHER) / EQH|Zed Zo|Y|NATIONAL|NV|EDITED (EITHER)'),
 chk('the unmatched name',
     (SELECT string_agg(concat_ws('|', source, wholesaler, kept, role, assigned_states), ' / ' ORDER BY wholesaler) FROM full_result
      WHERE status = 'EDIT NOT MATCHED: NO SUCH WHOLESALER'),
     'SHEET|New Hire|Y|WH|IA / SHEET|new two|Y|NATIONAL|NV');
SELECT '03_sheet_test: ok';
SQL
} | duckdb -bail -noheader -list
