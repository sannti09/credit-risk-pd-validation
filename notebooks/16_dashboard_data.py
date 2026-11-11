"""Exporta los datos del tablero a reports/dashboard/ (D26): tablas SQL (08) + resultados ya calculados.
Todo agregado (sin préstamos individuales) -> se puede versionar y publicar."""
from pathlib import Path
import shutil

import duckdb

OUT = Path("reports/dashboard")
OUT.mkdir(parents=True, exist_ok=True)
con = duckdb.connect("data/credit.duckdb")
con.execute(Path("sql/08_dashboard.sql").read_text())
for t in ("dash_vintage", "dash_originacion", "dash_cartera"):
    con.sql(f"select * from {t}").df().round(6).to_csv(OUT / f"{t.removeprefix('dash_')}.csv", index=False)
# Resultados ya calculados por otras fases
for src, dst in {"calibration_bands_oot.csv": "calibracion_bandas.csv", "monitoring.csv": "monitoreo.csv",
                 "ifrs9_ecl_by_stage.csv": "ecl_etapas.csv", "ifrs9_scenarios.csv": "ecl_escenarios.csv",
                 "ifrs9_sensitivity.csv": "ecl_sensibilidad.csv", "sfc_mrco_comparison.csv": "sfc_calificaciones.csv",
                 "sfc_vs_ifrs9_bridge.csv": "sfc_puente.csv", "challenger_performance.csv": "desempeno_modelos.csv",
                 "ifrs9_default_timing.csv": "momento_default.csv"}.items():
    if (Path("reports") / src).exists():
        shutil.copy(Path("reports") / src, OUT / dst)
# Ajustes para Tableau: nombrar la primera columna (índice) y quitar filas "total" (Tableau suma por su cuenta)
import pandas as pd  # noqa: E402

for f, name in {"ecl_escenarios.csv": "escenario", "ecl_sensibilidad.csv": "supuesto", "monitoreo.csv": "cohorte",
                "ecl_etapas.csv": "etapa", "sfc_calificaciones.csv": "calificacion"}.items():
    t = pd.read_csv(OUT / f)
    t = t.rename(columns={t.columns[0]: name})
    t = t[t[name].astype(str) != "total"]
    t.to_csv(OUT / f, index=False)
# ---- Hojas 3-5 del tablero, en inglés y formato "largo" (D32) ----
VARS = {"fico_low": "FICO score", "annual_inc": "Annual income", "avg_cur_bal": "Avg. current balance",
        "dti": "Debt-to-income", "acc_open_past_24mths": "Accounts opened (24m)", "home_ownership": "Home ownership",
        "mo_sin_rcnt_tl": "Months since newest account", "num_tl_op_past_12m": "Accounts opened (12m)",
        "percent_bc_gt_75": "% cards > 75% used", "mo_sin_old_rev_tl_op": "Months since oldest revolving",
        "mths_since_recent_inq": "Months since last inquiry", "revol_util": "Revolving utilization",
        "purpose": "Loan purpose"}
COH = {"valid 2014": "2014", "oot 2015": "2015", "2016": "2016", "2017": "2017", "2018": "2018"}
csi = pd.read_csv("reports/val_csi.csv", index_col=0).rename(columns=COH)
csi = csi.rename_axis("variable").reset_index().melt(id_vars="variable", var_name="year", value_name="csi")
csi["variable"] = csi["variable"].map(VARS).fillna(csi["variable"])
csi["status"] = pd.cut(csi.csi, [-1, 0.10, 0.25, 99], labels=["Green (< 0.10)", "Amber (0.10-0.25)", "Red (> 0.25)"])
csi.round(4).to_csv(OUT / "stability_csi.csv", index=False)

perf = pd.read_csv("reports/challenger_performance.csv")
perf["model"] = perf.modelo.map(lambda m: "Scorecard (13 vars)" if m.startswith("scorecard") else
                                ("Gradient boosting (regularized)" if m.startswith("gbm") else
                                 "Lending Club grade (benchmark)"))
perf["sample"] = perf.muestra.map({"train 2013": "Train 2013", "valid 2014": "Validation 2014",
                                   "oot 2015": "Out-of-time 2015"})
perf[["sample", "model", "gini", "ks"]].round(4).to_csv(OUT / "model_performance.csv", index=False)

sc = pd.read_csv("reports/ifrs9_scenarios.csv", index_col=0)
st = pd.read_csv("reports/ifrs9_ecl_by_stage.csv", index_col=0)
lgd = pd.read_csv("reports/ifrs9_lgd_param.csv").set_index("parametro").valor["lgd"]
tot = st.loc["total"]
kpis = pd.DataFrame([
    ("Expected credit loss (IFRS 9, weighted)", sc.loc["ponderado", "ecl_musd"], "US$ M"),
    ("Coverage (ECL / balance)", 100 * sc.loc["ponderado", "ecl_musd"] / tot.saldo, "%"),
    ("Live portfolio balance", tot.saldo, "US$ M"),
    ("Live loans", tot.prestamos, "loans"),
    ("Observed LGD", 100 * lgd, "%"),
    ("SFC reference model (Matrix A)", pd.read_csv("reports/sfc_mrco_comparison.csv", index_col=0).loc["total", "pe_A"], "US$ M"),
], columns=["kpi", "value", "unit"])
kpis.round(1).to_csv(OUT / "kpis.csv", index=False)
# ---- Hojas 6-8, en inglés y con la forma que necesita cada gráfico (D32) ----
st = pd.read_csv("reports/ifrs9_ecl_by_stage.csv", index_col=0).drop(index="total")
mix = pd.DataFrame({"stage": [f"Stage {int(i)}" for i in st.index],
                    "Share of balance": st.saldo / st.saldo.sum(), "Share of expected loss": st.ecl / st.ecl.sum()})
mix.melt(id_vars="stage", var_name="metric", value_name="share").round(4).to_csv(OUT / "stage_mix.csv", index=False)

br = pd.read_csv("reports/sfc_vs_ifrs9_bridge.csv")
names = ["SFC provision (Matrix A)", "LGD: 75% regulatory -> 90.7% observed", "PD: SFC matrix -> model 12m PD",
         "Stage 2: lifetime horizon", "Balance amortization", "Discounting at effective rate", "IFRS 9 ECL (base)"]
br["step"], br["order"] = names, range(1, len(names) + 1)
br["kind"] = ["Start"] + ["Increase" if v >= 0 else "Decrease" for v in br.efecto_musd[1:-1]] + ["Total"]
run = br.efecto_musd.iloc[:-1].cumsum()
br["start"] = [0.0] + list(run.iloc[:-1]) + [0.0]          # base de cada barra
br["effect"] = list(br.efecto_musd.iloc[:-1]) + [br.efecto_musd.iloc[-1]]
br[["order", "step", "kind", "start", "effect"]].round(2).to_csv(OUT / "bridge.csv", index=False)

se = pd.read_csv("reports/ifrs9_sensitivity.csv", index_col=0)
lab = {"multiplicador etapa 2 = 1,5": "Stage 2 PD multiplier 1.5 (base 2)",
       "multiplicador etapa 2 = 3": "Stage 2 PD multiplier 3 (base 2)",
       "Late 31-120 todo en etapa 3 (regla anterior)": "All 31-120 days past due in stage 3",
       "Late 31-120 todo en etapa 2": "All 31-120 days past due in stage 2",
       "PD sin tendencia (solo recalibración 2014)": "PD without trend adjustment",
       "LGD con defaults hasta 2017": "LGD including 2017 defaults",
       "umbral SICR caída FICO = 30": "SICR threshold: FICO drop 30 (base 50)",
       "umbral SICR caída FICO = 70": "SICR threshold: FICO drop 70 (base 50)",
       "LGD = 80%": "LGD 80% (base 90.7%)"}  # LGD 45% (Basilea) se excluye: no es un supuesto plausible (D19)
sens = se.loc[se.index.isin(lab)].rename(index=lab).rename_axis("assumption").reset_index()
sens["direction"] = sens.var_vs_base_pct.map(lambda v: "Raises ECL" if v >= 0 else "Lowers ECL")
sens[["assumption", "var_vs_base_pct", "ecl_musd", "direction"]].rename(
    columns={"var_vs_base_pct": "change_vs_base_pct"}).round(2).to_csv(OUT / "sensitivity.csv", index=False)
print(sorted(p.name for p in OUT.iterdir()))
v = con.sql("select cosecha, max(mob) mob, round(100*max(tasa_default_acum),1) dr from dash_vintage "
            "where cosecha like '%Q1' group by 1 order by 1").fetchall()
print("Cosechas Q1 (último mes observado, % default acumulado):", v)
