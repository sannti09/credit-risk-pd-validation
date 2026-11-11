# Informe de validación independiente — Scorecard PD (Lending Club, 36 meses)

*Generado automáticamente por `notebooks/08_validation_report.py` el 2026-11-10. No editar a mano.*

## 1. Alcance
- **Modelo:** scorecard logístico sobre WoE, 13 variables de solicitud y buró; escala 600 = 50:1, PDO 20.
- **Uso previsto:** PD de originación (vida del préstamo a 36 meses) para solicitantes que cumplen la política de
  Lending Club (**FICO ≥ 660, DTI ≤ 34,99**, rangos vistos en desarrollo). Fuera de ese dominio el modelo no entrega PD (D16).
- **Muestras:** desarrollo 2013 · validación 2014 · *out-of-time* (OOT) 2015 · estabilidad 2016–2018 (sin resultado).
- **Fuera de alcance:** préstamos a 60 meses, PD a 12 meses / NIIF 9 (fase siguiente).

## 2. Resumen de semáforos
Umbrales: verde / ámbar / rojo. 6 🟢 · 5 🟡 · 2 🔴

| Dimensión | Prueba | Resultado | Umbral (verde / ámbar / rojo) | Semáforo |
|---|---|---|---|---|
| Discriminación | Gini OOT 2015 | 0.325 | ≥ 0,40 / 0,25–0,40 / < 0,25 | 🟡 ámbar |
| Discriminación | KS OOT 2015 | 0.237 | ≥ 0,30 / 0,20–0,30 / < 0,20 | 🟡 ámbar |
| Discriminación | Caída de Gini train → OOT | 0.3% | < 10% / 10–20% / > 20% | 🟢 verde |
| Benchmark | Gini propio − Gini grado LC (OOT) | -3.2 pts | ≥ 0 / hasta −5 / < −5 pts | 🟡 ámbar |
| Estabilidad | PSI del score, máx. 2014–2018 | 0.081 (2018) | < 0,10 / 0,10–0,25 / > 0,25 | 🟢 verde |
| Estabilidad | CSI máx. por variable, OOT 2015 | 0.060 | < 0,10 / 0,10–0,25 / > 0,25 | 🟢 verde |
| Estabilidad | CSI máx. por variable, 2018 | 0.382 (revol_util) | < 0,10 / 0,10–0,25 / > 0,25 | 🔴 rojo |
| Calibración (original) | Brecha relativa PD vs. default, OOT | 13.1% | < 10% / 10–20% / > 20% | 🟡 ámbar |
| Calibración (original) | Bandas con subestimación significativa (binomial) | 9 de 10 | 0 / 1–2 / ≥ 3 | 🔴 rojo |
| Calibración (recalibrado + MoC) | Brecha relativa PD vs. default, OOT | 1.1% | < 10% / 10–20% / > 20% | 🟢 verde |
| Calibración (recalibrado + MoC) | Bandas con subestimación significativa (binomial) | 1 de 10 | 0 / 1–2 / ≥ 3 | 🟡 ámbar |
| Modelo oficial (dentro de dominio) | Brecha relativa PD vs. default, OOT | 1.7% | < 10% / 10–20% / > 20% | 🟢 verde |
| Modelo oficial (dentro de dominio) | Bandas con subestimación significativa (binomial) | 0 de 10 | 0 / 1–2 / ≥ 3 | 🟢 verde |
| Dominio | % de solicitudes fuera de dominio (2015 → 2018) | 3.4% → 6.4% | informativo: se les niega PD; default fuera de dominio en 2015 = 22.6% | ℹ️ info |
| Calibración | Hosmer-Lemeshow OOT (p-valor) | 0.000 → 0.000 | informativo: con n ≈ 283 mil rechaza diferencias mínimas | ℹ️ info |
| Representatividad | PSI aprobados vs. rechazados (FICO) | 0.89 | informativo: diferencia esperada por la política de LC | ℹ️ info |

## 3. Hallazgos
| # | Severidad | Hallazgo | Recomendación |
|---|---|---|---|
| H1 | Alta | **Subestimación de la PD:** el modelo original estima 13.0% frente a 14.9% observado en OOT; 9 de 10 bandas subestiman. Causa: el default sube ~1,4 pts por año. | **Aplicado:** modelo oficial recalibrado con MoC; dentro de dominio estima 14.9% vs. 14.6% observado, 0 bandas subestimadas. Reestimar el MoC cada año. |
| H2 | Media | **Poder discriminante moderado:** Gini OOT 0.325, 3.2 pts por debajo del grado de LC. | Aceptable para uso con datos públicos. El challenger GBM regularizado llega a 0.340: evaluar si la ganancia justifica la menor explicabilidad. |
| H3 | Media | **Deriva de población en 2017–2018:** CSI de `revol_util` = 0.38 y de `percent_bc_gt_75` = 0.37 en 2018; el PSI del score sigue en verde. | Monitoreo trimestral de CSI; disparar revisión si el PSI del score supera 0,10. |
| H4 | Media | **Sesgo de selección y dominio:** el modelo solo observa aprobados (59% de los rechazados con FICO válido está bajo 660). Además LC subió su tope de DTI de 35 a 40 en 2014: en 2015 el 3.4% de los préstamos tiene DTI > 35, con default de 22.6%. | **Aplicado:** fuera de dominio el modelo devuelve PD vacía. Esos casos requieren otra política o un modelo reentrenado con DTI > 35. |
| H5 | Baja | **OOT no 100% ciego:** la idea del MoC surgió tras observar la brecha en 2015 (D14). | Confirmar la calibración con la primera cohorte madura nueva. |

## 4. Limitaciones
- Datos de 2013–2015 de una plataforma P2P de EE. UU.: solo fines demostrativos.
- Sin LGD/EAD observadas en este análisis (fase NIIF 9).
- Validación 2014 optimista (se usó para decisiones de modelado). La referencia es OOT 2015.
- Detalle completo de decisiones y limitaciones: `docs/decisiones.md` (D1–D14).

## 5. Conclusión
**Aprobado con condiciones — condiciones implementadas** (`src/credit_risk/model.py`, `models/pd_model_final.pkl`):
1. La PD sale siempre recalibrada con MoC (ajuste de intercepto +0.184).
2. Fuera del dominio (FICO ≥ 660, DTI ≤ 34,99) el modelo no entrega PD.
3. Monitoreo por cohorte en `notebooks/09_monitoring.py` (PSI, CSI, % fuera de dominio, calibración).

Pendiente de seguimiento: CSI de `revol_util` en rojo en 2018 y el aumento de solicitudes fuera de dominio
(6.4% en 2018) → candidatos a disparar el reentrenamiento.
