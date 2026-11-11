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
print(sorted(p.name for p in OUT.iterdir()))
v = con.sql("select cosecha, max(mob) mob, round(100*max(tasa_default_acum),1) dr from dash_vintage "
            "where cosecha like '%Q1' group by 1 order by 1").fetchall()
print("Cosechas Q1 (último mes observado, % default acumulado):", v)
