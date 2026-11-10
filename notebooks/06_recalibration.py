"""Recalibración: se ajusta con valid 2014 y se evalúa en OOT 2015 (sin tocarlo). Ver D11.
Salida: reports/recalibration_oot.csv"""
import pickle

import duckdb
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.optimize import brentq

from credit_risk.calibration import apply_platt, apply_shift, fit_intercept_shift, fit_platt
from credit_risk.metrics import gini
from credit_risk.validation import binomial_by_band, hosmer_lemeshow

art = pickle.load(open("models/scorecard.pkl", "rb"))
b, m, cols = art["binner"], art["model"], art["features"]
con = duckdb.connect("data/credit.duckdb", read_only=True)
d = {s: con.sql(f"select * from model_sample where split='{s}'").df() for s in ("train", "valid", "oot")}
lin = {s: np.asarray(m.predict(sm.add_constant(b.transform(x)[cols], has_constant="add"), which="linear"))
       for s, x in d.items()}

delta = fit_intercept_shift(lin["valid"], d["valid"].target)
a, slope = fit_platt(lin["valid"], d["valid"].target)
# Margen de conservadurismo (MoC): proyecta la tendencia observada SOLO con train->valid (no mira OOT)
trend = d["valid"].target.mean() - d["train"].target.mean()
target_moc = d["valid"].target.mean() + trend
delta_moc = brentq(lambda z: apply_shift(lin["valid"], z).mean() - target_moc, -5, 5)
print(f"Tendencia train->valid: {100*trend:+.2f} pts · objetivo con MoC: {100*target_moc:.2f}%")
print(f"Intercepto: delta = {delta:+.3f} · Platt: a = {a:+.3f}, b = {slope:.3f}")

# Bandas = deciles del score en train (igual que en 04_validation)
edges = np.quantile(lin["train"], np.linspace(0, 1, 11)); edges[0], edges[-1] = -np.inf, np.inf
oot, y = d["oot"], d["oot"].target
band = pd.Series(pd.cut(lin["oot"], edges, labels=range(10, 0, -1)).astype(int), index=oot.index)  # 1 = más riesgo

rows = []
for name, pdv in [("original", 1 / (1 + np.exp(-lin["oot"]))),
                  ("intercepto (valid 2014)", apply_shift(lin["oot"], delta)),
                  ("platt (valid 2014)", apply_platt(lin["oot"], a, slope)),
                  ("intercepto + MoC tendencia", apply_shift(lin["oot"], delta_moc))]:
    pdv = pd.Series(pdv, index=oot.index)
    hl, p = hosmer_lemeshow(y, pdv)
    bt = binomial_by_band(band, y, pdv)
    rows.append({"metodo": name, "pd_media": pdv.mean(), "dr_obs": y.mean(),
                 "brecha_pts": 100 * (y.mean() - pdv.mean()), "hl_stat": hl, "hl_p": p,
                 "bandas_rojas": int((bt.semaforo == "rojo").sum()), "gini": gini(y, pdv)})
res = pd.DataFrame(rows).set_index("metodo")
res.round(4).to_csv("reports/recalibration_oot.csv")
pd.set_option("display.width", 140)
print(res.round(4).to_string())
print("\nDefault observado por año:", {s: round(100 * x.target.mean(), 1) for s, x in d.items()})

# ---- Modelo oficial (D16): recalibración + MoC + dominio = rangos vistos en train ----
from credit_risk.model import PDModel

domain = {"fico_low": (float(d["train"].fico_low.min()), None), "dti": (None, float(d["train"].dti.max()))}
final = PDModel(b, m, cols, delta=float(delta_moc), domain=domain, version="1.0 (MoC tendencia train->valid)",
                delta_sin_tendencia=float(delta))
pickle.dump(final, open("models/pd_model_final.pkl", "wb"))
print(f"\nModelo oficial guardado: delta = {delta_moc:+.3f}, dominio = {domain}")
