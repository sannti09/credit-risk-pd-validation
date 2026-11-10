"""NIIF 9 — ECL de la cartera al corte (D20): base, escenarios ponderados y sensibilidades.
Salidas: reports/ifrs9_ecl_by_stage.csv, reports/ifrs9_scenarios.csv, reports/ifrs9_sensitivity.csv"""
import pickle
from dataclasses import replace

import duckdb
import numpy as np
import pandas as pd

from credit_risk.ifrs9 import assign_stage, ecl, effective_timing

STAGE2_MULT = 2.0
# Escenarios forward-looking (overlay de juicio experto; sin modelo macro): multiplicador de PD, LGD, peso
SCEN = {"base": (1.00, None, 0.60), "adverso": (1.35, 0.93, 0.25), "optimista": (0.85, 0.89, 0.15)}

con = duckdb.connect("data/credit.duckdb", read_only=True)
model = pickle.load(open("models/pd_model_final.pkl", "rb"))
port = con.sql("select * from ifrs9_portfolio").df()
f = pd.read_csv("reports/ifrs9_default_timing.csv").pct_defaults.to_numpy()
LGD = float(pd.read_csv("reports/ifrs9_lgd_param.csv").valor.iloc[0])
seg_pd = con.sql("select avg(target) from model_sample where split='oot' and (dti > 34.99 or dti is null)"
                 ).fetchall()[0][0]
p_life = model.predict_pd(port).fillna(seg_pd).to_numpy()  # fuera de dominio -> PD de segmento (D18)
p_sin_tend = replace(model, delta=model.delta_sin_tendencia).predict_pd(port).fillna(seg_pd).to_numpy()
LGD_2017 = float(pd.read_csv("reports/ifrs9_lgd_param.csv").set_index("parametro").valor["lgd_hasta_2017"])
assert (assign_stage(port) == port.etapa.to_numpy()).all(), "regla de etapas SQL != Python"

mob_eff, n_left = effective_timing(port.mob.to_numpy(), port.meses_restantes.to_numpy())  # vencidos (D21)
args = dict(p_life=p_life, mob=mob_eff, balance=port.saldo.to_numpy(),
            annual_rate=port.int_rate.to_numpy(), n_left=n_left, f=f)


def run(stage=None, lgd=LGD, stage2_mult=STAGE2_MULT, pd_mult=1.0, p=None):
    st = assign_stage(port) if stage is None else stage
    a = args if p is None else {**args, "p_life": p}
    return ecl(st, lgd=lgd, stage2_mult=stage2_mult, pd_mult=pd_mult, **a)


def by_stage(r):
    g = r.groupby("etapa").agg(prestamos=("saldo", "size"), saldo=("saldo", "sum"), ecl=("ecl", "sum"))
    g.loc["total"] = g.sum()
    g["cobertura_pct"] = 100 * g.ecl / g.saldo
    g[["saldo", "ecl"]] /= 1e6
    return g


base = run()
tab = by_stage(base)
tab.round(3).to_csv("reports/ifrs9_ecl_by_stage.csv")

# Escenarios ponderados
sc = {}
for k, (mult, lgd_s, w) in SCEN.items():
    sc[k] = {"peso": w, "pd_mult": mult, "lgd": lgd_s or LGD, "ecl_musd": run(lgd=lgd_s or LGD, pd_mult=mult).ecl.sum() / 1e6}
sc = pd.DataFrame(sc).T
ecl_w = float((sc.peso * sc.ecl_musd).sum())
sc.loc["ponderado"] = [1.0, np.nan, np.nan, ecl_w]
sc.round(3).to_csv("reports/ifrs9_scenarios.csv")

# Sensibilidades (una a la vez, escenario base)
tot = base.ecl.sum() / 1e6
sens = {
    "multiplicador etapa 2 = 1,5": run(stage2_mult=1.5),
    "multiplicador etapa 2 = 3": run(stage2_mult=3.0),
    "Late 31-120 todo en etapa 3 (regla anterior)": run(stage=assign_stage(port, late31_stage=3)),
    "Late 31-120 todo en etapa 2": run(stage=assign_stage(port, late31_stage=2)),
    "PD sin tendencia (solo recalibración 2014)": run(p=p_sin_tend),
    "LGD con defaults hasta 2017": run(lgd=LGD_2017),
    "umbral SICR caída FICO = 30": run(stage=assign_stage(port, fico_drop=30)),
    "umbral SICR caída FICO = 70": run(stage=assign_stage(port, fico_drop=70)),
    "LGD = 80%": run(lgd=0.80),
    "LGD = 45% (Basilea, no aplica)": run(lgd=0.45),
}
s = pd.DataFrame({"ecl_musd": {k: v.ecl.sum() / 1e6 for k, v in sens.items()}})
s["var_vs_base_pct"] = 100 * (s.ecl_musd / tot - 1)
s["pct_saldo_etapa2"] = {k: 100 * v.saldo[v.etapa == 2].sum() / v.saldo.sum() for k, v in sens.items()}
s.round(2).to_csv("reports/ifrs9_sensitivity.csv")

pd.set_option("display.width", 140)
print(f"LGD = {LGD:.3f} · PD segmento fuera de dominio = {seg_pd:.3f}\n")
print("ECL BASE POR ETAPA (US$ M)\n", tab.round(2).to_string())
print("\nESCENARIOS\n", sc.round(2).to_string())
print(f"\nSENSIBILIDADES (base = {tot:.1f} M)\n", s.round(1).to_string())
