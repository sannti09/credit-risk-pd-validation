# Registro de decisiones (para explicar en entrevista)

## D1. Definición de default — `sql/03_clean.sql`
- **1 (default):** Charged Off, Default, Late (31-120 days).
- **0 (bueno):** Fully Paid.
- **Sin resultado (NULL):** Current, In Grace Period, Late (16-30 days) → aún no se sabe cómo terminan.
- **Excluidos:** "Does not meet the credit policy" (otra política de aprobación).

## D2. Fuga de información (*data leakage*) — `sql/03_clean.sql`
Solo se usan variables conocidas **al momento de otorgar** el crédito. Se excluyen pagos, recuperaciones,
saldos pendientes, `last_*`, hardship y settlement: existen solo después, y harían que el modelo "vea el futuro".
`grade`, `sub_grade`, `int_rate` son salidas del modelo de Lending Club: se guardan, decisión en fase de modelo.

## D3. Right censoring / Immature vintages — `sql/04_model_sample.sql`
- **Right censoring (censura por la derecha):** al cortar los datos (fin de 2018), muchos préstamos siguen vivos;
  su desenlace queda "cortado" a la derecha de la línea de tiempo.
- **Immature vintages (cosechas inmaduras):** cohortes de originación que no han tenido tiempo de madurar.
- **Sesgo:** en una cohorte inmadura, los préstamos ya cerrados son sobre todo defaults (el default ocurre rápido,
  pagar todo tarda años) → la tasa de default observada se infla (2017: 23,1% vs. 12–15% en 2012–2015, a 36 meses).
- **Decisión:** modelar con préstamos a **36 meses originados 2012–2015** (99,97% con resultado conocido: 86 préstamos de 2015 aún vivos se excluyen).
  - Entrenamiento: 2012–2014 · Prueba *out-of-time*: 2015.
  - 2016–2018 se usan solo para PSI (estabilidad de la población) y curvas de cosecha.
  - 60 meses: fuera por ahora (limitación documentada).
- **Frase para entrevista:** *"Excluí las cohortes inmaduras por right censoring: incluirlas sesga la PD hacia arriba
  porque solo se observan los defaults tempranos."*

## D4. Valores inválidos — `sql/03_clean.sql`
- `dti` < 0 o > 100 (2.563 casos, máx. 999 = valor centinela) → NULL.
- `annual_inc` = 0 (1.667 casos; ingreso 0 en un préstamo aprobado no es creíble) → NULL.
- `revol_util` > 100 (7.316 casos) **se mantiene**: es real (cliente por encima de su cupo).
- Outliers extremos (p. ej. ingreso 110 M) no se recortan: el binning por cuantiles los deja en el último grupo,
  así que no distorsionan el WoE. Si se usa un modelo sensible a escala, se winsoriza ahí.
- NULL resultante → grupo "MISSING" en el WoE.

## D5. Coarse classing y selección de variables — `notebooks/02_feature_selection.py`
- **Score de Lending Club fuera del modelo** (`grade`, `sub_grade`, `int_rate`): se usan solo como **benchmark**.
  Un scorecard con el score de otro no demuestra capacidad de construir uno.
- **Coarse classing monótono:** 20 grupos finos por cuantiles → se fusionan vecinos hasta que la tasa de default
  sea siempre creciente o decreciente y cada grupo tenga ≥ 5% de la muestra. Razón: el scorecard debe ser
  explicable ("a más FICO, menos riesgo") y estable (grupos pequeños = WoE ruidoso).
- **Filtros (en orden):** IV train ≥ 0,02 → estabilidad (IV en OOT no cae > 50%) → redundancia
  (|corr WoE| > 0,7: se queda la de mayor IV). `fico_high` fuera de entrada (= `fico_low` + 4).
- **Resultado:** 16 variables. Ninguna inestable. Detalle en `reports/iv_train_oot.csv`.
- **Observación:** `verification_status` pasa de IV 0,009 a 0,052 en 2015, y `acc_open_past_24mths` casi duplica
  su IV → la población cambió entre cohortes; revisar con PSI en la fase de validación.

## D6. Scorecard logístico — `notebooks/03_scorecard.py`
- **Modelo:** regresión logística (statsmodels) sobre WoE de las 16 variables de D5.
- **Eliminación hacia atrás:** fuera si coeficiente con signo incorrecto (> 0 → señal de colinealidad) o p > 0,05.
  Resultado: las 16 se mantienen, todas con signo correcto y p < 0,01.
- **Escalado:** 600 puntos = odds buenos:malos 50:1; **PDO = 20** (cada 20 puntos se duplican las odds).
  Rango en train: 482–614. Tabla de puntos en `reports/scorecard_points.csv`.
- **Desempeño (Gini / KS):**
  | Muestra | Scorecard propio | LC sub_grade |
  |---|---|---|
  | Train 2012–14 | 0,320 / 0,231 | 0,300 / 0,221 |
  | OOT 2015 | 0,334 / 0,240 | 0,357 / 0,262 |
- **Lectura:** sin degradación en OOT (el Gini incluso sube). Supera al grado de LC en train, pero en train juega
  con ventaja (se estimó ahí); en OOT el grado de LC gana por ~2 pts de Gini. LC usa información que no tenemos
  (p. ej. historial interno, modelo actualizado en 2015), así que quedar a 2 pts usando solo datos del buró y la
  solicitud es un resultado razonable. **Pendiente (fase 3):** calibración — default OOT 14,9% vs. 13,2% en train.
