#!/bin/sh
# Runs legacy_imo.sql in DuckDB on made-up tables with the real column names and checks the answers (worked out by
# hand from the rows below; DuckDB prints a FLOAT firm ID cast to text as 6694.0, display only).  Prints "legacy_imo_test: ok" or stops at the first failed check.  Run from anywhere.
set -e
here=$(cd "$(dirname "$0")" && pwd)
{
cat <<'SQL'
ATTACH ':memory:' AS ssdb_integration; CREATE SCHEMA ssdb_integration.lr_strategy;
CREATE TABLE ssdb_integration.lr_strategy.s1_old_t (fiscal_yr INTEGER, cbd_id TEXT, firm TEXT, dist_ch TEXT,
  new_dist TEXT, mm_opp DOUBLE, actual_sales_amount DOUBLE, sales_amount DOUBLE);
INSERT INTO ssdb_integration.lr_strategy.s1_old_t VALUES
  (2025, '6', 'RAYMOND JAMES', 'IFA/IMO', 'IFA/IMO', NULL, 7, 8), (2025, '9', 'SOME IMO', 'IMO', 'IMO', NULL, 4, 4),
  (2025, '9', 'SOME IMO', 'IMO', 'IMO', NULL, 1, 1), (2024, '6', 'RAYMOND JAMES', 'IFA/IMO', 'IFA/IMO', NULL, 99, 99);
CREATE TABLE ssdb_integration.lr_strategy.s2_old_t (fiscal_yr INTEGER, cbd_id DOUBLE, firm TEXT, dist_ch TEXT,
  new_dist TEXT, mm_opp DOUBLE, actual_sales_amount DOUBLE, sales_amount DOUBLE);
INSERT INTO ssdb_integration.lr_strategy.s2_old_t VALUES
  (2025, 6694, 'RAYMOND JAMES FINANCIAL SVCS', 'IFA', 'IFA/IMO', 100, NULL, NULL),
  (2025, 6694, 'RAYMOND JAMES FINANCIAL SVCS', 'IFA', 'IFA/IMO', 0, 10, 10),
  (2025, 100, 'ALPHA', 'IFA', 'IFA', 50, 5, NULL), (2025, 200, 'BETA', 'FI', 'FI/IMO', 0, 3, 3);
CREATE TABLE ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys (fiscal_yr INTEGER, source TEXT,
  cbd_id TEXT, dist_ch TEXT, new_dist TEXT, channel TEXT, mm_opp DOUBLE, actual_sales_amount DOUBLE,
  sales_amount DOUBLE, sales_wholesaler_territory_id TEXT, territory_wholesaler_territory_id TEXT);
INSERT INTO ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys VALUES
  (2025, 'F2', '6694', 'IFA', 'IFA/IMO', 'IFA/IMO', 0, 10, 10, 'A', NULL),
  (2025, 'F2', '100', 'IFA', 'IFA', 'IFA', 50, 5, 0, 'B', 'A'),
  (2025, 'F1', '6', 'IFA/IMO', 'IFA/IMO', 'IFA/IMO', 0, 7, 8, 'C', NULL),
  (2025, 'F1', '7', 'FI/IMO', 'FI/IMO', 'FI/IMO', 0, 3, 3, NULL, NULL),
  (2025, 'F1', '8', 'FI', 'FI', 'FI', 9, 0, 0, NULL, 'D'), (2025, 'F1', '8', 'WH', 'WH', 'WH', 9, 0, 0, NULL, 'D'),
  (2025, 'F1', '6', 'IFA/IMO', 'IFA/IMO', 'IFA/IMO', 0, 2, 2, 'D', NULL),
  (2025, 'F1', '6', 'IFA/IMO', 'IFA/IMO', 'IFA/IMO', 0, 0, 0, 'C', NULL);
SQL
sed -e '/^use /d' -e '/^SET s[12]_old/d' \
    -e 's/IDENTIFIER(\$s1_old)/ssdb_integration.lr_strategy.s1_old_t/' \
    -e 's/IDENTIFIER(\$s2_old)/ssdb_integration.lr_strategy.s2_old_t/' \
    -e 's/^WITH$/CREATE TABLE res AS WITH/' -e 's/^ORDER BY part.*;$/;/' "$here/legacy_imo.sql"
cat <<'SQL'
CREATE MACRO chk(name, got, want) AS CASE WHEN got IS NOT DISTINCT FROM want THEN 'ok'
  ELSE error(name || ': got ' || COALESCE(CAST(got AS VARCHAR), 'NULL') || ', want ' || CAST(want AS VARCHAR)) END;
CREATE MACRO p(pt) AS (SELECT string_agg(source || '|' || COALESCE(dist_ch, '-') || '>' || COALESCE(new_dist, '-') || '|'
  || COALESCE(channel, '-') || '|' || item || '|' || COALESCE(cbd_id, '-') || '|' || n_rows || '/' || n_firms || '|'
  || CAST(mm_opp AS INTEGER) || '/' || CAST(actual_sales_amount AS INTEGER) || '/' || CAST(sales_amount AS INTEGER),
  ', ' ORDER BY source, dist_ch, new_dist, item, cbd_id) FROM res WHERE part = pt);
SELECT
 chk('map: by row type, fiscal year 2025 only, firms counted', p('MAP'),
     'S1|IFA/IMO>IFA/IMO|-|SALES ONLY|-|1/1|0/7/8, S1|IMO>IMO|-|SALES ONLY|-|2/1|0/5/5, S2|FI>FI/IMO|-|SALES ONLY|-|1/1|0/3/3, S2|IFA>IFA|-|BOTH|-|1/1|50/5/0, S2|IFA>IFA/IMO|-|OPPORTUNITY ONLY|-|1/1|100/0/0, S2|IFA>IFA/IMO|-|SALES ONLY|-|1/1|0/10/10'),
 chk('firms: firm 2''s IMO labels and either firm''s Raymond James, not firm 1''s other IMO firms', p('IMO AND RAYMOND JAMES FIRMS'),
     'S1|IFA/IMO>IFA/IMO|-|SALES ONLY|6|1/1|0/7/8, S2|FI>FI/IMO|-|SALES ONLY|200.0|1/1|0/3/3, S2|IFA>IFA/IMO|-|OPPORTUNITY ONLY|6694.0|1/1|100/0/0, S2|IFA>IFA/IMO|-|SALES ONLY|6694.0|1/1|0/10/10'),
 chk('sellers: the seller''s territory channels from TERRITORY_WHOLESALER_TERRITORY_ID; rows with sales only', p('IMO SELLERS'' TERRITORIES'),
     'F1|FI/IMO>FI/IMO|FI/IMO|NO SELLER ID|-|1/1|0/3/3, F1|IFA/IMO>IFA/IMO|IFA/IMO|SELLER HOLDS NO TERRITORY|-|1/1|0/7/8, F1|IFA/IMO>IFA/IMO|IFA/IMO|SELLER HOLDS: FI .. WH|-|1/1|0/2/2, F2|IFA>IFA/IMO|IFA/IMO|SELLER HOLDS: IFA|-|1/1|0/10/10');
SELECT 'legacy_imo_test: ok';
SQL
} | duckdb -bail -noheader -list
