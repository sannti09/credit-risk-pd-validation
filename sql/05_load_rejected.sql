-- Carga cruda de solicitudes RECHAZADAS (2007-2018Q4). Sin desempeño: solo sirven para representatividad (D8).
-- El archivo original en data/raw/ no se modifica.
CREATE OR REPLACE TABLE rejected_raw AS
SELECT *
FROM read_csv('data/raw/lending_club_kaggle/rejected_2007_to_2018Q4.csv.gz',
              header = true, all_varchar = true);
