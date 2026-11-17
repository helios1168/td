use role rl_ssdb_Integration_Lr_Strategy_Rw;
use database ssdb_Integration;
use schema lr_strategy;

--The FIRM_CRD to company ID (CBD_ID) mapping, from firm 1's market metrics opportunity, fiscal year 2025, with the company
--ID rule of 01_opportunity_sales.sql statement 2 (tmp_o1_rows_s1): a listed broker name takes its fixed ID (the names
--below, s1_opp_sales.sql:475-479), otherwise the row's CBD_ID, company 0 taking its CLIENT_FIRM_ID.  Read-only, one Run All
--file, one result.
--Not from the union or Tableau table: there CBD_ID holds the CRD and FIRM the broker name (owner, 2026-11-01: "you will
--replace cbd_id with crd, firm with broker_name, and you can leave parent as all null", 01 statement 17), so it carries no
--company ID.
--One row per FIRM_CRD x BROKER_NAME x COMPANY_ID.  No wholesaler and no sales: AMT is the feed's GLOBAL_SALES, the
--market's opportunity, as 01 reads it.  Firm names may be shared (owner, 2026-11-09).
--Columns:
--  FIRM_CRD, BROKER_NAME, COMPANY_ID   the mapping (COMPANY_ID is the CBD_ID 01 uses)
--  RULE                                BY NAME, CLIENT FIRM ID (company 0) or CBD_ID: which part of the rule gave it
--  FEED_CBD_IDS, DIST_CH               the raw CBD_IDs and the feed's channels on the row group, ' | ' between them
--  N_ROWS, AMT                         feed rows and their opportunity
--  N_COMPANY_FOR_CRD                   company IDs the CRD maps to (2+ is a split CRD: firm 1 split it by channel,
--                                      owner 2026-10-30)
--  N_COMPANY_FOR_CRD_NAME              company IDs the CRD x broker name maps to (2+: the name does not decide either)
--  N_CRD_FOR_COMPANY                   CRDs the company ID covers

SET mm_tbl = 'life_prod.lif_murkylake.wc_market_metrics_opportunity';

WITH
cn AS (SELECT broker_name, company_id FROM (VALUES
         ('WELLS FARGO CLEARING SERVICES, LLC', '1822'),
         ('WELLS FARGO CLEARING SERVICES, LLC - BANK', '1823'),
         ('CETERA INVESTMENT SERVICES LLC', '46'),
         ('LPL FINANCIAL LLC - INDEPENDENT', '8'),
         ('LPL FINANCIAL LLC - BANK', '8'),
         ('LPL FINANCIAL LLC', '8')) AS v (broker_name, company_id)),
o AS (SELECT NULLIF(TRIM(CAST(firm_crd AS VARCHAR)), '') AS firm_crd, UPPER(TRIM(broker_name)) AS broker_name,
             NULLIF(TRIM(CAST(cbd_id AS VARCHAR)), '') AS cbd_id, NULLIF(TRIM(CAST(client_firm_id AS VARCHAR)), '') AS client_firm_id,
             NULLIF(UPPER(TRIM(dist_ch)), '') AS dist_ch, global_sales AS amt
      FROM IDENTIFIER($mm_tbl) WHERE fiscal_yr = '2025'),
m AS (SELECT o.*, COALESCE(cn.company_id, CASE WHEN o.cbd_id = '0' THEN o.client_firm_id ELSE o.cbd_id END) AS company_id,
             CASE WHEN cn.company_id IS NOT NULL THEN 'BY NAME' WHEN o.cbd_id = '0' THEN 'CLIENT FIRM ID' ELSE 'CBD_ID' END AS rule
      FROM o LEFT JOIN cn ON cn.broker_name = o.broker_name),
g AS (SELECT firm_crd, broker_name, company_id, MIN(rule) AS rule, COUNT(*) AS n_rows, SUM(amt) AS amt
      FROM m GROUP BY firm_crd, broker_name, company_id),
fc AS (SELECT firm_crd, broker_name, company_id, LISTAGG(cbd_id, ' | ') WITHIN GROUP (ORDER BY cbd_id) AS feed_cbd_ids
       FROM (SELECT DISTINCT firm_crd, broker_name, company_id, cbd_id FROM m WHERE cbd_id IS NOT NULL)
       GROUP BY firm_crd, broker_name, company_id),
fd AS (SELECT firm_crd, broker_name, company_id, LISTAGG(dist_ch, ' | ') WITHIN GROUP (ORDER BY dist_ch) AS dist_chs
       FROM (SELECT DISTINCT firm_crd, broker_name, company_id, dist_ch FROM m WHERE dist_ch IS NOT NULL)
       GROUP BY firm_crd, broker_name, company_id)
SELECT g.firm_crd, g.broker_name, g.company_id, g.rule, fc.feed_cbd_ids, fd.dist_chs AS dist_ch, g.n_rows, g.amt,
       COUNT(DISTINCT g.company_id) OVER (PARTITION BY g.firm_crd) AS n_company_for_crd,
       COUNT(DISTINCT g.company_id) OVER (PARTITION BY g.firm_crd, g.broker_name) AS n_company_for_crd_name,
       COUNT(DISTINCT g.firm_crd) OVER (PARTITION BY g.company_id) AS n_crd_for_company
FROM g
LEFT JOIN fc ON EQUAL_NULL(fc.firm_crd, g.firm_crd) AND EQUAL_NULL(fc.broker_name, g.broker_name) AND EQUAL_NULL(fc.company_id, g.company_id)
LEFT JOIN fd ON EQUAL_NULL(fd.firm_crd, g.firm_crd) AND EQUAL_NULL(fd.broker_name, g.broker_name) AND EQUAL_NULL(fd.company_id, g.company_id)
ORDER BY g.firm_crd, g.broker_name, g.company_id;
