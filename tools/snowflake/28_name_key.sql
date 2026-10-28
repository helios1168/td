use secondary roles all;

--NAME_KEY: one CLEAN_ID and CLEAN_NAME per wholesaler, for every name of the eight name columns (26's input), so the
--two union tables join the territories and address tables on CLEAN_ID.  Run 26_name_norm.sql, then
--27_name_xwalk.sql, then this.  One row per SRC_TABLE x SRC_COLUMN x RAW_NAME (the name as written in the table).
--  CLEAN_ID    SOURCE_LAST_FIRST_M_SUFFIX, e.g. CRBG_DOE_JANE_Q; NULL when REVIEW says why
--  CLEAN_NAME  "LAST, FIRST M SUFFIX", spelled as the territories table spells the person, else the union holder
--              column, the seller column, the address table
--A wholesaler = the names 27 matched to each other, directly or through another table (Bill Roe in the union, William
--Roe in territories and Roe, William R in the addresses are one).  No ID, and REVIEW says why, for: a placeholder or
--a name with no first name; a name 27 found ambiguous (2+ candidates in a column, or claimed by 2+ people); names that
--link people with different middle initials or suffixes; two unlinked wholesalers with one clean name.  Confirm a
--pair in 27's statement 3 and Run All 26, 27 and 28 again.
--Run All: statement 1 writes NAME_KEY, statement 2 checks it (MUST_BE_ZERO rows must be 0).
--
--Joining: give each table its key through its own name column, then join on CLEAN_ID.  Territories also on ZIP and
--channel (a wholesaler has a row per ZIP x channel); addresses on CLEAN_ID alone.  For CRBG:
--  SELECT u.*, h.CLEAN_ID AS HOLDER_ID, s.CLEAN_ID AS SELLER_ID, t.whslr_id, ha.city AS HOLDER_CITY, sa.city AS SELLER_CITY
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
--        ON ha.CLEAN_ID = h.CLEAN_ID
--  LEFT JOIN (... the same for the seller ...) sa ON sa.CLEAN_ID = s.CLEAN_ID;
--EQH: data_withnewchannel_eqhv3; eqh_territories by rvp (ON zip_code, channel = dist_ch); eqh_wh_addr by wh.
--Statement 2 counts how many union rows these joins reach, and the IDs with 2+ address rows (they repeat union rows).

--Statement 1.
CREATE OR REPLACE TABLE ssdb_integration.lr_strategy.NAME_KEY AS
WITH
n AS (   -- every name; NID = one node per SOURCE x column x NAME_STD (spellings that normalize alike are one)
  SELECT SOURCE, SRC_TABLE, SRC_COLUMN, RAW_NAME, N_ROWS, FIRST_NAME, MIDDLE_INITIAL, SUFFIX, NAME_STD, FORMAT,
         SOURCE || '|' || SRC_TABLE || '|' || SRC_COLUMN || '|' || NAME_STD AS NID,
         CASE WHEN SRC_TABLE IN ('crbg_territories', 'eqh_territories') THEN 1
              WHEN SRC_COLUMN = 'updated_wholesaler2026' THEN 2
              WHEN SRC_COLUMN = 'wholesaler_name' THEN 3 ELSE 4 END AS PRIO
  FROM ssdb_integration.lr_strategy.NAME_NORM),
x AS (SELECT * FROM ssdb_integration.lr_strategy.NAME_XWALK),
amb AS (   -- names 27 found ambiguous: 2+ candidates in a column (FROM), or claimed by 2+ people of a column (TO)
  SELECT SOURCE, FROM_TABLE AS T, FROM_COLUMN AS C, FROM_NAME AS NM FROM x WHERE STATUS = 'review' AND TO_NAME IS NULL
  UNION
  SELECT SOURCE, TO_TABLE, TO_COLUMN, TO_NAME FROM x WHERE REVIEW LIKE 'TO name also matched%'),
v AS (   -- the nodes that can carry an ID: a person name, not ambiguous in any spelling
  SELECT DISTINCT n.NID FROM n
  WHERE n.FIRST_NAME IS NOT NULL
    AND NOT EXISTS (SELECT 1 FROM n n2 JOIN amb ON amb.SOURCE = n2.SOURCE AND amb.T = n2.SRC_TABLE
                                                AND amb.C = n2.SRC_COLUMN AND amb.NM = n2.RAW_NAME
                    WHERE n2.NID = n.NID)),
m AS (   -- the matched pairs between such nodes
  SELECT DISTINCT a.NID AS A, b.NID AS B
  FROM x
  JOIN n a ON a.SOURCE = x.SOURCE AND a.SRC_TABLE = x.FROM_TABLE AND a.SRC_COLUMN = x.FROM_COLUMN AND a.RAW_NAME = x.FROM_NAME
  JOIN n b ON b.SOURCE = x.SOURCE AND b.SRC_TABLE = x.TO_TABLE AND b.SRC_COLUMN = x.TO_COLUMN AND b.RAW_NAME = x.TO_NAME
  WHERE x.STATUS = 'matched' AND a.NID IN (SELECT NID FROM v) AND b.NID IN (SELECT NID FROM v)),
e AS (SELECT A, B FROM m UNION SELECT B, A FROM m UNION SELECT NID, NID FROM v),
--A wholesaler's label: the smallest NID it reaches, one more step of the links per pass (statement 2 checks that six are
--enough; if not, copy the l6 line as l7 and read l7 in w)
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
  SELECT LAB, SOURCE, NAME_STD AS CLEAN_NAME, SOURCE || '_' || REGEXP_REPLACE(NAME_STD, '[^A-Z]+', '_') AS CLEAN_ID
  FROM w WHERE LAB NOT IN (SELECT LAB FROM mix)
  QUALIFY ROW_NUMBER() OVER (PARTITION BY LAB ORDER BY PRIO, LENGTH(NAME_STD) DESC, NAME_STD) = 1),
q AS (SELECT p.*, COUNT(*) OVER (PARTITION BY CLEAN_ID) AS N_SAME FROM p),
r AS (
  SELECT n.SOURCE, n.SRC_TABLE, n.SRC_COLUMN, n.RAW_NAME, n.N_ROWS, q.CLEAN_ID, q.CLEAN_NAME,
         CASE WHEN n.FORMAT = 'PLACEHOLDER' THEN 'placeholder'
              WHEN n.FIRST_NAME IS NULL THEN 'no first name'
              WHEN w.LAB IS NULL THEN 'ambiguous in 27: 2+ candidates, or claimed by 2+ people'
              WHEN mix.LAB IS NOT NULL THEN 'links people whose middle initials or suffixes differ'
              WHEN q.N_SAME > 1 THEN 'clean name shared by 2+ wholesalers not linked by 27' END AS REVIEW
  FROM n
  LEFT JOIN w ON w.SOURCE = n.SOURCE AND w.SRC_TABLE = n.SRC_TABLE AND w.SRC_COLUMN = n.SRC_COLUMN AND w.RAW_NAME = n.RAW_NAME
  LEFT JOIN mix ON mix.LAB = w.LAB
  LEFT JOIN q ON q.LAB = w.LAB)
SELECT SOURCE, SRC_TABLE, SRC_COLUMN, RAW_NAME, N_ROWS,
       CASE WHEN REVIEW IS NULL THEN CLEAN_ID END AS CLEAN_ID,
       CASE WHEN REVIEW IS NULL THEN CLEAN_NAME END AS CLEAN_NAME,
       REVIEW
FROM r;

--Statement 2.  Checks: every MUST_BE_ZERO = TRUE row must be 0.
WITH
k AS (SELECT * FROM ssdb_integration.lr_strategy.NAME_KEY),
kk AS (SELECT * FROM k WHERE CLEAN_ID IS NOT NULL),
x AS (SELECT * FROM ssdb_integration.lr_strategy.NAME_XWALK WHERE STATUS = 'matched'),
u AS (   -- the union rows with their holder's and seller's CLEAN_ID; ZIP and channel as 27 compares them
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
  LEFT JOIN a sa ON sa.CLEAN_ID = u.SID)
SELECT 'names on 2+ rows of NAME_KEY' AS CHECK_NAME,
       (SELECT COUNT(*) FROM (SELECT 1 FROM k GROUP BY SRC_TABLE, SRC_COLUMN, RAW_NAME HAVING COUNT(*) > 1) d) AS VALUE,
       TRUE AS MUST_BE_ZERO
UNION ALL SELECT 'pairs 27 matched whose names got two different CLEAN_IDs (six passes not enough)',
       (SELECT COUNT(*) FROM x
        JOIN kk a ON a.SOURCE = x.SOURCE AND a.SRC_TABLE = x.FROM_TABLE AND a.SRC_COLUMN = x.FROM_COLUMN AND a.RAW_NAME = x.FROM_NAME
        JOIN kk b ON b.SOURCE = x.SOURCE AND b.SRC_TABLE = x.TO_TABLE AND b.SRC_COLUMN = x.TO_COLUMN AND b.RAW_NAME = x.TO_NAME
        WHERE a.CLEAN_ID <> b.CLEAN_ID), TRUE
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
