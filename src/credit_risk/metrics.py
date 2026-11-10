"""Métricas de discriminación. Convención: score/PD más alto = más riesgo."""
from __future__ import annotations

import numpy as np
from sklearn.metrics import roc_auc_score, roc_curve


def gini(y, pd_score) -> float:
    """Gini = 2*AUC - 1."""
    return 2 * roc_auc_score(y, pd_score) - 1


def ks(y, pd_score) -> float:
    """Kolmogorov-Smirnov: máxima separación entre las distribuciones acumuladas de buenos y malos."""
    fpr, tpr, _ = roc_curve(y, pd_score)
    return float(np.max(tpr - fpr))
