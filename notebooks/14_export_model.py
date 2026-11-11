"""Exporta el modelo oficial (pickle) a una especificación JSON versionable para la API, y verifica paridad.
Salida: models/scorecard_v1.json. Ver D23."""
import json
import math
import pickle
import sys

import duckdb
import pandas as pd
import numpy as np

sys.path.insert(0, "api")
from scorer import Scorecard  # noqa: E402

from credit_risk.woe import MISSING, OTHER  # noqa: E402

model = pickle.load(open("models/pd_model_final.pkl", "rb"))
b, params = model.binner, model.logit_model.params
spec = {"version": "1.0", "description": "Scorecard PD Lending Club 36m, recalibrado + MoC (D16)",
        "intercept": float(params["const"]), "delta": float(model.delta),
        "scaling": {"base_score": 600, "base_odds": 50, "pdo": 20},
        "domain": {k: list(v) for k, v in model.domain.items()}, "variables": {}}
for f in model.features:
    t, coef = b.tables_[f], float(params[f])
    woe_missing = float(t.loc[MISSING, "woe"]) if MISSING in t.index else None
    if f in b.edges_:
        e = b.edges_[f]
        labels = [i for i in t.index if i != MISSING]
        woe = [float(t.loc[lbl, "woe"]) if lbl in t.index else 0.0
               for lbl in [next((x for x in labels if x.startswith(f"{i:02d} ")), None) for i in range(len(e) - 1)]]
        var = {"type": "numeric", "edges": [None if math.isinf(x) else float(x) for x in e], "woe": woe}
    else:
        woe = {k: float(w) for k, w in t["woe"].items() if k not in (MISSING, OTHER)}
        var = {"type": "categorical", "woe": woe,
               "woe_other": float(t.loc[OTHER, "woe"]) if OTHER in t.index else None}
    var.update({"coef": coef, "woe_missing": woe_missing,
                "best_contrib": float(min(coef * t["woe"]))})
    spec["variables"][f] = var
open("models/scorecard_v1.json", "w").write(json.dumps(spec, indent=1, ensure_ascii=False))

# Paridad: el JSON debe reproducir la PD del modelo oficial
df = duckdb.connect("data/credit.duckdb", read_only=True).sql(
    "select * from model_sample where split='oot' using sample 20000 rows (reservoir, 7)").df()
sc = Scorecard(spec)
cols = model.features + list(model.domain)
recs = df[cols].astype(object).where(df[cols].notna(), None).to_dict("records")
p_json = np.array([np.nan if (r := sc.score(x))["pd"] is None else r["pd"] for x in recs])
p_model = model.predict_pd(df).to_numpy()
same_nan = np.array_equal(np.isnan(p_json), np.isnan(p_model))
diff = np.nanmax(np.abs(p_json - p_model))
print(f"Paridad en {len(df)} préstamos: dominio idéntico = {same_nan}, máx |ΔPD| = {diff:.2e}")
assert same_nan and diff < 1e-9

# Casos de paridad para CI (D27): solicitantes SINTÉTICOS (no datos reales) + PD esperada del modelo oficial.
rng = np.random.default_rng(2026)
n = 300
train = duckdb.connect("data/credit.duckdb", read_only=True).sql(
    "select * from model_sample where split='train'").df()
synth = {}
for f in dict.fromkeys(list(b.tables_) + cols):  # el binner necesita todas sus variables, aunque el modelo use 13
    s = train[f]
    if f in b.edges_ or f in model.domain:
        lo, hi = np.nanquantile(s, [0.001, 0.999])
        v = rng.uniform(lo, hi, n)
        v = np.where(rng.random(n) < 0.05, np.nan, v) if f not in model.domain else v
        synth[f] = np.round(v, 2)
    else:
        known = spec["variables"][f]["woe"] if f in spec["variables"] else b.categories_[f]
        cats = list(known) + ["OTHER", None]
        synth[f] = rng.choice(np.array(cats, dtype=object), n)
syn = pd.DataFrame(synth)
syn["dti"] = np.where(rng.random(n) < 0.1, 38.0, syn["dti"])  # algunos fuera de dominio
expected = model.predict_pd(syn)
cases = [{"input": {k: (None if (v is None or (isinstance(v, float) and np.isnan(v))) else v)
                    for k, v in r.items() if k in cols},
          "pd": None if np.isnan(p) else float(p)} for r, p in zip(syn.to_dict("records"), expected)]
open("tests/fixtures/parity_cases.json", "w").write(json.dumps(cases))
print(f"Casos de paridad sintéticos: {len(cases)} ({sum(c['pd'] is None for c in cases)} fuera de dominio)")
