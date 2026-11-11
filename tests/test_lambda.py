import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "api"), str(ROOT / "aws" / "lambda")]
os.environ["MODEL_PATH"] = str(ROOT / "models" / "scorecard_v1.json")
from handler import lambda_handler  # noqa: E402
from scorer import Scorecard  # noqa: E402

APP = {"fico_low": 690, "dti": 18.5, "annual_inc": 65000, "revol_util": 55, "home_ownership": "RENT"}


def test_lambda_matches_scorer_direct_and_http_event():
    expected = Scorecard.load(os.environ["MODEL_PATH"]).score(APP)
    direct = lambda_handler(APP)
    http = lambda_handler({"body": json.dumps(APP)})
    assert direct["statusCode"] == http["statusCode"] == 200
    assert json.loads(direct["body"]) == json.loads(http["body"]) == expected


def test_lambda_validation():
    assert lambda_handler({**APP, "home_ownership": "rent"})["statusCode"] == 422
    assert lambda_handler({"dti": 10})["statusCode"] == 422
    assert lambda_handler({**APP, "fico_low": 1000})["statusCode"] == 422
    assert lambda_handler({"body": "no es json"})["statusCode"] == 400
