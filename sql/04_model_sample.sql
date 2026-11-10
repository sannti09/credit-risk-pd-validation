-- Muestra de modelado. Ver docs/decisiones.md (D3: right censoring / immature vintages).
-- 36 meses, originados 2013-2015 (cohortes maduras; 2012 fuera: datos de buró incompletos, ver D7).
-- split: train = 2013 (estimación) · valid = 2014 (selección de variables y ajustes) · oot = 2015 (prueba final,
-- no se usa para ninguna decisión de modelado; ver D9).
CREATE OR REPLACE TABLE model_sample AS
SELECT *,
       CASE issue_year WHEN 2013 THEN 'train' WHEN 2014 THEN 'valid' ELSE 'oot' END AS split
FROM loans
WHERE term_months = 36
  AND issue_year BETWEEN 2013 AND 2015
  AND target IS NOT NULL;
