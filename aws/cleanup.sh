#!/usr/bin/env bash
# BORRA todos los recursos AWS del proyecto: tabla y base de Athena, y el bucket con su contenido.
# Irreversible (los datos se pueden volver a subir con aws/upload.sh). Pide confirmación.
set -euo pipefail
cd "$(dirname "$0")/.."
source aws/config.env; export AWS_PROFILE AWS_REGION
read -r -p "Se borrará la base credit_risk y el bucket $BUCKET con todo su contenido. Escribe BORRAR para continuar: " ok
[[ "$ok" == "BORRAR" ]] || { echo "Cancelado."; exit 1; }
printf 'DROP TABLE IF EXISTS credit_risk.loans;\nDROP DATABASE IF EXISTS credit_risk;\n' > /tmp/credit_drop.sql
aws/athena_run.sh /tmp/credit_drop.sql
aws s3 rb "s3://$BUCKET" --force
echo "Recursos borrados."
