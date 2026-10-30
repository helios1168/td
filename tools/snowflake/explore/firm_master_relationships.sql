--How the first-pass firm master's columns relate: cbd_id, firm_client_id, firm_crd, broker_name; and whether dist_ch
--is a property of the firm (6).  Run All.
--EDIT statement 1's FROM to your master table.  Blank, '0' and NULL count as missing; names are upper-cased.
--Counts only: the master has no $.  Read 4 first, then 5 for the cases behind it.

--1. The master, cleaned, with a row id.
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_fm AS
SELECT ROW_NUMBER() OVER (ORDER BY cbd_id, firm_client_id, firm_crd, broker_name) AS RID,
       NULLIF(NULLIF(TRIM(TO_CHAR(cbd_id)), ''), '0')         AS CBD_ID,
       NULLIF(NULLIF(TRIM(TO_CHAR(firm_client_id)), ''), '0') AS CLIENT_ID,
       NULLIF(NULLIF(TRIM(TO_CHAR(firm_crd)), ''), '0')       AS CRD,
       NULLIF(UPPER(TRIM(broker_name)), '')                   AS NAME,
       NULLIF(UPPER(TRIM(TO_CHAR(dist_ch))), '')              AS DIST_CH   -- not an ID: kept out of 2-5 but for 3's last row
FROM ssdb_integration.lr_strategy.<firm_master>;

--2. The same, one row per master row x column.
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_fm_v AS
          SELECT RID, 'cbd_id' AS COL, CBD_ID AS VAL FROM ssdb_integration.lr_strategy.tmp_fm
UNION ALL SELECT RID, 'firm_client_id', CLIENT_ID FROM ssdb_integration.lr_strategy.tmp_fm
UNION ALL SELECT RID, 'firm_crd', CRD FROM ssdb_integration.lr_strategy.tmp_fm
UNION ALL SELECT RID, 'broker_name', NAME FROM ssdb_integration.lr_strategy.tmp_fm;

--3. Profile: per column, how full it is and how often a value repeats; last row, rows repeated whole.
SELECT COL, COUNT(*) AS N_ROWS, COUNT(VAL) AS N_WITH_VALUE, ROUND(100 * (COUNT(*) - COUNT(VAL)) / COUNT(*), 2) AS PCT_MISSING,
       COUNT(DISTINCT VAL) AS N_DISTINCT, ROUND(COUNT(VAL) / NULLIF(COUNT(DISTINCT VAL), 0), 2) AS ROWS_PER_VALUE
FROM ssdb_integration.lr_strategy.tmp_fm_v
GROUP BY COL
UNION ALL
SELECT 'whole row repeated', COUNT(*), NULL, NULL, COUNT(*) - (SELECT COUNT(*) FROM (SELECT DISTINCT CBD_ID, CLIENT_ID, CRD, NAME, DIST_CH
                                                                                   FROM ssdb_integration.lr_strategy.tmp_fm) d), NULL
FROM ssdb_integration.lr_strategy.tmp_fm
ORDER BY COL;

--4. For each pair of columns, every link between their values (rows carrying both), by shape:
--   1 : 1                  the same thing in both columns
--   one A, many B          B nests in A (each B has only this A): A is the coarser level
--   many A, one B          A nests in B
--   many : many            tangled: neither nests; these need a decision
--A pair that is 1 : 1 plus one 'one X, many Y' row is a clean hierarchy.  Each link is counted once, by its own two
--ends: a link beside a tangle can show as one-to-many.  A catch-all value (one ID linked to very many) makes most of
--the many : many links; 5 lists it first.
WITH
l AS (
  SELECT DISTINCT a.COL AS A, a.VAL AS A_VAL, b.COL AS B, b.VAL AS B_VAL
  FROM ssdb_integration.lr_strategy.tmp_fm_v a
  JOIN ssdb_integration.lr_strategy.tmp_fm_v b ON b.RID = a.RID AND a.COL < b.COL
  WHERE a.VAL IS NOT NULL AND b.VAL IS NOT NULL),
na AS (SELECT A, B, A_VAL, COUNT(*) AS N FROM l GROUP BY A, B, A_VAL),   -- B values per A value
nb AS (SELECT A, B, B_VAL, COUNT(*) AS N FROM l GROUP BY A, B, B_VAL)    -- A values per B value
SELECT l.A || ' - ' || l.B AS PAIR,
       CASE WHEN na.N = 1 AND nb.N = 1 THEN '1 : 1'
            WHEN na.N > 1 AND nb.N = 1 THEN 'one ' || l.A || ', many ' || l.B
            WHEN na.N = 1 AND nb.N > 1 THEN 'many ' || l.A || ', one ' || l.B
            ELSE 'many : many' END AS SHAPE,
       COUNT(*) AS N_LINKS, COUNT(DISTINCT l.A_VAL) AS N_A_VALUES, COUNT(DISTINCT l.B_VAL) AS N_B_VALUES
FROM l
JOIN na ON na.A = l.A AND na.B = l.B AND na.A_VAL = l.A_VAL
JOIN nb ON nb.A = l.A AND nb.B = l.B AND nb.B_VAL = l.B_VAL
GROUP BY 1, 2
ORDER BY 1, 2;

--5. The cases: every value of every column that reaches 2+ values of another column, with those values listed.
--The names say why: one root with qualifiers = a split; different names = a merger or a consolidation; near-identical
--spellings = variants.  Largest first within each column.
SELECT *
FROM (SELECT CASE WHEN GROUPING(CBD_ID) = 0 THEN 'cbd_id' WHEN GROUPING(CLIENT_ID) = 0 THEN 'firm_client_id'
                  WHEN GROUPING(CRD) = 0 THEN 'firm_crd' ELSE 'broker_name' END AS BY_COL,
             COALESCE(CBD_ID, CLIENT_ID, CRD, NAME) AS BY_VALUE,   -- the other three are rolled up (NULL) here
             COUNT(*) AS N_ROWS,
             COUNT(DISTINCT CBD_ID) AS N_CBD, COUNT(DISTINCT CLIENT_ID) AS N_CLIENT,
             COUNT(DISTINCT CRD) AS N_CRD, COUNT(DISTINCT NAME) AS N_NAME,
             LISTAGG(DISTINCT CBD_ID, ' | ') WITHIN GROUP (ORDER BY CBD_ID) AS CBD_IDS,
             LISTAGG(DISTINCT CLIENT_ID, ' | ') WITHIN GROUP (ORDER BY CLIENT_ID) AS CLIENT_IDS,
             LISTAGG(DISTINCT CRD, ' | ') WITHIN GROUP (ORDER BY CRD) AS CRDS,
             LISTAGG(DISTINCT NAME, ' | ') WITHIN GROUP (ORDER BY NAME) AS NAMES
      FROM ssdb_integration.lr_strategy.tmp_fm
      GROUP BY GROUPING SETS ((CBD_ID), (CLIENT_ID), (CRD), (NAME))
      HAVING COALESCE(CBD_ID, CLIENT_ID, CRD, NAME) IS NOT NULL   -- drops each column's missing-value group
         AND (COUNT(DISTINCT CBD_ID) > 1 OR COUNT(DISTINCT CLIENT_ID) > 1 OR COUNT(DISTINCT CRD) > 1
              OR COUNT(DISTINCT NAME) > 1)) x
ORDER BY BY_COL, N_CBD + N_CLIENT + N_CRD + N_NAME DESC, BY_VALUE
LIMIT 2000;

--6. Is dist_ch a property of the firm?  First rows: for each ID column, how many of its values carry no dist_ch, one,
--or 2+.  Last rows: the CRDs split over 2+ cbd_ids, by whether the split follows dist_ch.
SELECT 'values by dist_ch count' AS PART, BY_COL AS WHAT, N_DIST_CH AS OUTCOME, COUNT(*) AS N, NULL AS N_CBD
FROM (SELECT CASE WHEN GROUPING(CBD_ID) = 0 THEN 'cbd_id' WHEN GROUPING(CLIENT_ID) = 0 THEN 'firm_client_id'
                  WHEN GROUPING(CRD) = 0 THEN 'firm_crd' ELSE 'broker_name' END AS BY_COL,
             CASE WHEN COUNT(DISTINCT DIST_CH) >= 2 THEN '2+ dist_ch' ELSE TO_CHAR(COUNT(DISTINCT DIST_CH)) || ' dist_ch' END AS N_DIST_CH
      FROM ssdb_integration.lr_strategy.tmp_fm
      GROUP BY GROUPING SETS ((CBD_ID), (CLIENT_ID), (CRD), (NAME))
      HAVING COALESCE(CBD_ID, CLIENT_ID, CRD, NAME) IS NOT NULL) x
GROUP BY BY_COL, N_DIST_CH
UNION ALL
SELECT 'CRDs split over 2+ cbd_ids', 'firm_crd',
       CASE WHEN MIN_CH = 0 THEN 'a cbd_id has no dist_ch'
            WHEN MAX_CH >= 2 THEN 'a cbd_id carries 2+ dist_ch'
            WHEN N_CH = N_CBD THEN 'each cbd_id its own dist_ch: the split follows channel'
            WHEN N_CH = 1 THEN 'every cbd_id the same dist_ch: the split is not channel'
            ELSE 'some cbd_ids share a dist_ch' END,
       COUNT(*), SUM(N_CBD)
FROM (SELECT CRD, COUNT(*) AS N_CBD, MIN(N_CH) AS MIN_CH, MAX(N_CH) AS MAX_CH, COUNT(DISTINCT CH) AS N_CH
      FROM (SELECT CRD, CBD_ID, COUNT(DISTINCT DIST_CH) AS N_CH, MIN(DIST_CH) AS CH
            FROM ssdb_integration.lr_strategy.tmp_fm WHERE CRD IS NOT NULL AND CBD_ID IS NOT NULL GROUP BY CRD, CBD_ID) c
      GROUP BY CRD HAVING COUNT(*) >= 2) s
GROUP BY 3
ORDER BY 1 DESC, 2, 3;
