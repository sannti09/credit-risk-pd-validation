"""Genera aws/athena/01_create_tables.sql desde el esquema real del Parquet exportado (D28)."""
import sys

import duckdb

src, bucket = sys.argv[1], sys.argv[2]
TYPES = {"BIGINT": "bigint", "INTEGER": "int", "DOUBLE": "double", "VARCHAR": "string", "DATE": "date"}
cols = duckdb.sql(f"describe select * from read_parquet('{src}/*/*.parquet', hive_partitioning=false)").fetchall()
body = ",\n".join(f"  `{c}` {TYPES[t]}" for c, t, *_ in cols if c != "issue_year")
open("aws/athena/01_create_tables.sql", "w").write(f"""CREATE DATABASE IF NOT EXISTS credit_risk;
CREATE EXTERNAL TABLE IF NOT EXISTS credit_risk.loans (
{body}
)
PARTITIONED BY (issue_year bigint)
STORED AS PARQUET
LOCATION 's3://{bucket}/curated/loans/';
MSCK REPAIR TABLE credit_risk.loans;
""")
print(f"{len(cols) - 1} columnas + partición issue_year")
