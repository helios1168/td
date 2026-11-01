use role rl_ssdb_Integration_Lr_Strategy_Rw;
use database ssdb_Integration;
use schema lr_strategy;

--Firm 1's unmapped sales (no market metrics firm in TMP_O2_SALES) with every lead to a firm: the review list, and the
--size of each rule we could add (Q45, step A).  Run after 01_opportunity_sales.sql in the same worksheet: reads only its
--temporary tables plus MM_MAP and CRD_TO_CBD (no SLS_RPT_DETAIL, no MGA tables, no wholesaler names).  One result:
--this file's parts, then all of 01's (FILE).
--  DETAIL: one row per company ID x company name x MGA code x FIRM_BASIS x match channel.  Leads, each picked as
--    statement 10 picks (the one name on the CRD, or the one whose route is the sale's channel):
--    MM_MAP_*, CRD_TO_CBD_*: the map's CRD for the company.  NAME_*: market metrics names equal to the company name.
--    ZIP_*: splits only, where the MGA code helps: each sale's one candidate with the sale's channel and opportunity at
--    its ZIP x product, then per code ZIP_FIRM when all the code's sales agree (N_ZIP_FIRMS = 1); AMT_ZIP: $ with such a
--    candidate.  NEW_LIST_LABEL: the company on the new-channel list (a new channel without a firm).
--    LEADS: AGREE (LEAD_FIRM), CONFLICT (leads differ, or the code's sales point to 2+ names), NONE (the review list).
--    Map and name leads are not checked against a split's candidates.
--  SUMMARY: by FIRM_BASIS x LEADS x LEAD_SOURCES; PCT_AMT of FIRM_BASIS.  CHECKS: DETAIL against TMP_O2_SALES.
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_um_detail AS
WITH
u AS (SELECT * FROM ssdb_integration.lr_strategy.tmp_o2_sales WHERE source = 'S1' AND firm_crd IS NULL),
f AS (SELECT firm_crd, broker_name, route, firm_crd || ' | ' || broker_name AS firm
      FROM ssdb_integration.lr_strategy.tmp_o1_firm),
g AS (SELECT sales_firm_id, sales_firm, mga_agent_cd, firm_basis, match_channel, SUM(n_rows) AS n_rows,
             COUNT(DISTINCT seller_key) AS n_sellers, COUNT(DISTINCT zip) AS n_zips, SUM(sales) AS amt,
             SUM(sales_alt) AS amt_alt
      FROM u GROUP BY ALL),
maps AS (
            SELECT 'MM_MAP' AS map, CAST(CAST(CASE WHEN cbd_id = 0 THEN firm_client_id ELSE cbd_id END AS DECIMAL(38, 0))
                                         AS VARCHAR) AS company_id, CAST(CAST(firm_crd AS DECIMAL(38, 0)) AS VARCHAR) AS crd
            FROM ssdb_integration.lr_strategy.mm_map
  UNION ALL SELECT 'CRD_TO_CBD', CAST(CAST(cbd_id AS DECIMAL(38, 0)) AS VARCHAR), CAST(CAST(firm_crd AS DECIMAL(38, 0)) AS VARCHAR)
            FROM ssdb_integration.lr_strategy.crd_to_cbd),
mk AS (SELECT map, company_id, COUNT(DISTINCT crd) AS k, MIN(crd) AS crd FROM maps
       WHERE company_id IS NOT NULL AND crd IS NOT NULL GROUP BY ALL),
gk AS (SELECT DISTINCT sales_firm_id, sales_firm, match_channel FROM g),
lc AS (
            SELECT mk.map AS kind, gk.sales_firm_id, gk.sales_firm, gk.match_channel, mk.k, f.firm, f.route
            FROM gk JOIN mk ON mk.company_id = gk.sales_firm_id LEFT JOIN f ON mk.k = 1 AND f.firm_crd = mk.crd
  UNION ALL SELECT 'NAME', gk.sales_firm_id, gk.sales_firm, gk.match_channel, 1, f.firm, f.route
            FROM gk JOIN f ON UPPER(TRIM(f.broker_name)) = UPPER(TRIM(gk.sales_firm))),
ld AS (SELECT kind, sales_firm_id, sales_firm, match_channel,
              CASE WHEN MAX(k) > 1 THEN 'MAP: 2+ CRDS' WHEN COUNT(firm) = 0 THEN 'CRD NOT IN MARKET METRICS'
                   WHEN COUNT(firm) = 1 THEN 'ONE FIRM'
                   WHEN SUM(CASE WHEN route = match_channel THEN 1 ELSE 0 END) = 1 THEN 'MATCHED BY CHANNEL'
                   WHEN SUM(CASE WHEN route = match_channel THEN 1 ELSE 0 END) > 1 THEN '2+ CHANNEL MATCHES'
                   ELSE 'NO CHANNEL MATCH' END AS status,
              CASE WHEN MAX(k) > 1 THEN NULL WHEN COUNT(firm) = 1 THEN MIN(firm)
                   WHEN SUM(CASE WHEN route = match_channel THEN 1 ELSE 0 END) = 1
                   THEN MIN(CASE WHEN route = match_channel THEN firm END) END AS firm
       FROM lc GROUP BY ALL),
cell AS (SELECT DISTINCT zip, firm_crd, broker_name, product FROM ssdb_integration.lr_strategy.tmp_o1_dataset
         WHERE source = 'S1'),
zr AS (SELECT u.seller_key, u.seller, u.sales_firm_id, u.sales_firm, u.mga_agent_cd, u.zip, u.raw_product,
              u.old_channel, u.firm_basis, u.match_channel, u.sales,
              COUNT(DISTINCT ce.firm_crd || '|' || ce.broker_name) AS n_at_zip,
              MIN(CASE WHEN ce.firm_crd IS NOT NULL THEN f.firm END) AS at_zip
       FROM u
       JOIN ssdb_integration.lr_strategy.tmp_o2_company_firm cf ON cf.company_id = u.sales_firm_id
       JOIN f ON f.firm_crd = cf.firm_crd AND f.broker_name = cf.broker_name AND f.route = u.match_channel
       LEFT JOIN cell ce ON ce.zip = u.zip AND ce.product = u.product AND ce.firm_crd = f.firm_crd
                        AND ce.broker_name = f.broker_name
       WHERE u.firm_basis LIKE 'SPLIT%'
       GROUP BY ALL),
zl AS (SELECT sales_firm_id, sales_firm, mga_agent_cd, firm_basis, match_channel,
              COUNT(DISTINCT CASE WHEN n_at_zip = 1 THEN at_zip END) AS n_zip_firms,
              MIN(CASE WHEN n_at_zip = 1 THEN at_zip END) AS zip_firm,
              SUM(CASE WHEN n_at_zip = 1 THEN sales ELSE 0 END) AS amt_zip
       FROM zr GROUP BY ALL),
d AS (SELECT g.*, nl.new_label AS new_list_label,
             COALESCE(m.status, 'NOT IN THE MAP') AS mm_map_lead, m.firm AS mm_map_firm,
             COALESCE(c.status, 'NOT IN THE MAP') AS crd_to_cbd_lead, c.firm AS crd_to_cbd_firm,
             COALESCE(n.status, 'NO NAME MATCH') AS name_lead, n.firm AS name_firm,
             COALESCE(z.n_zip_firms, 0) AS n_zip_firms, CASE WHEN z.n_zip_firms = 1 THEN z.zip_firm END AS zip_firm,
             COALESCE(z.amt_zip, 0) AS amt_zip
      FROM g
      LEFT JOIN ssdb_integration.lr_strategy.tmp_new_label nl ON nl.company_id = g.sales_firm_id
      LEFT JOIN ld m ON m.kind = 'MM_MAP' AND EQUAL_NULL(m.sales_firm_id, g.sales_firm_id)
                    AND EQUAL_NULL(m.sales_firm, g.sales_firm) AND EQUAL_NULL(m.match_channel, g.match_channel)
      LEFT JOIN ld c ON c.kind = 'CRD_TO_CBD' AND EQUAL_NULL(c.sales_firm_id, g.sales_firm_id)
                    AND EQUAL_NULL(c.sales_firm, g.sales_firm) AND EQUAL_NULL(c.match_channel, g.match_channel)
      LEFT JOIN ld n ON n.kind = 'NAME' AND EQUAL_NULL(n.sales_firm_id, g.sales_firm_id)
                    AND EQUAL_NULL(n.sales_firm, g.sales_firm) AND EQUAL_NULL(n.match_channel, g.match_channel)
      LEFT JOIN zl z ON EQUAL_NULL(z.sales_firm_id, g.sales_firm_id) AND EQUAL_NULL(z.sales_firm, g.sales_firm)
                    AND EQUAL_NULL(z.mga_agent_cd, g.mga_agent_cd) AND z.firm_basis = g.firm_basis
                    AND EQUAL_NULL(z.match_channel, g.match_channel)),
e AS (SELECT d.*, COALESCE(zip_firm, mm_map_firm, crd_to_cbd_firm, name_firm) AS lf,
             NULLIF(TRIM(CASE WHEN n_zip_firms > 0 THEN 'ZIP ' ELSE '' END
                         || CASE WHEN mm_map_firm IS NOT NULL THEN 'MM_MAP ' ELSE '' END
                         || CASE WHEN crd_to_cbd_firm IS NOT NULL THEN 'CRD_TO_CBD ' ELSE '' END
                         || CASE WHEN name_firm IS NOT NULL THEN 'NAME' ELSE '' END), '') AS lead_sources
      FROM d),
h AS (SELECT e.*, CASE WHEN n_zip_firms > 1 OR COALESCE(mm_map_firm, lf) <> lf OR COALESCE(crd_to_cbd_firm, lf) <> lf
                            OR COALESCE(name_firm, lf) <> lf THEN 'CONFLICT'
                       WHEN lf IS NOT NULL THEN 'AGREE' ELSE 'NONE' END AS leads
      FROM e)
SELECT h.*, CASE WHEN leads = 'AGREE' THEN lf END AS lead_firm FROM h;

CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_um_out AS
WITH
t AS (SELECT SUM(sales) AS amt FROM ssdb_integration.lr_strategy.tmp_o2_sales WHERE source = 'S1' AND firm_crd IS NULL),
v AS (
            SELECT 'DETAIL' AS part, CAST(NULL AS VARCHAR) AS name, sales_firm_id AS company_id, sales_firm AS company,
                   mga_agent_cd, firm_basis, match_channel, new_list_label, mm_map_lead, mm_map_firm, crd_to_cbd_lead,
                   crd_to_cbd_firm, name_lead, name_firm, n_zip_firms, zip_firm, amt_zip, leads, lead_sources, lead_firm,
                   CAST(1 AS BIGINT) AS n_groups, CAST(NULL AS BIGINT) AS n_companies, n_rows, n_sellers, n_zips, amt,
                   amt_alt
            FROM ssdb_integration.lr_strategy.tmp_um_detail
  UNION ALL SELECT 'SUMMARY', NULL, NULL, NULL, NULL, firm_basis,
                   NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL,
                   SUM(amt_zip), leads, lead_sources, NULL, COUNT(*), COUNT(DISTINCT sales_firm_id), SUM(n_rows), NULL,
                   NULL, SUM(amt), SUM(amt_alt)
            FROM ssdb_integration.lr_strategy.tmp_um_detail GROUP BY ALL
  UNION ALL SELECT 'CHECKS', 'DETAIL MINUS TMP_O2_SALES UNRESOLVED (MUST BE 0)', NULL, NULL, NULL, NULL,
                   NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL,
                   NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL,
                   ROUND(COALESCE(SUM(d.amt), 0) - COALESCE(MAX(t.amt), 0), 2), NULL
            FROM ssdb_integration.lr_strategy.tmp_um_detail d CROSS JOIN t)
SELECT *, ROUND(100 * amt / NULLIF(SUM(amt) OVER (PARTITION BY part, CASE WHEN part = 'SUMMARY' THEN firm_basis END), 0),
                2) AS pct_amt
FROM v;

--Everything, one result set: this file's parts, then 01_opportunity_sales.sql's (its statement 15, in these columns).
SELECT 'SALES_UNMAPPED' AS file, part, CAST(NULL AS VARCHAR) AS source, name, CAST(NULL AS VARCHAR) AS item,
       CAST(NULL AS VARCHAR) AS item2, company_id, company, mga_agent_cd, firm_basis, match_channel, new_list_label,
       mm_map_lead, mm_map_firm, crd_to_cbd_lead, crd_to_cbd_firm, name_lead, name_firm, n_zip_firms, zip_firm, amt_zip,
       leads, lead_sources, lead_firm, n_groups, n_companies, n_rows, n_sellers, n_zips, CAST(NULL AS BIGINT) AS n_cells,
       CAST(NULL AS BIGINT) AS n_firms, CAST(NULL AS BIGINT) AS n_holders, CAST(NULL AS BIGINT) AS n_wholesalers, amt,
       amt_alt, pct_amt
FROM ssdb_integration.lr_strategy.tmp_um_out
UNION ALL
SELECT '01 OPPORTUNITY', part, source, name, item, item2,
       NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL,
       NULL, NULL, NULL, NULL, NULL, n_cells, n_firms, n_holders, NULL, amt, NULL,
       ROUND(100.0 * amt / NULLIF(SUM(amt) OVER (PARTITION BY part, source, name), 0), 2)
FROM ssdb_integration.lr_strategy.tmp_o1_out
UNION ALL
SELECT '01 SALES', part, source, name, item, NULL,
       NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL,
       NULL, NULL, n_rows, NULL, NULL, NULL, n_firms, NULL, n_wholesalers, amt, NULL,
       ROUND(100.0 * amt / NULLIF(SUM(amt) OVER (PARTITION BY part, source, name), 0), 2)
FROM ssdb_integration.lr_strategy.tmp_o2_out
ORDER BY file DESC, part, firm_basis, amt DESC NULLS LAST, source, name, item;
