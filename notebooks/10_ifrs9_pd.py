"""NIIF 9 — PD a 12 meses y PD de vida restante por préstamo (D18).
Entradas: ifrs9_portfolio (07), modelo oficial models/pd_model_final.pkl, cohortes maduras (model_sample).
Salidas: tabla ifrs9_pd en DuckDB, reports/ifrs9_default_timing.csv, reports/ifrs9_pd_by_stage.csv"""
import pickle

import duckdb
import numpy as np
import pandas as pd

STAGE2_MULT = 2.0  # SICR = riesgo de vida al menos duplicado -> piso coherente con la definición de etapa 2

con = duckdb.connect("data/credit.duckdb")
model = pickle.load(open("models/pd_model_final.pkl", "rb"))

# 1) Curva de momento del default (cohortes maduras 2013-2015, 36 meses)
#    Mes de default ≈ mes del último pago + 1 (sin pago registrado -> mes 1)
t = con.sql("""
    select least(greatest(coalesce(date_diff('month', s.issue_date,
                strptime(r.last_pymnt_d, '%b-%Y')::date) + 1, 1), 1), 36) as mob_default
    from model_sample s join loans_raw r on s.id = try_cast(r.id as bigint)
    where s.target = 1""").df()
f = t.mob_default.value_counts(normalize=True).reindex(range(1, 37), fill_value=0).sort_index()
F = np.r_[0.0, f.cumsum().values]  # F[m] = fracción de los defaults ocurridos hasta el mes m (F[0] = 0)
pd.DataFrame({"mob": range(1, 37), "pct_defaults": f.values, "acumulado": F[1:]}).round(4).to_csv(
    "reports/ifrs9_default_timing.csv", index=False)

# 2) PD de vida desde la originación (modelo oficial: recalibrado + MoC)
port = con.sql("select * from ifrs9_portfolio").df()
p_life = model.predict_pd(port)
in_dom = p_life.notna()
# Fuera de dominio (DTI > 35): PD de segmento = default observado de ese segmento en la última cohorte madura
seg_pd = con.sql("""select avg(target) from model_sample
                    where split = 'oot' and (dti > 34.99 or dti is null)""").fetchall()[0][0]
p_life = p_life.fillna(seg_pd)
# Etapa 2: piso de riesgo duplicado (definición de SICR)
p_life = np.where(port.etapa == 2, np.minimum(STAGE2_MULT * p_life, 0.99), p_life)

# 3) Condicionar a la supervivencia hasta hoy (mob) y repartir en el tiempo con la curva
m = port.mob.clip(0, 36).to_numpy()
m12 = np.minimum(m + 12, 36)
surv = 1 - p_life * F[m]                                   # P(no default hasta m)
pd_12m = p_life * (F[m12] - F[m]) / surv
pd_vida_rest = p_life * (1 - F[m]) / surv
etapa3 = port.etapa.to_numpy() == 3
pd_12m, pd_vida_rest = np.where(etapa3, 1.0, pd_12m), np.where(etapa3, 1.0, pd_vida_rest)

out = pd.DataFrame({"id": port.id, "etapa": port.etapa, "mob": port.mob, "saldo": port.saldo,
                    "en_dominio": in_dom.to_numpy(), "pd_vida_origen": p_life,
                    "pd_12m": pd_12m, "pd_vida_restante": pd_vida_rest})
out["pd_aplicable"] = np.where(out.etapa == 1, out.pd_12m, out.pd_vida_restante)  # etapa 1: 12m; 2-3: vida
con.execute("create or replace table ifrs9_pd as select * from out")

summ = out.groupby("etapa").apply(lambda g: pd.Series({
    "prestamos": len(g), "saldo_musd": g.saldo.sum() / 1e6, "mob_medio": g.mob.mean(),
    "pd_vida_origen": np.average(g.pd_vida_origen, weights=g.saldo),
    "pd_12m": np.average(g.pd_12m, weights=g.saldo),
    "pd_vida_restante": np.average(g.pd_vida_restante, weights=g.saldo),
    "pd_aplicable": np.average(g.pd_aplicable, weights=g.saldo)}), include_groups=False)
summ.round(4).to_csv("reports/ifrs9_pd_by_stage.csv")
print(f"PD segmento fuera de dominio: {seg_pd:.3f} · fuera de dominio: {100 * (~in_dom).mean():.1f}%")
print("Momento del default (% acumulado de defaults) mes 6/12/18/24/36:",
      [round(F[k], 3) for k in (6, 12, 18, 24, 36)])
print("\nPD ponderada por saldo:\n", summ.round(4).to_string())
