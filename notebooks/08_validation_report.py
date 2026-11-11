"""Genera el informe de validación con semáforos a partir de reports/*.csv. Ver D15.
Salida: reports/informe_validacion.md (se regenera; no editar a mano)."""
from datetime import date

import pickle

import pandas as pd

R = "reports/"
EMOJI = {"verde": "🟢", "ámbar": "🟡", "rojo": "🔴", "info": "ℹ️"}

# Umbrales (convención de industria para PD de consumo; se documentan en el informe)
TH = {
    "gini": (0.40, 0.25),          # verde >= 0,40 · ámbar 0,25–0,40 · rojo < 0,25
    "ks": (0.30, 0.20),            # verde >= 0,30 · ámbar 0,20–0,30 · rojo < 0,20
    "caida_gini": (0.10, 0.20),    # caída relativa train -> OOT: verde < 10% · ámbar 10–20% · rojo > 20%
    "psi": (0.10, 0.25),           # verde < 0,10 · ámbar 0,10–0,25 · rojo > 0,25
    "bandas_rojas": (0, 2),        # binomial por banda: verde 0 · ámbar 1–2 · rojo >= 3
    "brecha_rel": (0.10, 0.20),    # |PD - default| / default: verde < 10% · ámbar 10–20% · rojo > 20%
    "vs_benchmark": (0.0, -0.05),  # Gini propio - Gini LC: verde >= 0 · ámbar hasta -5 pts · rojo peor
}


def up(v, k):  # más alto es mejor
    g, a = TH[k]
    return "verde" if v >= g else ("ámbar" if v >= a else "rojo")


def down(v, k):  # más bajo es mejor
    g, a = TH[k]
    return "verde" if v < g else ("ámbar" if v <= a else "rojo")


def bands(n):  # bandas con subestimación significativa
    g, a = TH["bandas_rojas"]
    return "verde" if n <= g else ("ámbar" if n <= a else "rojo")


perf = pd.read_csv(R + "performance.csv")
# PSI del MODELO OFICIAL (recalibrado, dentro de dominio), misma fuente que el tablero (D31)
psi = pd.read_csv(R + "monitoring.csv", index_col=0).rename_axis("muestra")[["psi_score"]]
csi = pd.read_csv(R + "val_csi.csv", index_col=0)
cal = pd.read_csv(R + "val_calibration.csv").set_index("muestra")
rec = pd.read_csv(R + "recalibration_oot.csv").set_index("metodo")
chal = pd.read_csv(R + "challenger_performance.csv")
repr_ = pd.read_csv(R + "repr_psi.csv").set_index("variable")
mon = pd.read_csv(R + "monitoring.csv", index_col=0)
delta = pickle.load(open("models/pd_model_final.pkl", "rb")).delta


def g(muestra, modelo, col="gini"):
    return float(perf[(perf.muestra == muestra) & (perf.modelo == modelo)][col].iloc[0])


sc = "scorecard propio"
gini_tr, gini_oot, ks_oot = g("train 2013", sc), g("oot 2015", sc), g("oot 2015", sc, "ks")
caida = max(0.0, (gini_tr - gini_oot) / gini_tr)
vs_lc = gini_oot - g("oot 2015", "LC sub_grade")
gbm_oot = float(chal[(chal.muestra == "oot 2015") & chal.modelo.str.startswith("gbm")].gini.iloc[0])
orig, moc = rec.loc["original"], rec.loc["intercepto + MoC tendencia"]
brecha = lambda r: abs(r.pd_media - r.dr_obs) / r.dr_obs  # noqa: E731
psi_max = psi.psi_score.max()
csi_2018 = csi["2018"].sort_values(ascending=False)
csi_max_oot = csi["oot 2015"].max()

# (dimensión, prueba, resultado, umbral, semáforo)
rows = [
    ("Discriminación", "Gini OOT 2015", f"{gini_oot:.3f}", "≥ 0,40 / 0,25–0,40 / < 0,25", up(gini_oot, "gini")),
    ("Discriminación", "KS OOT 2015", f"{ks_oot:.3f}", "≥ 0,30 / 0,20–0,30 / < 0,20", up(ks_oot, "ks")),
    ("Discriminación", "Caída de Gini train → OOT", f"{100 * caida:.1f}%", "< 10% / 10–20% / > 20%",
     down(caida, "caida_gini")),
    ("Benchmark", "Gini propio − Gini grado LC (OOT)", f"{100 * vs_lc:+.1f} pts", "≥ 0 / hasta −5 / < −5 pts",
     up(vs_lc, "vs_benchmark")),
    ("Estabilidad", "PSI del score, máx. 2014–2018", f"{psi_max:.3f} ({psi.psi_score.idxmax()})",
     "< 0,10 / 0,10–0,25 / > 0,25", down(psi_max, "psi")),
    ("Estabilidad", "CSI máx. por variable, OOT 2015", f"{csi_max_oot:.3f}", "< 0,10 / 0,10–0,25 / > 0,25",
     down(csi_max_oot, "psi")),
    ("Estabilidad", "CSI máx. por variable, 2018", f"{csi_2018.iloc[0]:.3f} ({csi_2018.index[0]})",
     "< 0,10 / 0,10–0,25 / > 0,25", down(csi_2018.iloc[0], "psi")),
    ("Calibración (original)", "Brecha relativa PD vs. default, OOT", f"{100 * brecha(orig):.1f}%",
     "< 10% / 10–20% / > 20%", down(brecha(orig), "brecha_rel")),
    ("Calibración (original)", "Bandas con subestimación significativa (binomial)", f"{int(orig.bandas_rojas)} de 10",
     "0 / 1–2 / ≥ 3", bands(orig.bandas_rojas)),
    ("Calibración (recalibrado + MoC)", "Brecha relativa PD vs. default, OOT", f"{100 * brecha(moc):.1f}%",
     "< 10% / 10–20% / > 20%", down(brecha(moc), "brecha_rel")),
    ("Calibración (recalibrado + MoC)", "Bandas con subestimación significativa (binomial)",
     f"{int(moc.bandas_rojas)} de 10", "0 / 1–2 / ≥ 3", bands(moc.bandas_rojas)),
    ("Modelo oficial (dentro de dominio)", "Brecha relativa PD vs. default, OOT",
     f"{100 * abs(mon.loc['oot 2015', 'pd_media'] - mon.loc['oot 2015', 'dr_obs']) / mon.loc['oot 2015', 'dr_obs']:.1f}%",
     "< 10% / 10–20% / > 20%",
     down(abs(mon.loc['oot 2015', 'pd_media'] - mon.loc['oot 2015', 'dr_obs']) / mon.loc['oot 2015', 'dr_obs'], "brecha_rel")),
    ("Modelo oficial (dentro de dominio)", "Bandas con subestimación significativa (binomial)",
     f"{int(mon.loc['oot 2015', 'bandas_subestimadas'])} de 10", "0 / 1–2 / ≥ 3",
     bands(int(mon.loc['oot 2015', 'bandas_subestimadas']))),
    ("Dominio", "% de solicitudes fuera de dominio (2015 → 2018)",
     f"{mon.loc['oot 2015', 'pct_fuera_dominio']:.1f}% → {mon.loc['2018', 'pct_fuera_dominio']:.1f}%",
     "informativo: se les niega PD; default fuera de dominio en 2015 = "
     f"{100 * mon.loc['oot 2015', 'dr_fuera_dominio']:.1f}%", "info"),
    ("Calibración", "Hosmer-Lemeshow OOT (p-valor)", f"{orig.hl_p:.3f} → {moc.hl_p:.3f}",
     "informativo: con n ≈ 283 mil rechaza diferencias mínimas", "info"),
    ("Representatividad", "PSI aprobados vs. rechazados (FICO)", f"{repr_.loc['risk_score', 'psi']:.2f}",
     "informativo: diferencia esperada por la política de LC", "info"),
]

tabla = "\n".join(f"| {d} | {p} | {r} | {u} | {EMOJI[s]} {s} |" for d, p, r, u, s in rows)
conteo = pd.Series([s for *_, s in rows if s != "info"]).value_counts()

md = f"""# Informe de validación independiente — Scorecard PD (Lending Club, 36 meses)

*Generado automáticamente por `notebooks/08_validation_report.py` el {date.today():%Y-%m-%d}. No editar a mano.*

## 1. Alcance
- **Modelo:** scorecard logístico sobre WoE, 13 variables de solicitud y buró; escala 600 = 50:1, PDO 20.
- **Uso previsto:** PD de originación (vida del préstamo a 36 meses) para solicitantes que cumplen la política de
  Lending Club (**FICO ≥ 660, DTI ≤ 34,99**, rangos vistos en desarrollo). Fuera de ese dominio el modelo no entrega PD (D16).
- **Muestras:** desarrollo 2013 · validación 2014 · *out-of-time* (OOT) 2015 · estabilidad 2016–2018 (sin resultado).
- **Fuera de alcance:** préstamos a 60 meses. La ECL NIIF 9 se documenta aparte (README y D17–D21).

## 2. Resumen de semáforos
Umbrales: verde / ámbar / rojo. {conteo.get('verde', 0)} 🟢 · {conteo.get('ámbar', 0)} 🟡 · {conteo.get('rojo', 0)} 🔴

| Dimensión | Prueba | Resultado | Umbral (verde / ámbar / rojo) | Semáforo |
|---|---|---|---|---|
{tabla}

## 3. Hallazgos
| # | Severidad | Hallazgo | Recomendación |
|---|---|---|---|
| H1 | Alta | **Subestimación de la PD:** el modelo original estima {100 * orig.pd_media:.1f}% frente a {100 * orig.dr_obs:.1f}% observado en OOT; {int(orig.bandas_rojas)} de 10 bandas subestiman. Causa: el default sube ~1,4 pts por año. | **Aplicado:** modelo oficial recalibrado con MoC; dentro de dominio estima {100 * mon.loc['oot 2015', 'pd_media']:.1f}% vs. {100 * mon.loc['oot 2015', 'dr_obs']:.1f}% observado, 0 bandas subestimadas. Reestimar el MoC cada año. |
| H2 | Media | **Poder discriminante moderado:** Gini OOT {gini_oot:.3f}, {100 * abs(vs_lc):.1f} pts por debajo del grado de LC. | Aceptable para uso con datos públicos. El challenger GBM regularizado llega a {gbm_oot:.3f}: evaluar si la ganancia justifica la menor explicabilidad. |
| H3 | Media | **Deriva de población en 2017–2018:** CSI de `{csi_2018.index[0]}` = {csi_2018.iloc[0]:.2f} y de `{csi_2018.index[1]}` = {csi_2018.iloc[1]:.2f} en 2018; el PSI del score sigue en verde. | Monitoreo trimestral de CSI; disparar revisión si el PSI del score supera 0,10. |
| H4 | Media | **Sesgo de selección y dominio:** el modelo solo observa aprobados (59% de los rechazados con FICO válido está bajo 660). Además LC subió su tope de DTI de 35 a 40 en 2014: en 2015 el {mon.loc['oot 2015', 'pct_fuera_dominio']:.1f}% de los préstamos tiene DTI > 35, con default de {100 * mon.loc['oot 2015', 'dr_fuera_dominio']:.1f}%. | **Aplicado:** fuera de dominio el modelo devuelve PD vacía. Esos casos requieren otra política o un modelo reentrenado con DTI > 35. |
| H5 | Baja | **OOT no 100% ciego:** la idea del MoC surgió tras observar la brecha en 2015 (D14). | Confirmar la calibración con la primera cohorte madura nueva. |

## 4. Limitaciones
- Datos de 2013–2015 de una plataforma P2P de EE. UU.: solo fines demostrativos.
- Validación 2014 optimista (se usó para decisiones de modelado). La referencia es OOT 2015.
- Detalle completo de decisiones y limitaciones: `docs/decisiones.md`.

## 5. Conclusión
**Aprobado con condiciones — condiciones implementadas** (`src/credit_risk/model.py`, `models/pd_model_final.pkl`):
1. La PD sale siempre recalibrada con MoC (ajuste de intercepto {delta:+.3f}).
2. Fuera del dominio (FICO ≥ 660, DTI ≤ 34,99) el modelo no entrega PD.
3. Monitoreo por cohorte en `notebooks/09_monitoring.py` (PSI, CSI, % fuera de dominio, calibración).

Pendiente de seguimiento: CSI de `revol_util` en rojo en 2018 y el aumento de solicitudes fuera de dominio
({mon.loc['2018', 'pct_fuera_dominio']:.1f}% en 2018) → candidatos a disparar el reentrenamiento.
"""
open(R + "informe_validacion.md", "w").write(md)

# ---- Versión en inglés: mismas cifras y semáforos, solo cambia el texto (D34) ----
import re  # noqa: E402

ST = {"verde": "green", "ámbar": "amber", "rojo": "red", "info": "info"}
DIM = {"Discriminación": "Discrimination", "Estabilidad": "Stability", "Calibración (original)": "Calibration (original)",
       "Calibración (recalibrado + MoC)": "Calibration (recalibrated + MoC)", "Calibración": "Calibration",
       "Modelo oficial (dentro de dominio)": "Official model (in domain)", "Dominio": "Domain",
       "Representatividad": "Representativeness"}
TEST = {"Caída de Gini train → OOT": "Gini drop, train → OOT",
        "Gini propio − Gini grado LC (OOT)": "Own Gini − LC grade Gini (OOT)",
        "PSI del score, máx. 2014–2018": "Score PSI, max. 2014–2018",
        "CSI máx. por variable, OOT 2015": "Max. variable CSI, OOT 2015",
        "CSI máx. por variable, 2018": "Max. variable CSI, 2018",
        "Brecha relativa PD vs. default, OOT": "Relative gap PD vs. default rate, OOT",
        "Bandas con subestimación significativa (binomial)": "Bands significantly under-predicted (binomial)",
        "% de solicitudes fuera de dominio (2015 → 2018)": "% of applications out of domain (2015 → 2018)",
        "Hosmer-Lemeshow OOT (p-valor)": "Hosmer-Lemeshow OOT (p-value)",
        "PSI aprobados vs. rechazados (FICO)": "PSI approved vs. rejected (FICO)"}
TXT = {" de 10": " of 10", "hasta −5": "down to −5",
       "informativo: se les niega PD; default fuera de dominio en 2015 = ":
           "informative: no PD is issued; 2015 out-of-domain default rate = ",
       "informativo: con n ≈ 283 mil rechaza diferencias mínimas": "informative: with n ≈ 283k it rejects tiny gaps",
       "informativo: diferencia esperada por la política de LC": "informative: expected given LC's credit policy"}


def en(t):
    for a, b in TXT.items():
        t = t.replace(a, b)
    return re.sub(r"(\d),(\d)", r"\1.\2", t)


tabla_en = "\n".join(f"| {DIM.get(d, d)} | {TEST.get(p, p)} | {en(r)} | {en(u)} | {EMOJI[s]} {ST[s]} |"
                      for d, p, r, u, s in rows)
md_en = f"""# Independent validation report — PD scorecard (Lending Club, 36-month loans)

*Generated automatically by `notebooks/08_validation_report.py` on {date.today():%Y-%m-%d}. Do not edit by hand.
Spanish version: [`informe_validacion.md`](informe_validacion.md).*

## 1. Scope
- **Model:** logistic scorecard on WoE, 13 application and bureau variables; scale 600 = 50:1 odds, PDO 20.
- **Intended use:** origination PD (36-month loan lifetime) for applicants within Lending Club's policy (**FICO ≥ 660,
  DTI ≤ 34.99**, the ranges seen in development). Outside that domain the model issues no PD.
- **Samples:** development 2013 · validation 2014 · out-of-time (OOT) 2015 · stability 2016–2018 (no outcomes yet).
- **Out of scope:** 60-month loans. The IFRS 9 expected credit loss is documented separately (README).

## 2. Traffic-light summary
Thresholds: green / amber / red. {conteo.get('verde', 0)} 🟢 · {conteo.get('ámbar', 0)} 🟡 · {conteo.get('rojo', 0)} 🔴

| Dimension | Test | Result | Threshold (green / amber / red) | Status |
|---|---|---|---|---|
{tabla_en}

## 3. Findings
| # | Severity | Finding | Recommendation |
|---|---|---|---|
| F1 | High | **PD under-estimation:** the original model predicts {100 * orig.pd_media:.1f}% against {100 * orig.dr_obs:.1f}% observed out of time; {int(orig.bandas_rojas)} of 10 bands are significantly under-predicted. Cause: the default rate rises ~1.4 points per year. | **Implemented:** official model recalibrated with a margin of conservatism; within its domain it predicts {100 * mon.loc['oot 2015', 'pd_media']:.1f}% vs. {100 * mon.loc['oot 2015', 'dr_obs']:.1f}% observed, with no band significantly under-predicted. Re-estimate the margin yearly. |
| F2 | Medium | **Moderate discriminatory power:** OOT Gini {gini_oot:.3f}, {100 * abs(vs_lc):.1f} points below Lending Club's grade. | Acceptable given public data only. The regularized gradient-boosting challenger reaches {gbm_oot:.3f}: assess whether the gain justifies lower explainability. |
| F3 | Medium | **Population drift in 2017–2018:** CSI of `{csi_2018.index[0]}` = {csi_2018.iloc[0]:.2f} and of `{csi_2018.index[1]}` = {csi_2018.iloc[1]:.2f} in 2018; the score PSI stays green. | Quarterly CSI monitoring; trigger a review if the score PSI exceeds 0.10. |
| F4 | Medium | **Selection bias and domain:** the model only observes approved loans (59% of rejected applicants with a valid FICO are below 660). Lending Club also raised its DTI cap from 35 to 40 in 2014: in 2015, {mon.loc['oot 2015', 'pct_fuera_dominio']:.1f}% of loans have DTI > 35, with a {100 * mon.loc['oot 2015', 'dr_fuera_dominio']:.1f}% default rate. | **Implemented:** out of domain the model returns no PD. Those cases need a separate policy or a model retrained with DTI > 35. |
| F5 | Low | **OOT not fully blind:** the idea of the margin of conservatism came after observing the 2015 gap. | Confirm calibration on the next mature cohort. |

## 4. Limitations
- 2013–2015 data from a US peer-to-peer platform: demonstrative purposes only.
- The 2014 validation sample is optimistic (it was used for modeling decisions); the reference is OOT 2015.
- Full decision log (in Spanish): `docs/decisiones.md`.

## 5. Conclusion
**Approved with conditions — conditions implemented** (`src/credit_risk/model.py`, `models/pd_model_final.pkl`):
1. The PD is always recalibrated with the margin of conservatism (intercept adjustment {delta:+.3f}).
2. Outside the domain (FICO ≥ 660, DTI ≤ 34.99) the model issues no PD.
3. Cohort monitoring in `notebooks/09_monitoring.py` (PSI, CSI, % out of domain, calibration).

To follow up: `revol_util` CSI red in 2018 and the rise in out-of-domain applications
({mon.loc['2018', 'pct_fuera_dominio']:.1f}% in 2018) → candidate retraining triggers.
"""
open(R + "validation_report.md", "w").write(md_en)
print(md_en[md_en.index("## 2."):md_en.index("## 3.")])
