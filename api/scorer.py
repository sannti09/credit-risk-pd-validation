"""Puntuador liviano del scorecard oficial: solo biblioteca estándar (sin pandas/statsmodels/pickle).
Lee la especificación JSON exportada por notebooks/14_export_model.py. Ver D23."""
from __future__ import annotations

import json
import math
from bisect import bisect_left
from pathlib import Path


class Scorecard:
    def __init__(self, spec: dict):
        self.spec = spec
        self.factor = spec["scaling"]["pdo"] / math.log(2)
        self.offset = spec["scaling"]["base_score"] - self.factor * math.log(spec["scaling"]["base_odds"])

    @classmethod
    def load(cls, path: str | Path) -> "Scorecard":
        return cls(json.loads(Path(path).read_text()))

    def _woe(self, name: str, value) -> float:
        v = self.spec["variables"][name]
        if value is None or (isinstance(value, float) and math.isnan(value)):
            w = v.get("woe_missing")
        elif v["type"] == "numeric":
            edges = [-math.inf if e is None and i == 0 else math.inf if e is None else e
                     for i, e in enumerate(v["edges"])]
            w = v["woe"][max(bisect_left(edges, float(value)) - 1, 0)]  # grupos (e_i, e_i+1]
        else:
            w = v["woe"].get(str(value), v.get("woe_other"))
        return 0.0 if w is None else w  # grupo no visto en desarrollo -> neutral (como en desarrollo)

    def in_domain(self, x: dict) -> bool:
        for col, (lo, hi) in self.spec["domain"].items():
            val = x.get(col)
            if val is None or (lo is not None and val < lo) or (hi is not None and val > hi):
                return False
        return True

    def score(self, x: dict, n_reasons: int = 3) -> dict:
        contrib = {n: v["coef"] * self._woe(n, x.get(n)) for n, v in self.spec["variables"].items()}
        logit = self.spec["intercept"] + self.spec["delta"] + sum(contrib.values())
        lost = {n: self.factor * (c - self.spec["variables"][n]["best_contrib"]) for n, c in contrib.items()}
        reasons = [{"variable": n, "points_lost": round(p, 1), "missing": x.get(n) is None}
                   for n, p in sorted(lost.items(), key=lambda kv: -kv[1])[:n_reasons] if p > 0.5]
        ok = self.in_domain(x)
        return {"in_domain": ok,
                "pd": 1 / (1 + math.exp(-logit)) if ok else None,
                "score": round(self.offset - self.factor * logit) if ok else None,
                "reasons": reasons if ok else [],
                "model_version": self.spec["version"]}
