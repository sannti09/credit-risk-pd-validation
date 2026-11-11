#!/usr/bin/env bash
# BORRA todos los recursos AWS del proyecto: API Gateway (API, plan, clave), Lambda y su rol, Athena y el bucket.
# Irreversible (los datos se pueden volver a subir con aws/upload.sh). Pide confirmación.
set -euo pipefail
cd "$(dirname "$0")/.."
source aws/config.env; export AWS_PROFILE AWS_REGION
read -r -p "Se borrará la API pública, la Lambda credit-risk-pd-score, su rol, la base credit_risk y el bucket $BUCKET. Escribe BORRAR para continuar: " ok
[[ "$ok" == "BORRAR" ]] || { echo "Cancelado."; exit 1; }
API_ID=$(aws apigateway get-rest-apis --query "items[?name=='credit-risk-pd-api'].id | [0]" --output text)
PLAN_ID=$(aws apigateway get-usage-plans --query "items[?name=='credit-risk-pd-api-plan'].id | [0]" --output text)
KEY_ID=$(aws apigateway get-api-keys --name-query credit-risk-pd-api-public-key --query "items[0].id" --output text)
if [[ "$PLAN_ID" != "None" ]]; then
  aws apigateway update-usage-plan --usage-plan-id "$PLAN_ID" \
    --patch-operations op=remove,path=/apiStages,value="$API_ID:v1" >/dev/null 2>&1 || true
  aws apigateway delete-usage-plan --usage-plan-id "$PLAN_ID" || true
fi
[[ "$KEY_ID" != "None" ]] && aws apigateway delete-api-key --api-key "$KEY_ID" || true
[[ "$API_ID" != "None" ]] && aws apigateway delete-rest-api --rest-api-id "$API_ID" || true
aws lambda delete-function-url-config --function-name credit-risk-pd-score 2>/dev/null || true
aws lambda delete-function --function-name credit-risk-pd-score 2>/dev/null || true
aws iam detach-role-policy --role-name credit-risk-pd-lambda-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole 2>/dev/null || true
aws iam delete-role --role-name credit-risk-pd-lambda-role 2>/dev/null || true
printf 'DROP TABLE IF EXISTS credit_risk.loans;\nDROP DATABASE IF EXISTS credit_risk;\n' > /tmp/credit_drop.sql
aws/athena_run.sh /tmp/credit_drop.sql
aws s3 rb "s3://$BUCKET" --force
echo "Recursos borrados."
