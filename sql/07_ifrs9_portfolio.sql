-- NIIF 9: cartera viva de préstamos a 36 meses a la fecha de corte y asignación de etapas (D17).
-- Fecha de corte: 2019-03-01 (último mes con pagos en el archivo; el dataset se llama 2018Q4 pero llega a mar-2019).
-- Aquí SÍ se usan variables posteriores a la originación (estado, saldo, FICO actual): NIIF 9 mide la cartera
-- a una fecha, no predice al originar. No es fuga.
--
-- ETAPAS (D17, corregido en D21)
--   Días de mora ≈ meses desde el último pago × 30 (LC no separa 31-89 de 90-120 dentro de 'Late (31-120)').
--   3 (deterioro, presunción NIIF 9 de 90 días): 'Default', o 'Late (31-120)' con >= 3 meses sin pago
--     (o sin fecha de pago: conservador).
--   2 (SICR): 'Late (31-120)' con < 3 meses sin pago (backstop de 30 días), 'Late (16-30 days)', caída de FICO
--     >= 50 puntos, FICO actual < 600, o préstamo vencido (>= 36 meses en libros) sin cancelar.
--   1: el resto (al día o 'In Grace Period' sin señales de SICR).
CREATE OR REPLACE TABLE ifrs9_portfolio AS
WITH p AS (
    SELECT l.*,
           try_cast(r.last_fico_range_low AS DOUBLE) AS fico_actual,
           try_cast(r.out_prncp AS DOUBLE)           AS saldo,          -- EAD al corte (capital pendiente)
           date_diff('month', strptime(r.last_pymnt_d, '%b-%Y')::DATE, DATE '2019-03-01') AS meses_sin_pago,
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
           WHEN loan_status = 'Default'
             OR (loan_status = 'Late (31-120 days)' AND coalesce(meses_sin_pago, 99) >= 3) THEN 3
           WHEN loan_status IN ('Late (31-120 days)', 'Late (16-30 days)')
             OR fico_low - fico_actual >= 50
             OR fico_actual < 600
             OR mob >= 36                             THEN 2
           ELSE 1
       END                                           AS etapa,
       CASE
           WHEN loan_status = 'Default'
             OR (loan_status = 'Late (31-120 days)' AND coalesce(meses_sin_pago, 99) >= 3) THEN 'mora >= 90 días'
           WHEN loan_status = 'Late (31-120 days)'   THEN 'mora 31-89 días'
           WHEN loan_status = 'Late (16-30 days)'    THEN 'mora 16-30 días'
           WHEN fico_low - fico_actual >= 50         THEN 'caída FICO >= 50'
           WHEN fico_actual < 600                    THEN 'FICO actual < 600'
           WHEN mob >= 36                            THEN 'vencido sin cancelar'
           ELSE 'sin señales'
       END                                           AS motivo_etapa
FROM p
WHERE saldo > 0;
