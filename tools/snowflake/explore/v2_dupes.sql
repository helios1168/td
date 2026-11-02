use role rl_ssdb_Integration_Lr_Strategy_Rw;
use database ssdb_Integration;
use schema lr_strategy;

--Citizens Securities and HSBC in DATA_WITHNEWCHANNEL_UNION_W_JOINKEYS_V2: which kind of duplicate (owner, 2026-11-02:
--"it looks like we have quite a few duplicates for citizens securities and hsbc").  Reads the existing table; one
--result, per CHECK x SOURCE x FIRM x CBD_ID (N_ROWS, MM_OPP, ACTUAL_SALES_AMOUNT: the extra rows and their $):
--  EXACT DUPLICATE ROWS: rows equal in every column to another row.
--  CELL ON 2+ ROWS: a ZIP x CRD x firm x product x DIST_CH x NEW_DIST with MM_OPP on 2+ rows (the $ above one row).
--  CRD ON 2+ FIRM NAMES (N_ROWS: names), FIRM NAME ON 2+ CRDS (N_ROWS: CRDs).
--  ALL ROWS: rows and $ per source (the two sources are two firms' estimates of one market, not duplicates).
WITH
v AS (SELECT * FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys_v2
      WHERE firm ILIKE '%CITIZENS%' OR firm ILIKE '%HSBC%'),
x AS (SELECT HASH(*) AS h, * FROM v),
e AS (SELECT h, MIN(source) AS source, MIN(firm) AS firm, MIN(cbd_id) AS cbd_id, COUNT(*) - 1 AS n,
             MIN(mm_opp) * (COUNT(*) - 1) AS opp, MIN(actual_sales_amount) * (COUNT(*) - 1) AS sales
      FROM x GROUP BY h HAVING COUNT(*) > 1),
c AS (SELECT source, firm, cbd_id, COUNT(*) AS n, SUM(mm_opp) - MAX(mm_opp) AS opp
      FROM v WHERE mm_opp <> 0
      GROUP BY source, zip_code, cbd_id, firm, product_v2, dist_ch, new_dist HAVING COUNT(*) > 1)
            SELECT 'EXACT DUPLICATE ROWS' AS check_name, source, firm, cbd_id, SUM(n) AS n_rows, SUM(opp) AS mm_opp,
                   SUM(sales) AS actual_sales_amount
            FROM e GROUP BY ALL
  UNION ALL SELECT 'CELL ON 2+ ROWS', source, firm, cbd_id, SUM(n) - COUNT(*), SUM(opp), NULL FROM c GROUP BY ALL
  UNION ALL SELECT 'CRD ON 2+ FIRM NAMES', source, LISTAGG(DISTINCT firm, ' | '), cbd_id, COUNT(DISTINCT firm), NULL, NULL
            FROM v GROUP BY source, cbd_id HAVING COUNT(DISTINCT firm) > 1
  UNION ALL SELECT 'FIRM NAME ON 2+ CRDS', source, firm, LISTAGG(DISTINCT cbd_id, ' | '), COUNT(DISTINCT cbd_id), NULL, NULL
            FROM v GROUP BY source, firm HAVING COUNT(DISTINCT cbd_id) > 1
  UNION ALL SELECT 'ALL ROWS', source, firm, cbd_id, COUNT(*), SUM(mm_opp), SUM(actual_sales_amount) FROM v GROUP BY ALL
ORDER BY check_name, source, firm, cbd_id;
