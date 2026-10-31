#!/bin/sh
# Runs 01_opportunity_sales.sql, then transfers.sql, in DuckDB on 02_sales_test.sh's made-up tables (its fixture block,
# read from that file), and checks transfers.sql's result set, its own last statement: the transfers equal the
# cell-level old -> new wholesaler of TMP_O1_DATASET, the books net to 0, and hand-worked values.
# Prints "transfers_test: ok" or stops at the first failed check.  Run from anywhere: sh transfers_test.sh
set -e
here=$(cd "$(dirname "$0")" && pwd)
top=$(cd "$here/.." && pwd)
{
awk '/^cat <<.SQL.$/ && !s {s=1; next} s && /^SQL$/ {exit} s' "$top/02_sales_test.sh"
cat <<'SQL'
-- this test's own row: a blank-channel cell of firm 1's IFA firm at a ZIP x product where it also has an IFA cell
INSERT INTO life_prod.lif_murkylake.wc_market_metrics_opportunity VALUES
  ('2025','Q4','10',NULL,'100','Alpha','','01','IA','-77777','02134',15);
SQL
sed -e '/^use secondary roles all;$/d' -e '/^SET s[12]_/d' -e 's/TEMPORARY TABLE/TABLE/' \
    -e 's/IDENTIFIER(\$s1_territories)/ssdb_integration.lr_strategy.s1_terr_t/g' \
    -e 's/IDENTIFIER(\$s2_opp)/ssdb_integration.lr_strategy.s2_opp_t/g' \
    -e 's/IDENTIFIER(\$s2_territories)/ssdb_integration.lr_strategy.s2_terr_t/g' \
    -e 's/IDENTIFIER(\$s1_sales)/ssdb_integration.lr_strategy.s1_sales_t/g' \
    -e 's/IDENTIFIER(\$s2_sales)/ssdb_integration.lr_strategy.s2_sales_t/g' \
    -e '/^--15\./,$d' "$top/01_opportunity_sales.sql"
sed -e '/^use secondary roles all;$/d' -e 's/TEMPORARY TABLE/TABLE/' \
    -e 's/^SELECT \* FROM ssdb_integration.lr_strategy.tmp_xfer_moves$/CREATE TABLE r AS SELECT * FROM ssdb_integration.lr_strategy.tmp_xfer_moves/' \
    "$here/transfers.sql"
cat <<'SQL'
CREATE TABLE truth AS
SELECT source, CASE WHEN source = 'S1' THEN TRIM(old_wholesaler_id) ELSE UPPER(TRIM(old_wholesaler)) END AS f,
       CASE WHEN source = 'S1' THEN TRIM(new_wholesaler_id) ELSE UPPER(TRIM(new_wholesaler)) END AS t,
       COALESCE(old_channel_s1, '(BLANK)') AS oc, new_channel AS nc, CAST(SUM(opportunity) AS DOUBLE) AS o
FROM ssdb_integration.lr_strategy.tmp_o1_dataset
GROUP BY ALL;
CREATE TABLE moved AS SELECT source, wholesaler_key AS f, to_key AS t, old_channel_s1 AS oc, new_channel AS nc,
  SUM(opp) AS o FROM r WHERE part = 'TRANSFERS' GROUP BY ALL;
CREATE MACRO chk(name, got, want) AS CASE WHEN got IS NOT DISTINCT FROM want THEN 'ok'
  ELSE error(name || ': got ' || COALESCE(CAST(got AS VARCHAR), 'NULL') || ', want ' || CAST(want AS VARCHAR)) END;
SELECT
 chk('transfers = the cells that change hands', (SELECT COUNT(*) FROM (
   (SELECT * FROM moved EXCEPT SELECT * FROM truth WHERE f IS DISTINCT FROM t)
   UNION ALL (SELECT * FROM truth WHERE f IS DISTINCT FROM t EXCEPT SELECT * FROM moved)) x), 0),
 chk('a firm 2 move: REGIONAL (WH) firm routed IFA', (SELECT wholesaler || '>' || to_wholesaler || ' ' || old_channel_s1 || '>' || new_channel || ' ' || cells || ' ' || CAST(opp AS INTEGER) FROM r WHERE part = 'TRANSFERS' AND source = 'S2'), 'R2>R1 WH>IFA 1 30'),
 chk('a firm 1 move from no holder, beside a same-key cell of another old channel', (SELECT wholesaler || '>' || to_wholesaler || ' ' || old_channel_s1 || '>' || new_channel || ' ' || cells || ' ' || CAST(opp AS INTEGER) FROM r WHERE part = 'TRANSFERS' AND source = 'S1'), '(NO HOLDER)>N1 (BLANK)>IFA 1 15'),
 chk('books net to 0', (SELECT string_agg(source || '=' || CAST(n AS INTEGER), ' ' ORDER BY source) FROM (SELECT source, SUM(change) AS n FROM r WHERE part = 'BOOKS' GROUP BY ALL) x), 'S1=0 S2=0'),
 chk('books total = opportunity', (SELECT CAST(SUM(old_book) AS INTEGER) || ' ' || CAST(SUM(new_book) AS INTEGER) FROM r WHERE part = 'BOOKS'), (SELECT CAST(SUM(opportunity) AS INTEGER) || ' ' || CAST(SUM(opportunity) AS INTEGER) FROM ssdb_integration.lr_strategy.tmp_o1_dataset)),
 chk('a book: the giver loses, sales stay', (SELECT CAST(old_book AS INTEGER) || ' ' || CAST(new_book AS INTEGER) || ' ' || CAST(sales AS INTEGER) FROM r WHERE part = 'BOOKS' AND source = 'S2' AND wholesaler_key = 'R2'), '30 0 6'),
 chk('a book: the receiver gains', (SELECT CAST(change AS INTEGER) FROM r WHERE part = 'BOOKS' AND source = 'S2' AND wholesaler_key = 'R1'), 30),
 chk('books: sales total', (SELECT CAST(SUM(sales) AS INTEGER) FROM r WHERE part = 'BOOKS'), (SELECT CAST(SUM(sales) AS INTEGER) FROM ssdb_integration.lr_strategy.tmp_o2_dataset)),
 chk('no renamed duplicate column', (SELECT COUNT(*) FROM duckdb_columns() WHERE table_name IN ('r', 'tmp_xfer_moves', 'tmp_xfer_books') AND regexp_matches(column_name, '_[0-9]+$')), 0);
SELECT 'transfers_test: ok';
SQL
} | duckdb -bail -noheader -list
