--AMER's holder (Q41): does company 805 have territories of its own, and who covers it today?  AMER is company 805's
--channel (s1_opp_sales.sql:460); the territory step keeps only channel-level regions and company 3's own (:692), so
--any other company's own regions never reach the territory table, and AMER finds no holder (:719).
--One result set, counts, percentages and labels only (no amounts, no names):
--  COMPANY REGIONS: every company with current regions (CBD; 0 = channel-level): regions, 5-digit ZIPs, wholesalers,
--    the regions' DISTCH_CHANNEL labels and teams.
--  COMPANY OPPORTUNITY COVERAGE: the company's fiscal year 2025 opportunity (firm 1's market metrics) by what covers
--    its ZIPs: one of its own regions, a channel-level region per label (not exclusive), or neither; % of its $.
--  WHO SELLS TO THE COMPANY: its fiscal year 2025 sales (actual amount, s1_sales.sql's row filters but the product
--    list) by the seller's channel (WHSLR.DISTCH) and team, and whether the seller holds one of its regions; % of its
--    sales $ and sellers.
--Snowflake docs read 2026-10-30: session variables (https://docs.snowflake.com/en/sql-reference/session-variables);
--GROUP BY ALL (https://docs.snowflake.com/en/sql-reference/constructs/group-by).  LISTAGG(DISTINCT ...) WITHIN GROUP
--ran at work (archived explore/firm_master_relationships.sql, 2026-10-29).
use secondary roles all;

SET company_id = '805';   -- the company whose channel has no territory (AMER); change it to look at another

--1. Current regions with their wholesalers and teams.
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_aq_rg AS
SELECT CAST(CAST(gr.cbd AS DECIMAL(38, 0)) AS VARCHAR) AS cbd, gr.rgn_cd, LPAD(LEFT(TRIM(gr.start_zip), 5), 5, '0') AS zip,
       UPPER(TRIM(gr.distch_channel)) AS region_label, UPPER(TRIM(st.sales_team_name)) AS team, rw.whslr_id
FROM life_prod.lif_murkylake.geographic_region gr
JOIN life_prod.lif_murkylake.rgn_whslr rw ON rw.rgn_cd = gr.rgn_cd AND rw.expir_dt = '9999-12-31'
LEFT JOIN life_prod.lif_murkylake.wc_sales_team st ON st.sales_team_id = gr.sales_team_id
WHERE gr.expir_dt = '9999-12-31';

--2. Every company with regions.
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_aq_regions AS
SELECT 'COMPANY REGIONS' AS part, CASE WHEN cbd = '0' THEN '0 (CHANNEL-LEVEL)' ELSE cbd END AS item,
       LISTAGG(DISTINCT region_label, ' | ') WITHIN GROUP (ORDER BY region_label) AS labels,
       LISTAGG(DISTINCT team, ' | ') WITHIN GROUP (ORDER BY team) AS teams,
       COUNT(DISTINCT rgn_cd) AS n_regions, COUNT(DISTINCT zip) AS n_zips, COUNT(DISTINCT whslr_id) AS n_whslr,
       CAST(NULL AS DOUBLE) AS pct
FROM ssdb_integration.lr_strategy.tmp_aq_rg
GROUP BY ALL;

--3. What covers the company's opportunity ZIPs.
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_aq_cov AS
WITH
opp AS (SELECT LPAD(LEFT(TRIM(zip_code), 5), 5, '0') AS zip, SUM(global_sales) AS amt
        FROM life_prod.lif_murkylake.wc_market_metrics_opportunity
        WHERE fiscal_yr = '2025' AND TRIM(cbd_id) = $company_id GROUP BY ALL),
tot AS (SELECT SUM(amt) AS t FROM opp),
cov AS (SELECT DISTINCT zip, CASE WHEN cbd = $company_id THEN 'OWN REGION'
                                  ELSE 'CHANNEL-LEVEL ' || COALESCE(region_label, '(BLANK)') END AS kind
        FROM ssdb_integration.lr_strategy.tmp_aq_rg WHERE cbd IN ($company_id, '0')),
c AS (
            SELECT c.kind AS item, COUNT(*) AS n_zips, SUM(o.amt) AS amt
            FROM opp o JOIN cov c ON c.zip = o.zip GROUP BY ALL
  UNION ALL SELECT 'NO OWN OR CHANNEL-LEVEL REGION', COUNT(*), SUM(o.amt)
            FROM opp o WHERE NOT EXISTS (SELECT 1 FROM cov c WHERE c.zip = o.zip)
  UNION ALL SELECT 'TOTAL', COUNT(*), SUM(amt) FROM opp)
SELECT 'COMPANY OPPORTUNITY COVERAGE' AS part, c.item, CAST(NULL AS VARCHAR) AS labels, CAST(NULL AS VARCHAR) AS teams,
       CAST(NULL AS BIGINT) AS n_regions, c.n_zips, CAST(NULL AS BIGINT) AS n_whslr,
       ROUND(100.0 * c.amt / NULLIF(tot.t, 0), 2) AS pct
FROM c CROSS JOIN tot;

--4. Who sells to the company (seller per WHSLR row: the lowest channel and team where a wholesaler has 2+ rows).
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_aq_sellers AS
WITH
sl AS (SELECT whslr_id, SUM(actual_sales_amount) AS amt
       FROM life_prod.lif_murkylake.sls_rpt_detail
       WHERE fiscal_yr = 2025 AND consol_brkr_dlr_id = $company_id AND bonus_rate <> 0 AND init_pay_in = 'Y'
         AND agent_tax_id IS NOT NULL
       GROUP BY ALL),
tot AS (SELECT SUM(amt) AS t FROM sl),
ws AS (SELECT w.whslr_id, MIN(UPPER(TRIM(w.distch))) AS ch, MIN(UPPER(TRIM(st.sales_team_name))) AS team
       FROM life_prod.lif_murkylake.whslr w
       LEFT JOIN life_prod.lif_murkylake.wc_sales_district sd ON sd.sales_district_id = w.sales_district_id
       LEFT JOIN life_prod.lif_murkylake.wc_sales_team st ON st.sales_team_id = sd.sales_team_id
       GROUP BY ALL),
own AS (SELECT DISTINCT whslr_id FROM ssdb_integration.lr_strategy.tmp_aq_rg WHERE cbd = $company_id),
x AS (SELECT sl.whslr_id, sl.amt, COALESCE(ws.ch, '(NONE)') AS ch, COALESCE(ws.team, '(NONE)') AS team,
             CASE WHEN own.whslr_id IS NULL THEN 'NO' ELSE 'YES' END AS holds_own
      FROM sl LEFT JOIN ws ON ws.whslr_id = sl.whslr_id LEFT JOIN own ON own.whslr_id = sl.whslr_id),
c AS (
            SELECT 'SELLER CHANNEL ' || ch AS item, COUNT(*) AS n_whslr, SUM(amt) AS amt FROM x GROUP BY ALL
  UNION ALL SELECT 'SELLER TEAM ' || team, COUNT(*), SUM(amt) FROM x GROUP BY ALL
  UNION ALL SELECT 'SELLER HOLDS AN OWN REGION: ' || holds_own, COUNT(*), SUM(amt) FROM x GROUP BY ALL)
SELECT 'WHO SELLS TO THE COMPANY' AS part, c.item, CAST(NULL AS VARCHAR) AS labels, CAST(NULL AS VARCHAR) AS teams,
       CAST(NULL AS BIGINT) AS n_regions, CAST(NULL AS BIGINT) AS n_zips, c.n_whslr,
       ROUND(100.0 * c.amt / NULLIF(tot.t, 0), 2) AS pct
FROM c CROSS JOIN tot;

--5. Everything, one result set: download as CSV.
SELECT * FROM ssdb_integration.lr_strategy.tmp_aq_regions
UNION ALL SELECT * FROM ssdb_integration.lr_strategy.tmp_aq_cov
UNION ALL SELECT * FROM ssdb_integration.lr_strategy.tmp_aq_sellers
ORDER BY part, pct DESC NULLS LAST, n_zips DESC NULLS LAST, item;
