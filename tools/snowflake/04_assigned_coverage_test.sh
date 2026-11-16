#!/bin/sh
# Runs 04_assigned_coverage.sql in DuckDB on made-up UNION, TERRITORIES and assignments tables (the real column names)
# and checks the four tables and the result against answers worked out by hand from the rows below: run 1 with every
# area mode blank (today's ZIPs), run 2 on the same database with TRIM, ADD and REPLACE and the area checks.
# Prints "04_assigned_coverage_test: ok" or stops at the first failed check.  Run from anywhere.
set -e
here=$(cd "$(dirname "$0")" && pwd)
# the script as DuckDB runs it, into a fresh full_result
emit_sql() {
echo 'DROP TABLE IF EXISTS full_result;'
sed -e "s/\\\\\\\\s+', ' ')/\\\\s+', ' ', 'g')/g" -e '/^use /d' -e '/^SET /d' -e 's/TEMPORARY TABLE/TABLE/' \
    -e "s/^WITH\$/CREATE TABLE full_result AS WITH/" \
    -e 's/IDENTIFIER(\$union_tbl)/ssdb_integration.lr_strategy.union_t/' \
    -e 's/IDENTIFIER(\$terr_tbl)/ssdb_integration.lr_strategy.terr_t/' \
    -e 's/IDENTIFIER(\$zip_state_tbl)/ssdb_integration.lr_strategy.zst_t/' \
    -e 's/IDENTIFIER(\$assign_tbl)/ssdb_integration.lr_strategy.assign_t/' "$here/04_assigned_coverage.sql"
}
{
cat <<'SQL'
ATTACH ':memory:' AS ssdb_integration; CREATE SCHEMA ssdb_integration.lr_strategy;
CREATE TABLE ssdb_integration.lr_strategy.terr_t (source TEXT, name TEXT, zip_code TEXT, state TEXT, channel TEXT,
  clean_name TEXT, clean_id TEXT);
INSERT INTO ssdb_integration.lr_strategy.terr_t (source, name, zip_code, channel) VALUES
  -- A.  Ann: WH in 00001 and 00002, FI in 00001.  Bob: FI in 00002 and 00003.  Cy: WH in 00002 (with Ann) and 00003.
  -- Dee and Fay: IFA only.  Eve: WH and FI in 00004, WH in 00006.  Jay: FI in 00007, not on the roster.
  ('A','Ann A','1','WH'), ('A','Ann A','00002','wh'), ('A','ann  a','00001','FI'),
  ('A','Bob B','00002','FI'), ('A','Bob B','00003','FI'),
  ('A','Cy C','00002','WH'), ('A','Cy C','00003','WH'),
  ('A','Dee D','00001','IFA'), ('A','Dee D','00002','IFA'), ('A','Dee D','00003','IFA'), ('A','Fay F','00004','IFA'),
  ('A','Eve E','00004','WH'), ('A','Eve E','00004','FI'), ('A','Eve E','00006','WH'), ('A','Jay J','00007','FI'),
  ('A','Open','00005','FI'),
  -- B.  Gil: WH and FI in 00001 and 00002.  Hal: WH and FI in 00003 and 00004.
  ('B','Gil G','00001','WH'), ('B','Gil G','00001','FI'), ('B','Gil G','00002','WH'), ('B','Gil G','00002','FI'),
  ('B','Hal H','00003','WH'), ('B','Hal H','00003','FI'), ('B','Hal H','00004','WH'), ('B','Hal H','00004','FI');
-- the roster as loaded back: the seed's other columns are ignored
CREATE TABLE ssdb_integration.lr_strategy.assign_t (source TEXT, wholesaler TEXT, current_channels TEXT, kept TEXT, role TEXT,
  area_mode TEXT, area_states TEXT);
-- ZIP states: 00001-00002 MA, 00003-00004 NH, 00005-00008 VT (00008: nobody holds it, no opportunity), 00009 none
CREATE TABLE ssdb_integration.lr_strategy.zst_t (zip_code TEXT, state TEXT);
INSERT INTO ssdb_integration.lr_strategy.zst_t VALUES ('1','MA'), ('00002','ma'), ('00003','NH'), ('00004','NH'), ('00005','VT'),
  ('00006','VT'), ('00007','VT'), ('00008','VT'), ('00009','');
INSERT INTO ssdb_integration.lr_strategy.assign_t (source, wholesaler, kept, role) VALUES
  -- Ann FI: she holds FI, so her area is her FI ZIP only (00001).  Bob WIFI: 00002, 00003.
  -- Cy FI: he holds no FI, so his area is his WH ZIPs (00002, 00003).  Dee WH: an IFA holder, no area.
  ('A','Ann A','Y','FI'), ('A','BOB  B','yes','wifi'), ('A','Cy C','Y','FI'), ('A','Dee D','Y','WH'),
  -- Eve not kept, on two rows.  Fay kept outside the main map.  Zed: not a name of the territories.  Ivy: bad values.
  ('A','Eve E','N',NULL), ('A','eve e','n',''), ('A','Fay F','Y',''), ('A','Zed Z','Y','WH'), ('A','Ivy I','maybe','BOSS'),
  -- Gil NATIONAL: 00001, 00002 have national.  Hal WIFI: 00003, 00004.
  ('B','Gil G','Y','NATIONAL'), ('B','Hal H',' y ','WIFI');
CREATE TABLE ssdb_integration.lr_strategy.union_t (fiscal_yr INTEGER, source TEXT, old_terr_wholesaler TEXT,
  sales_wholesaler TEXT, terr_wholesaler_clean_name TEXT, sales_wholesaler_clean_name TEXT, dist_ch TEXT, new_dist TEXT,
  channel TEXT, state TEXT, zip_code TEXT, product_v2 TEXT, mm_opp DOUBLE, actual_sales_amount DOUBLE, sales_amount DOUBLE,
  sales_wholesaler_territory_id TEXT, sales_wholesaler_address_id TEXT, territory_wholesaler_territory_id TEXT,
  territory_wholesaler_address_id TEXT, sales_wholesaler_has_territory INTEGER, territory_wholesaler_has_territory INTEGER,
  firm_override BOOLEAN, row_origin TEXT, file_new_dist TEXT, channel_rule TEXT, n_holders INTEGER, firm_key TEXT,
  firm_crd TEXT, crd_rule TEXT, opp_override TEXT, firm TEXT, cbd_id TEXT, new_terr_wholesaler TEXT,
  new_terr_channel TEXT, parent TEXT);
INSERT INTO ssdb_integration.lr_strategy.union_t (fiscal_yr, source, zip_code, product_v2, dist_ch, new_dist, mm_opp, firm) VALUES
  -- A 00001 (national there: Gil).  The WH cell is on two rows (once).  Wells FI under WH, FI under IFA.
  (2025,'A','1','VA','WH','WH',100,'F1'), (2025,'A','00001','VA','WH','WH',100,'F1'),
  (2025,'A','00001','VA','FI','FI',200,'F1'), (2025,'A','00001','VA','FI','National (Chase)',30,'F2'),
  (2025,'A','00001','VA','WH','Wells FI',40,'F3'), (2025,'A','00001','VA','IFA','FI',50,'F4'),
  -- not the main map, a sales-only row, a negative: nothing
  (2025,'A','00001','VA','IFA','IFA',999,'F5'), (2025,'A','00001','FA','WH','WH',0,'F1'), (2025,'A','00001','IA','WH','WH',-5,'F1'),
  -- A 00002 (national there)
  (2025,'A','00002','VA','WH','WH',10,'F1'), (2025,'A','00002','VA','FI','FI',20,'F1'), (2025,'A','00002','VA','WH','Wells WH',5,'F3'),
  -- A 00003 (no national: Wells FI falls back to FI, Wells WH to WH)
  (2025,'A','00003','VA','WH','WH',300,'F1'), (2025,'A','00003','VA','FI','FI',400,'F1'),
  (2025,'A','00003','VA','FI','Wells FI',60,'F3'), (2025,'A','00003','VA','WH','Wells WH',7,'F3'),
  -- A 00004 (no national: Chase falls back to FI), 00005 (no channel today, nobody), 00006 (its holder is not kept)
  (2025,'A','00004','VA','WH','WH',1000,'F1'), (2025,'A','00004','VA','FI','FI',2000,'F1'),
  (2025,'A','00004','VA','FI','National (Chase)',500,'F2'), (2025,'A','00005','VA',NULL,'FI',9,'F1'),
  (2025,'A','00006','VA','WH','WH',70,'F1'),
  -- B: the other estimate, claimed by the same wholesalers
  (2025,'B','00001','VA','FI','FI',210,'F1'), (2025,'B','00003','VA','FI','Wells FI',61,'F3'), (2025,'B','00004','VA','WH','WH',1100,'F1');
SQL
emit_sql
cat <<'SQL'
CREATE MACRO chk(name, got, want) AS CASE WHEN got IS NOT DISTINCT FROM want THEN 'ok'
  ELSE error(name || ': got ' || COALESCE(CAST(got AS VARCHAR), 'NULL') || ', want ' || CAST(want AS VARCHAR)) END;
CREATE MACRO i(x) AS COALESCE(CAST(CAST(x AS BIGINT) AS VARCHAR), '-');
CREATE MACRO sec(s) AS (SELECT string_agg(concat_ws('|', source, k1, COALESCE(k2, '-'), i(n), i(mm_opp), must_be_zero), ' / ' ORDER BY source, k1, k2)
                        FROM full_result WHERE section = s);
SELECT
 chk('TD_MAP_AREA: Ann her FI ZIP only, Cy his WH ZIPs, Dee, Fay, Zed and Eve none',
     (SELECT string_agg(source || ' ' || wholesaler || ' ' || role || ' ' || zip_code || ' ' || has_wh || has_fi, ' / ' ORDER BY source, wholesaler, zip_code)
      FROM ssdb_integration.lr_strategy.td_map_area),
     'A Ann A FI 00001 11 / A BOB  B WIFI 00002 01 / A BOB  B WIFI 00003 01 / A Cy C FI 00002 10 / A Cy C FI 00003 10'
     || ' / B Gil G NATIONAL 00001 11 / B Gil G NATIONAL 00002 11 / B Hal H WIFI 00003 11 / B Hal H WIFI 00004 11'),
 chk('TD_MAP_CELL: need, claims, status, role or reason, per estimate x ZIP x fine channel x channel today',
     (SELECT string_agg(concat_ws(' ', source, zip_code, new_dist, '[' || dist_ch || ']', i(mm_opp), need, n_claim, n_claim_firms, status,
                                  COALESCE(captured_role, gap_reason, '-')), ' / ' ORDER BY source, zip_code, new_dist, dist_ch)
      FROM ssdb_integration.lr_strategy.td_map_cell),
     'A 00001 FI [FI] 200 FI 1 1 CAPTURED FI / A 00001 FI [IFA] 50 FI 1 1 CAPTURED FI / A 00001 NATIONAL (CHASE) [FI] 30 NATIONAL 1 1 CAPTURED NATIONAL'
     || ' / A 00001 WELLS FI [WH] 40 NATIONAL 1 1 CAPTURED NATIONAL / A 00001 WH [WH] 100 WH 0 0 GAP HOLDER KEPT IN A ROLE THAT DOES NOT COVER IT'
     || ' / A 00002 FI [FI] 20 FI 2 1 OVERLAP - / A 00002 WELLS WH [WH] 5 NATIONAL 1 1 CAPTURED NATIONAL / A 00002 WH [WH] 10 WH 1 1 CAPTURED WIFI'
     || ' / A 00003 FI [FI] 400 FI 3 2 OVERLAP - / A 00003 WELLS FI [FI] 60 FI 3 2 OVERLAP - / A 00003 WELLS WH [WH] 7 WH 2 2 OVERLAP - / A 00003 WH [WH] 300 WH 2 2 OVERLAP -'
     || ' / A 00004 FI [FI] 2000 FI 1 1 CAPTURED WIFI / A 00004 NATIONAL (CHASE) [FI] 500 FI 1 1 CAPTURED WIFI / A 00004 WH [WH] 1000 WH 1 1 CAPTURED WIFI'
     || ' / A 00005 FI [] 9 FI 0 0 GAP NO HOLDER TODAY / A 00006 WH [WH] 70 WH 0 0 GAP HOLDER NOT KEPT'
     || ' / B 00001 FI [FI] 210 FI 1 1 CAPTURED FI / B 00003 WELLS FI [FI] 61 FI 3 2 OVERLAP - / B 00004 WH [WH] 1100 WH 1 1 CAPTURED WIFI'),
 chk('TD_MAP_CLAIM: one row per claim, with the cell''s claim count',
     (SELECT string_agg(concat_ws(' ', source, wholesaler, role, zip_code, need, n_claim, n_claim_firms), ' / ' ORDER BY zip_code, need, source, wholesaler)
      FROM ssdb_integration.lr_strategy.td_map_claim),
     'A Ann A FI 00001 FI 1 1 / B Gil G NATIONAL 00001 NATIONAL 1 1 / A BOB  B WIFI 00002 FI 2 1 / A Cy C FI 00002 FI 2 1 / B Gil G NATIONAL 00002 NATIONAL 1 1'
     || ' / A BOB  B WIFI 00002 WH 1 1 / A BOB  B WIFI 00003 FI 3 2 / A Cy C FI 00003 FI 3 2 / B Hal H WIFI 00003 FI 3 2 / A BOB  B WIFI 00003 WH 2 2'
     || ' / B Hal H WIFI 00003 WH 2 2 / B Hal H WIFI 00004 FI 1 1 / B Hal H WIFI 00004 WH 1 1'),
 chk('TD_MAP_WHOLESALER: kept, role, in territories, area ZIPs, then claimed sole shared | held today, kept, released, gained (own source only)',
     (SELECT string_agg(concat_ws(' ', source, wholesaler, '[' || kept || role || in_territories || ']', est_source, n_area_zips, i(opp_claimed), i(opp_sole), i(opp_shared), '|',
                                  i(opp_held_today), i(opp_kept), i(opp_released), i(opp_gained)), ' / ' ORDER BY source, wholesaler, est_source)
      FROM ssdb_integration.lr_strategy.td_map_wholesaler),
     'A Ann A [YFI1] A 1 250 250 0 | 385 200 185 50 / A Ann A [YFI1] B 1 210 210 0 | - - - -'
     || ' / A BOB  B [YWIFI1] A 2 797 10 787 | 480 480 0 317 / A BOB  B [YWIFI1] B 2 61 0 61 | - - - -'
     || ' / A Cy C [YFI1] A 2 480 0 480 | 322 0 322 480 / A Cy C [YFI1] B 2 61 0 61 | - - - -'
     || ' / A Dee D [YWH1] A 0 0 0 0 | 50 0 50 0 / A Dee D [YWH1] B 0 0 0 0 | - - - -'
     || ' / A Eve E [N1] A 0 0 0 0 | 3570 0 3570 0 / A Eve E [N1] B 0 0 0 0 | - - - -'
     || ' / A Fay F [Y1] A 0 0 0 0 | 0 0 0 0 / A Fay F [Y1] B 0 0 0 0 | - - - -'
     || ' / A Ivy I [?BOSS0] A 0 0 0 0 | 0 0 0 0 / A Ivy I [?BOSS0] B 0 0 0 0 | - - - -'
     || ' / A Zed Z [YWH0] A 0 0 0 0 | 0 0 0 0 / A Zed Z [YWH0] B 0 0 0 0 | - - - -'
     || ' / B Gil G [YNATIONAL1] A 2 75 75 0 | - - - - / B Gil G [YNATIONAL1] B 2 0 0 0 | 210 0 210 0'
     || ' / B Hal H [YWIFI1] A 2 4267 3500 767 | - - - - / B Hal H [YWIFI1] B 2 1161 1100 61 | 1161 1161 0 0'),
 chk('result columns', (SELECT string_agg(column_name, ',' ORDER BY column_index) FROM duckdb_columns() WHERE table_name = 'full_result'),
     'section,source,k1,k2,n,mm_opp,must_be_zero'),
 chk('ROSTER', sec('ROSTER'),
     'A|01 ROWS|-|9|-|0 / A|02 KEPT Y|-|6|-|0 / A|03 KEPT N|-|1|-|0 / A|04 KEPT BLANK (NOT DECIDED)|-|0|-|0 / A|05 KEPT NOT Y, N OR BLANK|-|1|-|1'
     || ' / A|06 ROLE NOT NATIONAL, WH, FI, WIFI OR BLANK|-|1|-|1 / A|07 WHOLESALER ON 2+ ROWS|-|1|-|1 / A|08 KEPT WITH NO ROLE (OUTSIDE THE MAIN MAP)|-|1|-|0'
     || ' / A|09 KEPT WITH A ROLE, NAME NOT IN THE TERRITORIES (AREA FROM LISTED STATES ONLY)|-|1|-|0 / A|10 KEPT WITH A ROLE, IN THE TERRITORIES, NO ZIP IN THE AREA|-|1|-|0'
     || ' / A|11 WH OR FI HOLDERS NOT ON THE ROSTER (NOT KEPT)|-|1|-|0'
     || ' / A|12 AREA_MODE NOT TRIM, REPLACE, ADD OR BLANK|-|0|-|1 / A|13 AREA_MODE WITH NO AREA_STATES, OR AREA_STATES WITH NO AREA_MODE|-|0|-|1 / A|14 AREA_STATES CODE NOT IN THE ZIP STATE TABLE (OR TWICE)|-|0|-|1'
     || ' / B|01 ROWS|-|2|-|0 / B|02 KEPT Y|-|2|-|0 / B|03 KEPT N|-|0|-|0 / B|04 KEPT BLANK (NOT DECIDED)|-|0|-|0 / B|05 KEPT NOT Y, N OR BLANK|-|0|-|1'
     || ' / B|06 ROLE NOT NATIONAL, WH, FI, WIFI OR BLANK|-|0|-|1 / B|07 WHOLESALER ON 2+ ROWS|-|0|-|1 / B|08 KEPT WITH NO ROLE (OUTSIDE THE MAIN MAP)|-|0|-|0'
     || ' / B|09 KEPT WITH A ROLE, NAME NOT IN THE TERRITORIES (AREA FROM LISTED STATES ONLY)|-|0|-|0 / B|10 KEPT WITH A ROLE, IN THE TERRITORIES, NO ZIP IN THE AREA|-|0|-|0'
     || ' / B|11 WH OR FI HOLDERS NOT ON THE ROSTER (NOT KEPT)|-|0|-|0'
     || ' / B|12 AREA_MODE NOT TRIM, REPLACE, ADD OR BLANK|-|0|-|1 / B|13 AREA_MODE WITH NO AREA_STATES, OR AREA_STATES WITH NO AREA_MODE|-|0|-|1 / B|14 AREA_STATES CODE NOT IN THE ZIP STATE TABLE (OR TWICE)|-|0|-|1'),
 chk('ROLES', sec('ROLES'), 'A|FI|TODAY|2|-|0 / A|WH|TODAY|2|-|0 / A|WIFI|TODAY|1|-|0 / B|NATIONAL|TODAY|1|-|0 / B|WIFI|TODAY|1|-|0'),
 chk('CAPTURE: per estimate the rows add up to the main map (A 4801, B 1371)', sec('CAPTURE'),
     'A|FI|1 CLAIMANT: FI|2|250|0 / A|FI|1 CLAIMANT: WIFI|2|2500|0 / A|FI|2+ CLAIMANTS, 2+ FIRMS|2|460|0 / A|FI|2+ CLAIMANTS, ONE FIRM|1|20|0'
     || ' / A|FI|GAP: NO HOLDER TODAY|1|9|0 / A|NATIONAL|1 CLAIMANT: NATIONAL|3|75|0 / A|WH|1 CLAIMANT: WIFI|2|1010|0 / A|WH|2+ CLAIMANTS, 2+ FIRMS|2|307|0'
     || ' / A|WH|GAP: HOLDER KEPT IN A ROLE THAT DOES NOT COVER IT|1|100|0 / A|WH|GAP: HOLDER NOT KEPT|1|70|0'
     || ' / B|FI|1 CLAIMANT: FI|1|210|0 / B|FI|2+ CLAIMANTS, 2+ FIRMS|1|61|0 / B|WH|1 CLAIMANT: WIFI|1|1100|0'),
 chk('CAPTURE totals', (SELECT string_agg(source || ' ' || i(o), ' ' ORDER BY source) FROM (SELECT source, SUM(mm_opp) AS o FROM full_result WHERE section = 'CAPTURE' GROUP BY source)),
     'A 4801 B 1371'),
 chk('FINE CHANNEL: the national fine channels under NATIONAL where Gil is, fallen back elsewhere', sec('FINE CHANNEL'),
     'A|FI|FI|6|2679|0 / A|NATIONAL (CHASE)|FI|1|500|0 / A|NATIONAL (CHASE)|NATIONAL|1|30|0 / A|WELLS FI|FI|1|60|0 / A|WELLS FI|NATIONAL|1|40|0'
     || ' / A|WELLS WH|NATIONAL|1|5|0 / A|WELLS WH|WH|1|7|0 / A|WH|WH|5|1480|0 / B|FI|FI|1|210|0 / B|WELLS FI|FI|1|61|0 / B|WH|WH|1|1100|0'),
 chk('TIE', sec('TIE'), 'A|MAIN MAP IN ZIPS WITH NO STATE IN THE ZIP STATE TABLE|-|0|0|0 / A|TD_MAP_CELL MINUS THE UNION, MAIN MAP (N 1 = THEY DIFFER)|-|0|0|1'
     || ' / B|MAIN MAP IN ZIPS WITH NO STATE IN THE ZIP STATE TABLE|-|0|0|0 / B|TD_MAP_CELL MINUS THE UNION, MAIN MAP (N 1 = THEY DIFFER)|-|0|0|1'),
 chk('no wholesaler name in the result or in TD_MAP_CELL',
     (SELECT COUNT(*) FROM full_result f WHERE regexp_matches(CAST(f AS VARCHAR), 'ann a|bob +b|cy c|dee d|eve e|fay f|gil g|hal h|zed z|ivy i|jay j', 'i'))
     + (SELECT COUNT(*) FROM ssdb_integration.lr_strategy.td_map_cell f WHERE regexp_matches(CAST(f AS VARCHAR), 'ann a|bob +b|cy c|dee d|eve e|fay f|gil g|hal h|zed z|ivy i|jay j', 'i')), 0);
-- run 2: area modes.  Bob TRIM NH (today 00002, 00003 -> 00003).  Cy ADD VT (today 00002, 00003 + 00005-00008).
-- Dee REPLACE VT (holds no WH or FI: 00005-00008).  Zed REPLACE NH (not in the territories: 00003, 00004).
-- Hal REPLACE MA (today 00003, 00004 -> 00001, 00002).  Ann ADD 'MA XX' (XX flagged, MA adds 00002).
-- Fay mode GROW (flagged).  Gil states NH with no mode (flagged, ignored: today's ZIPs).
UPDATE ssdb_integration.lr_strategy.assign_t SET area_mode = 'trim', area_states = 'nh' WHERE wholesaler = 'BOB  B';
UPDATE ssdb_integration.lr_strategy.assign_t SET area_mode = 'ADD', area_states = 'VT' WHERE wholesaler = 'Cy C';
UPDATE ssdb_integration.lr_strategy.assign_t SET area_mode = 'REPLACE', area_states = ' VT ' WHERE wholesaler = 'Dee D';
UPDATE ssdb_integration.lr_strategy.assign_t SET area_mode = 'REPLACE', area_states = 'NH' WHERE wholesaler = 'Zed Z';
UPDATE ssdb_integration.lr_strategy.assign_t SET area_mode = 'REPLACE', area_states = 'ma' WHERE wholesaler = 'Hal H';
UPDATE ssdb_integration.lr_strategy.assign_t SET area_mode = 'ADD', area_states = 'MA,XX' WHERE wholesaler = 'Ann A';
UPDATE ssdb_integration.lr_strategy.assign_t SET area_mode = 'GROW' WHERE wholesaler = 'Fay F';
UPDATE ssdb_integration.lr_strategy.assign_t SET area_states = 'NH' WHERE wholesaler = 'Gil G';
SQL
emit_sql
cat <<'SQL'
SELECT
 chk('run 2 TD_MAP_AREA: mode, held today WH FI, in today''s area, in a listed state',
     (SELECT string_agg(concat_ws(' ', source, wholesaler, role, '[' || area_mode || ']', zip_code, has_wh || has_fi, in_today_area || in_listed_state), ' / '
                        ORDER BY source, wholesaler, zip_code)
      FROM ssdb_integration.lr_strategy.td_map_area),
     'A Ann A FI [ADD] 00001 11 11 / A Ann A FI [ADD] 00002 10 01 / A BOB  B WIFI [TRIM] 00003 01 11'
     || ' / A Cy C FI [ADD] 00002 10 10 / A Cy C FI [ADD] 00003 10 10 / A Cy C FI [ADD] 00005 00 01 / A Cy C FI [ADD] 00006 00 01'
     || ' / A Cy C FI [ADD] 00007 00 01 / A Cy C FI [ADD] 00008 00 01'
     || ' / A Dee D WH [REPLACE] 00005 00 01 / A Dee D WH [REPLACE] 00006 00 01 / A Dee D WH [REPLACE] 00007 00 01 / A Dee D WH [REPLACE] 00008 00 01'
     || ' / A Zed Z WH [REPLACE] 00003 00 01 / A Zed Z WH [REPLACE] 00004 00 01'
     || ' / B Gil G NATIONAL [] 00001 11 10 / B Gil G NATIONAL [] 00002 11 10 / B Hal H WIFI [REPLACE] 00001 00 01 / B Hal H WIFI [REPLACE] 00002 00 01'),
 chk('run 2 TD_MAP_CELL in 00003-00006',
     (SELECT string_agg(concat_ws(' ', source, zip_code, new_dist, '[' || dist_ch || ']', i(mm_opp), need, n_claim, n_claim_firms, status,
                                  COALESCE(captured_role, gap_reason, '-')), ' / ' ORDER BY source, zip_code, new_dist, dist_ch)
      FROM ssdb_integration.lr_strategy.td_map_cell WHERE zip_code BETWEEN '00003' AND '00006'),
     'A 00003 FI [FI] 400 FI 2 1 OVERLAP - / A 00003 WELLS FI [FI] 60 FI 2 1 OVERLAP - / A 00003 WELLS WH [WH] 7 WH 2 1 OVERLAP -'
     || ' / A 00003 WH [WH] 300 WH 2 1 OVERLAP - / A 00004 FI [FI] 2000 FI 0 0 GAP HOLDER NOT KEPT'
     || ' / A 00004 NATIONAL (CHASE) [FI] 500 FI 0 0 GAP HOLDER NOT KEPT / A 00004 WH [WH] 1000 WH 1 1 CAPTURED WH'
     || ' / A 00005 FI [] 9 FI 1 1 CAPTURED FI / A 00006 WH [WH] 70 WH 1 1 CAPTURED WH'
     || ' / B 00003 WELLS FI [FI] 61 FI 2 1 OVERLAP - / B 00004 WH [WH] 1100 WH 1 1 CAPTURED WH'),
 chk('run 2 TD_MAP_WHOLESALER: Dee, an IFA holder given VT, gains 00006''s WH and releases her IFA-held FI cell',
     (SELECT string_agg(concat_ws(' ', est_source, '[' || kept || role || area_mode || area_states || ']', n_area_zips, i(opp_claimed), i(opp_sole), i(opp_shared), '|',
                                  i(opp_held_today), i(opp_kept), i(opp_released), i(opp_gained)), ' / ' ORDER BY est_source)
      FROM ssdb_integration.lr_strategy.td_map_wholesaler WHERE wholesaler = 'Dee D'),
     'A [YWHREPLACEVT] 4 70 70 0 | 50 0 50 70 / B [YWHREPLACEVT] 4 0 0 0 | - - - -'),
 chk('run 2 ROSTER area checks and check 10 (Dee has an area now)',
     (SELECT string_agg(source || '|' || k1 || '|' || i(n), ' / ' ORDER BY source, k1) FROM full_result
      WHERE section = 'ROSTER' AND (k1 LIKE '1_ %' AND k1 NOT LIKE '11 %' OR k1 LIKE '09 %')),
     'A|09 KEPT WITH A ROLE, NAME NOT IN THE TERRITORIES (AREA FROM LISTED STATES ONLY)|1 / A|10 KEPT WITH A ROLE, IN THE TERRITORIES, NO ZIP IN THE AREA|0'
     || ' / A|12 AREA_MODE NOT TRIM, REPLACE, ADD OR BLANK|1 / A|13 AREA_MODE WITH NO AREA_STATES, OR AREA_STATES WITH NO AREA_MODE|0'
     || ' / A|14 AREA_STATES CODE NOT IN THE ZIP STATE TABLE (OR TWICE)|1'
     || ' / B|09 KEPT WITH A ROLE, NAME NOT IN THE TERRITORIES (AREA FROM LISTED STATES ONLY)|0 / B|10 KEPT WITH A ROLE, IN THE TERRITORIES, NO ZIP IN THE AREA|0'
     || ' / B|12 AREA_MODE NOT TRIM, REPLACE, ADD OR BLANK|0 / B|13 AREA_MODE WITH NO AREA_STATES, OR AREA_STATES WITH NO AREA_MODE|1'
     || ' / B|14 AREA_STATES CODE NOT IN THE ZIP STATE TABLE (OR TWICE)|0'),
 chk('run 2 ROLES', sec('ROLES'), 'A|FI|ADD|2|-|0 / A|WH|REPLACE|2|-|0 / A|WIFI|TRIM|1|-|0 / B|NATIONAL|TODAY|1|-|0 / B|WIFI|REPLACE|1|-|0'),
 chk('run 2 CAPTURE still adds up to the main map', (SELECT string_agg(source || ' ' || i(o), ' ' ORDER BY source)
      FROM (SELECT source, SUM(mm_opp) AS o FROM full_result WHERE section = 'CAPTURE' GROUP BY source)), 'A 4801 B 1371'),
 chk('run 2 no wholesaler name in the result',
     (SELECT COUNT(*) FROM full_result f WHERE regexp_matches(CAST(f AS VARCHAR), 'ann a|bob +b|cy c|dee d|eve e|fay f|gil g|hal h|zed z|ivy i|jay j', 'i')), 0);
SELECT '04_assigned_coverage_test: ok';
SQL
} | duckdb -bail -noheader -list
