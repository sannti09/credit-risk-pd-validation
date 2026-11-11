#!/usr/bin/env bash
# BORRA todos los recursos AWS del proyecto: función Lambda y su rol, tabla y base de Athena, y el bucket.
# Irreversible (los datos se pueden volver a subir con aws/upload.sh). Pide confirmación.
set -euo pipefail
cd "$(dirname "$0")/.."
source aws/config.env; export AWS_PROFILE AWS_REGION
read -r -p "Se borrará la Lambda credit-risk-pd-score, su rol, la base credit_risk y el bucket $BUCKET. Escribe BORRAR para continuar: " ok
[[ "$ok" == "BORRAR" ]] || { echo "Cancelado."; exit 1; }
aws lambda delete-function-url-config --function-name credit-risk-pd-score 2>/dev/null || true
aws lambda delete-function --function-name credit-risk-pd-score 2>/dev/null || true
aws iam detach-role-policy --role-name credit-risk-pd-lambda-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole 2>/dev/null || true
aws iam delete-role --role-name credit-risk-pd-lambda-role 2>/dev/null || true
printf 'DROP TABLE IF EXISTS credit_risk.loans;\nDROP DATABASE IF EXISTS credit_risk;\n' > /tmp/credit_drop.sql
aws/athena_run.sh /tmp/credit_drop.sql
aws s3 rb "s3://$BUCKET" --force
echo "Recursos borrados."
