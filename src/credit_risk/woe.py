"""Weight of Evidence (WoE) e Information Value (IV) para scorecards.

Convención (estándar en scorecards):
    WoE = ln(%buenos / %malos)   -> WoE > 0: grupo de menor riesgo.
    IV  = sum((%buenos - %malos) * WoE)

Reglas:
- Los cortes (bins) se aprenden SOLO en entrenamiento y se aplican igual en OOT (sin fuga).
- Numéricas: cortes finos por cuantiles y luego coarse classing monótono (tasa de default
  siempre creciente o siempre decreciente, cada grupo con >= 5% de la muestra). Faltantes = grupo propio "MISSING" (en Lending Club el vacío
  suele significar "nunca", p. ej. nunca ha tenido mora).
- Categóricas: cada categoría es un grupo; las raras (< min_share) se agrupan en "OTHER".
- Suavizado (+0.5) para evitar ln(0) en grupos sin buenos o sin malos.
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

MISSING = "MISSING"
OTHER = "OTHER"


def iv_strength(iv: float) -> str:
    """Interpretación habitual del IV (Siddiqi)."""
    if iv < 0.02:
        return "inútil"
    if iv < 0.1:
        return "débil"
    if iv < 0.3:
        return "media"
    if iv < 0.5:
        return "fuerte"
    return "sospechosa (revisar fuga)"


class WoEBinner:
    """Aprende cortes y WoE por variable en train; transforma cualquier muestra."""

    def __init__(self, n_bins: int = 20, min_share: float = 0.01, smoothing: float = 0.5,
                 monotonic: bool = True, min_bin_share: float = 0.05):
        self.n_bins = n_bins  # grupos finos iniciales (fine classing)
        self.monotonic = monotonic
        self.min_bin_share = min_bin_share
        self.min_share = min_share
        self.smoothing = smoothing
        self.edges_: dict[str, np.ndarray] = {}
        self.categories_: dict[str, set] = {}
        self.tables_: dict[str, pd.DataFrame] = {}

    # ---------- agrupación ----------
    def _fit_bins(self, x: pd.Series, y: pd.Series) -> None:
        if pd.api.types.is_numeric_dtype(x):
            q = np.unique(np.nanquantile(x.dropna(), np.linspace(0, 1, self.n_bins + 1)))
            edges = np.concatenate(([-np.inf], q[1:-1], [np.inf]))
            if self.monotonic:
                edges = self._coarse_monotonic(x, y, edges)
            self.edges_[x.name] = edges
        else:
            share = x.value_counts(normalize=True, dropna=True)
            self.categories_[x.name] = set(share[share >= self.min_share].index)

    def _coarse_monotonic(self, x: pd.Series, y: pd.Series, edges: np.ndarray) -> np.ndarray:
        """Coarse classing: fusiona grupos vecinos hasta que la tasa de default sea monótona
        (dirección = signo de la correlación de Spearman) y cada grupo tenga >= min_bin_share."""
        mask = x.notna()
        xs, ys = x[mask], y[mask]
        increasing = xs.rank().corr(ys) > 0
        edges = list(edges)
        while len(edges) > 2:
            codes = pd.cut(xs, edges, labels=False)
            g = ys.groupby(codes)
            n = g.size().reindex(range(len(edges) - 1), fill_value=0)
            rate = (g.sum() / g.size()).reindex(n.index)
            share = n / n.sum()
            merge = None
            for i in range(len(n) - 1):  # 1) grupos muy pequeños
                if share[i] < self.min_bin_share:
                    merge = i
                    break
            if merge is None and share.iloc[-1] < self.min_bin_share:
                merge = len(n) - 2
            if merge is None:  # 2) violaciones de monotonía
                for i in range(len(n) - 1):
                    d = rate[i + 1] - rate[i]
                    if (increasing and d < 0) or (not increasing and d > 0):
                        merge = i
                        break
            if merge is None:
                break
            del edges[merge + 1]  # une el grupo merge con merge+1
        return np.array(edges)

    def _assign(self, x: pd.Series) -> pd.Series:
        if x.name in self.edges_:
            e = self.edges_[x.name]
            labels = [f"{i:02d} ({e[i]:.4g}, {e[i + 1]:.4g}]" for i in range(len(e) - 1)]
            b = pd.cut(x, e, right=True, labels=labels).astype(str)  # prefijo 00, 01.. = orden
        else:
            keep = self.categories_[x.name]
            b = x.astype(object).where(x.isin(keep), OTHER).astype(str)  # robusto a dtype categórico
        return b.where(x.notna(), MISSING)

    # ---------- API ----------
    def fit(self, df: pd.DataFrame, target: str, features: list[str]) -> "WoEBinner":
        y = df[target]
        n_bad, n_good = y.sum(), (1 - y).sum()
        for f in features:
            self._fit_bins(df[f], y)
            g = pd.DataFrame({"bin": self._assign(df[f]), "y": y}).groupby("bin")["y"]
            t = pd.DataFrame({"n": g.size(), "bad": g.sum()})
            t["good"] = t["n"] - t["bad"]
            t["bad_rate"] = t["bad"] / t["n"]
            pct_good = (t["good"] + self.smoothing) / n_good
            pct_bad = (t["bad"] + self.smoothing) / n_bad
            t["woe"] = np.log(pct_good / pct_bad)
            t["iv"] = (pct_good - pct_bad) * t["woe"]
            self.tables_[f] = t
        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Reemplaza cada variable por su WoE. Grupos no vistos en train -> WoE 0 (neutral), con alerta."""
        out, unseen = {}, {}
        for f, t in self.tables_.items():
            w = self._assign(df[f]).map(t["woe"])
            if w.isna().any():
                unseen[f] = int(w.isna().sum())
            out[f] = w.fillna(0.0).astype(float)
        if unseen:
            warnings.warn(f"Grupos no vistos en train (WoE=0): {unseen}", stacklevel=2)
        return pd.DataFrame(out, index=df.index)

    def iv_summary(self) -> pd.DataFrame:
        s = pd.DataFrame(
            {"iv": {f: t["iv"].sum() for f, t in self.tables_.items()},
             "n_bins": {f: len(t) for f, t in self.tables_.items()}}
        ).sort_values("iv", ascending=False)
        s["fuerza"] = s["iv"].map(iv_strength)
        return s
