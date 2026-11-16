#!/bin/sh
# Runs maps_profile.sql in DuckDB on made-up UNION, TERRITORIES and ZCTA tables (the real column names) and checks every
# section against answers worked out by hand from the rows below.  Prints "maps_profile_test: ok" or stops at the first
# failed check.  Run from anywhere: sh maps_profile_test.sh
set -e
here=$(cd "$(dirname "$0")" && pwd)
{
cat <<'SQL'
ATTACH ':memory:' AS ssdb_integration; CREATE SCHEMA ssdb_integration.lr_strategy;
CREATE TABLE ssdb_integration.lr_strategy.zcta_t (geo_id TEXT, fully_qualified_id TEXT, geo_name TEXT, geo_boundary TEXT);
INSERT INTO ssdb_integration.lr_strategy.zcta_t (geo_id) VALUES ('02134'), ('02135'), ('02136'), ('02137'), ('02138');
CREATE TABLE ssdb_integration.lr_strategy.terr_t (source TEXT, name TEXT, zip_code TEXT, state TEXT, channel TEXT,
  clean_name TEXT, clean_id TEXT);
INSERT INTO ssdb_integration.lr_strategy.terr_t (source, name, zip_code, channel) VALUES
  -- A, firm 1's codes.  02134: Ann holds WH and FI.  02135: Bob WH, Cy FI.  02136: Bob WH, FI vacant.
  -- 02137: FI on two holders, no WH.  99999: IFA, not a ZCTA, a comma in the name.
  ('A','Ann Lee','2134','WH'), ('A','Ann Lee','02134','FI'),
  ('A','Bob Ray','02135','WH'), ('A','Cy Doe','02135','FI'),
  ('A','Bob Ray','02136','WH'), ('A','Open','02136','FI'),
  ('A','Cy Doe','02137','FI'), ('A','Dee Poe','02137','fi'),
  ('A','Eve, Fox','99999','IFA'),
  -- B, firm 2's codes (BD = WH, BK = FI).  Ann again, another case and spacing.
  ('B','ann  lee','02134','BD'), ('B','Gil Hu','02134','BK');
CREATE TABLE ssdb_integration.lr_strategy.union_t (fiscal_yr INTEGER, source TEXT, old_terr_wholesaler TEXT,
  sales_wholesaler TEXT, terr_wholesaler_clean_name TEXT, sales_wholesaler_clean_name TEXT, dist_ch TEXT, new_dist TEXT,
  channel TEXT, state TEXT, zip_code TEXT, product_v2 TEXT, mm_opp DOUBLE, actual_sales_amount DOUBLE, sales_amount DOUBLE,
  sales_wholesaler_territory_id TEXT, sales_wholesaler_address_id TEXT, territory_wholesaler_territory_id TEXT,
  territory_wholesaler_address_id TEXT, sales_wholesaler_has_territory INTEGER, territory_wholesaler_has_territory INTEGER,
  firm_override BOOLEAN, row_origin TEXT, file_new_dist TEXT, channel_rule TEXT, n_holders INTEGER, firm_key TEXT,
  firm_crd TEXT, crd_rule TEXT, opp_override TEXT, firm TEXT, cbd_id TEXT, new_terr_wholesaler TEXT,
  new_terr_channel TEXT, parent TEXT);
INSERT INTO ssdb_integration.lr_strategy.union_t (fiscal_yr, source, old_terr_wholesaler, sales_wholesaler, zip_code,
  product_v2, dist_ch, new_dist, channel, mm_opp, actual_sales_amount, firm, cbd_id) VALUES
  -- 1, 12: one WH cell on two holder rows (100 once).  Bob does not hold 02134: a union holder not in territories
  (2025,'A','Ann Lee',NULL,'2134','VA','WH','WH','WH',100,0,'FIRMNAME1','c1'),
  (2025,'A','Bob Ray',NULL,'02134','VA','WH','WH','WH',100,0,'FIRMNAME1','c1'),
  -- 2: Wells WH sits with the WH holder.  3: National (Chase) with the FI holder, and a sale by Ann in her own ZIP (10)
  (2025,'A','Ann Lee',NULL,'02134','VA','WH','Wells WH','National',40,0,'FIRMNAME2','c2'),
  (2025,'A','Ann Lee','ann lee','02134','VA','FI','National (Chase)','National',30,10,'FIRMNAME3','c3'),
  -- 4: Bob's WH.  5: FI under a name the territories do not have, who also sold (20)
  (2025,'A','Bob Ray',NULL,'02135','VA','WH','WH','WH',50,0,'FIRMNAME1','c1'),
  (2025,'A','Zed Unk','Zed Unk','02135','VA','FI','FI','FI',60,20,'FIRMNAME1','c1'),
  -- 6: Wells FI where FI is vacant, a sale with no seller (5)
  (2025,'A','open',NULL,'02136','VA','FI','Wells FI','National',70,5,'FIRMNAME2','c2'),
  -- 7: FI under one of the ZIP's two holders.  7b: Wells FI there with no union holder
  (2025,'A','Cy Doe',NULL,'02137','VA','FI','FI','FI',80,0,'FIRMNAME1','c1'),
  (2025,'A',NULL,NULL,'02137','VA','FI','Wells FI','National',9,0,'FIRMNAME2','c2'),
  -- 8: no DIST_CH, nobody.  8b: a union holder where the territories have no row
  (2025,'A',NULL,NULL,'02138','VA',NULL,'FI','FI',15,0,'FIRMNAME1','c1'),
  (2025,'A','Bob Ray',NULL,'02138','VA','WH','WH','WH',7,0,'FIRMNAME1','c1'),
  -- 9, 10: sales-only rows: Bob sells outside his ZIPs (30), Ann in a ZIP that is not one (25)
  (2025,'A','Ann Lee','Bob Ray','02134','VA','WH','WH','WH',0,30,'FIRMNAME1','c1'),
  (2025,'A',NULL,'Ann Lee','ABC','VA','WH','WH','WH',NULL,25,'FIRMNAME1','c1'),
  -- 11: IFA in a ZIP that is not a ZCTA, sold by its holder (10)
  (2025,'A','Eve, Fox','Eve,  Fox','99999','VA','IFA','IFA','IFA',5,10,'FIRMNAME1','c1'),
  -- B: Ann's BD is WH, and DIST_CH written as firm 2's own code still finds its holder
  (2025,'B','Ann Lee','Ann Lee','02134','VA','WH','WH','WH',200,100,'FIRMNAME1','c1'),
  (2025,'B','Gil Hu',NULL,'02134','VA','BK','FI','FI',300,0,'FIRMNAME1','c1');
CREATE TABLE full_result AS
SQL
sed -e 's/REGEXP_LIKE(/regexp_matches(/g' -e "s/\\\\\\\\s+', ' ')/\\\\s+', ' ', 'g')/g" -e '/^use /d' -e '/^SET /d' \
    -e 's/IDENTIFIER(\$union_tbl)/ssdb_integration.lr_strategy.union_t/' \
    -e 's/IDENTIFIER(\$terr_tbl)/ssdb_integration.lr_strategy.terr_t/' \
    -e 's/IDENTIFIER(\$zcta_tbl)/ssdb_integration.lr_strategy.zcta_t/' "$here/maps_profile.sql"
cat <<'SQL'
CREATE MACRO chk(name, got, want) AS CASE WHEN got IS NOT DISTINCT FROM want THEN 'ok'
  ELSE error(name || ': got ' || COALESCE(CAST(got AS VARCHAR), 'NULL') || ', want ' || CAST(want AS VARCHAR)) END;
-- a section as one string: SOURCE|K1|K2|K3|K4|N|N2|MM_OPP|PCT, '-' for NULL
CREATE MACRO sec(s) AS (SELECT string_agg(concat_ws('|', COALESCE(source, '-'), COALESCE(k1, '-'), COALESCE(k2, '-'), COALESCE(k3, '-'),
    COALESCE(k4, '-'), COALESCE(CAST(n AS VARCHAR), '-'), COALESCE(CAST(n2 AS VARCHAR), '-'), COALESCE(CAST(CAST(mm_opp AS BIGINT) AS VARCHAR), '-'),
    COALESCE(CAST(CAST(round(pct) AS BIGINT) AS VARCHAR), '-')), ' / ' ORDER BY source, k1, k2, k3, k4) FROM full_result WHERE section = s);
SELECT
 chk('columns', (SELECT string_agg(column_name, ',' ORDER BY column_index) FROM duckdb_columns() WHERE table_name = 'full_result'),
     'section,source,k1,k2,k3,k4,n,n2,mm_opp,pct'),
 chk('01: a cell once whatever its holder rows, sales rows and percent by the sale''s channels', sec('01 UNION CHANNELS'),
     'A||FI|FI|-|1|0|15|- / A|FI|FI|FI|-|2|1|140|20 / A|FI|NATIONAL (CHASE)|National|-|1|1|30|10 / A|FI|WELLS FI|National|-|2|1|79|5'
     || ' / A|IFA|IFA|IFA|-|1|1|5|10 / A|WH|WELLS WH|National|-|1|0|40|- / A|WH|WH|WH|-|3|2|157|55'
     || ' / B|BK|FI|FI|-|1|0|300|- / B|WH|WH|WH|-|1|1|200|100'),
 chk('02', sec('02 TERR CHANNELS'),
     'A|FI|HOLDERS|-|-|3|-|-|- / A|FI|OPEN OR NO NAME ROWS|-|-|1|-|-|- / A|FI|ROWS|-|-|5|-|-|- / A|FI|ZIPS|-|-|4|-|-|- / A|FI|ZIPS NOT A ZCTA|-|-|0|-|-|-'
     || ' / A|IFA|HOLDERS|-|-|1|-|-|- / A|IFA|OPEN OR NO NAME ROWS|-|-|0|-|-|- / A|IFA|ROWS|-|-|1|-|-|- / A|IFA|ZIPS|-|-|1|-|-|- / A|IFA|ZIPS NOT A ZCTA|-|-|1|-|-|-'
     || ' / A|WH|HOLDERS|-|-|2|-|-|- / A|WH|OPEN OR NO NAME ROWS|-|-|0|-|-|- / A|WH|ROWS|-|-|3|-|-|- / A|WH|ZIPS|-|-|3|-|-|- / A|WH|ZIPS NOT A ZCTA|-|-|0|-|-|-'
     || ' / B|BD|HOLDERS|-|-|1|-|-|- / B|BD|OPEN OR NO NAME ROWS|-|-|0|-|-|- / B|BD|ROWS|-|-|1|-|-|- / B|BD|ZIPS|-|-|1|-|-|- / B|BD|ZIPS NOT A ZCTA|-|-|0|-|-|-'
     || ' / B|BK|HOLDERS|-|-|1|-|-|- / B|BK|OPEN OR NO NAME ROWS|-|-|0|-|-|- / B|BK|ROWS|-|-|1|-|-|- / B|BK|ZIPS|-|-|1|-|-|- / B|BK|ZIPS NOT A ZCTA|-|-|0|-|-|-'),
 chk('03: a vacant ZIP is 0 holders', sec('03 TERR HOLDERS PER ZIP'),
     'A|FI|0|-|-|1|-|-|- / A|FI|1|-|-|2|-|-|- / A|FI|2|-|-|1|-|-|- / A|IFA|1|-|-|1|-|-|- / A|WH|1|-|-|3|-|-|- / B|BD|1|-|-|1|-|-|- / B|BK|1|-|-|1|-|-|-'),
 chk('04: firm 2 codes in firm 1''s names', sec('04 HOLDER CHANNEL SETS'),
     'A|FI|-|-|-|2|3|-|- / A|IFA|-|-|-|1|1|-|- / A|WH|-|-|-|1|2|-|- / A|WH FI|-|-|-|1|2|-|- / B|FI|-|-|-|1|1|-|- / B|WH|-|-|-|1|1|-|-'),
 chk('05: the five fine channels'' opportunity by who holds WH and FI', sec('05 WH AND FI AT A ZIP'),
     'A|BOTH HELD, DIFFERENT HOLDERS|-|-|-|1|-|110|- / A|BOTH HELD, THE SAME HOLDER(S)|-|-|-|1|-|170|- / A|FI HELD, WH NOT|-|-|-|1|-|89|-'
     || ' / A|NEITHER HELD (OPPORTUNITY ONLY)|-|-|-|1|-|22|- / A|WH HELD, FI NOT|-|-|-|1|-|70|- / B|BOTH HELD, DIFFERENT HOLDERS|-|-|-|1|-|500|-'),
 chk('06: each cell by the holders of its fallback channel on the ZIP (Wells WH with WH, Wells FI and National (Chase) with FI)', sec('06 FINE CHANNEL HOLDER'),
     'A|FI|||NO TERRITORY ROW|1|-|15|- / A|FI|FI|FI|1 HOLDER|1|-|60|- / A|FI|FI|FI|2+ HOLDERS|1|-|80|-'
     || ' / A|IFA|IFA|IFA|1 HOLDER|1|-|5|- / A|NATIONAL (CHASE)|FI|FI|1 HOLDER|1|-|30|- / A|WELLS FI|FI|FI|2+ HOLDERS|1|-|9|-'
     || ' / A|WELLS FI|FI|FI|OPEN OR NO NAME ONLY|1|-|70|- / A|WELLS WH|WH|WH|1 HOLDER|1|-|40|- / A|WH|WH|WH|1 HOLDER|2|-|150|-'
     || ' / A|WH|WH|WH|NO TERRITORY ROW|1|-|7|- / B|FI|BK|FI|1 HOLDER|1|-|300|- / B|WH|WH|WH|1 HOLDER|1|-|200|-'),
 chk('07: the union''s old holder against the territories'' holders of ZIP x DIST_CH, every class', sec('07 UNION HOLDER VS TERR'),
     'A||NO HOLDER IN EITHER|-|-|1|-|15|- / A|FI|A UNION HOLDER NOT IN TERRITORIES|-|-|1|-|60|- / A|FI|NO HOLDER IN EITHER|-|-|1|-|70|-'
     || ' / A|FI|TERRITORIES ONLY|-|-|1|-|9|- / A|FI|THE SAME HOLDER(S)|-|-|1|-|30|- / A|FI|UNION HAS FEWER, ALL IN TERRITORIES|-|-|1|-|80|-'
     || ' / A|IFA|THE SAME HOLDER(S)|-|-|1|-|5|- / A|WH|A UNION HOLDER NOT IN TERRITORIES|-|-|1|-|100|- / A|WH|THE SAME HOLDER(S)|-|-|2|-|90|-'
     || ' / A|WH|UNION ONLY|-|-|1|-|7|- / B|BK|THE SAME HOLDER(S)|-|-|1|-|300|- / B|WH|THE SAME HOLDER(S)|-|-|1|-|200|-'),
 chk('08: ZIPs held in one source or both, a vacancy is not held', sec('08 CROSS-FIRM'),
     '-|FI|2 SOURCES|-|-|1|-|-|- / -|FI|A ONLY|-|-|2|-|-|- / -|IFA|A ONLY|-|-|1|-|-|- / -|WH|2 SOURCES|-|-|1|-|-|- / -|WH|A ONLY|-|-|2|-|-|-'),
 chk('09: sales rows by ZIP, seller and whether the seller holds the ZIP, percent of the source''s sales', sec('09 SALES ROWS'),
     'A|ZIP IS A ZCTA|NO SELLER (BLANK OR OPEN)|-|-|1|-|-|5 / A|ZIP IS A ZCTA|SELLER HOLDS A TERRITORY|SALE IN A ZIP THE SELLER HOLDS|-|1|-|-|10'
     || ' / A|ZIP IS A ZCTA|SELLER HOLDS A TERRITORY|SALE OUTSIDE THE SELLER''S ZIPS|-|1|-|-|30 / A|ZIP IS A ZCTA|SELLER HOLDS NO TERRITORY|-|-|1|-|-|20'
     || ' / A|ZIP NOT 5 DIGITS|SELLER HOLDS A TERRITORY|SALE OUTSIDE THE SELLER''S ZIPS|-|1|-|-|25 / A|ZIP NOT A ZCTA|SELLER HOLDS A TERRITORY|SALE IN A ZIP THE SELLER HOLDS|-|1|-|-|10'
     || ' / B|ZIP IS A ZCTA|SELLER HOLDS A TERRITORY|SALE IN A ZIP THE SELLER HOLDS|-|1|-|-|100'),
 chk('10: names only counted', sec('10 NAMES'),
     'A|TERR HOLDERS|-|-|-|5|-|-|- / A|TERR HOLDERS ALSO A HOLDER IN ANOTHER SOURCE|-|-|-|1|-|-|- / A|TERR HOLDERS WITH A COMMA IN THE NAME|-|-|-|1|-|-|-'
     || ' / A|UNION OLD HOLDERS|-|-|-|5|-|-|- / A|UNION OLD HOLDERS NOT A TERR HOLDER|-|-|-|1|-|-|- / A|UNION OLD HOLDERS WITH A COMMA IN THE NAME|-|-|-|1|-|-|-'
     || ' / A|UNION SELLERS|-|-|-|4|-|-|- / A|UNION SELLERS NOT A TERR HOLDER|-|-|-|1|-|-|- / A|UNION SELLERS WITH A COMMA IN THE NAME|-|-|-|1|-|-|-'
     || ' / B|TERR HOLDERS|-|-|-|2|-|-|- / B|TERR HOLDERS ALSO A HOLDER IN ANOTHER SOURCE|-|-|-|1|-|-|- / B|TERR HOLDERS WITH A COMMA IN THE NAME|-|-|-|0|-|-|-'
     || ' / B|UNION OLD HOLDERS|-|-|-|2|-|-|- / B|UNION OLD HOLDERS NOT A TERR HOLDER|-|-|-|0|-|-|- / B|UNION OLD HOLDERS WITH A COMMA IN THE NAME|-|-|-|0|-|-|-'
     || ' / B|UNION SELLERS|-|-|-|1|-|-|- / B|UNION SELLERS NOT A TERR HOLDER|-|-|-|0|-|-|- / B|UNION SELLERS WITH A COMMA IN THE NAME|-|-|-|0|-|-|-'),
 chk('no wholesaler or firm name anywhere in the result',
     (SELECT COUNT(*) FROM full_result f WHERE regexp_matches(CAST(f AS VARCHAR), 'ann +lee|bob ray|cy doe|dee poe|eve, *fox|gil hu|zed unk|firmname', 'i')), 0),
 chk('opportunity ties: section 01 = 06 = 07 per source',
     (SELECT string_agg(source || ':' || CAST(CAST(o AS BIGINT) AS VARCHAR), ' ' ORDER BY section, source)
      FROM (SELECT section, source, SUM(mm_opp) AS o FROM full_result WHERE section LIKE '01%' OR section LIKE '06%' OR section LIKE '07%' GROUP BY section, source)),
     'A:466 B:500 A:466 B:500 A:466 B:500');
SELECT 'maps_profile_test: ok';
SQL
} | duckdb -bail -noheader -list
