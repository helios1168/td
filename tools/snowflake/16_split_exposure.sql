-- How often the split of a target channel's opportunity over a firm's DIST_CHs reaches people:
-- per firm, (zip, target channel) cells by how many DIST_CHs and how many CLEAN_IDs hold them.
-- Only several_dist_ch_several_people depends on the split rule; elsewhere one person gets it all.
WITH
m AS (SELECT DISTINCT SOURCE, DIST_CH, CHANNEL
      FROM ssdb_integration.lr_strategy.data_withnewchannel_union_w_joinkeys),
t AS (SELECT DISTINCT SOURCE, CLEAN_ID, ZIP_CODE, CHANNEL AS DIST_CH
      FROM ssdb_integration.lr_strategy.territories),
c AS (SELECT t.SOURCE, t.ZIP_CODE, m.CHANNEL AS target_channel,
             COUNT(DISTINCT t.DIST_CH) AS dist_ch_held, COUNT(DISTINCT t.CLEAN_ID) AS people
      FROM t JOIN m ON m.SOURCE = t.SOURCE AND m.DIST_CH = t.DIST_CH
      GROUP BY t.SOURCE, t.ZIP_CODE, m.CHANNEL),
f AS (SELECT SOURCE, 'firm_' || DENSE_RANK() OVER (ORDER BY SOURCE) AS firm_label
      FROM (SELECT DISTINCT SOURCE FROM c) x)
SELECT f.firm_label,
       COUNT(*)                                        AS zip_target_cells,
       COUNT_IF(dist_ch_held = 1)                      AS one_dist_ch_held,
       COUNT_IF(dist_ch_held > 1 AND people = 1)       AS several_dist_ch_one_person,
       COUNT_IF(dist_ch_held > 1 AND people > 1)       AS several_dist_ch_several_people
FROM c JOIN f ON f.SOURCE = c.SOURCE
GROUP BY f.firm_label
ORDER BY f.firm_label;
