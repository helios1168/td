use role rl_ssdb_Integration_Lr_Strategy_Rw;
use database ssdb_Integration;
use schema lr_strategy;
--THE RESULT HOLDS WHOLESALER NAMES: for the owner's screen only, never sent to an agent or put in the repo.
--The shortlist sheet's names that match no territory holder (03 returns them as EDIT NOT MATCHED, source SHEET), each
--beside the holders of either firm with the same last name, to tell a spelling difference from a new hire.  The key is
--03's: a name with a comma flipped, upper case, single spaces.  Read only, one result.  A name with no candidate has
--one row with the holder columns blank.  Fix a spelling difference in the sheet table, then Run All 03.
SET sheet_tbl = 'ssdb_integration.lr_strategy.REPLACE_WITH_THE_SHEET_TABLE';
SET terr_tbl  = 'ssdb_integration.lr_strategy.territories_tableau';
WITH
s AS (SELECT NULLIF(UPPER(TRIM(REGEXP_REPLACE(CASE WHEN POSITION(',' IN name) > 0
                                                  THEN SPLIT_PART(name, ',', 2) || ' ' || SPLIT_PART(name, ',', 1)
                                                  ELSE name END, '\\s+', ' '))), '') AS k,
             TRIM(name) AS name, UPPER(TRIM(channel)) AS ch
      FROM IDENTIFIER($sheet_tbl)),
h AS (SELECT DISTINCT UPPER(TRIM(source)) AS src, nm AS holder, UPPER(TRIM(channel)) AS ch,
             UPPER(TRIM(REGEXP_REPLACE(CASE WHEN POSITION(',' IN nm) > 0 THEN SPLIT_PART(nm, ',', 2) || ' ' || SPLIT_PART(nm, ',', 1)
                                            ELSE nm END, '\\s+', ' '))) AS k
      FROM (SELECT source, channel, TRIM(COALESCE(NULLIF(TRIM(clean_name), ''), name)) AS nm FROM IDENTIFIER($terr_tbl))
      WHERE NULLIF(TRIM(nm), '') IS NOT NULL AND UPPER(TRIM(nm)) <> 'OPEN'),
hk AS (SELECT src, MIN(holder) AS holder, k, LISTAGG(DISTINCT ch, ' ') WITHIN GROUP (ORDER BY ch) AS holder_channels
       FROM h GROUP BY src, k),
u AS (SELECT k, MIN(name) AS sheet_name, LISTAGG(DISTINCT ch, ' ') WITHIN GROUP (ORDER BY ch) AS sheet_channels
      FROM s WHERE k IS NOT NULL AND k NOT IN (SELECT k FROM hk) GROUP BY k)
SELECT u.sheet_name, u.sheet_channels, hk.src AS holder_source, hk.holder, hk.holder_channels
FROM u LEFT JOIN hk ON REGEXP_SUBSTR(hk.k, '[^ ]+$') = REGEXP_SUBSTR(u.k, '[^ ]+$')
ORDER BY u.sheet_name, hk.src, hk.holder;
