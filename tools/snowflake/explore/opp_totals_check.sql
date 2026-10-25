-- firm_2's opportunity at each stage of 23 and 24, in coded units (/ the MM_OPP divisor), safe to send back.  On the
-- coded extract: opp_original 306,530 rows / 90,431.3; OPP_MAPPED kept 234,760 / 56,993.5; UNION_OPP firm_2 69,045 /
-- 56,993.5; CBD_ID '0' about 0.1% (DATASET_LOG.md, 2026-10-25).  The same numbers at work = same data, no duplication.
WITH
d AS (SELECT NUM AS D FROM ssdb_integration.lr_strategy.synthetic_key WHERE KIND = 'divisor' AND VALUE = 'MM_OPP'),
s2 AS (SELECT VALUE AS V FROM ssdb_integration.lr_strategy.synthetic_key WHERE KIND = 'SOURCE' AND CODE = 'firm_2')
SELECT 'opp_original, all rows' AS STAGE, COUNT(*) AS N_ROWS, ROUND(SUM(OPP) / MAX(d.D), 1) AS CODED_UNITS
FROM ssdb_integration.lr_strategy.opp_original CROSS JOIN d
UNION ALL SELECT 'OPP_MAPPED, kept rows', COUNT(*), ROUND(SUM(OPP) / MAX(d.D), 1)
FROM ssdb_integration.lr_strategy.OPP_MAPPED CROSS JOIN d WHERE DROP_REASON IS NULL
UNION ALL SELECT 'UNION_OPP, firm_2 MM_OPP', COUNT(u.MM_OPP), ROUND(SUM(u.MM_OPP) / MAX(d.D), 1)
FROM ssdb_integration.lr_strategy.UNION_OPP u JOIN s2 ON u.SOURCE = s2.V CROSS JOIN d
UNION ALL SELECT 'UNION_OPP, firm_2 MM_OPP at CBD_ID 0', COUNT(u.MM_OPP), ROUND(SUM(u.MM_OPP) / MAX(d.D), 1)
FROM ssdb_integration.lr_strategy.UNION_OPP u JOIN s2 ON u.SOURCE = s2.V CROSS JOIN d
WHERE CAST(u.CBD_ID AS VARCHAR) = '0';
