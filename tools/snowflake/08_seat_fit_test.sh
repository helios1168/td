#!/bin/sh
# Runs 08_seat_fit.sql in DuckDB on made-up TD_GAP_CELL, TD_MAP_PIECE, td_assignments, td_holder_key, td_state_adj and a sales table (the real
# column names) and checks TD_SEAT_FIT and the result against answers worked out by hand (comment at each group).  theta 0.40, lambda 0.30: c1 0.70, c2 0.28.
# People, key, source, role, assigned states: Ann R10 A NATIONAL NH / Bob R20 A WH CT / Dee R40 A WIFI CT / Cy R30 B WIFI MA / Rex R5 B WIFI MA / Eve R60 A WIFI NH.
# Only a WIFI person is a NEIGHBOUR (owner, DATASET_LOG 2026-11-19): Ann (NATIONAL) and Bob (WH) border ME but are not neighbours, Bob is still a HOLDER there (BORDERS 0).
# Nick R45 is not kept and holds a piece in ME.  Next-door states (both ways): ME-NH, ME-CT, MA-RI.  Seats of E1: ME (OPEN z0001 100, z0002 40 + 20) and RI
# (z0011 30), of E2: ME (z0001 10).  Sales (A unless said), ZIP: Ann z0020 100, z0021 50, z0001 40 / Bob z0022 200, z0001 10 / Nick z0001 70, z0002 30 / Cy (B) z0023 300,
# z0011 20 / Rex (B) z0023 60 / 'OPEN' seller z0001 20 / blank seller z0002 5 / a seller with no key z0020 25.  Not counted: an IFA row and a 0 row.
# So T z0001 140, z0002 35, z0011 20, z0020 125, z0021 50, z0022 200, z0023 360.  A second run raises Eve's book (the DNASH order flips), a third adds
# a kept person and a holder with no key and a seat nobody can take.  Mutations (c2, lambda, the share rule removed, the DNASH order reversed, the neighbour role filter back to
# NATIONAL, WH or WIFI) must each fail the first checks.
# exclude_products (04's switch, FIXED by default): the product of every sale is INDEX but Mia's is NULL and the blank seller's is '' (kept by every list), and one
# FIXED sale of Ann's (10 in z0001) is left out by the default.  A run with '' counts it: S(Ann, z0001) 50, T(z0001) 150, so the ME seat's U moves by c1 * 10 = 7 for Ann
# and c2 * 10 = 2.8 for everyone else; 'RILA  VARIABLE' (a double space, no such product) is the same as ''.  Mutations (the filter off, the blank guard off) must fail.
# Prints "08_seat_fit_test: ok" or stops at the first failed check.  Run from anywhere: sh 08_seat_fit_test.sh
set -e
here=$(cd "$(dirname "$0")" && pwd)
# the script as DuckDB runs it ($1 = extra SQL before it, run in the same database; $2 = the exclude_products list, FIXED when not given)
emit() {
cat <<'SQL'
ATTACH ':memory:' AS ssdb_integration; CREATE SCHEMA ssdb_integration.lr_strategy;
CREATE MACRO UUID_STRING(ns, nm) AS md5(ns || nm);
CREATE TABLE ssdb_integration.lr_strategy.assign_t (source TEXT, wholesaler TEXT, kept TEXT, role TEXT, assigned_states TEXT);
INSERT INTO ssdb_integration.lr_strategy.assign_t VALUES
  ('A','Ann Zzq','Y','NATIONAL','NH'), ('A','Bob Zzq','y','wh','CT'), ('A','Dee Zzq','Y','WIFI','CT'), ('B','Cy Zzq','Y','WIFI','MA'),
  ('B','Rex Zzq','Y','WIFI','MA'), ('A','Nick Zzq','N','WIFI','ME'), ('A','Eve Zzq','Y','WIFI','NH');
CREATE TABLE ssdb_integration.lr_strategy.hk_t (source TEXT, holder_id TEXT, holder_n INTEGER);
INSERT INTO ssdb_integration.lr_strategy.hk_t SELECT source, UUID_STRING('6ba7b810-9dad-11d1-80b4-00c04fd430c8', nm), n
FROM (VALUES ('A','ANN ZZQ',10), ('A','BOB ZZQ',20), ('A','DEE ZZQ',40), ('B','CY ZZQ',30), ('B','REX ZZQ',5), ('A','NICK ZZQ',45), ('A','EVE ZZQ',60)) v(source, nm, n);
CREATE TABLE ssdb_integration.lr_strategy.adj_t (state_a TEXT, state_b TEXT);
INSERT INTO ssdb_integration.lr_strategy.adj_t VALUES ('ME','NH'), ('NH','ME'), ('ME','CT'), ('CT','ME'), ('MA','RI'), ('RI','MA');
-- Bob holds in ME (kept, also a neighbour), Nick holds in ME (not kept, no neighbour), Ann holds in RI (a holder there, not a neighbour)
CREATE TABLE ssdb_integration.lr_strategy.piece_t (source TEXT, wholesaler TEXT, kept TEXT, role TEXT, zip_code TEXT, state TEXT, terr_channel TEXT, piece_in_role INTEGER);
INSERT INTO ssdb_integration.lr_strategy.piece_t VALUES
  ('A','Bob Zzq','Y','WH','z0001','ME','WH',1), ('A','BOB  zzq ','Y','WH','z0002','ME','WH',1), ('A','Nick Zzq','','WIFI','z0002','ME','FI',0), ('A','Ann Zzq','Y','NATIONAL','z0011','RI','WH',1);
CREATE TABLE ssdb_integration.lr_strategy.union_t (source TEXT, zip_code TEXT, channel TEXT, sales_wholesaler TEXT, actual_sales_amount DOUBLE, product_v2 TEXT DEFAULT 'INDEX');
INSERT INTO ssdb_integration.lr_strategy.union_t (source, zip_code, channel, sales_wholesaler, actual_sales_amount) VALUES
  ('A','z0020','National','Ann Zzq',100), ('A','z0021','WH','ann  zzq ',50), ('A','z0001','FI','Ann Zzq',40), ('A','z0022','WH','Bob Zzq',200), ('A','z0001','FI','Bob Zzq',10),
  ('A','z0001','FI','Nick Zzq',70), ('A','z0002','FI','Nick Zzq',30), ('B','z0023','National','Cy Zzq',300), ('B','z0011','FI','Cy Zzq',20), ('B','z0023','National','Rex Zzq',60),
  ('A','z0001','FI',' open',20), ('A','z0002','FI','  ',5), ('A','z0020','WH','Mia Zzq',25), ('A','z0001','IFA','Ann Zzq',1000), ('A','z0002','FI','Ann Zzq',0);
UPDATE ssdb_integration.lr_strategy.union_t SET product_v2 = NULL WHERE sales_wholesaler = 'Mia Zzq';
UPDATE ssdb_integration.lr_strategy.union_t SET product_v2 = '' WHERE sales_wholesaler = '  ';
INSERT INTO ssdb_integration.lr_strategy.union_t VALUES ('A','z0001','FI','Ann Zzq',10,'FIXED');
-- the gap table: S1 is the scenario, S2 a noise scenario that must not show (an extra seat ZZ and a book for Ann)
CREATE TABLE ssdb_integration.lr_strategy.gap_t (scenario TEXT, est_source TEXT, zip_code TEXT, state TEXT, new_dist TEXT, mm_opp DOUBLE, channel TEXT,
  assigned TEXT, class TEXT, n_holders INTEGER, holders TEXT);
INSERT INTO ssdb_integration.lr_strategy.gap_t VALUES
  ('S1','E1','z0001','ME','FI',100,'OPEN',NULL,'OPEN SEAT HELD',1,'R20'), ('S1','E1','z0002','ME','FI',40,'OPEN',NULL,'OPEN SEAT HELD',1,'R20'),
  ('S1','E1','z0002','ME','WH',20,'OPEN',NULL,'OPEN SEAT UNHELD',0,NULL), ('S1','E1','z0011','RI','FI',30,'OPEN',NULL,'OPEN SEAT HELD',1,'R10'),
  ('S1','E1','z0099',NULL,'FI',500,'OPEN',NULL,'OPEN SEAT UNHELD',0,NULL),
  ('S1','E1','z0020','NH','WELLS FI',200,'NATIONAL','R10','COVERED',1,'R10'), ('S1','E1','z0021','NH','WELLS FI',100,'NATIONAL','R10','COVERED',1,'R10'),
  ('S1','E1','z0022','CT','WH',50,'WH','R20','COVERED',1,'R20'), ('S1','E1','z0022','CT','WH',80,'WH','R20 R50','OVERLAP',2,'R20 R50'),
  ('S1','E1','z0023','MA','FI',400,'REGIONAL','R5 R30','COVERED',1,'R30'),
  ('S1','E1','z0030','NH','FI',50,'REGIONAL','R60','COVERED',1,'R60'), ('S1','E1','z0031','CT','FI',100,'REGIONAL','R40','COVERED',1,'R40'),
  ('S1','E2','z0031','CT','FI',20,'REGIONAL','R40','COVERED',1,'R40'),
  ('S1','E2','z0001','ME','FI',10,'OPEN',NULL,'OPEN SEAT HELD',1,'R20'), ('S1','E2','z0020','NH','WELLS FI',8,'NATIONAL','R10','COVERED',1,'R10'),
  ('S2','E1','z0050','ZZ','FI',999,'OPEN',NULL,'OPEN SEAT UNHELD',0,NULL), ('S2','E1','z0020','NH','WELLS FI',7777,'NATIONAL','R10','COVERED',1,'R10');
SQL
echo "$1"
sed -e "s/[\$]exclude_products/'${2-FIXED}'/g" -e "s/\\\\\\\\s+', ' ')/\\\\s+', ' ', 'g')/g" -e '/^use /d' -e '/^SET /d' -e 's/TEMPORARY TABLE/TABLE/' \
    -e "s/^WITH\$/CREATE TABLE full_result AS WITH/" -e "s/[\$]scenario/'  S1 '/g" \
    -e 's/[$]c1/0.70/g' -e 's/[$]c2/0.28/g' -e 's/[$]lam/0.30/g' \
    -e 's/IDENTIFIER(\$gap_tbl)/ssdb_integration.lr_strategy.gap_t/g' \
    -e 's/IDENTIFIER(\$piece_tbl)/ssdb_integration.lr_strategy.piece_t/g' \
    -e 's/IDENTIFIER(\$assign_tbl)/ssdb_integration.lr_strategy.assign_t/g' \
    -e 's/IDENTIFIER(\$union_tbl)/ssdb_integration.lr_strategy.union_t/g' \
    -e 's/IDENTIFIER(\$adj_tbl)/ssdb_integration.lr_strategy.adj_t/g' \
    -e 's/IDENTIFIER(\$holder_tbl)/ssdb_integration.lr_strategy.hk_t/g' "${SQL08:-$here/08_seat_fit.sql}"
cat <<'SQL'
CREATE MACRO chk(name, got, want) AS CASE WHEN got IS NOT DISTINCT FROM want THEN 'ok'
  ELSE error(name || ': got ' || COALESCE(CAST(got AS VARCHAR), 'NULL') || ', want ' || CAST(want AS VARCHAR)) END;
-- the table's numbers against the hand-worked ones, 1e-9 (want: est, seat, kind, key, U, G, DNASH, NULL where none)
CREATE MACRO near(a, b) AS (a IS NULL AND b IS NULL) OR (a IS NOT NULL AND b IS NOT NULL AND abs(a - b) < 1e-9);
SQL
}
# the checks on the first run's tables
checks_base() {
cat <<'SQL'
CREATE TABLE want (est TEXT, seat TEXT, kind TEXT, holder TEXT, u DOUBLE, g DOUBLE, dnash DOUBLE);
INSERT INTO want VALUES
 -- seat ME, E1: z0001 M 100 and z0002 M 60 (40 + 20), so lambda M = 30 + 18 = 48 for everyone
 -- Only the WIFI people border as neighbours: Dee (CT) and Eve (NH).  Ann (NATIONAL, NH) and Bob (WH, CT) are not NEIGHBOUR rows.
 -- Dee U: no sales, z0001 0.28*140 = 39.2, z0002 0.28*35 = 9.8, +48 = 97.  Dee g: z0031 (share 1, no sales) 0 + lambda*100 = 30
 ('E1','ME','NEIGHBOUR','R40', 97, 30, ln(1 + 97/30)),
 -- Eve U 97 as Dee.  Eve g: z0030 (share 1, no sales) 0 + lambda*50 = 15, so her DNASH ln(1 + 97/15) beats Dee's
 ('E1','ME','NEIGHBOUR','R60', 97, 15, ln(1 + 97/15)),
 -- Nick (not kept, a holder only, no g): z0001 0.7*70 + 0.28*70 = 68.6, z0002 0.7*30 + 0.28*5 = 22.4, +48 = 139
 ('E1','ME','HOLDER','R45', 139, NULL, NULL),
 -- Bob only as a holder (a WH person is not a neighbour): U z0001 0.7*10 + 0.28*130 = 43.4, z0002 9.8, +48 = 101.2.  Bob g: z0022 has two cells, shares 1 ('R20') and
 --   0.5 ('R20 R50', not COVERED by R20 alone: 1/2), w = the largest = 1: 0.7*200 + 0.28*(200-200) = 140, lambda*(50*1 + 80*0.5) = 27, g = 167.  BORDERS 0
 ('E1','ME','HOLDER','R20', 101.2, 167, NULL),
 -- seat RI, E1: z0011 M 30 so lambda M = 9.  Cy U: 0.7*20 + 0.28*0 + 9 = 23.  Cy g: z0023 is 'R5 R30' COVERED by R30 alone: share 1: 0.7*300 + 0.28*60 = 226.8, + 0.3*400 = 346.8
 ('E1','RI','NEIGHBOUR','R30', 23, 346.8, ln(1 + 23/346.8)),
 -- Rex U: 0.28*20 + 9 = 14.6.  Rex g: z0023 is COVERED by Cy alone, so Rex's share is 0 (as gap_load): g 0, DNASH NULL, he ranks after Cy
 -- (with 1/2 shares Rex's g would be 123 and he would rank first)
 ('E1','RI','NEIGHBOUR','R5', 14.6, 0, NULL),
 -- Ann holds in RI, no sale there: U = 14.6, her g 202 as above
 ('E1','RI','HOLDER','R10', 14.6, 202, NULL),
 -- E2, seat ME, z0001 M 10 so lambda M = 3.  U 39.2 + 3 = 42.2 for Dee and Eve.  Dee g 0.3*20 = 6, Eve has no E2 book: g 0, DNASH NULL, ranks after Dee
 ('E2','ME','NEIGHBOUR','R40', 42.2, 6, ln(1 + 42.2/6)),
 ('E2','ME','NEIGHBOUR','R60', 42.2, 0, NULL),
 ('E2','ME','HOLDER','R45', 71.6, NULL, NULL),
 ('E2','ME','HOLDER','R20', 46.4, 0, NULL);
SELECT
 chk('result columns', (SELECT string_agg(column_name, ',' ORDER BY column_index) FROM duckdb_columns() WHERE table_name = 'full_result'),
     'section,scenario,est_source,seat,kind,holder,rank,borders,seat_mm_opp,n,must_be_zero'),
 chk('TD_SEAT_FIT columns', (SELECT string_agg(column_name, ',' ORDER BY column_index) FROM duckdb_columns() WHERE table_name = 'td_seat_fit'),
     'scenario,est_source,seat,seat_mm_opp,kind,holder,source,kept,role,borders,u,g,dnash,rank'),
 chk('the hand-worked U, G, DNASH (rows without a match or off by 1e-9)',
     (SELECT COUNT(*) FROM ssdb_integration.lr_strategy.td_seat_fit f FULL JOIN want w
        ON w.est = f.est_source AND w.seat = f.seat AND w.kind = f.kind AND w.holder = f.holder
      WHERE f.holder IS NULL OR w.holder IS NULL OR NOT (near(f.u, w.u) AND near(f.g, w.g) AND near(f.dnash, w.dnash))), 0),
 -- ranks: ME neighbours Eve (ln 7.4667 = 2.0105) before Dee (ln 4.2333 = 1.4429), RI Cy (0.0641) before Rex (NULL).  ME holders by U Nick 139, Bob 101.2.
 -- BORDERS: Bob 0 as a holder (a WH person is not a neighbour), Nick 0, Ann 0 in RI.  KEPT N and the role for Nick, the firm of each is its source.  Seat sizes 160, 30, 10
 chk('TD_SEAT_FIT, masked columns',
     (SELECT string_agg(concat_ws('|', est_source, seat, CAST(seat_mm_opp AS INTEGER), kind, rank, holder, source, kept, COALESCE(role, '-'), borders), ' / '
                        ORDER BY est_source, seat, kind, rank) FROM ssdb_integration.lr_strategy.td_seat_fit),
     'E1|ME|160|HOLDER|1|R45|A|N|WIFI|0 / E1|ME|160|HOLDER|2|R20|A|Y|WH|0'
     || ' / E1|ME|160|NEIGHBOUR|1|R60|A|Y|WIFI|1 / E1|ME|160|NEIGHBOUR|2|R40|A|Y|WIFI|1'
     || ' / E1|RI|30|HOLDER|1|R10|A|Y|NATIONAL|0 / E1|RI|30|NEIGHBOUR|1|R30|B|Y|WIFI|1 / E1|RI|30|NEIGHBOUR|2|R5|B|Y|WIFI|1'
     || ' / E2|ME|10|HOLDER|1|R45|A|N|WIFI|0 / E2|ME|10|HOLDER|2|R20|A|Y|WH|0'
     || ' / E2|ME|10|NEIGHBOUR|1|R40|A|Y|WIFI|1 / E2|ME|10|NEIGHBOUR|2|R60|A|Y|WIFI|1'),
 chk('result: seats, ties and the SEAT rows are the table',
     (SELECT string_agg(concat_ws('|', section, COALESCE(est_source, '-'), COALESCE(seat, '-'), COALESCE(kind, '-'), COALESCE(CAST(n AS VARCHAR), '-'), must_be_zero), ' / '
                        ORDER BY section, est_source, seat, kind) FROM full_result WHERE section <> 'SEAT'),
     'SEATS|E1|-|-|2|0 / SEATS|E2|-|-|1|0 / TIE|E1|-|SEATS WITH NO CANDIDATE|0|1 / TIE|E2|-|SEATS WITH NO CANDIDATE|0|1'
     || ' / TIE|-|-|CANDIDATES WITH NO td_holder_key ROW|0|1'),
 chk('SEAT rows = TD_SEAT_FIT rows', (SELECT COUNT(*) FROM full_result WHERE section = 'SEAT'), (SELECT COUNT(*) FROM ssdb_integration.lr_strategy.td_seat_fit)),
 chk('scenario column trimmed', (SELECT string_agg(DISTINCT scenario, ',') FROM ssdb_integration.lr_strategy.td_seat_fit), 'S1'),
 chk('no name in the result or the table',
     (SELECT COUNT(*) FROM full_result f WHERE regexp_matches(CAST(f AS VARCHAR), 'zzq', 'i'))
     + (SELECT COUNT(*) FROM ssdb_integration.lr_strategy.td_seat_fit f WHERE regexp_matches(CAST(f AS VARCHAR), 'zzq', 'i')), 0);
SQL
}
{
emit ''
checks_base
echo "SELECT '08_seat_fit_test: first run ok';"
} | duckdb -bail -noheader -list
# second run: Eve's E1 book grows (z0030 cell 50 -> 200): g 0.3*200 = 60, U as before 97.  Eve ln(1 + 97/60) = 0.9622 now falls behind Dee ln(1 + 97/30) = 1.4429.  The other order is
# the first run.  Holders do not move.
{
emit "UPDATE ssdb_integration.lr_strategy.gap_t SET mm_opp = 200 WHERE zip_code = 'z0030' AND est_source = 'E1';"
cat <<'SQL'
SELECT
 chk('the DNASH order flips', (SELECT string_agg(holder || ':' || rank, ' ' ORDER BY rank) FROM ssdb_integration.lr_strategy.td_seat_fit
                               WHERE est_source = 'E1' AND seat = 'ME' AND kind = 'NEIGHBOUR'), 'R40:1 R60:2'),
 chk('flipped DNASH Eve', (SELECT abs(dnash - ln(1 + 97/60)) < 1e-9 FROM ssdb_integration.lr_strategy.td_seat_fit WHERE est_source = 'E1' AND holder = 'R60' AND kind = 'NEIGHBOUR' AND seat = 'ME'), true),
 chk('flipped DNASH Dee', (SELECT abs(dnash - ln(1 + 97/30)) < 1e-9 FROM ssdb_integration.lr_strategy.td_seat_fit WHERE est_source = 'E1' AND holder = 'R40' AND kind = 'NEIGHBOUR' AND seat = 'ME'), true),
 chk('holders do not move (Nick 139, Bob 101.2)', (SELECT string_agg(holder || ':' || rank, ' ' ORDER BY rank) FROM ssdb_integration.lr_strategy.td_seat_fit
                               WHERE est_source = 'E1' AND seat = 'ME' AND kind = 'HOLDER'), 'R45:1 R20:2');
SELECT '08_seat_fit_test: flip run ok';
SQL
} | duckdb -bail -noheader -list
# third run: Kay is kept, WIFI, next to ME (NH) and has no key, Zed holds a piece in ME and has no key (2 people with no key, neither in the table), and E3 has an
# OPEN seat WY that no one borders or holds (1 seat with no candidate).  Everything else of E1 and E2 is as in the first run
{
emit "INSERT INTO ssdb_integration.lr_strategy.assign_t VALUES ('A','Kay Zzq','Y','WIFI','NH');
INSERT INTO ssdb_integration.lr_strategy.piece_t VALUES ('A','Zed Zzq','','WIFI','z0001','ME','FI',0);
INSERT INTO ssdb_integration.lr_strategy.gap_t VALUES ('S1','E3','z0060','WY','FI',5,'OPEN',NULL,'OPEN SEAT UNHELD',0,NULL);"
cat <<'SQL'
SELECT
 chk('TIE flags keyless people and a seat nobody can take',
     (SELECT string_agg(concat_ws('|', COALESCE(est_source, '-'), kind, n, must_be_zero), ' / ' ORDER BY est_source, kind) FROM full_result WHERE section = 'TIE'),
     'E1|SEATS WITH NO CANDIDATE|0|1 / E2|SEATS WITH NO CANDIDATE|0|1 / E3|SEATS WITH NO CANDIDATE|1|1 / -|CANDIDATES WITH NO td_holder_key ROW|2|1'),
 chk('the keyless are not in the table', (SELECT COUNT(*) FROM ssdb_integration.lr_strategy.td_seat_fit WHERE est_source <> 'E3'), 11),
 chk('E3 has a seat and its SEATS row', (SELECT n FROM full_result WHERE section = 'SEATS' AND est_source = 'E3'), 1);
SELECT '08_seat_fit_test: tie run ok';
SQL
} | duckdb -bail -noheader -list
# the FIXED sale counted: the ME seat's U (Dee and Eve +2.8, ranks as before: Eve ln(1 + 99.8/15) ahead of Dee ln(1 + 99.8/30)), g unchanged
checks_all() {
cat <<'SQL'
SELECT
 chk('FIXED counted: U of the ME seat',
     (SELECT string_agg(est_source || ' ' || kind || ' ' || holder || ' ' || CAST(round(u, 1) AS VARCHAR), ' / ' ORDER BY est_source, kind, holder)
      FROM ssdb_integration.lr_strategy.td_seat_fit WHERE seat = 'ME'),
     'E1 HOLDER R20 104.0 / E1 HOLDER R45 141.8 / E1 NEIGHBOUR R40 99.8 / E1 NEIGHBOUR R60 99.8'
     || ' / E2 HOLDER R20 49.2 / E2 HOLDER R45 74.4 / E2 NEIGHBOUR R40 45.0 / E2 NEIGHBOUR R60 45.0'),
 chk('FIXED counted: the RI seat does not move',
     (SELECT string_agg(kind || ' ' || holder || ' ' || CAST(round(u, 1) AS VARCHAR), ' / ' ORDER BY kind, holder) FROM ssdb_integration.lr_strategy.td_seat_fit WHERE seat = 'RI'),
     'HOLDER R10 14.6 / NEIGHBOUR R30 23.0 / NEIGHBOUR R5 14.6'),
 chk('FIXED counted: g does not move (Dee 30, Eve 15)',
     (SELECT string_agg(holder || ' ' || CAST(round(g, 1) AS VARCHAR), ' / ' ORDER BY holder) FROM ssdb_integration.lr_strategy.td_seat_fit WHERE est_source = 'E1' AND seat = 'ME' AND kind = 'NEIGHBOUR'),
     'R40 30.0 / R60 15.0'),
 chk('FIXED counted: ranks', (SELECT string_agg(est_source || ':' || holder || ':' || rank, ' ' ORDER BY est_source, rank) FROM ssdb_integration.lr_strategy.td_seat_fit WHERE seat = 'ME' AND kind = 'NEIGHBOUR'),
     'E1:R60:1 E1:R40:2 E2:R40:1 E2:R60:2');
SQL
}
{ emit '' ''; checks_all; echo "SELECT '08_seat_fit_test: include-all run ok';"; } | duckdb -bail -noheader -list
{ emit '' 'RILA  VARIABLE'; checks_all; echo "SELECT '08_seat_fit_test: double-space run ok';"; } | duckdb -bail -noheader -list
# mutations: each broken script must fail the first run's checks (a "got ... want" error)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
sed -e 's/[$]c2/0/g' "$here/08_seat_fit.sql" > "$tmp/c2.sql"
sed -e 's/[$]lam/0/g' "$here/08_seat_fit.sql" > "$tmp/lam.sql"
sed -e "s/WHEN g.class = 'COVERED' THEN CASE WHEN g.holders = p.k THEN 1 ELSE 0 END //" "$here/08_seat_fit.sql" > "$tmp/share.sql"
sed -e "s/WHERE p.role = 'WIFI';/WHERE p.role IN ('NATIONAL', 'WH', 'WIFI');/" "$here/08_seat_fit.sql" > "$tmp/roles.sql"
sed -e "s/ORDER BY CASE WHEN x.kind = 'NEIGHBOUR' THEN x.dnash END DESC/ORDER BY CASE WHEN x.kind = 'NEIGHBOUR' THEN x.dnash END ASC/" "$here/08_seat_fit.sql" > "$tmp/asc.sql"
# the filter off (the default run must fail), the blank-product guard off (the double-space run must fail)
cut() { awk '/^ +AND .*[$]exclude_products/ { sub(/AND \(\(.*= ..\)/, "AND 1 = 1") } { print }' "$here/08_seat_fit.sql"; }
cut > "$tmp/nofilter.sql"
sed -e "s/ OR COALESCE(TRIM(product_v2), '') = ''//" "$here/08_seat_fit.sql" > "$tmp/noguard.sql"
for v in nofilter noguard; do
  cmp -s "$tmp/$v.sql" "$here/08_seat_fit.sql" && { echo "08_seat_fit_test: mutation $v changed nothing"; exit 1; }
  bad=0
  for ex in FIXED 'RILA  VARIABLE'; do
    if { SQL08="$tmp/$v.sql" emit '' "$ex"; if [ "$ex" = FIXED ]; then checks_base; else checks_all; fi; } | duckdb -bail -noheader -list > "$tmp/out" 2>&1; then :; else
      grep -q ': got ' "$tmp/out" || { echo "08_seat_fit_test: mutation $v failed for another reason:"; cat "$tmp/out"; exit 1; }
      bad=1
    fi
  done
  [ $bad = 1 ] || { echo "08_seat_fit_test: mutation $v was not flagged"; exit 1; }
  echo "08_seat_fit_test: mutation $v flagged"
done
for v in c2 lam share asc roles; do
  cmp -s "$tmp/$v.sql" "$here/08_seat_fit.sql" && { echo "08_seat_fit_test: mutation $v changed nothing"; exit 1; }
  if { SQL08="$tmp/$v.sql" emit ''; checks_base; } | duckdb -bail -noheader -list > "$tmp/out" 2>&1; then
    echo "08_seat_fit_test: mutation $v was not flagged"; exit 1
  fi
  grep -q ': got ' "$tmp/out" || { echo "08_seat_fit_test: mutation $v failed for another reason:"; cat "$tmp/out"; exit 1; }
  echo "08_seat_fit_test: mutation $v flagged"
done
echo "08_seat_fit_test: ok"
