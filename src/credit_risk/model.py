"""Modelo PD oficial: scorecard + recalibración con MoC + dominio de aplicación (D16).

Condiciones del informe de validación aplicadas en código:
1. La PD siempre sale recalibrada (intercepto ajustado a valid 2014 + MoC por tendencia).
2. Fuera del dominio (rangos vistos en train) la PD es NaN: el modelo no extrapola.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import statsmodels.api as sm

from credit_risk.scorecard import score_from_logit
from credit_risk.woe import WoEBinner


@dataclass
class PDModel:
    binner: WoEBinner
    logit_model: object          # statsmodels LogitResults (sin datos)
    features: list[str]
    delta: float                 # ajuste de intercepto (recalibración + MoC)
    domain: dict[str, tuple[float | None, float | None]] = field(default_factory=dict)
    version: str = ""

    def in_domain(self, df: pd.DataFrame) -> pd.Series:
        ok = pd.Series(True, index=df.index)
        for col, (lo, hi) in self.domain.items():
            x = df[col]
            ok &= x.notna()
            if lo is not None:
                ok &= x >= lo
            if hi is not None:
                ok &= x <= hi
        return ok

    def logit(self, df: pd.DataFrame) -> pd.Series:
        X = sm.add_constant(self.binner.transform(df)[self.features], has_constant="add")
        return pd.Series(np.asarray(self.logit_model.predict(X, which="linear")) + self.delta, index=df.index)

    def predict_pd(self, df: pd.DataFrame) -> pd.Series:
        """PD recalibrada; NaN fuera del dominio."""
        pd_ = 1 / (1 + np.exp(-self.logit(df)))
        return pd_.where(self.in_domain(df))

    def score(self, df: pd.DataFrame) -> pd.Series:
        """Puntos del scorecard sobre la PD recalibrada; NaN fuera del dominio."""
        return pd.Series(score_from_logit(self.logit(df)), index=df.index).where(self.in_domain(df))
