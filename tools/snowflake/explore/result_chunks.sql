use role rl_ssdb_Integration_Lr_Strategy_Rw;
use database ssdb_Integration;
use schema lr_strategy;

--Download a large result in parts of about 1 MB, without running its script again.  Reads only the cached result
--(RESULT_SCAN, kept 24 hours).
--1. Paste the script's query ID from Query History (not LAST_QUERY_ID(): the use lines above are queries too), and see
--how many parts.
SET q = '<query id>';
SELECT COUNT(*) AS n_rows, CEIL(COUNT(*) / 20000) AS n_parts FROM TABLE(RESULT_SCAN($q));

--2. Set part to 1, run, download as CSV, then 2, and so on to n_parts.  The ORDER BY is a total order of
--02_model_extract.sql's rows, so every row is in exactly one part.
SET part = 1;
SELECT * FROM TABLE(RESULT_SCAN($q))
QUALIFY CEIL(ROW_NUMBER() OVER (ORDER BY layer, source, name, zip_code, state, dist_ch, new_dist, channel, holder) / 20000)
        = $part;
