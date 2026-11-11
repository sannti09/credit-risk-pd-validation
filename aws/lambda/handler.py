"""AWS Lambda: scoring del modelo PD oficial (D29). Mismo puntuador y especificación JSON que la API Docker.
Acepta invocación directa ({"fico_low": ..., ...}) o evento HTTP de Function URL ({"body": "..."})."""
import json
import os

from scorer import Scorecard

SC = Scorecard.load(os.environ.get("MODEL_PATH", "scorecard_v1.json"))
HOME = {"MORTGAGE", "OWN", "RENT", "OTHER", "NONE", "ANY"}
PURPOSE = {"debt_consolidation", "credit_card", "home_improvement", "other", "major_purchase", "small_business",
           "car", "medical", "moving", "vacation", "house", "wedding", "renewable_energy", "educational"}
RANGES = {"fico_low": (300, 850), "dti": (0, 100), "annual_inc": (0, None), "percent_bc_gt_75": (0, 100)}


def _validate(x: dict) -> list[str]:
    """Mismas reglas clave que la API FastAPI (api/main.py): obligatorios, rangos y categorías válidas."""
    err = [f"{k} es obligatorio" for k in ("fico_low", "dti") if x.get(k) is None]
    for k, (lo, hi) in RANGES.items():
        v = x.get(k)
        if v is not None and (not isinstance(v, (int, float)) or (lo is not None and v < lo)
                              or (hi is not None and v > hi)):
            err.append(f"{k} fuera de rango")
    if x.get("home_ownership") not in (None, *HOME):
        err.append("home_ownership inválido")
    if x.get("purpose") not in (None, *PURPOSE):
        err.append("purpose inválido")
    return err


def _resp(code: int, body: dict) -> dict:
    return {"statusCode": code, "headers": {"Content-Type": "application/json"}, "body": json.dumps(body)}


def lambda_handler(event, context=None):
    try:
        x = json.loads(event["body"]) if isinstance(event, dict) and "body" in event else event
    except (TypeError, ValueError):
        return _resp(400, {"error": "JSON inválido"})
    if not isinstance(x, dict):
        return _resp(400, {"error": "se espera un objeto JSON"})
    if x.get("path") == "/health":
        return _resp(200, {"status": "ok", "model_version": SC.spec["version"]})
    err = _validate(x)
    return _resp(422, {"errors": err}) if err else _resp(200, SC.score(x))
