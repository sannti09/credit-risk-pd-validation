"""Paridad API vs. modelo oficial (D27): casos sintéticos exportados por notebooks/14_export_model.py."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))
from scorer import Scorecard  # noqa: E402


def test_json_scorer_matches_official_model():
    sc = Scorecard.load(ROOT / "models" / "scorecard_v1.json")
    cases = json.loads((ROOT / "tests" / "fixtures" / "parity_cases.json").read_text())
    assert len(cases) >= 100
    for c in cases:
        got = sc.score(c["input"])["pd"]
        if c["pd"] is None:
            assert got is None
        else:
            assert abs(got - c["pd"]) < 1e-9
