-- Why territory rows find no channel mapping.  Run in the same worksheet session as
-- 08_rank_end_to_end.sql, after Part 0 (it reads ssdb_integration.lr_strategy.rank_os and ssdb_integration.lr_strategy.rank_terr_src).
-- Lists every territory CHANNEL value beside every sales DIST_CH value, per firm (firm_1 / firm_2):
--   matches_ignoring_case_space = true   -> case or stray spaces: UPPER(TRIM()) both sides in Part 0
--   matches_target_channel      = true   -> that firm's territories use target names: map to themselves
--   all false, a DIST_CH value spelled differently, or a channel with no sales this year
--                                         -> a hand-written crosswalk in Part 0
WITH
f AS (SELECT firm, 'firm_' || DENSE_RANK() OVER (ORDER BY firm) AS firm_label
      FROM (SELECT firm FROM ssdb_integration.lr_strategy.rank_terr_src UNION SELECT firm FROM ssdb_integration.lr_strategy.rank_os) x),
dist AS (SELECT DISTINCT firm, original_channel FROM ssdb_integration.lr_strategy.rank_os),
dist_norm AS (SELECT DISTINCT firm, UPPER(TRIM(original_channel)) AS k FROM ssdb_integration.lr_strategy.rank_os),
tgt AS (SELECT DISTINCT firm, channel FROM ssdb_integration.lr_strategy.rank_os),
tc AS (SELECT firm, original_channel, COUNT(*) AS n_rows FROM ssdb_integration.lr_strategy.rank_terr_src GROUP BY 1, 2)
SELECT f.firm_label, 'territory CHANNEL' AS column_, tc.original_channel AS value_, tc.n_rows,
       d.firm IS NOT NULL  AS matches_dist_ch,
       dn.firm IS NOT NULL AS matches_ignoring_case_space,
       g.firm IS NOT NULL  AS matches_target_channel
FROM tc JOIN f ON f.firm = tc.firm
LEFT JOIN dist d       ON d.firm = tc.firm AND d.original_channel = tc.original_channel
LEFT JOIN dist_norm dn ON dn.firm = tc.firm AND dn.k = UPPER(TRIM(tc.original_channel))
LEFT JOIN tgt g        ON g.firm = tc.firm AND g.channel = tc.original_channel
UNION ALL
SELECT f.firm_label, 'sales DIST_CH', o.original_channel, COUNT(*), NULL, NULL, NULL
FROM ssdb_integration.lr_strategy.rank_os o JOIN f ON f.firm = o.firm GROUP BY 1, 2, 3
ORDER BY 1, 2 DESC, 4 DESC;
