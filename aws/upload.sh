#!/usr/bin/env bash
# Sube el Parquet a S3 y crea las tablas de Athena. Requiere: aws login --profile credit-project y aws/config.env.
# Crear el bucket (una vez):  aws s3api create-bucket --bucket <nombre> --create-bucket-configuration LocationConstraint=us-east-2
set -euo pipefail
cd "$(dirname "$0")/.."
source aws/config.env; export AWS_PROFILE AWS_REGION
uv run python aws/export_parquet.py
aws s3 sync data/processed/aws_export/loans "s3://$BUCKET/curated/loans/" --delete --only-show-errors
uv run python aws/make_ddl.py data/processed/aws_export/loans "$BUCKET"
aws/athena_run.sh aws/athena/01_create_tables.sql
