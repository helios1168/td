-- Run after 01_build_safe.sql, in the same session.  Checks 1-3 must all return 0 before export.

-- 1. No real wholesaler or firm id survives.
SELECT COUNT(*) AS real_wholesalers
FROM scratch.td_safe s JOIN (SELECT DISTINCT wholesaler FROM raw) r ON s.wholesaler = r.wholesaler;
SELECT COUNT(*) AS real_firms
FROM scratch.td_safe s JOIN (SELECT DISTINCT firm FROM raw) r ON s.firm = r.firm;

-- 2. No filler key survives in any value, in any case.
SELECT COUNT(*) AS filler_left
FROM scratch.td_safe s JOIN filler_keys f
  ON CONTAINS(LOWER(CONCAT_WS('|', COALESCE(s.zip_code, ''), COALESCE(s.channel, ''),
                              COALESCE(s.firm, ''), COALESCE(s.wholesaler, ''))), LOWER(f.key));

-- 3. Same grain as the source.
SELECT (SELECT COUNT(*) FROM raw) - (SELECT COUNT(*) FROM scratch.td_safe) AS row_diff;

-- 4. Informational: (zip, channel, wholesaler) duplicates the shuffle made.
SELECT COUNT(*) AS dup_keys
FROM (SELECT zip_code, channel, wholesaler FROM scratch.td_safe
      GROUP BY 1, 2, 3 HAVING COUNT(*) > 1);

-- 5. By eye: no channel name names anything that may not leave.
SELECT channel, COUNT(*) AS n_rows FROM scratch.td_safe GROUP BY channel ORDER BY channel;

-- Export, then in SnowSQL: GET @~/td_safe.csv.gz file://<local dir>/;
-- or use Snowsight's "Download results" on SELECT * FROM scratch.td_safe.
COPY INTO @~/td_safe.csv.gz FROM scratch.td_safe
  FILE_FORMAT = (TYPE = CSV COMPRESSION = GZIP FIELD_OPTIONALLY_ENCLOSED_BY = '"')
  HEADER = TRUE SINGLE = TRUE OVERWRITE = TRUE;
