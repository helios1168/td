use role rl_ssdb_Integration_Lr_Strategy_Rw;
use database ssdb_Integration;
use schema lr_strategy;

--Firm 1's sales by MGA agent code, sales only (no opportunity): which codes span 2+ companies, firms, channels or
--sellers, how each company's sales spread over codes, and whether a sale left without a firm carries a code that
--resolved sales put on one firm (Q45: could the code pick a split company's firm?).  Reads TMP_O2_SALES
--(01_opportunity_sales.sql, statement 12): run it after 01_opportunity_sales.sql in the same worksheet, with s1_sales
--on the base sales table that has MGA_AGENT_CD (00_base_sales.sql).  Its one result also carries all of
--01_opportunity_sales.sql's (FILE says which), checks included, so one CSV has everything: the tie to the sales table
--by code is 01's SALES TABLE MINUS TMP_O2_SALES BY FIRM X MGA X CHANNEL X PRODUCT check.  No wholesaler names.
--tmp_mga_out columns: PART, ITEM, ITEM2, N_ROWS, N_CODES, N_COMPANIES, N_FIRMS, N_CHANNELS, N_SELLERS, N_ZIPS, AMT (actual $),
--AMT_ALT (comp'd $), PCT_AMT (of PART, and of ITEM in SPANS and UNRESOLVED SALES BY CODE).
--  CODES: one row per code, (BLANK) for none; N_*: distinct companies, firms reached, recorded channels, sellers, ZIPs.
--  COMPANY X CODE: ITEM company ID | name; ITEM2 code | FIRM_BASIS | broker name found.
--  SPANS: codes (blank left out) by how many companies, firms, channels, sellers each spans (0, 1, 2+); and COMPANIES
--    BY CODES, companies by how many codes they carry.
--  UNRESOLVED SALES BY CODE: sales with no firm, by FIRM_BASIS and whether their code is on one firm, 2+ or none
--    among the sales that did get a firm.

CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_mga_out AS
WITH
s AS (SELECT * FROM ssdb_integration.lr_strategy.tmp_o2_sales WHERE source = 'S1'),
c AS (SELECT mga_agent_cd, SUM(n_rows) AS n_rows, COUNT(DISTINCT sales_firm_id) AS n_companies,
             COUNT(DISTINCT firm_crd || '|' || broker_name) AS n_firms, COUNT(DISTINCT old_channel) AS n_channels,
             COUNT(DISTINCT seller_key) AS n_sellers, COUNT(DISTINCT zip) AS n_zips, SUM(sales) AS amt,
             SUM(sales_alt) AS amt_alt
      FROM s GROUP BY ALL),
r AS (SELECT mga_agent_cd, COUNT(DISTINCT firm_crd || '|' || broker_name) AS k FROM s
      WHERE mga_agent_cd IS NOT NULL AND firm_crd IS NOT NULL GROUP BY ALL),
pc AS (SELECT sales_firm_id, COUNT(DISTINCT mga_agent_cd) AS n_codes, SUM(sales) AS amt, SUM(sales_alt) AS amt_alt
       FROM s GROUP BY ALL),
sp AS (
            SELECT 'CODES ON COMPANIES' AS item, n_companies AS n, amt, amt_alt FROM c WHERE mga_agent_cd IS NOT NULL
  UNION ALL SELECT 'CODES ON FIRMS', n_firms, amt, amt_alt FROM c WHERE mga_agent_cd IS NOT NULL
  UNION ALL SELECT 'CODES ON CHANNELS', n_channels, amt, amt_alt FROM c WHERE mga_agent_cd IS NOT NULL
  UNION ALL SELECT 'CODES ON SELLERS', n_sellers, amt, amt_alt FROM c WHERE mga_agent_cd IS NOT NULL),
v AS (
            SELECT 'CODES' AS part, COALESCE(mga_agent_cd, '(BLANK)') AS item, CAST(NULL AS VARCHAR) AS item2, n_rows,
                   CAST(NULL AS BIGINT) AS n_codes, n_companies, n_firms, n_channels, n_sellers, n_zips, amt, amt_alt
            FROM c
  UNION ALL SELECT 'COMPANY X CODE', COALESCE(sales_firm_id, '(BLANK)') || ' | ' || COALESCE(sales_firm, '(BLANK)'),
                   COALESCE(mga_agent_cd, '(BLANK)') || ' | ' || firm_basis || ' | ' || COALESCE(broker_name, '-'),
                   SUM(n_rows), NULL, NULL, NULL, COUNT(DISTINCT old_channel), COUNT(DISTINCT seller_key),
                   COUNT(DISTINCT zip), SUM(sales), SUM(sales_alt)
            FROM s GROUP BY ALL
  UNION ALL SELECT 'SPANS', item, CASE WHEN n >= 2 THEN '2+' ELSE CAST(n AS VARCHAR) END, NULL, COUNT(*), NULL, NULL,
                   NULL, NULL, NULL, SUM(amt), SUM(amt_alt)
            FROM sp GROUP BY ALL
  UNION ALL SELECT 'SPANS', 'COMPANIES BY CODES', CASE WHEN n_codes >= 2 THEN '2+' ELSE CAST(n_codes AS VARCHAR) END,
                   NULL, NULL, COUNT(*), NULL, NULL, NULL, NULL, SUM(amt), SUM(amt_alt)
            FROM pc GROUP BY ALL
  UNION ALL SELECT 'UNRESOLVED SALES BY CODE', s.firm_basis,
                   CASE WHEN s.mga_agent_cd IS NULL THEN 'NO CODE' WHEN r.k IS NULL THEN 'CODE ON NO RESOLVED SALE'
                        WHEN r.k = 1 THEN 'CODE ON ONE FIRM IN RESOLVED SALES'
                        ELSE 'CODE ON 2+ FIRMS IN RESOLVED SALES' END,
                   SUM(s.n_rows), COUNT(DISTINCT s.mga_agent_cd), COUNT(DISTINCT s.sales_firm_id), NULL,
                   COUNT(DISTINCT s.old_channel), COUNT(DISTINCT s.seller_key), COUNT(DISTINCT s.zip), SUM(s.sales),
                   SUM(s.sales_alt)
            FROM s LEFT JOIN r ON r.mga_agent_cd = s.mga_agent_cd
            WHERE s.firm_crd IS NULL GROUP BY ALL)
SELECT *, ROUND(100 * amt / NULLIF(SUM(amt) OVER (PARTITION BY part,
                                    CASE WHEN part IN ('SPANS', 'UNRESOLVED SALES BY CODE') THEN item END), 0), 2) AS pct_amt
FROM v;

--Everything, one result set: this file's parts, then 01_opportunity_sales.sql's (its statement 15, in these columns).
SELECT 'SALES_MGA' AS file, part, CAST(NULL AS VARCHAR) AS source, CAST(NULL AS VARCHAR) AS name, item, item2, n_rows,
       n_codes, n_companies, n_firms, n_channels, n_sellers, n_zips, CAST(NULL AS BIGINT) AS n_cells,
       CAST(NULL AS BIGINT) AS n_holders, CAST(NULL AS BIGINT) AS n_wholesalers, amt, amt_alt, pct_amt
FROM ssdb_integration.lr_strategy.tmp_mga_out
UNION ALL
SELECT '01 OPPORTUNITY', part, source, name, item, item2, NULL, NULL, NULL, n_firms, NULL, NULL, NULL, n_cells, n_holders,
       NULL, amt, NULL, ROUND(100.0 * amt / NULLIF(SUM(amt) OVER (PARTITION BY part, source, name), 0), 2)
FROM ssdb_integration.lr_strategy.tmp_o1_out
UNION ALL
SELECT '01 SALES', part, source, name, item, NULL, n_rows, NULL, NULL, n_firms, NULL, NULL, NULL, NULL, NULL,
       n_wholesalers, amt, NULL, ROUND(100.0 * amt / NULLIF(SUM(amt) OVER (PARTITION BY part, source, name), 0), 2)
FROM ssdb_integration.lr_strategy.tmp_o2_out
ORDER BY file DESC, part, source, name, item, amt DESC NULLS LAST, item2;
