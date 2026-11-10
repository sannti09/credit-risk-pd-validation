"""Monitoreo del modelo oficial por cohorte (D16). Referencia: train 2013.
Salida: reports/monitoring.csv"""
import pickle

import duckdb
import pandas as pd

from credit_risk.monitoring import monitor

model = pickle.load(open("models/pd_model_final.pkl", "rb"))
con = duckdb.connect("data/credit.duckdb", read_only=True)
ref = con.sql("select * from model_sample where split='train'").df()
cohorts = {"valid 2014": "select * from model_sample where split='valid'",
           "oot 2015": "select * from model_sample where split='oot'"}
for y in (2016, 2017, 2018):  # sin resultado maduro: solo estabilidad
    cohorts[str(y)] = f"select * exclude (target) from loans where term_months=36 and issue_year={y}"

rows = {k: monitor(model, ref, con.sql(q).df()) for k, q in cohorts.items()}
res = pd.DataFrame(rows).T
res.to_csv("reports/monitoring.csv")
pd.set_option("display.width", 160)
print(res.to_string())
