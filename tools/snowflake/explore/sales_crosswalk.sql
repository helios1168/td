--Sales crosswalk (validation; owner, 2026-10-30: "I need to validate at the sales level for each source firm a complete
--cross walk across our mappings from [firm 2's sales table] and [firm 1's base sales table] to what is in o2_dataset").
--Run 01_opportunity_sales.sql first, in the same worksheet: this file reads its temporary tables and its session
--variables s1_sales and s2_sales (no SET lines here, so an unset variable fails loudly).  Firm names and sales $ appear
--together: read it at work, never bring it here (DATASET_LOG.md, Conventions, Masking).  One result set:
--  CROSSWALK: one row per source x the sales table's own key, fiscal year 2025 (firm 1: product bucket ALL), as the
--    table has it: SALES_FIRM_ID (firm 1's CONSOL_BRKR_DLR_ID, firm 2's FIRM_CRD), SALES_FIRM (CONSOL_BROKER_NM, FIRM),
--    RAW_CHANNEL (DIST_CH, CHANNEL), RAW_PRODUCT (PRODUCT_LINE2, PRODUCT).  Then each mapping step's output:
--    OLD_CHANNEL_S1 (firm 2's channel in firm 1's names), MATCH_CHANNEL (the channel that picks the firm on a split),
--    N_CANDIDATES and CANDIDATES (the market metrics firms the ID reaches: CRD, broker name, firm 1 route), FIRM_BASIS,
--    FIRM_CRD x BROKER_NAME (the firm chosen), PRODUCT, NEW_CHANNEL; and the amounts: rows, sellers, ZIPs, SALES,
--    SALES_ALT, the sales with no ZIP, no seller, on a cell with opportunity, in the seller's held cells old and new.
--  OUT OF WINDOW: each sales table's rows outside fiscal year 2025 (firm 1: or another product bucket), by ITEM.
--  CHECKS (CHECK_VALUE must be 0, per source): RAW KEYS VS CROSSWALK (keys whose $ differ; SALES: the $ apart); RAW
--    KEYS ON 2+ OUTPUTS; CROSSWALK VS TMP_O2_DATASET by firm x product x old channel x new channel; RAW TABLE MINUS
--    CROSSWALK AND OUT OF WINDOW.
--  TMP_SALES_MAP (statement 3, owner, 2026-10-30: "produce the mapping table we use to map the [firm 2] sales and
--    [firm 1] sales tables to the o2_dataset table"): the crosswalk's keys and outputs without amounts, one row per
--    sales-table key (RAW KEYS ON 2+ OUTPUTS must be 0).  SALES_FIRM_ID is firm 1's own CBD_ID (CONSOL_BRKR_DLR_ID);
--    CBD_ID is the company ID the mapped firm (FIRM_CRD x BROKER_NAME) carries on firm 1's opportunity rows, as
--    s1_opp_sales.sql:475-482 derives it, ' | ' between 2+ (N_CBD_ID), for both sources; none where no firm was
--    chosen or its rows carry none.  Join a sales table to it on SOURCE and the four keys, the
--    firm ID cast as below, NULL-safe; e.g. firm 1:
--      SELECT b.*, m.firm_crd, m.broker_name, m.product, m.old_channel_s1, m.new_channel, m.firm_basis
--      FROM IDENTIFIER($s1_sales) b
--      JOIN ssdb_integration.lr_strategy.tmp_sales_map m
--        ON m.source = 'S1'
--       AND EQUAL_NULL(m.sales_firm_id, NULLIF(CAST(CAST(b.consol_brkr_dlr_id AS DECIMAL(38, 0)) AS VARCHAR), '0'))
--       AND EQUAL_NULL(m.sales_firm, b.consol_broker_nm)
--       AND EQUAL_NULL(m.raw_channel, b.dist_ch) AND EQUAL_NULL(m.raw_product, b.product_line2)
--      WHERE b.fiscal_yr = 2025 AND b.product_bucket = 'ALL';
--    firm 2: FIRM_CRD as CAST(CAST(firm_crd AS DECIMAL(38, 0)) AS VARCHAR), FIRM, CHANNEL, PRODUCT, YEAR = 2025.  The other
--    two keys are formulas, not table rows: WHOLESALER_KEY is TRIM(WHSLR_ID) (firm 1) or UPPER(TRIM(RVP)) (firm 2);
--    ZIP is LPAD(LEFT(TRIM(zip), 5), 5, '0'), blank or 'BLANK' none.
--Snowflake docs read 2026-10-30: FULL OUTER JOIN (https://docs.snowflake.com/en/sql-reference/constructs/join), GROUP
--BY ALL (.../constructs/group-by), EQUAL_NULL, NULL-safe equality (.../functions/equal_null).  LISTAGG(DISTINCT ...) WITHIN
--GROUP ran at work (archived explore/firm_master_relationships.sql, 2026-10-29).
use secondary roles all;

--1. The market metrics firms each sales firm ID can reach, with each one's firm 1 route.
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_xw_cand AS
SELECT source, firm_id, COUNT(*) AS n_candidates, LISTAGG(DISTINCT cand, ' | ') WITHIN GROUP (ORDER BY cand) AS candidates
FROM (
            SELECT 'S1' AS source, cf.company_id AS firm_id,
                   cf.firm_crd || ' ' || cf.broker_name || ' (' || COALESCE(f.route, 'NO ROUTE') || ')' AS cand
            FROM ssdb_integration.lr_strategy.tmp_o2_company_firm cf
            LEFT JOIN ssdb_integration.lr_strategy.tmp_o1_firm f ON f.firm_crd = cf.firm_crd AND f.broker_name = cf.broker_name
  UNION ALL SELECT 'S2', firm_crd, firm_crd || ' ' || broker_name || ' (' || route || ')'
            FROM ssdb_integration.lr_strategy.tmp_o1_firm) x
GROUP BY source, firm_id;

--2. The crosswalk: TMP_O2_SALES (01_opportunity_sales.sql, statement 12) by the sales table's key and its outputs.
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_xw AS
SELECT 'CROSSWALK' AS part, CAST(NULL AS VARCHAR) AS item, s.source, s.sales_firm_id, s.sales_firm,
       s.old_channel AS raw_channel, s.raw_product, s.old_channel_s1, s.match_channel, c.n_candidates, c.candidates,
       s.firm_basis, s.firm_crd, s.broker_name, s.product, s.new_channel,
       SUM(s.n_rows) AS n_rows, COUNT(DISTINCT s.seller_key) AS n_sellers, COUNT(DISTINCT s.zip) AS n_zips,
       SUM(s.sales) AS sales, SUM(s.sales_alt) AS sales_alt,
       SUM(CASE WHEN s.zip IS NULL THEN s.sales ELSE 0 END) AS sales_no_zip,
       SUM(CASE WHEN s.seller_key IS NULL THEN s.sales ELSE 0 END) AS sales_no_seller,
       SUM(CASE WHEN s.cell_status = 'ON A CELL WITH OPPORTUNITY' THEN s.sales ELSE 0 END) AS sales_on_opp_cell,
       SUM(CASE WHEN s.held_old THEN s.sales ELSE 0 END) AS sales_in_held_cells_old,
       SUM(CASE WHEN s.held_new THEN s.sales ELSE 0 END) AS sales_in_held_cells_new,
       CAST(NULL AS DECIMAL(38, 6)) AS check_value
FROM ssdb_integration.lr_strategy.tmp_o2_sales s
LEFT JOIN ssdb_integration.lr_strategy.tmp_xw_cand c ON c.source = s.source AND c.firm_id = s.sales_firm_id
GROUP BY ALL;

--3. The mapping table: the crosswalk's keys and outputs, no amounts.
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_sales_map AS
WITH cb AS (SELECT firm_crd, broker_name, COUNT(DISTINCT company_id) AS n_cbd_id,
                   LISTAGG(DISTINCT company_id, ' | ') WITHIN GROUP (ORDER BY company_id) AS cbd_id
            FROM ssdb_integration.lr_strategy.tmp_o1_rows_s1
            WHERE firm_crd IS NOT NULL AND company_id IS NOT NULL
            GROUP BY ALL)
SELECT x.source, x.sales_firm_id, x.sales_firm, x.raw_channel, x.raw_product, x.firm_basis, x.firm_crd, x.broker_name,
       cb.cbd_id, cb.n_cbd_id, x.product, x.old_channel_s1, x.match_channel, x.new_channel
FROM ssdb_integration.lr_strategy.tmp_xw x
LEFT JOIN cb ON cb.firm_crd = x.firm_crd AND cb.broker_name = x.broker_name;

--4. Out of window and checks.
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_xw_checks AS
WITH
raw AS (
            SELECT 'S1' AS source, NULLIF(CAST(CAST(consol_brkr_dlr_id AS DECIMAL(38, 0)) AS VARCHAR), '0') AS firm_id,
                   consol_broker_nm AS firm, dist_ch AS channel, product_line2 AS product,
                   CAST(actual_agent_dollars AS DECIMAL(38, 6)) AS a1, CAST(compd_agent_dollars AS DECIMAL(38, 6)) AS a2
            FROM IDENTIFIER($s1_sales) WHERE fiscal_yr = 2025 AND product_bucket = 'ALL'
  UNION ALL SELECT 'S2', CAST(CAST(firm_crd AS DECIMAL(38, 0)) AS VARCHAR), firm, channel, product,
                   CAST(sales_amount AS DECIMAL(38, 6)), CAST(mm_amount AS DECIMAL(38, 6))
            FROM IDENTIFIER($s2_sales) WHERE year = 2025),
rk AS (SELECT source, COALESCE(firm_id, '(NULL)') AS k1, COALESCE(firm, '(NULL)') AS k2, COALESCE(channel, '(NULL)') AS k3,
              COALESCE(product, '(NULL)') AS k4, SUM(a1) AS a1, SUM(a2) AS a2
       FROM raw GROUP BY ALL),
xk AS (SELECT source, COALESCE(sales_firm_id, '(NULL)') AS k1, COALESCE(sales_firm, '(NULL)') AS k2,
              COALESCE(raw_channel, '(NULL)') AS k3, COALESCE(raw_product, '(NULL)') AS k4,
              SUM(sales) AS a1, SUM(sales_alt) AS a2, COUNT(*) AS n_out
       FROM ssdb_integration.lr_strategy.tmp_xw GROUP BY ALL),
kv AS (SELECT COALESCE(r.source, x.source) AS source,
              ABS(COALESCE(r.a1, 0) - COALESCE(x.a1, 0)) + ABS(COALESCE(r.a2, 0) - COALESCE(x.a2, 0)) AS d
       FROM rk r FULL OUTER JOIN xk x ON x.source = r.source AND x.k1 = r.k1 AND x.k2 = r.k2 AND x.k3 = r.k3 AND x.k4 = r.k4),
dk AS (SELECT source, COALESCE(firm_crd, '(NULL)') AS k1, COALESCE(broker_name, '(NULL)') AS k2,
              COALESCE(product, '(NULL)') AS k3, COALESCE(old_channel, '(NULL)') AS k4, COALESCE(new_channel, '(NULL)') AS k5,
              SUM(sales) AS a
       FROM ssdb_integration.lr_strategy.tmp_o2_dataset GROUP BY ALL),
ck AS (SELECT source, COALESCE(firm_crd, '(NULL)') AS k1, COALESCE(broker_name, '(NULL)') AS k2,
              COALESCE(product, '(NULL)') AS k3, COALESCE(raw_channel, '(NULL)') AS k4, COALESCE(new_channel, '(NULL)') AS k5,
              SUM(sales) AS a
       FROM ssdb_integration.lr_strategy.tmp_xw GROUP BY ALL),
dv AS (SELECT COALESCE(d.source, c.source) AS source, ABS(COALESCE(d.a, 0) - COALESCE(c.a, 0)) AS d
       FROM dk d FULL OUTER JOIN ck c ON c.source = d.source AND c.k1 = d.k1 AND c.k2 = d.k2 AND c.k3 = d.k3
                                     AND c.k4 = d.k4 AND c.k5 = d.k5),
ow AS (
            SELECT 'S1' AS source, 'FISCAL_YR ' || COALESCE(CAST(fiscal_yr AS VARCHAR), '(NULL)') || ' | BUCKET '
                   || COALESCE(product_bucket, '(NULL)') AS item, COUNT(*) AS n_rows,
                   SUM(CAST(actual_agent_dollars AS DECIMAL(38, 6))) AS a1, SUM(CAST(compd_agent_dollars AS DECIMAL(38, 6))) AS a2
            FROM IDENTIFIER($s1_sales)
            WHERE NOT EQUAL_NULL(fiscal_yr, 2025) OR NOT EQUAL_NULL(product_bucket, 'ALL')
            GROUP BY ALL
  UNION ALL SELECT 'S2', 'YEAR ' || COALESCE(CAST(year AS VARCHAR), '(NULL)'), COUNT(*),
                   SUM(CAST(sales_amount AS DECIMAL(38, 6))), SUM(CAST(mm_amount AS DECIMAL(38, 6)))
            FROM IDENTIFIER($s2_sales) WHERE NOT EQUAL_NULL(year, 2025)
            GROUP BY ALL),
whole AS (
            SELECT 'S1' AS source, SUM(CAST(actual_agent_dollars AS DECIMAL(38, 6))) AS a1 FROM IDENTIFIER($s1_sales)
  UNION ALL SELECT 'S2', SUM(CAST(sales_amount AS DECIMAL(38, 6))) FROM IDENTIFIER($s2_sales)),
c AS (
            SELECT source, 'RAW KEYS VS CROSSWALK (MUST BE 0)' AS item,
                   CAST(SUM(CASE WHEN ROUND(d, 2) <> 0 THEN 1 ELSE 0 END) AS DECIMAL(38, 6)) AS v, SUM(d) AS amt
            FROM kv GROUP BY ALL
  UNION ALL SELECT source, 'RAW KEYS ON 2+ OUTPUTS (MUST BE 0)',
                   CAST(SUM(CASE WHEN n_out > 1 THEN 1 ELSE 0 END) AS DECIMAL(38, 6)), NULL
            FROM xk GROUP BY ALL
  UNION ALL SELECT source, 'CROSSWALK VS TMP_O2_DATASET (MUST BE 0)',
                   CAST(SUM(CASE WHEN ROUND(d, 2) <> 0 THEN 1 ELSE 0 END) AS DECIMAL(38, 6)), SUM(d)
            FROM dv GROUP BY ALL
  UNION ALL SELECT w.source, 'RAW TABLE MINUS CROSSWALK AND OUT OF WINDOW (MUST BE 0)',
                   ROUND(w.a1 - COALESCE(x.a1, 0) - COALESCE(o.a1, 0), 2), NULL
            FROM whole w
            LEFT JOIN (SELECT source, SUM(sales) AS a1 FROM ssdb_integration.lr_strategy.tmp_xw GROUP BY ALL) x ON x.source = w.source
            LEFT JOIN (SELECT source, SUM(a1) AS a1 FROM ow GROUP BY ALL) o ON o.source = w.source)
SELECT 'OUT OF WINDOW' AS part, item, source, CAST(NULL AS VARCHAR) AS sales_firm_id, CAST(NULL AS VARCHAR) AS sales_firm,
       CAST(NULL AS VARCHAR) AS raw_channel, CAST(NULL AS VARCHAR) AS raw_product, CAST(NULL AS VARCHAR) AS old_channel_s1,
       CAST(NULL AS VARCHAR) AS match_channel, CAST(NULL AS BIGINT) AS n_candidates, CAST(NULL AS VARCHAR) AS candidates,
       CAST(NULL AS VARCHAR) AS firm_basis, CAST(NULL AS VARCHAR) AS firm_crd, CAST(NULL AS VARCHAR) AS broker_name,
       CAST(NULL AS VARCHAR) AS product, CAST(NULL AS VARCHAR) AS new_channel, n_rows, CAST(NULL AS BIGINT) AS n_sellers,
       CAST(NULL AS BIGINT) AS n_zips, a1 AS sales, a2 AS sales_alt, CAST(NULL AS DECIMAL(38, 6)) AS sales_no_zip,
       CAST(NULL AS DECIMAL(38, 6)) AS sales_no_seller, CAST(NULL AS DECIMAL(38, 6)) AS sales_on_opp_cell,
       CAST(NULL AS DECIMAL(38, 6)) AS sales_in_held_cells_old, CAST(NULL AS DECIMAL(38, 6)) AS sales_in_held_cells_new,
       CAST(NULL AS DECIMAL(38, 6)) AS check_value
FROM ow
UNION ALL
SELECT 'CHECKS', item, source, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL,
       NULL, amt, NULL, NULL, NULL, NULL, NULL, NULL, v
FROM c;

--5. Everything, one result set (read at work).
SELECT * FROM ssdb_integration.lr_strategy.tmp_xw
UNION ALL SELECT * FROM ssdb_integration.lr_strategy.tmp_xw_checks
ORDER BY part, source, sales DESC NULLS LAST, sales_firm_id, raw_channel, raw_product;
