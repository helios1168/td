-- The review CRD of 23 (Q20): opp_matched splits it over C00130 (55 ZIPs) and C00312 (1,313 ZIPs, 2.8% of the kept
-- file OPP); crd_cbd says C00130; CRD_MATCH takes C00312, which has no union rows, while firm_2 sells 4.17% of its
-- sales at C00130 (DATASET_LOG.md, 2026-10-25).  Run at work: the codes are turned back into real values through
-- synthetic_key, so the output holds names; keep it at work.

-- 1.  Which two companies are C00130 and C00312?  C00312 should have no union rows.
SELECT k.CODE, k.VALUE AS CBD_ID, u.SOURCE, u.FIRM, u.PARENT, u.CHANNEL, COUNT(u.CBD_ID) AS UNION_ROWS
FROM ssdb_integration.lr_strategy.synthetic_key k
LEFT JOIN ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys u ON u.CBD_ID = k.VALUE
WHERE k.KIND = 'CBD_ID' AND k.CODE IN ('C00130', 'C00312')
GROUP BY 1, 2, 3, 4, 5, 6
ORDER BY 1;

-- 2.  Which CRD is it, and how do opp_matched and crd_cbd map it?
WITH c AS (SELECT VALUE AS CBD_ID FROM ssdb_integration.lr_strategy.synthetic_key
           WHERE KIND = 'CBD_ID' AND CODE = 'C00130'),
crd AS (SELECT DISTINCT m.FIRM_CRD FROM ssdb_integration.lr_strategy.opp_matched m
        JOIN c ON CAST(m.CBD_ID AS VARCHAR) = c.CBD_ID)
SELECT 'opp_matched' AS SRC, m.FIRM_CRD, m.BROKER_NAME, CAST(m.CBD_ID AS VARCHAR) AS CBD_ID,
       COUNT(*) AS ROWS_, COUNT(DISTINCT m.ZIP_CODE) AS ZIPS
FROM ssdb_integration.lr_strategy.opp_matched m JOIN crd USING (FIRM_CRD)
GROUP BY 1, 2, 3, 4
UNION ALL
SELECT 'crd_cbd', x.FIRM_CRD, NULL, CAST(x.CBD_ID AS VARCHAR), COUNT(*), NULL
FROM ssdb_integration.lr_strategy.crd_cbd x JOIN crd USING (FIRM_CRD)
GROUP BY 1, 2, 3, 4;
