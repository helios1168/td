use role rl_ssdb_Integration_Lr_Strategy_Rw;
use database ssdb_Integration;
use schema lr_strategy;

--The masked export of 04_assigned_coverage.sql's four tables, so the maps can be drawn outside Snowflake.  One Run All file, one
--result set, read only: it creates and changes nothing.  Set the five table names below, nothing else.  Download the result as CSV
--into $TD_REPO/data/safe/ and run map_extract.py on it.
--No wholesaler name and no sales value leaves.  A wholesaler is the surrogate R<n> of the holder key td_holder_key (02_model_extract.sql
--builds and extends it, this file only reads it, never inserts into or creates it): the key is by SOURCE x holder id, the id being
--UUID_STRING over the namespace below of the name in upper case with each run of white space as one space and trimmed, the rule of
--02_model_extract.sql.  TD_MAP_PIECE.WHOLESALER and TD_MAP_WHOLESALER.WHOLESALER are raw spellings, normalized the same way.
--This file is the masking boundary and fails closed: it does not rely on 04_assigned_coverage.sql's checks having been cleared.  The
--owner-typed columns leave only as safe projections, never verbatim: ROLE is NATIONAL, WH, FI, WIFI or blank, else INVALID.  KEPT is
--Y, N, ? or blank, else INVALID.  STATE is two capital letters, else NULL.  ASSIGNED_STATES and STATES keep, in order and single
--spaced, the space separated tokens of two capital letters and drop every other token (REGEXP_REPLACE on the string with each space
--doubled, which removes a whole token at a time, both Snowflake and DuckDB run it).  Every other column is the dataset's own category
--(SOURCE, channels, NEW_DIST, TERR_CHANNEL, CELL STATE) or a number, or 04's CASE value (HOLDER_STATUS), none typed by the owner.
--SALES_MAIN and SALES_MAIN_IN_OWN_ZIPS are not read.  Run 02_model_extract.sql first: a wholesaler with no key row is a MUST_BE_ZERO check.
--Result under LAYER, all layers share the column list (NULL where a layer has no such column):
--  PIECE       SOURCE, HOLDER, KEPT, ROLE, ZIP_CODE, STATE, TERR_CHANNEL, PIECE_IN_ROLE, IN_ASSIGNED_STATE, N_ROLE_HOLDERS, N_ROLE_FIRMS:
--              TD_MAP_PIECE for the pieces with TERR_CHANNEL WH or FI, or of a wholesaler with KEPT Y (the file stays small).
--  CELL        EST_SOURCE, ZIP_CODE, STATE, DIST_CH, NEW_DIST, CHANNEL, NEW_TERR_CHANNEL, FIT_CHANNEL, MM_OPP, N_HOLDERS, HOLDER_STATUS:
--              TD_MAP_CELL as it is.
--  ZIP         ZIP_CODE, ROLE, N_ROLE_HOLDERS, N_ROLE_FIRMS: TD_MAP_ZIP, ROLE projected.
--  WHOLESALER  SOURCE, HOLDER, KEPT, ROLE, ASSIGNED_STATES, EST_SOURCE, N_ZIPS, N_ZIPS_IN_ROLE, STATES, OPP_MAIN, OPP_IN_ROLE,
--              OPP_OUT_OF_ROLE, OPP_OVERLAP, OPP_IN_ASSIGNED_STATES: TD_MAP_WHOLESALER without the sales columns.
--  CHECKS      SOURCE, NAME, VALUE, MUST_BE_ZERO.  MUST_BE_ZERO = 1 rows must have VALUE 0: map_extract.py refuses the file otherwise.
--              Wholesalers with no key row, key HOLDER_N duplicated, the exported rows whose ROLE or KEPT came out INVALID, whose STATE
--              was dropped, or whose ASSIGNED_STATES or STATES lost a token (counts only, never the value), and (information) the rows
--              of each layer.
--The result SELECT must stay the last statement, Run All shows one result.

SET piece_tbl  = 'ssdb_integration.lr_strategy.td_map_piece';
SET cell_tbl   = 'ssdb_integration.lr_strategy.td_map_cell';
SET zip_tbl    = 'ssdb_integration.lr_strategy.td_map_zip';
SET wh_tbl     = 'ssdb_integration.lr_strategy.td_map_wholesaler';
SET holder_tbl = 'ssdb_integration.lr_strategy.td_holder_key';

WITH
hk AS (SELECT source, holder_id, holder_n FROM IDENTIFIER($holder_tbl)),
hd AS (SELECT holder_n, COUNT(*) AS n FROM hk GROUP BY holder_n),
pc AS (SELECT p.source, p.nm, k.holder_n, p.kept, p.role, p.zip_code, p.state, p.terr_channel, p.piece_in_role, p.in_assigned_state,
              p.n_role_holders, p.n_role_firms, p.kept_bad, p.role_bad, p.state_bad
       FROM (SELECT source, nm, CASE WHEN nm IS NULL THEN NULL ELSE UUID_STRING('6ba7b810-9dad-11d1-80b4-00c04fd430c8', nm) END AS hid,
                    CASE WHEN COALESCE(kept, '') IN ('Y', 'N', '?', '') THEN kept ELSE 'INVALID' END AS kept,
                    CASE WHEN COALESCE(role, '') IN ('NATIONAL', 'WH', 'FI', 'WIFI', '') THEN role ELSE 'INVALID' END AS role,
                    zip_code, CASE WHEN REGEXP_LIKE(state, '^[A-Z]{2}$') THEN state END AS state, terr_channel, piece_in_role,
                    in_assigned_state, n_role_holders, n_role_firms, kept_bad, role_bad, state_bad
             FROM (SELECT source, NULLIF(UPPER(TRIM(REGEXP_REPLACE(TRIM(wholesaler), '\\s+', ' '))), '') AS nm,
                          kept, role, zip_code, state, terr_channel, piece_in_role, in_assigned_state, n_role_holders, n_role_firms,
                          CASE WHEN COALESCE(kept, '') IN ('Y', 'N', '?', '') THEN 0 ELSE 1 END AS kept_bad,
                          CASE WHEN COALESCE(role, '') IN ('NATIONAL', 'WH', 'FI', 'WIFI', '') THEN 0 ELSE 1 END AS role_bad,
                          CASE WHEN state IS NOT NULL AND NOT REGEXP_LIKE(state, '^[A-Z]{2}$') THEN 1 ELSE 0 END AS state_bad
                   FROM IDENTIFIER($piece_tbl))) p
       LEFT JOIN hk k ON k.source = p.source AND k.holder_id = p.hid),
wc AS (SELECT w.source, w.nm, k.holder_n, w.kept, w.role, w.assigned_states, w.est_source, w.n_zips, w.n_zips_in_role, w.states,
              w.opp_main, w.opp_in_role, w.opp_out_of_role, w.opp_overlap, w.opp_in_assigned_states, w.kept_bad, w.role_bad,
              CASE WHEN w.assigned_states <> w.a_raw THEN 1 ELSE 0 END AS as_cut, CASE WHEN w.states <> w.s_raw THEN 1 ELSE 0 END AS st_cut
       FROM (SELECT source, nm, CASE WHEN nm IS NULL THEN NULL ELSE UUID_STRING('6ba7b810-9dad-11d1-80b4-00c04fd430c8', nm) END AS hid,
                    CASE WHEN COALESCE(kept, '') IN ('Y', 'N', '?', '') THEN kept ELSE 'INVALID' END AS kept,
                    CASE WHEN COALESCE(role, '') IN ('NATIONAL', 'WH', 'FI', 'WIFI', '') THEN role ELSE 'INVALID' END AS role,
                    TRIM(REGEXP_REPLACE(REGEXP_REPLACE(REPLACE(a_raw, ' ', '  '), '(^| )([^ ]|[^ ]{3,}|[^A-Z ][^ ]|[A-Z][^A-Z ])( |$)', ''), ' +', ' ')) AS assigned_states, est_source, n_zips, n_zips_in_role,
                    TRIM(REGEXP_REPLACE(REGEXP_REPLACE(REPLACE(s_raw, ' ', '  '), '(^| )([^ ]|[^ ]{3,}|[^A-Z ][^ ]|[A-Z][^A-Z ])( |$)', ''), ' +', ' ')) AS states, opp_main, opp_in_role, opp_out_of_role,
                    opp_overlap, opp_in_assigned_states, kept_bad, role_bad, a_raw, s_raw
             FROM (SELECT source, NULLIF(UPPER(TRIM(REGEXP_REPLACE(TRIM(wholesaler), '\\s+', ' '))), '') AS nm,
                          kept, role, est_source, n_zips, n_zips_in_role, opp_main, opp_in_role,
                          opp_out_of_role, opp_overlap, opp_in_assigned_states,
                          CASE WHEN COALESCE(kept, '') IN ('Y', 'N', '?', '') THEN 0 ELSE 1 END AS kept_bad,
                          CASE WHEN COALESCE(role, '') IN ('NATIONAL', 'WH', 'FI', 'WIFI', '') THEN 0 ELSE 1 END AS role_bad,
                          REGEXP_REPLACE(TRIM(COALESCE(assigned_states, '')), ' +', ' ') AS a_raw, REGEXP_REPLACE(TRIM(COALESCE(states, '')), ' +', ' ') AS s_raw
                   FROM IDENTIFIER($wh_tbl))) w
       LEFT JOIN hk k ON k.source = w.source AND k.holder_id = w.hid),
ck AS (SELECT source, 'PIECE ROWS WITH ROLE EXPORTED AS INVALID' AS name, SUM(role_bad) AS value FROM pc WHERE terr_channel IN ('WH', 'FI') OR kept = 'Y' GROUP BY source
       UNION ALL
       SELECT source, 'PIECE ROWS WITH KEPT EXPORTED AS INVALID', SUM(kept_bad) FROM pc WHERE terr_channel IN ('WH', 'FI') OR kept = 'Y' GROUP BY source
       UNION ALL
       SELECT source, 'PIECE ROWS WITH STATE REMOVED', SUM(state_bad) FROM pc WHERE terr_channel IN ('WH', 'FI') OR kept = 'Y' GROUP BY source
       UNION ALL
       SELECT source, 'WHOLESALER ROWS WITH ROLE EXPORTED AS INVALID', SUM(role_bad) FROM wc GROUP BY source
       UNION ALL
       SELECT source, 'WHOLESALER ROWS WITH KEPT EXPORTED AS INVALID', SUM(kept_bad) FROM wc GROUP BY source
       UNION ALL
       SELECT source, 'WHOLESALER ROWS WITH ASSIGNED_STATES TOKENS REMOVED', SUM(as_cut) FROM wc GROUP BY source
       UNION ALL
       SELECT source, 'WHOLESALER ROWS WITH STATES TOKENS REMOVED', SUM(st_cut) FROM wc GROUP BY source
       UNION ALL
       SELECT CAST(NULL AS VARCHAR), 'ZIP ROWS WITH ROLE EXPORTED AS INVALID',
              COUNT(CASE WHEN COALESCE(role, '') NOT IN ('NATIONAL', 'WH', 'FI', 'WIFI', '') THEN 1 END)
       FROM IDENTIFIER($zip_tbl))
--PIECE
SELECT 'PIECE' AS layer, source, CAST(NULL AS VARCHAR) AS est_source, 'R' || holder_n AS holder, kept, role,
       CAST(NULL AS VARCHAR) AS assigned_states, zip_code, state, terr_channel, piece_in_role, in_assigned_state,
       CAST(NULL AS VARCHAR) AS dist_ch, CAST(NULL AS VARCHAR) AS new_dist, CAST(NULL AS VARCHAR) AS channel,
       CAST(NULL AS VARCHAR) AS new_terr_channel, CAST(NULL AS VARCHAR) AS fit_channel, CAST(NULL AS DOUBLE) AS mm_opp,
       CAST(NULL AS INTEGER) AS n_holders, CAST(NULL AS VARCHAR) AS holder_status, n_role_holders, n_role_firms,
       CAST(NULL AS INTEGER) AS n_zips, CAST(NULL AS INTEGER) AS n_zips_in_role, CAST(NULL AS VARCHAR) AS states,
       CAST(NULL AS DOUBLE) AS opp_main, CAST(NULL AS DOUBLE) AS opp_in_role, CAST(NULL AS DOUBLE) AS opp_out_of_role,
       CAST(NULL AS DOUBLE) AS opp_overlap, CAST(NULL AS DOUBLE) AS opp_in_assigned_states, CAST(NULL AS VARCHAR) AS name,
       CAST(NULL AS DOUBLE) AS value, CAST(NULL AS INTEGER) AS must_be_zero
FROM pc WHERE terr_channel IN ('WH', 'FI') OR kept = 'Y'
UNION ALL
--CELL
SELECT 'CELL', NULL, est_source, NULL, NULL, NULL, NULL, zip_code, state, NULL, NULL, NULL, dist_ch, new_dist, channel,
       new_terr_channel, fit_channel, mm_opp, n_holders, holder_status, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL,
       NULL, NULL, NULL, NULL
FROM IDENTIFIER($cell_tbl)
UNION ALL
--ZIP
SELECT 'ZIP', NULL, NULL, NULL, NULL, CASE WHEN COALESCE(role, '') IN ('NATIONAL', 'WH', 'FI', 'WIFI', '') THEN role ELSE 'INVALID' END, NULL, zip_code, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL,
       NULL, n_role_holders, n_role_firms, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL
FROM IDENTIFIER($zip_tbl)
UNION ALL
--WHOLESALER
SELECT 'WHOLESALER', source, est_source, 'R' || holder_n, kept, role, assigned_states, NULL, NULL, NULL, NULL, NULL, NULL,
       NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, n_zips, n_zips_in_role, states, opp_main, opp_in_role,
       opp_out_of_role, opp_overlap, opp_in_assigned_states, NULL, NULL, NULL
FROM wc
UNION ALL
--CHECKS
SELECT 'CHECKS', source, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL,
       NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL,
       'WHOLESALERS WITH NO KEY ROW (RUN 02_model_extract.sql FIRST)',
       COUNT(DISTINCT CASE WHEN holder_n IS NULL THEN COALESCE(nm, '') END), 1
FROM (SELECT source, nm, holder_n FROM pc UNION SELECT source, nm, holder_n FROM wc) GROUP BY source
UNION ALL
SELECT 'CHECKS', hk.source, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL,
       NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 'KEY HOLDER_N DUPLICATED',
       COUNT(CASE WHEN hd.n > 1 THEN 1 END), 1
FROM hk JOIN hd ON hd.holder_n = hk.holder_n GROUP BY hk.source
UNION ALL
SELECT 'CHECKS', source, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL,
       NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 'ROWS IN THE PIECE LAYER', COUNT(*), 0
FROM pc WHERE terr_channel IN ('WH', 'FI') OR kept = 'Y' GROUP BY source
UNION ALL
SELECT 'CHECKS', est_source, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL,
       NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 'ROWS IN THE CELL LAYER', COUNT(*), 0
FROM IDENTIFIER($cell_tbl) GROUP BY est_source
UNION ALL
SELECT 'CHECKS', CAST(NULL AS VARCHAR), NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL,
       NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 'ROWS IN THE ZIP LAYER', COUNT(*),
       0
FROM IDENTIFIER($zip_tbl)
UNION ALL
SELECT 'CHECKS', source, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL,
       NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 'ROWS IN THE WHOLESALER LAYER', COUNT(*), 0
FROM wc GROUP BY source
UNION ALL
SELECT 'CHECKS', source, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, name, value, 1
FROM ck
ORDER BY layer, source, est_source, zip_code, holder, terr_channel, dist_ch, new_dist, channel, role, name;
