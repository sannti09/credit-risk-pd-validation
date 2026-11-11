"""Gráficos NIIF 9 para el README (D35): puente SFC -> NIIF 9, reparto por etapa y sensibilidades.
Lee reports/dashboard/{bridge,stage_mix,sensitivity}.csv. Salidas: docs/img/ifrs9_overview{,_dark}.png"""
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.gridspec import GridSpec

br = pd.read_csv("reports/dashboard/bridge.csv").sort_values("order")
mix = pd.read_csv("reports/dashboard/stage_mix.csv")
se = pd.read_csv("reports/dashboard/sensitivity.csv").sort_values("change_vs_base_pct")

THEMES = {  # paleta de referencia (dataviz): polaridad naranja/azul, etapas en rampa de un solo tono
    "": dict(bg="#fcfcfb", ink="#0b0b0b", ink2="#55554f", grid="#e4e3dd", up="#eb6834", down="#2a78d6",
             total="#55554f", stages=("#b7d3f6", "#5598e7", "#184f95")),
    "_dark": dict(bg="#1a1a19", ink="#f0efec", ink2="#c3c2b7", grid="#34342f", up="#d95926", down="#3987e5",
                  total="#c3c2b7", stages=("#2b4a73", "#3987e5", "#9ec5f4")),
}
for suf, t in THEMES.items():
    fig = plt.figure(figsize=(11, 11), dpi=150, facecolor=t["bg"])
    gs = GridSpec(3, 1, figure=fig, height_ratios=[1.2, 0.42, 1.0], hspace=0.55)
    axes = [fig.add_subplot(gs[i]) for i in range(3)]
    for ax in axes:
        ax.set_facecolor(t["bg"])
        for sp in ax.spines.values():
            sp.set_visible(False)
        ax.tick_params(colors=t["ink2"], labelsize=8, length=0)

    # 1) Puente SFC (Matriz A) -> ECL NIIF 9 base
    ax = axes[0]
    col = {"Start": t["total"], "Total": t["total"], "Increase": t["up"], "Decrease": t["down"]}
    x = range(len(br))
    ax.bar(x, br.bar_length, bottom=br.bar_base, color=[col[k] for k in br.kind], width=0.6, zorder=2)
    for i, r in enumerate(br.itertuples()):
        top = r.bar_base + r.bar_length
        lab = f"{r.effect:,.1f}" if r.kind in ("Start", "Total") else f"{r.effect:+,.1f}"
        ax.text(i, top + 4, lab, ha="center", va="bottom", fontsize=8, color=t["ink"])
    names = ["SFC provision\n(Matrix A)", "LGD 75% →\n90.7% observed", "PD: matrix →\nmodel 12m", "Stage 2:\nlifetime",
             "Balance\namortization", "Discounting", "IFRS 9 ECL\n(base)"]
    ax.set_xticks(list(x), names, fontsize=8, color=t["ink2"])
    ax.set_ylim(0, 340)
    ax.yaxis.grid(True, color=t["grid"], lw=0.8, zorder=0)
    ax.set_ylabel("US$ M", color=t["ink2"], fontsize=8)
    ax.set_title("Why the SFC provision and the IFRS 9 ECL nearly coincide", loc="left", fontsize=11,
                 color=t["ink"], fontweight="bold", pad=18)
    ax.text(0, 1.03, "Offsetting effects: higher observed LGD and lifetime horizon add; amortization and discounting "
            "subtract.", transform=ax.transAxes, fontsize=8.5, color=t["ink2"])

    # 2) Reparto por etapa: saldo vs. pérdida esperada (barras apiladas al 100%)
    ax = axes[1]
    piv = mix.pivot(index="metric", columns="stage", values="share").loc[["Share of expected loss", "Share of balance"]]
    left = [0.0, 0.0]
    for st, c in zip(["Stage 1", "Stage 2", "Stage 3"], t["stages"]):
        v = piv[st].to_numpy()
        ax.barh([0, 1], v, left=left, color=c, height=0.55, edgecolor=t["bg"], linewidth=2, label=st, zorder=2)
        for i in (0, 1):
            if v[i] >= 0.06:
                txt_col = t["bg"] if c == t["stages"][2] or (suf == "" and c == t["stages"][1]) else t["ink"]
                ax.text(left[i] + v[i] / 2, i, f"{v[i]:.0%}", ha="center", va="center", fontsize=8, color=txt_col)
        left = [left[0] + v[0], left[1] + v[1]]
    ax.text(1.012, 1, "Stage 3: 1%", va="center", fontsize=8, color=t["ink2"])
    ax.set_yticks([0, 1], ["Expected loss", "Balance"], fontsize=8.5, color=t["ink2"])
    ax.set_xlim(0, 1.1)
    ax.set_xticks([])
    ax.legend(frameon=False, fontsize=8, labelcolor=t["ink"], ncol=3, loc="upper left", bbox_to_anchor=(0, -0.05))
    ax.set_title("Stage 3 is 1% of the balance but 19% of the loss", loc="left", fontsize=10.5, color=t["ink"],
                 fontweight="bold", pad=10)

    # 3) Sensibilidades (cambio % vs. ECL base)
    ax = axes[2]
    c = [t["up"] if v >= 0 else t["down"] for v in se.change_vs_base_pct]
    ax.barh(range(len(se)), se.change_vs_base_pct, color=c, height=0.6, zorder=2)
    ax.axvline(0, color=t["ink2"], lw=0.8)
    for i, v in enumerate(se.change_vs_base_pct):
        ax.text(v + (0.6 if v >= 0 else -0.6), i, f"{v:+.1f}%", va="center", ha="left" if v >= 0 else "right",
                fontsize=7.5, color=t["ink"])
    ax.set_yticks(range(len(se)), se.assumption, fontsize=7.5, color=t["ink2"])
    ax.set_xlim(-20, 25)
    ax.xaxis.grid(True, color=t["grid"], lw=0.8, zorder=0)
    ax.set_xlabel("Change vs. base ECL (US$ 223.6 M)", fontsize=8, color=t["ink2"])
    ax.set_title("What moves the ECL", loc="left", fontsize=10.5, color=t["ink"], fontweight="bold", pad=10)

    fig.savefig(f"docs/img/ifrs9_overview{suf}.png", facecolor=t["bg"], bbox_inches="tight")
    plt.close(fig)
print("docs/img/ifrs9_overview.png y _dark.png")
