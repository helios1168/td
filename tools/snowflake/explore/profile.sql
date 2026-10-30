--Profile of every table the rebuild reads: how each one's keys relate, how the tables join, which labels each uses,
--and the checks the owner's two queries raised (DATASET_LOG.md, 2026-10-30).  Counts, $ and the labels of channel,
--product and flag columns only; no ID or name value leaves the temporary tables.
--EDIT first (Find/Replace): <S1_TERRITORIES>, <S2_OPP>, <S2_SALES>, <S2_CRD_MAP>, <S2_TERRITORIES> are the
--LR_STRATEGY tables ending _TERRITORIES (source 1), _OPP_ORIGINAL, _SALES, _FIRM_CRD, _TERRITORIES (source 2);
--<S1_PRODUCT_4> is the fourth product line of s1_sales.sql:35.
--Run All; download the last statement's result as CSV into $TD_REPO/data/safe/.
--Fiscal year 2025.  Source 1 sales: s1_sales.sql:116-126's filters (its net-zero policy step is not applied).
--Source 2's opportunity table has no year column and is read whole.
--Snowflake docs read 2026-10-30: GROUP BY ALL groups by every SELECT item without an aggregate, and a GROUP BY name
--resolves to a table column before a SELECT alias (https://docs.snowflake.com/en/sql-reference/constructs/group-by),
--so every grouping here is GROUP BY ALL; TRANSLATE drops source characters with no target character
--(https://docs.snowflake.com/en/sql-reference/functions/translate).
use secondary roles all;

--1. Source 1's sales rows in scope, kept for 2 and the checks.
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_prof_s1_sales AS
SELECT policy_no, agent_tax_id, product_line, actual_sales_amount,
       CAST(CAST(consol_brkr_dlr_id AS DECIMAL(38, 0)) AS VARCHAR) AS cbd_id, consol_broker_nm, mga_agent_cd, whslr_id,
       duplicate_entry_in, src_delete_ind, reversal_cd, credit_type, trans_type
FROM life_prod.lif_murkylake.sls_rpt_detail
WHERE fiscal_yr = 2025
  AND TO_DATE(sales_date) BETWEEN '2024-01-01' AND '2025-12-31'
  AND bonus_rate <> 0
  AND init_pay_in = 'Y'
  AND consol_brkr_dlr_id <> '342'
  AND life70_co_cd NOT IN ('VV', 'VB')
  AND agent_tax_id IS NOT NULL
  AND product_line IN ('RILA', 'INDEX', 'VARIABLE', '<S1_PRODUCT_4>', 'FIXED', 'SPIA/DIA');

--2. Each dataset as its distinct key combinations, with rows (N) and $ (AMT), in long form: one row per combination x
--column.  KIND K: a key (4 pairs it with the dataset's other keys, 5 matches it across datasets); KIND D: a label (6
--lists its values).  Values: text, trimmed, upper-cased; blank and '0' are missing.  CH_ZIP is channel | 5-digit ZIP.
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_prof AS
WITH
s1_sales AS (SELECT *, ROW_NUMBER() OVER (ORDER BY n DESC) AS rid FROM (
  SELECT cbd_id, consol_broker_nm AS cbd_name, mga_agent_cd, whslr_id, product_line, duplicate_entry_in, src_delete_ind,
         reversal_cd, credit_type, trans_type, COUNT(*) AS n, SUM(actual_sales_amount) AS amt
  FROM ssdb_integration.lr_strategy.tmp_prof_s1_sales GROUP BY ALL)),
s1_opp_firm AS (SELECT *, ROW_NUMBER() OVER (ORDER BY n DESC) AS rid FROM (
  SELECT cbd_id, client_firm_id, firm_crd, broker_name, dist_ch, channel, product_line, va_product_type,
         COUNT(*) AS n, SUM(global_sales) AS amt
  FROM life_prod.lif_murkylake.wc_market_metrics_opportunity WHERE fiscal_yr = '2025' GROUP BY ALL)),
s1_opp_geo AS (SELECT *, ROW_NUMBER() OVER (ORDER BY n DESC) AS rid FROM (
  SELECT LPAD(LEFT(TRIM(zip_code), 5), 5, '0') AS zip, state, territory,
         dist_ch || '|' || LPAD(LEFT(TRIM(zip_code), 5), 5, '0') AS ch_zip, dist_ch, COUNT(*) AS n, SUM(global_sales) AS amt
  FROM life_prod.lif_murkylake.wc_market_metrics_opportunity WHERE fiscal_yr = '2025' GROUP BY ALL)),
mm_map AS (SELECT *, ROW_NUMBER() OVER (ORDER BY n DESC) AS rid FROM (
  SELECT CAST(CAST(cbd_id AS DECIMAL(38, 0)) AS VARCHAR) AS cbd_id,
         CAST(CAST(firm_client_id AS DECIMAL(38, 0)) AS VARCHAR) AS client_firm_id,
         CAST(CAST(firm_crd AS DECIMAL(38, 0)) AS VARCHAR) AS firm_crd, broker_name, dist_ch,
         CAST(CAST(channel AS DECIMAL(38, 0)) AS VARCHAR) AS channel, COUNT(*) AS n, CAST(NULL AS DECIMAL(38, 2)) AS amt
  FROM ssdb_integration.lr_strategy.mm_map GROUP BY ALL)),
crd_to_cbd AS (SELECT *, ROW_NUMBER() OVER (ORDER BY n DESC) AS rid FROM (
  SELECT CAST(CAST(firm_crd AS DECIMAL(38, 0)) AS VARCHAR) AS firm_crd, CAST(CAST(cbd_id AS DECIMAL(38, 0)) AS VARCHAR) AS cbd_id,
         firm, cbd_nm_best, COUNT(*) AS n, CAST(NULL AS DECIMAL(38, 2)) AS amt
  FROM ssdb_integration.lr_strategy.crd_to_cbd GROUP BY ALL)),
s1_master AS (SELECT *, ROW_NUMBER() OVER (ORDER BY n DESC) AS rid FROM (   -- the rows s1_sales.sql:70-79 keeps
  SELECT cbd_id, master_id, cbd_name, master_name, COUNT(*) AS n, CAST(NULL AS DECIMAL(38, 2)) AS amt
  FROM (SELECT DISTINCT CAST(CAST(consol_brkr_dealer_id AS DECIMAL(38, 0)) AS VARCHAR) AS cbd_id,
               master_consol_brkr_dealer_id AS master_id, consol_brkr_dealer_name AS cbd_name,
               master_consol_brkr_dealer_name AS master_name
        FROM life_prod.lif_murkylake.wc_edw_consol_brkr_dealer_mga_master
        WHERE expiration_dte = '9999-12-31' AND consol_brkr_dealer_id <> 0 AND consol_brkr_dealer_id IS NOT NULL) m
  GROUP BY ALL)),
s1_mga_map AS (SELECT *, ROW_NUMBER() OVER (ORDER BY n DESC) AS rid FROM (
  SELECT mga_agent_cd, channel, channel_calc, channel_override, COUNT(*) AS n, SUM(dollars_total) AS amt
  FROM ssdb_integration.lr_strategy.mga_map GROUP BY ALL)),
s1_whslr AS (SELECT *, ROW_NUMBER() OVER (ORDER BY n DESC) AS rid FROM (
  SELECT whslr_id, sales_district_id, distch, status_cd, COUNT(*) AS n, CAST(NULL AS DECIMAL(38, 2)) AS amt
  FROM life_prod.lif_murkylake.whslr GROUP BY ALL)),
s1_terr AS (SELECT *, ROW_NUMBER() OVER (ORDER BY n DESC) AS rid FROM (
  SELECT whslr_id, new_dist_channel || '|' || LPAD(LEFT(TRIM(zip), 5), 5, '0') AS ch_zip, new_dist_channel,
         COUNT(*) AS n, CAST(NULL AS DECIMAL(38, 2)) AS amt
  FROM ssdb_integration.lr_strategy.<S1_TERRITORIES> GROUP BY ALL)),
s2_opp_firm AS (SELECT *, ROW_NUMBER() OVER (ORDER BY n DESC) AS rid FROM (
  SELECT CAST(CAST(firm_crd AS DECIMAL(38, 0)) AS VARCHAR) AS firm_crd, broker_name,
         CAST(CAST(channel AS DECIMAL(38, 0)) AS VARCHAR) AS channel, dist_ch, product_line, va_product_type,
         COUNT(*) AS n, SUM(opp) AS amt
  FROM ssdb_integration.lr_strategy.<S2_OPP> GROUP BY ALL)),
s2_opp_geo AS (SELECT *, ROW_NUMBER() OVER (ORDER BY n DESC) AS rid FROM (
  SELECT LPAD(CAST(CAST(zip_code AS DECIMAL(38, 0)) AS VARCHAR), 5, '0') AS zip,
         dist_ch || '|' || LPAD(CAST(CAST(zip_code AS DECIMAL(38, 0)) AS VARCHAR), 5, '0') AS ch_zip, dist_ch,
         COUNT(*) AS n, SUM(opp) AS amt
  FROM ssdb_integration.lr_strategy.<S2_OPP> GROUP BY ALL)),
s2_sales AS (SELECT *, ROW_NUMBER() OVER (ORDER BY n DESC) AS rid FROM (
  SELECT CAST(CAST(firm_crd AS DECIMAL(38, 0)) AS VARCHAR) AS firm_crd, firm, parent_firm, channel, product, shareclass,
         COUNT(*) AS n, SUM(sales_amount) AS amt
  FROM ssdb_integration.lr_strategy.<S2_SALES> WHERE year = 2025 GROUP BY ALL)),
s2_crd_map AS (SELECT *, ROW_NUMBER() OVER (ORDER BY n DESC) AS rid FROM (
  SELECT CAST(CAST(firm_crd AS DECIMAL(38, 0)) AS VARCHAR) AS firm_crd, firm, COUNT(*) AS n, CAST(NULL AS DECIMAL(38, 2)) AS amt
  FROM ssdb_integration.lr_strategy.<S2_CRD_MAP> GROUP BY ALL)),
s2_terr AS (SELECT *, ROW_NUMBER() OVER (ORDER BY n DESC) AS rid FROM (
  SELECT territory_id, rvp, channel || '|' || LPAD(LEFT(TRIM(zipcode), 5), 5, '0') AS ch_zip, channel, channel_name,
         COUNT(*) AS n, CAST(NULL AS DECIMAL(38, 2)) AS amt
  FROM ssdb_integration.lr_strategy.<S2_TERRITORIES> GROUP BY ALL)),
lng AS (
            SELECT 'S1_SALES' AS ds, rid, 'K' AS kind, 'CBD_ID' AS col, cbd_id AS v, n, amt FROM s1_sales
  UNION ALL SELECT 'S1_SALES', rid, 'K', 'CBD_NAME', cbd_name, n, amt FROM s1_sales
  UNION ALL SELECT 'S1_SALES', rid, 'K', 'MGA_AGENT_CD', mga_agent_cd, n, amt FROM s1_sales
  UNION ALL SELECT 'S1_SALES', rid, 'K', 'WHSLR_ID', whslr_id, n, amt FROM s1_sales
  UNION ALL SELECT 'S1_SALES', rid, 'D', 'PRODUCT_LINE', product_line, n, amt FROM s1_sales
  UNION ALL SELECT 'S1_SALES', rid, 'D', 'DUPLICATE_ENTRY_IN', duplicate_entry_in, n, amt FROM s1_sales
  UNION ALL SELECT 'S1_SALES', rid, 'D', 'SRC_DELETE_IND', src_delete_ind, n, amt FROM s1_sales
  UNION ALL SELECT 'S1_SALES', rid, 'D', 'REVERSAL_CD', reversal_cd, n, amt FROM s1_sales
  UNION ALL SELECT 'S1_SALES', rid, 'D', 'CREDIT_TYPE', credit_type, n, amt FROM s1_sales
  UNION ALL SELECT 'S1_SALES', rid, 'D', 'TRANS_TYPE', trans_type, n, amt FROM s1_sales
  UNION ALL SELECT 'S1_OPP_FIRM', rid, 'K', 'CBD_ID', cbd_id, n, amt FROM s1_opp_firm
  UNION ALL SELECT 'S1_OPP_FIRM', rid, 'K', 'CLIENT_FIRM_ID', client_firm_id, n, amt FROM s1_opp_firm
  UNION ALL SELECT 'S1_OPP_FIRM', rid, 'K', 'FIRM_CRD', firm_crd, n, amt FROM s1_opp_firm
  UNION ALL SELECT 'S1_OPP_FIRM', rid, 'K', 'BROKER_NAME', broker_name, n, amt FROM s1_opp_firm
  UNION ALL SELECT 'S1_OPP_FIRM', rid, 'D', 'DIST_CH', dist_ch, n, amt FROM s1_opp_firm
  UNION ALL SELECT 'S1_OPP_FIRM', rid, 'D', 'CHANNEL', channel, n, amt FROM s1_opp_firm
  UNION ALL SELECT 'S1_OPP_FIRM', rid, 'D', 'PRODUCT_LINE', product_line, n, amt FROM s1_opp_firm
  UNION ALL SELECT 'S1_OPP_FIRM', rid, 'D', 'VA_PRODUCT_TYPE', va_product_type, n, amt FROM s1_opp_firm
  UNION ALL SELECT 'S1_OPP_GEO', rid, 'K', 'ZIP', zip, n, amt FROM s1_opp_geo
  UNION ALL SELECT 'S1_OPP_GEO', rid, 'K', 'STATE', state, n, amt FROM s1_opp_geo
  UNION ALL SELECT 'S1_OPP_GEO', rid, 'K', 'TERRITORY', territory, n, amt FROM s1_opp_geo
  UNION ALL SELECT 'S1_OPP_GEO', rid, 'K', 'CH_ZIP', ch_zip, n, amt FROM s1_opp_geo
  UNION ALL SELECT 'MM_MAP', rid, 'K', 'CBD_ID', cbd_id, n, amt FROM mm_map
  UNION ALL SELECT 'MM_MAP', rid, 'K', 'CLIENT_FIRM_ID', client_firm_id, n, amt FROM mm_map
  UNION ALL SELECT 'MM_MAP', rid, 'K', 'FIRM_CRD', firm_crd, n, amt FROM mm_map
  UNION ALL SELECT 'MM_MAP', rid, 'K', 'BROKER_NAME', broker_name, n, amt FROM mm_map
  UNION ALL SELECT 'MM_MAP', rid, 'D', 'DIST_CH', dist_ch, n, amt FROM mm_map
  UNION ALL SELECT 'MM_MAP', rid, 'D', 'CHANNEL', channel, n, amt FROM mm_map
  UNION ALL SELECT 'CRD_TO_CBD', rid, 'K', 'FIRM_CRD', firm_crd, n, amt FROM crd_to_cbd
  UNION ALL SELECT 'CRD_TO_CBD', rid, 'K', 'CBD_ID', cbd_id, n, amt FROM crd_to_cbd
  UNION ALL SELECT 'CRD_TO_CBD', rid, 'K', 'FIRM', firm, n, amt FROM crd_to_cbd
  UNION ALL SELECT 'CRD_TO_CBD', rid, 'K', 'CBD_NM_BEST', cbd_nm_best, n, amt FROM crd_to_cbd
  UNION ALL SELECT 'S1_MASTER', rid, 'K', 'CBD_ID', cbd_id, n, amt FROM s1_master
  UNION ALL SELECT 'S1_MASTER', rid, 'K', 'MASTER_ID', master_id, n, amt FROM s1_master
  UNION ALL SELECT 'S1_MASTER', rid, 'K', 'CBD_NAME', cbd_name, n, amt FROM s1_master
  UNION ALL SELECT 'S1_MASTER', rid, 'K', 'MASTER_NAME', master_name, n, amt FROM s1_master
  UNION ALL SELECT 'S1_MGA_MAP', rid, 'K', 'MGA_AGENT_CD', mga_agent_cd, n, amt FROM s1_mga_map
  UNION ALL SELECT 'S1_MGA_MAP', rid, 'D', 'CHANNEL', channel, n, amt FROM s1_mga_map
  UNION ALL SELECT 'S1_MGA_MAP', rid, 'D', 'CHANNEL_CALC', channel_calc, n, amt FROM s1_mga_map
  UNION ALL SELECT 'S1_MGA_MAP', rid, 'D', 'CHANNEL_OVERRIDE', channel_override, n, amt FROM s1_mga_map
  UNION ALL SELECT 'S1_WHSLR', rid, 'K', 'WHSLR_ID', whslr_id, n, amt FROM s1_whslr
  UNION ALL SELECT 'S1_WHSLR', rid, 'K', 'SALES_DISTRICT_ID', sales_district_id, n, amt FROM s1_whslr
  UNION ALL SELECT 'S1_WHSLR', rid, 'D', 'DISTCH', distch, n, amt FROM s1_whslr
  UNION ALL SELECT 'S1_WHSLR', rid, 'D', 'STATUS_CD', status_cd, n, amt FROM s1_whslr
  UNION ALL SELECT 'S1_TERR', rid, 'K', 'WHSLR_ID', whslr_id, n, amt FROM s1_terr
  UNION ALL SELECT 'S1_TERR', rid, 'K', 'CH_ZIP', ch_zip, n, amt FROM s1_terr
  UNION ALL SELECT 'S1_TERR', rid, 'D', 'NEW_DIST_CHANNEL', new_dist_channel, n, amt FROM s1_terr
  UNION ALL SELECT 'S2_OPP_FIRM', rid, 'K', 'FIRM_CRD', firm_crd, n, amt FROM s2_opp_firm
  UNION ALL SELECT 'S2_OPP_FIRM', rid, 'K', 'BROKER_NAME', broker_name, n, amt FROM s2_opp_firm
  UNION ALL SELECT 'S2_OPP_FIRM', rid, 'D', 'CHANNEL', channel, n, amt FROM s2_opp_firm
  UNION ALL SELECT 'S2_OPP_FIRM', rid, 'D', 'DIST_CH', dist_ch, n, amt FROM s2_opp_firm
  UNION ALL SELECT 'S2_OPP_FIRM', rid, 'D', 'PRODUCT_LINE', product_line, n, amt FROM s2_opp_firm
  UNION ALL SELECT 'S2_OPP_FIRM', rid, 'D', 'VA_PRODUCT_TYPE', va_product_type, n, amt FROM s2_opp_firm
  UNION ALL SELECT 'S2_OPP_GEO', rid, 'K', 'ZIP', zip, n, amt FROM s2_opp_geo
  UNION ALL SELECT 'S2_OPP_GEO', rid, 'K', 'CH_ZIP', ch_zip, n, amt FROM s2_opp_geo
  UNION ALL SELECT 'S2_SALES', rid, 'K', 'FIRM_CRD', firm_crd, n, amt FROM s2_sales
  UNION ALL SELECT 'S2_SALES', rid, 'K', 'FIRM', firm, n, amt FROM s2_sales
  UNION ALL SELECT 'S2_SALES', rid, 'K', 'PARENT_FIRM', parent_firm, n, amt FROM s2_sales
  UNION ALL SELECT 'S2_SALES', rid, 'D', 'CHANNEL', channel, n, amt FROM s2_sales
  UNION ALL SELECT 'S2_SALES', rid, 'D', 'PRODUCT', product, n, amt FROM s2_sales
  UNION ALL SELECT 'S2_SALES', rid, 'D', 'SHARECLASS', shareclass, n, amt FROM s2_sales
  UNION ALL SELECT 'S2_CRD_MAP', rid, 'K', 'FIRM_CRD', firm_crd, n, amt FROM s2_crd_map
  UNION ALL SELECT 'S2_CRD_MAP', rid, 'K', 'FIRM', firm, n, amt FROM s2_crd_map
  UNION ALL SELECT 'S2_TERR', rid, 'K', 'TERRITORY_ID', territory_id, n, amt FROM s2_terr
  UNION ALL SELECT 'S2_TERR', rid, 'K', 'RVP', rvp, n, amt FROM s2_terr
  UNION ALL SELECT 'S2_TERR', rid, 'K', 'CH_ZIP', ch_zip, n, amt FROM s2_terr
  UNION ALL SELECT 'S2_TERR', rid, 'D', 'CHANNEL', channel, n, amt FROM s2_terr
  UNION ALL SELECT 'S2_TERR', rid, 'D', 'CHANNEL_NAME', channel_name, n, amt FROM s2_terr)
SELECT ds, rid, kind, col, NULLIF(NULLIF(UPPER(TRIM(CAST(v AS VARCHAR))), ''), '0') AS val, n, amt FROM lng;

--3. Every column: rows, distinct values, % of rows and of $ with no value, value lengths, values with a non-digit.
--Statements 3-7 each build one part of the result, all with the same 15 columns; 8 returns them together.
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_prof_cols AS
SELECT 'COLUMNS' AS part, ds, col, kind AS col2, CAST(NULL AS VARCHAR) AS item,
       COUNT(DISTINCT val) AS n_values, SUM(n) AS n_rows, SUM(amt) AS amt,
       ROUND(100.0 * SUM(CASE WHEN val IS NULL THEN n ELSE 0 END) / SUM(n), 2) AS pct_rows,
       ROUND(100.0 * SUM(CASE WHEN val IS NULL THEN amt ELSE 0 END) / NULLIF(SUM(amt), 0), 2) AS pct_amt,
       MIN(LENGTH(val)) AS min_len, MAX(LENGTH(val)) AS max_len,
       COUNT(DISTINCT CASE WHEN TRANSLATE(val, '0123456789', '') <> '' THEN val END) AS n_nondigit,
       CAST(NULL AS BIGINT) AS n_a, CAST(NULL AS BIGINT) AS n_b
FROM ssdb_integration.lr_strategy.tmp_prof
GROUP BY ALL;

--4. Pairs of keys within a dataset, every link between their values (combinations carrying both) by shape:
--   1 : 1 the same thing; one A, many B: B nests in A; many A, one B: A nests in B; many : many tangled.
--   N_VALUES: links; N_ROWS and AMT: the rows and $ on them; PCT_AMT: of the pair's $; N_A, N_B: values of each column.
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_prof_pairs AS
WITH
l AS (
  SELECT a.ds, a.col AS a, a.val AS a_val, b.col AS b, b.val AS b_val, SUM(a.n) AS n, SUM(a.amt) AS amt
  FROM ssdb_integration.lr_strategy.tmp_prof a
  JOIN ssdb_integration.lr_strategy.tmp_prof b ON b.ds = a.ds AND b.rid = a.rid AND a.col < b.col
  WHERE a.kind = 'K' AND b.kind = 'K' AND a.val IS NOT NULL AND b.val IS NOT NULL
  GROUP BY ALL),
na AS (SELECT ds, a, b, a_val, COUNT(*) AS k FROM l GROUP BY ALL),
nb AS (SELECT ds, a, b, b_val, COUNT(*) AS k FROM l GROUP BY ALL),
s AS (
  SELECT l.ds, l.a, l.b,
         CASE WHEN na.k = 1 AND nb.k = 1 THEN '1 : 1'
              WHEN na.k > 1 AND nb.k = 1 THEN 'one ' || l.a || ', many ' || l.b
              WHEN na.k = 1 AND nb.k > 1 THEN 'many ' || l.a || ', one ' || l.b
              ELSE 'many : many' END AS shape,
         COUNT(*) AS links, SUM(l.n) AS n_rows, SUM(l.amt) AS amt,
         COUNT(DISTINCT l.a_val) AS n_a, COUNT(DISTINCT l.b_val) AS n_b
  FROM l
  JOIN na ON na.ds = l.ds AND na.a = l.a AND na.b = l.b AND na.a_val = l.a_val
  JOIN nb ON nb.ds = l.ds AND nb.a = l.a AND nb.b = l.b AND nb.b_val = l.b_val
  GROUP BY ALL)
SELECT 'PAIRS' AS part, ds, a AS col, b AS col2, shape AS item, links AS n_values, n_rows, amt,
       CAST(NULL AS DOUBLE) AS pct_rows,
       ROUND(100.0 * amt / NULLIF(SUM(amt) OVER (PARTITION BY ds, a, b), 0), 2) AS pct_amt,
       CAST(NULL AS BIGINT) AS min_len, CAST(NULL AS BIGINT) AS max_len, CAST(NULL AS BIGINT) AS n_nondigit, n_a, n_b
FROM s;

--5. Matches across datasets: each value of the left key by how many rows of the right dataset carry it (0, 1, 2+).
--   A left row whose value has 2+ right rows is repeated by a join on that key; 0 is not covered.  COL2: the right key.
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_prof_matches AS
WITH
m AS (SELECT * FROM (VALUES
  ('S1_SALES', 'MGA_AGENT_CD', 'S1_MGA_MAP', 'MGA_AGENT_CD'),
  ('S1_SALES', 'CBD_ID', 'S1_MASTER', 'CBD_ID'),
  ('S1_SALES', 'WHSLR_ID', 'S1_WHSLR', 'WHSLR_ID'),
  ('S1_SALES', 'CBD_ID', 'MM_MAP', 'CBD_ID'),
  ('S1_SALES', 'CBD_ID', 'CRD_TO_CBD', 'CBD_ID'),
  ('S1_OPP_FIRM', 'FIRM_CRD', 'MM_MAP', 'FIRM_CRD'),
  ('S1_OPP_FIRM', 'CBD_ID', 'MM_MAP', 'CBD_ID'),
  ('S1_OPP_GEO', 'CH_ZIP', 'S1_TERR', 'CH_ZIP'),
  ('S1_OPP_GEO', 'TERRITORY', 'S1_WHSLR', 'WHSLR_ID'),
  ('S2_SALES', 'FIRM_CRD', 'S2_OPP_FIRM', 'FIRM_CRD'),
  ('S2_SALES', 'FIRM_CRD', 'S2_CRD_MAP', 'FIRM_CRD'),
  ('S2_OPP_FIRM', 'FIRM_CRD', 'MM_MAP', 'FIRM_CRD'),
  ('S2_OPP_FIRM', 'FIRM_CRD', 'S1_OPP_FIRM', 'FIRM_CRD'),
  ('S2_OPP_GEO', 'CH_ZIP', 'S2_TERR', 'CH_ZIP')) AS v (lds, lcol, rds, rcol)),
lv AS (SELECT m.lds, m.lcol, m.rds, m.rcol, p.val, SUM(p.n) AS n, SUM(p.amt) AS amt
       FROM m JOIN ssdb_integration.lr_strategy.tmp_prof p ON p.ds = m.lds AND p.col = m.lcol
       GROUP BY ALL),
rv AS (SELECT m.lds, m.lcol, m.rds, m.rcol, p.val, SUM(p.n) AS n
       FROM m JOIN ssdb_integration.lr_strategy.tmp_prof p ON p.ds = m.rds AND p.col = m.rcol
       WHERE p.val IS NOT NULL
       GROUP BY ALL),
o AS (SELECT lv.lds, lv.lcol, lv.rds || '.' || lv.rcol AS r,
             CASE WHEN lv.val IS NULL THEN 'no value' WHEN rv.n IS NULL THEN '0'
                  WHEN rv.n = 1 THEN '1' ELSE '2+' END AS outcome,
             COUNT(*) AS n_values, SUM(lv.n) AS n_rows, SUM(lv.amt) AS amt
      FROM lv LEFT JOIN rv ON rv.lds = lv.lds AND rv.lcol = lv.lcol AND rv.rds = lv.rds AND rv.rcol = lv.rcol
                          AND rv.val = lv.val
      GROUP BY ALL)
SELECT 'MATCHES' AS part, lds AS ds, lcol AS col, r AS col2, outcome AS item, n_values, n_rows, amt,
       ROUND(100.0 * n_rows / SUM(n_rows) OVER (PARTITION BY lds, lcol, r), 2) AS pct_rows,
       ROUND(100.0 * amt / NULLIF(SUM(amt) OVER (PARTITION BY lds, lcol, r), 0), 2) AS pct_amt,
       CAST(NULL AS BIGINT) AS min_len, CAST(NULL AS BIGINT) AS max_len, CAST(NULL AS BIGINT) AS n_nondigit,
       CAST(NULL AS BIGINT) AS n_a, CAST(NULL AS BIGINT) AS n_b
FROM o;

--6. The labels: each value of every D column with rows and $, the 40 largest per column.
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_prof_labels AS
SELECT 'LABELS' AS part, ds, col, CAST(NULL AS VARCHAR) AS col2, val AS item, CAST(NULL AS BIGINT) AS n_values,
       n_rows, amt, pct_rows, pct_amt,
       CAST(NULL AS BIGINT) AS min_len, CAST(NULL AS BIGINT) AS max_len, CAST(NULL AS BIGINT) AS n_nondigit,
       CAST(NULL AS BIGINT) AS n_a, CAST(NULL AS BIGINT) AS n_b
FROM (SELECT ds, col, val, n_rows, amt,
             ROUND(100.0 * n_rows / SUM(n_rows) OVER (PARTITION BY ds, col), 2) AS pct_rows,
             ROUND(100.0 * amt / NULLIF(SUM(amt) OVER (PARTITION BY ds, col), 0), 2) AS pct_amt,
             ROW_NUMBER() OVER (PARTITION BY ds, col ORDER BY amt DESC NULLS LAST, n_rows DESC, val) AS rk
      FROM (SELECT ds, col, val, SUM(n) AS n_rows, SUM(amt) AS amt
            FROM ssdb_integration.lr_strategy.tmp_prof WHERE kind = 'D' GROUP BY ALL) x) y
WHERE rk <= 40;

--7. Checks the two queries raised (DATASET_LOG.md, 2026-10-30), each by outcome.  COL: the check.
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_prof_checks AS
WITH
pol AS (SELECT policy_no, COUNT(DISTINCT product_line) AS k, SUM(actual_sales_amount) AS amt
        FROM ssdb_integration.lr_strategy.tmp_prof_s1_sales GROUP BY ALL),
agt AS (SELECT agent_tax_id, SUM(actual_sales_amount) AS amt
        FROM ssdb_integration.lr_strategy.tmp_prof_s1_sales GROUP BY ALL),
con AS (SELECT contact_ssn, COUNT(*) AS k FROM life_prod.lif_murkylake.wc_sbl_contact GROUP BY ALL),
rgn AS (SELECT rgn_cd, start_zip, end_zip, cbd FROM life_prod.lif_murkylake.geographic_region
        WHERE expir_dt = '9999-12-31'),
rgn_wz AS (SELECT DISTINCT rw.whslr_id, LEFT(r.start_zip, 5) AS zip
           FROM life_prod.lif_murkylake.rgn_whslr rw JOIN rgn r ON r.rgn_cd = rw.rgn_cd
           WHERE rw.expir_dt = '9999-12-31' AND r.cbd IN (0, 3)),
terr_wz AS (SELECT DISTINCT whslr_id, LEFT(TRIM(zip), 5) AS zip FROM ssdb_integration.lr_strategy.<S1_TERRITORIES>),
zips AS (
            SELECT 'S1_OPP' AS ds, TRIM(zip_code) AS z, global_sales AS amt
            FROM life_prod.lif_murkylake.wc_market_metrics_opportunity WHERE fiscal_yr = '2025'
  UNION ALL SELECT 'S1_ADDR', TRIM(zip_cd), NULL FROM life_prod.lif_murkylake.wc_sbl_addr
  UNION ALL SELECT 'S1_REGION_START', TRIM(start_zip), NULL FROM rgn
  UNION ALL SELECT 'S1_TERR', TRIM(zip), NULL FROM ssdb_integration.lr_strategy.<S1_TERRITORIES>
  UNION ALL SELECT 'S2_OPP', CAST(CAST(zip_code AS DECIMAL(38, 0)) AS VARCHAR), opp FROM ssdb_integration.lr_strategy.<S2_OPP>
  UNION ALL SELECT 'S2_SALES', TRIM(zip_code), sales_amount FROM ssdb_integration.lr_strategy.<S2_SALES> WHERE year = 2025
  UNION ALL SELECT 'S2_TERR', TRIM(zipcode), NULL FROM ssdb_integration.lr_strategy.<S2_TERRITORIES>),
c AS (
            SELECT 'S1_SALES' AS ds, 'POLICY_PRODUCT_LINES' AS chk, CASE WHEN k >= 2 THEN '2+' ELSE '1' END AS outcome,
                   COUNT(*) AS n, SUM(amt) AS amt
            FROM pol GROUP BY ALL
  UNION ALL SELECT 'S1_SALES', 'AGENT_CONTACT_ROWS', CASE WHEN con.k IS NULL THEN '0' WHEN con.k = 1 THEN '1' ELSE '2+' END,
                   COUNT(*), SUM(agt.amt)
            FROM agt LEFT JOIN con ON con.contact_ssn = agt.agent_tax_id GROUP BY ALL
  UNION ALL SELECT 'S1_REGION', 'START_ZIP_VS_END_ZIP',
                   CASE WHEN end_zip IS NULL THEN 'end missing' WHEN start_zip = end_zip THEN 'same' ELSE 'range' END,
                   COUNT(*), NULL
            FROM rgn GROUP BY ALL
  UNION ALL SELECT 'S1_TERR', 'WHSLR_ZIP_VS_REGIONS',
                   CASE WHEN t.whslr_id IS NULL THEN 'regions only' WHEN r.whslr_id IS NULL THEN 'table only' ELSE 'both' END,
                   COUNT(*), NULL
            FROM terr_wz t FULL OUTER JOIN rgn_wz r ON r.whslr_id = t.whslr_id AND r.zip = t.zip GROUP BY ALL
  UNION ALL SELECT ds, 'ZIP_FORM',
                   CASE WHEN z IS NULL OR z = '' THEN 'missing' WHEN TRANSLATE(z, '0123456789', '') <> '' THEN 'non-digit'
                        WHEN LENGTH(z) = 5 THEN '5 digits' WHEN LENGTH(z) < 5 THEN 'under 5 digits'
                        ELSE 'over 5 digits' END,
                   COUNT(*), SUM(amt)
            FROM zips GROUP BY ALL
  UNION ALL SELECT 'S2_SALES', 'YEAR: SALES_AMOUNT', CAST(year AS VARCHAR), COUNT(*), SUM(sales_amount)
            FROM ssdb_integration.lr_strategy.<S2_SALES> GROUP BY ALL
  UNION ALL SELECT 'S2_SALES', 'YEAR: MM_AMOUNT', CAST(year AS VARCHAR), COUNT(*), SUM(mm_amount)
            FROM ssdb_integration.lr_strategy.<S2_SALES> GROUP BY ALL
  UNION ALL SELECT 'S1_OPP', 'FISCAL_YR: GLOBAL_SALES', fiscal_yr, COUNT(*), SUM(global_sales)
            FROM life_prod.lif_murkylake.wc_market_metrics_opportunity GROUP BY ALL)
SELECT 'CHECKS' AS part, ds, chk AS col, CAST(NULL AS VARCHAR) AS col2, outcome AS item, CAST(NULL AS BIGINT) AS n_values,
       n AS n_rows, amt,
       ROUND(100.0 * n / SUM(n) OVER (PARTITION BY ds, chk), 2) AS pct_rows,
       ROUND(100.0 * amt / NULLIF(SUM(amt) OVER (PARTITION BY ds, chk), 0), 2) AS pct_amt,
       CAST(NULL AS BIGINT) AS min_len, CAST(NULL AS BIGINT) AS max_len, CAST(NULL AS BIGINT) AS n_nondigit,
       CAST(NULL AS BIGINT) AS n_a, CAST(NULL AS BIGINT) AS n_b
FROM c;

--8. Everything, one result set: download as CSV.
SELECT * FROM ssdb_integration.lr_strategy.tmp_prof_cols
UNION ALL SELECT * FROM ssdb_integration.lr_strategy.tmp_prof_pairs
UNION ALL SELECT * FROM ssdb_integration.lr_strategy.tmp_prof_matches
UNION ALL SELECT * FROM ssdb_integration.lr_strategy.tmp_prof_labels
UNION ALL SELECT * FROM ssdb_integration.lr_strategy.tmp_prof_checks
ORDER BY part, ds, col, col2, item;
