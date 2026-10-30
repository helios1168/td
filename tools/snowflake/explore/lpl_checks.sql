--LPL checks (Q43, DATASET_LOG.md 2026-10-30): in the owner's output firm 1's LPL opportunity is $500MM under the feed
--in total and too high for individual wholesalers; firm 2 ties.  Two parts, one result set:
--  LPL FEED ROWS: the feed's fiscal year 2025 rows with LPL in the broker name, and every row under those rows' CRDs,
--    by the company ID s1_opp_sales.sql:475-482 gives them (that CASE verbatim, sha256 6262e2f93bbd...), CRD, broker
--    name and feed DIST_CH.  COMPANY_ID 8: what the owner's LPL list (:478) catches.  DROPPED (:500): the CASE gives
--    NULL and :500 deletes the row.  Anything else: the row goes on under that company ID (a '|' list is resolved by
--    :511-594).  Checks A1-A3.
--  OWN REGIONS: every company with current regions of its own (CBD not 0) and a current wholesaler, with its master
--    name: what s1_opp_sales.sql:692 leaves out (it keeps company 0's regions and company 3's).  If LPL's companies are
--    here, LPL's opportunity in their ZIPs goes to the channel-level wholesaler in the owner's output.  Checks B1.
--Firm names and opportunity $ appear (no sales $, no person's names).  No table variables: no carrier-named table is
--read.  Run All; download the result as CSV into $TD_REPO/data/safe/.
--Snowflake docs read 2026-10-30: strings compare by Unicode code unless a collation is set
--(https://docs.snowflake.com/en/sql-reference/collation), so the copied CASE matches names exactly as the owner's does;
--ILIKE is LIKE without case (.../functions/ilike); SUM(...) OVER () takes an empty OVER (.../functions/sum); GROUP BY
--ALL (.../constructs/group-by).
use secondary roles all;

--1. LPL's rows in the feed, with the owner's company ID.  PCT_OPP_OF_PART: % of this part's opportunity.
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_lpl_feed AS
SELECT 'LPL FEED ROWS' AS part, x.company_id, x.firm_crd, x.broker_name AS name, x.dist_ch AS label, x.n_rows, x.opp,
       ROUND(100.0 * x.opp / SUM(x.opp) OVER (), 2) AS pct_opp_of_part,
       CAST(NULL AS BIGINT) AS n_regions, CAST(NULL AS BIGINT) AS n_zips, CAST(NULL AS BIGINT) AS n_whslr
FROM (
  SELECT COALESCE(CASE WHEN broker_name = 'Wells Fargo Clearing Services, LLC' THEN '1822'
                       WHEN broker_name = 'Wells Fargo Clearing Services, LLC - BANK' THEN '1823'
                       WHEN broker_name = 'Cetera Investment Services LLC' THEN '46'
                       WHEN broker_name IN ('LPL Financial LLC - INDEPENDENT', 'LPL Financial LLC - BANK', 'LPL Financial LLC') THEN '8'
                       WHEN TO_CHAR(cbd_id) = '0' AND client_firm_id IS NOT NULL THEN TO_CHAR(client_firm_id)
                       WHEN TO_CHAR(cbd_id) = '0' THEN NULL
                       ELSE TO_CHAR(cbd_id) END, 'DROPPED (:500)') AS company_id,
         firm_crd, broker_name, dist_ch, COUNT(*) AS n_rows, SUM(global_sales) AS opp
  FROM life_prod.lif_murkylake.wc_market_metrics_opportunity
  WHERE fiscal_yr = '2025'
    AND (broker_name ILIKE '%LPL%'
         OR firm_crd IN (SELECT firm_crd FROM life_prod.lif_murkylake.wc_market_metrics_opportunity
                         WHERE fiscal_yr = '2025' AND broker_name ILIKE '%LPL%' AND TRIM(firm_crd) <> ''))
  GROUP BY ALL) x;

--2. Companies with regions of their own (counts only: no wholesaler's name).
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_lpl_regions AS
WITH nm AS (SELECT consol_brkr_dealer_id AS cbd, MIN(consol_brkr_dealer_name) AS firm
            FROM life_prod.lif_murkylake.wc_edw_consol_brkr_dealer_mga_master
            WHERE expiration_dte = '9999-12-31' GROUP BY ALL)
SELECT 'OWN REGIONS' AS part, CAST(CAST(gr.cbd AS DECIMAL(38, 0)) AS VARCHAR) AS company_id,
       CAST(NULL AS VARCHAR) AS firm_crd, nm.firm AS name, UPPER(TRIM(gr.distch_channel)) AS label,
       CAST(NULL AS BIGINT) AS n_rows, CAST(NULL AS DECIMAL(38, 2)) AS opp, CAST(NULL AS DOUBLE) AS pct_opp_of_part,
       COUNT(DISTINCT gr.rgn_cd) AS n_regions, COUNT(DISTINCT LEFT(gr.start_zip, 5)) AS n_zips,
       COUNT(DISTINCT rw.whslr_id) AS n_whslr
FROM life_prod.lif_murkylake.geographic_region gr
JOIN life_prod.lif_murkylake.rgn_whslr rw ON rw.rgn_cd = gr.rgn_cd AND rw.expir_dt = '9999-12-31'
LEFT JOIN nm ON nm.cbd = gr.cbd
WHERE gr.expir_dt = '9999-12-31' AND gr.cbd <> 0
GROUP BY ALL;

--3. Everything, one result set: download as CSV.
SELECT * FROM ssdb_integration.lr_strategy.tmp_lpl_feed
UNION ALL SELECT * FROM ssdb_integration.lr_strategy.tmp_lpl_regions
ORDER BY part, opp DESC NULLS LAST, n_zips DESC NULLS LAST, company_id, name;
