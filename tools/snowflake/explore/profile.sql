--Opportunity profile: what routing each source's opportunity by firm needs to know (DATA_MODEL.md, Opportunity routed
--by firm).  Per source: how full the firm key is (CRD, broker name), whether a firm has one channel, the product and
--channel labels, which ZIP x channel has 0, 1 or 2+ holders; across sources: whether source 2's firms have a source 1
--channel.  Counts, $ and the labels of channel and product columns only; no ID or name value leaves the temporary
--tables.  The sales half of this profile is in git history (73774ed).
--Reads crd_dist_override (2026-10-25).
--Run All; download the last statement's result as CSV into $TD_REPO/data/safe/.
--Source 1: fiscal year 2025, the vendor's own DIST_CH (the query's rules, s1_opp_sales.sql:459-470, not applied).
--Source 2's opportunity table has no year column and is read whole.
--Snowflake docs read 2026-10-30: GROUP BY ALL groups by every SELECT item without an aggregate, and a GROUP BY name
--resolves to a table column before a SELECT alias (https://docs.snowflake.com/en/sql-reference/constructs/group-by),
--so every grouping here is GROUP BY ALL; TRANSLATE drops source characters with no target character
--(https://docs.snowflake.com/en/sql-reference/functions/translate); VALUES takes column aliases
--(https://docs.snowflake.com/en/sql-reference/constructs/values).
use secondary roles all;

--EDIT once: the tables whose names carry a carrier, as session variables (SET, then IDENTIFIER($name); docs read
--2026-10-30: https://docs.snowflake.com/en/sql-reference/session-variables, .../identifier-literal: a fully
--qualified name is allowed, a variable lasts for the session).  A name left as <...> fails loudly.
SET s1_territories = 'ssdb_integration.lr_strategy.<source 1 territories, ends _TERRITORIES>';
SET s2_opp         = 'ssdb_integration.lr_strategy.<source 2 opportunity, ends _OPP_ORIGINAL>';
SET s2_territories = 'ssdb_integration.lr_strategy.<source 2 territories, ends _TERRITORIES>';

--1. Each source's opportunity, cleaned once and grouped: ZIP padded to 5, IDs as whole-number text, names and
--channels trimmed and upper-cased.  2 and 7 read these.
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_opp_s1 AS
SELECT LPAD(LEFT(TRIM(zip_code), 5), 5, '0') AS zip, cbd_id, client_firm_id, NULLIF(TRIM(firm_crd), '') AS firm_crd,
       UPPER(TRIM(broker_name)) AS broker_name, UPPER(TRIM(dist_ch)) AS dist_ch, channel, product_line,
       va_product_type, COUNT(*) AS n, SUM(global_sales) AS amt
FROM life_prod.lif_murkylake.wc_market_metrics_opportunity WHERE fiscal_yr = '2025'
GROUP BY ALL;

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
  SELECT cbd_id, client_firm_id, firm_crd, broker_name, firm_crd || '|' || broker_name AS crd_name, dist_ch, channel,
         product_line, va_product_type, SUM(n) AS n, SUM(amt) AS amt
  FROM s1 GROUP BY ALL)),
s1_opp_geo AS (SELECT *, ROW_NUMBER() OVER (ORDER BY n DESC) AS rid FROM (
  SELECT zip, dist_ch || '|' || zip AS ch_zip, SUM(n) AS n, SUM(amt) AS amt FROM s1 GROUP BY ALL)),
s1_crd_ch AS (SELECT *, ROW_NUMBER() OVER (ORDER BY n DESC) AS rid FROM (   -- one row per CRD x channel
  SELECT DISTINCT firm_crd, dist_ch, 1 AS n, CAST(NULL AS DECIMAL(38, 2)) AS amt FROM s1)),
s1_terr AS (SELECT *, ROW_NUMBER() OVER (ORDER BY n DESC) AS rid FROM (
  SELECT whslr_id, LPAD(LEFT(TRIM(zip), 5), 5, '0') AS zip,
         new_dist_channel || '|' || LPAD(LEFT(TRIM(zip), 5), 5, '0') AS ch_zip, new_dist_channel,
         COUNT(*) AS n, CAST(NULL AS DECIMAL(38, 2)) AS amt
  FROM IDENTIFIER($s1_territories) GROUP BY ALL)),
s2_opp_firm AS (SELECT *, ROW_NUMBER() OVER (ORDER BY n DESC) AS rid FROM (
  SELECT firm_crd, broker_name, firm_crd || '|' || broker_name AS crd_name, dist_ch, channel, product_line,
         va_product_type, SUM(n) AS n, SUM(amt) AS amt
  FROM s2 GROUP BY ALL)),
s2_opp_geo AS (SELECT *, ROW_NUMBER() OVER (ORDER BY n DESC) AS rid FROM (
  SELECT zip, dist_ch || '|' || zip AS ch_zip, SUM(n) AS n, SUM(amt) AS amt FROM s2 GROUP BY ALL)),
s2_override AS (SELECT *, ROW_NUMBER() OVER (ORDER BY n DESC) AS rid FROM (
  SELECT TRIM(firm_crd) AS firm_crd, COUNT(*) AS n, CAST(NULL AS DECIMAL(38, 2)) AS amt
  FROM ssdb_integration.lr_strategy.crd_dist_override GROUP BY ALL)),
s2_terr AS (SELECT *, ROW_NUMBER() OVER (ORDER BY n DESC) AS rid FROM (
  SELECT territory_id, rvp, LPAD(LEFT(TRIM(zipcode), 5), 5, '0') AS zip,
         channel || '|' || LPAD(LEFT(TRIM(zipcode), 5), 5, '0') AS ch_zip, channel, channel_name,
         COUNT(*) AS n, CAST(NULL AS DECIMAL(38, 2)) AS amt
  FROM IDENTIFIER($s2_territories) GROUP BY ALL)),
lng AS (
            SELECT 'S1_OPP_FIRM' AS ds, rid, 'K' AS kind, 'CBD_ID' AS col, cbd_id AS v, n, amt FROM s1_opp_firm
  UNION ALL SELECT 'S1_OPP_FIRM', rid, 'K', 'CLIENT_FIRM_ID', client_firm_id, n, amt FROM s1_opp_firm
  UNION ALL SELECT 'S1_OPP_FIRM', rid, 'K', 'FIRM_CRD', firm_crd, n, amt FROM s1_opp_firm
  UNION ALL SELECT 'S1_OPP_FIRM', rid, 'K', 'BROKER_NAME', broker_name, n, amt FROM s1_opp_firm
  UNION ALL SELECT 'S1_OPP_FIRM', rid, 'K', 'CRD_NAME', crd_name, n, amt FROM s1_opp_firm
  UNION ALL SELECT 'S1_OPP_FIRM', rid, 'KD', 'DIST_CH', dist_ch, n, amt FROM s1_opp_firm
  UNION ALL SELECT 'S1_OPP_FIRM', rid, 'D', 'CHANNEL', channel, n, amt FROM s1_opp_firm
  UNION ALL SELECT 'S1_OPP_FIRM', rid, 'D', 'PRODUCT_LINE', product_line, n, amt FROM s1_opp_firm
  UNION ALL SELECT 'S1_OPP_FIRM', rid, 'D', 'VA_PRODUCT_TYPE', va_product_type, n, amt FROM s1_opp_firm
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
  UNION ALL SELECT 'S2_OPP_FIRM', rid, 'D', 'PRODUCT_LINE', product_line, n, amt FROM s2_opp_firm
  UNION ALL SELECT 'S2_OPP_FIRM', rid, 'D', 'VA_PRODUCT_TYPE', va_product_type, n, amt FROM s2_opp_firm
  UNION ALL SELECT 'S2_OPP_GEO', rid, 'K', 'ZIP', zip, n, amt FROM s2_opp_geo
  UNION ALL SELECT 'S2_OPP_GEO', rid, 'K', 'CH_ZIP', ch_zip, n, amt FROM s2_opp_geo
  UNION ALL SELECT 'S2_OVERRIDE', rid, 'K', 'FIRM_CRD', firm_crd, n, amt FROM s2_override
  UNION ALL SELECT 'S2_TERR', rid, 'K', 'TERRITORY_ID', territory_id, n, amt FROM s2_terr
  UNION ALL SELECT 'S2_TERR', rid, 'K', 'RVP', rvp, n, amt FROM s2_terr
  UNION ALL SELECT 'S2_TERR', rid, 'K', 'ZIP', zip, n, amt FROM s2_terr
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
--   E.g. S1_OPP_FIRM FIRM_CRD - DIST_CH 'one FIRM_CRD, many DIST_CH': the $ of firms with 2+ channels.
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

--7. Checks, each by outcome.  COL: the check.  S2 DIST_CH -> S1 CHANNEL OF THE CRD: source 2's opportunity by its own
--label and the one channel source 1 gives its CRD ('2+ CHANNELS', 'NO SOURCE 1 ROWS'), '(OVERRIDE)' where
--crd_dist_override lists the CRD.  S1 CHANNELS PER ZIP X CRD X NAME: whether source 1's split of a firm into channels
--shows within a ZIP (ZIP CELL 2+) or only across ZIPs.  S2 ROUTE LEVEL: how far the market metrics columns carry
--source 2's opportunity to one source 1 channel, finest first (the same ZIP x CRD x broker name, then the CRD x broker
--name, then the CRD), the vendor's DIST_CH before the query's rules.  ZIP_FORM before padding; regions: does source 1's territory table
--match the regions it is read from (s1_opp_sales.sql:677-694 reads only START_ZIP); periods.
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
                   CASE WHEN end_zip IS NULL THEN 'end missing' WHEN start_zip = end_zip THEN 'same' ELSE 'range' END,
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
