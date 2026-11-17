use role rl_ssdb_Integration_Lr_Strategy_Rw;
use database ssdb_Integration;
use schema lr_strategy;

--The FIRM_CRD to CBD_ID mapping as the latest union table carries it.  Read-only, one Run All file, one result.
--One row per SOURCE x FIRM_CRD x CBD_ID, with the firm names, parents and channels seen on that pair, and flags for
--the splits: firm 1 made CBD_ID to split one CRD by channel (owner, 2026-10-30), so a CRD can have several CBD_IDs and a
--CBD_ID can cover several CRDs.  No wholesaler and no sales: MM_OPP is opportunity (not confidential), N_ROWS counts
--rows.  Firm names may be shared (owner, 2026-11-09).
--Columns:
--  SOURCE, FIRM_CRD, CBD_ID           the pair (trimmed, blank as NULL)
--  FIRMS, PARENTS                     the distinct firm names and parents on the pair, ' | ' between them
--  DIST_CH, NEW_DIST                  the distinct channels on the pair, ' | ' between them
--  N_ROWS, MM_OPP                     rows of the union on the pair, and their positive MM_OPP summed (a cell repeated on
--                                     several holder rows counts each time: a guide to size, not a total)
--  N_CBD_FOR_CRD, N_CRD_FOR_CBD       how many CBD_IDs the CRD has in this SOURCE, and how many CRDs the CBD_ID has
--  CBD_IS_CRD                         1 when CBD_ID equals FIRM_CRD (the union may carry the CRD as CBD_ID)
--Filter as needed, e.g. N_CBD_FOR_CRD > 1 for the split CRDs.

SET union_tbl = 'ssdb_integration.lr_strategy.sales_opp_2026_11_9';

WITH
u AS (SELECT source, NULLIF(TRIM(CAST(firm_crd AS VARCHAR)), '') AS firm_crd, NULLIF(TRIM(CAST(cbd_id AS VARCHAR)), '') AS cbd_id,
             NULLIF(TRIM(firm), '') AS firm, NULLIF(TRIM(parent), '') AS parent, NULLIF(TRIM(dist_ch), '') AS dist_ch,
             NULLIF(TRIM(new_dist), '') AS new_dist, mm_opp
      FROM IDENTIFIER($union_tbl)),
p AS (SELECT source, firm_crd, cbd_id, COUNT(*) AS n_rows, SUM(CASE WHEN mm_opp > 0 THEN mm_opp ELSE 0 END) AS mm_opp
      FROM u GROUP BY source, firm_crd, cbd_id),
f AS (SELECT source, firm_crd, cbd_id, LISTAGG(firm, ' | ') WITHIN GROUP (ORDER BY firm) AS firms
      FROM (SELECT DISTINCT source, firm_crd, cbd_id, firm FROM u WHERE firm IS NOT NULL) GROUP BY source, firm_crd, cbd_id),
pa AS (SELECT source, firm_crd, cbd_id, LISTAGG(parent, ' | ') WITHIN GROUP (ORDER BY parent) AS parents
       FROM (SELECT DISTINCT source, firm_crd, cbd_id, parent FROM u WHERE parent IS NOT NULL) GROUP BY source, firm_crd, cbd_id),
d AS (SELECT source, firm_crd, cbd_id, LISTAGG(dist_ch, ' | ') WITHIN GROUP (ORDER BY dist_ch) AS dist_chs
      FROM (SELECT DISTINCT source, firm_crd, cbd_id, dist_ch FROM u WHERE dist_ch IS NOT NULL) GROUP BY source, firm_crd, cbd_id),
nd AS (SELECT source, firm_crd, cbd_id, LISTAGG(new_dist, ' | ') WITHIN GROUP (ORDER BY new_dist) AS new_dists
       FROM (SELECT DISTINCT source, firm_crd, cbd_id, new_dist FROM u WHERE new_dist IS NOT NULL) GROUP BY source, firm_crd, cbd_id)
SELECT p.source, p.firm_crd, p.cbd_id, f.firms, pa.parents, d.dist_chs AS dist_ch, nd.new_dists AS new_dist, p.n_rows, p.mm_opp,
       COUNT(DISTINCT p.cbd_id) OVER (PARTITION BY p.source, p.firm_crd) AS n_cbd_for_crd,
       COUNT(DISTINCT p.firm_crd) OVER (PARTITION BY p.source, p.cbd_id) AS n_crd_for_cbd,
       CASE WHEN p.cbd_id = p.firm_crd THEN 1 ELSE 0 END AS cbd_is_crd
FROM p
LEFT JOIN f ON EQUAL_NULL(f.source, p.source) AND EQUAL_NULL(f.firm_crd, p.firm_crd) AND EQUAL_NULL(f.cbd_id, p.cbd_id)
LEFT JOIN pa ON EQUAL_NULL(pa.source, p.source) AND EQUAL_NULL(pa.firm_crd, p.firm_crd) AND EQUAL_NULL(pa.cbd_id, p.cbd_id)
LEFT JOIN d ON EQUAL_NULL(d.source, p.source) AND EQUAL_NULL(d.firm_crd, p.firm_crd) AND EQUAL_NULL(d.cbd_id, p.cbd_id)
LEFT JOIN nd ON EQUAL_NULL(nd.source, p.source) AND EQUAL_NULL(nd.firm_crd, p.firm_crd) AND EQUAL_NULL(nd.cbd_id, p.cbd_id)
ORDER BY p.source, p.firm_crd, p.cbd_id;
