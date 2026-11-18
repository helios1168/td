#!/bin/sh
# Runs 03_assignments.sql in DuckDB per scenario on a made-up TERRITORIES table, holder key (R47 Ann Lee CRBG, R108 Bo Ray
# EQH, R105 Cy Day EQH, R7 Dee Fox EQH, R3 Eve Ng CRBG) and shortlist sheet where Ann and Bo share two "or" cells (CA
# NATIONAL, CA REGIONAL) and Cy is on TX NATIONAL and TX REGIONAL: the sheet alone flags all three TWO ANSWERS.  Checks, with
# answers worked out by hand (comments at each case): no scenario; the three scenarios in the file (CA1_R105N, CA2_R105N,
# CA1_R105R: the key edit's ROLE wins, STATUS no longer TWO ANSWERS, kept and states stay from the sheet); the name in any
# case with spaces; an undefined scenario (first result row SCENARIO NOT DEFINED, table built without scenario edits); a key edit
# with scenario NULL applying under every scenario (and, placed before the scenario rows, losing to them), and an unmatched key
# reported only under the scenario that names it.
# Order relied on: each INSERT is its own autocommit statement, so DuckDB's now() (the transaction start) is later for a later
# statement, as in 03_assignments_test.sh; a tie would show as TWO ANSWERS, so the checks fail loudly rather than pass.
# Prints "03_scenario_test: ok" or stops at the failed check.  Run from anywhere: sh 03_scenario_test.sh
set -e
here=$(cd "$(dirname "$0")" && pwd)
nl='
'
# case LABEL SCENARIO BEFORE-SQL AFTER-SQL WANT-TABLE WANT-FLAGS
case_() {
{
cat <<'SQL'
ATTACH ':memory:' AS ssdb_integration; CREATE SCHEMA ssdb_integration.lr_strategy;
CREATE TABLE ssdb_integration.lr_strategy.terr_t (source TEXT, name TEXT, zip_code TEXT, state TEXT, channel TEXT,
  clean_name TEXT, clean_id TEXT);
INSERT INTO ssdb_integration.lr_strategy.terr_t (source, name, zip_code, state, channel, clean_name) VALUES
  ('CRBG','Lee, Ann','90001','CA','WH',NULL), ('EQH','Bo Ray','90002','CA','FI',NULL), ('EQH','Cy Day','75001','TX','WH',NULL),
  ('EQH','Dee Fox','10001','NY','WH',NULL), ('CRBG','Eve Ng','10002','NY','FI',NULL);
CREATE TABLE ssdb_integration.lr_strategy.sheet_t (name TEXT, state TEXT, comment TEXT, channel TEXT);
INSERT INTO ssdb_integration.lr_strategy.sheet_t VALUES
  ('Ann Lee or Bo Ray','California',NULL,'NATIONAL'), ('Bo Ray or Ann Lee','California',NULL,'REGIONAL'),
  ('Cy Day','Texas',NULL,'NATIONAL'), ('Cy Day','Texas',NULL,'REGIONAL'), ('Dee Fox','New York',NULL,'REGIONAL');
CREATE MACRO UUID_STRING(ns, nm) AS md5(ns || nm);
CREATE TABLE ssdb_integration.lr_strategy.hk_t (source TEXT, holder_id TEXT, holder_n INTEGER, first_seen TIMESTAMP);
INSERT INTO ssdb_integration.lr_strategy.hk_t SELECT source, UUID_STRING('6ba7b810-9dad-11d1-80b4-00c04fd430c8', nm), n, now()
FROM (VALUES ('CRBG','LEE, ANN',47), ('EQH','BO RAY',108), ('EQH','CY DAY',105), ('EQH','DEE FOX',7), ('CRBG','EVE NG',3)) v(source, nm, n);
SQL
sed -e "s/LISTAGG(\([a-z]*\), ' ') WITHIN GROUP (ORDER BY [a-z]*)/string_agg(\1, ' ' ORDER BY \1)/" \
    -e "s/\\\\\\\\s+', ' ')/\\\\s+', ' ', 'g')/g" -e "s/\\\\\\\\s/\\\\s/g" -e "s/', '|')/', '|', 'g')/" \
    -e "s/LATERAL SPLIT_TO_TABLE(\\(x\\.[a-z_]*\\), '|') p/LATERAL (SELECT unnest(string_split(\\1, '|')) AS value) p/" \
    -e "s/[\$]scenario/'$2'/g" -e '/^use /d' -e '/^SET /d' -e 's/TEMPORARY TABLE/TABLE/' \
    -e 's/TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()/TIMESTAMP DEFAULT now()/' \
    -e "s/^--key edits: begin\$/&\\
$3/" -e "s/^--key edits: end\$/$4/" \
    -e 's/^SELECT status, source, wholesaler, current_channels, zips_wh, zips_fi, zips_other, states, kept, role, assigned_states FROM ($/CREATE TABLE full_result AS &/' \
    -e "s/LISTAGG(DISTINCT \(.*\), ' ')\$/string_agg(DISTINCT \1, ' '/" -e "s/^ *WITHIN GROUP (ORDER BY \(.*\))\$/ ORDER BY \1)/" \
    -e 's/ FROM VALUES$/ FROM (VALUES/' -e "s/('WYOMING', 'WY')) c ON/('WYOMING', 'WY')) v(column1, column2)) c ON/" \
    -e 's/IDENTIFIER(\$sheet_tbl)/ssdb_integration.lr_strategy.sheet_t/g' \
    -e 's/IDENTIFIER(\$holder_tbl)/ssdb_integration.lr_strategy.hk_t/' \
    -e 's/IDENTIFIER(\$terr_tbl)/ssdb_integration.lr_strategy.terr_t/' \
    -e 's/IDENTIFIER(\$assign_tbl)/ssdb_integration.lr_strategy.assign_t/' "$here/03_assignments.sql"
cat <<SQL
CREATE MACRO chk(name, got, want) AS CASE WHEN got IS NOT DISTINCT FROM want THEN 'ok'
  ELSE error(name || ': got ' || COALESCE(CAST(got AS VARCHAR), 'NULL') || ', want ' || CAST(want AS VARCHAR)) END;
SELECT
 chk('$1 table',
     (SELECT string_agg(concat_ws('|', source, wholesaler, kept, role, assigned_states, status), ' / ' ORDER BY source, wholesaler)
      FROM ssdb_integration.lr_strategy.assign_t), '$5'),
 chk('$1 flags',
     (SELECT COALESCE(string_agg(concat_ws('|', status, source, wholesaler), ' / ' ORDER BY rowid), '') FROM full_result
      WHERE status LIKE 'EDIT NOT MATCHED%' OR status LIKE 'SCENARIO%'), '$6'),
 chk('$1 first row', (SELECT status FROM full_result WHERE rowid = 0), '$7');
SQL
} | duckdb -bail -noheader -list >/dev/null
}
ins='INSERT INTO ssdb_integration.lr_strategy.tmp_m_edit (holder, kept, role, assigned_states, scenario) VALUES'
none=''
# Hand-worked rosters.  Eve Ng holds FI only, is not on the sheet: KEPT N, default role WIFI.  Dee Fox: one REGIONAL row, EDITED.
# Ann/Bo/Cy have two sheet rows with two roles: TWO ANSWERS, and the table shows MAX of the two roles, WIFI.
tail_='CRBG|Eve Ng|N|WIFI||EDITED'
T_NONE="$tail_ / CRBG|Lee, Ann|Y|WIFI|CA|TWO ANSWERS IN ONE EDIT STATEMENT / EQH|Bo Ray|Y|WIFI|CA|TWO ANSWERS IN ONE EDIT STATEMENT / EQH|Cy Day|Y|WIFI|TX|TWO ANSWERS IN ONE EDIT STATEMENT / EQH|Dee Fox|Y|WIFI|NY|EDITED"
# Ann, Bo are in or-cells: EDITED (EITHER); Cy has plain rows: EDITED.
T_CA1N="$tail_ / CRBG|Lee, Ann|Y|NATIONAL|CA|EDITED (EITHER) / EQH|Bo Ray|Y|WIFI|CA|EDITED (EITHER) / EQH|Cy Day|Y|NATIONAL|TX|EDITED / EQH|Dee Fox|Y|WIFI|NY|EDITED"
T_CA2N="$tail_ / CRBG|Lee, Ann|Y|WIFI|CA|EDITED (EITHER) / EQH|Bo Ray|Y|NATIONAL|CA|EDITED (EITHER) / EQH|Cy Day|Y|NATIONAL|TX|EDITED / EQH|Dee Fox|Y|WIFI|NY|EDITED"
T_CA1R="$tail_ / CRBG|Lee, Ann|Y|NATIONAL|CA|EDITED (EITHER) / EQH|Bo Ray|Y|WIFI|CA|EDITED (EITHER) / EQH|Cy Day|Y|WIFI|TX|EDITED / EQH|Dee Fox|Y|WIFI|NY|EDITED"
# the result's rows to fix and flags: none for a defined scenario; the undefined one first
case_ none '' "$none" "$none" "$T_NONE" '' 'TWO ANSWERS IN ONE EDIT STATEMENT'
case_ ca1_r105n 'CA1_R105N' "$none" "$none" "$T_CA1N" '' 'EDITED'
case_ ca2_r105n 'CA2_R105N' "$none" "$none" "$T_CA2N" '' 'EDITED'
case_ ca1_r105r 'CA1_R105R' "$none" "$none" "$T_CA1R" '' 'EDITED'
# name in any case with spaces round it
case_ spelling '  ca1_R105n ' "$none" "$none" "$T_CA1N" '' 'EDITED'
# a scenario no key edit names: first row SCENARIO NOT DEFINED, table as with no scenario
case_ undefined 'NOPE' "$none" "$none" "$T_NONE" 'SCENARIO NOT DEFINED|NOPE' 'SCENARIO NOT DEFINED'
# a NULL-scenario key edit (Dee Fox R7 KEPT N, Eve Ng R3 role FI) applies under every scenario, with none, with an undefined one too
nul="$ins ('R7', 'N', NULL, NULL, NULL); $ins ('R3', NULL, 'FI', NULL, NULL);"
N_NONE="CRBG|Eve Ng|N|FI||EDITED / ${T_NONE#*Eve Ng|N|WIFI||EDITED / }"
N_NONE=$(printf '%s' "$N_NONE" | sed 's#EQH|Dee Fox|Y|WIFI|NY|EDITED#EQH|Dee Fox|N|WIFI|NY|EDITED#')
N_CA1N=$(printf '%s' "$T_CA1N" | sed -e 's#EQH|Dee Fox|Y|WIFI|NY|EDITED#EQH|Dee Fox|N|WIFI|NY|EDITED#' -e 's#Eve Ng|N|WIFI|#Eve Ng|N|FI|#')
case_ null_none '' "$none" "$nul" "$N_NONE" '' 'TWO ANSWERS IN ONE EDIT STATEMENT'
case_ null_ca1n 'CA1_R105N' "$none" "$nul" "$N_CA1N" '' 'EDITED'
case_ null_undefined 'NOPE' "$none" "$nul" "$N_NONE" 'SCENARIO NOT DEFINED|NOPE' 'SCENARIO NOT DEFINED'
# a NULL-scenario row placed before the block's scenario rows loses to them (later statement wins): Ann role FI, then CA1 NATIONAL
case_ null_before 'CA1_R105N' "$ins ('R47', NULL, 'FI', NULL, NULL);" "$none" "$T_CA1N" '' 'EDITED'
# ... and one placed after wins over them
T_AFTER=$(printf '%s' "$T_CA1N" | sed 's#Lee, Ann|Y|NATIONAL|CA#Lee, Ann|Y|FI|CA#')
case_ null_after 'CA1_R105N' "$none" "$ins ('R47', NULL, 'FI', NULL, NULL);" "$T_AFTER" '' 'EDITED'
# an unmatched key: shown only when it applies (NULL scenario: always; CA2_R105N: only under CA2_R105N)
un="$ins ('R999', 'Y', 'WH', NULL, NULL); $ins ('R998', 'Y', 'WH', NULL, 'CA2_R105N');"
case_ unmatched_ca1 'CA1_R105N' "$none" "$un" "$T_CA1N" 'EDIT NOT MATCHED: NO SUCH WHOLESALER|KEY|R999' 'EDIT NOT MATCHED: NO SUCH WHOLESALER'
case_ unmatched_ca2 'CA2_R105N' "$none" "$un" "$T_CA2N" 'EDIT NOT MATCHED: NO SUCH WHOLESALER|KEY|R998 / EDIT NOT MATCHED: NO SUCH WHOLESALER|KEY|R999' 'EDIT NOT MATCHED: NO SUCH WHOLESALER'
case_ unmatched_none '' "$none" "$un" "$T_NONE" 'EDIT NOT MATCHED: NO SUCH WHOLESALER|KEY|R999' 'EDIT NOT MATCHED: NO SUCH WHOLESALER'
echo "03_scenario_test: ok"
