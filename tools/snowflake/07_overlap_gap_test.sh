#!/bin/sh
# Runs 07_overlap_gap.sql in DuckDB on made-up TD_MAP_CELL, TD_MAP_PIECE, td_assignments and td_holder_key (the real column names)
# and checks the three tables and the result against answers worked out by hand from the rows below (comment at each group).
# People, key, source, role, assigned states, ZIPs they hold in role: Nan R10 A NATIONAL MA z01 z03 (two pieces) z06 z18 / Norm R15 A NATIONAL z03
# / Nell R8 B NATIONAL z03 z18 / Walt R20 A WH MA NH z04 z07 / Opal R25 A WH z12 z14 / Rita R30 A WIFI MA NH VT z04 z05 z06 z09 z14 z16
# / Rex R5 B WIFI vt / Ray R40 A WIFI CT z11 / Hank R35 A WIFI z08 z16 z17.  Fred R50 is kept FI (z13), Nick R45 is not kept and Walt has a piece
# with PIECE_IN_ROLE 0 on z13: none is a holder.  The keys are numbers, so 'R8 R10 R15' and 'R5 R30' test the order by number.
# Cells (est E1, one row each, NEW_DIST, opp), the attribution and class, see EXPECT below.  A second run adds Kay (kept WIFI, no key).
# Prints "07_overlap_gap_test: ok" or stops at the first failed check.  Run from anywhere: sh 07_overlap_gap_test.sh
set -e
here=$(cd "$(dirname "$0")" && pwd)
# the script as DuckDB runs it ($1 = extra SQL before it, run in the same database)
emit() {
cat <<'SQL'
ATTACH ':memory:' AS ssdb_integration; CREATE SCHEMA ssdb_integration.lr_strategy;
CREATE MACRO UUID_STRING(ns, nm) AS md5(ns || nm);
CREATE TABLE ssdb_integration.lr_strategy.assign_t (source TEXT, wholesaler TEXT, kept TEXT, role TEXT, assigned_states TEXT);
INSERT INTO ssdb_integration.lr_strategy.assign_t VALUES
  ('A','Nan Zzq','Y','NATIONAL','MA'), ('A','Norm Zzq','y','national',NULL), ('B','Nell Zzq','Y','NATIONAL',''),
  ('A','Walt Zzq','Y','WH','MA, NH'), ('A','Opal Zzq','Y','WH',NULL), ('A','Rita Zzq','Y','WIFI','MA NH VT'), ('B','Rex Zzq','Y','WIFI','vt'),
  ('A','Ray Zzq','Y','WIFI','CT'), ('A','Hank Zzq','Y','WIFI',''), ('A','Fred Zzq','Y','FI','ME'), ('A','Nick Zzq','N','WIFI','ME');
CREATE TABLE ssdb_integration.lr_strategy.hk_t (source TEXT, holder_id TEXT, holder_n INTEGER);
INSERT INTO ssdb_integration.lr_strategy.hk_t SELECT source, UUID_STRING('6ba7b810-9dad-11d1-80b4-00c04fd430c8', nm), n
FROM (VALUES ('A','NAN ZZQ',10), ('A','NORM ZZQ',15), ('B','NELL ZZQ',8), ('A','WALT ZZQ',20), ('A','OPAL ZZQ',25), ('A','RITA ZZQ',30),
             ('B','REX ZZQ',5), ('A','RAY ZZQ',40), ('A','HANK ZZQ',35), ('A','FRED ZZQ',50), ('A','NICK ZZQ',45)) v(source, nm, n);
CREATE TABLE ssdb_integration.lr_strategy.piece_t (source TEXT, wholesaler TEXT, zip_code TEXT, piece_in_role INTEGER);
INSERT INTO ssdb_integration.lr_strategy.piece_t VALUES
  ('A','Nan Zzq','z01',1), ('A','NAN  ZZQ ','z03',1), ('A','Nan Zzq','z03',1), ('A','Nan Zzq','z06',1), ('A','Nan Zzq','z18',1),
  ('A','Norm Zzq','z03',1), ('B','Nell Zzq','z03',1), ('B','Nell Zzq','z18',1),
  ('A','Walt Zzq','z04',1), ('A','Walt Zzq','z07',1), ('A','Opal Zzq','z12',1), ('A','Opal Zzq','z14',1),
  ('A','Rita Zzq','z04',1), ('A','Rita Zzq','z05',1), ('A','Rita Zzq','z06',1), ('A','Rita Zzq','z09',1), ('A','Rita Zzq','z14',1), ('A','Rita Zzq','z16',1),
  ('A','Ray Zzq','z11',1), ('A','Hank Zzq','z08',1), ('A','Hank Zzq','z16',1), ('A','Hank Zzq','z17',1),
  ('A','Fred Zzq','z13',1), ('A','Nick Zzq','z13',0), ('A','Walt Zzq','z13',0);
CREATE TABLE ssdb_integration.lr_strategy.cell_t (est_source TEXT, zip_code TEXT, state TEXT, dist_ch TEXT, new_dist TEXT, channel TEXT,
  new_terr_channel TEXT, mm_opp DOUBLE);
INSERT INTO ssdb_integration.lr_strategy.cell_t VALUES
  ('E1','z01','MA','FI','NATIONAL (CHASE)','National','FI',100), ('E1','z01','MA','IFA','NATIONAL (CHASE)','National','FI',5),
  ('E1','z02','MA','WH','WELLS FI','National','FI',200), ('E1','z03','MA','WH','WELLS WH','National','FI',300),
  ('E1','z04','MA','WH','WH','WH','',400), ('E1','z04','MA','FI','FI','FI','',40), ('E1','z05','MA','WH','WH','WH','',50),
  ('E1','z06','NH','FI','WELLS FI','National','FI',60), ('E1','z07','NH','WH','WELLS WH','National','FI',70),
  ('E1','z08','NH','FI','NATIONAL (CHASE)','National','FI',80), ('E1','z09','VT','FI','FI','FI','',90),
  ('E1','z10','CT','FI','FI','FI','',100), ('E1','z11','CT','WH','WELLS WH','National','FI',110),
  ('E1','z12','ME','WH','WH','WH','',120), ('E1','z13','ME','FI','FI','FI','',130), ('E1','z14','ME','FI','NATIONAL (CHASE)','National','FI',140),
  ('E1','z15',NULL,'FI','FI','FI','',150), ('E1','z16','MA','FI','FI','FI','',160), ('E1','z17','MA','FI','FI','FI','',170),
  ('E1','z18','MA','WH','WELLS FI','National','FI',180),
  ('E2','z01','MA','FI','NATIONAL (CHASE)','National','FI',11), ('E2','z12','ME','WH','WH','WH','',7),
  ('E2','z18','MA','WH','WELLS FI','National','FI',3), ('E2','z18','MA','IFA','WELLS FI','National','FI',4);
SQL
echo "$1"
sed -e "s/LISTAGG(\([a-z_]*\), ' ') WITHIN GROUP (ORDER BY \([a-z_]*\))/string_agg(\1, ' ' ORDER BY \2)/g" \
    -e "s/\\\\\\\\s+', ' ')/\\\\s+', ' ', 'g')/g" -e '/^use /d' -e '/^SET /d' -e 's/TEMPORARY TABLE/TABLE/' \
    -e "s/^WITH\$/CREATE TABLE full_result AS WITH/" -e "s/[\$]scenario/'  S1 '/g" \
    -e 's/IDENTIFIER(\$cell_tbl)/ssdb_integration.lr_strategy.cell_t/g' \
    -e 's/IDENTIFIER(\$piece_tbl)/ssdb_integration.lr_strategy.piece_t/g' \
    -e 's/IDENTIFIER(\$assign_tbl)/ssdb_integration.lr_strategy.assign_t/g' \
    -e 's/IDENTIFIER(\$holder_tbl)/ssdb_integration.lr_strategy.hk_t/g' "${SQL07:-$here/07_overlap_gap.sql}"
cat <<'SQL'
CREATE MACRO chk(name, got, want) AS CASE WHEN got IS NOT DISTINCT FROM want THEN 'ok'
  ELSE error(name || ': got ' || COALESCE(CAST(got AS VARCHAR), 'NULL') || ', want ' || CAST(want AS VARCHAR)) END;
CREATE MACRO i(x) AS COALESCE(CAST(CAST(x AS BIGINT) AS VARCHAR), '-');
CREATE MACRO sec(s) AS (SELECT string_agg(concat_ws('|', COALESCE(est_source, '-'), COALESCE(channel, '-'), item, i(n_zips), i(mm_opp), COALESCE(CAST(round(pct, 1) AS VARCHAR), '-'), must_be_zero),
                        ' / ' ORDER BY est_source, channel, item) FROM full_result WHERE section = s);
SQL
}
{
emit ''
cat <<'SQL'
SELECT
 chk('result columns', (SELECT string_agg(column_name, ',' ORDER BY column_index) FROM duckdb_columns() WHERE table_name = 'full_result'),
     'section,scenario,est_source,channel,item,n_zips,mm_opp,pct,must_be_zero'),
 chk('table columns', (SELECT string_agg(table_name || ':' || cols, ' ' ORDER BY table_name) FROM
      (SELECT table_name, string_agg(column_name, ',' ORDER BY column_index) AS cols FROM duckdb_columns() WHERE table_name LIKE 'td_gap_%' GROUP BY table_name)),
     'td_gap_cell:scenario,est_source,zip_code,state,new_dist,mm_opp,channel,assigned,class,n_holders,holders'
     || ' td_gap_pair:scenario,est_source,channel,holder_a,holder_b,n_zips,mm_opp'
     || ' td_gap_person:scenario,est_source,holder,source,role,assigned_states,opp_assigned,opp_covered,opp_overlap,opp_gap,opp_held_by_another,opp_held_elsewhere,n_zips_assigned'),
 -- priority chain: z01 Chase, z02 Wells FI, z03 Wells WH with a NATIONAL person (Nan) assigned to MA go NATIONAL (z03 holders R8 R10 R15 is the 3-holder overlap)
 -- MA also has a WH (Walt) and a WIFI (Rita) person: z04 WH goes to WH, z04 FI to REGIONAL, z05 WH has only Rita holding: GAP of WH.  NH has no NATIONAL person:
 -- z06 Wells FI and z08 Chase fall to REGIONAL (not WH), z07 Wells WH to WH.  z08 held by Hank not Rita: HELD BY ANOTHER.  z09 VT: Rita and Rex both assigned (R5 R30
 -- by number): DOUBLE ASSIGNED first.  CT: Ray only, z10 GAP, z11 Wells WH falls through to REGIONAL, COVERED.  ME no one assigned: z12 and z14 held (z14 by a WH and a
 -- WIFI person), z13 UNHELD (Fred is FI, Nick not kept) and z15 has no state.  z16 two WIFI holders OVERLAP, z17 Hank only.  z01's IFA row is its own cell.
 chk('TD_GAP_CELL', (SELECT string_agg(concat_ws('|', est_source, zip_code, COALESCE(state, '-'), new_dist, i(mm_opp), channel, COALESCE(assigned, '-'), class, n_holders, COALESCE(holders, '-')),
                                        ' / ' ORDER BY est_source, zip_code, new_dist, mm_opp) FROM ssdb_integration.lr_strategy.td_gap_cell),
     'E1|z01|MA|NATIONAL (CHASE)|5|NATIONAL|R10|COVERED|1|R10 / E1|z01|MA|NATIONAL (CHASE)|100|NATIONAL|R10|COVERED|1|R10'
     || ' / E1|z02|MA|WELLS FI|200|NATIONAL|R10|GAP|0|- / E1|z03|MA|WELLS WH|300|NATIONAL|R10|OVERLAP|3|R8 R10 R15'
     || ' / E1|z04|MA|FI|40|REGIONAL|R30|COVERED|1|R30 / E1|z04|MA|WH|400|WH|R20|COVERED|1|R20 / E1|z05|MA|WH|50|WH|R20|GAP|0|-'
     || ' / E1|z06|NH|WELLS FI|60|REGIONAL|R30|COVERED|1|R30 / E1|z07|NH|WELLS WH|70|WH|R20|COVERED|1|R20'
     || ' / E1|z08|NH|NATIONAL (CHASE)|80|REGIONAL|R30|HELD BY ANOTHER|1|R35 / E1|z09|VT|FI|90|REGIONAL|R5 R30|DOUBLE ASSIGNED|1|R30'
     || ' / E1|z10|CT|FI|100|REGIONAL|R40|GAP|0|- / E1|z11|CT|WELLS WH|110|REGIONAL|R40|COVERED|1|R40'
     || ' / E1|z12|ME|WH|120|OPEN|-|OPEN SEAT HELD|1|R25 / E1|z13|ME|FI|130|OPEN|-|OPEN SEAT UNHELD|0|- / E1|z14|ME|NATIONAL (CHASE)|140|OPEN|-|OPEN SEAT HELD|2|R25 R30'
     || ' / E1|z15|-|FI|150|OPEN|-|OPEN SEAT UNHELD|0|- / E1|z16|MA|FI|160|REGIONAL|R30|OVERLAP|2|R30 R35 / E1|z17|MA|FI|170|REGIONAL|R30|HELD BY ANOTHER|1|R35'
     || ' / E1|z18|MA|WELLS FI|180|NATIONAL|R10|OVERLAP|2|R8 R10 / E2|z01|MA|NATIONAL (CHASE)|11|NATIONAL|R10|COVERED|1|R10 / E2|z12|ME|WH|7|OPEN|-|OPEN SEAT HELD|1|R25'
     || ' / E2|z18|MA|WELLS FI|3|NATIONAL|R10|OVERLAP|2|R8 R10 / E2|z18|MA|WELLS FI|4|NATIONAL|R10|OVERLAP|2|R8 R10'),
 chk('scenario column trimmed', (SELECT string_agg(DISTINCT scenario, ',') FROM ssdb_integration.lr_strategy.td_gap_cell), 'S1'),
 -- the 3-holder cell z03 is in 3 pairs (R8 R10, R8 R15, R10 R15), R8 R10 also has z18 (2 ZIPs, 300 + 180).  R30 R35 only z16.  E2 has no overlap.
 chk('TD_GAP_PAIR', (SELECT string_agg(concat_ws('|', scenario, est_source, channel, holder_a, holder_b, n_zips, i(mm_opp)), ' / ' ORDER BY est_source, channel, holder_a, holder_b)
                     FROM ssdb_integration.lr_strategy.td_gap_pair),
     'S1|E1|NATIONAL|R10|R15|1|300 / S1|E1|NATIONAL|R8|R10|2|480 / S1|E1|NATIONAL|R8|R15|1|300 / S1|E1|REGIONAL|R30|R35|1|160'
     || ' / S1|E2|NATIONAL|R8|R10|1|7'),
 -- per person: assigned = the cells attributed to them (Rita 40+160+170+60+80+90), by class, then the cells on ZIPs they hold in role that are not theirs
 -- (Rita: z04 WH 400, z05 WH 50, z14 OPEN 140), then ZIPs assigned.  Rex shares z09 (DOUBLE ASSIGNED, in OPP_ASSIGNED only).  Fred (FI) and Nick (not kept) are not people here.
 chk('TD_GAP_PERSON', (SELECT string_agg(concat_ws('|', est_source, holder, source, role, COALESCE(assigned_states, '-'), i(opp_assigned), i(opp_covered), i(opp_overlap), i(opp_gap),
                                                   i(opp_held_by_another), i(opp_held_elsewhere), n_zips_assigned), ' / '
                                         ORDER BY est_source, CAST(substr(holder, 2) AS INTEGER)) FROM ssdb_integration.lr_strategy.td_gap_person),
     'E1|R5|B|WIFI|VT|90|0|0|0|0|0|1 / E1|R8|B|NATIONAL|-|0|0|0|0|0|480|0 / E1|R10|A|NATIONAL|MA|785|105|480|200|0|60|4 / E1|R15|A|NATIONAL|-|0|0|0|0|0|300|0'
     || ' / E1|R20|A|WH|MA NH|520|470|0|50|0|40|3 / E1|R25|A|WH|-|0|0|0|0|0|260|0 / E1|R30|A|WIFI|MA NH VT|600|100|160|0|250|590|6'
     || ' / E1|R35|A|WIFI|-|0|0|0|0|0|410|0 / E1|R40|A|WIFI|CT|210|110|0|100|0|0|2'
     || ' / E2|R5|B|WIFI|VT|0|0|0|0|0|0|0 / E2|R8|B|NATIONAL|-|0|0|0|0|0|7|0 / E2|R10|A|NATIONAL|MA|18|11|7|0|0|0|2 / E2|R15|A|NATIONAL|-|0|0|0|0|0|0|0'
     || ' / E2|R20|A|WH|MA NH|0|0|0|0|0|0|0 / E2|R25|A|WH|-|0|0|0|0|0|7|0 / E2|R30|A|WIFI|MA NH VT|0|0|0|0|0|0|0'
     || ' / E2|R35|A|WIFI|-|0|0|0|0|0|0|0 / E2|R40|A|WIFI|CT|0|0|0|0|0|0|0'),
 -- E1 main map 2655 (class rows add to it), E2 25 (z18 has two cells, one pair counts its ZIP once)
 chk('CLASS', sec('CLASS'),
     'E1|NATIONAL|COVERED|1|105|4.0|0 / E1|NATIONAL|GAP|1|200|7.5|0 / E1|NATIONAL|OVERLAP|2|480|18.1|0'
     || ' / E1|OPEN|OPEN SEAT HELD|2|260|9.8|0 / E1|OPEN|OPEN SEAT UNHELD|2|280|10.5|0'
     || ' / E1|REGIONAL|COVERED|3|210|7.9|0 / E1|REGIONAL|DOUBLE ASSIGNED|1|90|3.4|0 / E1|REGIONAL|GAP|1|100|3.8|0 / E1|REGIONAL|HELD BY ANOTHER|2|250|9.4|0 / E1|REGIONAL|OVERLAP|1|160|6.0|0'
     || ' / E1|WH|COVERED|2|470|17.7|0 / E1|WH|GAP|1|50|1.9|0'
     || ' / E2|NATIONAL|COVERED|1|11|44.0|0 / E2|NATIONAL|OVERLAP|1|7|28.0|0 / E2|OPEN|OPEN SEAT HELD|1|7|28.0|0'),
 chk('STATE', (SELECT string_agg(concat_ws('|', est_source, channel, item, i(n_zips), i(mm_opp)), ' / ' ORDER BY est_source, channel, item) FROM full_result WHERE section = 'STATE' AND est_source = 'E1'),
     'E1|NATIONAL|MA | COVERED|1|105 / E1|NATIONAL|MA | GAP|1|200 / E1|NATIONAL|MA | OVERLAP|2|480'
     || ' / E1|OPEN|(NO STATE) | OPEN SEAT UNHELD|1|150 / E1|OPEN|ME | OPEN SEAT HELD|2|260 / E1|OPEN|ME | OPEN SEAT UNHELD|1|130'
     || ' / E1|REGIONAL|CT | COVERED|1|110 / E1|REGIONAL|CT | GAP|1|100 / E1|REGIONAL|MA | COVERED|1|40 / E1|REGIONAL|MA | HELD BY ANOTHER|1|170 / E1|REGIONAL|MA | OVERLAP|1|160'
     || ' / E1|REGIONAL|NH | COVERED|1|60 / E1|REGIONAL|NH | HELD BY ANOTHER|1|80 / E1|REGIONAL|VT | DOUBLE ASSIGNED|1|90'
     || ' / E1|WH|MA | COVERED|1|400 / E1|WH|MA | GAP|1|50 / E1|WH|NH | COVERED|1|70'),
 chk('TIE (all clean)', sec('TIE'),
     'E1|-|CELLS WITH NO CLASS|0|0|-|1 / E1|-|CLASSES MINUS TD_MAP_CELL, MAIN MAP (N_ZIPS 1 = THEY DIFFER)|0|0|-|1'
     || ' / E2|-|CELLS WITH NO CLASS|0|0|-|1 / E2|-|CLASSES MINUS TD_MAP_CELL, MAIN MAP (N_ZIPS 1 = THEY DIFFER)|0|0|-|1 / -|-|KEPT HOLDERS WITH NO td_holder_key ROW|0|-|-|1'),
 chk('no name or holder id in the tables or result',
     (SELECT COUNT(*) FROM full_result f WHERE regexp_matches(CAST(f AS VARCHAR), 'zzq', 'i'))
     + (SELECT COUNT(*) FROM ssdb_integration.lr_strategy.td_gap_cell f WHERE regexp_matches(CAST(f AS VARCHAR), 'zzq', 'i'))
     + (SELECT COUNT(*) FROM ssdb_integration.lr_strategy.td_gap_pair f WHERE regexp_matches(CAST(f AS VARCHAR), 'zzq', 'i'))
     + (SELECT COUNT(*) FROM ssdb_integration.lr_strategy.td_gap_person f WHERE regexp_matches(CAST(f AS VARCHAR), 'zzq', 'i')), 0);
SELECT '07_overlap_gap_test: first run ok';
SQL
} | duckdb -bail -noheader -list
# second run: Kay is kept WIFI in VT with no key row: the no-key TIE row reads 1, and her NULL key adds nothing to the strings
{
emit "INSERT INTO ssdb_integration.lr_strategy.assign_t VALUES ('A','Kay Zzq','Y','WIFI','VT');"
cat <<'SQL'
SELECT
 chk('Kay has no key: counted by the TIE row',
     sec('TIE'), 'E1|-|CELLS WITH NO CLASS|0|0|-|1 / E1|-|CLASSES MINUS TD_MAP_CELL, MAIN MAP (N_ZIPS 1 = THEY DIFFER)|0|0|-|1'
     || ' / E2|-|CELLS WITH NO CLASS|0|0|-|1 / E2|-|CLASSES MINUS TD_MAP_CELL, MAIN MAP (N_ZIPS 1 = THEY DIFFER)|0|0|-|1 / -|-|KEPT HOLDERS WITH NO td_holder_key ROW|1|-|-|1'),
 chk('z09: Kay makes 3 assigned, still DOUBLE ASSIGNED, her NULL key adds nothing to the string',
     (SELECT class || ' ' || assigned FROM ssdb_integration.lr_strategy.td_gap_cell WHERE zip_code = 'z09'), 'DOUBLE ASSIGNED R5 R30');
SELECT '07_overlap_gap_test: second run ok';
SQL
} | duckdb -bail -noheader -list
# third and fourth run: the TIE must flag a broken script.  (a) the last class branch removed: HELD BY ANOTHER cells z08 80 and z17 170 get no class,
# so 2 cells 250 with no class and the classes are 250 short.  (b) the class table loses its third cell (E1 z02, 200): short by 200, every cell has a class.
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
sed -e "s/ELSE 'HELD BY ANOTHER' END AS class/END AS class/" "$here/07_overlap_gap.sql" > "$tmp/a.sql"
sed -e 's/FROM ssdb_integration.lr_strategy.tmp_g_cls;/FROM ssdb_integration.lr_strategy.tmp_g_cls WHERE cid <> 3;/' "$here/07_overlap_gap.sql" > "$tmp/b.sql"
for v in a b; do
if [ $v = a ]; then want='E1|-|CELLS WITH NO CLASS|2|250|-|1 / E1|-|CLASSES MINUS TD_MAP_CELL, MAIN MAP (N_ZIPS 1 = THEY DIFFER)|1|-250|-|1'
else want='E1|-|CELLS WITH NO CLASS|0|0|-|1 / E1|-|CLASSES MINUS TD_MAP_CELL, MAIN MAP (N_ZIPS 1 = THEY DIFFER)|1|-200|-|1'; fi
{
SQL07="$tmp/$v.sql" emit ''
cat <<SQL
SELECT chk('TIE flags the broken script ($v)',
  (SELECT string_agg(concat_ws('|', est_source, COALESCE(channel, '-'), item, i(n_zips), i(mm_opp), COALESCE(CAST(pct AS VARCHAR), '-'), must_be_zero), ' / ' ORDER BY item)
   FROM full_result WHERE section = 'TIE' AND est_source = 'E1'), '$want');
SELECT '07_overlap_gap_test: TIE flags script $v';
SQL
} | duckdb -bail -noheader -list
done
echo "07_overlap_gap_test: ok"
