import numpy as np

from credit_risk.metrics import gini, ks
from credit_risk.scorecard import score_from_logit


def test_perfect_and_random():
    y = np.array([0, 0, 1, 1])
    assert gini(y, [0.1, 0.2, 0.8, 0.9]) == 1.0 and ks(y, [0.1, 0.2, 0.8, 0.9]) == 1.0
    assert gini(y, [0.5] * 4) == 0.0


def test_score_scaling_pdo():
    # odds buenos 50:1 -> 600 puntos; odds 100:1 -> 620 (PDO = 20)
    assert round(score_from_logit(np.log(1 / 50)), 6) == 600
    assert round(score_from_logit(np.log(1 / 100)), 6) == 620


def test_points_sum_matches_score():
    import pandas as pd

    from credit_risk.scorecard import points_table

    woe = {"a": pd.DataFrame({"woe": [-0.5, 0.0, 0.7], "bad_rate": [0.3, 0.2, 0.1]}, index=["b0", "b1", "b2"]),
           "b": pd.DataFrame({"woe": [-0.2, 0.4], "bad_rate": [0.25, 0.12]}, index=["c0", "c1"])}
    coefs = pd.Series({"a": -0.8, "b": -0.6})
    pts = points_table(-1.9, coefs, woe)
    total = pts[pts.bin == "b2"].points.iloc[0] + pts[pts.bin == "c1"].points.iloc[0]
    exact = score_from_logit(-1.9 + (-0.8) * 0.7 + (-0.6) * 0.4)
    assert abs(total - exact) <= 0.5 * len(coefs)  # diferencia solo por redondeo
