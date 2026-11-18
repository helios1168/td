use role rl_ssdb_Integration_Lr_Strategy_Rw;
use database ssdb_Integration;
use schema lr_strategy;
--THE RESULT HOLDS WHOLESALER NAMES: for the owner's screen only, never sent to an agent or put in the repo.
--The shortlist sheet's names that match no territory holder (03 returns them as EDIT NOT MATCHED, source SHEET), each
--beside the holders of either firm with the same last name, to tell a spelling difference from a new hire.  The key is
--03's: a name with a comma flipped, upper case, single spaces.  Read only, one result.  A name with no candidate has
--one row with the holder columns blank.  A cell with several names (Ann Lee or Bo Ray, Ann Lee / Bo Ray, as 03) is each
--name on its own.  SHEET_KEY and HOLDER_KEY are the exact texts 03 compares, ODD_CHAR 1 when the name has a character
--outside plain ASCII (a non-breaking space, a curly apostrophe).  Fix a spelling difference in the sheet table
--(data\safe\fix_names.sql), then Run All 03.
SET sheet_tbl = 'ssdb_integration.lr_strategy.channel_contacts';
SET terr_tbl  = 'ssdb_integration.lr_strategy.territories_tableau';
WITH
s AS (SELECT NULLIF(NULLIF(NULLIF(NULLIF(UPPER(TRIM(REGEXP_REPLACE(CASE WHEN POSITION(',' IN p.value) > 0
                                                  THEN SPLIT_PART(p.value, ',', 2) || ' ' || SPLIT_PART(p.value, ',', 1)
                                                  ELSE p.value END, '\\s+', ' '))), ''), 'N/A'), 'OPEN'), 'TBD') AS k,
             TRIM(p.value) AS name, x.ch, CASE WHEN REGEXP_LIKE(p.value, '.*[^ -~].*') THEN 1 ELSE 0 END AS odd
      FROM (SELECT UPPER(TRIM(channel)) AS ch,
                   REGEXP_REPLACE(CASE WHEN UPPER(TRIM(name)) IN ('N/A', 'OPEN', 'TBD') THEN '' ELSE COALESCE(name, '') END, '(\\s+[Oo][Rr])?\\s*/\\s*|\\s+[Oo][Rr]\\s+', '|') || '|' AS nm_split
            FROM IDENTIFIER($sheet_tbl)) x,
      LATERAL SPLIT_TO_TABLE(x.nm_split, '|') p),
h AS (SELECT DISTINCT UPPER(TRIM(source)) AS src, nm AS holder, UPPER(TRIM(channel)) AS ch,
             CASE WHEN REGEXP_LIKE(nm, '.*[^ -~].*') THEN 1 ELSE 0 END AS odd,
             UPPER(TRIM(REGEXP_REPLACE(CASE WHEN POSITION(',' IN nm) > 0 THEN SPLIT_PART(nm, ',', 2) || ' ' || SPLIT_PART(nm, ',', 1)
                                            ELSE nm END, '\\s+', ' '))) AS k
      FROM (SELECT source, channel, TRIM(COALESCE(NULLIF(TRIM(clean_name), ''), name)) AS nm FROM IDENTIFIER($terr_tbl))
      WHERE NULLIF(TRIM(nm), '') IS NOT NULL AND UPPER(TRIM(nm)) <> 'OPEN'),
hk AS (SELECT src, MIN(holder) AS holder, k, MAX(odd) AS odd, LISTAGG(DISTINCT ch, ' ') WITHIN GROUP (ORDER BY ch) AS holder_channels
       FROM h GROUP BY src, k),
u AS (SELECT k, MIN(name) AS sheet_name, MAX(odd) AS odd, LISTAGG(DISTINCT ch, ' ') WITHIN GROUP (ORDER BY ch) AS sheet_channels
      FROM s WHERE k IS NOT NULL AND k NOT IN (SELECT k FROM hk) GROUP BY k)
SELECT u.sheet_name, u.k AS sheet_key, u.odd AS sheet_odd_char, u.sheet_channels,
       hk.src AS holder_source, hk.holder, hk.k AS holder_key, hk.odd AS holder_odd_char, hk.holder_channels
FROM u LEFT JOIN hk ON REGEXP_SUBSTR(hk.k, '[^ ]+$') = REGEXP_SUBSTR(u.k, '[^ ]+$')
ORDER BY u.sheet_name, hk.src, hk.holder;
