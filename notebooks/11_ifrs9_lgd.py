"""NIIF 9 — LGD observada (D19). Préstamos castigados de las cohortes maduras (36m, 2013-2015).
LGD = 1 - recuperaciones netas descontadas / EAD al default.
  EAD al default = monto desembolsado - capital recuperado (total_rec_prncp)
  Recuperaciones netas = recoveries - collection_recovery_fee
  Descuento: NIIF 9 descuenta a la tasa efectiva; sin fechas de recuperación se supone que llegan 12 meses
  después del default (venta de cartera castigada) -> factor 1 / (1 + int_rate).
Salidas: reports/ifrs9_lgd.csv, reports/ifrs9_lgd_param.csv"""
import duckdb
import numpy as np
import pandas as pd

RECOVERY_LAG_YEARS = 1.0
con = duckdb.connect("data/credit.duckdb", read_only=True)
d = con.sql("""
    select s.id, s.fico_low, s.int_rate, s.issue_year,
           year(strptime(r.last_pymnt_d, '%b-%Y')) as anio_default,
           try_cast(r.funded_amnt as double) - try_cast(r.total_rec_prncp as double) as ead,
           try_cast(r.recoveries as double) - try_cast(r.collection_recovery_fee as double) as rec_neta
    from model_sample s join loans_raw r on s.id = try_cast(r.id as bigint)
    where s.loan_status = 'Charged Off'""").df()
d = d[d.ead > 0].copy()
disc = (1 + d.int_rate / 100) ** RECOVERY_LAG_YEARS
d["lgd"] = (1 - d.rec_neta / d.ead).clip(0, 1)
d["lgd_desc"] = (1 - d.rec_neta / disc / d.ead).clip(0, 1)
d["banda_fico"] = pd.cut(d.fico_low, [0, 679, 699, 719, 749, 900], labels=["660-679", "680-699", "700-719",
                                                                           "720-749", "750+"])


def w(g):
    return pd.Series({"n": len(g), "ead_musd": g.ead.sum() / 1e6,
                      "lgd": np.average(g.lgd, weights=g.ead), "lgd_desc": np.average(g.lgd_desc, weights=g.ead),
                      "pct_sin_recup": 100 * (g.rec_neta <= 0).mean()})


tabs = {"total": w(d).to_frame("total").T,
        "por año de default": d.groupby("anio_default").apply(w, include_groups=False),
        "por banda FICO": d.groupby("banda_fico", observed=True).apply(w, include_groups=False)}
res = pd.concat(tabs, names=["corte", "grupo"])
res.round(4).to_csv("reports/ifrs9_lgd.csv")
# Parámetro: LGD descontada ponderada por EAD, defaults hasta 2017 (2018-19 con cobranza posiblemente incompleta)
base = d[d.anio_default <= 2017]
lgd_param = float(np.average(base.lgd_desc, weights=base.ead))
pd.DataFrame({"parametro": ["lgd"], "valor": [lgd_param]}).to_csv("reports/ifrs9_lgd_param.csv", index=False)
pd.set_option("display.width", 140)
print(res.round(3).to_string())
print(f"\nLGD parámetro (descontada, defaults <= 2017): {lgd_param:.3f}")
