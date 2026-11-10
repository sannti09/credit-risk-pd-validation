-- Carga cruda de Lending Club (aprobados 2007-2018Q4) en DuckDB.
-- Todo como texto: los tipos se definen en la limpieza (02), de forma explícita y documentada.
CREATE OR REPLACE TABLE loans_raw AS
SELECT *
FROM read_csv('data/raw/lending_club_kaggle/accepted_2007_to_2018Q4.csv.gz',
              header = true, all_varchar = true);
