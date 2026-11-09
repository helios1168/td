#!/bin/sh
# Runs 02_model_extract.sql in DuckDB on made-up UNION and TERRITORIES tables (the real column names) and checks the answers
# (worked out by hand from the rows below): a cell repeated on 2 holder rows counts once, a sales-only row adds nothing,
# an unequal repeat shows in the MUST_BE_ZERO check, two sources stay apart, TERR surrogates are stable and carry no
# CLEAN_ID or name.  The script then runs a second time on the same database after one holder is added and one removed:
# survivors keep their number, the new one gets max + 1, the removed number is not reused.  Prints "02_model_extract_test: ok" or stops at the first failed check.
# Run from anywhere: sh 02_model_extract_test.sh
set -e
here=$(cd "$(dirname "$0")" && pwd)
# the script as DuckDB runs it, into a fresh full_result
emit_sql() {
echo 'DROP TABLE IF EXISTS full_result;'
# DuckDB has no REGEXP_LIKE (Snowflake's full match): regexp_matches, the pattern anchored in the file
# and no CURRENT_TIMESTAMP() or TIMESTAMP_NTZ
sed -e 's/REGEXP_LIKE(/regexp_matches(/g' -e '/^use /d' -e '/^SET /d' -e 's/^WITH$/CREATE TABLE full_result AS WITH/' \
    -e 's/CURRENT_TIMESTAMP()/now()/' -e 's/TIMESTAMP_NTZ/TIMESTAMP/' \
    -e 's/IDENTIFIER(\$union_tbl)/ssdb_integration.lr_strategy.union_t/' \
    -e 's/IDENTIFIER(\$terr_tbl)/ssdb_integration.lr_strategy.terr_t/' \
    -e 's/IDENTIFIER(\$holder_tbl)/ssdb_integration.lr_strategy.holder_key/' "$here/02_model_extract.sql"
}
{
cat <<'SQL'
ATTACH ':memory:' AS ssdb_integration; CREATE SCHEMA ssdb_integration.lr_strategy;
CREATE TABLE ssdb_integration.lr_strategy.union_t (fiscal_yr INTEGER, source TEXT, old_terr_wholesaler TEXT,
  sales_wholesaler TEXT, terr_wholesaler_clean_name TEXT, sales_wholesaler_clean_name TEXT, dist_ch TEXT, new_dist TEXT,
  channel TEXT, state TEXT, zip_code TEXT, product_v2 TEXT, mm_opp DOUBLE, actual_sales_amount DOUBLE, sales_amount DOUBLE,
  sales_wholesaler_territory_id TEXT, sales_wholesaler_address_id TEXT, territory_wholesaler_territory_id TEXT,
  territory_wholesaler_address_id TEXT, sales_wholesaler_has_territory INTEGER, territory_wholesaler_has_territory INTEGER,
  firm_override BOOLEAN, row_origin TEXT, file_new_dist TEXT, channel_rule TEXT, n_holders INTEGER, firm_key TEXT,
  firm_crd TEXT, crd_rule TEXT, opp_override TEXT, firm TEXT, cbd_id TEXT, new_terr_wholesaler TEXT,
  new_terr_channel TEXT, parent TEXT);
-- columns: fiscal_yr, source, holder, sales holder, zip, product, dist_ch, new_dist, channel, mm_opp, sales, n_holders, firm, cbd_id
CREATE TEMP TABLE seed (fy INTEGER, src TEXT, wh TEXT, swh TEXT, zip TEXT, prod TEXT, dc TEXT, nd TEXT, ch TEXT,
  opp DOUBLE, sales DOUBLE, nh INTEGER, frm TEXT, cbd TEXT);
INSERT INTO seed VALUES
  -- one cell on 2 holder rows: counts once (100)
  (2025,'A','WHOLE1','WHOLE1','2134','VA','IFA','IFA','ifa',100,0,2,'FIRMNAME1','c1'),
  (2025,'A','WHOLE2','WHOLE2','2134','VA','IFA','IFA','ifa',100,0,2,'FIRMNAME1','c1'),
  -- a sales-only row (MM_OPP 0) and one with NULL MM_OPP: nothing
  (2025,'A','WHOLE1','WHOLE9','2134','FA','IFA','IFA','ifa',0,50,NULL,'FIRMNAME1','c1'),
  (2025,'A','WHOLE1','WHOLE9','2134','FA','IFA','IFA','ifa',NULL,7,NULL,'FIRMNAME1','c1'),
  -- an unequal repeat: 60 and 70, the cell keeps 70 and the check shows it
  (2025,'A','WHOLE1','WHOLE1','02135','VA','IFA','IFA','ifa',60,0,NULL,'FIRMNAME1','c1'),
  (2025,'A','WHOLE2','WHOLE2','02135','VA','IFA','IFA','ifa',70,0,NULL,'FIRMNAME1','c1'),
  -- a second firm in the same ZIP x channel: sums with the first (125, 2 cells); N_HOLDERS 3 vs 1 repeat
  (2025,'A','WHOLE1','WHOLE1','02134','VA','IFA','IFA','ifa',25,0,3,'FIRMNAME2','c2'),
  -- not a ZIP, NULL channel
  (2025,'A','WHOLE1','WHOLE1','ABC','VA','IFA','IFA',NULL,10,0,NULL,'FIRMNAME2','c2'),
  -- the other source, the same key columns
  (2025,'B','WHOLE1','WHOLE1','02134','VA','IFA','IFA','ifa',40,0,NULL,'FIRMNAME1','c1');
INSERT INTO ssdb_integration.lr_strategy.union_t (fiscal_yr, source, old_terr_wholesaler, sales_wholesaler, dist_ch,
  new_dist, channel, zip_code, product_v2, mm_opp, actual_sales_amount, n_holders, firm, cbd_id)
  SELECT fy, src, wh, swh, dc, nd, ch, zip, prod, opp, sales, nh, frm, cbd FROM seed;
CREATE TABLE ssdb_integration.lr_strategy.terr_t (source TEXT, name TEXT, zip_code TEXT, state TEXT, channel TEXT,
  clean_name TEXT, clean_id TEXT);
INSERT INTO ssdb_integration.lr_strategy.terr_t VALUES
  ('A','Alice Smith','2134','MA','ifa','alice smith','u-2'),
  ('A','Alice Smith','02135','MA','ifa','alice smith','u-2'),
  ('A','Bob Jones','02134','MA','ifa','bob jones','u-1'),
  ('A','Nobody','02136','MA','ifa',NULL,NULL),
  ('B','Cy Doe','02134','MA','ifa','cy doe','u-1'),
  ('C','Dee Roe','02134','MA','ifa','dee roe','u-3');
SQL
emit_sql
cat <<'SQL'
CREATE MACRO chk(name, got, want) AS CASE WHEN got IS NOT DISTINCT FROM want THEN 'ok'
  ELSE error(name || ': got ' || COALESCE(CAST(got AS VARCHAR), 'NULL') || ', want ' || CAST(want AS VARCHAR)) END;
CREATE MACRO c(src, nm) AS (SELECT COALESCE(CAST(CAST(value AS BIGINT) AS VARCHAR), '-') || '/' || COALESCE(CAST(CAST(mm_opp AS BIGINT) AS VARCHAR), '-')
                                   || '/' || COALESCE(CAST(n_cells AS VARCHAR), '-') || '/' || CAST(must_be_zero AS VARCHAR)
                            FROM full_result WHERE layer = 'CHECKS' AND source = src AND name = nm);
SELECT
 chk('one result set: the columns', (SELECT string_agg(column_name, ',' ORDER BY column_index) FROM duckdb_columns() WHERE table_name = 'full_result'),
     'layer,source,name,zip_code,state,dist_ch,new_dist,channel,holder,mm_opp,n_cells,value,must_be_zero'),
 chk('OPP: a repeated cell once, a second firm summed, ZIP padded, sales-only and NULL rows nothing, sources apart',
     (SELECT string_agg(source || '|' || zip_code || '|' || COALESCE(channel, '-') || '|' || CAST(mm_opp AS INTEGER) || '|' || n_cells, ' ' ORDER BY source, zip_code)
      FROM full_result WHERE layer = 'OPP'),
     'A|00ABC|-|10|1 A|02134|ifa|125|2 A|02135|ifa|70|1 B|02134|ifa|40|1'),
 chk('OPP: no firm, CBD_ID or holder columns filled', (SELECT COUNT(*) FROM full_result WHERE layer = 'OPP' AND (name IS NOT NULL OR holder IS NOT NULL OR state IS NOT NULL)), 0),
 chk('checks: raw and dedup', c('A', 'OPP RAW SUM(MM_OPP)') || ' ' || c('A', 'OPP DEDUP (CELLS)'), '-/365/-/0 -/205/4/0'),
 chk('checks: source B raw and dedup', c('B', 'OPP RAW SUM(MM_OPP)') || ' ' || c('B', 'OPP DEDUP (CELLS)'), '-/40/-/0 -/40/1/0'),
 chk('checks: the unequal repeat is MUST_BE_ZERO with its opp; B has none',
     c('A', 'CELL KEYS WITH UNEQUAL POSITIVE MM_OPP, THEIR OPP') || ' ' || c('B', 'CELL KEYS WITH UNEQUAL POSITIVE MM_OPP, THEIR OPP'), '1/70/-/1 0/-/-/1'),
 chk('checks: N_HOLDERS disagrees on one row', c('A', 'ROWS WHERE N_HOLDERS <> REPEAT COUNT OF THE CELL'), '1/-/-/0'),
 chk('checks: ZIP not 5 digits, NULL channel, no blank DIST_CH',
     c('A', 'CELLS WITH ZIP_CODE NOT 5 DIGITS') || ' ' || c('A', 'CELLS WITH NULL OR BLANK CHANNEL') || ' ' || c('A', 'CELLS WITH NULL OR BLANK DIST_CH'),
     '1/10/-/0 1/10/-/0 0/-/-/0'),
 chk('TERR: one surrogate per CLEAN_ID, in SOURCE x CLEAN_ID order, repeated across ZIPs, ZIP padded, NULL CLEAN_ID out',
     (SELECT string_agg(source || '|' || zip_code || '|' || state || '|' || channel || '|' || holder, ' ' ORDER BY source, zip_code, holder)
      FROM full_result WHERE layer = 'TERR'),
     'A|02134|MA|ifa|R1 A|02134|MA|ifa|R2 A|02135|MA|ifa|R2 B|02134|MA|ifa|R3 C|02134|MA|ifa|R4'),
 chk('checks: TERR 2+ holders, NULL CLEAN_ID, a source with no opportunity',
     c('A', 'TERR ZIP X CHANNEL WITH 2+ HOLDERS') || ' ' || c('A', 'TERR ROWS WITH NULL CLEAN_ID') || ' ' || c('C', 'TERR SOURCE WITH NO OPP SOURCE OF THE SAME NAME'),
     '1/-/-/0 1/-/-/0 1/-/-/1'),
 chk('no CLEAN_ID, name, firm or wholesaler anywhere in the result',
     (SELECT COUNT(*) FROM full_result f WHERE regexp_matches(CAST(f AS VARCHAR), 'alice|bob|u-1|u-2|whole|firmname|c1', 'i')), 0),
 chk('MUST_BE_ZERO rows not zero: A unequal and C no opp source, nothing else',
     (SELECT string_agg(source || ':' || name, ' ' ORDER BY source) FROM full_result WHERE layer = 'CHECKS' AND must_be_zero = 1 AND value <> 0),
     'A:CELL KEYS WITH UNEQUAL POSITIVE MM_OPP, THEIR OPP C:TERR SOURCE WITH NO OPP SOURCE OF THE SAME NAME'),
 chk('run 1: the key holds 4 pairs numbered 1..4, all added this run, none missing or duplicated',
     (SELECT string_agg(source || clean_id || '=' || holder_n, ' ' ORDER BY holder_n) FROM ssdb_integration.lr_strategy.holder_key),
     'Au-1=1 Au-2=2 Bu-1=3 Cu-3=4'),
 chk('run 1: key checks', (SELECT string_agg(source || ':' || name || '=' || CAST(value AS BIGINT), ' ' ORDER BY source, name) FROM full_result
                           WHERE layer = 'CHECKS' AND (name LIKE 'KEY %' OR name = 'TERR HOLDERS WITH NO KEY')),
     'A:KEY HOLDER_N DUPLICATED=0 A:KEY ROWS ADDED THIS RUN=2 A:TERR HOLDERS WITH NO KEY=0 B:KEY HOLDER_N DUPLICATED=0 B:KEY ROWS ADDED THIS RUN=1 B:TERR HOLDERS WITH NO KEY=0 C:KEY HOLDER_N DUPLICATED=0 C:KEY ROWS ADDED THIS RUN=1 C:TERR HOLDERS WITH NO KEY=0');
-- run 2 on the same database: Eve is new (her CLEAN_ID sorts before every other, a renumber would shift all), Dee, who held
-- the highest number, leaves
INSERT INTO ssdb_integration.lr_strategy.terr_t VALUES ('A','Eve Fox','02137','MA','ifa','eve fox','u-0');
DELETE FROM ssdb_integration.lr_strategy.terr_t WHERE clean_id = 'u-3';
SQL
emit_sql
cat <<'SQL'
SELECT
 chk('run 2: survivors keep their number, Eve is max + 1, Dee is gone from TERR',
     (SELECT string_agg(source || '|' || zip_code || '|' || holder, ' ' ORDER BY source, zip_code, holder) FROM full_result WHERE layer = 'TERR'),
     'A|02134|R1 A|02134|R2 A|02135|R2 A|02137|R5 B|02134|R3'),
 chk('run 2: the key keeps Dee as 4 and never reuses it', (SELECT string_agg(source || clean_id || '=' || holder_n, ' ' ORDER BY holder_n) FROM ssdb_integration.lr_strategy.holder_key),
     'Au-1=1 Au-2=2 Bu-1=3 Cu-3=4 Au-0=5'),
 chk('run 2: one key row added', (SELECT SUM(value) FROM full_result WHERE name = 'KEY ROWS ADDED THIS RUN'), 1),
 chk('run 2: both key MUST_BE_ZERO checks 0',
     (SELECT SUM(value) FROM full_result WHERE must_be_zero = 1 AND name IN ('TERR HOLDERS WITH NO KEY', 'KEY HOLDER_N DUPLICATED')), 0),
 chk('run 2: no CLEAN_ID or name in the result', (SELECT COUNT(*) FROM full_result f WHERE regexp_matches(CAST(f AS VARCHAR), 'eve|u-0|alice|bob|u-1|u-2|whole|firmname|c1', 'i')), 0);
SELECT '02_model_extract_test: ok';
SQL
} | duckdb -bail -noheader -list
