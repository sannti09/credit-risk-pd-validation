"""Escalado de un modelo logístico sobre WoE a puntos de scorecard.

score = offset + factor * ln(odds_buenos)
factor = PDO / ln(2)  -> cada PDO puntos se duplican las odds buenos:malos
offset = base_score - factor * ln(base_odds)
Con logit(P(malo)) = a + sum(b_i * WoE_i), ln(odds_buenos) = -(a + sum b_i*WoE_i).
Puntos de la variable i en un grupo = -factor * (b_i * WoE + a/n) + offset/n.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def points_table(intercept: float, coefs: pd.Series, woe_tables: dict[str, pd.DataFrame],
                 base_score: float = 600, base_odds: float = 50, pdo: float = 20) -> pd.DataFrame:
    factor = pdo / np.log(2)
    offset = base_score - factor * np.log(base_odds)
    n = len(coefs)
    rows = []
    for f, b in coefs.items():
        t = woe_tables[f]
        pts = -factor * (b * t["woe"] + intercept / n) + offset / n
        rows.append(pd.DataFrame({"feature": f, "bin": t.index, "woe": t["woe"].values,
                                  "bad_rate": t["bad_rate"].values, "points": pts.round().values}))
    return pd.concat(rows, ignore_index=True)


def score_from_logit(logit_bad, base_score: float = 600, base_odds: float = 50, pdo: float = 20):
    factor = pdo / np.log(2)
    return base_score - factor * np.log(base_odds) - factor * np.asarray(logit_bad)
