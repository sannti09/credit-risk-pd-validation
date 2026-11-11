# Guía para construir el tablero en Tableau Public

Dos tableros a partir de los CSV de `reports/dashboard/` (solo agregados, se pueden publicar):

1. **Riesgo y validación del modelo**: curvas de cosecha, calibración, estabilidad, desempeño.
2. **Provisiones NIIF 9 vs. SFC**: indicadores, ECL por etapa, puente SFC → NIIF 9, sensibilidades.

Tiempo estimado: 2–3 horas la primera vez. Términos en inglés porque así aparecen en Tableau.

---

## Unidades de cada archivo (formatea el eje según esto)
| Archivo | Columnas en **fracción** (0,15 = 15%) → formato *Percentage* | Columnas ya en **%** (15 = 15%) → *Number* + sufijo "%" |
|---|---|---|
| vintage | tasa_default_acum | — |
| calibracion_bandas | — | obs, orig, final |
| monitoreo | pd_media, dr_obs, dr_fuera_dominio, psi_score, csi_max (índices, no %) | pct_fuera_dominio |
| ecl_etapas | — | cobertura_pct · (saldo y ecl en **US$ M**) |
| ecl_sensibilidad | — | var_vs_base_pct, pct_saldo_etapa2 · (ecl_musd en US$ M) |
| sfc_calificaciones | pd12_modelo | pct_saldo · (saldo, pe_A, pe_B en US$ M) |
| originacion | default_obs, pct_con_resultado | tasa_media · (monto en US$) |
| cartera | pd_aplicable_pond | — · (saldo en **US$**, no millones) |
| momento_default | pct_defaults, acumulado = **participación de los defaults** (suman 1), no tasa de default | — |
| desempeno_modelos | gini, ks (índices); pd_media, dr_obs | — |

"desempeno_modelos": la fila "scorecard (13 var.)" es el scorecard **sin recalibrar**; la recalibración no cambia el
Gini (mismo orden), solo el nivel de PD.

## 0. Preparación (10 min)

1. Instala **Tableau Public** (gratis): https://public.tableau.com → *Download the App*. Crea tu perfil público.
2. Abre Tableau Public → panel izquierdo **Connect → To a File → Text file** → elige
   `reports/dashboard/vintage.csv`.
3. Agrega los demás archivos como **fuentes separadas** (menú **Data → New Data Source → Text file**), uno por uno:
   `calibracion_bandas.csv`, `monitoreo.csv`, `desempeno_modelos.csv`, `ecl_etapas.csv`, `ecl_escenarios.csv`,
   `ecl_sensibilidad.csv`, `sfc_puente.csv`, `cartera.csv`.
   No los unas entre sí (no comparten llaves): cada gráfico usa su propio archivo.
4. En cada fuente revisa los tipos (íconos sobre las columnas): números como **Number (decimal)**, `mob` y `etapa`
   como **Number (whole)**; si `cosecha` sale como fecha, cámbiala a **String**.

**Regla de diseño para todo el tablero:** un solo eje por gráfico, colores con significado (no decorativos), títulos
que digan la conclusión ("El default sube con cada cosecha"), no solo el tema ("Default por cosecha").

---

## Tablero 1 — Riesgo y validación del modelo

### Hoja 1: Curvas de cosecha (`vintage.csv`)
*Mensaje: las cosechas más recientes incumplen más.*
1. Hoja nueva (ícono abajo) → renómbrala "Cosechas".
2. Arrastra **mob** a **Columns** (clic derecho → *Dimension*, *Continuous*).
3. Arrastra **tasa_default_acum** a **Rows** (agregación *SUM* está bien: hay una fila por cosecha y mes).
4. Arrastra **cosecha** a **Color** del panel *Marks* (tipo de marca: *Line*).
5. Filtra para que se lea: arrastra **cosecha** a **Filters** → marca solo las que terminan en **-Q1**
   (2013-Q1 … 2018-Q1). Seis líneas se leen; 24 no.
6. Formato: eje Y en porcentaje (clic derecho en el eje → *Format* → *Numbers: Percentage*, 0 decimales).
   Título del eje X: "Meses desde el desembolso".
7. Título: "El default acumulado sube con cada cosecha (2013 → 2016: 12,5% → 15,4% a 36 meses)".

### Hoja 2: Calibración por banda (`calibracion_bandas.csv`)
*Mensaje: el modelo original subestima; el oficial coincide con lo observado.*
1. **band** a **Columns** (*Discrete*). **Measure Values** a **Rows**.
2. En la tarjeta **Measure Values** deja solo **obs**, **orig** y **final** (quita las demás).
3. **Measure Names** a **Color**. Tipo de marca: *Line* con puntos (*Marks → Color → Markers*: con marcadores).
4. Renombra los alias (clic derecho en la leyenda → *Edit Aliases*): obs → "Default observado",
   orig → "Modelo original", final → "Modelo oficial (recalibrado)".
5. Eje en porcentaje (los valores ya están en %, así que formato *Number* con sufijo "%").
6. Título (en inglés, ver D31): "Band 1 = highest risk. The recalibrated model tracks observed defaults within ±2 pp;
   no band is significantly under-predicted". (No decir "coincide": en 2 bandas queda levemente por debajo, sin
   significancia estadística.)

### Hoja 3: Estabilidad (`monitoreo.csv`)
*Mensaje: el score es estable; algunas variables se mueven en 2018.*
1. **cohorte** a **Columns**. **psi_score** y **csi_max** con **Measure Values** a **Rows** (barras agrupadas:
   **Measure Names** a **Color** y también a **Columns** después de cohorte).
2. Líneas de referencia: clic derecho en el eje → *Add Reference Line* → valor constante **0,10** (etiqueta
   "Ámbar") y otra en **0,25** (etiqueta "Rojo"). Línea punteada gris.
3. Tooltip: agrega **csi_var** al panel *Tooltip* para que se vea qué variable tiene el CSI máximo.
4. Título: "PSI del score en verde hasta 2018; revol_util supera el umbral rojo en 2018".

### Hoja 4: Desempeño de los modelos (`desempeno_modelos.csv`)
1. **muestra** a **Columns**, **gini** a **Rows**, **modelo** a **Color** y a **Columns** (barras agrupadas).
2. Etiquetas: *Marks → Label* → mostrar valores con 3 decimales.
3. Título: "Gini fuera de muestra: scorecard 0,325 · GBM regularizado 0,340 · grado LC 0,357".

### Armar el tablero 1
1. Ícono **New Dashboard** (abajo). *Size* → **Automatic** o **Generic Desktop (1366 × 768)**.
2. Arrastra las 4 hojas en cuadrícula 2 × 2: Cosechas (arriba izq.), Calibración (arriba der.),
   Estabilidad (abajo izq.), Desempeño (abajo der.).
3. Agrega un **Text** arriba con el título: "Modelo de PD — Lending Club (36 meses): riesgo, calibración y
   estabilidad", y debajo una línea de contexto: "Validación out-of-time 2015. Fuente: Lending Club / Kaggle".

---

## Tablero 2 — Provisiones NIIF 9 vs. SFC

### Hoja 5: Indicadores clave (`ecl_escenarios.csv`, `ecl_etapas.csv`)
Tres "tarjetas" grandes. Para cada una: hoja nueva, tipo de marca *Text*, una sola medida en *Text*, fuente grande.
- **ECL ponderada**: `ecl_escenarios.csv`, filtra **escenario = ponderado**, muestra **ecl_musd** →
  "US$ 238,1 M".
- **Saldo de la cartera**: `ecl_etapas.csv`, **SUM(saldo)** → "US$ 4.638 M".
- **Cobertura**: campo calculado en `ecl_etapas.csv`: `SUM([ecl]) / SUM([saldo])` → formato porcentaje
  (≈ 4,8% base; la ponderada es 5,1%: aclara en el subtítulo cuál muestras).

### Hoja 6: ECL por etapa (`ecl_etapas.csv`)
1. **etapa** a **Rows** (*Discrete*), **ecl** a **Columns** → barras horizontales.
2. Etiqueta con **cobertura_pct** (Label) para mostrar "3,4% / 8,5% / 90,7%".
3. Título: "La etapa 3 es el 1% del saldo pero ~19% de la pérdida esperada".

### Hoja 7: Puente SFC → NIIF 9 (cascada, `sfc_puente.csv`)
*Mensaje: la Matriz A y NIIF 9 coinciden por compensación de efectos.*
1. **paso** a **Columns**. Ordénalo manualmente en el orden del archivo (clic derecho → *Sort* → *Manual*).
2. Excluye la fila "NIIF 9 base" (clic derecho → *Exclude*): la cascada la calcula sola.
3. Campo calculado **Acumulado**: `RUNNING_SUM(SUM([efecto_musd]))` → a **Rows**.
4. Tipo de marca **Gantt Bar**. Campo calculado **Tamaño**: `-SUM([efecto_musd])` → a **Size**.
5. Campo calculado **Signo**: `IF SUM([efecto_musd]) >= 0 THEN "Sube" ELSE "Baja" END` → a **Color**
   (la primera barra, "SFC Matriz A", es el punto de partida: puedes darle un color neutro).
6. *Analysis → Totals → Show Row Grand Totals* para la barra final (o una línea de referencia en 223,6).
7. Título: "De la provisión SFC (Matriz A) a la ECL NIIF 9: +43 PDI, +11 PD, +26 etapa 2, −65 amortización, −12 descuento".

### Hoja 8: Sensibilidades (`ecl_sensibilidad.csv`)
1. **supuesto** a **Rows**, **var_vs_base_pct** a **Columns** → barras horizontales.
2. Ordena por **var_vs_base_pct** descendente. Color por signo (campo calculado como en la hoja 7).
3. Línea de referencia en 0.
4. Título: "Qué supuestos mueven la ECL: la regla de etapas pesa más que los juicios expertos".

### Armar el tablero 2
1. Fila superior: las tres tarjetas de indicadores.
2. Fila media: ECL por etapa (izq.) y Puente SFC → NIIF 9 (der., más ancho).
3. Fila inferior: Sensibilidades.
4. Texto de contexto: "Cartera viva al corte (mar-2019), 582.796 préstamos. ECL con escenarios ponderados;
   provisión SFC con matrices del MRCO (CE 047 de 2016)".

---

## Publicar
1. **File → Save to Tableau Public** (te pide iniciar sesión). Nombre: "Credit Risk PD & IFRS 9 — Lending Club".
2. En tu perfil de Tableau Public, abre el libro → **Share** → copia el enlace.
3. Pásame el enlace y lo agrego al README (y al CV / LinkedIn).

## Revisión antes de publicar (checklist)
- [ ] Cada gráfico tiene un título que dice la conclusión.
- [ ] Ningún gráfico tiene dos ejes con escalas distintas.
- [ ] Ejes en porcentaje donde corresponde; montos en US$ M.
- [ ] Colores consistentes entre hojas (p. ej., "modelo oficial" siempre del mismo color).
- [ ] Una línea de fuente y fecha de corte en cada tablero.
- [ ] Nada de datos a nivel de préstamo (todo viene de `reports/dashboard/`, que es agregado).

---

## Hojas 3–5 — versión actualizada (D32; reemplaza las hojas 3, 4 y 5 de arriba)
Archivos nuevos, ya en inglés: `stability_csi.csv`, `model_performance.csv`, `kpis.csv`.

### Hoja 3 — Stability: mapa de calor (`stability_csi.csv`)
1. Data → New Data Source → `stability_csi.csv`. Hoja nueva → pestaña **Stability**.
2. **year** a Columns (Discrete), **variable** a Rows, **csi** a **Color** (Marks: *Square*).
3. Colores: Color → Edit Colors → *Stepped Color*, 3 pasos, rango 0–0.25+ (verde → ámbar → rojo); o arrastra
   **status** a Color y asigna verde/ámbar/rojo a mano (más claro para el lector).
4. **csi** a **Label** (formato número, 2 decimales). En Color va **status** o **csi**, no ambos. Orden: clic
   derecho en variable → Sort → por **csi** (suma de todos los años; ordenar solo por 2018 requiere un cálculo extra).
5. Título: **Population drift is concentrated in 2017–2018** / gris: *CSI by variable vs. the 2013 development
   sample. Revolving utilization and card usage cross the red threshold (0.25) in 2018 → retraining trigger.*

### Hoja 4 — Model performance: barras horizontales (`model_performance.csv`)
1. Data → New Data Source → `model_performance.csv`. Hoja nueva → pestaña **Performance**.
2. **sample** a Filters → deja solo **Out-of-time 2015**. **model** a Rows, **gini** a Columns (barras).
3. Color: Scorecard = azul (el oficial), Gradient boosting = gris medio, Lending Club grade = gris claro.
4. **gini** a Label (3 decimales). Línea de referencia opcional: ninguna (no hay umbral universal).
5. Título: **Out-of-sample Gini: own models vs. Lending Club's grade** / gris: *The scorecard (0.325) uses only
   application and bureau data; LC's grade (0.357) used proprietary information. Recalibration does not change Gini.*

### Hoja 5 — Key figures: tarjetas (`kpis.csv`)
Una hoja por cifra (3 tarjetas: ECL, cobertura, saldo).
1. Data → New Data Source → `kpis.csv`. Hoja nueva → pestaña **KPI ECL**.
2. **kpi** a Filters → solo "Expected credit loss (IFRS 9, weighted)". Marks: *Text*. **value** a Text.
3. Clic en Text → edita: `US$ <SUM(value)> M` en tamaño 28 negrita; debajo `Expected credit loss (IFRS 9)` en 11 gris.
4. Duplica la hoja (clic derecho en la pestaña → *Duplicate*) y cambia el filtro: "Coverage (ECL / balance)"
   → `<SUM(value)>%`; "Live portfolio balance" → `US$ <SUM(value)> M`.
5. Sin título de hoja: menú **Worksheet → Show Title** (desmárcalo). El texto ya lo dice.

## Hojas 6–8 — versión actualizada (D32; reemplaza las hojas 6, 7 y 8 de arriba)
Archivos nuevos en inglés: `stage_mix.csv`, `bridge.csv`, `sensitivity.csv`.

### Hoja 6 — ECL by stage: barras apiladas al 100% (`stage_mix.csv`)
1. **metric** a Rows, **share** a Columns, **stage** a Color. Marks: *Bar* (salen 2 barras apiladas).
2. Colores: Stage 1 gris claro, Stage 2 ámbar, Stage 3 rojo. **share** a Label (formato %, 0 decimales).
3. Título: **Stage 3 is 1% of the balance but 19% of expected loss** / gris: *Live portfolio at Mar-2019,
   US$ 4,638 M. Stage 3 = 90+ days past due.*

### Hoja 7 — SFC → IFRS 9 bridge: cascada (`bridge.csv`)
1. **step** a Columns; ordénalo por **order** (clic derecho → Sort → Field: order, ascendente).
2. Marks: **Gantt Bar**. **bar_base** a Rows. **bar_length** a **Size** (siempre positivo: la barra va de
   bar_base hacia arriba; así no dependemos de tamaños negativos, D32).
3. **kind** a Color: Start y Total azul oscuro, Increase rojo, Decrease verde.
4. **effect** a Label (US$ M, 1 decimal). Rota los nombres del eje X si no caben (clic derecho → Rotate Label).
5. Título: **Why the SFC provision and IFRS 9 ECL nearly coincide** / gris: *Offsetting effects: higher observed LGD
   and lifetime horizon add; amortization and discounting subtract. US$ M.*

### Hoja 8 — Sensitivities: barras divergentes (`sensitivity.csv`)
1. **assumption** a Rows, **change_vs_base_pct** a Columns. Ordena por change_vs_base_pct (descendente).
2. **direction** a Color: Raises ECL rojo, Lowers ECL verde. Línea en 0: pestaña Analytics → arrastra
   **Constant Line** (o *Reference Line* → Constant) al gráfico → valor 0.
3. **change_vs_base_pct** a Label: clic derecho → Format → Numbers → **Custom**: `+0.0"%";-0.0"%";0.0"%"`
   (tres secciones: positivo; negativo; cero).
4. Título: **What moves the ECL: staging rules matter more than expert judgments** / gris: *Change vs. base ECL
   (US$ 223.6 M), one assumption at a time. Basel's 45% LGD excluded (not applicable to this portfolio).*
