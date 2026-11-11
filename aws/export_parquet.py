"""Exporta la tabla loans limpia (+ fecha de último pago) a Parquet particionado por año en
data/processed/aws_export/loans (no se versiona). Ver D28."""
import shutil
from pathlib import Path

import duckdb

OUT = Path("data/processed/aws_export/loans")
shutil.rmtree(OUT, ignore_errors=True)
OUT.parent.mkdir(parents=True, exist_ok=True)
duckdb.connect("data/credit.duckdb", read_only=True).execute(f"""
    COPY (SELECT l.*, r.last_pymnt_d FROM loans l JOIN loans_raw r ON l.id = try_cast(r.id AS BIGINT))
    TO '{OUT}' (FORMAT PARQUET, PARTITION_BY (issue_year), COMPRESSION ZSTD)""")
print("Parquet en", OUT)
