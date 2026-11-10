import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))
from main import app  # noqa: E402

client = TestClient(app)
EXAMPLE = app.openapi()["components"]["schemas"]["Applicant"]["example"]


def test_health_and_model_info():
    assert client.get("/health").json() == {"status": "ok"}
    info = client.get("/model").json()
    assert info["domain"]["dti"][1] == 34.99 and len(info["variables"]) == 13


def test_score_in_domain_and_monotonic_in_fico():
    r = client.post("/score", json=EXAMPLE).json()
    assert r["in_domain"] and 0 < r["pd"] < 1 and 400 < r["score"] < 700
    better = client.post("/score", json={**EXAMPLE, "fico_low": 780}).json()
    assert better["pd"] < r["pd"] and better["score"] > r["score"]
    assert all(x["points_lost"] > 0 for x in r["reasons"])


def test_out_of_domain_and_validation():
    r = client.post("/score", json={**EXAMPLE, "dti": 38}).json()
    assert r["in_domain"] is False and r["pd"] is None and r["reasons"] == []
    assert client.post("/score", json={**EXAMPLE, "fico_low": 1000}).status_code == 422
    assert client.post("/score", json={"fico_low": 700, "dti": 10}).json()["in_domain"]  # resto faltante
