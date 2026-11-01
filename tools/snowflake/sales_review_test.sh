#!/bin/sh
# Runs all of 01_opportunity_sales.sql in DuckDB on 02_sales_test.sh's made-up tables (its fixture block) plus the rows
# below, with manual assignments put into statement 8, and checks the rules, the manual assignments and the REVIEW
# layer (statements 15-16; answers worked out by hand).
# Prints "sales_review_test: ok" or stops at the first failed check.  Run from anywhere: sh sales_review_test.sh
set -e
here=$(cd "$(dirname "$0")" && pwd)
{
awk '/^cat <<.SQL.$/ && !s {s=1; next} s && /^SQL$/ {exit} s' "$here/02_sales_test.sh"
cat <<'SQL'
-- company 91 named like a market metrics firm and in MM_MAP on it; company 92 whose name and MM_MAP point to different
-- firms; a second LPL IFA sale on code M3 at a ZIP where the other IFA name has opportunity (M3's sales then match two
-- names by ZIP); codes M12, M4, M3 sold at 30301, where both IFA names have opportunity (M4's other sale matched one
-- name by ZIP); the plain LPL name with FIXED opportunity at 10001 (another product); firm 2 'Delta', a CRD not in the
-- market metrics data, named like a firm; Echo with FIXED opportunity at 02134 (no ZIP evidence for an INDEX sale);
-- code M13 at 94105, where the two IFA names have opportunity 9 and 4 (rule 4); company 99, a marketing organization
-- (IMO) named exactly like a market metrics firm; firm 2 'Foxtrot Inc' with no CRD (fuzzy names 93 and 92)
INSERT INTO life_prod.lif_murkylake.wc_market_metrics_opportunity VALUES
  ('2025','Q1','0',NULL,'200','LPL Financial LLC','IFA','01','FA','-77777','10001',5),
  ('2025','Q2','3',NULL,'500','Echo','EDWARD JONES','13','FA','-77777','02134',1),
  ('2025','Q1','0',NULL,'200','LPL Financial LLC - INDEPENDENT','IFA','01','IA','-77777','94105',9),
  ('2025','Q1','0',NULL,'200','LPL Financial LLC','IFA','01','IA','-77777','94105',4),
  ('2025','Q1','0',NULL,'200','LPL Financial LLC - INDEPENDENT','IFA','01','IA','-77777','30301',5),
  ('2025','Q1','0',NULL,'200','LPL Financial LLC','IFA','01','IA','-77777','30301',5);
INSERT INTO ssdb_integration.lr_strategy.s1_sales_t VALUES
  (2025,1,1,'INDEX','IFA','LPL',8,'P','','30301','GA','W6','N6','ALL',1,1,1,'M12'),
  (2025,2,2,'INDEX','IFA','LPL',8,'P','','30301','GA','W6','N6','ALL',1,1,1,'M4'),
  (2025,3,3,'INDEX','IFA','LPL',8,'P','','30301','GA','W6','N6','ALL',1,1,1,'M3'),
  (2025,6,6,'INDEX','WH','Delta',91,'P','','10001','NY','W3','N3','ALL',1,1,1,'M10'),
  (2025,3,3,'INDEX','IFA','Echo',92,'P','','02134','MA','W1','N1','ALL',1,1,1,'M11'),
  (2025,2,2,'INDEX','IFA','LPL',8,'P','','02134','MA','W1','N1','ALL',1,1,1,'M3'),
  (2025,2,2,'INDEX','IFA','LPL',8,'P','','94105','CA','W6','N6','ALL',1,1,1,'M13'),
  (2025,7,7,'INDEX','IMO','Alpha',99,'P','','02134','MA','W1','N1','ALL',1,1,1,'M14');
INSERT INTO ssdb_integration.lr_strategy.mm_map VALUES ('WH',91,11,NULL,'Delta',400), ('IFA',92,1,NULL,'Echo',100);
INSERT INTO ssdb_integration.lr_strategy.s2_sales_t VALUES
  ('P','Delta',999.0,'REGIONAL','NY','A','x','R2','D1',2025,4,4,'10001','IA'),
  ('P','Foxtrot Inc',NULL,'INDEPENDENT','MA','A','x','R1','D1',2025,5,5,'02134','IA');
SQL
manual="  ('S1', '8', 'LPL', 'IFA', 'M12', '200', 'LPL FINANCIAL LLC - INDEPENDENT'), ('S1', '8', 'LPL', 'IFA', NULL, '200', 'LPL FINANCIAL LLC - BANK'), (' s2', '438', ' kilo ', 'independent', NULL, '100 ', 'alpha'), ('S2', '805', 'Kilo', 'INDEPENDENT', NULL, '100', 'ALPHA'), ('S2', '888', 'New', 'BANK', NULL, '100', 'ALPHA'), ('S2', '888', 'New', 'BANK', NULL, '400', 'DELTA'), ('S2', NULL, 'No Crd', 'BANK', NULL, '777', 'NOWHERE'),"
sed -e '/^use /d' -e '/^  -- owner sales channels: begin$/,/^  -- owner sales channels: end$/d' -e '/^  -- owner routes: begin$/,/^  -- owner routes: end$/d' -e '/^  -- owner rows: begin$/,/^  -- owner rows: end$/d' -e '/^SET s[12]_/d' -e 's/TEMPORARY TABLE/TABLE/' \
    -e 's/IDENTIFIER(\$s1_territories)/ssdb_integration.lr_strategy.s1_terr_t/g' \
    -e 's/IDENTIFIER(\$s2_opp)/ssdb_integration.lr_strategy.s2_opp_t/g' \
    -e 's/IDENTIFIER(\$s2_territories)/ssdb_integration.lr_strategy.s2_terr_t/g' \
    -e 's/IDENTIFIER(\$s1_sales)/ssdb_integration.lr_strategy.s1_sales_t/g' \
    -e 's/IDENTIFIER(\$s2_sales)/ssdb_integration.lr_strategy.s2_sales_t/g' \
    -e "s/^  ('', '', '', '', '', '', '')   -- placeholder, keep it last\$/$manual ('', '', '', '', '', '', '')/" \
    -e "s/^  ('', '', '')   -- placeholder, keep it last\$/  ('601', ' foxtrot 2 ', 'ifa'), ('999999', 'NOWHERE', 'IFA'), ('300', 'CHARLIE', 'IFA'), ('300', 'CHARLIE', 'IFA\/IMO'), ('', '', '')/" \
    -e "s/^  ('', '', '', '', '', '')   -- placeholder, keep it last\$/  ('s1', '8', 'lpl', 'ifa', 'm12', 'ifa\/imo'), ('S1', '8', 'LPL', 'IFA', NULL, 'IFA\/IMO'), ('S1', '8', 'LPL', 'IFA', NULL, 'FI\/IMO'), ('S1', '8', 'LPL', 'IFA', 'M4', 'FI\/IMO'), ('S1', '77', 'NEW BD', 'IFA', 'M8', 'IMO'), ('', '', '', '', '', '')/" \
    -e "s/^SELECT 'REVIEW' AS layer,/CREATE TABLE full_result AS SELECT 'REVIEW' AS layer,/" \
    "$here/01_opportunity_sales.sql"
cat <<'SQL'
CREATE MACRO chk(name, got, want) AS CASE WHEN got IS NOT DISTINCT FROM want THEN 'ok'
  ELSE error(name || ': got ' || COALESCE(CAST(got AS VARCHAR), 'NULL') || ', want ' || CAST(want AS VARCHAR)) END;
CREATE MACRO sl(src, f, m, z) AS (SELECT firm_basis || ' ' || COALESCE(broker_name, '-') || ' ' || new_channel
  FROM ssdb_integration.lr_strategy.tmp_o2_sales WHERE source = src AND sales_firm = f
  AND mga_agent_cd IS NOT DISTINCT FROM m AND zip IS NOT DISTINCT FROM z);
CREATE MACRO ev(src, f) AS (SELECT top_wholesaler || ' ' || n_candidates || ' ' || ev_company || ' ' || ev_channel || ' '
  || ev_mm_map || ' ' || ev_crd_to_cbd || ' ' || CAST(ev_name * 100 AS INTEGER) || ' ' || CAST(zip_amt AS INTEGER) || ' ' || CAST(score * 100 AS INTEGER)
  FROM full_result WHERE layer = 'REVIEW' AND part = 'REVIEW' AND source = src AND sales_firm = f AND rank_in_key = 1);
SELECT
 chk('manual: a row with the code beats any code; its sales channel, firm and route unchanged', sl('S1', 'LPL', 'M12', '30301'), 'MANUAL LPL FINANCIAL LLC - INDEPENDENT IFA/IMO'),
 chk('sales channel: a sale with no firm set to IMO, out of the review', (SELECT new_channel || ' ' || firm_basis FROM ssdb_integration.lr_strategy.tmp_o2_sales WHERE source = 'S1' AND sales_firm_id = '77') || ' ' || (SELECT is_imo FROM ssdb_integration.lr_strategy.tmp_sales_review WHERE source = 'S1' AND sales_firm_id = '77'), 'IMO NO MARKET METRICS FIRM true'),
 chk('sales channel: a key on 2+ channels is not applied', sl('S1', 'LPL', 'M3', '30301'), 'MANUAL LPL FINANCIAL LLC - BANK FI'),
 chk('sales channel: only on MANUAL sales', sl('S1', 'LPL', 'M4', '30301'), 'SPLIT, MATCHED BY MGA CODE LPL FINANCIAL LLC IFA'),
 chk('sales channel: the new-channel part shows it, opportunity keeps none', (SELECT CAST(SUM(amt) AS INTEGER) FROM full_result WHERE layer = 'SALES' AND part = 'SALES NEW CHANNEL' AND item = 'IFA/IMO') || ' ' || (SELECT COUNT(*) FROM ssdb_integration.lr_strategy.tmp_o1_dataset WHERE new_channel = 'IFA/IMO'), '1 0'),
 chk('manual: any code', sl('S1', 'LPL', 'M3', '30301'), 'MANUAL LPL FINANCIAL LLC - BANK FI'),
 chk('rule 4: the name with the most opportunity at the ZIP', sl('S1', 'LPL', 'M13', '94105'), 'SPLIT, MOST OPPORTUNITY AT ZIP LPL FINANCIAL LLC - INDEPENDENT IFA'),
 chk('mga code rule: not where the code''s sales matched two names (then manual)', (SELECT string_agg(zip || ' ' || firm_basis, ', ' ORDER BY zip, firm_basis) FROM ssdb_integration.lr_strategy.tmp_o2_sales WHERE sales_firm_id = '8' AND mga_agent_cd = 'M3' AND source = 'S1'), '02134 SPLIT, MATCHED BY ZIP, 10001 SPLIT, MATCHED BY CHANNEL, 10001 SPLIT, MATCHED BY ZIP, 30301 MANUAL'),
 chk('manual: firm 2, typed in any case and padded; its new channel from the firm', sl('S2', 'Kilo', NULL, '02134'), 'MANUAL ALPHA IFA'),
 chk('manual: a key on 2+ firms and a firm not in market metrics are not applied', (SELECT string_agg(sales_firm || ' ' || firm_basis, ', ' ORDER BY sales_firm) FROM ssdb_integration.lr_strategy.tmp_o2_sales WHERE source = 'S2' AND sales_firm IN ('New', 'No Crd')), 'New NO MARKET METRICS FIRM, No Crd NO CRD'),
 chk('checks: the three manual checks count them (an edited key matches no sale), the rest 0', (SELECT COUNT(*) || ' ' || string_agg(name || '=' || CAST(amt AS INTEGER), ', ' ORDER BY name) FILTER (WHERE amt <> 0) FROM full_result WHERE layer = 'SALES' AND part = 'CHECKS'), '13 MANUAL FIRMS NOT IN TMP_O1_FIRM, NOT APPLIED (MUST BE 0)=1, MANUAL KEYS ON 2+ FIRMS, NOT APPLIED (MUST BE 0)=1, MANUAL ROWS MATCHING NO SALE, NOT APPLIED (MUST BE 0)=1, SALES CHANNELS: KEYS ON 2+ CHANNELS, NOT APPLIED (MUST BE 0)=1, SALES CHANNELS: ROWS MATCHING NO MANUAL OR UNMATCHED SALE, NOT APPLIED (MUST BE 0)=1'),
 chk('review: candidates ranked by score', (SELECT string_agg(rank_in_key || ' ' || cand_broker_name || ' ' || CAST(score * 100 AS INTEGER), ', ' ORDER BY rank_in_key) FROM full_result WHERE layer = 'REVIEW' AND part = 'REVIEW' AND sales_firm = 'Echo'), '1 ALPHA 348, 2 ECHO 100'),
 chk('review: map, name, channel and ZIP evidence, firm 1', ev('S1', 'Delta'), 'N3 1 0 1 1 0 100 6 400'),
 chk('review: firm 2 by name, its wholesaler by name', ev('S2', 'Delta'), 'R2 1 0 1 0 0 100 0 200'),
 chk('review: fuzzy names, ranked with the channel', (SELECT string_agg(rank_in_key || ' ' || cand_broker_name || ' ' || CAST(ev_name * 100 AS INTEGER) || ' ' || CAST(score * 100 AS INTEGER), ', ' ORDER BY rank_in_key) FROM full_result WHERE layer = 'REVIEW' AND part = 'REVIEW' AND sales_firm = 'Foxtrot Inc'), '1 FOXTROT 93 193, 2 FOXTROT 2 92 192'),
 chk('review: IMO kept out, no candidates looked for', (SELECT COUNT(*) FROM full_result WHERE layer = 'REVIEW' AND part = 'REVIEW' AND sales_firm_id = '99') || ' ' || (SELECT n_candidates || ' ' || is_imo FROM ssdb_integration.lr_strategy.tmp_sales_review WHERE sales_firm_id = '99'), '0 0 true'),
 chk('review: keys with no candidate, one row each, ranked by $ in the source', (SELECT string_agg(source || ' ' || COALESCE(sales_firm_id, '-') || ' ' || rank_key_by_amt || ' ' || rank_in_key, ', ' ORDER BY source, rank_key_by_amt) FROM full_result WHERE layer = 'REVIEW' AND part = 'REVIEW' AND cand_firm_crd IS NULL), 'S1 438 2 1, S1 - 4 1, S2 - 3 1, S2 888 4 1'),
 chk('review: the new-channel list', (SELECT new_list_label FROM full_result WHERE layer = 'REVIEW' AND part = 'REVIEW' AND sales_firm_id = '438'), 'AFS'),
 chk('review: AMT counts each key once', (SELECT string_agg(source || ' ' || n || ' ' || CAST(a AS INTEGER), ', ' ORDER BY source) FROM (SELECT source, COUNT(*) AS n, SUM(amt) AS a FROM full_result WHERE layer = 'REVIEW' AND part = 'REVIEW' GROUP BY ALL) x), 'S1 5 15, S2 5 12'),
 chk('summary', (SELECT string_agg(source || ' | ' || firm_basis || ' | ' || item || '=' || n_keys || '/' || CAST(amt AS INTEGER), ', ' ORDER BY source, firm_basis, item) FROM full_result WHERE layer = 'REVIEW' AND part = 'SUMMARY'), 'S1 | NO COMPANY | NO CANDIDATE=1/1, S1 | NO MARKET METRICS FIRM | CHANNEL ZIP MM_MAP=1/3, S1 | NO MARKET METRICS FIRM | CHANNEL ZIP MM_MAP NAME=1/6, S1 | NO MARKET METRICS FIRM | IMO, LEFT OUT=2/15, S1 | NO MARKET METRICS FIRM | NO CANDIDATE=1/5, S2 | NO CRD | CHANNEL FUZZY NAME=1/5, S2 | NO CRD | NO CANDIDATE=1/2, S2 | NO MARKET METRICS FIRM | CHANNEL NAME=1/4, S2 | NO MARKET METRICS FIRM | NO CANDIDATE=1/1'),
 chk('review check 0', (SELECT string_agg(source || '=' || CAST(amt AS INTEGER), ' ' ORDER BY source) FROM full_result WHERE layer = 'REVIEW' AND part = 'CHECKS'), 'S1=0 S2=0'),
 chk('owner route: the firm takes it, new state and route basis', (SELECT route || ' ' || route_basis || ' ' || new_label || ' ' || tau FROM ssdb_integration.lr_strategy.tmp_o1_firm WHERE firm_crd = '601'), 'IFA OWNER OVERRIDE: FI -> IFA IFA IFA'),
 chk('owner route: a firm on 2+ channels keeps its own', (SELECT route || ' ' || route_basis FROM ssdb_integration.lr_strategy.tmp_o1_firm WHERE firm_crd = '300'), 'IFA NAME'),
 chk('owner route: the opportunity it moves is reported', (SELECT source || ' ' || CAST(amt AS INTEGER) FROM full_result WHERE layer = 'OPPORTUNITY' AND part = 'CHECKS' AND name = 'ROUTE BASIS' AND item LIKE 'OWNER OVERRIDE%'), 'S1 10'),
 chk('owner route checks', (SELECT string_agg(name || '=' || n_firms, ', ' ORDER BY name) FROM full_result WHERE layer = 'OPPORTUNITY' AND name LIKE 'OWNER ROUTES%'), 'OWNER ROUTES: A FIRM ON 2+ CHANNELS, NOT APPLIED (MUST BE 0)=1, OWNER ROUTES: FIRM NOT IN THE DATA (MUST BE 0)=1, OWNER ROUTES: NO FIRM 1 TERRITORY CHANNEL (MUST BE 0)=1'),
 chk('one result: every layer', (SELECT string_agg(layer || '=' || n, ' ' ORDER BY layer) FROM (SELECT layer, COUNT(*) AS n FROM full_result GROUP BY ALL) x) = 'OPPORTUNITY=' || (SELECT COUNT(*) FROM ssdb_integration.lr_strategy.tmp_o1_out) || ' REVIEW=' || (SELECT COUNT(*) FROM ssdb_integration.lr_strategy.tmp_um_out) || ' SALES=' || (SELECT COUNT(*) FROM ssdb_integration.lr_strategy.tmp_o2_out), true);
SELECT 'sales_review_test: ok';
SQL
} | duckdb -bail -noheader -list
