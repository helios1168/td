--Override review: the firms where crd_dist_override and firm 1's route disagree (Q38, DATASET_LOG.md 2026-10-30,
--the second profile run: override FI where the route is WH, 2.48% of source 2's $).  One row per CRD x broker name of
--every CRD with a disagreement, all its names, so a disputed name sits beside its siblings.  Firm names and
--opportunity $ appear (no sales $, no person's names); read it at work or keep the CSV in $TD_REPO/data/safe/.
--Columns: STATUS (OVERRIDE <> ROUTE first), the override's channel and firm 1's route (ROUTE_FROM: the CRD x broker
--name, or the CRD for a name firm 1 lacks), firm 1's channel mix for the name in $ shares, its vendor DIST_CH, vendor
--codes, company IDs and the rules that fired (RULE_ORDER of tmp_s1_channel_rule), its fiscal year 2025 opportunity,
--then source 2's own labels, opportunity and share of its total, and how many override rows the key has.
--Run All after the SET line; one result set.  Same cleaning and rules as profile.sql (sha256 6262e2f93bbd... of
--s1_opp_sales.sql:459-470); the DuckDB test checks the rule rows are the profile's.
use secondary roles all;

--EDIT once: the carrier-named table, as a session variable (DATASET_LOG.md, Conventions, Table variables).
SET s2_opp = 'ssdb_integration.lr_strategy.<source 2 opportunity, ends _OPP_ORIGINAL>';

--1. Firm 1's channel rules (the profile's), firm 1's opportunity per firm with its channel, source 2's per firm.
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

CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_rv_s1 AS
WITH
o AS (SELECT *, ROW_NUMBER() OVER (ORDER BY amt DESC) AS oid FROM (
  SELECT NULLIF(TRIM(firm_crd), '') AS firm_crd, UPPER(TRIM(broker_name)) AS broker_name, NULLIF(TRIM(cbd_id), '') AS cbd_id,
         TRIM(channel) AS vendor_code, NULLIF(UPPER(TRIM(dist_ch)), '') AS feed_dist_ch, SUM(global_sales) AS amt
  FROM life_prod.lif_murkylake.wc_market_metrics_opportunity WHERE fiscal_yr = '2025' GROUP BY ALL)),
r AS (SELECT o.oid, ru.rule_order, ru.channel AS rule_channel,
             ROW_NUMBER() OVER (PARTITION BY o.oid ORDER BY ru.rule_order) AS rk
      FROM o JOIN ssdb_integration.lr_strategy.tmp_s1_channel_rule ru
        ON ru.cbd_id = o.cbd_id OR ru.broker_name = o.broker_name OR ru.dist_ch = o.feed_dist_ch)
SELECT o.firm_crd, o.broker_name, o.cbd_id, o.vendor_code, o.feed_dist_ch, CAST(r.rule_order AS VARCHAR) AS rule_order,
       COALESCE(r.rule_channel, o.feed_dist_ch) AS dist_ch, o.amt
FROM o LEFT JOIN r ON r.oid = o.oid AND r.rk = 1;

CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_rv_s2 AS
SELECT CAST(CAST(firm_crd AS DECIMAL(38, 0)) AS VARCHAR) AS firm_crd, UPPER(TRIM(broker_name)) AS broker_name,
       UPPER(TRIM(dist_ch)) AS dist_ch, SUM(opp) AS amt
FROM IDENTIFIER($s2_opp) GROUP BY ALL;

--2. The review: every name of every CRD with a disagreement.
WITH
ovk AS (SELECT TRIM(firm_crd) AS firm_crd, NULLIF(UPPER(TRIM(broker_name)), '') AS broker_name, COUNT(*) AS n_rows,
               COUNT(DISTINCT NULLIF(UPPER(TRIM(dist_ch)), '')) AS k, MIN(NULLIF(UPPER(TRIM(dist_ch)), '')) AS ch
        FROM ssdb_integration.lr_strategy.crd_dist_override GROUP BY ALL),
nr AS (SELECT firm_crd, broker_name, COUNT(DISTINCT dist_ch) AS k, MIN(dist_ch) AS ch, SUM(amt) AS s1_opp,
              LISTAGG(DISTINCT feed_dist_ch, ' | ') WITHIN GROUP (ORDER BY feed_dist_ch) AS s1_feed_dist_ch,
              LISTAGG(DISTINCT vendor_code, ' | ') WITHIN GROUP (ORDER BY vendor_code) AS s1_vendor_codes,
              LISTAGG(DISTINCT cbd_id, ' | ') WITHIN GROUP (ORDER BY cbd_id) AS s1_company_ids,
              LISTAGG(DISTINCT rule_order, ' | ') WITHIN GROUP (ORDER BY rule_order) AS s1_rules
       FROM ssdb_integration.lr_strategy.tmp_rv_s1 WHERE firm_crd IS NOT NULL GROUP BY ALL),
cr AS (SELECT firm_crd, COUNT(DISTINCT dist_ch) AS k, MIN(dist_ch) AS ch
       FROM ssdb_integration.lr_strategy.tmp_rv_s1 WHERE firm_crd IS NOT NULL GROUP BY ALL),
nc AS (SELECT firm_crd, broker_name, COALESCE(dist_ch, '(BLANK)') AS ch, SUM(amt) AS amt
       FROM ssdb_integration.lr_strategy.tmp_rv_s1 WHERE firm_crd IS NOT NULL GROUP BY ALL),
nmix AS (SELECT firm_crd, broker_name, LISTAGG(mix_item, ', ') WITHIN GROUP (ORDER BY amt DESC) AS s1_channel_mix
         FROM (SELECT firm_crd, broker_name, amt,
                      ch || ' ' || CAST(ROUND(100.0 * amt / NULLIF(SUM(amt) OVER (PARTITION BY firm_crd, broker_name), 0), 1) AS VARCHAR) || '%' AS mix_item
               FROM nc) x
         GROUP BY ALL),
s2n AS (SELECT firm_crd, broker_name, LISTAGG(DISTINCT dist_ch, ' | ') WITHIN GROUP (ORDER BY dist_ch) AS s2_own_dist_ch,
               SUM(amt) AS s2_opp
        FROM ssdb_integration.lr_strategy.tmp_rv_s2 GROUP BY ALL),
s2tot AS (SELECT SUM(amt) AS tot FROM ssdb_integration.lr_strategy.tmp_rv_s2),
names AS (SELECT firm_crd, broker_name FROM s2n WHERE firm_crd IS NOT NULL
          UNION SELECT firm_crd, broker_name FROM nr),
st AS (
  SELECT n.firm_crd, n.broker_name,
         CASE WHEN nr.firm_crd IS NOT NULL THEN CASE WHEN nr.k = 0 THEN 'UNMAPPED' WHEN nr.k = 1 THEN nr.ch ELSE '2+' END
              WHEN cr.firm_crd IS NOT NULL THEN CASE WHEN cr.k = 0 THEN 'UNMAPPED' WHEN cr.k = 1 THEN cr.ch ELSE '2+' END
              ELSE 'NO SOURCE 1 ROWS' END AS route_dist_ch,
         CASE WHEN nr.firm_crd IS NOT NULL THEN 'CRD X NAME' WHEN cr.firm_crd IS NOT NULL THEN 'CRD' END AS route_from,
         COALESCE(v1.ch, v0.ch) AS override_dist_ch, COALESCE(v1.k, v0.k) AS override_k,
         COALESCE(v1.n_rows, v0.n_rows) AS override_rows,
         m.s1_channel_mix, nr.s1_feed_dist_ch, nr.s1_vendor_codes, nr.s1_company_ids, nr.s1_rules, nr.s1_opp,
         s2n.s2_own_dist_ch, s2n.s2_opp
  FROM names n
  LEFT JOIN nr ON nr.firm_crd = n.firm_crd AND nr.broker_name = n.broker_name
  LEFT JOIN cr ON cr.firm_crd = n.firm_crd
  LEFT JOIN nmix m ON m.firm_crd = n.firm_crd AND m.broker_name = n.broker_name
  LEFT JOIN s2n ON s2n.firm_crd = n.firm_crd AND s2n.broker_name = n.broker_name
  LEFT JOIN ovk v1 ON v1.firm_crd = n.firm_crd AND v1.broker_name = n.broker_name
  LEFT JOIN ovk v0 ON v0.firm_crd = n.firm_crd AND v0.broker_name IS NULL),
st2 AS (
  SELECT st.*,
         CASE WHEN override_k IS NULL THEN 'NO OVERRIDE' WHEN override_k <> 1 THEN 'OVERRIDE BLANK OR 2+'
              WHEN route_dist_ch IN ('UNMAPPED', '2+', 'NO SOURCE 1 ROWS') THEN 'OVERRIDE FILLS'
              WHEN route_dist_ch = override_dist_ch THEN 'OVERRIDE = ROUTE' ELSE 'OVERRIDE <> ROUTE' END AS status
  FROM st),
crds AS (SELECT firm_crd, MAX(CASE WHEN status = 'OVERRIDE <> ROUTE' THEN 1 ELSE 0 END) AS has_case,
                SUM(COALESCE(s2_opp, 0)) AS crd_s2_opp
         FROM st2 GROUP BY ALL)
SELECT st2.firm_crd, st2.broker_name, st2.status, st2.override_dist_ch, st2.route_dist_ch, st2.route_from,
       st2.s1_channel_mix, st2.s1_feed_dist_ch, st2.s1_vendor_codes, st2.s1_company_ids, st2.s1_rules,
       ROUND(st2.s1_opp, 0) AS s1_opp, st2.s2_own_dist_ch, ROUND(st2.s2_opp, 0) AS s2_opp,
       ROUND(100.0 * st2.s2_opp / s2tot.tot, 3) AS pct_s2_opp, st2.override_rows
FROM st2 JOIN crds c ON c.firm_crd = st2.firm_crd CROSS JOIN s2tot
WHERE c.has_case = 1
ORDER BY c.crd_s2_opp DESC, st2.firm_crd, CASE WHEN st2.status = 'OVERRIDE <> ROUTE' THEN 0 ELSE 1 END, st2.s2_opp DESC NULLS LAST;
