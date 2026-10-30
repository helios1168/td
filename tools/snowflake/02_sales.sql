--Layer 02: sales, both sources, credited to the wholesaler who sold them, beside the opportunity each wholesaler holds
--(layer 01), at ZIP grain (DATA_MODEL.md: credit, I2; owner, 2026-10-30: "sales is tied to the actual wholesaler, not
--necessarily a cell"; "sales stay fixed to whoever actually sold"; "we also want sales at the zip grain").
--Run 01_opportunity.sql first, in the same worksheet (a temporary table lives only in the session that made it): this
--file reads its temporary tables.  It builds:
--  TMP_O2_SALES: each source's fiscal year 2025 sales, one row per seller x ZIP x the sales table's firm x product x
--    the sale's own channel, those three as the sales table has them (SALES_FIRM_ID and SALES_FIRM: firm 1's company
--    ID and name, firm 2's CRD and firm name; RAW_PRODUCT; OLD_CHANNEL), with the market metrics firm (CRD x broker
--    name) it reaches and how (FIRM_BASIS), the firm's new channel, scope, and whether the seller holds that ZIP x
--    firm x product in the old and the new state.
--  TMP_O2_DATASET: the table to look at.  One row per source x wholesaler x ZIP x firm x product x old channel x new
--    channel x scope: the opportunity the wholesaler holds there, old and new (TMP_O1_DATASET), and the sales
--    credited to them there.  Sales never move between states; only held opportunity does.  Every 2025 sale is in it,
--    so it ties to the sales tables (owner, 2026-10-30: "which we must be able to exactly replicate in this new
--    table"); SCOPE flags the firms out of scope, and an in-scope cut filters SCOPE = 'IN'.
--The last statement returns sizes, the tie-out and checks, no ID or name: download it as CSV into $TD_REPO/data/safe/.
--The decisions are the tables in 1 and the joins named in DATASET_LOG.md, Key decisions: change one and rerun.
--Snowflake docs read 2026-10-30: SPLIT_PART gives '' past the last part (.../functions/split_part); CROSS JOIN takes
--no ON (.../constructs/join); a set operator wants each column's type the same in all its inputs, so both sources'
--amounts are cast to one exact type, DECIMAL(38, 6) (.../operators-query); a temporary table exists only in the
--session that made it (.../user-guide/tables-temp-transient); GROUP BY ALL, VALUES, session variables and IDENTIFIER
--as in 01_opportunity.sql.
--TO_DATE, HAVING after GROUP BY and a comma join are s1_sales.sql's and s1_opp_sales.sql's, run at work.
use secondary roles all;

--EDIT once: the tables whose names carry a carrier (paste the SET lines from owner_sql/vars.sql).  s1_sales is the
--table owner_sql/s1_sales.sql makes with its first CREATE line and its last line uncommented.
SET s1_sales = 'ssdb_integration.lr_strategy.<source 1 base sales from s1_sales.sql, ends _BASE_SALES>';
SET s2_sales = 'ssdb_integration.lr_strategy.<source 2 sales, ends _SALES>';

--1. Decisions as tables.
--A sale's product -> the cell's product.  Source 1's are s1_sales.sql:315-317's (FIXED, SPIA/DIA, ASSURED EDGE are
--FIXED); source 2's market metrics codes as the opportunity map reads them.  Sales carry no VA type: a VA sale is
--VARIABLE, and IOVA opportunity has no sales.  A value not here keeps no product (SALES PRODUCT lists it).
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_sales_product AS
SELECT CAST(value AS VARCHAR) AS value, CAST(product AS VARCHAR) AS product
FROM (VALUES ('RILA', 'RILA'), ('INDEX', 'INDEX'), ('VARIABLE', 'VARIABLE'), ('FIXED', 'FIXED'), ('IOVA', 'IOVA'),
             ('IA', 'INDEX'), ('VA', 'VARIABLE'), ('FA', 'FIXED')) AS v (value, product);

--Source 1's sale channels in firm 1's channel names, used only to pick the firm where a company has 2+: IMO and the
--split-policy labels sell on their base channel (s1_sales.sql:18, :21, :418).  Any other label stands for itself.
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_s1_sale_channel AS
SELECT CAST(label AS VARCHAR) AS label, CAST(s1_channel AS VARCHAR) AS s1_channel
FROM (VALUES ('IMO', 'IFA'), ('IFA/IMO', 'IFA'), ('FI/IMO', 'FI')) AS v (label, s1_channel);

--2. Source 1's company ID -> the firms whose market metrics rows carry it, as layer 01 derives it from
--s1_opp_sales.sql:475-482.  A company found only inside a client firm ID list ('a|b') takes that list's firms; a
--company any row carries alone takes only those (lists of up to 10 parts: LISTS OVER 10 PARTS must be 0).
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_o2_company_firm AS
WITH
r AS (SELECT DISTINCT company_id, firm_crd, broker_name FROM ssdb_integration.lr_strategy.tmp_o1_rows_s1
      WHERE company_id IS NOT NULL AND firm_crd IS NOT NULL),
p AS (
            SELECT company_id, firm_crd, broker_name, 'DIRECT' AS how FROM r WHERE company_id NOT LIKE '%|%'
  UNION ALL SELECT NULLIF(TRIM(SPLIT_PART(r.company_id, '|', v.n)), ''), r.firm_crd, r.broker_name, 'LIST'
            FROM r, (VALUES (1), (2), (3), (4), (5), (6), (7), (8), (9), (10)) AS v (n)
            WHERE r.company_id LIKE '%|%'),
d AS (SELECT DISTINCT company_id FROM p WHERE how = 'DIRECT')
SELECT DISTINCT p.company_id, p.firm_crd, p.broker_name
FROM p LEFT JOIN d ON d.company_id = p.company_id
WHERE p.company_id IS NOT NULL AND (p.how = 'DIRECT' OR d.company_id IS NULL);

--3. Source 1's sales, fiscal year 2025, with the firm each reaches.  SALES_FIRM_ID, SALES_FIRM, RAW_PRODUCT and
--OLD_CHANNEL are the sales table's CONSOL_BRKR_DLR_ID, CONSOL_BROKER_NM, PRODUCT_LINE2 and DIST_CH as they are;
--matching reads them trimmed and upper-cased.  FIRM_BASIS: ONE FIRM (the company sits on one firm); SPLIT, MATCHED BY
--CHANNEL (2+ firms, exactly one with the sale's channel); SPLIT, 2+ CHANNEL MATCHES or NO CHANNEL MATCH (left without
--a firm: assign where unique, flag the rest); NO MARKET METRICS FIRM; NO COMPANY.
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_o2_s1 AS
WITH
s AS (SELECT *, ROW_NUMBER() OVER (ORDER BY sales DESC) AS sid FROM (
  SELECT NULLIF(CAST(CAST(consol_brkr_dlr_id AS DECIMAL(38, 0)) AS VARCHAR), '0') AS sales_firm_id,
         consol_broker_nm AS sales_firm, NULLIF(TRIM(CAST(whslr_id AS VARCHAR)), '') AS seller_key, whslr_nm AS seller,
         CASE WHEN NULLIF(TRIM(zip_cd), '') IS NULL OR TRIM(zip_cd) = 'BLANK' THEN NULL
              ELSE LPAD(LEFT(TRIM(zip_cd), 5), 5, '0') END AS zip,
         product_line2 AS raw_product, dist_ch AS old_channel, COUNT(*) AS n_rows,
         CAST(SUM(actual_agent_dollars) AS DECIMAL(38, 6)) AS sales,
         CAST(SUM(compd_agent_dollars) AS DECIMAL(38, 6)) AS sales_alt
  FROM IDENTIFIER($s1_sales)
  WHERE fiscal_yr = 2025 AND product_bucket = 'ALL'
  GROUP BY ALL) x),
sc AS (SELECT s.sid, COALESCE(m.s1_channel, UPPER(TRIM(s.old_channel))) AS s1_channel
       FROM s LEFT JOIN ssdb_integration.lr_strategy.tmp_s1_sale_channel m ON m.label = UPPER(TRIM(s.old_channel))),
c AS (SELECT s.sid, cf.firm_crd, cf.broker_name, f.route
      FROM s
      JOIN ssdb_integration.lr_strategy.tmp_o2_company_firm cf ON cf.company_id = s.sales_firm_id
      JOIN ssdb_integration.lr_strategy.tmp_o1_firm f ON f.firm_crd = cf.firm_crd AND f.broker_name = cf.broker_name),
k AS (SELECT sid, COUNT(*) AS n_firms, MIN(firm_crd) AS crd, MIN(broker_name) AS nm FROM c GROUP BY ALL),
m AS (SELECT c.sid, COUNT(*) AS n_match, MIN(c.firm_crd) AS crd, MIN(c.broker_name) AS nm
      FROM c JOIN sc ON sc.sid = c.sid WHERE c.route = sc.s1_channel GROUP BY ALL)
SELECT 'S1' AS source, s.seller_key, s.seller, s.sales_firm_id, s.sales_firm, s.zip, s.raw_product, s.old_channel,
       s.old_channel AS old_channel_s1, sc.s1_channel AS match_channel,
       CASE WHEN s.sales_firm_id IS NULL THEN 'NO COMPANY' WHEN k.sid IS NULL THEN 'NO MARKET METRICS FIRM'
            WHEN k.n_firms = 1 THEN 'ONE FIRM' WHEN m.n_match = 1 THEN 'SPLIT, MATCHED BY CHANNEL'
            WHEN m.n_match > 1 THEN 'SPLIT, 2+ CHANNEL MATCHES' ELSE 'SPLIT, NO CHANNEL MATCH' END AS firm_basis,
       CASE WHEN k.n_firms = 1 THEN k.crd WHEN m.n_match = 1 THEN m.crd END AS firm_crd,
       CASE WHEN k.n_firms = 1 THEN k.nm WHEN m.n_match = 1 THEN m.nm END AS broker_name,
       s.n_rows, s.sales, s.sales_alt
FROM s
JOIN sc ON sc.sid = s.sid
LEFT JOIN k ON k.sid = s.sid
LEFT JOIN m ON m.sid = s.sid;

--4. Source 2's sales, YEAR 2025, with the firm each reaches: its CRD's one broker name (TMP_O1_FIRM holds every
--CRD x broker name either source's opportunity carries), or on a CRD with 2+, the one whose firm 1 channel is the
--sale's: CHANNEL through Q19 (or a territory code as is), then Q39 read back, which is also OLD_CHANNEL_S1.
--SALES_FIRM_ID, SALES_FIRM, RAW_PRODUCT and OLD_CHANNEL are FIRM_CRD, FIRM, PRODUCT and CHANNEL as they are; each
--amount (a FLOAT) is cast to DECIMAL(38, 6) before it is summed.  FIRM_BASIS as in 3, NO CRD for none.
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_o2_s2 AS
WITH
q39 AS (SELECT terr_channel, MIN(s1_channel) AS s1_channel FROM ssdb_integration.lr_strategy.tmp_s1ch_s2terr GROUP BY ALL),
s AS (SELECT *, ROW_NUMBER() OVER (ORDER BY sales DESC) AS sid FROM (
  SELECT CAST(CAST(firm_crd AS DECIMAL(38, 0)) AS VARCHAR) AS sales_firm_id, firm AS sales_firm,
         NULLIF(UPPER(TRIM(rvp)), '') AS seller_key, rvp AS seller,
         CASE WHEN NULLIF(TRIM(zip_code), '') IS NULL THEN NULL ELSE LPAD(LEFT(TRIM(zip_code), 5), 5, '0') END AS zip,
         product AS raw_product, channel AS old_channel, COUNT(*) AS n_rows,
         SUM(CAST(sales_amount AS DECIMAL(38, 6))) AS sales, SUM(CAST(mm_amount AS DECIMAL(38, 6))) AS sales_alt
  FROM IDENTIFIER($s2_sales)
  WHERE year = 2025
  GROUP BY ALL) x),
sc AS (SELECT s.sid, COALESCE(qa.s1_channel, qb.s1_channel) AS s1_channel
       FROM s
       LEFT JOIN ssdb_integration.lr_strategy.tmp_s2_label_terr lt ON lt.label = UPPER(TRIM(s.old_channel))
       LEFT JOIN q39 qa ON qa.terr_channel = lt.terr_channel
       LEFT JOIN q39 qb ON qb.terr_channel = UPPER(TRIM(s.old_channel))),
c AS (SELECT s.sid, f.firm_crd, f.broker_name, f.route
      FROM s JOIN ssdb_integration.lr_strategy.tmp_o1_firm f ON f.firm_crd = s.sales_firm_id),
k AS (SELECT sid, COUNT(*) AS n_firms, MIN(firm_crd) AS crd, MIN(broker_name) AS nm FROM c GROUP BY ALL),
m AS (SELECT c.sid, COUNT(*) AS n_match, MIN(c.firm_crd) AS crd, MIN(c.broker_name) AS nm
      FROM c JOIN sc ON sc.sid = c.sid WHERE c.route = sc.s1_channel GROUP BY ALL)
SELECT 'S2' AS source, s.seller_key, s.seller, s.sales_firm_id, s.sales_firm, s.zip, s.raw_product, s.old_channel,
       sc.s1_channel AS old_channel_s1, sc.s1_channel AS match_channel,
       CASE WHEN s.sales_firm_id IS NULL THEN 'NO CRD' WHEN k.sid IS NULL THEN 'NO MARKET METRICS FIRM'
            WHEN k.n_firms = 1 THEN 'ONE FIRM' WHEN m.n_match = 1 THEN 'SPLIT, MATCHED BY CHANNEL'
            WHEN m.n_match > 1 THEN 'SPLIT, 2+ CHANNEL MATCHES' ELSE 'SPLIT, NO CHANNEL MATCH' END AS firm_basis,
       CASE WHEN k.n_firms = 1 THEN k.crd WHEN m.n_match = 1 THEN m.crd END AS firm_crd,
       CASE WHEN k.n_firms = 1 THEN k.nm WHEN m.n_match = 1 THEN m.nm END AS broker_name,
       s.n_rows, s.sales, s.sales_alt
FROM s
JOIN sc ON sc.sid = s.sid
LEFT JOIN k ON k.sid = s.sid
LEFT JOIN m ON m.sid = s.sid;

--5. Both sources' sales with the firm's new channel and scope (a firm out, or source 1's company out), where the sale
--lands (CELL_STATUS: on a ZIP x firm x product of TMP_O1_DATASET or why not), and whether its seller holds that cell
--in the old and the new state (source 1 by wholesaler ID, source 2 by RVP: its territory IDs are seats, not people).
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_o2_sales AS
WITH
u AS (SELECT * FROM ssdb_integration.lr_strategy.tmp_o2_s1 UNION ALL SELECT * FROM ssdb_integration.lr_strategy.tmp_o2_s2),
h AS (SELECT DISTINCT source, zip, firm_crd, broker_name, product,
             CASE WHEN source = 'S1' THEN TRIM(old_wholesaler_id) ELSE UPPER(TRIM(old_wholesaler)) END AS old_key,
             CASE WHEN source = 'S1' THEN TRIM(new_wholesaler_id) ELSE UPPER(TRIM(new_wholesaler)) END AS new_key
      FROM ssdb_integration.lr_strategy.tmp_o1_dataset),
cell AS (SELECT DISTINCT source, zip, firm_crd, broker_name, product FROM h),
ho AS (SELECT DISTINCT source, zip, firm_crd, broker_name, product, old_key AS w FROM h WHERE old_key IS NOT NULL),
hn AS (SELECT DISTINCT source, zip, firm_crd, broker_name, product, new_key AS w FROM h WHERE new_key IS NOT NULL)
SELECT u.source, u.seller_key, u.seller, u.sales_firm_id, u.sales_firm, u.zip, u.raw_product, p.product,
       u.old_channel, u.old_channel_s1, u.match_channel, u.firm_basis, u.firm_crd, u.broker_name,
       COALESCE(f.new_label, 'UNMAPPED') AS new_channel, COALESCE(f.scope_out, so.label) AS scope_out,
       CASE WHEN u.firm_crd IS NULL THEN 'NO FIRM' WHEN u.zip IS NULL THEN 'NO ZIP' WHEN p.product IS NULL THEN 'NO PRODUCT'
            WHEN ce.source IS NULL THEN 'NO OPPORTUNITY CELL' ELSE 'ON A CELL WITH OPPORTUNITY' END AS cell_status,
       ho.w IS NOT NULL AS held_old, hn.w IS NOT NULL AS held_new, u.n_rows, u.sales, u.sales_alt
FROM u
LEFT JOIN ssdb_integration.lr_strategy.tmp_sales_product p ON p.value = UPPER(TRIM(u.raw_product))
LEFT JOIN ssdb_integration.lr_strategy.tmp_o1_firm f ON f.firm_crd = u.firm_crd AND f.broker_name = u.broker_name
LEFT JOIN ssdb_integration.lr_strategy.tmp_scope_out so
  ON so.kind = 'COMPANY' AND so.value = u.sales_firm_id AND u.source = 'S1'
LEFT JOIN cell ce ON ce.source = u.source AND ce.zip = u.zip AND ce.firm_crd = u.firm_crd
                 AND ce.broker_name = u.broker_name AND ce.product = p.product
LEFT JOIN ho ON ho.source = u.source AND ho.zip = u.zip AND ho.firm_crd = u.firm_crd
               AND ho.broker_name = u.broker_name AND ho.product = p.product AND ho.w = u.seller_key
LEFT JOIN hn ON hn.source = u.source AND hn.zip = u.zip AND hn.firm_crd = u.firm_crd
               AND hn.broker_name = u.broker_name AND hn.product = p.product AND hn.w = u.seller_key;

--6. The dataset: every 2025 sale and the in-scope opportunity (TMP_O1_DATASET), each under its wholesaler.
--OLD_CHANNEL: on opportunity, the cell's old channel (TMP_O1_DATASET); on sales, the sale's own channel as its sales
--table has it (firm 1's DIST_CH), so SUM(SALES) for a cut on PRODUCT and OLD_CHANNEL is the sales table's for the same
--cut on its product (PRODUCT_LINE2 maps 1 : 1) and channel (owner, 2026-10-30: "I want to validate against the
--original dist_ch").  A sale shares a row with its cell's opportunity where the two old channels agree.
--OLD_CHANNEL_S1: firm 1's is OLD_CHANNEL; firm 2's is in firm 1's names (Q19, then Q39 read back).  SCOPE: 'IN', or
--'OUT: <label>' on sales of a firm out of scope (TMP_O1_DATASET has only in-scope opportunity).  OPP_HELD_OLD,
--OPP_HELD_NEW: TMP_O1_DATASET's opportunity under its old and its new wholesaler.  SALES: credited to the seller (firm
--1's actual sales, firm 2's SALES_AMOUNT); SALES_ALT: firm 1's comp'd sales, firm 2's MM_AMOUNT (Q42).
--SALES_IN_HELD_CELLS_OLD and _NEW: the part of SALES whose seller holds that ZIP x firm x product in that state.
--WHOLESALER_KEY: firm 1's wholesaler ID, firm 2's RVP.  No key: opportunity no one holds, or sales with no seller.
--Sales with no market metrics firm sit under a blank firm, new channel UNMAPPED; TMP_O2_SALES has their sales table's
--firm.
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_o2_dataset AS
WITH
ds AS (SELECT source, zip, firm_crd, broker_name, product, old_channel, old_channel_s1, new_channel, opportunity,
              CASE WHEN source = 'S1' THEN TRIM(old_wholesaler_id) ELSE UPPER(TRIM(old_wholesaler)) END AS old_key,
              old_wholesaler AS old_nm,
              CASE WHEN source = 'S1' THEN TRIM(new_wholesaler_id) ELSE UPPER(TRIM(new_wholesaler)) END AS new_key,
              new_wholesaler AS new_nm
       FROM ssdb_integration.lr_strategy.tmp_o1_dataset),
f AS (
            SELECT source, old_key AS w_key, old_nm AS w_nm, zip, firm_crd, broker_name, product, old_channel,
                   old_channel_s1, new_channel, CAST('IN' AS VARCHAR) AS scope, opportunity AS opp_old, 0 AS opp_new,
                   0 AS sales, 0 AS sales_alt, 0 AS held_old, 0 AS held_new
            FROM ds
  UNION ALL SELECT source, new_key, new_nm, zip, firm_crd, broker_name, product, old_channel, old_channel_s1,
                   new_channel, 'IN', 0, opportunity, 0, 0, 0, 0
            FROM ds
  UNION ALL SELECT source, seller_key, seller, zip, firm_crd, broker_name, product, old_channel, old_channel_s1,
                   new_channel, CASE WHEN scope_out IS NULL THEN 'IN' ELSE 'OUT: ' || scope_out END, 0, 0, sales,
                   sales_alt, CASE WHEN held_old THEN sales ELSE 0 END, CASE WHEN held_new THEN sales ELSE 0 END
            FROM ssdb_integration.lr_strategy.tmp_o2_sales)
SELECT source, w_key AS wholesaler_key, MIN(w_nm) AS wholesaler, zip, firm_crd, broker_name, product, old_channel,
       old_channel_s1, new_channel, scope, SUM(opp_old) AS opp_held_old, SUM(opp_new) AS opp_held_new, SUM(sales) AS sales, SUM(sales_alt) AS sales_alt,
       SUM(held_old) AS sales_in_held_cells_old, SUM(held_new) AS sales_in_held_cells_new
FROM f
GROUP BY ALL;

--7. Sizes, the tie-out and checks, one table; AMT is sales $ unless the name says otherwise.  PCT_AMT: of PART x
--SOURCE x NAME.
--  SALES FIRM BASIS, SALES SCOPE, SALES PRODUCT (value -> product), SALES CHANNEL (the sale's channel -> the firm 1
--    channel that picks its firm): all of a source's 2025 sales.  SALES ON CELLS: in scope; CELL, and SOLD BY THE
--    CELL'S HOLDER (old, new).  Q35: source 1's sales by how MM_MAP and CRD_TO_CBD map their company ID against the
--    firm found here.  SALES PERIOD: each sales table by year, firm 1's also by product bucket (s1_sales.sql keeps only
--    ALL, :439), before the 2025 filter.  WHOLESALERS: per source and state, in scope, wholesalers (N_WHOLESALERS) that
--    hold opportunity and sell, sell holding none, hold some with no sales; AMT their sales.
--  TIE-OUT: the owner's cut of firm 1's sales (PRODUCT_LINE2 <> 'FIXED' AND DIST_CH IN ('WH', 'FI', 'IFA')), actual and
--    comp'd: the sales table by fiscal year, and TMP_O2_DATASET's 2025 by SCOPE (PRODUCT, OLD_CHANNEL).
--  CHECKS (MUST BE 0): source 1's sales table against SLS_RPT_DETAIL under s1_sales.sql's row filters (:117-126) and
--    non-zero policies (:137-148), fiscal year 2025; each sales table against TMP_O2_SALES by firm x channel x product
--    as the sales table has them (N_ROWS: groups that differ; AMT: their $); the tie-out, sales table minus dataset;
--    the dataset's opportunity and sales against their sources; company lists over 10 parts.
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_o2_out AS
WITH
s AS (SELECT * FROM ssdb_integration.lr_strategy.tmp_o2_sales),
b AS (SELECT policy_no, fiscal_yr, actual_sales_amount, sales_amount
      FROM life_prod.lif_murkylake.sls_rpt_detail
      WHERE TO_DATE(sales_date) BETWEEN '2024-01-01' AND '2025-12-31'
        AND bonus_rate <> 0 AND init_pay_in = 'Y' AND consol_brkr_dlr_id <> '342'
        AND life70_co_cd NOT IN ('VV', 'VB') AND agent_tax_id IS NOT NULL
        AND product_line IN ('RILA', 'INDEX', 'VARIABLE', 'ASSURED EDGE', 'FIXED', 'SPIA/DIA')),
nz AS (SELECT policy_no FROM b GROUP BY policy_no HAVING SUM(sales_amount) <> 0),
raw1 AS (SELECT SUM(b.actual_sales_amount) AS act, SUM(b.sales_amount) AS comp
         FROM b JOIN nz ON nz.policy_no = b.policy_no WHERE b.fiscal_yr = 2025),
base1 AS (SELECT SUM(actual_agent_dollars) AS act, SUM(compd_agent_dollars) AS comp
          FROM IDENTIFIER($s1_sales) WHERE fiscal_yr = 2025 AND product_bucket = 'ALL'),
maps AS (
            SELECT 'MM_MAP' AS map, CAST(CAST(CASE WHEN cbd_id = 0 THEN firm_client_id ELSE cbd_id END AS DECIMAL(38, 0))
                                         AS VARCHAR) AS company_id, CAST(CAST(firm_crd AS DECIMAL(38, 0)) AS VARCHAR) AS crd
            FROM ssdb_integration.lr_strategy.mm_map
  UNION ALL SELECT 'CRD_TO_CBD', CAST(CAST(cbd_id AS DECIMAL(38, 0)) AS VARCHAR), CAST(CAST(firm_crd AS DECIMAL(38, 0)) AS VARCHAR)
            FROM ssdb_integration.lr_strategy.crd_to_cbd),
mk AS (SELECT map, company_id, COUNT(DISTINCT crd) AS k, MIN(crd) AS crd FROM maps
       WHERE company_id IS NOT NULL AND crd IS NOT NULL GROUP BY ALL),
mn AS (SELECT DISTINCT map FROM maps),
dw AS (SELECT source, wholesaler_key, SUM(opp_held_old) AS o_old, SUM(opp_held_new) AS o_new, SUM(sales) AS sl
       FROM ssdb_integration.lr_strategy.tmp_o2_dataset WHERE wholesaler_key IS NOT NULL AND scope = 'IN' GROUP BY ALL),
tb AS (SELECT CAST(fiscal_yr AS VARCHAR) AS fy, COUNT(*) AS n, SUM(actual_agent_dollars) AS act,
              SUM(compd_agent_dollars) AS comp
       FROM IDENTIFIER($s1_sales)
       WHERE product_bucket = 'ALL' AND product_line2 <> 'FIXED' AND dist_ch IN ('WH', 'FI', 'IFA')
       GROUP BY ALL),
td AS (SELECT scope, SUM(sales) AS act, SUM(sales_alt) AS comp FROM ssdb_integration.lr_strategy.tmp_o2_dataset
       WHERE source = 'S1' AND product <> 'FIXED' AND old_channel IN ('WH', 'FI', 'IFA') GROUP BY ALL),
am AS (SELECT * FROM (VALUES ('ACTUAL'), ('COMP''D')) AS x (amount)),
gd AS (SELECT source, firm_id, channel, product, SUM(a1) AS d1, SUM(a2) AS d2 FROM (
            SELECT 'S1' AS source, NULLIF(CAST(CAST(consol_brkr_dlr_id AS DECIMAL(38, 0)) AS VARCHAR), '0') AS firm_id,
                   dist_ch AS channel, product_line2 AS product, CAST(actual_agent_dollars AS DECIMAL(38, 6)) AS a1,
                   CAST(compd_agent_dollars AS DECIMAL(38, 6)) AS a2
            FROM IDENTIFIER($s1_sales) WHERE fiscal_yr = 2025 AND product_bucket = 'ALL'
  UNION ALL SELECT 'S2', CAST(CAST(firm_crd AS DECIMAL(38, 0)) AS VARCHAR), channel, product,
                   CAST(sales_amount AS DECIMAL(38, 6)), CAST(mm_amount AS DECIMAL(38, 6))
            FROM IDENTIFIER($s2_sales) WHERE year = 2025
  UNION ALL SELECT source, sales_firm_id, old_channel, raw_product, -sales, -sales_alt
            FROM ssdb_integration.lr_strategy.tmp_o2_sales) x
       GROUP BY ALL),
v AS (
            SELECT 'SALES FIRM BASIS' AS part, source, CAST(NULL AS VARCHAR) AS name, firm_basis AS item,
                   seller_key, firm_crd, broker_name, n_rows, sales AS amt
            FROM s
  UNION ALL SELECT 'SALES SCOPE', source, NULL, CASE WHEN scope_out IS NULL THEN 'IN' ELSE 'OUT: ' || scope_out END,
                   seller_key, firm_crd, broker_name, n_rows, sales FROM s
  UNION ALL SELECT 'SALES PRODUCT', source, NULL, COALESCE(raw_product, '(BLANK)') || ' -> ' || COALESCE(product, 'UNMAPPED'),
                   seller_key, firm_crd, broker_name, n_rows, sales FROM s
  UNION ALL SELECT 'SALES CHANNEL', source, NULL,
                   COALESCE(old_channel, '(BLANK)') || ' -> ' || COALESCE(match_channel, '(NONE)'),
                   seller_key, firm_crd, broker_name, n_rows, sales FROM s
  UNION ALL SELECT 'SALES ON CELLS', source, 'CELL', cell_status, seller_key, firm_crd, broker_name, n_rows, sales
            FROM s WHERE scope_out IS NULL
  UNION ALL SELECT 'SALES ON CELLS', source, 'SOLD BY THE CELL''S HOLDER, OLD', CASE WHEN held_old THEN 'YES' ELSE 'NO' END,
                   seller_key, firm_crd, broker_name, n_rows, sales FROM s WHERE scope_out IS NULL
  UNION ALL SELECT 'SALES ON CELLS', source, 'SOLD BY THE CELL''S HOLDER, NEW', CASE WHEN held_new THEN 'YES' ELSE 'NO' END,
                   seller_key, firm_crd, broker_name, n_rows, sales FROM s WHERE scope_out IS NULL
  UNION ALL SELECT 'Q35', s.source, mn.map,
                   CASE WHEN mk.company_id IS NULL THEN 'NOT IN THE MAP' WHEN mk.k > 1 THEN 'MAP: 2+ CRDS'
                        WHEN s.firm_crd IS NULL THEN 'MAP: ONE CRD, NONE FOUND HERE'
                        WHEN mk.crd = s.firm_crd THEN 'MAP: ONE CRD, THE SAME' ELSE 'MAP: ONE CRD, ANOTHER' END,
                   s.seller_key, s.firm_crd, s.broker_name, s.n_rows, s.sales
            FROM s CROSS JOIN mn LEFT JOIN mk ON mk.map = mn.map AND mk.company_id = s.sales_firm_id
            WHERE s.source = 'S1')
SELECT part, source, name, item, SUM(n_rows) AS n_rows, COUNT(DISTINCT seller_key) AS n_wholesalers,
       COUNT(DISTINCT firm_crd || '|' || broker_name) AS n_firms, SUM(amt) AS amt
FROM v GROUP BY ALL
UNION ALL
SELECT 'SALES PERIOD', 'S1', NULL, CAST(fiscal_yr AS VARCHAR) || ' | ' || COALESCE(product_bucket, '(BLANK)'), COUNT(*),
       NULL, NULL, SUM(actual_agent_dollars)
FROM IDENTIFIER($s1_sales) GROUP BY ALL
UNION ALL
SELECT 'SALES PERIOD', 'S2', NULL, CAST(year AS VARCHAR), COUNT(*), NULL, NULL, SUM(sales_amount)
FROM IDENTIFIER($s2_sales) GROUP BY ALL
UNION ALL
SELECT 'WHOLESALERS', source, st,
       CASE WHEN o <> 0 AND sl <> 0 THEN 'HOLDS OPPORTUNITY AND SELLS' WHEN sl <> 0 THEN 'SELLS, HOLDS NO OPPORTUNITY'
            WHEN o <> 0 THEN 'HOLDS OPPORTUNITY, NO SALES' ELSE 'NEITHER' END,
       NULL, COUNT(*), NULL, SUM(sl)
FROM (          SELECT source, 'OLD' AS st, o_old AS o, sl FROM dw
      UNION ALL SELECT source, 'NEW', o_new, sl FROM dw) x
GROUP BY ALL
UNION ALL
SELECT 'TIE-OUT', 'S1', 'SALES TABLE: PRODUCT_LINE2 <> FIXED, DIST_CH IN (WH, FI, IFA), ' || am.amount, tb.fy, tb.n,
       NULL, NULL, CASE WHEN am.amount = 'ACTUAL' THEN tb.act ELSE tb.comp END
FROM tb CROSS JOIN am
UNION ALL
SELECT 'TIE-OUT', 'S1', 'DATASET 2025: PRODUCT <> FIXED, OLD_CHANNEL IN (WH, FI, IFA), ' || am.amount, td.scope, NULL,
       NULL, NULL, CASE WHEN am.amount = 'ACTUAL' THEN td.act ELSE td.comp END
FROM td CROSS JOIN am
UNION ALL
SELECT 'CHECKS', 'S1', 'TIE-OUT: SALES TABLE MINUS DATASET, 2025, ACTUAL + COMP''D (MUST BE 0)', NULL, NULL, NULL, NULL,
       ROUND(ABS(COALESCE(t.act, 0) - COALESCE(d.act, 0)) + ABS(COALESCE(t.comp, 0) - COALESCE(d.comp, 0)), 2)
FROM (SELECT SUM(act) AS act, SUM(comp) AS comp FROM tb WHERE fy = '2025') t
CROSS JOIN (SELECT SUM(act) AS act, SUM(comp) AS comp FROM td) d
UNION ALL
SELECT 'CHECKS', source, 'SALES TABLE MINUS TMP_O2_SALES BY FIRM X CHANNEL X PRODUCT, 2025 (MUST BE 0)', NULL,
       SUM(CASE WHEN ROUND(COALESCE(d1, 0), 2) <> 0 OR ROUND(COALESCE(d2, 0), 2) <> 0 THEN 1 ELSE 0 END), NULL, NULL,
       ROUND(SUM(ABS(COALESCE(d1, 0)) + ABS(COALESCE(d2, 0))), 2)
FROM gd GROUP BY ALL
UNION ALL
SELECT 'CHECKS', 'S1', 'SALES TABLE MINUS SLS_RPT_DETAIL, 2025 ACTUAL (MUST BE 0)', NULL, NULL, NULL, NULL,
       ROUND(base1.act - raw1.act, 2) FROM base1 CROSS JOIN raw1
UNION ALL
SELECT 'CHECKS', 'S1', 'SALES TABLE MINUS SLS_RPT_DETAIL, 2025 COMP''D (MUST BE 0)', NULL, NULL, NULL, NULL,
       ROUND(base1.comp - raw1.comp, 2) FROM base1 CROSS JOIN raw1
UNION ALL
SELECT 'CHECKS', o.source, 'DATASET OPPORTUNITY MINUS TMP_O1_DATASET, OLD | NEW (MUST BE 0)', NULL, NULL, NULL, NULL,
       ROUND(ABS(o.o_old - o.opp) + ABS(o.o_new - o.opp), 2)
FROM (SELECT d.source, d.o_old, d.o_new, t.opp
      FROM (SELECT source, SUM(opp_held_old) AS o_old, SUM(opp_held_new) AS o_new
            FROM ssdb_integration.lr_strategy.tmp_o2_dataset GROUP BY ALL) d
      JOIN (SELECT source, SUM(opportunity) AS opp FROM ssdb_integration.lr_strategy.tmp_o1_dataset GROUP BY ALL) t
        ON t.source = d.source) o
UNION ALL
SELECT 'CHECKS', d.source, 'DATASET SALES MINUS TMP_O2_SALES (MUST BE 0)', NULL, NULL, NULL, NULL, ROUND(d.sl - t.sl, 2)
FROM (SELECT source, SUM(sales) AS sl FROM ssdb_integration.lr_strategy.tmp_o2_dataset GROUP BY ALL) d
JOIN (SELECT source, SUM(sales) AS sl FROM ssdb_integration.lr_strategy.tmp_o2_sales GROUP BY ALL) t
  ON t.source = d.source
UNION ALL
SELECT 'CHECKS', 'S1', 'COMPANY LISTS OVER 10 PARTS (MUST BE 0)', NULL, NULL, NULL, NULL, COUNT(*)
FROM ssdb_integration.lr_strategy.tmp_o1_rows_s1 WHERE SPLIT_PART(company_id, '|', 11) <> '';

--8. Everything, one result set: download as CSV.
SELECT part, source, name, item, n_rows, n_wholesalers, n_firms, amt,
       ROUND(100.0 * amt / NULLIF(SUM(amt) OVER (PARTITION BY part, source, name), 0), 2) AS pct_amt
FROM ssdb_integration.lr_strategy.tmp_o2_out
ORDER BY part, source, name, amt DESC NULLS LAST, item;
