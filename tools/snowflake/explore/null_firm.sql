-- firm_2 opp-only rows of UNION_OPP with no FIRM / PARENT: companies of the opportunity file that have no row in
-- union_base, so 24 has nothing to copy FIRM and PARENT from.  On the coded extract: 22 CBD_IDs, 6,022 rows, 5.25% of
-- firm_2 MM_OPP; two of them hold 4.9% (DATASET_LOG.md, 2026-10-25).  Run at work; the output has firm names.
WITH
nf AS (SELECT CBD_ID, COUNT(*) AS N_ROWS, SUM(MM_OPP) AS MM_OPP
       FROM ssdb_integration.lr_strategy.UNION_OPP
       WHERE FIRM IS NULL AND ROW_ORIGIN = 'opp file' GROUP BY CBD_ID),
names AS (SELECT DISTINCT CAST(FIRM_CRD AS VARCHAR) AS FIRM_CRD, BROKER_NAME FROM ssdb_integration.lr_strategy.opp_original)
SELECT nf.CBD_ID, nf.N_ROWS, nf.MM_OPP, ROUND(100 * nf.MM_OPP / SUM(nf.MM_OPP) OVER (), 1) AS PCT_OF_THESE,
       LISTAGG(DISTINCT c.FIRM_CRD || ' ' || n.BROKER_NAME || ' (' || c.METHOD || ')', '; ') AS CRDS
FROM nf
LEFT JOIN ssdb_integration.lr_strategy.CRD_MATCH c ON c.CBD_ID = nf.CBD_ID
LEFT JOIN names n ON n.FIRM_CRD = c.FIRM_CRD
GROUP BY nf.CBD_ID, nf.N_ROWS, nf.MM_OPP
ORDER BY nf.MM_OPP DESC;
