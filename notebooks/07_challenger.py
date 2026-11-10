"""Challenger: gradient boosting regularizado vs. scorecard logístico. Ver D12 y D13.

Controles contra sobreajuste:
1. Árboles poco profundos (max_depth 2-4) y hojas grandes (>= 1.000 clientes por hoja).
2. Early stopping contra valid 2014 (otro año), no contra una partición aleatoria de train.
3. Restricciones de monotonía (signo de Spearman en train) en variables numéricas.
4. Submuestreo de variables por división (max_features) y regularización L2.
5. Regla de selección (tipo "1 error estándar"): entre las configuraciones a <= TOL del mejor Gini en valid,
   la de MENOR brecha train - valid (la más simple). Se reporta si la brecha queda <= MAX_GAP.
OOT 2015 se usa una sola vez, al final.
Salidas: reports/challenger_grid.csv, reports/challenger_performance.csv
"""
import itertools
import pickle

import duckdb
import numpy as np
import pandas as pd
import statsmodels.api as sm
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance

from credit_risk.metrics import gini, ks

MAX_GAP = 0.03
TOL = 0.005
LC_SCORE = {"grade", "sub_grade", "int_rate"}
# installment: con plazo fijo, cuota + monto revelan la tasa de LC (fuga, D12)
# addr_state: 50 categorías (sobreajuste), IV ~0,01 y proxy geográfico (mismo criterio que zip_code)
EXCLUDE = {"id", "issue_date", "issue_year", "loan_status", "target", "split", "term_months", "fico_high",
           "installment", "addr_state"} | LC_SCORE

df = duckdb.connect("data/credit.duckdb", read_only=True).sql("select * from model_sample").df()
feats = [c for c in df.columns if c not in EXCLUDE]
cats = [c for c in feats if not pd.api.types.is_numeric_dtype(df[c])]
for c in cats:  # categorías aprendidas en train; las nuevas -> NaN
    known = sorted(df.loc[df.split == "train", c].dropna().unique())
    df[c] = pd.Categorical(df[c].where(df[c].isin(known)), categories=known)
tr, va, oot = (df[df.split == s] for s in ("train", "valid", "oot"))

# Monotonía: +1 si a mayor valor más default, -1 si menos; 0 si la relación es muy débil o es categórica
mono = {}
for c in feats:
    if c in cats:
        continue
    rho = tr[c].rank().corr(tr["target"])
    mono[c] = 0 if (np.isnan(rho) or abs(rho) < 0.01) else int(np.sign(rho))

grid = []
for depth, min_leaf, max_feat, l2 in itertools.product([2, 3, 4], [1000, 3000], [0.5, 1.0], [1.0, 10.0]):
    clf = HistGradientBoostingClassifier(
        learning_rate=0.05, max_depth=depth, max_leaf_nodes=None, min_samples_leaf=min_leaf,
        max_features=max_feat, l2_regularization=l2, monotonic_cst=mono, categorical_features="from_dtype",
        max_iter=2000, early_stopping=True, scoring="loss", n_iter_no_change=50, random_state=42)
    clf.fit(tr[feats], tr.target, X_val=va[feats], y_val=va.target)
    gt = gini(tr.target, clf.predict_proba(tr[feats])[:, 1])
    gv = gini(va.target, clf.predict_proba(va[feats])[:, 1])
    grid.append({"depth": depth, "min_leaf": min_leaf, "max_feat": max_feat, "l2": l2, "iters": clf.n_iter_,
                 "gini_train": gt, "gini_valid": gv, "brecha": gt - gv, "model": clf})
g = pd.DataFrame(grid)
near = g[g.gini_valid >= g.gini_valid.max() - TOL]
best = near.sort_values("brecha").iloc[0]
ok = g[g.brecha <= MAX_GAP]
gbm = best.model
g.drop(columns="model").round(4).to_csv("reports/challenger_grid.csv", index=False)
pd.set_option("display.width", 140)
print(g.drop(columns="model").sort_values("gini_valid", ascending=False).round(4).head(8).to_string(index=False))
print(f"\nA <= {TOL} del mejor Gini valid: {len(near)} · con brecha <= {MAX_GAP}: {len(ok)} de {len(g)}")
print("Elegida:", best.drop("model").round(4).to_dict())

# Comparación final (OOT se mira aquí por primera vez)
art = pickle.load(open("models/scorecard.pkl", "rb"))
b, m, cols = art["binner"], art["model"], art["features"]
rows = []
for name, d in [("train 2013", tr), ("valid 2014", va), ("oot 2015", oot)]:
    p_sc = m.predict(sm.add_constant(b.transform(d)[cols], has_constant="add"))
    p_gb = gbm.predict_proba(d[feats])[:, 1]
    sg = d["sub_grade"].astype(str).rank(method="dense")
    for mod, p in [("scorecard (13 var.)", p_sc), (f"gbm regularizado ({len(feats)} var.)", p_gb),
                   ("LC sub_grade", sg)]:
        rows.append({"muestra": name, "modelo": mod, "gini": gini(d.target, p), "ks": ks(d.target, p),
                     "pd_media": np.mean(p) if mod != "LC sub_grade" else np.nan, "dr_obs": d.target.mean()})
perf = pd.DataFrame(rows).round(4)
perf.to_csv("reports/challenger_performance.csv", index=False)
print("\n", perf.to_string(index=False))

sub = va.sample(30000, random_state=0)
imp = permutation_importance(gbm, sub[feats], sub.target, scoring="roc_auc", n_repeats=3, random_state=0)
print("\nTop 8 importancia (caída de AUC en valid):\n",
      pd.Series(imp.importances_mean, index=feats).sort_values(ascending=False).head(8).round(4).to_string())
pickle.dump({"model": gbm, "features": feats, "monotonic_cst": mono}, open("models/challenger_gbm.pkl", "wb"))
