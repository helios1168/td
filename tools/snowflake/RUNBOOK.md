# Wholesaler ranking in Snowflake: runbook

How to rank every wholesaler of both firms on one merged-company scale, so that a generalist who
splits time across channels is not penalised against a channelized specialist. Everything here runs
in one Snowsight worksheet session at work. The query files are `04_territory_profile.sql` and
`05_rank_territory.sql` beside this file; their full text is copied at the end.

## The method

Volume within a channel measures sales × time spent in the channel, so specialists win by design. The
ranking uses a rate instead:

| term | definition |
|---|---|
| cell | one (zip, channel), in the channelized firm's channels |
| channel rate | all credited sales ÷ all territory opportunity in the channel, both firms pooled |
| expected | a wholesaler's territory opportunity × the channel rate |
| credited | sales in the territory + `out_credit` × sales outside it (decided: outside sales count, `out_credit` = 1) |
| index | (credited + prior) ÷ (expected + prior); 1.0 = merged-company average |
| prior | `shrink_cells` typical territory cells at the channel rate; keeps a thin territory from an extreme rank |

`index_overall` (all the wholesaler's channels) decides who stays; `perf_index` by channel decides
which channel. Opportunity sits on one firm's rows and is NULL on the other's; it is summed per cell
across firms, so each cell counts it once and both firms are measured against it.

## Step 1. Create the five inputs

Replace every `<...>`. These views are the only place real table and column names appear.

```sql
-- a) Sales and opportunity, long across firms; channel = the distribution-company-level code
CREATE OR REPLACE TEMPORARY VIEW raw AS
SELECT <zip>               AS zip_code,     -- VARCHAR, 5 characters
       <firm>              AS firm,
       <wholesaler>        AS wholesaler,
       <distribution code> AS channel,
       <opportunity>       AS opportunity,  -- on one firm's rows, NULL on the other's
       <sales>             AS sales
FROM <sales table>;

-- b) Distribution-company code -> the channelized firm's channels, as the sales table defines it
CREATE OR REPLACE TEMPORARY VIEW channel_map AS
SELECT DISTINCT <firm> AS firm, <distribution code> AS source_channel, <target channel> AS channel
FROM <sales table>;

-- c) Each firm's original channel name -> the target channels, from the same table
CREATE OR REPLACE TEMPORARY VIEW territory_channel_map AS
SELECT DISTINCT <firm> AS firm, <original channel> AS territory_channel, <target channel> AS channel
FROM <sales table>;
-- if the sales table has no original channel name, write this by hand:
--   SELECT * FROM VALUES ('<firm>', '<original channel>', '<target channel>'), ...
--     AS v(firm, territory_channel, channel)

-- d) Territories, expanded to target channels
CREATE OR REPLACE TEMPORARY VIEW territory AS
SELECT DISTINCT t.<firm> AS firm, t.<wholesaler> AS wholesaler, t.<zip> AS zip_code, tm.channel
FROM <territory table> t
JOIN territory_channel_map tm ON tm.firm = t.<firm> AND tm.territory_channel = t.<original channel>;

-- e) Vacancy sentinels (delete the INSERT if there are none)
CREATE OR REPLACE TEMPORARY TABLE filler_keys (key VARCHAR);
INSERT INTO filler_keys VALUES ('<filler key>');
```

An original channel that maps to several target channels puts the wholesaler's zip in every one of
them: their territory covers all of those distribution companies, so all that opportunity is expected
of them. Several original channels that map to one target channel collapse into it.

## Step 2. Checks: each must return 0

Both mappings are read off the sales table, so they cover only codes and channels that appear in it.
A territory row in a channel with no sales rows at all fails the second territory check below.

```sql
-- each distribution code maps to exactly one target channel; a code with two would duplicate its
-- rows in the join and count their sales and opportunity twice
SELECT COUNT(*) FROM (
  SELECT firm, source_channel FROM channel_map GROUP BY 1, 2 HAVING COUNT(*) > 1);

-- no NULL target channel (those rows would drop out of every join)
SELECT COUNT(*) FROM channel_map WHERE channel IS NULL;

-- every raw row maps to a target channel
SELECT COUNT(*) FROM raw r
LEFT JOIN channel_map cm ON cm.firm = r.firm AND cm.source_channel = r.channel
WHERE cm.channel IS NULL;

-- every territory row's original channel maps to a target channel
SELECT COUNT(*) FROM <territory table> t
LEFT JOIN territory_channel_map tm ON tm.firm = t.<firm> AND tm.territory_channel = t.<original channel>
WHERE tm.channel IS NULL;

-- no cell carries opportunity on two firms (it would count twice)
SELECT COUNT(*) FROM (
  SELECT r.zip_code, cm.channel FROM raw r
  JOIN channel_map cm ON cm.firm = r.firm AND cm.source_channel = r.channel
  WHERE COALESCE(r.opportunity, 0) <> 0
  GROUP BY 1, 2 HAVING COUNT(DISTINCT r.firm) > 1);
```

Then look at this list by eye. A row is allowed, but each must be a split you expect:

```sql
-- original channels whose distribution companies split across target channels
SELECT firm, territory_channel, COUNT(*) AS n_target
FROM territory_channel_map GROUP BY 1, 2 HAVING COUNT(*) > 1;
```

## Step 3. Profile (`04_territory_profile.sql`)

Run it and read these rows; the output is counts and per-firm percentages only, firms shown as
`firm_1` / `firm_2`, safe to share.

| row | what to look for |
|---|---|
| `opp_rows_nonzero` | only the firm that carries opportunity appears |
| `territory_cells_without_opp`, `pct_sales_in_cells_without_opp` | under about 1% of a firm's sales is fine; above that, fill in those cells' opportunity at the source first, or their sales become free credit |
| `pct_sales_by_where_sold` | the gap between the firms' outside-territory shares; a few points is negligible, a large gap argues for `out_credit` = 0.5 |
| `wholesalers_with_sales_no_territory`, `wholesalers_with_territory_no_sales` | people missing from one side |

## Step 4. Rank (`05_rank_territory.sql`)

Settings at the top: `out_credit` (1.0) and `shrink_cells` (1.0). One row per wholesaler × channel:

| column | use |
|---|---|
| `rank_overall`, `index_overall` | who stays |
| `rank_in_channel`, `perf_index` | which channel |
| `index_territory_only`, `out_share` | how much outside sales moved the person |
| `channel_weight` | the channel's share of the person's expected sales: their time split, by opportunity |
| `terr_cells`, `cells_with_sales`, `opp`, `expected`, `sales_in`, `sales_out`, `sales_orphan`, `credited` | the working |

## Known limits

- An original channel split across target channels whose distribution companies the holder rarely
  works inflates their expected and lowers their index there. If a split in Step 2 is large, weight
  the expansion by each distribution company's share of the cell's opportunity (needs the
  distribution code on the opportunity rows).
- The opportunity must be the whole market, not one firm's own potential, for both firms to be
  measured against it. To confirm.
- Tested only in DuckDB on synthetic data (`synth.py --check`): per unit of true skill, the
  territory-only index is even between generalists and specialists (0.94 vs 0.94), and crediting
  outside sales lifts both to about 1.0. Not yet run in Snowflake, not yet independently reviewed.

## Appendix A. `04_territory_profile.sql`

```sql
-- Profile of the territory table against raw: counts and firm-level ratios, no names, no amounts.
-- Needs raw, channel_map, territory and filler_keys as in 05_rank_territory.sql.  Firms show as
-- firm_1 / firm_2 (by name order), so the output can leave work.
WITH
f AS (SELECT firm, 'firm_' || DENSE_RANK() OVER (ORDER BY firm) AS firm_label
      FROM (SELECT firm FROM raw UNION SELECT firm FROM territory)),
m AS (SELECT r.zip_code, r.firm, r.wholesaler, cm.channel, r.opportunity, r.sales
      FROM raw r JOIN channel_map cm ON cm.firm = r.firm AND cm.source_channel = r.channel
      WHERE r.wholesaler NOT IN (SELECT key FROM filler_keys)),
t AS (SELECT DISTINCT firm, wholesaler, zip_code, channel FROM territory),
cell AS (SELECT r.zip_code, cm.channel, SUM(r.opportunity) AS opp     -- across firms: NULLs add nothing
         FROM raw r JOIN channel_map cm ON cm.firm = r.firm AND cm.source_channel = r.channel
         GROUP BY 1, 2),
tw AS (SELECT firm, wholesaler, COUNT(DISTINCT zip_code) AS n_zip, COUNT(DISTINCT channel) AS n_ch
       FROM t GROUP BY 1, 2),
s AS (SELECT m.firm, m.sales,
             CASE WHEN t.wholesaler IS NOT NULL THEN 'own_territory'
                  WHEN EXISTS (SELECT 1 FROM t t2 WHERE t2.zip_code = m.zip_code AND t2.channel = m.channel)
                       THEN 'others_territory'
                  ELSE 'no_territory' END AS where_sold
      FROM m LEFT JOIN t ON t.firm = m.firm AND t.wholesaler = m.wholesaler
                        AND t.zip_code = m.zip_code AND t.channel = m.channel)
SELECT 'size' AS grp, 'territory_rows' AS k, COUNT(*) AS v FROM territory
UNION ALL SELECT 'size', 'territory_wholesalers', COUNT(*) FROM tw
UNION ALL SELECT 'size', 'territory_cells', COUNT(*) FROM (SELECT DISTINCT zip_code, channel FROM t)
UNION ALL SELECT 'size', 'duplicate_territory_rows', (SELECT COUNT(*) FROM territory) - (SELECT COUNT(*) FROM t)
UNION ALL SELECT 'size', 'wholesalers_with_sales_no_territory',
  COUNT(*) FROM (SELECT DISTINCT firm, wholesaler FROM m WHERE sales > 0) x
  WHERE NOT EXISTS (SELECT 1 FROM tw WHERE tw.firm = x.firm AND tw.wholesaler = x.wholesaler)
UNION ALL SELECT 'size', 'wholesalers_with_territory_no_sales',
  COUNT(*) FROM tw WHERE NOT EXISTS (SELECT 1 FROM m WHERE m.firm = tw.firm AND m.wholesaler = tw.wholesaler AND m.sales > 0)
UNION ALL SELECT 'size', 'territory_channels_not_in_map',
  COUNT(*) FROM t WHERE channel NOT IN (SELECT DISTINCT channel FROM channel_map)
UNION ALL SELECT 'holders_per_cell_same_firm', n::VARCHAR, COUNT(*)
  FROM (SELECT firm, zip_code, channel, COUNT(*) AS n FROM t GROUP BY 1, 2, 3) GROUP BY 2
UNION ALL SELECT 'zips_per_wholesaler_2^k', f.firm_label || ':' || FLOOR(LOG(2, GREATEST(n_zip, 1)))::VARCHAR, COUNT(*)
  FROM tw JOIN f USING (firm) GROUP BY 2
UNION ALL SELECT 'channels_per_wholesaler', f.firm_label || ':' || n_ch::VARCHAR, COUNT(*)
  FROM tw JOIN f USING (firm) GROUP BY 2
UNION ALL SELECT 'rows_by_where_sold', f.firm_label || ':' || where_sold, COUNT(*)
  FROM s JOIN f USING (firm) WHERE sales > 0 GROUP BY 2
UNION ALL SELECT 'pct_sales_by_where_sold', f.firm_label || ':' || where_sold,
  ROUND(100 * SUM(sales) / SUM(SUM(sales)) OVER (PARTITION BY f.firm_label))
  FROM s JOIN f USING (firm) GROUP BY f.firm_label, where_sold
-- opportunity must sit on one firm's rows only; the other firm's cells must still find it
UNION ALL SELECT 'opp_rows_nonzero', f.firm_label, COUNT(*)
  FROM raw r JOIN f USING (firm) WHERE COALESCE(r.opportunity, 0) <> 0 GROUP BY 2
UNION ALL SELECT 'territory_cells_without_opp', f.firm_label, COUNT(*)
  FROM t JOIN f USING (firm)
  LEFT JOIN cell c ON c.zip_code = t.zip_code AND c.channel = t.channel
  WHERE COALESCE(c.opp, 0) <= 0 GROUP BY 2
UNION ALL SELECT 'pct_sales_in_cells_without_opp', f.firm_label,
  ROUND(100 * SUM(CASE WHEN COALESCE(c.opp, 0) <= 0 THEN m.sales ELSE 0 END) / NULLIF(SUM(m.sales), 0), 1)
  FROM m JOIN f USING (firm)
  LEFT JOIN cell c ON c.zip_code = m.zip_code AND c.channel = m.channel GROUP BY 2
ORDER BY grp, k
```

## Appendix B. `05_rank_territory.sql`

```sql
-- Rank wholesalers on one merged-company scale against their assigned territories.
--
--   expected  = territory opportunity x the channel's pooled rate (both firms together)
--   credited  = sales in the territory + out_credit x sales outside it
--               (owner, 2026-10-19: out-of-territory sales are included; out_credit = 1)
--   perf_index    = (credited + prior) / (expected + prior), per channel with territory; the prior
--                   is `shrink_cells` typical territory cells at the channel rate, so a thin
--                   territory cannot produce an extreme rank
--   index_overall = the same over all the wholesaler's channels (stay / go)
--   index_territory_only = index_overall without the outside sales, for comparison
-- Outside sales add production but no expected opportunity, so they lift the index.  A seller
-- keeps the credit; the territory's holder is not charged for it.  Sales in a territory cell with
-- no positive opportunity count as outside: credited, nothing expected.  The channel rate pools
-- every credited sale over every territory, so the merged company averages exactly 1.
--
-- Needs, in the session (see README.md):
--   raw(zip_code, firm, wholesaler, channel, opportunity, sales)   -- channel = the firm's own
--   channel_map(firm, source_channel, channel)                     -- the channelized firm's channels
--   territory(firm, wholesaler, zip_code, channel)                 -- channel = the channelized firm's
--   filler_keys(key)                                               -- vacancy sentinels
-- If the territory table has no channel, build `territory` as a view: a specialist's zips in
-- their home channel, a generalist's zips crossed with every channel.
-- Opportunity may sit on one firm's rows only, NULL on the other's: `cell` sums it across firms,
-- so each (zip, channel) counts it once and both firms are measured against it.  A territory cell
-- with no opportunity drops out of `expected` and its sales count as outside; 04_territory_profile
-- reports how many (`territory_cells_without_opp`, `pct_sales_in_cells_without_opp`).
-- Run first; all three must return 0:
--   SELECT COUNT(*) FROM raw r LEFT JOIN channel_map cm
--     ON cm.firm = r.firm AND cm.source_channel = r.channel WHERE cm.channel IS NULL;
--   SELECT COUNT(*) FROM territory t
--     WHERE t.channel NOT IN (SELECT DISTINCT channel FROM channel_map);
--   SELECT COUNT(*) FROM (SELECT r.zip_code, cm.channel FROM raw r JOIN channel_map cm      -- cells where
--       ON cm.firm = r.firm AND cm.source_channel = r.channel                              -- two firms
--     WHERE COALESCE(r.opportunity, 0) <> 0                                                 -- both carry
--     GROUP BY 1, 2 HAVING COUNT(DISTINCT r.firm) > 1);                                     -- opportunity
WITH
params AS (SELECT CAST(1.0 AS DOUBLE) AS shrink_cells, CAST(1.0 AS DOUBLE) AS out_credit),
m AS (       -- every row, in the channelized firm's channels
  SELECT r.zip_code, r.firm, r.wholesaler, cm.channel,
         CAST(r.opportunity AS DOUBLE) AS opportunity, CAST(r.sales AS DOUBLE) AS sales
  FROM raw r
  JOIN channel_map cm ON cm.firm = r.firm AND cm.source_channel = r.channel),
cell AS (    -- the market: one row per (zip, channel); opportunity is stored once per cell
  SELECT zip_code, channel, SUM(opportunity) AS opp
  FROM m WHERE zip_code IS NOT NULL
  GROUP BY zip_code, channel),
terr AS (    -- territory cells with positive opportunity
  SELECT DISTINCT t.firm, t.wholesaler, t.zip_code, t.channel, c.opp
  FROM territory t
  JOIN cell c ON c.zip_code = t.zip_code AND c.channel = t.channel
  WHERE c.opp > 0),
held AS (SELECT DISTINCT zip_code, channel FROM territory),
ws AS (      -- a wholesaler's net sales per cell
  SELECT firm, wholesaler, zip_code, channel, SUM(sales) AS sales
  FROM m
  WHERE wholesaler NOT IN (SELECT key FROM filler_keys)
  GROUP BY firm, wholesaler, zip_code, channel),
inside AS (
  SELECT t.firm, t.wholesaler, t.channel,
         COUNT(*)                                             AS terr_cells,
         SUM(CASE WHEN w.sales > 0 THEN 1 ELSE 0 END)         AS cells_with_sales,
         SUM(t.opp)                                           AS opp,
         SUM(COALESCE(w.sales, 0))                            AS sales_in
  FROM terr t
  LEFT JOIN ws w ON w.firm = t.firm AND w.wholesaler = t.wholesaler
                AND w.zip_code = t.zip_code AND w.channel = t.channel
  GROUP BY t.firm, t.wholesaler, t.channel),
outside AS (
  SELECT w.firm, w.wholesaler, w.channel,
         SUM(w.sales)                                         AS sales_out,
         SUM(CASE WHEN h.zip_code IS NULL THEN w.sales ELSE 0 END) AS sales_orphan   -- in nobody's territory
  FROM ws w
  LEFT JOIN terr t ON t.firm = w.firm AND t.wholesaler = w.wholesaler
                  AND t.zip_code = w.zip_code AND t.channel = w.channel
  LEFT JOIN held h ON h.zip_code = w.zip_code AND h.channel = w.channel
  WHERE t.wholesaler IS NULL
  GROUP BY w.firm, w.wholesaler, w.channel),
wc AS (      -- wholesaler x channel
  SELECT COALESCE(i.firm, o.firm) AS firm, COALESCE(i.wholesaler, o.wholesaler) AS wholesaler,
         COALESCE(i.channel, o.channel) AS channel,
         COALESCE(i.terr_cells, 0) AS terr_cells, COALESCE(i.cells_with_sales, 0) AS cells_with_sales,
         COALESCE(i.opp, 0) AS opp, COALESCE(i.sales_in, 0) AS sales_in,
         COALESCE(o.sales_out, 0) AS sales_out, COALESCE(o.sales_orphan, 0) AS sales_orphan
  FROM inside i
  FULL OUTER JOIN outside o ON o.firm = i.firm AND o.wholesaler = i.wholesaler AND o.channel = i.channel),
ch AS (      -- the channel benchmark, pooled over both firms
  SELECT wc.channel,
         SUM(wc.sales_in + x.out_credit * wc.sales_out) / NULLIF(SUM(wc.opp), 0) AS channel_rate,
         MAX(x.shrink_cells) * SUM(wc.opp) / NULLIF(SUM(wc.terr_cells), 0)       AS shrink_opp
  FROM wc CROSS JOIN params x
  GROUP BY wc.channel),
idx AS (
  SELECT wc.*, ch.channel_rate,
         wc.sales_in + x.out_credit * wc.sales_out                         AS credited,
         wc.opp * ch.channel_rate                                          AS expected,
         CASE WHEN wc.opp > 0 THEN ch.shrink_opp * ch.channel_rate ELSE 0 END AS prior
  FROM wc
  JOIN ch ON ch.channel = wc.channel
  CROSS JOIN params x),
o AS (
  SELECT idx.*,
         CASE WHEN opp > 0 THEN (credited + prior) / NULLIF(expected + prior, 0) END AS perf_index,
         SUM(credited + prior) OVER (PARTITION BY firm, wholesaler)
           / NULLIF(SUM(expected + prior) OVER (PARTITION BY firm, wholesaler), 0)   AS index_overall,
         SUM(sales_in + prior) OVER (PARTITION BY firm, wholesaler)
           / NULLIF(SUM(expected + prior) OVER (PARTITION BY firm, wholesaler), 0)   AS index_territory_only,
         SUM(sales_out) OVER (PARTITION BY firm, wholesaler)
           / NULLIF(SUM(sales_in + sales_out) OVER (PARTITION BY firm, wholesaler), 0) AS out_share,
         expected / NULLIF(SUM(expected) OVER (PARTITION BY firm, wholesaler), 0)    AS channel_weight
  FROM idx)
SELECT DENSE_RANK() OVER (ORDER BY index_overall DESC NULLS LAST)                  AS rank_overall,
       firm, wholesaler, index_overall, index_territory_only, out_share,
       channel, channel_weight,
       CASE WHEN perf_index IS NOT NULL
            THEN RANK() OVER (PARTITION BY channel, perf_index IS NULL ORDER BY perf_index DESC) END AS rank_in_channel,
       perf_index, channel_rate, terr_cells, cells_with_sales, opp, expected,
       sales_in, sales_out, sales_orphan, credited
FROM o
ORDER BY rank_overall, wholesaler, channel_weight DESC NULLS LAST
```
