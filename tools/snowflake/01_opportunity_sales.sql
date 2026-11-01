use role rl_ssdb_Integration_Lr_Strategy_Rw;
use database ssdb_Integration;
use schema lr_strategy;

--Layers 01 and 02 in one Run All file (owner, 2026-10-30: "combine the opp and sales query into a single query").
--Statements 1-7, opportunity routed by firm, both sources (DATA_MODEL.md, Opportunity routed by firm; views 1, 2a, 2b,
--3): M_s, p, d, kappa_s, nu_D (re-keyed to CRD x broker name), nu, tau_s, H_s with k_s (the lowest ID).  Statements
--8-14, sales credited to the wholesaler who sold them, beside the opportunity each wholesaler holds, at ZIP grain
--(DATA_MODEL.md: credit, I2; owner, 2026-10-30: "sales is tied to the actual wholesaler, not necessarily a cell";
--"sales stay fixed to whoever actually sold"; "we also want sales at the zip grain").
--Builds temporary tables (owner, 2026-10-30: "create them as temporary tables for now"), queried in the same session:
--  TMP_O1_FIRM: one row per CRD x broker name either source carries: firm 1's route, how it was found, the new label
--    (the new-channel list re-keyed from company IDs), the holder channel in the new state (TAU).
--  TMP_O1_CELLS_S1, TMP_O1_CELLS_S2: one row per ZIP x CRD x broker name x product x current label, fiscal year 2025:
--    the opportunity, the current label, territory channel and holder, the new label, territory channel and holder.
--    Holders are IDs (wholesaler ID, territory ID), the lowest where 2+ hold (N_HOLDERS says how many).
--  TMP_O1_DATASET: every opportunity cell, both sources stacked, with the wholesalers' names (statement 6 shows a
--    query).
--  TMP_O2_SALES: each source's fiscal year 2025 sales, one row per seller x ZIP x the sales table's firm x product x
--    the sale's own channel, those three as the sales table has them (SALES_FIRM_ID and SALES_FIRM: firm 1's company
--    ID and name, firm 2's CRD and firm name; RAW_PRODUCT; OLD_CHANNEL), with the market metrics firm (CRD x broker
--    name) it reaches and how (FIRM_BASIS), the firm's new channel, and whether the seller holds that ZIP x firm x
--    product in the old and the new state.  Firm 1's rows are also per MGA_AGENT_CD (blank for firm 2); TMP_O2_DATASET
--    sums over it.
--  TMP_SALES_REVIEW: every sale still without a firm, with its candidate firms ranked: the list for manual
--    assignments (statement 8, tmp_sales_firm_override).
--  TMP_O2_DATASET: the table to look at.  One row per source x wholesaler x ZIP x firm x product x old channel x new
--    channel: the opportunity the wholesaler holds there, old and new (TMP_O1_DATASET), and the sales credited to
--    them there.  Sales never move between states; only held opportunity does.  Every 2025 sale and every
--    opportunity cell is in it, so it ties to the sales tables (owner, 2026-10-30: "which we must be able to exactly
--    replicate in this new table") and is the one master table (owner, 2026-10-30: "a single master table across all
--    cases which we then filter down afterwards").
--  DATA_WITHNEWCHANNEL_UNION_W_JOINKEYS_V2: the one permanent table, the Tableau table rebuilt (statement 17).
--EDJ, AMER and AFS are channels like the others: EDJ and AMER come from firm 1's rules (old and new), AFS from the
--new-channel list (new only); a cut without them filters NEW_CHANNEL (owner, 2026-10-30: "should edj, amer, and afs
--just be considered like their own channels?").
--The last statement returns, under LAYER (OPPORTUNITY, REVIEW, SALES, TABLEAU), views 1, 2a, 2b, 3 summed by label, the sales sizes,
--the tie-out and the checks: no ID or name.  Download it as CSV into $TD_REPO/data/safe/.  The decisions are the
--tables in 1 and 8 and the joins named in DATASET_LOG.md, Key decisions: change one and rerun.
--Snowflake docs read 2026-10-30: GROUP BY ALL (https://docs.snowflake.com/en/sql-reference/constructs/group-by), VALUES
--with column aliases (.../constructs/values), EQUAL_NULL, NULL-safe equality (.../functions/equal_null), session variables
--and IDENTIFIER (.../session-variables, .../identifier-literal); SPLIT_PART gives '' past the last part
--(.../functions/split_part); CROSS JOIN takes no ON (.../constructs/join); a set operator wants each column's type the
--same in all its inputs, so both sources' sales amounts are cast to one exact type, DECIMAL(38, 6)
--(.../operators-query); a temporary table exists only in the session that made it
--(.../user-guide/tables-temp-transient).  A comma join is s1_opp_sales.sql's, run at work.  Firm 1's sales are read only
--through the base sales table (no SLS_RPT_DETAIL or MGA tables: the owner has no access; owner, 2026-10-31).
use secondary roles all;

--EDIT once: the tables whose names carry a carrier (paste the SET lines from owner_sql/vars.sql).  A name left as <...>
--fails loudly.
SET s1_territories = 'ssdb_integration.lr_strategy.<source 1 territories, ends _TERRITORIES>';
SET s2_opp         = 'ssdb_integration.lr_strategy.<source 2 opportunity, ends _OPP_ORIGINAL>';
SET s2_territories = 'ssdb_integration.lr_strategy.<source 2 territories, ends _TERRITORIES>';
--s1_sales is the table owner_sql/s1_sales.sql makes with its first CREATE line and its last line uncommented.
SET s1_sales       = 'ssdb_integration.lr_strategy.<source 1 base sales from s1_sales.sql, ends _BASE_SALES>';
SET s2_sales       = 'ssdb_integration.lr_strategy.<source 2 sales, ends _SALES>';
--The SOURCE label each firm has in the Tableau table, data_withnewchannel_union_w_joinkeys (statement 17).
SET s1_source      = '<source 1 label in the Tableau table>';
SET s2_source      = '<source 2 label in the Tableau table>';

--1. Rules and decisions as tables.  The first three are profile.sql's, row for row (the test compares them).
--Firm 1's channel rules, s1_opp_sales.sql:459-470 (sha256 6262e2f93bbd...): a row matches on the one column it fills;
--the lowest RULE_ORDER that matches wins.
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_s1_channel_rule AS
SELECT CAST(rule_order AS INTEGER) AS rule_order, CAST(cbd_id AS VARCHAR) AS cbd_id,
       CAST(broker_name AS VARCHAR) AS broker_name, CAST(dist_ch AS VARCHAR) AS dist_ch, CAST(channel AS VARCHAR) AS channel
FROM (VALUES
  (1, '1993', NULL, NULL, 'PRI'),
  (1, '685', NULL, NULL, 'PRI'),
  (2, '805', NULL, NULL, 'AMER'),
  (3, NULL, 'WELLS FARGO CLEARING SERVICES, LLC', NULL, 'WH'),
  (3, NULL, 'FIRST COMMAND BROKERAGE SERVICES, INC.', NULL, 'WH'),
  (4, NULL, 'MERCER ALLIED COMPANY, L.P.', NULL, 'IFA'),
  (5, NULL, 'TD SECURITIES (USA) LLC', NULL, 'FI'),
  (5, NULL, 'WOODMEN FINANCIAL SERVICES, INC.', NULL, 'FI'),
  (5, NULL, 'UNITED BROKERAGE SERVICES, INC', NULL, 'FI'),
  (5, NULL, 'FROST BROKERAGE SERVICES, INC.', NULL, 'FI'),
  (6, NULL, NULL, 'EDWARD JONES', 'EDJ')
) AS v (rule_order, cbd_id, broker_name, dist_ch, channel);

--Q19: source 2's own label -> its territory channel (current-state holders); KEEP_NEW FALSE drops the label's rows
--from the new state.
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_s2_label_terr AS
SELECT CAST(label AS VARCHAR) AS label, CAST(terr_channel AS VARCHAR) AS terr_channel, CAST(keep_new AS BOOLEAN) AS keep_new
FROM (VALUES
  ('BANK', 'BK', TRUE),
  ('INDEPENDENT', 'FP', TRUE),
  ('REGIONAL', 'BD', TRUE),
  ('REGIONAL AGENCY', 'RA', TRUE),
  ('NO CHANNEL', NULL, TRUE)
) AS v (label, terr_channel, keep_new);

--Q39: firm 1's channel -> the source 2 territory channel that holds it in the new state.
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_s1ch_s2terr AS
SELECT CAST(s1_channel AS VARCHAR) AS s1_channel, CAST(terr_channel AS VARCHAR) AS terr_channel
FROM (VALUES
  ('IFA', 'FP'),
  ('FI', 'BK'),
  ('WH', 'BD'),
  ('PRI', 'RA')
) AS v (s1_channel, terr_channel);

--Company ID by broker name, s1_opp_sales.sql:475-479: these names take this ID whatever the row carries; otherwise
--company 0 takes the client firm ID, as the query's ORIGINAL_CBD_ID does.
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_s1_company_by_name AS
SELECT CAST(broker_name AS VARCHAR) AS broker_name, CAST(company_id AS VARCHAR) AS company_id
FROM (VALUES
  ('WELLS FARGO CLEARING SERVICES, LLC', '1822'),
  ('WELLS FARGO CLEARING SERVICES, LLC - BANK', '1823'),
  ('CETERA INVESTMENT SERVICES LLC', '46'),
  ('LPL FINANCIAL LLC - INDEPENDENT', '8'),
  ('LPL FINANCIAL LLC - BANK', '8'),
  ('LPL FINANCIAL LLC', '8')
) AS v (broker_name, company_id);

--The new-channel list (nu_D), s1_opp_sales.sql:703-706, by company ID; a firm (CRD x broker name) takes the label if
--its source 1 rows carry the ID.  HOLDER_CHANNEL: the firm 1 channel whose holder keeps it in the new state (Q29,
--owner 2026-10-30); AFS has none: its new-state holder is not decided (Q44).
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_new_label AS
SELECT CAST(company_id AS VARCHAR) AS company_id, CAST(new_label AS VARCHAR) AS new_label,
       CAST(holder_channel AS VARCHAR) AS holder_channel
FROM (VALUES
  ('57', 'National (Chase)', 'FI'),
  ('1967', 'National (Chase)', 'FI'),
  ('1822', 'Wells WH', 'WH'),
  ('14', 'Wells WH', 'WH'),
  ('1823', 'Wells FI', 'FI'),
  ('438', 'AFS', NULL)
) AS v (company_id, new_label, holder_channel);

--The owner's firm channels: a CRD x broker name takes this channel as its route, over firm 1's rows and
--crd_dist_override, so both sources' new state and the sales rules use it (owner, 2026-11-01: "when firm and written
--channel disagree, we need to override the actual channel for that firm and crd").  Matched trimmed and upper-cased;
--a NULL broker name = every name on the CRD (a row with the name wins).
--CHECKS (statement 7): a firm on 2+ channels (not applied), a firm not in the data, a channel no firm 1 territory has.
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_firm_route_override AS
SELECT TRIM(CAST(firm_crd AS VARCHAR)) AS firm_crd, NULLIF(UPPER(TRIM(CAST(broker_name AS VARCHAR))), '') AS broker_name,
       UPPER(TRIM(CAST(route AS VARCHAR))) AS route
FROM (VALUES
  -- owner routes: begin
  -- 2026-11-01, from the owner's review workbook: the channel written beside the chosen firm
  ('13572', 'CETERA WEALTH SERVICES, LLC', 'FI'),
  -- 2026-11-01, owner: "for cetera investment services crd: 15340 we are overriding to be FI" (every name on the CRD)
  ('15340', NULL, 'FI'),
  -- owner routes: end
  ('', '', '')   -- placeholder, keep it last
) AS v (firm_crd, broker_name, route)
WHERE TRIM(firm_crd) <> '';

--2. Each source's opportunity rows, cleaned and grouped: ZIP padded to 5, IDs as text, names and labels trimmed and
--upper-cased, the product map (DATA_MODEL.md, p: RILA if either column says RILA, IOVA, VARIABLE, INDEX, FIXED).
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_o1_rows_s1 AS
WITH
o AS (SELECT *, ROW_NUMBER() OVER (ORDER BY n DESC) AS oid FROM (
  SELECT LPAD(LEFT(TRIM(zip_code), 5), 5, '0') AS zip, NULLIF(TRIM(cbd_id), '') AS cbd_id,
         NULLIF(TRIM(CAST(client_firm_id AS VARCHAR)), '') AS client_firm_id,
         NULLIF(TRIM(firm_crd), '') AS firm_crd, UPPER(TRIM(broker_name)) AS broker_name,
         NULLIF(UPPER(TRIM(dist_ch)), '') AS feed_dist_ch,
         CASE WHEN UPPER(TRIM(product_line)) = 'RILA' OR UPPER(TRIM(va_product_type)) = 'RILA' THEN 'RILA'
              WHEN UPPER(TRIM(va_product_type)) = 'IOVA' THEN 'IOVA'
              WHEN UPPER(TRIM(product_line)) = 'VA' THEN 'VARIABLE'
              WHEN UPPER(TRIM(product_line)) = 'IA' THEN 'INDEX'
              WHEN UPPER(TRIM(product_line)) = 'FA' THEN 'FIXED' END AS product,
         COUNT(*) AS n, SUM(global_sales) AS amt
  FROM life_prod.lif_murkylake.wc_market_metrics_opportunity WHERE fiscal_yr = '2025' GROUP BY ALL)),
r AS (SELECT o.oid, ru.channel AS rule_channel, ROW_NUMBER() OVER (PARTITION BY o.oid ORDER BY ru.rule_order) AS rk
      FROM o JOIN ssdb_integration.lr_strategy.tmp_s1_channel_rule ru
        ON ru.cbd_id = o.cbd_id OR ru.broker_name = o.broker_name OR ru.dist_ch = o.feed_dist_ch)
SELECT o.zip, o.firm_crd, o.broker_name, o.product,
       COALESCE(cn.company_id, CASE WHEN o.cbd_id = '0' THEN o.client_firm_id ELSE o.cbd_id END) AS company_id,
       COALESCE(r.rule_channel, o.feed_dist_ch) AS cur_label, o.n, o.amt
FROM o
LEFT JOIN r ON r.oid = o.oid AND r.rk = 1
LEFT JOIN ssdb_integration.lr_strategy.tmp_s1_company_by_name cn ON cn.broker_name = o.broker_name;

CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_o1_rows_s2 AS
SELECT LPAD(CAST(CAST(zip_code AS DECIMAL(38, 0)) AS VARCHAR), 5, '0') AS zip,
       CAST(CAST(firm_crd AS DECIMAL(38, 0)) AS VARCHAR) AS firm_crd, UPPER(TRIM(broker_name)) AS broker_name,
       CASE WHEN UPPER(TRIM(product_line)) = 'RILA' OR UPPER(TRIM(va_product_type)) = 'RILA' THEN 'RILA'
            WHEN UPPER(TRIM(va_product_type)) = 'IOVA' THEN 'IOVA'
            WHEN UPPER(TRIM(product_line)) = 'VA' THEN 'VARIABLE'
            WHEN UPPER(TRIM(product_line)) = 'IA' THEN 'INDEX'
            WHEN UPPER(TRIM(product_line)) = 'FA' THEN 'FIXED' END AS product,
       NULLIF(UPPER(TRIM(dist_ch)), '') AS cur_label, COUNT(*) AS n, SUM(opp) AS amt
FROM IDENTIFIER($s2_opp)
GROUP BY ALL;

--3. The firm table.  Route (Q38): the one non-blank firm 1 channel of the CRD x broker name in source 1's rows, of the
--CRD where source 1 lacks the name (a source 2 name); crd_dist_override (distinct keys; its CRD x name row, else its CRD row) fills only a
--route with no channel, 2+ channels or no source 1 rows; else UNMAPPED.  The owner's channel (tmp_firm_route_override,
--one per firm) comes before all of these; ROUTE_BASIS then says OWNER OVERRIDE: the route it replaced -> the owner's.  NEW_LABEL: the new-channel list's label, else
--the route.  TAU: the list's holder channel, else the route.
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_o1_firm AS
WITH
s1 AS (SELECT * FROM ssdb_integration.lr_strategy.tmp_o1_rows_s1 WHERE firm_crd IS NOT NULL),
k AS (SELECT DISTINCT firm_crd, broker_name FROM s1
      UNION SELECT DISTINCT firm_crd, broker_name FROM ssdb_integration.lr_strategy.tmp_o1_rows_s2 WHERE firm_crd IS NOT NULL),
nr AS (SELECT firm_crd, broker_name, COUNT(DISTINCT cur_label) AS k, MIN(cur_label) AS ch FROM s1 GROUP BY ALL),
cr AS (SELECT firm_crd, COUNT(DISTINCT cur_label) AS k, MIN(cur_label) AS ch FROM s1 GROUP BY ALL),
ov AS (SELECT firm_crd, broker_name, COUNT(DISTINCT ch) AS k, MIN(ch) AS ch FROM (
         SELECT DISTINCT TRIM(firm_crd) AS firm_crd, NULLIF(UPPER(TRIM(broker_name)), '') AS broker_name,
                NULLIF(UPPER(TRIM(dist_ch)), '') AS ch
         FROM ssdb_integration.lr_strategy.crd_dist_override) x
       GROUP BY ALL),
nu AS (SELECT s1.firm_crd, s1.broker_name, COUNT(DISTINCT nl.new_label) AS k, MIN(nl.new_label) AS label,
              MIN(nl.holder_channel) AS holder_ch
       FROM s1 JOIN ssdb_integration.lr_strategy.tmp_new_label nl ON nl.company_id = s1.company_id GROUP BY ALL),
fo AS (SELECT firm_crd, broker_name, COUNT(DISTINCT route) AS k, MIN(route) AS route
       FROM ssdb_integration.lr_strategy.tmp_firm_route_override GROUP BY ALL),
r AS (SELECT k.firm_crd, k.broker_name, COALESCE(fo.route, f0.route) AS owner_route,
             CASE WHEN nr.firm_crd IS NOT NULL THEN nr.k ELSE cr.k END AS s1_k,
             CASE WHEN nr.firm_crd IS NOT NULL THEN nr.ch ELSE cr.ch END AS s1_ch,
             CASE WHEN nr.firm_crd IS NOT NULL THEN 'NAME' ELSE 'CRD' END AS s1_level,
             COALESCE(v1.k, v0.k) AS ov_k, COALESCE(v1.ch, v0.ch) AS ov_ch,
             nu.k AS nu_k, nu.label AS nu_label, nu.holder_ch
      FROM k
      LEFT JOIN nr ON nr.firm_crd = k.firm_crd AND nr.broker_name = k.broker_name
      LEFT JOIN cr ON cr.firm_crd = k.firm_crd
      LEFT JOIN ov v1 ON v1.firm_crd = k.firm_crd AND v1.broker_name = k.broker_name
      LEFT JOIN ov v0 ON v0.firm_crd = k.firm_crd AND v0.broker_name IS NULL
      LEFT JOIN nu ON nu.firm_crd = k.firm_crd AND nu.broker_name = k.broker_name
      LEFT JOIN fo ON fo.firm_crd = k.firm_crd AND fo.broker_name = UPPER(k.broker_name) AND fo.k = 1
      LEFT JOIN fo f0 ON f0.firm_crd = k.firm_crd AND f0.broker_name IS NULL AND f0.k = 1),
g0 AS (SELECT r.*,
              CASE WHEN s1_k = 1 THEN s1_ch WHEN ov_k = 1 THEN ov_ch ELSE 'UNMAPPED' END AS derived_route,
              CASE WHEN s1_k = 1 THEN s1_level
                   ELSE CASE WHEN ov_k = 1 THEN 'OVERRIDE FILLS ' ELSE 'UNMAPPED: ' END
                        || CASE WHEN s1_k = 0 THEN 'NO CHANNEL' WHEN s1_k > 1 THEN '2+ CHANNELS'
                                ELSE 'NO SOURCE 1 ROWS' END END AS derived_basis
       FROM r),
g AS (SELECT g0.*, COALESCE(owner_route, derived_route) AS route,
             CASE WHEN owner_route IS NOT NULL THEN 'OWNER OVERRIDE: ' || derived_route || ' -> ' || owner_route
                  ELSE derived_basis END AS route_basis
      FROM g0)
SELECT g.firm_crd, g.broker_name, g.route, g.route_basis, g.ov_ch,
       g.nu_k, CASE WHEN g.nu_k > 1 THEN '2+ NEW LABELS' WHEN g.nu_k = 1 THEN g.nu_label ELSE g.route END AS new_label,
       CASE WHEN g.nu_k > 1 THEN NULL WHEN g.nu_k = 1 THEN g.holder_ch ELSE g.route END AS tau
FROM g;

--4. Holders per territory channel x ZIP, each source: the lowest ID where 2+ hold (Settled, 2026-10-28).
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_o1_h1 AS
SELECT UPPER(TRIM(new_dist_channel)) AS channel, LPAD(LEFT(TRIM(zip), 5), 5, '0') AS zip,
       CAST(MIN(whslr_id) AS VARCHAR) AS holder, COUNT(DISTINCT whslr_id) AS n_holders
FROM IDENTIFIER($s1_territories) GROUP BY ALL;

CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_o1_h2 AS
SELECT UPPER(TRIM(channel)) AS channel, LPAD(LEFT(TRIM(zipcode), 5), 5, '0') AS zip,
       CAST(MIN(territory_id) AS VARCHAR) AS holder, COUNT(DISTINCT territory_id) AS n_holders
FROM IDENTIFIER($s2_territories) GROUP BY ALL;

--5. The cells.  Current: source 1's label is its territory channel; source 2's goes through Q19.  New: the firm's
--label; the holder channel TAU (source 2: through Q39); a row with no CRD has no firm and is UNMAPPED.
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_o1_cells_s1 AS
WITH c AS (SELECT zip, firm_crd, broker_name, product, cur_label, SUM(n) AS n_rows, SUM(amt) AS amt
           FROM ssdb_integration.lr_strategy.tmp_o1_rows_s1 GROUP BY ALL)
SELECT c.zip, c.firm_crd, c.broker_name, c.product, c.cur_label, c.cur_label AS cur_terr_ch,
       hc.holder AS cur_holder, hc.n_holders AS cur_n_holders,
       COALESCE(f.route_basis, 'NO CRD') AS route_basis, TRUE AS keep_new,
       COALESCE(f.new_label, 'UNMAPPED') AS new_label, NULLIF(f.tau, 'UNMAPPED') AS new_terr_ch,
       hn.holder AS new_holder, hn.n_holders AS new_n_holders, c.n_rows, c.amt
FROM c
LEFT JOIN ssdb_integration.lr_strategy.tmp_o1_firm f ON f.firm_crd = c.firm_crd AND f.broker_name = c.broker_name
LEFT JOIN ssdb_integration.lr_strategy.tmp_o1_h1 hc ON hc.channel = c.cur_label AND hc.zip = c.zip
LEFT JOIN ssdb_integration.lr_strategy.tmp_o1_h1 hn ON hn.channel = f.tau AND hn.zip = c.zip;

CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_o1_cells_s2 AS
WITH
c AS (SELECT zip, firm_crd, broker_name, product, cur_label, SUM(n) AS n_rows, SUM(amt) AS amt
      FROM ssdb_integration.lr_strategy.tmp_o1_rows_s2 GROUP BY ALL),
x AS (SELECT c.*, lm.terr_channel AS cur_terr_ch, COALESCE(lm.keep_new, TRUE) AS keep_new,
             COALESCE(f.route_basis, 'NO CRD') AS route_basis, COALESCE(f.new_label, 'UNMAPPED') AS new_label,
             nm.terr_channel AS new_terr_ch
      FROM c
      LEFT JOIN ssdb_integration.lr_strategy.tmp_s2_label_terr lm ON lm.label = c.cur_label
      LEFT JOIN ssdb_integration.lr_strategy.tmp_o1_firm f ON f.firm_crd = c.firm_crd AND f.broker_name = c.broker_name
      LEFT JOIN ssdb_integration.lr_strategy.tmp_s1ch_s2terr nm ON nm.s1_channel = f.tau)
SELECT x.zip, x.firm_crd, x.broker_name, x.product, x.cur_label, x.cur_terr_ch,
       hc.holder AS cur_holder, hc.n_holders AS cur_n_holders, x.route_basis, x.keep_new,
       CASE WHEN x.keep_new THEN x.new_label END AS new_label, CASE WHEN x.keep_new THEN x.new_terr_ch END AS new_terr_ch,
       CASE WHEN x.keep_new THEN hn.holder END AS new_holder, CASE WHEN x.keep_new THEN hn.n_holders END AS new_n_holders,
       x.n_rows, x.amt
FROM x
LEFT JOIN ssdb_integration.lr_strategy.tmp_o1_h2 hc ON hc.channel = x.cur_terr_ch AND hc.zip = x.zip
LEFT JOIN ssdb_integration.lr_strategy.tmp_o1_h2 hn ON hn.channel = x.new_terr_ch AND hn.zip = x.zip;

--6. The dataset: both sources' cells, every one, one row each: the master table, filtered afterwards (owner,
--2026-10-30: "a single master table across all cases which we then filter down afterwards").  Wholesaler names from
--the territory tables (firm 1: WHSLR_NM; firm 2: the territory's RVP).  OLD_CHANNEL: firm 1's channel after its
--rules; firm 2's own label.
--OLD_CHANNEL_S1: the old channel in firm 1's names (owner, 2026-10-30, option (a)): firm 1's own; firm 2's territory
--channel read back through the Q39 pairs (BK -> FI, FP -> IFA, BD -> WH, RA -> PRI), blank for NO CHANNEL.
--NEW_CHANNEL_BASIS: how the firm's channel was found (TMP_O1_FIRM.ROUTE_BASIS).  Look at it in the same session, e.g.
--  SELECT source, new_channel, product, SUM(opportunity) FROM ssdb_integration.lr_strategy.tmp_o1_dataset GROUP BY ALL;
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_o1_dataset AS
WITH
n1 AS (SELECT CAST(whslr_id AS VARCHAR) AS id, MIN(whslr_nm) AS nm FROM IDENTIFIER($s1_territories) GROUP BY ALL),
n2 AS (SELECT CAST(territory_id AS VARCHAR) AS id, MIN(rvp) AS nm FROM IDENTIFIER($s2_territories) GROUP BY ALL),
q39 AS (SELECT terr_channel, MIN(s1_channel) AS s1_channel   -- one row per territory channel: no fan-out (checked in 7)
        FROM ssdb_integration.lr_strategy.tmp_s1ch_s2terr GROUP BY ALL),
u AS (
            SELECT 'S1' AS source, c.*, a.nm AS cur_nm, b.nm AS new_nm, c.cur_label AS cur_s1
            FROM ssdb_integration.lr_strategy.tmp_o1_cells_s1 c
            LEFT JOIN n1 a ON a.id = c.cur_holder LEFT JOIN n1 b ON b.id = c.new_holder
  UNION ALL SELECT 'S2', c.*, a.nm, b.nm, q.s1_channel FROM ssdb_integration.lr_strategy.tmp_o1_cells_s2 c
            LEFT JOIN n2 a ON a.id = c.cur_holder LEFT JOIN n2 b ON b.id = c.new_holder
            LEFT JOIN q39 q ON q.terr_channel = c.cur_terr_ch)
SELECT source, zip, firm_crd, broker_name, product, cur_label AS old_channel, cur_s1 AS old_channel_s1,
       new_label AS new_channel,
       route_basis AS new_channel_basis, cur_terr_ch AS old_territory_channel, new_terr_ch AS new_territory_channel,
       cur_holder AS old_wholesaler_id, cur_nm AS old_wholesaler, new_holder AS new_wholesaler_id,
       new_nm AS new_wholesaler, amt AS opportunity
FROM u;

--7. Views and checks, one table, over every cell; PCT_AMT: of PART x SOURCE x NAME.
--  V1 CHANNEL: $ by label, NAME = the state.  V2A RECLASSIFIED: current label -> new label; ITEM2 (source 1):
--    RECLASSIFIED where they differ.  V2B HOLDER MOVES: same holder, other holder, gains, loses, none in either,
--    dropped; ITEM2 current -> new territory channel.  V3 COVERAGE: one holder, the lowest of 2+, no holder (no
--    territory channel: blank or UNMAPPED label, a label with no pair; no holder at the ZIP), dropped.
--  CHECKS: SOURCE MINUS CELLS and CURRENT MINUS NEW (I4) must be 0; FIRM KEYS REPEATED, FIRMS WITH 2+ NEW LABELS,
--    Q39 TERRITORY CHANNELS ON 2+ FIRM 1 CHANNELS must have N_FIRMS 0; the rest are reported: route basis, the override where the route was kept, listed firms
--    (label | holder channel | route), firms with no listed label on a CRD where another name has one, cells with
--    2+ current labels, product unmapped.
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_o1_out AS
WITH
cells AS (
            SELECT 'S1' AS source, * FROM ssdb_integration.lr_strategy.tmp_o1_cells_s1
  UNION ALL SELECT 'S2', * FROM ssdb_integration.lr_strategy.tmp_o1_cells_s2),
st AS (
            SELECT source, 'CURRENT' AS state, cur_label AS label, cur_terr_ch AS terr_ch, cur_holder AS holder,
                   cur_n_holders AS n_holders, TRUE AS kept, zip, firm_crd, broker_name, amt FROM cells
  UNION ALL SELECT source, 'NEW', new_label, new_terr_ch, new_holder, new_n_holders, keep_new, zip, firm_crd,
                   broker_name, amt FROM cells),
raw AS (
            SELECT 'S1' AS source, SUM(global_sales) AS amt
            FROM life_prod.lif_murkylake.wc_market_metrics_opportunity WHERE fiscal_yr = '2025'
  UNION ALL SELECT 'S2', SUM(opp) FROM IDENTIFIER($s2_opp)),
cl AS (SELECT DISTINCT firm_crd FROM ssdb_integration.lr_strategy.tmp_o1_firm WHERE nu_k = 1),
fx AS (SELECT f.*, CASE WHEN f.nu_k IS NULL AND cl.firm_crd IS NOT NULL THEN 'Y' END AS other_name_listed
       FROM ssdb_integration.lr_strategy.tmp_o1_firm f LEFT JOIN cl ON cl.firm_crd = f.firm_crd),
cf AS (SELECT c.*, fx.nu_k, fx.ov_ch, fx.route, fx.other_name_listed,
              CASE WHEN fx.nu_k = 1 THEN fx.new_label || ' | ' || COALESCE(fx.tau, '(NONE)') || ' | ' || fx.route END AS listed
       FROM cells c LEFT JOIN fx ON fx.firm_crd = c.firm_crd AND fx.broker_name = c.broker_name),
multi AS (SELECT * FROM (SELECT source, zip, firm_crd, broker_name, product, COUNT(*) AS k, SUM(amt) AS amt
                         FROM cells GROUP BY ALL) m WHERE k > 1),
v AS (
            SELECT 'V1 CHANNEL' AS part, source, state AS name, COALESCE(label, '(BLANK)') AS item,
                   CAST(NULL AS VARCHAR) AS item2, zip, firm_crd, broker_name, holder, amt
            FROM st WHERE kept
  UNION ALL SELECT 'V2A RECLASSIFIED', source, NULL,
                   COALESCE(cur_label, '(BLANK)') || ' -> ' || CASE WHEN keep_new THEN new_label ELSE '(DROPPED)' END,
                   CASE WHEN source = 'S1' THEN CASE WHEN EQUAL_NULL(cur_label, new_label) THEN 'SAME'
                                                     ELSE 'RECLASSIFIED' END END,
                   zip, firm_crd, broker_name, NULL, amt
            FROM cells
  UNION ALL SELECT 'V2B HOLDER MOVES', source, NULL,
                   CASE WHEN NOT keep_new THEN 'DROPPED'
                        WHEN cur_holder IS NULL AND new_holder IS NULL THEN 'NO HOLDER IN EITHER'
                        WHEN cur_holder IS NULL THEN 'GAINS A HOLDER' WHEN new_holder IS NULL THEN 'LOSES ITS HOLDER'
                        WHEN cur_holder = new_holder THEN 'SAME HOLDER' ELSE 'OTHER HOLDER' END,
                   COALESCE(cur_terr_ch, '(NONE)') || ' -> ' || COALESCE(new_terr_ch, '(NONE)'),
                   zip, firm_crd, broker_name, NULL, amt
            FROM cells
  UNION ALL SELECT 'V3 COVERAGE', source, state,
                   CASE WHEN NOT kept THEN 'DROPPED' WHEN terr_ch IS NULL THEN 'NO HOLDER: NO TERRITORY CHANNEL'
                        WHEN holder IS NULL THEN 'NO HOLDER: NONE AT THE ZIP'
                        WHEN n_holders = 1 THEN 'ONE HOLDER' ELSE 'LOWEST OF 2+ HOLDERS' END,
                   NULL, zip, firm_crd, broker_name, holder, amt
            FROM st
  UNION ALL SELECT 'CHECKS', source, 'ROUTE BASIS', route_basis, NULL, zip, firm_crd, broker_name, NULL, amt FROM cells
  UNION ALL SELECT 'CHECKS', source, 'OVERRIDE <> ROUTE, ROUTE KEPT', ov_ch || ' <> ' || route, NULL, zip, firm_crd,
                   broker_name, NULL, amt
            FROM cf WHERE route_basis IN ('NAME', 'CRD') AND ov_ch <> route
  UNION ALL SELECT 'CHECKS', source, 'LISTED FIRMS: LABEL | HOLDER CHANNEL | ROUTE', listed, NULL, zip, firm_crd,
                   broker_name, NULL, amt
            FROM cf WHERE listed IS NOT NULL
  UNION ALL SELECT 'CHECKS', source, 'NO LISTED LABEL, ANOTHER NAME OF THE CRD HAS ONE', new_label, NULL, zip, firm_crd,
                   broker_name, NULL, amt
            FROM cf WHERE other_name_listed = 'Y'
  UNION ALL SELECT 'CHECKS', source, 'PRODUCT UNMAPPED', 'NO PRODUCT', NULL, zip, firm_crd, broker_name, NULL, amt
            FROM cells WHERE product IS NULL)
SELECT part, source, name, item, item2, COUNT(*) AS n_cells,
       COUNT(DISTINCT firm_crd || '|' || broker_name) AS n_firms, COUNT(DISTINCT holder) AS n_holders, SUM(amt) AS amt
FROM v GROUP BY ALL
UNION ALL
SELECT 'CHECKS', r.source, 'SOURCE MINUS CELLS (MUST BE 0)', NULL, NULL, NULL, NULL, NULL, ROUND(r.amt - c.amt, 2)
FROM raw r JOIN (SELECT source, SUM(amt) AS amt FROM cells GROUP BY ALL) c ON c.source = r.source
UNION ALL
SELECT 'CHECKS', s.source, 'CURRENT MINUS NEW, DROPPED COUNTED (MUST BE 0)', NULL, NULL, NULL, NULL, NULL,
       ROUND(SUM(CASE WHEN s.state = 'CURRENT' THEN s.amt ELSE -s.amt END), 2)
FROM st s GROUP BY ALL
UNION ALL
SELECT 'CHECKS', NULL, 'FIRM KEYS REPEATED (MUST BE 0)', NULL, NULL, NULL,
       (SELECT COUNT(*) FROM (SELECT firm_crd, broker_name, COUNT(*) AS k FROM ssdb_integration.lr_strategy.tmp_o1_firm
                              GROUP BY ALL) d WHERE k > 1), NULL, NULL
UNION ALL
SELECT 'CHECKS', NULL, 'Q39 TERRITORY CHANNELS ON 2+ FIRM 1 CHANNELS (MUST BE 0)', NULL, NULL, NULL,
       (SELECT COUNT(*) FROM (SELECT terr_channel, COUNT(*) AS k FROM ssdb_integration.lr_strategy.tmp_s1ch_s2terr
                              GROUP BY ALL) d WHERE k > 1), NULL, NULL
UNION ALL
SELECT 'CHECKS', NULL, 'FIRMS WITH 2+ NEW LABELS (MUST BE 0)', NULL, NULL, NULL,
       (SELECT COUNT(*) FROM ssdb_integration.lr_strategy.tmp_o1_firm WHERE nu_k > 1), NULL, NULL
UNION ALL
SELECT 'CHECKS', NULL, 'OWNER ROUTES: A FIRM ON 2+ CHANNELS, NOT APPLIED (MUST BE 0)', NULL, NULL, NULL,
       (SELECT COUNT(*) FROM (SELECT firm_crd, broker_name, COUNT(DISTINCT route) AS k
                              FROM ssdb_integration.lr_strategy.tmp_firm_route_override GROUP BY ALL) d WHERE k > 1),
       NULL, NULL
UNION ALL
SELECT 'CHECKS', NULL, 'OWNER ROUTES: FIRM NOT IN THE DATA (MUST BE 0)', NULL, NULL, NULL,
       (SELECT COUNT(*) FROM ssdb_integration.lr_strategy.tmp_firm_route_override o
        LEFT JOIN ssdb_integration.lr_strategy.tmp_o1_firm f
          ON f.firm_crd = o.firm_crd AND UPPER(f.broker_name) = COALESCE(o.broker_name, UPPER(f.broker_name))
        WHERE f.firm_crd IS NULL), NULL, NULL
UNION ALL
SELECT 'CHECKS', NULL, 'OWNER ROUTES: NO FIRM 1 TERRITORY CHANNEL (MUST BE 0)', NULL, NULL, NULL,
       (SELECT COUNT(*) FROM ssdb_integration.lr_strategy.tmp_firm_route_override o
        LEFT JOIN (SELECT DISTINCT UPPER(TRIM(new_dist_channel)) AS ch FROM IDENTIFIER($s1_territories)) t ON t.ch = o.route
        WHERE t.ch IS NULL), NULL, NULL
UNION ALL
SELECT 'CHECKS', source, 'CELLS WITH 2+ CURRENT LABELS', NULL, NULL, COUNT(*), NULL, NULL, SUM(amt)
FROM multi GROUP BY ALL;

--SALES: statements 8-14 read the opportunity tables above.

--8. Decisions as tables.
--A sale's product -> the cell's product.  Source 1's are s1_sales.sql:315-317's (FIXED, SPIA/DIA, ASSURED EDGE are
--FIXED); source 2's market metrics codes as the opportunity map reads them.  Sales carry no VA type: a VA sale is
--VARIABLE, and IOVA opportunity has no sales.  A value not here keeps no product (SALES PRODUCT lists it).
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_sales_product AS
SELECT CAST(value AS VARCHAR) AS value, CAST(product AS VARCHAR) AS product
FROM (VALUES ('RILA', 'RILA'), ('INDEX', 'INDEX'), ('VARIABLE', 'VARIABLE'), ('FIXED', 'FIXED'), ('IOVA', 'IOVA'),
             ('IA', 'INDEX'), ('VA', 'VARIABLE'), ('FA', 'FIXED')) AS v (value, product);

--Source 1's sale channels in firm 1's channel names, used to pick the firm where a company has 2+: IMO and the
--split-policy labels sell on their base channel (s1_sales.sql:18, :21, :418).  Any other label stands for itself.
--Statement 12: a sale with one of these labels and no market metrics firm is a marketing organization, new channel IMO.
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_s1_sale_channel AS
SELECT CAST(label AS VARCHAR) AS label, CAST(s1_channel AS VARCHAR) AS s1_channel
FROM (VALUES ('IMO', 'IFA'), ('IFA/IMO', 'IFA'), ('FI/IMO', 'FI')) AS v (label, s1_channel);

--Manual assignments (the owner's): a sale the rules leave without a market metrics firm takes the firm named here
--(FIRM_BASIS MANUAL).  Copy a TMP_SALES_REVIEW row's key (SOURCE, SALES_FIRM_ID, SALES_FIRM, RAW_CHANNEL,
--MGA_AGENT_CD) and the chosen CAND_FIRM_CRD, CAND_BROKER_NAME; NULL MGA_AGENT_CD = any code (a row with the code wins).
--Matched trimmed and upper-cased (a typed name may be in any case).  A key on 2+ firms, a firm not in TMP_O1_FIRM or a
--key that matches no sale is not applied (CHECKS: MANUAL ...).
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_sales_firm_override AS
SELECT UPPER(TRIM(CAST(source AS VARCHAR))) AS source, NULLIF(TRIM(CAST(sales_firm_id AS VARCHAR)), '') AS sales_firm_id,
       UPPER(TRIM(CAST(sales_firm AS VARCHAR))) AS sales_firm, UPPER(TRIM(CAST(raw_channel AS VARCHAR))) AS raw_channel,
       NULLIF(UPPER(TRIM(CAST(mga_agent_cd AS VARCHAR))), '') AS mga_agent_cd, TRIM(CAST(firm_crd AS VARCHAR)) AS firm_crd,
       UPPER(TRIM(CAST(broker_name AS VARCHAR))) AS broker_name
FROM (VALUES
  -- one row per assignment, each ending in a comma, above the placeholder, e.g.
  -- ('S1', '8', 'LPL FINANCIAL CORPORATION', 'IFA', NULL, '<CAND_FIRM_CRD>', '<CAND_BROKER_NAME>'),
  -- owner rows: begin
  -- 2026-11-01, from the owner's review workbook (Decisions, DECISION = ASSIGN); keys as the sales table has them
  ('S2', NULL, 'Ameriprise Financial Svcs, LLC', 'FP', NULL, '6363', 'AMERIPRISE FINANCIAL SERVICES, LLC'),
  ('S2', NULL, 'Baird Trust Company', 'RA', NULL, '8158', 'Robert W. Baird & Co. Incorporated'),
  ('S1', '86', 'CADARET GRANT & COMPANY, INC.', 'IFA', '44AME', '6413', 'LPL FINANCIAL LLC - INDEPENDENT'),
  ('S1', '86', 'CADARET GRANT & COMPANY, INC.', 'IFA', '88070', '6413', 'LPL FINANCIAL LLC - INDEPENDENT'),
  ('S1', '86', 'CADARET GRANT & COMPANY, INC.', 'IFA', '41124', '6413', 'LPL FINANCIAL LLC - INDEPENDENT'),
  ('S1', '86', 'CADARET GRANT & COMPANY, INC.', 'IFA', '33AME', '6413', 'LPL FINANCIAL LLC - INDEPENDENT'),
  ('S1', '86', 'CADARET GRANT & COMPANY, INC.', 'IFA', '11124', '6413', 'LPL FINANCIAL LLC - INDEPENDENT'),
  ('S1', '86', 'CADARET GRANT & COMPANY, INC.', 'IFA', '7BG99', '6413', 'LPL FINANCIAL LLC - INDEPENDENT'),
  ('S2', '13572', 'Cetera Wealth Services', 'FP', NULL, '13572', 'Cetera Wealth Services, LLC - INDEPENDENT'),
  ('S2', NULL, 'Edward D.Jones & Co.,LP', 'BD', NULL, '250', 'EDWARD JONES'),
  ('S2', NULL, 'Flourish Financial - OID', 'FP', NULL, '293019', 'FLOURISH FINANCIAL LLC'),
  ('S1', '779', 'GOLD COAST SECURITIES, INC.', 'IFA', '88H49', '110925', 'GOLD COAST SECURITIES, INC.'),
  ('S1', '8', 'LPL FINANCIAL CORPORATION', 'IFA', '33AAZ', '6413', 'LPL FINANCIAL LLC - INDEPENDENT'),
  ('S1', '8', 'LPL FINANCIAL CORPORATION', 'IFA', '44AAZ', '6413', 'LPL FINANCIAL LLC - INDEPENDENT'),
  ('S1', '8', 'LPL FINANCIAL CORPORATION', 'IFA', '88268', '6413', 'LPL FINANCIAL LLC - INDEPENDENT'),
  ('S1', '8', 'LPL FINANCIAL CORPORATION', 'IFA', '41114', '6413', 'LPL FINANCIAL LLC - INDEPENDENT'),
  ('S1', '8', 'LPL FINANCIAL CORPORATION', 'IFA', '11114', '6413', 'LPL FINANCIAL LLC - INDEPENDENT'),
  ('S1', '8', 'LPL FINANCIAL CORPORATION', 'IFA', 'WNL0BD4400000000000', '6413', 'LPL FINANCIAL LLC - INDEPENDENT'),
  ('S1', '8', 'LPL FINANCIAL CORPORATION', 'IFA/IMO', '44AAL', '6413', 'LPL FINANCIAL LLC - BANK'),
  ('S2', '6413', 'LPL Financial LLC', 'FP', NULL, '6413', 'LPL FINANCIAL LLC - INDEPENDENT'),
  ('S2', '6413', 'LPL Financial LLC', 'BD', NULL, '6413', 'LPL FINANCIAL LLC - BANK'),
  ('S2', '6413', 'LPL Financial LLC', 'RA', NULL, '6413', 'LPL FINANCIAL LLC - INDEPENDENT'),
  ('S2', NULL, 'MS Howells & CO', 'FP', NULL, '104100', 'M. S. Howells & Co.'),
  ('S1', '327', 'NEXT FINANCIAL GROUP', 'IFA', '88E74', '6413', 'LPL FINANCIAL LLC - INDEPENDENT'),
  ('S1', '327', 'NEXT FINANCIAL GROUP', 'IFA', '44AJM', '6413', 'LPL FINANCIAL LLC - INDEPENDENT'),
  ('S1', '327', 'NEXT FINANCIAL GROUP', 'IFA', '11162', '6413', 'LPL FINANCIAL LLC - INDEPENDENT'),
  ('S1', '327', 'NEXT FINANCIAL GROUP', 'IFA', '33AJM', '6413', 'LPL FINANCIAL LLC - INDEPENDENT'),
  ('S1', '6', 'RAYMOND JAMES', 'IFA', '88186', '705', 'RAYMOND JAMES & ASSOCIATES, INC.'),
  ('S1', '569', 'STIFEL INDEPENDENT ADVISORS', 'IFA', '11346', '28218', 'STIFEL INDEPENDENT ADVISORS, LLC'),
  ('S1', '569', 'STIFEL INDEPENDENT ADVISORS', 'IFA', '33AKR', '28218', 'STIFEL INDEPENDENT ADVISORS, LLC'),
  ('S1', '569', 'STIFEL INDEPENDENT ADVISORS', 'IFA', '88874', '28218', 'STIFEL INDEPENDENT ADVISORS, LLC'),
  ('S1', '569', 'STIFEL INDEPENDENT ADVISORS', 'IFA', 'WNL0B27400000000000', '28218', 'STIFEL INDEPENDENT ADVISORS, LLC'),
  ('S1', '222', 'STIFEL NICOLAUS & CO INC', 'WH', '11182', '793', 'STIFEL, NICOLAUS & COMPANY, INCORPORATED'),
  ('S1', '100', 'THE INVESTMENT CENTER, INC.', 'IFA', '88544', '6413', 'LPL FINANCIAL LLC - INDEPENDENT'),
  ('S2', NULL, 'U.S. Bancorp Advisors, LLC', 'BK', NULL, '17868', 'U.S. BANCORP INVESTMENTS, INC.'),
  ('S2', NULL, 'VOYA FINANCIAL ADVISORS,INC', 'RA', NULL, '2882', 'VOYA FINANCIAL ADVISORS, INC.'),
  ('S2', NULL, 'VOYA FINANCIAL ADVISORS,INC', 'FP', NULL, '2882', 'VOYA FINANCIAL ADVISORS, INC.'),
  ('S1', '14', 'WELLS FARGO CLEARING SERVICES PCG', 'WH', '33ABN', '19616', 'WELLS FARGO CLEARING SERVICES, LLC - ADVISOR'),
  ('S1', '14', 'WELLS FARGO CLEARING SERVICES PCG', 'WH', 'WNL049AP00000000000', '19616', 'WELLS FARGO CLEARING SERVICES, LLC - ADVISOR'),
  ('S1', '14', 'WELLS FARGO CLEARING SERVICES PCG', 'WH', '88A30', '19616', 'WELLS FARGO CLEARING SERVICES, LLC - ADVISOR'),
  ('S1', '14', 'WELLS FARGO CLEARING SERVICES PCG', 'WH', '44ABN', '19616', 'WELLS FARGO CLEARING SERVICES, LLC - ADVISOR'),
  ('S1', '14', 'WELLS FARGO CLEARING SERVICES PCG', 'WH', '11190', '19616', 'WELLS FARGO CLEARING SERVICES, LLC - ADVISOR'),
  ('S1', '14', 'WELLS FARGO CLEARING SERVICES PCG', 'WH', '41190', '19616', 'WELLS FARGO CLEARING SERVICES, LLC - ADVISOR'),
  ('S1', '14', 'WELLS FARGO CLEARING SERVICES PCG', 'WH', 'FSA05FUS00000000000', '19616', 'WELLS FARGO CLEARING SERVICES, LLC - ADVISOR'),
  ('S2', '19616', 'WFCS, LLC', 'BD', NULL, '19616', 'WELLS FARGO CLEARING SERVICES, LLC - ADVISOR'),
  -- 2026-11-01, held row released: its firm's channel is now the owner's (tmp_firm_route_override)
  ('S2', '13572', 'Cetera Wealth Services', 'BD', NULL, '13572', 'CETERA WEALTH SERVICES, LLC'),
  -- 2026-11-01, held rows released: the firm as chosen, the sale's channel in tmp_sales_channel_override
  ('S2', '6694', 'Raymond James Financial Svcs', 'FP', NULL, '6694', 'RAYMOND JAMES FINANCIAL SERVICES, INC. - BANK'),
  ('S2', '6694', 'Raymond James Financial Svcs', 'BD', NULL, '6694', 'RAYMOND JAMES FINANCIAL SERVICES, INC. - BANK'),
  -- 2026-11-01, held rows assigned (owner: "yes map them both to lpl financial llc - independent IFA")
  ('S1', '1391', 'WESTERN INTERNATIONAL SEC', 'IFA', '33ASE', '6413', 'LPL FINANCIAL LLC - INDEPENDENT'),
  ('S1', '1391', 'WESTERN INTERNATIONAL SEC', 'IFA', '44ASE', '6413', 'LPL FINANCIAL LLC - INDEPENDENT'),
  ('S2', '19616', 'WFCS, LLC', 'FP', NULL, '19616', 'WELLS FARGO CLEARING SERVICES, LLC - ADVISOR'),
  -- 2026-11-01, the last Cetera keys (owner: "yep go with a")
  ('S1', '107', 'CETERA ADVISORS LLC', 'IFA', '88232', '10299', 'CETERA ADVISORS LLC'),
  ('S2', '13572', 'Cetera Wealth Services', 'BK', NULL, '13572', 'CETERA WEALTH SERVICES, LLC - BANK'),
  -- owner rows: end
  ('', '', '', '', '', '', '')   -- placeholder, keep it last
) AS v (source, sales_firm_id, sales_firm, raw_channel, mga_agent_cd, firm_crd, broker_name)
WHERE source <> '';

--The owner's sales channels: a sale the manual table assigns (FIRM_BASIS MANUAL), or one left without a firm, takes
--this NEW_CHANNEL in place of its firm's or UNMAPPED; the firm's route, its opportunity and its holders are unchanged
--(owner, 2026-11-01: "ok the only update the sales side to /IMO and keep the opp side as it is").  IMO marks a pure IMO
--sale, left out of the review list like firm 1's marketing organizations and filtered out at the end (owner,
--2026-11-01: "we treat them as pure imo and filter out in the end").  Key as in tmp_sales_firm_override, matched the same way;
--NULL MGA_AGENT_CD = any code, a row with the code wins.  CHECKS: a key on 2+ channels, a row matching no such sale.
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_sales_channel_override AS
SELECT UPPER(TRIM(CAST(source AS VARCHAR))) AS source, NULLIF(TRIM(CAST(sales_firm_id AS VARCHAR)), '') AS sales_firm_id,
       UPPER(TRIM(CAST(sales_firm AS VARCHAR))) AS sales_firm, UPPER(TRIM(CAST(raw_channel AS VARCHAR))) AS raw_channel,
       NULLIF(UPPER(TRIM(CAST(mga_agent_cd AS VARCHAR))), '') AS mga_agent_cd,
       UPPER(TRIM(CAST(new_channel AS VARCHAR))) AS new_channel
FROM (VALUES
  -- owner sales channels: begin
  -- 2026-11-01, Raymond James, from the owner's review workbook
  ('S1', '6', 'RAYMOND JAMES', 'IFA', '88186', 'IFA/IMO'),
  ('S2', '6694', 'Raymond James Financial Svcs', 'FP', NULL, 'IFA/IMO'),
  ('S2', '6694', 'Raymond James Financial Svcs', 'BD', NULL, 'FI/IMO'),
  -- 2026-11-01, pure IMO, filtered out at the end (Flourish, Gold Coast with their firm; DPL, FIDx, Pinnacle none)
  ('S2', NULL, 'Flourish Financial - OID', 'FP', NULL, 'IMO'),  -- $0.1MM
  ('S1', '779', 'GOLD COAST SECURITIES, INC.', 'IFA', '88H49', 'IMO'),  -- $0.2MM
  ('S2', NULL, 'DPL Financial Partners,LLC OID', 'FP', NULL, 'IMO'),  -- $57.4MM
  ('S2', NULL, 'FIDx Markets LLC - OID', 'FP', NULL, 'IMO'),  -- $3.7MM
  ('S2', NULL, 'The Pinnacle Group - OID', 'FP', NULL, 'IMO'),  -- $12.6MM
  -- owner sales channels: end
  ('', '', '', '', '', '')   -- placeholder, keep it last
) AS v (source, sales_firm_id, sales_firm, raw_channel, mga_agent_cd, new_channel)
WHERE source <> '';

--9. Source 1's company ID -> the firms whose market metrics rows carry it, as layer 01 derives it from
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

--10. Source 1's sales, fiscal year 2025, with the firm each reaches.  SALES_FIRM_ID, SALES_FIRM, RAW_PRODUCT and
--OLD_CHANNEL are the sales table's CONSOL_BRKR_DLR_ID, CONSOL_BROKER_NM, PRODUCT_LINE2 and DIST_CH as they are;
--matching reads them trimmed and upper-cased.  FIRM_BASIS: ONE FIRM (the company sits on one firm); SPLIT, MATCHED BY
--CHANNEL (2+ firms, exactly one with the sale's channel); SPLIT, MATCHED BY ZIP (2+ with the sale's channel, exactly
--one of them with opportunity at the sale's ZIP x product); SPLIT, MATCHED BY MGA CODE (still 2+: the one name that
--the company's sales under the same MGA code and channel matched by ZIP); SPLIT, MOST OPPORTUNITY AT ZIP (still 2+,
--all on the sale's route: the one with the most opportunity at the sale's ZIP x product, a strict maximum; owner,
--2026-10-31: "yes to 4 rules"); SPLIT, 2+ CHANNEL MATCHES or NO CHANNEL MATCH
--(left without a firm: assign where unique, flag the rest); NO MARKET METRICS FIRM; NO COMPANY.  MGA_AGENT_CD is the sales
--table's, trimmed, blank as NULL: a column only (Q45), the firm still comes from the company ID alone.
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_o2_s1 AS
WITH
s AS (SELECT *, ROW_NUMBER() OVER (ORDER BY sales DESC, sales_firm_id, sales_firm, mga_agent_cd, seller_key, seller, zip,
                                    raw_product, old_channel) AS sid FROM (
  SELECT NULLIF(CAST(CAST(consol_brkr_dlr_id AS DECIMAL(38, 0)) AS VARCHAR), '0') AS sales_firm_id,
         consol_broker_nm AS sales_firm, NULLIF(TRIM(CAST(mga_agent_cd AS VARCHAR)), '') AS mga_agent_cd,
         NULLIF(TRIM(CAST(whslr_id AS VARCHAR)), '') AS seller_key, whslr_nm AS seller,
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
      FROM c JOIN sc ON sc.sid = c.sid WHERE c.route = sc.s1_channel GROUP BY ALL),
cell AS (SELECT zip, firm_crd, broker_name, product, SUM(opportunity) AS opp
         FROM ssdb_integration.lr_strategy.tmp_o1_dataset WHERE source = 'S1' GROUP BY ALL),
zc AS (SELECT c.sid, c.firm_crd, c.broker_name, ce.opp
       FROM c JOIN sc ON sc.sid = c.sid AND c.route = sc.s1_channel JOIN s ON s.sid = c.sid
       JOIN ssdb_integration.lr_strategy.tmp_sales_product p ON p.value = UPPER(TRIM(s.raw_product))
       JOIN cell ce ON ce.zip = s.zip AND ce.product = p.product AND ce.firm_crd = c.firm_crd
                   AND ce.broker_name = c.broker_name),
z AS (SELECT sid, COUNT(*) AS n_zip, MIN(firm_crd) AS crd, MIN(broker_name) AS nm FROM zc GROUP BY ALL),
zo AS (SELECT sid, firm_crd AS crd, broker_name AS nm
       FROM (SELECT zc.*, ROW_NUMBER() OVER (PARTITION BY sid ORDER BY opp DESC, firm_crd, broker_name) AS rn,
                    LEAD(opp) OVER (PARTITION BY sid ORDER BY opp DESC, firm_crd, broker_name) AS next_opp
             FROM zc) x
       WHERE rn = 1 AND opp > next_opp),
cz AS (SELECT s.sales_firm_id, s.mga_agent_cd, sc.s1_channel, COUNT(DISTINCT z.crd || '|' || z.nm) AS k,
              MIN(z.crd) AS crd, MIN(z.nm) AS nm
       FROM s JOIN sc ON sc.sid = s.sid JOIN m ON m.sid = s.sid AND m.n_match > 1 JOIN z ON z.sid = s.sid AND z.n_zip = 1
       WHERE s.mga_agent_cd IS NOT NULL GROUP BY ALL)
SELECT 'S1' AS source, s.seller_key, s.seller, s.sales_firm_id, s.sales_firm, s.mga_agent_cd, s.zip, s.raw_product, s.old_channel,
       s.old_channel AS old_channel_s1, sc.s1_channel AS match_channel,
       CASE WHEN s.sales_firm_id IS NULL THEN 'NO COMPANY' WHEN k.sid IS NULL THEN 'NO MARKET METRICS FIRM'
            WHEN k.n_firms = 1 THEN 'ONE FIRM' WHEN m.n_match = 1 THEN 'SPLIT, MATCHED BY CHANNEL'
            WHEN m.n_match > 1 AND z.n_zip = 1 THEN 'SPLIT, MATCHED BY ZIP'
            WHEN m.n_match > 1 AND cz.k = 1 THEN 'SPLIT, MATCHED BY MGA CODE'
            WHEN m.n_match > 1 AND zo.sid IS NOT NULL THEN 'SPLIT, MOST OPPORTUNITY AT ZIP'
            WHEN m.n_match > 1 THEN 'SPLIT, 2+ CHANNEL MATCHES' ELSE 'SPLIT, NO CHANNEL MATCH' END AS firm_basis,
       CASE WHEN k.n_firms = 1 THEN k.crd WHEN m.n_match = 1 THEN m.crd WHEN m.n_match > 1 AND z.n_zip = 1 THEN z.crd
            WHEN m.n_match > 1 AND cz.k = 1 THEN cz.crd WHEN m.n_match > 1 AND zo.sid IS NOT NULL THEN zo.crd END AS firm_crd,
       CASE WHEN k.n_firms = 1 THEN k.nm WHEN m.n_match = 1 THEN m.nm WHEN m.n_match > 1 AND z.n_zip = 1 THEN z.nm
            WHEN m.n_match > 1 AND cz.k = 1 THEN cz.nm WHEN m.n_match > 1 AND zo.sid IS NOT NULL THEN zo.nm END AS broker_name,
       s.n_rows, s.sales, s.sales_alt
FROM s
JOIN sc ON sc.sid = s.sid
LEFT JOIN k ON k.sid = s.sid
LEFT JOIN m ON m.sid = s.sid
LEFT JOIN z ON z.sid = s.sid
LEFT JOIN zo ON zo.sid = s.sid
LEFT JOIN cz ON cz.sales_firm_id = s.sales_firm_id AND cz.mga_agent_cd = s.mga_agent_cd
            AND EQUAL_NULL(cz.s1_channel, sc.s1_channel);

--11. Source 2's sales, YEAR 2025, with the firm each reaches: its CRD's one broker name (TMP_O1_FIRM holds every
--CRD x broker name either source's opportunity carries), or on a CRD with 2+, the one whose firm 1 channel is the
--sale's: CHANNEL through Q19 (or a territory code as is), then Q39 read back, which is also OLD_CHANNEL_S1.
--SALES_FIRM_ID, SALES_FIRM, RAW_PRODUCT and OLD_CHANNEL are FIRM_CRD, FIRM, PRODUCT and CHANNEL as they are; each
--amount (a FLOAT) is cast to DECIMAL(38, 6) before it is summed; SALES_ALT is NULL (MM_AMOUNT is not used: Q42).
--FIRM_BASIS as in 10 (no MGA code rule: firm 2 has no codes), NO CRD for none.
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_o2_s2 AS
WITH
q39 AS (SELECT terr_channel, MIN(s1_channel) AS s1_channel FROM ssdb_integration.lr_strategy.tmp_s1ch_s2terr GROUP BY ALL),
s AS (SELECT *, ROW_NUMBER() OVER (ORDER BY sales DESC, sales_firm_id, sales_firm, seller_key, seller, zip, raw_product,
                                    old_channel) AS sid FROM (
  SELECT CAST(CAST(firm_crd AS DECIMAL(38, 0)) AS VARCHAR) AS sales_firm_id, firm AS sales_firm,
         NULLIF(UPPER(TRIM(rvp)), '') AS seller_key, rvp AS seller,
         CASE WHEN NULLIF(TRIM(zip_code), '') IS NULL THEN NULL ELSE LPAD(LEFT(TRIM(zip_code), 5), 5, '0') END AS zip,
         product AS raw_product, channel AS old_channel, COUNT(*) AS n_rows,
         SUM(CAST(sales_amount AS DECIMAL(38, 6))) AS sales, CAST(NULL AS DECIMAL(38, 6)) AS sales_alt
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
      FROM c JOIN sc ON sc.sid = c.sid WHERE c.route = sc.s1_channel GROUP BY ALL),
cell AS (SELECT zip, firm_crd, broker_name, product, SUM(opportunity) AS opp
         FROM ssdb_integration.lr_strategy.tmp_o1_dataset WHERE source = 'S2' GROUP BY ALL),
zc AS (SELECT c.sid, c.firm_crd, c.broker_name, ce.opp
       FROM c JOIN sc ON sc.sid = c.sid AND c.route = sc.s1_channel JOIN s ON s.sid = c.sid
       JOIN ssdb_integration.lr_strategy.tmp_sales_product p ON p.value = UPPER(TRIM(s.raw_product))
       JOIN cell ce ON ce.zip = s.zip AND ce.product = p.product AND ce.firm_crd = c.firm_crd
                   AND ce.broker_name = c.broker_name),
z AS (SELECT sid, COUNT(*) AS n_zip, MIN(firm_crd) AS crd, MIN(broker_name) AS nm FROM zc GROUP BY ALL),
zo AS (SELECT sid, firm_crd AS crd, broker_name AS nm
       FROM (SELECT zc.*, ROW_NUMBER() OVER (PARTITION BY sid ORDER BY opp DESC, firm_crd, broker_name) AS rn,
                    LEAD(opp) OVER (PARTITION BY sid ORDER BY opp DESC, firm_crd, broker_name) AS next_opp
             FROM zc) x
       WHERE rn = 1 AND opp > next_opp)
SELECT 'S2' AS source, s.seller_key, s.seller, s.sales_firm_id, s.sales_firm, CAST(NULL AS VARCHAR) AS mga_agent_cd, s.zip, s.raw_product, s.old_channel,
       sc.s1_channel AS old_channel_s1, sc.s1_channel AS match_channel,
       CASE WHEN s.sales_firm_id IS NULL THEN 'NO CRD' WHEN k.sid IS NULL THEN 'NO MARKET METRICS FIRM'
            WHEN k.n_firms = 1 THEN 'ONE FIRM' WHEN m.n_match = 1 THEN 'SPLIT, MATCHED BY CHANNEL'
            WHEN m.n_match > 1 AND z.n_zip = 1 THEN 'SPLIT, MATCHED BY ZIP'
            WHEN m.n_match > 1 AND zo.sid IS NOT NULL THEN 'SPLIT, MOST OPPORTUNITY AT ZIP'
            WHEN m.n_match > 1 THEN 'SPLIT, 2+ CHANNEL MATCHES' ELSE 'SPLIT, NO CHANNEL MATCH' END AS firm_basis,
       CASE WHEN k.n_firms = 1 THEN k.crd WHEN m.n_match = 1 THEN m.crd WHEN m.n_match > 1 AND z.n_zip = 1 THEN z.crd
            WHEN m.n_match > 1 AND zo.sid IS NOT NULL THEN zo.crd END AS firm_crd,
       CASE WHEN k.n_firms = 1 THEN k.nm WHEN m.n_match = 1 THEN m.nm WHEN m.n_match > 1 AND z.n_zip = 1 THEN z.nm
            WHEN m.n_match > 1 AND zo.sid IS NOT NULL THEN zo.nm END AS broker_name,
       s.n_rows, s.sales, s.sales_alt
FROM s
JOIN sc ON sc.sid = s.sid
LEFT JOIN k ON k.sid = s.sid
LEFT JOIN m ON m.sid = s.sid
LEFT JOIN z ON z.sid = s.sid
LEFT JOIN zo ON zo.sid = s.sid;

--12. Both sources' sales with the firm's new channel (a firm 1 sale with no firm: its company's on the new-channel
--list, else IMO for firm 1's marketing organizations (owner, 2026-11-01: "yes relabel as IMO"), else UNMAPPED; a sale still
--without a firm takes the manual assignment, FIRM_BASIS MANUAL, and the owner's
--sales channel where one is set), where the sale lands (CELL_STATUS: on a ZIP x firm x product of TMP_O1_DATASET or why not), and whether its seller holds that cell
--in the old and the new state (source 1 by wholesaler ID, source 2 by RVP: its territory IDs are seats, not people).
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_o2_sales AS
WITH
u0 AS (SELECT * FROM ssdb_integration.lr_strategy.tmp_o2_s1 UNION ALL SELECT * FROM ssdb_integration.lr_strategy.tmp_o2_s2),
ok AS (SELECT o.source, o.sales_firm_id, o.sales_firm, o.raw_channel, o.mga_agent_cd,
              COUNT(DISTINCT f.firm_crd || '|' || f.broker_name) AS k, MIN(f.firm_crd) AS crd, MIN(f.broker_name) AS nm
       FROM ssdb_integration.lr_strategy.tmp_sales_firm_override o
       JOIN ssdb_integration.lr_strategy.tmp_o1_firm f ON f.firm_crd = o.firm_crd AND UPPER(f.broker_name) = o.broker_name
       GROUP BY ALL),
u AS (SELECT u0.source, u0.seller_key, u0.seller, u0.sales_firm_id, u0.sales_firm, u0.mga_agent_cd, u0.zip,
             u0.raw_product, u0.old_channel, u0.old_channel_s1, u0.match_channel,
             CASE WHEN u0.firm_crd IS NULL AND COALESCE(oe.k, oa.k) = 1 THEN 'MANUAL' ELSE u0.firm_basis END AS firm_basis,
             CASE WHEN u0.firm_crd IS NULL AND COALESCE(oe.k, oa.k) = 1 THEN COALESCE(oe.crd, oa.crd)
                  ELSE u0.firm_crd END AS firm_crd,
             CASE WHEN u0.firm_crd IS NULL AND COALESCE(oe.k, oa.k) = 1 THEN COALESCE(oe.nm, oa.nm)
                  ELSE u0.broker_name END AS broker_name,
             u0.n_rows, u0.sales, u0.sales_alt
      FROM u0
      LEFT JOIN ok oe ON oe.source = u0.source AND EQUAL_NULL(oe.sales_firm_id, u0.sales_firm_id)
                     AND EQUAL_NULL(oe.sales_firm, UPPER(TRIM(u0.sales_firm)))
                     AND EQUAL_NULL(oe.raw_channel, UPPER(TRIM(u0.old_channel)))
                     AND oe.mga_agent_cd = UPPER(TRIM(u0.mga_agent_cd))
      LEFT JOIN ok oa ON oa.source = u0.source AND EQUAL_NULL(oa.sales_firm_id, u0.sales_firm_id)
                     AND EQUAL_NULL(oa.sales_firm, UPPER(TRIM(u0.sales_firm)))
                     AND EQUAL_NULL(oa.raw_channel, UPPER(TRIM(u0.old_channel)))
                     AND oa.mga_agent_cd IS NULL),
co AS (SELECT source, sales_firm_id, sales_firm, raw_channel, mga_agent_cd, COUNT(DISTINCT new_channel) AS k,
              MIN(new_channel) AS ch
       FROM ssdb_integration.lr_strategy.tmp_sales_channel_override GROUP BY ALL),
h AS (SELECT DISTINCT source, zip, firm_crd, broker_name, product,
             CASE WHEN source = 'S1' THEN TRIM(old_wholesaler_id) ELSE UPPER(TRIM(old_wholesaler)) END AS old_key,
             CASE WHEN source = 'S1' THEN TRIM(new_wholesaler_id) ELSE UPPER(TRIM(new_wholesaler)) END AS new_key
      FROM ssdb_integration.lr_strategy.tmp_o1_dataset),
cell AS (SELECT DISTINCT source, zip, firm_crd, broker_name, product FROM h),
ho AS (SELECT DISTINCT source, zip, firm_crd, broker_name, product, old_key AS w FROM h WHERE old_key IS NOT NULL),
hn AS (SELECT DISTINCT source, zip, firm_crd, broker_name, product, new_key AS w FROM h WHERE new_key IS NOT NULL)
SELECT u.source, u.seller_key, u.seller, u.sales_firm_id, u.sales_firm, u.mga_agent_cd, u.zip, u.raw_product, p.product,
       u.old_channel, u.old_channel_s1, u.match_channel, u.firm_basis, u.firm_crd, u.broker_name,
       COALESCE(CASE WHEN (u.firm_basis = 'MANUAL' OR u.firm_crd IS NULL) AND COALESCE(ce1.k, ca1.k) = 1
                     THEN COALESCE(ce1.ch, ca1.ch) END,
                f.new_label, nl.new_label,
                CASE WHEN u.source = 'S1' AND u.firm_basis = 'NO MARKET METRICS FIRM' AND sl.label IS NOT NULL THEN 'IMO' END,
                'UNMAPPED') AS new_channel,
       CASE WHEN u.firm_crd IS NULL THEN 'NO FIRM' WHEN u.zip IS NULL THEN 'NO ZIP' WHEN p.product IS NULL THEN 'NO PRODUCT'
            WHEN ce.source IS NULL THEN 'NO OPPORTUNITY CELL' ELSE 'ON A CELL WITH OPPORTUNITY' END AS cell_status,
       ho.w IS NOT NULL AS held_old, hn.w IS NOT NULL AS held_new, u.n_rows, u.sales, u.sales_alt
FROM u
LEFT JOIN ssdb_integration.lr_strategy.tmp_sales_product p ON p.value = UPPER(TRIM(u.raw_product))
LEFT JOIN ssdb_integration.lr_strategy.tmp_o1_firm f ON f.firm_crd = u.firm_crd AND f.broker_name = u.broker_name
LEFT JOIN ssdb_integration.lr_strategy.tmp_s1_sale_channel sl ON sl.label = UPPER(TRIM(u.old_channel))
LEFT JOIN ssdb_integration.lr_strategy.tmp_new_label nl ON u.source = 'S1' AND u.firm_crd IS NULL
                                                       AND nl.company_id = u.sales_firm_id
LEFT JOIN co ce1 ON ce1.source = u.source AND EQUAL_NULL(ce1.sales_firm_id, u.sales_firm_id)
                  AND EQUAL_NULL(ce1.sales_firm, UPPER(TRIM(u.sales_firm)))
                  AND EQUAL_NULL(ce1.raw_channel, UPPER(TRIM(u.old_channel)))
                  AND ce1.mga_agent_cd = UPPER(TRIM(u.mga_agent_cd))
LEFT JOIN co ca1 ON ca1.source = u.source AND EQUAL_NULL(ca1.sales_firm_id, u.sales_firm_id)
                  AND EQUAL_NULL(ca1.sales_firm, UPPER(TRIM(u.sales_firm)))
                  AND EQUAL_NULL(ca1.raw_channel, UPPER(TRIM(u.old_channel))) AND ca1.mga_agent_cd IS NULL
LEFT JOIN cell ce ON ce.source = u.source AND ce.zip = u.zip AND ce.firm_crd = u.firm_crd
                 AND ce.broker_name = u.broker_name AND ce.product = p.product
LEFT JOIN ho ON ho.source = u.source AND ho.zip = u.zip AND ho.firm_crd = u.firm_crd
               AND ho.broker_name = u.broker_name AND ho.product = p.product AND ho.w = u.seller_key
LEFT JOIN hn ON hn.source = u.source AND hn.zip = u.zip AND hn.firm_crd = u.firm_crd
               AND hn.broker_name = u.broker_name AND hn.product = p.product AND hn.w = u.seller_key;

--13. The dataset: every 2025 sale and every opportunity cell (TMP_O1_DATASET), each under its wholesaler.
--OLD_CHANNEL: on opportunity, the cell's old channel (TMP_O1_DATASET); on sales, the sale's own channel as its sales
--table has it (firm 1's DIST_CH), so SUM(SALES) for a cut on PRODUCT and OLD_CHANNEL is the sales table's for the same
--cut on its product (PRODUCT_LINE2 maps 1 : 1) and channel (owner, 2026-10-30: "I want to validate against the
--original dist_ch").  A sale shares a row with its cell's opportunity where the two old channels agree.
--OLD_CHANNEL_S1: firm 1's is OLD_CHANNEL; firm 2's is in firm 1's names (Q19, then Q39 read back).  OPP_HELD_OLD,
--OPP_HELD_NEW: TMP_O1_DATASET's opportunity under its old and its new wholesaler.  SALES: credited to the seller (firm
--1's actual sales, firm 2's SALES_AMOUNT); SALES_ALT: firm 1's comp'd sales, NULL for firm 2 (Q42).
--SALES_IN_HELD_CELLS_OLD and _NEW: the part of SALES whose seller holds that ZIP x firm x product in that state.
--WHOLESALER_KEY: firm 1's wholesaler ID, firm 2's RVP.  No key: opportunity no one holds, or sales with no seller.
--Sales with no market metrics firm sit under a blank firm, new channel as statement 12 sets it (the owner's, the
--new-channel list's, IMO for firm 1's marketing organizations, else UNMAPPED); TMP_O2_SALES has their sales table's firm.
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
                   old_channel_s1, new_channel, opportunity AS opp_old, 0 AS opp_new,
                   0 AS sales, 0 AS sales_alt, 0 AS held_old, 0 AS held_new
            FROM ds
  UNION ALL SELECT source, new_key, new_nm, zip, firm_crd, broker_name, product, old_channel, old_channel_s1,
                   new_channel, 0, opportunity, 0, 0, 0, 0
            FROM ds
  UNION ALL SELECT source, seller_key, seller, zip, firm_crd, broker_name, product, old_channel, old_channel_s1,
                   new_channel, 0, 0, sales, sales_alt, CASE WHEN held_old THEN sales ELSE 0 END,
                   CASE WHEN held_new THEN sales ELSE 0 END
            FROM ssdb_integration.lr_strategy.tmp_o2_sales)
SELECT source, w_key AS wholesaler_key, MIN(w_nm) AS wholesaler, zip, firm_crd, broker_name, product, old_channel,
       old_channel_s1, new_channel, SUM(opp_old) AS opp_held_old, SUM(opp_new) AS opp_held_new, SUM(sales) AS sales,
       SUM(sales_alt) AS sales_alt,
       SUM(held_old) AS sales_in_held_cells_old, SUM(held_new) AS sales_in_held_cells_new
FROM f
GROUP BY ALL;

--14. Sizes, the tie-out and checks, one table; AMT is sales $ unless the name says otherwise.  PCT_AMT: of PART x
--SOURCE x NAME.
--  SALES FIRM BASIS, SALES NEW CHANNEL, SALES PRODUCT (value -> product), SALES CHANNEL (the sale's channel -> the firm 1 channel that
--    picks its firm): all of a source's 2025 sales.  SALES ON CELLS: CELL, and SOLD BY THE
--    CELL'S HOLDER (old, new).  Q35: source 1's sales by how MM_MAP and CRD_TO_CBD map their company ID against the
--    firm found here.  SALES PERIOD: each sales table by year, firm 1's also by product bucket (s1_sales.sql keeps only
--    ALL, :439), before the 2025 filter.  WHOLESALERS: per source and state, wholesalers (N_WHOLESALERS) that
--    hold opportunity and sell, sell holding none, hold some with no sales; AMT their sales.
--  TIE-OUT: the owner's cut of firm 1's sales (PRODUCT_LINE2 <> 'FIXED' AND DIST_CH IN ('WH', 'FI', 'IFA')), actual and
--    comp'd: the sales table by fiscal year, and TMP_O2_DATASET's 2025 (PRODUCT, OLD_CHANNEL).
--  CHECKS (MUST BE 0): each sales table against TMP_O2_SALES by firm x MGA code x channel x product
--    as the sales table has them (N_ROWS: groups that differ; AMT: their $); the tie-out, sales table minus dataset;
--    the dataset's opportunity and sales against their sources; company lists over 10 parts.
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_o2_out AS
WITH
s AS (SELECT * FROM ssdb_integration.lr_strategy.tmp_o2_sales),
sk AS (SELECT DISTINCT source, sales_firm_id, UPPER(TRIM(sales_firm)) AS sales_firm,
              UPPER(TRIM(old_channel)) AS raw_channel, UPPER(TRIM(mga_agent_cd)) AS mga_agent_cd,
              firm_basis = 'MANUAL' OR firm_crd IS NULL AS manual_or_open
       FROM ssdb_integration.lr_strategy.tmp_o2_sales),
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
       FROM ssdb_integration.lr_strategy.tmp_o2_dataset WHERE wholesaler_key IS NOT NULL GROUP BY ALL),
tb AS (SELECT CAST(fiscal_yr AS VARCHAR) AS fy, COUNT(*) AS n, SUM(actual_agent_dollars) AS act,
              SUM(compd_agent_dollars) AS comp
       FROM IDENTIFIER($s1_sales)
       WHERE product_bucket = 'ALL' AND product_line2 <> 'FIXED' AND dist_ch IN ('WH', 'FI', 'IFA')
       GROUP BY ALL),
td AS (SELECT SUM(sales) AS act, SUM(sales_alt) AS comp FROM ssdb_integration.lr_strategy.tmp_o2_dataset
       WHERE source = 'S1' AND product <> 'FIXED' AND old_channel IN ('WH', 'FI', 'IFA')),
am AS (SELECT * FROM (VALUES ('ACTUAL'), ('COMP''D')) AS x (amount)),
gd AS (SELECT source, firm_id, mga, channel, product, SUM(a1) AS d1, SUM(a2) AS d2 FROM (
            SELECT 'S1' AS source, NULLIF(CAST(CAST(consol_brkr_dlr_id AS DECIMAL(38, 0)) AS VARCHAR), '0') AS firm_id,
                   NULLIF(TRIM(CAST(mga_agent_cd AS VARCHAR)), '') AS mga, dist_ch AS channel, product_line2 AS product, CAST(actual_agent_dollars AS DECIMAL(38, 6)) AS a1,
                   CAST(compd_agent_dollars AS DECIMAL(38, 6)) AS a2
            FROM IDENTIFIER($s1_sales) WHERE fiscal_yr = 2025 AND product_bucket = 'ALL'
  UNION ALL SELECT 'S2', CAST(CAST(firm_crd AS DECIMAL(38, 0)) AS VARCHAR), CAST(NULL AS VARCHAR), channel, product,
                   CAST(sales_amount AS DECIMAL(38, 6)), CAST(NULL AS DECIMAL(38, 6))
            FROM IDENTIFIER($s2_sales) WHERE year = 2025
  UNION ALL SELECT source, sales_firm_id, mga_agent_cd, old_channel, raw_product, -sales, -sales_alt
            FROM ssdb_integration.lr_strategy.tmp_o2_sales) x
       GROUP BY ALL),
v AS (
            SELECT 'SALES FIRM BASIS' AS part, source, CAST(NULL AS VARCHAR) AS name, firm_basis AS item,
                   seller_key, firm_crd, broker_name, n_rows, sales AS amt
            FROM s
  UNION ALL SELECT 'SALES PRODUCT', source, NULL, COALESCE(raw_product, '(BLANK)') || ' -> ' || COALESCE(product, 'UNMAPPED'),
                   seller_key, firm_crd, broker_name, n_rows, sales FROM s
  UNION ALL SELECT 'SALES CHANNEL', source, NULL,
                   COALESCE(old_channel, '(BLANK)') || ' -> ' || COALESCE(match_channel, '(NONE)'),
                   seller_key, firm_crd, broker_name, n_rows, sales FROM s
  UNION ALL SELECT 'SALES NEW CHANNEL', source, NULL, new_channel, seller_key, firm_crd, broker_name, n_rows, sales FROM s
  UNION ALL SELECT 'SALES ON CELLS', source, 'CELL', cell_status, seller_key, firm_crd, broker_name, n_rows, sales
            FROM s
  UNION ALL SELECT 'SALES ON CELLS', source, 'SOLD BY THE CELL''S HOLDER, OLD', CASE WHEN held_old THEN 'YES' ELSE 'NO' END,
                   seller_key, firm_crd, broker_name, n_rows, sales FROM s
  UNION ALL SELECT 'SALES ON CELLS', source, 'SOLD BY THE CELL''S HOLDER, NEW', CASE WHEN held_new THEN 'YES' ELSE 'NO' END,
                   seller_key, firm_crd, broker_name, n_rows, sales FROM s
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
SELECT 'TIE-OUT', 'S1', 'DATASET: PRODUCT <> FIXED, OLD_CHANNEL IN (WH, FI, IFA), ' || am.amount, '2025', NULL,
       NULL, NULL, CASE WHEN am.amount = 'ACTUAL' THEN td.act ELSE td.comp END
FROM td CROSS JOIN am
UNION ALL
SELECT 'CHECKS', 'S1', 'TIE-OUT: SALES TABLE MINUS DATASET, 2025, ACTUAL + COMP''D (MUST BE 0)', NULL, NULL, NULL, NULL,
       ROUND(ABS(COALESCE(t.act, 0) - COALESCE(d.act, 0)) + ABS(COALESCE(t.comp, 0) - COALESCE(d.comp, 0)), 2)
FROM (SELECT SUM(act) AS act, SUM(comp) AS comp FROM tb WHERE fy = '2025') t
CROSS JOIN (SELECT SUM(act) AS act, SUM(comp) AS comp FROM td) d
UNION ALL
SELECT 'CHECKS', source, 'SALES TABLE MINUS TMP_O2_SALES BY FIRM X MGA X CHANNEL X PRODUCT, 2025 (MUST BE 0)', NULL,
       SUM(CASE WHEN ROUND(COALESCE(d1, 0), 2) <> 0 OR ROUND(COALESCE(d2, 0), 2) <> 0 THEN 1 ELSE 0 END), NULL, NULL,
       ROUND(SUM(ABS(COALESCE(d1, 0)) + ABS(COALESCE(d2, 0))), 2)
FROM gd GROUP BY ALL
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
SELECT 'CHECKS', NULL, 'MANUAL KEYS ON 2+ FIRMS, NOT APPLIED (MUST BE 0)', NULL, NULL, NULL, NULL, COUNT(*)
FROM (SELECT source, sales_firm_id, sales_firm, raw_channel, mga_agent_cd,
             COUNT(DISTINCT firm_crd || '|' || broker_name) AS k
      FROM ssdb_integration.lr_strategy.tmp_sales_firm_override GROUP BY ALL) x
WHERE k > 1
UNION ALL
SELECT 'CHECKS', NULL, 'MANUAL FIRMS NOT IN TMP_O1_FIRM, NOT APPLIED (MUST BE 0)', NULL, NULL, NULL, NULL, COUNT(*)
FROM ssdb_integration.lr_strategy.tmp_sales_firm_override o
LEFT JOIN ssdb_integration.lr_strategy.tmp_o1_firm f ON f.firm_crd = o.firm_crd AND UPPER(f.broker_name) = o.broker_name
WHERE f.firm_crd IS NULL
UNION ALL
SELECT 'CHECKS', NULL, 'MANUAL ROWS MATCHING NO SALE, NOT APPLIED (MUST BE 0)', NULL, NULL, NULL, NULL, COUNT(*)
FROM (SELECT o.source, o.sales_firm_id, o.sales_firm, o.raw_channel, o.mga_agent_cd, o.firm_crd, o.broker_name,
             COUNT(x.source) AS hits
      FROM ssdb_integration.lr_strategy.tmp_sales_firm_override o
      LEFT JOIN sk x ON x.source = o.source AND EQUAL_NULL(x.sales_firm_id, o.sales_firm_id)
                    AND EQUAL_NULL(x.sales_firm, o.sales_firm) AND EQUAL_NULL(x.raw_channel, o.raw_channel)
                    AND (o.mga_agent_cd IS NULL OR x.mga_agent_cd = o.mga_agent_cd)
      GROUP BY ALL) y
WHERE hits = 0
UNION ALL
SELECT 'CHECKS', NULL, 'SALES CHANNELS: KEYS ON 2+ CHANNELS, NOT APPLIED (MUST BE 0)', NULL, NULL, NULL, NULL, COUNT(*)
FROM (SELECT source, sales_firm_id, sales_firm, raw_channel, mga_agent_cd, COUNT(DISTINCT new_channel) AS k
      FROM ssdb_integration.lr_strategy.tmp_sales_channel_override GROUP BY ALL) x
WHERE k > 1
UNION ALL
SELECT 'CHECKS', NULL, 'SALES CHANNELS: ROWS MATCHING NO MANUAL OR UNMATCHED SALE, NOT APPLIED (MUST BE 0)', NULL, NULL, NULL, NULL, COUNT(*)
FROM (SELECT o.source, o.sales_firm_id, o.sales_firm, o.raw_channel, o.mga_agent_cd, o.new_channel,
             COUNT(x.source) AS hits
      FROM ssdb_integration.lr_strategy.tmp_sales_channel_override o
      LEFT JOIN sk x ON x.source = o.source AND EQUAL_NULL(x.sales_firm_id, o.sales_firm_id)
                    AND EQUAL_NULL(x.sales_firm, o.sales_firm) AND EQUAL_NULL(x.raw_channel, o.raw_channel)
                    AND (o.mga_agent_cd IS NULL OR x.mga_agent_cd = o.mga_agent_cd) AND x.manual_or_open
      GROUP BY ALL) y
WHERE hits = 0
UNION ALL
SELECT 'CHECKS', 'S1', 'COMPANY LISTS OVER 10 PARTS (MUST BE 0)', NULL, NULL, NULL, NULL, COUNT(*)
FROM ssdb_integration.lr_strategy.tmp_o1_rows_s1 WHERE SPLIT_PART(company_id, '|', 11) <> '';

--15. The review list for manual assignments (TMP_SALES_REVIEW): every 2025 sale still without a market metrics firm,
--both sources, one row per review key x candidate firm.  Key: SOURCE, SALES_FIRM_ID (firm 1 CONSOL_BRKR_DLR_ID,
--firm 2 FIRM_CRD), SALES_FIRM (CONSOL_BROKER_NM, FIRM), RAW_CHANNEL (DIST_CH, CHANNEL), MGA_AGENT_CD, as the sales
--table has them.  IS_IMO: the key's sales have new channel IMO (firm 1's marketing organizations, statement 12, and
--sales the owner set to IMO), kept here with no candidates and left out of the REVIEW part (owner, 2026-10-31:
--"imo's stay out").  Candidates: one of the company's firms (firm 1: its opportunity rows carry the company; firm 2:
--a name on the CRD), a map's (MM_MAP, CRD_TO_CBD: firm 1's company to the firm's CRD), or one of the 5 market metrics
--names most like the sales firm name (JAROWINKLER_SIMILARITY 85 or more).  Evidence, 1 or 0: EV_COMPANY, EV_MM_MAP,
--EV_CRD_TO_CBD, EV_CHANNEL (the firm's route is the sale's channel); EV_NAME: name similarity, 0-1 (1 = the same name).
--ZIP_AMT: the key's $ sold at a ZIP x product where the firm has opportunity.  SCORE: EV_ sum + ZIP_AMT / KEY_AMT (0-6);
--RANK_IN_KEY 1 the strongest (ties: ZIP_AMT, then CRD, name); a key with no candidate has one row.  KEY_AMT: the
--key's $ on every row; RANK_KEY_BY_AMT: within the source, 1 the largest.  TOP_WHOLESALER: the key's largest seller's
--name (firm 1 WHSLR_NM, firm 2 RVP; owner, 2026-10-31: "include the wholesaler name column and drop the wholesaler id
--column for the review extract").  Assign by hand in tmp_sales_firm_override (statement 8): any firm in TMP_O1_FIRM,
--a candidate here or typed.
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_sales_review AS
WITH
u AS (SELECT * FROM ssdb_integration.lr_strategy.tmp_o2_sales WHERE firm_crd IS NULL),
g AS (SELECT x.*, ROW_NUMBER() OVER (ORDER BY source, sales_firm_id, sales_firm, raw_channel, mga_agent_cd, firm_basis,
                                              match_channel) AS kid
      FROM (SELECT source, sales_firm_id, sales_firm, old_channel AS raw_channel, mga_agent_cd, firm_basis, match_channel,
                   SUM(n_rows) AS n_rows, COUNT(DISTINCT seller_key) AS n_wholesalers, COUNT(DISTINCT zip) AS n_zips,
                   SUM(sales) AS amt, SUM(sales_alt) AS amt_alt, MAX(CASE WHEN new_channel = 'IMO' THEN 1 ELSE 0 END) AS any_imo
            FROM u GROUP BY ALL) x),
gi AS (SELECT g.*, g.any_imo = 1 AS is_imo FROM g),
ug AS (SELECT u.*, g.kid
       FROM u JOIN g ON g.source = u.source AND EQUAL_NULL(g.sales_firm_id, u.sales_firm_id)
                    AND EQUAL_NULL(g.sales_firm, u.sales_firm) AND EQUAL_NULL(g.raw_channel, u.old_channel)
                    AND EQUAL_NULL(g.mga_agent_cd, u.mga_agent_cd) AND g.firm_basis = u.firm_basis
                    AND EQUAL_NULL(g.match_channel, u.match_channel)),
maps AS (
            SELECT 'MM_MAP' AS map, CAST(CAST(CASE WHEN cbd_id = 0 THEN firm_client_id ELSE cbd_id END AS DECIMAL(38, 0))
                                         AS VARCHAR) AS company_id, CAST(CAST(firm_crd AS DECIMAL(38, 0)) AS VARCHAR) AS crd
            FROM ssdb_integration.lr_strategy.mm_map
  UNION ALL SELECT 'CRD_TO_CBD', CAST(CAST(cbd_id AS DECIMAL(38, 0)) AS VARCHAR), CAST(CAST(firm_crd AS DECIMAL(38, 0)) AS VARCHAR)
            FROM ssdb_integration.lr_strategy.crd_to_cbd),
mk AS (SELECT DISTINCT map, company_id, crd FROM maps WHERE company_id IS NOT NULL AND crd IS NOT NULL),
f AS (SELECT firm_crd, broker_name, route FROM ssdb_integration.lr_strategy.tmp_o1_firm),
gc AS (SELECT * FROM gi WHERE NOT is_imo),
fz AS (SELECT kid, firm_crd, broker_name
       FROM (SELECT y.*, ROW_NUMBER() OVER (PARTITION BY kid ORDER BY sim DESC, firm_crd, broker_name) AS rn
             FROM (SELECT gc.kid, f.firm_crd, f.broker_name,
                          JAROWINKLER_SIMILARITY(TRIM(gc.sales_firm), TRIM(f.broker_name)) AS sim
                   FROM gc CROSS JOIN f WHERE gc.sales_firm IS NOT NULL) y) x
       WHERE sim >= 85 AND rn <= 5),
c0 AS (
            SELECT gc.kid, cf.firm_crd, cf.broker_name, 'COMPANY' AS ev
            FROM gc JOIN ssdb_integration.lr_strategy.tmp_o2_company_firm cf
                      ON gc.source = 'S1' AND cf.company_id = gc.sales_firm_id
  UNION ALL SELECT gc.kid, f.firm_crd, f.broker_name, 'COMPANY' FROM gc JOIN f ON gc.source = 'S2' AND f.firm_crd = gc.sales_firm_id
  UNION ALL SELECT gc.kid, f.firm_crd, f.broker_name, mk.map
            FROM gc JOIN mk ON gc.source = 'S1' AND mk.company_id = gc.sales_firm_id JOIN f ON f.firm_crd = mk.crd
  UNION ALL SELECT kid, firm_crd, broker_name, 'NAME' FROM fz),
c AS (SELECT kid, firm_crd, broker_name, MAX(CASE WHEN ev = 'COMPANY' THEN 1 ELSE 0 END) AS ev_company,
             MAX(CASE WHEN ev = 'MM_MAP' THEN 1 ELSE 0 END) AS ev_mm_map,
             MAX(CASE WHEN ev = 'CRD_TO_CBD' THEN 1 ELSE 0 END) AS ev_crd_to_cbd
      FROM c0 GROUP BY ALL),
cell AS (SELECT DISTINCT source, zip, firm_crd, broker_name, product FROM ssdb_integration.lr_strategy.tmp_o1_dataset),
zc AS (SELECT c.kid, c.firm_crd, c.broker_name, SUM(ug.sales) AS zip_amt
       FROM c JOIN ug ON ug.kid = c.kid
       JOIN cell ce ON ce.source = ug.source AND ce.zip = ug.zip AND ce.product = ug.product
                   AND ce.firm_crd = c.firm_crd AND ce.broker_name = c.broker_name
       GROUP BY ALL),
w AS (SELECT kid, seller_key, MIN(seller) AS seller, SUM(sales) AS amt FROM ug GROUP BY ALL),
wt AS (SELECT kid, seller_key, seller, ROW_NUMBER() OVER (PARTITION BY kid ORDER BY amt DESC, seller_key) AS rn FROM w),
x AS (SELECT g.*, nl.new_label AS new_list_label, wt.seller AS top_wholesaler,
             c.firm_crd AS cand_firm_crd, c.broker_name AS cand_broker_name, f.route AS cand_route, c.ev_company,
             CASE WHEN c.kid IS NULL THEN NULL WHEN f.route = g.match_channel THEN 1 ELSE 0 END AS ev_channel,
             c.ev_mm_map, c.ev_crd_to_cbd,
             CASE WHEN c.kid IS NOT NULL
                  THEN COALESCE(JAROWINKLER_SIMILARITY(TRIM(g.sales_firm), TRIM(c.broker_name)), 0) / 100.0 END AS ev_name,
             CASE WHEN c.kid IS NOT NULL THEN COALESCE(zc.zip_amt, 0) END AS zip_amt
      FROM gi g
      LEFT JOIN c ON c.kid = g.kid
      LEFT JOIN f ON f.firm_crd = c.firm_crd AND f.broker_name = c.broker_name
      LEFT JOIN zc ON zc.kid = c.kid AND zc.firm_crd = c.firm_crd AND zc.broker_name = c.broker_name
      LEFT JOIN wt ON wt.kid = g.kid AND wt.rn = 1
      LEFT JOIN ssdb_integration.lr_strategy.tmp_new_label nl ON g.source = 'S1' AND nl.company_id = g.sales_firm_id),
y AS (SELECT x.*, ev_company + ev_channel + ev_mm_map + ev_crd_to_cbd + ev_name
                  + COALESCE(ROUND(zip_amt / NULLIF(amt, 0), 2), 0) AS score
      FROM x)
SELECT source, sales_firm_id, sales_firm, raw_channel, mga_agent_cd, firm_basis, match_channel, is_imo, new_list_label,
       top_wholesaler, n_wholesalers, n_zips, n_rows,
       DENSE_RANK() OVER (PARTITION BY source, is_imo ORDER BY amt DESC) AS rank_key_by_amt, amt AS key_amt,
       amt_alt AS key_amt_alt, COUNT(cand_firm_crd) OVER (PARTITION BY kid) AS n_candidates,
       ROW_NUMBER() OVER (PARTITION BY kid ORDER BY score DESC NULLS LAST, zip_amt DESC NULLS LAST, cand_firm_crd,
                                                    cand_broker_name) AS rank_in_key,
       cand_firm_crd, cand_broker_name, cand_route, ev_company, ev_channel, ev_mm_map, ev_crd_to_cbd, ev_name, zip_amt,
       score
FROM y;

--16. The review parts: REVIEW (statement 15 without the IMO keys; AMT is KEY_AMT on RANK_IN_KEY 1 rows only, so a
--sum over AMT counts each key once), SUMMARY (keys, N_KEYS, and $ by source x FIRM_BASIS x the top candidate's
--evidence, ITEM, or IMO, LEFT OUT), CHECKS (the list's $ against TMP_O2_SALES).  PCT_AMT: of PART x SOURCE.
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_um_out AS
WITH
r AS (SELECT * FROM ssdb_integration.lr_strategy.tmp_sales_review),
t AS (SELECT source, SUM(sales) AS amt FROM ssdb_integration.lr_strategy.tmp_o2_sales WHERE firm_crd IS NULL GROUP BY ALL),
v AS (
            SELECT 'REVIEW' AS part, CAST(NULL AS VARCHAR) AS name, CAST(NULL AS VARCHAR) AS item, source,
                   sales_firm_id, sales_firm, raw_channel, mga_agent_cd, firm_basis, match_channel, new_list_label,
                   top_wholesaler, rank_key_by_amt, key_amt, n_candidates, rank_in_key, cand_firm_crd,
                   cand_broker_name, cand_route, ev_company, ev_channel, ev_mm_map, ev_crd_to_cbd, ev_name, zip_amt,
                   score, CAST(NULL AS BIGINT) AS n_keys, n_rows, n_wholesalers, n_zips,
                   CASE WHEN rank_in_key = 1 THEN key_amt END AS amt,
                   CASE WHEN rank_in_key = 1 THEN key_amt_alt END AS amt_alt
            FROM r WHERE NOT is_imo
  UNION ALL SELECT 'SUMMARY', NULL,
                   CASE WHEN is_imo THEN 'IMO, LEFT OUT' WHEN cand_firm_crd IS NULL THEN 'NO CANDIDATE' ELSE TRIM(CASE WHEN ev_company = 1 THEN 'COMPANY ' ELSE '' END
                        || CASE WHEN ev_channel = 1 THEN 'CHANNEL ' ELSE '' END
                        || CASE WHEN zip_amt <> 0 THEN 'ZIP ' ELSE '' END
                        || CASE WHEN ev_mm_map = 1 THEN 'MM_MAP ' ELSE '' END
                        || CASE WHEN ev_crd_to_cbd = 1 THEN 'CRD_TO_CBD ' ELSE '' END
                        || CASE WHEN ev_name = 1 THEN 'NAME' WHEN ev_name >= 0.85 THEN 'FUZZY NAME' ELSE '' END) END,
                   source, NULL, NULL, NULL, NULL, firm_basis, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL,
                   NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, COUNT(*), SUM(n_rows), NULL, NULL, SUM(key_amt),
                   SUM(key_amt_alt)
            FROM r WHERE rank_in_key = 1 GROUP BY ALL
  UNION ALL SELECT 'CHECKS', 'REVIEW LIST MINUS TMP_O2_SALES WITHOUT A FIRM (MUST BE 0)', NULL, t.source, NULL, NULL,
                   NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL,
                   NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, ROUND(COALESCE(SUM(r.key_amt), 0) - MAX(t.amt), 2),
                   NULL
            FROM t LEFT JOIN r ON r.source = t.source AND r.rank_in_key = 1 GROUP BY ALL)
SELECT *, ROUND(100 * amt / NULLIF(SUM(amt) OVER (PARTITION BY part, source), 0), 2) AS pct_amt
FROM v;

--17. The Tableau table (owner, 2026-11-01: "tableau reads data_withnewchannel_union_w_joinkeys"), rebuilt from
--TMP_O1_DATASET and TMP_O2_SALES as DATA_WITHNEWCHANNEL_UNION_W_JOINKEYS_V2, a permanent table with the live table's
--columns and types (CREATE TABLE ... LIKE; INSERT coerces each value to its column's type, and a value it cannot coerce
--fails the run), TERR_WHOLESALER renamed OLD_TERR_WHOLESALER and NEW_TERR_WHOLESALER added (owner: "add the new state
--holder as new_terr_wholesaler, and name the old as old_terr_wholesaler").  The owner swaps it in after the TABLEAU
--parts tie out (18).  One row per source x old, new and sales wholesaler x CRD x broker name x old channel x new
--channel x ZIP x product:
--  OLD_ and NEW_TERR_WHOLESALER: who holds the row's territory channel at its ZIP in the old and the new state (the old
--    table's holder of its DIST_CH; owner: "terr_wholesaler reflected the wholesaler who owned that territory"): a
--    cell's channels are TMP_O1_DATASET's; a sale's are its own channel (firm 2's through Q19, else as is) and its
--    firm's TAU.  Where 2+ hold, the cell's opportunity is on a row per holder (owner: "opportunity is tied to the
--    geography / territory, so it is okay if it is duplicated. sales is tied to the wholesaler though"): the old and
--    the new holders, each in ID order (firm 2: by RVP, its lowest territory ID), are paired by rank, so each holder in
--    either state has the cell once.  A sale is on one row: the pair whose old holder is its seller, else the first.
--  SALES_WHOLESALER: the seller; with no seller, and on a cell's own rows, the old territory wholesaler, so a cell's
--    opportunity shares a row with its holder's sales there (owner: "keep the sales with no seller fall back to
--    territory wholesaler").  Names as the tables have them, no 'open' (owner: "drop open").
--  CBD_ID: the CRD; FIRM: the broker name; PARENT: NULL (owner: "replace cbd_id with crd, firm with broker_name, and
--    you can leave parent as all null").  DIST_CH: the old channel in firm 1's names (a sale's own channel); NEW_DIST:
--    the new channel; CHANNEL: owner_sql/uni_latest.sql's CASE on it.  STATE: ZIP_STATE_MAP's, the lowest of a ZIP's.
--  MM_OPP: the cell's opportunity; ACTUAL_SALES_AMOUNT: the sales (owner: "actual sales amount will be our
--    sales"); SALES_AMOUNT: firm 1's comp'd sales (TMP_O2_SALES.SALES_ALT; 0 on its opportunity rows), NULL on every
--    firm 2 row (owner, 2026-11-01: "we do want to add in the compd sales to "sales_amount" instead of setting it null.
--    and ok that source 2 will be null for every row there").
--  TERR_WHOLESALER_CLEAN_NAME: NEW_TERR_WHOLESALER, the holder that goes with CHANNEL (owner, 2026-11-01, asked
--    which wholesaler to map to it: "yes make the changes"); SALES_WHOLESALER_CLEAN_NAME: the seller as the territory table
--    names that wholesaler key, else SALES_WHOLESALER, so one wholesaler has one name in both (owner, 2026-11-01: "make
--    sure terr_wholesaler_clean name, and sales_whoelsaler clean name are mapped appropriately").
--  *_TERRITORY_ID: the wholesaler keys (firm 1's ID, firm 2's RVP): the seller's, and the new holder's with
--    TERR_WHOLESALER_CLEAN_NAME; the address IDs and the HAS_TERRITORY flags
--    NULL (owner: "we do not need to replicate any of the name matching logic"; "set those ... flags to null").
--  No filter (owner: "do not propagate any filters as we are implementing them in our override instead").
--TMP_UNION holds the same rows with this script's types; look at it in the same session.
--Snowflake docs read 2026-11-01: CREATE TABLE ... LIKE copies column names and types (.../sql/create-table); ALTER
--TABLE ... RENAME COLUMN, ADD COLUMN (.../sql/alter-table-column); INSERT coerces to the column's type
--(.../sql/insert).
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_union AS
WITH
h AS (
            SELECT 'S1' AS source, t.channel, t.zip, TRIM(CAST(t.whslr_id AS VARCHAR)) AS w_key, n.nm AS w_nm,
                   ROW_NUMBER() OVER (PARTITION BY t.channel, t.zip ORDER BY t.whslr_id) AS r
            FROM (SELECT DISTINCT UPPER(TRIM(new_dist_channel)) AS channel, LPAD(LEFT(TRIM(zip), 5), 5, '0') AS zip,
                         whslr_id
                  FROM IDENTIFIER($s1_territories) WHERE whslr_id IS NOT NULL) t
            JOIN (SELECT whslr_id, MIN(whslr_nm) AS nm FROM IDENTIFIER($s1_territories) GROUP BY ALL) n
              ON n.whslr_id = t.whslr_id
  UNION ALL SELECT 'S2', t.channel, t.zip, t.w_key, n.nm,
                   ROW_NUMBER() OVER (PARTITION BY t.channel, t.zip ORDER BY t.ord, t.w_key)
            FROM (SELECT UPPER(TRIM(channel)) AS channel, LPAD(LEFT(TRIM(zipcode), 5), 5, '0') AS zip,
                         UPPER(TRIM(rvp)) AS w_key, MIN(territory_id) AS ord
                  FROM IDENTIFIER($s2_territories) WHERE NULLIF(TRIM(rvp), '') IS NOT NULL GROUP BY ALL) t
            JOIN (SELECT UPPER(TRIM(rvp)) AS w_key, MIN(rvp) AS nm FROM IDENTIFIER($s2_territories) GROUP BY ALL) n
              ON n.w_key = t.w_key),
s AS (SELECT x.*, CASE WHEN x.source = 'S1' THEN UPPER(TRIM(x.old_channel))
                       ELSE COALESCE(lt.terr_channel, UPPER(TRIM(x.old_channel))) END AS oc,
             CASE WHEN x.source = 'S1' THEN NULLIF(f.tau, 'UNMAPPED') ELSE q.terr_channel END AS nc
      FROM ssdb_integration.lr_strategy.tmp_o2_sales x
      LEFT JOIN ssdb_integration.lr_strategy.tmp_o1_firm f ON f.firm_crd = x.firm_crd AND f.broker_name = x.broker_name
      LEFT JOIN ssdb_integration.lr_strategy.tmp_s2_label_terr lt ON x.source = 'S2' AND lt.label = UPPER(TRIM(x.old_channel))
      LEFT JOIN ssdb_integration.lr_strategy.tmp_s1ch_s2terr q ON x.source = 'S2' AND q.s1_channel = f.tau),
k AS (SELECT DISTINCT source, zip, COALESCE(old_territory_channel, '') AS oc, COALESCE(new_territory_channel, '') AS nc
      FROM ssdb_integration.lr_strategy.tmp_o1_dataset
      UNION SELECT DISTINCT source, zip, COALESCE(oc, ''), COALESCE(nc, '') FROM s),
po AS (SELECT k.*, h.r, h.w_key, h.w_nm FROM k JOIN h ON h.source = k.source AND h.channel = k.oc AND h.zip = k.zip),
pn AS (SELECT k.*, h.r, h.w_key, h.w_nm FROM k JOIN h ON h.source = k.source AND h.channel = k.nc AND h.zip = k.zip),
pr AS (SELECT COALESCE(po.source, pn.source) AS source, COALESCE(po.zip, pn.zip) AS zip, COALESCE(po.oc, pn.oc) AS oc,
              COALESCE(po.nc, pn.nc) AS nc, COALESCE(po.r, pn.r) AS r, po.w_key AS old_key, po.w_nm AS old_nm,
              pn.w_key AS new_key, pn.w_nm AS new_nm
       FROM po FULL JOIN pn ON pn.source = po.source AND pn.zip = po.zip AND pn.oc = po.oc AND pn.nc = po.nc
                            AND pn.r = po.r),
u AS (
            SELECT d.source, d.zip, d.firm_crd, d.broker_name, d.product, d.old_channel_s1 AS dist_ch,
                   d.new_channel AS new_dist, p.old_key, p.old_nm, p.new_key, p.new_nm, p.old_key AS sales_key,
                   CAST(NULL AS VARCHAR) AS sales_nm, CAST(d.opportunity AS DECIMAL(38, 6)) AS mm_opp,
                   CAST(0 AS DECIMAL(38, 6)) AS sales,
                   CASE WHEN d.source = 'S1' THEN CAST(0 AS DECIMAL(38, 6)) END AS sales_comp
            FROM ssdb_integration.lr_strategy.tmp_o1_dataset d
            LEFT JOIN pr p ON p.source = d.source AND p.zip = d.zip AND p.oc = COALESCE(d.old_territory_channel, '')
                          AND p.nc = COALESCE(d.new_territory_channel, '')
  UNION ALL SELECT s.source, s.zip, s.firm_crd, s.broker_name, COALESCE(s.product, s.raw_product), s.old_channel_s1,
                   s.new_channel, p.old_key, p.old_nm, p.new_key, p.new_nm, COALESCE(s.seller_key, p.old_key), s.seller,
                   CAST(0 AS DECIMAL(38, 6)), CAST(s.sales AS DECIMAL(38, 6)), CAST(s.sales_alt AS DECIMAL(38, 6))
            FROM s
            LEFT JOIN pr a ON a.source = s.source AND a.zip = s.zip AND a.oc = COALESCE(s.oc, '')
                          AND a.nc = COALESCE(s.nc, '') AND a.old_key = s.seller_key
            LEFT JOIN pr p ON p.source = s.source AND p.zip = s.zip AND p.oc = COALESCE(s.oc, '')
                          AND p.nc = COALESCE(s.nc, '') AND p.r = COALESCE(a.r, 1)),
g AS (SELECT source, zip, firm_crd, broker_name, product, dist_ch, new_dist, old_key, new_key, sales_key,
             MIN(old_nm) AS old_nm, MIN(new_nm) AS new_nm, MIN(sales_nm) AS sales_nm, SUM(mm_opp) AS mm_opp,
             SUM(sales) AS sales, SUM(sales_comp) AS sales_comp
      FROM u GROUP BY ALL),
x AS (SELECT g.*, COALESCE(g.sales_nm, CASE WHEN EQUAL_NULL(g.sales_key, g.old_key) THEN g.old_nm END) AS sales_wh
      FROM g),
zs AS (SELECT LPAD(TRIM(CAST(zip_code AS VARCHAR)), 5, '0') AS zip, MIN(state) AS state
       FROM ssdb_integration.lr_strategy.zip_state_map GROUP BY ALL),
nm AS (SELECT DISTINCT source, w_key, w_nm FROM h)
SELECT 2025 AS fiscal_yr, CASE x.source WHEN 'S1' THEN $s1_source WHEN 'S2' THEN $s2_source END AS source,
       x.old_nm AS old_terr_wholesaler, x.sales_wh AS sales_wholesaler, x.new_nm AS terr_wholesaler_clean_name,
       COALESCE(nm.w_nm, x.sales_wh) AS sales_wholesaler_clean_name, x.firm_crd AS cbd_id, x.broker_name AS firm,
       CAST(NULL AS VARCHAR) AS parent, x.dist_ch, x.new_dist,
       CASE WHEN x.new_dist IN ('PRI', 'AFS') THEN 'pri_afs'
            WHEN x.new_dist IN ('Wells WH', 'National (Chase)', 'Wells FI') THEN 'National' ELSE x.new_dist END AS channel,
       zs.state, x.zip AS zip_code, x.product AS product_v2, x.mm_opp, x.sales AS actual_sales_amount,
       x.sales_comp AS sales_amount, x.sales_key AS sales_wholesaler_territory_id,
       CAST(NULL AS VARCHAR) AS sales_wholesaler_address_id, x.new_key AS territory_wholesaler_territory_id,
       CAST(NULL AS VARCHAR) AS territory_wholesaler_address_id, CAST(NULL AS INTEGER) AS sales_wholesaler_has_territory,
       CAST(NULL AS INTEGER) AS territory_wholesaler_has_territory, x.new_nm AS new_terr_wholesaler
FROM x LEFT JOIN zs ON zs.zip = x.zip LEFT JOIN nm ON nm.source = x.source AND nm.w_key = x.sales_key;

CREATE OR REPLACE TABLE ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys_v2
  LIKE ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys;
ALTER TABLE ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys_v2 RENAME COLUMN terr_wholesaler TO old_terr_wholesaler;
ALTER TABLE ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys_v2 ADD COLUMN new_terr_wholesaler VARCHAR;
INSERT INTO ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys_v2
  (fiscal_yr, source, old_terr_wholesaler, sales_wholesaler, terr_wholesaler_clean_name, sales_wholesaler_clean_name,
   cbd_id, firm, parent, dist_ch, new_dist, channel, state, zip_code, product_v2, mm_opp, actual_sales_amount,
   sales_amount, sales_wholesaler_territory_id, sales_wholesaler_address_id, territory_wholesaler_territory_id,
   territory_wholesaler_address_id, sales_wholesaler_has_territory, territory_wholesaler_has_territory,
   new_terr_wholesaler)
SELECT fiscal_yr, source, old_terr_wholesaler, sales_wholesaler, terr_wholesaler_clean_name, sales_wholesaler_clean_name,
       cbd_id, firm, parent, dist_ch, new_dist, channel, state, zip_code, product_v2, mm_opp, actual_sales_amount,
       sales_amount, sales_wholesaler_territory_id, sales_wholesaler_address_id, territory_wholesaler_territory_id,
       territory_wholesaler_address_id, sales_wholesaler_has_territory, territory_wholesaler_has_territory,
       new_terr_wholesaler
FROM ssdb_integration.lr_strategy.tmp_union;

--18. The TABLEAU parts, per SOURCE label: SIZES (rows; MM_OPP, AMT_ALT TMP_O1_DATASET's: above it by the opportunity
--repeated for 2+ holders; ACTUAL_SALES_AMOUNT and SALES_AMOUNT, AMT_ALT TMP_O2_SALES' SALES and SALES_ALT), VS LIVE (by CHANNEL, ITEM, x PRODUCT_V2, ITEM2:
--AMT the new table, AMT_ALT the live one), CHECKS.
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_tb_out AS
WITH
lb AS (SELECT 'S1' AS src, $s1_source AS source UNION ALL SELECT 'S2', $s2_source),
v AS (SELECT * FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys_v2),
l AS (SELECT * FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys),
vt AS (SELECT source, COUNT(*) AS n, SUM(mm_opp) AS opp, SUM(actual_sales_amount) AS sales, SUM(sales_amount) AS comp,
              COUNT(sales_amount) AS n_comp FROM v GROUP BY ALL),
ut AS (SELECT source, COUNT(*) AS n, SUM(mm_opp) AS opp FROM ssdb_integration.lr_strategy.tmp_union GROUP BY ALL),
o1 AS (SELECT lb.source, SUM(d.opportunity) AS amt
       FROM ssdb_integration.lr_strategy.tmp_o1_dataset d JOIN lb ON lb.src = d.source GROUP BY ALL),
o2 AS (SELECT lb.source, SUM(s.sales) AS amt, SUM(s.sales_alt) AS comp
       FROM ssdb_integration.lr_strategy.tmp_o2_sales s JOIN lb ON lb.src = s.source GROUP BY ALL),
ck AS (SELECT lb.source, d.zip, d.firm_crd, d.broker_name, d.product, d.old_channel_s1, d.new_channel,
              SUM(d.opportunity) AS opp
       FROM ssdb_integration.lr_strategy.tmp_o1_dataset d JOIN lb ON lb.src = d.source GROUP BY ALL),
uk AS (SELECT source, zip_code, cbd_id, firm, product_v2, dist_ch, new_dist, SUM(mm_opp) AS opp
       FROM ssdb_integration.lr_strategy.tmp_union GROUP BY ALL),
sf AS (SELECT ck.source, COUNT(*) AS n, SUM(ck.opp - COALESCE(uk.opp, 0)) AS amt
       FROM ck
       LEFT JOIN uk ON uk.source = ck.source AND EQUAL_NULL(uk.zip_code, ck.zip) AND EQUAL_NULL(uk.cbd_id, ck.firm_crd)
                   AND EQUAL_NULL(uk.firm, ck.broker_name) AND EQUAL_NULL(uk.product_v2, ck.product)
                   AND EQUAL_NULL(uk.dist_ch, ck.old_channel_s1) AND EQUAL_NULL(uk.new_dist, ck.new_channel)
       WHERE ABS(COALESCE(uk.opp, 0)) < ABS(ck.opp) - 0.005 GROUP BY ALL),
ls AS (SELECT DISTINCT source FROM l),
lc AS (SELECT COUNT(*) AS n FROM ssdb_integration.information_schema.columns
       WHERE UPPER(table_schema) = 'LR_STRATEGY' AND UPPER(table_name) = 'DATA_WITHNEWCHANNEL_UNION_W_JOINKEYS'
         AND UPPER(column_name) NOT IN ('FISCAL_YR', 'SOURCE', 'TERR_WHOLESALER', 'SALES_WHOLESALER',
             'TERR_WHOLESALER_CLEAN_NAME', 'SALES_WHOLESALER_CLEAN_NAME', 'CBD_ID', 'FIRM', 'PARENT', 'DIST_CH',
             'NEW_DIST', 'CHANNEL', 'STATE', 'ZIP_CODE', 'PRODUCT_V2', 'MM_OPP', 'ACTUAL_SALES_AMOUNT', 'SALES_AMOUNT',
             'SALES_WHOLESALER_TERRITORY_ID', 'SALES_WHOLESALER_ADDRESS_ID', 'TERRITORY_WHOLESALER_TERRITORY_ID',
             'TERRITORY_WHOLESALER_ADDRESS_ID', 'SALES_WHOLESALER_HAS_TERRITORY', 'TERRITORY_WHOLESALER_HAS_TERRITORY')),
vl AS (SELECT source, channel, product_v2, SUM(new_opp) AS new_opp, SUM(live_opp) AS live_opp,
              SUM(new_sales) AS new_sales, SUM(live_sales) AS live_sales, SUM(new_comp) AS new_comp,
              SUM(live_comp) AS live_comp
       FROM (SELECT source, channel, product_v2, CAST(mm_opp AS DECIMAL(38, 6)) AS new_opp,
                    CAST(0 AS DECIMAL(38, 6)) AS live_opp, CAST(actual_sales_amount AS DECIMAL(38, 6)) AS new_sales,
                    CAST(0 AS DECIMAL(38, 6)) AS live_sales, CAST(sales_amount AS DECIMAL(38, 6)) AS new_comp,
                    CAST(NULL AS DECIMAL(38, 6)) AS live_comp FROM v
             UNION ALL SELECT source, channel, product_v2, 0, CAST(mm_opp AS DECIMAL(38, 6)), 0,
                    CAST(actual_sales_amount AS DECIMAL(38, 6)), NULL, CAST(sales_amount AS DECIMAL(38, 6)) FROM l) y
       GROUP BY ALL)
            SELECT 'SIZES' AS part, lb.source, 'TABLE ROWS (N_ROWS)' AS name, CAST(NULL AS VARCHAR) AS item,
                   CAST(NULL AS VARCHAR) AS item2, COALESCE(vt.n, 0) AS n_rows, CAST(NULL AS DECIMAL(38, 6)) AS amt,
                   CAST(NULL AS DECIMAL(38, 6)) AS amt_alt
            FROM lb LEFT JOIN vt ON vt.source = lb.source
  UNION ALL SELECT 'SIZES', lb.source, 'MM_OPP (AMT_ALT: TMP_O1_DATASET; ABOVE IT BY THE OPPORTUNITY REPEATED FOR 2+ HOLDERS)',
                   NULL, NULL, NULL, vt.opp, o1.amt
            FROM lb LEFT JOIN vt ON vt.source = lb.source LEFT JOIN o1 ON o1.source = lb.source
  UNION ALL SELECT 'SIZES', lb.source, 'ACTUAL_SALES_AMOUNT (AMT_ALT: TMP_O2_SALES)', NULL, NULL, NULL, vt.sales, o2.amt
            FROM lb LEFT JOIN vt ON vt.source = lb.source LEFT JOIN o2 ON o2.source = lb.source
  UNION ALL SELECT 'SIZES', lb.source, 'SALES_AMOUNT, COMP''D (AMT_ALT: TMP_O2_SALES SALES_ALT; NULL FOR SOURCE 2)', NULL,
                   NULL, NULL, vt.comp, o2.comp
            FROM lb LEFT JOIN vt ON vt.source = lb.source LEFT JOIN o2 ON o2.source = lb.source
  UNION ALL SELECT 'VS LIVE', source, 'MM_OPP (AMT: THIS TABLE, AMT_ALT: THE LIVE ONE)', channel, product_v2, NULL,
                   new_opp, live_opp FROM vl
  UNION ALL SELECT 'VS LIVE', source, 'ACTUAL_SALES_AMOUNT (AMT: THIS TABLE, AMT_ALT: THE LIVE ONE)', channel,
                   product_v2, NULL, new_sales, live_sales FROM vl
  UNION ALL SELECT 'VS LIVE', source, 'SALES_AMOUNT (AMT: THIS TABLE, AMT_ALT: THE LIVE ONE)', channel, product_v2,
                   NULL, new_comp, live_comp FROM vl
  UNION ALL SELECT 'CHECKS', lb.source, 'ACTUAL_SALES_AMOUNT MINUS TMP_O2_SALES (MUST BE 0)', NULL, NULL, 0,
                   ROUND(COALESCE(vt.sales, 0) - COALESCE(o2.amt, 0), 2), NULL
            FROM lb LEFT JOIN vt ON vt.source = lb.source LEFT JOIN o2 ON o2.source = lb.source
  UNION ALL SELECT 'CHECKS', lb.source, 'SALES_AMOUNT MINUS TMP_O2_SALES COMP''D (MUST BE 0)', NULL, NULL, 0,
                   ROUND(COALESCE(vt.comp, 0) - COALESCE(o2.comp, 0), 2), NULL
            FROM lb LEFT JOIN vt ON vt.source = lb.source LEFT JOIN o2 ON o2.source = lb.source
  UNION ALL SELECT 'CHECKS', lb.source, 'SOURCE 2 ROWS WITH A SALES_AMOUNT (MUST BE 0)', NULL, NULL,
                   COALESCE(vt.n_comp, 0), 0, NULL
            FROM lb LEFT JOIN vt ON vt.source = lb.source WHERE lb.src = 'S2'
  UNION ALL SELECT 'CHECKS', lb.source, 'TABLE MINUS TMP_UNION, ROWS AND MM_OPP (MUST BE 0)', NULL, NULL,
                   COALESCE(vt.n, 0) - COALESCE(ut.n, 0), ROUND(COALESCE(vt.opp, 0) - COALESCE(ut.opp, 0), 2), NULL
            FROM lb LEFT JOIN vt ON vt.source = lb.source LEFT JOIN ut ON ut.source = lb.source
  UNION ALL SELECT 'CHECKS', lb.source, 'CELLS WITH LESS MM_OPP THAN TMP_O1_DATASET (MUST BE 0)', NULL, NULL,
                   COALESCE(sf.n, 0), ROUND(COALESCE(sf.amt, 0), 2), NULL
            FROM lb LEFT JOIN sf ON sf.source = lb.source
  UNION ALL SELECT 'CHECKS', lb.source, 'SOURCE LABEL NOT IN THE LIVE TABLE (MUST BE 0)', NULL, NULL,
                   CASE WHEN ls.source IS NULL THEN 1 ELSE 0 END, 0, NULL
            FROM lb LEFT JOIN ls ON ls.source = lb.source
  UNION ALL SELECT 'CHECKS', NULL, 'LIVE TABLE COLUMNS THIS SCRIPT DOES NOT FILL (MUST BE 0)', NULL, NULL, n, 0, NULL
            FROM lc;

--19. Everything, one result set: download as CSV.  LAYER says which statements a row comes from (OPPORTUNITY 1-7,
--SALES 8-14, REVIEW 15-16, TABLEAU 17-18); SALES_FIRM_ID to SCORE and N_KEYS, N_ZIPS are REVIEW's columns.  PCT_AMT: of LAYER x PART x
--SOURCE x NAME (REVIEW: as statement 16 says).
SELECT 'REVIEW' AS layer, part, source, name, item, CAST(NULL AS VARCHAR) AS item2, sales_firm_id, sales_firm,
       raw_channel, mga_agent_cd, firm_basis, match_channel, new_list_label, top_wholesaler, rank_key_by_amt,
       key_amt, n_candidates, rank_in_key, cand_firm_crd, cand_broker_name, cand_route, ev_company, ev_channel,
       ev_mm_map, ev_crd_to_cbd, ev_name, zip_amt, score, n_keys, CAST(NULL AS BIGINT) AS n_cells, n_rows,
       CAST(NULL AS BIGINT) AS n_firms, CAST(NULL AS BIGINT) AS n_holders, n_wholesalers, n_zips, amt, amt_alt,
       pct_amt
FROM ssdb_integration.lr_strategy.tmp_um_out
UNION ALL
SELECT 'OPPORTUNITY', part, source, name, item, item2, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL,
       NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, n_cells, NULL, n_firms, n_holders,
       NULL, NULL, amt, NULL, ROUND(100.0 * amt / NULLIF(SUM(amt) OVER (PARTITION BY part, source, name), 0), 2)
FROM ssdb_integration.lr_strategy.tmp_o1_out
UNION ALL
SELECT 'SALES', part, source, name, item, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL,
       NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, n_rows, n_firms, NULL, n_wholesalers,
       NULL, amt, NULL, ROUND(100.0 * amt / NULLIF(SUM(amt) OVER (PARTITION BY part, source, name), 0), 2)
FROM ssdb_integration.lr_strategy.tmp_o2_out
UNION ALL
SELECT 'TABLEAU', part, source, name, item, item2, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL,
       NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, n_rows, NULL, NULL, NULL, NULL, amt,
       amt_alt, NULL
FROM ssdb_integration.lr_strategy.tmp_tb_out
ORDER BY layer, part, source, rank_key_by_amt, sales_firm_id, sales_firm, raw_channel, mga_agent_cd, rank_in_key, name,
         amt DESC NULLS LAST, item, item2;
