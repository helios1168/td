#!/bin/sh
# Runs 04_assigned_coverage.sql in DuckDB on made-up UNION, TERRITORIES and assignments tables (the real column names)
# and checks the four tables and the result against answers worked out by hand from the rows below.  Nothing may move a
# territory: every piece is a territory row, every cell's holder is its ZIP x DIST_CH holder.
# Prints "04_assigned_coverage_test: ok" or stops at the first failed check.  Run from anywhere.
set -e
here=$(cd "$(dirname "$0")" && pwd)
# The exclude_products switch is run three ways: the default 'FIXED' (the FIXED rows are left out, so the answers are the ones
# worked out for the rows without them), '' (every row: the FIXED opportunity and sales counted, worked out below the default's), and
# 'INDEX  RILA' with a double space (the same as '' here: no INDEX or RILA row, and a row with a blank or NULL product is kept, which the
# pattern '%  %' would otherwise drop).  Mutations (the filter off in both places, in one, the blank-product guard off) must each fail.
# the script as DuckDB runs it ($1 = the exclude list, $2 = the script, default 04's own)
emit() {
cat <<'SQL'
ATTACH ':memory:' AS ssdb_integration; CREATE SCHEMA ssdb_integration.lr_strategy;
CREATE TABLE ssdb_integration.lr_strategy.terr_t (source TEXT, name TEXT, zip_code TEXT, state TEXT, channel TEXT,
  clean_name TEXT, clean_id TEXT);
-- states: 00001-00002 MA, 00003-00004 NH, 00005-00007 VT
INSERT INTO ssdb_integration.lr_strategy.terr_t (source, name, zip_code, state, channel) VALUES
  ('A','Ann A','1','MA','WH'), ('A','Ann A','00002','MA','wh'), ('A','ann  a','00001','ma','FI'),
  ('A','Bob B','00002','MA','FI'), ('A','Bob B','00003','NH','FI'), ('A','Cy C','00003','NH','WH'),
  ('A','Dee D','00001','MA','IFA'), ('A','Dee D','00002','MA','IFA'),
  ('A','Eve E','00004','NH','WH'), ('A','Eve E','00004','NH','FI'), ('A','Fay F','00005','VT','IFA'),
  ('A','Open','00005','VT','FI'), ('A','Jay J','00007','VT','FI'),
  ('B','Gil G','00001','MA','WH'), ('B','Gil G','00001','MA','FI'), ('B','Gil G','00002','MA','WH'), ('B','Gil G','00002','MA','FI'),
  ('B','Hal H','00003','NH','WH'), ('B','Hal H','00003','NH','FI');
CREATE TABLE ssdb_integration.lr_strategy.assign_t (status TEXT, source TEXT, wholesaler TEXT, current_channels TEXT, kept TEXT,
  role TEXT, assigned_states TEXT);
-- Ann WIFI, states MA.  Bob FI, states NH and an unknown XX.  Cy WH.  Dee WIFI, holds only IFA.  Eve not kept, two rows.
-- Fay kept outside the main map.  Ivy bad values.  Zed not in the territories.  Jay not on the roster.
INSERT INTO ssdb_integration.lr_strategy.assign_t (source, wholesaler, kept, role, assigned_states) VALUES
  ('A','Ann A','Y','WIFI','ma'), ('A','Bob B','yes','fi','NH, XX'), ('A','Cy C','Y','WH',NULL), ('A','Dee D','Y','WIFI',''),
  ('A','Eve E','N',NULL,NULL), ('A','eve e','n','',''), ('A','Fay F','Y','',NULL), ('A','Ivy I','maybe','BOSS',NULL),
  ('A','Zed Z','Y','WH',NULL), ('B','Gil G','Y','WIFI',NULL), ('B','Hal H',' y ','national',NULL);
CREATE TABLE ssdb_integration.lr_strategy.union_t (fiscal_yr INTEGER, source TEXT, old_terr_wholesaler TEXT,
  sales_wholesaler TEXT, terr_wholesaler_clean_name TEXT, sales_wholesaler_clean_name TEXT, dist_ch TEXT, new_dist TEXT,
  channel TEXT, state TEXT, zip_code TEXT, product_v2 TEXT, mm_opp DOUBLE, actual_sales_amount DOUBLE, sales_amount DOUBLE,
  sales_wholesaler_territory_id TEXT, sales_wholesaler_address_id TEXT, territory_wholesaler_territory_id TEXT,
  territory_wholesaler_address_id TEXT, sales_wholesaler_has_territory INTEGER, territory_wholesaler_has_territory INTEGER,
  firm_override BOOLEAN, row_origin TEXT, file_new_dist TEXT, channel_rule TEXT, n_holders INTEGER, firm_key TEXT,
  firm_crd TEXT, crd_rule TEXT, opp_override TEXT, firm TEXT, cbd_id TEXT, new_terr_wholesaler TEXT,
  new_terr_channel TEXT, parent TEXT);
INSERT INTO ssdb_integration.lr_strategy.union_t (fiscal_yr, source, state, zip_code, product_v2, dist_ch, new_dist, channel, mm_opp,
  actual_sales_amount, sales_wholesaler, firm) VALUES
  -- A 00001: a WH cell on two rows (once), FI, Chase and Wells FI (CHANNEL National), FI under IFA (Dee's), IFA (not the main map)
  (2025,'A','MA','1','VA','WH','WH','WH',100,0,NULL,'F1'), (2025,'A','MA','00001','VA','WH','WH','WH',100,0,NULL,'F1'),
  (2025,'A','MA','00001','VA','FI','FI','FI',200,0,NULL,'F1'), (2025,'A','MA','00001','VA','FI','National (Chase)','National',30,0,NULL,'F2'),
  (2025,'A','MA','00001','VA','WH','Wells FI','National',40,0,NULL,'F3'), (2025,'A','MA','00001','VA','IFA','FI','FI',50,0,NULL,'F4'),
  (2025,'A','MA','00001','VA','IFA','IFA','IFA',999,0,NULL,'F5'),
  -- A 00002, and a row whose NEW_DIST is WH under CHANNEL IFA: left out, flagged
  (2025,'A','MA','00002','VA','WH','WH','WH',10,0,NULL,'F1'), (2025,'A','MA','00002','VA','FI','FI','FI',20,0,NULL,'F1'),
  (2025,'A','MA','00002','VA','WH','WH','IFA',5,0,NULL,'F6'),
  -- A 00003, 00004 (Eve, not kept), 00005 (FI vacant), 00006 (no channel today)
  (2025,'A','NH','00003','VA','WH','WH','WH',300,0,NULL,'F1'), (2025,'A','NH','00003','VA','FI','FI','FI',400,0,NULL,'F1'),
  (2025,'A','NH','00003','VA','FI','Wells FI','National',60,0,NULL,'F3'),
  (2025,'A','NH','00004','VA','WH','WH','WH',1000,0,NULL,'F1'), (2025,'A','NH','00004','VA','FI','FI','FI',2000,0,NULL,'F1'),
  (2025,'A','VT','00005','','FI','FI','FI',9,0,NULL,'F1'), (2025,'A','VT','00006',NULL,NULL,'FI','FI',7,0,NULL,'F1'),
  -- A sales: Ann in her ZIP (50) and outside (30), Eve (not kept) in hers (20), Kim holds nothing (10), no seller (5),
  -- Ann's IFA sale (not the main map)
  (2025,'A','MA','00001','FA','WH','WH','WH',0,50,'Ann A','F1'), (2025,'A','NH','00003','FA','FI','FI','FI',0,30,'ann a','F1'),
  (2025,'A','NH','00004','FA','WH','WH','WH',0,20,'Eve E','F1'), (2025,'A','MA','00002','FA','FI','FI','FI',0,10,'Kim K','F1'),
  (2025,'A','MA','00002','FA','FI','FI','FI',0,5,NULL,'F1'), (2025,'A','MA','00001','FA','IFA','IFA','IFA',0,999,'Ann A','F5'),
  -- FIXED rows (left out by default): 3 more in A 00001's WH cell, a new WH cell 4 in A 00005 (nobody holds WH there), a FIXED sale of Ann's in her ZIP (5)
  (2025,'A','MA','00001','FIXED','WH','WH','WH',3,0,NULL,'F1'), (2025,'A','VT','00005','FIXED','WH','WH','WH',4,0,NULL,'F1'),
  (2025,'A','MA','00001','FIXED','WH','WH','WH',0,5,'Ann A','F1'),
  -- B
  (2025,'B','MA','00001','VA','WH','WH','WH',110,0,NULL,'F1'), (2025,'B','MA','00001','VA','FI','FI','FI',210,0,NULL,'F1'),
  (2025,'B','NH','00003','VA','FI','Wells FI','National',61,0,NULL,'F3'), (2025,'B','NH','00003','VA','WH','WH','WH',310,0,NULL,'F1'),
  (2025,'B','NH','00003','FA','WH','WH','WH',0,40,'Hal H','F1');
-- the new-state holder's channel the dataset gives the national fine channels (B in its own code)
UPDATE ssdb_integration.lr_strategy.union_t SET new_terr_channel = CASE source WHEN 'A' THEN 'fi' ELSE 'BK' END
  WHERE new_dist IN ('Wells FI', 'National (Chase)');
SQL
# DuckDB has no LISTAGG ... WITHIN GROUP: string_agg with ORDER BY.  REGEXP_REPLACE as in 02_model_extract_test.sh
sed -e "s/LISTAGG(\([a-z]*\), ' ') WITHIN GROUP (ORDER BY [a-z]*)/string_agg(\1, ' ' ORDER BY \1)/" \
    -e "s/\\\\\\\\s+', ' ')/\\\\s+', ' ', 'g')/g" -e '/^use /d' -e '/^SET /d' -e 's/TEMPORARY TABLE/TABLE/' \
    -e "s/^WITH\$/CREATE TABLE full_result AS WITH/" \
    -e "s/[\$]exclude_products/'$1'/g" \
    -e 's/IDENTIFIER(\$union_tbl)/ssdb_integration.lr_strategy.union_t/' \
    -e 's/IDENTIFIER(\$terr_tbl)/ssdb_integration.lr_strategy.terr_t/' \
    -e 's/IDENTIFIER(\$assign_tbl)/ssdb_integration.lr_strategy.assign_t/' "${2:-$here/04_assigned_coverage.sql}"
cat <<'SQL'
CREATE MACRO chk(name, got, want) AS CASE WHEN got IS NOT DISTINCT FROM want THEN 'ok'
  ELSE error(name || ': got ' || COALESCE(CAST(got AS VARCHAR), 'NULL') || ', want ' || CAST(want AS VARCHAR)) END;
CREATE MACRO i(x) AS COALESCE(CAST(CAST(x AS BIGINT) AS VARCHAR), '-');
CREATE MACRO sec(s) AS (SELECT string_agg(concat_ws('|', source, k1, COALESCE(k2, '-'), i(n), i(mm_opp), COALESCE(CAST(round(pct, 1) AS VARCHAR), '-'), must_be_zero),
                        ' / ' ORDER BY source, k1, k2) FROM full_result WHERE section = s);
SQL
}
checks_common() {
cat <<'SQL'
SELECT
 chk('TD_MAP_PIECE: every territory row once, labelled, nothing added or moved',
     (SELECT string_agg(concat_ws('|', source, wholesaler, kept, role, zip_code, state, terr_channel, piece_in_role, i(in_assigned_state), i(n_role_holders), i(n_role_firms)),
                        ' / ' ORDER BY source, wholesaler, zip_code, terr_channel) FROM ssdb_integration.lr_strategy.td_map_piece),
     'A|Ann A|Y|WIFI|00001|MA|FI|1|1|2|2 / A|Ann A|Y|WIFI|00001|MA|WH|1|1|2|2 / A|Ann A|Y|WIFI|00002|MA|WH|1|1|2|2'
     || ' / A|Bob B|Y|FI|00002|MA|FI|1|0|1|1 / A|Bob B|Y|FI|00003|NH|FI|1|1|1|1 / A|Cy C|Y|WH|00003|NH|WH|1|-|1|1'
     || ' / A|Dee D|Y|WIFI|00001|MA|IFA|0|-|-|- / A|Dee D|Y|WIFI|00002|MA|IFA|0|-|-|- / A|Eve E|N||00004|NH|FI|0|-|-|- / A|Eve E|N||00004|NH|WH|0|-|-|-'
     || ' / A|Fay F|Y||00005|VT|IFA|0|-|-|- / A|JAY J|||00007|VT|FI|0|-|-|-'
     || ' / B|Gil G|Y|WIFI|00001|MA|FI|1|-|2|2 / B|Gil G|Y|WIFI|00001|MA|WH|1|-|2|2 / B|Gil G|Y|WIFI|00002|MA|FI|1|-|2|2 / B|Gil G|Y|WIFI|00002|MA|WH|1|-|2|2'
     || ' / B|Hal H|Y|NATIONAL|00003|NH|FI|1|-|1|1 / B|Hal H|Y|NATIONAL|00003|NH|WH|1|-|1|1'),
 chk('TD_MAP_PIECE: as many pieces as territory rows that are not vacant (two spellings of one ZIP x channel are one)',
     (SELECT COUNT(*) FROM ssdb_integration.lr_strategy.td_map_piece), 18),
 chk('TD_MAP_ZIP', (SELECT string_agg(concat_ws(' ', zip_code, role, n_role_holders, n_role_firms), ' / ' ORDER BY zip_code, role) FROM ssdb_integration.lr_strategy.td_map_zip),
     '00001 WIFI 2 2 / 00002 FI 1 1 / 00002 WIFI 2 2 / 00003 FI 1 1 / 00003 NATIONAL 1 1 / 00003 WH 1 1'),
 chk('result columns', (SELECT string_agg(column_name, ',' ORDER BY column_index) FROM duckdb_columns() WHERE table_name = 'full_result'),
     'section,source,k1,k2,n,mm_opp,pct,must_be_zero'),
 chk('ROSTER', sec('ROSTER'),
     'A|01 ROWS|-|9|-|-|0 / A|02 KEPT Y|-|6|-|-|0 / A|03 KEPT N|-|1|-|-|0 / A|04 KEPT BLANK (NOT DECIDED)|-|0|-|-|0 / A|05 KEPT NOT Y, N OR BLANK|-|1|-|-|1'
     || ' / A|06 ROLE NOT NATIONAL, WH, FI, WIFI OR BLANK|-|1|-|-|1 / A|07 WHOLESALER ON 2+ ROWS|-|1|-|-|1 / A|08 KEPT WITH NO ROLE (OUTSIDE THE MAIN MAP)|-|1|-|-|0'
     || ' / A|09 KEPT WITH A ROLE, NAME NOT IN THE TERRITORIES|-|1|-|-|0 / A|10 KEPT WITH A ROLE, NO PIECE IN ROLE (HOLDS NO WH OR FI)|-|1|-|-|0'
     || ' / A|11 HOLDERS NOT ON THE ROSTER (NOT KEPT)|-|1|-|-|0 / A|12 ASSIGNED_STATES CODE NOT A TERRITORY STATE (OR TWICE)|-|1|-|-|1'
     || ' / B|01 ROWS|-|2|-|-|0 / B|02 KEPT Y|-|2|-|-|0 / B|03 KEPT N|-|0|-|-|0 / B|04 KEPT BLANK (NOT DECIDED)|-|0|-|-|0 / B|05 KEPT NOT Y, N OR BLANK|-|0|-|-|1'
     || ' / B|06 ROLE NOT NATIONAL, WH, FI, WIFI OR BLANK|-|0|-|-|1 / B|07 WHOLESALER ON 2+ ROWS|-|0|-|-|1 / B|08 KEPT WITH NO ROLE (OUTSIDE THE MAIN MAP)|-|0|-|-|0'
     || ' / B|09 KEPT WITH A ROLE, NAME NOT IN THE TERRITORIES|-|0|-|-|0 / B|10 KEPT WITH A ROLE, NO PIECE IN ROLE (HOLDS NO WH OR FI)|-|0|-|-|0'
     || ' / B|11 HOLDERS NOT ON THE ROSTER (NOT KEPT)|-|0|-|-|0 / B|12 ASSIGNED_STATES CODE NOT A TERRITORY STATE (OR TWICE)|-|0|-|-|1'),
 chk('ROLES', sec('ROLES'), 'A|FI|-|1|-|-|0 / A|WH|-|2|-|-|0 / A|WIFI|-|2|-|-|0 / B|NATIONAL|-|1|-|-|0 / B|WIFI|-|1|-|-|0'),
 chk('TIE', sec('TIE'),
     'A|MAIN MAP CELLS WHOSE NEW_DIST IS NOT WH, FI, WELLS WH, WELLS FI OR NATIONAL (CHASE)|-|0|0|-|1'
     || ' / A|NATIONAL FINE CHANNELS BY NEW_TERR_CHANNEL (INFORMATION)|NATIONAL (CHASE) -> FI|1|30|-|0'
     || ' / A|NATIONAL FINE CHANNELS BY NEW_TERR_CHANNEL (INFORMATION)|WELLS FI -> FI|2|100|-|0'
     || ' / A|ROWS WITH NEW_DIST WH, FI, WELLS WH, WELLS FI OR NATIONAL (CHASE) AND CHANNEL NOT NATIONAL, WH OR FI|-|1|5|-|1'
     || ' / A|TD_MAP_CELL MINUS THE UNION, MAIN MAP (N 1 = THEY DIFFER)|-|0|0|-|1'
     || ' / B|MAIN MAP CELLS WHOSE NEW_DIST IS NOT WH, FI, WELLS WH, WELLS FI OR NATIONAL (CHASE)|-|0|0|-|1'
     || ' / B|NATIONAL FINE CHANNELS BY NEW_TERR_CHANNEL (INFORMATION)|WELLS FI -> BK|1|61|-|0'
     || ' / B|ROWS WITH NEW_DIST WH, FI, WELLS WH, WELLS FI OR NATIONAL (CHASE) AND CHANNEL NOT NATIONAL, WH OR FI|-|0|0|-|1'
     || ' / B|TD_MAP_CELL MINUS THE UNION, MAIN MAP (N 1 = THEY DIFFER)|-|0|0|-|1'),
 chk('no wholesaler name in the result or in TD_MAP_CELL, TD_MAP_ZIP',
     (SELECT COUNT(*) FROM full_result f WHERE regexp_matches(CAST(f AS VARCHAR), 'ann a|bob b|cy c|dee d|eve e|fay f|gil g|hal h|zed z|ivy i|jay j|kim k', 'i'))
     + (SELECT COUNT(*) FROM ssdb_integration.lr_strategy.td_map_cell f WHERE regexp_matches(CAST(f AS VARCHAR), 'ann a|bob b|cy c|dee d|eve e|gil g|hal h|jay j', 'i'))
     + (SELECT COUNT(*) FROM ssdb_integration.lr_strategy.td_map_zip f WHERE regexp_matches(CAST(f AS VARCHAR), 'ann a|bob b|cy c|dee d|eve e|gil g|hal h|jay j', 'i')), 0);
SQL
}
checks_default() {
cat <<'SQL'
SELECT
 chk('TD_MAP_CELL: the holder today and their label',
     (SELECT string_agg(concat_ws(' ', est_source, zip_code, state, new_dist, '[' || dist_ch || ']', channel, fit_channel, i(mm_opp), n_holders, holder_status), ' / '
                        ORDER BY est_source, zip_code, new_dist, dist_ch) FROM ssdb_integration.lr_strategy.td_map_cell),
     -- 00001 has no NATIONAL holder: Chase and Wells FI count for FI, so Ann (WIFI) has them in role.  00003 has Hal
     -- (NATIONAL): Wells FI counts for NATIONAL there, out of role for Bob (FI), in role for Hal.
     'A 00001 MA FI [FI] FI FI 200 1 KEPT IN ROLE / A 00001 MA FI [IFA] FI FI 50 1 KEPT IN ROLE / A 00001 MA NATIONAL (CHASE) [FI] NATIONAL FI 30 1 KEPT IN ROLE'
     || ' / A 00001 MA WELLS FI [WH] NATIONAL FI 40 1 KEPT IN ROLE / A 00001 MA WH [WH] WH WH 100 1 KEPT IN ROLE'
     || ' / A 00002 MA FI [FI] FI FI 20 1 KEPT IN ROLE / A 00002 MA WH [WH] WH WH 10 1 KEPT IN ROLE'
     || ' / A 00003 NH FI [FI] FI FI 400 1 KEPT IN ROLE / A 00003 NH WELLS FI [FI] NATIONAL NATIONAL 60 1 KEPT OUT OF ROLE / A 00003 NH WH [WH] WH WH 300 1 KEPT IN ROLE'
     || ' / A 00004 NH FI [FI] FI FI 2000 1 NOT KEPT (OPEN) / A 00004 NH WH [WH] WH WH 1000 1 NOT KEPT (OPEN)'
     || ' / A 00005 VT FI [FI] FI FI 9 0 NO HOLDER TODAY / A 00006 VT FI [] FI FI 7 0 NO HOLDER TODAY'
     || ' / B 00001 MA FI [FI] FI FI 210 1 KEPT IN ROLE / B 00001 MA WH [WH] WH WH 110 1 KEPT IN ROLE'
     || ' / B 00003 NH WELLS FI [FI] NATIONAL NATIONAL 61 1 KEPT IN ROLE / B 00003 NH WH [WH] WH WH 310 1 KEPT OUT OF ROLE'),
 chk('TD_MAP_WHOLESALER: zips, in role, states, then main = in role + out of role, overlap, in assigned states | sales, in own ZIPs (own source)',
     (SELECT string_agg(concat_ws(' ', source, wholesaler, '[' || kept || role || ']', est_source, n_zips, n_zips_in_role, states, i(opp_main), i(opp_in_role),
                                  i(opp_out_of_role), i(opp_overlap), i(opp_in_assigned_states), '|', i(sales_main), i(sales_main_in_own_zips)),
                        ' / ' ORDER BY source, wholesaler, est_source) FROM ssdb_integration.lr_strategy.td_map_wholesaler),
     'A Ann A [YWIFI] A 2 2 MA 380 380 0 380 380 | 80 50 / A Ann A [YWIFI] B 2 2 MA 320 320 0 320 320 | - -'
     || ' / A Bob B [YFI] A 2 2 MA NH 480 420 60 0 460 | 0 0 / A Bob B [YFI] B 2 2 MA NH 61 0 61 0 61 | - -'
     || ' / A Cy C [YWH] A 1 1 NH 300 300 0 0 - | 0 0 / A Cy C [YWH] B 1 1 NH 310 310 0 0 - | - -'
     || ' / A Dee D [YWIFI] A 2 0 MA 50 50 0 0 - | 0 0 / A Dee D [YWIFI] B 2 0 MA 0 0 0 0 - | - -'
     || ' / A Eve E [N] A 1 0 NH 3000 0 3000 0 - | 20 20 / A Eve E [N] B 1 0 NH 0 0 0 0 - | - -'
     || ' / A Fay F [Y] A 1 0 VT 0 0 0 0 - | 0 0 / A Fay F [Y] B 1 0 VT 0 0 0 0 - | - -'
     || ' / A JAY J [] A 1 0 VT 0 0 0 0 - | 0 0 / A JAY J [] B 1 0 VT 0 0 0 0 - | - -'
     || ' / B Gil G [YWIFI] A 2 2 MA 400 400 0 400 - | - - / B Gil G [YWIFI] B 2 2 MA 320 320 0 320 - | 0 0'
     || ' / B Hal H [YNATIONAL] A 1 1 NH 760 60 700 0 - | - - / B Hal H [YNATIONAL] B 1 1 NH 371 61 310 0 - | 40 40'),
 chk('OPPORTUNITY', sec('OPPORTUNITY'),
     'A|FI|KEPT IN ROLE|4|670|-|0 / A|FI|NO HOLDER TODAY|2|16|-|0 / A|FI|NOT KEPT (OPEN)|1|2000|-|0 / A|NATIONAL (CHASE)|KEPT IN ROLE|1|30|-|0'
     || ' / A|WELLS FI|KEPT IN ROLE|1|40|-|0 / A|WELLS FI|KEPT OUT OF ROLE|1|60|-|0 / A|WH|KEPT IN ROLE|3|410|-|0 / A|WH|NOT KEPT (OPEN)|1|1000|-|0'
     || ' / B|FI|KEPT IN ROLE|1|210|-|0 / B|WELLS FI|KEPT IN ROLE|1|61|-|0 / B|WH|KEPT IN ROLE|1|110|-|0 / B|WH|KEPT OUT OF ROLE|1|310|-|0'),
 chk('OPPORTUNITY adds up to the main map (A 4226, B 691)',
     (SELECT string_agg(source || ' ' || i(o), ' ' ORDER BY source) FROM (SELECT source, SUM(mm_opp) AS o FROM full_result WHERE section = 'OPPORTUNITY' GROUP BY source)),
     'A 4226 B 691'),
 chk('OVERLAP', sec('OVERLAP'),
     'A|FI|1 KEPT HOLDERS, 1 FIRM(S)|2|420|-|0 / A|NATIONAL|1 KEPT HOLDERS, 1 FIRM(S)|1|60|-|0 / A|WH|1 KEPT HOLDERS, 1 FIRM(S)|1|300|-|0'
     || ' / A|WIFI|2 KEPT HOLDERS, 2 FIRM(S)|2|450|-|0 / B|NATIONAL|1 KEPT HOLDERS, 1 FIRM(S)|1|61|-|0 / B|WH|1 KEPT HOLDERS, 1 FIRM(S)|1|310|-|0'
     || ' / B|WIFI|2 KEPT HOLDERS, 2 FIRM(S)|1|320|-|0'),
 chk('SALES: rows and percent only', sec('SALES'),
     'A|NO SELLER (BLANK OR OPEN)|NOT IN A ZIP THE SELLER HOLDS|1|-|4.3|0 / A|SELLER HOLDS NO TERRITORY|NOT IN A ZIP THE SELLER HOLDS|1|-|8.7|0'
     || ' / A|SELLER KEPT|IN A ZIP THE SELLER HOLDS|1|-|43.5|0 / A|SELLER KEPT|NOT IN A ZIP THE SELLER HOLDS|1|-|26.1|0'
     || ' / A|SELLER NOT KEPT|IN A ZIP THE SELLER HOLDS|1|-|17.4|0 / B|SELLER KEPT|IN A ZIP THE SELLER HOLDS|1|-|100.0|0');
SELECT chk('SETTINGS: which way the run went', sec('SETTINGS'), 'EXCLUDE_PRODUCTS|FIXED|-|-|-|0');
SQL
}
checks_all() {
cat <<'SQL'
SELECT
 chk('TD_MAP_CELL with FIXED: the FIXED 3 in A 00001 WH and the new A 00005 WH cell',
     (SELECT string_agg(concat_ws(' ', est_source, zip_code, state, new_dist, '[' || dist_ch || ']', channel, fit_channel, i(mm_opp), n_holders, holder_status), ' / '
                        ORDER BY est_source, zip_code, new_dist, dist_ch) FROM ssdb_integration.lr_strategy.td_map_cell),
     -- 00001 has no NATIONAL holder: Chase and Wells FI count for FI, so Ann (WIFI) has them in role.  00003 has Hal
     -- (NATIONAL): Wells FI counts for NATIONAL there, out of role for Bob (FI), in role for Hal.
     'A 00001 MA FI [FI] FI FI 200 1 KEPT IN ROLE / A 00001 MA FI [IFA] FI FI 50 1 KEPT IN ROLE / A 00001 MA NATIONAL (CHASE) [FI] NATIONAL FI 30 1 KEPT IN ROLE'
     || ' / A 00001 MA WELLS FI [WH] NATIONAL FI 40 1 KEPT IN ROLE / A 00001 MA WH [WH] WH WH 103 1 KEPT IN ROLE'
     || ' / A 00002 MA FI [FI] FI FI 20 1 KEPT IN ROLE / A 00002 MA WH [WH] WH WH 10 1 KEPT IN ROLE'
     || ' / A 00003 NH FI [FI] FI FI 400 1 KEPT IN ROLE / A 00003 NH WELLS FI [FI] NATIONAL NATIONAL 60 1 KEPT OUT OF ROLE / A 00003 NH WH [WH] WH WH 300 1 KEPT IN ROLE'
     || ' / A 00004 NH FI [FI] FI FI 2000 1 NOT KEPT (OPEN) / A 00004 NH WH [WH] WH WH 1000 1 NOT KEPT (OPEN)'
     || ' / A 00005 VT FI [FI] FI FI 9 0 NO HOLDER TODAY / A 00005 VT WH [WH] WH WH 4 0 NO HOLDER TODAY / A 00006 VT FI [] FI FI 7 0 NO HOLDER TODAY'
     || ' / B 00001 MA FI [FI] FI FI 210 1 KEPT IN ROLE / B 00001 MA WH [WH] WH WH 110 1 KEPT IN ROLE'
     || ' / B 00003 NH WELLS FI [FI] NATIONAL NATIONAL 61 1 KEPT IN ROLE / B 00003 NH WH [WH] WH WH 310 1 KEPT OUT OF ROLE'),
 chk('TD_MAP_WHOLESALER with FIXED (Ann opportunity +3 and sales +5, Gil est A +3): zips, in role, states, then main = in role + out of role, overlap, in assigned states | sales, in own ZIPs (own source)',
     (SELECT string_agg(concat_ws(' ', source, wholesaler, '[' || kept || role || ']', est_source, n_zips, n_zips_in_role, states, i(opp_main), i(opp_in_role),
                                  i(opp_out_of_role), i(opp_overlap), i(opp_in_assigned_states), '|', i(sales_main), i(sales_main_in_own_zips)),
                        ' / ' ORDER BY source, wholesaler, est_source) FROM ssdb_integration.lr_strategy.td_map_wholesaler),
     'A Ann A [YWIFI] A 2 2 MA 383 383 0 383 383 | 85 55 / A Ann A [YWIFI] B 2 2 MA 320 320 0 320 320 | - -'
     || ' / A Bob B [YFI] A 2 2 MA NH 480 420 60 0 460 | 0 0 / A Bob B [YFI] B 2 2 MA NH 61 0 61 0 61 | - -'
     || ' / A Cy C [YWH] A 1 1 NH 300 300 0 0 - | 0 0 / A Cy C [YWH] B 1 1 NH 310 310 0 0 - | - -'
     || ' / A Dee D [YWIFI] A 2 0 MA 50 50 0 0 - | 0 0 / A Dee D [YWIFI] B 2 0 MA 0 0 0 0 - | - -'
     || ' / A Eve E [N] A 1 0 NH 3000 0 3000 0 - | 20 20 / A Eve E [N] B 1 0 NH 0 0 0 0 - | - -'
     || ' / A Fay F [Y] A 1 0 VT 0 0 0 0 - | 0 0 / A Fay F [Y] B 1 0 VT 0 0 0 0 - | - -'
     || ' / A JAY J [] A 1 0 VT 0 0 0 0 - | 0 0 / A JAY J [] B 1 0 VT 0 0 0 0 - | - -'
     || ' / B Gil G [YWIFI] A 2 2 MA 403 403 0 403 - | - - / B Gil G [YWIFI] B 2 2 MA 320 320 0 320 - | 0 0'
     || ' / B Hal H [YNATIONAL] A 1 1 NH 760 60 700 0 - | - - / B Hal H [YNATIONAL] B 1 1 NH 371 61 310 0 - | 40 40'),
 chk('OPPORTUNITY', sec('OPPORTUNITY'),
     'A|FI|KEPT IN ROLE|4|670|-|0 / A|FI|NO HOLDER TODAY|2|16|-|0 / A|FI|NOT KEPT (OPEN)|1|2000|-|0 / A|NATIONAL (CHASE)|KEPT IN ROLE|1|30|-|0'
     || ' / A|WELLS FI|KEPT IN ROLE|1|40|-|0 / A|WELLS FI|KEPT OUT OF ROLE|1|60|-|0 / A|WH|KEPT IN ROLE|3|413|-|0 / A|WH|NO HOLDER TODAY|1|4|-|0 / A|WH|NOT KEPT (OPEN)|1|1000|-|0'
     || ' / B|FI|KEPT IN ROLE|1|210|-|0 / B|WELLS FI|KEPT IN ROLE|1|61|-|0 / B|WH|KEPT IN ROLE|1|110|-|0 / B|WH|KEPT OUT OF ROLE|1|310|-|0'),
 chk('OPPORTUNITY adds up to the main map (A 4233, B 691: 4226 without FIXED + 3 + 4)',
     (SELECT string_agg(source || ' ' || i(o), ' ' ORDER BY source) FROM (SELECT source, SUM(mm_opp) AS o FROM full_result WHERE section = 'OPPORTUNITY' GROUP BY source)),
     'A 4233 B 691'),
 chk('OVERLAP', sec('OVERLAP'),
     'A|FI|1 KEPT HOLDERS, 1 FIRM(S)|2|420|-|0 / A|NATIONAL|1 KEPT HOLDERS, 1 FIRM(S)|1|60|-|0 / A|WH|1 KEPT HOLDERS, 1 FIRM(S)|1|300|-|0'
     || ' / A|WIFI|2 KEPT HOLDERS, 2 FIRM(S)|2|453|-|0 / B|NATIONAL|1 KEPT HOLDERS, 1 FIRM(S)|1|61|-|0 / B|WH|1 KEPT HOLDERS, 1 FIRM(S)|1|310|-|0'
     || ' / B|WIFI|2 KEPT HOLDERS, 2 FIRM(S)|1|320|-|0'),
 chk('SALES with the FIXED sale (5 of Ann, 120 in all)', sec('SALES'),
     'A|NO SELLER (BLANK OR OPEN)|NOT IN A ZIP THE SELLER HOLDS|1|-|4.2|0 / A|SELLER HOLDS NO TERRITORY|NOT IN A ZIP THE SELLER HOLDS|1|-|8.3|0'
     || ' / A|SELLER KEPT|IN A ZIP THE SELLER HOLDS|2|-|45.8|0 / A|SELLER KEPT|NOT IN A ZIP THE SELLER HOLDS|1|-|25.0|0'
     || ' / A|SELLER NOT KEPT|IN A ZIP THE SELLER HOLDS|1|-|16.7|0 / B|SELLER KEPT|IN A ZIP THE SELLER HOLDS|1|-|100.0|0');
SQL
}
{ emit FIXED; checks_common; checks_default; echo "SELECT '04_assigned_coverage_test: default run ok';"; } | duckdb -bail -noheader -list
{ emit ''; checks_common; checks_all; echo "SELECT chk('SETTINGS: none', sec('SETTINGS'), 'EXCLUDE_PRODUCTS|(none)|-|-|-|0');"
  echo "SELECT '04_assigned_coverage_test: include-all run ok';"; } | duckdb -bail -noheader -list
{ emit 'INDEX  RILA'; checks_common; checks_all; echo "SELECT '04_assigned_coverage_test: double-space run ok';"; } | duckdb -bail -noheader -list
# mutations: each broken script must fail one of the runs (a "got ... want" error)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
cut() { awk -v which="$1" '/^ +AND .*[$]exclude_products/ { n++; if (which == 0 || n == which) sub(/AND \(\(.*= ..\)/, "AND 1 = 1") } { print }' "$here/04_assigned_coverage.sql"; }
cut 0 > "$tmp/nofilter.sql"
cut 1 > "$tmp/noopp.sql"
cut 2 > "$tmp/nosale.sql"
sed -e "s/ OR COALESCE(TRIM(product_v2), '') = ''//" "$here/04_assigned_coverage.sql" > "$tmp/noguard.sql"
for v in nofilter noopp nosale noguard; do
  cmp -s "$tmp/$v.sql" "$here/04_assigned_coverage.sql" && { echo "04_assigned_coverage_test: mutation $v changed nothing"; exit 1; }
  bad=0
  for ex in FIXED 'INDEX  RILA'; do
    if { emit "$ex" "$tmp/$v.sql"; checks_common; if [ "$ex" = FIXED ]; then checks_default; else checks_all; fi; } | duckdb -bail -noheader -list > "$tmp/out" 2>&1; then :; else
      grep -q ': got ' "$tmp/out" || { echo "04_assigned_coverage_test: mutation $v failed for another reason:"; cat "$tmp/out"; exit 1; }
      bad=1
    fi
  done
  [ $bad = 1 ] || { echo "04_assigned_coverage_test: mutation $v was not flagged"; exit 1; }
  echo "04_assigned_coverage_test: mutation $v flagged"
done
echo "04_assigned_coverage_test: ok"
