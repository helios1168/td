use role rl_ssdb_Integration_Lr_Strategy_Rw;
use database ssdb_Integration;
use schema lr_strategy;

--How the old union table carried IFA/IMO, FI/IMO, IMO and Raymond James (owner, 2026-11-01: "we've completely broken
--ifa/imo and raymond james now"; "we don't have the eqh v3 query, but I can send you extracts").  Reads the two tables
--owner_sql/uni_latest.sql unions (fiscal year 2025) and the live Tableau table.  One result set, no wholesaler names:
--  MAP: each old table's DIST_CH -> NEW_DIST by row type (opportunity only, sales only, both): rows, firms, $.
--  IMO AND RAYMOND JAMES FIRMS: firm 2's rows with an IMO label (DIST_CH or NEW_DIST), and either firm's Raymond James
--    rows, per CBD_ID x FIRM x DIST_CH x NEW_DIST x row type.
--  IMO SELLERS' TERRITORIES: the live table's sales with an IMO label (DIST_CH or CHANNEL), by whether the seller's
--    SALES_WHOLESALER_TERRITORY_ID is some row's TERRITORY_WHOLESALER_TERRITORY_ID, and that row's DIST_CH (the
--    seller's territory channels, lowest .. highest), i.e. whose territory ifa_imo_names_match gave the seller.
--Download as CSV into $TD_REPO/data/safe/.
--EDIT: the two tables owner_sql/uni_latest.sql reads (its first branch is firm 2's, its second firm 1's).
SET s1_old = 'ssdb_integration.lr_strategy.<firm 1 table, uni_latest.sql second branch>';
SET s2_old = 'ssdb_integration.lr_strategy.<firm 2 table, uni_latest.sql first branch>';

WITH
o AS (
            SELECT 'S1' AS source, CAST(cbd_id AS VARCHAR) AS cbd_id, firm, dist_ch, new_dist,
                   CAST(COALESCE(mm_opp, 0) AS DECIMAL(38, 6)) AS opp,
                   CAST(COALESCE(actual_sales_amount, 0) AS DECIMAL(38, 6)) AS sales,
                   CAST(COALESCE(sales_amount, 0) AS DECIMAL(38, 6)) AS comp
            FROM IDENTIFIER($s1_old) WHERE fiscal_yr = 2025
  UNION ALL SELECT 'S2', CAST(cbd_id AS VARCHAR), firm, dist_ch, new_dist, CAST(COALESCE(mm_opp, 0) AS DECIMAL(38, 6)),
                   CAST(COALESCE(actual_sales_amount, 0) AS DECIMAL(38, 6)),
                   CAST(COALESCE(sales_amount, 0) AS DECIMAL(38, 6))
            FROM IDENTIFIER($s2_old) WHERE fiscal_yr = 2025),
r AS (SELECT o.*, CASE WHEN sales = 0 AND comp = 0 THEN 'OPPORTUNITY ONLY' WHEN opp = 0 THEN 'SALES ONLY'
                       ELSE 'BOTH' END AS row_type FROM o),
l AS (SELECT * FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys WHERE fiscal_yr = 2025),
tw AS (SELECT territory_wholesaler_territory_id AS id, COUNT(DISTINCT dist_ch) AS n_ch, MIN(dist_ch) AS ch_lo,
              MAX(dist_ch) AS ch_hi
       FROM l WHERE territory_wholesaler_territory_id IS NOT NULL GROUP BY ALL)
            SELECT 'MAP' AS part, source, dist_ch, new_dist, CAST(NULL AS VARCHAR) AS channel, row_type AS item,
                   CAST(NULL AS VARCHAR) AS cbd_id, CAST(NULL AS VARCHAR) AS firm, COUNT(*) AS n_rows,
                   COUNT(DISTINCT cbd_id) AS n_firms, SUM(opp) AS mm_opp, SUM(sales) AS actual_sales_amount,
                   SUM(comp) AS sales_amount
            FROM r GROUP BY ALL
  UNION ALL SELECT 'IMO AND RAYMOND JAMES FIRMS', source, dist_ch, new_dist, NULL, row_type, cbd_id, firm, COUNT(*),
                   1, SUM(opp), SUM(sales), SUM(comp)
            FROM r
            WHERE (source = 'S2' AND (dist_ch ILIKE '%IMO%' OR new_dist ILIKE '%IMO%')) OR firm ILIKE '%RAYMOND JAMES%'
            GROUP BY ALL
  UNION ALL SELECT 'IMO SELLERS'' TERRITORIES', l.source, l.dist_ch, l.new_dist, l.channel,
                   CASE WHEN l.sales_wholesaler_territory_id IS NULL THEN 'NO SELLER ID'
                        WHEN tw.id IS NULL THEN 'SELLER HOLDS NO TERRITORY'
                        ELSE 'SELLER HOLDS: ' || tw.ch_lo || CASE WHEN tw.n_ch > 1 THEN ' .. ' || tw.ch_hi ELSE '' END
                   END, NULL, NULL, COUNT(*), COUNT(DISTINCT l.cbd_id),
                   SUM(CAST(COALESCE(l.mm_opp, 0) AS DECIMAL(38, 6))),
                   SUM(CAST(COALESCE(l.actual_sales_amount, 0) AS DECIMAL(38, 6))),
                   SUM(CAST(COALESCE(l.sales_amount, 0) AS DECIMAL(38, 6)))
            FROM l LEFT JOIN tw ON tw.id = l.sales_wholesaler_territory_id
            WHERE (l.dist_ch ILIKE '%IMO%' OR l.channel ILIKE '%IMO%') AND COALESCE(l.actual_sales_amount, 0) <> 0
            GROUP BY ALL
ORDER BY part, source, actual_sales_amount DESC, mm_opp DESC;
