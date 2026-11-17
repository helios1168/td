#!/bin/sh
# Runs 06_map_extract.sql in DuckDB on made-up TD_MAP_* and holder key tables (the real column names) and checks each layer
# against answers worked out by hand from the rows below: the PIECE filter (WH or FI, or kept), a wholesaler's two raw spellings
# one R<n>, the same name in the other source another R<n>, the CHECKS (a wholesaler with no key counted per source, a duplicated
# HOLDER_N), and that no wholesaler name, no holder id and no sales value is anywhere in the result.  The script is read only:
# no INSERT, CREATE or DROP outside comments, and the key table is unchanged.  A second run adds a key for the keyless one and a
# duplicate number.  A third run puts a made-up name and number in ROLE, KEPT, STATE, ASSIGNED_STATES and STATES: none leaves, the
# safe tokens survive, the CHECKS count them.  Prints "06_map_extract_test: ok" or stops at the first failed check.  Run from anywhere: sh 06_map_extract_test.sh
set -e
here=$(cd "$(dirname "$0")" && pwd)
if grep -v '^--' "$here/06_map_extract.sql" | grep -Eiq 'insert|create|drop|delete|update|alter|truncate'; then echo "06_map_extract.sql is not read only"; exit 1; fi
# the script as DuckDB runs it, into a fresh full_result (the stand-ins as in 02_model_extract_test.sh)
emit_sql() {
echo 'DROP TABLE IF EXISTS full_result;'
sed -e "s/\\\\\\\\s+', ' ')/\\\\s+', ' ', 'g')/" -e "s/', '')/', '', 'g')/" -e "s/' +', ' ')/' +', ' ', 'g')/" -e 's/REGEXP_LIKE(/regexp_matches(/g' -e '/^use /d' -e '/^SET /d' -e 's/^WITH$/CREATE TABLE full_result AS WITH/' \
    -e 's/IDENTIFIER(\$piece_tbl)/ssdb_integration.lr_strategy.piece_t/' \
    -e 's/IDENTIFIER(\$cell_tbl)/ssdb_integration.lr_strategy.cell_t/' \
    -e 's/IDENTIFIER(\$zip_tbl)/ssdb_integration.lr_strategy.zip_t/' \
    -e 's/IDENTIFIER(\$wh_tbl)/ssdb_integration.lr_strategy.wh_t/' \
    -e 's/IDENTIFIER(\$holder_tbl)/ssdb_integration.lr_strategy.holder_key/' "$here/06_map_extract.sql"
}
{
cat <<'SQL'
ATTACH ':memory:' AS ssdb_integration; CREATE SCHEMA ssdb_integration.lr_strategy;
CREATE MACRO uuid_string(ns, n) AS md5(ns || n);
CREATE TABLE ssdb_integration.lr_strategy.piece_t (source TEXT, wholesaler TEXT, kept TEXT, role TEXT, zip_code TEXT, state TEXT,
  terr_channel TEXT, piece_in_role INTEGER, in_assigned_state INTEGER, n_role_holders INTEGER, n_role_firms INTEGER);
-- Zorblat Quimby: two raw spellings in A (one holder), and in B (another number).  Wanda: not kept.  Karl: no key.  Orson in B: no key.
INSERT INTO ssdb_integration.lr_strategy.piece_t VALUES
  ('A','Zorblat Quimby','Y','WIFI','00001','MA','WH',1,1,2,2),
  ('A','ZORBLAT  QUIMBY ','Y','WIFI','00001','MA','IFA',0,NULL,NULL,NULL),
  ('A','Wanda Pfeffernuss','N','','00002','MA','FI',0,NULL,NULL,NULL),
  ('A','Wanda Pfeffernuss','N','','00003','MA','IFA',0,NULL,NULL,NULL),
  ('A','Orson Blixt','Y','NATIONAL','00004','NH','IFA',0,NULL,NULL,NULL),
  ('A','Keyless Karl','N','','00005','VT','WH',0,NULL,NULL,NULL),
  ('B','Zorblat Quimby','Y','WH','00001','MA','WH',1,NULL,1,1),
  ('B','Zorblat Quimby','Y','WH','00006','NH','IFA',0,NULL,NULL,NULL),
  ('B','Orson Blixt','N','','00007','NH','IFA',0,NULL,NULL,NULL);
CREATE TABLE ssdb_integration.lr_strategy.cell_t (est_source TEXT, zip_code TEXT, state TEXT, dist_ch TEXT, new_dist TEXT, channel TEXT,
  new_terr_channel TEXT, fit_channel TEXT, mm_opp DOUBLE, n_holders INTEGER, holder_status TEXT);
INSERT INTO ssdb_integration.lr_strategy.cell_t VALUES
  ('A','00001','MA','WH','WH','WH','WH','WH',100,1,'KEPT IN ROLE'),
  ('A','00005','VT','FI','WELLS FI','NATIONAL',NULL,'FI',7,0,'NO HOLDER TODAY'),
  ('B','00001','MA','FI','FI','FI',NULL,'FI',210,2,'NOT KEPT (OPEN)');
CREATE TABLE ssdb_integration.lr_strategy.zip_t (zip_code TEXT, role TEXT, n_role_holders INTEGER, n_role_firms INTEGER);
INSERT INTO ssdb_integration.lr_strategy.zip_t VALUES ('00001','WIFI',2,2), ('00003','NATIONAL',1,1);
-- 7654321 and 8765432 are the sales values: nothing of them may reach the result
CREATE TABLE ssdb_integration.lr_strategy.wh_t (source TEXT, wholesaler TEXT, kept TEXT, role TEXT, assigned_states TEXT, est_source TEXT,
  n_zips INTEGER, n_zips_in_role INTEGER, states TEXT, opp_main DOUBLE, opp_in_role DOUBLE, opp_out_of_role DOUBLE, opp_overlap DOUBLE,
  opp_in_assigned_states DOUBLE, sales_main DOUBLE, sales_main_in_own_zips DOUBLE);
INSERT INTO ssdb_integration.lr_strategy.wh_t VALUES
  ('A','Zorblat Quimby','Y','WIFI','MA','A',1,1,'MA',100,100,0,50,100,7654321,8765432),
  ('A','Zorblat Quimby','Y','WIFI','MA','B',1,1,'MA',80,80,0,0,80,NULL,NULL),
  ('A','Wanda Pfeffernuss','N','','','A',1,0,'MA',20,0,20,0,NULL,0,0),
  ('A','Orson Blixt','Y','NATIONAL','','A',1,0,'NH',5,0,5,0,NULL,0,0),
  ('A','Keyless Karl','N','','','A',1,0,'VT',3,0,3,0,NULL,0,0),
  ('B','Zorblat Quimby','Y','WH','','B',2,1,'MA NH',60,60,0,0,NULL,0,0),
  ('B','Orson Blixt','N','','','B',1,0,'NH',1,0,1,0,NULL,0,0);
CREATE TABLE ssdb_integration.lr_strategy.holder_key (source VARCHAR, holder_id VARCHAR, holder_n INTEGER, first_seen TIMESTAMP);
-- numbers not in name order, so a renumbering or a sort by name would show.  GONE GUS holds no territory.
INSERT INTO ssdb_integration.lr_strategy.holder_key VALUES
  ('A', uuid_string('6ba7b810-9dad-11d1-80b4-00c04fd430c8', 'ZORBLAT QUIMBY'), 5, now()),
  ('A', uuid_string('6ba7b810-9dad-11d1-80b4-00c04fd430c8', 'WANDA PFEFFERNUSS'), 3, now()),
  ('A', uuid_string('6ba7b810-9dad-11d1-80b4-00c04fd430c8', 'ORSON BLIXT'), 4, now()),
  ('A', uuid_string('6ba7b810-9dad-11d1-80b4-00c04fd430c8', 'GONE GUS'), 8, now()),
  ('B', uuid_string('6ba7b810-9dad-11d1-80b4-00c04fd430c8', 'ZORBLAT QUIMBY'), 9, now());
CREATE TEMP TABLE key_before AS SELECT * FROM ssdb_integration.lr_strategy.holder_key;
SQL
emit_sql
cat <<'SQL'
CREATE MACRO chk(name, got, want) AS CASE WHEN got IS NOT DISTINCT FROM want THEN 'ok'
  ELSE error(name || ': got ' || COALESCE(CAST(got AS VARCHAR), 'NULL') || ', want ' || CAST(want AS VARCHAR)) END;
CREATE MACRO i(x) AS COALESCE(CAST(CAST(x AS BIGINT) AS VARCHAR), '-');
CREATE MACRO c(src, nm) AS (SELECT COALESCE(CAST(CAST(value AS BIGINT) AS VARCHAR), '-') || '/' || CAST(must_be_zero AS VARCHAR)
                            FROM full_result WHERE layer = 'CHECKS' AND source IS NOT DISTINCT FROM src AND name = nm);
SELECT
 chk('one result set: the columns, no sales column',
     (SELECT string_agg(column_name, ',' ORDER BY column_index) FROM duckdb_columns() WHERE table_name = 'full_result'),
     'layer,source,est_source,holder,kept,role,assigned_states,zip_code,state,terr_channel,piece_in_role,in_assigned_state,dist_ch,new_dist,channel,new_terr_channel,fit_channel,mm_opp,n_holders,holder_status,n_role_holders,n_role_firms,n_zips,n_zips_in_role,states,opp_main,opp_in_role,opp_out_of_role,opp_overlap,opp_in_assigned_states,name,value,must_be_zero'),
 chk('PIECE: WH or FI pieces and every piece of a kept wholesaler, two spellings one R<n>, A and B apart, no key is NULL; Wanda IFA and Orson (B) IFA left out',
     (SELECT string_agg(concat_ws('|', source, COALESCE(holder, '-'), kept, role, zip_code, state, terr_channel, piece_in_role, i(in_assigned_state), i(n_role_holders), i(n_role_firms)),
                        ' / ' ORDER BY source, zip_code, terr_channel) FROM full_result WHERE layer = 'PIECE'),
     'A|R5|Y|WIFI|00001|MA|IFA|0|-|-|- / A|R5|Y|WIFI|00001|MA|WH|1|1|2|2 / A|R3|N||00002|MA|FI|0|-|-|- / A|R4|Y|NATIONAL|00004|NH|IFA|0|-|-|-'
     || ' / A|-|N||00005|VT|WH|0|-|-|- / B|R9|Y|WH|00001|MA|WH|1|-|1|1 / B|R9|Y|WH|00006|NH|IFA|0|-|-|-'),
 chk('CELL: as it is',
     (SELECT string_agg(concat_ws('|', est_source, zip_code, state, dist_ch, new_dist, channel, COALESCE(new_terr_channel, '-'), fit_channel, i(mm_opp), n_holders, holder_status),
                        ' / ' ORDER BY est_source, zip_code) FROM full_result WHERE layer = 'CELL'),
     'A|00001|MA|WH|WH|WH|WH|WH|100|1|KEPT IN ROLE / A|00005|VT|FI|WELLS FI|NATIONAL|-|FI|7|0|NO HOLDER TODAY / B|00001|MA|FI|FI|FI|-|FI|210|2|NOT KEPT (OPEN)'),
 chk('ZIP: as it is', (SELECT string_agg(concat_ws('|', zip_code, role, n_role_holders, n_role_firms), ' / ' ORDER BY zip_code) FROM full_result WHERE layer = 'ZIP'),
     '00001|WIFI|2|2 / 00003|NATIONAL|1|1'),
 chk('WHOLESALER: HOLDER for the name, no sales columns, no key is NULL',
     (SELECT string_agg(concat_ws('|', source, COALESCE(holder, '-'), kept, role, assigned_states, est_source, n_zips, n_zips_in_role, states, i(opp_main), i(opp_in_role),
                                  i(opp_out_of_role), i(opp_overlap), i(opp_in_assigned_states)),
                        ' / ' ORDER BY source, est_source, COALESCE(holder, 'Z')) FROM full_result WHERE layer = 'WHOLESALER'),
     'A|R3|N|||A|1|0|MA|20|0|20|0|- / A|R4|Y|NATIONAL||A|1|0|NH|5|0|5|0|- / A|R5|Y|WIFI|MA|A|1|1|MA|100|100|0|50|100 / A|-|N|||A|1|0|VT|3|0|3|0|-'
     || ' / A|R5|Y|WIFI|MA|B|1|1|MA|80|80|0|0|80 / B|R9|Y|WH||B|2|1|MA NH|60|60|0|0|- / B|-|N|||B|1|0|NH|1|0|1|0|-'),
 chk('CHECKS: wholesalers with no key (A: Karl, B: Orson), key HOLDER_N duplicated none',
     c('A', 'WHOLESALERS WITH NO KEY ROW (RUN 02_model_extract.sql FIRST)') || ' ' || c('B', 'WHOLESALERS WITH NO KEY ROW (RUN 02_model_extract.sql FIRST)')
     || ' ' || c('A', 'KEY HOLDER_N DUPLICATED') || ' ' || c('B', 'KEY HOLDER_N DUPLICATED'), '1/1 1/1 0/1 0/1'),
 chk('CHECKS: rows per layer (information), PIECE after its filter, ZIP has no source',
     c('A', 'ROWS IN THE PIECE LAYER') || ' ' || c('B', 'ROWS IN THE PIECE LAYER') || ' ' || c('A', 'ROWS IN THE CELL LAYER') || ' ' || c('B', 'ROWS IN THE CELL LAYER')
     || ' ' || c(NULL, 'ROWS IN THE ZIP LAYER') || ' ' || c('A', 'ROWS IN THE WHOLESALER LAYER') || ' ' || c('B', 'ROWS IN THE WHOLESALER LAYER'),
     '5/0 2/0 2/0 1/0 2/0 5/0 2/0'),
 chk('CHECKS: the MUST_BE_ZERO rows not zero are the two no-key ones',
     (SELECT string_agg(source || ':' || name, ' ' ORDER BY source) FROM full_result WHERE layer = 'CHECKS' AND must_be_zero = 1 AND value <> 0),
     'A:WHOLESALERS WITH NO KEY ROW (RUN 02_model_extract.sql FIRST) B:WHOLESALERS WITH NO KEY ROW (RUN 02_model_extract.sql FIRST)'),
 chk('no wholesaler name, in any spelling, no holder id and no sales value anywhere in the result',
     (SELECT COUNT(*) FROM full_result f,
        (SELECT DISTINCT v FROM (SELECT TRIM(wholesaler) AS v FROM ssdb_integration.lr_strategy.piece_t
                                 UNION SELECT TRIM(wholesaler) FROM ssdb_integration.lr_strategy.wh_t
                                 UNION SELECT regexp_replace(TRIM(wholesaler), '\s+', ' ', 'g') FROM ssdb_integration.lr_strategy.piece_t
                                 UNION SELECT holder_id FROM ssdb_integration.lr_strategy.holder_key
                                 UNION SELECT 'zorblat' UNION SELECT 'quimby' UNION SELECT 'wanda' UNION SELECT 'pfeffer' UNION SELECT 'orson' UNION SELECT 'blixt'
                                 UNION SELECT 'keyless' UNION SELECT 'karl' UNION SELECT 'gone gus' UNION SELECT '7654321' UNION SELECT '8765432' UNION SELECT 'sales') WHERE v <> '') n
      WHERE strpos(lower(CAST(f AS VARCHAR)), lower(n.v)) > 0), 0),
 chk('read only: the key table is as it was', (SELECT COUNT(*) FROM (SELECT * FROM ssdb_integration.lr_strategy.holder_key EXCEPT SELECT * FROM key_before)), 0),
 chk('read only: the key table has the same rows', (SELECT COUNT(*) FROM ssdb_integration.lr_strategy.holder_key), 5);
-- run 2: Karl gets a key (the script must pick it up, not create it), and a number is duplicated across the sources (B's Gus takes A Zorblat's 5)
INSERT INTO ssdb_integration.lr_strategy.holder_key VALUES
  ('A', uuid_string('6ba7b810-9dad-11d1-80b4-00c04fd430c8', 'KEYLESS KARL'), 10, now()),
  ('B', uuid_string('6ba7b810-9dad-11d1-80b4-00c04fd430c8', 'GONE GUS'), 5, now());
SQL
emit_sql
cat <<'SQL'
SELECT
 chk('run 2: Karl is R10 on his piece and his wholesaler row',
     (SELECT string_agg(layer || ':' || holder, ' ' ORDER BY layer) FROM full_result WHERE zip_code = '00005' AND layer = 'PIECE' OR (layer = 'WHOLESALER' AND n_zips_in_role = 0 AND opp_main = 3)),
     'PIECE:R10 WHOLESALER:R10'),
 chk('run 2: no-key A 0, B 1 (Orson), the duplicated number 5 in both sources',
     c('A', 'WHOLESALERS WITH NO KEY ROW (RUN 02_model_extract.sql FIRST)') || ' ' || c('B', 'WHOLESALERS WITH NO KEY ROW (RUN 02_model_extract.sql FIRST)')
     || ' ' || c('A', 'KEY HOLDER_N DUPLICATED') || ' ' || c('B', 'KEY HOLDER_N DUPLICATED'), '0/1 1/1 1/1 1/1'),
 chk('run 2: the key was not touched by the script (the two rows are the ones inserted above)', (SELECT COUNT(*) FROM ssdb_integration.lr_strategy.holder_key), 7);
-- run 3: owner-typed text where ROLE, KEPT, STATE, ASSIGNED_STATES and STATES are, 'Zed Q 98765' a made-up name and number: none of it may leave
INSERT INTO ssdb_integration.lr_strategy.piece_t VALUES
  ('A','Zorblat Quimby','Zed Q 98765','WIFI','00010','MA','WH',0,NULL,NULL,NULL),
  ('A','Zorblat Quimby','Y','Zed Q 98765','00011','MA','WH',0,NULL,NULL,NULL),
  ('A','Zorblat Quimby','Y','WIFI','00012','Zed Q 98765','WH',0,NULL,NULL,NULL);
INSERT INTO ssdb_integration.lr_strategy.zip_t VALUES ('00099','Zed Q 98765',1,1);
INSERT INTO ssdb_integration.lr_strategy.wh_t VALUES
  ('A','Zorblat Quimby','Y','Zed Q 98765','CA zed NV','B',1,1,'MA Q 98765 NH',777,0,0,0,NULL,0,0),
  ('B','Orson Blixt','Zed Q 98765','','ca nv','B',1,0,'  TX   zed  98765 ',778,0,0,0,NULL,0,0);
SQL
emit_sql
cat <<'SQL'
SELECT
 chk('run 3: no typed name or number anywhere in the result (zed, 98765)',
     (SELECT COUNT(*) FROM full_result f WHERE strpos(lower(CAST(f AS VARCHAR)), 'zed') > 0 OR strpos(CAST(f AS VARCHAR), '98765') > 0), 0),
 chk('run 3: WHOLESALER: ROLE and KEPT INVALID, the two-capital-letter tokens kept in order (CA zed NV -> CA NV, ca nv -> nothing, TX zed 98765 -> TX)',
     (SELECT string_agg(concat_ws('|', source, role, kept, assigned_states, states), ' / ' ORDER BY opp_main) FROM full_result WHERE layer = 'WHOLESALER' AND opp_main IN (777, 778)),
     'A|INVALID|Y|CA NV|MA NH / B||INVALID||TX'),
 chk('run 3: PIECE: KEPT INVALID, ROLE INVALID, STATE NULL, the rest as it is',
     (SELECT string_agg(concat_ws('|', zip_code, kept, role, COALESCE(state, '-')), ' / ' ORDER BY zip_code) FROM full_result WHERE layer = 'PIECE' AND zip_code IN ('00010', '00011', '00012')),
     '00010|INVALID|WIFI|MA / 00011|Y|INVALID|MA / 00012|Y|WIFI|-'),
 chk('run 3: ZIP: ROLE INVALID', (SELECT role FROM full_result WHERE layer = 'ZIP' AND zip_code = '00099'), 'INVALID'),
 chk('run 3: CHECKS count them, A: piece role, kept, state 1 1 1, wholesaler role 1 kept 0 assigned 1 states 1',
     c('A', 'PIECE ROWS WITH ROLE EXPORTED AS INVALID') || ' ' || c('A', 'PIECE ROWS WITH KEPT EXPORTED AS INVALID') || ' ' || c('A', 'PIECE ROWS WITH STATE REMOVED')
     || ' ' || c('A', 'WHOLESALER ROWS WITH ROLE EXPORTED AS INVALID') || ' ' || c('A', 'WHOLESALER ROWS WITH KEPT EXPORTED AS INVALID')
     || ' ' || c('A', 'WHOLESALER ROWS WITH ASSIGNED_STATES TOKENS REMOVED') || ' ' || c('A', 'WHOLESALER ROWS WITH STATES TOKENS REMOVED'),
     '1/1 1/1 1/1 1/1 0/1 1/1 1/1'),
 chk('run 3: CHECKS count them, B: piece 0 0 0, wholesaler role 0 kept 1 assigned 1 states 1, ZIP role 1',
     c('B', 'PIECE ROWS WITH ROLE EXPORTED AS INVALID') || ' ' || c('B', 'PIECE ROWS WITH KEPT EXPORTED AS INVALID') || ' ' || c('B', 'PIECE ROWS WITH STATE REMOVED')
     || ' ' || c('B', 'WHOLESALER ROWS WITH ROLE EXPORTED AS INVALID') || ' ' || c('B', 'WHOLESALER ROWS WITH KEPT EXPORTED AS INVALID')
     || ' ' || c('B', 'WHOLESALER ROWS WITH ASSIGNED_STATES TOKENS REMOVED') || ' ' || c('B', 'WHOLESALER ROWS WITH STATES TOKENS REMOVED')
     || ' ' || c(NULL, 'ZIP ROWS WITH ROLE EXPORTED AS INVALID'),
     '0/1 0/1 0/1 0/1 1/1 1/1 1/1 1/1');
SELECT '06_map_extract_test: ok';
SQL
} | duckdb -bail -noheader -list
