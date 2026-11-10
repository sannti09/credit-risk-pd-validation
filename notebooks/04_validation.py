"""Fase 3: validación del scorecard. Ver docs/decisiones.md (D7).
Salidas: reports/val_calibration.csv, reports/val_binomial_oot.csv, reports/val_psi.csv, reports/val_csi.csv"""
import pickle

import duckdb
import numpy as np
import pandas as pd
import statsmodels.api as sm

from credit_risk.scorecard import score_from_logit
from credit_risk.validation import binomial_by_band, hosmer_lemeshow, p_light, psi, psi_light

art = pickle.load(open("models/scorecard.pkl", "rb"))
b, m, cols = art["binner"], art["model"], art["features"]
con = duckdb.connect("data/credit.duckdb", read_only=True)
samples = {
    "train 2013": con.sql("select * from model_sample where split='train'").df(),
    "valid 2014": con.sql("select * from model_sample where split='valid'").df(),
    "oot 2015": con.sql("select * from model_sample where split='oot'").df(),
}
for y in (2016, 2017, 2018):  # solicitantes recientes: sin resultado maduro, solo para estabilidad
    samples[str(y)] = con.sql(f"select * from loans where term_months=36 and issue_year={y}").df()

for d in samples.values():
    lin = m.predict(sm.add_constant(b.transform(d)[cols], has_constant="add"), which="linear")
    d["pd"] = 1 / (1 + np.exp(-lin))
    d["score"] = score_from_logit(lin)

# Bandas de rating: deciles del score en train (1 = más riesgo)
edges = np.quantile(samples["train 2013"]["score"], np.linspace(0, 1, 11))
edges[0], edges[-1] = -np.inf, np.inf
for d in samples.values():
    d["banda"] = pd.cut(d["score"], edges, labels=range(1, 11)).astype(int)

# 1) Calibración (solo muestras con resultado)
cal = []
for k in ("train 2013", "valid 2014", "oot 2015"):
    d = samples[k]
    hl, p = hosmer_lemeshow(d.target, d.pd)
    cal.append({"muestra": k, "n": len(d), "pd_media": d.pd.mean(), "dr_observada": d.target.mean(),
                "hl_stat": hl, "hl_p": p, "semaforo": p_light(p)})
cal = pd.DataFrame(cal).set_index("muestra")
binom = binomial_by_band(samples["oot 2015"].banda, samples["oot 2015"].target, samples["oot 2015"].pd)

# 2) Estabilidad: PSI del score (por banda) y CSI por variable (por grupo WoE), vs. train
base = samples["train 2013"]
psi_rows, csi_rows = [], {}
for k, d in samples.items():
    if k == "train 2013":
        continue
    v = psi(base.banda, d.banda)
    psi_rows.append({"muestra": k, "psi_score": v, "semaforo": psi_light(v)})
    csi_rows[k] = {f: psi(b._assign(base[f]), b._assign(d[f])) for f in cols}
psi_t = pd.DataFrame(psi_rows).set_index("muestra")
csi_t = pd.DataFrame(csi_rows)

cal.round(4).to_csv("reports/val_calibration.csv")
binom.round(4).to_csv("reports/val_binomial_oot.csv")
psi_t.round(4).to_csv("reports/val_psi.csv")
csi_t.round(4).to_csv("reports/val_csi.csv")

pd.set_option("display.width", 140)
print("CALIBRACIÓN\n", cal.round(4).to_string())
print("\nBINOMIAL POR BANDA (OOT 2015; 1 = más riesgo)\n", binom.round(4).to_string())
print("\nPSI DEL SCORE vs train\n", psi_t.round(3).to_string())
print("\nCSI (solo variables con alguna CSI >= 0.10)\n", csi_t[(csi_t >= 0.10).any(axis=1)].round(3).to_string())
