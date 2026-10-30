--Opportunity profile: what routing each source's opportunity by firm needs to know (DATA_MODEL.md, Opportunity routed
--by firm).  Per source: how full the firm key is (CRD, broker name), whether a firm has one channel, the product and
--channel labels, which ZIP x channel has 0, 1 or 2+ holders; across sources: whether source 2's firms have a source 1
--channel.  Counts, $ and the labels of channel and product columns only; no ID or name value leaves the temporary
--tables.  The sales half of this profile is in git history (73774ed).
--Reads crd_dist_override (2026-10-25).
--Run All; download the last statement's result as CSV into $TD_REPO/data/safe/.
--Source 1: fiscal year 2025; DIST_CH is firm 1's channel after its rules, FEED_DIST_CH the vendor's.  A route with no
--firm 1 channel is UNMAPPED (owner, 2026-10-30).
--Source 2's opportunity table has no year column and is read whole.
--Snowflake docs read 2026-10-30: GROUP BY ALL groups by every SELECT item without an aggregate, and a GROUP BY name
--resolves to a table column before a SELECT alias (https://docs.snowflake.com/en/sql-reference/constructs/group-by),
--so every grouping here is GROUP BY ALL; TRANSLATE drops source characters with no target character
--(https://docs.snowflake.com/en/sql-reference/functions/translate); VALUES takes column aliases
--(https://docs.snowflake.com/en/sql-reference/constructs/values); IS NOT DISTINCT FROM is NULL-safe equality
--(https://docs.snowflake.com/en/sql-reference/functions/is-distinct-from).
use secondary roles all;

--EDIT once: the tables whose names carry a carrier, as session variables (SET, then IDENTIFIER($name); docs read
--2026-10-30: https://docs.snowflake.com/en/sql-reference/session-variables, .../identifier-literal: a fully
--qualified name is allowed, a variable lasts for the session).  A name left as <...> fails loudly.
SET s1_territories = 'ssdb_integration.lr_strategy.<source 1 territories, ends _TERRITORIES>';
SET s2_opp         = 'ssdb_integration.lr_strategy.<source 2 opportunity, ends _OPP_ORIGINAL>';
SET s2_territories = 'ssdb_integration.lr_strategy.<source 2 territories, ends _TERRITORIES>';

--1. Firm 1's channel rules, then each source's opportunity, cleaned once and grouped: ZIP padded to 5, IDs as
--whole-number text, names and channels trimmed and upper-cased.  The rules are s1_opp_sales.sql:459-470 (sha256
--6262e2f93bbd..., generated from those lines), one row per value: a row matches on the one column it fills (company
--ID, broker name, the vendor's DIST_CH) and the lowest RULE_ORDER that matches wins, as the query's CASE does.
--Source 1's rows take the winning rule's channel, else the vendor's DIST_CH.  2 and 7 read these.
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

--KEY DECISIONS (DATASET_LOG.md, Key decisions): change a row and rerun; statement 7's S2 HOLDER MOVES shows the effect.
--Q19: source 2's own label -> its territory channel (current-state holders); TERR_CHANNEL NULL: none.  KEEP_NEW: the
--rows go on into the new state, routed by firm 1's channel (NO CHANNEL kept, owner 2026-10-30; FALSE drops them).
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_s2_label_terr AS
SELECT CAST(label AS VARCHAR) AS label, CAST(terr_channel AS VARCHAR) AS terr_channel, CAST(keep_new AS BOOLEAN) AS keep_new
FROM (VALUES
  ('BANK', 'BK', TRUE),
  ('INDEPENDENT', 'FP', TRUE),
  ('REGIONAL', 'BD', TRUE),
  ('REGIONAL AGENCY', 'RA', TRUE),
  ('NO CHANNEL', NULL, TRUE)
) AS v (label, terr_channel, keep_new);

--Q39: firm 1's channel (the route) -> the source 2 territory channel that holds it in the new state.
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_s1ch_s2terr AS
SELECT CAST(s1_channel AS VARCHAR) AS s1_channel, CAST(terr_channel AS VARCHAR) AS terr_channel
FROM (VALUES
  ('IFA', 'FP'),
  ('FI', 'BK'),
  ('WH', 'BD'),
  ('PRI', 'RA')
) AS v (s1_channel, terr_channel);

--Scope: out of the exercise for now (owner, 2026-10-30): a firm (CRD x broker name) whose firm 1 channel is a CHANNEL
--row, or whose source 1 rows carry a COMPANY row's ID (AFS is company 438, s1_opp_sales.sql:706), is left out, both
--sources, both states; statement 7 reports it apart (SCOPE) and S2 HOLDER MOVES tags it.  Delete a row to bring it back.
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_scope_out AS
SELECT CAST(kind AS VARCHAR) AS kind, CAST(value AS VARCHAR) AS value, CAST(label AS VARCHAR) AS label
FROM (VALUES ('CHANNEL', 'EDJ', 'EDJ'), ('CHANNEL', 'AMER', 'AMER'), ('COMPANY', '438', 'AFS')) AS v (kind, value, label);

CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_opp_s1 AS
WITH
o AS (SELECT *, ROW_NUMBER() OVER (ORDER BY n DESC) AS oid FROM (
  SELECT LPAD(LEFT(TRIM(zip_code), 5), 5, '0') AS zip, NULLIF(TRIM(cbd_id), '') AS cbd_id, client_firm_id,
         NULLIF(TRIM(firm_crd), '') AS firm_crd, UPPER(TRIM(broker_name)) AS broker_name,
         NULLIF(UPPER(TRIM(dist_ch)), '') AS feed_dist_ch, channel, product_line, va_product_type,
         COUNT(*) AS n, SUM(global_sales) AS amt
  FROM life_prod.lif_murkylake.wc_market_metrics_opportunity WHERE fiscal_yr = '2025' GROUP BY ALL)),
r AS (SELECT o.oid, ru.channel AS rule_channel, ROW_NUMBER() OVER (PARTITION BY o.oid ORDER BY ru.rule_order) AS rk
      FROM o JOIN ssdb_integration.lr_strategy.tmp_s1_channel_rule ru
        ON ru.cbd_id = o.cbd_id OR ru.broker_name = o.broker_name OR ru.dist_ch = o.feed_dist_ch)
SELECT o.zip, o.cbd_id, o.client_firm_id, o.firm_crd, o.broker_name, o.feed_dist_ch,
       COALESCE(r.rule_channel, o.feed_dist_ch) AS dist_ch, o.channel, o.product_line, o.va_product_type, o.n, o.amt
FROM o LEFT JOIN r ON r.oid = o.oid AND r.rk = 1;

CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_opp_s2 AS
SELECT LPAD(CAST(CAST(zip_code AS DECIMAL(38, 0)) AS VARCHAR), 5, '0') AS zip,
       CAST(CAST(firm_crd AS DECIMAL(38, 0)) AS VARCHAR) AS firm_crd, UPPER(TRIM(broker_name)) AS broker_name,
       UPPER(TRIM(dist_ch)) AS dist_ch, CAST(channel AS VARCHAR) AS channel, product_line, va_product_type,
       COUNT(*) AS n, SUM(opp) AS amt
FROM IDENTIFIER($s2_opp)
GROUP BY ALL;

--2. Each dataset as its distinct key combinations, with rows (N) and $ (AMT), in long form: one row per combination x
--column.  KIND K: a key (4 pairs it with the dataset's other keys, 5 matches it across datasets); D: a label (6 lists
--its values); KD: both.  Values: text, trimmed, upper-cased; blank and '0' are missing.
--CRD_NAME is CRD | broker name; CH_ZIP is channel | 5-digit ZIP.
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_prof AS
WITH
s1 AS (SELECT * FROM ssdb_integration.lr_strategy.tmp_opp_s1),
s2 AS (SELECT * FROM ssdb_integration.lr_strategy.tmp_opp_s2),
s1_opp_firm AS (SELECT *, ROW_NUMBER() OVER (ORDER BY n DESC) AS rid FROM (
  SELECT cbd_id, client_firm_id, firm_crd, broker_name, firm_crd || '|' || broker_name AS crd_name, dist_ch,
         feed_dist_ch, channel, product_line, va_product_type, SUM(n) AS n, SUM(amt) AS amt
  FROM s1 GROUP BY ALL)),
s1_opp_geo AS (SELECT *, ROW_NUMBER() OVER (ORDER BY n DESC) AS rid FROM (
  SELECT zip, dist_ch || '|' || zip AS ch_zip, SUM(n) AS n, SUM(amt) AS amt FROM s1 GROUP BY ALL)),
s1_crd_ch AS (SELECT *, ROW_NUMBER() OVER (ORDER BY n DESC) AS rid FROM (   -- one row per CRD x channel
  SELECT DISTINCT firm_crd, dist_ch, 1 AS n, CAST(NULL AS DECIMAL(38, 2)) AS amt FROM s1)),
s1_terr AS (SELECT *, ROW_NUMBER() OVER (ORDER BY n DESC) AS rid FROM (
  SELECT whslr_id, LPAD(LEFT(TRIM(zip), 5), 5, '0') AS zip,
         new_dist_channel || '|' || LPAD(LEFT(TRIM(zip), 5), 5, '0') AS ch_zip, new_dist_channel,
         1 AS n, CAST(NULL AS DECIMAL(38, 2)) AS amt   -- distinct rows: a match counts holders, not repeats
  FROM IDENTIFIER($s1_territories) GROUP BY ALL)),
s2_opp_firm AS (SELECT *, ROW_NUMBER() OVER (ORDER BY n DESC) AS rid FROM (
  SELECT firm_crd, broker_name, firm_crd || '|' || broker_name AS crd_name, dist_ch, channel, product_line,
         va_product_type, SUM(n) AS n, SUM(amt) AS amt
  FROM s2 GROUP BY ALL)),
s2_opp_geo AS (SELECT *, ROW_NUMBER() OVER (ORDER BY n DESC) AS rid FROM (   -- channel: the Q19 territory channel
  SELECT s2.zip, lm.terr_channel || '|' || s2.zip AS ch_zip, SUM(s2.n) AS n, SUM(s2.amt) AS amt
  FROM s2 LEFT JOIN ssdb_integration.lr_strategy.tmp_s2_label_terr lm ON lm.label = s2.dist_ch GROUP BY ALL)),
s2_override AS (SELECT *, ROW_NUMBER() OVER (ORDER BY n DESC) AS rid FROM (
  SELECT TRIM(firm_crd) AS firm_crd, COUNT(*) AS n, CAST(NULL AS DECIMAL(38, 2)) AS amt
  FROM ssdb_integration.lr_strategy.crd_dist_override GROUP BY ALL)),
s2_terr AS (SELECT *, ROW_NUMBER() OVER (ORDER BY n DESC) AS rid FROM (
  SELECT territory_id, rvp, LPAD(LEFT(TRIM(zipcode), 5), 5, '0') AS zip,
         channel || '|' || LPAD(LEFT(TRIM(zipcode), 5), 5, '0') AS ch_zip, channel, channel_name,
         1 AS n, CAST(NULL AS DECIMAL(38, 2)) AS amt   -- distinct rows: a match counts holders, not repeats
  FROM IDENTIFIER($s2_territories) GROUP BY ALL)),
lng AS (
            SELECT 'S1_OPP_FIRM' AS ds, rid, 'K' AS kind, 'CBD_ID' AS col, cbd_id AS v, n, amt FROM s1_opp_firm
  UNION ALL SELECT 'S1_OPP_FIRM', rid, 'K', 'CLIENT_FIRM_ID', client_firm_id, n, amt FROM s1_opp_firm
  UNION ALL SELECT 'S1_OPP_FIRM', rid, 'K', 'FIRM_CRD', firm_crd, n, amt FROM s1_opp_firm
  UNION ALL SELECT 'S1_OPP_FIRM', rid, 'K', 'BROKER_NAME', broker_name, n, amt FROM s1_opp_firm
  UNION ALL SELECT 'S1_OPP_FIRM', rid, 'K', 'CRD_NAME', crd_name, n, amt FROM s1_opp_firm
  UNION ALL SELECT 'S1_OPP_FIRM', rid, 'KD', 'DIST_CH', dist_ch, n, amt FROM s1_opp_firm
  UNION ALL SELECT 'S1_OPP_FIRM', rid, 'KD', 'FEED_DIST_CH', feed_dist_ch, n, amt FROM s1_opp_firm
  UNION ALL SELECT 'S1_OPP_FIRM', rid, 'KD', 'CHANNEL', channel, n, amt FROM s1_opp_firm
  UNION ALL SELECT 'S1_OPP_FIRM', rid, 'KD', 'PRODUCT_LINE', product_line, n, amt FROM s1_opp_firm
  UNION ALL SELECT 'S1_OPP_FIRM', rid, 'KD', 'VA_PRODUCT_TYPE', va_product_type, n, amt FROM s1_opp_firm
  UNION ALL SELECT 'S1_OPP_GEO', rid, 'K', 'ZIP', zip, n, amt FROM s1_opp_geo
  UNION ALL SELECT 'S1_OPP_GEO', rid, 'K', 'CH_ZIP', ch_zip, n, amt FROM s1_opp_geo
  UNION ALL SELECT 'S1_CRD_CH', rid, 'K', 'FIRM_CRD', firm_crd, n, amt FROM s1_crd_ch
  UNION ALL SELECT 'S1_TERR', rid, 'K', 'WHSLR_ID', whslr_id, n, amt FROM s1_terr
  UNION ALL SELECT 'S1_TERR', rid, 'K', 'ZIP', zip, n, amt FROM s1_terr
  UNION ALL SELECT 'S1_TERR', rid, 'K', 'CH_ZIP', ch_zip, n, amt FROM s1_terr
  UNION ALL SELECT 'S1_TERR', rid, 'D', 'NEW_DIST_CHANNEL', new_dist_channel, n, amt FROM s1_terr
  UNION ALL SELECT 'S2_OPP_FIRM', rid, 'K', 'FIRM_CRD', firm_crd, n, amt FROM s2_opp_firm
  UNION ALL SELECT 'S2_OPP_FIRM', rid, 'K', 'BROKER_NAME', broker_name, n, amt FROM s2_opp_firm
  UNION ALL SELECT 'S2_OPP_FIRM', rid, 'K', 'CRD_NAME', crd_name, n, amt FROM s2_opp_firm
  UNION ALL SELECT 'S2_OPP_FIRM', rid, 'KD', 'DIST_CH', dist_ch, n, amt FROM s2_opp_firm
  UNION ALL SELECT 'S2_OPP_FIRM', rid, 'D', 'CHANNEL', channel, n, amt FROM s2_opp_firm
  UNION ALL SELECT 'S2_OPP_FIRM', rid, 'KD', 'PRODUCT_LINE', product_line, n, amt FROM s2_opp_firm
  UNION ALL SELECT 'S2_OPP_FIRM', rid, 'KD', 'VA_PRODUCT_TYPE', va_product_type, n, amt FROM s2_opp_firm
  UNION ALL SELECT 'S2_OPP_GEO', rid, 'K', 'ZIP', zip, n, amt FROM s2_opp_geo
  UNION ALL SELECT 'S2_OPP_GEO', rid, 'K', 'CH_ZIP', ch_zip, n, amt FROM s2_opp_geo
  UNION ALL SELECT 'S2_OVERRIDE', rid, 'K', 'FIRM_CRD', firm_crd, n, amt FROM s2_override
  UNION ALL SELECT 'S2_TERR', rid, 'K', 'TERRITORY_ID', territory_id, n, amt FROM s2_terr
  UNION ALL SELECT 'S2_TERR', rid, 'K', 'RVP', rvp, n, amt FROM s2_terr
  UNION ALL SELECT 'S2_TERR', rid, 'K', 'ZIP', zip, n, amt FROM s2_terr
  UNION ALL SELECT 'S2_TERR', rid, 'K', 'CH_ZIP', ch_zip, n, amt FROM s2_terr
  UNION ALL SELECT 'S2_TERR', rid, 'KD', 'CHANNEL', channel, n, amt FROM s2_terr
  UNION ALL SELECT 'S2_TERR', rid, 'KD', 'CHANNEL_NAME', channel_name, n, amt FROM s2_terr)
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
--   E.g. S1_OPP_FIRM FIRM_CRD - DIST_CH 'one FIRM_CRD, many DIST_CH': the $ of firms with 2+ channels; CHANNEL -
--   FEED_DIST_CH: whether the vendor's code and its channel label are one thing; PRODUCT_LINE - VA_PRODUCT_TYPE and
--   S2_TERR CHANNEL - CHANNEL_NAME: how those codes pair.
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_prof_pairs AS
WITH
l AS (
  SELECT a.ds, a.col AS a, a.val AS a_val, b.col AS b, b.val AS b_val, SUM(a.n) AS n, SUM(a.amt) AS amt
  FROM ssdb_integration.lr_strategy.tmp_prof a
  JOIN ssdb_integration.lr_strategy.tmp_prof b ON b.ds = a.ds AND b.rid = a.rid AND a.col < b.col
  WHERE a.kind IN ('K', 'KD') AND b.kind IN ('K', 'KD') AND a.val IS NOT NULL AND b.val IS NOT NULL
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
--   COL2: the right key.  CH_ZIP -> territories: 0 = no holder, 2+ = several holders.  S2 FIRM_CRD -> S1_CRD_CH: 0 = no
--   source 1 channel for the firm, 1 = one, 2+ = several (crd_dist_override's case).
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_prof_matches AS
WITH
m AS (SELECT * FROM (VALUES
  ('S1_OPP_GEO', 'CH_ZIP', 'S1_TERR', 'CH_ZIP'),
  ('S1_OPP_GEO', 'ZIP', 'S1_TERR', 'ZIP'),
  ('S2_OPP_GEO', 'CH_ZIP', 'S2_TERR', 'CH_ZIP'),
  ('S2_OPP_GEO', 'ZIP', 'S2_TERR', 'ZIP'),
  ('S2_OPP_FIRM', 'FIRM_CRD', 'S1_CRD_CH', 'FIRM_CRD'),
  ('S2_OPP_FIRM', 'FIRM_CRD', 'S2_OVERRIDE', 'FIRM_CRD'),
  ('S2_OPP_FIRM', 'CRD_NAME', 'S1_OPP_FIRM', 'CRD_NAME'),
  ('S1_OPP_FIRM', 'FIRM_CRD', 'S2_OPP_FIRM', 'FIRM_CRD')) AS v (lds, lcol, rds, rcol)),
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

--6. The labels: each value of every D and KD column with rows and $, the 40 largest per column.
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
            FROM ssdb_integration.lr_strategy.tmp_prof WHERE kind IN ('D', 'KD') GROUP BY ALL) x) y
WHERE rk <= 40;

--7. Checks, each by outcome.  COL: the check.
--  S2 DIST_CH -> S1 CHANNEL OF THE CRD: source 2's opportunity by its own label and the one channel source 1 gives its
--    CRD ('2+ CHANNELS', 'NO SOURCE 1 ROWS'), '(OVERRIDE)' where crd_dist_override lists the CRD.
--  S1 CHANNELS PER ZIP X CRD X NAME: whether firm 1's split of a firm into channels shows within a ZIP or only across.
--  S2 ROUTE LEVEL: the finest market metrics key at which firm 1's rows give source 2's opportunity one channel (the
--    same ZIP x CRD x broker name, the CRD x broker name, the CRD); in these three a blank channel counts as one.
--  ROUTE (CRD X NAME): the firm-level route, the one non-blank firm 1 channel of the CRD x broker name (of the CRD for a
--    name source 1 lacks), UNMAPPED if none; for source 1 rows also whether the row's own channel is blank.
--  S2 ROUTE (CRD X NAME) VS OVERRIDE: that route against crd_dist_override (its CRD x broker name row, else its CRD row).
--  OVERRIDE TABLE KEYS: the override's keys: CRD only or CRD x name, repeated, 2+ channels, matching no source 2 row.
--  S1 SCOPE, S2 SCOPE: each source's opportunity in scope or out by tmp_scope_out (a firm's firm 1 channel or company).
--  S2 HOLDER MOVES: source 2's opportunity from its current holder (its label, Q19, the territory at the ZIP) to its
--    new-state holder (the route, Q39, the territory at the ZIP; the lowest TERRITORY_ID where 2+): same territory,
--    other territory, no holder, dropped, out of scope; ... BY LABEL AND ROUTE: label | route | current -> new territory channel.
--  ZIP_FORM before padding; regions: does source 1's territory table match the regions it is read from
--    (s1_opp_sales.sql:677-694 reads only the first 5 digits of START_ZIP); periods.
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_prof_checks AS
WITH
rgn AS (SELECT rgn_cd, start_zip, end_zip, cbd FROM life_prod.lif_murkylake.geographic_region
        WHERE expir_dt = '9999-12-31'),
rgn_wz AS (SELECT DISTINCT rw.whslr_id, LEFT(r.start_zip, 5) AS zip
           FROM life_prod.lif_murkylake.rgn_whslr rw JOIN rgn r ON r.rgn_cd = rw.rgn_cd
           WHERE rw.expir_dt = '9999-12-31' AND r.cbd IN (0, 3)),
terr_wz AS (SELECT DISTINCT whslr_id, LEFT(TRIM(zip), 5) AS zip FROM IDENTIFIER($s1_territories)),
zips AS (
            SELECT 'S1_OPP' AS ds, TRIM(zip_code) AS z, global_sales AS amt
            FROM life_prod.lif_murkylake.wc_market_metrics_opportunity WHERE fiscal_yr = '2025'
  UNION ALL SELECT 'S2_OPP', CAST(CAST(zip_code AS DECIMAL(38, 0)) AS VARCHAR), opp FROM IDENTIFIER($s2_opp)
  UNION ALL SELECT 'S1_TERR', TRIM(zip), NULL FROM IDENTIFIER($s1_territories)
  UNION ALL SELECT 'S2_TERR', TRIM(zipcode), NULL FROM IDENTIFIER($s2_territories)
  UNION ALL SELECT 'S1_REGION_START', TRIM(start_zip), NULL FROM rgn),
s1_crd AS (SELECT firm_crd, CASE WHEN COUNT(DISTINCT COALESCE(dist_ch, '(BLANK)')) = 1
                                THEN MIN(COALESCE(dist_ch, '(BLANK)')) ELSE '2+ CHANNELS' END AS s1_channel
           FROM ssdb_integration.lr_strategy.tmp_opp_s1 WHERE firm_crd IS NOT NULL GROUP BY ALL),
ovr AS (SELECT DISTINCT TRIM(firm_crd) AS firm_crd FROM ssdb_integration.lr_strategy.crd_dist_override),
ovk AS (SELECT TRIM(firm_crd) AS firm_crd, NULLIF(UPPER(TRIM(broker_name)), '') AS broker_name, COUNT(*) AS n_rows,
               COUNT(DISTINCT NULLIF(UPPER(TRIM(dist_ch)), '')) AS k, MIN(NULLIF(UPPER(TRIM(dist_ch)), '')) AS ch
        FROM ssdb_integration.lr_strategy.crd_dist_override GROUP BY ALL),
s1_nr AS (SELECT firm_crd, broker_name, COUNT(DISTINCT dist_ch) AS k, MIN(dist_ch) AS ch
          FROM ssdb_integration.lr_strategy.tmp_opp_s1 WHERE firm_crd IS NOT NULL GROUP BY ALL),
s1_cr AS (SELECT firm_crd, COUNT(DISTINCT dist_ch) AS k, MIN(dist_ch) AS ch
          FROM ssdb_integration.lr_strategy.tmp_opp_s1 WHERE firm_crd IS NOT NULL GROUP BY ALL),
s2_route AS (
  SELECT o.n, o.amt, o.zip, o.dist_ch AS label, o.firm_crd, o.broker_name,
         CASE WHEN o.firm_crd IS NULL THEN 'NO CRD'
              WHEN nr.firm_crd IS NOT NULL THEN CASE WHEN nr.k = 0 THEN 'UNMAPPED' WHEN nr.k = 1 THEN nr.ch ELSE '2+' END
              WHEN cr.firm_crd IS NOT NULL THEN CASE WHEN cr.k = 0 THEN 'UNMAPPED' WHEN cr.k = 1 THEN cr.ch ELSE '2+' END
              ELSE 'NO SOURCE 1 ROWS' END AS route,
         COALESCE(v1.k, v0.k) AS ovr_k, COALESCE(v1.ch, v0.ch) AS ovr
  FROM ssdb_integration.lr_strategy.tmp_opp_s2 o
  LEFT JOIN s1_nr nr ON nr.firm_crd = o.firm_crd AND nr.broker_name = o.broker_name
  LEFT JOIN s1_cr cr ON cr.firm_crd = o.firm_crd
  LEFT JOIN ovk v1 ON v1.firm_crd = o.firm_crd AND v1.broker_name = o.broker_name
  LEFT JOIN ovk v0 ON v0.firm_crd = o.firm_crd AND v0.broker_name IS NULL),
out_firm AS (   -- the firms out of scope, with the scope row's label
  SELECT firm_crd, broker_name, MIN(label) AS label FROM (
              SELECT nr.firm_crd, nr.broker_name, so.label
              FROM s1_nr nr JOIN ssdb_integration.lr_strategy.tmp_scope_out so
                ON so.kind = 'CHANNEL' AND so.value = CASE WHEN nr.k = 1 THEN nr.ch END
    UNION ALL SELECT o.firm_crd, o.broker_name, so.label
              FROM ssdb_integration.lr_strategy.tmp_opp_s1 o JOIN ssdb_integration.lr_strategy.tmp_scope_out so
                ON so.kind = 'COMPANY' AND so.value = o.cbd_id
              WHERE o.firm_crd IS NOT NULL) x
  GROUP BY ALL),
s2_terr_k AS (SELECT channel, LPAD(LEFT(TRIM(zipcode), 5), 5, '0') AS zip, MIN(territory_id) AS territory_id
              FROM IDENTIFIER($s2_territories) GROUP BY ALL),   -- the lowest ID where 2+ hold (Settled)
s2_moves AS (
  SELECT r.n, r.amt, r.label, r.route, lm.label AS mapped_label, lm.terr_channel AS cur_ch,
         COALESCE(lm.keep_new, TRUE) AS keep_new, nm.terr_channel AS new_ch,
         tc.territory_id AS cur_t, tn.territory_id AS new_t, ofm.label AS out_ch
  FROM s2_route r
  LEFT JOIN out_firm ofm ON ofm.firm_crd = r.firm_crd AND ofm.broker_name = r.broker_name
  LEFT JOIN ssdb_integration.lr_strategy.tmp_s2_label_terr lm ON lm.label = r.label
  LEFT JOIN ssdb_integration.lr_strategy.tmp_s1ch_s2terr nm ON nm.s1_channel = r.route
  LEFT JOIN s2_terr_k tc ON tc.channel = lm.terr_channel AND tc.zip = r.zip
  LEFT JOIN s2_terr_k tn ON tn.channel = nm.terr_channel AND tn.zip = r.zip),
ovk_in_s2 AS (SELECT DISTINCT v.firm_crd, v.broker_name
              FROM ovk v JOIN ssdb_integration.lr_strategy.tmp_opp_s2 o
                ON o.firm_crd = v.firm_crd AND (v.broker_name IS NULL OR o.broker_name = v.broker_name)),
s1_cell AS (SELECT zip, firm_crd, broker_name, COUNT(DISTINCT COALESCE(dist_ch, '(BLANK)')) AS k
            FROM ssdb_integration.lr_strategy.tmp_opp_s1 WHERE firm_crd IS NOT NULL GROUP BY ALL),
s1_name AS (SELECT firm_crd, broker_name, COUNT(DISTINCT COALESCE(dist_ch, '(BLANK)')) AS k
            FROM ssdb_integration.lr_strategy.tmp_opp_s1 WHERE firm_crd IS NOT NULL GROUP BY ALL),
c AS (
            SELECT 'S1_OPP' AS ds, 'S1 CHANNELS PER ZIP X CRD X NAME, PER CRD X NAME' AS chk,
                   CASE WHEN o.firm_crd IS NULL THEN 'NO CRD' WHEN ce.k > 1 THEN 'ZIP CELL 2+'
                        WHEN nm.k > 1 THEN 'ZIP CELL 1, FIRM 2+' ELSE 'ZIP CELL 1, FIRM 1' END AS outcome,
                   SUM(o.n) AS n, SUM(o.amt) AS amt
            FROM ssdb_integration.lr_strategy.tmp_opp_s1 o
            LEFT JOIN s1_cell ce ON ce.zip = o.zip AND ce.firm_crd = o.firm_crd AND ce.broker_name = o.broker_name
            LEFT JOIN s1_name nm ON nm.firm_crd = o.firm_crd AND nm.broker_name = o.broker_name
            GROUP BY ALL
  UNION ALL SELECT 'S1_OPP', 'S1 ROUTE (CRD X NAME)',
                   CASE WHEN o.firm_crd IS NULL THEN 'NO CRD' WHEN nr.k = 0 THEN 'UNMAPPED' WHEN nr.k > 1 THEN '2+'
                        WHEN o.dist_ch IS NULL THEN 'ONE CHANNEL, ROW BLANK' ELSE 'ONE CHANNEL' END,
                   SUM(o.n), SUM(o.amt)
            FROM ssdb_integration.lr_strategy.tmp_opp_s1 o
            LEFT JOIN s1_nr nr ON nr.firm_crd = o.firm_crd AND nr.broker_name = o.broker_name
            GROUP BY ALL
  UNION ALL SELECT 'S2_OPP', 'S2 ROUTE (CRD X NAME)', route, SUM(n), SUM(amt) FROM s2_route GROUP BY ALL
  UNION ALL SELECT 'S2_OPP', 'S2 ROUTE (CRD X NAME) VS OVERRIDE',
                   CASE WHEN ovr_k IS NULL THEN 'NO OVERRIDE | ROUTE '
                                                || CASE WHEN route IN ('UNMAPPED', '2+', 'NO SOURCE 1 ROWS', 'NO CRD')
                                                        THEN route ELSE 'ONE CHANNEL' END
                        WHEN ovr_k = 0 THEN 'OVERRIDE BLANK'
                        WHEN ovr_k > 1 THEN 'OVERRIDE HAS 2+ CHANNELS'
                        WHEN route IN ('UNMAPPED', '2+', 'NO SOURCE 1 ROWS') THEN 'OVERRIDE FILLS ' || route || ': ' || ovr
                        WHEN route = ovr THEN 'OVERRIDE = ROUTE'
                        ELSE 'OVERRIDE ' || ovr || ' <> ROUTE ' || route END,
                   SUM(n), SUM(amt)
            FROM s2_route GROUP BY ALL
  UNION ALL SELECT 'S2_OPP', 'S2 HOLDER MOVES',
                   CASE WHEN out_ch IS NOT NULL THEN 'OUT OF SCOPE (' || out_ch || ')'
                        WHEN NOT keep_new THEN 'DROPPED' WHEN new_ch IS NULL THEN 'NO NEW CHANNEL (' || route || ')'
                        WHEN new_t IS NULL THEN 'NO NEW HOLDER' WHEN cur_t IS NULL THEN 'NO CURRENT HOLDER, NEW HOLDER'
                        WHEN cur_t = new_t THEN 'SAME TERRITORY' ELSE 'OTHER TERRITORY' END,
                   SUM(n), SUM(amt)
            FROM s2_moves GROUP BY ALL
  UNION ALL SELECT 'S1_OPP', 'S1 SCOPE',
                   CASE WHEN ofm.label IS NOT NULL THEN 'OUT: ' || ofm.label ELSE 'IN' END, SUM(o.n), SUM(o.amt)
            FROM ssdb_integration.lr_strategy.tmp_opp_s1 o
            LEFT JOIN out_firm ofm ON ofm.firm_crd = o.firm_crd AND ofm.broker_name = o.broker_name
            GROUP BY ALL
  UNION ALL SELECT 'S2_OPP', 'S2 SCOPE', CASE WHEN out_ch IS NOT NULL THEN 'OUT: ' || out_ch ELSE 'IN' END, SUM(n), SUM(amt)
            FROM s2_moves GROUP BY ALL
  UNION ALL SELECT 'S2_OPP', 'S2 HOLDER MOVES BY LABEL AND ROUTE',
                   COALESCE(label, '(BLANK)') || ' | ' || route || ' | '
                   || CASE WHEN mapped_label IS NULL THEN 'NOT IN Q19 MAP' ELSE COALESCE(cur_ch, 'NONE') END
                   || ' -> ' || CASE WHEN NOT keep_new THEN 'DROPPED' ELSE COALESCE(new_ch, 'NONE') END,
                   SUM(n), SUM(amt)
            FROM s2_moves GROUP BY ALL
  UNION ALL SELECT 'S2_OVERRIDE', 'OVERRIDE TABLE KEYS',
                   CASE WHEN v.broker_name IS NULL THEN 'CRD ONLY' ELSE 'CRD X NAME' END
                   || CASE WHEN v.n_rows > 1 THEN ', REPEATED' ELSE '' END
                   || CASE WHEN v.k > 1 THEN ', 2+ CHANNELS' ELSE '' END
                   || CASE WHEN i.firm_crd IS NULL THEN ', NOT IN S2' ELSE '' END,
                   COUNT(*), NULL
            FROM ovk v LEFT JOIN ovk_in_s2 i ON i.firm_crd = v.firm_crd AND i.broker_name IS NOT DISTINCT FROM v.broker_name
            GROUP BY ALL
  UNION ALL SELECT 'S2_OPP', 'S2 ROUTE LEVEL',
                   CASE WHEN o.firm_crd IS NULL THEN '0 NO CRD'
                        WHEN ce.k = 1 THEN '1 SAME ZIP X CRD X NAME: ONE CHANNEL'
                        WHEN ce.k > 1 THEN '2 SAME ZIP X CRD X NAME: 2+ CHANNELS'
                        WHEN nm.k = 1 THEN '3 SAME CRD X NAME: ONE CHANNEL'
                        WHEN nm.k > 1 THEN '4 SAME CRD X NAME: 2+ CHANNELS'
                        WHEN c1.s1_channel = '2+ CHANNELS' THEN '6 SAME CRD, OTHER NAME: 2+ CHANNELS'
                        WHEN c1.firm_crd IS NOT NULL THEN '5 SAME CRD, OTHER NAME: ONE CHANNEL'
                        ELSE '7 NO SOURCE 1 ROWS' END
                   || CASE WHEN v.firm_crd IS NOT NULL THEN ' (OVERRIDE)' ELSE '' END,
                   SUM(o.n), SUM(o.amt)
            FROM ssdb_integration.lr_strategy.tmp_opp_s2 o
            LEFT JOIN s1_cell ce ON ce.zip = o.zip AND ce.firm_crd = o.firm_crd AND ce.broker_name = o.broker_name
            LEFT JOIN s1_name nm ON nm.firm_crd = o.firm_crd AND nm.broker_name = o.broker_name
            LEFT JOIN s1_crd c1 ON c1.firm_crd = o.firm_crd
            LEFT JOIN ovr v ON v.firm_crd = o.firm_crd
            GROUP BY ALL
  UNION ALL
            SELECT 'S2_OPP', 'S2 DIST_CH -> S1 CHANNEL OF THE CRD',
                   COALESCE(o.dist_ch, '(BLANK)') || ' -> '
                   || CASE WHEN o.firm_crd IS NULL THEN 'NO CRD' ELSE COALESCE(c1.s1_channel, 'NO SOURCE 1 ROWS') END
                   || CASE WHEN v.firm_crd IS NOT NULL THEN ' (OVERRIDE)' ELSE '' END,
                   SUM(o.n), SUM(o.amt)
            FROM ssdb_integration.lr_strategy.tmp_opp_s2 o
            LEFT JOIN s1_crd c1 ON c1.firm_crd = o.firm_crd
            LEFT JOIN ovr v ON v.firm_crd = o.firm_crd
            GROUP BY ALL
  UNION ALL SELECT ds, 'ZIP_FORM',
                   CASE WHEN z IS NULL OR z = '' THEN 'missing' WHEN TRANSLATE(z, '0123456789', '') <> '' THEN 'non-digit'
                        WHEN LENGTH(z) = 5 THEN '5 digits' WHEN LENGTH(z) < 5 THEN 'under 5 digits'
                        ELSE 'over 5 digits' END,
                   COUNT(*), SUM(amt)
            FROM zips GROUP BY ALL
  UNION ALL SELECT 'S1_REGION', 'START_ZIP_VS_END_ZIP',
                   CASE WHEN end_zip IS NULL THEN 'end missing' WHEN start_zip = end_zip THEN 'same'
                        WHEN LEFT(start_zip, 5) = LEFT(end_zip, 5) THEN 'range within one ZIP'
                        ELSE 'range across ZIPs' END,
                   COUNT(*), NULL
            FROM rgn GROUP BY ALL
  UNION ALL SELECT 'S1_TERR', 'WHSLR_ZIP_VS_REGIONS',
                   CASE WHEN t.whslr_id IS NULL THEN 'regions only' WHEN r.whslr_id IS NULL THEN 'table only' ELSE 'both' END,
                   COUNT(*), NULL
            FROM terr_wz t FULL OUTER JOIN rgn_wz r ON r.whslr_id = t.whslr_id AND r.zip = t.zip GROUP BY ALL
  UNION ALL SELECT 'S1_OPP', 'FISCAL_YR | QUARTER', fiscal_yr || ' | ' || quarter, COUNT(*), SUM(global_sales)
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
