#!/usr/bin/env bash
# Despliega (o actualiza) la función Lambda de scoring (D29). Sin dependencias: scorer + handler + JSON del modelo.
set -euo pipefail
cd "$(dirname "$0")/.."
source aws/config.env; export AWS_PROFILE AWS_REGION
FN=credit-risk-pd-score; ROLE=credit-risk-pd-lambda-role; TAGS="project=credit-risk-pd"
PKG=$(mktemp -d); cp api/scorer.py aws/lambda/handler.py models/scorecard_v1.json "$PKG"/
(cd "$PKG" && zip -q -r function.zip handler.py scorer.py scorecard_v1.json)
if ! aws iam get-role --role-name "$ROLE" >/dev/null 2>&1; then
  aws iam create-role --role-name "$ROLE" --tags Key=project,Value=credit-risk-pd \
    --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]}' >/dev/null
  aws iam attach-role-policy --role-name "$ROLE" \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole   # solo escribir logs
  sleep 10  # propagación del rol en IAM
fi
ROLE_ARN=$(aws iam get-role --role-name "$ROLE" --query Role.Arn --output text)
if aws lambda get-function --function-name "$FN" >/dev/null 2>&1; then
  aws lambda update-function-code --function-name "$FN" --zip-file "fileb://$PKG/function.zip" >/dev/null
else
  for i in 1 2 3 4 5; do
    aws lambda create-function --function-name "$FN" --runtime python3.12 --architectures arm64 \
      --handler handler.lambda_handler --role "$ROLE_ARN" --zip-file "fileb://$PKG/function.zip" \
      --memory-size 128 --timeout 5 --tags "$TAGS" >/dev/null && break || sleep 8
  done
fi
aws lambda wait function-active-v2 --function-name "$FN"
echo "Función lista: $FN ($(du -h "$PKG/function.zip" | cut -f1))"
