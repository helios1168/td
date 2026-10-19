-- Whose opportunity is it?  Firm-level ratios and correlations, per channel, safe to bring back.
-- If the opportunity is the whole market, both firms' sales sit inside it and track it about
-- equally.  If it is one firm's own potential, that firm's sales track it far more tightly, and the
-- other firm's sales show up where it is zero or exceed it.  Needs raw and channel_map.
WITH
m AS (SELECT r.zip_code, r.firm, cm.channel, CAST(r.opportunity AS DOUBLE) AS opportunity, CAST(r.sales AS DOUBLE) AS sales
      FROM raw r JOIN channel_map cm ON cm.firm = r.firm AND cm.source_channel = r.channel
      WHERE r.zip_code IS NOT NULL),
cell AS (SELECT zip_code, channel, SUM(opportunity) AS opp, SUM(sales) AS sales_all FROM m GROUP BY 1, 2),
fc AS (SELECT firm, zip_code, channel, SUM(sales) AS sales FROM m GROUP BY 1, 2, 3 HAVING SUM(sales) > 0),
f AS (SELECT firm, 'firm_' || DENSE_RANK() OVER (ORDER BY firm) AS firm_label FROM (SELECT DISTINCT firm FROM raw))
SELECT f.firm_label, fc.channel,
       COUNT(*)                                                          AS cells_with_sales,
       COUNT_IF(COALESCE(c.opp, 0) <= 0)                                 AS cells_no_opp,
       COUNT_IF(c.opp > 0 AND c.sales_all > c.opp)                       AS cells_sales_exceed_opp,
       ROUND(SUM(CASE WHEN c.opp > 0 THEN fc.sales END) / NULLIF(SUM(CASE WHEN c.opp > 0 THEN c.opp END), 0), 4) AS pooled_rate,
       ROUND(MEDIAN(CASE WHEN c.opp > 0 THEN fc.sales / c.opp END), 4)   AS median_cell_rate,
       ROUND(CORR(LN(fc.sales), CASE WHEN c.opp > 0 THEN LN(c.opp) END), 3) AS corr_log_sales_log_opp
FROM fc
JOIN f ON f.firm = fc.firm
LEFT JOIN cell c ON c.zip_code = fc.zip_code AND c.channel = fc.channel
GROUP BY 1, 2
ORDER BY 2, 1
