use secondary roles all;

--NAME_XWALK: every person name of NAME_NORM (26_name_norm.sql: run it first) matched to the names of every other
--table x column of its SOURCE, so any two datasets join on name:
--  FROM <table A> a
--  JOIN NAME_XWALK x ON x.FROM_TABLE = '<A>' AND x.FROM_COLUMN = '<A column>' AND x.FROM_NAME = a.<A column>
--                   AND x.TO_TABLE = '<B>' AND x.TO_COLUMN = '<B column>' AND x.STATUS = 'matched'
--  JOIN <table B> b ON b.<B column> = x.TO_NAME
--One row per FROM name x TO table x column.  TO_NAME is the match (NULL: none); STATUS 'matched', 'review' (a
--candidate to confirm, or several: REVIEW says which) or 'none'; STEP how it was found; RULE which of 2+ candidates
--was taken and why; NAME_SCORE = JAROWINKLER_SIMILARITY of the two NAME_STD (0-100); COVER = share of the FROM
--name's ZIP_CODE x channel cells the TO name covers (NULL unless both columns have cells in statement 1).
--Steps, within SOURCE; the first step that finds a candidate decides:
--  0 manual     your pairs (statement 3)
--  1 same name  NAME_STD equal (last, first, middle initial, suffix)
--  2 same key   NAME_KEY equal (last, first)
--  3 nickname   last names equal, first names equal through the nickname list (statement 2)
--  4 initial    last names equal; one first name is the other's initial, or the other's middle name
--  5 hyphen     one last name is a part of the other's hyphenated one; first names equal through the list
--  6 spelling   JAROWINKLER_SIMILARITY >= 90 on the last names and >= 85 on the first names (as written or
--               through the list, the higher)
--  7 territory  no name candidate: each is the other's best by shared cells, COVER >= 0.8, runner-up < 0.5
--               (the rule of 21_name_match.sql)
--Steps 0-2 match on their own, unless both sides have cells and the territories disagree (COVER < 0.5).  Steps 3-6
--match only when the territories agree (COVER >= 0.8): name similarity is only a check (owner, 2026-10-21).
--Without cells on both sides they stay 'review' with the candidate filled in: confirm it in statement 3.  2+
--candidates at one step: the one with the same middle initial (steps 0-2), else the one with COVER >= 0.8, if exactly
--one; else 'review'.  A TO name matched by 2+ names of one column whose middle initials differ (two people) is
--'review' for all of them.  Names with no first name ('open', one word) take no part.
--Run All.  Statements 1-3 are temporary, NAME_XWALK (4) is kept, 5 = checks (MUST_BE_ZERO rows must be 0),
--6 = the review list: real names, keep at work.

--Statement 1.  The ZIP_CODE x channel cells a name covers: the union's territory holder and the territories tables.
--SRC_TABLE, SRC_COLUMN and SOURCE as in 26's input.  Both sides use the same channel labels: the CRBG union's
--updated_wholesaler2026 is crbg_territories' whslr_nm at the same zip and new_dist_channel = dist_ch (the owner's
--query); EQH's channel is taken to be the union's dist_ch (if 28's check shows otherwise, use channel_name, or the
--same constant on both sides to compare ZIP_CODEs alone).
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_name_geo AS
SELECT DISTINCT SRC_TABLE, SRC_COLUMN, SOURCE, RAW_NAME, LPAD(LEFT(TRIM(TO_CHAR(ZIP)), 5), 5, '0') AS ZIP_CODE, CHANNEL
FROM (
  SELECT 'data_withnewchannel_eqhv3' AS SRC_TABLE, 'updated_wholesaler2026' AS SRC_COLUMN, 'EQH' AS SOURCE,
         updated_wholesaler2026 AS RAW_NAME, zip_code AS ZIP, dist_ch AS CHANNEL
  FROM ssdb_integration.lr_strategy.data_withnewchannel_eqhv3
  UNION ALL SELECT 'data_withnewchannel_crbgwithiova', 'updated_wholesaler2026', 'CRBG', updated_wholesaler2026, zip_code, dist_ch
            FROM ssdb_integration.lr_strategy.data_withnewchannel_crbgwithiova
  UNION ALL SELECT 'eqh_territories', 'rvp', 'EQH', rvp, zip_code, channel FROM ssdb_integration.lr_strategy.eqh_territories
  UNION ALL SELECT 'crbg_territories', 'whslr_nm', 'CRBG', whslr_nm, zip, new_dist_channel
            FROM ssdb_integration.lr_strategy.crbg_territories
) x
WHERE RAW_NAME IS NOT NULL AND ZIP IS NOT NULL AND CHANNEL IS NOT NULL;

--Statement 2.  Nicknames: each NICK once, with the name it stands for.  Add lines as the review list shows them.
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_name_alias AS
SELECT NICK, FORMAL FROM (VALUES
  ('AL', 'ALBERT'), ('ALEX', 'ALEXANDER'), ('ANDY', 'ANDREW'), ('DREW', 'ANDREW'), ('TONY', 'ANTHONY'),
  ('BEN', 'BENJAMIN'), ('BRAD', 'BRADLEY'), ('CHUCK', 'CHARLES'), ('CHARLIE', 'CHARLES'), ('CHRIS', 'CHRISTOPHER'),
  ('DAN', 'DANIEL'), ('DANNY', 'DANIEL'), ('DAVE', 'DAVID'), ('DON', 'DONALD'), ('ED', 'EDWARD'), ('EDDIE', 'EDWARD'),
  ('FRED', 'FREDERICK'), ('GREG', 'GREGORY'), ('JAKE', 'JACOB'), ('JIM', 'JAMES'), ('JIMMY', 'JAMES'),
  ('JAMIE', 'JAMES'), ('JEFF', 'JEFFREY'), ('JERRY', 'GERALD'), ('JOE', 'JOSEPH'), ('JOEY', 'JOSEPH'),
  ('JACK', 'JOHN'), ('JOHNNY', 'JOHN'), ('JON', 'JONATHAN'), ('KEN', 'KENNETH'), ('KENNY', 'KENNETH'),
  ('LARRY', 'LAWRENCE'), ('MATT', 'MATTHEW'), ('MIKE', 'MICHAEL'), ('MICK', 'MICHAEL'), ('NATE', 'NATHAN'),
  ('NICK', 'NICHOLAS'), ('PAT', 'PATRICK'), ('PETE', 'PETER'), ('PHIL', 'PHILIP'), ('RAY', 'RAYMOND'),
  ('RICK', 'RICHARD'), ('RICH', 'RICHARD'), ('DICK', 'RICHARD'), ('ROB', 'ROBERT'), ('BOB', 'ROBERT'),
  ('BOBBY', 'ROBERT'), ('ROBBIE', 'ROBERT'), ('RON', 'RONALD'), ('SAM', 'SAMUEL'), ('STEVE', 'STEVEN'),
  ('STEPHEN', 'STEVEN'), ('TED', 'THEODORE'), ('TOM', 'THOMAS'), ('TOMMY', 'THOMAS'), ('TIM', 'TIMOTHY'),
  ('BILL', 'WILLIAM'), ('BILLY', 'WILLIAM'), ('WILL', 'WILLIAM'), ('WILLIE', 'WILLIAM'), ('ZACH', 'ZACHARY'),
  ('ABBY', 'ABIGAIL'), ('BETH', 'ELIZABETH'), ('LIZ', 'ELIZABETH'), ('BETSY', 'ELIZABETH'), ('CATHY', 'CATHERINE'),
  ('KATHY', 'KATHERINE'), ('KATE', 'KATHERINE'), ('KATIE', 'KATHERINE'), ('CINDY', 'CYNTHIA'), ('DEB', 'DEBORAH'),
  ('DEBBIE', 'DEBORAH'), ('JEN', 'JENNIFER'), ('JENNY', 'JENNIFER'), ('JESS', 'JESSICA'), ('JUDY', 'JUDITH'),
  ('MAGGIE', 'MARGARET'), ('MEG', 'MARGARET'), ('PEGGY', 'MARGARET'), ('PAM', 'PAMELA'), ('BECKY', 'REBECCA'),
  ('SUE', 'SUSAN'), ('SUSIE', 'SUSAN'), ('VICKY', 'VICTORIA'), ('MANDY', 'AMANDA'), ('CHRISSY', 'CHRISTINE')
) v(NICK, FORMAL);

--Statement 3.  Your pairs: two raw names of one SOURCE that are the same person, both ways, in any columns; they
--win over every step.  One line per pair, e.g. ('<SOURCE>', '<name as in one table>', '<name as in the other>');
--as it stands, ('', '', '') lists none.
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_name_manual AS
SELECT SOURCE, NAME_A, NAME_B FROM (VALUES ('', '', '')) v(SOURCE, NAME_A, NAME_B) WHERE NAME_A <> '';

--Statement 4.  NAME_XWALK, the table kept.
CREATE OR REPLACE TABLE ssdb_integration.lr_strategy.NAME_XWALK AS
WITH
n AS (   -- the person names (a first name); FIRST_CANON = the first name through the nickname list
  SELECT x.SRC_TABLE, x.SRC_COLUMN, x.SOURCE, x.RAW_NAME, x.LAST_NAME, x.FIRST_NAME, x.MIDDLE_NAME, x.MIDDLE_INITIAL,
         x.NAME_STD, x.NAME_KEY, COALESCE(a.FORMAL, x.FIRST_NAME) AS FIRST_CANON
  FROM ssdb_integration.lr_strategy.NAME_NORM x
  LEFT JOIN ssdb_integration.lr_strategy.tmp_name_alias a ON a.NICK = x.FIRST_NAME
  WHERE x.FIRST_NAME IS NOT NULL),
m AS (SELECT * FROM ssdb_integration.lr_strategy.tmp_name_manual),
g AS (SELECT * FROM ssdb_integration.lr_strategy.tmp_name_geo),
gcol AS (SELECT DISTINCT SOURCE, SRC_TABLE, SRC_COLUMN FROM g),
gc AS (SELECT SOURCE, SRC_TABLE, SRC_COLUMN, RAW_NAME, COUNT(*) AS CELLS FROM g GROUP BY SOURCE, SRC_TABLE, SRC_COLUMN, RAW_NAME),
gp AS (   -- cells two names share, and the share of the FROM name's cells
  SELECT a.SOURCE, a.SRC_TABLE AS FROM_TABLE, a.SRC_COLUMN AS FROM_COLUMN, a.RAW_NAME AS FROM_NAME,
         b.SRC_TABLE AS TO_TABLE, b.SRC_COLUMN AS TO_COLUMN, b.RAW_NAME AS TO_NAME, COUNT(*) / MAX(gc.CELLS) AS COVER
  FROM g a
  JOIN g b ON b.SOURCE = a.SOURCE AND b.ZIP_CODE = a.ZIP_CODE AND b.CHANNEL = a.CHANNEL
          AND (b.SRC_TABLE <> a.SRC_TABLE OR b.SRC_COLUMN <> a.SRC_COLUMN)
  JOIN gc ON gc.SOURCE = a.SOURCE AND gc.SRC_TABLE = a.SRC_TABLE AND gc.SRC_COLUMN = a.SRC_COLUMN AND gc.RAW_NAME = a.RAW_NAME
  GROUP BY a.SOURCE, a.SRC_TABLE, a.SRC_COLUMN, a.RAW_NAME, b.SRC_TABLE, b.SRC_COLUMN, b.RAW_NAME),
p AS (   -- every pair of person names of one SOURCE in different columns, with the first step it passes
  SELECT a.SOURCE, a.SRC_TABLE AS FROM_TABLE, a.SRC_COLUMN AS FROM_COLUMN, a.RAW_NAME AS FROM_NAME,
         b.SRC_TABLE AS TO_TABLE, b.SRC_COLUMN AS TO_COLUMN, b.RAW_NAME AS TO_NAME,
         COALESCE(a.MIDDLE_INITIAL = b.MIDDLE_INITIAL, FALSE) AS SAME_MI, a.NAME_STD AS FROM_STD, b.NAME_STD AS TO_STD,
         CASE WHEN m.NAME_A IS NOT NULL THEN 0
              WHEN a.NAME_STD = b.NAME_STD THEN 1
              WHEN a.NAME_KEY = b.NAME_KEY THEN 2
              WHEN a.LAST_NAME = b.LAST_NAME AND a.FIRST_CANON = b.FIRST_CANON THEN 3
              WHEN a.LAST_NAME = b.LAST_NAME
               AND (a.FIRST_NAME = LEFT(b.FIRST_NAME, 1) OR b.FIRST_NAME = LEFT(a.FIRST_NAME, 1)
                    OR a.FIRST_NAME = b.MIDDLE_NAME OR b.FIRST_NAME = a.MIDDLE_NAME) THEN 4
              WHEN a.FIRST_CANON = b.FIRST_CANON
               AND (('-' || a.LAST_NAME || '-') LIKE ('%-' || b.LAST_NAME || '-%')
                    OR ('-' || b.LAST_NAME || '-') LIKE ('%-' || a.LAST_NAME || '-%')) THEN 5
              WHEN JAROWINKLER_SIMILARITY(a.LAST_NAME, b.LAST_NAME) >= 90
               AND GREATEST(JAROWINKLER_SIMILARITY(a.FIRST_NAME, b.FIRST_NAME),
                            JAROWINKLER_SIMILARITY(a.FIRST_CANON, b.FIRST_CANON)) >= 85 THEN 6 END AS STEP
  FROM n a
  JOIN n b ON b.SOURCE = a.SOURCE AND (b.SRC_TABLE <> a.SRC_TABLE OR b.SRC_COLUMN <> a.SRC_COLUMN)
  LEFT JOIN m ON m.SOURCE = a.SOURCE AND ((m.NAME_A = a.RAW_NAME AND m.NAME_B = b.RAW_NAME)
                                        OR (m.NAME_A = b.RAW_NAME AND m.NAME_B = a.RAW_NAME))),
c AS (   -- the candidates of the first step that finds any, per FROM name x TO column, with their cover
  SELECT p.*, fg.SOURCE IS NOT NULL AND tg.SOURCE IS NOT NULL AS GEO,
         CASE WHEN fg.SOURCE IS NOT NULL AND tg.SOURCE IS NOT NULL THEN COALESCE(gp.COVER, 0) END AS COVER
  FROM p
  LEFT JOIN gcol fg ON fg.SOURCE = p.SOURCE AND fg.SRC_TABLE = p.FROM_TABLE AND fg.SRC_COLUMN = p.FROM_COLUMN
  LEFT JOIN gcol tg ON tg.SOURCE = p.SOURCE AND tg.SRC_TABLE = p.TO_TABLE AND tg.SRC_COLUMN = p.TO_COLUMN
  LEFT JOIN gp ON gp.SOURCE = p.SOURCE AND gp.FROM_TABLE = p.FROM_TABLE AND gp.FROM_COLUMN = p.FROM_COLUMN
              AND gp.FROM_NAME = p.FROM_NAME AND gp.TO_TABLE = p.TO_TABLE AND gp.TO_COLUMN = p.TO_COLUMN
              AND gp.TO_NAME = p.TO_NAME
  WHERE p.STEP IS NOT NULL
  QUALIFY p.STEP = MIN(p.STEP) OVER (PARTITION BY p.SOURCE, p.FROM_TABLE, p.FROM_COLUMN, p.FROM_NAME, p.TO_TABLE, p.TO_COLUMN)),
d AS (
  SELECT c.*,
         COUNT(*) OVER (PARTITION BY SOURCE, FROM_TABLE, FROM_COLUMN, FROM_NAME, TO_TABLE, TO_COLUMN) AS N_CAND,
         SUM(CASE WHEN SAME_MI THEN 1 ELSE 0 END)
           OVER (PARTITION BY SOURCE, FROM_TABLE, FROM_COLUMN, FROM_NAME, TO_TABLE, TO_COLUMN) AS N_MI,
         SUM(CASE WHEN COVER >= 0.8 THEN 1 ELSE 0 END)
           OVER (PARTITION BY SOURCE, FROM_TABLE, FROM_COLUMN, FROM_NAME, TO_TABLE, TO_COLUMN) AS N_GEO
  FROM c),
e AS (   -- PICKED: the only candidate, else the one with the same middle initial (steps 0-2), else the one whose
         -- territories agree
  SELECT d.*,
         CASE WHEN N_CAND = 1 THEN NULL
              WHEN STEP <= 2 AND N_MI = 1 AND SAME_MI THEN 'the one with the same middle initial'
              WHEN NOT (STEP <= 2 AND N_MI = 1) AND N_GEO = 1 AND COVER >= 0.8 THEN 'the one whose territories agree' END AS RULE,
         N_CAND = 1 OR (STEP <= 2 AND N_MI = 1 AND SAME_MI)
           OR (NOT (STEP <= 2 AND N_MI = 1) AND N_GEO = 1 AND COALESCE(COVER >= 0.8, FALSE)) AS PICKED
  FROM d),
f AS (SELECT e.*, SUM(CASE WHEN PICKED THEN 1 ELSE 0 END)
                    OVER (PARTITION BY SOURCE, FROM_TABLE, FROM_COLUMN, FROM_NAME, TO_TABLE, TO_COLUMN) AS N_PICKED FROM e),
t7 AS (  -- step 7: by territory alone, where no step found a name candidate
  SELECT gp.*,
         ROW_NUMBER() OVER (PARTITION BY SOURCE, FROM_TABLE, FROM_COLUMN, FROM_NAME, TO_TABLE, TO_COLUMN
                            ORDER BY COVER DESC, TO_NAME) AS RK_F,
         ROW_NUMBER() OVER (PARTITION BY SOURCE, TO_TABLE, TO_COLUMN, TO_NAME, FROM_TABLE, FROM_COLUMN
                            ORDER BY COVER DESC, FROM_NAME) AS RK_T
  FROM gp),
t7b AS (
  SELECT t7.*, MAX(CASE WHEN RK_F = 2 THEN COVER END)
                 OVER (PARTITION BY SOURCE, FROM_TABLE, FROM_COLUMN, FROM_NAME, TO_TABLE, TO_COLUMN) AS RUNNER_UP
  FROM t7),
res AS (
  SELECT SOURCE, FROM_TABLE, FROM_COLUMN, FROM_NAME, TO_TABLE, TO_COLUMN, TO_NAME, STEP, RULE, N_CAND, FROM_STD, TO_STD, COVER,
         CASE WHEN STEP = 0 OR (STEP <= 2 AND NOT (GEO AND COVER < 0.5)) OR COVER >= 0.8 THEN 'matched' ELSE 'review' END
           AS STATUS,
         CASE WHEN STEP = 0 OR (STEP <= 2 AND NOT (GEO AND COVER < 0.5)) OR COVER >= 0.8 THEN NULL
              WHEN STEP <= 2 THEN 'same name, territories do not agree'
              WHEN GEO THEN 'name candidate, territories do not agree'
              ELSE 'name candidate, no territory cells to check it' END AS REVIEW
  FROM f WHERE PICKED
  UNION ALL   -- 2+ candidates and no rule picks one
  SELECT SOURCE, FROM_TABLE, FROM_COLUMN, FROM_NAME, TO_TABLE, TO_COLUMN, NULL, MIN(STEP), NULL, MIN(N_CAND), MIN(FROM_STD),
         NULL, NULL, 'review', MIN(N_CAND) || ' candidates at one step, none picked'
  FROM f WHERE N_PICKED = 0
  GROUP BY SOURCE, FROM_TABLE, FROM_COLUMN, FROM_NAME, TO_TABLE, TO_COLUMN
  UNION ALL
  SELECT t.SOURCE, t.FROM_TABLE, t.FROM_COLUMN, t.FROM_NAME, t.TO_TABLE, t.TO_COLUMN, t.TO_NAME, 7, NULL, NULL, NULL, NULL,
         t.COVER, 'matched', NULL
  FROM t7b t
  JOIN n ON n.SOURCE = t.SOURCE AND n.SRC_TABLE = t.FROM_TABLE AND n.SRC_COLUMN = t.FROM_COLUMN AND n.RAW_NAME = t.FROM_NAME
  JOIN n n2 ON n2.SOURCE = t.SOURCE AND n2.SRC_TABLE = t.TO_TABLE AND n2.SRC_COLUMN = t.TO_COLUMN AND n2.RAW_NAME = t.TO_NAME
  WHERE t.RK_F = 1 AND t.RK_T = 1 AND t.COVER >= 0.8 AND COALESCE(t.RUNNER_UP, 0) < 0.5
    AND NOT EXISTS (SELECT 1 FROM c WHERE c.SOURCE = t.SOURCE AND c.FROM_TABLE = t.FROM_TABLE AND c.FROM_COLUMN = t.FROM_COLUMN
                    AND c.FROM_NAME = t.FROM_NAME AND c.TO_TABLE = t.TO_TABLE AND c.TO_COLUMN = t.TO_COLUMN)),
cl AS (  -- TO names matched by 2+ names of one FROM column whose middle initials differ: two people, one TO name
  SELECT r.SOURCE, r.FROM_TABLE, r.FROM_COLUMN, r.TO_TABLE, r.TO_COLUMN, r.TO_NAME
  FROM res r
  JOIN n ON n.SOURCE = r.SOURCE AND n.SRC_TABLE = r.FROM_TABLE AND n.SRC_COLUMN = r.FROM_COLUMN AND n.RAW_NAME = r.FROM_NAME
  WHERE r.STATUS = 'matched' AND r.STEP > 0
  GROUP BY r.SOURCE, r.FROM_TABLE, r.FROM_COLUMN, r.TO_TABLE, r.TO_COLUMN, r.TO_NAME
  HAVING COUNT(DISTINCT n.MIDDLE_INITIAL) > 1),
k AS (   -- every person name x every other column of its SOURCE
  SELECT n.SOURCE, n.SRC_TABLE AS FROM_TABLE, n.SRC_COLUMN AS FROM_COLUMN, n.RAW_NAME AS FROM_NAME,
         o.SRC_TABLE AS TO_TABLE, o.SRC_COLUMN AS TO_COLUMN
  FROM n JOIN (SELECT DISTINCT SOURCE, SRC_TABLE, SRC_COLUMN FROM n) o
    ON o.SOURCE = n.SOURCE AND (o.SRC_TABLE <> n.SRC_TABLE OR o.SRC_COLUMN <> n.SRC_COLUMN))
SELECT k.SOURCE, k.FROM_TABLE, k.FROM_COLUMN, k.FROM_NAME, k.TO_TABLE, k.TO_COLUMN, r.TO_NAME,
       CASE WHEN cl.TO_NAME IS NOT NULL THEN 'review' ELSE COALESCE(r.STATUS, 'none') END AS STATUS,
       CASE r.STEP WHEN 0 THEN '0 manual' WHEN 1 THEN '1 same name' WHEN 2 THEN '2 same key' WHEN 3 THEN '3 nickname'
                   WHEN 4 THEN '4 initial' WHEN 5 THEN '5 hyphen' WHEN 6 THEN '6 spelling' WHEN 7 THEN '7 territory' END AS STEP,
       r.RULE, r.N_CAND AS N_CANDIDATES,
       CASE WHEN r.TO_STD IS NOT NULL THEN JAROWINKLER_SIMILARITY(r.FROM_STD, r.TO_STD) END AS NAME_SCORE,
       ROUND(r.COVER, 3) AS COVER,
       CASE WHEN cl.TO_NAME IS NOT NULL THEN 'TO name also matched by another person of this column (middle initials differ)'
            ELSE r.REVIEW END AS REVIEW
FROM k
LEFT JOIN res r ON r.SOURCE = k.SOURCE AND r.FROM_TABLE = k.FROM_TABLE AND r.FROM_COLUMN = k.FROM_COLUMN
               AND r.FROM_NAME = k.FROM_NAME AND r.TO_TABLE = k.TO_TABLE AND r.TO_COLUMN = k.TO_COLUMN
LEFT JOIN cl ON cl.SOURCE = r.SOURCE AND cl.FROM_TABLE = r.FROM_TABLE AND cl.FROM_COLUMN = r.FROM_COLUMN
            AND cl.TO_TABLE = r.TO_TABLE AND cl.TO_COLUMN = r.TO_COLUMN AND cl.TO_NAME = r.TO_NAME AND r.STATUS = 'matched';

--Statement 5.  Checks: every MUST_BE_ZERO = TRUE row must be 0.  The match rates read FROM -> TO.
WITH
x AS (SELECT * FROM ssdb_integration.lr_strategy.NAME_XWALK),
nn AS (SELECT * FROM ssdb_integration.lr_strategy.NAME_NORM),
xr AS (SELECT x.*, nn.N_ROWS FROM x JOIN nn ON nn.SOURCE = x.SOURCE AND nn.SRC_TABLE = x.FROM_TABLE
                                          AND nn.SRC_COLUMN = x.FROM_COLUMN AND nn.RAW_NAME = x.FROM_NAME)
SELECT 'FROM name x TO column on 2+ rows' AS CHECK_NAME,
       (SELECT COUNT(*) FROM (SELECT 1 FROM x GROUP BY SOURCE, FROM_TABLE, FROM_COLUMN, FROM_NAME, TO_TABLE, TO_COLUMN
                              HAVING COUNT(*) > 1) d) AS VALUE, TRUE AS MUST_BE_ZERO
UNION ALL SELECT 'statement 1 names not in NAME_NORM (use the same SRC_TABLE, SRC_COLUMN, SOURCE and name expression as 26)',
       (SELECT COUNT(*) FROM (SELECT DISTINCT SOURCE, SRC_TABLE, SRC_COLUMN, RAW_NAME FROM ssdb_integration.lr_strategy.tmp_name_geo) g
        WHERE NOT EXISTS (SELECT 1 FROM nn WHERE nn.SOURCE = g.SOURCE AND nn.SRC_TABLE = g.SRC_TABLE
                          AND nn.SRC_COLUMN = g.SRC_COLUMN AND nn.RAW_NAME = g.RAW_NAME)), TRUE
UNION ALL SELECT 'manual pairs with a name that is not a person name of that SOURCE in NAME_NORM',
       (SELECT COUNT(*) FROM ssdb_integration.lr_strategy.tmp_name_manual m
        WHERE NOT EXISTS (SELECT 1 FROM nn WHERE nn.SOURCE = m.SOURCE AND nn.RAW_NAME = m.NAME_A AND nn.FIRST_NAME IS NOT NULL)
           OR NOT EXISTS (SELECT 1 FROM nn WHERE nn.SOURCE = m.SOURCE AND nn.RAW_NAME = m.NAME_B AND nn.FIRST_NAME IS NOT NULL)), TRUE
UNION ALL SELECT 'nicknames listed twice',
       (SELECT COUNT(*) FROM (SELECT NICK FROM ssdb_integration.lr_strategy.tmp_name_alias GROUP BY NICK HAVING COUNT(*) > 1) d), TRUE
UNION ALL SELECT 'names that take no part (no first name), ' || SRC_TABLE || '.' || SRC_COLUMN || ' ' || SOURCE, COUNT(*), FALSE
       FROM nn WHERE FIRST_NAME IS NULL GROUP BY SRC_TABLE, SRC_COLUMN, SOURCE
UNION ALL SELECT SOURCE || ' ' || FROM_TABLE || '.' || FROM_COLUMN || ' -> ' || TO_TABLE || '.' || TO_COLUMN || ': % of names matched',
       ROUND(100 * SUM(CASE WHEN STATUS = 'matched' THEN 1 ELSE 0 END) / COUNT(*), 1), FALSE
       FROM xr GROUP BY SOURCE, FROM_TABLE, FROM_COLUMN, TO_TABLE, TO_COLUMN
UNION ALL SELECT SOURCE || ' ' || FROM_TABLE || '.' || FROM_COLUMN || ' -> ' || TO_TABLE || '.' || TO_COLUMN || ': % of rows matched',
       ROUND(100 * SUM(CASE WHEN STATUS = 'matched' THEN N_ROWS ELSE 0 END) / SUM(N_ROWS), 1), FALSE
       FROM xr GROUP BY SOURCE, FROM_TABLE, FROM_COLUMN, TO_TABLE, TO_COLUMN
UNION ALL SELECT SOURCE || ' ' || FROM_TABLE || '.' || FROM_COLUMN || ' -> ' || TO_TABLE || '.' || TO_COLUMN || ': names for review',
       SUM(CASE WHEN STATUS = 'review' THEN 1 ELSE 0 END), FALSE
       FROM xr GROUP BY SOURCE, FROM_TABLE, FROM_COLUMN, TO_TABLE, TO_COLUMN
UNION ALL SELECT 'matches by STEP: ' || STEP, COUNT(*), FALSE FROM x WHERE STATUS = 'matched' GROUP BY STEP
UNION ALL SELECT 'TO names matched by 2+ names of one FROM column (two spellings of one person, or a wrong match)',
       (SELECT COUNT(*) FROM (SELECT 1 FROM x WHERE STATUS = 'matched'
                              GROUP BY SOURCE, FROM_TABLE, FROM_COLUMN, TO_TABLE, TO_COLUMN, TO_NAME HAVING COUNT(*) > 1) d), FALSE
ORDER BY 3 DESC, 1;

--Statement 6.  The review list: real names, keep at work.  Confirm a candidate by adding the pair to statement 3,
--or a nickname to statement 2.
SELECT x.SOURCE, x.FROM_TABLE, x.FROM_COLUMN, x.FROM_NAME, x.TO_TABLE, x.TO_COLUMN, x.TO_NAME, x.STEP, x.N_CANDIDATES,
       x.NAME_SCORE, x.COVER, x.REVIEW, nn.N_ROWS
FROM ssdb_integration.lr_strategy.NAME_XWALK x
JOIN ssdb_integration.lr_strategy.NAME_NORM nn ON nn.SOURCE = x.SOURCE AND nn.SRC_TABLE = x.FROM_TABLE
                                              AND nn.SRC_COLUMN = x.FROM_COLUMN AND nn.RAW_NAME = x.FROM_NAME
WHERE x.STATUS = 'review'
ORDER BY x.SOURCE, x.FROM_TABLE, x.FROM_COLUMN, x.TO_TABLE, x.TO_COLUMN, nn.N_ROWS DESC, x.FROM_NAME;
