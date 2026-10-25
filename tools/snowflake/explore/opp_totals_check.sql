-- Where firm_2's MM_OPP in UNION_OPP comes from, in coded units (/ the MM_OPP divisor): safe to send back.
-- 24 writes firm_2 MM_OPP from the file (D) onto rows of union_base, and keeps whatever MM_OPP firm_2's rows already
-- carry there (A, which must be 0: union_base is the union without firm_2's opportunity).  So E + F + G = A + D.  On the coded extract A is 0 and E + F + G = D = 56,993.5
-- (DATASET_LOG.md, 2026-10-25).

-- 1.  Reconciliation.
WITH
d AS (SELECT NUM AS D FROM ssdb_integration.lr_strategy.synthetic_key WHERE KIND = 'divisor' AND VALUE = 'MM_OPP'),
s2 AS (SELECT VALUE AS V FROM ssdb_integration.lr_strategy.synthetic_key WHERE KIND = 'SOURCE' AND CODE = 'firm_2'),
uo AS (SELECT u.* FROM ssdb_integration.lr_strategy.UNION_OPP u JOIN s2 ON u.SOURCE = s2.V)
SELECT 'A. union_base: firm_2 rows with MM_OPP (must be 0)' AS STAGE, COUNT(u.MM_OPP) AS N_ROWS,
       ROUND(SUM(u.MM_OPP) / MAX(d.D), 1) AS CODED_UNITS
FROM ssdb_integration.lr_strategy.union_base u JOIN s2 ON u.SOURCE = s2.V CROSS JOIN d
UNION ALL SELECT 'B. union_base: all rows (extract 97,361)', COUNT(*), NULL
FROM ssdb_integration.lr_strategy.union_base
UNION ALL SELECT 'C. opp_original rows; OPP_MAPPED must have the same (extract 306,530)', COUNT(*), ROUND(SUM(OPP) / MAX(d.D), 1)
FROM ssdb_integration.lr_strategy.opp_original CROSS JOIN d
UNION ALL SELECT 'C. OPP_MAPPED rows', COUNT(*), ROUND(SUM(OPP) / MAX(d.D), 1)
FROM ssdb_integration.lr_strategy.OPP_MAPPED CROSS JOIN d
UNION ALL SELECT 'D. OPP_MAPPED kept rows: the file after the drops (extract 234,760 / 56,993.5)', COUNT(*), ROUND(SUM(OPP) / MAX(d.D), 1)
FROM ssdb_integration.lr_strategy.OPP_MAPPED CROSS JOIN d WHERE DROP_REASON IS NULL
UNION ALL SELECT 'E. UNION_OPP firm_2 MM_OPP, ROW_ORIGIN union (extract 0)', COUNT(uo.MM_OPP), ROUND(SUM(uo.MM_OPP) / MAX(d.D), 1)
FROM uo CROSS JOIN d WHERE uo.ROW_ORIGIN = 'union'
UNION ALL SELECT 'F. UNION_OPP firm_2 MM_OPP, ROW_ORIGIN union + opp file', COUNT(uo.MM_OPP), ROUND(SUM(uo.MM_OPP) / MAX(d.D), 1)
FROM uo CROSS JOIN d WHERE uo.ROW_ORIGIN = 'union + opp file'
UNION ALL SELECT 'G. UNION_OPP firm_2 MM_OPP, ROW_ORIGIN opp file', COUNT(uo.MM_OPP), ROUND(SUM(uo.MM_OPP) / MAX(d.D), 1)
FROM uo CROSS JOIN d WHERE uo.ROW_ORIGIN = 'opp file'
UNION ALL SELECT 'H. key: codes used twice within a kind (must be 0)', COUNT(*), NULL
FROM (SELECT KIND, SOURCE, CODE FROM ssdb_integration.lr_strategy.synthetic_key WHERE KIND <> 'divisor'
      GROUP BY KIND, SOURCE, CODE HAVING COUNT(*) > 1) x
ORDER BY STAGE;

-- 2.  Where firm_2's MM_OPP sits: CBD_ID '0', NULL or a company, by ROW_ORIGIN and CBD_METHOD (coded units).
--     Note: a filter CBD_ID <> '0' also drops the NULL rows.
WITH
d AS (SELECT NUM AS D FROM ssdb_integration.lr_strategy.synthetic_key WHERE KIND = 'divisor' AND VALUE = 'MM_OPP'),
s2 AS (SELECT VALUE AS V FROM ssdb_integration.lr_strategy.synthetic_key WHERE KIND = 'SOURCE' AND CODE = 'firm_2')
SELECT CASE WHEN u.CBD_ID IS NULL THEN 'NULL' WHEN CAST(u.CBD_ID AS VARCHAR) = '0' THEN '0' ELSE 'a company' END AS CBD,
       u.ROW_ORIGIN, u.CBD_METHOD, COUNT(*) AS N_ROWS, ROUND(SUM(u.MM_OPP) / MAX(d.D), 1) AS CODED_UNITS
FROM ssdb_integration.lr_strategy.UNION_OPP u JOIN s2 ON u.SOURCE = s2.V CROSS JOIN d
WHERE u.MM_OPP IS NOT NULL
GROUP BY 1, 2, 3 ORDER BY 1, 2, 3;

-- 3.  CRDs that CRD_MATCH puts on '0', by METHOD and by what each table says (coded units).
WITH d AS (SELECT NUM AS D FROM ssdb_integration.lr_strategy.synthetic_key WHERE KIND = 'divisor' AND VALUE = 'MM_OPP')
SELECT METHOD, CAST(OM_CBD_ID AS VARCHAR) = '0' AS OPP_MATCHED_SAYS_0, CAST(CC_CBD_ID AS VARCHAR) = '0' AS CRD_CBD_SAYS_0,
       COUNT(*) AS CRDS, ROUND(SUM(OPP) / MAX(d.D), 1) AS CODED_UNITS
FROM ssdb_integration.lr_strategy.CRD_MATCH CROSS JOIN d
WHERE CAST(CBD_ID AS VARCHAR) = '0'
GROUP BY 1, 2, 3 ORDER BY 5 DESC;

-- 4.  The code '0' got in the key.  C00409 if '0' is only in the opportunity files; a code up to C00408 means the
--     union itself has CBD_ID '0'.
SELECT CODE FROM ssdb_integration.lr_strategy.synthetic_key WHERE KIND = 'CBD_ID' AND VALUE = '0';
