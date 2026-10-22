-- NAME_MATCH: a crosswalk from the union's territory-wholesaler names to the territories table's names, one
-- row per SOURCE x union name.  It answers: which territories name is this union person?  It replaces matching
-- by edit distance in successive passes: the pairing comes from the ZIP_CODE x DIST_CH each name covers; the
-- name similarity is only a check beside it.
-- Seller names are not matched here: SALES_WHOLESALER_CLEAN_NAME and TERR_WHOLESALER_CLEAN_NAME are the same
-- dataset and format.
-- Names never leave work.  Statements 1 and 3 hold real names; only the crosswalk with coded IDs does
-- (CURRENT_ID and CLEAN_ID coded W..., names M..., as in 20_synthetic_tables.sql).
-- Territories are limited to the (SOURCE, CHANNEL) pairs whose CHANNEL is a DIST_CH of that SOURCE in the
-- union; the other territory channels are out of scope (DATASET_LOG.md, Settled).
-- Run statement 1, then 2 (checks: every MUST_BE_ZERO row must be 0), then 3 (the list to read by hand).

-- Statement 1.  The table.
CREATE OR REPLACE TABLE ssdb_integration.lr_strategy.NAME_MATCH AS
WITH
base AS (            -- the two name columns to confirm at work: union TERR_WHOLESALER_CLEAN_NAME, territories NAME
  SELECT 'U' AS SIDE, SOURCE, TERR_WHOLESALER_CLEAN_NAME AS PERSON, ZIP_CODE, DIST_CH AS CH,
         TERRITORY_WHOLESALER_TERRITORY_ID AS ID
  FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys
  UNION ALL
  SELECT 'T', SOURCE, NAME, ZIP_CODE, CHANNEL, CLEAN_ID
  FROM ssdb_integration.lr_strategy.territories),
scope AS (           -- (SOURCE, channel) pairs in play: DIST_CH values of the union
  SELECT DISTINCT SOURCE, CH FROM base WHERE SIDE = 'U' AND CH IS NOT NULL),
t_in AS (
  SELECT b.* FROM base b JOIN scope s ON s.SOURCE = b.SOURCE AND s.CH = b.CH
  WHERE b.SIDE = 'T' AND b.PERSON IS NOT NULL),
u_names AS (         -- the ID the union already carries for the name
  SELECT SOURCE, PERSON, MAX(ID) AS CURRENT_ID FROM base WHERE SIDE = 'U' AND PERSON IS NOT NULL GROUP BY SOURCE, PERSON),
t_names AS (
  SELECT SOURCE, PERSON, MAX(ID) AS CLEAN_ID FROM t_in GROUP BY SOURCE, PERSON),
ug AS (              -- U: the ZIP_CODE x DIST_CH a union person covers as territory wholesaler
  SELECT DISTINCT SOURCE, PERSON, ZIP_CODE, CH FROM base
  WHERE SIDE = 'U' AND PERSON IS NOT NULL AND ZIP_CODE IS NOT NULL AND CH IS NOT NULL),
tg AS (              -- T: the ZIP_CODE x CHANNEL a territories name covers
  SELECT DISTINCT SOURCE, PERSON, ZIP_CODE, CH FROM t_in WHERE ZIP_CODE IS NOT NULL),
un AS (SELECT SOURCE, PERSON, COUNT(*) AS N FROM ug GROUP BY SOURCE, PERSON),
tn AS (SELECT SOURCE, PERSON, COUNT(*) AS N FROM tg GROUP BY SOURCE, PERSON),
pair AS (
  SELECT ug.SOURCE, ug.PERSON AS UNAME, tg.PERSON AS TNAME, COUNT(*) AS SHARED
  FROM ug JOIN tg ON tg.SOURCE = ug.SOURCE AND tg.ZIP_CODE = ug.ZIP_CODE AND tg.CH = ug.CH
  GROUP BY ug.SOURCE, ug.PERSON, tg.PERSON),
ranked AS (
  SELECT p.SOURCE, p.UNAME, p.TNAME, p.SHARED,
         p.SHARED / un.N AS COVER_UNION,
         p.SHARED / tn.N AS COVER_TERR,
         ROW_NUMBER() OVER (PARTITION BY p.SOURCE, p.UNAME ORDER BY p.SHARED DESC, p.TNAME) AS RK_U,
         ROW_NUMBER() OVER (PARTITION BY p.SOURCE, p.TNAME ORDER BY p.SHARED DESC, p.UNAME) AS RK_T
  FROM pair p
  JOIN un ON un.SOURCE = p.SOURCE AND un.PERSON = p.UNAME
  JOIN tn ON tn.SOURCE = p.SOURCE AND tn.PERSON = p.TNAME),
swapped AS (         -- "LAST, FIRST ..." -> "FIRST ... LAST"
  SELECT PERSON,
         CASE WHEN UPPER(PERSON) LIKE '%,%'
              THEN TRIM(REGEXP_REPLACE(UPPER(PERSON), '^[^,]*,', '')) || ' ' || TRIM(SPLIT_PART(UPPER(PERSON), ',', 1))
              ELSE UPPER(PERSON) END AS S
  FROM (SELECT PERSON FROM u_names UNION SELECT PERSON FROM t_names) x),
norm AS (            -- strip punctuation, drop suffix and designation tokens, collapse spaces
  SELECT PERSON,       -- spaces doubled so that adjacent suffix tokens each keep their own delimiters
         TRIM(REGEXP_REPLACE(
                REGEXP_REPLACE(' ' || REPLACE(REGEXP_REPLACE(S, '[^A-Z0-9 ]', ''), ' ', '  ') || ' ',
                               ' (JR|SR|II|III|IV|CFP|CHFC|CLU|CIMA|CFA|RICP|MBA) ', ' '),
                ' +', ' ')) AS NORM
  FROM swapped),
m AS (
  SELECT u.SOURCE, u.PERSON AS UNION_NAME, u.CURRENT_ID,
         r.TNAME AS TERR_NAME, t.CLEAN_ID,
         COALESCE(r.SHARED, 0) AS SHARED, r.COVER_UNION, r.COVER_TERR,
         r2.COVER_UNION AS RUNNER_UP_COVER,
         COALESCE(r.RK_T = 1, FALSE) AS MUTUAL
  FROM u_names u
  LEFT JOIN ranked r  ON r.SOURCE = u.SOURCE AND r.UNAME = u.PERSON AND r.RK_U = 1
  LEFT JOIN ranked r2 ON r2.SOURCE = u.SOURCE AND r2.UNAME = u.PERSON AND r2.RK_U = 2
  LEFT JOIN t_names t ON t.SOURCE = u.SOURCE AND t.PERSON = r.TNAME)
SELECT m.SOURCE, m.UNION_NAME, nu.NORM AS UNION_NAME_NORM, m.CURRENT_ID,
       m.TERR_NAME, nt.NORM AS TERR_NAME_NORM, m.CLEAN_ID,
       m.SHARED, ROUND(m.COVER_UNION, 3) AS COVER_UNION, ROUND(m.COVER_TERR, 3) AS COVER_TERR,
       ROUND(m.RUNNER_UP_COVER, 3) AS RUNNER_UP_COVER, m.MUTUAL,
       JAROWINKLER_SIMILARITY(nu.NORM, nt.NORM) AS NAME_SCORE,
       REGEXP_REPLACE(nu.NORM, '^.* ', '') = REGEXP_REPLACE(nt.NORM, '^.* ', '') AS LAST_NAME_EQUAL,
       -- ponytail: 0.8 guards against a name that covers only part of its own ZIP_CODE x DIST_CH (a partial or
       -- wrong match); 0.5 guards against a runner-up that is nearly as good (one person split over two names).
       CASE WHEN m.MUTUAL AND m.COVER_UNION >= 0.8 AND COALESCE(m.RUNNER_UP_COVER, 0) < 0.5
            THEN 'geography' ELSE 'review' END AS METHOD,
       CASE WHEN m.CLEAN_ID IS NULL THEN NULL ELSE m.CLEAN_ID = m.CURRENT_ID END AS AGREES_WITH_CURRENT
FROM m
JOIN norm nu ON nu.PERSON = m.UNION_NAME
LEFT JOIN norm nt ON nt.PERSON = m.TERR_NAME;

-- Statement 2.  Checks.
SELECT 'NAME_MATCH keys appearing twice' AS CHECK_NAME,
       (SELECT COUNT(*) FROM (SELECT SOURCE, UNION_NAME FROM ssdb_integration.lr_strategy.NAME_MATCH
                              GROUP BY SOURCE, UNION_NAME HAVING COUNT(*) > 1) x) AS VALUE, TRUE AS MUST_BE_ZERO
UNION ALL SELECT 'union territory-wholesaler names missing from NAME_MATCH',
       (SELECT COUNT(*) FROM (SELECT DISTINCT SOURCE, TERR_WHOLESALER_CLEAN_NAME AS UNION_NAME   -- same column as statement 1
                              FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys
                              WHERE TERR_WHOLESALER_CLEAN_NAME IS NOT NULL) u
        WHERE NOT EXISTS (SELECT 1 FROM ssdb_integration.lr_strategy.NAME_MATCH n
                          WHERE n.SOURCE = u.SOURCE AND n.UNION_NAME = u.UNION_NAME)), TRUE
UNION ALL SELECT 'rows with METHOD ' || METHOD, COUNT(*), FALSE
       FROM ssdb_integration.lr_strategy.NAME_MATCH GROUP BY METHOD
UNION ALL SELECT 'geography rows where AGREES_WITH_CURRENT is false',
       (SELECT COUNT(*) FROM ssdb_integration.lr_strategy.NAME_MATCH WHERE METHOD = 'geography' AND NOT AGREES_WITH_CURRENT), FALSE
UNION ALL SELECT 'rows whose matched CLEAN_ID is NULL',
       (SELECT COUNT(*) FROM ssdb_integration.lr_strategy.NAME_MATCH WHERE CLEAN_ID IS NULL), FALSE
UNION ALL SELECT 'territories names matched by 2+ union names',
       (SELECT COUNT(*) FROM (SELECT SOURCE, TERR_NAME FROM ssdb_integration.lr_strategy.NAME_MATCH
                              WHERE TERR_NAME IS NOT NULL GROUP BY SOURCE, TERR_NAME HAVING COUNT(*) > 1) x), FALSE
ORDER BY MUST_BE_ZERO DESC, CHECK_NAME;

-- Statement 3.  The review list: every 'review' row, every row that disagrees with the ID the union carries,
-- every row whose matched name has no CLEAN_ID.  Real names: keep at work.
SELECT *
FROM ssdb_integration.lr_strategy.NAME_MATCH
WHERE METHOD = 'review' OR AGREES_WITH_CURRENT = FALSE OR CLEAN_ID IS NULL
ORDER BY SOURCE, COVER_UNION;
