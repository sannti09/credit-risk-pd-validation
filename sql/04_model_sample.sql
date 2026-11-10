-- Muestra de modelado. Ver docs/decisiones.md (D3: right censoring / immature vintages).
-- 36 meses, originados 2012-2015 (cohortes maduras: 100% con resultado conocido).
-- split: train = 2012-2014, oot (out-of-time) = 2015.
CREATE OR REPLACE TABLE model_sample AS
SELECT *,
       CASE WHEN issue_year <= 2014 THEN 'train' ELSE 'oot' END AS split
FROM loans
WHERE term_months = 36
  AND issue_year BETWEEN 2012 AND 2015
  AND target IS NOT NULL;
