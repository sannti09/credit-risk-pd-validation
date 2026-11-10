"""Recalibración de PD (no cambia el ordenamiento: Gini/KS iguales).

- Intercepto (calibration-in-the-large): logit' = logit + delta, con delta tal que PD media = tasa observada.
- Platt: logit' = a + b * logit, estimado por regresión logística de y sobre logit (ajusta nivel y pendiente).
"""
from __future__ import annotations

import numpy as np
import statsmodels.api as sm
from scipy.optimize import brentq


def _sigmoid(z):
    return 1 / (1 + np.exp(-np.asarray(z)))


def fit_intercept_shift(logit, y) -> float:
    target = float(np.mean(y))
    return brentq(lambda d: _sigmoid(np.asarray(logit) + d).mean() - target, -5, 5)


def fit_platt(logit, y) -> tuple[float, float]:
    m = sm.Logit(np.asarray(y), sm.add_constant(np.asarray(logit))).fit(disp=0)
    return float(m.params[0]), float(m.params[1])


def apply_shift(logit, delta):
    return _sigmoid(np.asarray(logit) + delta)


def apply_platt(logit, a, b):
    return _sigmoid(a + b * np.asarray(logit))
