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
- **Decisión:** modelar con préstamos a **36 meses originados 2013–2015** (2012 fuera, ver D7) (99,97% con resultado conocido: 86 préstamos de 2015 aún vivos se excluyen).
  - Entrenamiento: 2013–2014 · Prueba *out-of-time*: 2015.
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
> ⚠️ **Reemplazada:** las cifras de esta sección son de una versión anterior de la muestra. Vigentes: **D9** (selección,
> modelo, desempeño), **D11** (calibración) y `reports/`. Se conserva por trazabilidad.

- **Score de Lending Club fuera del modelo** (`grade`, `sub_grade`, `int_rate`): se usan solo como **benchmark**.
  Un scorecard con el score de otro no demuestra capacidad de construir uno.
- **Coarse classing monótono:** 20 grupos finos por cuantiles → se fusionan vecinos hasta que la tasa de default
  sea siempre creciente o decreciente y cada grupo tenga ≥ 5% de la muestra. Razón: el scorecard debe ser
  explicable ("a más FICO, menos riesgo") y estable (grupos pequeños = WoE ruidoso).
- **Filtros (en orden):** IV train ≥ 0,02 → estabilidad (IV en OOT no cae > 50%) → redundancia
  (|corr WoE| > 0,7: se queda la de mayor IV). `fico_high` fuera de entrada (= `fico_low` + 4).
- **Resultado (train 2013–14):** 13 variables. Ninguna inestable. `purpose`, `revol_util` e `inq_last_6mths` quedaron
  justo bajo IV 0,02 al quitar 2012. Detalle en `reports/iv_train_oot.csv`.
- **Observación:** `verification_status` pasa de IV 0,009 a 0,052 en 2015, y `acc_open_past_24mths` casi duplica
  su IV → la población cambió entre cohortes; revisar con PSI en la fase de validación.

## D6. Scorecard logístico — `notebooks/03_scorecard.py`
> ⚠️ **Reemplazada:** las cifras de esta sección son de una versión anterior de la muestra. Vigentes: **D9** (selección,
> modelo, desempeño), **D11** (calibración) y `reports/`. Se conserva por trazabilidad.

- **Modelo:** regresión logística (statsmodels) sobre WoE de las 13 variables de D5.
- **Eliminación hacia atrás:** fuera si coeficiente con signo incorrecto (> 0 → señal de colinealidad) o p > 0,05.
  Resultado: las 13 se mantienen, todas con signo correcto y significativas.
- **Escalado:** 600 puntos = odds buenos:malos 50:1; **PDO = 20** (cada 20 puntos se duplican las odds).
  Rango en train: 491–609. Tabla de puntos en `reports/scorecard_points.csv`.
- **Desempeño (Gini / KS):**
  | Muestra | Scorecard propio | LC sub_grade |
  |---|---|---|
  | Train 2013–14 | 0,312 / 0,225 | 0,312 / 0,230 |
  | OOT 2015 | 0,328 / 0,237 | 0,357 / 0,262 |
- **Lectura:** sin degradación en OOT (el Gini incluso sube). Empata con el grado de LC en train; en OOT el grado
  de LC gana por ~3 pts de Gini. LC usa información que no tenemos
  (p. ej. historial interno, modelo actualizado en 2015), así que quedar a ~3 pts usando solo datos del buró y la
  solicitud es un resultado razonable. **Pendiente (fase 3):** calibración — default OOT 14,9% vs. 13,2% en train → ver D7.

## D7. Validación — `notebooks/04_validation.py`, `src/credit_risk/validation.py`
> ⚠️ **Reemplazada:** las cifras de esta sección son de una versión anterior de la muestra. Vigentes: **D9** (selección,
> modelo, desempeño), **D11** (calibración) y `reports/`. Se conserva por trazabilidad.

**Hallazgo previo (corregido):** el primer CSI dio ~0,84 en 5 variables. Causa: en 2012 el ~52% de los préstamos
no traía variables de buró (`avg_cur_bal`, `total_rev_hi_lim`, `num_tl_op_past_12m`, `mo_sin_*`); desde 2013 vienen
completas. El grupo MISSING (7% de train) desaparecía en OOT → artefacto de recolección, no cambio de población.
**Decisión:** entrenar con 2013–2014 (datos consistentes). Lección: un PSI enorme suele ser un problema de datos.

| Prueba | Resultado | Semáforo |
|---|---|---|
| Discriminación (Gini) | 0,312 train → 0,328 OOT | verde |
| PSI del score vs train | 2015: 0,004 · 2016: 0,000 · 2017: 0,018 · 2018: 0,076 | verde |
| CSI | `percent_bc_gt_75` 0,30 en 2018; `fico_low` 0,14 y `mo_sin_old_rev_tl_op` 0,11 en 2018 | rojo / ámbar (2018) |
| Calibración global OOT | PD media 13,6% vs. default observado 14,9% | rojo |
| Binomial por banda OOT | bandas 1–9 subestiman la PD (~1–2 pts); banda 10 ok | rojo |
| Hosmer-Lemeshow | train p = 0,005; OOT p ≈ 0 | rojo |

**Lectura (como validador):**
- El modelo **ordena bien** el riesgo y es **estable**, pero está **descalibrado en nivel**: en 2015 todos los grupos
  incumplieron más de lo estimado → cambio en la tasa de default de la población (*calibration-in-the-large*),
  no un problema de ordenamiento.
- **Recomendación:** recalibrar el intercepto (o calibrar por banda) con la cohorte más reciente madura, y monitorear.
- H-L rechaza incluso en train: con n ≈ 260 mil detecta diferencias mínimas. Se reporta, pero se juzga junto con
  la magnitud de la desviación (aquí ~1,4 pts en OOT, material para provisiones).
- 2018: revisar `percent_bc_gt_75` y `fico_low` (posible cambio de política de LC en cortes de FICO).

## D8. Sesgo de selección (solo aprobados) — investigación y tratamiento
**Problema:** el modelo se entrena solo con préstamos **aprobados** (modelo *known good/bad*); no se observa el
desempeño de los rechazados. La población de solicitantes (*through-the-door*) no es la de entrenamiento.

**Qué dice la literatura (reject inference):**
- Métodos: hard cutoff, parceling, reweighting, (fuzzy) augmentation, Heckman/probit bivariado, semi-supervisados,
  buró de rechazados, y experimentos *below cutoff* (aprobar una muestra bajo el punto de corte).
- Evidencia: **no hay consenso de que mejore el modelo**. Sin desempeño de los rechazados, cualquier corrección
  depende de supuestos no verificables (Hand & Henley 1993; Crook & Banasik 2004; Banasik & Crook 2007).
  Solo el experimento *below cutoff* identifica el efecto. Con Lending Club hay trabajos que usan el archivo de
  rechazados (Mancisidor et al. 2019, arXiv 1904.11376), pero sin poder validar contra desempeño real.

**Qué esperan reguladores y validadores:**
- **SR 26-2** (Fed, 17-abr-2026, reemplaza a SR 11-7 y SR 21-8): gestión de riesgo de modelo; documentar limitaciones.
- **EBA/GL/2017/16:** representatividad de los datos frente a la población y política actual, con análisis
  explícito; si no es representativa → ajustes o margen de conservadurismo.
- **BCBS WP14 (2005):** las pruebas estadísticas no bastan; complementar con benchmarking.
- Práctica: documentar la limitación **y cuantificarla** (aprobados vs. solicitantes), monitorear tasa de aprobación,
  *swap-set analysis*, champion-challenger.
- SFC (SARC, Cap. II CBCF): pendiente verificar texto sobre representatividad.

**Decisión para el proyecto:**
1. **Separar train / validación / OOT** para que 2015 no influya en el modelado (corrige *data snooping* de D5).
2. **Análisis de representatividad** con el archivo de rechazados: comparar aprobados vs. rechazados en las variables
   comunes (FICO, dti, antigüedad laboral, monto, estado) con PSI, y tasa de aprobación por año.
3. **Sensibilidad (no corrección):** reestimar con parceling y reportar cuánto cambian coeficientes, Gini y PD media.
4. Declarar la limitación en el informe: el modelo es válido para la población **aprobada** bajo la política de LC.

**Frase para entrevista:** *"No apliqué reject inference como corrección porque sin desempeño de los rechazados
no es verificable; cuantifiqué la diferencia de poblaciones y reporté la sensibilidad como lo pide la EBA."*

## D9. Separación train / validación / OOT (corrige *data snooping*) — **reemplaza las cifras de D5–D7**
- **Antes:** el filtro de estabilidad de D5 miraba el IV de 2015 → la prueba final influía en qué variables entraban.
- **Ahora:** train = **2013** (100 mil, estimación) · valid = **2014** (163 mil, selección de variables y ajustes)
  · OOT = **2015** (283 mil, prueba final: no se usa para ninguna decisión).
- **Variables (13):** fico_low, annual_inc, avg_cur_bal, dti, acc_open_past_24mths, home_ownership, mo_sin_rcnt_tl,
  num_tl_op_past_12m, percent_bc_gt_75, mo_sin_old_rev_tl_op, mths_since_recent_inq, revol_util, purpose.
  (`total_rev_hi_lim` y `mort_acc` salieron por p > 0,05 en la logística.)

| Muestra | Gini propio | Gini LC sub_grade | PD media | Default observado |
|---|---|---|---|---|
| Train 2013 | 0,326 | 0,298 | 12,3% | 12,3% |
| Valid 2014 | 0,313 | 0,319 | 13,0% | 13,7% |
| **OOT 2015** | **0,325** | 0,357 | 12,9% | **14,9%** |

- **Lectura:** discriminación estable (0,326 → 0,325) y PSI del score verde hasta 2018 (máx. 0,062). La
  descalibración ya aparece en valid 2014 (−0,7 pts) y crece en OOT (−2 pts) → la tasa de default sube año a año.
- **Siguiente:** recalibrar con valid 2014 (permitido) y comprobar en OOT 2015 si la recalibración funciona.
- CSI 2017–2018 en ámbar/rojo para `percent_bc_gt_75` (0,37) y `revol_util` (0,38): la población de 2018 usa más
  su cupo rotativo → vigilar en monitoreo.

## D10. Análisis de representatividad: aprobados vs. rechazados — `notebooks/05_representativeness.py`
Variables comunes en `sql/06_applications.sql`. Ventana 2013–2015: 5,55 M rechazados vs. 791 mil aprobados (todos
los plazos; los rechazados no tienen plazo). PSI calculado **solo sobre valores válidos**; faltantes aparte.

**Advertencias revisadas con datos (antes de concluir):**
1. **Score de rechazados cambia de escala el 5-nov-2013.** El diccionario de LC dice que antes de esa fecha es FICO
   (copia no oficial del diccionario). En los datos, justo desde esa fecha aparecen valores > 850 (imposibles en FICO)
   y el p90 salta de 709 a 720–734 → otro score (probablemente VantageScore). **Decisión:** usar el score de
   rechazados solo antes del 5-nov-2013 (≈ 600 mil solicitudes con score y DTI válidos).
2. **Faltantes:** 48% de rechazados 2013–15 sin score en el dato crudo; al restringir a FICO (antes del 5-nov-2013)
   queda **89% sin score válido** en la ventana (600 mil con score). Se excluyen del PSI y se reportan aparte. Sin ellos
   el PSI sigue en rojo → la diferencia es real, no un artefacto del faltante.
3. **Antigüedad laboral de rechazados no es confiable:** 86,5% viene como "< 1 year" (vs. 8,2% en aprobados) →
   valor por defecto de solicitudes incompletas. **Se excluye** de la comparación.

| Variable | Mediana aprobados | Mediana rechazados | PSI (válidos) |
|---|---|---|---|
| Score (solo FICO, antes 5-nov-13) | 685 | 649 | 0,89 🔴 |
| DTI | 18,0 | 19,3 | 0,55 🔴 |
| Monto | 13.600 | 10.000 | 0,65 🔴 |
| Estado | — | — | 0,02 🟢 |

- **Tasa de aprobación:** 15% (2013) → 5% (2018).
- **Soporte del modelo** (rechazados con FICO y DTI válidos): **59% con FICO < 660** (mínimo de aprobados), 19% con
  DTI > 39; solo **30%** cae dentro del rango de los aprobados.
- **Dominio de aplicación declarado:** solicitantes que cumplen la política de LC (FICO ≥ 660, DTI ≤ 39).
  → **Corregido en D16:** el dominio se define con los rangos de *train* (DTI ≤ 35), no con todos los aprobados. Fuera de ese
  rango el modelo extrapola a perfiles que nunca vio.
- **Limitación menor:** el score de rechazados solo cubre ene–oct 2013, mientras que los aprobados cubren 2013–2015.
- **Parceling (D8, paso 3): no factible.** Los rechazados traen 5 variables; el scorecard usa 13 de buró que no tienen.

## D11. Recalibración y margen de conservadurismo — `notebooks/06_recalibration.py`, `src/credit_risk/calibration.py`
Se ajusta **solo con train/valid** y se evalúa en OOT 2015 sin tocarlo. La recalibración no cambia el orden (Gini igual).

| Método (evaluado en OOT 2015) | PD media | Default obs. | Brecha | Bandas rojas (binomial) |
|---|---|---|---|---|
| Original | 12,9% | 14,9% | −2,0 pts | 9 de 10 |
| Intercepto ajustado a 2014 | 13,7% | 14,9% | −1,2 pts | 9 |
| Platt (nivel + pendiente) con 2014 | 13,7% | 14,9% | −1,2 pts | 8 |
| **Intercepto + MoC por tendencia** | **15,1%** | 14,9% | **+0,15 pts** (PD > observado) | **1** |

- **Por qué no basta recalibrar con el último año:** el default sube ~1,4 pts por año (12,3% → 13,7% → 14,9%).
  Calibrar con 2014 siempre llega un año tarde. Platt casi no mejora: la pendiente (0,94) estaba bien; el problema
  es de **nivel**, no de forma.
- **Decisión:** intercepto ajustado a la tasa de 2014 **+ margen de conservadurismo (MoC)** igual a la tendencia
  observada train→valid (+1,4 pts), calculado sin mirar OOT. Resultado: sesgo cerrado y ligeramente conservador.
- **Por qué conservador:** EBA/GL/2017/16 pide MoC cuando hay deficiencias o cambios identificados; ante la duda,
  sobreestimar la PD es preferible a subestimarla (provisiones/capital insuficientes).
- **Limitaciones:** (1) la tendencia sale de solo 2 puntos → frágil; si el default se estabiliza o baja, el MoC
  sobreestimará. (2) Hosmer-Lemeshow sigue rechazando (p ≈ 0) por el tamaño muestral, pero su estadístico cae de
  1.080 a 70. (3) Requiere monitoreo y reestimación anual del MoC.
- **NIIF 9:** este ajuste por tendencia se reemplazaría por un ajuste *forward-looking* con escenarios macro.
- **Frase para entrevista:** *"El modelo ordenaba bien pero subestimaba el nivel. Recalibrar al último año no bastaba
  por la tendencia creciente, así que agregué un margen de conservadurismo estimado sin usar la muestra OOT."*

## D12. Challenger: gradient boosting — `notebooks/07_challenger.py`
- **Modelo:** `HistGradientBoostingClassifier` (scikit-learn) con las 36 variables candidatas en crudo (sin WoE;
  maneja faltantes y categóricas). Mismas reglas: train 2013, hiperparámetros elegidos por Gini en valid 2014
  (grilla de 8), OOT 2015 solo para el resultado final.
- **Fuga detectada y corregida:** `installment` salió 3ª en importancia pese a IV ≈ 0,002. Con plazo fijo de 36 meses,
  cuota + monto determinan la tasa de interés, que LC fija según su grado → el GBM reconstruía el score de LC.
  Se excluyó. (El scorecard no la usaba: su IV individual era casi nulo; el GBM sí explota la interacción.)

| Gini (KS) | Train 2013 | Valid 2014 | OOT 2015 |
|---|---|---|---|
| Scorecard (13 var.) | 0,326 (0,238) | 0,313 (0,226) | 0,325 (0,237) |
| **GBM (36 var.)** | 0,487 (0,356) | 0,349 (0,253) | **0,361 (0,261)** |
| LC sub_grade (benchmark) | 0,298 | 0,319 | 0,357 |

- **Lectura:** el GBM supera al scorecard por **~3,6 pts de Gini en OOT** y empata con el grado de LC usando solo
  datos de solicitud y buró. Pero hay **sobreajuste** (0,49 en train vs 0,35 en valid): aprende ruido de 2013, aunque
  la ventaja se mantiene fuera de muestra. También subestima la PD en OOT (13,0% vs 14,9%) → misma recalibración.
- **Variables más importantes:** FICO, ingreso, monto, cuentas abiertas 24m, DTI (coherente con el scorecard).
- **Campeón vs. challenger (criterio de validador):** el GBM discrimina mejor, pero el scorecard es explicable por
  puntos, monótono y más fácil de defender ante regulador. Decisión: **scorecard sigue como campeón**; el GBM sirve como
  benchmark de cuánto poder se deja sobre la mesa (~3,6 pts) y como candidato si se acompaña de explicabilidad (SHAP)
  y restricciones de monotonía.

## D13. GBM regularizado contra sobreajuste — `notebooks/07_challenger.py` (reemplaza el GBM de D12)
**Controles:** árboles poco profundos (profundidad 2–4) · hojas ≥ 1.000–3.000 clientes · early stopping contra
**valid 2014** (otro año, no una partición de 2013) · monotonía por variable (signo de Spearman en train) ·
`max_features` 0,5 · L2. Se excluye además `addr_state` (50 categorías, IV ≈ 0,01, proxy geográfico).
**Regla de selección (tipo "1 error estándar"):** las 24 configuraciones quedaron dentro de 0,005 del mejor Gini
en valid (TOL) → entre ellas se elige la de menor brecha train−valid (la más simple): profundidad 2, hojas ≥ 3.000, 650 árboles.

| Gini | Train 2013 | Valid 2014 | OOT 2015 | Brecha train−valid |
|---|---|---|---|---|
| Scorecard | 0,326 | 0,313 | 0,325 | 0,013 |
| GBM sin controles (D12) | 0,487 | 0,349 | 0,361 | **0,138** |
| **GBM regularizado** | 0,363 | 0,333 | **0,340** | **0,030** |
| LC sub_grade | 0,298 | 0,319 | 0,357 | — |

- **Brecha de sobreajuste: 0,138 → 0,030** (**no cumple** el umbral de 0,03: 0,0303 > 0,03; ninguna de las 24 configuraciones lo cumplió). Parte de la brecha
  no es sobreajuste sino cambio de año: el propio scorecard pierde 0,013 de 2013 a 2014.
- **Costo:** el GBM regularizado pierde ~2 pts de Gini en OOT frente al GBM sin controles (0,361 → 0,340). Ventaja
  sobre el scorecard: +1,6 pts.
- **Lectura honesta:** el GBM sin controles generalizó bien en 2015 *a pesar* de su brecha; la brecha es un
  **riesgo** (inestable ante otros cambios de población), no una pérdida segura. El validador prefiere el modelo
  regularizado: menor riesgo de modelo, monótono y más explicable, a cambio de algo de poder.
- **Monotonía:** garantiza que, por ejemplo, más FICO nunca suba la PD → el modelo es defendible variable por variable.

## D14. Limitaciones del proceso (revisión independiente, fases 2–3)
Dos revisores independientes revisaron fases 2 y 3: sin errores de cálculo ni fugas; hallazgos de proceso:
1. **OOT 2015 no es 100% ciego.** Los números del MoC (D11) se calcularon sin 2015, pero la *decisión* de agregar un
   MoC por tendencia surgió de ver la subestimación en 2015 (D9). No hay otra cohorte madura (2016+ es inmadura,
   D3) para una prueba nueva → se declara como limitación. El Gini OOT (sin ajustes) sí es limpio.
2. **Valid 2014 es optimista:** se usa para seleccionar variables, early stopping y elegir hiperparámetros del GBM.
   Su Gini se reporta, pero el resultado de referencia es OOT 2015. Sesgo estimado en la grilla del GBM: 0,001–0,003.
3. **El GBM reconstruye parte del precio de LC:** con las variables permitidas predice `int_rate` con R² ≈ 0,33
   (dato del revisor, no reverificado). No es fuga determinista (a diferencia de `installment`), pero parte de su
   ventaja puede venir de replicar el criterio de LC.
4. **WoE de grupos no vistos en train = 0 (neutral).** Afecta 10 casos en OOT (2 de `annual_inc`, 7 de `dti`
   y 1 categoría nueva de `home_ownership`). Ahora `WoEBinner.transform` emite una alerta con el conteo.
5. **Puntos redondeados:** la suma de puntos enteros del scorecard puede diferir del score continuo en unos pocos
   puntos (13 variables × ±0,5). Probado en `tests/test_metrics.py`.

## D15. Informe de validación con semáforos — `notebooks/08_validation_report.py` → `reports/informe_validacion.md`
- El informe **se genera desde los CSV de `reports/`**: si cambian datos o modelo, se regenera sin copiar cifras a mano.
- **Umbrales** (convención de industria para PD de consumo; están en el script y en el informe):
  Gini ≥ 0,40 / 0,25–0,40 / < 0,25 · KS ≥ 0,30 / 0,20–0,30 / < 0,20 · caída de Gini < 10% / 10–20% / > 20% ·
  PSI/CSI < 0,10 / 0,10–0,25 / > 0,25 · brecha relativa de calibración < 10% / 10–20% / > 20% ·
  bandas con subestimación 0 / 1–2 / ≥ 3 · Gini vs. grado LC ≥ 0 / hasta −5 / < −5 pts.
  Hosmer-Lemeshow y PSI aprobados vs. rechazados: **informativos** (no semáforo; razones en D11 y D10).
- **Resultado:** 4 🟢 · 5 🟡 · 2 🔴. Rojos: CSI 2018 (`revol_util`) y bandas subestimadas del modelo **original**
  (la versión recalibrada pasa a 1 banda 🟡).
- **Conclusión del informe:** aprobado con condiciones — usar la versión recalibrada con MoC, dentro del dominio
  FICO ≥ 660 / DTI ≤ 35 (corregido en D16), con monitoreo anual de calibración y trimestral de estabilidad.
- Los umbrales de Gini/KS varían entre instituciones; un Gini de 0,325 es razonable para consumo no garantizado
  sobre población ya filtrada, pero se marca 🟡 por consistencia con el umbral elegido.

## D16. Condiciones del informe implementadas — `src/credit_risk/model.py`, `src/credit_risk/monitoring.py`
- **Modelo oficial** `models/pd_model_final.pkl` (clase `PDModel`, generado por `06_recalibration.py`):
  scorecard + ajuste de intercepto **+0,184** (recalibración a 2014 + MoC por tendencia) + dominio.
- **Dominio = rangos vistos en train 2013:** FICO ≥ 660 y **DTI ≤ 34,99**. Corrige el "DTI ≤ 39" de D10, que salía
  del p99,5 de *todos* los aprobados 2013–15: en 2013 el tope de LC era 35, así que el modelo nunca vio DTI > 35.
  Fuera de dominio `predict_pd` y `score` devuelven NaN (no extrapola).
- **Hallazgo:** LC subió el tope de DTI a 40 en 2014. En OOT 2015 el **3,4%** de los préstamos está fuera de dominio
  y su default es **22,6%** (vs. 14,6% dentro). Dentro de dominio el modelo oficial estima **14,9% vs. 14,6%**
  observado y **0 de 10 bandas** subestiman. Parte de la descalibración de D9/D11 venía de esos casos.
  (El dominio se definió solo con train; OOT se usó para medir, no para elegir el corte.)
- **Monitoreo** (`notebooks/09_monitoring.py` → `reports/monitoring.csv`): por cohorte, PSI del score, CSI máximo,
  % fuera de dominio y, si hay resultado, calibración y bandas. Resultado: PSI verde hasta 2018; CSI de `revol_util`
  ámbar en 2016–17 y rojo en 2018; fuera de dominio sube de 3,4% (2015) a 6,4% (2018).
- **Disparadores de reentrenamiento propuestos:** PSI del score > 0,10, CSI > 0,25 en una variable con peso alto, o
  fuera de dominio > 5% → 2018 ya dispara por CSI y por dominio.
