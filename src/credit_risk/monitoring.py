"""Monitoreo de una cohorte nueva frente a la población de desarrollo (D16).
Estabilidad (PSI del score, CSI por variable, % fuera de dominio) y, si hay resultado, calibración."""
from __future__ import annotations

import numpy as np
import pandas as pd

from credit_risk.model import PDModel
from credit_risk.validation import binomial_by_band, psi, psi_light


def monitor(model: PDModel, ref: pd.DataFrame, new: pd.DataFrame, target: str | None = "target") -> dict:
    s_ref, s_new = model.score(ref), model.score(new)
    edges = np.quantile(s_ref.dropna(), np.linspace(0, 1, 11))
    edges[0], edges[-1] = -np.inf, np.inf
    band = lambda s: pd.cut(s.dropna(), edges, labels=range(1, 11)).astype(int)  # noqa: E731  1 = más riesgo
    out = {"n": len(new), "pct_fuera_dominio": 100 * (1 - model.in_domain(new).mean()),
           "psi_score": psi(band(s_ref), band(s_new))}
    out["semaforo_psi"] = psi_light(out["psi_score"])
    csi = {f: psi(model.binner._assign(ref[f]), model.binner._assign(new[f])) for f in model.features}
    out["csi_max"], out["csi_var"] = max(csi.values()), max(csi, key=csi.get)
    out["semaforo_csi"] = psi_light(out["csi_max"])
    if target and target in new and new[target].notna().all():
        dom = model.in_domain(new)
        d, p = new[dom], model.predict_pd(new)[dom]
        bt = binomial_by_band(band(model.score(d)), d[target], p)
        out.update({"pd_media": p.mean(), "dr_obs": d[target].mean(),
                    "bandas_subestimadas": int((bt.semaforo == "rojo").sum()),
                    "dr_fuera_dominio": new.loc[~dom, target].mean() if (~dom).any() else np.nan})
    return out
