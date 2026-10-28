use secondary roles all;

--NAME_KEY: one CLEAN_ID and CLEAN_NAME per wholesaler for every name in the two union tables, the two territories
--tables and the two address tables, so they join on CLEAN_ID.  One file: Run All.  NAME_KEY is the one table kept.
--   1  tmp_name_manual  your pairs: two names that are one person (edit)
--   2  tmp_name_alias   nicknames (edit)
--   3  tmp_name_norm    every name split into last, first, middle, suffix
--   4  tmp_name_xwalk   every name matched to the names of each other column of its firm
--   5  NAME_KEY         one ID per wholesaler
--   6  checks           every MUST_BE_ZERO = TRUE row must be 0
--   7  review list      names with no ID and pairs to confirm (real names: keep at work)
--
--NAME_KEY has one row per SRC_TABLE x SRC_COLUMN x RAW_NAME (the name exactly as written in that table):
--  CLEAN_ID    SOURCE_LAST_FIRST_M_SUFFIX, e.g. CRBG_DOE_JANE_Q; NULL when REVIEW says why
--  CLEAN_NAME  "LAST, FIRST M SUFFIX" as the territories table spells the person, else the union holder column, the
--              seller column, the address table
--
--Joining: give each table its CLEAN_ID through its own name column, then join on CLEAN_ID.  Territories also on ZIP
--and channel (a wholesaler has a row per ZIP x channel); addresses on CLEAN_ID alone.  CRBG:
--  SELECT u.*, h.CLEAN_ID AS HOLDER_ID, s.CLEAN_ID AS SELLER_ID, t.whslr_id, ha.city AS HOLDER_CITY
--  FROM ssdb_integration.lr_strategy.data_withnewchannel_crbgwithiova u
--  LEFT JOIN ssdb_integration.lr_strategy.NAME_KEY h ON h.SRC_TABLE = 'data_withnewchannel_crbgwithiova'
--        AND h.SRC_COLUMN = 'updated_wholesaler2026' AND h.RAW_NAME = u.updated_wholesaler2026
--  LEFT JOIN ssdb_integration.lr_strategy.NAME_KEY s ON s.SRC_TABLE = 'data_withnewchannel_crbgwithiova'
--        AND s.SRC_COLUMN = 'wholesaler_name' AND s.RAW_NAME = u.wholesaler_name
--  LEFT JOIN (SELECT x.*, k.CLEAN_ID FROM ssdb_integration.lr_strategy.crbg_territories x
--             JOIN ssdb_integration.lr_strategy.NAME_KEY k ON k.SRC_TABLE = 'crbg_territories' AND k.RAW_NAME = x.whslr_nm) t
--        ON t.CLEAN_ID = h.CLEAN_ID AND t.zip = u.zip_code AND t.new_dist_channel = u.dist_ch
--  LEFT JOIN (SELECT x.*, k.CLEAN_ID FROM ssdb_integration.lr_strategy.crbg_wh_addr x
--             JOIN ssdb_integration.lr_strategy.NAME_KEY k ON k.SRC_TABLE = 'crbg_wh_addr' AND k.RAW_NAME = x.agent) ha
--        ON ha.CLEAN_ID = h.CLEAN_ID;
--EQH alike: data_withnewchannel_eqhv3; eqh_territories by rvp, ON zip_code and channel = dist_ch; eqh_wh_addr by wh.
--The checks count how many union rows these joins reach, and the IDs with 2+ address rows (they repeat union rows).
--
--How names are split (3): "Last, First M", "Last, First M Jr.", "Last Jr., First", "Last, M First", "First M Last",
--"M First Last", "First Last, CFP", nicknames in () or "", periods, accents, spacing, case, particles ("De La Cruz").
--An initial before a full name is the middle initial.  A placeholder (the word OPEN, UNASSIGNED or VACANT, or a spaced
--dash as in "IFA - Northeast") is not a person.  V is never a suffix.
--How names are matched (4), within a firm, the first step that finds a candidate deciding:
--  0 your pair   1 same name (last, first, middle initial, suffix)   2 same last and first   3 nickname
--  4 one first name is the other's initial or middle name   5 part of a hyphenated last name
--  6 close spelling (JAROWINKLER_SIMILARITY: last >= 90, first >= 85)   7 territories alone (each the other's best,
--  covering >= 0.8 of its ZIP x channel cells, runner-up < 0.5)
--Steps 0-2 match unless the territories clearly disagree (cover < 0.5); steps 3-6 match only where the territories
--agree (cover >= 0.8), otherwise they wait in the review list.  2+ candidates: the one with the same middle initial,
--else the one whose territories agree, else review.
--How IDs are given (5): a wholesaler is the names matched to each other, directly or through another table.  No ID,
--and REVIEW says why, for a placeholder or a name with no first name, a name with 2+ candidates or claimed by 2+
--people, names linking two middle initials or suffixes, and two unlinked wholesalers with one clean name.  To confirm
--a pair from the review list, add it to statement 1 (or the nickname to statement 2) and Run All again.

--Statement 1.  Your pairs: two names of one firm that are one person, in any two tables; they win over every step.
--One line per pair, e.g. ('CRBG', '<name as in one table>', '<name as in the other>'); ('', '', '') lists none.
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_name_manual AS
SELECT SOURCE, NAME_A, NAME_B FROM (VALUES ('', '', '')) v(SOURCE, NAME_A, NAME_B) WHERE NAME_A <> '';

--Statement 2.  Nicknames: each NICK once, with the name it stands for.
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

--Statement 3.  Every name split.  SRC_TABLE 'sample': made-up names with their expected split (E_*), parsed by the same
--steps, so the first check proves the parsing on Snowflake itself; add a line for any new case.  To add a name column:
--one more line in src.  To add a suffix, credential or particle: the lists in s and l.  No backslashes in any pattern.
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_name_norm AS
WITH
src AS (
  SELECT 'data_withnewchannel_eqhv3' AS SRC_TABLE, 'updated_wholesaler2026' AS SRC_COLUMN, 'EQH' AS SOURCE,
         updated_wholesaler2026 AS RAW_NAME
  FROM ssdb_integration.lr_strategy.data_withnewchannel_eqhv3
  UNION ALL SELECT 'data_withnewchannel_eqhv3', 'wholesaler_name', 'EQH', wholesaler_name
            FROM ssdb_integration.lr_strategy.data_withnewchannel_eqhv3
  UNION ALL SELECT 'data_withnewchannel_crbgwithiova', 'updated_wholesaler2026', 'CRBG', updated_wholesaler2026
            FROM ssdb_integration.lr_strategy.data_withnewchannel_crbgwithiova
  UNION ALL SELECT 'data_withnewchannel_crbgwithiova', 'wholesaler_name', 'CRBG', wholesaler_name
            FROM ssdb_integration.lr_strategy.data_withnewchannel_crbgwithiova
  UNION ALL SELECT 'eqh_territories', 'rvp', 'EQH', rvp FROM ssdb_integration.lr_strategy.eqh_territories
  UNION ALL SELECT 'crbg_territories', 'whslr_nm', 'CRBG', whslr_nm FROM ssdb_integration.lr_strategy.crbg_territories
  UNION ALL SELECT 'eqh_wh_addr', 'wh', 'EQH', wh FROM ssdb_integration.lr_strategy.eqh_wh_addr
  UNION ALL SELECT 'crbg_wh_addr', 'agent', 'CRBG', agent FROM ssdb_integration.lr_strategy.crbg_wh_addr),
smp AS (
  SELECT * FROM (VALUES
    ('Doe, Jane Q',              'DOE',       'JANE',    'Q',      NULL),
    ('DOE, JANE Q.',             'DOE',       'JANE',    'Q',      NULL),
    ('Doe, Jane Quinn',          'DOE',       'JANE',    'QUINN',  NULL),
    ('Doe, Jane Q Jr.',          'DOE',       'JANE',    'Q',      'JR'),
    ('Doe, Jane Q, III',         'DOE',       'JANE',    'Q',      'III'),
    ('Doe Jr., Jane Q',          'DOE',       'JANE',    'Q',      'JR'),
    ('Roe, Richard V',           'ROE',       'RICHARD', 'V',      NULL),
    ('Jane Q. Doe',              'DOE',       'JANE',    'Q',      NULL),
    ('Jane Doe',                 'DOE',       'JANE',    NULL,     NULL),
    ('  jane   q   doe  ',       'DOE',       'JANE',    'Q',      NULL),
    ('Jane Q Doe Jr',            'DOE',       'JANE',    'Q',      'JR'),
    ('Jane Q Doe IV',            'DOE',       'JANE',    'Q',      'IV'),
    ('Jane Doe, CFP',            'DOE',       'JANE',    NULL,     NULL),
    ('Jane Doe II, CFP, ChFC',   'DOE',       'JANE',    NULL,     'II'),
    ('Jane (JJ) Doe',            'DOE',       'JANE',    NULL,     NULL),
    ('Jane "JJ" Doe',            'DOE',       'JANE',    NULL,     NULL),
    ('Jane O Doe',               'DOE',       'JANE',    'O',      NULL),
    ('Jane Q Smith-Roe',         'SMITH-ROE', 'JANE',    'Q',      NULL),
    ('Jane O''Roe',              'O''ROE',    'JANE',    NULL,     NULL),
    ('Jane de la Roe',           'DE LA ROE', 'JANE',    NULL,     NULL),
    ('Jane Q Van Roe',           'VAN ROE',   'JANE',    'Q',      NULL),
    ('De La Roe, Jane',          'DE LA ROE', 'JANE',    NULL,     NULL),
    ('Del Roe',                  'ROE',       'DEL',     NULL,     NULL),
    ('José Doe',                 'DOE',       'JOSE',    NULL,     NULL),
    ('Doe, Q Jane',              'DOE',       'JANE',    'Q',      NULL),
    ('DOE, Q. JANE JR',          'DOE',       'JANE',    'Q',      'JR'),
    ('J. Robert Doe',            'DOE',       'ROBERT',  'J',      NULL),
    ('Doe, J',                   'DOE',       'J',       NULL,     NULL),
    ('Vacant',                   NULL,        NULL,      NULL,     NULL),
    ('Open - IFA',               NULL,        NULL,      NULL,     NULL),
    ('IFA-OPEN',                 NULL,        NULL,      NULL,     NULL),
    ('Unassigned',               NULL,        NULL,      NULL,     NULL),
    ('Copenhaver, Jane',         'COPENHAVER','JANE',    NULL,     NULL)
  ) v(RAW_NAME, E_LAST, E_FIRST, E_MIDDLE, E_SUFFIX)),
i AS (
  SELECT SRC_TABLE, SRC_COLUMN, SOURCE, RAW_NAME, COUNT(*) AS N_ROWS, CAST(NULL AS VARCHAR) AS E_LAST,
         CAST(NULL AS VARCHAR) AS E_FIRST, CAST(NULL AS VARCHAR) AS E_MIDDLE, CAST(NULL AS VARCHAR) AS E_SUFFIX
  FROM src WHERE RAW_NAME IS NOT NULL GROUP BY SRC_TABLE, SRC_COLUMN, SOURCE, RAW_NAME
  UNION ALL
  SELECT 'sample', 'RAW_NAME', NULL, RAW_NAME, 1, E_LAST, E_FIRST, E_MIDDLE, E_SUFFIX FROM smp),
c0 AS (  -- accents off, upper case, nicknames in () or "" out, anything but letters ' - and , becomes a space
  SELECT i.*,
         REGEXP_REPLACE(REGEXP_REPLACE(
           UPPER(TRANSLATE(RAW_NAME, 'ÀÁÂÃÄÅÇÈÉÊËÌÍÎÏÑÒÓÔÕÖÙÚÛÜÝàáâãäåçèéêëìíîïñòóôõöùúûüý',
                                     'AAAAAACEEEEIIIINOOOOOUUUUYaaaaaaceeeeiiiinooooouuuuy')),
           '[(][^)]*[)]|"[^"]*"', ' '),
           '[^A-Z,''-]', ' ') AS U0
  FROM i),
c AS (   -- PH: a placeholder, not a person (its U is blanked, so every part comes out NULL)
  SELECT c0.*, PH, CASE WHEN PH THEN '' ELSE U0 END AS U
  FROM (SELECT c0.*, ' ' || TRANSLATE(U0, '-,', '  ') || ' ' LIKE '% OPEN %'
                  OR ' ' || TRANSLATE(U0, '-,', '  ') || ' ' LIKE '% UNASSIGNED %'
                  OR ' ' || TRANSLATE(U0, '-,', '  ') || ' ' LIKE '% VACANT %'
                  OR RAW_NAME LIKE '% - %' AS PH
        FROM c0) c0),
t AS (   -- every token (commas too) between its own spaces, so adjacent tokens each match ' TOKEN '
  SELECT c.*, ' ' || REPLACE(REPLACE(U, ',', ' , '), ' ', '  ') || ' ' AS T FROM c),
s AS (   -- the suffix kept; suffixes and credentials taken out
  SELECT t.*,
         REGEXP_SUBSTR(T, ' (JR|SR|II|III|IV) ', 1, 1, 'e', 1) AS SFX,
         REGEXP_REPLACE(T, ' (JR|SR|II|III|IV|CFP|CHFC|CLU|CIMA|CFA|RICP|MBA) ', ' ') AS R0
  FROM t),
r AS (   -- one space between tokens, none around a hyphen or a comma, one comma at most in a row, none at either end
  SELECT s.*,
         TRIM(REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(R0, ' +', ' '), ' ?- ?', '-'), ' ?, ?', ','),
                             ',+', ','), ' ,-') AS R
  FROM s),
f AS (   -- "LAST, FIRST ..." when there is a comma
  SELECT r.*, POSITION(',' IN R) > 0 AS LF FROM r),
g AS (
  SELECT f.*,
         CASE WHEN LF THEN TRIM(REPLACE(SUBSTR(R, POSITION(',' IN R) + 1), ',', ' ')) ELSE R END AS GIVEN
  FROM f),
h AS (   -- FIRST = the first given token; REST = what follows it
  SELECT g.*, SPLIT_PART(GIVEN, ' ', 1) AS F1, TRIM(SUBSTR(GIVEN, LENGTH(SPLIT_PART(GIVEN, ' ', 1)) + 1)) AS REST
  FROM g),
l AS (   -- "FIRST ... LAST": LAST = the last token with any particles before it (never the first token)
  SELECT h.*,
         CASE WHEN LF THEN TRIM(SPLIT_PART(R, ',', 1))
              ELSE REGEXP_SUBSTR(REST, '(^| )(((DA|DE|DEL|DELLA|DER|DI|DU|LA|LE|VAN|VON|DEN|ST|SAN|SANTA) )*[^ ]+)$',
                                 1, 1, 'e', 2) END AS L1
  FROM h),
m AS (   -- M0 = the middle names: GIVEN after the first token ("LAST, FIRST ...") or REST before the last name
  SELECT l.*, NULLIF(TRIM(CASE WHEN LF THEN REST ELSE LEFT(REST, LENGTH(REST) - LENGTH(COALESCE(L1, ''))) END), '') AS M0
  FROM l),
x AS (   -- SW: an initial before a full name ("Last, M First", "M First Last"): the full name is the first name
  SELECT m.*, COALESCE(LENGTH(F1) = 1 AND LENGTH(SPLIT_PART(M0, ' ', 1)) > 1, FALSE) AS SW FROM m),
y AS (
  SELECT x.*,
         CASE WHEN SW THEN SPLIT_PART(M0, ' ', 1) ELSE F1 END AS FN,
         CASE WHEN SW THEN TRIM(F1 || ' ' || SUBSTR(M0, LENGTH(SPLIT_PART(M0, ' ', 1)) + 1)) ELSE M0 END AS MN
  FROM x),
z AS (
  SELECT SRC_TABLE, SRC_COLUMN, SOURCE, RAW_NAME, N_ROWS, E_LAST, E_FIRST, E_MIDDLE, E_SUFFIX,
         NULLIF(COALESCE(NULLIF(L1, ''), F1), '') AS LAST_NAME,
         CASE WHEN NULLIF(L1, '') IS NOT NULL THEN NULLIF(FN, '') END AS FIRST_NAME,
         MN AS MIDDLE_NAME, LEFT(MN, 1) AS MIDDLE_INITIAL, SFX AS SUFFIX,
         CASE WHEN PH THEN 'PLACEHOLDER' WHEN R = '' THEN NULL WHEN LF THEN 'LAST, FIRST'
              WHEN NULLIF(L1, '') IS NULL THEN 'ONE WORD' ELSE 'FIRST LAST' END AS FORMAT
  FROM y)
SELECT z.*,   -- NAME_STD "LAST, FIRST M SUFFIX"; NAME_KEY LAST|FIRST, letters only
       LAST_NAME || COALESCE(', ' || FIRST_NAME, '') || COALESCE(' ' || MIDDLE_INITIAL, '') || COALESCE(' ' || SUFFIX, '')
         AS NAME_STD,
       REGEXP_REPLACE(LAST_NAME, '[^A-Z]', '') || '|' || COALESCE(REGEXP_REPLACE(FIRST_NAME, '[^A-Z]', ''), '') AS NAME_KEY
FROM z;

--Statement 4.  Every name matched to the names of each other column of its firm: one row per name x other column
--where a step found a candidate.  STATUS 'matched' or 'review' (REVIEW says why; TO_NAME NULL: 2+ candidates, listed
--in CANDIDATES);
--CLAIMED: the TO name is matched by 2+ people of the FROM column.  COVER = share of the FROM name's ZIP x channel
--cells the TO name covers, where both columns have cells (g: the union holder and the territories tables; the CRBG
--union's updated_wholesaler2026 is crbg_territories.whslr_nm at the same zip and new_dist_channel = dist_ch; EQH's
--channel is taken to be the union's dist_ch: if the checks show few union rows reaching a territories row, use
--channel_name, or one constant on both sides to compare ZIPs alone).
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_name_xwalk AS
WITH
g AS (
  SELECT DISTINCT SRC_TABLE, SRC_COLUMN, SOURCE, RAW_NAME, LPAD(LEFT(TRIM(TO_CHAR(ZIP)), 5), 5, '0') AS ZIP_CODE, CHANNEL
  FROM (
    SELECT 'data_withnewchannel_eqhv3' AS SRC_TABLE, 'updated_wholesaler2026' AS SRC_COLUMN, 'EQH' AS SOURCE,
           updated_wholesaler2026 AS RAW_NAME, zip_code AS ZIP, dist_ch AS CHANNEL
    FROM ssdb_integration.lr_strategy.data_withnewchannel_eqhv3
    UNION ALL SELECT 'data_withnewchannel_crbgwithiova', 'updated_wholesaler2026', 'CRBG', updated_wholesaler2026, zip_code,
                     dist_ch
              FROM ssdb_integration.lr_strategy.data_withnewchannel_crbgwithiova
    UNION ALL SELECT 'eqh_territories', 'rvp', 'EQH', rvp, zip_code, channel FROM ssdb_integration.lr_strategy.eqh_territories
    UNION ALL SELECT 'crbg_territories', 'whslr_nm', 'CRBG', whslr_nm, zip, new_dist_channel
              FROM ssdb_integration.lr_strategy.crbg_territories) x
  WHERE RAW_NAME IS NOT NULL AND ZIP IS NOT NULL AND CHANNEL IS NOT NULL),
n AS (   -- the person names; FIRST_CANON = the first name through the nickname list
  SELECT x.*, COALESCE(a.FORMAL, x.FIRST_NAME) AS FIRST_CANON
  FROM ssdb_integration.lr_strategy.tmp_name_norm x
  LEFT JOIN ssdb_integration.lr_strategy.tmp_name_alias a ON a.NICK = x.FIRST_NAME
  WHERE x.FIRST_NAME IS NOT NULL AND x.SRC_TABLE <> 'sample'),
m AS (SELECT * FROM ssdb_integration.lr_strategy.tmp_name_manual),
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
p AS (   -- every pair of person names of one firm in different columns, with the first step it passes
  SELECT a.SOURCE, a.SRC_TABLE AS FROM_TABLE, a.SRC_COLUMN AS FROM_COLUMN, a.RAW_NAME AS FROM_NAME,
         b.SRC_TABLE AS TO_TABLE, b.SRC_COLUMN AS TO_COLUMN, b.RAW_NAME AS TO_NAME,
         COALESCE(a.MIDDLE_INITIAL = b.MIDDLE_INITIAL, FALSE) AS SAME_MI,
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
  SELECT SOURCE, FROM_TABLE, FROM_COLUMN, FROM_NAME, TO_TABLE, TO_COLUMN, TO_NAME, STEP, N_CAND, COVER,
         CASE WHEN STEP = 0 OR (STEP <= 2 AND NOT (GEO AND COVER < 0.5)) OR COVER >= 0.8 THEN 'matched' ELSE 'review' END
           AS STATUS,
         CASE WHEN STEP = 0 OR (STEP <= 2 AND NOT (GEO AND COVER < 0.5)) OR COVER >= 0.8 THEN NULL
              WHEN STEP <= 2 THEN 'same name, territories do not agree'
              WHEN GEO THEN 'name candidate, territories do not agree'
              ELSE 'name candidate, no territory cells to check it' END AS REVIEW,
         CAST(NULL AS VARCHAR) AS CANDIDATES
  FROM f WHERE PICKED
  UNION ALL   -- 2+ candidates and no rule picks one
  SELECT SOURCE, FROM_TABLE, FROM_COLUMN, FROM_NAME, TO_TABLE, TO_COLUMN, NULL, MIN(STEP), MIN(N_CAND), NULL, 'review',
         MIN(N_CAND) || ' candidates at one step, none picked', LISTAGG(TO_NAME, '; ') WITHIN GROUP (ORDER BY TO_NAME)
  FROM f WHERE N_PICKED = 0
  GROUP BY SOURCE, FROM_TABLE, FROM_COLUMN, FROM_NAME, TO_TABLE, TO_COLUMN
  UNION ALL
  SELECT t.SOURCE, t.FROM_TABLE, t.FROM_COLUMN, t.FROM_NAME, t.TO_TABLE, t.TO_COLUMN, t.TO_NAME, 7, NULL, t.COVER, 'matched', NULL,
         NULL
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
  HAVING COUNT(DISTINCT n.MIDDLE_INITIAL) > 1)
SELECT r.SOURCE, r.FROM_TABLE, r.FROM_COLUMN, r.FROM_NAME, r.TO_TABLE, r.TO_COLUMN, r.TO_NAME, r.STEP, r.N_CAND,
       ROUND(r.COVER, 3) AS COVER,
       CASE WHEN cl.TO_NAME IS NOT NULL THEN 'review' ELSE r.STATUS END AS STATUS,
       CASE WHEN cl.TO_NAME IS NOT NULL THEN 'claimed by 2+ people of this column' ELSE r.REVIEW END AS REVIEW,
       cl.TO_NAME IS NOT NULL AS CLAIMED, r.CANDIDATES
FROM res r
LEFT JOIN cl ON cl.SOURCE = r.SOURCE AND cl.FROM_TABLE = r.FROM_TABLE AND cl.FROM_COLUMN = r.FROM_COLUMN
            AND cl.TO_TABLE = r.TO_TABLE AND cl.TO_COLUMN = r.TO_COLUMN AND cl.TO_NAME = r.TO_NAME AND r.STATUS = 'matched';

--Statement 5.  NAME_KEY, the table kept.
CREATE OR REPLACE TABLE ssdb_integration.lr_strategy.NAME_KEY AS
WITH
n AS (   -- every name; NID = one node per firm x column x NAME_STD (spellings that normalize alike are one)
  SELECT SOURCE, SRC_TABLE, SRC_COLUMN, RAW_NAME, N_ROWS, FIRST_NAME, MIDDLE_INITIAL, SUFFIX, NAME_STD, FORMAT,
         SOURCE || '|' || SRC_TABLE || '|' || SRC_COLUMN || '|' || NAME_STD AS NID,
         CASE WHEN SRC_TABLE IN ('crbg_territories', 'eqh_territories') THEN 1
              WHEN SRC_COLUMN = 'updated_wholesaler2026' THEN 2
              WHEN SRC_COLUMN = 'wholesaler_name' THEN 3 ELSE 4 END AS PRIO
  FROM ssdb_integration.lr_strategy.tmp_name_norm WHERE SRC_TABLE <> 'sample'),
x AS (SELECT * FROM ssdb_integration.lr_strategy.tmp_name_xwalk),
amb AS (   -- ambiguous names: 2+ candidates in a column (FROM), or claimed by 2+ people of a column (TO)
  SELECT SOURCE, FROM_TABLE AS T, FROM_COLUMN AS C, FROM_NAME AS NM FROM x WHERE STATUS = 'review' AND TO_NAME IS NULL
  UNION
  SELECT SOURCE, TO_TABLE, TO_COLUMN, TO_NAME FROM x WHERE CLAIMED),
v AS (   -- the nodes that can carry an ID: a person name, not ambiguous in any spelling
  SELECT DISTINCT n.NID FROM n
  WHERE n.FIRST_NAME IS NOT NULL
    AND NOT EXISTS (SELECT 1 FROM n n2 JOIN amb ON amb.SOURCE = n2.SOURCE AND amb.T = n2.SRC_TABLE
                                                AND amb.C = n2.SRC_COLUMN AND amb.NM = n2.RAW_NAME
                    WHERE n2.NID = n.NID)),
mp AS (   -- the matched pairs between such nodes
  SELECT DISTINCT a.NID AS A, b.NID AS B
  FROM x
  JOIN n a ON a.SOURCE = x.SOURCE AND a.SRC_TABLE = x.FROM_TABLE AND a.SRC_COLUMN = x.FROM_COLUMN AND a.RAW_NAME = x.FROM_NAME
  JOIN n b ON b.SOURCE = x.SOURCE AND b.SRC_TABLE = x.TO_TABLE AND b.SRC_COLUMN = x.TO_COLUMN AND b.RAW_NAME = x.TO_NAME
  WHERE x.STATUS = 'matched' AND a.NID IN (SELECT NID FROM v) AND b.NID IN (SELECT NID FROM v)),
e AS (SELECT A, B FROM mp UNION SELECT B, A FROM mp UNION SELECT NID, NID FROM v),
--A wholesaler's label: the smallest NID it reaches, one more step along the pairs per pass (the checks say whether
--six are enough; if not, copy the l6 line as l7 and read l7 in w)
l1 AS (SELECT A AS NID, MIN(B) AS LAB FROM e GROUP BY A),
l2 AS (SELECT e.A AS NID, MIN(l.LAB) AS LAB FROM e JOIN l1 l ON l.NID = e.B GROUP BY e.A),
l3 AS (SELECT e.A AS NID, MIN(l.LAB) AS LAB FROM e JOIN l2 l ON l.NID = e.B GROUP BY e.A),
l4 AS (SELECT e.A AS NID, MIN(l.LAB) AS LAB FROM e JOIN l3 l ON l.NID = e.B GROUP BY e.A),
l5 AS (SELECT e.A AS NID, MIN(l.LAB) AS LAB FROM e JOIN l4 l ON l.NID = e.B GROUP BY e.A),
l6 AS (SELECT e.A AS NID, MIN(l.LAB) AS LAB FROM e JOIN l5 l ON l.NID = e.B GROUP BY e.A),
w AS (SELECT n.*, l6.LAB FROM n JOIN l6 ON l6.NID = n.NID),
mix AS (   -- labels joining names whose middle initials or suffixes differ: two people
  SELECT LAB FROM w GROUP BY LAB HAVING COUNT(DISTINCT MIDDLE_INITIAL) > 1 OR COUNT(DISTINCT SUFFIX) > 1),
p AS (   -- one row per wholesaler: CLEAN_NAME from its best-ranked spelling
  SELECT LAB, NAME_STD AS CLEAN_NAME, SOURCE || '_' || REGEXP_REPLACE(NAME_STD, '[^A-Z]+', '_') AS CLEAN_ID
  FROM w WHERE LAB NOT IN (SELECT LAB FROM mix)
  QUALIFY ROW_NUMBER() OVER (PARTITION BY LAB ORDER BY PRIO, LENGTH(NAME_STD) DESC, NAME_STD) = 1),
q AS (SELECT p.*, COUNT(*) OVER (PARTITION BY CLEAN_ID) AS N_SAME FROM p),
r AS (
  SELECT n.SOURCE, n.SRC_TABLE, n.SRC_COLUMN, n.RAW_NAME, n.N_ROWS, q.CLEAN_ID, q.CLEAN_NAME,
         CASE WHEN n.FORMAT = 'PLACEHOLDER' THEN 'placeholder'
              WHEN n.FIRST_NAME IS NULL THEN 'no first name'
              WHEN w.LAB IS NULL THEN 'ambiguous: 2+ candidates, or claimed by 2+ people'
              WHEN mix.LAB IS NOT NULL THEN 'links people whose middle initials or suffixes differ'
              WHEN q.N_SAME > 1 THEN 'clean name shared by 2+ wholesalers not linked' END AS REVIEW
  FROM n
  LEFT JOIN w ON w.SOURCE = n.SOURCE AND w.SRC_TABLE = n.SRC_TABLE AND w.SRC_COLUMN = n.SRC_COLUMN AND w.RAW_NAME = n.RAW_NAME
  LEFT JOIN mix ON mix.LAB = w.LAB
  LEFT JOIN q ON q.LAB = w.LAB)
SELECT SOURCE, SRC_TABLE, SRC_COLUMN, RAW_NAME, N_ROWS,
       CASE WHEN REVIEW IS NULL THEN CLEAN_ID END AS CLEAN_ID,
       CASE WHEN REVIEW IS NULL THEN CLEAN_NAME END AS CLEAN_NAME,
       REVIEW
FROM r;

--Statement 6.  Checks: every MUST_BE_ZERO = TRUE row must be 0.
WITH
nm AS (SELECT * FROM ssdb_integration.lr_strategy.tmp_name_norm),
x AS (SELECT * FROM ssdb_integration.lr_strategy.tmp_name_xwalk),
k AS (SELECT * FROM ssdb_integration.lr_strategy.NAME_KEY),
kk AS (SELECT * FROM k WHERE CLEAN_ID IS NOT NULL),
u AS (   -- the union rows with their holder's and seller's CLEAN_ID
  SELECT 'EQH' AS SOURCE, LPAD(LEFT(TRIM(TO_CHAR(u.zip_code)), 5), 5, '0') AS ZIP, u.dist_ch AS CH, h.CLEAN_ID AS HID, s.CLEAN_ID AS SID
  FROM ssdb_integration.lr_strategy.data_withnewchannel_eqhv3 u
  LEFT JOIN kk h ON h.SRC_TABLE = 'data_withnewchannel_eqhv3' AND h.SRC_COLUMN = 'updated_wholesaler2026' AND h.RAW_NAME = u.updated_wholesaler2026
  LEFT JOIN kk s ON s.SRC_TABLE = 'data_withnewchannel_eqhv3' AND s.SRC_COLUMN = 'wholesaler_name' AND s.RAW_NAME = u.wholesaler_name
  UNION ALL
  SELECT 'CRBG', LPAD(LEFT(TRIM(TO_CHAR(u.zip_code)), 5), 5, '0'), u.dist_ch, h.CLEAN_ID, s.CLEAN_ID
  FROM ssdb_integration.lr_strategy.data_withnewchannel_crbgwithiova u
  LEFT JOIN kk h ON h.SRC_TABLE = 'data_withnewchannel_crbgwithiova' AND h.SRC_COLUMN = 'updated_wholesaler2026' AND h.RAW_NAME = u.updated_wholesaler2026
  LEFT JOIN kk s ON s.SRC_TABLE = 'data_withnewchannel_crbgwithiova' AND s.SRC_COLUMN = 'wholesaler_name' AND s.RAW_NAME = u.wholesaler_name),
t AS (   -- the territories cells by CLEAN_ID
  SELECT DISTINCT k.CLEAN_ID, LPAD(LEFT(TRIM(TO_CHAR(x.zip_code)), 5), 5, '0') AS ZIP, x.channel AS CH
  FROM ssdb_integration.lr_strategy.eqh_territories x JOIN kk k ON k.SRC_TABLE = 'eqh_territories' AND k.RAW_NAME = x.rvp
  UNION
  SELECT DISTINCT k.CLEAN_ID, LPAD(LEFT(TRIM(TO_CHAR(x.zip)), 5), 5, '0'), x.new_dist_channel
  FROM ssdb_integration.lr_strategy.crbg_territories x JOIN kk k ON k.SRC_TABLE = 'crbg_territories' AND k.RAW_NAME = x.whslr_nm),
a AS (   -- address rows per CLEAN_ID
  SELECT k.CLEAN_ID, COUNT(*) AS N FROM ssdb_integration.lr_strategy.eqh_wh_addr x
  JOIN kk k ON k.SRC_TABLE = 'eqh_wh_addr' AND k.RAW_NAME = x.wh GROUP BY k.CLEAN_ID
  UNION ALL
  SELECT k.CLEAN_ID, COUNT(*) FROM ssdb_integration.lr_strategy.crbg_wh_addr x
  JOIN kk k ON k.SRC_TABLE = 'crbg_wh_addr' AND k.RAW_NAME = x.agent GROUP BY k.CLEAN_ID),
ua AS (   -- 1 = reached (t and a have one row per key, so no union row repeats)
  SELECT u.SOURCE, CASE WHEN th.CLEAN_ID IS NOT NULL THEN 1 ELSE 0 END AS H_TERR,
         CASE WHEN ha.CLEAN_ID IS NOT NULL THEN 1 ELSE 0 END AS H_ADDR,
         CASE WHEN sa.CLEAN_ID IS NOT NULL THEN 1 ELSE 0 END AS S_ADDR
  FROM u
  LEFT JOIN t th ON th.CLEAN_ID = u.HID AND th.ZIP = u.ZIP AND th.CH = u.CH
  LEFT JOIN a ha ON ha.CLEAN_ID = u.HID
  LEFT JOIN a sa ON sa.CLEAN_ID = u.SID),
sw AS (   -- names whose first and last swapped is another name's key in the firm: maybe "Last First" with no comma
  SELECT DISTINCT a.SOURCE, a.NAME_KEY FROM nm a
  JOIN nm b ON b.SOURCE = a.SOURCE
           AND b.NAME_KEY = REGEXP_REPLACE(a.FIRST_NAME, '[^A-Z]', '') || '|' || REGEXP_REPLACE(a.LAST_NAME, '[^A-Z]', '')
  WHERE a.FIRST_NAME IS NOT NULL AND b.NAME_KEY <> a.NAME_KEY)
SELECT 'sample names split differently from expected (the review list shows them)' AS CHECK_NAME,
       (SELECT COUNT(*) FROM nm WHERE SRC_TABLE = 'sample'
          AND (LAST_NAME IS DISTINCT FROM E_LAST OR FIRST_NAME IS DISTINCT FROM E_FIRST
               OR MIDDLE_NAME IS DISTINCT FROM E_MIDDLE OR SUFFIX IS DISTINCT FROM E_SUFFIX)) AS VALUE,
       TRUE AS MUST_BE_ZERO
UNION ALL SELECT 'nicknames listed twice',
       (SELECT COUNT(*) FROM (SELECT NICK FROM ssdb_integration.lr_strategy.tmp_name_alias GROUP BY NICK HAVING COUNT(*) > 1) d), TRUE
UNION ALL SELECT 'your pairs with a name that is not a person name of that firm',
       (SELECT COUNT(*) FROM ssdb_integration.lr_strategy.tmp_name_manual m
        WHERE NOT EXISTS (SELECT 1 FROM nm WHERE nm.SOURCE = m.SOURCE AND nm.RAW_NAME = m.NAME_A AND nm.FIRST_NAME IS NOT NULL)
           OR NOT EXISTS (SELECT 1 FROM nm WHERE nm.SOURCE = m.SOURCE AND nm.RAW_NAME = m.NAME_B AND nm.FIRST_NAME IS NOT NULL)), TRUE
UNION ALL SELECT 'name x column matched on 2+ rows',
       (SELECT COUNT(*) FROM (SELECT 1 FROM x GROUP BY SOURCE, FROM_TABLE, FROM_COLUMN, FROM_NAME, TO_TABLE, TO_COLUMN
                              HAVING COUNT(*) > 1) d), TRUE
UNION ALL SELECT 'names on 2+ rows of NAME_KEY',
       (SELECT COUNT(*) FROM (SELECT 1 FROM k GROUP BY SRC_TABLE, SRC_COLUMN, RAW_NAME HAVING COUNT(*) > 1) d), TRUE
UNION ALL SELECT 'matched pairs whose names got two different CLEAN_IDs (six passes not enough)',
       (SELECT COUNT(*) FROM x
        JOIN kk a ON a.SOURCE = x.SOURCE AND a.SRC_TABLE = x.FROM_TABLE AND a.SRC_COLUMN = x.FROM_COLUMN AND a.RAW_NAME = x.FROM_NAME
        JOIN kk b ON b.SOURCE = x.SOURCE AND b.SRC_TABLE = x.TO_TABLE AND b.SRC_COLUMN = x.TO_COLUMN AND b.RAW_NAME = x.TO_NAME
        WHERE x.STATUS = 'matched' AND a.CLEAN_ID <> b.CLEAN_ID), TRUE
UNION ALL SELECT 'names by FORMAT: ' || COALESCE(FORMAT, '(no letters)'), COUNT(*), FALSE
       FROM nm WHERE SRC_TABLE <> 'sample' GROUP BY FORMAT
UNION ALL SELECT 'names whose first/last swap is another name''s key (maybe "Last First", no comma)', (SELECT COUNT(*) FROM sw), FALSE
UNION ALL SELECT 'matches by step ' || STEP, COUNT(*), FALSE FROM x WHERE STATUS = 'matched' GROUP BY STEP
UNION ALL SELECT 'wholesalers, ' || SOURCE, COUNT(DISTINCT CLEAN_ID), FALSE FROM kk GROUP BY SOURCE
UNION ALL SELECT SRC_TABLE || '.' || SRC_COLUMN || ': % of names with a CLEAN_ID',
       ROUND(100 * COUNT(CLEAN_ID) / COUNT(*), 1), FALSE FROM k GROUP BY SRC_TABLE, SRC_COLUMN
UNION ALL SELECT SRC_TABLE || '.' || SRC_COLUMN || ': % of rows with a CLEAN_ID',
       ROUND(100 * SUM(CASE WHEN CLEAN_ID IS NOT NULL THEN N_ROWS ELSE 0 END) / SUM(N_ROWS), 1), FALSE
       FROM k GROUP BY SRC_TABLE, SRC_COLUMN
UNION ALL SELECT 'names with no CLEAN_ID: ' || REVIEW, COUNT(*), FALSE FROM k WHERE REVIEW IS NOT NULL GROUP BY REVIEW
UNION ALL SELECT SOURCE || ' union rows: % whose holder has a territories row at the same ZIP x channel',
       ROUND(100 * AVG(H_TERR), 1), FALSE FROM ua GROUP BY SOURCE
UNION ALL SELECT SOURCE || ' union rows: % whose holder has an address', ROUND(100 * AVG(H_ADDR), 1), FALSE
       FROM ua GROUP BY SOURCE
UNION ALL SELECT SOURCE || ' union rows: % whose seller has an address', ROUND(100 * AVG(S_ADDR), 1), FALSE
       FROM ua GROUP BY SOURCE
UNION ALL SELECT 'CLEAN_IDs with 2+ address rows (an address join repeats their union rows)',
       (SELECT COUNT(*) FROM a WHERE N > 1), FALSE
ORDER BY 3 DESC, 1;

--Statement 7.  The review list: real names, keep at work.  KIND:
--  'sample split wrong'  NAME_B = the split, REASON = what was expected
--  'no ID'               a name with no CLEAN_ID (placeholders left out), REASON = why
--  'pair to confirm'     two names a step found but did not match; same person: add the pair to statement 1
--  'pick one'            a name with 2+ candidates in a column (NAME_B lists them); add the right pair to statement 1
--  'maybe swapped'       NAME_A's first/last swapped is NAME_B's key; same person: add the pair to statement 1
WITH
nm AS (SELECT * FROM ssdb_integration.lr_strategy.tmp_name_norm),
k AS (SELECT * FROM ssdb_integration.lr_strategy.NAME_KEY),
pr AS (   -- review pairs, each once, unless both names already carry one CLEAN_ID
  SELECT x.*, JAROWINKLER_SIMILARITY(fa.NAME_STD, tb.NAME_STD) AS NAME_SCORE, ka.N_ROWS
  FROM ssdb_integration.lr_strategy.tmp_name_xwalk x
  JOIN nm fa ON fa.SOURCE = x.SOURCE AND fa.SRC_TABLE = x.FROM_TABLE AND fa.SRC_COLUMN = x.FROM_COLUMN AND fa.RAW_NAME = x.FROM_NAME
  JOIN nm tb ON tb.SOURCE = x.SOURCE AND tb.SRC_TABLE = x.TO_TABLE AND tb.SRC_COLUMN = x.TO_COLUMN AND tb.RAW_NAME = x.TO_NAME
  JOIN k ka ON ka.SRC_TABLE = x.FROM_TABLE AND ka.SRC_COLUMN = x.FROM_COLUMN AND ka.RAW_NAME = x.FROM_NAME
  JOIN k kb ON kb.SRC_TABLE = x.TO_TABLE AND kb.SRC_COLUMN = x.TO_COLUMN AND kb.RAW_NAME = x.TO_NAME
  WHERE x.STATUS = 'review' AND (ka.CLEAN_ID IS NULL OR kb.CLEAN_ID IS NULL OR ka.CLEAN_ID <> kb.CLEAN_ID)
  QUALIFY ROW_NUMBER() OVER (PARTITION BY x.SOURCE,
            LEAST(x.FROM_TABLE || '.' || x.FROM_COLUMN || ':' || x.FROM_NAME, x.TO_TABLE || '.' || x.TO_COLUMN || ':' || x.TO_NAME),
            GREATEST(x.FROM_TABLE || '.' || x.FROM_COLUMN || ':' || x.FROM_NAME, x.TO_TABLE || '.' || x.TO_COLUMN || ':' || x.TO_NAME)
          ORDER BY x.FROM_TABLE, x.FROM_COLUMN) = 1)
SELECT 'sample split wrong' AS KIND, CAST(NULL AS VARCHAR) AS SOURCE, 'sample' AS TABLE_A, 'RAW_NAME' AS COLUMN_A,
       RAW_NAME AS NAME_A, CAST(NULL AS VARCHAR) AS TABLE_B, CAST(NULL AS VARCHAR) AS COLUMN_B,
       COALESCE(LAST_NAME, '-') || ' | ' || COALESCE(FIRST_NAME, '-') || ' | ' || COALESCE(MIDDLE_NAME, '-') || ' | '
         || COALESCE(SUFFIX, '-') AS NAME_B,
       CAST(NULL AS INTEGER) AS STEP, CAST(NULL AS INTEGER) AS NAME_SCORE, CAST(NULL AS DOUBLE) AS COVER,
       'expected ' || COALESCE(E_LAST, '-') || ' | ' || COALESCE(E_FIRST, '-') || ' | ' || COALESCE(E_MIDDLE, '-') || ' | '
         || COALESCE(E_SUFFIX, '-') AS REASON,
       CAST(NULL AS INTEGER) AS N_ROWS
FROM nm
WHERE SRC_TABLE = 'sample' AND (LAST_NAME IS DISTINCT FROM E_LAST OR FIRST_NAME IS DISTINCT FROM E_FIRST
                                OR MIDDLE_NAME IS DISTINCT FROM E_MIDDLE OR SUFFIX IS DISTINCT FROM E_SUFFIX)
UNION ALL
SELECT 'no ID', SOURCE, SRC_TABLE, SRC_COLUMN, RAW_NAME, NULL, NULL, NULL, NULL, NULL, NULL, REVIEW, N_ROWS
FROM k WHERE REVIEW IS NOT NULL AND REVIEW <> 'placeholder'
UNION ALL
SELECT 'pair to confirm', SOURCE, FROM_TABLE, FROM_COLUMN, FROM_NAME, TO_TABLE, TO_COLUMN, TO_NAME, STEP, NAME_SCORE,
       COVER, REVIEW, N_ROWS
FROM pr
UNION ALL
SELECT 'pick one', x.SOURCE, x.FROM_TABLE, x.FROM_COLUMN, x.FROM_NAME, x.TO_TABLE, x.TO_COLUMN, x.CANDIDATES, x.STEP,
       NULL, NULL, x.REVIEW, k.N_ROWS
FROM ssdb_integration.lr_strategy.tmp_name_xwalk x
JOIN k ON k.SRC_TABLE = x.FROM_TABLE AND k.SRC_COLUMN = x.FROM_COLUMN AND k.RAW_NAME = x.FROM_NAME
WHERE x.STATUS = 'review' AND x.TO_NAME IS NULL
UNION ALL
SELECT DISTINCT 'maybe swapped', a.SOURCE, a.SRC_TABLE, a.SRC_COLUMN, a.RAW_NAME, b.SRC_TABLE, b.SRC_COLUMN, b.RAW_NAME,
       NULL, NULL, NULL, NULL, a.N_ROWS
FROM nm a
JOIN nm b ON b.SOURCE = a.SOURCE
         AND b.NAME_KEY = REGEXP_REPLACE(a.FIRST_NAME, '[^A-Z]', '') || '|' || REGEXP_REPLACE(a.LAST_NAME, '[^A-Z]', '')
WHERE a.FIRST_NAME IS NOT NULL AND b.NAME_KEY <> a.NAME_KEY AND a.NAME_KEY < b.NAME_KEY
ORDER BY 1, 2, 3, 4, 13 DESC, 5;
