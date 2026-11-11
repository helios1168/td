--The census boundary tables (GEO_ID, FULLY_QUALIFIED_ID, GEO_NAME, GEO_BOUNDARY GEOGRAPHY): vintage, ID format, size
--and validity.  Reads only these four tables, public data.  Edit the four SET lines to the real names, Run All, send the
--one result.  GEO_BOUNDARY itself is never selected (it would print GeoJSON).
SET zcta_tbl = '<db.schema.zcta table>';
SET cbsa_tbl = '<db.schema.metro cbsa table>';
SET csa_tbl  = '<db.schema.csa table>';
SET div_tbl  = '<db.schema.divisions table>';

WITH
t AS (SELECT 'ZCTA' AS tbl, * FROM IDENTIFIER($zcta_tbl)
      UNION ALL SELECT 'CBSA', * FROM IDENTIFIER($cbsa_tbl)
      UNION ALL SELECT 'CSA', * FROM IDENTIFIER($csa_tbl)
      UNION ALL SELECT 'DIVISION', * FROM IDENTIFIER($div_tbl)),
s AS (SELECT tbl, geo_id, fully_qualified_id, geo_name,
             ROW_NUMBER() OVER (PARTITION BY tbl ORDER BY geo_id) AS r FROM t)
SELECT 'SIZE' AS part, tbl, COUNT(*) AS n_rows, COUNT(DISTINCT geo_id) AS n_geo_id,
       COUNT(CASE WHEN geo_boundary IS NULL THEN 1 END) AS n_null_boundary,
       COUNT(CASE WHEN NOT ST_ISVALID(geo_boundary) THEN 1 END) AS n_invalid,
       MAX(ST_NPOINTS(geo_boundary)) AS max_points, SUM(ST_NPOINTS(geo_boundary)) AS sum_points,
       MIN(geo_id) AS geo_id, MAX(geo_id) AS fully_qualified_id, NULL AS geo_name
FROM t GROUP BY tbl
UNION ALL
SELECT 'SAMPLE', tbl, NULL, NULL, NULL, NULL, NULL, NULL, geo_id, fully_qualified_id, geo_name
FROM s WHERE r <= 3
ORDER BY part, tbl, geo_id;
