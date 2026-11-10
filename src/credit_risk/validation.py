"""Pruebas de validación: estabilidad (PSI/CSI) y calibración (Hosmer-Lemeshow, binomial por banda).

Semáforos (umbrales de industria):
    PSI/CSI: < 0,10 verde · 0,10-0,25 ámbar · > 0,25 rojo
    Tests de calibración (p-valor): > 0,05 verde · 0,01-0,05 ámbar · < 0,01 rojo
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats


def psi(expected: pd.Series, actual: pd.Series) -> float:
    """PSI entre dos distribuciones ya agrupadas (mismas categorías). sum((a - e) * ln(a / e))."""
    e = expected.value_counts(normalize=True)
    a = actual.value_counts(normalize=True).reindex(e.index.union(actual.unique()), fill_value=0)
    e = e.reindex(a.index, fill_value=0)
    e, a = e.clip(lower=1e-6), a.clip(lower=1e-6)
    return float(((a - e) * np.log(a / e)).sum())


def psi_light(v: float) -> str:
    return "verde" if v < 0.10 else ("ámbar" if v <= 0.25 else "rojo")


def p_light(p: float) -> str:
    return "verde" if p > 0.05 else ("ámbar" if p >= 0.01 else "rojo")


def hosmer_lemeshow(y, pd_hat, g: int = 10) -> tuple[float, float]:
    """H-L: agrupa por deciles de PD y compara defaults observados vs esperados. Devuelve (estadístico, p)."""
    d = pd.DataFrame({"y": np.asarray(y), "p": np.asarray(pd_hat)})
    d["g"] = pd.qcut(d["p"], g, labels=False, duplicates="drop")
    t = d.groupby("g").agg(n=("y", "size"), obs=("y", "sum"), exp=("p", "sum"))
    stat = (((t.obs - t.exp) ** 2) / (t.exp * (1 - t.exp / t.n))).sum()
    return float(stat), float(stats.chi2.sf(stat, len(t) - 2))


def binomial_by_band(band: pd.Series, y: pd.Series, pd_hat: pd.Series) -> pd.DataFrame:
    """Test binomial unilateral por banda: H0 PD real <= PD estimada (¿se subestima el riesgo?)."""
    rows = []
    for k, idx in band.groupby(band).groups.items():
        n, obs, pd_mean = len(idx), int(y.loc[idx].sum()), float(pd_hat.loc[idx].mean())
        p = stats.binomtest(obs, n, pd_mean, alternative="greater").pvalue
        rows.append({"banda": k, "n": n, "pd_estimada": pd_mean, "dr_observada": obs / n,
                     "p_valor": p, "semaforo": p_light(p)})
    return pd.DataFrame(rows).set_index("banda")
