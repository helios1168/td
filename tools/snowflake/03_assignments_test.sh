#!/bin/sh
# Runs 03_assignments.sql in DuckDB on a made-up TERRITORIES table with edits put in, and checks the table and the result
# against answers worked out by hand: the default (WH or FI holder: Y, WIFI), an edit replacing it (matched whatever the
# case and spacing), the same answer twice (fine), a bad value, two answers in one statement (flagged), a later statement
# winning over an earlier one (Bo Ray: N by row, then FI by a rule on the roster before edits), an edit matching nobody
# (shown once), states set apart from the role (Ann: states by a later statement keep her KEPT N; Gil: the later
# states win), edits by holder key (Cal Poe by R5 alone, Dot Kim by R4 while the row also names a nobody: the key is used, a later key edit ' r3' after name
# edits wins and an earlier key edit loses to a later name edit: Abe Orr R2 role WH then BOSS, a key no roster row has (R8 is in the key table, R99 is not) EDIT NOT MATCHED with the key shown),
# an unknown code (XX), states checked against the territories' STATE (ma counts as MA), the EXAMPLE row ignored, two spellings of one person one row, a vacancy and a blank name no row.
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
  ('A','Abe Orr','02134','MA','IFA',NULL), ('A','Bo Ray','02139','MA','FI',NULL), ('A','Dot Kim','02134','MA','WH',NULL), ('A','Cal Poe','02134','MA','IFA',NULL),
  ('A','Open','02136','MA','FI',NULL), ('A','  ','02137','MA','FI',NULL),
  ('B','Ann Lee','02134','MA','WH',NULL), ('B','Gil Hu','02134','ma','FI',NULL), ('B','Gil Hu','02134','MA','PRI',NULL);
-- no named person on the shortlist sheet: the sheet sets nothing (03_sheet_test.sh tests the sheet)
CREATE TABLE ssdb_integration.lr_strategy.sheet_t (name TEXT, state TEXT, comment TEXT, channel TEXT);
-- a tab-only name is no name: still nothing set
INSERT INTO ssdb_integration.lr_strategy.sheet_t VALUES (chr(9), 'Utah', NULL, 'WH');
CREATE MACRO UUID_STRING(ns, nm) AS md5(ns || nm);
CREATE TABLE ssdb_integration.lr_strategy.hk_t (source TEXT, holder_id TEXT, holder_n INTEGER, first_seen TIMESTAMP);
-- the holder key (02 owns it), numbers worked out by hand: R1 A Ann Lee, R2 A Abe Orr, R3 A Bo Ray, R4 A Dot Kim, R5 A Cal Poe,
-- R6 B Ann Lee, R7 B Gil Hu, R8 a key whose holder is not in the territories table
INSERT INTO ssdb_integration.lr_strategy.hk_t SELECT source, UUID_STRING('6ba7b810-9dad-11d1-80b4-00c04fd430c8', nm), n, now()
FROM (VALUES ('A','ANN LEE',1), ('A','ABE ORR',2), ('A','BO RAY',3), ('A','DOT KIM',4), ('A','CAL POE',5), ('B','ANN LEE',6),
             ('B','GIL HU',7), ('A','NOBODY HOME',8)) v(source, nm, n);
SQL
# DuckDB has no LISTAGG ... WITHIN GROUP: string_agg with ORDER BY.  REGEXP_REPLACE as in 02_model_extract_test.sh.
# The edits: rows beside the EXAMPLE row (one statement), then a later rule from the roster before edits.
sed -e "s/LISTAGG(\([a-z]*\), ' ') WITHIN GROUP (ORDER BY [a-z]*)/string_agg(\1, ' ' ORDER BY \1)/" \
    -e "s/\\\\\\\\s+', ' ')/\\\\s+', ' ', 'g')/g" -e "s/\\\\\\\\s/\\\\s/g" -e "s/', '|')/', '|', 'g')/" \
    -e "s/LATERAL SPLIT_TO_TABLE(\\(x\\.[a-z_]*\\), '|') p/LATERAL (SELECT unnest(string_split(\\1, '|')) AS value) p/" -e "s/[\$]scenario/''/g" -e '/^use /d' -e '/^SET /d' -e 's/TEMPORARY TABLE/TABLE/' \
    -e 's/TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()/TIMESTAMP DEFAULT now()/' \
    -e "s/^  ('EXAMPLE', 'Last, First', 'N', '');\$/  ('EXAMPLE', 'Last, First', 'N', ''), ('a', 'ann  LEE', 'n', ''), ('B', 'Gil Hu', 'Y', 'national'), ('B', 'gil hu', 'y', 'NATIONAL'), ('A', 'Abe Orr', 'Y', 'BOSS'), ('A', 'No One', 'Y', 'WH'), ('A', 'No One', 'Y', 'WH'), ('B', 'Ann Lee', 'N', ''), ('B', 'ann lee', 'Y', 'WH'), ('A', 'Bo Ray', 'N', '');/" \
    -e "s/^--key edits: end\$/INSERT INTO ssdb_integration.lr_strategy.tmp_m_edit (holder, kept, role) VALUES ('R5', 'Y', 'FI'), ('R2', 'Y', 'WH'), ('R8', 'Y', 'WH'), ('R99', 'Y', 'WH'); INSERT INTO ssdb_integration.lr_strategy.tmp_m_edit (holder, assigned_states) VALUES ('R1', 'MA'); INSERT INTO ssdb_integration.lr_strategy.tmp_m_edit (source, wholesaler, holder, kept) VALUES ('A', 'No One', 'R4', 'N');/" \
    -e "s/^--owner edits: end\$/INSERT INTO ssdb_integration.lr_strategy.tmp_m_edit (source, wholesaler, kept, role) SELECT source, wholesaler, 'Y', 'FI' FROM ssdb_integration.lr_strategy.tmp_m_base WHERE wholesaler ILIKE '%ray%' AND current_channels = 'FI'; INSERT INTO ssdb_integration.lr_strategy.tmp_m_edit (source, wholesaler, assigned_states) VALUES ('A', 'Bo Ray', 'ma,  nh'), ('B', 'Gil Hu', 'MA XX'), ('A', 'Dot Kim', 'MA XX'); INSERT INTO ssdb_integration.lr_strategy.tmp_m_edit (source, wholesaler, assigned_states) VALUES ('A', 'Ann Lee', 'NH'), ('B', 'Gil Hu', 'MA'); INSERT INTO ssdb_integration.lr_strategy.tmp_m_edit (holder, assigned_states) VALUES (' r3', 'NH');/" \
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
     (SELECT string_agg(concat_ws('|', source, wholesaler, current_channels, zips_wh, zips_fi, zips_other, states, kept, role, assigned_states, status), ' / ' ORDER BY source, wholesaler)
      FROM ssdb_integration.lr_strategy.assign_t),
     'A|Abe Orr|IFA|0|0|1|MA|Y|BOSS||KEPT OR ROLE NOT A LISTED VALUE / A|Ann Lee|FI WH|2|1|0|MA NH|N||NH|EDITED'
     || ' / A|Bo Ray|FI|0|1|0|MA|Y|FI|NH|EDITED / A|Cal Poe|IFA|0|0|1|MA|Y|FI||EDITED'
     || ' / A|Dot Kim|WH|1|0|0|MA|N|WIFI|MA XX|ASSIGNED_STATES CODE NOT A STATE (OR TWICE)'
     || ' / B|Ann Lee|WH|1|0|0|MA|Y|WH||TWO ANSWERS IN ONE EDIT STATEMENT / B|Gil Hu|FI PRI|0|1|1|MA|Y|NATIONAL|MA|EDITED'),
 chk('the result: rows to fix first, then WH and FI wholesalers, the unmatched edit shown, EXAMPLE not',
     (SELECT string_agg(concat_ws('|', status, source, wholesaler, kept, role, assigned_states), ' / ' ORDER BY rowid) FROM full_result),
     'EDIT NOT MATCHED: NO SUCH WHOLESALER|A|No One|Y|WH / EDIT NOT MATCHED: NO SUCH WHOLESALER|KEY|R8|Y|WH / EDIT NOT MATCHED: NO SUCH WHOLESALER|KEY|R99|Y|WH'
     || ' / ASSIGNED_STATES CODE NOT A STATE (OR TWICE)|A|Dot Kim|N|WIFI|MA XX'
     || ' / KEPT OR ROLE NOT A LISTED VALUE|A|Abe Orr|Y|BOSS| / TWO ANSWERS IN ONE EDIT STATEMENT|B|Ann Lee|Y|WH|'
     || ' / EDITED|A|Ann Lee|N||NH / EDITED|A|Bo Ray|Y|FI|NH / EDITED|A|Cal Poe|Y|FI| / EDITED|B|Gil Hu|Y|NATIONAL|MA');
SELECT '03_assignments_test: ok';
SQL
} | duckdb -bail -noheader -list
