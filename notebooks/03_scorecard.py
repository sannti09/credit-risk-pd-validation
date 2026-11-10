"""Fase 2b: regresión logística sobre WoE, escalado a puntos, Gini/KS train vs OOT vs benchmark.
Ver docs/decisiones.md (D6). Salidas: reports/model_coefs.csv, reports/scorecard_points.csv,
reports/performance.csv"""
import duckdb
import pandas as pd
import statsmodels.api as sm

from credit_risk.metrics import gini, ks
from credit_risk.scorecard import points_table, score_from_logit
from credit_risk.woe import WoEBinner

P_MAX = 0.05
df = duckdb.connect("data/credit.duckdb", read_only=True).sql("select * from model_sample").df()
train, oot = df[df.split == "train"], df[df.split == "oot"]
features = open("reports/selected_features.txt").read().split()

b = WoEBinner().fit(train, "target", features)
X_tr, X_oot = b.transform(train), b.transform(oot)

# Eliminación hacia atrás: fuera variables con signo incorrecto o no significativas.
# Signo esperado: coeficiente < 0 (WoE alto = grupo de menor riesgo -> baja P(malo)).
cols, log = list(features), []
while True:
    m = sm.Logit(train["target"], sm.add_constant(X_tr[cols])).fit(disp=0)
    c, p = m.params.drop("const"), m.pvalues.drop("const")
    bad_sign = c[c > 0]
    if len(bad_sign):
        drop, why = bad_sign.idxmax(), "signo incorrecto (colinealidad)"
    elif p.max() > P_MAX:
        drop, why = p.idxmax(), f"p-valor {p.max():.3f}"
    else:
        break
    cols.remove(drop)
    log.append((drop, why))
for d, w in log:
    print(f"Eliminada: {d:28s} {w}")

coefs = pd.DataFrame({"coef": m.params, "p_value": m.pvalues, "iv": b.iv_summary()["iv"]})
coefs.round(4).to_csv("reports/model_coefs.csv")
print(coefs.round(4).to_string())

pts = points_table(m.params["const"], m.params.drop("const"), b.tables_)
pts.to_csv("reports/scorecard_points.csv", index=False)

# Desempeño: modelo propio vs. benchmark Lending Club (int_rate y sub_grade como score de riesgo)
rows = []
for name, d, X in [("train 2012-14", train, X_tr), ("oot 2015", oot, X_oot)]:
    pd_hat = m.predict(sm.add_constant(X[cols]))
    sg = d["sub_grade"].rank(method="dense")  # A1 < A2 < ... < G5 = más riesgo
    rows += [(name, "scorecard propio", gini(d.target, pd_hat), ks(d.target, pd_hat)),
             (name, "LC int_rate", gini(d.target, d.int_rate), ks(d.target, d.int_rate)),
             (name, "LC sub_grade", gini(d.target, sg), ks(d.target, sg))]
perf = pd.DataFrame(rows, columns=["muestra", "modelo", "gini", "ks"]).round(3)
perf.to_csv("reports/performance.csv", index=False)
print("\n", perf.to_string(index=False))

s = score_from_logit(m.predict(sm.add_constant(X_tr[cols]), which="linear"))
print(f"\nScore train: min {s.min():.0f}, p50 {pd.Series(s).median():.0f}, max {s.max():.0f}")
