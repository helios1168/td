use role rl_ssdb_Integration_Lr_Strategy_Rw;
use database ssdb_Integration;
use schema lr_strategy;

--Coverage of the main map's opportunity by the kept wholesalers of the roster (the assignments table that
--03_assignments.sql builds).  One Run All file.  It builds four tables for the maps and ends on one result of
--checks.  Set the three table names below, nothing else.  Rules: DATASET_LOG.md, 2026-11-15.
--The main map is the five fine channels of NEW_DIST: WH, FI, Wells WH, Wells FI, National (Chase).  Opportunity is once
--per cell, as 02_model_extract.sql, and is never added across sources: every table keeps the estimate's SOURCE.
--AREA.  A kept wholesaler's area is ZIPs they hold today: role WIFI or NATIONAL, every ZIP held in WH or FI.  Role WH,
--the ZIPs held in WH, or if they hold none in WH, the ZIPs held in FI.  Role FI the same way round.
--NEED.  What a cell needs at its ZIP: NATIONAL for the three national fine channels where a NATIONAL wholesaler's area
--has the ZIP.  Elsewhere they fall back (#67): Wells WH needs WH, Wells FI and National (Chase) need FI.  WH needs WH,
--FI needs FI.
--CLAIM.  NATIONAL is claimed by role NATIONAL, WH by roles WH and WIFI, FI by roles FI and WIFI, of either source,
--where the ZIP is in the wholesaler's area.  One claimant: CAPTURED.  None: GAP.  Two or more: OVERLAP.
--Tables (replaced on every run).  The first three hold wholesaler names and stay in Snowflake:
--  TD_MAP_WHOLESALER  one row per roster wholesaler x estimate SOURCE (EST_SOURCE): KEPT, ROLE, IN_TERRITORIES, N_AREA_ZIPS,
--                     OPP_CLAIMED, OPP_SOLE (no other claimant), OPP_SHARED.  On the wholesaler's own source only:
--                     OPP_HELD_TODAY (main-map cells they hold today), OPP_KEPT (held today and claimed), OPP_RELEASED
--                     (held today, not claimed), OPP_GAINED (claimed, not held today).
--  TD_MAP_AREA        SOURCE, WHOLESALER, ROLE, ZIP_CODE, HAS_WH, HAS_FI: the area, ZIPs with no opportunity included.
--  TD_MAP_CLAIM       SOURCE, WHOLESALER, ROLE, ZIP_CODE, NEED, N_CLAIM, N_CLAIM_FIRMS: one row per claim.
--  TD_MAP_CELL        SOURCE (the estimate's), ZIP_CODE, NEW_DIST, DIST_CH, MM_OPP, NEED, N_CLAIM, N_CLAIM_FIRMS, STATUS,
--                     CAPTURED_ROLE, GAP_REASON (by the cell's holder today: none, not kept, or kept in a role that
--                     does not cover it).  No names.
--Result: SECTION, SOURCE, K1, K2, N, MM_OPP, MUST_BE_ZERO.  No wholesaler name: it can be sent back.
--  ROSTER        K1 the count's name.  MUST_BE_ZERO = 1 rows must have N 0 before the tables are used.
--  ROLES         K1 role.  N kept wholesalers.
--  CAPTURE       K1 need, K2 status.  N cells, MM_OPP.  Per estimate SOURCE these rows add up to the main map.
--  FINE CHANNEL  K1 NEW_DIST, K2 need.  N cells, MM_OPP.  A national fine channel under WH or FI has fallen back.
--  TIE           TD_MAP_CELL against the union.
--A wholesaler is matched by name in upper case with single spaces.  ZIP_CODE is LPAD(LEFT(TRIM(..), 5), 5, '0').

SET union_tbl  = 'ssdb_integration.lr_strategy.sales_opp_2026_11_9';
SET terr_tbl   = 'ssdb_integration.lr_strategy.territories_tableau';
SET assign_tbl = 'ssdb_integration.lr_strategy.td_assignments';

--1 the roster, one row per SOURCE x normalized name
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_m_roster AS
SELECT source, nm, MIN(wholesaler) AS wholesaler, MAX(kept) AS kept, MAX(role) AS role, COUNT(*) AS n_rows
FROM (SELECT source, TRIM(wholesaler) AS wholesaler,
             NULLIF(UPPER(TRIM(REGEXP_REPLACE(TRIM(wholesaler), '\\s+', ' '))), '') AS nm,
             CASE WHEN COALESCE(UPPER(TRIM(CAST(kept AS VARCHAR))), '') IN ('Y', 'YES', 'TRUE', '1') THEN 'Y'
                  WHEN COALESCE(UPPER(TRIM(CAST(kept AS VARCHAR))), '') IN ('N', 'NO', 'FALSE', '0') THEN 'N'
                  WHEN COALESCE(UPPER(TRIM(CAST(kept AS VARCHAR))), '') = '' THEN '' ELSE '?' END AS kept,
             COALESCE(UPPER(TRIM(role)), '') AS role
      FROM IDENTIFIER($assign_tbl))
WHERE nm IS NOT NULL AND source IS NOT NULL
GROUP BY source, nm;

--2 who holds what today, every channel
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_m_hold AS
SELECT DISTINCT source, zip_code, ch, nm
FROM (SELECT source, LPAD(LEFT(TRIM(zip_code), 5), 5, '0') AS zip_code, COALESCE(UPPER(TRIM(channel)), '') AS ch,
             NULLIF(NULLIF(UPPER(TRIM(REGEXP_REPLACE(TRIM(COALESCE(NULLIF(TRIM(clean_name), ''), name)), '\\s+', ' '))), ''), 'OPEN') AS nm
      FROM IDENTIFIER($terr_tbl))
WHERE nm IS NOT NULL AND source IS NOT NULL;

--3 the area of each kept wholesaler with a role
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_m_area AS
WITH hz AS (SELECT source, nm, zip_code, MAX(CASE WHEN ch = 'WH' THEN 1 ELSE 0 END) AS has_wh,
                   MAX(CASE WHEN ch = 'FI' THEN 1 ELSE 0 END) AS has_fi
            FROM ssdb_integration.lr_strategy.tmp_m_hold WHERE ch IN ('WH', 'FI') GROUP BY source, nm, zip_code),
     hn AS (SELECT source, nm, MAX(has_wh) AS any_wh, MAX(has_fi) AS any_fi FROM hz GROUP BY source, nm)
SELECT r.source, r.nm, r.role, hz.zip_code, hz.has_wh, hz.has_fi
FROM ssdb_integration.lr_strategy.tmp_m_roster r
JOIN hz ON hz.source = r.source AND hz.nm = r.nm
JOIN hn ON hn.source = r.source AND hn.nm = r.nm
WHERE r.kept = 'Y'
  AND (r.role IN ('WIFI', 'NATIONAL') OR (r.role = 'WH' AND (hz.has_wh = 1 OR hn.any_wh = 0))
       OR (r.role = 'FI' AND (hz.has_fi = 1 OR hn.any_fi = 0)));

--4 the main map's opportunity, once per cell, by SOURCE x ZIP x NEW_DIST x DIST_CH
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_m_opp AS
SELECT source, zip_code, new_dist, dist_ch, SUM(opp) AS mm_opp
FROM (SELECT source, LPAD(LEFT(TRIM(zip_code), 5), 5, '0') AS zip_code, UPPER(TRIM(new_dist)) AS new_dist,
             COALESCE(UPPER(TRIM(dist_ch)), '') AS dist_ch, MAX(CASE WHEN mm_opp > 0 THEN mm_opp END) AS opp
      FROM IDENTIFIER($union_tbl)
      WHERE UPPER(TRIM(new_dist)) IN ('WH', 'FI', 'WELLS WH', 'WELLS FI', 'NATIONAL (CHASE)')
      GROUP BY source, fiscal_yr, LPAD(LEFT(TRIM(zip_code), 5), 5, '0'), cbd_id, firm, parent, firm_key, firm_crd, product_v2,
               dist_ch, new_dist, file_new_dist, channel, new_terr_channel
      HAVING MAX(CASE WHEN mm_opp > 0 THEN mm_opp END) IS NOT NULL)
GROUP BY source, zip_code, new_dist, dist_ch;

--5 what each cell needs at its ZIP
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_m_cell AS
SELECT o.source, o.zip_code, o.new_dist, o.dist_ch, o.mm_opp,
       CASE WHEN o.new_dist IN ('WELLS WH', 'WELLS FI', 'NATIONAL (CHASE)') AND n.zip_code IS NOT NULL THEN 'NATIONAL'
            WHEN o.new_dist IN ('WH', 'WELLS WH') THEN 'WH' ELSE 'FI' END AS need
FROM ssdb_integration.lr_strategy.tmp_m_opp o
LEFT JOIN (SELECT DISTINCT zip_code FROM ssdb_integration.lr_strategy.tmp_m_area WHERE role = 'NATIONAL') n ON n.zip_code = o.zip_code;

--6 the claims: ZIP x need x wholesaler
CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_m_claim AS
SELECT k.zip_code, k.need, a.source, a.nm, a.role
FROM (SELECT DISTINCT zip_code, need FROM ssdb_integration.lr_strategy.tmp_m_cell) k
JOIN ssdb_integration.lr_strategy.tmp_m_area a
  ON a.zip_code = k.zip_code
 AND ((k.need = 'NATIONAL' AND a.role = 'NATIONAL') OR (k.need = 'WH' AND a.role IN ('WH', 'WIFI'))
      OR (k.need = 'FI' AND a.role IN ('FI', 'WIFI')));

CREATE OR REPLACE TEMPORARY TABLE ssdb_integration.lr_strategy.tmp_m_count AS
SELECT zip_code, need, COUNT(*) AS n_claim, COUNT(DISTINCT source) AS n_claim_firms, MIN(role) AS one_role
FROM ssdb_integration.lr_strategy.tmp_m_claim GROUP BY zip_code, need;

--7 the tables
CREATE OR REPLACE TABLE ssdb_integration.lr_strategy.td_map_cell AS
WITH th AS (SELECT h.source, h.zip_code, h.ch, COUNT(CASE WHEN r.kept = 'Y' THEN 1 END) AS n_kept
            FROM ssdb_integration.lr_strategy.tmp_m_hold h
            LEFT JOIN ssdb_integration.lr_strategy.tmp_m_roster r ON r.source = h.source AND r.nm = h.nm
            GROUP BY h.source, h.zip_code, h.ch)
SELECT c.source, c.zip_code, c.new_dist, c.dist_ch, c.mm_opp, c.need, COALESCE(n.n_claim, 0) AS n_claim,
       COALESCE(n.n_claim_firms, 0) AS n_claim_firms,
       CASE WHEN n.n_claim IS NULL THEN 'GAP' WHEN n.n_claim = 1 THEN 'CAPTURED' ELSE 'OVERLAP' END AS status,
       CASE WHEN n.n_claim = 1 THEN n.one_role END AS captured_role,
       CASE WHEN n.n_claim IS NOT NULL THEN NULL WHEN th.zip_code IS NULL THEN 'NO HOLDER TODAY'
            WHEN th.n_kept > 0 THEN 'HOLDER KEPT IN A ROLE THAT DOES NOT COVER IT' ELSE 'HOLDER NOT KEPT' END AS gap_reason
FROM ssdb_integration.lr_strategy.tmp_m_cell c
LEFT JOIN ssdb_integration.lr_strategy.tmp_m_count n ON n.zip_code = c.zip_code AND n.need = c.need
LEFT JOIN th ON th.source = c.source AND th.zip_code = c.zip_code AND th.ch = c.dist_ch;

CREATE OR REPLACE TABLE ssdb_integration.lr_strategy.td_map_area AS
SELECT a.source, r.wholesaler, a.role, a.zip_code, a.has_wh, a.has_fi
FROM ssdb_integration.lr_strategy.tmp_m_area a
JOIN ssdb_integration.lr_strategy.tmp_m_roster r ON r.source = a.source AND r.nm = a.nm;

CREATE OR REPLACE TABLE ssdb_integration.lr_strategy.td_map_claim AS
SELECT c.source, r.wholesaler, c.role, c.zip_code, c.need, n.n_claim, n.n_claim_firms
FROM ssdb_integration.lr_strategy.tmp_m_claim c
JOIN ssdb_integration.lr_strategy.tmp_m_count n ON n.zip_code = c.zip_code AND n.need = c.need
JOIN ssdb_integration.lr_strategy.tmp_m_roster r ON r.source = c.source AND r.nm = c.nm;

CREATE OR REPLACE TABLE ssdb_integration.lr_strategy.td_map_wholesaler AS
WITH b AS (SELECT c.source, c.nm, x.source AS est_source, SUM(x.mm_opp) AS opp_claimed,
                  COALESCE(SUM(CASE WHEN x.n_claim = 1 THEN x.mm_opp END), 0) AS opp_sole,
                  COALESCE(SUM(CASE WHEN h.nm IS NOT NULL THEN x.mm_opp END), 0) AS opp_kept
           FROM ssdb_integration.lr_strategy.tmp_m_claim c
           JOIN ssdb_integration.lr_strategy.td_map_cell x ON x.zip_code = c.zip_code AND x.need = c.need
           LEFT JOIN ssdb_integration.lr_strategy.tmp_m_hold h
                  ON h.source = c.source AND h.nm = c.nm AND h.source = x.source AND h.zip_code = x.zip_code AND h.ch = x.dist_ch
           GROUP BY c.source, c.nm, x.source),
     ht AS (SELECT h.source, h.nm, SUM(x.mm_opp) AS opp_held_today
            FROM ssdb_integration.lr_strategy.tmp_m_hold h
            JOIN ssdb_integration.lr_strategy.tmp_m_cell x ON x.source = h.source AND x.zip_code = h.zip_code AND x.dist_ch = h.ch
            GROUP BY h.source, h.nm),
     az AS (SELECT source, nm, COUNT(*) AS n_area_zips FROM ssdb_integration.lr_strategy.tmp_m_area GROUP BY source, nm),
     hs AS (SELECT DISTINCT source, nm FROM ssdb_integration.lr_strategy.tmp_m_hold)
SELECT r.source, r.wholesaler, r.kept, r.role, CASE WHEN hs.nm IS NULL THEN 0 ELSE 1 END AS in_territories, e.source AS est_source,
       COALESCE(az.n_area_zips, 0) AS n_area_zips, COALESCE(b.opp_claimed, 0) AS opp_claimed, COALESCE(b.opp_sole, 0) AS opp_sole,
       COALESCE(b.opp_claimed, 0) - COALESCE(b.opp_sole, 0) AS opp_shared,
       CASE WHEN e.source = r.source THEN COALESCE(ht.opp_held_today, 0) END AS opp_held_today,
       CASE WHEN e.source = r.source THEN COALESCE(b.opp_kept, 0) END AS opp_kept,
       CASE WHEN e.source = r.source THEN COALESCE(ht.opp_held_today, 0) - COALESCE(b.opp_kept, 0) END AS opp_released,
       CASE WHEN e.source = r.source THEN COALESCE(b.opp_claimed, 0) - COALESCE(b.opp_kept, 0) END AS opp_gained
FROM ssdb_integration.lr_strategy.tmp_m_roster r
CROSS JOIN (SELECT DISTINCT source FROM ssdb_integration.lr_strategy.tmp_m_opp) e
LEFT JOIN b ON b.source = r.source AND b.nm = r.nm AND b.est_source = e.source
LEFT JOIN ht ON ht.source = r.source AND ht.nm = r.nm
LEFT JOIN az ON az.source = r.source AND az.nm = r.nm
LEFT JOIN hs ON hs.source = r.source AND hs.nm = r.nm;

--8 the one result
WITH
ro AS (SELECT r.*, CASE WHEN hs.nm IS NULL THEN 0 ELSE 1 END AS in_terr, CASE WHEN az.nm IS NULL THEN 0 ELSE 1 END AS has_area
      FROM ssdb_integration.lr_strategy.tmp_m_roster r
      LEFT JOIN (SELECT DISTINCT source, nm FROM ssdb_integration.lr_strategy.tmp_m_hold) hs ON hs.source = r.source AND hs.nm = r.nm
      LEFT JOIN (SELECT DISTINCT source, nm FROM ssdb_integration.lr_strategy.tmp_m_area) az ON az.source = r.source AND az.nm = r.nm),
rc AS (SELECT source,
              SUM(n_rows) AS c01, COUNT(CASE WHEN kept = 'Y' THEN 1 END) AS c02, COUNT(CASE WHEN kept = 'N' THEN 1 END) AS c03,
              COUNT(CASE WHEN kept = '' THEN 1 END) AS c04, COUNT(CASE WHEN kept = '?' THEN 1 END) AS c05,
              COUNT(CASE WHEN role NOT IN ('NATIONAL', 'WH', 'FI', 'WIFI', '') THEN 1 END) AS c06,
              COUNT(CASE WHEN n_rows > 1 THEN 1 END) AS c07, COUNT(CASE WHEN kept = 'Y' AND role = '' THEN 1 END) AS c08,
              COUNT(CASE WHEN kept = 'Y' AND role <> '' AND in_terr = 0 THEN 1 END) AS c09,
              COUNT(CASE WHEN kept = 'Y' AND role <> '' AND in_terr = 1 AND has_area = 0 THEN 1 END) AS c10
       FROM ro GROUP BY source)
SELECT 'ROSTER' AS section, rc.source, v.name AS k1, CAST(NULL AS VARCHAR) AS k2,
       CASE v.i WHEN 1 THEN rc.c01 WHEN 2 THEN rc.c02 WHEN 3 THEN rc.c03 WHEN 4 THEN rc.c04 WHEN 5 THEN rc.c05 WHEN 6 THEN rc.c06
                WHEN 7 THEN rc.c07 WHEN 8 THEN rc.c08 WHEN 9 THEN rc.c09 ELSE rc.c10 END AS n,
       CAST(NULL AS DOUBLE) AS mm_opp, v.mbz AS must_be_zero
FROM rc CROSS JOIN (SELECT i, name, mbz FROM (VALUES
       (1, '01 ROWS', 0), (2, '02 KEPT Y', 0), (3, '03 KEPT N', 0), (4, '04 KEPT BLANK (NOT DECIDED)', 0),
       (5, '05 KEPT NOT Y, N OR BLANK', 1), (6, '06 ROLE NOT NATIONAL, WH, FI, WIFI OR BLANK', 1), (7, '07 WHOLESALER ON 2+ ROWS', 1),
       (8, '08 KEPT WITH NO ROLE (OUTSIDE THE MAIN MAP)', 0), (9, '09 KEPT WITH A ROLE, NAME NOT IN THE TERRITORIES (NO AREA)', 0),
       (10, '10 KEPT WITH A ROLE, HOLDS NO WH OR FI ZIP (NO AREA)', 0)) AS t (i, name, mbz)) v
UNION ALL
SELECT 'ROSTER', h.source, '11 WH OR FI HOLDERS NOT ON THE ROSTER (NOT KEPT)', NULL,
       COUNT(DISTINCT CASE WHEN r.nm IS NULL THEN h.nm END), NULL, 0
FROM ssdb_integration.lr_strategy.tmp_m_hold h
LEFT JOIN ssdb_integration.lr_strategy.tmp_m_roster r ON r.source = h.source AND r.nm = h.nm
WHERE h.ch IN ('WH', 'FI') GROUP BY h.source
UNION ALL
SELECT 'ROLES', source, role, NULL, COUNT(*), NULL, 0 FROM ro WHERE kept = 'Y' AND role <> '' GROUP BY source, role
UNION ALL
SELECT 'CAPTURE', source, need,
       CASE WHEN status = 'GAP' THEN 'GAP: ' || gap_reason WHEN status = 'CAPTURED' THEN '1 CLAIMANT: ' || captured_role
            WHEN n_claim_firms = 1 THEN '2+ CLAIMANTS, ONE FIRM' ELSE '2+ CLAIMANTS, 2+ FIRMS' END, COUNT(*), SUM(mm_opp), 0
FROM ssdb_integration.lr_strategy.td_map_cell
GROUP BY source, need,
         CASE WHEN status = 'GAP' THEN 'GAP: ' || gap_reason WHEN status = 'CAPTURED' THEN '1 CLAIMANT: ' || captured_role
              WHEN n_claim_firms = 1 THEN '2+ CLAIMANTS, ONE FIRM' ELSE '2+ CLAIMANTS, 2+ FIRMS' END
UNION ALL
SELECT 'FINE CHANNEL', source, new_dist, need, COUNT(*), SUM(mm_opp), 0
FROM ssdb_integration.lr_strategy.td_map_cell GROUP BY source, new_dist, need
UNION ALL
SELECT 'TIE', o.source, 'TD_MAP_CELL MINUS THE UNION, MAIN MAP (N 1 = THEY DIFFER)', NULL,
       CASE WHEN ABS(COALESCE(c.opp, 0) - o.opp) > 0.5 OR COALESCE(c.n, 0) <> o.n THEN 1 ELSE 0 END, COALESCE(c.opp, 0) - o.opp, 1
FROM (SELECT source, SUM(mm_opp) AS opp, COUNT(*) AS n FROM ssdb_integration.lr_strategy.tmp_m_opp GROUP BY source) o
LEFT JOIN (SELECT source, SUM(mm_opp) AS opp, COUNT(*) AS n FROM ssdb_integration.lr_strategy.td_map_cell GROUP BY source) c
       ON c.source = o.source
ORDER BY section, source, k1, k2;
