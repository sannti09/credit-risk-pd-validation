#!/usr/bin/env bash
# Ejecuta en Athena las sentencias de un archivo .sql (separadas por ';') y espera cada una. Uso: aws/athena_run.sh archivo.sql
set -euo pipefail
source "$(dirname "$0")/config.env"; export AWS_PROFILE AWS_REGION
OUT="s3://$BUCKET/athena-results/"
python3 -c "import sys; [print(s.strip()+'\x00', end='') for s in open(sys.argv[1]).read().split(';') if s.strip() and not all(l.strip().startswith('--') or not l.strip() for l in s.splitlines())]" "$1" |
while IFS= read -r -d '' q; do
  id=$(aws athena start-query-execution --query-string "$q" --result-configuration "OutputLocation=$OUT" --query QueryExecutionId --output text)
  while :; do
    st=$(aws athena get-query-execution --query-execution-id "$id" --query 'QueryExecution.Status.State' --output text)
    [[ "$st" =~ SUCCEEDED|FAILED|CANCELLED ]] && break; sleep 2
  done
  scanned=$(aws athena get-query-execution --query-execution-id "$id" --query 'QueryExecution.Statistics.DataScannedInBytes' --output text)
  echo "$st  $(echo "$q" | grep -v '^--' | head -1 | cut -c1-60)  (escaneado: $scanned bytes)  id=$id"
  [[ "$st" == SUCCEEDED ]] || aws athena get-query-execution --query-execution-id "$id" --query 'QueryExecution.Status.StateChangeReason' --output text
done
