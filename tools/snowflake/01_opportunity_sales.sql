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
--    product in the old and the new state.
--  TMP_O2_DATASET: the table to look at.  One row per source x wholesaler x ZIP x firm x product x old channel x new
--    channel: the opportunity the wholesaler holds there, old and new (TMP_O1_DATASET), and the sales credited to
--    them there.  Sales never move between states; only held opportunity does.  Every 2025 sale and every
--    opportunity cell is in it, so it ties to the sales tables (owner, 2026-10-30: "which we must be able to exactly
--    replicate in this new table") and is the one master table (owner, 2026-10-30: "a single master table across all
--    cases which we then filter down afterwards").
--EDJ, AMER and AFS are channels like the others: EDJ and AMER come from firm 1's rules (old and new), AFS from the
--new-channel list (new only); a cut without them filters NEW_CHANNEL (owner, 2026-10-30: "should edj, amer, and afs
--just be considered like their own channels?").
--The last statement returns, under LAYER (OPPORTUNITY, SALES), views 1, 2a, 2b, 3 summed by label, the sales sizes,
--the tie-out and the checks: no ID or name.  Download it as CSV into $TD_REPO/data/safe/.  The decisions are the
--tables in 1 and 8 and the joins named in DATASET_LOG.md, Key decisions: change one and rerun.
--Snowflake docs read 2026-10-30: GROUP BY ALL (https://docs.snowflake.com/en/sql-reference/constructs/group-by), VALUES
--with column aliases (.../constructs/values), IS NOT DISTINCT FROM (.../functions/is-distinct-from), session variables
--and IDENTIFIER (.../session-variables, .../identifier-literal); SPLIT_PART gives '' past the last part
--(.../functions/split_part); CROSS JOIN takes no ON (.../constructs/join); a set operator wants each column's type the
--same in all its inputs, so both sources' sales amounts are cast to one exact type, DECIMAL(38, 6)
--(.../operators-query); a temporary table exists only in the session that made it
--(.../user-guide/tables-temp-transient).  TO_DATE, HAVING after GROUP BY and a comma join are s1_sales.sql's and
--s1_opp_sales.sql's, run at work.
use secondary roles all;

--EDIT once: the tables whose names carry a carrier (paste the SET lines from owner_sql/vars.sql).  A name left as <...>
--fails loudly.
SET s1_territories = 'ssdb_integration.lr_strategy.<source 1 territories, ends _TERRITORIES>';
SET s2_opp         = 'ssdb_integration.lr_strategy.<source 2 opportunity, ends _OPP_ORIGINAL>';
SET s2_territories = 'ssdb_integration.lr_strategy.<source 2 territories, ends _TERRITORIES>';
--s1_sales is the table owner_sql/s1_sales.sql makes with its first CREATE line and its last line uncommented.
SET s1_sales       = 'ssdb_integration.lr_strategy.<source 1 base sales from s1_sales.sql, ends _BASE_SALES>';
SET s2_sales       = 'ssdb_integration.lr_strategy.<source 2 sales, ends _SALES>';

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
--route with no channel, 2+ channels or no source 1 rows; else UNMAPPED.  NEW_LABEL: the new-channel list's label, else
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
r AS (SELECT k.firm_crd, k.broker_name,
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
      LEFT JOIN nu ON nu.firm_crd = k.firm_crd AND nu.broker_name = k.broker_name),
g AS (SELECT r.*,
             CASE WHEN s1_k = 1 THEN s1_ch WHEN ov_k = 1 THEN ov_ch ELSE 'UNMAPPED' END AS route,
             CASE WHEN s1_k = 1 THEN s1_level
                  ELSE CASE WHEN ov_k = 1 THEN 'OVERRIDE FILLS ' ELSE 'UNMAPPED: ' END
                       || CASE WHEN s1_k = 0 THEN 'NO CHANNEL' WHEN s1_k > 1 THEN '2+ CHANNELS'
                               ELSE 'NO SOURCE 1 ROWS' END END AS route_basis
      FROM r)
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
                   CASE WHEN source = 'S1' THEN CASE WHEN cur_label IS NOT DISTINCT FROM new_label THEN 'SAME'
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

--Source 1's sale channels in firm 1's channel names, used only to pick the firm where a company has 2+: IMO and the
--split-policy labels sell on their base channel (s1_sales.sql:18, :21, :418).  Any other label stands for itself.
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_s1_sale_channel AS
SELECT CAST(label AS VARCHAR) AS label, CAST(s1_channel AS VARCHAR) AS s1_channel
FROM (VALUES ('IMO', 'IFA'), ('IFA/IMO', 'IFA'), ('FI/IMO', 'FI')) AS v (label, s1_channel);

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

--11. Source 2's sales, YEAR 2025, with the firm each reaches: its CRD's one broker name (TMP_O1_FIRM holds every
--CRD x broker name either source's opportunity carries), or on a CRD with 2+, the one whose firm 1 channel is the
--sale's: CHANNEL through Q19 (or a territory code as is), then Q39 read back, which is also OLD_CHANNEL_S1.
--SALES_FIRM_ID, SALES_FIRM, RAW_PRODUCT and OLD_CHANNEL are FIRM_CRD, FIRM, PRODUCT and CHANNEL as they are; each
--amount (a FLOAT) is cast to DECIMAL(38, 6) before it is summed.  FIRM_BASIS as in 10, NO CRD for none.
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

--12. Both sources' sales with the firm's new channel, where the sale lands (CELL_STATUS: on a ZIP x firm x product of TMP_O1_DATASET or why not), and whether its seller holds that cell
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
       COALESCE(f.new_label, 'UNMAPPED') AS new_channel,
       CASE WHEN u.firm_crd IS NULL THEN 'NO FIRM' WHEN u.zip IS NULL THEN 'NO ZIP' WHEN p.product IS NULL THEN 'NO PRODUCT'
            WHEN ce.source IS NULL THEN 'NO OPPORTUNITY CELL' ELSE 'ON A CELL WITH OPPORTUNITY' END AS cell_status,
       ho.w IS NOT NULL AS held_old, hn.w IS NOT NULL AS held_new, u.n_rows, u.sales, u.sales_alt
FROM u
LEFT JOIN ssdb_integration.lr_strategy.tmp_sales_product p ON p.value = UPPER(TRIM(u.raw_product))
LEFT JOIN ssdb_integration.lr_strategy.tmp_o1_firm f ON f.firm_crd = u.firm_crd AND f.broker_name = u.broker_name
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
--  SALES FIRM BASIS, SALES PRODUCT (value -> product), SALES CHANNEL (the sale's channel -> the firm 1 channel that
--    picks its firm): all of a source's 2025 sales.  SALES ON CELLS: CELL, and SOLD BY THE
--    CELL'S HOLDER (old, new).  Q35: source 1's sales by how MM_MAP and CRD_TO_CBD map their company ID against the
--    firm found here.  SALES PERIOD: each sales table by year, firm 1's also by product bucket (s1_sales.sql keeps only
--    ALL, :439), before the 2025 filter.  WHOLESALERS: per source and state, wholesalers (N_WHOLESALERS) that
--    hold opportunity and sell, sell holding none, hold some with no sales; AMT their sales.
--  TIE-OUT: the owner's cut of firm 1's sales (PRODUCT_LINE2 <> 'FIXED' AND DIST_CH IN ('WH', 'FI', 'IFA')), actual and
--    comp'd: the sales table by fiscal year, and TMP_O2_DATASET's 2025 (PRODUCT, OLD_CHANNEL).
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
       FROM ssdb_integration.lr_strategy.tmp_o2_dataset WHERE wholesaler_key IS NOT NULL GROUP BY ALL),
tb AS (SELECT CAST(fiscal_yr AS VARCHAR) AS fy, COUNT(*) AS n, SUM(actual_agent_dollars) AS act,
              SUM(compd_agent_dollars) AS comp
       FROM IDENTIFIER($s1_sales)
       WHERE product_bucket = 'ALL' AND product_line2 <> 'FIXED' AND dist_ch IN ('WH', 'FI', 'IFA')
       GROUP BY ALL),
td AS (SELECT SUM(sales) AS act, SUM(sales_alt) AS comp FROM ssdb_integration.lr_strategy.tmp_o2_dataset
       WHERE source = 'S1' AND product <> 'FIXED' AND old_channel IN ('WH', 'FI', 'IFA')),
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
  UNION ALL SELECT 'SALES PRODUCT', source, NULL, COALESCE(raw_product, '(BLANK)') || ' -> ' || COALESCE(product, 'UNMAPPED'),
                   seller_key, firm_crd, broker_name, n_rows, sales FROM s
  UNION ALL SELECT 'SALES CHANNEL', source, NULL,
                   COALESCE(old_channel, '(BLANK)') || ' -> ' || COALESCE(match_channel, '(NONE)'),
                   seller_key, firm_crd, broker_name, n_rows, sales FROM s
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

--15. Everything, one result set: download as CSV.  LAYER says which half a row comes from; PCT_AMT: of LAYER x PART x
--SOURCE x NAME.
SELECT 'OPPORTUNITY' AS layer, part, source, name, item, item2, n_cells, CAST(NULL AS BIGINT) AS n_rows, n_firms,
       n_holders, CAST(NULL AS BIGINT) AS n_wholesalers, amt,
       ROUND(100.0 * amt / NULLIF(SUM(amt) OVER (PARTITION BY part, source, name), 0), 2) AS pct_amt
FROM ssdb_integration.lr_strategy.tmp_o1_out
UNION ALL
SELECT 'SALES', part, source, name, item, CAST(NULL AS VARCHAR), CAST(NULL AS BIGINT), n_rows, n_firms,
       CAST(NULL AS BIGINT), n_wholesalers, amt,
       ROUND(100.0 * amt / NULLIF(SUM(amt) OVER (PARTITION BY part, source, name), 0), 2)
FROM ssdb_integration.lr_strategy.tmp_o2_out
ORDER BY layer, part, source, name, amt DESC NULLS LAST, item, item2;
