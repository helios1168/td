--Layer 01: opportunity routed by firm, both sources (DATA_MODEL.md, Opportunity routed by firm; views 1, 2a, 2b, 3).
--Implements M_s, p, d, kappa_s, nu_D (re-keyed to CRD x broker name), nu, tau_s, H_s with k_s (the lowest ID).
--Builds temporary tables (owner, 2026-10-30: "create them as temporary tables for now"), queried in the same session:
--  TMP_O1_FIRM: one row per CRD x broker name either source carries: firm 1's route, how it was found, the new label
--    (the new-channel list re-keyed from company IDs), the holder channel in the new state (TAU).
--  TMP_O1_CELLS_S1, TMP_O1_CELLS_S2: one row per ZIP x CRD x broker name x product x current label, fiscal year 2025:
--    the opportunity, the current label, territory channel and holder, the new label, territory channel and holder.
--    Holders are IDs (wholesaler ID, territory ID), the lowest where 2+ hold (N_HOLDERS says how many).
--  TMP_O1_DATASET: every cell, both sources stacked, with the wholesalers' names: the table to look at opportunity by
--    source, firm, channel, product, wholesaler, ZIP (statement 6 shows a query).
--EDJ, AMER and AFS are channels like the others: EDJ and AMER come from firm 1's rules (old and new), AFS from the
--new-channel list (new only); a cut without them filters NEW_CHANNEL (owner, 2026-10-30: "should edj, amer, and afs
--just be considered like their own channels?").
--The last statement returns views 1, 2a, 2b, 3 summed by label and the checks: no ID or name.  Download it as CSV into
--$TD_REPO/data/safe/.  The decisions are the tables in 1 (DATASET_LOG.md, Settled and Key decisions): change a
--row and rerun.
--Snowflake docs read 2026-10-30: GROUP BY ALL (https://docs.snowflake.com/en/sql-reference/constructs/group-by), VALUES
--with column aliases (.../constructs/values), IS NOT DISTINCT FROM (.../functions/is-distinct-from), session variables
--and IDENTIFIER (.../session-variables, .../identifier-literal).
use secondary roles all;

--EDIT once: the tables whose names carry a carrier (paste the SET lines from owner_sql/vars.sql).  A name left as <...>
--fails loudly.
SET s1_territories = 'ssdb_integration.lr_strategy.<source 1 territories, ends _TERRITORIES>';
SET s2_opp         = 'ssdb_integration.lr_strategy.<source 2 opportunity, ends _OPP_ORIGINAL>';
SET s2_territories = 'ssdb_integration.lr_strategy.<source 2 territories, ends _TERRITORIES>';

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

--8. Everything, one result set: download as CSV.
SELECT part, source, name, item, item2, n_cells, n_firms, n_holders, amt,
       ROUND(100.0 * amt / NULLIF(SUM(amt) OVER (PARTITION BY part, source, name), 0), 2) AS pct_amt
FROM ssdb_integration.lr_strategy.tmp_o1_out
ORDER BY part, source, name, amt DESC NULLS LAST, item, item2;
