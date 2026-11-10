"""NIIF 9: etapas, estructura temporal de PD y pérdida esperada (ECL) mensual. Ver D17-D20.

ECL = sum_t  PD_marginal(t) * LGD * EAD(t) * DF(t)
  t = 1..H meses; H = 12 (etapa 1) o meses restantes (etapa 2). Etapa 3: ECL = LGD * saldo.
  PD_marginal(t) = P * f(m+t) / (1 - P*F(m))  (P = PD de vida desde la originación, m = meses en libros)
  EAD(t) = saldo de capital al inicio del mes t según el calendario de amortización (cuota fija)
  DF(t) = 1 / (1 + r/12)^t, r = tasa del préstamo (tasa efectiva)
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def assign_stage(port: pd.DataFrame, fico_drop: float = 50, fico_floor: float = 600,
                 late31_stage: int = 3) -> np.ndarray:
    late31 = port.loan_status.isin(["Default", "Late (31-120 days)"]).to_numpy()
    sicr = ((port.loan_status == "Late (16-30 days)") | (port.fico_low - port.fico_actual >= fico_drop)
            | (port.fico_actual < fico_floor)).to_numpy()
    stage = np.where(sicr, 2, 1)
    stage = np.where(late31, late31_stage, stage)
    stage = np.where(port.loan_status.eq("Default").to_numpy(), 3, stage)  # > 120 días siempre etapa 3
    return stage


def marginal_pd(p_life: np.ndarray, mob: np.ndarray, f: np.ndarray, horizon: int = 36) -> np.ndarray:
    """Matriz (n, horizon) de PD marginal mensual, condicionada a supervivencia hasta mob.
    f: fracción de defaults por mes de vida 1..36 (suma 1)."""
    F = np.r_[0.0, np.cumsum(f)]
    f_ext = np.r_[f, np.zeros(horizon)]  # después del mes 36 no hay más defaults
    m = np.clip(mob, 0, 36).astype(int)
    idx = m[:, None] + np.arange(horizon)[None, :]  # mes de vida m+t (t desde 0 -> mes m+1)
    surv = 1 - p_life * F[m]
    return p_life[:, None] * f_ext[idx] / surv[:, None]


def amortization(balance: np.ndarray, annual_rate: np.ndarray, n_left: np.ndarray, horizon: int = 36):
    """Saldo al inicio de cada mes futuro (n, horizon) con cuota fija; 0 después del vencimiento."""
    i = annual_rate / 1200
    n = np.maximum(n_left, 1)
    pay = balance * i / (1 - (1 + i) ** -n)
    t = np.arange(horizon)[None, :]
    g = (1 + i)[:, None] ** t
    bal = balance[:, None] * g - pay[:, None] * (g - 1) / i[:, None]
    return np.where(t < n[:, None], np.maximum(bal, 0), 0.0)


def ecl(stage: np.ndarray, p_life: np.ndarray, mob: np.ndarray, balance: np.ndarray, annual_rate: np.ndarray,
        n_left: np.ndarray, f: np.ndarray, lgd: float, stage2_mult: float = 2.0, pd_mult: float = 1.0,
        horizon: int = 36) -> pd.DataFrame:
    """ECL por préstamo. pd_mult = multiplicador de escenario macro (1 = base)."""
    p = np.minimum(p_life * pd_mult * np.where(stage == 2, stage2_mult, 1.0), 0.99)
    mpd = marginal_pd(p, mob, f, horizon)
    ead = amortization(balance, annual_rate, n_left, horizon)
    df = (1 + annual_rate / 1200)[:, None] ** -(np.arange(horizon)[None, :] + 1)
    h = np.where(stage == 1, 12, horizon)
    mask = np.arange(horizon)[None, :] < h[:, None]
    loss = (mpd * lgd * ead * df * mask).sum(axis=1)
    loss = np.where(stage == 3, lgd * balance, loss)
    pd_h = np.where(stage == 3, 1.0, (mpd * mask).sum(axis=1))
    return pd.DataFrame({"etapa": stage, "pd_horizonte": pd_h, "ecl": loss, "saldo": balance})
