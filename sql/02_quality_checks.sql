-- Chequeos de calidad sobre la capa raw (correr después de 01_load_raw.sql).

-- 1. Unicidad de la llave: filas vs. id distintos (esperado: iguales)
SELECT count(*) AS filas, count(DISTINCT id) AS ids_distintos FROM loans_raw;

-- 2. Registros inválidos: id no numérico (líneas de totales al final del CSV)
SELECT count(*) AS ids_invalidos FROM loans_raw WHERE try_cast(id AS BIGINT) IS NULL;

-- 3. Cobertura temporal: rango de fechas de originación
SELECT min(strptime(issue_d, '%b-%Y')) AS desde, max(strptime(issue_d, '%b-%Y')) AS hasta
FROM loans_raw WHERE issue_d IS NOT NULL;

-- 4. Distribución de la variable objetivo
SELECT loan_status, count(*) AS n FROM loans_raw GROUP BY 1 ORDER BY 2 DESC;
