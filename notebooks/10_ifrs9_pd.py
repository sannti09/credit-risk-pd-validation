"""NIIF 9 — PD a 12 meses y PD de vida restante por préstamo (D18, corregido en D21).
Entradas: ifrs9_portfolio (07), modelo oficial models/pd_model_final.pkl, cohortes maduras (model_sample).
Salidas: tabla ifrs9_pd en DuckDB, reports/ifrs9_default_timing.csv, reports/ifrs9_pd_by_stage.csv"""
import pickle

import duckdb
import numpy as np
import pandas as pd

from credit_risk.ifrs9 import effective_timing, marginal_pd

STAGE2_MULT = 2.0  # juicio experto (D18/D21): PD de vida × 2 en etapa 2; sensibilidad 1,5–3 en D20

con = duckdb.connect("data/credit.duckdb")
model = pickle.load(open("models/pd_model_final.pkl", "rb"))

# 1) Curva de momento del default (cohortes maduras 2013-2015, 36 meses)
#    Mes de default ≈ mes del último pago + 1 (sin pago registrado -> mes 1; 373 casos)
t = con.sql("""
    select least(greatest(coalesce(date_diff('month', s.issue_date,
                strptime(r.last_pymnt_d, '%b-%Y')::date) + 1, 1), 1), 36) as mob_default
    from model_sample s join loans_raw r on s.id = try_cast(r.id as bigint)
    where s.target = 1""").df()
f = t.mob_default.value_counts(normalize=True).reindex(range(1, 37), fill_value=0).sort_index()
F = np.r_[0.0, f.cumsum().values]
pd.DataFrame({"mob": range(1, 37), "pct_defaults": f.values, "acumulado": F[1:]}).round(4).to_csv(
    "reports/ifrs9_default_timing.csv", index=False)

# 2) PD de vida desde la originación (modelo oficial) y PD de segmento fuera de dominio
port = con.sql("select * from ifrs9_portfolio").df()
p_base = model.predict_pd(port)
in_dom = p_base.notna()
seg_pd = con.sql("""select avg(target) from model_sample
                    where split = 'oot' and (dti > 34.99 or dti is null)""").fetchall()[0][0]
p_base = p_base.fillna(seg_pd).to_numpy()
p_adj = np.where(port.etapa == 2, np.minimum(STAGE2_MULT * p_base, 0.99), p_base)

# 3) PD marginal mensual condicionada a supervivencia (mismo módulo que la ECL)
mob_eff, n_left = effective_timing(port.mob.to_numpy(), port.meses_restantes.to_numpy())
mpd = marginal_pd(p_adj, mob_eff, f.to_numpy())
pd_12m = mpd[:, :12].sum(axis=1)
pd_vida_rest = mpd.sum(axis=1)
etapa3 = port.etapa.to_numpy() == 3
pd_12m = np.clip(np.where(etapa3, 1.0, pd_12m), 0, 1)
pd_vida_rest = np.clip(np.where(etapa3, 1.0, pd_vida_rest), 0, 1)

out = pd.DataFrame({"id": port.id, "etapa": port.etapa, "mob": port.mob, "saldo": port.saldo,
                    "en_dominio": in_dom.to_numpy(), "pd_vida_base": p_base, "pd_vida_ajustada": p_adj,
                    "pd_12m": pd_12m, "pd_vida_restante": pd_vida_rest})
out["pd_aplicable"] = np.where(out.etapa == 1, out.pd_12m, out.pd_vida_restante)  # etapa 1: 12m; 2-3: vida
con.execute("create or replace table ifrs9_pd as select * from out")

summ = out.groupby("etapa").apply(lambda g: pd.Series({
    "prestamos": len(g), "saldo_musd": g.saldo.sum() / 1e6, "mob_medio": g.mob.mean(),
    "pd_vida_base": np.average(g.pd_vida_base, weights=g.saldo),
    "pd_12m": np.average(g.pd_12m, weights=g.saldo),
    "pd_vida_restante": np.average(g.pd_vida_restante, weights=g.saldo),
    "pd_aplicable": np.average(g.pd_aplicable, weights=g.saldo)}), include_groups=False)
summ.round(4).to_csv("reports/ifrs9_pd_by_stage.csv")
print(f"PD segmento fuera de dominio: {seg_pd:.3f} · fuera de dominio: {100 * (~in_dom).mean():.1f}%")
print("\nPD ponderada por saldo:\n", summ.round(4).to_string())
