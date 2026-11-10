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
