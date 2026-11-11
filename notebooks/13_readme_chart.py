"""Gráfico del README: calibración por banda de riesgo en OOT 2015 (solo préstamos dentro de dominio).
Salidas: docs/img/calibration_oot.png (claro) y docs/img/calibration_oot_dark.png (oscuro)."""
import pickle
from dataclasses import replace

import duckdb
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

model = pickle.load(open("models/pd_model_final.pkl", "rb"))
con = duckdb.connect("data/credit.duckdb", read_only=True)
train = con.sql("select * from model_sample where split='train'").df()
oot = con.sql("select * from model_sample where split='oot'").df()
oot = oot[model.in_domain(oot)]

orig = replace(model, delta=0.0)  # modelo sin recalibrar
edges = np.quantile(orig.logit(train), np.linspace(0, 1, 11))
edges[0], edges[-1] = -np.inf, np.inf
band = pd.cut(orig.logit(oot), edges, labels=range(10, 0, -1)).astype(int)  # 1 = más riesgo
t = pd.DataFrame({"band": band, "obs": oot.target, "orig": orig.predict_pd(oot), "final": model.predict_pd(oot)})
g = t.groupby("band").mean().sort_index() * 100

THEMES = {
    "": dict(bg="#fcfcfb", ink="#0b0b0b", ink2="#55554f", grid="#e4e3dd", c=("#2a78d6", "#eb6834", "#1baf7a")),
    "_dark": dict(bg="#1a1a19", ink="#f0efec", ink2="#c3c2b7", grid="#34342f", c=("#3987e5", "#d95926", "#199e70")),
}
for suffix, th in THEMES.items():
    fig, ax = plt.subplots(figsize=(8, 4.2), dpi=150)
    fig.patch.set_facecolor(th["bg"]); ax.set_facecolor(th["bg"])
    x = g.index.to_numpy()
    ax.bar(x, g.obs, width=0.62, color=th["c"][0], alpha=0.85, label="Observed default rate", zorder=2)
    ax.plot(x, g.orig, color=th["c"][1], lw=2, marker="o", ms=7, mec=th["bg"], mew=2,
            label="Original model (under-predicts)", zorder=3)
    ax.plot(x, g.final, color=th["c"][2], lw=2, marker="s", ms=7, mec=th["bg"], mew=2,
            label="Recalibrated official model", zorder=4)
    ax.set_xticks(x, [f"{i}" for i in x])
    ax.set_xlabel("Risk band (1 = highest risk)  ·  out-of-time sample 2015", color=th["ink2"], fontsize=9)
    ax.set_ylabel("Default rate (%)", color=th["ink2"], fontsize=9)
    ax.set_title("Calibration by risk band: the official model matches observed defaults",
                 color=th["ink"], fontsize=11, loc="left", pad=12)
    ax.yaxis.grid(True, color=th["grid"], lw=0.8, zorder=0)
    ax.tick_params(colors=th["ink2"], labelsize=8, length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    leg = ax.legend(frameon=False, fontsize=8, loc="upper right", labelcolor=th["ink"])
    fig.tight_layout()
    fig.savefig(f"docs/img/calibration_oot{suffix}.png", facecolor=th["bg"])
    plt.close(fig)
g.round(4).to_csv("reports/calibration_bands_oot.csv")
print(g.round(1).to_string())
