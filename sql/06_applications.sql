-- Solicitudes armonizadas: aprobados + rechazados en las variables comunes (D8, representatividad).
-- Aprobados: todos los plazos (los rechazados no tienen plazo). Ventana: se filtra en el análisis.
-- risk_score: en aprobados = fico_range_low. En rechazados es FICO solo antes del 5-nov-2013 (diccionario de LC);
-- después cambia de escala (en los datos aparecen valores > 850 justo desde esa fecha) -> se anula (D10).
-- emp_length de rechazados NO se usa: 86,5% viene como '< 1 year' (vs 8,2% en aprobados) = valor por defecto.
CREATE OR REPLACE TABLE applications AS
SELECT 'aprobado' AS fuente, issue_year AS app_year, loan_amnt AS amount, fico_low AS risk_score,
       dti, emp_length_years, addr_state AS state
FROM loans
UNION ALL
SELECT 'rechazado',
       year(try_cast("Application Date" AS DATE)),
       try_cast("Amount Requested" AS DOUBLE),
       CASE WHEN try_cast("Risk_Score" AS DOUBLE) BETWEEN 300 AND 850
             AND try_cast("Application Date" AS DATE) < DATE '2013-11-05'
            THEN try_cast("Risk_Score" AS DOUBLE) END,             -- solo FICO; 0 o fuera de rango = inválido
       CASE WHEN try_cast(replace("Debt-To-Income Ratio", '%', '') AS DOUBLE) >= 0
            THEN try_cast(replace("Debt-To-Income Ratio", '%', '') AS DOUBLE) END,  -- >100 se conserva: puede ser causa del rechazo
       NULL::INTEGER,                                               -- emp_length no confiable (ver arriba)
       "State"
FROM rejected_raw;
