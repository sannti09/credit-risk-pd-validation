-- NIIF 9: cartera viva de préstamos a 36 meses a la fecha de corte y asignación de etapas (D17).
-- Fecha de corte: 2019-03-01 (último mes con pagos en el archivo; el dataset se llama 2018Q4 pero llega a mar-2019).
-- Aquí SÍ se usan variables posteriores a la originación (estado, saldo, FICO actual): NIIF 9 mide la cartera
-- a una fecha, no predice al originar. No es fuga.
--
-- ETAPAS
--   3 (deterioro crediticio): 'Default' (> 120 días) y 'Late (31-120 days)'. LC no separa 31-89 de 90-120 días;
--     se asigna todo a etapa 3 (opción conservadora: PD = 100%). Sensibilidad con etapa 2 en el análisis.
--   2 (aumento significativo del riesgo, SICR): 'Late (16-30 days)', o caída de FICO >= 50 puntos desde la
--     originación, o FICO actual < 600.
--   1: el resto (al día o 'In Grace Period' sin señales de SICR).
CREATE OR REPLACE TABLE ifrs9_portfolio AS
WITH p AS (
    SELECT l.*,
           try_cast(r.last_fico_range_low AS DOUBLE) AS fico_actual,
           try_cast(r.out_prncp AS DOUBLE)           AS saldo,          -- EAD al corte (capital pendiente)
           date_diff('month', l.issue_date, DATE '2019-03-01') AS mob    -- meses en libros
    FROM loans l
    JOIN loans_raw r ON l.id = try_cast(r.id AS BIGINT)
    WHERE l.term_months = 36
      AND l.loan_status IN ('Current', 'In Grace Period', 'Late (16-30 days)', 'Late (31-120 days)', 'Default')
)
SELECT *,
       greatest(36 - mob, 1)                         AS meses_restantes,
       fico_low - fico_actual                        AS caida_fico,
       CASE
           WHEN loan_status IN ('Default', 'Late (31-120 days)') THEN 3
           WHEN loan_status = 'Late (16-30 days)'
             OR fico_low - fico_actual >= 50
             OR fico_actual < 600                     THEN 2
           ELSE 1
       END                                           AS etapa,
       CASE
           WHEN loan_status IN ('Default', 'Late (31-120 days)') THEN 'mora > 30 días'
           WHEN loan_status = 'Late (16-30 days)'    THEN 'mora 16-30 días'
           WHEN fico_low - fico_actual >= 50         THEN 'caída FICO >= 50'
           WHEN fico_actual < 600                    THEN 'FICO actual < 600'
           ELSE 'sin señales'
       END                                           AS motivo_etapa
FROM p
WHERE saldo > 0;
