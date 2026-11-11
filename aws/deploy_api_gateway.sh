#!/usr/bin/env bash
# API pública con tope mensual (D30): API Gateway (REST) -> Lambda, con clave y plan de uso.
# POST /score y GET /health; clave obligatoria; plan: 100.000 llamadas/mes, 5 por segundo, ráfagas de 10.
set -euo pipefail
cd "$(dirname "$0")/.."
source aws/config.env; export AWS_PROFILE AWS_REGION
NAME=credit-risk-pd-api; FN=credit-risk-pd-score; STAGE=v1
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
FN_ARN=$(aws lambda get-function --function-name "$FN" --query Configuration.FunctionArn --output text)
URI="arn:aws:apigateway:$AWS_REGION:lambda:path/2015-03-31/functions/$FN_ARN/invocations"

API_ID=$(aws apigateway get-rest-apis --query "items[?name=='$NAME'].id | [0]" --output text)
if [[ "$API_ID" == "None" ]]; then
  API_ID=$(aws apigateway create-rest-api --name "$NAME" --endpoint-configuration types=REGIONAL \
           --tags project=credit-risk-pd --query id --output text)
  ROOT=$(aws apigateway get-resources --rest-api-id "$API_ID" --query "items[?path=='/'].id" --output text)
  for spec in "score POST" "health GET"; do
    set -- $spec
    RID=$(aws apigateway create-resource --rest-api-id "$API_ID" --parent-id "$ROOT" --path-part "$1" --query id --output text)
    aws apigateway put-method --rest-api-id "$API_ID" --resource-id "$RID" --http-method "$2" \
      --authorization-type NONE --api-key-required >/dev/null
    aws apigateway put-integration --rest-api-id "$API_ID" --resource-id "$RID" --http-method "$2" \
      --type AWS_PROXY --integration-http-method POST --uri "$URI" >/dev/null
  done
  aws lambda add-permission --function-name "$FN" --statement-id apigw-invoke --action lambda:InvokeFunction \
    --principal apigateway.amazonaws.com --source-arn "arn:aws:execute-api:$AWS_REGION:$ACCOUNT:$API_ID/*/*/*" >/dev/null
fi
aws apigateway create-deployment --rest-api-id "$API_ID" --stage-name "$STAGE" >/dev/null

PLAN_ID=$(aws apigateway get-usage-plans --query "items[?name=='$NAME-plan'].id | [0]" --output text)
if [[ "$PLAN_ID" == "None" ]]; then
  PLAN_ID=$(aws apigateway create-usage-plan --name "$NAME-plan" --tags project=credit-risk-pd \
    --api-stages "apiId=$API_ID,stage=$STAGE" --throttle burstLimit=10,rateLimit=5 \
    --quota limit=100000,period=MONTH --query id --output text)
  KEY_ID=$(aws apigateway create-api-key --name "$NAME-public-key" --enabled --tags project=credit-risk-pd \
           --query id --output text)
  aws apigateway create-usage-plan-key --usage-plan-id "$PLAN_ID" --key-id "$KEY_ID" --key-type API_KEY >/dev/null
fi
KEY_ID=$(aws apigateway get-api-keys --name-query "$NAME-public-key" --query "items[0].id" --output text)
KEY=$(aws apigateway get-api-key --api-key "$KEY_ID" --include-value --query value --output text)
URL="https://$API_ID.execute-api.$AWS_REGION.amazonaws.com/$STAGE"
grep -v '^API_URL=\|^API_KEY=' aws/config.env > aws/config.env.tmp && mv aws/config.env.tmp aws/config.env
printf "API_URL=%s\nAPI_KEY=%s\n" "$URL" "$KEY" >> aws/config.env
echo "API: $URL"
