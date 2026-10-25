-- CRD_MATCH: one row per FIRM_CRD of firm_2's opportunity file (opp_original, after the drops), with the CBD_ID
-- we assign it.  It answers: which distribution company is this CRD?  The first evidence is equality: the CBD_ID
-- whose firm_1 MM_OPP equals the CRD's OPP in the most ZIP_CODE x PRODUCT_V2 cells (the two files carry one
-- measure, DATASET_LOG.md, 2026-10-24).  Where that is weak, opp_matched and crd_cbd decide, and a CRD they
-- cannot settle is 'review'.  (Q20: proposed rule.)
-- Statement 1 builds OPP_MAPPED, opp_original with every map applied (DIST_CH, PRODUCT_V2, ZIP_CODE padded to 5)
-- and the reason a row is dropped; 24 reads it too.
-- Every map is written in codes and translated to real values through ssdb_integration.lr_strategy.synthetic_key
-- (CODE -> VALUE; DIST_CH rows carry SOURCE = firm_2's real SOURCE), so this file runs on real values and on the
-- coded extract alike.  CHANNEL values are clear.  Amount thresholds scale by the key's MM_OPP divisor.
-- firm_1's MM_OPP is read from union_base, the union without firm_2's opportunity (owner, 2026-10-25).
-- Run statements 1 and 2, then 3 (checks: every MUST_BE_ZERO row must be 0), then 4 (the review list).

-- Statement 1.  OPP_MAPPED.
CREATE OR REPLACE TABLE ssdb_integration.lr_strategy.OPP_MAPPED AS
WITH
k AS (SELECT * FROM ssdb_integration.lr_strategy.synthetic_key),
s2 AS (SELECT VALUE AS V FROM k WHERE KIND = 'SOURCE' AND CODE = 'firm_2'),
dm AS (              -- opportunity-file DIST_CH -> union DIST_CH (owner, 2026-10-25, Q19); GONE = no channel, rows dropped
  SELECT a.VALUE AS FILE_DIST_CH, b.VALUE AS DIST_CH, m.GONE
  FROM (VALUES ('O2_01', 'D2_01', FALSE), ('O2_02', 'D2_02', FALSE), ('O2_03', 'D2_04', FALSE),
               ('O2_04', 'D2_03', FALSE), ('O2_05', NULL, TRUE)) m(FILE_CODE, UNION_CODE, GONE)
  CROSS JOIN s2
  JOIN k a ON a.KIND = 'DIST_CH' AND a.SOURCE = s2.V AND a.CODE = m.FILE_CODE
  LEFT JOIN k b ON b.KIND = 'DIST_CH' AND b.SOURCE = s2.V AND b.CODE = m.UNION_CODE),
pm AS (              -- (PRODUCT_LINE, VA_PRODUCT_TYPE) -> PRODUCT_V2 (owner, 2026-10-24, Q22); GONE = fixed annuity, rows dropped
  SELECT pl.VALUE AS PL, va.VALUE AS VA, p.VALUE AS PRODUCT_V2, m.GONE
  FROM (VALUES ('PR05', 'V01', 'PR04', FALSE), ('PR05', 'V02', 'PR01', FALSE), ('PR05', 'V03', 'PR02', FALSE),
               ('L02', NULL, 'PR03', FALSE), ('L01', NULL, NULL, TRUE)) m(PL_CODE, VA_CODE, PRODUCT_CODE, GONE)
       -- (a first row without NULLs, so VALUES types every column as text)
  JOIN k pl ON pl.KIND = 'PRODUCT_V2' AND pl.CODE = m.PL_CODE
  LEFT JOIN k va ON va.KIND = 'VA_TYPE' AND va.CODE = m.VA_CODE
  LEFT JOIN k p ON p.KIND = 'PRODUCT_V2' AND p.CODE = m.PRODUCT_CODE)
SELECT CAST(o.FIRM_CRD AS VARCHAR) AS FIRM_CRD,
       LPAD(CAST(o.ZIP_CODE AS VARCHAR), 5, '0') AS ZIP_CODE,
       CAST(o.DIST_CH AS VARCHAR) AS FILE_DIST_CH,
       dm.DIST_CH, pm.PRODUCT_V2, o.OPP,
       -- a label or pair in no map is never dropped: it is an unmapped row, and the checks fail on it
       CASE WHEN pm.GONE IS NULL OR (NOT pm.GONE AND pm.PRODUCT_V2 IS NULL) THEN 'unmapped product'
            WHEN dm.GONE IS NULL OR (NOT dm.GONE AND dm.DIST_CH IS NULL) THEN 'unmapped DIST_CH'
            WHEN pm.GONE THEN 'fixed'
            WHEN dm.GONE THEN 'no channel' END AS DROP_REASON
FROM ssdb_integration.lr_strategy.opp_original o
LEFT JOIN dm ON dm.FILE_DIST_CH = CAST(o.DIST_CH AS VARCHAR)
LEFT JOIN pm ON pm.PL = CAST(o.PRODUCT_LINE AS VARCHAR) AND pm.VA IS NOT DISTINCT FROM CAST(o.VA_PRODUCT_TYPE AS VARCHAR);

-- Statement 2.  The table.
CREATE OR REPLACE TABLE ssdb_integration.lr_strategy.CRD_MATCH AS
WITH
k AS (SELECT * FROM ssdb_integration.lr_strategy.synthetic_key),
s1 AS (SELECT VALUE AS V FROM k WHERE KIND = 'SOURCE' AND CODE = 'firm_1'),
d AS (SELECT NUM AS D FROM k WHERE KIND = 'divisor' AND VALUE = 'MM_OPP'),
f2 AS (              -- firm_2: OPP per FIRM_CRD x ZIP_CODE x PRODUCT_V2, repeated keys summed
  SELECT FIRM_CRD, ZIP_CODE, PRODUCT_V2, SUM(OPP) AS V
  FROM ssdb_integration.lr_strategy.OPP_MAPPED WHERE DROP_REASON IS NULL
  GROUP BY FIRM_CRD, ZIP_CODE, PRODUCT_V2),
f1 AS (              -- firm_1: MM_OPP per CBD_ID x ZIP_CODE x PRODUCT_V2
  SELECT u.CBD_ID, u.ZIP_CODE, u.PRODUCT_V2, SUM(u.MM_OPP) AS V
  FROM ssdb_integration.lr_strategy.union_base u
  JOIN s1 ON u.SOURCE = s1.V
  WHERE u.CBD_ID IS NOT NULL
  GROUP BY u.CBD_ID, u.ZIP_CODE, u.PRODUCT_V2),
c AS (               -- cells to compare: at least 0.01 on each side
  SELECT f2.* FROM f2 CROSS JOIN d WHERE f2.V >= 0.01 * d.D),
n AS (SELECT FIRM_CRD, COUNT(*) AS N FROM c GROUP BY FIRM_CRD),
kc AS (              -- K: cells where this CBD_ID's firm_1 value is within 0.0015 of the CRD's
  SELECT c.FIRM_CRD, f1.CBD_ID, COUNT(*) AS K
  FROM c
  JOIN f1 ON f1.ZIP_CODE = c.ZIP_CODE AND f1.PRODUCT_V2 = c.PRODUCT_V2
  CROSS JOIN d
  WHERE f1.V >= 0.01 * d.D AND ABS(c.V - f1.V) <= 0.0015 * d.D
  GROUP BY c.FIRM_CRD, f1.CBD_ID),
kr AS (SELECT *, ROW_NUMBER() OVER (PARTITION BY FIRM_CRD ORDER BY K DESC, CBD_ID) AS RK FROM kc),
crd AS (SELECT FIRM_CRD, SUM(OPP) AS OPP FROM ssdb_integration.lr_strategy.OPP_MAPPED
        WHERE DROP_REASON IS NULL GROUP BY FIRM_CRD),
om AS (              -- opp_matched: the CBD_ID on most rows of the CRD
  SELECT FIRM_CRD, CBD_ID, ROW_NUMBER() OVER (PARTITION BY FIRM_CRD ORDER BY R DESC, CBD_ID) AS RK,
         COUNT(*) OVER (PARTITION BY FIRM_CRD) AS N_CBD
  FROM (SELECT CAST(FIRM_CRD AS VARCHAR) AS FIRM_CRD, CAST(CBD_ID AS VARCHAR) AS CBD_ID, COUNT(*) AS R
        FROM ssdb_integration.lr_strategy.opp_matched
        WHERE CBD_ID IS NOT NULL AND CAST(CBD_ID AS VARCHAR) <> '0' GROUP BY 1, 2) x),   -- '0' = no company (owner, 2026-10-25)
cc AS (              -- crd_cbd: same rule
  SELECT FIRM_CRD, CBD_ID, ROW_NUMBER() OVER (PARTITION BY FIRM_CRD ORDER BY R DESC, CBD_ID) AS RK,
         COUNT(*) OVER (PARTITION BY FIRM_CRD) AS N_CBD
  FROM (SELECT CAST(FIRM_CRD AS VARCHAR) AS FIRM_CRD, CAST(CBD_ID AS VARCHAR) AS CBD_ID, COUNT(*) AS R
        FROM ssdb_integration.lr_strategy.crd_cbd
        WHERE CBD_ID IS NOT NULL AND CAST(CBD_ID AS VARCHAR) <> '0' GROUP BY 1, 2) x),
j AS (
  SELECT crd.FIRM_CRD, crd.OPP, n.N AS N_CELLS,
         k1.CBD_ID AS EQ_CBD_ID,
         CASE WHEN n.N > 0 THEN COALESCE(k1.K, 0) / n.N END AS EQ_SHARE,
         CASE WHEN n.N > 0 THEN COALESCE(k2.K, 0) / n.N END AS RUNNER_UP_SHARE,
         om.CBD_ID AS OM_CBD_ID, om.N_CBD AS OM_N_CBD,
         cc.CBD_ID AS CC_CBD_ID, cc.N_CBD AS CC_N_CBD
  FROM crd
  LEFT JOIN n ON n.FIRM_CRD = crd.FIRM_CRD
  LEFT JOIN kr k1 ON k1.FIRM_CRD = crd.FIRM_CRD AND k1.RK = 1
  LEFT JOIN kr k2 ON k2.FIRM_CRD = crd.FIRM_CRD AND k2.RK = 2
  LEFT JOIN om ON om.FIRM_CRD = crd.FIRM_CRD AND om.RK = 1
  LEFT JOIN cc ON cc.FIRM_CRD = crd.FIRM_CRD AND cc.RK = 1),
e AS (               -- ponytail: 0.5 = equal in at least half the cells (the log's "likely" floor, 2026-10-25); lower is 'review' territory
  SELECT *, CASE WHEN EQ_SHARE >= 0.5 THEN EQ_CBD_ID END AS EQ_USED FROM j)
SELECT FIRM_CRD, OPP, N_CELLS, EQ_CBD_ID, EQ_SHARE, RUNNER_UP_SHARE, OM_CBD_ID, OM_N_CBD, CC_CBD_ID, CC_N_CBD,
       CASE WHEN EQ_USED IS NOT NULL THEN EQ_USED
            WHEN OM_CBD_ID = CC_CBD_ID THEN OM_CBD_ID
            WHEN CC_CBD_ID IS NULL THEN OM_CBD_ID
            WHEN OM_CBD_ID IS NULL THEN CC_CBD_ID
            ELSE OM_CBD_ID END AS CBD_ID,
       CASE WHEN EQ_USED IS NOT NULL THEN 'equality'
            WHEN OM_CBD_ID = CC_CBD_ID THEN 'tables agree'
            WHEN CC_CBD_ID IS NULL AND OM_CBD_ID IS NOT NULL THEN 'opp_matched only'
            WHEN OM_CBD_ID IS NULL AND CC_CBD_ID IS NOT NULL THEN 'crd_cbd only'
            WHEN OM_CBD_ID IS NULL AND CC_CBD_ID IS NULL THEN 'no company'
            ELSE 'review' END AS METHOD,
       -- every non-NULL of EQ (when used), OM and CC equal
       (EQ_USED IS NULL OR OM_CBD_ID IS NULL OR EQ_USED = OM_CBD_ID)
       AND (EQ_USED IS NULL OR CC_CBD_ID IS NULL OR EQ_USED = CC_CBD_ID)
       AND (OM_CBD_ID IS NULL OR CC_CBD_ID IS NULL OR OM_CBD_ID = CC_CBD_ID) AS AGREES
FROM e;

-- Statement 3.  Checks.
WITH
t AS (SELECT SUM(OPP) AS O FROM ssdb_integration.lr_strategy.CRD_MATCH)
SELECT 'CRD_MATCH FIRM_CRD twice' AS CHECK_NAME,
       (SELECT COUNT(*) FROM (SELECT FIRM_CRD FROM ssdb_integration.lr_strategy.CRD_MATCH
                              GROUP BY FIRM_CRD HAVING COUNT(*) > 1) x) AS VALUE, TRUE AS MUST_BE_ZERO
UNION ALL SELECT 'FIRM_CRDs of opp_original after drops, missing from CRD_MATCH',
       (SELECT COUNT(*) FROM (SELECT DISTINCT FIRM_CRD FROM ssdb_integration.lr_strategy.OPP_MAPPED
                              WHERE DROP_REASON IS NULL) o
        WHERE NOT EXISTS (SELECT 1 FROM ssdb_integration.lr_strategy.CRD_MATCH c WHERE c.FIRM_CRD = o.FIRM_CRD)), TRUE
UNION ALL SELECT 'opp_original rows with an unmapped DIST_CH label',
       (SELECT COUNT(*) FROM ssdb_integration.lr_strategy.OPP_MAPPED WHERE DROP_REASON = 'unmapped DIST_CH'), TRUE
UNION ALL SELECT 'opp_original rows with an unmapped product pair',
       (SELECT COUNT(*) FROM ssdb_integration.lr_strategy.OPP_MAPPED WHERE DROP_REASON = 'unmapped product'), TRUE
UNION ALL SELECT 'CRDs with METHOD ' || METHOD, COUNT(*), FALSE
       FROM ssdb_integration.lr_strategy.CRD_MATCH GROUP BY METHOD
UNION ALL SELECT 'percent of OPP with METHOD ' || METHOD, ROUND(100 * SUM(OPP) / MAX(t.O), 1), FALSE
       FROM ssdb_integration.lr_strategy.CRD_MATCH CROSS JOIN t GROUP BY METHOD
UNION ALL SELECT 'CRDs with NULL CBD_ID',
       (SELECT COUNT(*) FROM ssdb_integration.lr_strategy.CRD_MATCH WHERE CBD_ID IS NULL), FALSE
UNION ALL SELECT 'CRDs where AGREES is false',
       (SELECT COUNT(*) FROM ssdb_integration.lr_strategy.CRD_MATCH WHERE NOT AGREES), FALSE
UNION ALL SELECT 'percent of OPP where AGREES is false',
       (SELECT ROUND(100 * SUM(CASE WHEN NOT AGREES THEN OPP END) / MAX(t.O), 1)
        FROM ssdb_integration.lr_strategy.CRD_MATCH CROSS JOIN t), FALSE
ORDER BY MUST_BE_ZERO DESC, CHECK_NAME;

-- Statement 4.  The review list: METHOD 'review' or AGREES false, largest OPP first.
SELECT *
FROM ssdb_integration.lr_strategy.CRD_MATCH
WHERE METHOD = 'review' OR NOT AGREES
ORDER BY OPP DESC;
