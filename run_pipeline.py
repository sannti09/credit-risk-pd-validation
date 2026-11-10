"""Reproduce todo el proyecto en orden: SQL (DuckDB) y luego los scripts de notebooks/.
Requisito: el archivo de Kaggle descomprimido en data/raw/lending_club_kaggle/ (ver README).
Uso: uv run python run_pipeline.py"""
import subprocess
import sys
import time
from pathlib import Path

import duckdb

SQL = ["01_load_raw", "02_quality_checks", "03_clean", "04_model_sample", "05_load_rejected"]
SCRIPTS = ["02_feature_selection", "03_scorecard", "04_validation", "05_representativeness", "06_recalibration",
           "14_export_model", "07_challenger", "09_monitoring", "08_validation_report", "10_ifrs9_pd", "11_ifrs9_lgd",
           "12_ifrs9_ecl", "13_readme_chart"]

Path("models").mkdir(exist_ok=True)
t0 = time.time()
con = duckdb.connect("data/credit.duckdb")
for s in SQL:
    print(f"[sql] {s}", flush=True)
    con.execute(Path(f"sql/{s}.sql").read_text())
con.close()
for s in SCRIPTS:
    if s == "10_ifrs9_pd":  # la cartera NIIF 9 depende de la tabla loans (03) y del modelo oficial (06)
        print("[sql] 07_ifrs9_portfolio", flush=True)
        c = duckdb.connect("data/credit.duckdb")
        c.execute(Path("sql/07_ifrs9_portfolio.sql").read_text())
        c.close()
    print(f"[py ] {s}", flush=True)
    subprocess.run([sys.executable, f"notebooks/{s}.py"], check=True, stdout=subprocess.DEVNULL)
print(f"Listo en {time.time() - t0:.0f} s")
