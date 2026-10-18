-- Build scratch.td_safe: a synthetic copy of the live flat sales table that is safe to leave work.
-- Keeps the columns, the row grain and the edge cases (NULL, 0, negative, vacancy rows, several
-- wholesalers per cell); replaces every name and every number.  See README.md.
-- Source: raw(zip_code, firm, wholesaler, channel, opportunity, sales); rename `raw` below.
-- Run at work only.  Never save the salt or the filler keys in a file.

SET salt = '<long random string>';            -- type it here; never commit it

-- The wholesaler ids that mark a vacancy, not a person.  Fill in at work; never commit them.
CREATE OR REPLACE TEMPORARY TABLE filler_keys (key VARCHAR);
INSERT INTO filler_keys VALUES ('<filler key>');

CREATE OR REPLACE TRANSIENT TABLE scratch.td_safe AS
WITH
-- 1. Break territories: shuffle the (firm, wholesaler) pairs across rows.
rows_ AS (
  SELECT zip_code, channel, opportunity, sales,
         ROW_NUMBER() OVER (ORDER BY RANDOM()) AS k
  FROM raw),
reps_ AS (
  SELECT firm, wholesaler,
         ROW_NUMBER() OVER (ORDER BY RANDOM()) AS k
  FROM raw),
shuffled AS (
  SELECT r.zip_code, r.channel, r.opportunity, r.sales, p.firm, p.wholesaler
  FROM rows_ r JOIN reps_ p ON r.k = p.k),
-- 2. One made-up opportunity per cell; the real value is never read.
cell AS (
  SELECT zip_code, channel, EXP(NORMAL(0, 1.2, RANDOM())) AS opp
  FROM raw
  GROUP BY zip_code, channel),
x AS (
  SELECT s.*, c.opp,
         f.key IS NOT NULL                                   AS is_filler,
         UNIFORM(0::FLOAT, 1::FLOAT, RANDOM())               AS u,
         COUNT(*) OVER (PARTITION BY s.zip_code, s.channel)  AS n
  FROM shuffled s
  JOIN cell c ON EQUAL_NULL(s.zip_code, c.zip_code) AND EQUAL_NULL(s.channel, c.channel)
  LEFT JOIN filler_keys f ON s.wholesaler = f.key)
SELECT
  zip_code,
  channel,
  CASE WHEN firm IS NULL THEN NULL
       ELSE 'FX' || LPAD((DENSE_RANK() OVER (ORDER BY SHA2(firm || $salt)))::VARCHAR, 3, '0')
  END AS firm,
  CASE WHEN wholesaler IS NULL THEN NULL
       WHEN is_filler THEN 'VACANT'
       ELSE 'WX' || LPAD((DENSE_RANK() OVER (ORDER BY SHA2(wholesaler || $salt)))::VARCHAR, 4, '0')
  END AS wholesaler,
  -- keep the shape (NULL / 0 / negative / positive), replace the size
  CASE WHEN opportunity IS NULL THEN NULL
       WHEN opportunity = 0 THEN 0
       WHEN opportunity < 0 THEN -GREATEST(ROUND(opp, 4), 0.0001)
       ELSE GREATEST(ROUND(opp, 4), 0.0001)
  END AS opportunity,
  CASE WHEN sales IS NULL THEN NULL
       WHEN sales = 0 THEN 0
       WHEN sales < 0 THEN -GREATEST(ROUND(0.05 * opp * u, 4), 0.0001)
       ELSE GREATEST(ROUND(0.9 * opp * u / n, 4), 0.0001)      -- a cell's sales stay under its opportunity
  END AS sales
FROM x;
