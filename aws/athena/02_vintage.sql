-- Curvas de cosecha en Athena (Trino): misma lógica que sql/08_dashboard.sql (DuckDB). Ver D28.
WITH base AS (
    SELECT CAST(year(issue_date) AS varchar) || '-Q' || CAST(quarter(issue_date) AS varchar)  AS cosecha,
           date_diff('month', issue_date, DATE '2019-03-01')                                AS meses_observados,
           CASE WHEN loan_status IN ('Charged Off', 'Default', 'Late (31-120 days)')
                THEN greatest(coalesce(date_diff('month', issue_date,
                         CAST(date_parse(last_pymnt_d, '%b-%Y') AS date)) + 1, 1), 1) END  AS mes_default
    FROM credit_risk.loans
    WHERE term_months = 36 AND issue_year BETWEEN 2013 AND 2018          -- poda de particiones
),
tam AS (SELECT cosecha, count(*) AS prestamos, min(meses_observados) AS meses_obs FROM base GROUP BY 1),
defaults_mes AS (SELECT cosecha, mes_default AS mob, count(*) AS defaults
                 FROM base WHERE mes_default IS NOT NULL GROUP BY 1, 2),
grilla AS (SELECT t.cosecha, m.mob, t.prestamos
           FROM tam t CROSS JOIN UNNEST(sequence(1, 36)) AS m(mob) WHERE m.mob <= t.meses_obs)
SELECT g.cosecha, g.mob, g.prestamos,
       sum(coalesce(d.defaults, 0)) OVER (PARTITION BY g.cosecha ORDER BY g.mob) AS defaults_acum,
       CAST(sum(coalesce(d.defaults, 0)) OVER (PARTITION BY g.cosecha ORDER BY g.mob) AS double)
           / g.prestamos                                                            AS tasa_default_acum
FROM grilla g LEFT JOIN defaults_mes d ON g.cosecha = d.cosecha AND g.mob = d.mob
ORDER BY 1, 2
