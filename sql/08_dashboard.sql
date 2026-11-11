-- Tablas agregadas para el tablero (D26). Solo agregados: sin datos a nivel de préstamo.

-- 1) Curvas de cosecha (vintage): default acumulado por mes en libros, por trimestre de originación (36 meses).
--    Default = Charged Off / Default / Late (31-120); mes de default ≈ último pago + 1.
--    Solo se muestran meses observados para TODOS los préstamos de la cosecha (mínimo de la cosecha; una cosecha
--    trimestral mezcla 3 meses de originación): el denominador nunca incluye préstamos aún no observados (D31).
--    Defaults sin fecha de último pago (1.672 en 2013-2018) se asignan al mes 1 (efecto ≈ +0,1 pp, documentado).
CREATE OR REPLACE TABLE dash_vintage AS
WITH base AS (
    SELECT l.id,
           strftime(l.issue_date, '%Y') || '-Q' || quarter(l.issue_date)         AS cosecha,
           date_diff('month', l.issue_date, DATE '2019-03-01')                   AS meses_observados,
           CASE WHEN l.loan_status IN ('Charged Off', 'Default', 'Late (31-120 days)')
                THEN greatest(coalesce(date_diff('month', l.issue_date,
                         strptime(r.last_pymnt_d, '%b-%Y')::DATE) + 1, 1), 1) END AS mes_default
    FROM loans l JOIN loans_raw r ON l.id = try_cast(r.id AS BIGINT)
    WHERE l.term_months = 36 AND l.issue_year BETWEEN 2013 AND 2018
),
tam AS (SELECT cosecha, count(*) AS prestamos, min(meses_observados) AS meses_obs FROM base GROUP BY 1),
defaults_mes AS (SELECT cosecha, mes_default AS mob, count(*) AS defaults
                 FROM base WHERE mes_default IS NOT NULL GROUP BY 1, 2),
grilla AS (SELECT t.cosecha, m.mob, t.prestamos, t.meses_obs
           FROM tam t, range(1, 37) AS m(mob) WHERE m.mob <= t.meses_obs)
SELECT g.cosecha, g.mob, g.prestamos,
       sum(coalesce(d.defaults, 0)) OVER (PARTITION BY g.cosecha ORDER BY g.mob)            AS defaults_acum,
       sum(coalesce(d.defaults, 0)) OVER (PARTITION BY g.cosecha ORDER BY g.mob) / g.prestamos AS tasa_default_acum
FROM grilla g LEFT JOIN defaults_mes d USING (cosecha, mob)
ORDER BY 1, 2;

-- 2) Originación por año y grado de LC: volumen, tasa y default observado (36 meses)
CREATE OR REPLACE TABLE dash_originacion AS
SELECT issue_year AS anio, grade AS grado, count(*) AS prestamos, sum(loan_amnt) AS monto,
       avg(int_rate) AS tasa_media, avg(fico_low) AS fico_medio,
       avg(target) AS default_obs, avg((target IS NOT NULL)::INT) AS pct_con_resultado
FROM loans WHERE term_months = 36 GROUP BY 1, 2 ORDER BY 1, 2;

-- 3) Cartera NIIF 9 por año de originación y etapa
CREATE OR REPLACE TABLE dash_cartera AS
SELECT p.issue_year AS anio_originacion, p.etapa, p.motivo_etapa, count(*) AS prestamos, sum(p.saldo) AS saldo,
       sum(p.saldo * q.pd_aplicable) / sum(p.saldo) AS pd_aplicable_pond
FROM ifrs9_portfolio p JOIN ifrs9_pd q USING (id) GROUP BY ALL ORDER BY 1, 2;
